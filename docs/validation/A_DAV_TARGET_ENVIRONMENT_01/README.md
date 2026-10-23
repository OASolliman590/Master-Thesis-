# Shared DAV synthetic validation on AIU

The AIU software check passed on 24 October 2026 (Africa/Cairo; receipts use UTC on 23 October). This packet checks the shared DAV implementation at `f53d2222d7d82e6dfdf4af381d71946cd247a89d`. Luna at high effort ran the target check. The parent reviewed the runner, obtained the AIU receipts separately, checked types on AIU and repeated the resume command.

All **255 synthetic tests passed** on AIU Linux x86_64 with Python 3.11.16, pytest 9.1.1 and jsonschema 4.26.0. Fresh and resume commands exited 0. The parent resume command also exited 0 and preserved all four output hashes. Strict mypy 1.18.2 passed for the 14 new DAV modules and the runner. The parent local check passed all 14 runner boundary tests. [ACCEPTANCE.json](ACCEPTANCE.json) records the scope; [VERIFICATION.json](VERIFICATION.json) records the independent receipt and preservation checks.

## Inputs and execution

The transfer contained exactly 45 files: 18 runtime modules, seven synthetic test modules, 17 unchanged schemas, the pinned synthetic requirements, the reviewed runner and its manifest. Runtime, tests, schemas and requirements matched the base commit. No repository history, source datasets, caches, credentials or old tracer fixtures were transferred. [ALLOWLIST_MANIFEST.json](ALLOWLIST_MANIFEST.json) binds the bytes. [PAYLOAD_BUILD.json](PAYLOAD_BUILD.json) records the archive hash. [AIU_CONNECTION.json](AIU_CONNECTION.json) records the verified connection and initial dependency check. Strict checking used the existing dedicated host-key file; key contents were neither read nor copied.

The parent created a new directory under AIU's `planning/2026-10-24/`, verified every archive member before unpacking and created a private virtual environment there. [prepare_aiu.py](prepare_aiu.py) is the executed setup source. Its dependency install report retains selected package versions and public artifact hashes. No shared environment or existing server checkout changed. This is a record of the tested installation; a separate clean reconstruction from a complete hash-enforced lock was not run.

The single worker run used PID **2760066** and reached a terminal `PASSED` receipt. Its exact commands and individual exits are in [AIU_RECEIPTS/result/status.json](AIU_RECEIPTS/result/status.json). Child processes used UTC, disabled plugin autoload and bytecode, and limited numerical thread libraries to one thread. The environment receipt records the launcher's observed timezone separately. The invented fixture's declared environment field is fixture content; the AIU receipt supplies actual runtime provenance.

The full transferred suite covers stale code/config/schema/output rejection, tampering, interrupted invented transport, privacy summaries, unsafe destinations, collisions and fresh/resume behavior. Fresh/resume was also exercised directly. The parent checked a case-sensitive filesystem and symbolic-link support in a disposable directory, then verified the actual payload hashes after the run. This evidence applies to this AIU environment and the copied implementation. It is not a test of other operating systems or real source formats.

## Software fixes and missing evidence

Parent review found and closed four runner issues: absent thread limits, dependency blocks reported as failures, absent runtime version enforcement and insufficient bundle symlink checks. Boundary tests also cover rejection of counts and identifiers in public summaries. The shared DAV implementation needed no change. The [worker report](WORKER_REPORT.md) distinguishes its local checks from the later AIU run. The parent review is recorded in [REVIEW.md](REVIEW.md).

This closes the **synthetic target-environment software check** for DAV-T01–DAV-T14 and the connected Prat procedure. It does not close E01–E08 source and independent-review evidence, E09 named-method evidence or E10 actual admission and release. The prior [implementation receipt](../A_DAV_IMPLEMENTATION_01/ACCEPTANCE.json) remains an unchanged historical checkpoint; this packet adds later environment evidence.

The synthetic release draft is `READY_FOR_REVIEW`, with evidence class `SYNTHETIC`, software gate `PASS`, no admitted sources, data/statistical/protected-set gates `NOT_RUN`, and explicit actual-source/statistical review blocks. This is consistent with the frozen release schema and does not grant a real release. All actual-analysis flags remain false. Frozen specifications and all 2,142 protected files remained byte-identical. No real source data or biological analysis was used.

## Verify and next step

From this worktree, run:

```sh
python3 -B docs/validation/A_DAV_TARGET_ENVIRONMENT_01/VERIFY.py
```

This verifies retained evidence and preserved local files; it does not launch another AIU job. The isolated AIU directory and receipts remain available at the exact path in `AIU_CONNECTION.json`; the recorded runner has finished. No push or merge was performed.

The next source step is an authorized source-object inventory and independent two-reader review in approved custody. It needs actual evidence and authenticated reviewers. That work requires a separate instruction; this synthetic validation provides no source facts or biological conclusions.
