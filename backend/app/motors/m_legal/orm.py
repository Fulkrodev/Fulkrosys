"""ORM model · legal_obligations_catalog (read-only catalog table).

Tabla creada via migration add_legal_obl_catalog_001 (17 May 2026).
GRANT SELECT ON legal_obligations_catalog TO fulkro_app (read-only en runtime).
Sub-atom 1.C.0.C.expand v3.9 expone ORM Python sobre la tabla.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


class LegalObligationCatalog(Base):
    """Catálogo MAESTRO de obligaciones legales (RGPD/LOPDGDD/NIS2/DORA/AI_Act).

    Tabla SIN project_id, SIN RLS, readonly global (fulkro_app: GRANT SELECT only).
    Seeded via scripts/seed/seed_legal_obligations_catalog.py desde
    docs/catalogs/legal_obligations_v1.yaml (250 entries v2 EXPAND).
    """

    __tablename__ = "legal_obligations_catalog"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    codigo: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    regulacion: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    articulo: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    obligacion: Mapped[str] = mapped_column(Text, nullable=False)
    sector_aplica: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    ens_categoria_aplica: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    evidencia_requerida: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    vinculo_medida_ens: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    fuente_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
