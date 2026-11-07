import json
from pathlib import Path
from typing import Any

import yaml
from app.schemas.requests import InterpretationRequest, ReferenceContext
from app.schemas.responses import (
    DueTime,
    ErrorResponse,
    FollowUpInstruction,
    InterpretationIssue,
    InterpretationResult,
    Recurrence,
    ReminderDraft,
)
from pydantic import BaseModel

CONTRACT_PATH = (
    Path(__file__).parents[2]
    / "specs"
    / "001-natural-language-reminder-agent"
    / "contracts"
    / "openapi.yaml"
)
CONTRACT: dict[str, Any] = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
COMPONENTS: dict[str, Any] = CONTRACT["components"]["schemas"]
MODEL_SCHEMAS: dict[str, type[BaseModel]] = {
    "InterpretationRequest": InterpretationRequest,
    "ReferenceContext": ReferenceContext,
    "InterpretationResult": InterpretationResult,
    "ReminderDraft": ReminderDraft,
    "DueTime": DueTime,
    "Recurrence": Recurrence,
    "FollowUpInstruction": FollowUpInstruction,
    "InterpretationIssue": InterpretationIssue,
    "ErrorResponse": ErrorResponse,
}


def enum_values(schema: dict[str, Any]) -> set[Any]:
    values = set(schema.get("enum", []))
    for union_key in ("oneOf", "anyOf", "allOf"):
        for branch in schema.get(union_key, []):
            values.update(enum_values(branch))
    return values


def test_openapi_component_fields_and_requiredness_match_pydantic_models() -> None:
    for schema_name, model in MODEL_SCHEMAS.items():
        contract_schema = COMPONENTS[schema_name]
        assert set(contract_schema["properties"]) == set(model.model_fields)
        assert set(contract_schema.get("required", [])) == {
            name for name, field in model.model_fields.items() if field.is_required()
        }
        assert contract_schema["additionalProperties"] is False


def test_openapi_status_enums_and_error_responses_match_models() -> None:
    assert enum_values(COMPONENTS["InterpretationResult"]["properties"]["status"]) == {
        "ready",
        "needs_clarification",
        "invalid",
        "unsupported",
    }
    assert CONTRACT["paths"]["/api/v1/reminders/interpret"].keys() == {"post"}
    for status_code in ("422", "502", "503", "504"):
        response_schema = CONTRACT["paths"]["/api/v1/reminders/interpret"]["post"][
            "responses"
        ][status_code]["content"]["application/json"]["schema"]
        assert response_schema["$ref"] == "#/components/schemas/ErrorResponse"


def test_openapi_request_constraints_match_request_model() -> None:
    request_schema = COMPONENTS["InterpretationRequest"]
    text_schema = request_schema["properties"]["text"]

    assert text_schema["minLength"] == 1
    assert text_schema["maxLength"] == InterpretationRequest.model_json_schema()["properties"][
        "text"
    ]["maxLength"]
    assert "reference_context" in request_schema["required"]
    assert "oneOf" in request_schema["properties"]["reference_context"]


def test_openapi_examples_validate_against_pydantic_models() -> None:
    operation = CONTRACT["paths"]["/api/v1/reminders/interpret"]["post"]
    request_example = operation["requestBody"]["content"]["application/json"]["examples"][
        "relativeReminder"
    ]["value"]
    InterpretationRequest.model_validate_json(json.dumps(request_example))

    response_examples = operation["responses"]["200"]["content"]["application/json"][
        "examples"
    ]
    for example in response_examples.values():
        InterpretationResult.model_validate_json(json.dumps(example["value"]))


def test_openapi_error_schema_accepts_documented_envelope() -> None:
    ErrorResponse.model_validate_json(
        '{"error":{"code":"provider_unavailable","message":"Provider unavailable."}}'
    )