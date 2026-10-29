# Riaz baseline policy

`baseline_policy.py` builds a new `A_BASELINE_BIO` packet from a canonical ingestion
packet and then calls `review_prepare` to rebuild registries and metadata stages. The
branch packet includes identity-verified `PRE_INDEX_BASELINE` specimens and their linked
patients, assays, outcomes, treatment episodes, exposures and bindings. It preserves the
complete source inventory and the original ingestion questions. `On` records remain in
the raw source objects and their questions stay visible as outside this branch.

The endpoint configuration uses author clinical `BOR` as the source of record and RECIST
v1.1 as documented by the original article. CR/PR map to positive ORR, SD/PD to negative
ORR, and NE/unknown to null. Raw BOR and corroborating GEO labels remain available in the
source evidence. Only a specifically evidenced NE/UNK vocabulary pair receives a
proposed discrepancy crosswalk; other conflicts remain unresolved. The endpoint mapping
version is set on both configuration and derived source outcomes before registry rebuild.

## QC proposal

The QC rules and remaining decisions are recorded in [the Riaz QC proposal](../../docs/research/A_DAV_RIAZ_QC_PROPOSAL_20261026.md).
That proposal is pending reviewer decision and is not applied by this tool. It keeps
source retention, assay QC, ORR evaluability and admission separate; it also leaves the
four script removals and separate PCA exclusion as historical flags. Numerical matrix
checks and representation selection remain pending.

The implementation does not apply these QC proposals, choose an assay representation,
infer dates, resolve overlap or prior exposure, or set admission flags. This version
rejects populated overlap/prior-exposure tables rather than silently dropping them from
branch scope. `review_prepare` emits a fresh unsigned worksheet. The frozen
`episode_binding` schema requires a human reviewer and review time for VERIFIED
bindings; the CLI creates no such binding, signature or reviewer date. Endpoint mapping
therefore remains blocked until source-supported bindings receive legitimate review.

## Signed admission and V8 baseline build

Use `tools.a_dav.admit` when a worksheet is signed. The fresh-ingest form below reads only
the local content-addressed store, rebuilds the branch packet and assay policy, and checks
the signature context before admission. If the worksheet context changed, it writes a
private item diff and stops. If it matches, it validates the signature, regenerates
declared proposals, runs registries, endpoints, timing, assays, overlap, exposure and
admission with the resulting dependency receipts, then attempts the split and baseline
matrix stages. All outputs are private and must be written below `.scratch/runtime`.

```sh
PYTHONDONTWRITEBYTECODE=1 ../envs/dav-pipeline/bin/python -m tools.a_dav.admit \
  --cohort <cohort> --branch <branch> \
  --store .scratch/runtime/<cohort>/store \
  --v3-receipt .scratch/runtime/<cohort>/<v3-run>/receipt.json \
  --field-map tools/a_dav/field_maps/<cohort>.json \
  --worksheet .scratch/runtime/<cohort>/<signed-run>/reviewer_worksheet.signed.json \
  --out .scratch/runtime/<cohort>/<new-private-run>
```

The `--packet` form remains available for an already prepared branch packet and applies
the same field-map and signature-context checks. `SUMMARY.json`, `stage_statuses.json`,
and `admission.json` contain gate results; patient-level rows and records stay in the
private output folder.

For an unsigned structural preview, use the fresh-ingest arguments above with
`--provisional` and without `--worksheet`, or provide a matching unsigned worksheet.
The command writes explicitly provisional tables and an unsigned worksheet. Admission,
split and baseline validators remain blocked until review; the preview does not provide
an admission receipt and cannot be frozen or released. Check `PROVISIONAL.json` for
pending or unrun contract checks before treating the preview as complete.

## How to add a cohort

1. Read the frozen contracts and document primary sources and unresolved questions in a
   patient-free sources note. Do not infer identities, outcomes, timing, or independence.
