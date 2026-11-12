from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas", reason="run with envs/sc-analysis Python")

from tools.sc.sc3 import run_sc3_deseq2_released
from tools.sc.presentation import panel_definitions_for_sc1
from tools.sc.sc3_cli import run_released


OUTCOME_FIELDS = ["endpoint_family", "outcome_label", "response", "response_metric"]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_released_fixture(root: Path, *, record_status="TEST_ONLY_APPROVED"):
    inputs = root / "inputs"
    inputs.mkdir(parents=True)
    decision_path = root / "docs" / "decisions" / "fixture_sc3_release.md"
    decision_path.parent.mkdir(parents=True)
    decision_path.write_text("Invented test-only decision record. No authorization.\n", encoding="utf-8")

    registry_root = root / "registry"
    cohort_registry = registry_root / "docs" / "cohorts" / "REGISTRY.tsv"
    cohort_registry.parent.mkdir(parents=True)
    cohorts = ("fixture_sc3_study_A", "fixture_sc3_study_B")
    cohort_registry.write_text("cohort_id\n" + "\n".join(cohorts) + "\n", encoding="utf-8")
    lin_map = registry_root / "tools" / "sc" / "lin_cohort_map.tsv"
    lin_map.parent.mkdir(parents=True)
    lin_map.write_text("cohort\n" + "\n".join(cohorts) + "\n", encoding="utf-8")

    profiles = []
    for cohort_index, cohort in enumerate(cohorts):
        for arm in ("R", "NR"):
            for index in range(3):
                profiles.append({
                    "profile_id": f"fixture_profile_{cohort_index}_{arm}_{index}",
                    "patient_id": f"fixture_patient_{cohort_index}_{arm}_{index}",
                    "sample_id": f"fixture_specimen_{cohort_index}_{arm}_{index}",
                    "cohort": cohort,
                    "source_family": f"fixture_source_family_{cohort_index}",
                    "compartment": "T/NK",
                    "response_metric": "RECIST",
                    "endpoint_family": "RECIST",
                    "outcome_label": arm,
                    "response": arm,
                    "eligible": True,
                    "baseline": True,
                    "n_cells": 20,
                    "total_umis": 100_000,
                    "library_size": 100_000,
                    "cancer": "fixture_cancer",
                    "treatment": "aPD1",
                    "fraction_cells_total": 0.25,
                })

    clinical_path = inputs / "clinical.tsv"
    with clinical_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(profiles[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(profiles)

    expression_path = inputs / "expression.tsv"
    genes = sorted({
        gene
        for members in panel_definitions_for_sc1().values()
        for gene in members
    })
    with expression_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, delimiter="\t")
        writer.writerow(["gene", *[row["profile_id"] for row in profiles]])
        column_sums = [0] * len(profiles)
        for gene_index, gene in enumerate(genes):
            base = 50 + (gene_index % 25) * 2
            values = [
                base + ((gene_index + 5) * (profile_index + 2) % 23) * 3
                + (35 if row["outcome_label"] == "R" else 0)
                for profile_index, row in enumerate(profiles)
            ]
            column_sums = [total + value for total, value in zip(column_sums, values, strict=True)]
            writer.writerow([
                gene,
                *values,
            ])
        writer.writerow(["FIXTURE_OTHER_GENE", *[100_000 - total for total in column_sums]])

    manifest_path = inputs / "source_manifest.json"
    manifest = {
        "manifest_version": 1,
        "producer": "tools.sc.sc3_source_provenance",
        "data_classification": "source_derived_test_fixture",
        "kind": "sc3_input",
        "cohort_ids": list(cohorts),
        "source_family_by_cohort": {
            "fixture_sc3_study_A": "fixture_source_family_0",
            "fixture_sc3_study_B": "fixture_source_family_1",
        },
        "source_resolution_status": "RESOLVED",
        "overlap_resolution_status": "RESOLVED",
        "metric_resolution_status": "RESOLVED",
        "input_sha256": {
            "clinical": _sha256(clinical_path),
            "expression": _sha256(expression_path),
        },
    }
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")

    release_path = root / "fixture_release.json"
    release = {
        "record_type": "sc3_user_release_v1",
        "record_status": record_status,
        "real_authorization": False,
        "release_scope": "SC3_REAL_OUTCOME_ACCESS",
        "operation": "sc3-analysis",
        "input_manifest_sha256": _sha256(manifest_path),
        "input_sha256": manifest["input_sha256"],
        "cohorts": list(cohorts),
        "source_family_by_cohort": manifest["source_family_by_cohort"],
        "source_resolution_status": "RESOLVED",
        "overlap_resolution_status": "RESOLVED",
        "metric_resolution_status": "RESOLVED",
        "outcome_fields": OUTCOME_FIELDS,
        "decision": {
            "identity": "fixture_sc3_release",
            "path": "docs/decisions/fixture_sc3_release.md",
            "sha256": _sha256(decision_path),
        },
    }
    release_path.write_text(json.dumps(release, sort_keys=True) + "\n", encoding="utf-8")
    return clinical_path, expression_path, manifest_path, release_path, registry_root


def test_release_opt_in_and_record_are_required_before_payload_read_hash_or_output(tmp_path, monkeypatch):
    clinical, expression, manifest, release, registry = _write_released_fixture(tmp_path / "fixture")
    output = tmp_path / "results"
    payload_accesses = []

    def forbidden_hash(path):
        if Path(path) in {clinical, expression}:
            payload_accesses.append(("hash", Path(path)))
            raise AssertionError("payload hash reached before release preflight")
        return _sha256(Path(path))

    monkeypatch.setattr("tools.sc.sc3._input_sha256", forbidden_hash)
    with pytest.raises(PermissionError, match="explicit opt-in"):
        run_released(
            clinical, expression, manifest, output,
            allow_outcomes=False, release_record_path=release,
            test_only_root=tmp_path / "fixture", test_registry_root=registry,
        )
    assert payload_accesses == []
    assert not output.exists()

    with pytest.raises(PermissionError, match="release record"):
        run_released(
            clinical, expression, manifest, output,
            allow_outcomes=True, release_record_path=None,
            test_only_root=tmp_path / "fixture", test_registry_root=registry,
        )
    assert payload_accesses == []
    assert not output.exists()


def test_release_record_cannot_alias_the_input_manifest_before_reading_it(tmp_path, monkeypatch):
    root = tmp_path / "manifest_alias"
    clinical, expression, manifest, _release, registry = _write_released_fixture(root)
    payload_hashes = []
    def track_hash(path):
        payload_hashes.append(Path(path))
        return _sha256(Path(path))

    monkeypatch.setattr("tools.sc.sc3._input_sha256", track_hash)

    with pytest.raises(ValueError, match="alias"):
        run_released(
            clinical, expression, manifest, root / "results",
            allow_outcomes=True, release_record_path=manifest,
            test_only_root=root, test_registry_root=registry,
        )

    assert payload_hashes == []
    assert not (root / "results").exists()


@pytest.mark.parametrize(
    "mutation",
    [
        "status", "operation", "input_manifest_sha256", "input_sha256", "cohorts",
        "source_family_by_cohort", "source_resolution_status", "overlap_resolution_status",
        "metric_resolution_status", "outcome_fields",
    ],
)
def test_unapproved_or_mismatched_release_refuses_before_payload_hashes(tmp_path, monkeypatch, mutation):
    root = tmp_path / mutation
    clinical, expression, manifest, release_path, registry = _write_released_fixture(root)
    release = json.loads(release_path.read_text(encoding="utf-8"))
    if mutation == "status":
        release["record_status"] = "PENDING"
    elif mutation == "operation":
        release["operation"] = "another-operation"
    elif mutation == "input_manifest_sha256":
        release["input_manifest_sha256"] = "0" * 64
    elif mutation == "input_sha256":
        release["input_sha256"]["expression"] = "0" * 64
    elif mutation == "cohorts":
        release["cohorts"] = ["another_fixture_study"]
    elif mutation == "source_family_by_cohort":
        release["source_family_by_cohort"]["fixture_sc3_study_A"] = "another_fixture_family"
    elif mutation in {"source_resolution_status", "overlap_resolution_status", "metric_resolution_status"}:
        release[mutation] = "UNRESOLVED"
    else:
        release["outcome_fields"] = ["overall_survival"]
    release_path.write_text(json.dumps(release, sort_keys=True) + "\n", encoding="utf-8")
    payload_hashes = []

    def guarded_hash(path):
        if Path(path) in {clinical, expression}:
            payload_hashes.append(Path(path))
            raise AssertionError("mismatched release reached payload hashing")
        return _sha256(Path(path))

    monkeypatch.setattr("tools.sc.sc3._input_sha256", guarded_hash)
    with pytest.raises(PermissionError):
        run_released(
            clinical, expression, manifest, root / "results",
            allow_outcomes=True, release_record_path=release_path,
            test_only_root=root, test_registry_root=registry,
        )
    assert payload_hashes == []
    assert not (root / "results").exists()


def test_test_only_release_runs_real_de_and_a_meta_adapters_on_invented_inputs(tmp_path):
    if not shutil.which("Rscript"):
        pytest.skip("Rscript is unavailable")
    root = tmp_path / "positive_fixture"
    clinical, expression, manifest, release, registry = _write_released_fixture(root)

    output = run_released(
        clinical, expression, manifest, root / "results",
        allow_outcomes=True, release_record_path=release,
        test_only_root=root, test_registry_root=registry,
    )

    effects = pd.read_csv(output / "sc3_effects.tsv", sep="\t")
    summaries = pd.read_csv(output / "a_meta_summaries.tsv", sep="\t")
    de_results = pd.read_csv(output / "de_results.tsv", sep="\t")
    result_manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert not effects.empty
    assert not summaries.empty
    assert not de_results.empty
    assert set(de_results["endpoint_family"]) == {"RECIST"}
    assert (summaries["status"] == "pooled").any()
    assert result_manifest["data_classification"] == "source_derived_test_fixture"
    assert result_manifest["patient_identifiers_written_scope"] == "public outputs only; private verified inputs may contain identities"
    assert (output / ".sc3_private" / "de_r_retained").is_dir()


def test_released_path_does_not_accept_synthetic_fixture_provenance(tmp_path, monkeypatch):
    root = tmp_path / "synthetic_spoof"
    clinical, expression, manifest, _release, _registry = _write_released_fixture(root)
    value = json.loads(manifest.read_text(encoding="utf-8"))
    value["producer"] = "tools.a_meta.synthetic_fixture"
    value["data_classification"] = "synthetic"
    manifest.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
    release_path = root / "fixture_release.json"
    release = json.loads(release_path.read_text(encoding="utf-8"))
    release["input_manifest_sha256"] = _sha256(manifest)
    release_path.write_text(json.dumps(release, sort_keys=True) + "\n", encoding="utf-8")
    payload_hashes = []

    def guarded_hash(path):
        if Path(path) in {clinical, expression}:
            payload_hashes.append(Path(path))
            raise AssertionError("synthetic spoof reached payload hashing")
        return _sha256(Path(path))

    monkeypatch.setattr("tools.sc.sc3._input_sha256", guarded_hash)

    with pytest.raises(PermissionError, match="source-derived"):
        run_released(
            clinical, expression, manifest, root / "results",
            allow_outcomes=True, release_record_path=release_path,
            test_only_root=root, test_registry_root=root / "registry",
        )
    assert payload_hashes == []


def test_test_only_release_refuses_punctuation_insensitive_protected_cohort_before_payload_hash(tmp_path, monkeypatch):
    root = tmp_path / "protected_fixture"
    clinical, expression, manifest, release_path, registry = _write_released_fixture(root)
    release = json.loads(release_path.read_text(encoding="utf-8"))
    release["cohorts"] = ["IM-vigor_2.10"]
    release_path.write_text(json.dumps(release, sort_keys=True) + "\n", encoding="utf-8")
    payload_hashes = []
    monkeypatch.setattr("tools.sc.sc3_cli._input_sha256", lambda path: payload_hashes.append(Path(path)))

    with pytest.raises(PermissionError, match="IMvigor210"):
        run_released(
            clinical, expression, manifest, root / "results",
            allow_outcomes=True, release_record_path=release_path,
            test_only_root=root, test_registry_root=registry,
        )
    assert payload_hashes == []


@pytest.mark.parametrize("protected_place", ["release", "decision"])
def test_release_and_decision_protected_paths_refuse_before_hashes(tmp_path, monkeypatch, protected_place):
    root = tmp_path / protected_place
    clinical, expression, manifest, release_path, registry = _write_released_fixture(root)
    release = json.loads(release_path.read_text(encoding="utf-8"))
    if protected_place == "release":
        protected_release = root / "IM-Vigor_2.10" / "release.json"
        protected_release.parent.mkdir()
        protected_release.write_text(json.dumps(release), encoding="utf-8")
        supplied_release = protected_release
    else:
        decision_path = root / "docs" / "decisions" / "IM-vigor_2.10" / "fixture_decision.md"
        decision_path.parent.mkdir()
        decision_path.write_text("Invented protected-path sentinel.\n", encoding="utf-8")
        release["decision"] = {
            "identity": "fixture_decision",
            "path": "docs/decisions/IM-vigor_2.10/fixture_decision.md",
            "sha256": _sha256(decision_path),
        }
        release_path.write_text(json.dumps(release, sort_keys=True) + "\n", encoding="utf-8")
        supplied_release = release_path

    hashed = []

    def guarded_hash(path):
        hashed.append(Path(path))
        return _sha256(Path(path))

    monkeypatch.setattr("tools.sc.sc3._input_sha256", guarded_hash)
    with pytest.raises(ValueError, match="forbidden protected paths"):
        run_released(
            clinical, expression, manifest, root / "results",
            allow_outcomes=True, release_record_path=supplied_release,
            test_only_root=root, test_registry_root=registry,
        )
    assert hashed == []
    assert not (root / "results").exists()


def test_protected_clinical_identity_is_refused_before_expression_hash(tmp_path, monkeypatch):
    root = tmp_path / "protected_identity"
    clinical_path, expression_path, manifest_path, release_path, registry = _write_released_fixture(root)
    clinical = pd.read_csv(clinical_path, sep="\t")
    clinical["cohort"] = "IM-vigor_2.10"
    clinical.to_csv(clinical_path, sep="\t", index=False)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["input_sha256"]["clinical"] = _sha256(clinical_path)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
    release = json.loads(release_path.read_text(encoding="utf-8"))
    release["input_sha256"] = manifest["input_sha256"]
    release["input_manifest_sha256"] = _sha256(manifest_path)
    release_path.write_text(json.dumps(release, sort_keys=True) + "\n", encoding="utf-8")
    expression_hashes = []
    real_hash = _sha256

    def guarded_hash(path):
        if Path(path) == expression_path:
            expression_hashes.append(Path(path))
        return real_hash(Path(path))

    monkeypatch.setattr("tools.sc.sc3._input_sha256", guarded_hash)
    with pytest.raises(PermissionError, match="IMvigor210"):
        run_released(
            clinical_path, expression_path, manifest_path, root / "results",
            allow_outcomes=True, release_record_path=release_path,
            test_only_root=root, test_registry_root=registry,
        )
    assert expression_hashes == []
    assert not (root / "results").exists()


@pytest.mark.requires_r
def test_direct_r_rechecks_release_before_payload_hash_when_record_changes(tmp_path):
    if not shutil.which("Rscript"):
        pytest.skip("Rscript is unavailable")
    root = tmp_path / "r_recheck_fixture"
    clinical, expression, manifest, release_path, registry = _write_released_fixture(root)

    def change_release_before_r(command, *, cwd, env, capture_output, text, check=False):
        release = json.loads(release_path.read_text(encoding="utf-8"))
        release["record_status"] = "PENDING"
        release_path.write_text(json.dumps(release, sort_keys=True) + "\n", encoding="utf-8")
        return subprocess.run(
            command, cwd=cwd, env=env, capture_output=capture_output, text=text, check=check,
        )

    from tools.r_bridge import RScriptError

    output = root / "r_output"
    with pytest.raises(RScriptError, match="release record is not approved"):
        run_sc3_deseq2_released(
            expression,
            clinical,
            manifest,
            release_path,
            output,
            [],
            allow_outcomes=True,
            retention_dir=root / "r_retained",
            test_only_root=root,
            test_registry_root=registry,
            runner=change_release_before_r,
        )
    assert not (output / "de_results.tsv").exists()


@pytest.mark.requires_r
def test_direct_r_rejects_actual_protected_identity_before_expression_hash(tmp_path):
    if not shutil.which("Rscript"):
        pytest.skip("Rscript is unavailable")
    root = tmp_path / "r_protected_identity"
    clinical, expression, manifest, release_path, registry = _write_released_fixture(root)

    def protect_clinical_before_r(command, *, cwd, env, capture_output, text, check=False):
        frame = pd.read_csv(clinical, sep="\t")
        frame["cohort"] = "IM-vigor_2.10"
        frame.to_csv(clinical, sep="\t", index=False)
        return subprocess.run(
            command, cwd=cwd, env=env, capture_output=capture_output, text=text, check=check,
        )

    from tools.r_bridge import RScriptError

    with pytest.raises(RScriptError, match="IMvigor210 is locked"):
        run_sc3_deseq2_released(
            expression,
            clinical,
            manifest,
            release_path,
            root / "protected_r_output",
            [],
            allow_outcomes=True,
            retention_dir=root / "protected_r_retained",
            test_only_root=root,
            test_registry_root=registry,
            runner=protect_clinical_before_r,
        )


@pytest.mark.parametrize("protected_path", ["release_record", "decision"])
@pytest.mark.requires_r
def test_direct_r_rejects_protected_release_paths_before_path_open(tmp_path, protected_path):
    if not shutil.which("Rscript"):
        pytest.skip("Rscript is unavailable")
    root = tmp_path / protected_path
    clinical, expression, manifest, release_path, registry = _write_released_fixture(root)
    release_reference = release_path
    if protected_path == "release_record":
        release_reference = root / "IM-vigor_2.10" / "release.json"
    else:
        record = json.loads(release_path.read_text(encoding="utf-8"))
        record["decision"] = {
            "identity": "blocked_decision",
            "path": "docs/decisions/IM-vigor_2.10/blocked_decision.md",
            "sha256": "0" * 64,
        }
        release_path.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")

    from tools.a_meta.frozen import read_frozen_aliases
    from tools.r_bridge import RScriptError, run_r

    output = root / "direct_r_path_output"
    script = Path(__file__).resolve().parents[2] / "r/scripts/sc3_deseq2.R"
    with pytest.raises(RScriptError, match="forbidden protected paths"):
        run_r(
            script,
            {"counts": expression, "clinical": clinical},
            {
                "expected_outputs": ["de_results.tsv", "de_refusals.tsv"],
                "design": "~ response",
                "fdr": 0.10,
                "authorization": {
                    "data_classification": "source_derived_test_fixture",
                    "allow_outcomes": True,
                    "provenance_manifest": str(manifest),
                    "release_record": str(release_reference),
                    "test_only_root": str(root),
                    "test_registry_root": str(registry),
                },
                "validated_groups": [],
                "frozen_aliases": read_frozen_aliases(),
            },
            output,
            retention_dir=root / "direct_r_path_retained",
        )
    assert not (output / "de_results.tsv").exists()
