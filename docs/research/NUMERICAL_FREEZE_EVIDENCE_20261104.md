# Numerical freeze evidence, 4 Nov 2026

This note tests the draft `specs/amendments/2026-11-04-numerical-freeze/AMENDMENT.md` against primary sources. It answers five questions, then says what to keep, change or add. It does not repeat `docs/research/ANALYSIS_CODEBASE_SURVEY_20261103.md`.

How sources were read:
- **Code:** read through the GitHub API (`gh api repos/...`). Links carry a commit or tag. Where the repo pins a version, I read that version. Exceptions are stated.
- **Papers:** PubMed records (source: PubMed, with the DOI given). Full text came from PMC where open. Otherwise only the abstract was read, and this is marked **abstract only**.
- **Statistics papers outside PubMed:** the DOI was confirmed through Crossref. Abstracts were read on arXiv where available.
- **Web pages** (MSigDB, Reactome, Cochrane, OSF, NumPy, scikit-learn, Creative Commons, JCI): read through a fetch tool that summarises the page. Short quotes from these are as the tool returned them. Check them on the page before citing them in the thesis.
- **Repo files:** local paths with line numbers, at `codex/a-dav-01`.
- **Nothing was executed against any package.** R has neither `glmnet` nor `fgsea` installed here, and the repo's renv library is empty. Every statement about behaviour comes from reading source and documentation. Claims that need a run are marked **NOT RUN**.

Claims not confirmed from a primary record are marked **UNVERIFIED**.

Checked locally, from gene lists and hashes only:
- Both GMT SHA256 values match the draft. Line counts are 50 and 1,839.
- The IFN-gamma set has 200 unique genes. Its membership hash matches the registry contract.
- `r/renv.lock` and `envs/sc-analysis/requirements.lock` match the hash prefixes in N16.
- `glmnet` 5.2, `fgsea` 1.38.0, `scanpy` 1.12.5, `umap-learn` 0.5.12 and `pynndescent` 0.7.0 are the locked versions.

The 14-of-20 coverage counts were **not** checked. No per-study coverage table is in the amendment folder, and I did not read expression data.

---

## Summary

1. **Decision 1 contradicts a rule approved today.** The panel-coverage amendment says panels need complete coverage in the main results and that `panel_coverage90` "never replaces" the main family. The draft makes 90% the main rule for one panel without saying it overrides that text.
2. **No tool has an evidence-based coverage threshold.** Most tools silently drop missing genes. The numbers that exist (0.8 in a PredictioR example, 10% in a TIDE warning, 20% in AUCell) are unjustified defaults.
3. **The Hallmark pathway family has the same problem and the draft ignores it.** Pathways also need complete coverage (`2026-11-03-analysis-modules/SPEC.md`, line 61), so the formal singscore Hallmark family may hold very few studies.
4. **`thresh` and `maxit` are deprecated arguments in glmnet 5.x.** The objective matches the signed one exactly. The call in the draft should use `control = list(...)`.
5. **One seed is fine as a root, not as a single stream.** Same generator plus same seed gives the same resamples. `fgsea` is nproc-independent by reading the source. The scanpy kNN graph is not guaranteed stable across thread counts or CPUs.
6. **The gene sets are already public, without attribution.** Commit `78dba17` is on `origin/codex/a-dav-01` in a public repo. CC BY 4.0 allows this but needs attribution, which is missing. The draft's citation is also incomplete.
7. **The freeze has no external timestamp.** A signature in a git repo is not a registration.

---

## 1. Missing genes in large gene sets

### 1.1 What tools actually do

