"""Stream public metadata once; save only relevant compressed rows and aggregate evidence."""
import csv,gzip,hashlib,json,pathlib,time,urllib.request,datetime,collections,sys
p=pathlib.Path(__file__).parent
url='https://s3.amazonaws.com/macchiato.clue.io/builds/LINCS2020/siginfo_beta.txt'
expected=465242319
three={'BRD-K79254416':'decitabine','BRD-K77908580':'entinostat','BRD-K11215326':'tazemetostat (E-7438)'}
prostate={'22RV1','DU145','PC3','RWPE1','VCAP','LNCAP','LHSAR'}
panel=collections.defaultdict(set)
names={}
for r in csv.DictReader((p/'lincs2020_compoundinfo.txt').open(),delimiter='\t'):
    k=r['pert_id']; names[k]=r['cmap_name']; moa=r['moa']; target=r['target']
    if moa=='DNA methyltransferase inhibitor': panel[k].add('DNMTi')
    if moa=='HDAC inhibitor': panel[k].add('HDACi')
    if 'EZH2' in target.split('|') and 'inhibitor' in moa.lower(): panel[k].add('EZH2i')
panel['BRD-K11215326'].add('EZH2i_manual_ChEMBL3414621')
(p/'epi_panel.json').write_text(json.dumps({k:{'name':names.get(k),'classes':sorted(v)} for k,v in sorted(panel.items())},indent=2))
old={}; oldinst=set()
for r in csv.DictReader(gzip.open(p/'GSE70138_Broad_LINCS_sig_info_2017-03-06.txt.gz','rt'),delimiter='\t'):
    ids=set(r['distil_id'].split('|')); old[r['sig_id']]=ids; oldinst.update(ids)
summary={'url':url,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'expected_bytes':expected,'complete':False,'phase2_signatures':len(old),'phase2_distinct_instances':len(oldinst)}
counts=collections.Counter(); grid=collections.Counter(); qcs=collections.Counter(); classes=collections.defaultdict(set)
retained_inst=collections.Counter(); seenoldinst=set(); seenoldsig=set(); overlap_rows=0; exact_overlap=0; total=0; bytecount=0; sha=hashlib.sha256(); start=time.monotonic()
try:
    with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=45) as h:
        summary['head_headers']=dict(h.headers)
        if int(h.headers['Content-Length'])!=expected: raise RuntimeError('Source size changed; stop for review')
    with urllib.request.urlopen(url,timeout=120) as src, gzip.open(p/'prostate_or_thesis_signatures.tsv.gz','wt',newline='') as dst:
        summary['get_headers']=dict(src.headers)
        header=src.readline(); bytecount+=len(header); sha.update(header)
        fields=header.decode().rstrip('\r\n').split('\t'); summary['fields']=fields
        writer=csv.DictWriter(dst,fieldnames=fields,delimiter='\t'); writer.writeheader()
        for line in src:
            bytecount+=len(line); sha.update(line)
            if bytecount>expected: raise RuntimeError('Size exceeded expected')
            values=next(csv.reader([line.decode()],delimiter='\t'))
            if len(values)!=len(fields): raise RuntimeError('Malformed row')
            r=dict(zip(fields,values)); total+=1
            ids=set(r['distil_ids'].split('|'))-{'','-666'}
            ov=ids&oldinst
            if ov: overlap_rows+=1; seenoldinst.update(ov)
            if r['sig_id'] in old:
                seenoldsig.add(r['sig_id'])
                if ids==old[r['sig_id']]: exact_overlap+=1
            if r['pert_type']=='trt_cp':
                counts['chemical_all']+=1
                if r['cell_iname'] in prostate:
                    counts['chemical_'+r['cell_iname']]+=1
                    if r['pert_id'] in panel:
                        for cl in panel[r['pert_id']]: classes[(cl,r['cell_iname'])].add(r['pert_id'])
                if r['pert_id'] in three: counts['thesis_all_'+three[r['pert_id']]]+=1
            retain=(r['cell_iname'] in prostate or r['pert_id'] in three)
            if retain:
                writer.writerow(r); retained_inst.update(ids); counts['retained']+=1
                if ov: counts['retained_with_phase2_instance_overlap']+=1
            if r['pert_type']=='trt_cp' and r['cell_iname'] in prostate and (r['pert_id'] in panel or r['pert_id'] in three):
                key=(r['pert_id'],r['cmap_name'],r['cell_iname'],r['pert_time'],r['pert_time_unit'],r['pert_dose'],r['pert_dose_unit'],r['qc_pass'],r['is_hiq'],r['nsample'])
                grid[key]+=1; qcs[(r['pert_id'],r['cell_iname'],r['qc_pass'],r['is_hiq'])]+=1
            if total%100000==0:
                print(json.dumps({'rows':total,'bytes':bytecount,'seconds':round(time.monotonic()-start,1)}),flush=True)
    summary['complete']=bytecount==expected
    if not summary['complete']: raise RuntimeError('EOF bytecount mismatch')
except Exception as e:
    summary['error']=str(e)
finally:
    summary.update(bytes_read=bytecount,rows=total,sha256=sha.hexdigest(),elapsed_seconds=round(time.monotonic()-start,2),counts=dict(counts),phase2_identical_sig_ids=len(seenoldsig),phase2_identical_sigid_and_instance_set=exact_overlap,phase2_instances_reused=len(seenoldinst),rows_with_phase2_instance_overlap=overlap_rows,retained_distinct_instances=len(retained_inst),retained_instances_in_multiple_rows=sum(n>1 for n in retained_inst.values()))
    summary['class_line_distinct_compounds']=[{'class':cl,'cell':cell,'n_compounds':len(ids),'pert_ids':sorted(ids)} for (cl,cell),ids in sorted(classes.items())]
    (p/'audit_summary.json').write_text(json.dumps(summary,indent=2))
    with (p/'epi_prostate_dose_time_qc.tsv').open('w',newline='') as f:
        w=csv.writer(f,delimiter='\t');w.writerow(['pert_id','cmap_name','cell_iname','pert_time','pert_time_unit','pert_dose','pert_dose_unit','qc_pass','is_hiq','nsample','n_signatures']);w.writerows([*k,v] for k,v in sorted(grid.items()))
    print(json.dumps(summary),flush=True)
if not summary['complete']: sys.exit(1)
