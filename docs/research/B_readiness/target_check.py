import audit,json,urllib.request,zlib,hashlib,csv,io
P=audit.P; audit.log=json.loads((P/'fetch_log.json').read_text())
audit.fetch('GSE84493_samples.soft','https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE84493&targ=gsm&view=brief&form=text')
url='https://ftp.ncbi.nlm.nih.gov/geo/series/GSE107nnn/GSE107299/suppl/GSE107299_Matrix_processed_data.tsv.gz'
targets={'HLA-A','HLA-B','HLA-C','B2M','TAP1','TAP2','PSMB8','PSMB9'}
dec=zlib.decompressobj(16+zlib.MAX_WBITS); compressed=bytearray();pending=b'';rows=[];header=None;n=0
with urllib.request.urlopen(url,timeout=60) as r:
 while len(compressed)<24000000 and targets:
  b=r.read(min(64000,24000000-len(compressed)))
  if not b:break
  compressed.extend(b);pending+=dec.decompress(b)
  lines=pending.split(b'\n');pending=lines.pop()
  for line in lines:
   row=next(csv.reader([line.decode()],delimiter='\t'))
   if header is None:header=row;continue
   n+=1
   if row[1] in targets:rows.append(row);targets.remove(row[1])
with (P/'GSE107299_eight_gene_rows.tsv').open('w',newline='') as h:
 w=csv.writer(h,delimiter='\t');w.writerow(header);w.writerows(rows)
# Save byte-prefix digest with precise byte count. Original huge matrix is not retained or fully downloaded.
result=dict(url=url,partial=True,compressed_bytes_read=len(compressed),compressed_prefix_sha256=hashlib.sha256(compressed).hexdigest(),complete_rows_scanned=n,unfound_genes=sorted(targets),genes_found=[r[1] for r in rows],patient_columns=header[7:],note='Prefix digest, not full matrix checksum; extracted rows are a feature-presence check only.')
(P/'GSE107299_target_check.json').write_text(json.dumps(result,indent=2))
audit.log.append(result);(P/'fetch_log.json').write_text(json.dumps(audit.log,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='patient_columns'},indent=2))
