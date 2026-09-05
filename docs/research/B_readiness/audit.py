"""Bounded public readiness audit, no model fitting. Run from disjoint AIU staging."""
import collections,csv,hashlib,json,re,urllib.request,datetime,pathlib,sys
P=pathlib.Path(__file__).parent
log=[]
def fetch(name,url,cap=25000000):
    target=P/name
    if target.exists(): return target.read_bytes()
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'ThesisMetadataAudit/1.0'}),timeout=50) as r:
            if int(r.headers.get('Content-Length','0'))>cap: raise ValueError('Object exceeds bound')
            b=r.read(cap+1)
            if len(b)>cap: raise ValueError('Object exceeds bound')
        target.write_bytes(b)
        log.append(dict(file=name,url=url,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),retrieved_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
        return b
    except Exception as e:
        log.append(dict(file=name,url=url,error=str(e))); return None
    finally: (P/'fetch_log.json').write_text(json.dumps(log,indent=2))
def metadata():
    d=json.loads((P/'geo_samples.json').read_text())
    meth=d['GSE107298']; expr={x['patient_id']:x for x in d['GSE107299']}
    old={x['gsm']:x for x in d['GSE83917']}
    patients=collections.defaultdict(list)
    for x in meth:patients[x['patient_id']].append(x)
    rows=[]; edges=[]
    for pid,ss in sorted(patients.items()):
        origins=[]
        for s in ss:
            links=[g for rel in s.get('relation',[]) if rel.startswith('Reanalysis of:') for g in re.findall(r'GSM\d+',rel)]
            origins+=links
            for g in links:edges.append(dict(patient=pid,current_gsm=s['gsm'],original_gsm=g,original_in_GSE83917=g in old,original_title='|'.join(old[g]['title']) if g in old else '',current_title='|'.join(s['title'])))
        rows.append(dict(patient=pid,methyl_records=len(ss),methyl_gsms='|'.join(x['gsm'] for x in ss),titles='|'.join(x['title'][0] for x in ss),reanalysis_records=sum(any(y.startswith('Reanalysis of:') for y in x.get('relation',[])) for x in ss),original_gsms='|'.join(origins),expression_gsm=expr.get(pid,{}).get('gsm',''),expression_platform='|'.join(expr.get(pid,{}).get('platform_id',[]))))
    for name,rs in [('patient_multiplicity.tsv',rows),('reanalysis_edges.tsv',edges)]:
        with (P/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=rs[0].keys(),delimiter='\t');w.writeheader();w.writerows(rs)
    report=dict(patient_n=len(rows),record_n=len(meth),multiplicity_distribution=dict(collections.Counter(x['methyl_records'] for x in rows)),paired_patient_n=sum(bool(x['expression_gsm']) for x in rows),paired_record_n=sum(x['methyl_records'] for x in rows if x['expression_gsm']),reanalysis_edge_n=len(edges),unique_origin_gsms=len(set(x['original_gsm'] for x in edges)),edges_to_GSE83917=sum(x['original_in_GSE83917'] for x in edges),other_original_gsms=sorted(set(x['original_gsm'] for x in edges if not x['original_in_GSE83917'])),paired_multiplicity=dict(collections.Counter(x['methyl_records'] for x in rows if x['expression_gsm'])))
    (P/'multiplicity_summary.json').write_text(json.dumps(report,indent=2)); print(json.dumps({k:v for k,v in report.items() if k!='other_original_gsms'},indent=2))
    hits=json.loads((P/'gdc_files.json').read_text())['data']['hits']
    sample='TCGA-HC-A6AO-01A'
    chosen=[h for h in hits if any(s['submitter_id']==sample for c in h['cases'] for s in c.get('samples',[]))]
    (P/'tcga_selected.json').write_text(json.dumps(chosen,indent=2))
def initial_fetch():
    for x in json.loads((P/'tcga_selected.json').read_text()):
        fetch('tcga_'+x['file_id']+'_metadata.json','https://api.gdc.cancer.gov/files/'+x['file_id']+'?expand=cases.samples.portions.analytes.aliquots,analysis')
        fetch('tcga_'+x['file_id']+'.tsv','https://api.gdc.cancer.gov/data/'+x['file_id'])
    fetch('figshare.json','https://api.figshare.com/v2/articles/16574486')
    fetch('cbio_studies.json','https://www.cbioportal.org/api/studies?projection=DETAILED')
    for acc in ['GSE107298','GSE107299']:
        fetch(acc+'_series.soft','https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc='+acc+'&targ=self&view=brief&form=text')
    fetch('Proteogenomic2019.xml','https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6511374/fullTextXML')
if __name__=='__main__':
    metadata()
    if '--fetch' in sys.argv:initial_fetch()
