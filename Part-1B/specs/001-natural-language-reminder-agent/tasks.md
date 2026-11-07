---
description: "Implementation task list for the Natural-Language Reminder Agent"
---

# Tasks: Natural-Language Reminder Agent

**Input**: Design documents from `Part-1B/specs/001-natural-language-reminder-agent/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/openapi.yaml`, `quickstart.md`

**Organization**: Tasks are grouped by approved user story. Automated tests are required by the specification and constitution; offline unit, contract, integration, and evaluation tests are included. Live Gemini checks remain opt-in.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the independent Python 3.11+ project under Part 1B without changing Part 1A.

- [ ] T001 Create the `Part-1B/app`, `Part-1B/tests/unit`, `Part-1B/tests/contract`, `Part-1B/tests/integration`, `Part-1B/eval/cases`, `Part-1B/eval/results`, and `Part-1B/docs` directory structure from the plan (FR-025).
- [ ] T002 [P] Create `Part-1B/pyproject.toml` for Python 3.11+, FastAPI, Pydantic 2, `google-genai`, pytest, and HTTPX; pin compatible dependency ranges and define package discovery for the planned `app` package (FR-025).
- [ ] T003 Configure the Part-1B Python lint, type-check, test, and static-security commands in `Part-1B/pyproject.toml` after T002, without changing root or Part-1A tooling (FR-025; Constitution VI-VIII).
- [ ] T004 [P] Add `Part-1B/.env.example` with non-secret Gemini key, model identifier, and provider-timeout variable names and safe placeholder values (FR-025; Constitution VII).
- [ ] T005 [P] Add Part-1B-only ignore rules for virtual environments, local secrets, caches, and generated evaluation artifacts in `Part-1B/.gitignore` (FR-021, FR-025; Constitution VII, IX).
- [ ] T006 [P] Create `Part-1B/README.md` documenting the interpretation-only scope, Python setup, offline test commands, opt-in Gemini use, and disclosure that request text is sent to Gemini (FR-024, FR-025; Constitution VII).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build shared configuration, strict schemas, provider boundaries, and safe HTTP infrastructure required by all stories.

- [X] T007 Implement typed settings loading for optional Gemini credentials, configurable model ID, and a bounded provider timeout in `Part-1B/app/core/settings.py`; application import and startup must work without credentials (FR-010, FR-025; Constitution II, VII).
- [X] T008 [P] Implement strict request and reference-context Pydantic models in `Part-1B/app/schemas/requests.py`, including trimmed non-empty text, the 4,000-character limit, RFC 3339 offset validation, recognized IANA zone validation, and no inferred clock or zone (FR-004, FR-011, FR-025).
- [X] T009 [P] Implement strict response, reminder, due-time, recurrence, follow-up, issue, and error-envelope Pydantic models in `Part-1B/app/schemas/responses.py`; forbid extra fields and coercion and encode the documented enums/null representations (FR-001-FR-013, FR-024).
- [X] T010 [P] Add contract tests in `Part-1B/tests/contract/test_openapi_contract.py` comparing OpenAPI request, response, and error schemas/examples with the Pydantic models, including all four result statuses and unknown-field rejection (FR-001, FR-011, FR-012).
- [X] T011 [P] Add unit tests in `Part-1B/tests/unit/test_schemas.py` for required/null fields, strict types, enums, trimmed text boundaries, RFC 3339 offsets, IANA zones, and the data-model/OpenAPI reference-context and length-boundary ambiguities (FR-004, FR-011-FR-013).
- [X] T012 Define the injectable async provider protocol and provider dependency in `Part-1B/app/providers/base.py`; keep test providers independent of Gemini internals (FR-010, FR-025; Constitution V).
- [X] T013 Implement the stable safe HTTP error envelope and exception-to-status mapping in `Part-1B/app/api/errors.py` for invalid requests, provider failures, missing configuration, rate limiting, and timeout without exposing provider details (FR-010-FR-012; Constitution II, III, VII).
- [X] T014 Implement the FastAPI application factory and dependency wiring in `Part-1B/app/main.py`; expose only `POST /api/v1/reminders/interpret`, do not require credentials at startup, and expose no scheduling or notification operation (FR-001, FR-024, FR-025).
- [X] T015 [P] Add foundational app-factory and error-envelope tests in `Part-1B/tests/integration/test_app_foundation.py`, covering offline startup, dependency overrides, malformed JSON, and safe error shape (FR-010-FR-012, FR-025).
- [X] T016 Add centralized input validation/error-handler integration to `Part-1B/app/main.py` and `Part-1B/app/api/errors.py`, returning HTTP 422 for malformed or invalid request bodies as documented (FR-010-FR-012; Constitution III, IV).

