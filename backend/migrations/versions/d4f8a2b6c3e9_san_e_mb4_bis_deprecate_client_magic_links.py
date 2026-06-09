"""san_e_mb4_bis_deprecate_client_magic_links

SAN-E v3.MB-4.bis · ADR-020 NEW · Cliente in-portal only:
- ADD COLUMN deprecated_for_v3 BOOLEAN para marcar magic_links cliente-facing
- UPDATE flag para 21 purposes deprecated v3 (cliente con cuenta portal
  realiza in-portal · NO recibe magic links)
- NO revoca activos (preservar links productivos durante período transición)

Hard-revoke diferido a atom posterior (MB-4.bis4) tras período migración.

Revision ID: d4f8a2b6c3e9
Revises: f1d3a7c9b2e4
Create Date: 2026-05-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4f8a2b6c3e9"
down_revision: Union[str, None] = "f1d3a7c9b2e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# 21 purposes cliente-facing post-cuenta-portal v3 · ADR-020
DEPRECATED_PURPOSES_V3 = [
    "primer_acceso_cliente",
    "aprobacion_acta",
    "aprobacion_obligacion",
    "invitacion_reunion",
    "solicitud_informacion",
    "aprobacion_factura",
    "consentimiento_tratamiento_datos",
    "confirmacion_conformidad",
    "descarga_certificado_conformidad",
    "reporte_trimestral",
    "reporte_anual",
    "retainer_welcome",
    "normativa_alert_critical",
    "oferta_retainer",
    "reconsideracion_retainer",
    "renewal_campaign_details",
    "validacion_cambio_alcance",
    "aceptacion_riesgo_residual",
    "votacion_comite_seguridad",
    "encuesta_satisfaccion_nps",
    "comunicacion_incidente_seguridad",
]


def upgrade() -> None:
    # ── ADD COLUMN deprecated_for_v3 (soft mark · audit history preserved) ──
    op.add_column(
        "magic_links",
        sa.Column(
            "deprecated_for_v3",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # ── UPDATE flag para purposes cliente-facing v3 ──
    purposes_sql = ", ".join(f"'{p}'" for p in DEPRECATED_PURPOSES_V3)
    op.execute(f"""
        UPDATE magic_links
        SET deprecated_for_v3 = true
        WHERE tipo_operacion IN ({purposes_sql});
    """)

    # ── Index para queries filter deprecated ──
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_magic_links_deprecated_for_v3 "
        "ON magic_links (deprecated_for_v3) WHERE deprecated_for_v3 = true;"
    )

    # NOTA: NO revoca activos (revocado = false intacto · expira_at intacto)
    # Hard-revoke diferido a atom MB-4.bis4 tras período transición · evita
    # romper UX cliente con links activos en email durante migración.


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_magic_links_deprecated_for_v3;")
    op.drop_column("magic_links", "deprecated_for_v3")
