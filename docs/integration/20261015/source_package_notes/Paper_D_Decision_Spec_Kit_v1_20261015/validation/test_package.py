import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_package_checker_passes():
    p = subprocess.run([sys.executable, str(ROOT/'validation/check_package.py')], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    payload = json.loads(p.stdout)
    assert payload['status'] == 'PASS_SPECIFICATION_SOFTWARE_CHECKS_ONLY'
    assert payload['approved_decisions'] == 8
    assert payload['tickets'] == 19
    assert payload['schemas_validated'] == 16
    assert payload['examples_validated'] == 16
    assert payload['biological_validation'] is False
