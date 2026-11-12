from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

import pytest

pd = pytest.importorskip("pandas", reason="run with envs/sc-analysis Python")

from tools.a_meta.provenance import effect_rows_payload, write_synthetic_fixture_manifest
from tools.a_meta.synthesis import _read_effects, synthesize
from tools.sc.presentation import SC1_PANEL_IDS, panel_definitions_for_sc1
from tools.sc.sc3 import write_sc3_synthetic_manifest
from tools.sc import sc3
from tools.sc.sc3_cli import _partition_synthesis, main, run_synthetic


def _write_synthetic_inputs(directory: Path, *, cohort_override=None, protected=False):
    directory.mkdir(parents=True, exist_ok=True)
    cohorts = cohort_override or ("invented_study_A", "invented_study_B")
    rows = []
    for cohort_index, cohort in enumerate(cohorts):
        for metric in ("RECIST", "pathology", "T-cell expansion"):
            endpoint = "expansion" if metric == "T-cell expansion" else metric
            for compartment in ("T/NK", "myeloid"):
                for arm in ("R", "NR"):
                    for index in range(3):
                        profile_id = f"synthetic_profile_{cohort_index}_{endpoint}_{compartment}_{arm}_{index}"
                        rows.append({
                            "profile_id": profile_id,
                            "patient_id": f"synthetic_patient_{cohort_index}_{endpoint}_{compartment}_{arm}_{index}",
                            "sample_id": f"synthetic_specimen_{cohort_index}_{endpoint}_{compartment}_{arm}_{index}",
                            "cohort": cohort,
                            "source_family": f"invented_source_{cohort_index}",
                            "compartment": compartment,
                            "response_metric": metric,
                            "endpoint_family": endpoint,
                            "outcome_label": arm,
                            "response": arm if endpoint == "RECIST" else None,
                            "eligible": True,
                            "baseline": True,
                            "n_cells": 20,
                            "total_umis": 30_000,
                            "library_size": 1_000_000,
                            "cancer": "invented_cancer",
                            "treatment": "aPD1",
                            "fraction_cells_total": 0.1,
                        })
    clinical = pd.DataFrame.from_records(rows)
    if protected:
        clinical["overall_survival_months"] = [99] * len(clinical)
    clinical_path = directory / "synthetic_clinical.tsv"
    clinical.to_csv(clinical_path, sep="\t", index=False)
    parsed = pd.read_csv(clinical_path, sep="\t")

    definitions = panel_definitions_for_sc1()
    genes = sorted({gene for members in definitions.values() for gene in members})
    profile_ids = parsed["profile_id"].astype(str).tolist()
    count_values = []
    for gene_index, gene in enumerate(genes):
        multiplier = 1 + gene_index % 7
        values = []
        for row in parsed.itertuples(index=False):
            arm_index = int(str(row.profile_id).rsplit("_", 1)[-1]) + 1
            cohort_index = 2 if str(row.source_family).endswith("_1") else 1
            value = multiplier * arm_index * (10 if row.outcome_label == "R" else 1) * cohort_index
            values.append(value)
        count_values.append(values)
    expression = pd.DataFrame(count_values, index=genes, columns=profile_ids, dtype=int)
    expression.loc["OTHER_GENE"] = parsed["library_size"].astype(int).to_numpy() - expression.sum(axis=0)
    expression_path = directory / "synthetic_expression.tsv"
    expression.to_csv(expression_path, sep="\t", index_label="gene")

    manifest_path = directory / "synthetic_provenance.json"
    write_sc3_synthetic_manifest(
        parsed,
        manifest_path,
        input_sha256={
            "clinical": hashlib.sha256(clinical_path.read_bytes()).hexdigest(),
            "expression": hashlib.sha256(expression_path.read_bytes()).hexdigest(),
        },
    )
    return clinical_path, expression_path, manifest_path


def _args(clinical_path: Path, expression_path: Path, provenance_path: Path, output: Path):
    return [
        "--clinical", str(clinical_path),
        "--expression", str(expression_path),
        "--provenance", str(provenance_path),
        "--output-dir", str(output),
    ]


