# B-F1 Independent Opus Code Review

**Reviewer:** Claude Opus 4.6 (Thinking), static file-reading review  
**Date:** 6 September 2026  
**Base commit:** `43efda19bff062a2e9e140fadd84ab32c88cee71` (M1)  
**Candidate:** Nine staged NEW files under `tools/b_formats/`, `tests/b_formats/`, `docs/validation/B_formats/`  
**Method:** Static line-by-line inspection of all candidate and provenance files. No test execution by this reviewer; root's documented 14-test pass (Python 3.12, `BF1_TEST_TMP_ROOT`) is the actual test evidence. AIU 3.11 untested (SSH timeout). WinError 5 in default temp cleanup is recorded, not counted as pass.

---

## Scope

This review covers format-only inspection code for four TSV formats. It does **not** evaluate biological correctness, scoring, normalization, patient linkage, or any analytical pipeline. Synthetic fixtures validate parser mechanics, not biology.

---

## Findings

### BLOCKER Findings

#### B1. Stale variable `idx` in STAR blank-record error message

- **File/Line:** [`__main__.py:183`](file:///E:/Master_Thesis/master-thesis/tools/b_formats/__main__.py#L183)
- **Code:** `raise Failure(f"row={idx+1} field=record reason=blank record", EXIT_SCHEMA)`
- **Trigger:** An embedded blank line within the data rows of a STAR expression file (after the header and comment section).
- **Condition:** The variable `idx` is the loop variable from the _header-scanning_ loop at L149 (`for idx, raw_line in enumerate(lines, start=1)`). The data-row loop at L180 uses `row_no` as its loop variable. When a blank record is hit during data parsing, the error message reports `row={idx+1}` — the line number of the _last comment/header line scanned_, not the actual offending data row.
- **Expected:** `raise Failure(f"row={row_no} field=record reason=blank record", EXIT_SCHEMA)` — must use `row_no`.
- **Actual:** Reports wrong row number, potentially off by dozens of lines. Diagnostic is misleading.
- **Severity:** **Blocker.** The contract requires meaningful diagnostics with correct row references. A blank row embedded in a 60,664-row real file would be nearly impossible to locate from the wrong row number. This is a correctness bug, not cosmetic.
- **Test coverage:** No test currently exercises an embedded blank row in a STAR expression file. The `test_blank_records_rejected` test uses `tcga-methylation-beta` format only.
- **Fix:** Change `idx+1` to `row_no` on L183.

---

#### B2. Detection-P values validated with `strict_range=True` (beta [0,1] constraint)

- **File/Line:** [`__main__.py:456-461`](file:///E:/Master_Thesis/master-thesis/tools/b_formats/__main__.py#L456-L461)
- **Code:** `_parse_na_and_float(raw_value, row=row_idx, field=raw_name, strict_range=True)`
- **Trigger:** Any CPC methylation detection p-value.
- **Condition:** `strict_range=True` enforces `0.0 <= value <= 1.0`. While p-values are always in [0,1], this is coincidental — the range check was designed for beta methylation values. The loop iterates _all_ fields starting from index 1 with a single `strict_range=True` call, meaning both beta and detection-P columns share the beta range constraint.
- **Expected behaviour vs actual:** For well-formed data where detection p-values are always in [0,1], this produces correct results. The issue is that the error message says `"reason=beta value outside [0, 1]"` (L127) even for a detection-P column, which is a misleading diagnostic.
- **Severity:** **Correction** (downgraded from blocker). The range constraint is factually valid for both field types. The diagnostic label is misleading but would not reject correct data or accept incorrect data.
- **Fix:** Either pass `strict_range` only for beta columns (odd field indices) and a separate p-value-appropriate validation for detection columns, or at minimum customize the error message by field type.

---

#### B3. TOCTOU race between output-exists check and atomic write

- **File/Line:** [`__main__.py:94-110`](file:///E:/Master_Thesis/master-thesis/tools/b_formats/__main__.py#L94-L110) (check) and [`__main__.py:549`](file:///E:/Master_Thesis/master-thesis/tools/b_formats/__main__.py#L549) (write via `os.replace`)
- **Trigger:** Concurrent invocations or an external process creating the output file between the `_validate_output_path` check (L96-106) and `os.replace` (L549).
- **Condition:** `_validate_output_path` checks `output_path.exists()` early in `run_inspect`. The full file is hashed, parsed, and then the summary is atomically written via `os.replace`. On Windows, `os.replace` will silently overwrite an existing file; on POSIX, likewise. If the output is created between validation and write, the tool overwrites it silently.
- **Expected:** Contract says "output path must not already exist"; an existing output should be rejected.
- **Actual:** The check is at invocation time; the write is unbounded time later. `os.replace` will succeed even if the path appeared between check and write.
- **Severity:** **Correction.** In the single-process test/CLI use case this is extremely unlikely. However, the contract explicitly demands existing-output protection. A narrower mitigation: use `O_CREAT | O_EXCL` for the final rename target, or check again immediately before replace.
- **Scope concern:** The atomic-write pattern itself is correct (write temp, fsync, replace). The issue is _only_ the gap between early check and late replace.
- **Fix:** Either (a) use `os.link(temp, target)` which fails if target exists (POSIX only), or (b) re-check `output_path.exists()` immediately before `os.replace` and raise `EXIT_IO` if it appeared, accepting the remaining narrower race. Document the residual window.

---

#### B4. Double-open source integrity: hash and read are separate opens

- **File/Line:** [`__main__.py:582-583`](file:///E:/Master_Thesis/master-thesis/tools/b_formats/__main__.py#L582-L583)
- **Code:**
  ```python
  actual_sha256 = _assert_sha(input_path, source_sha256)  # opens and reads for hash
  lines = _load_lines(input_path)                           # opens and reads again for parse
  ```
- **Trigger:** Source file modified (even partially) between the hash read and the parse read.
- **Condition:** `_sha256_of_file` at L62-67 opens the file in binary mode, reads it fully, and closes. Then `_load_lines` at L494-500 reopens the same path in text mode and reads again. If the file is modified between these two operations, the tool certifies a hash that does not correspond to the data it parsed.
- **Expected:** The hash must cover exactly the bytes that are parsed.
- **Actual:** Two independent opens; the file could change between them.
- **Severity:** **Correction.** In the intended single-user CLI use case with read-only source fixtures, this race is unlikely. But the contract says "actual local input bytes before parsing" — the tool does check bytes before parsing, just not the _same_ read. A single-read approach (read bytes → hash → decode → parse) would be strictly correct.
- **Fix:** Read the file once in binary mode, compute SHA256 on those bytes, then decode to text and split into lines. This eliminates the race entirely and is simpler.

---

### CORRECTION Findings

#### C1. `_normalize_fields` does not reject `\r` embedded mid-line

- **File/Line:** [`__main__.py:139-140`](file:///E:/Master_Thesis/master-thesis/tools/b_formats/__main__.py#L139-L140)
- **Code:** `return line.rstrip("\r\n").split("\t")`
- **Condition:** `_load_lines` at L496 uses `str.splitlines()`, which splits on `\r\n`, `\r`, and `\n`. Then `_normalize_fields` strips trailing `\r\n`. However, `splitlines()` already handles line endings, so `rstrip("\r\n")` only catches a scenario where `splitlines()` left a trailing `\r` — which it does not. This is defensive but harmless.
- **A concern:** A bare `\r` _within_ a field value (not at line boundaries) would survive as part of a field value. The tool does not check for embedded control characters. This is minor — the source TSVs are known UTF-8 text — but worth documenting.
- **Severity:** **Optional.** No known trigger in the four authorized fixtures.

#### C2. CPC methylation header-repair triggers too broadly

- **File/Line:** [`__main__.py:370-384`](file:///E:/Master_Thesis/master-thesis/tools/b_formats/__main__.py#L370-L384)
- **Code:** Header repair is triggered if `raw_header[0] != "probe_id"` and the raw width is even (L378).
- **Trigger:** Any CPC methylation input whose first header field is not literally `"probe_id"` and whose raw header has even width.
- **Condition:** The contract says "omitted leading probe label repaired only under documented paired CPCG assay names." The code checks even-width (which is consistent with a missing probe_id making the width even), and then validates that all field pairs match the `CPCGdddd_repd` / `CPCGdddd_repd_Dectection_Pval` pattern (L398-426). So the repair is effectively gated by the CPCG pair validation.
- **Assessment:** The pair validation at L420-426 ensures only documented patterns trigger repair. The repair logic is **acceptable** as implemented — it repairs the header, then validates every pair. A file with a non-CPCG first field and even width would get the repair but then fail pair validation. This is **correct behavior**.
- **Severity:** **No action needed** — the concern in the brief is addressed by the CPCG regex gate.

#### C3. Non-summary STAR gene rows: `gene_name`/`gene_type` not validated

- **File/Line:** [`__main__.py:216-226`](file:///E:/Master_Thesis/master-thesis/tools/b_formats/__main__.py#L216-L226)
- **Condition:** For non-N_ rows, only `gene_id` (fields[0]) is required nonempty. Fields[1] (`gene_name`) and fields[2] (`gene_type`) are neither checked nor reported.
- **Contract relevance:** The contract says "identify named columns and four N_ summary rows separately." The tool identifies the header columns and counts. It does not validate that every gene_name/gene_type is populated, which is correct — the STAR format has empty gene_name for some entries (e.g., novel transcripts).
- **Severity:** **No action.** This is correct behavior for the format.

#### C4. `real_summaries_expected.json` omits `value_columns` for TCGA methylation

- **File/Line:** [`real_summaries_expected.json`](file:///E:/Master_Thesis/master-thesis/docs/validation/B_formats/real_summaries_expected.json)
- **Condition:** The CPC methylation entry includes `"value_columns": 788` (L33), but the TCGA methylation entry includes `"value_columns": 1` only in the tool output (via `_inspect_tcga_methylation` L292), not in this expected-values file. The expected-values JSON has `"sample_count": 1` for TCGA methylation.
- **Assessment:** The expected-values file is a contract reference for test validation; it uses format-specific fields. The TCGA methylation format has a single value column, so `sample_count: 1` is correct. The CPC methylation `value_columns: 788` is informational.
- **Severity:** **Optional.** Consider adding `value_columns` consistently across formats in the expected file, or explicitly noting the asymmetry.

#### C5. Synthetic CPC methylation fixture has 5 fields per data row but header implies 4+1=5

- **File/Line:** [`synthetic_cpc_methylation.tsv`](file:///E:/Master_Thesis/master-thesis/tests/b_formats/fixtures/synthetic_cpc_methylation.tsv)
- **Content:**
  ```
  CPCG0001_rep1\tCPCG0001_rep1_Dectection_Pval\tCPCG0002_rep2\tCPCG0002_rep2_Dectection_Pval
  cg0001\t0.2\t0.1\t0.3000000001\t0
  cg0002\t0.9\t0.0\tNA\t0.4
  ```
- **Analysis:** The header has 4 fields. Header repair adds `probe_id` → 5 fields. Data rows have 5 fields each (`probe_id`, then 4 values). This is consistent.
- **Concern:** `0.3000000001` is a valid beta value (between 0 and 1). This is fine.
- **Severity:** **No action.** Fixture is correct.

#### C6. Synthetic STAR fixture: summary row has populated normalized fields

- **File/Line:** [`synthetic_tcga_star.tsv`](file:///E:/Master_Thesis/master-thesis/tests/b_formats/fixtures/synthetic_tcga_star.tsv)
- **Content (row 2):** `N_unmapped\t\t\t1730\t1730\t1730\t1.2\t3.4\t5.6`
- **Condition:** The initial root review noted: "all four N_ summary records have empty gene_name/gene_type and empty normalized-expression fields." The real STAR file has summary rows where TPM/FPKM/FPKM_UQ are empty strings, but count fields (unstranded, stranded_first, stranded_second) have values.
- **In the synthetic fixture:** The summary row has values in ALL six numeric columns (1730, 1730, 1730, 1.2, 3.4, 5.6) — none are structural-empty. This means `summary_structural_missing_count` would be 0 for this fixture, while the real file has 12 structural empties (4 N_ rows × 3 normalized columns).
- **Assessment:** The synthetic fixture does not faithfully replicate the structural-empty pattern of the real data. The `test_synthetic_known_oracles` test does not assert `summary_structural_missing_count`, so it passes regardless. The _real format test_ correctly validates the actual count.
- **Severity:** **Correction.** The synthetic fixture should have empty strings in the tpm/fpkm columns for N_ rows to exercise the structural-missing counting path. Currently, the structural-missing code path is only exercised by the real fixture test, not by any synthetic-only test. If real fixtures are unavailable (e.g., on a different machine), this path is untested.
- **Fix:** Change the synthetic N_ row to: `N_unmapped\t\t\t1730\t1730\t1730\t\t\t` to match the real pattern.

---

### OPTIONAL / Design Preference Findings

#### O1. `test_repeated_runs_use_fresh_outputs` excludes `actual_bytes` from comparison

- **File/Line:** [`test_bf1_cli.py:603-606`](file:///E:/Master_Thesis/master-thesis/tests/b_formats/test_bf1_cli.py#L603-L606)
- **Code:** `{k: v for k, v in first.items() if k != "actual_bytes"}`
- **Condition:** Both runs use the same input file, so `actual_bytes` should be identical. The exclusion is unnecessary but harmless — perhaps a precaution against filesystem metadata differences. 
- **Severity:** **Optional.** Including `actual_bytes` in the comparison would be a stronger test.

#### O2. No test for STAR expression with an embedded blank row

- **File/Line:** [`test_bf1_cli.py`](file:///E:/Master_Thesis/master-thesis/tests/b_formats/test_bf1_cli.py) — missing test.
- **Condition:** The `test_blank_records_rejected` test (L483-500) covers only `tcga-methylation-beta`. Given blocker B1 (wrong row number in STAR blank-record error), a STAR-specific blank-record test would have caught the stale-`idx` bug.
- **Severity:** **Correction.** Add a STAR-specific embedded blank row test. This also serves as the regression test for the B1 fix.

#### O3. No test for existing-output file with path alias (symlink)

- **File/Line:** [`test_bf1_cli.py`](file:///E:/Master_Thesis/master-thesis/tests/b_formats/test_bf1_cli.py) — missing test.
- **Condition:** `_validate_output_path` uses `samefile` (L97) to detect input/output aliasing. No test creates a symlink or hardlink to verify that the alias check works through indirection. On Windows, symlink creation may require privileges, so this is legitimately difficult to test portably.
- **Severity:** **Optional.** Document the symlink limitation; consider testing on POSIX CI.

#### O4. `fixture_manifest.json` field inconsistency

- **File/Line:** [`fixture_manifest.json`](file:///E:/Master_Thesis/master-thesis/docs/validation/B_formats/fixture_manifest.json)
- **Condition:** CPC expression entry has `"parent_compressed_bytes_read": 24000000` (L22), while CPC methylation has `"parent_compressed_bytes": 256000` (L30). The field names differ: `parent_compressed_bytes_read` vs `parent_compressed_bytes`. Both refer to the number of compressed bytes read from the remote source.
- **Severity:** **Correction.** Normalize to one field name for consistency.
- **Fix:** Use `parent_compressed_bytes_read` consistently, since that matches what `fetch_more.py` actually does (reads the first N bytes).

---

## Provenance Cross-Check

### Fixture manifest vs. fetch_log.json

| Format | Manifest SHA | fetch_log SHA | Match |
|--------|-------------|---------------|-------|
| TCGA STAR expression | `8339cb0b...` | `8339cb0b...` (L13) | ✅ |
| TCGA methylation | `11d9fa63...` | `11d9fa63...` (L27) | ✅ |
| CPC expression prefix | `5a9aaaac...` (local TSV) | Not in fetch_log (only compressed prefix logged) | ⚠️ See below |
| CPC methylation prefix | `d2539ed6...` (local TSV) | Not in fetch_log (only compressed prefix logged) | ⚠️ See below |
| CPC expression compressed prefix | `4839b8d2...` | `4839b8d2...` (L148) | ✅ |
| CPC methylation compressed prefix | `a34821f3...` | `a34821f3...` (L123) | ✅ |

> [!NOTE]
> The CPC prefix TSV hashes (`5a9aaaac...` and `d2539ed6...`) are local-decompressed hashes, not logged in `fetch_log.json`. This is correct per contract: "any selected derived TSV uses a separately recorded local SHA and parent provenance." The parent compressed-prefix hashes cross-reference correctly. The local TSV hashes are recorded in the test code and fixture manifest and must match the actual files on disk (verified by root's 14-test pass).

### CPC compressed prefix sizes

- `fixture_manifest.json` L30: CPC methylation `"parent_compressed_bytes": 256000`
- `fetch_log.json` L122: `"bytes": 256000` for `GSE107298_processed_prefix.gzpart`
- `fetch_more.py` L24: `b=r.read(256000)` — reads exactly 256,000 bytes
- `fixture_manifest.json` L22: CPC expression `"parent_compressed_bytes_read": 24000000`
- `fetch_log.json` L147: `"compressed_bytes_read": 24000000` — this is a **different fetch** (the 24 MB target-check audit)

> [!IMPORTANT]
> The CPC expression manifest entry records the 24 MB audit's compressed prefix hash (`4839b8d2...`), while the original 256 KB fetch (L129-136) has a _different_ compressed prefix hash (`ccb85485...`). The initial 256 KB prefix produced 195 decompressed lines; the 24 MB audit produced 18,277 rows. The fixture manifest correctly points to the 24 MB audit as the parent. The 256 KB fetch was an earlier smaller prefix. **This is not an error** — the retained TSV prefix (195 lines = header + 194 data rows) was decompressed from the 24 MB fetch, not from the 256 KB fetch. The manifest correctly records `parent_compressed_bytes_read: 24000000` and the 24 MB SHA.

### Decompressed line counts

- CPC expression: `fetch_log.json` L134: `"decompressed_complete_lines": 195` from 256 KB → matches `row_count: 194` (header + 194 data) ✅
- CPC methylation: `fetch_log.json` L126: `"decompressed_complete_lines": 78` from 256 KB → matches `row_count: 77` (header + 77 data) ✅

> [!WARNING]
> Wait — the CPC expression prefix was cut from the 24 MB fetch, not the 256 KB fetch. The 256 KB fetch also produced 195 lines. This coincidence needs care: the retained TSV could be from either fetch. The **SHA differs** between the two compressed prefixes, and the TSV SHA is `5a9aaaac...` which must match the file on disk. The manifest's provenance chain uses the 24 MB parent, which is the correct one for the full coverage audit. The 256 KB prefix would have the same first 195 lines (assuming the compressed stream is deterministic), so the decompressed TSV would be byte-identical. This is consistent but should be explicitly documented.

---

## Missing Coverage and Honest Status

### Tested (by root's 14-test run, Python 3.12)
- All four synthetic fixture happy paths
- All four real fixture paths (TCGA STAR, TCGA methylation, CPC expression, CPC methylation)
- Malformed SHA, wrong format name
- Hash mismatch
- Wrong column width, duplicate identifiers
- Invalid numeric, out-of-range beta
- Swapped CPC methylation columns
- Wrong-width prefix row
- Compressed input rejection
- Missing final newline accepted
- Input/output identity and stale output
- Empty and header-only inputs
- Blank records (methylation only)
- CPC expression malformed schema and duplicate columns
- CPC methylation duplicate pairs and schema
- Repeated runs produce same summary

### Not tested
- STAR blank-record rejection (would expose B1)
- Symlink/alias input-output detection
- AIU Python 3.11 (SSH timeout)
- Concurrent output creation (TOCTOU)
- Structural-missing count in synthetic STAR (only real fixture exercises it)
- Extremely large files / memory limits
- Non-UTF-8 encoded input with .tsv extension (only gzip magic checked)
- Filename-only `.gz` extension rejection (code handles at L72, test at L360-374 uses gzip magic bytes instead of extension)

> [!NOTE]
> The filename extension rejection (L72) IS covered by the compressed input test, since `_forbidden_input` checks extension first, then magic bytes. However, the test at L363 creates a file named `compressed_input.tsv` with gzip magic, so it tests magic-byte detection, not extension detection. A file named `data.gz` with non-gzip content would hit the extension check. This path is untested but low-risk.

---

## Summary Table

| ID | Severity | File | Line(s) | Issue |
|----|----------|------|---------|-------|
| B1 | **Blocker** | `__main__.py` | 183 | Stale `idx` variable in STAR blank-row error; reports wrong row number |
| B2 | Correction | `__main__.py` | 456-461, 127 | Detection-P uses beta error message; misleading diagnostic |
| B3 | Correction | `__main__.py` | 94-110, 549 | TOCTOU race between output-exists check and atomic write |
| B4 | Correction | `__main__.py` | 582-583 | Hash and parse are separate file opens; content could change between |
| C6 | Correction | `synthetic_tcga_star.tsv` | row 2 | N_ row has populated normalized fields; structural-missing path untested by synthetic |
| O2 | Correction | `test_bf1_cli.py` | (missing) | No STAR-specific blank-row test |
| O4 | Correction | `fixture_manifest.json` | 22, 30 | Inconsistent compressed-bytes field names |
| C1 | Optional | `__main__.py` | 139-140 | Embedded `\r` not rejected |
| O1 | Optional | `test_bf1_cli.py` | 603-606 | `actual_bytes` unnecessarily excluded from repeat comparison |
| O3 | Optional | `test_bf1_cli.py` | (missing) | No symlink/alias test |

---

## Verdict

> [!CAUTION]
> **Changes required before reviewed WIP publication.**

**B1 is a blocker.** The stale `idx` variable produces wrong row numbers in STAR blank-row diagnostics. This is a one-line fix (`idx+1` → `row_no` at L183), plus a new test case. No other finding blocks publication.

**B3 and B4** (TOCTOU and double-open) are corrections that should be addressed but are not blocking given the single-process CLI context. They represent theoretical integrity gaps that the contract aspires to close. The single-read fix for B4 is simple and improves both correctness and performance.

**C6 and O2** (synthetic fixture and missing test) should be addressed together with B1 — the STAR blank-row test both catches B1 and covers the missing case.

**O4** (manifest field naming) is a documentation consistency fix.

**AIU Python 3.11 remains mandatory** before any milestone label beyond "reviewed WIP." The 14-test local pass on Python 3.12 establishes local format correctness but does not substitute for the declared AIU target runtime.

### Required actions (bounded to B-F1 scope):
1. Fix L183: `idx+1` → `row_no`
2. Add STAR blank-row test to `test_bf1_cli.py`
3. Fix synthetic STAR N_ row to have empty normalized fields
4. Recommend (not block): single-read hash+parse, manifest field normalization

After these fixes and re-passing the test suite (including the new STAR blank-row test): **ready for reviewed WIP publication pending AIU 3.11 confirmation.** Not a completed/validated milestone.
