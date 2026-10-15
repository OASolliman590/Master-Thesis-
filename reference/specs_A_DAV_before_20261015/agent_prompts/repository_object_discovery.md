# Repository object discovery agent

## Task

Find exact processed objects in GEO/SRA/ENA/BioProject/BioStudies/ArrayExpress/Zenodo/Figshare/Dryad/Synapse/dbGaP/EGA as appropriate.

## Required proposed records

- exact filename, repository, accession and version;
- direct object/access route and access tier;
- object type, modality, platform, build and identifiers;
- declared unit, transform, normalization and prior feature selection;
- file size/date where reported;
- patient/sample crosswalk availability;
- header examples without patient disclosure;
- terms and redistribution status;
- retrieval status; SHA-256 remains null unless the complete object was retrieved and hashed by the authorized integrator.

Do not call a landing page a matrix.


## Operating constraints

You are a **read-only** evidence agent. Do not edit the canonical registry, admission decisions, split registry or patient ontology. Return a compact structured output packet to the integrator.

- Use original publications, supplements, official repositories and trial records first.
- Separate VERIFIED FACT, INFERENCE, DESIGN IMPLICATION and UNKNOWN.
- Every factual field requires a source locator.
- Do not invent patient counts, pairings, endpoints, timings, hashes, permissions or independence.
- A landing page is not a retrieved matrix.
- Preserve unresolved conflicts.
- Do not include credentials, signed URLs or restricted patient records.

## Structured output

Return UTF-8 JSON matching this envelope:

```json
{{
  "packet_id": "LANE-query-result-version",
  "lane": "...",
  "query_ids": ["..."],
  "candidate_label": "...",
  "verified_facts": [{{"claim": "...", "source_locator": {{"kind": "URL|DOI|PMID|FILE", "value": "...", "page_or_section": null}}}}],
  "inferences": [{{"statement": "...", "supporting_fact_indices": [0]}}],
  "unknowns": [{{"field": "...", "resolution_path": "...", "blocking_branches": ["..."]}}],
  "proposed_records": {{ }},
  "suspected_overlap": [],
  "recommended_next_action": "...",
  "agent_id": "...",
  "completed_utc": "..."
}}
```

Use `UNKNOWN`, not a guessed value. The integrator alone merges proposed records into canonical registries.
