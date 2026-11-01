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

SUPPORTED_COHORTS = set(ADMITTED) | {'gse135222', 'gse136961', 'gse176307', 'braun2020', 'vanallen2015', 'gide2019', 'kim2018'}

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
        receipt = json.loads((base / 'PROVENANCE.json').read_text())
        if sha256(base / 'counts.tsv') != receipt['output_sha256'] or sha256(base / 'sample_inventory.tsv') != receipt['inventory_sha256']:
            raise ValueError('recount3 product hash mismatch')
        hashes = []
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
    for name, expected in manifest['output_sha256'].items():
        if name not in {'expression.tsv', 'clinical.tsv', 'caveats.md'} or sha256(safe_path(output / name)) != expected:
            raise ValueError('Output hash mismatch')
    if set(manifest['output_sha256']) != {'expression.tsv', 'clinical.tsv', 'caveats.md'}:
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
        else:
            clinical, genes, hashes, caveats = export_ingested(cohort, stage)
        columns = ['patient_id', 'sample_id', 'timepoint', 'drug_class', 'prior_ici', 'orr', 'clinical_benefit', 'pd_event', 'pfs', 'os', 'raw_orr', 'raw_clinical_benefit', 'endpoint_source', 'endpoint_definition']
        write_rows(stage / 'clinical.tsv', clinical, columns)
        (stage / 'caveats.md').write_text('# Caveats\n\n- ' + '\n- '.join([row['caveats'], *caveats]) + '\n')
        manifest = {'cohort': cohort, 'loader_version': VERSION, 'input_sha256': hashes,
                    'patients': len(clinical), 'genes': genes,
                    'status': 'ADMITTED' if cohort in ADMITTED else 'PENDING_BATCH_REVIEW', 'input_files': inputs,
                    'output_sha256': {name: sha256(stage / name) for name in ('expression.tsv', 'clinical.tsv', 'caveats.md')}}
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
    mapping = {r['external_id']: r['sample_title'] for r in inventory}
    output.mkdir(parents=True, exist_ok=True)
    genes, duplicates = project_matrix(base / 'counts.tsv', output / 'expression.tsv', mapping, {'format': 'MATRIX_HEADER_TSV'})
    clinical = [{'patient_id': r['sample_title'], 'sample_id': r['external_id'], 'timepoint': 'UNKNOWN', 'drug_class': 'ANTI_PD_1', 'prior_ici': 'UNKNOWN', 'orr': 'UNKNOWN', 'clinical_benefit': 'UNKNOWN', 'pfs': 'UNKNOWN', 'os': 'UNKNOWN'} for r in inventory]
    return clinical, genes, [sha256(base / x) for x in ('counts.tsv', 'sample_inventory.tsv', 'PROVENANCE.json')], [f'{len(inventory)} distinct tumour-labelled sample titles are provisional patient identifiers; patient identity and pretreatment timing are unverified. No response source; all ORR UNKNOWN. recount3 approximate counts; Megadepth version unknown. Duplicate gene IDs: {duplicates}.']


def project_matrix(source, target, mapping, source_cfg, orientation='samples_as_columns'):
    """Stream projected columns and retain every source feature row."""
    import sqlite3
    from tools.a_dav.matrix_header import matrix_rows
    dbpath = target.with_suffix('.sqlite')
    db = sqlite3.connect(dbpath)
    def check_values(values):
        try:
            if not all(math.isfinite(float(v)) for v in values):
                raise ValueError
        except ValueError:
            raise ValueError('Expression contains non-numeric or non-finite values') from None
    try:
        db.execute('CREATE TABLE features (id TEXT, values_text TEXT)')
        if not mapping or len(set(mapping.values())) != len(mapping) or any(not x for x in mapping.values()):
            raise ValueError('Ambiguous patient mapping')
        with matrix_rows(source, delimiter=source_cfg.get('delimiter', '\t'),
                         compressed=source_cfg.get('compressed', False), source_format=source_cfg['format'],
                         sheet_name=source_cfg.get('sheet_name'), header_row=source_cfg.get('header_row', 1)) as rows:
            header = next(rows)
            if not header or len(set(header)) != len(header):
                raise ValueError('Duplicate or empty matrix header')
            if orientation == 'samples_as_rows':
                selected = {}
                for row in rows:
                    if len(row) != len(header) or not row[0]:
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
                    if len(row) != len(header) or not row[0]:
                        raise ValueError('Malformed expression row')
                    vals = [row[positions[c]] for c in columns]
                    if not all(v and v.strip() for v in vals):
                        raise ValueError('Empty expression value')
                    check_values(vals)
                    db.execute('INSERT INTO features VALUES (?,?)', (row[0], '\t'.join(vals)))
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


