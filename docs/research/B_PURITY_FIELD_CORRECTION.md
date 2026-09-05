# Quarantine the mislabeled CPC portal purity field

6 September 2026. **Verified source-definition correction; no patient analysis was run.** The proposed B baseline must not consume `WGS_BASED_PURITY_ESTIMATION` from the inspected `prad_cpcg_2017` portal as tumour purity.

The original Fraser et al. Supplementary Table1 contains a field named `WGSvsOS accuracy`. Its legend, PDF page3, defines agreement between SNP calls from WGS and OncoScan. It is an assay agreement measure. In contrast, the same legend separately defines Qpure cellularity from matched tumour/blood SNP-array data, ASCAT cellularity from SNP-array profiles, pathologist-estimated cellularity and methylation-derived LUMP cellularity. These methods are distinct and are not automatically interchangeable. [Original study](https://doi.org/10.1038/nature20788), [original supplement and Table1 legend](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fnature20788/MediaObjects/41586_2017_BFnature20788_MOESM323_ESM.pdf).

The source auditor compared all130 CPCG portal values with original Table1 values under exact specimen identifiers. Astra independently repeated that comparison using the bundled Python runtime and openpyxl: all130 match, with maximum absolute difference `4.996451030692128e-10`. Astra also independently read the original legend. This is stronger evidence than inferring biological meaning from the portal's display name. The numerical match alone would not establish meaning without that source definition.

## Required specification consequence

- Retain the original portal field and its exact name in provenance, but classify it as **assay agreement / quarantined from purity**. It may not populate `purity_value`, count as an available independent-purity covariate, or silently substitute for a missing cellularity measurement.
- Correct the earlier interpretation of 73 paired patients with “WGS purity.” Seventy-three is still the count of candidate code matches through that portal route; it is not a verified count of patients with a legitimate purity measurement.
- Original Table1 offers separate cellularity candidates. Their specimen linkage, availability, missingness and comparability with TCGA need their own evidence. LUMP comes from methylation and cannot be presented as an independent genomic purity measurement.
- Future covariate-ingestion acceptance checks must reject this portal attribute as purity even when it is numeric, finite and within0–1. Range checks and a plausible column name cannot validate a measurement definition.

This correction applies to both proposed B-P and B-R; it chooses neither. It changes no patient outcomes and performs no baseline fit. Historical audit files remain preserved with this explicit correction so the original error cannot be silently reused.

The independent metadata check is retained in `SOURCE_GATE_REVIEW/ROOT_SOURCE_GATE_CHECK.json`. The first attempt used a local interpreter without openpyxl and failed before any comparison; the successful check used the existing bundled runtime. No package was installed into a shared environment. Source clinical tables remain outside Git; no individual cellularity values are published here.
