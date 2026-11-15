from typing import Annotated

from app.api.errors import ProviderUnavailableError
from app.main import create_app
from app.providers.base import ModelProvider, get_provider
from app.schemas.requests import InterpretationRequest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient


class FakeProvider:
    async def generate(self, prompt: str) -> str:
        return prompt


def app_with_test_routes() -> FastAPI:
    app = create_app()

    @app.post("/_test/validate")
    async def validate_request(request: InterpretationRequest) -> dict[str, str]:
        return {"text": request.text}

    @app.get("/_test/provider")
    async def provider_probe(
        provider: Annotated[ModelProvider | None, Depends(get_provider)],
    ) -> dict[str, str]:
        if provider is None:
            raise ProviderUnavailableError()
        return {"result": await provider.generate("probe")}

    @app.get("/_test/unavailable")
    async def unavailable_probe() -> None:
        raise ProviderUnavailableError("private provider configuration")

    @app.get("/_test/unhandled")
    async def unhandled_probe() -> None:
        raise RuntimeError("private exception detail")

    return app


def test_app_starts_and_serves_openapi_without_groq_credentials(monkeypatch) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["version"] == "1.0.0"
    assert set(response.json()["paths"]) == {"/api/v1/reminders/interpret"}


def test_interpret_endpoint_validates_body_without_calling_provider() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/reminders/interpret",
            json={
                "text": "private request",
                "unexpected": "do not echo",
                "reference_context": None,
            },
        )

    assert response.status_code == 422
    assert response.json() == {
        "error": {"code": "invalid_request", "message": "Request validation failed."}
    }
    assert "private request" not in response.text
    assert "do not echo" not in response.text


def test_interpret_endpoint_returns_safe_unavailable_without_provider_call() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/reminders/interpret",
            json={
                "text": "Remind me to call Rahul.",
                "reference_context": None,
            },
        )

    assert response.status_code == 503
    assert response.json() == {
        "error": {"code": "provider_unavailable", "message": "Provider unavailable."}
    }


def test_request_validation_returns_safe_422_without_echoing_input() -> None:
    app = app_with_test_routes()

    with TestClient(app) as client:
        response = client.post(
            "/_test/validate",
            json={"text": "private submitted text", "unexpected": "do not echo"},
        )

    assert response.status_code == 422
    assert response.json() == {
        "error": {"code": "invalid_request", "message": "Request validation failed."}
    }
    assert "private submitted text" not in response.text
    assert "do not echo" not in response.text


def test_malformed_json_returns_safe_422() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/reminders/interpret",
            content='{"text":',
            headers={"content-type": "application/json"},
        )

    assert response.status_code == 422
    assert response.json() == {
        "error": {"code": "invalid_request", "message": "Request validation failed."}
    }


def test_provider_dependency_can_be_overridden_without_network_access() -> None:
    app = app_with_test_routes()
    fake_provider = FakeProvider()
    app.dependency_overrides[get_provider] = lambda: fake_provider

    with TestClient(app) as client:
        response = client.get("/_test/provider")

    assert response.status_code == 200
    assert response.json() == {"result": "probe"}


def test_missing_groq_credentials_produce_safe_503() -> None:
    app = app_with_test_routes()

    with TestClient(app) as client:
        response = client.get("/_test/provider")

    assert response.status_code == 503
    assert response.json() == {
        "error": {"code": "provider_unavailable", "message": "Provider unavailable."}
    }


def test_provider_error_is_safe_and_uses_503_envelope() -> None:
    app = app_with_test_routes()

    with TestClient(app) as client:
        response = client.get("/_test/unavailable")

    assert response.status_code == 503
    assert response.json() == {
        "error": {"code": "provider_unavailable", "message": "Provider unavailable."}
    }
    assert "private" not in response.text


def test_unhandled_error_does_not_expose_exception_details() -> None:
    app = app_with_test_routes()

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/_test/unhandled")

    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "internal_error", "message": "Internal server error."}
    }
    assert "private exception detail" not in response.text