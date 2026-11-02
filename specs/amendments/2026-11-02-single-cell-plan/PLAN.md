# Single-cell in Papers A and B: plan, 2 Nov 2026 (revision 2)

**Status: DRAFT, unsigned.** Revision 2 follows two read-only reviews and one debate round (`REVIEW_ASTRA_HIGH.md`, `REVIEW_ARGON_HIGH.md`, `DEBATE.md`), the Gate 0 inspection of the Lin atlas, and the user's choice on 2 Nov 2026: **"All cancers, no spatial."** After the debate both reviewers preferred a single source study for Paper A; the user's all-cancers choice stands, now that Gate 0 shows six cancers pass the donor floor from one already-qualified object. It replaces the scope of `specs/amendments/2026-10-30-single-cell-module/DRAFT.md`. Simple mode applies: one catalogue (`docs/cohorts/SINGLE_CELL.tsv`), a provenance table, one batch sign-off; no per-study worksheets.

## Role
Single-cell is **descriptive support** only. It shows where locked genes are expressed in sampled cells. It never tests response, never selects or changes bulk features, never alters the frozen A→B gene handoff, and never touches the locked final test. Leaving out either paper's single-cell part is an acceptable outcome.

## Cut (both reviewers agreed)
- SC-3 (single-cell responder vs non-responder testing).
- Single-cell A.1 (on-treatment transitions); bulk A.1 stays. Lin 2026 and Yost 2019 are cited as prior evidence.
- SC-2 (deconvolution), permanently; a prostate reference is not a reason to reopen it.
- Spatial data (the four Visium samples), by the user's choice.
- Separate downloads of Sade-Feldman, Yost, Bi, Fuchs and Jerby-Arnon for A/B.

## Gate 0: inspect the Lin 2026 atlas (at most 3 hours)
Zenodo 10.5281/zenodo.19586163 (CC BY 4.0), pinned by hash. Record in the catalogue, at study level:
1. original count layer present, its units (UMI or reads) and gene coverage, checked by values, not only by layer name;
2. source-study accession for every cell, and patient, specimen, timepoint, sorting (CD45+ or unsorted) and regimen fields;
3. how cell labels were made, and whether malignant or epithelial cells are present;
4. samples from ICI plus non-ICI drug regimens (excluded);
5. overlap of source studies with the bulk registry and with the locked IMvigor210 family.

**Gate 0 result (2 Nov 2026):** 1,498,487 cells, 19,479 genes, 245 patients, 455 samples, 17 source cohorts; one RNA assay holding only raw integer count layers (verified: two layers of 941,592 and 556,895 cells covering 19,448 and 18,582 genes; median library about 3,900 counts per cell, consistent with UMIs). **A gene absent from a cell's layer is missing for that cell, never zero**; patient, sample, time point (Pre/On), treatment, cohort and response fields on every cell; 16 broad cell types including copy-number-confirmed malignant cells. No bladder cohort, so no IMvigor210-family material. Combination cohorts (NSCLC_Yan, TNBC_Zhang, the chemo arm of CRC_Chen) are excluded. Response metrics differ by cohort (pathology, T-cell expansion, RECIST, PSA), which confirms the SC-3 cut. Per-cohort counts: `docs/cohorts/SINGLE_CELL_LIN2026_COHORTS.tsv`.

**Pass rules:** without original counts or source-study and patient links, Paper A gets no single-cell. Any unresolved IMvigor210-family material also blocks use. Development-cohort overlap is allowed but is reported as non-independent.

## Paper A: SC-1 across all cancers that qualify (at most 10 hours)
Qualifying at Gate 0 (at least 5 baseline ICI-only patients): breast (3 cohorts, 75 patients), head and neck (3, 44), melanoma (2, 34), colorectal (2, 24), liver (2, 11), basal cell carcinoma (1, 10). Not qualifying: lung and TNBC_Zhang (chemotherapy combinations), kidney (no baseline ICI-only sample), prostate (3 baseline patients; shown only in Paper B as a labelled exception, see below). Head and neck cohorts are checked for overlap with bulk GSE159067 before use.
- **Which samples:** baseline, ICI-only samples (anti-PD-1/PD-L1, anti-CTLA-4, or dual ICI) from every atlas source study that passes Gate 0, one specimen per patient under a frozen rule. **Each cancer, and each source study within it, is its own panel on its own scale; nothing is pooled across studies.**
- **Cell types:** broad compartments built from the atlas's labels: T/NK, B/plasma, myeloid, fibroblast/stromal, endothelial, and malignant/epithelial only where the source supports it. Lin's 77 subtypes and four TIME types are not used as targets, because they were partly defined by genes in our panels.
- **What is shown:** the 11 locked panels with individual M5/M6 genes kept, and later the top Paper A meta-analysis genes chosen by a fixed rule on the frozen bulk results, keeping discordant ones.
- **Missing tumour cells:** reported as "not assessed". Cells from another cancer or study are not patched in.
- **Output:** one figure (cancer and study panels × broad compartments) and one provenance and coverage table.

