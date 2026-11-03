"""Build the frozen panel features from locally available, qualified inputs."""
import csv
import gzip
import json
import math
import os
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path

from tools.a_cohorts.core import ROOT, RUNTIME, gide_crosswalk, read_rows, safe_path, sha256, write_rows
from tools.a_cohorts.view import REPRESENTATION_FILE, _loader_runtime, cohort_view
from tools.a_dav.geo_soft import parse_geo_family_soft
from tools.a_scoring import (
    ALIAS_TABLE_PATH, DEFAULT_PANELS, PANEL_REGISTRY_PATH, cyt, endpoint_label,
    gene_info_path, log2p1, panel_scores, recount3_to_tpm, resolve, to_tpm,
)
from tools.a_scoring.core import COHORT_REGISTRY_PATH, panel_definitions

COHORTS = ('liu2019', 'hugo_gse78220', 'riaz_gse91061', 'vanallen2015', 'kim2018', 'gse176307', 'gide2019')
PANELS = DEFAULT_PANELS
ROUTES = {'liu2019': 'author_TPM', 'hugo_gse78220': 'author_FPKM_to_TPM', 'riaz_gse91061': 'author_FPKM_to_TPM', 'vanallen2015': 'author_FPKM_like_to_TPM', 'kim2018': 'recount3_counts_to_TPM', 'gse176307': 'Salmon_TPM', 'gide2019': 'recount3_counts_to_TPM'}
REGISTRY = PANEL_REGISTRY_PATH
ALIASES = ALIAS_TABLE_PATH
GTF_HASH = '2d1bdff8d91e08f1291fd47850d9d61cfa6768cc3a4cb8516775a873b007d0f6'


def accepted_gide_pairs(proposal, patients, loader_pairs):
    runs = Counter(r['run'] for r in proposal)
    patient_counts = Counter(r['patient'] for r in proposal)
    result = {}
    for row in proposal:
        run, patient = row['run'], row['patient']
        uid = patients.get(patient)
        if uid and runs[run] == patient_counts[patient] == 1 and loader_pairs.get(run) == uid:
            result[uid] = run
    return result


def _runtime_path(runtime=None):
    selected = runtime if runtime is not None else os.environ.get('THESIS_RUNTIME', RUNTIME)
    return Path(selected).expanduser()


def _safe_runtime_path(path, runtime):
    path = Path(path).expanduser()
    runtime = Path(runtime).expanduser()
    resolved_runtime = runtime.resolve()
    resolved = path.resolve()
    if not resolved.is_relative_to(resolved_runtime):
        raise ValueError('Runtime path escapes selected THESIS_RUNTIME')
    current = path
    while current != runtime and current != current.parent:
        if current.is_symlink():
            raise ValueError('Symlink in runtime path')
        current = current.parent
    if not resolved.is_file():
        raise FileNotFoundError(path)
    return resolved


def _safe_input_path(path, runtime=None):
    path = Path(path).expanduser()
    runtime = _runtime_path(runtime)
    try:
        path.resolve().relative_to(runtime.resolve())
    except ValueError:
        return safe_path(path)
    return _safe_runtime_path(path, runtime)


def gide_mapping(inputs, runtime=None):
    runtime = _runtime_path(runtime)
    base = runtime / 'gide2019'
    field = source(ROOT / 'tools/a_dav/field_maps/gide2019.json', inputs, runtime)
    cfg = json.loads(field.read_text())
    packet = source(base / 'admitted-20261030/fresh-ingest/records/ingestion_packet.json', inputs, runtime)
    records = json.loads(packet.read_text())['records']
    source(base / 'store-recount3/objects/f882e68caf9309a25e77b509a2c071229a034f8468d889bca7892122be71b61a', inputs, runtime)
    role = cfg['cbio_ingest']['sample_role']
    source(base / 'store/objects' / cfg['source_objects'][role]['sha256'], inputs, runtime)
    with _loader_runtime(runtime):
        loader_pairs, _ = gide_crosswalk(cfg, records)
    patients = {r['source_patient_id']: r['patient_uid'] for r in records['patient_registry']}
    proposal = read_rows(source(base / 'recount3-reviewed-20261030/unaccepted_identity_proposal.tsv', inputs, runtime))
    if len(proposal) != 60:
        raise ValueError('accepted Gide proposal must contain 60 PRE runs')
    return accepted_gide_pairs(proposal, patients, loader_pairs)

