# Paper A — baseline clinical-reference Spec Kit v1.0.0

**Architectural specification completed for review on 15 October 2026; real-data execution NOT released.** Controlling decision: ../../docs/decisions/A_A1_INTEGRATED_SPEC_20261015.md. A separate directory for A1 expresses a distinct analysis workstream, not a promised second publication.

## Question and products

Which pretreatment immune-expression programmes are reproducibly associated with objective ICI response, how do they vary by cancer/regimen, and how well does one frozen learned score discriminate response in independent studies?

A-BIO exports effects, uncertainty, context and contradictory evidence. A-PRED exports a reproducible frozen score and honestly labelled validation. A-BIO does not require A-PRED to beat CYT. Neither establishes a treatment effect, tumour-cell mechanism, epigenetic reversibility or prostate ICI efficacy.

## Single primary and secondary hierarchy

A-P2 is the selected primary: paired learned-score minus CYT AUROC on identical ORR-evaluable independent-test patients, averaged with equal cancer weights and equal study weights within cancer. A-P1 is a secondary fixed-CYT DCR-minus-ORR endpoint-sensitivity contrast. Baseline biological discovery is a prespecified secondary evidence product, not a second predictive primary. Composition, orthogonal modalities, qualified transport and additional comparators have branch-specific releases. A1 owns longitudinal response-associated change.

## Read in order

SCIENTIFIC_AIM_AND_CLAIMS.md; PREREGISTRATION_AND_DECISIONS.md; DATA_ACQUISITION.md; PATIENT_DATA_MODEL.md; ASSAY_PROCESSING_CONTRACT.md; BASELINE_BIOLOGICAL_ANALYSIS.md; PREDICTION_ANALYSIS.md; ENDPOINT_SENSITIVITY.md; VALIDATION_AND_SPLITS.md; A_TO_BC_HANDOFF.md; TICKETS_AND_TESTS.md; REPRODUCE_AND_READINESS.md. FIGURES.md specifies panel-level claims and no-result rules. NUMERICAL_FREEZE_REGISTER.tsv distinguishes selected architecture from unresolved numerical values.

All study, patient, treatment, specimen, assay, endpoint and split identities belong to ../A_DATA_ACQUISITION_VALIDATION. The wrappers PATIENT_MATRIX_SCHEMA.json and SOURCE_RECORD_SCHEMA.json point to that authority. A's analysis configuration must reference admission and matrix receipts; no ad hoc inclusion spreadsheet is accepted.

## First bounded implementation packet

../../docs/execution/PAPER_A_A1_PACKET_01.md permits code/data inventory, exact hash reconciliation, synthetic contract tests and separately gated format tracers. It does not permit response-associated analysis, feature selection, model fitting, score production or final-test release. The standalone Codex instruction is ../../docs/execution/PAPER_A_A1_CODEX_HANDOFF.md.

## History and dependencies

The original A tree, including tickets, is preserved in ../../reference/specs_A_before_20261015. The old ANALYSIS/DATA/DISCOVERY/ENGINEERING/TRANSPORT/PREREGISTRATION entry points now route to current contracts. The acquisition package from draft PR #9 is inherited, not duplicated. Draft PR #6 is explicitly reconciled, not silently adopted. No change is made to the selected Paper B primary or Paper C drug architecture.
