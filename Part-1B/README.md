# Natural-Language Reminder Agent

Part 1B is an independent Python 3.11+ service for interpreting one natural-language reminder request into validated structured data. It does not schedule reminders, persist user reminders, or deliver notifications. Part 1A remains separate and unchanged.

## Setup

From the repository root:

```sh
python3 --version
python3 -m venv Part-1B/.venv
Part-1B/.venv/bin/python -m pip install --upgrade pip
Part-1B/.venv/bin/python -m pip install -e 'Part-1B[dev]'
```

Python 3.11 or newer is required. The Gemini API key is optional for setup and offline checks. Copy the variable names from `Part-1B/.env.example` into a local, ignored environment configuration only when running a live provider check. Never commit credentials.

## Offline checks

Run from the repository root:

```sh
cd Part-1B
.venv/bin/python -m pytest
.venv/bin/ruff check app tests
.venv/bin/mypy app
.venv/bin/bandit -c pyproject.toml -r app
```

The test suite and Python modules are added in later implementation phases. Until then, pytest reports that no tests were collected, mypy reports no Python files, and Ruff/Bandit have no source files to scan. These checks do not call Gemini or require credentials.

## Privacy and live provider use

Live Gemini interpretation sends submitted reminder text to Google's Gemini service. Review the provider's current data-handling terms before sending real user requests; this project makes no provider-side retention promise. Live checks are opt-in and must use locally configured credentials, never committed files or fixtures.