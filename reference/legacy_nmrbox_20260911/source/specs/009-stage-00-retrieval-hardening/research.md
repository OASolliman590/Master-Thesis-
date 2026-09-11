# Research: Spec 009 — Stage 00 Retrieval

This file consolidates: (1) current-state audit with code citations, (2) I/O contracts to freeze, (3) scientific-validity considerations for the retrieval stage.

---

## 1. Current-State Audit (verified 2026-05-28)

### 1.1 Where the code lives

All in `src/pipeline/cli.py` (10,515 lines total). Stage 00 surface:

| Line | Symbol | Role | Public? |
|---:|---|---|---|
| 583 | `_extract_geo_accession_from_cohort_id` | Pulls leading GSE from `cohort_id` | private |
| 588 | `_find_geo_soft_file` | Locates already-downloaded SOFT file in cohort dir | private (used by Stage 02) |
| 619 | `_geo_series_prefix` | Maps `GSE123456` → `GSE123nnn` | private |
| 623 | `_download_url` | Streaming HTTP download with `.part` atomic rename | private |
| 643 | `_download_url_if_missing` | Idempotent wrapper around `_download_url` | private |
| 649 | `_fetch_html_links` | Scrapes `<a href>` from FTP HTML index | private |
| 661 | `_safe_remote_filename` | URL-decode and basename | private |
| 666 | `_download_geo_family_soft` | Fetches one `_family.soft.gz` per GSE | private |
| 680 | `_download_geo_series_matrix` | Lists matrix dir, fetches each `*series_matrix*.gz` | private |
| 716 | `_download_geo_supplementary` | Lists suppl dir, fetches each non-index file | private |
| 754 | `_download_runinfo` | Fetches SRA runinfo CSV; rejects empty/malformed | private |
| 787 | `_parse_geo_soft_sample_records` | Parses GSM records from SOFT | private (used by Stage 01) |
| 858 | `_parse_geo_soft_samples` | Flat-schema view of above | private (used by Stage 01) |
| 1306 | `cmd_retrieval_run` | argparse handler — basic driver | CLI |
| 1392 | `cmd_retrieval_geo_full` | argparse handler — full GEO | CLI |
| 1538 | `cmd_retrieval_geo_manifest` | argparse handler — downstream summarizer | CLI |

**Observation**: `_parse_geo_soft_*` is structurally Stage 00 (parses files Stage 00 downloads) but is also imported by Stage 01 metadata-extraction code. The extraction must keep `_parse_geo_soft_sample_records` callable from Stage 01 without circular imports — handle by exposing it from `_00_retrieval.soft_parser`.

### 1.2 What works

- Atomic rename via `.part` suffix in `_download_url` (L623–L640) — partial downloads do not pollute the cohort dir on crash.
- Idempotency via `_download_url_if_missing` (L643) checks `dest.exists() and dest.stat().st_size > 0`.
- Series-matrix listing dedups via `sorted(set(targets))` (L705) — safe against repeated hrefs.
- Runinfo content sanity check (L760–L765) — rejects empty or non-CSV responses by looking for `"Run,"` header.
- Existing test `tests/unit/test_retrieval_geo_manifest.py` (65 lines) verifies the geo-manifest summarizer correctly counts SOFT/matrix/suppl/runinfo files.

### 1.3 Gaps to close

| Gap | Severity | FR addressed |
|---|---|---|
| Stage 00 module dir empty; code in `cli.py` | High (blocks future stage refactors) | FR-001, FR-002, FR-009 |
| No tests for `cmd_retrieval_run` or `cmd_retrieval_geo_full` | High | FR-008 |
| No tests for any `_download_geo_*` helper (network-mocked) | High | FR-008 |
| Failure encoded as ad-hoc note strings, not vocabulary | Medium | FR-005 |
| No `--dry-run` mode | Medium | FR-006 |
| No reproducibility bundle for Stage 00 runs | Medium | FR-007 |
| `_geo_series_prefix` correctness for GSE < 1000 unverified | Low | FR-008 edge case |
| Stale `.part` files not cleaned at startup | Low | FR-004 edge case |
| Duplicate cohort_id in manifest silently re-downloads | Low | FR-008 edge case |
| No runbook | Medium | FR-010 |

