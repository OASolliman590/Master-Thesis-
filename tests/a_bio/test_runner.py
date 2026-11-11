from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from tools.a_bio.runner import (
    AdjustedAnalysisUnavailable,
    OutcomeGuardError,
    load_cohort_materialization,
    run,
)
from tests.a_bio.fakes import FakeBridge
from tests.a_bio.helpers import _read_tsv, write_synthetic_materialization


def test_adjusted_request_refuses_before_any_runtime_access(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    original_open = Path.open

    def guarded_open(path, *args, **kwargs):
        if path == runtime or runtime in path.parents:
            pytest.fail("runtime input was accessed before adjusted-model refusal")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)

    with pytest.raises(AdjustedAnalysisUnavailable, match="clinical adjustment sets"):
        run("outcomes", cohorts=("invented_study",), runtime=runtime, adjusted=True)

    assert not runtime.exists()


def test_fixture_cli_creates_only_invented_hash_matched_inputs(tmp_path, capsys):
    from tools.a_bio.__main__ import main

    runtime = tmp_path / "fixture-runtime"
    result = main([
        "fixture",
        "--runtime", str(runtime),
        "--cohort", "invented_cli_demo",
        "--sample-count", "8",
    ])
    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    manifest_path = runtime / "invented_cli_demo" / "simple" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["cohort_id"] == "invented_cli_demo"
    assert manifest["producer"] == "tools.a_bio.synthetic_fixture"
    assert manifest["data_classification"] == "synthetic"
    assert manifest["invented_source"] == "All rows and expression values were invented for software tests."
    for name, expected_hash in manifest["outputs_sha256"].items():
        import hashlib

        assert hashlib.sha256((manifest_path.parent / name).read_bytes()).hexdigest() == expected_hash


def test_real_outcome_route_refuses_before_runtime_access_without_release(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    original_open = Path.open

    def guarded_open(path, *args, **kwargs):
        if path == runtime or runtime in path.parents:
            pytest.fail("real cohort input was accessed before outcome release")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)

    with pytest.raises(OutcomeGuardError, match="no cohort or clinical input was read"):
        run("outcomes", cohorts=("liu2019",), runtime=runtime)

    assert not runtime.exists()


def test_outcome_free_materialization_projects_named_columns_without_opening_packets(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    manifest = write_synthetic_materialization(runtime)
    from tools.a_cohorts import core as cohort_core

    monkeypatch.setattr(
        cohort_core, "validate",
        lambda *_args, **_kwargs: pytest.fail("the packet-opening cohort validator was called"),
    )
    original_open = Path.open

    def guarded_open(path, *args, **kwargs):
        if path.name == "ingestion_packet.json":
            pytest.fail("an ingestion packet was opened")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)

    cohort = load_cohort_materialization(
        "invented_study",
        runtime=runtime,
        route="outcome-free",
        synthetic_manifest=manifest,
    )

    assert cohort.clinical_columns_read == (
        "patient_id", "drug_class", "batch", "biopsy"
    )
    assert set(cohort.clinical_rows[0]) == {
        "patient_id", "drug_class_normalised", "batch", "biopsy_site"
    }
    assert "Tumor_Shrinkage" not in cohort.clinical_rows[0]
    assert "raw_orr" not in cohort.clinical_rows[0]
    assert cohort.checks["ingestion_packet"] == "not_opened"


def test_synthetic_manifest_cannot_disguise_a_known_cohort_id_before_input_access(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    original_open = Path.open

    def guarded_open(path, *args, **kwargs):
        if path == runtime or runtime in path.parents:
            pytest.fail("a disguised synthetic identifier reached input access")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)

    with pytest.raises(ValueError, match="known cohort identifiers are not synthetic"):
        load_cohort_materialization(
            "invented_riaz_gse91061",
            runtime=runtime,
            route="outcome-free",
            synthetic_manifest=runtime / "invented_riaz_gse91061/simple/manifest.json",
        )

    assert not runtime.exists()


