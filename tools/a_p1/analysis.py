"""Complete Python interface for the fixed-score A-P1 sensitivity."""

from __future__ import annotations

import csv
import io
import json
from hashlib import sha256
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path

from tools.a_meta.r_manifest import run_r_sanitised
from tools.a_meta.provenance import canonical_sha256

from .endpoints import (
    _summarize_records,
    SCORE_MAPPING_VERSION,
)
from .provenance import (
    assert_allowed_input_path,
    load_input_tsv,
    preflight_input_manifest,
    validate_records_provenance,
)
from .synthesis import synthesize_studies


_ROOT = Path(__file__).resolve().parents[2]
_R_SCRIPT = _ROOT / "r/R/a_p1.R"
_EXPECTED_R_OUTPUTS = [
    "bootstrap_assignments.tsv",
    "bootstrap_replicates.tsv",
    "intervals.tsv",
    "random_receipts.tsv",
    "second_check_comparison.tsv",
]
_R_INPUT_FIELDS = ("study_id", "patient_key", "category", "score", "score_method")


def analyze_records(
    records: Sequence[Mapping[str, object]],
    provenance: Mapping[str, object],
    output_dir: Path | str,
    *,
    synthesis_contract: Mapping[str, object] | None = None,
    learned_score_records: Sequence[Mapping[str, object]] | None = None,
    learned_score_provenance: Mapping[str, object] | None = None,
    allow_outcomes: bool = False,
) -> dict:
    """Run point estimates and R-backed resampling from explicit input rows."""
    manifest = validate_records_provenance(records, provenance, allow_outcomes=allow_outcomes)
    summary, accepted_by_study, endpoint_eligible_by_study = _summarize_records(records)
    classification = str(manifest["data_classification"])
    summary["data_classification"] = classification
    summary["input_payload_sha256"] = manifest["payload_sha256"]
    summary["measurement_contract"] = dict(manifest["measurement_contract"])
    summary["synthesis"] = synthesize_studies(
        summary["studies"], synthesis_contract, data_classification=classification
    )

    endpoint_patients = [
        {"study_id": study, **patient}
        for study in sorted(endpoint_eligible_by_study, key=_utf8)
        for patient in endpoint_eligible_by_study[study]
    ]
    learned_rows: list[dict] | None = None
    if learned_score_records is not None or learned_score_provenance is not None:
        if learned_score_records is None or learned_score_provenance is None:
            raise ValueError("Learned-score rows and their provenance must be supplied together")
        from .learned import learned_score_analysis

        learned_summary, learned_rows = learned_score_analysis(
            learned_score_records,
            learned_score_provenance,
            endpoint_patients,
            data_classification=classification,
            allow_outcomes=allow_outcomes,
        )
        if set(learned_summary["studies"]) == set(summary["studies"]):
            learned_summary["synthesis"] = synthesize_studies(
                learned_summary["studies"], synthesis_contract,
                data_classification=classification,
            )
        else:
            learned_summary["synthesis"] = {
                "status": "unavailable_learned_collection_roster_mismatch",
                "reason": "The learned-score eligible studies do not match the declared A-P1 collection roster.",
                "cross_study_pooled_auc": None,
                "interval": None,
            }
        summary["learned_score_secondary"] = learned_summary

    r_rows = [
        {
            "study_id": study,
            "patient_key": str(patient["patient_key"]),
            "category": str(patient["category"]),
            "score": float(patient["score"]),
            "score_method": "CYT",
        }
        for study in sorted(accepted_by_study, key=_utf8)
        for patient in accepted_by_study[study]
    ]
    if learned_rows:
        r_rows.extend(learned_rows)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    if r_rows:
        r_result = _run_r(r_rows, out, summary)
        _attach_bootstrap_results(summary, r_result.outputs, r_result.manifest)
        summary["r_provenance"] = r_result.manifest
    else:
        summary["r_provenance"] = None
        for study in summary["studies"].values():
            study["bootstrap"] = _nonestimable_bootstrap(study)
        learned = summary.get("learned_score_secondary")
        if isinstance(learned, dict) and isinstance(learned.get("studies"), dict):
            for study in learned["studies"].values():
                study["bootstrap"] = _nonestimable_bootstrap(study)
    learned = summary.get("learned_score_secondary")
    if isinstance(learned, dict) and isinstance(learned.get("studies"), dict):
        learned["uncertainty_status"] = _study_uncertainty_status(learned["studies"])
    summary["synthetic_scope"] = (
        "invented software fixture; no biological claim"
        if classification == "synthetic" else None
    )
    summary["panel_extension"] = {
        "status": "pending_a_p1_scoring_authorization",
        "reason": (
            "The signed A-P1 scope repeats endpoint sensitivity for locked panels, but no "
            "A-P1-specific panel score definitions, fixed directions or qualification rules "
            "have been released. A-BIO custom means are not authorized for A-P1."
        ),
        "decision_note": "docs/decisions/A_P1_PANEL_SCORING_PENDING_20261106.md",
    }
    _write_summary(out / "summary.json", summary)
    return summary


