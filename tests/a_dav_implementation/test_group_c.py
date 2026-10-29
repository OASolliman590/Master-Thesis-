"""Invented records only; public stage contract regressions."""
from pathlib import Path
import copy
import importlib
import json

import pytest

from tools.a_dav.core import SchemaStore, finish

STORE = SchemaStore()


def packet():
    return {'classification': 'SYNTHETIC_ONLY', 'branch_id': 'A_BASELINE_BIO',
            'records': {}, 'config': {}, 'schema_hashes': STORE.hashes, 'dependencies': {}}


@pytest.mark.parametrize('module,name', [('matrices','build_baseline'), ('matrices','build_longitudinal'),
                                         ('release','validate_split'), ('reporting','build_public_report')])
def test_missing_dependency_is_blocked(module, name):
    api = getattr(importlib.import_module('tools.a_dav.' + module), name)
    result = api(packet(),schemas=STORE)
    assert result['status'] == 'BLOCKED_UNKNOWN'
    assert result['reasons'] == ['DEPENDENCY_MISSING']
    assert result['source_admission'] is False


def test_freeze_missing_dependency_is_blocked(tmp_path):
    from tools.a_dav.release import freeze_bundle
    result = freeze_bundle(packet(), tmp_path / 'bundle',schemas=STORE)
    assert result['status'] == 'BLOCKED_UNKNOWN'
    assert not (tmp_path / 'bundle').exists()


def material_packet():
    p = packet()
    loc = [{'kind': 'SYNTHETIC', 'value': 'invented'}]
    p['records'] = {
        'patient_registry': [{'patient_uid':'P1', 'study_id':'S1', 'source_patient_id':'001',
            'patient_identity_confidence':'VERIFIED', 'treatment_naive_status':'VERIFIED_YES',
            'inclusion_state':'CANDIDATE', 'source_locators':loc, 'cancer':'INVENTED'}],
        'source_record':[{'source_object_id':'SRC1','study_id':'S1','publication_family_id':'FAM1','repository':'INVENTED','object_type':'synthetic_matrix','exact_file_name':'invented.tsv','retrieval_status':'RETRIEVED','validation_status':'PASS','sha256':'a'*64,'hash_scope':'FULL_OBJECT','source_locators':loc}],
        'specimen_registry': [], 'assay_registry': [], 'treatment_episode': [
            {'schema_version':'1.1.0','data_classification':'SYNTHETIC_ONLY','treatment_episode_id':'E1',
             'patient_uid':'P1','study_id':'S1','regimen_id':'R1','index_event':'invented',
             'start_day':0,'stop_day':100,'timing_precision':'EXACT','prior_ici':'NO',
             'episode_status':'VERIFIED','source_locators':['invented']}], 'episode_binding': [],
        'endpoint': [{'row_type':'ENDPOINT','schema_version':'1.1.0','data_classification':'SYNTHETIC_ONLY',
            'patient_uid':'P1','treatment_episode_id':'E1','outcome_id':'O1','endpoint_id':'ORR1',
            'endpoint_class':'ORR','raw_value':'PR','canonical_category':'PR','assessment_system':'invented',
            'assessment_day':40,'binary_value':1,'duration_threshold':None,'event_time':None,
            'event_indicator':None,'censoring':None,'evaluability':'EVALUABLE','mapping_version':'v1',
            'source_locator':'invented','build_receipt_id':'synthetic-endpoint'}]}
    for sid, aid, day, category in [('B1','A1',-2,'PRE_INDEX_BASELINE'), ('B2','A2',-1,'PRE_INDEX_BASELINE'),
                                   ('F1','A3',10,'EARLY_ON_TREATMENT'), ('F2','A4',20,'EARLY_ON_TREATMENT')]:
        p['records']['specimen_registry'].append({'specimen_uid':sid,'patient_uid':'P1',
            'raw_sample_aliases':[sid], 'canonical_timing_category':category,'tissue_type':'invented',
            'biological_compartment':'TUMOUR','baseline_candidate_status':'YES' if day < 0 else 'NO',
            'longitudinal_pair_status':'PAIRABLE','source_locators':loc,'days_from_index_start':day,
            'lesion_site':'L1', 'timing_raw_text':'invented'})
        p['records']['assay_registry'].append({'assay_uid':aid,'specimen_uid':sid,'source_sample_id':aid,
            'source_object_id':'SRC1','modality':'RNA','platform':'invented','measurement_unit':'COUNTS',
            'matrix_header':aid,'qc_status':'PASS','branch_suitability':['BASELINE_DE','LONGITUDINAL'],
            'feature_annotation':'invented-v1','source_locators':loc})
        p['records']['episode_binding'].append({'schema_version':'1.1.0','data_classification':'SYNTHETIC_ONLY',
            'binding_id':'bind'+sid,'patient_uid':'P1','treatment_episode_id':'E1','subject_type':'SPECIMEN',
            'subject_id':sid,'role':'PRE_INDEX_BASELINE' if day < 0 else 'ON_TREATMENT',
            'binding_status':'VERIFIED','source_locators':['invented'],'reviewer':'invented','reviewed_utc':'invented'})
    p['records']['cohort_admission_receipt']=[{'admission_receipt_id':'synthetic-admission-draft',
        'study_id':'S1','publication_family_id':'FAM1','branch_id':p['branch_id'],'admission_version':'v1',
        'source_object_ids':['SRC1'],'source_object_hashes':['a'*64],
        'gate_results':[{'gate':'V'+str(n),'status':'BLOCKED_UNKNOWN','reason':'ACTUAL_REVIEW_NOT_RUN'} for n in range(8)],
        'admission_status':'BLOCKED_UNKNOWN','approved_branches':[],'blocked_branches':[p['branch_id']],
        'validator':'SOFTWARE_ONLY','reviewer':'NOT_AUTHENTICATED','code_version':'dav-software-v1',
        'config_hash':'a'*64,'created_utc':'NOT_RUN','unresolved_limitations':['ACTUAL_REVIEW_NOT_RUN']}]
    rank = {'specimen_rank': {'B1':0,'B2':1,'F1':0,'F2':1},
            'assay_rank': {'A1':0,'A2':1,'A3':0,'A4':1}, 'selection_basis':'PRESPECIFIED_METADATA',
            'assay_suitability':'BASELINE_DE', 'coverage_suitability':'de_suitability',
            'endpoint_policy':{'required':True,'endpoint_class':'ORR','discrepancy_policy':'SEALED_PREFERRED_OUTCOME'}, 'split_role':'DEVELOPMENT','prior_exposure_status':'UNKNOWN',
            'build_utc':'2026-10-23T00:00:00Z'}
    p['config'] = {'baseline': rank, 'longitudinal': {**rank, 'assay_suitability':'LONGITUDINAL', 'windows':[
        {'window_id':'W1','contrast_id':'C1','category':'EARLY_ON_TREATMENT','lower_day':1,'upper_day':30},
        {'window_id':'W2','contrast_id':'C2','category':'POST_TREATMENT','lower_day':50,'upper_day':80}]}}
    p['records']['coverage']=[{'row_type':'COVERAGE','schema_version':'1.1.0','study_id':'S1','assay_uid':a['assay_uid'],
        'branch_id':p['branch_id'],'required_genes':['G1'],'present_genes':['G1'],'missing_genes':[],
        'ambiguous_genes':[],'annotation_version':'invented-v1','expression_unit':'COUNTS',
        'measurement_suitability':'PASS','scoring_suitability':'PASS','de_suitability':'PASS',
        'final_test_suitability':'PASS','source_object_id':a['source_object_id']} for a in p['records']['assay_registry']]
    p['records']['split'] = [{'row_type':'SPLIT','schema_version':'1.1.0','data_classification':'SYNTHETIC_ONLY',
        'patient_uid':'P1','study_id':'S1','independence_family_id':'FAM1','permanent_role':'DEVELOPMENT',
        'prior_exposure_state':'UNKNOWN','exposure_decision_id':None,'split_version':'v1',
        'reason':'PRESPECIFIED_METADATA','nested_assignments':[]}]
    return seal(p)


