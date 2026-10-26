# Why the acquisition work stalled

25 October 2026. This diagnosis concerns the A/A.1 workstream, not the quality of the whole thesis. It distinguishes recorded facts from interpretation.

## What the record supports

The shared ticket register asks for both software tests and real-source tracers. Riaz is named for study resolution, endpoint and treatment work. The later synthetic acceptance receipt explicitly says actual source acceptance was not run for T01–T14. Therefore that checkpoint was useful software evidence but did not complete the source-acquisition task. Sources: [ticket register](../../../specs/A_DATA_ACQUISITION_VALIDATION/TICKETS_AND_TESTS.md) and [implementation acceptance](../../validation/A_DAV_IMPLEMENTATION_01/ACCEPTANCE.json).

The code also lacked a real-file ingestion interface and restricted downstream packets to synthetic classification. The current architecture changes address these concrete engineering gaps. Sources: [classification decision](../../adr/0001-data-classification-is-origin.md), [ingestion decision](../../adr/0002-cohorts-are-field-maps.md), and the working-tree diff against `5fd08d4` in `tools/a_dav/core.py` and the new `tools/a_dav/ingest.py`.

The retained records show repeated review/correction rounds. Examples include [A-DAV-02 revision 5](../../validation/A_DAV_02/REVISION_05_RECEIPT.md), [A-DAV-04 review 8](../../validation/A_DAV_04/SOL_CODE_REREVIEW_08_ACCEPT_RECEIPT.md), and [A-DAV-05 review 5](../../validation/A_DAV_05/SOL_CODE_SPEC_REREVIEW_05_ACCEPT_RECEIPT.md). A-DAV-07 has separate queue, listing, file-list and suffix reviews. The names and records establish repeated work; they do not by themselves prove each fix was unnecessary or quantify weeks lost.

Prat work expanded into custody checks, two-reader training and archive research. These were individually requested in the conversation, often following an agent's proposed next step. The later provenance decision establishes that unknown continuity with a 2017 attachment is not a universal prerequisite for reviewing a current official object. Sources: [procedure review](../../validation/A_DAV_PRAT_PROCEDURE_01/INDEPENDENT_PROCEDURE_REVIEW.md), [training scope](../../validation/A_DAV_PRAT_ENDPOINT_SCOPE_01/DECISION.md), and [corrected provenance resolution](../../wayfinding/A_A1_ACQUISITION_01/PROVENANCE_RESOLUTION.md).

## Responsibility and limits of the conclusion

**Specification:** its strict evidence and release requirements created real work, but they did not require an indefinite review loop or a universal historical-byte comparison. Some tickets request multiple review roles; it would be inaccurate to summarize every ticket as requiring exactly one reviewer. The public-reviewer amendment now records the agreed simpler signing rule. See [the amendment](../../decisions/AMENDMENT_V7_PUBLIC_REVIEWER_20261025.md).

**Agents:** the main execution failure was allowing successive local milestones to replace the end-to-end acquisition objective. The synthetic-only implementation was honestly labelled, but it still left no direct real-source path. Agent recommendations sustained the Prat procedural sequence. The coordinator's retained events and revision receipts show repeated delegation/review cycles. Responsibility for proposing a shorter route and noticing that software could not ingest real sources lay with the agents, not with the user being expected to diagnose the architecture.

**User:** earlier explicit instructions excluded real source data and authorized synthetic rehearsals and full shared-DAV implementation. Those instructions constrained those stages legitimately; an agent should not have silently ignored them. Later public-source inspection was explicitly authorized, and the task should then have been redirected toward the smallest working real-source path. The conversation supports that sequence, not a claim that the user requested endless validation. No quantitative allocation of blame is justified by these records.

## Operational correction

Use one real cohort slice with a finite end condition: retained public objects, automatic source-linked records, actual unresolved worksheet items, and a patient-free summary. Keep unknown source meaning separate from reproducible software failures. Apply the agreed review cap, preserve important privacy/integrity checks, and backlog nonblocking refinements. The user's signature remains a human action; software must neither fabricate it nor turn it into another invented-reader rehearsal.

The current implementation and final verification status belong in [HANDOFF.md](HANDOFF.md); this diagnosis is not an acceptance receipt.