2. Copy `field_maps/TEMPLATE.json` into a cohort-named field map. Replace all invented
   values, including object hashes and locators, with source-supported rules and validate
   it with `python -m tools.a_dav.field_maps validate <file>`. The template is illustrative,
   not runnable as supplied. The current adapters have source-role and table-layout
   assumptions; new formats may
   require shared adapter work. Declare a prespecified split policy and its lineage before
   reviewer sign-off. The policy and source requirements are part of worksheet context.
3. Write a fetch plan under `fetch_plans/` with exact objects, hashes, versions, approved
   hosts and byte limits. Retrieval requires separate network authorization. Keep the
   content-addressed store and all patient-level output under `.scratch/runtime`.
4. After authorized retrieval or staging, run the local commands below. Prepare and obtain
   a legitimate signed worksheet using the reviewed packet before the final command. The
   documented signed admission command above performs fresh ingestion and the remaining
   stages; use a new output folder for each run.

```sh
PYTHONDONTWRITEBYTECODE=1 ../envs/dav-pipeline/bin/python -m tools.a_dav.ingest --cohort <cohort> --branch <branch> --store .scratch/runtime/<cohort>/store --out .scratch/runtime/<cohort>/<ingest-run>
PYTHONDONTWRITEBYTECODE=1 ../envs/dav-pipeline/bin/python -m tools.a_dav.matrix_v3 --field-map tools/a_dav/field_maps/<cohort>.json --store .scratch/runtime/<cohort>/store --out .scratch/runtime/<cohort>/<v3-run>
PYTHONDONTWRITEBYTECODE=1 ../envs/dav-pipeline/bin/python -m tools.a_dav.review_prepare --packet .scratch/runtime/<cohort>/<configured-branch>/packet.json --out .scratch/runtime/<cohort>/<review-run>
```

Ingestion reports source and join counts and unresolved worksheet items. V3 reports
representation, feature, header and value-check counts and blockers. The signed command
reports each stage status, admission reasons and the checks it actually runs; a changed
worksheet context stops the run and writes a private diff. A structural pass does not
validate biological findings. Review the outputs and resolve blockers with source evidence;
never create or alter a signature on a reviewer's behalf.

GEO-only maps declare `geo_ingest` with the response source, raw-to-canonical
mapping, baseline values, and endpoint class. `baseline_tie_rule` defaults to
`null`; `LEXICOGRAPHIC_ACCESSION` is an outcome-blind option that selects one
baseline candidate while retaining a duplicate worksheet item. A cohort-level
baseline assumption generates a timing worksheet item. An unverified title
mapping generates identity worksheet items and does not create patient joins.
Source-binary definitions are retained with their citations; they are not ORR.
An unavailable author source of record remains blocked even when GEO contains a
corroborating label. `XLSX_NUMERIC` reads a single-sheet numeric table; its
sample binding and representation require source review.

`expression_column_map` declares per-representation bindings by exact GEO title,
accession, named-group regexes, or a pinned delimited crosswalk. Regex group
normalizations are explicit; duplicate candidates and unmatched samples generate
worksheet items. A `review_required` rule produces a review item even when it
matches uniquely. `header_allow_empty` permits a declared non-sample empty column
without changing the default strict header parser. Header-to-sample matches are
proposals; unresolved patient identity is not filled in by an expression match.

Expression representations may declare `orientation` as `samples_as_columns`
(default) or `samples_as_rows`. For row-oriented matrices the sample identifier
is read from the first column, and V3 and expression extraction transpose the
matrix while retaining source identifiers and blocking ambiguous matches.
A field map marked `PARKED` requires `parked_reason`; ingest and admission
refuse it before creating output.

A V3 field map may declare only a primary representation. In that case no
fallback or sensitivity representation is invented: a blocked primary remains
blocked. GEO-only primary V3 inventories restrict SOFT characteristics to patient
and visit keys, bind the sample axis using the declared expression rule, and
block on undocumented measurement fields or feature identity. `XLSX_NUMERIC`
is supported for V3, assay-policy reading and expression extraction. Declared
auxiliary header columns are checked by position and name before exclusion.
