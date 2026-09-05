# D proposed bounded tickets and test plan

**PROPOSED / NOT IMPLEMENTATION-READY — v0.1.** No production child issue is dispatchable. Research tasks may resolve prerequisites; all code tasks below require the reviewed four-kit programme gate and sequential implementation order. The orchestrator owns issue publication, commits and milestone pushes.

## Ticket contracts

| Ticket | Dependency / ownership | Bounded deliverable and acceptance | Restart/review |
|---|---|---|---|
| D-R01 Prostate data eligibility | No code dependency; owns D source/coverage research additions only | Identify an actual accession and joined sample/condition/control/replicate manifest; document modalities, terms, feature and exposure coverage. Accept only evidence for real prostate response ground truth; a baseline cohort is insufficient. | Resume accession audit from checksums; scientific Opus review then Astra disposition. No matrices beyond approved resource bounds. |
| D-R02 Checkpoint lineage and vocabulary | D-R01 can run independently; owns checkpoint/overlap research records only | Resolve selected final checkpoint source rows, label/structure mappings, full ordered features and transform; differentiate train/validation/test and unknown origins. | Retain exact model revision; no replacement on failed metadata lookup. Review of every mapping/unknown. |
| D-R03 Precision and analysis freeze | R01+R02; owns D statistical decisions/preregistration amendment only | Populate independent clusters, delta_min and h_target from documented rationale; evaluate precision using eligible design; freeze baseline training rows and primary inference interpretation. | No held-out outcomes for choice. A recommendation to narrow requires visible review. |
| D-I01 Bundle validator | G1–G5 scientific gates approved; owns proposed D validation module and boundary tests | Implement source/sample/feature/control/vocabulary/overlap checks producing typed eligibility and immutable seal. Acceptance includes real metadata smoke fixture and adversarial rejections below. | Metadata-only stages cached by content; independent code review. |
| D-I02 AIU runtime reproduction | G6 plus all-four-kit review and a separately released bounded feasibility contract; owns D environment recipe and upstream adapter | Produce exact lock/runtime manifest; load the pinned checkpoint and run a bounded known-label **nonprostate** reproduction with verified output placement. This establishes G7 and therefore does not require G7 in advance. A minimal reproduction-fixture validator is part of this ticket; prostate production I01 is not its prerequisite. Classify only as software reproduction. | Store scheduler handle, resource bounds and artifact hashes; no relaunch until handle checked. Review adapter semantics, not just imports. This ticket cannot pass prostate G1–G5. |
| D-I03 Baseline and metric kernel | I01; owns D baseline/evaluator modules and numerical tests | Build primary baseline from authorised training rows; implement theta/denominators without test leakage; match hand-worked answers and independent calculation. | Snapshot training-effects hash; stale input invalidates outputs. Review formula and grouping independently. |
| D-I04 Sealed prostate inference | I02+I03+all gates approved; owns D run configs/manifests, not outcome selection | Run predictions from baseline inputs only for sealed supported conditions; verify every eligible output. No hidden fallbacks or missing condition deletion. | Resume stage/hash-aware; inference failure blocks complete theta. Opus review and Astra release decision. |
| D-I05 Evaluation and figure bundle | I04; owns D evaluation outputs/report renderer | Join frozen truth, report primary/secondary results and failures; produce four figures with source tables and permitted reproduction bundle. | Keep all outcomes including nulls; rerun only for documented code/data amendment. Review statistics, provenance and claim limits. |

Proposed future code ownership is the paper-D module/test/workflow namespace chosen by the orchestrator at implementation; no unrelated shared schema edits without a separate interface ticket. GitHub IDs/URLs are pending publication. Ticket names are not implemented commands. Research completion cannot be used to mark inference tickets done.

## Meaningful acceptance tests

Synthetic tests verify software invariants only; label them synthetic in artifacts. Real-data smoke checks use permitted small source extracts after release and access review. Do not claim these tests passed: none has been implemented or run for D.

| Risk | Test at the benchmark-bundle boundary | Expected behaviour |
|---|---|---|
| Gain sign or formula error | Synthetic observed delta `[1,-1]`, baseline `[0,0]`, State `[1,-1]`; reverse State/baseline roles in second case | Theta +1 then -1 in the declared units. Independently calculate expected values, not via production helper. |
| Wrong hierarchical weights | Duplicate condition records for one drug; separately add more cells to one replicate | Exact duplicate IDs rejected. Cell replication does not change drug/condition/replicate weights; adding genuinely distinct conditions follows the declared denominator. |
| Cell pseudoreplication | Ten thousand cell rows sharing one biological-unit ID | Report one unit; no cell-bootstrap biological confidence interval. |
| Shared-control dependence | Two conditions share a control-set ID | Preserve dependency block in uncertainty handling; never manufacture independent controls. |
| Unknown drug fallback | Mutate a real vocabulary label to a missing label | Reject before model call; no control prediction enters accuracy table. |
| Dose/time confusion | Same drug with nonmatching categorical dose or unresolved duration | Typed unsupported/incompatible condition; no nearest-neighbour label substitution. |
| Feature ordering | Permute matrix columns while preserving names, then duplicate/remove one identifier | Explicit map can restore exact verified order; duplicates/missing primary features reject. Never trust dimension alone. |
| Representation mismatch | Label L1000 z-scores as counts, or repeat a bulk row as pseudo-cells | Reject incompatible provenance/representation; extension belongs to a different amended task. |
| Hidden control fallback | Valid label but no context/plate-matched control; only global controls remain | Reject or mark pending before upstream execution. |
| Test leakage | Alter held-out treated expression while predictions/baseline inputs remain sealed | Predictions and baseline hashes unchanged; only evaluation changes. |
| Source overlap | Same source sample re-exported under another accession or barcode prefix | Detect lineage conflict; block independent-test claim and report both source IDs. |
| Context leakage | A training response uses another drug in the same held-out prostate context | Block whole-context transfer claim even when the exact test condition is absent. |
| Control-weight mismatch | Two control replicates have unequal cell counts | Observed and predicted deltas use the same control identities and equal replicate weights; pooled-cell weighting is rejected. |
| Inference failure attrition | One eligible prediction missing/nonfinite | Retain failure in coverage; withhold complete-benchmark theta until reviewed repair, rather than average successful outputs. |
| Uncertainty implementation | Synthetic clustered units with shared controls compared with independent reference resampling | Match declared block handling; flag invalid design rather than assume exchangeability. |
| Scientific null | Valid model and baseline equal | Theta exactly zero; run can be technically complete with a null scientific result. |
| Interrupted job | Completion marker absent but process handle live/unknown | Poll same handle; never report passed or start duplicate work based on observation timeout. |

## Required real checks

Before I01 acceptance, recheck the downloaded official config, vocabulary label and split fixtures against their source hashes; these confirm parser/interface assumptions only. Before I02 acceptance, use actual known supported upstream data and confirm output feature placement and absence of fallback. Before I04 acceptance, inspect at least one complete real prostate condition/control join and compare its provenance against the frozen schema; that checks the route, not full biological validity. Before I05 acceptance, independently recalculate theta and denominators from exported replicate-level effects, then reproduce one primary figure from its source table. Broad scientific validation still requires the entire declared test scope.

Review evidence must record actual reviewer model/CLI and snapshot SHA. A favourable agent response is insufficient without inspected diff, meaningful tests and resolved findings. If AIU checks are deferred, the milestone is WIP, not validated.
