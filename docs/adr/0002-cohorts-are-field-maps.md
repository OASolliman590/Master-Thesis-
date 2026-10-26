# Cohorts are declarative field maps over a small set of format adapters

Code contains only format adapters: GEO family SOFT, delimited table and matrix header. Everything cohort-specific lives in a patient-free JSON field map, validated against a schema. Examples are sample-title regexes, which characteristic carries the visit or response, positional reads of duplicated headers, and sample-name rules.

The rejected alternative was one Python parser per cohort. That approach multiplies code and review effort with every source, and it hides each cohort's rules inside its code. With field maps, adding a cohort (for example Hugo or Gide) means writing a new field map and its tests. A new format adapter is added only when a new file format appears.

Ingestion reads source objects only by SHA-256 from a private content-addressed store. It never fetches over the network and never resolves an ambiguity itself. Every conflict becomes a worksheet item for a human to decide.
