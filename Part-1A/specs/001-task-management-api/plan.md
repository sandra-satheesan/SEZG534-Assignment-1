# Implementation Plan: Smart Todo & Task Management API

**Branch**: `main` (feature ID: `001-task-management-api`) | **Date**: 2026-10-31 | **Spec**: [spec.md](./spec.md)

**Input**: Approved feature specification in `specs/001-task-management-api/spec.md`

## Summary

Deliver the approved shared task-management REST API through a layered Node.js and
Express service. Routes map HTTP requests to controllers; controllers use centralized
validation and delegate task rules to a service; the service persists through a
JSON-file repository. A consistent JSON contract, atomic file replacement, and
separate deterministic unit, integration, and black-box restart acceptance tests
address the specification's reliability and data-integrity requirements.

## Technical Context

**Language/Version**: Node.js 24.

**Primary Dependencies**: Express 5; npm with a committed lockfile; ESM; Jest and
Supertest for deterministic unit and HTTP integration tests; ESLint; pinned Semgrep
CLI with a reviewed local JavaScript ruleset.

**Storage**: One JSON file containing an ordered task array. Default location:
`data/tasks.json`; allow `TASKS_FILE` to select an isolated file for tests and
deployment configuration.

**Testing**: Jest for unit and integration suites; Supertest for the app's HTTP
contract; a separately invoked black-box acceptance suite for actual process restart
and persistence. Use unique temporary directories and files per test.

**Target Platform**: Node.js 24 on the course-supported development and deployment
platforms; file replacement behavior must be tested on supported platforms.

**Project Type**: Single-project REST web service.

**Performance Goals**: No throughput or latency target is defined by the approved
specification. Acceptance is based on correctness and deterministic persistence
checks, not a new performance threshold.

**Constraints**: JSON-file persistence only; one shared task collection; no
authentication or per-user ownership; exactly one writer process, with mutations
serialized within that process; multi-process writes are out of scope; JSON request
bodies are limited to 10 KiB (10,240 bytes); no external network dependency in
automated tests; no success response for failed persistence operations.

**Scale/Scope**: Single-process service and one task collection for the specified
create/read/update/delete/filter/sort use cases. Multi-process writers are out of
scope. Multi-tenant behavior and migration of legacy data are also out of scope.

## Constitution Check

### Pre-Design Gate

- **Maintainability**: Pass. The planned routes/controllers/services/repository
  separation gives each layer a single responsibility.
- **Reliability**: Pass. A single JSON representation, serialized mutations, and
  same-directory temp-file replacement prevent handled partial writes from being
  reported as successful.
- **API standards**: Pass. Resource-oriented routes and the contract define JSON
  success/error envelopes and status codes.
- **Data integrity**: Pass. Central request validation and service-level transition
  rules precede persistence.
- **Testing**: Pass. Every FR maps to deterministic automated tests using isolated
  files; restart behavior is explicitly tested.
- **Code quality**: Pass. ESLint is a required independent validation command.
- **Security**: Pass. Central validation, the approved 10 KiB request-body limit,
  safe error responses, and a pinned Semgrep scan are planned.
- **Traceability**: Pass. Requirement-to-component/test mapping is included below.
- **Harness independence**: Pass. Acceptance tests exercise only the public HTTP
  contract and must remain separate from application internals.
- **Human accountability**: Pass. Automated results are evidence for, not a
  replacement for, human review.

No constitution violations or exceptions are required.

### Post-Design Gate

- **Maintainability and API consistency**: Pass. The project structure and OpenAPI
  contract define the required separation and a single documented HTTP surface.
- **Reliability and data integrity**: Pass. The repository design commits complete
  mutations through a replacement file; service rules reject invalid transitions
  before persistence.
- **Testing and harness independence**: Pass. Each FR has a test mapping, and
  acceptance uses public HTTP behavior without implementation imports.
- **Code quality, security, and accountability**: Pass. Lint and static security
  checks remain separate validation gates; human review is still mandatory.

No post-design gate failures or constitution exceptions were identified.

