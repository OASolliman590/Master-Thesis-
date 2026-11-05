from __future__ import annotations

import csv
import hashlib
import json
from types import SimpleNamespace

import pytest

from tools.a_meta.__main__ import (
    _cohort_row_identity_sha256,
    _panel_coverage_counts,
    _validate_feature_manifest,
    main,
)
from tools.a_meta.effects import EFFECT_COLUMNS
from tools.a_meta.features import AVAILABLE_PANEL_IDS, FeatureTable
from tools.a_meta.provenance import SYNTHETIC_FIXTURE_PRODUCER, write_synthetic_fixture_manifest


def test_real_cohort_effects_are_refused_without_allow_outcomes(tmp_path):
    with pytest.raises(SystemExit, match="explicit --allow-outcomes"):
        main(["effects", "--cohort", "liu2019", "--results", str(tmp_path)])

    assert not (tmp_path / "liu2019").exists()


def test_adjusted_effect_models_are_refused_before_loading_a_cohort(tmp_path):
    with pytest.raises(SystemExit, match="Adjusted models are unavailable"):
        main(["effects", "--cohort", "synthetic", "--adjusted", "--results", str(tmp_path)])

    assert not (tmp_path / "synthetic").exists()


def test_real_effect_table_synthesis_is_refused_without_allow_outcomes(tmp_path):
    effect_dir = tmp_path / "synthetic-test-input"
    effect_dir.mkdir()
    effects_path = effect_dir / "effects.tsv"
    with effects_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(EFFECT_COLUMNS)
        writer.writerow({
            "unit_family": "panel", "unit": "PANEL", "study": "liu2019",
            "cancer": "melanoma", "cancer_components": "melanoma",
            "drug_class_stratum": "ALL", "endpoint_family": "orr",
            "endpoint_definition_id": "ORR", "patient_set_id": "set-hash",
            "n_R": 4, "n_NR": 4, "g": 0.2, "se": 0.1, "status": "ok",
        })
    (effect_dir / "manifest.json").write_text(json.dumps({
        "data_classification": "real",
        "cohort": "liu2019",
        "outputs_sha256": {"effects.tsv": hashlib.sha256(effects_path.read_bytes()).hexdigest()},
    }), encoding="utf-8")

    with pytest.raises(SystemExit, match="explicit --allow-outcomes"):
        main([
            "synthesize",
            "--effects",
            str(effects_path),
            "--stratum",
            "per_cancer",
            "--results",
            str(tmp_path / "results"),
        ])
    assert not (tmp_path / "results").exists()


def _feature_input_identities(view):
    from tools.a_cohorts.view import REPRESENTATION_FILE
    from tools.a_meta import __main__ as cli
    from tools.a_meta.frozen import IDENTIFIER_PROPOSALS
    from tools.a_meta.features import GENE_ALIAS_ADDENDUM_PATH
    from tools.a_scoring import ALIAS_TABLE_PATH, PANEL_REGISTRY_PATH

    return {
        "cohort_expression": hashlib.sha256(view.expression_path.read_bytes()).hexdigest(),
        "cohort_clinical": hashlib.sha256(
            (view.expression_path.parent / "clinical.tsv").read_bytes()
        ).hexdigest(),
        "representation_registry": hashlib.sha256(REPRESENTATION_FILE.read_bytes()).hexdigest(),
        "cohort_registry": hashlib.sha256(cli.REGISTRY.read_bytes()).hexdigest(),
        "panel_registry": hashlib.sha256(PANEL_REGISTRY_PATH.read_bytes()).hexdigest(),
        "gene_aliases": hashlib.sha256(ALIAS_TABLE_PATH.read_bytes()).hexdigest(),
        "gene_alias_addendum": hashlib.sha256(GENE_ALIAS_ADDENDUM_PATH.read_bytes()).hexdigest(),
        "hallmark_identifier_proposals": hashlib.sha256(IDENTIFIER_PROPOSALS.read_bytes()).hexdigest(),
    }

