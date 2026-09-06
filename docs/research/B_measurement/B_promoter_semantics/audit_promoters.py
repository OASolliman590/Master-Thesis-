"""Offline candidate annotation audit. No patient matrices or outcome values read.

Python 3.11+ standard library. Candidates are versioned alternatives, not an
accepted promoter freeze. pc in policy IDs means the literal source label
protein_coding, not independently verified coding-transcript biotype.
Run from any directory; inputs resolve by this file.
"""
import collections
import csv
import gzip
import hashlib
import itertools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'B_annotation'
GENES = ('HLA-A', 'HLA-B', 'HLA-C', 'B2M', 'TAP1', 'TAP2', 'PSMB8', 'PSMB9')
INPUTS = {
    'HM450.hg38.manifest.gencode.v36.tsv.gz': 'cb908b2aa8f49b2c92e3698dc04c379607850c36c329f2ff24dc765af655e483',
    'HM450.hg38.mask.202209.tsv.gz': '5a02fa845578a0947ef1a80262d8514092f9c7690e37da0bc31b00f8f908e69d',
}
for name, expected in INPUTS.items():
    assert hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() == expected, name
with gzip.open(SOURCE / 'HM450.hg38.mask.202209.tsv.gz', 'rt', encoding='utf-8') as f:
    mask = {}
    for row in csv.DictReader(f, delimiter='\t'):
        assert row['probeID'] not in mask
        assert row['MASK_general'] in ('TRUE', 'FALSE')
        mask[row['probeID']] = row['MASK_general']

pair_rows, long_rows, example_rows = [], [], []
seen = set()
aligned_errors = []
gene_summary_disagreements = []
transcripts = collections.defaultdict(list)
sets = {policy: {g: set() for g in GENES} for policy in
        ('pc_abs1500', 'pc_abs200', 'all_biotypes_abs1500', 'pc_abs1500_unique_pc_gene')}
pre_mask = {g: set() for g in GENES}
naive = {g: set() for g in GENES}
all_pc_promoters = {}
target_association_count = collections.Counter()
with gzip.open(SOURCE / 'HM450.hg38.manifest.gencode.v36.tsv.gz', 'rt', encoding='utf-8') as f:
    for row in csv.DictReader(f, delimiter='\t'):
        probe = row['probeID']
        assert probe not in seen
        seen.add(probe)
        assert probe in mask
        arrays = [row[k].split(';') for k in ('geneNames', 'transcriptTypes', 'transcriptIDs', 'distToTSS')]
        if len(set(map(len, arrays))) != 1:
            aligned_errors.append(probe)
            continue
        zipped = list(zip(*arrays))
        if set(row['genesUniq'].split(';')) != set(arrays[0]):
            gene_summary_disagreements.append(probe)
        if not set(arrays[0]) & set(GENES):
            continue
        assert row['CpG_chrm'] != '*'
        assert int(row['CpG_end']) - int(row['CpG_beg']) == (2 if probe.startswith('cg') else 1)
        valid = [(g, t, tx, int(d)) for g, t, tx, d in zipped]
        pc_promoters = sorted({g for g, t, tx, d in valid if t == 'protein_coding' and abs(d) <= 1500})
        all_pc_promoters[probe] = pc_promoters
        for g in sorted(set(arrays[0]) & set(GENES)):
            target_association_count[g] += 1
            matching = [(t, tx, d) for gn, t, tx, d in valid if gn == g]
            pc = [(tx, d) for t, tx, d in matching if t == 'protein_coding']
            cg = probe.startswith('cg')
            eligible = mask[probe] == 'FALSE' and cg
            in1500 = cg and any(abs(d) <= 1500 for tx, d in pc)
            in200 = cg and any(abs(d) <= 200 for tx, d in pc)
            if in1500:
                pre_mask[g].add(probe)
            if eligible:
                if in1500: sets['pc_abs1500'][g].add(probe)
                if in200: sets['pc_abs200'][g].add(probe)
                if any(abs(d) <= 1500 for t, tx, d in matching): sets['all_biotypes_abs1500'][g].add(probe)
                if in1500 and pc_promoters == [g]: sets['pc_abs1500_unique_pc_gene'][g].add(probe)
                if any(t == 'protein_coding' and abs(d) <= 1500 for gn, t, tx, d in valid): naive[g].add(probe)
            pair_rows.append({'probe_id': probe, 'gene_symbol': g, 'chr': row['CpG_chrm'],
                              'cpg_beg_0based': row['CpG_beg'], 'cpg_end': row['CpG_end'],
                              'mask_general_202209': mask[probe],
                              'pc_abs1500_pre_mask': in1500, 'pc_abs200_pre_mask': in200,
                              'cognate_pc_transcripts': ';'.join(tx for tx, d in pc),
                              'cognate_pc_distances': ';'.join(str(d) for tx, d in pc),
                              'all_gene_associations': row['genesUniq'],
                              'pc_promoter_gene_assignments_abs1500': ';'.join(pc_promoters)})
            for t, tx, d in matching:
                transcripts[(g, tx, t)].append((int(row['CpG_beg']), d, probe))
                long_rows.append({'probe_id': probe, 'gene_symbol': g, 'transcript_id_versioned': tx,
                                  'transcriptTypes_source': t, 'distToTSS_source': d,
                                  'mask_general_202209': mask[probe],
                                  'pc_abs1500_candidate': cg and t == 'protein_coding' and abs(d) <= 1500})

