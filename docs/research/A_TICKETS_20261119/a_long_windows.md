# A-LONG on-treatment windows: primary-source review (19 Nov 2026)

**Status: RESEARCH NOTE. Every window below is PROPOSED.** Nothing here signs a window, admits a pair, fills `specs/A1/contrast_registry.tsv`, or closes gate 3 of `specs/A1/SPEC_v2.md` §9.

**Scope.** This note answers the timing requirement in SPEC_v2 §3. That section asks for an index event, lower and upper day bounds (or a verified source category), a tie rule, and a lesion and platform policy for each study. It also checks the Riaz and Gide statements in `docs/decisions/PROPOSED_A_LONG_N12_N13_20261107.md`.

**Sources read.** Only publications (Methods, STAR Methods, the main text, tables, and figure legends in the article PDF or PMC text) and series- or project-level descriptions (GEO series header fields, the ENA project record). No expression matrix, sample table, per-sample characteristics field, clinical table, or response table was opened. This note records no sample, run, or patient identifiers.

**Language.** "Schedule" means a protocol-stated interval. It is not an observed specimen day. "Category" means a source label (PRE/ON, PRE/EDT, before/after) with no day attached.

## Summary table

| Study | Treatment / index event | Baseline timing (source) | On-treatment timing (source) | Exact day or category? | Same lesion? | Proposed window (PROPOSED) |
|---|---|---|---|---|---|---|
| **Riaz 2017, GSE91061** | Nivolumab 3 mg/kg every 2 weeks (CA209-038). Index: first nivolumab dose. Ipi-naive and ipi-progressed strata. | 1–7 days before the first dose (protocol). | "Cycle 1, day 29 (between days 23–29)" (protocol). Elsewhere described as "4 weeks". | Schedule plus category only. The paper and series description give no per-specimen days. GEO says "On-treatment" / "Pre-treatment". | **Yes, by design:** the repeat biopsy was "collected from the same site". | Index = cycle 1 day 1 (first nivolumab dose). PRE = protocol baseline [−7, −1]. ON = protocol C1D29 biopsy, C1 days 23–29. Use the verified category; exact day UNKNOWN. Strata ipi-N and ipi-P are kept separate. |
| **Gide 2019, PRJEB23709** | Anti-PD-1 monotherapy (nivolumab 3 mg/kg 2-weekly or pembrolizumab 2 mg/kg 3-weekly) **or** ipilimumab + anti-PD-1. Index: "commencement of immunotherapy". | PRE: "prior to immunotherapy". No lower bound is given. Tissue was retrospectively identified from FFPE availability. | EDT: "taken 7-14 days following the commencement of immunotherapy". | Category plus stated range. No per-specimen days in the paper or the ENA project record. | **UNKNOWN.** The source does not say. | Index = first ICI dose (assumed meaning of "commencement"). PRE = before index, lower bound UNKNOWN. EDT = days [7, 14] as a verified category. **Monotherapy arm only** (§2 excludes combination cohorts). |
| **GSE165278** (Zappasodi 2021, reusing Chiappinelli 2015 / Nathanson 2017 / Snyder 2014) | Ipilimumab (the parent cohort also included tremelimumab). Index: first anti-CTLA-4 dose (inferred). | "Before ipilimumab" (category). Snyder 2014: samples "obtained at various time points". | "After ipilimumab" / "after initiating CTLA-4 blockade" (category). No schedule. | Category only, no schedule. | **Not applicable.** The parent cohort reports **one tumour per patient** (see below), so the sources support no within-patient pairs. | **No window proposed. Proposed status: NOT PAIRABLE** (cross-sectional pre-versus-post across different patients). |
| **GSE145996** (Amato 2020) | Anti-PD-1 (nivolumab 21%, pembrolizumab 79%). | The paper describes **all** samples as pre-therapeutic. Biorepository specimens; "the time interval between sample collection and subsequent treatment varied from years to months". | **None described** by the paper or the GEO series description. | Neither. The source describes no on-treatment samples. | Not described. | **No window proposed. Proposed status: NOT PAIRABLE.** The spec's "3 post-start samples (196–694 days)" are not supported by the publication; even if real, they fall far outside any scheduled window. |
| **GSE168204** (Du 2021, MGH new cohort) | Anti-PD-1/PD-L1 monotherapy (Du). Index: UNKNOWN (presumably first dose). | "Pre-treatment" (category). | "On-treatment" (category). **No timing is stated in Du 2021.** The sister MGH series (GSE115821, Auslander 2018) says "up to 90 days from treatment start", but that applies to that series, not to GSE168204. | Category only. No schedule for this series. | **UNKNOWN.** | Index = first anti-PD-1/PD-L1 dose (PROPOSED). ON = source category "on-treatment", upper bound UNKNOWN. **Blocked** until a source states timing, or the user accepts a category-only window with a declared upper bound. |

