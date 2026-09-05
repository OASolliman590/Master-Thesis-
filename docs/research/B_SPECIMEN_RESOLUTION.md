# Paper B: CPC-GENE specimen and cellularity source resolution

Checked 6 September 2026 (Cairo). Bounded metadata research only; no endpoint choice, omics association, production model, canonical edit, or final analytic sample count.

**The audit provides stronger technical-replicate provenance for 300 methylation assays and an original-study linkage route for 73 patients. It does not establish specimen identity for all 210 candidate patient pairs. It also identifies a material error in the previously used portal purity field: its 130 CPCG values reproduce an assay-concordance column, not tumour purity.** E3/E4 therefore remain open, with a much more concrete source-backed policy available for review.

## 1. Critical correction: the portal field cannot be used as WGS purity

The cached cBioPortal `prad_cpcg_2017` sample metadata calls `WGS_BASED_PURITY_ESTIMATION` “WGS Based Purity Estimation.” I compared every CPCG record containing that field against the original Fraser Supplementary Table 1, joined on its complete `SampleID`.

- 130 portal CPCG records have the field; all 130 have an original-table comparator.
- **130/130 match the original `WGSvsOS accuracy` column within absolute tolerance 1e-8; none differ.**
- The original supplementary PDF, printed page 3, Table 1 legend, defines this column as agreement between SNP calls from WGS and OncoScan. That is an assay concordance measure.

The source definition plus complete numerical correspondence strongly supports a portal annotation/import error. No publisher or portal maintainer has confirmed its cause. The direct operational conclusion is narrower and firm: **quarantine this field from purity adjustment and correct the earlier readiness statement that 73 paired patients had verified WGS purity.** The earlier cache remains unmodified for traceability. [Fraser supplementary definitions](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fnature20788/MediaObjects/41586_2017_BFnature20788_MOESM323_ESM.pdf)

Reproduction: `finish_metadata_audit.py`; result: `purity_label_audit.json`. This compared metadata fields only, without using clinical outcomes or expression/methylation measurements.

## 2. What methylation “rep” means where independently documented