def write_tsv(name, rows):
    with (ROOT / name).open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter='\t', lineterminator='\n')
        w.writeheader(); w.writerows(rows)

write_tsv('probe_gene_candidates.tsv', sorted(pair_rows, key=lambda x: (x['gene_symbol'], x['probe_id'])))
write_tsv('cognate_transcript_evidence.tsv', sorted(long_rows, key=lambda x: (x['gene_symbol'], x['probe_id'], x['transcript_id_versioned'])))
ids = [{'policy_id': policy, 'gene_symbol': gene, 'probe_id': probe}
       for policy in sets for gene in GENES for probe in sorted(sets[policy][gene])]
write_tsv('candidate_probe_ids.tsv', ids)
overlap = []
for g, h in itertools.combinations(GENES, 2):
    shared = sorted(sets['pc_abs1500'][g] & sets['pc_abs1500'][h])
    if shared: overlap.append({'gene1': g, 'gene2': h, 'shared_n': len(shared), 'probe_ids': shared})
tx_summary = []
for (g, tx, typ), rows in sorted(transcripts.items()):
    p_plus_d = {p + d for p, d, probe in rows}
    p_minus_d = {p - d for p, d, probe in rows}
    if len({p for p, d, probe in rows}) < 2: relation = 'insufficient_distinct_positions'
    elif len(p_plus_d) == 1: relation = 'CpG_beg_plus_dist_is_constant'
    elif len(p_minus_d) == 1: relation = 'CpG_beg_minus_dist_is_constant'
    else: relation = 'neither_constant'
    tx_summary.append({'gene': g, 'transcript': tx, 'biotype': typ, 'probe_count': len(rows),
                       'algebraic_relation_only': relation,
                       'inferred_anchor_coordinate_not_independent_TSS_validation':
                           next(iter(p_plus_d)) if relation == 'CpG_beg_plus_dist_is_constant' else
                           next(iter(p_minus_d)) if relation == 'CpG_beg_minus_dist_is_constant' else None})
summary = {
    'status': 'CANDIDATE OPTIONS ONLY; no primary, annotation or probe-QC freeze approved',
    'policy_label_semantics': 'pc denotes transcriptTypes source field equals protein_coding; not verified transcript coding biotype',
    'input_rows': len(seen), 'mask_rows': len(mask), 'aligned_field_errors': aligned_errors,
    'genesUniq_summary_disagreements': gene_summary_disagreements,
    'target_probe_gene_rows': len(pair_rows), 'target_transcript_rows': len(long_rows),
    'counts': {g: {'associated': target_association_count[g], 'pc_abs1500_pre_mask': len(pre_mask[g]),
                   **{policy: len(sets[policy][g]) for policy in sets},
                   'naive_any_transcript_then_all_row_genes_count': len(naive[g]),
                   'naive_incorrect_extra_ids': sorted(naive[g] - sets['pc_abs1500'][g])} for g in GENES},
    'shared_target_promoter_probes_abs1500': overlap,
    'unique_abs1500_probe_count_across_family': len(set.union(*sets['pc_abs1500'].values())),
    'sum_abs1500_gene_memberships': sum(map(len, sets['pc_abs1500'].values())),
    'distance_algebra': tx_summary,
    'source_sha256': INPUTS,
    'scope': 'Annotation and historical mask only. No TCGA/CPC methylation or expression data read.',
}
(ROOT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: v for k, v in summary.items() if k not in ('distance_algebra', 'shared_target_promoter_probes_abs1500')}, indent=2))
print('shared targets:', [(x['gene1'], x['gene2'], x['shared_n']) for x in overlap])
