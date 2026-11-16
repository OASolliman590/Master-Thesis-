# A3 decision sheet — clinical adjustment, ranking and gene handoff

Status: DRAFT / UNSIGNED / NOT APPROVED. Requested by the user on 10 November 2026. Approval to write this sheet is not approval of its recommendations. No real outcomes, clinical tables or real A-P2 inputs were opened to prepare it; no new analysis code was written.

| Choice | Suggested choice | Ready to sign? |
| --- | --- | --- |
| C — Clinical adjustment | Keep the signed unadjusted reference and recorded technical-batch handling. Freeze a separate minimal baseline clinical set for each cohort from an outcome-free availability table. | Not yet: exact source fields, coding and missingness by cohort must be verified first. |
| R — Post-meta pathway ranking | Rank eligible genes by pooled Hedges g divided by its reported standard error; retain the signed effect direction. | Proposed below; requires the user's explicit choice. |
| H — A-to-B/C handoff (N14) | Export the complete development-only gene-effect table, plus a separately flagged candidate subset under a fixed rule. | Proposed below; requires the user's explicit choice. |

## C. Clinical adjustment: no guessed universal set

The signed numerical freeze already leaves clinical adjustment deferred; this sheet does not reopen that decision or invent available columns. The unadjusted reference and recorded within-study batch design remain as specified. “Unadjusted” here means no additional clinical covariates; it does not remove a required technical batch term.

Before requesting a clinical-set signature, prepare one patient-free row per cohort with: source document/hash; explicitly named baseline fields; units and category definitions; timing relative to treatment; overall availability and joint completeness; proposed formula; categorical reference levels; missingness rule; and limitations. Do not stratify that audit by outcome, read whole clinical tables, or use ingestion packets. Under the current lock, even outcome-dependent estimability checks wait for a separate release.

Suggested candidate fields to assess, not a fixed set: age in years, source-recorded sex where it varies, pretreatment performance status, and documented prior ICI exposure. Disease burden or risk group requires its own source-specific definition. A field being available alone does not establish that it belongs in the adjustment set. No post-treatment variable, RNA-derived composition fraction, or outcome-selected covariate is allowed.

Suggested missingness rule for the future sheet: complete cases for the prespecified set, no automatic imputation, and an unadjusted comparison on those same patients to distinguish a changed population from adjustment. Unknown treatment history is not “untreated”. Rank deficiency or inseparable batch/response makes an effect unavailable; do not drop terms after inspecting results to obtain an estimate. The final covariate sets remain unsigned and unimplemented.

## R. Exact proposed post-meta ranking

Proposed ID: `A3_META_RANK_ESTIMATE_OVER_SE_V1`.

- Statistic: `rank = estimate / se`, using the pooled Hedges-g estimate and the SE emitted by the frozen REML/modified Knapp–Hartung synthesis. Do not substitute a new SE or call this an independent standard-normal test. Existing inference and confidence intervals stay unchanged.
- Positive means higher expression in responders; negative means higher expression in non-responders. Use the whole eligible gene ranking, not a significance-filtered gene list.
- Make a separate ranking for each endpoint definition, synthesis stratum, representation/effect family and analysis method. Never mix ORR, different benefit definitions, panels, genes, or native DE effects with Hedges g.
- Include only eligible gene rows with verified independent study membership, `pooled` status and at least four studies. The four-study threshold is a proposed restriction for this descriptive pathway stage, not a change to the signed small-k reporting rules. Retain smaller-k results in the main effect tables.
- Require finite estimate and finite positive SE. Drop unavailable statistics with reasons. Use the frozen identifier/alias mapping; unresolved, ambiguous or duplicate gene identities cannot enter the ranking. Apply the approved A1 policy without silently reducing a required panel.
- Sort the statistic decreasingly; break exact ties by canonical gene symbol. Do not jitter values or select the most significant duplicate. Retain mapping and excluded-row counts and hashes.
- Preserve the frozen Hallmark/Reactome releases, fgsea settings, seeds, size limits and descriptive interpretation. This does not change the separate formal Hallmark score analysis.

