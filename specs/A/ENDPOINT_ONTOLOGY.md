# Endpoint ontology — Paper A consumer rules

The authoritative schema and raw-to-canonical assertions live in the shared acquisition package. This file tightens A's branch admission and never overwrites source labels.

## Radiographic objective response

Where the original study's assessment definition is recoverable, CR/PR map to ORR=1; SD/PD map to ORR=0. NE/UNK or unassessed outcomes remain null and are excluded from an ORR-evaluable analysis with reasons. Record RECIST version, iRECIST/irRECIST or other source system, best-overall versus landmark assessment, day/window and index treatment episode. Binary R/NR without a documented definition is SOURCE_BINARY_UNKNOWN, not RECIST. Binary labels with an explicit equivalent objective-response definition may enter a separately documented source-binary ORR stratum; never fabricate missing CR/PR/SD/PD.

## Disease control and durable benefit

DCR=1 for source-supported CR/PR/SD and 0 for PD; unknown categories remain unknown. DCB is a separate endpoint requiring the source's duration threshold and follow-up/censoring logic. A censored patient before the durable-benefit threshold is not automatically a nonbenefiter. Do not infer SD from 'nonresponder'. Lack of DCR labels does not block a valid ORR branch.

## Other clinical endpoints

PSA response, pathological response, PFS and OS have distinct endpoint_id records, definitions and censoring. They do not become ORR labels. Sequential-regimen outcomes retain the actual episode and cannot isolate a component's efficacy. Response assessed after a follow-up biopsy describes retrospective response-associated change; it is not prospective dynamic prediction without a landmark design.

## Discrepancy handling

Preserve each original assertion with object/hash/locator and mapping version. The curator documents disagreements between paper, supplement, repository and atlas. Resolve only through source-supported adjudication with a named reviewer; do not privilege a convenient matrix label because execution otherwise succeeds. Rebuild all dependent matrices after an endpoint correction; retain prior versions and exposure consequences.

A-P1 category-composition and estimability rules are in ENDPOINT_SENSITIVITY.md. Endpoint curation and class counts can be inspected for design feasibility. Molecular–outcome relationships or final-test performance cannot be used to select the endpoint or scoring method.
