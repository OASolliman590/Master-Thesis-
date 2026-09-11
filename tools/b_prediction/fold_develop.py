"""Fold-local nested development: fit features inside every training partition."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from tools.b_features.provider import FeatureState, FoldFeatureProvider
from tools.b_prediction.adapter import encode_eligible_rows, ordered_feature_columns
from tools.b_prediction.__main__ import (
    EXIT_NUMERIC,
    Failure,
    RELEASED_ALPHA_GRID,
    RELEASED_BOOTSTRAP,
    SCHEMA_VERSION,
    _apply_transform,
    _atomic_write_json,
    _atomic_write_tsv,
    _build_model_json,
    _canonical_json_bytes,
    _engine_code_sha256,
    _fit_model_for_indices,
    _make_ridge_pipeline,
    _materialized_splits,
    _mse,
    _r2,
    _runtime_receipt,
    _select_alpha,
    _set_thread_limits,
    _sha256,
    _validate_contract_fields,
)
from tools.b_workflow.io import (
    PipelineFailure,
    atomic_write_json,
    canonical_json_bytes,
    json_no_dups,
    publish_directory,
    remove_tree,
    sha256_bytes,
    sha256_file,
    utc_stamp,
)


def _fail(message: str, code: int = 3) -> None:
    raise PipelineFailure(f"stage=W5 {message}", code, "W5")


def _base_eligibility(provider: FoldFeatureProvider, patient_id: str) -> str | None:
    policy = provider.policy
    universe = list(policy["universe_u"])
    expr = provider.expression.get(patient_id, {})
    cov = provider.covariates.get(patient_id, {})
    for gene in universe:
        if expr.get(gene) is None:
            return f"incomplete-universe:{gene}"
    from tools.b_workflow.io import parse_optional_float

    elig = policy["eligibility"]
    if elig.get("require_age") and parse_optional_float(cov.get("age_years", "NA"), field="age_years", row=1) is None:
        return "missing-age"
    if elig.get("require_gleason") and parse_optional_float(cov.get("gleason_sum", "NA"), field="gleason_sum", row=1) is None:
        return "missing-gleason"
    if elig.get("require_purity") and parse_optional_float(cov.get("purity_value", "NA"), field="purity_value", row=1) is None:
        return "missing-purity"
    return None


def _candidate_ids(provider: FoldFeatureProvider, development_cohort: str) -> list[str]:
    """Select only fixed cohort/endpoint/baseline eligibility before folds.

    Promoter eligibility is value-dependent and therefore belongs inside each
    training fold's fitted feature state and corresponding transform.
    """
    ids = []
    for pid, cov in provider.covariates.items():
        if cov.get("cohort") != development_cohort:
            continue
        reason = _base_eligibility(provider, pid)
        if reason is None:
            ids.append(pid)
    return sorted(ids, key=lambda item: item.encode("utf-8"))


def _score_alphas(
    cont: np.ndarray,
    dummy: np.ndarray,
    y: np.ndarray,
    valid_cont: np.ndarray,
    valid_dummy: np.ndarray,
    valid_y: np.ndarray,
    n_cont: int,
    n_cat: int,
    alpha_grid: list[float],
    model_cfg: dict[str, Any],
) -> list[tuple[float, float]]:
    rows: list[tuple[float, float]] = []
    x_train = np.ascontiguousarray(
        np.concatenate([cont, dummy], axis=1) if n_cat else cont,
        dtype=np.float64,
    )
    x_valid = np.ascontiguousarray(
        np.concatenate([valid_cont, valid_dummy], axis=1) if n_cat else valid_cont,
        dtype=np.float64,
    )
    y_train = np.ascontiguousarray(y, dtype=np.float64)
    y_valid = np.ascontiguousarray(valid_y, dtype=np.float64)
    for alpha in alpha_grid:
        pipeline = _make_ridge_pipeline(alpha, model_cfg, n_cont, n_cat)
        try:
            pipeline.fit(x_train, y_train)
            pred = pipeline.predict(x_valid)
        except Exception as exc:
            raise Failure(f"model tuning failed: {exc}", EXIT_NUMERIC) from exc
        rows.append((float(alpha), _mse(y_valid, np.asarray(pred, dtype=np.float64))))
    return rows


def _require_counts(train_n: int, valid_n: int, *, phase: str, outer: int, inner: int | None) -> None:
    if train_n < 2:
        _fail(
            f"reason=insufficient-eligible-training phase={phase} outer={outer} inner={inner} n={train_n}"
        )
    if valid_n < 1:
        _fail(
            f"reason=insufficient-eligible-validation phase={phase} outer={outer} inner={inner} n={valid_n}"
        )


def _model_cfg() -> dict[str, Any]:
    return {
        "type": "ridge",
        "continuous_scaler": "standard",
        "fit_intercept": True,
        "solver": "svd",
        "tol": 0.0001,
        "copy_X": True,
        "positive": False,
        "max_iter": None,
    }


def _synthetic_contract_payload(w5: dict[str, Any], development_sha256: str, development: str, external: str) -> dict[str, Any]:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "purpose": "synthetic-test",
        "development_cohort": development,
        "external_cohort": external,
        "patient_id_column": "patient_id",
        "target_column": "Y",
        "continuous_baseline_columns": list(w5["continuous_baseline_columns"]),
        "categorical_baseline_groups": [list(g) for g in w5["categorical_baseline_groups"]],
        "extended_columns": list(w5["extended_columns"]),
        "alpha_grid": list(RELEASED_ALPHA_GRID),
        "outer_cv": {"n_splits": 5, "shuffle": True, "random_state": 42},
        "inner_cv": {"n_splits": 5, "shuffle": True, "random_state": 42},
        "final_cv": {"n_splits": 5, "shuffle": True, "random_state": 42},
        "bootstrap": dict(RELEASED_BOOTSTRAP),
        "model": _model_cfg(),
        "development_sha256": development_sha256,
        "scientific_lock": {"status": "synthetic-only"},
    }
    _validate_contract_fields(payload)
    return payload


def run_fold_develop(
    config: dict[str, Any],
    *,
    repo_root: Path,
    w3_dir: Path,
    w4_dir: Path,
    stage_dir: Path,
    parent_hashes: dict[str, str],
    code_identity: str,
    interpreter: str,
) -> dict[str, Any]:
    _set_thread_limits()
    w5 = config["w5"]
    if w5.get("policy_label") != "synthetic-fixture-only":
        _fail("reason=non-fixture-policy-rejected")
    if w5.get("never_use_w4_full_training_state_for_nested_cv") is not True:
        _fail("reason=w5-must-forbid-global-nested-cv-state")
    w4_state_path = w4_dir / "full_training_feature_state.json"
    if not w4_state_path.is_file():
        _fail("reason=missing-w4-full-training-state")
    w4_full_artifact_sha256 = sha256_file(w4_state_path)
    w4_full_payload = json_no_dups(w4_state_path.read_bytes())
    w4_full_state = FeatureState(w4_full_payload)
    if w4_full_payload.get("state_sha256") != w4_full_state.sha256:
        _fail("reason=w4-full-feature-state-hash-mismatch")
    w4_full_state_sha256 = w4_full_state.sha256
    policy = config["w4"]
    probe_map_path = repo_root / config["w3"]["annotation"]["probe_map_path"]
    provider = FoldFeatureProvider.from_cohort(
        w3_dir,
        policy,
        probe_map_path=probe_map_path,
        parent_hashes=parent_hashes,
        code_identity_sha256=code_identity,
    )
    development = config["w3"]["specimen_policy"]["development_cohort"]
    external = config["w3"]["specimen_policy"]["external_cohort"]
    candidates = _candidate_ids(provider, development)
    min_n = int(w5["min_development_n"])
    if len(candidates) < min_n:
        _fail(f"reason=insufficient-development-candidates n={len(candidates)} min={min_n}")
    program = list(policy["program_p"])
    continuous_cols, categorical_cols, extended_cols = ordered_feature_columns(w5)
    n_base_cont = len(continuous_cols)
    n_cat = len(categorical_cols)
    n_ext_cont = n_base_cont + len(extended_cols)
    model_cfg = _model_cfg()
    alpha_grid = list(RELEASED_ALPHA_GRID)
    n = len(candidates)
    outer_splits = _materialized_splits(n, 42)
    oof_baseline = {pid: float("nan") for pid in candidates}
    oof_extended = {pid: float("nan") for pid in candidates}
    fold_assign = {pid: -1 for pid in candidates}
    exclusions: list[list[Any]] = []
    tuning_rows: list[list[Any]] = []
    inner_state_hashes: list[dict[str, Any]] = []
    outer_metrics: list[dict[str, Any]] = []
    outer_alpha_baseline: list[float] = []
    outer_alpha_extended: list[float] = []

    work = stage_dir.parent / f"{stage_dir.name}.work"
    if work.exists():
        remove_tree(work)
    work.mkdir(parents=True)
    (work / "fold_states").mkdir()
    (work / "bundle").mkdir()

    def _fit_partition(train_ids: list[str], valid_ids: list[str], *, phase: str, outer: int, inner: int | None) -> tuple[FeatureState, list[dict[str, Any]], list[dict[str, Any]]]:
        state = provider.fit(train_ids)
        train_rows = provider.transform(train_ids, state)
        valid_rows = provider.transform(valid_ids, state)
        for row in train_rows + valid_rows:
            if not row["eligible"]:
                exclusions.append(
                    [
                        phase,
                        outer,
                        inner if inner is not None else -1,
                        row["patient_id"],
                        "train" if row["patient_id"] in train_ids else "valid",
                        row["exclusion_reason"],
                        state.sha256,
                        True,
                    ]
                )
        train_ok = [row for row in train_rows if row["eligible"]]
        valid_ok = [row for row in valid_rows if row["eligible"]]
        _require_counts(len(train_ok), len(valid_ok), phase=phase, outer=outer, inner=inner)
        return state, train_ok, valid_ok

    for outer_fold, (train_idx, valid_idx) in enumerate(outer_splits):
        outer_train_ids = [candidates[i] for i in train_idx]
        outer_valid_ids = [candidates[i] for i in valid_idx]
        inner_splits = _materialized_splits(len(outer_train_ids), 42)
        mean_mse_baseline: dict[float, list[float]] = {alpha: [] for alpha in alpha_grid}
        mean_mse_extended: dict[float, list[float]] = {alpha: [] for alpha in alpha_grid}
        fold_dir = work / "fold_states" / f"outer_{outer_fold}"
        fold_dir.mkdir()
        (fold_dir / "inner").mkdir()
        for inner_fold, (inner_train_local, inner_valid_local) in enumerate(inner_splits):
            inner_train_ids = [outer_train_ids[i] for i in inner_train_local]
            inner_valid_ids = [outer_train_ids[i] for i in inner_valid_local]
            inner_state, train_ok, valid_ok = _fit_partition(
                inner_train_ids, inner_valid_ids, phase="outer", outer=outer_fold, inner=inner_fold
            )
            atomic_write_json(
                fold_dir / "inner" / f"feature_state_{inner_fold}.json",
                inner_state.to_json(),
            )
            inner_state_hashes.append(
                {
                    "outer_fold": outer_fold,
                    "inner_fold": inner_fold,
                    "training_patient_ids": list(inner_state.payload["training_patient_ids"]),
                    "state_sha256": inner_state.sha256,
                    "eligible_probes_by_gene": inner_state.payload["eligible_probes_by_gene"],
                }
            )
            ids_t, y_t, c_t, d_t, e_t = encode_eligible_rows(
                train_ok, covariates=provider.covariates, w5=w5, program=program
            )
            ids_v, y_v, c_v, d_v, e_v = encode_eligible_rows(
                valid_ok, covariates=provider.covariates, w5=w5, program=program
            )
            b_scores = _score_alphas(c_t, d_t, y_t, c_v, d_v, y_v, n_base_cont, n_cat, alpha_grid, model_cfg)
            e_cont_t = np.concatenate([c_t, e_t], axis=1)
            e_cont_v = np.concatenate([c_v, e_v], axis=1)
            e_scores = _score_alphas(
                e_cont_t, d_t, y_t, e_cont_v, d_v, y_v, n_ext_cont, n_cat, alpha_grid, model_cfg
            )
            for alpha, mse in b_scores:
                mean_mse_baseline[alpha].append(mse)
                tuning_rows.append(
                    ["outer", "baseline", outer_fold, inner_fold, alpha, mse, len(ids_t), len(ids_v)]
                )
            for alpha, mse in e_scores:
                mean_mse_extended[alpha].append(mse)
                tuning_rows.append(
                    ["outer", "extended", outer_fold, inner_fold, alpha, mse, len(ids_t), len(ids_v)]
                )
        b_alpha = _select_alpha([(a, float(np.mean(v))) for a, v in mean_mse_baseline.items()])
        e_alpha = _select_alpha([(a, float(np.mean(v))) for a, v in mean_mse_extended.items()])
        outer_alpha_baseline.append(float(b_alpha))
        outer_alpha_extended.append(float(e_alpha))
        outer_state, train_ok, valid_ok = _fit_partition(
            outer_train_ids, outer_valid_ids, phase="outer-refit", outer=outer_fold, inner=None
        )
        atomic_write_json(fold_dir / "feature_state.json", outer_state.to_json())
        ids_t, y_t, c_t, d_t, e_t = encode_eligible_rows(
            train_ok, covariates=provider.covariates, w5=w5, program=program
        )
        ids_v, y_v, c_v, d_v, e_v = encode_eligible_rows(
            valid_ok, covariates=provider.covariates, w5=w5, program=program
        )
        train_index = np.arange(len(ids_t), dtype=np.int64)
        b_transform, b_coef, b_intercept, _ = _fit_model_for_indices(
            c_t, d_t, y_t, continuous_cols, categorical_cols, train_index, b_alpha, model_cfg
        )
        e_transform, e_coef, e_intercept, _ = _fit_model_for_indices(
            np.concatenate([c_t, e_t], axis=1),
            d_t,
            y_t,
            continuous_cols + extended_cols,
            categorical_cols,
            train_index,
            e_alpha,
            model_cfg,
        )
        b_pred = (
            _apply_transform(c_v, d_v, continuous_cols, categorical_cols, b_transform) @ b_coef
            + b_intercept
        )
        e_pred = (
            _apply_transform(
                np.concatenate([c_v, e_v], axis=1),
                d_v,
                continuous_cols + extended_cols,
                categorical_cols,
                e_transform,
            )
            @ e_coef
            + e_intercept
        )
        if len(ids_v) != len(valid_ok):
            _fail("reason=paired-patient-set-mismatch")
        fold_y = np.asarray(y_v, dtype=np.float64)
        fold_p0 = np.asarray(b_pred, dtype=np.float64)
        fold_p1 = np.asarray(e_pred, dtype=np.float64)
        outer_metrics.append(
            {
                "outer_fold": outer_fold,
                "feature_state_sha256": outer_state.sha256,
                "training_n": len(ids_t),
                "validation_n": len(ids_v),
                "selected_alpha_baseline": float(b_alpha),
                "selected_alpha_extended": float(e_alpha),
                "mse_baseline": _mse(fold_y, fold_p0),
                "mse_extended": _mse(fold_y, fold_p1),
                "r2_baseline": _r2(fold_y, fold_p0),
                "r2_extended": _r2(fold_y, fold_p1),
            }
        )
        for pid, p0, p1 in zip(ids_v, b_pred, e_pred):
            oof_baseline[pid] = float(p0)
            oof_extended[pid] = float(p1)
            fold_assign[pid] = outer_fold

    predicted = [pid for pid in candidates if fold_assign[pid] >= 0]
    if not predicted:
        _fail("reason=no-oof-predictions")

    final_inner = _materialized_splits(n, 42)
    mean_b: dict[float, list[float]] = {alpha: [] for alpha in alpha_grid}
    mean_e: dict[float, list[float]] = {alpha: [] for alpha in alpha_grid}
    final_inner_dir = work / "fold_states" / "final"
    final_inner_dir.mkdir()
    (final_inner_dir / "inner").mkdir()
    for inner_fold, (inner_train, inner_valid) in enumerate(final_inner):
        train_ids = [candidates[i] for i in inner_train]
        valid_ids = [candidates[i] for i in inner_valid]
        state, train_ok, valid_ok = _fit_partition(
            train_ids, valid_ids, phase="final", outer=-1, inner=inner_fold
        )
        atomic_write_json(
            final_inner_dir / "inner" / f"feature_state_{inner_fold}.json",
            state.to_json(),
        )
        ids_t, y_t, c_t, d_t, e_t = encode_eligible_rows(
            train_ok, covariates=provider.covariates, w5=w5, program=program
        )
        ids_v, y_v, c_v, d_v, e_v = encode_eligible_rows(
            valid_ok, covariates=provider.covariates, w5=w5, program=program
        )
        b_scores = _score_alphas(c_t, d_t, y_t, c_v, d_v, y_v, n_base_cont, n_cat, alpha_grid, model_cfg)
        e_scores = _score_alphas(
            np.concatenate([c_t, e_t], axis=1),
            d_t,
            y_t,
            np.concatenate([c_v, e_v], axis=1),
            d_v,
            y_v,
            n_ext_cont,
            n_cat,
            alpha_grid,
            model_cfg,
        )
        for alpha, mse in b_scores:
            mean_b[alpha].append(mse)
            tuning_rows.append(["final", "baseline", -1, inner_fold, alpha, mse, len(ids_t), len(ids_v)])
        for alpha, mse in e_scores:
            mean_e[alpha].append(mse)
            tuning_rows.append(["final", "extended", -1, inner_fold, alpha, mse, len(ids_t), len(ids_v)])
    final_b_alpha = _select_alpha([(a, float(np.mean(v))) for a, v in mean_b.items()])
    final_e_alpha = _select_alpha([(a, float(np.mean(v))) for a, v in mean_e.items()])
    final_state = provider.fit(candidates)
    atomic_write_json(work / "final_feature_state.json", final_state.to_json())
    atomic_write_json(work / "bundle" / "final_feature_state.json", final_state.to_json())
    final_rows = provider.transform(candidates, final_state)
    final_ok = [row for row in final_rows if row["eligible"]]
    if len(final_ok) < min_n:
        _fail(f"reason=insufficient-eligible-final n={len(final_ok)} min={min_n}")
    ids_f, y_f, c_f, d_f, e_f = encode_eligible_rows(
        final_ok, covariates=provider.covariates, w5=w5, program=program
    )
    idx_all = np.arange(len(ids_f), dtype=np.int64)
    b_transform, b_coef, b_intercept, _ = _fit_model_for_indices(
        c_f, d_f, y_f, continuous_cols, categorical_cols, idx_all, final_b_alpha, model_cfg
    )
    e_transform, e_coef, e_intercept, _ = _fit_model_for_indices(
        np.concatenate([c_f, e_f], axis=1),
        d_f,
        y_f,
        continuous_cols + extended_cols,
        categorical_cols,
        idx_all,
        final_e_alpha,
        model_cfg,
    )
    baseline_model = _build_model_json(
        "baseline", continuous_cols, categorical_cols, b_transform, b_coef, b_intercept, final_b_alpha, len(ids_f)
    )
    extended_model = _build_model_json(
        "extended",
        continuous_cols + extended_cols,
        categorical_cols,
        e_transform,
        e_coef,
        e_intercept,
        final_e_alpha,
        len(ids_f),
    )
    baseline_model["feature_state_sha256"] = final_state.sha256
    extended_model["feature_state_sha256"] = final_state.sha256
    oof_ids = [pid for pid in candidates if fold_assign[pid] >= 0]
    y_oof = np.array(
        [float(provider.transform([pid], final_state)[0]["Y"]) for pid in oof_ids],
        dtype=np.float64,
    )
    # OOF metrics must use the Y from fold-local transform, not final state Y.
    # Y is sample-wise so it matches. Predictions come from oof maps.
    y_oof = []
    p0_oof = []
    p1_oof = []
    for pid in oof_ids:
        row = next(r for r in final_rows if r["patient_id"] == pid)
        y_oof.append(float(row["Y"]))
        p0_oof.append(oof_baseline[pid])
        p1_oof.append(oof_extended[pid])
    y_arr = np.asarray(y_oof, dtype=np.float64)
    p0_arr = np.asarray(p0_oof, dtype=np.float64)
    p1_arr = np.asarray(p1_oof, dtype=np.float64)
    sst = float(np.sum((y_arr - np.mean(y_arr, dtype=np.float64)) ** 2, dtype=np.float64))
    sse0 = float(np.sum((y_arr - p0_arr) ** 2, dtype=np.float64))
    sse1 = float(np.sum((y_arr - p1_arr) ** 2, dtype=np.float64))
    w3_checksums = sha256_file(w3_dir / "checksums.json")
    development_sha = sha256_bytes(
        canonical_json_bytes({"w3_checksums": w3_checksums, "candidates": candidates})
    )
    contract_payload = _synthetic_contract_payload(w5, development_sha, development, external)
    contract_bytes = _canonical_json_bytes(contract_payload)
    contract_sha = _sha256(contract_bytes)
    development_metrics = {
        "schema_version": "B-W5-development-metrics-1",
        "purpose": "synthetic-test",
        "synthetic": True,
        "contract_sha256": contract_sha,
        "n_candidates": n,
        "n_oof": len(oof_ids),
        "final_feature_state_sha256": final_state.sha256,
        "w4_full_training_state_sha256": w4_full_state_sha256,
        "w4_full_training_state_artifact_sha256": w4_full_artifact_sha256,
        "used_w4_full_state_for_nested_cv": False,
        "outer_folds": outer_metrics,
        "pooled": {
            "sse_baseline": sse0,
            "sse_extended": sse1,
            "sst": sst,
            "r2_baseline": None if sst == 0.0 else 1.0 - sse0 / sst,
            "r2_extended": None if sst == 0.0 else 1.0 - sse1 / sst,
            "delta_r2": None if sst == 0.0 else (sse0 - sse1) / sst,
        },
    }
    patient_hashes = [_sha256(pid.encode("utf-8")) for pid in candidates]
    bundle_manifest = {
        "schema_version": "B-W5-bundle-manifest-1",
        "purpose": "synthetic-test",
        "synthetic": True,
        "synthetic_label": "SYNTHETIC FIXTURE ONLY. Not a TCGA scientific fit.",
        "contract": contract_payload,
        "development_sha256": development_sha,
        "contract_sha256": contract_sha,
        "development_patient_count": len(candidates),
        "development_patient_id_hashes": patient_hashes,
        "development_patient_set_hash": _sha256(_canonical_json_bytes(patient_hashes)),
        "engine_code_sha256": _engine_code_sha256(),
        "final_feature_state_sha256": final_state.sha256,
        "w4_full_training_state_sha256": w4_full_state_sha256,
        "w4_full_training_state_artifact_sha256": w4_full_artifact_sha256,
        "used_w4_full_state_for_nested_cv": False,
        "selected_alpha": {
            "baseline_outer_median": float(np.median(outer_alpha_baseline)),
            "extended_outer_median": float(np.median(outer_alpha_extended)),
            "baseline_final": float(final_b_alpha),
            "extended_final": float(final_e_alpha),
        },
        "outer_folds": 5,
        "cv_random_state": 42,
        "code_identity_sha256": code_identity,
        "runtime": _runtime_receipt(),
    }
    bundle = work / "bundle"
    _atomic_write_json(bundle / "bundle_manifest.json", bundle_manifest)
    _atomic_write_json(bundle / "baseline_model.json", baseline_model)
    _atomic_write_json(bundle / "extended_model.json", extended_model)
    _atomic_write_json(bundle / "development_metrics.json", development_metrics)
    _atomic_write_json(bundle / "contract.json", contract_payload)
    _atomic_write_tsv(
        bundle / "fold_assignments.tsv",
        [[pid, str(fold_assign[pid])] for pid in candidates],
        ["patient_id", "outer_fold"],
    )
    _atomic_write_tsv(
        bundle / "oof_predictions.tsv",
        [
            [
                pid,
                str(float(y)),
                str(float(p0)),
                str(float(p1)),
                str(float((y - p0) ** 2)),
                str(float((y - p1) ** 2)),
            ]
            for pid, y, p0, p1 in zip(oof_ids, y_arr, p0_arr, p1_arr)
        ],
        ["patient_id", "Y", "f0", "f1", "sse_baseline", "sse_extended"],
    )
    _atomic_write_tsv(
        bundle / "tuning_results.tsv",
        [[str(v) for v in row] for row in tuning_rows],
        ["phase", "model", "outer_fold", "inner_fold", "alpha", "mse", "train_n", "valid_n"],
    )
    bundle_payloads = {
        "bundle_manifest.json": bundle / "bundle_manifest.json",
        "baseline_model.json": bundle / "baseline_model.json",
        "extended_model.json": bundle / "extended_model.json",
        "development_metrics.json": bundle / "development_metrics.json",
        "contract.json": bundle / "contract.json",
        "fold_assignments.tsv": bundle / "fold_assignments.tsv",
        "oof_predictions.tsv": bundle / "oof_predictions.tsv",
        "tuning_results.tsv": bundle / "tuning_results.tsv",
        "final_feature_state.json": bundle / "final_feature_state.json",
    }
    bundle_checksums = {
        "schema_version": "B-W5-bundle-checksums-1",
        "files": {name: sha256_file(path) for name, path in bundle_payloads.items()},
        "contract_sha256": contract_sha,
        "development_sha256": development_sha,
        "final_feature_state_sha256": final_state.sha256,
        "code_identity_sha256": code_identity,
    }
    _atomic_write_json(bundle / "checksums.json", bundle_checksums)
    bundle_sha256 = sha256_file(bundle / "checksums.json")
    _atomic_write_json(
        bundle / "COMPLETE.json",
        {
            "schema_version": "B-W5-bundle-complete-1",
            "status": "complete",
            "bundle_hash": bundle_sha256,
            "checksum_manifest": "checksums.json",
            "final_feature_state_sha256": final_state.sha256,
        },
    )
    _atomic_write_tsv(
        work / "fold_exclusions.tsv",
        [[str(value) for value in row] for row in exclusions],
        ["phase", "outer_fold", "inner_fold", "patient_id", "split_role", "exclusion_reason", "feature_state_sha256", "synthetic"],
    )
    _atomic_write_json(work / "inner_feature_states.json", inner_state_hashes)
    payload_files = {
        "bundle/bundle_manifest.json": bundle / "bundle_manifest.json",
        "bundle/baseline_model.json": bundle / "baseline_model.json",
        "bundle/extended_model.json": bundle / "extended_model.json",
        "bundle/development_metrics.json": bundle / "development_metrics.json",
        "bundle/contract.json": bundle / "contract.json",
        "bundle/fold_assignments.tsv": bundle / "fold_assignments.tsv",
        "bundle/oof_predictions.tsv": bundle / "oof_predictions.tsv",
        "bundle/tuning_results.tsv": bundle / "tuning_results.tsv",
        "bundle/final_feature_state.json": bundle / "final_feature_state.json",
        "bundle/checksums.json": bundle / "checksums.json",
        "bundle/COMPLETE.json": bundle / "COMPLETE.json",
        "final_feature_state.json": work / "final_feature_state.json",
        "fold_exclusions.tsv": work / "fold_exclusions.tsv",
        "inner_feature_states.json": work / "inner_feature_states.json",
    }
    artifact_hashes = {rel: sha256_file(path) for rel, path in payload_files.items()}
    for path in sorted((work / "fold_states").rglob("feature_state*.json")):
        rel = path.relative_to(work).as_posix()
        artifact_hashes[rel] = sha256_file(path)
    scientific = {
        "schema_version": "B-W5-manifest-v1",
        "stage": "W5",
        "synthetic": True,
        "synthetic_label": "SYNTHETIC FIXTURE ONLY. Not a scientific TCGA model.",
        "parent_hashes": parent_hashes,
        "code_identity_sha256": code_identity,
        "interpreter": interpreter,
        "final_feature_state_sha256": final_state.sha256,
        "bundle_sha256": bundle_sha256,
        "w4_full_training_state_sha256": w4_full_state_sha256,
        "w4_full_training_state_artifact_sha256": w4_full_artifact_sha256,
        "used_w4_full_state_for_nested_cv": False,
        "n_development_candidates": n,
        "n_oof": len(oof_ids),
        "artifact_hashes": artifact_hashes,
        "policy_label": w5["policy_label"],
    }
    atomic_write_json(work / "checksums.json", scientific)
    artifact_hashes["checksums.json"] = sha256_file(work / "checksums.json")
    manifest = dict(scientific)
    manifest["created_utc"] = utc_stamp()
    manifest["artifact_hashes"] = artifact_hashes
    atomic_write_json(work / "manifest.json", manifest)
    complete = {
        "stage": "W5",
        "status": "complete",
        "synthetic": True,
        "checksums_sha256": artifact_hashes["checksums.json"],
        "manifest_sha256": sha256_file(work / "manifest.json"),
        "parent_hashes": parent_hashes,
        "code_identity_sha256": code_identity,
        "final_feature_state_sha256": final_state.sha256,
        "bundle_sha256": bundle_sha256,
        "pipeline_complete": False,
    }
    atomic_write_json(work / "COMPLETE.json", complete)
    publish_directory(work, stage_dir)
    return json_no_dups((stage_dir / "manifest.json").read_bytes())
