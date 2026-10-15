# Standalone Codex handoff — Paper A/A1 integrated kit

You are implementing a bounded, spec-first recovery/intake packet in OASolliman590/Master-Thesis-. Read AGENTS.md, CONTEXT.md, actual PROGRESS, docs/decisions/A_A1_INTEGRATED_SPEC_20261015.md, specs/A/README.md, specs/A1/README.md and specs/A_DATA_ACQUISITION_VALIDATION/README.md before editing. Use the integrated review branch/commit supplied with this package; recheck its live head. Do not work on main or reset another branch.

## Settled design — do not reopen

A is one baseline clinical-reference manuscript with independent A-BIO and A-PRED products. A-P2 remains the selected paired independent-test AUROC improvement over fixed CYT, equal cancer and equal originating-study weights within cancer. A-P1 is secondary and CYT-led, with a frozen learned-score secondary only independently of construction. A1 is an active full longitudinal workstream, thesis-default and conditionally a separate manuscript. Missing final-test data or optional modalities must not deadlock unrelated properly released branches. All reserved patients and related specimens/assays remain protected. Prepare protocol reconciliation only; no institutional contact or invented approval.

## Your current executable scope

Execute docs/execution/PAPER_A_A1_PACKET_01.md only: three-way code/data inventory and hash comparison; characterization of legacy semantics; migration of shared episode/identity/receipt contracts; adversarial synthetic validation; an explicitly permitted small public format tracer if its plan/access is available. Do not run real response-associated analyses, produce a signature, train/tune a model, compute final-test predictions, impute absent modalities or begin raw sequencing reprocessing. Proposed CLI names in the specification are not evidence of existing executables.

## Shared authority and recovery

The canonical data authority is specs/A_DATA_ACQUISITION_VALIDATION, inherited from draft PR #9; do not build competing A/A1 registries. The new episode-binding extension joins existing normalized records without replacing their identity fields. Preserve source raw labels and patient aliases privately. Existing reference/legacy_nmrbox_20260911 is immutable. Historical tests/results and source-level candidate counts are not current validation or eligible N. Exact historical repository and local/AIU versions must be obtained, never guessed.

## Implementation discipline

One writer per component and one integrator. For each behavior, first write and execute a failing characterization/adversarial test, apply the smallest justified port/fix, then rerun focused and relevant full suites. Record command, exit status, code/config/environment/input hashes and evidence class. Distinguish NOT_RUN, SYNTHETIC, FORMAT_TRACER and REAL_COHORT_VALIDATED. Inspect existing utilities before writing duplicates. Do not expose patient IDs, signed URLs, tokens, private paths or restricted matrices in Git or delegation prompts.

## Stop and report

Return the exact component/recovery manifest, migration map, observed legacy failures or unreproduced findings, fresh test logs, any tracer receipt, unresolved dependencies and proposed next bounded ticket. Keep decisions/settings with null or UNKNOWN blocked at their own gate; do not silently invent numerical defaults. The complete clinical pipeline is not 'implemented' when schema tests pass. The orchestrator reviews and owns commits/PRs. Do not merge or close #1/#7. A later separately reviewed release is required for patient admission, statistical freeze and scientific execution.

## Document validation command

Run `python -m unittest discover -s tests/a_a1_spec_contract -v` for the integrated specification tests after installing the pinned document-test dependencies in that test directory. This validates documents/schemas and synthetic mathematical contracts only. It is not the legacy/AIU/clinical suite. Report the full repository suite separately if run, including all failures rather than relabelling this focused command as full validation.
