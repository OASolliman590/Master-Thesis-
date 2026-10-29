from pathlib import Path

import pytest

from tools.a_dav.admit import run_signed_admission
from tools.a_dav.ingest import IngestError, run_ingest


@pytest.mark.parametrize('cohort', ['gse115821', 'gse126044'])
def test_parked_cohort_ingest_refuses_before_writing(cohort: str, tmp_path: Path) -> None:
    output = tmp_path / 'output'
    with pytest.raises(IngestError, match='PARKED'):
        run_ingest(cohort, 'A_BASELINE_BIO', tmp_path / 'missing-store', output, allow_external_out=True)
    assert not output.exists()


def test_parked_cohort_admission_refuses_before_validation(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match='PARKED'):
        run_signed_admission({}, {'status': 'PARKED', 'parked_reason': 'invented reason'}, {}, tmp_path / 'output')
    assert not (tmp_path / 'output').exists()


def test_admit_cli_reports_parked_without_requiring_other_inputs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from tools.a_dav.admit import main
    with pytest.raises(SystemExit) as caught:
        main(['--field-map', 'tools/a_dav/field_maps/gse115821.json', '--out', str(tmp_path / 'output')])
    assert caught.value.code == 2
    assert 'PARKED' in capsys.readouterr().err
    assert not (tmp_path / 'output').exists()
