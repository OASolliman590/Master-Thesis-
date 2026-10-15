# Treatment-exposure and timepoint ontology

## Treatment exposure

One row represents one patient × treatment episode/component. Required distinctions:

- index ICI versus prior ICI;
- no prior ICI versus no prior systemic therapy;
- monotherapy versus combination;
- combination components;
- sequence and line of therapy;
- start/stop day/date;
- dose/schedule where reported;
- steroids or immunosuppression where available;
- progression/discontinuation relationship;
- certainty and source.

Pre-nivolumab after prior ipilimumab is not ICI-treatment-naïve. Unknown history remains unknown.

## Raw and canonical time

Raw timing text and exact dates/days are preserved. A canonical category is a versioned assertion relative to an explicit reference event.

Canonical categories:

- `PRE_INDEX_BASELINE`;
- `EARLY_ON_TREATMENT`;
- `LATE_ON_TREATMENT`;
- `RESPONSE_ASSESSMENT`;
- `MAXIMAL_RESPONSE`;
- `PROGRESSION`;
- `POST_TREATMENT`;
- `POST_DISCONTINUATION`;
- `AFTER_REGIMEN_CHANGE`;
- `UNKNOWN`.

## Required time assertion

```text
raw timing text
collection date/day
reference treatment episode
days from treatment start
days from treatment end
days from progression/assessment
canonical category
mapping rule/version
mapping confidence
pooling permission
source locator
```

## Rules

- never infer timepoint from row order;
- never infer same specimen from the same patient ID;
- do not call every follow-up “post”;
- progression and scheduled on-treatment samples are separate;
- a sample after a regimen change belongs to that state even if the repository calls it “on treatment”;
- exact day conflicts remain discrepancies;
- broad time labels may support discovery but can fail a narrow longitudinal window.

## Window registry

Each longitudinal branch uses a versioned window definition, for example:

```text
A1_EARLY_ON_V1: day 14–42 from index start, before progression and before regimen change
A1_LATE_ON_V1: after day 42, before progression and before regimen change
A1_PROGRESSION_V1: collection at or after documented progression, before subsequent systemic therapy where required
```

These examples are design placeholders until source feasibility and Paper A.1 analysis review freeze exact windows.

## Treatment and timing discrepancies

Failure codes include:

```text
INDEX_TREATMENT_UNRESOLVED
PRIOR_ICI_UNKNOWN
TREATMENT_SEQUENCE_CONFLICT
COLLECTION_CHRONOLOGY_CONFLICT
TIMEPOINT_ONLY_INFERRED_FROM_ORDER
FOLLOWUP_AFTER_REGIMEN_CHANGE
PROGRESSION_DATE_UNKNOWN
WINDOW_NOT_IDENTIFIABLE
```
