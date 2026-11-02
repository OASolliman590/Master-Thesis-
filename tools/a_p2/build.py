"""Build the frozen panel features from locally available, qualified inputs."""
import csv
import gzip
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

from tools.a_cohorts.core import ROOT, RUNTIME, gide_crosswalk, read_rows, safe_path, sha256, write_rows
from tools.a_dav.geo_soft import parse_geo_family_soft

COHORTS = ('liu2019', 'hugo_gse78220', 'riaz_gse91061', 'vanallen2015', 'kim2018', 'gse176307', 'gide2019')
PANELS = ('P_ANTIGEN_PRESENTATION', 'M2_CYTOTOXICITY', 'M3_VIRAL_MIMICRY', 'M4_EXCLUSION')
ROUTES = {'liu2019': 'author_TPM', 'hugo_gse78220': 'author_FPKM_to_TPM', 'riaz_gse91061': 'author_FPKM_to_TPM', 'vanallen2015': 'author_FPKM_like_to_TPM', 'kim2018': 'recount3_counts_to_TPM', 'gse176307': 'Salmon_TPM', 'gide2019': 'recount3_counts_to_TPM'}
REGISTRY = ROOT / 'specs/amendments/2026-10-16-immune-programmes/programme_registry.v1.json'
ALIASES = ROOT / 'specs/amendments/2026-11-02-paper-a-validation/gene_aliases.tsv'
INFO = RUNTIME / 'reference_gene_maps/store/objects/d332c8dcc76b0fc052dd7d66b17479b63e40f6b199f2eb40e5f7ea2fa59371dc'
GTF_HASH = '2d1bdff8d91e08f1291fd47850d9d61cfa6768cc3a4cb8516775a873b007d0f6'


def fpkm_to_tpm(values):
    if any(not math.isfinite(x) or x < 0 for x in values) or sum(values) <= 0:
        raise ValueError('invalid abundance or zero denominator')
    total = sum(values)
    return [x * 1e6 / total for x in values]


def counts_to_tpm(counts, lengths):
    if len(counts) != len(lengths) or any(not math.isfinite(x) or x <= 0 for x in lengths):
        raise ValueError('missing or invalid gene length')
    return fpkm_to_tpm([x / length for x, length in zip(counts, lengths)])


def panel_mean(values):
    return sum(math.log2(x + 1) for x in values) / len(values)


def cyt(gzma, prf1):
    return math.sqrt(gzma * prf1)


def resolve_genes(symbols, targets, aliases, synonyms):
    mapped = defaultdict(list)
    for i, symbol in enumerate(symbols):
        mapped[aliases.get(symbol, symbol)].append(i)
    added = {}
    for target in targets:
        if not mapped[target]:
            candidates = [i for i, symbol in enumerate(symbols) if symbol in synonyms.get(target, set())]
            if len(candidates) == 1:
                mapped[target] = candidates
                added[target] = symbols[candidates[0]]
        if len(mapped[target]) > 1:
            raise ValueError('duplicate rows for required gene ' + target)
    return {gene: indices[0] for gene, indices in mapped.items() if gene in targets and indices}, added



def exon_annotation(path):
    intervals = defaultdict(list)
    names, locations = {}, {}
    with gzip.open(path, 'rt') as f:
        for line in f:
            if line.startswith('#'):
                continue
            fields = line.rstrip('\n').split('\t')
            if len(fields) != 9:
                raise ValueError('malformed GTF row')
            if fields[2] != 'exon':
                continue
            attrs = dict(re.findall(r'(\w+) "([^"]+)"', fields[8]))
            gene = attrs.get('gene_id'); name = attrs.get('gene_name')
            if not gene or not name:
                raise ValueError('exon missing gene_id or gene_name')
            location = (fields[0], fields[6])
            if (gene in locations and locations[gene] != location) or (gene in names and names[gene] != name):
                raise ValueError('inconsistent exon annotation for gene')
            start, end = int(fields[3]), int(fields[4])
            if start < 1 or end < start:
                raise ValueError('invalid exon coordinates')
            names[gene] = name; locations[gene] = location
            intervals[gene].append((start, end))
    if not intervals:
        raise ValueError('pinned G026 GTF contains no exon rows; exon-union lengths unavailable')
    lengths = {}
    for gene, parts in intervals.items():
        merged = []
        for start, end in sorted(parts):
            if merged and start <= merged[-1][1] + 1:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        lengths[gene] = sum(end - start + 1 for start, end in merged)
    return lengths, names



