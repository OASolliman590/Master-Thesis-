from __future__ import annotations

import csv
import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.a_bulk import BulkDataset, adapt_view, analyse
from tools.a_bulk import core
from tools.a_bulk.__main__ import main
from tools.a_scoring.core import panel_definitions
from tools.r_bridge import RScriptError, run_r


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Representation:
    platform: str
    unit: str
    transform: str
    feature_id: str = "symbol"


def _make_dataset(
    directory: Path,
    *,
    engine: str = "deseq2",
    unit: str = "counts",
    transform: str = "linear",
    feature_ids: list[str] | None = None,
    sample_count: int = 12,
    outlier_column: int | None = None,
    plant_de: bool = True,
    data_classification: str = "synthetic",
) -> BulkDataset:
    directory.mkdir(parents=True, exist_ok=True)
    sample_ids = [f"synthetic_{index:02d}" for index in range(sample_count)]
    responders = [index >= sample_count // 2 for index in range(sample_count)]
    rng = random.Random(20261103)
    features = feature_ids or [f"GENE_{index:03d}" for index in range(100)]
    rows = []
    for gene_index, gene in enumerate(features):
        values = []
        for sample_index, responder in enumerate(responders):
            baseline = 35 + gene_index * 2
            if plant_de and gene_index == 0 and responder:
                baseline *= 7
            value = round(baseline * rng.uniform(0.6, 1.4))
            if outlier_column == sample_index:
                value *= 80
            if transform in {"log2", "log2p1"}:
                logged = 4.0 + (gene_index % 9) * 0.15 + rng.uniform(-0.12, 0.12)
                if gene_index == 0 and responder:
                    logged += 3.5
                value = logged
            values.append(value)
        rows.append((gene, values))

    expression_path = directory / "expression.tsv"
    with expression_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(["gene", *sample_ids])
        for gene, values in rows:
            writer.writerow([gene, *values])

    clinical = []
    for index, sample_id in enumerate(sample_ids):
        category = "PR" if responders[index] else "PD"
        clinical.append({
            "patient_id": sample_id,
            "orr": category,
            "raw_orr": category,
            "clinical_benefit": "UNKNOWN",
            "raw_clinical_benefit": "",
            "drug_class_normalised": "ANTI_PD_L1_AXIS",
            "batch": f"batch_{index % 2}",
        })
    representation = Representation(
        platform="rnaseq",
        unit=unit,
        transform=transform,
    )
    metadata = SimpleNamespace(
        cohort_id="liu2019",
        representation=representation,
        de_engine=engine,
        endpoint_families=("orr",),
    )
    return BulkDataset(
        paper="A",
        dataset_id="synthetic_dataset",
        metadata=metadata,
        expression_path=expression_path,
        clinical_rows=clinical,
        data_classification=data_classification,
    )


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return [dict(row) for row in csv.DictReader(stream, delimiter="\t")]


def test_de_engine_selection_follows_representation_and_rejects_log_counts():
    counts = Representation("rnaseq", "counts", "linear")
    log_expression = Representation("rnaseq", "tpm", "log2")
    assert core.select_de_engine(counts, "deseq2") == "deseq2"
    assert core.select_de_engine(log_expression, "limma") == "limma"
    with pytest.raises(ValueError, match="untransformed count"):
        core.select_de_engine(Representation("rnaseq", "counts", "log2"), "deseq2")
    with pytest.raises(ValueError, match="does not match"):
        core.select_de_engine(log_expression, "deseq2")


def test_real_outcome_guard_rejects_before_endpoint_label_is_called(tmp_path, monkeypatch):
    dataset = _make_dataset(tmp_path / "data", data_classification="real")
    monkeypatch.setattr(
        core.a_scoring,
        "endpoint_label",
        lambda *args, **kwargs: pytest.fail("real response labels were inspected"),
    )
    with pytest.raises(core.OutcomeGuardError, match="--allow-outcomes"):
        analyse(dataset, "de", results=tmp_path / "results")
    assert not (tmp_path / "results").exists()


def test_cli_outcome_guard_runs_before_loading_a_real_cohort(monkeypatch, capsys):
    from tools.a_bulk import __main__ as bulk_cli

    monkeypatch.setattr(
        bulk_cli, "cohort_view",
        lambda *args, **kwargs: pytest.fail("real cohort files were loaded"),
    )
    with pytest.raises(SystemExit) as error:
        main(["de", "--cohort", "liu2019", "--paper", "A"])
    assert error.value.code == 2
    assert "requires --allow-outcomes" in capsys.readouterr().err


@pytest.mark.parametrize("entrypoint", ["adapt_view", "analyse", "output_dir"])
def test_protected_dataset_identifier_is_refused_before_expression_access(
    entrypoint, tmp_path, monkeypatch
):
    dataset = _make_dataset(tmp_path / "data", data_classification="real")
    dataset.metadata.cohort_id = "IMvigor210"
    monkeypatch.setattr(
        Path, "is_file", lambda _path: pytest.fail("expression file was checked")
    )

    with pytest.raises(ValueError, match="protected or excluded"):
        if entrypoint == "adapt_view":
            adapt_view(dataset)
        elif entrypoint == "analyse":
            analyse(dataset, "de", allow_outcomes=True, results=tmp_path / "results")
        else:
            core.output_dir(dataset, tmp_path / "results")


@pytest.mark.parametrize("role", ["excluded from A/B", "dropped at admission", "development candidate", "parked"])
def test_excluded_registry_role_is_refused_by_public_adapter(tmp_path, monkeypatch, role):
    dataset = _make_dataset(tmp_path / "data", data_classification="real")
    dataset.metadata.cohort_id = "excluded_fixture"
    monkeypatch.setattr(
        core.cohort_core,
        "registry",
        lambda: {"excluded_fixture": {"role": role}},
    )

    with pytest.raises(ValueError, match="protected or excluded"):
        adapt_view(dataset)


def test_cli_protected_identifier_is_refused_before_cohort_loader(monkeypatch, capsys):
    from tools.a_bulk import __main__ as bulk_cli

    monkeypatch.setattr(
        bulk_cli, "cohort_metadata",
        lambda *_args, **_kwargs: pytest.fail("cohort registry entry was loaded"),
    )
    with pytest.raises(SystemExit) as error:
        main(["qc", "--cohort", "IMvigor210", "--paper", "A"])

    assert error.value.code == 2
    assert "protected or excluded" in capsys.readouterr().err


def test_paper_b_cohort_view_like_interface_is_supported(tmp_path):
    dataset = _make_dataset(tmp_path / "data", engine="limma", unit="tpm", transform="log2")
    metadata = SimpleNamespace(
        cohort_id="future_b_expression",
        representation=dataset.representation,
        de_engine="limma",
        endpoint_families=(),
    )
    view = SimpleNamespace(
        metadata=metadata,
        expression_path=dataset.expression_path,
        clinical_rows=dataset.clinical_rows,
    )
    adapted = adapt_view(view, paper="B", data_classification="synthetic")
    assert adapted.paper == "B"
    assert adapted.dataset_id == "future_b_expression"
    assert adapted.expression_path == dataset.expression_path


@pytest.mark.requires_r
def test_deseq2_recovers_planted_differential_gene(tmp_path):
    dataset = _make_dataset(tmp_path / "data", engine="deseq2")
    summary = analyse(dataset, "de", results=tmp_path / "results")
    result = _read_tsv(tmp_path / "results" / "A" / dataset.dataset_id / "de" / "bridge" / "de.tsv")
    planted = next(row for row in result if row["gene"] == "GENE_000")
    assert summary["stages"]["de"]["engine"] == "DESeq2"
    assert float(planted["log2FC"]) > 1.0
    assert float(planted["q"]) < 0.05


@pytest.mark.requires_r
def test_limma_trend_recovers_planted_differential_gene(tmp_path):
    dataset = _make_dataset(
        tmp_path / "data", engine="limma", unit="tpm", transform="log2"
    )
    summary = analyse(dataset, "de", results=tmp_path / "results")
    result = _read_tsv(tmp_path / "results" / "A" / dataset.dataset_id / "de" / "bridge" / "de.tsv")
    planted = next(row for row in result if row["gene"] == "GENE_000")
    assert summary["stages"]["de"]["engine"] == "limma-trend"
    assert float(planted["log2FC"]) > 2.0
    assert float(planted["q"]) < 0.05


@pytest.mark.requires_r
def test_qc_flags_planted_library_outlier_and_pca_variance_is_bounded(tmp_path):
    dataset = _make_dataset(tmp_path / "data", outlier_column=11)
    results = tmp_path / "results"
    summary = analyse(dataset, "qc", results=results)
    dataset_root = results / "A" / dataset.dataset_id
    qc = _read_tsv(dataset_root / "qc" / "bridge" / "qc.tsv")
    assert summary["stages"]["qc"]["outlier_count"] >= 1
    assert qc[-1]["outlier_flag"] == "TRUE"
    assert qc[-1]["library_size_outlier"] == "TRUE"
    assert summary["stages"]["qc"]["library_size_outlier_count"] == 1
    assert "pc1_outlier_count" in summary["stages"]["qc"]
    assert "pc2_outlier_count" in summary["stages"]["qc"]

    pca_summary = analyse(dataset, "pca", results=results)
    variance = _read_tsv(dataset_root / "pca" / "bridge" / "variance_explained.tsv")
    pc12 = sum(float(row["variance_explained"]) for row in variance[:2])
    assert pc12 <= 1.0
    assert pca_summary["stages"]["pca"]["variance_explained_pc1_pc2"] <= 1.0
    assert not (dataset_root / "pca" / "bridge" / "pca_response.png").exists()

    manifest = (dataset_root / "qc" / "manifest.json").read_bytes()
    try:
        analyse(dataset, "qc", results=results)
    except FileExistsError:
        pass
    assert (dataset_root / "qc" / "manifest.json").read_bytes() == manifest
    assert (dataset_root / "qc" / "bridge" / "manifest.json").is_file()
    patient_free = json.loads((dataset_root / "summary.json").read_text())
    assert patient_free["stages"]["qc"]["sample_count"] == 12
    assert all(sample not in json.dumps(patient_free) for sample in _matrix_sample_ids(dataset.expression_path))
    rendered_summary = json.dumps(patient_free)
    assert "provenance" in patient_free
    assert patient_free["provenance"]["qc"]["r_script"] == "r/scripts/bulk_qc_pca.R"
    def nested_strings(value):
        if isinstance(value, dict):
            return [item for nested in value.values() for item in nested_strings(nested)]
        if isinstance(value, list):
            return [item for nested in value for item in nested_strings(nested)]
        return [value] if isinstance(value, str) else []

    assert not any(Path(value).is_absolute() for value in nested_strings(patient_free))
    assert "r_library" not in rendered_summary
    assert "script_path" not in rendered_summary


@pytest.mark.requires_r
def test_clean_synthetic_cohort_has_no_qc_outlier_flags(tmp_path):
    dataset = _make_dataset(
        tmp_path / "data", sample_count=24, feature_ids=[f"CLEAN_{i:04d}" for i in range(500)],
        plant_de=False,
    )
    sample_ids = _matrix_sample_ids(dataset.expression_path)
    rows = _read_tsv(dataset.expression_path)
    totals = {sample: sum(int(row[sample]) for row in rows) for sample in sample_ids}
    target_total = max(totals.values())
    for sample in sample_ids:
        scale = target_total / totals[sample]
        scaled = [round(int(row[sample]) * scale) for row in rows]
        scaled[0] += target_total - sum(scaled)
        for row, value in zip(rows, scaled):
            row[sample] = str(value)
    _write_tsv(dataset.expression_path, ["gene", *sample_ids], rows)

    summary = analyse(dataset, "qc", results=tmp_path / "results")
    dataset_root = tmp_path / "results" / "A" / dataset.dataset_id
    qc = _read_tsv(dataset_root / "qc" / "bridge" / "qc.tsv")

    assert summary["stages"]["qc"]["outlier_count"] == 0
    assert all(row["pc1_outlier"] == "FALSE" for row in qc)
    assert all(row["pc2_outlier"] == "FALSE" for row in qc)
    assert all(row["pc12_distance_outlier"] == "FALSE" for row in qc)
    assert all(row["library_size_outlier"] == "FALSE" for row in qc)


def test_non_count_column_totals_are_not_treated_as_library_depth(tmp_path):
    dataset = _make_dataset(
        tmp_path / "data", engine="limma", unit="tpm", transform="linear",
        sample_count=12, plant_de=False,
    )
    rows = _read_tsv(dataset.expression_path)
    sample_ids = _matrix_sample_ids(dataset.expression_path)
    for row in rows:
        row[sample_ids[-1]] = str(float(row[sample_ids[-1]]) * 50)
    _write_tsv(dataset.expression_path, ["gene", *sample_ids], rows)

    summary = analyse(dataset, "qc", results=tmp_path / "results")
    dataset_root = tmp_path / "results" / "A" / dataset.dataset_id
    qc = _read_tsv(dataset_root / "qc" / "bridge" / "qc.tsv")

    assert summary["stages"]["qc"]["library_size_outlier_count"] == 0
    assert qc[-1]["library_size_outlier"] == "NA"
    assert qc[-1]["column_total"] != "NA"


def test_stale_stage_summary_is_excluded_when_dataset_input_changes(tmp_path):
    dataset = _make_dataset(tmp_path / "data")
    root = tmp_path / "results" / "A" / dataset.dataset_id
    stage = root / "qc"
    bridge = stage / "bridge"
    bridge.mkdir(parents=True)
    summary_file = bridge / "qc_summary.json"
    summary_file.write_text('{"sample_count": 12}\n', encoding="utf-8")
    bridge_manifest = bridge / "manifest.json"
    bridge_manifest.write_text('{"script_path":"/private/r_script.R","r_library":"/private/lib"}\n', encoding="utf-8")
    manifest = {
        "schema_version": 2,
        "paper": dataset.paper,
        "dataset_id": dataset.dataset_id,
        "stage": "qc",
        "data_classification": dataset.data_classification,
        "representation": core._representation_config(dataset),
        "dataset_identity": core._dataset_identity(dataset),
        "dataset_input_sha256": core._dataset_input_sha256(dataset),
        "endpoint": None,
        "r_script": "bulk_qc_pca.R",
        "input_sha256": {"expression.tsv": core._sha256(dataset.expression_path)},
        "code_sha256": {"r/scripts/bulk_qc_pca.R": "code-hash"},
        "output_sha256": {"bridge/qc_summary.json": core._sha256(summary_file)},
        "run_r_manifest": {"path": "bridge/manifest.json", "sha256": core._sha256(bridge_manifest)},
    }
    (stage / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    with dataset.expression_path.open("a", encoding="utf-8") as stream:
        stream.write("\n")
    summary = core._write_patient_free_summary(dataset, root)

    assert "qc" not in summary["stages"]
    assert summary["excluded_stage_summaries"]["qc"] == "dataset_input_hash_mismatch"


def test_outcome_stage_summary_is_not_read_without_guard(tmp_path, monkeypatch):
    dataset = _make_dataset(tmp_path / "data", data_classification="real")
    root = tmp_path / "results" / "A" / dataset.dataset_id
    de = root / "de"
    (de / "bridge").mkdir(parents=True)
    (de / "bridge" / "de_summary.json").write_text("invalid summary", encoding="utf-8")
    (de / "manifest.json").write_text("invalid manifest", encoding="utf-8")
    original_read_json = core._read_json
    read_paths = []

    def track_read(path):
        read_paths.append(Path(path))
        return original_read_json(path)

    monkeypatch.setattr(core, "_read_json", track_read)
    summary = core._write_patient_free_summary(dataset, root)

    assert de / "manifest.json" not in read_paths
    assert de / "bridge" / "de_summary.json" not in read_paths
    assert "de" not in summary["stages"]
    assert summary["excluded_stage_summaries"]["de"] == "outcome_guard_required"


@pytest.mark.requires_r
def test_pca_response_coloring_is_available_only_when_flagged_on_synthetic_data(tmp_path):
    dataset = _make_dataset(tmp_path / "data", engine="limma", unit="tpm", transform="log2")
    results = tmp_path / "results"
    analyse(dataset, "pca", results=results, allow_outcomes=True)
    plot = results / "A" / dataset.dataset_id / "pca" / "bridge" / "pca_response.png"
    assert plot.is_file()
    manifest = json.loads((results / "A" / dataset.dataset_id / "pca" / "manifest.json").read_text())
    assert manifest["endpoint"] == "orr"
    bridge_manifest = json.loads((results / "A" / dataset.dataset_id / "pca" / "bridge" / "manifest.json").read_text())
    assert bridge_manifest["config"]["response_coloring_allowed"] is True


@pytest.mark.requires_r
def test_fgsea_runs_on_a_synthetic_ranking_and_local_gene_set(tmp_path):
    ranking = tmp_path / "ranking.tsv"
    with ranking.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(["gene", "statistic"])
        for index in range(40):
            writer.writerow([f"SYN_GENE_{index:02d}", 4.0 - index * 0.2])
    gmt = tmp_path / "tiny.gmt"
    gmt.write_text("SYN_SET\tdeterministic fixture\t" + "\t".join(
        f"SYN_GENE_{index:02d}" for index in range(8)
    ) + "\n", encoding="utf-8")
    output = tmp_path / "fgsea"
    result = run_r(
        ROOT / "r/scripts/fgsea_rank.R",
        {"ranking": ranking, "gene_sets": gmt},
        {"endpoint": "orr", "ranking_id_type": "symbol", "gene_set_id_type": "symbol",
         "min_gene_set_overlap": 1, "min_size": 1, "max_size": 100,
         "expected_outputs": ["fgsea.tsv", "membership_overlap.tsv", "gsea_summary.json"]},
        output,
    )
    summary = json.loads(result.outputs["gsea_summary.json"].read_text())
    assert summary["method"] == "fgseaMultilevel"
    assert summary["pathway_count"] == 1
    assert summary["membership_overlap_count"] == 8
    assert _read_tsv(result.outputs["fgsea.tsv"])[0]["pathway"] == "SYN_SET"
    assert _read_tsv(result.outputs["membership_overlap.tsv"])[0]["ranking_overlap_count"] == "8"


@pytest.mark.requires_r
def test_fgsea_refuses_mismatched_ranking_and_gmt_identifier_types(tmp_path):
    ranking = tmp_path / "ranking.tsv"
    ranking.write_text("gene\tstatistic\nGENE_A\t2\nGENE_B\t1\n", encoding="utf-8")
    gmt = tmp_path / "set.gmt"
    gmt.write_text("SET\tfixture\tGENE_A\tGENE_B\n", encoding="utf-8")

    with pytest.raises(RScriptError, match="identifier types must match"):
        run_r(
            ROOT / "r/scripts/fgsea_rank.R",
            {"ranking": ranking, "gene_sets": gmt},
            {"ranking_id_type": "symbol", "gene_set_id_type": "entrez",
             "min_gene_set_overlap": 1, "min_size": 1, "max_size": 10,
             "expected_outputs": ["fgsea.tsv", "membership_overlap.tsv", "gsea_summary.json"]},
            tmp_path / "fgsea-mismatch",
        )


@pytest.mark.requires_r
def test_fgsea_refuses_membership_below_configured_floor(tmp_path):
    ranking = tmp_path / "ranking.tsv"
    ranking.write_text("gene\tstatistic\nGENE_A\t2\nGENE_B\t1\n", encoding="utf-8")
    gmt = tmp_path / "set.gmt"
    gmt.write_text("SET\tfixture\tGENE_A\n", encoding="utf-8")

    with pytest.raises(RScriptError, match="membership overlap is below configured floor"):
        run_r(
            ROOT / "r/scripts/fgsea_rank.R",
            {"ranking": ranking, "gene_sets": gmt},
            {"ranking_id_type": "symbol", "gene_set_id_type": "symbol",
             "min_gene_set_overlap": 2, "min_size": 1, "max_size": 10,
             "expected_outputs": ["fgsea.tsv", "membership_overlap.tsv", "gsea_summary.json"]},
            tmp_path / "fgsea-low-overlap",
        )


def test_gsea_refreshes_the_de_ranking_before_use(tmp_path, monkeypatch):
    dataset = _make_dataset(tmp_path / "data")
    results = tmp_path / "results"
    dataset_root = results / "A" / dataset.dataset_id
    ranking = dataset_root / "de" / "bridge" / "de.tsv"
    ranking.parent.mkdir(parents=True)
    ranking.write_text("gene\tstatistic\nOLD\t1\n", encoding="utf-8")
    gene_sets = tmp_path / "sets.gmt"
    gene_sets.write_text("SYN_SET\tfixture\tGENE_000\n", encoding="utf-8")
    calls = []

    def refresh_de(_dataset, root, **_kwargs):
        current_ranking = root / "de" / "bridge" / "de.tsv"
        current_ranking.write_text("gene\tstatistic\nGENE_000\t2\n", encoding="utf-8")
        calls.append("de")
        return {"engine": "DESeq2"}

    def run_gsea(_dataset, root, _gene_sets, **_kwargs):
        assert (root / "de" / "bridge" / "de.tsv").read_text(encoding="utf-8") == (
            "gene\tstatistic\nGENE_000\t2\n"
        )
        calls.append("gsea")
        return {"pathway_count": 1}

    monkeypatch.setattr(core, "_run_de", refresh_de)
    monkeypatch.setattr(core, "_run_gsea", run_gsea)
    monkeypatch.setattr(
        core, "_write_patient_free_summary",
        lambda *_args, **_kwargs: {"stages": {}, "provenance": {}, "excluded_stage_summaries": {}},
    )

    summary = analyse(
        dataset, "gsea", results=results, gene_sets=gene_sets,
        gene_set_id_type="symbol", min_gene_set_overlap=1,
    )

    assert calls == ["de", "gsea"]
    assert summary["completed_stages"] == ["de", "gsea"]


@pytest.mark.requires_r
def test_count_panel_scores_are_invariant_to_sample_depth_doubling(tmp_path):
    panel_genes = {gene for genes in panel_definitions(core.PANEL_IDS).values() for gene in genes}
    features = sorted(panel_genes | {f"BACKGROUND_{index:03d}" for index in range(50)})
    original = _make_dataset(
        tmp_path / "original", engine="deseq2", unit="counts", feature_ids=features
    )
    doubled = _make_dataset(
        tmp_path / "doubled", engine="deseq2", unit="counts", feature_ids=features
    )
    rows = _read_tsv(doubled.expression_path)
    sample_id = _matrix_sample_ids(doubled.expression_path)[0]
    for row in rows:
        row[sample_id] = str(int(row[sample_id]) * 2)
    _write_tsv(doubled.expression_path, ["gene", *_matrix_sample_ids(doubled.expression_path)], rows)

    original_summary = analyse(original, "panels", results=tmp_path / "results-original")
    doubled_summary = analyse(doubled, "panels", results=tmp_path / "results-doubled")
    original_scores = _read_tsv(
        tmp_path / "results-original" / "A" / original.dataset_id / "scores" / "panel_scores.tsv"
    )
    doubled_scores = _read_tsv(
        tmp_path / "results-doubled" / "A" / doubled.dataset_id / "scores" / "panel_scores.tsv"
    )

    assert original_summary["stages"]["scores"]["analysis_transform"] == "log2_cpm"
    assert doubled_summary["stages"]["scores"]["analysis_transform"] == "log2_cpm"
    assert float(original_scores[0]["P_ANTIGEN_PRESENTATION"]) == pytest.approx(
        float(doubled_scores[0]["P_ANTIGEN_PRESENTATION"]), abs=1e-12
    )


@pytest.mark.requires_r
def test_cyt_uses_unoffset_linear_tpm_and_preserves_zero_pair_order(tmp_path):
    panel_genes = {gene for genes in panel_definitions(core.PANEL_IDS).values() for gene in genes}
    features = sorted(panel_genes | {"GZMA", "PRF1"})
    dataset = _make_dataset(
        tmp_path / "data", engine="limma", unit="tpm", transform="linear",
        feature_ids=features,
    )
    rows = _read_tsv(dataset.expression_path)
    sample_ids = _matrix_sample_ids(dataset.expression_path)
    values = {"GZMA": ("0", "1"), "PRF1": ("100", "1")}
    for row in rows:
        if row["gene"] in values:
            row[sample_ids[0]], row[sample_ids[1]] = values[row["gene"]]
    _write_tsv(dataset.expression_path, ["gene", *sample_ids], rows)

    analyse(dataset, "panels", results=tmp_path / "results")
    scores = _read_tsv(
        tmp_path / "results" / "A" / dataset.dataset_id / "scores" / "panel_scores.tsv"
    )

    assert scores[0]["CYT"] == "0"
    assert scores[1]["CYT"] == "1"
    assert scores[0]["CYT"] < scores[1]["CYT"]


@pytest.mark.requires_r
def test_cyt_is_unavailable_without_a_linear_tpm_route(tmp_path):
    panel_genes = {gene for genes in panel_definitions(core.PANEL_IDS).values() for gene in genes}
    features = sorted(panel_genes | {"GZMA", "PRF1"})
    dataset = _make_dataset(
        tmp_path / "data", engine="deseq2", unit="counts", transform="linear",
        feature_ids=features,
    )

    summary = analyse(dataset, "panels", results=tmp_path / "results")
    scores = _read_tsv(
        tmp_path / "results" / "A" / dataset.dataset_id / "scores" / "panel_scores.tsv"
    )

    assert summary["stages"]["scores"]["cyt_available"] is False
    assert summary["stages"]["scores"]["cyt_unavailable_reason"] == "verified linear TPM is unavailable"
    assert all(row["CYT"] == "NA" for row in scores)


@pytest.mark.requires_r
def test_panel_scores_and_spearman_matrix_are_written_per_dataset(tmp_path):
    definitions = panel_definitions(core.PANEL_IDS)
    features = sorted({gene for genes in definitions.values() for gene in genes})
    dataset = _make_dataset(
        tmp_path / "data", engine="limma", unit="tpm", transform="linear",
        feature_ids=features,
    )
    summary = analyse(dataset, "panels", results=tmp_path / "results")
    folder = tmp_path / "results" / "A" / dataset.dataset_id / "scores"
    correlations = _read_tsv(folder / "bridge" / "correlation.tsv")
    scores = _read_tsv(folder / "panel_scores.tsv")
    assert summary["stages"]["scores"]["score_count"] == 12
    assert len(scores) == 12
    assert len(correlations) == 12
    assert (folder / "bridge" / "correlation_heatmap.png").is_file()
    assert (folder / "manifest.json").is_file()


def _matrix_sample_ids(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return next(csv.reader(stream, delimiter="\t"))[1:]


def _write_tsv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
