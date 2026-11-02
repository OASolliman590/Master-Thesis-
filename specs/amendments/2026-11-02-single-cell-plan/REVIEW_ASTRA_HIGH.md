# Astra (gpt-6-astra, high effort) review of the single-cell plan, 2 Nov 2026

Read-only review, kept verbatim.

**VERDICT: SIGN WITH CHANGES — retain a tightly bounded SC-1; cut SC-3 and the single-cell A.1 branch from the default MSc plan.**

**FINDINGS**

1. **HIGH — Overall scope / Order of work: the expansion is disproportionate.**  
   Moving from two small localisation references to 77 subtypes across ten cancers, response comparisons and longitudinal analyses substantially exceeds the earlier review’s minimal proposal. Twenty signed bulk development cohorts already provide the main scientific workload; single-cell does not resolve their endpoint, overlap or transport problems.  
   **Fix/default:** cap *all* single-cell work at 30–40 researcher-hours, including qualification and figures. Prioritise prostate SC-1, permit one inexpensive Paper A reference, and cut either component entirely if qualification becomes a separate project. Do not rebuild the atlas, pursue spatial analyses or fetch studies merely because they add another cancer.

2. **HIGH — Sources / inspection: Lin is a candidate reference, not yet an established main reference.**  
   Public availability and a permissive licence establish access, not suitability. The publication’s sample counts and longitudinal design do not establish what the deposited object actually contains.  
   **Fix/default:** before use, inspect and record:
   - Exact release, hash, documentation and source-study/accession crosswalk.
   - Patient → specimen → cell identities, repeated biopsies and duplicate source representations.
   - Cancer, site, stage, sorting, regimen and actual collection times.
   - Assays/layers, original versus corrected expression, units, gene identifiers and coverage.
   - Annotation provenance, malignant-cell evidence and documented doublet/ambient-RNA handling.
   - Response categories, definitions and missingness **only if SC-3 remains**.

   Metadata inspection alone cannot establish that a layer named `counts` contains original counts; a small structural/value check and processing documentation are necessary. Missing responses do not block SC-1. Missing trustworthy expression scale or unresolved protected-family membership does.

3. **HIGH — Sources / Rules carried over: integration and label reuse are separate risks.**  
   Scoring original counts avoids using corrected expression values, but does not undo integration-driven cell assignments. Testing panel enrichment in states defined partly by those same genes—or selected because they predict response—can reproduce Lin’s definitions rather than supply new evidence.  
   **Fix/default:** reuse broad, documented cell classes; avoid Lin’s four TIME types and 77-state response narrative as validation targets. Check how labels were constructed and whether target genes contributed. Preserve source-study boundaries, and describe reused labels as annotations, not independent biological findings.

4. **HIGH — Sources / overlap: the proposed overlap check is too narrow.**  
   Checking whether Sade-Feldman or Yost appears inside Lin prevents some duplication, but does not establish independence from the bulk cohorts. Different accessions, modalities and publications can represent the same patients.  
   **Fix/default:** make one compact crosswalk connecting atlas sources, standalone single-cell studies, bulk development families and the protected IMvigor210 family. Overlapping development patients can provide complementary localisation, not independent validation. Exclude protected-family material from every single-cell use; if it contributed to integrated labels, use independent source annotations or another reference rather than assuming removal of its cells removes its influence.

5. **MEDIUM — Paper A SC-1: the revised claim is defensible, but the measurement remains underspecified.**  
   “Expression across sampled compartments” is supportable; “cell of origin of the bulk association” is not. Expression localisation cannot distinguish cell abundance from within-cell regulation, establish whole-tumour RNA contributions or demonstrate cell function.  
   **Fix/default:** use one cancer chosen for development relevance and feasibility before examining concordance, broad compartments, donor-level normalized profiles, equal donor contributions, donor support and variability. Freeze score normalization and missing-gene rules; preserve individual M5/M6 genes rather than treating everything as eleven interchangeable composites. Select later A-DE genes by a deterministic rule applied to frozen bulk results, retaining discordant findings. If malignant cells are missing, report “not assessed”; do not patch melanoma malignant cells into a cross-cancer quantitative heatmap.

6. **HIGH — Paper A SC-3: a feasibility table frozen before scoring is not sufficient protection.**  
   It cannot undo knowledge of published response associations, outcome-informed subtype definitions, or selecting the most promising cancer–panel–cell-type combinations after SC-1. Seeing group counts for feasibility is legitimate; calling the resulting exercise outcome-blind is not.  
   **Fix/default:** cut SC-3 from the committed plan. If exceptionally retained, choose one study, one endpoint and a very small contrast set using documented prior rationale; freeze specimen selection, cell/library QC, scoring, missingness and reporting rules before inspecting score–outcome relationships. Record prior exposure and report every planned contrast, including null and opposite directions.

