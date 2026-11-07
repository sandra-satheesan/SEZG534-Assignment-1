import json

import pytest
from app.main import create_app
from fastapi.testclient import TestClient


class FakeProvider:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.prompts: list[str] = []

    async def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return json.dumps(self.response)


def ready_result(
    text: str,
    local_date: str,
    local_time: str | None,
    time_of_day: str | None,
    precision: str,
) -> dict:
    return {
        "schema_version": "1.0",
        "status": "ready",
        "reminder": {
            "title": text,
            "due": {
                "local_date": local_date,
                "local_time": local_time,
                "time_of_day": time_of_day,
                "time_zone": "Asia/Kolkata",
                "precision": precision,
            },
            "recurrence": None,
            "follow_ups": [],
            "additional_instructions": [],
        },
        "clarification_questions": [],
        "unresolved_fields": [],
        "issues": [],
    }


@pytest.mark.parametrize(
    ("text", "result", "expected_date", "expected_time", "expected_period", "precision"),
    [
        (
            "Remind me to call Rahul on November 4, 2026 at 10 AM.",
            ready_result("call Rahul", "2026-11-04", "10:00", None, "exact"),
            "2026-11-04",
            "10:00:00",
            None,
            "exact",
        ),
        (
            "Remind me to call Rahul tomorrow at 10 AM.",
            ready_result("call Rahul", "2026-11-04", "10:00", None, "exact"),
            "2026-11-04",
            "10:00:00",
            None,
            "exact",
        ),
        (
            "Remind me to submit my assignment next Monday evening.",
            ready_result("submit my assignment", "2026-11-09", None, "evening", "broad"),
            "2026-11-09",
            None,
            "evening",
            "broad",
        ),
    ],
)
def test_ready_interpretation_uses_fake_provider_and_preserves_time_precision(
    text: str,
    result: dict,
    expected_date: str,
    expected_time: str | None,
    expected_period: str | None,
    precision: str,
) -> None:
    provider = FakeProvider(result)
    app = create_app(provider=provider)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/reminders/interpret",
            json={
                "text": text,
                "reference_context": {
                    "reference_instant": "2026-11-03T09:00:00+05:30",
                    "time_zone": "Asia/Kolkata",
                },
            },
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    body = response.json()
    assert body["status"] == "ready"
    assert body["reminder"]["due"]["local_date"] == expected_date
    assert body["reminder"]["due"]["local_time"] == expected_time
    assert body["reminder"]["due"]["time_of_day"] == expected_period
    assert body["reminder"]["due"]["precision"] == precision
    assert len(provider.prompts) == 1
    assert text in provider.prompts[0]


def test_invalid_provider_output_is_rejected_without_echoing_raw_output() -> None:
    provider = FakeProvider({"raw": "private malformed output"})
    app = create_app(provider=provider)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/reminders/interpret",
            json={"text": "Remind me to call Rahul.", "reference_context": None},
        )

    assert response.status_code == 502
    assert response.json() == {
        "error": {
            "code": "provider_error",
            "message": "The model provider returned an invalid response.",
        }
    }
    assert "private malformed output" not in response.text