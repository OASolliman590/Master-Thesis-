# B-P1 — validated-table prediction engine

## Status and release boundary

**RELEASED by Astra for bounded coding, 6 September 2026; not a biological-analysis release.** Spark may now implement and test this ticket. See docs/reviews/B_BP_RELEASE_ASTRA.md. Implementation uses synthetic validated patient tables only. Actual TCGA development and CPC-GENE evaluation remain blocked until the program/U/Q, specimen, covariate, eligibility and precision contracts are signed.

Selected primary: independent CPC-GENE `Delta_R2=(SSE_baseline-SSE_extended)/SST` comparing two separately tuned TCGA-fitted frozen ridge predictors. B-R is historical and outside this ticket.

## Ownership and exclusions

Spark owns only:

- `tools/b_prediction/` — prediction module and CLI;
- `tests/b_prediction/` — unit/interface tests and tiny explicitly synthetic TSV/JSON fixtures; and
- `docs/validation/B_prediction/` — permitted test logs, schema examples and environment receipts.

Do not edit specs, source manifests, B-F1, other papers, shared environments, fleet configuration or historical data. Do not download cohort data, build U/Q, reconcile specimens, calculate biological features, select patients, fit an actual TCGA model, evaluate CPC-GENE or produce a scientific figure. Synthetic fixtures must say `purpose=synthetic-test` in every input and output.

## Deep module and seam

`tools.b_prediction` is one deep module. Its external interface has two commands:

```text
python -m tools.b_prediction develop --contract CONTRACT.json --development TCGA_FEATURES.tsv --output RUN_DIR
python -m tools.b_prediction evaluate --bundle RUN_DIR/bundle --evaluation-lock EVALUATION_LOCK.json --external CPC_FEATURES.tsv --output EVAL_DIR
```

The module owns schema validation, deterministic patient ordering, nested folds, fold-local transforms, separate tuning, full-development refit, bundle freeze, no-refit prediction, exact paired metrics, paired bootstrap uncertainty, provenance and atomic completion. Callers do not assemble estimators or preprocessing objects.

The seam is after biological feature construction. Upstream adapters must eventually produce validated numeric patient tables; they are not part of B-P1. The evaluator reads a plain numeric frozen bundle and has no fitting interface. Internal estimator/preprocessing seams remain private to the module and tests.

Exit statuses:0 success;2 invalid CLI/contract;3 input schema/hash/lock failure;4 model/numeric failure;5 output/I/O or pre-existing-output refusal. A failed command emits diagnostics but no `COMPLETE.json`.

## Contract JSON

Required fields:

| Field | Requirement |
|---|---|
| `schema_version` | Exact string `B-P1-contract-1`. Unknown versions fail. |
| `purpose` | `synthetic-test` or `scientific-run`. B-P1 acceptance uses only `synthetic-test`. |
| `development_cohort` / `external_cohort` | Exact distinct labels; scientific defaults will be `TCGA-PRAD` and `CPC-GENE` only after lock. |
| `patient_id_column` / `target_column` | Exact TSV columns. Target is the already constructed Y; the engine never derives it. |
| `continuous_baseline_columns` | Ordered numeric baseline columns. Proposed science currently includes age and approved purity, but the ticket does not choose them. |
| `categorical_baseline_groups` | Ordered nonreference dummy columns per categorical variable; values must be0/1 with at most one active level per group, allowing all-zero reference. |
| `extended_columns` | Ordered numeric promoter-feature columns added to the complete baseline. The engine does not require or infer gene names. |
| `alpha_grid` | Exact ordered values `[0.0001,0.001,0.01,0.1,1,10,100,1000,10000]`; nonpositive, duplicate, nonfinite or reordered values fail. |
| `outer_cv` / `inner_cv` / `final_cv` | Each records `n_splits=5`, `shuffle=true`, `random_state=42`. |
| `bootstrap` | `resamples=2000`, `random_state=42`, `bit_generator=PCG64`, `quantiles=[0.025,0.975]`, `quantile_method=linear`. |
| `model` | Exact fields below for ridge/scaling/selection. |
| `development_sha256` | Expected development-table bytes. External file identity is deliberately absent so it cannot perturb development artifacts. |
| `scientific_lock` | For `scientific-run`, requires `status=approved`, decision commit, reviewer receipt, eligibility/U/Q/feature-contract hashes and external population/precision identifiers. Synthetic mode requires `status=synthetic-only`. |

