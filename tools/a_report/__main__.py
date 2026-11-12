"""Build patient-free manuscript shells from fixed, invented display values.

This module contains presentation data only. It does not open project data,
runtime directories, model outputs, or statistical software.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

LABEL = "INVENTED DATA — MANUSCRIPT SHELL"
CODE_VERSION = "tools.a_report.v1"
FIXTURE_ID = "paper_a_joint_layout_fixture_v1"
ROOT = Path(__file__).resolve().parents[2]
plt = None


def _load_plotting():
    global plt
    if plt is not None:
        return plt
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as pyplot
    except ImportError as error:
        raise ValueError(
            "figure rendering requires Matplotlib and NumPy; use the existing "
            "sc-analysis Python environment"
        ) from error
    matplotlib.rcParams["svg.fonttype"] = "none"
    plt = pyplot
    return pyplot


FIGURE_NAMES = (
    "Figure_01_cohort_overview",
    "Figure_02_panel_forests",
    "Figure_03_gene_meta",
    "Figure_04_hallmark_summary",
    "Figure_05_a_p2_validation",
    "Figure_06_sc1_compartment_dotplot",
    "Figure_07_sc3_exploratory_effects",
    "Figure_08_along_pairing_time_effects",
    "Supplement_S1_bulk_qc_pca_de",
    "Supplement_S2_a_comp",
    "Supplement_S3_a_long_1a",
    "Supplement_S4_a_long_2a",
    "Supplement_S5_a_long_2c",
    "Supplement_S6_a_long_3c",
    "Supplement_S7_a_long_3a_gated",
    "Supplement_S8_a_long_3b_gated",
    "Supplement_S9_a_long_4a_gated",
    "Supplement_S10_a_long_4b_gated",
)

_COHORTS = [
    {"cohort": "Invented cohort A", "cancer": "Cancer A", "drug": "Drug class A", "platform": "RNA-seq", "n": 42},
    {"cohort": "Invented cohort B", "cancer": "Cancer A", "drug": "Drug class B", "platform": "Microarray", "n": 31},
    {"cohort": "Invented cohort C", "cancer": "Cancer B", "drug": "Drug class A", "platform": "NanoString", "n": 27},
    {"cohort": "Invented cohort D", "cancer": "Cancer C", "drug": "Drug class C", "platform": "Targeted RNA", "n": 19},
]
_PANEL_EFFECTS = [
    {"label": "Cancer A · Drug A · Panel A", "estimate": 0.48, "lower": 0.09, "upper": 0.87, "n": 42, "status": "illustrative"},
    {"label": "Cancer A · Drug B · Panel A", "estimate": 0.18, "lower": -0.21, "upper": 0.57, "n": 31, "status": "nonsignificant example"},
    {"label": "Cancer B · Drug A · Panel B", "estimate": -0.31, "lower": -0.72, "upper": 0.10, "n": 27, "status": "discordant example"},
    {"label": "Cancer C · Drug C · Panel B", "estimate": 0.36, "lower": 0.02, "upper": 0.70, "n": 19, "status": "illustrative"},
    {"label": "Cancer C · Drug C · Panel C", "estimate": None, "lower": None, "upper": None, "n": 19, "status": "unavailable example"},
]
_GENE_META = [
    {"gene": "Gene A", "pooled_g": 0.54, "neg_log10_fdr": 2.1, "fdr": 0.008, "study_a": 0.71, "study_b": 0.36, "study_c": 0.48},
    {"gene": "Gene B", "pooled_g": 0.11, "neg_log10_fdr": 0.3, "fdr": 0.50, "study_a": 0.28, "study_b": -0.10, "study_c": 0.14},
    {"gene": "Gene C", "pooled_g": -0.32, "neg_log10_fdr": 1.2, "fdr": 0.06, "study_a": -0.51, "study_b": -0.22, "study_c": 0.03},
    {"gene": "Gene D", "pooled_g": 0.27, "neg_log10_fdr": 0.7, "fdr": 0.20, "study_a": None, "study_b": 0.31, "study_c": 0.24},
    {"gene": "Gene E", "pooled_g": None, "neg_log10_fdr": None, "fdr": None, "study_a": None, "study_b": None, "study_c": None},
]
_HALLMARK = [
    {"set": "Hallmark set A", "meta_g": 0.42, "meta_lower": 0.08, "meta_upper": 0.76, "meta_q": 0.04, "fgsea_nes": 1.6, "fgsea_padj": 0.07, "status": "nonsignificant fgsea example"},
    {"set": "Hallmark set B", "meta_g": -0.16, "meta_lower": -0.51, "meta_upper": 0.19, "meta_q": 0.42, "fgsea_nes": -1.1, "fgsea_padj": 0.31, "status": "nonsignificant; same displayed direction"},
    {"set": "Hallmark set C", "meta_g": None, "meta_lower": None, "meta_upper": None, "meta_q": None, "fgsea_nes": None, "fgsea_padj": None, "status": "unavailable example"},
]
_ROC = {
    "Development example (invented)": {"x": [0.0, 0.20, 1.0], "y": [0.0, 0.74, 1.0], "auroc": 0.77},
    "Final-test example (invented)": {"x": [0.0, 0.25, 1.0], "y": [0.0, 0.49, 1.0], "auroc": 0.62},
}
_PAIRED_DELTA = [
    {"split": "Development example", "delta": 0.09, "lower": None, "upper": None, "status": "point estimate only"},
    {"split": "Final-test example", "delta": 0.06, "lower": -0.11, "upper": 0.20, "status": "95% interval crosses zero"},
]
_SC1_STUDIES = ("Invented study A", "Invented study B", "Invented study C")
_SC1_COMPARTMENTS = ("Compartment A", "Compartment B")
_SC1_PANEL_ROWS = ("Custom panel A", "Custom panel B")
_SC1_COMPOSITE_CELLS = [
    {"study": "Invented study A", "compartment": "Compartment A", "gene_group": "Custom panel A", "unit_id": "CUSTOM:Invented panel A", "unit_type": "panel", "method_id": "invented method A", "median_log2_cpm_plus1": 0.0, "n_donors_support": 5, "status": "shown", "reason": ""},
    {"study": "Invented study A", "compartment": "Compartment B", "gene_group": "Custom panel A", "unit_id": "CUSTOM:Invented panel A", "unit_type": "panel", "method_id": "invented method A", "median_log2_cpm_plus1": 1.20, "n_donors_support": 5, "status": "shown", "reason": ""},
    {"study": "Invented study A", "compartment": "Compartment A", "gene_group": "Custom panel B", "unit_id": "CUSTOM:Invented panel B", "unit_type": "panel", "method_id": "invented method A", "median_log2_cpm_plus1": 0.75, "n_donors_support": 5, "status": "shown", "reason": ""},
    {"study": "Invented study A", "compartment": "Compartment B", "gene_group": "Custom panel B", "unit_id": "CUSTOM:Invented panel B", "unit_type": "panel", "method_id": "invented method A", "median_log2_cpm_plus1": None, "n_donors_support": 0, "status": "not_assessed", "reason": "invented unassessed cell"},
    {"study": "Invented study B", "compartment": "Compartment A", "gene_group": "Custom panel A", "unit_id": "CUSTOM:Invented panel A", "unit_type": "panel", "method_id": "invented method B", "median_log2_cpm_plus1": 2.40, "n_donors_support": 6, "status": "shown", "reason": ""},
    {"study": "Invented study B", "compartment": "Compartment B", "gene_group": "Custom panel A", "unit_id": "CUSTOM:Invented panel A", "unit_type": "panel", "method_id": "invented method B", "median_log2_cpm_plus1": 1.80, "n_donors_support": 6, "status": "shown", "reason": ""},
    {"study": "Invented study B", "compartment": "Compartment A", "gene_group": "Custom panel B", "unit_id": "CUSTOM:Invented panel B", "unit_type": "panel", "method_id": "invented method B", "median_log2_cpm_plus1": None, "n_donors_support": 3, "status": "insufficient_donors", "reason": "invented support below display minimum"},
    {"study": "Invented study B", "compartment": "Compartment B", "gene_group": "Custom panel B", "unit_id": "CUSTOM:Invented panel B", "unit_type": "panel", "method_id": "invented method B", "median_log2_cpm_plus1": 0.0, "n_donors_support": 6, "status": "shown", "reason": ""},
    {"study": "Invented study C", "compartment": "Compartment A", "gene_group": "Custom panel A", "unit_id": "CUSTOM:Invented panel A", "unit_type": "panel", "method_id": "invented method C", "median_log2_cpm_plus1": 0.0, "n_donors_support": 5, "status": "shown", "reason": ""},
    {"study": "Invented study C", "compartment": "Compartment B", "gene_group": "Custom panel A", "unit_id": "CUSTOM:Invented panel A", "unit_type": "panel", "method_id": "invented method C", "median_log2_cpm_plus1": None, "n_donors_support": 0, "status": "not_assessed", "reason": "invented unassessed cell"},
    {"study": "Invented study C", "compartment": "Compartment A", "gene_group": "Custom panel B", "unit_id": "CUSTOM:Invented panel B", "unit_type": "panel", "method_id": "invented method C", "median_log2_cpm_plus1": 0.0, "n_donors_support": 5, "status": "shown", "reason": ""},
    {"study": "Invented study C", "compartment": "Compartment B", "gene_group": "Custom panel B", "unit_id": "CUSTOM:Invented panel B", "unit_type": "panel", "method_id": "invented method C", "median_log2_cpm_plus1": None, "n_donors_support": 2, "status": "insufficient_donors", "reason": "invented support below display minimum"},
]
_SC3_COHORTS = ("Invented cohort A", "Invented cohort B", "Invented cohort C")
_SC3_PANEL_COMPARTMENTS = (
    "Custom panel A · Compartment A", "Custom panel A · Compartment B",
    "Custom panel B · Compartment A", "Custom panel B · Compartment B",
)
_SC3_METRIC_FAMILIES = [
    {"family": "RECIST", "label": "RECIST · invented response metric family", "values": [
        [0.42, 0.00, -0.18], [-0.21, 0.33, None], [0.15, -0.44, 0.26], [0.08, -0.12, 0.54],
    ]},
    {"family": "Pathology", "label": "Pathology · invented response metric family", "values": [
        [-0.12, 0.36, 0.21], [0.43, -0.05, 0.17], [-0.31, 0.14, -0.22], [0.19, 0.51, -0.37],
    ]},
    {"family": "T-cell expansion", "label": "T-cell expansion · distinct nonclinical metric family", "values": [
        [0.11, -0.24, 0.09], [0.37, 0.06, -0.41], [-0.19, 0.29, 0.00], [0.24, -0.33, 0.18],
    ]},
]
_ALONG_EFFECTS = [
    {"unit": "CUSTOM:Invented panel A", "unit_family": "panel", "feature_method_id": "invented feature method", "analysis_method_id": "invented two-timepoint method", "endpoint_id": "invented endpoint", "regimen_id": "invented regimen", "window_id": "invented single window", "assay_id": "invented assay", "effect_scale_id": "INVENTED_NATIVE_SCALE_A", "panel_family": "invented panel family", "multiplicity_family_id": "INVENTED_PANEL_FAMILY", "source_family_id": "INVENTED_SOURCE_FAMILY", "overlap_receipt_id": "INVENTED_OVERLAP_RECEIPT", "overlap_status": "invented only", "study": "Invented study A", "patient_set_id": "invented patient set A", "model": "two_timepoint", "contrast": "R_minus_NR_change", "effect_role": "central_change_contrast", "estimate": 0.24, "ci_lb": 0.04, "ci_ub": 0.44, "status": "invented illustrative", "reason": ""},
    {"unit": "CUSTOM:Invented panel A", "unit_family": "panel", "feature_method_id": "invented feature method", "analysis_method_id": "invented two-timepoint method", "endpoint_id": "invented endpoint", "regimen_id": "invented regimen", "window_id": "invented single window", "assay_id": "invented assay", "effect_scale_id": "INVENTED_NATIVE_SCALE_A", "panel_family": "invented panel family", "multiplicity_family_id": "INVENTED_PANEL_FAMILY", "source_family_id": "INVENTED_SOURCE_FAMILY", "overlap_receipt_id": "INVENTED_OVERLAP_RECEIPT", "overlap_status": "invented only", "study": "Invented study B", "patient_set_id": "invented patient set B", "model": "two_timepoint", "contrast": "R_minus_NR_change", "effect_role": "central_change_contrast", "estimate": -0.08, "ci_lb": -0.31, "ci_ub": 0.15, "status": "invented nonsignificant example", "reason": ""},
    {"unit": "CUSTOM:Invented panel A", "unit_family": "panel", "feature_method_id": "invented feature method", "analysis_method_id": "invented two-timepoint method", "endpoint_id": "invented endpoint", "regimen_id": "invented regimen", "window_id": "invented single window", "assay_id": "invented assay", "effect_scale_id": "INVENTED_NATIVE_SCALE_A", "panel_family": "invented panel family", "multiplicity_family_id": "INVENTED_PANEL_FAMILY", "source_family_id": "INVENTED_SOURCE_FAMILY", "overlap_receipt_id": "INVENTED_OVERLAP_RECEIPT", "overlap_status": "invented only", "study": "Invented study C", "patient_set_id": "invented patient set C", "model": "two_timepoint", "contrast": "R_minus_NR_change", "effect_role": "central_change_contrast", "estimate": None, "ci_lb": None, "ci_ub": None, "status": "NOT_ESTIMABLE", "reason": "invented too-few-pairs layout"},
]
_ANCOVA = {
    "unit": "CUSTOM:Invented panel A", "unit_family": "panel",
    "feature_method_id": "invented feature method",
    "analysis_method_id": "invented ANCOVA sensitivity method",
    "endpoint_id": "invented endpoint", "regimen_id": "invented regimen",
    "window_id": "invented single window", "assay_id": "invented assay",
    "effect_scale_id": "INVENTED_NATIVE_SCALE_A", "panel_family": "invented panel family",
    "multiplicity_family_id": "INVENTED_PANEL_FAMILY",
    "source_family_id": "INVENTED_SOURCE_FAMILY",
    "overlap_receipt_id": "INVENTED_OVERLAP_RECEIPT", "overlap_status": "invented only",
    "study": "Invented study B", "patient_set_id": "invented patient set B",
    "model": "ancova_sensitivity",
    "contrast": "R_minus_NR_on_value_conditional_on_pre",
    "effect_role": "sensitivity", "estimate": 0.11, "ci_lb": -0.07,
    "ci_ub": 0.29, "status": "invented sensitivity example",
    "reason": "conditional on baseline association; not central Delta",
}
_ALONG_TIMING_EXAMPLES = {
    "pre_day": 0,
    "exact_on_day": 28,
    "interval_on_start": 21,
    "interval_on_end": 42,
}
_ALONG_SOURCE_COVERAGE = [
    {"family": "Invented family A", "catalogue_entries": 2,
     "regimen_id": "Invented regimen A", "window_id": "Invented window A",
     "selected_pairs": 4},
    {"family": "Invented family B", "catalogue_entries": 1,
     "regimen_id": "Invented regimen B", "window_id": "Invented window B",
     "selected_pairs": 2},
]
_ALONG_WITHIN_GROUP_DELTAS = [
    {"unit": "CUSTOM:Invented panel A", "window": "baseline_to_on",
     "response": "R", "arm": "Invented arm A", "n": 8,
     "estimate": 0.28, "se": 0.10, "ci_lb": 0.06, "ci_ub": 0.50,
     "df": 7, "effect_role": "invented within-group display",
     "status": "invented illustrative", "reason": "",
     "policy_status": "invented display only"},
    {"unit": "CUSTOM:Invented panel A", "window": "baseline_to_on",
     "response": "NR", "arm": "Invented arm A", "n": 7,
     "estimate": 0.08, "se": 0.12, "ci_lb": -0.17, "ci_ub": 0.33,
     "df": 6, "effect_role": "invented within-group display",
     "status": "invented illustrative", "reason": "",
     "policy_status": "invented display only"},
    {"unit": "CUSTOM:Invented panel A", "window": "baseline_to_on",
     "response": "NR", "arm": "Invented arm A", "n": None,
     "estimate": None, "se": None, "ci_lb": None, "ci_ub": None,
     "df": None, "effect_role": "invented unavailable display",
     "status": "NOT_ESTIMABLE", "reason": "invented support unavailable",
     "policy_status": "invented display only"},
]
_ALONG_PROGRAMME_ROWS = [
    {"programme": "Invented programme A", "source_family_id": "Invented family A",
     "cancer": "Invented cancer A", "n_R": 8, "n_NR": 7,
     "estimate": 0.30, "ci_lb": 0.06, "ci_ub": 0.54},
    {"programme": "Invented programme A", "source_family_id": "Invented family B",
     "cancer": "Invented cancer B", "n_R": 6, "n_NR": 5,
     "estimate": 0.18, "ci_lb": -0.02, "ci_ub": 0.38},
    {"programme": "Invented programme A", "source_family_id": "Invented family C",
     "cancer": "Invented cancer A", "n_R": 7, "n_NR": 6,
     "estimate": 0.25, "ci_lb": 0.04, "ci_ub": 0.46},
    {"programme": "Invented programme B", "source_family_id": "Invented family A",
     "cancer": "Invented cancer A", "n_R": 8, "n_NR": 7,
     "estimate": -0.18, "ci_lb": -0.42, "ci_ub": 0.06},
    {"programme": "Invented programme B", "source_family_id": "Invented family B",
     "cancer": "Invented cancer B", "n_R": 6, "n_NR": 5,
     "estimate": 0.07, "ci_lb": -0.11, "ci_ub": 0.25},
    {"programme": "Invented programme B", "source_family_id": "Invented family C",
     "cancer": "Invented cancer A", "n_R": 7, "n_NR": 6,
     "estimate": 0.12, "ci_lb": -0.08, "ci_ub": 0.32},
]
_ALONG_SENSITIVITY_ROWS = [
    {"model_label": "delta_primary", "estimate": 0.24, "ci_lb": 0.04,
     "ci_ub": 0.44, "n_patients_used": 12,
     "support_relation": "invented reference support"},
    {"model_label": "same-lesion sensitivity", "estimate": 0.18, "ci_lb": -0.09,
     "ci_ub": 0.45, "n_patients_used": 8,
     "support_relation": "invented changed support"},
    {"model_label": "exact-day sensitivity", "estimate": 0.29, "ci_lb": 0.04,
     "ci_ub": 0.54, "n_patients_used": 10,
     "support_relation": "invented changed support"},
    {"model_label": "tighter-timing sensitivity", "estimate": 0.21, "ci_lb": -0.05,
     "ci_ub": 0.47, "n_patients_used": 9,
     "support_relation": "invented changed support"},
]

_EFFECT_COLUMNS = (
    "unit_family", "unit", "method_id", "m5m6_gene_flag", "study", "cancer",
    "cancer_components", "drug_class_stratum", "endpoint_family",
    "endpoint_definition_id", "patient_set_id", "n_R", "n_NR", "mean_R",
    "mean_NR", "sd_R", "sd_NR", "g", "se", "status", "reason", "n_found",
    "n_total", "sensitivity_label",
)
_SYNTHESIS_COLUMNS = (
    "unit_family", "unit", "method_id", "m5m6_gene_flag", "endpoint_family",
    "endpoint_definition_id", "study", "patient_set_id", "n_R", "n_NR",
    "stratum_type", "stratum", "cancer", "drug_class_stratum", "stage", "k",
    "estimate", "se", "n_cancers", "n_studies", "sensitivity_label", "ci_lb",
    "ci_ub", "tau2", "I2", "Q", "p", "fixed_estimate", "fixed_ci_lb",
    "fixed_ci_ub", "q", "label", "low_k", "status", "reason", "weighting",
)
_SUBGROUP_COLUMNS = (
    "unit_family", "unit", "method_id", "endpoint_family",
    "endpoint_definition_id", "moderator", "total_k", "n_levels", "F", "p",
    "status", "reason",
)
_BIO_COVERAGE_COLUMNS = (
    "cohort_id", "unit_family", "unit", "n_found", "n_total", "complete",
    "scorable", "missing", "fixed_subset", "reason", "sensitivity_label",
)
_PAIR_ROWS = [
    {"study_id": "Invented study A", "specimens_in": 18, "assays_in": 18, "patients_in": 10, "patients_with_baseline": 10, "patients_with_followup": 8, "patients_paired": 6, "candidate_pairs": 8, "selected_pairs": 6, "technical_replicate_specimens": 0, "same_lesion_pairs": 4, "platform_counts": "Invented platform A: 18 assays", "selected_by_window": "Invented single window: 6 selected pairs", "endpoint_evaluable_counts": "unavailable before release", "endpoint_status": "unavailable before release", "derived_unpaired_baseline_patients": 4, "derived_field_definition": "patients_with_baseline - patients_paired; single-window invented example"},
    {"study_id": "Invented study B", "specimens_in": 15, "assays_in": 15, "patients_in": 8, "patients_with_baseline": 8, "patients_with_followup": 7, "patients_paired": 5, "candidate_pairs": 6, "selected_pairs": 5, "technical_replicate_specimens": 0, "same_lesion_pairs": 3, "platform_counts": "Invented platform B: 15 assays", "selected_by_window": "Invented single window: 5 selected pairs", "endpoint_evaluable_counts": "unavailable before release", "endpoint_status": "unavailable before release", "derived_unpaired_baseline_patients": 3, "derived_field_definition": "patients_with_baseline - patients_paired; single-window invented example"},
    {"study_id": "Invented study C", "specimens_in": 7, "assays_in": 7, "patients_in": 4, "patients_with_baseline": 4, "patients_with_followup": 3, "patients_paired": 2, "candidate_pairs": 3, "selected_pairs": 2, "technical_replicate_specimens": 0, "same_lesion_pairs": 1, "platform_counts": "Invented platform C: 7 assays", "selected_by_window": "Invented single window: 2 selected pairs", "endpoint_evaluable_counts": "unavailable before release", "endpoint_status": "unavailable before release", "derived_unpaired_baseline_patients": 2, "derived_field_definition": "patients_with_baseline - patients_paired; single-window invented example"},
]
_GATES = [
    {"gate": "Gate A", "status": "OPEN (invented shell row)", "blocker": "decision placeholder", "future_command": "NOT SUPPLIED"},
    {"gate": "Gate B", "status": "UNAVAILABLE (invented shell row)", "blocker": "evidence placeholder", "future_command": "NOT SUPPLIED"},
]


def _fixture_hash() -> str:
    fixture = {
        "cohorts": _COHORTS, "panel_effects": _PANEL_EFFECTS, "gene_meta": _GENE_META,
        "hallmark": _HALLMARK, "roc": _ROC, "paired_delta": _PAIRED_DELTA,
        "sc1": {
            "studies": _SC1_STUDIES, "compartments": _SC1_COMPARTMENTS,
            "panels": _SC1_PANEL_ROWS, "cells": _SC1_COMPOSITE_CELLS,
        },
        "sc3": {
            "cohorts": _SC3_COHORTS,
            "panel_compartments": _SC3_PANEL_COMPARTMENTS,
            "metric_families": _SC3_METRIC_FAMILIES,
        },
        "along_effects": _ALONG_EFFECTS,
        "ancova": _ANCOVA, "pair_rows": _PAIR_ROWS, "gates": _GATES,
        "along_timing": _ALONG_TIMING_EXAMPLES,
        "along_source_coverage": _ALONG_SOURCE_COVERAGE,
        "along_within_group_deltas": _ALONG_WITHIN_GROUP_DELTAS,
        "along_programme_rows": _ALONG_PROGRAMME_ROWS,
        "along_sensitivity_rows": _ALONG_SENSITIVITY_ROWS,
    }
    encoded = json.dumps(fixture, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _save_figure(fig, figures_dir: Path, stem: str, title: str,
                 *, use_tight_layout: bool = True) -> list[str]:
    if use_tight_layout:
        fig.tight_layout(rect=(0.0, 0.10, 1.0, 0.92))
    fig.text(0.5, 0.025, LABEL, ha="center", va="bottom", color="#9c2f2f",
             fontsize=9, fontweight="bold")
    svg = figures_dir / (stem + ".svg")
    pdf = figures_dir / (stem + ".pdf")
    provenance = (
        "invented fixture " + FIXTURE_ID + "; fixture_sha256=" + _fixture_hash()
        + "; code=" + CODE_VERSION + "; no external inputs or biological validation"
    )
    svg_meta = {"Title": LABEL + " | " + title, "Creator": CODE_VERSION,
                "Description": provenance}
    pdf_meta = {"Title": LABEL + " | " + title, "Creator": CODE_VERSION,
                "Subject": provenance,
                "CreationDate": None, "ModDate": None}
    fig.savefig(svg, format="svg", bbox_inches="tight", metadata=svg_meta)
    fig.savefig(pdf, format="pdf", bbox_inches="tight", metadata=pdf_meta)
    plt.close(fig)
    return [svg.relative_to(figures_dir.parent).as_posix(),
            pdf.relative_to(figures_dir.parent).as_posix()]


def _figure_01(figures_dir: Path) -> list[str]:
    fig, (bars, table_ax) = plt.subplots(
        2, 1, figsize=(10, 6.2), gridspec_kw={"height_ratios": [2, 1.2]},
    )
    bars.bar([row["cohort"] for row in _COHORTS], [row["n"] for row in _COHORTS],
             color=["#4472C4", "#70AD47", "#ED7D31", "#A5A5A5"])
    bars.set_ylabel("Invented sample count")
    bars.set_title("Cohort overview — invented metadata only")
    bars.set_ylim(0, 50)
    for row in _COHORTS:
        bars.text(row["cohort"], row["n"] + 1, str(row["n"]), ha="center", fontsize=9)
    table_ax.axis("off")
    table_ax.table(
        cellText=[[r["cohort"], r["cancer"], r["drug"], r["platform"]]
                  for r in _COHORTS],
        colLabels=["Study", "Cancer", "Drug class", "Platform"],
        loc="center", cellLoc="center",
    ).auto_set_font_size(False)
    table_ax.tables[0].set_fontsize(8)
    table_ax.set_title("No real cohort identities or counts", fontsize=9)
    return _save_figure(fig, figures_dir, FIGURE_NAMES[0], "Cohort overview")


def _figure_02(figures_dir: Path) -> list[str]:
    fig, ax = plt.subplots(figsize=(10, 5.8))
    positions = list(range(len(_PANEL_EFFECTS)))
    colors = ["#4472C4", "#4472C4", "#70AD47", "#ED7D31", "#A5A5A5"]
    for y, row, color in zip(positions, _PANEL_EFFECTS, colors):
        if row["estimate"] is None:
            ax.scatter([0], [y], marker="x", color=color, s=55)
            ax.text(0.06, y, "unavailable", va="center", fontsize=8)
            continue
        ax.errorbar(
            row["estimate"], y,
            xerr=[[row["estimate"] - row["lower"]], [row["upper"] - row["estimate"]]],
            fmt="o", color=color, capsize=3,
        )
        ax.text(0.96, y, "n=" + str(row["n"]), va="center", fontsize=8)
    ax.axvline(0, color="#666666", linewidth=1)
    ax.set_yticks(positions, [row["label"] for row in _PANEL_EFFECTS])
    ax.invert_yaxis()
    ax.set_xlabel("Invented Hedges g with supplied illustrative interval")
    ax.set_title("Panel forests by invented cancer and drug group")
    ax.set_xlim(-1.0, 1.2)
    return _save_figure(fig, figures_dir, FIGURE_NAMES[1], "Panel forests")


def _figure_03(figures_dir: Path) -> list[str]:
    fig, (volcano, heatmap) = plt.subplots(1, 2, figsize=(11, 5.3))
    for row in _GENE_META:
        if row["pooled_g"] is None:
            volcano.scatter([0], [0], marker="x", color="#888888")
            volcano.text(0.04, 0.10, row["gene"] + ": unavailable", fontsize=8)
            continue
        color = "#C0504D" if row["fdr"] is not None and row["fdr"] < 0.05 else "#4472C4"
        volcano.scatter(row["pooled_g"], row["neg_log10_fdr"], color=color, s=35)
        volcano.annotate(row["gene"], (row["pooled_g"], row["neg_log10_fdr"]), fontsize=8)
    volcano.axvline(0, color="#777777", linewidth=0.8)
    volcano.set_xlabel("Pooled g (invented)")
    volcano.set_ylabel("Supplied −log10(FDR) display value")
    volcano.set_title("Pooled-g / FDR illustration")
    heat = [[row[key] if row[key] is not None else float("nan")
             for key in ("study_a", "study_b", "study_c")] for row in _GENE_META]
    image = heatmap.imshow(heat, aspect="auto", cmap="coolwarm", vmin=-1, vmax=1)
    heatmap.set_yticks(range(len(_GENE_META)), [row["gene"] for row in _GENE_META])
    heatmap.set_xticks(range(3), ["Invented study A", "Invented study B", "Invented study C"])
    heatmap.tick_params(axis="x", rotation=25)
    heatmap.set_title("Study-level g; blanks remain unavailable")
    fig.colorbar(image, ax=heatmap, label="Invented study g")
    return _save_figure(fig, figures_dir, FIGURE_NAMES[2], "Pooled gene meta and study effects")


def _figure_04(figures_dir: Path) -> list[str]:
    fig, (meta_ax, fgsea_ax) = plt.subplots(1, 2, figsize=(11, 5.3))
    for y, row in enumerate(_HALLMARK):
        if row["meta_g"] is None:
            meta_ax.scatter([0], [y], marker="x", color="#888888")
            meta_ax.text(0.04, y, "unavailable", va="center", fontsize=8)
        else:
            meta_ax.errorbar(
                row["meta_g"], y,
                xerr=[[row["meta_g"] - row["meta_lower"]],
                      [row["meta_upper"] - row["meta_g"]]],
                fmt="o", color="#4472C4", capsize=3,
            )
            meta_ax.text(0.95, y, "q=" + str(row["meta_q"]), va="center", fontsize=8)
        if row["fgsea_nes"] is None:
            fgsea_ax.scatter([0], [y], marker="x", color="#888888")
            fgsea_ax.text(0.05, y, "unavailable", va="center", fontsize=8)
        else:
            fgsea_ax.scatter(row["fgsea_nes"], y, color="#70AD47")
            fgsea_ax.text(2.05, y, "padj=" + str(row["fgsea_padj"]), va="center", fontsize=8)
    meta_ax.axvline(0, color="#777777", linewidth=0.8)
    fgsea_ax.axvline(0, color="#777777", linewidth=0.8)
    labels = [row["set"] for row in _HALLMARK]
    for axis in (meta_ax, fgsea_ax):
        axis.set_yticks(range(len(labels)), labels)
        axis.invert_yaxis()
    meta_ax.set_xlabel("Meta-analysis estimate g")
    meta_ax.set_title("Meta output family")
    fgsea_ax.set_xlabel("fgsea NES")
    fgsea_ax.set_title("fgsea output family")
    fig.suptitle("Hallmark layout — separate supplied metrics; no pathway run")
    return _save_figure(fig, figures_dir, FIGURE_NAMES[3], "Hallmark meta and fgsea summary")


def _figure_05(figures_dir: Path) -> list[str]:
    fig, (roc_ax, delta_ax) = plt.subplots(1, 2, figsize=(11, 5.3))
    for label, row in _ROC.items():
        roc_ax.plot(row["x"], row["y"], marker="o",
                    label=label + " · AUROC=" + str(row["auroc"]))
    roc_ax.plot([0, 1], [0, 1], linestyle="--", color="#888888", linewidth=0.8)
    roc_ax.set(xlim=(0, 1), ylim=(0, 1), xlabel="False positive rate",
               ylabel="True positive rate", title="A-P2 ROC shell")
    roc_ax.legend(fontsize=8, loc="lower right")
    for y, row in enumerate(_PAIRED_DELTA):
        if row["lower"] is None or row["upper"] is None:
            delta_ax.plot(row["delta"], y, "o", color="#4472C4")
        else:
            delta_ax.errorbar(
                row["delta"], y,
                xerr=[[row["delta"] - row["lower"]], [row["upper"] - row["delta"]]],
                fmt="o", color="#4472C4", capsize=3,
            )
        delta_ax.text(0.24, y, row["status"], va="center", fontsize=8)
    delta_ax.axvline(0, color="#777777", linewidth=0.8)
    delta_ax.set_yticks(range(len(_PAIRED_DELTA)), [row["split"] for row in _PAIRED_DELTA])
    delta_ax.invert_yaxis()
    delta_ax.set_xlim(-0.2, 0.68)
    delta_ax.set_xlabel("Paired ΔAUROC (invented display value)")
    delta_ax.set_title("Paired comparison shell")
    fig.suptitle("A-P2 is primary; development and final-test examples are distinct")
    fig.text(0.5, 0.055, "M2 and CYT overlap; they are not independent signals.",
             ha="center", fontsize=9, color="#7A1F1F")
    return _save_figure(fig, figures_dir, FIGURE_NAMES[4], "A-P2 ROC and paired delta AUROC")


def _figure_06(figures_dir: Path) -> list[str]:
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize
    from matplotlib.lines import Line2D

    fig, axes = plt.subplots(1, len(_SC1_STUDIES), figsize=(18.0, 6.4), sharey=True)
    color_map = plt.get_cmap("viridis")
    for axis, study in zip(axes, _SC1_STUDIES):
        study_cells = [row for row in _SC1_COMPOSITE_CELLS if row["study"] == study]
        assessed_values = [
            float(row["median_log2_cpm_plus1"])
            for row in study_cells
            if row["status"] == "shown" and row["median_log2_cpm_plus1"] is not None
        ]
        if any(value < 0 for value in assessed_values):
            raise ValueError("invented SC-1 display values must be nonnegative")
        vmax = max(assessed_values, default=0.0)
        fallback_scale = vmax == 0.0
        if fallback_scale:
            vmax = 1.0
        norm = Normalize(vmin=0.0, vmax=vmax)
        for row in study_cells:
            x = _SC1_COMPARTMENTS.index(row["compartment"])
            y = _SC1_PANEL_ROWS.index(row["gene_group"])
            if row["status"] == "not_assessed":
                axis.scatter(x, y, marker="o", s=90, facecolors="none",
                             edgecolors="#555555", linewidth=1.2)
                continue
            if row["status"] == "insufficient_donors":
                axis.scatter(x, y, marker="^", s=90, color="#777777")
                continue
            value = row["median_log2_cpm_plus1"]
            if row["status"] != "shown" or value is None:
                axis.scatter(x, y, marker="x", s=90, color="#777777")
                continue
            axis.scatter(x, y, c=[value], cmap=color_map, norm=norm, s=90,
                         edgecolor="black", linewidth=0.4)
            axis.text(x, y + 0.16, f"{value:.2f}", ha="center", va="bottom",
                      fontsize=8, color="black")
        axis.set_xticks(range(len(_SC1_COMPARTMENTS)), _SC1_COMPARTMENTS)
        axis.set_yticks(range(len(_SC1_PANEL_ROWS)), _SC1_PANEL_ROWS)
        axis.set_xlim(-0.55, 1.55)
        axis.set_ylim(-0.55, 1.55)
        scale_title = f"Study-specific scale 0–{vmax:.2f}"
        if fallback_scale:
            scale_title += " · all zero/unavailable fallback"
        axis.set_title(study + "\n" + scale_title, fontsize=8.5)
        axis.set_xlabel("Invented compartment")
        colorbar = fig.colorbar(
            ScalarMappable(norm=norm, cmap=color_map), ax=axis, pad=0.05, fraction=0.06,
        )
        colorbar.set_label("Median donor log2(CPM+1)", fontsize=8)
        colorbar.ax.tick_params(labelsize=8)
    axes[0].set_ylabel("Invented custom panel")
    legend = [
        Line2D([], [], marker="o", linestyle="none", markersize=7,
               markerfacecolor="#aaaaaa", markeredgecolor="#444444", label="assessed; value shown"),
        Line2D([], [], marker="o", linestyle="none", markersize=7,
               markerfacecolor="none", markeredgecolor="#555555", label="not assessed"),
        Line2D([], [], marker="^", linestyle="none", markersize=7,
               markerfacecolor="#777777", markeredgecolor="#555555", label="insufficient donors"),
    ]
    fig.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, 0.105),
               ncol=3, fontsize=8, frameon=False)
    fig.suptitle("SC-1 per-study donor medians — invented custom panels only", y=0.98)
    fig.text(0.5, 0.065,
             "Fixed-size composite dots; zero is assessed (0.00), unlike NA/not assessed or insufficient donors. "
             "Study scales are separate; no cross-study pooling or z-scoring; all-zero/unavailable uses 0–1. "
             "M5/M6 genes are not plotted.",
             ha="center", fontsize=7.5)
    fig.subplots_adjust(left=0.08, right=0.97, bottom=0.24, top=0.78, wspace=0.78)
    return _save_figure(
        fig, figures_dir, FIGURE_NAMES[5], "SC-1 composite panel donor medians",
        use_tight_layout=False,
    )


def _figure_07(figures_dir: Path) -> list[str]:
    from matplotlib.patches import Rectangle

    fig, axes = plt.subplots(1, 3, figsize=(16.2, 7.2), sharey=True,
                             gridspec_kw={"width_ratios": [1.0, 1.0, 1.2]})
    image = None
    for axis, metric in zip(axes, _SC3_METRIC_FAMILIES):
        values = metric["values"]
        image_values = [
            [float("nan") if value is None else value for value in row]
            for row in values
        ]
        image = axis.imshow(image_values, aspect="auto", cmap="coolwarm", vmin=-0.8, vmax=0.8)
        for y, row in enumerate(values):
            for x, value in enumerate(row):
                if value is None:
                    axis.add_patch(Rectangle((x - 0.5, y - 0.5), 1, 1,
                                             facecolor="#eeeeee", edgecolor="#777777",
                                             hatch="///", linewidth=0.7))
                    axis.text(x, y, "NA", ha="center", va="center",
                              fontsize=8, fontweight="bold", color="#444444")
                else:
                    axis.text(x, y, f"{value:.2f}", ha="center", va="center",
                              fontsize=7.5, color="white" if abs(value) > 0.5 else "black")
        axis.set_xticks(range(len(_SC3_COHORTS)), _SC3_COHORTS,
                        rotation=25, ha="right", fontsize=8)
        axis.set_yticks(range(len(_SC3_PANEL_COMPARTMENTS)), _SC3_PANEL_COMPARTMENTS,
                        fontsize=8)
        axis.set_xlabel("Invented cohort")
        axis.set_title(metric["label"], fontsize=9, pad=10)
    axes[0].set_ylabel("Panel family × compartment")
    fig.subplots_adjust(left=0.16, right=0.86, bottom=0.22, top=0.84, wspace=0.44)
    fig.colorbar(image, ax=axes, pad=0.04, fraction=0.035,
                 label="Invented Hedges g (fixed symmetric scale −0.8 to +0.8)")
    fig.suptitle("SC-3 exploratory heatmaps — panel Hedges g by cohort × compartment",
                 y=0.98)
    fig.text(0.5, 0.07,
             "RECIST, pathology, and T-cell expansion remain separate. T-cell expansion is a nonclinical metric, not clinical response.",
             ha="center", fontsize=8)
    return _save_figure(
        fig, figures_dir, FIGURE_NAMES[6], "SC-3 exploratory panel Hedges g heatmaps",
        use_tight_layout=False,
    )


def _figure_08(figures_dir: Path) -> list[str]:
    fig = plt.figure(figsize=(16, 9))
    grid = fig.add_gridspec(
        2, 2, width_ratios=[1.45, 1], height_ratios=[1.0, 0.9],
        left=0.055, right=0.98, top=0.89, bottom=0.16, wspace=0.32, hspace=0.42,
    )
    pairs_ax = fig.add_subplot(grid[0, 0])
    timing_ax = fig.add_subplot(grid[1, 0])
    direct_ax = fig.add_subplot(grid[0, 1])
    ancova_ax = fig.add_subplot(grid[1, 1], sharex=direct_ax)
    pairs_ax.axis("off")
    pair_table = pairs_ax.table(
        cellText=[
            [row["study_id"], str(row["specimens_in"]), str(row["assays_in"]),
             str(row["patients_in"]),
             f'{row["patients_with_baseline"]}/{row["patients_with_followup"]}/{row["patients_paired"]}',
             f'{row["candidate_pairs"]}→{row["selected_pairs"]}',
             str(row["same_lesion_pairs"])]
            for row in _PAIR_ROWS
        ],
        colLabels=["Invented study", "specimens", "assays", "patients_in",
                   "baseline/follow-up/paired\npatients", "candidate→selected\npairs",
                   "same-lesion\npairs"],
        colWidths=[0.14, 0.10, 0.10, 0.11, 0.23, 0.18, 0.14],
        loc="center", cellLoc="center",
    )
    pair_table.auto_set_font_size(False)
    pair_table.set_fontsize(6.8)
    pair_table.scale(1, 1.85)
    pairs_ax.set_title("Panel 1B · pairing_summary.tsv structure and selection", pad=12)
    pairs_ax.text(
        0.5, 0.04,
        "Invented counts only. patients_paired counts unique patients; selected_pairs counts pairs. Endpoint-evaluable counts: unavailable.",
        ha="center", va="center", fontsize=7.1, wrap=True,
        transform=pairs_ax.transAxes,
    )

    timing_ax.set_xlim(-3, 46)
    timing_ax.set_ylim(-0.55, 1.55)
    timing_ax.set_yticks([1, 0], ["Exact-day example", "Categorical/interval example"])
    timing_ax.axvline(_ALONG_TIMING_EXAMPLES["pre_day"], color="#777777", linewidth=1)
    timing_ax.scatter([_ALONG_TIMING_EXAMPLES["pre_day"], _ALONG_TIMING_EXAMPLES["exact_on_day"]],
                      [1, 1], color=["#777777", "#4472C4"], zorder=3)
    timing_ax.plot(
        [_ALONG_TIMING_EXAMPLES["interval_on_start"], _ALONG_TIMING_EXAMPLES["interval_on_end"]],
        [0, 0], color="#70AD47", linewidth=8, solid_capstyle="butt",
    )
    timing_ax.scatter([_ALONG_TIMING_EXAMPLES["pre_day"]], [0], color="#777777", zorder=3)
    timing_ax.text(-1.5, 1.18, "PRE · day 0", ha="right", fontsize=7.5)
    timing_ax.text(29, 1.18, "ON · exact day +28", ha="left", fontsize=7.5)
    timing_ax.text(31.5, 0.18, "ON · interval +21 to +42", ha="center", fontsize=7.5)
    timing_ax.set_xlabel("Invented days from PRE; no real timing rule selected", fontsize=8)
    timing_ax.set_title("Timing and selection examples · aggregate layout only", fontsize=9)
    timing_ax.grid(axis="x", color="#dddddd", linewidth=0.6)

    for y, row in enumerate(_ALONG_EFFECTS):
        if row["estimate"] is None:
            display_y = direct_ax.get_yaxis_transform()
            direct_ax.text(
                0.5, y, f"NOT_ESTIMABLE · {row['reason']}", va="center",
                ha="center", fontsize=7.2, color="#666666", wrap=True,
                clip_on=True, transform=display_y,
            )
            continue
        direct_ax.errorbar(
            row["estimate"], y,
            xerr=[[row["estimate"] - row["ci_lb"]],
                  [row["ci_ub"] - row["estimate"]]],
            fmt="o", color="#4472C4", capsize=3,
        )
    direct_ax.axvline(0, color="#777777", linewidth=0.8)
    direct_ax.set_yticks(range(len(_ALONG_EFFECTS)), [row["study"] for row in _ALONG_EFFECTS])
    direct_ax.invert_yaxis()
    direct_ax.set_xlim(-0.5, 0.65)
    direct_ax.set_ylim(2.55, -0.55)
    direct_ax.set_xlabel("Invented native effect scale")
    direct_ax.set_title(
        "Panel 2B · central R_minus_NR_change\nR minus NR in (ON−PRE); patient unit",
        fontsize=8,
    )
    ancova_ax.errorbar(
        _ANCOVA["estimate"], 0,
        xerr=[[_ANCOVA["estimate"] - _ANCOVA["ci_lb"]],
              [_ANCOVA["ci_ub"] - _ANCOVA["estimate"]]],
        fmt="s", color="#888888", capsize=3,
    )
    ancova_ax.axvline(0, color="#777777", linewidth=0.8)
    ancova_ax.set_yticks([0], ["Sensitivity"])
    ancova_ax.set_xlim(-0.5, 0.65)
    ancova_ax.set_xlabel("Same invented native effect scale")
    ancova_ax.set_title(
        "ANCOVA sensitivity · R_minus_NR_on_value_conditional_on_pre\n"
        "conditional on baseline association · NOT central Delta",
        fontsize=8,
    )
    fig.suptitle("A-LONG Figure 8 · pairing/selection structure and direct response-by-time estimates", y=0.97)
    fig.text(
        0.5, 0.085,
        "Fixed invented aggregates and intervals; no patient rows. Real source/release: not admitted; real unique-patient N: UNKNOWN; real specimen/assay N: UNKNOWN separately.",
        ha="center", fontsize=8,
    )
    fig.text(
        0.5, 0.055,
        "Experimental unit: patient. Method: delta_primary; ANCOVA is separate, not central Delta. Claim limit: invented layout only, no findings; timing is not an N12 choice.",
        ha="center", fontsize=7.5,
    )
    return _save_figure(
        fig, figures_dir, FIGURE_NAMES[7],
        "Pair structure and direct response-by-time effects", use_tight_layout=False,
    )


def _figure_s1(figures_dir: Path) -> list[str]:
    fig, axes = plt.subplots(2, 3, figsize=(12, 7))
    for row_index, cohort in enumerate(("Invented study A", "Invented study B")):
        qc_ax, pca_ax, de_ax = axes[row_index]
        qc_values = [8.1, 8.4, 8.7, 9.0, 9.3] if row_index == 0 else [7.9, 8.3, 8.5, 8.8, 9.1]
        qc_ax.boxplot(qc_values, tick_labels=["invented samples"])
        qc_ax.set_title(cohort + " · QC")
        qc_ax.set_ylabel("Invented library-size scale")
        px = [-1.2, -0.6, 0.2, 0.8, 1.3]
        py = [0.9, -0.8, 0.3, -0.3, 0.7] if row_index == 0 else [-0.7, 0.6, -0.2, 0.8, -0.4]
        pca_ax.scatter(px, py, color="#4472C4")
        pca_ax.set_title(cohort + " · PCA")
        pca_ax.set_xlabel("PC1 (invented)")
        pca_ax.set_ylabel("PC2 (invented)")
        de_ax.scatter([-0.5, -0.1, 0.2, 0.6], [0.2, 1.3, 0.6, 1.8],
                      color=["#4472C4", "#70AD47", "#4472C4", "#A5A5A5"])
        de_ax.set_title(cohort + " · DE layout")
        de_ax.set_xlabel("Invented effect")
        de_ax.set_ylabel("Supplied display scale")
    fig.suptitle("Per-dataset QC / PCA / DE grids — invented data only")
    return _save_figure(fig, figures_dir, FIGURE_NAMES[8], "Per-dataset QC PCA DE grids")


def _placeholder_page(figures_dir: Path, stem: str, title: str, status: str,
                      rows: list[list[str]], *,
                      col_labels: tuple[str, str, str] = (
                          "Shell field", "Example display", "Availability",
                      ),
                      col_widths: tuple[float, float, float] | None = None,
                      figsize: tuple[float, float] = (9, 5.5),
                      table_fontsize: float = 9) -> list[str]:
    fig, ax = plt.subplots(figsize=figsize)
    ax.axis("off")
    ax.text(0.5, 0.92, title, ha="center", va="center", fontsize=14, fontweight="bold")
    ax.text(0.5, 0.78, status, ha="center", va="center", fontsize=11,
            color="#8A2D2D", fontweight="bold", wrap=True)
    table = ax.table(
        cellText=rows,
        colLabels=col_labels,
        colWidths=col_widths,
        loc="center", cellLoc="left",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(table_fontsize)
    table.scale(1, 1.35 if table_fontsize < 9 else 1.5)
    ax.text(0.5, 0.12, "No real measurements, pair identities, model outputs, or gate evidence.",
            ha="center", va="center", fontsize=9)
    return _save_figure(fig, figures_dir, stem, title)


def _figure_s2(figures_dir: Path) -> list[str]:
    fig, (fraction_ax, note_ax) = plt.subplots(1, 2, figsize=(10, 5))
    cells = ["Cell type A", "Cell type B", "Cell type C", "Cell type D"]
    values = [0.31, 0.25, 0.28, 0.16]
    fraction_ax.bar(cells, values, color=["#4472C4", "#70AD47", "#ED7D31", "#A5A5A5"])
    fraction_ax.set_ylim(0, 0.5)
    fraction_ax.set_ylabel("Invented fraction")
    fraction_ax.set_title("Illustrative composition layout")
    note_ax.axis("off")
    note_ax.text(0.05, 0.8, "A-COMP shell only", fontsize=13, fontweight="bold")
    note_ax.text(0.05, 0.60, "N15 is unsigned; no real deconvolution is shown.", wrap=True)
    note_ax.text(0.05, 0.42, "CIBERSORTx: not run.", wrap=True)
    note_ax.text(0.05, 0.22, "These invented fractions do not evidence a gate pass.", wrap=True)
    fig.suptitle("Supplement A-COMP")
    return _save_figure(fig, figures_dir, FIGURE_NAMES[9], "A-COMP shell")


def _figure_s3_long_source_coverage(figures_dir: Path) -> list[str]:
    fig = plt.figure(figsize=(14, 8))
    flow_ax = fig.add_axes([0.055, 0.57, 0.89, 0.30])
    flow_ax.set_xlim(0, 1)
    flow_ax.set_ylim(0, 1)
    flow_ax.axis("off")
    flow_ax.text(
        0.02, 0.55, "Invented source\ncatalogue\n3 entries",
        ha="center", va="center", fontsize=10,
        bbox={"boxstyle": "round,pad=0.5", "facecolor": "#F2F2F2", "edgecolor": "#777777"},
    )
    flow_ax.text(
        0.40, 0.76, "Invented family A\n2 catalogue entries",
        ha="center", va="center", fontsize=9,
        bbox={"boxstyle": "round,pad=0.5", "facecolor": "#DCE6F1", "edgecolor": "#4472C4"},
    )
    flow_ax.text(
        0.40, 0.28, "Invented family B\n1 catalogue entry",
        ha="center", va="center", fontsize=9,
        bbox={"boxstyle": "round,pad=0.5", "facecolor": "#E2F0D9", "edgecolor": "#70AD47"},
    )
    for target_y in (0.76, 0.28):
        flow_ax.annotate("", xy=(0.30, target_y), xytext=(0.15, 0.55),
                         arrowprops={"arrowstyle": "->", "color": "#777777"})
    flow_ax.text(
        0.80, 0.76, "regimen_id × window_id\nInvented regimen/window A",
        ha="center", va="center", fontsize=9,
        bbox={"boxstyle": "round,pad=0.5", "facecolor": "#FCE4D6", "edgecolor": "#ED7D31"},
    )
    flow_ax.text(
        0.80, 0.28, "regimen_id × window_id\nInvented regimen/window B",
        ha="center", va="center", fontsize=9,
        bbox={"boxstyle": "round,pad=0.5", "facecolor": "#FFF2CC", "edgecolor": "#BF9000"},
    )
    for y in (0.76, 0.28):
        flow_ax.annotate("", xy=(0.67, y), xytext=(0.53, y),
                         arrowprops={"arrowstyle": "->", "color": "#777777"})
    flow_ax.set_title("A-LONG1A · source flow into family and regimen/window coverage", fontsize=11)

    table_ax = fig.add_axes([0.045, 0.20, 0.91, 0.29])
    table_ax.axis("off")
    table_rows = [
        [row["family"], str(row["catalogue_entries"]),
         f'{row["regimen_id"]} / {row["window_id"]}',
         str(row["selected_pairs"]), "UNKNOWN", "UNKNOWN"]
        for row in _ALONG_SOURCE_COVERAGE
    ]
    table = table_ax.table(
        cellText=table_rows,
        colLabels=["Invented family", "Catalogue entries\n(invented)",
                   "Regimen / window coverage\n(invented)", "selected_pairs\n(invented)",
                   "Real patient N", "Real specimen / assay N"],
        colWidths=[0.18, 0.14, 0.25, 0.14, 0.13, 0.16],
        loc="center", cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(7.6)
    table.scale(1, 1.7)
    fig.suptitle("A-LONG1A · which longitudinal source families and time windows are represented?", y=0.96)
    fig.text(
        0.5, 0.105,
        "Invented layout only; no real source, release, or overlap receipt is admitted. Catalogue entries are not independent cohort counts.",
        ha="center", fontsize=8,
    )
    fig.text(
        0.5, 0.075,
        "Source-flow unit: independent study family. Real patient N: UNKNOWN; real specimen/assay N: UNKNOWN separately. Method: source-family/overlap coverage mapping only; no estimate or interval.",
        ha="center", fontsize=8,
    )
    return _save_figure(
        fig, figures_dir, FIGURE_NAMES[10], "A-LONG1A source and regimen/window coverage",
        use_tight_layout=False,
    )


def _figure_s4_long_within_group_deltas(figures_dir: Path) -> list[str]:
    fig, (effect_ax, note_ax) = plt.subplots(
        1, 2, figsize=(14, 7.5), gridspec_kw={"width_ratios": [1.45, 1]},
    )
    labels = [
        "DELTA_R · response=R · n=8 invented",
        "DELTA_NR · response=NR · n=7 invented",
        "DELTA_NR · support unavailable",
    ]
    for y, row in enumerate(_ALONG_WITHIN_GROUP_DELTAS):
        if row["estimate"] is None:
            effect_ax.text(
                0.5, y, "NOT_ESTIMABLE · invented support unavailable",
                ha="center", va="center", color="#666666", fontsize=8,
                transform=effect_ax.get_yaxis_transform(), clip_on=True,
            )
            continue
        effect_ax.errorbar(
            row["estimate"], y,
            xerr=[[row["estimate"] - row["ci_lb"]], [row["ci_ub"] - row["estimate"]]],
            fmt="o", color="#4472C4" if row["response"] == "R" else "#70AD47",
            capsize=3,
        )
    effect_ax.axvline(0, color="#777777", linewidth=0.8)
    effect_ax.set_yticks(range(len(labels)), labels)
    effect_ax.invert_yaxis()
    effect_ax.set_xlim(-0.45, 0.65)
    effect_ax.set_xlabel("Invented within-group baseline-to-ON change; native scale")
    effect_ax.set_title("within_group_deltas.tsv · window=baseline_to_on")

    note_ax.axis("off")
    note = (
        "A-LONG2A · change within each response group\n\n"
        "Experimental unit: patient. Product: within_group_deltas.tsv; response R and NR rows are separate DELTA_R / DELTA_NR summaries.\n\n"
        "Method display: two-timepoint baseline_to_on. All counts, estimates, and intervals are fixed invented values; no method was run here.\n\n"
        "Real source/release: not admitted. Real unique-patient N: UNKNOWN. Real specimen/assay N: UNKNOWN separately.\n\n"
        "Claim limit: a within-group change or significance in one group is not evidence of a response-by-time interaction."
    )
    note_ax.text(0.02, 0.96, note, va="top", fontsize=9, wrap=True, linespacing=1.35)
    fig.suptitle("A-LONG2A · what changes within each response group?", y=0.97)
    fig.text(0.5, 0.075, "Uncertainty intervals are invented layout values; NOT_ESTIMABLE retains a missing estimate and reason.",
             ha="center", fontsize=8)
    effect_ax.set_ylim(2.55, -0.55)
    fig.subplots_adjust(left=0.22, right=0.97, bottom=0.25, top=0.86, wspace=0.38)
    return _save_figure(
        fig, figures_dir, FIGURE_NAMES[11], "A-LONG2A within-group delta estimates",
        use_tight_layout=False,
    )


def _figure_s5_long_programme_directions(figures_dir: Path) -> list[str]:
    fig, (forest_ax, note_ax) = plt.subplots(
        1, 2, figsize=(15, 8), gridspec_kw={"width_ratios": [1.7, 1]},
    )
    rows = _ALONG_PROGRAMME_ROWS
    labels = [
        f'{row["programme"]} · {row["source_family_id"]} · {row["cancer"]} '
        f'(invented n_R/n_NR={row["n_R"]}/{row["n_NR"]})'
        for row in rows
    ]
    for y, row in enumerate(rows):
        forest_ax.errorbar(
            row["estimate"], y,
            xerr=[[row["estimate"] - row["ci_lb"]], [row["ci_ub"] - row["estimate"]]],
            fmt="o", color="#4472C4" if row["programme"].endswith("A") else "#ED7D31",
            capsize=3,
        )
    forest_ax.axvline(0, color="#777777", linewidth=0.8)
    forest_ax.axhline(2.5, color="#bbbbbb", linewidth=0.8)
    forest_ax.set_yticks(range(len(labels)), labels)
    forest_ax.invert_yaxis()
    forest_ax.tick_params(axis="y", labelsize=7.5)
    forest_ax.set_xlim(-0.55, 0.65)
    forest_ax.set_xlabel("Invented programme effect with invented interval; one fixture scale")
    forest_ax.set_title("All invented family/cancer rows · direction and support")

    note_ax.axis("off")
    note = (
        "A-LONG2C · programme-direction support\n\n"
        "Comparison unit: independent study family across cancers. Within-study effects use patient units; n_R/n_NR support values and family/cancer labels are invented. Method/effect-scale identity remains in the product fields; this shell does not select or run them.\n\n"
        "Real source/release: not admitted. Real independent-family count: UNKNOWN. Real unique-patient N: UNKNOWN; specimen/assay N is separate and UNKNOWN.\n\n"
        "Uncertainty: invented intervals are shown for each family row. Compatible synthesis identity/support fields are in a_long_synthesis.tsv; no pooled value is displayed here.\n\n"
        "Influence availability: UNAVAILABLE; no influence output was supplied.\n\n"
        "Claim limit: these rows do not establish replication. Catalogue entries and shared baselines are not counted as independent evidence."
    )
    note_ax.text(0.02, 0.97, note, va="top", fontsize=8.7, wrap=True, linespacing=1.3)
    fig.suptitle("A-LONG2C · which programme directions replicate?", y=0.97)
    fig.text(0.5, 0.07, "No biological direction, replication, or independence claim follows from invented display values.",
             ha="center", fontsize=8)
    fig.subplots_adjust(left=0.33, right=0.98, bottom=0.24, top=0.87, wspace=0.45)
    return _save_figure(
        fig, figures_dir, FIGURE_NAMES[12], "A-LONG2C programme direction support",
        use_tight_layout=False,
    )


def _figure_s6_long_sensitivity(figures_dir: Path) -> list[str]:
    fig, (forest_ax, note_ax) = plt.subplots(
        1, 2, figsize=(14, 7.5), gridspec_kw={"width_ratios": [1.5, 1]},
    )
    labels = [
        f'{row["model_label"]} · n_patients_used={row["n_patients_used"]} ({row["support_relation"]})'
        for row in _ALONG_SENSITIVITY_ROWS
    ]
    for y, row in enumerate(_ALONG_SENSITIVITY_ROWS):
        forest_ax.errorbar(
            row["estimate"], y,
            xerr=[[row["estimate"] - row["ci_lb"]], [row["ci_ub"] - row["estimate"]]],
            fmt="o" if y == 0 else "s", color="#4472C4" if y == 0 else "#888888",
            capsize=3,
        )
    forest_ax.axvline(0, color="#777777", linewidth=0.8)
    forest_ax.set_yticks(range(len(labels)), labels)
    forest_ax.invert_yaxis()
    forest_ax.tick_params(axis="y", labelsize=7.6)
    forest_ax.set_xlim(-0.5, 0.7)
    forest_ax.set_xlabel("Invented native effect scale · intervals are display values")
    forest_ax.set_title("Primary and prespecified sensitivity model rows")

    note_ax.axis("off")
    note = (
        "A-LONG3C · lesion, timing, and selection sensitivity\n\n"
        "Experimental unit: patient. `n_patients_used` is shown separately from specimen/assay counts. All support, estimates, and intervals are invented.\n\n"
        "Prespecified model rows: primary, same-lesion, exact-day, and tighter-timing. No additional route is introduced.\n\n"
        "Real source/release: not admitted. Real unique-patient N: UNKNOWN; real specimen/assay N: UNKNOWN.\n\n"
        "Selection, missing-biopsy, and influence results: UNAVAILABLE. Missing biopsies are not assumed random.\n\n"
        "Claim limit: no real sensitivity estimate or robustness conclusion is shown."
    )
    note_ax.text(0.02, 0.97, note, va="top", fontsize=8.6, wrap=True, linespacing=1.3)
    fig.suptitle("A-LONG3C · matched primary and lesion/timing sensitivity examples", y=0.97)
    fig.text(0.5, 0.07, "Same versus changed support is labeled per invented row; values are not analysis results.",
             ha="center", fontsize=8)
    fig.subplots_adjust(left=0.28, right=0.98, bottom=0.24, top=0.87, wspace=0.42)
    return _save_figure(
        fig, figures_dir, FIGURE_NAMES[13], "A-LONG3C sensitivity estimates",
        use_tight_layout=False,
    )


def _figure_s3_s6(figures_dir: Path, index: int) -> list[str]:
    renderers = (
        _figure_s3_long_source_coverage,
        _figure_s4_long_within_group_deltas,
        _figure_s5_long_programme_directions,
        _figure_s6_long_sensitivity,
    )
    return renderers[index](figures_dir)


def _figure_gated_along(figures_dir: Path, index: int) -> list[str]:
    components = (
        ("A-LONG3A", "Moderator-design identifiability", "Cancer / regimen / class / window design rank and confounding",
         "No moderator-design identifiability result or causal claim.",
         "Independent studies; paired-patient support",
         "Study N UNKNOWN; paired-patient N UNKNOWN; specimen/assay N UNKNOWN"),
        ("A-LONG3B", "Released moderator-effect heterogeneity", "Between-stratum effect heterogeneity after scoped release",
         "Not an efficacy ranking.",
         "Independent study families; released heterogeneity only",
         "Family N UNKNOWN; patient N UNKNOWN; specimen/assay N UNKNOWN"),
        ("A-LONG4A", "Orthogonal cellular/modality context", "Noncausal cellular and modality context",
         "No causal proof.",
         "Patient units; cells/spots are nested, not independent",
         "Patient N UNKNOWN; nested cell/spot N UNKNOWN; specimen/assay N UNKNOWN"),
        ("A-LONG4B", "NMA feasibility / qualified temporal handoff", "Network feasibility and qualified handoff",
         "Unsupported arrows are absent.",
         "Studies/programmes; feasibility and handoff only",
         "Study/programme N UNKNOWN; patient N UNKNOWN; specimen/assay N UNKNOWN"),
    )
    component, title, question, claim_limit, unit_method, support_counts = components[index]
    return _placeholder_page(
        figures_dir, FIGURE_NAMES[14 + index],
        component + " — " + title,
        "GATED — required release/design gate has not passed; no estimates shown.",
        [
            ["required question", question, "gated; unavailable"],
            ["source / release", "not admitted; real Ns UNKNOWN", "unavailable"],
            ["support counts", support_counts, "unavailable"],
            ["unit / method", unit_method, "not run"],
            ["estimate / uncertainty", "—", "no estimate or interval"],
            ["claim limit", claim_limit, "no inference"],
        ],
        col_widths=(0.18, 0.60, 0.22),
        figsize=(12, 7),
        table_fontsize=8,
    )


def _table_rows(rows: list[dict], fixture_sha256: str) -> list[dict]:
    metadata = {
        "data_classification": "invented",
        "classification": LABEL,
        "code_version": CODE_VERSION,
        "input_fixture_id": FIXTURE_ID,
        "input_fixture_sha256": fixture_sha256,
    }
    return [{**metadata, **row} for row in rows]


def _write_tsv(path: Path, rows: list[dict], fields: tuple[str, ...],
               fixture_sha256: str) -> None:
    all_fields = (
        "data_classification", "classification", "code_version",
        "input_fixture_id", "input_fixture_sha256", *fields,
    )
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=all_fields, delimiter="\t",
                                lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(_table_rows(rows, fixture_sha256))


def _write_tables(tables_dir: Path, fixture_sha256: str) -> list[str]:
    schemas = [
        {
            "shell_table": "Table_01_cohort_measurement_eligibility.tsv",
            "product": "cohort metadata",
            "source_schema": "tools/a_cohorts/view.py::CohortMetadata; MeasurementRepresentation",
            "mapped_fields": "cohort_id,cancer,uniform_drug_class,platform,unit,transform,feature_id,de_engine,endpoint_families",
            "mapping_status": "field map based on public code; eligibility not evaluated by this shell",
        },
        {
            "shell_table": "Table_02_coverage_provenance.tsv",
            "product": "A-BIO/A-META",
            "source_schema": "A_BIO COVERAGE_COLUMNS; tools/a_meta EFFECT_COLUMNS; manifests",
            "mapped_fields": "unit_family,unit,n_found,n_total,complete,scorable,missing,fixed_subset,reason,sensitivity_label; input/output hashes",
            "mapping_status": "field map based on public output schemas",
        },
        {
            "shell_table": "Table_03_full_effects_multiplicity.tsv",
            "product": "A-META",
            "source_schema": "tools/a_meta/effects.py::EFFECT_COLUMNS; tools/a_meta/synthesis.py::SYNTHESIS_COLUMNS and SUBGROUP_COLUMNS",
            "mapped_fields": ",".join(_EFFECT_COLUMNS) + "; " + ",".join(_SYNTHESIS_COLUMNS) + "; " + ",".join(_SUBGROUP_COLUMNS),
            "mapping_status": "full row families represented; no selection rule or inferential method added",
        },
        {
            "shell_table": "Table_04_a_p2_validation.tsv",
            "product": "A-P2",
            "source_schema": "tools/a_p2/product.py::_expected_outputs; r/R/a_p2.R::aggregate_leave_out,run_final,write_tsv",
            "mapped_fields": "primary_aggregates.tsv:analysis,metric,weighting,study_count,cancer_count,value,status,comparator_membership_caveat; final_metrics.tsv:analysis,evaluation_label,inference_status,status,n,responders,nonresponders,learner_auc,cyt_auc,delta_auc,lower_95,upper_95,second_check_flag,reason,comparator_membership_caveat; bootstrap_summary.tsv:stream,repetitions,confidence_level,lower_95,upper_95,conditional_on,comparator_membership_caveat; predictions.tsv:analysis,row_index,study,cancer,orr_class,learner_score,cyt_score,comparator_membership_caveat (private patient-level schema only)",
            "mapping_status": "metric columns mapped from stable W1 public code; values in this shell remain invented",
        },
        {
            "shell_table": "Table_05_a_long_pairing_attrition.tsv",
            "product": "A-LONG",
            "source_schema": "pairing_summary.tsv; pairing and model longitudinal_support.tsv; within_group_deltas.tsv; model_support.tsv; a_long_effects.tsv; a_long_synthesis.tsv; synthesis_support.tsv; private pair candidates/exclusions/manifest and overlap receipts",
            "mapped_fields": (
                "pairing_summary.tsv:study_id,specimens_in,assays_in,patients_in,patients_with_baseline,patients_with_followup,patients_paired,candidate_pairs,selected_pairs,technical_replicate_specimens,same_lesion_pairs,platform_counts,selected_by_window,endpoint_evaluable_counts,endpoint_status; "
                "pairing longitudinal_support.tsv:study_id,window,selected_pairs,support_role; "
                "model longitudinal_support.tsv:study_id,unit,window_id,record_type,model,effect_role,n_pairs,n_patients_input,n_patients_used,n_observations_used,n_observations_fitted,n_R,n_NR,n_arm_ici,n_arm_combination,status,reason,support_role; "
                "within_group_deltas.tsv:unit,window,response,arm,n,estimate,se,ci_lb,ci_ub,df,effect_role,status,reason,policy_status; "
                "model_support.tsv R columns:unit,n_input,n_complete,n_patients_input,n_patients_used,n_observations_used,n_missing_endpoint,n_missing_expression,n_R,n_NR,rank,n_arm_ici,n_arm_combination,residual_df,status,reason,policy_status; Python adds data_classification,analysis_family; repeated model support also includes n_missing_windows,patient_aware_model,fixed_patient_response_covariate_rank,fixed_patient_response_covariate_rank_status,convergence_status,singular,corroboration_role,repeated_selection_mode; "
                "a_long_effects.tsv:unit,unit_family,feature_method_id,analysis_method_id,endpoint_id,regimen_id,window_id,assay_id,effect_scale_id,panel_family,multiplicity_family_id,source_family_id,overlap_receipt_id,overlap_status,study,patient_set_id,model,contrast,effect_role,estimate,se,ci_lb,ci_ub,df,rank,n,n_observations_fitted,n_observations_contrast,n_R,n_NR,n_arm_ici,n_arm_combination,p_value,status,reason,analysis_family,policy_status; "
                "a_long_synthesis.tsv retains effect identity and includes k,n_input,n_excluded,independence_status,source_family_count,overlap_receipt_count,estimate,se,ci_lb,ci_ub,prediction_interval_lb,prediction_interval_ub,tau2,I2,Q,p_value,status,reason,policy_status,adjustment_method,adjusted_p; "
                "synthesis_support.tsv:analysis_group_id,preflight_reason,k,n_input,n_excluded,independence_status; "
                "repeated effects retain contrast-specific n_R/n_NR and n_observations_contrast separately from n_observations_fitted; repeated-model longitudinal support analysis_effect rows use n_patients_used=n_R+n_NR and n_observations_used=n_observations_contrast; n in repeated effects remains fitted observations, not patients; central R_minus_NR_change/effect_role=central_change_contrast; ANCOVA R_minus_NR_on_value_conditional_on_pre remains sensitivity; W10 display-only derived_unpaired_baseline_patients=patients_with_baseline-patients_paired for invented single-window rows"
            ),
            "mapping_status": "Public W8 field inventory for invented rows; schema mapping does not establish model validation or source admission; AP2:<panel>,CYT,CUSTOM:<panel>,21M5M6:<gene> units and effect_scale_id remain separate; real source admission unresolved",
        },
        {
            "shell_table": "Table_06_open_gates.tsv",
            "product": "readiness display",
            "source_schema": "invented layout rows; actual blockers listed in PAPER_A_READINESS.md",
            "mapped_fields": "gate,status,blocker,future_command",
            "mapping_status": "format shell only; rows are invented placeholders",
        },
        {
            "shell_table": "Supplement_S1_bulk_qc_pca_de",
            "product": "A-BIO/A-BULK",
            "source_schema": "A-BIO coverage and bulk-stage public output families; A-BULK qc/pca/de CLI",
            "mapped_fields": "cohort_id,stage,status,reason,sample_count,analysis_sample_count",
            "mapping_status": "layout only; no product output was loaded",
        },
        {
            "shell_table": "Supplement_S2_a_comp",
            "product": "A-COMP",
            "source_schema": "A-COMP public outputs and synthetic-demo route",
            "mapped_fields": "fraction inputs require study_id,sample_id,cell_type,fraction; public outputs include fractions.tsv,coverage.tsv,panel_correlations.tsv",
            "mapping_status": "layout only; no pin or product output was loaded",
        },
        {
            "shell_table": "Figure_06_sc1_compartment_dotplot",
            "product": "SC-1 (W5)",
            "source_schema": "unit_summary.tsv; provenance_coverage.tsv; source_hashes.tsv; panel_membership.tsv; coverage_audit.tsv; compartment_expression_panels.pdf; manifest.json",
            "mapped_fields": "study,cancer,compartment,unit_id,unit_type,gene_group,method_id,n_profiles,n_eligible_donors,n_donors_support,n_members_available_global,n_members_total,member_availability,member_support_min,member_support_max,median_log2_cpm_plus1,q1_log2_cpm_plus1,q3_log2_cpm_plus1,median_cpm,median_percent_cells_detected,detection_limit_tag,status,reason,aggregate_gene_status; plot composite values only when status=shown; individual M5/M6 gene dots use median_percent_cells_detected for size",
            "mapping_status": "exact public fields mapped from parent patient-free schema facts; this invented figure plots custom composite panels only, not M5/M6 genes",
        },
        {
            "shell_table": "Figure_07_sc3_exploratory_effects",
            "product": "SC-3 (W5)",
            "source_schema": "sc3_effects.tsv; sc3_refusals.tsv; a_meta_summaries.tsv; a_meta_subgroups.tsv; de_results.tsv; de_refusals.tsv; manifest.json",
            "mapped_fields": "sc3_effects.tsv:unit_family,unit,method_id,m5m6_gene_flag,study,cancer,cancer_components,drug_class_stratum,endpoint_family,endpoint_definition_id,patient_set_id,n_R,n_NR,mean_R,mean_NR,sd_R,sd_NR,g,se,status,reason,n_found,n_total,sensitivity_label,compartment,sc_endpoint_family,response_metric; heatmap is panel Hedges g by cohort and compartment (g), preserving status/reason; de_results.tsv:comparison_id,cohort,compartment,endpoint_family,gene,baseMean,log2FoldChange,lfcSE,stat,pvalue,padj,status,reason,padj_status; log2FoldChange remains separate from g",
            "mapping_status": "exact public fields mapped from parent patient-free schema facts; unit prefix is not treated as panel ID; RECIST, pathology, and T-cell expansion remain separate; T-cell expansion is a nonclinical metric, not clinical response",
        },
        {
            "shell_table": "W8_A_LONG_all_products",
            "product": "A-LONG (W8)",
            "source_schema": "pairing_summary.tsv; pair_candidates.tsv, pairing_exclusions.tsv, missing_followups.tsv, pair_manifest.json (private); longitudinal_support.tsv; within_group_deltas.tsv; model_support.tsv; a_long_effects.tsv; a_long_synthesis.tsv; synthesis_support.tsv; overlap receipts and R retention",
            "mapped_fields": "pair_candidates.tsv,pairing_exclusions.tsv,missing_followups.tsv and pair_manifest.json stay private; no pair or patient rows enter manuscript exports; exact public fields are mapped in Table_05_a_long_pairing_attrition.tsv and the Figure_08/Supplement_S3-S6 rows below; no influence output supplied",
            "mapping_status": "Public W8 schema inventory only; no real-source admission or influence output",
        },
        {
            "shell_table": "Figure_08_along_pair_structure_and_direct_effect",
            "product": "A-LONG1B + A-LONG2B",
            "source_schema": "pairing_summary.tsv; pairing/model longitudinal_support.tsv; a_long_effects.tsv",
            "mapped_fields": "pairing_summary.tsv separates specimens_in,assays_in,patients_in,patients_with_baseline,patients_with_followup,patients_paired,candidate_pairs,selected_pairs,same_lesion_pairs; longitudinal_support.tsv separates n_pairs,n_patients_input,n_patients_used,n_observations_used,n_observations_fitted; a_long_effects.tsv model=delta_primary,contrast=R_minus_NR_change,effect_role=central_change_contrast with estimate,se,ci_lb,ci_ub; ANCOVA R_minus_NR_on_value_conditional_on_pre remains a sensitivity; exact-day and interval timing categories shown as invented layout only",
            "mapping_status": "Invented layout keyed to public field names; real source/release absent; real patient N UNKNOWN separately from specimen/assay N; no patient rows",
        },
        {
            "shell_table": "Supplement_S3_a_long_1a_source_coverage",
            "product": "A-LONG1A",
            "source_schema": "pairing_summary.tsv; longitudinal_support.tsv; a_long_effects.tsv; overlap receipts",
            "mapped_fields": "source_family_id,overlap_receipt_id,overlap_status,study,regimen_id,window_id,selected_by_window,selected_pairs,support_role,specimens_in,assays_in,patients_in,patients_paired",
            "mapping_status": "source-flow comparison unit is independent study family; real patient/specimen/assay N UNKNOWN separately; catalogue entries are not independent cohort counts; invented layout only",
        },
        {
            "shell_table": "Supplement_S4_a_long_2a_within_group_delta",
            "product": "A-LONG2A",
            "source_schema": "within_group_deltas.tsv; model_support.tsv",
            "mapped_fields": "within_group_deltas.tsv:unit,window,response,arm,n,estimate,se,ci_lb,ci_ub,df,effect_role,status,reason,policy_status; model_support.tsv R:unit,n_input,n_complete,n_patients_input,n_patients_used,n_observations_used,n_missing_endpoint,n_missing_expression,n_R,n_NR,rank,n_arm_ici,n_arm_combination,residual_df,status,reason,policy_status; Python:data_classification,analysis_family",
            "mapping_status": "DELTA_R and DELTA_NR shown separately at window=baseline_to_on; these are within-group changes, not an interaction; one invented unavailable-support row retained",
        },
        {
            "shell_table": "Supplement_S5_a_long_2c_programme_directions",
            "product": "A-LONG2C",
            "source_schema": "a_long_effects.tsv; a_long_synthesis.tsv; synthesis_support.tsv",
            "mapped_fields": "effect rows retain source_family_id,unit,analysis_method_id,effect_scale_id,n_R,n_NR,estimate,se,ci_lb,ci_ub,status,reason; cancer context requires a separate admitted study/cancer registry mapping (currently unavailable), not a listed effect-table column; a_long_synthesis.tsv retains k,n_input,n_excluded,independence_status,source_family_count,overlap_receipt_count,estimate,se,ci_lb,ci_ub,prediction_interval_lb,prediction_interval_ub,tau2,I2,Q,p_value,status,reason,policy_status,adjustment_method,adjusted_p; synthesis_support.tsv:analysis_group_id,preflight_reason,k,n_input,n_excluded,independence_status",
            "mapping_status": "comparison unit is independent study family across cancers; within-study effects use patient units; influence availability UNAVAILABLE; no replication claim",
        },
        {
            "shell_table": "Supplement_S6_a_long_3c_sensitivity",
            "product": "A-LONG3C",
            "source_schema": "a_long_effects.tsv; model_support.tsv; longitudinal_support.tsv",
            "mapped_fields": "model,contrast,effect_role,analysis_method_id,effect_scale_id,estimate,se,ci_lb,ci_ub,n_patients_used,status,reason; prespecified primary,same-lesion,exact-day,tighter-timing model rows",
            "mapping_status": "matched primary/sensitivity estimates and support are invented; selection,missing-biopsy and influence results UNAVAILABLE; missing biopsies are not assumed random",
        },
        {
            "shell_table": "Supplements_S7-S10_a_long_gated_questions",
            "product": "A-LONG3A/3B/4A/4B",
            "source_schema": "no analysis output schema admitted before gates",
            "mapped_fields": "3A moderator-design identifiability (cancer,regimen,class,window,rank,confounding); 3B released moderator-effect heterogeneity; 4A orthogonal cellular/modality context; 4B NMA feasibility/qualified temporal handoff; units: 3A independent studies plus paired-patient support, 3B independent families, 4A patients with nested cells/spots, 4B studies/programmes",
            "mapping_status": "gated/unavailable; no estimates, intervals, or unsupported network arrows; real patient N UNKNOWN separately from specimen/assay N",
        },
    ]
    _write_tsv(
        tables_dir / "Table_00_product_schema_map.tsv", schemas,
        ("shell_table", "product", "source_schema", "mapped_fields", "mapping_status"),
        fixture_sha256,
    )

    eligibility = [
        {
            "cohort_id": row["cohort"], "cancer": row["cancer"],
            "uniform_drug_class": row["drug"], "platform": row["platform"],
            "unit": "invented display unit", "transform": "invented display transform",
            "feature_id": "invented placeholder", "de_engine": "not evaluated",
            "endpoint_families": "invented placeholder", "sample_count": row["n"],
            "eligibility_status": "not evaluated; invented metadata only",
        } for row in _COHORTS
    ]
    _write_tsv(
        tables_dir / "Table_01_cohort_measurement_eligibility.tsv", eligibility,
        ("cohort_id", "cancer", "uniform_drug_class", "platform", "unit", "transform",
         "feature_id", "de_engine", "endpoint_families", "sample_count",
         "eligibility_status"), fixture_sha256,
    )

    coverage = [
        {"cohort_id": "Invented cohort A", "unit_family": "panel", "unit": "Panel A",
         "n_found": 4, "n_total": 4, "complete": "true", "scorable": "true",
         "missing": "", "fixed_subset": "", "reason": "", "sensitivity_label": "illustrative"},
        {"cohort_id": "Invented cohort B", "unit_family": "pathway", "unit": "Hallmark set A",
         "n_found": 3, "n_total": 4, "complete": "false", "scorable": "false",
         "missing": "Invented feature D", "fixed_subset": "", "reason": "coverage incomplete",
         "sensitivity_label": "unavailable example"},
        {"cohort_id": "Invented cohort C", "unit_family": "fraction", "unit": "Fraction method",
         "n_found": 0, "n_total": 4, "complete": "false", "scorable": "false",
         "missing": "all invented fixture members", "fixed_subset": "",
         "reason": "unavailable shell row", "sensitivity_label": "unavailable"},
    ]
    _write_tsv(
        tables_dir / "Table_02_coverage_provenance.tsv", coverage,
        _BIO_COVERAGE_COLUMNS, fixture_sha256,
    )

    effects = []
    for index, row in enumerate(_PANEL_EFFECTS[:3]):
        cancer, drug, panel = row["label"].split(" · ")
        effects.append({
            "record_type": "study_effect", "unit_family": "panel", "unit": panel,
            "method_id": "invented_display_only", "m5m6_gene_flag": "not_applicable",
            "study": "Invented study " + chr(65 + index), "cancer": cancer,
            "cancer_components": "", "drug_class_stratum": drug,
            "endpoint_family": "invented_endpoint", "endpoint_definition_id": "invented_definition",
            "patient_set_id": "not_created", "n_R": 12, "n_NR": 11, "mean_R": "invented",
            "mean_NR": "invented", "sd_R": "invented", "sd_NR": "invented",
            "g": row["estimate"], "se": "invented", "ci_lb": row["lower"],
            "ci_ub": row["upper"], "status": row["status"], "reason": "",
            "n_found": 4, "n_total": 4, "sensitivity_label": "invented display",
            "stratum_type": "", "stratum": "", "k": "", "estimate": "", "tau2": "",
            "I2": "", "Q": "", "p": "", "q": "invented; no method applied",
            "fixed_estimate": "", "label": "", "low_k": "",
            "multiplicity_family": "INVENTED DISPLAY FAMILY ONLY",
        })
    effects.append({
        "record_type": "study_effect", "unit_family": "gene", "unit": "Gene C",
        "method_id": "invented_display_only", "m5m6_gene_flag": "not_applicable",
        "study": "Invented study D", "cancer": "Cancer C", "cancer_components": "",
        "drug_class_stratum": "Drug class C", "endpoint_family": "invented_endpoint",
        "endpoint_definition_id": "invented_definition", "patient_set_id": "not_created",
        "n_R": 0, "n_NR": 0, "mean_R": "", "mean_NR": "", "sd_R": "", "sd_NR": "",
        "g": "", "se": "", "ci_lb": "", "ci_ub": "", "status": "unavailable",
        "reason": "coverage incomplete; no estimate", "n_found": 0, "n_total": 4,
        "sensitivity_label": "unavailable", "stratum_type": "", "stratum": "",
        "k": "", "estimate": "", "tau2": "", "I2": "", "Q": "", "p": "", "q": "",
        "fixed_estimate": "", "label": "", "low_k": "",
        "multiplicity_family": "INVENTED DISPLAY FAMILY ONLY",
    })
    effects.append({
        "record_type": "synthesis_summary", "unit_family": "panel",
        "unit": "Panel A", "method_id": "not_run",
        "endpoint_family": "invented_endpoint",
        "endpoint_definition_id": "invented_definition",
        "stratum_type": "per_cancer", "stratum": "Cancer A",
        "cancer": "Cancer A", "drug_class_stratum": "Drug class A",
        "stage": "display only", "k": 3, "estimate": 0.18, "se": "invented",
        "n_cancers": 1, "n_studies": 3, "ci_lb": -0.21, "ci_ub": 0.57,
        "p": "", "q": "", "label": "nonsignificant example",
        "status": "invented layout only; no synthesis run",
        "reason": "fixed display value; no model fit",
        "weighting": "not applied",
        "multiplicity_family": "INVENTED DISPLAY FAMILY ONLY",
    })
    effects.append({
        "record_type": "subgroup_test", "unit_family": "panel",
        "unit": "Panel A", "method_id": "not_run",
        "endpoint_family": "invented_endpoint",
        "endpoint_definition_id": "invented_definition",
        "moderator": "invented grouping field", "total_k": 3, "n_levels": 2,
        "F": "", "p": "", "status": "unavailable; test not run",
        "reason": "no subgroup model in report shell",
        "multiplicity_family": "NOT APPLICABLE IN SHELL",
    })
    effects_fields = tuple(dict.fromkeys(
        ("record_type", *_EFFECT_COLUMNS, *_SYNTHESIS_COLUMNS,
         *_SUBGROUP_COLUMNS, "multiplicity_family")
    ))
    _write_tsv(tables_dir / "Table_03_full_effects_multiplicity.tsv",
               effects, effects_fields, fixture_sha256)

    validation = [
        {"analysis_role": "formal primary", "product": "A-P2", "validation_stage": "development leave-family-out example",
         "output_file": "primary_aggregates.tsv", "analysis": "PRIMARY_TPM", "evaluation_label": "",
         "metric": "learner_auc", "weighting": "equal_study", "study_count": 3, "cancer_count": 2,
         "value": 0.77, "learner_auc": "", "cyt_auc": "", "delta_auc": "", "lower_95": "", "upper_95": "",
         "inference_status": "", "status": "invented layout only", "reason": "",
         "source_metric_columns": "analysis,metric,weighting,study_count,cancer_count,value,status,comparator_membership_caveat",
         "overlap_disclosure": "M2 includes GZMA and PRF1 and partly overlaps CYT; these are not independent signals",
         "schema_mapping_status": "mapped to W1 development aggregate field names; value invented"},
        {"analysis_role": "formal primary", "product": "A-P2", "validation_stage": "development leave-family-out example",
         "output_file": "primary_aggregates.tsv", "analysis": "PRIMARY_TPM", "evaluation_label": "",
         "metric": "cyt_auc", "weighting": "equal_study", "study_count": 3, "cancer_count": 2,
         "value": 0.68, "learner_auc": "", "cyt_auc": "", "delta_auc": "", "lower_95": "", "upper_95": "",
         "inference_status": "", "status": "invented layout only", "reason": "",
         "source_metric_columns": "analysis,metric,weighting,study_count,cancer_count,value,status,comparator_membership_caveat",
         "overlap_disclosure": "M2 includes GZMA and PRF1 and partly overlaps CYT; these are not independent signals",
         "schema_mapping_status": "mapped to W1 development aggregate field names; value invented"},
        {"analysis_role": "formal primary", "product": "A-P2", "validation_stage": "development leave-family-out example",
         "output_file": "primary_aggregates.tsv", "analysis": "PRIMARY_TPM", "evaluation_label": "",
         "metric": "delta_auc", "weighting": "equal_study", "study_count": 3, "cancer_count": 2,
         "value": 0.09, "learner_auc": "", "cyt_auc": "", "delta_auc": "", "lower_95": "", "upper_95": "",
         "inference_status": "", "status": "invented layout only; no interval in this aggregate schema", "reason": "",
         "source_metric_columns": "analysis,metric,weighting,study_count,cancer_count,value,status,comparator_membership_caveat",
         "overlap_disclosure": "M2 includes GZMA and PRF1 and partly overlaps CYT; these are not independent signals",
         "schema_mapping_status": "mapped to W1 development aggregate field names; value invented"},
        {"analysis_role": "formal primary", "product": "A-P2", "validation_stage": "final-test example",
         "output_file": "final_metrics.tsv", "analysis": "PRIMARY_TPM", "evaluation_label": "INVENTED_FINAL_TEST_EXAMPLE",
         "metric": "learner_auc,cyt_auc,delta_auc", "weighting": "", "study_count": "", "cancer_count": "",
         "value": "", "learner_auc": 0.62, "cyt_auc": 0.56, "delta_auc": 0.06, "lower_95": -0.11, "upper_95": 0.20,
         "inference_status": "invented interval crosses zero", "status": "invented layout only", "reason": "",
         "source_metric_columns": "analysis,evaluation_label,inference_status,status,n,responders,nonresponders,learner_auc,cyt_auc,delta_auc,lower_95,upper_95,second_check_flag,reason,comparator_membership_caveat",
         "overlap_disclosure": "M2 includes GZMA and PRF1 and partly overlaps CYT; these are not independent signals",
         "schema_mapping_status": "mapped to W1 final metric fields; interval applies to paired delta_auc; values invented"},
        {"analysis_role": "secondary", "product": "A-LONG", "validation_stage": "not applicable",
         "output_file": "not applicable", "analysis": "", "evaluation_label": "",
         "metric": "", "weighting": "", "study_count": "", "cancer_count": "",
         "value": "", "learner_auc": "", "cyt_auc": "", "delta_auc": "", "lower_95": "", "upper_95": "",
         "inference_status": "", "status": "no A-LONG AUROC claim", "reason": "",
         "source_metric_columns": "No A-LONG AUROC metric; see Table_00 for the parent-supplied W8 output schemas",
         "overlap_disclosure": "shared baseline patients are not independent replication; A-LONG never changes A-P2/A-BIO",
         "schema_mapping_status": "A-LONG remains secondary; public W8 output schemas are mapped in Table_00; no A-LONG AUROC value is included"},
    ]
    _write_tsv(
        tables_dir / "Table_04_a_p2_validation.tsv", validation,
        ("analysis_role", "product", "validation_stage", "output_file", "analysis", "evaluation_label",
         "metric", "weighting", "study_count", "cancer_count", "value", "learner_auc", "cyt_auc",
         "delta_auc", "lower_95", "upper_95", "inference_status", "status", "reason",
         "source_metric_columns", "overlap_disclosure", "schema_mapping_status"), fixture_sha256,
    )

    pair_fields = (
        "study_id", "specimens_in", "assays_in", "patients_in",
        "patients_with_baseline", "patients_with_followup", "patients_paired",
        "candidate_pairs", "selected_pairs", "technical_replicate_specimens",
        "same_lesion_pairs", "platform_counts", "selected_by_window",
        "endpoint_evaluable_counts", "endpoint_status",
        "derived_unpaired_baseline_patients", "derived_field_definition",
    )
    _write_tsv(tables_dir / "Table_05_a_long_pairing_attrition.tsv",
               _PAIR_ROWS, pair_fields, fixture_sha256)
    _write_tsv(tables_dir / "Table_06_open_gates.tsv", _GATES,
               ("gate", "status", "blocker", "future_command"), fixture_sha256)
    return sorted(path.relative_to(tables_dir.parent).as_posix()
                  for path in tables_dir.iterdir() if path.is_file())


def _all_figures(figures_dir: Path) -> list[str]:
    output = []
    output.extend(_figure_01(figures_dir))
    output.extend(_figure_02(figures_dir))
    output.extend(_figure_03(figures_dir))
    output.extend(_figure_04(figures_dir))
    output.extend(_figure_05(figures_dir))
    output.extend(_figure_06(figures_dir))
    output.extend(_figure_07(figures_dir))
    output.extend(_figure_08(figures_dir))
    output.extend(_figure_s1(figures_dir))
    output.extend(_figure_s2(figures_dir))
    for index in range(4):
        output.extend(_figure_s3_s6(figures_dir, index))
    for index in range(4):
        output.extend(_figure_gated_along(figures_dir, index))
    return sorted(output)


def _prepare_output(output_dir: Path) -> Path:
    if not output_dir.is_absolute():
        raise ValueError("--output-dir must be an absolute path outside the repository")
    resolved = output_dir.expanduser().resolve()
    if resolved == Path(resolved.anchor) or resolved.is_relative_to(ROOT):
        raise ValueError("report artifacts must be written outside the repository")
    for parent in (output_dir.expanduser(), *output_dir.expanduser().parents):
        if parent.is_symlink():
            raise ValueError("output path cannot contain symlinks")
    if not resolved.exists():
        resolved.mkdir(parents=True)
        return resolved
    if not resolved.is_dir() or resolved.is_symlink():
        raise ValueError("output path must be a regular directory")
    if any(resolved.iterdir()):
        raise ValueError(
            "refusing to write into a nonempty output directory; choose a fresh private directory"
        )
    return resolved


def generate(output_dir: Path) -> dict:
    """Generate all static figures and tables in a dedicated private directory."""
    output_dir = _prepare_output(output_dir)
    _load_plotting()
    figures_dir = output_dir / "figures"
    tables_dir = output_dir / "tables"
    figures_dir.mkdir()
    tables_dir.mkdir()
    fixture_sha256 = _fixture_hash()
    figure_files = _all_figures(figures_dir)
    table_files = _write_tables(tables_dir, fixture_sha256)
    generated_files = sorted(figure_files + table_files)
    code_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    output_hashes = {
        name: hashlib.sha256((output_dir / name).read_bytes()).hexdigest()
        for name in generated_files
    }
    manifest = {
        "schema": "paper_a_joint_manuscript_shell_v1",
        "generator": CODE_VERSION,
        "data_classification": "invented",
        "classification": LABEL,
        "biological_validation": False,
        "external_inputs_opened": False,
        "input_provenance": {
            "fixture_id": FIXTURE_ID,
            "fixture_sha256": fixture_sha256,
            "source": "fixed presentation constants in tools/a_report/__main__.py",
            "runtime_or_product_outputs_read": False,
        },
        "code_sha256": code_sha256,
        "figure_count": len(FIGURE_NAMES),
        "figure_formats": ["SVG", "PDF"],
        "table_count": len(table_files),
        "generated_files": generated_files,
        "output_sha256": output_hashes,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tools.a_report",
        description="Build invented-data manuscript figure and table shells.",
    )
    parser.add_argument(
        "--output-dir", required=True, type=Path,
        help="dedicated private output directory outside this repository",
    )
    args = parser.parse_args(argv)
    try:
        manifest = generate(args.output_dir)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps({
        "classification": LABEL,
        "figure_count": manifest["figure_count"],
        "table_count": manifest["table_count"],
        "output_dir": str(args.output_dir),
        "manifest": "manifest.json",
    }, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
