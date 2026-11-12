from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas", reason="run with envs/sc-analysis Python")

from tools.sc.presentation import (
    AGGREGATE_COLUMNS,
    COMPARTMENT_QC_COLUMNS,
    HALLMARK_IFNG,
    LinProducts,
    LIN_COMPARTMENTS,
    SC1_PANEL_IDS,
    panel_definitions_for_sc1,
    build_presentation,
    main as presentation_main,
    read_lin_products,
    summarize_profiles,
    _add_provenance,
    _ici_only,
)


def test_sc1_uses_the_signed_eleven_custom_panels_and_alias():
    panels = panel_definitions_for_sc1()

    assert tuple(panels) == SC1_PANEL_IDS
    assert len(panels) == 11
    assert len(panels[HALLMARK_IFNG]) == 200
    assert "DDX58" in panels[HALLMARK_IFNG]
    assert "RIGI" not in panels[HALLMARK_IFNG]
    assert "TMT1B" in panels[HALLMARK_IFNG]
    assert len(panels["M5_CHECKPOINT_CANDIDATES"]) == 8
    assert len(panels["M6_EPIGENETIC_REGULATORS"]) == 13
    assert not set(panels["M5_CHECKPOINT_CANDIDATES"]) & set(panels["M6_EPIGENETIC_REGULATORS"])


def _clinical(n_donors: int = 5):
    return pd.DataFrame.from_records([
        {
            "profile_id": f"synthetic_profile_{index}",
            "patient_id": f"synthetic_patient_{index}",
            "sample_id": f"synthetic_specimen_{index}",
            "cohort": "invented_study",
            "cancer": "invented_cancer",
            "compartment": "T/NK",
            "treatment": "aPD1",
            "baseline": True,
            "eligible": True,
            "status": "eligible",
            "reason": "",
            "n_cells": 20,
            "total_umis": 1_000_000,
            "library_size": 1_000_000,
        }
        for index in range(n_donors)
    ])


def test_sc1_expression_alias_keeps_score_and_coverage_and_rejects_collisions():
    clinical = _clinical()
    panels = panel_definitions_for_sc1()
    expression = pd.DataFrame(
        100,
        index=list(panels[HALLMARK_IFNG]),
        columns=clinical["profile_id"].astype(str),
        dtype=float,
    )
    expression.loc["DDX58", clinical.loc[0, "profile_id"]] = float("nan")
    canonical = summarize_profiles(clinical, expression)
    aliased = summarize_profiles(clinical, expression.rename(index={"DDX58": "RIGI"}))
    canonical_row = canonical.loc[canonical["unit_id"].eq(HALLMARK_IFNG)].iloc[0]
    alias_row = aliased.loc[aliased["unit_id"].eq(HALLMARK_IFNG)].iloc[0]

    assert alias_row["median_log2_cpm_plus1"] == pytest.approx(canonical_row["median_log2_cpm_plus1"])
    assert alias_row["member_availability"] == canonical_row["member_availability"]
    assert alias_row["member_support_min"] == canonical_row["member_support_min"]
    assert alias_row["member_support_max"] == canonical_row["member_support_max"]
    collision = pd.concat([expression, expression.loc[["DDX58"]].rename(index={"DDX58": "RIGI"})])
    with pytest.raises(ValueError, match="collide after frozen gene alias"):
        summarize_profiles(clinical, collision)


def test_composites_are_scored_per_donor_after_full_library_cpm():
    panels = panel_definitions_for_sc1()
    clinical = _clinical()
    panel = panels["P_ANTIGEN_PRESENTATION"]
    focused_gene = panels["M5_CHECKPOINT_CANDIDATES"][0]
    expression = pd.DataFrame(
        0,
        index=(*panel, focused_gene),
        columns=clinical["profile_id"].tolist(),
        dtype=float,
    )
    expression.loc[panel[0]] = [1023, 1023, 1023, 0, 0]
    expression.loc[panel[1]] = [0, 0, 1023, 1023, 1023]
    expression.loc[focused_gene] = [1023] * 5

    result = summarize_profiles(clinical, expression)
    composite = result.loc[
        result["unit_id"].eq("P_ANTIGEN_PRESENTATION")
    ].iloc[0]
    gene = result.loc[result["unit_id"].eq(focused_gene)].iloc[0]

    assert composite["median_log2_cpm_plus1"] == pytest.approx(1.25)
    assert composite["median_log2_cpm_plus1"] != pytest.approx(2.5)
    assert composite["n_donors_support"] == 5
    assert gene["median_log2_cpm_plus1"] == pytest.approx(10.0)
    assert gene["median_cpm"] == pytest.approx(1023.0)


