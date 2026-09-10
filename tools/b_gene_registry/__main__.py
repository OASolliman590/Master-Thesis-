"""B-G1: outcome-blind gene-set registry validation and annotation-coverage audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import uuid
from datetime import date
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION_COMPLETE = "B-G1-complete-v1"
SCHEMA_VERSION_INCOMPLETE = "B-G1-incomplete-v1"
SCHEMA_VERSION_CHECKSUMS = "B-G1-checksums-v1"
SCHEMA_VERSION_REGISTRY_ROWS = "B-G1-registry-rows-v1"
SCHEMA_VERSION_COVERAGE = "B-G1-coverage-v1"
MANIFEST_SCHEMA_VERSION = "B-G1-annotation-manifest-v1"

EXIT_ARGUMENT = 2
EXIT_VALIDATION = 3
EXIT_IO = 4

PRIMARY_P = ["HLA-A", "HLA-B", "HLA-C", "B2M", "TAP1", "TAP2", "PSMB8", "PSMB9"]
REQUIRED_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"
REQUIRED_SCHEMA_ID = "https://local.invalid/specs/B/gene_set_registry.schema.json"
REQUIRED_SCHEMA_SEMANTIC_SHA256 = "26766be7fe932ca4e719278faae05d0a3db3b27de5390c7548fec8aeefc83dac"
REGISTRY_SCHEMA_VERSION_V02 = "B-gene-set-registry-proposed-v0.2"
RFC3339_FULL_DATE_RE = re.compile(r"^([0-9]{4})-([0-9]{2})-([0-9]{2})$")
REQUIRED_ALIASES = {
    "MB21D1": "CGAS",
    "TMEM173": "STING1",
    "TAPBPR": "TAPBPL",
}
REQUIRED_DO_NOT_COLLAPSE = ("TAPBP", "TAPBPL")
V02_PROGRAMS = (
    ("P_ANTIGEN_PRESENTATION", "primary"),
    ("AYERS_GEP_18", "planned_secondary"),
    ("HALLMARK_INTERFERON_GAMMA_RESPONSE", "planned_secondary"),
    ("HOPE_18", "planned_secondary"),
    ("M0_EXTRA_ANTIGEN_PRESENTATION", "exploratory"),
    ("M1_MOBILITY", "exploratory"),
    ("M2_CYTOTOXICITY", "exploratory"),
    ("M3_VIRAL_MIMICRY", "exploratory"),
    ("M4_EXCLUSION", "exploratory"),
    ("M5_CHECKPOINT_CANDIDATES", "exploratory_registry"),
    ("M6_EPIGENETIC_REGULATORS", "exploratory_context"),
)
ANNOTATION_HEADER = ["raw_id", "canonical_symbol", "entrez_id", "ensembl_id", "mapping_status"]
MAPPING_STATUSES = {"mapped", "ambiguous", "unmapped"}
MANIFEST_KEYS = (
    "schema_version",
    "source_id",
    "source_status",
    "canonicalization_authority",
    "identifier_namespace",
    "source_reference",
    "table_path",
    "table_sha256",
)
FORBIDDEN_COLUMN_TOKENS = frozenset({"patient", "value", "sample", "expression"})
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SOURCE_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
NUMERIC_STATUS_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")
GZIP_MAGIC = b"\x1f\x8b"
SCHEMA_META_KEYS = frozenset(
    {"$schema", "$id", "$defs", "$comment", "title", "description", "default"}
)
REGISTRY_ROWS_TSV_FIELDS = [
    "program_index",
    "program_id",
    "program_layer",
    "member_index",
    "raw_symbol",
    "canonical_symbol",
    "alias_applied",
    "overlap_with_primary_p",
    "membership_status",
    "direction_status",
    "weights_status",
    "scoring_status",
    "predictor_status",
]
COVERAGE_TSV_FIELDS = [
    "program_index",
    "program_id",
    "program_layer",
    "member_index",
    "raw_symbol",
    "canonical_symbol",
    "source_id",
    "present",
    "matching_row_count",
    "duplicate",
    "aggregate_mapping_status",
    "raw_ids",
    "entrez_ids",
    "ensembl_ids",
]
STATUS_FIELDS = (
    "direction_status",
    "weights_status",
    "scoring_status",
    "predictor_status",
)


class Failure(Exception):
    """Boundary-raised failure with an explicit process exit code."""

    def __init__(self, message: str, code: int = EXIT_VALIDATION):
        super().__init__(message)
        self.code = code


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _type_allows(value: Any, type_spec: Any) -> bool:
    kinds = type_spec if isinstance(type_spec, list) else [type_spec]
    actual = _json_type(value)
    for kind in kinds:
        if kind == "number" and actual in {"number", "integer"}:
            return True
        if kind == actual:
            return True
        if kind == "integer" and actual == "integer":
            return True
    return False


def _canon_dump(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _dedupe_object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise Failure(f"schema reason=duplicate-json-key {key}", EXIT_VALIDATION)
        out[key] = value
    return out


def _resolve_ref(ref: str, defs: dict[str, Any]) -> dict[str, Any]:
    prefix = "#/$defs/"
    if not ref.startswith(prefix):
        raise Failure(f"schema reason=unsupported-ref {ref}", EXIT_VALIDATION)
    name = ref[len(prefix) :]
    if name not in defs:
        raise Failure(f"schema reason=unresolved-ref {ref}", EXIT_VALIDATION)
    target = defs[name]
    if not isinstance(target, dict):
        raise Failure(f"schema reason=invalid-ref-target {ref}", EXIT_VALIDATION)
    return target


def _schema_valid(instance: Any, schema: dict[str, Any], defs: dict[str, Any], path: str) -> bool:
    try:
        _validate_schema(instance, schema, defs, path)
        return True
    except Failure:
        return False


def _validate_schema(instance: Any, schema: dict[str, Any], defs: dict[str, Any], path: str) -> None:
    if not isinstance(schema, dict):
        raise Failure(f"{path} schema reason=invalid-schema-node", EXIT_VALIDATION)

    if "$ref" in schema:
        _validate_schema(instance, _resolve_ref(schema["$ref"], defs), defs, path)

    if "allOf" in schema:
        if not isinstance(schema["allOf"], list):
            raise Failure(f"{path} schema reason=invalid-allOf", EXIT_VALIDATION)
        for index, sub in enumerate(schema["allOf"]):
            if not isinstance(sub, dict):
                raise Failure(f"{path} schema reason=invalid-allOf-item {index}", EXIT_VALIDATION)
            _validate_schema(instance, sub, defs, path)

    if "oneOf" in schema:
        if not isinstance(schema["oneOf"], list):
            raise Failure(f"{path} schema reason=invalid-oneOf", EXIT_VALIDATION)
        matched = 0
        type_compatible_errors: list[Failure] = []
        for sub in schema["oneOf"]:
            if not isinstance(sub, dict):
                continue
            try:
                _validate_schema(instance, sub, defs, path)
            except Failure as exc:
                if "type" not in sub or _type_allows(instance, sub["type"]):
                    type_compatible_errors.append(exc)
            else:
                matched += 1
        if matched != 1:
            if matched == 0 and len(type_compatible_errors) == 1:
                raise type_compatible_errors[0]
            raise Failure(f"{path} schema reason=oneOf-mismatch matched={matched}", EXIT_VALIDATION)

    if "if" in schema:
        if_schema = schema["if"]
        if not isinstance(if_schema, dict):
            raise Failure(f"{path} schema reason=invalid-if", EXIT_VALIDATION)
        if _schema_valid(instance, if_schema, defs, path):
            then_schema = schema.get("then")
            if then_schema is not None:
                if not isinstance(then_schema, dict):
                    raise Failure(f"{path} schema reason=invalid-then", EXIT_VALIDATION)
                _validate_schema(instance, then_schema, defs, path)
        else:
            else_schema = schema.get("else")
            if else_schema is not None:
                if not isinstance(else_schema, dict):
                    raise Failure(f"{path} schema reason=invalid-else", EXIT_VALIDATION)
                _validate_schema(instance, else_schema, defs, path)

    if "type" in schema and not _type_allows(instance, schema["type"]):
        raise Failure(
            f"{path} schema reason=type-mismatch expected={schema['type']} actual={_json_type(instance)}",
            EXIT_VALIDATION,
        )

    if "const" in schema:
        const = schema["const"]
        if isinstance(const, bool) or isinstance(instance, bool):
            ok = instance is const
        else:
            ok = instance == const
        if not ok:
            raise Failure(f"{path} schema reason=const-mismatch", EXIT_VALIDATION)

    if "enum" in schema:
        if not isinstance(schema["enum"], list):
            raise Failure(f"{path} schema reason=invalid-enum", EXIT_VALIDATION)
        if not any(_canon_dump(instance) == _canon_dump(option) for option in schema["enum"]):
            raise Failure(f"{path} schema reason=enum-mismatch", EXIT_VALIDATION)

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < int(schema["minLength"]):
            raise Failure(f"{path} schema reason=minLength", EXIT_VALIDATION)
        if "pattern" in schema:
            try:
                pattern = re.compile(schema["pattern"])
            except re.error as exc:
                raise Failure(f"{path} schema reason=invalid-pattern", EXIT_VALIDATION) from exc
            if pattern.search(instance) is None:
                raise Failure(f"{path} schema reason=pattern-mismatch", EXIT_VALIDATION)
        if schema.get("format") == "date" and not _is_rfc3339_full_date(instance):
            raise Failure(f"{path} schema reason=format-date", EXIT_VALIDATION)

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < int(schema["minItems"]):
            raise Failure(f"{path} schema reason=minItems", EXIT_VALIDATION)
        if "maxItems" in schema and len(instance) > int(schema["maxItems"]):
            raise Failure(f"{path} schema reason=maxItems", EXIT_VALIDATION)
        if schema.get("uniqueItems") is True:
            seen: set[str] = set()
            for index, item in enumerate(instance):
                key = _canon_dump(item)
                if key in seen:
                    if path.endswith("raw_gene_symbols"):
                        label = item if isinstance(item, str) else key
                        raise Failure(
                            f"{path}[{index}] reason=duplicate-raw-member {label}",
                            EXIT_VALIDATION,
                        )
                    raise Failure(f"{path}[{index}] schema reason=uniqueItems", EXIT_VALIDATION)
                seen.add(key)
        prefix = schema.get("prefixItems")
        item_schema = schema.get("items", True)
        if prefix is not None:
            if not isinstance(prefix, list):
                raise Failure(f"{path} schema reason=invalid-prefixItems", EXIT_VALIDATION)
            for index, prefix_schema in enumerate(prefix):
                if index >= len(instance):
                    break
                if not isinstance(prefix_schema, dict):
                    raise Failure(f"{path}[{index}] schema reason=invalid-prefixItems-item", EXIT_VALIDATION)
                _validate_schema(instance[index], prefix_schema, defs, f"{path}[{index}]")
            extra_start = len(prefix)
        else:
            extra_start = 0
        if item_schema is False:
            if len(instance) > extra_start:
                raise Failure(f"{path}[{extra_start}] schema reason=additional-items-forbidden", EXIT_VALIDATION)
        elif isinstance(item_schema, dict):
            start = extra_start if prefix is not None else 0
            for index in range(start, len(instance)):
                _validate_schema(instance[index], item_schema, defs, f"{path}[{index}]")

    if isinstance(instance, dict):
        required = schema.get("required", [])
        if not isinstance(required, list):
            raise Failure(f"{path} schema reason=invalid-required", EXIT_VALIDATION)
        for key in required:
            if key not in instance:
                raise Failure(f"{path}.{key} schema reason=missing-required", EXIT_VALIDATION)
        properties = schema.get("properties", {})
        if properties and not isinstance(properties, dict):
            raise Failure(f"{path} schema reason=invalid-properties", EXIT_VALIDATION)
        additional = schema.get("additionalProperties", True)
        for key, value in instance.items():
            if key in properties:
                _validate_schema(value, properties[key], defs, f"{path}.{key}")
            elif additional is False:
                raise Failure(f"{path}.{key} schema reason=unknown-field", EXIT_VALIDATION)
            elif isinstance(additional, dict):
                _validate_schema(value, additional, defs, f"{path}.{key}")

    extra_keywords = set(schema) - SCHEMA_META_KEYS - {
        "$ref",
        "allOf",
        "oneOf",
        "if",
        "then",
        "else",
        "type",
        "const",
        "enum",
        "minLength",
        "pattern",
        "format",
        "minItems",
        "maxItems",
        "uniqueItems",
        "prefixItems",
        "items",
        "required",
        "properties",
        "additionalProperties",
    }
    if extra_keywords:
        # Fixed repository schema; ignore only documented meta keys. Unknown
        # constraint keywords are a contract error rather than a silent skip.
        raise Failure(
            f"{path} schema reason=unsupported-schema-keyword {sorted(extra_keywords)[0]}",
            EXIT_VALIDATION,
        )


def _is_rfc3339_full_date(value: str) -> bool:
    match = RFC3339_FULL_DATE_RE.fullmatch(value)
    if match is None:
        return False
    year, month, day = (int(part) for part in match.groups())
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True


def _assert_closed_object_schemas(node: Any, path: str) -> None:
    if not isinstance(node, dict):
        return
    if node.get("type") == "object" and node.get("additionalProperties") is not False:
        raise Failure(
            f"{path} schema reason=object-must-reject-unknown-fields",
            EXIT_VALIDATION,
        )
    for key in ("properties", "$defs"):
        child = node.get(key)
        if isinstance(child, dict):
            for name, sub in child.items():
                _assert_closed_object_schemas(sub, f"{path}.{key}.{name}")
    for key in ("items", "if", "then", "else"):
        child = node.get(key)
        if isinstance(child, dict):
            _assert_closed_object_schemas(child, f"{path}.{key}")
    for key in ("allOf", "oneOf", "prefixItems"):
        child = node.get(key)
        if isinstance(child, list):
            for index, sub in enumerate(child):
                _assert_closed_object_schemas(sub, f"{path}.{key}[{index}]")


def assert_schema_identity(schema: dict[str, Any]) -> None:
    if not isinstance(schema, dict):
        raise Failure("schema reason=schema-not-object", EXIT_VALIDATION)
    dialect = schema.get("$schema")
    schema_id = schema.get("$id")
    if dialect != REQUIRED_SCHEMA_DIALECT:
        raise Failure(
            "schema reason=draft-2020-12-declaration-required "
            f"expected={REQUIRED_SCHEMA_DIALECT} actual={dialect!r}",
            EXIT_VALIDATION,
        )
    if schema_id != REQUIRED_SCHEMA_ID:
        raise Failure(
            "schema reason=schema-id-mismatch "
            f"expected={REQUIRED_SCHEMA_ID} actual={schema_id!r}",
            EXIT_VALIDATION,
        )
    if schema.get("type") != "object":
        raise Failure("schema reason=root-type-object-required", EXIT_VALIDATION)
    _assert_closed_object_schemas(schema, "$")
    semantic_sha256 = _sha256(_canon_dump(schema).encode("utf-8"))
    if semantic_sha256 != REQUIRED_SCHEMA_SEMANTIC_SHA256:
        raise Failure(
            "schema reason=schema-contract-mismatch "
            f"expected={REQUIRED_SCHEMA_SEMANTIC_SHA256} actual={semantic_sha256}",
            EXIT_VALIDATION,
        )


def validate_against_schema(instance: Any, schema: dict[str, Any]) -> None:
    if not isinstance(schema, dict):
        raise Failure("schema reason=schema-not-object", EXIT_VALIDATION)
    defs = schema.get("$defs", {})
    if defs is None:
        defs = {}
    if not isinstance(defs, dict):
        raise Failure("schema reason=invalid-$defs", EXIT_VALIDATION)
    _validate_schema(instance, schema, defs, "$")


def membership_payload_bytes(symbols: list[str]) -> bytes:
    return json.dumps(symbols, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def membership_sha256(symbols: list[str]) -> str:
    return _sha256(membership_payload_bytes(symbols))


def load_json_object(path: Path, *, missing_code: int, invalid_code: int) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        raise Failure(f"path error reason=missing-file {path}", missing_code) from exc
    except OSError as exc:
        raise Failure(f"I/O failure reading {path}", EXIT_IO) from exc
    if b"\x00" in raw:
        raise Failure(f"{path} schema reason=nul-byte", invalid_code)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Failure(f"{path} schema reason=malformed-utf8", invalid_code) from exc
    try:
        payload = json.loads(text, object_pairs_hook=_dedupe_object_pairs)
    except json.JSONDecodeError as exc:
        raise Failure(f"{path} schema reason=invalid-json", invalid_code) from exc
    if not isinstance(payload, dict):
        raise Failure(f"{path} schema reason=json-not-object", invalid_code)
    return payload, raw


def _alias_map(canonicalization: dict[str, Any]) -> dict[str, str]:
    rules = canonicalization["alias_rules"]
    mapping: dict[str, str] = {}
    for index, rule in enumerate(rules):
        raw_symbol = rule["raw_symbol"]
        canonical_symbol = rule["canonical_symbol"]
        if raw_symbol in mapping:
            raise Failure(
                f"canonicalization.alias_rules[{index}] reason=duplicate-raw-alias {raw_symbol}",
                EXIT_VALIDATION,
            )
        mapping[raw_symbol] = canonical_symbol
    return mapping


def apply_alias(raw_symbol: str, alias_map: dict[str, str]) -> str:
    return alias_map.get(raw_symbol, raw_symbol)


def _validate_required_aliases(alias_map: dict[str, str], pairs: list[list[str]]) -> None:
    for raw_symbol, canonical_symbol in REQUIRED_ALIASES.items():
        if raw_symbol not in alias_map:
            raise Failure(
                f"canonicalization.alias_rules reason=missing-required-alias {raw_symbol}",
                EXIT_VALIDATION,
            )
        actual = alias_map[raw_symbol]
        if actual != canonical_symbol:
            raise Failure(
                f"canonicalization.alias_rules reason=required-alias-mismatch "
                f"{raw_symbol} expected={canonical_symbol} actual={actual}",
                EXIT_VALIDATION,
            )
    for raw_symbol in REQUIRED_DO_NOT_COLLAPSE:
        mapped = alias_map.get(raw_symbol, raw_symbol)
        if mapped != raw_symbol:
            raise Failure(
                f"canonicalization.alias_rules reason=collapsed-distinct-loci {raw_symbol}->{mapped}",
                EXIT_VALIDATION,
            )
    declared = [tuple(pair) for pair in pairs if isinstance(pair, list) and len(pair) == 2]
    if REQUIRED_DO_NOT_COLLAPSE not in declared:
        raise Failure(
            "canonicalization.do_not_collapse reason=missing-required-pair TAPBP TAPBPL",
            EXIT_VALIDATION,
        )


def _validate_do_not_collapse(pairs: list[list[str]], alias_map: dict[str, str]) -> None:
    for index, pair in enumerate(pairs):
        left, right = pair[0], pair[1]
        if left == right:
            raise Failure(
                f"canonicalization.do_not_collapse[{index}] reason=identical-pair",
                EXIT_VALIDATION,
            )
        left_c = apply_alias(left, alias_map)
        right_c = apply_alias(right, alias_map)
        if left_c == right_c or left_c == right or right_c == left:
            raise Failure(
                f"canonicalization.do_not_collapse[{index}] reason=collapsed-distinct-loci {left} {right}",
                EXIT_VALIDATION,
            )


def _reject_numeric_status(program: dict[str, Any], path: str) -> None:
    for field in STATUS_FIELDS:
        value = program[field]
        if not isinstance(value, str):
            raise Failure(f"{path}.{field} reason=non-string-status", EXIT_VALIDATION)
        if NUMERIC_STATUS_RE.fullmatch(value.strip()):
            raise Failure(f"{path}.{field} reason=numeric-status-forbidden", EXIT_VALIDATION)


def _reject_duplicate_raw_members(registry: dict[str, Any]) -> None:
    programs = registry.get("programs")
    if not isinstance(programs, list):
        return
    for index, program in enumerate(programs):
        if not isinstance(program, dict):
            continue
        symbols = program.get("raw_gene_symbols")
        if not isinstance(symbols, list):
            continue
        seen: set[str] = set()
        for member_index, symbol in enumerate(symbols):
            if not isinstance(symbol, str):
                continue
            if symbol in seen:
                raise Failure(
                    f"programs[{index}].raw_gene_symbols[{member_index}] reason=duplicate-raw-member {symbol}",
                    EXIT_VALIDATION,
                )
            seen.add(symbol)


def _validate_registry_contract(registry: dict[str, Any]) -> tuple[dict[str, str], list[str], dict[str, Any]]:
    if registry.get("primary_unchanged") is not True:
        raise Failure("registry reason=primary-unchanged-required", EXIT_VALIDATION)
    if registry.get("primary_membership_frozen") is not False:
        raise Failure("registry reason=primary-must-remain-unfrozen", EXIT_VALIDATION)

    programs = registry["programs"]
    ids: list[str] = []
    seen_ids: set[str] = set()
    primary_programs: list[tuple[int, dict[str, Any]]] = []
    layers: set[str] = set()
    for index, program in enumerate(programs):
        program_id = program["id"]
        if program_id in seen_ids:
            raise Failure(f"programs[{index}].id reason=duplicate-program-id {program_id}", EXIT_VALIDATION)
        seen_ids.add(program_id)
        ids.append(program_id)
        layers.add(program["layer"])
        _reject_numeric_status(program, f"programs[{index}]")
        symbols = program["raw_gene_symbols"]
        digest = program["membership_sha256"]
        status = program["membership_status"]
        if symbols is None:
            if digest is not None:
                raise Failure(
                    f"programs[{index}] reason=null-membership-requires-null-hash",
                    EXIT_VALIDATION,
                )
            if status != "unresolved":
                raise Failure(
                    f"programs[{index}] reason=null-membership-requires-unresolved",
                    EXIT_VALIDATION,
                )
        else:
            if not isinstance(symbols, list):
                raise Failure(f"programs[{index}].raw_gene_symbols reason=type-mismatch", EXIT_VALIDATION)
            raw_seen: set[str] = set()
            for member_index, symbol in enumerate(symbols):
                if symbol in raw_seen:
                    raise Failure(
                        f"programs[{index}].raw_gene_symbols[{member_index}] reason=duplicate-raw-member {symbol}",
                        EXIT_VALIDATION,
                    )
                raw_seen.add(symbol)
            if digest is None:
                raise Failure(
                    f"programs[{index}] reason=non-null-membership-requires-hash",
                    EXIT_VALIDATION,
                )
            if status == "unresolved":
                raise Failure(
                    f"programs[{index}] reason=unresolved-forbids-symbol-list",
                    EXIT_VALIDATION,
                )
            actual = membership_sha256(symbols)
            if digest != actual:
                raise Failure(
                    f"programs[{index}] reason=membership-hash-mismatch expected={actual}",
                    EXIT_VALIDATION,
                )
        if program["layer"] == "primary":
            primary_programs.append((index, program))

    if len(primary_programs) != 1:
        raise Failure(
            f"programs reason=unique-primary-required count={len(primary_programs)}",
            EXIT_VALIDATION,
        )
    _, primary = primary_programs[0]
    if primary.get("raw_gene_symbols") != PRIMARY_P:
        raise Failure("programs reason=primary-membership-locked-order", EXIT_VALIDATION)
    required_layers = {"primary", "planned_secondary"}
    if not required_layers <= layers:
        raise Failure("programs reason=missing-required-layers", EXIT_VALIDATION)
    if registry.get("schema_version") == REGISTRY_SCHEMA_VERSION_V02:
        observed_ids = [program["id"] for program in programs]
        expected_ids = [program_id for program_id, _layer in V02_PROGRAMS]
        if observed_ids != expected_ids:
            raise Failure(
                "programs reason=v0.2-program-ids-mismatch "
                f"expected={expected_ids} actual={observed_ids}",
                EXIT_VALIDATION,
            )
        for index, (program_id, expected_layer) in enumerate(V02_PROGRAMS):
            actual_layer = programs[index]["layer"]
            if actual_layer != expected_layer:
                raise Failure(
                    f"programs[{index}].layer reason=v0.2-program-layer-mismatch "
                    f"id={program_id} expected={expected_layer} actual={actual_layer}",
                    EXIT_VALIDATION,
                )

    sources = registry["required_coverage_sources"]
    required_ids: list[str] = []
    seen_sources: set[str] = set()
    for index, source in enumerate(sources):
        source_id = source["source_id"]
        if source_id in seen_sources:
            raise Failure(
                f"required_coverage_sources[{index}].source_id reason=duplicate-source-id {source_id}",
                EXIT_VALIDATION,
            )
        seen_sources.add(source_id)
        required_ids.append(source_id)

    canonicalization = registry["canonicalization"]
    alias_map = _alias_map(canonicalization)
    collapse_pairs = canonicalization.get("do_not_collapse", [])
    if not isinstance(collapse_pairs, list):
        raise Failure("canonicalization.do_not_collapse reason=type-mismatch", EXIT_VALIDATION)
    _validate_required_aliases(alias_map, collapse_pairs)
    _validate_do_not_collapse(collapse_pairs, alias_map)
    return alias_map, required_ids, primary


def _column_tokens(name: str) -> list[str]:
    return [token for token in re.split(r"[^A-Za-z0-9]+", name.lower()) if token]


def _reject_forbidden_columns(header: list[str], *, context: str) -> None:
    for column in header:
        tokens = _column_tokens(column)
        forbidden = FORBIDDEN_COLUMN_TOKENS.intersection(tokens)
        if forbidden:
            token = sorted(forbidden)[0]
            raise Failure(
                f"{context} reason=forbidden-column column={column} token={token}",
                EXIT_VALIDATION,
            )


def _parse_annotation_table(raw: bytes, *, context: str) -> list[dict[str, str]]:
    if raw.startswith(GZIP_MAGIC):
        raise Failure(f"{context} reason=compressed-table-forbidden", EXIT_VALIDATION)
    if b"\x00" in raw:
        raise Failure(f"{context} reason=nul-byte", EXIT_VALIDATION)
    if b"\r" in raw:
        raise Failure(f"{context} reason=cr-record-forbidden", EXIT_VALIDATION)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Failure(f"{context} reason=malformed-utf8", EXIT_VALIDATION) from exc
    if text.startswith("\ufeff"):
        raise Failure(f"{context} reason=bom-forbidden", EXIT_VALIDATION)
    if not text:
        raise Failure(f"{context} reason=missing-header", EXIT_VALIDATION)
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines:
        raise Failure(f"{context} reason=missing-header", EXIT_VALIDATION)
    header = lines[0].split("\t")
    _reject_forbidden_columns(header, context=f"{context} header")
    if header != ANNOTATION_HEADER:
        raise Failure(
            f"{context} reason=header-mismatch expected={ANNOTATION_HEADER} actual={header}",
            EXIT_VALIDATION,
        )
    rows: list[dict[str, str]] = []
    seen_exact: set[tuple[str, str, str, str, str]] = set()
    for line_no, line in enumerate(lines[1:], start=2):
        if line == "":
            raise Failure(f"{context} row={line_no} reason=empty-record", EXIT_VALIDATION)
        fields = line.split("\t")
        if len(fields) != 5:
            raise Failure(
                f"{context} row={line_no} reason=field-count expected=5 actual={len(fields)}",
                EXIT_VALIDATION,
            )
        raw_id, canonical_symbol, entrez_id, ensembl_id, mapping_status = fields
        record = (raw_id, canonical_symbol, entrez_id, ensembl_id, mapping_status)
        if record in seen_exact:
            raise Failure(f"{context} row={line_no} reason=duplicate-exact-row", EXIT_VALIDATION)
        seen_exact.add(record)
        if raw_id == "":
            raise Failure(f"{context} row={line_no} field=raw_id reason=empty-raw-id", EXIT_VALIDATION)
        if mapping_status not in MAPPING_STATUSES:
            raise Failure(
                f"{context} row={line_no} field=mapping_status reason=enum-mismatch",
                EXIT_VALIDATION,
            )
        if mapping_status == "mapped":
            if canonical_symbol == "":
                raise Failure(
                    f"{context} row={line_no} reason=mapped-requires-canonical-symbol",
                    EXIT_VALIDATION,
                )
            if entrez_id == "" and ensembl_id == "":
                raise Failure(
                    f"{context} row={line_no} reason=mapped-requires-identifier",
                    EXIT_VALIDATION,
                )
        elif mapping_status == "unmapped":
            if canonical_symbol != "" or entrez_id != "" or ensembl_id != "":
                raise Failure(
                    f"{context} row={line_no} reason=unmapped-requires-empty-identifiers",
                    EXIT_VALIDATION,
                )
        rows.append(
            {
                "raw_id": raw_id,
                "canonical_symbol": canonical_symbol,
                "entrez_id": entrez_id,
                "ensembl_id": ensembl_id,
                "mapping_status": mapping_status,
            }
        )
    return rows


def _validate_manifest(payload: dict[str, Any], *, path: Path) -> None:
    keys = set(payload)
    expected = set(MANIFEST_KEYS)
    extra = keys - expected
    missing = expected - keys
    if extra:
        raise Failure(f"{path} schema reason=unknown-field {sorted(extra)[0]}", EXIT_VALIDATION)
    if missing:
        raise Failure(f"{path} schema reason=missing-required {sorted(missing)[0]}", EXIT_VALIDATION)
    if payload["schema_version"] != MANIFEST_SCHEMA_VERSION:
        raise Failure(f"{path} schema reason=schema-version-mismatch", EXIT_VALIDATION)
    if payload["source_status"] != "pinned":
        raise Failure(f"{path} source_status reason=non-pinned", EXIT_VALIDATION)
    source_id = payload["source_id"]
    if not isinstance(source_id, str) or not SOURCE_ID_RE.fullmatch(source_id):
        raise Failure(f"{path} source_id reason=pattern-mismatch", EXIT_VALIDATION)
    for field in (
        "canonicalization_authority",
        "identifier_namespace",
        "source_reference",
        "table_path",
    ):
        value = payload[field]
        if not isinstance(value, str) or value == "":
            raise Failure(f"{path}.{field} reason=empty-string", EXIT_VALIDATION)
    digest = payload["table_sha256"]
    if not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None:
        raise Failure(f"{path}.table_sha256 reason=pattern-mismatch", EXIT_VALIDATION)


def _resolve_table_path(manifest_path: Path, table_path_value: str) -> Path:
    table_path = Path(table_path_value)
    if not table_path.is_absolute():
        table_path = manifest_path.parent / table_path
    return table_path


def load_annotation_source(manifest_path: Path) -> dict[str, Any]:
    payload, raw = load_json_object(manifest_path, missing_code=EXIT_VALIDATION, invalid_code=EXIT_VALIDATION)
    _validate_manifest(payload, path=manifest_path)
    table_path = _resolve_table_path(manifest_path, payload["table_path"])
    try:
        table_bytes = table_path.read_bytes()
    except FileNotFoundError as exc:
        raise Failure(f"path error reason=missing-table {table_path}", EXIT_VALIDATION) from exc
    except OSError as exc:
        raise Failure(f"I/O failure reading {table_path}", EXIT_IO) from exc
    actual_sha = _sha256(table_bytes)
    if actual_sha != payload["table_sha256"]:
        raise Failure(
            f"{manifest_path} reason=table-hash-mismatch expected={payload['table_sha256']} actual={actual_sha}",
            EXIT_VALIDATION,
        )
    rows = _parse_annotation_table(table_bytes, context=str(table_path))
    return {
        "source_id": payload["source_id"],
        "manifest_path": manifest_path,
        "manifest": payload,
        "manifest_sha256": _sha256(raw),
        "table_path": table_path,
        "table_sha256": actual_sha,
        "rows": rows,
    }


def _annotation_matches(
    row: dict[str, str],
    *,
    raw_symbol: str,
    canonical_symbol: str,
    alias_map: dict[str, str],
) -> bool:
    raw_id = row["raw_id"]
    if raw_id == raw_symbol or raw_id == canonical_symbol:
        return True
    if apply_alias(raw_id, alias_map) == canonical_symbol:
        return True
    ann_canonical = row["canonical_symbol"]
    if ann_canonical and (ann_canonical == canonical_symbol or ann_canonical == raw_symbol):
        return True
    return False


def _unique_sorted(values: Iterable[str]) -> list[str]:
    return sorted({value for value in values if value != ""})


def _aggregate_mapping_status(statuses: list[str]) -> str:
    if not statuses:
        return "absent"
    unique = set(statuses)
    if len(unique) == 1:
        return next(iter(unique))
    return "mixed"


def build_registry_rows(
    programs: list[dict[str, Any]],
    alias_map: dict[str, str],
    primary_canonical: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    null_programs: list[dict[str, Any]] = []
    for program_index, program in enumerate(programs):
        symbols = program["raw_gene_symbols"]
        if symbols is None:
            null_programs.append(
                {
                    "program_index": program_index,
                    "program_id": program["id"],
                    "program_layer": program["layer"],
                    "membership_status": program["membership_status"],
                    "membership_sha256": program["membership_sha256"],
                    "direction_status": program["direction_status"],
                    "weights_status": program["weights_status"],
                    "scoring_status": program["scoring_status"],
                    "predictor_status": program["predictor_status"],
                }
            )
            continue
        for member_index, raw_symbol in enumerate(symbols):
            canonical_symbol = apply_alias(raw_symbol, alias_map)
            rows.append(
                {
                    "program_index": program_index,
                    "program_id": program["id"],
                    "program_layer": program["layer"],
                    "member_index": member_index,
                    "raw_symbol": raw_symbol,
                    "canonical_symbol": canonical_symbol,
                    "alias_applied": canonical_symbol != raw_symbol,
                    "overlap_with_primary_p": canonical_symbol in primary_canonical,
                    "membership_status": program["membership_status"],
                    "direction_status": program["direction_status"],
                    "weights_status": program["weights_status"],
                    "scoring_status": program["scoring_status"],
                    "predictor_status": program["predictor_status"],
                }
            )
    return rows, null_programs


def build_coverage_rows(
    registry_rows: list[dict[str, Any]],
    required_ids: list[str],
    sources: dict[str, dict[str, Any]],
    alias_map: dict[str, str],
) -> list[dict[str, Any]]:
    coverage: list[dict[str, Any]] = []
    for registry_row in registry_rows:
        for source_id in required_ids:
            annotation_rows = sources[source_id]["rows"]
            matched = [
                row
                for row in annotation_rows
                if _annotation_matches(
                    row,
                    raw_symbol=registry_row["raw_symbol"],
                    canonical_symbol=registry_row["canonical_symbol"],
                    alias_map=alias_map,
                )
            ]
            statuses = [row["mapping_status"] for row in matched]
            coverage.append(
                {
                    "program_index": registry_row["program_index"],
                    "program_id": registry_row["program_id"],
                    "program_layer": registry_row["program_layer"],
                    "member_index": registry_row["member_index"],
                    "raw_symbol": registry_row["raw_symbol"],
                    "canonical_symbol": registry_row["canonical_symbol"],
                    "source_id": source_id,
                    "present": bool(matched),
                    "matching_row_count": len(matched),
                    "duplicate": len(matched) > 1,
                    "aggregate_mapping_status": _aggregate_mapping_status(statuses),
                    "raw_ids": _unique_sorted(row["raw_id"] for row in matched),
                    "entrez_ids": _unique_sorted(row["entrez_id"] for row in matched),
                    "ensembl_ids": _unique_sorted(row["ensembl_id"] for row in matched),
                }
            )
    return coverage


def _tsv_field(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    text = str(value)
    if any(char in text for char in ("\t", "\n", "\r", '"')):
        return json.dumps(text, ensure_ascii=False)
    return text


def _tsv_bytes(fields: list[str], rows: list[dict[str, Any]]) -> bytes:
    lines = ["\t".join(fields)]
    for row in rows:
        lines.append("\t".join(_tsv_field(row[name]) for name in fields))
    return ("\n".join(lines) + "\n").encode("utf-8")


def _write_bytes(path: Path, payload: bytes) -> None:
    try:
        with path.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise Failure(f"I/O failure writing {path}", EXIT_IO) from exc


def _atomic_output_directory(output_path: Path):
    class _AtomicDir:
        def __init__(self) -> None:
            self.tmp: Path | None = None

        def __enter__(self) -> Path:
            parent = output_path.parent
            try:
                parent.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise Failure(f"I/O failure creating parent directory {parent}", EXIT_IO) from exc
            if os.path.lexists(output_path):
                raise Failure(
                    f"output argument reason=output path must not already exist: {output_path}",
                    EXIT_ARGUMENT,
                )
            tmp = parent / f".{output_path.name}.b_gene_registry.{os.getpid()}.{uuid.uuid4().hex}"
            try:
                tmp.mkdir(exist_ok=False)
            except OSError as exc:
                raise Failure(f"I/O failure creating temporary directory {tmp}", EXIT_IO) from exc
            self.tmp = tmp
            return tmp

        def __exit__(self, exc_type, exc, traceback) -> None:
            tmp = self.tmp
            if tmp is None:
                return
            if exc_type is None:
                try:
                    os.replace(tmp, output_path)
                    self.tmp = None
                    return
                except OSError as replace_exc:
                    if os.path.lexists(output_path):
                        failure = Failure(
                            f"output argument reason=output path must not already exist: {output_path}",
                            EXIT_ARGUMENT,
                        )
                    else:
                        failure = Failure(
                            f"I/O failure promoting output directory {output_path}",
                            EXIT_IO,
                        )
                    try:
                        shutil.rmtree(tmp)
                    except OSError:
                        pass
                    self.tmp = None
                    raise failure from replace_exc
            try:
                if os.path.lexists(tmp):
                    shutil.rmtree(tmp)
            except OSError:
                pass
            self.tmp = None

    return _AtomicDir()


def _bind_sources(
    required_ids: list[str],
    annotation_manifests: list[Path],
) -> tuple[dict[str, dict[str, Any]], list[str], list[str]]:
    loaded: dict[str, dict[str, Any]] = {}
    for manifest_path in annotation_manifests:
        source = load_annotation_source(manifest_path)
        source_id = source["source_id"]
        if source_id in loaded:
            raise Failure(f"annotation-manifest reason=duplicate-source-id {source_id}", EXIT_VALIDATION)
        if source_id not in required_ids:
            raise Failure(f"annotation-manifest reason=unknown-source-id {source_id}", EXIT_VALIDATION)
        loaded[source_id] = source
    missing = [source_id for source_id in required_ids if source_id not in loaded]
    supplied = [source_id for source_id in required_ids if source_id in loaded]
    return loaded, supplied, missing


def _manifest_hash_records(required_ids: list[str], sources: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    records = []
    for source_id in required_ids:
        if source_id not in sources:
            continue
        source = sources[source_id]
        records.append(
            {
                "source_id": source_id,
                "manifest_sha256": source["manifest_sha256"],
                "table_sha256": source["table_sha256"],
            }
        )
    return records


def write_incomplete(
    output_path: Path,
    *,
    registry_sha256: str,
    schema_sha256: str,
    required_ids: list[str],
    supplied_ids: list[str],
    missing_ids: list[str],
    sources: dict[str, dict[str, Any]],
) -> None:
    payload = {
        "schema_version": SCHEMA_VERSION_INCOMPLETE,
        "status": "incomplete_missing_annotations",
        "required_source_ids": list(required_ids),
        "supplied_source_ids": list(supplied_ids),
        "missing_source_ids": list(missing_ids),
        "registry_sha256": registry_sha256,
        "schema_sha256": schema_sha256,
        "manifests": _manifest_hash_records(required_ids, sources),
    }
    with _atomic_output_directory(output_path) as tmp:
        _write_bytes(tmp / "INCOMPLETE.json", _canonical_json_bytes(payload))


def write_complete(
    output_path: Path,
    *,
    registry: dict[str, Any],
    registry_sha256: str,
    schema_sha256: str,
    required_ids: list[str],
    sources: dict[str, dict[str, Any]],
    alias_map: dict[str, str],
    primary: dict[str, Any],
) -> None:
    primary_canonical = {apply_alias(symbol, alias_map) for symbol in primary["raw_gene_symbols"]}
    registry_rows, null_programs = build_registry_rows(registry["programs"], alias_map, primary_canonical)
    coverage_rows = build_coverage_rows(registry_rows, required_ids, sources, alias_map)
    registry_rows_json = {
        "schema_version": SCHEMA_VERSION_REGISTRY_ROWS,
        "row_count": len(registry_rows),
        "null_membership_programs": null_programs,
        "rows": registry_rows,
    }
    coverage_json = {
        "schema_version": SCHEMA_VERSION_COVERAGE,
        "row_count": len(coverage_rows),
        "required_source_ids": list(required_ids),
        "rows": coverage_rows,
    }
    registry_rows_tsv = _tsv_bytes(REGISTRY_ROWS_TSV_FIELDS, registry_rows)
    coverage_tsv = _tsv_bytes(COVERAGE_TSV_FIELDS, coverage_rows)
    registry_rows_json_bytes = _canonical_json_bytes(registry_rows_json)
    coverage_json_bytes = _canonical_json_bytes(coverage_json)
    checksums = {
        "schema_version": SCHEMA_VERSION_CHECKSUMS,
        "inputs": {
            "registry_sha256": registry_sha256,
            "schema_sha256": schema_sha256,
            "annotation_sources": _manifest_hash_records(required_ids, sources),
        },
        "outputs": {
            "coverage.json": _sha256(coverage_json_bytes),
            "coverage.tsv": _sha256(coverage_tsv),
            "registry_rows.json": _sha256(registry_rows_json_bytes),
            "registry_rows.tsv": _sha256(registry_rows_tsv),
        },
    }
    checksums_bytes = _canonical_json_bytes(checksums)
    complete = {
        "schema_version": SCHEMA_VERSION_COMPLETE,
        "status": "complete",
        "program_count": len(registry["programs"]),
        "registry_row_count": len(registry_rows),
        "coverage_row_count": len(coverage_rows),
        "null_membership_program_count": len(null_programs),
        "required_source_ids": list(required_ids),
        "checksums_sha256": _sha256(checksums_bytes),
    }
    with _atomic_output_directory(output_path) as tmp:
        _write_bytes(tmp / "registry_rows.tsv", registry_rows_tsv)
        _write_bytes(tmp / "registry_rows.json", registry_rows_json_bytes)
        _write_bytes(tmp / "coverage.tsv", coverage_tsv)
        _write_bytes(tmp / "coverage.json", coverage_json_bytes)
        _write_bytes(tmp / "checksums.json", checksums_bytes)
        _write_bytes(tmp / "COMPLETE.json", _canonical_json_bytes(complete))


def run_build(
    *,
    registry_path: Path,
    schema_path: Path,
    annotation_manifests: list[Path],
    output_path: Path,
) -> int:
    if os.path.lexists(output_path):
        raise Failure(
            f"output argument reason=output path must not already exist: {output_path}",
            EXIT_ARGUMENT,
        )
    schema, schema_raw = load_json_object(schema_path, missing_code=EXIT_IO, invalid_code=EXIT_VALIDATION)
    registry, registry_raw = load_json_object(registry_path, missing_code=EXIT_IO, invalid_code=EXIT_VALIDATION)
    assert_schema_identity(schema)
    _reject_duplicate_raw_members(registry)
    validate_against_schema(registry, schema)
    alias_map, required_ids, primary = _validate_registry_contract(registry)
    sources, supplied_ids, missing_ids = _bind_sources(required_ids, annotation_manifests)
    registry_sha256 = _sha256(registry_raw)
    schema_sha256 = _sha256(schema_raw)
    if missing_ids:
        write_incomplete(
            output_path,
            registry_sha256=registry_sha256,
            schema_sha256=schema_sha256,
            required_ids=required_ids,
            supplied_ids=supplied_ids,
            missing_ids=missing_ids,
            sources=sources,
        )
        return EXIT_VALIDATION
    write_complete(
        output_path,
        registry=registry,
        registry_sha256=registry_sha256,
        schema_sha256=schema_sha256,
        required_ids=required_ids,
        sources=sources,
        alias_map=alias_map,
        primary=primary,
    )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate the Paper B gene-set registry and audit annotation coverage.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--registry", required=True, type=Path)
    build_parser.add_argument("--schema", required=True, type=Path)
    build_parser.add_argument("--annotation-manifest", action="append", default=[], type=Path)
    build_parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code
        if code in (0, 2):
            return int(code or 0)
        return EXIT_ARGUMENT
    if args.command != "build":
        print("usage reason=only-build-subcommand-admitted", file=sys.stderr)
        return EXIT_ARGUMENT
    try:
        return run_build(
            registry_path=args.registry,
            schema_path=args.schema,
            annotation_manifests=list(args.annotation_manifest),
            output_path=args.output,
        )
    except Failure as exc:
        print(str(exc), file=sys.stderr)
        return exc.code
    except OSError as exc:
        print(f"I/O failure {exc}", file=sys.stderr)
        return EXIT_IO
    except Exception as exc:  # pragma: no cover
        print(f"unexpected_error={exc}", file=sys.stderr)
        return EXIT_IO


if __name__ == "__main__":
    raise SystemExit(main())
