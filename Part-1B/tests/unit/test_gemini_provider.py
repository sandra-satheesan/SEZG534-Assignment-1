from types import SimpleNamespace

import httpx
import pytest
from app.api.errors import ProviderOutputError, ProviderTimeoutError, ProviderUnavailableError
from app.core.settings import Settings
from app.providers.gemini import GeminiProvider
from google.genai import errors


class FakeModels:
    def __init__(self, response: object | None = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.call: dict[str, object] | None = None

    async def generate_content(self, **kwargs: object) -> object:
        self.call = kwargs
        if self.error is not None:
            raise self.error
        return self.response


class FakeClient:
    def __init__(self, models: FakeModels) -> None:
        self.aio = SimpleNamespace(models=models, aclose=self.aclose)
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_gemini_provider_requests_json_schema_and_closes_client(monkeypatch) -> None:
    models = FakeModels(response=SimpleNamespace(text='{"status":"ready"}'))
    client = FakeClient(models)
    client_arguments: dict[str, object] = {}

    def fake_client_factory(**kwargs: object) -> FakeClient:
        client_arguments.update(kwargs)
        return client

    monkeypatch.setattr("app.providers.gemini.genai.Client", fake_client_factory)
    provider = GeminiProvider(
        Settings(gemini_api_key="secret", gemini_model="test-model", provider_timeout_seconds=8)
    )

    output = await provider.generate("prepared prompt")

    assert output == '{"status":"ready"}'
    assert client_arguments["api_key"] == "secret"
    assert models.call is not None
    assert models.call["model"] == "test-model"
    assert models.call["contents"] == "prepared prompt"
    config = models.call["config"]
    assert config.response_mime_type == "application/json"
    assert client.closed


@pytest.mark.asyncio
async def test_gemini_provider_does_not_create_client_without_key(monkeypatch) -> None:
    def fail_client_factory(**kwargs: object) -> FakeClient:
        raise AssertionError("client must not be constructed without credentials")

    monkeypatch.setattr("app.providers.gemini.genai.Client", fail_client_factory)
    provider = GeminiProvider(Settings())

    with pytest.raises(ProviderUnavailableError):
        await provider.generate("prepared prompt")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (TimeoutError("private timeout detail"), ProviderTimeoutError),
        (httpx.TimeoutException("private timeout detail"), ProviderTimeoutError),
        (errors.APIError(429, {"message": "private quota detail"}), ProviderUnavailableError),
        (errors.APIError(400, {"message": "private provider detail"}), ProviderOutputError),
    ],
)
async def test_gemini_provider_maps_errors_without_leaking_details(
    monkeypatch,
    error: Exception,
    expected: type[Exception],
) -> None:
    models = FakeModels(error=error)
    client = FakeClient(models)
    monkeypatch.setattr("app.providers.gemini.genai.Client", lambda **kwargs: client)
    provider = GeminiProvider(Settings(gemini_api_key="secret"))

    with pytest.raises(expected) as raised:
        await provider.generate("prepared prompt")

    assert "private" not in str(raised.value)
    assert client.closed


@pytest.mark.asyncio
async def test_gemini_provider_rejects_empty_response_text(monkeypatch) -> None:
    client = FakeClient(FakeModels(response=SimpleNamespace(text=None)))
    monkeypatch.setattr("app.providers.gemini.genai.Client", lambda **kwargs: client)
    provider = GeminiProvider(Settings(gemini_api_key="secret"))

    with pytest.raises(ProviderOutputError):
        await provider.generate("prepared prompt")