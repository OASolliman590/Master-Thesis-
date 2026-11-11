from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.a_bio import runner as a_bio_runner
from tools.a_bio.paths import absolute_path, preflight_tree
from tools.a_bulk import core as bulk_core
from tools.a_meta import features
from tools.a_bio.enrichment import MetaRankingContract, run_meta_fgsea
from tests.a_bio.fakes import FakeBridge
from tests.a_bio.helpers import _read_tsv, write_synthetic_materialization


class _ClinicalAccessProbe:
    def __init__(self, *, cohort_id, classification, expression_path):
        self.dataset_id = cohort_id
        self.metadata = SimpleNamespace(
            cohort_id=cohort_id,
            cancer="melanoma",
            representation=SimpleNamespace(
                platform="rnaseq", unit="tpm", transform="linear", feature_id="symbol",
            ),
            de_engine="limma",
            endpoint_families=("orr",),
        )
        self.data_classification = classification
        self.expression_path = expression_path

    @property
    def clinical_rows(self):
        raise AssertionError("clinical payload was accessed before the entrypoint guard")


def test_endpoint_definition_view_rejects_real_classification_before_payload_access(tmp_path):
    view = _ClinicalAccessProbe(
        cohort_id="invented_endpoint_gate",
        classification="real",
        expression_path=tmp_path / "not-read.tsv",
    )

    with pytest.raises(bulk_core.OutcomeGuardError):
        bulk_core.endpoint_definition_views(
            view, "orr", results=tmp_path / "projections",
        )

    assert not (tmp_path / "projections").exists()


def test_endpoint_definition_view_rejects_known_real_identity_claimed_synthetic(tmp_path):
    view = _ClinicalAccessProbe(
        cohort_id="gse136961",
        classification="synthetic",
        expression_path=tmp_path / "not-read.tsv",
    )

    with pytest.raises(ValueError, match="synthetic"):
        bulk_core.endpoint_definition_views(
            view, "orr", results=tmp_path / "projections",
        )

    assert not (tmp_path / "projections").exists()


def test_endpoint_definition_view_rejects_forbidden_destination_before_clinical_access(tmp_path):
    view = _ClinicalAccessProbe(
        cohort_id="invented_endpoint_path",
        classification="synthetic",
        expression_path=tmp_path / "not-read.tsv",
    )

    with pytest.raises(ValueError, match="path|packet"):
        bulk_core.endpoint_definition_views(
            view, "orr", results=tmp_path / "ingestion_packet.json",
        )


def test_meta_fgsea_rejects_synthetic_spoof_before_ranking_or_output(tmp_path):
    dataset = SimpleNamespace(
        dataset_id="gse136961",
        metadata=SimpleNamespace(cohort_id="gse136961"),
        data_classification="synthetic",
        expression_path=tmp_path / "ingestion_packet.json",
        clinical_rows=(),
        clinical_path=None,
    )

    with pytest.raises(ValueError, match="synthetic"):
        run_meta_fgsea(
            dataset,
            summaries=(),
            mapping_by_unit={},
            endpoint_family="orr",
            endpoint_definition_id="ORR_RECIST_1_1",
            stratum="per_cancer",
            contract=MetaRankingContract("invented-guard", "estimate"),
            results=tmp_path / "results",
            runner=FakeBridge(),
        )

    assert not (tmp_path / "results").exists()


def test_meta_fgsea_rejects_forbidden_original_input_path_before_output(tmp_path):
    dataset = SimpleNamespace(
        dataset_id="invented_meta_path",
        metadata=SimpleNamespace(cohort_id="invented_meta_path"),
        data_classification="synthetic",
        expression_path=tmp_path / "ingestion_packet.json",
        clinical_rows=(),
        clinical_path=None,
    )

    with pytest.raises(ValueError, match="path"):
        run_meta_fgsea(
            dataset,
            summaries=(),
            mapping_by_unit={},
            endpoint_family="orr",
            endpoint_definition_id="ORR_RECIST_1_1",
            stratum="per_cancer",
            contract=MetaRankingContract("invented-path-guard", "estimate"),
            results=tmp_path / "results",
            runner=FakeBridge(),
        )

    assert not (tmp_path / "results").exists()


@pytest.mark.parametrize(
    "argument",
    ("runtime", "results", "retention_dir", "mapping", "provenance"),
)
def test_a_bio_rejects_packet_path_arguments_before_opening_them(tmp_path, monkeypatch, argument):
    sentinel = tmp_path / "ingestion_packet.json"
    original_open = Path.open

    def guarded_open(path, *args, **kwargs):
        if Path(path) == sentinel:
            raise AssertionError("forbidden packet sentinel was opened")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    call = {"results": tmp_path / "results"}
    if argument in {"runtime", "results", "retention_dir"}:
        call[argument] = sentinel
    elif argument == "mapping":
        call.update(
            packet_free_assay_mapping=sentinel,
            packet_free_assay_mapping_sha256="0" * 64,
        )
    else:
        call["synthetic_manifests"] = (sentinel,)

    with pytest.raises(ValueError, match="path|packet"):
        a_bio_runner.run(
            "outcome-free",
            cohorts=("invented_path_guard",),
            **call,
        )

    assert not sentinel.exists()


