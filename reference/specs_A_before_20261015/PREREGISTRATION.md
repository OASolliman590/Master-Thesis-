# A preregistration and evidence ledger

**Amendment:** [approved A/B reconciliation](../../docs/decisions/AB_IMMUNE_BARRIERS_20260911.md). This records user approval of direction only, not supervisor/institutional approval or an external registry submission.

Draft only. No external registration exists for this revision. Metadata, prior pipeline outputs and earlier candidate endpoints have been inspected; list those exposures in the registration. A future Git tag is a version marker, not proof of prospective external preregistration.

## Proposed freeze

Freeze the approved primary hypothesis/estimand in ANALYSIS.md, cohort and signature registries, response mappings, specimen rules, source versions, precision rationale, resampling, multiplicity, exclusions and all development/validation boundaries. Preserve signed and null outcomes. Compare the proposed change with the submitted cross-cancer discovery protocol and record supervisor/institutional decisions separately; their approval cannot be inferred here.

Record the resolved primary choice: A-P2 independent-test incremental discrimination of the learned signature; A-P1 fixed-CYT endpoint sensitivity is secondary. Both modules remain specified under this hierarchy. Freeze branch-specific cohort/weight registries, canonical O/SD/PD resampling and percentile quantiles, all secondary test IDs/family sizes, independent-test exposure, discovery handoff version, and prostate transport contracts. A failed frozen required source yields an incomplete primary, not a changed denominator.

## Grilling ledger

| ID | Question and current answer | Kind / decision status | Evidence and exact locator | Uncertainty and spec consequence |
|---|---|---|---|---|
| A01 | Is endpoint harmonization itself novel? No: Kang explicitly defines combined response/PFS mappings | Verified source fact, resolved | DOI10.3390/cancers15164094, response-data collection methods; full source report ../../docs/research/A_clinical_transfer.md | Source code boundary rules not reproduced; do not claim first harmonization |
| A02 | Are prostate ICI transcriptomes absent? No: published Guan and public COMBAT evidence exist | Verified publication/metadata, resolved as an absence correction | Guan DOI10.1038/s41586-022-04522-6; COMBAT DOI10.1038/s41467-023-44514-2, Data availability and treatment schedule | Complete Guan matrix/labels unresolved; COMBAT regimen not isolated ICI |
| A03 | Does COMBAT provide primary ORR/DCR categories? Not from inspected binary fields | Verified metadata limitation | GSE229555 `psa50 response`, `radiographic response`, `time point`; summary with source URL | Do not infer SD or ICI-specific benefit |
| A04 | Can clinical comparisons use the same patients? GSE91061 has51 baseline patient codes linked to original BOR/prior-ipi metadata,49 category-labelled; GSE176307 has89 labelled records but88 labelled patient codes after resolving repeat sequencing | Verified metadata, final eligibility open | Historical candidate_label_coverage.json plus ../../docs/research/A_source_admission_91061/REPORT.md and ../../docs/research/A_source_admission_176307/REPORT.md; original BOR, patient keys and hashes | Timing/overlap/scale checks remain; counts are ceilings |
| A05 | Should fixed CYT Delta be the primary rather than original discovery? No: A-P2 discovery selected; fixed-CYT analysis is secondary | User decision, 11 September 2026 | ANALYSIS.md; Rooney DOI10.1016/j.cell.2014.12.033 supports gene basis, not our study's novelty | Keep discovery branch and full secondary scope explicit; no silent replacement |
| A06 | Is DCR equivalent to durable benefit? No without duration/follow-up | Source definition distinction, resolved | Luo DOI10.1016/j.annonc.2022.04.450, SD-responder definition; original criteria | Censoring and six-month boundaries cannot be imputed |
| A07 | Does correlation with PRAD immune scores validate ICI response? No | Inferential boundary, resolved | Untreated cohort design plus endpoint definition; submitted thesis mapping | Molecular characterization only; overlap of gene sets reported |
| A08 | Are49+88 candidate labelled patients adequate for the proposed precision? Unknown | Unresolved factual/design dependency | Current category counts; no expression pilot or precision calculation | Admission and precision analysis required before readiness |
| A09 | Does fixed-score leave-cohort-out analysis need nested CV? No model is fitted | Design-method distinction, resolved for proposed fixed primary | Explicit estimator in ANALYSIS.md | Nested CV reserved for a separately approved trained-model branch |
| A10 | Can we publish this as a standalone paper? Not yet established | Scientific judgement, unresolved | Closest-study comparison and unrun evidence plan | Retain A; review proceed/combine after substantive novelty/precision assessment |
| A11 | Is the full discovery module now specified? Yes as a conditional proposed regularised cohort-held-out design; eligible split structure is not verified | Design drafted, admission open | DISCOVERY.md; DATA.md branch manifests | At least three development cohorts and reserved independent test sources required by proposed design, not an asserted existing resource |
| A12 | Is prostate transport an exact analysis rather than an unspecified score plot? Proposed median/IQR contrasts, pathology correlation and regimen-specific AUROCs are defined | Design drafted, source gates open | TRANSPORT.md | LUAD/PCaDB manifests, pathology linkage, compatible scales and clinical timing remain unverified |

The original source audit was checked on5 September2026; the6 September2026 source checkpoint adds separately dated evidence and the current COMPASS publication. Source publication dates and retrieval fields are retained in each report. Claims requiring matrix inspection remain open even when metadata is available. Proposed numerical settings are choices, not facts supplied by a paper.

## Readiness checklist

- [x] Scope, historical crosswalk and clinical-versus-molecular claim boundary documented.
- [x] Closest-study and source-field audits available with provisional counts.
- [x] Two competing exact primary proposals and a four-figure evidence contract drafted; exactly one must be chosen.
- [ ] User resolves the material primary/discovery tradeoff; independent scientific review completed.
- [ ] Cohort eligibility, patient/specimen and trial overlap fully verified.
- [ ] Actual matrix scale, gene mappings and score coverage verified; secondary panel locked.
- [ ] Discovery development/inner/outer/final-test source structure and exposure checked; training-only pipeline and B/C handoff frozen.
- [ ] Prostate reference/original-cohort manifests, orthogonal composition fields and regimen-specific clinical endpoints verified or explicitly unavailable.
- [ ] Precision target and analysis justified from admitted data, without outcome-driven success gates.
- [ ] Linux environment lock recreated and documented APIs/smoke tests verified.
- [ ] Tickets and public test seam reviewed; original protocol deviations reconciled.
- [ ] Registration/exposure statement externally recorded where chosen; no false prospective claim.
- [ ] GitHub parent/tickets published after review, with ready labels only for actually unblocked items.

Current disposition: proposed/conditional, **not implementation-ready**. Unchecked items are genuine missing evidence, not tasks claimed complete by this file's existence.

## Source checkpoint, 6 September 2026

COMBAT actual workbook/header and target-gene presence checks pass; standard pmeTPM scale is contradicted. Original response timing is BAT-only at C4D1; the later12-subject RNA analysis is not the public15-subject set without a crosswalk. Candidate clinical-ID/PSA agreement is not final-regimen endpoint validation. See ../../docs/research/A_COMBAT_ADMISSION.md and its independent review. No primary or alternate BAT-only endpoint is approved. Published aggregate outcomes and a small initial expression preview were inspected; no immune scores or clinical associations were computed.

The July2026 COMPASS final publication is added to the closest-study comparison; detailed comparator training/split overlap remains to be audited. Both A-P1 and A-P2 remain proposals.
