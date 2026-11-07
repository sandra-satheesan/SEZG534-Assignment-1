"""Interpretation orchestration with strict provider-output validation."""

from __future__ import annotations

import httpx
from pydantic import ValidationError

from app.api.errors import (
    ApplicationError,
    ProviderOutputError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.prompts.reminder_interpretation import build_interpretation_prompt
from app.providers.base import ModelProvider
from app.schemas.requests import InterpretationRequest
from app.schemas.responses import InterpretationResult
from app.services.invariants import validate_interpretation_result


class InterpretationService:
    def __init__(self, provider: ModelProvider) -> None:
        self._provider = provider

    async def interpret(self, request: InterpretationRequest) -> InterpretationResult:
        prompt = build_interpretation_prompt(request)
        try:
            provider_output = await self._provider.generate(prompt)
        except ApplicationError:
            raise
        except (TimeoutError, httpx.TimeoutException) as exc:
            raise ProviderTimeoutError() from exc
        except Exception as exc:
            raise ProviderUnavailableError() from exc
        if not isinstance(provider_output, str):
            raise ProviderOutputError()

        try:
            result = InterpretationResult.model_validate_json(provider_output)
        except (ValidationError, ValueError, TypeError) as exc:
            raise ProviderOutputError() from exc
        return validate_interpretation_result(request, result)