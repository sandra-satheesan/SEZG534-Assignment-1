from types import SimpleNamespace

import httpx
import pytest
from app.api.errors import ProviderOutputError, ProviderTimeoutError, ProviderUnavailableError
from app.core.settings import Settings
from app.providers.groq import GroqProvider, _groq_response_schema
from app.schemas.responses import InterpretationResult
from groq import APIStatusError, APITimeoutError


class FakeCompletions:
    def __init__(self, response: object | None = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.call: dict[str, object] | None = None

    async def create(self, **kwargs: object) -> object:
        self.call = kwargs
        if self.error is not None:
            raise self.error
        return self.response


class FakeClient:
    def __init__(self, completions: FakeCompletions) -> None:
        self.chat = SimpleNamespace(completions=completions)
        self.closed = False

    async def close(self) -> None:
        self.closed = True


def api_status_error(status_code: int) -> APIStatusError:
    response = httpx.Response(status_code=status_code, request=httpx.Request("POST", "https://test"))
    return APIStatusError("private provider detail", response=response, body={"message": "private"})


@pytest.mark.asyncio
async def test_groq_provider_requests_strict_json_schema_and_closes_client(monkeypatch) -> None:
    completions = FakeCompletions(
        response=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"status":"ready"}'))]
        )
    )
    client = FakeClient(completions)
    client_arguments: dict[str, object] = {}

    def fake_client_factory(**kwargs: object) -> FakeClient:
        client_arguments.update(kwargs)
        return client

    monkeypatch.setattr("app.providers.groq.AsyncGroq", fake_client_factory)
    provider = GroqProvider(
        Settings(groq_api_key="secret", groq_model="test-model", provider_timeout_seconds=8)
    )

    output = await provider.generate("prepared prompt")

    assert output == '{"status":"ready"}'
    assert client_arguments["api_key"] == "secret"
    assert client_arguments["timeout"] == 8
    assert completions.call is not None
    assert completions.call["model"] == "test-model"
    assert completions.call["messages"] == [{"role": "user", "content": "prepared prompt"}]
    response_format = completions.call["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    schema = response_format["json_schema"]["schema"]
    assert schema["properties"]["reminder"]["anyOf"][0]["$ref"] == "#/$defs/ReminderDraft"
    assert schema["$defs"]["DueTime"]["properties"]["local_time"]["anyOf"][0] == {
        "type": "string"
    }
    assert schema["$defs"]["DueTime"]["properties"]["local_date"]["anyOf"][0]["format"] == "date"
    assert client.closed


def test_groq_response_schema_preserves_application_schema_without_time_format() -> None:
    schema = _groq_response_schema()
    assert schema != InterpretationResult.model_json_schema()
    assert schema["$defs"]["DueTime"]["properties"]["local_time"]["anyOf"][0] == {
        "type": "string"
    }


@pytest.mark.asyncio
async def test_groq_provider_does_not_create_client_without_key(monkeypatch) -> None:
    def fail_client_factory(**kwargs: object) -> FakeClient:
        raise AssertionError("client must not be constructed without credentials")

    monkeypatch.setattr("app.providers.groq.AsyncGroq", fail_client_factory)
    provider = GroqProvider(Settings())

    with pytest.raises(ProviderUnavailableError):
        await provider.generate("prepared prompt")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (TimeoutError("private timeout detail"), ProviderTimeoutError),
        (httpx.TimeoutException("private timeout detail"), ProviderTimeoutError),
        (
            APITimeoutError(httpx.Request("POST", "https://test")),
            ProviderTimeoutError,
        ),
        (api_status_error(408), ProviderTimeoutError),
        (api_status_error(429), ProviderUnavailableError),
        (api_status_error(500), ProviderUnavailableError),
        (api_status_error(400), ProviderOutputError),
    ],
)
async def test_groq_provider_maps_errors_without_leaking_details(
    monkeypatch,
    error: Exception,
    expected: type[Exception],
) -> None:
    completions = FakeCompletions(error=error)
    client = FakeClient(completions)
    monkeypatch.setattr("app.providers.groq.AsyncGroq", lambda **kwargs: client)
    provider = GroqProvider(Settings(groq_api_key="secret"))

    with pytest.raises(expected) as raised:
        await provider.generate("prepared prompt")

    assert "private" not in str(raised.value)
    assert client.closed


@pytest.mark.asyncio
async def test_groq_provider_rejects_empty_response_content(monkeypatch) -> None:
    client = FakeClient(
        FakeCompletions(
            response=SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=None))]
            )
        )
    )
    monkeypatch.setattr("app.providers.groq.AsyncGroq", lambda **kwargs: client)
    provider = GroqProvider(Settings(groq_api_key="secret"))

    with pytest.raises(ProviderOutputError):
        await provider.generate("prepared prompt")