## Architecture

The HTTP layer owns protocol concerns: routes declare the public paths, validation
middleware rejects malformed input, and controllers map service results and errors
to the documented envelopes. The task service owns domain rules, including defaults,
filtering, stable priority ordering, and legal status transitions. The repository
owns JSON parsing and durable replacement. The app factory composes these parts
without opening a listening socket; the server entry point owns startup and shutdown.

Each running app has one repository instance. The repository serializes mutations
within that process. A mutation reads and validates the current collection, applies a
complete change, writes a uniquely named temporary file in the data file's directory,
and renames it over the canonical file. The old file remains authoritative until the
replacement succeeds. A missing file initializes as an empty collection; malformed,
unreadable, or unwritable storage is reported and is never silently replaced with
empty data.

The application supports one writer process only. Mutations are serialized within
that process; concurrent writers in multiple processes or instances sharing a file
are explicitly out of scope.

## API Endpoint Design

The API base path is `/api`. The OpenAPI contract in `contracts/openapi.yaml` is the
authoritative route, field, response, and status-code description.

| Method | Path | Purpose | Success |
|---|---|---|---|
| `POST` | `/api/tasks` | Create a task; status defaults to pending | `201`, task in `data`, `Location` header |
| `GET` | `/api/tasks` | Retrieve tasks; optional `status`, `priority`, repeated `tag`, and `sort=priority` query parameters | `200`, task array in `data` |
| `GET` | `/api/tasks/{id}` | Retrieve a task | `200`, task in `data` |
| `PATCH` | `/api/tasks/{id}` | Partially update task fields and/or advance status | `200`, updated task in `data` |
| `DELETE` | `/api/tasks/{id}` | Delete a task | `200`, deletion result in `data` |

All supplied filters combine with AND semantics. Repeated `tag` filters require all
requested tags; requested tags are trimmed and de-duplicated by exact
case-sensitive equality. Priority sort is high-to-low and stable for ties. All
responses are JSON. Invalid request, unknown request property, or transition returns
`400`; oversized JSON request bodies return `413`; unknown task IDs return `404`;
storage failures return a generic `500` error without file paths or internal details.

## Error-Handling Strategy

Request-body parsing, route parameter parsing, query parsing, and field validation
feed one application error path. JSON request bodies larger than 10,240 bytes return
HTTP 413. Validation rejects unknown request properties, invalid enums, empty
required text after trimming, and malformed shapes before mutation, returning HTTP
400. The service checks status transitions and computes the entire candidate task
update before asking the repository to persist it. A failed validation, transition,
or write leaves the previously stored task unchanged.

One final Express error handler maps known errors to the contract's stable error
envelope (`error.code`, `error.message`) and status. Persistence and unexpected
errors are logged with operational context but returned as generic messages that do
not expose file paths, stack traces, or sensitive internals. No broad catch may turn
an error into a success-shaped response.

## Testing Strategy

- **Unit**: Test validation helpers and service rules, including defaults, filters,
  all-tags matching, priority order/ties, transition progression, and no mutation on
  rejected transitions.
- **Repository integration**: Use a new temporary directory and JSON file per test.
  Verify initialization, read/write/parse failures, complete replacement, and that
  failed writes preserve the previous file.
- **HTTP integration**: Use Supertest against the app factory, without binding a
  fixed port. Verify route methods, status codes, JSON envelopes, validation,
  404 behavior, filters, sorting, and persistence interactions.
- **Restart acceptance**: Run the real server as a child process on loopback with a
  unique temporary `TASKS_FILE` and an ephemeral port. Wait for explicit readiness,
  exercise the public API, stop and await process exit, restart with the same file,
  and verify exact data. Run the 100 persistence checks specified by SC-004 without
  fixed sleeps or network services.
- **Decision acceptance checks**: `AT-02` exercises request-size boundary/413
  handling, unknown-property rejection, and tag normalization solely through the
  public HTTP contract. `IT-02` verifies serialized mutations within one process.
