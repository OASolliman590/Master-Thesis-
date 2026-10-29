"""Provisional artifacts never stand in for an admission receipt."""
from pathlib import Path

from tools.a_dav.core import SchemaStore
from tools.a_dav.release import validate_split, freeze_bundle
from tools.a_dav.matrices import build_baseline, build_longitudinal
from tools.a_dav.reporting import build_public_report
from tools.a_dav.provisional import provisional_patient_rows


def test_unsigned_preview_is_not_an_admission_receipt(tmp_path: Path) -> None:
    import pytest
    from tools.a_dav.core import DavError
    from tools.a_dav.expression_materialization import write_validated_products
    records = {
        'patient_registry': [{'patient_uid':'invented-patient', 'study_id':'invented-study', 'prior_ici':'UNKNOWN'}],
        'specimen_registry': [{'patient_uid':'invented-patient', 'specimen_uid':'invented-specimen',
                                'canonical_timing_category':'PRE_INDEX_BASELINE', 'biological_compartment':'TUMOUR',
                                'baseline_candidate_status':'YES'}],
        'assay_registry': [{'assay_uid':'invented-assay', 'specimen_uid':'invented-specimen',
                            'source_object_id':'invented-source', 'matrix_header':'invented-column'}],
        'clinical_outcome': [{'patient_uid':'invented-patient', 'raw_endpoint_label':'NE',
                              'canonical_category':'NE', 'evaluability':'NOT_EVALUABLE'}],
        'treatment_episode': [{'patient_uid':'invented-patient','prior_ici':'UNKNOWN'}],
    }
    result = provisional_patient_rows(records, 'invented-source', 'DEVELOPMENT')
    assert result['status'] == 'PROVISIONAL' and result['admission_status'] == 'PROVISIONAL_PENDING_SIGNATURE'
    assert result['rows'][0]['endpoint_evaluability'] == 'NOT_EVALUABLE'
    assert result['rows'][0]['inclusion_status'] == 'EXCLUDED'
    store = SchemaStore()
    packet = {'classification':'SYNTHETIC_ONLY','branch_id':'A_BASELINE_BIO','records':{},'config':{},
              'schema_hashes':store.hashes,'dependencies':{'admission':result}}
    for outcome in (validate_split(packet, schemas=store), build_baseline(packet, schemas=store),
                    build_longitudinal(packet, schemas=store), build_public_report(packet, schemas=store),
                    freeze_bundle(packet, tmp_path / 'bundle', schemas=store)):
        assert outcome['status'] != 'READY'
    assert not (tmp_path / 'bundle').exists()
    with pytest.raises(DavError):
        write_validated_products(packet, tmp_path, 'a' * 64, tmp_path / 'products',
                                 delimiter=',', compressed=False, allow_external_out=True)


def test_historical_flags_match_evidence_without_excluding_patients():
    from tools.a_dav.provisional import apply_historical_flags
    records = {'patient_registry': [{'patient_uid':'invented-1','source_patient_id':'person-1'},
                                    {'patient_uid':'invented-2','source_patient_id':'person-2'}],
               'specimen_registry': [{'patient_uid':'invented-1','raw_sample_aliases':['sample-1']},
                                     {'patient_uid':'invented-2','raw_sample_aliases':['sample-2']}]}
    rows = [{'patient_uid':'invented-1','flags':[],'inclusion_status':'INCLUDED'},
            {'patient_uid':'invented-2','flags':[],'inclusion_status':'INCLUDED'}]
    items = [{'category':'AUTHOR_EXCLUSION_POLICY_UNRESOLVED',
              'evidence_pointers':[{'record':'sample-2'}]}]
    apply_historical_flags(rows, records, items, outlier_source_id='person-1')
    assert rows[0]['flags'] == ['PAPER_PCA_OUTLIER']
    assert rows[1]['flags'] == ['AUTHOR_SCRIPT_EXCLUSION']
    assert all(row['inclusion_status'] == 'INCLUDED' for row in rows)


