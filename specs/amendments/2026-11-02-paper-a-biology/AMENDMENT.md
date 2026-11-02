# Paper A biology (A-BIO) settings, 2 Nov 2026

**Status: DECIDED by the user on 2 Nov 2026 ("Yes, both", adopting the coordinator's recommendations for D4 to D6).** It fills in settings left open by `specs/A/BASELINE_BIOLOGICAL_ANALYSIS.md` and the 29 Oct integrated plan; their rules are unchanged (per-study estimation, compatible-context synthesis, REML with modified Knapp–Hartung, never mixing effect types, retaining null and contradictory results). It authorises no analysis by itself.

## D4. Locked-panel effects
- **Effect measure:** Hedges g (small-sample-corrected standardised mean difference) of the panel score, responders minus non-responders, within each study and endpoint.
- **Score:** the frozen panel definition computed on each study's own log-scale expression. A study enters a panel only with complete coverage of its genes (after the frozen alias table). Individual M5 genes and M6 regulators are analysed separately as well as in composites.
- **Synthesis:** per cancer first, then across cancers. Combinations follow the signed rules: 1 study is reported alone; 2-3 studies are combined tentatively with modified Knapp–Hartung and no prediction interval; patient numbers never replace study numbers. The cross-cancer summary states its weighting explicitly.
- Hedges g is the declared cross-platform measure for panels, so arrays, NanoString panels and RNA-seq can contribute. It is not used for genome-wide gene effects (D6).

## D5. Endpoint families (never pooled across families)
1. **ORR** (CR/PR vs SD/PD, RECIST or the source's stated criteria): the main family.
2. **Clinical benefit:** each definition is tagged and kept separate, for example SD ≥ 6 months (Rose), DCB/NDB (GSE135222, GSE136961), PFS > 24 weeks (Nathanson for GSE165278), and source "clinical benefit" fields (GSE140901).
3. **Source-defined binary labels** without a stated clinical definition (GSE218989 "treatment outcome", GSE111636 responder/progressor, GSE168204): reported per study only, never combined.
Unknown response is never counted as non-response.

## D6. Genome-wide differential expression (discovery only)
- **Integer counts** (recount3 cohorts, GSE168204 featureCounts): negative-binomial GLM (DESeq2 or edgeR, chosen once and recorded), library offset, unshrunk log2 fold change with its SE.
- **Log-scale or array data** (TPM/FPKM/log CPM cohorts, Illumina and Affymetrix arrays): limma on the source log scale, with the moderated t.
- **Synthesis only within an effect type:** NB log fold changes with NB, limma mean differences with limma. Cross-type summaries, if any, are a separately labelled sensitivity.
- **Multiplicity:** Benjamini–Hochberg FDR 10% within each declared synthesis family. Full tables with unadjusted p-values are kept.
- Targeted panels (NanoString, Oncomine) are excluded from genome-wide synthesis; they contribute to D4 only.
- Genome-wide lists never feed the A-P2 learner (signed rule 3 of 29 Oct).
