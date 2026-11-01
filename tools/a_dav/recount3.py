"""Local, hash-pinned recount3 coverage-to-approximate-count preparation."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .ingest import validate_output_path
from .source_objects import ContentAddressedStore

ROLES = (
    'recount3_gene_sums_G026', 'recount3_qc_metadata', 'recount3_sra_metadata',
    'recount3_project_metadata', 'recount3_gencode_v26_gene_annotation',
)
AUTHORIZED_COHORTS = {
    'gide2019': 'ERP105482', 'kim2018': 'ERP107734',
    'riaz_gse91061': 'SRP094781', 'hugo_gse78220': 'SRP070710',
}


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise ValueError(code)


def _metadata(raw: bytes) -> dict[str, dict[str, str]]:
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8')), delimiter='\t')
    fields = reader.fieldnames or []
    _require('external_id' in fields and len(fields) == len(set(fields)), 'RECOUNT3_METADATA_HEADER_INVALID')
    result: dict[str, dict[str, str]] = {}
    for row in reader:
        _require(None not in row and all(v is not None for v in row.values()), 'RECOUNT3_METADATA_WIDTH_INVALID')
        key = row['external_id']
        _require(bool(key.strip()) and key not in result, 'RECOUNT3_METADATA_RUN_DUPLICATE_OR_BLANK')
        result[key] = row
    return result


def convert_recount3(store_path: Path, plan: dict[str, Any], output: Path, *,
                     allow_external_out: bool = False) -> dict[str, Any]:
    """Convert all runs without selecting patients, endpoints, or admission rules.

    The synthetic cohort is usable only with the explicit external-output test
    interface. The public CLI accepts only the four authorized source cohorts.
    """
    cohort = plan.get('cohort')
    _require(cohort in AUTHORIZED_COHORTS or (cohort == 'synthetic' and allow_external_out),
             'RECOUNT3_COHORT_NOT_AUTHORIZED')
    output = validate_output_path(output, allow_external_out=allow_external_out)
    _require(not output.exists(), 'RECOUNT3_OUTPUT_EXISTS')
    objects = plan.get('objects', [])
    _require(isinstance(objects, list) and len(objects) == len(ROLES)
             and {x.get('id') for x in objects} == set(ROLES), 'RECOUNT3_PLAN_ROLES_INVALID')
    if cohort in AUTHORIZED_COHORTS:
        accession = AUTHORIZED_COHORTS[cohort]
        prefix = 'https://recount-opendata.s3.amazonaws.com/recount3/release/human/'
        project_path = accession[-2:] + '/' + accession + '/'
        expected_urls = {
            'recount3_gene_sums_G026': prefix + 'data_sources/sra/gene_sums/' + project_path + 'sra.gene_sums.' + accession + '.G026.gz',
            'recount3_gencode_v26_gene_annotation': prefix + 'annotations/gene_sums/human.gene_sums.G026.gtf.gz',
        }
        for name in ('sra', 'project', 'qc'):
            source_name = 'sra' if name == 'sra' else 'recount_' + name
            expected_urls['recount3_' + name + '_metadata'] = (
                prefix + 'data_sources/sra/metadata/' + project_path
                + 'sra.' + source_name + '.' + accession + '.MD.gz')
        _require(all(obj.get('url') == expected_urls[obj['id']] for obj in objects),
                 'RECOUNT3_PROJECT_BINDING_INVALID')
    store = ContentAddressedStore(store_path)
    raw: dict[str, bytes] = {}
    hashes: dict[str, str] = {}
    for obj in objects:
        sha = obj.get('expected_sha256')
        _require(isinstance(sha, str) and re.fullmatch('[a-f0-9]{64}', sha) is not None,
                 'RECOUNT3_PIN_REQUIRED')
        source = store.read(sha)
        _require(source.locator == obj.get('url') and source.locator.startswith('https://'),
                 'RECOUNT3_LOCATOR_MISMATCH')
        raw[obj['id']] = gzip.decompress(source.bytes)
        hashes[obj['id']] = sha
    qc = _metadata(raw['recount3_qc_metadata'])
    sra = _metadata(raw['recount3_sra_metadata'])
    project = _metadata(raw['recount3_project_metadata'])
    annotation: set[str] = set()
    for line in raw['recount3_gencode_v26_gene_annotation'].decode('utf-8').splitlines():
        if line.startswith('#') or not line.strip():
            continue
        fields = line.split('\t')
        _require(len(fields) == 9, 'RECOUNT3_ANNOTATION_INVALID')
        if fields[2] == 'gene':
            match = re.search(r'(?:^|;\s*)gene_id "([^"]+)";', fields[8])
            _require(match is not None, 'RECOUNT3_ANNOTATION_GENE_ID_MISSING')
            assert match is not None
            _require(match[1] not in annotation, 'RECOUNT3_ANNOTATION_DUPLICATE')
            annotation.add(match[1])
    _require(bool(annotation), 'RECOUNT3_ANNOTATION_EMPTY')
    lines = raw['recount3_gene_sums_G026'].decode('utf-8').splitlines()
    _require('##annotation=G026' in lines, 'RECOUNT3_ANNOTATION_VERSION_MISMATCH')
    rows = csv.reader((line for line in lines if not line.startswith('##')), delimiter='\t')
    header = next(rows, [])
    _require(len(header) > 1 and header[0] == 'gene_id', 'RECOUNT3_MATRIX_HEADER_INVALID')
    runs = header[1:]
    _require(all(x.strip() for x in runs) and len(runs) == len(set(runs)), 'RECOUNT3_MATRIX_RUN_DUPLICATE_OR_BLANK')
    _require(set(runs) == set(qc) == set(sra) == set(project), 'RECOUNT3_RUN_INVENTORY_MISMATCH')
    lengths: list[float] = []
    for run in runs:
        try:
            length = float(qc[run]['star.average_mapped_length'])
        except (ValueError, KeyError):
            raise ValueError('RECOUNT3_LENGTH_INVALID') from None
        _require(math.isfinite(length) and length > 0, 'RECOUNT3_LENGTH_INVALID')
        _require(sra[run].get('library_strategy') == 'RNA-Seq', 'RECOUNT3_NOT_RNA_SEQ')
        lengths.append(length)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.recount3-', dir=output.parent))
    try:
        genes: set[str] = set()
        with (staging / 'counts.tsv').open('w', newline='') as handle:
            writer = csv.writer(handle, delimiter='\t', lineterminator='\n')
            writer.writerow(header)
            for row in rows:
                _require(len(row) == len(header), 'RECOUNT3_MATRIX_WIDTH_INVALID')
                gene = row[0]
                _require(gene in annotation and gene not in genes, 'RECOUNT3_FEATURE_UNKNOWN_OR_DUPLICATE')
                genes.add(gene)
                counts: list[int] = []
                for value, length in zip(row[1:], lengths):
                    try:
                        coverage = float(value)
                    except ValueError:
                        raise ValueError('RECOUNT3_COVERAGE_INVALID') from None
                    _require(math.isfinite(coverage) and coverage >= 0 and coverage.is_integer(),
                             'RECOUNT3_COVERAGE_INVALID')
                    count = coverage / length
                    _require(math.isfinite(count), 'RECOUNT3_COUNT_NONFINITE')
                    counts.append(round(count))
                writer.writerow([gene, *counts])
        _require(bool(genes), 'RECOUNT3_MATRIX_EMPTY')
        fields = ['external_id', 'sample_acc', 'sample_name', 'sample_title', 'library_strategy']
        with (staging / 'sample_inventory.tsv').open('w', newline='') as handle:
            inventory_writer = csv.DictWriter(handle, fieldnames=fields, delimiter='\t', lineterminator='\n')
            inventory_writer.writeheader()
            for run in runs:
                inventory_writer.writerow({key: sra[run].get(key, '') for key in fields})
        receipt = {
            'cohort': cohort, 'conversion': 'compute_read_counts(round=TRUE)',
            'length_column': 'recount_qc.star.average_mapped_length',
            'raw_qc_column': 'star.average_mapped_length',
            'rounding': 'nearest_integer_ties_to_even',
            'unit': 'approximate_read_counts', 'transform': 'NONE',
            'genome_build': 'hg38', 'annotation': 'GENCODE v26 (G026)',
            'aligner': 'STAR 2.7.3a', 'megadepth_version': 'UNDOCUMENTED',
            'source_sha256': hashes,
            'plan_sha256': hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
            'output_sha256': hashlib.sha256((staging / 'counts.tsv').read_bytes()).hexdigest(),
            'inventory_sha256': hashlib.sha256((staging / 'sample_inventory.tsv').read_bytes()).hexdigest(),
            'counts': {'genes': len(genes), 'runs': len(runs)},
            'annotation_genes_not_in_matrix': len(annotation - genes),
            'admission_status': 'UNSIGNED', 'patient_selection_status': 'NOT_PERFORMED',
            'method_evidence': 'docs/research/cohort_sources/BATCH3_EVIDENCE_20261030.md#A',
        }
        (staging / 'PROVENANCE.json').write_text(json.dumps(receipt, indent=2) + '\n')
        staging.rename(output)
    except BaseException:
        shutil.rmtree(staging)
        raise
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--store', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = convert_recount3(args.store, json.loads(args.plan.read_text()), args.out)
    except (ValueError, OSError, EOFError):
        print('BLOCKED: recount3 source, conversion or output validation failed')
        return 1
    print(json.dumps({'status': 'converted, unsigned', 'counts': receipt['counts']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
