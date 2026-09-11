"""B-P1 prediction engine CLI."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


SCHEMA_VERSION = "B-P1-contract-1"
LOCK_SCHEMA_VERSION = "B-P1-evaluation-lock-1"
RELEASED_ALPHA_GRID = [0.0001, 0.001, 0.01, 0.1, 1, 10, 100, 1000, 10000]
RELEASED_BOOTSTRAP = {
    "resamples": 2000,
    "random_state": 42,
    "bit_generator": "PCG64",
    "quantiles": [0.025, 0.975],
    "quantile_method": "linear",
}
EXIT_ARGUMENT = 2
EXIT_SCHEMA = 3
EXIT_NUMERIC = 4
EXIT_OUTPUT = 5
SCIENTIFIC_LOCK_FIELDS = (
    "status",
    "decision_commit",
    "reviewer_receipt",
    "eligibility_hash",
    "u_hash",
    "q_hashes",
    "feature_contract_hash",
    "external_population_contract_hash",
    "precision_contract_id",
    "environment_lock",
)
ENVIRONMENT_LOCK_FIELDS = (
    "python_version",
    "numpy_version",
    "scipy_version",
    "scikit_learn_version",
    "threadpoolctl_version",
)
SCIENTIFIC_EVALUATION_LOCK_FIELDS = (
    "schema_version",
    "status",
    "contract_sha256",
    "bundle_sha256",
    "external_sha256",
    "decision_commit",
    "reviewer_receipt",
    "eligibility_hash",
    "external_population_contract_hash",
    "precision_contract_id",
)
SYNTHETIC_EVALUATION_LOCK_FIELDS = (
    "schema_version",
    "status",
    "contract_sha256",
    "bundle_sha256",
    "external_sha256",
)
HASH_LOCK_FIELDS = {
    "eligibility_hash",
    "u_hash",
    "feature_contract_hash",
    "external_population_contract_hash",
}


class Failure(Exception):
    """Boundary-raised failure with explicit return code."""

    def __init__(self, message: str, code: int = EXIT_SCHEMA):
        super().__init__(message)
        self.code = code


def _canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _engine_code_sha256() -> str:
    try:
        return _sha256(Path(__file__).read_bytes())
    except OSError as exc:
        raise Failure("cannot hash prediction engine source", EXIT_SCHEMA) from exc


def _set_thread_limits() -> None:
    for key in [
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
    ]:
        os.environ[key] = "1"


def _runtime_receipt() -> dict[str, Any]:
    import importlib.metadata

    def _version(name: str) -> str:
        try:
            return importlib.metadata.version(name)
        except Exception:
            return "missing"

    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "numpy_version": np.__version__,
        "thread_settings": {
            "OMP_NUM_THREADS": os.getenv("OMP_NUM_THREADS"),
            "OPENBLAS_NUM_THREADS": os.getenv("OPENBLAS_NUM_THREADS"),
            "MKL_NUM_THREADS": os.getenv("MKL_NUM_THREADS"),
        },
        "packages": {
            "threadpoolctl": _version("threadpoolctl"),
            "scipy": _version("scipy"),
            "scikit_learn": _version("scikit-learn"),
        },
    }


def _json_no_dups(raw: bytes) -> dict[str, Any]:
    def dedupe(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in pairs:
            if key in out:
                raise Failure(f"schema reason=duplicate-json-key {key}", EXIT_SCHEMA)
            out[key] = value
        return out

    return json.loads(raw.decode("utf-8"), object_pairs_hook=dedupe)


def _atomic_write_bytes(path: Path, payload: bytes, *, code: int = EXIT_OUTPUT) -> None:
    out_dir = path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".b_prediction_", suffix=".tmp", dir=str(out_dir))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.replace(tmp_name, path)
        except OSError as exc:
            raise Failure(f"output path write failed: {path}", code) from exc
    finally:
        if os.path.exists(tmp_name):
            try:
                os.unlink(tmp_name)
            except OSError:
                pass


def _atomic_write_json(path: Path, payload: Any, *, code: int = EXIT_OUTPUT) -> None:
    _atomic_write_bytes(path, _canonical_json_bytes(payload), code=code)


def _atomic_write_tsv(path: Path, rows: list[list[str]], headers: list[str], *, code: int = EXIT_OUTPUT) -> None:
    lines = ["\t".join(headers)]
    lines.extend("\t".join(row) for row in rows)
    text = "\n".join(lines) + "\n"
    _atomic_write_bytes(path, text.encode("utf-8"), code=code)


def _ensure_new_output(path: Path, *, code: int = EXIT_OUTPUT) -> None:
    if path.exists():
        raise Failure(f"output path must not already exist: {path}", code)


def _load_bytes(path: Path) -> bytes:
    if path.suffix.lower() in {".gz", ".gzip", ".bgz"}:
        raise Failure(f"input path {path} reason=compressed input rejected", EXIT_ARGUMENT)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise Failure(f"I/O failure reading {path}", EXIT_SCHEMA) from exc
    if raw.startswith(b"\x1f\x8b\x08\x00"):
        raise Failure(f"input path {path} reason=gzip bytes detected", EXIT_ARGUMENT)
    return raw


def _validate_hash(expected: str, actual: str, field: str) -> None:
    if expected.lower() != actual.lower():
        raise Failure(
            f"{field} reason=hash mismatch supplied={expected.lower()} actual={actual}",
            EXIT_SCHEMA,
        )


def _parse_float(token: str, *, row: int, field: str) -> float:
    try:
        value = float(token)
    except ValueError as exc:
        raise Failure(f"row={row} field={field} reason=non-finite numeric token", EXIT_SCHEMA) from exc
    if not math.isfinite(value):
        raise Failure(f"row={row} field={field} reason=non-finite numeric token", EXIT_SCHEMA)
    return value


def _parse_binary(token: str, *, row: int, field: str) -> int:
    if token not in {"0", "1"}:
        raise Failure(f"row={row} field={field} reason=dummy-not-binary", EXIT_SCHEMA)
    return 1 if token == "1" else 0


@dataclass(frozen=True)
class Contract:
    path: Path
    payload: dict[str, Any]
    raw_bytes: bytes
    raw_sha256: str
    purpose: str
    development_cohort: str
    external_cohort: str
    patient_id_column: str
    target_column: str
    continuous_baseline_columns: list[str]
    categorical_baseline_groups: list[list[str]]
    extended_columns: list[str]
    alpha_grid: list[float]
    outer_cv: dict[str, Any]
    inner_cv: dict[str, Any]
    final_cv: dict[str, Any]
    bootstrap: dict[str, Any]
    model: dict[str, Any]
    scientific_lock: dict[str, Any]
    development_sha256: str


def _require_nonempty_str(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise Failure(f"contract-json reason=scientific-lock-bad-{field}", EXIT_SCHEMA)
    return value


def _require_hex_hash(value: Any, field: str) -> str:
    text = _require_nonempty_str(value, field)
    if len(text) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in text):
        raise Failure(f"contract-json reason=scientific-lock-bad-{field}", EXIT_SCHEMA)
    return text


def _validate_environment_lock(lock: Any) -> dict[str, str]:
    if not isinstance(lock, dict) or set(lock.keys()) != set(ENVIRONMENT_LOCK_FIELDS):
        raise Failure("contract-json reason=scientific-lock-environment", EXIT_SCHEMA)
    return {key: _require_nonempty_str(lock[key], f"environment_lock.{key}") for key in ENVIRONMENT_LOCK_FIELDS}


def _validate_q_hashes(value: Any) -> dict[str, str]:
    if not isinstance(value, dict) or not value:
        raise Failure("contract-json reason=scientific-lock-bad-q_hashes", EXIT_SCHEMA)
    out: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key:
            raise Failure("contract-json reason=scientific-lock-bad-q_hashes", EXIT_SCHEMA)
        out[key] = _require_hex_hash(item, f"q_hashes.{key}")
    return out


def _validate_scientific_contract_lock(lock: dict[str, Any]) -> None:
    if set(lock.keys()) != set(SCIENTIFIC_LOCK_FIELDS) or lock.get("status") != "approved":
        raise Failure("contract-json reason=scientific-lock", EXIT_SCHEMA)
    _require_nonempty_str(lock["decision_commit"], "decision_commit")
    _require_nonempty_str(lock["reviewer_receipt"], "reviewer_receipt")
    _require_nonempty_str(lock["precision_contract_id"], "precision_contract_id")
    for field in HASH_LOCK_FIELDS:
        _require_hex_hash(lock[field], field)
    _validate_q_hashes(lock["q_hashes"])
    _validate_environment_lock(lock["environment_lock"])


def _imported_environment() -> dict[str, str]:
    receipt = _runtime_receipt()
    return {
        "python_version": receipt["python_version"],
        "numpy_version": receipt["numpy_version"],
        "scipy_version": str(receipt["packages"]["scipy"]),
        "scikit_learn_version": str(receipt["packages"]["scikit_learn"]),
        "threadpoolctl_version": str(receipt["packages"]["threadpoolctl"]),
    }


def _enforce_scientific_environment(lock: dict[str, Any]) -> None:
    expected = _validate_environment_lock(lock["environment_lock"])
    actual = _imported_environment()
    if actual != expected:
        raise Failure("scientific-run environment lock mismatch", EXIT_SCHEMA)


def _validate_contract_fields(payload: dict[str, Any]) -> None:
    required_top = {
        "schema_version",
        "purpose",
        "development_cohort",
        "external_cohort",
        "patient_id_column",
        "target_column",
        "continuous_baseline_columns",
        "categorical_baseline_groups",
        "extended_columns",
        "alpha_grid",
        "outer_cv",
        "inner_cv",
        "final_cv",
        "bootstrap",
        "model",
        "development_sha256",
        "scientific_lock",
    }
    if set(payload.keys()) != required_top:
        missing = required_top - set(payload.keys())
        unknown = set(payload.keys()) - required_top
        if missing:
            raise Failure(f"contract-json reason=missing-field {sorted(missing)[0]}", EXIT_SCHEMA)
        raise Failure(f"contract-json reason=unknown-field {sorted(unknown)[0]}", EXIT_SCHEMA)

    if payload["schema_version"] != SCHEMA_VERSION:
        raise Failure("contract-json reason=bad-schema", EXIT_ARGUMENT)

    if payload["purpose"] not in {"synthetic-test", "scientific-run"}:
        raise Failure("contract-json reason=bad-purpose", EXIT_ARGUMENT)

    if payload["development_cohort"] == payload["external_cohort"]:
        raise Failure("contract-json reason=cohorts-must-differ", EXIT_SCHEMA)

    for key in ("patient_id_column", "target_column", "development_cohort", "external_cohort"):
        if not isinstance(payload[key], str) or not payload[key]:
            raise Failure(f"contract-json reason=bad-{key}", EXIT_SCHEMA)

    continuous = payload["continuous_baseline_columns"]
    groups = payload["categorical_baseline_groups"]
    extended = payload["extended_columns"]
    if not isinstance(continuous, list) or not all(isinstance(v, str) for v in continuous):
        raise Failure("contract-json reason=bad-continuous-baseline-columns", EXIT_SCHEMA)
    if not isinstance(groups, list) or not all(isinstance(g, list) and g and all(isinstance(v, str) for v in g) for g in groups):
        raise Failure("contract-json reason=bad-categorical-baseline-groups", EXIT_SCHEMA)
    if not isinstance(extended, list) or not all(isinstance(v, str) for v in extended):
        raise Failure("contract-json reason=bad-extended-columns", EXIT_SCHEMA)

    all_predictor_cols = continuous + [c for g in groups for c in g] + extended
    if len(set(all_predictor_cols)) != len(all_predictor_cols):
        raise Failure("contract-json reason=duplicate-predictor-columns", EXIT_SCHEMA)

    for g in groups:
        if len(set(g)) != len(g):
            raise Failure("contract-json reason=duplicate-group-column", EXIT_SCHEMA)

    alpha_grid = payload["alpha_grid"]
    if not isinstance(alpha_grid, list) or len(alpha_grid) != len(RELEASED_ALPHA_GRID) or any(
        abs(a - b) > 0 for a, b in zip(alpha_grid, RELEASED_ALPHA_GRID)
    ):
        raise Failure("contract-json reason=alpha-grid mismatch", EXIT_SCHEMA)
    for value in alpha_grid:
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise Failure("contract-json reason=alpha-grid mismatch", EXIT_SCHEMA)

    def _validate_cv(obj: Any, name: str) -> None:
        if not isinstance(obj, dict) or set(obj.keys()) != {"n_splits", "shuffle", "random_state"}:
            raise Failure(f"contract-json reason={name}-fields", EXIT_SCHEMA)
        if obj["n_splits"] != 5 or obj["shuffle"] is not True or obj["random_state"] != 42:
            raise Failure(f"contract-json reason={name}-mismatch", EXIT_SCHEMA)

    _validate_cv(payload["outer_cv"], "outer_cv")
    _validate_cv(payload["inner_cv"], "inner_cv")
    _validate_cv(payload["final_cv"], "final_cv")

    boot = payload["bootstrap"]
    if not isinstance(boot, dict):
        raise Failure("contract-json reason=bootstrap-fields", EXIT_SCHEMA)
    if set(boot.keys()) != set(RELEASED_BOOTSTRAP.keys()):
        raise Failure("contract-json reason=bootstrap-fields", EXIT_SCHEMA)
    if any(boot[k] != v for k, v in RELEASED_BOOTSTRAP.items()):
        raise Failure("contract-json reason=bootstrap-mismatch", EXIT_SCHEMA)

    model = payload["model"]
    if not isinstance(model, dict):
        raise Failure("contract-json reason=model-fields", EXIT_SCHEMA)
    expected_model_fields = {
        "type",
        "continuous_scaler",
        "fit_intercept",
        "solver",
        "tol",
        "copy_X",
        "positive",
        "max_iter",
    }
    if set(model.keys()) != expected_model_fields:
        raise Failure("contract-json reason=model-fields", EXIT_SCHEMA)
    if (
        model["type"] != "ridge"
        or model["continuous_scaler"] != "standard"
        or model["fit_intercept"] is not True
        or model["solver"] != "svd"
        or model["tol"] != 0.0001
        or model["copy_X"] is not True
        or model["positive"] is not False
        or model["max_iter"] is not None
    ):
        raise Failure("contract-json reason=model-fields", EXIT_SCHEMA)

    lock = payload["scientific_lock"]
    if not isinstance(lock, dict):
        raise Failure("contract-json reason=scientific-lock", EXIT_SCHEMA)
    if payload["purpose"] == "synthetic-test":
        if set(lock.keys()) != {"status"} or lock["status"] != "synthetic-only":
            raise Failure("contract-json reason=scientific-lock", EXIT_SCHEMA)
    else:
        _validate_scientific_contract_lock(lock)

    dev_sha = payload["development_sha256"]
    if not isinstance(dev_sha, str) or len(dev_sha) != 64:
        raise Failure("contract-json reason=development-sha256", EXIT_SCHEMA)


def _load_contract(path: Path) -> Contract:
    raw = _load_bytes(path)
    payload = _json_no_dups(raw)
    _validate_contract_fields(payload)
    return Contract(
        path=path,
        payload=payload,
        raw_bytes=raw,
        raw_sha256=_sha256(raw),
        purpose=payload["purpose"],
        development_cohort=payload["development_cohort"],
        external_cohort=payload["external_cohort"],
        patient_id_column=payload["patient_id_column"],
        target_column=payload["target_column"],
        continuous_baseline_columns=list(payload["continuous_baseline_columns"]),
        categorical_baseline_groups=[list(group) for group in payload["categorical_baseline_groups"]],
        extended_columns=list(payload["extended_columns"]),
        alpha_grid=[float(v) for v in payload["alpha_grid"]],
        outer_cv=dict(payload["outer_cv"]),
        inner_cv=dict(payload["inner_cv"]),
        final_cv=dict(payload["final_cv"]),
        bootstrap=dict(payload["bootstrap"]),
        model=dict(payload["model"]),
        scientific_lock=dict(payload["scientific_lock"]),
        development_sha256=payload["development_sha256"],
    )


@dataclass
class PatientTable:
    raw_bytes: bytes
    source_sha256: str
    patient_ids: list[str]
    patient_id_hashes: list[str]
    y: np.ndarray
    continuous_matrix: np.ndarray
    categorical_matrix: np.ndarray
    extended_matrix: np.ndarray
    continuous_columns: list[str]
    categorical_columns: list[str]
    extended_columns: list[str]


def _expected_table_columns(contract: Contract) -> list[str]:
    categorical = [column for group in contract.categorical_baseline_groups for column in group]
    return [
        "cohort_role",
        contract.patient_id_column,
        contract.target_column,
        *contract.continuous_baseline_columns,
        *categorical,
        *contract.extended_columns,
    ]


def _validate_patient_table(
    path: Path,
    expected_hash: str,
    contract: Contract,
    expected_role: str,
    *,
    min_n: int = 1,
) -> PatientTable:
    raw = _load_bytes(path)
    source_sha = _sha256(raw)
    _validate_hash(expected_hash, source_sha, "source-sha256")
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeError as exc:
        raise Failure("input file must be UTF-8", EXIT_SCHEMA) from exc
    if not lines:
        raise Failure("input table is empty", EXIT_SCHEMA)
    header = lines[0].split("\t")
    expected = _expected_table_columns(contract)
    if header != expected:
        raise Failure("input header mismatch", EXIT_SCHEMA)
    if len(lines) == 1:
        raise Failure("input table missing rows", EXIT_SCHEMA)
    categorical = [column for group in contract.categorical_baseline_groups for column in group]
    n_expected = len(header)
    index = {name: i for i, name in enumerate(header)}
    dummy_groups = [group for group in contract.categorical_baseline_groups]
    rows: list[tuple[str, float, list[float], list[int], list[float]]] = []
    seen_ids: set[str] = set()
    for row_no, line in enumerate(lines[1:], start=2):
        if line == "":
            raise Failure(f"row={row_no} field=record reason=blank-record", EXIT_SCHEMA)
        fields = line.split("\t")
        if len(fields) != n_expected:
            raise Failure(f"row={row_no} field=column_count reason=wrong-column-count", EXIT_SCHEMA)
        role = fields[index["cohort_role"]]
        if role != expected_role:
            raise Failure(f"row={row_no} field=cohort_role reason=role-mismatch", EXIT_SCHEMA)
        patient_id = fields[index[contract.patient_id_column]]
        if not patient_id:
            raise Failure(f"row={row_no} field={contract.patient_id_column} reason=empty-patient-id", EXIT_SCHEMA)
        if patient_id in seen_ids:
            raise Failure(f"row={row_no} field={contract.patient_id_column} reason=duplicate-patient-id", EXIT_SCHEMA)
        seen_ids.add(patient_id)
        y = _parse_float(fields[index[contract.target_column]], row=row_no, field=contract.target_column)
        continuous = [
            _parse_float(fields[index[column]], row=row_no, field=column)
            for column in contract.continuous_baseline_columns
        ]
        dummies: list[int] = []
        for group in dummy_groups:
            values = [_parse_binary(fields[index[column]], row=row_no, field=column) for column in group]
            if sum(values) > 1:
                raise Failure(
                    f"row={row_no} field=group:{','.join(group)} reason=non-exclusive-dummies",
                    EXIT_SCHEMA,
                )
            dummies.extend(values)
        extended = [
            _parse_float(fields[index[column]], row=row_no, field=column)
            for column in contract.extended_columns
        ]
        rows.append((patient_id, y, continuous, dummies, extended))
    if len(rows) < min_n:
        raise Failure(f"input patient count must be at least {min_n}", EXIT_SCHEMA)
    sorted_rows = sorted(enumerate(rows), key=lambda item: item[1][0].encode("utf-8"))
    patient_ids = [rows[i][0] for i, _ in sorted_rows]
    y = np.array([rows[i][1] for i, _ in sorted_rows], dtype=np.float64)
    continuous = np.array([rows[i][2] for i, _ in sorted_rows], dtype=np.float64, order="C")
    dummy = np.array([rows[i][3] for i, _ in sorted_rows], dtype=np.float64, order="C")
    extended = np.array([rows[i][4] for i, _ in sorted_rows], dtype=np.float64, order="C")
    patient_hashes = [_sha256(pid.encode("utf-8")) for pid in patient_ids]
    return PatientTable(
        raw_bytes=raw,
        source_sha256=source_sha,
        patient_ids=patient_ids,
        patient_id_hashes=patient_hashes,
        y=y,
        continuous_matrix=continuous,
        categorical_matrix=dummy,
        extended_matrix=extended,
        continuous_columns=contract.continuous_baseline_columns.copy(),
        categorical_columns=categorical,
        extended_columns=contract.extended_columns.copy(),
    )


@dataclass
class Transform:
    means: dict[str, float]
    scales: dict[str, float]
    dropped_columns: list[str]
    continuous_keep: list[int]
    categorical_keep: list[int]
    retained_feature_names: list[str]


def _apply_transform(
    continuous_matrix: np.ndarray,
    categorical_matrix: np.ndarray,
    continuous_columns: list[str],
    categorical_columns: list[str],
    transform: Transform,
) -> np.ndarray:
    if transform.continuous_keep:
        cont_means = np.array([transform.means[continuous_columns[i]] for i in transform.continuous_keep], dtype=np.float64)
        cont_scales = np.array([transform.scales[continuous_columns[i]] for i in transform.continuous_keep], dtype=np.float64)
        scaled = (continuous_matrix[:, transform.continuous_keep] - cont_means) / cont_scales
    else:
        scaled = np.empty((continuous_matrix.shape[0], 0), dtype=np.float64)
    cat = (
        categorical_matrix[:, transform.categorical_keep]
        if transform.categorical_keep
        else np.empty((categorical_matrix.shape[0], 0), dtype=np.float64)
    )
    return np.ascontiguousarray(np.concatenate([scaled, cat], axis=1), dtype=np.float64)


def _mse(y: np.ndarray, yhat: np.ndarray) -> float:
    diff = y - yhat
    return float(np.mean(np.square(diff), dtype=np.float64))


def _select_alpha(rows: list[tuple[float, float]]) -> float:
    best_alpha = rows[0][0]
    best_score = rows[0][1]
    for alpha, score in rows[1:]:
        if score < best_score:
            best_alpha = alpha
            best_score = score
        elif score == best_score and alpha > best_alpha:
            best_alpha = alpha
    return best_alpha


def _materialized_splits(n: int, seed: int) -> list[tuple[np.ndarray, np.ndarray]]:
    from sklearn.model_selection import KFold

    splitter = KFold(n_splits=5, shuffle=True, random_state=seed)
    return [
        (np.array(train_idx, dtype=np.int64), np.array(test_idx, dtype=np.int64))
        for train_idx, test_idx in splitter.split(np.arange(n))
    ]


def _combined_design(continuous_matrix: np.ndarray, categorical_matrix: np.ndarray) -> np.ndarray:
    parts = []
    if continuous_matrix.shape[1]:
        parts.append(continuous_matrix)
    if categorical_matrix.shape[1]:
        parts.append(categorical_matrix)
    if not parts:
        raise Failure("no predictor columns", EXIT_NUMERIC)
    return np.ascontiguousarray(np.concatenate(parts, axis=1), dtype=np.float64)


def _make_ridge_pipeline(alpha: float, model_cfg: dict[str, Any], n_continuous: int, n_categorical: int) -> Any:
    from sklearn.compose import ColumnTransformer
    from sklearn.feature_selection import VarianceThreshold
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    transformers: list[tuple[str, Any, list[int]]] = []
    if n_continuous:
        transformers.append(
            (
                "continuous",
                StandardScaler(copy=True, with_mean=True, with_std=True),
                list(range(n_continuous)),
            )
        )
    if n_categorical:
        transformers.append(
            (
                "categorical",
                "passthrough",
                list(range(n_continuous, n_continuous + n_categorical)),
            )
        )
    if not transformers:
        raise Failure("no predictor columns", EXIT_NUMERIC)
    preprocessor = ColumnTransformer(transformers, remainder="drop", sparse_threshold=0.0)
    ridge = Ridge(
        alpha=alpha,
        fit_intercept=model_cfg["fit_intercept"],
        solver=model_cfg["solver"],
        copy_X=model_cfg["copy_X"],
        positive=model_cfg["positive"],
        tol=model_cfg["tol"],
        max_iter=model_cfg["max_iter"],
    )
    return Pipeline(
        [
            ("preprocessor", preprocessor),
            ("variance", VarianceThreshold(threshold=0.0)),
            ("ridge", ridge),
        ]
    )


def _extract_fitted_state(
    pipeline: Any,
    continuous_columns: list[str],
    categorical_columns: list[str],
) -> tuple[Transform, np.ndarray, float, Any]:
    preprocessor = pipeline.named_steps["preprocessor"]
    variance = pipeline.named_steps["variance"]
    ridge = pipeline.named_steps["ridge"]
    means: dict[str, float] = {}
    scales: dict[str, float] = {}
    if continuous_columns:
        scaler = preprocessor.named_transformers_["continuous"]
        for i, column in enumerate(continuous_columns):
            means[column] = float(scaler.mean_[i])
            scales[column] = float(scaler.scale_[i])
    ordered_names = list(continuous_columns) + list(categorical_columns)
    support = np.asarray(variance.get_support(), dtype=bool)
    if support.size != len(ordered_names):
        raise Failure("variance-threshold feature mismatch", EXIT_NUMERIC)
    retained = [name for name, keep in zip(ordered_names, support) if keep]
    dropped = [name for name, keep in zip(ordered_names, support) if not keep]
    if not retained:
        raise Failure("fit produced zero non-constant columns", EXIT_NUMERIC)
    continuous_keep = [i for i, column in enumerate(continuous_columns) if column in retained]
    categorical_keep = [i for i, column in enumerate(categorical_columns) if column in retained]
    coef = np.ascontiguousarray(ridge.coef_, dtype=np.float64)
    if coef.shape[0] != len(retained):
        raise Failure("coefficient length mismatch", EXIT_NUMERIC)
    return (
        Transform(
            means=means,
            scales=scales,
            dropped_columns=dropped,
            continuous_keep=continuous_keep,
            categorical_keep=categorical_keep,
            retained_feature_names=retained,
        ),
        coef,
        float(ridge.intercept_),
        ridge,
    )


def _tune_model(
    continuous_matrix: np.ndarray,
    categorical_matrix: np.ndarray,
    y: np.ndarray,
    continuous_columns: list[str],
    categorical_columns: list[str],
    train_splits: list[tuple[np.ndarray, np.ndarray]],
    alpha_grid: list[float],
    model_cfg: dict[str, Any],
    phase: str,
    outer_fold: int,
    model_name: str,
) -> tuple[float, list[dict[str, Any]]]:
    from sklearn.model_selection import GridSearchCV

    x = _combined_design(continuous_matrix, categorical_matrix)
    y = np.ascontiguousarray(y, dtype=np.float64)
    pipeline = _make_ridge_pipeline(alpha_grid[0], model_cfg, len(continuous_columns), len(categorical_columns))
    cv_splits = [(np.asarray(train_idx, dtype=np.int64), np.asarray(valid_idx, dtype=np.int64)) for train_idx, valid_idx in train_splits]
    search = GridSearchCV(
        estimator=pipeline,
        param_grid={"ridge__alpha": list(alpha_grid)},
        scoring="neg_mean_squared_error",
        cv=cv_splits,
        refit=False,
        n_jobs=1,
        error_score="raise",
        return_train_score=False,
    )
    try:
        search.fit(x, y)
    except Exception as exc:
        raise Failure(f"model tuning failed: {exc}", EXIT_NUMERIC) from exc
    results = search.cv_results_
    alphas = [float(v) for v in results["param_ridge__alpha"]]
    mean_mse = [-float(v) for v in results["mean_test_score"]]
    candidate_scores = list(zip(alphas, mean_mse))
    if not candidate_scores:
        raise Failure("model tuning had no candidates", EXIT_NUMERIC)
    selected_alpha = _select_alpha(candidate_scores)
    tuning_rows: list[dict[str, Any]] = []
    for alpha_index, alpha in enumerate(alphas):
        for inner_fold, (train_idx, valid_idx) in enumerate(cv_splits):
            fold_mse = -float(results[f"split{inner_fold}_test_score"][alpha_index])
            tuning_rows.append(
                {
                    "phase": phase,
                    "model": model_name,
                    "outer_fold": outer_fold,
                    "inner_fold": inner_fold,
                    "alpha": alpha,
                    "mse": fold_mse,
                    "train_n": int(len(train_idx)),
                    "valid_n": int(len(valid_idx)),
                }
            )
    return selected_alpha, tuning_rows


def _fit_model_for_indices(
    continuous_matrix: np.ndarray,
    categorical_matrix: np.ndarray,
    y: np.ndarray,
    continuous_columns: list[str],
    categorical_columns: list[str],
    indices: np.ndarray,
    alpha: float,
    model_cfg: dict[str, Any],
) -> tuple[Transform, np.ndarray, float, Any]:
    x = _combined_design(continuous_matrix, categorical_matrix)
    y = np.ascontiguousarray(y, dtype=np.float64)
    pipeline = _make_ridge_pipeline(alpha, model_cfg, len(continuous_columns), len(categorical_columns))
    try:
        pipeline.fit(x[indices], y[indices])
    except Exception as exc:
        raise Failure(f"ridge fit failed: {exc}", EXIT_NUMERIC) from exc
    transform, coef, intercept, estimator = _extract_fitted_state(pipeline, continuous_columns, categorical_columns)
    solver_used = getattr(estimator, "solver_", None)
    if solver_used != model_cfg["solver"]:
        raise Failure(f"unexpected solver_ {solver_used}", EXIT_NUMERIC)
    return transform, coef, intercept, estimator


def _build_model_json(
    model_name: str,
    continuous_columns: list[str],
    categorical_columns: list[str],
    transform: Transform,
    coef: np.ndarray,
    intercept: float,
    alpha: float,
    sample_count: int,
) -> dict[str, Any]:
    if coef.shape[0] == 0:
        raise Failure("zero retained coefficients", EXIT_NUMERIC)
    return {
        "schema_version": f"B-P1-{model_name}-model-1",
        "name": model_name,
        "continuous_columns": list(continuous_columns),
        "categorical_columns": list(categorical_columns),
        "dropped_constant_columns": transform.dropped_columns,
        "retained_feature_names": transform.retained_feature_names,
        "continuous_means": transform.means,
        "continuous_scales": transform.scales,
        "alpha": alpha,
        "coefficients": [float(v) for v in coef.tolist()],
        "intercept": float(intercept),
        "solver": "svd",
        "solver_": "svd",
        "fit_intercept": True,
        "n_train_samples": int(sample_count),
        "n_train_features": int(len(transform.retained_feature_names)),
    }


def _build_bundle_manifest(contract: Contract, table: PatientTable, selected_alpha: dict[str, float], output_dir: Path) -> dict[str, Any]:
    return {
        "schema_version": "B-P1-bundle-manifest-1",
        "purpose": contract.purpose,
        "contract": contract.payload,
        "development_sha256": table.source_sha256,
        "contract_sha256": contract.raw_sha256,
        "development_patient_count": len(table.patient_ids),
        "development_patient_id_hashes": table.patient_id_hashes,
        "development_patient_set_hash": _sha256(_canonical_json_bytes(table.patient_id_hashes)),
        "engine_code_sha256": _engine_code_sha256(),
        "selected_alpha": selected_alpha,
        "outer_folds": 5,
        "cv_random_state": contract.outer_cv["random_state"],
        "python": platform.python_version(),
        "runtime": _runtime_receipt(),
    }


def _run_develop(contract_path: Path, development_path: Path, output_path: Path) -> int:
    _set_thread_limits()
    contract = _load_contract(contract_path)
    if contract.purpose == "scientific-run":
        _enforce_scientific_environment(contract.scientific_lock)
    _ensure_new_output(output_path, code=EXIT_OUTPUT)

    table = _validate_patient_table(
        development_path,
        contract.development_sha256,
        contract,
        contract.development_cohort,
        min_n=7,
    )
    n = len(table.y)

    baseline_cont_cols = table.continuous_columns
    baseline_cat_cols = table.categorical_columns
    ext_cont_cols = table.continuous_columns + table.extended_columns
    baseline_cont = table.continuous_matrix
    baseline_cat = table.categorical_matrix
    extended_cont = np.concatenate([table.continuous_matrix, table.extended_matrix], axis=1) if table.extended_columns else table.continuous_matrix
    # ext continuous columns remain numeric, shared cat matrix with baseline

    outer_splits = _materialized_splits(n, contract.outer_cv["random_state"])
    oof_baseline = np.full((n,), np.nan, dtype=np.float64)
    oof_extended = np.full((n,), np.nan, dtype=np.float64)
    fold_rows: list[tuple[str, int]] = [(pid, -1) for pid in table.patient_ids]
    tuning_rows: list[dict[str, Any]] = []
    outer_alpha_baseline: list[float] = []
    outer_alpha_extended: list[float] = []

    for outer_fold, (train_idx, valid_idx) in enumerate(outer_splits):
        inner_splits = _materialized_splits(len(train_idx), contract.inner_cv["random_state"])
        inner_splits = [  # map fold-local indices to global indices
            (train_idx[inner_train], train_idx[inner_valid])
            for inner_train, inner_valid in inner_splits
        ]

        b_alpha, b_tune = _tune_model(
            baseline_cont,
            baseline_cat,
            table.y,
            baseline_cont_cols,
            baseline_cat_cols,
            inner_splits,
            contract.alpha_grid,
            contract.model,
            phase="outer",
            outer_fold=outer_fold,
            model_name="baseline",
        )
        e_alpha, e_tune = _tune_model(
            extended_cont,
            baseline_cat,
            table.y,
            ext_cont_cols,
            baseline_cat_cols,
            inner_splits,
            contract.alpha_grid,
            contract.model,
            phase="outer",
            outer_fold=outer_fold,
            model_name="extended",
        )
        tuning_rows.extend(b_tune + e_tune)
        outer_alpha_baseline.append(b_alpha)
        outer_alpha_extended.append(e_alpha)

        b_transform, b_coef, b_intercept, _ = _fit_model_for_indices(
            baseline_cont,
            baseline_cat,
            table.y,
            baseline_cont_cols,
            baseline_cat_cols,
            train_idx,
            b_alpha,
            contract.model,
        )
        e_transform, e_coef, e_intercept, _ = _fit_model_for_indices(
            extended_cont,
            baseline_cat,
            table.y,
            ext_cont_cols,
            baseline_cat_cols,
            train_idx,
            e_alpha,
            contract.model,
        )
        b_pred = _apply_transform(
            baseline_cont, baseline_cat, baseline_cont_cols, baseline_cat_cols, b_transform
        )[valid_idx] @ b_coef + b_intercept
        e_pred = _apply_transform(
            extended_cont, baseline_cat, ext_cont_cols, baseline_cat_cols, e_transform
        )[valid_idx] @ e_coef + e_intercept
        oof_baseline[valid_idx] = b_pred
        oof_extended[valid_idx] = e_pred
        for v in valid_idx:
            fold_rows[v] = (table.patient_ids[v], outer_fold)

    if np.isnan(oof_baseline).any() or np.isnan(oof_extended).any():
        raise Failure("OOF predictions are incomplete", EXIT_NUMERIC)

    # Outer diagnostics
    outer_metrics: list[dict[str, Any]] = []
    for outer_fold, (_, valid_idx) in enumerate(outer_splits):
        y_val = table.y[valid_idx]
        y0 = oof_baseline[valid_idx]
        y1 = oof_extended[valid_idx]
        outer_metrics.append(
            {
                "outer_fold": outer_fold,
                "mse_baseline": _mse(y_val, y0),
                "mse_extended": _mse(y_val, y1),
                "r2_baseline": _r2(y_val, y0),
                "r2_extended": _r2(y_val, y1),
            }
        )

    final_inner = _materialized_splits(n, contract.final_cv["random_state"])
    final_baseline_alpha, final_baseline_rows = _tune_model(
        baseline_cont,
        baseline_cat,
        table.y,
        baseline_cont_cols,
        baseline_cat_cols,
        final_inner,
        contract.alpha_grid,
        contract.model,
        phase="final",
        outer_fold=-1,
        model_name="baseline",
    )
    final_extended_alpha, final_extended_rows = _tune_model(
        extended_cont,
        baseline_cat,
        table.y,
        ext_cont_cols,
        baseline_cat_cols,
        final_inner,
        contract.alpha_grid,
        contract.model,
        phase="final",
        outer_fold=-1,
        model_name="extended",
    )
    tuning_rows.extend(final_baseline_rows + final_extended_rows)

    baseline_transform, baseline_coef, baseline_intercept, _ = _fit_model_for_indices(
        baseline_cont,
        baseline_cat,
        table.y,
        baseline_cont_cols,
        baseline_cat_cols,
        np.arange(n, dtype=np.int64),
        final_baseline_alpha,
        contract.model,
    )
    extended_transform, extended_coef, extended_intercept, _ = _fit_model_for_indices(
        extended_cont,
        baseline_cat,
        table.y,
        ext_cont_cols,
        baseline_cat_cols,
        np.arange(n, dtype=np.int64),
        final_extended_alpha,
        contract.model,
    )

    baseline_model = _build_model_json(
        "baseline",
        baseline_cont_cols,
        baseline_cat_cols,
        baseline_transform,
        baseline_coef,
        baseline_intercept,
        final_baseline_alpha,
        n,
    )
    extended_model = _build_model_json(
        "extended",
        ext_cont_cols,
        baseline_cat_cols,
        extended_transform,
        extended_coef,
        extended_intercept,
        final_extended_alpha,
        n,
    )

    sst = float(np.sum((table.y - np.mean(table.y, dtype=np.float64)) ** 2, dtype=np.float64))
    sse_baseline = float(np.sum((table.y - oof_baseline) ** 2, dtype=np.float64))
    sse_extended = float(np.sum((table.y - oof_extended) ** 2, dtype=np.float64))
    r2_baseline = None if sst == 0.0 else 1.0 - (sse_baseline / sst)
    r2_extended = None if sst == 0.0 else 1.0 - (sse_extended / sst)
    development_metrics = {
        "schema_version": "B-P1-development-metrics-1",
        "purpose": contract.purpose,
        "contract_sha256": contract.raw_sha256,
        "development_rows": n,
        "outer_fold_metrics": outer_metrics,
        "pooled": {
            "sse_baseline": sse_baseline,
            "sse_extended": sse_extended,
            "sst": sst,
            "r2_baseline": r2_baseline,
            "r2_extended": None if sst == 0.0 else 1.0 - (sse_extended / sst),
            "delta_r2": None if sst == 0.0 else (sse_baseline - sse_extended) / sst,
        },
        "oof_rows": [
            {
                contract.patient_id_column: pid,
                contract.target_column: float(y),
                "f0": float(p0),
                "f1": float(p1),
            }
            for pid, y, p0, p1 in zip(table.patient_ids, table.y, oof_baseline, oof_extended)
        ],
    }

    selected_alpha = {
        "baseline_outer_median": float(np.median(outer_alpha_baseline)),
        "extended_outer_median": float(np.median(outer_alpha_extended)),
        "baseline_final": float(final_baseline_alpha),
        "extended_final": float(final_extended_alpha),
    }

    bundle_dir = output_path / "bundle"
    bundle_dir.mkdir(parents=True)
    manifest_path = bundle_dir / "bundle_manifest.json"
    baseline_path = bundle_dir / "baseline_model.json"
    extended_path = bundle_dir / "extended_model.json"
    metrics_path = bundle_dir / "development_metrics.json"
    fold_assignments_path = bundle_dir / "fold_assignments.tsv"
    tuning_path = bundle_dir / "tuning_results.tsv"
    oof_path = bundle_dir / "oof_predictions.tsv"
    checksums_path = bundle_dir / "checksums.json"
    complete_path = bundle_dir / "COMPLETE.json"

    # persist payloads
    bundle_manifest = _build_bundle_manifest(contract, table, selected_alpha, output_path)
    _atomic_write_json(manifest_path, bundle_manifest)
    _atomic_write_json(baseline_path, baseline_model)
    _atomic_write_json(extended_path, extended_model)
    _atomic_write_json(metrics_path, development_metrics)
    _atomic_write_tsv(
        fold_assignments_path,
        [[pid, str(fold)] for pid, fold in fold_rows],
        ["patient_id", "outer_fold"],
    )
    _atomic_write_tsv(
        oof_path,
        [
            [pid, str(float(y)), str(float(p0)), str(float(p1)), str(float((y - p0) ** 2)), str(float((y - p1) ** 2))]
            for pid, y, p0, p1 in zip(table.patient_ids, table.y, oof_baseline, oof_extended)
        ],
        ["patient_id", "Y", "f0", "f1", "sse_baseline", "sse_extended"],
    )
    _atomic_write_tsv(
        tuning_path,
        [[str(row[k]) for k in ["phase", "model", "outer_fold", "inner_fold", "alpha", "mse", "train_n", "valid_n"]] for row in tuning_rows],
        ["phase", "model", "outer_fold", "inner_fold", "alpha", "mse", "train_n", "valid_n"],
    )
    run_receipt = {
        "schema_version": "B-P1-develop-completion-1",
        "purpose": contract.purpose,
        "status": "complete",
        "command": f"python -m tools.b_prediction develop --contract {contract.path} --development {development_path} --output {output_path}",
        "hash": {
            "contract": contract.raw_sha256,
            "development": table.source_sha256,
        },
        "runtime": _runtime_receipt(),
        "host": {
            "python_version": platform.python_version(),
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    }
    run_receipt_path = output_path / "run_receipt.json"
    _atomic_write_json(run_receipt_path, run_receipt)

    payload_map = {
        "bundle_manifest.json": manifest_path,
        "baseline_model.json": baseline_path,
        "extended_model.json": extended_path,
        "development_metrics.json": metrics_path,
        "fold_assignments.tsv": fold_assignments_path,
        "tuning_results.tsv": tuning_path,
        "oof_predictions.tsv": oof_path,
    }
    checksums = {name: _sha256(path.read_bytes()) for name, path in payload_map.items()}
    checksums_payload = {
        "schema_version": "B-P1-checksums-1",
        "files": checksums,
        "contract_sha256": contract.raw_sha256,
        "development_sha256": table.source_sha256,
        "runtime": _runtime_receipt(),
    }
    _atomic_write_json(checksums_path, checksums_payload)
    complete_payload = {
        "schema_version": "B-P1-complete-1",
        "status": "complete",
        "bundle_hash": _sha256(checksums_path.read_bytes()),
        "checksum_manifest": str(checksums_path.name),
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _atomic_write_json(complete_path, complete_payload)
    return 0


def _r2(y_true: np.ndarray, y_pred: np.ndarray) -> float | None:
    if y_true.size < 2:
        return None
    sst = np.sum((y_true - np.mean(y_true, dtype=np.float64)) ** 2, dtype=np.float64)
    if sst == 0.0:
        return None
    sse = np.sum((y_true - y_pred) ** 2, dtype=np.float64)
    return 1.0 - (sse / sst)


def _load_bundle(bundle_dir: Path) -> dict[str, Any]:
    manifest_path = bundle_dir / "bundle_manifest.json"
    checksums_path = bundle_dir / "checksums.json"
    complete_path = bundle_dir / "COMPLETE.json"
    required_payload = {
        manifest_path.name,
        "baseline_model.json",
        "extended_model.json",
        "development_metrics.json",
        "fold_assignments.tsv",
        "tuning_results.tsv",
        "oof_predictions.tsv",
        checksums_path.name,
        complete_path.name,
    }
    for path in required_payload:
        if not (bundle_dir / path).exists():
            raise Failure(f"bundle missing {path}", EXIT_SCHEMA)
    all_files = {p.name for p in bundle_dir.iterdir() if p.is_file()}
    if all_files != required_payload:
        unknown = all_files - required_payload
        missing = required_payload - all_files
        if unknown:
            raise Failure(f"bundle has undeclared payload {sorted(unknown)[0]}", EXIT_SCHEMA)
        if missing:
            raise Failure(f"bundle missing payload {sorted(missing)[0]}", EXIT_SCHEMA)

    manifest = _json_no_dups(_load_bytes(manifest_path))
    checksums_raw = _load_bytes(checksums_path)
    checksums = _json_no_dups(checksums_raw)
    complete = _json_no_dups(_load_bytes(complete_path))
    if complete.get("schema_version") != "B-P1-complete-1" or complete.get("status") != "complete":
        raise Failure("bundle incomplete", EXIT_SCHEMA)
    if complete.get("bundle_hash") != _sha256(checksums_raw):
        raise Failure("bundle checksum mismatch", EXIT_SCHEMA)
    files = checksums.get("files", {})
    if set(files.keys()) != {
        "bundle_manifest.json",
        "baseline_model.json",
        "extended_model.json",
        "development_metrics.json",
        "fold_assignments.tsv",
        "tuning_results.tsv",
        "oof_predictions.tsv",
    }:
        raise Failure("checksum manifest mismatch", EXIT_SCHEMA)
    for name, expected_sha in files.items():
        observed = _sha256((bundle_dir / name).read_bytes())
        if expected_sha != observed:
            raise Failure(f"checksum mismatch {name}", EXIT_SCHEMA)

    baseline_model = _json_no_dups(_load_bytes(bundle_dir / "baseline_model.json"))
    extended_model = _json_no_dups(_load_bytes(bundle_dir / "extended_model.json"))
    contract_payload = manifest.get("contract")
    if not isinstance(contract_payload, dict):
        raise Failure("bundle manifest missing contract", EXIT_SCHEMA)
    return {
        "manifest": manifest,
        "checksums": checksums,
        "complete": complete,
        "baseline_model": baseline_model,
        "extended_model": extended_model,
        "contract_payload": contract_payload,
    }


def _load_evaluation_lock(
    path: Path,
    contract_hash: str,
    bundle_hash: str,
    external_sha: str,
    *,
    contract_purpose: str,
    contract_scientific_lock: dict[str, Any],
) -> tuple[dict[str, Any], bytes]:
    raw = _load_bytes(path)
    lock = _json_no_dups(raw)
    if not isinstance(lock, dict):
        raise Failure("evaluation-lock must be object", EXIT_SCHEMA)
    if contract_purpose == "synthetic-test":
        expected_fields = set(SYNTHETIC_EVALUATION_LOCK_FIELDS)
    elif contract_purpose == "scientific-run":
        expected_fields = set(SCIENTIFIC_EVALUATION_LOCK_FIELDS)
    else:
        raise Failure("evaluation-lock purpose mismatch", EXIT_SCHEMA)
    if set(lock.keys()) != expected_fields:
        missing = expected_fields - set(lock.keys())
        if missing:
            raise Failure(f"evaluation-lock missing {sorted(missing)[0]}", EXIT_SCHEMA)
        raise Failure(f"evaluation-lock unknown field {sorted(set(lock.keys()) - expected_fields)[0]}", EXIT_SCHEMA)
    if lock["schema_version"] != LOCK_SCHEMA_VERSION:
        raise Failure("evaluation-lock schema mismatch", EXIT_SCHEMA)
    if lock["status"] not in {"synthetic-only", "approved"}:
        raise Failure("evaluation-lock invalid status", EXIT_SCHEMA)
    if contract_purpose == "synthetic-test" and lock["status"] != "synthetic-only":
        raise Failure("evaluation-lock status mismatched for synthetic-test", EXIT_SCHEMA)
    if contract_purpose == "scientific-run" and lock["status"] != "approved":
        raise Failure("evaluation-lock status mismatched for scientific-run", EXIT_SCHEMA)
    if lock["contract_sha256"] != contract_hash:
        raise Failure("evaluation-lock contract hash mismatch", EXIT_SCHEMA)
    if lock["bundle_sha256"] != bundle_hash:
        raise Failure("evaluation-lock bundle hash mismatch", EXIT_SCHEMA)
    if lock["external_sha256"] != external_sha:
        raise Failure("evaluation-lock external hash mismatch", EXIT_SCHEMA)
    if contract_purpose == "scientific-run":
        for key in (
            "decision_commit",
            "reviewer_receipt",
            "eligibility_hash",
            "external_population_contract_hash",
            "precision_contract_id",
        ):
            if lock[key] != contract_scientific_lock.get(key):
                raise Failure(f"evaluation-lock {key} mismatch with frozen contract lock", EXIT_SCHEMA)
    return lock, raw


def _bootstrap_delta(y: np.ndarray, f0: np.ndarray, f1: np.ndarray, bootstrap_cfg: dict[str, Any]) -> dict[str, Any]:
    n = y.size
    if n < 2:
        return {
            "status": "undefined",
            "reason": "need at least 2 patients",
            "sse_baseline": None,
            "sse_extended": None,
            "sst": None,
            "r2_baseline": None,
            "r2_extended": None,
            "delta_r2": None,
            "bootstrap": {
                "status": "undefined",
                "reason": "need at least 2 patients",
                "undefined_count": int(n),
                "undefined_fraction": 1.0,
                "delta_ci_lower": None,
                "delta_ci_upper": None,
            },
        }

    base = np.mean(y, dtype=np.float64)
    sst = np.sum((y - base) ** 2, dtype=np.float64)
    sse0 = float(np.sum((y - f0) ** 2, dtype=np.float64))
    sse1 = float(np.sum((y - f1) ** 2, dtype=np.float64))
    if sst == 0.0:
        return {
            "status": "undefined",
            "reason": "external SST is zero",
            "sse_baseline": sse0,
            "sse_extended": sse1,
            "sst": float(sst),
            "r2_baseline": None,
            "r2_extended": None,
            "delta_r2": None,
            "bootstrap": {
                "status": "undefined",
                "reason": "external SST is zero",
                "undefined_count": int(bootstrap_cfg["resamples"]),
                "undefined_fraction": 1.0,
                "delta_ci_lower": None,
                "delta_ci_upper": None,
            },
        }
    r2_0 = 1.0 - (sse0 / sst)
    r2_1 = 1.0 - (sse1 / sst)
    delta = (sse0 - sse1) / sst

    rng = np.random.default_rng(np.random.PCG64(bootstrap_cfg["random_state"]))
    boot = []
    undefined = 0
    for _ in range(int(bootstrap_cfg["resamples"])):
        idx = rng.integers(0, n, size=n)
        yy = y[idx]
        d0 = f0[idx]
        d1 = f1[idx]
        sst_b = np.sum((yy - np.mean(yy, dtype=np.float64)) ** 2, dtype=np.float64)
        if sst_b == 0.0:
            undefined += 1
            continue
        sse0_b = np.sum((yy - d0) ** 2, dtype=np.float64)
        sse1_b = np.sum((yy - d1) ** 2, dtype=np.float64)
        boot.append((sse0_b - sse1_b) / sst_b)
    if boot:
        interval = np.quantile(np.array(boot, dtype=np.float64), bootstrap_cfg["quantiles"], method=bootstrap_cfg["quantile_method"])
        boot_payload = {
            "status": "defined",
            "reason": None,
            "undefined_count": int(undefined),
            "undefined_fraction": undefined / float(bootstrap_cfg["resamples"]),
            "delta_ci_lower": float(interval[0]),
            "delta_ci_upper": float(interval[1]),
        }
    else:
        boot_payload = {
            "status": "undefined",
            "reason": "no defined bootstrap resamples",
            "undefined_count": int(undefined),
            "undefined_fraction": 1.0,
            "delta_ci_lower": None,
            "delta_ci_upper": None,
        }

    return {
        "status": "defined",
        "reason": None,
        "sse_baseline": sse0,
        "sse_extended": sse1,
        "sst": float(sst),
        "r2_baseline": float(r2_0),
        "r2_extended": float(r2_1),
        "delta_r2": float(delta),
        "bootstrap": boot_payload,
    }


def _run_evaluate(bundle_dir: Path, lock_path: Path, external_path: Path, output_path: Path) -> int:
    _set_thread_limits()
    _ensure_new_output(output_path, code=EXIT_OUTPUT)
    bundle = _load_bundle(bundle_dir)
    external_sha = _sha256(_load_bytes(external_path))
    frozen_contract_sha = bundle["manifest"]["contract_sha256"]
    contract = _load_contract_from_payload(bundle["manifest"]["contract"], raw_sha256=frozen_contract_sha)
    engine_code_sha = _engine_code_sha256()
    if bundle["manifest"].get("engine_code_sha256") != engine_code_sha:
        raise Failure("bundle engine code hash mismatch", EXIT_SCHEMA)
    if contract.purpose == "scientific-run":
        _enforce_scientific_environment(contract.scientific_lock)
    lock, lock_raw = _load_evaluation_lock(
        lock_path,
        bundle["manifest"]["contract_sha256"],
        bundle["complete"]["bundle_hash"],
        external_sha,
        contract_purpose=contract.purpose,
        contract_scientific_lock=contract.scientific_lock,
    )
    lock_sha = _sha256(lock_raw)
    external = _validate_patient_table(
        external_path,
        lock["external_sha256"],
        contract,
        contract.external_cohort,
        min_n=1,
    )
    if set(external.patient_id_hashes) & set(bundle["manifest"]["development_patient_id_hashes"]):
        raise Failure("external and development patients overlap", EXIT_SCHEMA)

    baseline_pred, baseline_trace = _evaluate_from_models(
        external,
        contract,
        bundle["baseline_model"],
        include_extended=False,
    )
    extended_pred, extended_trace = _evaluate_from_models(
        external,
        contract,
        bundle["extended_model"],
        include_extended=True,
    )
    metrics = _bootstrap_delta(external.y, baseline_pred, extended_pred, bundle["manifest"]["contract"]["bootstrap"])
    output_path.mkdir(parents=True)
    predictions_path = output_path / "predictions.tsv"
    evaluation_path = output_path / "evaluation.json"
    checksums_path = output_path / "checksums.json"
    complete_path = output_path / "COMPLETE.json"

    _atomic_write_tsv(
        predictions_path,
        [
            [
                pid,
                str(float(y)),
                str(float(f0)),
                str(float(f1)),
                str(float((y - f0) ** 2)),
                str(float((y - f1) ** 2)),
            ]
            for pid, y, f0, f1 in zip(external.patient_ids, external.y, baseline_pred, extended_pred)
        ],
        ["patient_id", "Y", "f0", "f1", "sse_baseline", "sse_extended"],
    )

    eval_payload = {
        "schema_version": "B-P1-evaluation-1",
        "purpose": contract.purpose,
        "contract_sha256": frozen_contract_sha,
        "bundle_hash": bundle["complete"]["bundle_hash"],
        "evaluation_lock_sha256": lock_sha,
        "external_sha256": external_sha,
        "engine_code_sha256": engine_code_sha,
        "evaluation_lock_status": lock["status"],
        "metrics": {
            "sse_baseline": metrics["sse_baseline"],
            "sse_extended": metrics["sse_extended"],
            "sst": metrics["sst"],
            "r2_baseline": metrics["r2_baseline"],
            "r2_extended": metrics["r2_extended"],
            "delta_r2": metrics["delta_r2"],
            "status": metrics["status"],
            "reason": metrics["reason"],
            "bootstrap": metrics["bootstrap"],
        },
        "traces": {
            "baseline": baseline_trace,
            "extended": extended_trace,
            "runtime": _runtime_receipt(),
        },
        "contract": {
            "development_cohort": contract.development_cohort,
            "external_cohort": contract.external_cohort,
            "development_patient_count": int(len(bundle["manifest"]["development_patient_id_hashes"])),
            "external_patient_count": int(len(external.patient_ids)),
        },
    }
    if contract.purpose == "scientific-run":
        eval_payload["scientific_identifiers"] = {
            "decision_commit": lock["decision_commit"],
            "reviewer_receipt": lock["reviewer_receipt"],
            "eligibility_hash": lock["eligibility_hash"],
            "external_population_contract_hash": lock["external_population_contract_hash"],
            "precision_contract_id": lock["precision_contract_id"],
        }
    _atomic_write_json(evaluation_path, eval_payload)
    checksums = {
        "schema_version": "B-P1-evaluation-checksums-1",
        "files": {
            "predictions.tsv": _sha256(predictions_path.read_bytes()),
            "evaluation.json": _sha256(evaluation_path.read_bytes()),
        },
        "runtime": _runtime_receipt(),
        "contract_sha256": frozen_contract_sha,
        "bundle_hash": bundle["complete"]["bundle_hash"],
        "engine_code_sha256": engine_code_sha,
    }
    _atomic_write_json(checksums_path, checksums)
    complete_payload = {
        "schema_version": "B-P1-evaluation-complete-1",
        "status": "complete",
        "evaluation_hash": _sha256(checksums_path.read_bytes()),
        "purpose": contract.purpose,
    }
    _atomic_write_json(complete_path, complete_payload)
    return 0


def _load_contract_from_payload(payload: dict[str, Any], *, raw_sha256: str | None = None) -> Contract:
    payload_copy = dict(payload)
    raw = _canonical_json_bytes(payload_copy)
    path = Path("bundle-contract.json")
    _validate_contract_fields(payload_copy)
    return Contract(
        path=path,
        payload=payload_copy,
        raw_bytes=raw,
        raw_sha256=raw_sha256 if raw_sha256 is not None else _sha256(raw),
        purpose=payload_copy["purpose"],
        development_cohort=payload_copy["development_cohort"],
        external_cohort=payload_copy["external_cohort"],
        patient_id_column=payload_copy["patient_id_column"],
        target_column=payload_copy["target_column"],
        continuous_baseline_columns=list(payload_copy["continuous_baseline_columns"]),
        categorical_baseline_groups=[list(group) for group in payload_copy["categorical_baseline_groups"]],
        extended_columns=list(payload_copy["extended_columns"]),
        alpha_grid=list(payload_copy["alpha_grid"]),
        outer_cv=dict(payload_copy["outer_cv"]),
        inner_cv=dict(payload_copy["inner_cv"]),
        final_cv=dict(payload_copy["final_cv"]),
        bootstrap=dict(payload_copy["bootstrap"]),
        model=dict(payload_copy["model"]),
        scientific_lock=dict(payload_copy["scientific_lock"]),
        development_sha256=payload_copy["development_sha256"],
    )


def _evaluate_from_models(
    external: PatientTable,
    contract: Contract,
    model_payload: dict[str, Any],
    include_extended: bool,
) -> tuple[np.ndarray, dict[str, Any]]:
    required = {
        "continuous_columns",
        "categorical_columns",
        "dropped_constant_columns",
        "retained_feature_names",
        "continuous_means",
        "continuous_scales",
        "coefficients",
        "intercept",
    }
    if not required <= set(model_payload.keys()):
        raise Failure("bundle model missing fields", EXIT_SCHEMA)
    continuous_columns = contract.continuous_baseline_columns + (contract.extended_columns if include_extended else [])
    categorical_columns = [c for group in contract.categorical_baseline_groups for c in group]
    transform = Transform(
        means={k: float(v) for k, v in model_payload["continuous_means"].items()},
        scales={k: float(v) for k, v in model_payload["continuous_scales"].items()},
        dropped_columns=list(model_payload["dropped_constant_columns"]),
        continuous_keep=[i for i, col in enumerate(continuous_columns) if col in model_payload["retained_feature_names"] and col not in model_payload["dropped_constant_columns"]],
        categorical_keep=[i for i, col in enumerate(categorical_columns) if col in model_payload["retained_feature_names"] and col not in model_payload["dropped_constant_columns"]],
        retained_feature_names=list(model_payload["retained_feature_names"]),
    )
    continuous_matrix = external.continuous_matrix
    if include_extended:
        continuous_matrix = np.concatenate([external.continuous_matrix, external.extended_matrix], axis=1)
    transformed = _apply_transform(
        continuous_matrix,
        external.categorical_matrix,
        continuous_columns,
        categorical_columns,
        transform,
    )
    coefs = np.asarray(model_payload["coefficients"], dtype=np.float64)
    if transformed.shape[1] != coefs.shape[0]:
        raise Failure("evaluate model-projection mismatch", EXIT_SCHEMA)
    pred = transformed @ coefs + float(model_payload["intercept"])
    trace = {
        "n_features": int(transformed.shape[1]),
        "retained_features": transform.retained_feature_names,
    }
    return pred.astype(np.float64), trace


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="B-P1 released prediction engine")
    subparsers = parser.add_subparsers(dest="command", required=True)
    develop = subparsers.add_parser("develop")
    develop.add_argument("--contract", required=True, type=Path)
    develop.add_argument("--development", required=True, type=Path)
    develop.add_argument("--output", required=True, type=Path)

    develop_fold = subparsers.add_parser("develop-fold")
    develop_fold.add_argument("--config", required=True, type=Path)
    develop_fold.add_argument("--cohort", required=True, type=Path)
    develop_fold.add_argument("--w4", required=True, type=Path)
    develop_fold.add_argument("--output", required=True, type=Path)
    develop_fold.add_argument("--repo-root", type=Path, default=None)

    evaluate = subparsers.add_parser("evaluate")
    evaluate.add_argument("--bundle", required=True, type=Path)
    evaluate.add_argument("--evaluation-lock", required=True, type=Path)
    evaluate.add_argument("--external", required=True, type=Path)
    evaluate.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "develop":
            return _run_develop(args.contract, args.development, args.output)
        if args.command == "develop-fold":
            from tools.b_prediction.fold_develop import run_fold_develop
            from tools.b_workflow.config import load_config

            repo_root = (args.repo_root or Path.cwd()).resolve()
            config = load_config(args.config, repo_root=repo_root)
            run_fold_develop(
                config,
                repo_root=repo_root,
                w3_dir=args.cohort.resolve(),
                w4_dir=args.w4.resolve(),
                stage_dir=args.output.resolve(),
                parent_hashes={"config": config["_config_sha256"]},
                code_identity="cli-direct",
                interpreter=sys.executable,
            )
            return 0
        if args.command == "evaluate":
            return _run_evaluate(args.bundle, args.evaluation_lock, args.external, args.output)
        raise Failure("unknown command", EXIT_ARGUMENT)
    except Failure as exc:
        print(str(exc), file=sys.stderr)
        return exc.code
    except Exception as exc:  # pragma: no cover
        print(f"unexpected_error={exc}", file=sys.stderr)
        return EXIT_NUMERIC


if __name__ == "__main__":
    raise SystemExit(main())
