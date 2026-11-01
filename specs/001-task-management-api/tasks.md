# Tasks: Smart Todo & Task Management API

**Input**: Design documents from `specs/001-task-management-api/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/openapi.yaml`

**Organization**: Tasks are grouped by approved user story. Automated tests are
required by FR-016 and the constitution; test tasks are included for every story
and cross-cutting acceptance criterion.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize the approved Node.js 24 / npm / ESM project and independent
quality tools.

- [ ] T001 Create the Node.js 24 ESM npm project manifest and lockfile with Express 5, Jest, Supertest, ESLint, and pinned Semgrep dependencies in `package.json` and `package-lock.json`
- [ ] T002 [P] Configure the ESLint flat configuration and the `lint` script in `eslint.config.js` and `package.json`
- [ ] T003 [P] Add reviewed local Semgrep rules and a pinned, separately invokable `security` script in `contracts/semgrep.yml` and `package.json`
- [ ] T004 Create source, test, acceptance, and runtime-data directory placeholders without committing task data in `src/.gitkeep`, `tests/unit/.gitkeep`, `tests/integration/.gitkeep`, `acceptance/.gitkeep`, and `data/.gitkeep`

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared infrastructure required by all user stories.

- [ ] T005 Create the Express app factory with dependency/config injection and no listening side effect in `src/app.js`
- [ ] T006 [P] Define typed application errors for validation, missing resources, oversized requests, and persistence failures in `src/errors/app-error.js`
- [ ] T007 Implement centralized error handling that emits the documented `{ "error": { "code", "message" } }` JSON envelope, maps HTTP statuses, and hides internal details in `src/middleware/error-handler.js`
- [ ] T008 Implement shared request validation middleware for JSON object shape, allowed fields, enums, required/non-empty text, and empty-update rejection in `src/validation/tasks.validation.js`
- [ ] T009 Enforce a 10 KiB (10,240-byte) JSON request-body limit and map oversized bodies to HTTP 413 in `src/app.js` and `src/middleware/error-handler.js`
- [ ] T010 Implement JSON task repository initialization, parsing, stored-shape validation, and explicit read/parse errors in `src/persistence/json-task.repository.js`
- [ ] T011 Implement in-process serialized repository mutations and same-directory temporary-file replacement; preserve the prior file on failure and do not claim multi-process write support in `src/persistence/json-task.repository.js`
- [ ] T012 Implement server startup, `TASKS_FILE` configuration, ephemeral-port support, readiness signaling, and graceful shutdown in `src/server.js`
- [ ] T013 Add Jest configuration for Node.js ESM and isolated unit/integration suites in `jest.config.js`
- [ ] T014 Add an independent in-repository acceptance runner that starts/stops the server and calls only public loopback HTTP routes in `acceptance/run-acceptance.js`

## Phase 3: User Story 1 - Create and review tasks (Priority: P1) 🎯 MVP

**Goal**: Create tasks with unique IDs and retrieve one or all tasks using the
documented response contract.

**Independent Test**: With a fresh temporary JSON file, create a valid task,
retrieve the collection and that task by its returned ID, and verify fields, unique
ID, pending default, response envelopes, and persisted data. Invalid creation must
return a client error without creating a record.

### Tests for User Story 1

- [ ] T015 [P] [US1] Test task creation required fields, whitespace validation, pending default, and invalid supplied initial status for FR-001 and FR-010 in `tests/unit/tasks.create.test.js` and `tests/integration/tasks.create.test.js`
- [ ] T016 [P] [US1] Test UUID uniqueness, list retrieval, ID retrieval, success envelopes, and 404 for an unknown read ID for FR-002, FR-003, FR-011, and FR-012 in `tests/unit/tasks.identity.test.js` and `tests/integration/tasks.read.test.js`
- [ ] T017 [P] [US1] Black-box test task creation, unique IDs, list/get routes, pending default, validation outcomes, JSON envelopes, and create/read restart persistence for FR-001, FR-002, FR-003, FR-010, FR-012, FR-013, FR-015, and FR-016 using public HTTP in `acceptance/tasks.create-read.acceptance.test.js`
- [ ] T018 [P] [US1] Test JSON first-run initialization and malformed, unreadable, and unwritable persistence errors without success-shaped responses for FR-014 in `tests/integration/json-task.repository.test.js`
- [ ] T019 [P] [US1] Test JSON bodies at 10 KiB and above 10 KiB, expecting valid-boundary handling and HTTP 413 without mutation for TD-03 in `tests/integration/request-size.test.js`
- [ ] T020 [P] [US1] Test rejection of unknown create properties with HTTP 400 and no task creation for TD-04 in `tests/integration/tasks.validation.test.js`
- [ ] T021 [P] [US1] Test create-time tag trimming, whitespace-only tag rejection, case-sensitive duplicate removal, and first-occurrence order for TD-05 in `tests/unit/tasks.validation.test.js`

