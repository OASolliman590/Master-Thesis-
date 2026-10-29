import pytest

from tools.a_dav.delimited import DelimitedTable
from tools.a_dav.ingest import build_canonical_records, _parse_source
from tools.a_dav.source_objects import SourceObject


def source():
    return SourceObject('a' * 64, 'https://example.org/matrix', 'v1', 0, '2020-01-01', b'')


def fixture(rule, headers, *, crosswalk=None, visit="pre"):
    field_map = {
        'cohort': 'invented', 'branch_id': 'A_BASELINE_BIO',
        'source_objects': {'geo_family_soft': {'locator': 'https://example.org/soft', 'version': 'v1', 'format': 'GEO_FAMILY_SOFT', 'sha256': None},
                           'expression': {'locator': 'https://example.org/matrix', 'version': 'v1', 'format': 'MATRIX_HEADER_CSV', 'sha256': 'a' * 64}},
        'sample_identity': {'patient_characteristic': 'patient'},
        'geo': {'characteristics': {'patient': 'patient', 'visit': 'visit', 'response': 'response'}},
        'geo_ingest': {'baseline_values': ['pre'], 'response_source': 'geo_family_soft', 'endpoint_class': 'TUMOUR_RESPONSE', 'response_map': {'CR': 'CR'}, 'baseline_tie_rule': None},
        'measurement_representations': {'expression': {'unit': 'invented'}},
        'expression_column_map': {'expression': rule},
    }
    if crosswalk is not None:
        field_map['source_objects']['crosswalk'] = {'locator': 'https://example.org/crosswalk', 'version': 'v1', 'format': 'DELIMITED_CSV', 'sha256': 'a' * 64}
    samples = [{'accession': 'fake-accession', 'title': 'sample-one', 'characteristics': [{'key': 'patient', 'value': 'patient-one'}, {'key': 'visit', 'value': visit}, {'key': 'response', 'value': 'CR'}]}]
    parsed = {'geo_family_soft': samples, 'expression': tuple(headers)}
    sources = {'expression': source()}
    if crosswalk is not None:
        parsed['crosswalk'] = crosswalk
        sources['crosswalk'] = source()
    items = []
    result = build_canonical_records(parsed, sources, field_map, items)
    return result['assay_registry'], items


@pytest.mark.parametrize(('rule', 'header'), [
    ({'method': 'TITLE'}, 'sample-one'),
    ({'method': 'ACCESSION'}, 'fake-accession'),
    ({'method': 'REGEX', 'header_regex': r'^(?P<sample>.+)\.bam$', 'title_regex': r'^(?P<sample>.+)$'}, 'sample-one.bam'),
])
def test_declared_header_rule_links_the_sample(rule, header):
    assays, _ = fixture(rule, ['gene', header])
    assert len(assays) == 1
    assert assays[0]['matrix_header'] == header


def test_pinned_crosswalk_joins_column_to_geo_title():
    rule = {'method': 'CROSSWALK', 'source_role': 'crosswalk', 'matrix_column': 'matrix', 'geo_column': 'geo', 'geo_key': 'title'}
    assays, _ = fixture(rule, ['gene', 'file-one'], crosswalk=DelimitedTable(('matrix', 'geo'), (('file-one', 'sample-one'),)))
    assert [row['matrix_header'] for row in assays] == ['file-one']


def test_duplicate_crosswalk_never_links_ambiguous_column():
    rule = {'method': 'CROSSWALK', 'source_role': 'crosswalk', 'matrix_column': 'matrix', 'geo_column': 'geo', 'geo_key': 'title'}
    assays, items = fixture(rule, ['gene', 'file-one'], crosswalk=DelimitedTable(('matrix', 'geo'), (('file-one', 'sample-one'), ('file-one', 'other'))))
    assert assays == []
    assert any(row['category'] == 'EXPRESSION_BINDING_AMBIGUOUS' for row in items)


def test_missing_header_binding_is_reported():
    assays, items = fixture({'method': 'TITLE'}, ['gene', 'different'])
    assert assays == []
    assert any(row['category'] == 'EXPRESSION_BINDING_UNRESOLVED' for row in items)