## Paper B: SC-1 in prostate (at most 8 hours, done first)
- **ICI-treated prostate panel (user decision, 2 Nov 2026: include as subtle evidence with limitations).** The atlas's PCa_Hawley cohort (4 patients, anti-PD-1, response by blood PSA) is shown as a small, separately labelled panel next to the untreated reference. It is the only ICI-treated prostate single-cell data in the plan, so it adds context the untreated reference cannot.
  - It is an exception to the 5-donor floor: values are shown **per patient** (no medians, no intervals), baseline samples only (3 patients), with on-treatment samples left out.
  - No response contrast: all 3 baseline patients are PSA non-responders, and PSA is not RECIST.
  - Limitations stated in the legend and text: 3-4 patients, treated metastatic disease, PSA response, one study, atlas cell labels. The figure may say only that a gene "is detected in" a compartment in these patients, never that it is typical of ICI-treated prostate cancer.
  - Low-copy genes follow the detection-limit rule below; with so few patients, non-detection is never interpreted.
- One pre-annotated, untreated, unsorted, donor-resolved primary prostate adenocarcinoma dataset (GEO, CELLxGENE or the Human Cell Atlas), with a usable licence.
- Broad compartments: luminal/malignant epithelial, basal epithelial, T/NK, B/plasma, myeloid, fibroblast/stromal, endothelial.
- Shows where the frozen Paper B targets and epigenetic regulators are expressed, as one supplementary figure and a lookup column in Paper B's biological-context table.
- The claim is cellular context only. It shows no silencing, no causality, and no exclusive compartment from non-detection.
- If no suitable dataset is found within the 8 hours, Paper B has no single-cell; purity adjustment and annotations carry the limitation.

## Frozen numeric rules (from the debate)
- Use verified UMI counts. Sum counts per study × patient × baseline specimen × broad compartment.
- A profile is NA (missing, never zero) with fewer than 15 cells or fewer than 5,000 UMIs.
- A compartment is shown in a study only with at least 5 eligible donors; otherwise it is marked "insufficient donors".
- Normalise as log2(CPM + 1), with **CPM computed on each profile's full gene library before panel genes are extracted**.
- Report equal-weight donor medians and the donor-level percentage of cells with counts above zero, with donor support, variation and an ambient-RNA caveat.
- A composite panel score needs at least 80% of its genes present; individual M5/M6 genes and frozen top A-DE genes are always shown separately, as dot plots without z-scoring across compartments.
- **Low-copy genes are never called absent.** A gene below 50 CPM (donor median) in every compartment is tagged `below_scRNA_detection_limit`, not `absent` or `immune_stromal_restricted`; this matters for chromatin regulators (DNMT1/3A/3B, EZH2, HDACs) and IFNG.
- The provenance table lists study, cancer, sorting, eligible donors per compartment, cells per donor (median, IQR) and a bulk-overlap flag.

## Time
At most 21 hours in total: Gate 0 ≤3 (about 1 used), Paper B ≤8 (done first), Paper A ≤10. Reviewers proposed 18-20 hours for a single-study Paper A; the extra time covers the user's all-cancers choice. If time runs short, Paper A is cut first.

## Comparators (moved out of this plan)
Lin's 59-gene signature and Subramanian 2023 belong in the Paper A bulk spec, budgeted separately. Each is admitted only with its exact published scoring rule. Lin's discovery and validation cohorts are audited for overlap with ours. IMvigor210 stays UNTOUCHED_FINAL_TEST, with any prior exposure recorded only as comparator-specific metadata.

## Rules carried over
The unit is the patient; cells are never replicates. Sorted data describe immune compartments only. Licence and processing are recorded for each source. No patient-level data goes into Git. A wrong expression scale is a hard stop; undocumented processing is a caveat.
