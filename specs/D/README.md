# Paper D conditional specification kit

**PROPOSED / NOT IMPLEMENTATION-READY — v0.1, 2026-09-05.** No checkpoint inference or scientific benchmark has run. D remains an active paper idea. Earlier recommendations to defer are reviewable recommendations, not user acceptance of cancellation.

## Problem and proposed answer

Can a released virtual-cell model predict independently measured prostate chemical-perturbation expression changes more accurately than the same drug's average response in other training contexts? The required evidence is a compatible measured prostate test set and an auditable pretrained model, not a successful inference command. This conditional design preserves that question while identifying missing inputs.

Proposed primary task: **held-out prostate context, supported chemical treatment**. It is not globally unseen-drug prediction. Candidate model: State Transition `ST-HVG-Tahoe`, revision `ca6b751972493f8448e3256d1340ae70ad43e1e7`, zeroshot run's `checkpoints/final.ckpt`, subject to the compatibility gates below. Selecting `final` here avoids choosing a checkpoint after viewing our test results; its execution and provenance remain unverified. The alternative SE-based family is not a second co-primary model. Substitution requires an amendment before test access.

The thesis interface is evaluation of reliability of predicted perturbation evidence. D neither supplies patient ICI-response validation nor replaces the registered wet lab. B/C outputs may inform a secondary fixed immune-program analysis, but cannot train or tune the primary test after its outcomes are opened. Default programme order remains B, C, A, then D if gates pass.

## Novelty and claim ceiling

| Closest precedent | Already addressed | Proposed addition requiring evidence |
|---|---|---|
| State, Cell 2026, [10.1016/j.cell.2026.07.052](https://doi.org/10.1016/j.cell.2026.07.052) | Perturbation prediction and model evaluation | Independent prostate-context reliability under explicit drug vocabulary, assay and overlap constraints. |
| Systema, [10.1038/s41587-025-02777-8](https://www.nature.com/articles/s41587-025-02777-8) | Systematic response components and informative baselines in genetic datasets | Chemical-context evidence beyond shared drug effects; its genetic results do not establish chemical-model failure. |
| Ahlmann-Eltze et al., [10.1038/s41592-025-02772-6](https://doi.org/10.1038/s41592-025-02772-6) | Strong simple baselines for perturbation prediction | A fair comparison with equivalent permitted training information. |
| Mao et al., [arXiv:2604.27646](https://arxiv.org/abs/2604.27646), preprint | Cross-dataset/context/perturbation evaluation | A distinct prostate application with real compatible ground truth; not a relabelled general benchmark. |

This bounded comparison does not establish absence of an identical study. Novelty must be revisited when the actual test dataset is selected. Positive results support prediction accuracy for the declared benchmark population and representation only. Null/negative gains are valid results, not failed software. No claim of clinical benefit, immune killing, TME conversion or compound-class superiority follows.

## Research-user requirements

1. As a thesis researcher, identify whether a prostate test is actually eligible before allocating inference resources.
2. As an analyst, distinguish checkpoint-supported treatments from unknown vocabulary entries and model fallbacks.
3. As a reviewer, trace every sample, feature and checkpoint to immutable provenance and declared overlap.
4. As an evaluator, compare changes in the same expression representation with a meaningful baseline.
5. As an examiner, see which uncertainty is between biological units and which is computational sampling variation.
6. As a collaborator, reproduce the result on AIU without using outcome data in preprocessing or model selection.
7. As a supervisor, distinguish a software reproduction on nonprostate data from the thesis paper's evidence.
8. As a maintainer, resume an interrupted run without silently replacing files, inputs or checkpoints.

## Kit map and GOAL coverage

| GOAL deliverable | Location |
|---|---|
| 1 Scope/protocol/novelty/claim limits | This file |
| 2 Coverage, sources and real metadata evidence | DATA_AND_SOURCES.md; SOURCE_MANIFEST.json |
| 3 Exact primary analysis, inclusion, missingness, precision | ANALYSIS.md |
| 4 Validation and grouping | VALIDATION_AND_FIGURES.md |
| 5 Four figures | VALIDATION_AND_FIGURES.md |
| 6 Preregistration, decisions, evidence, glossary, citations | PREREGISTRATION_AND_LEDGER.md and linked source URLs throughout |
| 7 Architecture, versions, schemas, environment | SOFTWARE_CONTRACT.md; environment.contract.json |
| 8 Bounded tickets | TICKETS_AND_TESTS.md |
| 9 Meaningful tests | TICKETS_AND_TESTS.md |
| 10 Reproduction and readiness | REPRODUCE_AND_READINESS.md |

All ten categories are designed here; that does not mean their factual prerequisites are satisfied or review completed. No production ticket is ready. The research tickets can resolve the blockers without changing the paper's objective.

## Reviewable disposition criteria

**Proceed:** all G1–G8 gates in REPRODUCE_AND_READINESS pass and independent reviews approve the frozen contract. **Narrow:** a real prostate benchmark supports fewer contexts or drugs; report that target population and amend before outcomes, with user-visible scope review. **Combine:** if only a well-defined external-transfer analysis is defensible, propose a C appendix without describing native single-cell validation. **Defer execution:** if compatible prostate ground truth, training evidence or runtime cannot be obtained within the feasibility allocation. D stays an active conditional idea until the user accepts another disposition. Nonprostate reproduction alone cannot satisfy any prostate evidence gate.
