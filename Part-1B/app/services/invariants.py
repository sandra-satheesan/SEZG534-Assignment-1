"""Cross-field invariants for ready and clarification results."""

from __future__ import annotations

import re
from datetime import date, datetime

from app.api.errors import ProviderOutputError
from app.schemas.requests import InterpretationRequest
from app.schemas.responses import (
    FollowUpInstruction,
    InterpretationResult,
    Recurrence,
    ReminderDraft,
)

UNRESOLVED_FIELD_PATHS = {
    "reminder.title",
    "due",
    "due.local_date",
    "due.local_time",
    "due.time_zone",
    "reminder.recurrence",
    "reminder.follow_ups",
}

WEEKDAYS = {
    "MO": ("monday", "mon"),
    "TU": ("tuesday", "tue", "tues"),
    "WE": ("wednesday", "wed"),
    "TH": ("thursday", "thu", "thur", "thurs"),
    "FR": ("friday", "fri"),
    "SA": ("saturday", "sat"),
    "SU": ("sunday", "sun"),
}
NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
}


def _request_text(request: InterpretationRequest) -> str:
    return request.text.casefold()


def _has_recurrence_request(text: str) -> bool:
    return bool(
        re.search(
            r"\b(?:daily|weekly|monthly|yearly|annually|everyday|"
            r"every\s+(?:day|week|month|year|weekday|weekdays|weekend|weekends|"
            r"other\s+(?:day|week|weekday|weekdays)|"
            r"\d+|one|two|three|four|five|six|seven|eight|nine|ten|"
            r"monday|tuesday|wednesday|thursday|friday|saturday|sunday)|"
            r"once\s+a\s+(?:day|week|month|year))\b",
            text,
        )
    )


def _frequency_is_explicit(frequency: str, text: str) -> bool:
    interval_words = (
        r"other|\d+|one|two|three|four|five|six|seven|eight|nine|ten"
    )
    patterns = {
        "daily": (
            rf"\b(?:daily|everyday|every\s+(?:day|(?:{interval_words})\s+days?)|"
            r"once\s+a\s+day)\b"
        ),
        "weekly": (
            r"\b(?:weekly|every\s+week|once\s+a\s+week|every\s+(?:other|\d+|"
            r"one|two|three|four|five|six|seven|eight|nine|ten)\s+weeks?|"
            r"every\s+(?:weekday|weekdays|weekend|weekends|monday|tuesday|wednesday|"
            r"thursday|friday|saturday|sunday))\b"
        ),
        "monthly": (
            rf"\b(?:monthly|every\s+(?:month|(?:{interval_words})\s+months?)|"
            r"once\s+a\s+month)\b"
        ),
        "yearly": (
            rf"\b(?:yearly|annually|every\s+(?:year|(?:{interval_words})\s+years?)|"
            r"once\s+a\s+year)\b"
        ),
    }
    return bool(re.search(patterns[frequency], text))


def _number_value(token: str) -> int | None:
    if token.isdigit():
        return int(token)
    return NUMBER_WORDS.get(token)


def _interval_is_explicit(recurrence: Recurrence, text: str) -> bool:
    unit = {
        "daily": r"days?",
        "weekly": r"weeks?",
        "monthly": r"months?",
        "yearly": r"years?",
    }[recurrence.frequency]
    match = re.search(
        rf"\bevery\s+(?P<count>\d+|[a-z]+)\s+{unit}\b|\bevery\s+other\s+{unit}\b",
        text,
    )
    if match is None:
        return recurrence.interval == 1
    if match.group("count") is None:
        return recurrence.interval == 2
    return _number_value(match.group("count")) == recurrence.interval


def _weekday_is_explicit(weekday: str, text: str) -> bool:
    aliases = WEEKDAYS[weekday]
    if any(re.search(rf"\b{re.escape(alias)}\b", text) for alias in aliases):
        return True
    if weekday in {"MO", "TU", "WE", "TH", "FR"} and re.search(r"\bweekdays?\b", text):
        return True
    return weekday in {"SA", "SU"} and re.search(r"\bweekends?\b", text) is not None


def _explicit_end_date(text: str) -> date | None:
    marker = r"\b(?:until|through|ending\s+on|ends?\s+on)\s+"
    iso_match = re.search(rf"{marker}(?P<value>\d{{4}}-\d{{2}}-\d{{2}})\b", text)
    if iso_match is not None:
        try:
            return date.fromisoformat(iso_match.group("value"))
        except ValueError:
            return None

    month_names = (
        r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
        r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
    )
    month_match = re.search(
        rf"{marker}(?P<value>(?:{month_names})\s+\d{{1,2}}(?:st|nd|rd|th)?[,]?\s+\d{{4}})",
        text,
    )
    if month_match is None:
        return None
    date_text = re.sub(r"(\d)(st|nd|rd|th)", r"\1", month_match.group("value"))
    for date_format in ("%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y"):
        try:
            return datetime.strptime(date_text, date_format).date()
        except ValueError:
            continue
    return None


