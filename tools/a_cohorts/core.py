"""Build simple cohort tables from pinned local source products."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import tempfile
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / '.scratch/runtime'
REGISTRY = ROOT / 'docs/cohorts/REGISTRY.tsv'
VERSION = 'simple-3'
ADMITTED = {'riaz_gse91061': 'admitted-20261029', 'hugo_gse78220': 'admitted-20261029e',
            'gse168204': 'admitted-20261029e', 'liu2019': 'admitted-20261030d'}

SIMPLE_GEO = {'gse218989', 'gse159067', 'gse145996', 'gse165278',
              'gse93157', 'gse67501', 'gse122220', 'gse140901', 'gse111636'}
SUPPORTED_COHORTS = set(ADMITTED) | {'gse135222', 'gse136961', 'gse176307', 'braun2020', 'vanallen2015', 'gide2019', 'kim2018'} | SIMPLE_GEO

def registry():
    with REGISTRY.open(newline='') as f:
        return {r['cohort_id']: r for r in csv.DictReader(f, delimiter='\t')}


def check_allowed(cohort):
    if not re.fullmatch(r'[a-z0-9_]+', cohort) or 'imvigor' in cohort.lower():
        raise ValueError(f'{cohort} refused: invalid or locked cohort')
    row = registry().get(cohort)
    if row is None:
        raise ValueError('Unknown cohort')
    if 'final test' in row['role'].lower() or 'excluded' in row['role'].lower() or 'combination' in row['role'].lower():
        raise ValueError(f'{cohort} refused: locked or excluded from A/B')
    return row


def orr_category(value):
    value = str(value or '').upper().strip()
    value = {'COMPLETE RESPONSE': 'CR', 'PARTIAL RESPONSE': 'PR', 'STABLE DISEASE': 'SD', 'PROGRESSIVE DISEASE': 'PD'}.get(value, value)
    return value if value in {'CR', 'PR', 'SD', 'PD', 'NE'} else 'UNKNOWN'


def benefit_category(value):
    value = str(value or '').upper().strip()
    return {'SOURCE_POSITIVE': 'R', 'SOURCE_NEGATIVE': 'NR', 'DCB': 'R', 'NDB': 'NR', 'R': 'R', 'NR': 'NR'}.get(value, 'UNKNOWN')


def endpoints(orr, benefit):
    return {'orr': orr_category(orr), 'clinical_benefit': benefit_category(benefit)}


def source_outcomes(outcomes, *, preserve_benefit=False):
    orrs = {str(o['raw_endpoint_label']).strip() for o in outcomes
            if o['endpoint_class'] in {'ORR', 'TUMOUR_RESPONSE'} and o.get('raw_endpoint_label')}
    benefits = {str(o['raw_endpoint_label']).strip() for o in outcomes
                if o['endpoint_class'] == 'SOURCE_BINARY' and o.get('raw_endpoint_label')}
    if len(orrs) > 1 or len(benefits) > 1:
        raise ValueError('conflicting source outcomes')
    raw_orr = next(iter(orrs), 'UNKNOWN')
    raw_benefit = next(iter(benefits), 'UNKNOWN')
    return orr_category(raw_orr), raw_benefit if preserve_benefit else benefit_category(raw_benefit)


def survival_fields(values):
    return {label: f"{values[key]} months" if values.get(key) else 'UNKNOWN'
            for label, key in [('pfs', 'PFS_MONTHS'), ('os', 'OS_MONTHS')]}


def survival_from_source(values, unit):
    return {key: (str(values.get(key, '')).strip() + (' ' + unit if unit else ''))
            if str(values.get(key, '')).strip() not in {'', 'NA', 'N/A', 'UNKNOWN', '-'} else 'UNKNOWN'
            for key in ('pfs', 'os')}


def panel_survival(value):
    pfs = re.search(r'progression-free-survival_days:([0-9.]+)', value)
    os_match = re.search(r'overall-survival_days:([0-9.]+)', value)
    return survival_from_source({'pfs': pfs[1] if pfs else '', 'os': os_match[1] if os_match else ''}, 'days')


def geo_survival(cohort, field_map):
    from tools.a_dav.geo_soft import parse_geo_family_soft
    cfg = field_map['source_objects']['geo_family_soft']
    source = RUNTIME / cohort / 'store/objects' / cfg['sha256']
    result = {}
    for sample in parse_geo_family_soft(source.read_bytes()):
        attrs = {x['key']: x['value'] for x in sample['characteristics']}
        if cohort == 'gse136961':
            values = panel_survival(attrs.get('survival', ''))
        elif cohort == 'gse135222':
            values = survival_from_source({'pfs': attrs.get('pfs.time', '')}, '')
        elif cohort == 'gse176307':
            values = survival_from_source({'pfs': attrs.get('pfs', ''), 'os': attrs.get('overall survival', '')}, '')
        else:
            values = survival_from_source({'os': attrs.get('overall survival (days)', '')}, 'days')
        result[sample['accession']] = values
    return result


def cbio_survival(cohort, field_map):
    from tools.a_dav.cbioportal import read_clinical
    role = field_map['cbio_ingest']['patient_role']
    obj = RUNTIME / cohort / 'store/objects' / field_map['source_objects'][role]['sha256']
    rows = read_clinical(obj.read_bytes())
    return {r['PATIENT_ID']: survival_fields(r) for r in rows}


def sha256(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def safe_path(path):
    # Never traverse symlinks inside the private runtime tree.
    path = Path(path)
    for part in [path, *path.parents]:
        if part.is_symlink():
            raise ValueError('Symlink in runtime path')
        if part == ROOT:
            break
    if not path.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError('Runtime path escapes workspace')
    return path

def recount_count(coverage, average_length):
    if not math.isfinite(coverage) or coverage < 0 or not math.isfinite(average_length) or average_length <= 0:
        raise ValueError('Invalid coverage or average mapped length')
    return round(coverage / average_length)


def unique_index(rows, key):
    result = {}
    for row in rows:
        value = row[key]
        if not value or value in result:
            raise ValueError(f'Duplicate or empty {key}')
        result[value] = row
    return result


def one_to_one_pre_crosswalk(rows):
    from collections import Counter
    candidates = [r for r in rows if r.get('timepoint') == 'PRE' and r.get('run') and r.get('patient')]
    runs = Counter(r['run'] for r in candidates)
    patients = Counter(r['patient'] for r in candidates)
    return {r['run']: r['patient'] for r in candidates if runs[r['run']] == patients[r['patient']] == 1}


def gide_crosswalk(field_map, records):
    import gzip
    from tools.a_dav.cbioportal import read_inventory
    obj = RUNTIME / 'gide2019/store-recount3/objects/f882e68caf9309a25e77b509a2c071229a034f8468d889bca7892122be71b61a'
    if sha256(obj) != obj.name:
        raise ValueError('Gide SRA metadata hash mismatch')
    with gzip.open(obj, 'rt', newline='') as f:
        sra = list(csv.DictReader(f, delimiter='\t'))
    sample_role = field_map['cbio_ingest']['sample_role']
    sample_object = RUNTIME / 'gide2019/store/objects' / field_map['source_objects'][sample_role]['sha256']
    samples = read_inventory(sample_object.read_bytes(), ['SAMPLE_ID', 'PATIENT_ID', 'SAMPLE_TREATMENT'])
    sample_index = unique_index(samples, 'SAMPLE_ID')
    patient_index = {p['source_patient_id']: p['patient_uid'] for p in records['patient_registry']}
    unique_index(sra, 'external_id'); unique_index(sra, 'sample_acc'); unique_index(sra, 'sample_name')
    pairs = []
    pre_count = 0
    for row in sra:
        attrs = dict(x.split(';;', 1) for x in row['sample_attributes'].split('|') if ';;' in x)
        title = row['sample_title']
        match = re.fullmatch(r'(PD1|ipiPD1)_(\d+)_(PRE|EDT)', title)
        if not match or attrs.get('Title') != title or attrs.get('Alias') != title:
            raise ValueError('Gide SRA title/attribute inconsistency')
        if match[3] != 'PRE':
            continue
        pre_count += 1
        alias = ('PD' if match[1] == 'PD1' else 'iP') + match[2] + '_Pre'
        sample = sample_index.get(alias)
        patient = patient_index.get(sample['PATIENT_ID'], '') if sample and sample['SAMPLE_TREATMENT'] == 'Pre' else ''
        pairs.append({'run': row['external_id'], 'patient': patient, 'timepoint': 'PRE'})
    if pre_count != 73:
        raise ValueError('Unexpected Gide PRE run count')
    return one_to_one_pre_crosswalk(pairs), pre_count


def read_rows(path):
    with path.open(newline='') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def write_rows(path, rows, columns):
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns, delimiter='\t', lineterminator='\n', extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def expected_output_names(cohort):
    names = ['expression.tsv', 'clinical.tsv', 'caveats.md']
    if cohort in {'gse67501', 'gse122220', 'gse111636'}:
        names.append('probe_to_gene.tsv')
    return names


def _soft_platform_rows(soft_raw):
    import gzip
    text = gzip.decompress(soft_raw).decode('utf-8') if soft_raw.startswith(b'\x1f\x8b') else soft_raw.decode('utf-8')
    if '!platform_table_begin\n' not in text or '!platform_table_end' not in text:
        raise ValueError('GEO SOFT has no platform annotation table')
    table = text.split('!platform_table_begin\n', 1)[1].split('!platform_table_end', 1)[0]
    return list(csv.DictReader(table.splitlines(), delimiter='\t'))


def write_probe_to_gene_map(soft_raw, expression_path, target):
    """Write a probe-level table from the expression rows and SOFT platform annotation."""
    from collections import Counter
    annotation = {}
    for row in _soft_platform_rows(soft_raw):
        probe = (row.get('ID') or '').strip()
        if not probe or probe in annotation:
            raise ValueError('Missing or duplicate SOFT platform probe ID')
        symbol = (row.get('Symbol') or '').strip()
        entrez_key = next((key for key in row if key.lower() in {'entrez_gene_id', 'entrez id'}), None)
        entrez = (row.get(entrez_key) or '').strip() if entrez_key else ''
        if symbol in {'---', 'NA', 'N/A', 'NULL'}:
            symbol = ''
        if entrez in {'---', 'NA', 'N/A', 'NULL'}:
            entrez = ''
        annotation[probe] = (symbol, entrez)
    with expression_path.open(newline='') as stream:
        reader = csv.reader(stream, delimiter='\t')
        next(reader)
        probes = [row[0] for row in reader]
    if not probes or len(set(probes)) != len(probes):
        raise ValueError('Expression probe IDs are empty or duplicated')
    missing = set(probes) - set(annotation)
    if missing:
        raise ValueError('Expression probes are missing from the SOFT platform table')
    symbols = Counter()
    mapped = unmapped = 0
    rows = []
    for probe in probes:
        symbol, entrez = annotation[probe]
        if symbol:
            mapped += 1
            symbols[symbol] += 1
        else:
            unmapped += 1
        rows.append({'probe_id': probe, 'gene_symbol': symbol, 'entrez_id': entrez})
    write_rows(target, rows, ['probe_id', 'gene_symbol', 'entrez_id'])
    return {'mapped': mapped, 'unmapped': unmapped,
            'multi_probe_symbols': sum(count > 1 for count in symbols.values())}


def check_gse93157_scale(expression_path):
    from statistics import median
    values = []
    with expression_path.open(newline='') as stream:
        reader = csv.reader(stream, delimiter='\t')
        next(reader)
        for row in reader:
            values.extend(float(value) for value in row[1:])
    if not values or not all(math.isfinite(value) for value in values):
        raise ValueError('GSE93157 expression has no finite values')
    summary = {'minimum': min(values), 'maximum': max(values), 'median': median(values),
               'negative_values': sum(value < 0 for value in values)}
    if not (-2.5 <= summary['minimum'] <= -0.5 and 15 <= summary['maximum'] <= 21
            and 6.5 <= summary['median'] <= 9
            and summary['negative_values'] <= max(10, len(values) * 0.01)):
        raise ValueError('GSE93157 matrix values do not match the expected log2 NanoString scale')
    return summary


def export_admitted(cohort, output, row):
    base = safe_path(RUNTIME / cohort / ADMITTED[cohort])
    products = base / 'products'
    receipt = json.loads((products / 'matrix_build_receipt.json').read_text())
    from tools.a_dav.core import digest
    bundle_hash = digest({'expression': sha256(safe_path(products / 'expression.tsv')),
                          'patients': sha256(safe_path(products / 'patients.tsv'))})
    if bundle_hash != receipt['output_hash']:
        raise ValueError('Admitted product hash mismatch')
    with (products / 'expression.tsv').open(newline='') as f:
        reader = csv.reader(f, delimiter='\t'); header = next(reader); genes = sum(1 for _ in reader)
    patient_rows = unique_index([x for x in read_rows(products / 'patients.tsv') if x['inclusion_status'] == 'INCLUDED'], 'patient_uid')
    packet = json.loads((base / 'fresh-ingest/records/ingestion_packet.json').read_text())['records']
    assays = unique_index(packet['assay_registry'], 'assay_uid')
    exposures = {}
    for x in packet.get('treatment_exposure', []):
        exposures.setdefault(x['patient_uid'], set()).add(x.get('pharmacological_class', 'UNKNOWN'))
    output.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(products / 'expression.tsv', output / 'expression.tsv')
    survival_by_uid = {}
    if cohort == 'liu2019':
        fmap = json.loads((ROOT / 'tools/a_dav/field_maps/liu2019.json').read_text())
        by_id = cbio_survival(cohort, fmap)
        survival_by_uid = {p['patient_uid']: by_id.get(p['source_patient_id'], {}) for p in packet['patient_registry']}
    geo_survival_by_sample = {}
    if cohort == 'hugo_gse78220':
        fmap = json.loads((ROOT / 'tools/a_dav/field_maps/hugo_gse78220.json').read_text())
        geo_survival_by_sample = geo_survival(cohort, fmap)
    clinical = []
    for uid in header[1:]:
        p = patient_rows[uid]; assay = assays.get(p['assay_uid'], {})
        raw = p['raw_response']; category = p['canonical_category']
        survival = survival_by_uid.get(uid, geo_survival_by_sample.get(assay.get('source_sample_id'), {}))
        clinical.append({'patient_id': uid, 'sample_id': assay.get('source_sample_id') or p['specimen_uid'],
                         'timepoint': 'PRE_TREATMENT', 'drug_class': '+'.join(sorted(exposures.get(uid, {'UNKNOWN'}))),
                         'prior_ici': p['prior_ici'] or 'UNKNOWN', 'orr': orr_category(category),
                         'clinical_benefit': benefit_category(raw) if cohort == 'gse168204' else 'UNKNOWN', 'pfs': survival.get('pfs', 'UNKNOWN'), 'os': survival.get('os', 'UNKNOWN'),
                         'raw_orr': raw if cohort != 'gse168204' else '', 'raw_clinical_benefit': raw if cohort == 'gse168204' else '',
                         'endpoint_source': 'admitted patients.tsv', 'endpoint_definition': 'source category; see admitted records'})
    hashes = list(receipt['input_hashes']) + [sha256(safe_path(products / name)) for name in ('expression.tsv', 'patients.tsv', 'matrix_build_receipt.json')]
    hashes.append(sha256(safe_path(base / 'fresh-ingest/records/ingestion_packet.json')))
    return clinical, genes, sorted(set(hashes)), ['Exported from the admitted baseline matrix; existing sample-selection rule retained.']


def input_files(cohort):
    paths = [Path(__file__).resolve()]
    if cohort in ADMITTED:
        base = safe_path(RUNTIME / cohort / ADMITTED[cohort])
        packet = safe_path(base / 'fresh-ingest/records/ingestion_packet.json')
        if cohort in {'liu2019', 'hugo_gse78220'}:
            paths.append(ROOT / 'tools/a_dav/field_maps' / (cohort + '.json'))
        paths += [packet, *(safe_path(base / 'products' / name) for name in
                            ('expression.tsv', 'patients.tsv', 'matrix_build_receipt.json'))]
        records = json.loads(packet.read_text())['records']
        hashes = [r['sha256'] for r in records['source_record'] if r.get('sha256')]
    elif cohort == 'kim2018':
        base = safe_path(RUNTIME / cohort / 'recount3-reviewed-20261030')
        paths += [base / x for x in ('counts.tsv', 'sample_inventory.tsv', 'PROVENANCE.json')]
        paper = safe_path(RUNTIME / cohort / 'staging-paper-20261102')
        paths += [paper / x for x in ('paper.pdf', 'table2_extracted.tsv', 'table2_extracted.provenance.json')]
        receipt = json.loads((base / 'PROVENANCE.json').read_text())
        if sha256(base / 'counts.tsv') != receipt['output_sha256'] or sha256(base / 'sample_inventory.tsv') != receipt['inventory_sha256']:
            raise ValueError('recount3 product hash mismatch')
        hashes = []
    elif cohort in SIMPLE_GEO:
        manifest_path = safe_path(RUNTIME / cohort / 'store/MANIFEST.json')
        paths.append(manifest_path)
        manifest = json.loads(manifest_path.read_text())
        hashes = [digest for digest, entry in manifest.get('objects', {}).items()
                  if cohort != 'gse111636' or any(part in entry.get('locator', '') for part in ('/matrix/', 'family.soft'))]
        if len(hashes) != (3 if cohort == 'gse140901' else 2):
            raise ValueError('Unexpected number of pinned GEO source objects')
        if cohort == 'gse165278':
            paths.append(safe_path(RUNTIME / cohort / 'store_labels/MANIFEST.json'))
    else:
        field = ROOT / 'tools/a_dav/field_maps' / (cohort + '.json')
        packet = safe_path(RUNTIME / cohort / 'ingest-20261030/records/ingestion_packet.json')
        paths += [field, packet]
        mapping = json.loads(field.read_text())
        if cohort == 'gide2019':
            paths.append(safe_path(RUNTIME / cohort / 'admitted-20261030/fresh-ingest/records/ingestion_packet.json'))
            paths.extend(safe_path(RUNTIME / cohort / 'recount3-reviewed-20261030' / x) for x in ('unaccepted_identity_proposal.tsv', 'counts.tsv', 'PROVENANCE.json'))
            paths.append(safe_path(RUNTIME / cohort / 'store-recount3/objects/f882e68caf9309a25e77b509a2c071229a034f8468d889bca7892122be71b61a'))
        hashes = [r['sha256'] for r in mapping['source_objects'].values() if r.get('sha256')]
        if cohort == 'gse135222':
            base = safe_path(RUNTIME / cohort / 'staging-springer-20261030')
            paths += [safe_path(base / x) for x in ('MOESM1.pdf', 'supp_table3_extracted.tsv', 'supp_table3_extracted.provenance.json')]
    for expected in set(hashes):
        if not re.fullmatch(r'[0-9a-f]{64}', expected):
            raise ValueError('Invalid source hash')
        obj = safe_path(RUNTIME / cohort / 'store/objects' / expected)
        if sha256(obj) != expected:
            raise ValueError('Pinned source object hash mismatch')
        paths.append(obj)
    return {str(path.relative_to(ROOT)): sha256(safe_path(path)) for path in paths}


def validate(cohort):
    check_allowed(cohort)
    output = safe_path(RUNTIME / cohort / 'simple')
    manifest = json.loads((output / 'manifest.json').read_text())
    if manifest.get('cohort') != cohort or manifest.get('loader_version') != VERSION:
        raise ValueError('Stale output manifest')
    if input_files(cohort) != manifest.get('input_files'):
        raise ValueError('Stale source or configuration')
    expected_outputs = set(expected_output_names(cohort))
    for name, expected in manifest['output_sha256'].items():
        if name not in expected_outputs or sha256(safe_path(output / name)) != expected:
            raise ValueError('Output hash mismatch')
    if set(manifest['output_sha256']) != expected_outputs:
        raise ValueError('Incomplete output hashes')
    with (output / 'expression.tsv').open(newline='') as f:
        header = next(csv.reader(f, delimiter='\t'))
    clinical = read_rows(output / 'clinical.tsv')
    ids = [r['patient_id'] for r in clinical]
    if header[1:] != ids or len(set(ids)) != len(ids) or not ids:
        raise ValueError('Expression and clinical patient alignment mismatch')
    if len(ids) != manifest['patients']:
        raise ValueError('Patient count mismatch')
    return manifest


def load(cohort):
    row = check_allowed(cohort)
    if cohort not in SUPPORTED_COHORTS:
        raise ValueError('No loader configured for cohort')
    inputs = input_files(cohort)
    parent = safe_path(RUNTIME / cohort)
    output = safe_path(parent / 'simple')
    parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.simple-', dir=parent))
    try:
        if cohort in ADMITTED:
            clinical, genes, hashes, caveats = export_admitted(cohort, stage, row)
        elif cohort == 'kim2018':
            clinical, genes, hashes, caveats = export_kim(stage)
        elif cohort in SIMPLE_GEO:
            clinical, genes, hashes, caveats = export_simple_geo(cohort, stage)
        else:
            clinical, genes, hashes, caveats = export_ingested(cohort, stage)
        columns = ['patient_id', 'sample_id', 'timepoint', 'drug_class', 'prior_ici', 'orr', 'clinical_benefit', 'pd_event', 'pfs', 'os', 'raw_orr', 'raw_clinical_benefit', 'endpoint_source', 'endpoint_definition']
        if cohort in SIMPLE_GEO:
            columns[10:10] = ['pfs_event', 'os_event', 'hot_score', 'hot_phenotype']
        if cohort == 'gse218989':
            columns.append('treatment_outcome')
        if cohort == 'gse111636':
            columns.append('treatment_outcome')
        if cohort in {'gse93157', 'gse140901'}:
            columns.append('cancer')
        if cohort == 'gse93157':
            columns.append('biopsy')
        if cohort == 'gse67501':
            columns += ['specimen_origin', 'therapy_interval_months']
        if cohort == 'gse122220':
            columns.append('previous_ipilimumab')
        write_rows(stage / 'clinical.tsv', clinical, columns)
        (stage / 'caveats.md').write_text('# Caveats\n\n- ' + '\n- '.join([row['caveats'], *caveats]) + '\n')
        output_names = expected_output_names(cohort)
        manifest = {'cohort': cohort, 'loader_version': VERSION, 'input_sha256': hashes,
                    'patients': len(clinical), 'genes': genes,
                    'status': 'ADMITTED' if cohort in ADMITTED else 'PENDING_BATCH_REVIEW', 'input_files': inputs,
                    'output_sha256': {name: sha256(stage / name) for name in output_names}}
        (stage / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
        with (stage / 'expression.tsv').open(newline='') as f:
            header = next(csv.reader(f, delimiter='\t'))
        ids = [r['patient_id'] for r in clinical]
        if not ids or header[1:] != ids or len(set(ids)) != len(ids) or not genes:
            raise ValueError('Expression and clinical patient alignment mismatch')
        if output.exists():
            try:
                existing = validate(cohort)
            except (ValueError, OSError, KeyError, StopIteration):
                raise ValueError('Existing output is stale or invalid; left untouched') from None
            if existing != manifest:
                raise ValueError('Existing output is stale; left untouched')
            return existing
        os.rename(stage, output)
        return manifest
    finally:
        shutil.rmtree(stage, ignore_errors=True)

def export_kim(output):
    base = RUNTIME / 'kim2018/recount3-reviewed-20261030'
    inventory = read_rows(base / 'sample_inventory.tsv')
    unique_index(inventory, 'external_id')
    unique_index(inventory, 'sample_title')
    stage = RUNTIME / 'kim2018/staging-paper-20261102'
    provenance = json.loads((stage / 'table2_extracted.provenance.json').read_text())
    if sha256(stage / 'paper.pdf') != provenance['source_sha256']:
        raise ValueError('Kim 2018 paper hash mismatch')
    table = {r['seq_id']: r for r in read_rows(stage / 'table2_extracted.tsv')}
    # recount3 sample titles are the paper's Table 2 sequencing IDs plus '_RNA'; join exactly.
    linked = {r['external_id']: table.get(r['sample_title'].removesuffix('_RNA')) for r in inventory}
    if None in linked.values():
        raise ValueError('recount3 sample title without an exact Table 2 sequencing ID')
    mapping = {r['external_id']: linked[r['external_id']]['trial_patient'] for r in inventory}
    unique_index([{'p': p} for p in mapping.values()], 'p')
    output.mkdir(parents=True, exist_ok=True)
    genes, duplicates = project_matrix(base / 'counts.tsv', output / 'expression.tsv', mapping, {'format': 'MATRIX_HEADER_TSV'})
    clinical = []
    for r in inventory:
        t = linked[r['external_id']]
        best = t['best_response']
        clinical.append({'patient_id': t['trial_patient'], 'sample_id': r['external_id'], 'timepoint': 'PRE_TREATMENT',
                         'drug_class': 'ANTI_PD_1', 'prior_ici': 'NO', 'orr': best if best in {'CR', 'PR', 'SD', 'PD'} else 'UNKNOWN',
                         'clinical_benefit': 'UNKNOWN', 'pfs': 'UNKNOWN', 'os': 'UNKNOWN', 'raw_orr': best, 'raw_clinical_benefit': '',
                         'endpoint_source': 'Kim 2018 Nat Med Table 2 (coordinator-extracted)', 'endpoint_definition': 'Best overall response, RECIST 1.1'})
    hashes = [sha256(base / x) for x in ('counts.tsv', 'sample_inventory.tsv', 'PROVENANCE.json')]
    hashes += [sha256(stage / 'table2_extracted.tsv'), provenance['source_sha256']]
    return clinical, genes, hashes, [
        f'All {len(inventory)} recount3 RNA samples join exactly to Kim 2018 Table 2 sequencing IDs (title minus "_RNA"); patient IDs are the trial patient codes. Table 2 is coordinator-extracted from the hash-verified PDF text layer; rows with wrapped text were checked by hand.',
        'Pembrolizumab monotherapy after at least one platinum/fluoropyrimidine line (phase 2, NCT02589496). Fresh-frozen tumour obtained between day 42 and day 1 before treatment. Prior ICI recorded as NO: the trial required patients naive to anti-PD-1/PD-L1/PD-L2 (prior anti-CTLA-4 is not stated).',
        'ORR is best overall response per RECIST 1.1 as given in Table 2; NE would be UNKNOWN (none among the RNA samples).',
        f'recount3 approximate counts; Megadepth version unknown. Duplicate gene IDs: {duplicates}.']


def export_simple_geo(cohort, output):
    """Project one GEO expression object using its exact SOFT sample links."""
    import gzip
    from tools.a_dav.geo_soft import parse_geo_family_soft

    store = safe_path(RUNTIME / cohort / 'store')
    manifest = json.loads(safe_path(store / 'MANIFEST.json').read_text())
    objects = manifest.get('objects', {})
    soft_entry = next((v for v in objects.values() if 'family.soft' in v.get('locator', '')), None)
    if cohort == 'gse140901':
        matrix_entry = next((v for v in objects.values() if '/suppl/' in v.get('locator', '')), None)
    elif cohort in {'gse93157', 'gse67501', 'gse122220', 'gse111636'}:
        matrix_entry = next((v for v in objects.values() if '/matrix/' in v.get('locator', '')), None)
    else:
        # Earlier cohorts pin one SOFT plus one supplementary expression object.
        others = [v for v in objects.values() if 'family.soft' not in v.get('locator', '')]
        matrix_entry = others[0] if len(others) == 1 else None
    if not soft_entry or not matrix_entry:
        raise ValueError('Missing pinned GEO SOFT or expression object')
    soft_hash = soft_entry['receipt']['complete_sha256']
    matrix_hash = matrix_entry['receipt']['complete_sha256']
    soft_path = safe_path(store / 'objects' / soft_hash)
    matrix_path = safe_path(store / 'objects' / matrix_hash)
    if sha256(soft_path) != soft_hash or sha256(matrix_path) != matrix_hash:
        raise ValueError('Pinned source object hash mismatch')
    soft_raw = soft_path.read_bytes()
    samples = parse_geo_family_soft(soft_raw)

    # GSE159067's expression headers are explicitly repeated in Sample_description.
    descriptions = {}
    if cohort == 'gse159067':
        text = gzip.decompress(soft_raw).decode('utf-8')
        for match in re.finditer(r'(?ms)^\^SAMPLE = ([^\n]+)\n(.*?)(?=^\^SAMPLE = |\Z)', text):
            description = re.search(r'^!Sample_description = (.+)$', match[2], re.MULTILINE)
            if description:
                descriptions[match[1]] = description[1].strip()

    sample_by_matrix_id = {}
    parsed = {}
    selected_samples = []
    new_cohorts = {'gse93157', 'gse67501', 'gse122220', 'gse140901', 'gse111636'}
    for sample in samples:
        attrs = {x['key'].strip().lower(): x['value'].strip() for x in sample['characteristics']}
        title = sample['title'].strip()
        timing = 'PRE_TREATMENT' if cohort in new_cohorts else 'UNKNOWN'
        if cohort == 'gse140901':
            title_match = re.fullmatch(r'HCC\s+(S\d+)', title)
            matrix_id = title_match.group(1) if title_match else ''
        elif cohort in new_cohorts:
            matrix_id = sample['accession']
        elif cohort == 'gse159067':
            matrix_id = descriptions.get(sample['accession'], '')
            timing = 'PRE_TREATMENT'
        elif cohort in {'gse218989', 'gse145996'}:
            matrix_id = title
            if cohort == 'gse145996':
                timing = 'PRE_TREATMENT'
        else:
            matrix_id = title
            treatment = attrs.get('treatment', '').strip().lower()
            if treatment == 'pre ipilimumab':
                timing = 'PRE_TREATMENT'
            elif treatment == 'post ipilimumab':
                continue
            else:
                raise ValueError('GSE165278 sample has no recognized treatment timing')
        if not matrix_id or matrix_id in sample_by_matrix_id:
            raise ValueError('Missing or duplicate SOFT-to-expression sample link')
        sample_by_matrix_id[matrix_id] = sample
        parsed[sample['accession']] = attrs
        selected_samples.append((sample, matrix_id, timing))
    mapping = {matrix_id: sample['title'] for sample, matrix_id, _ in selected_samples}

    if cohort in new_cohorts:
        actual_headers = set(_geo_matrix_header(
            matrix_path, compressed=True, skip_hash_comment_rows=cohort == 'gse140901',
            series_matrix=cohort != 'gse140901')[1:])
        if actual_headers != set(mapping) or len(actual_headers) != len(mapping):
            raise ValueError('GEO expression columns do not map one-to-one through SOFT')

    probe_symbols = None
    unmapped_features = 0
    multi_probe_symbols = 0
    if cohort == 'gse111636':
        probe_symbols, unmapped_features, multi_probe_symbols = _gse111636_gene_map(soft_raw, matrix_path)
    if cohort == 'gse145996':
        cfg = {'format': 'MATRIX_HEADER_TSV', 'delimiter': '\t', 'compressed': True}
    elif cohort == 'gse165278':
        cfg = {'format': 'XLSX_NAMED_STREAM', 'delimiter': '\t', 'compressed': False,
               'sheet_name': 'Sheet 1', 'header_row': 1}
    else:
        cfg = {'format': 'MATRIX_HEADER_TSV', 'delimiter': '\t', 'compressed': True}
    if cohort in {'gse93157', 'gse67501', 'gse122220', 'gse111636'}:
        cfg['geo_series_matrix'] = True
    if cohort == 'gse140901':
        cfg['skip_hash_comment_rows'] = True
    if cohort == 'gse93157':
        cfg['skip_incomplete_features'] = True
    genes, duplicates = project_matrix(matrix_path, output / 'expression.tsv', mapping, cfg,
                                       skip_empty_features=cohort == 'gse165278')
    scale_summary = check_gse93157_scale(output / 'expression.tsv') if cohort == 'gse93157' else None
    probe_map_counts = None
    if cohort in {'gse67501', 'gse122220'}:
        probe_map_counts = write_probe_to_gene_map(
            soft_raw, output / 'expression.tsv', output / 'probe_to_gene.tsv')
    if cohort == 'gse111636':
        with (output / 'expression.tsv').open(newline='') as stream:
            reader = csv.reader(stream, delimiter='\t')
            next(reader)
            probes = [row[0] for row in reader]
        write_rows(output / 'probe_to_gene.tsv',
                   [{'probe_id': p, 'gene_symbol': probe_symbols.get(p, ''), 'entrez_id': ''} for p in probes],
                   ['probe_id', 'gene_symbol', 'entrez_id'])

    labels, label_hash = _nathanson_labels() if cohort == 'gse165278' else ({}, None)
    clinical = []
    for sample, _, timing in selected_samples:
        attrs = parsed[sample['accession']]
        response = attrs.get('best response on immunotherapy (recist)', '')
        binary = attrs.get('treatment outcome', '')
        extras = {}
        if cohort in new_cohorts:
            if cohort == 'gse93157':
                response = attrs.get('best.resp', '')
                orr, benefit = orr_category(response), 'UNKNOWN'
                cancer = {'MELANOMA': 'melanoma', 'LUNG NON-SQUAMOUS CANCER': 'lung non-squamous',
                          'SQUAMOUS LUNG CANCER': 'lung squamous', 'HEADNECK': 'head and neck'}.get(
                              sample.get('source_name_ch1', '').strip().upper(), 'UNKNOWN')
                extras = {'cancer': cancer, 'biopsy': attrs.get('biopsy', 'UNKNOWN')}
                pfs, pfs_event = attrs.get('pfs', ''), attrs.get('pfse', '')
                drug = attrs.get('drug', 'UNKNOWN').upper()
                endpoint_source = 'GEO SOFT characteristic: best.resp'
                endpoint_definition = 'ORR: CR/PR versus SD/PD; original best.resp category retained.'
                raw_orr, raw_benefit = response, ''
            elif cohort == 'gse67501':
                response_key = next((k for k in attrs if k.startswith('response to anti-pd-1') and '(complete response' in k), '')
                response = attrs.get(response_key, '')
                orr = 'R' if response.upper() in {'CR', 'PR'} else ('NR' if response.upper() in {'SD', 'NR'} else 'UNKNOWN')
                benefit = 'UNKNOWN'
                extras = {'specimen_origin': attrs.get('primary tumor or metastasis', 'UNKNOWN'),
                          'therapy_interval_months': attrs.get('interval between specimen collection and anti-pd1 therapy (months)', 'UNKNOWN')}
                pfs = pfs_event = ''
                drug = 'NIVOLUMAB'
                endpoint_source = 'GEO SOFT characteristic: CR/PR/SD/NR response field'
                endpoint_definition = 'ORR: CR/PR versus SD/NR; original category retained.'
                raw_orr, raw_benefit = response, ''
            elif cohort == 'gse122220':
                response_key = next((k for k in attrs if k.startswith('response (')), '')
                response = attrs.get(response_key, '')
                orr, benefit = orr_category(response), 'UNKNOWN'
                treatment = attrs.get('treatment', '').upper()
                drug = 'ANTI_CTLA4_PLUS_ANTI_PD1' if treatment == 'IPILIMUMAB+PD1' else 'ANTI_PD1'
                extras = {'previous_ipilimumab': attrs.get('previous ipilumimab', 'UNKNOWN')}
                pfs = pfs_event = ''
                endpoint_source = 'GEO SOFT characteristic: response (PD/SD/PR/CR)'
                endpoint_definition = 'ORR: CR/PR versus SD/PD; original category retained.'
                raw_orr, raw_benefit = response, ''
            elif cohort == 'gse140901':
                response = attrs.get('best_response', '')
                orr = orr_category(response)
                binary = attrs.get('clinical_benefit_response', '')
                benefit = {'YES': 'R', 'NO': 'NR'}.get(binary.upper(), 'UNKNOWN')
                extras = {'cancer': 'liver (HCC)'}
                pfs, pfs_event = attrs.get('pfs_time', ''), attrs.get('pfs_event', '')
                os_value, os_event = attrs.get('os_time', ''), attrs.get('os_event', '')
                drug = 'ICI_BASED_UNSPECIFIED'
                endpoint_source = 'GEO SOFT characteristics: best_response; clinical_benefit_response'
                endpoint_definition = 'ORR uses best_response (PR/SD/PD); separate SOURCE_BINARY clinical benefit uses clinical_benefit_response.'
                raw_orr, raw_benefit = response, binary
            else:
                binary = attrs.get('treatment response', '')
                orr = benefit = 'UNKNOWN'
                pfs = pfs_event = ''
                drug = 'ANTI_PD1'
                endpoint_source = 'GEO SOFT characteristic: treatment response'
                endpoint_definition = 'SOURCE_BINARY; responder/progressor source labels retained; SOFT does not define this as RECIST.'
                raw_orr, raw_benefit = '', ''
                extras['treatment_outcome'] = binary
            if cohort != 'gse140901':
                os_value, os_event = '', ''
        elif cohort == 'gse218989':
            benefit = 'UNKNOWN'
            orr = 'UNKNOWN'
            endpoint_source = 'GEO SOFT characteristic: treatment outcome'
            endpoint_definition = 'SOURCE_BINARY; raw GEO categories retained; no RECIST CR/PR evidence in SOFT.'
            raw_orr = ''
            raw_benefit = ''
        elif cohort == 'gse159067':
            orr = orr_category(response)
            benefit = 'UNKNOWN'
            endpoint_source = 'GEO SOFT characteristic: best response on immunotherapy (recist)'
            endpoint_definition = 'Best response on immunotherapy (RECIST), as named in GEO SOFT.'
            raw_orr = response
            raw_benefit = ''
        elif cohort == 'gse165278':
            # GEO titles are Nathanson 2017 Study IDs, with a '.n' suffix for extra lesions; join exactly.
            label = labels.get(sample['title'].split('.')[0])
            if label is None or label['Biopsy pre or post ipi'] != 'pre':
                raise ValueError('GSE165278 baseline sample without a matching pre-ipilimumab Nathanson 2017 row')
            orr = 'UNKNOWN'
            raw_benefit = label['Benefit']
            benefit = {'True': 'R', 'False': 'NR'}.get(raw_benefit, 'UNKNOWN')
            endpoint_source = 'Nathanson 2017 Online Data File 1 (cohort.csv), column Benefit'
            endpoint_definition = 'Clinical benefit: progression-free survival > 24 weeks after starting ipilimumab (Nathanson 2017). Not ORR.'
            raw_orr = ''
        else:
            orr = benefit = 'UNKNOWN'
            endpoint_source = 'No per-sample response characteristic in GEO SOFT'
            endpoint_definition = 'Response UNKNOWN; sample-title prefixes were not interpreted as response labels.'
            raw_orr = raw_benefit = ''
        if cohort not in new_cohorts:
            pfs = attrs.get('pfs (month)', '')
            os_value = attrs.get('os (month)', '')
        clinical.append({
            'patient_id': sample['title'], 'sample_id': sample['accession'],
            'timepoint': timing,
            'drug_class': drug if cohort in new_cohorts else {'gse218989': 'ANTI_PD_1_PD_L1', 'gse159067': 'ANTI_PD_1_PD_L1',
                           'gse145996': 'ANTI_PD_1', 'gse165278': 'ANTI_CTLA_4'}[cohort],
            'prior_ici': 'UNKNOWN', 'orr': orr, 'clinical_benefit': benefit,
            'pfs': (str(pfs) if cohort == 'gse93157' else f'{pfs} months') if pfs else 'UNKNOWN',
            'os': f'{os_value} months' if os_value else 'UNKNOWN',
            'pfs_event': pfs_event if cohort in new_cohorts else attrs.get('pfs (event)', ''),
            'os_event': os_event if cohort in new_cohorts else attrs.get('os (event)', ''),
            'hot_score': attrs.get('hot score', ''), 'hot_phenotype': attrs.get('hot phenotype', ''),
            'raw_orr': raw_orr, 'raw_clinical_benefit': raw_benefit,
            'treatment_outcome': binary if cohort == 'gse218989' else extras.get('treatment_outcome', ''),
            'endpoint_source': endpoint_source, 'endpoint_definition': endpoint_definition,
            **extras,
        })

    timing_notes = {
        'gse218989': 'SOFT does not state whether specimens were collected before treatment; timepoint is UNKNOWN.',
        'gse159067': 'Series overall design states biopsies/specimens were collected prior to treatment initiation.',
        'gse145996': 'Series overall design describes pre-immunotherapy tumors; SOFT has no per-sample response field.',
        'gse165278': 'Included only the 7 samples labelled pre ipilimumab; excluded 15 post ipilimumab samples from baseline. Post samples remain available for A.1.',
        'gse93157': 'SOFT biopsy labels distinguish BASELINE and ARCHIVAL specimens; archival specimens may substantially predate treatment.',
        'gse67501': 'SOFT specimen-to-nivolumab intervals are recorded in months; all are before therapy and some specimens predate therapy by several years.',
        'gse122220': 'SOFT labels all samples as pre-treatment.',
        'gse140901': 'The SOFT series design describes archival HCC tissue from patients receiving ICI; per-sample interval to treatment is not stated.',
        'gse111636': 'SOFT describes pretreatment bladder specimens; the treatment response field is patient-level and the samples are baseline.',
    }
    scale_notes = {
        'gse218989': 'Protein-coding TPM matrix; duplicate genes were already removed in the supplied object.',
        'gse159067': 'GEO-supplied log2 CPM targeted RNA panel; kept on its own scale, including control/probe rows.',
        'gse145996': 'GEO-supplied FPKM matrix; kept on its own scale. The matrix includes a Locus column, which is not used as expression.',
        'gse165278': 'GEO-supplied TPM XLSX, read with the repository standard-library XLSX reader; kept on its own scale.',
        'gse93157': 'log2, HK-normalised (5 HK genes) NanoString counts, as deposited. The log2 scale is inferred from the deposited value pattern; it is not explicit in the SOFT.',
        'gse67501': 'GEO SOFT says per-sample values were scaled to median 256 and log2 transformed; matrix values are retained on that claimed log2 scale.',
        'gse122220': 'GEO SOFT says probe values were quantile normalized, model-background adjusted, 3-MAD trimmed and averaged; matrix values are retained on this source scale.',
        'gse140901': 'GEO SOFT says counts were TMM normalized and converted to log2 CPM; the supplementary expression object is retained on that scale.',
        'gse111636': 'GEO SOFT says values were GCCN/SST normalized, summarized with RMA, then batch corrected with ComBat; the series-matrix values are retained on that claimed scale.',
    }
    response_notes = {
        'gse218989': 'Response source is the GEO SOFT field "treatment outcome" (Responder/Non-responder); no RECIST CR/PR definition was found, so this is SOURCE_BINARY and is not called ORR.',
        'gse159067': 'Response source is the GEO SOFT field "best response on immunotherapy (recist)"; OS/PFS times, event fields, hot score and hot phenotype are retained as supplied.',
        'gse145996': 'No per-sample response characteristic is present in the GEO SOFT; all response values remain UNKNOWN despite series-level responder-group summary.',
        'gse165278': 'GEO SOFT has no response field. Clinical benefit (PFS > 24 weeks) comes from Nathanson 2017 Online Data File 1 (hammerlab/melanoma-reanalysis cohort.csv, pinned commit), joined exactly by Study ID = GEO title; all 22 GEO samples match and GEO pre/post agrees with the table for every sample.',
        'gse93157': 'ORR uses GEO SOFT best.resp (CR/PR versus SD/PD). The separate SOFT characteristic response reports RC_RP_SD for 60 and PD for 5 and contradicts best.resp; it was not used.',
        'gse67501': 'ORR uses the GEO SOFT CR/PR/SD/NR characteristic as CR/PR versus SD/NR. The separate response/no-response characteristic was not substituted.',
        'gse122220': 'ORR uses the GEO SOFT response (PD/SD/PR/CR) characteristic; dual ipilimumab plus anti-PD-1 cases remain included and are identified by drug class.',
        'gse140901': 'ORR from best_response and SOURCE_BINARY clinical benefit from clinical_benefit_response are preserved as separate endpoints. SOFT names no per-patient drug; non-ICI combination exposure cannot be identified or excluded.',
        'gse111636': 'treatment response is retained as SOURCE_BINARY (responder/progressor). The SOFT does not define the field as RECIST, so it is not called ORR.',
    }
    if cohort == 'gse111636':
        feature_note = (f'Expression remains probe-level (all GPL17586 probes); probe_to_gene.tsv maps probes to symbols from the SOFT gene_assignment. '
                        f'{unmapped_features} probes have no single unambiguous symbol (blank in the map); '
                        f'{multi_probe_symbols} symbols have several probes. No probe collapse was applied.')
    elif cohort == 'gse93157':
        feature_note = f'Retained {genes} of 765 source feature rows; the 40 rows with no expression values were omitted without imputation. Duplicate identifiers among retained rows: {duplicates}.'
    else:
        feature_note = f'Retained all {genes} source feature rows, including {duplicates} duplicated feature identifiers; no aggregation or filtering was applied.'
    caveats = [scale_notes[cohort], timing_notes[cohort], response_notes[cohort], feature_note]
    if cohort == 'gse93157':
        caveats.append('Small cohort (65); four cancer arms remain in one cohort and are identified in the cancer column.')
        caveats.append(f"Scale inference: log2, HK-normalised (5 HK genes) NanoString counts, as deposited; values range {scale_summary['minimum']:.2f} to {scale_summary['maximum']:.2f}, median {scale_summary['median']:.2f}. The SOFT does not explicitly state log2; the few negative values ({scale_summary['negative_values']}) are consistent with log2 of very low normalised counts.")
    if cohort == 'gse67501':
        caveats.append('Small cohort (11); specimen-to-therapy intervals range from months to several years.')
        caveats.append(f"GPL14951 probe map: {probe_map_counts['mapped']} mapped, {probe_map_counts['unmapped']} without a symbol, {probe_map_counts['multi_probe_symbols']} symbols represented by multiple probes; expression remains probe-level.")
    if cohort == 'gse122220':
        caveats.append('Small cohort (10); eight anti-PD-1 monotherapy and two dual ipilimumab plus anti-PD-1 samples are retained.')
        caveats.append(f"GPL10558 probe map: {probe_map_counts['mapped']} mapped, {probe_map_counts['unmapped']} without a symbol, {probe_map_counts['multi_probe_symbols']} symbols represented by multiple probes; expression remains probe-level.")
    if cohort == 'gse140901':
        caveats.append('Small cohort (24); this is described as ICI-based therapy. GEO SOFT gives no per-patient regimen, so possible non-ICI combinations cannot be flagged.')
    if cohort == 'gse111636':
        caveats.append('Small cohort (11). The series matrix, rather than the unused CEL archive, is the expression source.')
    if cohort == 'gse165278':
        caveats.append('The response-looking sample-title prefixes are retained only as identifiers; treatment groups and response endpoints remain separate.')
        caveats.append('Rows with an empty gene identifier in the XLSX were omitted because they cannot be addressed as gene rows.')
        caveats.append('Same MSKCC ipilimumab cohort as Snyder 2014 / Nathanson 2017 (64 patients); any other loaded copy of that cohort overlaps. Small (7 baseline); prior ICI not recorded (ipilimumab era).')
        return clinical, genes, [soft_hash, matrix_hash, label_hash], caveats
    return clinical, genes, [soft_hash, matrix_hash], caveats


def _nathanson_labels():
    """Read the pinned Nathanson 2017 clinical table (Online Data File 1), keyed by Study ID."""
    store = safe_path(RUNTIME / 'gse165278' / 'store_labels')
    objects = json.loads(safe_path(store / 'MANIFEST.json').read_text())['objects']
    (digest, entry), = objects.items()
    path = safe_path(store / 'objects' / digest)
    if sha256(path) != digest or 'hammerlab/melanoma-reanalysis' not in entry['locator']:
        raise ValueError('Nathanson 2017 label object hash or source mismatch')
    rows = list(csv.DictReader(path.read_text().splitlines()))
    return unique_index(rows, 'Study ID'), digest


def _geo_rows(rows, *, series_matrix=False, skip_hash_comment_rows=False):
    active = not series_matrix
    for row in rows:
        marker = row[0].strip().lower() if row else ''
        if series_matrix and marker == '!series_matrix_table_begin':
            active = True
            continue
        if series_matrix and marker == '!series_matrix_table_end':
            break
        if not active:
            continue
        if skip_hash_comment_rows and (not row or not any(str(cell).strip() for cell in row)
                                       or row[0].strip().lstrip('"').startswith('#')):
            continue
        if skip_hash_comment_rows:
            while row and not str(row[-1]).strip():
                row.pop()
        yield row


def _geo_matrix_header(source, *, compressed, skip_hash_comment_rows=False, series_matrix=False):
    from tools.a_dav.matrix_header import matrix_rows
    with matrix_rows(source, delimiter='\t', compressed=compressed, source_format='MATRIX_HEADER_TSV') as rows:
        return next(_geo_rows(rows, series_matrix=series_matrix,
                              skip_hash_comment_rows=skip_hash_comment_rows))


def _gse111636_gene_map(soft_raw, matrix_path):
    import gzip
    from collections import Counter
    from tools.a_dav.matrix_header import matrix_rows
    text = gzip.decompress(soft_raw).decode('utf-8') if soft_raw.startswith(b'\x1f\x8b') else soft_raw.decode('utf-8')
    if '!platform_table_begin\n' not in text or '!platform_table_end' not in text:
        raise ValueError('GSE111636 SOFT has no platform annotation table')
    annotation = text.split('!platform_table_begin\n', 1)[1].split('!platform_table_end', 1)[0]
    rows = csv.DictReader(annotation.splitlines(), delimiter='\t')
    mapping = {}
    for row in rows:
        probe = (row.get('ID') or '').strip()
        symbols = set()
        for group in (row.get('gene_assignment') or '').split(' /// '):
            fields = group.split(' // ')
            if len(fields) > 1 and fields[1].strip() not in {'', '---', 'NULL'}:
                symbols.add(fields[1].strip())
        if probe and len(symbols) == 1:
            mapping[probe] = next(iter(symbols))
    with matrix_rows(matrix_path, delimiter='\t', compressed=True, source_format='MATRIX_HEADER_TSV') as matrix:
        matrix_rows_only = _geo_rows(matrix, series_matrix=True)
        next(matrix_rows_only)
        feature_ids = {row[0].strip('"') for row in matrix_rows_only if row}
    if not (feature_ids & set(mapping)):
        raise ValueError('GSE111636 SOFT platform annotation cannot map matrix probes to gene symbols')
    mapped = {probe: mapping[probe] for probe in feature_ids if probe in mapping}
    symbol_counts = Counter(mapped.values())
    multi_probe_symbols = sum(count > 1 for count in symbol_counts.values())
    return mapping, len(feature_ids - set(mapping)), multi_probe_symbols


def project_matrix(source, target, mapping, source_cfg, orientation='samples_as_columns',
                   skip_empty_features=False, skip_incomplete_features=False, feature_map=None):
    """Stream selected sample columns, with optional source feature mapping."""
    import sqlite3
    from tools.a_dav.matrix_header import matrix_rows
    dbpath = target.with_suffix('.sqlite')
    db = sqlite3.connect(dbpath)
    def check_values(values):
        try:
            numbers = [float(v) for v in values]
        except ValueError:
            raise ValueError('Expression contains non-numeric or non-finite values') from None
        if not all(math.isfinite(v) for v in numbers):
            raise ValueError('Expression contains non-numeric or non-finite values')
    try:
        db.execute('CREATE TABLE features (id TEXT, values_text TEXT)')
        if not mapping or len(set(mapping.values())) != len(mapping) or any(not x for x in mapping.values()):
            raise ValueError('Ambiguous patient mapping')
        with matrix_rows(source, delimiter=source_cfg.get('delimiter', '\t'),
                         compressed=source_cfg.get('compressed', False), source_format=source_cfg['format'],
                         sheet_name=source_cfg.get('sheet_name'), header_row=source_cfg.get('header_row', 1)) as rows:
            if source_cfg.get('skip_hash_comment_rows') or source_cfg.get('geo_series_matrix'):
                rows = _geo_rows(rows, series_matrix=source_cfg.get('geo_series_matrix', False),
                                 skip_hash_comment_rows=source_cfg.get('skip_hash_comment_rows', False))
            header = next(rows)
            if not header or len(set(header)) != len(header):
                raise ValueError('Duplicate or empty matrix header')
            if orientation == 'samples_as_rows':
                selected = {}
                for row in rows:
                    if len(row) != len(header):
                        raise ValueError('Malformed expression row')
                    if not row[0]:
                        if skip_empty_features:
                            continue
                        raise ValueError('Malformed expression row')
                    if row[0] in mapping:
                        if row[0] in selected:
                            raise ValueError('Duplicate sample row in expression')
                        selected[row[0]] = row[1:]
                if set(selected) != set(mapping):
                    raise ValueError('Selected sample rows missing from expression')
                columns = list(mapping)
                for i, gene in enumerate(header[1:]):
                    if not gene:
                        raise ValueError('Empty feature ID')
                    vals = [selected[c][i] for c in columns]
                    check_values(vals)
                    db.execute('INSERT INTO features VALUES (?,?)', (gene, '\t'.join(vals)))
            else:
                positions = {name: i for i, name in enumerate(header) if name in mapping}
                if set(positions) != set(mapping):
                    raise ValueError('Selected matrix columns missing')
                columns = list(mapping)
                for row in rows:
                    if len(row) != len(header):
                        raise ValueError('Malformed expression row')
                    if not row[0]:
                        if skip_empty_features:
                            continue
                        raise ValueError('Malformed expression row')
                    feature = feature_map.get(row[0], '') if feature_map is not None else row[0]
                    if not feature:
                        continue
                    vals = [row[positions[c]] for c in columns]
                    if not all(v and v.strip() for v in vals):
                        if skip_incomplete_features or source_cfg.get('skip_incomplete_features'):
                            continue
                        raise ValueError('Empty expression value')
                    check_values(vals)
                    db.execute('INSERT INTO features VALUES (?,?)', (feature, '\t'.join(vals)))
        db.commit()
        duplicates = db.execute('SELECT count(*) FROM (SELECT id FROM features GROUP BY id HAVING count(*)>1)').fetchone()[0]
        with target.open('w', newline='') as f:
            writer = csv.writer(f, delimiter='\t', lineterminator='\n')
            writer.writerow(['gene', *[mapping[c] for c in columns]])
            n = 0
            for gene, values in db.execute('SELECT id, values_text FROM features ORDER BY rowid'):
                writer.writerow([gene, *values.split('\t')]); n += 1
        return n, duplicates
    finally:
        db.close()
        dbpath.unlink(missing_ok=True)


def select_unique_assays(records, source_id):
    specimens = unique_index(records['specimen_registry'], 'specimen_uid')
    candidates = {}
    for a in records['assay_registry']:
        if a['source_object_id'] != source_id:
            continue
        specimen = specimens[a['specimen_uid']]
        if specimen.get('canonical_timing_category') in {'ON_TREATMENT', 'POST_TREATMENT'}:
            continue
        candidates.setdefault(specimen['patient_uid'], []).append(a)
    duplicates = sum(len(v) != 1 for v in candidates.values())
    selected = [(v[0]['matrix_header'], uid, v[0]) for uid, v in candidates.items() if len(v) == 1]
    if len({x[0] for x in selected}) != len(selected):
        raise ValueError('Ambiguous matrix header mapping')
    return {header: (uid, assay) for header, uid, assay in selected}, duplicates


def export_ingested(cohort, output):
    field_map = json.loads((ROOT / 'tools/a_dav/field_maps' / (cohort + '.json')).read_text())
    packet_path = safe_path(RUNTIME / cohort / 'ingest-20261030/records/ingestion_packet.json')
    if cohort == 'gide2019':
        packet_path = RUNTIME / cohort / 'admitted-20261030/fresh-ingest/records/ingestion_packet.json'
    records = json.loads(packet_path.read_text())['records']
    role = field_map['v3']['primary_representation']
    cfg = field_map['source_objects'][role].copy()
    cfg['delimiter'] = field_map['v3']['delimiters'][role]
    cfg['compressed'] = field_map['v3']['compressed'][role]
    source = safe_path(RUNTIME / cohort / 'store/objects' / cfg['sha256'])
    for obj in field_map['source_objects'].values():
        if obj.get('sha256'):
            objpath = safe_path(RUNTIME / cohort / 'store/objects' / obj['sha256'])
            if sha256(objpath) != obj['sha256']:
                raise ValueError('Pinned source object hash mismatch')
    with source.open('rb') as f:
        actual = hashlib.file_digest(f, 'sha256').hexdigest()
    if actual != cfg['sha256']:
        raise ValueError('Pinned expression object hash mismatch')
    if cohort == 'gide2019':
        pre = {x['specimen_uid'] for x in records['specimen_registry'] if x['canonical_timing_category'] == 'PRE_INDEX_BASELINE'}
        records['assay_registry'] = [x for x in records['assay_registry'] if x['specimen_uid'] in pre]
    candidates, duplicates = select_unique_assays(records, f'SOURCE:{cohort}:{role}')
    if not candidates:
        raise ValueError('No unambiguous expression samples')
    patient_data = unique_index(records['patient_registry'], 'patient_uid')
    outcomes = {}
    for o in records['clinical_outcome']:
        outcomes.setdefault(o['patient_uid'], []).append(o)
    exposures = {}
    for e in records.get('treatment_exposure', []):
        exposures.setdefault(e['patient_uid'], set()).add(e.get('pharmacological_class') or 'UNKNOWN')
    specimens = unique_index(records['specimen_registry'], 'specimen_uid')
    supplement = {}
    hashes = [v['sha256'] for v in field_map['source_objects'].values() if v.get('sha256')] + [sha256(packet_path), sha256(ROOT / 'tools/a_dav/field_maps' / (cohort + '.json'))]
    caveats = [f'Excluded {duplicates} patients with multiple candidate expression samples; no tie was guessed.']
    survival_by_patient = {}
    survival_by_sample = {}
    if cohort in {'gse135222', 'gse136961', 'gse176307'}:
        survival_by_sample = geo_survival(cohort, field_map)
        if cohort != 'gse136961': caveats.append('GEO survival values are retained as provided; units require source confirmation.')
    if cohort in {'vanallen2015', 'gide2019'}:
        survival_by_patient = cbio_survival(cohort, field_map)
    if cohort == 'braun2020':
        from tools.a_dav.cbioportal import read_workbook_inventory
        clinical_cfg = field_map['source_objects']['clinical']
        clinical_obj = RUNTIME / cohort / 'store/objects' / clinical_cfg['sha256']
        rows = read_workbook_inventory(clinical_obj, clinical_cfg['sheet_name'], clinical_cfg['header_row'], ['SUBJID', 'Arm', 'PFS', 'OS'])
        selected = [r for r in rows if r['Arm'].upper() == 'NIVOLUMAB']
        survival_by_patient = {r['SUBJID']: survival_from_source({'pfs': r['PFS'], 'os': r['OS']}, '') for r in selected}
        caveats.append('S1 PFS and OS values are retained as provided; their units require source confirmation.')
    if cohort == 'gide2019':
        from tools.a_dav.cbioportal import read_clinical, verified_author_links
        from tools.a_dav.xlsx import read_clinical_xlsx
        objs = field_map['source_objects']
        def obj(role): return (RUNTIME / cohort / 'store/objects' / objs[role]['sha256']).read_bytes()
        author = {arm: read_clinical_xlsx(obj(role), header_row=objs[role]['header_row']) for arm, role in [('mono', 'author_mmc2'), ('dual', 'author_mmc3')]}
        cbio = field_map['cbio_ingest']
        linked = verified_author_links(author, read_clinical(obj(cbio['patient_role'])), read_clinical(obj(cbio['sample_role'])))
        survival_by_patient.update({pid: survival_from_source({'pfs': x.get('Progression Free Survival (Days)', ''), 'os': x.get('Overall Survival (Days)', '')}, 'days') for pid, x in linked['links'].items()})
        caveats.append(f"Author-table linkage: {linked['matched_linked']} verified pairs; {linked['matched_without_rna']} matched patient without documented RNA uses cBioPortal fields only.")
        crosswalk, total_pre = gide_crosswalk(field_map, records)
        caveats.append(f'recount3 crosswalk pending: {len(crosswalk)}/{total_pre} PRE runs have one-to-one title-rule candidate matches; SRA attributes, title, sample and BioSample accessions contain no additional cBioPortal crosswalk. Using iAtlas log2 upper-quartile expression, with undocumented processing; use only on its own scale and report analyses without Gide.')
        caveats.append('Author clinical linkage is limited to the verified linked records; unlinked patients retain cBioPortal fields only.')
    if cohort == 'gse135222':
        stage = RUNTIME / cohort / 'staging-springer-20261030'
        provenance = json.loads((stage / 'supp_table3_extracted.provenance.json').read_text())
        with (stage / 'MOESM1.pdf').open('rb') as f:
            if hashlib.file_digest(f, 'sha256').hexdigest() != provenance['source_sha256']:
                raise ValueError('Supplement source hash mismatch')
        for s in read_rows(stage / 'supp_table3_extracted.tsv'):
            supplement.setdefault(s['sample_id'], []).append(s)
        with (stage / 'supp_table3_extracted.tsv').open('rb') as f:
            hashes.append(hashlib.file_digest(f, 'sha256').hexdigest())
        hashes.append(provenance['source_sha256'])
        caveats.append('Supplement Table 3 is coordinator-extracted from the hash-verified PDF; extracted labels require source review.')
    clinical = []
    unmatched = 0
    for column, (uid, assay) in candidates.items():
        specimen = specimens[assay['specimen_uid']]
        if cohort == 'gide2019':
            oo = outcomes.get(uid, [])
            category = orr_category(next((o['raw_endpoint_label'] for o in oo if o['endpoint_class'] == 'TUMOUR_RESPONSE'), 'UNKNOWN'))
            benefit = benefit_category(next((o['canonical_category'] for o in oo if o['endpoint_class'] == 'SOURCE_BINARY'), 'UNKNOWN'))
        else:
            category, benefit = source_outcomes(outcomes.get(uid, []), preserve_benefit=cohort == 'braun2020')
        title_prefix = ''
        if cohort == 'gse136961':
            title_prefix = str(patient_data[uid].get('source_patient_id', ''))[:1]
            benefit = {'D': 'DCB', 'N': 'NDB'}.get(title_prefix, 'UNKNOWN')
        if cohort == 'gse135222':
            matches = supplement.get(str(patient_data[uid].get('source_patient_id', '')), [])
            if len(matches) == 1:
                benefit = matches[0]['clinical_benefit'].upper()
                if benefit not in {'DCB', 'NDB'}: benefit = 'UNKNOWN'
            else:
                unmatched += 1; benefit = 'UNKNOWN'
        pd_event = matches[0]['pd_event'] if cohort == 'gse135222' and len(matches) == 1 else 'UNKNOWN'
        pfs = 'UNKNOWN'
        if cohort == 'gide2019':
            raw = next((o['raw_endpoint_label'] for o in outcomes.get(uid, []) if o['endpoint_class'] == 'SOURCE_BINARY'), '')
            match = re.search(r'PFS_DAYS=([^;]+)', raw)
            if match and match[1].strip().isdigit(): pfs = match[1].strip() + ' days'
        survival = survival_by_patient.get(patient_data[uid].get('source_patient_id', ''), survival_by_sample.get(assay['source_sample_id'], {}))
        pfs = survival.get('pfs', pfs)
        os_value = survival.get('os', 'UNKNOWN')
        timing = specimen.get('canonical_timing_category', 'UNKNOWN')
        clinical.append({'patient_id': uid, 'sample_id': assay['source_sample_id'],
                         'timepoint': 'PRE_TREATMENT' if timing == 'PRE_INDEX_BASELINE' else timing,
                         'drug_class': '+'.join(sorted(exposures.get(uid, {'UNKNOWN'}))), 'prior_ici': patient_data[uid].get('prior_ici') or 'UNKNOWN',
                         'orr': category, 'clinical_benefit': benefit, 'pd_event': pd_event, 'pfs': pfs, 'os': os_value,
                         'raw_orr': '|'.join(sorted({str(o.get('raw_endpoint_label', '')) for o in outcomes.get(uid, []) if o['endpoint_class'] in {'ORR', 'TUMOUR_RESPONSE'}})),
                         'raw_clinical_benefit': title_prefix if cohort == 'gse136961' else '|'.join(sorted({str(o.get('raw_endpoint_label', '')) for o in outcomes.get(uid, []) if o['endpoint_class'] == 'SOURCE_BINARY'})),
                         'endpoint_source': 'GEO title prefix D/N' if cohort == 'gse136961' else 'ingestion packet', 'endpoint_definition': '|'.join(sorted({str(o.get('assessment_criteria') or 'UNKNOWN') for o in outcomes.get(uid, [])}))})
    if cohort == 'gse135222': caveats.append(f'Exact GEO title sample ID to supplement sample_id join: {unmatched} expression samples unmatched or ambiguous; {len(supplement)} supplement sample IDs, including rows outside this expression set.')
    if cohort == 'gse136961':
        caveats.append('GEO title prefix D/N maps to DCB/NDB, respectively; five extra raw-count columns are not used.')
        from collections import Counter
        if Counter(c['clinical_benefit'] for c in clinical) != {'DCB': 9, 'NDB': 12}:
            raise ValueError('GSE136961 title prefix count mismatch')
    if cohort in {'gse135222', 'gse176307'}:
        caveats.append('Individual pretreatment timing is unverified; UNKNOWN timing is retained for review.')
    if cohort == 'braun2020':
        caveats.append('Expression is log2 upper-quartile-normalized TPM, ComBat-adjusted, with offset; not linear TPM. Archival samples.')
    output.mkdir(parents=True, exist_ok=True)
    orientation = field_map['measurement_representations'][role].get('orientation', 'samples_as_columns')
    if cohort == 'gide2019' and len(crosswalk) == total_pre:
        base = RUNTIME / cohort / 'recount3-reviewed-20261030'
        receipt = json.loads((base / 'PROVENANCE.json').read_text())
        if sha256(base / 'counts.tsv') != receipt['output_sha256']:
            raise ValueError('recount3 product hash mismatch')
        run_by_patient = {patient: run for run, patient in crosswalk.items()}
        if set(run_by_patient) != {r['patient_id'] for r in clinical}:
            raise ValueError('Complete recount3 crosswalk does not cover selected patients')
        mapping = {run_by_patient[r['patient_id']]: r['patient_id'] for r in clinical}
        source = base / 'counts.tsv'; cfg = {'format': 'MATRIX_HEADER_TSV'}; orientation = 'samples_as_columns'
        caveats[-2] = f'recount3 PRE crosswalk: {len(crosswalk)}/{total_pre} one-to-one title matches; approximate counts used.'
    else:
        mapping = {k: v[0] for k, v in candidates.items()}
    genes, duplicate_features = project_matrix(source, output / 'expression.tsv', mapping, cfg, orientation)
    caveats.append(f'Retained all feature rows, including {duplicate_features} duplicated feature identifiers; no aggregation or filtering was applied.')
    return clinical, genes, sorted(set(hashes)), caveats


