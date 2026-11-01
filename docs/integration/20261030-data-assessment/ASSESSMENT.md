# Paper A data assessment, 30 Oct 2026: what we have, and whether raw processing is worth it

## What we have (patients with pre-treatment expression and a usable response)

| Cancer | Development cohorts | Patients | Final test |
| --- | --- | ---: | --- |
| Melanoma | Riaz 49, Hugo 26, Liu 102 (signing), Gide 73 (join check running), GSE168204 10 (clinical benefit only) | ≈ 260 | — |
| Bladder | GSE176307 89 (worksheet open since 28 Oct: baseline timing, duplicate profile, matrix-ID mapping) | (89) | IMvigor210, 298 |
| Kidney, lung, other | none | 0 | — |

Under the signed review rules (amendment rule 1), a cancer with one study gives only that study's effect, a cancer with 2–3 studies gives a tentative pooled effect, and a pan-cancer analysis needs several cancers. **Today only melanoma can be meta-analysed.** The main gap is cancer diversity, not patient count.

## Raw-read processing (nf-core): cost and gain

| Study | Raw RNA-seq | Gain | Verdict |
| --- | ---: | --- | --- |
| Kim 2018, gastric, 45 | 292 GB | One gastric study, so k = 1: reported alone, not pooled | **Later, optional.** Worth it only if a second gastric cohort appears, or for the pan-cancer breadth |
| Zhao 2019, glioblastoma, 26 + 8 on-treatment | 105 GB | k = 1 in a cancer where ICI rarely works; 8 A.1 pairs | **Low priority** |
| Gide re-processing | 824 GB | Removes a documented limitation for 73 patients who are already usable | **Not worth it now** |

Each also needs the cluster setup, an nf-core output adapter in the pipeline, per-patient response labels from paper supplements, and a worksheet. That is several days of work for k = 1 cancers.

## Cheaper ways to add cancer types (open processed data, no raw processing)

| Cohort | Cancer | Patients | Source | Gain |
| --- | --- | ---: | --- | --- |
| Braun 2020 (CheckMate) | Kidney | 281 | Supplement S4A (normalized RNA) and S1 (clinical) | Largest open cohort after IMvigor210 |
| IMmotion150, atezolizumab-only arm | Kidney | ≈ 86 | cBioPortal `rcc_iatlas_immotion150_2018` | Kidney k = 2 with Braun |
| GSE176307 | Bladder | 89 | GEO (already ingested) | Bladder development; the bladder test is then no longer purely cross-cancer |
| GSE135222, GSE136961, GSE93157 (array, lung arm) | Lung | 27 + 21 + 35 | GEO | Lung k = 2–3 |
| Van Allen 2015 | Melanoma, anti-CTLA-4 | 41 | cBioPortal | A separate drug-class stratum |

## Code status

| Code | State | Remaining |
| --- | --- | --- |
| DAV admission pipeline (`tools/a_dav`) | Real-source ingestion for GEO, author tables and cBioPortal; signed admission; final-test guard | Finish Liu/Gide (round 19); commit |
| Discovery tool (`tools/a_discovery`) | v0.1 works live (GEO, cBioPortal, ENA, nf-core samplesheet; stops on challenge pages) | Europe PMC supplement lists; live EGA check; readiness evidence |
| nf-core output adapter | Not started | Only if raw processing goes ahead on the cluster |
| Analysis (`tools/a_analysis`) | Synthetic prototype (rank and mean-z scores, AUROC) | The main remaining code: per-study DE, random-effects meta-analysis (modified Knapp–Hartung), locked-panel scoring, paired endpoint contrasts. All built and tested on synthetic data before any analysis is authorized |

## Recommendation
1. Finish Liu and Gide, then commit.
2. Add the open, cheap cohorts in this order: Braun → IMmotion150 mono arm → GSE176307 → the lung GEO sets. This gives kidney, bladder and lung development cohorts.
3. Build the analysis code on synthetic data, in parallel.
4. Decide on raw processing when the cluster arrives. Default: skip Gide re-processing; consider Kim only if the pan-cancer breadth needs it.