def recount_annotation(path):
    primary = {f'chr{x}' for x in (*range(1, 23), 'X', 'Y', 'M')}
    annotation = {}
    with gzip.open(path, 'rt') as f:
        for line in f:
            if line.startswith('#'):
                continue
            fields = line.rstrip('\n').split('\t')
            if len(fields) != 9:
                raise ValueError('malformed GTF row')
            if fields[2] != 'gene':
                continue
            attrs = dict(re.findall(r'(\w+) "([^"]+)"', fields[8]))
            gene, name = attrs.get('gene_id'), attrs.get('gene_name')
            if not gene or not name or gene in annotation:
                raise ValueError('missing or duplicate GTF gene identifier or symbol')
            is_primary = fields[0] in primary
            if is_primary:
                try:
                    length = float(fields[5])
                except ValueError:
                    raise ValueError('invalid recount3 gene length') from None
                if not math.isfinite(length) or length <= 0:
                    raise ValueError('invalid recount3 gene length')
            else:
                length = None
            annotation[gene] = (name, length, is_primary)
    if not annotation:
        raise ValueError('GTF contains no gene rows')
    return annotation

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


def gide_mapping(inputs):
    base = RUNTIME / 'gide2019'
    field = source(ROOT / 'tools/a_dav/field_maps/gide2019.json', inputs)
    cfg = json.loads(field.read_text())
    packet = source(base / 'admitted-20261030/fresh-ingest/records/ingestion_packet.json', inputs)
    records = json.loads(packet.read_text())['records']
    source(base / 'store-recount3/objects/f882e68caf9309a25e77b509a2c071229a034f8468d889bca7892122be71b61a', inputs)
    role = cfg['cbio_ingest']['sample_role']
    source(base / 'store/objects' / cfg['source_objects'][role]['sha256'], inputs)
    loader_pairs, _ = gide_crosswalk(cfg, records)
    patients = {r['source_patient_id']: r['patient_uid'] for r in records['patient_registry']}
    proposal = read_rows(source(base / 'recount3-reviewed-20261030/unaccepted_identity_proposal.tsv', inputs))
    if len(proposal) != 60:
        raise ValueError('accepted Gide proposal must contain 60 PRE runs')
    return accepted_gide_pairs(proposal, patients, loader_pairs)

def read_info():
    by_id, synonyms = {}, defaultdict(set)
    with gzip.open(safe_path(INFO), 'rt') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            by_id[row['GeneID']] = row['Symbol']
            synonyms[row['Symbol']].update(row['Synonyms'].split('|'))
    return by_id, synonyms


def matrix(path, selected, mapper, annotation=None):
    opener = gzip.open if path.name in {'c7ebf750cc6e6ba967bba9a733c47572a53daaaff9fcf041e5ab4641ef615894'} else open
    symbols, retained, totals, dropped = [], [], [0.] * len(selected), 0
    with opener(safe_path(path), 'rt', newline='') as f:
        reader = csv.reader(f, delimiter='\t')
        header = next(reader)
        if len(set(header[1:])) != len(header)-1:
            raise ValueError('duplicate expression columns')
        positions = [header.index(x) for x in selected]
        for row in reader:
            if len(row) != len(header):
                raise ValueError('malformed expression row')
            if annotation is not None:
                if row[0] not in annotation:
                    raise ValueError('matrix gene missing from recount3 annotation')
                symbol, length, is_primary = annotation[row[0]]
                if not is_primary:
                    dropped += 1
                    continue
            values = [float(row[i]) for i in positions]
            if any(not math.isfinite(x) or x < 0 for x in values):
                raise ValueError('invalid abundance')
            if annotation is not None:
                values = [x / length for x in values]
            for i, x in enumerate(values): totals[i] += x
            symbols.append(symbol if annotation is not None else mapper.get(row[0], row[0]) if mapper is not None else row[0])
            retained.append(values)
    return symbols, retained, totals, dropped


def source(path, inputs):
    path = safe_path(path)
    digest = sha256(path)
    if len(path.name) == 64 and all(c in '0123456789abcdef' for c in path.name) and digest != path.name:
        raise ValueError('pinned source hash mismatch')
    inputs[str(path.relative_to(ROOT))] = digest
    return path


