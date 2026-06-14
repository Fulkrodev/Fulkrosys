"""Dossier generator (M9-B).

Genera el ZIP final de auditoria ENS con la estructura de §2.15 / §3.7.5:
14 carpetas tematicas + Matriz Cruzada 99 + MANIFEST con hashes.
"""
from __future__ import annotations

import hashlib
import io
import json
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy import text as _sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit_prep import AuditPreparationRun
from backend.app.models.documents import Document, Evidence
from backend.app.motors.m08_verification.integrations.m9_audit_prep import (
    collect_findings_for_dossier,
)

from . import matriz_99 as matriz_mod
from .checklist_service import get_run

# Referencia cruzada a IDMS (M24) — ambas estructuras tienen 15 carpetas alineadas
# por código (00-13 + 99). M9 usa MAYÚSCULAS para entrega al auditor ENAC;
# M24 usa Capitalizado para el Drive del cliente. 00 y 99 divergen intencionalmente:
# M9:  00=INDICE / 99=MATRIZ_CRUZADA (específicos del dossier)
# M24: 00=Contractual / 99=Misc (específicos del Drive)
from backend.app.motors.m24_idms.idms_service import STANDARD_FOLDERS as IDMS_STANDARD_FOLDERS  # noqa: F401


# Estructura de carpetas para auditoria ENAC — 14 tematicas + 99 matriz
# (spec interno de Marcos §2.15). Nomenclatura fija: MAYUSCULAS + guion
# bajo.
DOSSIER_STRUCTURE: list[dict] = [
    {"folder": "00_INDICE", "description": "Indice maestro navegable + resumen ejecutivo"},
    {"folder": "01_GOBIERNO", "description": "Roles, responsabilidades, organigrama, politica general"},
    {"folder": "02_CATEGORIZACION", "description": "Acta E-012 + justificacion categoria ENS"},
    {"folder": "03_ANALISIS_RIESGOS", "description": "Analisis de riesgos MAGERIT + plan de tratamiento"},
    {"folder": "04_DECLARACION_APLICABILIDAD", "description": "Informe Final de Adecuacion E-040 (incluye la Declaracion de Aplicabilidad / SoA como Anexo II) firmado por RSEG"},
    {"folder": "05_PLAN_ADECUACION", "description": "Plan de adecuacion E-020..E-030 + cronograma"},
    {"folder": "06_NORMATIVA", "description": "Politicas E-100..E-126 firmadas"},
    {"folder": "07_PROCEDIMIENTOS", "description": "Procedimientos E-200..E-234 + registros"},
    {"folder": "08_REGISTROS_OPERACION", "description": "Registros operativos ultimos 6 meses"},
    {"folder": "09_EVIDENCIAS_POR_MEDIDA", "description": "Evidencias por cada medida aplicable del Anexo II"},
    {"folder": "10_PLAN_CONTINUIDAD", "description": "BIA E-400 + BCP E-500..E-504 + pruebas"},
    {"folder": "11_FORMACION", "description": "Plan formacion + registros asistencia + evaluaciones"},
    {"folder": "12_PROVEEDORES", "description": "Inventario + contratos + evaluaciones proveedores"},
    {"folder": "13_INFORMES_TECNICOS", "description": "E-702/E-703/E-704 + delta + heatmap + raw outputs"},
    {"folder": "14_REMEDIACION", "description": "Remediaciones aplicadas (antes/despues + evidencia firmada) · ADR-055"},
    {"folder": "99_MATRIZ_CRUZADA", "description": "Matriz 99 medida x evidencia x documento (XLSX)"},
]

# Alias legacy de compatibilidad con codigo existente que aun use los
# nombres viejos. A ser eliminado tras migracion completa.
_LEGACY_FOLDER_ALIASES = {
    "08_REGISTROS_OPERATIVOS": "08_REGISTROS_OPERACION",
    "09_EVIDENCIAS": "09_EVIDENCIAS_POR_MEDIDA",
    "10_CONTINUIDAD": "10_PLAN_CONTINUIDAD",
}


# Mapeo exacto E-XXX -> carpeta
DELIVERABLE_TO_FOLDER: dict[str, str] = {
    "E-001": "06_NORMATIVA",
    "E-002": "06_NORMATIVA",
    "E-003": "07_PROCEDIMIENTOS",
    "E-005": "01_GOBIERNO",
    "E-012": "02_CATEGORIZACION",
    "E-040": "04_DECLARACION_APLICABILIDAD",
    # E-041..E-043: Declaración / cambio material / renovación periódica
    # son documentos corporate-level — viven en 01_GOBIERNO. E-042 es
    # comunicación de cambio (informativo técnico, también listable en
    # 13_INFORMES_TECNICOS si así lo prefiere el auditor; aquí se opta
    # por 01_GOBIERNO por coherencia con el resto de la familia E-04X).
    "E-041": "01_GOBIERNO",
    "E-042": "01_GOBIERNO",
    "E-043": "01_GOBIERNO",
    # R26 · artefactos de cierre de conformidad (corporate-level · 01_GOBIERNO):
    # E-049 = Distintivo de Conformidad CCN-STIC 809 (generado por FULKRO) ·
    # E-049-EXT = Certificado de la entidad de certificación acreditada (MEDIA/ALTA).
    "E-049": "01_GOBIERNO",
    "E-049-EXT": "01_GOBIERNO",
    "E-050": "03_ANALISIS_RIESGOS",
    "E-400": "10_PLAN_CONTINUIDAD",
    "E-500": "10_PLAN_CONTINUIDAD",
    # E-701 Informe Auditoría Interna pre-externa (Agente 11 / internal_auditor)
    "E-701": "13_INFORMES_TECNICOS",
    "E-702": "13_INFORMES_TECNICOS",
    "E-703": "13_INFORMES_TECNICOS",
    "E-704": "13_INFORMES_TECNICOS",
    "E-705": "13_INFORMES_TECNICOS",
    "E-706": "13_INFORMES_TECNICOS",
}


