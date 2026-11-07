# Research: Natural-Language Reminder Agent

**Date**: 2026-11-03

This research resolves the implementation choices needed for the plan. It uses official framework and provider documentation. SDK endpoints and supported Gemini models are version-sensitive and must be reconfirmed when dependencies are pinned.

## 1. Gemini Python SDK and structured output

**Decision**: Use Google's maintained `google-genai` Python SDK. Ask Gemini for JSON-constrained structured output using the simple reminder-result schema. Treat generated JSON as untrusted: parse the complete response, validate it with Pydantic, then apply application-level invariants before returning it.

**Rationale**: Google's current documentation recommends the GenAI SDK; its structured-output guide demonstrates Python/Pydantic schema-based JSON output. Google distinguishes structured output (formatting content) from function calling (requesting actions); interpretation-only does not need model-directed actions. Google also notes that supported JSON Schema is a subset and schema compliance does not guarantee semantic correctness, so application validation remains mandatory.

**Alternatives considered**:

- Legacy `google-generativeai`: rejected because Google marks the legacy Python library as no longer actively maintained.
- Function calling: rejected because the feature interprets and returns data but must not schedule reminders or trigger side effects.
- Trusting constrained decoding alone: rejected because supported constraints are partial and valid JSON may still contain incorrect or contradictory values.
- Partial/truncated JSON recovery: rejected because a recovered partial reminder could appear actionable despite missing information.

**Sources**:

- [Gemini API SDK libraries](https://ai.google.dev/gemini-api/docs/libraries)
- [Google GenAI SDK migration guide](https://ai.google.dev/gemini-api/docs/migrate)
- [Gemini structured output](https://ai.google.dev/gemini-api/docs/structured-output)
- [Gemini structured-output best practices and limitations](https://ai.google.dev/gemini-api/docs/structured-output#best-practices)
- [Pydantic JSON parsing](https://docs.pydantic.dev/latest/concepts/json/)
- [Pydantic strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/)

## 2. Async API and provider isolation

**Decision**: Use an async FastAPI route when awaiting the Gemini client's async method. Expose the interpreter/provider through FastAPI dependency injection. Tests override that dependency with a fake provider and reset overrides after each test.

**Rationale**: FastAPI supports async request handlers for awaitable libraries, and the GenAI Python SDK documents asynchronous client methods. Dependency overrides isolate tests from network, quotas, and credentials. Use the synchronous `TestClient` for ordinary deterministic cases; use async HTTPX/ASGI tests only where testing asynchronous behavior directly is valuable.

**Alternatives considered**:

- Calling a synchronous external SDK directly from an async route: rejected to avoid blocking the event loop.
- Requiring a real Gemini key for application startup/tests: rejected because deterministic tests must run offline and without credentials.
- Patching SDK internals in each test: rejected in favor of a stable provider boundary and dependency override.

**Sources**:

- [FastAPI async guidance](https://fastapi.tiangolo.com/async/)
- [FastAPI dependency injection](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [FastAPI dependency overrides in tests](https://fastapi.tiangolo.com/advanced/testing-dependencies/)
- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [FastAPI async tests](https://fastapi.tiangolo.com/advanced/async-tests/)
- [FastAPI lifespan testing](https://fastapi.tiangolo.com/advanced/testing-events/)
- [Google GenAI Python SDK reference](https://googleapis.github.io/python-genai/)

## 3. Output validation and failure policy

**Decision**: Parse the complete provider response with Pydantic JSON validation, reject unknown fields and invalid types, and perform separate domain checks for status, timing, recurrence, clarification, and instruction consistency. Missing credentials and provider failures return stable safe HTTP error envelopes; the service remains importable and deterministic tests remain runnable without credentials.

**Rationale**: JSON Schema constrained output is a useful generation constraint, not a trust boundary. Pydantic and domain checks enforce the stronger application contract. Invalid model output must not be made success-shaped through coercion, repair, or raw passthrough.

**Alternatives considered**:

- Returning raw provider JSON: rejected because it can be malformed or violate domain invariants.
- Coercing malformed values to defaults: rejected because this can invent a reminder date/time or make invalid output look successful.
- Failing application import/startup when the API key is absent: rejected because it prevents offline tests and development of non-provider behavior.

**Sources**:

- [Gemini structured output best practices](https://ai.google.dev/gemini-api/docs/structured-output#best-practices)
- [Pydantic JSON parsing](https://docs.pydantic.dev/latest/concepts/json/)
- [Pydantic strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/)

## 4. Version and configuration decisions

**Decision**: Target Python 3.11 or newer, FastAPI with Pydantic 2, and a pinned `google-genai` version. Keep Gemini model identifier and request timeout configurable, and record the selected model and SDK versions in every live evaluation report.

**Rationale**: This supports the requested stack while keeping provider/model replacement possible. Gemini model names, SDK surfaces, and structured-output support change over time; pinning and recording versions makes evaluations interpretable and reproducible.

**Alternatives considered**:

- Hard-code a Gemini model identifier: rejected because model availability and behavior vary over time.
- Select a provider-specific model during specification: rejected because it is implementation configuration and must be checked against current supported models, quota, and schema support when dependencies are pinned.

**Sources**:

- [Gemini API models](https://ai.google.dev/gemini-api/docs/models)
- [Google GenAI SDK](https://googleapis.github.io/python-genai/)
- [Gemini structured output](https://ai.google.dev/gemini-api/docs/structured-output)

## Resolved decisions and remaining implementation-time choices

- The application interprets and returns structured reminder data only; scheduling and notification delivery are explicitly out of scope.
- The service will not use host wall-clock time or an implicit time zone for relative-date interpretation; evaluation supplies a fixed reference context.
- Multi-reminder requests will be returned as requiring clarification to submit one reminder per request; this avoids silently dropping or merging distinct intents.
- A default maximum request length of 4,000 characters is planned as input protection and must be documented in the API contract.
- The exact Gemini model ID and final dependency versions are selected during implementation after checking current provider support. The design is not blocked by this configurable choice.
- Sending request text to Gemini is an operational privacy consideration. Deployment documentation must disclose the transfer and verify the current provider data-handling terms; no provider-side retention promise is made by this application.
