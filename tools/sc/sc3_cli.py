"""Synthetic-only CLI connecting SC-3 effects to DESeq2 and A-META."""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from contextlib import nullcontext
from pathlib import Path

import pandas as pd

from tools.a_meta.provenance import (
    SYNTHETIC_FIXTURE_PRODUCER,
    effect_rows_payload,
    is_locked_study,
    known_cohort_ids,
    write_synthetic_fixture_manifest,
)
from tools.a_meta.synthesis import _read_effects, synthesize

from .presentation import _apply_frozen_gene_aliases
from .sc3 import (
    SC3_IDENTITY_COLUMNS,
    SC3_R_CLINICAL_COLUMNS,
    _input_sha256,
    _preflight_sc3_paths,
    _read_sc3_identity,
    _real_sc_cohorts,
    SC3_RELEASE_OPERATION,
    SC3_RELEASE_OUTCOME_FIELDS,
    SC3_RELEASE_SCOPE,
    _SC3_RELEASE_TOKEN,
    _validate_sc3_identity,
    _sc3_effects,
    authorize_sc3,
    group_profiles,
    metric_family,
    preflight_sc3_release,
    run_sc3_deseq2_released,
    run_sc3_deseq2_synthetic,
    validated_group_manifest,
    write_sc3_r_synthetic_manifest,
    _existing_sc3_file,
)


SC3_INPUT_COLUMNS = {
    "profile_id", "patient_id", "sample_id", "cohort", "source_family", "compartment",
    "response_metric", "endpoint_family", "outcome_label", "response", "eligible",
    "baseline", "n_cells", "total_umis", "library_size", "cancer", "treatment",
    "drug_class", "fraction_cells_total",
}
SC3_REQUIRED_COLUMNS = {
    "profile_id", "patient_id", "sample_id", "cohort", "source_family", "compartment",
    "outcome_label", "eligible", "baseline", "n_cells", "total_umis", "library_size",
    "cancer", "treatment",
}
OUTPUT_NAMES = (
    "sc3_effects.tsv", "sc3_refusals.tsv", "a_meta_summaries.tsv", "a_meta_subgroups.tsv",
    "de_results.tsv", "de_refusals.tsv",
)


def _preflight_manifest(path: Path) -> dict:
    path = _existing_sc3_file(path)
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PermissionError("SC-3 synthetic provenance is missing or malformed") from error
    if not isinstance(manifest, dict) or not isinstance(manifest.get("cohort_ids", ()), (list, tuple)):
        raise PermissionError("SC-3 synthetic provenance header is malformed")
    cohort_ids = {str(value).strip() for value in manifest.get("cohort_ids", ()) if str(value).strip()}
    input_hashes = manifest.get("input_sha256")
    if (
        manifest.get("manifest_version") != 1
        or manifest.get("producer") != SYNTHETIC_FIXTURE_PRODUCER
        or manifest.get("data_classification") != "synthetic"
        or manifest.get("kind") != "sc3_input"
        or not cohort_ids
        or not re.fullmatch(r"[0-9a-f]{64}", str(manifest.get("payload_sha256", "")))
        or not isinstance(input_hashes, dict)
        or set(input_hashes) != {"clinical", "expression"}
        or any(not re.fullmatch(r"[0-9a-f]{64}", str(value)) for value in input_hashes.values())
    ):
        raise PermissionError("SC-3 requires explicit invented synthetic provenance bound to both inputs")
    if any(is_locked_study(cohort) for cohort in cohort_ids):
        raise PermissionError("SC-3 refuses the locked IMvigor210 final test")
    if cohort_ids & (_real_sc_cohorts() | known_cohort_ids()):
        raise PermissionError("SC-3 synthetic fixtures cannot use a known real cohort")
    return manifest


