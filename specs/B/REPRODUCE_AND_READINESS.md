# B reproduction and readiness contract

**Primary decision, 6 September 2026:** B-P external prediction improvement is selected as the single primary; B-R remains historical. The selection closes the alternative-choice gate only. E1-E4/E6 and real-cohort implementation acceptance remain open. [Decision record](../../docs/decisions/B_PRIMARY_BP_20260906.md).

**Measurement evidence, 6 September 2026:** [verified source facts refining proposed platform, promoter and cellularity contracts](../../docs/research/B_MEASUREMENT_CHECKPOINT.md) refine shared gates. Annotation and measurement choices remain unselected.

**PROPOSED / NOT IMPLEMENTATION-READY — v0.1.** A specified workflow is not an implemented or validated workflow. No production results, successful external validation or complete data manifest are claimed.

## Intended reproduction sequence

1. Read the canonical GOAL/CONTEXT, this kit and `docs/research/B_paired_prostate.md` plus `docs/research/B_readiness.md`. Resolve historical-run outcome access and retain original analyses separately. Review SOURCE_MANIFEST.json as an evidence snapshot, not the final cohort download manifest.
2. Complete R1–R3 evidence/design tickets. Produce final permitted per-object checksums, assay annotation maps, independent specimen map, baseline coverage, exact eligible-population rule, U/Q lists, detection-P/QC rules and approved precision assessment. Record unresolved or excluded records with reasons.
3. Freeze the analysis/preregistration with a dated commit and reviewer receipt. The orchestrator may publish the reviewed specification milestone through authorised GitHub/Notion workflows. Labels must say conditional until gates actually pass; no `ready-for-agent` claim overrides scientific unknowns.
4. On AIU, create the approved isolated environment, resolve its genuine lock and run importer/feature/leakage/metric tests. Read-only inspection of the available inventory is not a smoke test. Record actual resource allocation, file storage and runtime; do not assume undocumented scheduler capacity or change existing jobs.
5. Run TCGA development only, save fold assignments and paired internal predictions, then select final parameters on TCGA and freeze both model bundles. Independently review data lineage and scientific implementation before external evaluation. Run directories use immutable source/config/code hashes and machine-readable completion status.
6. Evaluate CPC-GENE once under the locked contract, including paired metrics, intervals, exclusions and transport limitations. Produce predeclared sensitivities, four figures and the independent TCGA-only C export when its own gate passes. Store large data/results on AIU and only permitted summaries/manifests in GitHub/Notion.
7. Reproduce from the same full source manifest in a clean run root. Record tolerance-aware numeric comparison, exact schema/identity matches, resolved environment, completed tests and remaining limits. An interrupted stage has no successful completion marker and resumes only from a matching checkpoint.

B-F1 in TICKETS_AND_TESTS.md is a separately released endpoint-independent format implementation, published as locally checked WIP at fed56e6. AIU validation and final Opus recheck remain pending. E1–E6 remain open; the exercised format CLI is not an implemented scientific pipeline. [B-P1](tickets/BP1_prediction_engine.md) now supplies a reviewable development/lock/evaluation interface for validated feature tables, but no executable exists until its bounded implementation lands. Real biological inputs remain blocked by E1–E4/E6.

## Readiness gates and evidence needed to close them

| Gate | Current state | Required evidence before release |
|---|---|---|
| E1 program/universe | Complete external audit verifies eight unique finite rows in213 samples; both historical platform annotations verified, with24,937 common candidate IDs. Final U and eight-gene choice remain open. | Preserve that completed coverage subgate; establish literal common TCGA/CPC annotation U and platform mapping, review biological membership citations, tie/missing/duplicate rules and cross-platform scale. E1 remains open. |
| E2 promoter/QC | Pinned legacy annotation/masks and literal candidate probe sets inspected; approved policy and complete cohort Q/QC remain open. | Pinned build/annotation and masks, per-gene common CpG coverage, full data completeness/detection-P rules, fold-safe final feature procedure. |
| E3 independent specimens | Physical barcode/source table verifies technical provenance for300 assays;73 candidates have original-study inclusion/adjacent-section support, not individual aliquot linkage. | Review acceptable evidence level for the biological unit and a deterministic one-patient/processed-replicate policy;94 assays lack the new technical-provenance evidence. No unresolved focus averaging or outcome-guided selection. |
| E4 baseline/target | Portal WGS field quarantined as SNP-call agreement. Original table supplies114 code candidates; Qpure present112 overall and72/73 original-study candidates. Qpure native0–1 scale is verified; TCGA has469 called matching primary-vial candidates. These are coverage counts, not final N or cross-method equivalence. | Verify same-population cellularity definition, scale, specimen applicability and TCGA comparability; freeze missingness/target-population rules and precision. No silent purity-method substitution. |
| E5 CNA/orthogonal mechanism | Gene-level external CNA source and malignant-cell/domain reference not fully specified. | Verified independent sources and mappings for any strengthened mechanistic claim. Primary prediction may proceed without CNA only under its explicit limited claim; CNA-adjusted or tumour-cell silencing claims stay unavailable. |
| E6 inference/freeze | B-P and its external Delta_R2 estimand are selected; program/score details, minimum effect, precision target and final population remain open. | Signed full analysis/threshold/precision/validation lock, historical-access ledger and independent scientific review. |
| E7 secondary/handoff | LUAD candidate metadata manifest acquired: 455 paired primary case UUIDs; complete molecular objects/QC and C-selection thresholds remain open. | Resolve portion/sample/file multiplicity and actual molecular coverage, then freeze a TCGA-only signed selection contract. Metadata acquisition alone does not release analysis or permit external outcome selection. |
| E8 implementation | B-F1 format tooling exists as locally checked WIP; no scientific pipeline implemented. | Actual code, resolved environment, meaningful tests, independent code/spec review, successful AIU cohort run and reconstruction evidence. |

## Publication and scope decisions

**Proceed with the selected B-P primary** only after E1–E4/E6 and implementation acceptance pass, with limitations from E5 explicit. A positive Delta_R2 is not an entry condition; precision and scientifically distinct information are. A negative or null estimate still answers the predeclared question and cannot trigger an undeclared switch to B-R, but does not guarantee a standalone paper.

**Narrow** to a verified covariate-complete population only by a pre-outcome decision documenting what population is now represented and why precision is acceptable. If the chosen rank scale is not defensible, amend it before external outcome use; do not optimise it to external performance.

**Combine with C** is a recommendation to consider if B's main contribution is a reliable discovery query and the separate manuscripts would mostly repeat known associations. It needs user/scientific review and must preserve the failed/null primary record. **Defer particular claims/analyses** when their sources remain missing. These are scope decisions, not an agent cancellation of Paper B or the approved thesis's wet-lab component.

## Milestone reporting

Report each milestone as proposed, source-verified, implementation-tested or scientifically evaluated, with actual evidence links. The orchestrator controls commits/pushes and Notion updates; this kit's author made none. VPN loss queues AIU tests for later with blockers/status visible. Do not convert a documentation check into “all tests pass,” and do not call public download metadata a complete eligible-data manifest.
