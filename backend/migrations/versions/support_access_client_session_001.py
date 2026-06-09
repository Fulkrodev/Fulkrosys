"""Acceso de soporte trazado · client_sessions += is_support_access + support_admin_user_id.

Impersonation READ-ONLY de soporte (admin → portal cliente · ADR-013 doble pool).
La sesión de soporte es un ClientUser del cliente X marcada is_support_access=True
+ a qué admin pertenece (support_admin_user_id). El READ-ONLY se enforce en
``authenticate_request`` (chokepoint app-level · main.py dependencies) leyendo el
claim ``support`` del JWT; estas columnas son el rastro en BD + revoke + atribución
operativa. La prueba legal inmutable (art.15 RGPD) va en ``audit_log`` (R6).

Additive · sin GRANT nuevo (client_sessions ya concede a fulkro_app · las columnas
nuevas heredan el grant de tabla).

up: ALTER client_sessions ADD is_support_access (bool · default false) +
    support_admin_user_id (UUID · FK auth_users · ON DELETE SET NULL · nullable).
down: drop ambas columnas.

Revision ID: support_access_client_session_001
Revises: precliente_consent_001
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "support_access_client_session_001"
down_revision = "precliente_consent_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "client_sessions",
        sa.Column(
            "is_support_access", sa.Boolean(), nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "client_sessions",
        sa.Column(
            "support_admin_user_id", UUID(as_uuid=True),
            sa.ForeignKey("auth_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("client_sessions", "support_admin_user_id")
    op.drop_column("client_sessions", "is_support_access")
