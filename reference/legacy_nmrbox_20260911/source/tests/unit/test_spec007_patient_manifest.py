from __future__ import annotations

import importlib
from pathlib import Path

from src.pipeline.common.io import read_tsv, write_tsv


patient_manifest = importlib.import_module(
    "src.pipeline.modules.01_dataset_intake.patient_manifest"
)


def test_patient_uid_generation_and_timing_aggregation(tmp_path: Path) -> None:
    sample_manifest = tmp_path / "sample_manifest.tsv"
    geo_tables = tmp_path / "geo_tables"
    write_tsv(
        sample_manifest,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "patient_id",
            "cancer_type",
            "therapy_class",
            "therapy_agent",
            "specimen_type",
            "timing_category",
            "response_label",
            "include_flag",
            "response_label_source",
            "expression_sample_alias",
        ],
        rows=[
            {
                "cohort_id": "gse91061_melanoma_pd1",
                "sample_id": "GSM1",
                "patient_id": "Pt1",
                "cancer_type": "Melanoma",
                "therapy_class": "PD-1",
                "therapy_agent": "anti-PD1",
                "specimen_type": "bulk tumor sample",
                "timing_category": "pre-treatment",
                "response_label": "responder",
                "include_flag": "true",
                "response_label_source": "manual",
                "expression_sample_alias": "Pt1_Pre",
            },
            {
                "cohort_id": "gse91061_melanoma_pd1",
                "sample_id": "GSM2",
                "patient_id": "Pt1",
                "cancer_type": "Melanoma",
                "therapy_class": "PD-1",
                "therapy_agent": "anti-PD1",
                "specimen_type": "bulk tumor sample",
                "timing_category": "on-treatment",
                "response_label": "responder",
                "include_flag": "false",
                "response_label_source": "manual",
                "expression_sample_alias": "Pt1_On",
            },
        ],
    )

    samples = patient_manifest.build_sample_annotations(sample_manifest, geo_tables)
    patients = patient_manifest.build_patient_manifest(samples)

    assert len(patients) == 1
    row = patients[0]
    assert row["patient_uid"] == "gse91061_melanoma_pd1::Pt1"
    assert row["has_pre"] is True
    assert row["has_on"] is True
    assert row["n_timepoints"] == 2
    assert row["is_longitudinal"] is True
    assert row["pre_sample_ids"] == "GSM1"
    assert row["on_sample_ids"] == "GSM2"


def test_gse67501_metadata_parser_overrides_wrong_existing_response(tmp_path: Path) -> None:
    sample_manifest = tmp_path / "sample_manifest.tsv"
    geo_tables = tmp_path / "geo_tables"
    metadata_dir = geo_tables / "gse67501_rcc_pd1"
    metadata_dir.mkdir(parents=True)
    write_tsv(
        metadata_dir / "sample_metadata.tsv",
        fieldnames=[
            "sample_id",
            "patient_id",
            "response_label_inferred",
            "timing_category_inferred",
            "metadata_text",
        ],
        rows=[
            {
                "sample_id": "GSM1648122",
                "patient_id": "GSM1648122",
                "response_label_inferred": "non_responder",
                "timing_category_inferred": "unknown",
                "metadata_text": "anti-PD-1_Response_rep1 | RCC Primary tumor",
            }
        ],
    )
    write_tsv(
        sample_manifest,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "patient_id",
            "cancer_type",
            "therapy_class",
            "therapy_agent",
            "specimen_type",
            "timing_category",
            "response_label",
            "include_flag",
            "response_label_source",
            "expression_sample_alias",
        ],
        rows=[
            {
                "cohort_id": "gse67501_rcc_pd1",
                "sample_id": "GSM1648122",
                "patient_id": "GSM1648122",
                "cancer_type": "RCC",
                "therapy_class": "PD-1",
                "therapy_agent": "nivolumab",
                "specimen_type": "bulk tumor sample",
                "timing_category": "unknown",
                "response_label": "non_responder",
                "include_flag": "false",
                "response_label_source": "old_inference",
                "expression_sample_alias": "",
            }
        ],
    )

    samples = patient_manifest.build_sample_annotations(sample_manifest, geo_tables)

    assert samples[0]["response_label"] == "responder"
    assert samples[0]["response_source"] == "metadata_sample_name"
    assert samples[0]["timing_category"] == "pre-treatment"
    assert samples[0]["correction_source"] == "metadata_parser"


def test_build_and_write_patient_manifest_outputs_contract_files(tmp_path: Path) -> None:
    sample_manifest = tmp_path / "sample_manifest.tsv"
    geo_tables = tmp_path / "geo_tables"
    out_dir = tmp_path / "patient_manifest"
    write_tsv(
        sample_manifest,
        fieldnames=[
            "cohort_id",
            "sample_id",
            "patient_id",
            "cancer_type",
            "therapy_class",
            "therapy_agent",
            "therapy_agent_normalized",
            "specimen_type",
            "timing_category",
            "response_label",
            "include_flag",
            "response_label_source",
            "expression_sample_alias",
        ],
        rows=[
            {
                "cohort_id": "gse12345_test_pd1",
                "sample_id": "GSM1",
                "patient_id": "P1",
                "cancer_type": "NSCLC",
                "therapy_class": "PD-1",
                "therapy_agent": "nivolumab",
                "therapy_agent_normalized": "NIVOLUMAB",
                "specimen_type": "bulk tumor sample",
                "timing_category": "pre-treatment",
                "response_label": "non_responder",
                "include_flag": "true",
                "response_label_source": "manual",
                "expression_sample_alias": "",
            }
        ],
    )

    outputs = patient_manifest.build_and_write_patient_manifest(
        sample_manifest=sample_manifest,
        geo_tables_dir=geo_tables,
        out_dir=out_dir,
        reference_manifest=None,
    )

    assert outputs["patient_manifest"].exists()
    assert outputs["sample_annotations"].exists()
    assert outputs["patient_clinical_record"].exists()
    assert outputs["patient_manifest_validation"].exists()

    clinical = read_tsv(outputs["patient_clinical_record"])
    assert clinical[0]["patient_uid"] == "gse12345_test_pd1::P1"
    assert clinical[0]["icb_drug_class"] == "PD1"
    assert clinical[0]["clinical_stage"] == "unknown"

    validation = read_tsv(outputs["patient_manifest_validation"])
    assert any(row["metric"] == "row_count" for row in validation)
