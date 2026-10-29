"""Build canonical treatment, binding, overlap and exposure proposals from field-map data."""
from __future__ import annotations

import copy
from typing import Any

from .admission import evaluate_admission
from .assays import validate_assays
from .core import SchemaStore, require
from .endpoints import map_endpoints
from .exposure import validate_exposure
from .overlap import validate_overlap
from .registries import build_registries
from .timing import validate_timing
from .worksheet import validate_signed_worksheet


def _render(template: str, **values: str) -> str:
    try:
        result = template.format(**values)
    except (KeyError, ValueError):
        raise ValueError("PROPOSAL_ID_TEMPLATE_INVALID") from None
    require(bool(result), "PROPOSAL_ID_TEMPLATE_INVALID")
    return result


def _signed_decisions(packet: dict[str, Any], worksheet: dict[str, Any] | None) -> dict[str, Any] | None:
    return validate_signed_worksheet(packet, worksheet) if worksheet is not None else None


def materialize_proposals(packet: dict[str, Any], declaration: dict[str, Any], *,
                          reviewer_worksheet: dict[str, Any] | None = None,
                          context_reviewer_identity: dict[str, str] | None = None,
                          rebuild_worksheet_context: bool = False,
                          schemas: SchemaStore | None = None) -> dict[str, Any]:
    """Materialize declared canonical records; only a validated V5 sign-off verifies bindings."""
    store = schemas or SchemaStore()
    signature = None if rebuild_worksheet_context else _signed_decisions(packet, reviewer_worksheet)
    if rebuild_worksheet_context and reviewer_worksheet is not None:
        raw_signature = reviewer_worksheet.get("signature", {})
        raw_decisions = reviewer_worksheet.get("decisions", [])
        if isinstance(raw_signature, dict) and isinstance(raw_decisions, list):
            status_by_id = {row.get("item_id"): row.get("status") for row in raw_decisions
                            if isinstance(row, dict)}
            signature = {"reviewer_name": raw_signature.get("reviewer_name"),
                         "review_date": raw_signature.get("review_date"),
                         "decisions": status_by_id}
    v5_signed = signature is not None and signature["decisions"].get("V5") == "PASS"
    v6_signed = signature is not None and signature["decisions"].get("V6") == "PASS"
    context_reviewer = context_reviewer_identity or {}
    context_name = context_reviewer.get("reviewer_name", "")
    context_date = context_reviewer.get("review_date", "")
    records = copy.deepcopy(packet["records"])
    episode_cfg = declaration["episode"]
    exposure_cfg = declaration["exposure"]
    binding_cfg = declaration["binding"]
    patients = records.get("patient_registry", [])
    study_by_id = {row["study_id"]: row for row in records.get("study_registry", [])}
    family_ids = sorted({row["publication_family_id"] for row in study_by_id.values()})
    require(len(family_ids) == 1, "PROPOSAL_STUDY_FAMILY_AMBIGUOUS")

    episodes: list[dict[str, Any]] = []
    exposures: list[dict[str, Any]] = []
    episode_by_patient: dict[str, dict[str, Any]] = {}
    for patient in patients:
        prior_raw = patient.get(exposure_cfg["prior_ici_field"])
        prior_ici = exposure_cfg["prior_ici_map"].get(prior_raw)
        require(prior_ici in {"YES", "NO", "UNKNOWN"}, "PRIOR_ICI_UNKNOWN", blocked=True)
        episode_id = _render(episode_cfg["id_template"], patient_uid=patient["patient_uid"],
                             study_id=patient["study_id"])
        exposure_id = _render(exposure_cfg["id_template"], patient_uid=patient["patient_uid"],
                              study_id=patient["study_id"])
        episode = {"schema_version": "1.1.0", "data_classification": packet["classification"],
                   "treatment_episode_id": episode_id, "patient_uid": patient["patient_uid"],
                   "study_id": patient["study_id"], "regimen_id": episode_cfg["regimen_id"],
                   "index_event": episode_cfg["index_event"], "start_day": episode_cfg.get("start_day"),
                   "stop_day": episode_cfg.get("stop_day"),
                   "start_source_text": episode_cfg.get("start_source_text"),
                   "stop_source_text": episode_cfg.get("stop_source_text"),
                   "timing_precision": episode_cfg["timing_precision"], "prior_ici": prior_ici,
                   "episode_status": episode_cfg["episode_status"],
                   "component_exposure_ids": [exposure_id],
                   "source_locators": list(episode_cfg["source_locators"]),
                   "notes": episode_cfg.get("notes")}
        exposure = {"schema_version": "1.0.0", "data_classification": "PRIVATE_PATIENT_LEVEL",
                    "treatment_exposure_id": exposure_id, "patient_uid": patient["patient_uid"],
                    "regimen_id": exposure_cfg["regimen_id"], "agent": exposure_cfg["agent"],
                    "pharmacological_class": exposure_cfg["pharmacological_class"],
                    "checkpoint_target": exposure_cfg.get("checkpoint_target"),
                    "monotherapy_or_combination": exposure_cfg["monotherapy_or_combination"],
                    "combination_components": list(exposure_cfg.get("combination_components", [])),
                    "sequence": exposure_cfg["sequence"], "line_of_therapy": exposure_cfg.get("line_of_therapy"),
                    "dose_schedule": exposure_cfg.get("dose_schedule"),
                    "start_date_or_day": exposure_cfg.get("start_date_or_day"),
                    "stop_date_or_day": exposure_cfg.get("stop_date_or_day"), "prior_ici": prior_ici,
                    "prior_systemic_therapy": exposure_cfg.get("prior_systemic_therapy", "UNKNOWN"),
                    "concomitant_therapy": exposure_cfg.get("concomitant_therapy"),
                    "steroid_immunosuppressant_exposure": exposure_cfg.get("steroid_immunosuppressant_exposure"),
                    "progression_discontinuation_relationship": exposure_cfg.get("progression_discontinuation_relationship"),
                    "certainty": exposure_cfg["certainty"],
                    "source_locators": copy.deepcopy(exposure_cfg["source_locators"])}
        store.validate("treatment_episode", episode)
        store.validate("treatment_exposure", exposure)
        episodes.append(episode)
        exposures.append(exposure)
        episode_by_patient[patient["patient_uid"]] = episode

    reviewer = signature["reviewer_name"] if v5_signed and signature is not None else None
    reviewed = signature["review_date"] if v5_signed and signature is not None else None
    binding_status = "VERIFIED" if v5_signed else "BLOCKED_UNKNOWN"
    signer_note = "; signer identity SELF_REPORTED" if v5_signed else None
    bindings: list[dict[str, Any]] = []
    subjects: list[tuple[str, dict[str, Any]]] = []
    subjects.extend(("TREATMENT_EXPOSURE", row) for row in exposures)
    subjects.extend(("SPECIMEN", row) for row in records.get("specimen_registry", []))
    subjects.extend(("CLINICAL_OUTCOME", row) for row in records.get("clinical_outcome", []))
    for subject_type, subject in subjects:
        patient_id = subject["patient_uid"]
        episode = episode_by_patient[patient_id]
        role = binding_cfg["role_by_subject_type"][subject_type]
        binding = {"schema_version": "1.1.0", "data_classification": packet["classification"],
                   "binding_id": _render(binding_cfg["id_template"], subject_type=subject_type,
                                          subject_id=subject.get("outcome_id", subject.get("specimen_uid",
                                                                subject.get("treatment_exposure_id", "")))),
                   "patient_uid": patient_id, "treatment_episode_id": episode["treatment_episode_id"],
                   "subject_type": subject_type,
                   "subject_id": subject.get("outcome_id", subject.get("specimen_uid",
                                                        subject.get("treatment_exposure_id", ""))),
                   "role": role, "binding_status": binding_status,
                   "source_locators": list(binding_cfg["source_locators"]),
                   "reviewer": reviewer, "reviewed_utc": reviewed,
                   "reason": signer_note or "Awaiting a validated signed worksheet with V5 PASS."}
        store.validate("episode_binding", binding)
        bindings.append(binding)

    rows: dict[str, list[dict[str, Any]]] = {"treatment_episode": episodes,
        "treatment_exposure": exposures, "episode_binding": bindings}
    overlap_cfg = declaration.get("overlap")
    if overlap_cfg is not None:
        study = next(iter(study_by_id.values()))
        edge = {"schema_version": "1.0.0", "overlap_edge_id": overlap_cfg["edge_id"],
                "source_node_type": "STUDY", "source_node_id": study["study_id"],
                "target_node_type": overlap_cfg["external_node"]["node_type"],
                "target_node_id": overlap_cfg["external_node"]["node_id"],
                "edge_type": overlap_cfg["edge_type"], "evidence": overlap_cfg["evidence"],
                "source_locators": copy.deepcopy(overlap_cfg["source_locators"]),
                "certainty": overlap_cfg["certainty"],
                "implication_for_independence": overlap_cfg["implication_for_independence"],
                "reviewer": signature["reviewer_name"] if v6_signed and signature is not None else context_name,
                "review_date": signature["review_date"] if v6_signed and signature is not None else context_date,
                "notes": overlap_cfg.get("notes")}
        store.validate("overlap_edge", edge)
        rows["overlap_edge"] = [edge]
    else:
        rows["overlap_edge"] = []

    prior_cfg = declaration["prior_exposure"]
    prior_rows: list[dict[str, Any]] = []
    for family_id in family_ids:
        row = {"schema_version": "1.1.0", "exposure_id": prior_cfg["id"],
               "subject_type": prior_cfg["subject_type"], "subject_id": family_id,
               "analysis_lineage_id": prior_cfg["analysis_lineage_id"],
               "fields_accessed": list(prior_cfg["fields_accessed"]), "use": prior_cfg["use"],
               "occurred_utc": prior_cfg.get("occurred_utc"), "date_precision": prior_cfg["date_precision"],
               "actor_role": prior_cfg["actor_role"],
               "independence_implication": prior_cfg["independence_implication"],
               "source_locators": list(prior_cfg["source_locators"]),
               "reviewer": signature["reviewer_name"] if v6_signed and signature is not None else context_name or None,
               "notes": prior_cfg.get("notes")}
        store.validate("prior_exposure_record", row)
        prior_rows.append(row)
    rows["prior_exposure_record"] = prior_rows
    records.update(rows)
    output = copy.deepcopy(packet)
    output["records"] = records
    declared_stage_config = copy.deepcopy(declaration.get("stage_config", {}))
    timing_config = declared_stage_config.get("timing", {})
    timing_config["version"] = declaration["timing"]["version"]
    timing_config["index_event"] = declaration["timing"]["index_event"]
    timing_config["episode_order"] = [row["treatment_episode_id"] for row in episodes]
    timing_config["allow_undated_treatment_exposure_ids"] = [row["treatment_exposure_id"] for row in exposures
                                                               if row["start_date_or_day"] is None and
                                                               row["stop_date_or_day"] is None]
    timing_config["specimens"] = {
        specimen["specimen_uid"]: {
            "treatment_episode_id": episode_by_patient[specimen["patient_uid"]]["treatment_episode_id"],
            "precision": "SOURCE_CATEGORY", "canonical_category": specimen["canonical_timing_category"],
            "source_locator": declaration["timing"]["source_locator"], "inferred_from_order": False,
            "category_only_allowed": True,
        } for specimen in records.get("specimen_registry", [])}
    declared_stage_config["timing"] = timing_config
    if overlap_cfg is not None:
        overlap_stage = declared_stage_config.setdefault("overlap", {})
        overlap_stage["review_complete"] = v6_signed
        overlap_stage["external_nodes"] = [copy.deepcopy(overlap_cfg["external_node"])]
    exposure_stage = declared_stage_config.setdefault("exposure", {})
    exposure_stage["analysis_lineage_id"] = prior_cfg["analysis_lineage_id"]
    exposure_stage["review_complete"] = v6_signed
    exposure_stage["covered_subjects"] = [{"subject_type": "STUDY_FAMILY", "subject_id": family_ids[0]}]
    admission_config = declared_stage_config.get("admission", {})
    required_roles = admission_config.pop("required_source_roles", [])
    if required_roles:
        source_ids = packet.get("config", {}).get("registries", {}).get("source_roles", {})
        require(isinstance(required_roles, list) and all(role in source_ids for role in required_roles),
                "REQUIRED_SOURCE_MISSING", blocked=True)
        admission_config["required_source_object_ids"] = [source_ids[role] for role in required_roles]
    required_hashes = admission_config.pop("required_source_hashes", [])
    if required_hashes:
        source_ids = {row.get("sha256"): row["source_object_id"]
                      for row in records.get("source_record", []) if row.get("sha256")}
        require(set(required_hashes) <= set(source_ids), "REQUIRED_SOURCE_MISSING", blocked=True)
        admission_config["required_source_object_ids"] = [source_ids[value] for value in required_hashes]
    declared_stage_config["admission"] = admission_config
    if "split" in declared_stage_config:
        declared_stage_config["split"]["required_source_ids"] = copy.deepcopy(
            admission_config.get("required_source_object_ids", output["config"].get("admission", {}).get("required_source_object_ids", [])))
    baseline_config = declared_stage_config.get("baseline")
    if isinstance(baseline_config, dict) and baseline_config.get("ranking") == "UNIQUE_CANDIDATE":
        baseline_config["specimen_rank"] = {row["specimen_uid"]: 0 for row in records.get("specimen_registry", [])}
        baseline_config["assay_rank"] = {row["assay_uid"]: 0 for row in records.get("assay_registry", [])}
    resolution_cfg = declaration.get("endpoint_discrepancy_resolution")
    if resolution_cfg is not None and signature is not None and reviewer_worksheet is not None:
        item_by_id = {item.get("item_id"): item for item in reviewer_worksheet.get("items", [])}
        decisions = {decision["item_id"]: decision["status"]
                     for decision in reviewer_worksheet.get("decisions", [])}
        relevant_items = [item for item in item_by_id.values()
                          if item.get("category") == resolution_cfg["worksheet_item_category"]]
        if relevant_items and all(decisions.get(item["item_id"]) == "PASS" for item in relevant_items):
            priority = output["config"].get("endpoints", {}).get("source_priority", [])
            rank = {outcome_id: index for index, outcome_id in enumerate(priority)}
            by_patient: dict[str, list[dict[str, Any]]] = {}
            for outcome in records.get("clinical_outcome", []):
                by_patient.setdefault(outcome["patient_uid"], []).append(outcome)
            resolutions = output["config"].setdefault("endpoints", {}).setdefault("discrepancy_resolutions", {})
            for patient_id, outcomes_for_patient in by_patient.items():
                episode_id = episode_by_patient[patient_id]["treatment_episode_id"]
                winner = min(outcomes_for_patient, key=lambda outcome: rank.get(outcome["outcome_id"], len(rank)))
                resolutions[f"{patient_id}:{episode_id}"] = {
                    "preferred_outcome_id": winner["outcome_id"],
                    "source_locator": resolution_cfg["source_locator"],
                }
    for section, section_config in declared_stage_config.items():
        if isinstance(output["config"].get(section), dict):
            output["config"][section].update(section_config)
        else:
            output["config"][section] = section_config
    return output


