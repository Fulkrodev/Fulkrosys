"""Guardia: los comentarios y la documentación no citan rutas que no existen.

El repositorio llevaba 200 citas a 103 rutas que ya no estaban: informes de
auditoría borrados en la limpieza de junio, un ``progress/`` que nunca se
versionó, modelos que se movieron de ``backend/app/models/`` a su motor,
scripts que pasaron de ``scripts/`` a ``backend/scripts/``. Quien seguía una
de esas citas no encontraba nada.

Qué cuenta como cita. Una ruta que empieza por un directorio de primer nivel
del repositorio (``backend/``, ``frontend/``, ``docs/``...) y acaba en una
extensión de fichero, escrita:

- en un comentario o un docstring de Python;
- en un comentario ``//`` o ``/* */`` de TypeScript o JavaScript;
- en un comentario ``#`` de shell, YAML, TOML o del Makefile;
- en cualquier parte de un Markdown, que es documentación de principio a fin.

Las cadenas del código no cuentan: una ruta que el programa lee o escribe es
comportamiento, no una cita.

Qué cuenta como que existe:

- está versionada (fichero o directorio);
- existe relativa al directorio de primer nivel del fichero que la cita
  (``scripts/axe-dump.mjs`` dentro de ``frontend/`` es
  ``frontend/scripts/axe-dump.mjs``);
- en ``frontend/app``, existe sin contar los grupos de ruta ``(x)`` de Next,
  que no forman parte de la URL y a menudo se omiten al citar;
- es una salida que se genera al ejecutar: todo ``out/`` y ``var/``
  (ignorados por git) y los ficheros de ``_GENERADOS``.

Una ruta que ya no existe se arregla apuntando a la vigente o quitándola; la
convención para las retiradas es dejar solo el nombre del fichero seguido de
«(retirado del repositorio)».
"""
from __future__ import annotations

import ast
import io
import re
import subprocess
import tokenize
from functools import lru_cache
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

_RAICES = "backend|frontend|docs|scripts|infra|landing|progress|out|var|agent"
_EXTENSIONES = "md|py|yml|yaml|sh|json|tsx|ts|txt|sql|html|mjs|cjs|csv|toml"
_RUTA = re.compile(
    rf"(?<![\w/.-])((?:{_RAICES})/[\w./()\[\]-]+\.(?:{_EXTENSIONES}))(?![\w-])"
)

# Salidas que el código genera al ejecutarse; no se versionan a propósito.
_GENERADOS = {
    # gunzip del fixture versionado corpus_seed.sql.gz (scripts/build_test_db.sh)
    "backend/tests/fixtures/corpus_seed.sql",
    # informes de `npm audit` que escribe .github/workflows/security-scan.yml
    "frontend/npm-audit-report.json",
    "frontend/npm-audit-report-dev.json",
    # backend/scripts/legal_audit_77_templates.py
    "progress/legal_audit_autocheck.json",
}
_SALIDAS = ("out/", "var/")


@lru_cache(maxsize=1)
def _versionado() -> tuple[frozenset[str], frozenset[str]]:
    salida = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO, capture_output=True, check=True,
    ).stdout.decode()
    ficheros = frozenset(f for f in salida.split("\0") if f)
    dirs = frozenset(
        "/".join(f.split("/")[:i]) for f in ficheros for i in range(1, f.count("/") + 1)
    )
    return ficheros, dirs


def _sin_grupos(ruta: str) -> str:
    return re.sub(r"\([^/]+\)/", "", ruta)


@lru_cache(maxsize=1)
def _app_sin_grupos() -> frozenset[str]:
    ficheros, _ = _versionado()
    return frozenset(_sin_grupos(f) for f in ficheros if f.startswith("frontend/app/"))


def existe(ruta: str, citada_desde: str) -> bool:
    ficheros, dirs = _versionado()
    if ruta in ficheros or ruta in dirs or ruta in _GENERADOS or ruta.startswith(_SALIDAS):
        return True
    raiz = citada_desde.split("/")[0]
    relativa = f"{raiz}/{ruta}"
    if "/" in citada_desde and (relativa in ficheros or relativa in dirs):
        return True
    return ruta.startswith("frontend/app/") and _sin_grupos(ruta) in _app_sin_grupos()


