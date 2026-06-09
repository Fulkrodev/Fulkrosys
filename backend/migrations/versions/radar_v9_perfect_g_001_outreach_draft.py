"""radar_v9_perfect_g_001 · Bloque G outreach draft assist columns radar_leads.

Mega-Atom RADAR-V9-PERFECT Fase 1.A · Marcos approve cement 2026-05-26.
Persiste el draft generado por backend (deterministic templates +
optional LLM personalization) para audit trail + UI "save/restore"
sin re-generar (re-fetch LLM cost).

Campos additive a radar_leads (all nullable · backwards compat):
- last_outreach_draft_subject VARCHAR(300) · subject line del email
- last_outreach_draft_body TEXT · body completo (markdown plaintext)
- last_outreach_draft_tier VARCHAR(30) · tier semantico que generó el
  draft (ardiendo, ardiendo_sostenido, vence_pronto_oferta, caliente,
  renovacion_proxima, tibio, ya_certificada · espeja temperatura pero
  desacoplado por audit trail si tier shifts post-draft generation)
- last_outreach_draft_at TIMESTAMP · timestamp generación
- last_outreach_draft_model VARCHAR(50) · 'deterministic_template' si
  no se invocó LLM · model name (claude-sonnet-4-5) si LLM personalization

NO conflicto con campos existing:
- mensaje_primer_contacto TEXT · pipeline LLM populated (dossier step)
- email_redactado TEXT · 8.5.C2 manual editable field
- dossier_completo TEXT · narrativa LLM pipeline
- notas_marcos TEXT · audit
- notas_privadas TEXT · privadas no expuestas cliente

last_outreach_draft_* es el NUEVO campo on-demand generated via UI
"Generar borrador" button · separado de pipeline-generated fields para:
1. No sobrescribir pipeline-populated message_primer_contacto
2. Tracking timestamp generación específico
3. Soporte regeneration sin perder previous draft (overwrite policy)

NO index: writes son point-by-point per lead · selects por lead_id ya
indexed via PK. Future-X si UI query patterns demand.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "radar_v9_perfect_g_001"
down_revision = "radar_v9_perfect_c_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "radar_leads",
        sa.Column("last_outreach_draft_subject", sa.String(300), nullable=True),
    )
    op.add_column(
        "radar_leads",
        sa.Column("last_outreach_draft_body", sa.Text(), nullable=True),
    )
    op.add_column(
        "radar_leads",
        sa.Column("last_outreach_draft_tier", sa.String(30), nullable=True),
    )
    op.add_column(
        "radar_leads",
        sa.Column(
            "last_outreach_draft_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "radar_leads",
        sa.Column("last_outreach_draft_model", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("radar_leads", "last_outreach_draft_model")
    op.drop_column("radar_leads", "last_outreach_draft_at")
    op.drop_column("radar_leads", "last_outreach_draft_tier")
    op.drop_column("radar_leads", "last_outreach_draft_body")
    op.drop_column("radar_leads", "last_outreach_draft_subject")
