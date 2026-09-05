# Paper C: pharmacology resource and tool contracts

Evidence checked 5 September 2026. This bounded audit preserves the restored source architecture; it does not rank compounds, finalize the primary endpoint, or substitute GEO perturbations for LINCS. Scope here is LINCS/CMap, CCLE/DepMap, PRISM/GDSC and DrugBank/ChEMBL. Immune-context sources are covered separately. Research was delegated under the AIHero research skill. Current local credentials must never be printed, copied into artifacts, or supplied to a third-party model.

## Findings that change the specification

1. **Do not depend on the hosted CLUE Query API.** Broad's current notice announces retirement of the website/tools effective 31 January 2026 and directs users to GEO for public data. Historical API documentation remains reachable, which does not establish a live service. Public static LINCS2020 annotations and GEO Phase II metadata were successfully downloaded in this audit. A reproducible local scoring route is therefore the design recommendation. [Official retirement notice](https://clue.io/connectopedia/core_cmap_cell_panel), [GEO guide](https://clue.io/geo-guide).
2. **DrugBank bulk academic downloads are currently paused.** The official latest-release page identifies 5.1.22, released 27 June 2026, but marks academic downloads unavailable. Keep DrugBank in the planned architecture with an explicit access state; do not fabricate a ready XML loader or silently claim its data were obtained. ChEMBL is independently accessible. [DrugBank release](https://go.drugbank.com/releases/latest).
3. **Most named immune readouts are inferred in L1000.** In the downloaded LINCS2020 gene annotation, PSMB8 is landmark; CXCL9, CXCL10, HLA-A/B/C, B2M, TAP1/2 and PSMB9 are best-inferred. A landmark-only sensitivity is useful but cannot be presented as a fully measured test of that entire immune panel. [Original gene annotation](https://s3.amazonaws.com/macchiato.clue.io/builds/LINCS2020/geneinfo_beta.txt).
4. **Tazemetostat has a non-obvious LINCS name.** LINCS2020 lists `E-7438`, `BRD-K11215326`, alias tazemetostat. Its complete InChIKey matches ChEMBL's tazemetostat record. Simple matching of `tazemetostat` against `cmap_name` would miss it. Compound annotation presence does not prove measured signatures in a given line. [Original compound annotation](https://s3.amazonaws.com/macchiato.clue.io/builds/LINCS2020/compoundinfo_beta.txt), [ChEMBL molecule query](https://www.ebi.ac.uk/chembl/api/data/molecule.json?pref_name__in=DECITABINE,ENTINOSTAT,TAZEMETOSTAT&limit=20).

## LINCS/CMap contract

### Release and access

GSE92742 is the Phase I route and GSE70138 the Phase II route. GSE106127 republishes the RNAi/CRISPR portion of those resources, so it is not an independent validation dataset. GEO Phase II's directory was actually retrieved; its 2017-03-06 Level 5 filename is `GSE70138_Broad_LINCS_Level5_COMPZ_n118050x12328_2017-03-06.gctx.gz`, listed at about 5 GB. The matrix was not downloaded. Older 2015 files in that same directory use different dimensions: never mix annotations by accession alone. [Broad GEO guide](https://clue.io/geo-guide), [inspected directory](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE70nnn/GSE70138/suppl/).

The separately inspected December 2020 beta README describes an expansion of the 2017 release, GCTX files split by data level and perturbation type, and the BigQuery dataset `cmap-big-table.cmap_lincs_public_views`. It warns files may change. BigQuery access/billing, schemas and subset extraction were not tested; it is a documented alternate route, not a verified working adapter. Record exact URLs, hashes, date, original filename and matrix dimensions rather than `latest`. The 2017/2020 datasets are overlapping releases, not independent replications. [Original README](https://s3.amazonaws.com/macchiato.clue.io/builds/LINCS2020/README.txt).

Public/NIH-funded L1000 redistribution is allowed by the resource's specific policy, which requests attribution and disclosure of reprocessing. The historical hosted-platform terms differ. Do not infer permission to redistribute every CLUE-hosted product from the public GEO policy. Current work should push code, manifests and modest derived coverage summaries; retain bulk source caches outside release artifacts until their exact provenance is recorded. [Redistribution policy](https://clue.io/connectopedia/data_redistribution).

### What was actually counted

Downloaded Phase II signature annotation contains **118,050 signature records**. Filtering `pert_type == trt_cp` gives **12,031 PC3** and **707 LNCAP** signatures. No VCAP, DU145 or22RV1 chemical signatures occur in this particular annotation. This is a release-specific observation, not evidence those lines never occur in LINCS. The 2020 cell dictionary includes prostate-labelled22RV1, DU145, PC3, RWPE1, VCAP and LNCAP, but dictionary membership is not assay coverage. RWPE1's tumour label in that dictionary needs biological curation before inclusion as a cancer model. [Phase II signature metadata](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE70nnn/GSE70138/suppl/GSE70138_Broad_LINCS_sig_info_2017-03-06.txt.gz), [2020 cell dictionary](https://s3.amazonaws.com/macchiato.clue.io/builds/LINCS2020/cellinfo_beta.txt).

| Compound | Identity verified in 2020 annotation | Phase II signatures across all lines | Phase II prostate coverage before QC |
|---|---|---:|---|
| Decitabine | BRD-K79254416; CHEMBL1201129 |171|15PC3 signatures:24h at0.04,0.12,0.37,1.11,3.33,10µM, two signatures each;6h at10µM, three signatures|
| Entinostat | BRD-K77908580; CHEMBL27759 |171|15PC3 signatures: same six24h doses, two signatures each;6h at2µM, three signatures|
| Tazemetostat | BRD-K11215326, E-7438; CHEMBL3414621 |0|No matching BRD-ID signatures in this Phase II file;2020 signature coverage remains unknown|

These are metadata observations, not passed-QC biological comparisons. Each decitabine/entinostat signature lists between one and three underlying `distil_id` values. Shared instances, plate structure and QC metrics must be audited before independence is assigned. Do not treat15collapsed signatures as15biological replicates. Recount and identity evidence: `C_pharmacology_contracts/verified_coverage_summary.json`; original files have hashes in the accompanying access manifests.

### Scoring and unit contract

- **WTCS** is a signed, bidirectional weighted-KS enrichment statistic, range[-1,1]. Opposing up/down enrichment signs contribute; same-sign enrichment yields zero under the documented rule. Negative scores mean reversal of the submitted disease query.
- **NCS** normalizes WTCS separately by signed means within cell-line/perturbagen-type reference strata. A local z-score is not automatically NCS.
- **Tau** compares NCS with a fixed reference-query distribution and retains the sign, range[-100,100]. An arbitrary permutation percentile is not interchangeable with official tau. Record the actual reference collection and implementation if reproducing it. A negative tau is not itself a p-value.

These distinctions follow [Broad's analytical-methods documentation](https://clue.io/connectopedia/category/Analytical%20Methods). **Design recommendation:** local WTCS as the reproducible core unless exact NCS/tau reference assets can be acquired and validated; prespecified empirical nulls are separately named statistics. Maintain the reversal oracle, tie handling, query overlap checks and gene-space coverage report. Do not assign zero to unassayed compounds.

Level4 is profile-level differential z-score data; Level5 is replicate-collapsed signature data. The documented MODZ procedure weights replicate vectors using their correlations. The scoring unit is therefore a signature carrying compound, cell, dose, duration and provenance, not an individual gene or an already pooled class. [Data levels and methods](https://clue.io/connectopedia/category/Analytical%20Methods), [replicate collapse](https://clue.io/connectopedia/pdf/replicate_collapse).

Minimum ingest fields: release, `sig_id`, `pert_id`, `pert_type`, cell identifier, original dose string and normalized numeric dose/unit, original duration and normalized hours, underlying instance IDs, QC flags/metrics, source file/hash and gene-space annotation. Phase II explicitly supplies `pert_idose` strings such as `10.0 um`, `pert_itime` such as `24 h`, and `distil_id` lists. Do not parse missing sentinel `-666` as a valid dose or duration.2020 uses a changed schema; a separate versioned adapter is required.

The assay's documented gene universe is12,328 genes:978measured,11,350inferred. The BING space combines landmarks and9,196well-inferred genes. Freeze the exact file rather than assume all inferred genes qualify. Report query coverage separately for measured, best-inferred, other inferred and absent genes. [Gene-space documentation](https://clue.io/connectopedia/pdf/l1000_gene_space). Drug-class mixed models remain conditional on enough independent compounds and overlapping conditions; neither metadata breadth nor random effects can repair perfect class–drug–dose confounding. This last statement is a statistical design constraint, not a measured result.

## CCLE/DepMap contract

DepMap's official26Q1 release announcement confirms updated CRISPR/omics data and changes to Chronos library correction. The live portal encountered a human-verification page during this audit; its indexed download descriptions identify `Model.csv`, `OmicsProfiles.csv`, and `CRISPRGeneEffect.csv`. Do not claim a26Q2 release was inspected or that a26Q1 Model.csv was successfully downloaded. [26Q1 announcement](https://forum.depmap.org/t/announcing-the-26q1-release/4606), [download catalogue](https://depmap.org/portal/data_page/?tab=currentRelease).

Required contracts are model identity, baseline expression, gene effect and available methylation. `ModelID` (`ACH-*`) is the model join key; profile-level files require `OmicsProfiles.csv` mapping and a prespecified representative-profile rule. Model, profile, model-condition and screen identifiers are different units. Freeze gene-ID interpretation and expression transformation from the selected file's description. Avoid joining by stripped names alone. Latest matched prostate counts and current file URLs/hashes remain unresolved.

CCLE is a resource family, not a guarantee of the same cell panel across assays. The official methylation repository provides pipeline code, but does not by itself establish the available prostate measurements or promoter coverage. Exact methylation release, assay, genome build, feature definitions, missingness and matched expression coverage are open acquisition questions. [CCLE methylation pipeline](https://github.com/broadinstitute/CCLE_methylation).

DepMap staff explain that DepMap-generated data generally use CC-BY4.0, while externally hosted projects may differ. Record the selected file's actual license. CCLE and DepMap downloads can represent the same baseline measurements and must not be counted as independent evidence. Dependency can support target-context annotation; it does not map an epigenetic regulator to a specific immune gene or establish pharmacological restoration. [Official licensing answer](https://forum.depmap.org/t/license-for-data-found-in-the-depmap-portal/130).

## PRISM/GDSC contract

The **PRISM 19Q4 Figshare record, version 4**, was retrieved through its official API. It is CC-BY4.0 and exposes named treatment/cell annotation, replicate-level and collapsed matrices, README files and secondary curve fits. Primary and secondary screens are different designs, not duplicate interchangeable scores. The release recommends MTS010 technical redos where available; screen provenance must survive integration. [Official release](https://figshare.com/articles/dataset/9393293), [verified API manifest](https://api.figshare.com/v2/articles/9393293).

Both downloaded cell dictionaries have588rows and four prostate entries: PC3`ACH-000090`, DU145`ACH-000979`, LNCAPCLONEFGC`ACH-000977`,22RV1`ACH-000956`. These are lookup counts, not proof that every drug has a valid result in all four lines. The primary collapsed-treatment dictionary has4,686records, including the three planned compounds: tazemetostat2.31µM, entinostat2.5µM and decitabine2.5µM. Full BRD IDs include batch/salt suffixes and must be retained before mapping to a parent compound. [Cell metadata](https://ndownloader.figshare.com/files/20237718), [treatment metadata](https://ndownloader.figshare.com/files/20237715).

PRISM's primary readme defines dose inµM, log2fold change against same-line/plate negative controls, and median collapse by drug–dose–cell condition. These are viability measurements. The secondary readme separately defines curve fitting, AUC, EC50/IC50 and fit diagnostics. Preserve source-scale values; a portal's log2AUC transformation is not the same field as raw AUC. Expression re-expression and viability remain separate evidence dimensions. [Primary README](https://ndownloader.figshare.com/files/20237700), [secondary README](https://ndownloader.figshare.com/files/20238123).

**GDSC:** the official fitted-data dictionary was inspected; the release directory request returned403, so current data-file hashes and prostate/compound overlap were not established. The dictionary specifies drug/COSMIC cell IDs, screening concentration bounds inµM, natural-logIC50 and AUC normalized to the screened concentration interval. Its documented transformation is `IC50_uM=exp(LN_IC50)`. Preserve dataset/version and the screening range. Do not compare IC50 values without checking extrapolation beyond tested concentrations, or pool GDSC1/2 and PRISM as identically scaled experiments. [Official fitted-data dictionary](https://cog.sanger.ac.uk/cancerrxgene/GDSC_release8.5/GDSC_Fitted_Data_Description.pdf), [official downloads](https://www.cancerrxgene.org/downloads/drug_data).

GDSC legal-page retrieval also failed; exact selected-release use/redistribution terms remain a gating metadata field. Do not substitute a third-party license assertion. Broad DepMap hosting of GDSC values would not make a second independent validation. All viable overlaps require actual nonmissing matrix entries, not a Cartesian product of drug/cell dictionaries.

## DrugBank/ChEMBL contract

DrugBank's inspected page offers academic eligibility conditions and lists CC-BY-NC4.0 for its datasets, but currently pauses all academic downloads. Record `access_status=provider_paused` and maintain an optional local-authorized-file adapter. No DrugBank API or credential was used. This access problem should not halt the entire paper: ChEMBL can provide an explicitly named parallel source, while unavailable DrugBank annotations remain missing. Exposure/clinical feasibility still requires original pharmacokinetic studies or regulatory labeling, with drug form, units, time course and binding assumptions made explicit. [DrugBank](https://go.drugbank.com/releases/latest).

The unauthenticated **ChEMBL status API returned ChEMBL_37, release date2026-05-01, statusUP**. A bounded exact preferred-name query returned three parent molecules, with structures, complete InChIKeys and parent/active hierarchy: CHEMBL1201129decitabine; CHEMBL27759entinostat; CHEMBL3414621tazemetostat. These are successful interface/identity checks, not a complete target or bioactivity extraction. [Status API](https://www.ebi.ac.uk/chembl/api/data/status.json), [verified molecule query](https://www.ebi.ac.uk/chembl/api/data/molecule.json?pref_name__in=DECITABINE,ENTINOSTAT,TAZEMETOSTAT&limit=20).

The official API documentation supports programmatic data access. Next contract checks must inspect molecule, mechanism, activity, assay, target and document records, including `standard_type`, `standard_relation`, value/units, organism, target confidence, assay type, and original document identifiers. Do not merge IC50, EC50, Ki and Kd as identical endpoints; do not infer on-target activity merely from a drug-name match. Preserve one-to-many mechanisms and parent/salt distinctions. [Official API documentation](https://chembl.gitbook.io/chembl-interface-documentation/web-services).

The database license is **CC-BY-SA3.0**, distinct from the CC-BY4.0 license on some EBI training pages and software licenses. Track annotations as sourced data with their license rather than applying the repository's code license to them. [Official ChEMBL licensing FAQ](https://chembl.gitbook.io/chembl-interface-documentation/frequently-asked-questions/general-questions).

## Evidence-based grilling ledger

| Question | Answer / status | Fact versus design | Evidence | Specification impact |
|---|---|---|---|---|
| Can we promise a live CLUE tau query? |No; retirement notice supersedes assumptions from old tutorial.|Verified operational notice; API execution not tested.|Broad retirement notice above.|Implement local screening; hosted service cannot be required.|
| Can local weighted-KS output be called tau? |Only with the documented normalization/reference procedure.|Documented method.|Broad analytical methods.|Separate statistic names, provenance and numerical tests.|
| Are our ten immune sentinel genes measured? |One landmark, nine best-inferred in2020 annotation.|Verified file recount.|Gene annotation/hash.|Report evidence tier; use measured corroboration.|
| Is tazemetostat missing from LINCS? |Present in2020compound dictionary asE-7438; absent from testedPhase II signature table;2020 signature count unknown.|Verified scoped observations.|InChIKey join plusPhase IIrecount.|Missingness must be release/context specific.|
| Are PC3 and VCAP both available for every planned drug? |No such coverage established. Phase IIprovidesPC3for two drugs;VCAPnot present in its chemical signatures.|Verified scoped recount.|Phase IIsig_info.|Coverage gate before prostate/class comparisons.|
| Are repeated signatures independent replicates? |Not established; inspect underlying instance/plate overlap.|Open metadata question/design constraint.|distil_id andMODZdocs.|Prohibit signature-count pseudoreplication.|
| Are CCLE methylation anddependency available on the same prostate panel? |Unknown until selected-release files are joined.|Open acquisition fact.|DepMapcatalogue/pipeline.|No invented complete multi-omics panel.|
| Does PRISMoffer the three drugs and prostate identities? |Yes in separate dictionaries; nonmissing drug–line measurements not yet checked.|Verified dictionaries, incomplete matrix coverage.|PRISMmetadata.|Distinguish annotated, assayed, QC-passed, usable.|
| Is PRISM or GDSC direct immune restoration evidence? |No; these measurements concern growth/viability.|Documented assay plus interpretation.|Readmes/data dictionary.|Separate sensitivity from reversal.|
| Can DrugBank be downloaded now? |Official academic downloads paused.|Verified current provider status.|DrugBankrelease.|Optional authenticated/local adapter; clear missingness.|
| Can ChEMBLprovide reproducible identities now? |Yes,37 status and three exact molecules retrieved.|Verified live API.|Cached response/hash.|Pin release; resolve identity before annotations.|
| Can we claim clinically feasible exposure from database annotations? |No; clinical PK source and appropriate exposure definition still needed.|Design/interpretive constraint.|Outside this bounded audit.|Require evidence extraction, no fabricatedfree Cmax.|
| Do more databases guarantee independence? |No; shared releases, measurements and literature can overlap.|Verified examples plus design.|LINCSreleases,DepMap/CCLE,PRISMhosting.|Build an evidence-provenance graph.|

## Reproduction and open gates

Actually executed public probes are documented in `C_pharmacology_contracts/probe.py`, `access_manifest.json`, `geo_phase2_access.json` and `prism_access.json`. Recount command executed successfully:

```powershell
python 'E:\Master_Thesis\master-thesis\docs\research\C_pharmacology_contracts\recount.py'
```

`probe.py` reproduces the initial public metadata requests with20 MB individual / 50 MB per-run caps. Phase IIandPRISMfollow-up URLs/hashes are in their manifests. Total successfully downloaded source payloads in this audit were approximately 9.16 MB; no expression or viability matrix was acquired. Public credential-free URLs only were requested. Initial sandbox network calls failed; the same bounded requests succeeded with approved network access except GDSC 403. No bypass of a portal verification page was attempted.

Before an executable scientific spec is called ready: acquire/pin eligible LINCS matrix+signature QC; resolve 2020 condition counts/overlap; approve exact score/null/reference implementation; audit query coverage; retrieve selected DepMap model/expression/effect/methylation metadata and actual matched coverage; acquire PRISM/GDSC valid entries with precise transformations and licenses; exerciseChEMBL target/activity provenance joins; document DrugBank access state; establish clinical PKevidence; obtain independence and uncertainty rules. These are concrete open gates, not reasons to discard the restored sources or pretend that missing measurements are biological negatives.