### Implementation for User Story 1

- [ ] T022 [P] [US1] Define the Task, Priority, and Status constants and field validation rules from `data-model.md` in `src/models/task.js`
- [ ] T023 [US1] Implement task creation with Node.js 24 `crypto.randomUUID()`, collision checking, and pending default in `src/services/tasks.service.js`
- [ ] T024 [US1] Implement collection and ID retrieval through the JSON repository in `src/services/tasks.service.js`
- [ ] T025 [US1] Add task routes for `POST /api/tasks`, `GET /api/tasks`, and `GET /api/tasks/:id` in `src/routes/tasks.routes.js`
- [ ] T026 [US1] Map create/list/get requests to documented JSON success envelopes and create `Location` header in `src/controllers/tasks.controller.js`
- [ ] T027 [US1] Wire task routes, validation middleware, JSON body-size handling, and centralized errors in `src/app.js`
- [ ] T028 [US1] Register the isolated User Story 1 black-box acceptance suite as a separately invokable npm script in `package.json`

**Checkpoint**: User Story 1 passes independently against a fresh isolated JSON
file. Creation and retrieval return documented responses and unique IDs.

## Phase 4: User Story 2 - Maintain task details and status (Priority: P1)

**Goal**: Partially update task details, enforce valid forward-only status changes,
and delete tasks without corrupting persisted state.

**Independent Test**: Create a task, update supplied fields, verify unspecified
fields remain unchanged, advance pending → in-progress → completed, reject invalid
transitions without mutation, delete the task, and verify nonexistent update/delete
return 404.

### Tests for User Story 2

- [ ] T029 [P] [US2] Test partial update field validation, unchanged omitted fields, completed-task detail edits that preserve completed status, empty update rejection, and unknown-property HTTP 400 with no mutation for FR-004 and TD-04 in `tests/unit/tasks.update.test.js` and `tests/integration/tasks.update.test.js`
- [ ] T030 [P] [US2] Test allowed transitions and skipped, reversed, repeated, and post-completion backward transitions, verifying completed-task detail edits preserve status and rejected transitions leave the entire stored task unchanged for FR-008 in `tests/unit/tasks.transitions.test.js` and `tests/integration/tasks.transitions.test.js`
- [ ] T031 [P] [US2] Test delete success, 404 for nonexistent update/delete, and persistence error responses for FR-005, FR-011, and FR-014 in `tests/integration/tasks.delete.test.js`
- [ ] T032 [P] [US2] Black-box test partial updates, completed-task title/description/priority/tag edits that retain completed status, deletion, documented success responses, and update/delete persistence across restart for FR-004, FR-005, FR-008, FR-012, FR-013, FR-015, and FR-016 using public HTTP in `acceptance/tasks.update-delete.acceptance.test.js`

### Implementation for User Story 2