def test_preview_outputs_are_labeled_and_do_not_claim_admission(tmp_path: Path) -> None:
    import hashlib
    from tools.a_dav.provisional import write_provisional_products
    data = b'gene,sample-a,sample-b\nA1,1,3\nA2,2,4\n'
    sha = hashlib.sha256(data).hexdigest()
    (tmp_path / 'store' / 'objects').mkdir(parents=True)
    (tmp_path / 'store' / 'objects' / sha).write_bytes(data)
    rows = [{'patient_uid':'invented-1','expression_column':'sample-a','endpoint_evaluability':'EVALUABLE',
             'inclusion_status':'INCLUDED','flags':[]},
            {'patient_uid':'invented-2','expression_column':'sample-b','endpoint_evaluability':'NOT_EVALUABLE',
             'inclusion_status':'EXCLUDED','flags':[]}]
    result = write_provisional_products(rows, tmp_path / 'store', sha, tmp_path / 'out',
                                        delimiter=',', compressed=False, allow_external_out=True)
    assert result['status'] == 'PROVISIONAL'
    assert result['admission_status'] == 'PROVISIONAL_PENDING_SIGNATURE'
    assert result['counts']['gene_count'] == 2 and result['counts']['expression_patient_count'] == 1
    assert result['checks']['UNADMITTED_SOURCE']['count'] == 2
    assert result['checks']['UNRESOLVED_IDENTIFIER']['status'] == 'NOT_RUN'
    assert result['releasable'] is False


def test_provisional_refuses_a_signed_worksheet(tmp_path: Path) -> None:
    import pytest
    from tools.a_dav.provisional import run_provisional
    with pytest.raises(ValueError, match='PROVISIONAL_WORKSHEET_MUST_BE_UNSIGNED'):
        run_provisional({}, {}, tmp_path, tmp_path / 'out',
                        worksheet={'signature': {'reviewer_name':'invented'}}, allow_external_out=True)


def test_historical_script_flags_resolve_patient_by_declared_title_rule():
    from tools.a_dav.provisional import apply_historical_flags
    records = {'patient_registry': [{'patient_uid':'invented-1','source_patient_id':'person-1'},
                                    {'patient_uid':'invented-2','source_patient_id':'person-2'}],
               'specimen_registry': [{'patient_uid':'invented-1','raw_sample_aliases':['alias-1']},
                                     {'patient_uid':'invented-2','raw_sample_aliases':['alias-2']}]}
    rows = [{'patient_uid':'invented-1','flags':[]},{'patient_uid':'invented-2','flags':[]}]
    items = [{'category':'AUTHOR_EXCLUSION_POLICY_UNRESOLVED',
              'evidence_pointers':[{'record':'person-2_pre'}]}]
    apply_historical_flags(rows, records, items, outlier_source_id='person-1',
                           patient_regex=r'^(person-\d+)_pre$', patient_group=1)
    assert rows[1]['flags'] == ['AUTHOR_SCRIPT_EXCLUSION']


def test_provisional_matrix_record_contains_no_admission_receipt():
    from tools.a_dav.provisional import provisional_matrix_record
    result = {'counts': {'retained_patient_count': 2, 'expression_patient_count': 1,
                         'gene_count': 3, 'missing_cells': 0,
                         'evaluability': {'EVALUABLE': 1, 'NOT_EVALUABLE': 1, 'UNKNOWN': 0}},
              'checks': {'MATRIX_GRAIN_DUPLICATE': {'count': 0}},
              'hashes': {'source_sha256': 'a' * 64, 'output_sha256': 'b' * 64},
              'build_utc': '2026-10-27T00:00:00+00:00'}
    worksheet = {'context': {'config_hash': 'c' * 64}, 'context_hash': 'd' * 64}
    record = provisional_matrix_record(result, worksheet, branch='A_BASELINE_BIO',
                                       matrix_version='invented-v1', split_version='invented-split')
    assert record['status'] == 'PROVISIONAL'
    assert record['source_admission_receipt_ids'] == []
    assert record['validation_status'] == 'PROVISIONAL_PENDING_SIGNATURE'
    assert record['test_status'] == 'NOT_RUN'
    assert record['patient_count'] == 2 and record['feature_coverage']['gene_count'] == 3
    assert record['output_hash'] != record['input_hashes'][0]
    assert set(record['code_hashes']) == {'provisional.py', 'expression_materialization.py'}


