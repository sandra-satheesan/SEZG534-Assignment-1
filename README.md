# SEZG534 Assignment 1

This repository contains two independent assignment parts:

- **Part 1A — Smart Todo application:** REST API, React frontend, tests,
  acceptance coverage, and feature specifications in [`Part-1A/`](./Part-1A/).
- **Part 1B — Natural-Language Reminder Agent:** reserved workspace in
  [`Part-1B/`](./Part-1B/); implementation has not started.

The root `.git` directory and `.specify/` configuration are shared. Each part
keeps its own application files and feature specifications.

## Part 1A

From the repository root, install the backend and frontend dependencies:

```sh
cd Part-1A
npm ci
npm --prefix web ci
```

In one terminal, start the API:

```sh
cd Part-1A
npm start
```

In another terminal, start the frontend:

```sh
cd Part-1A
npm run dev --prefix web
```

Open <http://127.0.0.1:5173>. Vite forwards `/api` requests to the API on
<http://127.0.0.1:3000>.

Run Part 1A checks from `Part-1A/`:

```sh
npm test -- --runInBand
npm run test:acceptance
npm run lint
npm run security
npm run build --prefix web
```

The API persists task data in `Part-1A/data/tasks.json`, which is ignored by Git.

## Separate Spec Kit workflows

The shared Spec Kit scripts and templates live in the root `.specify/` directory.
Keep each part's feature artifacts in its own specs directory:

- Part 1A: `Part-1A/specs/<feature>/`
- Part 1B: `Part-1B/specs/<feature>/`

When creating a feature, select the part-specific specs root explicitly:

```sh
SPECIFY_SPECS_DIRECTORY=Part-1A/specs \
  .specify/scripts/bash/create-new-feature.sh "Describe a Part 1A feature"
```

Or, for Part 1B:

```sh
SPECIFY_SPECS_DIRECTORY=Part-1B/specs \
  .specify/scripts/bash/create-new-feature.sh "Describe a Part 1B feature"
```

For subsequent plan, task, and prerequisite workflows, set
`SPECIFY_FEATURE_DIRECTORY` to the chosen feature path, for example:

```sh
SPECIFY_FEATURE_DIRECTORY=Part-1A/specs/001-task-management-api \
  .specify/scripts/bash/check-prerequisites.sh --paths-only
```

Use the corresponding `Part-1B/specs/<feature>` path for Part 1B. The ignored
`.specify/feature.json` stores only the most recently active feature as a
convenience; explicit environment variables keep workflows scoped correctly and
avoid ambiguity between parts. Shared constitution, templates, and workflow
configuration remain at the repository root.
