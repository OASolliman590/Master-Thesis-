# Paper B B-P specification handoff

Date: 6 September 2026

Status: specification coordinated; B-P1 is reviewable for Spark release; no implementation or biological run performed.

## Selected contract

The user selected B-P external prediction improvement as Paper B's one primary direction. B-R is retained only as historical decision provenance: it is not a co-primary, fallback after a null result or an alternate endpoint available to the same run.

The selected external estimand is

`Delta_R2 = (SSE_baseline - SSE_extended) / SST`

in the same independently eligible CPC-GENE patients. Both ridge models and every fitted transformation are developed, separately tuned and frozen using TCGA-PRAD only. External evaluation permits prediction and paired arithmetic only: no refit, recalibration, feature selection, patient selection from outcomes or endpoint rescaling.

This selection freezes the primary direction and estimand. It does **not** approve the candidate gene program, common expression universe U, promoter sets Q, specimen/replicate rules, purity/covariate comparability, final eligible population, minimum meaningful effect or precision target. Those remain explicit gates to a real-cohort run.

Authoritative decision: [B_PRIMARY_BP_20260906.md](../decisions/B_PRIMARY_BP_20260906.md).

## Coordinated files

- `specs/B/README.md`, `ANALYSIS.md`, `DATA_AND_SOURCES.md`, `SOFTWARE_CONTRACT.md`, `REPRODUCE_AND_READINESS.md`, `PREREGISTRATION_AND_LEDGER.md`, `VALIDATION_AND_FIGURES.md` and `TICKETS_AND_TESTS.md` now state the selected primary and retain the unresolved gates.
- `specs/B/PRIMARY_ALTERNATIVES_PROPOSED.md` is preserved as the historical comparison and records B-P as the decision outcome.
- `specs/B/SOURCE_MANIFEST.json` is schema `B-selected-primary-source-manifest-0.2` and records B-P, the exact estimand, B-R's historical status and every still-unfrozen biological input.
- `specs/issues/B_spec.md`, `docs/research/B_MEASUREMENT_CHECKPOINT.md` and `docs/execution/PROGRESS.md` now distinguish the resolved primary choice from open measurement/readiness gates.
- [BP1_prediction_engine.md](../../specs/B/tickets/BP1_prediction_engine.md) is the one bounded coding ticket.

Historical raw source and peer-review artifacts under `docs/research/B_measurement/` were not changed for this selection. No Paper A/C/D, fleet, AIU or Notion-owned file was changed in this task.

## B-P1 implementation seam

B-P1 defines one deep module, `tools.b_prediction`, whose public surface is only `develop` and `evaluate`:

1. `develop` accepts an exact contract and a validated numeric development patient table. It owns deterministic ordering, nested patient-level folds, fold-local preprocessing, separate baseline/extended tuning, full-TCGA refit and a checksummed plain-numeric frozen bundle.
2. `evaluate` accepts that bundle, a separate signed evaluation lock and a validated external patient table. Its import path must have no fitting interface or scikit-learn dependency; it reconstructs frozen predictions with NumPy and computes the selected paired metric and conditional paired bootstrap.

Keeping the external file receipt in the evaluation lock means external-file changes cannot perturb development artifacts. The boundary also keeps biological feature construction and eligibility upstream: the engine validates table mechanics but cannot certify that P/U/Q, specimens or covariates are scientifically approved.

The ticket pins the implementation behavior for the synthetic milestone: five-by-five nested shuffled K-fold CV with seed 42; the exact nine-value alpha grid; separate MSE tuning and larger-alpha tie rule; fold-fitted scaling/constant removal; ridge with an unpenalized intercept and explicit SVD solver; canonical non-pickle model state; 2,000 paired PCG64 bootstrap draws; direct SSE/SST arithmetic; and explicit undefined behavior for `n<2` or `SST=0`.

The API assumptions were checked against the official scikit-learn documentation for [KFold](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.KFold.html), [GridSearchCV](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GridSearchCV.html), [StandardScaler](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html) and [Ridge](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html). Candidate versions come from `docs/execution/aiu_python_inventory.json`: Python 3.11.16, NumPy 2.4.6, SciPy 1.17.1, scikit-learn 1.9.0 and threadpoolctl 3.6.0. They remain observed candidates until an isolated AIU import/smoke test and dependency lock are reviewed.

## Acceptance and remaining blockers

B-P1 synthetic acceptance requires schema and identity rejection tests, row-order invariance, nested-fold locality sentinels, split reuse, separate-alpha and tie fixtures, a hand-solved ridge oracle, immutable-bundle tests, a no-refit evaluator test, metric/undefined oracles, paired-bootstrap determinism, leakage-firewall tests and an environment receipt. A synthetic pass is software evidence only.

Before any actual TCGA development or CPC-GENE evaluation, Astra must release a signed scientific lock covering:

- the final expression program, U and rank-score mapping;
- Q and promoter/mask/coverage rules;
- patient/specimen/replicate and cross-assay identity rules;
- approved comparable baseline covariates, especially genuine tumour cellularity rather than `WGS_BASED_PURITY_ESTIMATION`;
- final development/external eligibility and patient-feature table hashes;
- minimum meaningful Delta_R2, precision/adequacy targets and reviewer receipt; and
- a resolved AIU dependency/runtime lock.

The parallel historical gene-list inspection may inform a later program decision, but filenames or prior CPC-GENE-selected lists cannot silently replace the program in this contract.

## Checks completed

- Parsed `specs/B/SOURCE_MANIFEST.json`: schema `B-selected-primary-source-manifest-0.2`, `selected_id=B-P`.
- Confirmed the decision, B-P1 ticket, measurement checkpoint and execution-progress paths exist.
- Searched the authorized current-state corpus for unqualified stale “primary unselected” language; none remains.
- Confirmed current-state documents identify B-P and preserve B-R as historical.
- Ran Git diff whitespace validation plus an explicit trailing-whitespace scan of the authorized tracked and untracked files successfully.

No code was implemented, no AIU or cohort command was run, no biological result was created, and no commit or push was made.
