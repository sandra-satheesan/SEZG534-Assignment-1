# Feature Specification: Natural-Language Reminder Agent

**Feature Branch**: `not specified`

**Created**: 2026-11-03

**Status**: Draft

**Input**: User description: Build a Natural-Language Reminder Agent for Part 1B that converts natural-language reminder requests into structured, actionable reminder data; supports relative dates, recurrence, snooze and rescheduling instructions; asks about ambiguity or missing information; avoids inventing facts; handles invalid or unsupported requests; and is evaluated with repeatable quality checks and human acceptance.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create a reminder from a clear request (Priority: P1)

A person submits a clear request and receives structured reminder details that preserve the requested activity and timing.

**Why this priority**: Converting an ordinary request into accurate reminder data is the primary user value.

**Independent Test**: Submit requests with explicit and relative dates and compare the returned title and scheduled time with the request and a supplied reference date, time, and time zone.

**Acceptance Scenarios**:

1. **Given** a reference date and time zone are available, **When** the person asks, “Remind me to call Rahul tomorrow at 10 AM,” **Then** the result identifies “call Rahul,” resolves tomorrow to the correct calendar date, and records 10:00 AM in the reference time zone.
2. **Given** the reference date is available, **When** the person asks, “Remind me to submit my assignment next Monday evening,” **Then** the result identifies the activity and Monday’s date, and does not invent an exact clock time for “evening.”
3. **Given** all required details are clear, **When** the request is interpreted, **Then** the person receives valid structured JSON with no unsupported or contradictory values.

### User Story 2 - Clarify incomplete or ambiguous requests (Priority: P1)

A person can complete a reminder request when essential information is missing or has multiple materially different interpretations.

**Why this priority**: A reminder with invented timing can cause missed or mistimed actions; requesting clarification preserves user intent.

**Independent Test**: Submit incomplete and ambiguous requests and verify the response identifies missing or ambiguous fields, asks a concise question, and leaves unresolved values unset.

**Acceptance Scenarios**:

1. **Given** the person asks, “Remind me to call my manager,” **When** no date or time is provided, **Then** the result asks which date and time to use and does not assign either.
2. **Given** a request could reasonably resolve to two different dates or times, **When** it is interpreted, **Then** the result identifies the ambiguity and asks the person to choose rather than silently selecting one.
3. **Given** a required reference date or time zone is unavailable for interpreting relative timing, **When** the request depends on that context, **Then** the result asks for the missing context or preserves the date as unresolved.

### User Story 3 - Capture recurrence and follow-up instructions (Priority: P2)

A person can describe recurring reminders and conditional follow-up behavior without losing those instructions.

**Why this priority**: Recurrence and follow-up language are explicit core capabilities but depend on reliable extraction of the primary reminder.

**Independent Test**: Submit recurring, snooze, and rescheduling requests and verify each instruction is represented distinctly and faithfully.

**Acceptance Scenarios**:

1. **Given** the person asks, “Remind me to take medicine every day at 8 AM,” **When** the request is interpreted, **Then** the result includes a daily recurrence and 8:00 AM, without an invented end date.
2. **Given** the person asks, “Remind me to pay electricity bill in two days. If I don't complete it, remind me again after 30 minutes,” **When** the request is interpreted, **Then** the result captures the initial due time and a conditional 30-minute follow-up, including the condition that the task remains incomplete.
3. **Given** a recurrence or follow-up instruction is contradictory or cannot be represented, **When** the request is interpreted, **Then** the result identifies the conflict or unsupported detail and does not silently discard or alter it.

### User Story 4 - Receive safe handling of invalid or unsupported requests (Priority: P2)

A person receives a useful, structured response when a request cannot be interpreted as a valid reminder.

**Why this priority**: Clear failure handling prevents malformed reminder data from being mistaken for an actionable reminder.

**Independent Test**: Submit invalid, contradictory, and unsupported requests and confirm each response is valid JSON, states the issue, and does not present an invalid reminder as ready.

**Acceptance Scenarios**:

1. **Given** the request contains an impossible date or time, **When** it is interpreted, **Then** the response identifies the invalid value and asks for a valid replacement.
2. **Given** the request contains mutually contradictory timing instructions, **When** it is interpreted, **Then** the response describes the conflict and requests clarification.
3. **Given** the request is unrelated to reminder creation or includes an unsupported instruction, **When** it is interpreted, **Then** the response identifies the unsupported content and does not claim that it has been scheduled.

