"""san_b_contract_scan_window_dedicated_jsonb

Revision ID: 1abd530a7869
Revises: 68c039a64829
Create Date: 2026-05-04 16:01:04.990884

Adds dedicated JSONB column ``contracts.scan_window`` to host
maintenance/scan window configuration per contract. M08 verification
scope_deriver consumes this when populating verification_runs scope.

Format ScanWindow (validado Pydantic en m14_contracts/schemas.py):
  {
    "horario_inicio": "HH:MM",
    "horario_fin": "HH:MM",
    "tz": "Europe/Madrid",
    "dias_ok": ["mon","tue","wed","thu","fri","sat","sun"],
    "dias_bloqueados": [],
    "fechas_bloqueadas": []
  }

NULL means "no contract-specific window · scope_deriver fallback default".
0 data loss · column nullable · existing rows untouched.

Refs: SAN-B.MB-3.bis.3 · cierre TODO-M8-G3 backlog formal
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '1abd530a7869'
down_revision: Union[str, None] = '68c039a64829'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "contracts",
        sa.Column(
            "scan_window",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("contracts", "scan_window")
