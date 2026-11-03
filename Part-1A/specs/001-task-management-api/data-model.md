# Data Model: Smart Todo & Task Management API

## Task

Represents one unit of work in the shared task collection.

| Field | Type | Required on create | Rules |
|---|---|---:|---|
| `id` | string | No; generated | Unique UUID; clients cannot set or change it |
| `title` | string | Yes | Trim surrounding whitespace; must contain at least one non-whitespace character |
| `description` | string | Yes | Trim surrounding whitespace; must contain at least one non-whitespace character |
| `priority` | enum string | Yes | Exactly `low`, `medium`, or `high` |
| `tags` | array of strings | Yes | Empty array is valid; trim each supplied tag, reject whitespace-only values, remove exact case-sensitive duplicates while preserving first occurrence and order |
| `status` | enum string | No | `pending`, `in-progress`, or `completed`; defaults to `pending` on create |

Creation, update, and deletion timestamps are not specified and are not added by
this plan.

## State Transitions

```text
pending → in-progress → completed
```

- Creation always results in `pending`; a supplied create status may be omitted or
  equal `pending`. Any other initial status is invalid.
- An update that changes status must advance exactly one step.
- Repeating the current status, reversing status, skipping a step, or changing status
  from `completed` is invalid.
- A request combining a valid detail change with an invalid status change is atomic:
  reject the request and persist none of its changes.
- Title, description, priority, and tags remain editable after completion. Such an
  edit leaves status as `completed`; a backward status transition is invalid.

## Collection and Persistence

- The canonical JSON document is an ordered array of Task objects.
- The order of this array is collection order. A priority-sorted response uses
  `high`, `medium`, `low`, with original collection order as the tie-breaker; sorting
  does not reorder the stored array.
- A missing file represents a first run and initializes as an empty array.
- Invalid JSON, invalid stored task shape, or read/write errors are persistence
  failures. They must be reported; they must never trigger silent replacement with
  an empty array.
- Mutations are serialized within one application process and replace the full JSON
  document using a same-directory temporary file and rename.
- Exactly one writer process is supported. Multi-process writers are out of scope.

## Input Normalization

- On create and update, trim each tag.
- Reject a tag that becomes empty after trimming.
- Remove duplicates by exact case-sensitive equality after trimming; preserve the
  first occurrence and the relative order of remaining tags.
- Consequently, `work` and ` work ` normalize to one tag, while `Work` and `work`
  remain distinct.
- Tag filter values are trimmed and compared exactly, case-sensitively, against the
  normalized task tags.

## Query Semantics

- `status` and `priority` each accept one allowed enum value.
- `tag` may be repeated. A task matches only if it contains every requested tag.
- Requested tag values are trimmed, then exact case-sensitive duplicates are
  removed while preserving first occurrence.
- Tag matching is exact and case-sensitive after trimming.
- Different filter dimensions combine using AND.
- `sort=priority` sorts high-to-low and preserves collection order for equal priority.
- Invalid filter values or sort options return a validation error, not an empty
  collection.

## Relationships

- A Task contains zero or more normalized tag strings.
- Status and Priority are enumerated values associated with a Task.
- No user, owner, project, or authentication entity is defined by this feature.
