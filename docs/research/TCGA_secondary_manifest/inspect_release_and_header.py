"""Pin current release metadata and one bounded LUAD RNA header; no analysis."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

root = Path(__file__).resolve().parent
records = []
def fetch(name, url, limit, partial=False):
    target = root / name
    if target.exists():
        raise RuntimeError('Refusing to overwrite source artifact')
    try:
        with urlopen(url,timeout=40) as response:
            data = response.read(limit if partial else limit+1)
            status = response.status
        if len(data)>limit:
            raise ValueError('Source exceeded byte budget')
        target.write_bytes(data)
        records.append({'file':name,'url':url,'status':status,'bytes':len(data),
                        'sha256':hashlib.sha256(data).hexdigest(),'partial':partial})
        return data
    except Exception as exc:
        records.append({'file':name,'url':url,'error_type':type(exc).__name__})
        return None

status = fetch('gdc_status.json','https://api.gdc.cancer.gov/status',250_000)
obj = json.loads((root / 'luad_files.json').read_text(encoding='utf-8'))
summary = json.loads((root / 'summary.json').read_text(encoding='utf-8'))
paired = set(summary['groups']['rna']['sample_ids']) & set(summary['groups']['methylation450k']['sample_ids'])
selected = next(hit for hit in obj['data']['hits'] if hit['data_type']=='Gene Expression Quantification'
                and hit['analysis']['workflow_type']=='STAR - Counts'
                and any(sample['sample_id'] in paired for case in hit['cases'] for sample in case['samples']))
prefix = fetch('luad_star_header.prefix','https://api.gdc.cancer.gov/data/'+selected['file_id'],2048,True)
header = {}
if prefix:
    lines = prefix.decode('utf-8').splitlines()
    header = {'comment':lines[0], 'columns':lines[1].split('\t'),
              'selection_rule':'first file-ID-sorted RNA record in metadata-paired primary samples; header-only audit, not analysis eligibility'}
(root / 'header_check.json').write_text(json.dumps({'selected_file_metadata':selected,
    'header':header,'release_status':json.loads(status) if status else None},indent=2)+'\n',encoding='utf-8',newline='\n')
(root / 'header_provenance.json').write_text(json.dumps({'retrieved_utc':datetime.now(timezone.utc).isoformat(),
    'records':records},indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({'header':header,'release':json.loads(status) if status else None,'records':records}))
