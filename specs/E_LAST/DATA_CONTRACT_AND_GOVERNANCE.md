# Original-data contract and governance

State sequence: planned → approved → generated → quality_checked → admitted → assigned_role. Each state has a date, responsible person, evidence reference and use scope. Do not infer institutional approvals from a thesis proposal, self-donation, purchase list or this specification.

Records link experiment ID/question/date, cell-model source/authentication/mycoplasma/passage where known, pseudonymous donor/preparation, independent culture/donor grouping, operator/batch/plate/well/instrument, reagent lot/clone/isotype/formulation/vehicle, culture conditions and viable ratios, exposure addition/removal/washout/sampling events, raw assay files, processing version, QC/exclusion/missingness reasons and allocation/blinding where feasible.

Hierarchy is donor/independent culture preparation → experiment/batch/plate → well → technical read/time. Define the independent unit separately for every assay. Passage labels, many wells or repeated readings do not establish independence. Shared controls and paired samples retain their dependence.

Use immutable raw storage under institutional control, versioned deidentified derivatives and separate restricted donor-key storage. Public code/manifests contain pseudonyms or non-identifying group references only where permitted. Exclude consent forms, signed protocols, identifiable dates/linkages, direct identifiers and credentials from releases. Role assignments and access/release permissions are separate.

Assay files may be measured but unusable for a particular model: Cq without reference stability, fluorescence without consistent settings, mixed tumour/immune viability, a concentration without dosing times, and unknown biological grouping trigger limited use or quarantine. Preserve original units/statistics and censoring; transformations retain code/hash and curator verification.

Use legacy observation/assay/event/experiment/role schemas distributed locally in `schemas_compat/` as syntax contracts, plus `schemas_v2/capability_snapshot.schema.json` and `extension_activation.schema.json` as use gates. Syntax validity alone never grants a role. Populate no fabricated experimental rows; example records are unmistakably synthetic.
