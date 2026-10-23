# Standards review: corrective round 1

Scoped re-review of the four findings in REVIEW_STANDARDS.md. Reviewed the Core/B corrective diff, current core against the initial additive review package, relevant A chronology diff, new regression assertions and worker evidence. No tests rerun, network/source access, installs, code changes, commits or subagents. This does not reopen the full package review or cover unrelated Spec-axis fixes.

| Original finding | Disposition | Evidence in current code |
|---|---|---|
| 1 — A component chronology | **ADDRESSED** | [timing.py:53](/Users/megastore/Documents/ChatGPT/MyThesis_Epigentics_Project/work/a-dav-01/tools/a_dav/timing.py:53) parses both endpoints, requires finite values, checks each against both episode bounds and checks start ≤ stop. Missing/unparseable component dates remain unknown. New literal regressions cover reversed and all four bound violations; legitimate delayed starts remain covered. |
| 2 — B required manifest authority | **ADDRESSED** | [prat_review.py:55](/Users/megastore/Documents/ChatGPT/MyThesis_Epigentics_Project/work/a-dav-01/tools/a_dav/prat_review.py:55) requires every authoritative required ID in the AVAILABLE/full-byte-verified set regardless of its optional flag. Line 96 applies that set to assertions. Freshly resealed unavailable objects block; unreferenced optional missing objects remain legitimate. |
| 3 — B study-order audit | **ADDRESSED** | [admission.py:213](/Users/megastore/Documents/ChatGPT/MyThesis_Epigentics_Project/work/a-dav-01/tools/a_dav/admission.py:213) derives study-local failure/reasons, computes eligibility, then aggregates. Public-API regressions reverse every record table and compare complete results for missing-evidence, non-ICI and failed-source cases. Batch-wide incomplete-source status still blocks the aggregate result. |
| 4 — Parent malformed-config failure | **ADDRESSED** | [core.py:175](/Users/megastore/Documents/ChatGPT/MyThesis_Epigentics_Project/work/a-dav-01/tools/a_dav/core.py:175) independently catches rejected config canonicalization and uses the fixed null digest. Invalid branches are normalized before sealing. Public decorated-stage tests cover NaN/set/bytes/cycles and verify empty records, fixed failure, false flags and valid receipt. |

Verdicts for this wave: **A addressed; B addressed; parent addressed; C has no finding assigned in this review wave.** Zero outstanding findings from my original four; no additional actionable breakage found in these corrections. Original severities remain four historical P2 findings, now addressed. This is a scoped Standards closure, not whole-package acceptance.

Inspected existing focused logs, without rerunning them: core **10 passed**, strict mypy **1 file**; B **74 passed**, strict mypy **4 files**; A `round1-final-green.txt` **65 passed, 41 deselected**, `round1-mypy-green.txt` clean for **4 files**. All three matching worker reports explain changes and preserve RED/GREEN history; A's final report confirms the chronology fix and final timing/test hashes below. Its unrelated endpoint/context fixes remain for the Spec re-review. Actual source, clinical/reviewer/environment/statistical acceptance remains **NOT_RUN**, and actual readiness/admission/release/analysis flags remain false.

## Exact reviewed SHA-256 values

| File | SHA-256 |
|---|---|
| tools/a_dav/core.py | `49afc1fb9454eb97182454dd68b61c701423bb9431e3aaac4ed734245bedbe6c` |
| tools/a_dav/timing.py | `ab8d588e0610371cebd647c3e92fc5f305dda8a21cf673124adba355bb5678a7` |
| tools/a_dav/admission.py | `0f5e36164a846b80e6e72e5a00b9203dacab8756181527447fbec275380dd093` |
| tools/a_dav/prat_review.py | `28938f74b953920823f784ab781834115cf62d30890499d577f0d2b244b2a181` |
| tests/a_dav_implementation/test_core.py | `5596a098002069671879e2c362ce06d004eda50ede2699d2b8d3158cccf1ad82` |
| tests/a_dav_implementation/test_group_a.py | `cf064145a9a928cc4d4f752a292e59f8bb406f52695fa6d097199b1742d97d64` |
| tests/a_dav_implementation/test_group_b_graph_admission.py | `d56405e72084c8bd6c6ae50ad40ca863e138ab35feb5f57fe391c8e49376cff6` |
| tests/a_dav_implementation/test_group_b_protocol.py | `db2baebe3c893c38ad5f82b8ba2a3e9619e25442814f61cb3958e9fd94af58b1` |
