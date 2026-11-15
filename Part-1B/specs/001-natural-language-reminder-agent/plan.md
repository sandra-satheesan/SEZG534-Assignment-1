# Implementation Plan: Natural-Language Reminder Agent

**Branch**: `main` (no feature branch was created) | **Date**: 2026-11-03 | **Spec**: [spec.md](./spec.md)

**Input**: Part 1B feature specification at `Part-1B/specs/001-natural-language-reminder-agent/spec.md`

## Summary

Build a Part 1B-only HTTP service that interprets natural-language reminder requests and returns validated structured data, clarification requests, or safe failure results. The service will use Python, FastAPI, Pydantic, and the Groq API, with the provider isolated behind an injectable interface so deterministic tests need neither credentials nor network access. Strict response-schema validation and explicit invariant checks will be applied to all model output before it is returned. A separate evaluation harness will run a versioned corpus of at least 15 cases repeatedly, report schema, invariant, semantic, reliability, and aggregate scores, and retain repair/re-evaluation evidence for human review.

The requested Part 1B stack conflicts with the repository constitution's Node.js/Express requirement. The user explicitly directed Python/FastAPI for this independent Part 1B application; the plan records this as a scoped, user-approved exception. No Part 1A files or behavior are in scope.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: FastAPI for HTTP handling; Pydantic 2 for strict request/response and model-output validation; the `groq` Python SDK for model integration; pytest and HTTPX for deterministic tests.

**Storage**: No reminder persistence or notification delivery. Versioned evaluation cases, run reports, and human review records are stored as files within `Part-1B/`.

**Testing**: pytest; FastAPI TestClient/HTTPX; unit tests with an injected fake model provider; offline contract and invariant tests; separate opt-in Groq smoke/evaluation runs when credentials are available.

**Target Platform**: Python 3.11+ server process on a supported developer or deployment operating system.

**Project Type**: Standalone Part 1B web service and evaluation tool.

**Performance Goals**: Deterministic validation and local fake-provider tests complete without external services. For a live provider request, return within 30 seconds or fail with a bounded, safe timeout response; model latency is external and will be reported separately from local processing.

**Constraints**: Do not require a Groq API key to import the application, start it for deterministic tests, or run the offline suite. Do not send raw provider output to clients. Validate syntax, strict schema, and cross-field invariants before returning any model interpretation. Do not log request text, API keys, or full provider responses. External Groq calls are opt-in and must use configured credentials. All application code, tests, evaluation data/results, and project documentation remain under `Part-1B/`.

**Scale/Scope**: Single-user assignment application; interpretation only, no reminder scheduling, notification delivery, or persistence of user reminders. Evaluation corpus has at least 15 cases, with at least three repeated runs per case and controlled reference context.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / constraint | Gate | Plan treatment |
|---|---|---|
| I. Maintainability | Exception required | The constitution requires Node.js/Express, while the user explicitly requires Python/FastAPI for this separately scoped Part 1B application. This is a user-approved, Part 1B-only exception; preserve modular separation among API, prompt, provider, validation, and evaluation components. |
| II. Reliability | Pass | Reject malformed model responses; use explicit errors for provider/configuration failures; do not claim a reminder was scheduled. Reminder persistence is out of scope. |
| III. RESTful API Standards | Pass | Expose a documented JSON HTTP contract with resource-oriented interpretation endpoint, consistent errors, and appropriate status codes. |
| IV. Data Integrity | Pass | Validate every request and model result; enforce state/result invariants before returning data. No task state is persisted. |
| V. Deterministic Testing | Pass | Inject a fake provider; tests control input and reference context; offline tests make no network calls or wall-clock assumptions. |
| VI. Code Quality | Pass | Define project-local Python lint/type/test commands in Part 1B; validate before acceptance. |
| VII. Security | Pass with external-service disclosure | Keep credentials in environment configuration, redact sensitive data, bound inputs/timeouts, and document that submitted reminder text is sent to Groq. |
| VIII. Traceability | Pass | Map requirements to API contract, validation rules, evaluation cases, and tests. |
| IX. Harness Independence | Pass | Keep evaluation corpus and scoring independent of provider/application internals; do not weaken thresholds to pass. |
| X. Human Accountability | Pass | Retain human review record; automated thresholds are evidence, not acceptance. |
| Technology Constraints | Exception required | Node.js/Express is not used in Part 1B due to the explicit user-selected stack; no reminder database or alternate persistence is introduced. |

