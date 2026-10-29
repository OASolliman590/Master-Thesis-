"""Invented-only expression extraction regressions."""
import csv
import hashlib
from pathlib import Path

import pytest

from tools.a_dav.expression_materialization import materialize_expression


def test_expression_materialization_preserves_features_and_excludes_unevaluable(tmp_path: Path) -> None:
    data = b'feature,assay-one,assay-two\nG001,1.0,2.0\nG002,,4.5\n'
    sha = hashlib.sha256(data).hexdigest()
    store = tmp_path / 'store' / 'objects'
    store.mkdir(parents=True)
    (store / sha).write_bytes(data)
    rows = [
        {'patient_uid': 'patient-invented-one', 'expression_column': 'assay-one', 'inclusion_status': 'INCLUDED',
         'endpoint_evaluability': 'EVALUABLE'},
        {'patient_uid': 'patient-invented-two', 'expression_column': 'assay-two', 'inclusion_status': 'EXCLUDED',
         'endpoint_evaluability': 'NOT_EVALUABLE'},
    ]
    output = tmp_path / 'expression.tsv'
    result = materialize_expression(tmp_path / 'store', sha, rows, output, delimiter=',', compressed=False, allow_external_out=True)
    assert result['gene_count'] == 2 and result['patient_count'] == 1 and result['missing_count'] == 1
    with output.open(newline='') as handle:
        assert list(csv.reader(handle, delimiter='\t')) == [
            ['feature_id', 'patient-invented-one'], ['G001', '1.0'], ['G002', '']]


def test_expression_materialization_blocks_changed_source(tmp_path: Path) -> None:
    sha = 'a' * 64
    source = tmp_path / 'store' / 'objects'
    source.mkdir(parents=True)
    (source / sha).write_text('feature,sample\nG1,1\n')
    with pytest.raises(ValueError, match='HASH_OR_VERSION_MISMATCH'):
        materialize_expression(tmp_path / 'store', sha, [], tmp_path / 'out.tsv', delimiter=',', compressed=False, allow_external_out=True)
    assert not (tmp_path / 'out.tsv').exists()


def test_expression_materialization_rejects_duplicate_features_without_leaving_output(tmp_path: Path) -> None:
    data = b'feature,assay-one\nG001,1\nG001,2\n'
    sha = hashlib.sha256(data).hexdigest()
    source = tmp_path / 'store' / 'objects'
    source.mkdir(parents=True)
    (source / sha).write_bytes(data)
    rows = [{'patient_uid': 'patient-invented-one', 'expression_column': 'assay-one',
             'inclusion_status': 'INCLUDED', 'endpoint_evaluability': 'EVALUABLE'}]
    output = tmp_path / 'out.tsv'
    with pytest.raises(ValueError, match='MATRIX_GRAIN_DUPLICATE'):
        materialize_expression(tmp_path / 'store', sha, rows, output, delimiter=',', compressed=False,
                               allow_external_out=True)
    assert not output.exists()


def test_validated_baseline_materializes_expression_after_real_stage_checks(tmp_path: Path) -> None:
    from test_group_c import STORE, material_packet, seal
    from tools.a_dav.matrices import build_baseline
    from tools.a_dav.expression_materialization import write_validated_products
    data = b'feature,A1,A2,A3,A4\nG1,1,2,3,4\nG2,5,6,7,8\n'
    sha = hashlib.sha256(data).hexdigest()
    folder = tmp_path / 'store' / 'objects'
    folder.mkdir(parents=True)
    (folder / sha).write_bytes(data)
    packet = material_packet()
    packet['records']['source_record'][0]['sha256'] = sha
    packet['records']['cohort_admission_receipt'][0]['source_object_hashes'] = [sha]
    packet = seal(packet)
    baseline = build_baseline(packet, schemas=STORE)
    assert baseline['status'] == 'READY'
    packet['records'] = baseline['records']
    packet['dependencies']['baseline'] = baseline
    result = write_validated_products(packet, tmp_path / 'store', sha, tmp_path / 'validated',
                                      delimiter=',', compressed=False, allow_external_out=True)
    assert result['counts']['gene_count'] == 2
    assert result['counts']['expression_patient_count'] == 1
    assert (tmp_path / 'validated' / 'expression.tsv').exists()
    import json
    receipt = json.loads((tmp_path / 'validated' / 'matrix_build_receipt.json').read_text())
    STORE.validate('matrix_build_receipt', receipt)
    assert receipt['patient_count'] == 1
    assert receipt['feature_coverage']['feature_count'] == 2


