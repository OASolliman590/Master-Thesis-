"""Invented public-API examples; no source objects or clinical acceptance."""
from copy import deepcopy

import pytest

from tools.a_dav.core import SchemaStore, public_summary
from tools.a_dav.registries import build_registries

SCHEMAS = SchemaStore()


def packet():
    loc = [{"kind": "INVENTED", "value": "synthetic-row"}]
    records = {
        "study_registry": [{"study_id": "s1", "publication_family_id": "f1", "study_title": "Invented", "study_class": "CLINICAL_ICI", "cancer_type": "invented", "study_design": "invented", "candidate_paper_branches": ["A_BASELINE_BIO"], "study_status": "RESOLVED", "source_locators": loc}],
        "publication_family": [{"publication_family_id": "f1", "study_id": "s1", "publication_id": "pub1", "publication_role": "PRIMARY_CLINICAL", "independence_status": "UNRESOLVED", "source_locators": loc}],
        "source_record": [{"source_object_id": "obj1", "study_id": "s1", "publication_family_id": "f1", "repository": "INVENTED", "object_type": "synthetic_matrix", "exact_file_name": "invented.tsv", "retrieval_status": "RETRIEVED", "validation_status": "PASS", "sha256": "a" * 64, "hash_scope": "FULL_OBJECT", "source_locators": loc}],
        "patient_registry": [{"patient_uid": "p1", "study_id": "s1", "source_patient_id": "001", "source_aliases": ["0001"], "patient_identity_confidence": "VERIFIED", "prior_ici": "NO", "treatment_naive_status": "VERIFIED_YES", "inclusion_state": "CANDIDATE", "source_locators": loc}],
        "specimen_registry": [{"specimen_uid": "sp1", "patient_uid": "p1", "raw_sample_aliases": ["sample-001"], "canonical_timing_category": "PRE_INDEX_BASELINE", "collection_date_or_day": "-2", "days_from_index_start": -2, "tissue_type": "invented", "biological_compartment": "TUMOUR", "lesion_site": "invented-a", "baseline_candidate_status": "YES", "longitudinal_pair_status": "PAIRABLE", "source_locators": loc}],
        "assay_registry": [{"assay_uid": "a1", "specimen_uid": "sp1", "source_sample_id": "sample-001", "source_object_id": "obj1", "modality": "RNA", "platform": "INVENTED", "measurement_unit": "counts", "transform": "NONE", "feature_annotation": "invented-v1", "matrix_header": "sample-001", "qc_status": "PASS", "replicate_status": "PRIMARY", "branch_suitability": ["BASELINE_DE"], "source_locators": loc}],
        "clinical_outcome": [{"outcome_id": "o1", "patient_uid": "p1", "raw_endpoint_label": "invented-partial", "endpoint_class": "TUMOUR_RESPONSE", "assessment_criteria": "INVENTED", "canonical_category": "PR", "orr_mapping": True, "dcr_mapping": True, "mapping_rule_version": "invented-v1", "mapping_confidence": "VERIFIED", "evaluability": "EVALUABLE", "discrepancy_status": "NONE", "source_locators": loc}],
        "treatment_episode": [{"schema_version": "1.1.0", "data_classification": "SYNTHETIC_ONLY", "treatment_episode_id": "e1", "patient_uid": "p1", "study_id": "s1", "regimen_id": "r1", "index_event": "invented-start", "start_day": 0, "stop_day": 60, "timing_precision": "EXACT", "prior_ici": "NO", "episode_status": "VERIFIED", "component_exposure_ids": ["x1"], "source_locators": ["invented-row"]}],
        "treatment_exposure": [{"treatment_exposure_id": "x1", "patient_uid": "p1", "regimen_id": "r1", "agent": "invented", "pharmacological_class": "ICI", "sequence": "1", "line_of_therapy": "1", "prior_ici": "NO", "certainty": "VERIFIED", "start_date_or_day": "0", "stop_date_or_day": "60", "source_locators": loc}],
        "episode_binding": []}
    for subject_type, subject_id, role in [("SPECIMEN", "sp1", "PRE_INDEX_BASELINE"), ("CLINICAL_OUTCOME", "o1", "OUTCOME_ASSESSMENT"), ("TREATMENT_EXPOSURE", "x1", "TREATMENT_COMPONENT")]:
        records["episode_binding"].append({"schema_version": "1.1.0", "data_classification": "SYNTHETIC_ONLY", "binding_id": "b" + subject_id, "patient_uid": "p1", "treatment_episode_id": "e1", "subject_type": subject_type, "subject_id": subject_id, "role": role, "binding_status": "VERIFIED", "source_locators": ["invented-row"], "reviewer": "invented-reader", "reviewed_utc": "2026-10-23"})
    return {"classification": "SYNTHETIC_ONLY", "branch_id": "A_BASELINE_BIO", "records": records, "config": {"registries": {"study_ids": ["s1"], "source_hashes": {"obj1": "a" * 64}}}, "schema_hashes": SCHEMAS.hashes, "dependencies": {}}


def test_registry_preserves_lexical_identity_and_all_records():
    p = packet()
    before = deepcopy(p)
    result = build_registries(p, schemas=SCHEMAS)
    assert result["status"] == "READY"
    assert result["records"]["patient_registry"][0]["source_patient_id"] == "001"
    assert {k: sorted(v, key=str) for k, v in result["records"].items()} == {k: sorted(v, key=str) for k, v in before["records"].items()}
    assert p == before
    assert "001" not in str(public_summary(result))


def test_registry_ambiguous_alias_fails():
    p = packet()
    other = deepcopy(p["records"]["patient_registry"][0]); other["patient_uid"] = "p2"
    p["records"]["patient_registry"].append(other)
    assert build_registries(p, schemas=SCHEMAS)["reasons"] == ["AMBIGUOUS_ALIAS"]


