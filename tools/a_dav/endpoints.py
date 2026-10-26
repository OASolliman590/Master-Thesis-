"""Source-preserving, explicitly configured synthetic endpoint materialization."""
from __future__ import annotations

import copy
from typing import Any

from .core import SchemaStore, dependency, digest, finish, require, stage_boundary

REASON_CODES = frozenset({"INVALID_ENDPOINT_CONVERSION", "ENDPOINT_MAPPING_UNKNOWN", "ENDPOINT_MAPPING_CONFLICT", "ENDPOINT_SOURCE_CONFLICT", "DCB_RULE_UNKNOWN", "ENDPOINT_EPISODE_UNKNOWN", "SOURCE_BINARY_DEFINITION_UNKNOWN", "SOURCE_BINARY_DEFINITION_CONFLICT"})


@stage_boundary("endpoints")
def map_endpoints(packet: dict[str, Any], *, schemas: SchemaStore | None = None) -> dict[str, Any]:
    assert schemas is not None
    dependency(packet, "registries", schemas)
    records = copy.deepcopy(packet["records"])
    cfg = packet["config"].get("endpoints", {})
    require(isinstance(cfg.get("version"), str) and bool(cfg["version"]), "ENDPOINT_MAPPING_UNKNOWN", blocked=True)
    classes = cfg.get("classes", [])
    require(bool(classes), "ENDPOINT_MAPPING_UNKNOWN", blocked=True)
    require(len(classes) == len(set(classes)) and set(classes) <= {"ORR", "DCR", "DCB", "PSA_RESPONSE", "PATHOLOGICAL_RESPONSE", "PFS", "OS", "SOURCE_BINARY_UNKNOWN", "OTHER"}, "INVALID_ENDPOINT_CONVERSION")
    category_map = cfg.get("category_map", {})
    priority = cfg.get("source_priority", [])
    outcomes = records.get("clinical_outcome", [])
    for outcome in outcomes:
        raw = outcome["raw_endpoint_label"]
        if raw in category_map:
            require(category_map[raw] == outcome["canonical_category"], "ENDPOINT_MAPPING_CONFLICT")
        source_class = outcome["endpoint_class"]
        allowed = {"TUMOUR_RESPONSE": {"ORR", "DCR", "DCB"}, "SOURCE_BINARY": {"SOURCE_BINARY_UNKNOWN", "OTHER"}}.get(source_class, {source_class, "OTHER"})
        require(bool(set(classes) & allowed), "INVALID_ENDPOINT_CONVERSION")
    require(set(priority) == {o["outcome_id"] for o in outcomes} and len(priority) == len(outcomes), "ENDPOINT_MAPPING_UNKNOWN", blocked=True)
    views: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    by_patient: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for outcome in outcomes:
        schemas.validate("clinical_outcome", outcome)
        raw = outcome["raw_endpoint_label"]
        require(raw in category_map, "ENDPOINT_MAPPING_UNKNOWN", blocked=True)
        category = category_map[raw]
        require(category == outcome["canonical_category"] and outcome["mapping_rule_version"] == cfg["version"], "ENDPOINT_MAPPING_CONFLICT")
        bindings = [b for b in records.get("episode_binding", []) if b["subject_type"] == "CLINICAL_OUTCOME" and b["subject_id"] == outcome["outcome_id"]]
        require(len(bindings) == 1 and bindings[0]["binding_status"] == "VERIFIED", "ENDPOINT_EPISODE_UNKNOWN", blocked=True)
        require(bindings[0]["patient_uid"] == outcome["patient_uid"], "ENDPOINT_MAPPING_CONFLICT")
        episode_id = bindings[0]["treatment_episode_id"]
        source_class = outcome["endpoint_class"]
        by_patient.setdefault((outcome["patient_uid"], episode_id, source_class), []).append(outcome)
        source_category = category in {"CR", "PR", "SD", "PD", "NE", "UNKNOWN"}
        require(category not in {"NE", "UNKNOWN"} or outcome.get("evaluability") != "EVALUABLE", "ENDPOINT_MAPPING_CONFLICT")
        allowed_targets = {"TUMOUR_RESPONSE": {"ORR", "DCR", "DCB"}, "SOURCE_BINARY": {"SOURCE_BINARY_UNKNOWN", "OTHER"}}.get(source_class, {source_class, "OTHER"})
        targets = [target for target in classes if target in allowed_targets]
        require(bool(targets), "INVALID_ENDPOINT_CONVERSION")
        for endpoint_class in targets:
            if endpoint_class in {"ORR", "DCR"}:
                require(source_class in {"TUMOUR_RESPONSE", endpoint_class} and source_category, "INVALID_ENDPOINT_CONVERSION")
            elif endpoint_class == "SOURCE_BINARY_UNKNOWN":
                require(source_class == "SOURCE_BINARY", "INVALID_ENDPOINT_CONVERSION")
            elif endpoint_class != "DCB":
                require(source_class == endpoint_class or endpoint_class == "OTHER", "INVALID_ENDPOINT_CONVERSION")
            binary: int | None = None
            evaluability = outcome.get("evaluability", "UNKNOWN")
            threshold: float | int | None = None
            if endpoint_class in {"ORR", "DCR"}:
                if category in {"NE", "UNKNOWN"}:
                    evaluability = "NOT_EVALUABLE" if category == "NE" else "UNKNOWN"
                elif evaluability == "EVALUABLE":
                    binary = int(category in ({"CR", "PR"} if endpoint_class == "ORR" else {"CR", "PR", "SD"}))
                supplied = outcome.get("orr_mapping" if endpoint_class == "ORR" else "dcr_mapping")
                require(supplied is None or binary is not None and supplied == bool(binary), "ENDPOINT_MAPPING_CONFLICT")
            elif endpoint_class == "DCB":
                rule = cfg.get("dcb_rule", {})
                require(rule.get("unit") == "days" and isinstance(rule.get("threshold"), (int, float)) and rule["threshold"] >= 0 and bool(rule.get("source_locator")), "DCB_RULE_UNKNOWN", blocked=True)
                evidence = rule.get("outcomes", {}).get(outcome["outcome_id"], {})
                require(evidence.get("source_supported_rule") is True and type(evidence.get("benefit")) is bool and type(evidence.get("censored")) is bool and type(evidence.get("duration")) in {int, float}, "DCB_RULE_UNKNOWN", blocked=True)
                require(source_class in {"TUMOUR_RESPONSE", "DCB"}, "INVALID_ENDPOINT_CONVERSION")
                threshold = rule["threshold"]
                duration = evidence["duration"]
                require(duration >= 0, "ENDPOINT_MAPPING_CONFLICT")
                if duration < threshold and evidence.get("censored") is True:
                    evaluability = "NOT_EVALUABLE"
                else:
                    require(duration >= threshold or evidence["benefit"] is False, "ENDPOINT_MAPPING_CONFLICT")
                    binary = int(evidence["benefit"])
                    evaluability = "EVALUABLE"
                require(outcome.get("dcb_mapping") is None or binary is not None and outcome["dcb_mapping"] == bool(binary), "ENDPOINT_MAPPING_CONFLICT")
            elif endpoint_class == "OTHER" and source_class == "SOURCE_BINARY":
                definition = cfg.get("binary_definitions", {}).get(outcome["outcome_id"], {})
                require(all(isinstance(definition.get(field), str) and bool(definition[field]) for field in ("name", "version", "source_locator")), "SOURCE_BINARY_DEFINITION_UNKNOWN", blocked=True)
                value_map = definition.get("raw_value_map", {})
                require(isinstance(value_map, dict), "SOURCE_BINARY_DEFINITION_CONFLICT")
                require(all(isinstance(key, str) and type(value) is int and value in {0, 1} for key, value in value_map.items()), "SOURCE_BINARY_DEFINITION_CONFLICT")
                require(raw in value_map, "SOURCE_BINARY_DEFINITION_UNKNOWN", blocked=True)
                require(category in {"SOURCE_POSITIVE", "SOURCE_NEGATIVE"}, "SOURCE_BINARY_DEFINITION_CONFLICT")
                require(value_map[raw] == int(category == "SOURCE_POSITIVE"), "SOURCE_BINARY_DEFINITION_CONFLICT")
                require(outcome.get("orr_mapping") is None and outcome.get("dcr_mapping") is None, "INVALID_ENDPOINT_CONVERSION")
                require(evaluability == "EVALUABLE", "SOURCE_BINARY_DEFINITION_UNKNOWN", blocked=True)
                binary = value_map[raw]
                audit.append({"check": "SOURCE_BINARY_DEFINED", "patient_uid": outcome["patient_uid"], "treatment_episode_id": episode_id, "outcome_id": outcome["outcome_id"], "definition_name": definition["name"], "definition_version": definition["version"], "source_locator": definition["source_locator"]})
            elif endpoint_class == "SOURCE_BINARY_UNKNOWN":
                evaluability = "UNKNOWN"
            elif endpoint_class in {"PFS", "OS"}:
                require(outcome.get("event_time") is not None and type(outcome.get("event_indicator")) is bool and bool(outcome.get("censoring")), "ENDPOINT_MAPPING_UNKNOWN", blocked=True)
            row = {"row_type": "ENDPOINT", "schema_version": "1.1.0", "data_classification": packet["classification"], "patient_uid": outcome["patient_uid"], "treatment_episode_id": episode_id, "outcome_id": outcome["outcome_id"], "endpoint_id": endpoint_class + ":" + outcome["outcome_id"], "endpoint_class": endpoint_class, "raw_value": raw, "canonical_category": ("UNK" if category == "UNKNOWN" else category) if source_category else "SOURCE_BINARY" if source_class == "SOURCE_BINARY" else "NOT_APPLICABLE", "assessment_system": outcome["assessment_criteria"], "assessment_day": cfg.get("assessment_days", {}).get(outcome["outcome_id"]), "binary_value": binary, "duration_threshold": threshold, "event_time": outcome.get("event_time"), "event_indicator": None if outcome.get("event_indicator") is None else int(outcome["event_indicator"]), "censoring": outcome.get("censoring"), "evaluability": evaluability, "mapping_version": cfg["version"], "source_locator": outcome["source_locators"][0]["value"], "build_receipt_id": "synthetic:" + digest(cfg)}
            schemas.validate("endpoint", row)
            views.append(row)
    for key, assertions in by_patient.items():
        conflict = len({o["canonical_category"] for o in assertions}) > 1 or any(o.get("discrepancy_status") in {"CONFLICT", "UNRESOLVED"} for o in assertions)
        if conflict:
            resolution = cfg.get("discrepancy_resolutions", {}).get(key[0] + ":" + key[1], {})
            winner = min(assertions, key=lambda o: priority.index(o["outcome_id"]))["outcome_id"]
            require(resolution.get("preferred_outcome_id") == winner and bool(resolution.get("source_locator")), "ENDPOINT_SOURCE_CONFLICT", blocked=True)
            audit.append({"check": "DISCREPANCY_RETAINED", "patient_uid": key[0], "treatment_episode_id": key[1], "preferred_outcome_id": winner, "all_outcome_ids": sorted(o["outcome_id"] for o in assertions)})
    records["endpoint"] = views
    audit.append({"check": "RAW_OUTCOMES_PRESERVED", "mapping_version": cfg["version"], "endpoint_count": len(views)})
    return finish("endpoints", packet, records, audit=audit, schemas=schemas)
