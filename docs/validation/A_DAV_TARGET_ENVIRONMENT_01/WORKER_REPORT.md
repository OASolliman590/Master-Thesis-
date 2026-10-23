# Luna worker report

Status: **TARGET_ENVIRONMENT_SOFTWARE_ACCEPTANCE_PASSED**. The local boundary checks and the subsequent isolated AIU target run are recorded separately below. The worker did not install packages or commit. The parent prepared the isolated pinned virtual environment; no shared environment changed. No source data or biology was used.

`runner.py` expects the fixed payload allowlist of 44 files: 18 named runtime modules, seven tests under `tests/a_dav_implementation/`, 17 frozen schemas, `tools/a_dav/requirements-synthetic.txt`, and `runner.py`. `ALLOWLIST_MANIFEST.json` has exactly the requested `classification`, `base_commit`, and `files` fields. The runner refuses missing, changed, extra, symlinked, unsafe, duplicate, or noncanonical members before starting a child process. It confirms the copied driver matches the executing bytes and records member hashes before and after execution.

The driver atomically writes a durable started and terminal `status.json`, records constrained OS/Python/locale/timezone/dependency facts, and runs the full transferred suite followed by fresh and same-destination resume demo commands. It records each child command and exit code and saves stdout/stderr in separate logs. The child environment disables bytecode and pytest plugin autoload, sets UTC, and caps OpenBLAS, OMP, MKL, NumExpr, VecLib and BLIS threads at one. Pytest/jsonschema must be installed at their pinned versions; missing and mismatched versions produce `BLOCKED` with `REQUIRED_DEPENDENCY_UNAVAILABLE` and `DEPENDENCY_VERSION_MISMATCH`, respectively, before any child starts. Acceptance requires successful stages, an exact four-file freeze bundle with matching member hashes, false actual flags, an allowlisted count-free public summary, matching fresh/resume summaries, unchanged bundle hashes, and a post-run payload hash match. Symlinked freeze roots or members fail before being read. Any failure leaves target software acceptance false and records the failing stage. Output must be a new empty directory outside the payload.

**RED/GREEN:** the first focused run exposed three failures in the runner/fixture handshake; I corrected copied-runner identity validation and made the fixture carry the pinned synthetic requirements content. After the parent review, I added thread caps, blocked dependency preflight, explicit dependency version checks, symlink-safe bundle inspection, and summary rejection tests. Final focused test command passed **14 tests** (`1.16 s`; [log](worker-local-tests.log)). Strict offline mypy 1.18.2 passed cleanly ([log](worker-mypy.log)). The focused tests cover traversal, symlink, missing/changed/extra members, failed test-stage rejection, false flags, fresh/resume summary mismatch, missing and mismatched dependencies, thread caps, summary counts/identifiers, symlink bundle rejection and successful acceptance through injected child processes. Stale code/config/output invalidation remains covered by the separately transferred DAV suite; that suite was not run in this worker environment.

The exact prescribed local typecheck command was used:

```text
UV_CACHE_DIR=/private/tmp/dav-uv-cache UV_TOOL_DIR=/private/tmp/dav-uv-tools uv tool run --offline --from mypy==1.18.2 mypy --strict --explicit-package-bases --ignore-missing-imports --follow-imports=silent docs/validation/A_DAV_TARGET_ENVIRONMENT_01/runner.py
```

Current hashes:

| File | Bytes | SHA-256 |
|---|---:|---|
| `runner.py` | 17,112 | `1ebe18b887a0a99573c6dcb07d6a5e96ac7471d4650aeb2319456137f6cbcc53` |
| `test_runner.py` | 9,157 | `04c3476f53dc68822e1394d3c5d2599b4dda86443ebf5b6b274658cf09f74c37` |

At the time of the original local boundary-check report, target-environment software acceptance was **NOT_RUN** pending a verified isolated target path. The subsequent target run below supersedes that interim status. External source/authentication/scientific/statistical gates remain **NOT_RUN** regardless of synthetic software results.

## Subsequent AIU target run

After the parent verified a fresh isolated payload and pinned private environment, I launched the driver once with PID **2760066**. The exact launch record is [worker-remote-launch.json](worker-remote-launch.json); the copied terminal receipt is [worker-remote-status.json](worker-remote-status.json). The full-suite output is [worker-remote-tests.stdout.log](worker-remote-tests.stdout.log), with an empty stderr log. Fresh and resume stdout/stderr, runner stdout/stderr, and the PID are also copied into this packet.

The target receipt is **PASSED**: `target_environment_software_acceptance=true`; the 255-test transferred `tests/a_dav_implementation/` suite passed in 34.82 seconds; both fresh and same-directory resume demo commands exited 0; the four bundle hashes remained stable; and the count-free public summaries matched. The receipt records Linux x86_64, Python 3.11.16, pytest 9.1.1, jsonschema 4.26.0, mypy 1.18.2, locale C.UTF-8, and the target timezone. `real_source_data_used`, `analysis_ready`, `source_admission`, `statistical_release`, `biological_analysis_executed`, and `frozen_specs_changed` are all false. The runner PID has completed.

This closes only the bounded synthetic software target-environment gate. External source, authentication, scientific, and statistical gates remain **NOT_RUN**. The parent independently checked the target payload hashes and ran its own typecheck; those parent-owned receipts remain separate.

The parent's independent artifact inspection found the canonical `release_draft` is `READY_FOR_REVIEW`, with `evidence_status=SYNTHETIC`, `software_gate=PASS`, `data_gate=NOT_RUN`, `statistical_gate=NOT_RUN`, empty admitted data, and blocked reasons for actual-source and statistical requirements. This matches the frozen release schema; the canonical release draft is not `BLOCKED_UNKNOWN` (that status applies to the admission and matrix-build drafts).

Target evidence hashes:

| File | Bytes | SHA-256 |
|---|---:|---|
| `worker-remote-launch.json` | 1,200 | `51b9f1dc0941c8dbe92f29e42bde3be9758632d9f59ddf661bbc1f81f0eae361` |
| `worker-remote-status.json` | 11,207 | `0fe4216a49add618bf138a8532492dd70692259e650a1eb5134f40de2b3f3ff4` |
| `worker-remote-tests.stdout.log` | 341 | `2a4bfe7afa0722d8b0eafa769b7b63d5b8f0a608854bb8a420698dc88d155cd4` |

Parent formatting note: removed one extra blank line at the end of the boundary test file after review; no test behavior changed. The hash table reflects the final file. The parent reran all 14 boundary tests on these final bytes. Target runner and payload bytes did not change.
