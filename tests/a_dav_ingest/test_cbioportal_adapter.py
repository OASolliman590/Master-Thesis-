"""Synthetic cBioPortal inputs only."""
import pytest

from tools.a_dav.cbioportal import read_clinical, read_meta, join_samples


def test_verified_author_links_exclude_rna_availability_exceptions():
    from tools.a_dav.cbioportal import verified_author_links
    def a(n, rna): return {'Patient no.': str(n), 'RNA Sequencing': rna, 'Sex': 'F', 'Age (Years)': '50', 'Treatment': 'Pembrolizumab', 'Best RECIST response': 'PR', 'Progression Free Survival (Days)': '304.375'}
    def p(n): return {'PATIENT_ID': 'PD'+str(n), 'SEX': 'Female', 'AGE_AT_DIAGNOSIS': '50', 'ICI_RX': 'Pembro', 'PFS_MONTHS': '10'}
    authors = {'mono': [a(1, 'PRE'), a(2, '-'), a(3, '-'), a(4, 'PRE')], 'dual': []}
    patients = [p(1), p(2)]
    samples = [{'PATIENT_ID': p['PATIENT_ID'], 'RESPONSE': 'Partial Response'} for p in patients]
    result = verified_author_links(authors, patients, samples)
    assert set(result['links']) == {'PD1'}
    assert result['matched_without_rna'] == 1 and result['unmatched_with_rna'] == 1
    assert result['matched_linked'] == 1 and result['unmatched_without_rna'] == 1


def test_linked_author_outcomes_preserve_orr_and_clinical_benefit_separately():
    from tools.a_dav.cbioportal import author_outcomes
    row = {'Best RECIST response': 'SD ', 'Progression Free Survival (Days)': '200', 'Progressed': 'No'}
    assert author_outcomes(row) == {'orr': 'SD', 'clinical_benefit': 'SOURCE_POSITIVE'}
    row['Progressed'] = 'Yes'
    assert author_outcomes(row) == {'orr': 'SD', 'clinical_benefit': 'UNKNOWN'}
    row['Best RECIST response'] = 'PD'
    assert author_outcomes(row) == {'orr': 'PD', 'clinical_benefit': 'SOURCE_NEGATIVE'}


def test_author_endpoint_records_are_separate_and_unlinked_patient_unchanged():
    from tools.a_dav.cbioportal import apply_author_endpoint_records
    tables = {'patient_registry': [{'patient_uid': 'u1', 'source_patient_id': 'PD1'}, {'patient_uid': 'u2', 'source_patient_id': 'PD2'}],
              'clinical_outcome': [{'outcome_id': 'u1:BOR', 'patient_uid': 'u1', 'canonical_category': 'UNKNOWN'},
                                   {'outcome_id': 'u2:BOR', 'patient_uid': 'u2', 'canonical_category': 'PD'}]}
    author = {'Best RECIST response': 'SD', 'Progression Free Survival (Days)': '200', 'Progressed': 'No'}
    apply_author_endpoint_records(tables, {'PD1': author}, {'PD1': 'source'})
    assert tables['clinical_outcome'][0]['canonical_category'] == 'SD'
    assert tables['clinical_outcome'][1]['canonical_category'] == 'PD'
    assert tables['clinical_outcome'][2]['endpoint_class'] == 'SOURCE_BINARY'
    assert tables['clinical_outcome'][2]['canonical_category'] == 'SOURCE_POSITIVE'
    assert tables['clinical_outcome'][2]['raw_endpoint_label'] == 'RECIST=SD; PFS_DAYS=200; PROGRESSED=No'


def test_cbio_ingest_uses_verified_author_clinical_endpoints():
    from tools.a_dav.ingest import build_canonical_records
    src = {r: {'locator': 'https://example.org/'+r, 'format': 'CBIO_CLINICAL_TSV', 'version': '1', 'sha256': None} for r in ('p', 's', 'a', 'b')}
    cfg = {'cohort': 'invented', 'branch_id': 'A_BASELINE_BIO', 'source_objects': src,
      'cbio_ingest': {'patient_role': 'p', 'sample_role': 's', 'matrix_role': 'm', 'patient_id': 'PATIENT_ID', 'sample_id': 'SAMPLE_ID',
        'visit_field': 'VISIT', 'baseline_values': ['Pre'], 'response_field': 'RESPONSE', 'response_map': {'Partial Response': 'PR'},
        'author_clinical_join': {'mono_role': 'a', 'dual_role': 'b'}}}
    patient = {'PATIENT_ID': 'PD1', 'SEX': 'Female', 'AGE_AT_DIAGNOSIS': '50', 'ICI_RX': 'Pembro', 'PFS_MONTHS': '10'}
    sample = {'PATIENT_ID': 'PD1', 'SAMPLE_ID': 'S1', 'VISIT': 'Pre', 'RESPONSE': 'Partial Response'}
    author = {'Patient no.': '1', 'RNA Sequencing': 'PRE', 'Sex': 'F', 'Age (Years)': '50', 'Treatment': 'Pembrolizumab',
              'Best RECIST response': 'PR', 'Progression Free Survival (Days)': '304.375', 'Progressed': 'No'}
    items = []; records = build_canonical_records({'p': [patient], 's': [sample], 'm': ('gene', 'S1'), 'a': [author], 'b': []}, {}, cfg, items)
    assert {x['endpoint_class'] for x in records['clinical_outcome']} == {'TUMOUR_RESPONSE', 'SOURCE_BINARY'}
    assert {x['canonical_category'] for x in records['clinical_outcome']} == {'PR', 'SOURCE_POSITIVE'}


def test_author_join_requires_every_row_unique_and_five_fields_agree():
    from tools.a_dav.cbioportal import verify_author_arm_number_join
    author = {'mono': [{'Patient no.': '1', 'Sex': 'F', 'Age (Years)': '50',
                        'Treatment': 'Pembrolizumab', 'Best RECIST response': 'PR',
                        'Progression Free Survival (Days)': '304.375'}], 'dual': []}
    patients = [{'PATIENT_ID': 'PD1', 'SEX': 'Female', 'AGE_AT_DIAGNOSIS': '50',
                 'ICI_RX': 'Pembro', 'PFS_MONTHS': '10'}]
    samples = [{'PATIENT_ID': 'PD1', 'RESPONSE': 'Partial Response'}]
    result = verify_author_arm_number_join(author, patients, samples)
    assert result['adopted'] and result['matched'] == 1
    assert all(v['agree'] == 1 and v['disagree'] == 0 for v in result['fields'].values())
    for key, value, field in [('SEX', 'Male', 'sex'), ('AGE_AT_DIAGNOSIS', '51', 'age'),
                              ('ICI_RX', 'Nivolumab', 'drug')]:
        old = patients[0][key]; patients[0][key] = value
        check = verify_author_arm_number_join(author, patients, samples)
        assert not check['adopted'] and check['fields'][field]['disagree'] == 1
        patients[0][key] = old
    samples[0]['RESPONSE'] = 'Progressive Disease'
    assert verify_author_arm_number_join(author, patients, samples)['fields']['response']['disagree'] == 1
    samples[0]['RESPONSE'] = 'Partial Response'
    check = verify_author_arm_number_join(author, patients, [])
    assert not check['adopted'] and check['fields']['response']['unresolved'] == 1
    patients[0]['PFS_MONTHS'] = '11'
    assert not verify_author_arm_number_join(author, patients, samples)['adopted']
    assert verify_author_arm_number_join(author, patients, samples)['fields']['pfs']['disagree'] == 1
    patients[0]['PFS_MONTHS'] = '10'
    author['mono'].append({**author['mono'][0], 'Patient no.': '2'})
    result = verify_author_arm_number_join(author, patients, samples)
    assert not result['adopted'] and result['unmatched_author'] == 1
    assert not verify_author_arm_number_join({'mono': author['mono'][:1], 'dual': []}, patients + patients, samples)['adopted']


def test_development_only_representation_refuses_final_test_and_confirmation():
    from tools.a_dav.provisional import cbio_preview_blockers
    receipt = {'checks': {'primary': {'status': 'PASS'}}}
    for role in ('FINAL_TEST', 'UNTOUCHED_FINAL_TEST', 'CONFIRMATION'):
        field_map = {'decision_config': {'preview': {'split_policy': role},
                     'representation_restrictions': {'development_only': True}}}
        assert 'DEVELOPMENT_ONLY_REPRESENTATION' in cbio_preview_blockers(field_map, receipt)


def test_development_only_signed_admission_rejects_final_test_before_io(tmp_path):
    from tools.a_dav.admit import run_fresh_signed_admission
    from tools.a_dav.core import DavError
    field_map = {'decision_config': {'preview': {'split_policy': 'FINAL_TEST'},
                 'representation_restrictions': {'development_only': True}}}
    with pytest.raises(DavError, match='DEVELOPMENT_ONLY_REPRESENTATION'):
        run_fresh_signed_admission('fictional', 'A_BASELINE_BIO', tmp_path, field_map,
                                   tmp_path / 'receipt', {}, tmp_path / 'out')
    assert not (tmp_path / 'out').exists()


def test_development_only_direct_preview_rejects_confirmation(tmp_path):
    from tools.a_dav.provisional import run_provisional
    field_map = {'decision_config': {'preview': {'split_policy': 'CONFIRMATION'},
                 'representation_restrictions': {'development_only': True}}}
    with pytest.raises(ValueError, match='DEVELOPMENT_ONLY_REPRESENTATION'):
        run_provisional({}, field_map, tmp_path, tmp_path / 'out')


def test_provisional_blocks_unresolved_author_outcome_join():
    from tools.a_dav.provisional import cbio_preview_blockers
    f = {'decision_config': {'preview': {'split_policy': 'DEVELOPMENT', 'author_endpoint_join': 'UNRESOLVED'}}}
    assert cbio_preview_blockers(f, {'checks': {'primary': {'status': 'PASS'}}}) == ['AUTHOR_ENDPOINT_JOIN_UNRESOLVED']


