# Spec reconciliation — 29 October 2026

**Status:** a proposal for the user to review. It checks the frozen specs (RC2, 15 Oct, plus the 16 Oct immune-programme amendment) against the work done since then and the ideas the user raised on 29 Oct. **No spec file is changed here.** Any accepted change goes in as a new amendment under `specs/amendments/`, the same way the 16 Oct one did.

## 1. What each spec says, in one line

| Spec | Question | Selected primary | Secondary products |
| --- | --- | --- | --- |
| **A** (baseline) | Which pre-treatment immune programmes go with ICI response, and how well does one frozen learned score predict it in new studies? | **A-P2**: learned score minus CYT, AUROC on independent test patients (equal cancer weights) | **A-BIO**: baseline programme effects per cohort/cancer (discovery). **A-P1**: endpoint sensitivity, DCR vs ORR for fixed CYT |
| **A.1** (longitudinal) | Which programmes change on treatment, and does the change differ between R and NR? | Delta_g = mean change in R − mean change in NR, within a study and window | Cross-study synthesis (needs ≥2 families), regimen/sequence moderators, NMA feasibility, pharmacological context |
| **B** (prostate methylation) | Which prostate immune deficits have reproducible epigenetic correlates? | **B-P**: CPC-GENE external Delta_R2 of 8-promoter methylation beyond covariates, for the fixed APM expression score (TCGA-PRAD fit) | Immune-barrier framework, M0–M6 modules, PRAD/LUAD contrast, frozen handoff to C |
| **C** (epigenetic pharmacology) | Which measured epigenetic perturbations oppose the prostate immune-deficit signature? | Q_M vs Q_E (C3 framework, 15 Oct) | LINCS/DepMap/CCLE; registered wet-lab drugs **decitabine, entinostat, tazemetostat** |
| **D** (virtual cell) | Conditional benchmark | Paired MSE reduction | Deferral recommended, not accepted |

Programme rules in the spec README: about 600 researcher-hours over 4 months; one paper in production at a time; default order **B → C → A → D**.

## 2. How far each one is

| Spec | Done | Not done |
| --- | --- | --- |
| **Shared DAV (acquisition)** | Pipeline graduated to real sources. **Admitted for DEVELOPMENT:** GSE168204 (75,205 × 10), Hugo GSE78220 (25,263 × 26). Combination rule and registry. Expanded cohort search (ICBatlas, roster, epigenetic + ICI). | **Riaz GSE91061 is waiting for your final signature.** GSE176307 worksheet open. Parked: GSE115821, GSE126044. Large candidates not started: IMvigor210 (347), Liu (122), Gide, Van Allen, IMmotion150 mono arm, GSE343570 pembrolizumab-only arm. **No final-test family chosen**, and A-P2 needs one. |
| **A** | Synthetic-only scoring/AUROC prototype (`tools/a_analysis`), not committed. Novelty check. | No response-associated analysis (not authorized yet). Comparator memberships for IFN-γ, GEP, MHC-II and stromal not source-verified. |
| **A.1** | Spec only. | No on-treatment branch in DAV yet (needed for pairs). |
| **B** | W1–W8 synthetic software. **TCGA-PRAD downloaded and tabled** (493 samples, 60,660 genes, 203 promoter probes, checksums verified). | P/U/Q freeze; promoter-rule decision; CPC-GENE linkage (114 candidate code matches, specimen policy open). |
| **C, D** | Specs only. | Everything. |

## 3. The 29 Oct ideas against the specs