7. **MEDIUM — Paper A SC-3: patient counts alone do not make the contrast interpretable.**  
   Ten patients per group is an exploratory operating threshold, not a power guarantee; response may still be inseparable from study, batch, site or regimen. A pooled atlas-wide Welch test would violate the per-study design.  
   **Fix/default:** if retained, sum original counts within patient × specimen × broad cell type, normalize, then score; compare within one eligible source study. Use two-sided effects and intervals, assess confounding and response-dependent missingness, and apply the earlier review’s BH correction across the actual tested family if reporting p-values. No SC-3 meta-analysis is needed. Patient-aware pseudobulk has methodological support, but does not solve these design problems ([muscat primary study](https://doi.org/10.1038/s41467-020-19894-4)).

8. **HIGH — Paper A.1: the proposed branch is derivative and overstates what pairing identifies.**  
   Reusing Lin’s patients and states to show that treatment-associated transitions matter largely reproduces the finding motivating the analysis. Paired biopsies do not track individual cells: apparent transitions can reflect recruitment, depletion, biopsy location or sampling.  
   **Fix/default:** cut this single-cell branch while preserving the separately specified bulk A.1. Cite Lin as prior evidence. If later revived, test a few frozen panel changes within broad compartments and actual patient pairs, with fixed timing rules; call it secondary reanalysis, not independent confirmation. Fuchs’s ICI-only window would still be an uncontrolled temporal comparison, not proof of an ICI-caused transition.

9. **MEDIUM — Paper B SC-1: useful interpretation, but “tests the interpretation” is too strong.**  
   A prostate reference can show that target genes and regulator transcripts occur in different compartments, illustrating a plausible composition alternative. It cannot determine what produced a TCGA methylation association, measure regulator activity, establish regulator–target causality or prove silencing.  
   **Fix/default:** retain one small supplementary localisation figure only if a readily usable, donor-resolved reference matches untreated primary prostate tumours reasonably well. Include broad immune, stromal and source-supported malignant/epithelial classes, with frozen B targets and regulators. Do not substitute metastatic treated prostate without explicitly narrowing the claim. If no suitable reference is readily available, **cut Paper B single-cell entirely** and state the limitation; B-P and B-MX remain scientifically intact.

10. **HIGH — Comparator: correct direction, incomplete implementation and exposure handling.**  
    A 59-gene list alone is not the published predictor. Checking only its 19 validation cohorts misses derivation, tuning, model selection and reference-data exposure.  
    **Fix/default:** admit the exact published scoring implementation, coefficients or rules, normalization, direction and coverage policy; otherwise leave it unavailable, with no substitute average. Audit all development and evaluation families. Keep CYT as the formal primary comparator and evaluate supporting methods on a frozen common eligible population, as required by the [comparator contract](specs/A/COMPARATOR_REGISTRY.md).

    `PREVIOUSLY_INSPECTED` should describe **Lin’s comparator–cohort exposure**, not change IMvigor210’s protected status for this project. Previous publication of a genuinely frozen validation result does not automatically prove training leakage; verify its actual role. Equally, known published performance is not a fresh blinded benchmark. Do not load IMvigor210 now or use its reported performance to select or tune this project’s models.

11. **MEDIUM — Rules carried over / signed amendments: inheritance needs explicit reconciliation.**  
    The earlier draft’s per-cohort DAV worksheets conflict with the later simple-mode amendment. Conversely, saying the earlier review “still applies” leaves essential scoring, multiplicity, contamination and overlap rules easy to overlook while expanding the scope it recommended.  
    **Fix/default:** use the existing study catalogue plus a compact provenance/coverage table and batch sign-off; do not resurrect worksheet machinery. Keep wrong expression scales as hard stops and ordinary undocumented processing as stated caveats. Explicitly preserve per-study analysis, separate response definitions, exclusion of non-ICI combination response cohorts, frozen A→B gene handoff, isolated A-P2/B-P primaries and no feedback from single-cell results into feature selection. A qualified prostate reference alone is **not** a reason to reopen SC-2.

**MINIMAL PLAN**

- **Paper A:** optional descriptive SC-1 using one qualified source study, possibly extracted from Lin. One broad-compartment, donor-aware figure for the locked programmes; frozen A-DE genes may be added downstream. No SC-3, single-cell A.1, custom integration or malignant-compartment patchwork. Omit single-cell altogether if the source fails quick qualification.
- **Paper B:** one optional supplementary figure localising frozen targets and regulators in a suitable untreated prostate reference. Describe cellular context only. No deconvolution, methylation mechanism claim or new regulator–target analysis.
- **Shared limit:** 30–40 hours total. Keep the Lin comparator audit separate: it remains relevant even if all single-cell analysis is cut.

**POINTS YOU ARE UNSURE ABOUT**

- The Lin object has not been inspected; counts, source identities, usable baseline labels, genuine pairs, malignant cells and protected-family overlap remain unknown.
- The novelty addendum explicitly relies on Lin’s abstract. Its full annotation methods, signature implementation and exact derivation/validation exposures are unverified.
- Fuchs’s accessible molecular data, timing details and usable patient linkage are unverified here; the files do not justify treating it as a ready supporting dataset.
- No qualified prostate reference is identified. Its availability within the proposed time cap is therefore uncertain.
- The bulk registry’s signed counts are not proof of 1,257 unique, endpoint-compatible, fully analyzable patients. Existing overlap and linkage caveats still matter.
- This review used local documents and the supplied facts only; no network access or file changes were made.
