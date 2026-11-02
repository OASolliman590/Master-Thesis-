# Batch sign-off under simple mode, 1 Nov 2026

The user signed in chat on 1 Nov 2026: "I sign the 9". The scope was presented immediately before that: the batch of 9 cohorts for development use, with the caveats and the three rules shown, while GSE176307 and Kim wait for their papers.

**Signed for DEVELOPMENT use** (tables in `.scratch/runtime/<c>/simple/`, made by `tools/a_cohorts`):

| Cohort | Patients | Cancer | Endpoints |
| --- | ---: | --- | --- |
| riaz_gse91061 | 49 | melanoma | ORR |
| hugo_gse78220 | 26 | melanoma | ORR |
| gse168204 | 10 | melanoma | clinical benefit (SOURCE_BINARY) |
| liu2019 | 102 | melanoma | ORR |
| gide2019 | 73 | melanoma | ORR; clinical benefit |
| braun2020 | 181 | kidney | ORR; clinical benefit (CB/ICB/NCB) |
| vanallen2015 | 40 | melanoma (anti-CTLA-4 stratum) | ORR |
| gse135222 | 27 | lung | clinical benefit (DCB/NDB) |
| gse136961 | 21 | lung (targeted panel) | clinical benefit (DCB/NDB) |

**Rules approved with this signature:**
1. **Gide:** the iAtlas log2 upper-quartile profile is used until recount3's run-to-patient crosswalk is complete (60 of 73 PRE runs link today). It has undocumented processing, is used on its own scale only, every pooled result is also reported without Gide, and it is never a final test.
2. **GSE135222:** clinical benefit comes from the coordinator-extracted Supplementary Table 3 of Jung 2019 (hash-verified PDF, page 12), joined by exact sample ID; all 27 RNA samples matched. Individual timing is unverified (a caveat).
3. **GSE136961:** DCB/NDB is read from the GEO title prefix (D/N), which gives 9/12 and matches the paper.

**Accepted limitations:** each cohort's `caveats.md`, as shown to the user, for example unknown tool versions, Braun's within-study ComBat and archival tissue, Van Allen's undocumented quantification, overlap flags and unknown prior ICI.

**Not signed (waiting for their papers):** gse176307 and kim2018. IMvigor210 remains UNTOUCHED_FINAL_TEST.

## Batch A addition (user, 1 Nov 2026: "I sign both")
Signed for DEVELOPMENT use (loaded by Luna into `.scratch/runtime/<c>/simple/`):
| Cohort | Patients | Cancer | Endpoint | Main caveats |
| --- | ---: | --- | --- | --- |
| gse218989 | 355 | lung | SOURCE_BINARY (GEO `treatment outcome`: Responder 168 / Non-responder 187). Not ORR | Biopsy timing not stated in GEO; protein-coding TPM |
| gse159067 | 102 | head and neck | ORR (GEO `best response on immunotherapy (recist)`: CR 5 / PR 6 / SD 27 / PD 64) | Targeted log2-CPM panel (2,567 genes); pre-treatment per the series design |
Not signed: gse145996 and gse165278 have no per-patient response in GEO (their papers may resolve it).

## Batch B (user, 2 Nov 2026: "I sign the four")
Signed for DEVELOPMENT use (loaded by Luna into `.scratch/runtime/<c>/simple/`; reviewed by the coordinator):
| Cohort | Patients | Cancer | Endpoint | Main caveats |
| --- | ---: | --- | --- | --- |
| gse93157 | 65 | melanoma, lung (non-squamous, squamous), head and neck; `cancer` column per patient | ORR from GEO `best.resp` (CR 3 / PR 17 / SD 16 / PD 29) | NanoString 730-gene panel; log2 HK-normalised scale inferred from the values; the contradictory GEO `response` field is ignored; 32 of 65 biopsies archival |
| gse67501 | 11 | kidney (PD-L1-positive RCC) | ORR from the CR/PR/SD/NR characteristic (CR 2 / PR 2 / SD 2 / NR 5) | Specimens predate nivolumab by months to years; probe-level with probe_to_gene map |
| gse122220 | 10 | melanoma | ORR (CR 2 / PR 2 / SD 1 / PD 5) | 2 dual ipilimumab + anti-PD-1 kept (drug class per patient); 8 had prior ipilimumab; probe-level with map |
| gse111636 | 11 | bladder (pembrolizumab) | SOURCE_BINARY (`treatment response`: responder 6 / progressor 5). Not ORR | Submitter RMA + ComBat values; probe-level with map; no linked paper |

**Not signed:** gse140901 (liver, 24) is on hold: its paper reports single-agent or combination ICI therapy and GEO gives no per-patient regimen. gse99070 is on hold (no ICI treatment shown); gse207422 is a combination study (combination paper only); the TCGA melanoma ICI subset is excluded.

## Paper-resolved addition (user, 2 Nov 2026: "I sign both")
Signed for DEVELOPMENT use after checking the user-supplied primary papers:
| Cohort | Patients | Cancer | Endpoint | Main caveats |
| --- | ---: | --- | --- | --- |
| gse176307 | 88 | bladder (urothelial) | ORR, RECIST 1.1 by a blinded radiologist (CR 7 / PR 9 / SD 4 / PD 67 / unknown 1) | Rose 2021: deaths or clear clinical progression before imaging count as non-responders; single-agent anti-PD-1/PD-L1; archival FFPE, interval to ICB not stated; log2(1+x) median-centred upper-quartile values; GEO has 16,383 genes and 88 patients vs 16,901 and 89 in the paper |
| kim2018 | 45 | gastric | ORR, RECIST 1.1 (CR 3 / PR 9 / SD 15 / PD 18) | Kim 2018 Table 2, coordinator-extracted from the hash-verified PDF and joined exactly by sequencing ID (45/45); pembrolizumab monotherapy, ICI-naive, fresh-frozen biopsy within 42 days before treatment; recount3 approximate counts |
