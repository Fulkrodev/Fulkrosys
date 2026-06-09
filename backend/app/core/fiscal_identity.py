"""Fuente única de identidad fiscal del emisor/consultor (punto #44).

Antes de #44 la identidad fiscal de FULKRO/Marcos vivía dispersa en
5+ sitios con placeholders ("__CONSULTOR_NIF__", "B00000000",
``fulkro_cif=''``, "[CIF FULKRO · alta autónomo pendiente]"). Este
módulo expone UNA sola lectura canónica que todos los consumidores
(QR Verifactu, PDF de factura, contratos/DPA, RoPA, Facturae seller)
deben usar.

Fuente de verdad: ``AdminSettings.fiscal`` (categoría JSONB persistente,
editable desde ``/admin/settings/fiscal`` y auditada por el trigger
``tg_audit_admin_settings``). Los datos bancarios admiten *fallback*
a ``Settings.marcos_bank_*`` (env) durante la transición, hasta que
Marcos los introduzca por la UI.

GARANTÍA ANTI-FALSO-VERDE (R12 · plan §0): si la categoría está vacía
(BD recién migrada, dato no introducido), el accessor devuelve cadenas
vacías / defaults neutros — NUNCA un placeholder. Los consumidores
degradan con elegancia (omiten el bloque, dejan el campo en blanco),
jamás imprimen ``__CONSULTOR_NIF__`` ni un CIF inventado.

Régimen por defecto: autónomo persona física (``tipo_persona='F'``,
``sujeto_irpf=True``) — decisión de Marcos para #44.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class FiscalIdentity:
    """Identidad fiscal del emisor, resuelta y lista para renderizar.

    Todos los campos tienen defaults neutros para degradación elegante:
    el consumidor comprueba ``has_nif`` / ``has_iban`` y omite el bloque
    si no hay dato, en vez de imprimir un placeholder.
    """

    nif: str = ""
    nombre_fiscal: str = ""
    nombre_comercial: str = ""
    tipo_persona: str = "F"  # F = persona física (autónomo) · J = jurídica
    domicilio_via: str = ""
    domicilio_cp: str = ""
    domicilio_municipio: str = ""
    domicilio_provincia: str = ""
    domicilio_pais: str = "España"
    iva_pct: float = 21.0
    sujeto_irpf: bool = True
    irpf_pct: float = 15.0
    iban: str = ""
    bank_holder: str = ""
    bank_institution: str = ""
    bank_bic: str = ""

    @property
    def display_name(self) -> str:
        """Nombre para mostrar: comercial si existe, si no el fiscal."""
        return self.nombre_comercial or self.nombre_fiscal

    @property
    def has_nif(self) -> bool:
        return bool(self.nif)

    @property
    def has_iban(self) -> bool:
        return bool(self.iban)

    @property
    def has_identity(self) -> bool:
        """True si hay al menos NIF o nombre fiscal configurado."""
        return bool(self.nif or self.nombre_fiscal)

    @property
    def domicilio_completo(self) -> str:
        """Domicilio fiscal en una línea (omite partes vacías)."""
        cp_muni = " ".join(p for p in (self.domicilio_cp, self.domicilio_municipio) if p)
        parts = [self.domicilio_via, cp_muni, self.domicilio_provincia, self.domicilio_pais]
        return ", ".join(p for p in parts if p)

    @property
    def person_type_code(self) -> str:
        """PersonTypeCode Facturae 3.2.x: 'F' física | 'J' jurídica."""
        return "J" if self.tipo_persona == "J" else "F"


def _s(value: object) -> str:
    """Coacciona a str strip-eado; None/'' → ''."""
    return str(value).strip() if value not in (None, "") else ""


async def get_fiscal_identity(db: AsyncSession) -> FiscalIdentity:
    """Devuelve la identidad fiscal canónica del emisor.

    Lee ``AdminSettings.fiscal``; para datos bancarios cae a
    ``Settings.marcos_bank_*`` si la categoría aún no los tiene
    (compat. transición pre-UI). NUNCA emite placeholders: si no hay
    dato, devuelve cadena vacía y el consumidor degrada.

    No lanza si el singleton no existe (BD sin seed): devuelve una
    identidad vacía neutra.
    """
    # Import local para evitar ciclo (admin_settings.service importa modelos).
    from backend.app.admin_settings.service import (
        AdminSettingsNotFoundError,
        get_settings as get_admin_settings,
    )
    from backend.app.config import get_settings as get_env_settings

    raw: dict = {}
    try:
        row = await get_admin_settings(db)
        raw = row.fiscal or {}
    except AdminSettingsNotFoundError:
        raw = {}

    env = get_env_settings()

    # Banca: fiscal-first, fallback env (Settings.marcos_bank_*).
    iban = _s(raw.get("iban")) or _s(env.marcos_bank_iban)
    bank_holder = _s(raw.get("bank_holder")) or _s(env.marcos_bank_holder)
    bank_institution = _s(raw.get("bank_institution")) or _s(env.marcos_bank_institution)
    bank_bic = _s(raw.get("bank_bic")) or _s(env.marcos_bank_bic)

    iva = raw.get("iva_pct")
    irpf = raw.get("irpf_pct")
    sujeto = raw.get("sujeto_irpf")
    tipo = _s(raw.get("tipo_persona")) or "F"

    return FiscalIdentity(
        nif=_s(raw.get("nif")),
        nombre_fiscal=_s(raw.get("nombre_fiscal")),
        nombre_comercial=_s(raw.get("nombre_comercial")),
        tipo_persona="J" if tipo == "J" else "F",
        domicilio_via=_s(raw.get("domicilio_via")),
        domicilio_cp=_s(raw.get("domicilio_cp")),
        domicilio_municipio=_s(raw.get("domicilio_municipio")),
        domicilio_provincia=_s(raw.get("domicilio_provincia")),
        domicilio_pais=_s(raw.get("domicilio_pais")) or "España",
        iva_pct=float(iva) if iva is not None else 21.0,
        sujeto_irpf=bool(sujeto) if sujeto is not None else True,
        irpf_pct=float(irpf) if irpf is not None else 15.0,
        iban=iban,
        bank_holder=bank_holder,
        bank_institution=bank_institution,
        bank_bic=bank_bic,
    )
