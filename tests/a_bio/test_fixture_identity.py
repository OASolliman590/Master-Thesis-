from __future__ import annotations

import csv

from tools.a_bio.fixtures import write_fixture


def _sample_ids(manifest_path):
    simple = manifest_path.parent
    with (simple / "expression.tsv").open(newline="", encoding="utf-8") as stream:
        expression_ids = next(csv.reader(stream, delimiter="\t"))[1:]
    with (simple / "clinical.tsv").open(newline="", encoding="utf-8") as stream:
        clinical_ids = [row["patient_id"] for row in csv.DictReader(stream, delimiter="\t")]
    return expression_ids, clinical_ids


def test_synthetic_fixture_patient_ids_are_cohort_scoped(tmp_path):
    runtime = tmp_path / "runtime"
    first = write_fixture(runtime, cohort_id="invented_identity_alpha")
    second = write_fixture(runtime, cohort_id="invented_identity_beta")

    first_expression, first_clinical = _sample_ids(first)
    second_expression, second_clinical = _sample_ids(second)

    assert first_expression == first_clinical
    assert second_expression == second_clinical
    assert set(first_expression).isdisjoint(second_expression)