def test_signed_admission_blocks_unresolved_author_outcome_join(tmp_path):
    from tools.a_dav.admit import run_fresh_signed_admission
    from tools.a_dav.core import DavError
    f = {'decision_config': {'preview': {'split_policy': 'DEVELOPMENT', 'author_endpoint_join': 'UNRESOLVED'}}}
    with pytest.raises(DavError, match='AUTHOR_ENDPOINT_JOIN_UNRESOLVED'):
        run_fresh_signed_admission('invented', 'A_BASELINE_BIO', tmp_path, f, tmp_path/'v3', {}, tmp_path/'out')


def test_v3_accepts_only_explicitly_reviewed_unknown_processing_fields():
    from tools.a_dav.matrix_v3 import reviewed_processing_unknowns
    declaration = {'accepted_unknown_fields': ['genome_build'], 'evidence': 'decision:review',
                   'limitation': 'Alignment reference is unknown.', 'split_role': 'DEVELOPMENT'}
    unknown = ['genome_build', 'platform']
    remaining, limitation = reviewed_processing_unknowns(unknown, declaration, 'DEVELOPMENT')
    assert remaining == ['platform']
    assert limitation == 'Alignment reference is unknown.'
    assert reviewed_processing_unknowns(unknown, declaration, 'FINAL_TEST')[0] == unknown
    assert reviewed_processing_unknowns(unknown, {**declaration, 'evidence': ''}, 'DEVELOPMENT')[0] == unknown


def test_schema_accepts_reviewed_processing_declaration(tmp_path):
    import json
    from tools.a_dav.field_maps import load_field_map
    source = {'sha256': None, 'locator': 'https://example.org/matrix', 'version': 'v1',
              'format': 'MATRIX_HEADER_TSV', 'role': 'source_of_record'}
    doc = {'cohort': 'synthetic', 'branch_id': 'A_BASELINE_BIO', 'source_objects': {'m': source},
           'v3': {'primary_representation': 'm', 'sample_inventory_source_role': 'm',
                  'expected_counts': {'full_header_columns': 1, 'baseline_selected': 1, 'on_selected': 0},
                  'processing_acceptance': {
               'accepted_unknown_fields': ['genome_build'], 'evidence': 'decision',
               'limitation': 'unknown alignment', 'split_role': 'DEVELOPMENT'}}}
    path = tmp_path / 'map.json'; path.write_text(json.dumps(doc))
    assert load_field_map(path)['v3']['processing_acceptance']['split_role'] == 'DEVELOPMENT'


def test_schema_accepts_clinical_workbook_source(tmp_path):
    import json
    from tools.a_dav.field_maps import load_field_map
    source = {'sha256': None, 'locator': 'docs/decision#table', 'version': 'v1',
              'format': 'XLSX_CLINICAL', 'role': 'source_of_record', 'header_row': 3}
    path = tmp_path / 'map.json'
    path.write_text(json.dumps({'cohort': 'synthetic', 'branch_id': 'A_BASELINE_BIO', 'source_objects': {'s': source}}))
    assert load_field_map(path)['source_objects']['s']['header_row'] == 3


def test_schema_accepts_named_streaming_workbook_source(tmp_path):
    import json
    from tools.a_dav.field_maps import load_field_map
    source={'sha256':None,'locator':'https://example.org/s.xlsx','version':'v1','format':'XLSX_NAMED_STREAM',
            'role':'source_of_record','header_row':2,'sheet_name':'clinical','table_kind':'clinical'}
    path=tmp_path/'map.json';path.write_text(json.dumps({'cohort':'synthetic','branch_id':'A_BASELINE_BIO','source_objects':{'s':source}}))
    assert load_field_map(path)['source_objects']['s']['sheet_name']=='clinical'


def test_schema_accepts_documented_feature_exclusions(tmp_path):
    import json
    from tools.a_dav.field_maps import load_field_map
    doc = {'cohort': 'synthetic', 'branch_id': 'A_BASELINE_BIO',
           'source_objects': {'m': {'sha256': None, 'locator': 'https://example.org', 'version': 'v1', 'format': 'MATRIX_HEADER_TSV', 'role': 'source_of_record'}},
           'measurement_representations': {'m': {'unit': 'TPM', 'transform': 'NONE', 'genome_build': 'UNKNOWN', 'annotation': 'synthetic', 'feature_scope': 'COMPLETE_WITH_DOCUMENTED_EXCLUSIONS', 'negative_values_allowed':True, 'negative_values_source_phrase':'median centered',
               'excluded_feature_classes': [{'class': 'synthetic', 'evidence': 'synthetic source'}]}}}
    path = tmp_path / 'map.json'; path.write_text(json.dumps(doc))
    assert load_field_map(path)['measurement_representations']['m']['excluded_feature_classes']


def test_filtered_gene_universe_stays_unknown_in_provisional_policy():
    from tools.a_dav.assay_policy import provisional_feature_scope
    assert provisional_feature_scope('GENE_LEVEL_EXCLUDING_SNORNA', True) == 'UNKNOWN'
    assert provisional_feature_scope('GENE_LEVEL_EXCLUDING_SNORNA', False) == 'GENE_LEVEL_EXCLUDING_SNORNA'
    assert provisional_feature_scope('COMPLETE', True) == 'COMPLETE'


@pytest.mark.parametrize(('response', 'pfs', 'progressed', 'expected'), [
    ('CR', '1', 'Yes', 'SOURCE_POSITIVE'), ('PR', '', '', 'SOURCE_POSITIVE'),
    ('PD', '1', 'Yes', 'SOURCE_NEGATIVE'), ('SD', '182.5', 'No', 'SOURCE_NEGATIVE'),
    ('SD', '183', 'No', 'SOURCE_POSITIVE'), ('SD', '183', 'Yes', 'UNKNOWN'),
    ('SD', '', 'No', 'UNKNOWN'), ('NE', '1', 'No', 'UNKNOWN')])
def test_clinical_benefit_keeps_unknowns_distinct(response, pfs, progressed, expected):
    from tools.a_dav.cbioportal import clinical_benefit
    assert clinical_benefit(response, pfs, progressed) == expected


def test_provisional_metadata_carries_v3_limitation():
    from tools.a_dav.provisional import v3_limitations
    receipt = {'checks': {'primary': {'processing_limitation': 'alignment unknown',
                                     'processing_acceptance_evidence': 'decision'}}}
    assert v3_limitations(receipt) == {'processing_limitation': 'alignment unknown',
                                        'processing_acceptance_evidence': 'decision'}


def test_provisional_excludes_baseline_sample_without_rna():
    from tools.a_dav.provisional import provisional_patient_rows
    records = {'patient_registry': [{'patient_uid': 'P1', 'study_id': 'study'}, {'patient_uid': 'P2', 'study_id': 'study'}],
               'specimen_registry': [{'patient_uid': p, 'specimen_uid': p+'S',
                 'canonical_timing_category': 'PRE_INDEX_BASELINE', 'biological_compartment': 'TUMOUR',
                 'baseline_candidate_status': 'YES'} for p in ('P1', 'P2')],
               'assay_registry': [{'specimen_uid': 'P1S', 'source_object_id': 'source', 'assay_uid': 'A1', 'matrix_header': 'S1'}],
               'clinical_outcome': [], 'treatment_episode': [{'patient_uid': 'P1'}]}
    result = provisional_patient_rows(records, 'source', 'DEVELOPMENT', exclude_without_assay=True)
    assert len(result['rows']) == 1


def test_provisional_chooses_orr_without_merging_separate_clinical_benefit():
    from tools.a_dav.provisional import provisional_patient_rows
    records={'patient_registry':[{'patient_uid':'P1','study_id':'S'}],
      'specimen_registry':[{'patient_uid':'P1','specimen_uid':'SP','canonical_timing_category':'PRE_INDEX_BASELINE','biological_compartment':'TUMOUR','baseline_candidate_status':'YES'}],
      'assay_registry':[{'specimen_uid':'SP','source_object_id':'source','assay_uid':'A','matrix_header':'S1'}],
      'clinical_outcome':[{'patient_uid':'P1','endpoint_class':'TUMOUR_RESPONSE','raw_endpoint_label':'PR','canonical_category':'PR'},
                          {'patient_uid':'P1','endpoint_class':'SOURCE_BINARY','raw_endpoint_label':'x','canonical_category':'UNKNOWN'}],
      'treatment_episode':[{'patient_uid':'P1'}]}
    row=provisional_patient_rows(records,'source','DEVELOPMENT')['rows'][0]
    assert row['canonical_category']=='PR' and row['endpoint_evaluability']=='EVALUABLE'
    assert row['endpoint_evaluability_by_class']=={'TUMOUR_RESPONSE':'EVALUABLE','SOURCE_BINARY':'UNKNOWN'}


def test_excluded_other_pretreatment_is_not_on_treatment():
    from tools.a_dav.ingest import build_canonical_records
    cfg = {'cohort': 'invented', 'branch_id': 'A_BASELINE_BIO',
           'source_objects': {role: {'locator': 'https://example.org/'+role, 'format': 'CBIO_CLINICAL_TSV',
                                     'version': '1', 'sha256': None} for role in ('p', 's')},
           'cbio_ingest': {'patient_role': 'p', 'sample_role': 's', 'matrix_role': 'm',
               'patient_id': 'PATIENT_ID', 'sample_id': 'SAMPLE_ID', 'visit_field': 'VISIT',
               'baseline_values': ['Pre'], 'excluded_visit_values': ['Earlier'], 'response_field': 'RESPONSE', 'response_map': {}}}
    items = []
    records = build_canonical_records({'p': [{'PATIENT_ID': 'P1'}],
               's': [{'PATIENT_ID': 'P1', 'SAMPLE_ID': 'S1', 'VISIT': 'Earlier'}], 'm': ('gene', 'S1')}, {}, cfg, items)
    specimen = records['specimen_registry'][0]
    assert specimen['baseline_candidate_status'] == 'NO'
    assert specimen['canonical_timing_category'] != 'ON_TREATMENT'
    assert not any(item['category'] == 'BASELINE_TIMING_UNRESOLVED' for item in items)


