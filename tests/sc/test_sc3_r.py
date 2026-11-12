from __future__ import annotations

import csv
import hashlib
import json
import random
import shutil
import subprocess
from pathlib import Path

import pytest

pytest.importorskip("pandas", reason="run with an analysis Python environment")

from tools.r_bridge import RScriptError, run_r
from tools.sc.sc3 import run_sc3_deseq2_synthetic, write_sc3_r_synthetic_manifest


def _write_minimal_invented_r_inputs(directory, *, cohort="invented_r_study"):
    directory.mkdir(parents=True, exist_ok=True)
    clinical_path = directory / "clinical.tsv"
    profiles = [
        {
            "cohort": cohort,
            "source_family": "invented_r_source",
            "profile_id": f"invented_profile_{index}",
            "patient_id": f"invented_patient_{index}",
            "sample_id": f"invented_specimen_{index}",
        }
        for index in range(6)
    ]
    with clinical_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(profiles[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(profiles)
    counts_path = directory / "counts.tsv"
    with counts_path.open("w", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t")
        writer.writerow(["gene", *[row["profile_id"] for row in profiles]])
        writer.writerow(["GENE_A", *([100] * len(profiles))])
    provenance_path = directory / "synthetic_manifest.json"
    provenance_path.write_text("{}\n", encoding="utf-8")
    return counts_path, clinical_path, provenance_path


def _direct_r_config(provenance_path):
    return {
        "expected_outputs": ["de_results.tsv", "de_refusals.tsv"],
        "authorization": {
            "data_classification": "synthetic",
            "provenance_manifest": str(provenance_path),
        },
        "validated_groups": [],
        "fdr": 0.10,
        "frozen_aliases": {},
    }


def _config_mutating_runner(change):
    def runner(command, *, cwd, env, capture_output, text, check=False):
        config_path = Path(command[-1])
        config = json.loads(config_path.read_text(encoding="utf-8"))
        change(config)
        config_path.write_text(json.dumps(config), encoding="utf-8")
        return subprocess.run(
            command, cwd=cwd, env=env, capture_output=capture_output, text=text, check=check,
        )
    return runner


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
                    "source_family": "invented_source",
                    "profile_id": f"synthetic_profile_{family}_{arm}_{index}",
                    "patient_id": patient,
                    "sample_id": f"synthetic_specimen_{family}_{arm}_{index}",
                    "compartment": "T/NK",
                    "endpoint_family": family,
                    "response_metric": "T-cell expansion" if family == "expansion" else "RECIST",
                    "outcome_label": arm,
                    "eligible": "TRUE",
                    "baseline": "TRUE",
                    "n_cells": 20,
                    "total_umis": 30_000,
                    "library_size": 30_000,
                    "treatment": "aPD1",
                    "sc3_group_id": group_id,
                }
                profiles.append(row)
                group_profiles.append(row["profile_id"])
        groups.append({
            "group_id": group_id,
            "cohort": "invented_study",
            "source_family": "invented_source",
            "compartment": "T/NK",
            "endpoint_family": family,
            "n_R": 3,
            "n_NR": 3,
            "profile_count": 6,
            "profile_ids_sha256": hashlib.sha256("\n".join(sorted(group_profiles)).encode("utf-8")).hexdigest(),
        })
    genes = [f"GENE_{index}" for index in range(20)] + ["RIGI", "COOK_OUTLIER"]
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
                if gene == "COOK_OUTLIER" and profile["endpoint_family"] == "RECIST" and profile["profile_id"].endswith("_R_2"):
                    value = 10**9
                values.append(value)
            writer.writerow([gene, *values])
    with clinical_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(profiles[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(profiles)

    provenance = tmp_path / "sc3_synthetic_manifest.json"
    write_sc3_r_synthetic_manifest(count_path, clinical_path, provenance)
    result = run_sc3_deseq2_synthetic(
        count_path,
        clinical_path,
        provenance,
        tmp_path / "sc3_synthetic_result",
        groups,
        retention_dir=tmp_path / "retained_synthetic",
    )
    with result.outputs["de_results.tsv"].open(newline="") as stream:
        de_rows = list(csv.DictReader(stream, delimiter="\t"))
    with result.outputs["de_refusals.tsv"].open(newline="") as stream:
        refusals = list(csv.DictReader(stream, delimiter="\t"))

    assert {row["endpoint_family"] for row in de_rows} == {"RECIST", "expansion"}
    assert {row["comparison_id"] for row in de_rows} == {"sc3_group_1", "sc3_group_2"}
    assert len(de_rows) == 44
    assert all("pathology" not in row["comparison_id"] for row in de_rows)
    assert refusals == []
    assert "DDX58" in {row["gene"] for row in de_rows}
    assert "RIGI" not in {row["gene"] for row in de_rows}
    expected_signal = next(
        row for row in de_rows
        if row["endpoint_family"] == "RECIST" and row["gene"] == "GENE_0"
    )
    assert float(expected_signal["baseMean"]) > 0
    assert float(expected_signal["log2FoldChange"]) > 0
    assert 0 <= float(expected_signal["pvalue"]) <= 1
    if expected_signal["padj"] != "NA":
        assert 0 <= float(expected_signal["padj"]) <= 1

    def independent_bh(pvalues):
        ordered = sorted(enumerate(pvalues), key=lambda item: item[1])
        adjusted = [None] * len(pvalues)
        running = 1.0
        for rank in range(len(ordered), 0, -1):
            index, value = ordered[rank - 1]
            running = min(running, value * len(pvalues) / rank)
            adjusted[index] = min(1.0, running)
        return adjusted

    for group_id in {row["comparison_id"] for row in de_rows}:
        tested = [row for row in de_rows if row["comparison_id"] == group_id and row["pvalue"] != "NA"]
        expected_adjustments = independent_bh([float(row["pvalue"]) for row in tested])
        for row, expected_adjustment in zip(tested, expected_adjustments, strict=True):
            assert float(row["padj"]) == pytest.approx(expected_adjustment, rel=1e-7, abs=1e-10)
    cook_rows = [row for row in de_rows if row["pvalue"] == "NA" and float(row["baseMean"]) > 0]
    assert cook_rows
    assert all(row["status"] == "pvalue_unavailable" for row in cook_rows)
    assert all("default_DESeq2_Cook_filter_or_model" in row["reason"] for row in cook_rows)
    assert all(row["padj_status"] == "not_adjusted_pvalue_unavailable" for row in cook_rows)

    def assert_invalid_group_rejected(mutator, message, label):
        invalid_profiles = [dict(row) for row in profiles]
        mutator(invalid_profiles)
        invalid_clinical_path = tmp_path / f"{label}_clinical.tsv"
        with invalid_clinical_path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(invalid_profiles[0]), delimiter="\t")
            writer.writeheader()
            writer.writerows(invalid_profiles)
        invalid_provenance = tmp_path / f"{label}_manifest.json"
        write_sc3_r_synthetic_manifest(count_path, invalid_clinical_path, invalid_provenance)
        with pytest.raises(RScriptError, match=message):
            run_sc3_deseq2_synthetic(
                count_path,
                invalid_clinical_path,
                invalid_provenance,
                tmp_path / f"{label}_result",
                groups,
                retention_dir=tmp_path / f"{label}_retained",
            )

    assert_invalid_group_rejected(
        lambda rows: rows[1].update(patient_id=rows[0]["patient_id"]),
        "one profile per patient",
        "duplicate_patient",
    )
    assert_invalid_group_rejected(
        lambda rows: rows[1].update(sample_id=rows[0]["sample_id"]),
        "unique specimens",
        "duplicate_specimen",
    )
    assert_invalid_group_rejected(
        lambda rows: rows[0].update(n_cells=14),
        "15-cell/5000-UMI floors",
        "below_cell_floor",
    )
    assert_invalid_group_rejected(
        lambda rows: rows[0].update(treatment="aPD1+chemotherapy"),
        "15-cell/5000-UMI floors",
        "non_ici_combination",
    )


@pytest.mark.requires_r
def test_direct_r_rejects_alias_collision_and_output_input_aliases(tmp_path):
    if not shutil.which("Rscript"):
        pytest.skip("Rscript is unavailable")

    clinical = []
    for arm in ("R", "NR"):
        for index in range(3):
            clinical.append({
                "cohort": "invented_alias_study",
                "source_family": "invented_alias_source",
                "profile_id": f"synthetic_alias_{arm}_{index}",
                "patient_id": f"synthetic_alias_patient_{arm}_{index}",
                "sample_id": f"synthetic_alias_specimen_{arm}_{index}",
                "compartment": "T/NK",
                "endpoint_family": "RECIST",
                "response_metric": "RECIST",
                "outcome_label": arm,
                "response": arm,
                "eligible": "TRUE",
                "baseline": "TRUE",
                "n_cells": 20,
                "total_umis": 30_000,
                "library_size": 30_000,
                "treatment": "aPD1",
                "sc3_group_id": "sc3_alias_group",
            })
    clinical_path = tmp_path / "alias_clinical.tsv"
    with clinical_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(clinical[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(clinical)
    counts_path = tmp_path / "alias_counts.tsv"
    with counts_path.open("w", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t")
        writer.writerow(["gene", *[row["profile_id"] for row in clinical]])
        for gene in ("RIGI", "DDX58", "GENE_A"):
            writer.writerow([gene, *([100, 200, 300, 20, 40, 60])])
    provenance = tmp_path / "alias_manifest.json"
    write_sc3_r_synthetic_manifest(counts_path, clinical_path, provenance)
    groups = [{
        "group_id": "sc3_alias_group",
        "cohort": "invented_alias_study",
        "source_family": "invented_alias_source",
        "compartment": "T/NK",
        "endpoint_family": "RECIST",
        "n_R": 3,
        "n_NR": 3,
        "profile_count": 6,
        "profile_ids_sha256": hashlib.sha256(
            "\n".join(sorted(row["profile_id"] for row in clinical)).encode("utf-8")
        ).hexdigest(),
    }]

    with pytest.raises(RScriptError, match="collide after frozen alias"):
        run_sc3_deseq2_synthetic(
            counts_path, clinical_path, provenance, tmp_path / "alias_result", groups,
            retention_dir=tmp_path / "alias_retained",
        )
    with pytest.raises(ValueError, match="new directory"):
        run_sc3_deseq2_synthetic(
            counts_path, clinical_path, provenance, clinical_path, groups,
            retention_dir=tmp_path / "alias_retained_2",
        )


@pytest.mark.requires_r
def test_direct_r_refuses_protected_paths_before_payload_reads_or_output_creation(tmp_path):
    if not shutil.which("Rscript"):
        pytest.skip("Rscript is unavailable")

    counts_path, clinical_path, provenance_path = _write_minimal_invented_r_inputs(tmp_path / "safe_inputs")
    script = Path(__file__).resolve().parents[2] / "r/scripts/sc3_deseq2.R"
    resolved_parent = tmp_path / "invented" / "IMvigor_210"
    alias_parent = tmp_path / "invented" / "safe_alias"
    alias_parent.parent.mkdir()
    alias_parent.symlink_to(resolved_parent, target_is_directory=True)
    cases = {
        "input": lambda config: config["inputs"].update({
            "counts": str(tmp_path / "invented" / "IMvigor_210" / "counts.tsv"),
        }),
        "provenance": lambda config: config["config"]["authorization"].update({
            "provenance_manifest": str(tmp_path / "invented" / "ingestion_packet.json" / "manifest.json"),
        }),
        "output": lambda config: config.update({
            "output_dir": str(tmp_path / "invented" / "imvigor-210" / "de_results"),
        }),
        "resolved input": lambda config: config["inputs"].update({
            "counts": str(alias_parent / "counts.tsv"),
        }),
        "resolved provenance": lambda config: config["config"]["authorization"].update({
            "provenance_manifest": str(alias_parent / "manifest.json"),
        }),
        "resolved output": lambda config: config.update({
            "output_dir": str(alias_parent / "de_results"),
        }),
    }
    for path_kind, mutate in cases.items():
        with pytest.raises(RScriptError, match="forbidden protected paths"):
            run_r(
                script,
                {"counts": counts_path, "clinical": clinical_path},
                _direct_r_config(provenance_path),
                tmp_path / f"safe_output_{path_kind}",
                runner=_config_mutating_runner(mutate),
                retention_dir=tmp_path / f"safe_retention_{path_kind}",
            )
        assert not resolved_parent.exists()
        assert not (resolved_parent / "de_results").exists()


@pytest.mark.requires_r
def test_direct_r_checks_bridge_config_path_before_reading_it(tmp_path):
    if not shutil.which("Rscript"):
        pytest.skip("Rscript is unavailable")

    counts_path, clinical_path, provenance_path = _write_minimal_invented_r_inputs(tmp_path / "safe_inputs")
    script = Path(__file__).resolve().parents[2] / "r/scripts/sc3_deseq2.R"
    protected_config = tmp_path / "invented" / "ingestion_packet.json" / "bridge-config.json"

    def runner(command, *, cwd, env, capture_output, text, check=False):
        command = [*command[:-1], str(protected_config)]
        return subprocess.run(
            command, cwd=cwd, env=env, capture_output=capture_output, text=text, check=check,
        )

    with pytest.raises(RScriptError, match="forbidden protected paths"):
        run_r(
            script,
            {"counts": counts_path, "clinical": clinical_path},
            _direct_r_config(provenance_path),
            tmp_path / "safe_output_config_path",
            runner=runner,
            retention_dir=tmp_path / "safe_retention_config_path",
        )
    assert not protected_config.parent.exists()


@pytest.mark.requires_r
def test_direct_r_punctuation_insensitive_identity_guard_precedes_input_hashes(tmp_path):
    if not shutil.which("Rscript"):
        pytest.skip("Rscript is unavailable")

    counts_path, clinical_path, provenance_path = _write_minimal_invented_r_inputs(
        tmp_path / "invented_identity_inputs", cohort="IM-Vigor_210",
    )
    from tools.a_meta.provenance import write_synthetic_fixture_manifest

    write_synthetic_fixture_manifest(
        provenance_path,
        kind="sc3_r_input",
        payload_sha256="0" * 64,
        cohort_ids=["invented_declared_fixture"],
    )
    script = Path(__file__).resolve().parents[2] / "r/scripts/sc3_deseq2.R"
    with pytest.raises(RScriptError, match="known-real or protected clinical cohort identities"):
        run_r(
            script,
            {"counts": counts_path, "clinical": clinical_path},
            _direct_r_config(provenance_path),
            tmp_path / "safe_output_identity",
            retention_dir=tmp_path / "safe_retention_identity",
        )
