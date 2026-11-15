"""Asynchronous Groq structured-output provider adapter."""

from __future__ import annotations

import httpx
from groq import APIConnectionError, APIStatusError, APITimeoutError, AsyncGroq, RateLimitError

from app.api.errors import (
    ProviderOutputError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.core.settings import Settings
from app.schemas.responses import InterpretationResult


def _groq_response_schema() -> dict[str, object]:
    schema = InterpretationResult.model_json_schema()
    _remove_time_formats(schema)
    return schema


def _remove_time_formats(value: object) -> None:
    if isinstance(value, dict):
        if value.get("format") == "time":
            value.pop("format")
        for nested_value in value.values():
            _remove_time_formats(nested_value)
    elif isinstance(value, list):
        for nested_value in value:
            _remove_time_formats(nested_value)


class GroqProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def generate(self, prompt: str) -> str:
        api_key = self._settings.groq_api_key
        if api_key is None:
            raise ProviderUnavailableError()

        client: AsyncGroq | None = None
        try:
            client = AsyncGroq(
                api_key=api_key,
                timeout=self._settings.provider_timeout_seconds,
            )
            response = await client.chat.completions.create(
                model=self._settings.groq_model,
                messages=[{"role": "user", "content": prompt}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "interpretation_result",
                        "strict": True,
                        "schema": _groq_response_schema(),
                    },
                },
            )
        except APITimeoutError as exc:
            raise ProviderTimeoutError() from exc
        except (TimeoutError, httpx.TimeoutException) as exc:
            raise ProviderTimeoutError() from exc
        except RateLimitError as exc:
            raise ProviderUnavailableError() from exc
        except APIStatusError as exc:
            if exc.status_code == 408:
                raise ProviderTimeoutError() from exc
            if exc.status_code == 429 or exc.status_code >= 500:
                raise ProviderUnavailableError() from exc
            raise ProviderOutputError() from exc
        except APIConnectionError as exc:
            raise ProviderUnavailableError() from exc
        except Exception as exc:
            raise ProviderUnavailableError() from exc
        finally:
            if client is not None:
                try:
                    await client.close()
                except Exception as exc:
                    raise ProviderUnavailableError() from exc

        try:
            response_text = response.choices[0].message.content
        except (AttributeError, IndexError, TypeError) as exc:
            raise ProviderOutputError() from exc
        if not isinstance(response_text, str) or not response_text.strip():
            raise ProviderOutputError()
        return response_text
