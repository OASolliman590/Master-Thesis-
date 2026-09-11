"""Load and validate a versioned Paper B workflow config. No shell commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.b_workflow.io import PipelineFailure, json_no_dups, sha256_bytes

SCHEMA_VERSION = "B-workflow-config-v1"
FORBIDDEN_KEYS = {
    "shell",
    "cmd",
    "command",
    "commands",
    "bash",
    "powershell",
    "execute",
    "script",
}
SOURCE_KEYS = {
    "source_id",
    "accession",
    "exact_url",
    "access_tier",
    "expected_sha256",
    "expected_size",
    "compression",
    "role",
    "format",
    "completeness",
    "object_name",
}
OPTIONAL_SOURCE_KEYS = {"expected_decompressed_sha256", "expected_decompressed_size"}
TOP_KEYS = {
    "schema_version",
    "purpose",
    "synthetic",
    "synthetic_label",
    "interpreter",
    "sources",
    "w3",
    "w4",
    "w5",
    "scientific_gates",
}


def _walk_forbidden(obj: Any, prefix: str) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            lowered = str(key).lower()
            if lowered in FORBIDDEN_KEYS:
                raise PipelineFailure(
                    f"config reason=forbidden-key {prefix}{key}; arbitrary shell commands are not allowed",
                    2,
                )
            if isinstance(value, str) and lowered in {"cmdline", "shell_command"}:
                raise PipelineFailure(f"config reason=forbidden-key {prefix}{key}", 2)
            _walk_forbidden(value, f"{prefix}{key}.")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _walk_forbidden(item, f"{prefix}{i}.")


def _require(mapping: dict[str, Any], keys: set[str], label: str) -> None:
    missing = sorted(keys - set(mapping))
    extra = sorted(set(mapping) - keys)
    if missing:
        raise PipelineFailure(f"config reason=missing-field {label}.{missing[0]}", 3)
    if extra:
        raise PipelineFailure(f"config reason=unknown-field {label}.{extra[0]}", 3)


def load_config(path: Path, *, repo_root: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    payload = json_no_dups(raw)
    _walk_forbidden(payload, "")
    if set(payload.keys()) != TOP_KEYS:
        missing = sorted(TOP_KEYS - set(payload.keys()))
        extra = sorted(set(payload.keys()) - TOP_KEYS)
        if missing:
            raise PipelineFailure(f"config reason=missing-field {missing[0]}", 3)
        raise PipelineFailure(f"config reason=unknown-field {extra[0]}", 3)
    if payload["schema_version"] != SCHEMA_VERSION:
        raise PipelineFailure("config reason=bad-schema", 2)
    if payload["purpose"] != "synthetic-test":
        raise PipelineFailure("config reason=unsupported-purpose", 2)
    if payload["synthetic"] is not True:
        raise PipelineFailure("config reason=synthetic-flag-required", 2)
    label = payload["synthetic_label"]
    if not isinstance(label, str) or "SYNTHETIC" not in label.upper():
        raise PipelineFailure("config reason=synthetic-label-required", 3)
    if not isinstance(payload["sources"], list) or not payload["sources"]:
        raise PipelineFailure("config reason=sources-required", 3)
    seen_ids: set[str] = set()
    for source in payload["sources"]:
        if not isinstance(source, dict):
            raise PipelineFailure("config reason=source-not-object", 3)
        allowed = SOURCE_KEYS | OPTIONAL_SOURCE_KEYS
        extra = set(source) - allowed
        missing = SOURCE_KEYS - set(source)
        if missing:
            raise PipelineFailure(f"config reason=missing-source-field {sorted(missing)[0]}", 3)
        if extra:
            raise PipelineFailure(f"config reason=unknown-source-field {sorted(extra)[0]}", 3)
        sid = source["source_id"]
        if sid in seen_ids:
            raise PipelineFailure(f"config reason=duplicate-source-id {sid}", 3)
        seen_ids.add(sid)
        if source["access_tier"] != "synthetic-fixture":
            raise PipelineFailure(f"config reason=non-fixture-source {sid}", 3)
        sha = source["expected_sha256"]
        if not isinstance(sha, str) or len(sha) != 64:
            raise PipelineFailure(f"config reason=bad-source-sha256 {sid}", 3)
        if not isinstance(source["expected_size"], int) or source["expected_size"] < 1:
            raise PipelineFailure(f"config reason=bad-source-size {sid}", 3)
        url = source["exact_url"]
        if not isinstance(url, str) or not (url.startswith("file:") or url.startswith("http://") or url.startswith("https://")):
            raise PipelineFailure(f"config reason=bad-exact-url {sid}", 3)
        if source["compression"] not in {"none", "gzip"}:
            raise PipelineFailure(f"config reason=bad-compression {sid}", 3)
    w3 = payload["w3"]
    if not isinstance(w3, dict) or "specimen_policy" not in w3 or "annotation" not in w3 or "identity" not in w3:
        raise PipelineFailure("config reason=w3-fields", 3)
    policy = w3["specimen_policy"]
    for key in (
        "label",
        "one_evaluation_row_per_patient",
        "ambiguous_focus",
        "unresolved_identifier",
        "technical_replicate_collapse",
        "forbid_wgs_agreement_as_purity",
        "development_cohort",
        "external_cohort",
        "rule_version",
    ):
        if key not in policy:
            raise PipelineFailure(f"config reason=missing-field w3.specimen_policy.{key}", 3)
    if policy["label"] != "synthetic-fixture-only":
        raise PipelineFailure("config reason=w3-policy-not-fixture", 3)
    if policy["forbid_wgs_agreement_as_purity"] is not True:
        raise PipelineFailure("config reason=wgs-quarantine-required", 3)
    w4 = payload["w4"]
    if not isinstance(w4, dict) or w4.get("policy_label") != "synthetic-fixture-only":
        raise PipelineFailure("config reason=w4-policy-not-fixture", 3)
    w5 = payload["w5"]
    if not isinstance(w5, dict) or w5.get("policy_label") != "synthetic-fixture-only":
        raise PipelineFailure("config reason=w5-policy-not-fixture", 3)
    for key in (
        "min_development_n",
        "never_use_w4_full_training_state_for_nested_cv",
        "continuous_baseline_columns",
        "categorical_baseline_groups",
        "extended_columns",
        "gleason_encoding",
    ):
        if key not in w5:
            raise PipelineFailure(f"config reason=missing-field w5.{key}", 3)
    if w5["never_use_w4_full_training_state_for_nested_cv"] is not True:
        raise PipelineFailure("config reason=w5-must-forbid-global-nested-cv-state", 3)
    if not isinstance(w5["min_development_n"], int) or w5["min_development_n"] < 7:
        raise PipelineFailure("config reason=w5-min-development-n-below-bp1", 3)
    payload["_config_sha256"] = sha256_bytes(raw)
    payload["_config_path"] = str(path.resolve())
    payload["_repo_root"] = str(repo_root.resolve())
    return payload