- [ ] T033 [US2] Implement atomic partial task updates, including editable title, description, priority, and tags after completion while preserving completed status, and validate a candidate task before persistence for FR-004 in `src/services/tasks.service.js`
- [ ] T034 [US2] Enforce only pending → in-progress → completed transitions and reject repeated, skipped, reversed, or backward transitions without persisting any update; detail edits after completion must retain completed status for FR-008 in `src/services/tasks.service.js`
- [ ] T035 [US2] Implement task deletion through the serialized JSON repository in `src/services/tasks.service.js`
- [ ] T036 [US2] Add `PATCH /api/tasks/:id` and `DELETE /api/tasks/:id` routes in `src/routes/tasks.routes.js`
- [ ] T037 [US2] Map update and delete outcomes to documented JSON envelopes and status codes in `src/controllers/tasks.controller.js`
- [ ] T038 [US2] Black-box test valid/invalid/backward status transitions, completed-task status preservation, 404 update/delete behavior, status codes, and error envelopes for FR-008, FR-010, FR-011, FR-012, FR-015, and FR-016 through public HTTP in `acceptance/tasks.transitions.acceptance.test.js`

**Checkpoint**: User Stories 1 and 2 pass independently; invalid transitions and
missing IDs leave persisted state unchanged and return the specified errors.

## Phase 5: User Story 3 - Find and prioritize tasks (Priority: P2)

**Goal**: Filter tasks by status, priority, and normalized tags, and sort results
high-to-low by priority with stable ties.

**Independent Test**: Seed isolated tasks with known statuses, priorities, and
normalized tags; verify each filter, AND combinations, all-requested-tags matching,
empty results, and stable priority ordering.

### Tests for User Story 3

- [ ] T039 [P] [US3] Test status, priority, and combined filter semantics including an empty result for FR-006 in `tests/unit/tasks.filters.test.js` and `tests/integration/tasks.filters.test.js`
- [ ] T040 [P] [US3] Test high-to-low priority ordering, stable ties, and invalid priority/sort query rejection for FR-007 in `tests/unit/tasks.sort.test.js` and `tests/integration/tasks.sort.test.js`
- [ ] T041 [P] [US3] Test repeated tag filters require all requested tags, trim query tags, remove case-sensitive duplicate query values, and distinguish case for FR-009 and TD-05 in `tests/unit/tasks.tags.test.js` and `tests/integration/tasks.tags.test.js`
- [ ] T042 [P] [US3] Black-box test status/priority/tag filters, AND semantics, all-tag matching, normalized case-sensitive tags, stable sorting, empty results, query validation, and response envelopes for FR-006, FR-007, FR-009, FR-010, FR-012, FR-015, and FR-016 using public HTTP in `acceptance/tasks.filters.acceptance.test.js`

### Implementation for User Story 3

- [ ] T043 [US3] Validate allowed `status`, `priority`, repeated `tag`, and `sort=priority` query parameters in `src/validation/tasks.validation.js`
- [ ] T044 [US3] Implement AND-combined filters, all-tags matching, normalized case-sensitive tags, and stable high-to-low priority sorting without reordering persisted data in `src/services/tasks.service.js`
- [ ] T045 [US3] Map validated task-list query parameters to service filters and return the standard collection envelope in `src/controllers/tasks.controller.js`
- [ ] T046 [US3] Register the isolated filter acceptance suite in the independent black-box runner without importing application modules in `acceptance/run-acceptance.js`

**Checkpoint**: All user stories pass independently against isolated fixtures and
the public API contract.

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verify shared quality gates, full traceability, and restart acceptance
without weakening the harness or requirements.

- [ ] T047 [P] Add tests for two simultaneous mutations within one process and verify both persist without lost updates; do not add multi-process guarantees in `tests/integration/json-task.repository.concurrency.test.js`
- [ ] T048 [P] Verify the supported runtime and dependency baseline is Node.js 24, npm, ESM, and Express 5 in `tests/integration/runtime-baseline.test.js`
- [ ] T049 Add and run the independent black-box restart suite with 100 consecutive checks that each save task data, restart the real server, and verify the unchanged task through public HTTP for SC-004, FR-013, and FR-016; record invocation/results in `acceptance/tasks.restart.acceptance.test.js` and `acceptance/README.md`
- [ ] T050 Run Jest, ESLint, and the pinned Semgrep scan; address findings without weakening acceptance assertions in the relevant files, including `package.json`
- [ ] T051 Review the FR-to-test mapping, OpenAPI contract, and harness independence; record human review evidence in `specs/001-task-management-api/acceptance-review.md`
- [ ] T052 Validate the documented commands and expected outcomes in `specs/001-task-management-api/quickstart.md`
- [ ] T053 [P] Add public-HTTP black-box tests for malformed and invalid requests, unknown properties (400), oversized bodies (413), consistent success/error envelopes, and controlled malformed/unreadable/unwritable JSON fixtures that produce safe observable persistence errors (500) without false success or mutation for FR-010, FR-012, FR-014, FR-015, and FR-016 in `acceptance/tasks.errors.acceptance.test.js`

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; T001 precedes dependency installation and
  scripts that rely on package metadata. T002–T004 can proceed independently after
  the initial project layout is available.
