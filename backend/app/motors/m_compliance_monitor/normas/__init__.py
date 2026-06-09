"""FULKRO Self-Compliance norma plugins · auto-discovered on import.

Importing this package walks the directory and imports every ``*.py``
file as a side-effect plugin module (each plugin calls
``NormaRegistry.register()`` at module level). Adding a new norma is a
single new file + one ``register()`` call — the motor core picks it up
automatically.

Public API:
- ``NormaModule``    — abstract base class (subclass to add a norma)
- ``NormaRegistry``  — singleton with ``get`` / ``get_all`` / etc.
- ``CheckOutcome``   — input dataclass for ``calculate_score``

See ``README.md`` in this package for the onboarding guide.
"""
from __future__ import annotations

import importlib
from pathlib import Path

from backend.app.motors.m_compliance_monitor.normas.base import (
    CheckOutcome,
    NormaModule,
)
from backend.app.motors.m_compliance_monitor.normas.registry import (
    NormaRegistry,
)


__all__ = ["CheckOutcome", "NormaModule", "NormaRegistry"]


_PACKAGE = __name__
_SKIP = {"__init__.py", "base.py", "registry.py"}


def _autodiscover() -> None:
    """Import every plugin module in this directory (side-effect: register)."""
    pkg_dir = Path(__file__).parent
    for path in sorted(pkg_dir.glob("*.py")):
        if path.name in _SKIP:
            continue
        importlib.import_module(f"{_PACKAGE}.{path.stem}")


_autodiscover()
