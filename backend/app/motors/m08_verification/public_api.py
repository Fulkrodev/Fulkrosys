"""M8 v5.1 - API publica de los 3 portales (sin login).

Accesibles solo por token JWT (magic link). Seguridad:
- Validacion estricta del token (hash, expiracion, revocacion, uses).
- Rate limit 20 req/min por token.
- Log cada acceso en client_interactions.
- Nunca expone IDs internos de BD en la URL (solo via token).
- CORS restrictivo se aplica en main.py a nivel de app.

3 portales:
- /public/remediation/{token}          → cliente (portal_remediacion)
- /public/pentester-portal/{token}     → pentester OSCP (portal_pentester_externo)
- /public/verify-auth/{token}          → RSEG firma (autorizar_verificacion_tecnica
                                         + autorizar_pentest_externo)
"""
from __future__ import annotations

import hashlib
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import jwt as pyjwt
from fastapi import (
    APIRouter, Depends, File, HTTPException, Request, UploadFile,
    status as http_status,
)
from fastapi.responses import FileResponse
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.database import get_db
from backend.app.models.operations import ClientInteraction, MagicLink
from backend.app.motors.m08_verification.external.findings_ingester import (
    ingest_external_findings, parse_structured_payload,
)
from backend.app.motors.m08_verification.models import (
    ExternalPentesterHandoff, VerificationFinding, VerificationRun,
)
from backend.app.motors.m08_verification.remediation.guide_generator import (
    finding_to_guide_input, generate_guide,
)
from backend.app.motors.m08_verification.remediation.retest_runner import (
    run_retest,
)
from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m12_magic_link.service import _hash_token, _verify_jwt


router = APIRouter(prefix="/public", tags=["Public Portals (Motor 8 v5.1)"])


# ════════════════════════════════════════════════════════════════════
# Rate limiter in-memory (20 req/min por token + IP)
# ════════════════════════════════════════════════════════════════════

_RATE_WINDOW_SECONDS = 60
_RATE_LIMIT = 20
_RATE_STATE: dict[str, deque[float]] = {}


def _rate_limit_key(token_hash: str, ip: str | None) -> str:
    return f"{token_hash[:16]}|{ip or 'unknown'}"


def _check_rate_limit(token_hash: str, ip: str | None) -> None:
    key = _rate_limit_key(token_hash, ip)
    now = time.monotonic()
    q = _RATE_STATE.setdefault(key, deque(maxlen=_RATE_LIMIT * 2))
    while q and q[0] < now - _RATE_WINDOW_SECONDS:
        q.popleft()
    if len(q) >= _RATE_LIMIT:
        raise HTTPException(
            status_code=http_status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiadas peticiones. Espera un minuto.",
        )
    q.append(now)


# ════════════════════════════════════════════════════════════════════
# Token validation (peek: no incrementa usos)
# ════════════════════════════════════════════════════════════════════

class TokenContext:
    """Resultado de validar un token sin consumirlo."""
    __slots__ = ("magic_link", "purpose", "project_id", "scope", "client_ip", "user_agent")

    def __init__(
        self,
        magic_link: MagicLink,
        purpose: MagicLinkPurpose,
        project_id: uuid.UUID,
        scope: dict[str, Any] | None,
        client_ip: str | None,
        user_agent: str | None,
    ) -> None:
        self.magic_link = magic_link
        self.purpose = purpose
        self.project_id = project_id
        self.scope = scope or {}
        self.client_ip = client_ip
        self.user_agent = user_agent


