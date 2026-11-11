from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.a_bio import runner
from tools.a_bulk import BulkDataset
from tools.a_bulk import core as bulk_core
from tools.a_meta import features
from tools.a_meta.frozen import REACTOME_GMT, HALLMARK_GMT
from tests.a_bio.fakes import FakeBridge
from tests.a_bio.helpers import _read_tsv, write_synthetic_materialization


def _write_matrix(path: Path, sample_ids: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(["gene", *sample_ids])
        writer.writerow(["GENE_A", *range(1, len(sample_ids) + 1)])
        writer.writerow(["GENE_B", *range(2, len(sample_ids) + 2)])


def _endpoint_dataset(root: Path) -> BulkDataset:
    definitions = (
        "Clinical benefit: durable clinical benefit (DCB) versus non-durable benefit (NDB).",
        "Clinical benefit: PFS > 6 months.",
    )
    rows = []
    sample_ids = []
    for definition_index, definition in enumerate(definitions):
        for row_index in range(8):
            sample_id = f"invented_endpoint_{definition_index}_{row_index}"
            sample_ids.append(sample_id)
            rows.append({
                "patient_id": sample_id,
                "endpoint_definition": definition,
                "clinical_benefit": "DCB" if row_index < 4 else "NDB",
                "raw_clinical_benefit": "DCB" if row_index < 4 else "NDB",
                "drug_class_normalised": "OTHER_EXCLUDED" if definition_index == 0 and row_index == 0 else "ANTI_PD_L1_AXIS",
                "batch": f"batch_{row_index % 2}",
            })
    expression = root / "expression.tsv"
    root.mkdir(parents=True, exist_ok=True)
    _write_matrix(expression, sample_ids)
    metadata = SimpleNamespace(
        cohort_id="invented_mixed_definitions",
        cancer="melanoma",
        representation=SimpleNamespace(
            platform="rnaseq", unit="tpm", transform="linear", feature_id="symbol",
        ),
        de_engine="limma",
        endpoint_families=("clinical_benefit",),
    )
    return BulkDataset(
        paper="A", dataset_id="invented_mixed_definitions", metadata=metadata,
        expression_path=expression, clinical_rows=rows, data_classification="synthetic",
    )


def test_packet_free_gse_mapping_hashes_and_exact_patient_sample_pairs(tmp_path):
    assert hasattr(features, "_GSE176307_SOFT_SHA256")
    assert hasattr(features, "read_gse176307_packet_free_assay_mapping")
    path = tmp_path / "packet-free-map.json"
    mapping = {
        "schema_version": 1,
        "cohort_id": "gse176307",
        "source_inputs_sha256": {
            "salmon_tpm": features._GSE176307_TPM_SHA256,
            "sample_assay_key": features._GSE176307_KEY_SHA256,
            "geo_family_soft": features._GSE176307_SOFT_SHA256,
        },
        "rows": [
            {"patient_id": "invented_patient_1", "sample_id": "invented_geo_1", "tpm_assay_sample_id": "invented_assay_1"},
            {"patient_id": "invented_patient_2", "sample_id": "invented_geo_2", "tpm_assay_sample_id": "invented_assay_2"},
        ],
    }
    path.write_text(json.dumps(mapping, sort_keys=True), encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()

    patient_to_assay, identity = features.read_gse176307_packet_free_assay_mapping(
        path,
        expected_sha256=digest,
        clinical_rows=[
            {"patient_id": "invented_patient_1", "sample_id": "invented_geo_1"},
            {"patient_id": "invented_patient_2", "sample_id": "invented_geo_2"},
        ],
    )

    assert patient_to_assay == {
        "invented_patient_1": "invented_assay_1",
        "invented_patient_2": "invented_assay_2",
    }
    assert identity["mapping_sha256"] == digest
    assert identity["source_inputs_sha256"] == mapping["source_inputs_sha256"]

    with pytest.raises(features.FeatureUnavailableError, match="hash"):
        features.read_gse176307_packet_free_assay_mapping(
            path, expected_sha256="0" * 64,
            clinical_rows=[{"patient_id": "invented_patient_1", "sample_id": "invented_geo_1"}],
        )
    with pytest.raises(features.FeatureUnavailableError) as error:
        features.read_gse176307_packet_free_assay_mapping(
            path, expected_sha256=digest,
            clinical_rows=[{"patient_id": "invented_patient_1", "sample_id": "invented_geo_OTHER"}],
        )
    assert error.value.reason_code == "gse176307_packet_free_assay_mapping_identity_mismatch"


def test_gse176307_safe_assay_identity_is_named_at_clinical_read_boundary():
    from tools.a_cohorts.view import cohort_metadata

    for route in ("outcome-free", "outcomes"):
        columns = runner._clinical_columns(cohort_metadata("gse176307"), route)
        assert "patient_id" in columns
        assert "sample_id" in columns
        if route == "outcome-free":
            assert not any(name in {"raw_orr", "raw_clinical_benefit", "treatment_outcome"}
                           for name in columns)


def test_source_inventory_rejects_absolute_platform_paths_before_manifest_output():
    with pytest.raises(ValueError, match="unsafe path or hash"):
        runner._source_inventory_from_manifest({
            "source_inputs_sha256": {"C:\\private\\source.tsv": "a" * 64},
        })


def test_all_eleven_custom_panel_memberships_include_hallmark_ifng_not_wang_apm():
    panels = features._panel_definitions(features.AVAILABLE_PANEL_IDS)

    assert tuple(panels) == features.AVAILABLE_PANEL_IDS
    assert len(panels) == 11
    assert "HALLMARK_INTERFERON_GAMMA_RESPONSE" in panels
    assert "APM_WANG_18" not in panels
    assert panels["HALLMARK_INTERFERON_GAMMA_RESPONSE"] == features.read_hallmark_gene_sets(
        aliases=features.read_frozen_aliases()
    )["HALLMARK_INTERFERON_GAMMA_RESPONSE"]


def test_a_bulk_endpoint_definition_views_partition_exact_definitions_and_exclusions(tmp_path):
    dataset = _endpoint_dataset(tmp_path / "input")

    assert hasattr(bulk_core, "endpoint_definition_views")
    views = bulk_core.endpoint_definition_views(dataset, "clinical_benefit", results=tmp_path / "projected")

    assert {view.endpoint_definition_id for view in views} == {
        "CB_DCB_NDB_EXPLICIT", "CB_PFS_GT6M",
    }
    first = next(view for view in views if view.endpoint_definition_id == "CB_DCB_NDB_EXPLICIT")
    second = next(view for view in views if view.endpoint_definition_id == "CB_PFS_GT6M")
    assert first.excluded_treatment_count == 1
    assert first.input_sample_count == 8
    assert first.analysis_sample_count == 7
    assert second.excluded_treatment_count == 0
    assert second.analysis_sample_count == 8
    assert first.dataset.expression_path.is_file() and second.dataset.expression_path.is_file()
    assert first.dataset.expression_path != second.dataset.expression_path
    assert _matrix_header(first.dataset.expression_path) == [
        row["patient_id"] for row in first.dataset.clinical_rows
    ]
    assert "invented_endpoint_0_0" not in _matrix_header(first.dataset.expression_path)
    assert all(row["drug_class_normalised"] != "OTHER_EXCLUDED" for row in first.dataset.clinical_rows)
    assert len({row["endpoint_definition"] for row in first.dataset.clinical_rows}) == 1
    assert len({row["endpoint_definition"] for row in second.dataset.clinical_rows}) == 1


def test_endpoint_projection_rejects_nested_symlink_before_expression_read(tmp_path, monkeypatch):
    dataset = _endpoint_dataset(tmp_path / "input")
    projection = tmp_path / "projected"
    projection.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (projection / dataset.dataset_id).symlink_to(outside, target_is_directory=True)
    original_open = Path.open

    def guarded_open(path, *args, **kwargs):
        if Path(path) == dataset.expression_path:
            pytest.fail("expression was read before nested destination symlink rejection")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    with pytest.raises(ValueError, match="symlink"):
        bulk_core.endpoint_definition_views(dataset, "clinical_benefit", results=projection)


def _matrix_header(path: Path) -> list[str]:
    with path.open("r", newline="", encoding="utf-8") as stream:
        return next(csv.reader(stream, delimiter="\t"))[1:]


def test_meta_ranking_requires_explicit_contract_and_keeps_only_mapped_pooled_genes():
    assert hasattr(runner, "MetaRankingContract")
    assert hasattr(runner, "build_meta_ranking")
    MetaRankingContract = runner.MetaRankingContract
    build_meta_ranking = runner.build_meta_ranking
    summaries = [
        {"unit_family": "gene", "unit": "SYMBOL_A", "endpoint_family": "orr", "endpoint_definition_id": "ORR", "status": "pooled", "estimate": "0.75", "se": "0.25"},
        {"unit_family": "gene", "unit": "ENSEMBL:UNMAPPED", "endpoint_family": "orr", "endpoint_definition_id": "ORR", "status": "pooled", "estimate": "2.0", "se": "0.1"},
        {"unit_family": "panel", "unit": "PANEL_A", "endpoint_family": "orr", "endpoint_definition_id": "ORR", "status": "pooled", "estimate": "9.0", "se": "1.0"},
        {"unit_family": "gene", "unit": "SYMBOL_NOT_POOLED", "endpoint_family": "orr", "endpoint_definition_id": "ORR", "status": "not_pooled", "estimate": "4.0", "se": "0.5"},
        {"unit_family": "gene", "unit": "SYMBOL_OTHER_ENDPOINT", "endpoint_family": "clinical_benefit", "endpoint_definition_id": "CB_DCB_NDB_EXPLICIT", "status": "pooled", "estimate": "4.0", "se": "0.5"},
    ]
    mappings = {
        "SYMBOL_A": {"status": "mapped", "source_feature_id": "ENSG000001"},
        "ENSEMBL:UNMAPPED": {"status": "unmapped", "source_feature_id": "ENSG999999"},
        "SYMBOL_NOT_POOLED": {"status": "mapped", "source_feature_id": "ENSG000002"},
        "SYMBOL_OTHER_ENDPOINT": {"status": "mapped", "source_feature_id": "ENSG000003"},
    }

    ranking, report = build_meta_ranking(
        summaries,
        mappings,
        endpoint_family="orr",
        endpoint_definition_id="ORR",
        contract=MetaRankingContract(contract_id="invented-estimate-v1", statistic="estimate"),
    )

    assert ranking == [{"gene": "SYMBOL_A", "statistic": 0.75}]
    assert report["unmapped_gene_count"] == 1
    assert report["excluded_status_count"] == 1
    assert report["ranking_statistic"] == "estimate"


def test_frozen_fgsea_contracts_are_reported_as_dependencies_without_a_signed_meta_statistic():
    assert HALLMARK_GMT.is_file()
    assert REACTOME_GMT.is_file()
    assert hasattr(runner, "MetaRankingContract")
    with pytest.raises(ValueError, match="explicit"):
        runner.MetaRankingContract(contract_id="", statistic="estimate")
    with pytest.raises(ValueError, match="supported"):
        runner.MetaRankingContract(contract_id="invented-v1", statistic="p")


def test_unavailable_reasons_are_controlled_and_distinguish_scientific_causes():
    cases = (
        (ValueError("rank deficient design matrix"), "rank_deficient_design"),
        (ValueError("unsupported representation units"), "unsupported_units"),
        (ValueError("mapping coverage is insufficient"), "mapping_or_coverage_unavailable"),
        (ValueError("no eligible patients in responder and non-responder groups"), "no_eligible_patients"),
        (FileNotFoundError("source unavailable"), "missing_source"),
        (ValueError("dependency_not_attempted"), "dependency_not_attempted"),
    )

    actual = {runner._safe_error_code(error) for error, _expected in cases}

    assert actual == {expected for _error, expected in cases}


def test_outcomes_bulk_views_partition_definitions_map_de_to_symbols_and_report_pending_meta(tmp_path):
    runtime = tmp_path / "runtime"
    cohort_id = "invented_mixed_cb"
    manifest_path = write_synthetic_materialization(
        runtime,
        cohort_id=cohort_id,
        endpoint_families=("clinical_benefit",),
        sample_count=8,
        include_frozen_genes=True,
    )
    clinical_path = manifest_path.parent / "clinical.tsv"
    with clinical_path.open("r", newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        columns = reader.fieldnames
        rows = list(reader)
    definitions = (
        "Clinical benefit: durable clinical benefit (DCB) versus non-durable benefit (NDB).",
        "Clinical benefit: PFS > 6 months.",
    )
    for index, row in enumerate(rows):
        row["endpoint_definition"] = definitions[index // 4]
        label = "DCB" if index % 4 < 2 else "NDB"
        row["clinical_benefit"] = label
        row["raw_clinical_benefit"] = label
        row["drug_class"] = "OTHER_EXCLUDED" if index == 0 else "ANTI_PD_L1_AXIS"
    with clinical_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["outputs_sha256"]["clinical.tsv"] = hashlib.sha256(clinical_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    summary = runner.run(
        "outcomes",
        cohorts=(cohort_id,),
        runtime=runtime,
        results=tmp_path / "results",
        synthetic_manifests=(manifest_path,),
        runner=FakeBridge(),
    )

    run_root = tmp_path / "results" / "A" / "a_bio" / "outcomes" / summary["run_id"]
    stages = _read_tsv(run_root / "bulk_stages.tsv")
    de_rows = [row for row in stages if row["stage"] == "de"]
    assert {row["endpoint_definition_id"] for row in de_rows} == {
        "CB_DCB_NDB_EXPLICIT", "CB_PFS_GT6M",
    }
    first = next(row for row in de_rows if row["endpoint_definition_id"] == "CB_DCB_NDB_EXPLICIT")
    second = next(row for row in de_rows if row["endpoint_definition_id"] == "CB_PFS_GT6M")
    assert (first["input_sample_count"], first["excluded_treatment_count"], first["analysis_sample_count"]) == ("4", "1", "3")
    assert (second["input_sample_count"], second["excluded_treatment_count"], second["analysis_sample_count"]) == ("4", "0", "4")
    fgsea_rows = [row for row in stages if row["stage"] == "fgsea"]
    assert {(row["endpoint_definition_id"], row["collection"]) for row in fgsea_rows} == {
        (definition, collection)
        for definition in ("CB_DCB_NDB_EXPLICIT", "CB_PFS_GT6M")
        for collection in ("hallmark", "reactome")
    }
    mappings = list(run_root.rglob("de_symbol_mapping.tsv"))
    assert len(mappings) == 2
    assert all({row["mapping_status"] for row in _read_tsv(path)} >= {"mapped"} for path in mappings)
    meta_rows = [row for row in stages if row["stage"] == "meta_fgsea"]
    assert meta_rows
    assert {row["status"] for row in meta_rows} == {"unavailable"}
    assert {row["reason"] for row in meta_rows} == {"pending_meta_ranking_statistic_decision"}
    assert summary["status"] == "partial"


def test_run_identity_binds_endpoint_mapping_and_source_input_hashes(tmp_path):
    inputs = {
        "invented_study": {
            "source_inputs_sha256": {"invented-source": "a" * 64},
            "outputs_sha256": {"expression.tsv": "b" * 64},
        },
    }
    code = {"tools/a_meta/endpoint_definitions.py": "c" * 64}
    first_id = runner._run_id("outcome-free", ("invented_study",), inputs, code)

    changed_mapping_code = {**code, "tools/a_meta/endpoint_definitions.py": "d" * 64}
    changed_mapping_id = runner._run_id(
        "outcome-free", ("invented_study",), inputs, changed_mapping_code,
    )
    changed_input = {
        "invented_study": {
            "source_inputs_sha256": {"invented-source": "e" * 64},
            "outputs_sha256": {"expression.tsv": "b" * 64},
        },
    }
    changed_input_id = runner._run_id(
        "outcome-free", ("invented_study",), changed_input, code,
    )
    assert first_id != changed_mapping_id
    assert first_id != changed_input_id

    root = tmp_path / "results"
    run_root = root / "A" / "a_bio" / "outcome-free" / first_id
    run_root.mkdir(parents=True)
    summary = {"route": "outcome-free", "run_id": first_id}
    runner._write_json(run_root / "summary.json", summary)
    runner._write_json(run_root / "manifest.json", {
        "route": "outcome-free",
        "run_id": first_id,
        "input_sha256": inputs,
        "code_sha256": code,
        "output_sha256": runner._collect_output_hashes(run_root, exclude={"manifest.json"}),
    })
    with pytest.raises(FileExistsError, match="identity differs"):
        runner._preflight_existing_run(
            root, run_root, "outcome-free", first_id, changed_input, code,
        )
    with pytest.raises(FileExistsError, match="identity differs"):
        runner._preflight_existing_run(
            root, run_root, "outcome-free", first_id, inputs, changed_mapping_code,
        )


def test_invented_meta_fgsea_contract_executes_both_frozen_collections_through_bulk_api(tmp_path):
    runtime = tmp_path / "runtime"
    cohort_ids = ("invented_meta_melanoma_a", "invented_meta_melanoma_b", "invented_meta_melanoma_c")
    manifests = tuple(
        write_synthetic_materialization(
            runtime,
            cohort_id=cohort_id,
            endpoint_families=("orr",),
            cancer="melanoma",
            include_frozen_genes=True,
        )
        for cohort_id in cohort_ids
    )

    summary = runner.run(
        "outcomes",
        cohorts=cohort_ids,
        runtime=runtime,
        results=tmp_path / "results",
        synthetic_manifests=manifests,
        meta_ranking_contract=runner.MetaRankingContract(
            contract_id="invented_hg_estimate_v1", statistic="estimate",
        ),
        runner=FakeBridge(),
    )

    run_root = tmp_path / "results" / "A" / "a_bio" / "outcomes" / summary["run_id"]
    stages = _read_tsv(run_root / "bulk_stages.tsv")
    meta_rows = [row for row in stages if row["stage"] == "meta_fgsea"]
    assert {row["stratum"].split(":", 1)[0] for row in meta_rows} == set(runner.SYNTHESIS_STRATA)
    assert {row["collection"] for row in meta_rows} == {"hallmark", "reactome"}
    assert any(row["status"] == "complete" for row in meta_rows)
    assert any(row["reason"] == "no_eligible_pooled_gene_rows" for row in meta_rows)
    complete = next(row for row in meta_rows if row["status"] == "complete")
    assert complete["ranking_contract_id"] == "invented_hg_estimate_v1"
    assert int(complete["ranked_gene_count"]) >= 2
    rankings = [path for path in run_root.rglob("ranking.tsv") if "post_meta_fgsea" in path.parts]
    assert rankings
    gsea_manifests = [
        path for path in run_root.rglob("manifest.json")
        if "post_meta_fgsea" in path.parts and path.parent.name == "gsea"
    ]
    assert gsea_manifests
    second_checks = [
        path for path in run_root.rglob("fgsea_second_check.tsv")
        if "post_meta_fgsea" in path.parts
    ]
    assert second_checks
    mapping_paths = [
        path for path in run_root.rglob("symbol_mapping.tsv")
        if "post_meta_fgsea" in path.parts
    ]
    assert mapping_paths
    mapping_rows = _read_tsv(mapping_paths[0])
    assert {"cohort_id", "source_feature_id", "mapping_status", "mapping_method"} <= set(mapping_rows[0])
    assert {row["cohort_id"] for row in mapping_rows} == set(cohort_ids)
    assert all(row["mapping_status"] == "mapped" and row["mapping_method"] for row in mapping_rows)
    assert summary["biological_evidence"] is False
