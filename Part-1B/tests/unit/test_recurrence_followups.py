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


def make_request(text: str) -> InterpretationRequest:
    return InterpretationRequest.model_validate_json(
        json.dumps({"text": text, "reference_context": REFERENCE_CONTEXT})
    )


def make_ready_result(
    *, recurrence: dict | None = None, follow_ups: list[dict] | None = None
) -> InterpretationResult:
    return InterpretationResult.model_validate_json(
        json.dumps(
            {
                "schema_version": "1.0",
                "status": "ready",
                "reminder": {
                    "title": "take medicine",
                    "due": {
                        "local_date": "2026-11-04",
                        "local_time": "08:00",
                        "time_of_day": None,
                        "time_zone": "Asia/Kolkata",
                        "precision": "exact",
                    },
                    "recurrence": recurrence,
                    "follow_ups": follow_ups or [],
                    "additional_instructions": [],
                },
                "clarification_questions": [],
                "unresolved_fields": [],
                "issues": [],
            }
        )
    )


def test_prompt_distinguishes_explicit_recurrence_and_does_not_invent_boundaries() -> None:
    prompt = " ".join(
        build_interpretation_prompt(
            make_request("Remind me to take medicine every day at 8 AM.")
        ).split()
    )

    assert "Represent only recurrence explicitly stated" in prompt
    assert (
        "Do not invent an interval, weekdays, start date, end date, or occurrence count"
        in prompt
    )
    assert 'a frequency phrase such as "every day" directly implies interval 1' in prompt
    assert "If recurrence wording is incomplete, ambiguous, contradictory, or unsupported" in prompt


def test_prompt_keeps_follow_up_separate_and_requires_stated_conditions() -> None:
    prompt = " ".join(
        build_interpretation_prompt(
            make_request(
                "If I do not complete the task, remind me again after 30 minutes."
            )
        ).split()
    )

    assert "Keep snooze, reschedule, and follow-up instructions separate" in prompt
    assert "only include a condition when the user states it" in prompt
    assert "ask for missing information rather than guessing" in prompt


def test_daily_recurrence_accepts_implied_interval_without_invented_boundary() -> None:
    request = make_request("Remind me to take medicine every day at 8 AM.")
    result = make_ready_result(
        recurrence={
            "frequency": "daily",
            "interval": 1,
            "weekdays": [],
            "ends_on": None,
            "occurrence_count": None,
        }
    )

    validate_interpretation_result(request, result)


def test_daily_frequency_accepts_explicit_multi_day_interval() -> None:
    request = make_request("Remind me to take medicine every 2 days at 8 AM.")
    result = make_ready_result(
        recurrence={
            "frequency": "daily",
            "interval": 2,
            "weekdays": [],
            "ends_on": None,
            "occurrence_count": None,
        }
    )

    validate_interpretation_result(request, result)


def test_weekly_recurrence_accepts_only_stated_days_and_end_date() -> None:
    request = make_request(
        "Remind me every Monday and Wednesday at 8 AM until December 1, 2026."
    )
    result = make_ready_result(
        recurrence={
            "frequency": "weekly",
            "interval": 1,
            "weekdays": ["MO", "WE"],
            "ends_on": "2026-12-01",
            "occurrence_count": None,
        }
    )

    validate_interpretation_result(request, result)


def test_conditional_follow_up_accepts_stated_duration_and_condition() -> None:
    request = make_request(
        "Remind me to take medicine every day at 8 AM. If I do not complete it, "
        "remind me again after 30 minutes."
    )
    result = make_ready_result(
        recurrence={
            "frequency": "daily",
            "interval": 1,
            "weekdays": [],
            "ends_on": None,
            "occurrence_count": None,
        },
        follow_ups=[
            {
                "kind": "conditional_follow_up",
                "delay_minutes": 30,
                "condition": "if_incomplete",
                "target": "take medicine",
            }
        ],
    )

    validate_interpretation_result(request, result)


@pytest.mark.parametrize(
    ("text", "recurrence"),
    [
        (
            "Remind me to take medicine every day at 8 AM.",
            {
                "frequency": "daily",
                "interval": 2,
                "weekdays": [],
                "ends_on": None,
                "occurrence_count": None,
            },
        ),
        (
            "Remind me to take medicine every day at 8 AM.",
            {
                "frequency": "daily",
                "interval": 1,
                "weekdays": ["MO"],
                "ends_on": None,
                "occurrence_count": None,
            },
        ),
        (
            "Remind me to take medicine every day at 8 AM.",
            {
                "frequency": "daily",
                "interval": 1,
                "weekdays": [],
                "ends_on": "2026-12-01",
                "occurrence_count": None,
            },
        ),
        (
            "Remind me to take medicine every day at 8 AM.",
            {
                "frequency": "daily",
                "interval": 1,
                "weekdays": [],
                "ends_on": None,
                "occurrence_count": 10,
            },
        ),
        (
            "Remind me to take medicine every 2 weeks on Monday at 8 AM.",
            {
                "frequency": "weekly",
                "interval": 1,
                "weekdays": ["MO"],
                "ends_on": None,
                "occurrence_count": None,
            },
        ),
    ],
    ids=[
        "invented-interval",
        "invented-weekday",
        "invented-end",
        "invented-count",
        "wrong-explicit-interval",
    ],
)
def test_recurrence_cannot_add_unsupported_interval_or_boundary(
    text: str, recurrence: dict
) -> None:
    with pytest.raises(ProviderOutputError):
        validate_interpretation_result(make_request(text), make_ready_result(recurrence=recurrence))


def test_recurrence_cannot_be_added_when_user_did_not_request_it() -> None:
    result = make_ready_result(
        recurrence={
            "frequency": "daily",
            "interval": 1,
            "weekdays": [],
            "ends_on": None,
            "occurrence_count": None,
        }
    )

    with pytest.raises(ProviderOutputError):
        validate_interpretation_result(
            make_request("Remind me to take medicine tomorrow at 8 AM."), result
        )


def test_recurrence_end_date_must_match_explicit_boundary() -> None:
    result = make_ready_result(
        recurrence={
            "frequency": "weekly",
            "interval": 1,
            "weekdays": ["MO"],
            "ends_on": "2026-11-30",
            "occurrence_count": None,
        }
    )

    with pytest.raises(ProviderOutputError):
        validate_interpretation_result(
            make_request(
                "Remind me every Monday at 8 AM until December 1, 2026."
            ),
            result,
        )


def test_follow_up_cannot_add_unstated_delay_or_condition() -> None:
    request = make_request("Remind me to take medicine every day at 8 AM.")
    result = make_ready_result(
        recurrence={
            "frequency": "daily",
            "interval": 1,
            "weekdays": [],
            "ends_on": None,
            "occurrence_count": None,
        },
        follow_ups=[
            {
                "kind": "conditional_follow_up",
                "delay_minutes": 30,
                "condition": "if_incomplete",
                "target": "take medicine",
            }
        ],
    )

    with pytest.raises(ProviderOutputError):
        validate_interpretation_result(request, result)


def test_valid_follow_up_must_preserve_explicit_duration_and_condition() -> None:
    request = make_request(
        "Remind me to take medicine every day at 8 AM. If I do not complete it, "
        "remind me again after 30 minutes."
    )
    result = make_ready_result(
        recurrence={
            "frequency": "daily",
            "interval": 1,
            "weekdays": [],
            "ends_on": None,
            "occurrence_count": None,
        },
        follow_ups=[
            {
                "kind": "conditional_follow_up",
                "delay_minutes": 20,
                "condition": "if_incomplete",
                "target": "take medicine",
            }
        ],
    )

    with pytest.raises(ProviderOutputError):
        validate_interpretation_result(request, result)


@pytest.mark.parametrize(
    ("text", "kind", "delay_minutes"),
    [
        ("Snooze the reminder for 10 minutes.", "snooze", 10),
        ("Reschedule the reminder in 2 hours.", "reschedule", 120),
    ],
)
def test_snooze_and_reschedule_preserve_explicit_delays(
    text: str, kind: str, delay_minutes: int
) -> None:
    request = make_request(f"Remind me to take medicine tomorrow at 8 AM. {text}")
    result = make_ready_result(
        follow_ups=[
            {
                "kind": kind,
                "delay_minutes": delay_minutes,
                "condition": None,
                "target": None,
            }
        ]
    )

    validate_interpretation_result(request, result)