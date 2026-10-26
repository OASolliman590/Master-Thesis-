"""Validate invented prior-use assertions without certifying actual untouched data."""
from __future__ import annotations
from typing import Any
from .core import SchemaStore, dependency, finish, require, stage_boundary

REASON_CODES = frozenset({"EXPOSURE_POLICY_UNKNOWN", "EXPOSURE_CONTRADICTION", "EXPOSURE_SUBJECT_UNKNOWN", "EXPOSURE_REVIEW_REQUIRED"})
ASSOCIATED = frozenset({"MOLECULAR_RESPONSE_INSPECTION", "DIFFERENTIAL_EXPRESSION", "PROGRAMME_LEARNING", "FEATURE_SELECTION", "MODEL_TUNING", "THRESHOLD_SELECTION", "PUBLISHED_COMPARATOR_DEVELOPMENT", "FINAL_TEST_EVALUATION", "PROSTATE_TRANSFER"})


@stage_boundary("exposure")
def validate_exposure(packet: dict[str, Any], *, schemas: SchemaStore | None = None) -> dict[str, Any]:
    store = schemas or SchemaStore()
    dependency(packet, "registries", store)
    records, config = packet["records"], packet["config"].get("exposure", {})
    subjects = {"STUDY_FAMILY": {r["publication_family_id"] for r in records.get("publication_family", [])},
                "SOURCE_OBJECT": {r["source_object_id"] for r in records.get("source_record", [])},
                "PATIENT_SET": {r["patient_uid"] for r in records.get("patient_registry", [])},
                "SPECIMEN_SET": {r["specimen_uid"] for r in records.get("specimen_registry", [])},
                "COMPARATOR_TRAINING_SET": set(config.get("comparator_training_set_ids", []))}
    decisions: dict[tuple[str, str], list[str]] = {}
    rows = records.get("prior_exposure_record", [])
    for row in rows:
        require(row["subject_id"] in subjects[row["subject_type"]], "EXPOSURE_SUBJECT_UNKNOWN")
        use, implication = row["use"], row["independence_implication"]
        if use in ASSOCIATED:
            require(implication != "METADATA_ONLY_REVIEWED", "EXPOSURE_CONTRADICTION")
        if use == "METADATA_INSPECTION":
            require(not any(f.lower() in {"expression", "molecular", "orr", "response", "outcome", "performance"} for f in row["fields_accessed"]), "EXPOSURE_CONTRADICTION")
        if row["analysis_lineage_id"] == config.get("analysis_lineage_id"):
            state = ("RESPONSE_ASSOCIATED" if use in ASSOCIATED else
                     "METADATA_ONLY" if use == "METADATA_INSPECTION" and implication == "METADATA_ONLY_REVIEWED" else
                     "CLINICAL_ONLY" if use in {"CLINICAL_ENDPOINT_CURATION", "CLASS_COUNT_PLANNING"} else "UNKNOWN")
            decisions.setdefault((row["subject_type"], row["subject_id"]), []).append(state)
    require(isinstance(config.get("analysis_lineage_id"), str) and bool(config["analysis_lineage_id"]), "EXPOSURE_POLICY_UNKNOWN", blocked=True)
    require(config.get("review_complete") is True, "EXPOSURE_POLICY_UNKNOWN", blocked=True)
    covered = config.get("covered_subjects")
    require(isinstance(covered, list) and bool(covered), "EXPOSURE_POLICY_UNKNOWN", blocked=True)
    audit: list[dict[str, Any]] = []
    covered_family_ids = {s.get("subject_id") for s in covered if s.get("subject_type") == "STUDY_FAMILY"}
    unknown = not subjects["STUDY_FAMILY"].issubset(covered_family_ids)
    for subject in covered:
        key = (subject["subject_type"], subject["subject_id"])
        require(key[0] in subjects and key[1] in subjects[key[0]], "EXPOSURE_SUBJECT_UNKNOWN")
        states = decisions.get(key, ["UNKNOWN"])
        state = "RESPONSE_ASSOCIATED" if "RESPONSE_ASSOCIATED" in states else "UNKNOWN" if "UNKNOWN" in states else "CLINICAL_ONLY" if "CLINICAL_ONLY" in states else "METADATA_ONLY"
        unknown |= state == "UNKNOWN"
        audit.append({"kind": "exposure_decision", "subject_type": key[0], "subject_id": key[1],
                      "analysis_lineage_id": config["analysis_lineage_id"], "state": state,
                      "untouched_certified": False})
    return finish("exposure", packet, records, status="BLOCKED_UNKNOWN" if unknown else "READY",
                  reasons=["EXPOSURE_REVIEW_REQUIRED"] if unknown else [], audit=audit, schemas=store)


def patient_exposure_state(records: dict[str, Any], audit: list[dict[str, Any]],
                           patient: dict[str, Any], lineage: str | None) -> str:
    """Reconcile applicable ledger rows and sealed decisions for one patient."""
    studies = {r['study_id']: r for r in records.get('study_registry', [])}
    study = studies.get(patient['study_id'], {})
    subjects = {('PATIENT_SET', patient['patient_uid']),
                ('STUDY_FAMILY', study.get('publication_family_id'))}
    subjects.update(('SPECIMEN_SET', r['specimen_uid']) for r in records.get('specimen_registry', [])
                    if r['patient_uid'] == patient['patient_uid'])
    specimen_ids = {uid for kind, uid in subjects if kind == 'SPECIMEN_SET'}
    subjects.update(('SOURCE_OBJECT', r['source_object_id']) for r in records.get('assay_registry', [])
                    if r['specimen_uid'] in specimen_ids)
    states = [r['state'] for r in audit if r.get('kind') == 'exposure_decision'
              and (lineage is None or r.get('analysis_lineage_id') == lineage)
              and (r.get('subject_type'), r.get('subject_id')) in subjects]
    for row in records.get('prior_exposure_record', []):
        if (lineage is not None and row['analysis_lineage_id'] != lineage) or (row['subject_type'], row['subject_id']) not in subjects:
            continue
        states.append('RESPONSE_ASSOCIATED' if row['use'] in ASSOCIATED else
                      'METADATA_ONLY' if row['use'] == 'METADATA_INSPECTION' and
                      row['independence_implication'] == 'METADATA_ONLY_REVIEWED' else
                      'CLINICAL_ONLY' if row['use'] in {'CLINICAL_ENDPOINT_CURATION', 'CLASS_COUNT_PLANNING'} else 'UNKNOWN')
    return next((state for state in ('RESPONSE_ASSOCIATED', 'UNKNOWN', 'CLINICAL_ONLY', 'METADATA_ONLY')
                 if state in states), 'UNKNOWN')
