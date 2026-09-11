"""Deterministic W5 adapter from fold-local feature rows to B-P1 matrices."""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from tools.b_workflow.io import PipelineFailure


def _fail(message: str, code: int = 3) -> None:
    raise PipelineFailure(f"stage=W5 {message}", code, "W5")


def gleason_dummies(category: str, encoding: dict[str, Any]) -> dict[str, int]:
    reference = encoding["reference"]
    mapping = encoding["dummies"]
    out = {name: 0 for name in mapping.values()}
    if category == reference:
        return out
    if category not in mapping:
        _fail(f"reason=unknown-gleason-category {category}")
    out[mapping[category]] = 1
    if sum(out.values()) > 1:
        _fail("reason=non-exclusive-gleason-dummies")
    return out


def ordered_feature_columns(w5: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    continuous = list(w5["continuous_baseline_columns"])
    categorical = [col for group in w5["categorical_baseline_groups"] for col in group]
    extended = list(w5["extended_columns"])
    all_cols = continuous + categorical + extended
    if len(set(all_cols)) != len(all_cols):
        _fail("reason=duplicate-predictor-columns")
    return continuous, categorical, extended


def promoter_column(gene: str) -> str:
    return f"promoter_{gene}"


def encode_eligible_rows(
    rows: Sequence[dict[str, Any]],
    *,
    covariates: dict[str, dict[str, str]],
    w5: dict[str, Any],
    program: Sequence[str],
) -> tuple[list[str], np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return UTF-8-sorted patient ids and Y / continuous / dummy / extended matrices."""
    continuous_cols, categorical_cols, extended_cols = ordered_feature_columns(w5)
    expected_promoters = [promoter_column(gene) for gene in program]
    if extended_cols != expected_promoters:
        _fail("reason=extended-columns-must-match-program-order")
    encoding = w5["gleason_encoding"]
    source_field = encoding["source_field"]
    eligible = [row for row in rows if row.get("eligible") is True]
    eligible = sorted(eligible, key=lambda row: str(row["patient_id"]).encode("utf-8"))
    ids: list[str] = []
    y_vals: list[float] = []
    cont_rows: list[list[float]] = []
    dummy_rows: list[list[float]] = []
    ext_rows: list[list[float]] = []
    for row in eligible:
        pid = row["patient_id"]
        if row.get("Y") is None:
            _fail(f"reason=eligible-row-missing-Y patient_id={pid}")
        cov = covariates.get(pid) or {}
        dummies = gleason_dummies(cov.get(source_field, ""), encoding)
        cont: list[float] = []
        for col in continuous_cols:
            value = row.get(col)
            if value is None:
                _fail(f"reason=missing-continuous {col} patient_id={pid}")
            cont.append(float(value))
        dummy = [float(dummies[col]) for col in categorical_cols]
        ext: list[float] = []
        for gene, col in zip(program, extended_cols):
            value = row.get("promoter", {}).get(gene)
            if value is None:
                _fail(f"reason=missing-promoter {col} patient_id={pid}")
            ext.append(float(value))
        ids.append(pid)
        y_vals.append(float(row["Y"]))
        cont_rows.append(cont)
        dummy_rows.append(dummy)
        ext_rows.append(ext)
    y = np.asarray(y_vals, dtype=np.float64)
    continuous = np.asarray(cont_rows, dtype=np.float64) if cont_rows else np.empty((0, len(continuous_cols)), dtype=np.float64)
    dummy = np.asarray(dummy_rows, dtype=np.float64) if dummy_rows else np.empty((0, len(categorical_cols)), dtype=np.float64)
    extended = np.asarray(ext_rows, dtype=np.float64) if ext_rows else np.empty((0, len(extended_cols)), dtype=np.float64)
    return ids, y, continuous, dummy, extended
