"""Ningún camino a un documento rellena un valor normativo que no tiene.

EL PATRÓN, dicho de una vez
    Es el que ha atravesado la campaña entera, con tres caras distintas:

      · el ``None`` convertido en BÁSICA (bloque O1, cuatro generadores)
      · el acta E-012 declarando MEDIO una dimensión que nadie valoró (O2)
      · las 12 de 13 justificaciones de la DdA culpando al eje equivocado (Q1)

    Siempre la misma forma: un valor que llega a un documento firmable **sin
    venir de la fuente que lo decide**. Y siempre el mismo remedio aparente
    —arreglar el sitio encontrado— seguido del mismo resultado: aparece otro.

    O1 construyó el remedio bueno (``CategoriaNoDeterminadaError``) y lo aplicó
    a los cinco generadores que encontró leyendo. Lo que faltaba era esto: una
    guarda que barra el árbol entero y **falle cuando aparezca uno nuevo**.

QUÉ HACE
    Recorre ``backend/app`` buscando las formas de relleno
    (``or "MEDIA"``, ``COALESCE(..., 'BASICA')``, ``.get(..., "BAJO")``,
    un campo de Pydantic con nivel por defecto) sobre el vocabulario normativo
    del RD 311/2022 —las tres categorías del Anexo I y los tres niveles de
    dimensión—, y falla si encuentra una que no esté en la lista de abajo.

    La lista NO es una válvula de escape: cada línea que hay en ella está ahí
    con el motivo escrito, y el motivo es siempre el mismo tipo de cosa —el
    valor no viaja a ningún documento, decide qué se enseña o qué se bloquea—.
    Añadir una línea a esta lista es una decisión que se lee en la revisión;
    dejar el relleno suelto, no.
"""
from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]

_NORMATIVO = r'(BASICA|MEDIA|ALTA|BAJO|MEDIO|ALTO)'
_PATRONES = (
    re.compile(r'\bor\s+["\']' + _NORMATIVO + r'["\']'),
    re.compile(r"COALESCE\([^)]*,\s*'" + _NORMATIVO + r"'\s*\)", re.I),
    re.compile(r'\.get\([^)]*,\s*["\']' + _NORMATIVO + r'["\']\s*\)'),
    re.compile(r':\s*\w*Type\s*=\s*["\']' + _NORMATIVO + r'["\']'),
)

# ─────────────────────────────────────────────────────────────────────────────
# Lista blanca · fichero -> motivo por el que ese relleno NO es una afirmación
# normativa. Se compara por FICHERO y se exige que el motivo esté escrito.
# ─────────────────────────────────────────────────────────────────────────────
PERMITIDOS: dict[str, str] = {
    "backend/app/core/feature_flags/api.py":
        "resuelve qué capacidades de la interfaz se ofrecen; no viaja a ningún "
        "documento ni se imprime como categoría del sistema",
    "backend/app/core/feature_flags/dependencies.py":
        "misma resolución de capacidades, en la dependencia de FastAPI",
    "backend/app/core/feature_flags/service.py":
        "misma resolución de capacidades, en el servicio",
    "backend/app/core/workflow_blocking_service.py":
        "decide qué pasos del flujo se bloquean; el valor no se imprime",
    "backend/app/motors/m08_verification/pentest_auto_trigger.py":
        "cae a ALTO, que es la verificación MÁS exigente: el relleno escala, no "
        "rebaja, y por tanto no puede declarar por debajo",
    "backend/app/motors/m21_diagnosis/dashboard_service.py":
        "cifra de un panel de la interfaz; no se emite en ningún entregable",
    "backend/app/motors/m21_diagnosis/paso5_orchestrator.py":
        "texto de una tarea sugerida en pantalla, no un documento",
    "backend/app/motors/m21_portal_cliente/task_service.py":
        "elige la plantilla de tareas del portal; no se imprime como categoría",
    "backend/app/motors/m21_portal_cliente/task_templates_loader.py":
        "mismo cargador de plantillas de tareas del portal",
    "backend/app/motors/m23_retainer/paso2_extensions.py":
        "sugiere el tramo de retainer, que es una decisión comercial revisable "
        "y no una declaración normativa",
    "backend/app/motors/m27_conformity/catalogs/__init__.py":
        "filtro por defecto al recorrer el catálogo en memoria; no persiste ni "
        "se imprime",
    "backend/app/motors/m_observability/golden_eval_runs_service.py":
        "metadato del arnés de evaluación de agentes; no sale del arnés",
}


def _lineas_de_codigo(texto: str):
    """Sólo CÓDIGO: fuera comentarios y fuera cadenas de varias líneas.

    Existe porque este mismo barrido se disparó a sí mismo en su primera
    ejecución: los comentarios que explican el patrón prohibido CONTIENEN el
    patrón prohibido. Le pasó cuatro veces a la campaña anterior con sus
    propias guardas. Una guarda que no distingue el código de la explicación
    del código no vale, así que aquí se tokeniza de verdad.
    """
    import io
    import tokenize

    lineas = texto.splitlines()
    fuera = set()
    try:
        for tok in tokenize.generate_tokens(io.StringIO(texto).readline):
            if tok.type == tokenize.COMMENT:
                fuera.add(tok.start[0])
            elif tok.type == tokenize.STRING and tok.end[0] > tok.start[0]:
                fuera.update(range(tok.start[0], tok.end[0] + 1))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return  # fichero no tokenizable: no se inventa un veredicto
    for numero, linea in enumerate(lineas, 1):
        if numero in fuera:
            continue
        limpio = linea.split('#', 1)[0]
        if limpio.strip():
            yield numero, limpio


def _hits() -> list[tuple[str, int, str]]:
    ficheros = sorted((RAIZ / "backend" / "app").rglob("*.py"))
    assert len(ficheros) > 500, (
        f"solo {len(ficheros)} ficheros barridos: la ruta está mal y este test "
        "no está comprobando nada"
    )
    fuera = []
    for f in ficheros:
        rel = str(f.relative_to(RAIZ))
        for i, linea in _lineas_de_codigo(
            f.read_text(encoding="utf-8", errors="ignore")
        ):
            if any(p.search(linea) for p in _PATRONES):
                fuera.append((rel, i, linea.strip()[:120]))
    return fuera


def test_la_lista_blanca_no_tiene_entradas_sin_motivo():
    for ruta, motivo in PERMITIDOS.items():
        assert len(motivo.split()) >= 6, (
            f"{ruta} está en la lista blanca con un motivo de una línea: "
            "escríbelo entero o quítalo de la lista"
        )


def test_la_lista_blanca_no_tiene_entradas_muertas():
    """Una excepción que ya no aplica es una puerta abierta sin vigilancia."""
    vivos = {h[0] for h in _hits()}
    muertas = sorted(set(PERMITIDOS) - vivos)
    assert not muertas, (
        "estas rutas están en la lista blanca y ya no tienen ningún relleno: "
        f"bórralas de la lista · {muertas}"
    )


def test_ningun_relleno_normativo_nuevo():
    nuevos = [h for h in _hits() if h[0] not in PERMITIDOS]
    assert not nuevos, (
        "un valor normativo se rellena por defecto en un sitio que no está "
        "justificado. Si de aquí sale un dato que acaba en un documento, "
        "levanta `CategoriaNoDeterminadaError` (o el error del motor) en vez de "
        "rellenar; si no sale de la interfaz, añádelo a PERMITIDOS con el "
        "motivo escrito.\n" + "\n".join(f"  {r}:{n}: {t}" for r, n, t in nuevos)
    )
