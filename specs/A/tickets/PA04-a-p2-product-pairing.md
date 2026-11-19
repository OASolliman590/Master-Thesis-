# PA04: A-P2 product: enforce the four signed package pairings

**Status:** Ready. Rules: `docs/process/HARD_RULES.md`.

## Why it matters
Each run must use its signed table and family grouping (main: 408/6, conservative: 408/4, bladder sensitivity: 375/6, freeze: 375/6). The product currently lets a development manifest carry either table and either grouping.

## Authority
Signed amendment 15 Nov §7; Cycle 02 review finding 2 and the tamper-test finding.

## Change
At product preflight, refuse any manifest whose table hash and grouping are not the signed combination for its package. Add a same-size tamper test (swap one excluded patient for another with refreshed hashes) that the preparer's own recomputation catches. Assert `structural_status`, not the always-BLOCKED `status`.

## Done when
Each wrong combination is refused at product preflight, in both directions; the same-size swap is caught.

## Needs from the user
Nothing.

## Depends on
—
