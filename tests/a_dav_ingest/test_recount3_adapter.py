"""Synthetic source fixtures exercise conversion and fail-closed source binding."""
import csv
import gzip
import hashlib
import json
from pathlib import Path

import pytest


def fixture(tmp_path):
    store = tmp_path / 'store'
    (store / 'objects').mkdir(parents=True)
    bodies = {
        'recount3_gene_sums_G026': '##annotation=G026\ngene_id\trun_b\trun_a\nENSG00000000001.1\t500\t500\nENSG00000000002.1\t700\t700\n',
        'recount3_qc_metadata': 'external_id\tstar.average_mapped_length\nrun_a\t100\nrun_b\t200\n',
        'recount3_sra_metadata': 'external_id\tsample_acc\tsample_name\tsample_title\tlibrary_strategy\nrun_a\tsample_a\tname_a\ttitle_a\tRNA-Seq\nrun_b\tsample_b\tname_b\ttitle_b\tRNA-Seq\n',
        'recount3_project_metadata': 'external_id\tproject\nrun_a\tproject_a\nrun_b\tproject_a\n',
        'recount3_gencode_v26_gene_annotation': 'chr1\tGENCODE\tgene\t1\t100\t.\t+\t.\tgene_id "ENSG00000000001.1";\nchr1\tGENCODE\tgene\t101\t200\t.\t+\t.\tgene_id "ENSG00000000002.1";\n',
    }
    plan = {'cohort': 'synthetic', 'objects': []}
    manifest = {'objects': {}}
    for role, body in bodies.items():
        raw = gzip.compress(body.encode(), mtime=0)
        sha = hashlib.sha256(raw).hexdigest()
        locator = 'https://example.org/' + role
        (store / 'objects' / sha).write_bytes(raw)
        manifest['objects'][sha] = {'locator': locator, 'version': 'fixture', 'byte_size': len(raw), 'retrieved_at': '2026-10-30'}
        plan['objects'].append({'id': role, 'url': locator, 'expected_sha256': sha})
    (store / 'MANIFEST.json').write_text(json.dumps(manifest))
    return store, plan, bodies


def convert(store, plan, out):
    from tools.a_dav import recount3
    return recount3.convert_recount3(store, plan, out, allow_external_out=True)


def replace_source(store, plan, role, text):
    obj = next(x for x in plan['objects'] if x['id'] == role)
    raw = gzip.compress(text.encode(), mtime=0)
    sha = hashlib.sha256(raw).hexdigest()
    manifest = json.loads((store / 'MANIFEST.json').read_text())
    entry = dict(manifest['objects'][obj['expected_sha256']])
    entry['byte_size'] = len(raw)
    manifest['objects'][sha] = entry
    (store / 'MANIFEST.json').write_text(json.dumps(manifest))
    (store / 'objects' / sha).write_bytes(raw)
    obj['expected_sha256'] = sha


def test_conversion_joins_lengths_by_run_and_uses_ties_to_even(tmp_path):
    store, plan, _ = fixture(tmp_path)
    out = tmp_path / 'result'
    receipt = convert(store, plan, out)
    rows = list(csv.reader((out / 'counts.tsv').open(), delimiter='\t'))
    assert rows == [['gene_id', 'run_b', 'run_a'], ['ENSG00000000001.1', '2', '5'], ['ENSG00000000002.1', '4', '7']]
    assert receipt['counts'] == {'genes': 2, 'runs': 2}
    assert receipt['output_sha256'] == hashlib.sha256((out / 'counts.tsv').read_bytes()).hexdigest()
    assert receipt['admission_status'] == 'UNSIGNED'
    assert receipt['conversion'] == 'compute_read_counts(round=TRUE)'


@pytest.mark.parametrize('value', ['0', '-1', 'NA', 'NaN', 'Inf'])
def test_invalid_length_cannot_publish_counts(tmp_path, value):
    store, plan, bodies = fixture(tmp_path)
    replace_source(store, plan, 'recount3_qc_metadata', bodies['recount3_qc_metadata'].replace('run_b\t200', 'run_b\t' + value))
    with pytest.raises(ValueError, match='RECOUNT3_LENGTH_INVALID'):
        convert(store, plan, tmp_path / 'result')
    assert not (tmp_path / 'result' / 'counts.tsv').exists()


@pytest.mark.parametrize('kind', ['duplicate_run', 'missing_run', 'extra_run', 'bad_value', 'bad_width', 'duplicate_gene', 'unannotated_gene', 'wrong_annotation'])
def test_corrupt_sources_cannot_publish_counts(tmp_path, kind):
    store, plan, bodies = fixture(tmp_path)
    role = 'recount3_gene_sums_G026'
    text = bodies[role]
    if kind == 'duplicate_run': text = text.replace('run_b\trun_a', 'run_a\trun_a')
    if kind == 'missing_run':
        role = 'recount3_qc_metadata'; text = 'external_id\tstar.average_mapped_length\nrun_a\t100\n'
    if kind == 'extra_run':
        role = 'recount3_sra_metadata'; text = bodies[role] + 'run_c\tsample_c\tname_c\ttitle_c\tRNA-Seq\n'
    if kind == 'bad_value': text = text.replace('\t500\t500', '\t-1\t500')
    if kind == 'bad_width': text = text.replace('\t500\t500', '\t500')
    if kind == 'duplicate_gene': text = text.replace('ENSG00000000002.1', 'ENSG00000000001.1')
    if kind == 'unannotated_gene': text = text.replace('ENSG00000000002.1', 'ENSG00000000003.1')
    if kind == 'wrong_annotation': text = text.replace('G026', 'G029')
    replace_source(store, plan, role, text)
    with pytest.raises(ValueError, match='RECOUNT3_'):
        convert(store, plan, tmp_path / 'result')
    assert not (tmp_path / 'result' / 'counts.tsv').exists()


def test_hash_pin_required_and_store_hash_verified(tmp_path):
    store, plan, _ = fixture(tmp_path)
    sha = plan['objects'][0]['expected_sha256']
    plan['objects'][0]['expected_sha256'] = None
    with pytest.raises(ValueError, match='RECOUNT3_PIN_REQUIRED'):
        convert(store, plan, tmp_path / 'result')
    plan['objects'][0]['expected_sha256'] = sha
    (store / 'objects' / sha).write_bytes(b'corrupt')
    with pytest.raises(ValueError, match='SOURCE_SIZE_MISMATCH'):
        convert(store, plan, tmp_path / 'result')


def test_protected_family_refused_before_source_access(tmp_path):
    with pytest.raises(ValueError, match='RECOUNT3_COHORT_NOT_AUTHORIZED'):
        convert(tmp_path / 'absent', {'cohort': 'imvigor210', 'objects': []}, tmp_path / 'result')


def test_no_overwrite_of_existing_product(tmp_path):
    store, plan, _ = fixture(tmp_path)
    out = tmp_path / 'result'
    convert(store, plan, out)
    with pytest.raises(ValueError, match='RECOUNT3_OUTPUT_EXISTS'):
        convert(store, plan, out)


def test_cross_cohort_substitution_is_rejected_before_source_read(tmp_path):
    store, plan, _ = fixture(tmp_path)
    plan['cohort'] = 'gide2019'
    with pytest.raises(ValueError, match='RECOUNT3_PROJECT_BINDING_INVALID'):
        convert(store, plan, tmp_path / 'result')
