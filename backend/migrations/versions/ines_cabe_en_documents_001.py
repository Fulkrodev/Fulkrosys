"""El informe INES del art. 32 cabe por fin en `documents`.

Revision ID: ines_cabe_documents_001
Revises: no_afectada_cabe_001
Create Date: 2026-09-12

POR QUE EXISTE
    ``documents`` es la tabla que lee el generador del expediente del auditor.
    Lo que no está ahí, para el auditor no existe. Y exigía ``project_id NOT
    NULL``.

    El informe INES del art. 32 del RD 311/2022 es ANUAL y POR ORGANIZACIÓN
    (``organization_id``), no por proyecto. Registrarlo obligaba antes a decidir
    a qué proyecto pertenece el informe de una organización que tiene varios —
    que no es un arreglo, es inventarse un dato de archivo. Por eso se quedó
    fuera del inventario documental, con el motivo escrito, desde el bloque O2.

    Es el mismo patrón que ``VARCHAR(10)`` contra ``NO_AFECTADA``: un estado
    legítimo que el esquema no sabía representar. Aquí, un documento legítimo
    cuyo ámbito el esquema no sabía expresar.

QUE HACE
    - ``project_id`` pasa a ser NULLABLE.
    - Se añade ``client_id`` (la organización), con su índice y su FK.
    - Se exige, con un CHECK, que haya AL MENOS UNO de los dos: un documento sin
      ámbito ninguno no se registra.
    - La política RLS pasa a la forma de dos ramas que este repositorio ya usa
      en ``audit_log``: coincide por proyecto **o** por cliente. Un documento de
      organización lo ve quien está en esa organización; los de proyecto siguen
      viéndose exactamente igual que antes.

QUE NO HACE
    No cambia dónde se guarda ningún documento existente: todos los que hay
    tienen ``project_id`` y siguen igual. Sólo abre la puerta al ámbito de
    organización, que antes no existía.
"""
from alembic import op
import sqlalchemy as sa

revision = "ines_cabe_documents_001"
down_revision = "no_afectada_cabe_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("documents", "project_id", existing_type=sa.dialects.postgresql.UUID(),
                    nullable=True)
    op.add_column("documents", sa.Column("client_id", sa.dialects.postgresql.UUID(),
                                         nullable=True))
    op.create_foreign_key(
        "documents_client_id_fkey", "documents", "clients", ["client_id"], ["id"],
    )
    op.create_index("ix_documents_client_id", "documents", ["client_id"])
    op.execute(
        "ALTER TABLE documents ADD CONSTRAINT ck_documents_ambito "
        "CHECK (project_id IS NOT NULL OR client_id IS NOT NULL)"
    )
    # RLS de dos ramas (mismo patrón que audit_log).
    op.execute("DROP POLICY IF EXISTS project_isolation ON documents")
    op.execute(
        "CREATE POLICY project_isolation ON documents USING ("
        "  (project_id IS NOT NULL AND project_id = current_project_id())"
        "  OR (client_id IS NOT NULL AND client_id = current_client_id())"
        ")"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS project_isolation ON documents")
    op.execute(
        "CREATE POLICY project_isolation ON documents USING ("
        "project_id = current_project_id())"
    )
    op.execute("ALTER TABLE documents DROP CONSTRAINT IF EXISTS ck_documents_ambito")
    op.drop_index("ix_documents_client_id", table_name="documents")
    op.drop_constraint("documents_client_id_fkey", "documents", type_="foreignkey")
    op.drop_column("documents", "client_id")
    op.execute("DELETE FROM documents WHERE project_id IS NULL")
    op.alter_column("documents", "project_id", existing_type=sa.dialects.postgresql.UUID(),
                    nullable=False)
