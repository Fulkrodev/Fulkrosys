"""Draft audit report PDF generator · CLUSTER 3 Phase C4.1.

Generates preliminary audit report PDF aggregating Phase C1 annotations,
Phase C2 clarifications, Phase C3 DdA-evidence gap matrix, + integrity status
(signatures + audit log hash chain). Signs PDF sha256 con Ed25519 (M05 reuse).

EMPIRICAL ADAPTATION (Phase C4.0 audit · OPS-052 honest):
- Architect brief mencionó weasyprint (HTML→PDF) · empirical check: weasyprint
  NO instalado · reportlab 4.4.10 INSTALLED canonical Python PDF library.
- ADAPTATION: usar reportlab platypus (flow-based · data-driven · UTF-8 native).
  PDFRenderer (docxtpl + LibreOffice) canonical pattern para design-heavy
  Word-editable templates · audit report es data-heavy + tabular · reportlab fit.
- Jinja2 utilizado para HTML preview endpoint (browser inline iframe display) ·
  reportlab para binary PDF download.
- Future-X: si Marcos prefiere DOCX-editable template + LibreOffice headless ·
  migration straightforward · template path swap.

REUSABLE para Sesión 3B-2B.10 simulacro Pre-ENAC engine target:
- Pure service · NO HTTP coupling · returns DraftReportBytes dataclass
- Reusa pattern Cluster 1 dossier signed (sign_payload + get_public_key_pem)
- Reusa Phase C1 annotations · C2 clarifications · C3 gap matrix services
"""
from __future__ import annotations

import hashlib
import io
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m09_audit_prep.dda_evidence_gap_service import (
    DdaEvidenceGapMatrix,
    GapDetectionOptions,
    GapStatus,
    compute_dda_evidence_gaps,
)


logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════
# Options + recommendation
# ════════════════════════════════════════════════════════════════════════


class Recommendation:
    APROBAR = "APROBAR"
    APROBAR_CON_CONDICIONES = "APROBAR_CON_CONDICIONES"
    NO_APROBAR = "NO_APROBAR"

    VALUES = ("APROBAR", "APROBAR_CON_CONDICIONES", "NO_APROBAR")


@dataclass(frozen=True)
class DraftReportOptions:
    """Configurable inputs for draft report generation."""

    auditor_opinion_text: str | None = None
    recommendation: str | None = None  # If None · auto-derive per gap matrix
    gap_options: Optional[GapDetectionOptions] = None
    auditor_name: str | None = None
    audit_period_start: str | None = None  # ISO date
    audit_period_end: str | None = None    # ISO date


@dataclass
class DraftReportBytes:
    """Result · PDF bytes + signature metadata."""

    pdf_bytes: bytes
    pdf_sha256: str
    signature_hex: str
    public_key_pem: str
    signed_at: str
    recommendation: str
    sections_count: int


# ════════════════════════════════════════════════════════════════════════
# Data aggregation helpers (pure read · NO side effects)
# ════════════════════════════════════════════════════════════════════════


