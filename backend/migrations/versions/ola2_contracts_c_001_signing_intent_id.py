"""ola2_contracts_c_signing_intent_id (M-OLA2-C · #43)

Revision ID: ola2_contracts_c_001
Revises: ola2_contracts_a_001
Create Date: 2026-06-03

Ola 2 (#43 · firma del contrato comercial con canvas Ed25519). Migración
**additive** y **nullable** (segura sobre filas existentes):

- ``contracts.signing_intent_id`` (UUID, FK → signing_intents.id, ON DELETE
  SET NULL) → puente Contract → SigningIntent (m05). El intent lleva el
  ``documento_sha256`` del contrato como ``document_hash_sha256`` y la firma
  canvas Ed25519 + hash chain vive en signing_events. El reverso (intent →
  contract) ya existe gratis vía ``SigningIntent.signable_ref_id`` +
  ``signable_ref_type='contract'``; esta columna da el sentido directo.

Scope-only (política TODO-DB-DRIFT-001 · sin autogenerate). Nullable →
``fulkro_app`` hereda el GRANT de tabla (sin GRANT extra por columna).
Reversible. ``signing_intents`` ya existe (migración 123920e86153).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "ola2_contracts_c_001"
down_revision: Union[str, None] = "ola2_contracts_a_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "contracts",
        sa.Column(
            "signing_intent_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_contracts_signing_intent",
        "contracts",
        "signing_intents",
        ["signing_intent_id"],
        ["id"],
        ondelete="SET NULL",
    )
    # #43 · WIDEN ck_signing_intents_signable_type para SINCRONIZAR el CHECK con
    # el catálogo Python signable_types.SIGNABLE_TYPES: añade 'contrato_comercial'
    # (#43) y recupera los F0-3 ('acta_nombramiento_roles', 'plan_adecuacion',
    # 'documento_alcance') que estaban en el catálogo pero NO en el CHECK (drift
    # pre-existente · Pasada 16). Additive (sólo amplía valores permitidos · 0
    # filas existentes violan).
    op.drop_constraint(
        "ck_signing_intents_signable_type", "signing_intents", type_="check"
    )
    op.create_check_constraint(
        "ck_signing_intents_signable_type",
        "signing_intents",
        "signable_type IN ('dda', 'magerit_validation', "
        "'pentest_authorization', 'conformidad_ens', 'acta_comite', "
        "'retainer_offer', 'retainer_quarterly_signoff', 'policy_approval', "
        "'incident_close', 'dpc_anual', 'renewal', 'acta_nombramiento_roles', "
        "'plan_adecuacion', 'documento_alcance', 'contrato_comercial', "
        "'document_generic')",
    )


def downgrade() -> None:
    # Restaura el CHECK previo (12 valores · sin F0-3 ni contrato_comercial).
    op.drop_constraint(
        "ck_signing_intents_signable_type", "signing_intents", type_="check"
    )
    op.create_check_constraint(
        "ck_signing_intents_signable_type",
        "signing_intents",
        "signable_type IN ('dda', 'magerit_validation', "
        "'pentest_authorization', 'conformidad_ens', 'acta_comite', "
        "'retainer_offer', 'policy_approval', 'incident_close', 'dpc_anual', "
        "'renewal', 'document_generic', 'retainer_quarterly_signoff')",
    )
    op.drop_constraint(
        "fk_contracts_signing_intent", "contracts", type_="foreignkey"
    )
    op.drop_column("contracts", "signing_intent_id")
