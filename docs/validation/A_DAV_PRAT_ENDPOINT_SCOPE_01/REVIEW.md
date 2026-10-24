# Independent contract review of endpoint summary scope

Reviewed the proposed [decision](DECISION.md), [form v3](FORM_V3.json), [previous rehearsal review](../A_DAV_PRAT_SYNTHETIC_WALKTHROUGH_02/REVIEW.md), existing seven questions and frozen local contracts. This is documentation review only. No prior reader pass, source object, patient record, network, SSH operation, test or biological analysis was used; no approval or authenticated source review is established.

## Finding

**One minor clarification recommended:** explicitly include assessment date/day and window in the evidence covered by `assessment_disposition`, or retain their absence as a gap. The proposed description currently names individual assessment, system/version and evaluability. The frozen [endpoint ontology, “Required source fields”](../../../specs/A_DATA_ACQUISITION_VALIDATION/ENDPOINT_ONTOLOGY.md) also names assessment date/day and window. This clarification needs no numerical window or new clinical rule and should not imply that a native label establishes timing.

## Contract assessment

The split is otherwise consistent: `endpoint` summarizes meaning plus individual assessment; `episode_link_disposition` and the cross-reference preserve the separate same-patient/same-index-episode assertion. A supported summary cannot complete the full endpoint question or release use when the link is unknown/conflicting. Actual use remains false in every invented example. This preserves the [original endpoint and episode questions](../../evidence/A_DAV_PRAT_SOURCE_REVIEW_PLAN_01/REVIEW_QUESTIONS.tsv) and [relational invariants, “Episode integrity”/“Endpoints and splits”](../../../specs/A_DATA_ACQUISITION_VALIDATION/RELATIONAL_INVARIANTS.md).

The local summary order classifies training annotations; it does not reorder clinical sources. Both documents retain raw assertions, unequal authority, locators and episode conflicts, and forbid source-binary conversion shortcuts or individual assignment from totals. The historical reader labels/seals remain unchanged. A source contradiction still requires retained assertions and adjudication under the frozen [endpoint ontology, “Objective”, “Prohibited mappings” and “Conflict resolution”](../../../specs/A_DATA_ACQUISITION_VALIDATION/ENDPOINT_ONTOLOGY.md). No actual Prat endpoint variant is selected.

## Remaining real work

The logical sequence remains: establish custody/access and reader authority/authentication; verify object inventory; prepare/familiarize readers and lock the source-supported policy/common basis before outcome-driven selection; obtain separate first passes, then compare and preserve disagreements/adjudication. These stages are proposed, not completed. [Existing two-reader plan, S0–S6](../../evidence/A_DAV_PRAT_SOURCE_REVIEW_PLAN_01/TWO_READER_PLAN.md).

V0–V6 completion and independent source sign-off precede V7 admission/reviewer approval, V8 matrix validation and V9 split/exposure approval; only the immutable release becomes analysis-facing. [Admission contract, “Release sequence”](../../../specs/A_DATA_ACQUISITION_VALIDATION/COHORT_ADMISSION_AND_RELEASE.md). Controlled-source application/institutional requirements apply conditionally; this review establishes no public or controlled route and invents no universal IRB/application requirement. [Access policy, “Controlled access”/“Redistribution”](../../../specs/A_DATA_ACQUISITION_VALIDATION/ACCESS_PRIVACY_AND_REDISTRIBUTION.md).

Settling a training label supplies neither authority nor source evidence. Missing approvals remain operational gaps, with no executable defect established. This review does not verify future checker behavior, authenticate reader independence or admit any source.
