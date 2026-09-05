import audit,json,re,zlib,urllib.request,hashlib
P=audit.P
audit.log=json.loads((P/'fetch_log.json').read_text())
for name,url in [
 ('cbio_clinical_patient.json','https://www.cbioportal.org/api/studies/prad_cpcg_2017/clinical-data?clinicalDataType=PATIENT&projection=DETAILED&pageSize=100000'),
 ('cbio_clinical_sample.json','https://www.cbioportal.org/api/studies/prad_cpcg_2017/clinical-data?clinicalDataType=SAMPLE&projection=DETAILED&pageSize=100000'),
 ('cbio_profiles.json','https://www.cbioportal.org/api/studies/prad_cpcg_2017/molecular-profiles'),
 ('GSM2237935.soft','https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSM2237935&targ=self&view=brief&form=text'),
 ('GSE107298_directory.html','https://ftp.ncbi.nlm.nih.gov/geo/series/GSE107nnn/GSE107298/suppl/'),
 ('GSE107299_directory.html','https://ftp.ncbi.nlm.nih.gov/geo/series/GSE107nnn/GSE107299/suppl/'),
 ('GDC_case.json','https://api.gdc.cancer.gov/cases/4045f40b-d42a-4598-9ee2-0d371a776d3f?expand=diagnoses,demographic,samples.portions.slides,samples.portions.analytes.aliquots'),
 ('Nature2017.html','https://www.nature.com/articles/nature20788'),
]: audit.fetch(name,url)
# Partial prefix only: never claim full-object checksum or feature coverage.
for acc in ['GSE107298','GSE107299']:
 t=(P/(acc+'_series.soft')).read_text()
 urls=re.findall(r'!Series_supplementary_file = (\S+)',t)
 for url in urls:
  if 'processed' not in url.lower():continue
  url=url.replace('ftp://','https://')
  name=acc+'_processed_prefix'
  try:
   with urllib.request.urlopen(url,timeout=60) as r:
    b=r.read(256000)
   (P/(name+'.gzpart')).write_bytes(b)
   dec=zlib.decompressobj(16+zlib.MAX_WBITS); out=dec.decompress(b,2000000)
   # Keep only complete lines, bounded prefix.
   out=out[:out.rfind(b'\n')+1]
   (P/(name+'.tsv')).write_bytes(out)
   audit.log.append(dict(file=name+'.gzpart',url=url,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),partial=True,decompressed_complete_lines=out.count(b'\n'),decompressed_bytes=len(out)))
  except Exception as e:audit.log.append(dict(file=name,url=url,error=str(e)))
(P/'fetch_log.json').write_text(json.dumps(audit.log,indent=2))
