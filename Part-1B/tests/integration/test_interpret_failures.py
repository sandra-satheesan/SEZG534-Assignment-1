import json

import pytest
from app.api.errors import ProviderOutputError, ProviderTimeoutError, ProviderUnavailableError
from app.main import create_app
from fastapi.testclient import TestClient


class FakeProvider:
    def __init__(self, response: str | dict | Exception) -> None:
        self.response = response
        self.prompts: list[str] = []

    async def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if isinstance(self.response, Exception):
            raise self.response
        if isinstance(self.response, str):
            return self.response
        return json.dumps(self.response)


def semantic_result(
    *, status: str, code: str, question: str | None = None, unresolved: list[str] | None = None
) -> dict:
    return {
        "schema_version": "1.0",
        "status": status,
        "reminder": None,
        "clarification_questions": [question] if question else [],
        "unresolved_fields": unresolved or [],
        "issues": [
            {"code": code, "field": "text", "message": "The request cannot be interpreted."}
        ],
    }


def post_request(provider: FakeProvider, text: str) -> tuple[int, dict, str]:
    app = create_app(provider=provider)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/reminders/interpret",
            json={"text": text, "reference_context": None},
        )
    return response.status_code, response.json(), response.text


@pytest.mark.parametrize(
    ("text", "result", "expected_status", "expected_code"),
    [
        (
            "Remind me to pay bill on February 30, 2027 at 9 AM.",
            semantic_result(status="invalid", code="invalid_date"),
            "invalid",
            "invalid_date",
        ),
        (
            "Remind me to call Rahul at 25:99.",
            semantic_result(status="invalid", code="invalid_time"),
            "invalid",
            "invalid_time",
        ),
        (
            "Write a poem about rain.",
            semantic_result(status="unsupported", code="unsupported_request"),
            "unsupported",
            "unsupported_request",
        ),
        (
            "Remind me to call Rahul at 9 AM and 5 PM.",
            semantic_result(
                status="needs_clarification",
                code="contradictory_timing",
                question="Which time should I use?",
                unresolved=["due.local_time"],
            ),
            "needs_clarification",
            "contradictory_timing",
        ),
        (
            "Remind me to call Rahul tomorrow and email Priya today.",
            {
                "schema_version": "1.0",
                "status": "needs_clarification",
                "reminder": None,
                "clarification_questions": ["Please submit one reminder per request."],
                "unresolved_fields": ["reminder.title"],
                "issues": [],
            },
            "needs_clarification",
            None,
        ),
    ],
)
def test_invalid_unsupported_and_conflicting_requests_return_structured_results(
    text: str, result: dict, expected_status: str, expected_code: str | None
) -> None:
    provider = FakeProvider(result)
    status_code, body, _ = post_request(provider, text)

    assert status_code == 200
    assert body["status"] == expected_status
    assert body["reminder"] is None
    if expected_code is not None:
        assert body["issues"][0]["code"] == expected_code
    if expected_status == "needs_clarification":
        assert body["clarification_questions"]
        assert body["unresolved_fields"]
    if expected_code == "contradictory_timing":
        prompt = " ".join(provider.prompts[0].split())
        assert "For contradictory or conflicting timing that needs user input" in prompt
        assert "return status needs_clarification" in prompt


@pytest.mark.parametrize(
    ("error", "status_code", "error_code"),
    [
        (ProviderTimeoutError("private timeout detail"), 504, "provider_timeout"),
        (ProviderUnavailableError("private API key detail"), 503, "provider_unavailable"),
        (RuntimeError("private stack and API key detail"), 503, "provider_unavailable"),
    ],
)
def test_provider_failures_are_safe_and_never_return_reminder_data(
    error: Exception, status_code: int, error_code: str
) -> None:
    response_status, body, response_text = post_request(
        FakeProvider(error), "Remind me to call Rahul tomorrow at 9 AM."
    )

    assert response_status == status_code
    assert body == {
        "error": {
            "code": error_code,
            "message": {
                "provider_timeout": "The model provider timed out.",
                "provider_unavailable": "Provider unavailable.",
            }[error_code],
        }
    }
    assert "reminder" not in body
    assert "private" not in response_text
    assert "API key" not in response_text


@pytest.mark.parametrize(
    "provider_output",
    [
        "{truncated-json",
        json.dumps({"schema_version": "1.0", "status": "ready", "unexpected": True}),
        json.dumps(
            {
                "schema_version": "1.0",
                "status": "ready",
                "reminder": None,
                "clarification_questions": [],
                "unresolved_fields": [],
                "issues": [],
            }
        ),
    ],
    ids=["truncated-json", "schema-invalid", "ready-without-reminder"],
)
def test_malformed_or_invariant_failing_provider_output_is_rejected(
    provider_output: str,
) -> None:
    status_code, body, response_text = post_request(
        FakeProvider(provider_output), "Remind me to call Rahul tomorrow at 9 AM."
    )

    assert status_code == 502
    assert body == {
        "error": {
            "code": "provider_error",
            "message": "The model provider returned an invalid response.",
        }
    }
    assert "reminder" not in body
    assert provider_output not in response_text


def test_provider_output_error_is_mapped_to_safe_502() -> None:
    status_code, body, response_text = post_request(
        FakeProvider(ProviderOutputError("private parsing details")), "Remind me to call Rahul."
    )

    assert status_code == 502
    assert body["error"]["code"] == "provider_error"
    assert "private parsing details" not in response_text