def seal(p, stages=('registries','endpoints','timing','assays','overlap','exposure','admission','split')):
    p['dependencies']={}
    if 'split' in p['config'] and 'assignments' in p['config']['split']:
        p['records']['split'] = copy.deepcopy(p['config']['split']['assignments'])
    order = ('registries','endpoints','timing','assays','overlap','exposure','admission','split',
             'baseline','longitudinal','prat_review','public_report')
    for stage in order:
        if stage not in stages: continue
        audit = []
        if stage == 'admission':
            audit = [{'kind':'admission_eligibility','study_id':'S1','branch_id':p['branch_id'],
                      'eligibility':'READY','criteria':{},'actual_source_review':'NOT_RUN'}]
        if stage == 'timing':
            audit=[{'check':'TIMING_ASSERTION','specimen_uid':sp['specimen_uid'],'precision':'EXACT',
                'relative_day':sp['days_from_index_start'],'canonical_category':sp['canonical_timing_category'],
                'treatment_episode_id':'E1','binding_id':'bind'+sp['specimen_uid'],
                'role':'PRE_INDEX_BASELINE' if sp['days_from_index_start']<0 else 'ON_TREATMENT',
                'interval':[None,None]} for sp in p['records'].get('specimen_registry',[])]
        if stage == 'split':
            audit=[{'kind':'PATIENT_LEDGER','patient_uid':row['patient_uid'],
                    'permanent_role':row['permanent_role'],'exposure_state':row['prior_exposure_state'],
                    'actual_untouched_certified':False} for row in p['records'].get('split', [])]
        p['dependencies'][stage] = finish(stage,p,p['records'],schemas=STORE,audit=audit)
    return p


def refresh_descendants(p, ancestor):
    """Refresh invented fixture receipts after intentionally replacing one audit."""
    from tools.a_dav.core import UPSTREAMS
    changed = {ancestor}
    for stage in ('registries','endpoints','timing','assays','overlap','exposure','admission','split',
                  'baseline','longitudinal','public_report'):
        if stage == ancestor or stage not in p['dependencies']: continue
        if changed.intersection(UPSTREAMS[stage]):
            old = p['dependencies'][stage]
            p['dependencies'][stage] = finish(stage,p,p['records'],schemas=STORE,audit=old['audit'])
            changed.add(stage)


