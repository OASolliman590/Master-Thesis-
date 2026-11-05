from __future__ import annotations

import csv
from pathlib import Path

import pytest

from tools.r_bridge import run_r


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "r/scripts/freeze_checks/software_checks.R"


@pytest.mark.requires_r
def test_frozen_numerical_software_checks_run_under_renv(tmp_path):
    result = run_r(
        SCRIPT,
        {},
        {"seed": 20261102, "expected_outputs": ["checks.tsv"]},
        tmp_path / "software_checks",
    )
    with result.outputs["checks.tsv"].open(newline="", encoding="utf-8") as stream:
        checks = {row["check"]: row["value"] for row in csv.DictReader(stream, delimiter="\t")}

    assert checks["glmnet_seed"] == "20261102"
    assert checks["glmnet_jerr"] == "0"
    assert int(checks["glmnet_npasses"]) > 0
    assert float(checks["glmnet_direct_max_difference"]) <= 1e-6
    assert float(checks["glmnet_kkt_max_residual"]) <= 1e-6
    assert float(checks["glmnet_lambda_path_max_difference"]) <= 1e-6
    assert float(checks["fgsea_repeat_max_difference"]) <= 1e-12
    assert float(checks["fgsea_nproc_1_vs_2_max_difference"]) <= 1e-8
    assert float(checks["fgsea_different_seed_max_difference"]) > 1e-12
    assert checks["singscore_seed_independent"] == "TRUE"
    assert checks["singscore_background_changes_score"] == "TRUE"
    assert checks["singscore_direction_changes_score"] == "TRUE"
    assert checks["singscore_centering_changes_score"] == "TRUE"
    assert set(("jsonlite", "BiocManager", "glmnet", "fgsea", "singscore")) <= set(
        result.manifest["package_versions"]
    )
