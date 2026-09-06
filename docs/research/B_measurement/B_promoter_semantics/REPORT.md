# B promoter measurement contract — proposed options, 6 September 2026

**Literal candidate probe sets are now reproducible without choosing B-P or B-R. They are not an accepted annotation freeze or a usable TCGA/CPC predictor set.** The existing cognate-transcript pairing is correct, but the description “matching protein-coding transcript” overstates what the cached `transcriptTypes` field establishes. Shared promoter assignments are substantial and must survive into interpretation and schemas.

This audit read only annotation/mask tables and small original-source metadata. It did not read patient methylation/expression values, calculate outcomes, select by associations, or edit the canonical repository.

## 1. What the source mapping actually means

The maintainer defines gene associations across each transcript's upstream 1.5kb region through transcript termination; promoter association uses the ±1.5kb TSS window. All isoforms participate. `genesUniq` summarizes genes; the four aligned lists are `geneNames`, `transcriptTypes`, `transcriptIDs`, `distToTSS`. The annotation is not a nearest-gene or canonical-transcript assignment. [Official field glossary](https://zwdzwd.github.io/InfiniumAnnotation/gene_annotation.html).

Across the complete cached485,577-row v36 manifest, the four-list lengths agree and `genesUniq` equals the set of `geneNames` in every row. The existing `B_annotation/count_features.py` correctly first matches the **cognate gene** and then filters its corresponding transcript distance. Applying a row's minimum distance to every associated gene would wrongly add10 unmasked TAP1 probes and29 PSMB9 probes under the existing literal-label ±1500 rule. These incorrect extra IDs are enumerated in `summary.json`; they are rejection examples, not candidate additions.