def test_synthetic_effect_table_requires_fixture_manifest_and_hash(tmp_path):
    effect_dir = tmp_path / "synthetic"
    effect_dir.mkdir()
    effects_path = effect_dir / "effects.tsv"
    with effects_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=EFFECT_COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerow({
            "unit_family": "panel", "unit": "PANEL", "study": "synthetic_study",
            "cancer": "melanoma", "cancer_components": "melanoma",
            "drug_class_stratum": "ALL", "endpoint_family": "source_label",
            "endpoint_definition_id": "SOURCE_LABEL_UNSPECIFIED", "patient_set_id": "set-hash",
            "n_R": 4, "n_NR": 4, "g": 0.2, "se": 0.1, "status": "ok",
        })
    write_synthetic_fixture_manifest(
        effect_dir / "manifest.json",
        kind="effect_table",
        payload_sha256="unused-for-file-input",
        cohort_ids=("synthetic_study",),
        output_path=effects_path,
    )

    assert main([
        "synthesize", "--effects", str(effects_path), "--stratum", "per_cancer",
        "--results", str(tmp_path / "results"),
    ]) == 0
    assert (tmp_path / "results/meta").is_dir()
    assert list((tmp_path / "results/meta").glob("*/synthesis.tsv"))


def test_synthetic_manifest_naming_real_cohort_is_refused_before_effect_read(tmp_path):
    effect_dir = tmp_path / "contradictory"
    effect_dir.mkdir()
    manifest_path = effect_dir / "manifest.json"
    manifest_path.write_text(json.dumps({
        "manifest_version": 1,
        "producer": "tools.a_meta.synthetic_fixture",
        "data_classification": "synthetic",
        "kind": "effect_table",
        "cohort": "liu2019",
        "cohort_ids": ["liu2019"],
    }), encoding="utf-8")

    with pytest.raises(SystemExit, match="Synthetic provenance contradicts"):
        main([
            "synthesize", "--effects", str(effect_dir / "effects.tsv"),
            "--stratum", "per_cancer", "--results", str(tmp_path / "results"),
        ])


def test_panel_coverage_counts_parse_false_strings_as_false():
    complete, incomplete = _panel_coverage_counts([
        {"unit_family": "panel", "complete": "true"},
        {"unit_family": "panel", "complete": "false"},
    ])

    assert (complete, incomplete) == (1, 1)