Shiah et al. explicitly studied technical replication of 450K measurements. Section 2.1 describes 202 unique samples generating 310 measurements: 114 singletons, 71 duplicates, 14 triplicates and three quadruplicates, distributed across six batches and 28 slides. Supplementary Table S1 supplies `Sample ID`, `Replicate`, `Sample Batch`, `Array`, and `Slide`; sections 2.6 and 3.2 explicitly discuss technical replicates. [Shiah et al., Bioinformatics 2017, DOI 10.1093/bioinformatics/btx372](https://academic.oup.com/bioinformatics/article/33/20/3151/3866477)

I joined this physical slide/array identifier to the IDAT filenames in cached GSE107298 sample metadata, requiring the CPCG patient code to agree. This is new physical-assay corroboration; the previously resolved 300 GEO reanalysis edges were not re-audited.

| Metadata check | Confirmed result |
|---|---:|
| Original Shiah assay rows / unique codes | 310 / 202 |
| Duplicate physical slide–array keys in that table | 0 |
| Current GSE107298 records matching physical barcode and patient | 300 of 394 |
| Barcode matches with a conflicting patient code | 0 |
| Current records without this provenance | 94 |
| Among 210 candidate RNA–methylation codes: all current assays documented | 119 |
| No current assays documented / partially documented | 90 / 1 |

There is one renamed replicate: current `GSM2864003`, `CPCG0184_rep2`, uses physical barcode `3998579082_R01C02`, which Table S1 labels `CPCG0184`, `rep4`, batch 6. Selecting by a `rep1`/`rep2` suffix alone is therefore unsafe. The partially documented patient is `CPCG0423`: two of four current assays match Table S1.

**Established:** the 300 barcode-matched assays belong to the source's technical-replication experiment. **Not established:** whether every one of the remaining 94 assays is technical replication, a new extraction, or a distinct sampled region; nor whether every expanded RNA sample was taken from the same lesion as its methylation sample. A technical-replicate classification is not itself an RNA–DNA focus bridge.

Row-level evidence is in `methylation_replicate_source_links.tsv`. It retains each current GSM, patient code, physical barcode, current/source replicate names and source batch, including unresolved rows.

## 3. Original-study RNA, DNA and clinical specimen bridge

Fraser et al. describe RNA obtained from alternating adjacent sections; their Extended Data Figure 1 distinguishes prostatectomy index-lesion samples from radiotherapy index-lesion biopsies. Their methylation analysis averages technical-replicate intensities. These support paired sampling of an index lesion at the study-method level, not an assertion that different assays measured identical cells or the same aliquot. [Fraser et al., Nature 2017, DOI 10.1038/nature20788](https://www.nature.com/articles/nature20788), Methods “mRNA microarray data generation,” “Methylation microarray data analysis,” and Extended Data Figure 1; [public author manuscript](https://ebms.nci.nih.gov/sites/ebms.nci.nih.gov/files/Fraser%20Nature%202017%2028068672.pdf), PDF pages 7, 8 and 12.

The original clinical table has 284 unique IDs, each ending literally `-F1`. Exactly 73 rows have `mRNA included=Yes`; their stripped CPCG codes exactly equal the 73 old GSE84042 expression codes. Those same 73 have `Methylation Included=Yes` and `WGS Included=Yes`, are present among the current 210 candidate pairs, and have all their current methylation assays independently represented in Shiah S1. [Original clinical table bundle](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fnature20788/MediaObjects/41586_2017_BFnature20788_MOESM324_ESM.zip), member `Supplementary Table 01 - Clinical Data.xlsx`.

This creates a deterministic **source-supported original-study bridge**: exact CPCG code → literal original clinical `CPCG####-F1` ID → three source assay-inclusion flags, backed by the adjacent-section/index-lesion protocol and physical methylation-assay provenance. It is stronger than matching a patient code alone. **It is still not an individual RNA aliquot → DNA aliquot → focus manifest.** The inspected records do not explicitly decode `F1` or provide section-level identifiers for each current assay; the method text should not be promoted to per-record certainty.

Another 41 of the 210 codes match an original clinical ID, making **114 candidate clinical bridges**. Those 41 lack the original-study three-assay inclusion evidence; the later expanded RNA/methylation specimens cannot be assumed to be the original clinical specimen. The other 96 codes do not match this table.

Sinha et al. provide additional primary methods support for multiomics generated from adjacent serial sections of the index lesion, with macrodissection and a genomic purity check. Their proteogenomic study concerns a selected 76-patient cohort, including 72 methylomes. These methods cannot establish the same-focus provenance of every sample in the larger GEO deposits. [Sinha et al., Cancer Cell 2019, DOI 10.1016/j.ccell.2019.02.005](https://doi.org/10.1016/j.ccell.2019.02.005), STAR Methods “Selection of Patient Cohort and Tumor Sections” and methylation data generation; [author PDF](https://qcb.ucla.edu/wp-content/uploads/sites/14/2020/04/PMID-30889379.pdf), PDF pages 17–18.

The GSE107299 `!Series_overall_design` field explicitly identifies `CPCG0398_rep` as a technical replicate and says the processed `CPCG0398` column already averages the two measurements. Do not average it a second time or count another patient. This statement is available directly in the cached series record, lines 10–12. [GSE107299 metadata](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE107299&targ=self&view=brief&form=text)

## 4. Actual cellularity alternatives and their missingness

The original Table 1 provides multiple distinct quantities. Its legend defines Qpure from matched blood/tumour **SNP-array** profiles; ASCAT estimates aberrant-cell fraction from SNP arrays; pathologic cellularity comes from review of a tumour section. LUMP is methylation-derived and therefore is not an independent genomic purity measurement. The source does not justify interchanging these covariates. See the original supplementary definitions linked in section 1.

| Original field | Present among 114 candidate clinical bridges | Present among original-study 73 |
|---|---:|---:|
| Age at Treatment | 114 | 73 |
| Gleason Score | 114 | 73 |
| Pathologic Cellularity | 70 | 70 |
| Qpure Cellularity | 112 | 72 |
| ASCAT Cellularity | 39 | 18 |
| ASCAT Ploidy | 39 | 18 |
| LUMP Cellularity | 73 | 73 |

These are **field-presence counts**, not approved eligible N. No imputation, covariate-outcome selection or model was performed. The primary source notes that age/grade ascertainment differs between radiotherapy and surgery. Confirm scales from the original numeric fields and choose a documented TCGA-compatible cellularity strategy; do not silently substitute portal percentages or pool purity estimators. SNP-array Qpure is a useful candidate with high coverage, but applicability to the later 41 code-matched specimens remains unresolved.

`patient_specimen_evidence.tsv` supplies all 210 candidate rows with source IDs, inclusion flags, assay multiplicity/provenance and clinical-field presence. `legacy_clinical_summary.json` and `linkage_summary.json` contain reproducible aggregates.

## 5. Concrete next policy options, not a selected analysis policy

1. Preserve three distinct mapping statuses: original-study supported bridge (73 candidates); clinical-code-only bridge (41); no original-table clinical bridge (96). Independently preserve complete, partial or absent methylation technical-provenance status. Do not collapse these into one “paired” boolean.
2. A conservative reproducibility route could use the original-study bridge as the candidate external cohort, explicitly accepting study-protocol rather than aliquot-level pairing. This would require a documented reviewer/user-approved specimen policy, a frozen technical-replicate aggregation rule appropriate to the available processed data, feature completeness checks, and a Qpure missingness/compatibility policy. Neither 73 nor 72 is declared the final N here.
3. A stricter requirement for direct per-record same-focus/aliquot linkage remains unsatisfied even for that route. The expanded 137 candidates need additional public specimen evidence before their clinical/purity bridge can be promoted. Code matching alone is insufficient.
4. Keep all original assay rows as provenance. Source methods average *intensities*; they do not automatically authorize averaging processed beta values as an equivalent operation. Replicate aggregation remains a design/format decision, without reference to outcomes. Do not pick the source with the most favorable methylation–expression relation.

**E3 remaining:** freeze the biological-unit definition, acceptable evidence level for adjacent-section pairing, and processed-data replicate policy; resolve or explicitly exclude unsupported specimen links. **E4 remaining:** replace the mislabelled WGS field, select and harmonize a legitimate covariate source, resolve expanded-specimen applicability and missingness. No endpoint or scientific gate has been approved by this audit.

## 6. Access, inspection and hash register

`provenance.json` records each request, UTC retrieval time, exact source URL, response type, retained bytes and SHA-256. `hash_register.json` hashes all local research artifacts except this narrative and the register itself, plus five reused cache inputs; `archive_inventory.json` records archive members and inspection status. New logged response bodies total **13,381,621 bytes**, below the 20,000,000-byte cap. HTTP headers, unreturned timeout bytes and browser-tool transport sizes are unavailable and excluded from that count. Previously cached metadata was reused rather than redownloaded.

**Archive scope disclosure:** the 8,357,921-byte publisher tables ZIP was retrieved to obtain the 38,116-byte clinical workbook. It also contains a per-gene CNA matrix workbook. Only the clinical workbook was extracted and inspected; the CNA workbook was neither extracted nor read. Thus an archive containing omics data was acquired, despite the requested no-full-matrix boundary; this was disclosed to the parent immediately. No RNA/methylation matrix was newly downloaded and no controlled-access data, credentials, server jobs or author contact was used.

The local `Fraser2017.pdf` is an HTML access response, and `Sinha2019.pdf` is empty: neither is valid evidence. The real paper text was inspected through the browser tool at the author-PDF links above, so no local checksum for those full papers is claimed. XML/PDF access failures are retained in the request ledger. The valid downloaded Fraser *supplement* and Shiah table carry local hashes. The small xlrd wheel was imported directly to read the old XLS; no package/environment installation occurred.

| Key artifact | SHA-256 |
|---|---|
| Shiah2017_S1.xls | `2be12838bf6514137dc404164c97ac9cb0b8f72d660cba119100ffb784c25a39` |
| Fraser2017_tables.zip | `89aa7aacd68fd5f5105afd7b8a2fb6fd457c2cce01f75a16a54d5fec77a277ee` |
| Fraser2017_supplement.pdf | `db2e84e39f6869065501eeda656ff0afcc5fbbbf10357d6c95c62e7bc6f8adbe` |

Public accessibility is recorded, not a blanket redistribution license. Artifacts remain in the owned planning folder; nothing was committed or pushed. The exact SHA-256 and parent ZIP-member relation for the extracted clinical workbook are in `hash_register.json`.
