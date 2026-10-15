# Access, privacy and redistribution

## Public-repository assumption

The primary repository is public. The specification therefore uses a patient-free public layer and an authorized private data layer.

## Public Git may contain

- schemas, code and tests;
- patient-free study/source registries;
- source URLs/accessions and permitted checksums;
- synthetic fixtures;
- aggregate counts and validation summaries;
- retrieval instructions;
- decision logs and tickets.

## Public Git must not contain

- raw patient IDs or alias crosswalks;
- patient-level clinical, treatment, specimen or split tables by default;
- controlled-access data;
- signed URLs, tokens, sessions or credentials;
- unpublished clinical records;
- restricted source bytes;
- private storage paths that reveal credentials or protected infrastructure.

## Logical storage classes

| Class | Contents | Public Git |
|---|---|---|
| `PUBLIC_SPEC` | contracts, schemas, prompts, synthetic tests | yes |
| `PUBLIC_SOURCE_METADATA` | patient-free source records, permitted hashes | yes |
| `PRIVATE_CROSSWALK` | raw aliases to project UIDs | no |
| `PRIVATE_PATIENT_REGISTRY` | patient-level normalized records | no |
| `PRIVATE_DERIVED_MATRIX` | branch matrices and split assignments | no by default |
| `CONTROLLED_SOURCE` | dbGaP/EGA or source-restricted objects | no |
| `PUBLIC_AGGREGATE_RECEIPT` | counts, gates and limitations | yes |

## Pseudonymization

Project UIDs are stable strings generated under private authorized configuration. The raw-to-project map and any secret/salt never enter the repository. IDs preserve source distinctions and do not embed names, dates or source patient IDs.

## Controlled access

A controlled source requires:

- approved application and named authorized users;
- local institutional authorization;
- source-specific processing/reporting terms;
- permitted storage and retention plan;
- access-expiry handling;
- release review ensuring no restricted fields or small-cell disclosures enter public outputs.

The system never bypasses controls. Controlled access is optional until a named branch demonstrates material need.

## Redistribution

Public accessibility is not equivalent to redistribution permission. Record terms at object level. If redistribution is unclear, publish retrieval instructions and hashes rather than bytes.

## Automated public-release scan

Before commit or PR:

- scan for credentials/tokens/signed URLs;
- scan for raw patient identifiers and restricted paths;
- verify templates contain headers only;
- verify receipts are aggregate;
- verify no controlled bytes are staged;
- fail closed and require reviewer disposition.

## Incident response

If restricted data are committed, stop release, revoke exposed credentials/URLs where applicable, remove the data through an approved history-remediation process and document the incident privately. A normal follow-up deletion is insufficient for sensitive history.
