from __future__ import annotations

import importlib
from pathlib import Path

import pandas as pd
import pytest

de_models_module = importlib.import_module("src.pipeline.modules.06_within_cohort_de.de_models")
harmonize_module = importlib.import_module("src.pipeline.modules.06_within_cohort_de.harmonize")
ssgsea_module = importlib.import_module("src.pipeline.modules.09_immune_state.ssgsea")

resolve_de_backend = de_models_module.resolve_de_backend
harmonize_expression_for_assay = harmonize_module.harmonize_expression_for_assay
resolve_ssgsea_backend = ssgsea_module.resolve_ssgsea_backend


def test_harmonize_expression_for_assay_routes_to_expected_scale() -> None:
    expr = pd.DataFrame({"S1": [0.0, 3.0], "S2": [4.0, 7.0]}, index=["G1", "G2"])

    as_is, as_is_method = harmonize_expression_for_assay(expr, "log_normalized")
    assert as_is_method == "as_is_log_scale"
    assert as_is.equals(expr)

    logged, logged_method = harmonize_expression_for_assay(expr, "tpm")
    assert logged_method == "log2(x+1)"
    assert float(logged.loc["G2", "S2"]) == pytest.approx(3.0)


def test_resolve_de_backend_contracts() -> None:
    hard_exclude = {"methylation_beta", "unreadable"}
    assert (
        resolve_de_backend(
            assay_type="methylation_beta",
            count_like_matrix=False,
            hard_exclude_assays=hard_exclude,
        )
        == "excluded"
    )
    assert (
        resolve_de_backend(
            assay_type="raw_counts",
            count_like_matrix=True,
            hard_exclude_assays=hard_exclude,
        )
        == "count_model"
    )
    assert (
        resolve_de_backend(
            assay_type="log_normalized",
            count_like_matrix=False,
            hard_exclude_assays=hard_exclude,
        )
        == "limma_trend"
    )


def test_resolve_ssgsea_backend_requires_rscript_unless_legacy(tmp_path: Path) -> None:
    script = tmp_path / "ssgsea_gsva.R"
    script.write_text("#!/usr/bin/env Rscript\n", encoding="utf-8")

    assert (
        resolve_ssgsea_backend(
            legacy_rank_mean=True,
            rscript_path=None,
            ssgsea_script=script,
        )
        == "legacy_rank_mean_python"
    )
    with pytest.raises(RuntimeError, match="Rscript not found"):
        resolve_ssgsea_backend(
            legacy_rank_mean=False,
            rscript_path=None,
            ssgsea_script=script,
        )
    assert (
        resolve_ssgsea_backend(
            legacy_rank_mean=False,
            rscript_path="/usr/bin/Rscript",
            ssgsea_script=script,
        )
        == "gsva_ssgsea_r_backend"
    )
