# Independent review of Grok W5

Date: 2026-09-11  
Fixed point: `69b70c8bb2b825b00c790e24fc632ddccb8ec20e`  
Scope: uncommitted Paper B W5 and real-source readiness changes in the canonical repository.

## Outcome

Grok delivered actual connected W5 code, but the reported green checkpoint was not acceptable as written. Independent adversarial review confirmed five additional correctness/reproducibility defects. They are fixed locally with regressions. The corrected synthetic path executes W1-W5 and stops before W6 with `pipeline_complete=false`.

No real biological analysis, external evaluation, AIU run, commit, or push was performed. Grok's reported 112-test full-suite result and its `n_candidates=10` output describe the pre-review implementation and are superseded; the parent must use a post-fix full regression before publication.

## Standards

### Fixed findings

1. **Hidden global complete-case prefilter.** `_candidate_ids()` called `_complete_promoter_raw()` before folds, inspecting every candidate's methylation and requiring every annotated promoter probe to be finite. This both leaked held-out feature availability into population selection and silently replaced the configured 95% training-probe / 80% aggregate rules with a stricter rule. Candidate selection now uses only fixed cohort, endpoint/universe, and baseline-covariate eligibility. Promoter eligibility occurs inside each fitted fold state and transform.
2. **Previously unreachable exclusion path crashed.** Once TCGA-0002/0008 were correctly allowed into folds, W5 attempted to pass integers/booleans to a string-only TSV writer. It now serializes exclusion rows explicitly and records the actual fold-dependent exclusions.
3. **The claimed frozen bundle was not internally frozen.** W5's `bundle/` lacked its own checksum manifest and completion record. It now has `checksums.json` and `COMPLETE.json`, with all numeric models, state, contract, folds, predictions, tuning, and metrics pinned.
4. **Feature-state/model linkage was indirect and ambiguous.** Both final model JSON files now carry the exact final fitted feature-state hash. The same hash is pinned in the bundle manifest, bundle completion record, W5 checksums, and W5 completion record. The W4 state payload hash and W4 state-file artifact hash are now recorded under distinct names and the W4 state's internal hash is validated before W5 starts.
5. **Identical fresh runs produced different scientific bundle hashes.** W2's scientific `sources.jsonl` embedded retrieval timestamps and run-directory cache paths. Those volatile values propagated through parent hashes into feature-state and model bytes. `sources.jsonl` now uses a stable cache-relative path and excludes retrieval time; timestamps remain in separate provenance receipts/manifests. A two-fresh-run regression verifies every W5 bundle payload byte is identical.
6. **Missing outer-fold diagnostics.** The initial `development_metrics.json` only had pooled OOF metrics. It now records five fold-level paired sample counts, selected baseline/extended alphas, MSE, R2, and the fold feature-state hash. Final manifest selection also records outer-alpha medians as required by the existing B-P1 shape.
7. **Compressed acquisition publication order.** A gzip object was moved to a cache path before its compressed digest was validated. Validation now occurs while bytes remain in the unpublished work path; a regression proves a bad compressed digest creates neither cached compressed nor decompressed payload.
8. **Dead/broken adapter helpers.** Removed unused helpers with incorrect return annotations and private CLI-only error dependencies.

### Residual judgement call

`fold_develop.py` imports many private helpers from the large `tools.b_prediction.__main__` module. This preserves the released implementation's exact numerical behavior but is tight coupling. A later maintenance refactor should move shared numerical primitives to a private library module without changing the public `develop`/`evaluate` TSV commands. It is not a scientific blocker for this checkpoint.

Standards result: eight fixed findings; worst was nondeterministic supposedly frozen model/state bytes.

## Spec

### Verified after fixes