- **Per-change gates**: Run the relevant Jest tests, full deterministic suite,
  ESLint, Semgrep, and the independent acceptance command. Keep tests repeatable and
  fixtures isolated; no test depends on wall-clock time, external network, or shared
  mutable files.

## Harness Architecture

Keep acceptance checks in a separately invoked `acceptance/` area. The harness must
be a black-box client: it may start/stop the server process and call documented HTTP
routes, but it must not import `src/` modules or read/write the task file to decide
whether an API assertion passed. It creates a unique temporary data path, uses only
loopback, obtains readiness from an explicit server signal, and cleans up its own
process and temporary files.

Keep the harness command and assertions separate from implementation unit tests.
Implementation changes may not weaken, skip, or edit acceptance assertions merely
to pass. A harness change requires an independently justified contract correction
and human review. This feature includes an independent in-repository black-box
harness at `acceptance/`; it runs against the public contract and is not coupled to
application modules.

## Security Considerations

- Validate type, shape, allowed values, and trimmed non-empty text centrally. Apply
  strict object schemas so unknown request properties return HTTP 400; do not
  interpolate input into paths or commands.
- Enforce a 10 KiB (10,240-byte) maximum JSON request body and return the documented
  JSON error envelope with HTTP 413 before request data reaches services or
  persistence.
- Use a unique ID generator with collision checking against the current collection.
- Create temporary persistence files exclusively with restrictive default file
  permissions; do not accept caller-controlled file locations through the API.
- Do not silently recover malformed JSON or expose file paths, stack traces, or
  implementation internals in error responses.
- Run a pinned Semgrep version and reviewed local ruleset independently of Jest.
  Findings must be fixed or have an explicit, human-approved exception.

## Traceability

| Spec requirement | Components | Implementation task(s) | Test and black-box acceptance coverage |
|---|---|---|---|
| FR-001 | Request validation, task service | T008, T023, T027 | UT-01/INT-01 → T015; AT-01 → T017: required fields, trimmed text, tags, pending default |
| FR-002 | Task service, ID generation | T023 | UT-02/INT-02 → T016; AT-01 → T017: unique IDs |
| FR-003 | Routes, controller, service, repository | T024–T027 | INT-03 → T016; AT-01 → T017: list and retrieve by ID |
| FR-004 | Validation, service, repository | T008, T033, T037 | UT-03/INT-04 → T029; AT-02 → T032: partial update, omitted fields unchanged, completed-task details editable without changing completed status |
| FR-005 | Routes, service, repository | T035–T037 | INT-05 → T031; AT-02 → T032: delete and verify absence |
| FR-006 | Query validation, service | T043–T045 | UT-04/INT-06 → T039; AT-03 → T042: each filter and AND combination |
| FR-007 | Query validation, service | T043–T044 | UT-05/INT-07 → T040; AT-03 → T042: priority enum, descending order, stable ties |
| FR-008 | Task service | T030, T034 | UT-06/INT-08 → T030; AT-04 → T038: valid progression, invalid transitions preserve state, completed-task edits preserve status |
| FR-009 | Query validation, service | T043–T044 | UT-07/INT-09 → T041; AT-03 → T042: all requested tags must match |
| FR-010 | Validation, error handler | T006–T009 | INT-10 → T015/T020/T029; AT-05 → T053: malformed, unknown-property, oversized, and invalid-transition errors |
| FR-011 | Service, controller, error handler | T006–T007, T024, T033, T035 | INT-11 → T016/T031; AT-04 → T038: unknown task IDs return 404 |
| FR-012 | Controller, error handler, OpenAPI contract | T007, T026, T037, T045 | INT-12 → T016; AT-01/AT-04/AT-05 → T017/T038/T053: success/error envelope schemas |
| FR-013 | JSON repository, server | T010–T012 | AT-01/AT-02/AT-06 → T017/T032/T049: create/update/delete data survives restart |
| FR-014 | JSON repository, error handler | T007, T010–T011 | IT-01 → T018; INT-13 → T031; AT-05 → T053: persistence read/parse/write failures surface through HTTP errors |
| FR-015 | Routes, controller, OpenAPI contract | T025–T027, T036–T037, T045 | INT-14 → T017/T038/T042; AT-01/AT-02/AT-03 → T017/T032/T042: methods, paths, and status codes match contract |
| FR-016 | Unit/integration suites and independent acceptance harness | T013–T014, T015–T053 | AT-01–AT-06 → T017/T032/T038/T042/T053/T049 cover every FR with observable public HTTP behavior |

