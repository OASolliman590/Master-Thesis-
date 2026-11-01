# Van Allen 2015 source notes

Van Allen et al., Science 2015; PMID 26359337 per pinned cBioPortal study metadata. The clinical source states ipilimumab treatment. The expression matrix has 40 exact sample-ID joins; pretreatment status is not established in the pinned clinical fields.

The filename describes RPKM, whereas `meta_mrna_seq_rpkm` describes FPKM. Processing details and unit remain UNKNOWN pending the author paper. The clinical field `DURABLE_CLINICAL_BENEFIT` contains raw CR/PR/SD/PD/X categories; the intended endpoint definition and assessment criteria need review. Prior ICI is UNKNOWN. DEVELOPMENT and METADATA_ONLY are proposed, unsigned.

Pinned objects:
- `skcm_dfci_2015_meta_study`: SHA-256 `5231297538e4c2074b5d2ada2e6ddbff24d8ab393d047d782010dbfe94531dff`; https://raw.githubusercontent.com/cBioPortal/datahub/e1b75cd25bf7436d16719b7d76117ad8f3f66e54/public/skcm_dfci_2015/meta_study.txt
- `skcm_dfci_2015_data_clinical_patient`: SHA-256 `c684b93833c3e1983fa94beb77eb6b9c033571c8c560ed83801806ae3e278ce0`; https://media.githubusercontent.com/media/cBioPortal/datahub/e1b75cd25bf7436d16719b7d76117ad8f3f66e54/public/skcm_dfci_2015/data_clinical_patient.txt
- `skcm_dfci_2015_data_clinical_sample`: SHA-256 `2c37d96c0daf6c9660aaea928ae7a129072e80fec048b90a6ac2aefd50399f9d`; https://media.githubusercontent.com/media/cBioPortal/datahub/e1b75cd25bf7436d16719b7d76117ad8f3f66e54/public/skcm_dfci_2015/data_clinical_sample.txt
- `skcm_dfci_2015_meta_mrna_seq_rpkm`: SHA-256 `caba3cdcdbcd3289cb24c0076a07a113027469eb65270472ecef3ee9609a1939`; https://raw.githubusercontent.com/cBioPortal/datahub/e1b75cd25bf7436d16719b7d76117ad8f3f66e54/public/skcm_dfci_2015/meta_mrna_seq_rpkm.txt
- `skcm_dfci_2015_data_mrna_seq_rpkm`: SHA-256 `4c7e8d686b8f81eb32115b8010b2ae5b87091ea24a1965e162e2916d855c1835`; https://media.githubusercontent.com/media/cBioPortal/datahub/e1b75cd25bf7436d16719b7d76117ad8f3f66e54/public/skcm_dfci_2015/data_mrna_seq_rpkm.txt