def test_baseline_selects_rank_and_preserves_sources_and_outcome_blindness():
    from tools.a_dav.matrices import build_baseline
    p=material_packet(); original=copy.deepcopy(p['records'])
    r=build_baseline(p,schemas=STORE)
    assert r['status']=='READY'
    assert [(v['patient_uid'],v['specimen_uid'],v['assay_uid']) for v in r['records']['baseline']]==[('P1','B1','A1')]
    assert p['records']==original
    for table in original: assert r['records'][table]==sorted(original[table],key=lambda v: __import__('json').dumps(v,sort_keys=True,separators=(',',':')))
    p['records']['endpoint'][0].update(raw_value='PD',canonical_category='PD',binary_value=0)
    p['records']['specimen_registry'].reverse(); p['records']['assay_registry'].reverse()
    r2=build_baseline(seal(p),schemas=STORE)
    assert r2['records']['baseline'][0]['specimen_uid']=='B1'
    assert len([a for a in r['audit'] if a.get('kind')=='CANDIDATE'])==4


def test_baseline_tie_blocks_without_identifier_tiebreak():
    from tools.a_dav.matrices import build_baseline
    p=material_packet();p['config']['baseline']['specimen_rank']['B2']=0
    p['config']['baseline']['assay_rank']['A2']=0
    r=build_baseline(seal(p),schemas=STORE)
    assert r['status']=='BLOCKED_UNKNOWN'; assert 'SELECTION_TIE' in r['reasons']


def test_longitudinal_keeps_repeats_and_missing_denominator():
    from tools.a_dav.matrices import build_longitudinal
    p=material_packet();r=build_longitudinal(p,schemas=STORE)
    assert r['status']=='READY'
    assert len(r['records']['timepoint'])==4
    pairs={v['window_id']:v for v in r['records']['pair']}
    assert pairs['W1']['followup_specimen_uid']=='F1'
    assert pairs['W1']['inclusion_status']=='INCLUDED'
    assert 'W2' not in pairs
    assert any(a.get('kind')=='PAIR_DENOMINATOR' and a.get('window_id')=='W2' and a.get('reason')=='NO_FOLLOWUP_IN_WINDOW' for a in r['audit'])
    assert len([a for a in r['audit'] if a.get('window_id')=='W1' and a.get('kind')=='WINDOW_CANDIDATE'])==2
    for table in ('timepoint','pair'):
        for row in r['records'][table]: STORE.validate(table,row)


@pytest.mark.parametrize('field,value,reason', [('lesion_site','L2','LESION_MISMATCH'),
    ('canonical_timing_category','AFTER_REGIMEN_CHANGE','AFTER_REGIMEN_CHANGE')])
def test_longitudinal_does_not_silently_qualify_mismatches(field,value,reason):
    from tools.a_dav.matrices import build_longitudinal
    p=material_packet();p['records']['specimen_registry'][2][field]=value
    r=build_longitudinal(seal(p),schemas=STORE);assert r['status'] in ('READY','FAIL','BLOCKED_UNKNOWN')
    assert reason in str(r['audit']) or reason in r['reasons']


def split_packet():
    p=material_packet()
    row={'row_type':'SPLIT','schema_version':'1.1.0','data_classification':'SYNTHETIC_ONLY',
         'patient_uid':'P1','study_id':'S1','independence_family_id':'FAM1','permanent_role':'DEVELOPMENT',
         'prior_exposure_state':'METADATA_ONLY','exposure_decision_id':None,'split_version':'v1',
         'reason':'PRESPECIFIED_METADATA','nested_assignments':[{'evaluation_id':'EV1','fold_id':'1','role':'TRAIN'}]}
    p['config']['split']={'assignments':[row],'version':'v1','required_source_ids':['SRC1'],
                          'selection_basis':'PRESPECIFIED_METADATA','performance_observed':False,
                          'analysis_lineage_id':'L1'}
    return seal(p)


def test_split_emits_valid_rows_and_rejects_patient_cross_roles():
    from tools.a_dav.release import validate_split
    p=split_packet();r=validate_split(p,schemas=STORE)
    assert r['status']=='READY'
    assert r['records']['split'][0]['permanent_role']=='DEVELOPMENT'
    STORE.validate('split',r['records']['split'][0])
    second=copy.deepcopy(p['config']['split']['assignments'][0]);second.update(permanent_role='FINAL_TEST',
        prior_exposure_state='ADJUDICATED_UNTOUCHED',exposure_decision_id='X1',nested_assignments=[])
    p['config']['split']['assignments'].append(second)
    assert validate_split(seal(p),schemas=STORE)['status']=='FAIL'


