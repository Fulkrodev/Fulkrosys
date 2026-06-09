"""contacts_dept_fk_1c_f_3_001 · sub-atom 1.C.F.3 (FK empleado → área).

ALTER client_contacts añadiendo ``department_id UUID NULL`` FK a
``departments(id)`` ON DELETE SET NULL.

Decisión arquitectural:
  - FK simple (1 empleado → 0..1 áreas por proyecto) en lugar de M2M.
  - Simplifica UX (dropdown vs multi-select).
  - MVP pattern realista para piloto MEDIA (~25 empleados típico).
  - ON DELETE SET NULL · borrar área NO borra empleados · solo des-asigna.

R23 sostener · departments + client_contacts ambos project-scoped.
Cross-project validation en service-layer (department.project_id ==
contact.project_id) · DB lo permite (sin CHECK constraint pesado) pero
service guard rechaza.

Revision ID: contacts_dept_fk_1c_f_3_001
Revises: departments_1c_f_2_001
Create Date: 2026-05-20
"""
from typing import Sequence, Union

from alembic import op


revision: str = "contacts_dept_fk_1c_f_3_001"
down_revision: Union[str, None] = "departments_1c_f_2_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE client_contacts
        ADD COLUMN department_id UUID NULL
        REFERENCES departments(id) ON DELETE SET NULL
        """
    )

    op.execute(
        """
        CREATE INDEX ix_client_contacts_department
        ON client_contacts (department_id)
        WHERE department_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_client_contacts_department")
    op.execute(
        "ALTER TABLE client_contacts DROP COLUMN IF EXISTS department_id"
    )
