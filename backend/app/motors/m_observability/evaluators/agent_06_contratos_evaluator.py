"""Evaluador del golden dataset de `agent_06_contratos` (BLOQUE D · D2).

Qué mide, exactamente
---------------------
La salida estructurada de `Agent06AnalistaContratos.invoke(...)['parsed']`.
El agente hace un MAPEO: proyecta el texto de un contrato sobre un catálogo
cerrado de cláusulas obligatorias cuyo tamaño depende de la categoría ENS
del cliente (6 en BÁSICA, 10 en MEDIA, 13 en ALTA) y, por cada cláusula,
devuelve un booleano de presencia y una calidad de tres valores. Eso se
comprueba por pertenencia a conjunto y por igualdad, sin juicio.

Lo que este evaluador NO hace: puntuar la adenda. `addendum_text` es prosa
jurídica de hasta 3500 caracteres y aquí sólo se comprueba que existe, que
es texto y que respeta ese tope. Medir su calidad exigiría un criterio
subjetivo, y este dataset se construyó para no tener ninguno.

Tres decisiones de diseño con su contrapartida
----------------------------------------------
1. **Tres listas de cláusulas en vez de una.** `clausulas_ausentes_esperadas`
   exige `present=false` y `quality="ausente"`;
   `clausulas_presentes_completas_esperadas` exige `present=true` y
   `quality="completo"`; y `clausulas_deficientes_esperadas` exige sólo
   `quality != "completo"`. La tercera existe porque el caso interesante de
   un contrato es la cláusula que EXISTE y NO SIRVE —«podrá subcontratar
   libremente», «auditoría una vez cada tres años a su costa»—, donde
   `present` es genuinamente discutible y `quality` no lo es. Un evaluador
   de igualdad simple sobre `present` habría convertido esa ambigüedad en
   ruido. Contrapartida: la tercera lista es más laxa; a cambio distingue
   graduar de marcar casillas, que es justo lo que aporta el agente.

2. **La cobertura del catálogo se comprueba entera y el catálogo se declara
   en el dataset.** Cada entrada lleva su `catalogo_obligatorio` explícito
   en vez de derivarlo de la categoría dentro del evaluador. El dataset es
   el contrato fijado: si mañana el agente añade una cláusula obligatoria a
   MEDIA, el dataset NO cambia solo y hay que actualizarlo a mano, que es lo
   que se quiere de un golden. Contrapartida: verbosidad en el JSON.

3. **La puntuación se comprueba por banda, no por número exacto.** Un
   `compliance_score` es un juicio agregado; exigir el entero exacto mediría
   ruido. Las bandas se han curado con dos anclas —un contrato que cubre
   las diez cláusulas de MEDIA y otro que no cubre ninguna— para que la
   escala tenga extremos y no sólo un centro difuso.

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


_AGENT_NAME = "agent_06_contratos"

# Las 7 claves que `Agent06AnalistaContratos._validate_schema` exige.
_CLAVES_OBLIGATORIAS: tuple[str, ...] = (
    "compliance_score",
    "compliance_level",
    "mandatory_clauses_check",
    "sector_specific_gaps",
    "addendum_text",
    "recommendation",
    "red_flags",
)

# Copias deliberadas de los enumerados de
# backend/app/agents/agent_06_contratos.py. No se importa el módulo del
# agente porque el job `evals-arnes` instala sólo pydantic y pyyaml y ese
# módulo arrastra SQLAlchemy. La copia la vigila
# backend/tests/motors/m_observability/test_evaluadores_agentes.py.
_NIVELES = {"conforme", "parcial", "no_conforme", "critico"}
_CALIDADES = {"completo", "incompleto", "ausente"}
_SEVERIDADES = {"critico", "alto", "medio", "bajo"}
_ACCIONES = {
    "firmar_adenda",
    "renegociar_contrato",
    "buscar_proveedor_alternativo",
    "aceptar_riesgo_documentado",
}
_URGENCIAS = {"inmediata", "1_mes", "1_trimestre", "1_ano"}

_MAX_ADENDA = 3500
_MAX_RATIONALE = 400
_MAX_GAPS = 5
_MAX_RED_FLAGS = 3
_MAX_RED_FLAG_CHARS = 250


def agent_06_contratos_evaluator(
    entry: GoldenDatasetEntry, actual: Any,
) -> EntryEvalResult:
    """Comprobación determinista del análisis de un contrato de proveedor."""
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

    # ── Puntuación ───────────────────────────────────────────────────────
    score = _comun.entero(actual.get("compliance_score"))
    s_min = int(_comun.extra(entry, "compliance_score_minimo", 0))
    s_max = int(_comun.extra(entry, "compliance_score_maximo", 100))
    if score is None:
        fallos.append(
            f"compliance_score no es entero: {actual.get('compliance_score')!r}",
        )
    elif not (0 <= score <= 100):
        fallos.append(f"compliance_score fuera de [0,100]: {score}")
    elif not (s_min <= score <= s_max):
        fallos.append(
            f"compliance_score {score} fuera de la banda curada "
            f"[{s_min}, {s_max}]",
        )

    # ── Nivel de cumplimiento ────────────────────────────────────────────
    nivel = actual.get("compliance_level")
    niveles_ok = list(_comun.extra(entry, "niveles_aceptables", []))
    if nivel not in _NIVELES:
        fallos.append(f"compliance_level fuera del enumerado: {nivel!r}")
    elif niveles_ok and nivel not in niveles_ok:
        fallos.append(
            f"compliance_level = {nivel}; el dataset acepta {niveles_ok}",
        )

    # ── Checklist de cláusulas: el mapeo ─────────────────────────────────
    clausulas = actual.get("mandatory_clauses_check")
    por_id: dict[str, dict[str, Any]] = {}
    if not isinstance(clausulas, list):
        fallos.append("mandatory_clauses_check no es una lista")
    else:
        for i, item in enumerate(clausulas):
            if not isinstance(item, dict):
                fallos.append(f"mandatory_clauses_check[{i}] no es un objeto")
                continue
            for campo in ("clause_id", "clause_name", "present", "quality"):
                if campo not in item:
                    fallos.append(
                        f"mandatory_clauses_check[{i}] no trae '{campo}'",
                    )
            if not isinstance(item.get("present"), bool):
                fallos.append(
                    f"mandatory_clauses_check[{i}].present no es booleano: "
                    f"{item.get('present')!r}",
                )
            if item.get("quality") not in _CALIDADES:
                fallos.append(
                    f"mandatory_clauses_check[{i}].quality fuera del "
                    f"enumerado: {item.get('quality')!r}",
                )
            cid = item.get("clause_id")
            if isinstance(cid, str):
                por_id[cid] = item

    catalogo = list(_comun.extra(entry, "catalogo_obligatorio", []))
    sin_cubrir = [cid for cid in catalogo if cid not in por_id]
    if sin_cubrir:
        fallos.append(
            f"el checklist no cubre {len(sin_cubrir)} cláusula(s) "
            f"obligatoria(s) de esta categoría: {sorted(sin_cubrir)[:5]}",
        )

    for cid in _comun.extra(entry, "clausulas_ausentes_esperadas", []):
        item = por_id.get(cid)
        if item is None:
            continue  # ya contado como cobertura no cubierta
        if item.get("present") is not False or item.get("quality") != "ausente":
            fallos.append(
                f"'{cid}' no está en el contrato y el modelo la reporta como "
                f"present={item.get('present')!r} "
                f"quality={item.get('quality')!r}",
            )

    for cid in _comun.extra(entry, "clausulas_presentes_completas_esperadas", []):
        item = por_id.get(cid)
        if item is None:
            continue
        if item.get("present") is not True or item.get("quality") != "completo":
            fallos.append(
                f"'{cid}' está completa en el contrato y el modelo la "
                f"reporta como present={item.get('present')!r} "
                f"quality={item.get('quality')!r}",
            )

    for cid in _comun.extra(entry, "clausulas_deficientes_esperadas", []):
        item = por_id.get(cid)
        if item is None:
            continue
        if item.get("quality") == "completo":
            fallos.append(
                f"'{cid}' existe pero no cumple, y el modelo la da por "
                f"completa",
            )

    # ── Huecos sectoriales ───────────────────────────────────────────────
    gaps = actual.get("sector_specific_gaps")
    if not isinstance(gaps, list):
        fallos.append("sector_specific_gaps no es una lista")
        gaps = []
    else:
        if len(gaps) > _MAX_GAPS:
            fallos.append(
                f"sector_specific_gaps con {len(gaps)} (tope {_MAX_GAPS})",
            )
        for i, gap in enumerate(gaps):
            if not isinstance(gap, dict):
                fallos.append(f"sector_specific_gaps[{i}] no es un objeto")
                continue
            for campo in ("requirement", "description", "severity"):
                if campo not in gap:
                    fallos.append(
                        f"sector_specific_gaps[{i}] no trae '{campo}'",
                    )
            if gap.get("severity") not in _SEVERIDADES:
                fallos.append(
                    f"sector_specific_gaps[{i}].severity fuera del "
                    f"enumerado: {gap.get('severity')!r}",
                )
    g_min = int(_comun.extra(entry, "gaps_sectoriales_minimos", 0))
    if len(gaps) < g_min:
        fallos.append(
            f"huecos sectoriales = {len(gaps)}; el dataset exige al menos "
            f"{g_min} para este sector",
        )

    # ── Adenda: sólo estructura, NO calidad de la prosa ──────────────────
    adenda = actual.get("addendum_text")
    if not isinstance(adenda, str) or not adenda.strip():
        fallos.append("addendum_text vacío o no es texto")
    elif len(adenda) > _MAX_ADENDA:
        fallos.append(
            f"addendum_text de {len(adenda)} caracteres (tope {_MAX_ADENDA})",
        )

    # ── Recomendación ────────────────────────────────────────────────────
    recomendacion = actual.get("recommendation")
    if not isinstance(recomendacion, dict):
        fallos.append("recommendation no es un objeto")
    else:
        accion = recomendacion.get("action")
        if accion not in _ACCIONES:
            fallos.append(
                f"recommendation.action fuera del enumerado: {accion!r}",
            )
        acciones_ok = list(_comun.extra(entry, "acciones_aceptables", []))
        if acciones_ok and accion not in acciones_ok:
            fallos.append(
                f"recommendation.action = {accion!r}; el dataset acepta "
                f"{acciones_ok}",
            )
        urgencia = recomendacion.get("urgency")
        if urgencia not in _URGENCIAS:
            fallos.append(
                f"recommendation.urgency fuera del enumerado: {urgencia!r}",
            )
        urgencias_ok = list(_comun.extra(entry, "urgencias_aceptables", []))
        if urgencias_ok and urgencia not in urgencias_ok:
            fallos.append(
                f"recommendation.urgency = {urgencia!r}; el dataset acepta "
                f"{urgencias_ok}",
            )
        rat = recomendacion.get("rationale")
        if not isinstance(rat, str) or not rat.strip():
            fallos.append("recommendation.rationale vacío o no es texto")
        elif len(rat) > _MAX_RATIONALE:
            fallos.append(
                f"recommendation.rationale de {len(rat)} caracteres "
                f"(tope {_MAX_RATIONALE})",
            )

    # ── Alertas ──────────────────────────────────────────────────────────
    alertas = actual.get("red_flags")
    if not isinstance(alertas, list):
        fallos.append("red_flags no es una lista")
        alertas = []
    else:
        if len(alertas) > _MAX_RED_FLAGS:
            fallos.append(
                f"red_flags con {len(alertas)} (tope {_MAX_RED_FLAGS})",
            )
        for i, alerta in enumerate(alertas):
            if not isinstance(alerta, str):
                fallos.append(f"red_flags[{i}] no es texto")
            elif len(alerta) > _MAX_RED_FLAG_CHARS:
                fallos.append(
                    f"red_flags[{i}] de {len(alerta)} caracteres "
                    f"(tope {_MAX_RED_FLAG_CHARS})",
                )
    f_min = int(_comun.extra(entry, "red_flags_minimas", 0))
    if len(alertas) < f_min:
        fallos.append(
            f"alertas = {len(alertas)}; el dataset exige al menos {f_min} "
            f"para este contrato",
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
            "compliance_score": score,
            "compliance_level": nivel,
            "clausulas_reportadas": len(por_id),
            "clausulas_del_catalogo": len(catalogo),
            "huecos_sectoriales": len(gaps),
            "alertas": len(alertas),
        },
    )


def salida_sintetica(entry: GoldenDatasetEntry) -> dict[str, Any]:
    """Respuesta perfecta para `entry`, con la forma que devuelve A6."""
    catalogo = list(_comun.extra(entry, "catalogo_obligatorio", []))
    ausentes = set(_comun.extra(entry, "clausulas_ausentes_esperadas", []))
    deficientes = set(_comun.extra(entry, "clausulas_deficientes_esperadas", []))

    checklist: list[dict[str, Any]] = []
    for cid in catalogo:
        if cid in ausentes:
            presente, calidad = False, "ausente"
        elif cid in deficientes:
            presente, calidad = True, "incompleto"
        else:
            presente, calidad = True, "completo"
        checklist.append({
            "clause_id": cid,
            "clause_name": cid.replace("_", " "),
            "present": presente,
            "quality": calidad,
        })

    s_min = int(_comun.extra(entry, "compliance_score_minimo", 0))
    s_max = int(_comun.extra(entry, "compliance_score_maximo", 100))
    niveles = list(_comun.extra(entry, "niveles_aceptables", ["parcial"]))
    acciones = list(_comun.extra(entry, "acciones_aceptables", []))
    urgencias = list(_comun.extra(entry, "urgencias_aceptables", []))
    g_min = int(_comun.extra(entry, "gaps_sectoriales_minimos", 0))
    f_min = int(_comun.extra(entry, "red_flags_minimas", 0))

    return {
        "compliance_score": (s_min + s_max) // 2,
        "compliance_level": niveles[0] if niveles else "parcial",
        "mandatory_clauses_check": checklist,
        "sector_specific_gaps": [
            {
                "requirement": f"Requisito sectorial sintético {i + 1}",
                "description": "Generado por el gate del arnés.",
                "severity": "alto",
            }
            for i in range(min(g_min, _MAX_GAPS))
        ],
        "addendum_text": (
            f"Adenda sintética del gate del arnés para la entrada "
            f"{entry.id}. No procede de ninguna llamada al modelo."
        ),
        "recommendation": {
            "action": acciones[0] if acciones else "firmar_adenda",
            "urgency": urgencias[0] if urgencias else "1_mes",
            "rationale": "Justificación sintética del gate del arnés.",
        },
        "red_flags": [
            f"Alerta sintética {i + 1} para {entry.id}."
            for i in range(min(f_min, _MAX_RED_FLAGS))
        ],
    }


register_evaluator(_AGENT_NAME, agent_06_contratos_evaluator)
register_synthetic_output(_AGENT_NAME, salida_sintetica)
