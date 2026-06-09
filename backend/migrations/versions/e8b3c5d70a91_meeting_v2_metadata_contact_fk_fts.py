"""meeting_v2: ampliar exploratory_meetings (FASE 7.A.1).

Revision ID: e8b3c5d70a91
Revises: d4e7a9b1f632
Create Date: 2026-04-30 09:00:00.000000

ADR-024 (supersedes ADR-004 videocall propio):
  Reuniones externas con plataformas (Google Meet/Zoom/Teams/presencial)
  + interlocutor M30 ContactQuickPicker + notas markdown rich + SSE A18
  stream + workflow status (scheduled/in_progress/completed/cancelled).

Schema delta (12 columnas NEW):
  - ``project_id`` UUID FK projects(id) ON DELETE SET NULL
    (meeting puede ser pre-proyecto lead o post-proyecto follow-up)
  - ``title`` VARCHAR(200) NOT NULL DEFAULT ''
  - ``platform`` VARCHAR(20) NULL — google_meet/zoom/teams/presencial/other
  - ``meeting_url`` VARCHAR(500) NULL — link plataforma externa
  - ``etapa_k`` VARCHAR(10) NULL — K.1 .. K.6 (workflow ENS)
  - ``interlocutor_contact_id`` UUID FK client_contacts(id) ON DELETE SET NULL
    (M30 cross-motor — H7.A.1 ADR-023 dominio compartido)
  - ``notes_markdown`` TEXT NULL — notas Marcos rich format
  - ``notes_html_sanitized`` TEXT NULL — render server-side bleach (XSS)
  - ``sse_session_id`` UUID NULL — link con A18 stream session
  - ``status`` VARCHAR(20) NOT NULL DEFAULT 'scheduled'
    CHECK IN ('scheduled','in_progress','completed','cancelled')
  - ``completed_at`` TIMESTAMPTZ NULL
  - ``cancelled_at`` TIMESTAMPTZ NULL

Indexes:
  - ``ix_exploratory_meetings_contact_id`` ON (interlocutor_contact_id)
    (filtros vista histórica por contacto + cleanup orphans)
  - ``ix_exploratory_meetings_status`` ON (status)
    (lista filtered scheduled/completed)
  - ``ix_exploratory_meetings_notes_fts`` GIN to_tsvector('spanish', notes_markdown)
    (full-text search admin)
  - ``ix_exploratory_meetings_project_id`` ON (project_id)
    WHERE project_id IS NOT NULL (vista histórica por proyecto)

Audit triggers: ``tg_audit_exploratory_meetings`` reusable
fn_audit_track shared canon (existing si tabla creada con audit
trigger M27 lifecycle migration).

CHECK constraints:
  - platform IN whitelist
  - etapa_k IN whitelist
  - status IN whitelist

Política TODO-DB-DRIFT-001: revision SIN ``--autogenerate`` (no
detecta GIN op_classes + CHECK enum + audit triggers).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "e8b3c5d70a91"
down_revision: Union[str, None] = "d4e7a9b1f632"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_PLATFORMS = ("google_meet", "zoom", "teams", "presencial", "jitsi", "other")
_ETAPAS_K = ("K.1", "K.2", "K.3", "K.4", "K.5", "K.6", "other")
_STATUSES = ("scheduled", "in_progress", "completed", "cancelled")


def upgrade() -> None:
    # ====================================================================
    # 1. ADD COLUMNS (12 NEW)
    # ====================================================================
    op.add_column(
        "exploratory_meetings",
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
            comment=(
                "FK projects opcional. Meeting puede ser pre-proyecto "
                "(lead K.1-K.4) o post-proyecto (K.5-K.6 retainer)."
            ),
        ),
    )
    op.add_column(
        "exploratory_meetings",
        sa.Column(
            "title", sa.String(200),
            nullable=False, server_default="",
        ),
    )
    op.add_column(
        "exploratory_meetings",
        sa.Column("platform", sa.String(20), nullable=True),
    )
    op.add_column(
        "exploratory_meetings",
        sa.Column("meeting_url", sa.String(500), nullable=True),
    )
    op.add_column(
        "exploratory_meetings",
        sa.Column("etapa_k", sa.String(10), nullable=True),
    )
    op.add_column(
        "exploratory_meetings",
        sa.Column(
            "interlocutor_contact_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("client_contacts.id", ondelete="SET NULL"),
            nullable=True,
            comment=(
                "FK client_contacts.id (M30) si interlocutor es contacto "
                "registrado. Auto-log interaction='meeting_attended' al "
                "complete_meeting si presente."
            ),
        ),
    )
    op.add_column(
        "exploratory_meetings",
        sa.Column("notes_markdown", sa.Text(), nullable=True),
    )
    op.add_column(
        "exploratory_meetings",
        sa.Column("notes_html_sanitized", sa.Text(), nullable=True),
    )
    op.add_column(
        "exploratory_meetings",
        sa.Column(
            "sse_session_id", postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="UUID generado al iniciar SSE stream A18 update.",
        ),
    )
    op.add_column(
        "exploratory_meetings",
        sa.Column(
            "status", sa.String(20),
            nullable=False, server_default="scheduled",
        ),
    )
    op.add_column(
        "exploratory_meetings",
        sa.Column(
            "completed_at", postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "exploratory_meetings",
        sa.Column(
            "cancelled_at", postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )

    # ====================================================================
    # 2. CHECK constraints
    # ====================================================================
    platforms_in = ", ".join(f"'{p}'" for p in _PLATFORMS)
    etapas_in = ", ".join(f"'{e}'" for e in _ETAPAS_K)
    statuses_in = ", ".join(f"'{s}'" for s in _STATUSES)
    op.execute(
        f"ALTER TABLE exploratory_meetings ADD CONSTRAINT "
        f"ck_exploratory_meetings_platform CHECK "
        f"(platform IS NULL OR platform IN ({platforms_in}))"
    )
    op.execute(
        f"ALTER TABLE exploratory_meetings ADD CONSTRAINT "
        f"ck_exploratory_meetings_etapa_k CHECK "
        f"(etapa_k IS NULL OR etapa_k IN ({etapas_in}))"
    )
    op.execute(
        f"ALTER TABLE exploratory_meetings ADD CONSTRAINT "
        f"ck_exploratory_meetings_status CHECK "
        f"(status IN ({statuses_in}))"
    )

    # ====================================================================
    # 3. INDEXES
    # ====================================================================
    op.create_index(
        "ix_exploratory_meetings_contact_id",
        "exploratory_meetings",
        ["interlocutor_contact_id"],
    )
    op.create_index(
        "ix_exploratory_meetings_status",
        "exploratory_meetings",
        ["status"],
    )
    op.create_index(
        "ix_exploratory_meetings_project_id",
        "exploratory_meetings",
        ["project_id"],
        postgresql_where=sa.text("project_id IS NOT NULL"),
    )
    op.execute(
        "CREATE INDEX ix_exploratory_meetings_notes_fts "
        "ON exploratory_meetings "
        "USING gin (to_tsvector('spanish', coalesce(notes_markdown, '')))"
    )

    # ====================================================================
    # 4. Audit trigger (fn_audit_track shared canon)
    # ====================================================================
    op.execute(
        "CREATE TRIGGER tg_audit_exploratory_meetings "
        "AFTER INSERT OR UPDATE OR DELETE ON exploratory_meetings "
        "FOR EACH ROW EXECUTE FUNCTION fn_audit_track();"
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS tg_audit_exploratory_meetings "
        "ON exploratory_meetings"
    )

    op.execute("DROP INDEX IF EXISTS ix_exploratory_meetings_notes_fts")
    op.drop_index(
        "ix_exploratory_meetings_project_id",
        table_name="exploratory_meetings",
    )
    op.drop_index(
        "ix_exploratory_meetings_status",
        table_name="exploratory_meetings",
    )
    op.drop_index(
        "ix_exploratory_meetings_contact_id",
        table_name="exploratory_meetings",
    )

    for ck in (
        "ck_exploratory_meetings_platform",
        "ck_exploratory_meetings_etapa_k",
        "ck_exploratory_meetings_status",
    ):
        op.execute(
            f"ALTER TABLE exploratory_meetings DROP CONSTRAINT IF EXISTS {ck}"
        )

    for col in (
        "cancelled_at",
        "completed_at",
        "status",
        "sse_session_id",
        "notes_html_sanitized",
        "notes_markdown",
        "interlocutor_contact_id",
        "etapa_k",
        "meeting_url",
        "platform",
        "title",
        "project_id",
    ):
        op.drop_column("exploratory_meetings", col)