| Tool | Behaviour when genes are absent | Stated threshold | Source |
|---|---|---|---|
| singscore | Warns with a count and list, then scores on the rest. The multi-set path intersects silently. | None | [rankAndScoring.R L44-51, L58](https://github.com/DavisLaboratory/singscore/blob/7a45243832a4/R/rankAndScoring.R#L44-L58) |
| GSVA / ssGSEA | Maps genes, then filters sets on size after mapping. Errors only if nothing matches. | `minSize` default 1, an absolute count | [ssgsea.R L124](https://github.com/rcastelo/GSVA/blob/51ef67f8ad81/R/ssgsea.R#L124), [genesets.R L1225-1231, L1282](https://github.com/rcastelo/GSVA/blob/51ef67f8ad81/R/genesets.R#L1225-L1283). Read at devel 2.7.28; the lock has 2.6.15 |
| decoupler | `prune` drops sources with too few shared targets. | `tmin` default 5, an absolute count | [net.py L81-84, L121](https://github.com/scverse/decoupler/blob/27f0006793b2/src/decoupler/pp/net.py#L81-L121) |
| IOBR 2.2.4 | Keeps signatures with enough genes and scores on those present. | `mini_gene_count` 3 (PCA, z-score), 5 and at least 5 for ssGSEA, 2 for the integration path | [calculate_sig_score.R L59-65, L127, L288-295, L406](https://github.com/IOBR/IOBR/blob/4a8f4f290b73/R/calculate_sig_score.R#L59-L65) |
| PredictioR | Returns NA unless the found fraction exceeds `sig.perc`. Genes that are mostly floor values are removed first by `rem()`. | `sig.perc` has **no default**. Every roxygen example uses 0.8. Most functions use `>`; `geneSigIPRES` uses `>=` | [geneSigMean.R L26, L65](https://github.com/bhklab/PredictioR/blob/d29803c85601/R/geneSigMean.R#L65), [geneSigIPRES.R L93](https://github.com/bhklab/PredictioR/blob/d29803c85601/R/geneSigIPRES.R#L93), [rem.R](https://github.com/bhklab/PredictioR/blob/d29803c85601/R/rem.R) |
| SignatureSets | Gene lists only. No scoring code and no coverage rule found. | None | [README](https://github.com/bhklab/SignatureSets/blob/ed57eb0555e6/README.md) |
| TIDEpy | MSI model warns above 10% missing and still scores. Signature scores print missing genes and use the overlap. | Warning at more than 10%, MSI model only | [model.py L35-40](https://github.com/liulab-dfci/TIDEpy/blob/898f609af1f5/tidepy/model.py#L35-L40), [L106-110](https://github.com/liulab-dfci/TIDEpy/blob/898f609af1f5/tidepy/model.py#L106-L110) |
| AUCell | Drops sets with 80% or more of genes missing, and stops if all are. Reports missing counts for the rest. | At least 20% present. This is the only hard fractional floor found besides PredictioR | [02_calcAUC.R L186-202](https://github.com/aertslab/AUCell/blob/91753b327a39/R/02_calcAUC.R#L186-L202) |
| UCell | Default `missing_genes = "impute"` treats absent genes as unexpressed. `"skip"` removes them. | None | [ScoreSignatures_UCell.R L38-39, L72](https://github.com/carmonalab/UCell/blob/f778e091f19e/R/ScoreSignatures_UCell.R#L38-L72) |
| scanpy `score_genes` | Logs a warning and uses the rest. | None | [_score_genes.py L234-239](https://github.com/scverse/scanpy/blob/1.12.5/src/scanpy/tools/_score_genes.py#L234-L239) |
| Seurat `AddModuleScore` | Warns and proceeds. | None | [utilities.R L341](https://github.com/satijalab/seurat/blob/v5.6.0/R/utilities.R#L341) |
| quanTIseq (`quantiseqr`) | Prints found/total and percent, then runs. | None | [quantiseqr.R L261-268](https://github.com/federicomarini/quantiseqr/blob/eaa87d40efba/R/quantiseqr.R#L261-L268) |
| easier | Reports missing genes, then tries re-annotation of old symbols. | None | [compute_scores_immune_response.R L148-189](https://github.com/olapuentesantana/easier/blob/d6354ad182a4/R/compute_scores_immune_response.R#L148-L189) |

Two side notes:
- TIDEpy's guard is `len(ol_gene) < 0`, which can never be true, so its "all missing" error cannot fire ([model.py L107](https://github.com/liulab-dfci/TIDEpy/blob/898f609af1f5/tidepy/model.py#L107)).
- easier's re-annotation step is the closest published match to this repo's alias table.
- The TIDE paper excluded microarray platforms with fewer than 15,000 genes, or lacking cytotoxic T cell marker probes (Jiang 2018, PMID 30127393, [doi:10.1038/s41591-018-0136-1](https://doi.org/10.1038/s41591-018-0136-1)). That is a dataset gate for analysis, not a coverage rule for scoring a gene set.

**Ayers GEP has no missing-gene rule because it is assay-locked.**
- The Ayers paper ran on a custom 680-gene NanoString panel. The 6-gene and 18-gene research signatures were plain means. The source says they were scored "by averaging of the included genes" ([JCI page](https://www.jci.org/articles/view/91190); Ayers 2017, PMID 28650338, [doi:10.1172/JCI91190](https://doi.org/10.1172/JCI91190)).
- The final 18-gene GEP is a **weighted** sum of housekeeping-normalised values (same source). Danaher 2018 describes the same structure for the Tumor Inflammation Signature (PMID 29929551, [doi:10.1186/s40425-018-0367-1](https://doi.org/10.1186/s40425-018-0367-1)).
- PMC served no full text for Ayers, so this rests on the JCI page.

**Is a threshold stated anywhere?** Not with evidence. In the code above, the only fractional numbers are PredictioR's example 0.8, TIDE's 10% warning and AUCell's 20% floor. None of them comes with a justification that I could find in the code. I found no paper that derives 80% or 90%. My PubMed searches (combinations of gene signature, gene set score, missing genes, incomplete coverage, subset, robustness, single-sample scoring) returned only unrelated prognostic-signature papers. That is a negative search, not proof of absence.

So 90% is defensible as a prespecified judgement. It is stricter than the only ICI-specific precedent (PredictioR at 0.8). It cannot be cited as an established standard.

### 1.2 Is an unweighted mean across studies with different missing genes defensible?

Partly. Standardising removes the scale problem. It does not remove the construct problem.

- **For.** Hedges g is computed within study, so absolute level drops out. SMD pooling exists for studies that used different scales ([Cochrane Handbook v6.5, section 10.5.1](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-10)). Unweighted means have direct precedent in Ayers 2017, and PredictioR also scores on the genes found.
- **Against.** The same Cochrane section says SMD is appropriate only if SD differences reflect measurement scale, not differences in reliability or in population variability. Different gene subsets can break this. A study missing 20 genes measures a slightly different score, so g differs for a reason unrelated to response.
- **Missing is not random (my inference).** Genes are missing through platform design or author filtering. Filtering removes low-count genes, so the missing set can be systematically low-expressed. Immune panels are enriched for immune genes, so what remains is not a random sample of the Hallmark.
- **Variance weighting (my inference).** A mean of raw log expression gives most influence to high-variance genes. Losing one such gene moves the score more than losing several flat genes. Coverage percentage alone does not capture this. PredictioR z-scores genes before averaging, which reduces this ([geneSigMean.R](https://github.com/bhklab/PredictioR/blob/d29803c85601/R/geneSigMean.R)).

At 180+ of 200 genes this is likely small. That is an expectation, not a result, and it can be tested without outcomes (section 1.4).

**"Per study and per patient" needs fixing.** Comparing responders with non-responders needs one gene set for all patients in a study. If coverage varies by patient, the group difference can reflect which genes were measured. Coverage should be set once per study. Genes with any missing value in that study should leave the score for all its patients, or the rule should say otherwise.

### 1.3 The four studies at 65-85 of 200 genes

These are at 33-43% coverage. That clears AUCell's 20% floor but fails the PredictioR example and the draft's own rule. The draft already keeps them out of the main analysis. It does not say what happens next.

- They should not be pooled with the main Hallmark estimate. A set of 65-85 genes chosen by a panel designer is a different instrument, which is the Cochrane concern above.
- They can be reported per study under a different name, for example a custom reduced IFN-gamma score. This follows the repo's own rule that simple averages are named custom scores (`specs/A/BASELINE_BIOLOGICAL_ANALYSIS.md`, line 23).
- They still contribute to any smaller panel where they have complete coverage. The spec already says targeted panels feed section 4.1 only (`specs/A/SPEC_v2.md`, line 48).
- The main Hallmark estimate will therefore contain no targeted or NanoString study. Platform cannot be tested for this panel. State this as a limitation.

**singscore on these panels is outside the tested range.** Foroutan 2018 varied the data's gene count down to 1,000 genes (PMID 30400809, [doi:10.1186/s12859-018-2435-4](https://doi.org/10.1186/s12859-018-2435-4), Methods). Ranks on a panel of a few hundred genes are below that. Bhuva 2020 built stingscore for targeted measurement, and it needs stable genes in the panel (PMID 32997146, [doi:10.1093/nar/gkaa802](https://doi.org/10.1093/nar/gkaa802); [stableGenes.R](https://github.com/DavisLaboratory/singscore/blob/7a45243832a4/R/stableGenes.R)). The signed spec keeps targeted panels out of genome-wide work but does not address this for pathways.

### 1.4 Is the Hallmark set compared with a reduced overlap set anywhere?

I found no published comparison of the full Hallmark IFN-gamma set against a platform-reduced overlap set. **Negative search, UNVERIFIED as absence.** PubMed queries combining Hallmark, NanoString, targeted panel, overlap and ssGSEA returned nothing.

Nearest evidence:
- Foroutan 2018 sub-sampled genes in the data and found singscore stable. That tests the background, not the signature itself.
- Ayers 2017 moved from 10 to 6 genes and 28 to 18 genes, but the paper reports no head-to-head comparison of all sizes (JCI page, as summarised).
- Liberzon 2015 built Hallmarks to be coherent, from founder sets (PMID 26771021, [doi:10.1016/j.cels.2015.12.004](https://doi.org/10.1016/j.cels.2015.12.004)). The IFN-gamma set has 82 founder sets ([MSigDB card](https://www.gsea-msigdb.org/gsea/msigdb/human/geneset/HALLMARK_INTERFERON_GAMMA_RESPONSE.html)). Coherence suggests subsets should track the whole. That is an argument, not a measurement.

Since nobody has published this, the project can do it. It needs no response labels, so it can run before signing:
1. In the studies with high coverage, compute the full score and each reduced score, using each study's actual missing-gene pattern.
2. Report the within-study correlation between full and reduced scores, and the SD ratio.
3. Do the same with the 65-85 gene patterns.

### 1.5 Findings specific to this repo

- **Conflict with signed text.** `specs/amendments/2026-11-04-panel-coverage/AMENDMENT.md`, decisions 3 and 4: main rule unchanged, and `panel_coverage90` is sensitivity only. Also `specs/A/SPEC_v2.md` line 35, `2026-11-03-analysis-modules/SPEC.md` line 61, and the test at line 75 ("incomplete panels are refused"). The draft must name each one it overrides.
- **Alias table does not cover Hallmark.** `gene_aliases.tsv` has 3 rows and the addendum has 1. Only one Hallmark symbol appears across them. The two studies at 176-177 are just below 180. If their gap is symbol drift, as with CCL5 in GSE135222, an alias audit could lift them. Do that audit before signing, and do not move the threshold.
- **Hallmark pathway family.** Pathways need complete coverage, and `singscore` Hallmark is the formal pathway analysis. The same 200 genes then enter two formal families under two scores and two coverage rules. The coverage of the other 49 sets was not checked.
- **`panel_coverage90` membership.** The draft says the 90% rule stays a sensitivity for "the other ten panels". N09 keeps the family. Say whether the family now holds 10 or 11 panels.
- **Overlap between panels.** Counted from the frozen lists: the Hallmark set shares 6 of 8 genes with `P_ANTIGEN_PRESENTATION`, 9 of 18 with `AYERS_GEP_18`, 8 of 16 with M0, 7 of 18 with M1, 6 of 13 with M3 and 5 of 18 with `HOPE_18`. These are not independent results.

---

## 2. Prespecified candidate genes alongside genome-wide testing

### 2.1 Separate family, IHW, stratified FDR, or both

**A separate family is stratified FDR.** Sun 2006 controls FDR separately in each stratum, and shows the aggregated FDR is a weighted average of stratum FDRs (PMID 16800000, [doi:10.1002/gepi.20164](https://doi.org/10.1002/gepi.20164), **abstract only**). So the draft's proposal is Sun's method. It is not a third option.

Efron 2008 argues that one combined analysis can be too conservative or too liberal for subclasses, and gives theory that supports testing within small subclasses ([doi:10.1214/07-AOAS141](https://doi.org/10.1214/07-AOAS141), [arXiv abstract](https://arxiv.org/abs/0803.3863), **abstract only**).

**IHW does not fit.**
- The package sets `nbins` to about m/1500, and messages that many more than 1,000 p-values per group are recommended ([ihw_convex.R L146, L214-215](https://github.com/nignatiadis/IHW/blob/2da27aa7d23c/R/ihw_convex.R#L146)).
- A binary covariate with 21 genes against about 20,000 gives one tiny bin.
- Korthauer 2019 found the gain from covariate methods grows with the number of tests, and that some of these methods fail with few tests (PMID 31164141, [doi:10.1186/s13059-019-1716-1](https://doi.org/10.1186/s13059-019-1716-1)).
- IHW is not in `r/renv.lock`.

Ignatiadis 2016 notes that weighting controls FDR when weights are prespecified (PMID 27240256, [doi:10.1038/nmeth.3885](https://doi.org/10.1038/nmeth.3885)). Genovese 2006 is the standard reference for fixed p-value weights ([doi:10.1093/biomet/93.3.509](https://doi.org/10.1093/biomet/93.3.509), DOI confirmed, not read). Fixed weights would be valid, but choosing them adds a free number for no gain here.

**Answer: separate family only. Not both.**

### 2.2 The same gene in both families

Acceptable, with one condition. Sun's strata are a partition, so a gene in both families is not strictly the Sun design. Two consequences:
- Each family's FDR statement holds on its own. The union of the two discovery lists has no stated FDR. In practice the effect is small: 21 of about 20,000 genes (my reasoning).
- The risk is choosing afterwards. A gene could be claimed from whichever family it passes in.

The fix is a claim rule. For M5 and M6 genes, only the focused family supports a claim. The genome-wide table shows them as flagged rows and is never used for a claim about them. The draft's phrase "not reinterpreted" points this way but should be explicit.

Removing the 21 genes from the genome-wide family would give a clean partition. It would change BH for other genes only slightly, but it would break "full tables are kept". Keeping and flagging them is simpler.

**The two rows for a gene may differ, and the draft does not say so.** Targeted panels contribute to section 4.1 only (`SPEC_v2.md` section 4.2). If a gene sits in both families, the focused row may include targeted studies and the genome-wide row will not. The k differs, so the estimate differs. Genes need k of 3 or more in synthesis (`2026-11-03-analysis-modules/SPEC.md`, line 17). The draft should say whether that applies to the M5/M6 family.

### 2.3 BH at 10% in small families

- BH has no minimum number of tests ([doi:10.1111/j.2517-6161.1995.tb02031.x](https://doi.org/10.1111/j.2517-6161.1995.tb02031.x), DOI confirmed, not read). I found no paper giving a lower limit on family size.
- Sun 2006 warns that a low FDR such as 5% or 10% may not be feasible for some GWA studies. That concerns very large strata. It is not a rule against small ones.
- Benjamini and Bogomolov show that per-family control does not guarantee control in families selected from the data ([doi:10.1111/rssb.12028](https://doi.org/10.1111/rssb.12028), [arXiv abstract](https://arxiv.org/abs/1106.3670), **abstract only**). N09 multiplies families by stratum and endpoint. This matters if results are later highlighted by best family, so highlights should follow a fixed order.
- BH validity under dependence: Benjamini and Yekutieli 2001 ([doi:10.1214/aos/1013699998](https://doi.org/10.1214/aos/1013699998)) is the usual reference for positive dependence. I could not read it. **UNVERIFIED.** R's `p.adjust` page does not state the condition for BH ([p.adjust.Rd](https://github.com/wch/r-source/blob/d0664093b020/src/library/stats/man/p.adjust.Rd)). M6 has mixed regulator roles (registry orientation field), so its statistics may not all be positively related.

**Power, computed here.** M5 and M6 have 21 genes with no overlap. The first BH rejection needs p of 0.1/21 = 0.0048 or less, unless several p-values are small together. With Knapp-Hartung, the test uses t with k - 1 df (survey, section 1.2). The |t| needed for that single-gene threshold:

| k | df | \|t\| needed |
|---:|---:|---:|
| 3 | 2 | 14.44 |
| 4 | 3 | 7.58 |
| 5 | 4 | 5.67 |
| 10 | 9 | 3.72 |

So in lung (k = 3) the family can almost never reject on one gene alone. This is not a reason to change the method. Report these strata as underpowered, and expect null q-values there. This is why melanoma will carry the result.

---

## 3. Reproducibility of random steps

### 3.1 fgsea 1.38.0 (multilevel, eps = 0)

Read at the pinned commit `1fe46448`, whose message marks the Bioconductor 3.23 version bump.

- **`set.seed` is respected.** All randomness comes from R's RNG, at three draws: [L117](https://github.com/ctlab/fgsea/blob/1fe46448457d30235f6de4ab963026aed4a8edf0/R/fgseaMultilevel.R#L117), [L204](https://github.com/ctlab/fgsea/blob/1fe46448457d30235f6de4ab963026aed4a8edf0/R/fgseaMultilevel.R#L204) and [L207](https://github.com/ctlab/fgsea/blob/1fe46448457d30235f6de4ab963026aed4a8edf0/R/fgseaMultilevel.R#L207). The vignette itself calls `set.seed(42)` ([fgsea-tutorial.Rmd L33](https://github.com/ctlab/fgsea/blob/1fe46448457d30235f6de4ab963026aed4a8edf0/vignettes/fgsea-tutorial.Rmd#L33)).
- **`nproc` should not change results.** The simple stage always runs under `SerialParam()` ([L120-123](https://github.com/ctlab/fgsea/blob/1fe46448457d30235f6de4ab963026aed4a8edf0/R/fgseaMultilevel.R#L120-L123)). The only parallel step passes one explicit integer seed into C++ ([L289-293](https://github.com/ctlab/fgsea/blob/1fe46448457d30235f6de4ab963026aed4a8edf0/R/fgseaMultilevel.R#L289-L293)), which builds its own engine ([fgseaMultilevelSupplement.cpp L135-136](https://github.com/ctlab/fgsea/blob/1fe46448457d30235f6de4ab963026aed4a8edf0/src/fgseaMultilevelSupplement.cpp#L135-L136)). Workers do not draw from R's RNG. **Inference from source, NOT RUN.**
- **Cross-platform intent.** The engine is `boost::mt19937` ([util.h L8](https://github.com/ctlab/fgsea/blob/1fe46448457d30235f6de4ab963026aed4a8edf0/src/util.h#L8)). The code replaces `std::uniform_int_distribution`, and a comment says a shuffle was written out for reproducibility between platforms ([util.cpp L9, L40](https://github.com/ctlab/fgsea/blob/1fe46448457d30235f6de4ab963026aed4a8edf0/src/util.cpp#L40)).
- **Seed drift trap.** The number of size groups sets how much `sample()` consumes at L204, and so the seed drawn at L207. Changing the gene sets or the ranked genes changes every pathway's random draws. The frozen GMT hash protects this. Also, `set.seed` must come immediately before each call.
- **`eps = 0`.** This removes the p-value floor. Each pathway gets a `log2err` from [`multilevelError`](https://github.com/ctlab/fgsea/blob/1fe46448457d30235f6de4ab963026aed4a8edf0/R/fgseaMultilevel.R#L265). `r/scripts/fgsea_rank.R` drops `log2err` from its output columns. It also leaves `nproc`, `sampleSize` and `nPermSimple` at defaults, and takes `minSize` and `maxSize` from config, so these are not frozen.

### 3.2 scanpy 1.12.5

**Defaults are seeded.** `random_state = 0` for [`umap` L52](https://github.com/scverse/scanpy/blob/1.12.5/src/scanpy/tools/_umap.py#L52), [`leiden` L54](https://github.com/scverse/scanpy/blob/1.12.5/src/scanpy/tools/_leiden.py#L54), [`neighbors` L93](https://github.com/scverse/scanpy/blob/1.12.5/src/scanpy/neighbors/__init__.py#L93) and [`pca` L67](https://github.com/scverse/scanpy/blob/1.12.5/src/scanpy/preprocessing/_pca/__init__.py#L67).

`tools/sc/prostate.py` lines 381-384 passes no seed, so it already runs with 0. The draft's line "No analysis script sets one today" is true of the code but overstates the gap for scanpy. Setting 20261102 changes the figures, and it also needs passing to all four calls.

**Thread stability is not guaranteed.**
- UMAP layout: scanpy calls `simplicial_set_embedding` directly and does not pass `parallel` ([_umap.py L218-233](https://github.com/scverse/scanpy/blob/1.12.5/src/scanpy/tools/_umap.py#L218-L233)). The default is `parallel=False` ([umap_.py L958](https://github.com/lmcinnes/umap/blob/release-0.5.12/umap/umap_.py#L958)). So this step should be single-threaded. The usual `n_jobs` override in the `UMAP` class ([L1950](https://github.com/lmcinnes/umap/blob/release-0.5.12/umap/umap_.py#L1950)) is not the path used.
- kNN graph: below 4,096 cells, or below 8,192 for Euclidean, scanpy uses exact brute force ([neighbors L734-737](https://github.com/scverse/scanpy/blob/1.12.5/src/scanpy/neighbors/__init__.py#L734-L737)). Above that it uses pynndescent with `n_jobs=settings.n_jobs`. pynndescent reads `numba.get_num_threads()` and splits work by thread ([pynndescent_.py L103, L312](https://github.com/lmcinnes/pynndescent/blob/release-0.7.0/pynndescent/pynndescent_.py#L312)). The graph can therefore depend on thread count. Reading the source shows the dependence exists. I did not measure its size.
- PCA: `tools/sc/prostate.py` uses `svd_solver="arpack"`. An open issue reports different arpack results across CPU counts ([#1187](https://github.com/scverse/scanpy/issues/1187)).
- Leiden: the seed reaches both backends ([L168, L180](https://github.com/scverse/scanpy/blob/1.12.5/src/scanpy/tools/_leiden.py#L168-L180)). The result is only as stable as the graph.
- Open issue [#2014](https://github.com/scverse/scanpy/issues/2014) reports UMAP and Leiden changing across CPUs, even in one container. Setting `NUMBA_DISABLE_JIT=1` stabilised Leiden but not UMAP, per the reporter. [#2114](https://github.com/scverse/scanpy/issues/2114) reports the same for UMAP across Windows PCs.

So fixing the seed gives repeatability on one machine with one thread setting. It does not give portability. Pin `NUMBA_NUM_THREADS` and the BLAS thread variables, record the CPU, and save the graph and embedding as outputs. These are descriptive steps, so a stated tolerance is enough: for example, cluster agreement by adjusted Rand index rather than identical labels.

### 3.3 R, Seurat and bootstrap seeds

- **Seurat resets the session RNG.** `RunPCA` and `RunUMAP` default to `seed.use = 42` and call `set.seed` ([dimensional_reduction.R L958-963](https://github.com/satijalab/seurat/blob/v5.6.0/R/dimensional_reduction.R#L958-L963), [L1445-1457](https://github.com/satijalab/seurat/blob/v5.6.0/R/dimensional_reduction.R#L1445-L1457)). `FindClusters` uses `random.seed = 0` ([clustering.R L320](https://github.com/satijalab/seurat/blob/v5.6.0/R/clustering.R#L320)). `AddModuleScore` uses `seed = 1` ([utilities.R L184](https://github.com/satijalab/seurat/blob/v5.6.0/R/utilities.R#L184)). Any R random step after one of these runs from that fixed seed, not from the seed set earlier. Bootstraps must not share a session sequence with Seurat calls, or must reseed after them.
- **uwot.** With `n_sgd_threads` above 1 and `batch = FALSE`, results are not reproducible even with `set.seed` ([uwot.R L500-503](https://github.com/jlmelville/uwot/blob/90fdd265c8b9/R/uwot.R#L500-L503), master). The default is 0 ([L714](https://github.com/jlmelville/uwot/blob/90fdd265c8b9/R/uwot.R#L714)). This matters if Seurat's UMAP is used on the Lin atlas.
- **Parallel R.** The R `parallel` vignette warns about workers' streams falling into step, and describes L'Ecuyer streams with `nextRNGStream` ([parallel.Rnw L342-387](https://github.com/wch/r-source/blob/d0664093b020/src/library/parallel/vignettes/parallel.Rnw#L342-L387)). `boot`'s parallel section also treats the seed separately ([boot.Rd L251-255](https://github.com/cran/boot/blob/c93d4f5e3210/man/boot.Rd#L251-L255)). BiocParallel's `RNGseed` gives results that do not change with workers or tasks ([Random_Numbers.Rmd L100-118](https://github.com/Bioconductor/BiocParallel/blob/1c24c4947ef3/vignettes/Random_Numbers.Rmd#L100-L118), devel).
- **Generator must be frozen too.** A seed means nothing without the generator. N08 names only the seed. In R that is `RNGkind`, including `sample.kind`. In Python it is `random.Random`, NumPy `Generator`, or legacy `RandomState`. `tools/a_p2` has no bootstrap code yet, so this is still free to set.

### 3.4 One shared seed or different streams

One number is fine as a **root**. It is not fine as the stream for every step.

- Across different generators (R Mersenne Twister, boost mt19937, NumPy PCG64) the same integer gives unrelated sequences in practice (my reasoning). This case is harmless.
- With the same generator and same seed, two steps of the same shape draw the same indices. A-P2's bootstrap and Paper B's bootstrap could use identical resampling patterns when the sizes match, so their Monte Carlo errors would be correlated. The same applies to the 20 repeated 70/30 splits if each is reseeded with the same value.
- NumPy recommends spawning children from one parent. It labels `root_seed + worker_id` unsafe, because nearby seeds can overlap ([NumPy parallel page, v2.5](https://numpy.org/doc/stable/reference/random/parallel.html)).
- Sandve 2013 Rule 6 asks that seeds be recorded (PMID 24204232, [doi:10.1371/journal.pcbi.1003285](https://doi.org/10.1371/journal.pcbi.1003285)). It does not ask for one seed.
- Exception: within one estimand, sharing is required. "Paired" in N08 means the learned score and CYT use the same resample. One stream per estimand, not per score.
- Existing prototype: `tools/a_analysis/endpoint_sensitivity.py` lines 53 and 127 rebuild `random.Random(seed)` with the same value at each use. It is labelled synthetic and non-frozen, but it shows the pattern to avoid.

Recommended scheme: keep 20261102 as root. Keep it unchanged for the signed A-P2 bootstrap. Give every other step a named stream in a table: `SeedSequence(20261102, spawn_key=(k,))` or `default_rng([k, 20261102])` in Python, and `L'Ecuyer-CMRG` streams in R.

Stated seed choice also removes one forking path: a seed can then never be changed after results are seen. A single second-seed run of stochastic steps, reported as a Monte Carlo check, would show the results do not depend on the seed.

---

## 4. Ridge logistic regression in glmnet 5.2

Read at [cran/glmnet `37f9d27dc161`](https://github.com/cran/glmnet/tree/37f9d27dc161), the commit for version 5.2. CRAN lists 5.2, published 2026-10-28 ([CRAN](https://cran.r-project.org/web/packages/glmnet/index.html)). Note that `NEWS.md` still heads it "5.2 (development)".

### 4.1 Does the objective match?

**Yes, exactly, for the character family.**
- The documented objective for non-Gaussian models is -loglik/nobs + lambda × penalty ([glmnet.Rd L288-290](https://github.com/cran/glmnet/blob/37f9d27dc161/man/glmnet.Rd#L288-L290)).
- The vignette gives the logistic form as a 1/N mean plus lambda × [(1 - alpha) ||beta||²/2 + alpha ||beta||₁] ([glmnet.Rmd L442](https://github.com/cran/glmnet/blob/37f9d27dc161/vignettes/glmnet.Rmd#L442)).
- With alpha = 0 and lambda = 0.1 this is mean logistic loss + (0.1/2) Σβ².
- The intercept sits outside the penalty in that formula.
- The default `penalty.factor` of ones stays at one after the rescale to sum to nvars ([base.hpp L10-13](https://github.com/cran/glmnet/blob/37f9d27dc161/src/glmnetpp/include/glmnetpp_bits/elnet_driver/base.hpp#L10-L13)).
- Unlike Gaussian, there is no y standardisation for binomial (glmnet.Rd L290-293 limits it to Gaussian).

### 4.2 Caveats

1. **`thresh` and `maxit` are deprecated as arguments.** Use `control = list(thresh = ..., maxit = ...)` ([glmnet.Rd L110-112, L154-156](https://github.com/cran/glmnet/blob/37f9d27dc161/man/glmnet.Rd#L110-L112); [NEWS L53-60](https://github.com/cran/glmnet/blob/37f9d27dc161/NEWS.md#L53-L60)). The old form still works but raises a `.Deprecated` warning once per session, and it wins over `control` ([glmnet.control.R L258-264](https://github.com/cran/glmnet/blob/37f9d27dc161/R/glmnet.control.R#L258-L264)). Avoid `glmnet.control()` for this, since it persists for the session.
2. **Say `family = "binomial"` as a string.** The draft omits `family`. A string uses the C++ engine. A `binomial()` object uses the R IRLS path, with different controls: `epsnr` and `mxitnr` apply only there ([glmnet.Rd L192-210](https://github.com/cran/glmnet/blob/37f9d27dc161/man/glmnet.Rd#L192-L210); [glmnet.R L435-439](https://github.com/cran/glmnet/blob/37f9d27dc161/R/glmnet.R#L435-L439)). Also state `type.logistic = "Newton"`, which is the default.
3. **Single lambda.** The help page says to avoid a single value and to supply a decreasing sequence ([glmnet.Rd L95-99](https://github.com/cran/glmnet/blob/37f9d27dc161/man/glmnet.Rd#L95-L99)). The stated reason is warm starts and speed. The problem is strictly convex here, so the minimiser is unique, and with p = 4 speed is irrelevant (my reasoning). A single lambda is acceptable. Path-stopping controls should not bind with one lambda, since `mnlam` is 5. The test should still confirm that a fit with `lambda = c(1, 0.5, 0.2, 0.1)` gives the same coefficients at 0.1. **NOT RUN.**
4. **`thresh` is not a coefficient tolerance.** It is relative to null deviance and applies to weighted squared change ([glmnet.control.Rd L82-87](https://github.com/cran/glmnet/blob/37f9d27dc161/man/glmnet.control.Rd#L82-L87); [binomial_base.hpp L291-293, L376](https://github.com/cran/glmnet/blob/37f9d27dc161/src/glmnetpp/include/glmnetpp_bits/elnet_point/internal/binomial_base.hpp#L291-L293); [vignette Appendix 0](https://github.com/cran/glmnet/blob/37f9d27dc161/vignettes/glmnet.Rmd#L1000)). The same threshold gates the outer loop in the engine, and `epsnr` is inert there ([glmnet.control.R L54-55](https://github.com/cran/glmnet/blob/37f9d27dc161/R/glmnet.control.R#L54-L55)). Because it is a squared quantity, 1e-10 means the last step in a coefficient is around 1e-5 in size (my rough estimate, assuming standardised features, NOT RUN). The real error should be smaller. So do not set the test tolerance to 1e-10.
5. **Is `thresh = 1e-10`, `maxit = 1e6` reasonable?** Yes. It is 1,000 times tighter than the 1e-7 default, and `maxit` is 10 times the default of 1e5, which counts total passes. With four features and about 400 patients neither has a cost. The value of `maxit` should never bind. Check `fit$jerr == 0` and `fit$npasses < maxit` ([lognet.R L89-101](https://github.com/cran/glmnet/blob/37f9d27dc161/R/lognet.R#L89-L101)). A tighter `thresh` is free if the test needs it.
6. **Response coding.** glmnet models the second factor level ([lognet.R L39](https://github.com/cran/glmnet/blob/37f9d27dc161/R/lognet.R#L39)). The sign of every coefficient depends on it. Freeze responder as the modelled class.
7. **SD divisor.** `standardize = FALSE` means the signed "training means and SDs" do all the scaling. The penalty acts on that scale, so n versus n - 1 changes the fit slightly. The spec does not say which. glmnet's own docs use 1/n for its y standardisation, which is a different step. Freeze the divisor.
8. **Guards that should not bite.** The class check warns below 8 and stops at 1 or fewer ([lognet.R L9-10](https://github.com/cran/glmnet/blob/37f9d27dc161/R/lognet.R#L9-L10)). N03's minimum of 20 per class clears this. The `pmin` clamp at 1e-9 only acts at |linear predictor| above about 20.7 ([binomial_base.hpp L197, L272](https://github.com/cran/glmnet/blob/37f9d27dc161/src/glmnetpp/include/glmnetpp_bits/elnet_point/internal/binomial_base.hpp#L272)). That cannot happen with standardised features under this penalty unless a feature is extreme (my reasoning).
9. **Young version.** 5.0 (April 2026) removed all Fortran ([NEWS L33-40](https://github.com/cran/glmnet/blob/37f9d27dc161/NEWS.md#L33-L40)). 5.2 is one week old. The renv pin holds it. This is a further reason for the independent check.

### 4.3 Recommended check against direct optimisation

I found no check prescribed in the glmnet documentation. Friedman 2010 describes the method (PMID 20808728; PubMed returned no DOI). The engine itself checks KKT conditions before stopping ([binomial_base.hpp L294-301](https://github.com/cran/glmnet/blob/37f9d27dc161/src/glmnetpp/include/glmnetpp_bits/elnet_point/internal/binomial_base.hpp#L294-L301)).

Use three independent checks on synthetic data:
1. **KKT residuals.** With p the fitted probabilities: mean(p - y) = 0 for the intercept, and (1/n) Xᵀ(p - y) + 0.1 β = 0 for the coefficients. This needs no second solver and is the strongest test.
2. **Direct solver.** Minimise the exact objective with Newton iterations written out, or `optim` with an analytic gradient. Compare coefficients and objective value.
3. **scikit-learn 1.9.1**, already in the lock. Its objective is the weighted mean loss plus r(w)/(SC) with r(w) = ||w||²/2, and `lbfgs` does not penalise the intercept ([User Guide, Logistic regression](https://scikit-learn.org/stable/modules/linear_model.html)). With equal weights S = n, so **C = 1/(0.1 n)**. C must change with n. `liblinear` must not be used, since it penalises the intercept.

Cover these synthetic cases: n near 408 with about 1:2 class balance, correlated features, near-separation, and a training-fold size. Set the numerical tolerance from the first synthetic run and write it into the test before real data. Also confirm that omitting `standardize = FALSE` makes the test fail, so the test has teeth.

---

## 5. What a numerical freeze should contain

### 5.1 What the sources say

No omics-specific preregistration standard was found. The closest sources are these.

- **PRISMA 2020** (PMID 33782057, [doi:10.1136/bmj.n71](https://doi.org/10.1136/bmj.n71)). It is a reporting guide, not a conduct guide. Relevant items: 13a-f synthesis methods, including software (13d) and sensitivity analyses (13f); 14 reporting bias; 15 certainty; 24a-c registration, protocol and amendments.
- **PRISMA-P 2015** (PMID 25554246, [doi:10.1186/2046-4053-4-1](https://doi.org/10.1186/2046-4053-4-1)). This is the protocol checklist, with 17 items. It says "Amendments to a review protocol should be tracked and dated."
- **Gamble 2017** (PMID 29260229, [doi:10.1001/jama.2017.18556](https://doi.org/10.1001/jama.2017.18556), **abstract only**). 55 minimum items for trial statistical analysis plans. It is written for trials, so it is an analogy. Item list not read.
- **Ramasamy 2008** (PMID 18767902, [doi:10.1371/journal.pmed.0050184](https://doi.org/10.1371/journal.pmed.0050184)). A seven-issue checklist for microarray meta-analysis. It recommends a detailed protocol, and names annotation and resolving probe-to-gene mapping as steps. Toro-Domínguez 2021 surveys methods (PMID 32095826, [doi:10.1093/bib/bbaa019](https://doi.org/10.1093/bib/bbaa019), **abstract only**).
- **OSF.** A registration is a time-stamped, read-only record, with embargo up to four years and a DOI when public. Templates include Secondary Data Preregistration and Generalized Systematic Review ([OSF help](https://help.osf.io/article/330-welcome-to-registrations)).
- **Van den Akker 2021.** A secondary-data template, motivated by bias from prior knowledge of the data ([doi:10.15626/MP.2020.2625](https://doi.org/10.15626/MP.2020.2625), abstract only; the PDF was unreadable to the tool). Van den Akker 2023 gives the generalized form ([doi:10.1186/s13643-023-02281-7](https://doi.org/10.1186/s13643-023-02281-7), DOI confirmed, not read).
- **A-P2 reporting.** TRIPOD+AI (PMID 38626948, [doi:10.1136/bmj-2023-078378](https://doi.org/10.1136/bmj-2023-078378), not read) and REMARK (PMID 16106022, [doi:10.1093/jnci/dji237](https://doi.org/10.1093/jnci/dji237), abstract only) are the likely reporting guides.
- **PROSPERO:** eligibility could not be read. The site did not render to the tool. **UNVERIFIED.** Whether this study fits it should be checked by hand. PubMed shows PROSPERO used with some transcriptomic work, for example [doi:10.3389/fimmu.2026.1925741](https://doi.org/10.3389/fimmu.2026.1925741), PMID 42688457, but there the registered review was a clinical meta-analysis.

I did not find a comparable ICI transcriptomic meta-analysis with a public numerical freeze. Not an exhaustive search.

### 5.2 Missing from the draft

The register's own `evidence_needed` column in `specs/A/NUMERICAL_FREEZE_REGISTER.tsv` is a useful check. Several items it asks for are absent from the draft.

| Missing item | Why | Source |
|---|---|---|
| External timestamped registration | Git history can be rewritten, and a signature is not third-party evidence | OSF help; PRISMA 24a |
| Dated deviation log | Amendments must be tracked | PRISMA-P; PRISMA 24c |
| Statement of prior knowledge | The cohorts are published and outcomes are widely known. "No result on real data" does not cover what the authors have read | Van den Akker 2021; `SPEC_v2.md` notes Riaz prior exposure |
| Per-study coverage table, hashed | The draft cites 14 of 20 with no table | PRISMA 13a |
| Study roster and input matrix hashes | Fixes the data the numbers apply to | PRISMA 13b |
| Alias table hash, extended to Hallmark | Coverage counts depend on it | Section 1.5; Ramasamy 2008 |
| Cross-cancer weighting | The spec says it is "stated". N10 does not state it | `SPEC_v2.md` section 4.1 |
| Reporting rules for k = 1, 2 and low k | Exists in the analysis-modules spec, not in N10 | `2026-11-03-analysis-modules/SPEC.md` lines 14-17 |
| Explicit `escalc` settings | "Defaults" can change. Today: `vtype = "LS"`, `correct = TRUE` | [escalc.Rd L13](https://github.com/wviechtb/metafor/blob/master/man/escalc.Rd#L13) (master, not the pinned tag) |
| singscore settings | `centerScore`, direction, and gene universe affect values | [rankAndScoring.R](https://github.com/DavisLaboratory/singscore/blob/7a45243832a4/R/rankAndScoring.R) |
| fgsea settings | `minSize`, `maxSize`, `nPermSimple`, `sampleSize`, `nproc`, ranking statistic | Section 3.1 |
| Reporting bias and certainty methods | PRISMA items 14 and 15. Neither is stated. A statement that they are not done is acceptable | PRISMA 2020 |
| List of sensitivity analyses | PRISMA 13f | PRISMA 2020 |
| Container digest | N16's `evidence_needed` asks for it. The draft has lock hashes only | Register TSV |
| Solver retry rule | N07's `evidence_needed` lists retry | Register TSV |
| Bootstrap precision | N08's `evidence_needed` lists precision | Register TSV |
| Panel weights and orientation | See below | Registry v1 |

**N11 "unweighted" conflicts with the registry.**
- `AYERS_GEP_18` is a weighted score in the source (section 1.1). An unweighted mean of its genes is a custom score and must be named so (`BASELINE_BIOLOGICAL_ANALYSIS.md`, line 23).
- The registry marks `CD276` negative in the Ayers vector, `HAVCR2` adverse in `HOPE_18`, opposing semantics in `M4_EXCLUSION`, and mixed roles in `M6`.
- A plain mean treats all as positive. Registry orientation is still "unfrozen" for several panels.
- Registry `scoring_status` values such as `registry_only_no_score_authorized` also need lifting or overriding.

### 5.3 MSigDB licence and citation

**Licence.**
- MSigDB content is under CC BY 4.0 for v2022.1 and above, with extra terms for some gene sets ([MSigDB licence page](https://www.gsea-msigdb.org/gsea/msigdb_license_terms.jsp)).
- The named exceptions are KEGG, BioCarta and AAAS/STKE. Neither Hallmark nor Reactome is listed as an exception.
- Reactome's own data are under CC0 ([Reactome licence](https://reactome.org/license)).
- So redistributing both GMT files in a public GitHub repo appears allowed. This is my reading, not legal advice.

**Conditions.** CC BY section 3(a) requires retaining credit and notices, stating modification, and naming the licence ([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/legalcode.en)).

**Current state.** Both files are already on `origin/codex/a-dav-01` (commit `78dba17`). The repo is public (`gh repo view`) and has no licence file. The amendment folder has no notice file. The GMT files carry only `MSigDB_2026.1.Hs` in column 2, and these files are a reformatted export from `msigdbr`, not the Broad's own files. Attribution should be added. msigdbr's MIT licence covers the package ([DESCRIPTION](https://github.com/igordot/msigdbr/blob/b2de6a3d9c6693070c73aa03e09fa031fc0a4589/DESCRIPTION)), not the data terms (my reading).

**Citation.** "Cite MSigDB and Liberzon 2015 for Hallmark" is partly right but incomplete. The MSigDB site asks for:
- Subramanian 2005 as the core citation (PMID 16199517, [doi:10.1073/pnas.0506580102](https://doi.org/10.1073/pnas.0506580102));
- Liberzon 2011 (PMID 21546393, [doi:10.1093/bioinformatics/btr260](https://doi.org/10.1093/bioinformatics/btr260)) and Liberzon 2015 (PMID 26771021) where appropriate;
- the source of each gene set, from its page ([MSigDB home](https://www.gsea-msigdb.org/gsea/msigdb/index.jsp)).

For Reactome, add a Reactome reference such as Milacic 2024 (PMID 37941124, [doi:10.1093/nar/gkad1025](https://doi.org/10.1093/nar/gkad1025)). Check Reactome's "Citing us" page, which I did not read. Check `specs/A/references.bib` too: my grep of it and `SOURCES.md` for MSigDB terms found no entries.

**Version.**
- MSigDB is now at 2026.2.Hs (October 2026), with 1,867 Reactome sets against 1,839 in the draft ([collections page](https://www.gsea-msigdb.org/gsea/msigdb/human/collections.jsp)). Hallmark still has 50.
- Pinning 2026.1 is fine, as `msigdbr` 26.1.1 is tied to it ([NEWS](https://github.com/igordot/msigdbr/blob/b2de6a3d9c6693070c73aa03e09fa031fc0a4589/NEWS.md)). The draft should say it is not the latest and that this was deliberate.
- Whether Hallmark IFN-gamma membership changed in 2026.2 is **UNVERIFIED**. The release notes did not render.
- `msigdbr` downloads its data at run time from a Zenodo zip ([utils.R L69](https://github.com/igordot/msigdbr/blob/b2de6a3d9c6693070c73aa03e09fa031fc0a4589/R/utils.R#L69)). So the package pin alone does not fix the bytes. The draft's GMT hashes do, and they should stay the authority. Record the Zenodo URL too.

---

## Implications for the draft

### Decision 1: coverage rule — CHANGE

| Action | What | Reason and source |
|---|---|---|
| Change | State that this overrides panel-coverage decisions 3 and 4, `SPEC_v2.md` line 35, and analysis-modules lines 61 and 75. Update the test | They say the opposite (section 1.5) |
| Keep | 90% as a judgement call, with strict coverage alongside | Stricter than PredictioR's example 0.8. No source validates any value (section 1.1) |
| Change | Write "at least 180 of 200", not "90% or more" alone | PredictioR mixes `>` and `>=` |
| Change | Coverage set once per study, not per patient | Within-study comparability (section 1.2) |
| Add | Alias audit for all 200 symbols before signing. Do not change the threshold | Alias tables hold 4 rows; two studies at 176-177 (section 1.5); easier does this step |
| Add | Outcome-blind bridging check before signing | Nothing published (section 1.4) |
| Add | Fixed common-gene sensitivity across included studies | Same instrument in all studies, meeting the Cochrane SMD assumption |
| Add | Four targeted studies: per-study only, custom name, not pooled | Cochrane 10.5.1; `BASELINE_BIOLOGICAL_ANALYSIS.md` line 23 |
| Add | Rule for the Hallmark pathway family, and whether targeted panels may enter singscore | Same coverage rule; below Foroutan's tested range |
| Add | Report `n_found`, missing gene list, and platform limitation | Panel-coverage decision 4 |

### Decision 2: M5 and M6 family — KEEP, with additions

| Action | What | Reason and source |
|---|---|---|
| Keep | One separate family, BH 10% | This is stratified FDR (Sun 2006; Efron 2008) |
| Keep | No IHW | Too few hypotheses (IHW source; Korthauer 2019) |
| Add | Claim rule: M5/M6 claims come only from the focused family. Genome-wide rows are flagged | Section 2.2 |
| Add | State the k rule, and whether targeted studies enter this family | Rows can differ (section 2.2) |
| Add | Fixed reading order across strata and endpoints | Benjamini and Bogomolov |
| Add | Expect low power at low k. State this before results | Table in section 2.3 |

### Decision 3: seeds — CHANGE

| Action | What | Reason and source |
|---|---|---|
| Keep | 20261102 as root, and for the signed A-P2 bootstrap | Signed; recording seeds is what Sandve asks |
| Change | Named stream per step, one per estimand. No shared stream across steps | NumPy guidance; R `parallel` vignette |
| Add | Freeze generators, not just seed values | Section 3.3 |
| Add | fgsea: `set.seed` right before each call, `nproc = 1`, keep `log2err` | Section 3.1 |
| Add | scanpy: pass `random_state` to all four steps, pin thread variables, save the graph, tolerance-based comparison | Section 3.2 |
| Add | Seurat: pass seeds explicitly, set `n_sgd_threads`, never rely on session RNG after a Seurat call | Section 3.3 |
| Change | Reword "No analysis script sets one today". scanpy and Seurat have fixed defaults | Section 3.2 |
| Add | One second-seed Monte Carlo check, reported | Shows the seed does not drive results |

### Decision 4: ridge solver — CHANGE the call, KEEP the method

Proposed form:

```r
glmnet(x, y, family = "binomial", alpha = 0, lambda = 0.1,
       standardize = FALSE, intercept = TRUE,
       control = list(thresh = 1e-10, maxit = 1e6))
```

| Action | What | Reason and source |
|---|---|---|
| Keep | `glmnet` 5.2, alpha 0, lambda 0.1, `standardize = FALSE`, `intercept = TRUE` | Objective matches exactly (section 4.1) |
| Change | Move `thresh` and `maxit` into `control`; state `family = "binomial"` | Deprecated; two execution paths (section 4.2) |
| Add | Responder as modelled class; freeze SD divisor | Section 4.2, caveats 6 and 7 |
| Add | Test: KKT residuals, direct solver, scikit-learn with C = 1/(0.1 n), a lambda-path comparison, and a stated tolerance. Check `jerr` and `npasses` | Section 4.3 |
| Add | Retry rule (for example, none; stop on `jerr != 0`) | N07 `evidence_needed` |

### Register

| ID | Action | What |
|---|---|---|
| N01-N04 | Keep | No evidence against them. N01 still needs actual weights from the roster, as the TSV says |
| N05 | Keep | SUPERSEDED, with a pointer to the validation amendment |
| N06 | Keep | Objective confirmed |
| N07 | Change | Use the call above; add test tolerance and retry rule |
| N08 | Change | Add generator, stream name and precision. Say "paired" means one shared resample |
| N09 | Change | State `escalc` arguments rather than "defaults". Clarify `panel_coverage90` membership (10 or 11). Add the k rule for M5/M6 |
| N10 | Add | Cross-cancer weighting and low-k reporting rules |
| N11 | Change | Weighted or custom status for `AYERS_GEP_18`; orientation per panel; override of registry scoring statuses |
| N12-N15 | Keep | OPEN |
| N16 | Add | Container digest or an explicit reason for none; thread variables; CPU record |
| New | Add | RNG stream table; alias table hash; coverage table hash; study roster and input hashes; fgsea and singscore settings; sensitivity list; reporting bias and certainty position |
| Format | Change | Match the TSV's columns and status terms (`setting_id`, `branch`, `value`, `status`, `owner`, `evidence_needed`, `blocked_stage`). The draft's table has different columns |

### Outside the register

- **Add** an external timestamped registration at signing. OSF offers Secondary Data and Generalized Systematic Review templates, with embargo. Whichever is used, keep the commit hash in it.
- **Add** a dated deviation log and a prior-knowledge statement.
- **Add** an attribution notice beside the GMT files, now, because they are already public. Complete the citation (section 5.3).
- **Add** a line saying 2026.1 was chosen deliberately over 2026.2.

---

## Could not verify

- Any tool behaviour by execution. No package was run. fgsea `nproc` independence, the glmnet path comparison, and the size of `thresh` effects are all NOT RUN.
- The 14-of-20 and 65-85 gene counts, and coverage of the other 49 Hallmark sets.
- Whether Hallmark IFN-gamma membership differs between 2026.1 and 2026.2. MSigDB release notes did not render.
- PROSPERO eligibility.
- Full text of: Sun 2006, Efron 2008, Benjamini and Bogomolov, Benjamini and Yekutieli 2001, BH 1995, Genovese 2006, Gamble 2017, Van den Akker 2021 and 2023, TRIPOD+AI, Cristescu 2018 (PMID 30309915, [doi:10.1126/science.aar3593](https://doi.org/10.1126/science.aar3593), abstract only, not relied on).
- The BH dependence condition (positive dependence). Not read from the primary paper.
- Friedman 2010 has no DOI in the PubMed record. Its PMID is confirmed by citation lookup.
- TIDE paper: searched by keyword in the PMC text only, not read in full.
- GSVA was read at devel 2.7.28, BiocParallel at devel, uwot and metafor at master. These are not the locked versions. Line numbers may differ for the locked versions.
- ESTIMATE was not checked (no GitHub source found).
- Absence claims (no validated threshold, no Hallmark versus overlap comparison, no omics freeze standard) rest on limited PubMed searches. The search tool combines all terms with AND, so broad queries returned little.
