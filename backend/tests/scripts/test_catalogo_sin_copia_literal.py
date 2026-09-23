"""Guardia permanente: el catálogo ENS no vuelve a contener texto extraído de la guía.

Contexto. Hasta 2026-09-10 el campo ``descripcion`` de
``docs/catalogs/ens_measures_catalog_v1.yaml`` era un extracto literal de la
guía CCN-STIC 804 v2017, obtenido por extracción automática de PDF. Este
repositorio es público, así que las descripciones se reescribieron con
redacción propia. Este test impide que la copia vuelva a entrar.

Cómo lo comprueba. Busca los MARCADORES que dejaba aquella extracción y que un
texto redactado de cero no produce nunca:

  - encabezados de sección al principio de la descripción ("3.1 [ORG.1] ..."),
    que es como empezaban casi todas las copias;
  - el código de la medida en mayúsculas entre corchetes ("[OP.EXP.1]");
  - restos del pie de página del documento original ("SIN CLASIFICAR");
  - bloques de referencias arrastrados desde el final de cada sección
    ("ISO/IEC 27000", "NIST SP 800-53").

La comprobación fuerte, que ninguna descripción comparta 8 o más palabras
consecutivas con la original, también corre aquí: compara contra la huella
``docs/catalogs/ens_catalog_huella_ccn804.json`` (el SHA-256 de cada racha de 8
palabras del texto antiguo, sin el texto) con las funciones de
``scripts/verificar_catalogo_sin_copia_literal.py``. No necesita git ni base de
datos.

Lo que este test NO comprueba: que la descripción sea normativamente correcta.
Un texto redactado de cero pero equivocado pasa este test. Esa revisión es
humana.
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest
import yaml

CATALOGO = (
    Path(__file__).resolve().parents[3]
    / "docs" / "catalogs" / "ens_measures_catalog_v1.yaml"
)

# (nombre legible, patrón). Cada uno es un rastro de la extracción del PDF.
MARCADORES_DE_EXTRACCION: list[tuple[str, re.Pattern[str]]] = [
    (
        "encabezado de sección al inicio (ej. '3.1 [ORG.1] ...')",
        re.compile(r"^\s*\d+\.\d+(\.\d+)*\s*\[[A-Z]"),
    ),
    (
        "código de medida en mayúsculas entre corchetes (ej. '[OP.EXP.1]')",
        re.compile(r"\[[A-Z]{2,}(\.[A-Z]+)*(\.\d+)?\]"),
    ),
    (
        "pie de página del documento original ('SIN CLASIFICAR')",
        re.compile(r"\bCLASIFICAR\b"),
    ),
    (
        "bloque de referencias arrastrado ('ISO/IEC 27000' / 'NIST SP 800-53')",
        re.compile(r"ISO/IEC\s+27000|NIST\s+SP\s+800-53"),
    ),
]


@pytest.fixture(scope="module")
def catalogo() -> dict:
    assert CATALOGO.exists(), f"No se encuentra el catálogo en {CATALOGO}"
    return yaml.safe_load(CATALOGO.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def medidas(catalogo: dict) -> list[dict]:
    ms = catalogo.get("medidas") or []
    # Sin esta guarda el test sería vacuamente verdadero: sobre una lista vacía
    # el bucle no se ejecuta y no se comprueba ni una aserción.
    assert len(ms) > 0, "El catálogo no tiene medidas: este test no puede verificar nada."
    return ms


def test_el_catalogo_conserva_las_73_medidas(catalogo: dict, medidas: list[dict]) -> None:
    """La reescritura de descripciones no debía añadir ni quitar medidas.

    Eran 79 hasta el 2026-09-11. Bajaron a 73 en el bloque N2, y NO por esta
    reescritura: se eliminaron seis códigos (op.exp.11, mp.com.9, mp.if.9,
    mp.per.9, mp.s.8, mp.s.9) que venían de CCN-STIC 804 v2017 -- basada en el
    RD 3/2010, derogado -- y que NO EXISTEN en el Anexo II del RD 311/2022.
    Contrastado contra el PDF del BOE en N0.

    Que este test congelara el 79 es parte de lo que N2 vino a arreglar: el
    catálogo declaraba seis medidas inexistentes, el sembrador las filtraba con
    una lista negra, y un test fijaba ese 79 como si fuera lo correcto.
    """
    assert len(medidas) == 73, f"Se esperaban 73 medidas, hay {len(medidas)}"
    assert catalogo.get("medidas_count") == len(medidas), (
        f"medidas_count={catalogo.get('medidas_count')} no cuadra con "
        f"{len(medidas)} medidas reales"
    )


def test_ninguna_descripcion_esta_vacia(medidas: list[dict]) -> None:
    """Reescribir no puede haber dejado descripciones en blanco."""
    vacias = [m["codigo"] for m in medidas if not (m.get("descripcion") or "").strip()]
    assert not vacias, f"Medidas sin descripción: {vacias}"


@pytest.mark.parametrize("nombre,patron", MARCADORES_DE_EXTRACCION,
                         ids=[m[0].split(" (")[0] for m in MARCADORES_DE_EXTRACCION])
def test_sin_marcadores_de_extraccion(medidas: list[dict], nombre: str,
                                      patron: re.Pattern[str]) -> None:
    """Ninguna descripción contiene rastros de la extracción del PDF original."""
    culpables = []
    for m in medidas:
        desc = m.get("descripcion") or ""
        encontrado = patron.search(desc)
        if encontrado:
            culpables.append(f"{m['codigo']}: ...{encontrado.group(0)!r}...")
    assert not culpables, (
        f"{len(culpables)} descripción(es) con {nombre}. "
        f"Se reescriben con lenguaje propio:\n  " + "\n  ".join(culpables)
    )


def test_la_cabecera_declara_redaccion_propia(catalogo: dict) -> None:
    """`fuentes.descripciones` no puede volver a atribuir el texto a la guía."""
    declarado = str(catalogo.get("fuentes", {}).get("descripciones", ""))
    assert declarado.strip(), "fuentes.descripciones está vacío"
    assert "propia" in declarado.lower(), (
        "fuentes.descripciones debe declarar que las descripciones son redacción "
        f"propia de FULKRO. Dice: {declarado!r}"
    )
    # El fallo concreto que se corrigió: declarar la guía como ORIGEN del texto.
    assert not re.match(r"^\s*CCN-STIC", declarado), (
        "fuentes.descripciones vuelve a presentar la guía CCN-STIC como origen "
        f"de las descripciones: {declarado!r}"
    )


def test_la_guia_sigue_citada_como_fuente_de_consulta(medidas: list[dict]) -> None:
    """La trazabilidad no se pierde: `fuente_oficial` sigue apuntando a la guía.

    Quitar la copia literal no debe convertirse, por exceso, en borrar también
    la referencia que permite localizar cada medida en su guía.
    """
    con_fuente = [m for m in medidas if (m.get("fuente_oficial") or "").strip()]
    assert len(con_fuente) == len(medidas), (
        "Hay medidas sin fuente_oficial: "
        f"{[m['codigo'] for m in medidas if not (m.get('fuente_oficial') or '').strip()]}"
    )
    citan_guia = [m for m in medidas if "CCN-STIC" in (m.get("fuente_oficial") or "")]
    assert citan_guia, (
        "Ninguna medida cita ya la guía CCN-STIC en fuente_oficial: se ha perdido "
        "la trazabilidad a la sección de origen."
    )


# ── Comprobación fuerte: contra la huella del texto antiguo ────────────────

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "verificar_catalogo_sin_copia_literal.py"


@pytest.fixture(scope="module")
def verificador():
    spec = importlib.util.spec_from_file_location("verificar_catalogo", _SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_la_huella_solo_guarda_hashes(verificador) -> None:
    """La huella cubre las 79 medidas antiguas y no contiene texto."""
    palabras, huella, codigos = verificador.cargar_huella()
    assert palabras == 8
    assert len(codigos) == 79
    assert len(huella) > 6000
    assert all(re.fullmatch(r"[0-9a-f]{64}", h) for h in huella)


def test_el_detector_ve_la_copia_aunque_cambien_tildes_y_puntuacion(verificador) -> None:
    """Control positivo: sin él, un detector roto daría verde siempre."""
    original = "El responsable de la seguridad aprobará la política de uso aceptable del sistema."
    huella = set(verificador.hashes_de_rachas(original, 8))
    copia = "Nota: el RESPONSABLE de la seguridad aprobara, la politica de uso aceptable!"
    assert verificador.rachas_copiadas(copia, huella, 8)
    propia = "La dirección firma la política y la revisa cada año con el comité."
    assert verificador.rachas_copiadas(propia, huella, 8) == []


def test_ninguna_descripcion_repite_8_palabras_del_texto_antiguo(verificador, medidas) -> None:
    palabras, huella, _ = verificador.cargar_huella()
    copiadas = {
        m["codigo"]: r
        for m in medidas
        if (r := verificador.rachas_copiadas(m.get("descripcion") or "", huella, palabras))
    }
    assert not copiadas, (
        f"{len(copiadas)} descripción(es) repiten {palabras}+ palabras del texto de la "
        f"guía:\n" + "\n".join(f"  {c}: {r[0]!r}" for c, r in copiadas.items())
    )
