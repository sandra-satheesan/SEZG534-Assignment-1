"""Diagnose one T059 Groq provider request without recording sensitive data."""

from __future__ import annotations

import asyncio
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.api.errors import ApplicationError
from app.core.settings import Settings
from app.prompts.reminder_interpretation import build_interpretation_prompt
from app.providers.groq import GroqProvider
from app.schemas.requests import InterpretationRequest
from app.schemas.responses import InterpretationResult
from app.services.invariants import validate_interpretation_result
from pydantic import ValidationError

OUTPUT_PATH = Path("eval/t059-diagnostic-retry.json")
TEXT = "Remind me to call Rahul tomorrow at 10 AM."
REFERENCE_CONTEXT = {
    "reference_instant": "2026-11-03T09:00:00+05:30",
    "time_zone": "Asia/Kolkata",
}


def _sanitize_message(message: object, sensitive_values: set[str]) -> str | None:
    if not isinstance(message, str) or not message:
        return None
    sanitized = message
    for value in sorted((value for value in sensitive_values if value), key=len, reverse=True):
        sanitized = sanitized.replace(value, "[REDACTED]")
    sanitized = re.sub(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [REDACTED]", sanitized)
    sanitized = re.sub(
        r"(?i)(api[_ -]?key|authorization|x-api-key)\s*[:=]\s*(['\"]?)[^,\s'\"]+\2",
        r"\1=[REDACTED]",
        sanitized,
    )
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    return sanitized[:500] or None


def _cause_metadata(exc: BaseException, sensitive_values: set[str]) -> list[dict[str, Any]]:
    chain: list[dict[str, Any]] = []
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        status_code = getattr(current, "status_code", None)
        status_value = getattr(current, "code", None)
        if not isinstance(status_code, int):
            status_code = None
        if not isinstance(status_value, str):
            status_value = None
        chain.append(
            {
                "exception_class": type(current).__name__,
                "api_status_code": status_code,
                "api_status": status_value,
                "sanitized_message": _sanitize_message(str(current), sensitive_values),
            }
        )
        current = current.__cause__ or current.__context__
    return chain


async def run() -> None:
    settings = Settings.from_environment()
    if settings.groq_api_key is None:
        raise SystemExit("GROQ_API_KEY is required; no request was made.")

    request = InterpretationRequest(text=TEXT, reference_context=REFERENCE_CONTEXT)
    provider = GroqProvider(settings)
    sensitive_values = {TEXT, *REFERENCE_CONTEXT.values()}
    evidence: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "scenario_id": "NLR-001",
        "provider": "GroqProvider",
        "provider_model": settings.groq_model,
        "request_count": 1,
        "provider_outcome": None,
        "exception_chain": [],
        "validation": {"status": "not_attempted"},
    }

    try:
        output = await provider.generate(build_interpretation_prompt(request))
    except Exception as exc:
        evidence["provider_outcome"] = {
            "public_exception_class": type(exc).__name__,
            "public_error_code": getattr(exc, "error_code", None),
            "public_message_category": (
                "provider_output_error"
                if isinstance(exc, ApplicationError)
                else "unexpected_provider_error"
            ),
        }
        evidence["exception_chain"] = _cause_metadata(exc, sensitive_values)
        evidence["validation"] = {"status": "not_available"}
    else:
        try:
            result = InterpretationResult.model_validate_json(output)
            validate_interpretation_result(request, result)
        except (ValidationError, ApplicationError) as exc:
            evidence["provider_outcome"] = {"status": "response_received"}
            evidence["exception_chain"] = _cause_metadata(exc, sensitive_values)
            evidence["validation"] = {
                "status": "invalid",
                "exception_class": type(exc).__name__,
            }
        else:
            evidence["provider_outcome"] = {"status": "response_received"}
            evidence["validation"] = {"status": "valid"}

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"Saved diagnostic evidence to {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(run())
