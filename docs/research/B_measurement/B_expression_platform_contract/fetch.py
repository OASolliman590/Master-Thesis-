"""Small public annotation/metadata requests; 15MB total, 10MB per object."""
import datetime,hashlib,json,pathlib,sys,urllib.request
P=pathlib.Path(__file__).parent
def fetch(name,url,cap=1_000_000):
    log=json.loads((P/'requests.json').read_text()) if (P/'requests.json').exists() else []
    cap=min(cap,10_000_000,15_000_000-sum(r.get('bytes',0) for r in log))
    rec={'file':name,'url':url,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cap_bytes':cap}
    try:
        if cap<=0:raise ValueError('Total budget exhausted')
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 source annotation audit'})
        with urllib.request.urlopen(req,timeout=20) as r:
            rec['content_type']=r.headers.get('Content-Type');rec['last_modified']=r.headers.get('Last-Modified')
            if int(r.headers.get('Content-Length','0'))>cap:raise ValueError('Declared size exceeds cap; body not read')
            data=r.read(cap);rec['bytes']=len(data)
            if len(data)==cap:raise ValueError('Reached cap; completeness unconfirmed; body discarded')
            (P/name).write_bytes(data);rec['sha256']=hashlib.sha256(data).hexdigest()
    except Exception as e:rec['error']=str(e)
    log.append(rec);(P/'requests.json').write_text(json.dumps(log,indent=2));print(json.dumps(rec))
if __name__=='__main__':fetch(sys.argv[1],sys.argv[2],int(sys.argv[3]) if len(sys.argv)>3 else 1_000_000)
