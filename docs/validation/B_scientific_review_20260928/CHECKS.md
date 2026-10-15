# Documentation verification receipt

Scope: newly written proposed-review documents and candidate manifest only. No application tests, patient analyses or AIU execution.

Actual local command: `python /mnt/data/check_b_revision.py` using Python 3.13.5. The first run on 28 September 2026 passed five check groups: 15 exact local document payloads, 20 unique schema-valid candidate records, 19 resolving internal relative links, only new proposed-review paths, and proposal labels. Later additions receive the same checks before publication. Full local SHA256 and Git-blob SHA1 values are in the downloadable package's LOCAL_DOCUMENT_CHECKS.json.

These are integrity checks, not scientific approval or evidence that B's existing software currently passes. The source schema intentionally describes candidate_not_admitted records, not a production admission contract. No eligible N or source-object hash was fabricated.

Repository audit limits and historical/current execution distinctions are in AUDIT.md. The source/overlap/exposure ledgers preserve unresolved source identities rather than asserting independence.
