"""Build the proposed Riaz pretreatment branch packet and unsigned review bundle."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, cast

from .core import DavError, ENTITY_TABLES, require
from .review_prepare import _read_packet, prepare_review

POLICY_VERSION = "riaz-baseline-bor-recist11-v1"
ARTICLE_LOCATOR = "https://pmc.ncbi.nlm.nih.gov/articles/PMC5685550/"
AUTHOR_CLINICAL_LOCATOR = "https://github.com/riazn/bms038_analysis/blob/137111c38a32f8626ee6a436e14ac667bd31b1e7/data/bms038_clinical_data.csv"
GEO_LOCATOR = "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE91061"
_RIAZ_SOURCE_HASHES = {
    "2ecd5f064b076fdce58fd651b0a3404cc01ef889c5cfb8d760dc5c7a01adeaf9",  # GEO family SOFT
    "775106fc1d43684bbd22414d179c4af08036de32cc2edacb1f50ed38768a4496",  # author sample table
    "a70ae5a0b1156b6d85ec89f0d58f3f67538bfb969d53ec5d98232411d19869ab",  # author clinical table
}

_CATEGORIES = {"CR": "CR", "PR": "PR", "SD": "SD", "PD": "PD", "NE": "NE",
               "UNKNOWN": "UNKNOWN", "UNK": "UNKNOWN"}
_NE_GEO_CROSSWALK = {"NE": {"UNK", "UNKNOWN"}}
_PENDING_QC_CATEGORIES = {"AUTHOR_EXCLUSION_POLICY_UNRESOLVED", "PCA_OUTLIER_STATUS_UNRESOLVED"}


def _index(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = row.get(key)
        if not isinstance(value, str) or value in result:
            raise DavError("BASELINE_IDENTITY_CONFLICT")
        result[value] = row
    return result


def _trim_questions(items: Any, *, baseline_aliases: set[str], nonbaseline_aliases: set[str],
                    baseline_source_patients: set[str]) -> list[dict[str, Any]]:
    require(isinstance(items, list), "BASELINE_WORKSHEET_INVALID")
    result: list[dict[str, Any]] = []
    for original in items:
        require(isinstance(original, dict) and isinstance(original.get("category"), str),
                "BASELINE_WORKSHEET_INVALID")
        row = copy.deepcopy(original)
        # Existing item status is preserved. These annotations document proposed branch
        # applicability; they are not reviewer decisions and never imply a signature.
        category = row["category"]
        pointers = row.get("evidence_pointers", [])
        require(isinstance(pointers, list) and all(isinstance(pointer, dict) for pointer in pointers),
                "BASELINE_WORKSHEET_INVALID")
        pointer_records = {str(pointer.get("record")) for pointer in pointers
                           if pointer.get("record") is not None}
        pointer_visits = {pointer.get("visit") for pointer in pointers}
        context = row.get("context", {})
        values = set(pointer_records)
        if isinstance(context, dict):
            values.update(str(value) for value in context.values()
                          if isinstance(value, (str, int, float)))
        has_baseline = bool(values & (baseline_aliases | baseline_source_patients))
        has_nonbaseline = bool(values & nonbaseline_aliases)
        if category in _PENDING_QC_CATEGORIES:
            disposition = "PENDING_OUTCOME_INDEPENDENT_QC_POLICY"
        elif (category == "OUTCOME_LABEL_DISAGREEMENT" and has_baseline
              and isinstance(context, dict)
              and context.get("source_of_record_bor") == "NE"
              and context.get("corroborating_label") == "UNK"):
            disposition = "PROPOSED_NE_UNK_NULL_ORR_CROSSWALK_PENDING_REVIEW"
        elif ((category == "ON_TREATMENT_WINDOW_UNRESOLVED" and isinstance(context, dict)
               and context.get("source_label") == "On") or "On" in pointer_visits):
            disposition = "OUTSIDE_BASELINE_MEMBERSHIP_RETAIN_SOURCE_QUESTION"
        elif has_nonbaseline and not has_baseline:
            disposition = "OUTSIDE_BASELINE_MEMBERSHIP_RETAIN_SOURCE_QUESTION"
        elif has_baseline:
            disposition = "BASELINE_RELEVANT_RETAIN_UNRESOLVED_FOR_REVIEW"
        elif category == "HARMONIZED_SAMPLE_COUNT_CROSSCHECK":
            disposition = "CROSSCHECK_ONLY_NO_MEMBERSHIP_CHANGE_PENDING_REVIEW"
        else:
            disposition = "RETAIN_UNRESOLVED_BRANCH_APPLICABILITY"
        row["branch_disposition"] = disposition
        row["branch_id"] = "A_BASELINE_BIO"
        row["disposition_basis"] = "PROPOSED_PUBLIC_SOURCE_POLICY_NOT_REVIEWER_APPROVAL"
        result.append(row)
    return result


def _all_patient_disagreements_are_ne_unk(items: list[dict[str, Any]], source_patient: str,
                                           current_status: Any) -> bool:
    if current_status == "CONFLICT":
        return False
    relevant: list[dict[str, Any]] = []
    for item in items:
        pointers = item.get("evidence_pointers", [])
        if (item.get("category") == "OUTCOME_LABEL_DISAGREEMENT"
                and isinstance(pointers, list)
                and any(isinstance(pointer, dict) and pointer.get("role") == "author_clinical_table"
                        and pointer.get("record") == source_patient for pointer in pointers)):
            relevant.append(item)
    return bool(relevant) and all(
        isinstance((context := item.get("context")), dict)
        and context.get("source_of_record_bor") == "NE"
        and context.get("corroborating_label") in _NE_GEO_CROSSWALK["NE"]
        for item in relevant)


def _build_declared_baseline(packet: dict[str, Any], field_map: dict[str, Any]) -> dict[str, Any]:
    require(packet.get('branch_id') == 'A_BASELINE_BIO', 'BASELINE_BRANCH_MISMATCH')
    require(isinstance(packet.get('records'), dict) and isinstance(packet.get('config'), dict), 'MALFORMED_INPUT')
    current = copy.deepcopy(packet)
    records = current['records']
    role_list = field_map.get('decision_config', {}).get('preview', {}).get('required_roles', [])
    require(isinstance(role_list, list) and bool(role_list), 'BASELINE_REQUIRED_ROLES_UNKNOWN', blocked=True)
    sources = {row.get('source_object_id'): row for row in records.get('source_record', [])}
    for role in role_list:
        declared_hash = field_map.get('source_objects', {}).get(role, {}).get('sha256')
        source = sources.get(f"SOURCE:{field_map['cohort']}:{role}")
        require(bool(declared_hash) and isinstance(source, dict) and source.get('sha256') == declared_hash
                and source.get('retrieval_status') == 'RETRIEVED' and source.get('hash_scope') == 'FULL_OBJECT',
                'BASELINE_SOURCE_MISMATCH', blocked=True)
    selected = {row['patient_uid'] for row in records.get('specimen_registry', [])
                if row.get('canonical_timing_category') == 'PRE_INDEX_BASELINE'
                and row.get('baseline_candidate_status') == 'YES'}
    require(bool(selected), 'BASELINE_POPULATION_EMPTY', blocked=True)
    records['patient_registry'] = [row for row in records.get('patient_registry', []) if row.get('patient_uid') in selected]
    records['specimen_registry'] = [row for row in records.get('specimen_registry', []) if row.get('patient_uid') in selected]
    specimens = {row['specimen_uid'] for row in records['specimen_registry']}
    records['assay_registry'] = [row for row in records.get('assay_registry', []) if row.get('specimen_uid') in specimens]
    records['clinical_outcome'] = [row for row in records.get('clinical_outcome', []) if row.get('patient_uid') in selected]
    for table in ('treatment_episode', 'treatment_exposure', 'episode_binding'):
        records[table] = [row for row in records.get(table, []) if row.get('patient_uid') in selected]
    cfg = field_map['geo_ingest']
    classes = ['OTHER'] if cfg['endpoint_class'] == 'SOURCE_BINARY' else ['ORR']
    current['config']['endpoints'] = {'version': 'field-map', 'classes': classes,
        'category_map': copy.deepcopy(cfg['response_map']),
        'source_priority': [row['outcome_id'] for row in records['clinical_outcome']]}
    current['dependencies'] = {}
    return current

def build_baseline_packet(packet: dict[str, Any], *, field_map: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create a branch-scoped copy from canonical ingestion records.

    The function preserves source inventory and raw labels. It filters branch membership
    to identity-verified pretreatment specimens and their linked records, and sets a
    versioned author-BOR-to-RECIST mapping without setting any admission decision.
    """
    if field_map is not None and "geo_ingest" in field_map:
        return _build_declared_baseline(packet, field_map)
    require(isinstance(packet, dict) and packet.get("branch_id") == "A_BASELINE_BIO",
            "BASELINE_BRANCH_MISMATCH")
    require(isinstance(packet.get("records"), dict) and isinstance(packet.get("config"), dict),
            "MALFORMED_INPUT")
    current = copy.deepcopy(packet)
    records = current["records"]
    require(set(records) <= ENTITY_TABLES | {"coverage"}, "BASELINE_NONCANONICAL_INPUT")
    require(len(records.get("study_registry", [])) == 1, "BASELINE_STUDY_MISMATCH")
    source_hashes = {row.get("sha256") for row in records.get("source_record", [])}
    require(_RIAZ_SOURCE_HASHES <= source_hashes, "BASELINE_SOURCE_MISMATCH")
    # These two tables have no public Riaz branch-specific selection policy in this
    # release. Do not silently carry unsupported links after reducing branch membership.
    require(not records.get("overlap_edge") and not records.get("prior_exposure_record"),
            "BASELINE_UNSUPPORTED_LINKED_ENTITY")
    patients = _index(records.get("patient_registry", []), "patient_uid")
    specimens = _index(records.get("specimen_registry", []), "specimen_uid")
    outcomes = _index(records.get("clinical_outcome", []), "outcome_id")

    selected_specimens: set[str] = set()
    selected_patients: set[str] = set()
    nonbaseline_aliases: set[str] = set()
    for specimen in specimens.values():
        patient_id = specimen.get("patient_uid")
        if not isinstance(patient_id, str):
            raise DavError("BASELINE_IDENTITY_CONFLICT")
        patient = patients.get(patient_id)
        if (specimen.get("canonical_timing_category") == "PRE_INDEX_BASELINE"
                and patient is not None
                and patient.get("patient_identity_confidence") == "VERIFIED"):
            selected_specimens.add(specimen["specimen_uid"])
            selected_patients.add(patient_id)
        else:
            nonbaseline_aliases.update(str(alias) for alias in specimen.get("raw_sample_aliases", []))

    require(bool(selected_specimens), "BASELINE_POPULATION_EMPTY", blocked=True)
    selected_outcomes = {outcome_id for outcome_id, row in outcomes.items()
                         if row.get("patient_uid") in selected_patients}
    selected_episodes = {row.get("treatment_episode_id") for row in records.get("treatment_episode", [])
                         if row.get("patient_uid") in selected_patients}
    selected_exposures = {row.get("treatment_exposure_id") for row in records.get("treatment_exposure", [])
                          if row.get("patient_uid") in selected_patients
                          or row.get("treatment_episode_id") in selected_episodes}
    retained_ids = {"SPECIMEN": selected_specimens, "CLINICAL_OUTCOME": selected_outcomes,
                    "TREATMENT_EXPOSURE": selected_exposures}
    for binding in records.get("episode_binding", []):
        if (binding.get("subject_type") in retained_ids
                and binding.get("subject_id") in retained_ids[binding["subject_type"]]):
            selected_episodes.add(binding.get("treatment_episode_id"))

    # Preserve referential closure across selected branch entities, while retaining all
    # study/publication/source inventory rows as provenance for the raw source package.
    keep_ids: dict[str, set[Any]] = {
        "patient_registry": selected_patients,
        "specimen_registry": selected_specimens,
        "assay_registry": selected_specimens,
        "clinical_outcome": selected_outcomes,
        "treatment_episode": selected_episodes,
        "treatment_exposure": selected_exposures,
    }
    id_fields = {"patient_registry": "patient_uid", "specimen_registry": "specimen_uid",
                 "assay_registry": "specimen_uid", "clinical_outcome": "outcome_id",
                 "treatment_episode": "treatment_episode_id", "treatment_exposure": "treatment_exposure_id"}
    for table, field in id_fields.items():
        if table in records:
            records[table] = [row for row in records[table] if row.get(field) in keep_ids[table]]
    if "episode_binding" in records:
        records["episode_binding"] = [row for row in records["episode_binding"]
            if row.get("treatment_episode_id") in selected_episodes
            and ((row.get("subject_type") == "SPECIMEN" and row.get("subject_id") in selected_specimens)
                 or (row.get("subject_type") == "CLINICAL_OUTCOME" and row.get("subject_id") in selected_outcomes)
                 or (row.get("subject_type") == "TREATMENT_EXPOSURE" and row.get("subject_id") in selected_exposures))]

    ingestion_value = current["config"].get("admission", {}).get("ingestion_worksheet", [])
    if isinstance(ingestion_value, dict):
        ingestion_value = ingestion_value.get("items", [])
    require(isinstance(ingestion_value, list), "BASELINE_WORKSHEET_INVALID")
    for row in records.get("clinical_outcome", []):
        raw = row.get("raw_endpoint_label")
        require(isinstance(raw, str) and raw in _CATEGORIES, "BASELINE_OUTCOME_CONFLICT")
        row["canonical_category"] = _CATEGORIES[raw]
        row["endpoint_class"] = "TUMOUR_RESPONSE"
        row["assessment_criteria"] = "RECIST v1.1 (Riaz et al., 2017)"
        row["best_overall_response"] = raw if raw in {"CR", "PR", "SD", "PD", "NE"} else "UNKNOWN"
        row["evaluability"] = "NOT_EVALUABLE" if raw == "NE" else "UNKNOWN" if row["canonical_category"] == "UNKNOWN" else "EVALUABLE"
        row["orr_mapping"] = (True if raw in {"CR", "PR"} else False if raw in {"SD", "PD"} else None)
        row["mapping_rule_version"] = POLICY_VERSION
        row["mapping_confidence"] = "PROBABLE"
        # Only the documented, non-substantive NE/UNK vocabulary pair is closed.
        # Other outcome disagreements remain unresolved and block endpoint mapping.
        source_patient_id = str(patients[row["patient_uid"]].get("source_patient_id", ""))
        row["discrepancy_status"] = ("RESOLVED" if raw == "NE" and
                                     _all_patient_disagreements_are_ne_unk(
                                         ingestion_value, source_patient_id,
                                         row.get("discrepancy_status")) else
                                     row.get("discrepancy_status", "NONE"))

    config = current["config"]
    config["endpoints"] = {
        "version": POLICY_VERSION,
        "classes": ["ORR"],
        "category_map": {"CR": "CR", "PR": "PR", "SD": "SD", "PD": "PD",
                         "NE": "NE", "UNKNOWN": "UNKNOWN", "UNK": "UNKNOWN"},
        "source_priority": [row["outcome_id"] for row in records.get("clinical_outcome", [])],
        "source_roles": {"BOR": "author_clinical_table", "GEO_response": "corroborating_only"},
        "assessment_criteria": "RECIST v1.1",
        "assessment_source_locator": ARTICLE_LOCATOR,
        "source_of_record_locator": AUTHOR_CLINICAL_LOCATOR,
        "corroborating_source_locator": GEO_LOCATOR,
    }
    admission = config.setdefault("admission", {})
    baseline_aliases = {str(alias) for specimen in records.get("specimen_registry", [])
                        for alias in specimen.get("raw_sample_aliases", [])}
    baseline_source_patients = {str(row.get("source_patient_id")) for row in records.get("patient_registry", [])}
    ingestion = admission.get("ingestion_worksheet", [])
    if isinstance(ingestion, dict):
        ingestion = ingestion.get("items", [])
    admission["ingestion_worksheet"] = _trim_questions(
        ingestion, baseline_aliases=baseline_aliases, nonbaseline_aliases=nonbaseline_aliases,
        baseline_source_patients=baseline_source_patients)
    admission.pop("reviewer_worksheet", None)
    admission.pop("worksheet_created_utc", None)
    current["dependencies"] = {}
    # Rebuild registry source mapping from the retained source inventory; do not carry
    # source_hashes from an earlier derived packet.
    admission_registry = config.setdefault("registries", {})
    admission_registry["study_ids"] = [row["study_id"] for row in records.get("study_registry", [])]
    admission_registry["source_hashes"] = {row["source_object_id"]: row["sha256"]
                                            for row in records.get("source_record", [])}
    current["records"] = records
    return current


def prepare_baseline(packet: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    """Build policy packet, then rebuild registries and metadata worksheet."""
    return prepare_review(build_baseline_packet(packet), output_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, type=Path, help="canonical local ingestion packet JSON")
    parser.add_argument("--out", required=True, type=Path, help="private output directory under .scratch/runtime")
    args = parser.parse_args(argv)
    try:
        prepare_baseline(_read_packet(args.packet), args.out)
    except DavError as error:
        parser.error(error.code)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