| Your idea (29 Oct) | Where the spec already covers it | Conflict or gap | Proposed revision |
| --- | --- | --- | --- |
| Genome-wide fair DE per study, R vs NR; meta-analysis per cancer and pan-cancer; 11 panels locked | **A-BIO** (baseline effects with cancer/regimen context, equal cancer weights) and `DISCOVERY.md` (original responder discovery) | A-BIO is defined at the programme level; genome-wide DE + FDR is not written out. The panels are not yet named as a locked confirmatory family. | Write A-BIO as two tiers: **genome-wide DE discovery** (per study → random-effects per cancer → pan-cancer, FDR) and a **locked 11-panel confirmatory family** with its own multiplicity. **Decision needed:** keep A-P2 (prediction) as primary, or promote A-BIO or A-P1. |
| Separate meta-analyses per endpoint (ORR vs clinical benefit) | **A-P1**, endpoint ontology; SOURCE_BINARY never merged with ORR | None | The novelty check says endpoint sensitivity is the less-covered part. Consider widening A-P1 from CYT-only to every locked panel + top DE genes. |
| Pre vs post treatment, comparative arms | **A.1** (contrast registry, pairing contract, NMA feasibility) | None; the spec is already more careful (association, not causal ICI effect) | No change. Add an on-treatment DAV branch when A.1 starts. |
| Exclude ICI + non-ICI drug; keep dual ICI; mixed studies keep the mono arm | Not in the specs | New cohort-selection rule | Add `COMBINATION_COHORTS_20261029.md` to the DAV amendment. |
| Paper B redoes Paper A's cohorts and analysis "as is" | — | **Conflicts with A.1/A:** B may not duplicate A's baseline results as independent evidence | B **consumes** A's frozen outputs (one shared code base and admitted tables); it does not re-run them as new evidence. |
| B: multi-cancer TCGA matched to the ICI cancers; MOFA+ / DIABLO; RNA + methylation + miRNA + RPPA (+ ATAC) | B-KIT v0.2 "proposed extra data types"; PRAD/LUAD contrast | **Conflicts with B's scope:** B is prostate-centred; the spec forbids cross-cancer pooling without a declared lineage model | Add **B-MX** as a new *secondary* module: per-cancer multi-omics first, pan-cancer only with a declared lineage/cancer model. **B-P stays the confirmatory primary.** |
| Prostate: transfer responder programmes to TCGA-PRAD | A "qualified prostate application", `PROSTATE_TRANSPORT.md`, B framework | None; matches the spec, and the novelty check rates it **novel** | Make it the explicit bridge between A and B in the amendment. |
| Methylation of the gene lists vs clinical outcome in TCGA | B framework (clinically anchored deficits) | TCGA treatment data are sparse; outcomes are survival/recurrence, not ICI response | Wording only: outcome = survival/BCR, not ICI response. |
| Epigenetic regulators in both papers | B module M6 (13 regulators) | None | No change. |
| Predictive model → ML/DL → equation → PK/PD | **A-PRED** (frozen learned score) | A deep model is not specified (and n is small). An equation export is not specified. A.1 forbids becoming a causal kinetic model. | Add an **equation export** of the frozen A-PRED score (sparse model; symbolic regression as a sensitivity check). PK/PD linkage goes in a discussion/future-work section, with C's pharmacology. |
| Epigenetic drug + ICI combinations (GSE248014 entinostat lead-in, GSE343570 vorinostat, guadecitabine studies) | **C** (epigenetic pharmacology), and the **registered wet-lab drugs include entinostat and decitabine** | Planned as a post-master's paper | **Decision needed:** these patient cohorts are exactly the "independent measured corroboration" that C lacks. Option: bring them into C as a small, pre-registered patient check, not a new paper. |
| The three-step chain (ICI genes → TCGA methylation → test in epi + ICI trials) | Pieces sit in A, B and C | No spec states the chain | State it in the amendment as the thesis's organising claim (the novelty check rates the chain **novel as a whole**). |

## 4. Process conflict to settle

The spec order is **B → C → A**, with one paper in production at a time. The work since 15 Oct has gone **A-first** (DAV admission), with B's TCGA download running in parallel. **Decision needed:** confirm the new order, for example "DAV + A-BIO first, B-P second, B-MX and C after", and whether two papers can be active at once.

## 5. Decisions for the user

1. **Paper A primary:** keep A-P2 (prediction AUROC vs CYT), or promote A-BIO (genome-wide DE + meta-analysis) or A-P1 (endpoint sensitivity)?
2. **Paper B scope:** accept B-P as the primary plus a new B-MX multi-cancer multi-omics secondary module?
3. **Combination cohorts:** use them inside C as patient corroboration now, or keep them for after the master's?
4. **Order and parallelism:** confirm the production order and how many papers run at once.
5. **Riaz:** sign the final A_BASELINE_BIO worksheet, so a third cohort is admitted.

After these answers, one amendment file (`specs/amendments/2026-10-29-integrated-plan/`) will record them. One statistics review by Astra follows, then implementation resumes.
