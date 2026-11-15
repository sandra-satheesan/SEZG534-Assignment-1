# Part 1B Harness Log

## Offline deterministic harness

- Harness: Python test suite using injected fake providers and fixed reference
  contexts
- Command: `cd Part-1B && .venv/bin/python -m pytest`
- Run date: 2026-11-15
- Environment: macOS, Python 3.13.15

## Result

```text
189 passed, 1 warning in 0.43s
```

The warning was a Starlette deprecation warning concerning the installed
`httpx` integration. It did not cause a test failure.

The deterministic suite covers contract, integration, unit, schema,
invariant, security-scope, evaluation-runner, human-review, and repair tests.
It does not require network access, Groq credentials, or the host clock.

## Evaluation corpus and live pipeline

- Corpus: `eval/cases/reminder-cases.v1.jsonl`
- Corpus size: 15 cases
- Non-deterministic pipeline: opt-in Groq evaluation via
  `app.evaluation.runner`
- Default live configuration: three runs per case
- Live reports are append-only and preserve per-case and per-run evidence.

The live pipeline requires `GROQ_API_KEY`, network access, provider
availability, and quota. It was not run as part of the offline validation.

## Preserved failure and repair evidence

The following evaluation records are preserved under `eval/`:

- `t059-review-evidence.json`
- `t059-review-evidence-repaired.json`
- `t059-diagnostic-retry.json`
- `t059-final-verification.json`

The final verification recorded 2 passed and 1 failed scenario. NLR-004
returned a safe `provider_error` because the provider output was invalid; no
validated interpretation was available.

## Quality and acceptance status

The documented offline quality commands are:

```text
.venv/bin/python -m ruff check app tests
.venv/bin/python -m mypy app
.venv/bin/python -m bandit -c pyproject.toml -r app
```

Ruff, mypy, and Bandit were previously recorded as passing in the human-review
record. No dependency vulnerability audit was recorded.

Final human decision: **REJECT**, recorded on 2026-11-13 in
`docs/human-review.md`, because the available live evidence did not
demonstrate complete successful coverage. The main unresolved limitation is
the NLR-004 conditional follow-up provider failure.