def gse_mapping(clinical, inputs):
    base = RUNTIME / 'gse176307'
    packet = source(base / 'ingest-20261030/records/ingestion_packet.json', inputs)
    records = json.loads(packet.read_text())['records']
    field = source(ROOT / 'tools/a_dav/field_maps/gse176307.json', inputs)
    cfg = json.loads(field.read_text())
    soft = source(base / 'store/objects' / cfg['source_objects']['geo_family_soft']['sha256'], inputs)
    titles = {x['accession']: x['title'].split()[-1] for x in parse_geo_family_soft(soft.read_bytes())}
    by_patient = {p['patient_uid']: p['source_patient_id'] for p in records['patient_registry']}
    key = source(base / 'store_tpm/objects/cfe452ec72c99f2c84216bb25fe291b4c78028e53b8a8189acbd5c9ed7db919b', inputs)
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


def build():
    inputs = {}
    for p in (REGISTRY, ALIASES, INFO): source(p, inputs)
    panels = {p['id']: p['membership'] for p in json.loads(REGISTRY.read_text())['programmes'] if p['id'] in PANELS}
    targets = set(sum((panels[x] for x in PANELS), []) + ['GZMA', 'PRF1'])
    aliases = {r['source_symbol']: r['registry_symbol'] for r in read_rows(ALIASES)}
    ids, synonyms = read_info()
    all_features, coverage = [], []
    columns = ['cohort', 'patients_in', 'excluded_timing', 'excluded_response', 'excluded_no_assay', 'excluded_cohort', 'final_n', 'R', 'NR', 'tpm_route', 'primary_assembly_rows_dropped', 'tpm_sum_check', 'tpm_max_abs_sum_error', 'found_genes', 'missing_genes', *[p + '_' + state for p in (*PANELS, 'CYT') for state in ('found', 'missing')], 'aliases_used', 'added_aliases', 'reason']
    for cohort in COHORTS:
        base = RUNTIME / cohort
        clinical = read_rows(source(base / 'simple/clinical.tsv', inputs))
        if len({r['patient_id'] for r in clinical}) != len(clinical): raise ValueError(cohort + ': duplicate patients')
        result = dict(cohort=cohort, patients_in=len(clinical), excluded_timing=0, excluded_response=0, excluded_no_assay=0, excluded_cohort=0, final_n=0, R=0, NR=0, tpm_route=ROUTES[cohort], found_genes='', missing_genes='', aliases_used='', reason='')
        try:
            # Van Allen et al., Science 2015, PMC5054517: the study's tumour
            # transcriptomes were obtained from pretreatment tumour samples.
            timing = [r for r in clinical if r['timepoint'] == 'PRE_TREATMENT'
                      or (cohort == 'vanallen2015' and r['timepoint'] == 'UNKNOWN')]
            result['excluded_timing'] = len(clinical)-len(timing)
            eligible = [r for r in timing if r['orr'] in {'CR', 'PR', 'SD', 'PD'}]
            result['excluded_response'] = len(timing)-len(eligible)
            if cohort == 'gse176307':
                mapping = gse_mapping(clinical, inputs)
                path = base / 'store_tpm/objects/c7ebf750cc6e6ba967bba9a733c47572a53daaaff9fcf041e5ab4641ef615894'
            elif cohort == 'gide2019':
                mapping = gide_mapping(inputs)
                path = base / 'recount3-reviewed-20261030/counts.tsv'
            else:
                mapping = {r['patient_id']: r['patient_id'] for r in clinical}
                path = base / 'simple/expression.tsv'
            path = source(path, inputs)
            with (gzip.open(path, 'rt') if cohort == 'gse176307' else path.open()) as f:
                headers = set(f.readline().rstrip('\n').split('\t')[1:])
            chosen = [r for r in eligible if mapping.get(r['patient_id']) in headers]
            result['excluded_no_assay'] = len(eligible)-len(chosen)
            selected = [mapping[r['patient_id']] for r in chosen]
            annotation = None
            mapper = ids if cohort in {'riaz_gse91061', 'vanallen2015'} else None
            if cohort in {'kim2018', 'gide2019'}:
                gtf = source(base / 'store-recount3/objects' / GTF_HASH, inputs)
                annotation = recount_annotation(gtf)
            symbols, values, totals, dropped = matrix(path, selected, mapper, annotation)
            if annotation is not None:
                result['primary_assembly_rows_dropped'] = dropped
            index, added = resolve_genes(symbols, targets, aliases, synonyms)
            missing = targets - index.keys()
            used = {symbols[i] + '->' + gene for gene, i in index.items() if symbols[i] != gene}
            result['found_genes'] = ','.join(sorted(index))
            result['missing_genes'] = ','.join(sorted(missing))
            for panel in (*PANELS, 'CYT'):
                genes = set(panels[panel] if panel != 'CYT' else ['GZMA', 'PRF1'])
                result[panel + '_found'] = ','.join(sorted(genes & index.keys()))
                result[panel + '_missing'] = ','.join(sorted(genes - index.keys()))
            result['added_aliases'] = ','.join(sorted(v + '->' + k for k, v in added.items()))
            result['aliases_used'] = ','.join(sorted(used))
            if missing: raise ValueError('missing required genes: ' + ','.join(sorted(missing)))
            if any(t <= 0 for t in totals): raise ValueError('zero normalization denominator')
            if annotation is not None:
                errors = [abs(math.fsum(v[j] * (1e6 / total) for v in values) - 1e6)
                          for j, total in enumerate(totals)]
                if any(error > 1e-6 for error in errors):
                    raise ValueError('recount3 TPM sum differs from 1000000')
                result['tpm_sum_check'] = 'PASS' if errors else 'NOT_CHECKED'
                result['tpm_max_abs_sum_error'] = max(errors) if errors else ''
            for j, row in enumerate(chosen):
                mult = 1e6/totals[j] if cohort in {'hugo_gse78220', 'riaz_gse91061', 'vanallen2015', 'kim2018', 'gide2019'} else 1
                gene_values = {g: values[i][j] * mult for g, i in index.items()}
                cls = 'R' if row['orr'] in {'CR', 'PR'} else 'NR'
                out = {'cohort': cohort, 'patient_id': row['patient_id'], 'cancer': 'gastric' if cohort == 'kim2018' else 'bladder' if cohort == 'gse176307' else 'melanoma', 'orr_raw': row['raw_orr'], 'orr_class': cls, 'CYT': cyt(gene_values['GZMA'], gene_values['PRF1']), 'tpm_route': ROUTES[cohort]}
                out.update({p: panel_mean([gene_values[g] for g in panels[p]]) for p in PANELS})
                all_features.append(out); result[cls] += 1
            result['final_n'] = len(chosen)
            if not chosen: result['reason'] = 'no eligible baseline patients; timing is unverified' if not timing else 'no eligible response and assay joins'
        except (ValueError, KeyError, OSError) as exc:
            result['reason'] = str(exc)
            result['excluded_cohort'] = len(clinical)-result['excluded_timing']-result['excluded_response']-result['excluded_no_assay']
        coverage.append(result)
    outdir = safe_path(RUNTIME / 'a_p2/inputs'); outdir.mkdir(parents=True, exist_ok=True)
    feature_path = outdir / 'features.tsv'; coverage_path = outdir / 'coverage.tsv'
    write_rows(feature_path, all_features, ['cohort', 'patient_id', 'cancer', 'orr_raw', 'orr_class', *PANELS, 'CYT', 'tpm_route'])
    write_rows(coverage_path, coverage, columns)
    code = [Path(__file__), Path(__file__).with_name('__main__.py'), Path(__file__).with_name('__init__.py'), ROOT / 'tools/a_cohorts/core.py', ROOT / 'tools/a_dav/cbioportal.py', ROOT / 'tools/a_dav/geo_soft.py']
    manifest = {'recount3_gene_length_method': 'Pinned G026 gene row column 6 (GTF score), recount3 bp_length in base pairs. TPM denominator includes only chr1-22, chrX, chrY and chrM gene rows; every sample sum is checked against 1000000.', 'vanallen_timing_override': 'Study-level pretreatment tumour samples; Van Allen et al., Science 2015, https://pmc.ncbi.nlm.nih.gov/articles/PMC5054517/', 'input_sha256': inputs, 'code_sha256': {str(p.relative_to(ROOT)): sha256(p) for p in code}, 'output_sha256': {p.name: sha256(p) for p in (feature_path, coverage_path)}}
    (outdir / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    print('Wrote', outdir)
    for row in coverage: print(row['cohort'], 'N=', row['final_n'], 'R=', row['R'], 'NR=', row['NR'], row['reason'])