def analyze_tsv(
    input_path: Path | str,
    provenance_path: Path | str,
    output_dir: Path | str,
    *,
    synthesis_contract: Mapping[str, object] | None = None,
    synthesis_contract_path: Path | str | None = None,
    learned_input_path: Path | str | None = None,
    learned_provenance_path: Path | str | None = None,
    learned_score_records: Sequence[Mapping[str, object]] | None = None,
    learned_score_provenance: Mapping[str, object] | None = None,
    allow_outcomes: bool = False,
) -> dict:
    """Preflight every path and manifest before reading any input table or contract."""
    input_path = assert_allowed_input_path(input_path)
    provenance_path = assert_allowed_input_path(provenance_path)
    contract_path = (
        assert_allowed_input_path(synthesis_contract_path)
        if synthesis_contract_path is not None else None
    )
    learned_paths_requested = learned_input_path is not None or learned_provenance_path is not None
    if learned_paths_requested:
        if learned_score_records is not None or learned_score_provenance is not None:
            raise ValueError("Choose learned-score file paths or in-memory rows, not both")
        if learned_input_path is None or learned_provenance_path is None:
            raise ValueError("Learned-score input and provenance paths must be supplied together")
        learned_input_path = assert_allowed_input_path(learned_input_path)
        learned_provenance_path = assert_allowed_input_path(learned_provenance_path)
    if (synthesis_contract is not None) and (contract_path is not None):
        raise ValueError("Choose an in-memory synthesis contract or a contract file, not both")

    manifest = preflight_input_manifest(provenance_path, allow_outcomes=allow_outcomes)
    learned_manifest = None
    if learned_paths_requested:
        from .learned import preflight_learned_score_manifest

        learned_manifest = preflight_learned_score_manifest(
            learned_provenance_path, allow_outcomes=allow_outcomes
        )
    if contract_path is not None:
        synthesis_contract = _read_json_object(contract_path)

    records, manifest = load_input_tsv(
        input_path, provenance_path, allow_outcomes=allow_outcomes
    )
    if learned_paths_requested:
        from .learned import load_learned_score_tsv

        learned_score_records, learned_score_provenance = load_learned_score_tsv(
            learned_input_path,
            learned_provenance_path,
            allow_outcomes=allow_outcomes,
        )
        if learned_score_provenance != learned_manifest:
            raise ValueError("Learned-score provenance changed after preflight")
    return analyze_records(
        records,
        manifest,
        output_dir,
        synthesis_contract=synthesis_contract,
        learned_score_records=learned_score_records,
        learned_score_provenance=learned_score_provenance,
        allow_outcomes=allow_outcomes,
    )


def _run_r(
    rows: Sequence[Mapping[str, object]], output_dir: Path, summary: Mapping[str, object]
):
    projected_rows = [
        {field: row[field] for field in _R_INPUT_FIELDS}
        for row in rows
    ]
    sorted_rows = sorted(
        projected_rows,
        key=lambda row: (
            _utf8(row["study_id"]), _utf8(row["patient_key"]), _utf8(row["score_method"])
        ),
    )
    synthesis_weights = {}
    synthesis_collection_ids = {}
    for method, key in (("CYT", "synthesis"), ("LEARNED", "learned_score_secondary")):
        result = summary.get(key)
        if method == "LEARNED" and isinstance(result, Mapping):
            result = result.get("synthesis")
        if isinstance(result, Mapping) and str(result.get("status", "")).startswith("estimated"):
            weights = result.get("weighting")
            collection_id = result.get("collection_id")
            if isinstance(weights, Mapping) and weights and collection_id:
                synthesis_weights[method] = dict(weights)
                synthesis_collection_ids[method] = str(collection_id)

    config = {
        "expected_outputs": _EXPECTED_R_OUTPUTS,
        "score_mapping_version": SCORE_MAPPING_VERSION,
        "score_mapping_versions": {
            row["score_method"]: (
                SCORE_MAPPING_VERSION if row["score_method"] == "CYT"
                else "A_P1_SINGLE_FROZEN_EQUATION_V1"
            )
            for row in sorted_rows
        },
        "endpoint_mapping_version": summary["endpoint_mapping_version"],
        "bootstrap_repetitions": 2000,
        "interval": "95_percentile_type_7",
        "main_stream": "a_p1_bootstrap",
        "second_check_stream": "second_check",
        "second_check_task_id": "a_p1_bootstrap",
        "assignment_iteration_order": (
            "replicate; study UTF-8 radix; score method UTF-8 radix within study; "
            "O, SD, PD; patient key UTF-8 radix within each stratum; draw"
        ),
        "synthesis_weights": synthesis_weights,
        "synthesis_collection_ids": synthesis_collection_ids,
    }
    work_key = canonical_sha256({"rows": sorted_rows, "config": config})
    work_dir = output_dir / ".a_p1_work" / work_key
    work_dir.mkdir(parents=True, exist_ok=True)
    input_path = work_dir / "analysis_input.tsv"
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=_R_INPUT_FIELDS, delimiter="\t")
    writer.writeheader()
    writer.writerows(sorted_rows)
    input_payload = buffer.getvalue().encode("utf-8")
    input_hash = sha256(input_payload).hexdigest()
    if input_path.exists():
        if sha256(input_path.read_bytes()).hexdigest() != input_hash:
            raise ValueError("Retained A-P1 R input does not match its hash-keyed work directory")
    else:
        input_path.write_bytes(input_payload)
    return run_r_sanitised(
        _R_SCRIPT,
        {"analysis_input": input_path},
        config,
        output_dir / "r",
        script_id="a_p1_random_stream_bootstrap",
        retention_dir=work_dir / "bridge_work",
    )


