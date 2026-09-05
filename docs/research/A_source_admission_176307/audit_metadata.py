"""Offline identity/header audit; never computes expression scores or effects."""
from pathlib import Path
import collections
import csv
import gzip
import hashlib
import io
import json
import re
import zlib

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parents[1] / 'feasibility' / 'GSE176307_metadata.json'
SOFT = SOURCE.parent / 'source_metadata' / 'GSE176307_family.soft.gz'
data = json.loads(SOURCE.read_text(encoding='utf-8'))
by_patient = collections.defaultdict(list)
for sample in data['samples']:
    fields = dict(s.split(': ', 1) for s in sample['characteristics'] if ': ' in s)
    patient = re.fullmatch(r'Patient sample (BACI\d+)(?:_[12])?', sample['title'][0]).group(1)
    by_patient[patient].append({'gsm': sample['id'], 'title': sample['title'][0],
                               'response': fields['io.response'], 'therapy': fields['io.therapy']})
key_bytes = gzip.decompress((ROOT / 'GSE176307_BACI_Omniseq_Sample_Name_Key_submitted_GEO_v2.csv.gz').read_bytes())
key = [r for r in csv.DictReader(io.StringIO(key_bytes.decode())) if r['Sample ID']]
rs_to_patient = {}
for row in key:
    for rs in row['Omniseq_RS_ID (RNAseq)'].split(','):
        assert rs not in rs_to_patient
        rs_to_patient[rs] = row['Sample ID']
header_audits = {}
for name in ['GSE176307_salmon_tpm_gene.matrix.tsv.gz',
             'GSE176307_baci_rsem_RS_BACI_headers_tab.txt.gz',
             'GSE176307_BACI_log_trans_normalized_RNAseq.csv.gz']:
    raw = zlib.decompressobj(31).decompress((ROOT / (name + '.prefix')).read_bytes())
    complete = b'\n' in raw
    first = raw.split(b'\n')[0].rstrip(b'\r')
    assert (ROOT / (name + '.header.txt')).read_bytes().rstrip(b'\r\n') == first
    header = next(csv.reader([first.decode()], delimiter=',' if '.csv.' in name else '\t'))
    item = {'complete_header': complete, 'identifier_header': header[0], 'data_columns': len(header) - 1,
            'unique_data_columns': len(set(header[1:])), 'header_sha256': hashlib.sha256(first).hexdigest()}
    if '.csv.' not in name:
        item.update({'unmapped_rs': sorted(set(header[1:]) - set(rs_to_patient)),
                     'key_rs_missing': sorted(set(rs_to_patient) - set(header[1:]))})
    else:
        item['orientation'] = 'gene columns; sample rows (row identities not audited)'
        item['cyt_gene_header_presence'] = {g: g in header[1:] for g in ['GZMA', 'PRF1']}
    header_audits[name] = item
soft = gzip.decompress(SOFT.read_bytes()).decode()
soft_gsms = re.findall(r'^\^SAMPLE = (GSM\d+)\s*$', soft, re.M)
assert set(soft_gsms) == {s['id'] for s in data['samples']}
audit = {
    'scope': 'Identifiers, metadata labels and complete headers only. No expression scores, models or effects.',
    'gsm_count': len(data['samples']), 'soft_gsm_count': len(soft_gsms), 'patient_codes': len(by_patient),
    'record_label_counts': dict(collections.Counter(v['response'] for vs in by_patient.values() for v in vs)),
    'patient_label_counts': dict(collections.Counter(v[0]['response'] for v in by_patient.values())),
    'duplicate_patients': {k: v for k, v in by_patient.items() if len(v) > 1},
    'unknown_response_patients': [k for k, v in by_patient.items() if v[0]['response'] == 'NA'],
    'key_rows': len(key), 'key_unique_rs_ids': len(rs_to_patient),
    'key_patient_missing_in_gsm': sorted(set(rs_to_patient.values()) - set(by_patient)),
    'gsm_patient_missing_in_key': sorted(set(by_patient) - set(rs_to_patient.values())),
    'therapy_patient_counts': dict(collections.Counter(v[0]['therapy'] for v in by_patient.values())),
    'headers': header_audits,
    'cached_sources': [{'path': str(p), 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                       for p in [SOURCE, SOFT]],
}
(ROOT / 'metadata_audit.json').write_text(json.dumps(audit, indent=2) + '\n', encoding='utf-8')
print(json.dumps(audit, indent=2))
