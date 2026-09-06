# Independent promoter-semantics review

6 September 2026. Read `B_promoter_semantics/REPORT.md`, both audit scripts, the policy JSON, summary outputs, cached maintainer glossary, five small UCSC slices, and the original cached manifest/mask. Recounted independently without executing source-producing scripts or changing their outputs. No downloads or patient molecular values were used.

## Result

No material counting or coordinate error found. The candidates remain unselected annotation options, not an accepted promoter contract or cohort-usable measurement set. The report appropriately corrects the claim that the manifest's literal `protein_coding` label proves a coding isoform.

## Independent verification

- Original manifest: 485,577 rows; zero discrepancies among the four aligned gene/type/transcript/distance list lengths; zero disagreements between `genesUniq` and the set of `geneNames`.
- All 3,127 target probe–transcript rows reproduce the cached UCSC coordinate calculation and match gene/chromosome identities. There are 64 versioned target transcripts, of which 31 have positive CDS span and 33 have zero CDS span.
- Every exported `(policy_id, gene_symbol, probe_id)` tuple, across both candidate TSV files, exactly matches the independently reconstructed source/mask/coordinate predicates. No duplicate exported tuples occur.
- Source-label ±1500: 403 gene memberships / 288 distinct probes. Positive-CDS ±1500: 318 memberships / 203 probes. Shared counts are 54 TAP1–PSMB9 and 61 PSMB8–PSMB9 under both options.

| Gene | Source ±1500 | Source ±200 | Unique source-labelled promoter gene | Positive CDS ±1500 |
|---|---:|---:|---:|---:|
| HLA-A | 3 | 1 | 3 | 3 |
| HLA-B | 8 | 7 | 8 | 8 |
| HLA-C | 12 | 1 | 12 | 10 |
| B2M | 14 | 9 | 1 | 14 |
| TAP1 | 83 | 34 | 29 | 61 |
| TAP2 | 75 | 21 | 30 | 45 |
| PSMB8 | 82 | 34 | 21 | 61 |
| PSMB9 | 126 | 32 | 11 | 116 |

The independent naive-row-join comparison also reproduces 10 false extra TAP1 and 29 false extra PSMB9 assignments. `cg16890093` fails TAP1's cognate window and passes the qualifying PSMB8/PSMB9 windows; a minimum distance borrowed from a different gene must not admit TAP1.

## Coordinate and coding semantics

The cached [maintainer glossary](https://zwdzwd.github.io/InfiniumAnnotation/gene_annotation.html) distinguishes target position from probe strand and considers all isoforms. Its CpG begin is zero-based, with an end coordinate numerically compatible with a half-open interval; describing the end as one-based inclusive in the glossary does not warrant subtracting one from the stored coordinate when using the corresponding zero-based half-open representation.

For the independently checked target records, plus-strand source distance is `CpG_beg - txStart`; minus-strand distance is `txEnd - CpG_beg`. The exclusive minus-strand boundary reproduces the existing source field. Substituting the last transcribed base would create a one-base difference. This verifies the source convention; it does not select inclusive window boundaries or equate ±1500 with a manufacturer TSS category.

The actual B2M transcript example `ENST00000559220.1` has the literal manifest label but equal CDS start/end in the version-matched track. Positive CDS span remains a different explicit rule, not a proven productive, canonical or MANE isoform. A hypothesis that the source label was inherited from gene classification is appropriately left unproved.

## Shared measurements: wording to preserve

The report does not claim independent loci from gene labels. Under the CDS option PSMB8's 61 probes are a **subset** of PSMB9's 116; the aggregates are not necessarily identical. Shared probes cannot be counted twice as independent CpG observations or used to infer independent regulatory evidence. Conversely overlap alone does not establish identical aggregates, perfect model collinearity, or dependence of every resulting gene-level statistic. Those are separate measurement/statistical questions. Multiple gene hypotheses can still exist with appropriate multiplicity control; the source audit does not demonstrate separate causal mechanisms.

The long-table `pc_abs1500_candidate` flag describes the transcript/window predicate before general-mask exclusion. Downstream readers must combine it with the explicit mask column; the final exported candidate sets correctly do so. The unique-promoter-gene option checks all source-labelled promoter genes, not just the eight targets, and is not a genomic uniqueness certificate.

## Provenance and limits

Both complete cached input hashes match the audit pins: manifest `cb908b2aa8f49b2c92e3698dc04c379607850c36c329f2ff24dc765af655e483`; mask `5a02fa845578a0947ef1a80262d8514092f9c7690e37da0bc31b00f8f908e69d`. Original URLs, coordinate-source slices and release pins are in `B_promoter_semantics/PROVENANCE.json`; nothing was fetched anew.

No stable-gene-ID bridge, assay detection coverage, same-specimen pairing, patient-specific promoter aggregate, measurement precision, or scientific primary choice was established. B-P/B-R and all promoter/mask options remain proposed. No canonical files or other agents' audit outputs were edited.
