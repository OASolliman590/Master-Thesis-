"""Extract a private, outcome-eligible expression matrix from a pinned source."""
from __future__ import annotations

import csv
from collections.abc import Iterator
import gzip
import hashlib
import math
import re
from pathlib import Path
from typing import Any, cast

from .ingest import validate_output_path
from .matrix_header import matrix_rows, transpose_sample_rows


def materialize_expression(store: Path, source_hash: str, rows: list[dict[str, Any]], output: Path,
                           *, delimiter: str, compressed: bool,
                           orientation: str = "samples_as_columns",
                           source_format: str = "MATRIX_HEADER_CSV",
                           missing_policy: str = "BLOCK",
                           excluded_feature_rows: list[dict[str, Any]] | None = None,
                           auxiliary_columns: list[dict[str, Any]] | None = None,
                           allow_external_out: bool = False) -> dict[str, Any]:
    """Extract source values verbatim; this does not confer admission or validation."""
    target = validate_output_path(output, allow_external_out=allow_external_out)
    if not re.fullmatch(r'[a-f0-9]{64}', source_hash):
        raise ValueError('HASH_OR_VERSION_MISMATCH')
    source = store / 'objects' / source_hash
    if not source.is_file():
        source = store / source_hash
    try:
        hasher = hashlib.sha256()
        with source.open('rb') as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                hasher.update(chunk)
    except OSError:
        raise ValueError('HASH_OR_VERSION_MISMATCH') from None
    if hasher.hexdigest() != source_hash:
        raise ValueError('HASH_OR_VERSION_MISMATCH')
    if missing_policy not in {'BLOCK', 'EXCLUDE_FEATURE_IF_ANY_MISSING'}:
        raise ValueError('ASSAY_UNSUPPORTED')
    if orientation not in {'samples_as_columns', 'samples_as_rows'}:
        raise ValueError('ASSAY_UNSUPPORTED')
    if delimiter not in {',', '\t'}:
        raise ValueError('ASSAY_UNSUPPORTED')
    patients = [row for row in rows if row.get('inclusion_status') == 'INCLUDED']
    if any(row.get('endpoint_evaluability') != 'EVALUABLE' for row in patients):
        raise ValueError('ENDPOINT_NOT_EVALUABLE')
    patient_ids = [row.get('patient_uid') for row in patients]
    columns = [row.get('expression_column') for row in patients]
    if (any(not isinstance(x, str) or not x for x in patient_ids + columns)
            or len(set(patient_ids)) != len(patient_ids) or len(set(columns)) != len(columns)):
        raise ValueError('MATRIX_GRAIN_DUPLICATE')
    source_columns = cast(list[str], columns)
    if target.exists():
        raise ValueError('HASH_OR_VERSION_MISMATCH')
    target.parent.mkdir(parents=True, exist_ok=True)
    features: set[str] = set()
    missing = 0
    excluded_missing = 0
    exclusions = {item['row']: item['identifier'] for item in (excluded_feature_rows or [])}
    excluded_count = 0
    if len(exclusions) != len(excluded_feature_rows or []):
        raise ValueError('FEATURE_COVERAGE_FAILED')
    created = False
    try:
        with matrix_rows(source, delimiter=delimiter, compressed=compressed, source_format=source_format) as reader:
            if orientation == "samples_as_rows":
                reader = iter(transpose_sample_rows(reader))
            header = next(reader, [])
            excluded_indexes = {item['index'] for item in (auxiliary_columns or [])}
            if (len(excluded_indexes) != len(auxiliary_columns or []) or
                any(type(item.get('index')) is not int or item['index'] <= 0 or item['index'] >= len(header) or header[item['index']] != item.get('header') for item in (auxiliary_columns or []))):
                raise ValueError('ASSAY_UNSUPPORTED')
            if len(header) != len(set(header)) or not all(x in header[1:] for x in source_columns):
                raise ValueError('UNRESOLVED_IDENTIFIER')
            indices = [header.index(x) for x in source_columns]
            if excluded_indexes.intersection(indices):
                raise ValueError('ASSAY_UNSUPPORTED')
            with target.open('x', encoding='utf-8', newline='') as target_handle:
                created = True
                writer = csv.writer(target_handle, delimiter='\t', lineterminator='\n')
                writer.writerow(['feature_id', *patient_ids])
                for row_number, row in enumerate(reader, 1):
                    if len(row) != len(header):
                        raise ValueError('FEATURE_COVERAGE_FAILED')
                    feature = row[0]
                    if row_number in exclusions:
                        if feature.strip() != exclusions[row_number]:
                            raise ValueError('FEATURE_COVERAGE_FAILED')
                        excluded_count += 1
                        continue
                    if not feature.strip() or feature in features:
                        raise ValueError('MATRIX_GRAIN_DUPLICATE')
                    features.add(feature)
                    if missing_policy == 'EXCLUDE_FEATURE_IF_ANY_MISSING':
                        source_values = [value for index, value in enumerate(row) if index > 0 and index not in excluded_indexes]
                        source_missing = sum(not value.strip() or value.strip().upper() in {'NA', 'N/A', 'NULL'} for value in source_values)
                        if source_missing:
                            missing += source_missing
                            excluded_missing += 1
                            continue
                    values = [row[index] for index in indices]
                    for value in values:
                        if not value.strip() or value.strip().upper() in {'NA', 'N/A', 'NULL'}:
                            missing += 1
                        else:
                            try:
                                number = float(value)
                            except ValueError:
                                raise ValueError('ASSAY_UNSUPPORTED') from None
                            if not math.isfinite(number) or number < 0:
                                raise ValueError('ASSAY_UNSUPPORTED')
                    writer.writerow([feature, *values])
                if excluded_count != len(exclusions) or not features or len(features) == excluded_missing:
                    raise ValueError('FEATURE_COVERAGE_FAILED')
    except (OSError, UnicodeError, csv.Error, ValueError):
        if created:
            target.unlink(missing_ok=True)
        raise
    return {'gene_count': len(features) - excluded_missing, 'patient_count': len(patients), 'missing_count': missing,
            'excluded_missing_gene_count': excluded_missing,
            'excluded_feature_row_count': excluded_count,
            'source_sha256': source_hash, 'output_sha256': hashlib.sha256(target.read_bytes()).hexdigest()}


