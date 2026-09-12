"""«No afectada» no cabía en la columna que la tiene que guardar.

Revision ID: no_afectada_cabe_001
Revises: magerit_analisis_vigente_001
Create Date: 2026-09-12

POR QUE EXISTE
    RD 311/2022, Anexo I, punto 3: una dimensión que no se ve afectada NO se
    adscribe a ningún nivel. El bloque N introdujo ese estado en el motor y el
    bloque O2 lo aceptó en el asistente de diagnóstico, pero las dos tablas
    canónicas que guardan una valoración —``information_types`` y ``services``—
    declaran sus cinco columnas como ``VARCHAR(10)``.

        NO_AFECTADA  ->  11 caracteres

    Es decir: el estado que la norma define era **irrepresentable** en la tabla.
    Cualquier intento de guardarlo salía con

        asyncpg.exceptions.StringDataRightTruncationError:
        value too long for type character varying(10)

    y lo único que quedaba para expresar «no afectada» era el NULL, que no es lo
    mismo: NULL es «no hay dato», y esa ambigüedad es justo la que hacía que un
    renderizador escribiera ``or "BAJO"`` y el acta E-012 firmada declarase BAJO
    una dimensión que nadie valoró.

    El defecto no se ve leyendo el código de la aplicación: vive en el ancho de
    una columna. Se encontró porque un test intentó guardar el valor.

QUE HACE
    Ensancha las diez columnas a ``VARCHAR(20)``. Es una ampliación de tipo: no
    reescribe la tabla en PostgreSQL, no puede perder datos y la bajada sólo
    falla si alguien ya guardó el valor nuevo (que es el comportamiento correcto:
    estrechar la columna volvería a hacer irrepresentable el estado).
"""
from alembic import op
import sqlalchemy as sa

revision = "no_afectada_cabe_001"
down_revision = "magerit_analisis_vigente_001"
branch_labels = None
depends_on = None

_TABLAS = ("information_types", "services")
_COLUMNAS = ("valoracion_d", "valoracion_i", "valoracion_c",
             "valoracion_a", "valoracion_t")


def upgrade() -> None:
    for tabla in _TABLAS:
        for col in _COLUMNAS:
            op.alter_column(
                tabla, col,
                existing_type=sa.String(10),
                type_=sa.String(20),
                existing_nullable=True,
            )


def downgrade() -> None:
    for tabla in _TABLAS:
        for col in _COLUMNAS:
            op.alter_column(
                tabla, col,
                existing_type=sa.String(20),
                type_=sa.String(10),
                existing_nullable=True,
            )
