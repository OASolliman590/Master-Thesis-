# Astra (gpt-6-astra, high) review of B-ICIM with the widened gene scope, 2 Nov 2026

Read-only review, kept verbatim except that absolute paths were made repository-relative.

**VERDICT: add minimal version.**

**GENE UNIVERSE**

Define the scope as **“a frozen, curated universe of immune-function, immunotherapy-response and immunotherapy-target genes.”** No finite catalogue warrants claiming *all genes biologically related to immunity*. Include immune suppression and resistance, as well as favourable immune activity.

The sources below are recommendations for the freeze, not newly verified downloads. This review used local files only; exact release membership and current drug status remain unverified.

| Tier | Frozen definition and sources | Approximate size | Multiplicity |
|---|---|---:|---|
| **0 — isolated B-P** | Existing antigen-presentation primary; TCGA-PRAD development → CPC-GENE evaluation. | 8 genes | Existing single primary estimand, unchanged. |
| **1 — established panels** | Preserve the 11 panel identities and memberships. Complete the official IFNG Hallmark membership freeze. Preserve individual M5/M6 reporting and CYT’s comparator status. | 111 unique genes currently enumerated, plus the 200-gene Hallmark before deduplication: roughly 250–300 total, maximum 311. | Panel summaries descriptive in the minimal version. Gene tests enter the shared exploratory family below. If formal panel tests are later introduced, Holm across **all panel × study hypotheses**, not separately within every panel. |
| **2 — immunotherapy targets** | Human molecular targets from a pinned published CRI immuno-oncology landscape target table/export, reconciled with IUPHAR/BPS Guide to Pharmacology. Verify approved status against dated FDA/EMA labels; investigational status against named clinical trials or original trial reports. Include checkpoint blockade, co-stimulation, cytokine pathways, innate-immune targets, cell therapies and bispecific engagers. | Planning allowance: approximately 100–300 genes; checkpoint/co-stimulatory targets are only a subset. | Same shared gene-testing family; no separate testing opportunity for a target already in Tier 1. |
| **3 — wider immune biology and response signatures** | Union of the **ImmPort immune-related gene list**, TISIDB’s curated immunomodulator/chemokine/receptor lists, and a fixed signature whitelist: Ayers GEP, Rooney CYT, Charoentong immunophenoscore components, HOPE, and official IFNG, IFNA and inflammatory-response Hallmarks. | ImmPort contributes roughly 1,800 genes; expect roughly 2,000–3,000 unique genes across the complete union. These are planning estimates, not audited counts. | One BH FDR 5% family across **all eligible unique gene × ICI-study tests** in Tiers 1–3. Report the same adjusted result wherever a gene appears. No separate FDR resets by pathway or source. |

