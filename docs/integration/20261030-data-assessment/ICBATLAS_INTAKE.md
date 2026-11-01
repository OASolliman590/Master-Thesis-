# ICBatlas full intake plan, 30 Oct 2026

**Goal (user, 30 Oct):** take in every cohort in the ICBatlas parse (25 studies, 33 pre-treatment cohorts, 1,361 patients). Two routes run side by side:
- **Route P (processed, now):** the deposited processed matrix, through the usual field map → V3 → signed worksheet.
- **Route R (raw, on the new HPC cluster):** every public RNA-seq study re-processed with **one pinned nf-core/rnaseq pipeline** (one reference genome, one annotation, one quantifier). This gives one documented, comparable representation across studies, removing today's FPKM / TPM / upper-quartile mix and the undocumented-pipeline limitations. Route-P tables are kept as sensitivities.

Sizes are ENA `fastq_bytes`, RNA-Seq runs only, measured 30 Oct with `tools.a_discovery fastq` (WXS runs excluded).

| ICBatlas study | Cancer | Patients | Pipeline status | Route P (processed) | Route R (raw RNA-seq) |
| --- | --- | ---: | --- | --- | --- |
| SRP094781 Riaz | Melanoma | 49 | Admitted | Done | 109 runs, 486 GB |
| SRP070710 Hugo | Melanoma | 27 | Admitted | Done | 28 runs, 239 GB |
| SRP011540 anti-PD-1 (Liu 2019) | Melanoma | 120 | Signing | Done (DFCI TPM) | Controlled (dbGaP phs000452): no public FASTQ |
| ERP105482 Gide | Melanoma | 73 | Join check | Done, with limitation | 91 runs, 824 GB; **removes the limitation** |
| IMvigor210 | Urothelial | 298 | Final test (locked) | Author package held | Controlled (EGA) |
| GSE176307 | Urothelial | 89 | Worksheet open | Resolve 3 items | Check SRA |
| SRP150548 (GSE115821) | Melanoma | 14 | Parked | Blocked: per-patient response | 37 runs, 69 GB; still needs response |
| SRP183455 (GSE126044) | NSCLC | 16 | Parked | Blocked: sample mapping | 16 runs, 99 GB; still needs mapping |
| SRP217040 (GSE135222) | NSCLC | 27 | Not started | GEO RSEM TPM | 27 runs, 106 GB |
| SRP250849 (GSE145996) | Melanoma | 14 | Not started | GEO FPKM (14 of 52) | 42 runs, 64 GB; **may recover more patients** |
| SRP302761 (GSE165278) | Melanoma (anti-CTLA-4) | 7 | Not started | GEO TPM (xlsx) | 149 runs, 103 GB |
| SRP155030 Zhao | GBM | 26 | Not started | None | 34 runs, 105 GB (raw only) |
| ERP107734 Kim | Gastric | 45 | Not started | None | 78 runs, 292 GB (raw only) |
| GSE136961 | NSCLC | 21 | Not started | GEO | Check SRA |
| PMID 32472114 Braun | RCC | 281 | Not started | Supplement S4A + S1 | Controlled |
| PMID 33806963 | RCC | 13 | Not started | Supplement S10 | Check |
| SRP011540 anti-CTLA-4 (Van Allen) | Melanoma | 41 | Not started | cBioPortal | Controlled |
| TCGA melanoma anti-CTLA-4 | Melanoma | 13 | Not started | TCGA subset (GDC) | GDC (controlled raw) |
| GSE93157 | HNSCC / melanoma / NSCLC | 5 / 25 / 35 | Not started | GEO array | n/a (array) |
| GSE67501 | RCC | 11 | Not started | GEO array | n/a |
| GSE99070 | Mesothelioma | 10 | Not started | GEO array | n/a |
| GSE122220 | Melanoma | 8 | Not started | GEO array | n/a |
| GSE140901 | HCC | 13 + 9 | Not started | GEO array | n/a |
| GSE111636 | Urothelial | 11 | Not started | GEO array | n/a |
| SRP128156 Miao | RCC | 33 | Not started | — | Controlled (dbGaP) |
| SRP230414 (phs001919) | Melanoma | 27 | Not started | — | Controlled; 5 of 60 runs public |

**Route R total (public RNA-seq):** about **2.39 TB** across 10 studies. Without Gide it is about 1.56 TB, and without Gide and Riaz about 1.08 TB. Arrays have no raw route; they stay processed-only, in their own measurement stratum.

**Discovery-tool fixes found while sizing:**
- paired runs with a third (unpaired) FASTQ file make the samplesheet step fail (SRP150548): it should use `_1`/`_2` and record the extra file;
- controlled projects (no public FASTQ) should be reported as CONTROLLED, not raise an error.

## Order
1. **Route P now**, cheapest first: the GEO RNA-seq sets (GSE135222, GSE136961, GSE145996, GSE165278), Braun, Van Allen, then the GEO arrays, PMID 33806963 and the TCGA subset. Each is one Terra round plus a user signature.
2. **Route R when the cluster arrives:** pin the nf-core release and reference, then run Zhao and Kim (new cancers), GSE145996 (more patients) and the standardization re-runs.
