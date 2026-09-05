# B source-integration review

6 September 2026. Read-only review of the current canonical B spec, source correction, copied specimen report and summary JSONs. No additional downloads, scientific analyses, endpoint choices or canonical edits. Excludes the E3/E4 readiness-table, replicate-ledger and ANALYSIS.md old-137 wording already identified as in flight by the root.

## One actionable stale active claim

**P2 — README.md:27 still says external clinical linkage “currently reaches only 73/210 candidate patient codes.”** This unqualified current-coverage statement contradicts DATA_AND_SOURCES.md:3 and the original-table audit: there are now 114 clinical-code candidates, comprising 73 original-study protocol-supported bridges plus 41 code-only bridges, with another 96 not in that table. Update this entry-point paragraph to preserve those evidence levels and state Qpure availability as 72/73 or 112/114 field-presence counts only. Do not convert either number into eligible N or imply same-aliquot verification. The old portal route can still be reported separately as 73 code candidates.

## Integration checks passed

- B_PURITY_FIELD_CORRECTION.md correctly quarantines the portal WGS_BASED_PURITY_ESTIMATION field and distinguishes source-defined WGS/OncoScan SNP concordance from Qpure, ASCAT, pathology and methylation-derived LUMP. The 130/130 comparison is supported by the independently checked source audit. The cause of the portal misannotation is not asserted as confirmed.
- The canonical B_SPECIMEN_RESOLUTION.md is byte-identical to the authored report. Its 300 technical-assay matches, 119 complete-provenance candidate patients, 73 original-study bridges and 114 clinical-code candidates retain the required distinctions. It explicitly leaves individual aliquot/focus mapping unresolved and does not approve an endpoint or final N.
- SOURCE_GATE_REVIEW/B_linkage_summary.json, B_legacy_clinical_summary.json and B_purity_label_audit.json are byte-identical to their source-audit artifacts.
- Active ANALYSIS/PREREGISTRATION headers prohibit treating the portal attribute as purity. The primary-alternative header describes Qpure 72/73 as presence, not eligibility. Both candidate primaries remain proposed, and no gate is silently opened by this metadata audit.

**Optional clarity refinement:** SOURCE_MANIFEST.json `coverage.CPC_clinical_candidate_codes=73` and `CPC_clinical_uncovered_via_inspected_route=137` retain the legacy portal route alongside new `original_table_clinical_code_candidates=114`. Add an explicit legacy-route label or rename those older keys before a consumer treats them as overall current coverage. The new original-table keys and `CPC_final_primary_n=null` already prevent this from being an unsupported final-N claim.

No additional substantive source-definition or specimen-certainty error found within the bounded reviewed scope.