def test_four_donors_are_insufficient_and_missing_is_not_a_measured_zero():
    panels = panel_definitions_for_sc1()
    clinical = _clinical(n_donors=4)
    measured_zero, missing_gene = panels["M5_CHECKPOINT_CANDIDATES"][:2]
    expression = pd.DataFrame(
        0,
        index=(measured_zero, missing_gene),
        columns=clinical["profile_id"].tolist(),
        dtype=float,
    )
    expression.loc[missing_gene] = float("nan")

    result = summarize_profiles(clinical, expression).set_index("unit_id")

    assert result.loc[measured_zero, "n_donors_support"] == 4
    assert result.loc[measured_zero, "median_log2_cpm_plus1"] == pytest.approx(0.0)
    assert result.loc[measured_zero, "status"] == "insufficient_donors"
    assert result.loc[missing_gene, "n_donors_support"] == 0
    assert result.loc[missing_gene, "status"] == "not_assessed"


def test_panel_scores_require_eighty_percent_member_availability():
    panels = panel_definitions_for_sc1()
    clinical = _clinical()
    panel = panels["AYERS_GEP_18"]
    expression = pd.DataFrame(
        1023,
        index=panel[:15],
        columns=clinical["profile_id"].tolist(),
        dtype=float,
    )

    summary = summarize_profiles(clinical, expression)
    score = summary.loc[summary["unit_id"].eq("AYERS_GEP_18")].iloc[0]

    assert score["n_members_available_global"] == 15
    assert score["n_members_total"] == 18
    assert score["n_donors_support"] == 5
    assert score["status"] == "shown"

    too_sparse = summarize_profiles(clinical, expression.loc[list(panel[:14])])
    unscored = too_sparse.loc[too_sparse["unit_id"].eq("AYERS_GEP_18")].iloc[0]
    assert unscored["n_members_available_global"] == 14
    assert unscored["n_donors_support"] == 0
    assert unscored["status"] == "not_assessed"


ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_PRODUCER_REVISION = "a32c147b883486a8400768c9c12c24df0c83cef0"
HISTORICAL_CLI_SHA256 = "987bfb663da75612a673836194ae452ff8fb4ecc76f1e9c48343c8b7c6b8d4c3"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _code_ref(relative: str) -> dict[str, str]:
    path = ROOT / relative
    return {"path": relative, "sha256": _sha256(path)}


