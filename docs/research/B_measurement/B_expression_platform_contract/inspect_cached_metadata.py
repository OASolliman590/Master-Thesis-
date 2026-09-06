"""Platform/sample annotation inspection from existing caches only."""
import collections,csv,gzip,json,pathlib,re
P=pathlib.Path(__file__).parent
R=pathlib.Path('E:/Master_Thesis/master-thesis/docs/research')
F=pathlib.Path('E:/Master_Thesis/planning/feasibility/source_metadata/GSE107299_family.soft.gz')
text=(R/'B_paired_prostate/GSE107299_sample_metadata.soft').read_text()
patients=[]
pairs={r['patient_code'] for r in csv.DictReader((R/'B_paired_prostate/CPCG_patient_pairs.tsv').open(),delimiter='\t')}
oldcodes=set(re.findall(r'CPCG\d+',(R/'B_paired_prostate/GSE84042_sample_metadata.soft').read_text()))
processing=collections.Counter()
for block in text.split('^SAMPLE = ')[1:]:
    lines=block.splitlines();gsm=lines[0]
    def value(prefix):return [line.partition(' = ')[2] for line in lines if line.startswith(prefix+' = ')]
    title=value('!Sample_title')[0];code=re.search(r'CPCG\d+',title).group()
    batch=[v.partition(': ')[2] for v in value('!Sample_characteristics_ch1') if v.startswith('batch: ')][0]
    platform=value('!Sample_platform_id')[0]
    for v in value('!Sample_data_processing'):processing[v]+=1
    patients.append({'patient_code':code,'GSM':gsm,'title':title,'platform':platform,'batch':batch,'paired_code_candidate':code in pairs,'legacy_GSE84042_code':code in oldcodes,'raw_file_urls':';'.join(value('!Sample_supplementary_file')),'reanalysis_source':';'.join(value('!Sample_relation'))})
with (P/'patient_platform_map.tsv').open('w',newline='',encoding='utf-8') as handle:
    writer=csv.DictWriter(handle,fieldnames=list(patients[0]),delimiter='\t');writer.writeheader();writer.writerows(patients)
def groups(rows):return dict(collections.Counter(r['platform']+' / '+r['batch'] for r in rows))
summary={'GSM_records':len(patients),'distinct_patient_codes':len({r['patient_code'] for r in patients}),'platform_batch_counts':groups(patients),'paired_candidate_platform_batch_counts':groups([r for r in patients if r['paired_code_candidate']]),'legacy73_platform_batch_counts':groups([r for r in patients if r['legacy_GSE84042_code']]),'processing_text_counts':dict(processing),'CPCG0398_records':[r for r in patients if r['patient_code']=='CPCG0398']}
audit=json.loads((R/'B_readiness/GSE107299_full_expression_audit.json').read_text())
summary['metadata_patient_set_equals_prior_actual_matrix_header']=set(audit['sample_ids'])=={r['patient_code'] for r in patients}
platforms={};current=None;table=False;header=None
target_ids={'3105','3106','3107','567','5696','5698','6890','6891'}
with gzip.open(F,'rt',encoding='utf-8') as handle:
    for line in handle:
        line=line.rstrip('\r\n')
        if line.startswith('^PLATFORM = '):
            current=line.partition(' = ')[2];platforms[current]={'metadata':[],'table_header':[],'rows':0,'target_gene_annotation_candidates':[]};table=False
        elif line.startswith('^'):current=None;table=False
        if current:
            if line.startswith('!Platform_'):platforms[current]['metadata'].append(line)
            if line=='!platform_table_begin':table=True;header=None;continue
            if line=='!platform_table_end':table=False;continue
            if table:
                parts=line.split('\t')
                if header is None:header=parts;platforms[current]['table_header']=header;continue
                platforms[current]['rows']+=1
                record=dict(zip(header,parts))
                # Manufacturer compound annotation is retained, not treated as a custom-CDF gene map.
                # In this vendor schema each /// separated assignment has five // fields;
                # the fifth field is Entrez. Do not match gene numbers embedded in aliases.
                assignments=[entry.split(' // ') for entry in record.get('gene_assignment','').split(' /// ')]
                candidate=any(len(entry)==5 and entry[4].strip() in target_ids for entry in assignments)
                if candidate:platforms[current]['target_gene_annotation_candidates'].append(record)
for name,record in platforms.items():
    (P/(name+'_vendor_metadata.txt')).write_text('\n'.join(record['metadata'])+'\n')
(P/'vendor_platform_inspection.json').write_text(json.dumps(platforms,indent=2))
(P/'metadata_summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps({k:v for k,v in summary.items() if k not in ['processing_text_counts','CPCG0398_records']},indent=2))
print({k:{'rows':v['rows'],'header':v['table_header'],'candidate_rows':len(v['target_gene_annotation_candidates'])} for k,v in platforms.items()})