### Test Identifier to Task Mapping

The UT/INT labels above are stable test-group identifiers, not task IDs. Each maps
to the task that creates the corresponding test file:

| Test group | Task ID | Test file |
|---|---|---|
| UT-01 | T015 | `tests/unit/tasks.create.test.js` |
| INT-01 | T015 | `tests/integration/tasks.create.test.js` |
| UT-02 | T016 | `tests/unit/tasks.identity.test.js` |
| INT-02 / INT-03 | T016 | `tests/integration/tasks.read.test.js` |
| UT-03 | T029 | `tests/unit/tasks.update.test.js` |
| INT-04 | T029 | `tests/integration/tasks.update.test.js` |
| INT-05 / INT-11 / INT-13 | T031 | `tests/integration/tasks.delete.test.js` |
| UT-04 | T039 | `tests/unit/tasks.filters.test.js` |
| INT-06 | T039 | `tests/integration/tasks.filters.test.js` |
| UT-05 | T040 | `tests/unit/tasks.sort.test.js` |
| INT-07 | T040 | `tests/integration/tasks.sort.test.js` |
| UT-06 | T030 | `tests/unit/tasks.transitions.test.js` |
| INT-08 | T030 | `tests/integration/tasks.transitions.test.js` |
| UT-07 | T041 | `tests/unit/tasks.tags.test.js` |
| INT-09 | T041 | `tests/integration/tasks.tags.test.js` |
| INT-10 | T015/T020/T029/T031 | Validation and error-path integration tests |
| INT-12 | T015/T016/T029/T031 | Success and error response envelope integration assertions |
| INT-14 | T015/T016/T029/T031/T039 | Route, method, query, and status-code integration assertions |
| IT-01 | T018 | `tests/integration/json-task.repository.test.js` |
| IT-02 | T047 | `tests/integration/json-task.repository.concurrency.test.js` |
| UT-08 | T021 | `tests/unit/tasks.validation.test.js` |
| INT-15 | T019 | `tests/integration/request-size.test.js` |
| INT-16 | T020/T029 | `tests/integration/tasks.validation.test.js` and `tests/integration/tasks.update.test.js` |
| INT-17 | T021/T041 | Tag normalization and query matching integration/unit tests |

Acceptance groups map to black-box task files as follows: AT-01 → T017,
AT-02 → T032, AT-03 → T042, AT-04 → T038, AT-05 → T053, and AT-06 → T049.

### Approved Technical Decision Traceability

| Decision | Design location | Planned deterministic verification |
|---|---|---|
| TD-01: One writer process; serialize mutations in-process; multi-process writes out of scope | Constraints, Architecture, Research, Data Model | IT-02 verifies serialized concurrent mutations within one process; no multi-process guarantee is asserted |
| TD-02: Independent in-repository black-box acceptance harness | Harness Architecture, Project Structure, Research | AT-01 invokes `acceptance/` against a child server over loopback without importing application modules |
| TD-03: 10 KiB (10,240-byte) maximum JSON request body; HTTP 413 above limit | Technical Context, Error Handling, Security, OpenAPI | INT-15 → T019 and AT-05 → T053 verify the boundary and 413 without mutation |
| TD-04: Reject unknown request properties with HTTP 400 | Error Handling, OpenAPI request schemas | INT-16 → T020/T029 and AT-05 → T053 verify create/update rejection without mutation |
| TD-05: Trim tags, remove exact case-sensitive duplicates, preserve first occurrence/order | Data Model, Research, OpenAPI tag descriptions | UT-08/INT-17 → T021/T041 and AT-01/AT-03 → T017/T042 verify normalization and case-sensitive matching |
| TD-06: Node.js 24, npm, ESM, Express 5 | Technical Context, Research, Project Structure | CI/runtime check verifies Node major 24, npm scripts, ESM module mode, and Express 5 dependency |

