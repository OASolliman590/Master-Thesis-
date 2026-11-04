"""A-META per-study effects and synthesis for Paper A."""

from .effects import EFFECT_COLUMNS, study_effects
from .features import (
    FeatureTable,
    build_feature_table,
    external_feature_table,
    read_external_feature_table,
    read_feature_table,
    write_feature_table,
)
from .synthesis import SynthesisResult, synthesize

__all__ = [
    "EFFECT_COLUMNS",
    "FeatureTable",
    "SynthesisResult",
    "build_feature_table",
    "external_feature_table",
    "read_external_feature_table",
    "read_feature_table",
    "study_effects",
    "synthesize",
    "write_feature_table",
]