# ── #33 (FRENTE B) · DEC-4 · topes de tamaño para los binarios del dossier ──
# El dossier firmado (sign_manifest=True) embebe los binarios REALES (PDF/DOCX)
# desde MinIO (durables · #31).
#
# DEC-4 (decisión Marcos 2026-06-06):
#  (a) Topes CONFIGURABLES por nivel ENS + override por ENV.
#  (b) CRÍTICO · los ARTEFACTOS CANÓNICOS (Declaración de Conformidad, SoA/DdA,
#      informe de pentest, certificado) NUNCA se omiten por tamaño — whitelist
#      que SIEMPRE entran al dossier sin importar el tope. La omisión graceful
#      vale SOLO para volumen secundario (logs en bruto, anexos), JAMÁS para
#      evidencia canónica (un dossier ENAC sin la Declaración firmada es inútil).
MAX_DOSSIER_SINGLE_BINARY_BYTES = 50 * 1024 * 1024   # 50 MB por documento (def)
MAX_DOSSIER_BINARY_TOTAL_BYTES = 500 * 1024 * 1024   # 500 MB acumulado (def)

# Tope total por NIVEL (MB) · ALTA genera más evidencia (SOC/DR/pentest).
_DOSSIER_TOTAL_MB_BY_LEVEL: dict[str, int] = {
    "BASICA": 200,
    "MEDIA": 500,
    "ALTA": 1024,
}

# Artefactos CANÓNICOS por template_codigo · SIEMPRE en el dossier (sin tope).
# IDENTIDAD CANÓNICA E-040 (R26 · cementada): E-040 = INFORME FINAL DE ADECUACIÓN
#   AL ENS · documento de síntesis firmado por RSEG que INCLUYE la Declaración de
#   Aplicabilidad (SoA · 73 medidas del Anexo II) como su Anexo II. "DdA/SoA" es el
#   ROL que cumple, NO un documento aparte: no existe un Document SoA independiente
#   (la matriz vive en dda_entries de m03 y se firma como dda_snapshot_hash vía M03;
#   el Document E-040 lo aprueba/firma el RSEG). · E-041 = Declaración de Conformidad
#   ENS · E-808C = Declaración de Conformidad BÁSICA (cierre) · E-130/E-131 = informe
#   técnico / pentest · E-049 = Distintivo de Conformidad CCN-STIC 809 (autopublicable;
#   NO es el «certificado» de la entidad de certificación acreditada).
_CANONICAL_DOSSIER_CODES: frozenset[str] = frozenset({
    "E-040", "E-041", "E-808C", "E-808", "E-130", "E-131", "E-049", "E-049-EXT",
})
# clasificaciones/tipos canónicos (defensa adicional si falta template_codigo).
_CANONICAL_DOSSIER_TIPOS: frozenset[str] = frozenset({
    "conformidad", "declaracion_conformidad", "certificado",
    "informe_pentest", "soa", "dda",
})


def resolve_dossier_caps(categoria: str | None) -> tuple[int, int]:
    """DEC-4 (a) · devuelve (single_cap, total_cap) en bytes, configurables por
    nivel ENS + override por ENV (FULKRO_DOSSIER_SINGLE_BINARY_MB /
    FULKRO_DOSSIER_TOTAL_BINARY_MB). Solo aplican a volumen NO canónico."""
    import os

    cat = (categoria or "").upper()
    total_mb = _DOSSIER_TOTAL_MB_BY_LEVEL.get(cat, 500)
    single_mb = MAX_DOSSIER_SINGLE_BINARY_BYTES // (1024 * 1024)
    try:
        single_mb = int(os.environ.get("FULKRO_DOSSIER_SINGLE_BINARY_MB", single_mb))
        total_mb = int(os.environ.get("FULKRO_DOSSIER_TOTAL_BINARY_MB", total_mb))
    except ValueError:
        pass
    return single_mb * 1024 * 1024, total_mb * 1024 * 1024


def is_canonical_dossier_artifact(doc: dict) -> bool:
    """DEC-4 (b) · ¿es evidencia canónica que NUNCA puede omitirse por tamaño?

    Declaración de Conformidad / SoA(DdA) / informe pentest / certificado.
    Reconoce por template_codigo (whitelist) o por tipo/clasificación canónica.
    """
    code = (doc.get("template_codigo") or "").upper().strip()
    if code in _CANONICAL_DOSSIER_CODES:
        return True
    tipo = (doc.get("tipo") or "").lower().strip()
    clasif = (doc.get("clasificacion") or "").lower().strip()
    return tipo in _CANONICAL_DOSSIER_TIPOS or clasif in _CANONICAL_DOSSIER_TIPOS


class DossierError(ValueError):
    pass


def classify_folder(template_codigo: Optional[str]) -> str:
    if not template_codigo:
        return "08_REGISTROS_OPERACION"
    code = template_codigo.strip().upper()
    if code in DELIVERABLE_TO_FOLDER:
        return DELIVERABLE_TO_FOLDER[code]
    if code.startswith("E-1"):
        return "06_NORMATIVA"
    if code.startswith("E-2"):
        return "07_PROCEDIMIENTOS"
    if code.startswith("E-3"):
        return "05_PLAN_ADECUACION"
    if code.startswith("E-4"):
        return "10_PLAN_CONTINUIDAD"
    if code.startswith("E-5"):
        return "10_PLAN_CONTINUIDAD"
    if code.startswith("E-6"):
        return "11_FORMACION"
    if code.startswith("E-7"):
        return "13_INFORMES_TECNICOS"
    return "08_REGISTROS_OPERACION"  # canónico (coincide con DOSSIER_STRUCTURE + línea 180)