**Checkpoint**: App imports and starts without Gemini credentials; strict models, error responses, and the documented endpoint contract have deterministic tests.

---

## Phase 3: User Story 1 - Create a reminder from a clear request (Priority: P1) 🎯 MVP

**Goal**: Interpret one clear request into a faithful structured reminder using only explicit temporal context.

**Independent Test**: With a fake provider and fixed reference instant/time zone, interpret explicit and relative exact times and broad time-of-day wording; verify title, local timing, schema, and absence of invented clock values.

### Tests for User Story 1

- [X] T017 [P] [US1] Add unit tests in `Part-1B/tests/unit/test_prompt.py` for prompt serialization of request text and explicit reference context, requiring no host clock or implicit time zone (FR-004, FR-005, FR-013).
- [X] T018 [P] [US1] Add deterministic endpoint integration tests in `Part-1B/tests/integration/test_interpret_ready.py` for explicit date/time, “tomorrow at 10 AM,” and “next Monday evening,” using an injected fake provider (FR-001-FR-005, FR-011, FR-013).
- [X] T019 [P] [US1] Add endpoint contract tests in `Part-1B/tests/contract/test_interpret_endpoint.py` for `POST /api/v1/reminders/interpret`, the ready response example, content type, and schema version (FR-001, FR-002, FR-011, FR-012).

### Implementation for User Story 1

- [X] T020 [P] [US1] Implement the reminder-interpretation prompt builder in `Part-1B/app/prompts/reminder_interpretation.py`, requiring one intent, faithful title extraction, exact-versus-broad time distinction, and no unsupported facts (FR-002-FR-005, FR-013, FR-024).
- [X] T021 [P] [US1] Implement the async Gemini structured-output adapter in `Part-1B/app/providers/gemini.py`, using the configured model and timeout and returning untrusted candidate output without exposing credentials or raw output (FR-010, FR-011, FR-013; Constitution II, VII).
- [X] T022 [US1] Implement the initial interpretation service in `Part-1B/app/services/interpreter.py`, assembling prompt/context, invoking the injected provider, parsing with strict response models, and returning only schema-valid results (FR-001-FR-005, FR-011-FR-013).
- [X] T023 [US1] Add the `POST /api/v1/reminders/interpret` route in `Part-1B/app/api/routes/reminders.py` and wire it in `Part-1B/app/main.py` to return the documented response without side effects (FR-001-FR-005, FR-011, FR-024).

**Checkpoint**: User Story 1 passes using fake-provider tests with no network, API key, host-clock dependency, or reminder side effect.

---

## Phase 4: User Story 2 - Clarify incomplete or ambiguous requests (Priority: P1)

**Goal**: Ask focused questions and keep unresolved values unset instead of guessing.

**Independent Test**: Submit missing date/time, ambiguous date/time, and missing reference context cases; verify `needs_clarification`, specific questions, unresolved fields, and non-ready state.

### Tests for User Story 2

