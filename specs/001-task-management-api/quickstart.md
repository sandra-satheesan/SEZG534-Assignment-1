# Quickstart: Smart Todo & Task Management API

This guide describes the implemented validation flow. It does not include
application implementation code.

## Prerequisites

- Node.js 24 and npm.
- Dependencies installed from the committed lockfile.
- Semgrep 1.183.0 installed from `requirements-security.txt` and available on `PATH`.
- For a user-level Semgrep installation on macOS/Linux, add the Python user scripts
  directory to `PATH` (the value of `python3 -m site --user-base`, followed by `/bin`).
- No external network service or database is required for tests.

## Install and validate

```sh
python3 -m pip install -r requirements-security.txt
# For a user-level Semgrep installation on macOS/Linux:
export PATH="$(python3 -m site --user-base)/bin:$PATH"
npm ci
npm test
npm run lint
npm run security
npm run test:acceptance
```

Expected result: deterministic unit and HTTP integration tests pass; ESLint reports
no violations; the pinned Semgrep scan completes with no unresolved findings or only
explicitly approved exceptions; and the independent black-box acceptance suite
passes, including the 100 restart checks.

## Run the service

```sh
npm start
```

The service listens on the configured port (default `3000`) and uses
`data/tasks.json` unless `TASKS_FILE` selects another path. The default file is
runtime data and is not committed.

## Exercise the API contract

Use the route, field, status, and response definitions in
[contracts/openapi.yaml](./contracts/openapi.yaml). Verify:

1. Create a valid task; expect `201`, a unique ID, `pending` status when omitted, and
   a `Location` header. Supplied tags are trimmed and exact case-sensitive
   duplicates are removed while retaining first occurrence order.
2. Retrieve the task and collection; expect the documented `data` envelopes.
3. Filter by status, priority, and repeated `tag` parameters; confirm AND semantics
   and all-requested-tags matching.
4. Sort by priority; expect high-to-low order and stable ties.
5. Advance status through pending → in-progress → completed; attempt invalid changes
   and verify an error response with no persisted mutation. After completion, update
   title, description, priority, and tags individually; verify the task remains
   completed, and verify attempts to move backward are rejected.
6. Submit invalid input and unknown IDs; expect `400` and `404` respectively.
7. Submit a create or update request with an unknown property; expect `400` and no
   persisted change.
8. Submit a JSON body larger than 10 KiB (10,240 bytes); expect `413` and no
   persisted change.

## Deterministic integration and restart checks

The planned test suites must isolate their data and must not share the default runtime
file. HTTP integration tests use an app instance and a unique temporary JSON file.
The independent acceptance suite is invoked separately:

```sh
npm run test:acceptance
```

It starts the actual server process on loopback, sets `TASKS_FILE` to a new temporary
path and an ephemeral port, waits for explicit readiness, verifies create/update/
delete persistence across stop and restart, and cleans up the process and temporary
directory. It performs the 100 persistence checks required by SC-004 without fixed
sleep-based synchronization. The acceptance suite must call only the public HTTP
contract and must not import application modules.

The request/error contract checks also run in this independent suite. They verify
validation and body-size failures, safe error envelopes, and observable persistence
failures using isolated fixtures.

## Human review

After automated validation, a human reviewer inspects the implementation, test
results, lint and security output, and requirement traceability. Automated PASS alone
does not authorize acceptance.
