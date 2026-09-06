from pathlib import Path
import urllib.request,hashlib,json,datetime
out=Path(r'E:\Master_Thesis\planning\next_evidence\B_TCGA_cellularity')
u='https://api.gdc.cancer.gov/data/4f277128-f793-4354-a13d-30cc7fe9f6b5'
p=out/'TCGA_mastercalls.abs_tables_JSedit.fixed.txt'
if not p.exists():
 with urllib.request.urlopen(u,timeout=45) as r:
  n=r.headers.get('Content-Length')
  if n and int(n)>3000000: raise ValueError(n)
  b=r.read(3000001)
  if len(b)>3000000: raise ValueError('cap exceeded')
  p.write_bytes(b)
b=p.read_bytes()
receipt={'url':u,'source_page':'https://gdc.cancer.gov/about-data/publications/PanCan-CellOfOrigin','bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(out/'retrieval.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps(receipt));print(b.decode().splitlines()[:3])
