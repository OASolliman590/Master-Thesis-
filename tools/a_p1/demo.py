"""Invented-data command used to demonstrate A-P1 software behavior."""

from __future__ import annotations

from pathlib import Path

from .analysis import analyze_records
from .provenance import create_synthetic_manifest


MEASUREMENT_CONTRACT = {
    "representation_id": "invented-qualified-tpm-v1",
    "unit": "TPM",
    "transform": "unlogged_abundance",
    "gene_mapping": "unique",
    "qualification_status": "qualified",
}


def run_demo(output_dir: Path | str) -> dict:
    """Run two invented cohorts through scoring and explicitly weighted synthesis."""
    records = []
    for study, cancer, values in (
        (
            "invented-study-a",
            "invented-cancer-a",
            (("CR", 9.0), ("PR", 4.0), ("SD", 4.0), ("SD", 1.0), ("PD", 1.0), ("PD", 4.0)),
        ),
        (
            "invented-study-b",
            "invented-cancer-b",
            (("CR", 1.0), ("PR", 2.0), ("SD", 4.0), ("SD", 4.0), ("PD", 9.0), ("PD", 1.0)),
        ),
    ):
        for index, (category, abundance) in enumerate(values, start=1):
            records.append({
                "study_id": study,
                "cancer": cancer,
                "patient_key": f"invented-{study[-1]}-{index:02d}",
                "specimen_key": f"invented-{study[-1]}-{index:02d}-specimen",
                "index_episode_id": "invented-index-episode",
                "is_index_specimen": True,
                "expression_episode_id": "invented-index-episode",
                "outcome_episode_id": "invented-index-episode",
                "response_category": category,
                "source_criteria": "invented-best-response-criteria-v1",
                "evaluation_window": "invented-assessment-window-v1",
                "TPM_GZMA": abundance,
                "TPM_PRF1": abundance,
            })
    synthesis_contract = {
        "collection_id": "invented-a-p1-collection-v1",
        "decision_status": "INVENTED_FIXTURE",
        "studies": [
            {
                "study_id": "invented-study-a",
                "cancer": "invented-cancer-a",
                "cancer_weight": 0.55,
                "study_weight": 1.0,
            },
            {
                "study_id": "invented-study-b",
                "cancer": "invented-cancer-b",
                "cancer_weight": 0.45,
                "study_weight": 1.0,
            },
        ],
    }
    return analyze_records(
        records,
        create_synthetic_manifest(records, MEASUREMENT_CONTRACT),
        output_dir,
        synthesis_contract=synthesis_contract,
    )