def _write_manifest(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _replace_fixture_cli_hash(atlas_dir: Path, expected: str) -> None:
    from tools.sc.cli import _slug

    manifests = [
        *(atlas_dir / "pseudobulk" / _slug(compartment) / "manifest.json"
          for compartment in LIN_COMPARTMENTS),
        atlas_dir / "compartments" / "manifest.json",
        atlas_dir / "qc" / "manifest.json",
    ]
    for path in manifests:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        matches = [row for row in manifest["code"] if row["path"] == "tools/sc/cli.py"]
        assert len(matches) == 1
        matches[0]["sha256"] = expected
        _write_manifest(path, manifest)


def _write_lin_products(atlas_dir: Path) -> Path:
    profiles = _clinical()
    profiles["cohort"] = "BRCA_Bassez1"
    profiles["cancer"] = "breast"
    profiles["study"] = "BRCA_Bassez1"
    profiles["response_metric"] = "TEST_ONLY_SENTINEL"
    profiles["response"] = "TEST_ONLY_SENTINEL"
    profiles["outcome_label"] = "TEST_ONLY_SENTINEL"
    profiles["endpoint_family"] = "TEST_ONLY_SENTINEL"
    profiles["count_layer"] = "counts.1"
    genes = ["GENE_X"]
    expression = pd.DataFrame(
        6_000,
        index=genes,
        columns=profiles["profile_id"].tolist(),
        dtype=int,
    )
    inputs = {"seurat": "a" * 64, "metadata": "b" * 64}
    code = [_code_ref(path) for path in (
        "r/scripts/sc_lin_pseudobulk.R", "r/R/sc_lin.R", "tools/sc/cli.py",
        "tools/sc/lin_cohort_map.tsv", "tools/sc/lin_compartment_map.tsv", "tools/a_scoring/core.py",
    )]

    from tools.sc.cli import LIN_COMPARTMENTS, _slug

    for compartment in LIN_COMPARTMENTS:
        slug = _slug(compartment)
        directory = atlas_dir / "pseudobulk" / slug
        directory.mkdir(parents=True, exist_ok=True)
        current = profiles[profiles["compartment"].eq(compartment)].copy()
        if compartment != "T/NK":
            current = current.iloc[:0].copy()
        current.to_csv(directory / "clinical.tsv", sep="\t", index=False)
        current_expression = expression.loc[:, current["profile_id"].tolist()]
        current_expression.to_csv(directory / "expression.tsv", sep="\t", index_label="gene")
        _write_manifest(directory / "manifest.json", {
            "atlas": "lin2026_atlas", "paper": "A", "unit": "patient",
            "compartment": compartment, "minimum_cells": 15, "minimum_umis": 5_000,
            "input_sha256": inputs, "code": code,
            "outputs": {
                "clinical.tsv": _sha256(directory / "clinical.tsv"),
                "expression.tsv": _sha256(directory / "expression.tsv"),
            },
        })

    compartments = atlas_dir / "compartments"
    compartments.mkdir(parents=True, exist_ok=True)
    aggregate_columns = [
        "study", "compartment", "gene", "status", "n_donors", "n_gene_donors",
        "median_log2_cpm_plus1", "q1_log2_cpm_plus1", "q3_log2_cpm_plus1",
        "median_cpm", "median_percent_cells_detected", "detection_limit_tag",
    ]
    pd.DataFrame([[
        "BRCA_Bassez1", "T/NK", "GENE_X", "shown", 5, 5, 9.97, 9.97, 9.97,
        1_000_000.0, 100.0, "measured_at_or_above_detection_limit",
    ]], columns=aggregate_columns).to_csv(
        compartments / "compartment_expression.tsv", sep="\t", index=False
    )
    qc_rows = [{
        "cohort": "BRCA_Bassez1", "compartment": compartment, "profiles": 5 if compartment == "T/NK" else 0,
        "eligible_donors": 5 if compartment == "T/NK" else 0, "na_profiles": 0 if compartment == "T/NK" else 0,
    } for compartment in LIN_COMPARTMENTS]
    pd.DataFrame(qc_rows).to_csv(compartments / "compartment_qc.tsv", sep="\t", index=False)
    (compartments / "compartment_dotplot.png").write_bytes(b"invented image bytes")
    _write_manifest(compartments / "manifest.json", {
        "atlas": "lin2026_atlas", "paper": "A", "unit": "patient",
        "expression": "donor median log2(CPM+1)", "minimum_cells": 15,
        "minimum_umis": 5_000, "minimum_donors_to_show": 5,
        "input_sha256": inputs, "code": code,
        "outputs": {
            "compartment_expression.tsv": _sha256(compartments / "compartment_expression.tsv"),
            "compartment_qc.tsv": _sha256(compartments / "compartment_qc.tsv"),
            "compartment_dotplot.png": _sha256(compartments / "compartment_dotplot.png"),
            "pcahawley_per_patient_expression.tsv": "c" * 64,
        },
    })
    qc = atlas_dir / "qc"
    qc.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{
        "cohort": "TNBC_Shiao", "count_layer": "ALL", "fractional_values": 8,
        "fractional_fraction": 0.1,
        "fractional_value_sample": "PROTECTED_SOURCE_VALUE_SENTINEL",
        "assessment": "fractional_values_compatible_with_normalized_values",
    }]).to_csv(qc / "data_quality.tsv", sep="\t", index=False)
    _write_manifest(qc / "manifest.json", {
        "atlas": "lin2026_atlas", "paper": "A", "unit": "patient-level raw-count audit",
        "input_sha256": inputs, "code": code,
        "outputs": {"data_quality.tsv": _sha256(qc / "data_quality.tsv")},
    })
    return atlas_dir


def test_sc1_reader_uses_named_safe_columns_and_never_opens_pca_exception(tmp_path, monkeypatch):
    atlas_dir = _write_lin_products(tmp_path / "A" / "sc_lin2026")
    pca_path = atlas_dir / "compartments" / "pcahawley_per_patient_expression.tsv"
    pca_path.write_text("protected sentinel", encoding="utf-8")
    reads = []
    original_read_csv = pd.read_csv

    def guarded_read_csv(path, *args, **kwargs):
        path = Path(path)
        if path.name == "clinical.tsv":
            reads.append(tuple(kwargs.get("usecols", ())))
        assert path.name != "pcahawley_per_patient_expression.tsv"
        return original_read_csv(path, *args, **kwargs)

    monkeypatch.setattr(pd, "read_csv", guarded_read_csv)
    products = read_lin_products(atlas_dir)

    protected = {"response", "response_metric", "outcome_label", "endpoint_family", "res_metric"}
    assert len(reads) == 6
    assert all(not (protected & set(columns)) for columns in reads)
    assert not protected.intersection(products.clinical.columns)
    assert "TEST_ONLY_SENTINEL" not in products.clinical.to_string()
    assert products.data_quality.loc[0, "assessment"] == "fractional_values_compatible_with_normalized_values"
    assert "fractional_value_sample" not in products.data_quality.columns


