R/NR DEFINITION FOUND: R = CR or PR; NR = PD by RECIST (no time threshold stated) ([Auslander et al., Methods, “Clinical response classification,” Table 1](https://pmc.ncbi.nlm.nih.gov/articles/PMC6693632/)).
TITLE-TO-PATIENT MAPPING AMBIGUOUS: GEO titles do not encode patient IDs; the `patient id` characteristic supplies the sample-to-patient mapping, and multiple baseline samples share patients. [GEO family SOFT](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE115nnn/GSE115821/soft/GSE115821_family.soft.gz)

# GSE115821 source review

## Response definition and endpoint source

The paper’s Table 1, “Response annotations for each melanoma dataset,” has a column headed “MGH dataset.” It lists response as **“‘CR’, ‘PR’”**, non-response as **“’PD’”**, and protocol as **“RECIST”**. The Methods section “Clinical response classification” introduces this table as the response annotations and criteria used in the original study. The MGH column does not give a RECIST version or a time threshold. The paper says patient-level classifications for the MGH dataset are described in Supplementary Table 9. Thus the mapped endpoint is `SOURCE_BINARY`, with the author’s MGH patient classifications as the source of record and GEO’s sample-level `response` characteristic as corroboration. [Original article, Methods / Clinical response classification / Table 1](https://pmc.ncbi.nlm.nih.gov/articles/PMC6693632/) · [Supplementary Table 9 is cited by the article as the MGH clinical information source](https://pmc.ncbi.nlm.nih.gov/articles/PMC6693632/#supplementary-materials) · [GEO family SOFT](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE115nnn/GSE115821/soft/GSE115821_family.soft.gz)

The source definition only supplies `CR`/`PR` and `PD` categories. It does not state how any other response category would be handled; none is inferred in the field map. RECIST version and response-assessment time threshold remain UNKNOWN.

## Title and patient mapping

The GEO `patient id` characteristic is populated for the sample records and gives the sample-to-patient link. GEO sample titles themselves are file/sample names, not patient IDs or a reliable patient/timepoint parser. The baseline inventory has 14 pre-ICI records but fewer distinct patients; several baseline records share a patient ID. Therefore there is not a one-to-one title-to-patient or baseline-sample-to-unique-patient mapping. [GEO family SOFT](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE115nnn/GSE115821/soft/GSE115821_family.soft.gz)

## Selected source objects

- **`geo_family_soft` — GEO family SOFT, 4,376 bytes, listing timestamp 2026-08-26.** Chosen for sample inventory, patient/timepoint/tissue/treatment/response characteristics and GEO data-processing text. It carries the `patient id`, `treatment state`, `timepoint`, `response`, `antibody`, and `tumor type` characteristics. [SOFT object](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE115nnn/GSE115821/soft/GSE115821_family.soft.gz) · [soft directory listing](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE115nnn/GSE115821/soft/)
- **`geo_featurecounts_hg19` — GEO supplementary expression object, 6,063,556 bytes (directory display: 5.8M).** Chosen as the expression object because GEO processing describes featureCounts v1.5.1 summary read counts and identifies build hg19. The transform and gene-ID type are not specified in that processing text, so they remain UNKNOWN. [Expression object](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE115nnn/GSE115821/suppl/GSE115821_MGH_counts.csv.gz) · [supplementary directory listing](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE115nnn/GSE115821/suppl/)

The two selected GEO objects total 6,067,932 bytes, below the 500 MB cohort cap. Their SHA-256 values remain null because full object bytes were not retrieved for hashing.

## Other source findings

- GEO describes 37 total sample records across 8 distinct patient IDs. Repeated patient/timepoint profiles mean sample counts are not independent-patient counts. [GSE115821 GEO record](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE115821) · [GEO family SOFT](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE115nnn/GSE115821/soft/GSE115821_family.soft.gz)
- Fourteen records are labeled pre-ICI: 11 `PRE Immune Checkpoint Blockade Therapy` and 3 `PRE Immune Checkpoint Blockade Therapy (On dabrafenib+trametinib)`. The latter are pre-ICI but carry concurrent targeted-treatment context. There are 23 records labeled on ICI. [GEO family SOFT](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE115nnn/GSE115821/soft/GSE115821_family.soft.gz)
- GEO identifies metastatic melanoma as the sample source and tissue context. The paper describes metastatic melanoma patients with tumor specimens. [GEO record](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE115821) · [Original article](https://pmc.ncbi.nlm.nih.gov/articles/PMC6693632/)
- GEO lists anti-PD-1, anti-CTLA-4, and combined anti-PD-1 plus anti-CTLA-4. The paper states the MGH cohort was enrolled in clinical trials and lists NCT01714739, NCT02083484, NCT01543698, NCT01072175, NCT00949702, NCT01783938, and NCT01006980; it does not link each patient to a trial or identify exact drug names. Prior immunotherapy status remains UNKNOWN. [GEO family SOFT](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE115nnn/GSE115821/soft/GSE115821_family.soft.gz) · [Original article, Methods / RNA-seq](https://pmc.ncbi.nlm.nih.gov/articles/PMC6693632/)
- GEO data processing names featureCounts v1.5.1, summary read counts and hg19; the deposited supplementary CSV is selected. Transform and gene-ID system are UNKNOWN because neither is stated in GEO processing text or the paper. [GEO family SOFT](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE115nnn/GSE115821/soft/GSE115821_family.soft.gz) · [GEO supplementary listing](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE115nnn/GSE115821/suppl/)
- The GEO matrix directory has platform-specific sample annotation matrices (3.0K and 2.8K). The checked NCBI RNA-seq counts listing for GSE115nnn has no GSE115821 entry. [GEO matrix listing](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE115nnn/GSE115821/matrix/) · [NCBI RNA-seq counts listing](https://ftp.ncbi.nlm.nih.gov/geo/rnaseq_counts/GSE115nnn/)
- The author’s `noamaus/IMPRES-codes` repository was checked. Its commit is pinned to `5ae40ca4dc117c0ae9d7160f381146aeeb455a49`, obtained from the GitHub commits API; no alternate R/NR definition was identified there. [GitHub repository](https://github.com/noamaus/IMPRES-codes) · [GitHub API commit](https://api.github.com/repos/noamaus/IMPRES-codes/commits/5ae40ca4dc117c0ae9d7160f381146aeeb455a49)
- cBioPortal was considered as a cross-check only and was not used to define or overwrite the response. [cBioPortal datahub](https://github.com/cBioPortal/datahub)

## Open questions

- What RECIST version and response-assessment time threshold, if any, apply specifically to the MGH cohort? Neither is specified for that column in the original paper.
- Which of the seven listed clinical trials applies to each patient, and what exact drug names correspond to the GEO antibody classes?
- Which patients had prior immune-checkpoint or other systemic therapy?
- What exact transform/scale and gene identifier system are used in the deposited featureCounts matrix?
- Which of the 14 pre-ICI records should be retained as unique baseline specimens after duplicate-profile and patient/timepoint review?