def run_admission_chain(packet: dict[str, Any], declaration: dict[str, Any], *,
                        reviewer_worksheet: dict[str, Any],
                        worksheet_context_packet: dict[str, Any] | None = None,
                        collect_blockers: bool = False,
                        schemas: SchemaStore | None = None) -> dict[str, Any]:
    """Run the declared evidence stages in dependency order through admission."""
    store = schemas or SchemaStore()
    current = copy.deepcopy(packet)
    current["dependencies"] = {}
    statuses: list[dict[str, Any]] = []
    functions = (build_registries, map_endpoints, validate_timing, validate_assays,
                 validate_overlap, validate_exposure)
    for function in functions:
        stage = function(current, schemas=store)
        statuses.append({"stage": stage["stage"], "status": stage["status"], "reasons": stage["reasons"]})
        if stage["status"] == "READY":
            current["records"] = stage["records"]
        if stage["status"] != "READY":
            if collect_blockers:
                continue
            current["records"] = stage["records"]
            admission = evaluate_admission(current, reviewer_worksheet=reviewer_worksheet,
                                           worksheet_context_packet=worksheet_context_packet, schemas=store)
            statuses.append({"stage": admission["stage"], "status": admission["status"],
                             "reasons": admission["reasons"]})
            current["records"] = admission["records"]
            return {"packet": current, "stage_statuses": statuses, "admission": admission}
        current["dependencies"][stage["stage"]] = stage
    admission = evaluate_admission(current, reviewer_worksheet=reviewer_worksheet,
                                   worksheet_context_packet=worksheet_context_packet, schemas=store)
    statuses.append({"stage": admission["stage"], "status": admission["status"],
                     "reasons": admission["reasons"]})
    current["records"] = admission["records"]
    if admission["status"] == "READY":
        current["dependencies"]["admission"] = admission
    return {"packet": current, "stage_statuses": statuses, "admission": admission}
