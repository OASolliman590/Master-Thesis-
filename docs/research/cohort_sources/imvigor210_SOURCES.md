# imvigor210 cBioPortal sources

Pinned cBioPortal datahub commit `e1b75cd25bf7436d16719b7d76117ad8f3f66e54`. Source of record is the iAtlas study; the split role and exposure review are undecided.

| Object | SHA-256 |
| --- | --- |
| [blca_iatlas_imvigor210_2017_meta_study](https://raw.githubusercontent.com/cBioPortal/datahub/e1b75cd25bf7436d16719b7d76117ad8f3f66e54/public/blca_iatlas_imvigor210_2017/meta_study.txt) | `f9d86e4c64755d33b826ed016fa16444dbe5744f28f6cb1beb6e5c875afa5748` |
| [blca_iatlas_imvigor210_2017_data_clinical_patient](https://media.githubusercontent.com/media/cBioPortal/datahub/e1b75cd25bf7436d16719b7d76117ad8f3f66e54/public/blca_iatlas_imvigor210_2017/data_clinical_patient.txt) | `293b80f4d0e8fe5ceeb32098ea8f6542aa26fbb2b6171f7aefecc8bbd0f3c14a` |
| [blca_iatlas_imvigor210_2017_data_clinical_sample](https://media.githubusercontent.com/media/cBioPortal/datahub/e1b75cd25bf7436d16719b7d76117ad8f3f66e54/public/blca_iatlas_imvigor210_2017/data_clinical_sample.txt) | `e21ff3efb00ecf583a90a804551cf0122aff0dc5819d9d8f6af6c2d9af064eb1` |
| [blca_iatlas_imvigor210_2017_meta_mrna_seq_tpm](https://raw.githubusercontent.com/cBioPortal/datahub/e1b75cd25bf7436d16719b7d76117ad8f3f66e54/public/blca_iatlas_imvigor210_2017/meta_mrna_seq_tpm.txt) | `704d5c0821767c076be973c76c9c73fc75fa6fb6f18d23a37add93b09612419b` |
| [blca_iatlas_imvigor210_2017_data_mrna_seq_tpm](https://media.githubusercontent.com/media/cBioPortal/datahub/e1b75cd25bf7436d16719b7d76117ad8f3f66e54/public/blca_iatlas_imvigor210_2017/data_mrna_seq_tpm.txt) | `e13445ffecb9f77b97c3ee0c50b8a2c591e79b0daef55ebbd009bdde6905228c` |

PMID in study metadata: 39642637, 27939400.
Patient linkage: `blca_iatlas_imvigor210_2017_data_clinical_patient:PATIENT_ID` and `blca_iatlas_imvigor210_2017_data_clinical_sample:PATIENT_ID/SAMPLE_ID`; baseline: `blca_iatlas_imvigor210_2017_data_clinical_sample:SAMPLE_TREATMENT=Pre`; response: `blca_iatlas_imvigor210_2017_data_clinical_sample:RESPONSE`; treatment: `blca_iatlas_imvigor210_2017_data_clinical_patient:ICI_RX`.
Expression profile: `blca_iatlas_imvigor210_2017_meta_mrna_seq_tpm`. The TPM file name identifies the deposited expression table; verify processing and transformation.

Open: reviewer must decide split role and prior exposure, verify missing assay facts and source identity. The author package is unavailable through the HTTPS-only retriever; author cross-check remains open.
