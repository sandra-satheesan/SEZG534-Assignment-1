import json

import pytest
from app.api.errors import ProviderOutputError
from app.prompts.reminder_interpretation import build_interpretation_prompt
from app.schemas.requests import InterpretationRequest
from app.schemas.responses import InterpretationResult
from app.services.invariants import validate_interpretation_result

REFERENCE_CONTEXT = {
    "reference_instant": "2026-11-03T09:00:00+05:30",
    "time_zone": "Asia/Kolkata",
}


def request(text: str, context: dict | None = REFERENCE_CONTEXT) -> InterpretationRequest:
    return InterpretationRequest.model_validate(
        {"text": text, "reference_context": context}
    )


def result(payload: dict) -> InterpretationResult:
    return InterpretationResult.model_validate_json(json.dumps(payload))


def clarification(
    *,
    question: str,
    unresolved_fields: list[str],
) -> dict:
    return {
        "schema_version": "1.0",
        "status": "needs_clarification",
        "reminder": None,
        "clarification_questions": [question],
        "unresolved_fields": unresolved_fields,
        "issues": [],
    }


def ready(
    *,
    title: str,
    local_date: str,
    local_time: str | None,
    time_of_day: str | None,
    recurrence: dict | None = None,
    follow_ups: list[dict] | None = None,
) -> dict:
    return {
        "schema_version": "1.0",
        "status": "ready",
        "reminder": {
            "title": title,
            "due": {
                "local_date": local_date,
                "local_time": local_time,
                "time_of_day": time_of_day,
                "time_zone": "Asia/Kolkata",
                "precision": "broad" if time_of_day else "exact",
            },
            "recurrence": recurrence,
            "follow_ups": follow_ups or [],
            "additional_instructions": [],
        },
        "clarification_questions": [],
        "unresolved_fields": [],
        "issues": [],
    }


def test_prompt_computes_next_monday_without_inventing_evening_time() -> None:
    prompt = build_interpretation_prompt(
        request("Remind me to submit my assignment next Monday evening.")
    )

    assert "next monday resolves to 2026-11-09" in prompt
    assert "broad time-of-day wording must leave local_time unset" in prompt.lower()
    assert "use it in due.time_zone" in prompt


def test_daily_recurrence_facts_are_explicitly_supplied_to_provider() -> None:
    prompt = build_interpretation_prompt(
        request("Remind me to take medicine every day at 8 AM.")
    )

    assert "recurrence is daily with interval 1" in prompt
    assert "no end boundary" in prompt


def test_next_monday_evening_result_matches_expected_interpretation() -> None:
    reminder_request = request("Remind me to submit my assignment next Monday evening.")
    interpretation = result(
        ready(
            title="submit my assignment",
            local_date="2026-11-09",
            local_time=None,
            time_of_day="evening",
        )
    )

    assert validate_interpretation_result(reminder_request, interpretation) == interpretation


def test_follow_up_facts_are_explicitly_supplied_to_provider() -> None:
    prompt = build_interpretation_prompt(
        request(
            "Remind me to pay the electricity bill in two days. "
            "If I do not complete it, remind me again after 30 minutes."
        )
    )

    assert "primary due date resolves to 2026-11-05" in prompt
    assert "follow-up delay is exactly 30 minutes" in prompt
    assert "follow-up condition is if_incomplete" in prompt
    assert "one follow_ups item" in prompt


def test_daily_recurrence_result_matches_expected_interpretation() -> None:
    reminder_request = request("Remind me to take medicine every day at 8 AM.")
    interpretation = result(
        ready(
            title="take medicine",
            local_date="2026-11-04",
            local_time="08:00",
            time_of_day=None,
            recurrence={
                "frequency": "daily",
                "interval": 1,
                "weekdays": [],
                "ends_on": None,
                "occurrence_count": None,
            },
        )
    )

    assert validate_interpretation_result(reminder_request, interpretation) == interpretation


def test_missing_date_time_clarification_does_not_use_time_of_day_field() -> None:
    reminder_request = request("Remind me to call my manager.", None)
    valid = result(
        {
            **clarification(
                question="When would you like to be reminded?",
                unresolved_fields=["due.local_date", "due.local_time", "due.time_zone"],
            ),
            "reminder": {
                "title": "call my manager",
                "due": None,
                "recurrence": None,
                "follow_ups": [],
                "additional_instructions": [],
            },
        }
    )

    assert validate_interpretation_result(reminder_request, valid) == valid


def test_unsupported_unresolved_field_is_rejected() -> None:
    reminder_request = request("Remind me to call my manager.", None)
    invalid = result(
        {
            **clarification(
                question="When would you like to be reminded?",
                unresolved_fields=["due.time_of_day"],
            ),
            "reminder": None,
        }
    )

    with pytest.raises(ProviderOutputError, match="unsupported unresolved field"):
        validate_interpretation_result(reminder_request, invalid)


def test_multiple_times_prompt_requires_explicit_choice() -> None:
    prompt = build_interpretation_prompt(
        request("Remind me tomorrow at 8 AM and tomorrow at 9 AM.")
    )

    assert "reminder null" in prompt
    assert "8 AM or 9 AM tomorrow" in prompt


def test_multiple_times_clarification_names_both_times() -> None:
    reminder_request = request("Remind me tomorrow at 8 AM and tomorrow at 9 AM.")
    valid = result(
        clarification(
            question="Would you like 8 AM or 9 AM tomorrow?",
            unresolved_fields=["reminder.title"],
        )
    )

    assert validate_interpretation_result(reminder_request, valid) == valid
    assert "8 AM" in valid.clarification_questions[0]
    assert "9 AM" in valid.clarification_questions[0]
