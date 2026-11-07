"""Structured human-review records for evaluation acceptance."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EvidenceReferences(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    specification: list[str] = Field(min_length=1)
    aggregate_metrics: list[str] = Field(min_length=1)
    per_case_results: list[str] = Field(min_length=1)
    failures: list[str] = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)


class HumanReviewRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    reviewer: str = Field(min_length=1)
    review_date: date | None
    run_id: str = Field(min_length=1)
    case_set_version: str = Field(min_length=1)
    decision: str | None
    findings: list[str] = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)
    evidence_references: EvidenceReferences

    @property
    def is_explicit(self) -> bool:
        return self.decision in {"approved", "rejected"}

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, value: str | None) -> str | None:
        if value not in {"approved", "rejected", None}:
            raise ValueError("decision must be approved or rejected.")
        return value


def validate_human_review(record: HumanReviewRecord) -> HumanReviewRecord:
    if not record.is_explicit:
        raise ValueError("An explicit approved or rejected decision is required.")
    if not record.review_date:
        raise ValueError("A review date is required.")
    return record
