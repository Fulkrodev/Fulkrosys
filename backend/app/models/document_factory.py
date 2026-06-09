"""Motor 6 — Document Factory — template metadata model."""
from sqlalchemy import String, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, FullMixin


class Template(FullMixin, Base):
    __tablename__ = "templates"

    codigo: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    categoria: Mapped[str] = mapped_column(String(32), nullable=False)
    familia_ens: Mapped[str | None] = mapped_column(String(32))
    aplica_desde: Mapped[str | None] = mapped_column(String(16))
    version_actual: Mapped[str] = mapped_column(
        String(16), nullable=False, default="1.0"
    )
    docx_path: Mapped[str | None] = mapped_column(String(512))
    placeholders_requeridos: Mapped[dict | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    content_hash: Mapped[str | None] = mapped_column(String(64))
    fuente_md: Mapped[str | None] = mapped_column(String(512))
    placeholders_detected: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        doc="Placeholders detected in the real DOCX via docxtpl introspection",
    )