async def _validate_token_peek(
    token: str,
    request: Request,
    db: AsyncSession,
    *,
    allowed_purposes: set[MagicLinkPurpose],
) -> TokenContext:
    """Valida token JWT + BD sin incrementar usos.

    Comprobaciones (fail-fast con 403 generico para no leak info):
    1. JWT valido (firma + no expirado)
    2. Token hash existe en DB (no soft-deleted)
    3. Purpose del link in allowed_purposes
    4. No revocado
    5. No expirado
    6. usos < max_usos
    """
    try:
        _verify_jwt(token)
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=403, detail="Invalid token")

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    token_hash = _hash_token(token)

    # Admin bypass para lookup cross-tenant por token_hash
    await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
    result = await db.execute(
        select(MagicLink).where(
            MagicLink.token_hash == token_hash,
            MagicLink.deleted_at.is_(None),
        )
    )
    link = result.scalars().first()
    if not link:
        _check_rate_limit(token_hash, client_ip)
        raise HTTPException(status_code=403, detail="Invalid token")

    _check_rate_limit(token_hash, client_ip)

    try:
        purpose = MagicLinkPurpose(link.tipo_operacion)
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid token")
    if purpose not in allowed_purposes:
        logger.warning(
            "Token purpose mismatch: got {} expected one of {}",
            purpose, allowed_purposes,
        )
        raise HTTPException(status_code=403, detail="Invalid token")

    if link.revocado or link.revoked_at is not None:
        raise HTTPException(status_code=403, detail="Invalid token")
    now = datetime.now(timezone.utc)
    expira = link.expira_at
    if expira.tzinfo is None:
        expira = expira.replace(tzinfo=timezone.utc)
    if now > expira:
        raise HTTPException(status_code=403, detail="Invalid token")
    max_usos = link.max_usos or 1
    if link.usos >= max_usos:
        raise HTTPException(status_code=403, detail="Invalid token")

    return TokenContext(
        magic_link=link, purpose=purpose,
        project_id=link.project_id, scope=link.scope,
        client_ip=client_ip, user_agent=user_agent,
    )


async def _log_portal_access(
    db: AsyncSession, ctx: TokenContext, action: str,
    payload: dict | None = None,
) -> None:
    interaction = ClientInteraction(
        magic_link_id=ctx.magic_link.id,
        accion=action,
        ip=ctx.client_ip,
        user_agent=ctx.user_agent,
        timestamp=datetime.now(timezone.utc),
        payload=payload,
    )
    db.add(interaction)
    await db.flush()


