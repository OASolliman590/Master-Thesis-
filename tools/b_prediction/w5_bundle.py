"""Dedicated loader for the W5 frozen fold-local bundle.

This is intentionally separate from the released B-P1 `_load_bundle`, which
rejects undeclared payloads. Do not weaken that exact-payload check.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.b_features.provider import STATE_SCHEMA, FeatureState
from tools.b_workflow.io import (
    PipelineFailure,
    canonical_json_bytes,
    json_no_dups,
    sha256_bytes,
    sha256_file,
)

W5_BUNDLE_COMPLETE_SCHEMA = "B-W5-bundle-complete-1"
W5_BUNDLE_CHECKSUMS_SCHEMA = "B-W5-bundle-checksums-1"
W5_BUNDLE_FILES = (
    "bundle_manifest.json",
    "baseline_model.json",
    "extended_model.json",
    "development_metrics.json",
    "contract.json",
    "fold_assignments.tsv",
    "oof_predictions.tsv",
    "tuning_results.tsv",
    "final_feature_state.json",
    "checksums.json",
    "COMPLETE.json",
)
W5_CHECKSUMMED_FILES = tuple(name for name in W5_BUNDLE_FILES if name not in {"checksums.json", "COMPLETE.json"})


def _fail(message: str, code: int = 3) -> None:
    raise PipelineFailure(f"stage=W6 {message}", code, "W6")


def load_feature_state(path: Path) -> FeatureState:
    payload = json_no_dups(path.read_bytes())
    if payload.get("schema_version") != STATE_SCHEMA:
        _fail("reason=unsupported-feature-state-schema")
    state = FeatureState(payload)
    recorded = payload.get("state_sha256")
    if not isinstance(recorded, str) or recorded != state.sha256:
        _fail("reason=feature-state-hash-mismatch")
    return state


def load_w5_bundle(bundle_dir: Path, *, expected_code_identity: str | None = None) -> dict[str, Any]:
    if not bundle_dir.is_dir():
        _fail(f"reason=missing-w5-bundle {bundle_dir}")
    present = {path.name for path in bundle_dir.iterdir() if path.is_file()}
    expected = set(W5_BUNDLE_FILES)
    missing = sorted(expected - present)
    extra = sorted(present - expected)
    if missing:
        _fail(f"reason=bundle-missing-payload {missing[0]}")
    if extra:
        _fail(f"reason=bundle-undeclared-payload {extra[0]}")

    complete = json_no_dups((bundle_dir / "COMPLETE.json").read_bytes())
    if complete.get("schema_version") != W5_BUNDLE_COMPLETE_SCHEMA or complete.get("status") != "complete":
        _fail("reason=bundle-incomplete")
    checksums_path = bundle_dir / "checksums.json"
    checksums_sha = sha256_file(checksums_path)
    if complete.get("bundle_hash") != checksums_sha:
        _fail("reason=bundle-checksum-mismatch")
    checksums = json_no_dups(checksums_path.read_bytes())
    if checksums.get("schema_version") != W5_BUNDLE_CHECKSUMS_SCHEMA:
        _fail("reason=bundle-checksums-schema")
    files = checksums.get("files")
    if not isinstance(files, dict) or set(files.keys()) != set(W5_CHECKSUMMED_FILES):
        _fail("reason=bundle-checksum-manifest-mismatch")
    for name, expected_sha in files.items():
        actual = sha256_file(bundle_dir / name)
        if actual != expected_sha:
            _fail(f"reason=bundle-payload-hash-mismatch {name}")

    manifest = json_no_dups((bundle_dir / "bundle_manifest.json").read_bytes())
    baseline = json_no_dups((bundle_dir / "baseline_model.json").read_bytes())
    extended = json_no_dups((bundle_dir / "extended_model.json").read_bytes())
    contract_payload = json_no_dups((bundle_dir / "contract.json").read_bytes())
    state = load_feature_state(bundle_dir / "final_feature_state.json")
    linked = {
        complete.get("final_feature_state_sha256"),
        manifest.get("final_feature_state_sha256"),
        checksums.get("final_feature_state_sha256"),
        baseline.get("feature_state_sha256"),
        extended.get("feature_state_sha256"),
        state.sha256,
    }
    if len(linked) != 1 or None in linked:
        _fail("reason=model-state-link-mismatch")

    contract_sha = sha256_file(bundle_dir / "contract.json")
    embedded_contract = manifest.get("contract")
    if not isinstance(embedded_contract, dict):
        _fail("reason=bundle-missing-contract")
    contract_links = {
        contract_sha,
        manifest.get("contract_sha256"),
        checksums.get("contract_sha256"),
        sha256_bytes(canonical_json_bytes(embedded_contract)),
    }
    if len(contract_links) != 1 or None in contract_links or embedded_contract != contract_payload:
        _fail("reason=bundle-contract-link-mismatch")

    code_links = {
        manifest.get("code_identity_sha256"),
        checksums.get("code_identity_sha256"),
        state.payload.get("code_identity_sha256"),
    }
    if len(code_links) != 1 or None in code_links:
        _fail("reason=bundle-code-identity-link-mismatch")
    if expected_code_identity is not None:
        if code_links != {expected_code_identity}:
            _fail("reason=bundle-code-identity-mismatch")
    development_hashes = manifest.get("development_patient_id_hashes")
    if not isinstance(development_hashes, list) or not development_hashes:
        _fail("reason=bundle-missing-development-patient-hashes")
    training_ids = state.payload.get("training_patient_ids")
    if not isinstance(training_ids, list) or not training_ids or any(not isinstance(pid, str) for pid in training_ids):
        _fail("reason=feature-state-missing-training-patients")
    expected_hashes = [sha256_bytes(pid.encode("utf-8")) for pid in training_ids]
    if development_hashes != expected_hashes or len(set(development_hashes)) != len(development_hashes):
        _fail("reason=development-state-patient-link-mismatch")
    if manifest.get("development_patient_count") != len(training_ids):
        _fail("reason=development-patient-count-mismatch")
    expected_state_set_hash = sha256_bytes(canonical_json_bytes(training_ids))
    if state.payload.get("training_patient_set_hash") != expected_state_set_hash:
        _fail("reason=feature-state-training-set-hash-mismatch")
    expected_manifest_set_hash = sha256_bytes(canonical_json_bytes(development_hashes))
    if manifest.get("development_patient_set_hash") != expected_manifest_set_hash:
        _fail("reason=development-patient-set-hash-mismatch")
    return {
        "bundle_dir": bundle_dir,
        "manifest": manifest,
        "checksums": checksums,
        "complete": complete,
        "baseline_model": baseline,
        "extended_model": extended,
        "feature_state": state,
        "contract": contract_payload,
        "contract_sha256": contract_sha,
        "bundle_sha256": complete["bundle_hash"],
        "final_feature_state_sha256": state.sha256,
        "development_patient_id_hashes": list(development_hashes),
    }


def validate_w5_stage(
    w5_dir: Path,
    bundle: dict[str, Any],
    *,
    expected_code_identity: str,
) -> dict[str, Any]:
    """Validate the enclosing W5 publication and its links to the bundle."""
    complete_path = w5_dir / "COMPLETE.json"
    checksums_path = w5_dir / "checksums.json"
    manifest_path = w5_dir / "manifest.json"
    for path in (complete_path, checksums_path, manifest_path):
        if not path.is_file():
            _fail(f"reason=w5-stage-missing-payload {path.name}")
    complete = json_no_dups(complete_path.read_bytes())
    checksums = json_no_dups(checksums_path.read_bytes())
    manifest = json_no_dups(manifest_path.read_bytes())
    if complete.get("stage") != "W5" or complete.get("status") != "complete":
        _fail("reason=w5-not-complete")
    if complete.get("checksums_sha256") != sha256_file(checksums_path):
        _fail("reason=w5-stage-checksums-hash-mismatch")
    if complete.get("manifest_sha256") != sha256_file(manifest_path):
        _fail("reason=w5-stage-manifest-hash-mismatch")
    artifacts = checksums.get("artifact_hashes")
    if not isinstance(artifacts, dict) or not artifacts:
        _fail("reason=w5-stage-missing-artifact-index")
    for rel, expected_sha in artifacts.items():
        path = w5_dir / rel
        if not isinstance(expected_sha, str) or not path.is_file() or sha256_file(path) != expected_sha:
            _fail(f"reason=w5-stage-artifact-hash-mismatch {rel}")
    code_links = {
        expected_code_identity,
        complete.get("code_identity_sha256"),
        checksums.get("code_identity_sha256"),
        manifest.get("code_identity_sha256"),
        bundle["manifest"].get("code_identity_sha256"),
        bundle["checksums"].get("code_identity_sha256"),
        bundle["feature_state"].payload.get("code_identity_sha256"),
    }
    if len(code_links) != 1 or None in code_links:
        _fail("reason=w5-stage-code-identity-mismatch")
    if {
        complete.get("bundle_sha256"),
        checksums.get("bundle_sha256"),
        manifest.get("bundle_sha256"),
    } != {bundle["bundle_sha256"]}:
        _fail("reason=w5-stage-bundle-hash-mismatch")
    if {
        complete.get("final_feature_state_sha256"),
        checksums.get("final_feature_state_sha256"),
        manifest.get("final_feature_state_sha256"),
    } != {bundle["final_feature_state_sha256"]}:
        _fail("reason=w5-stage-state-hash-mismatch")
    if bundle["feature_state"].payload.get("parent_hashes") != complete.get("parent_hashes"):
        _fail("reason=w5-stage-parent-link-mismatch")
    return complete
