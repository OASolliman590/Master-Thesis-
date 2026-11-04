from __future__ import annotations

import csv
from pathlib import Path
import random
import shutil

import pytest

from tools.r_bridge import run_r


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.requires_r
def test_deseq2_keeps_metric_families_separate_and_refuses_small_arms(tmp_path):
    if not shutil.which("Rscript"):
        pytest.skip("Rscript is unavailable")

    profiles = []
    for family, n_r, n_nr in (("RECIST", 3, 3), ("expansion", 3, 3), ("pathology", 2, 3)):
        for arm, count in (("R", n_r), ("NR", n_nr)):
            for index in range(count):
                profiles.append({
                    "cohort": "invented_study",
                    "profile_id": f"synthetic_{family}_{arm}_{index}",
                    "patient_id": f"synthetic_{family}_{arm}_{index}",
                    "compartment": "T/NK",
                    "endpoint_family": family,
                    "outcome_label": arm,
                    "eligible": "TRUE",
                })
    genes = [f"GENE_{index}" for index in range(20)]
    random_source = random.Random(20261103)
    count_path = tmp_path / "synthetic_counts.tsv"
    clinical_path = tmp_path / "synthetic_clinical.tsv"
    with count_path.open("w", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t")
        writer.writerow(["gene", *[row["profile_id"] for row in profiles]])
        for gene_index, gene in enumerate(genes):
            values = []
            for profile in profiles:
                value = random_source.randint(200, 2_000)
                if gene_index < 5 and profile["outcome_label"] == "R":
                    value *= 2
                values.append(value)
            writer.writerow([gene, *values])
    with clinical_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(profiles[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(profiles)

    result = run_r(
        ROOT / "r/scripts/sc3_deseq2.R",
        {"counts": count_path, "clinical": clinical_path},
        {"expected_outputs": ["de_results.tsv", "de_refusals.tsv"], "design": "~ response", "fdr": 0.10},
        tmp_path / "sc3_synthetic_result",
    )
    with result.outputs["de_results.tsv"].open(newline="") as stream:
        de_rows = list(csv.DictReader(stream, delimiter="\t"))
    with result.outputs["de_refusals.tsv"].open(newline="") as stream:
        refusals = list(csv.DictReader(stream, delimiter="\t"))

    comparisons = {row["endpoint_family"] for row in de_rows}
    assert comparisons == {"RECIST", "expansion"}
    assert all("pathology" not in row["comparison_id"] for row in de_rows)
    assert len({row["comparison_id"] for row in de_rows}) == 2
    assert len(refusals) == 1
    assert refusals[0]["endpoint_family"] == "pathology"
    assert refusals[0]["reason"] == "fewer_than_three_patients_per_arm"
