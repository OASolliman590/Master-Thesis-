"""W6 frozen external evaluation of a W5 fold-local bundle. No refit."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from tools.b_features.provider import FoldFeatureProvider
from tools.b_prediction.adapter import encode_eligible_rows, ordered_feature_columns
from tools.b_prediction.w5_bundle import load_w5_bundle, validate_w5_stage
from tools.b_prediction.__main__ import (
    PatientTable,
    _bootstrap_delta,
    _evaluate_from_models,
    _load_contract_from_payload,
    _sha256,
)
from tools.b_workflow.io import (
    PipelineFailure,
    atomic_write_json,
    atomic_write_tsv,
    canonical_json_bytes,
    json_no_dups,
    publish_directory,
    read_tsv,
    remove_tree,
    sha256_bytes,
    sha256_file,
    utc_stamp,
)

LOCK_SCHEMA = "B-W6-evaluation-lock-1"
LOCK_FIELDS = (
    "schema_version",
    "status",
    "synthetic",
    "synthetic_label",
    "bundle_sha256",
    "final_feature_state_sha256",
    "external_sha256",
    "contract_sha256",
    "eligibility_hash",
    "external_population_contract_hash",
    "precision_contract_id",
    "decision_receipt",
    "reviewer_receipt",
)


def _fail(message: str, code: int = 3) -> None:
    raise PipelineFailure(f"stage=W6 {message}", code, "W6")


def _hex_hash(value: str, field: str) -> str:
    text = str(value)
    if len(text) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in text):
        _fail(f"reason=bad-lock-hash {field}")
    return text.lower()


def build_external_input_hash(
    w3_dir: Path,
    external_ids: list[str],
) -> str:
    payload = {
        "w3_checksums_sha256": sha256_file(w3_dir / "checksums.json"),
        "expression_sha256": sha256_file(w3_dir / "expression.tsv"),
        "methylation_sha256": sha256_file(w3_dir / "methylation.tsv"),
        "covariates_sha256": sha256_file(w3_dir / "covariates.tsv"),
        "specimens_sha256": sha256_file(w3_dir / "specimens.tsv"),
        "external_patient_ids": list(external_ids),
    }
    return sha256_bytes(canonical_json_bytes(payload))


def build_synthetic_lock(
    template: dict[str, Any],
    *,
    bundle_sha256: str,
    final_feature_state_sha256: str,
    external_sha256: str,
    contract_sha256: str,
    eligibility_hash: str,
    population_hash: str,
) -> dict[str, Any]:
    lock = {
        "schema_version": LOCK_SCHEMA,
        "status": "synthetic-only",
        "synthetic": True,
        "synthetic_label": template["synthetic_label"],
        "bundle_sha256": bundle_sha256,
        "final_feature_state_sha256": final_feature_state_sha256,
        "external_sha256": external_sha256,
        "contract_sha256": contract_sha256,
        "eligibility_hash": eligibility_hash,
        "external_population_contract_hash": population_hash,
        "precision_contract_id": template["precision_contract_id"],
        "decision_receipt": template["decision_receipt"],
        "reviewer_receipt": template["reviewer_receipt"],
    }
    if set(lock.keys()) != set(LOCK_FIELDS):
        _fail("reason=lock-field-mismatch")
    if "SYNTHETIC" not in str(lock["synthetic_label"]).upper():
        _fail("reason=synthetic-lock-label-required")
    for field in (
        "decision_receipt",
        "reviewer_receipt",
        "precision_contract_id",
    ):
        if "synthetic" not in str(lock[field]).lower():
            _fail(f"reason=synthetic-lock-field {field}")
    return lock


def validate_lock(lock: dict[str, Any], expected: dict[str, str]) -> None:
    if set(lock.keys()) != set(LOCK_FIELDS):
        missing = sorted(set(LOCK_FIELDS) - set(lock.keys()))
        extra = sorted(set(lock.keys()) - set(LOCK_FIELDS))
        if missing:
            _fail(f"reason=lock-missing-field {missing[0]}")
        _fail(f"reason=lock-unknown-field {extra[0]}")
    if lock.get("schema_version") != LOCK_SCHEMA:
        _fail("reason=lock-schema")
    if lock.get("status") != "synthetic-only" or lock.get("synthetic") is not True:
        _fail("reason=lock-not-synthetic-only")
    for field in (
        "bundle_sha256",
        "final_feature_state_sha256",
        "external_sha256",
        "contract_sha256",
        "eligibility_hash",
        "external_population_contract_hash",
    ):
        _hex_hash(lock.get(field, ""), field)
    for key, value in expected.items():
        if lock.get(key) != value:
            _fail(f"reason=lock-hash-mismatch {key}")


def _external_ids(provider: FoldFeatureProvider, external_cohort: str) -> list[str]:
    ids = [
        pid
        for pid, cov in provider.covariates.items()
        if cov.get("cohort") == external_cohort
    ]
    if not ids:
        _fail("reason=no-external-patients")
    if len(ids) != len(set(ids)):
        _fail("reason=duplicate-external-patient")
    return sorted(ids, key=lambda item: item.encode("utf-8"))


def _to_patient_table(
    ids: list[str],
    y: np.ndarray,
    continuous: np.ndarray,
    dummy: np.ndarray,
    extended: np.ndarray,
    w5: dict[str, Any],
) -> PatientTable:
    cont_cols, cat_cols, ext_cols = ordered_feature_columns(w5)
    return PatientTable(
        raw_bytes=b"",
        source_sha256="0" * 64,
        patient_ids=ids,
        patient_id_hashes=[_sha256(pid.encode("utf-8")) for pid in ids],
        y=np.ascontiguousarray(y, dtype=np.float64),
        continuous_matrix=np.ascontiguousarray(continuous, dtype=np.float64),
        categorical_matrix=np.ascontiguousarray(dummy, dtype=np.float64),
        extended_matrix=np.ascontiguousarray(extended, dtype=np.float64),
        continuous_columns=list(cont_cols),
        categorical_columns=list(cat_cols),
        extended_columns=list(ext_cols),
    )


def run_fold_evaluate(
    config: dict[str, Any],
    *,
    repo_root: Path,
    w3_dir: Path,
    w5_dir: Path,
    stage_dir: Path,
    parent_hashes: dict[str, str],
    code_identity: str,
    interpreter: str,
) -> dict[str, Any]:
    w6 = config.get("w6")
    if not isinstance(w6, dict) or w6.get("policy_label") != "synthetic-fixture-only":
        _fail("reason=non-fixture-policy-rejected")
    template = w6.get("evaluation_lock")
    if not isinstance(template, dict):
        _fail("reason=missing-evaluation-lock-template")
    bundle = load_w5_bundle(
        w5_dir / "bundle",
        expected_code_identity=code_identity,
    )
    validate_w5_stage(w5_dir, bundle, expected_code_identity=code_identity)

    policy = config["w4"]
    external_cohort = config["w3"]["specimen_policy"]["external_cohort"]
    cov_header, cov_rows = read_tsv(w3_dir / "covariates.tsv")
    cov_idx = {name: i for i, name in enumerate(cov_header)}
    covariate_external_ids = [
        row[cov_idx["patient_id"]]
        for row in cov_rows
        if row[cov_idx["cohort"]] == external_cohort
    ]
    if len(covariate_external_ids) != len(set(covariate_external_ids)):
        _fail("reason=duplicate-external-patient")
    overlap = {_sha256(pid.encode("utf-8")) for pid in covariate_external_ids} & set(
        bundle["development_patient_id_hashes"]
    )
    if overlap:
        _fail("reason=tcga-external-patient-overlap")
    probe_map_path = repo_root / config["w3"]["annotation"]["probe_map_path"]
    provider = FoldFeatureProvider.from_cohort(
        w3_dir,
        policy,
        probe_map_path=probe_map_path,
        parent_hashes=parent_hashes,
        code_identity_sha256=code_identity,
    )
    external_ids = _external_ids(provider, external_cohort)

    external_sha = build_external_input_hash(w3_dir, external_ids)
    eligibility_hash = sha256_bytes(canonical_json_bytes(policy["eligibility"]))
    population_hash = sha256_bytes(canonical_json_bytes(external_ids))
    lock = build_synthetic_lock(
        template,
        bundle_sha256=bundle["bundle_sha256"],
        final_feature_state_sha256=bundle["final_feature_state_sha256"],
        external_sha256=external_sha,
        contract_sha256=bundle["contract_sha256"],
        eligibility_hash=eligibility_hash,
        population_hash=population_hash,
    )
    validate_lock(
        lock,
        {
            "bundle_sha256": bundle["bundle_sha256"],
            "final_feature_state_sha256": bundle["final_feature_state_sha256"],
            "external_sha256": external_sha,
            "contract_sha256": bundle["contract_sha256"],
            "eligibility_hash": eligibility_hash,
            "external_population_contract_hash": population_hash,
        },
    )

    # Publish the fixture-only lock before endpoint transformation or metrics.
    # A failed evaluation deliberately leaves no COMPLETE record.
    work = stage_dir.parent / f"{stage_dir.name}.work"
    if work.exists():
        remove_tree(work)
    work.mkdir(parents=True)
    atomic_write_json(work / "evaluation_lock.json", lock)

    rows = provider.transform(external_ids, bundle["feature_state"], refit=False)
    exclusions = [
        [
            row["patient_id"],
            row["exclusion_reason"],
            row["feature_state_sha256"],
            True,
        ]
        for row in rows
        if not row["eligible"]
    ]
    eligible_rows = [row for row in rows if row["eligible"]]
    if not eligible_rows:
        _fail("reason=no-eligible-external-patients")
    program = list(policy["program_p"])
    ids, y, cont, dummy, ext = encode_eligible_rows(
        eligible_rows,
        covariates=provider.covariates,
        w5=config["w5"],
        program=program,
    )
    if len(ids) != len(set(ids)):
        _fail("reason=duplicate-external-patient")
    table = _to_patient_table(ids, y, cont, dummy, ext, config["w5"])
    contract = _load_contract_from_payload(bundle["contract"], raw_sha256=bundle["contract_sha256"])
    baseline_pred, baseline_trace = _evaluate_from_models(
        table, contract, bundle["baseline_model"], include_extended=False
    )
    extended_pred, extended_trace = _evaluate_from_models(
        table, contract, bundle["extended_model"], include_extended=True
    )
    if baseline_pred.shape != extended_pred.shape or baseline_pred.shape[0] != len(ids):
        _fail("reason=paired-prediction-length-mismatch")

    metrics = _bootstrap_delta(table.y, baseline_pred, extended_pred, contract.bootstrap)
    atomic_write_tsv(
        work / "predictions.tsv",
        ["patient_id", "Y", "f0", "f1", "sse_baseline", "sse_extended", "synthetic"],
        [
            [
                pid,
                float(y_i),
                float(f0),
                float(f1),
                float((y_i - f0) ** 2),
                float((y_i - f1) ** 2),
                True,
            ]
            for pid, y_i, f0, f1 in zip(ids, table.y, baseline_pred, extended_pred)
        ],
    )
    atomic_write_tsv(
        work / "exclusions.tsv",
        ["patient_id", "exclusion_reason", "feature_state_sha256", "synthetic"],
        exclusions,
    )
    evaluation = {
        "schema_version": "B-W6-evaluation-1",
        "purpose": "synthetic-test",
        "synthetic": True,
        "synthetic_label": config["synthetic_label"],
        "n": int(len(ids)),
        "n_excluded": int(len(exclusions)),
        "n_external_candidates": int(len(external_ids)),
        "bundle_sha256": bundle["bundle_sha256"],
        "final_feature_state_sha256": bundle["final_feature_state_sha256"],
        "external_sha256": external_sha,
        "contract_sha256": bundle["contract_sha256"],
        "lock_sha256": sha256_file(work / "evaluation_lock.json"),
        "metrics": {
            "sse_baseline": metrics["sse_baseline"],
            "sse_extended": metrics["sse_extended"],
            "sst": metrics["sst"],
            "r2_baseline": metrics["r2_baseline"],
            "r2_extended": metrics["r2_extended"],
            "delta_r2": metrics["delta_r2"],
            "status": metrics["status"],
            "reason": metrics["reason"],
            "bootstrap": metrics["bootstrap"],
        },
        "paired_identical_patient_set": True,
        "used_external_fit": False,
        "traces": {
            "baseline": baseline_trace,
            "extended": extended_trace,
        },
    }
    atomic_write_json(work / "evaluation.json", evaluation)
    payload_files = {
        "evaluation_lock.json": work / "evaluation_lock.json",
        "predictions.tsv": work / "predictions.tsv",
        "exclusions.tsv": work / "exclusions.tsv",
        "evaluation.json": work / "evaluation.json",
    }
    artifact_hashes = {rel: sha256_file(path) for rel, path in payload_files.items()}
    scientific = {
        "schema_version": "B-W6-manifest-v1",
        "stage": "W6",
        "synthetic": True,
        "synthetic_label": config["synthetic_label"],
        "parent_hashes": parent_hashes,
        "code_identity_sha256": code_identity,
        "interpreter": interpreter,
        "bundle_sha256": bundle["bundle_sha256"],
        "final_feature_state_sha256": bundle["final_feature_state_sha256"],
        "external_sha256": external_sha,
        "lock_sha256": artifact_hashes["evaluation_lock.json"],
        "n_evaluated": int(len(ids)),
        "n_excluded": int(len(exclusions)),
        "artifact_hashes": artifact_hashes,
        "policy_label": w6["policy_label"],
        "pipeline_complete": False,
    }
    atomic_write_json(work / "checksums.json", scientific)
    artifact_hashes["checksums.json"] = sha256_file(work / "checksums.json")
    manifest = dict(scientific)
    manifest["created_utc"] = utc_stamp()
    manifest["artifact_hashes"] = artifact_hashes
    atomic_write_json(work / "manifest.json", manifest)
    complete = {
        "stage": "W6",
        "status": "complete",
        "synthetic": True,
        "checksums_sha256": artifact_hashes["checksums.json"],
        "manifest_sha256": sha256_file(work / "manifest.json"),
        "parent_hashes": parent_hashes,
        "code_identity_sha256": code_identity,
        "bundle_sha256": bundle["bundle_sha256"],
        "final_feature_state_sha256": bundle["final_feature_state_sha256"],
        "pipeline_complete": False,
    }
    atomic_write_json(work / "COMPLETE.json", complete)
    publish_directory(work, stage_dir)
    return json_no_dups((stage_dir / "manifest.json").read_bytes())
