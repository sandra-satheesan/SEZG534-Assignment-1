# Natural-Language Reminder Agent

Part 1B is an independent Python 3.11+ service that interprets one
natural-language reminder request into validated structured data. It exposes
only `POST /api/v1/reminders/interpret`.

The service is interpretation-only. It does not schedule reminders, persist
user reminders, send notifications, or claim that an action was scheduled.
Part 1A and its files remain outside this project.

## Architecture and request flow

The application separates:

- FastAPI application and route wiring in `app/main.py` and
  `app/api/routes/reminders.py`.
- Strict request and response models in `app/schemas/`.
- Prompt construction in `app/prompts/reminder_interpretation.py`.
- The asynchronous `ModelProvider.generate(prompt)` boundary in
  `app/providers/base.py`.
- Groq transport in `app/providers/groq.py`.
- Provider-output parsing and cross-field invariant validation in
  `app/services/interpreter.py` and `app/services/invariants.py`.
- Versioned corpus loading, scoring, repeated runs, reports, and human-review
  records in `app/evaluation/`.

For each request, the route validates the input, builds a prompt containing
only the submitted text and explicit reference context, calls the injected
provider, strictly parses the returned JSON, validates domain invariants, and
returns either a ready, clarification, invalid, or unsupported result.
Relative timing never uses the host clock or an implicit time zone.

## Prerequisites and setup

Use Python 3.11 or newer. From the repository root:

```sh
python3 --version
python3 -m venv Part-1B/.venv
Part-1B/.venv/bin/python -m pip install --upgrade pip
Part-1B/.venv/bin/python -m pip install -e 'Part-1B[dev]'
```

The development extra installs pytest, Ruff, mypy, Bandit, HTTPX,
pytest-asyncio, PyYAML, and the application dependencies. Offline tests do
not require Groq credentials or network access.

## Configuration

The supported environment variables are listed in `.env.example`:

| Variable | Purpose |
|---|---|
| `GROQ_API_KEY` | Optional credential for live Groq evaluation and provider use |
| `GROQ_MODEL` | Groq model identifier; defaults to `openai/gpt-oss-20b` |
| `GROQ_TIMEOUT_SECONDS` | Provider timeout in seconds; must be greater than 0 and no more than 30 |

`Settings.from_environment()` reads the process environment; the application
does not load `.env` files automatically. Keep real credentials in the
environment or an ignored local configuration file, never in source, tests,
fixtures, or reports.

## Running the FastAPI application

The application factory is `app.main:create_app`. Verify that it imports and
starts without credentials:

```sh
cd Part-1B
.venv/bin/python -c "from app.main import create_app; create_app(); print('application factory OK')"
```

The project manifest does not currently declare an ASGI server. If an ASGI
server such as Uvicorn is available in the environment, run from `Part-1B`:

```sh
.venv/bin/python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

The documented API route is:

```text
POST /api/v1/reminders/interpret
```

It accepts `text` and an explicit nullable `reference_context` containing an
RFC 3339 instant with offset and an IANA time-zone identifier. Requests are
limited to 4,000 characters after validation.

## Offline tests and quality checks

Run these commands from `Part-1B`:

```sh
.venv/bin/python -m pytest
.venv/bin/ruff check app tests
.venv/bin/mypy app
.venv/bin/bandit -c pyproject.toml -r app
```

The tests use injected fake providers and fixed reference contexts. They do
not call Groq, require credentials, depend on the host clock, or expose
provider details in API errors.

The offline evaluation runner behavior is covered by the deterministic
integration tests:

```sh
.venv/bin/python -m pytest tests/integration/test_evaluation_runner.py
```

The runner creates a fresh provider for each case run, executes at least three
runs per case, preserves prior reports, and records failed properties.

## Evaluation workflow

The immutable version-1 corpus is:

```text
eval/cases/reminder-cases.v1.jsonl
```

It contains 15 cases covering the required clear, relative, recurrence,
follow-up, ambiguous, incomplete, invalid, contradictory, and unsupported
categories.

The module CLI is the opt-in Groq evaluation command. From `Part-1B`, with
credentials configured:

```sh
.venv/bin/python -m app.evaluation.runner \
  --cases eval/cases/reminder-cases.v1.jsonl \
  --results eval/results
```

The command performs three runs per case by default. It requires
`GROQ_API_KEY`, sends request text to Groq, and records the configured
model and SDK metadata. Do not run it as part of ordinary offline pytest
execution. The CLI does not provide a fake-provider mode; offline provider
injection is exercised through the test suite.

Reports are written as uniquely named JSON files under `eval/results/`.
Writing is append-only and does not overwrite prior evaluation evidence.
Generated results are ignored by Git.

Acceptance requires all of the following:

- Schema correctness: 100%.
- Invariant correctness: 100%.
- Semantic quality: at least 85%.
- Reliability: at least 90%.
- Weighted aggregate: at least 90%.

The approved aggregate methodology weights schema correctness at 0.25,
invariant correctness at 0.25, semantic quality at 0.30, and reliability at
0.20. A failed 100% hard gate cannot be hidden by the aggregate score.
Automated PASS is evidence only; a reviewer must inspect the specification,
corpus coverage, aggregate and per-case/run evidence, failures, and
limitations before recording an explicit decision.

The review procedure and record template are in
`docs/human-review.md`. Human approval is not generated automatically.

## Limitations and privacy

- No scheduling, persistence, snoozing side effect, or notification delivery
  is implemented.
- The service interprets one reminder intent at a time; multiple intents
  require clarification.
- Missing reference context leaves relative timing unresolved or requires
  clarification.
- Groq use is optional and external. Submitted reminder text is sent to
  Groq when the live provider is selected. Review the
  provider's current data-handling terms before sending real user data.
- Live evaluation depends on provider availability, credentials, quota, and
  network access. Offline validation remains deterministic and credential-free.
