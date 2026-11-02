# Paper B: rethought specification v2, 3 Nov 2026

**Status: DRAFT v2 for debate review and signature.** It is the result of the user's request to rethink Paper B (2-3 Nov 2026) and of a grilling session whose decisions (Q1-Q21) are recorded below. It is informed by the evidence review `docs/research/SPEC_REVISION_EVIDENCE_20261102.md`.
- **Replaces** the earlier Paper B primary: B-P, 8 antigen-presentation genes, Delta R² TCGA-PRAD → CPC-GENE. B-P becomes a named sub-result.
- **Absorbs** the signed B-ICIM (`specs/amendments/2026-11-02-paper-b-ici-methylation/AMENDMENT.md`) and B-V (29 Oct) as supporting analyses.
- **Unchanged** older contracts in `specs/B/` keep their technical detail (probe masks, specimen policy, CPC-GENE linkage) unless this document says otherwise.

## 1. Question (Q1)
**How much of prostate cancer's immune-cold state is associated with DNA methylation of immune and immunotherapy-target genes, and does the same methylation–expression pattern appear in other cancers and in tumours treated with ICI?**

It is anchored in prostate. It links to the thesis rationale, epigenetic priming to sensitise prostate cancer to immunotherapy.

## 2. Role of each data source (Q2, Q4, Q10)
| Source | Role |
| --- | --- |
| **TCGA (treatment-naive multi-omics reference)** | The only public resource with matched methylation, expression, copy number, miRNA and protein across many cancers. Not an "anchor cohort": it is the naive reference that makes association and multi-omics analysis possible |
| **TCGA-PRAD** | Discovery set for the prostate primary (about 497 cases with matched RNA and 450K methylation) |
| **CPC-GENE** (GSE107298 methylation, GSE107299 expression arrays) | The single independent prostate test, used once; about 72-114 usable patients after specimen linkage |
| **TCGA comparator cancers** (SKCM, LUAD, LUSC, KIRC, BLCA, HNSC, STAD, LIHC: those of Paper A's cohorts) | Cross-cancer comparison ("cold versus hot") |
| **ICI-treated paired cohorts** (Jung GSE119144/GSE135222, Cho GSE126043/GSE126044, Krakow GSE264158/GSE213145; about 56 paired patients) | Supporting only (B-ICIM), never primary |
| **Epigenetic-drug + ICI cohorts** (GSE248014 entinostat lead-in, guadecitabine studies, GSE343570) | Supporting perturbation evidence (B-V) |
| **Prostate single-cell references** (CELLxGENE hormone-naive atlas, 24 donors; Lin atlas PCa_Hawley, labelled anti-PD-1 + ADT; PCCAT candidate) | Cellular context for interpretation |

## 3. Gene universe (Q3, Q17), frozen before any association is examined
| Tier | Content | Size | Role |
| --- | --- | ---: | --- |
| 1 | The 11 locked panels (P_ANTIGEN_PRESENTATION, AYERS_GEP_18, HALLMARK_IFNG with frozen membership, HOPE_18, M0-M6), M5 and M6 genes individually | 250-300 | Main family |
| 2 | Immunotherapy targets: CRI immuno-oncology landscape export reconciled with IUPHAR/BPS, approval from dated FDA/EMA labels; always PDCD1, CD274, CTLA4, LAG3, HAVCR2, TIGIT; co-stimulatory targets audited | 100-300 | Main family |
| 3 | Wider immune biology: ImmPort, TISIDB immunomodulators, a fixed signature whitelist | 2,000-3,000 | Discovery |
- Literal lists, releases, hashes and an evidence cutoff are frozen first, independently of Paper A's results. Paper A's frozen top genes are added later as a separately labelled set.
- **Excluded:** GO "immune" descendants, ImmuneSigDB unions, network neighbours, and any gene chosen because it was significant in an ICI study.

## 4. Measurement (Q8, Q18)
- **Methylation:** beta values. TCGA as released by GDC (SeSAMe). CPC-GENE and the ICI cohorts processed from IDAT with one pinned SeSAMe pipeline where raw files exist.
- **Probes:** the B rule (promoter annotation, cross-reactive and polymorphic mask, at least 95% finite in TCGA training, at least 80% coverage of the fixed eligible set), **restricted to probes common to 450K and EPIC**.
- **Promoter aggregate per gene:** mean beta over eligible probes. Probe counts are reported, single-probe genes flagged, and the most negative promoter is never chosen.
- **Enhancer and gene-body aggregates (secondary):** mapped by one frozen annotation (ENCODE cCRE / GeneHancer), the same rules.
- **Expression:** TCGA STAR counts → log2(TPM+1); CPC-GENE author-processed arrays on their own scale. The out-of-sample test uses per-gene standardisation within each cohort, so array and RNA-seq scales are not mixed.
- **Global methylation:** mean beta of the published solo-WCGW partially-methylated-domain probe set on the 450K–EPIC common array (frozen list), the measure of global hypomethylation that Jung 2019 showed matters.
- **Purity:**
  - a non-RNA estimate: TCGA ABSOLUTE (or the documented methylation-based estimate where ABSOLUTE is missing); CPC-GENE Qpure (available for about 112/114 candidates).
  - The CPC-GENE portal "WGS purity" field is quarantined (it is SNP-call agreement, not purity).
- **Copy number:** gene-level GISTIC2 in TCGA. **Gate:** CPC-GENE gene-level copy number is not yet established.
  - If it cannot be verified before the freeze, the primary model uses purity and global methylation only.
  - Copy number then becomes a TCGA-only sensitivity, and the primary is described as not adjusted for copy number.

## 5. Primary (Q7, Q9, Q14)
- **Estimand:** for each Tier 1+2 gene g, the out-of-sample gain in explained variance of g's expression from adding its promoter-methylation aggregate to a baseline model with purity, copy number (subject to the gate in section 4) and global methylation.
  - Model: expression_g ~ baseline + promoter_methylation_g (linear).
  - It is fitted in TCGA-PRAD and evaluated once in CPC-GENE: ΔR²_g = (SSE_baseline − SSE_extended) / SST in CPC-GENE.
- **Summary:** the median ΔR²_g across the Tier 1+2 family, with a patient bootstrap 95% interval (2,000 resamples, frozen seed). **"Association supported" only if the lower bound is above 0.**
- **Per gene:** ΔR²_g and the sign and size of the methylation coefficient, with BH FDR 5% across the tier family. The direction expected in advance is negative for promoter methylation, and positive associations are reported as such.
- **Named sub-result:** the 8 APM genes (the former B-P), reported as a pre-specified panel within the primary.
- **Pre-specified sensitivity (Q19):** the same models with MethylCIBERSORT cell fractions added (frozen reference; probes overlapping tested promoters removed from the deconvolution signature). The primary stays as frozen.

## 6. Secondaries
1. **Cold versus hot across TCGA (Q11, Q15), the main secondary:**
   - the same per-gene models within each TCGA cancer, with 5-fold cross-validated ΔR²;
   - prostate compared with each comparator cancer as a difference in median ΔR² with bootstrap intervals;
   - descriptive, with no pass/fail threshold; cancer types differ in many ways besides immunity.
2. **Enhancer and gene-body methylation (Q8):** the primary design with enhancer or gene-body aggregates.
3. **Multi-omics integration (Q12, Q16), exploratory:**
   - MOFA+ unsupervised, per cancer and pan-cancer, on RNA, methylation, copy number, and miRNA and RPPA where coverage allows.
   - DIABLO only with non-RNA labels: Gleason grade group in prostate, cancer type pan-cancer. No RNA-derived immune subtype labels (circular).
4. **Cell composition and methylation state (Q20, Q21):** quanTIseq (default; CIBERSORTx if the user obtains access) cell fractions related to each tumour's immune-gene methylation state, descriptively. RNA-derived fractions are never used as covariates for RNA outcomes. This runs in TCGA-PRAD, CPC-GENE, the comparator cancers and the ICI cohorts with the same frozen reference.
5. **Prostate transfer of Paper A's frozen panels:** TCGA-PRAD scored with Paper A's frozen programmes; "low" is relative to other prostate tumours. Low RNA is not HLA loss.
6. **B-ICIM (supporting):** the outcome-free immune-gene methylation–expression association in ICI-treated tumours, as signed, **with one change covered by this v2 signature: global methylation is added to the B-ICIM adjustment set** (from the Q9 decision, since Jung 2019 showed global hypomethylation drives immune-gene repression in this very cohort). Jung first (27 pairs); Cho and Krakow deferred. It is compared with Jung 2019 and Hossain 2025, which already reported methylation findings in these cohorts.
7. **B-V (supporting perturbation evidence):** change in pre-declared immune scores after an epigenetic drug, as signed on 29 Oct. Only GSE248014's lead-in isolates the drug alone, HDAC inhibitors are not assumed to demethylate DNA, and Holm correction applies.

## 7. Claim ceiling (Q13)
**Permitted:** "Paper B provides epigenetic evidence that promoter methylation of immune and immunotherapy-target genes is associated with their reduced expression in untreated prostate cancer. The association holds after adjustment for purity, copy number (if available) and global methylation, is replicated in an independent cohort, and is consistent with an epigenetically repressed immune state. **Only if the pre-specified MethylCIBERSORT sensitivity does not materially attenuate it** may the claim add "and is robust to methylation-estimated cell composition"; otherwise the attenuation is reported. Perturbation evidence from epigenetic-drug cohorts is reported where available."

**Not permitted:**
- "methylation silences", "causes" or "controls";
- any prediction of ICI response in prostate;
- any claim of drug reversibility beyond what B-V's design supports.

Signed rule 7 wording ("association supported", "inconclusive", "not measured") applies to every result.

## 8. Budget (Q6)
About 180 researcher-hours:
- gene universe and measurement freeze: 25;
- primary: 45;
- cold versus hot: 30;
- multi-omics: 30;
- deconvolution: 15;
- B-ICIM: 20 (stop-loss);
- B-V: 15.
Over-runs cut the exploratory items first, in this order: multi-omics, then deconvolution.

## 9. Open gates before any association is examined
1. Freeze the Tier 1-3 gene lists and the Hallmark IFN-gamma membership.
2. CPC-GENE gene-level copy number: verify, or apply the fallback in section 4.
3. CPC-GENE specimen and patient linkage (the 73/114 issue in `specs/B/DATA_AND_SOURCES.md`).
4. Freeze the probe sets, global-methylation probe list, purity sources and MethylCIBERSORT reference.
5. TCGA comparator cohort sizes with matched RNA and methylation (to be counted from GDC metadata).
6. Correct the PCa_Hawley label in the single-cell plan to "anti-PD-1 + ADT" once confirmed against Hawley 2023.
