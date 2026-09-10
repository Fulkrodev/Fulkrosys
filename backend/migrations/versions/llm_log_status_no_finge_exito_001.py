"""llm_interaction_log · una llamada fallida deja de contar como exito (D1).

Revision ID: llm_log_status_no_finge_exito_001
Revises: provider_c002_generado_status_001
Create Date: 2026-09-10

Contexto
--------
`AgentBase._call_llm` devolvia una respuesta FABRICADA cuando la llamada al
modelo fallaba, y `_log_interaction` la grababa con `status="success"`,
`completion_tokens=50` (constante inventada) y un `cost_usd` calculado sobre
esos tokens. El esquema no podia impedirlo: `status` era `String(16)` sin
restriccion y los tres contadores de tokens eran NOT NULL, asi que "no hubo
llamada" no tenia forma de escribirse. Habia que inventar un numero.

Que hace esta migracion
-----------------------
1. Permite NULL en `prompt_tokens`, `completion_tokens` y `total_tokens`.
   NULL es "no medido"; 0 seria "medido y salio cero", que es otra cosa.
2. `ck_llm_log_status_canonico` — `status` solo acepta los cuatro valores del
   modulo `backend/app/core/ai/llm_log_status.py`.
3. `ck_llm_log_tokens_medidos_no_nulos` — la ganancia del punto 1 NO se paga
   con perdida de garantia: una fila `success`/`estimado` (las que SI suman)
   sigue obligada a traer los tres contadores. El NULL queda reservado a
   `mock`/`error`.
4. `ck_llm_log_sin_coste_inventado` — una fila `mock` o `error` no puede llevar
   coste distinto de 0. Esta es la que habria impedido el defecto original a
   nivel de base de datos, no de codigo.

Contrapartida (ADR-059): a cambio de poder escribir "no medido", cualquier
lectura de los contadores tiene que tolerar NULL. Medido antes de tocar nada:
los unicos consumidores son `SUM(...)` con `COALESCE` (5 consultas en
`m_observability/llm_observability_service.py` y 2 en `copilot_rate_limit.py`),
y `SUM` ya ignora NULL. Ningun consumidor lee la columna fila a fila.
"""
from alembic import op

revision = "llm_log_status_no_finge_exito_001"
down_revision = "provider_c002_generado_status_001"
branch_labels = None
depends_on = None

_ESTADOS = ("success", "estimado", "mock", "error")
_SUMAN = ("success", "estimado")

_LISTA_ESTADOS = ", ".join(f"'{e}'" for e in _ESTADOS)
_LISTA_SUMAN = ", ".join(f"'{e}'" for e in _SUMAN)


def upgrade() -> None:
    # ── 1. NULL permitido en los tres contadores ────────────────────────────
    for col in ("prompt_tokens", "completion_tokens", "total_tokens"):
        op.execute(f"ALTER TABLE llm_interaction_log ALTER COLUMN {col} DROP NOT NULL")

    # ── 0. Saneo previo · cualquier estado historico fuera del catalogo pasa
    # a 'success', que es lo que el codigo escribia hasta hoy sin excepcion.
    # Sin esto, el CHECK del punto 2 no podria validarse sobre datos existentes.
    op.execute(
        "UPDATE llm_interaction_log SET status = 'success' "
        f"WHERE status NOT IN ({_LISTA_ESTADOS})"
    )

    # ── 2. Catalogo cerrado de estados ──────────────────────────────────────
    op.execute(
        "ALTER TABLE llm_interaction_log ADD CONSTRAINT ck_llm_log_status_canonico "
        f"CHECK (status IN ({_LISTA_ESTADOS}))"
    )

    # ── 3. Los estados que suman siguen obligados a traer los contadores ────
    op.execute(
        "ALTER TABLE llm_interaction_log "
        "ADD CONSTRAINT ck_llm_log_tokens_medidos_no_nulos CHECK ("
        f"  status NOT IN ({_LISTA_SUMAN})"
        "  OR (prompt_tokens IS NOT NULL"
        "      AND completion_tokens IS NOT NULL"
        "      AND total_tokens IS NOT NULL))"
    )

    # ── 4. Una fila que no gasto no puede declarar gasto ────────────────────
    op.execute(
        "ALTER TABLE llm_interaction_log "
        "ADD CONSTRAINT ck_llm_log_sin_coste_inventado CHECK ("
        f"  status IN ({_LISTA_SUMAN})"
        "  OR cost_usd IS NULL OR cost_usd = 0)"
    )


def downgrade() -> None:
    for nombre in (
        "ck_llm_log_sin_coste_inventado",
        "ck_llm_log_tokens_medidos_no_nulos",
        "ck_llm_log_status_canonico",
    ):
        op.execute(f"ALTER TABLE llm_interaction_log DROP CONSTRAINT IF EXISTS {nombre}")

    # Volver a NOT NULL exige rellenar lo que quedo sin medir. Se pone 0, que es
    # justamente la cifra inventada que esta migracion existia para evitar: el
    # downgrade PIERDE la distincion entre "cero medido" y "no medido".
    for col in ("prompt_tokens", "completion_tokens", "total_tokens"):
        op.execute(
            f"UPDATE llm_interaction_log SET {col} = 0 WHERE {col} IS NULL"
        )
        op.execute(f"ALTER TABLE llm_interaction_log ALTER COLUMN {col} SET NOT NULL")
