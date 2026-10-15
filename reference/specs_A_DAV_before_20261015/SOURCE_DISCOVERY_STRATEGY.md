# Source discovery strategy

## Objective

Build a versioned candidate universe that can be traced from catalogue or citation to the original study, exact source object and branch-specific acquisition decision. Discovery increases recall; admission preserves validity.

## Questions searched separately

1. Pretreatment tumour expression with clinical ICI response.
2. Baseline plus serial tumour expression under ICI.
3. Progression or acquired-resistance biopsies.
4. Actual comparative treatment arms with serial sampling.
5. Paired RNA–methylation, RNA–ATAC, RNA–protein or other orthogonal modalities.
6. Tumour plus blood/plasma with explicit patient/time linkage.
7. Single-cell or spatial corroboration linked to treated patients.
8. Prostate molecular transport sources.
9. Controlled-access objects that materially unblock a prespecified branch.
10. Prior predictor/signature development and method overlap.

## Source families

### Catalogues and curated resources

Search ICBatlas, TIGER, IOhub, Cancer-Immu, the current 77-reference queue, the historical 47-row registry and prior rosters. Catalogue labels are discovery leads only.

### Bibliographic and trial sources

Search PubMed, Europe PMC, Crossref-linked journal pages, trial registries, supplementary materials, institutional repositories, corrigenda and later molecular/follow-up publications.

### Data repositories

Search GEO, SRA, ENA, BioProject, BioStudies, ArrayExpress, Zenodo, Figshare, Dryad and Synapse. Search dbGaP/EGA for feasibility without bypassing access controls.

## Query architecture

Every query receives a stable `query_id` and logs:

- lane and source;
- exact query string;
- UTC timestamp;
- filters and date limits;
- page/cursor coverage;
- result identifiers;
- screened count;
- candidate disposition and reason;
- follow-up action;
- completion status;
- agent or reviewer identity.

The search log is append-only. A corrected disposition creates a new row linked to the superseded row.

## Discovery sequence

1. Reconcile every existing queue row before adding new candidates.
2. Resolve accession aliases and superseries/subseries.
3. Identify the original clinical publication/trial.
4. Search publication family, supplementary files and corrigenda.
5. Search repository objects and alternative mirrors.
6. Run backward and forward citation searches.
7. Search for later data releases and updated matrices.
8. Search predictor/signature development cohorts for exposure overlap.
9. Record unresolved leads rather than dropping them.

## Candidate inclusion at discovery

A lead enters the candidate registry when it plausibly contains one of the required evidence types and has a source locator. Discovery does not require patient-level eligibility.

## Candidate exclusion at discovery

Do not delete a lead. Assign a reason-coded disposition such as:

- non-ICI treatment;
- vaccine or adoptive-cell study;
- mechanistic cell model;
- untreated molecular cohort;
- wrong endpoint;
- no patient-level route;
- no molecular data;
- duplicate/reanalysis;
- inaccessible or unavailable object;
- wrong biological compartment;
- outside branch scope.

Non-ICI evidence can remain in a mechanistic/supporting inventory but cannot enlarge the Paper A clinical response denominator.

## Version-freeze stopping rule

A search version may freeze only when:

- all predefined source families were searched;
- every pre-existing queue row has a disposition;
- every included lead is traced to an original study;
- publication families and aliases are reconciled;
- repository availability is checked;
- backward, forward and update searches are recorded;
- unresolved records are preserved with resolution paths;
- an independent reviewer checks a sample of included and excluded records.

The method may be called systematic only when its declared protocol and coverage justify that wording. Otherwise use “structured, versioned source discovery.”

## Update policy

Before each scientific release, rerun update searches from the prior freeze date. New sources cannot be inserted into a frozen final-test role after performance is known; they enter a new release version.
