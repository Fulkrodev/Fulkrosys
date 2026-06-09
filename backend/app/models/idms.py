"""M24 Intelligent Document Management models.

DocumentFolder: jerarquía de carpetas virtuales por proyecto (15 estándar + custom).
DocumentTag: etiquetado manual/reglas/LLM de documentos por medida ENS o categoría.
IdmsDocumentPermission: permisos granulares por documento (Sesion 9 Paso 3.1).
"""
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Integer, Boolean, Float, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, FullMixin


class DocumentFolder(FullMixin, Base):
    __tablename__ = "document_folders"

    client_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True,
    )
    parent_folder_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("document_folders.id"),
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    virtual_path: Mapped[str] = mapped_column(String(500), nullable=False)
    is_standard: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    standard_code: Mapped[str | None] = mapped_column(String(20))
    # "00".."13", "99" — carpetas del esqueleto §2.15
    custom_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class DocumentTag(FullMixin, Base):
    __tablename__ = "document_tags"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id"), nullable=False, index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True,
    )
    tag_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # "measure_ens" | "category" | "phase" | "custom"
    tag_value: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)
    # "manual" | "rule" | "llm"


class IdmsDocumentPermission(FullMixin, Base):
    """Permisos granulares por documento (Sesion 9 Paso 3.1).

    Modelo hibrido de acceso:
    - Si un documento tiene 0 filas aqui -> fallback a RLS project_id
      (todos los usuarios del proyecto pueden ver y editar segun su rol).
    - Si tiene filas, SOLO los usuarios listados pueden acceder segun su
      role columnar.

    Roles:
    - owner:  full control (read, edit, approve, archive, grant/revoke).
    - editor: read, edit, submit_for_review.
    - viewer: solo read + download.
    """
    __tablename__ = "idms_document_permissions"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    # "owner" | "editor" | "viewer"
    granted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("auth_users.id"),
    )
    granted_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("document_id", "user_id", name="uq_idms_perm_doc_user"),
    )
