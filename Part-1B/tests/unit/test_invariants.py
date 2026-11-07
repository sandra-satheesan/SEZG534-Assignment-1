import json

import pytest
from app.api.errors import ProviderOutputError
from app.prompts.reminder_interpretation import build_interpretation_prompt
from app.schemas.requests import InterpretationRequest
from app.schemas.responses import InterpretationResult
from app.services.invariants import validate_interpretation_result


def make_request(text: str) -> InterpretationRequest:
    return InterpretationRequest.model_validate_json(
        json.dumps({"text": text, "reference_context": None})
    )


def make_failure_result(
    status: str, issues: list[dict] | None = None, reminder: dict | None = None
) -> InterpretationResult:
    return InterpretationResult.model_validate_json(
        json.dumps(
            {
                "schema_version": "1.0",
                "status": status,
                "reminder": reminder,
                "clarification_questions": [],
                "unresolved_fields": [],
                "issues": issues or [],
            }
        )
    )


@pytest.mark.parametrize("status", ["invalid", "unsupported"])
def test_invalid_and_unsupported_results_require_an_issue(status: str) -> None:
    with pytest.raises(ProviderOutputError):
        validate_interpretation_result(make_request("input"), make_failure_result(status))


@pytest.mark.parametrize(
    ("status", "code", "text"),
    [
        ("invalid", "invalid_date", "Remind me on February 30, 2027."),
        ("unsupported", "unsupported_request", "Write a poem about rain."),
    ],
)
def test_invalid_and_unsupported_results_with_issues_are_accepted(
    status: str, code: str, text: str
) -> None:
    result = make_failure_result(
        status,
        [{"code": code, "field": "text", "message": "The request cannot be interpreted."}],
    )

    assert validate_interpretation_result(make_request(text), result) == result


@pytest.mark.parametrize("status", ["invalid", "unsupported"])
def test_invalid_or_unsupported_result_with_issue_cannot_contain_reminder(
    status: str,
) -> None:
    result = make_failure_result(
        status,
        issues=[
            {
                "code": "invalid_date" if status == "invalid" else "unsupported_request",
                "field": "due.local_date",
                "message": "The request cannot be used as an actionable reminder.",
            }
        ],
        reminder={
            "title": "pay bill",
            "due": {
                "local_date": "2027-02-28",
                "local_time": "09:00",
                "time_of_day": None,
                "time_zone": None,
                "precision": "exact",
            },
            "recurrence": None,
            "follow_ups": [],
            "additional_instructions": [],
        },
    )

    with pytest.raises(ProviderOutputError):
        validate_interpretation_result(make_request("Pay bill February 30."), result)


def test_prompt_distinguishes_invalid_unsupported_and_multi_intent_requests() -> None:
    prompt = " ".join(
        build_interpretation_prompt(make_request("Pay bill February 30.")).split()
    )

    assert "For impossible dates or times" in prompt
    assert "return status invalid" in prompt
    assert "For non-reminder requests" in prompt
    assert "return status unsupported" in prompt
    assert "For multiple reminder intents" in prompt
    assert "ask the user to submit one reminder per request" in prompt
    assert "For contradictory or conflicting timing that needs user input" in prompt
    assert "return status needs_clarification" in prompt
    assert "Do not classify it as invalid merely because the instructions conflict" in prompt


def test_response_schema_rejects_impossible_clock_time_from_ready_result() -> None:
    payload = {
        "schema_version": "1.0",
        "status": "ready",
        "reminder": {
            "title": "call Rahul",
            "due": {
                "local_date": "2026-11-04",
                "local_time": "25:99",
                "time_of_day": None,
                "time_zone": "Asia/Kolkata",
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

    with pytest.raises(ValueError):
        InterpretationResult.model_validate_json(json.dumps(payload))