### 1.4 Existing test inventory for Stage 00

```
tests/unit/test_retrieval_geo_manifest.py   — 65 lines, 1 test, covers cmd_retrieval_geo_manifest only
```

`grep -ln "retrieval\|_download_geo\|cmd_retrieval" tests/` returns only the file above plus `tests/unit/test_audit_and_manifest_rules.py` (incidental mention, not a Stage 00 test).

**Target after this spec**: ≥ 9 tests (1 existing + 8 new per FR-008).

---

## 2. I/O Contracts (frozen)

These schemas are locked by this spec. Any change is a breaking change requiring a new spec.

### 2.1 Input: Discovery manifest

Path: passed via `--discovery-manifest`.
Format: TSV with header.

| Column | Type | Required | Notes |
|---|---|---|---|
| `cohort_id` | str | yes | Lowercase snake_case, often starts with `gse<id>_` |
| `accession` | str | yes | One or more accessions, separated by `;`, `,`, or whitespace. Supported prefixes: `GSE`, `GSM`, `GPL`, `SRP`, `SRX`, `SRR`, `PRJ`, `BIOPROJECT` |

Additional columns are allowed and ignored by Stage 00.

### 2.2 Output: Retrieval ledger

Path: `<out>/retrieval_ledger.tsv` for `cmd_retrieval_run`, or `<out>/../geo_full_retrieval_ledger.tsv` for `cmd_retrieval_geo_full`.

**Schema for `retrieval_ledger.tsv`** (FROZEN — order matters):

```
cohort_id              str   from manifest
input_accession        str   verbatim from manifest "accession" column
gse_id                 str   ; -joined GSE/GSM/GPL tokens
srp_id                 str   ; -joined SRP tokens
srx_id                 str   ; -joined SRX tokens
srr_id                 str   ; -joined SRR tokens
bioproject_id          str   ; -joined PRJ/BIOPROJECT tokens
source_db              enum  geo | sra | geo+sra | other
source_uri             str   computed by build_source_uri()
retrieval_status       enum  not_started | downloaded | partial | failed
retrieval_timestamp    str   ISO-8601 UTC, e.g. 2026-05-28T14:30:00Z
retrieval_note         str   human-readable; semicolon-separated tuples after this spec (see FR-005)
```

**Schema for `geo_full_retrieval_ledger.tsv`** (FROZEN):

```
cohort_id, gse_ids, sra_ids, retrieval_status, n_download_attempts, n_download_successes,
n_soft_files_downloaded, n_matrix_files_downloaded, n_suppl_files_downloaded,
n_runinfo_files_downloaded, retrieval_timestamp, retrieval_note
```

### 2.3 Output: Downloads tree

```
<out>/downloads/<cohort_id>/
├── <GSE>_family.soft.gz                  (Stage 00 produces)
├── <GSE>/matrix/<GSE>_series_matrix.txt.gz
├── <GSE>/suppl/<various files>
└── <SRA>_runinfo.csv
```

Filenames must be byte-identical to what NCBI serves (`_safe_remote_filename` strips URL encoding only).

### 2.4 Output: Reproducibility bundle (new in this spec)

```
<out>/reproducibility/
├── commands.sh         # exact CLI invocation
├── environment.yml     # `conda env export` or pip freeze
└── checksums.sha256    # sha256 over retrieval_ledger.tsv + every file in downloads/
```

### 2.5 Failure taxonomy (new in this spec, FR-005)

`ErrorClass` enum (str):

```
http_404            — HTTP 404 from NCBI
http_5xx            — HTTP 5xx (rate limit / NCBI outage)
http_other          — Any other HTTP error code
network_timeout     — urllib timeout (currently 120s)
empty_response      — body empty or fails sanity check (e.g. runinfo missing "Run,")
parse_error         — HTML link extraction failed
manifest_error      — input manifest row missing required columns
```

`retrieval_note` format after this spec, for any non-`downloaded` row:

```
<accession>:<file_kind>:<error_class>[:<detail>]; <accession>:...
```

Where `file_kind ∈ {soft, matrix, suppl, runinfo, listing}`.

