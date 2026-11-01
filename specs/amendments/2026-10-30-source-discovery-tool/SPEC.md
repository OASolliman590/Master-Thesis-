# Source discovery tool (`tools/a_discovery`): spec, 30 Oct 2026

**Status:** requested by the user in chat on 30 Oct 2026 ("create a script that mechanistically can look up data in GEO, SRA, cBioPortal, more data sources; insert into spec kit and implement"). It is an additive tool. It implements Lanes A and C of `specs/A_DATA_ACQUISITION_VALIDATION/AGENTIC_SEARCH_ARCHITECTURE.md` as deterministic code and emits that spec's candidate-packet contract. No frozen spec changes.

## Purpose
Replace hand-run searches with one repeatable Python command. It finds and describes candidate ICI cohorts across public repositories, and it prepares raw-data processing (nf-core) inputs. It **reads metadata only**. Data files are still retrieved by `tools/a_dav/retrieval.py` through a reviewed fetch plan.

## Commands
```sh
python -m tools.a_discovery search  --queries <queries.json> --out .scratch/runtime/discovery/<run>
python -m tools.a_discovery resolve --id <GSE…|GSM…|SRP…|PRJNA…|PRJEB…|ERP…|E-MTAB-…|EGAS…|phs…|cbioportal:<study>|pmid:<n>> --out <dir>
python -m tools.a_discovery fastq   --project <PRJEB…|PRJNA…|SRP…|ERP…> --out <dir>    # run list, sizes, MD5s, nf-core samplesheet draft
python -m tools.a_discovery draft-fetch-plan --packet <packet.json> --cohort <id> --out tools/a_dav/fetch_plans/<id>.json.draft
```

## Source adapters (each: HTTPS only, host allowlist, timeout, retry with backoff, ≥0.34 s between NCBI requests)
| Adapter | Endpoint | Returns |
| --- | --- | --- |
| NCBI E-utilities | `eutils.ncbi.nlm.nih.gov` (`esearch`/`esummary`/`elink`; db = gds, sra, pubmed, pmc, bioproject) | Series and project lists, linked PMIDs, BioProject ↔ SRA ↔ GEO links |
| GEO | `www.ncbi.nlm.nih.gov/geo/query/acc.cgi` (text views) and the GEO FTP directory listing | Series facts, platform, sample count, characteristic keys, and **aggregate** value counts per key, plus supplementary file names and sizes |
| ENA portal | `www.ebi.ac.uk/ena/portal/api` (`filereport`, `search`) | Runs, library strategy and layout, instrument, `fastq_bytes`, `fastq_md5`, `fastq_ftp` |
| cBioPortal | `www.cbioportal.org/api` and the GitHub datahub (`api.github.com`, `raw.githubusercontent.com`) | Studies, sample and patient counts, clinical attribute names, molecular profiles, plus the pinned datahub commit and LFS SHA-256 per file |
| BioStudies / ArrayExpress | `www.ebi.ac.uk/biostudies/api` | Study facts and file lists |
| EGA | `metadata.ega-archive.org` | Study and dataset facts; marks the cohort CONTROLLED |
| dbGaP | Accession pattern plus E-utilities | Marks the cohort CONTROLLED (no further access) |
| Europe PMC | `www.ebi.ac.uk/europepmc/webservices/rest` | Title, journal and open-access flag; supplementary file list where the API provides it |

New adapters (for example Zenodo or Figshare) plug in through one interface: `search(query) -> list[Lead]` and `resolve(id) -> Record`.

## Outputs
- `packets/*.json`: one candidate packet per lead, using the field contract in AGENTIC_SEARCH_ARCHITECTURE.md. Facts carry a `source_locator` (URL plus field). Anything not found is `UNKNOWN`, never inferred.
- `candidates.tsv`: rows in the `specs/A/SOURCE_CANDIDATE_QUEUE.tsv` column format, with readiness R1/R2/R3/X:
  - R1 = processed matrix plus per-sample response in the repository;
  - R2 = matrix public, labels in the paper;
  - R3 = raw reads only, or controlled;
  - X = set aside.
- `fastq/<project>.tsv`, plus `samplesheet.nfcore.csv` (a draft; strandedness `auto`), plus a size total.
- `receipt.json`: the tool version and git commit; every request URL, timestamp, HTTP status and response SHA-256; and the query file hash. Any later run can be compared against it.

## Rules
1. Metadata only. It never downloads expression matrices, FASTQ or supplementary data files.
2. It never bypasses access controls, firewalls, CAPTCHAs or rate limits. Controlled studies are marked CONTROLLED and left alone.
3. **No patient-level identifiers in Git-bound outputs.** Sample or run accessions may appear only in `.scratch/runtime/` outputs. Response information appears only as aggregate class counts per key, which is allowed for planning (`specs/A/VALIDATION_AND_SPLITS.md`).
4. The NCBI contact email and API key are read from environment variables (`NCBI_EMAIL`, `NCBI_API_KEY`), never hard-coded or logged.
5. Its output is a proposal. Admission still needs a field map, a reviewed fetch plan, V3 and the signed worksheet.
6. It applies the cohort rules on its own: combination regimens (ICI plus a non-ICI drug) are tagged `COMBINATION`, and leads overlapping known families (by shared accessions or PMIDs) are tagged `POSSIBLE_OVERLAP`.

## Tests
Offline unit tests use recorded fixture responses, one per adapter. They cover rate limiting, retries, the HTTPS/allowlist refusal, the `UNKNOWN` behaviour, the no-patient-IDs rule for Git-bound outputs, combination and overlap tagging, and that the fetch-plan draft carries published hashes (LFS SHA-256, ENA MD5). A live smoke test is opt-in only (`A_DISCOVERY_LIVE=1`).