- [X] T024 [P] [US2] Add unit tests in `Part-1B/tests/unit/test_clarification.py` for missing date/time, ambiguous weekday/time, and absent reference instant or zone, including required question and unresolved-field behavior (FR-004, FR-008, FR-009, FR-013).
- [X] T025 [P] [US2] Add fake-provider endpoint integration tests in `Part-1B/tests/integration/test_interpret_clarification.py` verifying incomplete and ambiguous requests return HTTP 200 with a contract-valid `needs_clarification` result (FR-008, FR-009, FR-011, FR-012).

### Implementation for User Story 2

- [X] T026 [US2] Implement clarification and unresolved-field invariant checks in `Part-1B/app/services/invariants.py`, rejecting ready results with missing required information or clarification questions (FR-008, FR-009, FR-013).
- [X] T027 [US2] Extend `Part-1B/app/prompts/reminder_interpretation.py` to ask concise questions for absent or materially ambiguous information and to preserve unresolved values as null (FR-004, FR-008, FR-009, FR-013).
- [X] T028 [US2] Integrate clarification invariants into `Part-1B/app/services/interpreter.py` and map violations to safe provider/model-output failures rather than silently repairing output (FR-009-FR-013; Constitution II, IV).

**Checkpoint**: User Story 2 independently returns valid clarification results and never presents unresolved reminders as ready.

---

## Phase 5: User Story 3 - Capture recurrence and follow-up instructions (Priority: P2)

**Goal**: Preserve recurrence boundaries, snooze/reschedule details, and conditional follow-ups separately from primary due time.

**Independent Test**: Interpret daily recurrence, explicit recurrence boundaries, and conditional follow-up requests with fixed context; verify exact fields and no invented boundaries or conditions.

### Tests for User Story 3

- [X] T029 [P] [US3] Add unit tests in `Part-1B/tests/unit/test_recurrence_followups.py` for supported frequencies, interval defaults, weekdays, ends/counts, snooze/reschedule delays, conditions, and unsupported or contradictory patterns (FR-006, FR-007, FR-013).
- [X] T030 [P] [US3] Add fake-provider endpoint integration tests in `Part-1B/tests/integration/test_interpret_recurrence_followups.py` for daily recurrence, explicit recurrence end, and incomplete-task follow-up (FR-006, FR-007, FR-011-FR-013).

### Implementation for User Story 3

- [X] T031 [US3] Implement recurrence and follow-up cross-field invariants in `Part-1B/app/services/invariants.py`, including no invented end/count, positive normalized delays, and conditions represented only when stated (FR-006, FR-007, FR-013).
- [X] T032 [US3] Extend `Part-1B/app/prompts/reminder_interpretation.py` to preserve recurrence frequency/boundaries and separate snooze, rescheduling, and conditional follow-up instructions (FR-006, FR-007, FR-013).
- [X] T033 [US3] Integrate recurrence/follow-up validation into `Part-1B/app/services/interpreter.py`, rejecting unsupported patterns as clarification or safe issue results rather than dropping details (FR-006, FR-007, FR-010, FR-013).

**Checkpoint**: User Story 3 preserves recurrence and follow-up fields and rejects contradictions without modifying the primary due time.

---

## Phase 6: User Story 4 - Receive safe handling of invalid or unsupported requests (Priority: P2)

**Goal**: Return structured invalid/unsupported results for semantic problems and safe HTTP errors for transport/provider failures.

**Independent Test**: Exercise impossible dates, contradictory timing, unsupported requests, multiple intents, malformed model output, missing credentials, provider exceptions, rate limiting, and timeout; verify documented statuses/envelopes and no false ready result.

### Tests for User Story 4

- [X] T034 [P] [US4] Add unit tests in `Part-1B/tests/unit/test_invariants.py` for ready, clarification, invalid, and unsupported status invariants, impossible timing, contradictions, and rejection of malformed or extra provider fields (FR-009-FR-013).
- [X] T035 [P] [US4] Add deterministic endpoint integration tests in `Part-1B/tests/integration/test_interpret_failures.py` for invalid dates, contradictions, unsupported input, multiple intents, malformed provider output, provider rejection/rate limit, timeout, and missing credentials (FR-010-FR-013, FR-024).
- [X] T036 [P] [US4] Extend `Part-1B/tests/contract/test_interpret_endpoint.py` to validate HTTP 422, 502, 503, and 504 error envelopes against OpenAPI and ensure provider details are absent (FR-010-FR-012; Constitution II, III, VII).

