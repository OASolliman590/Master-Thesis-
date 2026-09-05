"""Bounded public metadata audit; no expression/methylation matrices downloaded."""
import collections, csv, datetime, hashlib, json, pathlib, re, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
def fetch(url, name):
    req = urllib.request.Request(url, headers={'User-Agent':'MScMetadataAudit/1.0'})
    with urllib.request.urlopen(req, timeout=90) as r:
        data = r.read(12_000_001)
    if len(data)>12_000_000: raise RuntimeError('Metadata size cap exceeded')
    (ROOT/name).write_bytes(data)
    return data

def parse_soft(data):
    records=[]; cur=None
    for line in data.decode('utf-8').splitlines():
        if line.startswith('^SAMPLE = '):
            cur={'gsm':line.split(' = ',1)[1]}; records.append(cur)
        elif line.startswith('^'): cur=None
        elif cur is not None and line.startswith('!Sample_') and ' = ' in line:
            key,val=line[8:].split(' = ',1)
            cur.setdefault(key,[]).append(val)
    for s in records:
        hit=re.search(r'CPCG\d+', ' '.join(s.get('title',[])))
        s['patient_id']=hit.group(0) if hit else None
    return records

def main():
    provenance=[]; samples={}
    for acc in ['GSE83917','GSE84042','GSE107299','GSE107298']:
        url=f'https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={acc}&targ=gsm&view=brief&form=text'
        name=f'{acc}_sample_metadata.soft'
        raw=fetch(url,name); samples[acc]=parse_soft(raw)
        if not samples[acc]: raise RuntimeError(f'No samples {acc}')
        provenance.append({'url':url,'file':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    summary={}
    for a,ss in samples.items():
        ids={s['patient_id'] for s in ss if s['patient_id']}
        summary[a]={'records':len(ss),'unique_patient_codes':len(ids),'unmapped':sum(s['patient_id'] is None for s in ss),'platforms':dict(collections.Counter(x for s in ss for x in s.get('platform_id',[])))}
    expr={s['patient_id'] for s in samples['GSE107299'] if s['patient_id']}
    for acc in ['GSE83917','GSE107298']:
        meth={s['patient_id'] for s in samples[acc] if 'GPL13534' in s.get('platform_id',[]) and s['patient_id']}
        summary[acc]['matched_GSE107299_patient_codes']=sorted(meth & expr)
        summary[acc]['matched_GSE107299_patient_code_n']=len(meth & expr)
    summary['GSE84042_patient_overlap_GSE107299']=len({s['patient_id'] for s in samples['GSE84042']} & expr)
    (ROOT/'geo_samples.json').write_text(json.dumps(samples,indent=2),encoding='utf-8')
    (ROOT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    compact={k:({kk:vv for kk,vv in v.items() if not kk.endswith('_codes')} if isinstance(v,dict) else v) for k,v in summary.items()}
    print(json.dumps(compact,indent=2),flush=True)
    with (ROOT/'CPCG_patient_pairs.tsv').open('w',newline='',encoding='utf-8') as out:
        writer=csv.writer(out,delimiter='\t')
        writer.writerow(['patient_code','methylation_GSE107298_GSMs','expression_GSE107299_GSMs','expression_platform','also_in_GSE83917'])
        old_ids={s['patient_id'] for s in samples['GSE83917']}
        for pid in summary['GSE107298']['matched_GSE107299_patient_codes']:
            m=[s for s in samples['GSE107298'] if s['patient_id']==pid]
            e=[s for s in samples['GSE107299'] if s['patient_id']==pid]
            writer.writerow([pid,','.join(s['gsm'] for s in m),','.join(s['gsm'] for s in e),','.join(p for s in e for p in s['platform_id']),pid in old_ids])
    filters={'op':'and','content':[{'op':'in','content':{'field':'cases.project.project_id','value':['TCGA-PRAD']}},{'op':'in','content':{'field':'data_type','value':['Gene Expression Quantification','Methylation Beta Value']}}]}
    fields='file_id,file_name,data_type,platform,access,analysis.workflow_type,cases.case_id,cases.submitter_id,cases.samples.sample_id,cases.samples.submitter_id,cases.samples.sample_type'
    url='https://api.gdc.cancer.gov/files?'+urllib.parse.urlencode({'filters':json.dumps(filters),'fields':fields,'size':5000,'format':'JSON'})
    raw=fetch(url,'gdc_files.json'); obj=json.loads(raw)
    provenance.append({'url':url,'file':'gdc_files.json','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    if obj['data']['pagination']['total']>len(obj['data']['hits']): raise RuntimeError('Truncated GDC response')
    mods=collections.defaultdict(set); spec=collections.defaultdict(set); filecounts=collections.Counter()
    for f in obj['data']['hits']:
        key=(f['data_type'],f.get('analysis',{}).get('workflow_type',''),f.get('platform',''),f.get('access',''))
        filecounts[str(key)]+=1
        if f.get('access')!='open': continue
        for case in f.get('cases',[]):
            for s in case.get('samples',[]):
                if s.get('sample_type')=='Primary Tumor':
                    mods[f['data_type']].add(case['submitter_id'])
                    spec[f['data_type']].add(s['submitter_id'])
    summary['gdc']={'files':dict(filecounts),'primary_tumor_case_counts':{k:len(v) for k,v in mods.items()},'primary_tumor_matched_cases':sorted(set.intersection(*mods.values())) if len(mods)==2 else [],'primary_tumor_matched_sample_ids':sorted(set.intersection(*spec.values())) if len(spec)==2 else []}
    (ROOT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    (ROOT/'provenance.json').write_text(json.dumps({'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sources':provenance},indent=2),encoding='utf-8')
    print(json.dumps({'gdc_files':dict(filecounts),'matched_cases':len(summary['gdc']['primary_tumor_matched_cases']),'matched_samples':len(summary['gdc']['primary_tumor_matched_sample_ids'])},indent=2))

if __name__=='__main__': main()
