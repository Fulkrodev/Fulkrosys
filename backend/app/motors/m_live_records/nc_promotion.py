"""R26 · promoción de NC E-321/E-322 (JSONB) a proyección estructurada.

El registro vivo ``live_records`` (E-321 auditorías externas, E-322 hallazgos NC)
es la fuente de verdad WORM. Esta capa deriva una proyección estructurada y
consultable en ``audit_sessions`` + ``audit_findings`` (severidad + PAC + plazos),
con upsert idempotente (re-ejecutable). Reusa los modelos existentes (OPS-026);
NO crea modelos nuevos ni toca ``remediation_plans``.

La PAC (Plan de Acción Correctiva) de cada NC se proyecta en línea sobre el
AuditFinding (``accion_correctiva`` + ``fecha_compromiso`` + ``estado``). El
validador de servicio comprueba PAC ≤ 90 días para NC mayor y la exigencia de
APC formal sólo en categorías MEDIA/ALTA.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.findings import AuditFinding, AuditSession
from backend.app.models.live_record import LiveRecord

PAC_PLAZO_DIAS_MAYOR = 90


def _parse_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def validate_pac_constraints(
    *,
    severidad: str | None,
    categoria: str | None,
    accion_correctiva: str | None,
    fecha_compromiso: date | None,
    fecha_deteccion: date | None,
    codigo: str = "",
) -> list[str]:
    """Reglas ENAC del PAC. Devuelve violaciones (advisory · no bloquea persistencia).

    - NC mayor → exige acción correctiva (PAC) y fecha de compromiso dentro de
      ``PAC_PLAZO_DIAS_MAYOR`` (90 días) desde la detección.
    - APC formal (plan de acciones correctivas) → exigible sólo en MEDIA/ALTA.
    - NC menor / observación → sin PAC obligatorio.
    """
    violations: list[str] = []
    sev = (severidad or "").lower()
    cat = (categoria or "").upper()
    tag = f"[{codigo}] " if codigo else ""
    if sev != "mayor":
        return violations

    if not (accion_correctiva or "").strip():
        violations.append(f"{tag}NC mayor sin acción correctiva (PAC obligatorio).")
    if fecha_compromiso is None:
        violations.append(f"{tag}NC mayor sin fecha de compromiso del PAC.")
    elif fecha_deteccion is not None:
        limite = fecha_deteccion + timedelta(days=PAC_PLAZO_DIAS_MAYOR)
        if fecha_compromiso > limite:
            violations.append(
                f"{tag}PAC de NC mayor excede el plazo de {PAC_PLAZO_DIAS_MAYOR} días "
                f"(compromiso {fecha_compromiso.isoformat()} > "
                f"detección+{PAC_PLAZO_DIAS_MAYOR}d {limite.isoformat()})."
            )
    if cat in ("MEDIA", "ALTA") and not (accion_correctiva or "").strip():
        violations.append(
            f"{tag}Categoría {cat}: se exige Plan de Acciones Correctivas (APC) formal."
        )
    return violations


async def _project_categoria(db: AsyncSession, project_id: uuid.UUID) -> str | None:
    row = (await db.execute(
        sa_text("SELECT categoria_objetivo FROM projects WHERE id = :p"),
        {"p": str(project_id)},
    )).first()
    return row[0] if row else None


async def _live_records(
    db: AsyncSession, project_id: uuid.UUID, register_type: str,
) -> list[LiveRecord]:
    return list((await db.execute(
        select(LiveRecord).where(
            LiveRecord.project_id == project_id,
            LiveRecord.register_type == register_type,
            LiveRecord.status == "active",
        )
    )).scalars().all())


async def _upsert_session(
    db: AsyncSession, project_id: uuid.UUID, codigo: str, data: dict,
) -> AuditSession:
    existing = (await db.execute(
        select(AuditSession).where(
            AuditSession.project_id == project_id,
            AuditSession.codigo_externo == codigo,
            AuditSession.deleted_at.is_(None),
        ).limit(1)
    )).scalar_one_or_none()
    session = existing or AuditSession(project_id=project_id, codigo_externo=codigo)
    session.tipo = "externa"
    session.fecha_inicio = _parse_date(data.get("fecha_inicio"))
    session.fecha_fin = _parse_date(data.get("fecha_fin"))
    session.auditor = data.get("entidad_acreditada") or session.auditor
    session.alcance = data.get("alcance")
    session.resultado = data.get("resultado")
    if existing is None:
        db.add(session)
    await db.flush()
    return session


async def _upsert_finding(
    db: AsyncSession, session: AuditSession, data: dict,
) -> AuditFinding:
    codigo = data.get("codigo_hallazgo")
    existing = (await db.execute(
        select(AuditFinding).where(
            AuditFinding.audit_session_id == session.id,
            AuditFinding.codigo_externo == codigo,
            AuditFinding.deleted_at.is_(None),
        ).limit(1)
    )).scalar_one_or_none()
    finding = existing or AuditFinding(
        audit_session_id=session.id, codigo_externo=codigo,
    )
    finding.severidad = data.get("severidad")
    finding.medida_afectada = data.get("medida_ens_afectada")
    finding.descripcion = data.get("descripcion")
    finding.estado = data.get("estado")
    finding.accion_correctiva = data.get("accion_correctiva")
    finding.responsable = data.get("responsable")
    finding.fecha_compromiso = _parse_date(data.get("fecha_compromiso"))
    finding.fecha_cierre = _parse_date(data.get("fecha_cierre_real"))
    if existing is None:
        db.add(finding)
    await db.flush()
    return finding


async def promote_audit_ncs(db: AsyncSession, project_id: uuid.UUID) -> dict:
    """Proyecta E-321/E-322 a audit_sessions/audit_findings (idempotente)."""
    categoria = await _project_categoria(db, project_id)
    sessions_by_codigo: dict[str, AuditSession] = {}

    for rec in await _live_records(db, project_id, "E-321"):
        cod = (rec.entry_data or {}).get("codigo_auditoria_ext")
        if not cod:
            continue
        sessions_by_codigo[cod] = await _upsert_session(
            db, project_id, cod, rec.entry_data,
        )

    findings_out: list[dict] = []
    violations: list[str] = []
    for rec in await _live_records(db, project_id, "E-322"):
        data = rec.entry_data or {}
        aud_cod = data.get("auditoria_codigo") or "SIN-AUDITORIA"
        session = sessions_by_codigo.get(aud_cod)
        if session is None:
            session = await _upsert_session(
                db, project_id, aud_cod,
                {"entidad_acreditada": "(auditoría no registrada en E-321)"},
            )
            sessions_by_codigo[aud_cod] = session
        finding = await _upsert_finding(db, session, data)
        violations.extend(validate_pac_constraints(
            severidad=finding.severidad, categoria=categoria,
            accion_correctiva=finding.accion_correctiva,
            fecha_compromiso=finding.fecha_compromiso,
            fecha_deteccion=session.fecha_inicio,
            codigo=finding.codigo_externo or "",
        ))
        findings_out.append({
            "id": str(finding.id),
            "codigo": finding.codigo_externo,
            "severidad": finding.severidad,
            "medida_afectada": finding.medida_afectada,
            "estado": finding.estado,
        })

    return {
        "project_id": str(project_id),
        "categoria": categoria,
        "sessions_promoted": len(sessions_by_codigo),
        "findings_promoted": len(findings_out),
        "findings": findings_out,
        "pac_violations": violations,
        "pac_ok": not violations,
    }


async def list_structured_ncs(db: AsyncSession, project_id: uuid.UUID) -> list[dict]:
    """Lista las NC estructuradas (finding + sesión de origen) del proyecto."""
    rows = (await db.execute(
        select(AuditFinding, AuditSession)
        .join(AuditSession, AuditSession.id == AuditFinding.audit_session_id)
        .where(
            AuditSession.project_id == project_id,
            AuditFinding.deleted_at.is_(None),
        )
        .order_by(AuditFinding.severidad, AuditFinding.codigo_externo)
    )).all()
    out: list[dict] = []
    for finding, session in rows:
        out.append({
            "codigo": finding.codigo_externo,
            "severidad": finding.severidad,
            "medida_afectada": finding.medida_afectada,
            "descripcion": finding.descripcion,
            "estado": finding.estado,
            "accion_correctiva": finding.accion_correctiva,
            "responsable": finding.responsable,
            "fecha_compromiso": (
                finding.fecha_compromiso.isoformat()
                if finding.fecha_compromiso else None
            ),
            "fecha_cierre": (
                finding.fecha_cierre.isoformat() if finding.fecha_cierre else None
            ),
            "auditoria": {
                "codigo": session.codigo_externo,
                "entidad": session.auditor,
                "fecha_inicio": (
                    session.fecha_inicio.isoformat() if session.fecha_inicio else None
                ),
                "resultado": session.resultado,
            },
        })
    return out
