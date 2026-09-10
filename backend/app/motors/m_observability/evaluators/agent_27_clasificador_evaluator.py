"""Evaluador del golden dataset de `agent_27_clasificador` (BLOQUE D · D2).

Qué mide, exactamente
---------------------
La salida estructurada de `Agent27ClasificadorIDMS.invoke(...)['parsed']`,
es decir el JSON crudo del modelo. Todas las comprobaciones son de igualdad,
de pertenencia a un conjunto cerrado o de rango numérico: **ninguna juzga
prosa**. El campo `reasoning` sólo se mira para verificar que existe y que
respeta el tope de 250 caracteres que el propio agente impone; su contenido
no se puntúa.

Por qué este agente y no otro: su respuesta es una clasificación sobre un
catálogo cerrado de 15 códigos de carpeta más una confianza en [0,1]. Eso se
comprueba sin ambigüedad y sin pedirle a nadie que opine.

Dos decisiones de diseño con su contrapartida
---------------------------------------------
1. **Se acepta un conjunto de carpetas, no una sola.** Las entradas límite
   del dataset son documentos que encajan de verdad en dos carpetas del
   catálogo §2.15 (un contrato con proveedor cabe en 00_Contractual y en
   12_Proveedores). Exigir una sola respuesta convertiría una respuesta
   defendible en un fallo, y el número que saliera mediría la arbitrariedad
   del curador, no al modelo. Contrapartida: el criterio es más laxo en esas
   entradas, y por eso a cambio se les exige declarar la duda (confianza por
   debajo de 0,85 y al menos una alternativa).

2. **La bandera de revisión humana se DERIVA, no se copia.** En producción,
   `_enforce_review_flag` recalcula `requires_human_review` a partir de la
   confianza y de las alternativas, así que el valor que el modelo escriba
   en ese campo se sobrescribe siempre. Comparar el campo tal cual mediría
   algo que el código repara. Lo que aquí se compara es la bandera QUE SALE
   DE APLICAR LA REGLA a la confianza y a las alternativas del modelo: eso
   sí llega al usuario. Contrapartida: si el modelo se contradice a sí mismo
   (confianza 0,95 y bandera a true) esta entrada no falla por ello; la
   contradicción se anota en `actual_summary` para que se vea, sin castigar
   un defecto que la producción ya corrige.

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


_AGENT_NAME = "agent_27_clasificador"

# Las 7 claves que `Agent27ClasificadorIDMS._validate_schema` exige.
_CLAVES_OBLIGATORIAS: tuple[str, ...] = (
    "suggested_folder_code",
    "suggested_folder_name",
    "confidence",
    "reasoning",
    "suggested_tags",
    "alternative_folders",
    "requires_human_review",
)

# Copia deliberada de `FOLDER_NAMES` de
# backend/app/agents/agent_27_clasificador.py. No se importa el módulo del
# agente porque el job `evals-arnes` instala sólo pydantic y pyyaml, y ese
# módulo arrastra SQLAlchemy. La copia la vigila
# backend/tests/motors/m_observability/test_evaluadores_agentes.py, que
# importa ambos y exige igualdad exacta.
_NOMBRES_CARPETA: dict[str, str] = {
    "00": "Contractual",
    "01": "Gobierno",
    "02": "Categorizacion",
    "03": "Analisis_Riesgos",
    "04": "Declaracion_Aplicabilidad",
    "05": "Plan_Adecuacion",
    "06": "Normativa",
    "07": "Procedimientos",
    "08": "Registros_Operativos",
    "09": "Evidencias",
    "10": "Continuidad",
    "11": "Formacion",
    "12": "Proveedores",
    "13": "Informes_Tecnicos",
    "99": "Misc",
}

# Copias de `_AUTO_APPROVABLE_THRESHOLD` y `_ALT_REVIEW_THRESHOLD` del mismo
# módulo del agente (mismo motivo y misma vigilancia que el catálogo).
_UMBRAL_AUTO_APROBABLE = 0.85
_UMBRAL_ALTERNATIVA_RELEVANTE = 0.50

_TIPOS_TAG = {"measure_ens", "sector", "normativa"}
_MAX_TAGS = 5
_MAX_ALTERNATIVAS = 2
_MAX_REASONING = 250


def _revision_derivada(confianza: float, alternativas: list[Any]) -> bool:
    """Reproduce la regla de `_enforce_review_flag` del agente.

    Revisión humana si la confianza no llega al umbral de auto-aprobación
    O si alguna alternativa es lo bastante fuerte como para competir.
    """
    for alt in alternativas:
        if not isinstance(alt, dict):
            continue
        conf_alt = _comun.numero(alt.get("confidence"))
        if conf_alt is not None and conf_alt >= _UMBRAL_ALTERNATIVA_RELEVANTE:
            return True
    return confianza < _UMBRAL_AUTO_APROBABLE


def agent_27_clasificador_evaluator(
    entry: GoldenDatasetEntry, actual: Any,
) -> EntryEvalResult:
    """Comprobación determinista de una clasificación de documento."""
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

    fallos: list[str] = []

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

    # ── Carpeta ──────────────────────────────────────────────────────────
    codigo = actual.get("suggested_folder_code")
    aceptables = list(_comun.extra(entry, "carpetas_aceptables", []))
    if codigo not in _NOMBRES_CARPETA:
        fallos.append(
            f"suggested_folder_code fuera del catálogo de 15 carpetas: "
            f"{codigo!r}",
        )
    elif aceptables and codigo not in aceptables:
        fallos.append(
            f"carpeta {codigo} ({_NOMBRES_CARPETA[codigo]}); el dataset "
            f"acepta {aceptables}",
        )

    nombre = actual.get("suggested_folder_name")
    if codigo in _NOMBRES_CARPETA and nombre != _NOMBRES_CARPETA[codigo]:
        fallos.append(
            f"suggested_folder_name no corresponde al código: {nombre!r} "
            f"cuando {codigo} es {_NOMBRES_CARPETA[codigo]!r}",
        )

    # ── Confianza ────────────────────────────────────────────────────────
    confianza = _comun.numero(actual.get("confidence"))
    conf_min = float(_comun.extra(entry, "confianza_minima", 0.0))
    conf_max = float(_comun.extra(entry, "confianza_maxima", 1.0))
    if confianza is None:
        fallos.append(f"confidence no es numérica: {actual.get('confidence')!r}")
        confianza = 0.0
    elif not (0.0 <= confianza <= 1.0):
        fallos.append(f"confidence fuera de [0,1]: {confianza}")
    elif not (conf_min <= confianza <= conf_max):
        fallos.append(
            f"confidence {confianza} fuera de la banda curada "
            f"[{conf_min}, {conf_max}]",
        )

    # ── Reasoning: sólo existencia y tope de longitud, NO contenido ──────
    reasoning = actual.get("reasoning")
    if not isinstance(reasoning, str) or not reasoning.strip():
        fallos.append("reasoning vacío o no es texto")
    elif len(reasoning) > _MAX_REASONING:
        fallos.append(
            f"reasoning de {len(reasoning)} caracteres (tope {_MAX_REASONING})",
        )

    # ── Etiquetas ────────────────────────────────────────────────────────
    tags = actual.get("suggested_tags")
    if not isinstance(tags, list):
        fallos.append("suggested_tags no es una lista")
    else:
        if len(tags) > _MAX_TAGS:
            fallos.append(f"suggested_tags con {len(tags)} (tope {_MAX_TAGS})")
        for i, tag in enumerate(tags):
            if not isinstance(tag, dict):
                fallos.append(f"suggested_tags[{i}] no es un objeto")
                continue
            if tag.get("tag_type") not in _TIPOS_TAG:
                fallos.append(
                    f"suggested_tags[{i}].tag_type fuera del enumerado: "
                    f"{tag.get('tag_type')!r}",
                )
            if not isinstance(tag.get("value"), str):
                fallos.append(f"suggested_tags[{i}].value no es texto")
            conf_tag = _comun.numero(tag.get("confidence"))
            if conf_tag is None or not (0.0 <= conf_tag <= 1.0):
                fallos.append(
                    f"suggested_tags[{i}].confidence fuera de [0,1]: "
                    f"{tag.get('confidence')!r}",
                )

    # ── Alternativas ─────────────────────────────────────────────────────
    alternativas = actual.get("alternative_folders")
    if not isinstance(alternativas, list):
        fallos.append("alternative_folders no es una lista")
        alternativas = []
    else:
        if len(alternativas) > _MAX_ALTERNATIVAS:
            fallos.append(
                f"alternative_folders con {len(alternativas)} "
                f"(tope {_MAX_ALTERNATIVAS})",
            )
        for i, alt in enumerate(alternativas):
            if not isinstance(alt, dict):
                fallos.append(f"alternative_folders[{i}] no es un objeto")
                continue
            if alt.get("folder_code") not in _NOMBRES_CARPETA:
                fallos.append(
                    f"alternative_folders[{i}].folder_code fuera del "
                    f"catálogo: {alt.get('folder_code')!r}",
                )
            conf_alt = _comun.numero(alt.get("confidence"))
            if conf_alt is None or not (0.0 <= conf_alt <= 1.0):
                fallos.append(
                    f"alternative_folders[{i}].confidence fuera de [0,1]: "
                    f"{alt.get('confidence')!r}",
                )
    minimo_alt = int(_comun.extra(entry, "alternativas_minimas", 0))
    if len(alternativas) < minimo_alt:
        fallos.append(
            f"el documento es ambiguo y el dataset exige al menos "
            f"{minimo_alt} alternativa(s); vinieron {len(alternativas)}",
        )

    # ── Revisión humana derivada (ver docstring, decisión 2) ─────────────
    esperada_revision = _comun.extra(entry, "requiere_revision_humana", None)
    derivada = _revision_derivada(confianza, alternativas)
    if isinstance(esperada_revision, bool) and derivada is not esperada_revision:
        fallos.append(
            f"la regla de revisión aplicada a esta salida da "
            f"requires_human_review={derivada} y el dataset espera "
            f"{esperada_revision}",
        )

    # ── Frases canónicas (hoy vacías en este dataset) ────────────────────
    ausentes, prohibidas = _comun.frases(entry, actual)
    if ausentes:
        fallos.append(f"faltan frases requeridas: {ausentes[:3]}")
    if prohibidas:
        fallos.append(f"aparecen frases prohibidas: {prohibidas[:3]}")

    declarada = actual.get("requires_human_review")
    return EntryEvalResult(
        entry_id=entry.id,
        category=entry.category,
        passed=not fallos,
        diff_summary="; ".join(fallos) if fallos else "ok",
        required_missing=ausentes,
        forbidden_present_unflagged=prohibidas,
        actual_summary={
            "carpeta": codigo,
            "confianza": confianza,
            "alternativas": len(alternativas),
            "revision_declarada_por_el_modelo": declarada,
            "revision_derivada_de_la_regla": derivada,
            "el_modelo_se_contradice": (
                isinstance(declarada, bool) and declarada is not derivada
            ),
        },
    )


def salida_sintetica(entry: GoldenDatasetEntry) -> dict[str, Any]:
    """Respuesta perfecta para `entry`, con la forma que devuelve A27.

    La usa el gate de auto-consistencia del arnés. La confianza se sitúa en
    el punto medio de la banda curada, que por el invariante del dataset
    (banda por encima de 0,85 cuando no toca revisión y por debajo cuando
    sí) cae siempre del lado correcto de la regla de revisión.
    """
    aceptables = list(_comun.extra(entry, "carpetas_aceptables", ["99"]))
    codigo = aceptables[0] if aceptables else "99"
    conf_min = float(_comun.extra(entry, "confianza_minima", 0.0))
    conf_max = float(_comun.extra(entry, "confianza_maxima", 1.0))
    confianza = round((conf_min + conf_max) / 2, 4)

    minimo_alt = int(_comun.extra(entry, "alternativas_minimas", 0))
    alternativas: list[dict[str, Any]] = []
    for otro in aceptables[1:] + ["99", "01"]:
        if len(alternativas) >= min(minimo_alt, _MAX_ALTERNATIVAS):
            break
        if otro == codigo or any(a["folder_code"] == otro for a in alternativas):
            continue
        alternativas.append({
            "folder_code": otro,
            "folder_name": _NOMBRES_CARPETA[otro],
            # Por debajo del umbral de alternativa relevante para no forzar
            # la bandera de revisión por esta vía: quien la decide en la
            # salida sintética es la confianza principal.
            "confidence": 0.4,
        })

    return {
        "suggested_folder_code": codigo,
        "suggested_folder_name": _NOMBRES_CARPETA[codigo],
        "confidence": confianza,
        "reasoning": (
            f"Salida sintética del gate del arnés para la entrada "
            f"{entry.id}. No procede de ninguna llamada al modelo."
        )[:_MAX_REASONING],
        "suggested_tags": [],
        "alternative_folders": alternativas,
        "requires_human_review": _revision_derivada(confianza, alternativas),
    }


register_evaluator(_AGENT_NAME, agent_27_clasificador_evaluator)
register_synthetic_output(_AGENT_NAME, salida_sintetica)
