# Paper B measurement checkpoint

6 September 2026. **Source evidence and proposed measurement contracts; B-P external prediction improvement is now selected as Paper B's single primary.** The later user decision fixes the external paired Delta_R2 estimand but does not turn this source checkpoint into a final gene/probe universe, eligible population or biological validation. B-R is retained as a historical alternative, not co-primary. B-F1 code and its outstanding AIU/final-Opus gates are unchanged.

| Shared question | Verified evidence | Remaining decision or measurement gate |
|---|---|---|
| What measures expression in CPC? | HuGene2.0ST (147 patients) and HTA2.0 (66), processed with author-reported RMA/custom BrainArray v18 and sva. Stronger73-code subset contains17/56 respectively. | Original sva function/design and score transport are unresolved. Platform and published batch labels are confounded. |
| Can the processed genes be mapped? | Both original v18 annotation databases are inspected;24,937 common nonmissing Entrez IDs, all eight targets unique in each. | This is not final U: intersect actual processed feature IDs and a pinned TCGA crosswalk; adjudicate missing/conflicting/retired mappings explicitly. |
| What defines a promoter measurement? | Literal cognate-transcript windows and masks are reproducible;3,127 distances match independent v36 coordinates. | Source label, positive CDS span, canonical transcript, manufacturer category, window and shared-probe rules are different choices. No annotation policy is frozen. |
| Are eight gene measurements independent loci? | Source-labelled candidate:403 gene memberships/288 unique probes. CDS-bearing alternative:318/203. Shared TAP1–PSMB9 and PSMB8–PSMB9 memberships are substantial. | Preserve shared-probe groups. One probe contributes once per gene; gene-family multiplicity correction does not establish locus independence. |
| Is CPC cellularity a real0–1 field? | Original Qpure Cellularity has214 numeric/70 NA across284 source rows, range0.12–1.00; these are source-wide QC counts. | Do not divide by100. Existing112/114 and72/73 candidate presence counts remain before specimen/QC eligibility. |
| Is TCGA cellularity available? | Actual public ABSOLUTE table gives469 called matching primary sample-vials from469 candidate cases;16 matching rows have blank calls and values. | Match portions/aliquots to selected molecular files and freeze valid-call/missingness policies. These are not final training patients. |
| Are Qpure and ABSOLUTE interchangeable? | Original methods describe different estimation/calibration approaches. ABSOLUTE purity and Cancer DNA fraction are distinct columns. | B-P requires justified covariate transport; B-R could propose cohort-specific measured-covariate adjustment, with residual-confounding limits, through an explicit amendment. No substitution is approved. |

## Evidence and source pointers

- [Expression report](B_measurement/B_expression_platform_contract/REPORT.md) and [independent review](B_measurement/B_expression_platform_contract/EXPRESSION_REVIEW.md): original GEO records, historical BrainArray v18 packages, exact source/hash receipts and metadata-only checks.
- [Promoter report](B_measurement/B_promoter_semantics/REPORT.md) and [independent review](B_measurement/B_promoter_semantics/PROMOTER_REVIEW.md): pinned v36/202209 tables and five small UCSC slices; explicit unselected candidate policies. Of64 source-labelled transcripts,33 lack positive CDS spans. This qualifies the label; it does not prove a source error.
- [Cellularity methods](B_measurement/B_cellularity_methods/REPORT.md): original Qpure and ABSOLUTE papers plus Fraser supplementary field/scale QC.
- [TCGA table audit](B_measurement/B_TCGA_cellularity/REPORT.md) and [independent recount](B_measurement/B_TCGA_cellularity/REVIEW.md): source-field and hierarchical candidate linkage only.

## Contract changes and next implementation boundary

Preserve source platform and batch as separate metadata fields; do not put perfectly collinear indicators into an adjustment model and claim their effects separately. Retain source gene IDs, annotation release and missing/conflict states. A database-mapped gene is not proof of probe specificity, particularly in HLA genes.

Promoter maps must carry versioned cognate transcript, literal source label/distance, coordinate convention, mask and all shared-gene memberships. Do not apply one transcript's distance to every gene in a row, equate source-label protein_coding with a coding isoform, or silently turn source ±1500 windows into manufacturer TSS categories. The existing candidate counts remain correct under their literal predicates; their interpretation is corrected.

Future covariate schemas must preserve estimator, field name, native scale, call status and source specimen hierarchy. A numeric0–1 value is insufficient evidence of tumour purity. The earlier portal WGS-agreement field remains prohibited. Blank calls are unknown/missing, not zero or an inferred failure class.

These checks did not themselves select the primary; the subsequent user decision selected B-P. They still do not authorize analytical release, replace source-specific QC or the required wet lab, or establish new causal biology. Next: finish actual feature-ID and aliquot linkage, settle specimen/measurement policies, and freeze the resulting validation and precision contract before any real-cohort feature/model run. The bounded B-P1 engine can be implemented against synthetic validated-table fixtures independently of those biological gates.

## Reproduction and storage

The subfolders retain reports, hash receipts, aggregate summaries, source-audit helpers and proposed methylation probe-ID policies. Raw patient tables/matrices, annotation databases, large manifests/masks and downloaded source bodies remain in the original outer audit cache. Expression mapping exports and patient-platform rows are not copied to Git. Candidate methylation probe IDs are derived policy outputs, not patient data or frozen Q.

Copied audit helpers are historical snapshots and are not self-contained production commands. [The package wrapper](B_measurement/README.md) distinguishes audit-time statements from current canonical location, gives exact restore layouts/commands and records the one safety-modified retrieval helper alongside its byte-identical original snapshot. The promoter crosscheck depends on the full long annotation generated by its first helper and five cached UCSC responses. Restore declared source inputs by hash before reproduction. `B_measurement/ARTIFACTS.json` inventories every retained file except itself and separately identifies omitted dependencies. Metadata/count verification is distinct from running a statistical method or validating B-F1 on AIU.