def _count_is_explicit(text: str, count: int) -> bool:
    count_text = str(count)
    count_words = [word for word, value in NUMBER_WORDS.items() if value == count]
    tokens = [re.escape(count_text), *(re.escape(word) for word in count_words)]
    return bool(
        re.search(
            rf"\bfor\s+(?:{'|'.join(tokens)})\s+(?:times|occurrences|instances)\b",
            text,
        )
    )


def _explicit_occurrence_count(text: str) -> int | None:
    match = re.search(r"\bfor\s+(?P<count>\d+|[a-z]+)\s+(?:times|occurrences|instances)\b", text)
    return _number_value(match.group("count")) if match is not None else None


def _validate_recurrence(recurrence: Recurrence, text: str) -> None:
    if not _frequency_is_explicit(recurrence.frequency, text):
        raise ProviderOutputError("Recurrence frequency is not supported by the request.")
    if not _interval_is_explicit(recurrence, text):
        raise ProviderOutputError("Recurrence interval is not supported by the request.")
    if any(not _weekday_is_explicit(day, text) for day in recurrence.weekdays):
        raise ProviderOutputError("Recurrence contains an unstated weekday.")
    explicit_end_date = _explicit_end_date(text)
    if recurrence.ends_on is not None and recurrence.ends_on != explicit_end_date:
        raise ProviderOutputError("Recurrence end date does not match the request.")
    if explicit_end_date is not None and recurrence.ends_on != explicit_end_date:
        raise ProviderOutputError("Explicit recurrence end date was omitted from the result.")
    if recurrence.occurrence_count is not None and not _count_is_explicit(
        text, recurrence.occurrence_count
    ):
        raise ProviderOutputError("Recurrence count is not stated by the request.")
    explicit_count = _explicit_occurrence_count(text)
    if explicit_count is not None and recurrence.occurrence_count != explicit_count:
        raise ProviderOutputError("Explicit recurrence count was omitted or changed.")


def _has_follow_up_request(text: str) -> bool:
    return bool(
        re.search(
            r"\b(?:snooze|reschedul\w*|follow[ -]?up|remind\s+me\s+again|"
            r"remind\s+again|again\s+(?:after|in))\b",
            text,
        )
    )


def _follow_up_text(text: str) -> str:
    matches = list(
        re.finditer(
            r"\b(?:snooze|reschedul\w*|follow[ -]?up|remind\s+me\s+again|"
            r"remind\s+again|again\s+(?:after|in))\b",
            text,
        )
    )
    return text[matches[-1].start() :] if matches else text


def _duration_minutes(text: str) -> int | None:
    duration_text = _follow_up_text(text)
    if re.search(r"\bhalf\s+(?:an?|one)\s+hour\b", duration_text):
        return 30
    match = re.search(
        r"\b(?P<count>\d+|[a-z]+)\s*(?P<unit>minutes?|mins?|hours?|days?|weeks?)\b",
        duration_text,
    )
    if match is None:
        return None
    amount = _number_value(match.group("count"))
    if amount is None:
        return None
    unit = match.group("unit")
    multiplier = 1 if unit.startswith(("min",)) else 60 if unit.startswith("hour") else 1440
    if unit.startswith("week"):
        multiplier = 7 * 1440
    return amount * multiplier


def _follow_up_kind_is_explicit(follow_up: FollowUpInstruction, text: str) -> bool:
    if follow_up.kind == "snooze":
        return re.search(r"\bsnooze\b", text) is not None
    if follow_up.kind == "reschedule":
        return re.search(r"\b(?:reschedul\w*|move\s+(?:it|this|the reminder))\b", text) is not None
    return re.search(r"\b(?:follow[ -]?up|again)\b", text) is not None


def _incomplete_condition_is_explicit(text: str) -> bool:
    return bool(
        re.search(
            r"\b(?:incomplete|unfinished|not\s+done|not\s+complete|"
            r"do\s+not\s+complete|don't\s+complete|haven't\s+completed)\b",
            text,
        )
    )


def _validate_follow_ups(follow_ups: list[FollowUpInstruction], text: str) -> None:
    for follow_up in follow_ups:
        if not _follow_up_kind_is_explicit(follow_up, text):
            raise ProviderOutputError("Follow-up kind is not supported by the request.")
        if follow_up.delay_minutes is None:
            raise ProviderOutputError("Follow-up delay is unresolved.")
        if _duration_minutes(text) != follow_up.delay_minutes:
            raise ProviderOutputError("Follow-up delay does not match the request.")
        if follow_up.condition == "if_incomplete" and not _incomplete_condition_is_explicit(text):
            raise ProviderOutputError("Follow-up condition is not stated by the request.")
        if follow_up.condition is None and _incomplete_condition_is_explicit(text):
            raise ProviderOutputError("Follow-up condition was omitted from the result.")


