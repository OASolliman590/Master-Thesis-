# B-F1 Standards recheck

6 September 2026. Reviewed the updated **staged** changes against M1 `43efda19bff062a2e9e140fadd84ab32c88cee71` in the three released directories. Read the revised inspector, boundary regressions, real-fixture assertions, verification driver, run guide and four local receipts. Earlier report is preserved.

## Dispositions

1. **Output collision finding resolved.** `_atomic_write_json` now publishes with Windows `os.rename`, which refuses an existing destination, or POSIX `os.link`. Neither branch falls back to replacement. A completed temporary file is used and cleaned up; a competing destination produces an argument failure. The regression injects the collision at `fsync`, then checks the existing output bytes and absence of temporary artifacts. The documented E: hard-link limitation explains the platform branch without claiming AIU execution.

2. **Checksum/snapshot finding resolved.** `run_inspect` acquires `source_bytes` once. Compression detection, byte count, SHA-256 and decoding all consume that object. The regression changes the source after the read, verifies that the mutation occurred, and asserts the summary describes the original acquired snapshot.

3. **Oracle drift concern addressed.** Real-fixture tests now compare every expected JSON field and cross-check fixture paths/hashes against the manifest. CPC `value_columns` is emitted. Some metadata remains duplicated, but consistency is checked; no further refactoring is required for this bounded ticket.

## Evidence and limits

The new verification driver uses subprocess argument arrays, bounded timeouts and a fresh output directory; it records interpreter/platform, commands, exit status and source/code/output hashes. I independently compared the receipt's five code/contract hashes and four summary hashes against the **staged blobs**: zero mismatches. All four recorded checks have exit 0 and matching expected fields.

Root reports 19 tests passed in 7.638 seconds on local Python 3.12. I did not rerun tests or perform network access. AIU/Python 3.11 execution remains pending; the guide and receipts state that limitation. These are format checks, not evidence that Paper B's scientific gates passed.

**Unresolved substantive Standards findings: 0.** The two earlier P2 findings are closed for this staged revision. No new mandatory or optional findings.