### User Story 5 - Evaluate and accept interpretation quality (Priority: P1)

A reviewer can assess quality across a representative set of requests, inspect failures, require repairs, and make the final acceptance decision.

**Why this priority**: AI output can vary between runs, so a single successful example is insufficient evidence of reliability.

**Independent Test**: Run a fixed evaluation set repeatedly, verify its per-case and aggregate results against the stated thresholds, repair a failing result, rerun the same set, and obtain an explicit human decision.

**Acceptance Scenarios**:

1. **Given** an evaluation set contains at least 15 cases, **When** evaluation runs, **Then** it reports schema correctness, invariant/property correctness, semantic quality, reliability, and an aggregate score.
2. **Given** an evaluation result is below any required acceptance threshold, **When** a repair is made, **Then** the complete evaluation set is rerun and the new results are reported alongside the prior results.
3. **Given** automated results meet all thresholds, **When** human review has not yet been recorded, **Then** the feature remains unaccepted.

### Edge Cases

- Relative dates cross a month, year, daylight-saving transition, or other local-clock change.
- A phrase such as “next Monday” has different interpretations under common conventions or is near the reference date.
- A broad time-of-day phrase such as “evening” is supplied where an exact clock time is required.
- The request omits a date, time, time zone, or reference date needed to determine timing.
- A recurrence has an explicit end date, count, or exception, or conflicts with another timing instruction.
- A snooze or follow-up instruction omits its condition, duration, or target reminder.
- Several reminders or actions are included in one request.
- The request includes an invalid calendar date, impossible time, past due time, or contradictory requirements.
- A request is empty, excessively long, malformed, in an unsupported language, or unrelated to reminders.
- An interpretation varies between repeated evaluations or includes extra, missing, or mistyped JSON fields.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST accept a natural-language request and return a structured result that identifies whether it is ready, needs clarification, invalid, or unsupported.
- **FR-002**: For a ready reminder, the result MUST represent the reminder title, date and time when determinable, recurrence when present, and additional instructions when present.
- **FR-003**: The result MUST distinguish an exact date/time from a broad time-of-day phrase and MUST NOT silently convert a broad phrase such as “evening” into an exact clock time.
- **FR-004**: The system MUST resolve relative dates and times only using an explicitly available reference date, reference time, and applicable time zone; when required context is absent, it MUST ask or preserve the value as unresolved.
- **FR-005**: The system MUST preserve the user's stated local date and time meaning across calendar boundaries and local-clock changes, or identify when it cannot do so reliably.
- **FR-006**: The system MUST represent recurrence frequency and relevant boundaries or exceptions only when supported by the request; it MUST NOT invent an end date or recurrence limit.
- **FR-007**: The system MUST identify snooze, rescheduling, and conditional follow-up instructions and preserve their timing and conditions separately from the primary due time.
- **FR-008**: The system MUST ask a concise, relevant clarifying question when required information is absent or multiple reasonable interpretations would produce materially different reminder data.
- **FR-009**: While clarification is required, the system MUST leave unresolved values unset and MUST NOT present the reminder as ready for action.
- **FR-010**: The system MUST identify invalid dates, impossible times, contradictory instructions, and unsupported requests without claiming successful interpretation or scheduling.
- **FR-011**: Every response MUST be valid JSON conforming to a documented, versioned response schema, including responses that need clarification or report invalid or unsupported input.
- **FR-012**: The response schema MUST make the status, extracted reminder data, unresolved or invalid fields, clarifying question(s), and relevant explanation distinguishable; fields that do not apply MUST use the schema's defined empty or null representation.
- **FR-013**: The system MUST NOT invent a title, date, time, recurrence, time zone, condition, or other user instruction that is not stated or safely derivable from supplied context.
- **FR-014**: The evaluation set MUST contain at least 15 documented cases covering clear requests, relative timing, recurrence, follow-up instructions, ambiguous and incomplete requests, invalid and contradictory input, and unsupported requests.
- **FR-015**: The evaluation process MUST account for non-deterministic output by evaluating every case at least three times under the same documented reference context and retaining per-case, per-run results.
- **FR-016**: Evaluation MUST separately report schema correctness, invariant/property checks, semantic quality, and overall reliability, and MUST calculate an aggregate score using documented scoring rules.
- **FR-017**: Acceptance MUST require 100% schema correctness and 100% invariant/property correctness across evaluation runs, a mean semantic-quality score of at least 85%, and an aggregate score of at least 90%. The aggregate MUST NOT conceal a failure of either 100% requirement.
- **FR-018**: Semantic quality MUST assess preservation of user intent, correct interpretation of supplied date/time context, faithful recurrence and follow-up extraction, and appropriate clarification or rejection instead of invented values.
- **FR-019**: Overall reliability MUST report the proportion of evaluated outputs that satisfy the case's expected behavior across repeated runs; the acceptance threshold MUST be at least 90%.
- **FR-020**: When evaluation fails an acceptance threshold, the evaluation report MUST identify failing cases and properties, support repair, and permit rerunning the complete unchanged evaluation set; the repaired result MUST be reported against the same thresholds.
- **FR-021**: Evaluation case inputs, expected properties, reference contexts, scoring rules, thresholds, run counts, and results MUST be retained sufficiently for another reviewer to reproduce and inspect the evaluation.
- **FR-022**: A human reviewer MUST inspect the specification, evaluation coverage, aggregate and per-case evidence, and remaining failures or limitations before acceptance.
- **FR-023**: Human acceptance MUST be an explicit recorded decision by the reviewer; passing automated evaluation alone MUST NOT mark the feature accepted.
- **FR-024**: The feature MUST interpret requests and produce actionable reminder data only; scheduling reminders and delivering notifications are outside scope.
- **FR-025**: The feature MUST remain isolated to Part 1B; its specification and subsequent feature artifacts MUST be kept under `Part-1B/specs/001-natural-language-reminder-agent/`, without changing Part 1A behavior or its acceptance evidence.

