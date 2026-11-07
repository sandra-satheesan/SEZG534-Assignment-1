import json

import pytest
from app.main import create_app
from app.schemas.responses import InterpretationResult
from fastapi.testclient import TestClient


class FakeProvider:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.prompts: list[str] = []

    async def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return json.dumps(self.response)


def clarification_result(
    *, title: str | None, due: dict | None, question: str, unresolved_fields: list[str]
) -> dict:
    return {
        "schema_version": "1.0",
        "status": "needs_clarification",
        "reminder": None
        if title is None and due is None
        else {
            "title": title,
            "due": due,
            "recurrence": None,
            "follow_ups": [],
            "additional_instructions": [],
        },
        "clarification_questions": [question],
        "unresolved_fields": unresolved_fields,
        "issues": [],
    }


@pytest.mark.parametrize(
    ("text", "context", "result", "expected_unresolved", "question_fragment"),
    [
        (
            "Remind me.",
            None,
            clarification_result(
                title=None,
                due=None,
                question="What would you like to be reminded about?",
                unresolved_fields=["reminder.title"],
            ),
            ["reminder.title"],
            "reminded about",
        ),
        (
            "Remind me to call my manager.",
            None,
            clarification_result(
                title="call my manager",
                due=None,
                question="What date and time should I use?",
                unresolved_fields=["due.local_date", "due.local_time"],
            ),
            ["due.local_date", "due.local_time"],
            "date and time",
        ),
        (
            "Remind me to call Rahul on November 4, 2026.",
            {
                "reference_instant": "2026-11-03T09:00:00+05:30",
                "time_zone": "Asia/Kolkata",
            },
            clarification_result(
                title="call Rahul",
                due={
                    "local_date": "2026-11-04",
                    "local_time": None,
                    "time_of_day": None,
                    "time_zone": "Asia/Kolkata",
                    "precision": "unresolved",
                },
                question="What time should I use?",
                unresolved_fields=["due.local_time"],
            ),
            ["due.local_time"],
            "What time",
        ),
        (
            "Remind me to call Rahul tomorrow at 10 AM.",
            None,
            clarification_result(
                title="call Rahul",
                due={
                    "local_date": None,
                    "local_time": "10:00",
                    "time_of_day": None,
                    "time_zone": None,
                    "precision": "unresolved",
                },
                question="What reference date and time zone should I use?",
                unresolved_fields=["due.local_date", "due.time_zone"],
            ),
            ["due.local_date", "due.time_zone"],
            "reference date and time zone",
        ),
        (
            "Remind me to call Rahul next Monday.",
            {
                "reference_instant": "2026-11-03T09:00:00+05:30",
                "time_zone": "Asia/Kolkata",
            },
            clarification_result(
                title="call Rahul",
                due={
                    "local_date": None,
                    "local_time": None,
                    "time_of_day": None,
                    "time_zone": "Asia/Kolkata",
                    "precision": "unresolved",
                },
                question="Which Monday do you mean?",
                unresolved_fields=["due.local_date"],
            ),
            ["due.local_date"],
            "Which Monday",
        ),
    ],
)
def test_incomplete_or_ambiguous_request_returns_schema_valid_clarification(
    text: str,
    context: dict | None,
    result: dict,
    expected_unresolved: list[str],
    question_fragment: str,
) -> None:
    provider = FakeProvider(result)
    app = create_app(provider=provider)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/reminders/interpret",
            json={"text": text, "reference_context": context},
        )

    assert response.status_code == 200
    parsed = InterpretationResult.model_validate_json(response.text)
    assert parsed.status == "needs_clarification"
    assert parsed.clarification_questions
    assert question_fragment in parsed.clarification_questions[0]
    assert parsed.unresolved_fields == expected_unresolved
    assert len(provider.prompts) == 1
    assert text in provider.prompts[0]
    if context is not None:
        assert context["time_zone"] in provider.prompts[0]