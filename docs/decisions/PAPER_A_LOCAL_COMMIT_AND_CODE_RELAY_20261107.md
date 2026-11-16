# Paper A: local commit and code-only relay permissions

Recorded 7 November 2026 from the user's explicit chat replies. This records authorization; it is not an agent signature or a scientific gate closure.

## Local A-P2 commit

Question: May I commit the nine staged A-P2 software files? They have one completed review, 287 passing tests in each main mode, and 26 passing single-cell tests. Automatic approval review blocked the commit because the earlier instruction requires an explicit request to commit. This asks for the local A-P2 commit only.

User reply: **"Approve the local A-P2 commit"**.

Authorized paths, on the existing A-P2 worktree branch:

- `docs/usage/A_P2.md`
- `r/R/a_p2.R`
- `tests/a_meta/test_r_manifest_retention.py`
- `tests/a_p2/test_product.py`
- `tests/r_bridge/test_bridge.py`
- `tools/a_meta/r_manifest.py`
- `tools/a_p2/__main__.py`
- `tools/a_p2/product.py`
- `tools/r_bridge/__init__.py`

This authorizes one local commit of those nine verified files only. It does not authorize a merge, push, other commits, real A-P2 rebuild, outcome run, or final-test release. This permission record is not part of the nine-file commit.

## Prepared W4/W5 fixes and W6 review

Question: Automatic approval review blocked the W6 external review because "public code" did not clearly cover newly written, uncommitted code. May Luna/Astra inspect the uncommitted Paper A code and invented tests for the prepared W4/W5 fixes and W6 review, with patient-free requirements only and no real data, secrets, or signed protocol files?

User reply: **"Authorize that code-only scope"**.

The authorization covers the prepared original-session W4 and W5 corrections and the one W6 review. It includes their new, uncommitted code and invented tests and the patient-free requirements supplied in the bounded briefs. It excludes real data, secrets and signed protocol files. W4/W5 already had their single reviews; no additional review round is authorized by this reply. No extra delegation scope, publication or scientific signature is inferred.

## Continuing locks

Real outcomes remain locked. The real A-P2 rebuild remains deferred. IMvigor210 stays UNTOUCHED_FINAL_TEST. Paper B is outside this work. No scientific decision or signature is supplied by either reply.

## Remaining A-LONG and manuscript code scope

Question: May Luna/Astra also implement and review the remaining A-LONG and manuscript work (W8/W10), including newly written, uncommitted code and invented tests? The latest approval names W4/W5/W6 only. The prepared briefs keep the same limits: patient-free requirements, no real data, secrets or signed protocol files, and one review per item.

User reply: **"Authorize W8/W10 under those same limits"**.

This extends the code-only delegation scope to W8 and W10, including their new uncommitted code, invented tests and patient-free requirements. Each receives one review. It does not authorize real outcome use, access to signed protocol files by external agents, scientific signatures, additional commits, merges or pushes.

## Test-fixture correction and rerun, 10 November 2026

User instruction: **"fix the test fixture bug and rerun the checks. keep real outcomes locked and keep it simple, no extra review loops or commits"**.

This authorizes correcting the nondeterministic cohort selection in `tests/a_p1/test_learned_score.py`, synchronizing that test into the combined verification checkout, and rerunning the invented-data checks. The production guards and scientific decisions remain unchanged. No real outcomes, new review, commit, merge or push are authorized by this instruction. This records the user’s instruction; it is not an agent signature.
