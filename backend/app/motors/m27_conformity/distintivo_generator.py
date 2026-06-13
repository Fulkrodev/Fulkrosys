"""Distintivo + Declaración Conformidad CCN-STIC 809 · SAN-C.MB-9.2.

Genera 2 artefactos canónicos para cierre FASE 9:

* **Distintivo SVG** publicable en sede electrónica del cliente. Logo
  ENS + categoría + año + cert_id. URL pública (sin auth) con firma
  Ed25519 verificable vía ``/api/v1/auth/verify-signature``.
* **Declaración Conformidad Básica DOCX** (E-180) firmable por el
  Responsable de Seguridad. Para BÁSICA es autoevaluación (no ENAC).
  Para Media/Alta este artefacto NO sustituye al certificado ENAC sino
  que documenta el cierre interno previo al envío a entidad acreditada.

cert_id es UUID determinístico ``uuid5(NAMESPACE_OID, project_id::str)``
para que el mismo proyecto produzca siempre el mismo cert_id (idempotente
+ cacheable + URL pública estable).

Refs: SAN-C.MB-9.2
"""
from __future__ import annotations

import io
import uuid
from dataclasses import dataclass
from datetime import date, timedelta

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.fulkro_identity import (
    FULKRO_DISTINTIVO_COLOR_PANTONE_ORANGE_021C,
)


DISTINTIVO_TEMPLATE_VERSION = "1.0"
DECLARATION_DOCUMENT_KIND = "E-180"
DEFAULT_VALIDITY_YEARS = 2


def derive_cert_id(project_id: uuid.UUID) -> uuid.UUID:
    """Devuelve cert_id determinístico desde project_id (idempotente).

    Misma medida → mismo cert_id, sin necesidad de tabla auxiliar (evita
    ALTER schema). El cert_id se incrusta en SVG + DOCX + URL pública.
    """
    return uuid.uuid5(uuid.NAMESPACE_OID, f"fulkro-conformity:{project_id}")


@dataclass(slots=True)
class DistintivoContext:
    """Contexto aglutinado para distintivo + declaración."""

    project_id: uuid.UUID
    cert_id: uuid.UUID
    client_name: str
    client_cif: str
    client_domicilio: str
    system_name: str
    system_category: str
    today: str
    expiry_date: str
    public_badge_url: str
    services_summary: str
    information_summary: str
    assets_essential_count: int
    dda_total: int
    dda_aplicables: int
    dda_con_refuerzos: int
    dda_no_aplica: int
    conformes_count: int
    no_conformes_count: int
    pct_conformidad: float
    rseg_name: str
    rseg_email: str
    # #2 Ola 7 · firmante de la Declaración de Conformidad 809 = Dirección /
    # órgano superior (CCN-STIC 809 Anexo A · asume la responsabilidad sobre la
    # seguridad del sistema · NO el RSeg, que gestiona pero no declara).
    sponsor_name: str = "(pendiente designación de Dirección)"
    sponsor_email: str = ""


