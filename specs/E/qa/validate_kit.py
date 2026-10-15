"""Run local contract checks and emit a level-specific receipt."""
import json,sys,unittest,datetime,platform
from pathlib import Path
from importlib.metadata import version
from e_contracts import validate_all
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
 result=validate_all()
 suite=unittest.defaultTestLoader.discover(str(ROOT/'qa'),pattern='test_contracts.py')
 run=unittest.TextTestRunner(verbosity=2).run(suite)
 result.update(timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),python=platform.python_version(),jsonschema=version('jsonschema'),tests_run=run.testsRun,failures=len(run.failures),errors=len(run.errors),skips=len(run.skipped),success=run.wasSuccessful(),validation_level='software_contract',biological_validation=False,not_run=['ODE positivity/mass balance','solver and event convergence','upstream numerical parity','real source acquisition/cache restart','scientific deduplication adjudication','real-fit heldout isolation','PK or biological calibration','independent empirical evaluation','prospective biological validation'])
 (ROOT/'qa/QA_RECEIPT.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2))
 sys.exit(0 if run.wasSuccessful() else 1)
