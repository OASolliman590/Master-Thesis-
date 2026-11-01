import io
import zipfile

from tools.a_dav.ingest import build_canonical_records
from tools.a_dav.xlsx import read_numeric_xlsx


def test_named_xlsx_sheet_is_streamed_without_reading_other_sheets(tmp_path):
    import zipfile
    from tools.a_dav.xlsx import iter_xlsx_sheet
    path=tmp_path/'invented.xlsx'
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="data" sheetId="1" r:id="r1"/><sheet name="excluded" sheetId="2" r:id="r2"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r1" Target="worksheets/sheet1.xml"/><Relationship Id="r2" Target="worksheets/sheet2.xml"/></Relationships>')
        z.writestr('xl/sharedStrings.xml','<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si><t>gene</t></si><si><t>sample</t></si></sst>')
        z.writestr('xl/worksheets/sheet1.xml','<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c><c r="C1" t="s"><v>1</v></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>G1</t></is></c><c r="C2"><v>3</v></c><c r="D2" t="b"><v>1</v></c></row></sheetData></worksheet>')
        z.writestr('xl/worksheets/sheet2.xml','not a worksheet')
    assert list(iter_xlsx_sheet(path,'data'))==[['gene','','sample'],['G1','','3','TRUE']]
    assert list(iter_xlsx_sheet(path,'data',selected_columns={1,3}))==[['gene','','sample'],['G1','','3']]
    from types import SimpleNamespace
    from tools.a_dav.ingest import _parse_source
    assert _parse_source(SimpleNamespace(bytes=path.read_bytes()), {'format':'XLSX_NAMED_STREAM','sheet_name':'data','header_row':1,'table_kind':'matrix'}) == ('gene','','sample')
    from tools.a_dav.matrix_header import matrix_rows
    with matrix_rows(path,delimiter='\t',compressed=False,source_format='XLSX_NAMED_STREAM',sheet_name='data',header_row=1) as rows:
        assert next(rows)==['gene','','sample']
    from tools.a_dav.cbioportal import read_workbook_inventory
    assert read_workbook_inventory(path,'data',1,['gene','sample'])==[{'gene':'G1','sample':'3'}]


def test_v3_validates_named_streaming_xlsx(tmp_path):
    import zipfile
    from tools.a_dav.matrix_v3 import validate_v3_matrix
    path=tmp_path/'synthetic.xlsx'
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="data" sheetId="1" r:id="r1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r1" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr('xl/worksheets/sheet1.xml','<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>gene</t></is></c><c r="B1" t="inlineStr"><is><t>S1</t></is></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>G1</t></is></c><c r="B2"><v>3</v></c></row></sheetData></worksheet>')
    result=validate_v3_matrix(path,expected_sample_ids={'S1'},pre_sample_ids={'S1'},on_sample_ids=set(),selected_sample_ids={'S1'},expected_counts={'full_header_columns':1,'baseline_selected':1,'on_selected':0},annotation_feature_ids=None,annotation_evidence_status='DECLARED_ID_FORMAT_ONLY',feature_id_pattern='[A-Z0-9]+',annotation_label='synthetic',genome_build='synthetic',representation='synthetic',processing_documented=True,certification_level='format',feature_identity_limit='synthetic',source_format='XLSX_NAMED_STREAM',sheet_name='data',header_row=1)
    assert result['status']=='PASS'


def test_declared_source_review_items_apply_to_geo_ingestion():
    from tools.a_dav.ingest import _known_items
    items=[]
    _known_items({'decision_config':{'review_items':{'items':[{'category':'SPLIT_REVIEW','role':'soft','question':'Review split.'}]}}},items,{'geo_samples':0},{})
    assert [item['category'] for item in items]==['SPLIT_REVIEW']


def test_negative_values_require_declared_source_processing_evidence():
    from tools.a_dav.matrix_v3 import source_allows_negative
    d={'negative_values_allowed':True,'negative_values_source_phrase':'median centered'}
    assert source_allows_negative(d,'!Sample_data_processing = values median centered')
    assert not source_allows_negative(d,'!Sample_data_processing = counts')
    assert not source_allows_negative({'negative_values_allowed':True},'!Sample_data_processing = values median centered')


