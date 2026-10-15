# Activation, order and noninterference

## State machine

`DORMANT -> INVENTORIED -> ELIGIBLE_FOR_REVIEW -> AUTHORISED -> INGESTED -> ROLE_FROZEN -> FIT_OR_EVALUATE -> REVIEWED_RELEASE`.

At any transition use `DEFERRED_NO_DATA`, `BLOCKED_CORE`, `BLOCKED_PERMISSION`, `QUARANTINED_QC`, `BLOCKED_IDENTITY`, `BLOCKED_CONTEXT`, `INSUFFICIENT_CAPABILITY` or `WITHDRAWN_PERMISSION` with a specific reason. These are extension statuses, never core failures. Reconsider when a versioned object/capability changes, not by repeated polling or invented data.

## Foundation gate

Verify core release hashes, complete profile, E0–E7 receipts, source-role ledger, uncertainty/configuration, software/environment identity, scientific review and reproduction. A C-IDENTIFIABILITY foundation is eligible: the extension may target the measured quantities that the core proved missing. Core scientific incompleteness is not bypassed because an experimental dataset happens to exist.

## Data and authority gate

Require generated actual records, appropriate approved-use scope, provenance/identity, QC admission, known independent-unit grouping, lawful secure access and an assigned role. Unknown approval or unknown QC is not approval. Require a reviewed assay/context-to-state mapping for quantitative use. A file extension or a nonempty matrix is not a capability.

## Last-stage scheduling

Core implementation E0–E7 finishes first. X0–X5 implementation is released after core handoff. Preparing this spec, recording approved experiment metadata and planning a future challenge can happen earlier. A prospective freeze may be created after foundation completion and before the separate new experiment; it never retroactively predates observations already seen.

Do not require completion of every A–D paper. Only optional interfaces actually consumed must be frozen and source-qualified. The biological paper need not be accepted/published for permitted original data to be used; their generation, approval/QC and role are the relevant gates.

## Noninterference

Read the frozen foundation; write only a new namespace such as `runs/e_last/<extension_id>/`. Never update core release weights, role labels, fitted parameters, figures or completion status in place. A core error discovered during comparison is handled as a transparent erratum/new core version, not overwritten silently. Failed or contradictory extension results are retained and do not become evidence that a prior computational claim was experimentally established.