def write_validated_products(packet: dict[str, Any], store: Path, source_hash: str, output: Path, *,
                             delimiter: str, compressed: bool,
                             orientation: str = "samples_as_columns",
                             source_format: str = "MATRIX_HEADER_CSV",
                             missing_policy: str = "BLOCK",
                             excluded_feature_rows: list[dict[str, Any]] | None = None,
                             auxiliary_columns: list[dict[str, Any]] | None = None,
                             allow_external_out: bool = False) -> dict[str, Any]:
    """Write products only after validating the actual baseline and admission dependencies."""
    import json
    from datetime import datetime, timezone
    from .core import SchemaStore, dependency, digest
    from .provisional import apply_historical_flags
    import re as regex

    schemas = SchemaStore()
    baseline = dependency(packet, 'baseline', schemas)
    admission = dependency(packet, 'admission', schemas)
    split = dependency(packet, 'split', schemas)
    records = baseline['records']
    rows = [dict(row, flags=[]) for row in records.get('baseline', [])]
    ids = [row['patient_uid'] for row in rows]
    if not rows or len(ids) != len(set(ids)):
        raise ValueError('MATRIX_GRAIN_DUPLICATE')
    patients = {row['patient_uid'] for row in records.get('patient_registry', [])}
    specimens = {row['specimen_uid'] for row in records.get('specimen_registry', [])}
    assays = {row['assay_uid']:row for row in records.get('assay_registry', [])}
    if set(ids) != patients or any(row.get('specimen_uid') not in specimens or row.get('assay_uid') not in assays for row in rows):
        raise ValueError('UNRESOLVED_IDENTIFIER')
    if any(row.get('branch_id') != packet['branch_id'] for row in rows):
        raise ValueError('MATRIX_GRAIN_DUPLICATE')
    sources = [row for row in records.get('source_record', []) if row.get('sha256') == source_hash]
    if len(sources) != 1:
        raise ValueError('HASH_OR_VERSION_MISMATCH')
    source = sources[0]
    if source.get('retrieval_status') != 'RETRIEVED' or source.get('validation_status') != 'PASS' or source.get('hash_scope') != 'FULL_OBJECT':
        raise ValueError('UNADMITTED_SOURCE')
    if any(assays[row['assay_uid']]['source_object_id'] != source['source_object_id'] for row in rows):
        raise ValueError('ASSAY_UNSUPPORTED')
    if packet['classification'] != 'SYNTHETIC_ONLY':
        receipts = admission['records'].get('cohort_admission_receipt', [])
        if not any(source['source_object_id'] in receipt.get('source_object_ids', []) and
                   packet['branch_id'] in receipt.get('approved_branches', []) and
                   receipt.get('admission_status') in {'ADMITTED','ADMITTED_WITH_LIMITATIONS','SENSITIVITY_ONLY'}
                   for receipt in receipts):
            raise ValueError('UNADMITTED_SOURCE')
    roles = {row['patient_uid']:row['permanent_role'] for row in split['records'].get('split', [])}
    split_versions = {row['split_version'] for row in split['records'].get('split', [])}
    if set(roles) != set(ids) or any(roles[row['patient_uid']] != row.get('split_role') for row in rows):
        raise ValueError('SPLIT_NOT_FROZEN')
    if len(split_versions) != 1:
        raise ValueError('SPLIT_NOT_FROZEN')
    evidence = packet['config'].get('materialization', {}).get('pca_flag_evidence')
    if evidence is not None:
        document = Path(evidence['document'])
        if document.is_absolute() or '..' in document.parts:
            raise ValueError('HISTORICAL_FLAG_EVIDENCE_MISSING')
        found = regex.findall(evidence['patient_id_regex'], document.read_text(encoding='utf-8'), regex.IGNORECASE)
        if len(found) != 1 or not isinstance(found[0], str):
            raise ValueError('HISTORICAL_FLAG_EVIDENCE_MISSING')
        items = packet['config']['admission'].get('ingestion_worksheet', [])
        if isinstance(items, dict):
            items = items.get('items', [])
        title_rule = packet['config']['materialization'].get('historical_title_rule', {})
        apply_historical_flags(rows, records, items, outlier_source_id=found[0],
                               patient_regex=title_rule.get('patient_regex'), patient_group=title_rule.get('patient_group', 1))
    folder = validate_output_path(output, allow_external_out=allow_external_out)
    folder.mkdir(parents=True, exist_ok=False)
    expression = materialize_expression(store, source_hash, rows, folder / 'expression.tsv',
                                        orientation=orientation, source_format=source_format,
                                        missing_policy=missing_policy, excluded_feature_rows=excluded_feature_rows, auxiliary_columns=auxiliary_columns,
                                        delimiter=delimiter, compressed=compressed, allow_external_out=allow_external_out)
    fields = ['patient_uid','raw_response','canonical_category','endpoint_evaluability','split_role','prior_ici','flags',
              'inclusion_status','exclusion_reason','specimen_uid','assay_uid','expression_column']
    with (folder / 'patients.tsv').open('x', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter='\t', extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, 'flags':'|'.join(row['flags'])})
    state_counts = {state: sum(row.get('endpoint_evaluability') == state for row in rows)
                    for state in ('EVALUABLE','NOT_EVALUABLE','UNKNOWN')}
    checks = {name:0 for name in ('MATRIX_GRAIN_DUPLICATE','UNRESOLVED_IDENTIFIER','UNADMITTED_SOURCE',
              'BASELINE_SELECTION_AMBIGUOUS','ASSAY_UNSUPPORTED','FEATURE_COVERAGE_FAILED',
              'SPLIT_NOT_FROZEN','HASH_OR_VERSION_MISMATCH')}
    checks['ENDPOINT_NOT_EVALUABLE'] = state_counts['NOT_EVALUABLE'] + state_counts['UNKNOWN']
    result = {'classification':packet['classification'], 'branch_id':packet['branch_id'],
              'counts':{'gene_count':expression['gene_count'],'expression_patient_count':expression['patient_count'],
                        'patient_count':len(rows),'specimen_count':len({r['specimen_uid'] for r in rows}),
                        'assay_count':len({r['assay_uid'] for r in rows}),'evaluability':state_counts,
                        'missing_cells':expression['missing_count'],
                        'excluded_missing_gene_count':expression['excluded_missing_gene_count'],
                        'paper_pca_outlier_flags':sum('PAPER_PCA_OUTLIER' in r['flags'] for r in rows),
                        'author_script_exclusion_flags':sum('AUTHOR_SCRIPT_EXCLUSION' in r['flags'] for r in rows)},
              'checks':checks,'source_admission_receipt_id':admission['receipt_id'],
              'split_version':next(iter(split_versions)), 'build_utc':datetime.now(timezone.utc).isoformat(),
              'config_sha256':digest(packet['config']), 'input_sha256':source_hash,
              'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'expression_sha256':expression['output_sha256'],
              'patient_table_sha256':hashlib.sha256((folder / 'patients.tsv').read_bytes()).hexdigest()}
    counts = result['counts']
    output_hash = digest({'expression': result['expression_sha256'], 'patients': result['patient_table_sha256']})
    receipt = {'matrix_build_receipt_id': rows[0]['build_receipt_id'],
               'matrix_id': 'baseline-expression-' + output_hash[:16], 'branch_id': packet['branch_id'],
               'schema_version_used': '1.1.0', 'source_admission_receipt_ids': [admission['receipt_id']],
               'patient_count':len(rows), 'specimen_count':counts['specimen_count'], 'assay_count':counts['assay_count'],
               'class_counts':state_counts, 'timepoint_counts':{'PRE_INDEX_BASELINE':len(rows)},
               'excluded_records':{'ENDPOINT_NOT_EVALUABLE':checks['ENDPOINT_NOT_EVALUABLE']},
               'duplicate_checks':{'patient_rows':checks['MATRIX_GRAIN_DUPLICATE']},
               'overlap_checks':{'dependency_receipt_id':packet['dependencies']['overlap']['receipt_id']},
               'feature_coverage':{'feature_count':expression['gene_count']},
               'missingness':{'missing_cells':expression['missing_count'],
                              'excluded_missing_gene_count':expression['excluded_missing_gene_count'],
                              'policy':missing_policy},
               'split_version':next(iter(split_versions)), 'input_hashes':[source_hash, baseline['receipt_id']],
               'code_hash':result['code_sha256'], 'config_hash':result['config_sha256'],
               'output_hash':output_hash, 'build_utc':result['build_utc'], 'test_status':'NOT_RUN',
               'validation_status':'PASS'}
    schemas.validate('matrix_build_receipt', receipt)
    (folder / 'matrix_build_receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    (folder / 'matrix_contract.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    return result
