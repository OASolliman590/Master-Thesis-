# Guo-lab index cross-check (ICBatlas, ICBcomb, ICBcDrug), 30 Oct 2026

**Source:** the user's own parse of the three Guo-lab resources, kept outside this repo. The ICBatlas tables come from the paper's Figshare supplementary tables S1–S4 (Yang et al., Cancer Immunol Res 2022). The ICBcomb catalogue was read from the site's front-end bundle. The ICBcDrug tables come partly from the Nature Immunology 2024 supplement and partly from the site.

**Use:** a study-level index and cross-check only, never a source of record. Cohort data still come from the original GEO, author or cBioPortal objects through the pipeline. Only the published supplementary tables are cited; content obtained from the sites themselves is not redistributed.

## ICBatlas pre-treatment roster (33 cohorts, 1,361 patients) against the pipeline

| ICBatlas study | Cancer | Regimen | Labelled patients | Pipeline status |
| --- | --- | --- | ---: | --- |
| SRP094781 (Riaz) | Melanoma | anti-PD-1 | 49 | Admitted |
| SRP070710 (Hugo) | Melanoma | anti-PD-1 | 27 | Admitted (26) |
| SRP011540 anti-PD-1, PMID 31792460 (**Liu 2019**) | Melanoma | anti-PD-1 | 120 | Worksheet (our `liu2019`) |
| ERP105482 (Gide) | Melanoma | anti-PD-1; + anti-CTLA-4 | 41 + 32 | Worksheet |
| IMvigor210 | Urothelial | anti-PD-L1 | 298 | Final test (locked) |
| GSE176307 | Urothelial | anti-PD-1 | 89 | Worksheet open |
| SRP150548 (GSE115821) | Melanoma | mixed | 14 | Parked |
| SRP183455 (GSE126044) | NSCLC | anti-PD-1 | 16 | Parked |
| SRP011540 anti-CTLA-4 (Van Allen) | Melanoma | anti-CTLA-4 | 41 | Not started (cBioPortal open processed) |
| PMID 32472114 (**Braun 2020**) | RCC | anti-PD-1 | 281 | **Not started**: open supplement S4A, high value |
| SRP217040 (GSE135222) | NSCLC | anti-PD-L1 | 27 | Not started |
| GSE136961 | NSCLC | anti-PD-1 | 21 | Not started |
| SRP250849 (GSE145996) | Melanoma | anti-PD-1 | 14 | Not started |
| SRP302761 (GSE165278) | Melanoma | anti-CTLA-4 | 7 | Not started (A.1 interest) |
| GSE93157 | HNSCC / melanoma / NSCLC | anti-PD-1 | 5 / 25 / 35 | Not started (array) |
| GSE67501 | RCC | anti-PD-1 | 11 | Not started (array) |
| GSE99070 | Mesothelioma | anti-PD-1 | 10 | Not started (array) |
| GSE122220 | Melanoma | anti-PD-1 | 8 | Not started (array) |
| GSE140901 | HCC | anti-PD-1; + anti-CTLA-4 | 13 + 9 | Not started (array) |
| GSE111636 | Urothelial | anti-PD-1 | 11 | Not started (array) |
| PMID 33806963 | RCC | anti-PD-1 | 13 | Not started (supplement S10) |
| SRP128156 (Miao) | RCC | anti-PD-1; + anti-CTLA-4 | 29 + 4 | Controlled (dbGaP) |
| SRP230414 (phs001919) | Melanoma | anti-PD-1 | 27 | Controlled (dbGaP); **not** our Liu |
| SRP155030 (Zhao) | GBM | anti-PD-1 | 26 | Raw reads only |
| ERP107734 (Kim) | Gastric | anti-PD-1 | 45 | Raw reads only |
| TCGA melanoma | Melanoma | anti-CTLA-4 | 13 | TCGA subset; for Paper B context |

**Coverage:** about 656 of 1,361 ICBatlas patients are admitted, in a worksheet, or locked as the final test, if GSE176307 is counted.

**Corrections from this check:**
- ICBatlas's "Liu" is SRP011540 / PMID 31792460, which is our `liu2019`. SRP230414 is a different, controlled UCLA study. Nothing is double-counted.
- The IMvigor210 row in the parse lists NR 68 / R 230. Our cBioPortal counts give CR + PR = 68, so R and NR are swapped in the parse or in the source.

## ICBcomb (combination therapy expression)
Its 10 human datasets are small experimental sets (cell or tissue models, 5–26 samples), not ICI-treated patient cohorts. Examples: E-MTAB-11058 (uveal melanoma, entinostat or JQ1), GSE158164 (CRC, CXD101, an HDAC inhibitor), GSE148476 (CLL, avadomide). They are preclinical context for Paper C and B-V at most, not patient validation. The other 66 datasets are mouse.

## ICBcDrug (predicted ICB-sensitising drugs)
536 compounds have CM-scores from LINCS perturbations, with vorinostat among the evaluated compounds. This is relevant to Paper C as an independent prior ranking to compare against. It is not used as evidence in Papers A/B.
