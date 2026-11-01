<!--
Sync Impact Report
Version change: unratified template → 1.0.0
Modified principles: none (initial adoption)
Added sections: ten Core Principles; Technology Constraints; Development Workflow
Removed sections: none
Follow-up TODOs: Confirm the original ratification date and replace TODO(RATIFICATION_DATE).
-->

# Smart Todo & Task Management API Constitution

## Core Principles

### I. Maintainability
The API MUST use modular Node.js and Express.js components with clear separation of
responsibilities. Names and control flow MUST make behavior readable without relying
on undocumented conventions.

### II. Reliability
For the same valid request and persisted state, the API MUST behave predictably.
JSON persistence MUST use a consistent documented format; storage or parse failures
MUST be reported as errors and MUST NOT be presented as successful operations.

### III. RESTful API Standards
Task resources MUST use RESTful HTTP methods and resource-oriented routes. Responses
MUST use JSON, consistent documented success and error formats, and HTTP status codes
appropriate to the outcome.

### IV. Data Integrity
Every external input MUST be validated before it changes task state or is persisted.
Only specified task state transitions are permitted; invalid transitions MUST leave
the persisted state unchanged and return an appropriate error.

### V. Deterministic Testing
Every approved functional requirement MUST map to one or more automated deterministic
tests. Tests MUST control their data and persistence fixtures, avoid dependence on
network services, wall-clock timing, or shared mutable state, and verify observable
API and persistence behavior.

### VI. Code Quality
The project MUST define and run a linter and consistent formatting or coding
conventions. Changes MUST pass the configured lint checks and relevant automated
tests before they are considered complete.

### VII. Security
Inputs MUST be validated and sanitized where needed for their use. Responses and logs
MUST NOT expose sensitive information. The project MUST run static security checks
and address reported findings before release or document an approved exception.

### VIII. Traceability
Implementation tasks and tests MUST identify the approved specification requirement
they satisfy. Work that cannot be traced to an approved requirement MUST be clarified
or approved before it is included.

### IX. Harness Independence
Validation scripts and acceptance tests are authoritative controls. They MUST NOT be
weakened, bypassed, or modified merely to make an implementation pass; changes to
them require an independently justified, reviewed specification or harness correction.

### X. Human Accountability
An automated PASS is evidence, not approval. A human reviewer MUST inspect the
relevant implementation and validation results before work is accepted.

## Technology Constraints

The application MUST run on Node.js and use Express.js for HTTP handling. Task data
MUST be persisted in JSON files; introducing a database or alternate persistence
backend requires an approved specification change. Automated tests MUST be
deterministic and MUST exercise the API behavior and JSON persistence contract.

## Development Workflow

Each change MUST be grounded in an approved specification and trace its implementation
tasks and tests to that specification. Before acceptance, run the applicable
deterministic tests, lint checks, and static security checks, then obtain human review.
Validation scripts and acceptance tests MUST remain independent of implementation
changes except for separately reviewed, specification-backed corrections.

## Governance

This constitution governs project specifications, implementation, tests, and review.
Amendments require a documented rationale and human approval. The constitution
version MUST follow semantic versioning: MAJOR for incompatible principle or
governance changes, MINOR for new principles or materially expanded requirements,
and PATCH for clarifications and non-semantic corrections. Compliance MUST be
reviewed during human review of each change; exceptions require explicit approval
and a recorded rationale. Automated PASS results MUST never substitute for this
review.

**Version**: 1.0.0 | **Ratified**: 2026-10-31 | **Last Amended**: 2026-10-31
