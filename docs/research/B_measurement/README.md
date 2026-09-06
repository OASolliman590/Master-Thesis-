# Paper B measurement evidence package

This directory is the canonical selected copy of the 6 September 2026 source-audit checkpoint. `REPORT.md` files and most helper/output files are byte-identical audit-time snapshots. Statements inside those reports that artifacts “remain outside the canonical repository” describe the state when the audit was performed; selected small artifacts are now copied here, while raw/large inputs remain outside Git.

`ARTIFACTS.json` inventories every retained file except itself and records required omitted inputs with exact paths, sizes and hashes. The copied expression and promoter independent-review receipts are byte-identical to their outer originals. These receipts do not establish AIU or final-Opus validation.

## Historical helper boundary

Do not treat these scripts as production commands. Do not run a retrieval helper merely to validate documentation. No helper chooses B-P/B-R, U, Q, a specimen, final N or any molecular effect.

The audit-time expression helpers are reproducible from their original outer cache:

```text
python -B E:/Master_Thesis/planning/next_evidence/B_expression_platform_contract/inspect_annotations.py
python -B E:/Master_Thesis/planning/next_evidence/B_expression_platform_contract/inspect_cached_metadata.py
```

`inspect_annotations.py` requires, in its own directory, both v18 `.tar.gz` packages plus `GPL19803_desc.annot.txt.gz` and `GPL19803_probe_tab.txt.gz`; it extracts the two SQLite members there. `inspect_cached_metadata.py` additionally reads the hard-coded canonical `docs/research/B_paired_prostate/` files, `docs/research/B_readiness/GSE107299_full_expression_audit.json`, and `E:/Master_Thesis/planning/feasibility/source_metadata/GSE107299_family.soft.gz`. `fetch.py` is a historical network acquisition helper and is not part of an offline reproduction check.

The promoter helpers must run in their original layout, where `B_promoter_semantics/` and `B_annotation/` are sibling directories:

```text
python -B E:/Master_Thesis/planning/next_evidence/B_promoter_semantics/audit_promoters.py
python -B E:/Master_Thesis/planning/next_evidence/B_promoter_semantics/crosscheck_transcripts.py
```

The first command verifies the two full annotation/mask hashes and generates `probe_gene_candidates.tsv`, `cognate_transcript_evidence.tsv` and `summary.json` in `B_promoter_semantics/`. The second then requires those outputs plus the five `ucsc_gencode_v36_*.json` files in that same directory. The raw full annotation/mask and UCSC response bodies remain omitted from Git.

The TCGA audit-time layout is:

```text
python -B E:/Master_Thesis/planning/next_evidence/B_TCGA_cellularity/audit.py
```

It requires the omitted source TSV and the canonical `docs/research/B_paired_prostate/summary.json`. `retrieve_original_20260906.py` preserves the exact original acquisition-helper bytes and must not be run against the historical cache. The maintained `retrieve.py` adds explicit `--output-dir`, `--url`, `--source-page` and `--expected-sha256` inputs; cache reuse preserves `retrieved_utc`, records `verified_utc`, and fails on missing receipt or digest/URL disagreement. Its offline regression test uses only disposable synthetic cache directories:

```text
python -B docs/research/B_measurement/B_TCGA_cellularity/test_retrieve_cache.py
```

The cellularity-method report used the already retained Fraser supplement PDF and table listed under omitted dependencies in `ARTIFACTS.json`; no source-producing helper was copied for that audit.
