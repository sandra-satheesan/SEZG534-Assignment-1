import json

import pytest
from app.api.errors import ProviderOutputError, ProviderTimeoutError, ProviderUnavailableError
from app.main import create_app
from app.schemas.responses import ErrorResponse, InterpretationResult
from fastapi.testclient import TestClient


class FakeProvider:
    async def generate(self, prompt: str) -> str:
        return json.dumps(
            {
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
        )


class ClarifyingProvider:
    async def generate(self, prompt: str) -> str:
        return json.dumps(
            {
                "schema_version": "1.0",
                "status": "needs_clarification",
                "reminder": {
                    "title": "call my manager",
                    "due": None,
                    "recurrence": None,
                    "follow_ups": [],
                    "additional_instructions": [],
                },
                "clarification_questions": ["What date and time should I use?"],
                "unresolved_fields": ["due.local_date", "due.local_time"],
                "issues": [],
            }
        )


class RecurrenceProvider:
    async def generate(self, prompt: str) -> str:
        return json.dumps(
            {
                "schema_version": "1.0",
                "status": "ready",
                "reminder": {
                    "title": "take medicine",
                    "due": {
                        "local_date": "2026-11-04",
                        "local_time": "08:00",
                        "time_of_day": None,
                        "time_zone": "Asia/Kolkata",
                        "precision": "exact",
                    },
                    "recurrence": {
                        "frequency": "weekly",
                        "interval": 2,
                        "weekdays": ["MO"],
                        "ends_on": None,
                        "occurrence_count": None,
                    },
                    "follow_ups": [
                        {
                            "kind": "conditional_follow_up",
                            "delay_minutes": 30,
                            "condition": "if_incomplete",
                            "target": "take medicine",
                        }
                    ],
                    "additional_instructions": [],
                },
                "clarification_questions": [],
                "unresolved_fields": [],
                "issues": [],
            }
        )


class RaisingProvider:
    def __init__(self, error: Exception) -> None:
        self.error = error

    async def generate(self, prompt: str) -> str:
        raise self.error


def test_openapi_interpret_operation_matches_contract() -> None:
    with TestClient(create_app(provider=FakeProvider())) as client:
        openapi = client.get("/openapi.json").json()

    operation = openapi["paths"]["/api/v1/reminders/interpret"]["post"]
    assert operation["operationId"] == "interpretReminder"
    assert operation["requestBody"]["content"]["application/json"]["schema"]["$ref"] == (
        "#/components/schemas/InterpretationRequest"
    )
    for status_code in ("200", "422", "502", "503", "504"):
        assert status_code in operation["responses"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"] == (
        "#/components/schemas/InterpretationResult"
    )


def test_endpoint_success_response_conforms_to_openapi_model() -> None:
    with TestClient(create_app(provider=FakeProvider())) as client:
        response = client.post(
            "/api/v1/reminders/interpret",
            json={
                "text": "Remind me to call Rahul tomorrow at 10 AM.",
                "reference_context": {
                    "reference_instant": "2026-11-03T09:00:00+05:30",
                    "time_zone": "Asia/Kolkata",
                },
            },
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    parsed = InterpretationResult.model_validate_json(response.text)
    assert parsed.schema_version == "1.0"
    assert parsed.status == "ready"


def test_clarification_response_conforms_to_openapi_model() -> None:
    with TestClient(create_app(provider=ClarifyingProvider())) as client:
        response = client.post(
            "/api/v1/reminders/interpret",
            json={"text": "Remind me to call my manager.", "reference_context": None},
        )

    assert response.status_code == 200
    parsed = InterpretationResult.model_validate_json(response.text)
    assert parsed.status == "needs_clarification"
    assert parsed.reminder is not None
    assert parsed.reminder.due is None
    assert parsed.clarification_questions == ["What date and time should I use?"]
    assert parsed.unresolved_fields == ["due.local_date", "due.local_time"]


def test_recurrence_and_follow_up_response_conforms_to_openapi_model() -> None:
    with TestClient(create_app(provider=RecurrenceProvider())) as client:
        response = client.post(
            "/api/v1/reminders/interpret",
            json={
                "text": "Remind me to take medicine every 2 weeks on Monday at 8 AM. "
                "If incomplete, remind me again after 30 minutes.",
                "reference_context": {
                    "reference_instant": "2026-11-03T09:00:00+05:30",
                    "time_zone": "Asia/Kolkata",
                },
            },
        )

    assert response.status_code == 200
    parsed = InterpretationResult.model_validate_json(response.text)
    assert parsed.reminder is not None
    assert parsed.reminder.recurrence is not None
    assert parsed.reminder.recurrence.frequency == "weekly"
    assert parsed.reminder.recurrence.interval == 2
    assert parsed.reminder.recurrence.weekdays == ["MO"]
    assert parsed.reminder.follow_ups[0].delay_minutes == 30
    assert parsed.reminder.follow_ups[0].condition == "if_incomplete"


@pytest.mark.parametrize(
    ("status_code", "provider", "expected_code"),
    [
        (422, FakeProvider(), "invalid_request"),
        (502, RaisingProvider(ProviderOutputError("private parse detail")), "provider_error"),
        (
            503,
            RaisingProvider(ProviderUnavailableError("private key detail")),
            "provider_unavailable",
        ),
        (504, RaisingProvider(ProviderTimeoutError("private timeout detail")), "provider_timeout"),
    ],
    ids=["request-invalid", "provider-invalid-output", "provider-unavailable", "provider-timeout"],
)
def test_documented_http_errors_conform_to_error_response_schema(
    status_code: int, provider: object, expected_code: str
) -> None:
    with TestClient(create_app(provider=provider)) as client:
        if status_code == 422:
            response = client.post(
                "/api/v1/reminders/interpret",
                json={"text": "bad input", "extra": True, "reference_context": None},
            )
        else:
            response = client.post(
                "/api/v1/reminders/interpret",
                json={"text": "Remind me to call Rahul.", "reference_context": None},
            )

    assert response.status_code == status_code
    error = ErrorResponse.model_validate_json(response.text)
    assert error.error.code == expected_code
    assert "private" not in response.text