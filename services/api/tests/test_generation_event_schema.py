from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker


def _schema() -> dict[str, object]:
    path = Path(__file__).parents[3] / "contracts/events/generation-events.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_generation_event_schema_accepts_structured_events() -> None:
    schema = _schema()
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())

    validator.validate(
        {
            "schemaVersion": "1.0",
            "eventId": "evt_0001",
            "eventType": "task.accepted",
            "occurredAt": "2026-08-08T07:00:00Z",
            "generationId": "gen_test",
            "sequence": 1,
            "payload": {"generationId": "gen_test", "reservedEnergy": 1200},
        }
    )
    validator.validate(
        {
            "schemaVersion": "1.0",
            "eventId": "evt_0002",
            "eventType": "candidate.completed",
            "occurredAt": "2026-08-08T07:00:01Z",
            "generationId": "gen_test",
            "sequence": 2,
            "payload": {
                "candidate": {
                    "candidateId": "can_test",
                    "strategy": "SAFE",
                    "styleId": "warm",
                    "text": "Test candidate",
                    "safetyStatus": "PASSED",
                }
            },
        }
    )


def test_generation_event_schema_rejects_internal_fields() -> None:
    validator = Draft202012Validator(_schema(), format_checker=FormatChecker())

    errors = list(
        validator.iter_errors(
            {
                "schemaVersion": "1.0",
                "eventId": "evt_bad",
                "eventType": "task.stage",
                "occurredAt": "2026-08-08T07:00:00Z",
                "generationId": "gen_test",
                "sequence": 3,
                "payload": {"stage": "ANALYZING"},
                "chainOfThought": "must never be emitted",
            }
        )
    )

    assert errors