def endpoint_config(p):
    p["config"]["endpoints"] = {"version": "invented-v1", "category_map": {"invented-partial": "PR"}, "classes": ["ORR", "DCR"], "source_priority": ["o1"]}
    return p


def with_registries(p):
    p["dependencies"].pop("registries", None)
    p["dependencies"]["registries"] = build_registries(p, schemas=SCHEMAS)
    return p


def test_endpoint_raw_immutable_and_orr_dcr_literal():
    from tools.a_dav.endpoints import map_endpoints
    p = with_registries(endpoint_config(packet()))
    r = map_endpoints(p, schemas=SCHEMAS)
    assert r["status"] == "READY"
    assert [(x["endpoint_class"], x["binary_value"]) for x in sorted(r["records"]["endpoint"], key=lambda x: x["endpoint_class"])] == [("DCR", 1), ("ORR", 1)]
    assert r["records"]["clinical_outcome"] == p["records"]["clinical_outcome"]


def test_endpoint_source_binary_cannot_become_orr():
    from tools.a_dav.endpoints import map_endpoints
    p = endpoint_config(packet()); p["records"]["clinical_outcome"][0]["endpoint_class"] = "SOURCE_BINARY"
    r = map_endpoints(with_registries(p), schemas=SCHEMAS)
    assert r["status"] == "FAIL"
    assert r["reasons"] == ["INVALID_ENDPOINT_CONVERSION"]


def timing_config(p):
    p["config"]["timing"] = {"version": "invented-time-v1", "episode_order": ["e1"], "windows": {"invented-pre": {"category": "PRE_INDEX_BASELINE", "min_day": -5, "max_day": -1}}, "specimens": {"sp1": {"treatment_episode_id": "e1", "precision": "EXACT", "relative_day": -2, "canonical_category": "PRE_INDEX_BASELINE", "window_id": "invented-pre", "source_locator": "invented-row", "inferred_from_order": False}}}
    return p


def test_timing_preserves_rows_and_exact_day_evidence():
    from tools.a_dav.timing import validate_timing
    p = with_registries(timing_config(packet()))
    r = validate_timing(p, schemas=SCHEMAS)
    assert r["status"] == "READY"
    assert any(x.get("relative_day") == -2 and x.get("specimen_uid") == "sp1" for x in r["audit"])
    assert r["records"]["specimen_registry"] == p["records"]["specimen_registry"]


def test_timing_exact_day_contradiction_fails():
    from tools.a_dav.timing import validate_timing
    p = timing_config(packet()); p["config"]["timing"]["specimens"]["sp1"]["relative_day"] = -3
    r = validate_timing(with_registries(p), schemas=SCHEMAS)
    assert r["reasons"] == ["COLLECTION_CHRONOLOGY_CONFLICT"]


def assay_config(p):
    p["config"]["assays"] = {"required_features": ["F1", "F2"], "matrices": [{"source_object_id": "obj1", "source_sha256": "a" * 64, "headers": ["sample-001"], "features": ["F1", "F2"], "values": [[0], [2]], "unit": "counts", "transform": "NONE", "annotation": "invented-v1", "feature_universe": ["F1", "F2"], "feature_map": {"F1": "F1", "F2": "F2"}, "feature_scope": "COMPLETE", "normalization": "NONE", "lane": "COUNTS", "source_locator": "invented-row", "replicate_policy": "PRESERVE", "missingness_policy": "PRESERVE", "delimiter": "TAB", "encoding": "UTF-8", "platform": "INVENTED", "modality": "RNA", "library_properties": {"sample-001": {"library_size": 2, "source_locator": "invented-library"}}}]}
    return p


def test_assay_zero_is_observed_and_coverage_literal():
    from tools.a_dav.assays import validate_assays
    p = with_registries(assay_config(packet()))
    r = validate_assays(p, schemas=SCHEMAS)
    assert r["status"] == "READY"
    row = r["records"]["coverage"][0]
    assert row["required_genes"] == ["F1", "F2"]
    assert row["present_genes"] == ["F1", "F2"]
    assert row["missing_genes"] == []
    assert row["de_suitability"] == "PASS"
    assert any(x.get("missing_value_count") == 0 and x.get("zero_value_count") == 1 for x in r["audit"])


def test_assay_missing_is_not_zero():
    from tools.a_dav.assays import validate_assays
    p = assay_config(packet()); p["config"]["assays"]["matrices"][0]["values"][0][0] = None
    r = validate_assays(with_registries(p), schemas=SCHEMAS)
    assert r["status"] == "BLOCKED_UNKNOWN"
    assert r["records"]["coverage"][0]["missing_genes"] == ["F1"]
    assert any(x.get("missing_value_count") == 1 and x.get("zero_value_count") == 0 for x in r["audit"])


@pytest.mark.parametrize("change,reason", [("duplicate_patient", "DUPLICATE_ID"), ("numeric_id", "SCHEMA_INVALID"), ("missing_patient", "FOREIGN_KEY_UNRESOLVED"), ("source_hash", "SOURCE_CONTEXT_CONFLICT"), ("partial_hash", "SOURCE_CONTEXT_UNKNOWN"), ("cross_study_source", "FOREIGN_KEY_UNRESOLVED")])
def test_registry_adversarial_identity_and_source_context(change, reason):
    p = packet(); r = p["records"]
    if change == "duplicate_patient":
        r["patient_registry"].append(deepcopy(r["patient_registry"][0]))
    elif change == "numeric_id":
        r["patient_registry"][0]["source_patient_id"] = 1
    elif change == "missing_patient":
        r["specimen_registry"][0]["patient_uid"] = "absent"
    elif change == "source_hash":
        p["config"]["registries"]["source_hashes"]["obj1"] = "b" * 64
    elif change == "partial_hash":
        r["source_record"][0]["hash_scope"] = "HEADER_ONLY"
    else:
        r["source_record"][0]["study_id"] = "absent"
    assert build_registries(p, schemas=SCHEMAS)["reasons"] == [reason]