### Implementation for User Story 4

- [X] T037 [US4] Complete status-dependent result invariants in `Part-1B/app/services/invariants.py`, requiring issues for invalid/unsupported results and forbidding ready status with blocking issues (FR-001, FR-009-FR-013).
- [X] T038 [US4] Extend `Part-1B/app/prompts/reminder_interpretation.py` to identify impossible dates/times, contradictions, unsupported requests, and multi-intent requests without claiming scheduling (FR-010, FR-013, FR-024).
- [X] T039 [US4] Map Gemini configuration, provider, rate-limit, timeout, parse, schema, and invariant failures to stable safe errors in `Part-1B/app/providers/gemini.py` and `Part-1B/app/api/errors.py` (FR-010-FR-012; Constitution II, VII).
- [X] T040 [US4] Ensure `Part-1B/app/services/interpreter.py` rejects truncated, malformed, invalid-schema, and invariant-failing model output without coercion, partial recovery, or raw passthrough (FR-010-FR-013; Constitution II, IV).

**Checkpoint**: All semantic and provider failure paths are distinguishable, safe, contract-valid where applicable, and cannot appear as successful scheduling.

---

## Phase 7: User Story 5 - Evaluate and accept interpretation quality (Priority: P1)

**Goal**: Reproduce quality measurements across a versioned corpus and retain evidence for repair and explicit human review.

**Independent Test**: Run at least 15 fixed cases three times each with the fake provider; verify category coverage, per-case results, metric math, thresholds, immutable reruns, and that automated PASS does not record human acceptance.

### Tests for User Story 5

- [ ] T041 [P] [US5] Add unit tests in `Part-1B/tests/unit/test_evaluation_scoring.py` for anchored semantic dimensions, schema/invariant percentages, expected-behavior reliability, weighted aggregate math, and independent hard gates (FR-016-FR-019).
- [ ] T042 [P] [US5] Add unit tests in `Part-1B/tests/unit/test_evaluation_cases.py` validating stable IDs, required categories, fixed reference contexts, required/forbidden facts, rubrics, and a minimum 15-case corpus (FR-014, FR-018, FR-021).
- [ ] T043 [P] [US5] Add unit tests in `Part-1B/tests/unit/test_human_review.py` validating reviewer identity, date, run/case-set references, explicit approved/rejected decision, findings, and limitations (FR-022, FR-023).
- [ ] T044 [P] [US5] Add evaluation integration tests in `Part-1B/tests/integration/test_evaluation_runner.py` verifying three runs per case, full case-set reruns, explicit failures, and preservation of prior run evidence (FR-015, FR-020, FR-021).

### Implementation for User Story 5

- [ ] T045 [P] [US5] Create immutable version-1 JSONL cases with stable IDs NLR-001–NLR-015, fixed temporal contexts, expected properties, invariant assertions, rubric dimensions, and FR-014 category coverage in `Part-1B/eval/cases/reminder-cases.v1.jsonl` (FR-014, FR-018, FR-021).
- [ ] T046 [US5] Implement versioned case loading and category/expectation validation in `Part-1B/app/evaluation/cases.py` (FR-014, FR-021).
- [ ] T047 [P] [US5] Implement deterministic schema, invariant, semantic-rubric, and expected-behavior scoring in `Part-1B/app/evaluation/scoring.py`, including schema/invariant 100%, semantic 85%, reliability 90%, and weighted aggregate 90% gates (FR-016-FR-019).
- [ ] T048 [US5] Implement repeat execution in `Part-1B/app/evaluation/runner.py` for at least three runs per case with injectable fake/Gemini provider, fixed contexts, recorded provider/model/SDK versions, and complete unchanged-corpus reruns (FR-015, FR-020, FR-021).
- [ ] T049 [US5] Implement append-only report serialization and per-case failure evidence in `Part-1B/app/evaluation/reporting.py`; write uniquely named artifacts under `Part-1B/eval/results/` without overwriting prior runs or logging secrets/unnecessary raw text (FR-015, FR-020, FR-021; Constitution VII, IX).
- [ ] T050 [US5] Add human review record template and acceptance procedure in `Part-1B/docs/human-review.md`, requiring review of coverage, per-case/aggregate evidence, limitations, and explicit decision after thresholds pass (FR-022, FR-023; Constitution X).
- [ ] T051 [US5] Add a separate opt-in Gemini smoke/evaluation command in `Part-1B/app/evaluation/runner.py` that requires configured credentials, uses bounded requests, records model/date, and never runs as part of offline tests (FR-015-FR-021; Constitution V, VII).