- **Foundational (Phase 2)**: Depends on Setup. The app, validation, error mapping,
  JSON repository, server lifecycle, and independent harness runner block story work.
- **User Stories (Phases 3–5)**: Depend on the foundational phase. User Story 1 and
  User Story 2 are both P1; User Story 3 is P2. Stories share the foundation but are
  organized and independently verified by user value.
- **Polish (Phase 6)**: Depends on all three story checkpoints.

### User Story Dependencies

- **US1 (P1)**: Depends on the shared app, validation, error, and persistence
  foundation. It is the MVP; no other story is required to demonstrate create/read.
- **US2 (P1)**: Depends on US1's Task entity, service, repository, and routes, because
  updates and deletes operate on existing tasks.
- **US3 (P2)**: Depends on US1's Task entity, list route, and repository. It does not
  require US2's update/delete behavior.

### Within Each User Story

- Write the story's deterministic unit/integration/acceptance tests before story
  implementation; confirm they fail for the intended missing behavior.
- Keep each test file in its own task; test files marked `[P]` can be authored in
  parallel after the foundation exists.
- Complete service behavior before mapping the corresponding route/controller
  behavior.
- Do not mark a story complete until its independent test criteria pass.

### Parallel Opportunities

- After T001, ESLint configuration (T002) and Semgrep rules (T003) can be prepared
  independently; source/test directory placeholders (T004) are also independent.
- After shared foundations, independent test files within each user story can be
  created in parallel.
- US3 filter tests and service work can proceed after the US1 list endpoint exists,
  while US2 update/delete work proceeds separately; edits to shared service/routes
  files must be coordinated to avoid conflicts.
- Runtime-baseline verification and single-process concurrency tests can proceed in
  parallel during polish.
- Acceptance tests remain separate from application internals and must never be
  edited or weakened just to make implementation pass.

## Parallel Example: User Story 1

```text
After Phase 2 completes, write in parallel:
- T015: creation unit and HTTP tests in tests/unit/tasks.create.test.js and tests/integration/tasks.create.test.js
- T016: identity unit and read/response HTTP tests in tests/unit/tasks.identity.test.js and tests/integration/tasks.read.test.js
- T017: restart acceptance tests in acceptance/tasks.create-read.acceptance.test.js
- T018: persistence failure tests in tests/integration/json-task.repository.test.js
- T019: body-size tests in tests/integration/request-size.test.js
- T020: unknown-property tests in tests/integration/tasks.validation.test.js
- T021: tag normalization unit tests in tests/unit/tasks.validation.test.js
Then implement T022–T027, run the focused suites, and complete T028 against HTTP.
```

## Implementation Strategy

### MVP First (User Story 1)

1. Complete setup and foundational tasks.
2. Implement and independently test User Story 1 only.
3. Verify unique IDs, required-field validation, documented JSON responses, and
   create/read persistence.
4. Stop for human review; automated PASS alone is not acceptance.

### Incremental Delivery

1. Add US1 to provide create/list/get MVP value and verify it independently.
2. Add US2 for safe updates, legal status progression, and deletion.
3. Add US3 for filtering and sorting.
4. Run all deterministic tests, lint, static security checks, and the independent
   restart harness without changing its assertions to fit implementation.

## Notes

- Every task uses the required checklist form: checkbox, sequential ID, optional
  `[P]`, story label only in story phases, and an explicit file path.
- `[P]` means the task can proceed independently without editing the same file as
  another parallel task.
- Story task descriptions reference functional requirements and approved technical
  decisions to preserve traceability.
- No application source files are created by this task-generation phase.
