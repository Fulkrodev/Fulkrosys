"""7 modelos legales DOCX programáticos · SAN-C.MB-10.2.

Catálogo manual ENS + CCN-STIC 823 para cadena suministro:

* C-100  Contrato prestación servicios
* C-110  NDA bilateral
* C-120  Encargo tratamiento (RGPD Art. 28)
* C-130  Cláusulas terceros ENS (CCN-STIC 823)
* C-140  Compromiso confidencialidad empleados/subcontratistas
* C-150  DPA Data Processing Agreement (SCC + Schrems II)
* C-160  Contrato marco subcontratación pentesting (back-to-back)

Generación programática python-docx (no archivos binarios en repo) ·
mismo patrón que ``rectores_generator.py`` (E-160 / E-170). Cada modelo
acepta un ``LegalContext`` aglutinador con datos del cliente + proyecto
+ proveedor (cuando aplica) y produce DOCX firmable.

Refs: SAN-C.MB-10.2
"""
from __future__ import annotations

import io
import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession


LEGAL_TEMPLATES_VERSION = "1.0"


# ── Catálogo ──────────────────────────────────────────────────────────


@dataclass(slots=True, frozen=True)
class LegalTemplateInfo:
    code: str
    slug: str
    title: str
    description: str
    requires_provider: bool = False
    ccn_stic: str | None = None


LEGAL_TEMPLATES: list[LegalTemplateInfo] = [
    LegalTemplateInfo(
        code="C-100",
        slug="contrato_prestacion_servicios",
        title="Contrato de prestación de servicios de consultoría ENS",
        description=(
            "Cláusulas: alcance · entregables · plazos · honorarios · "
            "IP entregables · RC profesional · auditoría · no concurrencia."
        ),
    ),
    LegalTemplateInfo(
        code="C-110",
        slug="nda_bilateral",
        title="NDA bilateral",
        description=(
            "Acuerdo de confidencialidad bilateral · información sensible · "
            "duración · excepciones · jurisdicción."
        ),
    ),
    LegalTemplateInfo(
        code="C-120",
        slug="encargo_tratamiento_rgpd_art28",
        title="Encargo de tratamiento de datos (RGPD Art. 28)",
        description=(
            "Encargo formal Art. 28 RGPD · finalidad · subcontratación · "
            "medidas técnicas · devolución/destrucción · asistencia AEPD."
        ),
        ccn_stic="RGPD Art. 28",
    ),
    LegalTemplateInfo(
        code="C-130",
        slug="clausulas_terceros_ens",
        title="Cláusulas terceros ENS (cadena suministro)",
        description=(
            "CCN-STIC 823 cadena suministro · conformidad ENS · notificación "
            "incidentes · derecho auditoría · SLA/SLO · soberanía datos · plan salida."
        ),
        requires_provider=True,
        ccn_stic="CCN-STIC 823",
    ),
    LegalTemplateInfo(
        code="C-140",
        slug="compromiso_confidencialidad_empleados",
        title="Compromiso de confidencialidad empleados/subcontratistas",
        description=(
            "Para empleados internos + subcontratistas con acceso a sistema · "
            "obligaciones · sanciones · post-relación contractual."
        ),
    ),
    LegalTemplateInfo(
        code="C-150",
        slug="dpa_data_processing_agreement",
        title="DPA · Data Processing Agreement (SCC + Schrems II)",
        description=(
            "Cláusulas SCC UE 2021/914 + medidas suplementarias post-Schrems II · "
            "transferencias internacionales · evaluación impacto."
        ),
        requires_provider=True,
    ),
    LegalTemplateInfo(
        code="C-160",
        slug="contrato_marco_pentesting",
        title="Contrato marco subcontratación pentesting (back-to-back)",
        description=(
            "Subcontratación pentesting con cláusulas back-to-back FULKRO ↔ partner · "
            "RC · alcance · disponibilidad · entrega informe · destrucción evidencia."
        ),
        requires_provider=True,
    ),
]