@pytest.mark.parametrize("path_kind", ("clinical", "expression", "provenance", "output", "resolved_clinical"))
def test_sc3_forbidden_paths_refuse_before_reads_hashes_or_output_creation(tmp_path, monkeypatch, path_kind):
    clinical_path, expression_path, provenance_path = _write_synthetic_inputs(tmp_path / "safe_inputs")
    output = tmp_path / "safe_results"
    supplied = {
        "clinical": clinical_path,
        "expression": expression_path,
        "provenance": provenance_path,
        "output": output,
    }
    if path_kind == "resolved_clinical":
        protected_parent = tmp_path / "invented" / "IM-Vigor_210"
        alias_parent = tmp_path / "invented" / "safe_alias"
        alias_parent.parent.mkdir()
        alias_parent.symlink_to(protected_parent, target_is_directory=True)
        supplied["clinical"] = alias_parent / "clinical.tsv"
    elif path_kind in {"clinical", "expression", "output"}:
        target = tmp_path / "invented" / "INGESTION_PACKET.JSON" / "target"
        supplied[path_kind] = target
    else:
        supplied["provenance"] = tmp_path / "invented" / "IMvigor-210" / "manifest.json"

    def forbidden_access(*_args, **_kwargs):
        pytest.fail("SC-3 read, hashed, or wrote before protected-path refusal")

    monkeypatch.setattr(sc3, "_input_sha256", forbidden_access)
    monkeypatch.setattr(sc3, "_read_sc3_identity", forbidden_access)
    monkeypatch.setattr(pd, "read_csv", forbidden_access)
    monkeypatch.setattr(Path, "open", forbidden_access)
    monkeypatch.setattr(Path, "read_text", forbidden_access)
    monkeypatch.setattr(Path, "mkdir", forbidden_access)

    with pytest.raises(ValueError, match="forbidden protected paths"):
        run_synthetic(
            supplied["clinical"],
            supplied["expression"],
            supplied["provenance"],
            supplied["output"],
        )
    assert not output.exists()
    assert not (tmp_path / "invented" / "INGESTION_PACKET.JSON").exists()


@pytest.mark.requires_r
def test_sc3_cli_runs_per_cohort_deseq2_and_partitioned_real_a_meta(tmp_path):
    if not shutil.which("Rscript"):
        pytest.skip("Rscript is unavailable")
    clinical_path, expression_path, provenance_path = _write_synthetic_inputs(tmp_path / "inputs")
    output = tmp_path / "results"

    assert main(_args(clinical_path, expression_path, provenance_path, output)) == 0

    effects = pd.read_csv(output / "sc3_effects.tsv", sep="\t")
    summaries = pd.read_csv(output / "a_meta_summaries.tsv", sep="\t")
    de_results = pd.read_csv(output / "de_results.tsv", sep="\t")
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    panel_rows = effects[effects["unit_family"].eq("panel")]
    panel_ids = set(panel_rows["unit"].str.rsplit("::", n=1).str[-1])
    m5m6_rows = effects[effects["unit_family"].eq("m5m6_gene")]
    m5m6_genes = set(m5m6_rows["unit"].str.rsplit("::", n=1).str[-1])

    assert panel_ids == set(SC1_PANEL_IDS)
    assert len(m5m6_genes) == 21
    assert set(m5m6_rows["m5m6_gene_flag"]) == {1}
    assert "fraction" in set(effects["unit_family"])
    assert set(effects["n_R"].dropna()) == {3}
    assert set(effects["n_NR"].dropna()) == {3}
    assert set(summaries["sc_endpoint_family"]) == {"RECIST", "pathology", "expansion"}
    assert set(summaries["compartment"]) == {"T/NK", "myeloid"}
    recist = summaries[summaries["sc_endpoint_family"].eq("RECIST")]
    assert set(recist["endpoint_family"]) == {"orr"}
    assert (recist["status"] == "pooled").any()
    for metric in ("pathology", "expansion"):
        rows = summaries[summaries["sc_endpoint_family"].eq(metric)]
        assert not rows.empty
        assert set(rows["endpoint_definition_id"]) == {"SOURCE_LABEL_UNSPECIFIED"}
        assert set(rows["status"]) == {"per_study_only"}
    assert len(manifest["synthesis_partitions"]) == 6
    assert all(
        item["pooled"] if item["metric_family"] == "RECIST" else not item["pooled"]
        for item in manifest["synthesis_partitions"]
    )
    assert len(set(de_results["comparison_id"])) == 12
    assert {"RECIST", "pathology", "expansion"}.issubset(set(de_results["endpoint_family"]))
    assert manifest["deseq2_api"] == "tools.r_bridge.run_r -> r/scripts/sc3_deseq2.R"
    assert manifest["private_r_retention"] is True
    assert manifest["patient_identifiers_written"] is False
    assert not {"profile_id", "patient_id", "sample_id", "response", "source_family"} & set(effects.columns)
    assert (output / ".sc3_private" / "de_r_retained").is_dir()
    assert list((output / ".sc3_private" / "a_meta_retained").iterdir())


