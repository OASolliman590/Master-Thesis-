import json,csv,collections,math,pathlib,hashlib
P=pathlib.Path(__file__).parent
report={}
genes=['HLA-A','HLA-B','HLA-C','B2M','TAP1','TAP2','PSMB8','PSMB9']
f=P/'tcga_a4980c9c-6c37-46da-8db3-c60a1c29081f.tsv'
with f.open() as h:
 comment=next(h).strip(); rows=list(csv.DictReader(h,delimiter='\t'))
rs=[r for r in rows if not r['gene_id'].startswith('N_')]
report['TCGA_RNA']=dict(comment=comment,columns=list(rows[0]),gene_rows=len(rs),unique_gene_ids=len(set(r['gene_id'] for r in rs)),missing_tpm=sum(not r['tpm_unstranded'] for r in rs),candidate_rows=[r for r in rs if r['gene_name'] in genes])
f=P/'tcga_9cebe5e9-f133-479a-b0f6-e91d8b06ab38.tsv'
with f.open() as h: meth=list(csv.reader(h,delimiter='\t'))
values=[]; missing=collections.Counter(); bad=[]
for r in meth:
 try:
  v=float(r[1])
  if math.isfinite(v):values.append(v)
  else:missing[r[1]]+=1
 except ValueError:missing[r[1]]+=1
 if len(r)!=2:bad.append(r)
report['TCGA_methylation']=dict(header_present=False,first_row=meth[0],rows=len(meth),unique_ids=len(set(r[0] for r in meth)),finite_values=len(values),missing=dict(missing),minimum=min(values),maximum=max(values),bad_width_rows=len(bad),cg_rows=sum(r[0].startswith('cg') for r in meth),ch_rows=sum(r[0].startswith('ch') for r in meth))
for typ in ['patient','sample']:
 f=P/('cbio_clinical_'+typ+'.json')
 if not f.exists():continue
 data=json.loads(f.read_text()); by=collections.defaultdict(dict)
 for r in data:by[r.get('patientId',r.get('sampleId'))][r['clinicalAttributeId']]=r['value']
 pairs={r['patient'] for r in csv.DictReader((P/'patient_multiplicity.tsv').open(),delimiter='\t') if r['expression_gsm']}
 overlap=sorted(set(by)&pairs)
 fields=sorted({k for p in by.values() for k in p})
 report['cbio_'+typ]=dict(records=len(data),patients=len(by),exact_paired_overlap_n=len(overlap),overlap=overlap,fields=fields,coverage_in_210={k:sum(k in by.get(p,{}) and by[p][k].lower() not in ['na','nan','unknown','not available',''] for p in pairs) for k in fields})
 with (P/('clinical_'+typ+'_210.tsv')).open('w',newline='') as h:
  w=csv.DictWriter(h,fieldnames=['patient']+fields,delimiter='\t');w.writeheader();w.writerows(dict(patient=p,**by.get(p,{})) for p in sorted(pairs))
(P/'table_inspection.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
