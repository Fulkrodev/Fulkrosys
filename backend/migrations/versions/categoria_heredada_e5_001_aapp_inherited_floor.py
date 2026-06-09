"""categoria_heredada_aapp · suelo de categoría heredado de la AAPP (#5 · Sub-bloque E)

Revision ID: categoria_heredada_e5_001
Revises: ola2_contracts_c_001
Create Date: 2026-06-04

Punto #5 (herencia de categorización de la AAPP). Migración **additive** y
**nullable** (segura sobre filas existentes · todas quedan NULL = sin herencia)
que añade el suelo de categoría que la AAPP contratante asignó al servicio:

- ``projects.categoria_heredada_aapp`` (VARCHAR(10), nullable) → categoría
  heredada de la AAPP (BASICA/MEDIA/ALTA). Es un PISO DURO: la categorización
  computada (regla del máximo, Anexo I RD 311/2022) solo puede SUBIR por encima,
  nunca declararse por debajo. Capturado por Marcos en Fase 1 desde el
  pliego/contrato de la licitación (decisión-producto A · criterio de consultor
  informado, NO autodeclaración del cliente). Sibling de ``projects.papel_aapp``.

Scope-only (política TODO-DB-DRIFT-001 · sin autogenerate): conserva SOLO esta
operación. Nullable → ``fulkro_app`` hereda el GRANT de tabla (sin GRANT extra
por columna). Reversible. La columna vive en ``projects`` (RLS ``client_isolation``
existente · migración e41cd7163c02) → hereda la RLS por fila sin política nueva.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "categoria_heredada_e5_001"
down_revision: Union[str, None] = "ola2_contracts_c_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("categoria_heredada_aapp", sa.String(length=10), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("projects", "categoria_heredada_aapp")