def matrix(path, selected, runtime=None):
    path = _safe_input_path(path, runtime)
    opener = gzip.open if path.name in {'c7ebf750cc6e6ba967bba9a733c47572a53daaaff9fcf041e5ab4641ef615894'} else open
    symbols, retained = [], []
    with opener(path, 'rt', newline='') as f:
        reader = csv.reader(f, delimiter='\t')
        header = next(reader)
        if len(set(header[1:])) != len(header)-1:
            raise ValueError('duplicate expression columns')
        positions = [header.index(x) for x in selected]
        for row in reader:
            if len(row) != len(header):
                raise ValueError('malformed expression row')
            values = [float(row[i]) for i in positions]
            if any(not math.isfinite(x) or x < 0 for x in values):
                raise ValueError('invalid abundance')
            symbols.append(row[0])
            retained.append(values)
    return symbols, retained


def source(path, inputs, runtime=None):
    runtime = _runtime_path(runtime)
    path = _safe_input_path(path, runtime)
    digest = sha256(path)
    if len(path.name) == 64 and all(c in '0123456789abcdef' for c in path.name) and digest != path.name:
        raise ValueError('pinned source hash mismatch')
    try:
        key = str(path.relative_to(ROOT))
    except ValueError:
        key = str(path.relative_to(runtime.resolve().parent.parent)) if path.is_relative_to(runtime.resolve().parent.parent) else str(path)
    inputs[key] = digest
    return path


def gse_mapping(clinical, inputs, runtime=None):
    runtime = _runtime_path(runtime)
    base = runtime / 'gse176307'
    packet = source(base / 'ingest-20261030/records/ingestion_packet.json', inputs, runtime)
    records = json.loads(packet.read_text())['records']
    field = source(ROOT / 'tools/a_dav/field_maps/gse176307.json', inputs, runtime)
    cfg = json.loads(field.read_text())
    soft = source(base / 'store/objects' / cfg['source_objects']['geo_family_soft']['sha256'], inputs, runtime)
    titles = {x['accession']: x['title'].split()[-1] for x in parse_geo_family_soft(soft.read_bytes())}
    by_patient = {p['patient_uid']: p['source_patient_id'] for p in records['patient_registry']}
    key = source(base / 'store_tpm/objects/cfe452ec72c99f2c84216bb25fe291b4c78028e53b8a8189acbd5c9ed7db919b', inputs, runtime)
    with gzip.open(key, 'rt', newline='') as f:
        rows = list(csv.DictReader(f))
    assays = defaultdict(list)
    for row in rows: assays[row['Sample ID']].append(row['Omniseq_RS_ID (RNAseq)'])
    result = {}
    for row in clinical:
        pid = row['patient_id']; code = by_patient[pid]
        if titles.get(row['sample_id']) != code:
            raise ValueError('GEO title to patient mismatch')
        if code in assays:
            result[pid] = min(assays[code])
    if len(set(result.values())) != len(result): raise ValueError('ambiguous assay join')
    return result


def _a_p2_representation(cohort, view):
    if cohort == 'gide2019':
        return {'platform': 'rnaseq', 'unit': 'counts', 'transform': 'linear'}
    if cohort == 'gse176307':
        return {'platform': 'rnaseq', 'unit': 'tpm', 'transform': 'linear'}
    return view