async def _gather_project_metadata(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict[str, Any]:
    row = (await db.execute(sa_text(
        "SELECT p.id, p.nombre, p.categoria_objetivo, p.fase, "
        "p.lifecycle_state, p.certified_at, p.audit_passed_at, "
        "p.audit_result, c.id, c.nombre, c.cif, "
        "c.primary_color, c.footer_text "
        "FROM projects p "
        "JOIN clients c ON c.id = p.client_id "
        "WHERE p.id = :pid"
    ), {"pid": str(project_id)})).first()
    if row is None:
        raise ValueError(f"Project {project_id} not found")
    return {
        "project_id": str(row[0]),
        "project_name": row[1] or "Proyecto",
        "categoria": (row[2] or "MEDIA").upper(),
        "fase": row[3],
        "lifecycle_state": row[4],
        "certified_at": row[5].isoformat() if row[5] else None,
        "audit_passed_at": row[6].isoformat() if row[6] else None,
        "audit_result": row[7],
        "client_id": str(row[8]),
        "client_name": row[9] or "",
        "cif": row[10] or "",
        "razon_social": row[9] or "Cliente",
        "primary_color": row[11] or "",
        "footer_text": row[12] or "",
    }


async def _gather_annotations(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict[str, Any]:
    rows = (await db.execute(sa_text(
        "SELECT id, target_type, target_id, annotation_text, flag_severity, "
        "status, admin_response, admin_responded_at, admin_responded_by, "
        "created_at "
        "FROM auditor_annotations "
        "WHERE project_id = :pid AND deleted_at IS NULL "
        "ORDER BY flag_severity, created_at"
    ), {"pid": str(project_id)})).all()
    items: list[dict[str, Any]] = []
    by_severity: dict[str, int] = {
        "critical": 0, "concern": 0, "warning": 0, "info": 0,
    }
    resolved = 0
    pending = 0
    for r in rows:
        sev = r[4]
        by_severity[sev] = by_severity.get(sev, 0) + 1
        if r[5] in ("resolved", "dismissed", "admin_reviewed"):
            resolved += 1
        else:
            pending += 1
        items.append({
            "id": str(r[0]),
            "target_type": r[1],
            "target_id": str(r[2]),
            "annotation_text": r[3],
            "flag_severity": sev,
            "status": r[5],
            "admin_response": r[6],
            "admin_responded_at": r[7].isoformat() if r[7] else None,
            "admin_responded_by": r[8],
            "created_at": r[9].isoformat() if r[9] else None,
        })
    return {
        "total": len(items),
        "resolved": resolved,
        "pending": pending,
        "by_severity": by_severity,
        "items": items,
    }


async def _gather_clarifications(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict[str, Any]:
    rows = (await db.execute(sa_text(
        "SELECT id, question_text, linked_target_type, priority, status, "
        "admin_response, admin_responded_at, admin_responded_by, created_at "
        "FROM auditor_clarification_requests "
        "WHERE project_id = :pid AND deleted_at IS NULL "
        "ORDER BY priority, created_at"
    ), {"pid": str(project_id)})).all()
    items: list[dict[str, Any]] = []
    responded = 0
    open_count = 0
    by_priority: dict[str, int] = {
        "urgent": 0, "high": 0, "normal": 0, "low": 0,
    }
    for r in rows:
        prio = r[3]
        by_priority[prio] = by_priority.get(prio, 0) + 1
        if r[4] in ("responded", "closed"):
            responded += 1
        else:
            open_count += 1
        items.append({
            "id": str(r[0]),
            "question_text": r[1],
            "linked_target_type": r[2],
            "priority": prio,
            "status": r[4],
            "admin_response": r[5],
            "admin_responded_at": r[6].isoformat() if r[6] else None,
            "admin_responded_by": r[7],
            "created_at": r[8].isoformat() if r[8] else None,
        })
    return {
        "total": len(items),
        "responded": responded,
        "open": open_count,
        "by_priority": by_priority,
        "items": items,
    }


async def _gather_integrity_status(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict[str, Any]:
    """Check hash chain integrity + count audit_log events for project."""
    audit_count_row = (await db.execute(sa_text(
        "SELECT count(*), min(timestamp), max(timestamp) "
        "FROM audit_log WHERE project_id = :pid"
    ), {"pid": str(project_id)})).first()
    audit_count = audit_count_row[0] if audit_count_row else 0
    first_ts = audit_count_row[1] if audit_count_row else None
    last_ts = audit_count_row[2] if audit_count_row else None

    # Verify hash chain via R6 trigger function
    chain_status = "unknown"
    try:
        verify_row = (await db.execute(sa_text(
            "SELECT fn_audit_log_verify_chain() AS valid"
        ))).first()
        if verify_row is not None:
            chain_status = "valid" if verify_row[0] else "invalid"
    except Exception:
        logger.exception(
            "Hash chain verify failed (best-effort) · project_id=%s",
            project_id,
        )
        chain_status = "verify_unavailable"

    # Signatures status (DdA + dossier + E-041)
    dda_signed_row = (await db.execute(sa_text(
        "SELECT created_at FROM dda_project_signatures "
        "WHERE project_id = :pid LIMIT 1"
    ), {"pid": str(project_id)})).first()
    dossier_runs_row = (await db.execute(sa_text(
        "SELECT count(*) FROM audit_preparation_runs "
        "WHERE project_id = :pid AND dossier_generated_at IS NOT NULL "
        "AND deleted_at IS NULL"
    ), {"pid": str(project_id)})).first()
    declarations_row = (await db.execute(sa_text(
        "SELECT count(*) FROM basic_declarations "
        "WHERE project_id = :pid AND signed_at IS NOT NULL"
    ), {"pid": str(project_id)})).first()

    return {
        "audit_log_events": audit_count,
        "audit_log_first_at": first_ts.isoformat() if first_ts else None,
        "audit_log_last_at": last_ts.isoformat() if last_ts else None,
        "hash_chain_status": chain_status,
        "dda_signed": dda_signed_row is not None,
        "dda_signed_at": (
            dda_signed_row[0].isoformat() if dda_signed_row else None
        ),
        "signed_dossiers_count": (
            dossier_runs_row[0] if dossier_runs_row else 0
        ),
        "signed_e041_count": (
            declarations_row[0] if declarations_row else 0
        ),
    }


def _derive_recommendation(
    matrix: DdaEvidenceGapMatrix,
    annotations_pending: int,
) -> str:
    """Default recommendation per gap + annotations pending."""
    if matrix.severity_summary.critical_missing > 0:
        return Recommendation.NO_APROBAR
    if matrix.total_missing > 0 or matrix.total_partial > 0:
        return Recommendation.APROBAR_CON_CONDICIONES
    if annotations_pending > 0:
        return Recommendation.APROBAR_CON_CONDICIONES
    return Recommendation.APROBAR


# ════════════════════════════════════════════════════════════════════════
# Context builder (cross HTML + PDF rendering)
# ════════════════════════════════════════════════════════════════════════


async def build_report_context(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    options: Optional[DraftReportOptions] = None,
) -> dict[str, Any]:
    opts = options or DraftReportOptions()
    project = await _gather_project_metadata(db, project_id)
    annotations = await _gather_annotations(db, project_id)
    clarifications = await _gather_clarifications(db, project_id)
    matrix = await compute_dda_evidence_gaps(
        db, project_id, options=opts.gap_options,
    )
    integrity = await _gather_integrity_status(db, project_id)

    recommendation = opts.recommendation or _derive_recommendation(
        matrix, annotations["pending"],
    )
    if recommendation not in Recommendation.VALUES:
        recommendation = Recommendation.APROBAR_CON_CONDICIONES

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project": project,
        "annotations": annotations,
        "clarifications": clarifications,
        "matrix": matrix.to_dict(),
        "integrity": integrity,
        "recommendation": recommendation,
        "auditor_opinion_text": (
            opts.auditor_opinion_text
            or "[Pendiente · auditor ENAC redactará opinión final post-revisión]"
        ),
        "auditor_name": (
            opts.auditor_name or "[Pendiente · auditor ENAC firmará versión final]"
        ),
        "audit_period_start": opts.audit_period_start,
        "audit_period_end": opts.audit_period_end,
    }


# ════════════════════════════════════════════════════════════════════════
# HTML preview rendering (Jinja2 · for inline iframe display)
# ════════════════════════════════════════════════════════════════════════


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Borrador informe auditoría · {{ project.project_name }}</title>
<style>
body { font-family: Arial, Helvetica, sans-serif; color: #222; max-width: 900px;
  margin: 20px auto; padding: 0 20px; line-height: 1.4; font-size: 13px; }
h1 { color: #1a1a1a; border-bottom: 3px solid {{ project.primary_color or '#6c63ff' }};
  padding-bottom: 6px; }
h2 { color: #333; border-left: 4px solid {{ project.primary_color or '#6c63ff' }};
  padding-left: 8px; margin-top: 18px; }
.disclaimer { background: #fff8e1; border: 1px solid #ffb74d; padding: 8px;
  border-radius: 4px; font-size: 12px; margin-bottom: 16px; }
.severity-badge { display: inline-block; padding: 2px 6px; border-radius: 3px;
  font-size: 11px; font-weight: bold; margin-right: 4px; }
.sev-critical { background: #ffcdd2; color: #b71c1c; }
.sev-high, .sev-concern { background: #ffe0b2; color: #e65100; }
.sev-warning, .sev-medium { background: #fff9c4; color: #f57f17; }
.sev-info, .sev-low { background: #e1f5fe; color: #01579b; }
.stat { display: inline-block; margin-right: 18px; }
.stat-value { font-size: 18px; font-weight: bold; }
.stat-label { font-size: 11px; color: #666; text-transform: uppercase; }
table { width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 12px; }
th, td { border: 1px solid #ddd; padding: 4px 6px; text-align: left; }
th { background: #f5f5f5; font-weight: bold; }
.status-covered { background: #c8e6c9; }
.status-partial { background: #fff59d; }
.status-missing { background: #ffcdd2; }
.status-not_applicable { background: #eeeeee; color: #999; }
.recommendation { padding: 12px; border-radius: 6px; font-size: 16px;
  font-weight: bold; text-align: center; margin: 12px 0; }
.rec-aprobar { background: #c8e6c9; color: #1b5e20; }
.rec-aprobar-con-condiciones { background: #fff59d; color: #f57f17; }
.rec-no-aprobar { background: #ffcdd2; color: #b71c1c; }
.footer { margin-top: 32px; padding-top: 12px; border-top: 1px solid #ccc;
  font-size: 10px; color: #888; }
</style>
</head>
<body>
<h1>Borrador · Informe preliminar de auditoría ENS</h1>
<div class="disclaimer">
  <strong>BORRADOR</strong> · Documento generado automáticamente por la plataforma FULKRO.
  No constituye dictamen final. Pendiente firma del auditor ENAC responsable.
</div>

<h2>1. Portada</h2>
<p><strong>Proyecto:</strong> {{ project.project_name }}</p>
<p><strong>Cliente:</strong> {{ project.razon_social }} ({{ project.cif }})</p>
<p><strong>Categoría ENS:</strong> {{ project.categoria }}</p>
<p><strong>Fecha de emisión:</strong> {{ generated_at }}</p>

<h2>2. Alcance y metodología</h2>
<p>Auditoría preliminar del sistema bajo el alcance del proyecto
{{ project.project_name }}, categoría ENS {{ project.categoria }} según RD 311/2022.</p>
<p>Periodo auditado: {{ audit_period_start or '[No especificado]' }} a
{{ audit_period_end or '[No especificado]' }}.</p>
<p>Metodología: revisión documental + análisis de evidencias + entrevistas vía
portal del auditor (anotaciones + solicitudes de aclaración).</p>
<p>Normas de referencia: RD 311/2022 · CCN-STIC-808 · criterios ENAC.</p>

<h2>3. Resumen ejecutivo</h2>
<div>
  <div class="stat"><div class="stat-value">{{ matrix.total_applicable }}</div>
    <div class="stat-label">Medidas aplicables</div></div>
  <div class="stat"><div class="stat-value">{{ matrix.total_covered }}</div>
    <div class="stat-label">Cubiertas</div></div>
  <div class="stat"><div class="stat-value">{{ matrix.total_partial }}</div>
    <div class="stat-label">Parciales</div></div>
  <div class="stat"><div class="stat-value">{{ matrix.total_missing }}</div>
    <div class="stat-label">Sin evidencia</div></div>
  <div class="stat"><div class="stat-value">{{ matrix.coverage_pct }}%</div>
    <div class="stat-label">Cobertura</div></div>
</div>
<p style="margin-top:8px;">Hallazgos por severidad:
  <span class="severity-badge sev-critical">Críticos: {{ matrix.severity_summary.critical_missing }}</span>
  <span class="severity-badge sev-high">Altos: {{ matrix.severity_summary.high_partial }}</span>
  <span class="severity-badge sev-medium">Medios: {{ matrix.severity_summary.medium_total }}</span>
  <span class="severity-badge sev-low">Bajos: {{ matrix.severity_summary.low_total }}</span>
  · <span style="font-weight:bold;">{{ matrix.severity_summary.recoverable }}</span> recuperables.
</p>

<div class="recommendation
  {% if recommendation == 'APROBAR' %}rec-aprobar
  {% elif recommendation == 'APROBAR_CON_CONDICIONES' %}rec-aprobar-con-condiciones
  {% else %}rec-no-aprobar{% endif %}">
  Recomendación preliminar: {{ recommendation.replace('_', ' ') }}
</div>

<h2>4. Hallazgos (anotaciones del auditor)</h2>
<p>{{ annotations.total }} anotaciones · {{ annotations.resolved }} resueltas ·
{{ annotations.pending }} pendientes</p>
{% if annotations["items"] %}
<table>
  <thead><tr><th>Severidad</th><th>Objetivo</th><th>Anotación</th>
    <th>Estado</th><th>Respuesta admin</th></tr></thead>
  <tbody>
  {% for a in annotations["items"][:20] %}
  <tr>
    <td><span class="severity-badge sev-{{ a.flag_severity }}">{{ a.flag_severity }}</span></td>
    <td>{{ a.target_type }}</td>
    <td>{{ a.annotation_text[:200] }}{% if a.annotation_text|length > 200 %}…{% endif %}</td>
    <td>{{ a.status }}</td>
    <td>{{ (a.admin_response or '—')[:150] }}{% if a.admin_response and a.admin_response|length > 150 %}…{% endif %}</td>
  </tr>
  {% endfor %}
  </tbody>
</table>
{% if annotations["items"]|length > 20 %}
<p style="font-size:11px;color:#666;">… y {{ annotations["items"]|length - 20 }} anotaciones adicionales (truncadas en preview).</p>
{% endif %}
{% else %}
<p>Sin anotaciones registradas para este proyecto.</p>
{% endif %}

<h2>5. Aclaraciones solicitadas</h2>
<p>{{ clarifications.total }} solicitudes · {{ clarifications.responded }} respondidas ·
{{ clarifications.open }} pendientes</p>
{% if clarifications["items"] %}
{% for c in clarifications["items"][:10] %}
<div style="border:1px solid #ddd; padding:6px; margin:4px 0;">
  <p><span class="severity-badge sev-{{ c.priority }}">{{ c.priority }}</span>
    <strong>P:</strong> {{ c.question_text[:300] }}{% if c.question_text|length > 300 %}…{% endif %}</p>
  {% if c.admin_response %}
  <p style="margin-top:4px;color:#0277bd;"><strong>R:</strong> {{ c.admin_response[:300] }}{% if c.admin_response|length > 300 %}…{% endif %}</p>
  {% else %}
  <p style="margin-top:4px;color:#999;font-style:italic;">Sin respuesta del admin todavía.</p>
  {% endif %}
</div>
{% endfor %}
{% else %}
<p>Sin solicitudes de aclaración para este proyecto.</p>
{% endif %}

<h2>6. Cobertura DdA · Evidencias</h2>
<p>Cobertura global: <strong>{{ matrix.coverage_pct }}%</strong>
  ({{ matrix.total_covered }}/{{ matrix.total_applicable }})</p>
<p>Categoría {{ matrix.categoria }} · {{ matrix.total_not_applicable }} medidas
  no aplicables (filtradas por categoría).</p>
<table>
  <thead><tr><th>Código</th><th>Familia</th><th>Estado</th>
    <th>Evidencias</th><th>Última actualización</th><th>Motivo gap</th></tr></thead>
  <tbody>
  {% for m in matrix["medidas"] if m.status != 'not_applicable' %}
  <tr class="status-{{ m.status }}">
    <td><code>{{ m.medida_code }}</code></td>
    <td>{{ m.family or '—' }}</td>
    <td>{{ m.status }}</td>
    <td>{{ m.evidence_count }}/{{ m.min_required }}</td>
    <td>{{ m.last_uploaded_at[:10] if m.last_uploaded_at else '—' }}</td>
    <td>{{ m.gap_reason or '—' }}</td>
  </tr>
  {% endfor %}
  </tbody>
</table>

<h2>7. Integridad del expediente</h2>
<p>Eventos audit log: {{ integrity.audit_log_events }} desde
  {{ integrity.audit_log_first_at or '—' }} hasta {{ integrity.audit_log_last_at or '—' }}.</p>
<p>Hash chain R6 (inmutabilidad): <strong>{{ integrity.hash_chain_status }}</strong></p>
<p>DdA firmada Ed25519: {{ 'Sí · ' + integrity.dda_signed_at if integrity.dda_signed else 'No' }}</p>
<p>Dossiers firmados generados: {{ integrity.signed_dossiers_count }}</p>
<p>E-041 declaraciones firmadas: {{ integrity.signed_e041_count }}</p>

<h2>8. Opinión preliminar del auditor</h2>
<p>{{ auditor_opinion_text }}</p>
<p><strong>Auditor:</strong> {{ auditor_name }}</p>
<p style="font-style:italic;color:#666;">Este borrador NO constituye dictamen final · pendiente firma del auditor ENAC.</p>

<div class="footer">
  Generado por FULKRO Audit Prep Motor · {{ generated_at }} ·
  Documento firmado Ed25519 con clave M05 (verificación independiente disponible).
  {% if project.footer_text %}<br/>{{ project.footer_text }}{% endif %}
</div>
</body>
</html>
"""


def render_report_html(context: dict[str, Any]) -> str:
    """Renderiza el HTML preview · Jinja2 · UTF-8 Spanish-friendly."""
    import jinja2
    env = jinja2.Environment(autoescape=True)
    tpl = env.from_string(_HTML_TEMPLATE)
    return tpl.render(**context)


# ════════════════════════════════════════════════════════════════════════
# PDF rendering (reportlab platypus · Python-only · UTF-8 native)
# ════════════════════════════════════════════════════════════════════════


def _build_pdf_bytes(context: dict[str, Any]) -> bytes:
    """Render PDF using reportlab platypus · returns bytes."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        PageBreak,
    )
    from reportlab.lib.enums import TA_CENTER

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title=f"Borrador audit · {context['project']['project_name']}",
        author="FULKRO Audit Prep Motor",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleC", parent=styles["Title"], fontSize=16,
        textColor=colors.HexColor("#1a1a1a"),
    )
    h2_style = ParagraphStyle(
        "H2C", parent=styles["Heading2"], fontSize=12,
        textColor=colors.HexColor("#333333"),
        borderColor=colors.HexColor("#6c63ff"), borderPadding=4,
        leftIndent=4, spaceAfter=4,
    )
    body = styles["BodyText"]
    body.fontSize = 9
    body.leading = 11
    disclaimer = ParagraphStyle(
        "Disclaimer", parent=body, fontSize=9, textColor=colors.HexColor("#e65100"),
        backColor=colors.HexColor("#fff8e1"), borderPadding=6,
    )
    rec_style = ParagraphStyle(
        "Rec", parent=body, fontSize=12, alignment=TA_CENTER,
        textColor=colors.white, backColor=colors.HexColor("#f57f17"),
        borderPadding=8, spaceAfter=8, spaceBefore=8,
    )

    project = context["project"]
    matrix = context["matrix"]
    annotations = context["annotations"]
    clarifications = context["clarifications"]
    integrity = context["integrity"]
    recommendation = context["recommendation"]

    rec_color = {
        "APROBAR": colors.HexColor("#1b5e20"),
        "APROBAR_CON_CONDICIONES": colors.HexColor("#f57f17"),
        "NO_APROBAR": colors.HexColor("#b71c1c"),
    }.get(recommendation, colors.HexColor("#666"))

    story: list = []

    story.append(Paragraph(
        "Borrador · Informe preliminar de auditoría ENS", title_style,
    ))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "<b>BORRADOR</b> · Documento generado automáticamente por la "
        "plataforma FULKRO. No constituye dictamen final. Pendiente firma "
        "del auditor ENAC responsable.",
        disclaimer,
    ))
    story.append(Spacer(1, 6))

    # 1. Portada
    story.append(Paragraph("1. Portada", h2_style))
    cover_data = [
        ["Proyecto:", project["project_name"]],
        ["Cliente:", f"{project['razon_social']} · CIF {project['cif']}"],
        ["Categoría ENS:", project["categoria"]],
        ["Fecha emisión:", context["generated_at"]],
    ]
    cover_t = Table(cover_data, colWidths=[35 * mm, 130 * mm])
    cover_t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f5f5f5")),
    ]))
    story.append(cover_t)
    story.append(Spacer(1, 6))

    # 2. Alcance
    story.append(Paragraph("2. Alcance y metodología", h2_style))
    period_start = context.get("audit_period_start") or "[No especificado]"
    period_end = context.get("audit_period_end") or "[No especificado]"
    story.append(Paragraph(
        f"Auditoría preliminar del sistema bajo el alcance del proyecto "
        f"<b>{project['project_name']}</b>, categoría ENS "
        f"<b>{project['categoria']}</b> según RD 311/2022.",
        body,
    ))
    story.append(Paragraph(
        f"Periodo auditado: {period_start} a {period_end}.", body,
    ))
    story.append(Paragraph(
        "Metodología: revisión documental + análisis de evidencias + "
        "entrevistas vía portal del auditor (anotaciones + solicitudes de "
        "aclaración).",
        body,
    ))
    story.append(Paragraph(
        "Normas de referencia: RD 311/2022 · CCN-STIC-808 · criterios ENAC.",
        body,
    ))
    story.append(Spacer(1, 6))

    # 3. Resumen ejecutivo
    story.append(Paragraph("3. Resumen ejecutivo", h2_style))
    summary_data = [
        ["Aplicables", "Cubiertas", "Parciales", "Sin evidencia",
         "N/A", "Cobertura"],
        [
            str(matrix["total_applicable"]),
            str(matrix["total_covered"]),
            str(matrix["total_partial"]),
            str(matrix["total_missing"]),
            str(matrix["total_not_applicable"]),
            f"{matrix['coverage_pct']:.1f}%",
        ],
    ]
    summary_t = Table(summary_data, colWidths=[27 * mm] * 6)
    summary_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f5f5f5")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#ccc")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
    ]))
    story.append(summary_t)
    story.append(Spacer(1, 4))
    sev = matrix["severity_summary"]
    story.append(Paragraph(
        f"Severidad: <b>Críticos</b> {sev['critical_missing']} · "
        f"<b>Altos</b> {sev['high_partial']} · <b>Medios</b> "
        f"{sev['medium_total']} · <b>Bajos</b> {sev['low_total']} · "
        f"<b>{sev['recoverable']}</b> recuperables.",
        body,
    ))

    rec_para = ParagraphStyle(
        "RecLocal", parent=rec_style, backColor=rec_color, borderColor=rec_color,
    )
    story.append(Paragraph(
        f"Recomendación preliminar: {recommendation.replace('_', ' ')}",
        rec_para,
    ))

    # 4. Anotaciones
    story.append(Paragraph("4. Hallazgos (anotaciones del auditor)", h2_style))
    story.append(Paragraph(
        f"{annotations['total']} anotaciones · "
        f"{annotations['resolved']} resueltas · "
        f"{annotations['pending']} pendientes",
        body,
    ))
    if annotations["items"]:
        ann_data = [["Severidad", "Objetivo", "Texto", "Estado"]]
        for a in annotations["items"][:20]:
            text_snippet = a["annotation_text"][:120]
            if len(a["annotation_text"]) > 120:
                text_snippet += "…"
            ann_data.append([
                a["flag_severity"], a["target_type"],
                text_snippet, a["status"],
            ])
        ann_t = Table(
            ann_data,
            colWidths=[22 * mm, 28 * mm, 90 * mm, 26 * mm],
        )
        ann_t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f5f5f5")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#ccc")),
        ]))
        story.append(ann_t)
    else:
        story.append(Paragraph(
            "Sin anotaciones registradas para este proyecto.", body,
        ))
    story.append(Spacer(1, 6))

    # 5. Clarifications
    story.append(Paragraph("5. Aclaraciones solicitadas", h2_style))
    story.append(Paragraph(
        f"{clarifications['total']} solicitudes · "
        f"{clarifications['responded']} respondidas · "
        f"{clarifications['open']} pendientes",
        body,
    ))
    if not clarifications["items"]:
        story.append(Paragraph(
            "Sin solicitudes de aclaración para este proyecto.", body,
        ))
    else:
        for c in clarifications["items"][:10]:
            q_snippet = c["question_text"][:200]
            if len(c["question_text"]) > 200:
                q_snippet += "…"
            story.append(Paragraph(
                f"<b>[{c['priority']}] P:</b> {q_snippet}", body,
            ))
            if c["admin_response"]:
                r_snippet = c["admin_response"][:200]
                if len(c["admin_response"]) > 200:
                    r_snippet += "…"
                story.append(Paragraph(
                    f'<font color="#0277bd"><b>R:</b> {r_snippet}</font>', body,
                ))
            else:
                story.append(Paragraph(
                    '<font color="#999">Sin respuesta del admin todavía.</font>',
                    body,
                ))
            story.append(Spacer(1, 3))

    story.append(PageBreak())

    # 6. DdA-evidence matrix
    story.append(Paragraph("6. Cobertura DdA · Evidencias", h2_style))
    story.append(Paragraph(
        f"Cobertura global: <b>{matrix['coverage_pct']}%</b> "
        f"({matrix['total_covered']}/{matrix['total_applicable']})",
        body,
    ))
    matrix_data = [["Código", "Familia", "Estado", "Ev.", "Última", "Motivo"]]
    for m in matrix["medidas"]:
        if m["status"] == "not_applicable":
            continue
        last_short = (m["last_uploaded_at"] or "—")[:10]
        gap_short = (m["gap_reason"] or "—")[:60]
        matrix_data.append([
            m["medida_code"], m["family"] or "—",
            m["status"], f"{m['evidence_count']}/{m['min_required']}",
            last_short, gap_short,
        ])
    matrix_t = Table(
        matrix_data,
        colWidths=[22 * mm, 18 * mm, 22 * mm, 14 * mm, 22 * mm, 65 * mm],
        repeatRows=1,
    )
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f5f5f5")),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#ccc")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]
    # Color rows per status
    for i, row in enumerate(matrix_data[1:], start=1):
        status = row[2]
        bg = {
            "covered": colors.HexColor("#c8e6c9"),
            "partial": colors.HexColor("#fff59d"),
            "missing": colors.HexColor("#ffcdd2"),
        }.get(status)
        if bg is not None:
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), bg))
    matrix_t.setStyle(TableStyle(style_cmds))
    story.append(matrix_t)
    story.append(Spacer(1, 6))

    # 7. Integrity
    story.append(Paragraph("7. Integridad del expediente", h2_style))
    integrity_data = [
        ["Eventos audit log:", str(integrity["audit_log_events"])],
        ["Hash chain R6:", integrity["hash_chain_status"]],
        ["DdA firmada Ed25519:",
         "Sí · " + (integrity["dda_signed_at"] or "")
         if integrity["dda_signed"] else "No"],
        ["Dossiers firmados:", str(integrity["signed_dossiers_count"])],
        ["E-041 declaraciones firmadas:", str(integrity["signed_e041_count"])],
    ]
    integrity_t = Table(integrity_data, colWidths=[60 * mm, 105 * mm])
    integrity_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f5f5f5")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#ccc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(integrity_t)
    story.append(Spacer(1, 6))

    # 8. Opinion
    story.append(Paragraph("8. Opinión preliminar del auditor", h2_style))
    story.append(Paragraph(context["auditor_opinion_text"], body))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"<b>Auditor:</b> {context['auditor_name']}", body))
    story.append(Paragraph(
        '<font color="#666"><i>Este borrador NO constituye dictamen final · '
        'pendiente firma del auditor ENAC.</i></font>', body,
    ))
    story.append(Spacer(1, 6))

    # 9. Footer
    story.append(Paragraph("9. Firma + metadatos", h2_style))
    story.append(Paragraph(
        f"Generado por FULKRO Audit Prep Motor · {context['generated_at']}. "
        "Documento firmado Ed25519 con clave M05 (verificación independiente "
        "disponible vía manifest).", body,
    ))
    if project.get("footer_text"):
        story.append(Paragraph(
            f'<font color="#888">{project["footer_text"]}</font>', body,
        ))

    doc.build(story)
    return buf.getvalue()


# ════════════════════════════════════════════════════════════════════════
# Public API · generate_draft_audit_report (reusable)
# ════════════════════════════════════════════════════════════════════════


async def generate_draft_audit_report(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    options: Optional[DraftReportOptions] = None,
) -> DraftReportBytes:
    """Generate draft audit report PDF + Ed25519 signature.

    Reusable cross-context (Sesión 3B-2B.10 simulacro Pre-ENAC engine target).
    Pure: NO side effects DB · returns bytes + signature metadata.
    """
    from backend.app.motors.m05_signing.keypair import (
        get_public_key_pem,
        sign_payload,
    )

    context = await build_report_context(db, project_id, options=options)
    pdf_bytes = _build_pdf_bytes(context)

    pdf_sha256 = hashlib.sha256(pdf_bytes).hexdigest()
    signature = sign_payload(pdf_sha256.encode("utf-8"))
    signed_at = datetime.now(timezone.utc).isoformat()

    return DraftReportBytes(
        pdf_bytes=pdf_bytes,
        pdf_sha256=pdf_sha256,
        signature_hex=signature.hex(),
        public_key_pem=get_public_key_pem(),
        signed_at=signed_at,
        recommendation=context["recommendation"],
        sections_count=9,
    )