def test_registry_repeats_lesions_and_raw_ids_across_studies_are_preserved():
    p = packet(); r = p["records"]
    for table, idkey, newid in [("study_registry", "study_id", "s2"), ("publication_family", "publication_id", "pub2"), ("source_record", "source_object_id", "obj2"), ("patient_registry", "patient_uid", "p2")]:
        row = deepcopy(r[table][0]); row[idkey] = newid
        row["study_id"] = "s2"
        if "publication_family_id" in row:
            row["publication_family_id"] = "f2"
        r[table].append(row)
    p["config"]["registries"]["study_ids"].append("s2")
    p["config"]["registries"]["source_hashes"]["obj2"] = "a" * 64
    lesion = deepcopy(r["specimen_registry"][0]); lesion.update(specimen_uid="sp2", raw_sample_aliases=["sample-002"], lesion_site="invented-b")
    r["specimen_registry"].append(lesion)
    repeat = deepcopy(r["assay_registry"][0]); repeat.update(assay_uid="a2", matrix_header="repeat-001", replicate_status="REPEATED_SEQUENCING")
    r["assay_registry"].append(repeat)
    result = build_registries(p, schemas=SCHEMAS)
    assert result["status"] == "READY"
    assert len(result["records"]["patient_registry"]) == 2
    assert len(result["records"]["specimen_registry"]) == 2
    assert len(result["records"]["assay_registry"]) == 2


@pytest.mark.parametrize("category,orr,dcr,evaluable", [("CR", 1, 1, "EVALUABLE"), ("PR", 1, 1, "EVALUABLE"), ("SD", 0, 1, "EVALUABLE"), ("PD", 0, 0, "EVALUABLE"), ("NE", None, None, "NOT_EVALUABLE"), ("UNKNOWN", None, None, "UNKNOWN")])
def test_endpoint_all_source_categories(category, orr, dcr, evaluable):
    from tools.a_dav.endpoints import map_endpoints
    p = endpoint_config(packet()); o = p["records"]["clinical_outcome"][0]
    o.update(raw_endpoint_label="invented-" + category, canonical_category=category, orr_mapping=None if orr is None else bool(orr), dcr_mapping=None if dcr is None else bool(dcr), evaluability=evaluable)
    p["config"]["endpoints"]["category_map"] = {o["raw_endpoint_label"]: category}
    result = map_endpoints(with_registries(p), schemas=SCHEMAS)
    assert result["status"] == "READY"
    rows = {x["endpoint_class"]: x for x in result["records"]["endpoint"]}
    assert rows["ORR"]["binary_value"] == orr
    assert rows["DCR"]["binary_value"] == dcr
    assert rows["ORR"]["evaluability"] == evaluable


@pytest.mark.parametrize("source_class,target", [("PSA_RESPONSE", "ORR"), ("PATHOLOGICAL_RESPONSE", "ORR"), ("PFS", "ORR"), ("OS", "ORR")])
def test_endpoint_disallowed_conversion(source_class, target):
    from tools.a_dav.endpoints import map_endpoints
    p = endpoint_config(packet()); p["records"]["clinical_outcome"][0]["endpoint_class"] = source_class
    p["config"]["endpoints"]["classes"] = [target]
    assert map_endpoints(with_registries(p), schemas=SCHEMAS)["reasons"] == ["INVALID_ENDPOINT_CONVERSION"]


@pytest.mark.parametrize("source_class", ["PSA_RESPONSE", "PATHOLOGICAL_RESPONSE", "PFS", "OS", "SOURCE_BINARY"])
def test_endpoint_separate_non_orr_lanes(source_class):
    from tools.a_dav.endpoints import map_endpoints
    p = endpoint_config(packet()); o = p["records"]["clinical_outcome"][0]
    o.update(endpoint_class=source_class, canonical_category="NOT_APPLICABLE", orr_mapping=None, dcr_mapping=None)
    p["config"]["endpoints"]["classes"] = ["SOURCE_BINARY_UNKNOWN" if source_class == "SOURCE_BINARY" else source_class]
    p["config"]["endpoints"]["category_map"] = {o["raw_endpoint_label"]: "NOT_APPLICABLE"}
    if source_class in {"PFS", "OS"}:
        o.update(event_time=8, event_indicator=False, censoring="INVENTED_CENSORED")
    result = map_endpoints(with_registries(p), schemas=SCHEMAS)
    assert result["status"] == "READY"
    row = result["records"]["endpoint"][0]
    assert row["binary_value"] is None
    if source_class in {"PFS", "OS"}:
        assert row["event_time"] == 8 and row["event_indicator"] == 0


def test_endpoint_dcb_requires_source_rule_and_short_censor_is_unevaluable():
    from tools.a_dav.endpoints import map_endpoints
    p = endpoint_config(packet()); p["config"]["endpoints"]["classes"] = ["DCB"]
    assert map_endpoints(with_registries(p), schemas=SCHEMAS)["reasons"] == ["DCB_RULE_UNKNOWN"]
    p["config"]["endpoints"]["dcb_rule"] = {"unit": "days", "threshold": 7, "source_locator": "invented-duration-rule", "outcomes": {"o1": {"source_supported_rule": True, "benefit": False, "duration": 2, "censored": True}}}
    result = map_endpoints(with_registries(p), schemas=SCHEMAS)
    assert result["status"] == "READY"
    assert result["records"]["endpoint"][0]["binary_value"] is None
    assert result["records"]["endpoint"][0]["evaluability"] == "NOT_EVALUABLE"