### Key Entities *(include if feature involves data)*

- **Reminder Request**: The original user wording and any reference date, reference time, or time-zone context supplied for interpretation.
- **Reminder Result**: The structured interpretation, including status, title, determinable timing, recurrence, additional instructions, unresolved fields, and explanation.
- **Clarification**: A focused question and the unresolved information needed before a reminder can be treated as ready.
- **Evaluation Case**: A documented request, reference context, expected output properties, and quality criteria used to assess interpretation.
- **Evaluation Run**: The outputs and per-case measurements from one execution of the evaluation set, associated with its scoring rules and aggregate result.
- **Human Review Decision**: The reviewer's recorded acceptance or rejection, including findings, limitations, and decision date.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Across the accepted evaluation set and at least three runs per case, 100% of responses are valid and conform to the documented response schema.
- **SC-002**: Across the accepted evaluation set and repeated runs, 100% of checked invariants hold, including no invented unresolved date/time and no ready status while required clarification remains.
- **SC-003**: Mean semantic-quality score is at least 85%, aggregate score is at least 90%, and at least 90% of all evaluated outputs satisfy their expected behavior.
- **SC-004**: The evaluation set contains at least 15 cases and covers every category named in FR-014.
- **SC-005**: Every failed threshold is linked to inspectable cases and properties, and a complete rerun of the same evaluation set can establish whether a repair meets all thresholds.
- **SC-006**: Before acceptance, a human reviewer records an explicit decision after reviewing the specification and evaluation evidence; automated results alone do not count as acceptance.
- **SC-007**: In a human usability review, at least 4 of 5 representative users can identify the reminder title, timing, recurrence or follow-up instructions, and any requested clarification from the returned result without additional explanation.

## Assumptions

- The initial supported language is English; additional languages require explicit evaluation coverage before they are represented as supported.
- The feature converts requests into reminder data only; it does not schedule reminders or deliver notifications.
- A reminder with no requested recurrence is one-time. A recurrence without an explicit end condition continues until the user changes or cancels it.
- If an exact time cannot be derived without guessing, the result remains unresolved or retains a supported broad time-of-day expression and asks a question when needed.
- A supplied time zone is authoritative. If relative timing depends on a time zone that is unavailable, the system asks for it rather than silently choosing one.
- Evaluation cases provide controlled reference dates, times, and time zones wherever relative-time correctness is assessed; evaluation does not depend on the machine's current clock.
- The exact response schema and scoring rubric must be documented before evaluation is run, but their detailed design is deferred to planning.
- Human review is required for acceptance, including review of errors and documented limitations even when automated thresholds pass.
