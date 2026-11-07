import json

import pytest
from app.schemas.requests import InterpretationRequest
from app.schemas.responses import ErrorResponse, InterpretationResult
from pydantic import ValidationError


def request_payload(text: str = "Remind me to call Rahul tomorrow at 10 AM.") -> dict:
    return {
        "text": text,
        "reference_context": {
            "reference_instant": "2026-11-03T09:00:00+05:30",
            "time_zone": "Asia/Kolkata",
        },
    }


def test_request_trims_text_and_accepts_explicit_reference_context() -> None:
    payload = request_payload("  Remind me to call Rahul tomorrow at 10 AM.  ")

    request = InterpretationRequest.model_validate_json(json.dumps(payload))

    assert request.text == "Remind me to call Rahul tomorrow at 10 AM."
    assert request.reference_context is not None
    assert request.reference_context.reference_instant.utcoffset() is not None


def test_request_accepts_explicit_null_context() -> None:
    request = InterpretationRequest.model_validate_json(
        json.dumps({"text": "Remind me to call Rahul.", "reference_context": None})
    )

    assert request.reference_context is None


@pytest.mark.parametrize("text", ["", "   ", "x" * 4001, " " + ("x" * 4000) + " "])
def test_request_rejects_empty_or_overlong_text(text: str) -> None:
    with pytest.raises(ValidationError):
        InterpretationRequest.model_validate_json(
            json.dumps({"text": text, "reference_context": None})
        )


def test_request_accepts_text_at_openapi_length_limit() -> None:
    request = InterpretationRequest.model_validate_json(
        json.dumps({"text": "x" * 4000, "reference_context": None})
    )

    assert len(request.text) == 4000


def test_request_requires_reference_context_property_even_when_nullable() -> None:
    with pytest.raises(ValidationError):
        InterpretationRequest.model_validate_json(json.dumps({"text": "Call Rahul."}))


def test_request_rejects_unknown_fields() -> None:
    payload = request_payload()
    payload["unexpected"] = True

    with pytest.raises(ValidationError):
        InterpretationRequest.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize(
    "reference_instant",
    ["2026-11-03T09:00:00", "not-a-date", "2026-02-30T09:00:00+00:00"],
)
def test_reference_instant_requires_valid_rfc3339_offset(reference_instant: str) -> None:
    payload = request_payload()
    payload["reference_context"]["reference_instant"] = reference_instant

    with pytest.raises(ValidationError):
        InterpretationRequest.model_validate_json(json.dumps(payload))


def test_reference_context_rejects_unknown_time_zone() -> None:
    payload = request_payload()
    payload["reference_context"]["time_zone"] = "Mars/Olympus_Mons"

    with pytest.raises(ValidationError):
        InterpretationRequest.model_validate_json(json.dumps(payload))


def test_response_models_are_strict_and_validate_contract_values() -> None:
    result_payload = {
        "schema_version": "1.0",
        "status": "ready",
        "reminder": {
            "title": "call Rahul",
            "due": {
                "local_date": "2026-11-04",
                "local_time": "10:00",
                "time_of_day": None,
                "time_zone": "Asia/Kolkata",
                "precision": "exact",
            },
            "recurrence": None,
            "follow_ups": [],
            "additional_instructions": [],
        },
        "clarification_questions": [],
        "unresolved_fields": [],
        "issues": [],
    }

    result = InterpretationResult.model_validate_json(json.dumps(result_payload))

    assert result.status == "ready"
    assert result.reminder is not None
    assert result.reminder.due is not None
    assert result.reminder.due.local_time.isoformat(timespec="minutes") == "10:00"


def test_response_models_reject_coercion_and_unknown_fields() -> None:
    payload = {
        "schema_version": "1.0",
        "status": "ready",
        "reminder": {
            "title": "call Rahul",
            "due": None,
            "recurrence": {
                "frequency": "daily",
                "interval": "1",
                "weekdays": [],
                "ends_on": None,
                "occurrence_count": None,
            },
            "follow_ups": [],
            "additional_instructions": [],
        },
        "clarification_questions": [],
        "unresolved_fields": [],
        "issues": [],
    }

    with pytest.raises(ValidationError):
        InterpretationResult.model_validate_json(json.dumps(payload))

    payload["reminder"]["recurrence"]["interval"] = 1
    payload["unexpected"] = "extra"
    with pytest.raises(ValidationError):
        InterpretationResult.model_validate_json(json.dumps(payload))


def test_error_response_has_strict_documented_envelope() -> None:
    error = ErrorResponse.model_validate_json(
        '{"error":{"code":"invalid_request","message":"Request validation failed."}}'
    )

    assert error.error.code == "invalid_request"
    with pytest.raises(ValidationError):
        ErrorResponse.model_validate_json(
            '{"error":{"code":"invalid_request","message":"bad","detail":"secret"}}'
        )