# D validation and evidence figures

**PROPOSED / NOT IMPLEMENTATION-READY — v0.1.** No test dataset or completed inference is available. The following are contracts to review, not achieved validation.

## Information boundaries

Maintain four disjoint roles: model training provenance; development/adapter checks; frozen prostate test inputs; sealed prostate test outcomes. The selected training checkpoint may have seen a drug elsewhere: that is permitted for the proposed supported-treatment/context-transfer task, disclosed explicitly, and required for the primary same-drug baseline. It may not have seen the prostate test condition's measured responses. All cells, replicate measurements and technical subdivisions of an assigned test condition remain together. Shared controls are linked and must not be counted repeatedly as independent experiments.

For the proposed whole-context transfer claim, **every perturbation response from each test prostate context must be absent from transition training and tuning**, not just the selected drug conditions. A checkpoint that saw other treatment responses from that context supports a different within-context task; it cannot pass this primary claim through a condition-only split. Audit context aliases and originating models as well as exact sample IDs. Untreated observational pretraining exposure is separately disclosed and assessed, not conflated with transition-response training.

The outcome store is unavailable to the inference and baseline builders. Inference receives eligible baseline expression plus requested supported condition labels, not actual treated RNA rows. An evaluator joins predictions and truth only after checkpoint/transform/gene order/labels/baselines/eligibility are sealed. A test outcome used to select preprocessing or checkpoints converts that dataset to development and requires a new independent test; merely changing its split flag does not undo exposure.

No random cell split can establish biological context transfer. A source-study or experiment split is required where the task claims independent-study generalisation; absent that, state the narrower unit of held-out context actually supported. Preprocessing choices that use outcomes, including HVG selection, gene filters, scaling and threshold selection, are prohibited. The frozen checkpoint output list determines primary features. Source annotations may establish tissue/model identity but may not tune effect thresholds.

## Two pretraining audits

**Transition training:** map each selected checkpoint to code, config, final weights hash, split manifest and actual source rows. The released TOML's author-local directory and context labels are not proof that the binary checkpoint used exactly those rows. Resolve accession, sample, replicate and context overlap; record exact match, plausible shared origin, excluded, or unknown separately.

**Embedding pretraining:** the primary candidate is the HVG-input family, so it does not require running SE as the input encoder. Still inspect checkpoint initialisation and dependencies rather than assume no pretrained subcomponent. If the SE family is proposed instead, separately audit SE observational training and ST perturbation training; pretrained exposure to untreated contexts is not identical to leakage of response labels. Such a switch changes the contract and needs a pre-test amendment. [State official source](https://github.com/ArcInstitute/state), [candidate config](https://huggingface.co/arcinstitute/ST-HVG-Tahoe/resolve/ca6b751972493f8448e3256d1340ae70ad43e1e7/zeroshot/state_generalization_zeroshot_X_hvg/config.yaml).

Unknown overlap blocks an **independent-test** claim. It must not be relabelled “unseen” through model/reviewer agreement. The published nonprostate Tahoe split is a reproduction fixture only. Its reproduced metrics, even perfect, leave G1/G3 prostate evidence open.

## Four-figure outline

| Figure/panel | Question and source | Analysis and uncertainty display | Permitted claim |
|---|---|---|---|
| 1A Source flow | What data and checkpoint are actually eligible? All-source manifest | Counts by source, context, condition and independent unit; attrition reasons | Scope and missingness, not performance. |
| 1B Vocabulary/feature compatibility | Which test conditions and output features are supported? Frozen mappings/config | Coverage heatmap; distinguish unsupported, missing, inferred and measured | Exact admissible coverage. |
| 1C Overlap | Is the test independent? Checkpoint/source lineage | Training–development–test overlap diagram with unknown categories | Only verified independence. |
| 2A Primary paired gain | Does State improve on the primary baseline? Sealed prostate responses/predictions | Per-drug equal-weight gains plus theta and justified block interval; show descriptive-only status if interval gate fails | Comparative error on declared target population. |
| 2B Constituent errors | Is apparent gain driven by weak reference performance? Same data | State/baseline losses side by side; independent-unit denominators | Absolute scale and comparison fairness. |
| 2C Baseline sensitivity | Does comparison depend on baseline choice? Frozen secondary baseline outputs | No-change/global-average/other approved development-trained baselines, clearly secondary | Robustness, not reselected primary success. |
| 3A Biological subset | Is accuracy useful for a fixed immune program? Frozen B/C or literature gene list and measured overlap | Gene-level change errors with coverage and uncertainty | Program-specific prediction accuracy only. |
| 3B Discrimination | Are predictions condition-specific? Held-out condition effects | Prespecified descriptive condition-discrimination metric and uncertainty if support permits | Separation of distinct observed responses. |
| 3C Reproducibility reference | How noisy are measured responses? Independent observed replicates | Replicate–replicate differences; distinguish technical/cell-sampling variability | Empirical measurement variation, not a universal ceiling. |
| 4A Heterogeneity | Where does performance differ? Same frozen test | Gains by model context, dose metadata and observed signal strength; no outcome-based exclusion | Descriptive applicability limits. |
| 4B Failures | What could not be predicted? All eligible/requested conditions | Failure/missingness categories including unsupported labels and inference failures | Transparent coverage and operational limitations. |
| 4C Stability | Is result sensitive to computation? Repeated fixed-input seeds, approved sensitivities | Variation separated from biological uncertainty | Computational reproducibility. |

If the primary dataset is unavailable, these figures remain planned. A figure consisting only of catalogue metadata does not constitute Figure 2–4 completion. No TME or ICI response figures are implied by molecular prediction metrics.
