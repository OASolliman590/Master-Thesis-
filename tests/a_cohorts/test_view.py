import csv
import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

from tools.a_cohorts import core
from tools.a_cohorts.view import (
    cohort_metadata,
    cohort_view,
    normalise_drug_class,
)


REGISTRY = Path(__file__).resolve().parents[2] / 'docs/cohorts/REGISTRY.tsv'
REPRESENTATION = Path(__file__).resolve().parents[2] / 'docs/cohorts/REPRESENTATION.tsv'


def _signed_cohorts():
    with REGISTRY.open(newline='') as stream:
        return [row for row in csv.DictReader(stream, delimiter='\t')
                if row['role'] == 'development' and row['status'].startswith('SIGNED')]


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_runtime(runtime, cohort, labels, *, expression_ids=None, clinical_ids=None):
    output = runtime / cohort / 'simple'
    output.mkdir(parents=True)
    clinical_ids = clinical_ids or [f'patient_{index}' for index in range(len(labels))]
    expression_ids = expression_ids or clinical_ids
    expression = output / 'expression.tsv'
    clinical = output / 'clinical.tsv'
    caveats = output / 'caveats.md'
    expression.write_text('gene\t' + '\t'.join(expression_ids) + '\nG1\t' + '\t'.join('1' for _ in expression_ids) + '\n')
    columns = ['patient_id', 'drug_class', 'orr', 'clinical_benefit', 'raw_orr', 'raw_clinical_benefit']
    if cohort_metadata(cohort).cancer == 'multi':
        columns.append('cancer')
    rows = []
    for index, (patient_id, label) in enumerate(zip(clinical_ids, labels)):
        row = {'patient_id': patient_id, 'drug_class': label, 'orr': 'PR',
               'clinical_benefit': 'UNKNOWN', 'raw_orr': 'PR', 'raw_clinical_benefit': ''}
        if 'cancer' in columns:
            row['cancer'] = ('head and neck', 'lung non-squamous')[index % 2]
        rows.append(row)
    with clinical.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, delimiter='\t', lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    caveats.write_text('synthetic fixture\n')
    manifest = {
        'cohort': cohort, 'loader_version': core.VERSION,
        'patients': len(clinical_ids), 'genes': 1, 'input_files': {},
        'output_sha256': {path.name: _sha256(path) for path in (expression, clinical, caveats)},
    }
    (output / 'manifest.json').write_text(json.dumps(manifest))
    return output, expression, clinical


def test_all_signed_cohorts_have_controlled_representation_and_metadata():
    signed = _signed_cohorts()
    with REPRESENTATION.open(newline='') as stream:
        rows = list(csv.DictReader(stream, delimiter='\t'))
    assert len(signed) == 20
    assert len(rows) == 20
    assert {row['cohort_id'] for row in rows} == {row['cohort_id'] for row in signed}
    assert 'uniform_drug_class' in rows[0]
    assert {row['cohort_id']: row['uniform_drug_class'] for row in rows if row['uniform_drug_class']} == {
        'riaz_gse91061': 'ANTI_PD_L1_AXIS',
        'hugo_gse78220': 'ANTI_PD_L1_AXIS',
    }
    for cohort in signed:
        metadata = cohort_metadata(cohort['cohort_id'])
        assert metadata.cancer in {'melanoma', 'lung', 'kidney', 'bladder', 'gastric', 'liver', 'head_and_neck', 'multi'}
        assert metadata.representation.platform in {'rnaseq', 'microarray', 'nanostring', 'targeted_rna'}
        assert metadata.representation.unit in {'counts', 'tpm', 'fpkm', 'rpkm', 'probe_intensity', 'normalised_counts', 'cpm'}
        assert metadata.representation.transform in {'linear', 'log2', 'log2p1', 'other'}
        assert metadata.representation.feature_id in {'symbol', 'ensembl', 'entrez', 'probe'}
        assert metadata.de_engine in {'deseq2', 'limma'}
        assert metadata.endpoint_families
    assert cohort_metadata('gse140901').endpoint_families == ('orr', 'clinical_benefit')
    assert cohort_metadata('gse218989').endpoint_families == ('source_label',)
    assert cohort_metadata('gse159067').endpoint_families == ('orr',)
    assert cohort_metadata('gse165278').endpoint_families == ('clinical_benefit',)


@pytest.mark.parametrize('cohort', ['imvigor210', 'gse248014'])
def test_locked_and_excluded_cohorts_have_no_view(cohort):
    with pytest.raises(ValueError, match='refused'):
        cohort_metadata(cohort)
    with pytest.raises(ValueError, match='refused'):
        cohort_view(cohort, runtime=Path('unused_runtime'))


