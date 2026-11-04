from __future__ import annotations

from pathlib import Path

from tools.a_meta.provenance import (
    effect_input_payload,
    effect_rows_payload,
    write_synthetic_fixture_manifest,
)


def synthetic_effect_input_manifest(view, features, path: Path) -> Path:
    cohort_id = str(view.metadata.cohort_id)
    write_synthetic_fixture_manifest(
        path,
        kind="study_effects_input",
        payload=effect_input_payload(view, features),
        cohort_ids=(cohort_id,),
    )
    return path


def synthetic_effect_rows_manifest(rows, path: Path) -> Path:
    studies = sorted({str(row["study"]) for row in rows})
    write_synthetic_fixture_manifest(
        path,
        kind="effect_rows",
        payload=effect_rows_payload(rows),
        cohort_ids=studies,
    )
    return path
