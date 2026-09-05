"""Recount retained rows only; EI1's class uses explicit primary literature."""
import csv,gzip,json,pathlib,collections,hashlib
p=pathlib.Path(__file__).parent
panel=json.loads((p/'epi_panel.json').read_text())
panel['BRD-K91535048']={'name':'EI1','classes':['EZH2i_manual_Qi2012'],'source':'https://doi.org/10.1073/pnas.1210371110','identity_basis':'LINCS dictionary cmap_name EI1 / alias EI-1; structure-crosscheck beyond dictionary remains pending'}
panel['BRD-K26818574']['curation_warning']='BIX-01294: DNA methyltransferase inhibitor is raw LINCS label; primary mechanism is G9a HMT inhibition, DOI10.1016/j.molcel.2007.01.017. Exclude from uncurated DNMT-class inference.'
(p/'epi_panel_supplemented.json').write_text(json.dumps(panel,indent=2))
groups=collections.defaultdict(list);ei=[]; instances=collections.Counter(); nrows=0
for r in csv.DictReader(gzip.open(p/'prostate_or_thesis_signatures.tsv.gz','rt'),delimiter='\t'):
    if r['pert_type']!='trt_cp' or r['cell_iname'] not in {'22RV1','DU145','PC3','VCAP','LNCAP','LHSAR','RWPE1'}:continue
    nrows+=1;instances.update(r['distil_ids'].split('|'))
    if r['pert_id'] not in panel:continue
    if r['pert_id']=='BRD-K91535048':ei.append(r)
    for c in panel[r['pert_id']]['classes']: groups[(c,r['cell_iname'],r['pert_time'])].append(r)
out=[dict(raw_class=c,cell=cell,time_h=t,n_raw_BRD_ids=len({r['pert_id'] for r in rr}),n_sigs=len(rr),n_qcpass=sum(r['qc_pass']=='1' for r in rr),n_hiq=sum(r['is_hiq']=='1' for r in rr),n_BRD_qcpass=len({r['pert_id'] for r in rr if r['qc_pass']=='1'})) for (c,cell,t),rr in sorted(groups.items())]
(p/'epi_panel_condition_coverage.json').write_text(json.dumps(out,indent=2))
(p/'EI1_rows.json').write_text(json.dumps(ei,indent=2))
(p/'chemical_prostate_overlap.json').write_text(json.dumps(dict(n_signature_rows=nrows,n_distinct_instances=len(instances),instances_in_multiple_signature_rows=sum(n>1 for n in instances.values())),indent=2))
manifest=[dict(file=f.name,bytes=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for f in p.iterdir() if f.is_file() and f.name!='artifact_checksums.json']
(p/'artifact_checksums.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(out,indent=2))
