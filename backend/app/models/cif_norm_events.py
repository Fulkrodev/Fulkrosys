"""Auto-populate cif_norm on write (#7 · populate-on-write canónico).

Event listeners SQLAlchemy ``before_insert``/``before_update`` sobre Lead y
Client: derivan ``cif_norm`` del CIF fuente en CADA escritura, garantizando que
ningún call-site se olvide de poblarlo (single source of truth = el CIF crudo).

Registrado desde ``models/__init__.py`` (tras importar Lead+Client).
"""
from __future__ import annotations

from sqlalchemy import event

from backend.app.core.cif_norm import normalize_cif
from backend.app.models.commercial import Lead
from backend.app.models.core import Client


def _lead_cif_norm(mapper, connection, target) -> None:  # noqa: ANN001
    target.cif_norm = normalize_cif(target.empresa_cif)


def _client_cif_norm(mapper, connection, target) -> None:  # noqa: ANN001
    target.cif_norm = normalize_cif(target.cif)


for _ev in ("before_insert", "before_update"):
    event.listen(Lead, _ev, _lead_cif_norm)
    event.listen(Client, _ev, _client_cif_norm)