def test_endpoint_discrepancies_require_explicit_priority_resolution_and_retain_both():
    from tools.a_dav.endpoints import map_endpoints
    p = endpoint_config(packet()); other = deepcopy(p["records"]["clinical_outcome"][0]); other.update(outcome_id="o2", raw_endpoint_label="invented-progressive", canonical_category="PD", orr_mapping=False, dcr_mapping=False, discrepancy_status="CONFLICT")
    p["records"]["clinical_outcome"].append(other)
    b = deepcopy(p["records"]["episode_binding"][1]); b.update(binding_id="bo2", subject_id="o2"); p["records"]["episode_binding"].append(b)
    p["config"]["endpoints"]["category_map"]["invented-progressive"] = "PD"; p["config"]["endpoints"]["source_priority"].append("o2")
    assert map_endpoints(with_registries(p), schemas=SCHEMAS)["reasons"] == ["ENDPOINT_SOURCE_CONFLICT"]
    p["config"]["endpoints"]["discrepancy_resolutions"] = {"p1:e1": {"preferred_outcome_id": "o1", "source_locator": "invented-priority-rule"}}
    result = map_endpoints(with_registries(p), schemas=SCHEMAS)
    assert result["status"] == "READY"
    assert len(result["records"]["clinical_outcome"]) == 2
    assert any(x.get("all_outcome_ids") == ["o1", "o2"] for x in result["audit"])


@pytest.mark.parametrize("change,reason", [("order_inference", "TIMEPOINT_ONLY_INFERRED_FROM_ORDER"), ("unknown_prior", "PRIOR_ICI_UNKNOWN"), ("negative_stop", "COLLECTION_CHRONOLOGY_CONFLICT"), ("wrong_episode", "EPISODE_BINDING_CONFLICT"), ("missing_component", "COMPONENT_CLOSURE_CONFLICT"), ("missing_window", "WINDOW_NOT_IDENTIFIABLE"), ("category_mismatch", "TIMING_MAPPING_CONFLICT"), ("regimen_mismatch", "TREATMENT_SEQUENCE_CONFLICT")])
def test_timing_adversarial_families(change, reason):
    from tools.a_dav.timing import validate_timing
    p = timing_config(packet()); cfg = p["config"]["timing"]; records = p["records"]
    if change == "order_inference":
        cfg["specimens"]["sp1"]["inferred_from_order"] = True
    elif change == "unknown_prior":
        records["treatment_episode"][0]["prior_ici"] = "UNKNOWN"
    elif change == "negative_stop":
        records["treatment_episode"][0]["stop_day"] = -1
    elif change == "wrong_episode":
        cfg["specimens"]["sp1"]["treatment_episode_id"] = "e-other"
    elif change == "missing_component":
        records["treatment_episode"][0]["component_exposure_ids"] = ["x-other"]
    elif change == "missing_window":
        cfg["windows"] = {}
    elif change == "category_mismatch":
        cfg["specimens"]["sp1"]["canonical_category"] = "EARLY_ON_TREATMENT"
    else:
        records["treatment_exposure"][0]["regimen_id"] = "r-other"
    result = validate_timing(with_registries(p), schemas=SCHEMAS)
    assert result["reasons"] == [reason]


def test_timing_bounded_interval_is_not_exact_and_row_order_is_invariant():
    from tools.a_dav.timing import validate_timing
    p = timing_config(packet()); evidence = p["config"]["timing"]["specimens"]["sp1"]
    evidence.update(precision="BOUNDED_INTERVAL", interval=[-3, -1]); evidence.pop("relative_day")
    p["records"]["specimen_registry"][0]["days_from_index_start"] = None
    p["records"]["specimen_registry"][0]["collection_date_or_day"] = None
    first = validate_timing(with_registries(p), schemas=SCHEMAS)
    assert first["status"] == "READY"
    assert first["audit"][0]["precision"] == "BOUNDED_INTERVAL"
    assert first["audit"][0]["relative_day"] is None
    for rows in p["records"].values():
        rows.reverse()
    second = validate_timing(with_registries(p), schemas=SCHEMAS)
    assert first == second


@pytest.mark.parametrize("category,role,day,reference_key", [("EARLY_ON_TREATMENT", "ON_TREATMENT", 2, None), ("LATE_ON_TREATMENT", "ON_TREATMENT", 8, None), ("PROGRESSION", "PROGRESSION", 15, "progression_days"), ("AFTER_REGIMEN_CHANGE", "AFTER_REGIMEN_CHANGE", 22, "regimen_change_days"), ("POST_DISCONTINUATION", "POST_TREATMENT", 65, None)])
def test_timing_followup_states_are_explicit_and_separate(category, role, day, reference_key):
    from tools.a_dav.timing import validate_timing
    p = timing_config(packet()); specimen = p["records"]["specimen_registry"][0]; cfg = p["config"]["timing"]
    specimen.update(canonical_timing_category=category, days_from_index_start=day, collection_date_or_day=str(day), baseline_candidate_status="NO")
    p["records"]["episode_binding"][0]["role"] = role
    cfg["specimens"]["sp1"].update(canonical_category=category, relative_day=day)
    cfg["windows"]["invented-pre"].update(category=category, min_day=day-1, max_day=day+1)
    if reference_key:
        cfg[reference_key] = {"e1": day - 1}
    result = validate_timing(with_registries(p), schemas=SCHEMAS)
    assert result["status"] == "READY"
    assert result["audit"][0]["canonical_category"] == category


