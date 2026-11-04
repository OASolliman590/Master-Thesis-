from __future__ import annotations

import csv
import hashlib
from pathlib import Path
import random
import shutil

import pytest

pytest.importorskip("pandas", reason="run with an analysis Python environment")

from tools.r_bridge import RScriptError, run_r
from tools.sc.sc3 import write_sc3_r_synthetic_manifest


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.requires_r
def test_deseq2_uses_verified_patient_groups_and_keeps_metrics_separate(tmp_path):
    if not shutil.which("Rscript"):
        pytest.skip("Rscript is unavailable")

    profiles = []
    groups = []
    for group_index, family in enumerate(("RECIST", "expansion"), start=1):
        group_id = f"sc3_group_{group_index}"
        group_profiles = []
        for arm in ("R", "NR"):
            for index in range(3):
                patient = f"synthetic_{family}_{arm}_{index}"
                row = {
                    "cohort": "invented_study",
                    "profile_id": f"synthetic_profile_{family}_{arm}_{index}",
                    "patient_id": patient,
                    "sample_id": f"synthetic_specimen_{family}_{arm}_{index}",
                    "compartment": "T/NK",
                    "endpoint_family": family,
                    "response_metric": "T-cell expansion" if family == "expansion" else "RECIST",
                    "outcome_label": arm,
                    "eligible": "TRUE",
                    "sc3_group_id": group_id,
                }
                profiles.append(row)
                group_profiles.append(row["profile_id"])
        groups.append({
            "group_id": group_id,
            "cohort": "invented_study",
            "compartment": "T/NK",
            "endpoint_family": family,
            "n_R": 3,
            "n_NR": 3,
            "profile_count": 6,
            "profile_ids_sha256": hashlib.sha256("\n".join(sorted(group_profiles)).encode("utf-8")).hexdigest(),
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

    script = ROOT / "r/scripts/sc3_deseq2.R"
    expected = ["de_results.tsv", "de_refusals.tsv"]
    with pytest.raises(RScriptError, match="explicit outcome authorization"):
        run_r(
            script,
            {"counts": count_path, "clinical": clinical_path},
            {"expected_outputs": expected},
            tmp_path / "sc3_without_authorization",
        )

    provenance = tmp_path / "sc3_synthetic_manifest.json"
    write_sc3_r_synthetic_manifest(count_path, clinical_path, provenance)
    result = run_r(
        script,
        {"counts": count_path, "clinical": clinical_path},
        {
            "expected_outputs": expected,
            "design": "~ response",
            "fdr": 0.10,
            "authorization": {"data_classification": "synthetic", "provenance_manifest": str(provenance)},
            "validated_groups": groups,
        },
        tmp_path / "sc3_synthetic_result",
    )
    with result.outputs["de_results.tsv"].open(newline="") as stream:
        de_rows = list(csv.DictReader(stream, delimiter="\t"))
    with result.outputs["de_refusals.tsv"].open(newline="") as stream:
        refusals = list(csv.DictReader(stream, delimiter="\t"))

    assert {row["endpoint_family"] for row in de_rows} == {"RECIST", "expansion"}
    assert {row["comparison_id"] for row in de_rows} == {"sc3_group_1", "sc3_group_2"}
    assert all("pathology" not in row["comparison_id"] for row in de_rows)
    assert refusals == []
