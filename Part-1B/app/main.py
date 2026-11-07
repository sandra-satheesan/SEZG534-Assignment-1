"""FastAPI application factory for the Part 1B service."""

from __future__ import annotations

from fastapi import FastAPI

from app.api.errors import register_error_handlers
from app.api.routes.reminders import router as reminders_router
from app.core.settings import Settings
from app.providers.base import ModelProvider
from app.providers.gemini import GeminiProvider


def create_app(
    settings: Settings | None = None,
    provider: ModelProvider | None = None,
) -> FastAPI:
    """Create an app without network calls or a credential requirement."""
    app = FastAPI(title="Natural-Language Reminder Interpretation API", version="1.0.0")
    app_settings = settings if settings is not None else Settings.from_environment()
    app.state.settings = app_settings
    app.state.model_provider = provider
    if provider is None and app_settings.gemini_api_key is not None:
        app.state.model_provider = GeminiProvider(app_settings)
    register_error_handlers(app)
    app.include_router(reminders_router)
    return app