def test_signed_known_real_id_loads_outcome_free_from_invented_tables(tmp_path, monkeypatch):
    from tools.a_cohorts import core as cohort_core
    from tools.a_cohorts.view import cohort_metadata

    cohort_id = "riaz_gse91061"
    metadata = cohort_metadata(cohort_id)
    simple = tmp_path / cohort_id / "simple"
    simple.mkdir(parents=True)
    sample_ids = [f"invented_subject_{index}" for index in range(8)]
    expression = "gene\t" + "\t".join(sample_ids) + "\n" + "GZMA\t" + "\t".join("1" for _ in sample_ids) + "\n"
    (simple / "expression.tsv").write_text(expression, encoding="utf-8")
    columns = ("patient_id", "drug_class", "batch", "biopsy", "raw_orr", "Tumor_Shrinkage")
    with (simple / "clinical.tsv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for index, sample_id in enumerate(sample_ids):
            writer.writerow({
                "patient_id": sample_id,
                "drug_class": "ANTI_PD_L1_AXIS",
                "batch": "invented_batch",
                "biopsy": "invented_site",
                "raw_orr": "invented_hidden_label",
                "Tumor_Shrinkage": "invented_hidden_value",
            })
    (simple / "caveats.md").write_text("Invented table content only.\n", encoding="utf-8")
    output_hashes = {
        name: hashlib.sha256((simple / name).read_bytes()).hexdigest()
        for name in cohort_core.expected_output_names(cohort_id)
    }
    (simple / "manifest.json").write_text(json.dumps({
        "cohort": cohort_id,
        "loader_version": cohort_core.VERSION,
        "patients": len(sample_ids),
        "input_sha256": ["a" * 64],
        "input_files": {"invented-source": "b" * 64},
        "output_sha256": output_hashes,
    }), encoding="utf-8")
    original_open = Path.open

    def guarded_open(path, *args, **kwargs):
        if path.name == "ingestion_packet.json":
            pytest.fail("packet was opened while loading invented simple tables")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    loaded = load_cohort_materialization(
        cohort_id,
        runtime=tmp_path,
        route="outcome-free",
    )

    assert loaded.data_classification == "real"
    assert loaded.metadata == metadata
    assert loaded.clinical_columns_read == ("patient_id", "drug_class", "batch", "biopsy")
    assert all("raw_orr" not in row and "Tumor_Shrinkage" not in row for row in loaded.clinical_rows)
    assert loaded.checks["signed_eligibility"] == "passed"
    assert loaded.checks["ingestion_packet"] == "not_opened"


@pytest.mark.parametrize("cohort_id", (".", "..", "nested/name", "nested\\name"))
def test_fixture_rejects_non_component_cohort_ids_before_creating_paths(tmp_path, cohort_id):
    from tools.a_bio.fixtures import write_fixture

    runtime = tmp_path / "fixture-runtime"
    with pytest.raises(ValueError, match="one safe path component"):
        write_fixture(runtime, cohort_id=cohort_id)
    assert not runtime.exists()


def test_results_symlink_is_refused_before_input_reads(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    write_synthetic_materialization(runtime)
    results = tmp_path / "results"
    results.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (results / "A").symlink_to(outside, target_is_directory=True)
    original_open = Path.open

    def guarded_open(path, *args, **kwargs):
        if runtime in path.parents or path == runtime:
            pytest.fail("runtime input was read before the output path was rejected")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    with pytest.raises(ValueError, match="symlink"):
        run(
            "outcome-free",
            cohorts=("invented_study",),
            runtime=runtime,
            results=results,
            synthetic_manifests=(runtime / "invented_study/simple/manifest.json",),
            runner=FakeBridge(),
        )


def test_simple_materialization_rejects_expression_clinical_identity_mismatch(tmp_path):
    runtime = tmp_path / "runtime"
    manifest = write_synthetic_materialization(runtime)
    clinical_path = manifest.parent / "clinical.tsv"
    with (manifest.parent / "expression.tsv").open(newline="", encoding="utf-8") as stream:
        sample_id = next(csv.reader(stream, delimiter="\t"))[1]
    clinical_text = clinical_path.read_text(encoding="utf-8").replace(sample_id, "other_subject")
    clinical_path.write_text(clinical_text, encoding="utf-8")
    payload = __import__("json").loads(manifest.read_text(encoding="utf-8"))
    import hashlib

    payload["outputs_sha256"]["clinical.tsv"] = hashlib.sha256(clinical_path.read_bytes()).hexdigest()
    manifest.write_text(__import__("json").dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="expression and clinical identities do not align"):
        load_cohort_materialization(
            "invented_study",
            runtime=runtime,
            route="outcome-free",
            synthetic_manifest=manifest,
        )


def test_outcome_free_route_runs_bulk_qc_pca_panels_and_writes_patient_free_manifest(tmp_path):
    runtime = tmp_path / "runtime"
    manifest_path = write_synthetic_materialization(runtime)
    results = tmp_path / "results"

    summary = run(
        "outcome-free",
        cohorts=("invented_study",),
        runtime=runtime,
        results=results,
        synthetic_manifests=(manifest_path,),
        runner=FakeBridge(),
    )

    cohort = summary["cohorts"][0]
    assert cohort["status"] == "complete"
    assert cohort["completed_stages"] == ["panels", "pca", "qc"]
    assert set(cohort["clinical_columns_read"]) == {"batch", "biopsy", "drug_class", "patient_id"}
    run_root = results / "A" / "a_bio" / "outcome-free" / summary["run_id"]
    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    input_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["route"] == "outcome-free"
    assert manifest["input_sha256"]["invented_study"]["source_inputs_sha256"] == input_manifest["source_inputs_sha256"]
    assert manifest["source_inputs_sha256"]["invented_study"] == input_manifest["source_inputs_sha256"]
    assert manifest["cohorts"][0]["checks"]["ingestion_packet"] == "not_opened"
    assert set(manifest["cohorts"][0]["clinical_columns_read"]) == {
        "batch", "biopsy", "drug_class", "patient_id"
    }
    assert "Tumor_Shrinkage" not in (run_root / "summary.json").read_text(encoding="utf-8")
    bulk_root = run_root / "bulk" / "A" / "invented_study"
    assert (bulk_root / "qc/manifest.json").is_file()
    assert (bulk_root / "pca/manifest.json").is_file()
    assert (bulk_root / "scores/manifest.json").is_file()


def test_outcomes_route_keeps_endpoint_families_frozen_families_and_synthesis_strata(tmp_path):
    runtime = tmp_path / "runtime"
    endpoint_specs = (
        ("orr", "invented_orr", "Best response per RECIST 1.1 (paper methods); ORR CR/PR versus SD/PD."),
        ("clinical_benefit", "invented_cb_explicit_1", "Clinical benefit: durable clinical benefit (DCB) versus non-durable benefit (NDB)."),
        ("clinical_benefit", "invented_cb_explicit_2", "Clinical benefit: durable clinical benefit (DCB) versus non-durable benefit (NDB)."),
        ("clinical_benefit", "invented_cb_pfs", "Clinical benefit: PFS > 6 months."),
        ("source_label", "invented_source_label", "SOURCE_BINARY; responder/progressor source labels retained; SOFT does not define this as RECIST."),
    )
    manifests = []
    cohort_ids = []
    for endpoint, cohort_id, definition in endpoint_specs:
        cohort_ids.append(cohort_id)
        manifests.append(write_synthetic_materialization(
            runtime,
            cohort_id=cohort_id,
            endpoint_families=(endpoint,),
            endpoint_definition=definition,
        ))

    summary = run(
        "outcomes",
        cohorts=tuple(cohort_ids),
        runtime=runtime,
        results=tmp_path / "results",
        synthetic_manifests=manifests,
        runner=FakeBridge(),
    )

    run_root = tmp_path / "results" / "A" / "a_bio" / "outcomes" / summary["run_id"]
    availability = _read_tsv(run_root / "availability.tsv")
    for cohort_id in cohort_ids:
        rows = {row["unit_family"]: row for row in availability if row["cohort_id"] == cohort_id}
        assert set(rows) == {
            "panel", "m5m6_gene", "gene", "pathway", "panel_coverage90",
            "pathway_coverage90", "pathway_common", "targeted_subset", "fraction",
        }
        assert all(rows[family]["status"] == "available" for family in (
            "panel", "m5m6_gene", "gene", "pathway", "panel_coverage90",
            "pathway_coverage90", "pathway_common",
        ))
        assert rows["targeted_subset"]["reason"] == "non_targeted_platform"
        assert rows["fraction"]["reason"].startswith("A-COMP family is outside W2")

    orr_cohort = next(row for row in summary["cohorts"] if row["cohort_id"] == "invented_orr")
    assert set(orr_cohort["clinical_columns_read"]) == {
        "patient_id", "drug_class", "batch", "biopsy", "raw_orr", "orr", "endpoint_definition",
    }
    assert not ({"clinical_benefit", "raw_clinical_benefit", "treatment_outcome", "pfs", "os", "Tumor_Shrinkage"}
                & set(orr_cohort["clinical_columns_read"]))

    assert summary["endpoint_families"] == ["clinical_benefit", "orr", "source_label"]
    assert summary["synthesis_strata"] == [
        "per_cancer", "per_drug_class", "melanoma_cancer_drug", "across_cancers",
    ]
    bulk_rows = _read_tsv(run_root / "bulk_stages.tsv")
    per_study_bulk_rows = [row for row in bulk_rows if row["cohort_id"] != "meta"]
    assert {(row["endpoint_family"], row["stage"], row["collection"]) for row in per_study_bulk_rows} == {
        (endpoint, "de", "")
        for endpoint, _cohort, _definition in endpoint_specs
    } | {
        (endpoint, "fgsea", collection)
        for endpoint, _cohort, _definition in endpoint_specs
        for collection in ("hallmark", "reactome")
    }
    effects = _read_tsv(run_root / "effects.tsv")
    assert {row["endpoint_family"] for row in effects} == {endpoint for endpoint, _cohort, _ in endpoint_specs}
    assert {row["endpoint_definition_id"] for row in effects if row["endpoint_family"] == "clinical_benefit"} == {
        "CB_DCB_NDB_EXPLICIT", "CB_PFS_GT6M",
    }
    assert {row["endpoint_definition_id"] for row in effects if row["endpoint_family"] == "source_label"} == {
        "SOURCE_LABEL_UNSPECIFIED",
    }
    for row in _read_tsv(run_root / "synthesis" / "per_cancer" / "synthesis.tsv"):
        if row["endpoint_family"] == "source_label":
            assert row["stage"] == "per_study"
            assert row["status"] == "per_study_only"
            assert row["q"] == ""
    synthesis_status = _read_tsv(run_root / "synthesis_status.tsv")
    assert {row["stratum"] for row in synthesis_status} == {
        "per_cancer", "per_drug_class", "melanoma_cancer_drug", "across_cancers",
    }
    assert all(row["status"] == "complete" for row in synthesis_status)
    coverage = _read_tsv(run_root / "coverage.tsv")
    assert coverage
    assert all(row["complete"] == "false" for row in coverage if row["unit_family"] == "panel")
    assert all(row["complete"] == "false" for row in coverage if row["unit_family"] == "pathway")
    assert all(row["sensitivity_label"] == "sensitivity only; does not support claims alone"
               for row in coverage if row["unit_family"] in {"panel_coverage90", "pathway_coverage90", "pathway_common"})


def test_outcomes_route_retains_unavailable_cohort_and_stratum_reasons(tmp_path):
    runtime = tmp_path / "runtime"
    manifest = write_synthetic_materialization(runtime)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["outputs_sha256"]["expression.tsv"] = "0" * 64
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    summary = run(
        "outcomes",
        cohorts=("invented_study",),
        runtime=runtime,
        results=tmp_path / "results",
        synthetic_manifests=(manifest,),
        runner=FakeBridge(),
    )
    run_root = tmp_path / "results" / "A" / "a_bio" / "outcomes" / summary["run_id"]
    assert summary["cohorts"][0]["status"] == "unavailable"
    availability = _read_tsv(run_root / "availability.tsv")
    assert {row["unit_family"] for row in availability} == {
        "panel", "m5m6_gene", "gene", "pathway", "panel_coverage90",
        "pathway_coverage90", "pathway_common", "targeted_subset", "fraction",
    }
    assert all(row["status"] == "unavailable" and row["reason"] == "hash_validation_failed"
               for row in availability)
    synthesis = _read_tsv(run_root / "synthesis_status.tsv")
    assert len(synthesis) == 4
    assert all(row["status"] == "unavailable" and row["reason"] == "no_validated_cohorts"
               for row in synthesis)


def test_outcome_free_route_records_that_packet_validation_was_not_called(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    manifest_path = write_synthetic_materialization(runtime)
    original_open = Path.open
    from tools.a_cohorts import core as cohort_core

    monkeypatch.setattr(
        cohort_core,
        "validate",
        lambda *_args, **_kwargs: pytest.fail("packet-opening cohort validator was invoked"),
    )

    def guarded_open(path, *args, **kwargs):
        if path.name == "ingestion_packet.json":
            pytest.fail("outcome-free runner opened an ingestion packet")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    summary = run(
        "outcome-free",
        cohorts=("invented_study",),
        runtime=runtime,
        results=tmp_path / "results",
        synthetic_manifests=(manifest_path,),
        runner=FakeBridge(),
    )
    assert summary["cohorts"][0]["checks"]["ingestion_packet"] == "not_opened"


def test_outcomes_route_rejects_real_identifiers_before_opening_synthetic_manifests(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    cohort_id = "invented_riaz_gse91061"
    manifest = runtime / cohort_id / "simple" / "manifest.json"
    original_open = Path.open

    def guarded_open(path, *args, **kwargs):
        if path == runtime or runtime in path.parents:
            pytest.fail("protected cohort materialization was read before identifier rejection")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    with pytest.raises(ValueError, match="known cohort identifiers are not synthetic"):
        run(
            "outcomes",
            cohorts=(cohort_id,),
            runtime=runtime,
            synthetic_manifests=(manifest,),
        )


def test_synthetic_manifest_outside_runtime_is_rejected_before_it_is_read(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    outside = tmp_path / "manifest.json"
    outside.write_text("{}\n", encoding="utf-8")
    original_open = Path.open

    def guarded_open(path, *args, **kwargs):
        if path == outside:
            pytest.fail("out-of-runtime synthetic manifest was opened")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    with pytest.raises(ValueError, match="outside the expected cohort path"):
        run(
            "outcome-free",
            cohorts=("invented_study",),
            runtime=runtime,
            synthetic_manifests=(outside,),
        )


def test_simple_materialization_rejects_manifest_output_hash_mismatch(tmp_path):
    runtime = tmp_path / "runtime"
    manifest = write_synthetic_materialization(runtime)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["outputs_sha256"]["clinical.tsv"] = "0" * 64
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="output hash mismatch"):
        load_cohort_materialization(
            "invented_study",
            runtime=runtime,
            route="outcome-free",
            synthetic_manifest=manifest,
        )


def test_simple_materialization_rejects_clinical_schema_mismatch(tmp_path):
    runtime = tmp_path / "runtime"
    manifest = write_synthetic_materialization(runtime)
    clinical_path = manifest.parent / "clinical.tsv"
    with clinical_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream, delimiter="\t"))
    rows[0][0] = "subject"
    with clinical_path.open("w", newline="", encoding="utf-8") as stream:
        csv.writer(stream, delimiter="\t", lineterminator="\n").writerows(rows)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["outputs_sha256"]["clinical.tsv"] = hashlib.sha256(clinical_path.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="clinical table has an invalid named-column header"):
        load_cohort_materialization(
            "invented_study",
            runtime=runtime,
            route="outcome-free",
            synthetic_manifest=manifest,
        )


def test_targeted_subset_remains_per_study_and_has_no_pooled_fdr(tmp_path, monkeypatch):
    from tools.a_meta import features

    cohort_id = "invented_targeted"
    monkeypatch.setattr(features, "TARGETED_SUBSET_STUDIES", {cohort_id})
    runtime = tmp_path / "runtime"
    manifest = write_synthetic_materialization(
        runtime,
        cohort_id=cohort_id,
        platform="targeted_rna",
        include_frozen_genes=True,
    )
    summary = run(
        "outcomes",
        cohorts=(cohort_id,),
        runtime=runtime,
        results=tmp_path / "results",
        synthetic_manifests=(manifest,),
        runner=FakeBridge(),
    )
    run_root = tmp_path / "results" / "A" / "a_bio" / "outcomes" / summary["run_id"]
    availability = {row["unit_family"]: row for row in _read_tsv(run_root / "availability.tsv")}
    assert availability["targeted_subset"]["status"] == "available"
    assert availability["gene"]["reason"] == "targeted_platform_excluded_from_gene_family"
    assert availability["pathway"]["reason"] == "targeted_platform_excluded_from_pathway_families"

    summaries = _read_tsv(run_root / "synthesis" / "per_cancer" / "synthesis.tsv")
    targeted_rows = [row for row in summaries if row["unit_family"] == "targeted_subset"]
    assert targeted_rows
    assert all(row["stage"] == "per_study" for row in targeted_rows)
    assert all(row["status"] == "per_study_only" for row in targeted_rows)
    assert all(row["q"] == "" for row in targeted_rows)
    assert all("pooling and FDR are disabled" in row["reason"] for row in targeted_rows)
    groups = _read_tsv(run_root / "synthesis" / "per_cancer" / "groups.tsv")
    assert all(row["unit_family"] != "targeted_subset" for row in groups)