def test_timing_on_treatment_after_regimen_change_fails():
    from tools.a_dav.timing import validate_timing
    p = timing_config(packet()); p["records"]["specimen_registry"][0].update(canonical_timing_category="EARLY_ON_TREATMENT", days_from_index_start=4, collection_date_or_day="4")
    p["records"]["episode_binding"][0]["role"] = "ON_TREATMENT"
    p["config"]["timing"]["specimens"]["sp1"].update(canonical_category="EARLY_ON_TREATMENT", relative_day=4)
    p["config"]["timing"]["regimen_change_days"] = {"e1": 3}
    assert validate_timing(with_registries(p), schemas=SCHEMAS)["reasons"] == ["FOLLOWUP_AFTER_REGIMEN_CHANGE"]


@pytest.mark.parametrize("change,reason", [("duplicate_header", "DUPLICATE_HEADER"), ("duplicate_feature", "DUPLICATE_FEATURE"), ("collision", "FEATURE_COLLISION"), ("negative", "ASSAY_SCALE_CONFLICT"), ("fractional_count", "ASSAY_SCALE_CONFLICT"), ("transformed_count", "ASSAY_SCALE_CONFLICT"), ("unknown_scale", "ASSAY_SCALE_UNKNOWN"), ("fpkm_as_tpm", "ASSAY_SCALE_CONFLICT"), ("tpm_as_counts", "ASSAY_SCALE_CONFLICT"), ("truncated_fpkm", "FEATURE_UNIVERSE_UNKNOWN"), ("qc_failure", "ASSAY_QC_FAILED"), ("header_mismatch", "ASSAY_SOURCE_CONFLICT"), ("annotation", "ASSAY_PLATFORM_CONFLICT")])
def test_assay_adversarial_measurement_families(change, reason):
    from tools.a_dav.assays import validate_assays
    p = assay_config(packet()); m = p["config"]["assays"]["matrices"][0]; a = p["records"]["assay_registry"][0]
    if change == "duplicate_header":
        m["headers"] *= 2
    elif change == "duplicate_feature":
        m["features"] = ["F1", "F1"]
    elif change == "collision":
        m["feature_map"]["F2"] = "F1"
    elif change == "negative":
        m["values"][0][0] = -1
    elif change == "fractional_count":
        m["values"][0][0] = 1.5
    elif change == "transformed_count":
        m["transform"] = "LOG2"
    elif change == "unknown_scale":
        m["unit"] = "UNREPORTED"
    elif change == "fpkm_as_tpm":
        m.update(unit="TPM", lane="CONTINUOUS"); a["measurement_unit"] = "FPKM"
    elif change == "tpm_as_counts":
        p["records"]["source_record"][0]["measurement_unit"] = "TPM"
    elif change == "truncated_fpkm":
        m.update(unit="FPKM", lane="CONTINUOUS", feature_universe=["F1", "F2", "F3"])
    elif change == "qc_failure":
        a["qc_status"] = "FAIL"
    elif change == "header_mismatch":
        m["headers"] = ["invented-wrong"]
    else:
        m["annotation"] = "other-annotation"
    result = validate_assays(with_registries(p), schemas=SCHEMAS)
    assert result["reasons"] == [reason]


@pytest.mark.parametrize("unit,lane,transform,values", [("counts", "COUNTS", "NONE", [[0], [2]]), ("estimated_counts", "COUNTS", "NONE", [[0.1], [2.3]]), ("TPM", "CONTINUOUS", "NONE", [[0.3], [2.3]]), ("FPKM", "CONTINUOUS", "NONE", [[0.3], [2.3]]), ("log_expression", "CONTINUOUS", "LOG2", [[-0.3], [2.3]]), ("array_intensity", "ARRAY", "NONE", [[0.3], [2.3]]), ("beta", "METHYLATION_BETA", "NONE", [[0.3], [0.8]]), ("M", "METHYLATION_M", "NONE", [[-0.3], [2.3]])])
def test_assay_declared_lanes_pass_without_coercion(unit, lane, transform, values):
    from tools.a_dav.assays import validate_assays
    p = assay_config(packet()); m = p["config"]["assays"]["matrices"][0]; a = p["records"]["assay_registry"][0]
    m.update(unit=unit, lane=lane, transform=transform, values=values, platform="INVENTED", quantifier="invented", estimated_count_structure="invented-fractional-counts", preprocessing="invented", probe_to_gene_policy="invented", batch_structure="invented", genome_build="invented", detection_p_provenance="invented", probe_filter_policy="invented", snp_policy="invented", cross_reactive_policy="invented", sex_chromosome_policy="invented")
    a.update(measurement_unit=unit, transform=transform)
    if lane.startswith("METHYLATION"):
        a["modality"] = m["modality"] = "METHYLATION"
    result = validate_assays(with_registries(p), schemas=SCHEMAS)
    assert result["status"] == "READY"
    assert result["records"]["coverage"][0]["expression_unit"] == unit
    assert result["records"]["assay_registry"][0]["measurement_unit"] == unit


def test_assay_targeted_panel_never_full_universe_de_and_missing_required_is_explicit():
    from tools.a_dav.assays import validate_assays
    p = assay_config(packet()); p["config"]["assays"]["matrices"][0]["feature_scope"] = "TARGETED"
    result = validate_assays(with_registries(p), schemas=SCHEMAS)
    assert result["status"] == "READY"
    assert result["records"]["coverage"][0]["de_suitability"] == "FAIL"
    p["config"]["assays"]["required_features"].append("F3")
    result = validate_assays(with_registries(p), schemas=SCHEMAS)
    assert result["status"] == "BLOCKED_UNKNOWN"
    assert result["records"]["coverage"][0]["missing_genes"] == ["F3"]
    assert result["records"]["coverage"][0]["scoring_suitability"] == "FAIL"


