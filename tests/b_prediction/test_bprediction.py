"""Acceptance tests for B-P1 released prediction engine."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON = [sys.executable, "-m", "tools.b_prediction"]
TIMEOUT = 120

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures"
CONTRACT_FIXTURE = FIXTURE_ROOT / "synthetic_contract.json"
DEV_FIXTURE = FIXTURE_ROOT / "synthetic_development.tsv"
EXT_FIXTURE = FIXTURE_ROOT / "synthetic_external.tsv"
OVERLAP_FIXTURE = FIXTURE_ROOT / "synthetic_external_overlap.tsv"
LOCK_FIXTURE = FIXTURE_ROOT / "synthetic_evaluation_lock.json"


def _tmp_root() -> Path:
    explicit = os.environ.get("BP1_TEST_TMP_ROOT")
    if explicit:
        return Path(explicit)
    fallback = Path(__file__).resolve().parents[2] / "tmp" / "b_prediction"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def _run_env() -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
            "VECLIB_MAXIMUM_THREADS": "1",
        }
    )
    return env


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_cmd(args: list[str], cwd: Path) -> tuple[int, str, str]:
    completed = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, timeout=TIMEOUT, env=_run_env())
    return completed.returncode, completed.stdout, completed.stderr


def _has_sklearn() -> bool:
    try:
        import sklearn  # noqa: F401

        return True
    except Exception:
        return False


def _write_contract_with_hash(target: Path, development_hash: str) -> None:
    payload = json.loads(CONTRACT_FIXTURE.read_text(encoding="utf-8"))
    payload["development_sha256"] = development_hash
    target.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_lock(target: Path, contract_hash: str, bundle_hash: str, external_hash: str, status: str = "synthetic-only") -> dict:
    payload = json.loads(LOCK_FIXTURE.read_text(encoding="utf-8"))
    payload["contract_sha256"] = contract_hash
    payload["bundle_sha256"] = bundle_hash
    payload["external_sha256"] = external_hash
    payload["status"] = status
    target.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )
    return payload


class BP1AcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.has_sklearn = _has_sklearn()

    def setUp(self) -> None:
        self.tmp_root = _tmp_root()
        self.tmp_root.mkdir(parents=True, exist_ok=True)

    def test_cli_help_and_contract_schema_fields(self) -> None:
        rc, stdout, stderr = _run_cmd([*PYTHON, "develop", "--help"], REPO_ROOT)
        self.assertEqual(rc, 0, stderr)
        self.assertIn("develop", stdout + stderr)
        self.assertIn("--development", stdout + stderr)
        self.assertNotIn("--external", stdout + stderr)

        bad_contract = self.tmp_root / "invalid_contract.json"
        bad_contract.write_text(json.dumps({"schema_version": "B-P1-contract-1", "purpose": "synthetic-test"}), encoding="utf-8")
        rc, _, err = _run_cmd(
            [
                *PYTHON,
                "develop",
                "--contract",
                str(bad_contract),
                "--development",
                str(DEV_FIXTURE),
                "--output",
                str(self.tmp_root / "invalid"),
            ],
            REPO_ROOT,
        )
        self.assertNotEqual(rc, 0)
        self.assertIn("contract-json reason=missing-field", err)

    @unittest.skipUnless(_has_sklearn(), "AIU/host runtime does not expose sklearn")
    def test_develop_evaluate_happy_path_and_deterministic_bundle(self) -> None:
        with tempfile.TemporaryDirectory(dir=self.tmp_root) as td:
            temp = Path(td)
            contract_path = temp / "contract.json"
            _write_contract_with_hash(contract_path, _sha256(DEV_FIXTURE))

            develop_one = temp / "develop_one"
            rc, _, err = _run_cmd(
                [*PYTHON, "develop", "--contract", str(contract_path), "--development", str(DEV_FIXTURE), "--output", str(develop_one)],
                REPO_ROOT,
            )
            self.assertEqual(rc, 0, err)

            bundle = develop_one / "bundle"
            complete = _load_json(bundle / "COMPLETE.json")
            checksums_one = _load_json(bundle / "checksums.json")
            manifest_one = _load_json(bundle / "bundle_manifest.json")
            self.assertIn("bundle_hash", complete)
            self.assertEqual(manifest_one["schema_version"], "B-P1-bundle-manifest-1")

            lock = temp / "lock.json"
            _build_lock(lock, manifest_one["contract_sha256"], complete["bundle_hash"], _sha256(EXT_FIXTURE))

            eval_out = temp / "eval"
            rc, _, err = _run_cmd(
                [
                    *PYTHON,
                    "evaluate",
                    "--bundle",
                    str(bundle),
                    "--evaluation-lock",
                    str(lock),
                    "--external",
                    str(EXT_FIXTURE),
                    "--output",
                    str(eval_out),
                ],
                REPO_ROOT,
            )
            self.assertEqual(rc, 0, err)
            eval_payload = _load_json(eval_out / "evaluation.json")
            self.assertEqual(eval_payload["metrics"]["status"], "defined")
            self.assertEqual(eval_payload["contract_sha256"], manifest_one["contract_sha256"])
            self.assertEqual(eval_payload["bundle_hash"], complete["bundle_hash"])
            self.assertEqual(eval_payload["evaluation_lock_sha256"], _sha256(lock))
            self.assertEqual(eval_payload["external_sha256"], _sha256(EXT_FIXTURE))
            self.assertIn("python_version", manifest_one["runtime"])
            self.assertEqual(_load_json(bundle / "baseline_model.json")["solver_"], "svd")
            self.assertEqual(_load_json(bundle / "extended_model.json")["solver_"], "svd")

            lines = DEV_FIXTURE.read_text(encoding="utf-8").splitlines()
            header, rows = lines[0], lines[1:]
            shuffled_dev = temp / "dev_shuffled.tsv"
            shuffled_dev.write_text("\n".join([header] + rows[::-1]) + "\n", encoding="utf-8")
            _write_contract_with_hash(contract_path, _sha256(shuffled_dev))

            develop_two = temp / "develop_two"
            rc, _, err = _run_cmd(
                [*PYTHON, "develop", "--contract", str(contract_path), "--development", str(shuffled_dev), "--output", str(develop_two)],
                REPO_ROOT,
            )
            self.assertEqual(rc, 0, err)

            def _model_state(path: Path) -> dict:
                payload = _load_json(path)
                return {
                    "alpha": payload["alpha"],
                    "coefficients": payload["coefficients"],
                    "intercept": payload["intercept"],
                    "dropped": payload["dropped_constant_columns"],
                    "retained": payload["retained_feature_names"],
                    "means": payload["continuous_means"],
                    "scales": payload["continuous_scales"],
                    "solver_": payload.get("solver_"),
                }

            self.assertEqual(
                (develop_one / "bundle" / "fold_assignments.tsv").read_bytes(),
                (develop_two / "bundle" / "fold_assignments.tsv").read_bytes(),
            )
            self.assertEqual(
                (develop_one / "bundle" / "oof_predictions.tsv").read_bytes(),
                (develop_two / "bundle" / "oof_predictions.tsv").read_bytes(),
            )
            self.assertEqual(
                (develop_one / "bundle" / "tuning_results.tsv").read_bytes(),
                (develop_two / "bundle" / "tuning_results.tsv").read_bytes(),
            )
            self.assertEqual(
                _model_state(develop_one / "bundle" / "baseline_model.json"),
                _model_state(develop_two / "bundle" / "baseline_model.json"),
            )
            self.assertEqual(
                _model_state(develop_one / "bundle" / "extended_model.json"),
                _model_state(develop_two / "bundle" / "extended_model.json"),
            )
            self.assertEqual(
                _load_json(develop_one / "bundle" / "bundle_manifest.json")["selected_alpha"],
                _load_json(develop_two / "bundle" / "bundle_manifest.json")["selected_alpha"],
            )
            self.assertEqual(
                _load_json(develop_one / "bundle" / "development_metrics.json")["pooled"],
                _load_json(develop_two / "bundle" / "development_metrics.json")["pooled"],
            )
            checksums_two = _load_json(develop_two / "bundle" / "checksums.json")
            self.assertEqual(set(checksums_one["files"]), set(checksums_two["files"]))

    @unittest.skipUnless(_has_sklearn(), "AIU/host runtime does not expose sklearn")
    def test_lock_validation_and_external_overlap(self) -> None:
        with tempfile.TemporaryDirectory(dir=self.tmp_root) as td:
            temp = Path(td)
            contract_path = temp / "contract.json"
            _write_contract_with_hash(contract_path, _sha256(DEV_FIXTURE))
            out = temp / "develop"
            rc, _, err = _run_cmd(
                [*PYTHON, "develop", "--contract", str(contract_path), "--development", str(DEV_FIXTURE), "--output", str(out)],
                REPO_ROOT,
            )
            self.assertEqual(rc, 0, err)

            bundle = out / "bundle"
            complete = _load_json(bundle / "COMPLETE.json")
            manifest = _load_json(bundle / "bundle_manifest.json")

            lock_bad_status = temp / "lock_bad_status.json"
            _build_lock(lock_bad_status, manifest["contract_sha256"], complete["bundle_hash"], _sha256(EXT_FIXTURE), status="approved")
            rc, _, err = _run_cmd(
                [
                    *PYTHON,
                    "evaluate",
                    "--bundle",
                    str(bundle),
                    "--evaluation-lock",
                    str(lock_bad_status),
                    "--external",
                    str(EXT_FIXTURE),
                    "--output",
                    str(temp / "eval_bad"),
                ],
                REPO_ROOT,
            )
            self.assertNotEqual(rc, 0)
            self.assertIn("evaluation-lock", err)

            lock_overlap = temp / "lock_overlap.json"
            _build_lock(lock_overlap, manifest["contract_sha256"], complete["bundle_hash"], _sha256(OVERLAP_FIXTURE), status="synthetic-only")
            rc, _, err = _run_cmd(
                [
                    *PYTHON,
                    "evaluate",
                    "--bundle",
                    str(bundle),
                    "--evaluation-lock",
                    str(lock_overlap),
                    "--external",
                    str(OVERLAP_FIXTURE),
                    "--output",
                    str(temp / "eval_overlap"),
                ],
                REPO_ROOT,
            )
            self.assertNotEqual(rc, 0)
            self.assertIn("overlap", err)

    def test_select_alpha_tie_rule(self) -> None:
        from tools.b_prediction.__main__ import _select_alpha

        candidate_rows = [(0.1, 1.0), (1.0, 0.5), (10.0, 0.5), (100.0, 0.9)]
        self.assertEqual(_select_alpha(candidate_rows), 10.0)
        near_tie = [(1.0, 0.5), (10.0, 0.5 + 5e-13), (100.0, 0.6)]
        self.assertEqual(_select_alpha(near_tie), 1.0)

    @unittest.skipUnless(_has_sklearn(), "AIU/host runtime does not expose sklearn")
    def test_no_refit_predictor_path(self) -> None:
        with tempfile.TemporaryDirectory(dir=self.tmp_root) as td:
            temp = Path(td)
            contract_path = temp / "contract.json"
            _write_contract_with_hash(contract_path, _sha256(DEV_FIXTURE))
            out = temp / "develop"
            rc, _, err = _run_cmd(
                [*PYTHON, "develop", "--contract", str(contract_path), "--development", str(DEV_FIXTURE), "--output", str(out)],
                REPO_ROOT,
            )
            self.assertEqual(rc, 0, err)

            bundle = out / "bundle"
            complete = _load_json(bundle / "COMPLETE.json")
            manifest = _load_json(bundle / "bundle_manifest.json")
            lock = temp / "lock.json"
            _build_lock(lock, manifest["contract_sha256"], complete["bundle_hash"], _sha256(EXT_FIXTURE))

            fake_lib = temp / "fake_sklearn"
            (fake_lib / "sklearn").mkdir(parents=True)
            (fake_lib / "sklearn" / "__init__.py").write_text(
                "raise RuntimeError('should not import in evaluate')",
                encoding="utf-8",
            )

            env = _run_env()
            env["PYTHONPATH"] = str(fake_lib) + os.pathsep + env.get("PYTHONPATH", "")
            completed = subprocess.run(
                [
                    *PYTHON,
                    "evaluate",
                    "--bundle",
                    str(bundle),
                    "--evaluation-lock",
                    str(lock),
                    "--external",
                    str(EXT_FIXTURE),
                    "--output",
                    str(temp / "eval"),
                ],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=TIMEOUT,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_bootstrap_constant_target(self) -> None:
        from tools.b_prediction.__main__ import _bootstrap_delta, RELEASED_BOOTSTRAP

        import numpy as np

        y = np.ones(5, dtype=np.float64)
        f0 = np.arange(5, dtype=np.float64)
        f1 = f0 + 1.0
        output = _bootstrap_delta(y, f0, f1, RELEASED_BOOTSTRAP)
        self.assertEqual(output["status"], "undefined")
        self.assertIsNone(output["r2_baseline"])
        self.assertEqual(output["bootstrap"]["status"], "undefined")
        self.assertIsNone(output["bootstrap"]["delta_ci_lower"])
        self.assertIsNone(output["bootstrap"]["delta_ci_upper"])
        self.assertEqual(output["bootstrap"]["undefined_count"], RELEASED_BOOTSTRAP["resamples"])

    def test_schema_identity_failures(self) -> None:
        from tools.b_prediction.__main__ import EXIT_SCHEMA

        with tempfile.TemporaryDirectory(dir=self.tmp_root) as td:
            temp = Path(td)
            header = DEV_FIXTURE.read_text(encoding="utf-8").splitlines()[0]
            rows = DEV_FIXTURE.read_text(encoding="utf-8").splitlines()[1:]

            def run_dev(table_text: str, sha: str | None = None) -> tuple[int, str]:
                table = temp / "table.tsv"
                table.write_text(table_text, encoding="utf-8")
                contract_path = temp / "contract.json"
                _write_contract_with_hash(contract_path, sha if sha is not None else _sha256(table))
                out = temp / f"out_{len(list(temp.glob('out_*')))}"
                rc, _, err = _run_cmd(
                    [*PYTHON, "develop", "--contract", str(contract_path), "--development", str(table), "--output", str(out)],
                    REPO_ROOT,
                )
                self.assertFalse((out / "bundle" / "COMPLETE.json").exists())
                return rc, err

            rc, err = run_dev("\n".join([header] + rows) + "\n", sha="0" * 64)
            self.assertEqual(rc, EXIT_SCHEMA)
            self.assertIn("hash mismatch", err)

            dup_rows = rows + [rows[0]]
            rc, err = run_dev("\n".join([header] + dup_rows) + "\n")
            self.assertEqual(rc, EXIT_SCHEMA)
            self.assertIn("duplicate-patient-id", err)

            unknown_header = header + "\textra"
            unknown_rows = [row + "\t0.1" for row in rows]
            rc, err = run_dev("\n".join([unknown_header] + unknown_rows) + "\n")
            self.assertEqual(rc, EXIT_SCHEMA)
            self.assertIn("header mismatch", err)

            na_rows = list(rows)
            parts = na_rows[0].split("\t")
            parts[2] = "NA"
            na_rows[0] = "\t".join(parts)
            rc, err = run_dev("\n".join([header] + na_rows) + "\n")
            self.assertEqual(rc, EXIT_SCHEMA)
            self.assertIn("non-finite", err)

            dummy_rows = list(rows)
            parts = dummy_rows[0].split("\t")
            parts[4] = "1"
            parts[5] = "1"
            dummy_rows[0] = "\t".join(parts)
            rc, err = run_dev("\n".join([header] + dummy_rows) + "\n")
            self.assertEqual(rc, EXIT_SCHEMA)
            self.assertIn("non-exclusive-dummies", err)

            role_rows = list(rows)
            parts = role_rows[0].split("\t")
            parts[0] = "CPC-GENE"
            role_rows[0] = "\t".join(parts)
            rc, err = run_dev("\n".join([header] + role_rows) + "\n")
            self.assertEqual(rc, EXIT_SCHEMA)
            self.assertIn("role-mismatch", err)

            rc, err = run_dev("\n".join([header] + rows[:6]) + "\n")
            self.assertEqual(rc, EXIT_SCHEMA)
            self.assertIn("at least 7", err)

            lock_payload = json.loads(CONTRACT_FIXTURE.read_text(encoding="utf-8"))
            lock_payload["development_sha256"] = _sha256(DEV_FIXTURE)
            lock_payload["scientific_lock"]["feature_selection_provenance"] = "CPC-derived"
            marked = temp / "marked_contract.json"
            marked.write_text(json.dumps(lock_payload, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            rc, _, err = _run_cmd(
                [
                    *PYTHON,
                    "develop",
                    "--contract",
                    str(marked),
                    "--development",
                    str(DEV_FIXTURE),
                    "--output",
                    str(temp / "marked_out"),
                ],
                REPO_ROOT,
            )
            self.assertEqual(rc, EXIT_SCHEMA)
            self.assertIn("scientific-lock", err)
            self.assertFalse((temp / "marked_out" / "bundle" / "COMPLETE.json").exists())

    @unittest.skipUnless(_has_sklearn(), "AIU/host runtime does not expose sklearn")
    def test_fold_locality_and_shared_splits(self) -> None:
        from tools.b_prediction.__main__ import _combined_design, _make_ridge_pipeline, _materialized_splits
        import numpy as np

        n = 10
        continuous = np.arange(n, dtype=np.float64).reshape(-1, 1)
        categorical = np.array([[1.0, 0.0] if i % 2 == 0 else [0.0, 1.0] for i in range(n)], dtype=np.float64)
        y = np.linspace(0.0, 1.0, n, dtype=np.float64)
        train_idx = np.array([0, 1, 2, 3, 4, 5], dtype=np.int64)
        model_cfg = {
            "fit_intercept": True,
            "solver": "svd",
            "tol": 0.0001,
            "copy_X": True,
            "positive": False,
            "max_iter": None,
        }
        x = _combined_design(continuous, categorical)
        first = _make_ridge_pipeline(1.0, model_cfg, 1, 2)
        first.fit(x[train_idx], y[train_idx])
        first_mean = first.named_steps["preprocessor"].named_transformers_["continuous"].mean_.copy()
        first_scale = first.named_steps["preprocessor"].named_transformers_["continuous"].scale_.copy()
        first_support = first.named_steps["variance"].get_support().copy()

        mutated_valid = x.copy()
        mutated_valid[9, 0] = 10_000.0
        second = _make_ridge_pipeline(1.0, model_cfg, 1, 2)
        second.fit(mutated_valid[train_idx], y[train_idx])
        np.testing.assert_array_equal(first_mean, second.named_steps["preprocessor"].named_transformers_["continuous"].mean_)
        np.testing.assert_array_equal(first_scale, second.named_steps["preprocessor"].named_transformers_["continuous"].scale_)
        np.testing.assert_array_equal(first_support, second.named_steps["variance"].get_support())

        mutated_train = x.copy()
        mutated_train[0, 0] = 10_000.0
        third = _make_ridge_pipeline(1.0, model_cfg, 1, 2)
        third.fit(mutated_train[train_idx], y[train_idx])
        self.assertFalse(
            np.allclose(first_mean, third.named_steps["preprocessor"].named_transformers_["continuous"].mean_)
        )

        splits_a = _materialized_splits(8, 42)
        splits_b = _materialized_splits(8, 42)
        self.assertEqual(len(splits_a), 5)
        for (train_a, valid_a), (train_b, valid_b) in zip(splits_a, splits_b):
            np.testing.assert_array_equal(train_a, train_b)
            np.testing.assert_array_equal(valid_a, valid_b)

    @unittest.skipUnless(_has_sklearn(), "AIU/host runtime does not expose sklearn")
    def test_separate_tuning_and_zero_predictor_failure(self) -> None:
        from tools.b_prediction.__main__ import (
            EXIT_NUMERIC,
            Failure,
            RELEASED_ALPHA_GRID,
            _materialized_splits,
            _tune_model,
        )
        import numpy as np

        model_cfg = {
            "type": "ridge",
            "continuous_scaler": "standard",
            "fit_intercept": True,
            "solver": "svd",
            "tol": 0.0001,
            "copy_X": True,
            "positive": False,
            "max_iter": None,
        }
        n = 12
        y = np.linspace(-2.0, 2.0, n, dtype=np.float64)
        rng = np.random.default_rng(0)
        baseline_cont = rng.normal(scale=0.01, size=(n, 1))
        extended_cont = np.concatenate([baseline_cont, y.reshape(-1, 1)], axis=1)
        cat = np.zeros((n, 0), dtype=np.float64)
        splits = _materialized_splits(n, 42)
        baseline_alpha, _ = _tune_model(
            baseline_cont, cat, y, ["noise"], [], splits, RELEASED_ALPHA_GRID, model_cfg, "final", -1, "baseline"
        )
        extended_alpha, _ = _tune_model(
            extended_cont, cat, y, ["noise", "signal"], [], splits, RELEASED_ALPHA_GRID, model_cfg, "final", -1, "extended"
        )
        self.assertNotEqual(baseline_alpha, extended_alpha)

        constant_cont = np.ones((n, 1), dtype=np.float64)
        constant_cat = np.ones((n, 1), dtype=np.float64)
        with self.assertRaises(Failure) as raised:
            _tune_model(
                constant_cont,
                constant_cat,
                y,
                ["c"],
                ["d"],
                splits,
                RELEASED_ALPHA_GRID,
                model_cfg,
                "final",
                -1,
                "baseline",
            )
        self.assertEqual(raised.exception.code, EXIT_NUMERIC)

    @unittest.skipUnless(_has_sklearn(), "AIU/host runtime does not expose sklearn")
    def test_model_oracle_ridge_scaling_and_unpenalized_intercept(self) -> None:
        from tools.b_prediction.__main__ import _apply_transform, _fit_model_for_indices
        import numpy as np

        model_cfg = {
            "fit_intercept": True,
            "solver": "svd",
            "tol": 0.0001,
            "copy_X": True,
            "positive": False,
            "max_iter": None,
        }
        continuous = np.array([[1.0], [2.0], [3.0], [4.0], [5.0], [6.0], [7.0], [8.0]], dtype=np.float64)
        categorical = np.array(
            [[1.0, 0.0], [0.0, 1.0], [1.0, 0.0], [0.0, 1.0], [1.0, 0.0], [0.0, 1.0], [1.0, 0.0], [0.0, 1.0]],
            dtype=np.float64,
        )
        y = np.array([1.0, 2.2, 2.8, 4.1, 5.0, 6.2, 6.9, 8.1], dtype=np.float64)
        idx = np.arange(8, dtype=np.int64)
        transform, coef, intercept, estimator = _fit_model_for_indices(
            continuous, categorical, y, ["age"], ["sex_F", "sex_M"], idx, 1.0, model_cfg
        )
        x = _apply_transform(continuous, categorical, ["age"], ["sex_F", "sex_M"], transform)
        self.assertTrue(x.flags["C_CONTIGUOUS"])
        self.assertEqual(x.dtype, np.float64)
        expected_mean = float(np.mean(continuous[:, 0]))
        expected_scale = float(np.std(continuous[:, 0], ddof=0))
        self.assertAlmostEqual(transform.means["age"], expected_mean)
        self.assertAlmostEqual(transform.scales["age"], expected_scale)

        def closed_form(x_design: np.ndarray, target: np.ndarray, alpha: float) -> tuple[np.ndarray, float]:
            target = np.ascontiguousarray(target, dtype=np.float64)
            x_design = np.ascontiguousarray(x_design, dtype=np.float64)
            y_mean = float(np.mean(target))
            x_mean = np.mean(x_design, axis=0)
            y_c = target - y_mean
            x_c = x_design - x_mean
            gram = x_c.T @ x_c + alpha * np.eye(x_design.shape[1], dtype=np.float64)
            beta = np.linalg.solve(gram, x_c.T @ y_c)
            intercept_hat = y_mean - float(x_mean @ beta)
            return beta.astype(np.float64), intercept_hat

        beta, intercept_hat = closed_form(x, y, 1.0)
        np.testing.assert_allclose(coef, beta, rtol=0, atol=1e-10)
        self.assertAlmostEqual(intercept, intercept_hat, places=10)
        self.assertEqual(estimator.solver_, "svd")
        np.testing.assert_allclose(x @ coef + intercept, x @ beta + intercept_hat, rtol=0, atol=1e-10)

        _, coef_shift, intercept_shift, _ = _fit_model_for_indices(
            continuous, categorical, y + 5.0, ["age"], ["sex_F", "sex_M"], idx, 1.0, model_cfg
        )
        np.testing.assert_allclose(coef_shift, coef, rtol=0, atol=1e-10)
        self.assertAlmostEqual(intercept_shift - intercept, 5.0, places=10)
        beta_shift, intercept_shift_hat = closed_form(x, y + 5.0, 1.0)
        np.testing.assert_allclose(coef_shift, beta_shift, rtol=0, atol=1e-10)
        self.assertAlmostEqual(intercept_shift, intercept_shift_hat, places=10)

    def test_metric_oracle_delta_r2_signs_and_undefined(self) -> None:
        from tools.b_prediction.__main__ import RELEASED_BOOTSTRAP, _bootstrap_delta
        import numpy as np

        y = np.array([1.0, 2.0, 3.0], dtype=np.float64)
        equal = np.array([0.0, 2.0, 4.0], dtype=np.float64)
        perfect = np.array([1.0, 2.0, 3.0], dtype=np.float64)
        worse = np.array([10.0, 10.0, 10.0], dtype=np.float64)
        sst = 2.0
        sse_equal = 2.0
        improved = _bootstrap_delta(y, equal, perfect, RELEASED_BOOTSTRAP)
        self.assertEqual(improved["status"], "defined")
        self.assertAlmostEqual(improved["sst"], sst)
        self.assertAlmostEqual(improved["sse_baseline"], sse_equal)
        self.assertAlmostEqual(improved["sse_extended"], 0.0)
        self.assertAlmostEqual(improved["r2_baseline"], 0.0)
        self.assertAlmostEqual(improved["r2_extended"], 1.0)
        self.assertAlmostEqual(improved["delta_r2"], 1.0)

        equal_models = _bootstrap_delta(y, equal, equal, RELEASED_BOOTSTRAP)
        self.assertAlmostEqual(equal_models["delta_r2"], 0.0)

        degraded = _bootstrap_delta(y, equal, worse, RELEASED_BOOTSTRAP)
        self.assertLess(degraded["delta_r2"], 0.0)
        self.assertLess(degraded["r2_extended"], 0.0)

        singleton = _bootstrap_delta(np.array([1.0]), np.array([0.0]), np.array([0.5]), RELEASED_BOOTSTRAP)
        self.assertEqual(singleton["status"], "undefined")
        self.assertIsNone(singleton["delta_r2"])

    def test_bootstrap_paired_seeded_repeat(self) -> None:
        from tools.b_prediction.__main__ import RELEASED_BOOTSTRAP, _bootstrap_delta
        import numpy as np

        y = np.array([1.0, 1.0, 1.0, 4.0, 5.0], dtype=np.float64)
        f0 = np.array([0.8, 1.1, 0.9, 3.5, 5.5], dtype=np.float64)
        f1 = np.array([1.2, 0.7, 1.0, 4.2, 4.8], dtype=np.float64)

        def independent_bootstrap() -> dict:
            rng = np.random.Generator(np.random.PCG64(RELEASED_BOOTSTRAP["random_state"]))
            n = y.size
            defined = []
            undefined = 0
            for _ in range(int(RELEASED_BOOTSTRAP["resamples"])):
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
                defined.append((sse0_b - sse1_b) / sst_b)
            interval = np.quantile(
                np.array(defined, dtype=np.float64),
                RELEASED_BOOTSTRAP["quantiles"],
                method=RELEASED_BOOTSTRAP["quantile_method"],
            )
            return {
                "undefined_count": undefined,
                "delta_ci_lower": float(interval[0]),
                "delta_ci_upper": float(interval[1]),
            }

        expected = independent_bootstrap()
        observed = _bootstrap_delta(y, f0, f1, RELEASED_BOOTSTRAP)
        second = _bootstrap_delta(y, f0, f1, RELEASED_BOOTSTRAP)
        self.assertEqual(observed["bootstrap"], second["bootstrap"])
        self.assertEqual(observed["bootstrap"]["status"], "defined")
        self.assertEqual(observed["bootstrap"]["undefined_count"], expected["undefined_count"])
        self.assertGreater(expected["undefined_count"], 0)
        self.assertAlmostEqual(observed["bootstrap"]["delta_ci_lower"], expected["delta_ci_lower"], places=12)
        self.assertAlmostEqual(observed["bootstrap"]["delta_ci_upper"], expected["delta_ci_upper"], places=12)

    def test_leakage_firewall_evaluator_source(self) -> None:
        import inspect
        from tools.b_prediction import __main__ as engine

        evaluate_src = inspect.getsource(engine._run_evaluate)
        self.assertNotIn("sklearn", evaluate_src)
        self.assertNotIn("_fit_ridge", evaluate_src)
        self.assertNotIn("_tune_model", evaluate_src)
        self.assertNotIn("_fit_transform", evaluate_src)
        predict_src = inspect.getsource(engine._evaluate_from_models)
        self.assertNotIn("sklearn", predict_src)
        self.assertNotIn(".fit(", predict_src)

    @unittest.skipUnless(_has_sklearn(), "AIU/host runtime does not expose sklearn")
    def test_bundle_lock_existing_output_and_undefined_n1(self) -> None:
        from tools.b_prediction.__main__ import EXIT_OUTPUT, EXIT_SCHEMA

        with tempfile.TemporaryDirectory(dir=self.tmp_root) as td:
            temp = Path(td)
            contract_path = temp / "contract.json"
            _write_contract_with_hash(contract_path, _sha256(DEV_FIXTURE))
            out = temp / "develop"
            rc, _, err = _run_cmd(
                [*PYTHON, "develop", "--contract", str(contract_path), "--development", str(DEV_FIXTURE), "--output", str(out)],
                REPO_ROOT,
            )
            self.assertEqual(rc, 0, err)
            rc, _, err = _run_cmd(
                [*PYTHON, "develop", "--contract", str(contract_path), "--development", str(DEV_FIXTURE), "--output", str(out)],
                REPO_ROOT,
            )
            self.assertEqual(rc, EXIT_OUTPUT)
            self.assertIn("must not already exist", err)

            bundle = out / "bundle"
            complete = _load_json(bundle / "COMPLETE.json")
            manifest = _load_json(bundle / "bundle_manifest.json")
            identical = temp / "develop_identical"
            rc, _, err = _run_cmd(
                [*PYTHON, "develop", "--contract", str(contract_path), "--development", str(DEV_FIXTURE), "--output", str(identical)],
                REPO_ROOT,
            )
            self.assertEqual(rc, 0, err)
            self.assertEqual(
                _load_json(bundle / "checksums.json")["files"],
                _load_json(identical / "bundle" / "checksums.json")["files"],
            )

            mutated = temp / "mutated_bundle"
            mutated.mkdir()
            for item in bundle.iterdir():
                (mutated / item.name).write_bytes(item.read_bytes())
            target = mutated / "baseline_model.json"
            raw = bytearray(target.read_bytes())
            raw[0] = raw[0] ^ 0x01
            target.write_bytes(bytes(raw))
            lock = temp / "lock.json"
            _build_lock(lock, manifest["contract_sha256"], complete["bundle_hash"], _sha256(EXT_FIXTURE))
            rc, _, err = _run_cmd(
                [
                    *PYTHON,
                    "evaluate",
                    "--bundle",
                    str(mutated),
                    "--evaluation-lock",
                    str(lock),
                    "--external",
                    str(EXT_FIXTURE),
                    "--output",
                    str(temp / "eval_mutated"),
                ],
                REPO_ROOT,
            )
            self.assertEqual(rc, EXIT_SCHEMA)
            self.assertFalse((temp / "eval_mutated" / "COMPLETE.json").exists())

            whitespace = temp / "whitespace_bundle"
            whitespace.mkdir()
            for item in bundle.iterdir():
                (whitespace / item.name).write_bytes(item.read_bytes())
            checksums_obj = json.loads((whitespace / "checksums.json").read_text(encoding="utf-8"))
            (whitespace / "checksums.json").write_text(json.dumps(checksums_obj, indent=2) + "\n", encoding="utf-8")
            rc, _, err = _run_cmd(
                [
                    *PYTHON,
                    "evaluate",
                    "--bundle",
                    str(whitespace),
                    "--evaluation-lock",
                    str(lock),
                    "--external",
                    str(EXT_FIXTURE),
                    "--output",
                    str(temp / "eval_whitespace"),
                ],
                REPO_ROOT,
            )
            self.assertEqual(rc, EXIT_SCHEMA)
            self.assertIn("bundle checksum mismatch", err)
            self.assertFalse((temp / "eval_whitespace" / "COMPLETE.json").exists())

            incomplete = temp / "incomplete_bundle"
            incomplete.mkdir()
            for item in bundle.iterdir():
                if item.name != "oof_predictions.tsv":
                    (incomplete / item.name).write_bytes(item.read_bytes())
            rc, _, err = _run_cmd(
                [
                    *PYTHON,
                    "evaluate",
                    "--bundle",
                    str(incomplete),
                    "--evaluation-lock",
                    str(lock),
                    "--external",
                    str(EXT_FIXTURE),
                    "--output",
                    str(temp / "eval_incomplete"),
                ],
                REPO_ROOT,
            )
            self.assertEqual(rc, EXIT_SCHEMA)
            self.assertFalse((temp / "eval_incomplete" / "COMPLETE.json").exists())

            header = EXT_FIXTURE.read_text(encoding="utf-8").splitlines()[0]
            one_row = EXT_FIXTURE.read_text(encoding="utf-8").splitlines()[1]
            one_table = temp / "one_external.tsv"
            one_table.write_text(header + "\n" + one_row + "\n", encoding="utf-8")
            one_lock = temp / "one_lock.json"
            _build_lock(one_lock, manifest["contract_sha256"], complete["bundle_hash"], _sha256(one_table))
            eval_one = temp / "eval_one"
            rc, _, err = _run_cmd(
                [
                    *PYTHON,
                    "evaluate",
                    "--bundle",
                    str(bundle),
                    "--evaluation-lock",
                    str(one_lock),
                    "--external",
                    str(one_table),
                    "--output",
                    str(eval_one),
                ],
                REPO_ROOT,
            )
            self.assertEqual(rc, 0, err)
            payload = _load_json(eval_one / "evaluation.json")
            self.assertEqual(payload["metrics"]["status"], "undefined")
            self.assertIsNone(payload["metrics"]["delta_r2"])
            self.assertTrue((eval_one / "COMPLETE.json").exists())

    def test_scientific_lock_schema_dummy_ids_only(self) -> None:
        from tools.b_prediction.__main__ import (
            EXIT_SCHEMA,
            Failure,
            _enforce_scientific_environment,
            _imported_environment,
            _load_evaluation_lock,
            _validate_contract_fields,
        )

        payload = json.loads(CONTRACT_FIXTURE.read_text(encoding="utf-8"))
        dummy_hash = "ab" * 32
        payload["purpose"] = "scientific-run"
        payload["scientific_lock"] = {
            "status": "approved",
            "decision_commit": "dummy-decision-commit",
            "reviewer_receipt": "dummy-reviewer-receipt",
            "eligibility_hash": dummy_hash,
            "u_hash": dummy_hash,
            "q_hashes": {"dummy_q": dummy_hash},
            "feature_contract_hash": dummy_hash,
            "external_population_contract_hash": dummy_hash,
            "precision_contract_id": "dummy-precision-id",
            "environment_lock": _imported_environment(),
        }
        _validate_contract_fields(payload)
        _enforce_scientific_environment(payload["scientific_lock"])

        missing = dict(payload)
        missing_lock = dict(payload["scientific_lock"])
        del missing_lock["u_hash"]
        missing["scientific_lock"] = missing_lock
        with self.assertRaises(Failure) as raised:
            _validate_contract_fields(missing)
        self.assertEqual(raised.exception.code, EXIT_SCHEMA)

        mismatched_env = dict(payload["scientific_lock"])
        mismatched_env["environment_lock"] = dict(_imported_environment())
        mismatched_env["environment_lock"]["numpy_version"] = "0.0.0-dummy"
        with self.assertRaises(Failure) as raised:
            _enforce_scientific_environment(mismatched_env)
        self.assertEqual(raised.exception.code, EXIT_SCHEMA)

        with tempfile.TemporaryDirectory(dir=self.tmp_root) as td:
            temp = Path(td)
            lock_path = temp / "sci_lock.json"
            lock_payload = {
                "schema_version": "B-P1-evaluation-lock-1",
                "status": "approved",
                "contract_sha256": dummy_hash,
                "bundle_sha256": dummy_hash,
                "external_sha256": dummy_hash,
                "decision_commit": "dummy-decision-commit",
                "reviewer_receipt": "dummy-reviewer-receipt",
                "eligibility_hash": dummy_hash,
                "external_population_contract_hash": dummy_hash,
                "precision_contract_id": "dummy-precision-id",
            }
            lock_path.write_text(json.dumps(lock_payload, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            loaded, raw = _load_evaluation_lock(
                lock_path,
                dummy_hash,
                dummy_hash,
                dummy_hash,
                contract_purpose="scientific-run",
                contract_scientific_lock=payload["scientific_lock"],
            )
            self.assertEqual(loaded["decision_commit"], "dummy-decision-commit")
            self.assertEqual(hashlib.sha256(raw).hexdigest(), hashlib.sha256(lock_path.read_bytes()).hexdigest())

            lock_payload["decision_commit"] = "other-dummy-commit"
            bad_lock = temp / "sci_lock_bad.json"
            bad_lock.write_text(json.dumps(lock_payload, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            with self.assertRaises(Failure) as raised:
                _load_evaluation_lock(
                    bad_lock,
                    dummy_hash,
                    dummy_hash,
                    dummy_hash,
                    contract_purpose="scientific-run",
                    contract_scientific_lock=payload["scientific_lock"],
                )
            self.assertIn("decision_commit", str(raised.exception))

    @unittest.skipUnless(_has_sklearn(), "AIU/host runtime does not expose sklearn")
    def test_gridsearch_error_score_raise(self) -> None:
        from sklearn.linear_model import Ridge
        from tools.b_prediction.__main__ import (
            EXIT_NUMERIC,
            Failure,
            RELEASED_ALPHA_GRID,
            _materialized_splits,
            _tune_model,
        )
        import numpy as np

        model_cfg = {
            "type": "ridge",
            "continuous_scaler": "standard",
            "fit_intercept": True,
            "solver": "svd",
            "tol": 0.0001,
            "copy_X": True,
            "positive": False,
            "max_iter": None,
        }
        n = 12
        y = np.linspace(-2.0, 2.0, n, dtype=np.float64)
        cont = np.linspace(0.0, 1.0, n, dtype=np.float64).reshape(-1, 1)
        cat = np.zeros((n, 0), dtype=np.float64)
        splits = _materialized_splits(n, 42)
        original = Ridge.fit

        def boom(self, X, y=None, sample_weight=None):
            if float(self.alpha) == RELEASED_ALPHA_GRID[0]:
                raise ValueError("induced-fit-failure")
            return original(self, X, y, sample_weight=sample_weight)

        Ridge.fit = boom  # type: ignore[method-assign]
        try:
            with self.assertRaises(Failure) as raised:
                _tune_model(cont, cat, y, ["x"], [], splits, RELEASED_ALPHA_GRID, model_cfg, "final", -1, "baseline")
            self.assertEqual(raised.exception.code, EXIT_NUMERIC)
            self.assertIn("induced-fit-failure", str(raised.exception))
        finally:
            Ridge.fit = original  # type: ignore[method-assign]


if __name__ == "__main__":
    unittest.main()
