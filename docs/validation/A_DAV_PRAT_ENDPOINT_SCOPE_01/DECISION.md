# Endpoint summary scope for the Prat training form

**Settled for training form v3 only.** The grouped `endpoint` disposition summarizes native endpoint meaning and individual assessment evidence. Same-patient/same-episode matching is separately recorded and cross-referenced to `episode_bindings`. The full endpoint question still requires all of them. No endpoint becomes usable or admitted from its summary label.

In the previous invented case INV-C02, the native value's meaning and assessment are missing: the endpoint summary is therefore `UNRESOLVED`. The unsupported ALPHA transfer remains a separately visible episode conflict against the BETA-only native binding. Preserve the native value, both proposed bindings with their unequal authority, and all source locators. The previous CONFLICTING/UNRESOLVED reader labels and seals remain unchanged; this new instruction is not backdated into those passes.

## The form rule

For the endpoint assertion, add an `endpoint_components` object containing:

| Field | Meaning |
|---|---|
| `summary_scope` | Fixed `NATIVE_ENDPOINT_MEANING_AND_ASSESSMENT` |
| `meaning_disposition` | Evidence for the original endpoint definition, vocabulary and any required duration premise |
| `assessment_disposition` | Evidence for the individual assessment, assessment system/version, evaluability, assessment date/day and window, or their documented gaps; do not infer it from totals or a native label alone and do not invent a timing default |
| `episode_link_disposition` | Evidence for the proposed same-patient/same-index-episode link, including retained conflicts and gaps |
| `episode_question_reference` | Fixed `episode_bindings`; it does not substitute for the actual assertion and its locators |
| `actual_use_authorized` | Always false in this synthetic form; never an approval or admission field |

The local summary rule is: a supported contradiction within meaning/assessment yields `CONFLICTING`; otherwise both supported yields narrowly `SUPPORTED`; both unaddressed yields `NOT_IN_INSPECTED_OBJECTS`; any other incomplete combination yields `UNRESOLVED`. These are training-summary instructions, not a new canonical clinical precedence rule. Unsupported proposals do not acquire source authority and hypothetical alternatives do not become adjudicated source contradictions.

An episode-only conflict is not used to replace the meaning/assessment label. It must still be reported and must withhold use. A supported definition and assessment with an unknown or conflicting episode link cannot complete the original question or pass a consumer gate. Actual use remains false even in a fully supported invented example.

`episode_link_disposition` concerns the proposed specimen/outcome use for this case. An unsupported ALPHA transfer does not globally invalidate a distinct native BETA assessment or decide another branch's eligibility. Keep each assertion and its intended episode/use explicit.

## Frozen requirements still apply

The original seven question IDs/texts remain unchanged. The endpoint question still asks for the native meaning **and the same-episode individual assessment**. The extra component record exposes that requirement rather than removing it. No frozen schema, runtime input, source-specific endpoint variant or admission rule is changed. [Existing questions](../../evidence/A_DAV_PRAT_SOURCE_REVIEW_PLAN_01/REVIEW_QUESTIONS.tsv)

Raw labels remain immutable; conflicting source assertions and source priority remain in force. No source-binary-to-ORR/DCR/DCB conversion, individual assignment from group totals or outcome transfer across episodes is permitted. [Endpoint ontology](../../../specs/A_DATA_ACQUISITION_VALIDATION/ENDPOINT_ONTOLOGY.md#conflict-resolution), [episode integrity](../../../specs/A_DATA_ACQUISITION_VALIDATION/RELATIONAL_INVARIANTS.md#episode-integrity).

The new fields belong only to [FORM_V3.json](FORM_V3.json). They are not additions to `clinical_outcome`, `episode_binding` or any other canonical record. Missing approval remains an authority gap; this coding-scope decision establishes no software defect or real-source finding.
