# Machine-readable search plan and stopping amendment

## Search execution versus specification

search_plan.tsv contains planned work. templates/search_log.tsv is the authoritative execution-log shape; a plan row or query string does not demonstrate execution. source_search_update_log.tsv records only the bounded repository/literature checks actually performed in this revision. No comprehensive search completion, original-study census or systematic-review designation is claimed.

## Workstreams and integration

S1 resolves ICBatlas, TIGER, IOhub, Cancer-Immu, the 77-reference queue and historical rosters. S2 resolves original publications/supplements/corrections and trial families, including backward/forward citation chasing. S3 resolves official GEO/SRA/ENA/BioProject/BioStudies/ArrayExpress/Zenodo/Figshare/Dryad/Synapse/dbGaP/EGA processed objects and access terms. S4 targets baseline/on/progression/after-stop and comparative/sequential regimens. S5 maps measured RNA/methylation/chromatin/protein/single-cell/spatial/tumour-blood combinations at patient/time/specimen levels. S6 updates predictors/benchmarks and their training/source reuse. Workers produce read-only evidence packets; one integrator owns registry writes and conflict resolution.

Every packet includes exact query, source, actual execution date, pagination/export counts and caps, result IDs, inclusion decision/reason, original locator, unresolved items and next action. Agents' summaries are not evidence; verify original objects/publications. Publication family and accession-neighbour/superseries review are mandatory for included leads. Separate raw-read availability from processed-object availability.

## Stopping rule replacing the historical shortcut

A frozen version is complete only when all predefined source/query families have documented executed coverage; actual pages/exports and source-imposed limits are recorded; every existing queue row has a disposition; included studies are traced to originals; potentially eligible publications have a data-availability review; aliases/overlaps are reconciled; backward/forward and family chasing are recorded; and an update date plus unresolved-source register is frozen. Two pages with no new eligible results do not establish exhaustion of ranked results. A capped/inaccessible source is explicitly PARTIAL/BLOCKED with its unsearched remainder and effect on scope, never silently COMPLETE.

No favourable model result can terminate a source search or remove a frozen study. Search completeness is relative to the disclosed protocol/source universe, not proof that every study worldwide was found. A specific branch may use a reviewed bounded universe with its own gate, while the broader search continues under a new version; it must not claim the broader search was complete.

## Privacy and reproducibility

Public logs contain study/source-level records only; patient identifiers, signed URLs, credentials and restricted paths are excluded. Retrieved bytes are hashed separately. Catalogue DEG tables or outcome-derived modules encountered during search enter the exposure ledger and are kept outside reserved-test development. Historical queue records and the original draft stopping rule remain preserved with this dated supersession.
