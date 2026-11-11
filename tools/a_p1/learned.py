"""Validation and independent summary of an optional frozen learned score."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence

from tools.a_meta.provenance import canonical_sha256, is_locked_study, known_cohort_ids

from .endpoints import ENDPOINT_MAPPING_VERSION, category_metrics
from .provenance import assert_allowed_input_path, is_known_real_identity


LEARNED_SCORE_FIELDS = ("study_id", "patient_key", "index_episode_id", "score")
_LEARNED_PRODUCER = "tools.a_p1.synthetic_learned_score_fixture"
_LEARNED_KIND = "a_p1_learned_score"


def create_synthetic_learned_manifest(
    records: Sequence[Mapping[str, object]],
    *,
    equation_id: str,
    equation_sha256: str,
    feature_selection_patients: Sequence[Mapping[str, object]],
    fitting_patients: Sequence[Mapping[str, object]],
    tuning_patients: Sequence[Mapping[str, object]],
    score_kind: str,
    training_source_sha256: Sequence[str],
) -> dict:
    scores = _project_score_rows(records)
    cohort_ids = sorted({str(row["study_id"]) for row in scores})
    if any(is_locked_study(study) for study in cohort_ids) or any(
        is_known_real_identity(study) for study in cohort_ids
    ):
        raise ValueError("Synthetic learned scores cannot name a protected or known real cohort")
    prediction_patients = _patient_set(scores)
    feature_patients = _normalize_patient_set(feature_selection_patients, "feature selection")
    fit_patients = _normalize_patient_set(fitting_patients, "fitting")
    tuning = _normalize_patient_set(tuning_patients, "tuning")
    return {
        "manifest_version": 1,
        "producer": _LEARNED_PRODUCER,
        "data_classification": "synthetic",
        "kind": _LEARNED_KIND,
        "cohort_ids": cohort_ids,
        "selected_fields": list(LEARNED_SCORE_FIELDS),
        "score_kind": score_kind,
        "frozen_status": "INVENTED_FIXTURE",
        "equation_id": equation_id,
        "equation_sha256": equation_sha256,
        "training_source_sha256": list(training_source_sha256),
        "feature_selection_patients": feature_patients,
        "fitting_patients": fit_patients,
        "tuning_patients": tuning,
        "prediction_patients": prediction_patients,
        "prediction_patient_set_sha256": _patient_set_hash(prediction_patients),
        "payload_sha256": _score_payload_hash(scores),
    }


def learned_score_sensitivity(
    records: Sequence[Mapping[str, object]],
    manifest: Mapping[str, object],
    primary_patients: Sequence[Mapping[str, object]],
    *,
    data_classification: str = "synthetic",
    allow_outcomes: bool = False,
) -> dict:
    """Estimate endpoint sensitivity only for a validated single frozen score."""
    result, _ = learned_score_analysis(
        records,
        manifest,
        primary_patients,
        data_classification=data_classification,
        allow_outcomes=allow_outcomes,
    )
    return result


def learned_score_analysis(
    records: Sequence[Mapping[str, object]],
    manifest: Mapping[str, object],
    endpoint_patients: Sequence[Mapping[str, object]],
    *,
    data_classification: str = "synthetic",
    allow_outcomes: bool = False,
) -> tuple[dict, list[dict]]:
    """Return learned-score summaries and independently qualified R rows."""
    _preflight_learned_manifest(manifest, allow_outcomes=allow_outcomes)
    scores = _project_score_rows(records)
    _validate_manifest(
        manifest, scores, data_classification=data_classification, allow_outcomes=allow_outcomes
    )
    prediction_set = _patient_tuples(manifest.get("prediction_patients"), "prediction")
    fit_sets = _patient_tuples(manifest.get("feature_selection_patients"), "feature selection")
    fit_sets.update(_patient_tuples(manifest.get("fitting_patients"), "fitting"))
    fit_sets.update(_patient_tuples(manifest.get("tuning_patients"), "tuning"))
    if prediction_set & fit_sets:
        raise ValueError("Learned-score predictions must be disjoint from fitting, tuning and feature selection")

    outcome_lookup = {}
    for row in endpoint_patients:
        key = (str(row["study_id"]), str(row["patient_key"]))
        if key in outcome_lookup:
            raise ValueError("A-P1 patient keys must be unique within each study")
        outcome_lookup[key] = row
    grouped: dict[str, list[tuple[float, str, str]]] = defaultdict(list)
    exclusions: Counter[str] = Counter()
    accepted_rows = []
    for row in scores:
        key = (str(row["study_id"]), str(row["patient_key"]))
        outcome = outcome_lookup.get(key)
        if outcome is None:
            exclusions["NO_MATCHING_ENDPOINT_PATIENT"] += 1
            continue
        if str(outcome["index_episode_id"]) != str(row["index_episode_id"]):
            exclusions["INDEX_EPISODE_MISMATCH"] += 1
            continue
        category = str(outcome["category"])
        grouped[key[0]].append((float(row["score"]), category, key[1]))
        accepted_rows.append({
            "study_id": key[0],
            "patient_key": key[1],
            "index_episode_id": str(row["index_episode_id"]),
            "category": category,
            "score": float(row["score"]),
            "score_method": "LEARNED",
        })

    study_results = {}
    for study in sorted({str(row["study_id"]) for row in scores}, key=lambda value: value.encode("utf-8")):
        eligible = sorted(grouped.get(study, ()), key=lambda row: row[2].encode("utf-8"))
        if eligible:
            metrics = category_metrics(
                [row[0] for row in eligible], [row[1] for row in eligible]
            )
        else:
            metrics = _empty_metrics()
        study_scores = [row for row in accepted_rows if row["study_id"] == study]
        study_results[study] = {
            "study_id": study,
            **metrics,
            "score_hash_sha256": _learned_score_hash(study, study_scores),
        }
    accepted_rows.sort(key=lambda row: (str(row["study_id"]).encode("utf-8"),
                                        str(row["patient_key"]).encode("utf-8")))
    result = {
        "status": "estimated_synthetic_fixture" if data_classification == "synthetic" else "estimated",
        "analysis_identity": "A_P1_LEARNED_SCORE_SECONDARY_V1",
        "equation_id": str(manifest["equation_id"]),
        "equation_sha256": str(manifest["equation_sha256"]),
        "score_kind": "single_frozen_equation",
        "score_mapping_version": "A_P1_SINGLE_FROZEN_EQUATION_V1",
        "endpoint_mapping_version": ENDPOINT_MAPPING_VERSION,
        "prediction_payload_sha256": str(manifest["payload_sha256"]),
        "score_hash_sha256": _learned_score_hash_all(accepted_rows),
        "prediction_patient_set_sha256": str(manifest["prediction_patient_set_sha256"]),
        "training_provenance_sha256": {
            "feature_selection_patients": _patient_set_hash(manifest["feature_selection_patients"]),
            "fitting_patients": _patient_set_hash(manifest["fitting_patients"]),
            "tuning_patients": _patient_set_hash(manifest["tuning_patients"]),
        },
        "source_hashes": list(manifest["training_source_sha256"]),
        "studies": study_results,
        "uncertainty_status": "not_run_standalone_point_summary_requires_joint_a_p1_analysis",
        "exclusions": dict(sorted(exclusions.items())),
        "synthetic_scope": (
            "invented provenance fixture; not biological evidence"
            if data_classification == "synthetic" else None
        ),
    }
    return result, accepted_rows


def load_learned_score_tsv(
    input_path: str,
    manifest_path: str,
    *,
    allow_outcomes: bool = False,
) -> tuple[list[dict[str, object]], dict]:
    """Preflight provenance, then read exact learned-score columns."""
    source_path = assert_allowed_input_path(input_path)
    provenance_path = assert_allowed_input_path(manifest_path)
    manifest = preflight_learned_score_manifest(
        provenance_path, allow_outcomes=allow_outcomes
    )
    with source_path.open(newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream, delimiter="\t")
        try:
            headers = next(reader)
        except StopIteration as error:
            raise ValueError("Learned-score input is empty") from error
        if len(headers) != len(set(headers)):
            raise ValueError("Learned-score input has duplicate field names")
        indices = {field: headers.index(field) for field in LEARNED_SCORE_FIELDS if field in headers}
        if set(indices) != set(LEARNED_SCORE_FIELDS):
            raise ValueError("Learned-score input is missing an exact required field")
        records = []
        for row in reader:
            if len(row) != len(headers):
                raise ValueError("Learned-score row width does not match its header")
            records.append({field: row[indices[field]] for field in LEARNED_SCORE_FIELDS})
    scores = _project_score_rows(records)
    _validate_manifest(
        manifest, scores,
        data_classification=str(manifest["data_classification"]),
        allow_outcomes=allow_outcomes,
    )
    return scores, manifest


def preflight_learned_score_manifest(
    manifest_path: str,
    *,
    allow_outcomes: bool = False,
) -> dict:
    """Read and validate learned-score provenance before touching score rows."""
    from pathlib import Path

    provenance_path = assert_allowed_input_path(manifest_path)
    try:
        manifest = json.loads(provenance_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("Learned-score provenance is missing or malformed") from error
    if not isinstance(manifest, dict):
        raise ValueError("Learned-score provenance must be a JSON object")
    _preflight_learned_manifest(manifest, allow_outcomes=allow_outcomes)
    return manifest


def _validate_manifest(
    manifest: Mapping[str, object],
    scores: Sequence[Mapping[str, object]],
    *,
    data_classification: str,
    allow_outcomes: bool,
) -> None:
    if manifest.get("manifest_version") != 1 or manifest.get("kind") != _LEARNED_KIND:
        raise ValueError("Unsupported learned-score provenance manifest")
    classification = manifest.get("data_classification")
    if classification != data_classification:
        raise ValueError("Learned-score data classification does not match the analysis input")
    cohort_ids = manifest.get("cohort_ids")
    if not isinstance(cohort_ids, list) or not cohort_ids:
        raise ValueError("Learned-score provenance must declare cohort identities")
    if any(is_locked_study(value) for value in cohort_ids):
        raise PermissionError("Protected final-test identities are refused by A-P1")
    known = known_cohort_ids()
    if classification == "synthetic":
        if manifest.get("producer") != _LEARNED_PRODUCER:
            raise ValueError("This learned-score test route requires explicit synthetic provenance")
        if any(is_known_real_identity(study) for study in cohort_ids):
            raise ValueError("Synthetic learned scores contradict a known real cohort")
    elif classification == "real":
        if not set(cohort_ids).issubset(known):
            raise ValueError("Real learned-score provenance names an unknown cohort")
        if not allow_outcomes:
            raise PermissionError("Real learned-score outcomes are restricted without --allow-outcomes")
        if not str(manifest.get("outcome_release_id", "")).strip():
            raise PermissionError("Real learned-score input requires an explicit outcome release ID")
        if manifest.get("outcome_release_status") != "SIGNED_RELEASED":
            raise PermissionError("Real learned-score input requires a signed outcome release")
        source_hashes = manifest.get("source_object_sha256")
        if not isinstance(source_hashes, list) or not source_hashes or not all(_is_sha256(value) for value in source_hashes):
            raise PermissionError("Real learned-score provenance requires source-object SHA-256 values")
    else:
        raise ValueError("Learned-score provenance must declare synthetic or real data")
    if tuple(manifest.get("selected_fields", ())) != LEARNED_SCORE_FIELDS:
        raise ValueError("Learned-score provenance must bind the exact selected fields")
    if manifest.get("score_kind") != "single_frozen_equation":
        raise ValueError("Learned-score endpoint sensitivity requires one single frozen equation")
    expected_status = "INVENTED_FIXTURE" if classification == "synthetic" else "FROZEN"
    if manifest.get("frozen_status") != expected_status:
        raise ValueError("Learned-score provenance does not declare one frozen equation")
    if not str(manifest.get("equation_id", "")).strip():
        raise ValueError("Learned-score provenance requires one equation ID")
    if not _is_sha256(manifest.get("equation_sha256")):
        raise ValueError("Learned-score provenance requires the frozen equation hash")
    source_hashes = manifest.get("training_source_sha256")
    if not isinstance(source_hashes, list) or not source_hashes or not all(_is_sha256(value) for value in source_hashes):
        raise ValueError("Learned-score provenance requires training source hashes")
    studies = sorted({str(row["study_id"]) for row in scores})
    if studies != sorted(cohort_ids):
        raise ValueError("Learned-score provenance study identities do not match predictions")
    if _score_payload_hash(scores) != manifest.get("payload_sha256"):
        raise ValueError("Learned-score provenance payload hash does not match predictions")
    prediction = _patient_set(scores)
    if prediction != _normalize_patient_set(manifest.get("prediction_patients"), "prediction"):
        raise ValueError("Learned-score prediction set does not match score rows")
    if _patient_set_hash(prediction) != manifest.get("prediction_patient_set_sha256"):
        raise ValueError("Learned-score prediction set hash does not match")
    for field in ("feature_selection_patients", "fitting_patients", "tuning_patients"):
        _normalize_patient_set(manifest.get(field), field)
    for study in studies:
        if is_locked_study(study) or (classification == "synthetic" and is_known_real_identity(study)):
            raise ValueError("Synthetic learned scores contradict a known real or protected cohort")


def _preflight_learned_manifest(manifest: Mapping[str, object], *, allow_outcomes: bool) -> None:
    if manifest.get("manifest_version") != 1 or manifest.get("kind") != _LEARNED_KIND:
        raise ValueError("Unsupported learned-score provenance manifest")
    classification = manifest.get("data_classification")
    cohort_ids = manifest.get("cohort_ids")
    if not isinstance(cohort_ids, list) or not cohort_ids:
        raise ValueError("Learned-score provenance must declare cohort identities")
    if any(is_locked_study(value) for value in cohort_ids):
        raise PermissionError("Protected final-test identities are refused by A-P1")
    known = known_cohort_ids()
    if classification == "synthetic":
        if manifest.get("producer") != _LEARNED_PRODUCER or any(
            is_known_real_identity(study) for study in cohort_ids
        ):
            raise ValueError("Synthetic learned-score provenance is not valid for these identities")
    elif classification == "real":
        if not set(cohort_ids).issubset(known):
            raise ValueError("Real learned-score provenance names an unknown cohort")
        if not allow_outcomes:
            raise PermissionError("Real learned-score outcomes are restricted without --allow-outcomes")
        if not str(manifest.get("outcome_release_id", "")).strip():
            raise PermissionError("Real learned-score input requires an explicit outcome release ID")
        if manifest.get("outcome_release_status") != "SIGNED_RELEASED":
            raise PermissionError("Real learned-score input requires a signed outcome release")
        source_hashes = manifest.get("source_object_sha256")
        if not isinstance(source_hashes, list) or not source_hashes or not all(_is_sha256(value) for value in source_hashes):
            raise PermissionError("Real learned-score provenance requires source-object SHA-256 values")
    else:
        raise ValueError("Learned-score provenance must declare synthetic or real data")
    if tuple(manifest.get("selected_fields", ())) != LEARNED_SCORE_FIELDS:
        raise ValueError("Learned-score provenance must bind the exact selected fields")
    if manifest.get("score_kind") != "single_frozen_equation":
        raise ValueError("Learned-score endpoint sensitivity requires one single frozen equation")
    expected_status = "INVENTED_FIXTURE" if classification == "synthetic" else "FROZEN"
    if manifest.get("frozen_status") != expected_status:
        raise ValueError("Learned-score provenance does not declare one frozen equation")
    if not str(manifest.get("equation_id", "")).strip() or not _is_sha256(manifest.get("equation_sha256")):
        raise ValueError("Learned-score provenance requires one hashed equation")
    source_hashes = manifest.get("training_source_sha256")
    if not isinstance(source_hashes, list) or not source_hashes or not all(_is_sha256(value) for value in source_hashes):
        raise ValueError("Learned-score provenance requires training source hashes")
    if not _is_sha256(manifest.get("payload_sha256")):
        raise ValueError("Learned-score provenance must bind a prediction payload hash")
    prediction_patients = _normalize_patient_set(manifest.get("prediction_patients"), "prediction")
    if _patient_set_hash(prediction_patients) != manifest.get("prediction_patient_set_sha256"):
        raise ValueError("Learned-score prediction set hash does not match")
    for field in ("feature_selection_patients", "fitting_patients", "tuning_patients"):
        _normalize_patient_set(manifest.get(field), field)


def _project_score_rows(records: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    if not records:
        raise ValueError("Learned-score input has no rows")
    rows = []
    seen = set()
    for raw in records:
        if any(field not in raw for field in LEARNED_SCORE_FIELDS):
            raise ValueError("Learned-score input is missing an exact required field")
        row = {field: raw[field] for field in LEARNED_SCORE_FIELDS}
        study = str(row["study_id"]).strip()
        patient = str(row["patient_key"]).strip()
        episode = str(row["index_episode_id"]).strip()
        if not study or not patient or not episode:
            raise ValueError("Learned-score rows require study, patient and index episode keys")
        key = study, patient
        if key in seen:
            raise ValueError("Learned-score rows contain duplicate study/patient keys")
        seen.add(key)
        try:
            score = float(row["score"])
        except (TypeError, ValueError) as error:
            raise ValueError("Learned-score predictions must be numeric") from error
        if not math.isfinite(score):
            raise ValueError("Learned-score predictions must be finite")
        row["score"] = score
        rows.append(row)
    return sorted(rows, key=lambda row: (str(row["study_id"]).encode("utf-8"),
                                         str(row["patient_key"]).encode("utf-8")))


def _normalize_patient_set(values: object, label: str) -> list[dict[str, str]]:
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"Learned-score {label} patient set is missing")
    result = []
    for value in values:
        if not isinstance(value, Mapping):
            raise ValueError(f"Learned-score {label} patient set has an invalid member")
        study = str(value.get("study_id", "")).strip()
        patient = str(value.get("patient_key", "")).strip()
        if not study or not patient:
            raise ValueError(f"Learned-score {label} patient set has an empty member")
        result.append({"study_id": study, "patient_key": patient})
    keys = {(row["study_id"], row["patient_key"]) for row in result}
    if len(keys) != len(result):
        raise ValueError(f"Learned-score {label} patient set has duplicates")
    return sorted(result, key=lambda row: (row["study_id"].encode("utf-8"),
                                           row["patient_key"].encode("utf-8")))


def _patient_set(records: Sequence[Mapping[str, object]]) -> list[dict[str, str]]:
    return _normalize_patient_set(records, "prediction")


def _patient_tuples(values: object, label: str) -> set[tuple[str, str]]:
    return {
        (row["study_id"], row["patient_key"])
        for row in _normalize_patient_set(values, label)
    }


def _patient_set_hash(values: object) -> str:
    rows = _normalize_patient_set(values, "patient")
    return canonical_sha256(rows)


def _score_payload_hash(rows: Sequence[Mapping[str, object]]) -> str:
    return canonical_sha256({"selected_fields": list(LEARNED_SCORE_FIELDS), "records": list(rows)})


def _learned_score_hash(study: str, rows: Sequence[Mapping[str, object]]) -> str:
    return canonical_sha256({
        "score_mapping_version": "A_P1_SINGLE_FROZEN_EQUATION_V1",
        "study": study,
        "scores": [
            [row["patient_key"], row["index_episode_id"], format(float(row["score"]), ".17g")]
            for row in rows
        ],
    })


def _learned_score_hash_all(rows: Sequence[Mapping[str, object]]) -> str:
    return canonical_sha256({
        "score_mapping_version": "A_P1_SINGLE_FROZEN_EQUATION_V1",
        "scores": [
            [row["study_id"], row["patient_key"], row["index_episode_id"],
             format(float(row["score"]), ".17g")]
            for row in rows
        ],
    })


def _is_sha256(value: object) -> bool:
    token = str(value or "")
    return len(token) == 64 and all(character in "0123456789abcdef" for character in token)


def _empty_metrics() -> dict:
    return {
        "n": 0,
        "category_counts": {"O": 0, "SD": 0, "PD": 0},
        "category_fractions": {"O": None, "SD": None, "PD": None},
        "auc_orr": None,
        "auc_dcr": None,
        "delta": None,
        "pairwise_auc": {"O_SD": None, "O_PD": None, "SD_PD": None},
        "auc_orr_decomposed": None,
        "auc_dcr_decomposed": None,
        "decomposition_verified": None,
        "status": "nonestimable_no_eligible_patients",
        "informative": False,
        "nonestimability_reason": "no_eligible_scored_source_supported_categories",
    }
