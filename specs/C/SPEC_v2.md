# Paper C: consolidated specification v2.1, 3 Nov 2026

**Status: SIGNED by the user on 3 Nov 2026 ("I sign it"), v2.1.** It consolidates the approved C framework (`docs/decisions/C_FRAMEWORK_20261015.md`: C3 prioritisation, bounded C2 discovery, C1 calibration, paired Q_M versus Q_E primary) and re-bases its inputs on the signed v2.1 specs of Papers A, A.1 and B (3 Nov 2026). The decisions come from the user's answers on 3 Nov 2026 (decisions C-Q1 to C-Q12; all recommendations accepted except C-Q3, where the user chose to include M4, M5, M6, the negative-weight Ayers genes and all HOPE_18 genes). One astra-high review was applied (`specs/C/REVIEW_ASTRA_HIGH_20261103.md`). Where the older files in `specs/C/` and `specs/C/revision_20261015/` disagree with this document, this document prevails; the older files keep the technical detail (compound identity, WTCS parity, source records, pharmacology fields, wet-lab handoff).

> **DRAFT amendment pending, 4 Nov 2026, NOT SIGNED:** `specs/C/AMENDMENT_C_VIRTUAL_20261104.md` proposes the conditional secondary module C-VIRTUAL (Paper D merged into C). Until the user signs it, the signed text below applies unchanged. No C product, gate or claim depends on it.

**Amendments to the 15 Oct kit made here (explicit):** (1) the queries are built from B v2.1 outputs, not from a B "deficit contrast" (B v2.1 has none); (2) Q_E is an expression-matched comparator, not a deficit-ranked list; (3) the primary scores re-expression of all eligible genes, not programme-first desired-direction restoration; (4) the primary is restricted to DNMT-inhibitor experiments; (5) programme quotas are replaced by stratum-matched pairs.

## 1. Question and products
**Question.** In prostate cancer, do immune genes whose low expression is associated with promoter methylation (Paper B) re-express more after a DNA-methyltransferase inhibitor than equally expressed immune genes without that methylation support? Which compounds, models and exposures then deserve prospective testing?

**Products, in order of importance:**
1. **C-P (single primary):** the paired Q_M versus Q_E re-expression difference, Δ_Q, in independent measured prostate DNMT-inhibitor experiments.
2. **C-FAV (key secondary):** the same estimand restricted to genes whose re-expression is immunologically favourable.
3. **C-CLASS (secondary):** the C-P estimand in HDAC-inhibitor and EZH2/PRC2-inhibitor experiments, each its own family.
4. **C2 (discovery):** bounded LINCS2020 screen of a curated epigenetic-compound universe in prostate lines; C1 three-drug anchor as calibration.
5. **C-CONTEXT:** model relevance, viability and stress, mechanism and immune context, pharmacology.
6. **C-HANDOFF:** evidence tiers, Pareto set and the prospective wet-lab nomination.

## 2. Inputs from Papers A, A.1 and B (frozen, hash-checked)
| From | Product | Use in C | Not used for |
| --- | --- | --- | --- |
| B §3 | Tier 1+2 gene lists (frozen before any association) | Gene pool | — |
| B §5 model, TCGA-PRAD fit only | Per-gene promoter-methylation coefficient and its test | Methylation gate for Q_M (C-Q5) | CPC-GENE results never select C genes (11 Sep contract: TCGA-discovery-only table) |
| B §8 rule | Frozen single-cell compartment rule | C applies it to every pool gene (C-Q4) | — |
| B §4 | TCGA-PRAD log2(TPM+1) | Expression matching of Q_E (C-Q6) | — |
| A §4.1 (A-BIO) | Per-panel and per-gene response effects | Annotation: concordance with the gene's desirability label | Not a selection filter |
| A.1 | longitudinal_support.tsv | Annotation: the response-associated differential change (response-time interaction), with window, regimen and uncertainty | Not a selection filter |
| A §5 (A-P2) | Frozen predictor | Nothing | Coefficient signs are never restoration directions |
| B-V | Epigenetic-drug + ICI clinical cohorts | Cited as Level 3 context only (C-Q11) | Never re-analysed, never Level 2 |

**IMvigor210 is never read by C**, in any modality. C reads no CPC-GENE outcome, no A final-test result and no A.1 reserved data.

