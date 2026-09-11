from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from src.pipeline.cli import cmd_router_run
from src.pipeline.common.io import read_tsv, write_tsv


def test_router_dry_run_emits_readiness_and_stub_exclusion(tmp_path: Path) -> None:
    sample_manifest = tmp_path / "sample_manifest.tsv"
    out_dir = tmp_path / "router_out"
    run_manifest = tmp_path / "logs/run_manifest.yaml"

    write_tsv(
        sample_manifest,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "comparison_tracks_final",
            "include_flag",
            "sync_status",
            "timing_category",
            "response_label",
            "pair_id",
        ],
        rows=[
            {
                "cohort_id": "cohort_real",
                "sample_id": "s1",
                "comparison_tracks_final": "PRE_RESPONSE",
                "include_flag": "true",
                "sync_status": "",
                "timing_category": "pre-treatment",
                "response_label": "responder",
                "pair_id": "",
            },
            {
                "cohort_id": "cohort_stub",
                "sample_id": "s_stub",
                "comparison_tracks_final": "PRE_RESPONSE",
                "include_flag": "true",
                "sync_status": "added_cohort_stub_no_sample_rows",
                "timing_category": "pre-treatment",
                "response_label": "responder",
                "pair_id": "",
            },
        ],
    )

    args = Namespace(
        sample_manifest=str(sample_manifest),
        track="A",
        out=str(out_dir),
        include_excluded=False,
        allow_stub_rows=False,
        dry_run=True,
        expression_manifest=str(tmp_path / "geo_tables_summary.tsv"),
        downloads_root=str(tmp_path / "downloads"),
        count_method="deseq2",
        gene_id_mapping=str(tmp_path / "gene_map.tsv"),
        min_hgnc_mapping_rate=0.60,
        max_unmapped_ensembl_fraction=0.20,
        max_duplicate_collapse_fraction=0.25,
        allow_weak_gene_mapping=False,
        run_manifest=str(run_manifest),
    )
    assert cmd_router_run(args) == 0

    summary_rows = read_tsv(out_dir / "route_execution_summary.tsv")
    assert summary_rows
    row = summary_rows[0]
    assert row["n_routed_cohorts"] == "2"
    assert row["n_stub_excluded_cohorts"] == "1"
    assert row["n_routed_not_executed_cohorts"] == "1"
    assert row["n_analyzed_cohorts"] == "0"

    readiness_rows = read_tsv(out_dir / "cohort_readiness_status.tsv")
    by_cohort = {r["cohort_id"]: r for r in readiness_rows}
    assert by_cohort["cohort_stub"]["readiness_status"] == "stub_excluded"
    assert by_cohort["cohort_real"]["readiness_status"] == "routed_not_executed"
    assert by_cohort["cohort_real"]["execution_status"] == "dry_run"


def test_router_forwards_allow_welch_fallback_to_de_stage(tmp_path: Path, monkeypatch) -> None:
    sample_manifest = tmp_path / "sample_manifest.tsv"
    expression_manifest = tmp_path / "geo_tables_summary.tsv"
    downloads_root = tmp_path / "downloads"
    out_dir = tmp_path / "router_out"
    run_manifest = tmp_path / "logs/run_manifest.yaml"

    write_tsv(
        sample_manifest,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "comparison_tracks_final",
            "include_flag",
            "sync_status",
            "timing_category",
            "response_label",
            "pair_id",
        ],
        rows=[
            {
                "cohort_id": "cohort_a",
                "sample_id": "R1",
                "comparison_tracks_final": "PRE_RESPONSE",
                "include_flag": "true",
                "sync_status": "",
                "timing_category": "pre-treatment",
                "response_label": "responder",
                "pair_id": "",
            },
            {
                "cohort_id": "cohort_a",
                "sample_id": "N1",
                "comparison_tracks_final": "PRE_RESPONSE",
                "include_flag": "true",
                "sync_status": "",
                "timing_category": "pre-treatment",
                "response_label": "non_responder",
                "pair_id": "",
            },
        ],
    )
    write_tsv(
        expression_manifest,
        fieldnames=["cohort_id", "primary_expression_file", "downloads_folder"],
        rows=[{"cohort_id": "cohort_a", "primary_expression_file": "expr.tsv", "downloads_folder": "cohort_a"}],
    )
    expr_file = downloads_root / "cohort_a" / "expr.tsv"
    expr_file.parent.mkdir(parents=True, exist_ok=True)
    expr_file.write_text(
        "gene_id\tR1\tN1\nGENE1\t10\t4\nGENE2\t6\t3\n",
        encoding="utf-8",
    )

    monkeypatch.setattr("src.pipeline.cli.cmd_intake_gene_audit", lambda *_: 0)
    monkeypatch.setattr("src.pipeline.cli.cmd_ingest_run", lambda *_: 0)
    monkeypatch.setattr("src.pipeline.cli.cmd_qc_run", lambda *_: 0)
    monkeypatch.setattr("src.pipeline.cli.cmd_meta_run", lambda *_: 0)
    monkeypatch.setattr("src.pipeline.cli.cmd_visualize_run", lambda *_: 0)

    captured: dict[str, bool] = {}

    def _fake_cmd_de_run(de_args):  # noqa: ANN001
        captured["allow_welch_fallback"] = bool(getattr(de_args, "allow_welch_fallback", False))
        de_path = Path(de_args.out) / de_args.contrast / "cohort_a.tsv"
        write_tsv(
            de_path,
            fieldnames=["comparison_id", "gene_id", "model_class", "log2fc", "se_or_stat", "p_value", "fdr"],
            rows=[
                {
                    "comparison_id": "cmp_test",
                    "gene_id": "GENE1",
                    "model_class": "welch_fallback_log2",
                    "log2fc": "1.0",
                    "se_or_stat": "0.5",
                    "p_value": "0.05",
                    "fdr": "0.1",
                }
            ],
        )
        return 0

    monkeypatch.setattr("src.pipeline.cli.cmd_de_run", _fake_cmd_de_run)

    args = Namespace(
        sample_manifest=str(sample_manifest),
        track="A",
        out=str(out_dir),
        include_excluded=False,
        allow_stub_rows=False,
        dry_run=False,
        expression_manifest=str(expression_manifest),
        downloads_root=str(downloads_root),
        count_method="deseq2",
        gene_id_mapping=str(tmp_path / "gene_map.tsv"),
        min_hgnc_mapping_rate=0.60,
        max_unmapped_ensembl_fraction=0.20,
        max_duplicate_collapse_fraction=0.25,
        allow_weak_gene_mapping=False,
        allow_welch_fallback=True,
        run_manifest=str(run_manifest),
    )
    assert cmd_router_run(args) == 0
    assert captured["allow_welch_fallback"] is True