async def build_distintivo_context(
    db: AsyncSession,
    project_id: uuid.UUID,
    public_base_url: str = "",
) -> DistintivoContext:
    """Construye contexto cross-motor para distintivo + declaración."""
    proj_row = await db.execute(
        sa_text(
            "SELECT p.id, p.client_id, "
            "       COALESCE(c.nombre, 'Cliente') AS client_name, "
            "       COALESCE(c.cif, '') AS cif, "
            "       COALESCE(p.nombre, 'Sistema') AS system_name, "
            "       COALESCE(c.domicilio_fiscal, '') AS domicilio "
            "FROM projects p "
            "LEFT JOIN clients c ON c.id = p.client_id "
            "WHERE p.id = :pid"
        ),
        {"pid": str(project_id)},
    )
    proj = proj_row.first()
    if proj is None:
        raise ValueError(f"Project {project_id} not found")

    client_id = proj[1]
    client_name = str(proj[2])
    client_cif = str(proj[3] or "")
    client_domicilio = str(proj[5] or "")

    # Categoría
    cat_row = await db.execute(
        sa_text(
            "SELECT c.categoria_resultante FROM categorizations c "
            "JOIN systems s ON s.id = c.system_id "
            "WHERE s.project_id = :pid AND c.deleted_at IS NULL "
            "ORDER BY c.created_at DESC LIMIT 1"
        ),
        {"pid": str(project_id)},
    )
    cat = cat_row.first()
    system_category = cat[0] if cat else "BASICA"

    # DdA totales
    dda_row = await db.execute(
        sa_text(
            "SELECT count(*), "
            "       count(*) FILTER (WHERE aplicabilidad = 'aplica'), "
            "       count(*) FILTER (WHERE aplicabilidad = 'aplica_con_refuerzos'), "
            "       count(*) FILTER (WHERE aplicabilidad = 'no_aplica'), "
            "       count(*) FILTER (WHERE estado_implementacion = 'implantada') "
            "FROM dda_entries WHERE project_id = :pid"
        ),
        {"pid": str(project_id)},
    )
    dda = dda_row.first()
    dda_total = int(dda[0] or 0) if dda else 0
    dda_aplicables = int(dda[1] or 0) if dda else 0
    dda_con_refuerzos = int(dda[2] or 0) if dda else 0
    dda_no_aplica = int(dda[3] or 0) if dda else 0
    conformes_count = int(dda[4] or 0) if dda else 0
    no_conformes_count = max(
        (dda_aplicables + dda_con_refuerzos) - conformes_count, 0
    )
    pct_conformidad = round(
        (conformes_count / max(dda_aplicables + dda_con_refuerzos, 1)) * 100,
        1,
    )

    # RSEG desde M30
    rseg_name = "(pendiente designación)"
    rseg_email = ""
    if client_id:
        rseg_row = await db.execute(
            sa_text(
                "SELECT full_name, email FROM client_contacts "
                "WHERE client_id = :cid AND is_active = true "
                "AND deleted_at IS NULL "
                "AND role_category IN ('responsable_seguridad', 'rseg', 'ciso') "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            {"cid": str(client_id)},
        )
        rseg = rseg_row.first()
        if rseg:
            rseg_name = rseg[0] or rseg_name
            rseg_email = rseg[1] or ""

    # #2 Ola 7 · Dirección/órgano superior (firmante de la Declaración 809) ·
    # role_category='sponsor' en M30. Es quien declara la conformidad (asume la
    # responsabilidad), distinto del RSeg (que gestiona la seguridad).
    sponsor_name = "(pendiente designación de Dirección)"
    sponsor_email = ""
    if client_id:
        sponsor_row = await db.execute(
            sa_text(
                "SELECT full_name, email FROM client_contacts "
                "WHERE client_id = :cid AND is_active = true "
                "AND deleted_at IS NULL "
                "AND role_category = 'sponsor' "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            {"cid": str(client_id)},
        )
        sponsor = sponsor_row.first()
        if sponsor:
            sponsor_name = sponsor[0] or sponsor_name
            sponsor_email = sponsor[1] or ""

    # Activos esenciales (M22)
    try:
        assets_row = await db.execute(
            sa_text(
                "SELECT count(*) FROM magerit_assets a "
                "JOIN magerit_analysis ma ON ma.id = a.analysis_id "
                "WHERE ma.project_id = :pid"
            ),
            {"pid": str(project_id)},
        )
        assets_essential_count = assets_row.scalar() or 0
    except Exception:
        assets_essential_count = 0

    cert_id = derive_cert_id(project_id)
    today = date.today()
    expiry = today + timedelta(days=365 * DEFAULT_VALIDITY_YEARS)

    public_badge_url = (
        f"{public_base_url.rstrip('/')}"
        f"/api/v1/conformity/badge/{cert_id}/badge.svg"
    ) if public_base_url else (
        f"/api/v1/conformity/badge/{cert_id}/badge.svg"
    )

    return DistintivoContext(
        project_id=project_id,
        cert_id=cert_id,
        client_name=client_name,
        client_cif=client_cif,
        client_domicilio=client_domicilio,
        system_name=str(proj[4]),
        system_category=str(system_category),
        today=today.isoformat(),
        expiry_date=expiry.isoformat(),
        public_badge_url=public_badge_url,
        services_summary="Servicios identificados en M01 categorización",
        information_summary="Información identificada en M01 categorización",
        assets_essential_count=int(assets_essential_count),
        dda_total=dda_total,
        dda_aplicables=dda_aplicables,
        dda_con_refuerzos=dda_con_refuerzos,
        dda_no_aplica=dda_no_aplica,
        conformes_count=conformes_count,
        no_conformes_count=no_conformes_count,
        pct_conformidad=pct_conformidad,
        rseg_name=rseg_name,
        rseg_email=rseg_email,
        sponsor_name=sponsor_name,
        sponsor_email=sponsor_email,
    )


# ── SVG Distintivo ────────────────────────────────────────────────────


# F-14-06 (Ejecutable 8 Pasada 16): el distintivo de conformidad ENS usa un color
# canónico ÚNICO — Pantone Orange 021C (#FE5000) por CCN-STIC 809 — NO un color
# por categoría. Centralizado en fulkro_identity (single source of truth).
# (Antes: BASICA verde / MEDIA azul / ALTA violeta · incorrecto vs CCN-STIC 809.)


def generate_distintivo_svg(ctx: DistintivoContext) -> str:
    """Genera distintivo SVG canónico CCN-STIC 809.

    Estructura visual:

    * Badge horizontal 320×120 px
    * Banda superior: "ENS" + categoría
    * Cuerpo central: cliente + sistema
    * Banda inferior: cert_id corto + año vigencia
    * Color: Pantone Orange 021C (#FE5000) canónico CCN-STIC 809 · único para
      todas las categorías (B/M/A).
    """
    color = FULKRO_DISTINTIVO_COLOR_PANTONE_ORANGE_021C
    short_cert = str(ctx.cert_id)[:8]
    issued_year = ctx.today[:4]
    expiry_year = ctx.expiry_date[:4]

    safe_client = _escape_xml(ctx.client_name)
    safe_system = _escape_xml(ctx.system_name)
    safe_cat = _escape_xml(ctx.system_category)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 120" width="320" height="120" role="img" aria-label="Distintivo Conformidad ENS {safe_cat}">
  <title>Distintivo Conformidad ENS · {safe_client} · {safe_cat}</title>
  <desc>FULKRO certificación ENS · cert_id {ctx.cert_id} · vigencia {issued_year}-{expiry_year}</desc>
  <rect x="0" y="0" width="320" height="120" rx="8" ry="8" fill="#FFFFFF" stroke="{color}" stroke-width="2"/>
  <rect x="0" y="0" width="320" height="32" rx="8" ry="8" fill="{color}"/>
  <text x="16" y="22" fill="#FFFFFF" font-family="Helvetica, Arial, sans-serif" font-size="14" font-weight="700">ESQUEMA NACIONAL DE SEGURIDAD</text>
  <text x="304" y="22" fill="#FFFFFF" font-family="Helvetica, Arial, sans-serif" font-size="14" font-weight="700" text-anchor="end">{safe_cat}</text>
  <text x="160" y="62" fill="#111827" font-family="Helvetica, Arial, sans-serif" font-size="13" font-weight="600" text-anchor="middle">{safe_client[:48]}</text>
  <text x="160" y="80" fill="#374151" font-family="Helvetica, Arial, sans-serif" font-size="11" text-anchor="middle">{safe_system[:64]}</text>
  <rect x="0" y="92" width="320" height="28" fill="#F3F4F6"/>
  <text x="16" y="110" fill="#374151" font-family="Helvetica, Arial, sans-serif" font-size="10">cert: {short_cert}</text>
  <text x="304" y="110" fill="#374151" font-family="Helvetica, Arial, sans-serif" font-size="10" text-anchor="end">{issued_year} – {expiry_year}</text>
</svg>
"""


def _escape_xml(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# ── DOCX Declaración ──────────────────────────────────────────────────


def _add_heading(doc: Document, text: str, level: int = 1) -> None:
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = RGBColor(0x00, 0x00, 0x00)


def generate_declaration_docx(ctx: DistintivoContext) -> io.BytesIO:
    """Genera Declaración Conformidad Básica E-180 (CCN-STIC 809)."""
    doc = Document()

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(
        "Declaración de Conformidad con el Esquema Nacional de Seguridad"
    )
    run.bold = True
    run.font.size = Pt(15)

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub_run = sub.add_run(f"Categoría {ctx.system_category}")
    sub_run.bold = True
    sub_run.font.size = Pt(13)

    is_basica = (ctx.system_category or "").strip().upper() == "BASICA"

    # Naturaleza del artefacto · regla de nomenclatura CCN-STIC 809 (R26): lo que
    # FULKRO genera es el DISTINTIVO de conformidad (autopublicable). La palabra
    # «certificado» queda reservada al documento de la entidad de certificación
    # acreditada (MEDIA/ALTA), que NUNCA emite FULKRO.
    disc = doc.add_paragraph()
    disc.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if is_basica:
        disc_text = (
            "Distintivo de Conformidad con el ENS (CCN-STIC 809) · "
            "Autoevaluación de categoría BÁSICA. La categoría BÁSICA se acredita "
            "por autoevaluación, sin certificación por entidad acreditada."
        )
    else:
        disc_text = (
            "Distintivo de Conformidad con el ENS (CCN-STIC 809) · artefacto "
            "autopublicable por la entidad. NO sustituye al certificado de "
            "conformidad emitido por la entidad de certificación acreditada, que "
            "es el documento de certificación oficial para las categorías "
            "MEDIA y ALTA."
        )
    disc_run = disc.add_run(disc_text)
    disc_run.italic = True
    disc_run.font.size = Pt(9)

    doc.add_paragraph(
        f"Cliente: {ctx.client_name} ({ctx.client_cif})\n"
        f"Domicilio fiscal: {ctx.client_domicilio or '(no informado)'}\n"
        f"Sistema: {ctx.system_name}\n"
        f"Identificador del distintivo: {ctx.cert_id}\n"
        f"Fecha emisión: {ctx.today}\n"
        f"Vigencia: {DEFAULT_VALIDITY_YEARS} años (vencimiento {ctx.expiry_date})\n"
        f"Plantilla: {DECLARATION_DOCUMENT_KIND} v{DISTINTIVO_TEMPLATE_VERSION}"
    )

    _add_heading(doc, "1. Identificación de la entidad", 1)
    if is_basica:
        ident_text = (
            f"{ctx.client_name} ({ctx.client_cif}), con domicilio fiscal en "
            f"{ctx.client_domicilio or '(no informado)'}, declara haber cumplido "
            f"los requisitos del Esquema Nacional de Seguridad (RD 311/2022) en la "
            f"Categoría {ctx.system_category}, conforme al procedimiento de "
            f"autoevaluación CCN-STIC 809."
        )
    else:
        ident_text = (
            f"{ctx.client_name} ({ctx.client_cif}), con domicilio fiscal en "
            f"{ctx.client_domicilio or '(no informado)'}, ha completado la "
            f"implantación del Esquema Nacional de Seguridad (RD 311/2022) en la "
            f"Categoría {ctx.system_category}. La conformidad se verifica mediante "
            f"auditoría de certificación por entidad de certificación acreditada "
            f"(CCN-STIC 808); este distintivo (CCN-STIC 809) acompaña, y no "
            f"sustituye, a dicho certificado."
        )
    doc.add_paragraph(ident_text)

    _add_heading(doc, "2. Sistema certificado y alcance", 1)
    doc.add_paragraph(
        f"Sistema: {ctx.system_name}\n"
        f"Servicios prestados: {ctx.services_summary}\n"
        f"Tipos de información: {ctx.information_summary}\n"
        f"Activos esenciales identificados: {ctx.assets_essential_count}\n"
        f"Periodo: {ctx.today} – {ctx.expiry_date}"
    )

    _add_heading(doc, "3. Categoría del sistema", 1)
    doc.add_paragraph(
        f"Conforme al RD 311/2022 Anexo I (regla del máximo aplicada sobre "
        f"las dimensiones D-I-C-A-T), el sistema ha sido clasificado como "
        f"Categoría {ctx.system_category}."
    )

    _add_heading(doc, "4. Resultado de la autoevaluación", 1)
    rtbl = doc.add_table(rows=1, cols=2)
    rtbl.style = "Light Grid Accent 1"
    rtbl.rows[0].cells[0].text = "Métrica"
    rtbl.rows[0].cells[1].text = "Valor"
    for label, value in [
        ("Total medidas Anexo II evaluadas", str(ctx.dda_total)),
        ("Aplicables base", str(ctx.dda_aplicables)),
        ("Aplicables con refuerzos", str(ctx.dda_con_refuerzos)),
        ("No aplicables (justificadas)", str(ctx.dda_no_aplica)),
        ("Conformes", str(ctx.conformes_count)),
        ("No conformes", str(ctx.no_conformes_count)),
        ("Porcentaje conformidad", f"{ctx.pct_conformidad}%"),
    ]:
        cells = rtbl.add_row().cells
        cells[0].text = label
        cells[1].text = value

    _add_heading(doc, "5. Distintivo de conformidad", 1)
    doc.add_paragraph(
        "Conforme a CCN-STIC 809, esta entidad publicará el distintivo "
        "de conformidad en su sede electrónica con la siguiente URL:"
    )
    p = doc.add_paragraph()
    p.add_run(ctx.public_badge_url).bold = True
    doc.add_paragraph(
        "El distintivo se sirve con firma digital Ed25519 verificable "
        "contra la clave pública FULKRO en /api/v1/auth/public-key."
    )

    _add_heading(doc, "6. Compromiso de mantenimiento", 1)
    doc.add_paragraph(
        "El cliente se compromete a: (a) mantener vigentes las medidas "
        "declaradas durante el periodo; (b) notificar a CCN-CERT vía "
        "LUCIA cualquier incidente significativo (art. 33 RD 311/2022); "
        "(c) ejecutar autoevaluación o reauditoría antes del vencimiento; "
        "(d) disparar auditoría extraordinaria ante cambios sustanciales "
        "(art. 31)."
    )

    _add_heading(
        doc,
        "7. Firma de la Dirección (órgano superior · CCN-STIC 809 Anexo A)",
        1,
    )
    doc.add_paragraph(
        "Conforme a la CCN-STIC 809 Anexo A, la Declaración de Conformidad la "
        "suscribe la Dirección u órgano superior de la entidad, que asume la "
        "responsabilidad sobre la seguridad del sistema de información objeto de "
        "esta declaración. El Responsable de Seguridad gestiona y supervisa las "
        "medidas; la declaración de conformidad es un acto de responsabilidad de "
        "la Dirección."
    )
    sig = doc.add_table(rows=1, cols=2)
    sig.style = "Light Grid Accent 1"
    sig.rows[0].cells[0].text = "Campo"
    sig.rows[0].cells[1].text = "Valor"
    for label, value in [
        ("Nombre (Dirección / órgano superior)", ctx.sponsor_name),
        ("Email", ctx.sponsor_email),
        ("Firma", "_____________"),
        ("Fecha de firma", "_____________"),
    ]:
        cells = sig.add_row().cells
        cells[0].text = label
        cells[1].text = value

    footer = doc.add_paragraph()
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fr = footer.add_run(
        f"Documento generado por FULKRO conforme CCN-STIC 809 · "
        f"plantilla {DECLARATION_DOCUMENT_KIND} v{DISTINTIVO_TEMPLATE_VERSION} · "
        f"cert_id {ctx.cert_id}"
    )
    fr.italic = True
    fr.font.size = Pt(8)

    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio
