import json

import pytest
from app.main import create_app
from app.schemas.responses import InterpretationResult
from fastapi.testclient import TestClient

REFERENCE_CONTEXT = {
    "reference_instant": "2026-11-03T09:00:00+05:30",
    "time_zone": "Asia/Kolkata",
}


class FakeProvider:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.prompts: list[str] = []

    async def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return json.dumps(self.response)


def result_payload(
    *, recurrence: dict | None = None, follow_ups: list[dict] | None = None
) -> dict:
    return {
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


def post_interpretation(text: str, provider: FakeProvider) -> InterpretationResult:
    app = create_app(provider=provider)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/reminders/interpret",
            json={"text": text, "reference_context": REFERENCE_CONTEXT},
        )

    assert response.status_code == 200, response.text
    return InterpretationResult.model_validate_json(response.text)


def test_daily_recurrence_keeps_explicit_context_and_has_no_invented_end() -> None:
    provider = FakeProvider(
        result_payload(
            recurrence={
                "frequency": "daily",
                "interval": 1,
                "weekdays": [],
                "ends_on": None,
                "occurrence_count": None,
            }
        )
    )

    result = post_interpretation("Remind me to take medicine every day at 8 AM.", provider)

    assert result.reminder is not None
    assert result.reminder.recurrence is not None
    assert result.reminder.recurrence.interval == 1
    assert result.reminder.recurrence.ends_on is None
    assert result.reminder.recurrence.occurrence_count is None
    assert "Asia/Kolkata" in provider.prompts[0]
    assert "2026-11-03T09:00:00+05:30" in provider.prompts[0]


@pytest.mark.parametrize(
    ("text", "recurrence"),
    [
        (
            "Remind me to take medicine every Monday and Wednesday at 8 AM "
            "until December 1, 2026.",
            {
                "frequency": "weekly",
                "interval": 1,
                "weekdays": ["MO", "WE"],
                "ends_on": "2026-12-01",
                "occurrence_count": None,
            },
        ),
        (
            "Remind me to take medicine every 2 weeks on Monday at 8 AM.",
            {
                "frequency": "weekly",
                "interval": 2,
                "weekdays": ["MO"],
                "ends_on": None,
                "occurrence_count": None,
            },
        ),
        (
            "Remind me to take medicine every 2 days at 8 AM.",
            {
                "frequency": "daily",
                "interval": 2,
                "weekdays": [],
                "ends_on": None,
                "occurrence_count": None,
            },
        ),
    ],
)
def test_weekly_recurrence_preserves_only_stated_days_and_boundaries(
    text: str, recurrence: dict
) -> None:
    provider = FakeProvider(result_payload(recurrence=recurrence))

    result = post_interpretation(text, provider)

    assert result.reminder is not None
    assert result.reminder.recurrence is not None
    assert result.reminder.recurrence.weekdays == recurrence["weekdays"]
    assert result.reminder.recurrence.interval == recurrence["interval"]
    actual_end = result.reminder.recurrence.ends_on
    assert (actual_end.isoformat() if actual_end is not None else None) == recurrence["ends_on"]


def test_conditional_follow_up_is_kept_separate_from_primary_due_time() -> None:
    provider = FakeProvider(
        result_payload(
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
    )

    result = post_interpretation(
        "Remind me to take medicine every day at 8 AM. If I do not complete it, "
        "remind me again after 30 minutes.",
        provider,
    )

    assert result.reminder is not None
    assert result.reminder.due is not None
    assert result.reminder.due.local_time is not None
    assert len(result.reminder.follow_ups) == 1
    follow_up = result.reminder.follow_ups[0]
    assert follow_up.delay_minutes == 30
    assert follow_up.condition == "if_incomplete"


@pytest.mark.parametrize(
    ("instruction", "kind", "delay_minutes"),
    [
        ("Snooze the reminder for 10 minutes.", "snooze", 10),
        ("Reschedule the reminder in 2 hours.", "reschedule", 120),
    ],
)
def test_snooze_and_reschedule_are_returned_as_separate_follow_ups(
    instruction: str, kind: str, delay_minutes: int
) -> None:
    provider = FakeProvider(
        result_payload(
            follow_ups=[
                {
                    "kind": kind,
                    "delay_minutes": delay_minutes,
                    "condition": None,
                    "target": None,
                }
            ]
        )
    )

    result = post_interpretation(
        f"Remind me to take medicine tomorrow at 8 AM. {instruction}", provider
    )

    assert result.reminder is not None
    assert len(result.reminder.follow_ups) == 1
    follow_up = result.reminder.follow_ups[0]
    assert follow_up.kind == kind
    assert follow_up.delay_minutes == delay_minutes
    assert follow_up.condition is None


@pytest.mark.parametrize(
    ("text", "question"),
    [
        (
            "Remind me to take medicine every other weekday at 8 AM.",
            "Which weekdays should I use?",
        ),
        (
            "Remind me to take medicine every day and every Monday at 8 AM.",
            "Which recurrence should I use?",
        ),
    ],
)
def test_unsupported_or_contradictory_recurrence_returns_clarification(
    text: str, question: str
) -> None:
    provider = FakeProvider(
        {
            "schema_version": "1.0",
            "status": "needs_clarification",
            "reminder": {
                "title": "take medicine",
                "due": {
                    "local_date": None,
                    "local_time": "08:00",
                    "time_of_day": None,
                    "time_zone": "Asia/Kolkata",
                    "precision": "unresolved",
                },
                "recurrence": None,
                "follow_ups": [],
                "additional_instructions": [],
            },
            "clarification_questions": [question],
            "unresolved_fields": ["reminder.recurrence"],
            "issues": [],
        }
    )

    result = post_interpretation(text, provider)

    assert result.status == "needs_clarification"
    assert result.reminder is not None
    assert result.reminder.recurrence is None
    assert result.clarification_questions == [question]
    assert result.unresolved_fields == ["reminder.recurrence"]


def test_incomplete_follow_up_returns_clarification_instead_of_guessing_delay() -> None:
    provider = FakeProvider(
        {
            "schema_version": "1.0",
            "status": "needs_clarification",
            "reminder": {
                "title": "take medicine",
                "due": {
                    "local_date": "2026-11-04",
                    "local_time": "08:00",
                    "time_of_day": None,
                    "time_zone": "Asia/Kolkata",
                    "precision": "exact",
                },
                "recurrence": None,
                "follow_ups": [],
                "additional_instructions": [],
            },
            "clarification_questions": ["After how long should I remind you again?"],
            "unresolved_fields": ["reminder.follow_ups"],
            "issues": [],
        }
    )

    result = post_interpretation(
        "Remind me to take medicine tomorrow at 8 AM. If I do not complete it, "
        "remind me again.",
        provider,
    )

    assert result.status == "needs_clarification"
    assert result.reminder is not None
    assert result.reminder.follow_ups == []
    assert result.unresolved_fields == ["reminder.follow_ups"]
    assert "After how long" in result.clarification_questions[0]