Unknown contract fields fail unless explicitly listed as optional in the schema. JSON numbers must be finite; duplicate JSON keys fail. The command records the exact contract bytes/hash rather than rewriting it into a silently different contract.

`EVALUATION_LOCK.json` is a separate canonical JSON artifact supplied only to `evaluate`. It contains `schema_version=B-P1-evaluation-lock-1`, the frozen bundle hash, external table SHA-256, approved external eligibility/population-contract hash, precision-contract identifier, decision commit and reviewer receipt. Synthetic mode requires `status=synthetic-only`; a scientific evaluation requires `status=approved`. The evaluator records its exact bytes/hash. Development never reads this artifact, so later external-file receipt changes cannot alter any fitted bundle byte.

## Validated patient-table interface

Inputs are uncompressed UTF-8 TSV with one header and one row per independent patient. The development and external tables share exactly the contract columns:

```text
cohort_role  patient_id  Y  <continuous baseline>  <categorical dummies>  <extended features>
```

Requirements:

- `cohort_role` is constant and matches the command/contract role.
- `patient_id` is nonempty and unique. Before any split, rows are sorted by the UTF-8 byte ordering of the exact patient ID; input row permutation cannot change folds or model state.
- All model/target fields are finite decimal numbers. No NA token, infinity, imputation or row deletion is permitted inside this module.
- Dummy values are exact0/1; each declared group has at most one1. Unknown, duplicate, omitted or extra columns fail.
- Baseline and extended models use the same patient rows, target and outer/inner splits. The extended design is exactly baseline columns followed by `extended_columns`.
- The input SHA-256 must match before parsing. Development and external patient IDs must not overlap; the bundle carries sorted individual patient-ID hashes for this check without publishing raw IDs.
- Validated-table status means upstream rules have already resolved one patient, specimen, score, feature and covariate row. B-P1 does not certify that claim; a future scientific run must cite the upstream signed lock.

## Exact development behavior

1. Validate and byte-sort patients. Reject `n<7`, the smallest size at which every training partition of the specified five-fold outer split can itself support five-fold inner CV; the scientific lock may impose a larger minimum later.
2. Create the outer splitter with `KFold(n_splits=5, shuffle=True, random_state=42)`. Save one fold assignment per patient.
3. For each outer-training set, create its inner splitter with the same explicit KFold arguments. Materialize splits once and reuse them for baseline and extended tuning.
4. For each model, fit all value-learned transforms inside each inner-training split. Continuous fields are centered/scaled using training mean/population SD (`ddof=0`); categorical dummies pass unscaled. Training-constant columns are recorded and removed after transformation. Validation values never choose columns/statistics.
5. Tune baseline and extended models separately by mean inner validation MSE across the exact alpha grid. The same patient splits are used, but different alphas are allowed. Exact mean-MSE ties select the larger alpha. Any failed candidate fails the run; no `error_score=nan` continuation.
6. Refit the selected fold model on the full outer-training set and emit paired outer predictions for the untouched outer validation patients. OOF results are development diagnostics, not the external primary.
7. Repeat separate five-fold tuning on all development patients, fit both final models on all development patients, and freeze their transforms/coefficients.
8. Write the bundle and all development outputs to a new output directory. Hash every file, then write `COMPLETE.json` last. Existing output paths are refused; partial outputs are never promoted to complete.

No external file/path/object is accepted by `develop`. Changing an external fixture must leave every development byte except an explicitly separate test receipt unchanged.

## Model and library assumptions

Candidate AIU versions are observed, not yet a resolved project lock: Python3.11.16, NumPy2.4.6, SciPy1.17.1, scikit-learn1.9.0 and threadpoolctl3.6.0 from `docs/execution/aiu_python_inventory.json`. B-P1 may not install or mutate them. The implementation must record actual imported versions and fail a `scientific-run` if they differ from the later resolved lock.

