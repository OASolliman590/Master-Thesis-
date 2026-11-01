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