def _clinical_columns(path: Path) -> list[str]:
    path = _existing_sc3_file(path)
    with path.open(newline="", encoding="utf-8") as stream:
        header = next(csv.reader(stream, delimiter="\t"), [])
    if not header or len(header) != len(set(header)):
        raise ValueError("SC-3 synthetic clinical header is missing or duplicated")
    missing = SC3_REQUIRED_COLUMNS - set(header)
    unknown = set(header) - SC3_INPUT_COLUMNS
    if missing or unknown:
        raise ValueError(
            f"SC-3 synthetic clinical schema mismatch; missing={sorted(missing)}, unknown={sorted(unknown)}"
        )
    if not ("response_metric" in header or "endpoint_family" in header):
        raise ValueError("SC-3 synthetic clinical input requires a declared response metric family")
    return header


def _verify_input_hashes(inputs: dict[str, Path], manifest: dict) -> dict[str, str]:
    hashes = {
        "clinical": _input_sha256(inputs["clinical"]),
        "expression": _input_sha256(inputs["expression"]),
    }
    if manifest.get("input_sha256") != hashes:
        raise PermissionError("SC-3 synthetic provenance does not bind the supplied clinical and expression files")
    return hashes


def _read_synthetic_inputs(
    clinical_path: Path,
    expression_path: Path,
    provenance_path: Path,
    manifest: dict,
    expected_hashes: dict[str, str],
):
    clinical_path = _existing_sc3_file(clinical_path)
    expression_path = _existing_sc3_file(expression_path)
    provenance_path = _existing_sc3_file(provenance_path)
    clinical_columns = _clinical_columns(clinical_path)
    clinical = pd.read_csv(
        clinical_path, sep="\t", usecols=clinical_columns, keep_default_na=True,
    )
    identity = clinical.loc[:, list(SC3_IDENTITY_COLUMNS)].fillna("").astype(str)
    declared_cohorts = set(map(str, manifest.get("cohort_ids", ())))
    _validate_sc3_identity(identity, declared_cohorts)
    authorize_sc3(clinical, provenance_manifest=provenance_path)
    profile_ids = clinical["profile_id"].astype(str).tolist()
    with expression_path.open(newline="", encoding="utf-8") as stream:
        expression_header = next(csv.reader(stream, delimiter="\t"), [])
    if not expression_header or expression_header[0] != "gene" or len(expression_header) != len(set(expression_header)):
        raise ValueError("SC-3 synthetic expression header is invalid")
    if not set(profile_ids).issubset(expression_header[1:]):
        raise ValueError("SC-3 synthetic expression columns do not align with clinical profiles")
    expression = pd.read_csv(
        expression_path, sep="\t", usecols=["gene", *profile_ids], index_col="gene", na_values=["NA"],
    )
    expression = expression.loc[:, profile_ids]
    expression = _apply_frozen_gene_aliases(expression)
    if expression.index.astype(str).duplicated().any() or expression.columns.astype(str).duplicated().any():
        raise ValueError("SC-3 synthetic expression identities must be unique after frozen alias resolution")
    if _input_sha256(clinical_path) != expected_hashes["clinical"] or _input_sha256(expression_path) != expected_hashes["expression"]:
        raise PermissionError("SC-3 synthetic inputs changed during validation")
    return clinical, expression


