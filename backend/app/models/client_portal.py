"""M21 Portal Cliente — usuarios, sesiones y auditoria (Sesion 8 Paso 3).

Portal persistente con login + password (SAN-E v3.MB-1.1 · TOTP off cliente
· ADR-046 v3). Marcos crea usuarios desde su cockpit. Separado de
`auth_users` (que es solo para Marcos con WebAuthn/TOTP).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    ForeignKey, String, Integer, Boolean, Text, Index, text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP, INET
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, FullMixin


class ClientUser(FullMixin, Base):
    """Usuario del portal cliente. Creado por Marcos desde cockpit."""

    __tablename__ = "client_users"

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"),
        nullable=False, index=True,
    )
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True,
    )
    password_hash: Mapped[str] = mapped_column(String(100), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dni: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # #7.5 · cargo del usuario portal (StepFirstUser lo recoge · antes se tiraba).
    cargo: Mapped[str | None] = mapped_column(String(150), nullable=True)
    # ADR-013 v3 single-user-RW · drop role/custom_role_description/scopes_jsonb.
    # Migration san_e_mb3_cleanup_m21_drop_role_columns elimina columns BD.
    # Estado
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
    )
    last_login: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    password_changed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    failed_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    created_by_marcos: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
    )
    deactivated_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )

    # SAN-E MB-8 atom 8.1 · WhatsApp opt-in (Q3.D hybrid)
    whatsapp_number: Mapped[str | None] = mapped_column(
        String(20), nullable=True,
    )
    whatsapp_verified_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    whatsapp_opt_in_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    whatsapp_verification_otp: Mapped[str | None] = mapped_column(
        String(8), nullable=True,
    )
    whatsapp_otp_sent_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )

    # SAN-E MB-9.bis atom 9.bis.1 · cookie consent state (Guía AEPD 2020).
    # ``consent_renewal_due`` is checked by Self-Monitoring atom 9.bis.6
    # (check_cookie_consent_renewal_24month).
    consent_functional: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )
    consent_analytics: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )
    consent_marketing: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )
    consent_timestamp: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    consent_renewal_due: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    consent_ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    consent_user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    # CLUSTER 6 Phase 6A · MFA opt-in flag.
    # Login gate cuando ``True``. El segundo factor se resuelve según
    # ``mfa_method`` (ver más abajo).
    mfa_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )

    # 2026-06-09 · MFA por CÓDIGO AL EMAIL (sustituye al TOTP "más rollo" para
    # el cliente · directiva Marcos). ``mfa_method``:
    #   - 'email' (default · nuevo): en login le enviamos un código de 6 dígitos
    #      a su email y lo teclea. NO necesita app autenticadora.
    #   - 'totp'  (legacy · compat): app autenticadora (ClientUserTotpSecret).
    mfa_method: Mapped[str] = mapped_column(
        String(10), nullable=False, default="email", server_default="email",
    )
    # Código de login transitorio (hash sha256 · NUNCA en claro), su caducidad,
    # nº de intentos y cuándo se envió (rate-limit del reenvío).
    mfa_email_code_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
    )
    mfa_email_code_expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    mfa_email_code_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
    )
    mfa_email_code_sent_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )

    __table_args__ = (
        Index(
            "uq_client_users_client_email",
            "client_id", "email", unique=True,
        ),
    )


class ClientUserTotpSecret(FullMixin, Base):
    """TOTP secret cliente · 1 secret per client_user (UNIQUE FK).

    Mirror admin ``auth_totp_secrets`` shape. ``verified=True`` activa
    login gate cuando ``client_users.mfa_enabled=True``.
    """

    __tablename__ = "client_user_totp_secrets"

    client_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("client_users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    secret: Mapped[str] = mapped_column(String(64), nullable=False)
    verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )


class ClientUserBackupCode(Base):
    """Backup codes single-use post-MFA confirm.

    10 codes generated post-confirm · hashed SHA-256 (single-use limit
    rules out bcrypt cost). ``used_at`` marks consumed.
    """

    __tablename__ = "client_user_backup_codes"
    __table_args__ = (
        Index(
            "ix_client_user_backup_codes_unused",
            "client_user_id",
            postgresql_where=text("used_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    client_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("client_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )


class ClientSession(FullMixin, Base):
    """Sesion JWT del cliente (TTL 12h)."""

    __tablename__ = "client_sessions"

    client_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("client_users.id"),
        nullable=False, index=True,
    )
    jwt_jti: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True,
    )
    jwt_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, index=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    last_activity: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True,
    )
    # Acceso de soporte trazado (impersonation READ-ONLY admin → portal cliente).
    # is_support_access marca la sesión como soporte; el READ-ONLY se enforce en
    # authenticate_request (chokepoint app-level) via claim 'support' del JWT.
    # support_admin_user_id = a qué admin pertenece (atribución · audit_log es la
    # prueba legal inmutable separada).
    is_support_access: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false",
    )
    support_admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="SET NULL"),
        nullable=True,
    )


class ClientUserAudit(Base):
    """Log append-only de acciones del portal cliente.

    SAN-D MB-14.1 · hash chain backward compat (DEC-MB14-1 ADR-038
    Opción A): columnas chain extendidas nullable. Rows pre-MB-14
    con ``chain_index NULL`` legítimos · sin hash. AuditLogService
    nuevo escribe rows con hash chain. Verificación integrity opera
    sólo sobre rows con ``chain_index NOT NULL``.
    """

    __tablename__ = "client_user_audit"
    __table_args__ = (
        Index(
            "idx_client_user_audit_current_hash",
            "current_hash",
        ),
        Index(
            "ix_client_audit_action_type",
            "action_type",
        ),
        Index(
            "ix_client_audit_project_chain",
            "project_id", "chain_index",
        ),
        Index(
            "ix_client_user_audit_action",
            "action",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    client_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("client_users.id"),
        nullable=True, index=True,
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True,
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    # login_success | login_failure | password_change | account_locked |
    # document_downloaded | evidence_uploaded | session_revoked |
    # user_created | user_deactivated | role_changed |
    # first_access_completed
    # (SAN-E v3.MB-1.1 · totp_enabled/totp_disabled removed · TOTP off cliente)
    metadata_jsonb: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
    )
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
    )
    # SAN-D MB-14.1 hash chain extension (DEC-MB14-1 Opción A)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
    )
    chain_index: Mapped[int | None] = mapped_column(nullable=True)
    prev_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # SAN-E v3.MB-1.1.D · NO unique global · audit chain integrity is per-project,
    # enforced by audit_log_service.verify_chain_integrity()
    current_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
    )
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    action_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