def test_field_map_accepts_source_agent_class_mapping(tmp_path):
    import json
    from tools.a_dav.field_maps import load_field_map
    f={'cohort':'synthetic','branch_id':'A_BASELINE_BIO','source_objects':{'g':{'sha256':None,'locator':'https://example.org/g','version':'1','format':'GEO_FAMILY_SOFT','role':'source_of_record'}},
       'treatment_proposal':{'agent_source':'GEO_CHARACTERISTIC','agent_field':'drug','source_locator':'https://example.org/g','regimen_id':'r','index_event':'START_OF_INDEX_TREATMENT','pharmacological_class':'ICI','agent_class_map':{'invented':'INVENTED_CLASS'}}}
    p=tmp_path/'map.json';p.write_text(json.dumps(f));assert load_field_map(p)['treatment_proposal']['agent_class_map']['invented']=='INVENTED_CLASS'


def test_geo_v3_reads_processing_evidence_without_derived_facts(tmp_path):
    import gzip,hashlib,json
    from tools.a_dav.matrix_v3 import _run_geo_primary_only
    root=tmp_path/'store'/'objects';root.mkdir(parents=True)
    soft=(b'^SAMPLE = synthetic\n!Sample_geo_accession = synthetic\n!Sample_title = P1\n'
          b'!Sample_characteristics_ch1 = visit: Pre\n!Sample_data_processing = values median centered\n')
    matrix=b'gene,P1\nG1,-1\n'
    def store(raw):
        sha=hashlib.sha256(raw).hexdigest();(root/sha).write_bytes(raw);return sha
    a,b=store(gzip.compress(soft)),store(matrix)
    f={'source_objects':{'geo_family_soft':{'sha256':a,'locator':'https://example.org/soft','version':'1','format':'GEO_FAMILY_SOFT'},'m':{'sha256':b,'locator':'https://example.org/m','version':'1','format':'MATRIX_HEADER_CSV'}},
       'geo':{'characteristics':{'visit':'visit'}},'sample_identity':{'title_regex':'^(P[0-9]+)$','patient_group':1},
       'geo_ingest':{'baseline_values':['Pre'],'baseline_tie_rule':None},'expression_column_map':{'m':{'method':'TITLE'}},
       'measurement_representations':{'m':{'unit':'UNKNOWN','transform':'UNKNOWN','platform':'UNKNOWN','genome_build':'UNKNOWN','feature_identifier_system':'UNKNOWN','negative_values_allowed':True,'negative_values_source_phrase':'median centered'}},
       'v3':{'primary_representation':'m','sample_inventory_source_role':'geo_family_soft','expected_counts':{'full_header_columns':1,'baseline_selected':1,'on_selected':0},'delimiters':{'m':','},'compressed':{'m':False},'documentation':{'m':{'status':'DOCUMENTED'}}}}
    out=tmp_path/'out';_run_geo_primary_only(tmp_path/'store',f,out)
    assert 'NEGATIVE_VALUES_PRESENT' not in json.loads((out/'receipt.json').read_text())['checks']['primary']['reasons']


