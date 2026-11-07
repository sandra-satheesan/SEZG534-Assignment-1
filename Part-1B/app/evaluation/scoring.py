"""Deterministic evaluation metrics and acceptance gates."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

AGGREGATE_WEIGHTS = {
    "schema_correctness": 0.25,
    "invariant_correctness": 0.25,
    "semantic_quality": 0.30,
    "reliability": 0.20,
}
SEMANTIC_DIMENSIONS = (
    "intent_preservation",
    "temporal_context",
    "recurrence_follow_up_fidelity",
    "clarification_or_rejection",
)


@dataclass(frozen=True, slots=True)
class EvaluationMetrics:
    schema_correctness: float
    invariant_correctness: float
    semantic_quality: float
    reliability: float


@dataclass(frozen=True, slots=True)
class AcceptanceThresholds:
    schema_correctness: float = 1.0
    invariant_correctness: float = 1.0
    semantic_quality: float = 0.85
    reliability: float = 0.90
    aggregate: float = 0.90

    def failed_gates(self, metrics: EvaluationMetrics) -> list[str]:
        failures: list[str] = []
        for name in (
            "schema_correctness",
            "invariant_correctness",
            "semantic_quality",
            "reliability",
        ):
            if getattr(metrics, name) < getattr(self, name):
                failures.append(name)
        if aggregate_score(metrics) < self.aggregate:
            failures.append("aggregate")
        return failures

    def is_accepted(self, metrics: EvaluationMetrics) -> bool:
        return not self.failed_gates(metrics)


def _mean(values: list[float]) -> float:
    if not values:
        raise ValueError("At least one evaluation run is required.")
    return sum(values) / len(values)


def score_semantic_dimensions(scores: Mapping[str, float]) -> float:
    if set(scores) != set(SEMANTIC_DIMENSIONS):
        raise ValueError("All semantic dimensions must be provided.")
    if any(value < 0 or value > 1 for value in scores.values()):
        raise ValueError("Semantic scores must be between 0 and 1.")
    return _mean([scores[dimension] for dimension in SEMANTIC_DIMENSIONS])


def score_case_runs(
    *,
    schema_results: list[bool],
    invariant_results: list[bool],
    semantic_scores: list[float],
    expected_behavior_results: list[bool],
) -> EvaluationMetrics:
    lengths = {
        len(schema_results),
        len(invariant_results),
        len(semantic_scores),
        len(expected_behavior_results),
    }
    if len(lengths) != 1:
        raise ValueError("All evaluation inputs must have the same number of runs.")
    if any(value < 0 or value > 1 for value in semantic_scores):
        raise ValueError("Semantic scores must be between 0 and 1.")
    return EvaluationMetrics(
        schema_correctness=_mean([float(value) for value in schema_results]),
        invariant_correctness=_mean([float(value) for value in invariant_results]),
        semantic_quality=_mean(semantic_scores),
        reliability=_mean([float(value) for value in expected_behavior_results]),
    )


def aggregate_score(metrics: EvaluationMetrics) -> float:
    total = 0.0
    for name, weight in AGGREGATE_WEIGHTS.items():
        total += getattr(metrics, name) * weight
    return total
