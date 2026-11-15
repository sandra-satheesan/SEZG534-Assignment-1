"""Asynchronous repeated evaluation runner."""

from __future__ import annotations

import asyncio
import hashlib
import importlib.metadata
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from app.core.settings import Settings
from app.evaluation.cases import EvaluationCase, EvaluationCaseSet
from app.evaluation.reporting import write_report
from app.evaluation.scoring import (
    AGGREGATE_WEIGHTS,
    AcceptanceThresholds,
    EvaluationMetrics,
    aggregate_score,
)
from app.prompts.reminder_interpretation import build_interpretation_prompt
from app.providers.base import ModelProvider
from app.providers.groq import GroqProvider
from app.schemas.requests import InterpretationRequest, ReferenceContext
from app.schemas.responses import InterpretationResult
from app.services.invariants import validate_interpretation_result


@dataclass(frozen=True, slots=True)
class RunEvidence:
    run_number: int
    schema_valid: bool
    invariant_valid: bool
    expected_behavior: bool
    semantic_score: float
    failure_code: str | None
    failed_properties: list[str]


@dataclass(frozen=True, slots=True)
class CaseEvidence:
    case_id: str
    runs: list[RunEvidence]


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    run_id: str
    report_path: Path
    case_set_digest: str
    evaluation_config_digest: str
    run_count: int
    case_count: int
    case_results: dict[str, CaseEvidence]
    metrics: EvaluationMetrics
    aggregate: float
    failed_gates: list[str]
    acceptance_passed: bool


class EvaluationRunner:
    def __init__(
        self,
        *,
        case_set: EvaluationCaseSet,
        provider_factory: Callable[[], ModelProvider],
        results_dir: Path,
        runs_per_case: int = 3,
        thresholds: AcceptanceThresholds | None = None,
        evaluation_metadata: dict[str, str] | None = None,
    ) -> None:
        if runs_per_case < 3:
            raise ValueError("At least three runs per case are required.")
        self.case_set = case_set
        self.provider_factory = provider_factory
        self.results_dir = results_dir
        self.runs_per_case = runs_per_case
        self.thresholds = thresholds or AcceptanceThresholds()
        self.evaluation_metadata = evaluation_metadata or {}
        self._provider_types: set[str] = set()

    async def run(self) -> EvaluationReport:
        case_results: dict[str, CaseEvidence] = {}
        all_schema: list[bool] = []
        all_invariants: list[bool] = []
        all_semantic: list[float] = []
        all_expected: list[bool] = []

        for case in self.case_set.cases:
            runs: list[RunEvidence] = []
            for run_number in range(1, self.runs_per_case + 1):
                evidence = await self._evaluate_case(case, run_number)
                runs.append(evidence)
                all_schema.append(evidence.schema_valid)
                all_invariants.append(evidence.invariant_valid)
                all_semantic.append(evidence.semantic_score)
                all_expected.append(evidence.expected_behavior)
            case_results[case.case_id] = CaseEvidence(case.case_id, runs)

        metrics = EvaluationMetrics(
            schema_correctness=sum(all_schema) / len(all_schema),
            invariant_correctness=sum(all_invariants) / len(all_invariants),
            semantic_quality=sum(all_semantic) / len(all_semantic),
            reliability=sum(all_expected) / len(all_expected),
        )
        failed_gates = self.thresholds.failed_gates(metrics)
        run_id = f"evaluation-{self.case_set.digest()[:12]}"
        config_payload = {
            "runs_per_case": self.runs_per_case,
            "weights": AGGREGATE_WEIGHTS,
            "thresholds": asdict(self.thresholds),
            "provider_types": sorted(self._provider_types),
            "sdk_versions": {
                "groq": importlib.metadata.version("groq"),
            },
            "metadata": self.evaluation_metadata,
        }
        config_digest = hashlib.sha256(
            json.dumps(config_payload, sort_keys=True).encode()
        ).hexdigest()
        report = EvaluationReport(
            run_id=run_id,
            report_path=Path(),
            case_set_digest=self.case_set.digest(),
            evaluation_config_digest=config_digest,
            run_count=self.runs_per_case,
            case_count=len(self.case_set.cases),
            case_results=case_results,
            metrics=metrics,
            aggregate=aggregate_score(metrics),
            failed_gates=failed_gates,
            acceptance_passed=not failed_gates,
        )
        report_path = write_report(report, self.results_dir)
        return replace(report, report_path=report_path)

    async def _evaluate_case(self, case: EvaluationCase, run_number: int) -> RunEvidence:
        reference_context = (
            ReferenceContext.model_validate(
                case.reference_context.model_dump(mode="json")
            )
            if case.reference_context is not None
            else None
        )
        request = InterpretationRequest(text=case.text, reference_context=reference_context)
        provider = self.provider_factory()
        self._provider_types.add(type(provider).__qualname__)
        failure_code: str | None = None
        failed_properties: list[str] = []
        schema_valid = False
        invariant_valid = False
        result: InterpretationResult | None = None
        try:
            output = await provider.generate(build_interpretation_prompt(request))
            result = InterpretationResult.model_validate_json(output)
            schema_valid = True
            try:
                validate_interpretation_result(request, result)
                invariant_valid = True
            except Exception:
                failure_code = "invariant_failure"
                failed_properties.append("invariant_correctness")
        except Exception:
            failure_code = "schema_failure"
            failed_properties.append("schema_correctness")

        expected_behavior = self._expected_behavior(case, result)
        semantic_score = self._semantic_score(case, result)
        if not expected_behavior:
            failed_properties.append("reliability")
        if semantic_score < self.thresholds.semantic_quality:
            failed_properties.append("semantic_quality")
        return RunEvidence(
            run_number=run_number,
            schema_valid=schema_valid,
            invariant_valid=invariant_valid,
            expected_behavior=expected_behavior,
            semantic_score=semantic_score,
            failure_code=failure_code,
            failed_properties=sorted(set(failed_properties)),
        )

    @staticmethod
    def _expected_behavior(case: EvaluationCase, result: InterpretationResult | None) -> bool:
        return result is not None and result.status == case.expected_status

    @staticmethod
    def _semantic_score(case: EvaluationCase, result: InterpretationResult | None) -> float:
        if result is None:
            return 0.0
        serialized = result.model_dump_json().casefold()
        if any(fact.casefold() not in serialized for fact in case.required_facts):
            return 0.0
        if any(fact.casefold() in serialized for fact in case.forbidden_facts):
            return 0.0
        return 1.0


async def run_groq_evaluation(
    case_set: EvaluationCaseSet,
    results_dir: Path,
    settings: Settings,
    runs_per_case: int = 3,
) -> EvaluationReport:
    if settings.groq_api_key is None:
        raise ValueError("GROQ_API_KEY is required for live evaluation.")
    return await EvaluationRunner(
        case_set=case_set,
        provider_factory=lambda: GroqProvider(settings),
        results_dir=results_dir,
        runs_per_case=runs_per_case,
        evaluation_metadata={"model": settings.groq_model},
    ).run()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run opt-in Groq evaluation.")
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    args = parser.parse_args()
    from app.evaluation.cases import load_case_set

    asyncio.run(
        run_groq_evaluation(
            load_case_set(args.cases),
            args.results,
            Settings.from_environment(),
        )
    )


if __name__ == "__main__":
    main()
