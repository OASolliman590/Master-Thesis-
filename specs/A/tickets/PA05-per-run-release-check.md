# PA05: Real routes check a signed record for their own run

**Status:** Needs your decision. Rules: `docs/process/HARD_RULES.md`.

## Why it matters
A-BIO, A-P1 and A-LONG can open outcome columns once a flag or a status field says so. A correctly hashed but unrelated decision would pass. Each real route should open outcomes only under a signed record naming that exact run.

## Authority
Cycle 02 review finding 3; hard rule 1.

## Change
Reuse the PA03 record format: one signed record lists runs and their input hashes; each real entry point refuses unless its run and inputs are listed. Real routes stay closed until then.

## Done when
Invented tests: an unrelated, correctly hashed record is refused by each of the three routes; a matching record is accepted.

## Needs from the user
Accept that the PA03 record format is the release mechanism for every Paper A real run.

## Depends on
PA03