**Checkpoint**: Offline evaluation is reproducible and complete; live Gemini is opt-in; prior reports remain intact; acceptance still requires human review.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Verify documentation, security, traceability, usability, and final acceptance gates across all stories.

- [ ] T052 [P] Add tests for log redaction, request-length limits, timeout bounds, absence of credentials/raw request text in ordinary logs, and no reminder persistence or notification routes in `Part-1B/tests/integration/test_security_scope.py` (FR-024, FR-025; Constitution II, VII).
- [ ] T053 [P] Add deterministic temporal edge-case tests for month/year boundaries, daylight-saving transitions, “next Monday” policy, and controlled reference context in `Part-1B/tests/unit/test_temporal_edges.py` (FR-004, FR-005, FR-013).
- [ ] T054 Update `Part-1B/README.md` with final install, server, test, evaluation, opt-in live-check, privacy, and human-review commands consistent with `Part-1B/specs/001-natural-language-reminder-agent/quickstart.md` (FR-021-FR-025).
- [ ] T055 Run all Part-1B unit, contract, and integration tests using the test configuration in `Part-1B/pyproject.toml`; fix implementation defects without weakening tests and preserve deterministic offline execution (FR-001-FR-025; Constitution V, VI).
- [ ] T056 Run configured lint, type, static-security, and dependency-audit commands from `Part-1B/pyproject.toml`; resolve findings in Part-1B implementation files without weakening tests or acceptance thresholds (FR-025; Constitution VI-IX).
- [ ] T057 Validate every OpenAPI operation/example against generated response behavior and verify that no scheduling, persistence, or notification operation is exposed in `Part-1B/tests/contract/test_openapi_contract.py` (FR-011, FR-012, FR-024).
- [ ] T058 Validate the commands and expected outcomes in `Part-1B/specs/001-natural-language-reminder-agent/quickstart.md` and record any command adjustments only in implementation configuration or `Part-1B/README.md` (FR-021, FR-024, FR-025).
- [ ] T059 Conduct the specified usability review with five representative users, verify at least four can identify title, timing, recurrence/follow-up, and clarification from results, and record evidence in `Part-1B/docs/human-review.md` (SC-007, FR-022, FR-023).
- [ ] T060 Complete human acceptance review using the evaluation reports, requirement traceability, quality checks, and documented limitations; record an explicit approved/rejected decision in `Part-1B/docs/human-review.md` (FR-022, FR-023; Constitution VIII, X).

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; all tasks are Part-1B-only. T002 establishes the package configuration before dependency installation or project checks.
- **Foundational (Phase 2)**: Depends on project setup. T007-T016 establish configuration, schemas, provider boundary, error mapping, and app factory; this phase blocks all stories.
- **User Stories (Phases 3-7)**: Depend on the foundation. US1 establishes the endpoint and baseline interpretation; US2-US4 add clarification, recurrence/follow-up, and safe failure behavior. US5's complete evaluation depends on the implemented behaviors of US1-US4.
- **Polish (Phase 8)**: Depends on the desired stories and evaluation harness being complete. T059-T060 require completed reports and implementation evidence.