def test_contract_audit_counts_unresolved_joins_and_preserves_pending_admission(tmp_path: Path) -> None:
    from tools.a_dav.provisional import audit_provisional_contract
    records = {'patient_registry':[{'patient_uid':'invented'}],
               'specimen_registry':[{'specimen_uid':'specimen','patient_uid':'invented',
                   'canonical_timing_category':'PRE_INDEX_BASELINE','biological_compartment':'TUMOUR',
                   'baseline_candidate_status':'YES'}],
               'assay_registry':[{'assay_uid':'assay','specimen_uid':'specimen',
                   'source_object_id':'source','matrix_header':'column'}],
               'source_record':[{'source_object_id':'source','sha256':'a' * 64}]}
    rows = [{'patient_uid':'invented','specimen_uid':'specimen','assay_uid':'wrong','expression_column':'column',
             'endpoint_evaluability':'EVALUABLE'}]
    report = {'counts':{'retained_patient_count':1,'gene_count':2},'hashes':{'source_sha256':'a' * 64},
              'stages':[{'stage':'assays','status':'READY'}]}
    v3 = {'source_sha256':{'fallback':'a' * 64}, 'checks':{'effective_primary':'role',
          'fallback':{'status':'PASS','counts':{'features':2,'missing_cells':0},
                      'checks':{'feature_identity':{'status':'PASS'}}}}}
    fmap = {'v3':{'source_object_roles':{'fallback':'role'}},
            'measurement_representations':{'role':{'feature_scope':'COMPLETE'}},
            'source_objects':{'role':{'sha256':'a' * 64}}}
    checks = audit_provisional_contract(rows, records, report, v3, fmap)
    assert checks['UNRESOLVED_IDENTIFIER']['count'] == 1
    assert checks['UNADMITTED_SOURCE'] == {'count':1,'status':'PENDING_SIGNATURE'}
    assert checks['SPLIT_NOT_FROZEN']['status'] == 'PENDING_SIGNATURE'


def test_provisional_is_rejected_even_when_other_dependencies_exist(tmp_path: Path) -> None:
    import pytest
    from tools.a_dav.core import DavError
    from tools.a_dav.expression_materialization import write_validated_products
    from test_group_c import STORE, material_packet, seal
    packet = material_packet()
    stages = ('registries','endpoints','timing','assays','overlap','exposure','admission','split',
              'baseline','longitudinal','prat_review','public_report')
    packet = seal(packet, stages=stages)
    packet['dependencies']['admission'] = {'status':'PROVISIONAL',
        'admission_status':'PROVISIONAL_PENDING_SIGNATURE','releasable':False}
    results = [validate_split(packet, schemas=STORE), build_baseline(packet, schemas=STORE),
               build_longitudinal(packet, schemas=STORE), build_public_report(packet, schemas=STORE),
               freeze_bundle(packet, tmp_path / 'bundle', schemas=STORE)]
    assert all(result['status'] != 'READY' for result in results)
    assert all('DEPENDENCY_INVALID' in result['reasons'] for result in results)
    with pytest.raises(DavError, match='DEPENDENCY_INVALID'):
        write_validated_products(packet, tmp_path, 'a' * 64, tmp_path / 'products',
                                 delimiter=',', compressed=False, allow_external_out=True)


def test_nonbaseline_only_patient_is_not_applicable_when_policy_declared():
    from tools.a_dav.provisional import provisional_patient_rows
    records = {'patient_registry': [{'patient_uid': 'invented-on', 'study_id': 'invented-study'}],
               'specimen_registry': [{'patient_uid': 'invented-on', 'specimen_uid': 'invented-specimen', 'baseline_candidate_status': 'NO', 'canonical_timing_category': 'UNKNOWN', 'timing_raw_text': 'on-treatment', 'biological_compartment': 'TUMOUR'}],
               'assay_registry': [], 'clinical_outcome': [], 'treatment_episode': []}
    result = provisional_patient_rows(records, 'invented-source', 'DEVELOPMENT', nonbaseline_visit_values=['on-treatment'])
    assert result['rows'] == []
    assert result['not_applicable_patients'] == 1


def test_geo_preview_does_not_require_an_undocumented_riaz_pca_flag():
    from tools.a_dav.provisional import apply_declared_historical_flags
    rows = [{'patient_uid': 'invented', 'flags': []}]
    packet = {'records': {'patient_registry': [], 'specimen_registry': []}, 'config': {'admission': {}}}
    apply_declared_historical_flags(rows, packet, {'geo_ingest': {}, 'sample_identity': {}}, {})
    assert rows[0]['flags'] == []


