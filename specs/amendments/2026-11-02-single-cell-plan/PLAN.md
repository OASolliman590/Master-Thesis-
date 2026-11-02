# Single-cell in Papers A and B: plan, 2 Nov 2026

**Status: DRAFT, unsigned.** It replaces the scope of `specs/amendments/2026-10-30-single-cell-module/DRAFT.md`, whose rules and Astra review (`REVIEW_ASTRA_HIGH.md`) still apply. Requested by the user on 2 Nov 2026 ("come up with a plan how single cell will have its place in paper A and B"). The new fact since the draft is that the Lin 2026 *Cancer Cell* atlas is public (Zenodo 10.5281/zenodo.19586163, CC BY 4.0).

## Role (unchanged)
Single-cell **supports** the bulk results and is never primary evidence. Bulk cohorts carry the patient-level response evidence. No single-cell result may select or change bulk features after an outcome look, or touch the locked final test.

## Sources
| Source | Cancer | Treatment | What it gives | Use |
| --- | --- | --- | --- | --- |
| **Lin 2026 atlas** (Zenodo, integrated Seurat object) | 10 cancers, 241 patients, 441 samples | ICI, before and during therapy | 77 immune and stromal subtypes, 4 TIME types, transitions | **Main reference** for A (SC-1, SC-3, A.1) |
| Jerby-Arnon 2018 (GSE115978) | melanoma | ICI-naive vs post-ICI | all cell types, **including malignant cells** (Smart-seq2) | SC-1 malignant compartment, if the atlas lacks malignant cells |
| Sade-Feldman 2018 (GSE120575) | melanoma | anti-PD-1, anti-CTLA-4, both | CD45+ only, response labels | SC-3, only if not already inside the atlas |
| Yost 2019 (GSE123813) | basal / squamous cell skin cancer | anti-PD-1, pre and post | T-cell clonal replacement | A.1 support, only if not inside the atlas |
| Bi 2021 (Broad SCP1288) | kidney | ICI | kidney tumour and immune states | Kidney SC-1/SC-3, only if not inside the atlas and the licence allows |
| GSE207422; Zhang 2021 (GSE169246) | lung; breast | ICI + chemotherapy | — | **Combination paper only**; catalogued, not used in A/B |
| Prostate reference (to find) | prostate | untreated, unsorted, donor-resolved | malignant, immune and stromal cells | **Paper B** SC-1 |

The atlas was assembled from public studies, so the first step is to find which of the rows above it already contains. A dataset is fetched separately only if it adds something the atlas lacks: malignant cells, a cancer, or patients.

## Paper A
1. **SC-1, where the panels are expressed** (can start once the atlas is inspected). For the 11 locked panels, and later for Paper A's top meta-analysis genes, show donor-aware expression across the atlas's cell subtypes, by cancer. Malignant cells come from Jerby-Arnon (melanoma) where the atlas has none. Output: one figure and a provenance table. Claims cover the sampled compartments only, never a whole-tumour share.
2. **SC-3, responder check** (conditional). Per patient and cell type, sum raw counts at baseline (one pre-treatment sample per patient), score the locked panels, and compare responders with non-responders (Welch, mean difference and 95% interval). Thresholds from the Astra review: fewer than 5 per group gives description only; 5-9 is exploratory and fragile; 10 or more is a reasonable exploratory comparison. A feasibility table (patients per cancer, cell type and response) is produced and frozen **before** any score is computed.
3. **A.1, on-treatment change** (after the A.1 spec). The atlas's pre/on pairs show whether bulk on-treatment panel changes match cell-state transitions. Yost, and Fuchs 2026 if accessible, are supporting sets.
4. **Comparator.** Lin's 59-gene signature joins the comparator registry. Its 19 validation cohorts are checked for overlap with ours; where IMvigor210 is among them, its result there is marked PREVIOUSLY_INSPECTED.

## Paper B
1. **SC-1 in prostate.** Using an untreated, unsorted, donor-resolved prostate tumour reference, show which cell types express the B gene panels and the epigenetic regulators. This tests the interpretation that a methylation association need not mean silencing inside tumour cells (amendment rule 7). It never shows silencing itself, because scRNA carries no methylation.
2. **Composition sensitivity (SC-2) stays deferred.** It is reconsidered only if a qualified prostate reference exists, following the Astra rules (frozen reference, markers excluding panel genes, identical patients).
3. **Context.** Fuchs 2026 (methylation subtypes and ICI outcome in oesophageal cancer) is cited as the nearest neighbour.

## Order of work
1. Inspect the atlas (study-level metadata only) and record it in `docs/cohorts/SINGLE_CELL.tsv`: source studies, cancers, timepoints, patients with response labels, cell-type labels, raw counts present.
2. Settle overlaps with the table above; fetch only what adds something.
3. Search for a prostate reference (metadata only: GEO, CELLxGENE, the Human Cell Atlas).
4. Paper A SC-1 on the 11 locked panels.
5. The SC-3 feasibility table; the user decides whether SC-3 runs.
6. A.1 and Paper B SC-1 when their specs are ready.

## Rules carried over
- The unit is the patient; cells are never replicates.
- Studies are not merged at the count level; the atlas's own integration is used for cell labels only, and scores come from raw counts within each source study.
- Sorted (CD45+) data describe immune compartments only; other compartments are "not assessed".
- Absent or under-sampled cell types give missing scores, not zero.
- Licence and processing are recorded for each source; no patient-level data goes into Git.
