from __future__ import annotations

from src.pipeline.cli import _infer_response_from_text, _infer_response_label, _infer_timing_from_text


def test_response_inference_supports_geo_clinical_patterns() -> None:
    assert _infer_response_from_text("treated with anti-PD-1 therapy")[0] == "unknown"
    assert _infer_response_from_text("response_to_ici: R")[0] == "responder"
    assert _infer_response_from_text("response_to_ici: NR")[0] == "non_responder"
    assert _infer_response_from_text("io.response: PR")[0] == "responder"
    assert _infer_response_from_text("io.response: SD")[0] == "non_responder"
    assert _infer_response_from_text("group: Nonresponder")[0] == "non_responder"
    assert _infer_response_from_text("Primary Path Response_minor Respoder")[0] == "responder"


def test_response_inference_supports_sample_prefixes() -> None:
    assert _infer_response_label("CR1509")[0] == "responder"
    assert _infer_response_label("NR4631")[0] == "non_responder"


def test_timing_inference_supports_baseline_week_and_surgery() -> None:
    assert _infer_timing_from_text("collection: Baseline from Pt_7") == "pre-treatment"
    assert _infer_timing_from_text("Biopsy collected at 4wks from Pt_7") == "on-treatment"
    assert _infer_timing_from_text("Surgery sample post treatment") == "post-treatment"
