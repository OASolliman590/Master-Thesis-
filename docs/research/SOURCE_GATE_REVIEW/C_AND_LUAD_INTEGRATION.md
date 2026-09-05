# Integration review: C row identity and LUAD candidate manifest

Reviewed 2026-09-06, using local retained artifacts only. No network, matrix re-downloads, effects, model runs, test suite, or canonical edits.

## Decision

The central scientific assertions are supported. GSE199800 now has **12 observed candidate count rows and zero unique row-to-GSM/plate assignments**. LUAD has **1,013 primary-tumor candidate file/sample edges: 540 RNA and 473 450K**, not 1,013 paired patients. Neither source is promoted to final biological validation readiness.

## Material findings

No scientific discrepancy was found in `docs/research/C_GSE199800_IDENTITY.md`, the corresponding `specs/C/DATA.md` update, or the control-join status in `specs/C/SOURCE_MANIFEST.json`.

No material findings remain. An initially unclear reference to the outside report's hash register was resolved when root identified `docs/research/SOURCE_GATE_REVIEW/REPORT_REGISTER.json`. Its C report entry records 11,166 bytes and SHA-256 `da745bd3201e49e9a1d912b6587b7ed1e0b809b98b209304a3e4829cdef42c83`; the actual report hash matches. Root is making this register link explicit in the C summary.

## Verification evidence

- Reconstructed the expected LUAD candidate rows directly from the complete cached `planning/next_evidence/TCGA_secondary_manifest/luad_files.json`: primary-tumor edges for STAR Counts RNA and SeSAMe 450K. Every TSV field and the complete row multiset matched `docs/research/TCGA_secondary_manifest/candidate_files.tsv` exactly: 1,013 edges, RNA 540 and 450K 473.
- Distinct RNA and methylation case counts are 517 and 458, with 455 shared case IDs. Distinct sample IDs are 529 and 469, with 466 shared sample IDs. These metadata intersections are not a same-portion, QC-complete, duplicate-resolved paired analysis set.
- All five SHA-256 entries in the retained TCGA `EVIDENCE_MANIFEST.json` match their actual files: `summary.json`, `candidate_files.tsv`, `header_check.json`, `provenance.json`, and `header_provenance.json`.
- The cached complete LUAD raw response has the advertised 997,384 bytes and SHA-256 `3230295913d19f2345cc1b224434080a52f09b537a5023d2384c02b036d20336`, matching its provenance.
- All six retained C JSON artifacts are byte-identical to their complete outside-audit counterparts: transfer manifest, candidate row sets, identifier audit, positional-hypothesis checks, reused-source hashes, and code-resource access log.
- C's summary correctly distinguishes 767 DU145 count rows from 768 GEO entries without attributing the discrepancy to QC or identifying an omitted sample without evidence. LNCaP's different order rejects a general row-ordinal-to-GSM mapping. Duplicate condition identifiers do not provide plate identity. All-DMSO pooling is not presented as plate-matched validation.
- The source manifest's top-level update correctly records the complete identifier audit and unresolved control join. Its per-source accession-level contrast audit remains pending; this is compatible with a completed identifier sub-audit and does not admit a biological contrast.

## Limits

Review covers the current working-tree documentation and retained evidence. The candidate TSV was not yet tracked according to read-only `git ls-files --error-unmatch` at review time, so this is not a claim of verification against a committed Git blob. No molecular object checksum or biological effect was revalidated; advertised GDC molecular-file MD5 values remain metadata. No unseen mapping resource, dose-unit convention, independent culture/day replication, or count-file row ordering is inferred. A bounded metadata inspection command initially used the CSV default delimiter and failed before comparing records; the subsequent explicit TSV parsing produced the complete exact comparison above.