def test_clinical_skips_comment_rows_and_joins_patient_sample_and_expression():
    patients=read_clinical(b'#Description\tPatient\nPATIENT_ID\tRESPONSE\tDRUG\nP1\tPR\tanti-PD-1\n')
    samples=read_clinical(b'#Type\tType\tType\nPATIENT_ID\tSAMPLE_ID\tVISIT\nP1\tS1\tPre\nP1\tS2\tOn\n')
    result=join_samples(patients,samples,['S1','S2'],{'patient_id':'PATIENT_ID','sample_id':'SAMPLE_ID','visit_field':'VISIT','baseline_values':['Pre'],'response_field':'RESPONSE','drug_field':'DRUG'})
    assert len(result['samples'])==2
    assert result['samples'][0]['baseline'] is True
    assert result['samples'][1]['baseline'] is False
    assert result['samples'][0]['response']=='PR'
    assert result['samples'][0]['drug']=='anti-PD-1'
    assert result['samples'][0]['identity_confidence']=='UNRESOLVED'
    assert result['items']==[]


def test_orphan_and_missing_matrix_join_are_reported_without_guessing():
    patients=read_clinical(b'PATIENT_ID\tRESPONSE\nP1\tCR\n')
    samples=read_clinical(b'PATIENT_ID\tSAMPLE_ID\tVISIT\nP2\tS1\tPre\nP1\tS2\tPre\n')
    result=join_samples(patients,samples,['S1'],{'patient_id':'PATIENT_ID','sample_id':'SAMPLE_ID','visit_field':'VISIT','baseline_values':['Pre'],'response_field':'RESPONSE'})
    assert {x['category'] for x in result['items']}=={'PATIENT_JOIN_UNRESOLVED','EXPRESSION_SAMPLE_UNMATCHED'}
    assert all(x['identity_confidence']=='UNRESOLVED' for x in result['samples'])


def test_meta_records_source_units_without_inference():
    data=read_meta(b'genetic_alteration_type: MRNA_EXPRESSION\nprofile_name: mRNA expression (TPM)\n')
    assert data['genetic_alteration_type']=='MRNA_EXPRESSION'
    assert data['profile_name']=='mRNA expression (TPM)'
    assert 'units' not in data
    with pytest.raises(ValueError):read_meta(b'profile_name: one\nprofile_name: two\n')


def test_canonical_ingest_keeps_source_identifiers_and_unverified_identity():
    from tools.a_dav.ingest import build_canonical_records
    cfg={'cohort':'invented','branch_id':'A_BASELINE_BIO','study_class':'CLINICAL_ICI','source_objects':{'patients':{'locator':'https://example.org/p','format':'DELIMITED_TSV','version':'1','sha256':None},'samples':{'locator':'https://example.org/s','format':'DELIMITED_TSV','version':'1','sha256':None}},'cbio_ingest':{'patient_role':'patients','sample_role':'samples','matrix_role':'matrix','patient_id':'PATIENT_ID','sample_id':'SAMPLE_ID','visit_field':'VISIT','baseline_values':['Pre'],'response_field':'RESPONSE','response_map':{'PR':'PR'},'drug_field':'DRUG'}}
    patients=read_clinical(b'PATIENT_ID\tRESPONSE\tDRUG\nP1\tPR\tanti-PD-1\n')
    samples=read_clinical(b'PATIENT_ID\tSAMPLE_ID\tVISIT\nP1\tS1\tPre\n')
    items=[]; r=build_canonical_records({'patients':patients,'samples':samples,'matrix':('Hugo_Symbol','S1')},{},cfg,items)
    assert len(r['patient_registry'])==1
    assert r['patient_registry'][0]['source_patient_id']=='P1'
    assert r['patient_registry'][0]['patient_identity_confidence']=='UNRESOLVED'
    assert r['specimen_registry'][0]['baseline_candidate_status']=='YES'
    assert r['clinical_outcome'][0]['endpoint_class']=='TUMOUR_RESPONSE'
    assert r['clinical_outcome'][0]['canonical_category']=='PR'
    assert r['clinical_outcome'][0]['evaluability']=='UNKNOWN'


def test_cbio_ingest_excludes_non_ici_arm_before_patient_join():
    from tools.a_dav.ingest import build_canonical_records
    source={r:{'locator':'https://example.org/'+r,'format':'CBIO_CLINICAL_TSV','version':'1','sha256':None} for r in ('p','s')}
    f={'cohort':'invented','branch_id':'A_BASELINE_BIO','source_objects':source,'cbio_ingest':{'patient_role':'p','sample_role':'s','matrix_role':'m','patient_id':'PATIENT_ID','sample_id':'SAMPLE_ID','visit_field':'VISIT','baseline_values':['Pre'],'response_field':'RESPONSE','response_map':{'PR':'PR'},'cohort_filter':{'field':'ARM','allowed_values':['ICI']}}}
    rows=[{'PATIENT_ID':'P1','SAMPLE_ID':'S1','ARM':'ICI','VISIT':'Pre','RESPONSE':'PR'}, {'PATIENT_ID':'P2','SAMPLE_ID':'S2','ARM':'OTHER','VISIT':'Pre','RESPONSE':'PR'}]
    result=build_canonical_records({'p':rows,'s':rows,'m':('gene','S1','S2')},{},f,[])
    assert len(result['patient_registry'])==1 and result['patient_registry'][0]['source_patient_id']=='P1'
    mixed=[rows[0],{**rows[1],'PATIENT_ID':'P1'}]
    issues=[];result=build_canonical_records({'p':mixed,'s':mixed,'m':('gene','S1','S2')},{},f,issues)
    assert not result['patient_registry']
    assert any(item['category']=='COHORT_FILTER_IDENTITY_AMBIGUOUS' for item in issues)


def test_cbio_declared_expression_only_excludes_unmatched_clinical_rows():
    from tools.a_dav.ingest import build_canonical_records
    source={r:{'locator':'https://example.org/'+r,'format':'CBIO_CLINICAL_TSV','version':'1','sha256':None} for r in ('p','s')}
    f={'cohort':'invented','branch_id':'A_BASELINE_BIO','source_objects':source,'cbio_ingest':{'patient_role':'p','sample_role':'s','matrix_role':'m','patient_id':'PATIENT_ID','sample_id':'SAMPLE_ID','visit_field':'VISIT','baseline_values':['Pre'],'response_field':'RESPONSE','response_map':{'PR':'PR'},'expression_samples_only':True}}
    rows=[{'PATIENT_ID':'P1','SAMPLE_ID':'S1','VISIT':'Pre','RESPONSE':'PR'}, {'PATIENT_ID':'P2','SAMPLE_ID':'','VISIT':'Pre','RESPONSE':'PR'}]
    issues=[];result=build_canonical_records({'p':rows,'s':rows,'m':('gene','S1')},{},f,issues)
    assert len(result['patient_registry'])==1 and result['patient_registry'][0]['source_patient_id']=='P1'
    assert any(item['category']=='CLINICAL_WITHOUT_EXPRESSION_EXCLUDED' and item['context']['sample_count']==1 for item in issues)


def test_cbio_retains_two_source_endpoints_when_timing_is_unknown():
    from tools.a_dav.ingest import build_canonical_records
    source={r:{'locator':'https://example.org/'+r,'format':'CBIO_CLINICAL_TSV','version':'1','sha256':None} for r in ('p','s')}
    f={'cohort':'invented','branch_id':'A_BASELINE_BIO','source_objects':source,'cbio_ingest':{'patient_role':'p','sample_role':'s','matrix_role':'m','patient_id':'PATIENT_ID','sample_id':'SAMPLE_ID','visit_field':'VISIT','baseline_values':[],'response_field':'RESPONSE','response_map':{'PR':'PR'},
       'outcomes_without_baseline':True,'secondary_outcome':{'field':'BENEFIT','endpoint_class':'SOURCE_BINARY','response_map':{'R':'SOURCE_POSITIVE'}}}}
    rows=[{'PATIENT_ID':'P1','SAMPLE_ID':'S1','VISIT':'','RESPONSE':'PR','BENEFIT':'R'}]
    result=build_canonical_records({'p':rows,'s':rows,'m':('gene','S1')},{},f,[])
    assert {(o['endpoint_class'],o['canonical_category']) for o in result['clinical_outcome']}=={('TUMOUR_RESPONSE','PR'),('SOURCE_BINARY','SOURCE_POSITIVE')}
    patient=[{'PATIENT_ID':'P1','RESPONSE':'PR'}];sample=[{'PATIENT_ID':'P1','SAMPLE_ID':'S1','VISIT':'','BENEFIT':'R'}]
    result=build_canonical_records({'p':patient,'s':sample,'m':('gene','S1')},{},f,[])
    assert next(o for o in result['clinical_outcome'] if o['endpoint_class']=='SOURCE_BINARY')['source_locators'][0]['value']=='https://example.org/s'


def test_ingestion_parses_cbio_clinical_and_meta_objects():
    from types import SimpleNamespace
    from tools.a_dav.ingest import _parse_source
    clinical=SimpleNamespace(bytes=b'#description\nPATIENT_ID\tSAMPLE_ID\nP1\tS1\n')
    assert _parse_source(clinical,{'format':'CBIO_CLINICAL_TSV'})==[{'PATIENT_ID':'P1','SAMPLE_ID':'S1'}]
    meta=SimpleNamespace(bytes=b'profile_name: mRNA expression (TPM)\n')
    assert _parse_source(meta,{'format':'CBIO_META'})['profile_name']=='mRNA expression (TPM)'


def test_field_map_accepts_declared_cbioportal_roles(tmp_path):
    import json
    from tools.a_dav.field_maps import load_field_map
    doc={'cohort':'synthetic','branch_id':'A_BASELINE_BIO','source_objects':{'meta':{'sha256':None,'locator':'https://example.org/meta','version':'v1','format':'CBIO_META','role':'source_of_record'}},'cbio_ingest':{'patient_role':'patients','sample_role':'samples','matrix_role':'matrix','patient_id':'PATIENT_ID','sample_id':'SAMPLE_ID','visit_field':'VISIT','baseline_values':['Pre'],'response_field':'RESPONSE','response_map':{'PR':'PR'}}}
    path=tmp_path/'map.json';path.write_text(json.dumps(doc));assert load_field_map(path)['cbio_ingest']['patient_id']=='PATIENT_ID'