def test_failed_exclusive_create_never_deletes_a_competing_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data = b'feature,assay-one\nG1,1\n'
    sha = hashlib.sha256(data).hexdigest()
    store = tmp_path / 'store' / 'objects'
    store.mkdir(parents=True)
    (store / sha).write_bytes(data)
    output = tmp_path / 'out.tsv'
    original = Path.open
    def competing_open(path: Path, mode: str = 'r', *args: object, **kwargs: object):
        if path == output and mode == 'x':
            original(path, 'w').write('competing-output')
            raise FileExistsError('invented race')
        return original(path, mode, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', competing_open)
    rows = [{'patient_uid':'invented', 'expression_column':'assay-one',
             'inclusion_status':'INCLUDED', 'endpoint_evaluability':'EVALUABLE'}]
    with pytest.raises(FileExistsError):
        materialize_expression(tmp_path / 'store', sha, rows, output, delimiter=',', compressed=False,
                               allow_external_out=True)
    assert output.read_text() == 'competing-output'


def test_expression_materialization_transposes_sample_rows(tmp_path: Path) -> None:
    data = b'sample,G001,G002\nassay-one,1.0,3.0\nassay-two,2.0,4.5\n'
    sha = hashlib.sha256(data).hexdigest()
    store = tmp_path / 'store' / 'objects'
    store.mkdir(parents=True)
    (store / sha).write_bytes(data)
    rows = [{'patient_uid': 'patient-invented-one', 'expression_column': 'assay-one',
             'inclusion_status': 'INCLUDED', 'endpoint_evaluability': 'EVALUABLE'}]
    output = tmp_path / 'expression.tsv'
    result = materialize_expression(tmp_path / 'store', sha, rows, output, delimiter=',', compressed=False,
                                    orientation='samples_as_rows', allow_external_out=True)
    assert result['gene_count'] == 2 and result['patient_count'] == 1
    with output.open(newline='') as handle:
        assert list(csv.reader(handle, delimiter='\t')) == [['feature_id', 'patient-invented-one'], ['G001', '1.0'], ['G002', '3.0']]



def test_expression_extraction_from_xlsx(tmp_path: Path) -> None:
    import io
    import zipfile
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as z:
        z.writestr('xl/workbook.xml', '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="data" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr('xl/sharedStrings.xml', '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si><t>gene</t></si><si><t>assay-one</t></si><si><t>G001</t></si></sst>')
        z.writestr('xl/worksheets/sheet1.xml', '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row><row r="2"><c r="A2" t="s"><v>2</v></c><c r="B2"><v>1.25</v></c></row></sheetData></worksheet>')
    raw = stream.getvalue()
    sha = hashlib.sha256(raw).hexdigest()
    store = tmp_path / 'store' / 'objects'
    store.mkdir(parents=True)
    (store / sha).write_bytes(raw)
    rows = [{'patient_uid': 'invented-patient', 'expression_column': 'assay-one', 'inclusion_status': 'INCLUDED', 'endpoint_evaluability': 'EVALUABLE'}]
    output = tmp_path / 'expression.tsv'
    result = materialize_expression(tmp_path / 'store', sha, rows, output, delimiter=',', compressed=False,
                                    source_format='XLSX_NUMERIC', allow_external_out=True)
    assert result['gene_count'] == 1 and result['patient_count'] == 1
    assert output.read_text() == 'feature_id\tinvented-patient\nG001\t1.25\n'


def test_exclusion_policy_drops_features_with_any_source_missing_without_zero_fill(tmp_path: Path) -> None:
    data = b'feature,assay-one,assay-two\nG001,1,\nG002,0,4\n'
    sha = hashlib.sha256(data).hexdigest()
    objects = tmp_path / 'store' / 'objects'; objects.mkdir(parents=True); (objects / sha).write_bytes(data)
    rows = [{'patient_uid': 'invented-patient', 'expression_column': 'assay-one', 'inclusion_status': 'INCLUDED', 'endpoint_evaluability': 'EVALUABLE'}]
    output = tmp_path / 'expression.tsv'
    result = materialize_expression(tmp_path / 'store', sha, rows, output, delimiter=',', compressed=False,
        missing_policy='EXCLUDE_FEATURE_IF_ANY_MISSING', allow_external_out=True)
    assert output.read_text() == 'feature_id\tinvented-patient\nG002\t0\n'
    assert result['gene_count'] == 1
    assert result['excluded_missing_gene_count'] == 1


def test_missing_feature_exclusion_rejects_duplicate_auxiliary_declarations(tmp_path: Path) -> None:
    data=b'feature,assay-one,annotation\nG1,1,x\n';sha=hashlib.sha256(data).hexdigest()
    objects=tmp_path/'store'/'objects';objects.mkdir(parents=True);(objects/sha).write_bytes(data)
    rows=[{'patient_uid':'invented','expression_column':'assay-one','inclusion_status':'INCLUDED','endpoint_evaluability':'EVALUABLE'}]
    output=tmp_path/'expression.tsv'
    with pytest.raises(ValueError,match='ASSAY_UNSUPPORTED'):
        materialize_expression(tmp_path/'store',sha,rows,output,delimiter=',',compressed=False,
            missing_policy='EXCLUDE_FEATURE_IF_ANY_MISSING',auxiliary_columns=[{'index':2,'header':'annotation'},{'index':2,'header':'annotation'}],allow_external_out=True)
    assert not output.exists()


def test_missing_feature_exclusion_cannot_ignore_a_selected_sample(tmp_path: Path) -> None:
    data=b'feature,assay-one,assay-two\nG1,,2\n';sha=hashlib.sha256(data).hexdigest()
    objects=tmp_path/'store'/'objects';objects.mkdir(parents=True);(objects/sha).write_bytes(data)
    rows=[{'patient_uid':'invented','expression_column':'assay-one','inclusion_status':'INCLUDED','endpoint_evaluability':'EVALUABLE'}]
    output=tmp_path/'expression.tsv'
    with pytest.raises(ValueError,match='ASSAY_UNSUPPORTED'):
        materialize_expression(tmp_path/'store',sha,rows,output,delimiter=',',compressed=False,
            missing_policy='EXCLUDE_FEATURE_IF_ANY_MISSING',auxiliary_columns=[{'index':1,'header':'assay-one'}],allow_external_out=True)
    assert not output.exists()


def test_materialization_excludes_approved_source_rows_without_renaming(tmp_path: Path) -> None:
    data = b'feature,assay-one\nGENEA,1\nBAD_NAME,2\nGENEB,3\n'
    sha = hashlib.sha256(data).hexdigest()
    objects = tmp_path / 'store' / 'objects'; objects.mkdir(parents=True); (objects / sha).write_bytes(data)
    rows = [{'patient_uid':'invented', 'expression_column':'assay-one', 'inclusion_status':'INCLUDED', 'endpoint_evaluability':'EVALUABLE'}]
    excluded = [{'row': 2, 'identifier': 'BAD_NAME', 'reason': 'NONSTANDARD_IDENTIFIER'}]
    output = tmp_path / 'out.tsv'
    result = materialize_expression(tmp_path / 'store', sha, rows, output, delimiter=',', compressed=False,
                                   excluded_feature_rows=excluded, allow_external_out=True)
    assert output.read_text() == 'feature_id\tinvented\nGENEA\t1\nGENEB\t3\n'
    assert result['excluded_feature_row_count'] == 1


def test_validated_products_apply_receipt_feature_exclusions(tmp_path: Path) -> None:
    from test_group_c import STORE, material_packet, seal
    from tools.a_dav.matrices import build_baseline
    from tools.a_dav.expression_materialization import write_validated_products
    data=b'feature,A1,A2,A3,A4\nG1,1,2,3,4\ninvalid feature,5,6,7,8\n'
    sha=hashlib.sha256(data).hexdigest(); objects=tmp_path/'store'/'objects'; objects.mkdir(parents=True); (objects/sha).write_bytes(data)
    packet=material_packet(); packet['records']['source_record'][0]['sha256']=sha; packet['records']['cohort_admission_receipt'][0]['source_object_hashes']=[sha]
    packet=seal(packet); baseline=build_baseline(packet,schemas=STORE); packet['records']=baseline['records']; packet['dependencies']['baseline']=baseline
    result=write_validated_products(packet,tmp_path/'store',sha,tmp_path/'validated',delimiter=',',compressed=False,allow_external_out=True,excluded_feature_rows=[{'row':2,'identifier':'invalid feature','reason':'NONSTANDARD'}])
    assert result['counts']['gene_count']==1
    assert len((tmp_path/'validated'/'expression.tsv').read_text().splitlines())==2
