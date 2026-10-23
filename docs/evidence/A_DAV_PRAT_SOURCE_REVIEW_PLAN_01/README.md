# Prat source-object inventory and two-reader review plan

**PLAN_COMPLETE; ACTUAL_SOURCE_REVIEW_NOT_RUN.** Scope: the existing candidate label `Prat-GSE93157` and branch `A_BASELINE_BIO`. The canonical study/family IDs, source objects, endpoint declaration and reader appointments remain unresolved. This packet prepares the next review. It does not carry it out.

The [previous evidence brief](../A_DAV_PRAT_BASELINE_BRIEF_01/BRIEF.md) defines E01–E10. The [independent procedure review](../../validation/A_DAV_PRAT_PROCEDURE_01/INDEPENDENT_PROCEDURE_REVIEW.md) identifies P01–P08. The later [AIU checkpoint](../../validation/A_DAV_TARGET_ENVIRONMENT_01/ACCEPTANCE.json) accepted synthetic software tests, including the Prat procedure checks. That software result does not close source evidence or authenticate reviewers. This packet uses the current contracts without editing them.

## Prepared materials

| File | Use |
|---|---|
| [INVENTORY_REQUIREMENTS.tsv](INVENTORY_REQUIREMENTS.tsv) | Expected evidence roles, owners and closure conditions; not a list of verified files |
| [SOURCE_OBJECT_CHECKLIST.md](SOURCE_OBJECT_CHECKLIST.md) | Populate and seal the private object inventory using the existing DAV registry |
| [REVIEW_QUESTIONS.tsv](REVIEW_QUESTIONS.tsv) | The seven existing question IDs and their source-evidence tests |
| [TWO_READER_PLAN.md](TWO_READER_PLAN.md) | Custody, policy lock, independent first passes, comparison, adjudication and permitted export |
| [EVIDENCE_SOFTWARE_DISPOSITION.tsv](EVIDENCE_SOFTWARE_DISPOSITION.tsv) | E01–E10, current software support and the trigger for any later fix |
| [METHODS_NOTE.md](METHODS_NOTE.md) | Verified primary guidance for duplicate extraction, retained disagreements and provenance; its limits in DAV |
| [REVIEW.md](REVIEW.md) | Parent and separate methods review; the one plan-detail finding and its closure |
| [STATUS.json](STATUS.json) | Planning status and unexecuted evidence gates |

The inventory contains requirements, not discovered source objects. Each role can need several objects; one object can satisfy several roles. All exact object names, versions, digests, availability, permissions and completeness claims remain unverified here. No file count, patient roster or reader result is inferred. Historical source locators remain future review leads in the previous brief, not new evidence.

## Missing evidence and software fixes

E01–E08 still need actual evidence and authorized review. E09 named-method use remains deferred. E10 admission and later release are not requested or established. The software routes in the disposition table refer to the accepted implementation; they are not new defects or evidence passes. This planning pass establishes **no new software defect** and changes no runtime, schema, endpoint rule, numerical policy or frozen specification.

The synthetic-only bridge and DAV demonstration APIs remain synthetic-only. A real-source workflow needs an independently approved operational path in authorized custody. This plan neither supplies that path nor authorizes passing real objects into a synthetic API. If later authorized work exposes a concrete software failure, reproduce it with invented data and scope the smallest fix separately. Do not replace missing evidence with a default or weaken a gate.

**F01 — software-fix trigger:** a concrete invented counterexample violates an existing accepted contract, with exact code/config/schema versions and expected versus observed safe output. Retain the evidence gap separately; make the smallest bounded fix and review it. A requested new operational path, missing authentication authority or unknown source rule is not automatically a defect in accepted synthetic software.

## Status and next step

No source bytes, patient records, matrix headers or molecular values were opened, retrieved, copied or analysed. Only existing planning/contracts, software receipts and method guidance were read. No AIU job, source download, molecular calculation, score, model fit or biological analysis ran. The only new executable is a local document-integrity checker. The frozen specs, prior packets and existing code remain unchanged.

The first operational step is to appoint the source custodian and two authorized independent readers, establish approved custody and verify the exact current source-object set. Those appointments and permissions are not inferred from this planning instruction. The selection policy and review basis must be fixed before the first passes. Actual source work remains outside the present no-real-data scope.

Run `python3 -B docs/evidence/A_DAV_PRAT_SOURCE_REVIEW_PLAN_01/VERIFY.py` from this worktree to check scope, evidence/question coverage, local links and preservation. It does not execute source software, contact AIU or validate a source. [VERIFICATION.json](VERIFICATION.json) records the check; [BINDINGS.json](BINDINGS.json) binds the existing inputs and preservation baseline.
