"""Validación magic-bytes de uploads · sin dependencia (auditoría 2026-06-07).

Defensa de borde contra suplantación de tipo (content-type/extensión spoofing):
verifica que los primeros bytes del fichero coincidan con la firma binaria
esperada para su extensión declarada. Complementa —no sustituye— al antivirus
(clamd · m07) y a la whitelist de extensiones.

Sin python-magic/libmagic (no instalado · evita tocar el venv compartido): un
diccionario de firmas cubre los tipos permitidos en los portales (PDF, ofimática
OOXML/OLE2, imágenes, zip). Texto plano (txt/csv) no tiene firma fiable → se omite.
"""
from __future__ import annotations

# extensión (lower) -> firmas magic aceptables · None = sin firma fiable (se permite)
_MAGIC_SIGNATURES: dict[str, tuple[bytes, ...] | None] = {
    ".pdf": (b"%PDF-",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".gif": (b"GIF87a", b"GIF89a"),
    ".zip": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
    # OOXML (docx/xlsx/pptx) son contenedores ZIP
    ".docx": (b"PK\x03\x04",),
    ".xlsx": (b"PK\x03\x04",),
    ".pptx": (b"PK\x03\x04",),
    # OLE2 compound (ofimática legacy)
    ".doc": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
    ".xls": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
    # texto plano · sin magic fiable
    ".txt": None,
    ".csv": None,
}


class MagicByteMismatch(ValueError):
    """El contenido no coincide con la firma esperada para la extensión."""


def validate_magic_bytes(content: bytes, ext: str) -> None:
    """Lanza ``MagicByteMismatch`` si ``content`` no empieza por una firma válida.

    - Extensión no catalogada → no valida (la gobierna la whitelist de extensiones).
    - Extensión con firma ``None`` (txt/csv) → no valida (texto sin magic fiable).
    """
    ext = (ext or "").lower()
    if ext not in _MAGIC_SIGNATURES:
        return
    sigs = _MAGIC_SIGNATURES[ext]
    if sigs is None:
        return
    head = content[:16]
    if not any(head.startswith(s) for s in sigs):
        raise MagicByteMismatch(
            f"El contenido del fichero no coincide con la extensión '{ext}' "
            f"(posible suplantación de tipo · rechazado)."
        )