## Technical Decision Status

All six technical decisions reviewed for this update are approved and incorporated
above; none of those six remains unresolved. The approved specification also now
explicitly allows title, description, priority, and tag edits after completion while
requiring status to remain completed and prohibiting backward transitions. Tags are
trimmed, deduplicated by exact case-sensitive value while preserving first occurrence,
and matched exactly and case-sensitively.

## Project Structure

### Documentation (this feature)

```text
specs/001-task-management-api/
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   └── openapi.yaml
├── quickstart.md
├── checklists/
│   └── requirements.md
└── tasks.md                 # Created by /speckit-tasks, not this workflow
```

### Source Code (repository root)

```text
src/
├── app.js                              # Compose Express app; inject config/dependencies
├── server.js                           # Start, signal readiness, and shut down server
├── models/
│   └── task.js                          # Task, priority, and status definitions
├── routes/
│   └── tasks.routes.js                 # Declare task resource routes and middleware
├── controllers/
│   └── tasks.controller.js             # Map HTTP inputs/results to response contract
├── services/
│   └── tasks.service.js                # Validation-independent task rules and queries
├── validation/
│   └── tasks.validation.js             # Shared request shape and field validation
├── persistence/
│   └── json-task.repository.js         # JSON read, serialized mutation, atomic replace
├── middleware/
│   └── error-handler.js                # Central error-to-HTTP mapping
└── errors/
    └── app-error.js                    # Typed application errors

data/
└── .gitkeep                            # Runtime tasks.json is not committed

tests/
├── unit/
│   ├── tasks.create.test.js
│   ├── tasks.identity.test.js
│   ├── tasks.update.test.js
│   ├── tasks.transitions.test.js
│   ├── tasks.filters.test.js
│   ├── tasks.sort.test.js
│   ├── tasks.tags.test.js
│   └── tasks.validation.test.js
└── integration/
    ├── json-task.repository.test.js
    ├── json-task.repository.concurrency.test.js
    ├── request-size.test.js
    ├── runtime-baseline.test.js
    ├── tasks.create.test.js
    ├── tasks.read.test.js
    ├── tasks.update.test.js
    ├── tasks.transitions.test.js
    ├── tasks.delete.test.js
    ├── tasks.filters.test.js
    ├── tasks.sort.test.js
    ├── tasks.tags.test.js
    └── tasks.validation.test.js

acceptance/
├── run-acceptance.js                        # Independent runner; public HTTP only
├── tasks.create-read.acceptance.test.js       # AT-01: FR-001–003, FR-010, FR-012–013, FR-015–016
├── tasks.update-delete.acceptance.test.js     # AT-02: FR-004–005, FR-008, FR-012–013, FR-015–016
├── tasks.filters.acceptance.test.js           # AT-03: FR-006–007, FR-009–010, FR-012, FR-015–016
├── tasks.transitions.acceptance.test.js       # AT-04: FR-008, FR-010–012, FR-015–016
├── tasks.errors.acceptance.test.js            # AT-05: FR-010, FR-012, FR-014–016
└── tasks.restart.acceptance.test.js           # AT-06: FR-013, FR-016; 100 restart checks

contracts/
└── semgrep.yml                         # Reviewed, version-controlled local rules

eslint.config.js
package.json
package-lock.json
```

**Structure Decision**: Use one Node.js web-service project rooted at the repository.
Separate HTTP routing, controllers, domain service, validation, error handling, and
JSON persistence as requested. Keep unit/integration tests separate from the
independent in-repository black-box acceptance harness. Configure package metadata
for Node.js 24, npm, ESM, and Express 5. Do not introduce a frontend, database, or
additional service.

## Complexity Tracking

No constitution violations. No extra projects or abstractions beyond the required
layers and independent test harness are proposed.
