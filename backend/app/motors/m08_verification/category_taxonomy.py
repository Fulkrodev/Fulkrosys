"""Canonical ENS category taxonomy bridge for Motor 8 (verification).

WAVE C3 (tracker §2.2 line 229) — two category taxonomies coexist in this motor:

  * Internal autopilot keys: masculine ``BASICO | MEDIO | ALTO``
    (``orchestrator.CATEGORY_PLAN`` keys, ``models.py`` docstring,
    ``schemas.VALID_CATEGORIES``).
  * ENS / project-facing field ``project.categoria_objetivo``: feminine
    ``BASICA | MEDIA | ALTA``.

The dual taxonomy is *intentional* (the internal scan plan key vs. the
domain ENS field), and it is already safely bridged at every ``CATEGORY_PLAN``
access via ``orchestrator._normalize_category``. This module promotes that
private bridge into a single shared, importable source of truth so the same
normalization is reused across the motor (orchestrator, trigger events,
evidence pack) instead of ad-hoc ``in ("ALTO", "ALTA")`` checks.

Canonical internal key = masculine ``BASICO | MEDIO | ALTO`` (matches
``CATEGORY_PLAN`` keys and ``run.category`` storage).
"""
from __future__ import annotations

from typing import Optional

# Canonical internal autopilot keys (masculine).
BASICO = "BASICO"
MEDIO = "MEDIO"
ALTO = "ALTO"

INTERNAL_KEYS = (BASICO, MEDIO, ALTO)

# ENS / project-facing display form (feminine).
_INTERNAL_TO_ENS: dict[str, str] = {
    BASICO: "BASICA",
    MEDIO: "MEDIA",
    ALTO: "ALTA",
}

# Every accepted spelling (both genders, any case) -> internal key.
_CATEGORY_NORM: dict[str, str] = {
    "ALTA": ALTO, "ALTO": ALTO,
    "MEDIA": MEDIO, "MEDIO": MEDIO,
    "BASICA": BASICO, "BASICO": BASICO,
}


def normalize_category(cat: Optional[str], *, default: str = BASICO) -> str:
    """Collapse any ENS category spelling/gender/case to the internal key.

    Unknown/empty inputs degrade to ``default`` (``BASICO`` — the least
    privileged scan plan, fail-safe). Never raises.
    """
    return _CATEGORY_NORM.get((cat or "").strip().upper(), default)


def to_ens_category(cat: Optional[str]) -> Optional[str]:
    """Return the ENS feminine form (BASICA/MEDIA/ALTA), or None if unknown."""
    if not cat or not str(cat).strip():
        return None
    key = _CATEGORY_NORM.get(str(cat).strip().upper())
    if key is None:
        return None
    return _INTERNAL_TO_ENS[key]


def is_alta(cat: Optional[str]) -> bool:
    """True iff the category is the highest ENS level, in any spelling.

    Robust replacement for ad-hoc ``categoria == "ALTA"`` /
    ``category in ("ALTO", "ALTA")`` checks that break if the other gendered
    spelling shows up.
    """
    return _CATEGORY_NORM.get((cat or "").strip().upper()) == ALTO


__all__ = [
    "BASICO",
    "MEDIO",
    "ALTO",
    "INTERNAL_KEYS",
    "normalize_category",
    "to_ens_category",
    "is_alta",
]
