import gzip
import zipfile

import pytest

from tools.a_cohorts import core


def test_locked_and_combination_cohorts_refused():
    for cohort in ('imvigor210', 'gse248014'):
        with pytest.raises(ValueError, match='refused'):
            core.check_allowed(cohort)


def test_unknown_is_not_nonresponse():
    assert core.orr_category('unknown') == 'UNKNOWN'
    assert core.benefit_category('unknown') == 'UNKNOWN'


def test_endpoint_types_remain_separate():
    result = core.endpoints('PR', 'NR')
    assert result['orr'] == 'PR'
    assert result['clinical_benefit'] == 'NR'


def test_recount3_read_count_conversion():
    assert core.recount_count(1050, 100) == 10
    assert core.recount_count(1150, 100) == 12
    with pytest.raises(ValueError):
        core.recount_count(1, 0)


def test_matrix_selection_preserves_duplicate_features(tmp_path):
    source = tmp_path / 'in.tsv'
    source.write_text('gene\ts1\ts2\ng1\t1\t2\ng2\t3\t4\ng2\t5\t6\n')
    target = tmp_path / 'out.tsv'
    genes, duplicates = core.project_matrix(source, target, {'s2': 'p2'}, {'format': 'MATRIX_HEADER_TSV'}, orientation='samples_as_columns')
    assert (genes, duplicates) == (3, 1)
    assert target.read_text() == 'gene\tp2\ng1\t2\ng2\t4\ng2\t6\n'


def test_compressed_tsv_matrix_source(tmp_path):
    source = tmp_path / 'in.tsv.gz'
    with gzip.open(source, 'wt', encoding='utf-8') as stream:
        stream.write('gene\ts1\ts2\ng1\t1\t2\n')
    target = tmp_path / 'out.tsv'
    genes, duplicates = core.project_matrix(
        source, target, {'s2': 'p2'},
        {'format': 'MATRIX_HEADER_TSV', 'delimiter': '\t', 'compressed': True})
    assert (genes, duplicates) == (1, 0)
    assert target.read_text() == 'gene\tp2\ng1\t2\n'


def test_named_xlsx_matrix_source(tmp_path):
    source = tmp_path / 'in.xlsx'
    files = {
        'xl/workbook.xml': '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Sheet 1" sheetId="1" r:id="rId1"/></sheets></workbook>',
        'xl/_rels/workbook.xml.rels': '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"/></Relationships>',
        'xl/worksheets/sheet1.xml': '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Gene</t></is></c><c r="B1" t="inlineStr"><is><t>s1</t></is></c><c r="C1" t="inlineStr"><is><t>s2</t></is></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>g1</t></is></c><c r="B2"><v>1</v></c><c r="C2"><v>2</v></c></row></sheetData></worksheet>',
    }
    with zipfile.ZipFile(source, 'w') as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    target = tmp_path / 'out.tsv'
    genes, duplicates = core.project_matrix(
        source, target, {'s2': 'p2'},
        {'format': 'XLSX_NAMED_STREAM', 'sheet_name': 'Sheet 1', 'header_row': 1})
    assert (genes, duplicates) == (1, 0)
    assert target.read_text() == 'gene\tp2\ng1\t2\n'


def test_non_numeric_expression_is_refused(tmp_path):
    source = tmp_path / 'in.tsv'
    source.write_text('gene\ts1\ng1\tbad\n')
    with pytest.raises(ValueError, match='numeric'):
        core.project_matrix(source, tmp_path / 'out.tsv', {'s1': 'p1'}, {'format': 'MATRIX_HEADER_TSV'})


def test_multiple_samples_are_not_selected_arbitrarily():
    records = {'specimen_registry': [{'specimen_uid': 'a', 'patient_uid': 'p'}, {'specimen_uid': 'b', 'patient_uid': 'p'}],
               'assay_registry': [{'source_object_id': 'SOURCE:x:expression', 'specimen_uid': 'a', 'matrix_header': 'a'},
                                  {'source_object_id': 'SOURCE:x:expression', 'specimen_uid': 'b', 'matrix_header': 'b'}]}
    mapping, dropped = core.select_unique_assays(records, 'SOURCE:x:expression')
    assert mapping == {}
    assert dropped == 1


def test_tumour_response_endpoint_maps_without_merging_benefit():
    assert core.source_outcomes([{'endpoint_class': 'TUMOUR_RESPONSE', 'raw_endpoint_label': 'PR'}, {'endpoint_class': 'SOURCE_BINARY', 'raw_endpoint_label': 'NR'}]) == ('PR', 'NR')


def test_survival_months_are_preserved_and_missing_is_unknown():
    assert core.survival_fields({'PFS_MONTHS': '4.5', 'OS_MONTHS': ''}) == {'pfs': '4.5 months', 'os': 'UNKNOWN'}

@pytest.mark.parametrize('text,mapping', [
    ('gene\ts1\ts1\ng1\t1\t2\n', {'s1': 'p1'}),
    ('gene\ts1\ts2\ng1\t1\t2\n', {'s1': 'p1', 's2': 'p1'}),
    ('gene\ts1\ng1\t\n', {'s1': 'p1'}),
    ('gene\ts1\n\t1\n', {'s1': 'p1'}),
    ('gene\ts1\ng1\n', {'s1': 'p1'}),
])
def test_invalid_expression_rejected(tmp_path, text, mapping):
    source = tmp_path / 'in.tsv'
    source.write_text(text)
    with pytest.raises(ValueError):
        core.project_matrix(source, tmp_path / 'out.tsv', mapping, {'format': 'MATRIX_HEADER_TSV'})


