# Part 1B Validation Quickstart

This guide describes the planned local validation workflow. It does not configure or call Gemini unless an explicit live-provider check is requested.

## Prerequisites

- Python 3.11 or newer.
- Work from the repository root so shared Spec Kit files remain separate from the Part 1B application.
- A virtual environment and the Part 1B dependency manifest created during implementation.
- No Gemini API key is needed for deterministic tests. A key is required only for the opt-in live-provider smoke check.

## Setup

After implementation creates `Part-1B/pyproject.toml`:

```sh
python3 -m venv Part-1B/.venv
Part-1B/.venv/bin/python -m pip install -e 'Part-1B[dev]'
```

Keep the Gemini key in an environment variable or an ignored local environment file. Do not commit credentials. The app and offline tests must run without this configuration.

## Deterministic validation

Run from the repository root:

```sh
Part-1B/.venv/bin/python -m pytest Part-1B/tests
```

Expected result: unit, contract, and API-integration tests pass without network access or a Gemini key. Integration tests inject a fake provider through the application dependency boundary.

Validate the versioned evaluation corpus offline:

```sh
Part-1B/.venv/bin/python -m app.evaluation.runner \
  --cases Part-1B/eval/cases/reminder-cases.v1.jsonl \
  --provider fake \
  --runs-per-case 3
```

Expected result: at least 15 cases are checked; every case runs at least three times; the report contains per-case schema, invariant, semantic, expected-behavior, reliability, and aggregate results; failures are explicit and a new run does not overwrite prior evidence. Exact CLI flags are finalized with implementation but must preserve these behaviors.

## API contract validation

Validate the OpenAPI contract at [contracts/openapi.yaml](./contracts/openapi.yaml) against request/response models and run the API test suite. A valid request to `POST /api/v1/reminders/interpret` with a fake provider returns a contract-conforming result. Requests with empty or overlong text return HTTP 422. A missing provider key returns the documented safe HTTP 503 envelope without preventing application startup.

For relative-time tests, use a fixed `reference_instant` and `time_zone`; expected local dates/times must be independent of the host clock.

## Optional live-provider check

Only when credentials, quota, and network access are available:

```sh
GEMINI_API_KEY=... Part-1B/.venv/bin/python -m app.evaluation.runner \
  --cases Part-1B/eval/cases/reminder-cases.v1.jsonl \
  --provider gemini \
  --runs-per-case 3
```

The actual key must be supplied through the local environment, not written in shell history or committed files. Record run date, selected Gemini model, SDK version, case-set version, scores, provider errors, and accepted limitations. Recheck current provider data-handling terms before sending real user requests.

## Acceptance evidence and repair

An evaluation report is acceptable only if schema correctness and invariant correctness are each 100%, semantic mean is at least 85%, overall reliability is at least 90%, and the weighted aggregate is at least 90%. Any failed hard gate fails acceptance regardless of aggregate. After a repair, rerun the complete unchanged case set and preserve both old and new results. A human reviewer records the final decision in the Part 1B review record after inspecting per-case evidence and limitations.