def _read_released_inputs(inputs: dict[str, Path], verified_release):
    """Read only the preflighted identity and named outcome fields for a released input."""
    clinical_path = _existing_sc3_file(inputs["clinical"])
    expression_path = _existing_sc3_file(inputs["expression"])
    header = _clinical_columns(clinical_path)
    clinical_outcomes = set(header) & set(SC3_RELEASE_OUTCOME_FIELDS)
    if not clinical_outcomes or not clinical_outcomes <= set(SC3_RELEASE_OUTCOME_FIELDS):
        raise PermissionError("SC-3 clinical header contains outcome fields outside the scoped release")
    clinical = pd.read_csv(
        clinical_path, sep="\t", usecols=header, keep_default_na=True,
    )
    authorize_sc3(
        clinical,
        allow_outcomes=True,
        provenance_manifest=verified_release.manifest_path,
        verified_release=verified_release,
    )
    profile_ids = clinical["profile_id"].astype(str).tolist()
    with expression_path.open(newline="", encoding="utf-8") as stream:
        expression_header = next(csv.reader(stream, delimiter="\t"), [])
    if not expression_header or expression_header[0] != "gene" or len(expression_header) != len(set(expression_header)):
        raise ValueError("SC-3 expression header is invalid")
    if not set(profile_ids).issubset(expression_header[1:]):
        raise ValueError("SC-3 expression columns do not align with clinical profiles")
    expression = pd.read_csv(
        expression_path, sep="\t", usecols=["gene", *profile_ids], index_col="gene", na_values=["NA"],
    ).loc[:, profile_ids]
    expression = _apply_frozen_gene_aliases(expression)
    if expression.index.astype(str).duplicated().any() or expression.columns.astype(str).duplicated().any():
        raise ValueError("SC-3 expression identities must be unique after frozen alias resolution")
    if (
        _input_sha256(clinical_path) != verified_release.input_sha256["clinical"]
        or _input_sha256(expression_path) != verified_release.input_sha256["expression"]
    ):
        raise PermissionError("SC-3 source-derived inputs changed during validation")
    return clinical, expression


def _write_tsv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, sep="\t", index=False, na_rep="NA")


def _partition_synthesis(
    effect_rows: list[dict],
    private: Path,
    *,
    stratum: str,
    verified_release=None,
):
    if verified_release is not None and getattr(verified_release, "proof", None) is not _SC3_RELEASE_TOKEN:
        raise PermissionError("SC-3 A-META synthesis requires a locally verified release proof")
    summaries: list[dict] = []
    subgroup_tests: list[dict] = []
    partition_manifest: list[dict] = []
    dimensions = sorted({
        (str(row["sc_endpoint_family"]), str(row["compartment"])) for row in effect_rows
    })
    for metric, compartment in dimensions:
        rows = [
            row for row in effect_rows
            if str(row["sc_endpoint_family"]) == metric and str(row["compartment"]) == compartment
        ]
        safe_key = re.sub(r"[^a-z0-9]+", "_", f"{metric}_{compartment}".casefold()).strip("_")
        normalized = _read_effects(rows)
        cohort_ids = sorted({str(row["study"]) for row in normalized if str(row.get("study", ""))})
        if verified_release is None:
            effect_manifest = private / f"effect_rows_{safe_key}.json"
            write_synthetic_fixture_manifest(
                effect_manifest,
                kind="effect_rows",
                payload=effect_rows_payload(normalized),
                cohort_ids=cohort_ids,
            )
            result = synthesize(
                rows,
                stratum,
                output_dir=private / "a_meta" / safe_key,
                provenance_manifest=effect_manifest,
                retention_dir=private / "a_meta_retained" / safe_key,
            )
        else:
            from tools.a_meta.provenance import canonical_sha256

            effect_file = private / f"released_effects_{safe_key}.tsv"
            pd.DataFrame.from_records(normalized).to_csv(
                effect_file, sep="\t", index=False, na_rep="NA",
            )
            effect_manifest = private / f"released_effects_{safe_key}.json"
            manifest = {
                "manifest_version": 1,
                "producer": "tools.sc.sc3_release_adapter",
                "data_classification": "real",
                "kind": "effect_file",
                "payload_sha256": canonical_sha256(effect_rows_payload(normalized)),
                "cohort_ids": cohort_ids,
                "outputs_sha256": {effect_file.name: _input_sha256(effect_file)},
                "cohort": cohort_ids[0] if cohort_ids else "",
            }
            effect_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            if verified_release.test_registry_root is None:
                registry_context = nullcontext()
            else:
                import tools.a_meta.provenance as provenance_api

                registry_file = verified_release.test_registry_root / "docs" / "cohorts" / "REGISTRY.tsv"

                class TestRegistryContext:
                    def __enter__(self):
                        self.original = provenance_api.REGISTRY
                        provenance_api.REGISTRY = registry_file

                    def __exit__(self, *_args):
                        provenance_api.REGISTRY = self.original

                registry_context = TestRegistryContext()
            with registry_context:
                result = synthesize(
                    effect_file,
                    stratum,
                    output_dir=private / "a_meta" / safe_key,
                    allow_outcomes=True,
                    provenance_manifest=effect_manifest,
                    retention_dir=private / "a_meta_retained" / safe_key,
                )
        for row in result.summaries:
            summaries.append({**row, "sc_endpoint_family": metric, "compartment": compartment})
        for row in result.subgroup_tests:
            subgroup_tests.append({**row, "sc_endpoint_family": metric, "compartment": compartment})
        pooled = any(row.get("status") == "pooled" for row in result.summaries)
        per_study_only = any(row.get("status") == "per_study_only" for row in result.summaries)
        partition_manifest.append({
            "metric_family": metric,
            "compartment": compartment,
            "a_meta_endpoint_family": sorted({str(row["endpoint_family"]) for row in rows}),
            "status": "pooled" if pooled else "per_study_only" if per_study_only else "no_estimable_synthesis",
            "pooled": pooled,
            "gate": (
                "SOURCE_LABEL_UNSPECIFIED is per-study only; metric compatibility remains unresolved"
                if metric in {"pathology", "expansion"}
                else ""
            ),
        })
    return summaries, subgroup_tests, partition_manifest