def test_split_requires_complete_sources_and_prespecified_policy():
    from tools.a_dav.release import validate_split
    p=split_packet();p['config']['split']['required_source_ids'].append('MISSING')
    assert validate_split(seal(p),schemas=STORE)['status']=='BLOCKED_UNKNOWN'
    p=split_packet();p['config']['split']['performance_observed']=True
    assert validate_split(seal(p),schemas=STORE)['reasons']==['FINAL_TEST_SELECTED_AFTER_PERFORMANCE']


def test_split_unknown_final_exposure_cannot_be_promoted():
    from tools.a_dav.release import validate_split
    p=split_packet();p['config']['split']['assignments'][0].update(permanent_role='FINAL_TEST',
        prior_exposure_state='ADJUDICATED_UNTOUCHED', exposure_decision_id='CLAIM',nested_assignments=[])
    assert validate_split(seal(p),schemas=STORE)['status']=='BLOCKED_UNKNOWN'


def report_packet():
    p=split_packet()
    p['config']['public_report']={'minimum_cell_count':3,'include_counts':True}
    p['config']['freeze']={'commands':['python -B -m synthetic_dav'], 'environment':{'python':'invented'},
                           'required_source_ids':['SRC1'],'source_universe_version':'synthetic-v1'}
    p=seal(p)
    for stage in ('baseline','longitudinal'):
        p['dependencies'][stage]=finish(stage,p,p['records'],schemas=STORE)
    return p


def test_reporting_suppresses_small_cells_and_exports_no_source_rows():
    from tools.a_dav.reporting import build_public_report
    p=report_packet();r=build_public_report(p,schemas=STORE)
    assert r['status']=='READY'
    public=next(v['public_report'] for v in r['audit'] if 'public_report' in v)
    assert public['classification']=='SYNTHETIC_ONLY'
    assert '"001"' not in json.dumps(public); assert '"P1"' not in json.dumps(public); assert '"invented"' not in json.dumps(public)
    assert public['patient_count'] is None


@pytest.mark.parametrize('payload', [{'patient_uid':'P1'},{'sidecars':['/private/x']},
    {'status':'https://host?token=SECRET'}, {'counts':{'P1':1}}, {'notes':'anything'}])
def test_reporting_rejects_non_allowlisted_export_payload(payload):
    from tools.a_dav.reporting import build_public_report
    p=report_packet();p['config']['public_report']['payload']=payload
    r=build_public_report(seal(p,tuple(p['dependencies'])),schemas=STORE)
    assert r['status']=='FAIL';assert r['reasons']==['PUBLIC_PAYLOAD_REJECTED']


def test_freeze_fresh_resume_tamper_and_collision(tmp_path):
    from tools.a_dav.reporting import build_public_report
    from tools.a_dav.release import freeze_bundle, verify_bundle
    p=report_packet();p['dependencies']['public_report']=build_public_report(p,schemas=STORE)
    target=tmp_path/'bundle';r=freeze_bundle(p,target,schemas=STORE)
    assert r['status']=='READY';assert target.is_dir()
    assert freeze_bundle(p,target,schemas=STORE)==r
    verified=verify_bundle(target)
    assert verified['status']=='READY'
    assert sorted(v.name for v in target.iterdir())==['manifest.json','packet.json','release_draft.json','result.json']
    (target/'packet.json').write_text('{}')
    with pytest.raises(ValueError): verify_bundle(target)
    assert freeze_bundle(p,target,schemas=STORE)['status']=='FAIL'


def test_freeze_refuses_symlink_and_traversal_destination(tmp_path):
    from tools.a_dav.release import freeze_bundle
    p=packet()
    link=tmp_path/'link';link.symlink_to(tmp_path,target_is_directory=True)
    assert freeze_bundle(p,link/'escape',schemas=STORE)['status']=='FAIL'
    assert freeze_bundle(p,tmp_path/'x'/'..'/'escape',schemas=STORE)['status']=='FAIL'
    assert not (tmp_path/'escape').exists()


def test_unknown_timing_never_becomes_an_exact_pair_from_numeric_source_day():
    from tools.a_dav.matrices import build_longitudinal
    p=material_packet()
    audit=[{'check':'TIMING_ASSERTION','specimen_uid':sp['specimen_uid'],
        'precision':'UNKNOWN' if sp['specimen_uid']=='F1' else 'EXACT',
        'relative_day':None if sp['specimen_uid']=='F1' else sp['days_from_index_start'],
        'canonical_category':sp['canonical_timing_category'],'treatment_episode_id':'E1',
        'binding_id':'bind'+sp['specimen_uid'],'role':'PRE_INDEX_BASELINE' if sp['days_from_index_start']<0 else 'ON_TREATMENT','interval':[None,None]} for sp in p['records']['specimen_registry']]
    p['dependencies']['timing']=finish('timing',p,p['records'],audit=audit,schemas=STORE)
    refresh_descendants(p, 'timing')
    r=build_longitudinal(p,schemas=STORE)
    assert not any(v['inclusion_status']=='INCLUDED' and v['followup_specimen_uid']=='F1' for v in r['records']['pair'])
    assert 'TIMING_UNKNOWN' in str(r['audit'])


