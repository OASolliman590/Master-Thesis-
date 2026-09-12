# S0 — Evidence expansion and scientific execution kit

Version 0.1, 12 September 2026. **User-authorized design direction; technical proposal awaiting review and source admission.** This is a shared kit, not Paper E. No numerical primary endpoint, new cohort eligibility, independent-test designation or institutional amendment is frozen by its creation.

Start with [the roadmap](../../START_HERE.md). Existing A/B/C/D specifications remain in force except for a later explicitly accepted, versioned amendment. In particular, preserve A-P2, the fixed B-P APM validation module, the full Paper C source architecture and D's independent-benchmark requirements. Do not change the wet-lab plan in this kit.

## Scope in one table

| User request | Contract in this kit | Status |
|---|---|---|
| Expand data for every paper | Original-study search and processed-object admission across clinical, patient-molecular and perturbational sources | Source work can start; all new eligibility unknown |
| Reuse old progress | Selected-component audit, keeping the recovered archive immutable | Initial source-level issues recorded; no legacy rerun |
| Pre/on/post and R/NR comparisons | Separate baseline, follow-up and paired-change estimands | Proposed analysis modules |
| CIBERSORT, ESTIMATE, MethylCIBERSORT | Qualified composition evidence with correct output meanings | Exact implementation/reference/version contracts pending |
| Paired methylation/RNA, proteins, single-cell and spatial | Modality-specific branches with specimen-level pairing and patient-level inference | Conditional on processed object and metadata coverage |
| Extensive TCGA multi-omics and stage analysis | Prostate-centred, within-cancer-first molecular and clinical characterization | Not clinical ICI validation |
| MOFA2 and DIABLO/mixOmics | Unsupervised variation versus supervised observed-outcome integration | No interchangeable algorithm use or pseudo-label validation |
| Drug/class/cancer synthesis | Within-study effects, stratified synthesis, interaction tests and conditional comparative-trial review | No automatic clinical NMA |
| Easier future implementation | Owned tickets, explicit inputs/outputs/tests, small vertical slices and prompts | No agent dispatched by this document |

## Read in this order

1. `DATA_CONTRACT.md`: sources, assays, patients and permitted processing.
2. `A_BIOLOGICAL_DISCOVERY.md` and `A1_LONGITUDINAL_META.md`: clinical baseline and longitudinal questions.
3. `B_TCGA_MULTIOMICS.md`, `CELLULAR_SPATIAL.md` and `CD_PERTURBATION.md`: downstream context and orthogonal evidence.
4. `TASKS.md` and `CODEX_PROMPTS.md`: implementation handoffs.
5. `REFERENCES_AND_NOVELTY.md`, `source_search_plan.tsv` and `source_record.schema.json`: cited leads and machine-readable starting contracts.

## Definition of completion

S0 inventory completion means the search strategy, original-study crosswalk, coverage/missingness report, data access classification, prior-exposure ledger and selected legacy-reuse assessment have been reviewed. It does not mean the scientific pipeline is complete.

A module is ready for real analysis only when its source set, estimand, units, grouping, transformations, exclusions, uncertainty, multiplicity and validation boundary are fixed in a release receipt. Proposed software can be tested before that receipt, but cannot silently choose scientific settings from results. A unavailable optional module must not stop an otherwise valid core analysis; its evidence must remain visibly missing.

Unresolved choices are decision items, not reasons to restart the whole project. Source search is deliberately broad; the production analysis set is deliberately evidence-limited.
