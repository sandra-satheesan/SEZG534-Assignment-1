# Part 1A Harness Log

## Harness

- Harness: independent public-HTTP acceptance harness in `acceptance/`
- Command: `cd Part-1A && npm run test:acceptance`
- Run date: 2026-11-15
- Environment: macOS

## Result

```text
Test Suites: 6 passed, 6 total
Tests:       19 passed, 19 total
Snapshots:   0 total
```

The acceptance harness starts the actual server process on loopback, uses
isolated temporary JSON storage and ephemeral ports, waits for readiness, and
cleans up child processes and temporary directories. Assertions use only
public HTTP responses.

The suites include create/read, update/delete, filtering, lifecycle
transitions, persistence errors, and restart persistence. The restart suite
includes the recorded 100-cycle create/restart/retrieve check.

## Additional recorded evidence

- Full Jest suite: 27 suites and 103 tests passed.
- ESLint: passed with zero warnings.
- Semgrep: 0 findings in the recorded 2026-11-01 run.
- `npm audit --audit-level=low`: 0 vulnerabilities in the recorded
  2026-11-03 run.
- `git diff --check`: passed.

## Limitations

- The Windows-specific branch of the persistence write-failure fixture was not
  verified.
- The recorded Semgrep result was not rerun during the latest validation.

## Human review

Human reviewer sign-off: **Approved** on 2026-11-03. The Windows-specific
persistence-fixture limitation was accepted.
