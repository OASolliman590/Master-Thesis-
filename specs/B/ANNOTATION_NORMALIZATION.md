# B-G2 annotation-normalization preparation contract

**Status:** PROPOSED / NOT FROZEN / NO NORMALIZED EXPORT PINNED — 10 September 2026.
**Ticket:** [BG2_annotation_normalization.md](tickets/BG2_annotation_normalization.md).
**Machine-readable plan:** [annotation_normalization.proposed.json](annotation_normalization.proposed.json), validated against [annotation_normalization.schema.json](annotation_normalization.schema.json).
**Consumer:** already-implemented [B-G1](tickets/BG1_gene_set_registry.md) five-column annotation tables and `B-G1-annotation-manifest-v1` manifests.
**Does not mutate:** [gene_set_registry.proposed.json](gene_set_registry.proposed.json) or [gene_set_registry.schema.json](gene_set_registry.schema.json).

This document is a deterministic, source-specific **identifier-metadata preparation** contract. It is not a claim that any normalized annotation table has been emitted, hashed, or accepted as `source_status=pinned`. It does not freeze `P` or `U`, define `Q`, score a program, select genes, view CPC outcomes, prove measurement specificity, establish cross-platform transport, or release a biological analysis.

B-P remains the selected primary ([decision](../../docs/decisions/B_PRIMARY_BP_20260906.md)). Specimen, covariate, precision and promoter policies remain unresolved.

## Scope

Cover **exactly** the three B-G1 `required_coverage_sources`, with unchanged `source_id` strings:

| `source_id` | Role in B-G1 | What this contract prepares |
|---|---|---|
| `tcga_gencode_v36` | TCGA expression feature universe using audited GENCODE v36 identifiers | Patient-free identifier rows extracted later from a hash-audited example GDC STAR table; cohort-wide source freeze remains required |
| `gse107299_processed` | GSE107299 processed expression gene identifiers | Patient-free rows from the processed-matrix identifier fields |
| `historical_v18_maps` | Already-acquired historical HuGene 2.0 ST and HTA 2.0 BrainArray/custom-CDF v18 identifier maps | Patient-free rows from both v18 annotation databases as one B-G1 source |

No other expression, methylation, promoter-mask, or clinical source is admitted here.

Preparation of public annotation/identifier metadata is **separate** from later real-cohort feature construction (B-R1/B-I2). B-G2 may not build `U`, ingest patient expression values, or choose mappings by abundance, coverage, outcome, effect, or convenience.

## B-G1 output contract (normative consumer)

Each successful source export that a later freeze receipt marks `pinned` must be an uncompressed UTF-8 TSV, LF newlines, no BOM, exactly this header and no other columns:

```text
raw_id	canonical_symbol	entrez_id	ensembl_id	mapping_status
```

Every subsequent record has exactly five fields. `mapping_status` is exactly one of `mapped`, `ambiguous`, or `unmapped`.

| Status | Required cell contents |
|---|---|
| `mapped` | Non-empty `canonical_symbol` and at least one non-empty `entrez_id` or `ensembl_id` |
| `unmapped` | Empty `canonical_symbol`, `entrez_id`, and `ensembl_id`; `raw_id` preserved |
| `ambiguous` | Source-provided candidate symbol and/or identifiers retained **without automatic resolution**; `raw_id` preserved |

Companion B-G1 manifest JSON has **exactly** these keys and no others:

```json
{
  "schema_version": "B-G1-annotation-manifest-v1",
  "source_id": "tcga_gencode_v36",
  "source_status": "pinned",
  "canonicalization_authority": "non-empty source-specific authority and version",
  "identifier_namespace": "symbol_entrez_ensembl",
  "source_reference": "auditable local/source reference",
  "table_path": "relative/or/absolute/annotation.tsv",
  "table_sha256": "64 lowercase hex characters"
}
```

B-G1 rejects unknown fields, non-`pinned` status, empty text fields, hash mismatch, patient/value/sample/expression columns, NULs, malformed UTF-8, CR-only records, empty `raw_id`, and duplicate **exact** rows. Multiple **distinct** rows that share a symbol are retained; B-G1 reports them as duplicate/ambiguous coverage rather than collapsing them.

