# PA01: A-BIO: report "not estimable" when batch determines response

**Status:** Ready. Rules: `docs/process/HARD_RULES.md`.

## Why it matters
If every responder came from one batch and every non-responder from another, any expression difference could be the batch, not response. The signed spec says such an effect is not estimable. Today `_effect_row` returns an effect (an invented 2+2 example gives g = 1.60), and it flows into the meta-analysis.

## Authority
`specs/A/SPEC_v2.md` §4.3; Cycle 02 review finding 1.

## Change
Check estimability on the endpoint-, stratum- and feature-evaluable patients before an effect is emitted (`tools/a_meta/effects.py`, `tools/a_bio/runner.py`). A non-estimable effect is reported with its reason and never enters A-META input.

## Done when
Invented fully confounded case → `not_estimable`, absent from `meta_input.tsv`; invented estimable control → effect as before. Deliberate break (guard disabled) makes the test fail. Module tests, then the full gate.

## Needs from the user
Nothing.

## Depends on
—