### 2.6 Aim-spec schema (FR-012)

Path: `inputs/discovery/study_aim_query.yaml`. Loaded by `query/aim_spec.py` and JSON-schema validated at startup.

```yaml
# Versioned spec — change the version when semantics shift.
aim_spec_version: "1.0.0"
study_aim: pre_treatment_icb_response  # short slug used in query_run_id

include:
  organism: ["Homo sapiens"]
  assay:                 # canonical names; adapters expand to endpoint-specific synonyms
    - bulk_rnaseq
    - methylation_array
  sample_source:
    - tumor_tissue
  treatment_class:
    - anti_PD1
    - anti_PDL1
    - anti_CTLA4
    - ICB_combo
  treatment_agents:
    - pembrolizumab
    - nivolumab
    - atezolizumab
    - durvalumab
    - avelumab
    - ipilimumab
    - tremelimumab
  timing:
    - pre_treatment      # synonyms: baseline, screening, day0, prior_to_therapy
  outcome_signal:        # at least one must be detectable in metadata text
    - RECIST_response
    - durable_clinical_benefit
    - PFS_with_threshold
    - OS_with_threshold
  cancer_types: any      # explicit "any" — ICB approvals span many tumor types

exclude:
  assay:
    - scRNA_seq          # pseudobulk handling deferred; flag for future
  sample_source:
    - cell_line
    - PDX_only
  study_design:
    - in_vitro_only
    - non_human_model

filters:
  min_year: 2014         # ICB era starts roughly 2014
  min_samples: 8         # rough floor: ≥4 R + ≥4 NR

endpoints:               # active adapters for this run
  - ncbi_geo
  - ncbi_sra
  - arrayexpress
  - ena
  - recount3
  - omicsdi

scoring:
  required_rules: 3      # candidate must match ≥3 inclusion rules to appear
  weights:
    treatment_match: 3
    timing_match: 3
    outcome_match: 2
    assay_match: 2
    cancer_type_known: 1
```

### 2.7 Discovery candidates schema (FR-014, FROZEN)

Path: `<out>/discovery_candidates.tsv`. Order matters.

```
query_run_id                  str    isoformat-utc + random suffix; identifies the query invocation
endpoint                      enum   ncbi_geo | ncbi_sra | arrayexpress | ena | recount3 | omicsdi
endpoint_uid                  str    the endpoint's native identifier (e.g. GEO Series ID, SRP, E-MTAB-xxx)
canonical_accession           str    cross-walked to GEO accession when possible, else endpoint_uid
endpoint_seen                 str    ;-joined endpoints that returned the same canonical record (dedup)
title                         str    study title
summary                       str    study abstract / description (truncated to 4000 chars)
pmid                          str    ;-joined PubMed IDs if returned
omics_type                    str    transcriptomics | methylation | proteomics | metabolomics | mixed | unknown
n_samples_estimated           int    best-effort sample count from endpoint metadata
cancer_type_inferred          str    free-text; ;-joined if multiple
treatment_agents_inferred     str    ;-joined canonical agent names (mapped via synonym table)
timing_inferred               str    pre | post | on | mixed | unknown
match_score                   int    sum of matched-rule weights
matched_rules                 str    ;-joined rule names (e.g. "treatment_match;timing_match;outcome_match")
triage_status                 enum   new | already_in_manifest | already_excluded | out_of_scope | multi_omics_for_later | needs_review
endpoint_status               enum   ok | rate_limited | partial | unreachable
discovered_at                 str    ISO-8601 UTC
```

### 2.8 Manifest promotion log (FR-016, FROZEN)

Path: `inputs/discovery/manifest_promotion_log.tsv`. Append-only.

```
promotion_id          str    uuid4
query_run_id          str    links to the candidates file that sourced this row
candidate_endpoint    str    where it was found
cohort_id             str    the new discovery_manifest cohort_id (constructed at promotion time)
canonical_accession   str
match_score           int
promoted_at           str    ISO-8601 UTC
approving_user        str    git user.email if available, else "$USER"
source_candidates_file str   path to the candidates.tsv that was promoted from
```

---

### 2.9 Endpoint adapter contract (FR-013)