## 3. Queries (frozen before any perturbation outcome is read)
### 3.1 Pool P (C-Q2, C-Q3, C-Q4)
A gene g enters P only if all hold:
1. g is in B Tier 1 (all 11 locked panels, including M4, M5, M6, all AYERS_GEP_18 and all HOPE_18 genes) or Tier 2;
2. g is labelled **epithelial/malignant** by B's frozen single-cell rule, applied by C to every Tier 1+2 gene on the hormone-naive atlas (outcome-free). "Mixed" genes enter only sensitivity (c); immune/stromal-only and `below_scRNA_detection_limit` genes are reported, not scored;
3. g has an eligible promoter-methylation aggregate under B §4, so "not supported" always means tested and not supported, never untested.

### 3.2 Direction and desirability
DNMT inhibition is expected to raise expression of methylation-repressed genes. The primary therefore scores **re-expression (up)** for every pool gene (C-Q2). Separately, each gene gets a frozen, reasoned **desirability label** in `c_gene_direction_table.tsv`:
- `favourable`: re-expression is expected to help immune recognition (P_ANTIGEN_PRESENTATION, HALLMARK_IFNG, M0, M1, M3, positive-weight AYERS genes);
- `unfavourable`: re-expression is expected to oppose it (M4_EXCLUSION genes);
- `ambiguous`: M5 checkpoints (for example CD274 is both an immune-evasion molecule and the ICI target), M6 regulators, negative-weight AYERS genes (for example CD276), HOPE_18 genes not in another favourable panel, Tier 2 targets without a panel.
Precedence for genes in several panels: `unfavourable` > `ambiguous` > `favourable`. The table is frozen with one line of justification per gene. A-BIO and A.1 concordance are annotation columns.