def test_provisional_audit_accepts_matching_missing_gene_exclusions():
    from tools.a_dav.provisional import audit_provisional_contract
    sha='a'*64
    records={'patient_registry':[{'patient_uid':'invented'}],
        'specimen_registry':[{'specimen_uid':'specimen','patient_uid':'invented','canonical_timing_category':'PRE_INDEX_BASELINE','biological_compartment':'TUMOUR','baseline_candidate_status':'YES'}],
        'assay_registry':[{'assay_uid':'assay','specimen_uid':'specimen','source_object_id':'source','matrix_header':'column'}],
        'source_record':[{'source_object_id':'source','sha256':sha}]}
    rows=[{'patient_uid':'invented','specimen_uid':'specimen','assay_uid':'assay','expression_column':'column','endpoint_evaluability':'EVALUABLE'}]
    report={'counts':{'retained_patient_count':1,'gene_count':56,'excluded_missing_gene_count':44},'hashes':{'source_sha256':sha},'stages':[{'stage':'assays','status':'READY'}]}
    v3={'source_sha256':{'primary':sha},'checks':{'effective_primary':'role','primary':{'status':'PASS','counts':{'features':100,'excluded_missing_features':44,'missing_cells':44},'checks':{'feature_identity':{'status':'PASS'}}}}}
    fmap={'v3':{'source_object_roles':{'primary':'role'}},'source_objects':{'role':{'sha256':sha}},'measurement_representations':{'role':{'feature_scope':'COMPLETE','missing_policy':'EXCLUDE_FEATURE_IF_ANY_MISSING'}}}
    checks=audit_provisional_contract(rows,records,report,v3,fmap)
    assert checks['FEATURE_COVERAGE_FAILED']['count']==0
    report['counts']['excluded_missing_gene_count']=43
    assert audit_provisional_contract(rows,records,report,v3,fmap)['FEATURE_COVERAGE_FAILED']['count']==1


def test_geo_preview_uses_only_declared_split_role():
    import pytest
    from tools.a_dav.provisional import preview_split_role
    field_map = {'geo_ingest': {}, 'decision_config': {'preview': {'split_policy': 'DEVELOPMENT'}}}
    assert preview_split_role({}, field_map) == 'DEVELOPMENT'
    with pytest.raises(ValueError, match='SPLIT_NOT_FROZEN'):
        preview_split_role({}, {'decision_config': {'preview': {}}})


def test_unsigned_geo_preview_uses_mapped_response_without_verifying_bindings():
    import copy
    template = {'patient_registry': [{'patient_uid':'invented','study_id':'study'}],
        'specimen_registry':[{'patient_uid':'invented','specimen_uid':'specimen','canonical_timing_category':'PRE_INDEX_BASELINE','biological_compartment':'TUMOUR','baseline_candidate_status':'YES'}],
        'assay_registry':[{'specimen_uid':'specimen','assay_uid':'assay','source_object_id':'source','matrix_header':'sample'}],
        'clinical_outcome':[], 'treatment_episode':[{'patient_uid':'invented','prior_ici':'UNKNOWN','episode_status':'BLOCKED_UNKNOWN'}], 'episode_binding':[]}
    for endpoint_class, category, expected in [('TUMOUR_RESPONSE','PR','EVALUABLE'), ('SOURCE_BINARY','SOURCE_NEGATIVE','EVALUABLE'), ('TUMOUR_RESPONSE','NE','NOT_EVALUABLE'), ('TUMOUR_RESPONSE','UNKNOWN','UNKNOWN')]:
        records = copy.deepcopy(template)
        records['clinical_outcome'] = [{'patient_uid':'invented','endpoint_class':endpoint_class,'raw_endpoint_label':'invented','canonical_category':category,'evaluability':'UNKNOWN'}]
        result = provisional_patient_rows(records, 'source', 'DEVELOPMENT')
        assert result['rows'][0]['endpoint_evaluability'] == expected
        assert result['rows'][0]['inclusion_status'] == ('INCLUDED' if expected == 'EVALUABLE' else 'EXCLUDED')
        assert records['treatment_episode'][0]['episode_status'] == 'BLOCKED_UNKNOWN'
        assert not records['episode_binding']
    result = provisional_patient_rows(template, 'source', 'DEVELOPMENT')
    assert result['rows'][0]['endpoint_evaluability'] == 'UNKNOWN'
    assert result['rows'][0]['inclusion_status'] == 'EXCLUDED'
