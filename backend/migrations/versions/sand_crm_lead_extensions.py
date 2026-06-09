"""sand_crm_lead_extensions

SAN-D MB-19.1 · CRM workflow comercial m13_commercial extension (ADR-041).

Cambios additive (cero breaking · todos los ADD COLUMN nullable):

1. ALTER leads · campos workflow CRM extendido:
   - estado_contacto VARCHAR(50) NULL CHECK 8 estados workflow comercial v2
     (mismo CheckConstraint que radar_leads.estado_contacto · coherencia
     dominio FASE 8.5 C2): nuevo · enviado · respondio · reunion_agendada
     · propuesta_enviada · ganado · descartado · no_interesa.
   - primer_contacto_at TIMESTAMP NULL · primer email/llamada timestamp.
   - fecha_perdida TIMESTAMP NULL · si estado_contacto = descartado/no_interesa.
   - razon_perdida VARCHAR(200) NULL · razón documentada lost.
   - fecha_conversion TIMESTAMP NULL · si estado_contacto = ganado.
   - convertido_a_proyecto_id UUID NULL FK projects.id · target conversion.
   - temperature_level INTEGER NULL · 1-7 mapping ENS Radar temperatura.
   - categoria_objetivo_ens VARCHAR(20) NULL · BASICA/MEDIA/ALTA target.
   - archetype_ens VARCHAR(50) NULL · arquetipo PYME existing M11.

2. ALTER proposals · revisions tracking extendido:
   - feedback_cliente TEXT NULL · feedback recibido cliente sobre revisión.
   - cambios_desde_anterior TEXT NULL · resumen diff vs revisión anterior.
   - superseded BOOLEAN NOT NULL DEFAULT FALSE · marca revisión obsoleta.
   - fecha_aceptacion TIMESTAMP NULL · cliente acepta propuesta.
   - agent_19_metadata JSONB NULL · metadata RedactorPropuestasAgent.

3. CREATE TABLE lead_stage_history · audit trail movements estado_contacto:
   Append-only log per transición · análogo billing_milestones audit pattern.

4. ALTER radar_leads · tracking auto-import M13:
   - imported_to_commercial_id UUID NULL FK leads.id · dedup auto-import
     ENS Radar→leads M13 (Celery beat MB-19.6).

NO drop columns existing · NO breaking changes · downgrade reversible.

Revision ID: sand_crm_lead_extensions
Revises: sand_retainer_health_001
Create Date: 2026-05-07
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "sand_crm_lead_extensions"
down_revision = "sand_retainer_health_001"
branch_labels = None
depends_on = None


# 8 estados workflow comercial v2 FASE 8.5 C2 · mismo CheckConstraint
# que radar_leads.estado_contacto (coherencia dominio comercial).
_VALID_ESTADOS_CONTACTO = (
    "nuevo",
    "enviado",
    "respondio",
    "reunion_agendada",
    "propuesta_enviada",
    "ganado",
    "descartado",
    "no_interesa",
)


def upgrade() -> None:
    # ──────────────────────────────────────────────────────────────
    # 1. ALTER leads · campos workflow CRM extendido
    # ──────────────────────────────────────────────────────────────
    with op.batch_alter_table("leads") as batch:
        batch.add_column(
            sa.Column("estado_contacto", sa.String(50), nullable=True)
        )
        batch.add_column(
            sa.Column(
                "primer_contacto_at",
                sa.TIMESTAMP(timezone=True),
                nullable=True,
            )
        )
        batch.add_column(
            sa.Column(
                "fecha_perdida",
                sa.TIMESTAMP(timezone=True),
                nullable=True,
            )
        )
        batch.add_column(
            sa.Column("razon_perdida", sa.String(200), nullable=True)
        )
        batch.add_column(
            sa.Column(
                "fecha_conversion",
                sa.TIMESTAMP(timezone=True),
                nullable=True,
            )
        )
        batch.add_column(
            sa.Column(
                "convertido_a_proyecto_id",
                UUID(as_uuid=True),
                sa.ForeignKey("projects.id"),
                nullable=True,
            )
        )
        batch.add_column(
            sa.Column("temperature_level", sa.Integer, nullable=True)
        )
        batch.add_column(
            sa.Column(
                "categoria_objetivo_ens", sa.String(20), nullable=True
            )
        )
        batch.add_column(
            sa.Column("archetype_ens", sa.String(50), nullable=True)
        )
        batch.create_check_constraint(
            "ck_leads_estado_contacto",
            f"estado_contacto IS NULL OR estado_contacto IN "
            f"{_VALID_ESTADOS_CONTACTO}",
        )
        batch.create_check_constraint(
            "ck_leads_temperature_range",
            "temperature_level IS NULL OR "
            "(temperature_level >= 1 AND temperature_level <= 7)",
        )
        batch.create_check_constraint(
            "ck_leads_categoria_objetivo_ens",
            "categoria_objetivo_ens IS NULL OR "
            "categoria_objetivo_ens IN ('BASICA', 'MEDIA', 'ALTA')",
        )

    op.create_index(
        "ix_leads_estado_contacto",
        "leads",
        ["estado_contacto"],
    )
    op.create_index(
        "ix_leads_temperature_level",
        "leads",
        ["temperature_level"],
    )
    op.create_index(
        "ix_leads_convertido_proyecto",
        "leads",
        ["convertido_a_proyecto_id"],
    )

    # Backfill estado_contacto desde columna existing 'estado' string
    # convención: 'nuevo' default → 'nuevo' estado_contacto.
    # Otros valores legacy quedan NULL (Marcos asigna manualmente).
    op.execute(
        "UPDATE leads SET estado_contacto = 'nuevo' "
        "WHERE estado = 'nuevo' AND estado_contacto IS NULL"
    )

    # ──────────────────────────────────────────────────────────────
    # 2. ALTER proposals · revisions tracking extendido
    # ──────────────────────────────────────────────────────────────
    with op.batch_alter_table("proposals") as batch:
        batch.add_column(
            sa.Column("feedback_cliente", sa.Text, nullable=True)
        )
        batch.add_column(
            sa.Column("cambios_desde_anterior", sa.Text, nullable=True)
        )
        batch.add_column(
            sa.Column(
                "superseded",
                sa.Boolean,
                nullable=False,
                server_default=sa.text("FALSE"),
            )
        )
        batch.add_column(
            sa.Column(
                "fecha_aceptacion",
                sa.TIMESTAMP(timezone=True),
                nullable=True,
            )
        )
        batch.add_column(
            sa.Column("agent_19_metadata", JSONB, nullable=True)
        )

    op.create_index(
        "ix_proposals_lead_active",
        "proposals",
        ["lead_id", "superseded"],
    )

    # ──────────────────────────────────────────────────────────────
    # 3. CREATE TABLE lead_stage_history · audit trail transiciones
    # ──────────────────────────────────────────────────────────────
    op.create_table(
        "lead_stage_history",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "lead_id",
            UUID(as_uuid=True),
            sa.ForeignKey("leads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "estado_anterior",
            sa.String(50),
            nullable=True,
        ),
        sa.Column(
            "estado_nuevo",
            sa.String(50),
            nullable=False,
        ),
        sa.Column(
            "cambiado_por_user_id",
            UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "notas",
            sa.Text,
            nullable=True,
        ),
        sa.Column(
            "metadata_jsonb",
            JSONB,
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"estado_nuevo IN {_VALID_ESTADOS_CONTACTO}",
            name="ck_lead_stage_history_estado_nuevo",
        ),
        sa.CheckConstraint(
            f"estado_anterior IS NULL OR estado_anterior IN "
            f"{_VALID_ESTADOS_CONTACTO}",
            name="ck_lead_stage_history_estado_anterior",
        ),
    )
    op.create_index(
        "ix_lead_stage_history_lead_recent",
        "lead_stage_history",
        ["lead_id", sa.text("created_at DESC")],
    )

    op.execute(
        "GRANT SELECT, INSERT ON lead_stage_history TO fulkro_app"
    )

    # ──────────────────────────────────────────────────────────────
    # 4. ALTER radar_leads · tracking auto-import M13
    # ──────────────────────────────────────────────────────────────
    with op.batch_alter_table("radar_leads") as batch:
        batch.add_column(
            sa.Column(
                "imported_to_commercial_id",
                UUID(as_uuid=True),
                sa.ForeignKey("leads.id", ondelete="SET NULL"),
                nullable=True,
            )
        )

    op.create_index(
        "ix_radar_leads_imported_commercial",
        "radar_leads",
        ["imported_to_commercial_id"],
    )


def downgrade() -> None:
    # 4. radar_leads
    op.drop_index(
        "ix_radar_leads_imported_commercial", table_name="radar_leads"
    )
    with op.batch_alter_table("radar_leads") as batch:
        batch.drop_column("imported_to_commercial_id")

    # 3. lead_stage_history
    op.execute(
        "REVOKE SELECT, INSERT ON lead_stage_history FROM fulkro_app"
    )
    op.drop_index(
        "ix_lead_stage_history_lead_recent", table_name="lead_stage_history"
    )
    op.drop_table("lead_stage_history")

    # 2. proposals
    op.drop_index("ix_proposals_lead_active", table_name="proposals")
    with op.batch_alter_table("proposals") as batch:
        batch.drop_column("agent_19_metadata")
        batch.drop_column("fecha_aceptacion")
        batch.drop_column("superseded")
        batch.drop_column("cambios_desde_anterior")
        batch.drop_column("feedback_cliente")

    # 1. leads
    for ix in (
        "ix_leads_convertido_proyecto",
        "ix_leads_temperature_level",
        "ix_leads_estado_contacto",
    ):
        op.drop_index(ix, table_name="leads")

    with op.batch_alter_table("leads") as batch:
        batch.drop_constraint(
            "ck_leads_categoria_objetivo_ens", type_="check"
        )
        batch.drop_constraint("ck_leads_temperature_range", type_="check")
        batch.drop_constraint("ck_leads_estado_contacto", type_="check")
        batch.drop_column("archetype_ens")
        batch.drop_column("categoria_objetivo_ens")
        batch.drop_column("temperature_level")
        batch.drop_column("convertido_a_proyecto_id")
        batch.drop_column("fecha_conversion")
        batch.drop_column("razon_perdida")
        batch.drop_column("fecha_perdida")
        batch.drop_column("primer_contacto_at")
        batch.drop_column("estado_contacto")