**Pre-research gate**: Pass with the explicit, scoped technology exception above. The exception is justified by the user's direct instruction to use Python, FastAPI, Pydantic, and Groq for Part 1B, which is an independent workspace and does not change Part 1A.

## Architecture Decisions

1. **Provider boundary**: Define a small async provider interface whose operation accepts the prepared request/context and returns an untrusted structured candidate. The Groq adapter is one implementation; a fake provider is injected through FastAPI dependency overrides in tests. API, prompt creation, provider transport, schema validation, and evaluation remain separate modules.
2. **Structured generation is not validation**: Request schema-constrained JSON from Groq where supported, parse the returned text explicitly with Pydantic JSON validation, validate it with strict models (`extra="forbid"` and strict field types), then run domain invariants. Any parse/schema/invariant failure is a safe upstream/model-output failure; do not repair by silently coercing or exposing raw output. Keep the model-facing JSON Schema within the provider's strict structured-output subset.
3. **Reference context is explicit**: Accept optional reference instant and IANA time zone with the user request. Never read the current system clock or infer a time zone to interpret relative expressions. If the context or user wording is insufficient, return clarification/unresolved fields.
4. **No reminder side effects**: This service only interprets and returns data. It does not create, schedule, persist, snooze, or deliver reminders.
5. **Provider failures are isolated**: Missing credentials do not prevent app startup or deterministic test execution. The live endpoint reports a stable, safe service error for missing configuration, provider rejection, rate limiting, timeout, or invalid provider output. Tests assert error shape without calling Groq.
6. **Independent evaluation**: Maintain immutable, versioned case inputs and expectations; run each case at least three times with identical context. Score schema and invariant checks mechanically, score semantic quality with a documented case-specific rubric and reviewer-verifiable evidence, compute reliability and aggregate scores, and retain all per-run outputs (redacted as needed) and repairs.
7. **Reproducibility over opaque model judging**: Do not rely on another generative model as the sole evaluator. Use explicit expected properties, fixed scoring rules, and human review for semantic judgments.

## Evaluation Design

The harness will include at least 15 cases with stable IDs and category coverage from FR-014:

| Case IDs | Coverage |
|---|---|
| NLR-001–003 | Explicit date/time; relative “tomorrow”; next weekday with broad time-of-day |
| NLR-004–005 | Daily recurrence; recurrence with explicit end/boundary |
| NLR-006–007 | Conditional incomplete-task follow-up; snooze/reschedule instruction |
| NLR-008–010 | Missing date/time; ambiguous weekday/time; missing reference date or time zone |
| NLR-011–013 | Impossible date/time; contradictory timing; unsupported non-reminder request |
| NLR-014–015 | Multiple reminder intents; malformed/empty or unsupported-language input |

Each case records the input text, controlled reference context, expected status, required/forbidden fields, expected semantic facts, invariant assertions, and scoring rubric. Each run records the case-set version, run number, provider/model identifier (or fake), timestamp, raw response only in a protected/redacted artifact if retention is necessary, normalized result, failures, and scores.

