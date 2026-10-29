"""Invented fixtures for declarative episode, overlap and exposure proposals."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from tools.a_dav.core import SchemaStore
from tools.a_dav.ingestion_proposals import materialize_proposals, run_admission_chain
from tools.a_dav.worksheet import build_worksheet
from test_group_a import assay_config, packet as registry_packet

STORE = SchemaStore()


def declarations() -> dict[str, Any]:
    return {
        "episode": {
            "id_template": "{patient_uid}:index-episode", "regimen_id": "invented-regimen",
            "index_event": "START_OF_INDEX_TREATMENT", "start_day": None, "stop_day": None,
            "timing_precision": "UNKNOWN", "episode_status": "VERIFIED",
            "source_locators": ["invented-methods"],
        },
        "exposure": {
            "id_template": "{patient_uid}:index-exposure", "regimen_id": "invented-regimen",
            "agent": "invented-agent", "pharmacological_class": "ICI", "sequence": "INDEX",
            "monotherapy_or_combination": "MONOTHERAPY",
            "line_of_therapy": "NOT_REPORTED", "prior_ici_field": "prior_ici",
            "prior_ici_map": {"YES": "YES", "NO": "NO", "UNKNOWN": "UNKNOWN"},
            "certainty": "VERIFIED", "source_locators": [{"kind": "INVENTED", "value": "invented-cohort"}],
        },
        "binding": {
            "id_template": "{subject_type}:{subject_id}:index", "role_by_subject_type": {
                "TREATMENT_EXPOSURE": "TREATMENT_COMPONENT", "SPECIMEN": "PRE_INDEX_BASELINE",
                "CLINICAL_OUTCOME": "OUTCOME_ASSESSMENT"},
            "source_locators": ["invented-binding-evidence"],
        },
        "overlap": {
            "edge_id": "invented-site-independence", "external_node": {"node_type": "STUDY", "node_id": "invented-comparator"},
            "edge_type": "OTHER", "certainty": "UNRESOLVED", "implication_for_independence": "UNKNOWN",
            "evidence": "Invented fixture: site-level independence unknown.",
            "source_locators": [{"kind": "INVENTED", "value": "invented-overlap"}],
            "single_cohort_disposition": "NON_BLOCKING", "joint_split_disposition": "BLOCKING",
        },
        "prior_exposure": {
            "id": "invented-prior-use", "subject_type": "STUDY_FAMILY", "analysis_lineage_id": "invented-lineage",
            "fields_accessed": ["study_identity", "sample_identity", "treatment_metadata"],
            "use": "METADATA_INSPECTION", "occurred_utc": None, "date_precision": "UNKNOWN",
            "actor_role": "invented-reviewer", "independence_implication": "METADATA_ONLY_REVIEWED",
            "source_locators": ["invented-exposure-review"],
        },
        "timing": {"version": "invented-timing-v1", "index_event": "START_OF_INDEX_TREATMENT",
                   "source_locator": "invented-timepoint-source"},
        "stage_config": {
            "timing": {"version": "invented-timing-v1", "index_event": "START_OF_INDEX_TREATMENT",
                        "source_category_only": True},
            "overlap": {"review_complete": True},
            "exposure": {"analysis_lineage_id": "invented-lineage", "review_complete": True,
                         "covered_subjects": [{"subject_type": "STUDY_FAMILY", "subject_id": "f1"}]},
        },
    }


def signed_for(packet: dict[str, Any], *, v5: str = "PASS") -> dict[str, Any]:
    worksheet = build_worksheet(packet)
    worksheet["signature"] = {"reviewer_name": "Invented Reviewer", "review_date": "2026-10-26",
                              "source_reviewer_name": "Invented Reviewer", "source_review_date": "2026-10-26",
                              "integrator_name": "Invented Reviewer", "integration_date": "2026-10-26"}
    worksheet["decisions"] = [{"item_id": item["item_id"],
                               "status": v5 if item.get("gate") == "V5" else
                               "BLOCKED_UNKNOWN" if item.get("gate") == "V8" else
                               "PASS" if item.get("kind") == "gate" else
                               item.get("prefilled_decision", {}).get("status", "PASS"),
                               "rationale": "Invented fixture decision."}
                              for item in worksheet["items"]]
    return worksheet


def proposal_packet() -> dict[str, Any]:
    packet = registry_packet()
    packet["classification"] = "PRIVATE_PATIENT_LEVEL"
    packet["config"].update(declarations()["stage_config"])
    packet["config"]["endpoints"] = {"version": "invented-v1", "category_map": {"invented-partial": "PR"},
                                      "classes": ["ORR"], "source_priority": ["o1"]}
    packet = assay_config(packet)
    packet["config"]["admission"] = {"required_source_object_ids": ["obj1"],
                                     "branch_policies": {"A_BASELINE_BIO": {
                                         "baseline": {"policy_version": "invented-v1", "source_locators": ["invented"]},
                                         "endpoint": {"policy_version": "invented-v1", "source_locators": ["invented"], "endpoint_class": "ORR"}}}}
    packet["config"]["overlap"].update({"external_nodes": [declarations()["overlap"]["external_node"]]})
    packet["config"]["exposure"].update({"covered_subjects": [{"subject_type": "STUDY_FAMILY", "subject_id": "f1"}]})
    packet["records"]["treatment_episode"] = []
    packet["records"]["treatment_exposure"] = []
    packet["records"]["episode_binding"] = []
    packet["records"]["overlap_edge"] = []
    packet["records"]["prior_exposure_record"] = []
    return packet


def test_unsigned_proposals_stay_unverified_and_signed_v5_uses_reported_identity() -> None:
    packet = proposal_packet()
    unsigned = materialize_proposals(packet, declarations())
    assert unsigned["records"]["episode_binding"]
    assert {row["binding_status"] for row in unsigned["records"]["episode_binding"]} == {"BLOCKED_UNKNOWN"}
    assert all(row["reviewer"] is None and row["reviewed_utc"] is None
               for row in unsigned["records"]["episode_binding"])

    worksheet = signed_for(unsigned)
    signed = materialize_proposals(unsigned, declarations(), reviewer_worksheet=worksheet)
    assert {row["binding_status"] for row in signed["records"]["episode_binding"]} == {"VERIFIED"}
    assert all(row["reviewer"] == "Invented Reviewer" and row["reviewed_utc"] == "2026-10-26"
               for row in signed["records"]["episode_binding"])


def test_schema_validity_for_generated_decision_records() -> None:
    packet = proposal_packet()
    result = materialize_proposals(packet, declarations(), reviewer_worksheet=signed_for(packet))
    for table in ("treatment_episode", "treatment_exposure", "episode_binding", "overlap_edge", "prior_exposure_record"):
        for row in result["records"][table]:
            STORE.validate(table, row)


def test_fresh_rebuild_reproduces_reviewed_overlap_records_and_context() -> None:
    packet = proposal_packet()
    declaration = declarations()
    # The user-signed worksheet carries the V6 reviewer identity used by fix5.
    identity = {"reviewer_name": "Invented Reviewer", "review_date": "2026-10-26"}
    rebuilt = materialize_proposals(packet, declaration,
                                    context_reviewer_identity=identity)
    fix5_context = deepcopy(rebuilt)
    for binding in fix5_context["records"]["episode_binding"]:
        binding.update(binding_status="VERIFIED", reviewer=identity["reviewer_name"],
                       reviewed_utc=identity["review_date"], reason="; signer identity SELF_REPORTED")
    fix5_context["config"]["overlap"]["review_complete"] = True
    fix5_context["config"]["exposure"]["review_complete"] = True
    signed = signed_for(fix5_context)
    final = materialize_proposals(packet, declaration, reviewer_worksheet=signed,
                                  rebuild_worksheet_context=True)

    assert fix5_context["records"]["overlap_edge"] == final["records"]["overlap_edge"]
    assert fix5_context["records"]["prior_exposure_record"] == final["records"]["prior_exposure_record"]
    assert build_worksheet(final)["context_hash"] == signed["context_hash"]
    assert len(rebuilt["records"]["overlap_edge"]) == 1
    assert len(rebuilt["records"]["prior_exposure_record"]) == 1


def test_signed_worksheet_without_v5_pass_cannot_verify_bindings() -> None:
    packet = proposal_packet()
    initial = materialize_proposals(packet, declarations())
    worksheet = signed_for(initial, v5="BLOCKED_UNKNOWN")
    result = materialize_proposals(initial, declarations(), reviewer_worksheet=worksheet)
    assert {row["binding_status"] for row in result["records"]["episode_binding"]} == {"BLOCKED_UNKNOWN"}
    assert all(row["reviewer"] is None and row["reviewed_utc"] is None
               for row in result["records"]["episode_binding"])


def test_required_source_roles_resolve_only_declared_roles_to_object_ids() -> None:
    packet = proposal_packet()
    packet["config"]["registries"]["source_roles"] = {"author_fpkm_hg19": "obj1"}
    declaration = declarations()
    declaration["stage_config"]["admission"] = {
        "required_source_roles": ["author_fpkm_hg19"]}

    result = materialize_proposals(packet, declaration)

    assert result["config"]["admission"]["required_source_object_ids"] == ["obj1"]


def test_decision_record_chain_reaches_admission_on_invented_fixture() -> None:
    packet = proposal_packet()
    initial = materialize_proposals(packet, declarations())
    proposed = materialize_proposals(initial, declarations(), reviewer_worksheet=signed_for(initial))
    worksheet = signed_for(proposed)
    result = run_admission_chain(proposed, declarations(), reviewer_worksheet=worksheet, schemas=STORE)
    assert [row["stage"] for row in result["stage_statuses"]] == [
        "registries", "endpoints", "timing", "assays", "overlap", "exposure", "admission"]
    assert result["stage_statuses"][-1]["stage"] == "admission"
    assert result["admission"]["status"] == "READY"
    assert result["packet"]["dependencies"]["admission"] == result["admission"]


def test_split_policy_is_bound_to_admission_sources_and_worksheet_context() -> None:
    packet = proposal_packet()
    declaration = declarations()
    declaration['stage_config']['admission'] = {'required_source_hashes': ['a' * 64]}
    packet['records']['source_record'][0]['sha256'] = 'a' * 64
    declaration['stage_config']['split'] = {'version': 'invented-v1',
        'selection_basis': 'PRESPECIFIED_METADATA', 'performance_observed': False,
        'analysis_lineage_id': 'invented-lineage',
        'policy': {'permanent_role': 'DEVELOPMENT', 'prior_exposure_state': 'METADATA_ONLY'}}
    result = materialize_proposals(packet, declaration)
    assert result['config']['split']['required_source_ids'] == [packet['records']['source_record'][0]['source_object_id']]
    assert build_worksheet(result)['context_hash'] != build_worksheet(packet)['context_hash']


def test_baseline_ranks_are_frozen_from_source_metadata_before_review() -> None:
    packet = proposal_packet()
    declaration = declarations()
    declaration['stage_config']['baseline'] = {
        'selection_basis': 'PRESPECIFIED_METADATA', 'ranking': 'UNIQUE_CANDIDATE',
        'assay_suitability': 'BASELINE_DE', 'coverage_suitability': 'de_suitability',
        'endpoint_policy': {'required': True, 'endpoint_class': 'ORR',
                            'discrepancy_policy': 'SEALED_PREFERRED_OUTCOME'},
        'build_utc': 'AT_BUILD_TIME'}
    result = materialize_proposals(packet, declaration)
    config = result['config']['baseline']
    assert config['specimen_rank'] == {row['specimen_uid']: 0 for row in packet['records']['specimen_registry']}
    assert config['assay_rank'] == {row['assay_uid']: 0 for row in packet['records']['assay_registry']}
    assert config['selection_basis'] == 'PRESPECIFIED_METADATA'


def test_split_uses_existing_admission_sources_when_not_redeclared() -> None:
    packet = proposal_packet()
    declaration = declarations()
    declaration['stage_config']['split'] = {'version':'invented-v1','selection_basis':'PRESPECIFIED_METADATA',
        'performance_observed':False,'analysis_lineage_id':'invented-lineage',
        'policy':{'permanent_role':'DEVELOPMENT','prior_exposure_state':'METADATA_ONLY'}}
    result = materialize_proposals(packet, declaration)
    assert result['config']['split']['required_source_ids'] == ['obj1']


def test_one_signature_builds_the_invented_baseline_table(tmp_path, monkeypatch) -> None:
    import hashlib
    from tools.a_dav import admit, expression_materialization
    data = b'feature\tsample-001\nF1\t0\nF2\t2\n'
    sha = hashlib.sha256(data).hexdigest()
    store = tmp_path / 'store'
    (store / 'objects').mkdir(parents=True)
    (store / 'objects' / sha).write_bytes(data)
    packet = proposal_packet()
    packet['records']['patient_registry'][0]['cancer'] = 'invented'
    packet['records']['source_record'][0]['sha256'] = sha
    packet['config']['registries']['source_hashes']['obj1'] = sha
    packet['config']['assays']['matrices'][0]['source_sha256'] = sha
    declaration = declarations()
    declaration['stage_config']['split'] = {'version':'invented-v1','selection_basis':'PRESPECIFIED_METADATA',
        'performance_observed':False,'analysis_lineage_id':'invented-lineage',
        'policy':{'permanent_role':'DEVELOPMENT','prior_exposure_state':'METADATA_ONLY'}}
    declaration['stage_config']['baseline'] = {'selection_basis':'PRESPECIFIED_METADATA','ranking':'UNIQUE_CANDIDATE',
        'assay_suitability':'BASELINE_DE','coverage_suitability':'de_suitability',
        'endpoint_policy':{'required':True,'endpoint_class':'ORR','discrepancy_policy':'SEALED_PREFERRED_OUTCOME'},
        'build_utc':'AT_BUILD_TIME'}
    unsigned_packet = materialize_proposals(packet, declaration)
    worksheet = signed_for(unsigned_packet)
    field_map = {'proposal_generation':declaration, 'source_objects':{'invented_expression':{'sha256':sha}},
                 'v3':{'delimiters':{'invented_expression':'\t'},'compressed':{'invented_expression':False}}}
    monkeypatch.setattr(admit, 'validate_output_path', lambda path:path)
    monkeypatch.setattr(expression_materialization, 'validate_output_path', lambda path, **kwargs:path)
    result = admit.run_signed_admission(unsigned_packet, field_map, worksheet, tmp_path / 'out', store_root=store)
    assert result['admission']['status'] == 'READY', result['stage_statuses']
    assert result['matrix']['status'] == 'READY', result['matrix']
    assert result['products']['counts']['gene_count'] == 2
    assert result['products']['counts']['expression_patient_count'] == 1
    assert build_worksheet(unsigned_packet)['context_hash'] == worksheet['context_hash']
    monkeypatch.setattr(admit, 'run_ingest', lambda *_args, **_kwargs: {'packet': packet})
    monkeypatch.setattr(admit, 'build_baseline_packet', lambda value:value)
    monkeypatch.setattr(admit, 'materialize_primary_assay_policy', lambda value, *_args:value)
    receipt = tmp_path / 'receipt.json'
    receipt.write_text('{}')
    fresh = admit.run_fresh_signed_admission('invented', 'A_BASELINE_BIO', store, field_map, receipt,
                                             worksheet, tmp_path / 'fresh-out')
    assert fresh['admission']['status'] == 'READY'
    assert fresh['matrix']['status'] == 'READY'
    assert fresh['products']['counts']['expression_patient_count'] == 1


def test_diagnostic_chain_runs_independent_stages_after_one_blocks(monkeypatch):
    from tools.a_dav import ingestion_proposals as module
    calls=[]
    def stage(name, status):
        def run(packet, **kwargs):
            calls.append(name)
            return {'stage':name,'status':status,'reasons':['BLOCKED_REASON'] if status!='READY' else [],'records':packet['records'],'receipt_id':'a'*64}
        return run
    for attr,name,status in [('build_registries','registries','READY'),('map_endpoints','endpoints','BLOCKED_UNKNOWN'),('validate_timing','timing','READY'),('validate_assays','assays','READY'),('validate_overlap','overlap','READY'),('validate_exposure','exposure','READY')]:
        monkeypatch.setattr(module,attr,stage(name,status))
    monkeypatch.setattr(module,'evaluate_admission',lambda packet,**kwargs:{'stage':'admission','status':'BLOCKED_UNKNOWN','reasons':['DEPENDENCY_MISSING'],'records':packet['records']})
    result=module.run_admission_chain({'records':{},'dependencies':{}},{},reviewer_worksheet={},collect_blockers=True)
    assert calls==['registries','endpoints','timing','assays','overlap','exposure']
    assert [s['stage'] for s in result['stage_statuses']]==calls+['admission']
