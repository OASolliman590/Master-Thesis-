"""One local metadata catalogue pointing to separate, validated cohort tables."""
from __future__ import annotations

import csv
import json
import os
import sqlite3
import tempfile
from pathlib import Path

from . import core

SOURCE_DIR = core.ROOT / 'docs/cohorts'
_APPLEDOUBLE_MAGIC = b'\x00\x05\x16\x07'


def read_tsv(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream, delimiter='\t'))


def build_catalog(output=None, build_results=None):
    output = core.safe_path(Path(output) if output else core.RUNTIME / 'data_repository')
    if not output.resolve().is_relative_to(core.RUNTIME.resolve()):
        raise ValueError('Catalogue belongs in private runtime')
    output.mkdir(parents=True, exist_ok=True)
    report = output / 'build_report.json'
    if build_results is None and report.exists():
        build_results = json.loads(report.read_text())
    build_results = build_results or {}
    cohorts = []
    for cohort, source in core.registry().items():
        row = dict(source)
        row.update(table_status='', genes='', patients='', approval_status='',
                   expression_path='', clinical_path='', caveats_path='', manifest_path='')
        role = source['role'].lower()
        if cohort.lower().startswith('imvigor210') or 'final test' in role:
            row['table_status'] = 'UNTOUCHED_FINAL_TEST'
        elif 'excluded' in role or 'combination' in role:
            row['table_status'] = 'excluded from A/B; retained in inventory'
        elif cohort not in core.SUPPORTED_COHORTS:
            row['table_status'] = 'blocked, because ' + (source['caveats'] or 'local source tables are not yet prepared')
        else:
            try:
                manifest = core.validate(cohort)
            except (OSError, ValueError, KeyError, StopIteration) as exc:
                reason = str(exc) if not isinstance(exc, FileNotFoundError) else build_results.get(cohort, {}).get('reason', 'no validated local table; run build for the specific blocker')
                # No host-specific paths in the portable metadata catalogue.
                reason = reason.replace(str(core.ROOT), '.')
                row['table_status'] = 'blocked, because ' + reason
            else:
                row.update(table_status='table ready', genes=str(manifest['genes']),
                           patients=str(manifest['patients']), approval_status=manifest['status'])
                base = core.RUNTIME / cohort / 'simple'
                for key, filename in [('expression_path', 'expression.tsv'), ('clinical_path', 'clinical.tsv'),
                                      ('caveats_path', 'caveats.md'), ('manifest_path', 'manifest.json')]:
                    row[key] = str((base / filename).relative_to(core.ROOT))
        cohorts.append(row)
    tables = {'cohorts': cohorts, 'resources': read_tsv(SOURCE_DIR / 'RESOURCES.tsv'),
              'icbatlas_index': read_tsv(SOURCE_DIR / 'ICBATLAS_INDEX.tsv')}
    # Only metadata is copied. Patient matrices remain in their cohort directories.
    with tempfile.TemporaryDirectory(prefix='.catalog-', dir=output) as stage_name:
        stage = Path(stage_name)
        with sqlite3.connect(stage / 'catalog.sqlite') as db:
            for name, rows in tables.items():
                if not rows:
                    raise ValueError(f'Empty catalogue input: {name}')
                fields = list(rows[0])
                if any(not key.replace('_', '').isalnum() for key in fields):
                    raise ValueError('Invalid catalogue column')
                db.execute(f'CREATE TABLE {name} (' + ','.join(f'"{key}" TEXT' for key in fields) + ')')
                db.executemany(f'INSERT INTO {name} VALUES (' + ','.join('?' for _ in fields) + ')',
                               [[row.get(key, '') for key in fields] for row in rows])
                with (stage / f'{name}.tsv').open('w', newline='') as stream:
                    writer = csv.DictWriter(stream, fieldnames=fields, delimiter='\t', lineterminator='\n')
                    writer.writeheader()
                    writer.writerows(rows)
        (stage / 'README.md').write_text(
            '# Local data repository\n\nOpen cohorts.tsv for status, dimensions and paths. '
            'Paths are relative to the repository root. Use catalog.sqlite for SQL.\n\n'
            'Table ready means file hashes and patient alignment passed. Approval is a separate column. '
            'Pending tables retain source features and labels, including unknown timing and duplicate features; '
            'read caveats.md before use. No response analysis is authorized.\n\n'
            'resources.tsv lists other tracks and pending sources. icbatlas_index.tsv is supplied study metadata, '
            'not patient data or verified eligibility. IMvigor210 is never loaded.\n')
        (stage / 'build_report.json').write_text(json.dumps(build_results, indent=2, sort_keys=True) + '\n')
        for path in _publication_files(stage):
            os.replace(path, output / path.name)
    return {'database': str((output / 'catalog.sqlite').relative_to(core.ROOT)),
            'cohorts': len(cohorts), 'tables_ready': sum(r['table_status'] == 'table ready' for r in cohorts),
            'resources': len(tables['resources']), 'icbatlas_entries': len(tables['icbatlas_index'])}


def _publication_files(stage):
    """Exclude valid filesystem AppleDouble sidecars before moving stage files."""
    files = []
    sidecars = []
    for path in list(stage.iterdir()):
        if not path.name.startswith('._'):
            files.append(path)
            continue
        if path.is_symlink() or path.is_dir():
            raise ValueError(f'Unexpected AppleDouble sidecar type: {path.name}')
        try:
            with path.open('rb') as stream:
                valid = stream.read(4) == _APPLEDOUBLE_MAGIC
        except OSError as error:
            raise ValueError(f'Could not validate AppleDouble sidecar: {path.name}') from error
        if not valid:
            raise ValueError(f'Invalid AppleDouble sidecar: {path.name}')
        sidecars.append(path)
    for sidecar in sidecars:
        try:
            sidecar.unlink()
        except FileNotFoundError:
            # Renaming the base file may remove its filesystem-created sidecar.
            continue
    return files
