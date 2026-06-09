"""P0.1 ENS Radar · ALTER ccn_certificados ADD cols para scraper Playwright.

ADD columns (additive only · backwards-compat):
- cert_id VARCHAR(50) NULL  → id estable del certificado (idempotencia upsert)
- cif_norm VARCHAR(20) NULL → CIF normalizado para match O(1)
- website VARCHAR(500) NULL → URL corporativa (extraDataSiteURL)
- scraped_at TIMESTAMP NULL → marca temporal del scrape

ADD index idx_ccn_cif_norm + UNIQUE uq_ccn_cert_id (idempotencia).

Revision: ccn_certs_scraper_cols_001
Down: esignature_canvas_tier1_001
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "ccn_certs_scraper_cols_001"
down_revision: Union[str, None] = "esignature_canvas_tier1_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ccn_certificados",
        sa.Column("cert_id", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "ccn_certificados",
        sa.Column("cif_norm", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "ccn_certificados",
        sa.Column("website", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "ccn_certificados",
        sa.Column("scraped_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "idx_ccn_cif_norm", "ccn_certificados", ["cif_norm"], unique=False
    )
    op.create_unique_constraint(
        "uq_ccn_cert_id", "ccn_certificados", ["cert_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_ccn_cert_id", "ccn_certificados", type_="unique")
    op.drop_index("idx_ccn_cif_norm", table_name="ccn_certificados")
    op.drop_column("ccn_certificados", "scraped_at")
    op.drop_column("ccn_certificados", "website")
    op.drop_column("ccn_certificados", "cif_norm")
    op.drop_column("ccn_certificados", "cert_id")
