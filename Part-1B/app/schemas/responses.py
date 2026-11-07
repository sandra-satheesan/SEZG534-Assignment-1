"""Strict result and error-envelope schemas matching the OpenAPI contract."""

from __future__ import annotations

from datetime import date, time
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class DueTime(StrictModel):
    local_date: date | None
    local_time: time | None
    time_of_day: Literal["morning", "afternoon", "evening", "night"] | None
    time_zone: Annotated[str, Field(min_length=1)] | None
    precision: Literal["exact", "broad", "unresolved"]


class Recurrence(StrictModel):
    frequency: Literal["daily", "weekly", "monthly", "yearly"]
    interval: Annotated[int, Field(ge=1)]
    weekdays: list[Literal["MO", "TU", "WE", "TH", "FR", "SA", "SU"]]
    ends_on: date | None
    occurrence_count: Annotated[int, Field(ge=1)] | None


class FollowUpInstruction(StrictModel):
    kind: Literal["snooze", "reschedule", "conditional_follow_up"]
    delay_minutes: Annotated[int, Field(ge=1)] | None
    condition: Literal["if_incomplete"] | None
    target: str | None


class InterpretationIssue(StrictModel):
    code: Annotated[str, Field(min_length=1)]
    field: str | None
    message: Annotated[str, Field(min_length=1)]


class ReminderDraft(StrictModel):
    title: Annotated[str, Field(min_length=1)] | None
    due: DueTime | None
    recurrence: Recurrence | None
    follow_ups: list[FollowUpInstruction]
    additional_instructions: list[str]


class InterpretationResult(StrictModel):
    schema_version: Literal["1.0"]
    status: Literal["ready", "needs_clarification", "invalid", "unsupported"]
    reminder: ReminderDraft | None
    clarification_questions: list[Annotated[str, Field(min_length=1)]]
    unresolved_fields: list[str]
    issues: list[InterpretationIssue]


class ErrorDetail(StrictModel):
    code: str
    message: str


class ErrorResponse(StrictModel):
    error: ErrorDetail