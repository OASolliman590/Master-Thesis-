from __future__ import annotations

import csv
import json

import pytest

from tools.a_meta.__main__ import main


def test_real_cohort_effects_are_refused_without_allow_outcomes(tmp_path):
    with pytest.raises(SystemExit, match="explicit --allow-outcomes"):
        main(["effects", "--cohort", "liu2019", "--results", str(tmp_path)])

    assert not (tmp_path / "liu2019").exists()


def test_real_effect_table_synthesis_is_refused_without_allow_outcomes(tmp_path):
    effect_dir = tmp_path / "synthetic-test-input"
    effect_dir.mkdir()
    effects_path = effect_dir / "effects.tsv"
    with effects_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(["study"])
    (effect_dir / "manifest.json").write_text(
        json.dumps({"data_classification": "real"}),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="explicit --allow-outcomes"):
        main([
            "synthesize",
            "--effects",
            str(effects_path),
            "--stratum",
            "per_cancer",
            "--results",
            str(tmp_path / "results"),
        ])

    assert not (tmp_path / "results").exists()
