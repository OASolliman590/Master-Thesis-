# Immunotherapy combinations are set aside for a separate paper (29 Oct 2026)

**Status:** decided by the user in chat on 29 Oct 2026. This applies to Paper A and Paper B. The frozen specs are unchanged; this is a cohort-selection rule.

**Rule.** If immunotherapy was given together with a non-immunotherapy agent, that study (or arm) is excluded from Papers A and B. Such agents include chemotherapy, targeted therapy or TKIs, anti-VEGF, HDAC or hypomethylating agents, ADT, and radiotherapy given as part of the regimen. Excluded studies are kept, not deleted, in this registry for a later paper on combination effects. Any ingested data, field maps and signed worksheets stay in place.

**Answers (user, 29 Oct 2026):**
- **Dual checkpoint stays in A/B.** Regimens that combine only checkpoint inhibitors (for example anti-PD-1 + anti-CTLA-4) are not "combination" for this rule. They stay in A/B, tagged per patient by drug class, and are never pooled silently with monotherapy.
- **Mixed studies are kept.** When a study has both an immunotherapy-only arm and an immunotherapy + non-ICI arm:
  - the immunotherapy-only arm feeds the A/B analyses;
  - the combination arm is kept and compared with the immunotherapy-only arm within the same study (differential expression);
  - that difference is then related to TCGA and epigenetics, to ask how the combination improves on immunotherapy.
  - Within-study arm comparisons are causal only when the arms were randomised (for example IMmotion150). Otherwise they are descriptive.
- Studies whose patients all received a combination (no immunotherapy-only arm) are excluded from A/B and saved in the registry below for the combination paper.

**Follow-ups (user, 29 Oct 2026):**
- **GSE248014: epigenetic-drug effect.** GEO has 23 Baseline biopsies, 18 C1D1 biopsies (after the 14-day entinostat-only lead-in, before nivolumab) and 4 C2D1 biopsies (after 6 weeks of entinostat + nivolumab). Baseline vs C1D1 isolates the HDAC inhibitor's effect on the 11 panels before any checkpoint drug. It is paired, within-patient and needs no new download, because all 45 columns are in the RSEM table already held. Similar epigenetic-drug + ICI cohorts are being searched for, to replicate it; results will go in `docs/research/ICI_COHORT_SEARCH_EXPANDED_20261028.md`.
- **Dual-checkpoint subgroup.** Patients on dual checkpoint therapy are also analysed as their own subgroup. In GSE168204 that is only 2 patients, so they are shown descriptively (per-patient panel scores) and not tested statistically. The tested dual-ICI subgroup pools dual-ICI patients across cohorts by meta-analysis (for example GSE224450, Gide 2019's combination arm, Helmink if access allows).

## Combination registry
| Cohort | Cancer | Regimen | Status before this rule |
| --- | --- | --- | --- |
| GSE248014 | PDAC | entinostat (HDAC inhibitor) lead-in, then entinostat + nivolumab | Signed 29 Oct, in admission; now **excluded from A/B** |
| GSE211645 (NIBIT-M4) | Melanoma | ipilimumab + guadecitabine | Candidate |
| GSE241876 | TNBC | pembrolizumab + carboplatin + nab-paclitaxel | Candidate |
| GSE235919 | RAS-mutant CRC | anti-PD-L1 + anti-CTLA-4 + chemo | Candidate |
| GSE345048 | Inflammatory breast | anti-PD-L1 + chemo or other | Candidate |
| GSE248514 (DREAM) | Mesothelioma | durvalumab + chemo | Candidate |
| GSE285963 | HCC | atezolizumab + bevacizumab | Candidate |
| GSE213065 | Soft-tissue sarcoma | PD-1 + CTLA-4 ± chemo ± cryotherapy | Candidate |
| GSE319641 (NeoTRIP) | TNBC | atezolizumab + chemo vs chemo | Candidate |
| GSE273798 | Small-cell bladder/prostate | PD-1 + cisplatin | Candidate (B) |
| GSE227666 | Ovarian | chemo ± pembrolizumab | Candidate (B) |
| GSE271757 | Ovarian | PD-1 + chemo | Candidate (B) |
| GSE266919 | TNBC | PD-L1 + chemo | Set aside already |
| GSE165252 (PERFECT) | Esophageal | chemoradiation + atezolizumab | Candidate |
| GSE77910 | Prostate, localized | ipilimumab + leuprolide (ADT) | Candidate (B) |
| cBioPortal `paad_iatlas_prince_2022` | PDAC | chemo ± nivolumab | Mixed study: check for an immunotherapy-only arm (chemo-only arm is not an ICI arm) |
| cBioPortal `rcc_iatlas_immotion150_2018` | RCC | atezolizumab ± bevacizumab (sunitinib arm dropped) | Mixed study: atezolizumab-only arm → A/B; + bevacizumab arm → within-study comparison (randomised) |
| GSE343570 | NSCLC, first line | **Randomised** pembrolizumab alone vs pembrolizumab + vorinostat | Mixed study (search 29 Oct, section 5): pembrolizumab-only arm → A/B candidate; vorinostat arm → within-study comparison (randomised) |
| GSE188249 / GSE186825 | Ovarian, platinum-resistant | guadecitabine + pembrolizumab (RNA + EPIC methylation) | Combination paper (R2) |
| GSE222932 / GSE222933 | Urothelial, post-ICI | guadecitabine + atezolizumab (RNA + EPIC methylation) | Combination paper (R2) |
| GSE147537 (METADUR) | CRC / breast / ovarian | CC-486 + durvalumab (methylation only) | Combination paper (R2) |