def test_matrix_receipts_are_invariant_under_source_row_permutations():
    from tools.a_dav.matrices import build_baseline,build_longitudinal
    p=material_packet();other=copy.deepcopy(p)
    for rows in other['records'].values():rows.reverse()
    other=seal(other)
    for api in (build_baseline,build_longitudinal):
        assert api(p,schemas=STORE)==api(other,schemas=STORE)


def test_stale_dependency_prevents_materialization_and_freeze(tmp_path):
    from tools.a_dav.matrices import build_baseline
    from tools.a_dav.reporting import build_public_report
    from tools.a_dav.release import freeze_bundle
    p=material_packet();p['records']['patient_registry'][0]['source_patient_id']='changed'
    assert build_baseline(p,schemas=STORE)['status']=='FAIL'
    p=report_packet();p['dependencies']['public_report']=build_public_report(p,schemas=STORE)
    p['config']['public_report']['minimum_cell_count']=4
    assert freeze_bundle(p,tmp_path/'stale',schemas=STORE)['status']=='FAIL'
    assert not (tmp_path/'stale').exists()


def test_extra_bundle_sidecar_and_changed_input_are_rejected(tmp_path):
    from tools.a_dav.reporting import build_public_report
    from tools.a_dav.release import freeze_bundle,verify_bundle
    p=report_packet();p['dependencies']['public_report']=build_public_report(p,schemas=STORE)
    target=tmp_path/'bundle';assert freeze_bundle(p,target,schemas=STORE)['status']=='READY'
    (target/'extra.json').write_text('{}')
    with pytest.raises(ValueError):verify_bundle(target)
    (target/'extra.json').unlink()
    changed=copy.deepcopy(p);changed['config']['freeze']['environment']['python']='changed'
    stages=tuple(changed['dependencies']);changed=seal(changed,stages)
    changed['dependencies']['public_report']=build_public_report(changed,schemas=STORE)
    assert freeze_bundle(changed,target,schemas=STORE)['reasons']==['BUNDLE_COLLISION']


def test_split_blocks_transitive_possible_overlap_across_roles():
    from tools.a_dav.release import validate_split
    p=split_packet();other=copy.deepcopy(p['records']['patient_registry'][0]);other.update(patient_uid='P2',study_id='S2',source_patient_id='002')
    p['records']['patient_registry'].append(other)
    row=copy.deepcopy(p['config']['split']['assignments'][0]);row.update(patient_uid='P2',study_id='S2',independence_family_id='FAM2',permanent_role='A1_ONLY',nested_assignments=[])
    p['config']['split']['assignments'].append(row);p=seal(p)
    audit=[{'kind':'overlap_component','nodes':[{'node_type':'PATIENT','node_id':'P1'},
        {'node_type':'SOURCE_OBJECT','node_id':'bridge'},{'node_type':'PATIENT','node_id':'P2'}],
        'protection':'POTENTIAL_OR_UNKNOWN','independence_certified':False}]
    p['dependencies']['overlap']=finish('overlap',p,p['records'],audit=audit,schemas=STORE)
    refresh_descendants(p, 'overlap')
    assert validate_split(p,schemas=STORE)['reasons']==['SPLIT_LEAKAGE']


def final_packet():
    p=split_packet();p['config']['split']['assignments'][0].update(permanent_role='FINAL_TEST',
        prior_exposure_state='ADJUDICATED_UNTOUCHED',exposure_decision_id='SIM-REVIEW',nested_assignments=[])
    p['config']['split']['final_test_review']={'decision_id':'SIM-REVIEW','analysis_lineage_id':'L1',
        'review_complete':True,'metadata_only_permitted':True,'covered_patient_uids':['P1'],'source_locators':['invented']}
    p=seal(p)
    p['dependencies']['exposure']=finish('exposure',p,p['records'],schemas=STORE,audit=[{
        'kind':'exposure_decision','subject_type':'SOURCE_OBJECT','subject_id':'SRC1',
        'analysis_lineage_id':'L1','state':'METADATA_ONLY','untouched_certified':False}])
    refresh_descendants(p, 'exposure')
    return p


def test_final_split_simulation_keeps_actual_certification_false():
    from tools.a_dav.release import validate_split
    r=validate_split(final_packet(),schemas=STORE)
    assert r['status']=='READY'
    assert all(a['actual_untouched_certified'] is False for a in r['audit'])
    assert r['source_admission'] is False


def test_uncovered_prior_exposure_cannot_hide_behind_metadata_decision():
    from tools.a_dav.release import validate_split
    p=final_packet();p['records']['prior_exposure_record']=[{'schema_version':'1.1.0','exposure_id':'X0',
        'subject_type':'SOURCE_OBJECT','subject_id':'SRC1','analysis_lineage_id':'OLDER-LINEAGE',
        'fields_accessed':['expression','outcome'],'use':'FEATURE_SELECTION','occurred_utc':None,
        'date_precision':'UNKNOWN','actor_role':'invented','independence_implication':'BLOCKS_UNTOUCHED_FOR_LINEAGE',
        'source_locators':['invented']}]
    old_audit=p['dependencies']['exposure']['audit'];p=seal(p)
    p['dependencies']['exposure']=finish('exposure',p,p['records'],audit=old_audit,schemas=STORE)
    refresh_descendants(p, 'exposure')
    r=validate_split(p,schemas=STORE)
    assert r['status']=='FAIL';assert r['reasons']==['PRIOR_MODEL_EXPOSURE']


