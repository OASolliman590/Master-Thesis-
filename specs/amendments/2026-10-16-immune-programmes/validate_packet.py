"""Read-only specification checks; never loads biological data or computes scores."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
def sha(b):
    return hashlib.sha256(b).hexdigest()
def check_registry(reg):
    assert reg['data_analysis_execution_granted'] is False
    assert reg['primary_replacement'] is False
    ids = [p['id'] for p in reg['programmes']]
    assert len(ids) == len(set(ids))
    for p in reg['programmes']:
        assert p['scientific_release'] is False
        assert p['pending_gates'] and p['source_ids']
        genes = p['membership']
        if genes is None:
            assert p['membership_sha256'] is None
            assert p['scoring_status'] == 'NO_SCORE_AUTHORIZED' or p['id'] == 'HALLMARK_INTERFERON_GAMMA_RESPONSE'
        else:
            assert len(genes) == len(set(genes))
            assert p['membership_sha256'] == sha(json.dumps(genes, separators=(',', ':'), ensure_ascii=False).encode())
    rows = {p['id']: p for p in reg['programmes']}
    for pid in ('HOPE_18', 'AYERS_GEP_18', 'APM_WANG_18'):
        assert len(rows[pid]['membership']) == 18
    old = json.loads((ROOT/'specs/B/gene_set_registry.proposed.json').read_text())
    for p in old['programs']:
        assert rows[p['id']]['membership'] == p['raw_gene_symbols']
    assert set(rows['P_ANTIGEN_PRESENTATION']['membership']) < set(rows['APM_WANG_18']['membership'])
    assert '0.01' in rows['CYT_ROONEY_OFFSET_REFERENCE']['scoring_status']
    assert 'no pseudocount' in rows['CYT_FROZEN_UNOFFSET']['scoring_status']
    return len(ids)

def main():
    reg = json.loads((HERE/'programme_registry.v1.json').read_text())
    n = check_registry(reg)
    rejected = 0
    for mutation in ('release', 'genes', 'hash', 'primary'):
        r = json.loads(json.dumps(reg))
        if mutation == 'release': r['programmes'][0]['scientific_release'] = True
        if mutation == 'genes': r['programmes'][0]['membership'].append('FAKE')
        if mutation == 'hash': r['programmes'][0]['membership_sha256'] = '0'*64
        if mutation == 'primary': r['primary_replacement'] = True
        try: check_registry(r)
        except AssertionError: rejected += 1
        else: raise AssertionError('Invalid mutation accepted: '+mutation)
    frozen = json.loads((ROOT/'docs/integration/20261015/FREEZE_MANIFEST.json').read_text())
    for item in frozen['files']:
        b = (ROOT/item['path']).read_bytes()
        assert sha(b) == item['sha256'], item['path']
        assert len(b) == item['bytes'], item['path']
    provenance = json.loads((HERE/'legacy_provenance.json').read_text())
    copies = 0
    for rec in provenance['records']:
        assert rec['git_blob_match'] and rec['upstream_commit'] == '96c16794bafc8946ae9f0bdcef81d5f3a599542b'
        if rec['archive_copy']:
            b=(HERE/rec['archive_copy']).read_bytes()
            assert sha(b)==rec['local_receipt_sha256']
            assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==rec['upstream_blob_sha1']
            copies += 1
    print(json.dumps({'result':'PASS','programmes':n,'negative_mutations_rejected':rejected,'rc2_manifest_files_unchanged':len(frozen['files']),'legacy_copies_verified':copies,'biology_executed':False},indent=2))

if __name__ == '__main__':
    main()
