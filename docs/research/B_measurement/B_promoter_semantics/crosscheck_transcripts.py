"""Offline GENCODE-v36 target transcript comparison; no patient data/analysis.

Uses cached UCSC genePred locus responses, not a downloaded full annotation.
Positive CDS span is an explicit candidate rule, not a canonical-transcript or
transcript-biotype designation. Does not change the original candidate policy.
"""
import collections
import csv
import hashlib
import itertools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
tx = {}
receipts = []
for f in sorted(ROOT.glob('ucsc_gencode_v36_*.json')):
    content = f.read_bytes()
    d = json.loads(content)
    assert d['genome'] == 'hg38' and d['track'] == 'wgEncodeGencodeCompV36'
    rows = d['wgEncodeGencodeCompV36']
    assert d['itemsReturned'] == len(rows)
    for row in rows:
        if row['name'] in tx: assert tx[row['name']] == row
        tx[row['name']] = row
    receipts.append({'file': f.name, 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest(),
                     'dataTime': d.get('dataTime'), 'downloadTime': d.get('downloadTime'),
                     'url': 'https://api.genome.ucsc.edu/getData/track?genome=hg38;track=wgEncodeGencodeCompV36;'
                            f"chrom={d['chrom']};start={d['start']};end={d['end']}"})
with (ROOT / 'probe_gene_candidates.tsv').open(encoding='utf-8') as f:
    pair_rows = list(csv.DictReader(f, delimiter='\t'))
with (ROOT / 'cognate_transcript_evidence.tsv').open(encoding='utf-8') as f:
    long_rows = list(csv.DictReader(f, delimiter='\t'))
positions = {r['probe_id']: (r['chr'], int(r['cpg_beg_0based'])) for r in pair_rows}
candidate = collections.defaultdict(set)
target_transcripts = collections.defaultdict(set)
evidence = {}
distance_mismatches = []
for row in long_rows:
    t = tx[row['transcript_id_versioned']]
    gene = row['gene_symbol']
    assert t['name2'] == gene
    chrom, beg = positions[row['probe_id']]
    assert t['chrom'] == chrom
    assert t['strand'] in ('+', '-')
    # Preserve source boundary convention: minus-strand anchor is txEnd,
    # not txEnd-1. This reproduces the manifest's signed distance exactly.
    anchor = t['txStart'] if t['strand'] == '+' else t['txEnd']
    expected_distance = beg - anchor if t['strand'] == '+' else anchor - beg
    if expected_distance != int(row['distToTSS_source']): distance_mismatches.append(row)
    cds = t['cdsStart'] < t['cdsEnd']
    target_transcripts[gene].add(t['name'])
    evidence[t['name']] = {'gene_symbol': gene, 'transcript_id_versioned': t['name'],
                          'manifest_transcriptTypes_literal': row['transcriptTypes_source'],
                          'strand': t['strand'], 'txStart_0based': t['txStart'], 'txEnd_exclusive': t['txEnd'],
                          'cdsStart': t['cdsStart'], 'cdsEnd': t['cdsEnd'], 'positive_CDS_span': cds,
                          'source_distance_anchor': anchor}
    if (row['probe_id'].startswith('cg') and cds and abs(expected_distance) <= 1500
            and row['mask_general_202209'] == 'FALSE'):
        candidate[gene].add(row['probe_id'])

with (ROOT / 'transcript_coordinate_CDS_evidence.tsv').open('w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(next(iter(evidence.values()))), delimiter='\t', lineterminator='\n')
    w.writeheader(); w.writerows(sorted(evidence.values(), key=lambda r: (r['gene_symbol'], r['transcript_id_versioned'])))
with (ROOT / 'CDS_bearing_candidate_probe_ids.tsv').open('w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, delimiter='\t', lineterminator='\n'); w.writerow(['policy_id', 'gene_symbol', 'probe_id'])
    for g in sorted(candidate):
        for probe in sorted(candidate[g]): w.writerow(['gencode36_positive_CDS_span_abs1500', g, probe])
base = json.loads((ROOT / 'summary.json').read_text(encoding='utf-8'))
original = {g: {r['probe_id'] for r in pair_rows if r['gene_symbol'] == g
               and r['pc_abs1500_pre_mask'] == 'True' and r['mask_general_202209'] == 'FALSE'} for g in target_transcripts}
result = {
    'status': 'PROPOSED metadata-only alternative; no primary/promoter/mask choice approved',
    'versioned_transcripts_joined': len(evidence), 'missing_target_transcripts': [],
    'probe_transcript_rows_compared': len(long_rows), 'distance_mismatches': distance_mismatches,
    'gene_counts': {g: {'source_pc_label_transcripts': len(ids),
                       'positive_CDS_span_transcripts': sum(evidence[t]['positive_CDS_span'] for t in ids),
                       'zero_CDS_span_transcripts': sum(not evidence[t]['positive_CDS_span'] for t in ids),
                       'source_pc_label_candidates': len(original[g]), 'positive_CDS_span_candidates': len(candidate[g]),
                       'source_only_probe_ids': sorted(original[g] - candidate[g]),
                       'CDS_only_probe_ids': sorted(candidate[g] - original[g])}
                    for g, ids in sorted(target_transcripts.items())},
    'shared_target_CDS_candidates': [{'gene1': g, 'gene2': h, 'n': len(candidate[g] & candidate[h]),
                                    'probe_ids': sorted(candidate[g] & candidate[h])}
                                   for g, h in itertools.combinations(sorted(candidate), 2) if candidate[g] & candidate[h]],
    'candidate_unique_probes': len(set.union(*candidate.values())),
    'candidate_gene_memberships': sum(map(len, candidate.values())),
    'receipts': receipts,
    'limitations': 'CDS span is not exact transcript biotype or canonical/MANE designation; only target-locus metadata checked. No patient matrices or outcomes used.',
}
(ROOT / 'CDS_crosscheck_summary.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: v for k, v in result.items() if k not in ('receipts', 'shared_target_CDS_candidates')}, indent=2))
print('CDS overlap:', [(r['gene1'], r['gene2'], r['n']) for r in result['shared_target_CDS_candidates']])