def test_tied_candidates_remain_in_blocked_matrix_audit():
    from tools.a_dav.matrices import build_baseline
    p=material_packet();p['config']['baseline']['specimen_rank']['B2']=0
    p['config']['baseline']['assay_rank']['A2']=0
    r=build_baseline(seal(p),schemas=STORE)
    assert r['status']=='BLOCKED_UNKNOWN'
    assert {a['specimen_uid'] for a in r['audit'] if a.get('kind')=='CANDIDATE'}=={'B1','B2','F1','F2'}


def test_unadmitted_assay_source_is_excluded_with_audit():
    from tools.a_dav.matrices import build_baseline
    p=material_packet();other=copy.deepcopy(p['records']['source_record'][0]);other['source_object_id']='SRC2'
    p['records']['source_record'].append(other);p['records']['assay_registry'][0]['source_object_id']='SRC2'
    r=build_baseline(seal(p),schemas=STORE)
    assert r['records']['baseline'][0]['specimen_uid']=='B2'
    assert any(a.get('assay_uid')=='A1' and a.get('reason')=='SOURCE_NOT_ELIGIBLE' for a in r['audit'])


def test_canonically_excluded_patient_cannot_enter_matrix():
    from tools.a_dav.matrices import build_baseline,build_longitudinal
    p=material_packet();p['records']['patient_registry'][0].update(inclusion_state='EXCLUDED',exclusion_reason='invented')
    p=seal(p)
    baseline=build_baseline(p,schemas=STORE)
    assert baseline['records']['baseline'][0]['inclusion_status']=='EXCLUDED'
    longitudinal=build_longitudinal(p,schemas=STORE)
    assert all(row['inclusion_status']!='INCLUDED' for row in longitudinal['records']['pair'])


def test_freeze_requires_upstream_code_closure(tmp_path):
    from tools.a_dav.reporting import build_public_report
    from tools.a_dav.release import freeze_bundle
    p=report_packet();p['dependencies']['public_report']=build_public_report(p,schemas=STORE)
    del p['dependencies']['assays']
    r=freeze_bundle(p,tmp_path/'incomplete',schemas=STORE)
    assert r['status']=='BLOCKED_UNKNOWN';assert r['reasons']==['DEPENDENCY_MISSING']
    assert not (tmp_path/'incomplete').exists()


def test_computed_coverage_fail_overrides_declared_branch_suitability():
    from tools.a_dav.matrices import build_baseline
    p=material_packet()
    for coverage in p['records']['coverage']:coverage['de_suitability']='FAIL'
    r=build_baseline(seal(p),schemas=STORE)
    assert all(v['inclusion_status']!='INCLUDED' for v in r['records']['baseline'])
    assert any(a.get('reason')=='ASSAY_UNSUITABLE' for a in r['audit'])
    p['config']['baseline']['coverage_suitability']='scoring_suitability'
    p['config']['baseline']['assay_suitability']='BASELINE_SCORING'
    for assay in p['records']['assay_registry']:assay['branch_suitability'].append('BASELINE_SCORING')
    r=build_baseline(seal(p),schemas=STORE)
    assert r['records']['baseline'][0]['inclusion_status']=='INCLUDED'


def test_source_defined_binary_uses_own_meaning_without_orr():
    from tools.a_dav.matrices import build_baseline
    p=material_packet();p['records']['endpoint'][0].update(endpoint_class='OTHER',canonical_category='SOURCE_BINARY')
    p['config']['baseline']['endpoint_policy']['endpoint_class']='OTHER'
    r=build_baseline(seal(p),schemas=STORE)
    assert r['status']=='READY'
    row=r['records']['baseline'][0]
    assert row['inclusion_status']=='INCLUDED';assert row['orr'] is None;assert row['dcr'] is None
    assert row['canonical_category']=='SOURCE_BINARY'


def test_longitudinal_explicit_endpoint_optional_preserves_unlabelled_pairs():
    from tools.a_dav.matrices import build_longitudinal
    p=material_packet();p['records']['endpoint']=[]
    p['config']['longitudinal']['endpoint_policy'].update(required=False,endpoint_class=None)
    r=build_longitudinal(seal(p),schemas=STORE)
    assert r['status']=='READY'
    assert r['records']['pair'][0]['inclusion_status']=='INCLUDED'
    assert r['records']['pair'][0]['response_group']=='NOT_APPLICABLE'


