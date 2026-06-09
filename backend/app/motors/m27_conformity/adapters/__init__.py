"""Motor 27 — External tool adapters (PILAR, LUCIA, INES, Registro).

All adapters follow the same contract: produce an exportable artifact with
metadata + checklist for the human operator to confirm submission. They are
manual-assisted (no live API integration) per addendum §7.9.
"""
from backend.app.motors.m27_conformity.adapters import (  # noqa: F401
    clara_ingester,
    ines_adapter,
    lucia_adapter,
    pilar_adapter,
    registry_adapter,
)
