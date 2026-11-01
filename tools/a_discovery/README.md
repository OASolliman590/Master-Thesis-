# Paper A metadata discovery

Run from the repository root. Discovery outputs must be under `.scratch/runtime` because they can contain sample or run accessions. All results are unreviewed proposals; they do not admit a cohort.

```sh
python -m tools.a_discovery search --queries queries.json --out .scratch/runtime/discovery/run1
python -m tools.a_discovery resolve --id GSE000000 --out .scratch/runtime/discovery/run2
python -m tools.a_discovery fastq --project PRJEB00000 --strategy RNA-Seq --out .scratch/runtime/discovery/run3
python -m tools.a_discovery draft-fetch-plan --packet .scratch/runtime/discovery/run2/packets/GSE000000.json --cohort example --out tools/a_dav/fetch_plans/example.json.draft
```

Queries are a JSON array of objects with `id`, `adapter`, and `query` fields. Adapter names are `ncbi`, `geo`, `ena`, `cbioportal`, `biostudies`, `ega`, `dbgap`, and `europepmc`. Set `NCBI_EMAIL` and optionally `NCBI_API_KEY` in the environment. The tool never fetches data objects. Review all evidence and the draft plan before use; its presence does not satisfy the field-map, V3, or signed-worksheet gates.

The packet's `object_inventory` records source-reported file sizes and hashes. FASTQ records include `published_md5` for nf-core; FASTQ objects are excluded from retrieval plans. The tool does not download expression or supplementary files. GEO characteristic values that look identifying or are unique free text are suppressed; aggregate categorical response values are retained. Readiness remains `UNKNOWN` until the available evidence explicitly supports R1, R2, R3, or X. Regimen and overlap tags are leads for review, not clinical conclusions.

FASTQ output defaults to `RNA-Seq`; `--strategy` selects another library strategy. The size report includes per-strategy run counts and totals. Recognized, small cBioPortal LFS pointers are read at a pinned commit, with their published SHA-256 and size in the inventory. Challenge pages terminate the affected adapter and are marked in the packet and receipt.

Limitations: Europe PMC supplementary file lists are not implemented. EGA keyword endpoint behavior and the GEO listing format have only hand-written offline fixtures; they have not been verified live. GEO directory listings may provide rounded display sizes; these are preserved as displayed and are not promoted to exact bytes or included in drafts. E-utilities links preserve numeric identifiers and extract accessions found in summaries, but do not resolve every linked record's complete provenance. No real-study or biological validation is implied.
