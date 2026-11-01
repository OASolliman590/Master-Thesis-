# gide2019 cBioPortal sources

Pinned cBioPortal datahub commit `e1b75cd25bf7436d16719b7d76117ad8f3f66e54`. The deposited expression profile is from iAtlas. The author clinical tables are the requested source for RECIST and clinical benefit, pending a supported identity join. The split role is DEVELOPMENT and exposure is METADATA_ONLY.

| Object | SHA-256 |
| --- | --- |
| [mel_iatlas_gide_2019_meta_study](https://raw.githubusercontent.com/cBioPortal/datahub/e1b75cd25bf7436d16719b7d76117ad8f3f66e54/public/mel_iatlas_gide_2019/meta_study.txt) | `f90ef6d4b91762ebd12d7e793db72e2dbd344132552474632d680a878a8de8ca` |
| [mel_iatlas_gide_2019_data_clinical_patient](https://media.githubusercontent.com/media/cBioPortal/datahub/e1b75cd25bf7436d16719b7d76117ad8f3f66e54/public/mel_iatlas_gide_2019/data_clinical_patient.txt) | `d66be75803000e29be7d57674ccdba29de3d7cf264d6cbb62e0cf63c658fa437` |
| [mel_iatlas_gide_2019_data_clinical_sample](https://media.githubusercontent.com/media/cBioPortal/datahub/e1b75cd25bf7436d16719b7d76117ad8f3f66e54/public/mel_iatlas_gide_2019/data_clinical_sample.txt) | `ebdf3aa1067c7aac73d17167bed34d246c243d177f7e95671fb34c988c3b5e62` |
| [mel_iatlas_gide_2019_meta_mrna_seq_expression](https://raw.githubusercontent.com/cBioPortal/datahub/e1b75cd25bf7436d16719b7d76117ad8f3f66e54/public/mel_iatlas_gide_2019/meta_mrna_seq_expression.txt) | `2488f76b26dd7b4bc27be671bc7f49fe9104b3c22a56082b71a6cb2b412c090a` |
| [mel_iatlas_gide_2019_data_mrna_seq_expression](https://media.githubusercontent.com/media/cBioPortal/datahub/e1b75cd25bf7436d16719b7d76117ad8f3f66e54/public/mel_iatlas_gide_2019/data_mrna_seq_expression.txt) | `a2e5e119409f76120510f82954f605c02d64605ef8e7bb9b17fb49bd3683912b` |

PMID in study metadata: 30753825.
Patient linkage: `mel_iatlas_gide_2019_data_clinical_patient:PATIENT_ID` and `mel_iatlas_gide_2019_data_clinical_sample:PATIENT_ID/SAMPLE_ID`; baseline: `mel_iatlas_gide_2019_data_clinical_sample:SAMPLE_TREATMENT=Pre`; response: `mel_iatlas_gide_2019_data_clinical_sample:RESPONSE`; treatment: `mel_iatlas_gide_2019_data_clinical_patient:ICI_RX`.
Expression profile: `mel_iatlas_gide_2019_meta_mrna_seq_expression`. The profile describes log2 upper-quartile normalized counts.

Open: source identity and author clinical linkage require review. Melanoma family overlap remains unresolved; no independence is certified.

The author clinical supplementary tables S1 and S2 are pinned locally by the hashes in the [Gide decision](../../decisions/BATCH2_CBIOPORTAL_20261030.md#gide-decisions-user-30-oct-2026). The sparse XLSX tables parse, but a documented, unambiguous link from their arm and patient number to cBioPortal patient identifiers remains unresolved; their endpoints have not been transferred.

The same decision assigns DEVELOPMENT and METADATA_ONLY and accepts the deposited profile with the stated four conditions. The deposited processing pipeline remains undocumented. Prior ICI stays UNKNOWN.

## Author methods (read from the paper PDF supplied by the user, 30 Oct 2026)
Gide et al., Cancer Cell 35:238–255, 2019 (PMID 30753825), STAR Methods, "RNA-seq Data Processing" and "Differentially Expressed Gene Analysis":
- **Authors' pipeline:**
  - Trimmomatic adapter removal;
  - TopHat 2.0.8 (Bowtie 2.1.0, SAMtools 0.1.19) alignment to Ensembl GRCh38;
  - HTSeq 0.6.1 htseq-count against the Ensembl gene annotation (release not stated);
  - DESeq2 normalization, with values displayed as counts per million.
  - Illumina HiSeq 2500, paired-end, median 47 M reads.
- **Consequence:** the authors never describe "log2 upper-quartile normalized counts". The deposited cBioPortal profile `mel_iatlas_gide_2019` was therefore produced downstream (presumably by iAtlas, from the ENA FASTQ), by a pipeline that remains UNDOCUMENTED. No author processed table is public. Data availability lists only ENA PRJEB23709 (FASTQ).
- **Cohort:**
  - anti-PD-1 monotherapy RNA-seq: 41 PRE + 9 EDT;
  - ipilimumab + anti-PD-1: 32 PRE + 9 EDT.
  - EDT = 7–14 days after starting treatment.
  - Per-patient clinical data: supplementary Tables S1 (monotherapy) and S2 (combined); online only, not in the PDF.
- **Authors' response definition:** RECIST 1.1. Responders are CR, PR, or SD > 6 months with no progression. Non-responders are PD, or SD ≤ 6 months. This is a clinical-benefit (SOURCE_BINARY) definition, separate from ORR. ORR can be derived only from per-patient RECIST categories.
