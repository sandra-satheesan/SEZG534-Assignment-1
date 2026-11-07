"""Asynchronous Gemini structured-output provider adapter."""

from __future__ import annotations

from typing import Any

import httpx
from google import genai
from google.genai import errors, types

from app.api.errors import (
    ProviderOutputError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.core.settings import Settings
from app.schemas.responses import InterpretationResult


class GeminiProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def generate(self, prompt: str) -> str:
        api_key = self._settings.gemini_api_key
        if api_key is None:
            raise ProviderUnavailableError()

        client: Any | None = None
        try:
            client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(
                    timeout=round(self._settings.provider_timeout_seconds * 1000)
                ),
            )
            response = await client.aio.models.generate_content(
                model=self._settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=InterpretationResult,
                ),
            )
        except (TimeoutError, httpx.TimeoutException) as exc:
            raise ProviderTimeoutError() from exc
        except errors.APIError as exc:
            if exc.code == 408:
                raise ProviderTimeoutError() from exc
            if exc.code == 429 or exc.code >= 500:
                raise ProviderUnavailableError() from exc
            raise ProviderOutputError() from exc
        except Exception as exc:
            raise ProviderUnavailableError() from exc
        finally:
            if client is not None:
                try:
                    await client.aio.aclose()
                except Exception as exc:
                    raise ProviderUnavailableError() from exc

        response_text = response.text
        if not isinstance(response_text, str) or not response_text.strip():
            raise ProviderOutputError()
        return response_text