def test_field_map_accepts_author_clinical_join(tmp_path):
    import json
    from tools.a_dav.field_maps import load_field_map
    doc={'cohort':'synthetic','branch_id':'A_BASELINE_BIO','source_objects':{'meta':{'sha256':None,'locator':'https://example.org/meta','version':'v1','format':'CBIO_META','role':'source_of_record'}},'cbio_ingest':{'patient_role':'p','sample_role':'s','matrix_role':'m','patient_id':'PATIENT_ID','sample_id':'SAMPLE_ID','visit_field':'VISIT','baseline_values':['Pre'],'response_field':'RESPONSE','response_map':{'PR':'PR'},'author_clinical_join':{'mono_role':'a','dual_role':'b'}}}
    path=tmp_path/'map.json';path.write_text(json.dumps(doc))
    assert load_field_map(path)['cbio_ingest']['author_clinical_join']['mono_role']=='a'


def test_schema_accepts_declared_ici_arm_filter(tmp_path):
    import json
    from tools.a_dav.field_maps import load_field_map
    doc={'cohort':'synthetic','branch_id':'A_BASELINE_BIO','source_objects':{'m':{'sha256':None,'locator':'https://example.org','version':'1','format':'CBIO_META','role':'source_of_record'}},
      'cbio_ingest':{'patient_role':'p','sample_role':'s','matrix_role':'m','patient_id':'P','sample_id':'S','visit_field':'V','baseline_values':[],'response_field':'R','response_map':{},'cohort_filter':{'field':'ARM','allowed_values':['ICI']},'expression_samples_only':True,'outcomes_without_baseline':True,'secondary_outcome':{'field':'B','endpoint_class':'SOURCE_BINARY','response_map':{}}}}
    path=tmp_path/'map.json';path.write_text(json.dumps(doc))
    assert load_field_map(path)['cbio_ingest']['cohort_filter']['allowed_values']==['ICI']


def test_v3_field_map_can_declare_no_confirmed_baseline(tmp_path):
    import json
    from tools.a_dav.field_maps import load_field_map
    doc={'cohort':'synthetic','branch_id':'A_BASELINE_BIO','source_objects':{'m':{'sha256':None,'locator':'https://example.org/m','version':'v1','format':'MATRIX_HEADER_TSV','role':'source_of_record'}},
         'v3':{'primary_representation':'m','sample_inventory_source_role':'m','expected_counts':{'full_header_columns':1,'baseline_selected':0,'on_selected':0}}}
    p=tmp_path/'map.json';p.write_text(json.dumps(doc));assert load_field_map(p)['v3']['expected_counts']['baseline_selected']==0


def test_cbio_ingestion_cli_builds_unsigned_review_context(tmp_path, monkeypatch):
    import hashlib,json
    from tools.a_dav import ingest
    objects={'patient':('CBIO_CLINICAL_TSV',b'PATIENT_ID\tRESPONSE\tDRUG\nP1\tPR\tdrug\n'), 'sample':('CBIO_CLINICAL_TSV',b'PATIENT_ID\tSAMPLE_ID\tVISIT\nP1\tS1\tPre\n'), 'matrix':('MATRIX_HEADER_TSV',b'Hugo_Symbol\tS1\nG1\t1\n')}
    store=tmp_path/'store';(store/'objects').mkdir(parents=True); manifest={};src={}
    for role,(fmt,raw) in objects.items():
        sha=hashlib.sha256(raw).hexdigest();(store/'objects'/sha).write_bytes(raw);url='https://example.org/'+role
        manifest[sha]={'locator':url,'version':'v1','byte_size':len(raw),'retrieved_at':'2026-01-01'}
        src[role]={'sha256':sha,'locator':url,'version':'v1','format':fmt,'role':'source_of_record'}
    (store/'MANIFEST.json').write_text(json.dumps({'objects':manifest}));maps=tmp_path/'maps';maps.mkdir()
    cfg={'cohort':'fictional','branch_id':'A_BASELINE_BIO','study_class':'CLINICAL_ICI','source_objects':src,'cbio_ingest':{'patient_role':'patient','sample_role':'sample','matrix_role':'matrix','patient_id':'PATIENT_ID','sample_id':'SAMPLE_ID','visit_field':'VISIT','baseline_values':['Pre'],'response_field':'RESPONSE','response_map':{'PR':'PR'},'drug_field':'DRUG'},'measurement_representations':{'matrix':{'unit':'TPM','transform':'NONE','platform':'UNKNOWN','annotation':'Hugo','genome_build':'UNKNOWN'}}}
    (maps/'fictional.json').write_text(json.dumps(cfg));monkeypatch.setattr(ingest,'FIELD_MAP_ROOT',maps)
    result=ingest.run_ingest('fictional','A_BASELINE_BIO',store,tmp_path/'out',allow_external_out=True)
    assert result['summary']['counts']['baseline_samples_linked_to_patient']==1
    assert result['packet']['records']['patient_registry'][0]['patient_identity_confidence']=='UNRESOLVED'
    assert result['packet']['records']['assay_registry'][0]['source_sample_id']=='S1'
    assert result['worksheet']['review_status']=='UNSIGNED'


def test_cbio_v3_blocks_unestablished_platform_and_checks_source_sample_axis(tmp_path):
    import hashlib
    from tools.a_dav.matrix_v3 import run_cbioportal_v3
    def obj(data):
        sha=hashlib.sha256(data).hexdigest();(tmp_path/'objects').mkdir(exist_ok=True);(tmp_path/'objects'/sha).write_bytes(data);return sha
    ss=obj(b'PATIENT_ID\tSAMPLE_ID\tVISIT\nP1\tS1\tPre\n')
    mm=obj(b'Hugo_Symbol\tS1\nG1\t1\n')
    meta=obj(b'profile_name: mRNA expression (TPM)\n')
    f={'source_objects':{'samples':{'sha256':ss},'matrix':{'sha256':mm},'meta':{'sha256':meta}},'cbio_ingest':{'sample_role':'samples','sample_id':'SAMPLE_ID','visit_field':'VISIT','baseline_values':['Pre'],'nonbaseline_values':['On']},'measurement_representations':{'matrix':{'unit':'TPM','transform':'NONE','platform':'UNKNOWN','genome_build':'hg38','annotation':'GENE_SYMBOL','feature_identifier_system':'GENE_SYMBOL'}},'v3':{'primary_representation':'matrix','sample_inventory_source_role':'samples','expected_counts':{'full_header_columns':1,'baseline_selected':1,'on_selected':0},'source_object_roles':{'primary':'matrix'},'documentation':{'matrix':{'status':'DOCUMENTED','evidence_pointer':'meta:profile_name'}},'delimiters':{'matrix':'\t'},'compressed':{'matrix':False}}}
    result=run_cbioportal_v3(tmp_path,f)
    assert result['checks']['primary']['status']=='BLOCKED'
    assert 'PROCESSING_DOCUMENTATION_INSUFFICIENT' in result['checks']['primary']['reasons']
    assert result['checks']['primary']['counts']['selected_pre_columns']==1


def test_cbio_v3_ignores_clinical_samples_without_matrix_columns(tmp_path):
    import hashlib
    from tools.a_dav.matrix_v3 import run_cbioportal_v3
    def obj(data):
        sha=hashlib.sha256(data).hexdigest();(tmp_path/'objects').mkdir(exist_ok=True);(tmp_path/'objects'/sha).write_bytes(data);return sha
    ss=obj(b'PATIENT_ID\tSAMPLE_ID\tVISIT\nP1\tS1\tPre\nP2\tS2\tPre\n');mm=obj(b'Hugo_Symbol\tS1\nG1\t1\n')
    f={'source_objects':{'samples':{'sha256':ss},'matrix':{'sha256':mm}},'cbio_ingest':{'sample_role':'samples','sample_id':'SAMPLE_ID','visit_field':'VISIT','baseline_values':['Pre']},
       'measurement_representations':{'matrix':{'unit':'TPM','transform':'NONE','platform':'invented','genome_build':'hg38','annotation':'GENE_SYMBOL','feature_identifier_system':'GENE_SYMBOL'}},
       'v3':{'primary_representation':'matrix','expected_counts':{'full_header_columns':1,'baseline_selected':1,'on_selected':0},'documentation':{'matrix':{'status':'DOCUMENTED'}},'delimiters':{'matrix':'\t'},'compressed':{'matrix':False}}}
    result=run_cbioportal_v3(tmp_path,f)['checks']['primary']
    assert result['status']=='PASS' and result['counts']['selected_pre_columns']==1


def test_cbio_v3_accepts_negative_log2_values_without_assuming_count_scale(tmp_path):
    import hashlib
    from tools.a_dav.matrix_v3 import run_cbioportal_v3
    def obj(data):
        sha=hashlib.sha256(data).hexdigest();(tmp_path/'objects').mkdir(exist_ok=True);(tmp_path/'objects'/sha).write_bytes(data);return sha
    ss=obj(b'PATIENT_ID\tSAMPLE_ID\tVISIT\nP1\tS1\tPre\n');mm=obj(b'Hugo_Symbol\tS1\nG1\t-1\n')
    f={'source_objects':{'samples':{'sha256':ss},'matrix':{'sha256':mm}},'cbio_ingest':{'sample_role':'samples','sample_id':'SAMPLE_ID','visit_field':'VISIT','baseline_values':['Pre']},'measurement_representations':{'matrix':{'unit':'log_expression','transform':'LOG2','platform':'invented','genome_build':'hg38','annotation':'GENE_SYMBOL','feature_identifier_system':'GENE_SYMBOL'}},'v3':{'primary_representation':'matrix','expected_counts':{'full_header_columns':1,'baseline_selected':1,'on_selected':0},'documentation':{'matrix':{'status':'DOCUMENTED'}},'delimiters':{'matrix':'\t'},'compressed':{'matrix':False}}}
    result=run_cbioportal_v3(tmp_path,f)['checks']['primary']
    assert result['checks']['numeric_validity']['status']=='PASS'
    assert result['counts']['negative_cells']==1


