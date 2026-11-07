from __future__ import annotations

from datetime import date

import pytest
from app.evaluation.review import HumanReviewRecord, validate_human_review


def valid_review(**overrides: object) -> HumanReviewRecord:
    values: dict[str, object] = {
        "reviewer": "reviewer@example.test",
        "review_date": date(2026, 11, 7),
        "run_id": "run-20261107-001",
        "case_set_version": "1",
        "decision": "approved",
        "findings": ["All hard gates passed."],
        "limitations": ["Semantic scores were manually anchored."],
        "evidence_references": {
            "specification": ["spec.md"],
            "aggregate_metrics": ["eval/results/run-20261107-001.json"],
            "per_case_results": ["eval/results/run-20261107-001.json"],
            "failures": ["eval/results/run-20261107-001.json"],
            "limitations": ["eval/results/run-20261107-001.json"],
        },
    }
    values.update(overrides)
    return HumanReviewRecord.model_validate(values)


def test_human_review_requires_explicit_approval_or_rejection() -> None:
    assert validate_human_review(valid_review()).decision == "approved"
    assert validate_human_review(valid_review(decision="rejected")).decision == "rejected"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("reviewer", ""),
        ("run_id", ""),
        ("case_set_version", ""),
        ("findings", []),
        ("limitations", []),
    ],
)
def test_human_review_rejects_missing_required_evidence(field: str, value: object) -> None:
    with pytest.raises(ValueError):
        validate_human_review(valid_review(**{field: value}))


def test_human_review_requires_a_real_review_date() -> None:
    with pytest.raises(ValueError, match="review date"):
        validate_human_review(valid_review(review_date=None))


def test_automated_pass_does_not_create_human_acceptance() -> None:
    assert validate_human_review(valid_review(decision="approved")).is_explicit is True
    with pytest.raises(ValueError, match="decision"):
        validate_human_review(
            valid_review(decision=None, findings=["Automated thresholds passed."])
        )


@pytest.mark.parametrize(
    "evidence_key",
    ["specification", "aggregate_metrics", "per_case_results", "failures", "limitations"],
)
def test_human_review_requires_evidence_references_for_fr022(
    evidence_key: str,
) -> None:
    evidence = valid_review().evidence_references.model_dump()
    evidence[evidence_key] = []

    with pytest.raises(ValueError, match="evidence"):
        validate_human_review(valid_review(evidence_references=evidence))
