import json
from datetime import date, datetime

import pytest
from app.api.errors import ProviderOutputError
from app.main import create_app
from app.prompts.reminder_interpretation import build_interpretation_prompt
from app.schemas.requests import InterpretationRequest
from app.schemas.responses import InterpretationResult
from app.services.invariants import validate_interpretation_result
from fastapi.testclient import TestClient
from pydantic import ValidationError


class FakeProvider:
    def __init__(self, response: dict) -> None:
        self.response = response

    async def generate(self, prompt: str) -> str:
        return json.dumps(self.response)


def ready_result(
    *,
    local_date: str,
    local_time: str,
    time_zone: str,
) -> dict:
    return {
        "schema_version": "1.0",
        "status": "ready",
        "reminder": {
            "title": "review the report",
            "due": {
                "local_date": local_date,
                "local_time": local_time,
                "time_of_day": None,
                "time_zone": time_zone,
                "precision": "exact",
            },
            "recurrence": None,
            "follow_ups": [],
            "additional_instructions": [],
        },
        "clarification_questions": [],
        "unresolved_fields": [],
        "issues": [],
    }


def request_with_context(text: str, context: dict) -> InterpretationRequest:
    return InterpretationRequest.model_validate(
        {"text": text, "reference_context": context}
    )


@pytest.mark.parametrize(
    ("reference_instant", "expected_date"),
    [
        ("2026-01-31T09:00:00+05:30", "2026-02-01"),
        ("2026-12-31T09:00:00+05:30", "2027-01-01"),
        ("2028-02-28T09:00:00+05:30", "2028-02-29"),
        ("2027-02-28T09:00:00+05:30", "2027-03-01"),
    ],
    ids=["month-boundary", "year-boundary", "leap-year", "non-leap-year"],
)
def test_tomorrow_preserves_calendar_boundaries(
    reference_instant: str,
    expected_date: str,
) -> None:
    context = {
        "reference_instant": reference_instant,
        "time_zone": "Asia/Kolkata",
    }
    provider = FakeProvider(
        ready_result(local_date=expected_date, local_time="09:00", time_zone="Asia/Kolkata")
    )
    app = create_app(provider=provider)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/reminders/interpret",
            json={
                "text": "Remind me to review the report tomorrow at 9 AM.",
                "reference_context": context,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["reminder"]["due"]["local_date"] == expected_date
    assert body["reminder"]["due"]["local_time"] == "09:00:00"
    assert body["reminder"]["due"]["time_zone"] == "Asia/Kolkata"


@pytest.mark.parametrize(
    ("reference_instant", "expected_date", "expected_time"),
    [
        ("2026-03-07T12:00:00-05:00", "2026-03-08", "09:00"),
        ("2026-11-01T12:00:00-04:00", "2026-11-02", "09:00"),
    ],
    ids=["spring-forward", "fall-back"],
)
def test_dst_transition_uses_explicit_timezone_context(
    reference_instant: str,
    expected_date: str,
    expected_time: str,
) -> None:
    context = {
        "reference_instant": reference_instant,
        "time_zone": "America/New_York",
    }
    provider = FakeProvider(
        ready_result(
            local_date=expected_date,
            local_time=expected_time,
            time_zone="America/New_York",
        )
    )
    app = create_app(provider=provider)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/reminders/interpret",
            json={
                "text": "Remind me to review the report tomorrow at 9 AM.",
                "reference_context": context,
            },
        )

    assert response.status_code == 200
    due = response.json()["reminder"]["due"]
    assert due["local_date"] == expected_date
    assert due["local_time"] == "09:00:00"
    assert due["time_zone"] == "America/New_York"


