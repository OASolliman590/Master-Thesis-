# Source discovery and executable retrieval specification
> **v2 operating contract:** Core numerical evidence is external public evidence. References to culture, assay, donor or experimental data below mean source-attributed published measurements in core, not a requirement to generate local data. Original project integration is exclusively E_LAST after core release. Core profiles and release gates are defined in CORE_COMPLETION_CONTRACT, not legacy D01–D14 labels. Technical observation/identity restrictions apply unchanged.


## Bounded search lanes

PK; epigenetic target/temporal PD; antibody pharmacology; prostate/immune function; upstream model assets; independent validation. Each read-only lane emits candidate objects and a search receipt. One integrator resolves publication families, shared trials/controls, model-training overlap and canonical IDs. No lane independently admits data or downloads private objects.

Use exact DOI/PMID/NCT first, then compound synonyms plus question-specific terms. Initial queries are in SEARCH_LOG.tsv. Stop a lane after the named precedents, their direct references/supplements and two bounded query pages yield no new eligible original study. Record saturation as a bounded search result, not evidence of exhaustive absence. Reopen when the lead/assay changes, a blocked source becomes public, a new final article supersedes a preprint, or before scientific/manuscript freeze.

## Question → object → parser → table → role

| Question | Query/identifier and official route | Object/parser/validation | Destination and role |
|---|---|---|---|
| What model already exists? | S001 DOI via Europe PMC; S002/S003 exact DOI via publisher | Article metadata/JATS/HTML and actually linked supplements; verify DOI/title/version | studies, families, model_assets; context/reconstruction only initially. |
| Human small-molecule PK? | Compound+pharmacokinetics; Drugs@FDA application/clinical pharmacology documents | Original review PDF/table/figure, route/analyte/time/N validation | dosing_events, PK observations; role assigned after independence audit. |
| Antibody PK/target binding? | Selected molecule+population PK/receptor binding; open regulatory review and primary papers | Exact population summaries/equations, target/assay and covariate checks | parameter_evidence/model_assets; not automatic culture potency. |
| Trial context/outcomes? | ClinicalTrials.gov v2, exact NCT or condition/intervention search | Study JSON and posted original documents; regimen/timing/aggregate checks | studies/regimens/populations; contextual or actual endpoint evaluation. |
| Compound identity/activity? | ChEMBL molecule search, PubChem name/CID | JSON; parent/salt, standard relation/unit, target/assay/publication identity | compounds/formulations/parameter evidence; contextual potency only. |
| Prostate/immune perturbations? | GEO/BioStudies exact accession from original study | SOFT/MINiML metadata and exact processed supplement; sample/control/time/donor checks | assays/observations; no PK rates from expression signatures. |
| Existing model files? | Author repository, OSP/BioModels/Zenodo identity | Exact release/tree/file/licence; inspect equations before execution | model_assets; executable status only after runtime/parity. |
| PK-DB observations? | Compound and original-study identifiers at O07 | Exact current API/download object UNKNOWN; verify documentation before adapter | Optional discovery until verified; not required dependency. |

LINCS, CCLE/DepMap, PRISM, GDSC and GDC remain candidate molecular/context sources, not an assertion that they contain this drug's immune PD time course. Use the shared A–C acquisition handoff where verified, but preserve its role restrictions.

## Concrete read-only requests

These are target retrieval commands, not a claim they were executed or their responses retained. Use URL encoding rather than string substitution from untrusted metadata. Redirects require a reviewed host allowlist. A downloaded object is quarantined until content-type and identity validation.

```bash
# Article identity, not necessarily measurements.
curl --fail --get 'https://www.ebi.ac.uk/europepmc/webservices/rest/search' \
  --data-urlencode 'query=DOI:10.1007/s00280-017-3447-x' \
  --data 'format=json' --data 'pageSize=25' --data-urlencode 'cursorMark=*' \
  --output europepmc_s001.json
# Official drug-approval metadata search; follow actual returned document links.
curl --fail --get 'https://api.fda.gov/drug/drugsfda.json' \
  --data-urlencode 'search=products.active_ingredients.name:"VORINOSTAT"' \
  --data 'limit=1' --output fda_vorinostat_metadata.json
# Trial discovery. Persist returned nextPageToken before requesting another page.
curl --fail --get 'https://clinicaltrials.gov/api/v2/studies' \
  --data-urlencode 'query.cond=prostate cancer' \
  --data-urlencode 'query.intr=vorinostat' --data 'pageSize=10' --data 'format=json' \
  --output trial_candidates.json
# Compound identity discovery; selected molecule ID must be resolved, not guessed.
curl --fail --get 'https://www.ebi.ac.uk/chembl/api/data/molecule/search.json' \
  --data-urlencode 'q=vorinostat' --output chembl_candidates.json
```

Europe PMC uses returned cursorMark for continuation; ChEMBL uses returned page metadata/next links; trial v2 uses nextPageToken; openFDA limit/skip rules and ceilings must be checked from official documentation before expansion. Do not guess pagination by changing URLs indefinitely. Default local pacing is one request/second with one worker per host, a conservative project limit—not a claim about each service quota. Obey stricter current service limits and Retry-After.

## Retrieval receipt

Record query, query date, lane/curator, official route, actual resolved URL, object ID/version, page/cursor, HTTP status, format, parser/version, expected/observed content type, size/hash after retained retrieval, retries, cache status and stop reason. If blocked or unknown, size/hash remain null with reason. No invented URLs or filenames beyond actual source links. An API returning HTML/login instead of JSON is failure, not an empty dataset.
