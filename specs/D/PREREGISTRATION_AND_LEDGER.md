# D preregistration draft and evidence ledger

**PROPOSED / NOT IMPLEMENTATION-READY — v0.1.** This file is a draft and has not been externally preregistered or independently approved. Git timestamps document changes, not prospective registration.

## Registration record to complete

Title proposal: *Independent-context evaluation of a virtual-cell model for measured prostate drug responses*. Primary hypothesis/estimand: ANALYSIS.md theta, positive gain over the fixed same-supported-drug baseline. Candidate checkpoint and revision: README. Prior exposure: the team has inspected published State findings, model metadata, vocabulary/splits and historical prostate bulk/LINCS metadata; no D prostate prediction or response matrix was analysed for this kit. Preserve all later access dates. No results-dependent “preregistration” claim is permissible.

Before external registration: identify the actual test accession and independent units; settle exact transform/features, biological grouping, baseline training rows, precision target, final checkpoint hash, source licences and split lineage; freeze secondary analyses and multiplicity families; archive a reviewed spec hash and sealed test manifest. Registration service and institutional requirements are unknown, so no registration identifier or permission is invented. Any analyses of previously inspected outcomes must be marked retrospective/development.

## Evidence-grounded grilling ledger

All rows were assessed 2026-09-05. Scientific citations below and exact artifact checksums in SOURCE_MANIFEST.json form the citation library; no unsupported BibTeX author/title expansion is required.

| ID / question | Answer; type | Source/field and verification | Uncertainty; spec effect; decision |
|---|---|---|---|
| D-Q01 Is a chemical State model real? | Manifest/config exist; **verified fact** | ST-HVG-Tahoe API revision; `siblings` and `pert_col` | Weights/runtime not executed; candidate only. |
| D-Q02 Does “State” alone specify the prediction tool? | SE and ST are different stages; **verified fact** | [Official repository](https://github.com/ArcInstitute/state); pinned package/config | Use HVG-ST candidate, not an embedding-only model. |
| D-Q03 Are unseen categorical drugs supported? | Inspected inference source falls back for absent labels; **verified source behaviour**, not observed run | Pinned `_infer.py` in manifest, unknown-label branch | Wrapper must reject; no control-like result interpreted as efficacy/inefficacy. |
| D-Q04 Does a dimension count prove gene coverage? | No; **inference from metadata limits** | `var_dims.pkl` opcode inspection shows dimensions; ordered identifiers unresolved | G2 remains open. |
| D-Q05 Does the released split validate prostate? | Its five named test contexts do not include prostate; **verified manifest fact** | Pinned `zeroshot/generalization.toml` | Nonprostate reproduction cannot finish D. |
| D-Q06 Are all planned compounds represented? | Decitabine names found; queried other aliases absent; **literal audit fact** | `vocabulary_summary.json`, source vocabulary hash | Structure-level mapping unknown; do not infer universal absence or support. |
| D-Q07 Is complete independent prostate response data available? | **Unknown** | Existing evidence report has no native compatible joined manifest | G1/G3 blocked; no invented sample size. |
| D-Q08 What is the primary comparator? | Same supported drug–dose–duration mean in non-test training contexts; **design choice** | ANALYSIS formula, informed by [Systema](https://doi.org/10.1038/s41587-025-02777-8) and [simple baselines](https://doi.org/10.1038/s41592-025-02772-6) | Training rows required; choice proposed for review. |
| D-Q09 How should repetitions be weighted? | Equal drugs, then conditions, then biological units; **design choice** | ANALYSIS theta | Actual independent-unit structure unknown; no cell pseudoreplication. |
| D-Q10 Is precision adequate? | **Unknown** | No eligible design/variance evidence or agreed delta_min | G5 open; do not manufacture a powered study. |
| D-Q11 Is the niche novel? | Plausible prostate-specific question; **inference/proposal** | [State](https://doi.org/10.1016/j.cell.2026.07.052), [Mao preprint](https://arxiv.org/abs/2604.27646), README comparison | No exhaustive absence claim; revisit against selected dataset. |
| D-Q12 Must D be deferred? | Prior agent recommended deferral; **recommendation, not user decision** | GOAL preserves D as conditional | Complete design, retain idea and explicit research gates. |

## Proposed decision records

| ADR | Proposed decision | Rationale / alternatives | Acceptance |
|---|---|---|---|
| D-ADR01 | Native measured prostate response is the primary task. | Bulk/L1000 conversion changes measurement model; a separate transfer task is possible only by amendment. | Pending scientific review. |
| D-ADR02 | Candidate pinned final HVG-ST checkpoint; supported-treatment context transfer. | Avoid treating SE-only or genetic perturbations as chemical response models. SE-ST alternative adds pretraining/decoder requirements. | Pending compatibility and review. |
| D-ADR03 | Same-drug training-context baseline is primary; no-change secondary. | Shared effects can inflate apparent performance against no-change alone. No baseline selection from test outcomes. | Pending training access and review. |
| D-ADR04 | Hard rejection before upstream unknown-label/control fallback. | Upstream command success is insufficient evidence of semantic validity. | Proposed adapter invariant; not implemented. |
| D-ADR05 | Do not cancel D because gates remain open. | User requires every design kit and reviewable dispositions. | User scope requirement, implementation still conditional. |

## Glossary and amendment policy

Use the single canonical [CONTEXT.md](../../CONTEXT.md) glossary for context transfer, supported perturbation, native expression representation, independent biological unit, reproduction and unknown training overlap. The symbol T-expression in ANALYSIS.md denotes the selected checkpoint's native expression representation; its exact transform remains unresolved. Missing treatment support is not a negative biological effect.

Each amendment records date, author/reviewer role, previous/new decision, factual trigger, dataset/outcome exposure already incurred, affected figures/tickets and whether a new test is required. Never overwrite null results or historical choices. A final independent Opus review followed by Astra disposition is required; neither has reviewed this kit yet. GitHub issue URL, registration record, final review and Notion synchronization are pending orchestrator actions.
