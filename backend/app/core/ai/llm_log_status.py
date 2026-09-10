"""Estados canonicos de `llm_interaction_log.status` · BLOQUE D · D1.

Un solo sitio donde se decide que fila cuenta como gasto y cual no. Antes no
existia: la columna aceptaba cualquier cadena, TODAS las filas se escribian con
`"success"` (incluidas las que no habian hablado con ningun modelo) y ninguna
consulta filtraba por estado.

    ==========  ================================  =========  ====================
    status      significa                         suma?      tokens en la fila
    ==========  ================================  =========  ====================
    success     el proveedor respondio y devolvio  SI        medidos
                su recuento de tokens
    estimado    hubo llamada real, pero el         SI        estimados (~4
                proveedor NO devolvio recuento               chars/token)
                (streaming del copiloto)
    mock        NO hubo llamada (sin clave de      NO        NULL
                API): modo degradado
    error       la llamada fallo                   NO        NULL
    ==========  ================================  =========  ====================

Por que `estimado` SI suma: alimenta el tope de gasto del copiloto, y un tope
tiene que pecar de conservador. Lo que NO puede hacer es presentarse como
medicion, y por eso lleva estado propio en vez de camuflarse de `success`.
Contrapartida documentada en `docs/adr/ADR-059-llamada-llm-fallida-no-es-exito.md`.
"""
from __future__ import annotations

MEDIDO = "success"
ESTIMADO = "estimado"
MOCK = "mock"
ERROR = "error"

#: Estados que representan gasto real y por tanto entran en cualquier suma de
#: coste o de tokens.
CONTABILIZABLES: tuple[str, ...] = (MEDIDO, ESTIMADO)

#: Estados que NO representan gasto: quedan fuera de toda agregacion.
NO_CONTABILIZABLES: tuple[str, ...] = (MOCK, ERROR)

TODOS: tuple[str, ...] = CONTABILIZABLES + NO_CONTABILIZABLES

#: Fragmento SQL reutilizable para las consultas en texto plano de
#: `m_observability/llm_observability_service.py`. Se escribe literal (y no como
#: parametro ligado) porque va dentro de cadenas SQL construidas por concatenacion;
#: los valores son constantes de este modulo, nunca entrada de usuario.
SQL_SOLO_CONTABILIZABLE = "status IN (" + ", ".join(
    f"'{e}'" for e in CONTABILIZABLES
) + ")"
