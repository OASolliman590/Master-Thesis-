#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, re, sys
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'specs/D/revision_20261015'

def fail(msg):
    raise AssertionError(msg)

def check():
    decisions = (BASE/'DECISIONS_DA_DH.md').read_text(encoding='utf-8')
    approval = (ROOT/'APPROVAL_RECORD.md').read_text(encoding='utf-8')
    analysis = (BASE/'ANALYSIS_AND_ENDPOINTS.md').read_text(encoding='utf-8')
    ontology = (BASE/'CELL_STATE_ONTOLOGY.md').read_text(encoding='utf-8')
    architecture = (BASE/'VIRTUAL_CELL_ARCHITECTURE.md').read_text(encoding='utf-8')

    for key in [f'D-{c}' for c in 'ABCDEFGH']:
        if key not in decisions or key not in approval:
            fail(f'missing approved decision {key}')
    for token in ['theta =', 'same-supported-drug', 'Positive `theta` favours']:
        if token not in analysis:
            fail(f'missing D1 invariant: {token}')
    if 'UNSUPPORTED' not in ontology or 'B-cell/TLS' not in ontology:
        fail('missing unsupported B/TLS rule')
    if 'D2-PAIR' not in architecture or 'not a full TME' not in architecture:
        fail('missing D2-PAIR scope limit')

    ticket_files = sorted((BASE/'tickets').glob('D-R*.md'))
    if len(ticket_files) != 19:
        fail(f'expected 19 D-R tickets, found {len(ticket_files)}')

    schema_files = sorted((BASE/'schemas').glob('*.schema.json'))
    example_files = sorted((BASE/'examples').glob('*.example.json'))
    if len(schema_files) != 16 or len(example_files) != 16:
        fail(f'expected 16 schemas/examples, found {len(schema_files)}/{len(example_files)}')
    for sf in schema_files:
        name = sf.name.replace('.schema.json','')
        ef = BASE/'examples'/f'{name}.example.json'
        sch = json.loads(sf.read_text(encoding='utf-8'))
        ex = json.loads(ef.read_text(encoding='utf-8'))
        Draft202012Validator.check_schema(sch)
        Draft202012Validator(sch).validate(ex)

    forbidden = []
    for p in ROOT.rglob('*'):
        if p.is_file() and p.suffix.lower() in {'.md','.txt','.tsv','.json'} and 'provenance/PAPER_D_SCIENTIFIC_REVISION_REPORT.md' not in str(p):
            txt = p.read_text(encoding='utf-8', errors='ignore')
            if re.search(r'\b(TODO|TBD)\b', txt):
                forbidden.append(str(p.relative_to(ROOT)))
    if forbidden:
        fail('unresolved placeholder tokens: ' + ', '.join(forbidden))

    print(json.dumps({
        'status':'PASS_SPECIFICATION_SOFTWARE_CHECKS_ONLY',
        'approved_decisions':8,
        'tickets':len(ticket_files),
        'schemas_validated':len(schema_files),
        'examples_validated':len(example_files),
        'biological_validation':False,
        'model_inference_run':False,
        'simulation_run':False
    }, indent=2))

if __name__ == '__main__':
    try:
        check()
    except Exception as e:
        print(f'FAIL: {e}', file=sys.stderr)
        raise