Per-run measures are: (a) schema validity, (b) invariant/property validity, (c) semantic score from case-specific criteria, and (d) expected-behavior pass/fail. Semantic scoring uses four applicable dimensions—intent/title preservation, temporal interpretation, recurrence/follow-up fidelity, and uncertainty/unsupported-input handling—with anchored ratings of 0 (incorrect, missing, or invented material fact), 1 (partly correct with a material omission or ambiguity), or 2 (all expected facts preserved without material invention). The evaluator records the evidence and omits dimensions explicitly marked not applicable by that case. Semantic score is `100 × earned points / available points` across all evaluated outputs. Run at least three times per case. Reliability is the share of case-runs satisfying all case-specific expected status, required facts, forbidden-fact, and clarification properties. Report schema and invariants as pass percentages; semantic quality as a 0–100 mean; reliability as the share of case-runs passing expected behavior. Calculate a transparent weighted aggregate (schema 20%, invariants 20%, semantic 40%, reliability 20%) while keeping hard gates visible. Acceptance requires schema and invariant checks at 100%, semantic mean at least 85%, reliability at least 90%, and aggregate at least 90%; a high aggregate cannot override a failed hard gate. A repair creates a new run set against the unchanged corpus and thresholds; never overwrite earlier reports.

## Project Structure

### Documentation (this feature)

```text
Part-1B/specs/001-natural-language-reminder-agent/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── openapi.yaml
├── checklists/
│   └── requirements.md
└── tasks.md                 # Created by /speckit-tasks, not by this plan
```

### Source Code (Part 1B only)

```text
Part-1B/
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── routes/
│   │   └── errors.py
│   ├── core/
│   │   └── settings.py
│   ├── schemas/
│   │   ├── requests.py
│   │   └── responses.py
│   ├── prompts/
│   │   └── reminder_interpretation.py
│   ├── providers/
│   │   ├── base.py
│   │   └── groq.py
│   ├── services/
│   │   ├── interpreter.py
│   │   └── invariants.py
│   └── evaluation/
│       ├── runner.py
│       ├── scoring.py
│       └── reporting.py
├── eval/
│   ├── cases/
│   │   └── reminder-cases.v1.jsonl
│   └── results/
│       └── .gitkeep
├── tests/
│   ├── unit/
│   ├── contract/
│   └── integration/
├── docs/
│   └── human-review.md
├── pyproject.toml
├── .env.example
└── README.md
```

**Structure Decision**: Use one self-contained Python service under `Part-1B/app/`; keep tests, deterministic evaluation corpus/results, credentials example, and operator/reviewer documentation inside `Part-1B/`. Do not add or modify root or Part 1A application files. The API route orchestrates input validation and service invocation only; prompt building, Groq transport, strict output validation, invariant checks, and evaluation are separate responsibilities.

## Testing Strategy

- **Unit**: Validate request normalization, prompt/context serialization, strict response parsing, each invariant, status-dependent field rules, scoring math, and report serialization. Inject fake providers; never use network or system clock.
- **Contract**: Validate OpenAPI examples and request/response/error payloads against Pydantic schemas, including all result statuses and invalid payload rejection.
- **API integration**: Exercise the FastAPI application with an injected deterministic provider for ready, clarification, invalid, unsupported, malformed model output, provider exception, timeout, and missing-credential cases.
- **Evaluation harness**: Run all versioned cases at least three times; verify category coverage, exact per-case metrics, hard gates, aggregate math, and stable re-evaluation on the same corpus. Include tests proving a repair run does not overwrite prior evidence.
- **Live Groq checks**: Keep separate and opt-in; require a configured API key, use a small bounded smoke set, record model/version and date, and do not make deterministic CI depend on network, quota, or credentials.
- **Security/quality**: Run the Part 1B Python lint/type/static checks, dependency audit where available, and tests before human review; verify secrets and raw user text are absent from ordinary logs and committed fixtures/results.

## Requirement Traceability

