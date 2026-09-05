"""Read installed package metadata; no installation or environment mutation."""
import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path

prefix = Path(sys.prefix)
packages = []
for path in sorted((prefix / 'conda-meta').glob('*.json')):
    raw = path.read_bytes()
    record = json.loads(raw)
    url = record.get('url', '')
    if not url.startswith('https://conda.anaconda.org/conda-forge/') or '?' in url:
        url = None  # Do not expose authenticated or unverified channel URLs.
    packages.append({k: record.get(k) for k in ['name', 'version', 'build', 'subdir', 'md5', 'sha256']} |
                    {'public_url': url, 'installed_metadata_sha256': hashlib.sha256(raw).hexdigest()})
print(json.dumps({'python': sys.version, 'prefix': str(prefix), 'scope': 'Installed metadata inventory; package archives and environment recreation not validated.',
                  'conda_packages': packages, 'python_distributions': sorted(
                      [{'name': d.metadata['Name'], 'version': d.version} for d in importlib.metadata.distributions()],
                      key=lambda x: x['name'].lower())}, indent=2))
