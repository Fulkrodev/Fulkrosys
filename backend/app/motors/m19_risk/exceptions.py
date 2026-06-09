"""Motor 19 — Project Risk Management — exception hierarchy.

Patron consistente con M12 Magic Link (8 excepciones) y
M3 DdA Engine (5 excepciones).
"""


class ProjectRiskError(Exception):
    """Base exception for Motor 19 Project Risk Management errors."""


class ProjectRiskNotFoundError(ProjectRiskError):
    """Project risk not found by id."""


class ProjectRiskValidationError(ProjectRiskError):
    """Invalid input data for a project risk."""


class ProjectRiskStateError(ProjectRiskError):
    """Invalid state transition.

    Valid transitions:
    - identificado -> monitorizado
    - monitorizado -> materializado
    - monitorizado -> cerrado
    - materializado -> cerrado
    - identificado -> cerrado (only if justified)
    """


class CatalogNotFoundError(ProjectRiskError):
    """Project risks catalog YAML not found or unreadable."""


class CatalogParseError(ProjectRiskError):
    """Project risks catalog YAML is malformed or missing required fields."""


class CatalogAlreadyInstantiatedError(ProjectRiskError):
    """Catalog already instantiated for this project."""


class TriggerEvaluationError(ProjectRiskError):
    """Error evaluating a trigger condition for risk materialization."""
