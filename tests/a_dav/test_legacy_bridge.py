"""Adversarial checks for the synthetic-only legacy bridge."""
import hashlib
import json
from pathlib import Path

from tools.a_dav.legacy_bridge import build_legacy_candidate, public_summary

ROOT = Path(__file__).resolve().parents[2]
LEGACY = ROOT.parent / "paper-a-batch-pipeline"
SCHEMAS = ROOT / "specs/A_DATA_ACQUISITION_VALIDATION/schemas"
FIXTURE = Path(__file__).parent / "fixtures/legacy_bridge/synthetic_metadata.json"


def sha(data): return hashlib.sha256(data).hexdigest()


def anchor(meta):
    from batchqual.patient import schema as S
    allowed=set(S.COLUMNS)-{"assay_value","feature","gate_status"}
    th={t:sha(S.canonical_table(meta["tables"],t)) for t in allowed}
    ch={n:sha((LEGACY/"batchqual/patient"/n).read_bytes()) for n in ("contract.py","schema.py","builder.py","auditor.py")}
    return S.digest({"classification":"SYNTHETIC_ONLY","table_hashes":th,"source_code_hashes":ch})


def reanchor(meta,supp):
    from batchqual.patient import schema as S
    allowed=set(S.COLUMNS)-{"assay_value","feature","gate_status"}
    hashes={t:sha(S.canonical_table(meta["tables"],t)) for t in allowed}
    meta["producer_hashes"]=dict(hashes); meta["auditor_hashes"]=dict(hashes)
    meta["source_code_hashes"]={n:sha((LEGACY/"batchqual/patient"/n).read_bytes()) for n in ("contract.py","schema.py","builder.py","auditor.py")}
    supp["legacy_metadata_sha256"]=anchor(meta)


def bundle(unresolved=()):
    from batchqual.patient import schema as S
    seed=json.loads(FIXTURE.read_text())
    tables={t:[] for t in set(S.COLUMNS)-{"assay_value","feature","gate_status"}}
    tables.update(json.loads(json.dumps(seed["legacy_table_rows"])))
    hashes={t:sha(S.canonical_table(tables,t)) for t in tables}
    source={n:sha((LEGACY/"batchqual/patient"/n).read_bytes()) for n in ("contract.py","schema.py","builder.py","auditor.py")}
    metadata={"classification":seed["classification"],"tables":tables,"producer_hashes":hashes,"auditor_hashes":dict(hashes),"source_code_hashes":source}
    records=json.loads(json.dumps(seed["canonical_records"]))
    schema_hashes={t:sha((SCHEMAS/(t+".schema.json")).read_bytes()) for t in records}
    supplement={"classification":seed["classification"],"records":records,"links":json.loads(json.dumps(seed["links"])),"unresolved":list(unresolved),"schema_hashes":schema_hashes}
    supplement["legacy_metadata_sha256"]=anchor(metadata)
    return metadata,supplement


def test_explicit_links_preserve_lexical_ids_and_repeats():
    meta,supp=bundle()
    from batchqual.patient import schema as S
    meta["tables"]["source_object"]=[{"object_id":"obj-1","study_id":"legacy-study","locator":"invented","sha256":None,"bytes":None,"format":None,"licence":None,"custody_manifest_sha":None}]
    meta["tables"]["assay"]=[{"assay_id":a,"source_object_id":"obj-1","native_label":"001","platform":None,"native_unit":"unknown","declared_transform":None,"qc_flags":None} for a in ("assay-a","assay-b")]
    for t in ("source_object","assay"):
        ah=sha(S.canonical_table(meta["tables"],t)); meta["producer_hashes"][t]=ah; meta["auditor_hashes"][t]=ah
    meta["tables"]["specimen"]=[{"specimen_id":f"lesion-{i}","person_key":"person-001","site":None,"tissue":"tumour","collection_rel_days":None,"rule_id":"rule-1","source_label":f"sample-{i}"} for i in (1,2)]
    sh=sha(S.canonical_table(meta["tables"],"specimen")); meta["producer_hashes"]["specimen"]=sh; meta["auditor_hashes"]["specimen"]=sh
    reanchor(meta,supp)
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    person=next(x for x in result["lineage"] if x["legacy_table"]=="person")
    assert person["raw_fields"]["source_label"] == "001"
    assert person["canonical_key"] == "patient-001"
    assert result["status"] == "BLOCKED_UNKNOWN"
    assert sum(1 for x in result["lineage"] if x["legacy_table"]=="assay") == 2
    assert sum(1 for x in result["lineage"] if x["legacy_table"]=="specimen") == 2


def test_structural_candidate_is_not_admission():
    meta,supp=bundle()
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"] == "STRUCTURAL_CANDIDATE"
    assert not any(result[k] for k in ("analysis_ready","source_admission","statistical_release","biological_analysis_executed"))
    assert "INCLUDED" not in str(result["records"])


def test_unknown_timing_unit_and_protection_remain_unresolved():
    meta,supp=bundle(["E04","E06","E07"])
    meta["tables"]["treatment_episode"]=[{"episode_id":"legacy-ep","person_key":"person-001","regimen":"invented","agents":None,"line":None,"start_rel_days":None,"rule_id":"rule-001"}]
    meta["tables"]["analysis_unit"]=[{"estimand_id":"estimand-1","person_key":"person-001","episode_id":"legacy-ep","specimen_id":None,"assay_id":None,"selection_rule_id":"rule-001","frozen_manifest_sha":"invented"}]
    from batchqual.patient import schema as S
    for t in ("treatment_episode","analysis_unit"):
        h=sha(S.canonical_table(meta["tables"],t)); meta["producer_hashes"][t]=h; meta["auditor_hashes"][t]=h
    reanchor(meta,supp)
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"] == "BLOCKED_UNKNOWN"
    assert next(x for x in result["lineage"] if x["legacy_table"]=="treatment_episode")["raw_fields"]["start_rel_days"] is None
    assert next(x for x in result["dispositions"] if x["legacy_table"]=="analysis_unit")["state"] == "SUPPORT_ONLY"
    assert not any(result[k] for k in ("analysis_ready","source_admission","statistical_release","biological_analysis_executed"))


def test_hash_schema_alias_and_review_shortcuts_fail():
    meta,supp=bundle()
    meta["tables"]["person"][0]["source_label"]="sentinel-private-id"
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"] == "FAIL"
    summary=public_summary(result)
    assert "sentinel-private-id" not in json.dumps(summary)
    meta,supp=bundle(); supp["records"]["patient_registry"][0]["inclusion_state"]="INCLUDED"
    assert build_legacy_candidate(meta,supp,schema_root=SCHEMAS)["reason_counts"]=={"ADMISSION_STATE_NOT_ALLOWED":1}
    meta,supp=bundle(); meta["tables"]["assay_value"]=[]
    assert build_legacy_candidate(meta,supp,schema_root=SCHEMAS)["reason_counts"]=={"UNSUPPORTED_INPUT_TABLE":1}


def test_unknown_unit_and_changed_transform_conflict_with_canonical_assay():
    meta,supp=bundle()
    from batchqual.patient import schema as S
    meta["tables"]["source_object"]=[{"object_id":"legacy-object","study_id":"legacy-study","locator":None,"sha256":"a"*64,"bytes":32,"format":"tsv","licence":None,"custody_manifest_sha":None}]
    meta["tables"]["specimen"]=[{"specimen_id":"legacy-specimen","person_key":"person-001","site":None,"tissue":"tumour","collection_rel_days":None,"rule_id":"rule-1","source_label":"sample-1"}]
    meta["tables"]["assay"]=[{"assay_id":"legacy-assay","source_object_id":"legacy-object","native_label":"sample-1","platform":"native","native_unit":"UNKNOWN","declared_transform":"log2","qc_flags":None}]
    meta["tables"]["assay_specimen"]=[{"assay_id":"legacy-assay","specimen_id":"legacy-specimen","relation":"unknown","rule_id":"rule-1"}]
    for t in ("source_object","specimen","assay","assay_specimen"):
        h=sha(S.canonical_table(meta["tables"],t)); meta["producer_hashes"][t]=h; meta["auditor_hashes"][t]=h
    supp["records"]["source_record"]=[{"source_object_id":"dav-object","study_id":"study-001","publication_family_id":"family-001","repository":"invented","object_type":"matrix","exact_file_name":"invented.tsv","retrieval_status":"LOCATED","validation_status":"STRUCTURAL_ONLY","sha256":"a"*64,"source_locators":[{"kind":"fixture","value":"invented"}]}]
    supp["records"]["specimen_registry"]=[{"specimen_uid":"dav-specimen","patient_uid":"patient-001","raw_sample_aliases":["sample-1"],"canonical_timing_category":"UNKNOWN","tissue_type":"UNKNOWN","biological_compartment":"UNKNOWN","baseline_candidate_status":"UNKNOWN","longitudinal_pair_status":"UNKNOWN","source_locators":[{"kind":"fixture","value":"invented"}]}]
    supp["records"]["assay_registry"]=[{"assay_uid":"dav-assay","specimen_uid":"dav-specimen","source_sample_id":"sample-1","source_object_id":"dav-object","modality":"RNA","platform":"invented","measurement_unit":"TPM","transform":"log1p","matrix_header":"sample-1","qc_status":"NOT_EVALUATED","branch_suitability":["UNSUPPORTED"],"source_locators":[{"kind":"fixture","value":"invented"}]}]
    supp["links"].extend([{"legacy_table":"source_object","legacy_key":"legacy-object","canonical_table":"source_record","canonical_key":"dav-object","evidence_refs":["fixture"]},{"legacy_table":"specimen","legacy_key":"legacy-specimen","canonical_table":"specimen_registry","canonical_key":"dav-specimen","evidence_refs":["fixture"]},{"legacy_table":"assay","legacy_key":"legacy-assay","canonical_table":"assay_registry","canonical_key":"dav-assay","evidence_refs":["fixture"]}])
    reanchor(meta,supp)
    assert build_legacy_candidate(meta,supp,schema_root=SCHEMAS)["reason_counts"]=={"RAW_VALUE_CONFLICT":1}


