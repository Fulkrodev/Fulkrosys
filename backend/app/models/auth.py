"""Auth models — users, WebAuthn credentials, TOTP, sessions, login attempts.

Single-user platform (Marcos). Tables prefixed with ``auth_`` to avoid clashing
with existing motor tables. No RLS on auth_* tables — auth data is global.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, LargeBinary, String, text
from sqlalchemy.dialects.postgresql import INET, JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, FullMixin, TimestampMixin, UUIDPrimaryKeyMixin


class User(FullMixin, Base):
    __tablename__ = "auth_users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="owner",
        server_default=text("'owner'"),
        doc=(
            "Identidad invariante del usuario. Valores en "
            "backend.app.auth.constants.ALLOWED_ROLES: owner, "
            "client_user, partner_senior, pentester_external, introducer. "
            "Capabilities operacionales viven en "
            "Settings, no aquí (ADR-015)."
        ),
    )
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    locked_until: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    webauthn_credentials: Mapped[list["WebAuthnCredential"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    totp_secret: Mapped["TOTPSecret | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    sessions: Mapped[list["Session"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class WebAuthnCredential(FullMixin, Base):
    __tablename__ = "auth_webauthn_credentials"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False
    )
    credential_id: Mapped[bytes] = mapped_column(LargeBinary, unique=True, nullable=False)
    public_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    sign_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    transports: Mapped[list | None] = mapped_column(JSONB)
    device_name: Mapped[str | None] = mapped_column(String(255))
    last_used_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    user: Mapped["User"] = relationship(back_populates="webauthn_credentials")


class TOTPSecret(FullMixin, Base):
    __tablename__ = "auth_totp_secrets"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    secret: Mapped[str] = mapped_column(String(64), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    user: Mapped["User"] = relationship(back_populates="totp_secret")


class Session(FullMixin, Base):
    __tablename__ = "auth_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False
    )
    jti: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(String(500))

    user: Mapped["User"] = relationship(back_populates="sessions")


class LoginAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Sliding-window log of login attempts for rate limiting.

    One row per attempt. Query window:
        SELECT COUNT(*) FROM auth_login_attempts
         WHERE ip_address = :ip
           AND created_at > NOW() - INTERVAL '15 minutes'
    """

    __tablename__ = "auth_login_attempts"

    email: Mapped[str | None] = mapped_column(String(255))
    ip_address: Mapped[str | None] = mapped_column(INET)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    reason: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(500))
