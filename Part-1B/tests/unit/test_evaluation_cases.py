from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from app.evaluation.cases import (
    REQUIRED_CATEGORIES,
    EvaluationCase,
    load_case_set,
    validate_case_set,
)

CASE_FILE = (
    Path(__file__).resolve().parents[2] / "eval" / "cases" / "reminder-cases.v1.jsonl"
)

REQUIRED_FR014_CATEGORIES = {
    "clear_request",
    "relative_timing",
    "recurrence",
    "follow_up",
    "ambiguous",
    "incomplete",
    "invalid",
    "contradictory",
    "unsupported",
}


def test_version_one_corpus_has_minimum_size_and_required_categories() -> None:
    case_set = load_case_set(CASE_FILE)

    assert case_set.version == "1"
    assert len(case_set.cases) >= 15
    assert REQUIRED_CATEGORIES == REQUIRED_FR014_CATEGORIES
    assert REQUIRED_FR014_CATEGORIES <= {
        category for case in case_set.cases for category in case.categories
    }


def test_case_ids_are_stable_and_unique() -> None:
    case_set = load_case_set(CASE_FILE)
    ids = [case.case_id for case in case_set.cases]

    assert ids == [f"NLR-{number:03d}" for number in range(1, len(ids) + 1)]
    assert len(ids) == len(set(ids))


def test_cases_have_complete_reproducibility_and_semantic_expectations() -> None:
    case_set = load_case_set(CASE_FILE)

    for case in case_set.cases:
        if case.reference_context is not None:
            assert case.reference_context.time_zone
            assert case.reference_context.reference_instant.tzinfo is not None
        assert case.required_facts
        assert case.forbidden_facts is not None
        assert set(case.rubric_dimensions) == {
            "intent_preservation",
            "temporal_context",
            "recurrence_follow_up_fidelity",
            "clarification_or_rejection",
        }
        assert case.expected_status in {
            "ready",
            "needs_clarification",
            "invalid",
            "unsupported",
        }
        assert case.expected_behavior


def test_case_set_rejects_duplicate_ids_and_missing_categories() -> None:
    case = EvaluationCase(
        case_id="NLR-001",
        text="Remind me to call Rahul tomorrow at 10 AM.",
        reference_context=None,
        categories=[],
        expected_status="ready",
        required_facts=["call Rahul"],
        forbidden_facts=["schedule a notification"],
        rubric_dimensions=["intent_preservation"],
    )

    with pytest.raises(ValueError, match="categories"):
        validate_case_set([case, case])


def test_case_set_rejects_naive_reference_instants() -> None:
    case = EvaluationCase(
        case_id="NLR-001",
        text="Remind me tomorrow at 10 AM.",
        reference_context={
            "reference_instant": datetime(2026, 11, 3, 9, 0),
            "time_zone": "Asia/Kolkata",
        },
        categories=["relative_timing"],
        expected_status="ready",
        required_facts=["10:00"],
        forbidden_facts=[],
        rubric_dimensions=["timing_context"],
    )

    with pytest.raises(ValueError, match="reference"):
        validate_case_set([case])