def test_linked_source_object_hash_mismatch_is_detected_in_isolation():
    meta,supp=bundle()
    from batchqual.patient import schema as S
    meta["tables"]["source_object"]=[{"object_id":"legacy-object","study_id":"legacy-study","locator":None,"sha256":"a"*64,"bytes":32,"format":"tsv","licence":None,"custody_manifest_sha":None}]
    meta["tables"]["specimen"]=[{"specimen_id":"legacy-specimen","person_key":"person-001","site":None,"tissue":"tumour","collection_rel_days":None,"rule_id":"rule-1","source_label":"sample-1"}]
    meta["tables"]["assay"]=[{"assay_id":"legacy-assay","source_object_id":"legacy-object","native_label":"sample-1","platform":"native","native_unit":"UNKNOWN","declared_transform":"UNKNOWN","qc_flags":None}]
    meta["tables"]["assay_specimen"]=[{"assay_id":"legacy-assay","specimen_id":"legacy-specimen","relation":"unknown","rule_id":"rule-1"}]
    for t in ("source_object","specimen","assay","assay_specimen"):
        h=sha(S.canonical_table(meta["tables"],t)); meta["producer_hashes"][t]=h; meta["auditor_hashes"][t]=h
    supp["records"]["source_record"]=[{"source_object_id":"dav-object","study_id":"study-001","publication_family_id":"family-001","repository":"invented","object_type":"matrix","exact_file_name":"invented.tsv","retrieval_status":"LOCATED","validation_status":"STRUCTURAL_ONLY","sha256":"a"*64,"source_locators":[{"kind":"fixture","value":"invented"}]}]
    supp["records"]["specimen_registry"]=[{"specimen_uid":"dav-specimen","patient_uid":"patient-001","raw_sample_aliases":["sample-1"],"canonical_timing_category":"UNKNOWN","tissue_type":"UNKNOWN","biological_compartment":"UNKNOWN","baseline_candidate_status":"UNKNOWN","longitudinal_pair_status":"UNKNOWN","source_locators":[{"kind":"fixture","value":"invented"}]}]
    supp["records"]["assay_registry"]=[{"assay_uid":"dav-assay","specimen_uid":"dav-specimen","source_sample_id":"sample-1","source_object_id":"dav-object","modality":"RNA","platform":"invented","measurement_unit":"UNKNOWN","transform":"UNKNOWN","matrix_header":"sample-1","qc_status":"NOT_EVALUATED","branch_suitability":["UNSUPPORTED"],"source_locators":[{"kind":"fixture","value":"invented"}]}]
    supp["links"].extend([
        {"legacy_table":"source_object","legacy_key":"legacy-object","canonical_table":"source_record","canonical_key":"dav-object","evidence_refs":["fixture"]},
        {"legacy_table":"specimen","legacy_key":"legacy-specimen","canonical_table":"specimen_registry","canonical_key":"dav-specimen","evidence_refs":["fixture"]},
        {"legacy_table":"assay","legacy_key":"legacy-assay","canonical_table":"assay_registry","canonical_key":"dav-assay","evidence_refs":["fixture"]}])
    reanchor(meta,supp)
    assert build_legacy_candidate(meta,supp,schema_root=SCHEMAS)["status"]=="STRUCTURAL_CANDIDATE"
    supp["records"]["source_record"][0]["sha256"]="b"*64
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="FAIL" and result["reason_counts"]=={"RAW_VALUE_CONFLICT":1}


def test_public_summary_and_failures_exclude_private_details():
    meta,supp=bundle()
    original=json.dumps((meta,supp),sort_keys=True)
    supp["classification"]="PRIVATE_PATIENT_LEVEL"
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"] == "FAIL"
    assert "PRIVATE_PATIENT_LEVEL" not in json.dumps(public_summary(result))
    assert original != json.dumps((meta,supp),sort_keys=True)


def test_missing_supplement_blocks_without_invented_fields():
    meta,supp=bundle(["E01"])
    del supp["records"]["patient_registry"][0]["source_patient_id"]
    from batchqual.patient import schema as S
    meta["tables"]["specimen"]=[{"specimen_id":"spec-legacy","person_key":"person-001","site":None,"tissue":None,"collection_rel_days":None,"rule_id":"rule-001","source_label":"sample-1"}]
    h=sha(S.canonical_table(meta["tables"],"specimen")); meta["producer_hashes"]["specimen"]=h; meta["auditor_hashes"]["specimen"]=h
    supp["records"]["specimen_registry"]=[{"specimen_uid":"spec-001","patient_uid":"patient-001","raw_sample_aliases":["sample-1"],"canonical_timing_category":"UNKNOWN","tissue_type":"UNKNOWN","biological_compartment":"UNKNOWN","baseline_candidate_status":"UNKNOWN","longitudinal_pair_status":"UNKNOWN","source_locators":[{"kind":"fixture","value":"invented"}]}]
    supp["links"].append({"legacy_table":"specimen","legacy_key":"spec-legacy","canonical_table":"specimen_registry","canonical_key":"spec-001","evidence_refs":["FIXTURE-EVIDENCE-1"]})
    reanchor(meta,supp)
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"] == "BLOCKED_UNKNOWN"
    assert next(d for d in result["dispositions"] if d["legacy_table"]=="person")["state"] == "WITHHELD"
    assert result["records"]["patient_registry"] == []
    assert result["records"]["specimen_registry"] == []
    assert "MISSING_CANONICAL_ASSERTION" in result["reason_counts"]


def test_actual_legacy_metadata_enters_bridge():
    from batchqual.patient import auditor, builder, schema as S
    from batchqual.patient.contract import load_contract
    fixture=LEGACY/"tests/fixtures/patient_synthetic"
    contract=load_contract((fixture/"contract.json").read_bytes())
    sources={o["object_id"]:(fixture/(o["object_id"]+".json")).read_bytes() for o in contract["source_objects"]}
    produced=builder.compute_tables(contract,sources)
    reconstructed=auditor.reconstruct(contract,sources)
    declared=set(S.COLUMNS)-{"assay_value","feature","gate_status"}
    hashes={t:sha(S.canonical_table(produced,t)) for t in declared}
    audit={t:sha(S.canonical_table(reconstructed,t)) for t in declared}
    assert hashes==audit
    metadata={"classification":"SYNTHETIC_ONLY","tables":{t:produced[t] for t in declared},"producer_hashes":hashes,"auditor_hashes":audit,"source_code_hashes":{n:sha((LEGACY/"batchqual/patient"/n).read_bytes()) for n in ("contract.py","schema.py","builder.py","auditor.py")}}
    records={t:[] for t in ("study_registry","publication_family","source_record","patient_registry","specimen_registry","assay_registry","treatment_episode","treatment_exposure","clinical_outcome","episode_binding")}
    records["study_registry"]=[{"study_id":"dav-study-synthetic","publication_family_id":"dav-family-synthetic","study_title":"Invented bridge study","study_class":"OTHER","cancer_type":"invented","study_design":"invented","candidate_paper_branches":[],"study_status":"CANDIDATE","source_locators":[{"kind":"fixture","value":"invented"}]}]
    records["publication_family"]=[{"publication_family_id":"dav-family-synthetic","study_id":"dav-study-synthetic","publication_id":"dav-pub-synthetic","publication_role":"OTHER","independence_status":"UNRESOLVED","source_locators":[{"kind":"fixture","value":"invented"}]}]
    links=[{"legacy_table":"study","legacy_key":produced["study"][0]["study_id"],"canonical_table":"study_registry","canonical_key":"dav-study-synthetic","evidence_refs":["FIXTURE-ASSERTION"]}]
    for i,row in enumerate(produced["person"]):
        uid=f"dav-patient-{i+1}"
        records["patient_registry"].append({"schema_version":"1.0.0","data_classification":"PRIVATE_PATIENT_LEVEL","patient_uid":uid,"study_id":"dav-study-synthetic","source_patient_id":row["source_label"],"patient_identity_confidence":"UNRESOLVED","treatment_naive_status":"UNKNOWN","inclusion_state":"CANDIDATE","source_locators":[{"kind":"fixture","value":"invented"}]})
        links.append({"legacy_table":"person","legacy_key":row["person_key"],"canonical_table":"patient_registry","canonical_key":uid,"evidence_refs":["FIXTURE-ASSERTION"]})
    sh={t:sha((SCHEMAS/(t+".schema.json")).read_bytes()) for t in records}
    supp={"classification":"SYNTHETIC_ONLY","records":records,"links":links,"unresolved":["E01"],"schema_hashes":sh,"legacy_metadata_sha256":anchor(metadata)}
    result=build_legacy_candidate(metadata,supp,schema_root=SCHEMAS)
    assert result["status"]=="BLOCKED_UNKNOWN"
    assert result["analysis_ready"] is False
    assert sum(d["state"]=="MAPPED" for d in result["dispositions"])==3
    assert sum(d["state"]=="WITHHELD" for d in result["dispositions"])==10
    assert sum(d["state"]=="SUPPORT_ONLY" for d in result["dispositions"])==28


