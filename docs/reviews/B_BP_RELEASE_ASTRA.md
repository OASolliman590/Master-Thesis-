# Astra release review: selected B-P spec and B-P1 coding

6 September 2026. Decision: RELEASE B-P1 for bounded implementation and synthetic software tests only. The user chose B-P and authorized coding. The all-four-kit M1 review is already complete; this release does not authorize other papers or an actual biological model run.

Reviewed Sol's B_BP_SPEC_HANDOFF.md, exact BP1 ticket, selected-primary spec changes, prior measurement source/checkpoint and Sol packaging dispositions. The B-P estimand, identical external patient set, TCGA-only fitting/tuning, no-refit evaluation and preserved historical B-R status agree with the user decision. No further broad review cycle is required before this bounded coding task.

The parent independently reconciled all31 retained measurement artifact hashes with zero errors. The four offline cache-provenance tests passed in the parent check (1.551 seconds); the repaired helper preserves retrieved time and fails mismatched receipts. The absent inventory and omitted peer receipts are resolved. Historical source reports retain their audit-time wording under an explicit wrapper/restore guide. The parent inspected the corrected helper directly; no new source retrieval was run.

The BP1 release addendum specifies checksum boundaries, synthetic TSV provenance, all-undefined bootstrap handling, no-predictor failure and the upstream feature-selection limitation. These are bounded engineering clarifications, not changes to primary/gene/measurement policies. No arbitrary successful-result threshold is added.

Fresh AIU read-only import check: Python3.11.16, NumPy2.4.6, SciPy1.17.1, scikit-learn1.9.0 and threadpoolctl3.6.0 available. No environment changed or cohort model run. Local bundled Python3.12 lacks SciPy; use the available AIU runtime for numerical acceptance when code is ready, or record pending tests if connectivity fails. Spark may develop locally in the three owned paths and use a uniquely scoped AIU scratch directory for synthetic tests under the dispatch brief; no shared environment/data changes.

One accountable implementation: Spark through the approved heavy lane. Owned paths tools/b_prediction, tests/b_prediction, docs/validation/B_prediction. No commits by Spark. Parent inspects the result and one independent code review before implementation publication. Initial B-F1 final Opus/AIU validations remain separate outstanding items; this release does not mark those passed.

Remaining science: program/P and U, promoter Q/QC, clinical/specimen matching, covariate comparability, eligible population and precision. The separate AIU historical-list inventory may inform those choices but is not an automatic endpoint replacement. Tangible engineering acceptance is runnable develop/evaluate commands with outputs and verified leakage/arithmetic tests, followed by a real molecular result only after admitted inputs.