def test_coverage_cli_writes_aggregate_missing_genes_and_cyt_availability(tmp_path, monkeypatch):
    from tools.a_meta import __main__ as cli
    from tools.a_scoring.core import panel_definitions

    registry = tmp_path / "registry.tsv"
    registry.write_text(
        "cohort_id\trole\tstatus\nsynthetic\tdevelopment\tSIGNED for development\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "REGISTRY", registry)
    monkeypatch.setattr(
        cli,
        "cohort_view",
        lambda cohort, runtime: SimpleNamespace(
            metadata=SimpleNamespace(
                cohort_id="synthetic",
                representation=SimpleNamespace(platform="rnaseq", unit="tpm", transform="linear")
            ),
            clinical_rows=[{}],
        ),
    )
    all_panels = cli._panel_definitions(AVAILABLE_PANEL_IDS)
    available = {gene for members in all_panels.values() for gene in members} - {"CCL5", "PRF1"}
    available.add("GZMA")
    monkeypatch.setattr(
        cli,
        "_gene_table",
        lambda view, **kwargs: FeatureTable(
            cohort_id="synthetic",
            unit_family="gene",
            values_by_unit={gene: [1.0] for gene in available},
            n_patients=1,
            metadata={"scale_rule": "synthetic scale"},
        ),
    )
    output = tmp_path / "coverage.tsv"

    assert main(["coverage", "--output", str(output)]) == 0

    with output.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    ayers = next(row for row in rows if row["panel"] == "AYERS_GEP_18")
    assert len(rows) == len(AVAILABLE_PANEL_IDS)
    assert ayers["complete"] == "false"
    assert ayers["coverage90"] == "true"
    assert ayers["missing"] == "CCL5"
    assert ayers["n_patients"] == "1"
    assert ayers["patients_complete"] == "0"
    assert ayers["patients_coverage90"] == "1"
    assert ayers["cyt_gzma_present"] == "true"
    assert ayers["cyt_prf1_present"] == "false"
    assert ayers["cyt_complete"] == "false"
    assert ayers["linear_tpm_available"] == "true"
    text = output.read_text(encoding="utf-8").casefold()
    assert "patient_id" not in text
    assert "sample_id" not in text


def test_feature_manifest_rejects_stale_input_output_and_row_identity(tmp_path):
    cohort_dir = tmp_path / "cohort"
    feature_dir = cohort_dir / "features"
    feature_dir.mkdir(parents=True)
    expression_path = cohort_dir / "expression.tsv"
    clinical_path = cohort_dir / "clinical.tsv"
    expression_path.write_text("gene\tsample-a\nsymbol\t1\n", encoding="utf-8")
    clinical_path.write_text("patient_id\tsample_id\ttimepoint\npatient-a\tsample-a\tPRE\n", encoding="utf-8")
    feature_path = feature_dir / "genes.tsv"
    feature_path.write_text("patient_row\tGENE_A\n0\t1\n", encoding="utf-8")
    view = SimpleNamespace(
        expression_path=expression_path,
        clinical_rows=[{"patient_id": "patient-a", "sample_id": "sample-a", "timepoint": "PRE"}],
    )
    from tools.a_meta import __main__ as cli

    manifest_path = feature_dir / "manifest.json"
    manifest = {
        "cohort": "synthetic_cohort",
        "data_classification": "synthetic",
        "inputs_sha256": _feature_input_identities(view),
        "code_sha256": cli._code_hashes(),
        "outputs_sha256": {"genes.tsv": hashlib.sha256(feature_path.read_bytes()).hexdigest()},
        "row_identity_sha256": _cohort_row_identity_sha256(view),
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    _validate_feature_manifest(view, feature_dir, "synthetic_cohort")

    clinical_path.write_text("patient_id\tsample_id\ttimepoint\npatient-b\tsample-b\tPRE\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="stale relative to the current cohort view"):
        _validate_feature_manifest(view, feature_dir, "synthetic_cohort")

    clinical_path.write_text("patient_id\tsample_id\ttimepoint\npatient-a\tsample-a\tPRE\n", encoding="utf-8")
    feature_path.write_text("patient_row\tGENE_A\n0\t2\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="Feature output hash mismatch"):
        _validate_feature_manifest(view, feature_dir, "synthetic_cohort")

    feature_path.write_text("patient_row\tGENE_A\n0\t1\n", encoding="utf-8")
    view.clinical_rows[0]["patient_id"] = "patient-b"
    with pytest.raises(SystemExit, match="row identities"):
        _validate_feature_manifest(view, feature_dir, "synthetic_cohort")


def test_feature_manifest_rejects_old_code_identity(tmp_path):
    from tools.a_meta import __main__ as cli

    cohort_dir = tmp_path / "cohort"
    feature_dir = cohort_dir / "features"
    feature_dir.mkdir(parents=True)
    expression_path = cohort_dir / "expression.tsv"
    clinical_path = cohort_dir / "clinical.tsv"
    expression_path.write_text("gene\tfixture_row\nsymbol\t1\n", encoding="utf-8")
    clinical_path.write_text("fixture\nrow\n", encoding="utf-8")
    feature_path = feature_dir / "genes.tsv"
    feature_path.write_text("patient_row\tGENE_A\n0\t1\n", encoding="utf-8")
    view = SimpleNamespace(
        expression_path=expression_path,
        clinical_rows=[{}],
    )
    code_hashes = cli._code_hashes()
    code_hashes["tools/a_meta/features.py"] = "0" * 64
    manifest = {
        "cohort": "synthetic_cohort",
        "data_classification": "synthetic",
        "inputs_sha256": _feature_input_identities(view),
        "code_sha256": code_hashes,
        "outputs_sha256": {"genes.tsv": hashlib.sha256(feature_path.read_bytes()).hexdigest()},
        "row_identity_sha256": _cohort_row_identity_sha256(view),
    }
    (feature_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(SystemExit, match="code identity"):
        _validate_feature_manifest(view, feature_dir, "synthetic_cohort")


def test_gse176307_feature_manifest_rejects_old_matrix_source(tmp_path, monkeypatch):
    from tools.a_meta import __main__ as cli

    cohort_dir = tmp_path / "cohort"
    feature_dir = cohort_dir / "features"
    feature_dir.mkdir(parents=True)
    expression_path = cohort_dir / "expression.tsv"
    clinical_path = cohort_dir / "clinical.tsv"
    expression_path.write_text("gene\tfixture_row\nsymbol\t1\n", encoding="utf-8")
    clinical_path.write_text("fixture\nrow\n", encoding="utf-8")
    feature_path = feature_dir / "genes.tsv"
    feature_path.write_text("patient_row\tGENE_A\n0\t1\n", encoding="utf-8")
    view = SimpleNamespace(
        metadata=SimpleNamespace(cohort_id="gse176307"),
        expression_path=expression_path,
        clinical_rows=[{}],
    )
    current_sources = {"salmon_matrix.tsv.gz": "current-source-hash"}
    monkeypatch.setattr(cli, "_registry_ids", lambda: {"gse176307"})
    monkeypatch.setattr(cli, "_gse176307_source_hashes", lambda view, runtime: current_sources)
    manifest = {
        "cohort": "gse176307",
        "data_classification": "real",
        "inputs_sha256": {
            **_feature_input_identities(view),
            "salmon_matrix.tsv.gz": "old-matrix-hash",
        },
        "code_sha256": cli._code_hashes(),
        "outputs_sha256": {"genes.tsv": hashlib.sha256(feature_path.read_bytes()).hexdigest()},
        "feature_metadata": {"gene": {
            "source_route": "official Salmon TPM via the A-P2 GSE176307 assay mapping",
            "scale_rule": "log2(TPM+1); official GSE176307 Salmon TPM",
            "source_inputs_sha256": {"salmon_matrix.tsv.gz": "old-matrix-hash"},
        }},
        "row_identity_sha256": _cohort_row_identity_sha256(view),
    }
    (feature_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(SystemExit, match="source identities"):
        _validate_feature_manifest(view, feature_dir, "gse176307")


def test_gse135222_feature_manifest_requires_alias_addendum_identity(tmp_path, monkeypatch):
    from tools.a_meta import __main__ as cli

    cohort_dir = tmp_path / "cohort"
    feature_dir = cohort_dir / "features"
    feature_dir.mkdir(parents=True)
    expression_path = cohort_dir / "expression.tsv"
    clinical_path = cohort_dir / "clinical.tsv"
    expression_path.write_text("gene\tfixture_row\nsymbol\t1\n", encoding="utf-8")
    clinical_path.write_text("fixture\nrow\n", encoding="utf-8")
    feature_path = feature_dir / "genes.tsv"
    feature_path.write_text("patient_row\tCCL5\n0\t1\n", encoding="utf-8")
    view = SimpleNamespace(
        metadata=SimpleNamespace(cohort_id="gse135222"),
        expression_path=expression_path,
        clinical_rows=[{}],
    )
    inputs = _feature_input_identities(view)
    del inputs["gene_alias_addendum"]
    manifest = {
        "cohort": "gse135222",
        "data_classification": "real",
        "inputs_sha256": inputs,
        "code_sha256": cli._code_hashes(),
        "outputs_sha256": {"genes.tsv": hashlib.sha256(feature_path.read_bytes()).hexdigest()},
        "row_identity_sha256": _cohort_row_identity_sha256(view),
    }
    (feature_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(cli, "_registry_ids", lambda: {"gse135222"})

    with pytest.raises(SystemExit, match="analysis input identities"):
        _validate_feature_manifest(view, feature_dir, "gse135222")


def test_effects_ignore_old_optional_feature_after_reordered_rebuild(tmp_path, monkeypatch):
    from tools.a_meta import __main__ as cli

    cohort_id = "synthetic_reordered"
    source_dir = tmp_path / "source"
    feature_dir = tmp_path / "results" / cohort_id / "features"
    source_dir.mkdir()
    feature_dir.mkdir(parents=True)
    expression_path = source_dir / "expression.tsv"
    clinical_path = source_dir / "clinical.tsv"
    expression_path.write_text("gene\trow-b\trow-a\nGENE\t2\t1\n", encoding="utf-8")
    clinical_path.write_text(
        "patient_id\tsample_id\ttimepoint\nrow-b\trow-b\tPRE\nrow-a\trow-a\tPRE\n",
        encoding="utf-8",
    )
    view = SimpleNamespace(
        metadata=SimpleNamespace(endpoint_families=("orr",)),
        expression_path=expression_path,
        clinical_rows=[
            {"patient_id": "row-b", "sample_id": "row-b", "timepoint": "PRE"},
            {"patient_id": "row-a", "sample_id": "row-a", "timepoint": "PRE"},
        ],
    )
    outputs = {}
    for filename, content in {
        "genes.tsv": "patient_row\tGENE\n0\t2\n1\t1\n",
        "panels.tsv": "patient_row\tPANEL\n0\t2\n1\t1\n",
        "panel_coverage90.tsv": "patient_row\tPANEL\n0\t2\n1\t1\n",
        "coverage.tsv": "unit_family\tunit\tcomplete\npanel\tPANEL\ttrue\n",
        # This is an old optional table from before the patients were reordered.
        "pathways.tsv": "patient_row\tPATHWAY\n0\told-row-a\n1\told-row-b\n",
    }.items():
        path = feature_dir / filename
        path.write_text(content, encoding="utf-8")
        if filename != "pathways.tsv":
            outputs[filename] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {
        "data_classification": "synthetic",
        "producer": SYNTHETIC_FIXTURE_PRODUCER,
        "cohort": cohort_id,
        "inputs_sha256": _feature_input_identities(view),
        "code_sha256": cli._code_hashes(),
        "outputs_sha256": outputs,
        "feature_tables": {
            "gene": {"rows": 2},
            "panel": {"rows": 2},
            "panel_coverage90": {"rows": 2},
        },
        "row_identity_sha256": _cohort_row_identity_sha256(view),
    }
    (feature_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    loaded_families = []
    monkeypatch.setattr(cli, "cohort_view", lambda cohort, runtime: view)
    monkeypatch.setattr(
        cli,
        "read_feature_table",
        lambda path, *, cohort_id, unit_family, **kwargs: (
            loaded_families.append(unit_family)
            or SimpleNamespace(cohort_id=cohort_id, unit_family=unit_family)
        ),
    )
    monkeypatch.setattr(
        cli,
        "study_effects",
        lambda *args, **kwargs: [{"method_id": "CUSTOM_MEAN_SYNTHETIC_PANEL"}],
    )
    args = SimpleNamespace(
        cohort=cohort_id,
        runtime=None,
        allow_outcomes=False,
        unit_family="all",
        endpoint_family="all",
        no_drug_class=False,
    )

    with pytest.warns(RuntimeWarning, match="Ignoring unlisted feature file pathways.tsv"):
        cli._effects(args, tmp_path / "results")

    assert loaded_families == ["gene", "panel", "panel_coverage90"]
    effects_path = tmp_path / "results" / cohort_id / "effects" / "effects.tsv"
    effect_manifest = json.loads(
        (tmp_path / "results" / cohort_id / "effects" / "manifest.json").read_text(encoding="utf-8")
    )
    assert "method_id" in effects_path.read_text(encoding="utf-8").splitlines()[0].split("\t")
    assert effect_manifest["method_ids"] == ["CUSTOM_MEAN_SYNTHETIC_PANEL"]

    loaded_families.clear()
    (feature_dir / "panel_coverage90.tsv").unlink()
    manifest["outputs_sha256"].pop("panel_coverage90.tsv")
    manifest["feature_tables"].pop("panel_coverage90")
    (feature_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.warns(RuntimeWarning, match="Ignoring unlisted feature file pathways.tsv"):
        with pytest.raises(SystemExit, match="missing required panel_coverage90.tsv"):
            cli._effects(args, tmp_path / "results")
    assert loaded_families == []
