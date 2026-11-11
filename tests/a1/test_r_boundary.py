from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tools.r_bridge import _r_environment


ROOT = Path(__file__).resolve().parents[2]
R_PROJECT = ROOT / "r"
R_SCRIPT = R_PROJECT / "R" / "a_long.R"
RSCRIPT = shutil.which("Rscript")


@pytest.mark.skipif(RSCRIPT is None, reason="Rscript is unavailable")
def test_a_long_r_script_parses_in_configured_r():
    result = subprocess.run(
        [
            RSCRIPT,
            "--no-save",
            "--no-restore",
            "--no-site-file",
            "-e",
            'invisible(parse(file="R/a_long.R"))',
        ],
        cwd=R_PROJECT,
        env=_r_environment(),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(RSCRIPT is None, reason="Rscript is unavailable")
def test_direct_r_refuses_protected_path_before_reading_payload(tmp_path):
    sentinel = tmp_path / "copy-of-IMVIGOR210-invented.tsv"
    sentinel.write_text("DO_NOT_READ_SENTINEL\n", encoding="utf-8")
    config_path = tmp_path / "direct-r-config.json"
    output_dir = tmp_path / "direct-r-output"
    config_path.write_text(
        json.dumps(
            {
                "config": {
                    "mode": "fit_two_timepoint",
                    "boundary": {
                        "data_classification": "real",
                        "source_paths": {"design": str(sentinel)},
                        "retention_dir": str(tmp_path / "retention"),
                    },
                },
                "inputs": {"design": str(sentinel)},
                "expected_outputs": ["effects.tsv"],
                "output_dir": str(output_dir),
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [RSCRIPT, "--no-save", "--no-restore", "--no-site-file", str(R_SCRIPT), str(config_path)],
        cwd=R_PROJECT,
        env=_r_environment(),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    assert result.returncode != 0
    assert "always refuses IMvigor210" in result.stderr
    assert "DO_NOT_READ_SENTINEL" not in result.stdout + result.stderr
    assert not output_dir.exists()


@pytest.mark.skipif(RSCRIPT is None, reason="Rscript is unavailable")
def test_direct_r_requires_outcome_opt_in_before_hashing_real_payload(tmp_path):
    sentinel = tmp_path / "invented-real-classified-source.tsv"
    sentinel.write_text("DO_NOT_READ_OUTCOME_SENTINEL\n", encoding="utf-8")
    manifest = tmp_path / "invented-real-manifest.json"
    manifest.write_text(json.dumps({
        "schema": "a_long_release_input_manifest_v1",
        "data_classification": "PRIVATE_PATIENT_LEVEL",
        "cohort_ids": ["invented-direct-r-cohort"],
    }), encoding="utf-8")
    config_path = tmp_path / "invented-direct-r-config.json"
    output_dir = tmp_path / "not-created-model-output"
    retention_dir = tmp_path / "not-created-retention"
    output_dir.mkdir()
    retention_dir.mkdir()
    config_path.write_text(json.dumps({
        "config": {
            "mode": "fit_two_timepoint",
            "boundary": {
                "data_classification": "real",
                "manifest_kind": "a_long_release_input_manifest_v1",
                "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
                "cohorts": ["invented-direct-r-cohort"],
                "source_paths": {"design": str(sentinel)},
                "release_scope": "N13_TWO_TIMEPOINT",
                "operation": "fit_two_timepoint",
                "retention_dir": str(retention_dir),
            },
        },
        "inputs": {"design": str(sentinel), "provenance_manifest": str(manifest)},
        "expected_outputs": ["effects.tsv"],
        "output_dir": str(output_dir),
    }), encoding="utf-8")

    result = subprocess.run(
        [RSCRIPT, "--no-save", "--no-restore", "--no-site-file", str(R_SCRIPT), str(config_path)],
        cwd=R_PROJECT,
        env=_r_environment(),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    assert result.returncode != 0
    assert "explicit allow_outcomes=true" in result.stderr
    assert "DO_NOT_READ_OUTCOME_SENTINEL" not in result.stdout + result.stderr
    assert list(output_dir.iterdir()) == []
