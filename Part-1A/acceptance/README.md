# Independent acceptance harness

Run all public-HTTP acceptance suites from `Part-1A/`:

```sh
npm run test:acceptance
```

The harness starts the actual server process on loopback, uses isolated temporary
JSON paths and ephemeral ports, waits for the server's readiness signal, and cleans
up child processes and temporary directories. Assertions use only public HTTP
responses; acceptance tests do not import application modules or inspect persisted
task data to determine pass/fail.

## Restart persistence result

The restart acceptance suite is included in `npm run test:acceptance`. From
`Part-1A/`, run its 100-cycle check by itself with:

```sh
npm test -- --runInBand --testMatch='**/acceptance/tasks.restart.acceptance.test.js'
```

Each cycle creates a task through HTTP, stops the server, restarts it with the same
temporary JSON file, and retrieves the task through HTTP to compare the complete
response. No fixed sleeps or external network services are used.

**Recorded isolated run (2026-11-01):** the command above passed; Jest reported
1 suite and 1 test passed. The test completed all 100 create/restart/retrieve checks.

**Recorded complete run (2026-11-01):** `npm run test:acceptance` passed 6 suites
and 19 tests, including the 100-cycle restart check and public-HTTP error cases.
