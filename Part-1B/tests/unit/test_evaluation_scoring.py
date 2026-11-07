from __future__ import annotations

import pytest
from app.evaluation.scoring import (
    AGGREGATE_WEIGHTS,
    SEMANTIC_DIMENSIONS,
    AcceptanceThresholds,
    EvaluationMetrics,
    aggregate_score,
    score_case_runs,
    score_semantic_dimensions,
)


def test_aggregate_weights_are_named_and_sum_to_one() -> None:
    assert AGGREGATE_WEIGHTS == {
        "schema_correctness": 0.25,
        "invariant_correctness": 0.25,
        "semantic_quality": 0.30,
        "reliability": 0.20,
    }
    assert sum(AGGREGATE_WEIGHTS.values()) == pytest.approx(1.0)


def test_scoring_reports_schema_invariant_semantic_and_reliability_percentages() -> None:
    metrics = score_case_runs(
        schema_results=[True, True, True],
        invariant_results=[True, True, True],
        semantic_scores=[1.0, 0.8, 0.9],
        expected_behavior_results=[True, True, False],
    )

    assert metrics == EvaluationMetrics(
        schema_correctness=1.0,
        invariant_correctness=1.0,
        semantic_quality=pytest.approx(0.9),
        reliability=pytest.approx(2 / 3),
    )


def test_aggregate_score_uses_documented_weighted_components() -> None:
    metrics = EvaluationMetrics(
        schema_correctness=1.0,
        invariant_correctness=1.0,
        semantic_quality=0.8,
        reliability=0.9,
    )

    expected = (
        metrics.schema_correctness * AGGREGATE_WEIGHTS["schema_correctness"]
        + metrics.invariant_correctness * AGGREGATE_WEIGHTS["invariant_correctness"]
        + metrics.semantic_quality * AGGREGATE_WEIGHTS["semantic_quality"]
        + metrics.reliability * AGGREGATE_WEIGHTS["reliability"]
    )
    assert aggregate_score(metrics) == pytest.approx(expected)


def test_semantic_quality_scores_each_fr018_dimension_independently() -> None:
    scores = {
        "intent_preservation": 1.0,
        "temporal_context": 0.8,
        "recurrence_follow_up_fidelity": 0.6,
        "clarification_or_rejection": 0.4,
    }

    assert SEMANTIC_DIMENSIONS == tuple(scores)
    assert score_semantic_dimensions(scores) == pytest.approx(0.7)


def test_semantic_quality_rejects_missing_or_out_of_range_dimensions() -> None:
    with pytest.raises(ValueError, match="semantic dimensions"):
        score_semantic_dimensions({"intent_preservation": 1.0})

    with pytest.raises(ValueError, match="between 0 and 1"):
        score_semantic_dimensions(
            {
                "intent_preservation": 1.0,
                "temporal_context": 1.0,
                "recurrence_follow_up_fidelity": -0.1,
                "clarification_or_rejection": 1.0,
            }
        )


@pytest.mark.parametrize(
    ("metrics", "expected_gate"),
    [
        (
            EvaluationMetrics(0.99, 1.0, 1.0, 1.0),
            "schema_correctness",
        ),
        (
            EvaluationMetrics(1.0, 0.99, 1.0, 1.0),
            "invariant_correctness",
        ),
        (
            EvaluationMetrics(1.0, 1.0, 0.84, 1.0),
            "semantic_quality",
        ),
        (
            EvaluationMetrics(1.0, 1.0, 1.0, 0.89),
            "reliability",
        ),
    ],
)
def test_each_hard_gate_is_independent(
    metrics: EvaluationMetrics, expected_gate: str
) -> None:
    thresholds = AcceptanceThresholds()

    assert thresholds.failed_gates(metrics) == [expected_gate]


def test_aggregate_pass_cannot_hide_a_failed_hard_gate() -> None:
    metrics = EvaluationMetrics(
        schema_correctness=0.99,
        invariant_correctness=1.0,
        semantic_quality=1.0,
        reliability=1.0,
    )

    assert aggregate_score(metrics) >= AcceptanceThresholds().aggregate
    assert AcceptanceThresholds().is_accepted(metrics) is False


def test_scoring_rejects_mismatched_run_lengths() -> None:
    with pytest.raises(ValueError, match="same number of runs"):
        score_case_runs(
            schema_results=[True, True],
            invariant_results=[True],
            semantic_scores=[1.0, 1.0],
            expected_behavior_results=[True, True],
        )


def test_semantic_scores_are_bounded() -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        score_case_runs(
            schema_results=[True],
            invariant_results=[True],
            semantic_scores=[1.1],
            expected_behavior_results=[True],
        )
