"""Record actual local/AIU format checks; never retrieve or modify source data."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    manifest_path = Path(__file__).with_name('fixture_manifest.json')
    expected_path = Path(__file__).with_name('real_summaries_expected.json')
    manifest = json.loads(manifest_path.read_text())
    expected = json.loads(expected_path.read_text())
    args.output_dir.mkdir(parents=True, exist_ok=False)
    records = []
    for name, entry in manifest['formats'].items():
        output = (args.output_dir / (name + '.json')).resolve()
        command = [sys.executable, '-m', 'tools.b_formats', 'inspect', '--format', name,
                   '--input', str(root / entry['path']), '--source-sha256', entry['source_sha256'],
                   '--completeness', entry['expected_completeness'], '--output', str(output)]
        try:
            result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=60)
            record = {'format': name, 'command': command, 'exit_code': result.returncode,
                      'stderr': result.stderr, 'expected_fields_match': False}
            if result.returncode == 0:
                content = output.read_bytes()
                summary = json.loads(content)
                record['summary_sha256'] = hashlib.sha256(content).hexdigest()
                record['actual_input_bytes'] = summary['actual_bytes']
                record['actual_input_sha256'] = summary['actual_source_sha256']
                record['expected_fields_match'] = all(
                    summary['format_summary'].get(key) == value
                    for key, value in expected[name].items())
        except (OSError, subprocess.TimeoutExpired, ValueError, KeyError) as error:
            record = {'format': name, 'command': command, 'exit_code': None,
                      'expected_fields_match': False, 'error_type': type(error).__name__}
        records.append(record)
    checked_files = [manifest_path, expected_path, root / 'tools/b_formats/__main__.py',
                     root / 'tools/b_formats/__init__.py', Path(__file__)]
    passed = all(item['exit_code'] == 0 and item['expected_fields_match'] for item in records)
    receipt = {'scope': 'four real format inspections only; no biological validation',
               'python': sys.version, 'executable': sys.executable, 'platform': platform.platform(),
               'passed': passed, 'code_and_contract_sha256': {
                   path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in checked_files}, 'checks': records}
    (args.output_dir / 'run.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': passed, 'checked_formats': len(records), 'run': str(args.output_dir / 'run.json')}))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
