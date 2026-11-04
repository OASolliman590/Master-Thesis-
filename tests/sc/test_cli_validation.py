from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas", reason="run with envs/sc-analysis Python")

from tools.sc.cli import _code_ref, _read_profiles


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_compartment(atlas_dir: Path, compartment: str, *, input_hash: str = "a" * 64,
                       clinical_compartment: str | None = None, atlas: str = "lin2026") -> Path:
    slug = compartment.casefold().replace("/", "_").replace(" ", "_")
    directory = atlas_dir / "pseudobulk" / slug
    directory.mkdir(parents=True, exist_ok=True)
    clinical = pd.DataFrame([{
        "profile_id": f"synthetic_patient__{slug}",
        "patient_id": "synthetic_patient",
        "sample_id": "synthetic_specimen",
        "compartment": clinical_compartment or compartment,
        "cohort": "invented_study",
        "eligible": "true",
        "status": "eligible",
        "n_cells": 16,
        "total_umis": 6_000,
        "library_size": 6_000,
    }])
    clinical.to_csv(directory / "clinical.tsv", sep="\t", index=False)
    expression = pd.DataFrame({clinical.iloc[0]["profile_id"]: [6_000]}, index=["GENE_A"])
    expression.to_csv(directory / "expression.tsv", sep="\t", index_label="gene")
    manifest = {
        "atlas": "lin2026_atlas" if atlas == "lin2026" else "prostate_hormone_naive_atlas",
        "paper": "A" if atlas == "lin2026" else "B",
        "unit": "patient",
        "compartment": compartment,
        "minimum_cells": 15,
        "minimum_umis": 5_000,
        "input_sha256": {"seurat": input_hash},
        "code": [_code_ref("tools/sc/cli.py"), _code_ref("tools/sc/core.py")],
        "outputs": {
            "expression.tsv": _digest(directory / "expression.tsv"),
            "clinical.tsv": _digest(directory / "clinical.tsv"),
        },
    }
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return directory


def test_read_profiles_accepts_hash_checked_patient_layout(tmp_path):
    atlas_dir = tmp_path / "A" / "sc_lin2026"
    _write_compartment(atlas_dir, "T/NK")

    clinical, expression = _read_profiles(atlas_dir, "lin2026")

    assert clinical.loc[0, "patient_id"] == "synthetic_patient"
    assert expression.loc["GENE_A", "synthetic_patient__t_nk"] == 6_000


def test_read_profiles_accepts_prostate_immune_compartment_layout(tmp_path):
    atlas_dir = tmp_path / "B" / "sc_prostate_hormone_naive_atlas"
    _write_compartment(atlas_dir, "T/NK", atlas="prostate")

    clinical, expression = _read_profiles(atlas_dir, "prostate")

    assert clinical.loc[0, "compartment"] == "T/NK"
    assert expression.loc["GENE_A", "synthetic_patient__t_nk"] == 6_000


def test_read_profiles_rejects_output_hash_or_clinical_expression_mismatch(tmp_path):
    atlas_dir = tmp_path / "A" / "sc_lin2026"
    directory = _write_compartment(atlas_dir, "T/NK")
    clinical_path = directory / "clinical.tsv"
    clinical = pd.read_csv(clinical_path, sep="\t")
    clinical.loc[0, "profile_id"] = "synthetic_other_profile"
    clinical.to_csv(clinical_path, sep="\t", index=False)

    with pytest.raises(ValueError, match="output hash mismatch"):
        _read_profiles(atlas_dir, "lin2026")

    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["outputs"]["clinical.tsv"] = _digest(clinical_path)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="Expression columns do not align"):
        _read_profiles(atlas_dir, "lin2026")


def test_read_profiles_rejects_compartment_or_shared_input_identity_mismatch(tmp_path):
    atlas_dir = tmp_path / "A" / "sc_lin2026"
    _write_compartment(atlas_dir, "T/NK", clinical_compartment="B/plasma")

    with pytest.raises(ValueError, match="membership differs"):
        _read_profiles(atlas_dir, "lin2026")

    atlas_dir = tmp_path / "A" / "another_lin2026"
    _write_compartment(atlas_dir, "T/NK", input_hash="a" * 64)
    _write_compartment(atlas_dir, "B/plasma", input_hash="b" * 64)
    with pytest.raises(ValueError, match="one input identity"):
        _read_profiles(atlas_dir, "lin2026")


def test_read_profiles_rejects_absolute_code_and_runtime_paths(tmp_path):
    atlas_dir = tmp_path / "A" / "sc_lin2026"
    directory = _write_compartment(atlas_dir, "T/NK")
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["code"][0]["path"] = "/absolute/script.py"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="relative paths and SHA256 hashes"):
        _read_profiles(atlas_dir, "lin2026")

    manifest["code"][0] = _code_ref("tools/sc/cli.py")
    manifest["r_run"] = {"r_library": "/absolute/library"}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="absolute script, library, or config"):
        _read_profiles(atlas_dir, "lin2026")
