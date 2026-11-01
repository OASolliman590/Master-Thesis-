import csv
import sqlite3

from tools.a_cohorts import catalog


def test_catalog_exposes_verified_tables_and_never_opens_locked_cohort(tmp_path, monkeypatch):
    root = tmp_path
    runtime = root / '.scratch/runtime'
    runtime.mkdir(parents=True)
    monkeypatch.setattr(catalog.core, 'ROOT', root)
    monkeypatch.setattr(catalog.core, 'RUNTIME', runtime)
    monkeypatch.setattr(catalog.core, 'registry', lambda: {
        'good': {'cohort_id': 'good', 'study': 'Good', 'role': 'development', 'status': 'pending', 'caveats': 'timing unknown'},
        'broken': {'cohort_id': 'broken', 'study': 'Broken', 'role': 'development', 'status': 'pending', 'caveats': ''},
        'imvigor210': {'cohort_id': 'imvigor210', 'study': 'Locked', 'role': 'FINAL TEST (locked)', 'status': 'locked', 'caveats': ''},
        'later': {'cohort_id': 'later', 'study': 'Later', 'role': 'development', 'status': 'candidate', 'caveats': 'source not checked'},
    })
    monkeypatch.setattr(catalog.core, 'SUPPORTED_COHORTS', {'good', 'broken', 'imvigor210'})
    calls = []
    def validate(cohort):
        calls.append(cohort)
        if cohort == 'broken':
            raise ValueError('Output hash mismatch')
        assert cohort == 'good'
        return {'genes': 3, 'patients': 2, 'status': 'PENDING_BATCH_REVIEW'}
    monkeypatch.setattr(catalog.core, 'validate', validate)
    monkeypatch.setattr(catalog, 'SOURCE_DIR', root / 'docs/cohorts')
    catalog.SOURCE_DIR.mkdir(parents=True)
    (catalog.SOURCE_DIR / 'RESOURCES.tsv').write_text('resource_id\tstatus\nexternal\tpending\n')
    (catalog.SOURCE_DIR / 'ICBATLAS_INDEX.tsv').write_text('study\tevidence\nStudy\tprovided_index\n')
    result = catalog.build_catalog()
    db = sqlite3.connect(root / result['database'])
    db.row_factory = sqlite3.Row
    rows = {r['cohort_id']: dict(r) for r in db.execute('SELECT * FROM cohorts')}
    assert rows['good']['table_status'] == 'table ready'
    assert rows['good']['approval_status'] == 'PENDING_BATCH_REVIEW'
    assert rows['good']['expression_path'] == '.scratch/runtime/good/simple/expression.tsv'
    assert rows['broken']['table_status'] == 'blocked, because Output hash mismatch'
    assert rows['broken']['expression_path'] == ''
    assert rows['imvigor210']['table_status'] == 'UNTOUCHED_FINAL_TEST'
    assert rows['later']['table_status'].startswith('blocked, because')
    assert calls == ['good', 'broken']
    assert db.execute('SELECT count(*) FROM resources').fetchone()[0] == 1
    assert db.execute('SELECT count(*) FROM icbatlas_index').fetchone()[0] == 1
    assert not any('patient' in r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'"))
    db.close()
    # Rebuilding metadata must be safe and must not append duplicate entries.
    assert catalog.build_catalog()['cohorts'] == 4
    with (runtime / 'data_repository/cohorts.tsv').open() as f:
        assert len(list(csv.DictReader(f, delimiter='\t'))) == 4
