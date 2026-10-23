# Independent Spec fix-wave 1 review

**Scoped verdict: S1–S7 ADDRESSED; zero remaining findings from this review.** This closes the original 1 P1 and 6 P2 findings at the hashes below. I reviewed `review-fix-wave1.diff`, current changed code, added regression assertions and the final A/B/C fix-round report sections. The current reporting code includes the subsequent Prat count guard absent from the initial fix-diff snapshot. No new breakage was identified within this fix scope; this is not another broad review or final whole-branch acceptance.

| Finding | Disposition and evidence |
|---|---|
| S1 | **ADDRESSED.** `matrices.py:124` consumes matching sealed coverage; named DE/scoring/final-test lanes require their corresponding property. Original targeted-DE tracer now emits EXCLUDED, rather than INCLUDED. |
| S2 | **ADDRESSED.** `endpoints.py:86` validates an explicit defined binary in OTHER; `matrices.py:140` consumes the declared class. Connected defined-binary tracer now reaches SYNTHETIC_READY with INCLUDED/SOURCE_BINARY and null ORR. Undefined binaries remain unevaluable. |
| S3 | **ADDRESSED.** `matrices.py:146` selects the preferred outcome from sealed same-patient/episode adjudication. Original tracer now includes ORR=1 while retaining both source outcomes. |
| S4 | **ADDRESSED.** `matrices.py:293` records every patient/window denominator; line 297 suppresses absent-sided pairs. Original tracer emits no pair, retaining its explicit NO_FOLLOWUP_IN_WINDOW audit. |
| S5 | **ADDRESSED.** `prat_review.py:55` checks required IDs against available byte-verified objects; line 96 also restricts assertion authority. Freshly resealed original bypass now blocks with OBJECT_MANIFEST_INCOMPLETE and ASSERTION_EVIDENCE_MISSING. |
| S6 | **ADDRESSED.** `reporting.py:24` adds allowlisted gate/limitation/count tables. Lines 30–38 verify Prat lineage and suppress all general count fields under its narrower export policy. |
| S7 | **ADDRESSED.** `timing.py:46` distinguishes evidenced episode contexts; `matrices.py:83` keys timing by specimen/episode and checks binding ID/role. Added A/C regressions retain both context-specific timepoints and reject ambiguous/missing contexts. |

**Group verdicts:** A's S2/S7 interface changes are addressed; B's S5 is addressed; C's S1–S4/S6/S7 are addressed; parent demo/workflow changes consume the new explicit policies and retain stage checks privately. Other original ticket verdicts are unchanged by this scoped review. Real source, authenticated reviewer, environment and scientific/statistical acceptance remain NOT_RUN. Parent owns final integrated tests and broad review.

## Verification and version appendix

I independently replayed only the five original invented S1–S5 public-API tracers using `/private/tmp/thesis-adav05-20261020/bin/python -B`; outputs are summarized above. S2 supplied the new explicit OTHER binary definition and corresponding matrix endpoint policy. No full tests, network, source/private fixture reads, product edits, installs, commits or subagents occurred. S6/S7 assessment used changed code, the added observable assertions and recorded worker evidence, not a claimed independent execution.

The final worker report sections record A: 65 focused passes and strict mypy on four modules; B: 74 focused passes and strict mypy on four modules; C: 41 focused passes and strict mypy on three modules. These are worker results, not a re-executed whole suite. C's final corrected log explicitly supersedes two privacy-test false positives caused by substrings inside permitted hashes.

Current inspected SHA-256 values match those final worker reports for changed owned files:

```text
49afc1fb9454eb97182454dd68b61c701423bb9431e3aaac4ed734245bedbe6c  tools/a_dav/core.py
3bfe5786674bcb5e4a5692fa31af96a55d1d3fbaf9297512b061abb4a5f4dad2  tools/a_dav/endpoints.py
ab8d588e0610371cebd647c3e92fc5f305dda8a21cf673124adba355bb5678a7  tools/a_dav/timing.py
0f5e36164a846b80e6e72e5a00b9203dacab8756181527447fbec275380dd093  tools/a_dav/admission.py
28938f74b953920823f784ab781834115cf62d30890499d577f0d2b244b2a181  tools/a_dav/prat_review.py
2cb3a2e90a6d9fca6e9f8047fb26659d07b07106d89a08b8e9c474534e711717  tools/a_dav/matrices.py
b003325edff179577f40613a487b12b5b94f1f5550ff081cdd86d912e44c6dc6  tools/a_dav/release.py
d5f390ef192339f83db2c5c04d339736b28efff94e55be65b343685f79079c41  tools/a_dav/reporting.py
2afea0b4e0f99e6932f07d55b89d262cbdff8f3b14cd972d87a2b17a8b8adf65  tools/a_dav/workflow.py
51ee82c7e1a375811f4a7c29fd8f1f938764e80fa94106e3b9b4e1eae2765e0a  tools/a_dav/demo.py
```

`release.py` is unchanged from the initial review. Core/admission hashes are recorded to identify the connected replay context, not to extend this Spec closure to separate Standards findings.