def _controlled_effect_rows():
    rows = []
    for compartment, effect in (("T/NK", 6.8), ("myeloid", 0.089)):
        for study in ("invented_study_A", "invented_study_B"):
            rows.append({
                "unit_family": "panel",
                "unit": f"sc3::{compartment}::RECIST::CUSTOM_PANEL",
                "method_id": "CUSTOM_MEAN_CUSTOM_PANEL",
                "m5m6_gene_flag": 0,
                "study": study,
                "cancer": "invented_cancer",
                "cancer_components": "invented_cancer",
                "drug_class_stratum": "ALL",
                "endpoint_family": "orr",
                "endpoint_definition_id": "ORR",
                "patient_set_id": hashlib.sha256(f"{study}:{compartment}".encode()).hexdigest(),
                "n_R": 3,
                "n_NR": 3,
                "mean_R": effect,
                "mean_NR": 0.0,
                "sd_R": 1.0,
                "sd_NR": 1.0,
                "g": effect,
                "se": 1.0,
                "status": "ok",
                "reason": "",
                "n_found": None,
                "n_total": None,
                "sensitivity_label": "",
                "compartment": compartment,
                "sc_endpoint_family": "RECIST",
                "response_metric": "RECIST",
                "source_family": f"{study}_source",
            })
    return rows


def _independent_bh(values):
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    result = [None] * len(values)
    running = 1.0
    for rank in range(len(ordered), 0, -1):
        index, value = ordered[rank - 1]
        running = min(running, value * len(values) / rank)
        result[index] = min(1.0, running)
    return result


@pytest.mark.requires_r
def test_compartment_partitions_keep_bh_families_independent(tmp_path):
    if not shutil.which("Rscript"):
        pytest.skip("Rscript is unavailable")
    rows = _controlled_effect_rows()
    private = tmp_path / "private"
    private.mkdir()
    partitioned, _subgroups, _metadata = _partition_synthesis(
        rows, private, stratum="per_cancer",
    )
    by_compartment = {row["compartment"]: row for row in partitioned}
    p_values = [by_compartment["T/NK"]["p"], by_compartment["myeloid"]["p"]]
    assert p_values[0] == pytest.approx(0.06, abs=0.02)
    assert p_values[1] == pytest.approx(0.90, abs=0.03)
    assert by_compartment["T/NK"]["q"] == pytest.approx(p_values[0])
    assert by_compartment["myeloid"]["q"] == pytest.approx(p_values[1])

    normalized = _read_effects(rows)
    combined_manifest = tmp_path / "combined_effects_manifest.json"
    write_synthetic_fixture_manifest(
        combined_manifest,
        kind="effect_rows",
        payload=effect_rows_payload(normalized),
        cohort_ids=["invented_study_A", "invented_study_B"],
    )
    combined = synthesize(
        rows,
        "per_cancer",
        provenance_manifest=combined_manifest,
        output_dir=tmp_path / "combined",
        retention_dir=tmp_path / "combined_retained",
    )
    combined_tnk = next(row for row in combined.summaries if "T/NK" in row["unit"])
    independent_expected = _independent_bh(p_values)[0]
    assert independent_expected == pytest.approx(0.12, abs=0.04)
    assert combined_tnk["q"] == pytest.approx(independent_expected, abs=0.04)