# =============== Collectors ===============

async def _collect_documents(
    db: AsyncSession, project_id: uuid.UUID,
) -> list[dict]:
    r = await db.execute(
        select(Document).where(
            Document.project_id == project_id,
            Document.deleted_at.is_(None),
        ).order_by(Document.template_codigo.asc())
    )
    docs = list(r.scalars().all())
    out: list[dict] = []
    for d in docs:
        out.append({
            "template_codigo": d.template_codigo,
            "nombre": d.nombre,
            "tipo": d.tipo,
            "estado": d.estado,
            "aprobado_por": d.aprobado_por,
            "fecha_aprobacion": (
                d.fecha_aprobacion.isoformat() if d.fecha_aprobacion else None
            ),
            "signature_ed25519": d.signature_ed25519,
            "docx_path": d.docx_path,
            "pdf_path": d.pdf_path,
            "storage_path": d.storage_path,
            "clasificacion": d.clasificacion,
            "rendered_hash": d.rendered_hash,
            "carpeta_destino": classify_folder(d.template_codigo),
            "document_id": str(d.id),
        })
    return out


async def _collect_evidence(
    db: AsyncSession, project_id: uuid.UUID,
) -> list[dict]:
    r = await db.execute(
        select(Evidence).where(
            Evidence.project_id == project_id,
            Evidence.deleted_at.is_(None),
        )
    )
    out: list[dict] = []
    for ev in r.scalars().all():
        out.append({
            "evidence_id": str(ev.id),
            "measure_code": ev.measure_code or "sin_medida",
            "tipo": ev.tipo,
            "hash_sha256": ev.hash_sha256,
            "fecha_evidencia": (
                ev.fecha_evidencia.isoformat() if ev.fecha_evidencia else None
            ),
            "fecha_caducidad": (
                ev.fecha_caducidad.isoformat() if ev.fecha_caducidad else None
            ),
            "vigente": bool(ev.vigente),
            "fuente": ev.fuente,
            "evidence_type_id": ev.evidence_type_id,
        })
    return out


async def _collect_operational_records(
    db: AsyncSession, project_id: uuid.UUID,
) -> list[dict]:
    r = await db.execute(
        select(Evidence).where(
            Evidence.project_id == project_id,
            Evidence.deleted_at.is_(None),
            Evidence.tipo == "registro_operativo",
        )
    )
    out: list[dict] = []
    for ev in r.scalars().all():
        mes = ev.fecha_evidencia.strftime("%Y-%m") if ev.fecha_evidencia else "sin_fecha"
        out.append({
            "mes": mes,
            "evidence_id": str(ev.id),
            "measure_code": ev.measure_code,
            "hash_sha256": ev.hash_sha256,
            "fecha_evidencia": (
                ev.fecha_evidencia.isoformat() if ev.fecha_evidencia else None
            ),
            "fuente": ev.fuente,
        })
    return out


async def _collect_pentest_findings(
    db: AsyncSession, project_id: uuid.UUID,
) -> list[dict]:
    """Hallazgos de verificacion tecnica (M8 v5.1) listos para el dossier.

    Delega al helper ``m8_verification.integrations.m9_audit_prep`` que
    solo devuelve findings con classification in {confirmed, probable}.
    """
    return await collect_findings_for_dossier(db, project_id)


async def _collect_conformity_declarations(
    db: AsyncSession, project_id: uuid.UUID,
) -> list[dict]:
    """Declaraciones M27 (E-041 Declaración Conformidad ENS) listas para dossier.

    Carga ``BasicDeclarationRow`` + ``ConformitySubmissionRow`` enlazada por
    submission_id. Devuelve metadata firmada lista para empaquetar bajo
    ``01_GOBIERNO/declaracion_conformidad/``. Si M27 no se ha invocado todavía
    en este proyecto (ruta BÁSICA no iniciada o MEDIA/ALTA pre-certif), la
    lista es vacía — el dossier sigue siendo válido sin esta sección.
    """
    from backend.app.models.conformity_lifecycle import (
        BasicDeclarationRow,
        ConformitySubmissionRow,
    )

    r = await db.execute(
        select(BasicDeclarationRow).where(
            BasicDeclarationRow.project_id == project_id,
        ).order_by(BasicDeclarationRow.created_at.asc())
    )
    declarations = list(r.scalars().all())
    if not declarations:
        return []

    sub_ids = [d.submission_id for d in declarations if d.submission_id]
    submissions_by_id: dict[uuid.UUID, ConformitySubmissionRow] = {}
    if sub_ids:
        rs = await db.execute(
            select(ConformitySubmissionRow).where(
                ConformitySubmissionRow.id.in_(sub_ids),
            )
        )
        submissions_by_id = {s.id: s for s in rs.scalars().all()}

    out: list[dict] = []
    for d in declarations:
        sub = submissions_by_id.get(d.submission_id) if d.submission_id else None
        out.append({
            "declaration_id": str(d.id),
            "declaration_type": d.declaration_type,
            "template_codigo": "E-041",
            "responsible_person_name": d.responsible_person_name,
            "responsible_person_email": d.responsible_person_email,
            "published_evidence_url": d.published_evidence_url,
            "signed_at": d.signed_at.isoformat() if d.signed_at else None,
            "signed_hash": d.signed_hash,
            "status": d.status,
            "self_assessment_report_id": (
                str(d.self_assessment_report_id)
                if d.self_assessment_report_id else None
            ),
            "submission": (
                {
                    "submission_id": str(sub.id),
                    "submission_type": sub.submission_type,
                    "external_system": sub.external_system,
                    "external_ref_id": sub.external_ref_id,
                    "submitted_at": (
                        sub.submitted_at.isoformat() if sub.submitted_at else None
                    ),
                    "status": sub.status,
                }
                if sub else None
            ),
            "carpeta_destino": "01_GOBIERNO",
        })
    return out