@pytest.mark.parametrize(('raw', 'expected'), [
    ('anti-PD-1', 'ANTI_PD_L1_AXIS'),
    ('anti-PD-L1', 'ANTI_PD_L1_AXIS'),
    ('PD-1 or PD-L1 unspecified', 'ANTI_PD_L1_AXIS'),
    ('ANTI_PD_L1_AXIS', 'ANTI_PD_L1_AXIS'),
    ('ANTI_CTLA4', 'ANTI_CTLA4'),
    ('nivolumab', 'ANTI_PD_L1_AXIS'),
    ('atezolizumab', 'ANTI_PD_L1_AXIS'),
    ('NIVOLUMAB+IPILIMUMAB', 'DUAL_PD1_CTLA4'),
    ('IPILIMUMAB+NIVOLUMAB', 'DUAL_PD1_CTLA4'),
    ("{'IPILIMUMAB', 'NIVOLUMAB'}", 'DUAL_PD1_CTLA4'),
    ('nivolumab+carboplatin', 'OTHER_EXCLUDED'),
    ('ANTI_PD_1_PLUS_ANTI_TIM_3', 'OTHER_EXCLUDED'),
    ('OTHER_EXCLUDED', 'OTHER_EXCLUDED'),
])
def test_normalise_drug_class(raw, expected):
    assert normalise_drug_class(raw) == expected


@pytest.mark.parametrize('raw', ['UNKNOWN', 'ICI', 'invented checkpoint drug'])
def test_unknown_drug_labels_fail_closed(raw):
    with pytest.raises(ValueError, match='Unmapped drug class'):
        normalise_drug_class(raw)


def test_loader_drug_class_literals_have_exact_expected_classes():
    source = Path(core.__file__).read_text()
    literals = set(re.findall(
        r"['\"]((?:ANTI_[A-Z0-9_]+|NIVOLUMAB|PEMBROLIZUMAB|ATEZOLIZUMAB|DURVALUMAB|AVELUMAB|IPILIMUMAB|UNKNOWN))['\"]",
        source, re.IGNORECASE))
    expected = {
        'ANTI_CTLA4_PLUS_ANTI_PD1': 'DUAL_PD1_CTLA4',
        'ANTI_CTLA_4': 'ANTI_CTLA4',
        'ANTI_PD1': 'ANTI_PD_L1_AXIS',
        'ANTI_PD_1': 'ANTI_PD_L1_AXIS',
        'ANTI_PD_1_PD_L1': 'ANTI_PD_L1_AXIS',
        'ANTI_PD_1_PLUS_ANTI_CTLA_4': 'DUAL_PD1_CTLA4',
        'ANTI_PD_1_PLUS_ANTI_TIM_3': 'OTHER_EXCLUDED',
        'NIVOLUMAB': 'ANTI_PD_L1_AXIS',
        'Nivolumab': 'ANTI_PD_L1_AXIS',
        'UNKNOWN': None,
    }
    assert literals == set(expected)
    for raw, drug_class in expected.items():
        if drug_class is None:
            with pytest.raises(ValueError):
                normalise_drug_class(raw)
        else:
            assert normalise_drug_class(raw) == drug_class


def test_cohort_view_adds_drug_and_cancer_classes_without_changing_alignment(tmp_path, monkeypatch):
    runtime = tmp_path / '.scratch' / 'runtime'
    _, expression, _ = _write_runtime(runtime, 'gse93157', ['NIVOLUMAB', 'PEMBROLIZUMAB'])
    monkeypatch.setattr(core, 'input_files', lambda cohort: {})

    view = cohort_view('gse93157', runtime=runtime)

    assert view.expression_path == expression
    assert [row['patient_id'] for row in view.clinical_rows] == ['patient_0', 'patient_1']
    assert [row['drug_class_normalised'] for row in view.clinical_rows] == ['ANTI_PD_L1_AXIS', 'ANTI_PD_L1_AXIS']
    assert [row['cancer_normalised'] for row in view.clinical_rows] == ['head_and_neck', 'lung']
    with expression.open(newline='') as stream:
        assert next(csv.reader(stream, delimiter='\t'))[1:] == [row['patient_id'] for row in view.clinical_rows]


@pytest.mark.parametrize('raw', ['', 'UNKNOWN', 'ICI'])
def test_unknown_row_label_requires_uniform_cohort_declaration(raw, tmp_path, monkeypatch):
    runtime = tmp_path / '.scratch' / 'runtime'
    _write_runtime(runtime, 'gse93157', [raw])
    monkeypatch.setattr(core, 'input_files', lambda cohort: {})

    with pytest.raises(ValueError, match='gse93157') as error:
        cohort_view('gse93157', runtime=runtime)
    assert repr(raw) in str(error.value)
    assert 'patient_0' not in str(error.value)


