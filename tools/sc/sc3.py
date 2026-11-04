"""Synthetic-tested patient-level exploratory single-cell response contrasts."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import pandas as pd


@dataclass(frozen=True)
class SC3Group:
    cohort: str
    compartment: str
    endpoint_family: str
    profile_ids: tuple[str, ...]
    n_r: int
    n_nr: int


SC_ENDPOINT_MAPPINGS = {
    "RECIST": ("orr", "ORR"),
    "pathology": ("source_label", "SOURCE_LABEL_UNSPECIFIED"),
    "expansion": ("source_label", "SOURCE_LABEL_UNSPECIFIED"),
}


def metric_family(metric: str | None) -> str | None:
    value = str(metric or "").strip().casefold().replace("_", " ")
    if value in {"t cell expansion", "t-cell expansion", "expansion"}:
        return "expansion"
    if value in {"recist", "objective response", "orr"}:
        return "RECIST"
    if value.startswith("pathology") or ("pathology" in value and "recist" in value):
        return "pathology"
    return None


def outcome_fields(metric: str | None, label: str | None) -> dict[str, str | None]:
    family = metric_family(metric)
    value = str(label or "").strip().upper()
    outcome = value if value in {"R", "NR"} else None
    return {
        "endpoint_family": family,
        "response": outcome if family != "expansion" else None,
        "outcome_label": outcome,
    }


def guard_sc3(
    *,
    is_synthetic: bool,
    allow_outcomes: bool,
    clinical: pd.DataFrame | None = None,
    provenance_manifest: Path | str | None = None,
) -> None:
    if is_synthetic:
        if clinical is None:
            raise PermissionError("Synthetic SC-3 requires clinical profiles and a verified provenance manifest")
        authorize_sc3(clinical, provenance_manifest=provenance_manifest)
    elif not allow_outcomes:
        raise PermissionError("SC-3 on real atlas data requires --allow-outcomes")


def _sc3_payload(clinical: pd.DataFrame) -> dict:
    frame = clinical.copy().astype(object)
    frame = frame.where(pd.notna(frame), None)
    return {"profiles": frame.to_dict(orient="records")}


def write_sc3_synthetic_manifest(clinical: pd.DataFrame, path: Path | str) -> dict:
    """Authenticate a synthetic clinical fixture using the A-META fixture format."""
    from tools.a_meta.provenance import write_synthetic_fixture_manifest

    cohorts = sorted(set(clinical.get("cohort", pd.Series(dtype=str)).astype(str)))
    return write_synthetic_fixture_manifest(
        path,
        kind="sc3_input",
        payload=_sc3_payload(clinical),
        cohort_ids=cohorts,
    )


def write_sc3_r_synthetic_manifest(
    counts_path: Path | str,
    clinical_path: Path | str,
    path: Path | str,
) -> dict:
    """Write verified synthetic input provenance for the direct R analysis entry point."""
    from tools.a_meta.provenance import write_synthetic_fixture_manifest

    counts_path, clinical_path = Path(counts_path), Path(clinical_path)
    clinical = pd.read_csv(clinical_path, sep="\t", dtype=str, keep_default_na=False)
    cohorts = sorted(set(clinical["cohort"].astype(str)))
    input_hashes = {
        "counts": hashlib.sha256(counts_path.read_bytes()).hexdigest(),
        "clinical": hashlib.sha256(clinical_path.read_bytes()).hexdigest(),
    }
    payload = (
        f"counts:{input_hashes['counts']}\nclinical:{input_hashes['clinical']}\n"
        f"cohorts:{','.join(cohorts)}\n"
    )
    return write_synthetic_fixture_manifest(
        path,
        kind="sc3_r_input",
        payload_sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        cohort_ids=cohorts,
    )


def _real_sc_cohorts() -> set[str]:
    cohort_map = Path(__file__).with_name("lin_cohort_map.tsv")
    frame = pd.read_csv(cohort_map, sep="\t", dtype=str)
    return set(frame["cohort"].astype(str)) | {"prostate_hormone_naive_atlas"}


def authorize_sc3(
    clinical: pd.DataFrame,
    *,
    allow_outcomes: bool = False,
    provenance_manifest: Path | str | None = None,
) -> None:
    """Fail closed unless the caller explicitly authorizes outcomes or proves fixture input."""
    from tools.a_meta.provenance import (
        SYNTHETIC_FIXTURE_PRODUCER,
        canonical_sha256,
        is_locked_study,
        known_cohort_ids,
    )

    cohorts = set(clinical.get("cohort", pd.Series(dtype=str)).dropna().astype(str))
    if any(is_locked_study(cohort) for cohort in cohorts):
        raise PermissionError("SC-3 refuses the locked IMvigor210 final test")
    real_ids = cohorts & (_real_sc_cohorts() | known_cohort_ids())
    if real_ids:
        if not allow_outcomes:
            raise PermissionError("SC-3 on real atlas outcomes requires explicit allow_outcomes=True")
        return
    if allow_outcomes:
        return
    if provenance_manifest is None:
        raise PermissionError("SC-3 requires explicit real-outcome authorization or a verified synthetic manifest")
    try:
        manifest = json.loads(Path(provenance_manifest).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PermissionError("SC-3 synthetic provenance is missing or malformed") from error
    expected_cohorts = {cohort for cohort in cohorts if cohort}
    if (
        manifest.get("manifest_version") != 1
        or manifest.get("producer") != SYNTHETIC_FIXTURE_PRODUCER
        or manifest.get("data_classification") != "synthetic"
        or manifest.get("kind") != "sc3_input"
        or set(map(str, manifest.get("cohort_ids", ()))) != expected_cohorts
        or manifest.get("payload_sha256") != canonical_sha256(_sc3_payload(clinical))
        or expected_cohorts & (known_cohort_ids() | _real_sc_cohorts())
    ):
        raise PermissionError("SC-3 synthetic manifest does not match the supplied clinical profiles")


def _truthy(values: pd.Series) -> pd.Series:
    if values.dtype == bool:
        return values
    return values.astype(str).str.strip().str.casefold().isin({"true", "1", "yes"})


def group_profiles(
    clinical: pd.DataFrame,
    *,
    allow_outcomes: bool = False,
    provenance_manifest: Path | str | None = None,
) -> tuple[dict[tuple[str, str, str], SC3Group], list[dict]]:
    """Group validated patient profiles without mixing outcome metric families."""
    authorize_sc3(
        clinical,
        allow_outcomes=allow_outcomes,
        provenance_manifest=provenance_manifest,
    )
    required = {"cohort", "profile_id", "patient_id", "sample_id", "compartment", "outcome_label", "eligible"}
    if "endpoint_family" not in clinical and "response_metric" not in clinical:
        required.add("endpoint_family")
    missing = required - set(clinical.columns)
    if missing:
        raise ValueError(f"Clinical profiles are missing fields: {sorted(missing)}")
    frame = clinical.copy()
    for column in ("cohort", "profile_id", "patient_id", "sample_id", "compartment"):
        frame[column] = frame[column].astype("string").fillna("").str.strip()
    if frame[["profile_id", "patient_id", "sample_id", "cohort", "compartment"]].eq("").any().any():
        raise ValueError("SC-3 profiles require non-empty patient, specimen, cohort, and profile identities")
    if frame["profile_id"].duplicated().any():
        raise ValueError("SC-3 profile IDs must be unique")
    sample_counts = frame.groupby(["cohort", "patient_id"], dropna=False)["sample_id"].nunique()
    if (sample_counts > 1).any():
        raise ValueError("Each SC-3 patient must have one baseline specimen per cohort")

    if "response_metric" in frame:
        mapped = frame["response_metric"].map(metric_family)
        if "endpoint_family" in frame:
            declared = frame["endpoint_family"].map(metric_family)
            conflict = mapped.notna() & declared.notna() & mapped.ne(declared)
            if conflict.any():
                raise ValueError("SC-3 response metric and endpoint family disagree")
        frame["endpoint_family"] = mapped.fillna(frame.get("endpoint_family", pd.Series(index=frame.index, dtype=object)).map(metric_family))
    else:
        frame["endpoint_family"] = frame["endpoint_family"].map(metric_family)
    if "response" in frame:
        expansion_rows = frame["endpoint_family"].eq("expansion")
        clinical_response = frame["response"].astype("string").fillna("").str.strip().str.upper()
        if (expansion_rows & clinical_response.isin({"R", "NR"})).any():
            raise ValueError("T-cell expansion labels cannot be stored as clinical response")
    frame["eligible"] = _truthy(frame["eligible"])

    groups: dict[tuple[str, str, str], SC3Group] = {}
    refusals: list[dict] = []
    dimensions = ["cohort", "compartment", "endpoint_family"]
    for key, complete_frame in frame.groupby(dimensions, dropna=False, sort=True):
        cohort, compartment, family = map(str, key)
        if family in {"", "nan", "None"}:
            refusals.append({"cohort": cohort, "compartment": compartment, "endpoint_family": "unusable",
                             "n_R": 0, "n_NR": 0, "reason": "unusable_response_metric"})
            continue
        if complete_frame["patient_id"].duplicated().any():
            raise ValueError("SC-3 requires one pseudobulk profile per patient and compartment/metric")
        valid = complete_frame[
            complete_frame["eligible"] & complete_frame["outcome_label"].isin(["R", "NR"])
        ].copy()
        n_r = int(valid.loc[valid["outcome_label"].eq("R"), "patient_id"].nunique())
        n_nr = int(valid.loc[valid["outcome_label"].eq("NR"), "patient_id"].nunique())
        if n_r < 3 or n_nr < 3:
            refusals.append({"cohort": cohort, "compartment": compartment, "endpoint_family": family,
                             "n_R": n_r, "n_NR": n_nr, "reason": "fewer_than_three_patients_per_arm"})
            continue
        groups[(cohort, compartment, family)] = SC3Group(
            cohort=cohort,
            compartment=compartment,
            endpoint_family=family,
            profile_ids=tuple(valid["profile_id"].astype(str)),
            n_r=n_r,
            n_nr=n_nr,
        )
    return groups, refusals


def validated_group_manifest(
    clinical: pd.DataFrame,
    groups: Mapping,
    *,
    allow_outcomes: bool = False,
    provenance_manifest: Path | str | None = None,
) -> list[dict]:
    import hashlib

    authorize_sc3(clinical, allow_outcomes=allow_outcomes, provenance_manifest=provenance_manifest)
    by_profile = clinical.set_index(clinical["profile_id"].astype(str), drop=False)
    result = []
    for group_id, group in enumerate(groups.values(), start=1):
        profiles = list(group.profile_ids)
        frame = by_profile.loc[profiles]
        profile_hash = hashlib.sha256("\n".join(sorted(profiles)).encode("utf-8")).hexdigest()
        result.append({
            "group_id": f"sc3_group_{group_id}",
            "cohort": group.cohort,
            "compartment": group.compartment,
            "endpoint_family": group.endpoint_family,
            "n_R": group.n_r,
            "n_NR": group.n_nr,
            "profile_ids_sha256": profile_hash,
            "profile_count": len(profiles),
        })
    return result


def _drug_class(treatment: str) -> str:
    from tools.a_cohorts.view import normalise_drug_class

    value = re.sub(r"\baPD\s*-?1\b", "anti-PD1", str(treatment), flags=re.IGNORECASE)
    value = re.sub(r"\baPD\s*-?L1\b", "anti-PD-L1", value, flags=re.IGNORECASE)
    value = re.sub(r"\baCTLA\s*-?4\b", "anti-CTLA4", value, flags=re.IGNORECASE)
    value = re.sub(r"(?<!anti-)\bCTLA\s*-?4\b", "anti-CTLA4", value, flags=re.IGNORECASE)
    try:
        return str(normalise_drug_class(value))
    except ValueError:
        return "UNMAPPED"


def _sc3_effects(
    clinical: pd.DataFrame,
    expression: pd.DataFrame,
    *,
    allow_outcomes: bool = False,
    provenance_manifest: Path | str | None = None,
) -> pd.DataFrame:
    from types import SimpleNamespace

    from tools.a_meta.effects import EFFECT_COLUMNS, _effect_row
    from tools.a_cohorts.view import normalise_drug_class
    from .core import panel_definitions

    groups, _ = group_profiles(
        clinical,
        allow_outcomes=allow_outcomes,
        provenance_manifest=provenance_manifest,
    )
    definitions = panel_definitions()
    panel_ids = (
        "P_ANTIGEN_PRESENTATION", "AYERS_GEP_18", "HOPE_18", "M0_EXTRA_ANTIGEN_PRESENTATION",
        "M1_MOBILITY", "M2_CYTOTOXICITY", "M3_VIRAL_MIMICRY", "M4_EXCLUSION",
        "CYT_FROZEN_UNOFFSET", "CYT_ROONEY_OFFSET_REFERENCE", "APM_WANG_18",
    )
    extras = ("compartment", "sc_endpoint_family", "response_metric")
    records: list[dict] = []
    clinical_index = clinical.copy()
    clinical_index["profile_id"] = clinical_index["profile_id"].astype(str)
    by_profile = clinical_index.set_index("profile_id", drop=False)

    for group in groups.values():
        ids = list(group.profile_ids)
        frame = by_profile.loc[ids].copy().reset_index(drop=True)
        if not set(ids).issubset(expression.columns):
            raise ValueError("SC-3 expression columns do not cover the validated patient groups")
        raw = expression.loc[:, ids]
        library_sizes = pd.to_numeric(frame["library_size"], errors="coerce")
        if library_sizes.isna().any() or (library_sizes <= 0).any():
            raise ValueError("SC-3 profiles require positive full-library sizes")
        normalized = np_log2_plus1(raw.divide(library_sizes.to_numpy(), axis=1) * 1_000_000.0)
        labels = [1 if value == "R" else 0 if value == "NR" else None for value in frame["outcome_label"]]
        treatment_col = "treatment" if "treatment" in frame else "drug_class"
        frame["_sc3_drug_class"] = frame[treatment_col].astype(str).map(_drug_class)
        valid_classes = {"ANTI_PD_L1_AXIS", "ANTI_CTLA4", "DUAL_PD1_CTLA4"}
        included = [index for index, value in enumerate(frame["_sc3_drug_class"]) if value in valid_classes]
        strata = [("ALL", included)]
        strata.extend(
            (drug_class, [index for index in included if frame.loc[index, "_sc3_drug_class"] == drug_class])
            for drug_class in sorted({frame.loc[index, "_sc3_drug_class"] for index in included})
        )
        cancers = sorted(set(frame.get("cancer", pd.Series("unknown", index=frame.index)).astype(str)))
        cancer = cancers[0] if len(cancers) == 1 else "multi"
        metric_values = sorted(set(frame.get("response_metric", pd.Series(group.endpoint_family, index=frame.index)).astype(str)))
        metric_label = ",".join(metric_values)
        endpoint_family, endpoint_definition_id = SC_ENDPOINT_MAPPINGS[group.endpoint_family]
        view = SimpleNamespace(metadata=SimpleNamespace(cohort_id=group.cohort))
        clinical_rows = [
            {"patient_id": str(row.patient_id), "sample_id": str(row.sample_id)}
            for row in frame.itertuples(index=False)
        ]

        def add_effect(unit_family, unit, values, *, coverage=None):
            for stratum, indices in strata:
                row = _effect_row(
                    view=view,
                    unit_family=unit_family,
                    unit=f"sc3::{group.compartment}::{group.endpoint_family}::{unit}",
                    cancer=cancer,
                    stratum=stratum,
                    endpoint_family=endpoint_family,
                    endpoint_definition_id=endpoint_definition_id,
                    labels=labels,
                    values=values,
                    patient_indices=indices,
                    excluded={},
                    coverage=coverage,
                    clinical_rows=clinical_rows,
                    cancer_components=cancers,
                )
                row.update({
                    "compartment": group.compartment,
                    "sc_endpoint_family": group.endpoint_family,
                    "response_metric": metric_label,
                })
                records.append(row)

        for panel_id in panel_ids:
            members = definitions[panel_id]
            present = [gene for gene in members if gene in normalized.index]
            coverage_complete = bool(members) and len(present) / len(members) >= 0.8
            values = [None] * len(ids)
            if coverage_complete:
                for index, profile_id in enumerate(ids):
                    measured = normalized.loc[present, profile_id].dropna()
                    if len(measured) >= 0.8 * len(members):
                        values[index] = float(measured.mean())
            add_effect("panel", panel_id, values, coverage={"complete": coverage_complete})

        for panel_id in ("M5_CHECKPOINT_CANDIDATES", "M6_EPIGENETIC_REGULATORS"):
            for gene in definitions[panel_id]:
                values = [
                    float(normalized.at[gene, profile_id]) if gene in normalized.index and pd.notna(normalized.at[gene, profile_id]) else None
                    for profile_id in ids
                ]
                add_effect("gene", gene, values)

        if "fraction_cells_total" in frame:
            values = [
                float(value) if pd.notna(value) else None
                for value in pd.to_numeric(frame["fraction_cells_total"], errors="coerce")
            ]
            add_effect("fraction", "compartment_fraction", values)

    columns = [*EFFECT_COLUMNS, *extras]
    return pd.DataFrame.from_records(records, columns=columns)


def np_log2_plus1(frame: pd.DataFrame) -> pd.DataFrame:
    import numpy as np

    return np.log2(frame + 1.0)