- Fold feature state is fitted on each inner-training, outer-training/refit, final-tuning-training, and final-development partition; corresponding held-out rows are transformed with that state.
- TCGA-0002 and TCGA-0008 remain in the candidate population despite `cgA2=NA`; their fold-dependent aggregate exclusions are recorded rather than globally selecting them away.
- Synthetic fixtures now provide 14 fixed-eligible development candidates, preserving the fixed five outer/five inner/five final folds and the intentional TCGA-0004 endpoint/universe exclusion.
- Baseline and extended predictions share the same eligible rows and fold assignments. The reviewed fresh run emitted 14 unique paired OOF rows.
- Separate baseline/extended tuning uses the released alpha grid, training-only preprocessing, fixed KFold settings, `Ridge(solver="svd")`, and explicit failure on empty training/validation partitions.
- Final feature state is independently fitted on the full fixed-eligible development set, frozen beside the numeric models, and cryptographically linked to both models and bundle receipts.
- `tools/b_prediction` W5 sources participate in workflow code identity; a regression proves changing the adapter changes that identity. Resume on unchanged inputs skips W1-W5.
- Existing `develop` command still exposes the released validated-TSV interface without cohort/external parameters. Parent full regression remains the authoritative post-fix compatibility check.
- Real-source audit is truthful and local-only: 24 confirmed local objects, missing full GSE107299 expression matrix, and one `docs/research/B_readiness.md` size/hash mismatch. It reports no scores/models and no synthetic substitution.
- Credential-bearing URLs are rejected without echoing secrets; gzip acquisition requires and enforces decompressed size and digest.

### Focused evidence

- W5 + acquisition + workflow adversarial set: 23/23 passed in 58.008 seconds.
- Final W5-focused set, including two-fresh-run byte reproducibility: 6/6 passed in 16.768 seconds.
- Source audit: 1/1 passed; observed counts `confirmed=24`, `missing=1`, `mismatch=1`, `controlled_blocked=0`, `credential_rejected=0`.
- Fresh connected run: `tmp/paper_b_checks/w5_reviewed_final_sol_20260911`, exit 0, executed W1-W5, `pipeline_complete=false`.
- Resume: exit 0, `executed=[]`, skipped W1-W5.
- Reviewed run: 14 candidates, 14 paired OOF predictions, five outer-fold records; nested fold exclusions are present and machine-readable.
- `py_compile` and `git diff --check`: exit 0.
- Full post-fix regression: pending parent; do not reuse Grok's pre-fix 112-test receipt.
- AIU/server: pending; no server pass claimed.

Spec result: six implementation defects corrected; W5 meets the local synthetic checkpoint subject to the parent's post-fix full regression. W6-W8 and all scientific gates remain open.

## Exact W6 prerequisites

1. Treat the W5 `bundle/COMPLETE.json` bundle hash and final feature-state hash as immutable W6 inputs. Verify the bundle checksum manifest, every payload, model/state cross-links, W5 parent receipt, and accepted workflow code identity before reading external rows.
2. Add a W6-specific adapter/loader for the W5 bundle. The released fixed-table evaluator deliberately expects the original B-P1 bundle file set and does not yet accept W5's additional feature-state/contract payloads. Preserve its old interface and regression tests; do not weaken its exact-payload checks globally.
3. Load the final frozen W5 feature state and call only `transform(external_patient_ids, state, refit=False)`. Reject state hash/schema mismatch. No CPC fitting, probe reselection, imputation, scaling, recalibration, or population selection based on CPC outcome/performance.
4. Build the external numeric table in the exact contract column order. Apply the final training-selected probes; record external fold-independent eligibility/exclusions and require baseline/extended comparison on the identical independently eligible patient set.
5. Enforce development/external patient non-overlap and a separate evaluation lock tying together W5 bundle hash, final state hash, external canonical-input hash, eligibility/population contract, decision/reviewer receipt, and precision identifier.
6. Exercise negative and undefined outcomes unchanged: paired predictions, SSE/SST, negative R2/Delta-R2, constant-target handling, and seeded paired bootstrap. External outcome mutation may alter metrics only; it must never alter bundle/state bytes or eligibility/features.
7. Use synthetic CPC fixtures only until E1-E4/E6 and the evaluation release receipt are frozen. The missing GSE107299 full matrix and stale `B_readiness.md` manifest snapshot remain explicit readiness issues, not permission to substitute data or rewrite the manifest silently.
8. Keep W7/W8 unimplemented and `pipeline_complete=false`. AIU validation remains a separately recorded pending milestone.

Files directly corrected by the independent reviewer are within the uncommitted W5 tree: `tools/b_prediction/{adapter.py,fold_develop.py}`, `tools/b_acquire/acquire.py`, `tests/b_prediction/test_fold_w5.py`, `tests/b_workflow/{test_acquire.py,test_workflow.py}`, and expanded synthetic TCGA-0014/0015 fixtures/config generated by `specs/B/synthetic/write_fixtures.py`. Unrelated user/parent changes were preserved.