def test_v3_inventory_discards_outcome_and_drug_fields():
    from tools.a_dav.cbioportal import read_inventory
    raw=b'# comment\nSAMPLE_ID\tVISIT\tRESPONSE\tDRUG\nS1\tPre\tPR\tanti-PD-1\n'
    assert read_inventory(raw,['SAMPLE_ID','VISIT'])==[{'SAMPLE_ID':'S1','VISIT':'Pre'}]


def test_cbio_preview_reports_split_and_v3_blockers_without_inventing_role():
    from tools.a_dav.provisional import cbio_preview_blockers
    f={'decision_config':{'preview':{'split_policy':'UNKNOWN'}}}
    receipt={'checks':{'primary':{'status':'BLOCKED','reasons':['PROCESSING_DOCUMENTATION_INSUFFICIENT']}}}
    result=cbio_preview_blockers(f,receipt)
    assert result==['SPLIT_NOT_FROZEN','V3_BLOCKED:PROCESSING_DOCUMENTATION_INSUFFICIENT']


def test_unknown_responses_are_counted_without_assuming_not_evaluable():
    from tools.a_dav.ingest import build_canonical_records
    cfg={'cohort':'invented','branch_id':'A_BASELINE_BIO','source_objects':{'p':{'locator':'https://example.org/p','format':'DELIMITED_TSV','version':'1','sha256':None},'s':{'locator':'https://example.org/s','format':'DELIMITED_TSV','version':'1','sha256':None}},'cbio_ingest':{'patient_role':'p','sample_role':'s','matrix_role':'m','patient_id':'PATIENT_ID','sample_id':'SAMPLE_ID','visit_field':'VISIT','baseline_values':['Pre'],'response_field':'RESPONSE','response_map':{}}}
    p=read_clinical(b'PATIENT_ID\tRESPONSE\nP1\tNA\nP2\tNA\n');s=read_clinical(b'PATIENT_ID\tSAMPLE_ID\tVISIT\nP1\tS1\tPre\nP2\tS2\tPre\n');items=[]
    result=build_canonical_records({'p':p,'s':s,'m':('gene','S1','S2')},{},cfg,items)
    assert [o['canonical_category'] for o in result['clinical_outcome']]==['UNKNOWN','UNKNOWN']
    unknown=[i for i in items if i['category']=='ORR_RESPONSE_UNKNOWN']
    assert len(unknown)==1 and unknown[0]['context']['record_count']==2


def test_cbio_preview_writes_blockers_and_unsigned_worksheet(tmp_path, monkeypatch):
    import json
    from tools.a_dav import admit
    from tools.a_dav.worksheet import build_worksheet
    packet={'classification':'PRIVATE_PATIENT_LEVEL','branch_id':'A_BASELINE_BIO','records':{'study_registry':[{'study_id':'invented'}]},'config':{},'dependencies':{}}
    worksheet=build_worksheet(packet)
    monkeypatch.setattr(admit,'validate_output_path',lambda path:path)
    monkeypatch.setattr(admit,'run_ingest',lambda *a,**kw:{'packet':packet,'worksheet':worksheet})
    receipt=tmp_path/'receipt.json';receipt.write_text(json.dumps({'checks':{'primary':{'status':'BLOCKED','reasons':['FEATURE_ID_BLANK']}}}))
    f={'cbio_ingest':{},'decision_config':{'preview':{'split_policy':'UNKNOWN'}}}
    result=admit.run_fresh_provisional('invented','A_BASELINE_BIO',tmp_path,f,receipt,tmp_path/'out')
    assert result['status']=='BLOCKED_UNKNOWN'
    assert 'SPLIT_NOT_FROZEN' in result['reasons']
    assert (tmp_path/'out'/'reviewer_worksheet.unsigned.json').is_file()
    assert not (tmp_path/'out'/'table').exists()


def test_geo_preview_reports_blocked_v3_before_baseline_selection(tmp_path, monkeypatch):
    import json
    from tools.a_dav import admit
    from tools.a_dav.worksheet import build_worksheet
    packet={'classification':'PRIVATE_PATIENT_LEVEL','branch_id':'A_BASELINE_BIO','records':{'study_registry':[{'study_id':'invented'}]},'config':{'admission':{'ingestion_worksheet':[]}},'dependencies':{}}
    monkeypatch.setattr(admit,'validate_output_path',lambda path:path)
    monkeypatch.setattr(admit,'run_ingest',lambda *a,**kw:{'packet':packet,'worksheet':build_worksheet(packet)})
    receipt=tmp_path/'receipt.json';receipt.write_text(json.dumps({'checks':{'primary':{'status':'BLOCKED','reasons':['EMPTY_BASELINE_SELECTION']}}}))
    f={'geo_ingest':{},'decision_config':{'preview':{'split_policy':'UNKNOWN'}}}
    result=admit.run_fresh_provisional('invented','A_BASELINE_BIO',tmp_path,f,receipt,tmp_path/'out')
    assert result['status']=='BLOCKED_UNKNOWN' and 'V3_BLOCKED:EMPTY_BASELINE_SELECTION' in result['reasons']
    assert (tmp_path/'out'/'reviewer_worksheet.unsigned.json').is_file()


def test_blocked_v3_reasons_are_worksheet_items():
    from tools.a_dav.provisional import add_v3_blocker_item
    p={'config':{'admission':{'ingestion_worksheet':[]}}}
    receipt={'checks':{'primary':{'status':'BLOCKED','reasons':['FEATURE_ID_DUPLICATE']}},'source_sha256':{'primary':'a'*64}}
    result=add_v3_blocker_item(p,receipt)
    item=result['config']['admission']['ingestion_worksheet'][0]
    assert item['category']=='V3_REVIEW_REQUIRED' and item['context']['reasons']==['FEATURE_ID_DUPLICATE']
    assert p['config']['admission']['ingestion_worksheet']==[]


def test_author_crosscheck_counts_disagreement_without_replacing_source_labels():
    from tools.a_dav.cbioportal import crosscheck_by_patient
    source=[{'PATIENT_ID':'P1','RESPONSE':'PR'},{'PATIENT_ID':'P2','RESPONSE':'PD'}]
    author=[{'PATIENT_ID':'P1','BR':'PR'},{'PATIENT_ID':'P2','BR':'SD'}]
    result=crosscheck_by_patient(source,author,'PATIENT_ID','RESPONSE','BR')
    assert result=={'matched_patients':2,'agree':1,'different':1,'unmatched':0}
    assert source[1]['RESPONSE']=='PD'


def test_crosscheck_disagreement_emits_one_review_item():
    from tools.a_dav.ingest import build_canonical_records
    cfg={'cohort':'invented','branch_id':'A_BASELINE_BIO','source_objects':{'p':{'locator':'https://example.org/p','format':'DELIMITED_TSV','version':'1','sha256':None},'s':{'locator':'https://example.org/s','format':'DELIMITED_TSV','version':'1','sha256':None}},'cbio_ingest':{'patient_role':'p','sample_role':'s','matrix_role':'m','patient_id':'PATIENT_ID','sample_id':'SAMPLE_ID','visit_field':'VISIT','baseline_values':['Pre'],'response_field':'RESPONSE','response_map':{'PR':'PR'},'response_crosscheck':{'source_role':'s','author_role':'author','source_field':'RESPONSE','author_field':'BR'}}}
    p=read_clinical(b'PATIENT_ID\tDRUG\nP1\tdrug\n');s=read_clinical(b'PATIENT_ID\tSAMPLE_ID\tVISIT\tRESPONSE\nP1\tS1\tPre\tPR\n');a=read_clinical(b'PATIENT_ID\tBR\nP1\tPD\n');items=[]
    result=build_canonical_records({'p':p,'s':s,'author':a,'m':('gene','S1')},{},cfg,items)
    assert result['clinical_outcome'][0]['canonical_category']=='PR'
    issue=next(i for i in items if i['category']=='AUTHOR_RESPONSE_DISAGREEMENT')
    assert issue['context']['different']==1


def test_signed_cbio_identity_requires_verified_source_join_and_v4(tmp_path):
    import copy,hashlib,json
    from tools.a_dav.admit import verify_signed_cbio_identities
    from tools.a_dav.worksheet import build_worksheet
    from tools.a_dav.core import DavError
    raws={'patients':b'PATIENT_ID\tDRUG\nP1\tdrug\n','samples':b'PATIENT_ID\tSAMPLE_ID\nP1\tS1\n'};objects={};sources={};(tmp_path/'objects').mkdir()
    for role,raw in raws.items():
        sha=hashlib.sha256(raw).hexdigest();(tmp_path/'objects'/sha).write_bytes(raw);objects[sha]={'locator':'https://example.org/'+role,'version':'1','byte_size':len(raw),'retrieved_at':'2026-10-30'};sources[role]={'sha256':sha}
    (tmp_path/'MANIFEST.json').write_text(json.dumps({'objects':objects}))
    f={'cbio_ingest':{'patient_role':'patients','sample_role':'samples','patient_id':'PATIENT_ID','sample_id':'SAMPLE_ID'},'source_objects':sources}
    p={'branch_id':'A_BASELINE_BIO','records':{'study_registry':[{'study_id':'study'}],'source_record':[],'patient_registry':[{'patient_uid':'uid','source_patient_id':'P1','patient_identity_confidence':'UNRESOLVED','source_locators':[]}],'specimen_registry':[{'patient_uid':'uid','raw_sample_aliases':['S1']}]},'config':{}}
    w=build_worksheet(p);w.update(review_status='SIGNED',signature={'reviewer_name':'invented','review_date':'2026-10-30','source_reviewer_name':'invented','source_review_date':'2026-10-30','integrator_name':'invented','integration_date':'2026-10-30'},decisions=[{'item_id':i['item_id'],'status':'PASS'} for i in w['items']])
    signed_result = verify_signed_cbio_identities(p,f,w,tmp_path)
    assert signed_result['records']['patient_registry'][0]['patient_identity_confidence']=='VERIFIED'
    assert signed_result['records']['specimen_registry'][0]['tissue_type']=='UNKNOWN'
    assert p['records']['patient_registry'][0]['patient_identity_confidence']=='UNRESOLVED'
    blocked=copy.deepcopy(w);next(x for x in blocked['decisions'] if x['item_id']=='V4')['status']='BLOCKED_UNKNOWN'
    assert verify_signed_cbio_identities(p,f,blocked,tmp_path)['records']['patient_registry'][0]['patient_identity_confidence']=='UNRESOLVED'
    unsigned=copy.deepcopy(w);unsigned['review_status']='UNSIGNED'
    with pytest.raises(DavError):verify_signed_cbio_identities(p,f,unsigned,tmp_path)


