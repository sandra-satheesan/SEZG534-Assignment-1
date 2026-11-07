import pytest
from app.core.settings import Settings


def test_settings_allow_missing_credentials_and_use_bounded_default_timeout(
    monkeypatch,
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("GEMINI_TIMEOUT_SECONDS", raising=False)

    settings = Settings.from_environment()

    assert settings.gemini_api_key is None
    assert settings.gemini_model
    assert 0 < settings.provider_timeout_seconds <= 30


def test_settings_load_credentials_model_and_timeout(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    monkeypatch.setenv("GEMINI_TIMEOUT_SECONDS", "12.5")

    settings = Settings.from_environment()

    assert settings.gemini_api_key == "test-key"
    assert settings.gemini_model == "test-model"
    assert settings.provider_timeout_seconds == 12.5
    assert "test-key" not in repr(settings)


@pytest.mark.parametrize("timeout", ["0", "-1", "30.1", "not-a-number"])
def test_settings_reject_invalid_or_unbounded_timeout(monkeypatch, timeout: str) -> None:
    monkeypatch.setenv("GEMINI_TIMEOUT_SECONDS", timeout)

    with pytest.raises(ValueError):
        Settings.from_environment()


def test_settings_reject_empty_model_id(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_MODEL", "  ")

    with pytest.raises(ValueError):
        Settings.from_environment()