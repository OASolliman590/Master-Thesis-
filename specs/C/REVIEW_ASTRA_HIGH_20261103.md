# Astra (gpt-6-astra, high effort) review of the Paper C SPEC_v2 draft, 3 Nov 2026

Read-only review via Codex CLI, kept verbatim except that absolute paths were made repository-relative. One review, no loop.

The paired endpoint is defensible, but the draft is **not ready to sign**. The main blockers are query direction, an impossible down-block size requirement, and unspecified small-sample inference. This was a local, read-only review; no downloads or edits.

1. **Primary estimand and interval.**  
   Computing \(D_i=S_i(Q_M)-S_i(Q_E)\) within each biological sample correctly preserves covariance between queries. Equal-study averaging is valid for the explicitly stated **finite collection of admitted studies**. Its SE formula is correct when study estimates are independent and their SEs correctly incorporate shared controls and blocking.

   “95% interval” is insufficient. With small biological replicate counts, do not default to \(1.96\,SE\). Prefer an ordinary linear/GLS model for the single score, retaining residual degrees of freedom, followed by an approximate Welch–Satterthwaite interval:
   \[
   \nu=\frac{(\sum_s SE_s^2)^2}{\sum_s SE_s^4/\nu_s},
   \qquad \Delta_Q\pm t_{0.975,\nu}\frac{\sqrt{\sum_s SE_s^2}}{k}.
   \]
   This requires the corresponding variance assumptions. Standard limma empirical-Bayes moderation cannot meaningfully learn a variance distribution from **one score**. Neither genes nor correlated programme scores should become artificial replicates.

   Small \(k\) limits generalisation; it does not automatically invalidate this conditional interval. REML with modified Knapp–Hartung is an alternative for a **different, population-level estimand**, not a mandatory replacement for the finite-set primary.

2. **Expression-matched comparator.**  
   Useful, but insufficient to isolate the contribution of methylation support. TCGA tumour expression does **not** remove the expression floor in cultured prostate models. Missing balance includes programme membership, cellular compartment, CpG-island/promoter architecture, eligible methylation-probe count and variability, expression detectability, transcript length, array-probe specificity, and co-regulation.

   Add programme/functional-stratum balance, an expression caliper and explicit unmatched-gene handling. Prioritise external untreated cell-line expression as a sensitivity; stratify or sensitivity-match CpG-island status and methylation-probe coverage. Check gene-length/array effects rather than imposing every matching variable on a small pool. Sample-level analysis already accommodates gene correlation statistically; it does not remove biological differences between an IFN-heavy query and another programme. “Not significant” must remain **not supported**, not “unmethylated” or “unregulated.”

3. **DNMTi primary; HDACi/EZH2i secondary.**  
   **Yes.** It gives the promoter-methylation hypothesis a clearer mechanistic test. Preserve compound, dose, duration, cell state and washout differences. Azacitidine and decitabine are not interchangeable exposures. A negative DNMTi result cannot distinguish a failed hypothesis from insufficient exposure or absent methylation in the model without those annotations. Methylation-supported **desired-down** genes are especially problematic: demethylation-associated induction would oppose their declared desired direction.

4. **Pool and leakage.**  
   Frozen Tier 1+2 membership and a TCGA-only discovery gate avoid perturbation-outcome leakage. In-sample selection is acceptable for constructing a query tested in independent experiments; it is not independent validation of the methylation association.

   However, blanket panel directions are unsupported, M5 exclusion is ambiguous because its genes overlap included panels, and B’s single-cell annotation must cover **both supported and unsupported genes**. BH within a genuinely predeclared pool is defensible, but it is a separate C discovery family from B’s Tier 1+2 family.

   The size rule fails concretely: **M4 contains 13 genes, so it cannot supply 10 Q_M genes plus 10 disjoint Q_E genes.** Before other filters, its maximum matched size is six. Ten genes is also not a power calculation.

5. **Consistency with signed A/A.1/B.**  
   IMvigor210 exclusion, rejection of A-P2 coefficient directions, B-V’s contextual role and the principal causal/clinical claim ceilings are consistent.

   The CPC-replicated sensitivity contradicts C’s own “CPC results never select C genes” statement. It need not contaminate B’s already completed test, but it cannot retain a TCGA-only provenance claim or count CPC as independent validation of the selected subset.

   A.1 supplies **response-associated differential change**, not merely “rises in responders.” The draft also removes the older programme quotas, equal-programme scoring and prostate-deficit eligibility. These are substantive amendments requiring explicit reconciliation, not merely consolidation.

6. **Admission and GEO candidates.**  
   The admission principles are sound; three to five qualifying studies are **not established**. Three profiles must mean independent cultures/donors, not wells, time points or different cell lines. Old arrays require explicit probe-to-gene collapse, cross-hybridisation checks and query-specific coverage.

   A concrete existing blocker is **GSE216053**: the repository records decitabine in sample titles but DNMT1 knockout in genotype fields. The new list must preserve that conflict. The other new accession assignments lack supporting local audits; I cannot certify them. “5-aza” must be resolved to the actual chemical, and time-course/combination arms must be identified before admission.

