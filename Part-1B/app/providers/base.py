"""Injectable asynchronous model-provider boundary."""

from __future__ import annotations

from typing import Protocol

from fastapi import Request


class ModelProvider(Protocol):
    async def generate(self, prompt: str) -> str:
        """Return untrusted provider output for a prepared prompt."""
        ...


def get_provider(request: Request) -> ModelProvider | None:
    """Resolve the optional app-injected provider without performing I/O."""
    provider: ModelProvider | None = request.app.state.model_provider
    return provider