@pytest.mark.parametrize("api,config_fn", [("endpoints", endpoint_config), ("timing", timing_config), ("assays", assay_config)])
def test_group_a_downstream_rejects_tampered_or_stale_registry(api, config_fn):
    from tools.a_dav.endpoints import map_endpoints
    from tools.a_dav.timing import validate_timing
    from tools.a_dav.assays import validate_assays
    function = {"endpoints": map_endpoints, "timing": validate_timing, "assays": validate_assays}[api]
    p = with_registries(config_fn(packet()))
    p["dependencies"]["registries"]["status"] = "FAIL"
    assert function(p, schemas=SCHEMAS)["reasons"] == ["RECEIPT_TAMPERED"]
    p = with_registries(config_fn(packet())); p["config"][api]["invented_changed_config"] = True
    assert function(p, schemas=SCHEMAS)["reasons"] == ["DEPENDENCY_INVALID"]


def test_timing_component_start_can_be_delayed_within_episode():
    from tools.a_dav.timing import validate_timing
    p = timing_config(packet()); p["records"]["treatment_exposure"][0].update(start_date_or_day="1", stop_date_or_day="59")
    assert validate_timing(with_registries(p), schemas=SCHEMAS)["status"] == "READY"


def test_timing_unknown_precision_never_certifies_exact_window():
    from tools.a_dav.timing import validate_timing
    p = timing_config(packet()); e = p["config"]["timing"]["specimens"]["sp1"]
    e.update(precision="UNKNOWN", category_only_allowed=True); e.pop("relative_day")
    assert validate_timing(with_registries(p), schemas=SCHEMAS)["status"] == "BLOCKED_UNKNOWN"


def test_assay_missing_modality_platform_documentation_blocks():
    from tools.a_dav.assays import validate_assays
    p = assay_config(packet()); m = p["config"]["assays"]["matrices"][0]
    m.pop("platform", None); m.pop("modality", None)
    assert validate_assays(with_registries(p), schemas=SCHEMAS)["status"] == "BLOCKED_UNKNOWN"


def test_assay_count_library_properties_required():
    from tools.a_dav.assays import validate_assays
    p = assay_config(packet()); p["config"]["assays"]["matrices"][0].pop("library_properties", None)
    assert validate_assays(with_registries(p), schemas=SCHEMAS)["status"] == "BLOCKED_UNKNOWN"


def test_registry_present_schema_contradiction_beats_another_missing_assertion():
    p = packet(); p["records"]["patient_registry"][0].pop("patient_identity_confidence")
    p["records"]["specimen_registry"][0]["canonical_timing_category"] = "NOT_A_CATEGORY"
    assert build_registries(p, schemas=SCHEMAS)["status"] == "FAIL"
    assert build_registries(p, schemas=SCHEMAS)["reasons"] == ["SCHEMA_INVALID"]


def test_endpoint_supplied_binary_conflict_fails_without_mutating_source():
    from tools.a_dav.endpoints import map_endpoints
    p = endpoint_config(packet()); p["records"]["clinical_outcome"][0]["orr_mapping"] = False
    before = deepcopy(p["records"]["clinical_outcome"])
    result = map_endpoints(with_registries(p), schemas=SCHEMAS)
    assert result["reasons"] == ["ENDPOINT_MAPPING_CONFLICT"]
    assert result["records"]["clinical_outcome"] == before


@pytest.mark.parametrize("prior_ici,reverse_order,reason", [("NO", False, "TREATMENT_SEQUENCE_CONFLICT"), ("YES", True, "TREATMENT_SEQUENCE_CONFLICT"), ("YES", False, None)])
def test_timing_explicit_treatment_sequence_and_prior_ici(prior_ici, reverse_order, reason):
    from tools.a_dav.timing import validate_timing
    p = timing_config(packet()); records = p["records"]
    episode = deepcopy(records["treatment_episode"][0]); episode.update(treatment_episode_id="e2", regimen_id="r2", start_day=100, stop_day=160, prior_ici=prior_ici, component_exposure_ids=["x2"])
    exposure = deepcopy(records["treatment_exposure"][0]); exposure.update(treatment_exposure_id="x2", regimen_id="r2", sequence="2", prior_ici=prior_ici, start_date_or_day="100", stop_date_or_day="160")
    binding = deepcopy(records["episode_binding"][2]); binding.update(binding_id="bx2", treatment_episode_id="e2", subject_id="x2")
    records["treatment_episode"].append(episode); records["treatment_exposure"].append(exposure); records["episode_binding"].append(binding)
    p["config"]["timing"]["episode_order"] = ["e2", "e1"] if reverse_order else ["e1", "e2"]
    result = validate_timing(with_registries(p), schemas=SCHEMAS)
    assert result["status"] == ("READY" if reason is None else "FAIL")
    assert result["reasons"] == ([] if reason is None else [reason])


def test_timing_multiple_followups_are_all_retained_with_explicit_windows():
    from tools.a_dav.timing import validate_timing
    p = timing_config(packet()); records = p["records"]; cfg = p["config"]["timing"]
    for number, day in [(2, 2), (3, 3)]:
        specimen = deepcopy(records["specimen_registry"][0]); specimen.update(specimen_uid="sp" + str(number), raw_sample_aliases=["sample-00" + str(number)], canonical_timing_category="EARLY_ON_TREATMENT", collection_date_or_day=str(day), days_from_index_start=day, baseline_candidate_status="NO")
        binding = deepcopy(records["episode_binding"][0]); binding.update(binding_id="bsp" + str(number), subject_id=specimen["specimen_uid"], role="ON_TREATMENT")
        records["specimen_registry"].append(specimen); records["episode_binding"].append(binding)
        cfg["specimens"][specimen["specimen_uid"]] = {"treatment_episode_id": "e1", "precision": "EXACT", "relative_day": day, "canonical_category": "EARLY_ON_TREATMENT", "window_id": "invented-on", "source_locator": "invented-row", "inferred_from_order": False}
    cfg["windows"]["invented-on"] = {"category": "EARLY_ON_TREATMENT", "min_day": 1, "max_day": 4}
    result = validate_timing(with_registries(p), schemas=SCHEMAS)
    assert result["status"] == "READY"
    assert sorted(x["relative_day"] for x in result["audit"]) == [-2, 2, 3]
    assert len(result["records"]["specimen_registry"]) == 3


