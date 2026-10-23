# Independent Spec review

**Verdict: changes required; 1 P1, 6 P2.** Reviewed the fixed-base addition package and current files, frozen tickets/contracts, integrated decision, plan, Prat review and all three group reports. No scope creep found. Source/reviewer/environment acceptance remains NOT_RUN, separately from these software gaps.

| Slice | Software verdict |
|---|---|
| Parent T01, T02, T03 | Reused APIs and connected invented-byte seams covered; no new real-source acceptance. |
| A T04 | Covered for reviewed synthetic identity cases. |
| A T05 | Partial: declared binary branch and adjudicated endpoint consumption, S2–S3. |
| A T06 | Partial: legitimate episode reuse rejected, S7. |
| A T07 | Coverage produced; downstream enforcement incomplete, S1. |
| B T08, T09 | Substantial branch/overlap/exposure checks; see separate Standards findings before acceptance. |
| Prat P01 | Partial, S5. |
| Prat P02–P08 | Bounded protocol checks present; authentic independence/semantic/source acceptance remains external. P07 shares S7. |
| C T10, T11 | Partial, S1–S4/S7. |
| C T12, T14 | Reviewed protection/freeze paths covered; target-environment acceptance pending. |
| C T13 | Partial, S6. |
| Connected workflow | Partial through the affected consumers; all actual admission/release flags remain false. |

- **S1 [P1] Enforce computed assay suitability.** ASSAY_AND_MEASUREMENT_CONTRACT.md:97: “Suitability is evidence-based and branch-specific.” `tools/a_dav/matrices.py:99` trusts supplied labels rather than sealed coverage. A targeted matrix with `de_suitability=FAIL` still becomes INCLUDED in BASELINE_DE.
- **S2 [P2] Support the declared endpoint branch.** ENDPOINT_ONTOLOGY.md:92 permits “a separately declared source-binary endpoint branch.” `tools/a_dav/matrices.py:124` requires ORR; supported source-binary admission cannot materialize.
- **S3 [P2] Consume adjudication.** ENDPOINT_ONTOLOGY.md:80 requires “separate assertions and a discrepancy state.” `tools/a_dav/matrices.py:125` blocks two retained ORR assertions even after `endpoints.py:99` records the preferred outcome.
- **S4 [P2] Keep absent follow-up in audit.** RELATIONAL_INVARIANTS.md:15: “not fabricated in a pair row.” `tools/a_dav/matrices.py:288` appends a pair with null follow-up.
- **S5 [P2] Reconcile required-object declarations.** Prat review:36: “Missing required objects … withholds dependent acceptance.” `tools/a_dav/prat_review.py:44` lets `required=False` override membership in `required_object_ids`.
- **S6 [P2] Complete aggregate reporting.** TICKETS_AND_TESTS.md:23 requires “gate/count/limitation tables.” `tools/a_dav/reporting.py:19` exports statuses/hashes and one optional count, omitting gate/limitation tables.
- **S7 [P2] Permit evidenced specimen reuse.** RELATIONAL_INVARIANTS.md:11 permits “separate explicitly evidenced bindings.” `tools/a_dav/timing.py:47` and `matrices.py:75` reject multiple bindings regardless of episode.

## Reproduction appendix

These were five narrow invented reproductions, not a repeated full suite. Command interpreter: `/private/tmp/thesis-adav05-20261020/bin/python -B`. Every workflow case started with `tools.a_dav.demo.synthetic_workflow_packet()` and invoked actual `run_workflow` stage APIs. No product file, real object or private fixture was changed/read.

1. **S1:** set `config.assays.matrices[0].feature_scope='TARGETED'`. Observed workflow `SYNTHETIC_READY`; both coverage rows had `de_suitability='FAIL'`, `scoring_suitability='PASS'`; baseline `a1` was `INCLUDED`.
2. **S2:** change the invented outcome to `endpoint_class='SOURCE_BINARY'`, `canonical_category='SOURCE_POSITIVE'`, null ORR/DCR mappings; retain its EVALUABLE/VERIFIED fields. Configure classes `['SOURCE_BINARY_UNKNOWN']`, the corresponding category map, and admission endpoint policy `endpoint_class='SOURCE_BINARY'` with explicit `source_binary_definition`. Observed endpoint and admission stages `SYNTHETIC_READY`, then baseline `BLOCKED_UNKNOWN / ENDPOINT_UNKNOWN`. The source-specific binary must retain its own meaning; fixing this must not manufacture ORR.
3. **S3:** copy outcome `o1` to `o2`, with raw label `invented-progressive`, category PD, false ORR/DCR mappings and RESOLVED discrepancy; add its valid same-episode outcome binding. Append `o2` to source priority/category map and configure `discrepancy_resolutions['p1:e1']={'preferred_outcome_id':'o1','source_locator':'invented-authority'}`. Observed endpoints and admission `SYNTHETIC_READY`, then baseline `BLOCKED_UNKNOWN / ENDPOINT_UNKNOWN`. Preserve both assertions while selecting the evidenced preferred endpoint.
4. **S4:** change longitudinal window bounds to `[15,20]`, leaving the invented follow-up at day 10. Observed workflow `SYNTHETIC_READY` and a pair row `(pre_specimen_uid='sp1',followup_specimen_uid=None,missing_followup_reason='NO_FOLLOWUP_IN_WINDOW')`. The denominator/exclusion belongs in audit; actual timepoint rows remain preserved.
5. **S5:** use only the invented `prat()` constructor in `tests/a_dav_implementation/test_group_b_protocol.py`; set its sole manifest object to `state='MISSING',required=False`, leaving it in `required_object_ids`. Recompute the common manifest digest and both reader basis/seals to represent a consistently authored packet. Observed `SYNTHETIC_READY`, no reasons. No complete bytes were verified for this explicitly required object.

S6–S7 are direct missing-behavior findings from the cited executable branches; no test was rerun for them. S7 affects real legitimate relational shape even within wholly invented cases, rather than requiring actual source evidence.

Reviewed product SHA-256: matrices `6088325e6779e34d594daa205c0054ed4e0aed9458721c873e7bea90cc8f3875`; release `b003325edff179577f40613a487b12b5b94f1f5550ff081cdd86d912e44c6dc6`; reporting `fbc3040578ae0bb784a0d75be6a2f2701a3376992f64c8c7709f9d3e90f064f8`; Prat `e311611115b5081bf5d61e38cdf286ff50a0fd618470a7344b2418fc32cabed5`. Core changed during independent review; the current inspected hash was `49afc1fb9454eb97182454dd68b61c701423bb9431e3aaac4ed734245bedbe6c`. This report does not certify later worker fixes or any final integrated acceptance run.