async def generate_declaracion_conformidad_via_m27(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    responsible_person_name: str,
    responsible_person_email: str,
    published_url: str | None = None,
    self_assessment_report_id: uuid.UUID | None = None,
) -> dict:
    """Genera E-041 vía M27 ``process_basic_declaration``.

    Wire ligero M9 → M27 que delega la lógica de generación de declaración
    al motor canónico (M27 ConformityServicePaso5) y devuelve los metadatos
    listos para inclusión en el dossier. NO renderiza el DOCX (eso ocurre
    cuando M6 genera el E-041 a partir del template registrado) — esta
    función solo crea el ``BasicDeclarationRow`` + ``ConformitySubmissionRow``.

    Sólo aplicable a proyectos con ``route_type=declaracion_basica`` (BÁSICA).
    Para MEDIA/ALTA se usa el flujo ENAC vía ``prepare_enac_certification``.

    El caller debe haber establecido el contexto RLS antes de invocar.
    """
    from backend.app.motors.m27_conformity.conformity_service_paso5 import (
        ConformityError,
        ConformityServicePaso5,
    )

    service = ConformityServicePaso5()
    try:
        decl = await service.process_basic_declaration(
            db, project_id,
            responsible_person_name=responsible_person_name,
            responsible_person_email=responsible_person_email,
            published_url=published_url,
            self_assessment_report_id=self_assessment_report_id,
        )
    except ConformityError as exc:
        raise DossierError(
            f"No se pudo generar la Declaración de Conformidad vía M27: {exc}"
        ) from exc

    return {
        "declaration_id": str(decl.id),
        "signed_hash": decl.signed_hash,
        "status": decl.status,
        "submission_id": str(decl.submission_id) if decl.submission_id else None,
        "carpeta_destino": "01_GOBIERNO",
        "template_codigo": "E-041",
    }


# =============== Indice + resumen ejecutivo ===============

def _build_index(
    documents: list[dict], evidence: list[dict],
    records: list[dict], findings: list[dict],
) -> str:
    lines: list[str] = []
    lines.append("# Indice Maestro del Dossier")
    lines.append("")
    lines.append(
        f"_Generado: {datetime.now(timezone.utc).isoformat()}_"
    )
    lines.append("")

    by_folder: dict[str, list[str]] = {}
    for d in documents:
        folder = d["carpeta_destino"]
        code = d.get("template_codigo") or "sin_codigo"
        nombre = d.get("nombre") or ""
        by_folder.setdefault(folder, []).append(f"- {code}: {nombre}")

    for item in DOSSIER_STRUCTURE:
        folder = item["folder"]
        lines.append(f"## {folder} — {item['description']}")
        entries = by_folder.get(folder, [])
        if entries:
            for e in entries:
                lines.append(e)
        else:
            # Contenidos auto-generados por carpeta (nombres canónicos =
            # DOSSIER_STRUCTURE; antes comparaba nombres legacy que nunca casaban).
            if folder == "08_REGISTROS_OPERACION":
                lines.append(f"- {len(records)} registros operativos")
            elif folder == "09_EVIDENCIAS_POR_MEDIDA":
                by_measure: dict[str, int] = {}
                for ev in evidence:
                    by_measure[ev["measure_code"]] = (
                        by_measure.get(ev["measure_code"], 0) + 1
                    )
                lines.append(
                    f"- {len(by_measure)} medidas con evidencias, "
                    f"{len(evidence)} evidencias totales"
                )
            elif folder == "13_INFORMES_TECNICOS":
                lines.append(f"- {len(findings)} findings pentest")
            elif folder == "99_MATRIZ_CRUZADA":
                lines.append("- matriz_medidas_evidencias.xlsx")
            else:
                lines.append("- (vacia)")
        lines.append("")
    return "\n".join(lines)


def _build_executive_summary(
    run: AuditPreparationRun,
    documents: list[dict], evidence: list[dict],
    findings: list[dict],
    *,
    declarations: list[dict] | None = None,
) -> str:
    results = run.checklist_results or {}
    readiness = run.readiness_score or 0
    interpretation = (
        "LISTO PARA AUDITORIA" if readiness >= 90
        else "AJUSTES MENORES" if readiness >= 70
        else "TRABAJO SIGNIFICATIVO" if readiness >= 50
        else "NO PRESENTAR"
    )
    ent = results.get("entregables", {})
    evid = results.get("evidencias", {})

    vigentes = sum(1 for e in evidence if e["vigente"])
    # FIX: collect_findings_for_dossier emite la clave "severity" (inglés), no
    # "severidad" → critical_findings era SIEMPRE 0 y el resumen ejecutivo del
    # dossier ENAC decía "(0 criticos)" ocultando hallazgos críticos al auditor.
    critical_findings = sum(
        1 for f in findings if (f.get("severity") or "").lower() in {"critical", "critica"}
    )
    decls = declarations or []
    signed_decls = sum(
        1 for d in decls if (d.get("status") or "").lower() == "signed"
    )

    lines = [
        "# Resumen Ejecutivo — Dossier de Auditoria ENS",
        "",
        f"**Fecha de generacion**: {datetime.now(timezone.utc).isoformat()}",
        f"**Proyecto ID**: {run.project_id}",
        f"**Categoria ENS**: {run.categoria}",
        f"**Readiness score**: {readiness}/100 ({interpretation})",
        "",
        "## Stats clave",
        f"- Entregables requeridos: {ent.get('total', 0)}, "
        f"presentes: {ent.get('present', 0)}, "
        f"ausentes: {len(ent.get('missing', []) or [])}",
        f"- Evidencias totales: {len(evidence)}, vigentes: {vigentes}",
        f"- Evidencias vigentes (checklist): {evid.get('vigentes', 0)}/"
        f"{evid.get('total', 0)}",
        f"- Findings pentest: {len(findings)} "
        f"({critical_findings} criticos)",
        f"- Declaraciones de Conformidad (E-041) registradas: {len(decls)} "
        f"({signed_decls} firmadas)",
        f"- Contradicciones detectadas: {run.contradicciones_count}",
        f"- Alertas: {run.alertas_count}",
        "",
        "## Contacto consultor",
        "- Marcos Mata García",
        "- Consultor independiente en Esquema Nacional de Seguridad",
        "",
        "## Instrucciones para el auditor",
        "Consulte 00_INDICE/indice_maestro.md para la estructura "
        "completa del dossier. El fichero 99_MATRIZ_CRUZADA/"
        "matriz_medidas_evidencias.xlsx contiene el mapa "
        "medida → evidencia → documento recomendado como punto de partida. "
        "Las Declaraciones de Conformidad (E-041) firmadas se encuentran en "
        "01_GOBIERNO/declaracion_conformidad/.",
    ]
    return "\n".join(lines)


