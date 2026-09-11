"""O2 · los dorados se comprueban contra la norma, no contra si mismos.

EL DEFECTO ESTRUCTURAL
    El job `evals-arnes` corrio 24 veces en verde y NO PUEDE detectar un dorado
    equivocado, por construccion: alimenta al evaluador con
    `salida_sintetica(entry)`, que es una copia literal de `expected_output`.
    Comparar la respuesta esperada consigo misma da 10/10 siempre.

    Es el mismo patron que la puerta de accesibilidad sobre una pagina rota: un
    verde tranquilizador que no mide nada.

LO QUE ESO PERMITIO
    Tres entradas del dorado de `deliverable_text_auditor` citaban medidas que
    NO existen en el RD 311/2022 (a11-004 y a11-006 con `mp.s.8`, a11-005 con
    `mp.s.9`; la familia `mp.s` llega a `mp.s.4`). Dos de ellas etiquetadas
    `PASS_AUDITOR_READY`.

    Medido con el evaluador REAL sobre el dataset pre-arreglo: un modelo que
    aprobara un entregable con `mp.s.8` contaba como ACIERTO, y uno que
    detectara la medida inexistente contaba como FALLO. El baremo premiaba lo
    contrario de lo que se quiere. Y esas dos entradas valian exactamente el
    margen completo de tolerancia del umbral (2 fallos de 10, min_pass_rate
    0,80).

    El gate LLM nunca llego a ejecutarse -- no hay `ANTHROPIC_API_KEY` en el
    repositorio --, asi que el danyo no fue un verde falso de CI: fue el baremo.

LO QUE COMPRUEBA ESTE TEST, que el arnes no puede
    Coherencia del dorado contra una fuente EXTERNA al propio dorado: el fixture
    del Anexo II extraido del PDF del BOE.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[4]
DORADOS = RAIZ / "docs/catalogs/golden_datasets"
FIXTURE = RAIZ / "backend/tests/fixtures/anexo2_boe_verificado.json"

CODIGO = re.compile(r"\b((?:org|op|mp)\.(?:[a-z]{1,6}\.)?\d{1,2})\b")


def _validos() -> set[str]:
    return {m["codigo"] for m in json.loads(FIXTURE.read_text("utf-8"))["medidas"]}


def _datasets() -> list[Path]:
    return sorted(DORADOS.rglob("*.json"))


def test_hay_dorados_que_comprobar():
    """Anti-vacuidad: sin ficheros, todo lo de abajo pasaria en blanco."""
    assert len(_datasets()) >= 4


@pytest.mark.parametrize("ruta", _datasets(), ids=lambda p: p.parent.name)
def test_ningun_dorado_cita_medidas_inexistentes(ruta: Path):
    validos = _validos()
    datos = json.loads(ruta.read_text("utf-8"))
    malos: list[str] = []
    for entrada in datos.get("entries", []):
        # La nota de revision del propio dataset SI puede nombrar los codigos
        # malos para explicar que se corrigieron; las ENTRADAS no.
        texto = json.dumps(entrada, ensure_ascii=False)
        for codigo in sorted(set(CODIGO.findall(texto))):
            if codigo not in validos:
                malos.append(f"{entrada.get('id', '?')}: {codigo}")
    assert not malos, (
        f"{ruta.relative_to(RAIZ)} cita medidas que no existen en el Anexo II "
        f"del RD 311/2022: {malos}"
    )


def test_una_entrada_aprobada_no_puede_citar_una_medida_inexistente():
    """El caso concreto que el arnes premiaba al reves.

    Redundante con el test de arriba a proposito: si alguien relaja aquel
    barrido, este sigue cubriendo el caso que mas danyo hace, que es el de una
    entrada etiquetada como APTA.
    """
    validos = _validos()
    ruta = DORADOS / "deliverable_text_auditor/v1.json"
    datos = json.loads(ruta.read_text("utf-8"))
    aprobadas = [
        e for e in datos["entries"]
        if (e.get("expected_output") or {}).get("verdict") == "PASS_AUDITOR_READY"
    ]
    assert aprobadas, "no hay entradas PASS_AUDITOR_READY: el dataset cambio de forma"
    malos = []
    for e in aprobadas:
        texto = json.dumps(e, ensure_ascii=False)
        malos += [f"{e.get('id')}: {c}" for c in sorted(set(CODIGO.findall(texto)))
                  if c not in validos]
    assert not malos, (
        "entradas etiquetadas PASS_AUDITOR_READY que citan medidas inexistentes "
        f"-- el baremo premiaria aprobarlas: {malos}"
    )
