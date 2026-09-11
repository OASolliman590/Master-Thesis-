"""Stage 06: within-cohort DE."""

from .de_models import resolve_de_backend
from .harmonize import harmonize_expression_for_assay

__all__ = ["harmonize_expression_for_assay", "resolve_de_backend"]