def test_sc1_manifest_ignores_extra_outputs_and_skips_normalized_paper_b_names(tmp_path, monkeypatch):
    atlas_dir = _write_lin_products(tmp_path / "A" / "sc_lin2026")
    manifest_path = atlas_dir / "compartments" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["outputs"]["./PCaHawley_per_patient_expression.tsv"] = "not-a-real-hash"
    manifest["outputs"]["unlisted_secret.tsv"] = "not-a-real-hash"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    from tools.sc import presentation

    original_sha = presentation._sha256
    hashed_names = []

    def guarded_sha(path):
        hashed_names.append(Path(path).name.casefold())
        assert Path(path).name.casefold() not in {
            "unlisted_secret.tsv", "pcahawley_per_patient_expression.tsv",
        }
        return original_sha(path)

    monkeypatch.setattr(presentation, "_sha256", guarded_sha)
    read_lin_products(atlas_dir)

    assert "unlisted_secret.tsv" not in hashed_names
    assert "pcahawley_per_patient_expression.tsv" not in hashed_names


def test_sc1_manifest_path_rejects_symlinks_before_reading(tmp_path):
    atlas_dir = _write_lin_products(tmp_path / "A" / "sc_lin2026")
    source = atlas_dir / "pseudobulk" / "t_nk" / "manifest.json"
    link = source.with_name("manifest-link.json")
    link.symlink_to(source)

    from tools.sc.presentation import _validate_artifact_manifest

    with pytest.raises(ValueError, match="cannot contain symlinks"):
        _validate_artifact_manifest(
            link,
            atlas="lin2026_atlas",
            paper="A",
            required_outputs=("clinical.tsv", "expression.tsv"),
            allowed_outputs=frozenset({"clinical.tsv", "expression.tsv"}),
        )


@pytest.mark.parametrize("relative", (
    Path("invented_IM-Vigor_210/manifest.json"),
    Path("invented/INGESTION_PACKET.JSON/manifest.json"),
))
def test_sc1_forbidden_manifest_paths_stop_before_read_or_hash(tmp_path, monkeypatch, relative):
    from tools.sc import presentation

    def forbidden_access(*_args, **_kwargs):
        pytest.fail("SC-1 touched a protected sentinel path")

    monkeypatch.setattr(Path, "read_text", forbidden_access)
    monkeypatch.setattr(presentation, "_sha256", forbidden_access)
    with pytest.raises(ValueError, match="forbidden protected paths"):
        presentation._validate_artifact_manifest(
            tmp_path / relative,
            atlas="lin2026_atlas",
            paper="A",
            required_outputs=("clinical.tsv",),
            allowed_outputs=frozenset({"clinical.tsv"}),
        )


def test_sc1_resolves_protected_manifest_ancestor_before_opening(tmp_path, monkeypatch):
    from tools.sc import presentation

    protected_parent = tmp_path / "invented" / "imvigor210"
    alias_parent = tmp_path / "invented" / "safe_alias"
    alias_parent.parent.mkdir()
    alias_parent.symlink_to(protected_parent, target_is_directory=True)

    def forbidden_access(*_args, **_kwargs):
        pytest.fail("SC-1 opened or hashed a resolved protected sentinel path")

    monkeypatch.setattr(Path, "read_text", forbidden_access)
    monkeypatch.setattr(presentation, "_sha256", forbidden_access)
    with pytest.raises(ValueError, match="forbidden protected paths"):
        presentation._validate_artifact_manifest(
            alias_parent / "manifest.json",
            atlas="lin2026_atlas",
            paper="A",
        )


def test_sc1_forbidden_atlas_path_stops_before_output_creation(tmp_path, monkeypatch):
    from tools.sc import presentation

    output = tmp_path / "safe_output"
    monkeypatch.setattr(Path, "mkdir", lambda *_args, **_kwargs: pytest.fail("SC-1 created output before path refusal"))
    with pytest.raises(ValueError, match="forbidden protected paths"):
        presentation.build_presentation(
            tmp_path / "invented" / "INGESTION_PACKET.JSON" / "sc_lin2026",
            output,
        )
    assert not output.exists()


def test_sc1_ici_filter_uses_recognized_membership_only():
    assert _ici_only("aPD1")
    assert _ici_only("aPD-L1")
    assert _ici_only("aPD1+aCTLA4")
    assert _ici_only("nivolumab+ipilimumab")
    assert not _ici_only("aPD1+lenvatinib")
    assert not _ici_only("aPD1+unknown_agent")
    assert not _ici_only("chemotherapy")


