"""Norma plugin registry singleton (mini-atom 3).

Plugins register themselves at import time via
``NormaRegistry.register(SubclassInstance())``. The motor core consumes
the registry to:

- Iterate registered normas (``get_all``).
- Look up a specific norma by key (``get``).
- Find normas that own a particular check (``get_by_check_owned``) —
  cross-cutting concerns: e.g. ``ssl_cert_expiry`` is owned by both
  NIS2 and ISO 27001.
"""
from __future__ import annotations

from typing import Iterable

from backend.app.motors.m_compliance_monitor.normas.base import NormaModule


class NormaRegistry:
    """Process-wide singleton mapping ``norma_key`` → ``NormaModule`` instance."""

    _registered: dict[str, NormaModule] = {}

    @classmethod
    def register(cls, norma_module: NormaModule) -> None:
        norma_module.__class__.validate()
        cls._registered[norma_module.norma_key] = norma_module

    @classmethod
    def get(cls, norma_key: str) -> NormaModule | None:
        return cls._registered.get(norma_key)

    @classmethod
    def get_all(cls) -> list[NormaModule]:
        return sorted(cls._registered.values(), key=lambda n: n.norma_key)

    @classmethod
    def get_by_check_owned(cls, check_name: str) -> list[NormaModule]:
        """Return every registered norma that owns ``check_name``.

        Used by the reports service when a cross-cutting check influences
        more than one regulatory framework (e.g. ``ssl_cert_expiry``
        feeds both NIS2 and ISO 27001 scoring).
        """
        return [n for n in cls.get_all() if check_name in n.checks_owned]

    @classmethod
    def keys(cls) -> Iterable[str]:
        return list(cls._registered.keys())

    @classmethod
    def clear(cls) -> None:
        """Test-only helper · NEVER call from production code."""
        cls._registered.clear()
