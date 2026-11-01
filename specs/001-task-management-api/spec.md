# Feature Specification: Smart Todo & Task Management API

**Feature Branch**: `Not created (no branch hook configured)`

**Created**: 2026-10-31

**Status**: Approved

**Input**: User description: "Build a REST API that allows users to manage tasks with JSON file-based persistence."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create and review tasks (Priority: P1)

As a task manager, I want to create tasks and retrieve the task list or a task by ID
so that I can record work and see what needs attention.

**Why this priority**: Task creation and retrieval provide the essential task-management
value and establish the records used by every other story.

**Independent Test**: Create a valid task, retrieve the collection, and retrieve that
task by its returned ID. Each result can be checked against the submitted task details.

**Acceptance Scenarios**:

1. **Given** a valid task request with title, description, priority, tags, and status,
   **When** the user creates the task, **Then** the API returns a successful response
   containing a unique task ID and the task details.
2. **Given** a task has been created, **When** the user retrieves all tasks,
   **Then** the response contains the task.
3. **Given** a task has been created, **When** the user retrieves it by its ID,
   **Then** the response contains that task and its ID.
4. **Given** a task request omits a required field or supplies an invalid value,
   **When** the user submits it, **Then** the API returns a client error and does not
   create a task.
5. **Given** a valid task request omits status, **When** the user creates the task,
   **Then** the created task has pending status.

---

### User Story 2 - Maintain task details and status (Priority: P1)

As a task manager, I want to update task details, move tasks through their allowed
statuses, and delete tasks so that the task list reflects current work.

**Why this priority**: A task list is useful only when users can keep it current and
record progress without corrupting task state.

**Independent Test**: Update a task's editable details, exercise allowed and disallowed
status changes, then delete it and verify its absence.

**Acceptance Scenarios**:

1. **Given** an existing task, **When** the user updates one or more task details with
   valid values, **Then** the API returns the updated task and persists those changes.
2. **Given** an existing task, **When** the user requests its deletion, **Then** the
   API returns a successful deletion response and the task is no longer retrievable.
3. **Given** the task is pending, **When** the user changes its status to in-progress,
   **Then** the transition succeeds.
4. **Given** the task is in-progress, **When** the user changes its status to
   completed, **Then** the transition succeeds.
5. **Given** a requested status change is not the next permitted transition,
   **When** the user submits the update, **Then** the API returns a client error and
   the stored task remains unchanged.
6. **Given** an ID does not identify an existing task, **When** the user updates or
   deletes it, **Then** the API returns 404 and changes no stored data.
7. **Given** a task is completed, **When** the user updates its title, description,
   priority, or tags without requesting a status change, **Then** those details are
   updated and the task remains completed.
8. **Given** a task is completed, **When** the user attempts to move it to an earlier
   status, **Then** the API rejects the request and leaves the task unchanged.

---

### User Story 3 - Find and prioritize tasks (Priority: P2)

As a task manager, I want to filter tasks by status, priority, and tags and sort them
by priority so that I can focus on the tasks relevant to me.

**Why this priority**: Finding and prioritizing tasks improves usability once task
records can be created and maintained.

**Independent Test**: Create tasks with distinct statuses, priorities, and tags; apply
each filter and priority sort; compare every returned result and ordering with the
known fixture data.

**Acceptance Scenarios**:

1. **Given** tasks with different statuses exist, **When** the user filters by one
   status, **Then** every returned task has that status and no nonmatching task is
   returned.
2. **Given** tasks with different priorities exist, **When** the user filters by one
   priority, **Then** every returned task has that priority and no nonmatching task
   is returned.
3. **Given** tasks with different tags exist, **When** the user filters by multiple
   tags, **Then** every returned task has all requested tags.
4. **Given** tasks with different priorities exist, **When** the user sorts by
   priority, **Then** tasks appear in high-to-low order (high, medium, low), with
   equal-priority tasks retaining their collection order.
5. **Given** a filter matches no tasks, **When** the user requests the filtered list,
   **Then** the API returns a successful response containing an empty collection.

## Edge Cases

- A missing, empty, or whitespace-only required text field or tag is rejected.
- Unknown task IDs return 404 for individual retrieval, update, and deletion.
- An invalid status, priority, tag value, or malformed request is rejected without
  changing persisted task data.
- A task created without a status starts as pending; a supplied initial status other
  than pending is rejected.
- An attempt to skip, reverse, or repeat a status transition is rejected without
  changing the stored status or other task details.
- A completed task's title, description, priority, and tags remain editable; those
  edits do not change its completed status, and backward status transitions remain
  prohibited.
- A filter with no matching tasks returns an empty result, not an error.
- A malformed or unreadable persisted data file is reported as a persistence error;
  the API does not claim that a failed read or write succeeded.