def test_cross_episode_subject_and_patient_conflicts_fail():
    meta,supp=bundle()
    supp["records"]["patient_registry"].append({"schema_version":"1.0.0","data_classification":"PRIVATE_PATIENT_LEVEL","patient_uid":"patient-002","study_id":"study-001","source_patient_id":"002","patient_identity_confidence":"UNRESOLVED","treatment_naive_status":"UNKNOWN","inclusion_state":"CANDIDATE","source_locators":[{"kind":"fixture","value":"invented"}]})
    supp["records"]["treatment_episode"]=[{"schema_version":"1.1.0","data_classification":"SYNTHETIC_ONLY","treatment_episode_id":"ep-1","patient_uid":"patient-001","study_id":"study-001","regimen_id":"reg-1","index_event":"start","start_day":None,"stop_day":None,"timing_precision":"UNKNOWN","prior_ici":"UNKNOWN","episode_status":"BLOCKED_UNKNOWN","source_locators":["fixture"]}]
    supp["records"]["clinical_outcome"]=[{"outcome_id":"out-1","patient_uid":"patient-002","raw_endpoint_label":"NPD","endpoint_class":"OTHER","assessment_criteria":"unknown","canonical_category":"UNKNOWN","mapping_rule_version":"unreviewed","mapping_confidence":"UNRESOLVED","source_locators":[{"kind":"fixture","value":"invented"}]}]
    supp["records"]["episode_binding"]=[{"schema_version":"1.1.0","data_classification":"SYNTHETIC_ONLY","binding_id":"bind-1","patient_uid":"patient-002","treatment_episode_id":"ep-1","subject_type":"CLINICAL_OUTCOME","subject_id":"out-1","role":"OUTCOME_ASSESSMENT","binding_status":"BLOCKED_UNKNOWN","source_locators":["fixture"],"reviewer":None,"reviewed_utc":None}]
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="FAIL"
    assert set(result["reason_counts"])=={"EPISODE_PATIENT_MISMATCH"}
    meta,supp=bundle()
    from batchqual.patient import schema as S
    eps=[{"episode_id":"legacy-1","person_key":"person-001","regimen":"invented","agents":None,"line":None,"start_rel_days":None,"rule_id":"rule-1"},{"episode_id":"legacy-2","person_key":"person-001","regimen":"invented","agents":None,"line":None,"start_rel_days":None,"rule_id":"rule-1"}]
    meta["tables"]["treatment_episode"]=eps
    h=sha(S.canonical_table(meta["tables"],"treatment_episode")); meta["producer_hashes"]["treatment_episode"]=h; meta["auditor_hashes"]["treatment_episode"]=h
    obs=dict(zip(S.COLUMNS["endpoint_obs"],["obs-1","legacy-1","BOR","NPD","vocab","native",None,None,None,"rule-1"]))
    meta["tables"]["endpoint_obs"]=[obs]
    h=sha(S.canonical_table(meta["tables"],"endpoint_obs")); meta["producer_hashes"]["endpoint_obs"]=h; meta["auditor_hashes"]["endpoint_obs"]=h
    def episode(uid): return {"schema_version":"1.1.0","data_classification":"SYNTHETIC_ONLY","treatment_episode_id":uid,"patient_uid":"patient-001","study_id":"study-001","regimen_id":"reg-1","index_event":"start","start_day":None,"stop_day":None,"timing_precision":"UNKNOWN","prior_ici":"UNKNOWN","episode_status":"BLOCKED_UNKNOWN","source_locators":["fixture"]}
    supp["records"]["treatment_episode"]=[episode("dav-ep-1"),episode("dav-ep-2")]
    supp["records"]["clinical_outcome"]=[{"outcome_id":"out-1","patient_uid":"patient-001","raw_endpoint_label":"NPD","endpoint_class":"OTHER","assessment_criteria":"unknown","canonical_category":"UNKNOWN","mapping_rule_version":"unreviewed","mapping_confidence":"UNRESOLVED","source_locators":[{"kind":"fixture","value":"invented"}]}]
    supp["records"]["episode_binding"]=[{"schema_version":"1.1.0","data_classification":"SYNTHETIC_ONLY","binding_id":"bind-1","patient_uid":"patient-001","treatment_episode_id":"dav-ep-2","subject_type":"CLINICAL_OUTCOME","subject_id":"out-1","role":"OUTCOME_ASSESSMENT","binding_status":"BLOCKED_UNKNOWN","source_locators":["fixture"],"reviewer":None,"reviewed_utc":None}]
    supp["links"].extend([{"legacy_table":"treatment_episode","legacy_key":"legacy-1","canonical_table":"treatment_episode","canonical_key":"dav-ep-1","evidence_refs":["fixture"]},{"legacy_table":"treatment_episode","legacy_key":"legacy-2","canonical_table":"treatment_episode","canonical_key":"dav-ep-2","evidence_refs":["fixture"]},{"legacy_table":"endpoint_obs","legacy_key":"obs-1","canonical_table":"clinical_outcome","canonical_key":"out-1","evidence_refs":["fixture"]}])
    reanchor(meta,supp)
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["reason_counts"]=={"EPISODE_PATIENT_MISMATCH":1}


def test_raw_missing_zero_and_endpoint_types_remain_distinct():
    meta,supp=bundle()
    from batchqual.patient import schema as S
    meta["tables"]["treatment_episode"]=[{"episode_id":"ep-x","person_key":"person-001","regimen":"invented","agents":None,"line":None,"start_rel_days":None,"rule_id":"fixture-rule"}]
    rows=[]
    for i,value in enumerate((None,0,"NPD","DCB")):
        rows.append(dict(zip(S.COLUMNS["endpoint_obs"], [f"obs-{i}","ep-x","BOR",value,"vocab","native",None,None,None,"rule"])))
    meta["tables"]["endpoint_obs"]=rows
    meta["producer_hashes"]["endpoint_obs"]=sha(S.canonical_table(meta["tables"],"endpoint_obs"))
    meta["auditor_hashes"]["endpoint_obs"]=meta["producer_hashes"]["endpoint_obs"]
    reanchor(meta,supp)
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    vals=[r["raw_fields"]["native_value"] for r in result["lineage"] if r["legacy_table"]=="endpoint_obs"]
    assert vals==[None,0,"NPD","DCB"]
    assert "orr_mapping" not in str(result["records"])
    meta,supp=bundle()
    ep={"episode_id":"legacy-ep","person_key":"person-001","regimen":"invented","agents":None,"line":None,"start_rel_days":None,"rule_id":"rule-001"}
    meta["tables"]["treatment_episode"]=[ep]
    eh=sha(S.canonical_table(meta["tables"],"treatment_episode")); meta["producer_hashes"]["treatment_episode"]=eh; meta["auditor_hashes"]["treatment_episode"]=eh
    obs=dict(zip(S.COLUMNS["endpoint_obs"],["obs-null","legacy-ep","BOR",None,"vocab","native",None,None,None,"rule-001"]))
    meta["tables"]["endpoint_obs"]=[obs]
    oh=sha(S.canonical_table(meta["tables"],"endpoint_obs")); meta["producer_hashes"]["endpoint_obs"]=oh; meta["auditor_hashes"]["endpoint_obs"]=oh
    supp["records"]["treatment_episode"]=[{"schema_version":"1.1.0","data_classification":"SYNTHETIC_ONLY","treatment_episode_id":"dav-ep","patient_uid":"patient-001","study_id":"study-001","regimen_id":"reg-1","index_event":"start","start_day":None,"stop_day":None,"timing_precision":"UNKNOWN","prior_ici":"UNKNOWN","episode_status":"BLOCKED_UNKNOWN","source_locators":["fixture"]}]
    supp["records"]["clinical_outcome"]=[{"outcome_id":"out-null","patient_uid":"patient-001","raw_endpoint_label":"invented-text","endpoint_class":"OTHER","assessment_criteria":"unknown","canonical_category":"UNKNOWN","mapping_rule_version":"unreviewed","mapping_confidence":"UNRESOLVED","source_locators":[{"kind":"fixture","value":"invented"}]}]
    supp["links"].extend([{"legacy_table":"treatment_episode","legacy_key":"legacy-ep","canonical_table":"treatment_episode","canonical_key":"dav-ep","evidence_refs":["fixture"]},{"legacy_table":"endpoint_obs","legacy_key":"obs-null","canonical_table":"clinical_outcome","canonical_key":"out-null","evidence_refs":["fixture"]}])
    reanchor(meta,supp)
    assert build_legacy_candidate(meta,supp,schema_root=SCHEMAS)["reason_counts"]=={"RAW_VALUE_CONFLICT":1}


