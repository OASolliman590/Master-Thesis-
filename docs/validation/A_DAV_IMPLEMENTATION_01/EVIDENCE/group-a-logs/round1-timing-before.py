"""Evidence-bearing validation of immutable invented treatment and specimen timing."""
from __future__ import annotations

from typing import Any

from .core import SchemaStore, dependency, finish, require, stage_boundary

REASON_CODES = frozenset({"INDEX_TREATMENT_UNRESOLVED", "PRIOR_ICI_UNKNOWN", "TREATMENT_SEQUENCE_CONFLICT", "COLLECTION_CHRONOLOGY_CONFLICT", "TIMEPOINT_ONLY_INFERRED_FROM_ORDER", "FOLLOWUP_AFTER_REGIMEN_CHANGE", "PROGRESSION_DATE_UNKNOWN", "WINDOW_NOT_IDENTIFIABLE", "EPISODE_BINDING_CONFLICT", "COMPONENT_CLOSURE_CONFLICT", "TIMING_MAPPING_CONFLICT"})


def _number(value: Any) -> bool:
    return type(value) in {int, float}


@stage_boundary("timing")
def validate_timing(packet: dict[str, Any], *, schemas: SchemaStore | None = None) -> dict[str, Any]:
    assert schemas is not None
    dependency(packet, "registries", schemas)
    records = packet["records"]
    cfg = packet["config"].get("timing", {})
    episodes = {e["treatment_episode_id"]: e for e in records.get("treatment_episode", [])}
    patients = {p["patient_uid"]: p for p in records.get("patient_registry", [])}
    exposures = {e["treatment_exposure_id"]: e for e in records.get("treatment_exposure", [])}
    specimens = {s["specimen_uid"]: s for s in records.get("specimen_registry", [])}
    outcomes = {o["outcome_id"]: o for o in records.get("clinical_outcome", [])}
    bindings = records.get("episode_binding", [])
    require(bool(episodes), "INDEX_TREATMENT_UNRESOLVED", blocked=True)
    for episode in episodes.values():
        require(episode["episode_status"] != "CONFLICT", "TREATMENT_SEQUENCE_CONFLICT")
        if _number(episode.get("start_day")) and _number(episode.get("stop_day")):
            require(episode["start_day"] <= episode["stop_day"], "COLLECTION_CHRONOLOGY_CONFLICT")
        require(episode["patient_uid"] in patients and patients[episode["patient_uid"]]["study_id"] == episode["study_id"], "EPISODE_BINDING_CONFLICT")
    subject_tables = {"SPECIMEN": specimens, "CLINICAL_OUTCOME": outcomes, "TREATMENT_EXPOSURE": exposures}
    occupied: set[tuple[str, str]] = set()
    for binding in bindings:
        require(binding["binding_status"] != "CONFLICT", "EPISODE_BINDING_CONFLICT")
        require(binding["treatment_episode_id"] in episodes and binding["subject_id"] in subject_tables[binding["subject_type"]], "EPISODE_BINDING_CONFLICT")
        episode = episodes[binding["treatment_episode_id"]]
        subject = subject_tables[binding["subject_type"]][binding["subject_id"]]
        require(binding["patient_uid"] == subject["patient_uid"] == episode["patient_uid"], "EPISODE_BINDING_CONFLICT")
        key = (binding["subject_type"], binding["subject_id"])
        require(key not in occupied, "EPISODE_BINDING_CONFLICT")
        occupied.add(key)
        if binding["subject_type"] == "TREATMENT_EXPOSURE":
            require(subject["regimen_id"] == episode["regimen_id"], "TREATMENT_SEQUENCE_CONFLICT")
            require(subject["prior_ici"] == episode["prior_ici"] or "UNKNOWN" in {subject["prior_ici"], episode["prior_ici"]}, "TREATMENT_SEQUENCE_CONFLICT")
            for field, ep_field in (("start_date_or_day", "start_day"), ("stop_date_or_day", "stop_day")):
                if subject.get(field) is not None and episode.get(ep_field) is not None:
                    try:
                        parsed = float(subject[field])
                    except ValueError:
                        continue
                    require((parsed >= episode[ep_field] if ep_field == "start_day" else parsed <= episode[ep_field]), "COLLECTION_CHRONOLOGY_CONFLICT")
    for episode_id, episode in episodes.items():
        expected = episode.get("component_exposure_ids")
        require(isinstance(expected, list) and bool(expected), "INDEX_TREATMENT_UNRESOLVED", blocked=True)
        actual = {b["subject_id"] for b in bindings if b["treatment_episode_id"] == episode_id and b["subject_type"] == "TREATMENT_EXPOSURE"}
        require(set(expected) == actual and all(x in exposures for x in expected), "COMPONENT_CLOSURE_CONFLICT")
    for specimen_id, specimen in specimens.items():
        evidence = cfg.get("specimens", {}).get(specimen_id, {})
        require(evidence.get("inferred_from_order") is not True, "TIMEPOINT_ONLY_INFERRED_FROM_ORDER")
        if "canonical_category" in evidence:
            require(evidence["canonical_category"] == specimen["canonical_timing_category"], "TIMING_MAPPING_CONFLICT")
        if _number(evidence.get("relative_day")) and _number(specimen.get("days_from_index_start")):
            require(evidence["relative_day"] == specimen["days_from_index_start"], "COLLECTION_CHRONOLOGY_CONFLICT")
    require(occupied == {(kind, key) for kind, subjects in subject_tables.items() for key in subjects}, "INDEX_TREATMENT_UNRESOLVED", blocked=True)
    require(all(e["certainty"] != "DISPROVED" for e in exposures.values()), "TREATMENT_SEQUENCE_CONFLICT")
    require(bool(cfg.get("version")), "WINDOW_NOT_IDENTIFIABLE", blocked=True)
    order = cfg.get("episode_order", [])
    require(set(order) == set(episodes) and len(order) == len(episodes), "INDEX_TREATMENT_UNRESOLVED", blocked=True)
    previous: dict[str, dict[str, Any]] = {}
    for episode_id in order:
        episode = episodes[episode_id]
        prior = previous.get(episode["patient_uid"])
        if prior is not None:
            require(prior.get("start_day") is not None and episode.get("start_day") is not None, "INDEX_TREATMENT_UNRESOLVED", blocked=True)
            require(prior["start_day"] < episode["start_day"], "TREATMENT_SEQUENCE_CONFLICT")
            require(episode["prior_ici"] != "NO" or not any(exposures[x]["pharmacological_class"] == "ICI" for x in prior["component_exposure_ids"]), "TREATMENT_SEQUENCE_CONFLICT")
        previous[episode["patient_uid"]] = episode
    audit: list[dict[str, Any]] = []
    for specimen_id, specimen in specimens.items():
        evidence = cfg.get("specimens", {}).get(specimen_id, {})
        require(evidence.get("inferred_from_order") is not True, "TIMEPOINT_ONLY_INFERRED_FROM_ORDER")
        require(evidence.get("canonical_category", specimen["canonical_timing_category"]) == specimen["canonical_timing_category"], "TIMING_MAPPING_CONFLICT")
        relevant = [b for b in bindings if b["subject_type"] == "SPECIMEN" and b["subject_id"] == specimen_id]
        require(len(relevant) == 1 and relevant[0]["binding_status"] == "VERIFIED", "INDEX_TREATMENT_UNRESOLVED", blocked=True)
        binding = relevant[0]
        require(evidence.get("treatment_episode_id") == binding["treatment_episode_id"], "EPISODE_BINDING_CONFLICT")
        episode = episodes[binding["treatment_episode_id"]]
        require(evidence.get("source_locator") and evidence.get("precision") in {"EXACT", "BOUNDED_INTERVAL", "SOURCE_CATEGORY", "UNKNOWN"}, "WINDOW_NOT_IDENTIFIABLE", blocked=True)
        precision = evidence["precision"]
        require(precision != "UNKNOWN", "WINDOW_NOT_IDENTIFIABLE", blocked=True)
        day = evidence.get("relative_day")
        canonical_day = specimen.get("days_from_index_start")
        if _number(day) and _number(canonical_day):
            require(day == canonical_day, "COLLECTION_CHRONOLOGY_CONFLICT")
        if precision == "EXACT":
            require(_number(day), "WINDOW_NOT_IDENTIFIABLE", blocked=True)
            if specimen.get("collection_date_or_day") is not None and episode.get("start_day") is not None:
                try:
                    collection_day = float(specimen["collection_date_or_day"])
                except ValueError:
                    collection_day = None
                if collection_day is not None:
                    require(collection_day - episode["start_day"] == day, "COLLECTION_CHRONOLOGY_CONFLICT")
            low = high = day
        elif precision == "BOUNDED_INTERVAL":
            interval = evidence.get("interval")
            require(isinstance(interval, list) and len(interval) == 2 and all(_number(x) for x in interval), "WINDOW_NOT_IDENTIFIABLE", blocked=True)
            low, high = interval
            require(low <= high, "COLLECTION_CHRONOLOGY_CONFLICT")
            require(canonical_day is None or low <= canonical_day <= high, "COLLECTION_CHRONOLOGY_CONFLICT")
        else:
            low = high = None
        category = specimen["canonical_timing_category"]
        if category == "PRE_INDEX_BASELINE" and high is not None:
            require(high <= 0 and binding["role"] == "PRE_INDEX_BASELINE", "COLLECTION_CHRONOLOGY_CONFLICT")
        if category in {"EARLY_ON_TREATMENT", "LATE_ON_TREATMENT"} and low is not None:
            require(low >= 0 and binding["role"] == "ON_TREATMENT", "COLLECTION_CHRONOLOGY_CONFLICT")
            change = cfg.get("regimen_change_days", {}).get(episode["treatment_episode_id"])
            if _number(change):
                require(high < change, "FOLLOWUP_AFTER_REGIMEN_CHANGE")
            progression = cfg.get("progression_days", {}).get(episode["treatment_episode_id"])
            if _number(progression):
                require(high < progression, "COLLECTION_CHRONOLOGY_CONFLICT")
            if episode.get("stop_day") is not None and episode.get("start_day") is not None:
                require(high <= episode["stop_day"] - episode["start_day"], "COLLECTION_CHRONOLOGY_CONFLICT")
        if category in {"PROGRESSION", "AFTER_REGIMEN_CHANGE", "POST_TREATMENT", "POST_DISCONTINUATION"}:
            require(binding["role"] == ("POST_TREATMENT" if category == "POST_DISCONTINUATION" else category), "TIMING_MAPPING_CONFLICT")
            reference = cfg.get("progression_days" if category == "PROGRESSION" else "regimen_change_days", {}).get(episode["treatment_episode_id"]) if category in {"PROGRESSION", "AFTER_REGIMEN_CHANGE"} else None if episode.get("stop_day") is None or episode.get("start_day") is None else episode["stop_day"] - episode["start_day"]
            require(_number(reference), "PROGRESSION_DATE_UNKNOWN" if category == "PROGRESSION" else "WINDOW_NOT_IDENTIFIABLE", blocked=True)
            if low is not None:
                require(low >= reference, "COLLECTION_CHRONOLOGY_CONFLICT")
        if low is not None:
            window = cfg.get("windows", {}).get(evidence.get("window_id"), {})
            require(window.get("category") == category and _number(window.get("min_day")) and _number(window.get("max_day")), "WINDOW_NOT_IDENTIFIABLE", blocked=True)
            require(window["min_day"] <= window["max_day"], "TIMING_MAPPING_CONFLICT")
            require(window["min_day"] <= low <= high <= window["max_day"], "WINDOW_NOT_IDENTIFIABLE", blocked=True)
        else:
            require(category != "UNKNOWN" and evidence.get("category_only_allowed") is True, "WINDOW_NOT_IDENTIFIABLE", blocked=True)
        audit.append({"check": "TIMING_ASSERTION", "specimen_uid": specimen_id, "treatment_episode_id": episode["treatment_episode_id"], "canonical_category": category, "precision": precision, "relative_day": day, "interval": [low, high], "window_id": evidence.get("window_id"), "mapping_version": cfg["version"]})
    require(all(e["episode_status"] == "VERIFIED" for e in episodes.values()) and all(b["binding_status"] == "VERIFIED" for b in bindings), "INDEX_TREATMENT_UNRESOLVED", blocked=True)
    require(all(e["prior_ici"] != "UNKNOWN" for e in episodes.values()) and all(e["prior_ici"] != "UNKNOWN" for e in exposures.values()), "PRIOR_ICI_UNKNOWN", blocked=True)
    require(all(e["certainty"] == "VERIFIED" and bool(e["sequence"]) and bool(e["line_of_therapy"]) for e in exposures.values()), "INDEX_TREATMENT_UNRESOLVED", blocked=True)
    for patient_id, patient in patients.items():
        require(not (patient.get("prior_ici") == "YES" and patient["treatment_naive_status"] == "VERIFIED_YES"), "TREATMENT_SEQUENCE_CONFLICT")
        first = next((episodes[e] for e in order if episodes[e]["patient_uid"] == patient_id), None)
        if first is not None and patient.get("prior_ici") not in {None, "UNKNOWN"}:
            require(patient["prior_ici"] == first["prior_ici"], "TREATMENT_SEQUENCE_CONFLICT")
    return finish("timing", packet, records, audit=audit, schemas=schemas)
