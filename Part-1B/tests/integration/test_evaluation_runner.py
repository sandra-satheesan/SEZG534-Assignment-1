from __future__ import annotations

import json
from pathlib import Path

from app.evaluation.cases import EvaluationCase, EvaluationCaseSet
from app.evaluation.reporting import list_reports
from app.evaluation.runner import EvaluationRunner


class FakeProvider:
    def __init__(self, response: dict | None = None) -> None:
        self.calls: list[str] = []
        self.response = response or {
            "schema_version": "1.0",
            "status": "needs_clarification",
            "reminder": {
                "title": None,
                "due": None,
                "recurrence": None,
                "follow_ups": [],
                "additional_instructions": [],
            },
            "clarification_questions": ["Which date and time should I use?"],
            "unresolved_fields": ["due"],
            "issues": [],
        }

    async def generate(self, prompt: str) -> str:
        self.calls.append(prompt)
        return json.dumps(self.response)


def make_case_set() -> EvaluationCaseSet:
    rubric = [
        "intent_preservation",
        "temporal_context",
        "recurrence_follow_up_fidelity",
        "clarification_or_rejection",
    ]
    return EvaluationCaseSet(
        version="1",
        cases=[
            EvaluationCase(
                case_id="NLR-001",
                text="Remind me to call my manager.",
                reference_context=None,
                categories=["incomplete"],
                expected_status="needs_clarification",
                required_facts=["clarification"],
                forbidden_facts=["ready"],
                rubric_dimensions=rubric,
                expected_behavior="asks for missing date and time",
            ),
            EvaluationCase(
                case_id="NLR-002",
                text="Remind me to submit the report tomorrow at 10 AM.",
                reference_context={
                    "reference_instant": "2026-11-03T09:00:00+05:30",
                    "time_zone": "Asia/Kolkata",
                },
                categories=["clear_request", "relative_timing"],
                expected_status="ready",
                required_facts=["submit the report", "10:00"],
                forbidden_facts=["schedule a notification"],
                rubric_dimensions=rubric,
                expected_behavior="resolves tomorrow using the supplied context",
            ),
        ],
    )


async def test_runner_executes_three_runs_per_case_and_writes_report(
    tmp_path: Path,
) -> None:
    providers: list[FakeProvider] = []

    def provider_factory() -> FakeProvider:
        provider = FakeProvider()
        providers.append(provider)
        return provider

    runner = EvaluationRunner(
        case_set=make_case_set(),
        provider_factory=provider_factory,
        results_dir=tmp_path,
        runs_per_case=3,
    )

    report = await runner.run()

    assert len(providers) == 6
    assert all(len(provider.calls) == 1 for provider in providers)
    assert report.run_count == 3
    assert report.case_count == 2
    assert report.report_path.exists()
    assert all(len(result.runs) == 3 for result in report.case_results.values())


async def test_complete_rerun_uses_same_case_set_and_preserves_prior_report(
    tmp_path: Path,
) -> None:
    providers: list[FakeProvider] = []

    def provider_factory() -> FakeProvider:
        provider = FakeProvider()
        providers.append(provider)
        return provider

    runner = EvaluationRunner(
        case_set=make_case_set(),
        provider_factory=provider_factory,
        results_dir=tmp_path,
        runs_per_case=3,
    )

    first = await runner.run()
    second = await runner.run()

    assert first.case_set_digest == second.case_set_digest
    assert first.evaluation_config_digest == second.evaluation_config_digest
    assert first.report_path != second.report_path
    assert len(list_reports(tmp_path)) == 2
    assert len(providers) == 12


async def test_runner_retains_explicit_failure_evidence(tmp_path: Path) -> None:
    class FailingProvider(FakeProvider):
        async def generate(self, prompt: str) -> str:
            self.calls.append(prompt)
            return '{"not": "an interpretation"}'

    report = await EvaluationRunner(
        case_set=make_case_set(),
        provider_factory=FailingProvider,
        results_dir=tmp_path,
        runs_per_case=3,
    ).run()

    for case_result in report.case_results.values():
        assert all(run.schema_valid is False for run in case_result.runs)
        assert all(run.failure_code for run in case_result.runs)
        assert all(run.failed_properties for run in case_result.runs)
        assert all(
            "schema_correctness" in run.failed_properties
            for run in case_result.runs
        )
    assert report.acceptance_passed is False
