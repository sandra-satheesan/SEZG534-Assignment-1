import json

import pytest
from app.api.errors import ProviderOutputError
from app.prompts.reminder_interpretation import build_interpretation_prompt
from app.schemas.requests import InterpretationRequest
from app.schemas.responses import InterpretationResult
from app.services.invariants import validate_interpretation_result


def make_request(text: str, context: dict | None = None) -> InterpretationRequest:
    return InterpretationRequest.model_validate_json(
        json.dumps({"text": text, "reference_context": context})
    )


def make_clarification(
    *,
    title: str | None,
    due: dict | None,
    questions: list[str],
    unresolved_fields: list[str],
) -> InterpretationResult:
    return InterpretationResult.model_validate_json(
        json.dumps(
            {
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
            "clarification_questions": questions,
            "unresolved_fields": unresolved_fields,
            "issues": [],
            }
        )
    )


def exact_due() -> dict:
    return {
        "local_date": "2026-11-04",
        "local_time": "10:00",
        "time_of_day": None,
        "time_zone": "Asia/Kolkata",
        "precision": "exact",
    }


def test_prompt_requests_clarification_for_missing_activity_or_timing() -> None:
    prompt = " ".join(build_interpretation_prompt(make_request("Remind me.")).split())

    assert "If the reminder action is missing" in prompt
    assert "ask what the user wants to be reminded about" in prompt
    assert "If the date or time is missing" in prompt
    assert "ask only for the missing fields" in prompt
    assert "leave their values unset" in prompt


def test_prompt_requests_reference_context_and_flags_ambiguous_time() -> None:
    prompt = " ".join(
        build_interpretation_prompt(make_request("Remind me to call Rahul next Monday.")).split()
    )

    assert "If relative timing has no reference context" in prompt
    assert "ask for the reference instant and time zone" in prompt
    assert "If a temporal phrase has materially different interpretations" in prompt
    assert "ask the user to choose" in prompt


def test_valid_title_clarification_has_unresolved_title_and_question() -> None:
    request = make_request("Remind me.")
    result = make_clarification(
        title=None,
        due=None,
        questions=["What would you like to be reminded about?"],
        unresolved_fields=["reminder.title"],
    )

    validate_interpretation_result(request, result)


def test_valid_missing_date_and_time_clarification_keeps_values_unset() -> None:
    request = make_request("Remind me to call my manager.")
    result = make_clarification(
        title="call my manager",
        due=None,
        questions=["What date and time should I use?"],
        unresolved_fields=["due.local_date", "due.local_time"],
    )

    validate_interpretation_result(request, result)


def test_valid_ambiguous_time_clarification_keeps_supplied_context() -> None:
    context = {
        "reference_instant": "2026-11-03T09:00:00+05:30",
        "time_zone": "Asia/Kolkata",
    }
    request = make_request("Remind me to call Rahul next Monday.", context)
    result = make_clarification(
        title="call Rahul",
        due={
            "local_date": None,
            "local_time": None,
            "time_of_day": None,
            "time_zone": "Asia/Kolkata",
            "precision": "unresolved",
        },
        questions=["Which Monday do you mean?"],
        unresolved_fields=["due.local_date"],
    )

    validate_interpretation_result(request, result)
    assert request.reference_context is not None
    assert result.reminder is not None
    assert result.reminder.due is not None
    assert result.reminder.due.time_zone == request.reference_context.time_zone


def test_clarification_cannot_drop_supplied_time_zone_when_due_is_present() -> None:
    request = make_request(
        "Remind me to call Rahul on November 4, 2026.",
        {
            "reference_instant": "2026-11-03T09:00:00+05:30",
            "time_zone": "Asia/Kolkata",
        },
    )
    result = make_clarification(
        title="call Rahul",
        due={
            "local_date": "2026-11-04",
            "local_time": None,
            "time_of_day": None,
            "time_zone": None,
            "precision": "unresolved",
        },
        questions=["What time should I use?"],
        unresolved_fields=["due.local_time"],
    )

    with pytest.raises(ProviderOutputError):
        validate_interpretation_result(request, result)


@pytest.mark.parametrize(
    "result",
    [
        (
            {
                "schema_version": "1.0",
                "status": "ready",
                "reminder": {
                    "title": "call my manager",
                    "due": None,
                    "recurrence": None,
                    "follow_ups": [],
                    "additional_instructions": [],
                },
                "clarification_questions": [],
                "unresolved_fields": ["due.local_date", "due.local_time"],
                "issues": [],
            }
        ),
        (
            {
                "schema_version": "1.0",
                "status": "needs_clarification",
                "reminder": {
                    "title": "call my manager",
                    "due": None,
                    "recurrence": None,
                    "follow_ups": [],
                    "additional_instructions": [],
                },
                "clarification_questions": [],
                "unresolved_fields": ["due.local_date"],
                "issues": [],
            }
        ),
        (
            {
                "schema_version": "1.0",
                "status": "needs_clarification",
                "reminder": {
                    "title": "call my manager",
                    "due": {
                        **exact_due(),
                        "local_date": "2026-11-04",
                    },
                    "recurrence": None,
                    "follow_ups": [],
                    "additional_instructions": [],
                },
                "clarification_questions": ["Which date do you mean?"],
                "unresolved_fields": ["due.local_date"],
                "issues": [],
            }
        ),
    ],
    ids=[
        "ready-has-unresolved-fields",
        "clarification-has-no-question",
        "unresolved-value-populated",
    ],
)
def test_inconsistent_ready_or_clarification_result_is_rejected(result: dict) -> None:
    request = make_request("Remind me to call my manager.")
    parsed = InterpretationResult.model_validate_json(json.dumps(result))

    with pytest.raises(ProviderOutputError):
        validate_interpretation_result(request, parsed)