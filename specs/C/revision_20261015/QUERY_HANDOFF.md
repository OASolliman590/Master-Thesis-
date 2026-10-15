# Paper B to Paper C query handoff

## Required products

Paper B must export two separate, versioned products:

- `Q_E`: expression-only, clinically anchored prostate immune-barrier query;
- `Q_M`: methylation-supported query derived under the same discovery and budget rules.

The handoff is row-based and machine-readable under `schemas/query_handoff.schema.json`.

## Shared eligibility

A gene may enter either query only if all are frozen before C outcomes:

1. a Paper A clinical programme supplies the desired biological direction;
2. Paper B demonstrates the relevant prostate deficit under a declared contrast;
3. the gene is addressable in the intended tumour-cell perturbation question or is explicitly labelled microenvironment-only;
4. effect, uncertainty, annotation and multiplicity provenance are available;
5. source patients and discovery split are declared;
6. prior exposure to clinical outcomes is declared;
7. composition, purity and genetic alternatives are retained rather than silently filtered.

A predictive coefficient is not automatically a restoration direction. A methylation–RNA association is not proof of reversibility.

## Fair `Q_E` versus `Q_M` construction

Within every programme and direction block:

- both queries use the same source patients;
- both use the same expression eligibility and ranking rule;
- both have the same quota `k[p,d]`;
- `Q_M` applies a frozen methylation-support gate before the same expression ranking rule;
- `Q_E` does not use methylation evidence;
- tie-breaking is deterministic and outcome-blind;
- overlap between the two queries is permitted and reported;
- no perturbation, viability, PK or wet-lab result selects genes, weights, direction or size.

If fewer than `k[p,d]` genes pass the methylation gate, that programme-direction block is ineligible for the paired primary. It is not padded with unsupported genes.

## Direction

Queries are oriented as the desired restored state:

- `desired_up`: treatment should increase the gene/programme;
- `desired_down`: treatment should decrease the gene/programme.

A biologically one-sided programme remains one-sided. The other direction must not be manufactured for WTCS. `SCORER_CONTRACT.md` defines separate bidirectional and one-sided paths.

## Required row fields

- query and programme IDs;
- gene identifier and annotation release;
- desired direction;
- A clinical effect, uncertainty and cohort stability;
- B expression deficit, uncertainty, contrast and multiplicity;
- methylation feature, region, direction, model and uncertainty;
- methylation-support gate result;
- composition/purity sensitivity;
- tumour/immune/stromal localisation evidence;
- CNA/mutation/other regulatory alternatives;
- source patient set and split;
- prior outcome exposure;
- L1000 landmark/inference/absence tier;
- selection rank and deterministic tie key;
- source hashes and query hash.

## Leakage boundaries

- CPC-GENE outcomes may not select a query later presented as independently CPC-validated.
- C perturbation effects may not alter B query membership or direction.
- independent validation outcomes may not select eligible contrasts, genes or top-k.
- Paper D predictions may not alter the primary query.

## Freeze sequence

1. Freeze A programme version.
2. Freeze B discovery patients and contrasts.
3. Freeze expression eligibility/ranking and methylation gate.
4. Produce `Q_E` and `Q_M` with hashes.
5. Validate quotas, directions, coverage and leakage fields.
6. Approve the query release.
7. Only then expose C perturbation outcomes.
