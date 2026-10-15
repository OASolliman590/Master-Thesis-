"""Export selected public specification artifacts with actual verification logs.
No data acquisition, model fitting, patient records or repository writes.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'_a_a1_export'
REPORT=OUT/'docs/validation/A_A1_SPEC_KIT_20261015'

def main():
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir()
    paths=['specs/A','specs/A1','specs/A_DATA_ACQUISITION_VALIDATION','reference/specs_A_before_20261015','reference/specs_A_DAV_before_20261015','tests/a_a1_spec_contract','docs/decisions/A_A1_INTEGRATED_SPEC_20261015.md','docs/execution/PAPER_A_A1_PACKET_01.md','docs/execution/PAPER_A_A1_CODEX_HANDOFF.md','docs/reviews/A_A1_INTEGRATION_REVIEW_20261015.md','AGENTS.md','CONTEXT.md','README.md']
    for rel in paths:
        src=ROOT/rel;dst=OUT/rel
        dst.parent.mkdir(parents=True,exist_ok=True)
        if src.is_dir(): shutil.copytree(src,dst,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        else: shutil.copy2(src,dst)
    REPORT.mkdir(parents=True,exist_ok=True)
    with (REPORT/'FOCUSED_TEST_LOG.txt').open('w') as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT/'tests/a_a1_spec_contract')))
    try:
        proc=subprocess.run([sys.executable,'-m','pytest','-q'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=120)
        full={'status':'PASS' if proc.returncode==0 else 'FAILED_OR_ENVIRONMENT_BLOCKED','exit_code':proc.returncode,'command':'python -m pytest -q','log':'REPOSITORY_TEST_LOG.txt'}
        (REPORT/'REPOSITORY_TEST_LOG.txt').write_text(proc.stdout)
    except subprocess.TimeoutExpired as exc:
        text=exc.stdout or b''
        if isinstance(text,bytes): text=text.decode(errors='replace')
        (REPORT/'REPOSITORY_TEST_LOG.txt').write_text(text+'\nTIMEOUT after 120 seconds; not a pass.\n')
        full={'status':'TIMEOUT_NOT_PASSED','command':'python -m pytest -q','timeout_seconds':120,'log':'REPOSITORY_TEST_LOG.txt'}
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    summary={'verified_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'git_commit':commit,'github_run_id':os.environ.get('GITHUB_RUN_ID'),'evidence_class':'SPECIFICATION_SCHEMA_AND_SYNTHETIC_ALGEBRA_ONLY','focused_tests':{'run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful()},'repository_suite':full,'historical_pipeline_tests':'NOT_RERUN','AIU_validation':'NOT_RUN','patient_admission':'NOT_PERFORMED','real_response_associated_analysis':'NOT_RUN','environment':{'python':sys.version,'platform':platform.platform(),'packages':{p:importlib.metadata.version(p) for p in ['jsonschema','referencing','pytest']}}}
    (REPORT/'VALIDATION_SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
    (REPORT/'REVIEW.md').write_text('# Executed package verification\n\nFocused document/schema/synthetic algebra tests: '+('PASS' if result.wasSuccessful() else 'FAIL')+'; '+str(result.testsRun)+' tests; '+str(len(result.failures))+' failures; '+str(len(result.errors))+' errors.\n\nRepository-wide pytest attempt: '+full['status']+'. Inspect REPOSITORY_TEST_LOG.txt; this result is not replaced by the focused result.\n\nHistorical implementation, AIU execution, patient linkage/admission and real biological/model analyses were not validated by this run. The package is a scientific/software specification, not a released clinical analysis.\n')
    (OUT/'START_HERE.md').write_text('# Paper A + A1 integrated Spec Kit\n\nStart with specs/A/README.md, specs/A1/README.md and specs/A_DATA_ACQUISITION_VALIDATION/README.md. The approved architecture is implemented in populated specification files; cohorts, numerical statistical settings and biological execution are not released.\n\nThe standalone next-agent instruction is docs/execution/PAPER_A_A1_CODEX_HANDOFF.md. Its first bounded packet is PAPER_A_A1_PACKET_01.md: recovery/intake contracts and synthetic or separately permitted format tests, not real response-associated analysis.\n\nActual verification results are in docs/validation/A_A1_SPEC_KIT_20261015/. Source commit: '+commit+'. The exact prior A and DAV trees are preserved under reference. Other historical repository links may require the complete repository checkout; the package is not the legacy pipeline/data archive.\n')
    records=[]
    for p in sorted(OUT.rglob('*')):
        if p.is_file():
            b=p.read_bytes();records.append({'path':str(p.relative_to(OUT)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
    manifest={'package_version':'1.0.0-review.20261015','git_commit':commit,'status':'SPECIFICATION_REVIEW_ONLY','patient_data_included':False,'files':records}
    (OUT/'PACKAGE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    allfiles=sorted(p for p in OUT.rglob('*') if p.is_file())
    (OUT/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(OUT))+'\n' for p in allfiles))
    print(json.dumps(summary,indent=2))
    return 0 if result.wasSuccessful() else 1

if __name__=='__main__': raise SystemExit(main())
