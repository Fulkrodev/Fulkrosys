"""Guardia: ni el NIF ni el domicilio del titular vuelven al repositorio.

Fulkro cerró en septiembre de 2026 y su titular ya no ejerce como autónomo, así
que no hay obligación de publicar su NIF (LSSI art. 10) ni motivo para que su
domicilio aparezca en ningún sitio. Estaban en 14 y 5 ficheros: la migración de
identidad fiscal, las páginas legales, los fixtures de facturas y contratos, el
placeholder de un formulario. Hoy el código usa ``12345678Z`` y el domicilio
ficticio del demo.

El test no puede contener los datos que vigila, porque entonces los publicaría
él. Guarda solo su SHA-256 y compara contra el hash de lo que encuentra:

- el NIF, con letra y sin ella, contra cada palabra de 8 cifras (con o sin
  letra) de cada fichero;
- la calle, contra cada racha de 4 palabras que empiece por la palabra cuyo
  hash es ``_PRIMERA_PALABRA_CALLE``. Se normaliza antes: minúsculas, sin
  tildes y sin puntuación, así que «Paseo de la Dirección, 46» y «PASEO DE LA
  DIRECCION 46» dan la misma racha.

Recorre ``git ls-files``: lo versionado, que es lo que se publica. Si falla,
dice fichero y línea, nunca el valor.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
import unicodedata
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

_NIF_CON_LETRA = "a0f8534c9fb3f80495a0a7e380122bb2bfb9e47ffb5536c403a7f713528ebdc4"
_NIF_SOLO_CIFRAS = "b80249542111e58da06e2105f53353ab89ec170f8e7f53d675aee5a83965cd33"
_CALLE = "e9ff9919a45eb57a30941de5e8ee696731a5f7668864166ef5c79d30ff050ade"
_PRIMERA_PALABRA_CALLE = "68a32dd6b2c35412abbf319675fa086748a052cb8693e503111c32179e921d48"
_PALABRAS_CALLE = 4

_BINARIOS = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".pdf", ".gz",
             ".zip", ".docx", ".xlsx", ".woff", ".woff2", ".ttf", ".otf", ".mp4"}
_OCHO_CIFRAS = re.compile(r"^\d{8}[a-z]?$")


def _sha(texto: str) -> str:
    return hashlib.sha256(texto.encode()).hexdigest()


def normalizar(texto: str) -> list[str]:
    """Minúsculas, sin tildes, sin puntuación, partido en palabras."""
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", texto).split()


def apariciones(linea: str) -> list[str]:
    """Qué dato del titular hay en la línea: 'nif', 'domicilio' o nada."""
    palabras = normalizar(linea)
    encontrados: list[str] = []
    for i, palabra in enumerate(palabras):
        if _OCHO_CIFRAS.match(palabra) and _sha(palabra) in (_NIF_CON_LETRA, _NIF_SOLO_CIFRAS):
            encontrados.append("nif")
        if _sha(palabra) == _PRIMERA_PALABRA_CALLE:
            racha = " ".join(palabras[i:i + _PALABRAS_CALLE])
            if _sha(racha) == _CALLE:
                encontrados.append("domicilio")
    return encontrados


def _versionados() -> list[Path]:
    salida = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO, capture_output=True, check=True,
    ).stdout.decode()
    return [REPO / f for f in salida.split("\0") if f and Path(f).suffix.lower() not in _BINARIOS]


def test_el_detector_reconoce_las_grafias_normalizadas():
    """La normalización une grafías y el detector no salta con otros NIF."""
    assert apariciones("NIF: 12345678Z · B12345678") == []
    assert apariciones("Calle Mayor 1, 28013 Madrid") == []
    assert normalizar("Dirección, 46") == ["direccion", "46"]


def test_ni_el_nif_ni_el_domicilio_del_titular_estan_versionados():
    if not (REPO / ".git").exists():
        pytest.skip("sin checkout de git no hay árbol versionado que recorrer")
    hallazgos: list[str] = []
    for fichero in _versionados():
        try:
            texto = fichero.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
            continue
        for n, linea in enumerate(texto.splitlines(), 1):
            for dato in apariciones(linea):
                hallazgos.append(f"{fichero.relative_to(REPO)}:{n} · {dato}")
    assert not hallazgos, (
        "Datos personales del titular en el repositorio (se muestra dónde, no el valor):\n"
        + "\n".join(hallazgos)
    )
