import json

from app.prompts.reminder_interpretation import build_interpretation_prompt
from app.schemas.requests import InterpretationRequest


def make_request(text: str, reference_context: dict | None) -> InterpretationRequest:
    return InterpretationRequest.model_validate_json(
        json.dumps({"text": text, "reference_context": reference_context})
    )


def test_prompt_serialization_is_deterministic_and_preserves_explicit_context() -> None:
    request = make_request(
        "Remind me to call Rahul tomorrow at 10 AM.",
        {
            "reference_instant": "2026-11-03T09:00:00+05:30",
            "time_zone": "Asia/Kolkata",
        },
    )

    first = build_interpretation_prompt(request)
    second = build_interpretation_prompt(request)

    assert first == second
    assert json.dumps(
        {
            "reference_context": {
                "reference_instant": "2026-11-03T09:00:00+05:30",
                "time_zone": "Asia/Kolkata",
            },
            "text": "Remind me to call Rahul tomorrow at 10 AM.",
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ) in first
    assert "Never use the host clock" in first
    assert "Never infer a time zone" in first


def test_prompt_serialization_does_not_invent_missing_reference_context() -> None:
    request = make_request("Remind me to call Rahul tomorrow.", None)

    prompt = build_interpretation_prompt(request)

    assert '"reference_context":null' in prompt
    assert "2026-11-07" not in prompt
    assert "UTC" not in prompt


def test_prompt_serialization_escapes_user_text_as_json() -> None:
    request = make_request('Remind me to say "hello" \\ tomorrow.', None)

    prompt = build_interpretation_prompt(request)

    assert json.dumps(request.text, ensure_ascii=False) in prompt