### User Story Dependencies

- **US1 (P1)**: Starts after Phase 2; no dependency on another story. It is the MVP.
- **US2 (P1)**: Starts after Phase 2 and builds on US1's endpoint and interpreter.
- **US3 (P2)**: Starts after Phase 2 and builds on the common result schema and US1 interpreter; it can be developed alongside US2 if changes to shared prompt/service files are coordinated.
- **US4 (P2)**: Starts after Phase 2; endpoint/error infrastructure is foundational, while this story adds semantic-invalid and provider/model-output handling. Integrates with US2/US3 invariants.
- **US5 (P1)**: Corpus and scoring unit tasks can begin after setup, but full runner integration and acceptance depend on US1-US4 and stable response/invariant contracts.

### Parallel Opportunities

- Setup T002-T006 can be authored in parallel after T001; avoid simultaneous edits to `pyproject.toml` between T002 and T003.
- Foundational schema tests (T010-T011), provider interface (T012), and app-factory tests (T015) can proceed independently once their corresponding interface files are agreed; T014/T016 share `app/main.py` and should be coordinated.
- Within each story, independent unit, contract, and integration test files can be written in parallel before implementation. Prompt, service, and invariant changes share files and should be sequenced or coordinated rather than run concurrently.
- US2 and US3 feature tests/case design may proceed in parallel; their prompt/service/invariant implementation tasks touch shared files and require coordination.
- US5 scoring, corpus validation, and human-review record tests use separate files and can proceed in parallel. Runner/report implementation must follow the agreed case and scoring formats.
- Polish security and temporal tests can proceed in parallel; final quickstart validation, usability review, and human acceptance depend on completed implementation evidence.

## Parallel Example: User Story 1

```text
After Phase 2 completes, write in parallel:
- T017: prompt serialization unit tests in Part-1B/tests/unit/test_prompt.py
- T018: ready-result endpoint integration tests in Part-1B/tests/integration/test_interpret_ready.py
- T019: endpoint contract tests in Part-1B/tests/contract/test_interpret_endpoint.py

Then implement prompt construction and provider transport (T020-T021), followed by the interpreter and route (T022-T023). Run the US1 test files before proceeding to US2.
```

## Implementation Strategy

### MVP First (User Story 1)

1. Complete setup and foundational tasks.
2. Implement US1 using the fake provider and fixed reference context.
3. Run US1 unit, contract, and integration tests offline; do not require Gemini credentials.
4. Stop for human review of the MVP behavior; automated PASS alone is not acceptance.

### Incremental Delivery

1. Add US2 clarification behavior and verify unresolved values remain unset.
2. Add US3 recurrence and follow-up behavior and verify no unsupported details are invented.
3. Add US4 invalid/unsupported and provider-failure handling and verify safe outcomes.
4. Add US5's versioned repeated evaluation, scoring, retained reports, and explicit human-review record.
5. Run all deterministic quality gates, then optionally run bounded live Gemini evaluation when credentials and quota are available.

## Notes

- All tasks use the required checkbox, sequential ID, optional `[P]`, story label for story phases, and explicit file path format.
- Each task names the specification requirement(s) it implements or verifies; cross-cutting and policy tasks also cite constitution principles or success criteria where relevant.
- The plan records a scoped, user-approved Python/FastAPI exception to the Node.js/Express constitution; tasks remain isolated to Part 1B and do not alter the constitution or Part 1A.
- Existing design artifacts have two details that need a consistent implementation/test interpretation: the data model makes `reference_context` optional while OpenAPI requires the field but permits null; and the data model measures the 4,000-character limit after trimming while OpenAPI constrains the submitted string. Task T011 explicitly tests both boundaries. This task file does not revise either artifact.
- Research also requires the 4,000-character maximum to be documented in the API contract; OpenAPI currently specifies `maxLength: 4000`, so that requirement is represented and tested by T008, T011, and T057.