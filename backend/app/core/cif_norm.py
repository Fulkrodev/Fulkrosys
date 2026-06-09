"""Normalización de CIF/NIF/NIE para dedup robusto (#7).

El CIF del lead vive en dos sitios (``Lead.empresa_cif`` y la respuesta ``q-cif``
del cuestionario) y nada garantiza que coincidan en formato. La clave de dedup
canónica es el CIF **normalizado**: mayúsculas, sin espacios/puntos/guiones/barras.
"""
from __future__ import annotations

import re

_CLEAN_RE = re.compile(r"[\s./\-]")
# NIF (8 dígitos + letra) · CIF (letra + 7 dígitos + control letra/dígito) ·
# NIE ([XYZ] + 7 dígitos + letra).
_VALID_RE = re.compile(r"^([A-Z]\d{7}[A-Z0-9]|\d{8}[A-Z]|[XYZ]\d{7}[A-Z])$")


def normalize_cif(raw: str | None) -> str | None:
    """Limpia un CIF/NIF/NIE para usarlo como clave de dedup.

    Mayúsculas, sin espacios/puntos/guiones/barras. **No rechaza** formatos
    inválidos (devuelve el string limpio igualmente) para no perder el dato;
    la validación de formato es aparte (``is_valid_cif``).
    """
    if not raw:
        return None
    cleaned = _CLEAN_RE.sub("", str(raw)).upper()
    return cleaned or None


def is_valid_cif(value: str | None) -> bool:
    """True si ``value`` (tras normalizar) encaja con NIF/CIF/NIE español."""
    norm = normalize_cif(value)
    return bool(norm and _VALID_RE.match(norm))
