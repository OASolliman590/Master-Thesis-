# PA03: A-P2: one release record for the four development runs

**Status:** Ready. Rules: `docs/process/HARD_RULES.md`.

## Why it matters
You sign once for the four development runs, and the signature must cover exactly the files prepared on 19 Nov. The code still writes four per-run forms and points at the superseded proposal.

## Authority
Signed amendment 15 Nov §§5–7; `docs/decisions/A_P2_DEVELOPMENT_RELEASE_DRAFT_2026-11-19.md`; process simplification item 3.

## Change
`tools/a_p2/prepare.py` emits one unapproved record listing the four runs with their input, manifest and sidecar hashes, the A1 artifact and registry hashes, and no hash of the decision document. `tools/a_p2/product.py` accepts a run only if it is listed in a signed record whose bindings match. Point `PROPOSED_DECISION_ID` at the draft.

## Done when
Invented inputs: an unsigned record, a record missing the run, and a record with one wrong hash are each refused; a signed matching record is accepted. Re-run `prepare-development --check-only` on the real inputs (outcome-free) and confirm the hashes in the draft are unchanged or update them.

## Needs from the user
Nothing to build it; your signature comes in PA06.

## Depends on
PA04 (same files; do in sequence)
