"""Evaluador del golden dataset de `agent_18_reunion` (BLOQUE D · D2).

Qué mide, exactamente
---------------------
La salida estructurada de `Agent18ReunionExploratoria.invoke(...)['parsed']`.
De las 9 claves obligatorias del esquema, cinco son enumerados cerrados
(`categoria_ens`, `madurez_actual`, `viabilidad_temporal`, `impacto` de cada
riesgo, `esfuerzo` de cada quick win), una es un intervalo numérico de horas
y tres son listas con cardinalidad máxima. Todo eso se comprueba con
pertenencia a conjunto, solape de intervalos y conteo. Los textos
(`rationale_categoria`, títulos, descripciones, preguntas) se comprueban
como estructura —que existan, que sean cadenas, que respeten el tope de 250
caracteres del agente— y **no se puntúa su contenido**.

Tres decisiones de diseño con su contrapartida
----------------------------------------------
1. **Categoría y madurez se comparan contra un conjunto aceptable, no
   contra un valor único.** En una reunión exploratoria todavía no hay
   valoración firmada de las dimensiones del Anexo I, así que en varios
   casos hay dos respuestas defendibles (por ejemplo MEDIA o ALTA para un
   sistema con datos de salud). El dataset declara el conjunto y, cuando lo
   importante es lo que NO se puede responder, lo hace excluyendo: la
   entrada del cliente que pide BÁSICA para una sede electrónica acepta
   {MEDIA, ALTA} justamente para que BÁSICA falle. Contrapartida: el
   criterio es más laxo que una igualdad, y por eso las bandas de confianza
   y las cardinalidades mínimas cargan con el resto del peso.

2. **Las horas se comprueban por SOLAPE, no por igualdad.** Una estimación
   de esfuerzo no es determinista; exigir el número exacto mediría ruido de
   muestreo y no calidad. Se exige que el intervalo [min, max] del modelo
   corte el intervalo curado. Contrapartida: un modelo que devuelva un
   intervalo absurdamente ancho (0-500) solapa siempre y pasa esta
   comprobación; contra eso está el tope de 500 del propio agente y, sobre
   todo, el resto de comprobaciones de la entrada.

3. **`viabilidad_temporal` sí es igualdad de conjunto estricta en las
   entradas de plazo.** Es el campo que convierte el panel en útil: decirle
   a Marcos que tres semanas para una MEDIA desde cero es "ajustada" en vez
   de "inviable" es el error caro, y por eso ahí el conjunto aceptable tiene
   un solo elemento.

Registrado al importar el paquete `evaluators`.
"""
from __future__ import annotations

from typing import Any

from backend.app.motors.m_observability.eval_runner import (
    EntryEvalResult,
    register_evaluator,
    register_synthetic_output,
)
from backend.app.motors.m_observability.evaluators import _comun
from backend.app.motors.m_observability.golden_datasets_loader import (
    GoldenDatasetEntry,
)


_AGENT_NAME = "agent_18_reunion"

# Las 9 claves que `Agent18ReunionExploratoria._validate_schema` exige.
_CLAVES_OBLIGATORIAS: tuple[str, ...] = (
    "categoria_ens",
    "confianza_categoria",
    "rationale_categoria",
    "madurez_actual",
    "horas_marcos_estimadas",
    "viabilidad_temporal",
    "riesgos_detectados",
    "quick_wins_sugeridas",
    "preguntas_pendientes",
)

# Copias deliberadas de los enumerados de
# backend/app/agents/agent_18_reunion.py. No se importa el módulo del agente
# porque el job `evals-arnes` instala sólo pydantic y pyyaml y ese módulo
# arrastra SQLAlchemy. La copia la vigila
# backend/tests/motors/m_observability/test_evaluadores_agentes.py.
_CATEGORIAS = {"BASICA", "MEDIA", "ALTA", "UNKNOWN"}
_MADUREZ = {"L0", "L1", "L2", "L3", "L4", "L5"}
_VIABILIDAD = {"holgada", "ajustada", "inviable", "desconocida"}
_IMPACTO = {"alto", "medio", "bajo"}
_ESFUERZO = {"1h", "1d", "1w"}

