"""Strict request schemas for the versioned interpretation API."""

from __future__ import annotations

import re
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

RFC3339_OFFSET_DATETIME = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ReferenceContext(StrictModel):
    reference_instant: AwareDatetime = Field(strict=False)
    time_zone: Annotated[str, Field(min_length=1)]

    @field_validator("reference_instant", mode="before")
    @classmethod
    def require_rfc3339_offset(cls, value: object) -> object:
        if not isinstance(value, str) or RFC3339_OFFSET_DATETIME.fullmatch(value) is None:
            raise ValueError("reference_instant must be RFC 3339 with an explicit UTC offset.")
        return value

    @field_validator("time_zone")
    @classmethod
    def require_iana_time_zone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ValueError, ZoneInfoNotFoundError) as exc:
            raise ValueError("time_zone must be a recognized IANA time-zone identifier.") from exc
        return value


class InterpretationRequest(StrictModel):
    text: Annotated[str, Field(min_length=1, max_length=4000)]
    reference_context: ReferenceContext | None

    @field_validator("text", mode="before")
    @classmethod
    def trim_and_bound_text(cls, value: object) -> object:
        if isinstance(value, str):
            if len(value) > 4000:
                raise ValueError("text must be at most 4000 characters.")
            return value.strip()
        return value