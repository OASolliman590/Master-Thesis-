from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from src.pipeline.cli import cmd_intake_curation_report
from src.pipeline.common.io import read_tsv, write_tsv


def test_stage01_curation_report_emits_contract_and_repro_bundle(tmp_path: Path) -> None:
    assay_detection = tmp_path / "assay_detection.tsv"
    response_definition = tmp_path / "response_definition.tsv"
    timing_provenance = tmp_path / "timing_provenance.tsv"
    sample_manifest = tmp_path / "sample_manifest_with_contract.tsv"

    write_tsv(
        assay_detection,
        fieldnames=[
            "cohort_id",
            "assay_type",
            "detection_confidence",
            "cohort_flags",
        ],
        rows=[
            {
                "cohort_id": "cohort_ready",
                "assay_type": "rlog_vst",
                "detection_confidence": "0.93",
                "cohort_flags": "",
            },
            {
                "cohort_id": "cohort_methyl",
                "assay_type": "methylation_beta",
                "detection_confidence": "0.99",
                "cohort_flags": "",
            },
        ],
    )
    write_tsv(
        response_definition,
        fieldnames=[
            "cohort_id",
            "label_provenance",
            "needs_manual_confirmation",
            "n_unknown",
            "cohort_flags",
        ],
        rows=[
            {
                "cohort_id": "cohort_ready",
                "label_provenance": "curated",
                "needs_manual_confirmation": "false",
                "n_unknown": "0",
                "cohort_flags": "",
            },
            {
                "cohort_id": "cohort_methyl",
                "label_provenance": "sampleid_inferred",
                "needs_manual_confirmation": "true",
                "n_unknown": "1",
                "cohort_flags": "",
            },
        ],
    )
    write_tsv(
        timing_provenance,
        fieldnames=["cohort_id", "sample_id", "timing_category", "timing_provenance"],
        rows=[
            {
                "cohort_id": "cohort_ready",
                "sample_id": "S1",
                "timing_category": "pre-treatment",
                "timing_provenance": "curated",
            },
            {
                "cohort_id": "cohort_methyl",
                "sample_id": "S2",
                "timing_category": "pre-treatment",
                "timing_provenance": "default_pre",
            },
        ],
    )
    write_tsv(
        sample_manifest,
        fieldnames=["cohort_id", "sample_id"],
        rows=[
            {"cohort_id": "cohort_ready", "sample_id": "S1"},
            {"cohort_id": "cohort_methyl", "sample_id": "S2"},
        ],
    )

    out_dir = tmp_path / "out"
    args = Namespace(
        assay_detection=str(assay_detection),
        response_definition=str(response_definition),
        timing_provenance=str(timing_provenance),
        sample_manifest=str(sample_manifest),
        out=str(out_dir),
        run_manifest=str(tmp_path / "logs/run_manifest.yaml"),
    )
    assert cmd_intake_curation_report(args) == 0

    report_rows = {row["cohort_id"]: row for row in read_tsv(out_dir / "intake_curation_report.tsv")}
    assert report_rows["cohort_ready"]["status"] == "ready"
    assert report_rows["cohort_methyl"]["status"] == "excluded"
    assert report_rows["cohort_methyl"]["notes"] == "excluded_assay_type_methylation_beta"
    assert report_rows["cohort_methyl"]["n_timing_default_pre"] == "1"

    assert (out_dir / "intake_curation_report.md").exists()
    assert (out_dir / "reproducibility" / "commands.sh").exists()
    assert (out_dir / "reproducibility" / "environment.yml").exists()
    assert (out_dir / "reproducibility" / "checksums.sha256").exists()