_BY_SLUG: dict[str, LegalTemplateInfo] = {t.slug: t for t in LEGAL_TEMPLATES}


def get_legal_template(slug: str) -> LegalTemplateInfo:
    if slug not in _BY_SLUG:
        raise KeyError(f"Legal template '{slug}' no existe en catálogo")
    return _BY_SLUG[slug]


def list_legal_templates() -> list[LegalTemplateInfo]:
    return list(LEGAL_TEMPLATES)


# ── Context aglutinador ───────────────────────────────────────────────


@dataclass(slots=True)
class LegalContext:
    project_id: uuid.UUID
    client_name: str = "Cliente"
    client_cif: str = ""
    client_domicilio: str = ""
    client_representante: str = "(pendiente designación)"
    client_persona_contacto: str = ""  # #9 · contacto del cliente (default firmante)
    fulkro_name: str = "FULKRO Consultoría ENS"
    fulkro_cif: str = ""
    fulkro_domicilio: str = "Madrid, España"
    fulkro_representante: str = "Marcos Mata García"
    provider_name: str | None = None
    provider_cif: str | None = None
    provider_role: str | None = None
    today: str = field(default_factory=lambda: date.today().isoformat())
    rseg_name: str = "(pendiente designación)"
    dpo_name: str = "(pendiente designación)"
    project_scope: str = "Consultoría ENS conforme RD 311/2022"
    # #42 FASE C · enriquecimiento del contrato comercial redactado (C-001).
    categoria: str | None = None
    importe_total: float | None = None
    hitos: list[dict[str, Any]] = field(default_factory=list)  # code/pct/description/amount
    alcance: dict[str, Any] | None = None  # alcance_snapshot comercial (#10 B1)
    llm_clauses: dict[str, Any] | None = None  # cláusulas Agent 20 (complemento)


