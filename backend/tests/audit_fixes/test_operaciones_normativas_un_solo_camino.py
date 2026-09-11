"""Las operaciones normativas tienen UN camino, y el build falla si aparece otro.

EL PATRON, CON TRES INSTANCIAS YA VISTAS
    Una regla del ENS implementada N veces. Se arregla una copia; las otras se
    quedan atras y el sistema se contradice segun por donde se le pregunte.

      1. CATEGORIZACION · la regla del maximo del Anexo I estaba en tres
         sitios. `service.py` arrancaba en NO_AFECTADA y `api.py` conservaba su
         propia tabla arrancando en BAJO: un sistema sin valorar salia BASICA
         por una puerta y sin categoria por la otra.
         Guard: m01_categorization/test_sin_logica_duplicada.py

      2. APLICABILIDAD · `medidas_aplicables()` se escribio y se probo, y no
         tenia NI UN llamante en produccion: la pantalla usaba la funcion buena
         y la GENERACION de la DdA usaba `_measure_applies`, que solo miraba el
         eje de categoria e ignoraba el eje de dimension del Anexo II punto 5.

      3. EMISION DE DOCUMENTO · el acta E-012 se renderizaba a mano en el
         endpoint, fuera de la fabrica documental. No quedaba fila en
         `documents`, y el expediente del auditor se arma leyendo esa tabla.

    Los tres guards viven aqui juntos porque el patron es uno.

LA CUARTA Y LA QUINTA INSTANCIA, QUE SALIERON DE ESCRIBIR ESTE FICHERO
    El barrido de `render_docx` encontro dos caminos mas que no habiamos visto:

      4. m14_contracts/adenda_generator · renderiza la E-604 (adenda contractual
         de proveedor, FIRMABLE, y con plantilla EN el catalogo) fuera de la
         fabrica. Graba en `provider_addendums` y sube a MinIO, pero no deja
         fila en `documents`.
      5. m18_communication/minutes_service · el acta de reunion E-005, tambien
         firmable (`POST /api/v1/minutes-signing/approve`), se construye con
         python-docx y se registra en `meetings`, no en `documents`.

    Las dos quedan ABIERTAS con su medicion, congeladas en la linea base de
    abajo: E-604 es enchufable a la fabrica porque su plantilla esta en el
    catalogo; E-005 no tiene plantilla ("E-005 sin plantilla" consta en tres
    sitios de m09), asi que enchufarla exige crearla primero.

    Congelada la linea base, un SEXTO camino rompe el build.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
APP = RAIZ / "backend" / "app"


def _ficheros() -> list[Path]:
    ficheros = list(APP.rglob("*.py"))
    assert len(ficheros) > 500, (
        f"solo {len(ficheros)} ficheros barridos: la ruta esta mal y este "
        "fichero no estaria comprobando nada"
    )
    return ficheros


def _llamantes(nombre: str) -> dict[str, list[int]]:
    """Ficheros que LLAMAN a ``nombre``, por linea. No cuenta la definicion."""
    fuera: dict[str, list[int]] = {}
    for py in _ficheros():
        try:
            arbol = ast.parse(py.read_text("utf-8", errors="ignore"))
        except SyntaxError:  # pragma: no cover
            continue
        for n in ast.walk(arbol):
            if (
                isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name)
                and n.func.id == nombre
            ):
                fuera.setdefault(str(py.relative_to(RAIZ)), []).append(n.lineno)
    return fuera


# ================================================================
# 2 · APLICABILIDAD · un solo llamante canonico
# ================================================================

# El unico sitio que decide que medidas aplican a un proyecto. Si aparece otro,
# o es la misma decision tomada dos veces (y divergira), o es un consumidor que
# deberia leer la DdA ya calculada en vez de recalcularla.
LLAMANTE_CANONICO_APLICABILIDAD = "backend/app/motors/m03_dda/service.py"
# El propio modulo se llama a si mismo desde `diferencia_explicada()`; eso es la
# definicion, no un segundo camino.
_MODULO_DE_LA_FUNCION = "backend/app/motors/m01_categorization/aplicabilidad.py"


def test_la_aplicabilidad_la_decide_un_solo_llamante():
    llamantes = _llamantes("medidas_aplicables")
    assert llamantes, (
        "nadie llama a medidas_aplicables(): es exactamente el defecto que se "
        "arreglo en N1 -- la funcion escrita y probada, y la generacion de la "
        "DdA usando otra cosa"
    )
    intrusos = sorted(
        set(llamantes) - {LLAMANTE_CANONICO_APLICABILIDAD, _MODULO_DE_LA_FUNCION}
    )
    assert not intrusos, (
        "segundo camino para decidir la aplicabilidad del Anexo II:\n  "
        + "\n  ".join(f"{f}:{llamantes[f]}" for f in intrusos)
    )


def test_la_generacion_de_la_dda_no_usa_el_atajo_por_categoria():
    """``_measure_applies`` solo mira el eje de categoria.

    El Anexo II punto 5 exige los DOS ejes: una medida aplica por la categoria
    del sistema O por el nivel de una dimension. La funcion se conserva -- esta
    documentada como solo-categoria -- pero no puede volver a alimentar la
    generacion de la DdA.
    """
    servicio = (RAIZ / LLAMANTE_CANONICO_APLICABILIDAD).read_text("utf-8")
    generacion = servicio[servicio.index("async def generate_dda"):]
    corte = generacion.find("\n    async def ", 10)
    if corte > 0:
        generacion = generacion[:corte]
    assert "medidas_aplicables(" in generacion
    assert "_measure_applies(" not in generacion, (
        "generate_dda vuelve a decidir la aplicabilidad por el eje de categoria "
        "solo, ignorando el eje de dimension (Anexo II punto 5)"
    )


# ================================================================
# 3 · EMISION DE DOCUMENTO · nadie renderiza un entregable fuera de la fabrica
# ================================================================

# La fabrica documental (m06) renderiza, calcula la huella, firma con Ed25519,
# convierte a PDF, graba la fila en `documents` y sube copia durable a MinIO.
# Quien renderiza por su cuenta se salta las cinco cosas -- y `documents` es
# exactamente lo que lee el generador del expediente del auditor.
FABRICA = "backend/app/motors/m06_document_factory/service.py"

# Linea base CONGELADA de caminos alternativos conocidos. Cada uno esta ABIERTO
# con su motivo, no justificado. Un camino nuevo rompe el build.
CAMINOS_ALTERNATIVOS_CONOCIDOS = {
    # ABIERTO · E-604 adenda de proveedor, firmable, plantilla EN el catalogo.
    # Graba en provider_addendums + MinIO, pero no en `documents`: no llega al
    # inventario documental ni al expediente. Enchufable a la fabrica.
    "backend/app/motors/m14_contracts/adenda_generator.py",
    # ABIERTO · E-005 acta de reunion, firmable via /minutes-signing/approve.
    # Se construye con python-docx y solo convierte a PDF por aqui; se registra
    # en `meetings`. No tiene plantilla en el catalogo ("E-005 sin plantilla"
    # consta en m09 checklist_service, internal_auditor y el registro), asi que
    # enchufarla exige crear la plantilla primero.
    "backend/app/motors/m18_communication/minutes_service.py",
}


def test_solo_la_fabrica_renderiza_entregables():
    llamantes = set(_llamantes("render_docx")) | set(
        _llamantes("convert_docx_to_pdf")
    )
    assert FABRICA in llamantes, (
        "la fabrica documental ya no renderiza: el barrido esta mal apuntado"
    )
    nuevos = sorted(
        llamantes
        - {FABRICA}
        - CAMINOS_ALTERNATIVOS_CONOCIDOS
        - {"backend/app/motors/m06_document_factory/rendering.py"}
    )
    assert not nuevos, (
        "camino nuevo para emitir un documento fuera de la fabrica: no dejara "
        "fila en `documents`, asi que no llegara al expediente del auditor:\n  "
        + "\n  ".join(nuevos)
    )


def test_el_acta_e012_no_vuelve_a_renderizarse_a_mano():
    """La instancia 3, cerrada por nombre y no solo por barrido."""
    api = (RAIZ / "backend/app/motors/m01_categorization/api.py").read_text("utf-8")
    assert "generar_o_recuperar_acta_e012" in api
    assert not re.search(r"render_docx\s*\(", api), (
        "el endpoint del acta volvio a renderizar por su cuenta"
    )


def test_la_linea_base_de_caminos_alternativos_sigue_siendo_cierta():
    """Que los dos ABIERTOS existan de verdad.

    Sin esto, el dia que alguien los arregle la linea base se queda tapando
    ficheros que ya no hacen nada, y el guard afloja sin que nadie lo note.
    """
    llamantes = set(_llamantes("render_docx")) | set(
        _llamantes("convert_docx_to_pdf")
    )
    desaparecidos = sorted(CAMINOS_ALTERNATIVOS_CONOCIDOS - llamantes)
    assert not desaparecidos, (
        "estos ya no renderizan por su cuenta: quitalos de la linea base "
        "en vez de dejarla aflojada:\n  " + "\n  ".join(desaparecidos)
    )


# ================================================================
# 1 · CATEGORIZACION · el guard vive en su motor; aqui se comprueba que sigue
# ================================================================


def test_el_guard_de_la_categorizacion_sigue_en_pie():
    """No se copia aqui: se comprueba que existe donde esta.

    Duplicar el guard de la duplicacion seria una broma con mala suerte.
    """
    guard = RAIZ / (
        "backend/tests/motors/m01_categorization/test_sin_logica_duplicada.py"
    )
    assert guard.exists(), "desaparecio el guard de la regla del maximo"
    texto = guard.read_text("utf-8")
    assert "test_no_reaparece_una_segunda_implementacion_de_la_regla_del_maximo" in texto