def test_signed_cbio_v5_binds_outcome_and_drug_component_without_unsigned_upgrade():
    from tools.a_dav.admit import verify_signed_cbio_outcome_bindings
    from tools.a_dav.worksheet import build_worksheet
    p={'classification':'SYNTHETIC_ONLY','branch_id':'A_BASELINE_BIO', 'records':{
      'study_registry':[{'study_id':'study'}], 'clinical_outcome':[{'outcome_id':'o','patient_uid':'p'},{'outcome_id':'o2','patient_uid':'p2'}],
      'treatment_episode':[{'treatment_episode_id':'e','patient_uid':'p','regimen_id':'r','index_event':'START_OF_INDEX_TREATMENT','component_exposure_ids':['x'],'episode_status':'BLOCKED_UNKNOWN'},
          {'treatment_episode_id':'e2','patient_uid':'p2','regimen_id':'r','index_event':'START_OF_INDEX_TREATMENT','component_exposure_ids':['x2'],'episode_status':'BLOCKED_UNKNOWN'}],
      'treatment_exposure':[{'treatment_exposure_id':'x','patient_uid':'p','regimen_id':'r','certainty':'UNRESOLVED','pharmacological_class':'ANTI_PD_1'},
          {'treatment_exposure_id':'x2','patient_uid':'p2','regimen_id':'r','certainty':'UNRESOLVED','pharmacological_class':'ANTI_PD_1_PLUS_ANTI_CTLA_4'}],
      'specimen_registry':[],'episode_binding':[]}, 'config':{}}
    f={'cbio_ingest':{'patient_role':'patient','treatment':{'regimen_id':'r'}},'source_objects':{'patient':{'locator':'https://example.org/patient'}}}
    w=build_worksheet(p);w.update(review_status='SIGNED',signature={'reviewer_name':'invented','review_date':'2026-10-30','source_reviewer_name':'invented','source_review_date':'2026-10-30','integrator_name':'invented','integration_date':'2026-10-30'},decisions=[{'item_id':i['item_id'],'status':'PASS'} for i in w['items']])
    result=verify_signed_cbio_outcome_bindings(p,f,w)
    assert {(b['subject_type'],b['binding_status']) for b in result['records']['episode_binding']}=={('CLINICAL_OUTCOME','VERIFIED'),('TREATMENT_EXPOSURE','VERIFIED')}
    assert len(result['records']['episode_binding'])==4
    assert result['records']['treatment_exposure'][1]['pharmacological_class']=='ANTI_PD_1_PLUS_ANTI_CTLA_4'
    next(x for x in w['decisions'] if x['item_id']=='V5')['status']='BLOCKED_UNKNOWN'
    assert not verify_signed_cbio_outcome_bindings(p,f,w)['records']['episode_binding']


def test_signed_cbio_development_and_exposure_require_signed_gates():
    from tools.a_dav.admit import materialize_signed_cbio_development
    from tools.a_dav.worksheet import build_worksheet
    p={'classification':'SYNTHETIC_ONLY','branch_id':'A_BASELINE_BIO','records':{'study_registry':[{'study_id':'s'}],
        'publication_family':[{'publication_family_id':'f'}],'patient_registry':[{'patient_uid':'p'}],
        'specimen_registry':[{'specimen_uid':'sp','timing_raw_text':'Pre'}],
        'assay_registry':[{'specimen_uid':'sp','assay_uid':'a','source_object_id':'obj','branch_suitability':[]}],'episode_binding':[]},
        'config':{'assays':{'matrices':[{'source_object_id':'obj','feature_scope':'COMPLETE_WITH_DOCUMENTED_EXCLUSIONS','lane':'CONTINUOUS','headers':[],'values':[]}]}}}
    f={'cohort':'synthetic','cancer_type':'invented cancer','cbio_ingest':{'patient_role':'source'},'source_objects':{'source':{'locator':'https://example.org/source'}},'decision_config':{'cancer_evidence':{'source_role':'source'},'preview':{'split_policy':'DEVELOPMENT'},
       'prior_ici_policy':{'value':'UNKNOWN_ALLOWED_DEVELOPMENT'},'exposure':{'state':'METADATA_ONLY','evidence':'synthetic decision'}}}
    w=build_worksheet(p);w.update(review_status='SIGNED',signature={'reviewer_name':'invented','review_date':'2026-10-30','source_reviewer_name':'invented','source_review_date':'2026-10-30','integrator_name':'invented','integration_date':'2026-10-30'},decisions=[{'item_id':i['item_id'],'status':'PASS'} for i in w['items']])
    result=materialize_signed_cbio_development(p,f,w)
    assert result['config']['split']['policy']['permanent_role']=='DEVELOPMENT'
    assert result['config']['exposure']['review_complete'] is True
    assert result['records']['patient_registry'][0]['cancer']=='invented cancer'
    assert 'BASELINE_DE' in result['records']['assay_registry'][0]['branch_suitability']
    next(d for d in w['decisions'] if d['item_id']=='V7')['status']='BLOCKED_UNKNOWN'
    assert 'split' not in materialize_signed_cbio_development(p,f,w)['config']


def test_signed_cbio_endpoint_evaluability_is_per_outcome():
    from tools.a_dav.admit import materialize_signed_cbio_endpoints
    from tools.a_dav.worksheet import build_worksheet
    p={'branch_id':'A_BASELINE_BIO','records':{'study_registry':[{'study_id':'s'}],'clinical_outcome':[
        {'outcome_id':'o','patient_uid':'p','raw_endpoint_label':'PR','endpoint_class':'TUMOUR_RESPONSE','canonical_category':'PR','discrepancy_status':'UNRESOLVED'},
        {'outcome_id':'b','patient_uid':'p','raw_endpoint_label':'raw','endpoint_class':'SOURCE_BINARY','canonical_category':'UNKNOWN','discrepancy_status':'UNRESOLVED'}]},
       'config':{'endpoints':{'category_map':{'PR':'PR','raw':'UNKNOWN'}}}}
    w=build_worksheet(p);w.update(review_status='SIGNED',signature={'reviewer_name':'invented','review_date':'2026-10-30','source_reviewer_name':'invented','source_review_date':'2026-10-30','integrator_name':'invented','integration_date':'2026-10-30'},decisions=[{'item_id':i['item_id'],'status':'PASS'} for i in w['items']])
    rows=materialize_signed_cbio_endpoints(p,w)['records']['clinical_outcome']
    assert [r['evaluability'] for r in rows]==['EVALUABLE','UNKNOWN']
    assert all(r['discrepancy_status']=='RESOLVED' for r in rows)


def test_signed_cbio_overlap_flags_uncertainty_without_independence():
    from tools.a_dav.admit import materialize_signed_cbio_overlap
    from tools.a_dav.worksheet import build_worksheet
    p={'branch_id':'A_BASELINE_BIO','records':{'study_registry':[{'study_id':'s'}]},'config':{}}
    f={'decision_config':{'overlap_review':{'status':'UNKNOWN','no_independence_certified':True,'evidence':'synthetic source','targets':['STUDY:other']}}}
    w=build_worksheet(p);w.update(review_status='SIGNED',signature={'reviewer_name':'invented','review_date':'2026-10-30','source_reviewer_name':'invented','source_review_date':'2026-10-30','integrator_name':'invented','integration_date':'2026-10-30'},decisions=[{'item_id':i['item_id'],'status':'PASS'} for i in w['items']])
    result=materialize_signed_cbio_overlap(p,f,w);cfg=result['config']['overlap']
    assert cfg['review_complete'] is True and cfg['independence_certified'] is False
    assert result['records']['overlap_edge'][0]['target_node_id']=='STUDY:other'
    assert result['records']['overlap_edge'][0]['implication_for_independence']=='INDEPENDENCE_BLOCKED'


def test_signed_cbio_admission_uses_declared_source_roles():
    from tools.a_dav.admit import materialize_signed_cbio_admission
    from tools.a_dav.worksheet import build_worksheet
    p={'branch_id':'A_BASELINE_BIO','records':{'study_registry':[{'study_id':'s'}]},'config':{'registries':{'source_roles':{'patient':'SOURCE:patient'}}}}
    f={'cbio_ingest':{'patient_role':'patient'},'source_objects':{'patient':{'locator':'https://example.org/source'}},'decision_config':{'preview':{'required_roles':['patient']}}}
    w=build_worksheet(p);w.update(review_status='SIGNED',signature={'reviewer_name':'invented','review_date':'2026-10-30','source_reviewer_name':'invented','source_review_date':'2026-10-30','integrator_name':'invented','integration_date':'2026-10-30'},decisions=[{'item_id':i['item_id'],'status':'PASS'} for i in w['items']])
    a=materialize_signed_cbio_admission(p,f,w)['config']['admission']
    assert a['required_source_object_ids']==['SOURCE:patient']
    assert a['branch_policies']['A_BASELINE_BIO']['endpoint']['endpoint_class']=='ORR'


