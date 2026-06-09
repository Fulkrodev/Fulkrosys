"""FULKRO — Helpers legales transversales.

Utilidades que el motor de contratos (M14), facturación (M15) y
generación de documentos (M6) comparten para decidir sobre el
régimen jurídico aplicable al cliente (LCSP / LOPDGDD / ENS AAPP vs
privado).
"""
from __future__ import annotations

from typing import Any

# CIFs de personas jurídicas públicas (orden 5/1999 AEAT sobre NIF):
#   P — Corporaciones Locales (ayuntamientos, diputaciones)
#   Q — Organismos Públicos autónomos y similares
#   R — Congregaciones e instituciones religiosas
#   S — Órganos de la Administración del Estado y CC.AA.
#
# R (religiosas) se excluye aunque sean personas jurídicas públicas
# porque no están sujetas a LCSP como poder adjudicador general (el
# Sector Público incluye AAPP + entidades asimiladas, no iglesias
# catalogadas como "instituciones sin fin de lucro").
AAPP_CIF_PREFIXES: frozenset[str] = frozenset({"P", "Q", "S"})

# Keywords que identifican una entidad del sector público al aparecer
# en el campo de tipo_organizacion o razón social. Se buscan como
# substrings en minúscula sin tildes.
AAPP_ORG_KEYWORDS: tuple[str, ...] = (
    "ayuntamiento",
    "concello",
    "udala",
    "diputacion",
    "diputacion foral",
    "cabildo",
    "consell insular",
    "consejeria",
    "conselleria",
    "departamento",  # Gobierno Vasco, Gobierno Navarra
    "ministerio",
    "secretaria de estado",
    "subsecretaria",
    "consorcio publico",
    "universidad publica",
    "escuela publica",
    "organismo autonomo",
    "agencia estatal",
    "junta de andalucia",
    "junta de castilla",
    "junta de extremadura",
    "junta de comunidades",
    "generalitat",
    "xunta",
    "gobierno vasco",
    "gobierno de navarra",
    "gobierno de canarias",
    "gobierno de aragon",
    "gobierno balear",
    "gobierno de la rioja",
    "gobierno de cantabria",
    "comunidad de madrid",
    "principado de asturias",
    "region de murcia",
    "administracion general",
    "administracion publica",
    "administracion local",
    "administracion autonomica",
    "entidad publica",
    "entidad local",
    "mancomunidad",
    "area metropolitana",
    "comarca",
    "sector publico",
)


def _normalize(text: str | None) -> str:
    """Lowercase + remove accents."""
    if not text:
        return ""
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def is_aapp_by_fields(
    cif: str | None = None,
    tipo_organizacion: str | None = None,
    razon_social: str | None = None,
) -> bool:
    """Decide si un cliente es Administración Pública (LCSP/ENS Art. 2)
    basándose en CIF + tipo_organizacion + razón social.

    Retorna True si:
    - El primer carácter del CIF es P, Q o S (personas jurídicas
      públicas según orden AEAT 5/1999), o
    - Aparece alguna palabra clave AAPP en ``tipo_organizacion`` o
      ``razon_social`` (lista de 40+ keywords cubriendo AAPP central,
      autonómica y local en los 4 idiomas oficiales).
    """
    if cif:
        first = cif.strip()[:1].upper()
        if first in AAPP_CIF_PREFIXES:
            return True
    blob = _normalize(f"{tipo_organizacion or ''} {razon_social or ''}")
    return any(kw in blob for kw in AAPP_ORG_KEYWORDS)


def is_aapp(cliente: Any) -> bool:
    """Alias que acepta un objeto/dict con los campos estandar.

    El objeto puede ser un modelo SQLAlchemy (``Client``), un dict o
    cualquier estructura con atributos ``cif``, ``tipo_organizacion``,
    ``nombre``, ``razon_social``.
    """
    if cliente is None:
        return False
    if isinstance(cliente, dict):
        cif = cliente.get("cif")
        tipo = cliente.get("tipo_organizacion") or cliente.get("tipo")
        rs = cliente.get("razon_social") or cliente.get("nombre")
    else:
        cif = getattr(cliente, "cif", None)
        tipo = (
            getattr(cliente, "tipo_organizacion", None)
            or getattr(cliente, "tipo", None)
        )
        rs = (
            getattr(cliente, "razon_social", None)
            or getattr(cliente, "nombre", None)
        )
    return is_aapp_by_fields(cif=cif, tipo_organizacion=tipo, razon_social=rs)