def test_assay_repeated_profiles_preserved_and_audited():
    from tools.a_dav.assays import validate_assays
    p = assay_config(packet()); assay = deepcopy(p["records"]["assay_registry"][0]); assay.update(assay_uid="a2", matrix_header="replicate-001", replicate_status="REPEATED_SEQUENCING")
    p["records"]["assay_registry"].append(assay)
    m = p["config"]["assays"]["matrices"][0]; m["headers"].append("replicate-001")
    m["library_properties"]["replicate-001"] = {"library_size": 2, "source_locator": "invented-replicate"}
    for row in m["values"]:
        row.append(row[0])
    result = validate_assays(with_registries(p), schemas=SCHEMAS)
    assert result["status"] == "READY"
    assert len(result["records"]["coverage"]) == 2
    assert any(x.get("check") == "IDENTICAL_PROFILE_RETAINED" and x["assay_uids"] == ["a1", "a2"] for x in result["audit"])


def test_assay_missing_to_zero_policy_is_rejected():
    from tools.a_dav.assays import validate_assays
    p = assay_config(packet()); p["config"]["assays"]["matrices"][0]["missingness_policy"] = "ZERO_FILL"
    assert validate_assays(with_registries(p), schemas=SCHEMAS)["status"] == "BLOCKED_UNKNOWN"


def test_group_a_actual_shared_source_structural_status_preserved():
    from tools.a_dav.assays import validate_assays
    p = assay_config(packet()); p["records"]["source_record"][0]["validation_status"] = "STRUCTURAL_ONLY"
    result = validate_assays(with_registries(p), schemas=SCHEMAS)
    assert result["status"] == "READY"
    assert result["records"]["source_record"][0]["validation_status"] == "STRUCTURAL_ONLY"
    assert result["source_admission"] is False


def test_endpoint_ne_cannot_carry_evaluable_source_assertion():
    from tools.a_dav.endpoints import map_endpoints
    p = endpoint_config(packet()); o = p["records"]["clinical_outcome"][0]
    o.update(canonical_category="NE", orr_mapping=None, dcr_mapping=None)
    p["config"]["endpoints"]["category_map"][o["raw_endpoint_label"]] = "NE"
    assert map_endpoints(with_registries(p), schemas=SCHEMAS)["status"] == "FAIL"


def test_assay_estimated_counts_require_quantifier_structure():
    from tools.a_dav.assays import validate_assays
    p = assay_config(packet()); m = p["config"]["assays"]["matrices"][0]
    m["unit"] = p["records"]["assay_registry"][0]["measurement_unit"] = "estimated_counts"
    assert validate_assays(with_registries(p), schemas=SCHEMAS)["status"] == "BLOCKED_UNKNOWN"


@pytest.mark.parametrize("component_start,component_stop", [("50", "10"), ("61", "60"), ("0", "-1"), ("-1", "10"), ("0", "61")])
def test_timing_component_interval_must_be_ordered_inside_episode(component_start, component_stop):
    from tools.a_dav.timing import validate_timing
    p = timing_config(packet())
    p["records"]["treatment_exposure"][0].update(start_date_or_day=component_start, stop_date_or_day=component_stop)
    result = validate_timing(with_registries(p), schemas=SCHEMAS)
    assert result["status"] == "FAIL"
    assert result["reasons"] == ["COLLECTION_CHRONOLOGY_CONFLICT"]
    assert result["analysis_ready"] is False and result["biological_analysis_executed"] is False


@pytest.mark.parametrize("missing_field", ["start_date_or_day", "stop_date_or_day"])
def test_timing_missing_component_date_is_unknown(missing_field):
    from tools.a_dav.timing import validate_timing
    p = timing_config(packet())
    p["records"]["treatment_exposure"][0][missing_field] = None
    result = validate_timing(with_registries(p), schemas=SCHEMAS)
    assert result["status"] == "BLOCKED_UNKNOWN"
    assert result["reasons"] == ["INDEX_TREATMENT_UNRESOLVED"]
    assert result["source_admission"] is False and result["statistical_release"] is False


def timing_shared_specimen_context_packet():
    p = timing_config(packet()); records = p["records"]
    records["specimen_registry"][0].update(canonical_timing_category="POST_TREATMENT", days_from_index_start=60, collection_date_or_day="60", baseline_candidate_status="NO")
    records["episode_binding"][0]["role"] = "POST_TREATMENT"
    episode = deepcopy(records["treatment_episode"][0]); episode.update(treatment_episode_id="e2", regimen_id="r2", start_day=60, stop_day=120, prior_ici="YES", component_exposure_ids=["x2"])
    exposure = deepcopy(records["treatment_exposure"][0]); exposure.update(treatment_exposure_id="x2", regimen_id="r2", sequence="2", prior_ici="YES", start_date_or_day="60", stop_date_or_day="120")
    component_binding = deepcopy(records["episode_binding"][2]); component_binding.update(binding_id="bx2", subject_id="x2", treatment_episode_id="e2")
    specimen_binding = deepcopy(records["episode_binding"][0]); specimen_binding.update(binding_id="bsp1-e2", treatment_episode_id="e2", role="PRE_INDEX_BASELINE")
    records["treatment_episode"].append(episode); records["treatment_exposure"].append(exposure)
    records["episode_binding"].extend([component_binding, specimen_binding])
    cfg = p["config"]["timing"]; cfg["episode_order"] = ["e1", "e2"]
    cfg["windows"] = {"invented-end": {"category": "POST_TREATMENT", "min_day": 60, "max_day": 60}, "invented-start": {"category": "PRE_INDEX_BASELINE", "min_day": 0, "max_day": 0}}
    cfg["specimens"]["sp1"] = {"canonical_context_episode_id": "e1", "contexts": {
        "e1": {"treatment_episode_id": "e1", "precision": "EXACT", "relative_day": 60, "canonical_category": "POST_TREATMENT", "window_id": "invented-end", "source_locator": "invented-end-binding", "inferred_from_order": False},
        "e2": {"treatment_episode_id": "e2", "precision": "EXACT", "relative_day": 0, "canonical_category": "PRE_INDEX_BASELINE", "window_id": "invented-start", "source_locator": "invented-start-binding", "inferred_from_order": False}}}
    return p


