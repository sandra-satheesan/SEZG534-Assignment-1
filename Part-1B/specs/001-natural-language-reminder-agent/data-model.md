# Data Model: Natural-Language Reminder Agent

All models are versioned through the API contract. Inputs and outputs use explicit nullable values where a fact may be unknown; absence must never be interpreted as permission to invent it. Model-generated data is untrusted until strict schema parsing and domain invariants pass.

## Reminder Interpretation Request

One interpretation request, containing a single natural-language request and optional controlled temporal context.

| Field | Type | Required | Validation / meaning |
|---|---|---:|---|
| `text` | string | Yes | Trimmed; 1–4,000 Unicode characters after trimming. Empty or overlong values are rejected as invalid HTTP input. |
| `reference_context` | object or null | No | Explicit context for relative-date interpretation; never populated from system clock. |
| `reference_context.reference_instant` | RFC 3339 date-time with offset | When context supplied | The reference instant supplied by the caller. |
| `reference_context.time_zone` | IANA time-zone identifier | When context supplied | Must be a recognized zone; required with the reference instant. |

If relative timing is requested but reference context is unavailable, the result must ask for clarification or preserve unresolved timing.

## Reminder Interpretation Result

The top-level result returned for all semantically processed requests.

| Field | Type | Required | Validation / meaning |
|---|---|---:|---|
| `schema_version` | string | Yes | Current contract version, initially `1.0`. |
| `status` | enum | Yes | `ready`, `needs_clarification`, `invalid`, or `unsupported`. |
| `reminder` | Reminder Draft or null | Yes | Complete or partial extracted reminder; may not be marked ready unless ready invariants pass. |
| `clarification_questions` | array of strings | Yes | Empty unless clarification is needed; questions are specific to unresolved material fields. |
| `unresolved_fields` | array of field paths | Yes | Explicit fields that cannot safely be resolved; empty when none. |
| `issues` | array of Interpretation Issue | Yes | Empty for an unambiguous ready result; otherwise bounded issue codes and safe descriptions. |

### Reminder Draft

| Field | Type | Required | Validation / meaning |
|---|---|---:|---|
| `title` | string or null | Yes | Concise action title, non-empty when supplied; null if not safely extractable. |
| `due` | Due Time or null | Yes | Local date/time or broad time-of-day as stated/derived; null if no safe due interpretation exists. |
| `recurrence` | Recurrence or null | Yes | Present only when recurrence is stated or safely derived. |
| `follow_ups` | array of Follow-up Instruction | Yes | Snooze, rescheduling, or conditional follow-up instructions, preserved separately from primary due time. |
| `additional_instructions` | array of strings | Yes | Supported user instructions that do not fit structured fields; must not replace explicit fields. |

### Due Time

| Field | Type | Required | Validation / meaning |
|---|---|---:|---|
| `local_date` | ISO date or null | Yes | Date in the user's intended local calendar; null while unresolved. |
| `local_time` | 24-hour local time or null | Yes | Exact clock time only when present or safely derivable. |
| `time_of_day` | `morning`, `afternoon`, `evening`, `night`, or null | Yes | Preserves broad wording without converting it to an invented clock time. |
| `time_zone` | IANA zone or null | Yes | Only when stated or supplied in reference context. |
| `precision` | `exact`, `broad`, or `unresolved` | Yes | `exact` requires date and local time; `broad` requires a date and time-of-day; `unresolved` must not imply an actionable exact time. |

### Recurrence

| Field | Type | Required | Validation / meaning |
|---|---|---:|---|
| `frequency` | `daily`, `weekly`, `monthly`, or `yearly` | Yes | Frequency explicitly stated or safely derivable. Unsupported/custom patterns require clarification or an issue. |
| `interval` | positive integer | Yes | Defaults to 1 only when the frequency phrase directly implies it (for example, “every day”). |
| `weekdays` | array of weekday codes | Yes | Empty unless specified or required by a weekly pattern. |
| `ends_on` | ISO date or null | Yes | No end date is invented. |
| `occurrence_count` | positive integer or null | Yes | No count is invented. |

### Follow-up Instruction

| Field | Type | Required | Validation / meaning |
|---|---|---:|---|
| `kind` | `snooze`, `reschedule`, or `conditional_follow_up` | Yes | The instruction type expressed by the user. |
| `delay_minutes` | positive integer or null | Yes | Present only when a duration can be safely normalized. |
| `condition` | `if_incomplete` or null | Yes | Preserves the incomplete-task condition when present. |
| `target` | string or null | Yes | Target reminder/action if stated; otherwise null. |

### Interpretation Issue

| Field | Type | Required | Validation / meaning |
|---|---|---:|---|
| `code` | bounded enum/string | Yes | Stable machine-readable issue code, such as `ambiguous_time`, `invalid_date`, `contradictory_timing`, or `unsupported_request`. |
| `field` | string or null | Yes | Relevant field path, if known. |
| `message` | string | Yes | Safe, concise user-facing explanation; no provider internals. |

## Evaluation Case

Immutable versioned evaluation input and expected properties. Contains case ID, category, request text, reference context, expected status, required and forbidden facts/fields, invariant assertions, semantic rubric, and spec requirement trace IDs. A case set must contain at least 15 cases across all FR-014 categories.

## Evaluation Run and Case Result

An evaluation run records run ID, case-set version, run date/time, provider kind, model/SDK version when applicable, run index per case, thresholds, and aggregate results. Each case result records the normalized output, schema pass, invariant/property results, rubric scores, expected-behavior pass, safe failure category, and evidence reference. Repair runs append new evidence and never overwrite prior results.

## Human Review Record

Records reviewer identity, review date, case-set and run IDs reviewed, decision (`approved` or `rejected`), findings, accepted limitations, and follow-up actions. A record is required before feature acceptance; an automated pass is not equivalent to approval.

## Cross-Entity Invariants

- A `ready` result has a reminder with a non-empty title, a resolved local date, and an exact or explicitly broad time; it has no unresolved fields, clarification questions, or blocking issues.
- A `needs_clarification` result has at least one question and at least one unresolved field; it is not ready for action.
- `invalid` and `unsupported` results include at least one issue and are never presented as ready.
- Exact precision requires a date and local time. Broad precision requires a date and a broad time-of-day; it never includes an invented local clock time.
- A relative date/time is only resolved from user wording plus explicit reference context.
- Recurrence boundaries, time zones, follow-up conditions, and delays are not invented.
- Model output that fails JSON parsing, schema validation, or invariants is rejected as a provider/model-output failure and is not returned as an interpretation.
- Evaluation thresholds are all enforced independently: schema 100%, invariants 100%, semantic mean at least 85%, reliability at least 90%, and weighted aggregate at least 90%.
