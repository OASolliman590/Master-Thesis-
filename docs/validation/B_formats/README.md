# B-F1 format inspection

This tool checks the four audited file formats and their actual byte checksums. It does not normalize data, select probes/genes, join patients, compute scores or validate biological claims. Python3.11 standard library is the target; local Windows Python3.12 is separately recorded. AIU execution remains pending until a verified run receipt exists.

From the repository root:

```sh
python -m tools.b_formats inspect --format tcga-methylation-beta --input /path/to/input.tsv --source-sha256 ACTUAL_64_HEX_SHA --completeness full --output /path/to/new-summary.json
python -m unittest discover -s tests/b_formats -v
python docs/validation/B_formats/verify_real.py --output-dir /path/to/new-format-check-run
```

Use `bounded-prefix` for the two retained CPC prefixes. Supported formats are `tcga-star-expression`, `tcga-methylation-beta`, `cpc-expression` and `cpc-methylation`. A complete final record without an ending newline is accepted. A valid prefix's syntax cannot prove full remote-object completeness. `source_sha256` identifies the supplied artifact, not an uninspected larger remote matrix.

Windows sandbox sessions may need a writable test directory:

```powershell
$env:BF1_TEST_TMP_ROOT='E:/Master_Thesis/planning/delegation_runs/bf1_test_tmp'
New-Item -ItemType Directory -Path $env:BF1_TEST_TMP_ROOT -Force | Out-Null
python -m unittest discover -s tests/b_formats -v
```

On AIU, use `/home/omics/miniforge3/envs/omics-py/bin/python`. The normal temporary directory can be used if writable; alternatively set `BF1_TEST_TMP_ROOT` to an existing directory in the run root. Do not relaunch a remote run whose state is unknown after a VPN interruption. No source retrieval or environment installation occurs in these commands.

## Fixtures and provenance

`fixture_manifest.json` supplies local paths, source URLs and actual TSV SHA256 values. Real source tables stay outside Git under `docs/research/B_readiness/`; the full single-specimen TCGA examples and bounded CPC prefixes were already acquired. A fresh checkout requires those authorized fixtures to be restored or retrieved with their exact source/checksum and scope. Missing fixtures must fail the real-format test, not silently skip it.

Both CPC retained prefixes derive from their own256,000-byte compressed prefixes. Reproduce the existing `fetch_more.py` derivation: gzip-mode zlib decompression capped at2,000,000 output bytes, then keep through the last complete LF. That yields626,448 methylation TSV bytes and557,800 expression TSV bytes. The expression fixture's compressed parent SHA is `ccb85485c521a3e02d8fd0d9edb5e15f096d9726a486da67f2e24e24b4b7099c`; the later24MB target check is a different audit. Local re-derivation matched both retained TSVs byte-for-byte.

`real_summaries_expected.json` contains reviewed count/schema expectations. The suite compares all its fields and checks fixture paths/hashes against the manifest. `verify_real.py` writes actual format summaries, exact commands/exit status, interpreter/platform information and code/input/output hashes into a fresh run directory. Expected JSON is an oracle, not evidence that a run happened. Never overwrite a prior run to make it appear current.

## Integrity and failure contract

The CLI reads one immutable byte snapshot, hashes that snapshot, then decodes/parses the same bytes. A later source modification cannot silently change what that hash attests. The current bounded examples are held in memory; this is not a streaming whole-cohort loader.

Existing output paths, including aliases, are refused. The complete temporary JSON is flushed before publication. Windows uses `os.rename`, which refuses an existing destination; POSIX uses `os.link` then removes the temporary name. A competing output created after the initial check is preserved. Unsupported filesystem operations fail as I/O errors; there is no overwriting fallback. Python supports hard links on Windows too, but this project's mounted E: returned WinError1 for a hard-link probe, hence the Windows rename path. These operations provide publication integrity; directory-level crash durability and hostile directory replacement are not certified. [Python3.11 filesystem APIs](https://docs.python.org/3.11/library/os.html#os.rename), [byte snapshot API](https://docs.python.org/3.11/library/pathlib.html#pathlib.Path.read_bytes).

Exit0 means a new completed summary;2 means invalid arguments or an existing/aliased output;3 means checksum/schema failure;4 means I/O failure. Failures never make an old output a success. Source IDs and literal NA are retained as identifiers/missing classifications; numeric assay values are not exported or logged. STAR's recognized N_ records have separately counted structural normalized-field absence, while their count fields must be numeric/NA. Beta and detection-P counts are separate. Patient-code counts do not establish independent patient N.

Synthetic tests exercise software invariants. Two deterministic CLI regressions inject source replacement and output collision at filesystem boundaries, without replacing the parser or its internal collaborators. They showed the prior failures before the fixes. Local passes do not substitute for AIU/Python3.11 validation or paper-level scientific gates.