def test_timing_shared_specimen_keeps_separate_evidenced_episode_contexts():
    from tools.a_dav.timing import validate_timing
    p = timing_shared_specimen_context_packet(); before = deepcopy(p["records"]["specimen_registry"])
    first = validate_timing(with_registries(p), schemas=SCHEMAS)
    assert first["status"] == "READY"
    contexts = sorted((row["treatment_episode_id"], row["canonical_category"], row["relative_day"]) for row in first["audit"] if row["specimen_uid"] == "sp1")
    assert contexts == [("e1", "POST_TREATMENT", 60), ("e2", "PRE_INDEX_BASELINE", 0)]
    assert first["records"]["specimen_registry"] == before
    for rows in p["records"].values():
        rows.reverse()
    assert validate_timing(with_registries(p), schemas=SCHEMAS) == first


def test_timing_shared_specimen_missing_context_evidence_blocks():
    from tools.a_dav.timing import validate_timing
    p = timing_shared_specimen_context_packet()
    p["config"]["timing"]["specimens"]["sp1"]["contexts"].pop("e2")
    assert validate_timing(with_registries(p), schemas=SCHEMAS)["status"] == "BLOCKED_UNKNOWN"


def test_timing_duplicate_same_episode_context_fails():
    from tools.a_dav.timing import validate_timing
    p = timing_config(packet()); duplicate = deepcopy(p["records"]["episode_binding"][0]); duplicate["binding_id"] = "duplicate-same-context"
    p["records"]["episode_binding"].append(duplicate)
    assert validate_timing(with_registries(p), schemas=SCHEMAS)["reasons"] == ["EPISODE_BINDING_CONFLICT"]


def defined_source_binary_packet(binary_value=1):
    p = endpoint_config(packet()); outcome = p["records"]["clinical_outcome"][0]
    raw = "invented-positive" if binary_value else "invented-negative"
    outcome.update(endpoint_class="SOURCE_BINARY", raw_endpoint_label=raw, canonical_category="SOURCE_POSITIVE" if binary_value else "SOURCE_NEGATIVE", orr_mapping=None, dcr_mapping=None)
    cfg = p["config"]["endpoints"]
    cfg["classes"] = ["OTHER"]; cfg["category_map"] = {raw: outcome["canonical_category"]}
    cfg["binary_definitions"] = {"o1": {"name": "invented-binary-endpoint", "version": "invented-binary-v1", "source_locator": "invented-binary-rule", "raw_value_map": {"invented-positive": 1, "invented-negative": 0}}}
    return p


@pytest.mark.parametrize("binary_value", [0, 1])
def test_endpoint_explicit_defined_source_binary_separate_other_lane(binary_value):
    from tools.a_dav.endpoints import map_endpoints
    p = defined_source_binary_packet(binary_value); before = deepcopy(p["records"]["clinical_outcome"])
    result = map_endpoints(with_registries(p), schemas=SCHEMAS)
    assert result["status"] == "READY"
    row = result["records"]["endpoint"][0]
    assert (row["endpoint_class"], row["canonical_category"], row["binary_value"], row["evaluability"]) == ("OTHER", "SOURCE_BINARY", binary_value, "EVALUABLE")
    assert result["records"]["clinical_outcome"] == before
    assert any(x.get("check") == "SOURCE_BINARY_DEFINED" and x["definition_version"] == "invented-binary-v1" and x["source_locator"] == "invented-binary-rule" for x in result["audit"])
    assert result["source_admission"] is False and result["analysis_ready"] is False


@pytest.mark.parametrize("change,status", [("missing", "BLOCKED_UNKNOWN"), ("no_locator", "BLOCKED_UNKNOWN"), ("no_version", "BLOCKED_UNKNOWN"), ("contradictory", "FAIL"), ("boolean", "FAIL"), ("unmapped_raw", "BLOCKED_UNKNOWN")])
def test_endpoint_defined_source_binary_requires_consistent_explicit_definition(change, status):
    from tools.a_dav.endpoints import map_endpoints
    p = defined_source_binary_packet(); definitions = p["config"]["endpoints"]["binary_definitions"]
    if change == "missing":
        definitions.clear()
    elif change == "no_locator":
        definitions["o1"].pop("source_locator")
    elif change == "no_version":
        definitions["o1"].pop("version")
    elif change == "contradictory":
        definitions["o1"]["raw_value_map"]["invented-positive"] = 0
    elif change == "boolean":
        definitions["o1"]["raw_value_map"]["invented-positive"] = True
    else:
        definitions["o1"]["raw_value_map"].pop("invented-positive")
    assert map_endpoints(with_registries(p), schemas=SCHEMAS)["status"] == status


def test_endpoint_defined_source_binary_still_cannot_be_orr_or_dcr():
    from tools.a_dav.endpoints import map_endpoints
    p = defined_source_binary_packet(); p["config"]["endpoints"]["classes"] = ["ORR", "DCR"]
    assert map_endpoints(with_registries(p), schemas=SCHEMAS)["reasons"] == ["INVALID_ENDPOINT_CONVERSION"]
