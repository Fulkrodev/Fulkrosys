"""El analisis MAGERIT vigente de un proyecto deja de decidirse por orden.

Revision ID: magerit_analisis_vigente_001
Revises: recategorizacion_regla_anexo_i_001
Create Date: 2026-09-11

POR QUE EXISTE
    "¿Que analisis de riesgos tiene este proyecto?" estaba contestado OCHO veces
    en el codigo, todas con la misma consulta: el ultimo no borrado por
    ``created_at`` descendente, sin desempate. Se unificaron en
    ``m02_magerit/analisis_vigente.py``, pero un resolutor al que llaman ocho
    sitios lo arregla hoy: el noveno que alguien escriba manyana lo vuelve a
    romper, porque nada en la base impide escribir otra vez la consulta mala.

    Y la consulta mala tiene un fallo real, no teorico: ``created_at`` lleva
    ``server_default now()``, que en PostgreSQL devuelve el sello de INICIO DE
    TRANSACCION. Dos analisis creados en la misma transaccion comparten
    ``created_at`` al microsegundo, y entonces el "ultimo" lo elige el
    planificador de consultas. De ese analisis cuelga el informe E-028, que se
    firma.

QUE HACE
    Sustituye el orden por un HECHO: la columna ``es_vigente``, con un indice
    unico parcial que impide que un proyecto tenga dos. Ya no hay nada que
    ordenar ni que desempatar.

    La garantia va en disparadores y no en la aplicacion a proposito: un
    disparador no se puede esquivar escribiendo otra consulta. Al insertar un
    analisis, pasa a ser el vigente y los demas dejan de serlo. Al borrar
    (borrado blando) el vigente, asciende el mas reciente que quede -- con
    desempate por ``id``, porque aqui tambien puede haber empate a sello.

    Las funciones son SECURITY DEFINER porque ``magerit_analysis`` lleva RLS
    (``project_isolation``) y el disparador tiene que tocar las filas hermanas
    del MISMO proyecto. El alcance esta acotado a ``NEW.project_id``: no cruza
    tenant.

BACKFILL
    Se marca vigente el mas reciente de cada proyecto con el mismo criterio
    (``created_at`` desc, ``id`` desc), que es lo que el codigo venia
    devolviendo. No cambia que analisis se usa; fija cual es.
"""
from alembic import op
import sqlalchemy as sa

revision = "magerit_analisis_vigente_001"
down_revision = "recategorizacion_regla_anexo_i_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "magerit_analysis",
        sa.Column(
            "es_vigente",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment=(
                "El analisis que el proyecto usa AHORA. Lo mantienen los "
                "disparadores tg_magerit_analysis_*; no se escribe a mano."
            ),
        ),
    )

    # Backfill: el mas reciente de cada proyecto, con desempate determinista.
    op.execute(
        """
        UPDATE magerit_analysis m SET es_vigente = true
        FROM (
            SELECT DISTINCT ON (project_id) id
            FROM magerit_analysis
            WHERE deleted_at IS NULL
            ORDER BY project_id, created_at DESC, id DESC
        ) elegido
        WHERE m.id = elegido.id
        """
    )

    op.execute(
        """
        CREATE UNIQUE INDEX uq_magerit_analysis_vigente_por_proyecto
        ON magerit_analysis (project_id)
        WHERE es_vigente AND deleted_at IS NULL
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_magerit_analysis_nuevo_es_vigente()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $$
        BEGIN
            IF NEW.deleted_at IS NULL THEN
                UPDATE magerit_analysis
                   SET es_vigente = false
                 WHERE project_id = NEW.project_id
                   AND id <> NEW.id
                   AND es_vigente;
                NEW.es_vigente := true;
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER tg_magerit_analysis_nuevo_es_vigente
        BEFORE INSERT ON magerit_analysis
        FOR EACH ROW EXECUTE FUNCTION fn_magerit_analysis_nuevo_es_vigente()
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_magerit_analysis_asciende_al_borrar()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $$
        DECLARE
            sucesor uuid;
        BEGIN
            UPDATE magerit_analysis SET es_vigente = false WHERE id = NEW.id;
            SELECT id INTO sucesor
              FROM magerit_analysis
             WHERE project_id = NEW.project_id
               AND deleted_at IS NULL
             ORDER BY created_at DESC, id DESC
             LIMIT 1;
            IF sucesor IS NOT NULL THEN
                UPDATE magerit_analysis SET es_vigente = true WHERE id = sucesor;
            END IF;
            RETURN NULL;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER tg_magerit_analysis_asciende_al_borrar
        AFTER UPDATE OF deleted_at ON magerit_analysis
        FOR EACH ROW
        WHEN (OLD.deleted_at IS NULL AND NEW.deleted_at IS NOT NULL
              AND OLD.es_vigente)
        EXECUTE FUNCTION fn_magerit_analysis_asciende_al_borrar()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS tg_magerit_analysis_asciende_al_borrar "
        "ON magerit_analysis"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS tg_magerit_analysis_nuevo_es_vigente "
        "ON magerit_analysis"
    )
    op.execute("DROP FUNCTION IF EXISTS fn_magerit_analysis_asciende_al_borrar()")
    op.execute("DROP FUNCTION IF EXISTS fn_magerit_analysis_nuevo_es_vigente()")
    op.execute("DROP INDEX IF EXISTS uq_magerit_analysis_vigente_por_proyecto")
    op.drop_column("magerit_analysis", "es_vigente")