def test_adjudicated_endpoint_selection_uses_sealed_preferred_outcome():
    from tools.a_dav.matrices import build_baseline
    p=material_packet();second=copy.deepcopy(p['records']['endpoint'][0])
    second.update(outcome_id='O2',endpoint_id='ORR2',raw_value='PD',canonical_category='PD',binary_value=0)
    p['records']['endpoint'].append(second);p=seal(p)
    p['dependencies']['endpoints']=finish('endpoints',p,p['records'],schemas=STORE,audit=[{
        'check':'DISCREPANCY_RETAINED','patient_uid':'P1','treatment_episode_id':'E1',
        'preferred_outcome_id':'O1','all_outcome_ids':['O1','O2']}])
    refresh_descendants(p, 'endpoints')
    r=build_baseline(p,schemas=STORE)
    assert r['status']=='READY';assert r['records']['baseline'][0]['orr']==1
    assert len(r['records']['endpoint'])==2


def test_missing_pre_or_followup_only_emits_denominator_audit():
    from tools.a_dav.matrices import build_longitudinal
    p=material_packet();p['config']['longitudinal']['windows'][0].update(lower_day=30,upper_day=40)
    r=build_longitudinal(seal(p),schemas=STORE)
    assert r['records']['pair']==[]
    denominators=[a for a in r['audit'] if a.get('kind')=='PAIR_DENOMINATOR']
    assert [(a['window_id'],a['reason']) for a in denominators]==[('W1','NO_FOLLOWUP_IN_WINDOW'),('W2','NO_FOLLOWUP_IN_WINDOW')]
    assert len(r['records']['timepoint'])==4


def test_public_report_has_allowlisted_gate_and_limitation_tables():
    from tools.a_dav.reporting import build_public_report
    r=build_public_report(report_packet(),schemas=STORE)
    public=next(a['public_report'] for a in r['audit'] if 'public_report' in a)
    assert public['gate_table']==[
        {'gate':'SOFTWARE_CHECKS','status':'READY'},
        {'gate':'SOURCE_REVIEW','status':'NOT_RUN'},{'gate':'INDEPENDENT_REVIEW','status':'NOT_RUN'},
        {'gate':'ENVIRONMENT_VALIDATION','status':'NOT_RUN'},{'gate':'STATISTICAL_RELEASE','status':'NOT_RUN'}]
    assert public['limitation_table']==[{'code':v,'status':'NOT_RUN'} for v in
        ['ACTUAL_SOURCE_REVIEW','AUTHENTICATED_INDEPENDENT_REVIEW','TARGET_ENVIRONMENT_VALIDATION','SCIENTIFIC_STATISTICAL_ACCEPTANCE']]
    assert public['count_table']==[{'metric':'PATIENTS','count':None,'disclosure':'SUPPRESSED'}]


def test_multiple_evidenced_specimen_contexts_preserve_episode_specific_timepoints():
    from tools.a_dav.matrices import build_longitudinal
    p=material_packet();episode=copy.deepcopy(p['records']['treatment_episode'][0]);episode.update(treatment_episode_id='E2',regimen_id='R2')
    p['records']['treatment_episode'].append(episode)
    binding=copy.deepcopy(p['records']['episode_binding'][2]);binding.update(binding_id='reuseF1',treatment_episode_id='E2',role='PRE_INDEX_BASELINE')
    p['records']['episode_binding'].append(binding)
    p['config']['longitudinal']['index_episode_by_patient']={'P1':'E1'};p=seal(p)
    audits=copy.deepcopy(p['dependencies']['timing']['audit'])
    audits.append({'check':'TIMING_ASSERTION','specimen_uid':'F1','treatment_episode_id':'E2',
        'binding_id':'reuseF1','role':'PRE_INDEX_BASELINE','canonical_category':'PRE_INDEX_BASELINE',
        'precision':'EXACT','relative_day':-3,'interval':[None,None]})
    p['dependencies']['timing']=finish('timing',p,p['records'],audit=audits,schemas=STORE)
    refresh_descendants(p, 'timing')
    r=build_longitudinal(p,schemas=STORE)
    assert r['status']=='READY'
    contexts={(v['treatment_episode_id'],v['canonical_timing'],v['relative_day']) for v in r['records']['timepoint'] if v['specimen_uid']=='F1'}
    assert contexts=={('E1','EARLY_ON_TREATMENT',10),('E2','PRE_INDEX_BASELINE',-3)}
    assert r['records']['pair'][0]['followup_specimen_uid']=='F1'


def test_prat_bound_general_report_is_count_free_despite_count_request():
    from tools.a_dav.reporting import build_public_report
    p=report_packet();p['dependencies']['prat_review']=finish('prat_review',p,p['records'],schemas=STORE)
    r=build_public_report(p,schemas=STORE)
    assert r['status']=='READY'
    public=next(a['public_report'] for a in r['audit'] if 'public_report' in a)
    assert 'patient_count' not in public;assert 'count_table' not in public
    assert {'code':'PRAT_COUNT_FREE_EXPORT','status':'ENFORCED'} in public['limitation_table']
    prat=next(a['prat_summary'] for a in r['audit'] if 'prat_summary' in a)
    assert 'record_count' not in prat
    assert '"P1"' not in json.dumps(public);assert '"001"' not in json.dumps(public)