def test_cbio_v3_uses_only_allowed_arm_in_named_workbook(tmp_path):
    import zipfile,hashlib
    from tools.a_dav.matrix_v3 import run_cbioportal_v3
    raw=tmp_path/'synthetic.xlsx'
    with zipfile.ZipFile(raw,'w') as z:
        z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="clinical" sheetId="1" r:id="r1"/><sheet name="expression" sheetId="2" r:id="r2"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r1" Target="worksheets/sheet1.xml"/><Relationship Id="r2" Target="worksheets/sheet2.xml"/></Relationships>')
        def sheet(rows):
            return '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'+''.join('<row r="%d">'%n+''.join('<c r="%s%d" t="inlineStr"><is><t>%s</t></is></c>'%(chr(65+i),n,v) for i,v in enumerate(row))+'</row>' for n,row in enumerate(rows,1))+'</sheetData></worksheet>'
        z.writestr('xl/worksheets/sheet1.xml',sheet([['PATIENT','SAMPLE','VISIT','ARM'],['P1','S1','Pre','ICI'],['P2','S2','Pre','OTHER']]))
        z.writestr('xl/worksheets/sheet2.xml','<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>gene</t></is></c><c r="B1" t="inlineStr"><is><t>S1</t></is></c><c r="C1" t="inlineStr"><is><t>S2</t></is></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>G1</t></is></c><c r="B2"><v>1</v></c><c r="C2"><f>1+1</f><v>2</v></c></row></sheetData></worksheet>')
    sha=hashlib.sha256(raw.read_bytes()).hexdigest();(tmp_path/'objects').mkdir();(tmp_path/'objects'/sha).write_bytes(raw.read_bytes())
    source=lambda sheet:{'sha256':sha,'format':'XLSX_NAMED_STREAM','sheet_name':sheet,'header_row':1}
    f={'source_objects':{'s':source('clinical'),'m':source('expression')},'cbio_ingest':{'sample_role':'s','sample_id':'SAMPLE','patient_id':'PATIENT','visit_field':'VISIT','baseline_values':['Pre'],'cohort_filter':{'field':'ARM','allowed_values':['ICI']}},
       'measurement_representations':{'m':{'unit':'TPM','transform':'NONE','platform':'synthetic','genome_build':'synthetic','annotation':'gene','feature_identifier_system':'GENE_SYMBOL'}},
       'v3':{'primary_representation':'m','expected_counts':{'full_header_columns':1,'baseline_selected':1,'on_selected':0},'documentation':{'m':{'status':'DOCUMENTED'}},'delimiters':{'m':'\t'},'compressed':{'m':False}}}
    result=run_cbioportal_v3(tmp_path,f)['checks']['primary']
    assert result['status']=='PASS' and result['counts']['selected_pre_columns']==1


