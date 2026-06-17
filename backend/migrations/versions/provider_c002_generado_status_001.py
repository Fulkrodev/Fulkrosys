"""m14 · provider_c002.status add 'generado' (M8 · C-002 genera doc real ≠ firma)

Antes ``generate_c002`` ponía ``status='firmado'`` SIN producir documento (firma
fingida · hueco de trazabilidad ENS/ENAC). Ahora genera la adenda E-604 real
(DOCX + MinIO + ProviderAddendum) y el estado pasa a 'generado' — la firma real
('firmado') es un paso aparte sobre la adenda. Esta migración amplía el CHECK de
``provider_c002.status`` para admitir 'generado'.

Revision ID: provider_c002_generado_status_001
Revises: ens_measures_embedding_001
Create Date: 2026-06-17
"""
from __future__ import annotations

from alembic import op

revision = "provider_c002_generado_status_001"
down_revision = "ens_measures_embedding_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE provider_c002 DROP CONSTRAINT IF EXISTS ck_provider_c002_status")
    op.execute(
        "ALTER TABLE provider_c002 ADD CONSTRAINT ck_provider_c002_status "
        "CHECK (status IN ('pendiente','generado','firmado','no_aplica','revocado'))"
    )


def downgrade() -> None:
    # Normaliza filas 'generado' a 'pendiente' antes de re-imponer el CHECK viejo.
    op.execute("UPDATE provider_c002 SET status = 'pendiente' WHERE status = 'generado'")
    op.execute("ALTER TABLE provider_c002 DROP CONSTRAINT IF EXISTS ck_provider_c002_status")
    op.execute(
        "ALTER TABLE provider_c002 ADD CONSTRAINT ck_provider_c002_status "
        "CHECK (status IN ('pendiente','firmado','no_aplica','revocado'))"
    )