def test_prat_bound_public_report_rejects_stale_prat_config():
    from tools.a_dav.reporting import build_public_report
    p=report_packet();stale=copy.deepcopy(p);stale['config']['public_report']['include_counts']=False
    p['dependencies']['prat_review']=finish('prat_review',stale,stale['records'],schemas=STORE)
    r=build_public_report(p,schemas=STORE)
    assert r['status']=='FAIL';assert r['reasons']==['DEPENDENCY_INVALID']


def test_direct_baseline_requires_applicable_frozen_patient_split():
    from tools.a_dav.matrices import build_baseline
    p = material_packet()
    del p['dependencies']['split']
    result = build_baseline(p, schemas=STORE)
    assert result['status'] == 'BLOCKED_UNKNOWN'
    assert result['reasons'] == ['DEPENDENCY_MISSING']
    assert 'baseline' not in result['records']


def test_unknown_branch_compartment_policy_does_not_default_to_tumour():
    from tools.a_dav.matrices import build_baseline
    p = material_packet()
    p['branch_id'] = 'A1_ON_R_NR'
    for row in p['records']['coverage']: row['branch_id'] = p['branch_id']
    for row in p['records']['cohort_admission_receipt']: row.update(branch_id=p['branch_id'], blocked_branches=[p['branch_id']])
    blocked = build_baseline(seal(p), schemas=STORE)
    assert blocked['status'] == 'BLOCKED_UNKNOWN'
    assert blocked['reasons'] == ['SPECIMEN_POLICY_UNKNOWN']
    p['config']['baseline']['baseline_compartments'] = ['TUMOUR']
    good = build_baseline(seal(p), schemas=STORE)
    assert good['status'] == 'READY'
    assert good['records']['baseline'][0]['specimen_uid'] == 'B1'


def test_declared_split_policy_generates_schema_valid_patient_rows():
    from tools.a_dav.release import validate_split
    p = split_packet()
    p['records']['study_registry'] = [{'study_id': 'S1', 'publication_family_id': 'FAM1'}]
    p['config']['split'].pop('assignments')
    p['config']['split']['policy'] = {'permanent_role': 'DEVELOPMENT', 'prior_exposure_state': 'METADATA_ONLY'}
    result = validate_split(seal(p), schemas=STORE)
    assert result['status'] == 'READY', result['reasons']
    rows = result['records']['split']
    assert len(rows) == 1
    assert rows[0]['patient_uid'] == 'P1'
    assert rows[0]['permanent_role'] == 'DEVELOPMENT'
    STORE.validate('split', rows[0])


@pytest.mark.parametrize(('role', 'state', 'expected'), [
    ('UNKNOWN', 'UNKNOWN', 'BLOCKED_UNKNOWN'),
    ('FINAL_TEST', 'METADATA_ONLY', 'FAIL'),
])
def test_declared_split_policy_rejects_unresolved_roles_and_final_exposure(role, state, expected):
    from tools.a_dav.release import validate_split
    p = split_packet()
    p['records']['study_registry'] = [{'study_id': 'S1', 'publication_family_id': 'FAM1'}]
    p['config']['split'].pop('assignments')
    p['config']['split']['policy'] = {'permanent_role': role, 'prior_exposure_state': state}
    assert validate_split(seal(p), schemas=STORE)['status'] == expected


def test_baseline_matrix_carries_split_role():
    from tools.a_dav.matrices import build_baseline
    result = build_baseline(material_packet(), schemas=STORE)
    assert result['status'] == 'READY'
    assert result['records']['baseline'][0]['split_role'] == 'DEVELOPMENT'


def test_baseline_build_records_runtime_timestamp_when_config_requests_it():
    from datetime import datetime
    from tools.a_dav.matrices import build_baseline
    p = material_packet()
    p['config']['baseline']['build_utc'] = 'AT_BUILD_TIME'
    result = build_baseline(seal(p), schemas=STORE)
    assert result['status'] == 'READY'
    stamp = result['records']['matrix_build_receipt'][-1]['build_utc']
    assert datetime.fromisoformat(stamp.replace('Z', '+00:00')).tzinfo is not None


def test_unknown_prior_ici_development_exception_cannot_be_reused_for_final_test():
    from tools.a_dav.release import validate_split
    p = split_packet()
    p['config']['timing'] = {'prior_ici_policy':'UNKNOWN_ALLOWED_DEVELOPMENT'}
    p['records']['patient_registry'][0]['prior_ici'] = 'UNKNOWN'
    p['config']['split']['assignments'][0].update(permanent_role='FINAL_TEST', prior_exposure_state='ADJUDICATED_UNTOUCHED', exposure_decision_id='CLAIM', nested_assignments=[])
    result = validate_split(seal(p), schemas=STORE)
    assert result['status'] == 'BLOCKED_UNKNOWN'
    assert result['reasons'] == ['PRIOR_ICI_UNKNOWN']


def test_baseline_preserves_unknown_prior_ici_covariate():
    from tools.a_dav.matrices import build_baseline
    p=material_packet(); p['records']['treatment_episode'][0]['prior_ici']='UNKNOWN'
    result=build_baseline(seal(p),schemas=STORE)
    assert result['status']=='READY'
    assert result['records']['baseline'][0]['prior_ici']=='UNKNOWN'
