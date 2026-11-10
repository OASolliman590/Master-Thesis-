# A-P2 fit and evaluation

This product implements the signed A-P2 learner and its separately labelled cohort-adaptive sensitivity. Its outputs are software artifacts; synthetic runs do not validate biology. The governing method and thresholds are in [the signed validation amendment](../../specs/amendments/2026-11-02-paper-a-validation/AMENDMENT.md), [the numerical freeze amendment](../../specs/amendments/2026-11-04-numerical-freeze/AMENDMENT.md), and [N01–N08B](../../specs/A/NUMERICAL_FREEZE_REGISTER.tsv).

## Input contract

Each command takes an `a_p2_input_manifest_v1` JSON file. It declares `data_classification` (`SYNTHETIC_ONLY` or `PRIVATE_PATIENT_LEVEL`), `role` (`development` or `final_test`), the `input_table` path and SHA256, the four frozen feature-membership hashes, the cohort-specific feature-transform contract and exact CYT definition, a `cohorts` map, input provenance, and a hash-bound identity sidecar. Each cohort entry names its `study_family`, `cancer`, measurement `representation`, `feature_transform`, and explicit `primary_eligible`, `adaptive_eligible`, and `cyt_available` values.

The table reader names and selects only `cohort`, `patient_id`, `orr_class`, the four panel features, and `CYT`. Each panel column must be the arithmetic mean over its complete frozen membership after the declared cohort transform. Primary-eligible cohorts must declare `log2(TPM + 1)`; the cohort-adaptive sensitivity also accepts the signed deposited log2 upper-quartile representation. The frozen equation records each training cohort's representation and transform. `CYT` must be `sqrt(TPM_GZMA * TPM_PRF1)` with no offset. A learner result remains available without a CYT difference when CYT is unavailable.

A synthetic manifest uses explicit generated-fixture provenance and binds both the exact table hash and an invented identity sidecar. The sidecar marks every invented identity as unique and cannot be used as real identity evidence. Known source names and protected aliases are rejected even when a manifest claims synthetic origin. Synthetic provenance cannot authorize real inputs. No fixture signatures are used.

## Operations

```sh
python -m tools.a_p2 development --manifest INVENTED_DEVELOPMENT.json --out .scratch/a_p2/development
python -m tools.a_p2 freeze --manifest INVENTED_DEVELOPMENT.json --out .scratch/a_p2/frozen
python -m tools.a_p2 final-evaluate --manifest INVENTED_FINAL.json --equation .scratch/a_p2/frozen/equation.json --out .scratch/a_p2/final
```

`development` reports leave-one-complete-family-out results with per-study learner/CYT AUROCs, paired differences, equal-study and equal-cancer summaries, the joint study-and-cancer label for single-study cancers, and the 20 repeated stratified within-study splits. Split output includes each weighted learner AUROC, CYT AUROC, and paired difference; small studies remain training-only. The split mean and SD describe split variability; this is a validation-setting contrast, not an optimism estimate. Cohort-adaptive outputs and aggregates have separate filenames and labels; if CYT is unavailable, learner-only results remain available while paired aggregates are marked unavailable.

`freeze` fits both eligible equations on all declared development patients and writes a portable `equation.json` with complete panel memberships, the primary and cohort-adaptive training-cohort transforms, training scaling, coefficients, coefficient/scaling hashes, diagnostics, and an equation hash. `final-evaluate` checks the equation hash and family separation before reading the input table. It reports the primary paired comparison and its 2,000 response-stratified bootstrap interval when both classes meet the 10-patient floor. The second-check bootstrap uses its separate frozen stream; a discrepancy over 0.01 AUROC is flagged and never replaces the main interval. Final cohort-adaptive results are descriptive and separately labelled.

`adaptive_external_scaling.tsv` records the final sensitivity's cohort-wide means and sample SDs, computed without outcomes. This within-study standardisation cannot undo preprocessing already estimated across the full source cohort, such as ComBat.

Each run records input, code, signed-contract, software-lock, output, and R runtime hashes in its product and R bridge manifests. Verified input, identity, and equation bytes are snapshotted under the private `.work/` output directory before R reads them. Successful and failed R bridge stages are retained under `.work/r_bridge_stages`; these private stages are excluded from the publishable product manifest. Random split/bootstrap assignments and receipts use only the existing R streams; each receipt names the published assignment file and carries its matching digest. Keep all generated tables, predictions, manifests, sidecars, snapshots, and bridge stages in `.scratch/` or `results/`; do not commit them.

## Real-data gate

All three real-data commands default to outcome access disabled. The CLI exposes `--allow-outcomes` as a separate, default-false gate; a real operation also needs an approved user-release record. This worker did not use the flag or run any real operation. The release record references a scoped decision by identity, path, and exact SHA256, and binds operation, input role, manifest/table hashes, identity-sidecar and registry hashes, cohort list, and `orr_class`. A final record additionally binds `UNTOUCHED_FINAL_TEST`, the final cohort, and the exact frozen-equation hash. The record must be an explicit approved decision; invented fixtures are never accepted as approvals. No signing keys or detached-signature workflow are used. IMvigor210 remains refused except through a future matching real final-evaluation record after the explicit outcome gate.

Real execution also requires a private identity sidecar linked to the authoritative acquisition, publication-family, and overlap registries. Unresolved or duplicate canonical patient identities stop before any fit or split. Caller-supplied cohort labels alone do not establish family independence. The real identity/family inventory and a real user-release decision remain readiness requirements.

Path checks reject symlink ancestry, `ingestion_packet.json`, and protected paths before opening files. `THESIS_RUNTIME` does not select inputs for the three fit/evaluation operations.

The ridge implementation is pinned to glmnet 5.2 and uses the frozen `family="binomial"`, `alpha=0`, `lambda=0.1`, `standardize=FALSE`, and `control` settings. See the [glmnet reference manual](https://cran.rstudio.com/web/packages/glmnet/refman/glmnet.html) and the primary algorithm paper ([Friedman, Hastie, and Tibshirani, 2010](https://doi.org/10.18637/jss.v033.i01)). CYT is the established cytolytic activity measure ([Rooney et al., 2015](https://doi.org/10.1016/j.cell.2014.12.033)).

The current implementation and tests use invented inputs only. No real development or final evaluation is released or run by this product handoff. CIBERSORTx: not run.