def test_sc1_profiles_reject_unmapped_non_ici_combination():
    clinical = _clinical()
    clinical.loc[0, "treatment"] = "aPD1+lenvatinib"
    expression = pd.DataFrame(
        0,
        index=["GENE_A"],
        columns=clinical["profile_id"].astype(str),
        dtype=int,
    )
    with pytest.raises(ValueError, match="ICI-only profiles"):
        summarize_profiles(clinical, expression)


def test_sc1_reader_rejects_changed_product_hashes_and_thresholds(tmp_path):
    atlas_dir = _write_lin_products(tmp_path / "A" / "sc_lin2026")
    profile_manifest = atlas_dir / "pseudobulk" / "t_nk" / "manifest.json"
    manifest = json.loads(profile_manifest.read_text(encoding="utf-8"))
    manifest["outputs"]["expression.tsv"] = "0" * 64
    profile_manifest.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="output hash mismatch"):
        read_lin_products(atlas_dir)

    atlas_dir = _write_lin_products(tmp_path / "second" / "sc_lin2026")
    aggregate_manifest = atlas_dir / "compartments" / "manifest.json"
    manifest = json.loads(aggregate_manifest.read_text(encoding="utf-8"))
    manifest["minimum_cells"] = 16
    aggregate_manifest.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="source thresholds differ"):
        read_lin_products(atlas_dir)


def test_sc1_reader_rejects_changed_profile_thresholds(tmp_path):
    atlas_dir = _write_lin_products(tmp_path / "A" / "sc_lin2026")
    profile_manifest = atlas_dir / "pseudobulk" / "t_nk" / "manifest.json"
    manifest = json.loads(profile_manifest.read_text(encoding="utf-8"))
    manifest["minimum_cells"] = 16
    profile_manifest.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="profile thresholds differ"):
        read_lin_products(atlas_dir)


def test_sc1_default_producer_verification_stays_bound_to_current_code(tmp_path):
    atlas_dir = _write_lin_products(tmp_path / "A" / "sc_lin2026")
    _replace_fixture_cli_hash(atlas_dir, HISTORICAL_CLI_SHA256)

    with pytest.raises(ValueError, match="code hash is stale or unverifiable: tools/sc/cli.py"):
        read_lin_products(atlas_dir)


def test_sc1_producer_revision_requires_exact_local_commit_before_product_reads(tmp_path, monkeypatch):
    from tools.sc import presentation

    atlas_dir = tmp_path / "invented" / "sc_lin2026"
    atlas_dir.mkdir(parents=True)
    output_dir = tmp_path / "presentation_output"

    def forbidden_access(*_args, **_kwargs):
        pytest.fail("producer revision validation must precede product reads, hashes, and writes")

    monkeypatch.setattr(Path, "read_text", forbidden_access)
    monkeypatch.setattr(pd, "read_csv", forbidden_access)
    monkeypatch.setattr(presentation, "_sha256", forbidden_access)
    monkeypatch.setattr(Path, "mkdir", forbidden_access)
    monkeypatch.setattr(
        presentation.subprocess, "run",
        lambda *_args, **_kwargs: pytest.fail("mutable references must be rejected before Git access"),
    )
    with pytest.raises(ValueError, match="full 40-character commit ID"):
        build_presentation(atlas_dir, output_dir=output_dir, producer_revision="main")
    assert not output_dir.exists()


@pytest.mark.parametrize("resolved", (
    "0" * 40,
    "not-a-commit",
))
def test_sc1_producer_revision_rejects_absent_or_noncommit_resolution(
    tmp_path, monkeypatch, resolved,
):
    from tools.sc import presentation

    def fake_run(args, **kwargs):
        assert args[-1] == f"{HISTORICAL_PRODUCER_REVISION}^{{commit}}"
        if resolved == "not-a-commit":
            raise subprocess.CalledProcessError(128, args)
        return subprocess.CompletedProcess(args, 0, stdout=f"{resolved}\n")

    monkeypatch.setattr(presentation.subprocess, "run", fake_run)
    with pytest.raises(ValueError, match="absent or does not resolve|exact immutable commit"):
        presentation._resolve_producer_revision(HISTORICAL_PRODUCER_REVISION)


def test_sc1_git_blob_reader_accepts_only_regular_allowlisted_blob(monkeypatch):
    from tools.sc import presentation

    blob = b"invented producer source bytes"
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if args[4] == "ls-tree":
            return subprocess.CompletedProcess(
                args, 0, stdout=b"100644 blob 0123456789abcdef0123456789abcdef01234567\ttools/sc/cli.py\0",
            )
        assert args[4:6] == ["cat-file", "blob"]
        return subprocess.CompletedProcess(args, 0, stdout=blob)

    monkeypatch.setattr(presentation.subprocess, "run", fake_run)
    assert presentation._git_blob_sha256(HISTORICAL_PRODUCER_REVISION, "tools/sc/cli.py") == hashlib.sha256(blob).hexdigest()
    assert len(calls) == 2
    assert "ls-tree" in calls[0]
    assert "cat-file" in calls[1]


