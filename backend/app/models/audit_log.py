"""Immutable audit log with hash chain."""
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Index, String, text
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_seq_unique", "seq", unique=True),
    )
    # `seq` BIGSERIAL UNIQUE para hash chain tamper-evidence audit
    # (RD 311/2022 ENS). Sequence `audit_log_seq_seq` pre-existing
    # pre-S11 (migración d4f8b2a90001 2026-04-20). NO regenerar.
    # Triggers BD `fn_audit_log_hash_chain` ORDER BY seq calculan
    # `hash_current = sha256(prev || fields)`; `fn_audit_log_verify_chain`
    # valida integridad iterando ORDER BY seq.
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    seq: Mapped[int] = mapped_column(
        BigInteger,
        server_default=text("nextval('audit_log_seq_seq'::regclass)"),
        nullable=False,
    )
    tabla: Mapped[str] = mapped_column(String(100), nullable=False)
    registro_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    accion: Mapped[str] = mapped_column(String(60), nullable=False)
    usuario: Mapped[str | None] = mapped_column(String(255))
    timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )
    payload_old: Mapped[dict | None] = mapped_column(JSONB)
    payload_new: Mapped[dict | None] = mapped_column(JSONB)
    hash_prev: Mapped[str | None] = mapped_column(String(64))
    hash_current: Mapped[str | None] = mapped_column(String(64))
    # Sub-atom 5.A (migración audit_log_rls_001): propagación 3-way OR project_id + client_id
    # (nullable). Ejecutable 8 Pasada 16: declarados en el modelo — faltaban, así que alembic
    # check los marcaba como columnas+índices a eliminar (drift). index=True replica los
    # ix_audit_log_project_id / ix_audit_log_client_id creados por la migración.
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    client_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