B-G2 must emit tables that can pass that parser. It must **not** emit `source_status=pinned` until an explicit source-acquisition/freeze receipt exists for that `source_id`.

The similarly named status fields remain distinct: the existing registry's `required_coverage_sources[].annotation_status` and this proposed plan's `sources[].source_status` both remain `pending_normalized_export`; only a later parent-approved B-G1 manifest may carry `source_status=pinned`.

## Source-freeze and input binding

Production `prepare` requires an exact `B-G2-source-freeze-receipt-v1` with `purpose=source_freeze`, `pin_authorized=true`, the target `source_id`, SHA-256 values for the exact approved plan and schema bytes, ordered input descriptors, parent reviewer identity/timestamp fields and a non-empty rationale. Unknown receipt or descriptor keys fail. Each descriptor binds exactly `role`, `object_name`, positive `byte_count`, lowercase 64-hex `sha256`, `retrieved_utc`, credential-free `exact_url`, `access_class=public`, `completeness`, `redistribution` and null `committed_path` for repository-bound receipts.

CLI inputs are repeatable `--input ROLE=PATH` values and must match the receipt order: one `tcga_gencode_v36` input for TCGA; one `gse107299_processed` input for GSE107299; and exactly `hta20`, then `hugene20st`, for the combined v18 source. Missing, extra, duplicate, reordered, role-mismatched, byte-count-mismatched or hash-mismatched inputs fail before parsing.

The emitted B-G1 `source_reference` is exactly `B-G2|{source_id}|source_freeze|{plan_sha256}|{schema_sha256}|{role1}:{sha256_1}[,{roleN}:{sha256_N}]|{reviewed_utc}`. It contains no path, URL or credential. Absent, false or synthetic authorization cannot produce a pinned manifest or `COMPLETE.json`.

Synthetic fixtures use only `validate-table --purpose synthetic_test`. That command emits a validation receipt, never a B-G1 manifest or completion marker, and therefore cannot be promoted into a source freeze. A later Python 3.11 standard-library implementation validates these explicit known structures directly; it need not implement a general JSON Schema engine.

## Canonicalization authority (already established; not re-decided)

Reuse the B-G1 registry rules. Do not edit the registry.

- Authority string: `NCBI Gene current symbols and aliases, reviewed 2026-09-10`
- Authority date: `2026-09-10`
- Exact, case-sensitive raw-token aliases only:
  - `MB21D1` → `CGAS`
  - `TMEM173` → `STING1`
  - `TAPBPR` → `TAPBPL`
- `TAPBP` and `TAPBPL` are distinct loci and must **never** collapse.
- Do not query live NCBI, HGNC, or Ensembl at convert time. The dated registry authority is the freeze for `canonical_symbol` rewriting.
- Preserve every `raw_id` exactly as extracted. Aliasing rewrites only `canonical_symbol`.

The B-G1 manifest's `canonicalization_authority` is source-specific: it names GDC STAR GENCODE v36 `gene_name`, GSE107299 processed `Symbol_UCSC`, or BrainArray ENTREZG 18.0.0 historical `SYMBOL`/`ENSEMBL` as applicable, followed by the dated NCBI alias authority above.

HLA **symbol** matches require explicit caution: a matching `HLA-*` token is not evidence of locus-specific measurement ([measurement checkpoint](../../docs/research/B_MEASUREMENT_CHECKPOINT.md); [expression-platform report](../../docs/research/B_measurement/B_expression_platform_contract/REPORT.md)). B-G2 records that caution in a sidecar; it does not recode mapping status from expression, probe-count, or convenience.

## Shared transformation rules

These rules are machine-indexed in the proposed JSON. They apply to every source unless a source recipe replaces them.