### 3.3 Q_M and Q_E
**Q_M** = genes in P whose TCGA-PRAD promoter-methylation coefficient is negative with BH q < 0.05.
- Model, as in B §5: expression_g ~ purity + copy number (per B's gate) + global methylation + promoter_methylation_g, OLS in TCGA-PRAD; two-sided Wald t-test on the methylation coefficient.
- BH family: all genes of P with an eligible aggregate. This is C's own discovery family, separate from B's Tier 1+2 family; B's q-values are kept as a separate column.
- Selection stability: proportion of 200 patient-bootstrap refits that select each gene (descriptive).
- Genes not selected are "not supported": never "unmethylated" or "unregulated".

**Q_E** = the expression-matched comparator (C-Q6).
- **Stratum:** the gene's first locked panel in registry order; Tier 2-only genes form one stratum.
- **Matching:** for each Q_M gene, in order of TCGA-PRAD median log2(TPM+1) then gene symbol, the not-supported P gene in the same stratum with the nearest TCGA-PRAD median log2(TPM+1), within a caliper of 0.5 log2 units, without replacement.
- **Unmatched:** a Q_M gene without a partner within the caliper leaves both queries and is listed.
- **Balance table:** per stratum and overall, the TCGA-PRAD expression, CpG-island promoter status, eligible probe count, desirability label and CCLE baseline expression of both queries.
- Matching reduces tumour baseline-expression imbalance. It does not remove the expression floor in cultured cells; sensitivities (a) and (b) address this.

**Size rule.** C-P is estimable only with at least 10 matched pairs. Otherwise C-P is "not estimable" and C continues with C-FAV (if estimable), C2, C-CONTEXT and C-HANDOFF. Ten is a minimum for a usable score, not a power calculation.

The pool, exclusions with reasons, the direction table, Q_M, Q_E, the balance table and their SHA-256 hashes are released in `c_query_release.json` before any perturbation matrix is opened.

## 4. C-P: primary
### 4.1 Sources (Level 2) and audit first (C-Q9)
A metadata-only, accession-level admission audit runs **first**, before any LINCS download. Each accession row records: exact chemical (azacitidine and decitabine are different exposures), dose, duration, schedule and washout, genotype, cell model, control, independent cultures per arm, platform, probe-to-gene rule, combination or time-course arms, and overlap with other studies. A study is admitted only if all hold:
1. human prostate cancer cell line, organoid or explant;
2. a DNMT inhibitor alone against a vehicle or untreated control in the same experiment;
3. a full measured feature space (array or RNA-seq), not a DE-gene table; old arrays need an explicit probe-to-gene collapse and a cross-hybridisation flag;
4. at least 3 independent cultures per arm (not wells, time points or cell lines); 2 per arm: descriptive only;
5. replicate, block and control structure reconstructable from metadata;
6. at least 80% of Q_M and of Q_E measured, and their coverage within 10 percentage points;
7. no overlap with LINCS, B patients or another admitted study.

**Time point:** per study, the longest exposure up to 7 days that has at least 3 cultures per arm, frozen in the audit. **Combination arms** are excluded from C-P.

Candidates from one GEO search (none audited yet): GSE63196 (decitabine; 22Rv1, DU145, LNCaP), GSE186782 (azacitidine), GSE184168 (DNMT), GSE2932, GSE4089, GSE25346, GSE18573 (older, small arrays). **GSE216053 is blocked**: its titles say decitabine but its genotype field says DNMT1 knockout (`docs/research/POST_M1_EVIDENCE.md`).

### 4.2 Score
In each sample i, singscore (version pinned at gate 5) on the full measured universe, up-direction, unweighted, each gene once (C-Q7): S_i(Q) = mean over g∈Q of the scaled rank of g, centred as in Foroutan et al. 2018 (BMC Bioinformatics 19:404, doi:10.1186/s12859-018-2435-4), ties averaged, absent genes skipped and counted. D_i = S_i(Q_M) − S_i(Q_E).

### 4.3 Per study (C-Q8)
Ordinary least squares on the single score D (no limma moderation: one score has no gene-wise variance to borrow):
D_i = Σ_c μ_{c,t} · 1[context c, arm t] (+ block terms for paired or batch designs).
- Contrast per context c (cell line, dose): δ_{s,c} = μ_{c,treated} − μ_{c,control}.
- Study effect: δ_s = (1/C_s) Σ_c δ_{s,c}, equal context weights fixed in the audit; SE_s from the OLS covariance (shared controls handled within the same fit); ν_s = residual degrees of freedom.
- The same model on S(Q_M) and on S(Q_E) gives their separate treatment effects; these are always reported.

### 4.4 Across studies
Δ_Q = (1/k) Σ_s δ_s over the k admitted studies.
SE(Δ_Q) = √(Σ_s SE_s²) / k.
ν = (Σ_s SE_s²)² / Σ_s (SE_s⁴ / ν_s) (Welch–Satterthwaite).
95% interval: Δ_Q ± t_{0.975, ν} · SE(Δ_Q).

Δ_Q is a finite-set, equal-study summary of the admitted studies. It is not a population drug effect. Wording (B rule 7 style):
- **"Methylation advantage supported"**: k ≥ 3, the lower bound is above 0, and the equal-study mean effect on S(Q_M) itself is positive (a positive Δ_Q from both queries falling is not re-expression).
- **"Inconclusive"**: the interval includes 0 (no equivalence margin is set, so no "no advantage" claim).
- **"Expression-only advantage"**: the upper bound is below 0.
- k = 1–2: δ_s reported descriptively, no Δ_Q (C-Q10).
- Leave-one-study-out range always reported. REML with modified Knapp–Hartung is a sensitivity for a different, population-level estimand, only if k ≥ 5.

### 4.5 Prespecified sensitivities
(a) Q_E matched on CCLE baseline expression of the study's own cell line instead of TCGA-PRAD; (b) matching also on CpG-island promoter status; (c) pool including "mixed" genes; (d) per-stratum δ; (e) common-measured-gene matching within each study; (f) excluding studies with exactly 3 cultures per arm; (g) gene-length and array-probe check (descriptive).

## 5. Secondaries
1. **C-FAV (key secondary):** C-P restricted to `favourable` genes (pairs re-formed under the same rules within that subset). Only here may results be called "desired-direction" responsiveness; restoration of an established prostate deficit is not claimed, because B v2.1 does not test a deficit.
2. **C-CLASS:** the C-P estimand in HDACi studies (candidates GSE35242, GSE74418, GSE80657, GSE149784 HDAC arm) and EZH2/PRC2 studies (GSE80239, GSE298094, GSE149784 EZH2 arm, GSE294887 human arms), each a separate family. Holm is applied across the study-specific δ_s within each family; the class summary is reported with its interval and no test. No expectation is fixed: a methylation advantage is mechanistically expected for DNMTi, not for HDACi or EZH2i.
3. **Cell-line methylation (never cut):** within each admitted DNMTi experiment, the per-gene treatment effect for Q_M genes methylated versus not methylated in that line (CCLE RRBS, pinned release). Descriptive. It separates "hypothesis failed" from "the model lacks the methylation".
4. **C2 LINCS discovery (after the audit, C-Q11):** LINCS2020 Level 5 `trt_cp` (35.5 GB, S3, hash-pinned) restricted to PC3, VCaP, 22Rv1, LNCaP; curated compound universe (DNMT; HDAC with isoform class; EZH2/EED; other chromatin classes only with a predeclared link). One-sided weighted enrichment on Q_M and on Q_E separately, after parity with the pinned cmapM `getCombinedES` path; raw WTCS only where a bidirectional query exists. Results stay indexed by compound × cell × dose × time × project; coverage reported as landmark / best-inferred / other-inferred / absent. No compound p-value, no class superiority.
5. **C1 calibration:** decitabine, entinostat, tazemetostat at PC3/24 h/1.11111 µM, per compound, with component signatures and project labels. Parity tests are kept even if the display is cut.
6. **Context (capped lookups):** CCLE/DepMap model relevance and target dependency; PRISM/GDSC viability on native scales; Perturb-CITE-seq (Frangieh 2021, one originating study) gene-level immune-evasion evidence; TISMO mouse cytokine and ICB context with frozen orthologues; the LJP4 IFNG reference only after payload verification (six breast lines, not prostate).
7. **Pharmacology** on the shortlist only: regulatory status with date (tazemetostat's 2026 US withdrawal is stated only after verification against the FDA record), human PK, unbound exposure, formulation; categories as in `revision_20261015/PHARMACOLOGY.md`.

## 6. Integration and handoff
Evidence matrix per candidate, missing evidence `UNKNOWN`; tiers A–D and a Pareto set as in `revision_20261015/EVIDENCE_INTEGRATION.md`; separate nominations (best molecular re-expression, best mechanistic, best translational, feasible pilot, control). The wet-lab handoff follows `revision_20261015/WETLAB_HANDOFF.md` and does not change the registered protocol.

## 7. Figures (4)
1. Query architecture: A/A.1/B inputs, pool filters, direction table, Q_M/Q_E matching and the balance table.
2. C-P and C-FAV: per-study δ_s, Δ_Q with interval, separate effects on S(Q_M) and S(Q_E); C-CLASS beside it; cell-line methylation strata.
3. C2/C1 context tensor and Q_M/Q_E disagreement; viability and mechanism beside re-expression.
4. Evidence tiers, Pareto set and wet-lab handoff.
Missing sources stay as labelled empty panels.

## 8. Claims
**Can claim:** in the admitted prostate DNMTi experiments, methylation-supported immune genes do (or do not) re-express more than expression-matched immune genes ("supported", "inconclusive" or "expression-only advantage"); the same for favourable genes; context-specific connectivity in LINCS; a transparent candidate evidence matrix.

**Cannot claim:** that methylation causes silencing; restoration of an established prostate deficit; drug or class superiority; immune killing; ICI synergy; clinical benefit; prostate ICI response; that a LINCS-inferred gene was measured; independent validation of B's association.

## 9. Budget (researcher-hours, C-Q12)
About 190 h:
- query release (pool, direction table, gate, matching): 15;
- source admission audit: 15;
- C-P and C-FAV engine and run: 30;
- C-CLASS: 15;
- cell-line methylation: 5;
- C2 (download, parity, run): 35;
- C1: 5;
- context lookups: 25 (DepMap/PRISM/GDSC 9, Perturb-CITE-seq 8, TISMO 8);
- pharmacology: 10;
- integration and handoff: 15;
- contingency (preprocessing of old arrays, failed admissions, review): 20.
Over-runs cut, in this order: TISMO, Perturb-CITE-seq, the C1 display (parity kept). The cell-line methylation check is never cut. The standalone-paper decision (gate 8) is taken before the C2 download.

## 10. Open gates before any perturbation outcome is read
1. B Tier 1+2 lists, B's single-cell rule and the TCGA-PRAD methylation model inputs released with hashes.
2. Hallmark IFN-gamma membership frozen (shared with A and B).
3. `c_gene_direction_table.tsv` and `c_query_release.json` (pool, Q_M, Q_E, balance, hashes).
4. Source admission audit and frozen contrast registry for DNMTi, HDACi and EZH2i studies.
5. singscore version pinned; WTCS and one-sided parity fixtures pass.
6. Compound universe and identity release.
7. LINCS2020 matrix downloaded and hashed (after gate 8).
8. Standalone-paper gate: if fewer than 3 DNMTi studies pass the audit, C-P is descriptive and C stays a thesis chapter; the standalone-paper decision is then the user's (C-Q10).
