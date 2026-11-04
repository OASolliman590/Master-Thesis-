"""Synthetic-tested patient-level exploratory single-cell response contrasts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SC3Group:
    cohort: str
    compartment: str
    endpoint_family: str
    profile_ids: tuple[str, ...]
    n_r: int
    n_nr: int


def metric_family(metric: str | None) -> str | None:
    value = str(metric or "").strip().casefold().replace("_", " ")
    if value == "t cell expansion" or value == "t-cell expansion":
        return "expansion"
    if value in {"recist", "objective response", "orr"}:
        return "RECIST"
    if value.startswith("pathology"):
        return "pathology"
    if "pathology" in value and "recist" in value:
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


def guard_sc3(*, is_synthetic: bool, allow_outcomes: bool) -> None:
    if not is_synthetic and not allow_outcomes:
        raise PermissionError("SC-3 on real atlas data requires --allow-outcomes")


def group_profiles(clinical: pd.DataFrame) -> tuple[dict[tuple[str, str, str], SC3Group], list[dict]]:
    """Group eligible pseudobulk profiles without mixing response metric families."""
    required = {"cohort", "profile_id", "patient_id", "compartment", "endpoint_family", "outcome_label", "eligible"}
    missing = required - set(clinical.columns)
    if missing:
        raise ValueError(f"Clinical profiles are missing fields: {sorted(missing)}")
    if clinical["profile_id"].astype(str).duplicated().any():
        raise ValueError("SC-3 profile IDs must be unique")
    groups: dict[tuple[str, str, str], SC3Group] = {}
    refusals: list[dict] = []
    dimensions = ["cohort", "compartment", "endpoint_family"]
    for key, frame in clinical.groupby(dimensions, dropna=False, sort=True):
        cohort, compartment, family = map(str, key)
        if family in {"", "nan", "None"}:
            refusals.append(
                {"cohort": cohort, "compartment": compartment, "endpoint_family": "unusable", "n_R": 0, "n_NR": 0, "reason": "unusable_response_metric"}
            )
            continue
        valid = frame[frame["eligible"].astype(bool)].copy()
        valid = valid[valid["outcome_label"].isin(["R", "NR"]) & valid["endpoint_family"].notna()]
        if valid["patient_id"].astype(str).duplicated().any():
            refusals.append(
                {"cohort": cohort, "compartment": compartment, "endpoint_family": family,
                 "n_R": int(valid.loc[valid["outcome_label"].eq("R"), "patient_id"].nunique()),
                 "n_NR": int(valid.loc[valid["outcome_label"].eq("NR"), "patient_id"].nunique()),
                 "reason": "multiple_pseudobulk_profiles_per_patient"}
            )
            continue
        n_r = int((valid["outcome_label"] == "R").sum())
        n_nr = int((valid["outcome_label"] == "NR").sum())
        if n_r < 3 or n_nr < 3:
            refusals.append(
                {"cohort": cohort, "compartment": compartment, "endpoint_family": family, "n_R": n_r, "n_NR": n_nr, "reason": "fewer_than_three_patients_per_arm"}
            )
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


def hedges_g(values_r: Iterable[float], values_nr: Iterable[float]) -> dict[str, float | int]:
    r = np.asarray(tuple(values_r), dtype=float)
    nr = np.asarray(tuple(values_nr), dtype=float)
    if r.size < 2 or nr.size < 2 or not np.isfinite(r).all() or not np.isfinite(nr).all():
        raise ValueError("Hedges g requires at least two finite patient values per arm")
    mean_r = float(r.mean())
    mean_nr = float(nr.mean())
    df = r.size + nr.size - 2
    pooled_variance = ((r.size - 1) * r.var(ddof=1) + (nr.size - 1) * nr.var(ddof=1)) / df
    if pooled_variance <= 0:
        return {
            "n_R": int(r.size), "n_NR": int(nr.size), "mean_R": mean_r, "mean_NR": mean_nr,
            "sd_R": float(r.std(ddof=1)), "sd_NR": float(nr.std(ddof=1)), "g": np.nan, "se": np.nan,
        }
    correction = 1.0 - 3.0 / (4.0 * df - 1.0)
    g = correction * (mean_r - mean_nr) / np.sqrt(pooled_variance)
    se = np.sqrt((r.size + nr.size) / (r.size * nr.size) + g * g / (2.0 * df))
    return {
        "n_R": int(r.size), "n_NR": int(nr.size), "mean_R": mean_r, "mean_NR": mean_nr,
        "sd_R": float(r.std(ddof=1)), "sd_NR": float(nr.std(ddof=1)), "g": float(g), "se": float(se),
    }
