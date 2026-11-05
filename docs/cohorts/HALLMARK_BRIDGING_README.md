# Hallmark full-versus-reduced score bridge

This is an outcome-blind comparison of expression scores. The study universe is
the following 16 signed development cohorts whose platform is
not `targeted_rna` or `nanostring`:

- `riaz_gse91061` — melanoma, `rnaseq`
- `hugo_gse78220` — melanoma, `rnaseq`
- `gse168204` — melanoma, `rnaseq`
- `liu2019` — melanoma, `rnaseq`
- `gide2019` — melanoma, `rnaseq`
- `braun2020` — kidney, `rnaseq`
- `vanallen2015` — melanoma, `rnaseq`
- `gse135222` — lung, `rnaseq`
- `gse176307` — bladder, `rnaseq`
- `kim2018` — gastric, `rnaseq`
- `gse145996` — melanoma, `rnaseq`
- `gse165278` — melanoma, `rnaseq`
- `gse67501` — kidney, `microarray`
- `gse122220` — melanoma, `microarray`
- `gse111636` — bladder, `microarray`
- `gse218989` — lung, `rnaseq`

The following 4 targeted studies define reduced gene subsets only:

- `gse136961` — lung, `targeted_rna`
- `gse93157` — multi, `nanostring`
- `gse140901` — liver, `nanostring`
- `gse159067` — head_and_neck, `targeted_rna`

GSE176307 uses its hash-pinned Salmon TPM matrix on log2(TPM+1), the source
A-META scores. This audit reads every assay column directly; A-META keeps only
the assays linked to patients through an identity packet, which this
outcome-blind audit does not open.

For each Hallmark set, membership symbols are normalized through the frozen
alias table. A non-targeted study qualifies when at least 90% of the set's
members are available after the proposed, locally supported identifier
crosswalk. The full score in a qualifying study uses every set member available
in that study. Reduced scores use (1) the same study's full members minus the
members absent from each other non-targeted study, (2) the intersection of
members present in every qualifying non-targeted study, and (3) each targeted
study's measured members intersected with the full members in the qualifying
study. Empty subsets are omitted.

Both score methods use the same per-study expression values: the unweighted
arithmetic mean, and `singscore::simpleScore` from the repository's
`r/scripts/singscore.R`, with `rankGenes(..., tiesMethod = "min")`, the measured
gene rows as the background, `upSet` as the gene set, and
`knownDirection = TRUE`. No clinical field enters either score.

Each comparison is paired within one study. Spearman correlation uses average
ranks for ties; the SD ratio is sample SD(reduced) / sample SD(full). The
reported median and minimum are across all qualifying-study × reduced-pattern
comparisons for that set. Scores and synthetic sample-row keys are kept only
under ignored `results/`; the tracked tables contain aggregate summaries.

For one set, let `A(s)` be the unique Hallmark members available in study `s`
after frozen aliases and proposed, locally supported identifier mappings.
Qualifying studies are the non-targeted studies with `10 * |A(s)| >= 9 * N`,
where `N` is the unique set membership count. The common membership is the
sorted set intersection of `A(s)` across all qualifying studies; if there are
no qualifying studies, it is empty. The membership hash is SHA-256 of those
sorted symbols encoded as UTF-8, one symbol per line with a final newline (an
empty membership hashes the empty byte string). The common-gene TSV carries
the exact membership as well as its count and hash.
