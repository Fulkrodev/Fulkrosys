"""san_e_mb6_atom6_evidence_antivirus_scan

Revision ID: 9d1b4035222b
Revises: fb5ef0575945
Create Date: 2026-05-11

SAN-E v3.MB-6 atom 6 · ClamAV antivirus scan cliente uploads.
Gap A27 ENS Anexo II RD 311/2022 · mp.s.5 "Proteccion frente al codigo danino".

7 decisiones Marcos cement:
- Q1 A · clamav docker-compose sidecar (clamav/clamav:stable Cisco-Talos GPL2)
- Q2 B · quarantine + admin review (compliance + false-positive recoverable)
- Q3 B · async Celery scan_evidence_file_task (UX <1s)
- Q4 B · cliente uploads scope (m07_evidence ingestion_service)
- Q5 A · 5 scan_status values (clean/scanning/infected/error/quarantined)
- Q6 bonus · WIDEN ck_alert_queue_category +antivirus_infected +antivirus_scan_error
- Q7 NO MixinA evidence (tecnico antivirus · NO decisional)

Cambios:
1. ALTER evidence ADD 5 cols:
   - scan_status (String 20 default 'scanning' · CHECK 5 enum)
   - scan_started_at (TIMESTAMP tz NULL)
   - scan_completed_at (TIMESTAMP tz NULL)
   - scan_engine_version (String 80 NULL · "ClamAV-1.X.X")
   - scan_result_jsonb (JSONB NULL · virus_name + signature_db_version + duration_ms + error_msg)
2. CHECK ck_evidence_scan_status (5 enum)
3. Index parcial idx_evidence_scan_infected WHERE scan_status='infected'
4. Index parcial idx_evidence_scan_quarantined WHERE scan_status='quarantined'
5. WIDEN ck_alert_queue_category +'antivirus_infected' +'antivirus_scan_error'
6. Backfill existing evidence rows scan_status='clean' (trusted legacy pre-mp.s.5)

Reversible · downgrade limpio.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = '9d1b4035222b'
down_revision: Union[str, None] = 'fb5ef0575945'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_SCAN_STATUSES = ("clean", "scanning", "infected", "error", "quarantined")

_ALERT_CATEGORIES_OLD = (
    "bienal_art31",
    "payment_overdue_aapp",
    "client_inactivity",
    "evidence_stale",
    "retainer_overdue",
    "milestone_due",
    "workflow_blocked",
    "audit_due",
    "rgpd_72h",
    "contract_milestone",
    "renewal_due",
    "dpc_due",
    "incident_critical_pending_route",
    "incident_ccn_cert_overdue",
    "other",
)

_ALERT_CATEGORIES_NEW = _ALERT_CATEGORIES_OLD + (
    "antivirus_infected",
    "antivirus_scan_error",
)


def upgrade() -> None:
    # 1. ALTER evidence ADD scan cols
    op.add_column(
        "evidence",
        sa.Column(
            "scan_status",
            sa.String(20),
            nullable=False,
            server_default="scanning",
        ),
    )
    op.add_column(
        "evidence",
        sa.Column(
            "scan_started_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "evidence",
        sa.Column(
            "scan_completed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "evidence",
        sa.Column("scan_engine_version", sa.String(80), nullable=True),
    )
    op.add_column(
        "evidence",
        sa.Column("scan_result_jsonb", JSONB, nullable=True),
    )

    # 2. CHECK scan_status (5 enum)
    status_values = ", ".join(f"'{v}'" for v in _SCAN_STATUSES)
    op.create_check_constraint(
        "ck_evidence_scan_status",
        "evidence",
        f"scan_status IN ({status_values})",
    )

    # 3-4. Indexes parciales (infected + quarantined)
    op.create_index(
        "idx_evidence_scan_infected",
        "evidence",
        ["project_id", "scan_status"],
        unique=False,
        postgresql_where=sa.text("scan_status = 'infected'"),
    )
    op.create_index(
        "idx_evidence_scan_quarantined",
        "evidence",
        ["project_id", "scan_status"],
        unique=False,
        postgresql_where=sa.text("scan_status = 'quarantined'"),
    )

    # 5. WIDEN ck_alert_queue_category (+2 antivirus categorias)
    op.drop_constraint(
        "ck_alert_queue_category",
        "alert_queue",
        type_="check",
    )
    new_values = ", ".join(f"'{v}'" for v in _ALERT_CATEGORIES_NEW)
    op.create_check_constraint(
        "ck_alert_queue_category",
        "alert_queue",
        f"category IN ({new_values})",
    )

    # 6. Backfill legacy evidence rows scan_status='clean' (trusted pre-mp.s.5).
    # Justificacion auditor ENAC: estos uploads existieron antes de la
    # implementacion mp.s.5 y son confianza legacy. Future uploads
    # transitionan via scanning -> clean/infected/error/quarantined.
    op.execute(
        "UPDATE evidence SET scan_status = 'clean', "
        "scan_completed_at = COALESCE(updated_at, created_at), "
        "scan_engine_version = 'legacy-pre-mp.s.5' "
        "WHERE scan_status = 'scanning'"
    )


def downgrade() -> None:
    # Restore alert_queue CHECK
    op.drop_constraint(
        "ck_alert_queue_category",
        "alert_queue",
        type_="check",
    )
    old_values = ", ".join(f"'{v}'" for v in _ALERT_CATEGORIES_OLD)
    op.create_check_constraint(
        "ck_alert_queue_category",
        "alert_queue",
        f"category IN ({old_values})",
    )

    op.drop_index(
        "idx_evidence_scan_quarantined",
        table_name="evidence",
    )
    op.drop_index(
        "idx_evidence_scan_infected",
        table_name="evidence",
    )
    op.drop_constraint(
        "ck_evidence_scan_status",
        "evidence",
        type_="check",
    )
    op.drop_column("evidence", "scan_result_jsonb")
    op.drop_column("evidence", "scan_engine_version")
    op.drop_column("evidence", "scan_completed_at")
    op.drop_column("evidence", "scan_started_at")
    op.drop_column("evidence", "scan_status")
