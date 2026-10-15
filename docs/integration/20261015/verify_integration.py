"""Read-only integration document/schema/manifest verification, no biological jobs."""
from pathlib import Path
import hashlib,json,re,sys
from jsonschema.validators import validator_for
ROOT=Path(__file__).resolve().parents[3]

def verify_manifest(root, failures, allow_missing=False):
    manifest=root/'docs/integration/20261015/FREEZE_MANIFEST.json'
    if not manifest.is_file():
        if not allow_missing:failures.append(['FREEZE_MANIFEST.json','required manifest missing'])
        return 0
    records=json.loads(manifest.read_text()).get('files',[])
    if not records:failures.append(['FREEZE_MANIFEST.json','empty manifest'])
    seen=set()
    for rec in records:
        rel=Path(rec['path'])
        if rel.is_absolute() or '..' in rel.parts or str(rel) in seen:
            failures.append([str(rel),'unsafe or duplicate manifest path']);continue
        seen.add(str(rel));p=root/rel
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=rec['sha256']:
            failures.append([str(rel),'freeze hash mismatch'])
    return len(records)

def main():
    failures=[];schemas=0;examples=0;links=0
    for base in ['specs/A','specs/A1','specs/A_DATA_ACQUISITION_VALIDATION','specs/B/revision_20260928','specs/C/revision_20261015','specs/D/revision_20261015','specs/E','specs/E_LAST']:
        for p in (ROOT/base).rglob('*.json'):
            x=json.loads(p.read_text())
            if isinstance(x,dict) and '$schema' in x:
                try:validator_for(x).check_schema(x);schemas+=1
                except Exception as e:failures.append([str(p.relative_to(ROOT)),str(e)])
    d=ROOT/'specs/D/revision_20261015'
    for p in (d/'examples').glob('*.example.json'):
        schema=d/'schemas'/p.name.replace('.example.json','.schema.json')
        if not schema.exists():failures.append([str(p.relative_to(ROOT)),'missing schema']);continue
        x=json.loads(schema.read_text());v=validator_for(x)(x)
        try:v.validate(json.loads(p.read_text()));examples+=1
        except Exception as e:failures.append([str(p.relative_to(ROOT)),str(e)])
    # Canonical entries plus authored dossier; archival package notes deliberately retain old context.
    entries=[ROOT/'START_HERE.md']+[ROOT/'specs'/p/'README.md' for p in ['A','A1','B','C','D','E','E_LAST']]
    entries+=list((ROOT/'docs/integration/20261015').glob('*.md'))
    for p in entries:
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
            if '://' in target or target.startswith('#'):continue
            target=target.split('#')[0]
            if not (p.parent/target).exists():failures.append([str(p.relative_to(ROOT)),'broken link '+target])
            links+=1
    hashes=verify_manifest(ROOT,failures,allow_missing='--pre-freeze' in sys.argv)
    print(json.dumps({'schemas':schemas,'D_examples':examples,'entry_links':links,'manifest_hashes':hashes,'failures':failures},indent=2))
    return bool(failures)
if __name__=='__main__':sys.exit(main())
