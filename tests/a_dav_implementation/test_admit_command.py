"""The single-command signed admission path preserves stage receipts."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.a_dav import admit


def test_run_admission_command_persists_full_chain_before_matrix_attempt(
    tmp_path: Path, monkeypatch: Any,
) -> None:
    packet = {"classification": "PRIVATE_PATIENT_LEVEL", "branch_id": "A_BASELINE_BIO",
              "records": {"study_registry": [{"study_id": "invented-study"}],
                          "source_record": []}, "config": {"admission": {}},
              "dependencies": {}}
    worksheet = {"signature": {"reviewer_name": "Invented Reviewer",
                                "review_date": "2026-10-26"}}
    chain = {"packet": {**packet, "dependencies": {
                name: {"stage": name, "status": "READY", "receipt_id": "a" * 64}
                for name in ("registries", "endpoints", "timing", "assays", "overlap", "exposure")}},
             "stage_statuses": [{"stage": name, "status": "READY", "reasons": []}
                                for name in ("registries", "endpoints", "timing", "assays", "overlap", "exposure")]
                               + [{"stage": "admission", "status": "READY", "reasons": []}],
             "admission": {"stage": "admission", "status": "READY", "reasons": [],
                           "records": {"cohort_admission_receipt": []}}}
    seen: dict[str, Any] = {}

    def fake_chain(current: dict[str, Any], declaration: dict[str, Any], *,
                   reviewer_worksheet: dict[str, Any], worksheet_context_packet: dict[str, Any] | None = None,
                   schemas: Any = None) -> dict[str, Any]:
        seen.update(packet=current, declaration=declaration, worksheet=reviewer_worksheet)
        return chain

    monkeypatch.setattr(admit, "run_admission_chain", fake_chain)
    monkeypatch.setattr(admit, "read_worksheet", lambda _path: worksheet)
    monkeypatch.setattr(admit, "materialize_proposals", lambda current, _decl, **_kwargs: current)
    monkeypatch.setattr(admit, "validate_signed_worksheet", lambda *_args: {"decisions": {"V5": "PASS"}})
    monkeypatch.setattr(admit, "validate_output_path", lambda path: path)
    monkeypatch.setattr(admit, "attempt_baseline_build", lambda *_args, **_kwargs: {
        "status": "BLOCKED_UNKNOWN", "reasons": ["SPLIT_NOT_FROZEN"]})

    result = admit.run_signed_admission(packet, {"episode": {}}, worksheet, tmp_path)

    assert [row["stage"] for row in result["stage_statuses"]] == [
        "registries", "endpoints", "timing", "assays", "overlap", "exposure", "admission", "split"]
    assert set(seen["packet"]["dependencies"]) == set()
    assert result["matrix"]["reasons"] == ["SPLIT_NOT_FROZEN"]
    persisted = json.loads((tmp_path / "stage_statuses.json").read_text())
    assert persisted == result["stage_statuses"]


def test_signed_runner_rejects_worksheet_before_any_stage_execution(
    tmp_path: Path, monkeypatch: Any,
) -> None:
    packet = {"records": {}, "config": {}, "branch_id": "A_BASELINE_BIO"}
    monkeypatch.setattr(admit, "validate_signed_worksheet",
                        lambda *_args: (_ for _ in ()).throw(ValueError("WORKSHEET_UNSIGNED")))
    called = False

    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        nonlocal called
        called = True
        raise AssertionError("stage chain must not run before signature validation")

    monkeypatch.setattr(admit, "run_admission_chain", forbidden)
    try:
        admit.run_signed_admission(packet, {}, {}, tmp_path)
    except ValueError as error:
        assert str(error) == "WORKSHEET_UNSIGNED"
    else:
        raise AssertionError("unsigned worksheet unexpectedly accepted")
    assert not called


def test_fresh_runner_records_item_changes_and_stops_before_admission(
    tmp_path: Path, monkeypatch: Any,
) -> None:
    packet = {"records": {}, "config": {"ingestion_validation": {}}}
    regenerated = {"context_hash": "new-context", "items": [
        {"kind": "gate", "gate": "V4", "evidence_pointers": [{"locator": "new"}],
         "prefilled_decision": {"status": "PASS"}}]}
    signed = {"context_hash": "signed-context", "items": [
        {"kind": "gate", "gate": "V4", "evidence_pointers": [{"locator": "old"}],
         "prefilled_decision": {"status": "PASS"}},
        {"kind": "gate", "gate": "V6", "evidence_pointers": [],
         "prefilled_decision": {"status": "PASS"}}]}
    receipt = tmp_path / "receipt.json"
    receipt.write_text("{}")
    monkeypatch.setattr(admit, "validate_output_path", lambda path: path)
    monkeypatch.setattr(admit, "run_ingest", lambda *_args, **_kwargs: {"packet": packet})
    monkeypatch.setattr(admit, "build_baseline_packet", lambda value: value)
    monkeypatch.setattr(admit, "materialize_primary_assay_policy", lambda value, *_args: value)
    monkeypatch.setattr(admit, "materialize_proposals", lambda value, *_args, **_kwargs: value)
    monkeypatch.setattr(admit, "build_worksheet", lambda _value: regenerated)
    monkeypatch.setattr(admit, "run_signed_admission",
                        lambda *_args, **_kwargs: (_ for _ in ()).throw(
                            AssertionError("admission must not run after a context change")))

    result = admit.run_fresh_signed_admission("invented_cohort", "A_BASELINE_BIO", tmp_path,
                                              {}, receipt, signed, tmp_path / "out")

    assert result["status"] == "WORKSHEET_CONTEXT_MISMATCH"
    assert [row["item"] for row in result["changed_items"]] == ["V4", "V6"]
    assert result["changed_items"][0]["changed_fields"] == ["evidence_pointers[0].locator"]
    assert result["changed_items"][1]["changed_fields"] == ["item_count"]
    diff = json.loads((tmp_path / "out/pre-admission/worksheet_context_diff.json").read_text())
    assert diff["status"] == "WORKSHEET_CONTEXT_MISMATCH"


def test_fresh_preflight_does_not_change_unsigned_context_from_signer_decisions(tmp_path: Path, monkeypatch: Any) -> None:
    packet = {'records': {}, 'config': {'ingestion_validation': {}}}
    worksheet = {'context_hash': 'frozen-unsigned-context', 'items': [],
                 'signature': {'reviewer_name': 'Invented Reviewer', 'review_date': '2026-10-27'},
                 'decisions': [{'item_id': 'V6', 'status': 'PASS'}]}
    receipt = tmp_path / 'receipt.json'
    receipt.write_text('{}')
    monkeypatch.setattr(admit, 'validate_output_path', lambda path: path)
    monkeypatch.setattr(admit, 'run_ingest', lambda *_args, **_kwargs: {'packet': packet})
    monkeypatch.setattr(admit, 'build_baseline_packet', lambda value: value)
    monkeypatch.setattr(admit, 'materialize_primary_assay_policy', lambda value, *_args: value)
    seen: dict[str, Any] = {}
    def proposals(value: dict[str, Any], _declaration: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        seen.update(kwargs)
        return value
    monkeypatch.setattr(admit, 'materialize_proposals', proposals)
    monkeypatch.setattr(admit, 'build_worksheet', lambda _value: worksheet)
    monkeypatch.setattr(admit, 'run_signed_admission', lambda *_args, **_kwargs: {'status': 'COMPLETE'})
    result = admit.run_fresh_signed_admission('invented', 'A_BASELINE_BIO', tmp_path, {}, receipt,
                                              worksheet, tmp_path / 'out')
    assert result['status'] == 'COMPLETE'
    assert seen.get('reviewer_worksheet') is None
    assert seen.get('context_reviewer_identity') is None


def test_provisional_cli_is_available_without_a_signature():
    import subprocess
    import sys
    result = subprocess.run([sys.executable, '-B', '-m', 'tools.a_dav.admit', '--help'],
                            capture_output=True, text=True)
    assert result.returncode == 0
    assert '--provisional' in result.stdout


def test_signed_admission_builds_expression_products_after_baseline(tmp_path: Path, monkeypatch: Any) -> None:
    packet = {'classification':'SYNTHETIC_ONLY', 'branch_id':'A_BASELINE_BIO',
              'records':{'patient_registry':[], 'study_registry':[]},
              'config':{'assays':{'matrices':[{'source_sha256':'a' * 64}]}}, 'dependencies':{}}
    admission = {'stage':'admission','status':'READY','reasons':[],'records':{}}
    chain = {'packet':packet,'admission':admission,'stage_statuses':[]}
    baseline = {'status':'READY','reasons':[],'records':{'baseline':[]}}
    matrix = {'status':'READY','reasons':[],'baseline':baseline,'split':{'status':'READY','reasons':[]}}
    monkeypatch.setattr(admit, 'ensure_field_map_matches', lambda *_args: None)
    monkeypatch.setattr(admit, 'validate_signed_worksheet', lambda *_args: {'decisions':{}})
    monkeypatch.setattr(admit, 'materialize_proposals', lambda value, *_args, **_kwargs:value)
    monkeypatch.setattr(admit, 'run_admission_chain', lambda *_args, **_kwargs:chain)
    monkeypatch.setattr(admit, 'attempt_baseline_build', lambda *_args, **_kwargs:matrix)
    monkeypatch.setattr(admit, 'validate_output_path', lambda value:value)
    import tools.a_dav.expression_materialization as expression
    seen: dict[str, Any] = {}
    def writer(*args: Any, **kwargs: Any) -> dict[str, Any]:
        seen['called'] = True
        return {'counts':{}}
    monkeypatch.setattr(expression, 'write_validated_products', writer)
    fmap = {'source_objects':{'invented_expression':{'sha256':'a' * 64}},
            'v3':{'delimiters':{'invented_expression':','},'compressed':{'invented_expression':False}}}
    result = admit.run_signed_admission(packet, fmap, {'items':[]}, tmp_path / 'out', store_root=tmp_path)
    assert seen['called']
    assert result['products'] == {'counts':{}}


def test_admit_cli_returns_failure_when_signed_build_blocks(tmp_path: Path, monkeypatch: Any) -> None:
    from tools.a_dav import field_maps
    monkeypatch.setattr(admit, 'read_worksheet', lambda _: {'signature': {'reviewer_name':'invented'}})
    monkeypatch.setattr(field_maps, 'load_field_map', lambda _: {})
    monkeypatch.setattr(admit, '_read_packet', lambda _: {})
    monkeypatch.setattr(admit, 'run_signed_admission', lambda *_args, **_kwargs: {
        'admission':{'status':'BLOCKED_UNKNOWN'}, 'matrix':None, 'products':None})
    assert admit.main(['--packet','invented.json','--worksheet','signed.json','--field-map','map.json',
                       '--out',str(tmp_path / 'out')]) != 0


def test_fresh_admission_never_overwrites_an_existing_run(tmp_path: Path, monkeypatch: Any) -> None:
    import pytest
    from tools.a_dav.core import DavError
    output = tmp_path / 'existing-run'
    output.mkdir()
    marker = output / 'SUMMARY.json'
    marker.write_text('existing')
    monkeypatch.setattr(admit, 'validate_output_path', lambda path:path)
    monkeypatch.setattr(admit, 'run_ingest', lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError('must stop before ingestion')))
    with pytest.raises(DavError, match='OUTPUT_ALREADY_EXISTS'):
        admit.run_fresh_signed_admission('invented', 'A_BASELINE_BIO', tmp_path, {}, tmp_path / 'v3', {}, output)
    assert marker.read_text() == 'existing'


def test_geo_ingest_proposals_are_preserved_when_no_legacy_declaration():
    from tools.a_dav.admit import materialize_configured_proposals
    packet = {'records': {'treatment_episode': [{'episode_status': 'BLOCKED_UNKNOWN'}]}}
    assert materialize_configured_proposals(packet, {'geo_ingest': {}}) == packet


def test_fresh_signed_geo_preflight_keeps_source_proposals(tmp_path: Path, monkeypatch: Any) -> None:
    packet = {'records': {'treatment_episode': [{'episode_status':'BLOCKED_UNKNOWN'}]}, 'config': {'ingestion_validation': {}}}
    worksheet = {'context_hash':'old','items':[]}
    receipt = tmp_path / 'receipt.json'; receipt.write_text('{}')
    monkeypatch.setattr(admit, 'validate_output_path', lambda path:path)
    monkeypatch.setattr(admit, 'run_ingest', lambda *_args, **_kwargs:{'packet':packet})
    monkeypatch.setattr(admit, 'build_baseline_packet', lambda value, **kwargs:value)
    monkeypatch.setattr(admit, 'materialize_primary_assay_policy', lambda value, *_args:value)
    monkeypatch.setattr(admit, 'build_worksheet', lambda value:{'context_hash':'new','items':[]})
    monkeypatch.setattr(admit, 'materialize_proposals', lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError('must preserve GEO proposals')))
    result=admit.run_fresh_signed_admission('invented','A_BASELINE_BIO',tmp_path,{'geo_ingest':{}},receipt,worksheet,tmp_path/'out')
    assert result['status']=='WORKSHEET_CONTEXT_MISMATCH'
    assert result['packet']['records']['treatment_episode'][0]['episode_status']=='BLOCKED_UNKNOWN'


def test_signed_geo_admission_keeps_existing_proposals_and_reports_stage_blocker(tmp_path: Path, monkeypatch: Any) -> None:
    packet={'classification':'SYNTHETIC_ONLY','branch_id':'A_BASELINE_BIO','records':{'study_registry':[]},'config':{},'dependencies':{}}
    monkeypatch.setattr(admit,'ensure_field_map_matches',lambda *_:None)
    monkeypatch.setattr(admit,'validate_signed_worksheet',lambda *_:{'decisions':{}})
    monkeypatch.setattr(admit,'materialize_proposals',lambda *_args, **_kwargs:(_ for _ in ()).throw(AssertionError('must preserve GEO proposals')))
    monkeypatch.setattr(admit,'run_admission_chain',lambda p,*_args,**_kwargs:{'packet':p,'stage_statuses':[{'stage':'registries','status':'BLOCKED_UNKNOWN','reasons':['IDENTITY_UNRESOLVED']}], 'admission':{'status':'BLOCKED_UNKNOWN','reasons':['IDENTITY_UNRESOLVED']}})
    monkeypatch.setattr(admit,'validate_output_path',lambda p:p)
    result=admit.run_signed_admission(packet,{'geo_ingest':{}},{'items':[]},tmp_path/'out')
    assert result['admission']['reasons']==['IDENTITY_UNRESOLVED']
    assert (tmp_path/'out'/'SUMMARY.json').exists()


def test_geo_identity_requires_signed_v4_and_source_characteristic(tmp_path: Path) -> None:
    import copy
    import hashlib
    import pytest
    from tools.a_dav.core import DavError
    from tools.a_dav.worksheet import build_worksheet
    from tools.a_dav.admit import verify_signed_geo_identities
    raw=(b'^SAMPLE = invented-sample\n!Sample_geo_accession = invented-sample\n!Sample_title = invented-title\n!Sample_characteristics_ch1 = patient id: invented-patient\n')
    sha=hashlib.sha256(raw).hexdigest(); (tmp_path/'objects').mkdir(); (tmp_path/'objects'/sha).write_bytes(raw)
    (tmp_path/'MANIFEST.json').write_text(json.dumps({'objects':{sha:{'locator':'https://example.org/source','version':'1','byte_size':len(raw),'retrieved_at':'2026-10-29'}}}))
    fmap={'geo_ingest':{}, 'geo':{'characteristics':{'patient':'patient id'}}, 'sample_identity':{'patient_characteristic':'patient id'}, 'source_objects':{'geo_family_soft':{'sha256':sha,'locator':'https://example.org/source'}}}
    packet={'branch_id':'A_BASELINE_BIO','records':{'study_registry':[{'study_id':'invented-study'}], 'source_record':[], 'patient_registry':[{'patient_uid':'invented-uid','source_patient_id':'invented-patient','patient_identity_confidence':'UNRESOLVED','source_locators':[]}], 'specimen_registry':[{'patient_uid':'invented-uid','raw_sample_aliases':['invented-sample']}]},'config':{}}
    worksheet=build_worksheet(packet)
    worksheet.update(review_status='SIGNED',signature={'reviewer_name':'invented reviewer','review_date':'2026-10-29'},decisions=[{'item_id':item['item_id'],'status':'PASS'} for item in worksheet['items']])
    # No source records implies controlled-access validation; provide reviewer roles.
    worksheet['signature'].update(source_reviewer_name='invented',source_review_date='2026-10-29',integrator_name='invented',integration_date='2026-10-29')
    verified=verify_signed_geo_identities(packet,fmap,worksheet,tmp_path)
    assert verified['records']['patient_registry'][0]['patient_identity_confidence']=='VERIFIED'
    assert packet['records']['patient_registry'][0]['patient_identity_confidence']=='UNRESOLVED'
    assert any('V4' in loc['value'] for loc in verified['records']['patient_registry'][0]['source_locators'])
    not_pass=copy.deepcopy(worksheet); next(d for d in not_pass['decisions'] if d['item_id']=='V4')['status']='BLOCKED_UNKNOWN'
    assert verify_signed_geo_identities(packet,fmap,not_pass,tmp_path)['records']['patient_registry'][0]['patient_identity_confidence']=='UNRESOLVED'
    unverified=copy.deepcopy(fmap);unverified['geo_ingest']['patient_mapping_unverified']=True
    assert verify_signed_geo_identities(packet,unverified,worksheet,tmp_path)['records']['patient_registry'][0]['patient_identity_confidence']=='UNRESOLVED'
    no_characteristic=copy.deepcopy(fmap);no_characteristic['geo']['characteristics'].pop('patient')
    assert verify_signed_geo_identities(packet,no_characteristic,worksheet,tmp_path)['records']['patient_registry'][0]['patient_identity_confidence']=='UNRESOLVED'
    wrong=copy.deepcopy(packet);wrong['records']['patient_registry'][0]['source_patient_id']='different'
    wrong_sheet=build_worksheet(wrong); wrong_sheet.update(review_status='SIGNED',signature=worksheet['signature'],decisions=worksheet['decisions'])
    assert verify_signed_geo_identities(wrong,fmap,wrong_sheet,tmp_path)['records']['patient_registry'][0]['patient_identity_confidence']=='UNRESOLVED'
    unsigned=build_worksheet(packet)
    with pytest.raises(DavError): verify_signed_geo_identities(packet,fmap,unsigned,tmp_path)


def test_unsigned_status_with_signature_never_verifies_geo_identity(tmp_path: Path) -> None:
    import pytest
    from tools.a_dav.core import DavError
    from tools.a_dav.worksheet import build_worksheet
    from tools.a_dav.admit import verify_signed_geo_identities
    packet={'branch_id':'A_BASELINE_BIO','records':{'study_registry':[{'study_id':'invented-study'}], 'source_record':[]},'config':{}}
    worksheet=build_worksheet(packet)
    worksheet['signature']={'reviewer_name':'invented', 'review_date':'2026-10-29', 'source_reviewer_name':'invented', 'source_review_date':'2026-10-29', 'integrator_name':'invented', 'integration_date':'2026-10-29'}
    worksheet['decisions']=[{'item_id':item['item_id'],'status':'PASS'} for item in worksheet['items']]
    with pytest.raises(DavError, match='WORKSHEET_UNSIGNED'):
        verify_signed_geo_identities(packet, {'geo_ingest':{}}, worksheet, tmp_path)


def test_signed_v5_binds_outcome_only_to_the_unique_declared_index_episode():
    import copy
    import pytest
    from tools.a_dav.core import DavError, SchemaStore
    from tools.a_dav.worksheet import build_worksheet
    from tools.a_dav.admit import verify_signed_geo_outcome_bindings
    packet={'classification':'SYNTHETIC_ONLY','branch_id':'A_BASELINE_BIO','records':{'study_registry':[{'study_id':'invented'}], 'source_record':[], 'clinical_outcome':[{'outcome_id':'outcome','patient_uid':'patient'}], 'treatment_episode':[{'patient_uid':'patient','treatment_episode_id':'episode','regimen_id':'regimen','index_event':'index'}], 'episode_binding':[]},'config':{}}
    field={'geo_ingest':{},'treatment_proposal':{'regimen_id':'regimen','index_event':'index','source_locator':'https://example.org/treatment'}}
    w=build_worksheet(packet); w.update(review_status='SIGNED',signature={'reviewer_name':'invented','review_date':'2026-10-29','source_reviewer_name':'invented','source_review_date':'2026-10-29','integrator_name':'invented','integration_date':'2026-10-29'},decisions=[{'item_id':item['item_id'],'status':'PASS'} for item in w['items']])
    verified=verify_signed_geo_outcome_bindings(packet,field,w)
    binding=verified['records']['episode_binding'][0]
    assert binding['binding_status']=='VERIFIED' and binding['treatment_episode_id']=='episode'
    assert any('V5' in x for x in binding['source_locators']) and 'https://example.org/treatment' in binding['source_locators']
    SchemaStore().validate('episode_binding',binding)
    assert packet['records']['episode_binding']==[]
    other=copy.deepcopy(w);next(d for d in other['decisions'] if d['item_id']=='V5')['status']='BLOCKED_UNKNOWN'
    assert verify_signed_geo_outcome_bindings(packet,field,other)['records']['episode_binding']==[]
    multiple=copy.deepcopy(packet);multiple['records']['treatment_episode'].append(dict(multiple['records']['treatment_episode'][0],treatment_episode_id='other'))
    mw=build_worksheet(multiple);mw.update(review_status='SIGNED',signature=w['signature'],decisions=w['decisions'])
    assert verify_signed_geo_outcome_bindings(multiple,field,mw)['records']['episode_binding']==[]
    unsigned=copy.deepcopy(w);unsigned['review_status']='UNSIGNED'
    with pytest.raises(DavError):verify_signed_geo_outcome_bindings(packet,field,unsigned)


def test_geo_title_identity_needs_explicit_opt_in_and_signed_v4(tmp_path: Path) -> None:
    import copy
    import hashlib
    from tools.a_dav.worksheet import build_worksheet
    from tools.a_dav.admit import verify_signed_geo_identities
    raw=b'^SAMPLE = sample\n!Sample_geo_accession = sample\n!Sample_title = person_PRE\n';sha=hashlib.sha256(raw).hexdigest();(tmp_path/'objects').mkdir();(tmp_path/'objects'/sha).write_bytes(raw)
    (tmp_path/'MANIFEST.json').write_text(json.dumps({'objects':{sha:{'locator':'https://example.org','version':'1','byte_size':len(raw),'retrieved_at':'2026-10-29'}}}))
    f={'geo_ingest':{},'geo':{'characteristics':{}},'sample_identity':{'title_regex':'^([a-z]+)_','patient_group':1},'source_objects':{'geo_family_soft':{'sha256':sha}}}
    p={'branch_id':'A_BASELINE_BIO','records':{'study_registry':[{'study_id':'study'}],'source_record':[],'patient_registry':[{'patient_uid':'uid','source_patient_id':'person','patient_identity_confidence':'UNRESOLVED','source_locators':[]}],'specimen_registry':[{'patient_uid':'uid','raw_sample_aliases':['sample']}]},'config':{}}
    w=build_worksheet(p);w.update(review_status='SIGNED',signature={'reviewer_name':'invented','review_date':'2026-10-29','source_reviewer_name':'invented','source_review_date':'2026-10-29','integrator_name':'invented','integration_date':'2026-10-29'},decisions=[{'item_id':item['item_id'],'status':'PASS'} for item in w['items']])
    assert verify_signed_geo_identities(p,f,w,tmp_path)['records']['patient_registry'][0]['patient_identity_confidence']=='UNRESOLVED'
    f['sample_identity']['accept_title_token_with_signed_v4']=True
    assert verify_signed_geo_identities(p,f,w,tmp_path)['records']['patient_registry'][0]['patient_identity_confidence']=='VERIFIED'
    blocked=copy.deepcopy(w);next(d for d in blocked['decisions'] if d['item_id']=='V4')['status']='BLOCKED_UNKNOWN'
    assert verify_signed_geo_identities(p,f,blocked,tmp_path)['records']['patient_registry'][0]['patient_identity_confidence']=='UNRESOLVED'


def test_signed_v5_materializes_declared_binary_endpoint_without_orr_conversion():
    from tools.a_dav.worksheet import build_worksheet
    from tools.a_dav.admit import materialize_signed_geo_endpoints
    packet={'branch_id':'A_BASELINE_BIO','records':{'study_registry':[{'study_id':'invented'}], 'source_record':[], 'clinical_outcome':[{'patient_uid':'patient','outcome_id':'outcome','raw_endpoint_label':'yes','canonical_category':'SOURCE_POSITIVE','endpoint_class':'SOURCE_BINARY','evaluability':'UNKNOWN','discrepancy_status':'UNRESOLVED'}]},'config':{'endpoints':{'version':'field-map'}}}
    field={'geo_ingest':{'response_map':{'yes':'SOURCE_POSITIVE','no':'SOURCE_NEGATIVE'}},'decision_config':{'endpoint':{'source_binary_definition':{'citation':'https://example.org/definition'}}}}
    w=build_worksheet(packet);w.update(review_status='SIGNED',signature={'reviewer_name':'invented','review_date':'2026-10-29','source_reviewer_name':'invented','source_review_date':'2026-10-29','integrator_name':'invented','integration_date':'2026-10-29'},decisions=[{'item_id':x['item_id'],'status':'PASS'} for x in w['items']])
    result=materialize_signed_geo_endpoints(packet,field,w)
    outcome=result['records']['clinical_outcome'][0];definition=result['config']['endpoints']['binary_definitions']['outcome']
    assert outcome['evaluability']=='EVALUABLE' and outcome['endpoint_class']=='SOURCE_BINARY'
    assert definition['source_locator']=='https://example.org/definition' and definition['raw_value_map']=={'yes':1,'no':0}
    assert packet['records']['clinical_outcome'][0]['evaluability']=='UNKNOWN'


def test_signed_v5_binds_declared_treatment_component_without_inventing_dates():
    from tools.a_dav.worksheet import build_worksheet
    from tools.a_dav.admit import verify_signed_geo_outcome_bindings
    packet={'classification':'SYNTHETIC_ONLY','branch_id':'A_BASELINE_BIO','records':{'study_registry':[{'study_id':'invented'}], 'source_record':[], 'clinical_outcome':[], 'treatment_episode':[{'patient_uid':'patient','treatment_episode_id':'episode','regimen_id':'regimen','index_event':'index','component_exposure_ids':['component']}], 'treatment_exposure':[{'patient_uid':'patient','treatment_exposure_id':'component','regimen_id':'regimen','start_date_or_day':None}], 'episode_binding':[]},'config':{}}
    f={'geo_ingest':{},'treatment_proposal':{'regimen_id':'regimen','index_event':'index','source_locator':'https://example.org/treatment'}}
    w=build_worksheet(packet);w.update(review_status='SIGNED',signature={'reviewer_name':'invented','review_date':'2026-10-29','source_reviewer_name':'invented','source_review_date':'2026-10-29','integrator_name':'invented','integration_date':'2026-10-29'},decisions=[{'item_id':i['item_id'],'status':'PASS'} for i in w['items']])
    result=verify_signed_geo_outcome_bindings(packet,f,w)
    assert result['records']['episode_binding'][0]['subject_type']=='TREATMENT_EXPOSURE'
    assert result['records']['episode_binding'][0]['binding_status']=='VERIFIED'
    assert result['records']['treatment_exposure'][0]['start_date_or_day'] is None


def test_signed_v5_links_only_source_declared_baseline_specimens():
    from tools.a_dav.worksheet import build_worksheet
    from tools.a_dav.admit import verify_signed_geo_outcome_bindings
    p={'classification':'SYNTHETIC_ONLY','branch_id':'A_BASELINE_BIO','records':{'study_registry':[{'study_id':'invented'}],'source_record':[],'clinical_outcome':[],'treatment_episode':[{'patient_uid':'p','treatment_episode_id':'episode','regimen_id':'r','index_event':'start','component_exposure_ids':[]}],'treatment_exposure':[], 'episode_binding':[],'specimen_registry':[{'patient_uid':'p','specimen_uid':'pre','timing_raw_text':'PRE','canonical_timing_category':'PRE_INDEX_BASELINE'}, {'patient_uid':'p','specimen_uid':'other','timing_raw_text':'unknown','canonical_timing_category':'UNKNOWN'}]},'config':{}}
    f={'geo_ingest':{'baseline_values':['PRE']},'source_objects':{'geo_family_soft':{'locator':'https://example.org/geo'}},'treatment_proposal':{'regimen_id':'r','index_event':'start','source_locator':'https://example.org/treatment'}}
    w=build_worksheet(p);w.update(review_status='SIGNED',signature={'reviewer_name':'invented','review_date':'2026-10-29','source_reviewer_name':'invented','source_review_date':'2026-10-29','integrator_name':'invented','integration_date':'2026-10-29'},decisions=[{'item_id':i['item_id'],'status':'PASS'} for i in w['items']])
    result=verify_signed_geo_outcome_bindings(p,f,w)
    assert [x['subject_id'] for x in result['records']['episode_binding']]==['pre']
    assert result['config']['timing']['specimens']['pre']['precision']=='SOURCE_CATEGORY'
    assert result['config']['timing']['episode_order']==['episode']
    assert result['config']['timing']['version']=='field-map-signed-v5'
    assert result['records']['specimen_registry'][1]['canonical_timing_category']=='UNKNOWN'


def test_signed_v5_verifies_declared_episode_and_component_without_filling_unknowns():
    from tools.a_dav.worksheet import build_worksheet
    from tools.a_dav.admit import verify_signed_geo_outcome_bindings
    p={'classification':'SYNTHETIC_ONLY','branch_id':'A_BASELINE_BIO','records':{'study_registry':[{'study_id':'s'}], 'source_record':[], 'clinical_outcome':[], 'treatment_episode':[{'patient_uid':'p','treatment_episode_id':'e','regimen_id':'r','index_event':'start','component_exposure_ids':['x'],'episode_status':'BLOCKED_UNKNOWN','prior_ici':'UNKNOWN'}], 'treatment_exposure':[{'patient_uid':'p','treatment_exposure_id':'x','regimen_id':'r','certainty':'UNRESOLVED','agent':'UNKNOWN','prior_ici':'UNKNOWN','start_date_or_day':None,'stop_date_or_day':None}], 'episode_binding':[]},'config':{}}
    f={'geo_ingest':{},'treatment_proposal':{'regimen_id':'r','index_event':'start','source_locator':'https://example.org/treatment'}}
    w=build_worksheet(p);w.update(review_status='SIGNED',signature={'reviewer_name':'invented','review_date':'2026-10-29','source_reviewer_name':'invented','source_review_date':'2026-10-29','integrator_name':'invented','integration_date':'2026-10-29'},decisions=[{'item_id':i['item_id'],'status':'PASS'} for i in w['items']])
    result=verify_signed_geo_outcome_bindings(p,f,w)
    episode=result['records']['treatment_episode'][0]; exposure=result['records']['treatment_exposure'][0]
    assert episode['episode_status']=='VERIFIED' and exposure['certainty']=='VERIFIED'
    assert episode['prior_ici']==exposure['prior_ici']=='UNKNOWN' and exposure['agent']=='UNKNOWN'


def test_signed_v6_preserves_declared_possible_overlap_as_a_protective_edge():
    import copy
    from tools.a_dav.core import SchemaStore
    from tools.a_dav.worksheet import build_worksheet
    from tools.a_dav.admit import materialize_signed_geo_overlap
    p={'branch_id':'A_BASELINE_BIO','records':{'study_registry':[{'study_id':'study'}],'source_record':[],'overlap_edge':[]},'config':{}}
    f={'geo_ingest':{},'decision_config':{'overlap_review':{'source_locator':'docs/decisions/invented.md','edges':[{'target_node_type':'STUDY','target_node_id':'other','edge_type':'SUSPECTED_SAME_PATIENT','certainty':'POSSIBLE','implication_for_independence':'INDEPENDENCE_BLOCKED','evidence':'Possible overlap remains unresolved.'}]}}}
    w=build_worksheet(p);w.update(review_status='SIGNED',signature={'reviewer_name':'invented','review_date':'2026-10-29','source_reviewer_name':'invented','source_review_date':'2026-10-29','integrator_name':'invented','integration_date':'2026-10-29'},decisions=[{'item_id':i['item_id'],'status':'PASS'} for i in w['items']])
    result=materialize_signed_geo_overlap(p,f,w)
    assert result['config']['overlap']['review_complete'] is True
    assert result['records']['overlap_edge'][0]['implication_for_independence']=='INDEPENDENCE_BLOCKED'
    assert result['records']['overlap_edge'][0]['certainty']=='POSSIBLE'
    SchemaStore().validate('overlap_edge', result['records']['overlap_edge'][0])
    assert p['records']['overlap_edge']==[]
    blocked=copy.deepcopy(w);next(d for d in blocked['decisions'] if d['item_id']=='V6')['status']='BLOCKED_UNKNOWN'
    assert materialize_signed_geo_overlap(p,f,blocked)['records']['overlap_edge']==[]


def test_signed_geo_admission_policy_uses_declared_roles_and_endpoint_class():
    from tools.a_dav.worksheet import build_worksheet
    from tools.a_dav.admit import materialize_signed_geo_admission_policy
    p={'branch_id':'A_BASELINE_BIO','records':{'study_registry':[{'study_id':'study'}], 'source_record':[]},'config':{'registries':{'source_roles':{'geo':'source-geo','matrix':'source-matrix'}}}}
    f={'geo_ingest':{'endpoint_class':'SOURCE_BINARY'},'decision_config':{'preview':{'required_roles':['geo','matrix']},'endpoint':{'source_binary_definition':{'citation':'https://example.org/definition'}}},'source_objects':{'geo_family_soft':{'locator':'https://example.org/geo'}}}
    w=build_worksheet(p);w.update(review_status='SIGNED',signature={'reviewer_name':'invented','review_date':'2026-10-29','source_reviewer_name':'invented','source_review_date':'2026-10-29','integrator_name':'invented','integration_date':'2026-10-29'},decisions=[{'item_id':i['item_id'],'status':'PASS'} for i in w['items']])
    result=materialize_signed_geo_admission_policy(p,f,w)
    cfg=result['config']['admission']; assert cfg['required_source_object_ids']==['source-geo','source-matrix']
    assert cfg['branch_policies']['A_BASELINE_BIO']['endpoint']['endpoint_class']=='SOURCE_BINARY'
    assert 'admission' not in p['config']


def test_signed_geo_source_certification_requires_hash_adapter_and_review_decisions():
    from tools.a_dav.admit import certify_required_source_validation
    p={'records':{'source_record':[{'sha256':'a'*64,'retrieval_status':'RETRIEVED','hash_scope':'FULL_OBJECT','validation_status':'STRUCTURAL_ONLY'}], 'patient_registry':[{'patient_identity_confidence':'VERIFIED'}], 'clinical_outcome':[{'outcome_id':'outcome'}], 'episode_binding':[{'subject_type':'CLINICAL_OUTCOME','subject_id':'outcome','binding_status':'VERIFIED'}]},'config':{}}
    f={'geo_ingest':{},'decision_config':{'preview':{'required_roles':['geo']}},'source_objects':{'geo':{'sha256':'a'*64,'format':'GEO_FAMILY_SOFT'}}}
    evidence={'sha256_verified_roles':['geo'],'parsed_source_roles':['geo'],'adapter_by_role':{'geo':'GEO_FAMILY_SOFT'}}
    decisions={'V2':'PASS','V3':'PASS','V4':'PASS','V5':'PASS'}
    assert certify_required_source_validation(p,f,decisions,evidence)['records']['source_record'][0]['validation_status']=='PASS'
    assert certify_required_source_validation(p,f,{**decisions,'V2':'BLOCKED_UNKNOWN'},evidence)['records']['source_record'][0]['validation_status']=='STRUCTURAL_ONLY'
    assert certify_required_source_validation(p,f,decisions,{**evidence,'parsed_source_roles':[]})['records']['source_record'][0]['validation_status']=='STRUCTURAL_ONLY'


def test_signed_development_declarations_scope_specimens_and_record_reviewed_metadata():
    import copy

    from tools.a_dav.admit import materialize_signed_geo_development_policy
    from tools.a_dav.worksheet import build_worksheet
    p = {'classification':'SYNTHETIC_ONLY', 'branch_id':'A_BASELINE_BIO', 'records':{
        'study_registry':[{'study_id':'study'}], 'publication_family':[{'publication_family_id':'family'}],
        'patient_registry':[{'patient_uid':'p'}],
        'specimen_registry':[{'specimen_uid':'pre','canonical_timing_category':'PRE_INDEX_BASELINE'}, {'specimen_uid':'other','canonical_timing_category':'UNKNOWN','timing_raw_text':'ON'}, {'specimen_uid':'uncertain','canonical_timing_category':'UNKNOWN','timing_raw_text':'UNRESOLVED'}],
        'prior_exposure_record':[{'exposure_id':'existing'}], 'assay_registry':[{'assay_uid':'a1','specimen_uid':'pre','source_object_id':'src','branch_suitability':[]}, {'assay_uid':'a2','specimen_uid':'other','source_object_id':'src','branch_suitability':[]}], 'episode_binding':[]}, 'config':{'admission':{'required_source_object_ids':['src']},'assays':{'matrices':[{'source_object_id':'src','feature_scope':'COMPLETE','lane':'CONTINUOUS','headers':[],'values':[]}]}}}
    f={'geo_ingest':{'endpoint_class':'TUMOUR_RESPONSE'}, 'decision_config':{'development_policy':{'prior_ici_policy':'UNKNOWN_ALLOWED_DEVELOPMENT', 'nonbaseline_specimens':'OUTSIDE_BRANCH', 'nonbaseline_visit_values':['ON'], 'split_role':'DEVELOPMENT', 'exposure_state':'METADATA_ONLY', 'review_complete':True, 'covered_subject_types':['STUDY_FAMILY','PATIENT_SET'], 'cancer':'INVENTED', 'cancer_source_locator':'invented-decision', 'analysis_lineage_id':'invented-lineage', 'source_locator':'invented-decision'}}}
    w=build_worksheet(p); w.update(review_status='SIGNED',signature={'reviewer_name':'invented','review_date':'2026-10-29','source_reviewer_name':'invented','source_review_date':'2026-10-29','integrator_name':'invented','integration_date':'2026-10-29'},decisions=[{'item_id':i['item_id'],'status':'PASS'} for i in w['items']])
    result=materialize_signed_geo_development_policy(p,f,w)
    assert [s['specimen_uid'] for s in result['records']['specimen_registry']]==['pre','uncertain']
    assert [a['specimen_uid'] for a in result['records']['assay_registry']]==['pre']
    assert result['config']['timing']['prior_ici_policy']=='UNKNOWN_ALLOWED_DEVELOPMENT'
    assert result['config']['split']['policy']['permanent_role']=='DEVELOPMENT'
    assert result['config']['exposure']['review_complete'] is True
    assert result['records']['patient_registry'][0]['cancer']=='INVENTED'
    assert result['config']['baseline']['endpoint_policy']['endpoint_class']=='ORR'
    assert 'BASELINE_DE' in result['records']['assay_registry'][0]['branch_suitability']
    assert result['records']['prior_exposure_record'][0]['exposure_id']=='existing'
    assert {r['subject_type'] for r in result['records']['prior_exposure_record'][1:]}=={'STUDY_FAMILY','PATIENT_SET'}
    from tools.a_dav.core import SchemaStore
    for row in result['records']['prior_exposure_record'][1:]:
        SchemaStore().validate('prior_exposure_record', row)
    assert len(p['records']['specimen_registry'])==3
    blocked=copy.deepcopy(w); next(d for d in blocked['decisions'] if d['item_id']=='V6')['status']='BLOCKED_UNKNOWN'
    assert materialize_signed_geo_development_policy(p,f,blocked)==p