def test_sc1_git_blob_reader_rejects_git_symlink_without_reading_blob(monkeypatch):
    from tools.sc import presentation

    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(
            args, 0, stdout=b"120000 blob 0123456789abcdef0123456789abcdef01234567\ttools/sc/cli.py\0",
        )

    monkeypatch.setattr(presentation.subprocess, "run", fake_run)
    with pytest.raises(ValueError, match="not a regular allowlisted blob"):
        presentation._git_blob_sha256(HISTORICAL_PRODUCER_REVISION, "tools/sc/cli.py")
    assert len(calls) == 1


@pytest.mark.parametrize("failure", ("missing_blob", "wrong_hash"))
def test_sc1_selected_producer_revision_rejects_missing_or_mismatched_blob_before_payloads(
    tmp_path, monkeypatch, failure,
):
    from tools.sc import presentation

    atlas_dir = _write_lin_products(tmp_path / "A" / "sc_lin2026")
    manifest = json.loads(
        (atlas_dir / "pseudobulk" / "t_nk" / "manifest.json").read_text(encoding="utf-8")
    )
    expected = {row["path"]: row["sha256"] for row in manifest["code"]}
    expected["tools/sc/cli.py"] = HISTORICAL_CLI_SHA256
    _replace_fixture_cli_hash(atlas_dir, HISTORICAL_CLI_SHA256)
    read_csv = pd.read_csv

    def payload_guard(path, *args, **kwargs):
        if Path(path).name in {"clinical.tsv", "expression.tsv", "compartment_expression.tsv", "data_quality.tsv"}:
            pytest.fail("producer source hash must validate before saved product payloads are read")
        return read_csv(path, *args, **kwargs)

    calls = []

    def reader(revision, code_name):
        assert revision == HISTORICAL_PRODUCER_REVISION
        calls.append(code_name)
        if failure == "missing_blob" and code_name == "r/scripts/sc_lin_pseudobulk.R":
            raise ValueError("invented missing blob")
        if failure == "wrong_hash" and code_name == "tools/sc/cli.py":
            return "f" * 64
        return expected[code_name]

    monkeypatch.setattr(pd, "read_csv", payload_guard)
    monkeypatch.setattr(
        presentation, "_sha256",
        lambda *_args, **_kwargs: pytest.fail("producer mismatch must precede input/output hashing"),
    )
    monkeypatch.setattr(
        presentation, "_resolve_producer_revision",
        lambda revision: HISTORICAL_PRODUCER_REVISION,
    )
    monkeypatch.setattr(presentation, "_git_blob_sha256", reader)
    output_dir = tmp_path / "new_presentation"
    with pytest.raises(ValueError, match="code hash is stale or unverifiable"):
        build_presentation(
            atlas_dir,
            output_dir=output_dir,
            producer_revision=HISTORICAL_PRODUCER_REVISION,
        )
    assert not output_dir.exists()
    assert calls


def test_sc1_historical_producer_revision_is_recorded_in_output_provenance(tmp_path, monkeypatch):
    from tools.sc import presentation

    atlas_dir = _write_complete_synthetic_lin_products(tmp_path / "A" / "sc_lin2026")
    manifest = json.loads(
        (atlas_dir / "pseudobulk" / "t_nk" / "manifest.json").read_text(encoding="utf-8")
    )
    expected = {row["path"]: row["sha256"] for row in manifest["code"]}
    expected["tools/sc/cli.py"] = HISTORICAL_CLI_SHA256
    _replace_fixture_cli_hash(atlas_dir, HISTORICAL_CLI_SHA256)
    calls = []

    def reader(revision, code_name):
        assert revision == HISTORICAL_PRODUCER_REVISION
        calls.append(code_name)
        return expected[code_name]

    monkeypatch.setattr(
        presentation, "_resolve_producer_revision",
        lambda revision: HISTORICAL_PRODUCER_REVISION,
    )
    monkeypatch.setattr(presentation, "_git_blob_sha256", reader)
    monkeypatch.setattr(
        presentation, "_write_figure",
        lambda _summary, path: (path.write_bytes(b"invented figure"), 6)[1],
    )
    output = tmp_path / "selected_revision_output"

    assert presentation_main([
        "--atlas-dir", str(atlas_dir),
        "--output-dir", str(output),
        "--producer-revision", HISTORICAL_PRODUCER_REVISION,
    ]) == 0

    output_manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    provenance = pd.read_csv(output / "provenance_coverage.tsv", sep="\t")
    assert output_manifest["producer_revision"] == HISTORICAL_PRODUCER_REVISION
    assert output_manifest["producer_verification"] == "immutable_git_commit"
    assert set(provenance["producer_revision"]) == {HISTORICAL_PRODUCER_REVISION}
    assert set(calls) == set(expected)
    assert len(calls) == len(expected) == 6


