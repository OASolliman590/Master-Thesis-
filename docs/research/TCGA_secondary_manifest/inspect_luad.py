"""Bounded public metadata audit, not a cohort download or analysis."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
MAX_BYTES = 12_000_000
filters = {'op':'and','content':[
    {'op':'in','content':{'field':'cases.project.project_id','value':['TCGA-LUAD']}},
    {'op':'in','content':{'field':'data_type','value':['Gene Expression Quantification','Methylation Beta Value']}},
    {'op':'in','content':{'field':'access','value':['open']}}]}
fields = ['file_id','file_name','file_size','md5sum','data_type','platform','access',
          'analysis.workflow_type','created_datetime','updated_datetime',
          'cases.case_id','cases.submitter_id','cases.samples.sample_id',
          'cases.samples.submitter_id','cases.samples.sample_type']
url = 'https://api.gdc.cancer.gov/files?' + urlencode({'filters':json.dumps(filters),
    'fields':','.join(fields),'size':5000,'format':'JSON','sort':'file_id:asc'})
path = ROOT / 'luad_files.json'
if path.exists():
    raise SystemExit('Existing response: inspect and reuse; do not overwrite.')
with urlopen(Request(url,headers={'User-Agent':'MSc-thesis-metadata-audit/1'}),timeout=50) as handle:
    content = handle.read(MAX_BYTES+1)
    status = handle.status
    final_url = handle.url
if len(content)>MAX_BYTES:
    raise SystemExit('Response exceeds bounded metadata budget')
obj = json.loads(content)
hits = obj['data']['hits']
assert len(hits)==obj['data']['pagination']['total'], 'Truncated response'
assert len({h['file_id'] for h in hits})==len(hits), 'Duplicate file IDs'
path.write_bytes(content)
groups = {'rna': [], 'methylation450k': []}
for hit in hits:
    if hit['data_type']=='Gene Expression Quantification' and hit['analysis']['workflow_type']=='STAR - Counts':
        groups['rna'].append(hit)
    if hit['data_type']=='Methylation Beta Value' and hit.get('platform')=='Illumina Human Methylation 450' and hit['analysis']['workflow_type']=='SeSAMe Methylation Beta Estimation':
        groups['methylation450k'].append(hit)
sets = {}
summary = {'scope':'Complete public metadata response only; not final eligibility or same-portion pairing',
           'total_file_records':len(hits), 'platform_workflow_counts':dict(Counter(
               str((h['data_type'],h.get('platform'),h.get('analysis',{}).get('workflow_type'))) for h in hits)),
           'groups':{}}
for key, records in groups.items():
    by_case = {}
    by_sample = {}
    for record in records:
        for case in record['cases']:
            for sample in case.get('samples',[]):
                if sample.get('sample_type')!='Primary Tumor':
                    continue
                by_case.setdefault(case['case_id'],set()).add(sample['sample_id'])
                by_sample.setdefault(sample['sample_id'],set()).add(record['file_id'])
    sets[key] = (set(by_case),set(by_sample))
    summary['groups'][key] = {'all_sample_type_files':len(records),'primary_cases':len(by_case),
        'primary_samples':len(by_sample),'primary_files':len(set().union(*by_sample.values())),
        'cases_with_multiple_primary_samples':sum(len(v)>1 for v in by_case.values()),
        'samples_with_multiple_files':sum(len(v)>1 for v in by_sample.values()),
        'case_ids':sorted(by_case),'sample_ids':sorted(by_sample)}
summary['shared_primary_cases'] = len(sets['rna'][0]&sets['methylation450k'][0])
summary['shared_primary_samples'] = len(sets['rna'][1]&sets['methylation450k'][1])
summary['rna_only_primary_cases'] = len(sets['rna'][0]-sets['methylation450k'][0])
summary['methylation_only_primary_cases'] = len(sets['methylation450k'][0]-sets['rna'][0])
(ROOT / 'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8',newline='\n')
(ROOT / 'provenance.json').write_text(json.dumps({'retrieved_utc':datetime.now(timezone.utc).isoformat(),
    'url':url,'final_url':final_url,'status':status,'bytes':len(content),
    'sha256':hashlib.sha256(content).hexdigest(),'complete_metadata_response':True,
    'matrices_downloaded':0,'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({key:value for key,value in summary.items() if key not in ['groups','platform_workflow_counts']}))
print(json.dumps({key:{k:v for k,v in value.items() if not k.endswith('_ids')} for key,value in summary['groups'].items()}))
