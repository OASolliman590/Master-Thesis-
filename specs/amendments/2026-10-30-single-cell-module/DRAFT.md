# Single-cell module (A-SC / B-SC): DRAFT, revised after Astra review, 30 Oct 2026

**Superseded on 2 Nov 2026** by the signed `specs/amendments/2026-11-02-single-cell-plan/PLAN.md`. Kept for the record.

**Status: DRAFT, unsigned. Revised to the minimal version Astra recommended (`REVIEW_ASTRA_HIGH.md`):**
- **SC-1 kept:** cell-type expression *localization* in sampled compartments only. It covers one donor-resolved, unsorted prostate tumour reference, plus one for Paper A's main development cancer if inexpensive. It gives one donor-aware figure and a provenance table.
- **SC-3 conditional:** a small baseline per-patient pseudobulk check, only if verified patient counts and labels meet frozen feasibility rules.
- **SC-2 deferred:** no custom deconvolution.
- **No claims of** whole-tumour cell share, of composition "explaining" an effect, or of a methylation mechanism. Sorted (CD45+) data describe immune compartments only; malignant and stromal expression there is "not assessed", not "absent". A-P2 and B-P are unchanged, and IMvigor210's family is excluded throughout.
The sections below are the original draft, kept for the record. Requested by the user on 30 Oct ("if [single cell fits] we can align single cell to bulk RNA data; review with Astra high effort"). It adds to the signed 29 Oct amendment and changes no primary result.

## Role: support for the bulk analyses, never primary evidence
Bulk cohorts carry the patient-level ICI response evidence (A-P2, the locked panels, A-DE). Single-cell ICI cohorts are small in patients (typically 10–50), differ in tissue handling, and often sort cells (CD45+). They are used only for three things:

1. **SC-1, cell-of-origin attribution of the locked panels and A-DE genes.** For each panel and gene, estimate which cell types express it (malignant, T/NK, myeloid, B, stromal, endothelial) in public tumour scRNA. This answers questions bulk cannot: is antigen-presentation (P) or HLA-I expression mostly malignant-cell or immune-cell? It directly supports Paper B's caution that methylation association is not tumour-cell-intrinsic silencing (amendment rule 7).
2. **SC-2, a deconvolution reference for bulk.** Build cell-type reference profiles from scRNA. Estimate bulk cell composition with a declared method. Use it as a **sensitivity adjustment**: is a bulk responder effect explained by composition? It also supports B-MX's purity/composition adjustment. The reference is built only from cohorts and patients outside any protected final-test family.
3. **SC-3, a responder versus non-responder cell-state check, descriptive.** In scRNA cohorts with response labels, compare per-patient pseudobulk scores of the locked panels by response, as a direction-consistency check of the bulk findings. Never pooled with bulk patients.

## Rules
- **The unit is the patient.** Cells are never treated as independent replicates; scores are aggregated to per-patient (per cell type) pseudobulk first.
- One cohort is one study; studies are never merged at the count level.
- Endpoints follow the existing ontology. Sorted versus whole-tumour preparations are separate strata.
- Admission goes through DAV like any source: a field map, V3 (counts, processing documented), a signed worksheet. Portals (TISCH2, CELLxGENE, the Broad Single Cell Portal) are used only where a licence and documented processing allow; otherwise GEO/author files.
- No single-cell result can select or change bulk features after any outcome look, or open the final test.
- Paper B: SC-1 and SC-2 inform interpretation and composition sensitivity. They cannot by themselves establish epigenetic silencing; scRNA has no methylation, unless a joint scRNA + methylation dataset is admitted separately.

## Candidate cohorts (accessions being verified; several user-supplied claims were wrong)
Jerby-Arnon 2018 (melanoma), Sade-Feldman 2018 (melanoma, CD45+), Yost 2019 (BCC/SCC, pre/post), plus portal-listed ICI cohorts. Verification results: `docs/research/USER_LEADS_VERIFICATION_20261030.md`.

## Questions for the reviewer
1. Is "supporting only" (SC-1 to SC-3) the right role, or should any SC analysis be confirmatory?
2. SC-2: which deconvolution approach and reference-construction rules avoid circularity with the bulk responder analysis? How should a reference built from melanoma be transferred to other cancers?
3. SC-3: is per-patient pseudobulk with n ≈ 10–30 patients worth reporting? What minimum, and which test?
4. Are there conflicts with the signed amendment's rules (final-test protection, no merging, panel locking, composition circularity flagged in INTERFACES_AND_GATES.md)?
5. Is adding this module worth the effort for an MSc with about 600 researcher-hours, or should it be cut to SC-1 only?
