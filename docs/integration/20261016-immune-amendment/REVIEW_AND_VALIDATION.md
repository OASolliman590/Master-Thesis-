# Reviewed immune-programme amendment, 16 October 2026

User authorization: amend A/A.1 immune-programme scope, align B, verify original-source membership/scoring, preserve RC2, update the PDF; no biological analysis.

Astra Medium authored the additive packet. A separate Astra Medium reviewer independently inspected the scientific/source contracts and reran the packet validator. Review accepted after correcting wording that could imply the proposed B P membership had been frozen. The eight-gene candidate remains unfrozen under inherited P/U/Q gates. The PDF crosswalk now distinguishes HOPE RNA from Teng PD-L1/TIL measurement; recovered Ayers inventor weights are described as a candidate, not an admitted assay.

## Fresh verification

- Packet validator: PASS; 21 programme entries; four deliberate invalid mutations rejected; seven archived legacy files verified; 696 RC2 scoped files unchanged.
- A/A.1/DAV document, schema and synthetic estimand contracts: 38 passed, zero failures/errors/skips (0.515 s).
- Freeze adversarial checks: four passed, zero failures/errors/skips (0.252 s).
- Baseline integration verifier against `specs/thesis-20261015-v1-rc2`: 697 Git blobs verified (696 scope plus manifest), 94 schemas, 16 D examples and 38 entry links; zero failures.
- Validation used the existing isolated Python environment `/private/tmp/thesis-spec-venv`. The first baseline-check attempt with the PDF runtime failed because jsonschema was absent; no test passed in that environment. Switching to the existing test environment resolved this without dependency changes.

No production scoring or biological regression was run. Existing full B implementation regressions and AIU fixture gaps retain their prior status; this document does not count historical results as fresh verification. The new checks establish specification consistency and baseline preservation, not biology.

## Scope of snapshot

The snapshot freezes the reviewed specification text and candidate-status records, not unresolved gene membership/scoring choices. All new programme scientific releases remain false. Source/assay/method qualification, data admission and statistical releases remain distinct. No thresholds, cohorts, coefficients beyond the explicitly sourced unadmitted candidate, or biological results were invented. RC2 tag and original files remain intact. No branch merge or tag overwrite is authorized.

The parent owns publication and remote verification. The independent reviewers did not commit or push.

Non-failing observations: inherited A contract tests emit ResourceWarning for unclosed fixture readers; the log preserves these warnings with checkout paths sanitized. Git whitespace check flags one trailing blank line in the archived legacy YAML. Its exact upstream bytes are intentionally preserved; authored files pass whitespace checking. Neither is a biological validation failure.
