"""Inspect identifiers, visit/response provenance and file headers; no scoring."""
import collections, csv, gzip, hashlib, json, pathlib, re, zlib
P=pathlib.Path(__file__).parent
F=pathlib.Path('E:/Master_Thesis/planning/feasibility/source_metadata')
def geo(acc):
    text=gzip.decompress((F/(acc+'_family.soft.gz')).read_bytes()).decode()
    out=[]
    for block in text.split('^SAMPLE = ')[1:]:
        record={'GSM':block.splitlines()[0]}
        for line in block.splitlines():
            if line.startswith('!Sample_title = '):record['title']=line.split(' = ',1)[1]
            if line.startswith('!Sample_characteristics_ch1 = '):
                key,_,value=line.split(' = ',1)[1].partition(': ');record[key]=value
        record['BioSample']=';'.join(sorted(set(re.findall(r'SAMN\d+',block))))
        record['SRA_experiment']=';'.join(sorted(set(re.findall(r'SRX\d+',block))))
        out.append(record)
    return out
riaz,hugo=geo('GSE91061'),geo('GSE78220')
source=list(csv.reader((P/'riaz_sample_table.csv').open()))
# Original source has two distinct columns both called Response. Keep positional meanings.
assert source[0][9:14]==['BOR','Response','Response','USUBJID','Cohort']
samples={row[3].removesuffix('.bam'):row for row in source[1:]}
normalized_samples={re.sub(r'\.(\d+)$',r'-\1',key):row for key,row in samples.items()}
assert len(normalized_samples)==len(samples)
clinical=list(csv.DictReader((P/'riaz_clinical.csv').open()))
clinical_by_patient={row['PatientID']:row for row in clinical}
summary={'original_sample_table_rows':len(source)-1,'original_sample_table_headers':source[0]}
baseline=[]
for row in riaz:
    if row['visit (pre or on treatment)']!='Pre':continue
    exact_author=samples.get(row['title'])
    author=normalized_samples.get(row['title'])
    patient=row['title'].split('_')[0]
    cr=clinical_by_patient.get(patient)
    baseline.append({'GSM':row['GSM'],'title':row['title'],'patient_namespace':'CA209-038/Riaz2017','patient_id':patient,'GEO_response':row['response'],
        'author_BOR':author[9] if author else '', 'author_Response_column10':author[10] if author else '',
        'author_Response_column11':author[11] if author else '', 'author_USUBJID':author[12] if author else '',
        'author_Cohort':author[13] if author else '', 'clinical_BOR':cr['BOR'] if cr else '',
        'source_bam_title_match':bool(exact_author),'source_bam_after_suffix_punctuation_rule':bool(author),
        'source_BamName':author[3] if author else '',
        'author_baseline_DEG_explicit_exclusion':patient in ['Pt48','Pt67','Pt52','Pt27'],
        'paper_PCA_outlier_statement':patient=='Pt3','BioSample':row['BioSample'],'SRA_experiment':row['SRA_experiment']})
with (P/'Riaz_baseline_source_crosswalk.tsv').open('w',newline='',encoding='utf-8') as handle:
    writer=csv.DictWriter(handle,fieldnames=list(baseline[0]),delimiter='\t');writer.writeheader();writer.writerows(baseline)
def counts(rows,key):return dict(collections.Counter(row[key] for row in rows))
summary['Riaz']={'GEO_profiles':len(riaz),'GEO_patient_codes':len({r['title'].split('_')[0] for r in riaz}),
 'visit_counts':counts(riaz,'visit (pre or on treatment)'),'baseline_profiles':len(baseline),'baseline_patients':len({r['patient_id'] for r in baseline}),
 'baseline_GEO_response':counts(baseline,'GEO_response'),'baseline_source_BOR':counts(baseline,'author_BOR'),
 'baseline_source_cohort':counts(baseline,'author_Cohort'),'baseline_source_bam_exact_matches':sum(r['source_bam_title_match'] for r in baseline),
 'baseline_source_bam_matches_after_explicit_terminal_dot_digit_to_hyphen_digit_rule':sum(r['source_bam_after_suffix_punctuation_rule'] for r in baseline),
 'source_clinical_GEO_category_disagreements':[r['patient_id'] for r in baseline if r['clinical_BOR'] and {'CR':'PRCR','PR':'PRCR','SD':'SD','PD':'PD','NE':'UNK'}.get(r['clinical_BOR'])!=r['GEO_response']],
 'stratum_BOR_counts':{cohort:counts([r for r in baseline if r['author_Cohort']==cohort],'author_BOR') for cohort in sorted({r['author_Cohort'] for r in baseline})}}
raw=(P/'Riaz_FPKM.gzpart').read_bytes();decomp=zlib.decompressobj(31).decompress(raw).decode();rows=list(csv.reader(decomp[:decomp.rfind('\n')].splitlines()))
header=rows[0];titles={r['title'] for r in riaz};columns=set(header[1:])
(P/'Riaz_FPKM_header.csv').write_text(next(iter(decomp.splitlines()))+'\n')
summary['FPKM_prefix']={'compressed_bytes_inspected':len(raw),'complete_rows_inspected':len(rows)-1,'sample_columns':len(header)-1,
 'first_column_header':header[0],'sample_titles_equal_GEO_titles':titles==columns,'duplicate_header_columns':len(header[1:])-len(columns),
 'missing_GEO_titles':sorted(titles-columns),'unexpected_header_titles':sorted(columns-titles),
 'all_complete_row_widths':sorted({len(r) for r in rows[1:]}),'example_gene_identifiers':[r[0] for r in rows[1:6]],
 'full_object_downloaded':False,'gene_coverage_or_nonnegative_full_matrix_certified':False}
hugo_pre=[r for r in hugo if r['biopsy time']=='pre-treatment']
by_patient=collections.defaultdict(list)
for row in hugo_pre:by_patient[row['patient id']].append(row)
unique=[rows[0] for rows in by_patient.values()]
summary['Hugo']={'GEO_profiles':len(hugo),'GEO_patients':len({r['patient id'] for r in hugo}),'baseline_profiles':len(hugo_pre),'baseline_patients':len(by_patient),
 'baseline_unique_patient_response':counts(unique,'anti-pd-1 response'),'all_treatments':counts(hugo,'treatment'),'all_study_sites':counts(hugo,'study site'),
 'multiple_baseline_specimens':{pid:[r['title'] for r in rows] for pid,rows in by_patient.items() if len(rows)>1},
 'duplicate_patient_response_disagreement':[pid for pid,rows in by_patient.items() if len({r['anti-pd-1 response'] for r in rows})>1],
 'nonbaseline_profiles':[{'title':r['title'],'GSM':r['GSM'],'visit':r['biopsy time']} for r in hugo if r not in hugo_pre]}
summary['cross_accession_overlap']={key:sorted({r[key] for r in riaz}&{r[key] for r in hugo}) for key in ['GSM','BioSample','SRA_experiment']}
summary['cross_accession_overlap']['biological_patient_independence_proven']=False
summary['cross_accession_overlap']['patient_code_numeric_intersection_not_identity_evidence']=sorted({r['title'].split('_')[0] for r in riaz}&{r['patient id'] for r in hugo})
(P/'metadata_summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