def test_permutation_and_stale_source_crosswalk():
    meta,supp=bundle()
    from batchqual.patient import schema as S
    meta["tables"]["study"].append({"study_id":"legacy-study-2","doi":None,"pmid":None,"trial_id":None,"accessions":None,"role_proposed":"SYNTHETIC"})
    hh=sha(S.canonical_table(meta["tables"],"study")); meta["producer_hashes"]["study"]=hh; meta["auditor_hashes"]["study"]=hh
    meta["tables"]["cohort"]=[{"cohort_id":"cohort-001","study_id":"legacy-study","definition_rule_id":"rule-1","independence_group_id":"g1"},{"cohort_id":"cohort-002","study_id":"legacy-study-2","definition_rule_id":"rule-1","independence_group_id":"g2"}]
    hh=sha(S.canonical_table(meta["tables"],"cohort")); meta["producer_hashes"]["cohort"]=hh; meta["auditor_hashes"]["cohort"]=hh
    meta["tables"]["person"].append({"person_key":"person-002","cohort_id":"cohort-002","source_label":"001","rule_id":"rule-1"})
    meta["tables"]["person"].append({"person_key":"person-003","cohort_id":"cohort-002","source_label":"1","rule_id":"rule-1"})
    hh=sha(S.canonical_table(meta["tables"],"person")); meta["producer_hashes"]["person"]=hh; meta["auditor_hashes"]["person"]=hh
    meta["tables"]["person_alias"]=[{"person_key":"person-001","study_id":"legacy-study","source_label":"alias-a","rule_id":"rule-1"},{"person_key":"person-001","study_id":"legacy-study","source_label":"alias-b","rule_id":"rule-1"}]
    hh=sha(S.canonical_table(meta["tables"],"person_alias")); meta["producer_hashes"]["person_alias"]=hh; meta["auditor_hashes"]["person_alias"]=hh
    supp["records"]["study_registry"].append({"study_id":"study-002","publication_family_id":"family-002","study_title":"Second invented study","study_class":"OTHER","cancer_type":"invented","study_design":"invented","candidate_paper_branches":[],"study_status":"CANDIDATE","source_locators":[{"kind":"fixture","value":"invented"}]})
    supp["records"]["publication_family"].append({"publication_family_id":"family-002","study_id":"study-002","publication_id":"publication-002","publication_role":"OTHER","independence_status":"UNRESOLVED","source_locators":[{"kind":"fixture","value":"invented"}]})
    supp["records"]["patient_registry"].append({"schema_version":"1.0.0","data_classification":"PRIVATE_PATIENT_LEVEL","patient_uid":"patient-002","study_id":"study-002","source_patient_id":"001","patient_identity_confidence":"UNRESOLVED","treatment_naive_status":"UNKNOWN","inclusion_state":"CANDIDATE","source_locators":[{"kind":"fixture","value":"invented"}]})
    supp["records"]["patient_registry"].append({"schema_version":"1.0.0","data_classification":"PRIVATE_PATIENT_LEVEL","patient_uid":"patient-003","study_id":"study-002","source_patient_id":"1","patient_identity_confidence":"UNRESOLVED","treatment_naive_status":"UNKNOWN","inclusion_state":"CANDIDATE","source_locators":[{"kind":"fixture","value":"invented"}]})
    supp["links"].append({"legacy_table":"study","legacy_key":"legacy-study-2","canonical_table":"study_registry","canonical_key":"study-002","evidence_refs":["fixture"]})
    supp["links"].append({"legacy_table":"person","legacy_key":"person-002","canonical_table":"patient_registry","canonical_key":"patient-002","evidence_refs":["fixture"]})
    supp["links"].append({"legacy_table":"person","legacy_key":"person-003","canonical_table":"patient_registry","canonical_key":"patient-003","evidence_refs":["fixture"]})
    reanchor(meta,supp)
    first=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    meta["tables"]["study"].reverse(); meta["tables"]["person_alias"].reverse(); supp["records"]["study_registry"].reverse(); supp["records"]["publication_family"].reverse(); supp["links"].reverse()
    second=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert first==second
    assert [r["source_patient_id"] for r in first["records"]["patient_registry"]]==["001","001","1"]
    meta,supp=bundle(); meta["source_code_hashes"]["builder.py"]="0"*64
    third=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert third["status"]=="FAIL" and "CODE_BINDING_MISMATCH" in third["reason_counts"]


def test_empty_bundle_never_claims_structural_success():
    meta,supp=bundle()
    from batchqual.patient import schema as S
    for table in meta["tables"]: meta["tables"][table]=[]
    hashes={t:sha(S.canonical_table(meta["tables"],t)) for t in meta["tables"]}
    meta["producer_hashes"]=dict(hashes); meta["auditor_hashes"]=dict(hashes)
    supp["records"]={t:[] for t in supp["records"]}; supp["links"]=[]; supp["unresolved"]=[]
    reanchor(meta,supp)
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="BLOCKED_UNKNOWN"
    assert result["reason_counts"]["MISSING_CANONICAL_ASSERTION"]==1


def test_metadata_anchor_rejects_refreshed_source_hash_with_stale_links():
    meta,supp=bundle()
    from batchqual.patient import schema as S
    meta["tables"]["source_object"]=[{"object_id":"object-new-bytes","study_id":"legacy-study","locator":"invented","sha256":"f"*64,"bytes":17,"format":"tsv","licence":None,"custody_manifest_sha":None}]
    h=sha(S.canonical_table(meta["tables"],"source_object"))
    meta["producer_hashes"]["source_object"]=h; meta["auditor_hashes"]["source_object"]=h
    meta["source_code_hashes"]={n:sha((LEGACY/"batchqual/patient"/n).read_bytes()) for n in ("contract.py","schema.py","builder.py","auditor.py")}
    assert build_legacy_candidate(meta,supp,schema_root=SCHEMAS)["reason_counts"]=={"METADATA_HASH_MISMATCH":1}


def test_schema_bytes_and_many_to_one_patient_merge_fail():
    meta,supp=bundle()
    with __import__("tempfile").TemporaryDirectory() as td:
        import shutil
        shutil.copytree(SCHEMAS,Path(td),dirs_exist_ok=True)
        p=Path(td)/"patient_registry.schema.json"
        p.write_bytes(p.read_bytes()+b" ")
        assert build_legacy_candidate(meta,supp,schema_root=Path(td))["reason_counts"]=={"SCHEMA_BINDING_MISMATCH":1}
    meta,supp=bundle()
    from batchqual.patient import schema as S
    row={"person_key":"person-002","cohort_id":"cohort-002","source_label":"001","rule_id":"rule-001"}
    meta["tables"]["person"].append(row)
    h=sha(S.canonical_table(meta["tables"],"person")); meta["producer_hashes"]["person"]=h; meta["auditor_hashes"]["person"]=h
    supp["links"].append({"legacy_table":"person","legacy_key":"person-002","canonical_table":"patient_registry","canonical_key":"patient-001","evidence_refs":["fixture"]})
    reanchor(meta,supp)
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["reason_counts"]=={"AMBIGUOUS_IDENTITY":1}


def test_summary_and_inputs_are_unchanged_and_private_sentinels_are_hidden():
    meta,supp=bundle()
    before=copy_json=(json.dumps((meta,supp),sort_keys=True))
    meta["tables"]["person"][0]["source_label"]="sentinel-private-id"
    h=sha(__import__("batchqual.patient.schema",fromlist=["canonical_table"]).canonical_table(meta["tables"],"person"))
    meta["producer_hashes"]["person"]=h; meta["auditor_hashes"]["person"]=h
    after=json.dumps((meta,supp),sort_keys=True)
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert json.dumps((meta,supp),sort_keys=True)==after
    assert "sentinel-private-id" not in json.dumps(public_summary(result))
    assert "sentinel-private-id" not in str(result["reason_counts"])
    assert before!=after


def _refresh(meta, tables):
    from batchqual.patient import schema as S
    for t in tables:
        h=sha(S.canonical_table(meta["tables"],t)); meta["producer_hashes"][t]=h; meta["auditor_hashes"][t]=h


def _episode_record(uid="dav-ep"):
    return {"schema_version":"1.1.0","data_classification":"SYNTHETIC_ONLY","treatment_episode_id":uid,"patient_uid":"patient-001","study_id":"study-001","regimen_id":"reg-1","index_event":"start","start_day":None,"stop_day":None,"timing_precision":"UNKNOWN","prior_ici":"UNKNOWN","episode_status":"BLOCKED_UNKNOWN","source_locators":["fixture"]}


def _outcome_record(uid="out-1", label="NPD"):
    return {"outcome_id":uid,"patient_uid":"patient-001","raw_endpoint_label":label,"endpoint_class":"OTHER","assessment_criteria":"unknown","canonical_category":"UNKNOWN","mapping_rule_version":"unreviewed","mapping_confidence":"UNRESOLVED","source_locators":[{"kind":"fixture","value":"invented"}]}


def test_family_dependency_closure_withholds_study_and_patient():
    meta,supp=bundle()
    del supp["records"]["publication_family"][0]["publication_role"]
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="BLOCKED_UNKNOWN"
    assert result["records"]["publication_family"]==[]
    assert result["records"]["study_registry"]==[]
    assert result["records"]["patient_registry"]==[]
    assert all(d["state"]=="WITHHELD" for d in result["dispositions"] if d["legacy_table"] in {"study","person"})
    assert all(x["canonical_key"] is None for x in result["lineage"] if x["legacy_table"] in {"study","person"})


