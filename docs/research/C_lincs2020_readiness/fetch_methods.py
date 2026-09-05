"""Small primary-source metadata/documentation audit; no matrices or credentials."""
import urllib.request, urllib.parse, json, hashlib, pathlib, datetime
out=pathlib.Path(__file__).parent
sha=json.loads((out/'cmapM_tree.json').read_text())['sha']
paths=['README.md','docs/SigToolDemo.md','sig_tools/resources/mortar.sigtools.SigQueryl1k.arg','sig_tools/+mortar/+sigtools/@SigQueryl1k/runAnalysis_.m','sig_tools/+mortar/+compute/@Connectivity/fastWTCSCore.m','sig_tools/+mortar/+compute/@Connectivity/getCombinedES.m','sig_tools/+mortar/+compute/@Connectivity/runCmapQuery.m','sig_tools/+mortar/+compute/@Connectivity/computeCmapScore.m']
urls={('cmapM_'+p.split('/')[-1]):'https://raw.githubusercontent.com/cmap/cmapM/'+sha+'/'+urllib.parse.quote(p,safe='/') for p in paths}
urls['field_definitions.xlsx']='https://s3.amazonaws.com/macchiato.clue.io/builds/LINCS2020/LINCS2020%20Release%20Metadata%20Field%20Definitions.xlsx'
urls['cmapPy_README.rst']='https://raw.githubusercontent.com/cmap/cmapPy/master/README.rst'
manifest=[]
for name,url in urls.items():
    rec={'url':url,'file':name,'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        with urllib.request.urlopen(url,timeout=45) as r:
            b=r.read(5_000_001)
            if len(b)>5_000_000: raise RuntimeError('size cap')
            rec.update(bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),headers=dict(r.headers))
        (out/name).write_bytes(b)
    except Exception as e: rec['error']=str(e)
    manifest.append(rec)
(out/'methods_manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps([{k:v for k,v in r.items() if k in ('file','bytes','error')} for r in manifest]))
