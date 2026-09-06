from pathlib import Path
import json,csv,collections,math,hashlib,re
p=Path(r'E:\Master_Thesis\planning\next_evidence\B_TCGA_cellularity')
src=Path(r'E:\Master_Thesis\master-thesis\docs\research\B_paired_prostate\summary.json')
s=json.loads(src.read_text())['gdc']; c=set(s['primary_tumor_matched_cases']); v=set(s['primary_tumor_matched_sample_ids'])
rows=list(csv.DictReader((p/'TCGA_mastercalls.abs_tables_JSedit.fixed.txt').open(),delimiter='\t'))
pr=[r for r in rows if r['sample'][:12] in c]
called=[r for r in pr if r['call status']=='called']
vm=[r for r in pr if r['sample'][:16] in v]; vc=[r for r in vm if r['call status']=='called']
def stats(rr):
 valid=[r for r in rr if re.fullmatch(r'TCGA-[A-Z0-9]{2}-[A-Z0-9]{4}-[0-9]{2}[A-Z]-[0-9]{2}[A-Z]-[A-Z0-9]{4}-[0-9]{2}',r['sample'])]
 ans={'rows':len(rr),'unique_cases':len({r['sample'][:12] for r in valid}),'unique_sample_vials':len({r['sample'][:16] for r in valid}),'status_counts':dict(collections.Counter(r['call status'] for r in rr)),'full_TCGA_aliquot_barcode_rows':len(valid),'non_full_TCGA_aliquot_rows':len(rr)-len(valid),'sample_type_counts_for_full_barcodes':dict(collections.Counter(r['sample'][13:15] for r in valid))}
 for k in ('purity','ploidy','Cancer DNA fraction'):
  vals=[]; missing=collections.Counter()
  for r in rr:
   try:
    x=float(r[k])
    if not math.isfinite(x): raise ValueError()
    vals.append(x)
   except ValueError: missing[r[k]]+=1
  ans[k]={'numeric':len(vals),'missing_tokens':dict(missing),'min':min(vals) if vals else None,'max':max(vals) if vals else None}
 return ans
out={'scope':'Source field and candidate identifier coverage only; no purity correction, model or outcome association. Matching sample-vial does not establish portion/analyte/aliquot identity. No final eligible N.','source':json.loads((p/'retrieval.json').read_text()),'candidate_metadata_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'candidate_cases':len(c),'candidate_sample_vials':len(v),'all_table':stats(rows),'candidate_case_link':stats(pr),'candidate_case_called':stats(called),'candidate_vial_link':stats(vm),'candidate_vial_called':stats(vc),'candidate_cases_without_any_table_row':len(c-{r['sample'][:12] for r in pr}),'candidate_cases_without_called_row':len(c-{r['sample'][:12] for r in called}),'candidate_vials_without_called_row':len(v-{r['sample'][:16] for r in vc})}
(p/'summary.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:out[k] for k in ('candidate_vial_called','candidate_cases_without_called_row')}))
print('multiple_case_row_counts',dict(collections.Counter(collections.Counter(r['sample'][:12] for r in pr).values())))
print('non_vial_rows',len([r for r in pr if r['sample'][:16] not in v]))
