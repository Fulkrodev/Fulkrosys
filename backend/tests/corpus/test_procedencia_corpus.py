"""El corpus no puede atribuir a un tercero un texto escrito aquí.

Qué vigila y por qué
--------------------
El 2026-09-10 se encontró esto: `backend/app/corpus/data/CCN_STIC_809.md` eran
103 líneas y 14,7 KB escritas en este repositorio, tituladas como la guía
CCN-STIC-809 y subtituladas «Guía de Seguridad de las TIC · Centro Criptológico
Nacional · Abril 2026». El módulo que lo ingiere las declaraba con
``publisher="Centro Criptológico Nacional (CCN)"`` y con la URL oficial del CCN
como ``source_url``. La guía real son decenas de páginas.

**No era una copia: era un resumen que se presentaba como el original.** Y el
problema no es de derechos de copia sino de PROCEDENCIA: el buscador del
copiloto podía devolver un fragmento de ese resumen citando al CCN, con un texto
que puede no estar en su guía. Un usuario leería una cita normativa donde hay
una redacción nuestra.

Es el mismo defecto que cerró D1 —fabricar algo y sellarlo como auténtico— una
capa más abajo: allí era una respuesta del modelo grabada como `success`, aquí
es la procedencia de una fuente del corpus.

La regla
--------
**Un texto versionado bajo `backend/app/corpus/data/` es texto nuestro.** Si una
declaración de fuente lo referencia, no puede declarar como editor a un tercero
ni poner una URL de un tercero como origen del texto.

Lo que NO prohíbe: que `ccn_pdf_ingest` declare al CCN como editor de las guías
que ingiere. Ese texto SÍ es del CCN: sale de PDFs que el operador descarga a
`var/corpus/`, que no está versionado (`git ls-files | grep stic_serie_800` → 0).
La frontera es exactamente ésa: lo que viaja en el repositorio es nuestro.

Este test NO necesita base de datos: lee el código. Corre en el job `test` de CI.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

_RAIZ = Path(__file__).resolve().parents[3]
_CORPUS = _RAIZ / "backend" / "app" / "corpus"
_DATOS = _CORPUS / "data"

#: Editores que somos nosotros. Cualquier variante nueva se añade aquí.
_EDITORES_PROPIOS = ("fulkro", "marcos mata")

#: Dominios de terceros que no pueden figurar como ORIGEN de un texto nuestro.
#: Como referencia para consultar el original sí, pero eso va en `metadata`.
_DOMINIOS_AJENOS = (
    "ccn-cert.cni.es", "ccn.cni.es", "boe.es", "europa.eu",
    "iso.org", "une.org", "nist.gov", "enac.es",
)

# ── Lista blanca ────────────────────────────────────────────────────────────
# Vacía a propósito, y conviene que siga así.
#
# Qué entraría aquí legítimamente: un texto que se versione bajo `data/` cuyo
# editor de terceros sea CIERTO **y** cuya redistribución esté permitida. El
# caso real sería el RD 311/2022: es norma oficial, libremente reproducible, y
# `publisher="BOE - Ministerio de Asuntos Económicos..."` sería exacto. Hoy no
# hace falta la excepción porque ese HTML NO está versionado: se descarga a
# `var/corpus/` (ver `rd311_ingest.CORPUS_DIR`).
#
# Qué NO entra: un resumen, una traducción, una refundición o cualquier texto
# redactado aquí. Por muy fiel que sea al original, el editor somos nosotros.
#
# Formato: {"nombre_del_fichero.md": "por qué, con fecha y quién lo decidió"}
_EXCEPCIONES_EDITOR_AJENO: dict[str, str] = {}


def _ficheros_de_datos() -> set[str]:
    """Nombres de los ficheros versionados bajo backend/app/corpus/data/."""
    if not _DATOS.is_dir():
        return set()
    return {p.name for p in _DATOS.iterdir() if p.is_file()}


def _constantes_de_modulo(arbol: ast.Module) -> dict[str, str]:
    """`NOMBRE = "literal"` a nivel de módulo, para resolver referencias."""
    fuera: dict[str, str] = {}
    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign) and isinstance(nodo.value, ast.Constant):
            if isinstance(nodo.value.value, str):
                for destino in nodo.targets:
                    if isinstance(destino, ast.Name):
                        fuera[destino.id] = nodo.value.value
    return fuera


def _cadenas(nodo: ast.AST, constantes: dict[str, str]) -> list[str]:
    """Todas las cadenas del subárbol, resolviendo nombres de módulo."""
    fuera: list[str] = []
    for hijo in ast.walk(nodo):
        if isinstance(hijo, ast.Constant) and isinstance(hijo.value, str):
            fuera.append(hijo.value)
        elif isinstance(hijo, ast.Name) and hijo.id in constantes:
            fuera.append(constantes[hijo.id])
    return fuera


def _valor_de(nodo: ast.AST, clave: str, constantes: dict[str, str]) -> str | None:
    """Valor de `clave` como entrada de diccionario o como argumento con nombre."""
    if isinstance(nodo, ast.Dict):
        for k, v in zip(nodo.keys, nodo.values):
            if isinstance(k, ast.Constant) and k.value == clave:
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    return v.value
                if isinstance(v, ast.Name):
                    return constantes.get(v.id)
    if isinstance(nodo, ast.Call):
        for kw in nodo.keywords:
            if kw.arg == clave:
                if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                    return kw.value.value
                if isinstance(kw.value, ast.Name):
                    return constantes.get(kw.value.id)
    return None


def _declaraciones_que_usan_datos_del_repo() -> list[dict]:
    """Declaraciones (dict o llamada) que referencian un fichero de `data/`."""
    datos = _ficheros_de_datos()
    encontradas: list[dict] = []
    for modulo in sorted(_CORPUS.rglob("*.py")):
        arbol = ast.parse(modulo.read_text(encoding="utf-8"), filename=str(modulo))
        constantes = _constantes_de_modulo(arbol)
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, (ast.Dict, ast.Call)):
                continue
            cadenas = _cadenas(nodo, constantes)
            ficheros = [c for c in cadenas if c in datos]
            if not ficheros:
                continue
            encontradas.append({
                "modulo": str(modulo.relative_to(_RAIZ)),
                "linea": getattr(nodo, "lineno", 0),
                "ficheros": sorted(set(ficheros)),
                "publisher": _valor_de(nodo, "publisher", constantes),
                "source_url": _valor_de(nodo, "source_url", constantes),
            })
    return encontradas


def _es_propio(publisher: str) -> bool:
    bajo = publisher.lower()
    return any(marca in bajo for marca in _EDITORES_PROPIOS)


# ════════════════════════════════════════════════════════════════════════════
# 1 · el editor
# ════════════════════════════════════════════════════════════════════════════

def test_ningun_texto_del_repo_declara_editor_ajeno():
    """La regla, en una línea: lo que viaja en el repositorio es nuestro."""
    culpables = []
    for d in _declaraciones_que_usan_datos_del_repo():
        publisher = d["publisher"]
        if publisher is None:
            continue  # una función auxiliar, no una declaración de fuente
        exentos = [f for f in d["ficheros"] if f in _EXCEPCIONES_EDITOR_AJENO]
        if exentos:
            continue
        if not _es_propio(publisher):
            culpables.append(
                f"{d['modulo']}:{d['linea']} declara publisher={publisher!r} "
                f"para {d['ficheros']}, que está versionado en el repositorio"
            )
    assert not culpables, (
        "Hay texto escrito en este repositorio atribuido a un tercero:\n  "
        + "\n  ".join(culpables)
        + "\n\nUn fichero bajo backend/app/corpus/data/ lo hemos escrito nosotros."
        " Si además se le declara un editor ajeno, el copiloto puede citar a ese"
        " tercero con un texto que ese tercero no ha escrito.\n"
        "Arreglo: publisher propio (ver PUBLISHER_PROPIO en ccn_stic_ingest) y la"
        " referencia al original en `metadata`. Si de verdad es una excepción"
        " legítima, va a _EXCEPCIONES_EDITOR_AJENO con su porqué escrito."
    )


# ════════════════════════════════════════════════════════════════════════════
# 1.bis · el editor, aunque esté enterrado lejos de la ruta
# ════════════════════════════════════════════════════════════════════════════
#
# Por qué hace falta esta segunda comprobación, más basta que la anterior:
# medido contra el estado anterior a la corrección, la de arriba NO cazaba el
# fallo real. El `publisher="Centro Criptológico Nacional (CCN)"` estaba dentro
# del cuerpo de `ingest_ccn_stic_guide`, a ochenta líneas del diccionario que
# nombraba el fichero, así que ninguna declaración tenía las dos cosas juntas.
#
# Ésta mira el MÓDULO entero: si un módulo del corpus toca un fichero
# versionado bajo `data/` y en alguna parte declara un editor ajeno, salta.
# Es deliberadamente burda. Hoy no da falsos positivos porque `ccn_pdf_ingest`
# —el que sí declara al CCN con razón— no toca ningún fichero de `data/`. Si
# algún día un módulo necesita legítimamente las dos cosas, hay que partirlo en
# dos módulos o razonar la excepción por escrito. Que cueste es la intención.

def _publishers_del_modulo(arbol: ast.Module, constantes: dict[str, str]) -> list[tuple[int, str]]:
    """Todo valor asignado a `publisher` en el módulo, esté donde esté."""
    fuera: list[tuple[int, str]] = []
    for nodo in ast.walk(arbol):
        valor = None
        if isinstance(nodo, ast.keyword) and nodo.arg == "publisher":
            valor = nodo.value
        elif (isinstance(nodo, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == "publisher"
                      for t in nodo.targets)):
            valor = nodo.value
        if valor is None:
            continue
        if isinstance(valor, ast.Constant) and isinstance(valor.value, str):
            fuera.append((getattr(nodo, "lineno", 0), valor.value))
        elif isinstance(valor, ast.Name) and valor.id in constantes:
            fuera.append((getattr(nodo, "lineno", 0), constantes[valor.id]))
    # También las entradas de diccionario `"publisher": "..."`.
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Dict):
            continue
        for k, v in zip(nodo.keys, nodo.values):
            if isinstance(k, ast.Constant) and k.value == "publisher":
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    fuera.append((getattr(v, "lineno", 0), v.value))
                elif isinstance(v, ast.Name) and v.id in constantes:
                    fuera.append((getattr(v, "lineno", 0), constantes[v.id]))
    return fuera


def test_un_modulo_que_toca_datos_del_repo_no_declara_editores_ajenos():
    datos = _ficheros_de_datos()
    culpables = []
    for modulo in sorted(_CORPUS.rglob("*.py")):
        texto = modulo.read_text(encoding="utf-8")
        arbol = ast.parse(texto, filename=str(modulo))
        constantes = _constantes_de_modulo(arbol)
        tocados = sorted({c for c in _cadenas(arbol, constantes) if c in datos})
        if not tocados:
            continue
        if all(f in _EXCEPCIONES_EDITOR_AJENO for f in tocados):
            continue
        for linea, publisher in _publishers_del_modulo(arbol, constantes):
            if not _es_propio(publisher):
                culpables.append(
                    f"{modulo.relative_to(_RAIZ)}:{linea} declara "
                    f"publisher={publisher!r} y el módulo ingiere {tocados}"
                )
    assert not culpables, (
        "Un módulo que ingiere texto versionado en el repositorio declara como "
        "editor a un tercero:\n  " + "\n  ".join(culpables)
        + "\n\nDa igual a qué distancia esté del `md_path`: si el módulo sólo "
        "ingiere texto nuestro, el editor tiene que ser nuestro. Si de verdad "
        "hace las dos cosas, pártelo en dos módulos."
    )


# ════════════════════════════════════════════════════════════════════════════
# 2 · la URL de origen
# ════════════════════════════════════════════════════════════════════════════

def test_ningun_texto_del_repo_declara_una_url_ajena_como_origen():
    """`source_url` dice de dónde SALE el texto. La referencia va en metadata."""
    culpables = []
    for d in _declaraciones_que_usan_datos_del_repo():
        url = d["source_url"]
        if not url:
            continue
        if any(dom in url for dom in _DOMINIOS_AJENOS):
            culpables.append(
                f"{d['modulo']}:{d['linea']} pone source_url={url!r} para "
                f"{d['ficheros']}, que está versionado en el repositorio"
            )
    assert not culpables, (
        "Hay texto del repositorio que declara como ORIGEN la web de un tercero:\n  "
        + "\n  ".join(culpables)
        + "\n\n`source_url` es de dónde sale el texto, no dónde consultar el"
        " original. Para lo segundo está `metadata`."
    )


# ════════════════════════════════════════════════════════════════════════════
# 3 · el propio fichero tampoco puede firmar como un tercero
# ════════════════════════════════════════════════════════════════════════════

_FIRMAS_AJENAS = re.compile(
    r"Gu[ií]a de Seguridad de las TIC"
    r"|^\s*Centro Criptol[óo]gico Nacional\b"
    r"|^#\s*CCN-STIC-\d+",
    re.IGNORECASE | re.MULTILINE,
)


@pytest.mark.parametrize(
    "nombre", sorted(_ficheros_de_datos()) or ["(no hay ficheros en data/)"],
)
def test_el_fichero_no_se_presenta_como_obra_de_un_tercero(nombre: str):
    """La cabecera del texto tiene que decir de quién es.

    El editor correcto en la base de datos no basta si el propio documento se
    titula como la guía ajena: el fragmento recuperado lleva ese título dentro.
    """
    if nombre.startswith("("):
        pytest.skip("no hay ficheros versionados en backend/app/corpus/data/")
    ruta = _DATOS / nombre
    # Se mira la VOZ PROPIA del documento: las líneas fuera de cita. Una cita
    # (`>`) es lo contrario de una reclamación de autoría, y este mismo fichero
    # cita entre `>` el subtítulo falso que tenía antes, para dejar constancia.
    # Sin esta distinción, el aviso que arregla el problema disparaba el aviso.
    voz_propia = "\n".join(
        linea for linea in ruta.read_text(encoding="utf-8").splitlines()
        if not linea.lstrip().startswith(">")
    )[:2000]
    encontradas = _FIRMAS_AJENAS.findall(voz_propia)
    assert not encontradas, (
        f"{ruta.relative_to(_RAIZ)} se presenta como obra de un tercero en su "
        f"cabecera: {encontradas}.\n"
        "Si es un resumen propio, tiene que decirlo en la primera pantalla, con "
        "la referencia al original claramente separada del texto."
    )


def test_la_lista_blanca_solo_contiene_ficheros_que_existen():
    """Una excepción a un fichero que ya no está es una excepción olvidada."""
    datos = _ficheros_de_datos()
    fantasmas = sorted(set(_EXCEPCIONES_EDITOR_AJENO) - datos)
    assert not fantasmas, (
        f"_EXCEPCIONES_EDITOR_AJENO menciona ficheros que no existen: {fantasmas}. "
        "Bórralos: una lista blanca con entradas muertas deja de proteger."
    )
