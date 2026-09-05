# Independent metadata cross-check

6 September 2026. **No material discrepancy found in the reported LUAD metadata counts or scope.** Reviewed both audit scripts, raw cached JSON, summary, provenance, status, header check and report. Recomputed counts from distinct `(file UUID, case UUID, primary-sample UUID)` edges independently of the audit functions; no network, molecular analysis or repository tests were run.

| Recomputed quantity | STAR RNA | SeSAMe 450K |
|---|---:|---:|
| All-sample-type files | 601 | 507 |
| Primary files | 540 | 473 |
| Primary sample UUIDs | 529 | 469 |
| Primary case UUIDs | 517 | 458 |
| Cases with two primary samples | 12 | 11 |
| Samples with two files | 11 | 4 |

All other primary cases/samples have one corresponding sample/file: RNA 505/518; methylation 447/465. There are no higher multiplicities in these counted relationships. Recomputed case and sample UUID sets exactly match the saved lists. Intersections are **455 cases and 466 samples**, with **62 RNA-only and 3 methylation-only cases**, as reported.

The raw response contains 1,311 distinct file UUIDs, equals its pagination total, is file-ID sorted and records open access for every file. The platform/workflow table matches exactly: 600 Illumina STAR files plus one platform-missing STAR file; 507 SeSAMe 450K, 150 SeSAMe 27K and 53 SeSAMe EPIC-v2 files. The code restricts the methylation group to explicit 450K plus SeSAMe; 27K and EPIC-v2 are correctly excluded and separately labelled. Project attribution follows the retained TCGA-LUAD API filter; project IDs were not separately requested in each returned case object.

Recomputed metadata SHA256 `3230295913d19f2345cc1b224434080a52f09b537a5023d2384c02b036d20336`, its 997,384-byte size and the recorded `inspect_luad.py` source hash all match. Both status/prefix SHA256 values and byte counts match `header_provenance.json`; total retained response bytes are 999,653. Release status equals the copy in `header_check.json`.

Independently sorting eligible RNA candidates selects `0052ae83-7ae5-470a-a125-5cd94a9fa9e9`; its full metadata object matches the saved selection. The actual prefix confirms GENCODE v36 and the nine saved STAR column labels. **The 2,048-byte prefix ends mid-record:** this is acceptable for its declared header-only purpose, but it is not a complete-record bounded TSV fixture and must not be reused as one without separately documented trimming and a new hash.

The report correctly claims metadata acquisition and one-header inspection only. It retains portion/focus/aliquot linkage, independent-patient selection, object checksums, assay coverage/QC, covariates and biological interpretation as unresolved. Neither sample intersections nor workflow/header agreement certify a validated paired cohort, cross-tissue comparability or a scientific primary. The PRAD 497 ceiling was not independently re-audited in this LUAD-only review.