def test_assay_must_retain_legacy_source_object_owner():
    meta,supp=bundle()
    meta["tables"]["source_object"]=[
        {"object_id":"legacy-a","study_id":"legacy-study","locator":"a","sha256":"a"*64,"bytes":1,"format":"tsv","licence":None,"custody_manifest_sha":None},
        {"object_id":"legacy-b","study_id":"legacy-study","locator":"b","sha256":"b"*64,"bytes":1,"format":"tsv","licence":None,"custody_manifest_sha":None}]
    meta["tables"]["specimen"]=[{"specimen_id":"legacy-s","person_key":"person-001","site":None,"tissue":None,"collection_rel_days":None,"rule_id":"r","source_label":"sample"}]
    meta["tables"]["assay"]=[{"assay_id":"legacy-a1","source_object_id":"legacy-a","native_label":"sample","platform":None,"native_unit":None,"declared_transform":None,"qc_flags":None}]
    meta["tables"]["assay_specimen"]=[{"assay_id":"legacy-a1","specimen_id":"legacy-s","relation":"unknown","rule_id":"r"}]
    _refresh(meta,("source_object","specimen","assay","assay_specimen")); reanchor(meta,supp)
    supp["records"]["source_record"]=[
        {"source_object_id":"dav-a","study_id":"study-001","publication_family_id":"family-001","repository":"invented","object_type":"matrix","exact_file_name":"a.tsv","retrieval_status":"LOCATED","validation_status":"STRUCTURAL_ONLY","sha256":"a"*64,"source_locators":[{"kind":"fixture","value":"a"}]},
        {"source_object_id":"dav-b","study_id":"study-001","publication_family_id":"family-001","repository":"invented","object_type":"matrix","exact_file_name":"b.tsv","retrieval_status":"LOCATED","validation_status":"STRUCTURAL_ONLY","sha256":"b"*64,"source_locators":[{"kind":"fixture","value":"b"}]}]
    supp["records"]["specimen_registry"]=[{"specimen_uid":"dav-s","patient_uid":"patient-001","raw_sample_aliases":["sample"],"canonical_timing_category":"UNKNOWN","tissue_type":"UNKNOWN","biological_compartment":"UNKNOWN","baseline_candidate_status":"UNKNOWN","longitudinal_pair_status":"UNKNOWN","source_locators":[{"kind":"fixture","value":"invented"}]}]
    supp["records"]["assay_registry"]=[{"assay_uid":"dav-assay","specimen_uid":"dav-s","source_sample_id":"sample","source_object_id":"dav-b","modality":"RNA","platform":"invented","measurement_unit":"UNKNOWN","transform":"UNKNOWN","matrix_header":"sample","qc_status":"NOT_EVALUATED","branch_suitability":["UNSUPPORTED"],"source_locators":[{"kind":"fixture","value":"invented"}]}]
    supp["links"].extend([
        {"legacy_table":"source_object","legacy_key":"legacy-a","canonical_table":"source_record","canonical_key":"dav-a","evidence_refs":["fixture"]},
        {"legacy_table":"source_object","legacy_key":"legacy-b","canonical_table":"source_record","canonical_key":"dav-b","evidence_refs":["fixture"]},
        {"legacy_table":"specimen","legacy_key":"legacy-s","canonical_table":"specimen_registry","canonical_key":"dav-s","evidence_refs":["fixture"]},
        {"legacy_table":"assay","legacy_key":"legacy-a1","canonical_table":"assay_registry","canonical_key":"dav-assay","evidence_refs":["fixture"]}])
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="FAIL" and result["reason_counts"]=={"FOREIGN_KEY_UNRESOLVED":1}


def test_pruning_reconciles_dispositions_lineage_and_reason_counts():
    meta,supp=bundle()
    del supp["records"]["study_registry"][0]["study_title"]
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="BLOCKED_UNKNOWN"
    assert result["records"]["study_registry"]==[] and result["records"]["patient_registry"]==[]
    for d in result["dispositions"]:
        if d["legacy_table"] in {"study","person"}:
            assert d["state"]=="WITHHELD" and d["reason_codes"]
    for row in result["lineage"]:
        if row["legacy_table"] in {"study","person"}:
            assert row["canonical_key"] is None and row["canonical_table"] is None
    assert result["reason_counts"]["MISSING_CANONICAL_ASSERTION"]>=2


def test_non_scalar_metadata_values_fail_even_with_refreshed_hashes():
    for value in ({"nested":"sentinel"},["nested"]):
        meta,supp=bundle()
        meta["tables"]["person_alias"]=[{"person_key":"person-001","study_id":"legacy-study","source_label":value,"rule_id":"rule-001"}]
        _refresh(meta,("person_alias",)); reanchor(meta,supp)
        result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
        assert result["status"]=="FAIL" and result["reason_counts"]=={"MALFORMED_INPUT":1}


def test_mapped_outcome_requires_explicit_matching_episode_binding():
    meta,supp=bundle()
    from batchqual.patient import schema as S
    meta["tables"]["treatment_episode"]=[{"episode_id":"legacy-ep","person_key":"person-001","regimen":"invented","agents":None,"line":None,"start_rel_days":None,"rule_id":"r"}]
    meta["tables"]["endpoint_obs"]=[dict(zip(S.COLUMNS["endpoint_obs"],["legacy-out","legacy-ep","BOR","NPD","vocab","native",None,None,None,"r"]))]
    _refresh(meta,("treatment_episode","endpoint_obs")); reanchor(meta,supp)
    supp["records"]["treatment_episode"]=[_episode_record()]
    supp["records"]["clinical_outcome"]=[_outcome_record()]
    supp["links"].extend([
        {"legacy_table":"treatment_episode","legacy_key":"legacy-ep","canonical_table":"treatment_episode","canonical_key":"dav-ep","evidence_refs":["fixture"]},
        {"legacy_table":"endpoint_obs","legacy_key":"legacy-out","canonical_table":"clinical_outcome","canonical_key":"out-1","evidence_refs":["fixture"]}])
    reanchor(meta,supp)
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="BLOCKED_UNKNOWN" and result["records"]["clinical_outcome"]==[]
    assert next(d for d in result["dispositions"] if d["legacy_table"]=="endpoint_obs")["state"]=="WITHHELD"
    assert result["reason_counts"].get("SOURCE_EVIDENCE_REQUIRED",0)>=1


def test_outcome_wrong_episode_binding_fails_even_for_same_patient():
    meta,supp=bundle()
    from batchqual.patient import schema as S
    meta["tables"]["treatment_episode"]=[{"episode_id":e,"person_key":"person-001","regimen":"invented","agents":None,"line":None,"start_rel_days":None,"rule_id":"r"} for e in ("legacy-ep-a","legacy-ep-b")]
    meta["tables"]["endpoint_obs"]=[dict(zip(S.COLUMNS["endpoint_obs"],["legacy-out","legacy-ep-a","BOR","NPD","vocab","native",None,None,None,"r"]))]
    _refresh(meta,("treatment_episode","endpoint_obs")); reanchor(meta,supp)
    supp["records"]["treatment_episode"]=[_episode_record("dav-ep-a"),_episode_record("dav-ep-b")]
    supp["records"]["clinical_outcome"]=[_outcome_record()]
    supp["records"]["episode_binding"]=[{"schema_version":"1.1.0","data_classification":"SYNTHETIC_ONLY","binding_id":"bind-out","patient_uid":"patient-001","treatment_episode_id":"dav-ep-b","subject_type":"CLINICAL_OUTCOME","subject_id":"out-1","role":"OUTCOME_ASSESSMENT","binding_status":"BLOCKED_UNKNOWN","source_locators":["fixture"],"reviewer":None,"reviewed_utc":None}]
    supp["links"].extend([
        {"legacy_table":"treatment_episode","legacy_key":"legacy-ep-a","canonical_table":"treatment_episode","canonical_key":"dav-ep-a","evidence_refs":["fixture"]},
        {"legacy_table":"treatment_episode","legacy_key":"legacy-ep-b","canonical_table":"treatment_episode","canonical_key":"dav-ep-b","evidence_refs":["fixture"]},
        {"legacy_table":"endpoint_obs","legacy_key":"legacy-out","canonical_table":"clinical_outcome","canonical_key":"out-1","evidence_refs":["fixture"]}])
    reanchor(meta,supp)
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="FAIL" and result["reason_counts"]=={"EPISODE_PATIENT_MISMATCH":1}


def test_specimen_episode_requires_and_preserves_each_explicit_binding():
    meta,supp=bundle()
    meta["tables"]["specimen"]=[{"specimen_id":"legacy-s","person_key":"person-001","site":None,"tissue":None,"collection_rel_days":None,"rule_id":"r","source_label":"sample"}]
    meta["tables"]["treatment_episode"]=[{"episode_id":e,"person_key":"person-001","regimen":"invented","agents":None,"line":None,"start_rel_days":None,"rule_id":"r"} for e in ("legacy-ep-a","legacy-ep-b")]
    meta["tables"]["specimen_episode"]=[{"specimen_id":"legacy-s","episode_id":e,"timing_class":"unknown","intervening_therapy":None,"rule_id":"r"} for e in ("legacy-ep-a","legacy-ep-b")]
    _refresh(meta,("specimen","treatment_episode","specimen_episode")); reanchor(meta,supp)
    supp["records"]["specimen_registry"]=[{"specimen_uid":"dav-s","patient_uid":"patient-001","raw_sample_aliases":["sample"],"canonical_timing_category":"UNKNOWN","tissue_type":"UNKNOWN","biological_compartment":"UNKNOWN","baseline_candidate_status":"UNKNOWN","longitudinal_pair_status":"UNKNOWN","source_locators":[{"kind":"fixture","value":"invented"}]}]
    supp["records"]["treatment_episode"]=[_episode_record("dav-ep-a"),_episode_record("dav-ep-b")]
    supp["records"]["episode_binding"]=[]
    supp["links"].extend([
        {"legacy_table":"specimen","legacy_key":"legacy-s","canonical_table":"specimen_registry","canonical_key":"dav-s","evidence_refs":["fixture"]},
        {"legacy_table":"treatment_episode","legacy_key":"legacy-ep-a","canonical_table":"treatment_episode","canonical_key":"dav-ep-a","evidence_refs":["fixture"]},
        {"legacy_table":"treatment_episode","legacy_key":"legacy-ep-b","canonical_table":"treatment_episode","canonical_key":"dav-ep-b","evidence_refs":["fixture"]}])
    reanchor(meta,supp)
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="BLOCKED_UNKNOWN" and result["records"]["specimen_registry"]==[]
    assert result["reason_counts"].get("SOURCE_EVIDENCE_REQUIRED",0)>=1
    for i,ep in enumerate(("dav-ep-a","dav-ep-b")):
        supp["records"]["episode_binding"].append({"schema_version":"1.1.0","data_classification":"SYNTHETIC_ONLY","binding_id":f"bind-s-{i}","patient_uid":"patient-001","treatment_episode_id":ep,"subject_type":"SPECIMEN","subject_id":"dav-s","role":"UNKNOWN","binding_status":"BLOCKED_UNKNOWN","source_locators":["fixture"],"reviewer":None,"reviewed_utc":None})
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert len(result["records"]["episode_binding"])==2
    supp["records"]["episode_binding"].pop()
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="BLOCKED_UNKNOWN" and result["records"]["specimen_registry"]==[]


