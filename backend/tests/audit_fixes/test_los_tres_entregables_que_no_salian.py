"""Los tres entregables de 28 que no salían: dos arreglados, uno con motivo.

E-001 · FICHA DE SEGUIMIENTO · ARREGLADO
    Usa 21 variables ``ficha.*`` y 10 ``proyecto.*``, y **nadie las
    construía**: el render abortaba con ``'ficha' is undefined`` y el endpoint
    devolvía un 500 opaco («None is undefined» en el panel). Ahora hay productor
    (``ficha_seguimiento_context``) que las saca del plan del proyecto, del
    parte de horas y de los hitos de facturación, y lo que no consta lo dice con
    esas palabras en vez de inventar una cifra — que es la regla de toda la
    campaña, y esta ficha la recibe el cliente.

E-702 / E-703 · INFORMES DE VERIFICACIÓN · CERRADO CON MOTIVO
    Piden ``run.*`` y ``score.*``: el resultado de una EJECUCIÓN de verificación,
    no datos del proyecto. Que no se generen sin ella es lo correcto — un informe
    de verificación sin verificación detrás sería un documento inventado, que es
    justo el defecto que esta campaña persigue. Tienen productor propio
    (``VerificationReportGenerator.generate_report``) y su endpoint.

    Lo que sí era un defecto: el endpoint genérico contestaba «Missing required
    placeholders: score.score, run.fecha_emision» y dejaba al operador sin saber
    de dónde sale eso. Ahora el 422 dice qué documento es y por dónde se lanza.

    (De paso: el diagnóstico que circulaba —«engancharlos al auditor interno»—
    era incorrecto. El auditor interno emite E-701; estos son de M08,
    verificación técnica, con CVE, CVSS, objetivos y alcance de escaneo.)
"""
from __future__ import annotations

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]


def test_e001_tiene_productor_de_contexto():
    productor = (RAIZ / "backend" / "app" / "motors" / "m06_document_factory"
                 / "ficha_seguimiento_context.py")
    assert productor.exists(), "E-001 vuelve a quedarse sin quien construya `ficha`"
    fuente = productor.read_text(encoding="utf-8")
    # Las 21 variables del cuerpo de la plantilla, comprobadas contra el .docx.
    import re
    import zipfile

    with zipfile.ZipFile(RAIZ / "var" / "templates_docx" / "E-001.docx") as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    texto = re.sub(r"<[^>]+>", "", xml)
    pedidas = {
        m.split(".", 1)[1]
        for m in re.findall(r"\{\{\s*(ficha\.[a-z_]+)", texto)
    }
    assert len(pedidas) >= 15, (
        f"sólo {len(pedidas)} variables `ficha.*` leídas de la plantilla: el "
        "barrido está mal y este test no comprueba nada"
    )
    faltan = sorted(v for v in pedidas if f'"{v}"' not in fuente)
    assert not faltan, (
        f"el productor de E-001 no construye estas variables: {faltan}"
    )


def test_e001_no_inventa_lo_que_no_sabe():
    fuente = (RAIZ / "backend" / "app" / "motors" / "m06_document_factory"
              / "ficha_seguimiento_context.py").read_text(encoding="utf-8")
    assert 'NO_CONSTA = "no consta"' in fuente, (
        "el productor de E-001 vuelve a rellenar huecos en vez de decirlos"
    )
    # La inversión en la auditoría externa la contrata y paga el cliente: si
    # apareciera una cifra ahí, sería inventada.
    assert 'proyecto["inversion_auditoria_externa"] = NO_CONSTA' in fuente


def test_e001_esta_cableado_a_la_fabrica():
    fuente = (RAIZ / "backend" / "app" / "motors" / "m06_document_factory"
              / "service.py").read_text(encoding="utf-8")
    assert "build_ficha_seguimiento_context" in fuente


def test_los_informes_de_verificacion_dicen_por_donde_se_lanzan():
    servicio = (RAIZ / "backend" / "app" / "motors" / "m06_document_factory"
                / "service.py").read_text(encoding="utf-8")
    for codigo in ("E-702", "E-703", "E-704"):
        assert f'"{codigo}"' in servicio, (
            f"{codigo} deja de explicar que necesita una ejecución previa"
        )
    api = (RAIZ / "backend" / "app" / "motors" / "m06_document_factory"
           / "api.py").read_text(encoding="utf-8")
    assert "_ENTREGABLES_CON_EJECUCION_PREVIA" in api
