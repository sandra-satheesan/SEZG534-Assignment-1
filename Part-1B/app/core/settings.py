"""Typed environment-backed application settings."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import cast

from fastapi import Request

DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"
DEFAULT_PROVIDER_TIMEOUT_SECONDS = 30.0
MAX_PROVIDER_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True, slots=True)
class Settings:
    groq_api_key: str | None = field(default=None, repr=False)
    groq_model: str = DEFAULT_GROQ_MODEL
    provider_timeout_seconds: float = DEFAULT_PROVIDER_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        api_key = self.groq_api_key
        if api_key is not None:
            normalized_key = api_key.strip()
            object.__setattr__(self, "groq_api_key", normalized_key or None)

        model = self.groq_model.strip()
        if not model:
            raise ValueError("GROQ_MODEL must not be empty.")
        object.__setattr__(self, "groq_model", model)

        timeout = self.provider_timeout_seconds
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout)
            or timeout <= 0
            or timeout > MAX_PROVIDER_TIMEOUT_SECONDS
        ):
            raise ValueError("GROQ_TIMEOUT_SECONDS must be greater than 0 and at most 30.")
        object.__setattr__(self, "provider_timeout_seconds", float(timeout))

    @classmethod
    def from_environment(cls) -> Settings:
        raw_timeout = os.environ.get(
            "GROQ_TIMEOUT_SECONDS", str(DEFAULT_PROVIDER_TIMEOUT_SECONDS)
        )
        try:
            timeout = float(raw_timeout)
        except ValueError as exc:
            raise ValueError("GROQ_TIMEOUT_SECONDS must be a number.") from exc

        return cls(
            groq_api_key=os.environ.get("GROQ_API_KEY"),
            groq_model=os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL),
            provider_timeout_seconds=timeout,
        )


def get_settings(request: Request) -> Settings:
    """Return app-scoped settings without re-reading environment state per request."""
    return cast(Settings, request.app.state.settings)