def test_cbio_signed_development_excludes_declared_no_rna_patients():
    from tools.a_dav.admit import materialize_signed_cbio_development
    from tools.a_dav.worksheet import build_worksheet
    p={'classification':'SYNTHETIC_ONLY','branch_id':'A_BASELINE_BIO','records':{'study_registry':[{'study_id':'s'}],
      'publication_family':[{'publication_family_id':'f'}],'patient_registry':[{'patient_uid':'p1'},{'patient_uid':'p2'}],
      'specimen_registry':[{'specimen_uid':'s1','patient_uid':'p1','timing_raw_text':'Pre'},{'specimen_uid':'s2','patient_uid':'p2','timing_raw_text':'Pre'}],
      'assay_registry':[{'assay_uid':'a','specimen_uid':'s1','source_object_id':'m','branch_suitability':[]}], 'episode_binding':[]},'config':{}}
    f={'cohort':'invented','cbio_ingest':{},'decision_config':{'preview':{'split_policy':'DEVELOPMENT','exclude_without_assay':True},
       'prior_ici_policy':{'value':'UNKNOWN_ALLOWED_DEVELOPMENT'},'exposure':{'state':'METADATA_ONLY','evidence':'synthetic decision'}}}
    w=build_worksheet(p);w.update(review_status='SIGNED',signature={'reviewer_name':'invented','review_date':'2026-10-30','source_reviewer_name':'invented','source_review_date':'2026-10-30','integrator_name':'invented','integration_date':'2026-10-30'},decisions=[{'item_id':i['item_id'],'status':'PASS'} for i in w['items']])
    assert [x['patient_uid'] for x in materialize_signed_cbio_development(p,f,w)['records']['patient_registry']]==['p1']


def test_endpoint_priority_retains_only_surviving_outcomes():
    from tools.a_dav.admit import retain_endpoint_source_priority
    cfg={'source_priority':['o1','o2']}
    retain_endpoint_source_priority(cfg,[{'outcome_id':'o1'}])
    assert cfg['source_priority']==['o1']


def test_cbio_baseline_packet_uses_declared_roles_without_choosing_split():
    from tools.a_dav.baseline_policy import build_baseline_packet
    packet={'branch_id':'A_BASELINE_BIO','records':{'source_record':[{'source_object_id':'SOURCE:invented:sample','sha256':'a'*64,'retrieval_status':'RETRIEVED','hash_scope':'FULL_OBJECT'}],'patient_registry':[{'patient_uid':'p'}],'specimen_registry':[{'specimen_uid':'s','patient_uid':'p','canonical_timing_category':'PRE_INDEX_BASELINE','baseline_candidate_status':'YES'}],'assay_registry':[],'clinical_outcome':[{'outcome_id':'o','patient_uid':'p'}]},'config':{}}
    f={'cohort':'invented','cbio_ingest':{'response_map':{'PR':'PR'}},'source_objects':{'sample':{'sha256':'a'*64}},'decision_config':{'preview':{'required_roles':['sample'],'split_policy':'UNKNOWN'}}}
    result=build_baseline_packet(packet,field_map=f)
    assert result['config']['endpoints']['classes']==['ORR']
    assert result['records']['patient_registry'][0]['patient_uid']=='p'
    assert 'split' not in result['config']


def test_cbio_baseline_declares_two_separate_endpoint_mappings():
    from tools.a_dav.baseline_policy import build_baseline_packet
    packet={'branch_id':'A_BASELINE_BIO','records':{'source_record':[{'source_object_id':'SOURCE:invented:sample','sha256':'a'*64,'retrieval_status':'RETRIEVED','hash_scope':'FULL_OBJECT'}],
      'patient_registry':[{'patient_uid':'p'}],'specimen_registry':[{'specimen_uid':'s','patient_uid':'p','canonical_timing_category':'PRE_INDEX_BASELINE','baseline_candidate_status':'YES'}],
      'assay_registry':[],'clinical_outcome':[{'outcome_id':'o','patient_uid':'p','endpoint_class':'TUMOUR_RESPONSE','raw_endpoint_label':'PR','canonical_category':'PR'},
       {'outcome_id':'b','patient_uid':'p','endpoint_class':'SOURCE_BINARY','raw_endpoint_label':'combined-value','canonical_category':'SOURCE_POSITIVE'}]},'config':{}}
    f={'cohort':'invented','cbio_ingest':{'response_map':{'PR':'PR'}},'source_objects':{'sample':{'sha256':'a'*64}},
       'decision_config':{'preview':{'required_roles':['sample']},'author_endpoints':{'clinical_benefit':{'definition':'invented'},'evidence':'synthetic source'}}}
    cfg=build_baseline_packet(packet,field_map=f)['config']['endpoints']
    assert cfg['classes']==['ORR','OTHER']
    assert cfg['category_map']['combined-value']=='SOURCE_POSITIVE'
    assert cfg['binary_definitions']['b']['raw_value_map']['combined-value']==1


def test_cbio_declared_role_is_available_to_unsigned_preview():
    from tools.a_dav.provisional import preview_split_role
    assert preview_split_role({}, {'cbio_ingest':{},'decision_config':{'preview':{'split_policy':'DEVELOPMENT'}}})=='DEVELOPMENT'
    with pytest.raises(ValueError,match='SPLIT_NOT_FROZEN'):
        preview_split_role({}, {'cbio_ingest':{},'decision_config':{'preview':{'split_policy':'UNKNOWN'}}})