def test_same_patient_specimen_binding_to_wrong_episode_fails():
    meta,supp=bundle()
    meta["tables"]["specimen"]=[{"specimen_id":"legacy-s","person_key":"person-001","site":None,"tissue":None,"collection_rel_days":None,"rule_id":"r","source_label":"sample"}]
    meta["tables"]["treatment_episode"]=[{"episode_id":e,"person_key":"person-001","regimen":"invented","agents":None,"line":None,"start_rel_days":None,"rule_id":"r"} for e in ("legacy-ep-a","legacy-ep-b")]
    meta["tables"]["specimen_episode"]=[{"specimen_id":"legacy-s","episode_id":"legacy-ep-a","timing_class":"unknown","intervening_therapy":None,"rule_id":"r"}]
    _refresh(meta,("specimen","treatment_episode","specimen_episode")); reanchor(meta,supp)
    supp["records"]["specimen_registry"]=[{"specimen_uid":"dav-s","patient_uid":"patient-001","raw_sample_aliases":["sample"],"canonical_timing_category":"UNKNOWN","tissue_type":"UNKNOWN","biological_compartment":"UNKNOWN","baseline_candidate_status":"UNKNOWN","longitudinal_pair_status":"UNKNOWN","source_locators":[{"kind":"fixture","value":"invented"}]}]
    supp["records"]["treatment_episode"]=[_episode_record("dav-ep-a"),_episode_record("dav-ep-b")]
    supp["records"]["episode_binding"]=[{"schema_version":"1.1.0","data_classification":"SYNTHETIC_ONLY","binding_id":"bind-s","patient_uid":"patient-001","treatment_episode_id":"dav-ep-a","subject_type":"SPECIMEN","subject_id":"dav-s","role":"UNKNOWN","binding_status":"BLOCKED_UNKNOWN","source_locators":["fixture"],"reviewer":None,"reviewed_utc":None}]
    supp["links"].extend([
        {"legacy_table":"specimen","legacy_key":"legacy-s","canonical_table":"specimen_registry","canonical_key":"dav-s","evidence_refs":["fixture"]},
        {"legacy_table":"treatment_episode","legacy_key":"legacy-ep-a","canonical_table":"treatment_episode","canonical_key":"dav-ep-a","evidence_refs":["fixture"]},
        {"legacy_table":"treatment_episode","legacy_key":"legacy-ep-b","canonical_table":"treatment_episode","canonical_key":"dav-ep-b","evidence_refs":["fixture"]}])
    reanchor(meta,supp)
    assert build_legacy_candidate(meta,supp,schema_root=SCHEMAS)["status"]=="STRUCTURAL_CANDIDATE"
    supp["records"]["episode_binding"][0]["treatment_episode_id"]="dav-ep-b"
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="FAIL" and result["reason_counts"]=={"EPISODE_PATIENT_MISMATCH":1}


def _source_object_bundle():
    meta,supp=bundle()
    meta["tables"]["source_object"]=[{"object_id":"legacy-object","study_id":"legacy-study","locator":"invented","sha256":"a"*64,"bytes":20,"format":"tsv","licence":None,"custody_manifest_sha":None}]
    _refresh(meta,("source_object",)); reanchor(meta,supp)
    supp["records"]["source_record"]=[{"source_object_id":"dav-object","study_id":"study-001","publication_family_id":"family-001","repository":"invented","object_type":"matrix","exact_file_name":"invented.tsv","retrieval_status":"LOCATED","validation_status":"STRUCTURAL_ONLY","sha256":"a"*64,"source_locators":[{"kind":"fixture","value":"invented"}]}]
    supp["links"].append({"legacy_table":"source_object","legacy_key":"legacy-object","canonical_table":"source_record","canonical_key":"dav-object","evidence_refs":["fixture"]})
    reanchor(meta,supp)
    return meta,supp


def test_source_object_scope_and_hash_conflicts_are_not_hidden_by_missing_study_link():
    meta,supp=_source_object_bundle()
    control=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert control["status"]=="STRUCTURAL_CANDIDATE" and len(control["records"]["source_record"])==1
    meta,supp=_source_object_bundle()
    meta["tables"]["source_object"][0]["study_id"]="absent-native-study"
    _refresh(meta,("source_object",)); reanchor(meta,supp)
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="FAIL" and result["reason_counts"]=={"FOREIGN_KEY_UNRESOLVED":1}
    meta,supp=_source_object_bundle()
    supp["links"]=[link for link in supp["links"] if link["legacy_table"]!="study"]
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="BLOCKED_UNKNOWN"
    assert result["records"]["source_record"]==[]
    meta,supp=_source_object_bundle()
    supp["links"]=[link for link in supp["links"] if link["legacy_table"]!="study"]
    supp["records"]["source_record"][0]["sha256"]="b"*64
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="FAIL" and result["reason_counts"]=={"RAW_VALUE_CONFLICT":1}


def test_native_assay_source_reference_must_exist_even_without_a_link():
    meta,supp=bundle()
    meta["tables"]["source_object"]=[{"object_id":"present-object","study_id":"legacy-study","locator":"invented","sha256":"a"*64,"bytes":20,"format":"tsv","licence":None,"custody_manifest_sha":None}]
    meta["tables"]["assay"]=[{"assay_id":"legacy-assay","source_object_id":"missing-object","native_label":"sample","platform":None,"native_unit":None,"declared_transform":None,"qc_flags":None}]
    _refresh(meta,("source_object","assay")); reanchor(meta,supp)
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="FAIL" and result["reason_counts"]=={"FOREIGN_KEY_UNRESOLVED":1}


def test_native_specimen_owner_must_exist_even_without_a_canonical_link():
    meta,supp=bundle()
    meta["tables"]["specimen"]=[{"specimen_id":"legacy-specimen","person_key":"missing-person","site":None,"tissue":"tumour","collection_rel_days":None,"rule_id":"fixture-rule","source_label":"sample"}]
    _refresh(meta,("specimen",)); reanchor(meta,supp)
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="FAIL" and result["reason_counts"]=={"FOREIGN_KEY_UNRESOLVED":1}


def _episode_exposure_bundle(*, native_episode=True, link_episode=True):
    meta,supp=bundle()
    if native_episode:
        meta["tables"]["treatment_episode"]=[{"episode_id":"legacy-ep","person_key":"person-001","regimen":"invented","agents":None,"line":None,"start_rel_days":None,"rule_id":"fixture-rule"}]
        _refresh(meta,("treatment_episode",))
    reanchor(meta,supp)
    supp["records"]["treatment_episode"]=[dict(_episode_record(),component_exposure_ids=["exp-1"])]
    supp["records"]["treatment_exposure"]=[{"treatment_exposure_id":"exp-1","patient_uid":"patient-001","regimen_id":"reg-1","agent":"invented","pharmacological_class":"UNKNOWN","monotherapy_or_combination":"UNKNOWN","sequence":None,"line_of_therapy":None,"prior_ici":"UNKNOWN","certainty":"UNRESOLVED","source_locators":[{"kind":"fixture","value":"invented"}]}]
    supp["records"]["episode_binding"]=[{"schema_version":"1.1.0","data_classification":"SYNTHETIC_ONLY","binding_id":"bind-exp","patient_uid":"patient-001","treatment_episode_id":"dav-ep","subject_type":"TREATMENT_EXPOSURE","subject_id":"exp-1","role":"TREATMENT_COMPONENT","binding_status":"BLOCKED_UNKNOWN","source_locators":["fixture"],"reviewer":None,"reviewed_utc":None}]
    if link_episode:
        supp["links"].append({"legacy_table":"treatment_episode","legacy_key":"legacy-ep","canonical_table":"treatment_episode","canonical_key":"dav-ep","evidence_refs":["fixture"]})
    reanchor(meta,supp)
    return meta,supp


def _assert_exposure_graph_closed(result):
    episodes={row["treatment_episode_id"]:row for row in result["records"]["treatment_episode"]}
    exposures={row["treatment_exposure_id"] for row in result["records"]["treatment_exposure"]}
    bindings={(row["subject_type"],row["subject_id"],row["treatment_episode_id"]) for row in result["records"]["episode_binding"]}
    for exposure_id in exposures:
        assert any(kind=="TREATMENT_EXPOSURE" and subject==exposure_id and episode_id in episodes for kind,subject,episode_id in bindings)
    for episode_id,episode in episodes.items():
        for exposure_id in episode.get("component_exposure_ids",[]):
            assert exposure_id in exposures and ("TREATMENT_EXPOSURE",exposure_id,episode_id) in bindings