def test_sc3_rejects_known_real_manifest_before_reading_clinical_values(tmp_path, monkeypatch, capsys):
    clinical_path, expression_path, provenance_path = _write_synthetic_inputs(
        tmp_path / "spoof", cohort_override=("PCa_Hawley",),
    )
    original_read_csv = pd.read_csv
    clinical_reads = []

    def guarded_read_csv(path, *args, **kwargs):
        if Path(path) == clinical_path:
            clinical_reads.append(path)
        return original_read_csv(path, *args, **kwargs)

    monkeypatch.setattr(pd, "read_csv", guarded_read_csv)
    with pytest.raises(SystemExit) as error:
        main(_args(clinical_path, expression_path, provenance_path, tmp_path / "spoof_results"))

    assert error.value.code == 2
    assert "known real cohort" in capsys.readouterr().err
    assert clinical_reads == []


def test_sc3_rejects_actual_known_cohort_from_identity_columns_before_outcomes(tmp_path, monkeypatch, capsys):
    clinical_path, expression_path, provenance_path = _write_synthetic_inputs(tmp_path / "identity_spoof")
    clinical = pd.read_csv(clinical_path, sep="\t")
    clinical["cohort"] = "PCa_Hawley"
    clinical.to_csv(clinical_path, sep="\t", index=False)
    original_read_csv = pd.read_csv
    clinical_reads = []

    def guarded_read_csv(path, *args, **kwargs):
        if Path(path) == clinical_path:
            clinical_reads.append(tuple(kwargs.get("usecols", ())))
            assert set(kwargs.get("usecols", ())) == {"cohort", "source_family", "profile_id", "patient_id", "sample_id"}
        return original_read_csv(path, *args, **kwargs)

    monkeypatch.setattr(pd, "read_csv", guarded_read_csv)
    with pytest.raises(SystemExit) as error:
        main(_args(clinical_path, expression_path, provenance_path, tmp_path / "identity_spoof_results"))

    assert error.value.code == 2
    assert "known-real" in capsys.readouterr().err
    assert len(clinical_reads) == 1


def test_sc3_rejects_output_alias_before_manifest_or_payload_reads(tmp_path, monkeypatch):
    clinical_path, expression_path, provenance_path = _write_synthetic_inputs(tmp_path / "alias")
    original_read_csv = pd.read_csv
    reads = []

    def guarded_read_csv(path, *args, **kwargs):
        reads.append(Path(path))
        return original_read_csv(path, *args, **kwargs)

    monkeypatch.setattr(pd, "read_csv", guarded_read_csv)
    with pytest.raises(SystemExit):
        main(_args(clinical_path, expression_path, provenance_path, clinical_path.parent))
    assert reads == []


def test_sc3_rejects_changed_expression_hash_before_reading_clinical_outcomes(tmp_path, monkeypatch, capsys):
    clinical_path, expression_path, provenance_path = _write_synthetic_inputs(tmp_path / "hash_mismatch")
    expression_path.write_text(expression_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    original_read_csv = pd.read_csv
    clinical_reads = []

    def guarded_read_csv(path, *args, **kwargs):
        if Path(path) == clinical_path:
            clinical_reads.append(tuple(kwargs.get("usecols", ())))
            assert set(kwargs.get("usecols", ())) == {"cohort", "source_family", "profile_id", "patient_id", "sample_id"}
        return original_read_csv(path, *args, **kwargs)

    monkeypatch.setattr(pd, "read_csv", guarded_read_csv)
    with pytest.raises(SystemExit) as error:
        main(_args(clinical_path, expression_path, provenance_path, tmp_path / "hash_results"))

    assert error.value.code == 2
    assert "does not bind" in capsys.readouterr().err
    assert len(clinical_reads) == 1


def test_sc3_rejects_unlisted_protected_clinical_column_before_reading_values(tmp_path, monkeypatch, capsys):
    clinical_path, expression_path, provenance_path = _write_synthetic_inputs(
        tmp_path / "protected", protected=True,
    )
    original_read_csv = pd.read_csv
    clinical_reads = []

    def guarded_read_csv(path, *args, **kwargs):
        if Path(path) == clinical_path:
            clinical_reads.append(path)
        return original_read_csv(path, *args, **kwargs)

    monkeypatch.setattr(pd, "read_csv", guarded_read_csv)
    with pytest.raises(SystemExit) as error:
        main(_args(clinical_path, expression_path, provenance_path, tmp_path / "protected_results"))

    assert error.value.code == 2
    assert "unknown=['overall_survival_months']" in capsys.readouterr().err
    assert clinical_reads == []
