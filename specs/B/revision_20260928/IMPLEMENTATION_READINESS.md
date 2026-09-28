# Software reuse, implementation tickets and readiness

PROPOSED. This review changes documentation only. No application code, cohort files, historical decisions or production configuration is modified.

## Reuse assessment at inspected main

| Component | Reuse classification | Evidence state and required action |
|---|---|---|
| B-F1 format inspectors | Reusable after source/config review | Existing code and historical real-format/synthetic receipts; not a new whole-cohort validation |
| B-G1 registry | Reusable after scientific/config update | Registry and historical synthetic acceptance; real normalized coverage still gated |
| B-G2 annotation normalizer | Reusable after source/config update | Implemented despite stale specification-only text; official normalized exports not established |
| W1/W2 planning/acquisition | Reusable after adapter review | Existing connected fixture workflow; qualify new objects, sizes, hashes and access |
| W3 identity/cohort import | Needs extension/refactoring | New clinical timelines, modality relations and source-specific specimen evidence; do not assume suffix joins suffice |
| W4/W5 feature development | Reusable after scientific release/refactoring | Inspected fold-local fit/transform inside inner/outer/final training partitions; current connected path explicitly rejects non-fixture policy |
| W6 locked evaluation | Reusable after reviewed real-data release | Inspected no-refit bundle/hash checks; current connected lock is synthetic-only; external identity checks need source overlap ledger |
| W7 report | Reusable reporting infrastructure | Historical partial synthetic APM report, not the revised paper-wide four figures |
| W8 secondary/handoff | Needs scientific/config extension | Fictional score/query fixtures; named programmes, MethylCIBERSORT and LUAD blocked |
| Expanded omics/composition/scRNA/spatial adapters | Not established as implemented | Must inspect owned paths and implement only admitted modules after freeze |
| Historical status prose/issues | Obsolete statements mixed with current evidence | Reconcile by dated receipts and actual code; never discard historical failures |

No component is newly certified real-data validated by this review. Historical local W8 receipt: 147 passing, zero skipped; historical AIU W5 strict receipt: 115/116 with missing approved real fixture, while connected synthetic W1–W5/resume passed. AIU W6–W8 acceptance remains pending in inspected records. Current runtime tests were not rerun because a complete checkout was not available; no green status is inferred from code inspection.

## Bounded tickets and acceptance

| Ticket | Dependencies and scope | Deliverable / acceptance |
|---|---|---|
| R00 authority and audit completion | This review | Approve scientific scope/contrast proposal; finish unread spec/schema/test artifacts; resolve stale text by dated additive decisions. Do not change B-P. |
| R01 source/identity census | R00; no endpoint scoring | Original-study/object manifest, clinical timeline, overlap/exposure ledgers, per-view and specimen-linked N; source-specific processed object/terms verified. UNKNOWN remains explicit. |
| R02 A product admission | R00; frozen A export | Effect estimates separate from predictor; source/test exposure, scoring, directions and coverage validated. No A output means affected B analyses blocked. |
| R03 P/U/Q and B-P population | R01 | Outcome-independent measurement maps; technical-replicate rule; non-RNA baseline comparability; eligibility and precision contract; signed freeze before modelling. |
| R04 broader scientific freeze | R01/R02 | Exact prostate contrasts, programme/gene families, effect models, alternatives, candidate selection and validation populations. User approval for material changes. |
| I01 isolate and reproduce baseline software | Approved execution environment | Unchanged current strict suite and synthetic run/resume; actual versions/hashes/failures; missing real-fixture gate not silently skipped. AIU preferred. |
| I02 source/clinical adapters | R01/I01 | TDD for identity, clinical-state and units; duplicate origins do not increase N; unknown history cannot become untreated. |
| I03 regulatory/composition layer | R04/I02 | Only frozen models/references; hand-calculated synthetic/adversarial oracles; same-patient sensitivity comparisons; all evidence states retained. |
| I04 APM real-contract adapter | R03/I01/I02 | Preserve fold-local state and no-refit separation; prohibit fixture-lock promotion; independent scientific/code review. |
| I05 bounded source tracer | I02–I04 as applicable | Small real-format/source check without reserved external endpoint exploration; source and config lineage validated. Exit 0 alone is not biological validation. |
| G01 real-analysis release | R03/R04/I05 | Scientific contracts, environment and actual input hashes frozen; explicit production permission. |
| A01 discovery | G01 | TCGA-only results, uncertainty and nulls; Freeze D handoff before CPC/C outcomes. |
| A02 external evaluation | A01/final model lock | Locked B-P and separately frozen association-replication analyses; append evidence without candidate reselection. |
| A03 optional orthogonal module | Own source/analysis gates | One source-qualified cellular/protein/ATAC/spatial analysis only when it resolves a named question. |
| A04 manuscript reproduction | A01–A03 applicable | Four traceable figures, full exclusions/negative results, clean approved rerun and limits. |

Independent documentation/source-metadata tasks can run in parallel with disjoint ownership. Do not parallelise uncontrolled access to reserved CPC outcomes. Existing one-production-paper-at-a-time governance is unchanged.

## Adversarial tests to add after design approval

Test patient/reanalysis duplication; different-focus ambiguity; unknown treatment versus verified naive; same-patient/different-assay denominators; portal TCGA contamination; mislabeled SNP-agreement purity; percent versus fraction; source detection-P direction; shared promoter probes and strand boundaries; cross-platform gene conflicts; absent target versus measured zero; compositional rank deficiency; donor versus cell bootstrap; spatial spot/cell semantics; fold-local feature mutation; external Y mutation preserving training and discovery handoff; negative/undefined Delta_R2; external evidence appended without candidate mutation; one-direction C query rejected; fixture receipts rejected as production approval.

These are acceptance requirements, not tests written or passed by this documentation review. Preserve existing valid regression tests. TDD applies to later implementation; do not rewrite science to satisfy a test expecting desired biology.

## Readiness and unresolved decisions

Release is blocked until: approved proposed scope/reference axes; actual A products for A-derived analyses; exact P/U/Q and source-compatible score; specimen/replicate policy; baseline purity/age/grade compatibility; eligible N and precision; source-specific omics/composition references; statistical families; exposure/overlap ledger; independent code/spec review and actual environment/test receipts.

Strategic approval requested: adopt this prostate-centred evidence architecture and the proposed within-prostate tumour/adjacent comparison as a separately named discovery/query axis, while retaining LUAD and B-P unchanged. Remaining factual questions should be resolved by source audits, not broad questions to the user.

Institutional amendment status, final Arbet methods/overlap, current local dirty work, AIU execution state and complete current test status remain UNKNOWN. A proposed spec can be review-ready while its biological analysis is not execution-ready; do not collapse those labels.