1. **Preserve raw identifiers.** Never rewrite `raw_id` to a “better” current ID.
2. **No outcome/abundance selection.** Never choose a mapping by expression magnitude, patient coverage, CPC/TCGA outcome, effect size, or convenience.
3. **Missing.** Empty source symbol and empty Entrez/Ensembl after extraction → `unmapped`. Do not impute from another source.
4. **Retired / NULL native maps.** Retain the row. `mapping_status=unmapped`. Do not fill from a conflicting table.
5. **Ambiguous native maps.** One `raw_id` with more than one source-provided candidate symbol or conflicting identifier set → one **row per candidate**, `mapping_status=ambiguous`. Do not pack multiple candidates into one cell with an invented delimiter (B-G1 did not define one).
6. **Many-to-one.** Distinct `raw_id` values mapping to one canonical symbol → retain all rows; do not collapse.
7. **One-to-many.** One `raw_id` mapping to multiple canonical symbols → ambiguous rows as in (5).
8. **Duplicates.** Byte-identical five-field rows are a failure, not a silent collapse. Distinct rows that differ in any field are retained.
9. **Conflicts across tables of the same source.** Emit both states (or unmapped plus a conflict receipt). Do not pick a winner by suffix stripping or majority.
10. **Stable order.** Sort by UTF-8 `raw_id`, then `mapping_status`, then `canonical_symbol`, then `entrez_id`, then `ensembl_id`. LF-terminated final row.
11. **Exact-byte hash.** SHA-256 of the uncompressed UTF-8 TSV bytes actually written. Hash the companion manifest separately. Do not invent hashes in this plan file.
12. **Empty cells** are empty strings, not `NA`, `NULL`, or `NaN`.
13. **Version suffixes** are source-specific (below). Stripping a suffix is never a silent uniqueness repair.

### Version-suffix rules

| Source | Native token | Required handling |
|---|---|---|
| `tcga_gencode_v36` | GDC `gene_id` such as the audited `ENSG00000166710.21` form | `raw_id` is the **exact** versioned token. Do not strip `.version` to merge rows. Proposed `ensembl_id` for `mapped`/`ambiguous` gene rows is that same exact token. |
| `gse107299_processed` | Processed `GeneID` Entrez digit string (audit used `"3105"` not `"3105_at"`) | Do not append `_at`. Do not invent Ensembl. |
| `historical_v18_maps` | BrainArray probeset `probe_id` such as `3105_at` | Keep `_at`. Do not strip `_at` to fill NULL Entrez rows. HuGene package NULL `101928749_at` versus GPL19803 description id `101928749` remains a recorded conflict ([expression report](../../docs/research/B_measurement/B_expression_platform_contract/REPORT.md); [independent review](../../docs/research/B_measurement/B_expression_platform_contract/EXPRESSION_REVIEW.md)). |

## Source recipes

Evidence classifications: **evidenced** = already recorded in named repository artifacts; **proposed** = this contract’s preparation rule, not yet executed; **blocked** = cannot be closed without a later freeze/receipt or a scientific decision outside B-G2.

### 1. `tcga_gencode_v36`