Alternative for the user: rank by pooled Hedges g alone. That emphasizes magnitude; the suggested ratio also reflects uncertainty and may favor more precisely estimated effects. Neither option is declared universally optimal.

The existing invented-data implementation supports both `estimate` and `estimate_over_se`; production authorization and the full eligibility contract remain required. The [fgsea documentation](https://bioconductor.org/packages/release/bioc/vignettes/fgsea/inst/doc/fgsea-tutorial.html) establishes the preranked-statistic interface; it does not prescribe this project's meta-ranking formula. The [metafor documentation](https://wviechtb.github.io/metafor/reference/rma.uni.html) describes the synthesis outputs and inference options. The choice above is an explicit project proposal, not a method mandated by either source.

## H. Exact proposed handoff, with complete results retained

Proposed ID: `A3_DEVELOPMENT_HANDOFF_V1`.

1. Export every tested development-cohort gene row and its endpoint definition, stratum, effect type, representation/method, estimate, SE, interval, raw p, within-family adjusted p, independent-study count, heterogeneity, availability/exclusion reason, mapping provenance and source/code hashes. Include negative, null, tentative and non-estimable rows with their status. No patient-level records are exported to Git.
2. Keep two products separate: the unchanged frozen A-P2 equation with its complete membership/scaling contract, and A-BIO association tables. A-BIO-selected genes never become A-P2 features.
3. Proposed candidate flag: only pooled ORR Hedges-g rows from the prespecified per-cancer syntheses, with at least four verified independent studies and the signed within-family BH adjusted p at or below 0.10. Require valid finite estimates/uncertainty and resolved gene identity. Other endpoint definitions and across-cancer results remain in the full export but do not silently join this candidate family. No top-N cap, no direction filter, no selection using Paper B or CPC-GENE results. An empty candidate set remains empty.
4. Preserve the per-study signs and cross-cancer disagreements. Do not collapse one gene's context-specific effects into a universal direction. “Higher in responders” is an association, not an instruction to activate the gene or proof of benefit. C must separately freeze any perturbation/query interpretation.
5. Hash the full export, candidate rule and candidate set before downstream use. Paper B's primary Tier 1–2 universe remains independently frozen; this handoff is a separately labelled A-derived set and never changes that primary universe. Paper C's final query and SC-1's display-size rule remain separate gates, not implicit approvals here.
6. Protected final-test data, external validation outcomes, future B results and C rankings cannot select, remove or reorder candidates. A later revision receives a new version and cannot overwrite the frozen original.

The four-study/candidate filter is a proposed downstream selection rule; it does not delete low-k or non-significant A results and is not yet adopted. If a different rule is wanted, specify it before any relevant results are inspected.

## Decision record left for the author

- C: await the outcome-free per-cohort field/coding/missingness sheet; no clinical set signed.
- R: pending choice of ratio versus effect-only ranking and acceptance of the eligibility rules.
- H: pending acceptance or amendment of the full-export and candidate-selection rules.

No signature is filled in. Accepting a scientific rule later still will not release real outcomes or the real rebuild. Cohort admission, prior-exposure/overlap verification, applicable N12/N13/N15 gates and separate execution releases remain necessary; A3 is not the sole remaining gate.

Controlling local records: [Paper A specification](../../specs/A/SPEC_v2.md), [numerical freeze](../../specs/amendments/2026-11-04-numerical-freeze/AMENDMENT.md), [analysis modules](../../specs/amendments/2026-11-03-analysis-modules/SPEC.md), [Paper B specification](../../specs/B/SPEC_v2.md), and [approved policies](AB_POLICIES_AND_A_P2_INTEGRATION_20261110.md). The earlier A-BIO post-meta ranking proposal remains pending; this sheet does not overwrite it.