async def build_legal_context(
    db: AsyncSession,
    project_id: uuid.UUID,
    provider_name: str | None = None,
    provider_cif: str | None = None,
) -> LegalContext:
    """Aglutina datos del proyecto + cliente + RSEG/DPO desde M30.

    Identidad fiscal de FULKRO/emisor desde la FUENTE ÚNICA
    (``core.fiscal_identity`` · punto #44); degradación elegante a los
    defaults de ``LegalContext`` si aún no está configurada.
    """
    from backend.app.core.fiscal_identity import get_fiscal_identity
    fi = await get_fiscal_identity(db)

    proj_row = await db.execute(
        sa_text(
            "SELECT p.id, p.client_id, "
            "       COALESCE(c.nombre, 'Cliente') AS cn, "
            "       COALESCE(c.cif, '') AS cif, "
            # #9 · domicilio_fiscal + persona_contacto (#7.5) para el contrato.
            "       COALESCE(c.domicilio_fiscal, '') AS dom, "
            "       COALESCE(c.persona_contacto, '') AS pcont "
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
    rseg_name = "(pendiente designación)"
    dpo_name = "(pendiente designación)"
    if client_id:
        roles_row = await db.execute(
            sa_text(
                "SELECT role_category, full_name FROM client_contacts "
                "WHERE client_id = :cid AND is_active = true "
                "AND deleted_at IS NULL "
                "AND role_category IN ('responsable_seguridad', 'rseg', 'ciso', "
                "                       'delegado_proteccion_datos', 'dpo') "
                "ORDER BY created_at DESC"
            ),
            {"cid": str(client_id)},
        )
        for cat, name in roles_row.fetchall():
            if cat in {"responsable_seguridad", "rseg", "ciso"} and rseg_name.startswith("("):
                rseg_name = name or rseg_name
            if cat in {"delegado_proteccion_datos", "dpo"} and dpo_name.startswith("("):
                dpo_name = name or dpo_name

    return LegalContext(
        project_id=project_id,
        client_name=str(proj[2]),
        client_cif=str(proj[3] or ""),
        client_domicilio=str(proj[4] or ""),
        client_persona_contacto=str(proj[5] or ""),
        fulkro_name=fi.display_name or "FULKRO Consultoría ENS",
        fulkro_cif=fi.nif,
        fulkro_domicilio=fi.domicilio_completo or "Madrid, España",
        fulkro_representante=fi.nombre_fiscal or "Marcos Mata García",
        provider_name=provider_name,
        provider_cif=provider_cif,
        rseg_name=rseg_name,
        dpo_name=dpo_name,
    )


# ── Generators ────────────────────────────────────────────────────────


def _heading(doc: Document, text: str, level: int = 1) -> None:
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = RGBColor(0x00, 0x00, 0x00)


def _add_signature_table(doc: Document, signatories: list[tuple[str, str]]) -> None:
    """Tabla firma · ``signatories`` = [(rol, nombre), ...]."""
    _heading(doc, "Firmas", 1)
    tbl = doc.add_table(rows=1, cols=4)
    tbl.style = "Light Grid Accent 1"
    hdr = tbl.rows[0].cells
    hdr[0].text = "Rol"
    hdr[1].text = "Nombre"
    hdr[2].text = "Firma"
    hdr[3].text = "Fecha"
    for rol, nombre in signatories:
        row = tbl.add_row().cells
        row[0].text = rol
        row[1].text = nombre


def _fmt_eur(n: Any) -> str:
    """Formato € español (miles con punto · decimales con coma)."""
    if not isinstance(n, (int, float)):
        return ""
    return f"{n:,.2f} €".replace(",", "⁣").replace(".", ",").replace("⁣", ".")


def _format_commercial_scope(ctx: LegalContext) -> str:
    """#42 §1 · descripción del alcance COMERCIAL desde el snapshot (#10 B1)."""
    alc = ctx.alcance or {}
    parts: list[str] = []
    cat = alc.get("categoria") or ctx.categoria
    if cat:
        parts.append(f"categoría ENS {cat}")
    if alc.get("sistemas"):
        parts.append(f"{alc['sistemas']} sistema(s) de información")
    if alc.get("ubicaciones"):
        parts.append(f"{alc['ubicaciones']} ubicación(es)/sede(s)")
    if alc.get("empleados"):
        parts.append(f"organización de ~{alc['empleados']} empleados")
    base = "; ".join(parts) if parts else ctx.project_scope
    excl = alc.get("exclusiones") or []
    excl_txt = ""
    if excl:
        excl_txt = " Exclusiones del alcance: " + "; ".join(str(e) for e in excl) + "."
    return base + "." + excl_txt


def _add_hitos_table(doc: Document, hitos: list[dict[str, Any]], total: float | None) -> None:
    """#42 §2 · tabla de hitos de pago (Hito/Concepto/%/Importe)."""
    tbl = doc.add_table(rows=1, cols=4)
    tbl.style = "Light Grid Accent 1"
    hdr = tbl.rows[0].cells
    hdr[0].text = "Hito"
    hdr[1].text = "Concepto"
    hdr[2].text = "%"
    hdr[3].text = "Importe"
    for h in hitos:
        row = tbl.add_row().cells
        row[0].text = str(h.get("code", ""))
        row[1].text = str(h.get("description", ""))
        pct = h.get("pct")
        row[2].text = f"{pct:.0f}%" if isinstance(pct, (int, float)) else ""
        row[3].text = _fmt_eur(h.get("amount"))
    if total is not None:
        trow = tbl.add_row().cells
        trow[0].text = ""
        trow[1].text = "TOTAL"
        trow[2].text = "100%"
        trow[3].text = _fmt_eur(total)


def _add_llm_complement_clauses(doc: Document, llm_clauses: dict[str, Any]) -> None:
    """#42/#43 · cláusulas específicas del caso (Agent 20) como COMPLEMENTO · NO
    tocan el esqueleto de 8 cláusulas estáticas (decisión Marcos)."""
    draft = llm_clauses.get("clauses_draft") or llm_clauses.get("draft")
    if not draft:
        return
    _heading(doc, "9. Cláusulas específicas del caso (complementarias)", 1)
    doc.add_paragraph(
        "Las siguientes cláusulas, específicas de este encargo, complementan —sin "
        "sustituir— el clausulado general anterior:"
    )
    if isinstance(draft, str):
        for para in (p.strip() for p in draft.split("\n") if p.strip()):
            doc.add_paragraph(para)
    elif isinstance(draft, list):
        for item in draft:
            doc.add_paragraph(str(item))
    else:
        doc.add_paragraph(str(draft))


def _add_title_block(doc: Document, info: LegalTemplateInfo, ctx: LegalContext) -> None:
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(info.title)
    run.bold = True
    run.font.size = Pt(15)

    # #9/#44 · bloque de partes con datos fiscales (domicilio + contacto).
    cliente_line = f"Cliente: {ctx.client_name} ({ctx.client_cif})"
    if ctx.client_domicilio:
        cliente_line += f" · Domicilio: {ctx.client_domicilio}"
    if ctx.client_persona_contacto:
        cliente_line += f" · Contacto: {ctx.client_persona_contacto}"
    fulkro_line = f"FULKRO: {ctx.fulkro_name} ({ctx.fulkro_cif})"
    if ctx.fulkro_domicilio:
        fulkro_line += f" · Domicilio: {ctx.fulkro_domicilio}"
    doc.add_paragraph(
        f"{cliente_line}\n"
        f"{fulkro_line}\n"
        # La fecha de FIRMA se consigna en el bloque de firmas (se fija al firmar);
        # aquí solo la fecha de generación del documento (#42 · evita fecha falsa).
        f"Fecha de generación: {ctx.today} · la fecha de firma se consigna al firmar\n"
        f"Plantilla: {info.code} v{LEGAL_TEMPLATES_VERSION}"
    )


def _gen_contrato_prestacion_servicios(ctx: LegalContext, info: LegalTemplateInfo) -> Document:
    doc = Document()
    _add_title_block(doc, info, ctx)
    _heading(doc, "1. Objeto", 1)
    doc.add_paragraph(
        f"FULKRO prestará al Cliente servicios de consultoría para la "
        f"implantación del Esquema Nacional de Seguridad conforme al alcance "
        f"descrito: {_format_commercial_scope(ctx)} Los entregables incluirán "
        f"los documentos previstos en el Plan de Adecuación (E-150) y los "
        f"informes de auditoría interna conforme CCN-STIC 802."
    )
    _heading(doc, "2. Plazos y honorarios", 1)
    if ctx.hitos:
        total_txt = (
            _fmt_eur(ctx.importe_total) if ctx.importe_total is not None else "—"
        )
        doc.add_paragraph(
            f"El importe total de los honorarios asciende a {total_txt}, "
            f"facturado conforme al siguiente calendario de hitos vinculados a "
            f"las fases del proyecto:"
        )
        _add_hitos_table(doc, ctx.hitos, ctx.importe_total)
        doc.add_paragraph(
            "Las desviaciones del alcance requerirán un cambio de alcance formal "
            "con su correspondiente ajuste económico."
        )
    else:
        doc.add_paragraph(
            "Los plazos y honorarios se acuerdan en propuesta económica anexa "
            "(P-001). Desviaciones requerirán cambio de alcance formal."
        )
    _heading(doc, "3. Protección de datos personales (art. 28 RGPD)", 1)
    doc.add_paragraph(
        "En la ejecución del presente contrato FULKRO podrá acceder a sistemas "
        "del Cliente que traten datos personales (entornos cloud, evidencias). "
        "Dicho tratamiento se rige por el Acuerdo de Encargo del Tratamiento "
        "(DPA · art. 28 RGPD) suscrito entre las Partes, que forma parte "
        "integrante del presente contrato. FULKRO tratará los datos únicamente "
        "para los fines de la consultoría, conforme a las instrucciones "
        "documentadas del Cliente, aplicando las medidas técnicas y "
        "organizativas exigidas por el ENS y guardando confidencialidad."
    )
    _heading(doc, "4. Propiedad intelectual de entregables", 1)
    doc.add_paragraph(
        "Los entregables se ceden al Cliente para su uso interno indefinido. "
        "FULKRO conserva know-how y plantillas genéricas. Cláusula compatible "
        "con cesión derechos explotación obras conforme Ley Propiedad Intelectual."
    )
    _heading(doc, "5. Limitación de responsabilidad", 1)
    doc.add_paragraph(
        "La responsabilidad de FULKRO se limita al importe de honorarios "
        "abonados en los últimos 12 meses, salvo dolo o negligencia grave. "
        "Excluidos daños indirectos, lucro cesante, pérdida de oportunidad."
    )
    _heading(doc, "6. Seguro de RC profesional", 1)
    doc.add_paragraph(
        "FULKRO mantendrá seguro de Responsabilidad Civil profesional con "
        "capital mínimo 600.000 € durante toda la vigencia y posteriores 24 meses."
    )
    _heading(doc, "7. Cláusula de auditoría", 1)
    doc.add_paragraph(
        "El Cliente podrá auditar prestación con preaviso 15 días y máximo "
        "1 vez/año. Hallazgos confidenciales bilaterales."
    )
    # La NO CONCURRENCIA se negocia caso a caso → la añade Agent 20 como cláusula
    # específica cuando aplique (NO en el esqueleto fijo · decisión Marcos).
    _heading(doc, "8. Incompatibilidad implantador / auditor", 1)
    doc.add_paragraph(
        "FULKRO NO podrá realizar la auditoría externa ENAC sobre los sistemas "
        "objeto del presente contrato (CCN-STIC 802 + ISO/IEC 17065 + IC-01/19). "
        "La auditoría externa corresponde a entidad certificadora acreditada "
        "por ENAC distinta del Consultor."
    )
    # #42/#43 · Agent 20 COMPLEMENTA el esqueleto (no lo sustituye · decisión Marcos).
    if ctx.llm_clauses:
        _add_llm_complement_clauses(doc, ctx.llm_clauses)
    _add_signature_table(doc, [
        ("FULKRO", ctx.fulkro_representante),
        (f"Cliente · {ctx.client_name}", ctx.client_representante),
    ])
    return doc


def _gen_nda_bilateral(ctx: LegalContext, info: LegalTemplateInfo) -> Document:
    doc = Document()
    _add_title_block(doc, info, ctx)
    _heading(doc, "1. Información Confidencial", 1)
    doc.add_paragraph(
        "Toda información intercambiada entre las Partes en el contexto del "
        "proyecto que tenga carácter confidencial, identificada como tal o "
        "que por su naturaleza deba considerarse confidencial."
    )
    _heading(doc, "2. Obligaciones", 1)
    doc.add_paragraph(
        "Las Partes se obligan a no divulgar la Información Confidencial a "
        "terceros sin autorización previa por escrito y a usarla únicamente "
        "para los fines del proyecto. Medidas técnicas y organizativas "
        "razonables para preservar confidencialidad."
    )
    _heading(doc, "3. Excepciones", 1)
    doc.add_paragraph(
        "No se considerará confidencial: información de dominio público, "
        "previamente conocida, desarrollada independientemente, recibida "
        "legítimamente de terceros sin obligación, o requerida por ley."
    )
    _heading(doc, "4. Duración", 1)
    doc.add_paragraph(
        "Vigencia desde firma + 5 años post-finalización del proyecto. Para "
        "información etiquetada como secreto industrial, vigencia indefinida."
    )
    _heading(doc, "5. Jurisdicción", 1)
    doc.add_paragraph("Tribunales de Madrid · Ley aplicable española.")
    _add_signature_table(doc, [
        ("FULKRO", ctx.fulkro_representante),
        (f"Cliente · {ctx.client_name}", ctx.client_representante),
    ])
    return doc


def _gen_encargo_tratamiento_rgpd(ctx: LegalContext, info: LegalTemplateInfo) -> Document:
    doc = Document()
    _add_title_block(doc, info, ctx)
    _heading(doc, "1. Identificación", 1)
    doc.add_paragraph(
        f"Responsable del tratamiento: {ctx.client_name} ({ctx.client_cif}). "
        f"Encargado del tratamiento: {ctx.fulkro_name} ({ctx.fulkro_cif})."
    )
    _heading(doc, "2. Finalidad limitada", 1)
    doc.add_paragraph(
        "El Encargado tratará datos personales únicamente para los fines del "
        "proyecto consultoría ENS · prohibido tratamientos adicionales sin "
        "instrucción documentada del Responsable."
    )
    _heading(doc, "3. Subcontratación", 1)
    doc.add_paragraph(
        "El Encargado no subcontratará total o parcialmente sin autorización "
        "previa por escrito. En caso de subcontratación autorizada, mismas "
        "obligaciones contractuales se imponen al subencargado."
    )
    _heading(doc, "4. Medidas técnicas y organizativas", 1)
    doc.add_paragraph(
        "Cifrado at-rest (AES-256) + tránsito (TLS 1.2+) · MFA admins · "
        "control acceso lógico · trazabilidad accesos · backup cifrado · "
        "destrucción segura. Conformidad ENS Categoría Media + ISO 27001."
    )
    _heading(doc, "5. Devolución / destrucción", 1)
    doc.add_paragraph(
        "Al finalizar el contrato el Encargado devolverá o destruirá los "
        "datos personales (a elección del Responsable) en plazo 30 días. "
        "Certificado de destrucción firmado RSEG."
    )
    _heading(doc, "6. Asistencia AEPD", 1)
    doc.add_paragraph(
        "El Encargado asistirá al Responsable en respuesta a derechos de "
        "interesados (ARSULIPO) y en notificaciones brechas a AEPD ≤ 72h."
    )
    _add_signature_table(doc, [
        (f"Responsable · {ctx.client_name}", ctx.client_representante),
        (f"Encargado · {ctx.fulkro_name}", ctx.fulkro_representante),
        (f"DPO · {ctx.client_name}", ctx.dpo_name),
    ])
    return doc


def _gen_clausulas_terceros_ens(ctx: LegalContext, info: LegalTemplateInfo) -> Document:
    doc = Document()
    _add_title_block(doc, info, ctx)
    _heading(doc, "Identificación tercero", 1)
    doc.add_paragraph(
        f"Tercero: {ctx.provider_name or '(pendiente)'} "
        f"· CIF: {ctx.provider_cif or '(pendiente)'} · Rol: {ctx.provider_role or 'proveedor'}."
    )
    _heading(doc, "1. Conformidad ENS proveedor", 1)
    doc.add_paragraph(
        "El proveedor se obliga a mantener nivel de conformidad ENS "
        "equivalente o superior al del cliente, conforme CCN-STIC 823."
    )
    _heading(doc, "2. Notificación incidentes", 1)
    doc.add_paragraph(
        "Plazos de notificación: 24h alerta · 72h evaluación intermedia · "
        "1 mes informe final. Canales acordados: email cifrado RSEG cliente."
    )
    _heading(doc, "3. Derecho de auditoría", 1)
    doc.add_paragraph(
        "El cliente podrá auditar al proveedor con preaviso 15 días, "
        "máximo 1 vez/año, salvo incidente material que justifique extraordinaria."
    )
    _heading(doc, "4. Subcontratación", 1)
    doc.add_paragraph(
        "Subcontratación requiere autorización previa cliente · subencargado "
        "con mismas obligaciones contractuales (back-to-back)."
    )
    _heading(doc, "5. SLA / SLO", 1)
    doc.add_paragraph(
        "Niveles servicio acordados en anexo SLA · disponibilidad mínima · "
        "MTTR · MTBF · penalizaciones por incumplimiento."
    )
    _heading(doc, "6. Soberanía de datos", 1)
    doc.add_paragraph(
        "Datos personales tratados en territorio UE / España. Transferencias "
        "internacionales requieren cláusulas SCC + DPIA + autorización."
    )
    _heading(doc, "7. Plan de salida", 1)
    doc.add_paragraph(
        "Al finalizar contrato proveedor entregará datos en formato estándar "
        "+ documentación reversibilidad. Plazo migración: mínimo 90 días."
    )
    _add_signature_table(doc, [
        (f"Cliente · {ctx.client_name}", ctx.client_representante),
        (f"Proveedor · {ctx.provider_name or ''}", "(representante)"),
    ])
    return doc


def _gen_compromiso_confidencialidad(ctx: LegalContext, info: LegalTemplateInfo) -> Document:
    doc = Document()
    _add_title_block(doc, info, ctx)
    _heading(doc, "1. Compromiso", 1)
    doc.add_paragraph(
        "El abajo firmante (empleado / subcontratista) se compromete a "
        "guardar confidencialidad de toda información a la que acceda en "
        "el desempeño de sus funciones, conforme política E100 PSI del cliente."
    )
    _heading(doc, "2. Obligaciones específicas", 1)
    doc.add_paragraph(
        "(a) No divulgar a terceros sin autorización escrita. "
        "(b) Usar la información solo para fines profesionales. "
        "(c) No copiar fuera de medios autorizados. "
        "(d) Notificar incidentes que afecten confidencialidad."
    )
    _heading(doc, "3. Sanciones", 1)
    doc.add_paragraph(
        "Incumplimiento puede dar lugar a sanción disciplinaria + "
        "responsabilidad civil + penal (Art. 197-201 CP secretos)."
    )
    _heading(doc, "4. Vigencia post-relación contractual", 1)
    doc.add_paragraph(
        "Las obligaciones de confidencialidad se mantienen 5 años "
        "tras finalizar la relación contractual con el cliente."
    )
    _add_signature_table(doc, [
        ("Empleado / subcontratista", "(nombre + DNI)"),
        (f"Cliente · {ctx.client_name}", ctx.client_representante),
    ])
    return doc


def _gen_dpa(ctx: LegalContext, info: LegalTemplateInfo) -> Document:
    doc = Document()
    _add_title_block(doc, info, ctx)
    _heading(doc, "1. Marco SCC UE 2021/914", 1)
    doc.add_paragraph(
        "El presente DPA incorpora cláusulas tipo aprobadas por la Comisión "
        "Europea (Decisión 2021/914) Módulo 2 (Responsable → Encargado) y "
        "Módulo 3 (Encargado → Subencargado) según corresponda."
    )
    _heading(doc, "2. Medidas suplementarias post-Schrems II", 1)
    doc.add_paragraph(
        "Para transferencias a países sin decisión de adecuación: cifrado "
        "extremo a extremo · gestión claves bajo control UE · evaluación "
        "régimen jurídico destino (Government Access · interferencias TIC)."
    )
    _heading(doc, "3. Evaluación de Impacto en Transferencia (TIA)", 1)
    doc.add_paragraph(
        "Las Partes han realizado TIA documentada · resultado: transferencia "
        "permitida con medidas suplementarias enumeradas en Anexo II."
    )
    _heading(doc, "4. Derechos interesados", 1)
    doc.add_paragraph(
        "Procedimiento ARSULIPO documentado · plazo respuesta ≤ 30 días · "
        "asistencia mutua entre Partes."
    )
    _add_signature_table(doc, [
        (f"Responsable · {ctx.client_name}", ctx.client_representante),
        (f"Encargado · {ctx.provider_name or ctx.fulkro_name}", "(representante)"),
        ("DPO Responsable", ctx.dpo_name),
    ])
    return doc


def _gen_contrato_marco_pentesting(ctx: LegalContext, info: LegalTemplateInfo) -> Document:
    doc = Document()
    _add_title_block(doc, info, ctx)
    _heading(doc, "1. Objeto", 1)
    doc.add_paragraph(
        f"FULKRO subcontrata la realización de pruebas de penetración "
        f"al Partner ({ctx.provider_name or 'pendiente'}) para los "
        f"sistemas del Cliente · alcance acordado en orden trabajo per proyecto."
    )
    _heading(doc, "2. Cláusulas back-to-back", 1)
    doc.add_paragraph(
        "Las obligaciones contractuales FULKRO ↔ Cliente se trasladan al "
        "Partner en términos sustancialmente idénticos: confidencialidad, "
        "RC, plazos, calidad informe, destrucción evidencias."
    )
    _heading(doc, "3. Seguro RC profesional Partner", 1)
    doc.add_paragraph(
        "El Partner mantendrá seguro RC profesional ≥ 1.000.000 € durante "
        "ejecución y posteriores 36 meses · acreditación previa a inicio."
    )
    _heading(doc, "4. Alcance + autorización formal", 1)
    doc.add_paragraph(
        "Cada engagement requiere autorización formal del Cliente · scope "
        "técnico documentado (IPs · URLs · ventana temporal) · firma "
        "responsable IT + RSEG cliente · magic-link autorización FULKRO."
    )
    _heading(doc, "5. Entrega informe + destrucción", 1)
    doc.add_paragraph(
        "El Partner entregará informe técnico + ejecutivo en plazo acordado · "
        "destrucción segura evidencias en 30 días post-entrega · certificado "
        "destrucción firmado por director técnico Partner."
    )
    _add_signature_table(doc, [
        ("FULKRO", ctx.fulkro_representante),
        (f"Partner · {ctx.provider_name or ''}", "(representante)"),
    ])
    return doc


_GENERATORS: dict[str, Callable[[LegalContext, LegalTemplateInfo], Document]] = {
    "contrato_prestacion_servicios": _gen_contrato_prestacion_servicios,
    "nda_bilateral": _gen_nda_bilateral,
    "encargo_tratamiento_rgpd_art28": _gen_encargo_tratamiento_rgpd,
    "clausulas_terceros_ens": _gen_clausulas_terceros_ens,
    "compromiso_confidencialidad_empleados": _gen_compromiso_confidencialidad,
    "dpa_data_processing_agreement": _gen_dpa,
    "contrato_marco_pentesting": _gen_contrato_marco_pentesting,
}


def generate_legal_docx(slug: str, ctx: LegalContext) -> io.BytesIO:
    """Genera DOCX para el slug pedido (lanza KeyError si no existe)."""
    info = get_legal_template(slug)
    if slug not in _GENERATORS:
        raise KeyError(f"Generator no implementado para slug '{slug}'")
    doc = _GENERATORS[slug](ctx, info)
    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio


async def build_contract_legal_context(
    db: AsyncSession, contract: Any,
) -> LegalContext:
    """#42 · LegalContext enriquecido para renderizar el contrato comercial
    redactado (C-100) desde un Contract: cliente/emisor (build_legal_context ·
    #9/#44) + pricing/hitos (parametros_xyzpr) + alcance_snapshot (#10 B1) +
    cláusulas Agent 20 (complemento)."""
    ctx = await build_legal_context(db, contract.project_id)
    params = contract.parametros_xyzpr or {}
    pricing = params.get("pricing") or {}
    ctx.categoria = pricing.get("categoria")
    ctx.importe_total = pricing.get("total")
    ctx.hitos = pricing.get("hitos") or []
    ctx.alcance = contract.alcance_snapshot
    ctx.llm_clauses = params.get("llm_clauses")
    return ctx


async def render_canonical_contract_docx(
    db: AsyncSession, contract: Any,
) -> bytes:
    """#42 · DOCX canónico REDACTADO del contrato comercial: las 8 cláusulas del
    esqueleto legal + tabla de hitos (§2) + alcance comercial (§1) + emisor/cliente
    con datos fiscales en el bloque de partes + complemento Agent 20. Sustituye el
    volcado de parámetros (``ContractService.generate_docx``)."""
    ctx = await build_contract_legal_context(db, contract)
    return generate_legal_docx("contrato_prestacion_servicios", ctx).getvalue()
