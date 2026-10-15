# Clinical endpoint ontology

## Objective

Preserve source truth while enabling explicit, versioned, branch-specific mappings. Original labels are immutable; derived endpoint fields never overwrite them.

## Endpoint classes

- complete response (`CR`);
- partial response (`PR`);
- stable disease (`SD`);
- progressive disease (`PD`);
- not evaluable (`NE`);
- unknown;
- objective response (`ORR`);
- disease control (`DCR`);
- durable clinical benefit (`DCB`);
- PSA response;
- pathological response;
- progression-free survival (`PFS`);
- overall survival (`OS`);
- time to progression;
- recurrence/progression;
- source-specific binary response.

## Required source fields

```text
outcome_id
patient_uid
raw endpoint label
endpoint class
assessment criteria and version
assessment date/day and window
best overall response where reported
raw binary-response definition where used
event time, indicator and censoring for time-to-event outcomes
source locator
```

## Canonical mappings

### ORR

Default Paper A ORR mapping where source categories are available:

```text
CR/PR -> objective responder
SD/PD -> objective nonresponder
NE/unknown -> not evaluable
```

This is a branch mapping, not a claim that SD and PD are biologically equivalent. The original category remains available.

### DCR

```text
CR/PR/SD -> disease control
PD -> no disease control
```

Duration is not implied.

### DCB

Requires the study’s declared benefit rule and duration threshold. A duration threshold cannot be reconstructed from PFS or treatment duration without a prespecified, source-supported rule.

## Prohibited mappings

- infer SD from “nonresponse”;
- turn PSA response into radiographic ORR;
- turn PFS/OS into response;
- treat a short censored follow-up as nonbenefit;
- convert a source-specific binary group to RECIST categories without evidence;
- use publication group totals to assign individual outcomes;
- overwrite conflicting source labels.

## Conflict resolution

Conflicting outcomes create separate assertions and a discrepancy state. Resolution priority:

1. source patient-level clinical table tied to the study;
2. corrected supplement/erratum;
3. original study code with explicit patient mapping;
4. repository sample metadata;
5. curated atlas label.

A lower-priority source may expose a conflict but cannot silently replace the higher-priority record.

## Branch eligibility

- `A_BASELINE_BIO` and A-P2 branches require evaluable objective-response mapping or a separately declared source-binary endpoint branch.
- `A_P1_ENDPOINT_SENSITIVITY` requires recoverable CR/PR/SD/PD categories so SD membership can change.
- survival outcomes remain separate secondary branches.
- a cohort can pass ORR but fail DCB sensitivity, or vice versa.

## Mapping receipt

Every mapping release records rule/version, category counts before and after mapping, discrepancies, excluded/unevaluable records and reviewer sign-off.
