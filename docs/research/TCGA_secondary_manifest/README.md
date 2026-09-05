# Reproducing the metadata audit

These are source-audit utilities and metadata references, not the B/C production workflow. `candidate_files.tsv` contains 1,013 primary-file/sample edges before biological eligibility and duplicate resolution. Its MD5/size fields are source-advertised metadata, not our verification of the molecular objects.

To retrieve a fresh snapshot, copy `inspect_luad.py` and `inspect_release_and_header.py` into a new empty audit directory outside the tracked evidence directory. Run them in that order using Python3.11 or newer. The first rejects an existing raw response and responses over12MB; the second reads at most250KB status plus2KB of one molecular object. Network/API or shape failures require inspection, not blind retry. Current retained scripts were executed with local Python3.12; AIU was inaccessible.

The original raw response and prefix remain at `E:/Master_Thesis/planning/next_evidence/TCGA_secondary_manifest/`. Their exact lengths/checksums and query URLs are retained. The published summary omits the redundant UUID lists; the candidate file-reference table preserves source joins. The 2KB prefix ends mid-record and is suitable only for its recorded header inspection. Do not run it through the complete-record B-F1 fixture contract.

`REVIEW.md` records independent recomputation from the original response. It does not certify downloaded cohort data, same-portion pairing, QC, statistical eligibility or biology. A new API snapshot may differ; preserve the prior snapshot and compare changes explicitly rather than overwriting its provenance.