def test_conflicting_outcomes_are_not_last_write_wins():
    outcomes = [{'endpoint_class': 'ORR', 'raw_endpoint_label': 'PR'},
                {'endpoint_class': 'ORR', 'raw_endpoint_label': 'PD'}]
    with pytest.raises(ValueError, match='conflict'):
        core.source_outcomes(outcomes)



def test_load_is_atomic_reuses_identical_and_preserves_stale(tmp_path, monkeypatch):
    monkeypatch.setattr(core, 'ROOT', tmp_path)
    monkeypatch.setattr(core, 'RUNTIME', tmp_path / 'runtime')
    monkeypatch.setattr(core, 'check_allowed', lambda cohort: {'caveats': 'Test caveat'})
    monkeypatch.setattr(core, 'input_files', lambda cohort: {'source': 'hash'})
    monkeypatch.setitem(core.ADMITTED, 'fixture', 'admitted')
    monkeypatch.setattr(core, 'SUPPORTED_COHORTS', {'fixture'})
    def export(cohort, stage, row):
        (stage / 'expression.tsv').write_text('gene\tp1\ng1\t1\n')
        return ([{'patient_id': 'p1', 'orr': 'UNKNOWN', 'clinical_benefit': 'UNKNOWN'}], 1, ['hash'], [])
    monkeypatch.setattr(core, 'export_admitted', export)
    first = core.load('fixture')
    assert core.load('fixture') == first
    output = core.RUNTIME / 'fixture' / 'simple'
    (output / 'clinical.tsv').write_text('user data')
    with pytest.raises(ValueError, match='stale or invalid'):
        core.load('fixture')
    assert (output / 'clinical.tsv').read_text() == 'user data'
    assert not list((core.RUNTIME / 'fixture').glob('.simple-*'))


def test_failure_does_not_publish_partial_output(tmp_path, monkeypatch):
    monkeypatch.setattr(core, 'ROOT', tmp_path)
    monkeypatch.setattr(core, 'RUNTIME', tmp_path / 'runtime')
    monkeypatch.setattr(core, 'check_allowed', lambda cohort: {'caveats': 'Test'})
    monkeypatch.setattr(core, 'input_files', lambda cohort: {})
    monkeypatch.setitem(core.ADMITTED, 'fixture', 'admitted')
    monkeypatch.setattr(core, 'SUPPORTED_COHORTS', {'fixture'})
    def fail(cohort, stage, row):
        (stage / 'expression.tsv').write_text('partial')
        raise ValueError('bad source')
    monkeypatch.setattr(core, 'export_admitted', fail)
    with pytest.raises(ValueError, match='bad source'):
        core.load('fixture')
    assert not (core.RUNTIME / 'fixture' / 'simple').exists()
    assert not list((core.RUNTIME / 'fixture').glob('.simple-*'))


def test_admitted_product_bundle_digest_detects_tampering(tmp_path, monkeypatch):
    import json
    from tools.a_dav.core import digest
    monkeypatch.setattr(core, 'ROOT', tmp_path)
    monkeypatch.setattr(core, 'RUNTIME', tmp_path / 'runtime')
    monkeypatch.setitem(core.ADMITTED, 'fixture', 'admitted')
    base = core.RUNTIME / 'fixture' / 'admitted'
    products = base / 'products'
    products.mkdir(parents=True)
    expression = products / 'expression.tsv'
    patients = products / 'patients.tsv'
    expression.write_text('gene\tp1\ng1\t1\n')
    patients.write_text('patient_uid\tinclusion_status\tassay_uid\tspecimen_uid\traw_response\tcanonical_category\tprior_ici\np1\tINCLUDED\ta1\ts1\tPR\tPR\tUNKNOWN\n')
    expected = digest({'expression': core.sha256(expression), 'patients': core.sha256(patients)})
    (products / 'matrix_build_receipt.json').write_text(json.dumps({'output_hash': expected, 'input_hashes': []}))
    packet = base / 'fresh-ingest/records/ingestion_packet.json'
    packet.parent.mkdir(parents=True)
    packet.write_text(json.dumps({'records': {'assay_registry': [{'assay_uid': 'a1', 'source_sample_id': 's1'}]}}))
    clinical, genes, _, _ = core.export_admitted('fixture', tmp_path / 'out', {})
    assert len(clinical) == genes == 1
    original = patients.read_text()
    patients.write_text(original.replace('PR', 'PD'))
    with pytest.raises(ValueError, match='hash mismatch'):
        core.export_admitted('fixture', tmp_path / 'out2', {})
    patients.write_text(original)
    expression.write_text(expression.read_text().replace('\t1\n', '\t2\n'))
    with pytest.raises(ValueError, match='hash mismatch'):
        core.export_admitted('fixture', tmp_path / 'out3', {})


def test_crosswalk_requires_unique_run_and_patient():
    rows = [
        {'run': 'r1', 'patient': 'p1', 'timepoint': 'PRE'},
        {'run': 'r2', 'patient': 'p2', 'timepoint': 'PRE'},
        {'run': 'r3', 'patient': 'p2', 'timepoint': 'PRE'},
        {'run': 'r4', 'patient': '', 'timepoint': 'PRE'},
    ]
    assert core.one_to_one_pre_crosswalk(rows) == {'r1': 'p1'}


def test_survival_values_preserve_units_and_unknowns():
    assert core.survival_from_source({'pfs': '12.5', 'os': ''}, 'days') == {'pfs': '12.5 days', 'os': 'UNKNOWN'}


def test_panel_survival_keeps_progression_and_overall_separate():
    result = core.panel_survival('recurrence:1, progression-free-survival_days:120, dead, overall-survival_days:400')
    assert result == {'pfs': '120 days', 'os': '400 days'}
