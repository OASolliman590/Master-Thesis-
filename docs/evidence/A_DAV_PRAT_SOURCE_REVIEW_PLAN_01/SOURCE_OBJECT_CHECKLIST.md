# Private source-object inventory checklist

This checklist resolves the planning part of P01/P02/P08. Actual object verification is **NOT_RUN**. Its authority is the existing [source registry template](../../../specs/A_DATA_ACQUISITION_VALIDATION/templates/source_object_registry.tsv), [source-record schema](../../../specs/A_DATA_ACQUISITION_VALIDATION/schemas/source_record.schema.json), [patient model](../../../specs/A_DATA_ACQUISITION_VALIDATION/PATIENT_DATA_MODEL.md) and [relational invariants](../../../specs/A_DATA_ACQUISITION_VALIDATION/RELATIONAL_INVARIANTS.md). This packet creates no second canonical registry and no canonical source IDs.

## Inventory scope

Use [INVENTORY_REQUIREMENTS.tsv](INVENTORY_REQUIREMENTS.tsv) as an evidence request list. In approved custody, link each requirement to the exact supporting source object(s), the part examined and any unresolved search limit. Include original publications, deposit records, supplements, corrections and relevant reanalyses in the scope assessment. Do not presume that all exist, that one supplement is complete, or that an accession resolves the originating family. Internal permission and prior-use records are review evidence, not fabricated deposited source objects.

Represent each physical object once in the existing source registry; link its several evidentiary roles separately. Preserve compressed-container and extracted-member relationships when applicable. A digest for a container does not replace the digest and identity of an inspected member. Record superseded versions without deleting them. A required role with no located object remains unresolved, rather than receiving an invented filename or canonical ID.

## Required private record and checks

| Area | Required information and decision |
|---|---|
| Identity and authority | Canonical source-object/study/family references when resolved; authoritative origin, exact name and object type; published version or documented immutable capture; publication/deposit/correction relationship. An unresolved canonical link stays unresolved. |
| Retrieval and integrity | Actual retrieval time, route and retained location; complete-byte size and full SHA-256; independent check of the retained bytes; container/member identity where relevant. Before retrieval, hash and byte size remain null under the source schema. A prefix/header hash never becomes `FULL_OBJECT`. |
| Terms and custody | Object-level access and redistribution terms, approved access/retention authority, named allowed readers and custody/retrieval history. Keep private paths, access records and authentication material in the authorized system. Public availability does not prove redistribution permission. |
| Inspection scope | Format/version and exact sheet, table, section or header scope examined; whether the file is complete and readable; every source locator needed for a later assertion. A listing or format pass is not substantive inspection. |
| Availability | Separately record located, retained, inspected, unreadable/truncated, unavailable, superseded and still uninspected facts with their basis. Use the existing schema's retrieval and validation enums for canonical records; these checklist words do not add schema enums. “Not in inspected objects” is not a claim of global absence. |
| Coverage and limits | Required-role-to-object links; objects considered but not usable; missing required evidence and dependent questions; repository/publication-family search scope, queries/versions if used and unresolved completeness limits. An inventory shape cannot prove completeness. |
| Provenance | Reviewer/custodian authentication reference and actual activity date, object version, source locator, rule version and supersession links. Dates and identities must be verified in the authorized system, not filled with this plan's author/date. |

The [access policy](../../../specs/A_DATA_ACQUISITION_VALIDATION/ACCESS_PRIVACY_AND_REDISTRIBUTION.md) applies. Prat's narrower existing review-export boundary also applies: the populated inventory and detailed custody evidence stay private. This local plan receives neither a populated registry nor patient-free object details exported by implication.

## Seal the common review basis

After the custodian has justified the scoped required object set, retain a private immutable manifest with exact entries, required/optional status, completeness limitations, versions, whole-object hashes and an explicit version. Seal its digest. Bind the required-object set and inventory scope separately so omitting an object cannot preserve apparent acceptance. Distinguish this object-manifest seal from the separately hashed reader-authored contracts.

The common basis also binds the branch, fixed question set, policy/version, schema set, rule-language definition and executor/auditor code versions. It gives both readers the same evidence and questions, **not common answers**. Use the existing synthetic procedure's basis names as a compatibility reference only; they do not authorize real-data execution. [Existing procedure code](../../../tools/a_dav/prat_review.py)

A missing required object, unexplained version difference, hash mismatch or unresolved permission prevents the dependent review from passing. Record useful partial findings with their scope, but do not claim complete review. A replacement/correction creates a new manifest/basis version and reopens affected first passes, comparisons and receipts. Keep the originals and explain the dependency impact; do not silently substitute bytes or copy old approvals.

The private inventory is ready for reader work only after the custodian and an authorized reviewer have checked authority, scoped completeness, terms/custody and retained-byte identity. Neither that operational check nor an object seal was performed here.