def _full_episode_subject_bundle():
    meta,supp=_episode_exposure_bundle()
    from batchqual.patient import schema as S
    meta["tables"]["specimen"]=[{"specimen_id":"legacy-specimen","person_key":"person-001","site":None,"tissue":"tumour","collection_rel_days":None,"rule_id":"fixture-rule","source_label":"sample-1"}]
    meta["tables"]["specimen_episode"]=[{"specimen_id":"legacy-specimen","episode_id":"legacy-ep","timing_class":"unknown","intervening_therapy":None,"rule_id":"fixture-rule"}]
    meta["tables"]["endpoint_obs"]=[dict(zip(S.COLUMNS["endpoint_obs"],["legacy-out","legacy-ep","BOR","NPD","vocab","native",None,None,None,"fixture-rule"]))]
    _refresh(meta,("specimen","specimen_episode","endpoint_obs")); reanchor(meta,supp)
    supp["records"]["specimen_registry"]=[{"specimen_uid":"dav-specimen","patient_uid":"patient-001","raw_sample_aliases":["sample-1"],"canonical_timing_category":"UNKNOWN","tissue_type":"UNKNOWN","biological_compartment":"UNKNOWN","baseline_candidate_status":"UNKNOWN","longitudinal_pair_status":"UNKNOWN","source_locators":[{"kind":"fixture","value":"invented"}]}]
    supp["records"]["clinical_outcome"]=[_outcome_record()]
    supp["records"]["episode_binding"].extend([
        {"schema_version":"1.1.0","data_classification":"SYNTHETIC_ONLY","binding_id":"bind-out","patient_uid":"patient-001","treatment_episode_id":"dav-ep","subject_type":"CLINICAL_OUTCOME","subject_id":"out-1","role":"OUTCOME_ASSESSMENT","binding_status":"BLOCKED_UNKNOWN","source_locators":["fixture"],"reviewer":None,"reviewed_utc":None},
        {"schema_version":"1.1.0","data_classification":"SYNTHETIC_ONLY","binding_id":"bind-specimen","patient_uid":"patient-001","treatment_episode_id":"dav-ep","subject_type":"SPECIMEN","subject_id":"dav-specimen","role":"UNKNOWN","binding_status":"BLOCKED_UNKNOWN","source_locators":["fixture"],"reviewer":None,"reviewed_utc":None}])
    supp["links"].extend([
        {"legacy_table":"specimen","legacy_key":"legacy-specimen","canonical_table":"specimen_registry","canonical_key":"dav-specimen","evidence_refs":["fixture"]},
        {"legacy_table":"endpoint_obs","legacy_key":"legacy-out","canonical_table":"clinical_outcome","canonical_key":"out-1","evidence_refs":["fixture"]}])
    reanchor(meta,supp)
    return meta,supp


def _assert_full_subject_graph_empty_or_closed(result):
    episodes={r["treatment_episode_id"] for r in result["records"]["treatment_episode"]}
    specimens={r["specimen_uid"] for r in result["records"]["specimen_registry"]}
    exposures={r["treatment_exposure_id"] for r in result["records"]["treatment_exposure"]}
    outcomes={r["outcome_id"] for r in result["records"]["clinical_outcome"]}
    bindings=result["records"]["episode_binding"]
    for row in bindings:
        assert row["treatment_episode_id"] in episodes
        targets={"SPECIMEN":specimens,"TREATMENT_EXPOSURE":exposures,"CLINICAL_OUTCOME":outcomes}[row["subject_type"]]
        assert row["subject_id"] in targets
    for outcome in outcomes:
        assert any(b["subject_type"]=="CLINICAL_OUTCOME" and b["subject_id"]==outcome for b in bindings)
    for specimen in specimens:
        assert any(b["subject_type"]=="SPECIMEN" and b["subject_id"]==specimen for b in bindings)


def test_final_exposure_graph_requires_retained_linked_episode():
    meta,supp=_episode_exposure_bundle()
    control=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert control["status"]=="STRUCTURAL_CANDIDATE"
    assert [len(control["records"][table]) for table in ("treatment_episode","treatment_exposure","episode_binding")] == [1,1,1]
    _assert_exposure_graph_closed(control)
    meta,supp=_episode_exposure_bundle(native_episode=False,link_episode=False)
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="BLOCKED_UNKNOWN"
    assert [len(result["records"][table]) for table in ("treatment_episode","treatment_exposure","episode_binding")] == [0,0,0]
    assert result["reason_counts"].get("MISSING_CANONICAL_ASSERTION",0)>0
    _assert_exposure_graph_closed(result)


def test_missing_episode_assertion_withholds_exposure_component_closure():
    meta,supp=_episode_exposure_bundle()
    del supp["records"]["treatment_episode"][0]["index_event"]
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="BLOCKED_UNKNOWN"
    assert [len(result["records"][table]) for table in ("treatment_episode","treatment_exposure","episode_binding")] == [0,0,0]
    assert result["reason_counts"].get("MISSING_CANONICAL_ASSERTION",0)>0
    person=next(d for d in result["dispositions"] if d["legacy_table"]=="treatment_episode")
    assert person["state"]=="WITHHELD"
    lineage=next(x for x in result["lineage"] if x["legacy_table"]=="treatment_episode")
    assert lineage["canonical_key"] is None and lineage["canonical_table"] is None
    _assert_exposure_graph_closed(result)


def test_missing_exposure_field_and_missing_patient_id_are_withheld_not_failed():
    meta,supp=_episode_exposure_bundle()
    del supp["records"]["treatment_exposure"][0]["agent"]
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="BLOCKED_UNKNOWN"
    assert [len(result["records"][table]) for table in ("treatment_episode","treatment_exposure","episode_binding")] == [0,0,0]
    assert result["reason_counts"].get("MISSING_CANONICAL_ASSERTION",0)>0
    assert next(d for d in result["dispositions"] if d["legacy_table"]=="treatment_episode")["state"]=="WITHHELD"
    _assert_exposure_graph_closed(result)
    meta,supp=bundle()
    del supp["records"]["patient_registry"][0]["patient_uid"]
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="BLOCKED_UNKNOWN"
    person=next(d for d in result["dispositions"] if d["legacy_table"]=="person")
    lineage=next(x for x in result["lineage"] if x["legacy_table"]=="person")
    assert person["state"]=="WITHHELD" and lineage["canonical_key"] is None and lineage["canonical_table"] is None
    assert result["records"]["patient_registry"]==[]


def test_component_pruning_withholds_outcome_and_specimen_dependencies():
    meta,supp=_full_episode_subject_bundle()
    control=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert control["status"]=="STRUCTURAL_CANDIDATE"
    assert [len(control["records"][t]) for t in ("treatment_episode","treatment_exposure","clinical_outcome","specimen_registry","episode_binding")] == [1,1,1,1,3]
    assert next(d for d in control["dispositions"] if d["legacy_table"]=="endpoint_obs")["state"]=="MAPPED"
    _assert_full_subject_graph_empty_or_closed(control)
    del supp["records"]["treatment_exposure"][0]["agent"]
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="BLOCKED_UNKNOWN"
    assert [len(result["records"][t]) for t in ("treatment_episode","treatment_exposure","clinical_outcome","specimen_registry","episode_binding")] == [0,0,0,0,0]
    assert result["reason_counts"].get("MISSING_CANONICAL_ASSERTION",0)>0
    for table in ("treatment_episode","endpoint_obs","specimen"):
        disp=next(d for d in result["dispositions"] if d["legacy_table"]==table)
        lin=next(r for r in result["lineage"] if r["legacy_table"]==table)
        assert disp["state"]=="WITHHELD" and lin["canonical_key"] is None and lin["canonical_table"] is None
    _assert_full_subject_graph_empty_or_closed(result)


def test_incomplete_exposure_binding_withholds_but_wrong_episode_fails():
    meta,supp=_full_episode_subject_bundle()
    control=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert control["status"]=="STRUCTURAL_CANDIDATE"
    for field in ("reviewer","patient_uid","treatment_episode_id","subject_type","subject_id"):
        meta,supp=_full_episode_subject_bundle()
        exposure_binding=next(b for b in supp["records"]["episode_binding"] if b["subject_type"]=="TREATMENT_EXPOSURE")
        del exposure_binding[field]
        result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
        assert result["status"]=="BLOCKED_UNKNOWN", field
        assert result["reason_counts"].get("MISSING_CANONICAL_ASSERTION",0)>0, field
        assert [len(result["records"][t]) for t in ("treatment_episode","treatment_exposure","clinical_outcome","specimen_registry","episode_binding")] == [0,0,0,0,0], field
        for table in ("treatment_episode","endpoint_obs","specimen"):
            disp=next(d for d in result["dispositions"] if d["legacy_table"]==table)
            lineage=next(r for r in result["lineage"] if r["legacy_table"]==table)
            assert disp["state"]=="WITHHELD" and lineage["canonical_key"] is None and lineage["canonical_table"] is None, (field,table)
        _assert_full_subject_graph_empty_or_closed(result)
    # Even when another required field is missing, an explicit conflicting episode remains a failure.
    meta,supp=_full_episode_subject_bundle()
    exposure_binding=next(b for b in supp["records"]["episode_binding"] if b["subject_type"]=="TREATMENT_EXPOSURE")
    exposure_binding["treatment_episode_id"]="absent-episode"
    del exposure_binding["reviewer"]
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="FAIL" and result["reason_counts"]=={"FOREIGN_KEY_UNRESOLVED":1}