def test_evaluation_policy_treats_next_monday_as_strictly_future_monday() -> None:
    """Use the evaluation policy; the specification does not define this convention."""
    context = {
        "reference_instant": "2026-11-03T09:00:00+05:30",
        "time_zone": "Asia/Kolkata",
    }
    provider = FakeProvider(
        {
            **ready_result(
                local_date="2026-11-09",
                local_time="10:00",
                time_zone="Asia/Kolkata",
            ),
            "reminder": {
                **ready_result(
                    local_date="2026-11-09",
                    local_time="10:00",
                    time_zone="Asia/Kolkata",
                )["reminder"],
                "due": {
                    "local_date": "2026-11-09",
                    "local_time": None,
                    "time_of_day": "morning",
                    "time_zone": "Asia/Kolkata",
                    "precision": "broad",
                },
            },
        }
    )
    app = create_app(provider=provider)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/reminders/interpret",
            json={
                "text": "Remind me to review the report next Monday morning.",
                "reference_context": context,
            },
        )

    assert response.status_code == 200
    due = response.json()["reminder"]["due"]
    assert due["local_date"] == "2026-11-09"
    assert due["local_time"] is None
    assert due["time_of_day"] == "morning"
    assert due["precision"] == "broad"


def test_reference_context_is_serialized_without_host_clock_or_timezone_inference() -> None:
    request = request_with_context(
        "Remind me tomorrow at 9 AM.",
        {
            "reference_instant": "2026-11-03T09:00:00+05:30",
            "time_zone": "Asia/Kolkata",
        },
    )

    prompt = build_interpretation_prompt(request)

    assert '"reference_instant":"2026-11-03T09:00:00+05:30"' in prompt
    assert '"time_zone":"Asia/Kolkata"' in prompt
    assert "current date" in prompt
    assert "host clock" in prompt


@pytest.mark.parametrize(
    "reference_instant",
    ["2026-11-03T09:00:00", "2026-11-03T09:00:00.000"],
)
def test_naive_reference_datetimes_are_rejected(reference_instant: str) -> None:
    with pytest.raises(ValidationError):
        InterpretationRequest.model_validate(
            {
                "text": "Remind me tomorrow at 9 AM.",
                "reference_context": {
                    "reference_instant": reference_instant,
                    "time_zone": "Asia/Kolkata",
                },
            }
        )


def test_reference_context_datetime_is_timezone_aware_after_validation() -> None:
    request = request_with_context(
        "Remind me tomorrow at 9 AM.",
        {
            "reference_instant": "2026-11-03T09:00:00+05:30",
            "time_zone": "Asia/Kolkata",
        },
    )

    assert request.reference_context is not None
    assert request.reference_context.reference_instant.tzinfo is not None
    assert request.reference_context.reference_instant.utcoffset() is not None


def test_temporal_result_invariants_require_exact_or_explicitly_broad_precision() -> None:
    request = request_with_context(
        "Remind me tomorrow at 9 AM.",
        {
            "reference_instant": "2026-11-03T09:00:00+05:30",
            "time_zone": "Asia/Kolkata",
        },
    )
    result = InterpretationResult.model_validate(
        {
            **ready_result(
                local_date="2026-11-04",
                local_time="09:00",
                time_zone="Asia/Kolkata",
            ),
            "reminder": {
                **ready_result(
                    local_date="2026-11-04",
                    local_time="09:00",
                    time_zone="Asia/Kolkata",
                )["reminder"],
                "due": {
                    "local_date": date(2026, 11, 4),
                    "local_time": None,
                    "time_of_day": None,
                    "time_zone": "Asia/Kolkata",
                    "precision": "exact",
                },
            },
        }
    )

    with pytest.raises(ProviderOutputError):
        validate_interpretation_result(request, result)


def test_temporal_context_rejects_a_naive_python_datetime_before_model_validation() -> None:
    with pytest.raises(ValidationError):
        InterpretationRequest.model_validate(
            {
                "text": "Remind me tomorrow.",
                "reference_context": {
                    "reference_instant": datetime(2026, 11, 3, 9, 0),
                    "time_zone": "Asia/Kolkata",
                },
            }
        )