async def _load_client_info(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict[str, str]:
    row = (await db.execute(sa_text(
        "SELECT c.nombre, c.cif FROM clients c "
        "JOIN projects p ON p.client_id = c.id "
        "WHERE p.id = :pid"
    ), {"pid": str(project_id)})).first()
    if not row:
        return {"razon_social": "Cliente", "cif": ""}
    return {"razon_social": row[0] or "Cliente", "cif": row[1] or ""}


# ════════════════════════════════════════════════════════════════════
# PORTAL 1 - REMEDIACION CLIENTE
# ════════════════════════════════════════════════════════════════════

REMEDIATION_PURPOSES = {MagicLinkPurpose.PORTAL_REMEDIACION}


@router.get("/remediation/{token}")
async def remediation_portal_data(
    token: str, request: Request, db: AsyncSession = Depends(get_db),
):
    """Datos del portal de remediacion: findings abiertos + progreso."""
    ctx = await _validate_token_peek(
        token, request, db, allowed_purposes=REMEDIATION_PURPOSES,
    )
    await _log_portal_access(db, ctx, "portal_remediation_view")
    await db.commit()

    client = await _load_client_info(db, ctx.project_id)

    stmt = select(VerificationFinding).where(
        VerificationFinding.project_id == ctx.project_id,
        VerificationFinding.deleted_at.is_(None),
        VerificationFinding.zfp_gate5_classification.in_(
            ("confirmed", "probable"),
        ),
    )
    all_findings = list((await db.execute(stmt)).scalars().all())

    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    all_findings.sort(key=lambda f: (
        sev_order.get((f.severity or "info").lower(), 99),
        -float(f.confidence_score or 0),
    ))

    pending = [f for f in all_findings if f.status in ("open", "needs_review")]
    resolved = [f for f in all_findings if f.status == "remediated"]
    total = len(pending) + len(resolved)

    sev_counts_pending = {k: 0 for k in sev_order}
    sev_counts_total = {k: 0 for k in sev_order}
    for f in pending:
        sev_counts_pending[(f.severity or "info").lower()] += 1
    for f in all_findings:
        sev_counts_total[(f.severity or "info").lower()] += 1

    def _to_card(f: VerificationFinding) -> dict:
        guide = generate_guide(
            finding_to_guide_input(f), force_offline=True,
        )
        return {
            "finding_id": str(f.id),
            "title": f.title,
            "severity": f.severity,
            "host_port": f"{f.affected_host}{':' + str(f.affected_port) if f.affected_port else ''}",
            "summary_non_technical": guide.get("resumen_no_tecnico", ""),
            "risk_real": guide.get("riesgo_real", ""),
            "time_estimate": guide.get("tiempo_estimado", ""),
            "requires_restart": bool(guide.get("requiere_reinicio", False)),
            "requires_maintenance_window": bool(
                guide.get("requiere_ventana_mantenimiento", False),
            ),
            "status": f.status,
            "remediated_at": (
                f.remediated_at.isoformat() if f.remediated_at else None
            ),
        }

    return {
        "cliente": client,
        "scope": {
            "project_id": str(ctx.project_id),
            "scan_date": (
                all_findings[0].created_at.isoformat()
                if all_findings and all_findings[0].created_at else None
            ),
        },
        "progress": {
            "total": total,
            "resolved": len(resolved),
            "pending": len(pending),
            "pct": round(100 * len(resolved) / total, 1) if total else 100.0,
        },
        "severity_buckets": {
            sev: {
                "pending": sev_counts_pending.get(sev, 0),
                "total": sev_counts_total.get(sev, 0),
            }
            for sev in ("critical", "high", "medium", "low")
        },
        "pending_findings": [_to_card(f) for f in pending],
        "resolved_findings": [
            {
                "finding_id": str(f.id),
                "title": f.title,
                "severity": f.severity,
                "remediated_at": (
                    f.remediated_at.isoformat() if f.remediated_at else None
                ),
            }
            for f in resolved
        ],
    }


@router.get("/remediation/{token}/findings/{finding_id}/guide")
async def remediation_guide(
    token: str, finding_id: uuid.UUID,
    request: Request, db: AsyncSession = Depends(get_db),
):
    """Guia detallada de remediacion con pasos + comandos + verificacion."""
    ctx = await _validate_token_peek(
        token, request, db, allowed_purposes=REMEDIATION_PURPOSES,
    )
    stmt = select(VerificationFinding).where(
        VerificationFinding.id == finding_id,
        VerificationFinding.project_id == ctx.project_id,
        VerificationFinding.deleted_at.is_(None),
    )
    f = (await db.execute(stmt)).scalars().first()
    if not f:
        raise HTTPException(status_code=404, detail="Finding not found")
    await _log_portal_access(
        db, ctx, "portal_remediation_guide_view",
        {"finding_id": str(finding_id)},
    )
    await db.commit()
    guide = generate_guide(
        finding_to_guide_input(f), force_offline=True,
    )
    return {
        "finding_id": str(f.id),
        "title": f.title,
        "severity": f.severity,
        "host_port": f"{f.affected_host}{':' + str(f.affected_port) if f.affected_port else ''}",
        "guide": guide,
    }


@router.post("/remediation/{token}/findings/{finding_id}/fixed")
async def remediation_mark_fixed(
    token: str, finding_id: uuid.UUID,
    request: Request, db: AsyncSession = Depends(get_db),
):
    """El cliente dice 'ya lo arreglé' → dispara re-test quirurgico."""
    ctx = await _validate_token_peek(
        token, request, db, allowed_purposes=REMEDIATION_PURPOSES,
    )
    stmt = select(VerificationFinding).where(
        VerificationFinding.id == finding_id,
        VerificationFinding.project_id == ctx.project_id,
        VerificationFinding.deleted_at.is_(None),
    )
    f = (await db.execute(stmt)).scalars().first()
    if not f:
        raise HTTPException(status_code=404, detail="Finding not found")

    retest = await run_retest(
        db, f, triggered_by="client_portal",
    )
    await _log_portal_access(
        db, ctx, "portal_remediation_retest",
        {
            "finding_id": str(finding_id),
            "retest_result": retest.result,
        },
    )
    await db.commit()
    return {
        "finding_id": str(f.id),
        "retest_result": retest.result,
        "retest_detail": retest.result_detail,
        "executed_at": retest.executed_at.isoformat() if retest.executed_at else None,
        "finding_status_after": f.status,
        "verified_at": (
            f.remediated_at.isoformat()
            if (f.status == "remediated" and f.remediated_at) else None
        ),
    }


# ════════════════════════════════════════════════════════════════════
# PORTAL 2 - PENTESTER EXTERNO
# ════════════════════════════════════════════════════════════════════

PENTESTER_PURPOSES = {MagicLinkPurpose.PORTAL_PENTESTER_EXTERNO}


async def _load_handoff_for_token(
    db: AsyncSession, ctx: TokenContext,
) -> tuple[ExternalPentesterHandoff, VerificationRun]:
    stmt = (
        select(ExternalPentesterHandoff)
        .where(
            ExternalPentesterHandoff.project_id == ctx.project_id,
            ExternalPentesterHandoff.deleted_at.is_(None),
        )
        .order_by(ExternalPentesterHandoff.created_at.desc())
        .limit(1)
    )
    handoff = (await db.execute(stmt)).scalars().first()
    if not handoff:
        raise HTTPException(status_code=404, detail="Handoff not found")
    run = await db.get(VerificationRun, handoff.run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return handoff, run


@router.get("/pentester-portal/{token}")
async def pentester_portal_data(
    token: str, request: Request, db: AsyncSession = Depends(get_db),
):
    """Datos del portal: engagement + documentos + VPN + estado."""
    ctx = await _validate_token_peek(
        token, request, db, allowed_purposes=PENTESTER_PURPOSES,
    )
    await _log_portal_access(db, ctx, "pentester_portal_view")
    handoff, run = await _load_handoff_for_token(db, ctx)
    client = await _load_client_info(db, ctx.project_id)
    await db.commit()

    scope = run.scope_jsonb or {}
    return {
        "cliente": client,
        "engagement": {
            "run_id": str(run.id),
            "handoff_id": str(handoff.id),
            "category": run.category,
            "mode": run.mode,
            "scope": {
                "targets": scope.get("targets") or [],
                "web_apps": scope.get("web_apps") or [],
                "exclusions": scope.get("exclusions") or [],
                "scan_window": scope.get("scan_window") or "L-V 09:00-18:00 CET",
            },
            "deadline": (
                handoff.deadline.isoformat() if handoff.deadline else None
            ),
            "kickoff_scheduled_at": (
                handoff.kickoff_scheduled_at.isoformat()
                if handoff.kickoff_scheduled_at else None
            ),
            "status": handoff.status,
            "report_received_at": (
                handoff.report_received_at.isoformat()
                if handoff.report_received_at else None
            ),
            "total_findings_received": handoff.total_findings_received,
        },
        "pentester": {
            "name": run.external_pentester_name or "",
            "certification": run.external_pentester_cert or "",
            "email": run.external_pentester_email or "",
        },
        "documents": [
            {
                "name": d.get("name"),
                "path": d.get("path"),
                "hash_sha256": d.get("hash_sha256"),
                "generated_at": d.get("generated_at"),
            }
            for d in (handoff.package_documents or [])
        ],
        "vpn": {
            "config_available": bool(handoff.vpn_config_path),
            "requires_otp_for_creds": True,
        },
        "consultor_contact": {
            "nombre": get_settings().consultor_name,
            "email": get_settings().consultor_email,
            "phone_emergency": get_settings().consultor_phone_emergency,
            "procedimiento": (
                "Si detectas compromiso activo o impacto operativo, "
                "llama INMEDIATAMENTE al telefono de emergencia. "
                "Fuera de compromiso activo, email en horario L-V 9-18h."
            ),
        },
    }


@router.get("/pentester-portal/{token}/documents/{index}")
async def pentester_download_document(
    token: str, index: int,
    request: Request, db: AsyncSession = Depends(get_db),
):
    """Descarga un documento del paquete (indexado por orden)."""
    ctx = await _validate_token_peek(
        token, request, db, allowed_purposes=PENTESTER_PURPOSES,
    )
    handoff, _ = await _load_handoff_for_token(db, ctx)
    docs = handoff.package_documents or []
    if index < 0 or index >= len(docs):
        raise HTTPException(status_code=404, detail="Document not found")
    doc = docs[index]
    rel_path = doc.get("path")
    if not rel_path:
        raise HTTPException(status_code=404, detail="Document path missing")
    root = Path(__file__).resolve().parents[4]
    abs_path = (root / rel_path).resolve()
    # Anti path traversal: must be under var/verification_handoffs/
    allowed_root = (root / "var" / "verification_handoffs").resolve()
    try:
        abs_path.relative_to(allowed_root)
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid path")
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="Document file missing")
    await _log_portal_access(
        db, ctx, "pentester_portal_document_download",
        {"index": index, "name": doc.get("name")},
    )
    await db.commit()
    return FileResponse(
        str(abs_path),
        media_type="text/markdown" if str(abs_path).endswith(".md") else "application/octet-stream",
        filename=abs_path.name,
    )


@router.get("/pentester-portal/{token}/vpn-config")
async def pentester_download_vpn(
    token: str, request: Request, db: AsyncSession = Depends(get_db),
):
    """Descarga la config .ovpn. Las credenciales van por canal aparte."""
    ctx = await _validate_token_peek(
        token, request, db, allowed_purposes=PENTESTER_PURPOSES,
    )
    handoff, _ = await _load_handoff_for_token(db, ctx)
    if not handoff.vpn_config_path:
        raise HTTPException(status_code=404, detail="VPN config not generated")
    abs_path = Path(handoff.vpn_config_path).resolve()
    # §1.7 anti path-traversal: el .ovpn DEBE vivir bajo var/verification_vpn/
    # (mismo guard que /documents/{index}). Antes se servía la ruta absoluta de
    # BD sin validar → un path malicioso (../../etc/...) leería ficheros del host.
    root = Path(__file__).resolve().parents[4]
    allowed_root = (root / "var" / "verification_vpn").resolve()
    try:
        abs_path.relative_to(allowed_root)
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid path")
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="VPN config file missing")
    await _log_portal_access(db, ctx, "pentester_portal_vpn_download")
    await db.commit()
    return FileResponse(
        str(abs_path), media_type="application/x-openvpn-profile",
        filename=f"engagement-{str(handoff.id)[:8]}.ovpn",
    )