def test_missing_binding_field_does_not_mask_other_schema_errors():
    meta,supp=_full_episode_subject_bundle()
    assert build_legacy_candidate(meta,supp,schema_root=SCHEMAS)["status"]=="STRUCTURAL_CANDIDATE"
    meta,supp=_full_episode_subject_bundle()
    exposure=next(b for b in supp["records"]["episode_binding"] if b["subject_type"]=="TREATMENT_EXPOSURE")
    del exposure["reviewer"]
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="BLOCKED_UNKNOWN"
    assert result["reason_counts"].get("MISSING_CANONICAL_ASSERTION",0)>0
    for mutation in (("role","OUTCOME_ASSESSMENT"),("patient_uid",7)):
        meta,supp=_full_episode_subject_bundle()
        exposure=next(b for b in supp["records"]["episode_binding"] if b["subject_type"]=="TREATMENT_EXPOSURE")
        exposure[mutation[0]]=mutation[1]
        result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
        assert result["status"]=="FAIL" and result["reason_counts"]=={"CANONICAL_SCHEMA_INVALID":1}, mutation
        del exposure["reviewer"]
        result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
        assert result["status"]=="FAIL" and result["reason_counts"]=={"CANONICAL_SCHEMA_INVALID":1}, (mutation,"plus missing reviewer")
    meta,supp=_full_episode_subject_bundle()
    exposure_binding=next(b for b in supp["records"]["episode_binding"] if b["subject_type"]=="TREATMENT_EXPOSURE")
    exposure_binding["treatment_episode_id"]="absent-episode"
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="FAIL" and result["reason_counts"]=={"FOREIGN_KEY_UNRESOLVED":1}


def test_missing_patient_key_with_dependents_withholds_the_complete_closure():
    meta,supp=_episode_exposure_bundle()
    control=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert control["status"]=="STRUCTURAL_CANDIDATE"
    assert [len(control["records"][table]) for table in ("patient_registry","treatment_episode","treatment_exposure","episode_binding")] == [1,1,1,1]
    del supp["records"]["patient_registry"][0]["patient_uid"]
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="BLOCKED_UNKNOWN"
    assert result["reason_counts"].get("MISSING_CANONICAL_ASSERTION",0)>0
    assert [len(result["records"][table]) for table in ("patient_registry","treatment_episode","treatment_exposure","episode_binding")] == [0,0,0,0]
    person=next(d for d in result["dispositions"] if d["legacy_table"]=="person")
    assert person["state"]=="WITHHELD"
    lineage=next(x for x in result["lineage"] if x["legacy_table"]=="person")
    assert lineage["canonical_table"] is None and lineage["canonical_key"] is None
    meta,supp=_episode_exposure_bundle()
    del supp["records"]["patient_registry"][0]["patient_uid"]
    supp["records"]["treatment_episode"][0]["patient_uid"]="unrelated-patient"
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="FAIL" and result["reason_counts"]=={"FOREIGN_KEY_UNRESOLVED":1}


def test_multiple_keyless_proposals_are_permutation_invariant_and_unresolved():
    meta,supp=bundle()
    proposal=supp["records"]["patient_registry"][0]
    del proposal["patient_uid"]
    supp["records"]["patient_registry"].append(dict(proposal))
    first=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    meta2,supp2=bundle()
    proposal=supp2["records"]["patient_registry"][0]
    del proposal["patient_uid"]
    supp2["records"]["patient_registry"].append(dict(proposal))
    supp2["records"]["patient_registry"].reverse()
    supp2["links"].reverse()
    second=build_legacy_candidate(meta2,supp2,schema_root=SCHEMAS)
    assert first==second
    assert first["status"]=="FAIL"
    assert first["reason_counts"]=={"FOREIGN_KEY_UNRESOLVED":1}


def test_canonical_exposure_components_require_explicit_records_and_bindings():
    meta,supp=bundle()
    supp["records"]["treatment_episode"]=[dict(_episode_record(),component_exposure_ids=["exposure-missing"])]
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="FAIL" and result["reason_counts"]=={"FOREIGN_KEY_UNRESOLVED":1}
    meta,supp=bundle()
    supp["records"]["treatment_episode"]=[dict(_episode_record(),component_exposure_ids=["exposure-1"])]
    supp["records"]["treatment_exposure"]=[{"treatment_exposure_id":"exposure-1","patient_uid":"patient-001","regimen_id":"reg-1","agent":"invented","pharmacological_class":"UNKNOWN","monotherapy_or_combination":"UNKNOWN","sequence":None,"line_of_therapy":None,"prior_ici":"UNKNOWN","certainty":"UNRESOLVED","source_locators":[{"kind":"fixture","value":"invented"}]}]
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="FAIL" and result["reason_counts"]=={"FOREIGN_KEY_UNRESOLVED":1}


def test_cohort_is_support_only_and_person_scope_requires_explicit_study():
    meta,supp=bundle()
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert next(d for d in result["dispositions"] if d["legacy_table"]=="cohort")["state"]=="SUPPORT_ONLY"
    assert not any("cohort" in table for table in result["records"])
    meta,supp=bundle()
    meta["tables"]["person"][0]["cohort_id"]="missing-cohort"
    _refresh(meta,("person",)); reanchor(meta,supp)
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="FAIL" and result["reason_counts"]=={"FOREIGN_KEY_UNRESOLVED":1}
    meta,supp=bundle()
    meta["tables"]["study"].append({"study_id":"legacy-study-2","doi":None,"pmid":None,"trial_id":None,"accessions":None,"role_proposed":"SYNTHETIC"})
    meta["tables"]["cohort"].append({"cohort_id":"cohort-002","study_id":"legacy-study-2","definition_rule_id":"rule-002","independence_group_id":"group-002"})
    meta["tables"]["person"][0]["cohort_id"]="cohort-002"
    _refresh(meta,("study","cohort","person")); reanchor(meta,supp)
    supp["records"]["study_registry"].append({"study_id":"study-002","publication_family_id":"family-002","study_title":"Second invented study","study_class":"OTHER","cancer_type":"invented","study_design":"invented","candidate_paper_branches":[],"study_status":"CANDIDATE","source_locators":[{"kind":"fixture","value":"invented"}]})
    supp["records"]["publication_family"].append({"publication_family_id":"family-002","study_id":"study-002","publication_id":"publication-002","publication_role":"OTHER","independence_status":"UNRESOLVED","source_locators":[{"kind":"fixture","value":"invented"}]})
    supp["links"].append({"legacy_table":"study","legacy_key":"legacy-study-2","canonical_table":"study_registry","canonical_key":"study-002","evidence_refs":["fixture"]})
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="FAIL" and result["reason_counts"]=={"FOREIGN_KEY_UNRESOLVED":1}


def test_populated_summary_redacts_sentinels_and_counts_match_records():
    meta,supp=bundle()
    supp["records"]["study_registry"][0]["source_locators"]=[{"kind":"fixture","value":"private-sentinel-locator"}]
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    summary=public_summary(result)
    assert result["status"]=="STRUCTURAL_CANDIDATE"
    assert summary["counts"]["records"]==sum(len(v) for v in result["records"].values())
    assert summary["counts"]["lineage"]==len(result["lineage"])==summary["counts"]["dispositions"]
    assert "private-sentinel-locator" not in json.dumps(summary)
    key_fields={"study_registry":"study_id","publication_family":"publication_family_id","source_record":"source_object_id","patient_registry":"patient_uid","specimen_registry":"specimen_uid","assay_registry":"assay_uid","treatment_episode":"treatment_episode_id","treatment_exposure":"treatment_exposure_id","clinical_outcome":"outcome_id"}
    for d in result["dispositions"]:
        if d["state"]=="MAPPED":
            lineage=next(x for x in result["lineage"] if (x["legacy_table"],x["legacy_key"])==(d["legacy_table"],d["legacy_key"]))
            assert lineage["canonical_key"] is not None
            assert any(r.get(key_fields[lineage["canonical_table"]])==lineage["canonical_key"] for r in result["records"][lineage["canonical_table"]])


def test_missing_all_canonical_proposals_blocks_with_coherent_native_scope():
    meta,supp=bundle(["E01"])
    supp["records"]={table:[] for table in supp["records"]}
    supp["links"]=[]
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="BLOCKED_UNKNOWN"
    assert result["records"]=={table:[] for table in supp["records"]}
    assert next(d for d in result["dispositions"] if d["legacy_table"]=="study")["state"]=="WITHHELD"
    assert next(d for d in result["dispositions"] if d["legacy_table"]=="person")["state"]=="WITHHELD"
    assert next(d for d in result["dispositions"] if d["legacy_table"]=="cohort")["state"]=="SUPPORT_ONLY"
    assert {r["legacy_table"] for r in result["lineage"]}>={"study","person","cohort"}


def test_omitted_study_link_blocks_person_closure_but_bad_native_scope_fails():
    meta,supp=bundle()
    supp["links"]=[link for link in supp["links"] if link["legacy_table"]!="study"]
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="BLOCKED_UNKNOWN"
    assert result["records"]["study_registry"]==[] and result["records"]["patient_registry"]==[]
    assert all(d["state"]=="WITHHELD" for d in result["dispositions"] if d["legacy_table"] in {"study","person"})
    assert all(x["canonical_key"] is None for x in result["lineage"] if x["legacy_table"] in {"study","person"})
    meta,supp=bundle()
    meta["tables"]["cohort"][0]["study_id"]="absent-native-study"
    _refresh(meta,("cohort",)); reanchor(meta,supp)
    result=build_legacy_candidate(meta,supp,schema_root=SCHEMAS)
    assert result["status"]=="FAIL" and result["reason_counts"]=={"FOREIGN_KEY_UNRESOLVED":1}