def _copy_private(source: Path, destination: Path, expected_sha256: str) -> None:
    shutil.copyfile(source, destination)
    if _input_sha256(destination) != expected_sha256:
        raise PermissionError("SC-3 verified private input copy failed its SHA256 check")
    destination.chmod(0o600)


def run_synthetic(
    clinical_path: Path | str,
    expression_path: Path | str,
    provenance_path: Path | str,
    output_dir: Path | str,
    *,
    stratum: str = "per_cancer",
) -> Path:
    """Run invented SC-3 effects, per-cohort DESeq2, and partitioned A-META."""
    inputs, provenance, output, _ = _preflight_sc3_paths(
        {"clinical": clinical_path, "expression": expression_path}, provenance_path, output_dir,
    )
    assert output is not None
    manifest = _preflight_manifest(provenance)
    header = _clinical_columns(inputs["clinical"])
    identity = _read_sc3_identity(inputs["clinical"])
    declared_cohorts = set(map(str, manifest["cohort_ids"]))
    _validate_sc3_identity(identity, declared_cohorts)
    hashes = _verify_input_hashes(inputs, manifest)
    clinical, expression = _read_synthetic_inputs(
        inputs["clinical"], inputs["expression"], provenance, manifest, hashes,
    )
    if set(header) != set(clinical.columns):
        raise ValueError("SC-3 safe clinical columns changed during read")

    groups, refusals = group_profiles(clinical, provenance_manifest=provenance)
    if not groups:
        raise ValueError("No baseline ICI SC-3 group meets the three-R/three-NR floor")
    effects = _sc3_effects(clinical, expression, provenance_manifest=provenance)
    effect_rows = effects.to_dict(orient="records")

    output.mkdir(mode=0o700)
    private = output / ".sc3_private"
    private.mkdir(mode=0o700)
    private.chmod(0o700)
    private_inputs = private / "verified_inputs"
    private_inputs.mkdir(mode=0o700)
    _copy_private(inputs["clinical"], private_inputs / "clinical.tsv", hashes["clinical"])
    _copy_private(inputs["expression"], private_inputs / "expression.tsv", hashes["expression"])
    _copy_private(provenance, private_inputs / "input_manifest.json", _input_sha256(provenance))

    group_contract = validated_group_manifest(clinical, groups, provenance_manifest=provenance)
    profile_group: dict[str, str] = {}
    for group, contract in zip(groups.values(), group_contract, strict=True):
        for profile_id in group.profile_ids:
            profile_group[str(profile_id)] = str(contract["group_id"])
    r_profile_ids = list(profile_group)
    r_clinical = clinical[clinical["profile_id"].astype(str).isin(r_profile_ids)].copy()
    r_clinical["sc3_group_id"] = r_clinical["profile_id"].astype(str).map(profile_group)
    r_clinical = r_clinical[[column for column in r_clinical.columns if column in SC3_R_CLINICAL_COLUMNS]]
    counts = expression.loc[:, r_profile_ids].copy()
    r_clinical_path = private_inputs / "sc3_clinical.tsv"
    counts_path = private_inputs / "sc3_counts.tsv"
    r_clinical.to_csv(r_clinical_path, sep="\t", index=False, na_rep="NA")
    counts.to_csv(counts_path, sep="\t", index_label="gene", na_rep="NA")
    r_provenance = private_inputs / "sc3_r_manifest.json"
    write_sc3_r_synthetic_manifest(counts_path, r_clinical_path, r_provenance)
    r_output = private / "de_results"
    r_retention = private / "de_r_retained"
    r_result = run_sc3_deseq2_synthetic(
        counts_path,
        r_clinical_path,
        r_provenance,
        r_output,
        group_contract,
        retention_dir=r_retention,
    )
    shutil.copyfile(r_result.outputs["de_results.tsv"], output / "de_results.tsv")
    shutil.copyfile(r_result.outputs["de_refusals.tsv"], output / "de_refusals.tsv")

    summary_rows, subgroup_rows, partitions = _partition_synthesis(
        effect_rows, private, stratum=stratum,
    )
    public_effects = effects.drop(columns=["source_family"], errors="ignore")
    _write_tsv(public_effects, output / "sc3_effects.tsv")
    _write_tsv(pd.DataFrame.from_records(refusals), output / "sc3_refusals.tsv")
    _write_tsv(pd.DataFrame.from_records(summary_rows), output / "a_meta_summaries.tsv")
    _write_tsv(pd.DataFrame.from_records(subgroup_rows), output / "a_meta_subgroups.tsv")

    metric_column = "response_metric" if "response_metric" in clinical else "endpoint_family"
    metric_families = sorted({
        str(family) for family in clinical[metric_column].map(metric_family).dropna()
    })
    private_hashes = {
        path.name: _input_sha256(path)
        for path in (private_inputs / "clinical.tsv", private_inputs / "expression.tsv", private_inputs / "input_manifest.json")
    }
    outputs = [output / name for name in OUTPUT_NAMES]
    manifest_output = {
        "analysis": "Paper A SC-3 synthetic effects, per-cohort DESeq2, and A-META synthesis",
        "data_classification": "synthetic",
        "status": "invented_data_only",
        "input_manifest_kind": manifest["kind"],
        "cohort_ids": sorted({str(value) for value in clinical["cohort"].dropna()}),
        "source_families": sorted({
            (str(row.cohort), str(row.source_family)) for row in clinical[["cohort", "source_family"]].drop_duplicates().itertuples(index=False)
        }),
        "response_metric_families": metric_families,
        "compartments": sorted({str(value) for value in clinical["compartment"].dropna()}),
        "drug_strata": sorted(set(effects["drug_class_stratum"].astype(str))) if not effects.empty else [],
        "a_meta_stratum": stratum,
        "a_meta_api": "tools.a_meta.synthesis.synthesize",
        "synthesis_partitions": partitions,
        "synthesis_gate": "unmapped or SOURCE_LABEL_UNSPECIFIED metric compatibility remains per-study only",
        "deseq2_api": "tools.r_bridge.run_r -> r/scripts/sc3_deseq2.R",
        "deseq2_group_count": len(group_contract),
        "private_r_retention": True,
        "private_verified_inputs_sha256": private_hashes,
        "input_sha256": {
            **hashes,
            "provenance_manifest": _input_sha256(provenance),
        },
        "outputs_sha256": {path.name: _input_sha256(path) for path in outputs},
        "patient_identifiers_written": False,
        "patient_identifiers_written_scope": "public outputs only; private verified inputs may contain identities",
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest_output, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    (output / "manifest.json").chmod(0o600)
    return output


def run_released(
    clinical_path: Path | str,
    expression_path: Path | str,
    provenance_path: Path | str,
    output_dir: Path | str,
    *,
    allow_outcomes: bool,
    release_record_path: Path | str | None,
    stratum: str = "per_cancer",
    test_only_root: Path | str | None = None,
    test_registry_root: Path | str | None = None,
    runner=None,
) -> Path:
    """Run SC-3 after matching an explicit source-derived release to every input."""
    inputs, provenance, release_record, output, verified, _ = preflight_sc3_release(
        {"clinical": clinical_path, "expression": expression_path},
        provenance_path,
        release_record_path,
        output_dir,
        allow_outcomes=allow_outcomes,
        test_only_root=test_only_root,
        test_registry_root=test_registry_root,
    )
    clinical, expression = _read_released_inputs(inputs, verified)
    groups, refusals = group_profiles(
        clinical,
        allow_outcomes=True,
        provenance_manifest=provenance,
        verified_release=verified,
    )
    if not groups:
        reasons = sorted({str(row.get("reason", "unusable")) for row in refusals})
        detail = "; ".join(reasons) if reasons else "no validated metric, source, or donor group"
        raise ValueError(f"No baseline ICI SC-3 group is estimable: {detail}")
    effects = _sc3_effects(
        clinical,
        expression,
        allow_outcomes=True,
        provenance_manifest=provenance,
        verified_release=verified,
    )
    effect_rows = effects.to_dict(orient="records")

    output.mkdir(mode=0o700)
    private = output / ".sc3_private"
    private.mkdir(mode=0o700)
    private.chmod(0o700)
    private_inputs = private / "verified_inputs"
    private_inputs.mkdir(mode=0o700)
    hashes = dict(verified.input_sha256)
    _copy_private(inputs["clinical"], private_inputs / "clinical.tsv", hashes["clinical"])
    _copy_private(inputs["expression"], private_inputs / "expression.tsv", hashes["expression"])
    _copy_private(provenance, private_inputs / "source_manifest.json", _input_sha256(provenance))
    _copy_private(release_record, private_inputs / "user_release.json", _input_sha256(release_record))

    group_contract = validated_group_manifest(
        clinical,
        groups,
        allow_outcomes=True,
        provenance_manifest=provenance,
        verified_release=verified,
    )
    r_group_contract = []
    for group, contract in zip(groups.values(), group_contract, strict=True):
        r_group_contract.append({**contract, "profile_ids": list(group.profile_ids)})
    r_output = private / "de_results"
    r_retention = private / "de_r_retained"
    r_result = run_sc3_deseq2_released(
        inputs["expression"],
        inputs["clinical"],
        provenance,
        release_record,
        r_output,
        r_group_contract,
        allow_outcomes=True,
        retention_dir=r_retention,
        test_only_root=test_only_root,
        test_registry_root=test_registry_root,
        runner=runner,
    )
    shutil.copyfile(r_result.outputs["de_results.tsv"], output / "de_results.tsv")
    shutil.copyfile(r_result.outputs["de_refusals.tsv"], output / "de_refusals.tsv")

    summary_rows, subgroup_rows, partitions = _partition_synthesis(
        effect_rows, private, stratum=stratum, verified_release=verified,
    )
    public_effects = effects.drop(columns=["source_family"], errors="ignore")
    _write_tsv(public_effects, output / "sc3_effects.tsv")
    _write_tsv(pd.DataFrame.from_records(refusals), output / "sc3_refusals.tsv")
    _write_tsv(pd.DataFrame.from_records(summary_rows), output / "a_meta_summaries.tsv")
    _write_tsv(pd.DataFrame.from_records(subgroup_rows), output / "a_meta_subgroups.tsv")

    metric_column = "response_metric" if "response_metric" in clinical else "endpoint_family"
    metric_families = sorted({
        str(family) for family in clinical[metric_column].map(metric_family).dropna()
    })
    private_hashes = {
        path.name: _input_sha256(path)
        for path in (
            private_inputs / "clinical.tsv", private_inputs / "expression.tsv",
            private_inputs / "source_manifest.json", private_inputs / "user_release.json",
        )
    }
    outputs = [output / name for name in OUTPUT_NAMES]
    manifest_output = {
        "analysis": "Paper A SC-3 source-derived effects, per-cohort DESeq2, and A-META synthesis",
        "data_classification": verified.classification,
        "status": "test_fixture_only" if verified.test_only_root is not None else "released_source_derived",
        "release_scope": SC3_RELEASE_SCOPE,
        "release_operation": SC3_RELEASE_OPERATION,
        "release_record_status": "test-only" if verified.test_only_root is not None else "approved",
        "input_manifest_kind": verified.manifest["kind"],
        "input_manifest_sha256": _input_sha256(provenance),
        "cohort_ids": sorted({str(value) for value in clinical["cohort"].dropna()}),
        "source_families": sorted({
            (str(row.cohort), str(row.source_family))
            for row in clinical[["cohort", "source_family"]].drop_duplicates().itertuples(index=False)
        }),
        "response_metric_families": metric_families,
        "compartments": sorted({str(value) for value in clinical["compartment"].dropna()}),
        "drug_strata": sorted(set(effects["drug_class_stratum"].astype(str))) if not effects.empty else [],
        "a_meta_stratum": stratum,
        "a_meta_api": "tools.a_meta.synthesis.synthesize",
        "synthesis_partitions": partitions,
        "synthesis_gate": "unmapped source metrics remain per-study only; source resolution must be explicit",
        "deseq2_api": "tools.r_bridge.run_r -> r/scripts/sc3_deseq2.R",
        "deseq2_group_count": len(group_contract),
        "private_r_retention": True,
        "private_verified_inputs_sha256": private_hashes,
        "input_sha256": {
            **hashes,
            "provenance_manifest": _input_sha256(provenance),
            "release_record": _input_sha256(release_record),
        },
        "outputs_sha256": {path.name: _input_sha256(path) for path in outputs},
        "patient_identifiers_written": False,
        "patient_identifiers_written_scope": "public outputs only; private verified inputs may contain identities",
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest_output, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    (output / "manifest.json").chmod(0o600)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.sc.sc3_cli")
    parser.add_argument("--clinical", required=True, help="SC-3 clinical input TSV")
    parser.add_argument("--expression", required=True, help="SC-3 expression UMI-sum TSV")
    parser.add_argument("--provenance", required=True, help="Hash-matched SC-3 input manifest")
    parser.add_argument("--output-dir", required=True, help="New SC-3 result directory")
    parser.add_argument("--release-record", help="approved scoped user-release record for a future source-derived run")
    parser.add_argument(
        "--allow-outcomes", action="store_true", default=False,
        help="explicit opt-in; still requires a release record bound to exact inputs and a decision hash",
    )
    parser.add_argument(
        "--stratum", default="per_cancer",
        choices=("per_cancer", "per_drug_class", "across_cancers", "melanoma_cancer_drug"),
    )
    args = parser.parse_args(argv)
    try:
        if args.allow_outcomes or args.release_record:
            output = run_released(
                args.clinical,
                args.expression,
                args.provenance,
                args.output_dir,
                stratum=args.stratum,
                allow_outcomes=args.allow_outcomes,
                release_record_path=args.release_record,
            )
        else:
            output = run_synthetic(
                args.clinical, args.expression, args.provenance, args.output_dir, stratum=args.stratum,
            )
    except (OSError, PermissionError, ValueError) as error:
        parser.exit(2, f"SC-3 analysis refused: {error}\n")
    run_kind = "source-derived" if args.allow_outcomes or args.release_record else "invented-data"
    print(f"SC-3 {run_kind} analysis written to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