# =============== ZIP assembly ===============

def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def _collect_remediations(
    db: AsyncSession, project_id: uuid.UUID,
) -> tuple[list[dict], str]:
    """FASE 4 · recopila las remediaciones (ADR-055) del proyecto para el dossier:
    acción, medida ENS, estado, antes/después (result), recurso, evidencia. El
    estado de cada job + su `result` aporta la trazabilidad antes/después. Best-
    effort: si el motor no está o RLS no deja ver nada → ([], nota honesta)."""
    try:
        from backend.app.motors.m_remediation.catalog import get_action_spec
        rows = (await db.execute(_sa_text(
            "SELECT id::text AS id, action_type, tier, status, target_ref, "
            "source_gap_id::text AS source_gap_id, error_message, result, "
            "created_at, finished_at "
            "FROM remediation_jobs "
            "WHERE project_id = :pid AND deleted_at IS NULL "
            "ORDER BY created_at DESC"
        ), {"pid": str(project_id)})).mappings().all()
    except Exception:  # noqa: BLE001 — non-fatal · el ZIP se entrega igual
        return [], "Sin datos de remediación disponibles."

    out: list[dict] = []
    for r in rows:
        spec = get_action_spec(r["action_type"])
        out.append({
            "job_id": r["id"],
            "action_type": r["action_type"],
            "titulo": spec.title_es if spec else r["action_type"],
            "ens_measures": list(spec.ens_measures) if spec else [],
            "tier": r["tier"],
            "estado": r["status"],
            "recurso": r["target_ref"],
            "source_gap_id": r["source_gap_id"],
            "resultado": r["result"],
            "error": r["error_message"],
            "created_at": str(r["created_at"]) if r["created_at"] else None,
            "finished_at": str(r["finished_at"]) if r["finished_at"] else None,
        })

    lines = ["# Informe de Remediaciones aplicadas (ADR-055)", ""]
    if not out:
        lines.append(
            "No se han registrado remediaciones automáticas para este proyecto."
        )
    else:
        succeeded = sum(1 for j in out if j["estado"] == "succeeded")
        lines += [
            f"Total de remediaciones: **{len(out)}** · resueltas con éxito: "
            f"**{succeeded}**.", "",
            "| Acción | Medida ENS | Estado | Recurso |",
            "|--------|-----------|--------|---------|",
        ]
        for j in out:
            lines.append(
                f"| {j['titulo']} | {', '.join(j['ens_measures']) or '-'} | "
                f"{j['estado']} | {j['recurso'] or '-'} |"
            )
    return out, "\n".join(lines)


def _build_impl_coverage_section(categoria: str | None) -> tuple[dict, str]:
    """IMPL-6 · matriz 'no falta ni uno' para el dossier ENAC.

    Para el nivel del proyecto, demuestra que CADA medida del Anexo II aplicable
    tiene un camino de implantación: automático (plantilla cloud/host que el
    sistema aplica con ciclo seguro) o guiado (tarea + entregable que ejecuta el IT
    del cliente y se verifica con evidencia). Determinista (R1) · reutiliza
    ``m_remediation.impl_coverage``. Best-effort: si no se puede calcular, nota
    honesta sin romper el ZIP."""
    try:
        from backend.app.motors.m_remediation.impl_coverage import (
            compute_implementation_coverage,
        )
        cov = compute_implementation_coverage(categoria or "MEDIA")
    except Exception:  # noqa: BLE001 — non-fatal · el ZIP se entrega igual
        return {}, "Cobertura de implantación técnica no disponible."

    lines = [
        "# Cobertura de implantación técnica (ENS · 'no falta ni uno')", "",
        f"Nivel del proyecto: **{cov['level']}** · medidas aplicables: "
        f"**{cov['total_applicable']}** · con plantilla automática: "
        f"**{cov['auto_count']}** · guiadas (tarea + entregable): "
        f"**{cov['guided_count']}** · sin camino de implantación: "
        f"**{len(cov['uncovered'])}**.", "",
        "Toda medida aplicable tiene un camino de implantación. Las **automáticas** "
        "las aplica el sistema con ciclo seguro (copia previa + verificación + "
        "deshacer si falla); las **guiadas** las ejecuta el IT del cliente con guía "
        "del copiloto y se cierran con evidencia.", "",
        "| Medida | Nombre | Camino |",
        "|--------|--------|--------|",
    ]
    for r in cov.get("rows", []):
        camino = "Automático" if r["coverage"] == "auto" else "Guiado"
        lines.append(f"| {r['measure']} | {r['nombre']} | {camino} |")
    return cov, "\n".join(lines)


