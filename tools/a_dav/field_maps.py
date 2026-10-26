"""Load patient-free cohort field maps against the local JSON Schema."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


FIELD_MAP_SCHEMA = Path(__file__).with_name("field_maps") / "field_map.schema.json"


class FieldMapError(ValueError):
    """Safe field map validation error."""


def load_field_map(path: Path) -> dict[str, Any]:
    try:
        schema = json.loads(FIELD_MAP_SCHEMA.read_bytes())
        document = json.loads(Path(path).read_bytes())
        Draft202012Validator.check_schema(schema)
        errors = list(Draft202012Validator(schema).iter_errors(document))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise FieldMapError("FIELD_MAP_INVALID") from None
    if errors or not isinstance(document, dict):
        raise FieldMapError("FIELD_MAP_INVALID")
    return document