def _attach_bootstrap_results(summary: dict, outputs: Mapping[str, Path], manifest: Mapping) -> None:
    intervals = _read_tsv(outputs["intervals.tsv"])
    receipts = _read_tsv(outputs["random_receipts.tsv"])
    comparisons = _read_tsv(outputs["second_check_comparison.tsv"])
    interval_lookup = defaultdict(lambda: defaultdict(dict))
    for row in intervals:
        interval_lookup[(row["scope"], row["score_method"], row["study_id"])][row["stream"]][row["metric"]] = {
            "interval": [float(row["lower"]), float(row["upper"])],
            "conditioning": row["conditioning"],
        }
    receipt_lookup = {}
    for row in receipts:
        receipt_lookup[row["stream"]] = row
    comparison_lookup = {
        (row["scope"], row["score_method"], row["study_id"]): row for row in comparisons
    }
    main_receipt = receipt_lookup["a_p1_bootstrap"]
    check_receipt = receipt_lookup["second_check"]

    def attach(target: dict, scope: str, method: str, study: str) -> None:
        if target.get("status") not in {"informative", "structurally_zero_no_sd"}:
            target["bootstrap"] = _nonestimable_bootstrap(target)
            return
        streams = interval_lookup.get((scope, method, study), {})
        if "a_p1_bootstrap" not in streams:
            return
        if any(metric not in streams["a_p1_bootstrap"] for metric in ("auc_orr", "auc_dcr", "delta")):
            target["bootstrap"] = _nonestimable_bootstrap(target)
            return
        comparison = comparison_lookup.get((scope, method, study), {})
        conditioning = streams["a_p1_bootstrap"]["delta"]["conditioning"]
        target["bootstrap"] = {
            "status": "structural_zero_sensitivity" if target.get("status") == "structurally_zero_no_sd" else "estimated",
            "stream": "a_p1_bootstrap",
            "seed": int(main_receipt["seed"]),
            "repetitions": int(main_receipt["repetitions"]),
            "conditioning": conditioning,
            "conditioning_statement": (
                "Intervals condition on the original O/SD/PD category counts within each "
                "study and score analysis; they do not include category-composition uncertainty."
            ),
            "main_interval": {
                metric: value["interval"]
                for metric, value in streams["a_p1_bootstrap"].items()
            },
            "second_check_stream": "second_check",
            "second_check_seed": int(check_receipt["seed"]),
            "second_check_interval": {
                metric: value["interval"]
                for metric, value in streams["second_check"].items()
            },
            "second_check_delta_lower_difference": float(comparison["delta_lower_difference"]),
            "second_check_delta_upper_difference": float(comparison["delta_upper_difference"]),
            "second_check_flag_over_0_01": _as_bool(comparison["flag_over_0_01"]),
            "second_check_decision": "reported_only",
            "second_check_replaces_main": False,
            "selected_interval_stream": "a_p1_bootstrap",
            "assignment_receipt_sha256": main_receipt["receipt_sha256"],
            "assignment_file_sha256": main_receipt["assignment_file_sha256"],
            "second_check_receipt_sha256": check_receipt["receipt_sha256"],
            "second_check_assignment_file_sha256": check_receipt["assignment_file_sha256"],
            "assignment_artifact_sha256": manifest["output_sha256"]["bootstrap_assignments.tsv"],
        }

    for study, result in summary["studies"].items():
        attach(result, "study", "CYT", study)
        if "bootstrap" not in result:
            result["bootstrap"] = _nonestimable_bootstrap(result)
    learned = summary.get("learned_score_secondary")
    if isinstance(learned, dict) and isinstance(learned.get("studies"), dict):
        for study, result in learned["studies"].items():
            attach(result, "study", "LEARNED", study)
            if "bootstrap" not in result:
                result["bootstrap"] = _nonestimable_bootstrap(result)

    for method, key in (("CYT", "synthesis"), ("LEARNED", "learned_score_secondary")):
        target = summary.get(key)
        if method == "LEARNED" and isinstance(target, dict):
            target = target.get("synthesis")
        if not isinstance(target, dict) or not str(target.get("status", "")).startswith("estimated"):
            continue
        collection_id = str(target.get("collection_id", ""))
        streams = interval_lookup.get(("collection", method, collection_id), {})
        if "a_p1_bootstrap" not in streams:
            target["interval_status"] = "not_estimable_joint_bootstrap_missing_collection_rows"
            continue
        comparison = comparison_lookup[("collection", method, collection_id)]
        target["interval"] = {
            metric: value["interval"]
            for metric, value in streams["a_p1_bootstrap"].items()
        }
        target["interval_status"] = "estimated_conditional_on_original_category_counts"
        target["bootstrap"] = {
            "status": "estimated",
            "stream": "a_p1_bootstrap",
            "seed": int(main_receipt["seed"]),
            "repetitions": int(main_receipt["repetitions"]),
            "conditioning": streams["a_p1_bootstrap"]["delta"]["conditioning"],
            "conditioning_statement": (
                "Collection intervals condition on the original O/SD/PD category counts "
                "within each weighted study and score analysis."
            ),
            "interval": target["interval"],
            "second_check_stream": "second_check",
            "second_check_seed": int(check_receipt["seed"]),
            "second_check_interval": {
                metric: value["interval"]
                for metric, value in streams["second_check"].items()
            },
            "second_check_delta_lower_difference": float(comparison["delta_lower_difference"]),
            "second_check_delta_upper_difference": float(comparison["delta_upper_difference"]),
            "second_check_flag_over_0_01": _as_bool(comparison["flag_over_0_01"]),
            "second_check_decision": "reported_only",
            "second_check_replaces_main": False,
            "selected_interval_stream": "a_p1_bootstrap",
            "assignment_receipt_sha256": main_receipt["receipt_sha256"],
            "assignment_file_sha256": main_receipt["assignment_file_sha256"],
            "second_check_receipt_sha256": check_receipt["receipt_sha256"],
            "second_check_assignment_file_sha256": check_receipt["assignment_file_sha256"],
            "assignment_artifact_sha256": manifest["output_sha256"]["bootstrap_assignments.tsv"],
        }