async def generate_dossier(
    db: AsyncSession, project_id: uuid.UUID, run_id: uuid.UUID,
    *, force: bool = False, sign_manifest: bool = False,
) -> bytes:
    """Genera el ZIP del dossier.

    - Si ``force=False`` (default), valida con
      ``require_complete_audit_prep`` y si hay bloqueantes levanta
      ``DossierError`` con el detalle de todos los items a resolver.
    - Si ``force=True``, emite un dossier parcial marcado como
      BORRADOR con los items faltantes listados en el manifest y el
      indice (para uso interno de Marcos, nunca para entrega ENAC).
    - Si ``sign_manifest=True`` (Sesión 3B-2B.6 Cluster 1 Phase 1):
      MANIFEST.json incluye `_signature` block Ed25519 (M05 keypair).
      Auditor ENAC verifica integridad cross-archivo + autoría Marcos
      sin depender ZIP-level signatures. NUNCA True junto force=True
      (BORRADOR no debe firmar · entrega final ENAC only).
    """
    if sign_manifest and force:
        raise DossierError(
            "sign_manifest=True incompatible con force=True · "
            "BORRADOR no debe firmar (entrega ENAC final only).",
        )
    run = await get_run(db, run_id)
    if run is None or run.project_id != project_id:
        raise DossierError(f"AuditPreparationRun {run_id} no encontrado")

    from .checklist_service import require_complete_audit_prep
    blockers: list[dict] = []
    try:
        blockers = require_complete_audit_prep(run)
    except Exception as exc:  # pragma: no cover — validation requires completed run
        raise DossierError(
            f"No se pudo validar el run: {exc}"
        ) from exc
    if blockers and not force:
        short = "; ".join(
            b["descripcion"] for b in blockers[:3]
        )
        raise DossierError(
            f"Dossier bloqueado por {len(blockers)} item(s) pendientes: "
            f"{short}{'...' if len(blockers) > 3 else ''}. "
            f"Resuelve los items o ejecuta generate_dossier(force=True) "
            f"para obtener un dossier parcial BORRADOR.",
        )
    draft_mode = bool(blockers) and force

    documents = await _collect_documents(db, project_id)
    evidence = await _collect_evidence(db, project_id)
    records = await _collect_operational_records(db, project_id)
    findings = await _collect_pentest_findings(db, project_id)
    declarations = await _collect_conformity_declarations(db, project_id)

    index_content = _build_index(documents, evidence, records, findings)
    exec_summary = _build_executive_summary(
        run, documents, evidence, findings, declarations=declarations,
    )
    matriz_xlsx = await matriz_mod.generate_matriz_99(
        db, project_id, run.categoria,
    )

    buf = io.BytesIO()
    file_hashes: list[dict] = []

    def _write(zipf: zipfile.ZipFile, name: str, payload: bytes) -> None:
        zipf.writestr(name, payload)
        file_hashes.append({
            "file": name,
            "sha256": _sha256_bytes(payload),
            "size_bytes": len(payload),
        })

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zipf:
        # Crear marcadores de cada carpeta
        for item in DOSSIER_STRUCTURE:
            zipf.writestr(f"{item['folder']}/.keep", b"")

        # 00_INDICE
        _write(
            zipf, "00_INDICE/indice_maestro.md",
            index_content.encode("utf-8"),
        )
        _write(
            zipf, "00_INDICE/resumen_ejecutivo.md",
            exec_summary.encode("utf-8"),
        )
        # PDF maestro navegable (si pandoc + libreoffice disponibles)
        pdf_master_included = False
        try:
            from .pdf_master_generator import (
                generate_pdf_master, PdfMasterError,
            )
            pdf_bytes = await generate_pdf_master(db, project_id, run_id)
            _write(zipf, "00_INDICE/00_INDICE_MAESTRO.pdf", pdf_bytes)
            pdf_master_included = True
        except PdfMasterError as exc:
            # Non-fatal: ZIP se entrega con los MDs aunque falte el PDF
            import logging
            logging.getLogger(__name__).warning(
                "PDF maestro no generado: %s", exc,
            )
        except Exception as exc:  # pragma: no cover
            import logging
            logging.getLogger(__name__).warning(
                "PDF maestro fallo inesperado: %s", exc,
            )

        # Documentos en sus carpetas
        # #33 (FRENTE B): cuando sign_manifest=True el dossier es la ENTREGA
        # ENAC → embebe los binarios REALES (PDF/DOCX) desde MinIO, no solo el
        # .json de metadata. DEC-4: topes de tamaño con omisión graceful anotada.
        # DEC-4 · topes configurables por nivel ENS + override ENV.
        single_cap, total_cap = resolve_dossier_caps(run.categoria)
        binaries_included = 0
        binaries_total_bytes = 0
        binary_omissions: list[dict] = []
        binaries_canonical_forced = 0  # canónicos incluidos pese a superar tope
        for d in documents:
            folder = d["carpeta_destino"]
            code = d.get("template_codigo") or "doc"
            safe_name = (
                str(d.get("nombre") or "document")
                .replace("/", "_").replace(" ", "_")
            )
            filename = f"{code}_{safe_name[:60]}.json"
            _write(
                zipf, f"{folder}/{filename}",
                json.dumps(
                    d, default=str, indent=2, ensure_ascii=False,
                ).encode("utf-8"),
            )

            if not sign_manifest:
                continue
            # DEC-4 (b): evidencia canónica NUNCA se omite por tamaño.
            canonical = is_canonical_dossier_artifact(d)
            storage_path = d.get("storage_path")
            if not storage_path or not str(storage_path).startswith("minio://"):
                binary_omissions.append({
                    "template_codigo": code,
                    "document_id": d.get("document_id"),
                    "reason": "sin_binario_durable_minio",
                    "canonical": canonical,
                })
                continue
            rest = str(storage_path)[len("minio://"):]
            bucket, _, key = rest.partition("/")
            bin_ext = ".pdf" if key.endswith(".pdf") else (
                ".docx" if key.endswith(".docx") else ".bin"
            )
            try:
                from backend.app.core.storage.minio_client import get_object
                payload = get_object(bucket, key)
            except Exception as exc:  # noqa: BLE001 — entrega honesta
                # Incluso un canónico no puede embeberse si MinIO no responde ·
                # se anota como canonical para que el admin lo resuelva (no falla
                # el ZIP · pero queda VISIBLE que falta evidencia canónica).
                binary_omissions.append({
                    "template_codigo": code,
                    "document_id": d.get("document_id"),
                    "reason": f"minio_unreachable: {exc}",
                    "canonical": canonical,
                })
                continue
            # Topes SOLO para volumen NO canónico (logs/anexos secundarios).
            if not canonical:
                if len(payload) > single_cap:
                    binary_omissions.append({
                        "template_codigo": code,
                        "document_id": d.get("document_id"),
                        "reason": "supera_tope_por_documento",
                        "size_bytes": len(payload),
                        "canonical": False,
                    })
                    continue
                if binaries_total_bytes + len(payload) > total_cap:
                    binary_omissions.append({
                        "template_codigo": code,
                        "document_id": d.get("document_id"),
                        "reason": "supera_tope_total_dossier",
                        "size_bytes": len(payload),
                        "canonical": False,
                    })
                    continue
            elif (
                len(payload) > single_cap
                or binaries_total_bytes + len(payload) > total_cap
            ):
                # Canónico que excede el tope → se incluye IGUAL (whitelist).
                binaries_canonical_forced += 1
            _write(zipf, f"{folder}/{code}_{safe_name[:60]}{bin_ext}", payload)
            binaries_included += 1
            binaries_total_bytes += len(payload)

        # 09_EVIDENCIAS_POR_MEDIDA — subcarpetas por medida
        seen_paths: set[str] = set()
        for ev in evidence:
            measure = ev["measure_code"]
            hash_short = (ev.get("hash_sha256") or "noh")[:8]
            tipo = ev.get("tipo") or "evidencia"
            base = f"09_EVIDENCIAS_POR_MEDIDA/{measure}/{tipo}_{hash_short}"
            # Evitar duplicados cuando varias evidencias comparten hash+tipo
            path = f"{base}.json"
            suffix = 1
            while path in seen_paths:
                suffix += 1
                path = f"{base}_{suffix}.json"
            seen_paths.add(path)
            _write(
                zipf, path,
                json.dumps(
                    ev, default=str, indent=2, ensure_ascii=False,
                ).encode("utf-8"),
            )

        # 08_REGISTROS_OPERATIVOS — agrupado por mes
        for rec in records:
            mes = rec.get("mes", "sin_fecha")
            hash_short = (rec.get("hash_sha256") or "noh")[:8]
            filename = f"{mes}_{hash_short}.json"
            _write(
                zipf, f"08_REGISTROS_OPERACION/{filename}",
                json.dumps(
                    rec, default=str, indent=2, ensure_ascii=False,
                ).encode("utf-8"),
            )

        # 13_INFORMES_TECNICOS — findings pentest summary
        if findings:
            _write(
                zipf, "13_INFORMES_TECNICOS/pentest_findings_summary.json",
                json.dumps(
                    findings, default=str, indent=2, ensure_ascii=False,
                ).encode("utf-8"),
            )

        # F9 (FRENTE F) · compliance_declaration.json · estado del vuln-scan/
        # pentest interno + nota honesta ENAC (mp.s.2). SIEMPRE presente (aunque
        # no haya findings) para que el auditor vea el estado de la verificación
        # técnica y la regla ALTA (pentester EXTERNO obligatorio · este motor
        # COMPLEMENTA, no sustituye). Reusa compute_pentest_summary (F7) · OPS-026.
        from backend.app.motors.m09_audit_prep.simulacro_pre_enac_service import (
            compute_pentest_summary,
        )

        pentest_status = await compute_pentest_summary(db, project_id)
        compliance_declaration = {
            "project_id": str(project_id),
            "categoria": run.categoria,
            "readiness_score": run.readiness_score,
            "pentest_status": pentest_status,
            "alta_external_pentest_required": (run.categoria or "").upper()
            in {"ALTA", "ALTO"},
            "total_conformity_declarations": len(declarations),
            "total_pentest_findings": len(findings),
        }
        _write(
            zipf, "13_INFORMES_TECNICOS/compliance_declaration.json",
            json.dumps(
                compliance_declaration, default=str, indent=2,
                ensure_ascii=False,
            ).encode("utf-8"),
        )

        # 14_REMEDIACION — remediaciones ADR-055 (antes/después + estado) · FASE 4.
        # Cierra el "todo junto": el dossier (auditor + cliente) incluye también lo
        # que el sistema remedió automáticamente tras el pentest/diagnóstico.
        remediations, remediation_md = await _collect_remediations(db, project_id)
        _write(
            zipf, "14_REMEDIACION/remediaciones.json",
            json.dumps(
                remediations, default=str, indent=2, ensure_ascii=False,
            ).encode("utf-8"),
        )
        _write(
            zipf, "14_REMEDIACION/informe_remediaciones.md",
            remediation_md.encode("utf-8"),
        )
        # IMPL-6 · matriz de cobertura de implantación ('no falta ni uno') para
        # que el auditor ENAC vea que cada medida tiene camino auto o guiado.
        cov_data, cov_md = _build_impl_coverage_section(run.categoria)
        _write(
            zipf, "14_REMEDIACION/cobertura_implantacion.json",
            json.dumps(
                cov_data, default=str, indent=2, ensure_ascii=False,
            ).encode("utf-8"),
        )
        _write(
            zipf, "14_REMEDIACION/cobertura_implantacion.md",
            cov_md.encode("utf-8"),
        )

        # 01_GOBIERNO/declaracion_conformidad/ — M27 BasicDeclarationRow + submission
        for d in declarations:
            short_hash = (d.get("signed_hash") or "unsigned")[:10]
            decl_type = d.get("declaration_type", "decl")
            filename = f"E-041_{decl_type}_{short_hash}.json"
            _write(
                zipf,
                f"01_GOBIERNO/declaracion_conformidad/{filename}",
                json.dumps(
                    d, default=str, indent=2, ensure_ascii=False,
                ).encode("utf-8"),
            )

        # 99_MATRIZ_CRUZADA
        _write(
            zipf, "99_MATRIZ_CRUZADA/matriz_medidas_evidencias.xlsx",
            matriz_xlsx,
        )

        # BORRADOR banner si aplica
        if draft_mode:
            banner_lines = [
                "# BORRADOR — DOSSIER PARCIAL",
                "",
                f"Generado con `force=True` a pesar de {len(blockers)} "
                "item(s) bloqueantes. **NO ENTREGAR a auditor ENAC.**",
                "",
                "## Items a resolver antes de dossier final",
                "",
            ]
            for b in blockers:
                banner_lines.append(
                    f"- [{b.get('tipo','?')}] **{b.get('codigo','?')}** · "
                    f"{b.get('descripcion','')}",
                )
            _write(
                zipf, "00_INDICE/BORRADOR_pendientes.md",
                "\n".join(banner_lines).encode("utf-8"),
            )

        # MANIFEST final
        manifest = {
            "run_id": str(run_id),
            "project_id": str(project_id),
            "categoria": run.categoria,
            "readiness_score": run.readiness_score,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "dossier_structure": DOSSIER_STRUCTURE,
            "total_documents": len(documents),
            "total_evidence": len(evidence),
            "total_records": len(records),
            "total_findings": len(findings),
            "total_declarations": len(declarations),
            "pdf_master_included": pdf_master_included,
            # #33 (FRENTE B): binarios reales embebidos (solo en dossier firmado)
            "binaries_included": binaries_included,
            "binaries_total_bytes": binaries_total_bytes,
            "binaries_omitted": binary_omissions,
            # DEC-4 (b): canónicos incluidos pese a superar tope (whitelist) +
            # alerta si SE OMITIÓ algún canónico (debe ser 0 en una entrega real).
            "binaries_canonical_forced": binaries_canonical_forced,
            "canonical_omitted_count": sum(
                1 for o in binary_omissions if o.get("canonical")
            ),
            "draft_mode": draft_mode,
            "blockers": blockers if draft_mode else [],
            "files": file_hashes,
        }

        # Sesión 3B-2B.6 Cluster 1 Phase 1 · sign manifest Ed25519 (M05).
        # Canonical JSON (sort_keys + UTF-8 NO BOM) firma · manifest emitted
        # with `_signature` block containing signature_ed25519_hex + algorithm +
        # public_key_pem para verificación independiente auditor ENAC.
        if sign_manifest:
            from backend.app.motors.m05_signing.keypair import (
                get_public_key_pem,
                sign_payload,
            )
            canonical_payload = json.dumps(
                manifest, indent=None, separators=(",", ":"),
                sort_keys=True, ensure_ascii=False,
            ).encode("utf-8")
            signature = sign_payload(canonical_payload)
            manifest["_signature"] = {
                "algorithm": "Ed25519",
                "signature_hex": signature.hex(),
                "public_key_pem": get_public_key_pem(),
                "canonical_format": "json sort_keys=True separators=,: ensure_ascii=False",
                "signed_at": datetime.now(timezone.utc).isoformat(),
            }
        zipf.writestr(
            "MANIFEST.json",
            json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8"),
        )
    return buf.getvalue()