def test_xlsx_clinical_table_supports_sparse_cells_and_strings():
    import io, zipfile
    from tools.a_dav.xlsx import read_clinical_xlsx
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as z:
        z.writestr('xl/workbook.xml', '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="s" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr('xl/sharedStrings.xml', '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si><t>Patient</t></si><si><t>Response</t></si><si><t>PR</t></si></sst>')
        z.writestr('xl/worksheets/sheet1.xml', '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="3"><c r="A3" t="s"><v>0</v></c><c r="B3" t="s"><v>1</v></c></row><row r="4"><c r="A4"><v>1</v></c><c r="B4" t="s"><v>2</v></c></row><row r="5"><c r="A5"><v>2</v></c></row></sheetData></worksheet>')
    assert read_clinical_xlsx(out.getvalue(), header_row=3) == [{'Patient': '1', 'Response': 'PR'}, {'Patient': '2', 'Response': ''}]
    from types import SimpleNamespace
    from tools.a_dav.ingest import _parse_source
    assert _parse_source(SimpleNamespace(bytes=out.getvalue()), {'format': 'XLSX_CLINICAL', 'header_row': 3}) == read_clinical_xlsx(out.getvalue(), header_row=3)


def test_geo_only_preserves_response_and_flags_duplicate_baseline():
    mapping = {
        'cohort': 'fictional', 'branch_id': 'A_BASELINE_BIO',
        'source_objects': {'geo_family_soft': {'locator': 'https://example.org/source', 'version': 'v1', 'format': 'GEO_FAMILY_SOFT', 'sha256': None}},
        'sample_identity': {'patient_characteristic': 'patient'},
        'geo': {'characteristics': {'patient': 'patient', 'visit': 'visit', 'response': 'response'}},
        'geo_ingest': {'baseline_values': ['pre'], 'response_source': 'geo_family_soft', 'endpoint_class': 'SOURCE_BINARY', 'response_map': {'R': 'SOURCE_POSITIVE', 'NR': 'SOURCE_NEGATIVE'}, 'baseline_tie_rule': None},
    }
    samples = [{'accession': 'invented-' + str(i), 'title': 'invented', 'characteristics': [{'key': 'patient', 'value': 'fictional-1'}, {'key': 'visit', 'value': 'pre'}, {'key': 'response', 'value': 'R'}]} for i in range(2)]
    items = []
    records = build_canonical_records({'geo_family_soft': samples}, {}, mapping, items)
    assert len(records['patient_registry']) == 1
    assert len(records['specimen_registry']) == 2
    assert records['clinical_outcome'][0]['endpoint_class'] == 'SOURCE_BINARY'
    assert records['clinical_outcome'][0]['canonical_category'] == 'SOURCE_POSITIVE'
    assert any(item['category'] == 'DUPLICATE_GEO_PATIENT_VISIT' for item in items)


def test_xlsx_shared_strings_and_numeric_values():
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as z:
        z.writestr('xl/workbook.xml', '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="data" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"/></Relationships>')
        z.writestr('xl/sharedStrings.xml', '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si><t>gene</t></si><si><t>sample</t></si><si><t>gene1</t></si></sst>')
        z.writestr('xl/worksheets/sheet1.xml', '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row><row r="2"><c r="A2" t="s"><v>2</v></c><c r="B2"><v>1.25</v></c></row></sheetData></worksheet>')
    assert read_numeric_xlsx(out.getvalue()) == (('gene', 'sample'), (('gene1', 1.25),))


def test_unverified_patient_title_never_produces_patient_or_outcome():
    mapping = {
        'cohort': 'fictional', 'branch_id': 'A_BASELINE_BIO',
        'source_objects': {'geo_family_soft': {'locator': 'https://example.org/source', 'version': 'v1', 'format': 'GEO_FAMILY_SOFT', 'sha256': None}},
        'sample_identity': {'title_regex': r'^(fictional-\d+)$', 'patient_group': 1},
        'geo': {'characteristics': {'visit': 'visit', 'response': 'response'}},
        'geo_ingest': {'baseline_values': ['pre'], 'response_source': 'geo_family_soft', 'endpoint_class': 'SOURCE_BINARY', 'response_map': {'R': 'SOURCE_POSITIVE'}, 'baseline_tie_rule': None, 'patient_mapping_unverified': True},
    }
    samples = [{'accession': 'invented-1', 'title': 'fictional-1', 'characteristics': [{'key': 'visit', 'value': 'pre'}, {'key': 'response', 'value': 'R'}]}]
    items = []
    records = build_canonical_records({'geo_family_soft': samples}, {}, mapping, items)
    assert records['patient_registry'] == []
    assert records['clinical_outcome'] == []
    assert items[0]['category'] == 'GEO_PATIENT_IDENTITY_UNRESOLVED'


def test_lowest_lesion_letter_selects_baseline_and_keeps_other_specimen():
    mapping = {
        'cohort': 'fictional', 'branch_id': 'A_BASELINE_BIO',
        'source_objects': {'geo_family_soft': {'locator': 'https://example.org/source', 'version': 'v1', 'format': 'GEO_FAMILY_SOFT', 'sha256': None}},
        'sample_identity': {'title_regex': r'^(P[0-9]+)([A-Z])$', 'patient_group': 1, 'lesion_group': 2},
        'geo': {'characteristics': {'patient': 'patient', 'visit': 'visit', 'response': 'response'}},
        'geo_ingest': {'baseline_values': ['pre'], 'response_source': 'geo_family_soft', 'endpoint_class': 'TUMOUR_RESPONSE', 'response_map': {'CR': 'CR'}, 'baseline_tie_rule': 'LOWEST_LESION_LETTER'},
    }
    samples = [{'accession': 'invented-' + letter, 'title': 'P999' + letter, 'characteristics': [{'key': 'patient', 'value': 'P999'}, {'key': 'visit', 'value': 'pre'}, {'key': 'response', 'value': 'CR'}]} for letter in ('B', 'A')]
    result = build_canonical_records({'geo_family_soft': samples}, {}, mapping, [])
    assert len(result['patient_registry']) == 1
    statuses = {row['raw_sample_aliases'][0]: row['baseline_candidate_status'] for row in result['specimen_registry']}
    assert statuses == {'invented-A': 'YES', 'invented-B': 'NO'}


def test_outcome_blind_resolved_lesion_tie_does_not_leave_duplicate_question():
    mapping = {'cohort': 'fictional', 'branch_id': 'A_BASELINE_BIO',
        'source_objects': {'geo_family_soft': {'locator': 'https://example.org/source', 'version': 'v1', 'format': 'GEO_FAMILY_SOFT', 'sha256': None}},
        'sample_identity': {'title_regex': r'^(P[0-9]+)([A-Z])$', 'patient_group': 1, 'lesion_group': 2},
        'geo': {'characteristics': {'patient': 'patient', 'visit': 'visit', 'response': 'response'}},
        'geo_ingest': {'baseline_values': ['pre'], 'response_source': 'geo_family_soft', 'endpoint_class': 'TUMOUR_RESPONSE', 'response_map': {'CR': 'CR'}, 'baseline_tie_rule': 'LOWEST_LESION_LETTER'}}
    samples = [{'accession': 'invented-' + letter, 'title': 'P999' + letter, 'characteristics': [{'key': 'patient', 'value': 'P999'}, {'key': 'visit', 'value': 'pre'}, {'key': 'response', 'value': 'CR'}]} for letter in ('B', 'A')]
    items = []
    build_canonical_records({'geo_family_soft': samples}, {}, mapping, items)
    assert not any(item['category'] == 'DUPLICATE_GEO_PATIENT_VISIT' for item in items)


def test_missing_lesion_letters_leave_baseline_selection_unknown():
    mapping = {'cohort': 'fictional', 'branch_id': 'A_BASELINE_BIO',
        'source_objects': {'geo_family_soft': {'locator': 'https://example.org/source', 'version': 'v1', 'format': 'GEO_FAMILY_SOFT', 'sha256': None}},
        'sample_identity': {'title_regex': r'^(P[0-9]+)([A-Z]?)$', 'patient_group': 1, 'lesion_group': 2},
        'geo': {'characteristics': {'patient': 'patient', 'visit': 'visit', 'response': 'response'}},
        'geo_ingest': {'baseline_values': ['pre'], 'response_source': 'geo_family_soft', 'endpoint_class': 'TUMOUR_RESPONSE', 'response_map': {'CR': 'CR'}, 'baseline_tie_rule': 'LOWEST_LESION_LETTER'}}
    samples = [{'accession': 'invented-' + str(i), 'title': 'P999', 'characteristics': [{'key': 'patient', 'value': 'P999'}, {'key': 'visit', 'value': 'pre'}, {'key': 'response', 'value': 'CR'}]} for i in range(2)]
    items = []
    result = build_canonical_records({'geo_family_soft': samples}, {}, mapping, items)
    assert {row['baseline_candidate_status'] for row in result['specimen_registry']} == {'UNKNOWN'}
    assert any(item['category'] == 'BASELINE_LESION_TIE_UNRESOLVED' for item in items)


def test_geo_tissue_characteristic_supplies_declared_compartment():
    mapping = {'cohort': 'fictional', 'branch_id': 'A_BASELINE_BIO',
        'source_objects': {'geo_family_soft': {'locator': 'https://example.org/source', 'version': 'v1', 'format': 'GEO_FAMILY_SOFT', 'sha256': None}},
        'sample_identity': {'patient_characteristic': 'patient'},
        'geo': {'characteristics': {'patient': 'patient', 'visit': 'visit', 'response': 'response'}},
        'biological_compartment': {'source_name_field': 'tissue', 'source_name_map': {'biopsy': 'TUMOUR'}},
        'geo_ingest': {'baseline_values': ['pre'], 'response_source': 'geo_family_soft', 'endpoint_class': 'TUMOUR_RESPONSE', 'response_map': {'CR': 'CR'}, 'baseline_tie_rule': None}}
    sample = {'accession': 'invented-1', 'title': 'invented', 'characteristics': [{'key': 'patient', 'value': 'invented-1'}, {'key': 'visit', 'value': 'pre'}, {'key': 'response', 'value': 'CR'}, {'key': 'tissue', 'value': 'biopsy'}]}
    result = build_canonical_records({'geo_family_soft': [sample]}, {}, mapping, [])
    assert result['specimen_registry'][0]['biological_compartment'] == 'TUMOUR'


def test_geo_parser_can_restrict_characteristics_to_outcome_blind_inventory():
    from tools.a_dav.geo_soft import parse_geo_family_soft
    soft = (b'^SAMPLE = invented-1\n!Sample_geo_accession = invented-1\n!Sample_title = invented-title\n'
            b'!Sample_characteristics_ch1 = visit: pre\n!Sample_characteristics_ch1 = endpoint: invented\n')
    samples = parse_geo_family_soft(soft, characteristic_keys={'visit'})
    assert samples[0]['characteristics'] == [{'key': 'visit', 'value': 'pre'}]


def test_geo_treatment_proposals_keep_source_agent_and_unknown_index_timing():
    mapping = {'cohort': 'fictional', 'branch_id': 'A_BASELINE_BIO',
        'source_objects': {'geo_family_soft': {'locator': 'https://example.org/source', 'version': 'v1', 'format': 'GEO_FAMILY_SOFT', 'sha256': None}},
        'sample_identity': {'patient_characteristic': 'patient'},
        'geo': {'characteristics': {'patient': 'patient', 'visit': 'visit', 'response': 'response'}},
        'treatment_proposal': {'agent_source': 'GEO_CHARACTERISTIC', 'agent_field': 'treatment', 'source_locator': 'https://example.org/source', 'regimen_id': 'REGIMEN:fictional:INDEX', 'index_event': 'START_OF_INDEX_TREATMENT', 'pharmacological_class': 'ICI'},
        'geo_ingest': {'baseline_values': ['pre'], 'response_source': 'geo_family_soft', 'endpoint_class': 'TUMOUR_RESPONSE', 'response_map': {'CR': 'CR'}, 'baseline_tie_rule': None}}
    sample = {'accession': 'invented-1', 'title': 'invented', 'characteristics': [{'key': 'patient', 'value': 'invented-1'}, {'key': 'visit', 'value': 'pre'}, {'key': 'response', 'value': 'CR'}, {'key': 'treatment', 'value': 'invented-drug'}]}
    result = build_canonical_records({'geo_family_soft': [sample]}, {}, mapping, [])
    episode, exposure = result['treatment_episode'][0], result['treatment_exposure'][0]
    assert episode['index_event'] == 'START_OF_INDEX_TREATMENT'
    assert episode['timing_precision'] == 'UNKNOWN' and episode['episode_status'] == 'BLOCKED_UNKNOWN'
    assert exposure['agent'] == 'invented-drug' and exposure['prior_ici'] == 'UNKNOWN'
    assert exposure['certainty'] == 'UNRESOLVED'
    mapping['treatment_proposal']['agent_class_map']={'invented-drug':'INVENTED_CLASS'}
    classified=build_canonical_records({'geo_family_soft':[sample]}, {}, mapping, [])
    assert classified['treatment_exposure'][0]['pharmacological_class']=='INVENTED_CLASS'
    from tools.a_dav.core import SchemaStore
    SchemaStore().validate('treatment_episode', episode)
    SchemaStore().validate('treatment_exposure', exposure)


def test_treatment_class_does_not_invent_a_specific_drug():
    mapping = {'cohort': 'fictional', 'branch_id': 'A_BASELINE_BIO',
        'source_objects': {'geo_family_soft': {'locator': 'https://example.org/source', 'version': 'v1', 'format': 'GEO_FAMILY_SOFT', 'sha256': None}},
        'sample_identity': {'patient_characteristic': 'patient'}, 'geo': {'characteristics': {'patient': 'patient', 'visit': 'visit', 'response': 'response'}},
        'treatment_proposal': {'agent_source': 'GEO_CHARACTERISTIC', 'agent_field': 'antibody', 'agent_interpretation': 'CLASS', 'source_locator': 'https://example.org/source', 'regimen_id': 'REGIMEN:fictional:INDEX', 'index_event': 'START_OF_INDEX_TREATMENT', 'pharmacological_class': 'ICI'},
        'geo_ingest': {'baseline_values': ['pre'], 'response_source': 'geo_family_soft', 'endpoint_class': 'TUMOUR_RESPONSE', 'response_map': {'CR': 'CR'}, 'baseline_tie_rule': None}}
    sample = {'accession': 'invented-1', 'title': 'invented', 'characteristics': [{'key': 'patient', 'value': 'invented-1'}, {'key': 'visit', 'value': 'pre'}, {'key': 'response', 'value': 'CR'}, {'key': 'antibody', 'value': 'anti-invented'}]}
    items = []
    result = build_canonical_records({'geo_family_soft': [sample]}, {}, mapping, items)
    assert any(item['category'] == 'TREATMENT_DRUG_IDENTITY_UNKNOWN' for item in items)
    exposure = result['treatment_exposure'][0]
    assert exposure['agent'] == 'UNKNOWN'
    assert exposure['pharmacological_class'] == 'anti-invented'
