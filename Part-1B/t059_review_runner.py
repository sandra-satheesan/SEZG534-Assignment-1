"""Run exactly one live Groq interpretation for each T059 scenario.

This is a focused usability-review harness, not part of the 15-case evaluator.
It performs no requests when imported; execute it explicitly.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.api.errors import (
    ApplicationError,
    ProviderOutputError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.core.settings import Settings
from app.prompts.reminder_interpretation import build_interpretation_prompt
from app.providers.groq import GroqProvider
from app.schemas.requests import InterpretationRequest
from app.schemas.responses import InterpretationResult
from app.services.invariants import validate_interpretation_result
from pydantic import ValidationError

OUTPUT_PATH = Path("eval/t059-review-evidence.json")

REFERENCE_CONTEXT = {
    "reference_instant": "2026-11-03T09:00:00+05:30",
    "time_zone": "Asia/Kolkata",
}

SCENARIOS = (
    ("NLR-001", "Remind me to call Rahul tomorrow at 10 AM.", REFERENCE_CONTEXT),
    (
        "NLR-002",
        "Remind me to submit my assignment next Monday evening.",
        REFERENCE_CONTEXT,
    ),
    (
        "NLR-003",
        "Remind me to take medicine every day at 8 AM.",
        REFERENCE_CONTEXT,
    ),
    (
        "NLR-004",
        "Remind me to pay the electricity bill in two days. "
        "If I do not complete it, remind me again after 30 minutes.",
        REFERENCE_CONTEXT,
    ),
    ("NLR-005", "Remind me to call my manager.", None),
    (
        "NLR-009",
        "Remind me tomorrow at 8 AM and tomorrow at 9 AM.",
        REFERENCE_CONTEXT,
    ),
)


def _provider_failure(exc: Exception) -> dict[str, str]:
    if isinstance(exc, ProviderTimeoutError):
        code = "provider_timeout"
        message = exc.public_message
    elif isinstance(exc, ProviderUnavailableError):
        code = "provider_unavailable"
        message = exc.public_message
    elif isinstance(exc, ProviderOutputError):
        code = "provider_error"
        message = exc.public_message
    elif isinstance(exc, ApplicationError):
        code = exc.error_code
        message = exc.public_message
    else:
        code = "unexpected_error"
        message = "The application raised an unexpected error."
    return {"code": code, "message": message}


async def run(
    scenario_ids: set[str] | None = None,
    output_path: Path = OUTPUT_PATH,
) -> None:
    settings = Settings.from_environment()
    if settings.groq_api_key is None:
        raise SystemExit("GROQ_API_KEY is required; no request was made.")

    provider = GroqProvider(settings)
    evidence: list[dict[str, Any]] = []

    selected_scenarios = tuple(
        scenario for scenario in SCENARIOS
        if scenario_ids is None or scenario[0] in scenario_ids
    )
    if not selected_scenarios:
        raise SystemExit("At least one valid scenario ID is required; no request was made.")

    for scenario_id, text, context in selected_scenarios:
        request = InterpretationRequest(text=text, reference_context=context)
        record: dict[str, Any] = {
            "scenario_id": scenario_id,
            "request": request.model_dump(mode="json"),
            "provider": "GroqProvider",
            "raw_response": None,
            "validated_result": None,
            "validation": {"status": "not_attempted"},
            "provider_error": None,
        }
        try:
            raw_response = await provider.generate(build_interpretation_prompt(request))
        except (ApplicationError, TimeoutError) as exc:
            record["provider_error"] = _provider_failure(exc)
            record["validation"] = {"status": "not_available"}
        else:
            record["raw_response"] = raw_response
            try:
                result = InterpretationResult.model_validate_json(raw_response)
                validate_interpretation_result(request, result)
            except (ProviderOutputError, ValidationError) as exc:
                record["validation"] = {
                    "status": "invalid",
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
            else:
                record["validated_result"] = result.model_dump(mode="json")
                record["validation"] = {"status": "valid"}
        evidence.append(record)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "provider_model": settings.groq_model,
        "request_count": len(selected_scenarios),
        "scenarios": evidence,
    }
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"Saved {len(evidence)} scenario results to {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run selected T059 Groq scenarios once.")
    parser.add_argument(
        "--scenario-ids", nargs="+", choices=[scenario[0] for scenario in SCENARIOS]
    )
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    asyncio.run(run(set(args.scenario_ids) if args.scenario_ids else None, args.output))
