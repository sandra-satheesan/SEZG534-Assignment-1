"""Validation-only endpoint registration for the interpretation API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.errors import ProviderUnavailableError
from app.providers.base import ModelProvider, get_provider
from app.schemas.requests import InterpretationRequest
from app.schemas.responses import ErrorResponse, InterpretationResult
from app.services.interpreter import InterpretationService

router = APIRouter()


@router.post(
    "/api/v1/reminders/interpret",
    operation_id="interpretReminder",
    response_model=InterpretationResult,
    responses={
        422: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
    summary="Interpret a reminder request",
)
async def interpret_reminder(
    request: InterpretationRequest,
    provider: Annotated[ModelProvider | None, Depends(get_provider)],
) -> InterpretationResult:
    """Interpret one request through the injected model-provider boundary."""
    if provider is None:
        raise ProviderUnavailableError()
    return await InterpretationService(provider).interpret(request)