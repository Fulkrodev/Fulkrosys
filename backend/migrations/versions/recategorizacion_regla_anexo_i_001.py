"""Marca las categorizaciones calculadas con la regla del maximo sin NO_AFECTADA.

Revision ID: recategorizacion_regla_anexo_i_001
Revises: llm_log_status_no_finge_exito_001
Create Date: 2026-09-11

POR QUE EXISTE
    Hasta el bloque N, la categorizacion arrancaba las CINCO dimensiones en
    BAJO. El Anexo I punto 3 del RD 311/2022 dice lo contrario: "Si una
    dimension de seguridad no se ve afectada, no se adscribira a ningun nivel".
    Un sistema que nadie habia valorado salia como BASICA.

    ADR-061 dejo escrito que "no se han migrado las categorizaciones
    existentes". Eso no es la contrapartida de una decision: es un dato
    incorrecto en la base con una nota al lado. De la categoria cuelga todo --
    que medidas aplican, la DdA, el plan, el alcance --, asi que una categoria
    mal calculada contamina el expediente entero.

QUE HACE, Y QUE NO HACE
    NO recalcula ninguna categorizacion. Una categorizacion es un acto aprobado
    y firmado (`aprobado_por`, `fecha_acta`, `version`): sobrescribirla desde
    una migracion seria falsificar un acta.

    Lo que hace es anyadir la MARCA para que el sistema pueda exigir
    recategorizar. El marcado de las filas existentes lo hace
    `backend/app/motors/m01_categorization/recategorizacion.py`, que recomputa
    desde `input_snapshot` con la regla correcta y compara: asi solo se senyalan
    las que de verdad cambian, no todas por fecha.
"""
from alembic import op
import sqlalchemy as sa

revision = "recategorizacion_regla_anexo_i_001"
down_revision = "llm_log_status_no_finge_exito_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "categorizations",
        sa.Column(
            "requiere_recategorizacion",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "categorizations",
        sa.Column("motivo_recategorizacion", sa.Text(), nullable=True),
    )
    # Indice parcial: lo que se consulta es "cuales hay que rehacer", que es
    # una minoria. Un indice sobre toda la tabla no compra nada aqui.
    op.create_index(
        "ix_categorizations_requiere_recat",
        "categorizations",
        ["requiere_recategorizacion"],
        unique=False,
        postgresql_where=sa.text("requiere_recategorizacion IS TRUE"),
    )


def downgrade() -> None:
    op.drop_index("ix_categorizations_requiere_recat", table_name="categorizations")
    op.drop_column("categorizations", "motivo_recategorizacion")
    op.drop_column("categorizations", "requiere_recategorizacion")
