# Paper B next implementation: W5 and real-source readiness

Work in `E:\Master_Thesis\master-thesis`. Write actual code; do not delegate, commit or push. Preserve unrelated changes. Sol will independently review your work.

Read AGENTS.md, CONTEXT.md, specs/B/WORKFLOW_IMPLEMENTATION.md, ANALYSIS.md, tickets/BP1_prediction_engine.md, DATA_AND_SOURCES.md, SOURCE_MANIFEST.json, docs/validation/B_workflow/HANDOFF.md and REVIEW_ACCEPTANCE.md. W1-W4 now exist and include reviewer fixes: do not replace them or regress frozen-state/QC/hash checks.

## Deliverable 1: connected W5

Extend `tools/b_prediction` and connect it to `tools/b_workflow`. Reuse `tools/b_features/provider.py`. Preserve the original validated-TSV develop/evaluate interfaces and their tests.

1. Expand raw synthetic TCGA assay/specimen/covariate fixtures to at least 10 eligible patients with enough variation for meaningful nested fits. Preserve explicit synthetic labels and update source hashes. Do not lower the fixed five outer/five inner/five final folds or existing minimum sample requirements.
2. Add a deterministic adapter for ordered baseline and promoter columns. Fit the feature provider inside EVERY inner training partition, outer training partition and final tuning partition. Transform each corresponding held-out set using that fitted state. Never use W4's full-training state to select nested-CV probes.
3. Tune baseline/extended models under the existing B-P1 contract. Compare on identical held-out patients; record fold-specific exclusions. Fail explicitly on insufficient eligible training/validation rows rather than changing folds, imputing silently or skipping failed candidates.
4. Freeze the final full-development feature state beside the final model, pin its hash, and preserve fold states, patient splits, tuning evidence, paired predictions and lineage. Add b_prediction to workflow code identity. Resume must invalidate W5 when a relevant ancestor/code/config changes.
5. Add a held-out-beta perturbation regression proving inner-training probe selection is unchanged, frozen-state tamper rejection and original-interface compatibility tests.
6. Deliver `python -m tools.b_workflow run --mode synthetic --config specs/B/workflow.synthetic.json --output NEW_RUN --through W5`. It must perform actual feature fitting and ridge training. A default full run must stop honestly at the first unimplemented stage, with pipeline_complete=false. Do not fabricate W6-W8 outputs or weaken future graph/explanation requirements.

## Deliverable 2: start real-source preparation, not more synthetic-only infrastructure

Use the source manifest and existing evidence to implement an explicit real-source audit/preparation entry point that does NOT compute expression scores or fit models. Audit actual available files or permitted public metadata, exact source identities, access tiers, checksums, sizes and remaining coverage/identity requirements. Missing sources must be reported as missing, not replaced with synthetic files. Controlled sources remain blocked without access. Before acquisition, enforce expected_decompressed_size and reject credential-bearing URLs without leaking secrets; record compression and source provenance. Keep large/private data outside git. Record actual network/file checks separately from proposed checks. Do not run real biological analyses until applicable contracts are frozen.

Real readiness output must distinguish confirmed source evidence, missing files, unresolved specimen/annotation/purity policies and unimplemented processing. Source unavailability must not prevent completing the W5 software deliverable.

## Verification and handoff

Use `E:\Master_Thesis\.venvs\paper-b-20260911\Scripts\python.exe`.

Run `python tools/check_paper_b.py`, focused new leakage tests, a fresh connected W5 run and a resume test. No skipped tests count as passing. Preserve original specimens/gene-set scope, including HOPE, IFNG, Ayers and M0-M6; do not invent scoring defaults. Follow existing approved AIU access instructions for isolated server testing if available; record exact commands and outcomes or explicit pending status. Never change shared environments or bypass access restrictions.

Write `E:\Master_Thesis\planning\grok_local_repair\GROK_W5_IMPLEMENTATION_REPORT.md` with changed files, commands, actual test counts, output paths, real-source evidence, server receipts/pending status and remaining W6-W8 work. No commits or pushes. Do not edit the scientific spec or redefine endpoints to make tests pass.
