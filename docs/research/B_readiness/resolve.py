import json,csv,re,collections,pathlib,math
P=pathlib.Path(__file__).parent
pairs={r['patient'] for r in csv.DictReader((P/'patient_multiplicity.tsv').open(),delimiter='\t') if r['expression_gsm']}
out={}; mappings=[]
for typ in ['patient','sample']:
 d=json.loads((P/('cbio_clinical_'+typ+'.json')).read_text());by=collections.defaultdict(dict)
 for r in d:
  sid=r.get('sampleId',r['patientId']);m=re.fullmatch(r'(CPCG\d+)-F1',sid)
  if m:
   by[m[1]][r['clinicalAttributeId']]=r['value']
   if not any(x['source_id']==sid for x in mappings):mappings.append(dict(patient=m[1],source_id=sid,rule='Exact CPCG code plus -F1; patient-level candidate link, same-focus identity unresolved'))
 fields=sorted({k for rs in by.values() for k in rs})
 out[typ]=dict(source_cpcg_n=len(by),paired_code_overlap=len(set(by)&pairs),coverage_in_210={k:sum(k in by.get(p,{}) and by[p][k].lower() not in ['na','nan','unknown','not available',''] for p in pairs) for k in fields})
 with (P/('clinical_'+typ+'_candidate210.tsv')).open('w',newline='') as h:
  w=csv.DictWriter(h,fieldnames=['patient']+fields,delimiter='\t');w.writeheader();w.writerows(dict(patient=p,**by.get(p,{})) for p in sorted(pairs))
 if typ=='sample':out['joint_grade_cellularity_wgs_purity']=sum(all(k in by.get(p,{}) for k in ['GLEASON_SCORE','CELLULARITY','WGS_BASED_PURITY_ESTIMATION']) for p in pairs)
with (P/'clinical_candidate_mapping.tsv').open('w',newline='') as h:
 w=csv.DictWriter(h,fieldnames=mappings[0],delimiter='\t');w.writeheader();w.writerows(mappings)
with (P/'GSE107298_processed_prefix.tsv').open() as h:m=list(csv.reader(h,delimiter='\t'))
header=m[0];cols=[x for x in header if not x.endswith('_Dectection_Pval')];ids=[re.search(r'CPCG\d+',x)[0] for x in cols]
vals=[float(x) for r in m[1:] for x in r[1::2] if x not in ['NA','NaN','']]
out['methyl_prefix']=dict(header_fields=len(header),first_data_fields=len(m[1]),beta_columns=len(cols),patient_codes=len(set(ids)),paired_codes_present=len(set(ids)&pairs),detection_p_columns=sum(x.endswith('_Dectection_Pval') for x in header),feature_rows=len(m)-1,minimum_beta=min(vals),maximum_beta=max(vals),header_missing_probe_label=len(m[1])==len(header)+1)
with (P/'GSE107299_processed_prefix.tsv').open() as h:e=list(csv.DictReader(h,delimiter='\t'))
exprcols=[x for x in e[0] if re.fullmatch(r'CPCG\d+',x)]
out['expression_prefix']=dict(annotation_columns=[k for k in e[0] if k not in exprcols],patient_columns=len(exprcols),paired_codes_present=len(set(exprcols)&pairs),complete_feature_rows=len(e))
# Resolve every older GSM by original series metadata, not numerical proximity.
s=(P/'GSE84493_samples.soft').read_text();old={}
for block in re.split(r'\^SAMPLE = ',s)[1:]:
 gsm=block.splitlines()[0].strip();pid=re.search(r'CPCG\d+',block);old[gsm]=pid[0] if pid else None
edges=list(csv.DictReader((P/'reanalysis_edges.tsv').open(),delimiter='\t'))
for r in edges:
 r['original_series']='GSE83917' if r['original_in_GSE83917']=='True' else ('GSE84493' if r['original_gsm'] in old else 'unresolved')
 r['original_patient_code']=old.get(r['original_gsm'],'')
with (P/'reanalysis_edges_resolved.tsv').open('w',newline='') as h:
 w=csv.DictWriter(h,fieldnames=edges[0],delimiter='\t');w.writeheader();w.writerows(edges)
out['original_series_counts']=dict(collections.Counter(r['original_series'] for r in edges));out['GSE84493_patient_mismatches']=[r for r in edges if r['original_series']=='GSE84493' and r['original_patient_code']!=r['patient']]
(P/'readiness_summary.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
