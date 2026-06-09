"""Motor 4 -- Gap Analysis Engine -- exception hierarchy.

Pattern: consistent with M3 DdA Engine (7 exceptions) and M19 (8 exceptions).
"""


class GapAnalysisError(Exception):
    """Base exception for Motor 4 Gap Analysis Engine errors."""


class GapNotFoundError(GapAnalysisError):
    """Gap finding not found by id."""


class GapValidationError(GapAnalysisError):
    """Invalid input data for gap operations."""


class GapStateError(GapAnalysisError):
    """Invalid gap state transition (e.g., close already-closed gap)."""


class DdANotReadyError(GapAnalysisError):
    """Cannot run gap analysis: project has no approved DdA yet.

    Motor 4 requires Motor 3 to have generated and approved a DdA
    for the project before gap analysis can compare current vs target state.
    """


class GapAlreadyAnalyzedError(GapAnalysisError):
    """Gap analysis already run for this project. Use force=True to re-analyze."""


class SeverityCatalogNotFoundError(GapAnalysisError):
    """gap_severity_rules_v1.yaml not found or unreadable."""


class SeverityCatalogParseError(GapAnalysisError):
    """gap_severity_rules_v1.yaml is malformed or missing required fields."""