def test_sc1_presentation_refuses_to_write_into_source_product_roots(tmp_path):
    atlas_dir = tmp_path / "A" / "sc_lin2026"

    with pytest.raises(ValueError, match="new directory"):
        build_presentation(atlas_dir, output_dir=atlas_dir / "pseudobulk" / "new_output")


def test_sc1_forbidden_output_subtree_preflights_before_missing_source_resolution(tmp_path):
    atlas_dir = tmp_path / "not_created_source_atlas"
    output_dir = atlas_dir / "pseudobulk" / "nested_output"

    with pytest.raises(ValueError, match="new directory"):
        build_presentation(atlas_dir, output_dir=output_dir)

    assert not atlas_dir.exists()


def _write_complete_synthetic_lin_products(atlas_dir: Path) -> Path:
    atlas_dir = _write_lin_products(atlas_dir)

    definitions = panel_definitions_for_sc1()
    all_members = sorted({gene for members in definitions.values() for gene in members} - {"TMT1B"})
    focused_genes = [
        *definitions["M5_CHECKPOINT_CANDIDATES"],
        *definitions["M6_EPIGENETIC_REGULATORS"],
    ]
    profile_path = atlas_dir / "pseudobulk" / "t_nk"
    clinical_path = profile_path / "clinical.tsv"
    clinical = pd.read_csv(clinical_path, sep="\t", dtype=str, keep_default_na=False)
    profile_ids = clinical["profile_id"].astype(str).tolist()
    expression = pd.DataFrame(0, index=[*all_members, "OTHER_GENE"], columns=profile_ids, dtype=int)
    expression.loc["OTHER_GENE"] = 1_000_000
    expression.to_csv(profile_path / "expression.tsv", sep="\t", index_label="gene")
    manifest_path = profile_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["outputs"]["expression.tsv"] = _sha256(profile_path / "expression.tsv")
    _write_manifest(manifest_path, manifest)

    compartments = atlas_dir / "compartments"
    aggregate = pd.DataFrame.from_records([
        {
            "study": "BRCA_Bassez1", "compartment": "T/NK", "gene": gene,
            "status": "shown", "n_donors": 5, "n_gene_donors": 5,
            "median_log2_cpm_plus1": 0.0, "q1_log2_cpm_plus1": 0.0,
            "q3_log2_cpm_plus1": 0.0, "median_cpm": 0.0,
            "median_percent_cells_detected": 0.0,
            "detection_limit_tag": "below_scRNA_detection_limit",
        }
        for gene in focused_genes
    ], columns=AGGREGATE_COLUMNS)
    aggregate.to_csv(compartments / "compartment_expression.tsv", sep="\t", index=False)
    scope = pd.read_csv(
        ROOT / "docs/cohorts/SINGLE_CELL_LIN2026_COHORTS.tsv", sep="\t",
        usecols=["cohort", "paper_A_SC1"], dtype=str,
    )
    scope = scope[scope["paper_A_SC1"].str.casefold().eq("yes")]
    qc_rows = []
    for cohort in scope["cohort"]:
        for compartment in LIN_COMPARTMENTS:
            profiles = 5 if cohort == "BRCA_Bassez1" and compartment == "T/NK" else 0
            qc_rows.append({
                "cohort": cohort, "compartment": compartment, "profiles": profiles,
                "eligible_donors": profiles, "na_profiles": 0,
            })
    qc_frame = pd.DataFrame(qc_rows, columns=COMPARTMENT_QC_COLUMNS)
    qc_frame.to_csv(compartments / "compartment_qc.tsv", sep="\t", index=False)
    manifest_path = compartments / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["outputs"]["compartment_expression.tsv"] = _sha256(compartments / "compartment_expression.tsv")
    manifest["outputs"]["compartment_qc.tsv"] = _sha256(compartments / "compartment_qc.tsv")
    _write_manifest(manifest_path, manifest)
    return atlas_dir