class PortalFindingBody(BaseModel):
    title: str = Field(..., min_length=2, max_length=300)
    description: str = Field(..., min_length=2)
    severity: str = Field(..., pattern="^(critical|high|medium|low|info)$")
    affected_host: str = Field(..., min_length=1)
    affected_port: int | None = Field(None, ge=0, le=65535)
    affected_url: str | None = None
    cve_id: str | None = None
    cvss_score: float | None = Field(None, ge=0.0, le=10.0)
    cvss_vector: str | None = None
    cwe_id: str | None = None
    remediation_summary: str | None = None


class PentesterFindingsSubmitBody(BaseModel):
    findings: list[PortalFindingBody] = Field(..., min_length=1)


@router.post("/pentester-portal/{token}/findings")
async def pentester_submit_findings(
    token: str, body: PentesterFindingsSubmitBody,
    request: Request, db: AsyncSession = Depends(get_db),
):
    """Entrega de findings via formulario estructurado (preferente)."""
    ctx = await _validate_token_peek(
        token, request, db, allowed_purposes=PENTESTER_PURPOSES,
    )
    handoff, run = await _load_handoff_for_token(db, ctx)
    # Acepta multiples submissions hasta que 'complete' marque entregado
    if handoff.status == "integrated":
        raise HTTPException(
            status_code=409,
            detail="Handoff ya marcado como integrado; no se admiten mas findings",
        )
    parsed = parse_structured_payload([f.model_dump() for f in body.findings])
    created = await ingest_external_findings(
        db, run.id, parsed, source="structured_form",
    )
    await _log_portal_access(
        db, ctx, "pentester_portal_findings_submit",
        {"count": len(created)},
    )
    await db.commit()
    return {
        "submitted": len(created),
        "total_in_handoff": handoff.total_findings_received or 0,
    }