def _validate_recurrence_and_follow_ups(
    request: InterpretationRequest, result: InterpretationResult
) -> None:
    text = _request_text(request)
    reminder = result.reminder
    if reminder is None:
        return

    recurrence_requested = _has_recurrence_request(text)
    if reminder.recurrence is not None:
        if not recurrence_requested:
            raise ProviderOutputError("Recurrence was not requested by the user.")
        _validate_recurrence(reminder.recurrence, text)
    elif recurrence_requested:
        if result.status == "ready" or "reminder.recurrence" not in result.unresolved_fields:
            raise ProviderOutputError("Requested recurrence was dropped without clarification.")

    follow_up_requested = _has_follow_up_request(text)
    if reminder.follow_ups:
        if not follow_up_requested:
            raise ProviderOutputError("Follow-up instruction was not requested by the user.")
        _validate_follow_ups(reminder.follow_ups, text)
    elif follow_up_requested:
        if result.status == "ready" or "reminder.follow_ups" not in result.unresolved_fields:
            raise ProviderOutputError("Requested follow-up was dropped without clarification.")


def _unresolved_value_is_unset(reminder: ReminderDraft | None, field_path: str) -> bool:
    if reminder is None:
        return True
    if field_path == "reminder.title":
        return reminder.title is None
    if field_path == "due":
        return reminder.due is None
    if field_path == "reminder.recurrence":
        return reminder.recurrence is None
    if field_path == "reminder.follow_ups":
        return not reminder.follow_ups
    if reminder.due is None:
        return True
    if field_path == "due.local_date":
        return reminder.due.local_date is None
    if field_path == "due.local_time":
        return reminder.due.local_time is None
    if field_path == "due.time_zone":
        return reminder.due.time_zone is None
    return False


def _require_valid_ready_result(result: InterpretationResult) -> None:
    reminder = result.reminder
    if reminder is None or reminder.title is None or not reminder.title.strip():
        raise ProviderOutputError("Ready result has no reminder title.")
    due = reminder.due
    if due is None or due.local_date is None:
        raise ProviderOutputError("Ready result has no resolved date.")
    has_exact_time = due.precision == "exact" and due.local_time is not None
    has_broad_time = due.precision == "broad" and due.time_of_day is not None
    if not (has_exact_time or has_broad_time):
        raise ProviderOutputError("Ready result has no exact or broad due time.")
    if result.unresolved_fields or result.clarification_questions or result.issues:
        raise ProviderOutputError("Ready result contains unresolved or blocking details.")


def _require_valid_clarification_result(
    request: InterpretationRequest, result: InterpretationResult
) -> None:
    if not result.clarification_questions or not result.unresolved_fields:
        raise ProviderOutputError("Clarification result is missing questions or unresolved fields.")
    if len(set(result.unresolved_fields)) != len(result.unresolved_fields):
        raise ProviderOutputError("Clarification result repeats unresolved fields.")
    if any(field_path not in UNRESOLVED_FIELD_PATHS for field_path in result.unresolved_fields):
        raise ProviderOutputError("Clarification result contains an unsupported unresolved field.")
    if any(
        not _unresolved_value_is_unset(result.reminder, field_path)
        for field_path in result.unresolved_fields
    ):
        raise ProviderOutputError("Clarification result populates a value marked unresolved.")

    context = request.reference_context
    reminder = result.reminder
    due = reminder.due if reminder is not None else None
    if context is not None and due is not None and due.time_zone != context.time_zone:
        raise ProviderOutputError("Clarification result conflicts with supplied time-zone context.")


def _require_valid_failure_result(result: InterpretationResult) -> None:
    if not result.issues:
        raise ProviderOutputError("Invalid or unsupported result is missing an issue.")
    if result.reminder is not None:
        raise ProviderOutputError("Invalid or unsupported result cannot contain reminder data.")


def validate_interpretation_result(
    request: InterpretationRequest, result: InterpretationResult
) -> InterpretationResult:
    """Reject status/data contradictions without repairing provider output."""
    if result.status == "ready":
        _require_valid_ready_result(result)
    elif result.status == "needs_clarification":
        _require_valid_clarification_result(request, result)
    elif result.status in {"invalid", "unsupported"}:
        _require_valid_failure_result(result)
    if result.status in {"ready", "needs_clarification"}:
        _validate_recurrence_and_follow_ups(request, result)
    return result