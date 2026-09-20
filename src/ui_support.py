"""Compatibility imports for the relocated web application helpers."""

from .web_app.support import (
    GOLDEN_DATASET,
    EVALUATION_REPORT,
    ROOT,
    STANDARDIZED,
    load_corpus_catalog,
    load_evaluation_status,
    load_golden_questions,
    retrieval_label,
    run_generation,
)

__all__ = [
    "EVALUATION_REPORT",
    "GOLDEN_DATASET",
    "ROOT",
    "STANDARDIZED",
    "load_corpus_catalog",
    "load_evaluation_status",
    "load_golden_questions",
    "retrieval_label",
    "run_generation",
]