def _comentarios_python(texto: str) -> list[tuple[int, str]]:
    trozos: list[tuple[int, str]] = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(texto).readline):
            if tok.type == tokenize.COMMENT:
                trozos.append((tok.start[0], tok.string))
        arbol = ast.parse(texto)
    except (tokenize.TokenError, SyntaxError, IndentationError):
        return trozos
    for nodo in ast.walk(arbol):
        if (
            isinstance(nodo, ast.Expr)
            and isinstance(nodo.value, ast.Constant)
            and isinstance(nodo.value.value, str)
        ):
            for i, linea in enumerate(nodo.value.value.splitlines()):
                trozos.append((nodo.lineno + i, linea))
    return trozos


_COMENTARIO_JS = re.compile(r"/\*.*?\*/|(?<![:\"'`\\])//[^\n]*", re.S)
_COMENTARIO_ALMOHADILLA = re.compile(r"(?:^|\s)#[^\n]*")


def _comentarios_por_regex(texto: str, patron: re.Pattern[str]) -> list[tuple[int, str]]:
    trozos = []
    for m in patron.finditer(texto):
        inicio = texto.count("\n", 0, m.start()) + 1
        for i, linea in enumerate(m.group(0).splitlines()):
            trozos.append((inicio + i, linea))
    return trozos


def trozos_citables(ruta: str, texto: str) -> list[tuple[int, str]]:
    """(línea, texto) de las partes del fichero donde una ruta es una cita."""
    if ruta.endswith(".md"):
        return list(enumerate(texto.splitlines(), 1))
    if ruta.endswith(".py"):
        return _comentarios_python(texto)
    if ruta.endswith((".ts", ".tsx", ".js", ".mjs", ".cjs")):
        return _comentarios_por_regex(texto, _COMENTARIO_JS)
    if ruta.endswith((".sh", ".yml", ".yaml", ".toml")) or ruta.endswith("Makefile"):
        return _comentarios_por_regex(texto, _COMENTARIO_ALMOHADILLA)
    return []


def citas_rotas(ruta: str, texto: str) -> list[tuple[int, str]]:
    rotas = []
    for n, trozo in sorted(trozos_citables(ruta, texto)):
        for cita in _RUTA.findall(trozo):
            cita = cita.split("](")[0].rstrip(".")
            if "..." in cita or "*" in cita:
                continue
            if not existe(cita, ruta):
                rotas.append((n, cita))
    return rotas


def test_el_extractor_distingue_comentarios_de_codigo():
    py = '"""Ver docs/no_existe.md."""\nx = "docs/tampoco.md"  # y backend/fantasma.py\n'
    assert [c for _, c in citas_rotas("backend/m.py", py)] == ["docs/no_existe.md", "backend/fantasma.py"]
    ts = 'const a = "docs/no.md"; // ver docs/nada.md\n/* y backend/x.py */\n'
    assert [c for _, c in citas_rotas("frontend/m.ts", ts)] == ["docs/nada.md", "backend/x.py"]
    assert citas_rotas("docs/a.md", "Ver [docs/CI.md](CI.md) y out/x.json") == []


def test_ningun_comentario_ni_documento_cita_una_ruta_que_no_existe():
    if not (REPO / ".git").exists():
        pytest.skip("sin checkout de git no hay árbol versionado")
    ficheros, _ = _versionado()
    hallazgos = []
    for ruta in sorted(ficheros):
        if not ruta.endswith((".md", ".py", ".ts", ".tsx", ".js", ".mjs", ".cjs",
                              ".sh", ".yml", ".yaml", ".toml", "Makefile")):
            continue
        try:
            texto = (REPO / ruta).read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        hallazgos += [f"{ruta}:{n} -> {cita}" for n, cita in citas_rotas(ruta, texto)]
    assert not hallazgos, (
        f"{len(hallazgos)} cita(s) a rutas que no existen. Apunta a la vigente o deja "
        "el nombre con «(retirado del repositorio)»:\n" + "\n".join(hallazgos)
    )