## Riaz et al. 2017 (GSE91061)

Primary source: Riaz N et al., "Tumor and Microenvironment Evolution during Immunotherapy with Nivolumab", *Cell* 171:934–949 (2017), STAR Methods, "Experimental Model and Subject Details". [doi:10.1016/j.cell.2017.09.028](https://doi.org/10.1016/j.cell.2017.09.028), PMC5685550. Text retrieved via PubMed Central.

1. **Treatment and index event.** Eighty-five patients were accrued to the prospective study CA209-038. "All patients received Nivo (3 mg/kg every 2 weeks) until progression or for a maximum of 2 years". Thirty-five of the 68 analysable patients were ipilimumab-progressed (Ipi-P) and 33 were ipilimumab-naive (Ipi-N). The protocol anchors timing to the first nivolumab dose.
2. **Biopsy schedule.** The STAR Methods say the patients "underwent biopsy before commencing therapy (1–7 days before first dose of therapy)" and "underwent a repeat biopsy, collected from the same site, on cycle 1, day 29 (between days 23–29)". The Results and the TCR-seq Methods call this time point "4 weeks post-Nivo initiation".
3. **Exact day or schedule.** The publication gives a protocol schedule only. The GEO series overall design gives category counts only: "109 RNASeq samples (58 On-treatment and 51 Pre-treatment) from 65 patients". Per-sample fields were not read, so whether GEO carries per-specimen days is not known from this review.
4. **Same lesion.** Same lesion by protocol ("collected from the same site"). The Discussion repeats that "biopsies targeted the same site". Lesion identity per specimen is not verified.
5. **Progression and regimen-change biopsies.** The protocol has only the two scheduled biopsies. Response was assessed about every 8 weeks, and progression was confirmed by CT "typically 4 weeks later". No progression biopsies are described as part of the RNA-seq set. The Ipi-P baseline is taken *after* progression on ipilimumab. That is the regimen-history stratum that SPEC §6.4 keeps separate; it is not a mixed-in progression biopsy. The authors removed one patient from all transcriptome analysis as a PCA outlier (RNA Sequencing Methods). Whether A-LONG follows them is a user decision.
6. **Platform and processing.** Tissue for both timepoints was "divided for FFPE and storage with RNAlater". "RNA was extracted from tissue specimens stored using RNAlater". Reads were aligned to hg19 with STAR and counted with Rsamtools against TxDb.Hsapiens.UCSC.hg19.knownGene. The paper does not state the RNA library kit or the RNA sequencer. The HiSeq 2000 V3/2500 statement belongs to the exome section. The GEO series lists platform GPL9052, whose GEO title is "Illumina Genome Analyzer (Homo sapiens)". That conflicts with the HiSeq era of the exome data, so the actual RNA sequencer is **UNKNOWN**. The paper describes no difference in processing between timepoints.
7. **Check of the N12 statement.** N12 says "baseline sampling 1–7 days before the first nivolumab dose": **confirmed verbatim**. N12 says "scheduled on-treatment sampling 23–29 days after treatment start": **imprecise**. The source says "cycle 1, day 29 (between days 23–29)", which is a cycle-day label. Under the usual convention (cycle 1 day 1 = first dose), days 23–29 are **22–28 days after** the first dose. The paper does not state its day-1 convention, so the offset is UNKNOWN. N12 also says "with an intended same-site sample": **confirmed**. N12 says "These are schedule intervals, not exact observed specimen days": **confirmed**.

**PROPOSED window (Riaz).**
- Index event: cycle 1 day 1 = first nivolumab dose [STAR Methods].
- PRE: the protocol baseline biopsy, scheduled 1–7 days before the first dose. Record the bounds as the cycle-day interval [−7, −1] relative to C1D1 [STAR Methods].
- ON: the protocol "cycle 1, day 29" biopsy, scheduled C1 days 23–29 [STAR Methods]. Admit by the source category "On-treatment" [GEO overall design]. Exact day: UNKNOWN. Keep the target as the cycle-day label C1D29. Do not convert it to "days after first dose" until the user picks the convention (see open items).
- Tie rule: the protocol yields one PRE and one ON per patient. If more than one specimen of a category exists for a patient, the source does not settle the choice (UNKNOWN). Proposal: apply the N12 deterministic hierarchy (prefer same lesion, then a known day closest to the target, then the opaque stable tie-breaker) and log the event.
- Lesion policy: same site by design. Label all pairs "same site (protocol)", not "verified same lesion".
- Platform policy: single route (RNAlater, one GEO platform). Sequencer UNKNOWN but common to both timepoints as far as the sources say.
- Strata: Ipi-N and Ipi-P are analysed separately (SPEC §6.4).

## Gide et al. 2019 (PRJEB23709, PRE and EDT)

Primary source: Gide TN et al., "Distinct Immune Cell Populations Define Response to Anti-PD-1 Monotherapy and Anti-PD-1/Anti-CTLA-4 Combined Therapy", *Cancer Cell* 35:238–255.e6 (2019). [doi:10.1016/j.ccell.2019.01.003](https://doi.org/10.1016/j.ccell.2019.01.003). Read from the publisher PDF (user-supplied copy). Cited sections: STAR Methods "Experimental Model and Subject Details" (p. e3) and "RNA Isolation and Sequencing"; Results; legend of Figure 2. The ENA project PRJEB23709 description was read at project level only.

1. **Treatment and index event.** STAR Methods: 54 monotherapy patients ("n=12 nivolumab 3 mg/kg 2-weekly; n=42 pembrolizumab 2 mg/kg 3-weekly"). 51 combination patients ("n=11 ipilimumab 3 mg/kg + nivolumab 1 mg/kg; n=40 ipilimumab 1 mg/kg + pembrolizumab 2 mg/kg"). Patients received standard of care, and some were on clinical trials. Index event: "the commencement of immunotherapy". The paper does not literally say "first dose".
2. **Biopsy timing.** "Pre-treatment (PRE) biopsies taken prior to immunotherapy, and early during treatment (EDT) samples, taken 7-14 days following the commencement of immunotherapy". No lower bound is given for PRE. Patients "were retrospectively identified based on formalin-fixed paraffin-embedded (FFPE) tissue availability". The paper notes that Australian practice requires BRAF testing of melanoma tissue before any drug therapy. So a PRE specimen may be diagnostic or archival tissue taken an unknown time before the index, and possibly before earlier lines of therapy. Prior BRAF inhibitor exposure is tabulated in Table 1. Prior anti-CTLA-4 is not tabulated in the paper. Du 2021 (a secondary source) states that 30 Gide monotherapy patients had prior anti-CTLA-4. That is unverified against Gide.
3. **Exact day or category.** Category plus the stated 7–14-day range only. No per-specimen days appear in the paper. The ENA project record carries only a title and abstract.
4. **Counts relevant to pairing (paper-reported).** RNA-seq monotherapy arm: 41 PRE + 9 EDT, with "9 with matched PRE-EDT samples". RNA-seq combination arm: 32 PRE + 9 EDT, with "7 patients had matched PRE-EDT samples". The Figure 2B legend says "paired PRE-EDT samples from the same patient", and the paired analysis pooled both arms "due to limited number of patient-paired PRE and EDT samples".
5. **Same lesion.** **UNKNOWN.** The paper never says whether EDT came from the PRE lesion.
6. **Progression and regimen-change biopsies.** None described in the RNA-seq set. The two arms are different regimens and must not be mixed. SPEC §2 excludes combination cohorts from A.1, so only the monotherapy arm (9 paper-reported pairs) is in scope.
7. **Platform and processing.** "Total RNA was isolated from FFPE tissue sections using the AllPrep DNA/RNA FFPE Kit". Libraries used the "TruSeq RNA Access Library Prep Kit" (exome capture, not poly-A), sequenced paired-end on the HiSeq 2500 (median 47 M reads). The same route is described for PRE and EDT.
8. **Check of the N12 statement.** N12 says "PRE is before therapy and EDT is scheduled 7–14 days after treatment begins": **confirmed**. The source wording is "taken 7-14 days following the commencement of immunotherapy". "Scheduled" overstates it slightly: the paper reports the range of days on which the samples were taken, not a protocol schedule. **Discrepancy to resolve:** N12 and SPEC §2 mention a 14-run title-rule crosswalk. The paper reports 18 EDT RNA samples (9 + 9) and 16 matched RNA pairs (9 monotherapy + 7 combination). The 14 does not match either number. The crosswalk stays unaccepted.

**PROPOSED window (Gide).**
- Index event: commencement of anti-PD-1 therapy, read as the first ICI dose [STAR Methods; "first dose" is an interpretation, flagged].
- PRE: any source-labelled PRE specimen before the index. Lower bound: UNKNOWN; the source gives none. The user decides whether to require one (see open items).
- EDT: verified source category "EDT", with the stated range of days [7, 14] after commencement [STAR Methods]. Exact day: UNKNOWN.
- Tie rule: not settled by the source. Proposal: as for Riaz (N12 hierarchy), with the event logged.
- Lesion policy: lesion UNKNOWN for every pair. Label pairs "lesion unknown". No same-lesion sensitivity is estimable.
- Platform policy: FFPE + RNA Access + HiSeq 2500 at both timepoints [STAR Methods]. One route.
- Regimen: monotherapy arm only. The combination arm is excluded per SPEC §2 (not randomised, so the §2 within-study arm comparison does not apply).

## GSE165278 (Zappasodi et al. 2021)

Primary sources:
- Zappasodi R et al., *Nature* 591:652–658 (2021), [doi:10.1038/s41586-021-03326-4](https://doi.org/10.1038/s41586-021-03326-4), PMC8057670: Methods "RNA sequencing analyses" and Data Availability.
- The two cited parent publications: Chiappinelli KB et al., *Cell* 162:974–986 (2015), [doi:10.1016/j.cell.2015.07.011](https://doi.org/10.1016/j.cell.2015.07.011); and Nathanson T et al., *Cancer Immunol Res* 5:84–91 (2017), [doi:10.1158/2326-6066.CIR-16-0019](https://doi.org/10.1158/2326-6066.CIR-16-0019).
- Their cohort source: Snyder A et al., *N Engl J Med* 371:2189–2199 (2014), [doi:10.1056/NEJMoa1406498](https://doi.org/10.1056/NEJMoa1406498).
- The GEO series description.

1. **Treatment and index event.** The GEO overall design reads "human melanoma tumors before and after ipilimumab treatment". Zappasodi Methods: "22 human melanoma samples (n=7, before ipilimumab; n=15, after ipilimumab) from our previously published analyses", citing Chiappinelli 2015 and Nathanson 2017. Snyder 2014 is the parent cohort: 64 patients, "of whom 5 were treated with tremelimumab". Index event: first anti-CTLA-4 dose (inferred; no source states it).
2. **Timing.** Nathanson 2017 says "34 patients had tumor samples collected prior to initiating CTLA-4 blockade and 30 patients had samples collected after initiating CTLA-4 blockade". Snyder 2014 Discussion says "tumor samples were obtained at various time points". No schedule, range, or per-specimen day is given in any of the four sources.
3. **Pairing.** The sources report **one tumour per patient**. Snyder reports "128 exomes" (64 tumours + 64 matched normals) from 64 patients. Nathanson's 34 pre + 30 post = 64 patients corresponds to the "64-sample dataset". The 24 RNA-seq samples (9 pre, 15 post) "were a subset of the published 64-sample dataset". **On the sources, the pre and post samples come from different patients.** No within-patient change can be formed. Not checked here: whether any patient contributes to both GEO categories. That would require per-sample metadata, which this review did not read.
4. **Progression-type samples.** Snyder's clinical groups include "CTLA-4 blockade with resection of an isolated stable or nonresponding lesion". Nathanson reports "Eight discordant lesions ... among post-treatment samples" and that one RNA-seq post-treatment lesion was discordant. So the post-treatment set may contain resections of progressing or nonresponding lesions. SPEC §3 forbids treating those as scheduled on-treatment samples.
5. **Platform.** Nathanson 2017: "Illumina TruSeq mRNA library kit (v2) ... HiSeq 2500 with 2x50bp paired reads" (New York Genome Center). The GEO series platform is GPL16791 (HiSeq 2500). The TruSeq Stranded / HiSeq 4000 text in Zappasodi applies to the mouse samples only. Tissue preservation for the human samples is not stated (UNKNOWN).
6. **Same lesion.** Not applicable (different patients).

**PROPOSED status (GSE165278): NOT PAIRABLE. No window registered.** Reason: the sources describe a cross-sectional before/after design across different patients, at unscheduled times, with possible nonresponding-lesion resections. A cross-sectional on-treatment R-versus-NR contrast is explicitly not a change claim (SPEC §7).

## GSE145996 (Amato et al. 2020)

Primary source: Amato CM et al., "Pre-Treatment Mutational and Transcriptomic Landscape of Responding Metastatic Melanoma Patients to Anti-PD1 Immunotherapy", *Cancers* 12:1943 (2020), [doi:10.3390/cancers12071943](https://doi.org/10.3390/cancers12071943), PMC7409244, Methods 2.1–2.2 and 2.5, and the GEO series description.

1. **Treatment.** "All patients had tumor samples taken before anti-PD1 immune checkpoint therapy of nivolumab (21%) or pembrolizumab (79%)".
2. **Timing.** The design is pre-treatment only. The series title is "Pre- Treatment ... Landscape"; the GEO overall design is "We analyzed pre-immunotherapy treated tumors from 52 patients". Methods 2.1: "52 patients with 71 total tissue samples that had previously undergone immunotherapy and had a pre-therapeutic biopsy". Methods 2.2: the IRB allows collection of archived specimens "at any time. Therefore, the time interval between sample collection and subsequent treatment varied from years to months". RNA-seq covers 14 samples ("8 responding tumor samples and 6 non-responding tumor samples").
3. **On-treatment samples.** **None are described** in the publication or the series description. The SPEC §2 roster note ("3 samples collected after the anti-PD-1 start (196–694 days)") presumably comes from per-sample fields, which this review did not open. The publication does not support it. If such samples exist, they were taken 6.5 to 23 months after start, with no schedule and no stated reason (progression, resection, or other). Under SPEC §3 they could not count as scheduled on-treatment samples without a documented reason.
4. **Same lesion.** Not described.
5. **Platform.** "Nugen Universal Plus mRNA seq kit was used for polyA selected RNA library construction", single-end 150 cycles on the HiSeq 2500. RNA came "from frozen tissue or cells" (RNeasy Plus Mini). GEO platform: GPL16791 (HiSeq 2500).

**PROPOSED status (GSE145996): NOT PAIRABLE. No window registered.** Reason: the publication describes a pre-treatment-only design. The post-start samples cited in the roster are unsupported by the source and fall outside any scheduled window.

## GSE168204 (Du et al. 2021, new MGH cohort)

Primary sources:
- Du K et al., "Pathway signatures derived from on-treatment tumor specimens predict response to anti-PD1 blockade in metastatic melanoma", *Nat Commun* 12:6023 (2021), [doi:10.1038/s41467-021-26299-4](https://doi.org/10.1038/s41467-021-26299-4), PMC8519947: Results "Patient cohorts" and Methods.
- The GEO series description.
- Auslander N et al., *Nat Med* 24:1545–1549 (2018), [doi:10.1038/s41591-018-0157-9](https://doi.org/10.1038/s41591-018-0157-9), PMC6693632. This describes the earlier MGH series, GSE115821.

1. **Treatment and index event.** Du describes "patients with metastatic melanoma who were treated with anti-PD1/PD-L1 monotherapy at Massachusetts General Hospital (MGH), including a published dataset and a newly generated dataset". GSE168204 is the newly generated dataset: "a total of 27 pre- and on-treatment tumor specimens". Samples were collected under the DFCI protocol 11-181 and Wistar IRB protocols. Index event: not stated (UNKNOWN).
2. **Timing.** Du gives **no day schedule or range** for "on-treatment". The only MGH timing statement is in Auslander 2018: "(up to 90 days from treatment start)". It refers to GSE115821, a different series and partly a different patient set. Du's MGH pair counts ("42 paired pre- and on-treatment biopsies and 8 unpaired") combine both series. They cannot be attributed to GSE168204 alone; N12 already says this, and it is confirmed.
3. **Exact day or category.** Category only ("pre-treatment" / "on-treatment"). The day-field origin in the deposit is UNKNOWN (per-sample fields not read).
4. **Progression and regimen-change biopsies.** Not addressed by Du. Du excluded only specimens "not subject to RNA sequencing, lacked response evaluation, or ... duplicated tumor specimens of the same timepoint". So on-treatment specimens taken at progression cannot be ruled out from the source.
5. **Same lesion.** **UNKNOWN.** The GEO summary says the authors "investigated the effect of biopsy sites at the same biopsy time point", which implies that biopsy sites vary.
6. **Platform and processing.** This is the critical point for this series. Du Methods: "RNA was extracted from fresh frozen tumors". The GEO overall design says "frozen or formalin-fixed tumor specimens". These disagree on preservation. Sequencing was done at two sites on two instruments: "Broad Institute (Illumina HiSeq2000) and the Wistar Institute (Illumina NextSeq 500)". The GEO series lists GPL11154 and GPL18573. Library chemistry: "standard Illumina protocols" (kit unnamed). Within-patient PRE/ON pairs may therefore straddle preservation methods and/or sequencers.

**PROPOSED window (GSE168204).**
- Index event: first anti-PD-1/PD-L1 dose (PROPOSED). The source does not state it.
- PRE: source category "pre-treatment". Bounds UNKNOWN.
- ON: source category "on-treatment". Lower bound > 0 days (by definition). Upper bound UNKNOWN. **Do not borrow** the Auslander "up to 90 days" bound; it belongs to GSE115821.
- Tie rule: UNKNOWN. Du dropped same-timepoint duplicates without stating a rule. Proposal: the N12 hierarchy.
- Lesion policy: lesion UNKNOWN for every pair.
- Platform policy: admit a pair only when both members share the same GEO platform (and preservation method, if determinable). Otherwise label the pair "cross-platform", or exclude it under a user-chosen rule.
- **Status: BLOCKED.** Pairing waits until a source gives on-treatment timing, or until the user accepts a category-only window and declares an upper bound.

## Still open / needs the user's decision

1. **Riaz day convention.** Should "cycle 1, day 29 (days 23–29)" be recorded as cycle-day labels (recommended, source-faithful), or converted to "22–28 days after first dose" under the C1D1 = day 1 convention, which the paper does not state? N12's "23–29 days after treatment start" should be corrected either way.
2. **Riaz outlier.** Should A-LONG follow the authors' removal of one patient from transcriptome analysis (PCA outlier), or keep that patient and record the authors' exclusion as a flag?
3. **Riaz platform.** The GEO platform record (Illumina Genome Analyzer) and the paper (no RNA sequencer stated) leave the RNA sequencer UNKNOWN. Accept it as a single unknown platform common to both timepoints?
4. **Gide PRE lower bound.** The source gives none, and PRE tissue may be archival BRAF-testing tissue. Options: accept any pre-index PRE; or require a user-chosen maximum look-back. A look-back would need per-specimen dates the sources do not give, so in practice it would block Gide.
5. **Gide crosswalk count.** The paper reports 16 matched RNA pairs (9 monotherapy, 7 combination) and 18 EDT RNA samples. The candidate title-rule crosswalk has 14 runs. Reconcile before accepting any crosswalk (SPEC §9 gate 2). With combination excluded, at most 9 monotherapy pairs are expected from the paper.
6. **Gide "commencement" = first dose?** Accept this reading for the index event?
7. **Gide lesion unknown.** Run Gide with all pairs labelled "lesion unknown" and no same-lesion sensitivity, or drop it?
8. **Gide monotherapy prior anti-CTLA-4.** Gide does not tabulate it; only a secondary source (Du 2021) states it. Is a Riaz-style ipi-N/ipi-P split required for Gide? Applying one would need per-patient data the sources do not give.
9. **GSE165278.** Accept NOT PAIRABLE (cross-sectional, different patients) and drop it from the A-LONG paired roster? A per-sample check that no patient sits in both categories would be a separate, metadata-only task the user must authorise.
10. **GSE145996.** Accept NOT PAIRABLE (pre-treatment-only design) and drop it? The "3 post-start samples, 196–694 days" roster note conflicts with the publication and would need a metadata-only check, which this review did not do.
11. **GSE168204 window.** Choose one: (a) keep it blocked until a primary source gives on-treatment timing (for example, the authors or the DFCI 11-181 protocol); (b) accept a category-only window with a user-declared upper bound; or (c) drop it. Also choose the cross-platform policy (HiSeq 2000 vs NextSeq 500; frozen vs FFPE).
12. **Tie rule.** None of the five sources states a tie rule. Confirm the N12 hierarchy (same lesion, then known day closest to target, then opaque stable tie-breaker) as the registered rule for every study.

### Effect on the candidate roster (if items 9–11 are accepted as proposed)
A-LONG paired analysis would rest on two studies: Riaz, with ipi-N and ipi-P as separate strata, and Gide monotherapy (up to 9 paper-reported pairs, lesion unknown). Under the signed small-k rules, any synthesis would be k ≤ 2 per regimen family, so tentative at most. Riaz and Gide also differ in window (C1D29 versus days 7–14), and SPEC §5 combines studies only when windows are compatible. So they may not be poolable at all. That is a further user decision.