Relevant source anchors include [ImmPort, Bhattacharya et al.](https://doi.org/10.1038/sdata.2018.15), [TISIDB, Ru et al.](https://doi.org/10.1093/bioinformatics/btz210), [Ayers et al.](https://www.jci.org/articles/view/91190), [Charoentong et al.](https://doi.org/10.1016/j.celrep.2016.12.019), and the [official Hallmark collection](https://www.gsea-msigdb.org/gsea/msigdb/human/collections.jsp). Target relationships should use the [IUPHAR/BPS resource](https://www.guidetopharmacology.org/) alongside indication-specific regulatory/trial evidence.

**Combination rule:** take the union, canonicalise human gene identifiers, deduplicate biological loci, and retain every source-membership tag. Assign reporting precedence Tier 1 → Tier 2 → Tier 3 without discarding overlap. Freeze literal lists, releases, hashes, inclusion reasons and the 2 November 2026 evidence cutoff **before examining TCGA or ICI associations**. Newly retrieved evidence cannot silently expand that version.

Explicitly retain `PDCD1`, `CD274`, `CTLA4`, `LAG3`, `HAVCR2` and `TIGIT`; audit co-stimulatory targets such as `ICOS`, `CD40`, `TNFRSF4` and `TNFRSF9`. Distinguish a drug-binding target from a ligand, downstream mediator or response biomarker. Tumour antigens targeted by immune therapies belong in a separately tagged target category even when they are not intrinsically immune-function genes. Do not silently restrict the registry to solid-tumour checkpoint antibodies.

**Exclude** wholesale C7/ImmuneSigDB unions, all GO “immune” descendants, unrestricted network neighbours, genome-wide TIDE weights, and every gene reported significant in any ICI study. Exclude generic anticancer drug targets without a documented immunotherapy mechanism. Patient-specific neoantigens, non-gene targets and unmappable entities remain documented outside the gene-level assay universe. Published response signatures derived from these same cohorts cannot be presented as independent validation.

**ANSWERS**

**Q1. Worth adding? Yes, conditionally; retain Q1 and cut Q2 from the minimal version.**

Its useful contribution is whether immune-gene methylation–expression relationships observed in TCGA are also observable in independently collected tumours from patients subsequently receiving ICI. That provides molecular context beyond untreated prostate cohorts.

However, separately estimating correlations is **association consistency**, not transport of a frozen expression predictor. Pretreatment specimens also do not measure an ICI-induced methylation effect.

Q2 would measure association with observed clinical benefit among treated patients. Without an appropriate comparator, it cannot identify benefit attributable to ICI or distinguish predictive from prognostic biomarkers. Small samples, outcome uncertainty and biologically questionable methylation composites make it the weaker use of time.

**Frozen default:** a secondary, outcome-free, cross-cohort association analysis; no clinical-benefit analysis, classifier, cutpoint search or claim of predictive-model validation.

**Q2. Promoter aggregates and panel comparisons? Conditionally valid, but not as currently specified.**

The cited B contracts still describe promoter selection and the 80% threshold as proposed. The draft must point to an actual signed measurement freeze or explicitly establish one for B-ICIM. “B’s frozen rule” cannot substitute for that evidence. See [B’s measurement contract](specs/B/DATA_AND_SOURCES.md).

The main failure modes are:

- **Different measured promoters:** EPIC-only CpGs can change an aggregate relative to TCGA 450K. A 450K mask does not qualify EPIC-only probes. Use an annotation-defined common 450K–EPIC probe set for the TCGA comparison, with pinned platform-appropriate masks.
- **Ambiguous denominator:** 80% must refer to the fixed eligible probe set, not a denominator repeatedly reduced after study-specific failures. One surviving CpG is not broad promoter coverage; report probe counts and flag single-probe measurements.
- **Biological heterogeneity:** alternative promoters, transcript usage and opposing CpG associations can make an average misleading. Do not choose the most negatively correlated promoter. Preserve positive associations and unresolved mappings.
- **FFPE and technical effects:** detection filtering alone does not address restoration, DNA quality, RNA degradation or preservation-associated batch effects. Cho’s source notes report mixed fresh/FFPE RNA; Krakow is FFPE.
- **Composition:** checkpoint RNA often reflects immune-cell abundance. Bulk methylation–RNA associations can arise from cell mixtures. Purity adjustment helps but does not establish tumour-cell regulation.
- **Different RNA estimands:** gene abundance ranked **across patients** is not B-P’s gene percentile ranked **within each sample**. Spearman is not immune to library-size differences; Cho’s counts need a frozen count-normalisation procedure.

Median gene correlations and direction concordance are reasonable **descriptive** panel summaries. They do not establish equivalence to TCGA. Genes are correlated, panels overlap, and TCGA signs near zero are unstable. Do not use independent-gene binomial tests. Patient bootstrap resampling must preserve the complete gene vector and include TCGA uncertainty.

**Frozen default:** one annotation-defined promoter aggregate per eligible gene; the same probe definition in each relevant TCGA–ICI comparison; normalised gene-level RNA; purity-adjusted rank association. Report per-gene results and descriptive panel summaries on exactly matched gene sets. No mean methylation “activation score,” particularly for M5/M6.

Keep LUAD and LUSC benchmarks separate. An unstratified mixed-NSCLC correlation can be driven by histology. Unknown histology or poorly matched melanoma sampling sites limit the result to contextual comparison.

**Q3. Pairing and labels adequate? Adequate leads, inadequate admission evidence.**

Sex concordance is an exclusion check, **not identity confirmation**. It cannot distinguish two patients of the same sex; low expression and tumour chromosome alterations complicate it further.

Require a source-supported patient–specimen–timepoint crosswalk, one baseline specimen per patient, duplicate handling and RNA–DNA specimen compatibility. Use genotype concordance where compatible existing measurements make it straightforward; do not launch a raw-sequencing project merely to rescue this secondary. Author-documented pairing plus concordant metadata can suffice without genetic verification.

Three corrections matter:

- **Jung:** 27 candidate pairs, not 60. The 33 methylation-only patients cannot enter Q1. The local source note reports 60 clinical-table rows, with parsing/missing-outcome problems; that is not 60 verified labels.
- **Cho:** “labels to locate” is stale. [The local source audit](docs/research/cohort_sources/gse126044_SOURCES.md) already records GEO responder/non-responder fields and the published PR/SD-duration definition. The unresolved problem is the reviewed patient mapping and its extension to methylation.
- **Krakow:** 13 shared codes with 5/8 labels are a candidate intersection, not confirmed same-specimen pairs. The 17 methylation samples have a different denominator. Benefit including prolonged SD is not ORR.

**Frozen default:** admit Q1 independently of response-label availability once pairing, timing and assay gates pass. Missing labels must not remove otherwise eligible Q1 patients. Retain unresolved pairs as excluded, not “confirmed by sex.” Thirteen pairs can support descriptive estimates, not a convincing broad discovery or adjusted response model.

**Q4. Statistical design? Per-study estimation is right; omit meta-analysis and Hedges g by default.**

For Q1, use a small, fixed expression model: ranked normalised gene abundance against ranked promoter methylation and independently derived purity. Include known histology or preservation effects only under a frozen, estimable design; do not select covariates by significance. Report an adjusted rank-association measure and patient-level uncertainty, with the unadjusted association as sensitivity.

Purity derived from methylation remains a shared-assay estimate: disclose overlapping probes and reference suitability. If no defensible purity measure exists, the adjusted analysis is unavailable; unadjusted results remain descriptive.

For the two NSCLC studies, modified Knapp–Hartung is permitted by the signed plan but does not solve different histologies, specimens, endpoints or measurement definitions. A two-study forest plot is sufficient. Do not average correlations or panel medians across studies without a separate estimand.

There is also a specification discrepancy: the question mentions **two scores**, but the draft specifies **11 scores plus 21 M5/M6 genes**. Two-score Holm correction cannot cover that analysis.

If Q2 is later authorised, select and name the scores beforehand. On a genuinely comparable beta scale, a mean difference with an interval is more directly interpretable than standardising it into Hedges g. Reserve g for the signed plan’s predeclared cross-platform sensitivity. Correct across every retained score × study × endpoint claim.

**Frozen default:** study-specific Q1 estimates; shared gene-level BH family; descriptive panel summaries; no combined estimate and no Q2. A nonsignificant result receives its interval and an “inconclusive” classification, not a blanket claim that methylation has no relationship with expression.

**Q5. Signed-rule conflicts and omissions? Several require explicit correction.**

- **B-P isolation:** no B-ICIM gene, probe, sign, QC change or result may modify B-P or use CPC-GENE to tune this secondary. Likewise, no automatic rewriting of the TCGA-only C handoff.
- **Rule 7:** merely reporting purity does not satisfy adjustment. Expression models must use methylation and permitted non-RNA covariates, without recycling expression-derived immune scores as independent predictors.
- **B-V:** keep epigenetic-drug combinations outside B-ICIM response analysis. B-ICIM establishes neither demethylation nor drug reversibility; B-V’s attribution restrictions remain intact.
- **Protected families:** “outcome-free” does not authorise inspecting molecular data from an A final-test family. Whole-family protection covers modalities and timepoints.
- **No pooling:** no pooled beta/RNA analysis or joint harmonisation across studies; no endpoint merging. Distinct publications alone do not establish patient independence.
- **Programme status:** locked panel identity does not authorise new scores. The registry explicitly leaves several scoring rules unresolved; the IFNG membership is still null.
- **Release status:** the draft is unsigned. Scope approval is not measurement readiness or permission to bypass the review and production gates.

These follow the [signed integrated amendment](specs/amendments/2026-10-29-integrated-plan/AMENDMENT.md) and [B’s immune-barrier framework](specs/B/IMMUNE_BARRIER_FRAMEWORK.md).

**Frozen default:** a separately released B-ICIM supplement with its own source, exposure, measurement and multiplicity freeze. Report supported, inconclusive and unmeasured findings without causal silencing, prostate-ICI or reversibility claims.

**Q6. Is 20 hours realistic? Not for the draft’s full scope.**

Three raw-IDAT cohorts, specimen reconciliation, broad target curation, TCGA matching, purity qualification, two research questions and publication-quality reporting are not a credible unconditional 20-hour commitment.

It can be a realistic **stop-loss budget** for one cohort if existing curated exports and processing infrastructure are reusable. Broad gene coverage adds little computation; source qualification and measurement interpretation consume the time.

**Frozen default:** Jung first, chosen for its largest candidate paired sample and existing RNA admission—not its results. Allocate approximately four hours to feasibility, four to universe/measurement freeze, six to processing and QC, three to estimation, and three to review/reporting. Stop if those prerequisites cannot fit. Cho and Krakow remain deferred rather than triggering automatic extensions.

**MINIMAL VERSION**

- Freeze the broad curated union and target catalogue; retain the 11 panels as separate reporting annotations.
- Use Jung’s verified pretreatment paired subset only; exclude the 33 methylation-only patients from Q1.
- Apply a common-probe promoter definition, frozen RNA normalisation and qualified non-RNA purity adjustment.
- Estimate gene-level associations; report the full tested family, BH-adjusted results, coverage and uncertainty.
- Produce one association/coverage figure and descriptive panel comparisons against appropriate TCGA histologies.
- Cut Q2, meta-analysis and new composite scores; enforce the 20-hour stop and document deferred cohorts.

**WORDING**

“B-ICIM assesses whether promoter DNA methylation is associated with immune-related gene expression, after tumour-purity adjustment, in pretreatment tumours from patients receiving ICI, providing cross-cancer molecular context rather than evidence of causal regulation or benefit attributable to immunotherapy.”