def build(runtime=None, out=None):
    runtime = _runtime_path(runtime)
    inputs = {}
    for path in (REGISTRY, ALIASES, COHORT_REGISTRY_PATH, REPRESENTATION_FILE, gene_info_path(runtime)):
        source(path, inputs, runtime)
    panels = panel_definitions(PANELS)
    targets = {gene for panel in PANELS for gene in panels[panel]} | {'GZMA', 'PRF1'}
    all_features, coverage = [], []
    columns = ['cohort', 'patients_in', 'excluded_timing', 'excluded_response', 'excluded_no_assay', 'excluded_cohort', 'final_n', 'R', 'NR', 'tpm_route', 'primary_assembly_rows_dropped', 'tpm_sum_check', 'tpm_max_abs_sum_error', 'found_genes', 'missing_genes', *[p + '_' + state for p in (*PANELS, 'CYT') for state in ('found', 'missing')], 'aliases_used', 'added_aliases', 'reason']
    for cohort in COHORTS:
        base = runtime / cohort
        source(base / 'simple/clinical.tsv', inputs, runtime)
        view = cohort_view(cohort, runtime)
        clinical = view.clinical_rows
        if len({r['patient_id'] for r in clinical}) != len(clinical): raise ValueError(cohort + ': duplicate patients')
        result = dict(cohort=cohort, patients_in=len(clinical), excluded_timing=0, excluded_response=0, excluded_no_assay=0, excluded_cohort=0, final_n=0, R=0, NR=0, tpm_route=ROUTES[cohort], found_genes='', missing_genes='', aliases_used='', reason='')
        try:
            # Van Allen et al., Science 2015, PMC5054517: the study's tumour
            # transcriptomes were obtained from pretreatment tumour samples.
            timing = [r for r in clinical if r['timepoint'] == 'PRE_TREATMENT'
                      or (cohort == 'vanallen2015' and r['timepoint'] == 'UNKNOWN')]
            result['excluded_timing'] = len(clinical)-len(timing)
            labels, excluded = endpoint_label(replace(view, clinical_rows=timing), 'orr')
            label_by_patient = {row['patient_id']: label for row, label in zip(timing, labels)}
            result['excluded_response'] = sum(excluded.values())
            eligible = [row for row, label in zip(timing, labels) if label is not None]
            if cohort == 'gse176307':
                mapping = gse_mapping(clinical, inputs, runtime)
                path = base / 'store_tpm/objects/c7ebf750cc6e6ba967bba9a733c47572a53daaaff9fcf041e5ab4641ef615894'
            elif cohort == 'gide2019':
                mapping = gide_mapping(inputs, runtime)
                path = base / 'recount3-reviewed-20261030/counts.tsv'
            else:
                mapping = {r['patient_id']: r['patient_id'] for r in clinical}
                path = view.expression_path
            path = source(path, inputs, runtime)
            with (gzip.open(path, 'rt') if cohort == 'gse176307' else path.open()) as f:
                headers = set(f.readline().rstrip('\n').split('\t')[1:])
            chosen = [r for r in eligible if mapping.get(r['patient_id']) in headers]
            result['excluded_no_assay'] = len(eligible)-len(chosen)
            selected = [mapping[r['patient_id']] for r in chosen]
            symbols, values = matrix(path, selected, runtime=runtime)
            if cohort in {'kim2018', 'gide2019'}:
                gtf = source(base / 'store-recount3/objects' / GTF_HASH, inputs, runtime)
                symbols, tpm, dropped = recount3_to_tpm(symbols, values, gtf)
                result['primary_assembly_rows_dropped'] = dropped
            else:
                tpm = to_tpm(values, _a_p2_representation(cohort, view))
            logged = log2p1(tpm)
            index, target_coverage = resolve(symbols, targets, runtime=runtime)
            missing = targets - index.keys()
            used = {
                str(details['resolved_symbol']) + '->' + gene
                for gene, details in target_coverage.items()
                if details['resolution'] == 'alias'
            }
            result['found_genes'] = ','.join(sorted(index))
            result['missing_genes'] = ','.join(sorted(missing))
            for panel in (*PANELS, 'CYT'):
                genes = set(panels[panel] if panel != 'CYT' else ['GZMA', 'PRF1'])
                result[panel + '_found'] = ','.join(sorted(genes & index.keys()))
                result[panel + '_missing'] = ','.join(sorted(genes - index.keys()))
            added = {
                str(details['resolved_symbol']) + '->' + gene
                for gene, details in target_coverage.items()
                if details['resolution'] == 'synonym'
            }
            result['added_aliases'] = ','.join(sorted(added))
            result['aliases_used'] = ','.join(sorted(used))
            if missing: raise ValueError('missing required genes: ' + ','.join(sorted(missing)))
            if cohort in {'kim2018', 'gide2019'}:
                errors = [abs(math.fsum(row[j] for row in tpm) - 1e6)
                          for j in range(len(chosen))]
                if any(error > 1e-6 for error in errors):
                    raise ValueError('recount3 TPM sum differs from 1000000')
                result['tpm_sum_check'] = 'PASS' if errors else 'NOT_CHECKED'
                result['tpm_max_abs_sum_error'] = max(errors) if errors else ''
            for j, row in enumerate(chosen):
                gene_values = {gene: tpm[index[gene]][j] for gene in index}
                logged_values = {gene: logged[index[gene]][j] for gene in index}
                scores, _ = panel_scores(logged_values, panels)
                if any(scores[panel] is None for panel in PANELS):
                    raise ValueError('incomplete panel coverage after aliases')
                cls = 'R' if label_by_patient[row['patient_id']] == 1 else 'NR'
                feature = {'cohort': cohort, 'patient_id': row['patient_id'], 'cancer': view.metadata.cancer, 'orr_raw': row['raw_orr'], 'orr_class': cls, 'CYT': cyt(gene_values['GZMA'], gene_values['PRF1']), 'tpm_route': ROUTES[cohort]}
                feature.update({panel: scores[panel] for panel in PANELS})
                all_features.append(feature); result[cls] += 1
            result['final_n'] = len(chosen)
            if not chosen: result['reason'] = 'no eligible baseline patients; timing is unverified' if not timing else 'no eligible response and assay joins'
        except (ValueError, KeyError, OSError) as exc:
            result['reason'] = str(exc)
            result['excluded_cohort'] = len(clinical)-result['excluded_timing']-result['excluded_response']-result['excluded_no_assay']
        coverage.append(result)
    outdir = safe_path(Path(out).expanduser() if out is not None else RUNTIME / 'a_p2/inputs')
    outdir.mkdir(parents=True, exist_ok=True)
    feature_path = outdir / 'features.tsv'; coverage_path = outdir / 'coverage.tsv'
    write_rows(feature_path, all_features, ['cohort', 'patient_id', 'cancer', 'orr_raw', 'orr_class', *PANELS, 'CYT', 'tpm_route'])
    write_rows(coverage_path, coverage, columns)
    code = [Path(__file__), Path(__file__).with_name('__main__.py'), Path(__file__).with_name('__init__.py'), ROOT / 'tools/a_cohorts/core.py', ROOT / 'tools/a_cohorts/view.py', ROOT / 'tools/a_dav/cbioportal.py', ROOT / 'tools/a_dav/geo_soft.py', ROOT / 'tools/a_scoring/core.py', ROOT / 'tools/a_scoring/__init__.py']
    manifest = {'recount3_gene_length_method': 'Pinned G026 gene row column 6 (GTF score), recount3 bp_length in base pairs. TPM denominator includes only chr1-22, chrX, chrY and chrM gene rows; every sample sum is checked against 1000000.', 'vanallen_timing_override': 'Study-level pretreatment tumour samples; Van Allen et al., Science 2015, https://pmc.ncbi.nlm.nih.gov/articles/PMC5054517/', 'input_sha256': inputs, 'code_sha256': {str(p.relative_to(ROOT)): sha256(p) for p in code}, 'output_sha256': {p.name: sha256(p) for p in (feature_path, coverage_path)}}
    (outdir / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    print('Wrote', outdir)
    for row in coverage: print(row['cohort'], 'N=', row['final_n'], 'R=', row['R'], 'NR=', row['NR'], row['reason'])

    return feature_path, coverage_path