**Object / release identity (evidenced for one public specimen table, not all-case completeness).**
GDC STAR RNA-seq TSV for file UUID `a4980c9c-6c37-46da-8db3-c60a1c29081f`: comment `# gene-model: GENCODE v36`; columns `gene_id`, `gene_name`, `gene_type`, `unstranded`, `stranded_first`, `stranded_second`, `tpm_unstranded`, `fpkm_unstranded`, `fpkm_uq_unstranded`; 60,660 distinct gene IDs plus four `N_` summary records; SHA-256 `8339cb0b1bf80236a7fff6ec9ee18b5d8779a35fa32adf4f43c20e2495fd6d2c`; public URL recorded in [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json) and [table_inspection.json](../../docs/research/B_readiness/table_inspection.json). GDC documents GENCODE v36 STAR output ([LUAD header note](../../docs/research/TCGA_LUAD_SECONDARY.md); [GDC mRNA workflow](https://docs.gdc.cancer.gov/Data/Bioinformatics_Pipelines/Expression_mRNA_Pipeline/)). Cohort-wide identity of the 60,660-id set is **not** established.

**Raw identifier namespace:** versioned Ensembl gene IDs in `gene_id`.
**Parser / extraction boundary (proposed, grounded in B-F1):** read the GENCODE comment and header; skip `#` comments; exclude `gene_id` in `{N_unmapped, N_multimapping, N_noFeature, N_ambiguous}` as non-genes; extract only `gene_id` and `gene_name`. Do not parse abundance columns for mapping. Do not drop rows by `gene_type`.

**Provenance fields required on freeze:** object UUID/filename, byte count, SHA-256 of the exact local bytes used, retrieval URL without credentials, retrieved UTC, completeness (`full_single_object_not_full_cohort` until a later receipt proves a cohort-wide identical `gene_id` set), access class, redistribution-not-adjudicated.

**Transformation (proposed):**
`raw_id` ← `gene_id`; `canonical_symbol` ← alias(`gene_name`); `ensembl_id` ← exact `gene_id` when it is a non-summary gene token; `entrez_id` ← empty unless a **separately pinned** GENCODE-v36-to-Entrez crosswalk is named in that source’s freeze receipt. No such crosswalk was run ([expression report](../../docs/research/B_measurement/B_expression_platform_contract/REPORT.md)). Empty `gene_name` with a gene `gene_id` is `unmapped` if no Entrez crosswalk fills a unique identifier pair that still satisfies B-G1 `mapped` (Ensembl alone plus symbol can still be `mapped`).

**Acceptance:**

| Check | Class |
|---|---|
| Comment is GENCODE v36; header matches the nine STAR fields | evidenced (one object) |
| 60,660 gene rows after excluding four `N_` summaries | evidenced (one object); blocked as all-case |
| Eight proposed primary symbols present as `gene_name` with unique `gene_id` in that object | evidenced (identifier presence only) |
| No patient/value columns in the export | proposed |
| Entrez filled only from a freeze-named crosswalk | proposed / currently empty |
| Cohort-wide identical `gene_id` set | blocked until freeze |

### 2. `gse107299_processed`

**Object / release identity (evidenced).**
GEO processed matrix [GSE107299_Matrix_processed_data.tsv.gz](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE107nnn/GSE107299/suppl/GSE107299_Matrix_processed_data.tsv.gz); complete compressed object 32,357,821 bytes; SHA-256 `09d866ce89adb7122879354a523ae0c1fdac03572c555a2d647b64a35c342f2b`; retrieved 2026-09-05 20:44:59 UTC; 24,598 feature rows; 213 sample columns; zero malformed rows; matrix **not retained** ([full-expression audit](../../docs/research/B_readiness/GSE107299_full_expression_audit.json)). Author processing is RMA / BrainArray custom CDF v18 / `sva`, not RNA-seq TPM ([expression report](../../docs/research/B_measurement/B_expression_platform_contract/REPORT.md)).

**Raw identifier namespace:** processed `GeneID` (Entrez digit strings in the audit).
**Parser / extraction boundary:** the seven annotation fields before patient columns, as already accepted by B-F1: `GeneID`, `Symbol_UCSC`, `Name_UCSC`, `Chr_UCSC`, `Start_UCSC`, `End_UCSC`, `RefSeq_UCSC`. Extract `GeneID` and `Symbol_UCSC` only for the five-column table. **Do not read patient columns.** Coordinate/name/RefSeq fields are provenance, not B-G1 columns. `RefSeq_UCSC` is not Ensembl.

**Provenance fields required on freeze:** compressed-object SHA-256 above (or a newly hashed local copy that matches it), uncompressed-table SHA-256 if a decompressed identifier extract is stored, retrieval URL, retrieved UTC, feature-row count 24,598, explicit `matrix_retained=false` unless a later receipt says otherwise, redistribution-not-adjudicated. Compressed and decompressed hashes are distinct.

**Transformation (proposed):**
`raw_id` ← `GeneID`; `canonical_symbol` ← alias(`Symbol_UCSC`); `ensembl_id` empty (no Ensembl field in the seven columns). If `Symbol_UCSC` is empty, default `mapping_status=unmapped` and leave Entrez/Ensembl cells empty (B-G1 requires unmapped identifier fields empty); a sidecar may keep the native `GeneID`. A freeze-named Entrez-to-symbol table may later unique-map that GeneID into `mapped` with a non-empty canonical symbol. When symbol is non-empty and `GeneID` matches `^[0-9]+$`, `entrez_id` ← `GeneID` and status is `mapped` unless another native ambiguity applies.

**Acceptance:**

| Check | Class |
|---|---|
| Seven annotation field names match B-F1 | evidenced |
| 24,598 identifier rows on the complete object | evidenced (audit); blocked until freeze re-acquires identifier fields against that hash |
| Eight proposed genes have unique `GeneID` rows in the audit | evidenced (identifier/finite-row subgate only; not U) |
| Processed count 24,598 is not equated to v18 intersection 24,937 | evidenced |
| Patient columns absent from export | proposed |
| Ensembl invented from current NCBI | forbidden |

### 3. `historical_v18_maps`

**Object / release identity (evidenced as acquired annotation packages, not as a Git object and not as redistribution permission).**
BrainArray ENTREZG 18.0.0 packages, packaged 29 Jan 2014, Artistic-2.0 stated in DESCRIPTION, HTTP retrieval recorded:

| Package | Bytes | Mapping rows / nonmissing Entrez | SHA-256 |
|---|---:|---:|---|
| `hta20hsentrezg.db_18.0.0.tar.gz` | 814,118 | 26,194 / 26,191 | `e3e2e8f24951e6f067f08417e9677b571c58dc0832a5d7d3c11dfdf0b121add1` |
| `hugene20sthsentrezg.db_18.0.0.tar.gz` | 781,983 | 25,088 / 25,087 | `4edaefa017ed2bd2c82aeeed52c25bdc781170d636c2b65b26e7c2f10350d928` |

SQLite metadata: `HUMANCHIP_DB` schema 2.1, central id `ENTREZID`, taxon 9606, Entrez source date 2013-Sep12, Ensembl source date 2013-Sep3, UCSC hg19 2010-Mar22. CHIPNAME values `hta20` and `hugene20st`. NULL Entrez rows: HTA `100996402_at`, `101928749_at`, `101928757_at`; HuGene `101928749_at`. All inspected `is_multiple=0` (does **not** prove genomic specificity). Nonmissing Entrez intersection 24,937; HTA-only 1,254; HuGene-only 150. This intersection is **not** final `U`. Direct package URLs and the [BrainArray 18.0.0 ENTREZG page](http://brainarray.mbni.med.umich.edu/Brainarray/Database/CustomCDF/18.0.0/entrezg.asp) are in the expression report. Manufacturer GPL16686 / GPL17586 tables are **not** the processed-feature dictionary.

**Raw identifier namespace:** BrainArray v18 `probe_id` (`${Entrez}_at` when mapped).
**Parser / extraction boundary:** read-only SQLite members `hta20hsentrezg.db/inst/extdata/hta20hsentrezg.sqlite` and `hugene20sthsentrezg.db/inst/extdata/hugene20sthsentrezg.sqlite` from the hashed tarballs; tables used by the historical inspector: `probes(probe_id, gene_id, is_multiple)`, `metadata`, and optionally `SYMBOL` / `ENSEMBL` maps. Do not install or execute the R packages. Do not use vendor GPL transcript-cluster IDs as processed IDs. Do not ingest the HuGene probe-sequence table as a mapping oracle.

**Why platform-qualify `raw_id` (proposed):** both databases use overlapping `*_at` tokens. B-G1 rejects duplicate exact five-field rows and has no platform column. Proposed encoding: `{chipname}:{probe_id}` with `chipname` in `{hta20,hugene20st}`. Unqualified probesets are a validation failure.

**Provenance fields required on freeze:** both tarball SHA-256 values, SQLite member SHA-256 values already recorded in the expression-platform `hash_register.json` (`42a46e7f57b8e97252ab804e9978fb74478ec3193f055326300e3b5a27e91026` HTA sqlite; `c0941fd26e1d19c9479a6c6fba5be8c3ba9a32804a720b07ad0f1b81bde735ac` HuGene sqlite), member paths inside the archives, Entrez/Ensembl source dates, redistribution-not-adjudicated. Historical availability ≠ permission to commit the databases.

**Transformation (proposed):**
For each probeset row on each chip: `raw_id` ← `{chip}:{probe_id}`; if `gene_id` (Entrez) is NULL → `unmapped`; else `entrez_id` ← that Entrez string; `canonical_symbol` ← alias(historical `SYMBOL` if a unique SYMBOL exists for that probeset). Historical Ensembl (2013-Sep3 / Entrez-linked 2013-Sep12): copy into `ensembl_id` only when that probeset/Entrez has exactly one Ensembl token; otherwise leave `ensembl_id` empty and, if SYMBOL/Entrez already satisfy `mapped`, keep `mapped` and record the one-to-many Ensembl event in the sidecar. Never mix live current Ensembl with v18 Ensembl in the same cell.

**Conflicts (evidenced, unresolved policy):** GPL19803 description mapping includes `101928749` while the HuGene v18 database maps `101928749_at` to NULL. Proposed default: database NULL wins as `unmapped`; description-only id is recorded on the conflict receipt; suffix stripping is forbidden. A later freeze may name a different precedence **explicitly**; it may not silently fill.

**Acceptance:**

| Check | Class |
|---|---|
| Row counts 26,194 / 25,088 and NULL probesets listed above | evidenced |
| Each of the eight proposed genes has exactly one `${Entrez}_at` on each chip | evidenced (annotation coverage, not specificity) |
| `raw_id` platform-qualified; `_at` retained | proposed |
| NULL / GPL19803 conflict not suffix-repaired | evidenced requirement; proposed export behaviour |
| `is_multiple=0` not treated as specificity | evidenced limit |
| 24,937 intersection exported as if it were `U` | forbidden |
| HTA probe-sequence specificity | blocked (not retrieved) |

## Sidecar outputs (B-G2 owned; not B-G1 columns)

A later tool may write, beside the B-G1 table and manifest:

- `PROVENANCE.json` — source hashes, freeze-receipt hash, parser version, row counts
- `CONFLICTS.tsv` — retired, NULL, GPL19803 disagreement, one-to-many Ensembl, duplicate symbols
- `HLA_CAUTION.tsv` — rows whose canonical or source symbol matches `HLA-` prefix
- `UNMAPPED.tsv` — `raw_id` plus native fields that B-G1 requires to be emptied
- `FAILURE.json` / `INCOMPLETE.json` — see ticket
- `FREEZE_RECEIPT.json` — required before `source_status=pinned`

These sidecars must contain no patient, sample, or expression values.

## Failure receipts

Fail closed. Typical causes: missing freeze receipt; hash mismatch; unexpected header/comment; gzip/uncompressed hash confusion; patient/value columns present; empty `raw_id`; NUL/CR/UTF-8 errors; duplicate exact rows; unknown `source_id`; attempt to pin without freeze; schema additional-property; TAPBP/TAPBPL collapse; alias not applied exactly; invented Entrez/Ensembl; suffix stripping used as repair.

A failure writes a receipt with `status=failed` or `incomplete`, ordered reasons, and hashes of inputs that were actually read. It must not write a B-G1 `source_status=pinned` manifest.

## What B-G2 cannot freeze or claim

- Primary membership `P`, universe `U`, promoter set `Q`, specimen policy, purity comparability, eligible N, precision
- Program scores, models, CPC outcomes, gene selection, measurement specificity, cross-platform rank transport
- Redistribution rights (Artistic-2.0 on v18 DESCRIPTION, public GEO/GDC access, and historical acquisition are not a licence to commit source databases)
- That synthetic fixtures validate biology
- That the 24,937 v18 Entrez intersection or the 24,598 processed rows or the 60,660 STAR gene ids are interchangeable or are `U`

Large source objects stay outside Git. Git may hold this spec, schemas, later tiny synthetic fixtures, and permitted hash/provenance summaries. No credentials or private filesystem paths in committed files.

## Machine-readable correspondence

Every numbered shared rule and each source parser/suffix/conflict rule is a field under `mapping_rules` or `sources[].rules` in the proposed JSON. Remaining prose-only items are listed under `prose_only_rules` with an explicit reason (legal redistribution conclusion; HLA biochemical specificity; `U`/`Q` scientific freeze; cohort-wide TCGA gene-id identity).