def test_uniform_cohort_declaration_fills_only_unknown_labels(tmp_path, monkeypatch):
    runtime = tmp_path / '.scratch' / 'runtime'
    _write_runtime(runtime, 'riaz_gse91061', ['ICI'])
    monkeypatch.setattr(core, 'input_files', lambda cohort: {})

    view = cohort_view('riaz_gse91061', runtime=runtime)

    assert view.clinical_rows[0]['drug_class_normalised'] == 'ANTI_PD_L1_AXIS'


def test_uniform_cohort_declaration_rejects_contradictory_real_class(tmp_path, monkeypatch):
    runtime = tmp_path / '.scratch' / 'runtime'
    _write_runtime(runtime, 'riaz_gse91061', ['IPILIMUMAB'])
    monkeypatch.setattr(core, 'input_files', lambda cohort: {})

    with pytest.raises(ValueError, match="riaz_gse91061.*IPILIMUMAB.*contradicts") as error:
        cohort_view('riaz_gse91061', runtime=runtime)
    assert 'patient_0' not in str(error.value)


def test_cohort_view_rejects_corrupted_output_hash(tmp_path, monkeypatch):
    runtime = tmp_path / '.scratch' / 'runtime'
    _, expression, _ = _write_runtime(runtime, 'gse93157', ['NIVOLUMAB'])
    expression.write_text(expression.read_text() + 'G2\t2\n')
    monkeypatch.setattr(core, 'input_files', lambda cohort: {})

    with pytest.raises(ValueError, match='Output hash mismatch'):
        cohort_view('gse93157', runtime=runtime)


def test_cohort_view_rejects_expression_clinical_misalignment(tmp_path, monkeypatch):
    runtime = tmp_path / '.scratch' / 'runtime'
    _write_runtime(runtime, 'gse93157', ['NIVOLUMAB'], expression_ids=['sample_x'])
    monkeypatch.setattr(core, 'input_files', lambda cohort: {})

    with pytest.raises(ValueError, match='alignment mismatch'):
        cohort_view('gse93157', runtime=runtime)


def _run_view_cli(cohort, runtime, monkeypatch, capsys):
    monkeypatch.setenv('THESIS_RUNTIME', str(runtime))
    monkeypatch.setattr(sys, 'argv', ['a_cohorts', 'view', '--cohort', cohort])
    from tools.a_cohorts.__main__ import main
    with pytest.raises(SystemExit) as exit_info:
        main()
    return exit_info.value.code, capsys.readouterr()


def test_cli_reports_unknown_label_category_without_runtime_path(tmp_path, monkeypatch, capsys):
    runtime = tmp_path / '.scratch' / 'runtime'
    _write_runtime(runtime, 'gse93157', ['invented drug label'])
    monkeypatch.setattr(core, 'input_files', lambda cohort: {})

    code, captured = _run_view_cli('gse93157', runtime, monkeypatch, capsys)

    assert code == 1
    assert captured.err.strip() == 'gse93157: unmapped_drug_label'
    assert str(runtime) not in captured.err
    assert '/' not in captured.err


def test_cli_reports_excluded_cohort_as_refused(tmp_path, monkeypatch, capsys):
    code, captured = _run_view_cli('gse248014', tmp_path / 'runtime', monkeypatch, capsys)

    assert code == 1
    assert captured.err.strip() == 'gse248014: refused'
    assert '/' not in captured.err


def test_cli_reports_corrupted_hash_as_stale_output(tmp_path, monkeypatch, capsys):
    runtime = tmp_path / '.scratch' / 'runtime'
    _, expression, _ = _write_runtime(runtime, 'gse93157', ['NIVOLUMAB'])
    expression.write_text(expression.read_text() + 'G2\t2\n')
    monkeypatch.setattr(core, 'input_files', lambda cohort: {})

    code, captured = _run_view_cli('gse93157', runtime, monkeypatch, capsys)

    assert code == 1
    assert captured.err.strip() == 'gse93157: stale_output'
    assert str(runtime) not in captured.err
    assert '/' not in captured.err


def test_cli_reports_uniform_class_contradiction_without_runtime_path(tmp_path, monkeypatch, capsys):
    runtime = tmp_path / '.scratch' / 'runtime'
    _write_runtime(runtime, 'riaz_gse91061', ['IPILIMUMAB'])
    monkeypatch.setattr(core, 'input_files', lambda cohort: {})

    code, captured = _run_view_cli('riaz_gse91061', runtime, monkeypatch, capsys)

    assert code == 1
    assert captured.err.strip() == 'riaz_gse91061: drug_class_conflict'
    assert str(runtime) not in captured.err
    assert '/' not in captured.err
