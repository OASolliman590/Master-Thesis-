# PA02: A-META: keep 2–3-study pools tentative; tighten three tests

**Status:** Ready. Rules: `docs/process/HARD_RULES.md`.

## Why it matters
With two or three studies the between-study spread is barely estimable, so the signed spec calls such pools tentative. Current tests require the label `standard` at three studies, which upgrades the evidence without your signature.

## Authority
`specs/A/SPEC_v2.md` §4.1; numerical freeze N10; Cycle 02 review finding 4 and two moderate findings.

## Change
Keep pooling from three units, but report k = 2–3 as tentative (`tools/a_meta/synthesis.py` `_label`). Rewrite the endpoint-isolation test to join `groups.tsv` and `meta_input.tsv` on `analysis_id` and assert the exact study set. Label the tiny-variance fixtures as numerical stress inputs.

## Done when
Tests assert `tentative` at k = 3 and the exact study set per definition; swapping two equal-sized study sets makes the isolation test fail.

## Needs from the user
Nothing (this restores the signed wording).

## Depends on
—