Each adapter implements:

```python
class Endpoint(Protocol):
    name: str                                                 # one of the enum values in § 2.7

    def render_query(self, aim: AimSpec) -> RenderedQuery:    # endpoint-specific syntax + URL(s)
        ...
    def execute(self, q: RenderedQuery) -> list[RawRecord]:   # HTTP, paginated, rate-limit-aware
        ...
    def parse(self, raws: list[RawRecord], aim: AimSpec) -> list[CandidateRecord]:
        # extracts title/summary/pmid/n_samples; infers omics_type, cancer_type, treatment_agents, timing
        ...
    def cache_key(self, q: RenderedQuery) -> str:             # for fixture replay in tests
        ...
```

**Adapter-specific notes:**

| Endpoint | Base URL | Search syntax | Rate limit | Notes |
|---|---|---|---|---|
| `ncbi_geo` | `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/` | `esearch.fcgi?db=gds&term=<expr>` then `esummary.fcgi?db=gds&id=...` | 3 req/s w/o key, 10 w/ `NCBI_API_KEY` | Use boolean field tags: `("Homo sapiens"[Organism]) AND (immune checkpoint OR pembrolizumab OR ...) AND (expression profiling by high throughput sequencing[DataSet Type])` |
| `ncbi_sra` | same | `esearch.fcgi?db=sra&term=<expr>` | same | Library strategy filter `RNA-Seq[Strategy] AND Homo sapiens[Organism]` |
| `arrayexpress` | `https://www.ebi.ac.uk/biostudies/api/v1/search` | `?type=Array Express&query=<text>&pageSize=...` | Polite use; 1 req/s default | Returns JSON with accession E-xxx-IDs |
| `ena` | `https://www.ebi.ac.uk/ena/portal/api/search` | `?result=read_study&query=<filters>&fields=...&format=json` | Polite use | Field-based query; library_strategy=RNA-Seq |
| `recount3` | `https://recount-opendata.s3.amazonaws.com/recount3/release/human/...` | Static metadata TSVs | N/A (static files) | Filter the published `metadata.csv` locally; no live query |
| `omicsdi` | `https://www.omicsdi.org/ws/dataset/search` | `?query=<text>&start=0&size=50&faceCount=20` | Polite use; ≤2 req/s | Federates GEO, SRA, ArrayExpress, ENA, PRIDE, MetaboLights, ExpressionAtlas, dbGaP (metadata only), EGA (metadata only), JPOST, MassIVE, BioModels, LINCS, ICGC. `omics_type` is in the response — use it directly. Spec: `https://www.omicsdi.org/ws/swagger-ui/index.html` |

## 3. Scientific Validity

### 3.1 What Stage 00 should retrieve, by science

For the thesis question (pre-treatment ICB R-vs-NR DE meta-analysis), Stage 00 must provide:

- **Sample-level metadata**: GEO SOFT family files carry GSM records with title, source_name, characteristics. This is the only reliable source of timing and response labels for many older GEO cohorts. **Required**.
- **Expression data**:
  - Pre-processed: GEO series matrix files (already-normalized expression in many cohorts).
  - Raw: GEO supplementary (often `*_raw_counts.tsv.gz` or per-sample files) + SRA-derived FASTQ for cohorts where supplementary is unusable.
- **Run metadata**: SRA runinfo CSV provides sample-to-run mapping needed when supplementary is absent.

### 3.2 Scientific risks of current implementation

1. **Series matrix can be wrong-or-empty**: Some GEO series have `*_series_matrix.txt.gz` containing only normalized log-ratios from microarrays misfiled as RNA-seq. Stage 00 does not detect this; downstream Stage 02 must. **Out of scope for this spec but noted in research for Spec 011 (Stage 02).**
2. **Supplementary can carry non-expression data**: methylation arrays, ChIP-seq peaks. Stage 00 downloads everything in `/suppl/`. Downstream stages filter. Acceptable as long as we know what arrived. **Bundling checksums (FR-007) makes this auditable.**
3. **SRA runinfo can be stale**: SRA mirrors lag. Empty-response detection (L760) covers the worst case but not "stale but valid" responses. **Low risk; not in scope.**
4. **No DOI/publication cross-check**: Stage 00 trusts the manifest. If a manifest accession is wrong, Stage 00 happily downloads the wrong cohort. **Out of scope — manifest curation is Spec 010 (Stage 01) territory.**

