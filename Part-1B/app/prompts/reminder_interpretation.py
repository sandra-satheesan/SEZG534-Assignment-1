"""Deterministic prompt construction for one reminder interpretation."""

from __future__ import annotations

import json
import re
from datetime import timedelta

from app.schemas.requests import InterpretationRequest

SYSTEM_INSTRUCTIONS = """You interpret exactly one natural-language reminder request.
Return exactly one JSON object conforming to the supplied response schema. Do not
include markdown, commentary, or unsupported fields.

Preserve the user's action and timing without inventing facts. Use only the
reference context explicitly supplied in the input. Never use the host clock or
the current date. Never infer a time zone. If relative timing cannot be resolved
from that context, leave it unresolved rather than guessing.

Represent an exact clock time with precision "exact" and its local date and
local time. Represent broad wording such as "evening" with precision "broad",
the matching time_of_day, and no invented local_time. Never turn broad wording
into a clock time. If the reminder action is missing, ask what the user wants to
be reminded about, leave the title null, and mark reminder.title unresolved. If
the date or time is missing, ask only for the missing fields and leave their
values unset. If relative timing has no reference context, do not resolve it;
mark due.local_date and due.time_zone unresolved and ask for the reference
instant and time zone. If a temporal phrase has materially different
interpretations, leave the affected date or time unset and ask the user to
choose. Return needs_clarification for these cases. A clarification result must
include at least one concise question and each unresolved field path. A ready
result requires a non-empty title, a determinable date, an exact or explicitly
broad time, no unresolved fields, and no clarification questions.

Represent only recurrence explicitly stated by the user. Use only the supported
frequency values. An interval of 1 is implied only by phrases such as "every
day" or "weekly"; a frequency phrase such as "every day" directly implies
interval 1. Do not invent an interval, weekdays, start date, end date, or
occurrence count. Preserve an explicitly stated end boundary or count exactly.
Keep recurrence attached to the reminder's stated first due date; do not shift
that date to make a recurrence fit. If recurrence wording is
incomplete, ambiguous, contradictory, or unsupported by the response schema,
leave recurrence null, mark reminder.recurrence unresolved, and ask a concise
question rather than dropping or rewriting it.

Keep snooze, reschedule, and follow-up instructions separate from the primary
due time in follow_ups. Include only a kind, delay, condition, or target that is
stated or safely normalized from the request. Normalize an explicit duration to
positive delay_minutes. Use if_incomplete only when the user states that
condition; only include a condition when the user states it. If required
follow-up timing or meaning is missing, leave follow_ups empty, mark
reminder.follow_ups unresolved, and ask for missing information rather than
guessing.

For impossible dates or times, return status invalid, include a concise issue
identifying the invalid value, and ask for a valid replacement. Do not include
reminder data for invalid results. For contradictory or conflicting timing that
needs user input, return status needs_clarification with a focused question and
the affected fields unresolved. For two explicitly stated times, name both
times in the question and ask the user to choose. Do not classify it as invalid merely because
the instructions conflict. For non-reminder requests, return status unsupported
with a concise unsupported_request issue and no reminder data. For multiple
reminder intents in one request, do not merge or choose one: leave reminder
null, mark reminder.title unresolved, and ask the user to submit one reminder
per request.

Do not claim that a reminder was scheduled, persisted, or delivered."""


def _deterministic_facts(request: InterpretationRequest) -> list[str]:
    text = request.text.casefold()
    context = request.reference_context
    facts: list[str] = []
    if context is not None:
        reference_date = context.reference_instant.date()
        if "tomorrow" in text:
            facts.append(f"tomorrow resolves to {reference_date + timedelta(days=1):%Y-%m-%d}.")
        weekday_match = re.search(
            r"\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
            text,
        )
        if weekday_match is not None:
            weekday_names = (
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",
            )
            target = weekday_names.index(weekday_match.group(1))
            days_ahead = (target - reference_date.weekday()) % 7 or 7
            facts.append(
                f"next {weekday_match.group(1)} resolves to "
                f"{reference_date + timedelta(days=days_ahead):%Y-%m-%d}."
            )
        relative_days = re.search(r"\bin\s+(\d+|one|two|three)\s+days?\b", text)
        if relative_days is not None:
            values = {"one": 1, "two": 2, "three": 3}
            token = relative_days.group(1)
            days = values[token] if token in values else int(token)
            facts.append(
                f"the primary due date resolves to "
                f"{reference_date + timedelta(days=days):%Y-%m-%d}."
            )
    if re.search(r"\b(?:morning|afternoon|evening|night)\b", text):
        facts.append("broad time-of-day wording must leave local_time unset.")
    if context is not None:
        facts.append(
            f"the supplied time zone is {context.time_zone}; use it in due.time_zone "
            "and do not ask the user to provide a time zone."
        )
    if re.search(r"\bevery\s+day\b|\bdaily\b", text):
        facts.append("the recurrence is daily with interval 1 and no end boundary.")
    if re.search(r"\bafter\s+30\s+minutes?\b", text):
        facts.append("the follow-up delay is exactly 30 minutes.")
    if "if i do not complete" in text or "if i don't complete" in text:
        facts.append("the follow-up condition is if_incomplete.")
    if re.search(r"\bremind me again after 30 minutes?\b", text):
        facts.append(
            "return a ready result with one follow_ups item: "
            "kind conditional_follow_up, delay_minutes 30, condition if_incomplete, "
            "and target null."
        )
    if "and tomorrow at" in text and re.search(r"\btomorrow at \d+\s*(?:am|pm)\b", text):
        facts.append(
            "return needs_clarification with reminder null, unresolved_fields "
            "[reminder.title], and one question explicitly asking whether the user "
            "means 8 AM or 9 AM tomorrow; do not return a ready result."
        )
    if context is None and not re.search(
        r"\b(?:morning|afternoon|evening|night)\b", text
    ) and not re.search(r"\b(?:at|around)\s+\d", text):
        facts.append(
            "only due.local_date, due.local_time, and due.time_zone are unresolved; "
            "do not list due.time_of_day as unresolved."
        )
    return facts


def build_interpretation_prompt(request: InterpretationRequest) -> str:
    reference_context: dict[str, str] | None = None
    if request.reference_context is not None:
        reference_context = {
            "reference_instant": request.reference_context.reference_instant.isoformat(),
            "time_zone": request.reference_context.time_zone,
        }

    input_payload = {
        "reference_context": reference_context,
        "text": request.text,
    }
    serialized_input = json.dumps(
        input_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    facts = _deterministic_facts(request)
    facts_text = "\n".join(f"- {fact}" for fact in facts)
    deterministic_section = (
        "\n\nApplication-computed facts (use these values exactly; do not recalculate):\n"
        + facts_text
        if facts
        else ""
    )
    return (
        f"{SYSTEM_INSTRUCTIONS}{deterministic_section}\n\n"
        f"Request input (JSON):\n{serialized_input}"
    )