async def build_index_data(
    db: AsyncSession, project_id: uuid.UUID, run_id: uuid.UUID,
) -> dict:
    """Devuelve el indice como JSON (para API /dossier/index)."""
    run = await get_run(db, run_id)
    if run is None or run.project_id != project_id:
        raise DossierError(f"AuditPreparationRun {run_id} no encontrado")

    documents = await _collect_documents(db, project_id)
    evidence = await _collect_evidence(db, project_id)
    records = await _collect_operational_records(db, project_id)
    findings = await _collect_pentest_findings(db, project_id)
    declarations = await _collect_conformity_declarations(db, project_id)

    by_folder: dict[str, list[dict]] = {}
    for d in documents:
        by_folder.setdefault(d["carpeta_destino"], []).append({
            "template_codigo": d.get("template_codigo"),
            "nombre": d.get("nombre"),
            "estado": d.get("estado"),
        })
    evidence_by_measure: dict[str, int] = {}
    for ev in evidence:
        evidence_by_measure[ev["measure_code"]] = (
            evidence_by_measure.get(ev["measure_code"], 0) + 1
        )
    return {
        "run_id": str(run_id),
        "project_id": str(project_id),
        "categoria": run.categoria,
        "readiness_score": run.readiness_score,
        "structure": DOSSIER_STRUCTURE,
        "documents_by_folder": by_folder,
        "evidence_by_measure": evidence_by_measure,
        "declarations": declarations,
        "total_documents": len(documents),
        "total_evidence": len(evidence),
        "total_records": len(records),
        "total_findings": len(findings),
        "total_declarations": len(declarations),
    }
