"""B-G2 deterministic, patient-free annotation normalization."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import re
import shutil
import sqlite3
import sys
import tarfile
import tempfile
import uuid
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator
from urllib.parse import parse_qsl, quote, urlsplit


EXIT_ARGUMENT = 2
EXIT_VALIDATION = 3
EXIT_IO = 4

PLAN_VERSION = "B-G2-annotation-normalization-proposed-v1"
RECEIPT_VERSION = "B-G2-source-freeze-receipt-v1"
MANIFEST_VERSION = "B-G1-annotation-manifest-v1"
SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"
SCHEMA_ID = "https://local.invalid/specs/B/annotation_normalization.schema.json"
SCHEMA_SEMANTIC_SHA256 = "e3721bfbac3ab677d5d832f7a42fc3d5487cd0a73b950ca78ee25e352297447b"

SOURCE_IDS = ("tcga_gencode_v36", "gse107299_processed", "historical_v18_maps")
SOURCE_ROLES = {
    "tcga_gencode_v36": ("tcga_gencode_v36",),
    "gse107299_processed": ("gse107299_processed",),
    "historical_v18_maps": ("hta20", "hugene20st"),
}
ALIASES = {"MB21D1": "CGAS", "TMEM173": "STING1", "TAPBPR": "TAPBPL"}
DO_NOT_COLLAPSE = ("TAPBP", "TAPBPL")
ANNOTATION_HEADER = ("raw_id", "canonical_symbol", "entrez_id", "ensembl_id", "mapping_status")
MAPPING_STATUSES = frozenset({"mapped", "ambiguous", "unmapped"})
TCGA_HEADER = (
    "gene_id",
    "gene_name",
    "gene_type",
    "unstranded",
    "stranded_first",
    "stranded_second",
    "tpm_unstranded",
    "fpkm_unstranded",
    "fpkm_uq_unstranded",
)
TCGA_SUMMARIES = frozenset({"N_unmapped", "N_multimapping", "N_noFeature", "N_ambiguous"})
GSE_HEADER = ("GeneID", "Symbol_UCSC", "Name_UCSC", "Chr_UCSC", "Start_UCSC", "End_UCSC", "RefSeq_UCSC")
RECEIPT_KEYS = frozenset(
    {
        "schema_version",
        "purpose",
        "source_id",
        "pin_authorized",
        "plan_sha256",
        "schema_sha256",
        "inputs",
        "reviewer_id",
        "reviewer_identity",
        "reviewed_utc",
        "notes",
    }
)
INPUT_DESCRIPTOR_KEYS = frozenset(
    {
        "role",
        "object_name",
        "byte_count",
        "sha256",
        "retrieved_utc",
        "exact_url",
        "access_class",
        "completeness",
        "redistribution",
        "committed_path",
    }
)
MANIFEST_KEYS = frozenset(
    {
        "schema_version",
        "source_id",
        "source_status",
        "canonicalization_authority",
        "identifier_namespace",
        "source_reference",
        "table_path",
        "table_sha256",
    }
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DIGITS_RE = re.compile(r"^[0-9]+$")
FORBIDDEN_NULL_TOKENS = frozenset({"na", "null", "nan"})
FORBIDDEN_URL_QUERY_KEYS = frozenset(
    {"access_token", "api_key", "apikey", "key", "password", "secret", "signature", "token"}
)
GZIP_MAGIC = b"\x1f\x8b"
SQLITE_MAGIC = b"SQLite format 3\x00"

CONFLICT_HEADER = ("raw_id", "conflict_type", "native_symbol", "native_entrez_id", "native_ensembl_id", "detail")
HLA_HEADER = ("raw_id", "source_symbol", "canonical_symbol", "mapping_status")
UNMAPPED_HEADER = ("raw_id", "native_symbol", "native_entrez_id", "native_ensembl_id", "reason")


class Failure(Exception):
    """A boundary failure with a stable process exit code and receipt status."""

    def __init__(self, message: str, code: int = EXIT_VALIDATION, *, status: str = "failed") -> None:
        super().__init__(message)
        self.code = code
        self.status = status


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode("utf-8")


def _duplicate_rejecting_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise Failure(f"json reason=duplicate-key field={key}")
        result[key] = value
    return result


def _load_json(path: Path, *, missing_status: str = "failed") -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        raise Failure(f"path reason=missing-json file={path.name}", status=missing_status) from exc
    except OSError as exc:
        raise Failure(f"I/O failure reading {path}", EXIT_IO) from exc
    if b"\x00" in raw:
        raise Failure(f"json reason=nul-byte file={path.name}")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise Failure(f"json reason=malformed-utf8 file={path.name}") from exc
    try:
        payload = json.loads(text, object_pairs_hook=_duplicate_rejecting_object)
    except Failure:
        raise
    except (json.JSONDecodeError, ValueError) as exc:
        raise Failure(f"json reason=invalid file={path.name}") from exc
    if not isinstance(payload, dict):
        raise Failure(f"json reason=top-level-not-object file={path.name}")
    return payload, raw


def _json_kind(value: Any) -> str:
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


def _schema_type_matches(value: Any, declared: Any) -> bool:
    allowed = declared if isinstance(declared, list) else [declared]
    actual = _json_kind(value)
    return actual in allowed or (actual == "integer" and "number" in allowed)


def _resolve_pointer(root: dict[str, Any], pointer: str) -> Any:
    if not pointer.startswith("#/"):
        raise Failure(f"schema reason=unsupported-ref ref={pointer}")
    node: Any = root
    for token in pointer[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or token not in node:
            raise Failure(f"schema reason=unresolved-ref ref={pointer}")
        node = node[token]
    return node


def _validate_schema_node(value: Any, node: dict[str, Any], root: dict[str, Any], path: str) -> None:
    if "$ref" in node:
        target = _resolve_pointer(root, node["$ref"])
        if not isinstance(target, dict):
            raise Failure(f"schema reason=invalid-ref-target path={path}")
        _validate_schema_node(value, target, root, path)
    for child in node.get("allOf", []):
        _validate_schema_node(value, child, root, path)
    if "type" in node and not _schema_type_matches(value, node["type"]):
        raise Failure(f"plan reason=type-mismatch path={path}")
    if "const" in node and value != node["const"]:
        raise Failure(f"plan reason=const-mismatch path={path}")
    if "enum" in node and value not in node["enum"]:
        raise Failure(f"plan reason=enum-mismatch path={path}")
    if isinstance(value, dict):
        required = node.get("required", [])
        for key in required:
            if key not in value:
                raise Failure(f"plan reason=missing-required path={path}.{key}")
        properties = node.get("properties", {})
        if node.get("additionalProperties") is False:
            extras = sorted(set(value) - set(properties))
            if extras:
                raise Failure(f"plan reason=unknown-field path={path}.{extras[0]}")
        for key, child_value in value.items():
            child_schema = properties.get(key)
            if isinstance(child_schema, dict):
                _validate_schema_node(child_value, child_schema, root, f"{path}.{key}")
    elif isinstance(value, list):
        if "minItems" in node and len(value) < node["minItems"]:
            raise Failure(f"plan reason=min-items path={path}")
        if "maxItems" in node and len(value) > node["maxItems"]:
            raise Failure(f"plan reason=max-items path={path}")
        prefix = node.get("prefixItems", [])
        for index, child_schema in enumerate(prefix[: len(value)]):
            _validate_schema_node(value[index], child_schema, root, f"{path}[{index}]")
        item_schema = node.get("items")
        if item_schema is False and len(value) > len(prefix):
            raise Failure(f"plan reason=extra-array-item path={path}")
        if isinstance(item_schema, dict):
            for index, child_value in enumerate(value[len(prefix) :], start=len(prefix)):
                _validate_schema_node(child_value, item_schema, root, f"{path}[{index}]")
    elif isinstance(value, str):
        if "minLength" in node and len(value) < node["minLength"]:
            raise Failure(f"plan reason=min-length path={path}")
        if "pattern" in node and re.fullmatch(node["pattern"], value) is None:
            raise Failure(f"plan reason=pattern-mismatch path={path}")
        if node.get("format") == "date":
            try:
                datetime.strptime(value, "%Y-%m-%d")
            except ValueError as exc:
                raise Failure(f"plan reason=invalid-date path={path}") from exc
    elif isinstance(value, int) and not isinstance(value, bool):
        if "minimum" in node and value < node["minimum"]:
            raise Failure(f"plan reason=minimum path={path}")


def _validate_plan(plan: dict[str, Any], schema: dict[str, Any]) -> None:
    if schema.get("$schema") != SCHEMA_DIALECT or schema.get("$id") != SCHEMA_ID:
        raise Failure("schema reason=identity-mismatch")
    semantic = _sha256(json.dumps(schema, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    if semantic != SCHEMA_SEMANTIC_SHA256:
        raise Failure("schema reason=semantic-hash-mismatch")
    _validate_schema_node(plan, schema, schema, "plan")
    if plan.get("schema_version") != PLAN_VERSION:
        raise Failure("plan reason=schema-version-mismatch")
    sources = plan.get("sources")
    if not isinstance(sources, list) or tuple(source.get("source_id") for source in sources) != SOURCE_IDS:
        raise Failure("plan reason=source-order-mismatch")
    aliases = plan.get("canonicalization", {}).get("alias_rules")
    observed_aliases = {
        item.get("raw_symbol"): item.get("canonical_symbol") for item in aliases or [] if isinstance(item, dict)
    }
    if observed_aliases != ALIASES:
        raise Failure("plan reason=alias-contract-mismatch")
    if plan.get("canonicalization", {}).get("do_not_collapse") != [[*DO_NOT_COLLAPSE]]:
        raise Failure("plan reason=non-collapse-contract-mismatch")


def _require_exact_keys(payload: dict[str, Any], expected: frozenset[str], context: str) -> None:
    extra = sorted(set(payload) - expected)
    missing = sorted(expected - set(payload))
    if extra:
        raise Failure(f"{context} reason=unknown-field field={extra[0]}")
    if missing:
        raise Failure(f"{context} reason=missing-required field={missing[0]}")


def _nonempty_string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise Failure(f"{context} reason=nonempty-string-required")
    return value


def _utc_timestamp(value: Any, context: str) -> str:
    text = _nonempty_string(value, context)
    if not (text.endswith("Z") or text.endswith("+00:00")):
        raise Failure(f"{context} reason=utc-required")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)
    except ValueError as exc:
        raise Failure(f"{context} reason=invalid-timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise Failure(f"{context} reason=utc-required")
    return text


def _credential_free_url(value: Any, context: str) -> str:
    text = _nonempty_string(value, context)
    parsed = urlsplit(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise Failure(f"{context} reason=http-url-required")
    if parsed.username is not None or parsed.password is not None:
        raise Failure(f"{context} reason=credentials-forbidden")
    for key, _ in parse_qsl(parsed.query, keep_blank_values=True):
        if key.lower() in FORBIDDEN_URL_QUERY_KEYS:
            raise Failure(f"{context} reason=credentials-forbidden")
    return text


def _validate_receipt(
    receipt: dict[str, Any],
    *,
    source_id: str,
    plan_sha256: str,
    schema_sha256: str,
) -> None:
    _require_exact_keys(receipt, RECEIPT_KEYS, "freeze-receipt")
    if receipt["schema_version"] != RECEIPT_VERSION:
        raise Failure("freeze-receipt reason=schema-version-mismatch")
    if receipt["purpose"] != "source_freeze":
        raise Failure("freeze-receipt reason=source-freeze-required", status="incomplete_missing_freeze")
    if receipt["pin_authorized"] is not True:
        raise Failure("freeze-receipt reason=pin-authorization-required", status="incomplete_missing_freeze")
    if receipt["source_id"] != source_id:
        raise Failure("freeze-receipt reason=source-id-mismatch")
    for field, expected in (("plan_sha256", plan_sha256), ("schema_sha256", schema_sha256)):
        value = receipt[field]
        if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None or value != expected:
            raise Failure(f"freeze-receipt reason={field}-mismatch", status="incomplete_hash_mismatch")
    _nonempty_string(receipt["reviewer_id"], "freeze-receipt.reviewer_id")
    _nonempty_string(receipt["reviewer_identity"], "freeze-receipt.reviewer_identity")
    _utc_timestamp(receipt["reviewed_utc"], "freeze-receipt.reviewed_utc")
    _nonempty_string(receipt["notes"], "freeze-receipt.notes")
    descriptors = receipt["inputs"]
    if not isinstance(descriptors, list):
        raise Failure("freeze-receipt.inputs reason=array-required")
    expected_roles = SOURCE_ROLES[source_id]
    if len(descriptors) != len(expected_roles):
        raise Failure("freeze-receipt.inputs reason=cardinality-mismatch")
    for index, (descriptor, role) in enumerate(zip(descriptors, expected_roles)):
        if not isinstance(descriptor, dict):
            raise Failure(f"freeze-receipt.inputs[{index}] reason=object-required")
        _require_exact_keys(descriptor, INPUT_DESCRIPTOR_KEYS, f"freeze-receipt.inputs[{index}]")
        if descriptor["role"] != role:
            raise Failure(f"freeze-receipt.inputs[{index}] reason=role-order-mismatch")
        object_name = _nonempty_string(
            descriptor["object_name"], f"freeze-receipt.inputs[{index}].object_name"
        )
        if object_name in {".", ".."} or "/" in object_name or "\\" in object_name or re.match(r"^[A-Za-z]:", object_name):
            raise Failure(f"freeze-receipt.inputs[{index}].object_name reason=basename-required")
        count = descriptor["byte_count"]
        if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
            raise Failure(f"freeze-receipt.inputs[{index}].byte_count reason=positive-integer-required")
        digest = descriptor["sha256"]
        if not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None:
            raise Failure(f"freeze-receipt.inputs[{index}].sha256 reason=lowercase-sha256-required")
        _utc_timestamp(descriptor["retrieved_utc"], f"freeze-receipt.inputs[{index}].retrieved_utc")
        _credential_free_url(descriptor["exact_url"], f"freeze-receipt.inputs[{index}].exact_url")
        if descriptor["access_class"] != "public":
            raise Failure(f"freeze-receipt.inputs[{index}].access_class reason=public-required")
        _nonempty_string(descriptor["completeness"], f"freeze-receipt.inputs[{index}].completeness")
        if descriptor["redistribution"] != "not_adjudicated":
            raise Failure(f"freeze-receipt.inputs[{index}].redistribution reason=not-adjudicated-required")
        if descriptor["committed_path"] is not None:
            raise Failure(f"freeze-receipt.inputs[{index}].committed_path reason=null-required")


def _parse_cli_inputs(values: list[str], source_id: str) -> list[tuple[str, Path]]:
    parsed: list[tuple[str, Path]] = []
    for value in values:
        if "=" not in value:
            raise Failure("input argument reason=ROLE=PATH-required", EXIT_ARGUMENT)
        role, path_text = value.split("=", 1)
        if not role or not path_text:
            raise Failure("input argument reason=ROLE=PATH-required", EXIT_ARGUMENT)
        parsed.append((role, Path(path_text)))
    expected = SOURCE_ROLES[source_id]
    if tuple(role for role, _ in parsed) != expected:
        raise Failure("input argument reason=role-order-or-cardinality-mismatch")
    return parsed


def _read_and_bind_inputs(
    parsed: list[tuple[str, Path]],
    descriptors: list[dict[str, Any]],
    observed: list[dict[str, Any]],
) -> tuple[list[tuple[str, Path, bytes]], list[dict[str, Any]]]:
    bound: list[tuple[str, Path, bytes]] = []
    for index, ((role, path), descriptor) in enumerate(zip(parsed, descriptors)):
        if role != descriptor["role"]:
            raise Failure(f"input[{index}] reason=receipt-role-mismatch")
        try:
            raw = path.read_bytes()
        except FileNotFoundError as exc:
            raise Failure(f"input[{index}] reason=missing-file") from exc
        except OSError as exc:
            raise Failure(f"I/O failure reading input[{index}]", EXIT_IO) from exc
        digest = _sha256(raw)
        observed.append({"role": role, "byte_count": len(raw), "sha256": digest})
        if len(raw) != descriptor["byte_count"]:
            raise Failure(f"input[{index}] reason=byte-count-mismatch", status="incomplete_hash_mismatch")
        if digest != descriptor["sha256"]:
            raise Failure(f"input[{index}] reason=sha256-mismatch", status="incomplete_hash_mismatch")
        bound.append((role, path, raw))
    return bound, observed


def _decode_utf8(raw: bytes, context: str, *, allow_bom: bool = False) -> str:
    if b"\x00" in raw:
        raise Failure(f"{context} reason=nul-byte", status="incomplete_parser")
    if raw.startswith(b"\xef\xbb\xbf") and not allow_bom:
        raise Failure(f"{context} reason=utf8-bom-forbidden", status="incomplete_parser")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Failure(f"{context} reason=malformed-utf8", status="incomplete_parser") from exc


def _row_sort_key(row: dict[str, str]) -> tuple[str, str, str, str, str]:
    return (
        row["raw_id"],
        row["mapping_status"],
        row["canonical_symbol"],
        row["entrez_id"],
        row["ensembl_id"],
    )


def _apply_alias(symbol: str) -> str:
    return ALIASES.get(symbol, symbol)


def _validate_annotation_rows(rows: list[dict[str, str]], *, require_sorted: bool) -> None:
    seen: set[tuple[str, str, str, str, str]] = set()
    for index, row in enumerate(rows, start=2):
        values = tuple(row[field] for field in ANNOTATION_HEADER)
        if any("\t" in value or "\n" in value or "\r" in value or "\x00" in value for value in values):
            raise Failure(f"annotation row={index} reason=control-character")
        raw_id, canonical, entrez, ensembl, status = values
        if not raw_id:
            raise Failure(f"annotation row={index} reason=empty-raw-id")
        if any(value.lower() in FORBIDDEN_NULL_TOKENS for value in values if value):
            raise Failure(f"annotation row={index} reason=forbidden-null-token")
        if status not in MAPPING_STATUSES:
            raise Failure(f"annotation row={index} reason=invalid-mapping-status")
        if status == "mapped" and (not canonical or not (entrez or ensembl)):
            raise Failure(f"annotation row={index} reason=invalid-mapped-cells")
        if status == "unmapped" and (canonical or entrez or ensembl):
            raise Failure(f"annotation row={index} reason=invalid-unmapped-cells")
        if status == "ambiguous" and not (canonical or entrez or ensembl):
            raise Failure(f"annotation row={index} reason=empty-ambiguous-candidates")
        if raw_id in ALIASES and canonical != ALIASES[raw_id]:
            raise Failure(f"annotation row={index} reason=alias-not-applied")
        if raw_id == DO_NOT_COLLAPSE[0] and canonical == DO_NOT_COLLAPSE[1]:
            raise Failure(f"annotation row={index} reason=tapbp-tapbpl-collapse")
        if values in seen:
            raise Failure(f"annotation row={index} reason=duplicate-exact-row")
        seen.add(values)
    if require_sorted and rows != sorted(rows, key=_row_sort_key):
        raise Failure("annotation reason=unstable-row-order")


def _annotation_tsv_bytes(rows: list[dict[str, str]]) -> bytes:
    ordered = sorted(rows, key=_row_sort_key)
    _validate_annotation_rows(ordered, require_sorted=True)
    lines = ["\t".join(ANNOTATION_HEADER)]
    lines.extend("\t".join(row[field] for field in ANNOTATION_HEADER) for row in ordered)
    return ("\n".join(lines) + "\n").encode("utf-8")


def _parse_annotation_tsv(raw: bytes) -> list[dict[str, str]]:
    if raw.startswith(GZIP_MAGIC):
        raise Failure("annotation reason=gzip-forbidden")
    if b"\r" in raw:
        raise Failure("annotation reason=lf-newlines-required")
    text = _decode_utf8(raw, "annotation")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines or tuple(lines[0].split("\t")) != ANNOTATION_HEADER:
        raise Failure("annotation reason=header-mismatch")
    rows: list[dict[str, str]] = []
    for line_no, line in enumerate(lines[1:], start=2):
        fields = line.split("\t")
        if len(fields) != len(ANNOTATION_HEADER):
            raise Failure(f"annotation row={line_no} reason=field-count")
        rows.append(dict(zip(ANNOTATION_HEADER, fields)))
    _validate_annotation_rows(rows, require_sorted=True)
    return rows


def _record_sidecars(
    row: dict[str, str],
    *,
    source_symbol: str,
    native_entrez: str,
    native_ensembl: str,
    unmapped_reason: str,
    hla_rows: list[dict[str, str]],
    unmapped_rows: list[dict[str, str]],
) -> None:
    if source_symbol.startswith("HLA-") or row["canonical_symbol"].startswith("HLA-"):
        hla_rows.append(
            {
                "raw_id": row["raw_id"],
                "source_symbol": source_symbol,
                "canonical_symbol": row["canonical_symbol"],
                "mapping_status": row["mapping_status"],
            }
        )
    if row["mapping_status"] == "unmapped":
        unmapped_rows.append(
            {
                "raw_id": row["raw_id"],
                "native_symbol": source_symbol,
                "native_entrez_id": native_entrez,
                "native_ensembl_id": native_ensembl,
                "reason": unmapped_reason,
            }
        )


def _parse_tcga(raw: bytes) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    if raw.startswith(GZIP_MAGIC):
        raise Failure("tcga reason=gzip-forbidden", status="incomplete_parser")
    text = _decode_utf8(raw, "tcga")
    lines = text.splitlines()
    first_nonempty_index = next((i for i, line in enumerate(lines) if line.strip()), None)
    if first_nonempty_index is None or lines[first_nonempty_index] != "# gene-model: GENCODE v36":
        raise Failure("tcga reason=gencode-v36-comment-required", status="incomplete_parser")
    header_index = next((i for i, line in enumerate(lines) if line.strip() and not line.startswith("#")), None)
    if header_index is None or tuple(lines[header_index].split("\t")) != TCGA_HEADER:
        raise Failure("tcga reason=star-header-mismatch", status="incomplete_parser")
    native: list[tuple[str, str]] = []
    for line_no, line in enumerate(lines[header_index + 1 :], start=header_index + 2):
        if not line:
            continue
        fields = line.split("\t")
        if len(fields) != len(TCGA_HEADER):
            raise Failure(f"tcga row={line_no} reason=field-count", status="incomplete_parser")
        gene_id, symbol = fields[0], fields[1]
        if gene_id in TCGA_SUMMARIES:
            continue
        if not gene_id:
            raise Failure(f"tcga row={line_no} reason=empty-gene-id", status="incomplete_parser")
        native.append((gene_id, symbol))
    candidates: dict[str, set[str]] = defaultdict(set)
    occurrence: Counter[tuple[str, str]] = Counter(native)
    if any(count > 1 for count in occurrence.values()):
        raise Failure("tcga reason=duplicate-exact-native-row", status="incomplete_parser")
    for raw_id, symbol in native:
        candidates[raw_id].add(symbol)
    rows: list[dict[str, str]] = []
    hla: list[dict[str, str]] = []
    unmapped: list[dict[str, str]] = []
    conflicts: list[dict[str, str]] = []
    for raw_id, symbol in native:
        if not symbol:
            row = dict(zip(ANNOTATION_HEADER, (raw_id, "", "", "", "unmapped")))
            reason = "missing-gene-name"
        else:
            canonical = _apply_alias(symbol)
            status = "ambiguous" if len(candidates[raw_id]) > 1 else "mapped"
            row = dict(zip(ANNOTATION_HEADER, (raw_id, canonical, "", raw_id, status)))
            reason = ""
        rows.append(row)
        _record_sidecars(
            row,
            source_symbol=symbol,
            native_entrez="",
            native_ensembl=raw_id,
            unmapped_reason=reason,
            hla_rows=hla,
            unmapped_rows=unmapped,
        )
        if len(candidates[raw_id]) > 1:
            conflicts.append(
                {
                    "raw_id": raw_id,
                    "conflict_type": "one-raw-to-many-symbols",
                    "native_symbol": symbol,
                    "native_entrez_id": "",
                    "native_ensembl_id": raw_id,
                    "detail": "source candidates retained",
                }
            )
    return rows, conflicts, hla, unmapped


def _parse_gse(
    raw: bytes,
    *,
    descriptor: dict[str, Any],
    plan_source: dict[str, Any],
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    compressed = raw.startswith(GZIP_MAGIC)
    if compressed:
        identity = plan_source["object_identity"]
        if _sha256(raw) != identity["compressed_sha256"] or descriptor["object_name"] != identity["object_name"]:
            raise Failure("gse reason=unfrozen-compressed-object", status="incomplete_hash_mismatch")
        try:
            byte_stream: Any = gzip.GzipFile(fileobj=io.BytesIO(raw), mode="rb")
        except OSError as exc:
            raise Failure("gse reason=invalid-gzip", status="incomplete_parser") from exc
    else:
        byte_stream = io.BytesIO(raw)
    native: list[tuple[str, str]] = []
    try:
        with io.TextIOWrapper(byte_stream, encoding="utf-8", errors="strict", newline="") as text_stream:
            header_line = text_stream.readline()
            if not header_line:
                raise Failure("gse reason=empty-input", status="incomplete_parser")
            if "\x00" in header_line:
                raise Failure("gse reason=nul-byte", status="incomplete_parser")
            header = header_line.rstrip("\r\n").split("\t", 7)
            if tuple(header[:7]) != GSE_HEADER:
                raise Failure("gse reason=annotation-header-mismatch", status="incomplete_parser")
            if not compressed and len(header) != 7:
                raise Failure("gse reason=patient-or-value-columns-forbidden", status="incomplete_parser")
            for line_no, line in enumerate(text_stream, start=2):
                if "\x00" in line:
                    raise Failure(f"gse row={line_no} reason=nul-byte", status="incomplete_parser")
                line = line.rstrip("\r\n")
                if not line:
                    continue
                fields = line.split("\t", 7)
                if len(fields) < 7 or (not compressed and len(fields) != 7):
                    raise Failure(f"gse row={line_no} reason=field-count", status="incomplete_parser")
                raw_id, symbol = fields[0], fields[1]
                if not raw_id:
                    raise Failure(f"gse row={line_no} reason=empty-gene-id", status="incomplete_parser")
                native.append((raw_id, symbol))
    except UnicodeDecodeError as exc:
        raise Failure("gse reason=malformed-utf8", status="incomplete_parser") from exc
    except (OSError, EOFError) as exc:
        raise Failure("gse reason=invalid-gzip", status="incomplete_parser") from exc
    occurrence: Counter[tuple[str, str]] = Counter(native)
    if any(count > 1 for count in occurrence.values()):
        raise Failure("gse reason=duplicate-exact-native-row", status="incomplete_parser")
    candidates: dict[str, set[str]] = defaultdict(set)
    for raw_id, symbol in native:
        candidates[raw_id].add(symbol)
    rows: list[dict[str, str]] = []
    hla: list[dict[str, str]] = []
    unmapped: list[dict[str, str]] = []
    conflicts: list[dict[str, str]] = []
    for raw_id, symbol in native:
        if not symbol or DIGITS_RE.fullmatch(raw_id) is None:
            row = dict(zip(ANNOTATION_HEADER, (raw_id, "", "", "", "unmapped")))
            reason = "missing-symbol" if not symbol else "non-numeric-gene-id"
        else:
            canonical = _apply_alias(symbol)
            status = "ambiguous" if len(candidates[raw_id]) > 1 else "mapped"
            row = dict(zip(ANNOTATION_HEADER, (raw_id, canonical, raw_id, "", status)))
            reason = ""
        rows.append(row)
        _record_sidecars(
            row,
            source_symbol=symbol,
            native_entrez=raw_id,
            native_ensembl="",
            unmapped_reason=reason,
            hla_rows=hla,
            unmapped_rows=unmapped,
        )
        if len(candidates[raw_id]) > 1:
            conflicts.append(
                {
                    "raw_id": raw_id,
                    "conflict_type": "one-raw-to-many-symbols",
                    "native_symbol": symbol,
                    "native_entrez_id": raw_id,
                    "native_ensembl_id": "",
                    "detail": "source candidates retained",
                }
            )
    return rows, conflicts, hla, unmapped


def _table_names(connection: sqlite3.Connection) -> dict[str, str]:
    rows = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {str(name).lower(): str(name) for (name,) in rows}


def _quoted_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _columns(connection: sqlite3.Connection, table: str) -> dict[str, str]:
    query = f"PRAGMA table_info({_quoted_identifier(table)})"
    return {str(row[1]).lower(): str(row[1]) for row in connection.execute(query)}


def _optional_map(
    connection: sqlite3.Connection,
    tables: dict[str, str],
    table_key: str,
    value_candidates: tuple[str, ...],
) -> tuple[str | None, dict[str, set[str]]]:
    actual = tables.get(table_key)
    if actual is None:
        return None, {}
    cols = _columns(connection, actual)
    value_col = next((cols[name] for name in value_candidates if name in cols), None)
    key_col = next((cols[name] for name in ("probe_id", "gene_id", "_id") if name in cols), None)
    if value_col is None or key_col is None:
        raise Failure(f"v18 reason=unsupported-{table_key}-schema", status="incomplete_parser")
    query = f"SELECT {_quoted_identifier(key_col)}, {_quoted_identifier(value_col)} FROM {_quoted_identifier(actual)}"
    result: dict[str, set[str]] = defaultdict(set)
    for key, value in connection.execute(query):
        if key is not None and value is not None and str(value):
            result[str(key)].add(str(value))
    return key_col.lower(), result


def _sqlite_rows(
    path: Path,
    *,
    chip: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    uri = f"file:{quote(path.resolve().as_posix(), safe='/:')}?mode=ro&immutable=1"
    try:
        connection = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as exc:
        raise Failure(f"v18 reason=sqlite-open-failed chip={chip}", status="incomplete_parser") from exc
    try:
        connection.execute("PRAGMA query_only=ON")
        tables = _table_names(connection)
        probes_table = tables.get("probes")
        if probes_table is None:
            raise Failure(f"v18 reason=missing-probes-table chip={chip}", status="incomplete_parser")
        probe_cols = _columns(connection, probes_table)
        required = {"probe_id", "gene_id", "is_multiple"}
        if not required.issubset(probe_cols):
            raise Failure(f"v18 reason=probes-schema-mismatch chip={chip}", status="incomplete_parser")
        genes: dict[str, str] = {}
        genes_table = tables.get("genes")
        if genes_table is not None:
            gene_cols = _columns(connection, genes_table)
            if {"_id", "gene_id"}.issubset(gene_cols):
                query = (
                    f"SELECT {_quoted_identifier(gene_cols['_id'])}, {_quoted_identifier(gene_cols['gene_id'])} "
                    f"FROM {_quoted_identifier(genes_table)}"
                )
                genes = {str(internal): str(external) for internal, external in connection.execute(query) if external is not None}
        symbol_key, symbols = _optional_map(connection, tables, "symbol", ("symbol",))
        ensembl_key, ensembl = _optional_map(connection, tables, "ensembl", ("ensembl_id", "ensembl"))
        query = (
            f"SELECT {_quoted_identifier(probe_cols['probe_id'])}, {_quoted_identifier(probe_cols['gene_id'])}, "
            f"{_quoted_identifier(probe_cols['is_multiple'])} FROM {_quoted_identifier(probes_table)} "
            f"ORDER BY {_quoted_identifier(probe_cols['probe_id'])}"
        )
        native_rows = list(connection.execute(query))
    except sqlite3.Error as exc:
        raise Failure(f"v18 reason=sqlite-query-failed chip={chip}", status="incomplete_parser") from exc
    finally:
        connection.close()

    rows: list[dict[str, str]] = []
    conflicts: list[dict[str, str]] = []
    hla: list[dict[str, str]] = []
    unmapped: list[dict[str, str]] = []
    seen_probe_ids: set[str] = set()
    for probe_value, gene_value, _is_multiple in native_rows:
        probe_id = "" if probe_value is None else str(probe_value)
        if not probe_id or not probe_id.endswith("_at"):
            raise Failure(f"v18 reason=probe-suffix-required chip={chip}", status="incomplete_parser")
        if probe_id in seen_probe_ids:
            raise Failure(f"v18 reason=duplicate-probe-id chip={chip}", status="incomplete_parser")
        seen_probe_ids.add(probe_id)
        raw_id = f"{chip}:{probe_id}"
        native_gene = "" if gene_value is None else str(gene_value)
        entrez = genes.get(native_gene, native_gene)

        def candidates(key_kind: str | None, mapping: dict[str, set[str]]) -> set[str]:
            if key_kind == "probe_id":
                return mapping.get(probe_id, set())
            if key_kind == "gene_id":
                return mapping.get(entrez, set()) | mapping.get(native_gene, set())
            if key_kind == "_id":
                return mapping.get(native_gene, set())
            return set()

        source_symbols = sorted(candidates(symbol_key, symbols))
        ensembl_values = sorted(candidates(ensembl_key, ensembl))
        if not entrez or not source_symbols:
            row = dict(zip(ANNOTATION_HEADER, (raw_id, "", "", "", "unmapped")))
            rows.append(row)
            reason = "null-entrez" if not entrez else "missing-historical-symbol"
            _record_sidecars(
                row,
                source_symbol="" if not source_symbols else source_symbols[0],
                native_entrez=entrez,
                native_ensembl=";".join(ensembl_values),
                unmapped_reason=reason,
                hla_rows=hla,
                unmapped_rows=unmapped,
            )
            if probe_id == "101928749_at" and not entrez:
                conflicts.append(
                    {
                        "raw_id": raw_id,
                        "conflict_type": "historical-null-no-suffix-repair",
                        "native_symbol": "",
                        "native_entrez_id": "",
                        "native_ensembl_id": "",
                        "detail": "v18 database NULL retained",
                    }
                )
            continue
        canonical_symbols = sorted({_apply_alias(symbol) for symbol in source_symbols})
        ambiguous_symbols = len(canonical_symbols) > 1
        chosen_ensembl = ensembl_values[0] if len(ensembl_values) == 1 else ""
        if len(ensembl_values) > 1:
            conflicts.append(
                {
                    "raw_id": raw_id,
                    "conflict_type": "one-to-many-ensembl",
                    "native_symbol": ";".join(source_symbols),
                    "native_entrez_id": entrez,
                    "native_ensembl_id": ";".join(ensembl_values),
                    "detail": "Ensembl omitted from annotation cell",
                }
            )
        for canonical in canonical_symbols:
            status = "ambiguous" if ambiguous_symbols else "mapped"
            row = dict(zip(ANNOTATION_HEADER, (raw_id, canonical, entrez, chosen_ensembl, status)))
            rows.append(row)
            original = next(symbol for symbol in source_symbols if _apply_alias(symbol) == canonical)
            _record_sidecars(
                row,
                source_symbol=original,
                native_entrez=entrez,
                native_ensembl=";".join(ensembl_values),
                unmapped_reason="",
                hla_rows=hla,
                unmapped_rows=unmapped,
            )
        if ambiguous_symbols:
            conflicts.append(
                {
                    "raw_id": raw_id,
                    "conflict_type": "one-raw-to-many-symbols",
                    "native_symbol": ";".join(source_symbols),
                    "native_entrez_id": entrez,
                    "native_ensembl_id": ";".join(ensembl_values),
                    "detail": "one row per candidate symbol",
                }
            )
    return rows, conflicts, hla, unmapped


@contextmanager
def _sqlite_input_path(
    role: str,
    path: Path,
    raw: bytes,
    *,
    descriptor: dict[str, Any],
    plan_source: dict[str, Any],
) -> Iterator[Path]:
    if raw.startswith(SQLITE_MAGIC):
        expected_name = f"{role}hsentrezg.sqlite"
        if descriptor["object_name"] != expected_name:
            raise Failure(f"v18 reason=sqlite-object-name-mismatch role={role}")
        yield path
        return
    if not raw.startswith(GZIP_MAGIC):
        raise Failure(f"v18 reason=sqlite-or-tar-gzip-required role={role}", status="incomplete_parser")
    identity = plan_source["object_identity"]
    expected_package = identity[f"{role}_package"]
    expected_package_sha = identity[f"{role}_sha256"]
    if descriptor["object_name"] != expected_package or _sha256(raw) != expected_package_sha:
        raise Failure(f"v18 reason=unfrozen-package role={role}", status="incomplete_hash_mismatch")
    expected_suffix = f"{role}hsentrezg.db/inst/extdata/{role}hsentrezg.sqlite"
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
            matches = [member for member in archive.getmembers() if member.isfile() and member.name.replace("\\", "/").endswith(expected_suffix)]
            if len(matches) != 1:
                raise Failure(f"v18 reason=sqlite-member-cardinality role={role}", status="incomplete_parser")
            extracted = archive.extractfile(matches[0])
            if extracted is None:
                raise Failure(f"v18 reason=sqlite-member-unreadable role={role}", status="incomplete_parser")
            sqlite_bytes = extracted.read()
    except (tarfile.TarError, OSError) as exc:
        raise Failure(f"v18 reason=invalid-package role={role}", status="incomplete_parser") from exc
    if not sqlite_bytes.startswith(SQLITE_MAGIC):
        raise Failure(f"v18 reason=invalid-sqlite-member role={role}", status="incomplete_parser")
    if _sha256(sqlite_bytes) != identity[f"sqlite_{role}_sha256"]:
        raise Failure(f"v18 reason=sqlite-member-hash-mismatch role={role}", status="incomplete_hash_mismatch")
    with tempfile.TemporaryDirectory(prefix=f"b_g2_{role}_") as temp_dir:
        sqlite_path = Path(temp_dir) / f"{role}.sqlite"
        sqlite_path.write_bytes(sqlite_bytes)
        yield sqlite_path


def _parse_v18(
    bound: list[tuple[str, Path, bytes]],
    *,
    descriptors: list[dict[str, Any]],
    plan_source: dict[str, Any],
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    all_rows: list[dict[str, str]] = []
    all_conflicts: list[dict[str, str]] = []
    all_hla: list[dict[str, str]] = []
    all_unmapped: list[dict[str, str]] = []
    for (role, path, raw), descriptor in zip(bound, descriptors):
        with _sqlite_input_path(role, path, raw, descriptor=descriptor, plan_source=plan_source) as sqlite_path:
            rows, conflicts, hla, unmapped = _sqlite_rows(sqlite_path, chip=role)
        all_rows.extend(rows)
        all_conflicts.extend(conflicts)
        all_hla.extend(hla)
        all_unmapped.extend(unmapped)
    return all_rows, all_conflicts, all_hla, all_unmapped


def _tsv_bytes(header: Iterable[str], rows: list[dict[str, str]], *, sort_fields: tuple[str, ...]) -> bytes:
    fields = tuple(header)
    ordered = sorted(rows, key=lambda row: tuple(row[field] for field in sort_fields))
    lines = ["\t".join(fields)]
    for row in ordered:
        values = [row[field] for field in fields]
        if any(any(char in value for char in ("\t", "\n", "\r", "\x00")) for value in values):
            raise Failure("sidecar reason=control-character")
        lines.append("\t".join(values))
    return ("\n".join(lines) + "\n").encode("utf-8")


def _write_bytes(path: Path, data: bytes) -> None:
    try:
        with path.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise Failure(f"I/O failure writing {path.name}", EXIT_IO) from exc


@contextmanager
def _atomic_directory(output: Path) -> Iterator[Path]:
    parent = output.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise Failure(f"I/O failure creating output parent {parent}", EXIT_IO) from exc
    if os.path.lexists(output):
        raise Failure("output argument reason=path-already-exists", EXIT_ARGUMENT)
    temp = parent / f".{output.name}.b_annotation_normalize.{os.getpid()}.{uuid.uuid4().hex}"
    try:
        temp.mkdir(exist_ok=False)
    except OSError as exc:
        raise Failure("I/O failure creating temporary output", EXIT_IO) from exc
    try:
        yield temp
        if os.path.lexists(output):
            raise Failure("output argument reason=path-already-exists", EXIT_ARGUMENT)
        os.replace(temp, output)
    except Exception:
        try:
            if os.path.lexists(temp):
                shutil.rmtree(temp)
        except OSError:
            pass
        raise


def _write_failure_receipt(
    output: Path,
    *,
    source_id: str,
    failure: Failure,
    observed_inputs: list[dict[str, Any]],
) -> None:
    if failure.code != EXIT_VALIDATION or os.path.lexists(output):
        return
    filename = "INCOMPLETE.json" if failure.status.startswith("incomplete_") else "FAILURE.json"
    payload = {
        "schema_version": "B-G2-failure-receipt-v1",
        "status": failure.status,
        "source_id": source_id,
        "reasons": [str(failure)],
        "input_hashes": observed_inputs,
        "pinned_manifest_emitted": False,
        "complete_marker_emitted": False,
    }
    with _atomic_directory(output) as temp:
        _write_bytes(temp / filename, _canonical_json_bytes(payload))


def _source_plan(plan: dict[str, Any], source_id: str) -> dict[str, Any]:
    return next(source for source in plan["sources"] if source["source_id"] == source_id)


def _write_prepare_success(
    output: Path,
    *,
    source_id: str,
    plan: dict[str, Any],
    plan_raw: bytes,
    schema_raw: bytes,
    receipt: dict[str, Any],
    receipt_raw: bytes,
    bound: list[tuple[str, Path, bytes]],
    rows: list[dict[str, str]],
    conflicts: list[dict[str, str]],
    hla: list[dict[str, str]],
    unmapped: list[dict[str, str]],
) -> None:
    if not rows:
        raise Failure("annotation reason=empty-production-export", status="incomplete_parser")
    annotation = _annotation_tsv_bytes(rows)
    annotation_rows = _parse_annotation_tsv(annotation)
    source_plan = _source_plan(plan, source_id)
    source_reference = (
        f"B-G2|{source_id}|source_freeze|{_sha256(plan_raw)}|{_sha256(schema_raw)}|"
        + ",".join(f"{role}:{_sha256(raw)}" for role, _path, raw in bound)
        + f"|{receipt['reviewed_utc']}"
    )
    manifest = {
        "schema_version": MANIFEST_VERSION,
        "source_id": source_id,
        "source_status": "pinned",
        "canonicalization_authority": source_plan["canonicalization_authority"],
        "identifier_namespace": plan["output_contract"]["identifier_namespace"],
        "source_reference": source_reference,
        "table_path": "annotation.tsv",
        "table_sha256": _sha256(annotation),
    }
    _require_exact_keys(manifest, MANIFEST_KEYS, "manifest")
    manifest_bytes = _canonical_json_bytes(manifest)
    conflicts_bytes = _tsv_bytes(CONFLICT_HEADER, conflicts, sort_fields=("raw_id", "conflict_type", "detail"))
    hla_bytes = _tsv_bytes(HLA_HEADER, hla, sort_fields=("raw_id", "source_symbol", "canonical_symbol"))
    unmapped_bytes = _tsv_bytes(UNMAPPED_HEADER, unmapped, sort_fields=("raw_id", "reason"))
    provenance = {
        "schema_version": "B-G2-provenance-v1",
        "source_id": source_id,
        "evidence_class": "patient_free_identifier_metadata_only",
        "parser_boundary": source_plan["parser_boundary"],
        "raw_identifier_namespace": source_plan["raw_identifier_namespace"],
        "canonicalization_authority": source_plan["canonicalization_authority"],
        "canonicalization_authority_date": plan["canonicalization"]["authority_date"],
        "freeze_receipt_sha256": _sha256(receipt_raw),
        "input_hashes": [{"role": role, "byte_count": len(raw), "sha256": _sha256(raw)} for role, _path, raw in bound],
        "annotation_row_count": len(annotation_rows),
        "mapping_status_counts": dict(sorted(Counter(row["mapping_status"] for row in annotation_rows).items())),
        "conflict_row_count": len(conflicts),
        "hla_caution_row_count": len(hla),
        "unmapped_row_count": len(unmapped),
        "synthetic_fixtures_validate_biology": False,
    }
    provenance_bytes = _canonical_json_bytes(provenance)
    output_payloads = {
        "annotation.tsv": annotation,
        "MANIFEST.json": manifest_bytes,
        "PROVENANCE.json": provenance_bytes,
        "CONFLICTS.tsv": conflicts_bytes,
        "HLA_CAUTION.tsv": hla_bytes,
        "UNMAPPED.tsv": unmapped_bytes,
    }
    checksums = {
        "schema_version": "B-G2-checksums-v1",
        "inputs": {
            "plan_sha256": _sha256(plan_raw),
            "schema_sha256": _sha256(schema_raw),
            "freeze_receipt_sha256": _sha256(receipt_raw),
            "source_inputs": [{"role": role, "byte_count": len(raw), "sha256": _sha256(raw)} for role, _path, raw in bound],
        },
        "outputs": {name: _sha256(data) for name, data in sorted(output_payloads.items())},
    }
    checksums_bytes = _canonical_json_bytes(checksums)
    complete = {
        "schema_version": "B-G2-complete-v1",
        "status": "complete",
        "source_id": source_id,
        "annotation_row_count": len(annotation_rows),
        "annotation_sha256": _sha256(annotation),
        "checksums_sha256": _sha256(checksums_bytes),
        "source_status": "pinned",
        "biological_analysis_released": False,
    }
    with _atomic_directory(output) as temp:
        for name, data in output_payloads.items():
            _write_bytes(temp / name, data)
        _write_bytes(temp / "checksums.json", checksums_bytes)
        _write_bytes(temp / "COMPLETE.json", _canonical_json_bytes(complete))


def run_prepare(args: argparse.Namespace) -> int:
    output: Path = args.output
    if os.path.lexists(output):
        raise Failure("output argument reason=path-already-exists", EXIT_ARGUMENT)
    if args.source_id not in SOURCE_IDS:
        raise Failure("source-id argument reason=unknown-source-id", EXIT_ARGUMENT)
    observed_inputs: list[dict[str, Any]] = []
    try:
        parsed_inputs = _parse_cli_inputs(args.input, args.source_id)
        plan, plan_raw = _load_json(args.plan)
        schema, schema_raw = _load_json(args.schema)
        _validate_plan(plan, schema)
        receipt, receipt_raw = _load_json(args.freeze_receipt, missing_status="incomplete_missing_freeze")
        _validate_receipt(
            receipt,
            source_id=args.source_id,
            plan_sha256=_sha256(plan_raw),
            schema_sha256=_sha256(schema_raw),
        )
        bound, observed_inputs = _read_and_bind_inputs(parsed_inputs, receipt["inputs"], observed_inputs)
        source_plan = _source_plan(plan, args.source_id)
        if args.source_id == "tcga_gencode_v36":
            rows, conflicts, hla, unmapped = _parse_tcga(bound[0][2])
        elif args.source_id == "gse107299_processed":
            rows, conflicts, hla, unmapped = _parse_gse(
                bound[0][2], descriptor=receipt["inputs"][0], plan_source=source_plan
            )
        else:
            rows, conflicts, hla, unmapped = _parse_v18(
                bound, descriptors=receipt["inputs"], plan_source=source_plan
            )
        _write_prepare_success(
            output,
            source_id=args.source_id,
            plan=plan,
            plan_raw=plan_raw,
            schema_raw=schema_raw,
            receipt=receipt,
            receipt_raw=receipt_raw,
            bound=bound,
            rows=rows,
            conflicts=conflicts,
            hla=hla,
            unmapped=unmapped,
        )
        return 0
    except Failure as failure:
        try:
            _write_failure_receipt(
                output,
                source_id=args.source_id,
                failure=failure,
                observed_inputs=observed_inputs,
            )
        except Failure as receipt_failure:
            if receipt_failure.code == EXIT_IO:
                raise receipt_failure from failure
        raise


def run_validate_table(args: argparse.Namespace) -> int:
    if os.path.lexists(args.output):
        raise Failure("output argument reason=path-already-exists", EXIT_ARGUMENT)
    if args.source_id not in SOURCE_IDS:
        raise Failure("source-id argument reason=unknown-source-id", EXIT_ARGUMENT)
    if args.purpose != "synthetic_test":
        raise Failure("purpose reason=synthetic-test-required")
    try:
        raw = args.table.read_bytes()
    except FileNotFoundError as exc:
        raise Failure("table reason=missing-file") from exc
    except OSError as exc:
        raise Failure("I/O failure reading table", EXIT_IO) from exc
    rows = _parse_annotation_tsv(raw)
    payload = {
        "schema_version": "B-G2-synthetic-validation-v1",
        "status": "validated",
        "purpose": "synthetic_test",
        "source_id": args.source_id,
        "table_sha256": _sha256(raw),
        "row_count": len(rows),
        "mapping_status_counts": dict(sorted(Counter(row["mapping_status"] for row in rows).items())),
        "manifest_emitted": False,
        "complete_marker_emitted": False,
        "biological_validation": False,
    }
    with _atomic_directory(args.output) as temp:
        _write_bytes(temp / "VALIDATED.json", _canonical_json_bytes(payload))
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare patient-free Paper B annotation tables.")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--plan", required=True, type=Path)
    prepare.add_argument("--schema", required=True, type=Path)
    prepare.add_argument("--source-id", required=True)
    prepare.add_argument("--freeze-receipt", required=True, type=Path)
    prepare.add_argument("--input", action="append", default=[])
    prepare.add_argument("--output", required=True, type=Path)
    validate = commands.add_parser("validate-table")
    validate.add_argument("--purpose", required=True)
    validate.add_argument("--table", required=True, type=Path)
    validate.add_argument("--source-id", required=True)
    validate.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)
    try:
        if args.command == "prepare":
            return run_prepare(args)
        if args.command == "validate-table":
            return run_validate_table(args)
        raise Failure("usage reason=unknown-command", EXIT_ARGUMENT)
    except Failure as exc:
        print(str(exc), file=sys.stderr)
        return exc.code
    except OSError as exc:
        print(f"I/O failure {exc}", file=sys.stderr)
        return EXIT_IO
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        print(f"unexpected_error={exc}", file=sys.stderr)
        return EXIT_IO


if __name__ == "__main__":
    raise SystemExit(main())
