# gse135222 source notes

PMID 31537801 and 32762727 as listed in the pinned GEO series metadata.

Pinned local GEO objects:
- `geo_family_soft`: SHA-256 `6cd0243c00b2b7c88cf1c210b37a961d94e53a61ecd9b23e31d2af054f3a7598`; https://ftp.ncbi.nlm.nih.gov/geo/series/GSE135nnn/GSE135222/soft/GSE135222_family.soft.gz
- `geo_tpm`: SHA-256 `8b122e610492e88fb0aa0a759b8e380b04f26f2f58ddc581f9c050e54d0990a0`; https://ftp.ncbi.nlm.nih.gov/geo/series/GSE135nnn/GSE135222/suppl/GSE135222_GEO_RNA-seq_omicslab_exp.tsv.gz

GEO family SOFT supplies the series design, sample titles, platform and processing statements. Patient identity and expression joins are proposals for review. Prior ICI is undocumented. Split DEVELOPMENT and exposure METADATA_ONLY are proposals.

The series describes 27 anti-PD-1/PD-L1 NSCLC patients, STAR 2.5.3, RSEM 1.3.1, hg19 and TPM. Individual pretreatment timing and response labels are not established in the inspected family SOFT.

The object contains 57,773 Ensembl-format identifiers among 57,820 feature rows; 47 rows have other formats. The mixed identifier system remains UNKNOWN under the all-identifiers rule.

## Per-patient clinical benefit (coordinator, 30 Oct 2026)
Jung et al. 2019, Nat Commun (doi:10.1038/s41467-019-12159-9), Supplementary Information PDF (`MOESM1_ESM.pdf`, open access, SHA-256 `d37fd1d6ce8a5c6201102b422e439011da5a52d236d514a14490c72ee20570e8`), page 12. **Supplementary Table 3, "Patient cohort for checkpoint blockade in lung cancer":** sample ID, mutation burden, global methylation, aneuploidy, PFS, PD event, and clinical benefit (DCB/NDB/na).
- The table has 60 patient rows: 59 parsed, plus 1 row with all-na outcome. Clinical benefit: DCB 14, NDB 44, na 1, plus 1 unparsed. This is the WES/methylation cohort, larger than the 27 GEO RNA samples; the RNA subset must be joined by sample ID to GEO titles under a reviewed rule.
- A derived TSV, with a provenance file (source hash, page, extractor), is in `.scratch/runtime/gse135222/staging-springer-20261030/`. The PDF text layer fuses the aneuploidy and PFS columns in some rows, so only sample ID, PD event and clinical benefit are used.
- The endpoint is SOURCE_BINARY (DCB/NDB, as defined in the paper; see BATCH3_EVIDENCE §3), not ORR.