7. **Budget and cuts.**  
   The listed tasks total **165 hours**, reasonably rounded to 170. That is an optimistic execution budget assuming ready B exports, usable processed data and reusable scoring infrastructure. It lacks explicit allowance for source reconciliation, platform preprocessing, review and failed admissions.

   Keep TISMO and extensive Perturb-CITE-seq extraction early in the cut order. Preserve a minimal cell-line baseline-expression/methylation check: it directly affects interpretation of the primary. Preserve numerical parity even if the biological C1 display is cut. Move the standalone-paper feasibility decision ahead of expensive LINCS work.

**P0 — blocks signing**

- **[specs/C/SPEC_v2.md:32](specs/C/SPEC_v2.md:32): Directions and exclusions are ambiguous.** Seven M5 genes also occur in included “up” panels. The registry explicitly records CD276’s negative Ayers weight and HOPE’s non-uniform prognostic semantics. Those weights are not restoration directions either. **Fix:** freeze a gene-level direction table with biological justification, exclusion precedence and conflict handling; separate ambiguous checkpoint/exclusion biology from the primary.

- **[specs/C/SPEC_v2.md:40](specs/C/SPEC_v2.md:40): The M4 primary block is mathematically impossible.** **Fix:** make the DNMTi primary a justified desired-up query, or explicitly redesign the down-block eligibility. Require sufficient controls and acceptable matching distances before declaring any block eligible.

- **[specs/C/SPEC_v2.md:57](specs/C/SPEC_v2.md:57): Model and interval are under-specified.** An additive treatment-plus-cell-line model imposes a common treatment effect; it does not automatically estimate the stated equal-weight average of heterogeneous contrasts. **Fix:** specify treatment-by-context contrasts, fixed aggregation weights, covariance propagation, residual degrees of freedom and interval construction; clarify that ordinary single-score inference is used.

**P1 — should fix before signing**

- **[specs/C/SPEC_v2.md:38](specs/C/SPEC_v2.md:38): Comparator fairness is overstated.** Greedy nearest matching has no caliper or failure rule and drops programme balance. **Fix:** use constrained matching with balance diagnostics; replace “removes the floor effect” with “reduces TCGA baseline-expression imbalance”; add the targeted sensitivities above.

- **[specs/C/SPEC_v2.md:33](specs/C/SPEC_v2.md:33): B’s supplied annotation is insufficiently specified for C.** B describes labels for association-positive genes; C needs labels across the entire candidate pool. **Fix:** export an outcome-independent attribution table for all eligible genes, with thresholds, donor coverage and missing-compartment handling. “Mixed” does not establish tumour-intrinsic regulation.

- **[specs/C/SPEC_v2.md:36](specs/C/SPEC_v2.md:36): The methylation gate lacks a precise test contract.** **Fix:** identify the TCGA coefficient test, adjustment set, valid-test denominator and BH family; retain B-family q-values separately. Report selection stability and distinguish significant positive associations from imprecise null results.

- **[specs/C/SPEC_v2.md:64](specs/C/SPEC_v2.md:64): CPC sensitivity conflicts with the declared input boundary.** **Fix:** remove it, or explicitly amend the boundary to permit one frozen post-evaluation B annotation, with no B retesting and no independent-CPC-validation claim for that selected query.

- **[specs/C/SPEC_v2.md:55](specs/C/SPEC_v2.md:55): Scoring changes the older contract.** The older analysis specifies programme-first, equal-programme scoring; the draft pools genes. **Fix:** explicitly choose and justify one weighting scheme, handle overlapping membership once, and pin exact centring, size normalisation, ties and missing-gene rules against the [singscore method](https://doi.org/10.1186/s12859-018-2435-4).

- **[specs/C/SPEC_v2.md:53](specs/C/SPEC_v2.md:53): Candidate status hides a known intervention conflict.** **Fix:** mark GSE216053 blocked pending reconciliation; build an accession-level table of exact chemical, genotype, exposure, independent replication, platform and originating-study overlap. Freeze time-point selection or averaging explicitly.

- **[specs/C/SPEC_v2.md:85](specs/C/SPEC_v2.md:85): Claims exceed what a null or rank change establishes.** **Fix:** use “inconclusive” when the interval includes zero, unless an equivalence margin is prespecified. Describe relative rank-score responsiveness; without a demonstrated prostate deficit, avoid calling it restoration of an established deficit.

**P2 — nice to fix**

- **[specs/C/SPEC_v2.md:23](specs/C/SPEC_v2.md:23):** Replace “rises in responders” with A.1’s response-time interaction, retaining window, regimen and uncertainty.
- **[specs/C/SPEC_v2.md:67](specs/C/SPEC_v2.md:67):** Define whether Holm covers study-specific tests or class-summary hypotheses; these are different families.
- **[specs/C/SPEC_v2.md:90](specs/C/SPEC_v2.md:90):** Add a bounded preprocessing/review contingency and conduct the feasibility audit first.

**VERDICT: DO NOT SIGN YET—retain the paired finite-study primary, but resolve directions, matching feasibility and inference before approval.**