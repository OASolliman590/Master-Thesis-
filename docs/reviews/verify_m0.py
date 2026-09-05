"""Independent recount of cached public metadata. No scientific outcome analysis."""
import collections
import csv
import gzip
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
b = root / 'docs/research/B_paired_prostate'
c = root / 'docs/research/C_pharmacology_contracts'
records = json.loads((b / 'geo_samples.json').read_text())
meth = {x['patient_id'] for x in records['GSE107298'] if x['patient_id']}
expr = {x['patient_id'] for x in records['GSE107299'] if x['patient_id']}
paired = meth & expr
exported = list(csv.DictReader((b/'CPCG_patient_pairs.tsv').open(), delimiter='\t'))
assert len(exported) == len(paired) == 210
assert {x['patient_code'] for x in exported} == paired
gdc = json.loads((b/'gdc_files.json').read_text())
cases = collections.defaultdict(set)
samples = collections.defaultdict(set)
for f in gdc['data']['hits']:
    if f['access'] != 'open':
        continue
    for case in f.get('cases', []):
        for sample in case.get('samples', []):
            if sample['sample_type'] == 'Primary Tumor':
                cases[f['data_type']].add(case['submitter_id'])
                samples[f['data_type']].add(sample['submitter_id'])
assert len(set.intersection(*cases.values())) == 497
assert len(set.intersection(*samples.values())) == 501
with gzip.open(c/'GSE70138_Broad_LINCS_sig_info_2017-03-06.txt.gz', 'rt') as f:
    signatures = list(csv.DictReader(f, delimiter='\t'))
assert len(signatures) == 118050
prostate = collections.Counter(x['cell_id'] for x in signatures if x['pert_type']=='trt_cp' and x['cell_id'] in {'PC3','LNCAP','VCAP','DU145'})
assert prostate == {'PC3':12031, 'LNCAP':707}
drug_counts = {}
for name, pid in [('decitabine','BRD-K79254416'),('entinostat','BRD-K77908580'),('tazemetostat','BRD-K11215326')]:
    drug_counts[name] = sum(x['pert_id']==pid and x['cell_id']=='PC3' and x['pert_type']=='trt_cp' for x in signatures)
assert drug_counts == {'decitabine':15,'entinostat':15,'tazemetostat':0}
hashes = []
for directory, manifest in [(b,'provenance.json'),(c,'access_manifest.json'),(c,'geo_phase2_access.json'),(c,'prism_access.json')]:
    entries = json.loads((directory/manifest).read_text())
    if isinstance(entries, dict): entries=entries['sources']
    for item in entries:
        if 'sha256' not in item: continue
        file = directory/item['file']
        assert hashlib.sha256(file.read_bytes()).hexdigest()==item['sha256'], str(file)
        hashes.append(str(file.relative_to(root)))
result = {'status':'passed','scope':'independent cached-metadata recount and recorded-source hashes only; not biological or matrix validation', 'CPCG_pre_QC_patient_codes':210,'TCGA_pre_QC_cases':497,'TCGA_sample_ids':501,'LINCS_PhaseII_signatures':118050,'prostate_chemical_signatures':dict(prostate),'PC3_drug_signature_counts':drug_counts,'source_files_hash_verified':len(hashes)}
Path(__file__).with_name('M0_LOCAL_VERIFICATION.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result,indent=2))