- After a successful create, update, or delete, restarting the service does not
  restore stale task data or lose the successful change.
- A task collection with equal priorities retains its collection order when sorted.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The API MUST allow a user to create a task with title, description,
  priority, and tags. Title, description, priority, and tags are required; title and
  description MUST be non-empty after trimming. Tags MUST be a list of non-empty
  strings and MAY be empty. A new task MUST start as pending; an omitted status
  defaults to pending, and any supplied initial status other than pending MUST be
  rejected.
- **FR-002**: The API MUST assign every created task a unique ID.
- **FR-003**: The API MUST allow a user to retrieve all tasks and retrieve one task by
  ID.
- **FR-004**: The API MUST allow a user to update task title, description, priority,
  and tags. An update MUST validate the supplied fields and leave unspecified fields
  unchanged. These fields MUST remain editable after a task reaches completed status;
  such edits MUST leave status completed.
- **FR-005**: The API MUST allow a user to delete a task by ID.
- **FR-006**: The API MUST allow filtering tasks by status, priority, and tags. When
  multiple filters are supplied, all supplied filters MUST be satisfied.
- **FR-007**: The API MUST accept only low, medium, and high as priority values and
  MUST sort tasks high to low. Equal-priority tasks MUST retain their collection order.
- **FR-008**: The only permitted status transitions MUST be pending → in-progress →
  completed. Invalid and backward transitions MUST be rejected without changing
  stored task data. A completed task MUST remain completed when its title,
  description, priority, or tags are edited.
- **FR-009**: When a task filter includes multiple tags, a task MUST match all
  requested tags.
- **FR-010**: The API MUST reject missing required fields, invalid values, and invalid
  status transitions with an appropriate client-error response and a consistent JSON
  error body.
- **FR-011**: Retrieval, update, and deletion of a nonexistent task MUST return 404.
- **FR-012**: Successful API responses MUST use a documented, consistent JSON response
  structure; errors MUST use a documented, consistent JSON error structure.
- **FR-013**: Task changes MUST be persisted to a JSON file and remain available after
  the service restarts.
- **FR-014**: Persistence read, parse, or write failures MUST be reported and MUST NOT
  be returned as successful task operations.
- **FR-015**: Endpoints MUST follow RESTful resource conventions and use HTTP status
  codes appropriate to success, client errors, missing resources, and persistence
  failures.
- **FR-016**: Automated acceptance tests MUST deterministically verify each functional
  requirement, including filtering, sorting, validation, transition rejection,
  response structure, and persistence across a restart.

### Key Entities

- **Task**: A unit of work identified by a unique ID, with a required title,
  description, priority, tags, and status.
- **Status**: A task lifecycle value with the permitted progression pending,
  in-progress, and completed.
- **Priority**: One of low, medium, or high; used to filter and sort tasks from high
  to low.
- **Tag**: A user-provided label associated with a task and used for filtering.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a deterministic acceptance run, 100% of valid task-creation requests
  produce a task retrievable by its unique ID.
- **SC-002**: In deterministic acceptance runs, 100% of tested invalid inputs and
  invalid transitions are rejected without changing stored task data.
- **SC-003**: In deterministic acceptance runs, 100% of tested filter and sort
  results match the expected task membership and ordering.
- **SC-004**: In 100 consecutive persistence checks, each successfully saved task
  remains retrievable with unchanged details after a service restart.
- **SC-005**: 100% of tested success and error responses conform to the documented
  JSON response structure and expected HTTP status behavior.

## Assumptions

- The API serves one shared task collection; user accounts, authentication, and
  per-user ownership are outside this feature's scope.
- An update changes only fields supplied by the caller; an empty update is invalid.
- When multiple filters are provided, they combine with AND semantics across filter
  dimensions; a task must match all requested tags in a multi-tag filter.
- Title, description, priority, and tags are required on creation. Title and
  description must contain non-whitespace text; tags must be a list of strings but
  may be empty; each supplied tag must contain non-whitespace text. Tag filters use
  exact, case-sensitive matching after trimming whitespace. A missing status
  defaults to pending, and a supplied status on creation must be pending.
- Priority values are low, medium, and high; sorting is high to low. Equal-priority
  tasks retain the order they had in the collection before sorting.
- The success response envelope will contain task or collection data under `data`;
  the error envelope will contain an `error` object with a stable code and readable
  message. Exact field names and examples are to be documented with the API contract.
- Malformed request bodies, field validation failures, and invalid status transitions
  return 400; nonexistent task IDs return 404; unrecoverable persistence failures
  return 500 without exposing file paths or sensitive internals.
- The application is constrained to Node.js and Express.js, persists task data in a
  JSON file, and uses deterministic automated testing, as required by the project.
- No migration of preexisting task data is required for this feature.
