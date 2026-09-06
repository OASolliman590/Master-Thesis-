"""Inspect versioned expression annotation structures without assay values."""
import collections,csv,gzip,json,pathlib,sqlite3,tarfile
P=pathlib.Path(__file__).parent
targets={'HLA-A':'3105','HLA-B':'3106','HLA-C':'3107','B2M':'567','TAP1':'6890','TAP2':'6891','PSMB8':'5696','PSMB9':'5698'}
result={};universes={};members=[]
for chip in ['hta20','hugene20st']:
    archive=P/(chip+'hsentrezg.db_18.0.0.tar.gz')
    with tarfile.open(archive) as handle:
        for member in handle.getmembers():
            if not member.isfile():continue
            chosen=member.name.endswith('/DESCRIPTION') or member.name.endswith('.sqlite')
            members.append({'archive':archive.name,'member':member.name,'uncompressed_bytes':member.size,'extracted':chosen})
            if chosen:
                name=chip+'_DESCRIPTION.txt' if member.name.endswith('/DESCRIPTION') else pathlib.Path(member.name).name
                (P/name).write_bytes(handle.extractfile(member).read())
    db=sqlite3.connect('file:'+str(P/(chip+'hsentrezg.sqlite')).replace('\\','/')+'?mode=ro',uri=True)
    rows=db.execute('select probe_id,gene_id,is_multiple from probes').fetchall()
    universe={gene for probe,gene,multiple in rows if gene is not None}
    universes[chip]=universe
    result[chip]={'metadata':dict(db.execute('select name,value from metadata')),'map_metadata':db.execute('select * from map_metadata').fetchall(),
        'mapping_rows':len(rows),'unique_probeset_ids':len({r[0] for r in rows}),'unique_nonnull_Entrez_ids':len(universe),
        'null_gene_mapping_rows':sum(r[1] is None for r in rows),'is_multiple_counts':dict(collections.Counter(str(r[2]) for r in rows)),
        'target_mappings':{symbol:[list(r) for r in rows if r[1]==gene] for symbol,gene in targets.items()}}
    with (P/(chip+'_v18_candidate_entrez_universe.tsv')).open('w') as output:
        output.write('entrez_id\n');output.writelines(gene+'\n' for gene in sorted(universe,key=int))
    db.close()
desc=list(csv.reader(gzip.open(P/'GPL19803_desc.annot.txt.gz','rt'),delimiter='\t'))
desc_ids={r[1] for r in desc}
result['GEO_HuGene2_desc']={'rows':len(desc),'unique_ids':len(desc_ids),'same_gene_set_as_original_v18_db':desc_ids==universes['hugene20st'],'description_only_ids':sorted(desc_ids-universes['hugene20st']),'database_only_ids':sorted(universes['hugene20st']-desc_ids)}
common=universes['hta20']&universes['hugene20st']
result['platform_intersection']={'candidate_common_Entrez_ids':len(common),'hta20_only':len(universes['hta20']-common),'hugene20st_only':len(universes['hugene20st']-common),'all_eight_in_common':set(targets.values())<=common,'not_final_U':'No processed feature-ID set or TCGA versioned crosswalk intersected; no annotation policy selected.'}
with (P/'v18_two_platform_candidate_common_entrez.tsv').open('w') as output:
    output.write('entrez_id\n');output.writelines(gene+'\n' for gene in sorted(common,key=int))
probe_counts=collections.Counter();target_sequences=collections.defaultdict(set);target_rows=[]
with gzip.open(P/'GPL19803_probe_tab.txt.gz','rt') as handle:
    for row in csv.DictReader(handle,delimiter='\t'):
        probe_counts[row['Probe Set Name']]+=1
        if row['Probe Set Name'].removesuffix('_at') in targets.values():
            target_rows.append(row);target_sequences[row['Probe Sequence']].add(row['Probe Set Name'])
foreign_shared=collections.defaultdict(set)
with gzip.open(P/'GPL19803_probe_tab.txt.gz','rt') as handle:
    for row in csv.DictReader(handle,delimiter='\t'):
        if row['Probe Sequence'] in target_sequences:
            foreign_shared[row['Probe Sequence']].add(row['Probe Set Name'])
result['HuGene2_v18_probe_annotation']={'total_probe_rows':sum(probe_counts.values()),'probesets_with_probe_rows':len(probe_counts),'target_probe_counts':{symbol:probe_counts[gene+'_at'] for symbol,gene in targets.items()},
    'target_exact_sequence_shared_between_multiple_probesets':sum(len(ids)>1 for ids in foreign_shared.values()),
    'target_sequence_lengths':sorted({len(row['Probe Sequence']) for row in target_rows}),
    'specificity_limit':'Only exact duplicate sequences within this table checked; no genomic remapping, HLA allele/SNP evaluation or HTA2 probe sequences. This does not validate biological specificity.'}
(P/'annotation_inspection.json').write_text(json.dumps(result,indent=2))
(P/'package_member_inventory.json').write_text(json.dumps(members,indent=2))
print(json.dumps({k:v for k,v in result.items() if k not in ['hta20','hugene20st']},indent=2))
print({chip:{k:v for k,v in result[chip].items() if k in ['mapping_rows','unique_probeset_ids','unique_nonnull_Entrez_ids','null_gene_mapping_rows','is_multiple_counts','target_mappings']} for chip in universes})
