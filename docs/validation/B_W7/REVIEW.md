# Paper B W7 traceable report checkpoint

Date: 11 September 2026. Status: local synthetic APM-component reporting implemented and reviewed; broader scientific figures and W8 remain open.

## Executable result

`tools.b_report` now consumes validated W3, W5 and W6 publications and emits four deterministic SVG figures, six machine-readable TSV source tables, `traceability.json`, `report.json`, a readable `report.md`, checksums, manifest and atomic completion record. W7 is connected to `tools.b_workflow`; `--through W7` succeeds and resume skips W1-W7. Default continuation reaches W7 and stops honestly at `stage-not-implemented:w8` with `pipeline_complete=false`.

The figures are deliberately limited to evidence present in the implemented APM component:

1. patient-level cohort/accountability flow and measured assay coverage;
2. the exact frozen promoter-probe state, with excluded probes and reasons;
3. W5 nested out-of-fold development predictions on identical axes;
4. W6 no-refit external predictions, Delta R2 and paired-bootstrap interval.

Every figure says `SYNTHETIC FIXTURE ONLY — NOT A BIOLOGICAL RESULT`. Each plotted scientific value is derived from a linked TSV and pinned to upstream artifact hashes. The report gives plain-language instructions, the supported software claim and the claim ceiling for every figure. It explicitly marks the broader immune-deficit/epigenetic/composition framework, MethylCIBERSORT and W8 as pending. It does not create an association, composition estimate, barrier score, clinical-response probability or B-to-C ranking.

The independent spec review initially found that W3 exclusions were omitted, Figure 3's displayed development Delta R2 lacked a mapped metrics table, and `report.md` did not link artifacts or fully explain colours/intervals. All three were corrected. The standards review found duplicated publication verification and a large orchestration function; the verifier is now shared in `tools.b_workflow.io`, and pure flow/probe/prediction builders were extracted from the report orchestration.

## Verification and receipt

- W7 focused suite: 6 tests passed, covering four-figure presence, source-table hashes, scope labels, metric preservation, deterministic payloads, W3 patient/specimen exclusion accounting, parent tamper rejection and resume.
- Final post-review strict Paper B acceptance: 133 tests passed, zero skipped, 219.248 seconds.
- Fresh run: `tmp/paper_b_checks/w7_fresh_reviewed_20260911` executed W1-W7; code identity `6417d623242878b21ca25a3aa49d92515d58a60524f67c4ea8ce06e13aea739e`; `pipeline_complete=false`.
- Resume executed no stage and skipped W1-W7.
- W7 `COMPLETE.json` pins four figures and the full artifact manifest. The attempted in-app SVG preview could not attach to a local-file browser tab; structural SVG checks, byte-level determinism and source traceability passed. This is recorded as a UI-preview limitation, not an AIU test.

## Remaining boundary

This checkpoint satisfies the executable partial-report allowance in `IMMUNE_BARRIER_FRAMEWORK.md`; it does not close the revised four-figure scientific plan or ticket B-I6. Those require separately frozen prostate-deficit, methylation-association, composition and B-to-C nomination contracts and real-data authorization. Real execution remains behind E1-E4/E6 and an evaluation release. AIU execution remains pending.