| Specification requirements | Planned contract/design evidence | Planned verification |
|---|---|---|
| FR-001, FR-011, FR-012 | Versioned interpretation request/result and error schemas in `contracts/openapi.yaml`; Pydantic schemas | Contract tests for every result status, required/null fields, extra-field rejection, and JSON errors |
| FR-002–FR-007, FR-013 | Reminder Draft, Due Time, Recurrence, Follow-up Instruction, explicit reference context | Unit invariant tests; evaluation cases for relative timing, broad time-of-day, recurrence, follow-up, and non-invention |
| FR-008–FR-009 | Clarification questions and unresolved field representation | Deterministic API tests for missing/ambiguous date, time, reference date, and time zone |
| FR-010 | Invalid/unsupported statuses and safe provider/API error envelope | Unit and API tests for invalid dates, contradictions, unsupported input, malformed provider output, and provider failures |
| FR-014–FR-021 | Versioned 15+ case corpus, repeat runner, scoring and immutable reports | Evaluation-harness tests for category minimums, three runs/case, metrics, thresholds, aggregate math, and repair/re-evaluation |
| FR-022–FR-023 | Human Review Record and explicit acceptance gate | Record-schema tests plus a required manual reviewer decision before acceptance |
| FR-024 | Interpretation-only scope in API description and user-facing documentation | Contract/documentation tests ensure no scheduling or notification operation is exposed |
| FR-025 | Part 1B-only source, tests, and docs layout | Repository-scope checks and implementation review ensure no Part 1A changes |

## Risks and Unresolved Decisions

- **Privacy/provider retention**: Reminder text may contain personal information and is transmitted to Groq. Before deployment, disclose this to users and verify the selected Groq product's current data-handling terms; do not promise provider-side non-retention.
- **Model identifier/version**: Keep the Groq model identifier configurable and record it in every live run. Select the specific supported model during implementation setup after checking current structured-output support and project quota; this is not a blocker to the architecture.
- **Semantic score calibration**: Define anchored case-specific scoring examples before evaluating the model; human review should adjudicate disputed semantic scores.
- **Time interpretation policy**: The spec requires controlled reference context and no invented values. Exact natural-language convention decisions (for example, inclusive meaning of “next Monday”) should be pinned in evaluation expectations rather than inferred from the host locale.

## Constitution Check (Post-Design)

| Principle / constraint | Result | Evidence in design |
|---|---|---|
| I. Maintainability | Scoped exception retained | Explicit Part 1B Python/FastAPI instruction; modules have single responsibilities. |
| II. Reliability | Pass | Strict output acceptance, stable safe errors, repeated evaluation, no false scheduling success. |
| III. RESTful API Standards | Pass | OpenAPI-documented JSON endpoint and consistent HTTP errors. |
| IV. Data Integrity | Pass | Request validation and cross-field invariants before response; no reminder persistence. |
| V. Deterministic Testing | Pass | Fake-provider tests use controlled contexts and no external network or wall-clock assumptions. |
| VI. Code Quality | Pass | Part 1B-specific project commands and test/lint/type gates are planned. |
| VII. Security | Pass with operational disclosure | Secret handling, bounded requests, log redaction, and explicit Groq data-transmission disclosure. |
| VIII. Traceability | Pass | Spec IDs map to contracts, cases, scoring rules, and tests. |
| IX. Harness Independence | Pass | Versioned independent cases, immutable thresholds, and preserved rerun evidence. |
| X. Human Accountability | Pass | Human review evidence is required before acceptance. |
| Technology Constraints | Scoped exception retained | Python/FastAPI is used only in the independently scoped Part 1B workspace; no Part 1A changes. |

**Post-design gate**: Pass with the same explicit Part 1B technology exception documented above. No unresolved architecture decision blocks task generation. The Groq model identifier and evaluation rubric calibration are implementation-time configuration/details; the external-data disclosure is a deployment prerequisite.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Python/FastAPI rather than constitution-mandated Node.js/Express in Part 1B | The user explicitly selected Python, FastAPI, Pydantic, and Groq for a separate Part 1B application. | Reusing the Part 1A Node/Express stack would contradict the explicit Part 1B requirement; isolating the exception avoids changing Part 1A. |