def test_presentation_cli_outputs_readable_scoped_tables_and_provenance(tmp_path):
    atlas_dir = _write_complete_synthetic_lin_products(tmp_path / "A" / "sc_lin2026")

    assert presentation_main(["--atlas-dir", str(atlas_dir)]) == 0
    output = atlas_dir / "presentation_w5"

    summary = pd.read_csv(output / "unit_summary.tsv", sep="\t")
    provenance = pd.read_csv(output / "provenance_coverage.tsv", sep="\t")
    membership = pd.read_csv(output / "panel_membership.tsv", sep="\t")
    coverage = pd.read_csv(output / "coverage_audit.tsv", sep="\t")
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    expected_units = set(SC1_PANEL_IDS) | {
        gene for panel in ("M5_CHECKPOINT_CANDIDATES", "M6_EPIGENETIC_REGULATORS")
        for gene in panel_definitions_for_sc1()[panel]
    }
    assert set(summary["unit_id"]) == expected_units
    assert not {"profile_id", "patient_id", "sample_id", "response", "outcome_label"} & set(summary.columns)
    assert not summary.astype(str).apply(lambda column: column.str.contains("SENTINEL")).any().any()
    ifng = summary.loc[
        summary["study"].eq("BRCA_Bassez1")
        & summary["compartment"].eq("T/NK")
        & summary["unit_id"].eq(HALLMARK_IFNG)
    ].iloc[0]
    assert ifng["member_availability"] == "199/200"
    assert ifng["n_donors_support"] == 5
    assert ifng["status"] == "shown"
    ifng_members = set(membership.loc[
        membership["unit_id"].eq(HALLMARK_IFNG), "member_gene"
    ])
    assert len(ifng_members) == 200
    assert {"DDX58", "TMT1B"}.issubset(ifng_members)
    assert "RIGI" not in ifng_members
    ifng_coverage = coverage.loc[
        coverage["study"].eq("BRCA_Bassez1")
        & coverage["compartment"].eq("T/NK")
        & coverage["unit_id"].eq(HALLMARK_IFNG)
    ].iloc[0]
    assert ifng_coverage["n_members_required_80pct"] == 160
    assert ifng_coverage["donors_meeting_80pct"] == 5
    missing_compartment = summary.loc[
        summary["study"].eq("BRCA_Bassez1")
        & summary["compartment"].eq("malignant/epithelial")
    ]
    assert set(missing_compartment["status"]) == {"not_assessed"}
    tnbc = provenance.loc[
        provenance["study"].eq("TNBC_Shiao")
        & provenance["compartment"].eq("T/NK")
        & provenance["unit_id"].eq(HALLMARK_IFNG)
    ].iloc[0]
    assert tnbc["status"] == "not_assessed"
    assert "non_integer_or_invalid_raw_counts" in tnbc["reason"]
    assert "fractional_values_compatible_with_normalized_values" in tnbc["source_quality_assessment"]
    assert tnbc["bulk_overlap_flag"] == "not_assessed"
    assert tnbc["sorting"] == "not_assessed_from_safe_metadata"
    assert manifest["deferred_top_outcome_selected_genes"].startswith("deferred")
    assert manifest["clinical_outcome_columns_read"] == []
    assert {"panel_membership.tsv", "coverage_audit.tsv"}.issubset(manifest["outputs"])
    assert manifest["restricted_output_not_opened"] == "pcahawley_per_patient_expression.tsv"
    assert (output / "compartment_expression_panels.pdf").stat().st_size > 1000


def test_head_and_neck_display_is_blocked_pending_source_check():
    clinical = _clinical()
    clinical["cohort"] = "invented_head_neck_study"
    clinical["cancer"] = "Head and Neck"
    expression = pd.DataFrame(
        1023,
        index=panel_definitions_for_sc1()["P_ANTIGEN_PRESENTATION"],
        columns=clinical["profile_id"].astype(str),
        dtype=float,
    )
    qc = pd.DataFrame.from_records([
        {
            "cohort": "invented_head_neck_study", "compartment": compartment,
            "profiles": 5 if compartment == "T/NK" else 0,
            "eligible_donors": 5 if compartment == "T/NK" else 0, "na_profiles": 0,
        }
        for compartment in LIN_COMPARTMENTS
    ])
    products = LinProducts(
        clinical=clinical,
        expression=expression,
        aggregate_expression=pd.DataFrame(),
        compartment_qc=qc,
        data_quality=pd.DataFrame(columns=["cohort", "count_layer", "fractional_values", "assessment"]),
        cohort_scope=pd.DataFrame([{"cohort": "invented_head_neck_study", "cancer": "Head and Neck"}]),
        source_hashes=pd.DataFrame(columns=["source", "sha256"]),
        input_sha256={},
    )

    provenance = _add_provenance(summarize_profiles(clinical, expression), products)

    assert set(provenance["status"]) == {"not_assessed"}
    assert set(provenance["reason"]) == {"source_check_pending"}
    assert provenance["median_log2_cpm_plus1"].isna().all()
    assert set(provenance["source_mapping_status"]) == {"source_check_pending"}
    assert set(provenance["bulk_overlap_flag"]) == {"not_assessed"}
