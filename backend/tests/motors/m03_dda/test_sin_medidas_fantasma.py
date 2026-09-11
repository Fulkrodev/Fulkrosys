"""O1 · ningun codigo de medida ENS inexistente en producto ni en entregables.

QUE PASABA
    El RD 311/2022 derogo al RD 3/2010, y con el se fueron medidas que la guia
    CCN-STIC 804 v2017 aun citaba. El repositorio arrastraba 20 codigos que NO
    EXISTEN en el Anexo II vigente, en 64 sitios vivos. Lo grave no era la
    cifra: era DONDE estaban.

      · Plantillas de entregables FIRMABLES: E-106 y E-207 (copias de
        seguridad) citaban "mp.info.9"; E-120 (claves criptograficas) tambien;
        E-700 (auditoria interna) citaba "las medidas mp.aud.1 / mp.aud.2 /
        mp.aud.3 / mp.aud.4 del Anexo II", una familia entera que no existe.
      · Prompts de agentes: `agent_11_auditor_virtual` y
        `agent_27_clasificador_idms` ensenyaban al modelo, como ejemplo, que la
        medida de MFA es "mp.acc.2". Un ejemplo few-shot no es texto muerto: el
        modelo lo reproduce sobre entradas reales.
      · Tooltips de onboarding mostrados al cliente: "ENS exige ... (op.acc.11)".
      · Catalogos PCE de nube: tres overlays colgando de "mp.info.9.pce-*".

    Todo eso son afirmaciones normativas falsas puestas delante de un cliente o
    de un auditor. La familia correcta de cada una esta en el commit que lo
    arreglo.

LA FUENTE DE VERDAD
    `backend/tests/fixtures/anexo2_boe_verificado.json`, extraido del PDF del
    BOE (ver `backend/scripts/extraer_anexo2_boe.py`). 73 codigos, ni uno mas.

QUE QUEDA FUERA DEL BARRIDO, Y POR QUE
    `docs/spec/` y `docs/archive/` son documentos de ENTRADA historicos -- la
    especificacion con la que se construyo esto, anterior al alineamiento con el
    RD 311/2022 -- y no salidas del producto. Reescribirlos seria falsear el
    historial. Que citen medidas derogadas es un hecho de su fecha, no un
    defecto del producto de hoy.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

# parents[4] es la raiz del repo (el fichero vive en backend/tests/motors/m03_dda/).
RAIZ = Path(__file__).resolve().parents[4]
FIXTURE = RAIZ / "backend/tests/fixtures/anexo2_boe_verificado.json"

CODIGO = re.compile(r"\b((?:org|op|mp)\.(?:[a-z]{1,6}\.)?\d{1,2})\b")

# Lineas que MENCIONAN un codigo muerto justamente para decir que lo esta.
DOCUMENTA_EL_ARREGLO = re.compile(
    r"(no existe|NO EXISTE|inexistente|fantasma|derogad|RD 3/2010|v2017|"
    r"obsolet|fosil|skip-list|descart|era \w+\.\w+)",
    re.IGNORECASE,
)

# Producto vivo + entregables. NO docs/spec ni docs/archive (ver docstring).
AMBITO = (
    "backend/app",
    "backend/mcp_servers",
    "backend/scripts",
    "frontend/components",
    "frontend/lib",
    "frontend/app",
    "docs/catalogs",
)
EXTENSIONES = {".py", ".yaml", ".yml", ".json", ".ts", ".tsx", ".md"}
EXCLUIR = ("node_modules", "__pycache__", "/migrations/", "/tests/")


def _codigos_validos() -> set[str]:
    return {m["codigo"] for m in json.loads(FIXTURE.read_text("utf-8"))["medidas"]}


def _ficheros() -> list[Path]:
    out: list[Path] = []
    for rel in AMBITO:
        base = RAIZ / rel
        if not base.exists():
            continue
        for root, _dirs, files in os.walk(base):
            if any(x in root + "/" for x in EXCLUIR):
                continue
            for f in files:
                p = Path(root) / f
                if p.suffix in EXTENSIONES:
                    out.append(p)
    return out


def test_ningun_codigo_de_medida_inexistente_en_producto_ni_entregables():
    validos = _codigos_validos()
    ficheros = _ficheros()
    # Anti-vacuidad: si el ambito se rompe, el test pasaria sin mirar nada.
    assert len(ficheros) > 800, (
        f"solo {len(ficheros)} ficheros barridos: el ambito esta mal y este "
        "test no comprueba nada"
    )

    culpables: list[str] = []
    for p in ficheros:
        try:
            texto = p.read_text("utf-8", errors="ignore")
        except OSError:
            continue
        for i, linea in enumerate(texto.splitlines(), 1):
            if DOCUMENTA_EL_ARREGLO.search(linea):
                continue
            malos = sorted({c for c in CODIGO.findall(linea) if c not in validos})
            if malos:
                culpables.append(
                    f"{p.relative_to(RAIZ)}:{i}: {malos} -> {linea.strip()[:90]}"
                )
    assert not culpables, (
        f"{len(culpables)} citas a medidas que NO existen en el Anexo II del "
        "RD 311/2022:\n" + "\n".join(culpables)
    )


def test_el_fixture_del_boe_sigue_teniendo_las_73():
    assert len(_codigos_validos()) == 73