def _nonestimable_bootstrap(result: Mapping[str, object]) -> dict:
    status = str(result.get("status", ""))
    return {
        "status": (
            "not_run_nonestimable_missing_o_or_pd"
            if status == "nonestimable_missing_o_or_pd"
            else "not_run_nonestimable_no_eligible_patients"
        ),
        "stream": "a_p1_bootstrap",
        "seed": 20261108,
        "conditioning": "conditional_on_original_study_category_counts_O_SD_PD",
        "conditioning_statement": (
            "Any reported intervals condition on the original O/SD/PD category counts within "
            "each study and score analysis; they do not include category-composition uncertainty."
        ),
    }


def _study_uncertainty_status(studies: Mapping[str, Mapping[str, object]]) -> str:
    statuses = [
        str(study.get("bootstrap", {}).get("status", ""))
        for study in studies.values()
    ]
    if statuses and all(status in {"estimated", "structural_zero_sensitivity"} for status in statuses):
        return "per_study_bootstrap_intervals_available"
    if any(status in {"estimated", "structural_zero_sensitivity"} for status in statuses):
        return "partial_per_study_bootstrap_nonestimable_studies"
    return "no_estimable_per_study_bootstrap_intervals"


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def _write_summary(path: Path, summary: Mapping[str, object]) -> None:
    path.write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _read_json_object(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("A-P1 synthesis contract is missing or malformed") from error
    if not isinstance(value, dict):
        raise ValueError("A-P1 synthesis contract must be a JSON object")
    return value


def _utf8(value: object) -> bytes:
    return str(value).encode("utf-8")


def _as_bool(value: object) -> bool:
    return str(value).strip().casefold() in {"true", "1"}