The implementation contract for scikit-learn1.9 is:

- [`KFold`](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.KFold.html): `n_splits=5, shuffle=True, random_state=42`; never rely on its unshuffled defaults.
- [`Pipeline`](https://scikit-learn.org/stable/modules/generated/sklearn.pipeline.Pipeline.html) with a private [`ColumnTransformer`](https://scikit-learn.org/stable/modules/generated/sklearn.compose.ColumnTransformer.html): `StandardScaler(copy=True, with_mean=True, with_std=True)` for continuous columns and passthrough for categorical dummies; a fold-fitted `VarianceThreshold(threshold=0.0)` removes training-constant transformed columns.
- [`GridSearchCV`](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GridSearchCV.html): explicit materialized inner splits, `scoring="neg_mean_squared_error"`, `refit=False`, `n_jobs=1`, `error_score="raise"`, `return_train_score=False`; select/refit explicitly to enforce the larger-alpha tie rule.
- [`Ridge`](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html): `fit_intercept=True`, `solver="svd"`, `copy_X=True`, `positive=False`, `tol=0.0001`, `max_iter=None`. Alpha is scalar. The intercept is unpenalized; all retained slopes are penalized. No sample weights.
- All arrays are C-contiguous NumPy `float64`. Set and record numerical thread limits at1 for acceptance runs; do not claim bitwise cross-BLAS identity without testing it.

If scikit-learn1.9 behavior differs on AIU, stop and record the observed signature/error; do not silently change solver, folds, scaling, score or tie behavior.

## Frozen bundle

Do not serialize or unpickle estimator objects. `bundle/` contains canonical JSON/TSV numeric state sufficient for prediction:

- `bundle_manifest.json`: schema/purpose, contract and development hashes, ordered input/features, environment, folds, selected alphas, training patient-set hash and individual patient-ID hashes;
- `baseline_model.json` and `extended_model.json`: ordered raw and retained columns, categorical/continuous roles, dropped constants, training means/scales, ridge alpha, coefficient vector and intercept;
- `development_metrics.json`: outer-fold MSE/R2 diagnostics and pooled paired OOF rows, explicitly not the primary result;
- `fold_assignments.tsv`, `tuning_results.tsv` and `oof_predictions.tsv`;
- `checksums.json`; and
- `COMPLETE.json`, written last and containing the checksum-manifest hash.

Canonical JSON uses UTF-8, sorted keys, compact separators, a terminal newline and `allow_nan=false`. Floating values round-trip as Python/JSON double precision. The evaluator verifies every bundle checksum and reconstructs predictions with NumPy only; its import path must not import scikit-learn or expose `fit`, `tune` or transform-learning functions.

## Locked external evaluation

`evaluate` must:

1. require a complete checksum-valid bundle and a new output directory;
2. validate/hash/sort the external table and reject any development patient-ID hash;
3. apply the two frozen transforms and coefficient vectors without fitting, recalibration, column selection or eligibility changes;
4. emit one paired patient row with Y, f0, f1 and both squared errors;
5. compute directly in float64: `SSE0`, `SSE1`, `SST=sum((Y-mean(Y))^2)`, `R2_0=1-SSE0/SST`, `R2_1=1-SSE1/SST`, and selected `Delta_R2=(SSE0-SSE1)/SST`;
6. keep negative R2/Delta_R2 values; if `n<2` or `SST==0`, set all ratio metrics to null with explicit `status=undefined` and reason;
7. draw2000 paired patient bootstrap samples using `numpy.random.Generator(numpy.random.PCG64(42))`, keeping Y/f0/f1 together, recomputing the ratio, reporting linear-method2.5/97.5 percentiles and undefined-resample count/fraction; and
8. write `predictions.tsv`, `evaluation.json`, `checksums.json` and `COMPLETE.json` last. Scientific outputs carry bundle, external-input, contract, eligibility/population and code hashes.

The paired bootstrap is conditional on the two fitted models. It does not represent retraining uncertainty. No correlation, recalibrated prediction, platform-favourable subset or secondary metric can replace the selected primary.

## Meaningful acceptance checks

1. **Schema/identity:** wrong hash, duplicate patient, unknown column, NA/nonfinite value, invalid dummy group, role mismatch and development/external ID overlap fail without `COMPLETE.json`.
2. **Order invariance:** row permutation yields identical sorted folds, selected alphas, numeric bundle state and scientific result fields.
3. **Fold locality:** sentinels show an inner-validation value cannot change its inner-training means/scales/constants; an outer-validation value cannot change outer-training transforms/tuning. Baseline and extended share exact split indices.
4. **Separate tuning/ties:** a controlled fixture selects different baseline/extended alphas; an exact score tie selects the larger alpha. Candidate failures stop instead of being skipped.
5. **Model oracle:** a tiny manually solved ridge/scaling case matches coefficients/predictions within a declared tolerance; intercept is unpenalized and `solver_` records `svd` during development.
6. **Bundle lock:** byte mutation, missing file, changed contract/hash, incomplete bundle or existing output path fails. Two identical runs have identical scientific JSON/model/fold/prediction bytes; timestamp receipts may differ and are excluded from scientific hashes.
7. **No-refit evaluator:** monkeypatch every scikit-learn `fit` entry to raise and show evaluation still succeeds from numeric bundle state. Altering external Y changes metrics only; altering external predictors changes predictions/metrics but never bundle bytes.
8. **Metric oracle:** hand-computed cases reproduce SSE/SST/R2/Delta_R2; equal models give Delta_R2=0; improved and worse extended predictions have correct signs; negative R2 is retained; `n<2` and constant Y are undefined/null.
9. **Bootstrap unit:** resamples paired patient rows, never model columns separately. Seeded repeats match; constant-target draws increment the undefined count and are not redrawn.
10. **Leakage firewall:** `develop --help` has no external argument; evaluator source has no fitting import/path; external data cannot affect alpha, transforms, columns or coefficients. A CPC-derived feature-selection provenance marker fails the scientific lock.
11. **Environment receipt:** record Python/package/BLAS/thread versions and actual command/exit statuses. Local/synthetic success is labelled as such; AIU or cohort validation remains pending when not run.

Minimum implementation acceptance is the full synthetic suite plus independent code/spec review. It does not close E1–E4/E6, establish final N/precision, or authorize actual TCGA/CPC execution.

## Spark handoff

Return one diff limited to the owned paths, actual commands/exit statuses, a file inventory and unresolved implementation questions. Do not commit or push. Stop rather than expanding the interface, adding a new model/cohort, changing scientific specs or fabricating cohort-shaped output as a real result.

## Release clarifications

These resolve implementation ambiguity without selecting biological inputs:

- Timestamp receipts are separate from deterministic numeric model state. Define checksums without circular self-reference: checksums.json covers payload files and excludes itself and COMPLETE.json; COMPLETE.json pins checksums.json. Reject undeclared/missing payload entries and unsafe paths. Define the bundle hash as SHA256 of the exact checksums.json bytes and use that value in the evaluation lock.
- The TSV schema has no purpose column. Synthetic fixtures are identified by the required contract purpose and associated fixture metadata; every generated JSON records purpose and output TSVs inherit the hashed run contract. Never label synthetic patient tables as TCGA/CPC measurements.
- A draw with undefined SST is recorded and never redrawn. If no bootstrap draws have a defined ratio, interval limits are null with an explicit reason. If constant-column removal leaves zero predictors, fail clearly with numeric/model exit4; do not invent an undocumented fallback model.
- The engine consumes prepared features. It cannot retroactively make value-selected upstream probe sets fold-safe. A later scientific release must either supply genuinely fixed, outcome-independent measurements or add an approved fold-aware upstream feature-selection interface. Successful synthetic engine tests cannot close that gate.
- AIU was reachable in the parent check on6 September2026; Python3.11.16 actually imported NumPy2.4.6, SciPy1.17.1, scikit-learn1.9.0 and threadpoolctl3.6.0. This confirms availability, not a resolved immutable environment or a completed model run. The local bundled Python lacks SciPy. Do not install into shared environments.
