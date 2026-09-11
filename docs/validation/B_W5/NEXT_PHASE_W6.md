# Paper B W6: frozen external evaluation

Release boundary: W6 synthetic software implementation may proceed from the reviewed W5 checkpoint. AIU fresh W1-W5 and resume passed, but full AIU regression remains 115/116 because four existing server fixtures were excluded from the isolated copy. Subsequent SSH timeouts prevent closure. This is NOT a full AIU test pass or real-cohort release; retain the pending server gate and resolve when connectivity returns.

Work in `E:\Master_Thesis\master-thesis`. Read AGENTS.md, CONTEXT.md, the current progress record, specs/B/WORKFLOW_IMPLEMENTATION.md, ANALYSIS.md, the B-P1 ticket, and the reviewed W5 report at `E:\Master_Thesis\planning\grok_local_repair\SOL_W5_REVIEW.md`. Preserve existing reviewed code and scientific scope. No delegation, commits or pushes.

Implement actual W6 code connecting W5's frozen bundle to external canonical assay rows. Do not change W5 fitting or the released fixed-table develop/evaluate behavior to accommodate the new bundle.

1. Add a dedicated W5-bundle loader and W6 adapter. Verify COMPLETE, checksum index, every declared payload, both model-to-final-state links, state schema/internal hash and upstream stage identity. Reject altered, missing, undeclared or mismatched payloads before external transformation. Preserve the original fixed-table evaluator's exact-payload checks.
2. Require a separate versioned evaluation lock linking model bundle, final feature state, external canonical inputs, fixed eligibility/population contract, decision receipt and precision identifier. Synthetic receipts are visibly fixture-only and cannot release real data.
3. Apply final training-selected probes using transform(external_ids, frozen_state, refit=False). Use training coefficients/scaling/column order. No external fitting, imputation, probe selection, calibration or model tuning. Reject development/external patient overlap and duplicate external patients.
4. Record deterministic external exclusions and compare both models on identical eligible rows. Required outcome availability can affect evaluability, but changing finite external Y values must not change eligibility, features or predictions. Never select the population from external prediction performance.
5. Emit paired patient predictions and errors; compute SSE0, SSE1, SST, R2 values and primary Delta_R2=(SSE0-SSE1)/SST exactly. Preserve negative values; undefined cases serialize null with explicit reason. Reuse the prescribed 2000 paired-patient PCG64 seed-42 bootstrap and report undefined resamples. Do not add unprespecified significance claims.
6. Integrate W6 into workflow dependencies, code identity, checksummed publication and resume invalidation. Provide fresh --through W6 and resume commands; default execution must stop honestly at W7 with pipeline_complete=false. W7 graph/report and W8 remain pending.
7. Tests must prove: every fit entry can be disabled during W6; model/state bytes stay unchanged after external Y or predictor mutations; Y changes affect only evaluation statistics, while predictor changes can affect predictions; bundle/state tampering fails; external overlap fails; paired metric/undefined/bootstrap oracles match; original B-P1 interface still passes.

Use only synthetic CPC assay fixtures for evaluation until E1-E4/E6 and the real evaluation release are frozen. Missing full GSE107299 and the stale B_readiness.md manifest snapshot remain real-readiness issues; do not overwrite provenance or substitute synthetic data. Do not modify scientific specs to force a pass.

Use `E:\Master_Thesis\.venvs\paper-b-20260911\Scripts\python.exe`. Run `python tools/check_paper_b.py`, focused W6 tests, fresh W1-W6 and resume. Record AIU tests only if actually executed through permitted isolated access; otherwise pending.

Write `E:\Master_Thesis\planning\grok_local_repair\GROK_W6_IMPLEMENTATION_REPORT.md`: changed files, actual commands/tests, output paths, lock/bundle evidence, remaining W7/W8/real-data gaps. Return code for Sol review. Do not commit or push.