def test_a_bio_path_boundary_rejects_protected_and_resolved_symlink_components(tmp_path):
    with pytest.raises(ValueError):
        absolute_path(tmp_path / "IMvigor_210" / "invented.tsv", label="invented path")
    with pytest.raises(ValueError):
        absolute_path(tmp_path / "safe" / "ingestion_packet.json", label="invented path")

    alias = tmp_path / "safe_alias"
    alias.symlink_to(tmp_path / "IMvigor210" / "invented.tsv")
    with pytest.raises(ValueError):
        preflight_tree(alias, label="invented tree")

    nested = tmp_path / "invented_tree"
    nested.mkdir()
    (nested / "ingestion_packet.json").mkdir()
    with pytest.raises(ValueError):
        preflight_tree(nested, label="invented tree")


def test_gse176307_mapping_rejects_packet_sentinel_before_hash_or_parse(tmp_path, monkeypatch):
    sentinel = tmp_path / "ingestion_packet.json"
    monkeypatch.setattr(
        features, "file_sha256",
        lambda *_args, **_kwargs: pytest.fail("mapping bytes were hashed"),
    )

    with pytest.raises(features.FeatureUnavailableError) as error:
        features.read_gse176307_packet_free_assay_mapping(
            sentinel,
            expected_sha256="0" * 64,
            clinical_rows=(),
        )

    assert error.value.reason_code == "gse176307_packet_free_assay_mapping_path_unsafe"


def test_gse176307_mapping_rejects_protected_symlink_before_hash(tmp_path, monkeypatch):
    protected_path = tmp_path / "IMvigor210" / "invented_mapping.json"
    alias = tmp_path / "mapping_alias.json"
    alias.symlink_to(protected_path)
    monkeypatch.setattr(
        features, "file_sha256",
        lambda *_args, **_kwargs: pytest.fail("protected mapping bytes were hashed"),
    )

    with pytest.raises(features.FeatureUnavailableError) as error:
        features.read_gse176307_packet_free_assay_mapping(
            alias,
            expected_sha256="0" * 64,
            clinical_rows=(),
        )

    assert error.value.reason_code == "gse176307_packet_free_assay_mapping_path_unsafe"


def _remove_invented_expression_gene(manifest_path: Path, gene: str) -> None:
    expression_path = manifest_path.parent / "expression.tsv"
    with expression_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream, delimiter="\t"))
    rows = [row for row in rows if row[0] != gene]
    with expression_path.open("w", newline="", encoding="utf-8") as stream:
        csv.writer(stream, delimiter="\t", lineterminator="\n").writerows(rows)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["outputs_sha256"]["expression.tsv"] = hashlib.sha256(
        expression_path.read_bytes()
    ).hexdigest()
    manifest_path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


@pytest.mark.parametrize("platform", ("targeted_rna", "nanostring"))
@pytest.mark.parametrize("incomplete", (False, True))
def test_targeted_platforms_use_frozen_panel_route_with_strict_coverage(
    tmp_path, monkeypatch, platform, incomplete,
):
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("THESIS_RUNTIME", str(runtime))
    cohort_id = f"invented_{platform}_{'partial' if incomplete else 'complete'}"
    manifest = write_synthetic_materialization(
        runtime,
        cohort_id=cohort_id,
        platform=platform,
        endpoint_families=("orr",),
        include_frozen_genes=True,
    )
    panel_definitions = features._panel_definitions(features.AVAILABLE_PANEL_IDS)
    if incomplete:
        missing_gene = panel_definitions["AYERS_GEP_18"][0]
        _remove_invented_expression_gene(manifest, missing_gene)

    summary = a_bio_runner.run(
        "outcome-free",
        cohorts=(cohort_id,),
        runtime=runtime,
        results=tmp_path / "results",
        synthetic_manifests=(manifest,),
        runner=FakeBridge(),
    )

    assert summary["status"] == "complete"
    cohort_summary = summary["cohorts"][0]
    assert cohort_summary["stage_status"]["panels"]["status"] == "complete"
    panel_records = cohort_summary["panel_mapping"]["panel_availability"]
    assert tuple(row["panel_id"] for row in panel_records) == features.AVAILABLE_PANEL_IDS
    assert all(
        row["method_id"] == f"CUSTOM_MEAN_{row['panel_id']}"
        for row in panel_records
    )
    if incomplete:
        assert next(
            row for row in panel_records if row["panel_id"] == "AYERS_GEP_18"
        )["status"] == "unavailable"
    else:
        assert all(row["status"] == "available" for row in panel_records)

    view = a_bio_runner.load_cohort_materialization(
        cohort_id,
        runtime=runtime,
        route="outcome-free",
        synthetic_manifest=manifest,
    )
    with pytest.raises(ValueError, match="gene family excludes"):
        features.build_feature_table(view, "gene", runtime=runtime)
    with pytest.raises(ValueError, match="Pathway families exclude"):
        features.build_feature_table(view, "pathway", runtime=runtime, runner=FakeBridge())
