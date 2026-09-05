import csv,gzip,json,pathlib,collections,hashlib
p=pathlib.Path(__file__).parent
three={'BRD-K79254416':'decitabine','BRD-K77908580':'entinostat','BRD-K11215326':'tazemetostat'}
rows=list(csv.DictReader(gzip.open(p/'prostate_or_thesis_signatures.tsv.gz','rt'),delimiter='\t'))
thesis=[r for r in rows if r['pert_id'] in three and r['pert_type']=='trt_cp']
groups=collections.defaultdict(list)
for r in thesis:
    groups[(three[r['pert_id']],r['cell_iname'],r['pert_time'])].append(r)
summary=[]
for (drug,cell,t),rr in sorted(groups.items()):
    if cell not in {'22RV1','DU145','PC3','RWPE1','VCAP','LNCAP','LHSAR'}:continue
    summary.append(dict(drug=drug,cell=cell,time_h=t,n_sig=len(rr),n_qc_pass=sum(r['qc_pass']=='1' for r in rr),n_hiq=sum(r['is_hiq']=='1' for r in rr),doses=sorted({r['pert_dose'] for r in rr},key=float),nsamples=sorted({int(r['nsample']) for r in rr})))
eligible={k:[r for r in thesis if r['pert_id']==k and r['cell_iname']=='PC3' and r['pert_time']=='24' and r['pert_dose_unit']=='uM' and r['qc_pass']=='1'] for k in three}
common=set.intersection(*[{r['pert_dose'] for r in rr} for rr in eligible.values()])
anchor=[]
for dose in sorted(common,key=float):
    for k in three:
        rr=[r for r in eligible[k] if r['pert_dose']==dose]
        inst=collections.Counter(i for r in rr for i in r['distil_ids'].split('|'))
        anchor.append(dict(drug=three[k],dose_uM=dose,n_qc_pass=len(rr),n_hiq=sum(r['is_hiq']=='1' for r in rr),distinct_instances=len(inst),instances_in_multiple_sigs=sum(n>1 for n in inst.values()),rows=[{f:r[f] for f in ['sig_id','pert_dose','pert_idose','nsample','qc_pass','is_hiq','tas','project_code','det_plates','distil_ids']} for r in rr]))
out=dict(prostate_thesis_groups=summary,common_exact_qc_pass_PC3_24h_doses_uM=sorted(common,key=float),anchor=anchor)
(p/'thesis_anchor_summary.json').write_text(json.dumps(out,indent=2))
print(json.dumps(dict(groups=summary,common=sorted(common,key=float),anchors=[{k:v for k,v in r.items() if k!='rows'} for r in anchor]),indent=2))
