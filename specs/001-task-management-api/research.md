# Research: Smart Todo & Task Management API

**Date**: 2026-10-31  
**Scope**: Resolve design choices for the approved API and project technology
constraints. This research does not change the specification.

## Decision: Use a single Express app factory and a separate server entry point

**Rationale**: Express middleware order is part of request behavior, and error
handling should be centralized. Exporting an app factory without opening a listening
socket enables HTTP integration tests to use an ephemeral port. The server entry
point remains responsible for process startup, readiness, and shutdown.

**Alternatives considered**: Starting the server as an import side effect would make
tests contend for ports and couple app construction to process lifecycle. A broader
multi-service architecture is unnecessary for one task collection.

**References**:
- [Express middleware guide](https://expressjs.com/en/guide/using-middleware.html)
- [Express error handling](https://expressjs.com/en/guide/error-handling.html)

## Decision: Keep one ordered task array in a JSON file and serialize writes per process

**Rationale**: This representation is direct, inspectable, and consistent with the
approved JSON-file constraint. Node documents that concurrent filesystem operations
against the same file are not automatically synchronized. A per-repository mutation
queue prevents overlapping mutations within one service process.

**Alternatives considered**: A database or another persistence backend violates the
constitution. Writing the canonical file directly risks leaving truncated JSON if a
write fails. Multi-process writers are explicitly out of scope; the implementation
does not claim cross-process locking or lost-update prevention.

For each mutation, validate the current file, prepare the complete replacement,
write it to an exclusive temporary file in the same directory, close/sync it as
supported, then rename it over the canonical file. Return success only after replace
succeeds. On failure, preserve the old canonical file and report an error. Treat a
missing file as first-run empty data; never silently convert malformed JSON to an
empty collection.

**References**:
- [Node.js file system API](https://nodejs.org/api/fs.html)
- [`rename(2)` reference](https://man7.org/linux/man-pages/man2/rename.2.html)

## Decision: Generate task IDs with Node's cryptographic UUID facility

**Rationale**: `crypto.randomUUID()` is a built-in UUID generator that avoids a new
runtime dependency. Check the generated candidate against the current collection
before insertion so a collision is never accepted.

**Alternatives considered**: Hand-rolled timestamps or counters are more collision
prone and can reveal ordering; an external ID package is unnecessary.

**Reference**:
- [Node.js `crypto.randomUUID()`](https://nodejs.org/api/crypto.html#cryptorandomuuidoptions)

## Decision: Use Jest and Supertest with isolated data per test

**Rationale**: Jest provides deterministic asynchronous setup and teardown; Supertest
can exercise an Express app without a fixed port. Each test receives a new temporary
directory and a separately configured JSON file. Restart acceptance tests spawn the
real server and exercise only loopback HTTP.

**Alternatives considered**: Tests that share the default data file are order-dependent
and can corrupt developer data. Fixed-port servers conflict with parallel tests.
Restarting only a repository object does not prove process restart persistence.

**References**:
- [Jest setup and teardown](https://jestjs.io/docs/setup-teardown)
- [Supertest README](https://github.com/forwardemail/supertest#readme)
- [Node.js child processes](https://nodejs.org/api/child_process.html)

## Decision: Keep acceptance validation black-box and independently invoked

**Rationale**: A separate acceptance command that starts the server, configures a
temporary file, and calls documented HTTP routes does not depend on controllers,
services, or repository internals. It can therefore detect contract mismatches and
remains independent of implementation changes.

**Alternatives considered**: Importing internal modules into acceptance assertions
would couple the harness to implementation and weaken its authority. Editing
acceptance expectations to make failing implementation pass violates the constitution.

The approved design places this harness in-repository under `acceptance/`, separate
from application and unit/integration code. It invokes the actual server process
using an isolated temporary JSON path and public HTTP only. It must remain
independently runnable and its checks must not be weakened to make implementation
pass.

## Decision: Use pinned ESLint and Semgrep checks as independent quality gates

**Rationale**: A checked-in ESLint flat configuration makes style checks repeatable.
A pinned Semgrep CLI and reviewed local rules avoid dependence on an unpinned remote
ruleset. Both checks run separately from Jest so a test result does not imply static
checks passed.

**Alternatives considered**: An unpinned remote ruleset can change between runs or
require network access; silently ignoring findings is inconsistent with the
constitution.

**References**:
- [ESLint configuration](https://eslint.org/docs/latest/use/configure)
- [Semgrep rule syntax](https://docs.semgrep.dev/writing-rules/rule-syntax)

## Approved Technical Decisions

- Node.js 24, npm with committed lockfile, ESM, and Express 5.
- `TASKS_FILE` selects persistence path for test isolation; default is
  `data/tasks.json`.
- Use `PATCH /api/tasks/{id}` for partial updates and repeated `tag` query parameters.
- JSON request bodies are limited to 10 KiB (10,240 bytes); larger bodies return
  HTTP 413 in the documented JSON error envelope.
- Unknown top-level properties on create/update request objects are rejected with
  HTTP 400 before any mutation.
- Trim tags and remove duplicates after trimming using exact case-sensitive
  comparison. Preserve the first occurrence and the remaining order; `Foo` and `foo`
  are distinct tags. Tag queries use the same normalized, case-sensitive equality.
- Status may only advance pending → in-progress → completed, with no repeat, reverse,
  or skip.
- Preserve collection order when priorities tie.
- One process is the only supported writer. Serialize its mutations in-process;
  concurrent multi-process writes are out of scope.
- Run a separate, in-repository black-box acceptance harness in `acceptance/`.

## Decision Traceability

| Decision | Recorded in | Verification |
|---|---|---|
| Single writer process; serialized in-process mutations; multi-process writers out of scope | Plan constraints and architecture; data model | Repository concurrency test within one process; no multi-process guarantee |
| Independent in-repository black-box acceptance harness | Plan harness architecture and project structure | Child-process acceptance run through loopback HTTP; no imports from application source |
| 10 KiB (10,240-byte) JSON body limit; 413 response | Plan error/security sections; OpenAPI | Boundary and over-limit request tests, including no mutation after 413 |
| Unknown request properties produce 400 | Plan error handling; OpenAPI request schemas | Create/update requests with an extra property are rejected without mutation |
| Trim tags and remove exact case-sensitive duplicates; preserve first occurrence | Plan and data model; OpenAPI descriptions | Unit, HTTP, and black-box tests for normalization, order, and case |
| Node.js 24, npm, ESM, Express 5 | Plan technical context | Runtime and package metadata checks |

These are approved technical choices for design and implementation; they do not
change or weaken the specification's existing acceptance criteria.

## Completed-Task Editing

The approved specification permits updating title, description, priority, and tags
after completion. These edits preserve `completed` status; backward transitions
remain invalid. Integration and black-box acceptance coverage is mapped in the plan.
