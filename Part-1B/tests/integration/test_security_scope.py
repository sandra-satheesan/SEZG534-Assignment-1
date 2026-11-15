import json

import pytest
from app.api.errors import ProviderOutputError, ProviderUnavailableError
from app.core.settings import MAX_PROVIDER_TIMEOUT_SECONDS, Settings
from app.main import create_app
from app.providers.base import ModelProvider
from fastapi.testclient import TestClient


class FailingProvider:
    def __init__(self, error: Exception) -> None:
        self.error = error

    async def generate(self, prompt: str) -> str:
        raise self.error


def post_interpretation(
    provider: ModelProvider | None,
    *,
    text: str,
) -> tuple[int, dict[str, object], str]:
    app = create_app(provider=provider)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/reminders/interpret",
            json={"text": text, "reference_context": None},
        )
    return response.status_code, response.json(), response.text


def test_provider_failures_do_not_expose_credentials_or_internal_details() -> None:
    secret = "GROQ_API_KEY=super-secret-value"
    status_code, body, response_text = post_interpretation(
        FailingProvider(RuntimeError(secret)),
        text="Remind me to call Rahul.",
    )

    assert status_code == 503
    assert body == {
        "error": {
            "code": "provider_unavailable",
            "message": "Provider unavailable.",
        }
    }
    assert secret not in response_text
    assert "super-secret-value" not in response_text


def test_provider_output_errors_do_not_expose_raw_provider_content() -> None:
    secret_output = json.dumps(
        {
            "api_key": "super-secret-value",
            "request_text": "private reminder content",
        }
    )
    status_code, body, response_text = post_interpretation(
        FailingProvider(ProviderOutputError(secret_output)),
        text="Remind me to call Rahul.",
    )

    assert status_code == 502
    assert body == {
        "error": {
            "code": "provider_error",
            "message": "The model provider returned an invalid response.",
        }
    }
    assert "super-secret-value" not in response_text
    assert "private reminder content" not in response_text


def test_request_text_is_not_echoed_when_request_validation_fails() -> None:
    private_text = "private reminder text that must not appear in an error response"
    app = create_app()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/reminders/interpret",
            json={"text": private_text, "unexpected": "private field"},
        )

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "invalid_request",
            "message": "Request validation failed.",
        }
    }
    assert private_text not in response.text
    assert "private field" not in response.text


def test_request_length_limit_is_enforced_without_echoing_input() -> None:
    oversized_text = "x" * 4001
    app = create_app()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/reminders/interpret",
            json={"text": oversized_text, "reference_context": None},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert oversized_text not in response.text


@pytest.mark.parametrize("timeout", [0, -1, MAX_PROVIDER_TIMEOUT_SECONDS + 0.1])
def test_provider_timeout_settings_cannot_be_unbounded(timeout: float) -> None:
    with pytest.raises(ValueError):
        Settings(provider_timeout_seconds=timeout)


def test_provider_timeout_setting_is_bounded_at_configured_maximum() -> None:
    settings = Settings(provider_timeout_seconds=MAX_PROVIDER_TIMEOUT_SECONDS)

    assert settings.provider_timeout_seconds == MAX_PROVIDER_TIMEOUT_SECONDS


def test_application_exposes_only_interpretation_without_side_effect_routes() -> None:
    app = create_app()

    with TestClient(app) as client:
        openapi = client.get("/openapi.json").json()
        scheduling_response = client.post("/api/v1/reminders/schedule", json={})
        notification_response = client.post("/api/v1/notifications", json={})
        persistence_response = client.post("/api/v1/reminders", json={})

    assert set(openapi["paths"]) == {"/api/v1/reminders/interpret"}
    assert scheduling_response.status_code == 404
    assert notification_response.status_code == 404
    assert persistence_response.status_code == 404


def test_interpretation_endpoint_has_no_successful_scheduling_claim() -> None:
    app = create_app(provider=FailingProvider(ProviderUnavailableError()))

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/reminders/interpret",
            json={
                "text": "Schedule a reminder to call Rahul tomorrow.",
                "reference_context": None,
            },
        )

    assert response.status_code == 503
    assert "scheduled" not in response.text.lower()
    assert "notification" not in response.text.lower()