_MAX_RATIONALE = 250
_MAX_RIESGOS = 3
_MAX_QUICK_WINS = 3
_MAX_PREGUNTAS = 5
_MAX_HORAS = 500


def _revisar_lista_objetos(
    valor: Any,
    nombre: str,
    tope: int,
    campos: tuple[str, ...],
    enumerados: dict[str, set[str]],
    fallos: list[str],
) -> list[Any]:
    """Comprueba lista de objetos con campos obligatorios y enumerados."""
    if not isinstance(valor, list):
        fallos.append(f"{nombre} no es una lista")
        return []
    if len(valor) > tope:
        fallos.append(f"{nombre} con {len(valor)} elementos (tope {tope})")
    for i, item in enumerate(valor):
        if not isinstance(item, dict):
            fallos.append(f"{nombre}[{i}] no es un objeto")
            continue
        for campo in campos:
            if campo not in item:
                fallos.append(f"{nombre}[{i}] no trae '{campo}'")
        for campo, permitidos in enumerados.items():
            if campo in item and item.get(campo) not in permitidos:
                fallos.append(
                    f"{nombre}[{i}].{campo} fuera del enumerado: "
                    f"{item.get(campo)!r}",
                )
    return valor


def agent_18_reunion_evaluator(
    entry: GoldenDatasetEntry, actual: Any,
) -> EntryEvalResult:
    """Comprobación determinista del panel de una reunión exploratoria."""
    if actual is None:
        return EntryEvalResult(
            entry_id=entry.id,
            category=entry.category,
            passed=False,
            diff_summary="saltada · el proveedor no pudo llamar al modelo",
            skipped=True,
            skip_reason=(
                "sin proveedor cableado o sin ANTHROPIC_API_KEY: no se ha "
                "llamado al modelo, así que no hay nada que puntuar"
            ),
        )

    motivo = _comun.sin_json(actual)
    if motivo:
        return EntryEvalResult(
            entry_id=entry.id,
            category=entry.category,
            passed=False,
            diff_summary=motivo,
        )

    faltan = _comun.claves_faltantes(actual, _CLAVES_OBLIGATORIAS)
    if faltan:
        return EntryEvalResult(
            entry_id=entry.id,
            category=entry.category,
            passed=False,
            diff_summary=f"faltan claves obligatorias: {faltan}",
        )

    fallos: list[str] = []

    # ── Categoría ENS ────────────────────────────────────────────────────
    categoria = actual.get("categoria_ens")
    aceptables = list(_comun.extra(entry, "categorias_aceptables", []))
    if categoria not in _CATEGORIAS:
        fallos.append(f"categoria_ens fuera del enumerado: {categoria!r}")
    elif aceptables and categoria not in aceptables:
        fallos.append(
            f"categoria_ens = {categoria}; el dataset acepta {aceptables}",
        )

    # ── Confianza de la categoría ────────────────────────────────────────
    confianza = _comun.numero(actual.get("confianza_categoria"))
    conf_min = float(_comun.extra(entry, "confianza_minima", 0.0))
    conf_max = float(_comun.extra(entry, "confianza_maxima", 1.0))
    if confianza is None:
        fallos.append(
            f"confianza_categoria no es numérica: "
            f"{actual.get('confianza_categoria')!r}",
        )
    elif not (0.0 <= confianza <= 1.0):
        fallos.append(f"confianza_categoria fuera de [0,1]: {confianza}")
    elif not (conf_min <= confianza <= conf_max):
        fallos.append(
            f"confianza_categoria {confianza} fuera de la banda curada "
            f"[{conf_min}, {conf_max}]",
        )

    # ── Rationale: estructura y tope, NO contenido ───────────────────────
    rationale = actual.get("rationale_categoria")
    if not isinstance(rationale, str) or not rationale.strip():
        fallos.append("rationale_categoria vacío o no es texto")
    elif len(rationale) > _MAX_RATIONALE:
        fallos.append(
            f"rationale_categoria de {len(rationale)} caracteres "
            f"(tope {_MAX_RATIONALE})",
        )

    # ── Madurez ──────────────────────────────────────────────────────────
    madurez = actual.get("madurez_actual")
    madurez_ok = list(_comun.extra(entry, "madurez_aceptable", []))
    if madurez not in _MADUREZ:
        fallos.append(f"madurez_actual fuera del enumerado: {madurez!r}")
    elif madurez_ok and madurez not in madurez_ok:
        fallos.append(
            f"madurez_actual = {madurez}; el dataset acepta {madurez_ok}",
        )

    # ── Horas: solape de intervalos ──────────────────────────────────────
    horas = actual.get("horas_marcos_estimadas")
    if not isinstance(horas, dict):
        fallos.append("horas_marcos_estimadas no es un objeto")
    else:
        h_min = _comun.entero(horas.get("min"))
        h_max = _comun.entero(horas.get("max"))
        if h_min is None or h_max is None:
            fallos.append(
                f"horas_marcos_estimadas.min/max no son enteros: "
                f"{horas.get('min')!r}/{horas.get('max')!r}",
            )
        else:
            if not (0 <= h_min <= _MAX_HORAS and 0 <= h_max <= _MAX_HORAS):
                fallos.append(
                    f"horas fuera de [0,{_MAX_HORAS}]: {h_min}-{h_max}",
                )
            if h_min > h_max:
                fallos.append(f"horas con min > max: {h_min} > {h_max}")
            banda = list(_comun.extra(entry, "horas_rango_esperado", []))
            if len(banda) == 2:
                solapa = h_min <= banda[1] and banda[0] <= h_max
                if not solapa:
                    fallos.append(
                        f"la estimación {h_min}-{h_max} h no solapa con la "
                        f"banda curada {banda[0]}-{banda[1]} h",
                    )
        if not isinstance(horas.get("rationale"), str):
            fallos.append("horas_marcos_estimadas.rationale no es texto")

    # ── Viabilidad temporal ──────────────────────────────────────────────
    viabilidad = actual.get("viabilidad_temporal")
    viab_ok = list(_comun.extra(entry, "viabilidades_aceptables", []))
    if viabilidad not in _VIABILIDAD:
        fallos.append(
            f"viabilidad_temporal fuera del enumerado: {viabilidad!r}",
        )
    elif viab_ok and viabilidad not in viab_ok:
        fallos.append(
            f"viabilidad_temporal = {viabilidad}; el dataset acepta "
            f"{viab_ok}",
        )

    # ── Riesgos ──────────────────────────────────────────────────────────
    riesgos = _revisar_lista_objetos(
        actual.get("riesgos_detectados"), "riesgos_detectados", _MAX_RIESGOS,
        ("titulo", "impacto", "descripcion"), {"impacto": _IMPACTO}, fallos,
    )
    r_min = int(_comun.extra(entry, "riesgos_minimos", 0))
    r_max = int(_comun.extra(entry, "riesgos_maximos", _MAX_RIESGOS))
    if not (r_min <= len(riesgos) <= r_max):
        fallos.append(
            f"riesgos detectados = {len(riesgos)}; el dataset espera entre "
            f"{r_min} y {r_max}",
        )

    # ── Quick wins ───────────────────────────────────────────────────────
    quick = _revisar_lista_objetos(
        actual.get("quick_wins_sugeridas"), "quick_wins_sugeridas",
        _MAX_QUICK_WINS, ("titulo", "esfuerzo", "impacto"),
        {"esfuerzo": _ESFUERZO, "impacto": _IMPACTO}, fallos,
    )
    q_min = int(_comun.extra(entry, "quick_wins_minimas", 0))
    if len(quick) < q_min:
        fallos.append(
            f"quick wins = {len(quick)}; el dataset exige al menos {q_min}",
        )

    # ── Preguntas pendientes ─────────────────────────────────────────────
    preguntas = actual.get("preguntas_pendientes")
    if not isinstance(preguntas, list):
        fallos.append("preguntas_pendientes no es una lista")
        preguntas = []
    else:
        if len(preguntas) > _MAX_PREGUNTAS:
            fallos.append(
                f"preguntas_pendientes con {len(preguntas)} "
                f"(tope {_MAX_PREGUNTAS})",
            )
        if any(not isinstance(p, str) for p in preguntas):
            fallos.append("preguntas_pendientes contiene elementos no textuales")
    p_min = int(_comun.extra(entry, "preguntas_minimas", 0))
    p_max = int(_comun.extra(entry, "preguntas_maximas", _MAX_PREGUNTAS))
    if not (p_min <= len(preguntas) <= p_max):
        fallos.append(
            f"preguntas pendientes = {len(preguntas)}; el dataset espera "
            f"entre {p_min} y {p_max}",
        )

    ausentes, prohibidas = _comun.frases(entry, actual)
    if ausentes:
        fallos.append(f"faltan frases requeridas: {ausentes[:3]}")
    if prohibidas:
        fallos.append(f"aparecen frases prohibidas: {prohibidas[:3]}")

    return EntryEvalResult(
        entry_id=entry.id,
        category=entry.category,
        passed=not fallos,
        diff_summary="; ".join(fallos) if fallos else "ok",
        required_missing=ausentes,
        forbidden_present_unflagged=prohibidas,
        actual_summary={
            "categoria_ens": categoria,
            "confianza_categoria": confianza,
            "madurez_actual": madurez,
            "viabilidad_temporal": viabilidad,
            "riesgos": len(riesgos),
            "preguntas": len(preguntas),
        },
    )


