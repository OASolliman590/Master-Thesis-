# Paper B W1-W4 handoff — connected synthetic foundation

**Disposition, 11 September 2026:** local synthetic W1-W4 software checkpoint. This is not a completed Paper B pipeline and not a scientific or real-cohort release. All policy values and outputs are labelled `synthetic=true` / `SYNTHETIC FIXTURE ONLY`.

## 1. What executable path now works

From the repository root, with `E:\Master_Thesis\.venvs\paper-b-20260911\Scripts\python.exe`:

```text
python -m tools.b_workflow plan --config specs/B/workflow.synthetic.json
python -m tools.b_workflow run --mode synthetic --config specs/B/workflow.synthetic.json --output RUN_DIR --through W4
python -m tools.b_workflow resume --output RUN_DIR --through W4
```

This is genuinely connected: `run` loads the versioned config, writes `plan.json`, then executes W2→W3→W4 in-process. Each stage consumes predecessor checksums, publishes atomically (`STAGE.work` renamed only after `COMPLETE.json`), and carries `synthetic=true`. W3 parses W2 cached raw STAR/CPC bytes via `tools.b_formats.records` (not B-F1 summary JSON). W4 fits fold-local feature state from W3 canonical tables. A default run without `--through W4` executes W1-W4 then fails with `stage-not-implemented:w5` and `pipeline_complete=false`.

## 2. Fold-local W4 → W5 interface

Import `tools.b_features.provider.FoldFeatureProvider`.

- `fit(training_patient_ids) -> FeatureState` uses only those patients' canonical assay values. Probe eligibility is training-fold coverage of unmasked promoter probes. Outcomes, held-out rows, external rows and globally selected probes cannot enter `fit`.
- `transform(patient_ids, state, refit=False)` applies the frozen gene universe, program membership and eligible-probe lists without refitting. `refit=True` is rejected.
- Persisted hashes: `W4/full_training_feature_state.json` (`state_sha256`) and `W4/fold_states/fold_*/feature_state.json`. The full-development state must not be reused inside nested CV; W5 must call `fit` on each training fold.
- Existing `tools.b_prediction` validated table interface and its 16 tests are unchanged.

Leakage protection checked: changing an inner-validation/held-out beta does not change the inner-training `FeatureState` hash; body and masked probes never become promoter features; NA is not converted to zero.

## 3. Files touched

Pre-existing dirty (not edited here):

- `specs/B/WORKFLOW_IMPLEMENTATION.md` — parent-owned figure-explanation paragraph, preserved
- `tmp/` — pre-existing scratch plus this checkpoint's run directories

This implementation:

- `tools/b_workflow/` — plan/run/resume
- `tools/b_acquire/` — immutable file/HTTP acquisition
- `tools/b_cohort/` — canonical identity/assay tables
- `tools/b_features/` — scores and fold-local provider
- `tools/b_formats/records.py` — record parsers (inspect CLI unchanged)
- `tools/check_paper_b.py` — now discovers `tests/b_workflow`
- `specs/B/workflow.synthetic.json`
- `specs/B/synthetic/` — tiny raw STAR/CPC, annotation, specimen, covariate fixtures
- `tests/b_workflow/`
- `docs/validation/B_workflow/HANDOFF.md`

## 4. Commands and results

Interpreter: `E:\Master_Thesis\.venvs\paper-b-20260911\Scripts\python.exe`

| Command | Result |
|---|---|
| `python -m unittest discover -s tests/b_workflow -v` | **35 tests, 0 failed, 0 skipped**, 14.679 s |
| `python tools/check_paper_b.py` | **101 tests, 0 failed, 0 skipped**, 125.091 s (19 formats + 15 registry + 16 annotation + 16 prediction + 35 workflow) |
| `python -m tools.b_workflow plan --config specs/B/workflow.synthetic.json` | exit 0; `pipeline_complete=false`; W5-W8 `stage-not-implemented` |
| fresh `--through W4` | exit 0; executed W1-W4; `pipeline_complete=false` |
| resume on that output | exit 0; `executed=[]`; skipped W1-W4 |
| tamper W2 cache then resume | exit 0; W2 hash mismatch; invalidated W2-W4; re-executed W2-W4 from original sources; no stale W3 reuse |
| `git diff --check` | exit 0 |

Fresh run: `tmp/paper_b_checks/w1w4_fresh_20260911`  
Tamper copy: `tmp/paper_b_checks/w1w4_tamper_20260911`

Hand-calculated synthetic oracles on the fresh W4 scores: TCGA-0001 Y=0.375 (ties), TCGA-0002 Y=0.125, TCGA-0003 Y=0.5, TCGA-0004 ineligible (incomplete U). WGS agreement 0.99 is quarantined; purity is 0.70 from `qpure_cellularity`.

## 5. Remaining blockers / W5 requirement

W5-W8 are not implemented. End-to-end acceptance (W2-W7 figures, W8 enabled/blocked contracts) has **not** passed. Real-cohort feature construction remains blocked on E1-E4/E6. Ayers weights, HOPE scoring, full IFNG, M0-M6 and approved-immunotherapy target scores are not inferred.

W5 must extend `tools.b_prediction` `develop` with this fold-local provider, persist the final TCGA probe-state hash beside the frozen bundle, and keep the existing fixed-feature table interface for regression tests. Do not feed `full_training_feature_state.json` into nested CV.

Tables are TSV/JSON (declared serialization), not parquet. Annotation/identity fixtures are hashed into the plan from repo paths rather than re-acquired as public objects. W4 `demo_folds` are interface fixtures, not scientific 5-fold CV.

## 6. Safety

No git add/commit/push. No real TCGA/CPC-GENE cohort access. HTTP tests used loopback only. No Notion or external application updates.
