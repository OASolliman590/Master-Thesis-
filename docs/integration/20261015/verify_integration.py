"""Read-only integration document/schema/manifest verification, no biological jobs."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,sys
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

def verify_git_snapshot(root, failures, ref='HEAD'):
    """Verify exact staged/committed bytes, including ignored files omitted from Git."""
    manifest=root/'docs/integration/20261015/FREEZE_MANIFEST.json'
    if not manifest.is_file():
        failures.append(['FREEZE_MANIFEST.json','required manifest missing']);return 0
    records=json.loads(manifest.read_text()).get('files',[])
    if not records:
        failures.append(['FREEZE_MANIFEST.json','empty manifest']);return 0
    # The snapshot must also contain the exact current manifest, excluded from its own hash list.
    records=records+[{'path':'docs/integration/20261015/FREEZE_MANIFEST.json',
                     'sha256':hashlib.sha256(manifest.read_bytes()).hexdigest()}]
    for rec in records:
        rel=Path(rec['path'])
        if rel.is_absolute() or '..' in rel.parts or '\n' in str(rel):
            failures.append([str(rel),'unsafe Git snapshot path']);return 0
    prefix='' if ref=='INDEX' else ref
    query=''.join(prefix+':'+rec['path']+'\n' for rec in records)
    result=subprocess.run(['git','cat-file','--batch'],cwd=root,input=query.encode(),capture_output=True)
    if result.returncode:
        failures.append(['git snapshot','cannot read '+ref]);return 0
    data=result.stdout;pos=0;verified=0
    for rec in records:
        end=data.find(b'\n',pos);header=data[pos:end];pos=end+1
        if header.endswith(b' missing'):
            failures.append([rec['path'],'missing from Git '+ref]);continue
        fields=header.split()
        if len(fields)!=3 or fields[1]!=b'blob':
            failures.append([rec['path'],'invalid Git object']);return verified
        size=int(fields[2]);content=data[pos:pos+size];pos+=size+1
        if hashlib.sha256(content).hexdigest()!=rec['sha256']:
            failures.append([rec['path'],'Git '+ref+' content hash mismatch'])
        else:verified+=1
    return verified

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--git-ref',default='HEAD',help='Commit/tag, or INDEX for staged bytes')
    parser.add_argument('--working-tree-only',action='store_true',help='Construction check only; NOT publication acceptance')
    parser.add_argument('--pre-freeze',action='store_true')
    args=parser.parse_args()
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
    hashes=verify_manifest(ROOT,failures,allow_missing=args.pre_freeze)
    git_hashes=0 if args.working_tree_only else verify_git_snapshot(ROOT,failures,args.git_ref)
    print(json.dumps({'git_ref':None if args.working_tree_only else args.git_ref,'git_hashes':git_hashes,'publication_check':not args.working_tree_only,'schemas':schemas,'D_examples':examples,'entry_links':links,'manifest_hashes':hashes,'failures':failures},indent=2))
    return bool(failures)
if __name__=='__main__':sys.exit(main())