Concrete example: **cg16890093** is gene-associated with TAP1, PSMB8, PSMB9 and an antisense transcript. Its matching TAP1 distances are4836–8672bp; none passes ±1500. Matching PSMB8/PSMB9 distances do pass. A gene-summary join would falsely call this a TAP1 promoter measurement. `probe_gene_candidates.tsv` and `cognate_transcript_evidence.tsv` preserve the actual assignments from the [pinned v36 table](https://raw.githubusercontent.com/zhou-lab/InfiniumAnnotationData/6d176d6e7e56465403d4478a09fe11b983eeb721/Anno/HM450/HM450.hg38.manifest.gencode.v36.tsv.gz).

## 2. Independent coordinate and coding-sequence check

Five small [UCSC GENCODE-v36 track](https://genome.ucsc.edu/cgi-bin/hgTrackUi?db=hg38&g=wgEncodeGencodeV36) slices cover the target loci. All64 versioned target transcripts match their gene symbols. All3,127 target probe–transcript distances agree exactly with:

```text
plus strand:  d = CpG_beg - txStart
minus strand: d = txEnd - CpG_beg
```

Thus source-positive distance is downstream in transcriptional orientation for these records. The source minus-strand anchor is the **exclusive txEnd boundary**: replacing it with txEnd−1 changes distances by one base. Preserve this convention for a literal source-based policy; do not silently reinterpret a source distance as a manufacturer category. `probe_strand` is not transcript strand. All raw API URLs, versioned transcripts, strand, coordinates, CDS boundaries and zero-mismatch checks are in `CDS_crosscheck_summary.json` and `transcript_coordinate_CDS_evidence.tsv`. [UCSC genePred field definitions](https://genome.ucsc.edu/FAQ/FAQformat.html#format9).

**Biotype caveat:** all64 target manifest records have `transcriptTypes=protein_coding`, but only31 have `cdsStart<cdsEnd` in the matching v36 transcript track;33 have zero CDS span. For example, B2M ENST00000559220.1 is labelled `protein_coding` in the manifest but has no positive CDS interval. This may reflect gene-level classification inherited across transcript rows; it does not by itself demonstrate an annotation error. The manifest-generation provenance needed to prove that explanation was not located. Consequently, call the existing option **source-label-based**, not verified coding-isoform-only. Positive CDS span is a concrete alternative rule, not an exact biotype, productive-transcript, MANE or canonical designation.

## 3. Candidate options and shared measurements

Every column below uses cg probes and the exact historical202209 `MASK_general=FALSE` call. Each option is **unselected**. Boundaries are inclusive, a proposed explicit implementation convention.

| Gene | Source-label ±1500 | Source-label ±200 | ±1500 with unique source-labelled promoter gene¹ | GENCODE-v36 positive-CDS-span ±1500 |
|---|---:|---:|---:|---:|
| HLA-A | 3 | 1 | 3 | 3 |
| HLA-B | 8 | 7 | 8 | 8 |
| HLA-C | 12 | 1 | 12 | 10 |
| B2M | 14 | 9 | 1 | 14 |
| TAP1 | 83 | 34 | 29 | 61 |
| TAP2 | 75 | 21 | 30 | 45 |
| PSMB8 | 82 | 34 | 21 | 61 |
| PSMB9 | 126 | 32 | 11 | 116 |

¹Uniqueness is tested among **all cognate promoter genes in the source row**, including genes outside the eight-gene family, using the same literal source label/window. This is not genomic mapping uniqueness or a demonstration of gene-specific regulation. Unrestricted transcript-biotype ±1500 produces the same target counts as the source-label option here, not a generally equivalent genome-wide policy.

The literal-label candidate comprises403 gene memberships from288 unique probes. The CDS-bearing alternative comprises318 memberships from203 unique probes. Both contain54 shared TAP1/PSMB9 probes and61 shared PSMB8/PSMB9 probes. Under the CDS option, all61 PSMB8 candidates also belong to PSMB9; the two summaries cannot supply independent locus-specific evidence. No unmasked HLA-A/B/C probe is shared across those three target-gene sets, but this does not prove HLA assay specificity or eliminate polymorphism concerns.

Outside-family overlaps explain why “unique promoter gene” is a substantive choice:13 of14 B2M candidates also map to PATL2 and45 of75 TAP2 candidates map to AL669918.1 under source-label semantics. Excluding shared probes drastically changes the measurement. Retaining shared probes is allowed as a declared descriptive measurement; never count duplicate gene memberships as independent CpGs, double-count a probe within one gene, or infer separate causal regulation from their reuse. All counts above are annotation-derived; neither biological activity nor cohort usability is measured.

The unchanged3/8/12/14/83/75/82/126 counts independently reproduce the earlier inspection. **The required correction is interpretation of the source label, not those literal counts.** Source versus CDS differences are fully enumerated; no policy was selected to achieve a preferred count.

## 4. Concrete contract available for review

Proposed common schema: `policy_id`, source manifest/mask/version/hash, `probe_id`, genome/coordinate convention, target gene symbol plus **pending validated stable-gene-ID bridge**, versioned cognate transcript ID, `transcriptTypes_source`, transcript-strand/coordinate source, literal distance, inclusion predicate, mask status/reason, all matched promoter genes and shared-probe group. Persist the long annotation before collapsing to unique probe–gene pairs. Transcript multiplicity must not create extra weight in a gene mean.

A review can now choose explicitly among the exported source-label and CDS-bearing candidates, or request a separately documented canonical/MANE or manufacturer definition. The latter choices are not supplied by this manifest and remain uncomputed. Window, transcript/coding criterion, shared-probe handling, historical mask and coordinate boundaries are separate decisions. There is no automatic substitution of ±1500 for manufacturer TSS200/TSS1500, no latest-release substitution, and no implicit acceptance of this legacy combination as the GDC's internal mask.

The mask comes from the [pinned202209 file](https://raw.githubusercontent.com/zhou-lab/InfiniumAnnotationData/6d176d6e7e56465403d4478a09fe11b983eeb721/Anno/HM450/archive/202209/HM450.hg38.mask.tsv.gz). Zhou's primary study supports explicit mapping/polymorphism quality considerations, not a guarantee of unique regulation for an unmasked probe. [Zhou et al., DOI10.1093/nar/gkw967](https://pmc.ncbi.nlm.nih.gov/articles/PMC5389466/). GDC's current SeSAMe output is probe-ID/beta data; its separate historical liftover description uses GENCODEv22 and is not evidence that these v36/202209 files recreate current processing. [GDC documentation, current workflow versus liftover sections](https://docs.gdc.cancer.gov/Data/Bioinformatics_Pipelines/Methylation_Pipeline/).

Required downstream gates remain: source-supported stable gene/transcript mapping to RNA, CPC probe/detection coverage, source-equivalent specimen identity, assay QC, user-reviewed promoter/mask policy and actual measurement precision. The selected annotation set would be Q's **candidate universe**, not final Q. B-P still needs fold-specific TCGA-only availability filtering; a proposed B-R freeze still needs its independently specified QC/complete-case rules. Neither can use external effects to select annotation options.

## 5. Proposed specific canonical edits

1. Amend the annotation audit and B alternative prose from “any matching protein-coding transcript” to “any matching transcript carrying the manifest's literal protein_coding label,” with the direct CDS cross-check and unselected alternative.
2. Extend `SOFTWARE_CONTRACT.md` beyond aligned gene/group pairs to include versioned transcript, raw source label/distance, strand/coordinate convention, mask and shared-probe membership. Do not derive ENSG identity from an unvalidated symbol alias.
3. In ANALYSIS/B-R, name the eventual policy hash before Q generation. One probe contributes once per gene; shared probes remain marked across genes. The gene mean is a chosen summary of one or several annotated promoter regions, not proven cognate-transcript repression.
4. Add future acceptance cases: cg16890093 fails TAP1 and passes its actual qualifying genes; equal list lengths and cognate matching; no transcript-count weighting; reverse-strand boundary; literal label versus CDS choice; overlapping PSMB8/PSMB9 measurements. These audit facts are fixtures, not production tests already implemented.
5. Preserve both B-P and B-R. The annotation decision is shared measurement design; this audit supplies neither primary approval nor an analysis-ready external cohort.

## 6. Reproduction and provenance

Run the two offline scripts sequentially with Python3.11+ standard library:

```powershell
python -B E:/Master_Thesis/planning/next_evidence/B_promoter_semantics/audit_promoters.py
python -B E:/Master_Thesis/planning/next_evidence/B_promoter_semantics/crosscheck_transcripts.py
```

The first verifies the two cached input SHA256 values before reading them and emits literal IDs. The second reads the generated annotations and five cached UCSC slices. Both succeeded locally; this is metadata verification, not an AIU production-analysis acceptance run. Candidate exports and scripts remain outside the canonical repository.

New saved public bodies total35,568 bytes:2,130-byte maintainer glossary plus33,438 bytes across five target-locus responses. Python's UCSC TLS store failed; a normal Windows-validated `Invoke-WebRequest` succeeded without disabling certificate verification. No full GTF or new matrix was retrieved. `PROVENANCE.json` records exact source URLs, versions, bytes, file hashes and limitations; full downloaded annotation/mask tables remain in the existing outer cache. No redistribution license or release approval is inferred from accessibility.