def salida_sintetica(entry: GoldenDatasetEntry) -> dict[str, Any]:
    """Respuesta perfecta para `entry`, con la forma que devuelve A18."""
    categorias = list(_comun.extra(entry, "categorias_aceptables", ["UNKNOWN"]))
    madurez = list(_comun.extra(entry, "madurez_aceptable", ["L0"]))
    viabilidades = list(
        _comun.extra(entry, "viabilidades_aceptables", ["desconocida"]),
    )
    banda = list(_comun.extra(entry, "horas_rango_esperado", [0, 0]))
    conf_min = float(_comun.extra(entry, "confianza_minima", 0.0))
    conf_max = float(_comun.extra(entry, "confianza_maxima", 1.0))
    r_min = int(_comun.extra(entry, "riesgos_minimos", 0))
    q_min = int(_comun.extra(entry, "quick_wins_minimas", 0))
    p_min = int(_comun.extra(entry, "preguntas_minimas", 0))

    return {
        "categoria_ens": categorias[0] if categorias else "UNKNOWN",
        "confianza_categoria": round((conf_min + conf_max) / 2, 4),
        "rationale_categoria": (
            f"Salida sintética del gate del arnés para {entry.id}."
        )[:_MAX_RATIONALE],
        "madurez_actual": madurez[0] if madurez else "L0",
        "horas_marcos_estimadas": {
            "min": int(banda[0]) if len(banda) == 2 else 0,
            "max": int(banda[1]) if len(banda) == 2 else 0,
            "rationale": "Banda curada del propio dataset.",
        },
        "viabilidad_temporal": (
            viabilidades[0] if viabilidades else "desconocida"
        ),
        "riesgos_detectados": [
            {
                "titulo": f"Riesgo sintético {i + 1}",
                "impacto": "medio",
                "descripcion": "Generado por el gate del arnés, no por el modelo.",
            }
            for i in range(min(r_min, _MAX_RIESGOS))
        ],
        "quick_wins_sugeridas": [
            {
                "titulo": f"Quick win sintética {i + 1}",
                "esfuerzo": "1d",
                "impacto": "medio",
            }
            for i in range(min(q_min, _MAX_QUICK_WINS))
        ],
        "preguntas_pendientes": [
            f"Pregunta sintética {i + 1} para {entry.id}."
            for i in range(min(p_min, _MAX_PREGUNTAS))
        ],
    }


register_evaluator(_AGENT_NAME, agent_18_reunion_evaluator)
register_synthetic_output(_AGENT_NAME, salida_sintetica)
