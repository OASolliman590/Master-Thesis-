"""Run bounded specification tests and save an honest machine-readable receipt."""
from pathlib import Path
from datetime import datetime, timezone
import importlib.metadata
import io
import json
import platform
import sys
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
suite=unittest.defaultTestLoader.discover(str(HERE),pattern='test_*.py')
stream=io.StringIO()
result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
(HERE/'TEST_OUTPUT.txt').write_text(stream.getvalue())
receipt={
    'checked_at_utc':datetime.now(timezone.utc).isoformat(),
    'scope':'v2-synthetic-schema-and-declared-contract-checks-only',
    'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
    'skips':len(result.skipped),'success':result.wasSuccessful(),
    'schemas_checked':5,'synthetic_examples_checked':7,
    'selected_capability_combinations_checked':4096,
    'python':platform.python_version(),'jsonschema':importlib.metadata.version('jsonschema'),
    'scientific_authorisation':False,'biological_validation':False,
    'production_implementation':False,'real_model_noninterference_tested':False,
    'not_run':['ODE simulation or fitting','upstream numerical parity','actual scientific data admission',
               'real-fit held-out isolation','AIU execution','independent biological evaluation',
               'prospective experimental validation','clinical evaluation'],
    'duplicate_distribution_notice':'Same reference suite in core and optional extension; do not count copies as independent tests.'
}
(HERE/'QA_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(stream.getvalue())
print(json.dumps(receipt,indent=2))
raise SystemExit(0 if result.wasSuccessful() else 1)