def test_final_test_family_refuses_provisional_before_source_access(tmp_path, monkeypatch):
    from tools.a_dav import admit
    from tools.a_dav.core import DavError
    f={'decision_config':{'family_protection':{'status':'UNTOUCHED_FINAL_TEST'}}}
    def forbidden(*args, **kwargs):
        raise AssertionError('source accessed')
    monkeypatch.setattr(admit,'run_ingest',forbidden)
    monkeypatch.setattr(admit,'validate_output_path',lambda path:path)
    with pytest.raises(DavError,match='UNTOUCHED_FINAL_TEST_PROTECTED'):
        admit.run_fresh_provisional('invented','A_BASELINE_BIO',tmp_path,f,tmp_path/'receipt',tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_final_test_family_refuses_signed_development_before_source_access(tmp_path, monkeypatch):
    from tools.a_dav import admit
    from tools.a_dav.core import DavError
    f={'decision_config':{'family_protection':{'status':'UNTOUCHED_FINAL_TEST'}}}
    monkeypatch.setattr(admit,'run_ingest',lambda *args,**kwargs:pytest.fail('source accessed'))
    monkeypatch.setattr(admit,'validate_output_path',lambda path:path)
    with pytest.raises(DavError,match='UNTOUCHED_FINAL_TEST_PROTECTED'):
        admit.run_fresh_signed_admission('invented','A_BASELINE_BIO',tmp_path,f,tmp_path/'receipt',{},tmp_path/'out')


def test_final_test_family_ingest_refuses_expression_outcome_join(tmp_path,monkeypatch):
    from tools.a_dav import ingest
    f={'branch_id':'A_BASELINE_BIO','decision_config':{'family_protection':{'status':'UNTOUCHED_FINAL_TEST'}}}
    monkeypatch.setattr(ingest,'load_field_map',lambda _p:f)
    with pytest.raises(ingest.IngestError,match='UNTOUCHED_FINAL_TEST_PROTECTED'):
        ingest.run_ingest('invented','A_BASELINE_BIO',tmp_path,tmp_path/'out',allow_external_out=True)
    assert not (tmp_path/'out').exists()


def test_final_test_family_refuses_direct_provisional(tmp_path):
    from tools.a_dav.provisional import run_provisional
    with pytest.raises(ValueError,match='UNTOUCHED_FINAL_TEST_PROTECTED'):
        run_provisional({}, {'decision_config':{'family_protection':{'status':'UNTOUCHED_FINAL_TEST'}}}, tmp_path, tmp_path/'out')


def test_v3_joins_patient_visit_to_matrix_axis_without_inventing_missing_samples(tmp_path):
    import hashlib
    from tools.a_dav.matrix_v3 import run_cbioportal_v3
    def obj(raw):
        sha=hashlib.sha256(raw).hexdigest();(tmp_path/'objects').mkdir(exist_ok=True);(tmp_path/'objects'/sha).write_bytes(raw);return sha
    patients=obj(b'PATIENT_ID\tVISIT\tRESPONSE\nP1\tPre\tPR\nP2\tPre\tPD\n')
    samples=obj(b'PATIENT_ID\tSAMPLE_ID\nP1\tS1\nP2\tS2\n')
    matrix=obj(b'Hugo_Symbol\tEntrez_Gene_Id\tS1\nGENE1\t1\t1\n')
    f={'source_objects':{'patients':{'sha256':patients},'samples':{'sha256':samples},'matrix':{'sha256':matrix}},'cbio_ingest':{'patient_role':'patients','sample_role':'samples','patient_id':'PATIENT_ID','sample_id':'SAMPLE_ID','visit_field':'VISIT','visit_source':'patient','baseline_values':['Pre']},'measurement_representations':{'matrix':{'unit':'TPM','transform':'NONE','platform':'invented','genome_build':'hg38','annotation':'GENE_SYMBOL','feature_identifier_system':'GENE_SYMBOL','auxiliary_columns':[{'index':1,'header':'Entrez_Gene_Id'}]}},'v3':{'primary_representation':'matrix','expected_counts':{'full_header_columns':1,'baseline_selected':1,'on_selected':0},'documentation':{'matrix':{'status':'DOCUMENTED'}},'delimiters':{'matrix':'\t'},'compressed':{'matrix':False}}}
    r=run_cbioportal_v3(tmp_path,f)['checks']['primary']
    assert r['status']=='PASS',r['reasons']
    assert r['counts']['selected_pre_columns']==1


def test_cbio_v3_excludes_duplicate_symbols_only_when_rule_declared(tmp_path):
    import hashlib
    from tools.a_dav.matrix_v3 import run_cbioportal_v3
    def obj(raw):
        sha=hashlib.sha256(raw).hexdigest();(tmp_path/'objects').mkdir(exist_ok=True);(tmp_path/'objects'/sha).write_bytes(raw);return sha
    ss=obj(b'PATIENT_ID\tSAMPLE_ID\tVISIT\nP1\tS1\tPre\n');mm=obj(b'Hugo_Symbol\tS1\nG1\t1\nG1\t2\nG2\t3\n')
    f={'source_objects':{'samples':{'sha256':ss},'matrix':{'sha256':mm}},'cbio_ingest':{'sample_role':'samples','sample_id':'SAMPLE_ID','visit_field':'VISIT','baseline_values':['Pre']},'measurement_representations':{'matrix':{'unit':'TPM','transform':'NONE','platform':'invented','genome_build':'hg38','annotation':'GENE_SYMBOL','feature_identifier_system':'GENE_SYMBOL','derived_facts':{'feature_identifier_system':{'rule':'GENE_SYMBOL_MAJORITY','source_sha256':mm}}}},'v3':{'primary_representation':'matrix','expected_counts':{'full_header_columns':1,'baseline_selected':1,'on_selected':0},'documentation':{'matrix':{'status':'DOCUMENTED'}},'delimiters':{'matrix':'\t'},'compressed':{'matrix':False}}}
    check=run_cbioportal_v3(tmp_path,f)['checks']['primary']
    assert check['status']=='PASS',check['reasons']
    evidence=check['object_derived_evidence'];assert evidence['excluded_rows_evidence']['rule']=='NONSTANDARD_ROWS_EXCLUDED'
    assert evidence['excluded_rows_evidence']['evidence_type']=='DERIVED_FROM_OBJECT'
    assert len(evidence['excluded_rows'])==2
    assert all(x['reason']=='DUPLICATE_SYMBOL' for x in evidence['excluded_rows'])


def test_corroboration_keeps_both_source_labels_by_exact_patient():
    from tools.a_dav.cbioportal import response_corroboration
    primary=[{'PATIENT_ID':'P1','BR':'PD'},{'PATIENT_ID':'P2','BR':'PR'}]
    other=[{'PATIENT_ID':'P1','RESPONSE':'SD'}]
    rows=response_corroboration(primary,other,'PATIENT_ID','BR','RESPONSE')
    assert rows==[{'patient_id':'P1','primary':'PD','corroborating':'SD'}, {'patient_id':'P2','primary':'PR','corroborating':None}]
    assert primary[0]['BR']=='PD'


def test_unmatched_or_duplicate_matrix_columns_are_never_linked():
    from tools.a_dav.cbioportal import join_samples,read_clinical
    p=read_clinical(b'PATIENT_ID\tRESPONSE\nP1\tPR\n');s=read_clinical(b'PATIENT_ID\tSAMPLE_ID\tVISIT\nP1\tS1\tPre\n')
    cfg={'patient_id':'PATIENT_ID','sample_id':'SAMPLE_ID','visit_field':'VISIT','baseline_values':['Pre'],'response_field':'RESPONSE'}
    result=join_samples(p,s,['S1','S1','UNMATCHED'],cfg)
    assert result['samples'][0]['expression_linked'] is False
    assert any(i['category']=='MATRIX_COLUMN_UNMAPPED_OR_AMBIGUOUS' for i in result['items'])


def test_ambiguous_patient_identity_never_links_expression():
    from tools.a_dav.cbioportal import join_samples,read_clinical
    p=read_clinical(b'PATIENT_ID\tRESPONSE\nP1\tPR\nP1\tPD\n');s=read_clinical(b'PATIENT_ID\tSAMPLE_ID\tVISIT\nP1\tS1\tPre\n')
    r=join_samples(p,s,['S1'],{'patient_id':'PATIENT_ID','sample_id':'SAMPLE_ID','visit_field':'VISIT','baseline_values':['Pre'],'response_field':'RESPONSE'})
    assert r['samples'][0]['expression_linked'] is False
    assert any(i['category']=='PATIENT_JOIN_UNRESOLVED' for i in r['items'])


def test_unknown_visit_is_a_review_item_and_never_promoted_to_baseline():
    from tools.a_dav.ingest import build_canonical_records
    cfg={'cohort':'invented','branch_id':'A_BASELINE_BIO','source_objects':{'p':{'locator':'https://example.org/p','format':'DELIMITED_TSV','version':'1','sha256':None},'s':{'locator':'https://example.org/s','format':'DELIMITED_TSV','version':'1','sha256':None}},'cbio_ingest':{'patient_role':'p','sample_role':'s','matrix_role':'m','patient_id':'PATIENT_ID','sample_id':'SAMPLE_ID','visit_field':'VISIT','baseline_values':['Pre'],'nonbaseline_values':['On'],'response_field':'RESPONSE','response_map':{'PR':'PR'}}}
    p=read_clinical(b'PATIENT_ID\tVISIT\tRESPONSE\nP1\tBefore-other-treatment\tPR\n');s=read_clinical(b'PATIENT_ID\tSAMPLE_ID\nP1\tS1\n');items=[]
    result=build_canonical_records({'p':p,'s':s,'m':('gene','S1')},{},cfg,items)
    assert result['specimen_registry'][0]['baseline_candidate_status']=='UNKNOWN'
    assert any(x['category']=='BASELINE_TIMING_UNRESOLVED' for x in items)


def test_missing_matrix_samples_are_summarized_as_one_review_item():
    from tools.a_dav.ingest import build_canonical_records
    cfg={'cohort':'invented','branch_id':'A_BASELINE_BIO','source_objects':{'p':{'locator':'https://example.org/p','format':'DELIMITED_TSV','version':'1','sha256':None},'s':{'locator':'https://example.org/s','format':'DELIMITED_TSV','version':'1','sha256':None}},'cbio_ingest':{'patient_role':'p','sample_role':'s','matrix_role':'m','patient_id':'PATIENT_ID','sample_id':'SAMPLE_ID','visit_field':'VISIT','baseline_values':['Pre'],'response_field':'RESPONSE','response_map':{'PR':'PR'}}}
    p=read_clinical(b'PATIENT_ID\tRESPONSE\nP1\tPR\nP2\tPR\n');s=read_clinical(b'PATIENT_ID\tSAMPLE_ID\tVISIT\nP1\tS1\tPre\nP2\tS2\tPre\n');items=[]
    build_canonical_records({'p':p,'s':s,'m':('gene','S3')},{},cfg,items)
    issues=[x for x in items if x['category']=='EXPRESSION_SAMPLE_UNMATCHED']
    assert len(issues)==1 and issues[0]['context']['sample_count']==2


def test_v3_excluded_rows_are_carried_to_unsigned_worksheet():
    from tools.a_dav.provisional import add_v3_exclusion_item
    packet={'config':{'admission':{'ingestion_worksheet':{'items':[]}}}}
    receipt={'checks':{'primary':{'object_derived_evidence':{'excluded_rows':[{'row':1,'identifier':'GENE','reason':'DUPLICATE_SYMBOL'}],'excluded_rows_evidence':{'evidence_type':'DERIVED_FROM_OBJECT','rule':'NONSTANDARD_ROWS_EXCLUDED','source_sha256':'a'*64}}}}}
    result=add_v3_exclusion_item(packet,receipt)
    item=result['config']['admission']['ingestion_worksheet']['items'][0]
    assert item['category']=='FEATURE_ROWS_EXCLUDED'
    assert item['context']['count']==1 and item['context']['excluded_rows'][0]['reason']=='DUPLICATE_SYMBOL'
    assert item['context']['evidence_type']=='DERIVED_FROM_OBJECT'
    assert packet['config']['admission']['ingestion_worksheet']['items']==[]


def test_patient_sourced_response_and_prior_keep_patient_source_locator():
    from tools.a_dav.ingest import build_canonical_records
    cfg={'cohort':'invented','branch_id':'A_BASELINE_BIO','source_objects':{'p':{'locator':'https://example.org/p','format':'DELIMITED_TSV','version':'1','sha256':None},'s':{'locator':'https://example.org/s','format':'DELIMITED_TSV','version':'1','sha256':None}},'cbio_ingest':{'patient_role':'p','sample_role':'s','matrix_role':'m','patient_id':'PATIENT_ID','sample_id':'SAMPLE_ID','visit_field':'VISIT','visit_source':'patient','baseline_values':['Pre'],'response_field':'BR','response_map':{'PR':'PR'},'prior_ici_field':'PRIOR','prior_ici_map':{'Yes':'YES'}}}
    p=read_clinical(b'PATIENT_ID\tVISIT\tBR\tPRIOR\nP1\tPre\tPR\tYes\n');s=read_clinical(b'PATIENT_ID\tSAMPLE_ID\nP1\tS1\n');r=build_canonical_records({'p':p,'s':s,'m':('gene','S1')},{},cfg,[])
    assert any(x['value']=='https://example.org/p' for x in r['clinical_outcome'][0]['source_locators'])
    assert any(x['value']=='https://example.org/p' for x in r['patient_registry'][0]['source_locators'])
    assert r['patient_registry'][0]['prior_ici']=='YES'


def test_unknown_patient_response_item_points_to_patient_field():
    from tools.a_dav.ingest import build_canonical_records
    cfg={'cohort':'invented','branch_id':'A_BASELINE_BIO','source_objects':{'p':{'locator':'https://example.org/p','format':'DELIMITED_TSV','version':'1','sha256':None},'s':{'locator':'https://example.org/s','format':'DELIMITED_TSV','version':'1','sha256':None}},'cbio_ingest':{'patient_role':'p','sample_role':'s','matrix_role':'m','patient_id':'PATIENT_ID','sample_id':'SAMPLE_ID','visit_field':'VISIT','baseline_values':['Pre'],'response_field':'BR','response_map':{}}}
    p=read_clinical(b'PATIENT_ID\tVISIT\tBR\nP1\tPre\tMixed\n');s=read_clinical(b'PATIENT_ID\tSAMPLE_ID\nP1\tS1\n');items=[];build_canonical_records({'p':p,'s':s,'m':('gene','S1')},{},cfg,items)
    item=next(i for i in items if i['category']=='ORR_RESPONSE_UNKNOWN')
    assert item['evidence_pointers']==[{'role':'p','field':'BR'}]