def test_declared_non_sample_columns_allow_empty_header_cell():
    s = SourceObject('a' * 64, 'https://example.org/matrix', 'v1', 0, '2020-01-01', b'gene,sample-one,,gene\n')
    assert _parse_source(s, {'format': 'MATRIX_HEADER_CSV', 'header_allow_empty': True}) == ('gene', 'sample-one', '', 'gene')


def test_proposed_regex_rule_requires_review_even_when_unique():
    rule = {'method': 'REGEX', 'header_regex': r'^(?P<sample>.+)\.bam$', 'title_regex': r'^(?P<sample>.+)$', 'review_required': True}
    assays, items = fixture(rule, ['gene', 'sample-one.bam'])
    assert len(assays) == 1
    assert any(row['category'] == 'EXPRESSION_BINDING_RULE_REVIEW_REQUIRED' for row in items)


def test_assay_source_sample_id_is_specimen_alias():
    rule = {'method': 'REGEX', 'header_regex': r'^(?P<sample>.+)\.bam$', 'title_regex': r'^(?P<sample>.+)$'}
    assays, _ = fixture(rule, ['gene', 'sample-one.bam'])
    assert assays[0]['source_sample_id'] == 'fake-accession'
    assert assays[0]['matrix_header'] == 'sample-one.bam'


def test_patient_source_identifier_with_spaces_has_valid_stable_uid():
    import re
    m = {'cohort': 'invented', 'branch_id': 'A_BASELINE_BIO',
         'source_objects': {'geo_family_soft': {'locator': 'https://example.org/soft', 'version': 'v1', 'format': 'GEO_FAMILY_SOFT', 'sha256': None}},
         'sample_identity': {'patient_characteristic': 'patient'}, 'geo': {'characteristics': {'patient': 'patient', 'visit': 'visit', 'response': 'response'}},
         'geo_ingest': {'baseline_values': ['pre'], 'response_source': 'geo_family_soft', 'endpoint_class': 'TUMOUR_RESPONSE', 'response_map': {'CR': 'CR'}, 'baseline_tie_rule': None}}
    sample = {'accession': 'fake-accession', 'title': 'sample-one', 'characteristics': [{'key': 'patient', 'value': 'person 1'}, {'key': 'visit', 'value': 'pre'}, {'key': 'response', 'value': 'CR'}]}
    records = build_canonical_records({'geo_family_soft': [sample]}, {}, m, [])
    uid = records['patient_registry'][0]['patient_uid']
    assert re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]*', uid)
    assert records['specimen_registry'][0]['patient_uid'] == uid
    assert records['patient_registry'][0]['source_patient_id'] == 'person 1'


def test_row_oriented_matrix_exposes_sample_axis_for_geo_binding():
    import gzip
    data = gzip.compress(b'feature,gene-one,gene-two\nsample-one,1,2\n')
    obj = SourceObject('a' * 64, 'https://example.org/matrix', 'v1', len(data), '2020-01-01', data)
    assert _parse_source(obj, {'format': 'MATRIX_HEADER_CSV', 'orientation': 'samples_as_rows'}) == ('sample-one',)


def test_nonbaseline_unmatched_is_not_applicable_when_declared():
    rule = {'method': 'TITLE', 'nonbaseline_unmatched': 'NOT_APPLICABLE'}
    assays, items = fixture(rule, ['gene', 'different'], visit='on')
    assert assays == []
    assert not any(item['category'] == 'EXPRESSION_BINDING_UNRESOLVED' for item in items)


def test_expression_mapping_requires_header_visit_agree_with_geo():
    rule = {'method': 'REGEX', 'header_regex': r'^(?P<sample>.+)\.(?P<time>baseline|OnTx)$',
            'title_regex': r'^(?P<sample>.+)$',
            'characteristic_groups': {'time': {'characteristic': 'visit', 'values': {'baseline': 'pre', 'OnTx': 'on'}}}}
    assays, items = fixture(rule, ['gene', 'sample-one.OnTx'], visit='on')
    assert [row['matrix_header'] for row in assays] == ['sample-one.OnTx']
    wrong, issues = fixture(rule, ['gene', 'sample-one.OnTx'], visit='pre')
    assert wrong == []
    assert any(item['category'] == 'EXPRESSION_BINDING_UNRESOLVED' for item in issues)
