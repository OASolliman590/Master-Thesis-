# Riaz/Hugo final source-integration review

6 September 2026. Read-only, bounded to the requested canonical A documents and source artifacts. No further research, downloads, code execution, cohort admission or canonical changes.

**No substantive integration blocker found.**

- DATA.md:7 correctly reports 51 Riaz baseline patients, original BOR CR3/PR7/SD16/PD23/NE2, 25 prior-ipilimumab-naive and26 prior-ipilimumab-progressed. Its49 ceiling remains explicitly conditional on source/QC/scale/independence gates; no author's exclusion list is silently adopted.
- DATA.md:11 correctly distinguishes Hugo28 profiles,27 baseline specimens and26 baseline patients, with CR4/PR10/PD12. Deterministic site selection and irRECIST/category reconciliation remain open. ENGINEERING.md:75 prevents splitting repeated specimens across development/test.
- ENGINEERING.md:73 preserves the two original Response columns by source position and selects original BOR for category mapping, retaining NE. The eight terminal punctuation reconciliations are restricted to their source, with raw IDs/collision checks; they do not authorize generic identifier cleaning or automatic specimen admission.
- The report retains the Pt3/publication-versus-source-code discrepancy, prior-treatment timing and unresolved biological cross-study independence. Absence of shared deposited assay IDs is not promoted to proof of distinct patients.
- Canonical REPORT.md, metadata_summary.json, audit_metadata.py and hash_register.json are byte-identical to the outer source-audit files. A_ROOT_SOURCE_COUNTS.json agrees with the source audit on Riaz original labels/prior-treatment counts and Hugo patient/visit counts. The canonical evidence README correctly locates the unredistributed raw inputs and says the copied scripts are not a standalone pipeline.
- README and TRANSPORT preserve both A-P1/A-P2 and the separate molecular versus regimen-specific clinical prostate branches. This audit has not opened those analysis gates.

**Minor reference refinement:** PREREGISTRATION.md A04 now describes original-author Riaz linkage and patient-deduplicated Rose counts, but its source locator still names the preliminary `candidate_label_coverage.json` and generic fields. Add the new source-admission report and `A_ROOT_SOURCE_COUNTS.json` there, so readers can directly reconstruct the updated assertion. DATA.md already links the appropriate source report; this is traceability clarity, not a numerical or admission error.
