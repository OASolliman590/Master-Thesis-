"""Real-source audit/preparation. No scores, models, or silent synthetic substitution."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlparse

from tools.b_acquire.acquire import CREDENTIAL_QUERY_KEYS
from tools.b_workflow.io import (
    PipelineFailure,
    atomic_write_json,
    json_no_dups,
    sha256_file,
    utc_stamp,
)

AUDIT_SCHEMA = "B-source-audit-v1"
CONTROLLED_TOKENS = ("dbgap", "controlled", "restricted", "authorized", "gdc-controlled")
UNRESOLVED_POLICIES = [
    "P/U/Q membership and promoter rule are unfrozen",
    "specimen/replicate/focus policy is unfrozen",
    "purity/covariate comparability is unfrozen",
    "CPC WGS_BASED_PURITY_ESTIMATION remains quarantined and is not purity",
]


def _fail(message: str, code: int = 3) -> None:
    raise PipelineFailure(f"stage=source-audit {message}", code, "source-audit")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _credential_url(url: str | None) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.username or parsed.password:
        return True
    for raw_key, _value in parse_qsl(parsed.query, keep_blank_values=True):
        key = raw_key.lower()
        if key in CREDENTIAL_QUERY_KEYS or "token" in key or "secret" in key or "password" in key:
            return True
    return False


def _access_tier(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in CONTROLLED_TOKENS):
        return "controlled-blocked"
    if "public" in lowered:
        return "public"
    return "unspecified"


def _check_local_file(repo_root: Path, rel: str, expected_sha: str | None, expected_size: int | None) -> dict[str, Any]:
    path = repo_root / rel
    record: dict[str, Any] = {
        "path": rel.replace("\\", "/"),
        "exists": path.is_file(),
        "actual_bytes": None,
        "actual_sha256": None,
        "hash_match": None,
        "size_match": None,
        "status": "missing",
    }
    if not path.is_file():
        record["status"] = "missing"
        return record
    actual_size = path.stat().st_size
    actual_sha = sha256_file(path)
    record["actual_bytes"] = actual_size
    record["actual_sha256"] = actual_sha
    if expected_size is not None:
        record["size_match"] = actual_size == expected_size
    if expected_sha:
        record["hash_match"] = actual_sha.lower() == expected_sha.lower()
    if record.get("hash_match") is False or record.get("size_match") is False:
        record["status"] = "mismatch"
    else:
        record["status"] = "confirmed-local"
    return record


def audit_sources(
    *,
    repo_root: Path,
    manifest_path: Path,
    output_path: Path,
    network: str = "none",
) -> dict[str, Any]:
    if network != "none":
        _fail("reason=network-not-enabled-for-this-audit")
    raw = manifest_path.read_bytes()
    manifest = json_no_dups(raw)
    confirmed: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    mismatches: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    credential_rejected: list[dict[str, Any]] = []
    proposed_not_executed: list[dict[str, Any]] = []
    unpublished_diagnostics: list[dict[str, Any]] = []

    for obj in manifest.get("retrieved_objects", []):
        rel = obj.get("source_file")
        url = obj.get("exact_url")
        access = _access_tier(str(obj.get("access") or ""))
        entry = {
            "source_file": rel,
            "accession_or_url_host": urlparse(url).hostname if isinstance(url, str) else None,
            "access_tier": access,
            "completeness": obj.get("completeness"),
            "manifest_bytes": obj.get("byte_count"),
            "manifest_sha256": obj.get("sha256"),
            "compression": "gzip" if str(rel).endswith((".gz", ".gzpart")) else "none",
            "expected_decompressed_size": obj.get("expected_decompressed_size"),
            "credential_url": False,
            "synthetic_substitute": False,
        }
        if isinstance(url, str) and _credential_url(url):
            entry["credential_url"] = True
            entry["status"] = "credential-bearing-url-rejected"
            credential_rejected.append(entry)
            continue
        if access == "controlled-blocked":
            entry["status"] = "controlled-blocked-without-access"
            blocked.append(entry)
            continue
        if not rel:
            entry["status"] = "missing"
            missing.append(entry)
            continue
        checked = _check_local_file(repo_root, rel, obj.get("sha256"), obj.get("byte_count"))
        entry.update(checked)
        if str(rel).endswith(".gzpart") or "prefix" in str(rel).lower():
            unpublished_diagnostics.append(
                {
                    "path": rel,
                    "note": "Retained prefix/partial object is unpublished diagnostic bytes, not a full cohort matrix.",
                    "status": checked["status"],
                }
            )
        if checked["status"] == "confirmed-local":
            confirmed.append(entry)
        elif checked["status"] == "missing":
            missing.append(entry)
        else:
            mismatches.append(entry)
        if isinstance(url, str) and url.startswith("http"):
            proposed_not_executed.append(
                {
                    "kind": "http-metadata-or-object",
                    "host": urlparse(url).hostname,
                    "reason": "local file audit only; live network not executed",
                    "source_file": rel,
                }
            )

    coverage = manifest.get("coverage") or {}
    full_expr = coverage.get("full_external_expression_audit") or {}
    if full_expr.get("matrix_retained") is False:
        missing.append(
            {
                "source_file": None,
                "status": "missing",
                "note": "GSE107299 full expression matrix was audited then not retained",
                "manifest_sha256": full_expr.get("complete_object_sha256"),
                "manifest_bytes": full_expr.get("complete_object_bytes"),
                "synthetic_substitute": False,
            }
        )

    for snap in manifest.get("local_evidence_snapshots", []):
        rel = snap.get("path")
        if not rel:
            continue
        checked = _check_local_file(repo_root, rel, snap.get("sha256"), snap.get("bytes"))
        entry = {"role": snap.get("role"), **checked, "synthetic_substitute": False}
        if checked["status"] == "confirmed-local":
            confirmed.append(entry)
        elif checked["status"] == "missing":
            missing.append(entry)
        else:
            mismatches.append(entry)

    payload = {
        "schema_version": AUDIT_SCHEMA,
        "synthetic": False,
        "computes_scores": False,
        "fits_models": False,
        "network_mode": network,
        "manifest_path": str(manifest_path.as_posix()),
        "manifest_sha256": _sha256_bytes(raw),
        "created_utc": utc_stamp(),
        "confirmed_source_evidence": confirmed,
        "missing_files": missing,
        "mismatches": mismatches,
        "controlled_blocked": blocked,
        "credential_bearing_urls_rejected": credential_rejected,
        "proposed_checks_not_executed": proposed_not_executed,
        "unpublished_diagnostic_bytes": unpublished_diagnostics,
        "unresolved_specimen_annotation_purity_policies": UNRESOLVED_POLICIES,
        "unimplemented_processing": [
            "full-cohort acquisition",
            "real feature construction",
            "real nested development",
            "external evaluation",
        ],
        "counts": {
            "confirmed": len(confirmed),
            "missing": len(missing),
            "mismatch": len(mismatches),
            "controlled_blocked": len(blocked),
            "credential_rejected": len(credential_rejected),
        },
        "note": (
            "Local evidence only. Missing sources are reported as missing and are not replaced "
            "with synthetic fixtures. This audit does not authorize biological analysis."
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(output_path, payload)
    return payload