@router.post("/pentester-portal/{token}/upload-pdf")
async def pentester_upload_pdf(
    token: str, request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Entrega de informe via PDF (fallback si no hay formulario)."""
    ctx = await _validate_token_peek(
        token, request, db, allowed_purposes=PENTESTER_PURPOSES,
    )
    handoff, run = await _load_handoff_for_token(db, ctx)
    if handoff.status == "integrated":
        raise HTTPException(
            status_code=409, detail="Handoff ya integrado",
        )
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(
            status_code=422, detail="Solo se acepta PDF",
        )
    pdf_bytes = await file.read()
    if len(pdf_bytes) > 50 * 1024 * 1024:
        raise HTTPException(
            status_code=422, detail="PDF excede 50MB",
        )
    # Persistir el PDF original
    root = Path(__file__).resolve().parents[4]
    pdf_dir = root / "var" / "verification_handoffs" / str(ctx.project_id) / str(run.id) / "report"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    pdf_path = pdf_dir / f"external_report_{ts}.pdf"
    pdf_path.write_bytes(pdf_bytes)
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()

    run.external_report_original_path = str(pdf_path.relative_to(root))
    # La ingesta LLM del PDF es opcional. Solo si hay ANTHROPIC_API_KEY
    # intentamos parse con Haiku; sino, marcamos 'received' y Marcos
    # integra manualmente via el formulario estructurado.
    from backend.app.motors.m08_verification.external.findings_ingester import (
        parse_pdf_payload,
    )
    findings_parsed = parse_pdf_payload(pdf_bytes)
    ingested: list = []
    if findings_parsed:
        ingested = await ingest_external_findings(
            db, run.id, findings_parsed, source="pdf",
            original_pdf_path=str(pdf_path.relative_to(root)),
        )
    await _log_portal_access(
        db, ctx, "pentester_portal_pdf_upload",
        {
            "filename": file.filename,
            "size_bytes": len(pdf_bytes),
            "hash_sha256": pdf_hash,
            "auto_parsed_findings": len(ingested),
        },
    )
    await db.commit()
    return {
        "status": "received",
        "filename": file.filename,
        "size_bytes": len(pdf_bytes),
        "hash_sha256": pdf_hash,
        "auto_parsed_findings": len(ingested),
    }


@router.post("/pentester-portal/{token}/complete")
async def pentester_complete_engagement(
    token: str, request: Request, db: AsyncSession = Depends(get_db),
):
    """Pentester marca engagement como entregado (irrevocable)."""
    ctx = await _validate_token_peek(
        token, request, db, allowed_purposes=PENTESTER_PURPOSES,
    )
    handoff, _ = await _load_handoff_for_token(db, ctx)
    if handoff.status == "integrated":
        return {"status": "already_integrated"}
    handoff.status = "report_received"
    if handoff.report_received_at is None:
        handoff.report_received_at = datetime.now(timezone.utc)
    await _log_portal_access(db, ctx, "pentester_portal_complete")
    await db.commit()
    return {
        "status": handoff.status,
        "report_received_at": (
            handoff.report_received_at.isoformat()
            if handoff.report_received_at else None
        ),
    }


# ════════════════════════════════════════════════════════════════════
# PORTAL 3 - AUTORIZACION RSEG
# ════════════════════════════════════════════════════════════════════

AUTH_PURPOSES = {
    MagicLinkPurpose.AUTORIZAR_VERIFICACION_TECNICA,
    MagicLinkPurpose.AUTORIZAR_PENTEST_EXTERNO,
}


@router.get("/verify-auth/{token}")
async def verify_auth_portal_data(
    token: str, request: Request, db: AsyncSession = Depends(get_db),
):
    """Scope del run pendiente de autorizacion + declaracion legal."""
    ctx = await _validate_token_peek(
        token, request, db, allowed_purposes=AUTH_PURPOSES,
    )
    await _log_portal_access(db, ctx, "verify_auth_view")

    client = await _load_client_info(db, ctx.project_id)

    # Buscar el run pendiente (status=pending o authorized sin firma previa)
    stmt = (
        select(VerificationRun)
        .where(
            VerificationRun.project_id == ctx.project_id,
            VerificationRun.deleted_at.is_(None),
            VerificationRun.authorization_signed_at.is_(None),
        )
        .order_by(VerificationRun.created_at.desc())
        .limit(1)
    )
    run = (await db.execute(stmt)).scalars().first()
    if not run:
        raise HTTPException(
            status_code=404,
            detail="No hay verificaciones pendientes de autorizacion",
        )
    await db.commit()

    scope = run.scope_jsonb or {}
    tools = run.tools_used or []
    return {
        "cliente": client,
        "run": {
            "run_id": str(run.id),
            "category": run.category,
            "mode": run.mode,
            "scheduled_start": (
                run.scheduled_start.isoformat() if run.scheduled_start else None
            ),
            "scope": {
                "targets": scope.get("targets") or [],
                "web_apps": scope.get("web_apps") or [],
                "exclusions": scope.get("exclusions") or [],
                "scan_window": scope.get("scan_window") or "22:00-06:00 CET",
            },
            "tools": tools or [
                "nmap", "nuclei", "testssl", "dns_checker",
            ],
        },
        "legal_statement": _LEGAL_STATEMENT,
        "requires_otp": bool(ctx.magic_link.otp_hash),
    }


_LEGAL_STATEMENT = (
    "Al autorizar acepto: la ejecucion de las herramientas de verificacion "
    "descritas dentro del alcance y ventana especificados; comprendo que "
    "estos tests pueden generar registros en los sistemas monitorizados; "
    "asumo responsabilidad como responsable de seguridad de la informacion "
    "del cliente. La autorizacion queda firmada electronicamente con sello "
    "de tiempo y es inmutable."
)


class VerifyAuthOTPRequest(BaseModel):
    delivery_method: Literal["email", "sms"] = "email"


@router.post("/verify-auth/{token}/request-otp")
async def verify_auth_request_otp(
    token: str, body: VerifyAuthOTPRequest,
    request: Request, db: AsyncSession = Depends(get_db),
):
    """Solicitar (re)envio del OTP al RSEG."""
    ctx = await _validate_token_peek(
        token, request, db, allowed_purposes=AUTH_PURPOSES,
    )
    if not ctx.magic_link.otp_hash:
        raise HTTPException(
            status_code=422,
            detail="Este enlace no requiere OTP",
        )
    # El OTP original se envio al generar el link; aqui solo se registra
    # la solicitud de reenvio. El reenvio real lo hace M12/M18.
    await _log_portal_access(
        db, ctx, "verify_auth_otp_requested",
        {"delivery_method": body.delivery_method},
    )
    await db.commit()
    return {
        "delivery_method": body.delivery_method,
        "delivered_to": ctx.magic_link.recipient_email,
        "expires_in_seconds": 600,
    }


class VerifyAuthSubmitRequest(BaseModel):
    otp: str | None = Field(None, min_length=4, max_length=10)
    accepted_legal: bool = Field(
        ..., description="Checkbox 'He leido y acepto'",
    )


@router.post("/verify-auth/{token}/submit")
async def verify_auth_submit(
    token: str, body: VerifyAuthSubmitRequest,
    request: Request, db: AsyncSession = Depends(get_db),
):
    """El RSEG firma la autorizacion.

    Valida OTP, incrementa usos (consume real), marca run como authorized,
    registra timestamp y hash de la firma. Devuelve ID de run + hash.
    """
    if not body.accepted_legal:
        raise HTTPException(
            status_code=422,
            detail="Es obligatorio aceptar la declaracion legal",
        )
    ctx = await _validate_token_peek(
        token, request, db, allowed_purposes=AUTH_PURPOSES,
    )
    link = ctx.magic_link

    # OTP check (si aplica)
    if link.otp_hash:
        if not body.otp:
            raise HTTPException(status_code=422, detail="Falta OTP")
        from backend.app.motors.m12_magic_link.service import (
            OTP_FAILURE_THRESHOLD, _hash_otp,
        )
        if link.otp_failures >= OTP_FAILURE_THRESHOLD:
            raise HTTPException(status_code=403, detail="OTP bloqueado")
        if _hash_otp(body.otp) != link.otp_hash:
            link.otp_failures += 1
            await _log_portal_access(
                db, ctx, "verify_auth_otp_failed",
                {"attempt": link.otp_failures},
            )
            await db.commit()
            raise HTTPException(status_code=403, detail="OTP invalido")

    stmt = (
        select(VerificationRun)
        .where(
            VerificationRun.project_id == ctx.project_id,
            VerificationRun.deleted_at.is_(None),
            VerificationRun.authorization_signed_at.is_(None),
        )
        .order_by(VerificationRun.created_at.desc())
        .limit(1)
    )
    run = (await db.execute(stmt)).scalars().first()
    if not run:
        raise HTTPException(status_code=404, detail="Run no encontrado")

    now = datetime.now(timezone.utc)
    run.authorized_by = link.recipient_email or "RSEG (firma via portal)"
    run.authorization_signed_at = now
    run.authorization_magic_link_id = link.id
    if run.status == "pending":
        run.status = "authorized"

    # Incrementar usos (single-use normal)
    link.usos += 1

    signature_payload = f"{run.id}|{link.id}|{now.isoformat()}"
    signature_hash = hashlib.sha256(
        signature_payload.encode("utf-8"),
    ).hexdigest()

    await _log_portal_access(
        db, ctx, "verify_auth_signed",
        {
            "run_id": str(run.id),
            "signature_hash": signature_hash,
            "signed_at": now.isoformat(),
        },
    )
    await db.commit()

    fecha_prevista_fin = scope = None  # noqa: F841
    return {
        "status": "signed",
        "run_id": str(run.id),
        "signed_at": now.isoformat(),
        "signature_hash": signature_hash,
        "expected_completion": (
            run.scheduled_start.isoformat() if run.scheduled_start else None
        ),
    }
