"""Versioned evaluation-case models and validation."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field

REQUIRED_CATEGORIES = {
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
SEMANTIC_DIMENSIONS = {
    "intent_preservation",
    "temporal_context",
    "recurrence_follow_up_fidelity",
    "clarification_or_rejection",
}
EXPECTED_STATUSES = {"ready", "needs_clarification", "invalid", "unsupported"}


class EvaluationReferenceContext(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    reference_instant: datetime = Field(strict=False)
    time_zone: str = Field(min_length=1)


class EvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    case_id: str = Field(pattern=r"^NLR-\d{3}$")
    text: str = Field(min_length=1, max_length=4000)
    reference_context: EvaluationReferenceContext | None
    categories: list[str]
    expected_status: Literal["ready", "needs_clarification", "invalid", "unsupported"]
    required_facts: list[str] = Field(min_length=1)
    forbidden_facts: list[str]
    rubric_dimensions: list[str] = Field(min_length=1)
    expected_behavior: str = Field(default="unspecified", min_length=1)


class EvaluationCaseSet(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    version: str = Field(min_length=1)
    cases: list[EvaluationCase] = Field(min_length=1)

    def digest(self) -> str:
        payload = self.model_dump(mode="json")
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


def validate_case_set(cases: list[EvaluationCase]) -> None:
    if not cases:
        raise ValueError("The evaluation case set must not be empty.")
    for case in cases:
        if not case.categories:
            raise ValueError(f"Case {case.case_id} must declare categories.")
        if case.reference_context is not None:
            if case.reference_context.reference_instant.tzinfo is None:
                raise ValueError(f"Case {case.case_id} reference instant must include a timezone.")
            try:
                ZoneInfo(case.reference_context.time_zone)
            except (ValueError, ZoneInfoNotFoundError) as exc:
                raise ValueError(f"Case {case.case_id} has an invalid IANA timezone.") from exc
    ids = [case.case_id for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Evaluation case IDs must be unique.")
    expected_ids = [f"NLR-{number:03d}" for number in range(1, len(cases) + 1)]
    if ids != expected_ids:
        raise ValueError("Evaluation case IDs must be stable and sequential.")
    categories = {category for case in cases for category in case.categories}
    missing_categories = REQUIRED_CATEGORIES - categories
    if missing_categories:
        raise ValueError(f"Missing required evaluation categories: {sorted(missing_categories)}")

    for case in cases:
        if set(case.categories) - REQUIRED_CATEGORIES:
            raise ValueError(f"Case {case.case_id} declares an unknown category.")
        if case.expected_status not in EXPECTED_STATUSES:
            raise ValueError(f"Case {case.case_id} declares an invalid expected status.")
        if set(case.rubric_dimensions) != SEMANTIC_DIMENSIONS:
            raise ValueError(
                f"Case {case.case_id} must define all semantic rubric dimensions."
            )
    if len(cases) < 15:
        raise ValueError("The evaluation case set must contain at least 15 cases.")


def load_case_set(path: Path) -> EvaluationCaseSet:
    records: list[dict[str, object]] = []
    try:
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON on line {line_number}.") from exc
                if not isinstance(value, dict):
                    raise ValueError(f"Case on line {line_number} must be a JSON object.")
                records.append(value)
    except OSError as exc:
        raise ValueError(f"Unable to read evaluation cases from {path}.") from exc

    case_set = EvaluationCaseSet.model_validate(
        {"version": "1", "cases": records}
    )
    validate_case_set(case_set.cases)
    return case_set
