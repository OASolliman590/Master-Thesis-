# Independent expression-platform contract review

6 September 2026. **No material findings in the reviewed report.** This is a source/annotation verification, not approval of B-P/B-R, U, preprocessing or cohort eligibility.

I queried both cached SQLite databases using `mode=ro&immutable=1`, without executing the peer's extraction script, and byte-compared each database to its original tar member. Independently recomputed:

- HTA:26,194 mappings,26,191 distinct non-NULL Entrez IDs; HuGene:25,088 mappings,25,087 distinct non-NULL IDs.
- Intersection **24,937**, HTA-only1,254, HuGene-only150; exported common-ID set matches exactly. All eight genes each map to exactly one expected `${Entrez}_at` probeset on both arrays.
- HuGene database NULL `101928749_at` conflicts with the GPL19803 description mapping to101928749. HTA additionally has NULL100996402_at and101928757_at. The report preserves this discrepancy rather than silently stripping suffixes or filling NULL mappings.

I independently parsed the original cached sample SOFT, joined its patient codes to the paired-code and GSE84042 source sets, and compared the exported metadata table and previously retained actual-expression header IDs:

- All213 codes: **147 HuGene/66 HTA**; paired210:144/66; legacy73: **17/56**.
- Batch/platform counts match every reported row. HTA is exactly equivalent to the Batch2 indicator, confirming that separate platform and Batch2 effects are not identifiable from those labels alone. This is design-matrix aliasing, not a measured biological batch effect.
- Exported GSM/platform/batch assignments and the expression-header patient-ID set match. All33 entries in `hash_register.json` match current byte counts and SHA256 values.

The report correctly limits24,937 to the two historical annotation dictionaries. It is **not final U**, proof of processed-row coverage, a TCGA crosswalk, score comparability or HLA assay specificity. Its24,598 processed-feature count is identified as previous evidence, not equated to the annotation intersection. Source-linked73 does not remove platform heterogeneity. The unknown `sva` function/design and unresolved clinical/specimen/annotation choices remain explicit.

No downloads, source changes, patient-value inspection, molecular scores, canonical edits or production tests were performed. This review did not independently repeat vendor-table and oligonucleotide sequence-specificity tabulations, which remain explicitly bounded in the peer report.
