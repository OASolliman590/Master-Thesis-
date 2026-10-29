import io
import zipfile

from tools.a_dav.ingest import build_canonical_records
from tools.a_dav.xlsx import read_numeric_xlsx


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
