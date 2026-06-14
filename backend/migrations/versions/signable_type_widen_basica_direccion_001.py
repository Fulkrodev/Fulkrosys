"""widen ck_signing_intents_signable_type · +declaracion_conformidad_basica +acta_decision_direccion

Revision ID: signable_type_widen_001
Revises: remediation_agent_001
Create Date: 2026-06-14

Drift FIX (batch2 audit): el catálogo Python ``signable_types.SIGNABLE_TYPES``
tiene 18 valores, pero el CHECK ``ck_signing_intents_signable_type`` (última
redefinición en ola2_contracts_c_001) solo listaba 16: faltaban
``declaracion_conformidad_basica`` (#44 · cierre BÁSICA firmado por Dirección ·
CCN-STIC 809) y ``acta_decision_direccion`` (E-010). El endpoint POST
``/portal/signing/intents`` valida contra SIGNABLE_TYPES (18) y luego inserta el
valor crudo → PostgreSQL rechazaba esos 2 con violación del CHECK → IntegrityError
no manejado → HTTP 500.

Additive (sólo amplía valores permitidos · 0 filas existentes violan).
Reversible. Política TODO-DB-DRIFT-001 (scope-only · sin autogenerate).
"""
from typing import Sequence, Union

from alembic import op


revision: str = "signable_type_widen_001"
down_revision: Union[str, None] = "remediation_agent_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_ALL_18 = (
    "signable_type IN ('dda', 'magerit_validation', 'pentest_authorization', "
    "'conformidad_ens', 'declaracion_conformidad_basica', 'acta_comite', "
    "'retainer_offer', 'retainer_quarterly_signoff', 'policy_approval', "
    "'incident_close', 'dpc_anual', 'renewal', 'acta_nombramiento_roles', "
    "'acta_decision_direccion', 'plan_adecuacion', 'documento_alcance', "
    "'contrato_comercial', 'document_generic')"
)

_PREV_16 = (
    "signable_type IN ('dda', 'magerit_validation', 'pentest_authorization', "
    "'conformidad_ens', 'acta_comite', 'retainer_offer', "
    "'retainer_quarterly_signoff', 'policy_approval', 'incident_close', "
    "'dpc_anual', 'renewal', 'acta_nombramiento_roles', 'plan_adecuacion', "
    "'documento_alcance', 'contrato_comercial', 'document_generic')"
)


def upgrade() -> None:
    op.drop_constraint(
        "ck_signing_intents_signable_type", "signing_intents", type_="check"
    )
    op.create_check_constraint(
        "ck_signing_intents_signable_type", "signing_intents", _ALL_18
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_signing_intents_signable_type", "signing_intents", type_="check"
    )
    op.create_check_constraint(
        "ck_signing_intents_signable_type", "signing_intents", _PREV_16
    )