### 3.3 What this spec does NOT change scientifically

- Per user decision (2026-05-28): scientific gaps from Spec 007 are deferred. This spec preserves Stage 00 behavior; it does not, e.g., add a step to also fetch BioProject XML for richer metadata. Such additions are future spec material.

### 3.4 Reproducibility-as-science

For the thesis defense, "I can show every byte that entered my analysis came from a recorded URL on a recorded date" is itself a scientific-validity argument. FR-007 (checksums + commands + env snapshot) is the load-bearing piece — without it, no claim about downstream results is auditable.

### 3.5 Scientific validity of aim-driven discovery (FR-011..FR-017)

**What the query function is, scientifically:** A reproducible literature/data-search engine encoded as a versioned filter spec, replacing ad-hoc keyword searches that vary by curator and date.

**What it is not:** A curator. It does not decide which candidates enter the analysis. Promotion is manual and audited.

**False-positive risk:** Free-text metadata is noisy. "Checkpoint inhibitor" in an abstract does not imply tumor samples were profiled at baseline. Adapters use a synonym table for treatment agents and known timing keywords, but final eligibility is determined by Stage 01–03 metadata curation. The `match_score` is a triage signal, not eligibility.

**False-negative risk:** Older deposits use idiosyncratic vocabulary (e.g. "anti-CD279" for anti-PD-1, "MK-3475" for pembrolizumab). The synonym table in `aim_spec.py` is load-bearing; it must be extended over time. Every false negative discovered by hand should be added to the synonym table and a regression test added.

**Cross-endpoint dedup integrity:** GEO–SRA cross-references via SRP↔GSE mapping; ArrayExpress E-MTAB-IDs are unique; OmicsDI carries the `repository` field directly. Dedup happens before scoring so the same study is not counted twice toward `required_rules`.

**OmicsDI specific:** Federates more than RNA-seq. Methylation, proteomics, metabolomics datasets matching the ICB aim are preserved in the candidates file with `triage_status=multi_omics_for_later`. This is a forward-looking deposit: when spec_008+ methylation work begins, the candidates file is the starting roster, not a fresh search.

**No PHI / no controlled access:** Adapters only call open metadata endpoints. dbGaP / EGA records returned by OmicsDI are listed (metadata-only) but never trigger downloads; controlled-access study handling is out of pipeline scope.

**Reproducibility of the query itself:** Each query run emits `rendered_queries.json` (one record per endpoint with the exact URL and parameters used), `commands.sh` (the invocation), and optional cached HTTP responses. Two query runs on the same date with the same aim-spec and cached responses produce byte-identical candidates files (modulo the `query_run_id` and `discovered_at` columns).

---

## 4. References

- NCBI GEO FTP layout: `https://ftp.ncbi.nlm.nih.gov/geo/series/<SERIES_PREFIX>/<GSE>/{soft,matrix,suppl}/`
- NCBI SRA runinfo: `https://trace.ncbi.nlm.nih.gov/Traces/sra-db-be/runinfo?acc=<ACC>`
- NCBI EUtils: `https://www.ncbi.nlm.nih.gov/books/NBK25501/`; `gds` database docs `https://www.ncbi.nlm.nih.gov/books/NBK3837/`
- EBI ArrayExpress / BioStudies REST: `https://www.ebi.ac.uk/biostudies/help#api-v1`
- EBI ENA portal API: `https://www.ebi.ac.uk/ena/portal/api/`
- recount3 metadata: `https://rna.recount.bio/`
- OmicsDI REST: `https://www.omicsdi.org/ws/` (Swagger UI: `https://www.omicsdi.org/ws/swagger-ui/index.html`); paper: Perez-Riverol et al. 2017 (PMID 28604312)
- ClawBio reference for stage cycle pattern: `~/.claude/clawbio-reference/skills/rnaseq-de/SKILL.md` (reproducibility triad: `report.md` + `figures/` + `tables/` + `reproducibility/`).
