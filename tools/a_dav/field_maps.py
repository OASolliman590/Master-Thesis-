"""Load patient-free cohort field maps against the local JSON Schema."""
from __future__ import annotations

import json
import argparse
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a cohort field map")
    parser.add_argument("command", choices=["validate"])
    parser.add_argument("file", type=Path)
    args = parser.parse_args()
    try:
        schema = json.loads(FIELD_MAP_SCHEMA.read_bytes())
        document = json.loads(args.file.read_bytes())
        Draft202012Validator.check_schema(schema)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"Cannot read JSON: {exc}")
        return 1
    errors = sorted(Draft202012Validator(schema).iter_errors(document),
                    key=lambda error: (tuple(str(part) for part in error.absolute_path), error.message))
    if errors:
        for error in errors:
            location = ".".join(str(part) for part in error.absolute_path) or "$"
            print(f"{location}: {error.message}")
        return 1
    print("valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
