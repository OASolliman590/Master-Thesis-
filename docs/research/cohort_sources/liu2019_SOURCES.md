# liu2019 cBioPortal sources

Pinned cBioPortal datahub commit `e1b75cd25bf7436d16719b7d76117ad8f3f66e54`. The author DFCI study is the source of record; iAtlas is the sensitivity and cross-check. The split role is DEVELOPMENT and exposure is METADATA_ONLY.

| Object | SHA-256 |
| --- | --- |
| [mel_iatlas_liu_2019_meta_study](https://raw.githubusercontent.com/cBioPortal/datahub/e1b75cd25bf7436d16719b7d76117ad8f3f66e54/public/mel_iatlas_liu_2019/meta_study.txt) | `1dc403307920ef96de99bf2544cffc138e084d9e969e4c66a2f7e0216920c339` |
| [mel_iatlas_liu_2019_data_clinical_patient](https://media.githubusercontent.com/media/cBioPortal/datahub/e1b75cd25bf7436d16719b7d76117ad8f3f66e54/public/mel_iatlas_liu_2019/data_clinical_patient.txt) | `ef4a7d9d14d78ccbbb75bbb0f17161388921122ccc6729acec47769c7bb60f5b` |
| [mel_iatlas_liu_2019_data_clinical_sample](https://media.githubusercontent.com/media/cBioPortal/datahub/e1b75cd25bf7436d16719b7d76117ad8f3f66e54/public/mel_iatlas_liu_2019/data_clinical_sample.txt) | `f6ece7f92fed7cc62aa080bb509e78da8b76660219c25d21ecb0db208955f945` |
| [mel_iatlas_liu_2019_meta_mrna_seq_tpm](https://raw.githubusercontent.com/cBioPortal/datahub/e1b75cd25bf7436d16719b7d76117ad8f3f66e54/public/mel_iatlas_liu_2019/meta_mrna_seq_tpm.txt) | `f830c1b9abf8891522f41b1b3bc27e3d993c8e9df0f9b9c2742d35ab844e614e` |
| [mel_iatlas_liu_2019_data_mrna_seq_tpm](https://media.githubusercontent.com/media/cBioPortal/datahub/e1b75cd25bf7436d16719b7d76117ad8f3f66e54/public/mel_iatlas_liu_2019/data_mrna_seq_tpm.txt) | `ec81f1658973d09263f488aefd2907266a6febc7bf4a9f0621f43c3d98942fbe` |
| [mel_dfci_2019_meta_study](https://raw.githubusercontent.com/cBioPortal/datahub/e1b75cd25bf7436d16719b7d76117ad8f3f66e54/public/mel_dfci_2019/meta_study.txt) | `7776359bea1a80ad9b88acef36ecb09a29a88c7010b9bafa816ab3548d331341` |
| [mel_dfci_2019_data_clinical_patient](https://media.githubusercontent.com/media/cBioPortal/datahub/e1b75cd25bf7436d16719b7d76117ad8f3f66e54/public/mel_dfci_2019/data_clinical_patient.txt) | `3defdf06485e877d4b91b6b69c8e7af5615dd749c9dea54662ca3f4d0bc760a1` |
| [mel_dfci_2019_data_clinical_sample](https://media.githubusercontent.com/media/cBioPortal/datahub/e1b75cd25bf7436d16719b7d76117ad8f3f66e54/public/mel_dfci_2019/data_clinical_sample.txt) | `f665b8688708327e7a32f2d5a4efa3e34e7a7c849a9eb3996ec50e19d9111316` |
| [mel_dfci_2019_meta_mrna_seq_tpm](https://raw.githubusercontent.com/cBioPortal/datahub/e1b75cd25bf7436d16719b7d76117ad8f3f66e54/public/mel_dfci_2019/meta_mrna_seq_tpm.txt) | `eef866a8e2a4148dab228c5aed2cd5a11d9bfe001f60abb6c4c1098bce77d51f` |
| [mel_dfci_2019_data_mrna_seq_tpm](https://media.githubusercontent.com/media/cBioPortal/datahub/e1b75cd25bf7436d16719b7d76117ad8f3f66e54/public/mel_dfci_2019/data_mrna_seq_tpm.txt) | `5b12ee2a161cbce35274d5ed6a999e89d6fcb21679cd10f2f8e8e0374c6c2dd4` |

PMID in study metadata: 31792460.

The [30 October follow-up](../../decisions/BATCH2_CBIOPORTAL_20261030.md#follow-up-decisions) selects the author DFCI TPM as primary and iAtlas TPM as a separate sensitivity. Patient and sample joins use DFCI `PATIENT_ID` and `SAMPLE_ID`; `BIOPSY_CONTEXT=Pre-PD1` supplies the baseline label. The source of record for response is DFCI `BR`; iAtlas `RESPONSE` is preserved alongside. DFCI `PRIOR_CTLA4` describes the patient, and does not necessarily establish exposure at biopsy.

The [processing evidence](BATCH2_PROCESSING_EVIDENCE_20261030.md#2-liu-2019-mel_dfci_2019-authors-tpm) records STAR and RSEM gene-level linear TPM, snoRNA removal and re-summing, and the Ensembl GRCh38.p10 biotype filter. Tool versions and alignment build and GTF remain unknown; the filter build is not treated as the alignment build. The instruments were Illumina HiSeq 2000 v3 or 2500, as cited below.

The DFCI matrix has 121 sample columns, all mapped by source sample ID; 104 have a source-labelled Pre-PD1 biopsy. The approved decision excludes Pre-Ipi biopsies from the baseline branch for a prior-ICI sensitivity. Clinical samples without a matrix column have no eligible RNA. An exact patient-key cross-check found 122 shared patient identifiers, 120 matching response labels and two differences; DFCI remains source of record. Possible melanoma overlap is flagged, not certified independent.

## Sequencing and processing facts (PMC full text, PMC6898788, read 30 Oct 2026)
Liu et al., Nat Med 2019, doi:10.1038/s41591-019-0654-5, Methods:
- **Library:** whole-transcriptome sequencing of FFPE tissue. The cDNA libraries were exome-captured (hybrid capture), pooled four-plex, and sequenced on **Illumina HiSeq 2000 v3 or HiSeq 2500, 76 bp paired-end**. Demultiplexing used the Broad Picard pipeline.
- **Processing:** aligned with **STAR** and quantified with **RSEM** to gene-level TPM. snoRNA genes (380) were excluded using Ensembl biotypes (`hsapiens_gene_ensembl`, GRCh38.p10), and TPM was re-normalized.
- **Not stated in the paper:** the STAR/RSEM versions, and the alignment reference build and gene annotation (GTF). These stay UNKNOWN.
- **RNA-seq after QC:** 121 patients (pretreatment).
