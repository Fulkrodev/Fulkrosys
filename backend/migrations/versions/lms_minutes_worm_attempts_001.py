"""LMS/Actas: archivado WORM (minio://) + límite de intentos de quiz (§5.5 audit C6).

Wave C6 (auditoría 2026-06-14, §5.5):

1) ARCHIVADO WORM. Las evidencias E-502/E-503 (LMS) y E-005 (actas de comité) se
   escribían SOLO en el FS local (``var/documents_lms`` / ``var/documents_minutes``).
   La integridad ya estaba garantizada por el hash SHA-256 (y, en actas, la firma
   Ed25519) persistidos en la fila. Lo que faltaba era la INMUTABILIDAD de
   almacenamiento (Object Lock COMPLIANCE) para el auditor ENAC.

   Este cambio NO altera el contrato de lectura existente: el servicio sigue
   escribiendo el fichero local (``e50x_path`` / ``docx_path`` / ``pdf_path``) y
   ADEMÁS archiva una copia best-effort al bucket WORM (``fulkro-evidence-worm``),
   guardando la URI canónica ``minio://{bucket}/{key}`` en columnas NUEVAS. Si MinIO
   no está configurado (dev), las columnas quedan NULL y el flujo no se rompe — mismo
   patrón que ``m07_evidence._archive_clean_evidence_to_worm``.

   Columnas añadidas:
   - ``lms_assignments.e502_worm_uri``  (String(500), nullable)
   - ``lms_assignments.e503_worm_uri``  (String(500), nullable)
   - ``committee_meetings.docx_worm_uri`` (String(500), nullable)
   - ``committee_meetings.pdf_worm_uri``  (String(500), nullable)

2) LÍMITE DE INTENTOS DE QUIZ (LMS). ``submit_quiz`` aceptaba reenvíos ilimitados
   (estados {in_progress, assigned, failed, completed}) sin contador de intentos, de
   modo que un asistente podía reintentar el cuestionario indefinidamente hasta
   aprobar. Se añade un contador ``intentos`` (Integer, default 0) que el servicio
   incrementa en cada envío y compara contra ``max_attempts`` (definido por curso en
   el catálogo, con fallback por defecto). Al alcanzar el límite, el envío se rechaza
   con un mensaje claro.

   Columna añadida:
   - ``lms_assignments.intentos`` (Integer, NOT NULL, server_default '0')

Aditiva e idempotente. NO toca datos existentes.

Revision ID: lms_minutes_worm_attempts_001
Revises: anon_consent_rls_001
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "lms_minutes_worm_attempts_001"
down_revision: str = "anon_consent_rls_001"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    # 1) WORM URIs (LMS)
    if not _has_column("lms_assignments", "e502_worm_uri"):
        op.add_column(
            "lms_assignments",
            sa.Column("e502_worm_uri", sa.String(length=500), nullable=True),
        )
    if not _has_column("lms_assignments", "e503_worm_uri"):
        op.add_column(
            "lms_assignments",
            sa.Column("e503_worm_uri", sa.String(length=500), nullable=True),
        )

    # 1) WORM URIs (actas)
    if not _has_column("committee_meetings", "docx_worm_uri"):
        op.add_column(
            "committee_meetings",
            sa.Column("docx_worm_uri", sa.String(length=500), nullable=True),
        )
    if not _has_column("committee_meetings", "pdf_worm_uri"):
        op.add_column(
            "committee_meetings",
            sa.Column("pdf_worm_uri", sa.String(length=500), nullable=True),
        )

    # 2) Contador de intentos de quiz (LMS)
    if not _has_column("lms_assignments", "intentos"):
        op.add_column(
            "lms_assignments",
            sa.Column(
                "intentos",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )


def downgrade() -> None:
    if _has_column("lms_assignments", "intentos"):
        op.drop_column("lms_assignments", "intentos")
    if _has_column("committee_meetings", "pdf_worm_uri"):
        op.drop_column("committee_meetings", "pdf_worm_uri")
    if _has_column("committee_meetings", "docx_worm_uri"):
        op.drop_column("committee_meetings", "docx_worm_uri")
    if _has_column("lms_assignments", "e503_worm_uri"):
        op.drop_column("lms_assignments", "e503_worm_uri")
    if _has_column("lms_assignments", "e502_worm_uri"):
        op.drop_column("lms_assignments", "e502_worm_uri")
