"""M09 Auditor Portal public_api · Sesión 3B-2B.6 CLUSTER 2 Phase 4.

Mirror del pattern m08_verification.public_api (pentester-portal · remediation ·
verify-auth) · expone endpoints `/public/auditor-portal/{token}/*` para auditor
ENAC consume magic-link gated read-only views.

Architecture decisions (audit Phase 0 DIM 6):
- Separate route group desde admin / cliente portals · neutral chrome
- Stateless per-request validation · NO session cookie (token-bounded)
- _validate_token_peek pattern reused · rate limit + purpose enforce
- Audit log emit hash chain inmutable (Sub-atom 5.A RLS protected)

Endpoints scope Phase 4 (token gate + metadata only):
- GET /public/auditor-portal/{token}              · project metadata + cliente branding
- POST /public/auditor-portal/{token}/session     · session.start emit + consume usos

Phase 5 endpoints añadidos en commits siguientes (read-only views):
- GET /public/auditor-portal/{token}/dda
- GET /public/auditor-portal/{token}/magerit
- GET /public/auditor-portal/{token}/plan
- GET /public/auditor-portal/{token}/evidence
- GET /public/auditor-portal/{token}/audit-log
- GET /public/auditor-portal/{token}/e041
- GET /public/auditor-portal/{token}/pentest
- GET /public/auditor-portal/{token}/documents
- GET /public/auditor-portal/{token}/dossier.zip (signed Cluster 1 Phase 1 reused)
"""
from __future__ import annotations

import time
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any

import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException, Request, status as http_status
from loguru import logger
from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models.operations import ClientInteraction, MagicLink
from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m12_magic_link.service import _hash_token, _verify_jwt


router = APIRouter(
    prefix="/public/auditor-portal",
    tags=["Public Portal · Auditor ENAC (Motor 9)"],
)


AUDITOR_PORTAL_PURPOSES = {MagicLinkPurpose.AUDITOR_PORTAL_ENAC}


# ── Rate limit (mirror M08 pattern) ─────────────────────────────────────

_RATE_LIMIT_WINDOW_SECONDS = 60
_RATE_LIMIT_MAX_FAILURES = 10
_failed_attempts: dict[str, deque[float]] = {}


def _check_rate_limit(token_hash: str, client_ip: str | None) -> None:
    """Rate limit attempts per (token_hash, IP) · 10 fails/60s threshold."""
    key = f"{token_hash}:{client_ip or 'unknown'}"
    now = time.time()
    window = _failed_attempts.setdefault(key, deque())
    while window and now - window[0] > _RATE_LIMIT_WINDOW_SECONDS:
        window.popleft()
    window.append(now)
    if len(window) > _RATE_LIMIT_MAX_FAILURES:
        logger.warning(
            "Auditor portal rate limit · token_hash={} ip={}",
            token_hash[:8], client_ip,
        )
        raise HTTPException(
            status_code=http_status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limited",
        )


# ── Token context ──────────────────────────────────────────────────────

class TokenContext:
    """Container per request post-validation · binding token → magic_link."""

    def __init__(
        self, *,
        magic_link: MagicLink,
        purpose: MagicLinkPurpose,
        project_id: uuid.UUID,
        scope: dict | None,
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
    token: str, request: Request, db: AsyncSession,
) -> TokenContext:
    """Mirror M08 _validate_token_peek · AUDITOR_PORTAL_ENAC purpose only.

    Comprobaciones fail-fast con 403 genérico (NO leak info):
    1. JWT válido (firma + no expirado)
    2. token_hash existe en DB no soft-deleted
    3. Purpose == AUDITOR_PORTAL_ENAC
    4. NO revocado · NO expirado · usos < max_usos
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

    # NO rate-limit en el path VÁLIDO: un auditor ENAC legítimo navega muchas
    # vistas del dossier (cada carga = varias peeks) y a 10/60s recibía
    # "Acceso no disponible · Rate limited" a media auditoría. El rate limit
    # (`_failed_attempts`) solo debe frenar intentos con token INVÁLIDO (arriba).
    # Defecto real detectado en la galería de la simulación full-cloth.

    try:
        purpose = MagicLinkPurpose(link.tipo_operacion)
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid token")
    if purpose not in AUDITOR_PORTAL_PURPOSES:
        logger.warning(
            "Auditor portal purpose mismatch: got {} expected {}",
            purpose, AUDITOR_PORTAL_PURPOSES,
        )
        raise HTTPException(status_code=403, detail="Invalid token")

    if link.revocado or link.revoked_at is not None:
        raise HTTPException(status_code=410, detail="Token revoked")
    now = datetime.now(timezone.utc)
    expira = link.expira_at
    if expira.tzinfo is None:
        expira = expira.replace(tzinfo=timezone.utc)
    if now > expira:
        raise HTTPException(status_code=410, detail="Token expired")
    max_usos = link.max_usos or 1
    if link.usos >= max_usos:
        raise HTTPException(status_code=410, detail="Token usage exhausted")

    return TokenContext(
        magic_link=link, purpose=purpose,
        project_id=link.project_id, scope=link.scope,
        client_ip=client_ip, user_agent=user_agent,
    )


async def emit_auditor_event(
    db: AsyncSession,
    ctx: TokenContext,
    action: str,
    *,
    target: str | None = None,
    metadata: dict | None = None,
) -> None:
    """Emit auditor portal action audit_log entry · canonical helper Phase 6.

    Sesión 3B-2B.6 CLUSTER 2 Phase 6 · single source of truth para auditor event
    emission cross-motor (consumed by Phase 4 + Phase 5 + Phase 6 download wire-in).

    Persists 2 rows in 1 transaction:
    1. ClientInteraction (portal-level per token · ip · UA · payload)
    2. audit_log inmutable hash chain entry tagged con project_id + client_id
       (Sub-atom 5.A RLS isolation enforced · R6 hash chain inviolable preserved)

    payload_new schema:
        magic_link_id: str (token reference)
        scope: dict (magic_link.scope · purpose-specific metadata)
        target: str | None (view section · download asset type)
        ...metadata (caller-supplied custom fields)
    """
    interaction_payload: dict = dict(metadata or {})
    if target is not None:
        interaction_payload["target"] = target

    interaction = ClientInteraction(
        magic_link_id=ctx.magic_link.id,
        accion=action,
        ip=ctx.client_ip,
        user_agent=ctx.user_agent,
        timestamp=datetime.now(timezone.utc),
        payload=interaction_payload or None,
    )
    db.add(interaction)
    await db.flush()

    auditor_email = (
        ctx.magic_link.recipient_email
        or (ctx.scope or {}).get("auditor_email")
        or "auditor"
    )
    client_id_row = (await db.execute(sa_text(
        "SELECT client_id FROM projects WHERE id = :pid"
    ), {"pid": str(ctx.project_id)})).first()
    client_id_val = str(client_id_row[0]) if client_id_row else None

    audit_payload: dict = {
        "magic_link_id": str(ctx.magic_link.id),
        "scope": ctx.scope or {},
    }
    if target is not None:
        audit_payload["target"] = target
    if metadata:
        audit_payload.update(metadata)

    await db.execute(sa_text(
        "INSERT INTO audit_log (id, tabla, registro_id, accion, usuario, "
        "project_id, client_id, payload_new, timestamp) "
        "VALUES (gen_random_uuid(), 'auditor_portal', :rid, :accion, :auditor, "
        ":pid, :cid, :payload, now())"
    ), {
        "rid": str(ctx.magic_link.id),
        "accion": action,
        "auditor": auditor_email[:255],
        "pid": str(ctx.project_id),
        "cid": client_id_val,
        "payload": __import__("json").dumps(audit_payload),
    })
    await db.flush()


async def _log_portal_access(
    db: AsyncSession, ctx: TokenContext, action: str,
    payload: dict | None = None,
) -> None:
    """Backward-compat wrapper Phase 4 · delegates to emit_auditor_event.

    Caller pasa payload dict completo (incluye 'target' inside) · split en
    target (extraído si present) + metadata (rest) para canonical schema.
    """
    target = None
    metadata = dict(payload or {})
    if "target" in metadata:
        target = metadata.pop("target")
    await emit_auditor_event(
        db, ctx, action, target=target, metadata=metadata or None,
    )


async def _load_client_info(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict[str, str]:
    row = (await db.execute(sa_text(
        "SELECT c.id, c.nombre, c.cif, c.primary_color, c.secondary_color, "
        "c.footer_text, c.logo_path FROM clients c "
        "JOIN projects p ON p.client_id = c.id "
        "WHERE p.id = :pid"
    ), {"pid": str(project_id)})).first()
    if not row:
        return {
            "client_id": "",
            "razon_social": "Cliente", "cif": "",
            "primary_color": "", "secondary_color": "",
            "footer_text": "", "has_logo": False,
        }
    return {
        "client_id": str(row[0]),
        "razon_social": row[1] or "Cliente",
        "cif": row[2] or "",
        "primary_color": row[3] or "",
        "secondary_color": row[4] or "",
        "footer_text": row[5] or "",
        "has_logo": bool(row[6]),
    }


async def _load_project_info(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict[str, Any]:
    row = (await db.execute(sa_text(
        "SELECT id, nombre, categoria_objetivo, fase, lifecycle_state, "
        "certified_at, audit_passed_at, audit_result, audit_report_ref "
        "FROM projects WHERE id = :pid"
    ), {"pid": str(project_id)})).first()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "id": str(row[0]),
        "nombre": row[1] or "Proyecto",
        "categoria": row[2] or "MEDIA",
        "fase": row[3],
        "lifecycle_state": row[4],
        "certified_at": row[5].isoformat() if row[5] else None,
        "audit_passed_at": row[6].isoformat() if row[6] else None,
        "audit_result": row[7],
        "audit_report_ref": row[8],
    }


# ══════════════════════════════════════════════════════════════════════
# Endpoint principal · metadata + session start emit
# ══════════════════════════════════════════════════════════════════════

@router.get("/{token}")
async def auditor_portal_metadata(
    token: str, request: Request, db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Project metadata + cliente branding + audit-passed status para landing.

    Endpoint stateless · token-bounded · returns 403 si token inválido · 410 si
    revocado/expirado/exhausto. NO incrementa usos (peek only · Phase 5 views
    pueden emit additional events sin consumir uso adicional · token TTL gate).

    Emits audit_log row · auditor_portal.view (Sub-atom 5.A RLS isolation).
    """
    ctx = await _validate_token_peek(token, request, db)
    await _log_portal_access(db, ctx, "auditor_portal.view")
    cliente = await _load_client_info(db, ctx.project_id)
    project = await _load_project_info(db, ctx.project_id)
    await db.commit()

    return {
        "cliente": cliente,
        "project": project,
        "token_meta": {
            "expires_at": ctx.magic_link.expira_at.isoformat()
                if ctx.magic_link.expira_at else None,
            "max_uses": ctx.magic_link.max_usos,
            "current_uses": ctx.magic_link.usos,
        },
        "available_sections": [
            "summary", "dda", "magerit", "plan", "evidence",
            "e041", "audit-log", "pentest", "documents",
            # CLUSTER 3 · faltaban en el contrato de metadata (el FE las
            # renderiza igual · se añaden por coherencia con AuditorPortalChrome).
            "audit/dda-evidence-gaps", "draft-report",
        ],
    }


@router.post("/{token}/session")
async def auditor_portal_session_start(
    token: str, request: Request, db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Emit auditor.session.start event + increment usos (formal session begin).

    Llamado UNA VEZ desde frontend tras consume OTP en landing page · marca
    session start formal · subsequent GETs en Phase 5 views peek-only.
    """
    ctx = await _validate_token_peek(token, request, db)
    # Increment usos (formal session start consumes 1 use)
    ctx.magic_link.usos = (ctx.magic_link.usos or 0) + 1
    await _log_portal_access(db, ctx, "auditor.session.start")
    await db.flush()
    await db.commit()

    return {
        "status": "ok",
        "session_started_at": datetime.now(timezone.utc).isoformat(),
        "remaining_uses": (ctx.magic_link.max_usos or 1) - ctx.magic_link.usos,
    }


# ══════════════════════════════════════════════════════════════════════
# Phase 5 read-only views · Cluster A · Summary + DdA + MAGERIT
# ══════════════════════════════════════════════════════════════════════
#
# Architecture (mirror metadata pattern):
# - Each endpoint validates token via _validate_token_peek (NO consume uso)
# - Emits audit_log row · auditor_portal.view target=<section> (Sub-atom 5.A)
# - Returns JSON read-only · NO write actions exposed · NO admin nav leaked
# - SET LOCAL ROLE fulkro_app_bypassrls applied in _validate_token_peek persists scope to
#   request transaction → cross-tenant data fetch authorized solely by token
# - Download endpoints emit auditor_portal.download target=<asset>
#
# Section endpoints share helper signatures · payload schema documented inline.

@router.get("/{token}/summary")
async def auditor_portal_summary(
    token: str, request: Request, db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Project summary read-only · categoría + lifecycle + audit status.

    Phase 5.1 · friendly Spanish R29 tone · top-level overview con
    cliente razón social + categoría ENS + key dates.
    """
    ctx = await _validate_token_peek(token, request, db)
    await _log_portal_access(
        db, ctx, "auditor_portal.view", payload={"target": "summary"},
    )

    cliente = await _load_client_info(db, ctx.project_id)
    project = await _load_project_info(db, ctx.project_id)

    # Counts agregados read-only para overview
    counts = (await db.execute(sa_text(
        "SELECT "
        "(SELECT count(*) FROM dda_entries WHERE project_id = :pid "
        "  AND deleted_at IS NULL) AS dda_total, "
        "(SELECT count(*) FROM evidence WHERE project_id = :pid "
        "  AND deleted_at IS NULL) AS evidence_total, "
        "(SELECT count(*) FROM magerit_analysis WHERE project_id = :pid "
        "  AND deleted_at IS NULL) AS magerit_analyses, "
        "(SELECT count(*) FROM verification_runs WHERE project_id = :pid "
        "  AND deleted_at IS NULL) AS pentest_runs"
    ), {"pid": str(ctx.project_id)})).first()

    await db.commit()
    return {
        "cliente": cliente,
        "project": project,
        "counts": {
            "dda_entries": counts[0] if counts else 0,
            "evidence_files": counts[1] if counts else 0,
            "magerit_analyses": counts[2] if counts else 0,
            "pentest_runs": counts[3] if counts else 0,
        },
    }


@router.get("/{token}/dda")
async def auditor_portal_dda(
    token: str, request: Request, db: AsyncSession = Depends(get_db),
    family: str | None = None,
) -> dict[str, Any]:
    """DdA read-only · 73 medidas applicable + justificación per medida.

    Phase 5.2 · pre-filter aplicabilidad in ('aplica', 'aplica_aceptado',
    'aplica_compensa', 'aplica_refuerza') · NO mostrar no-aplica con justif
    sin medida. Cliente review status visible para auditor inspection.
    Optional `family` filter org · op · mp.
    """
    ctx = await _validate_token_peek(token, request, db)
    await _log_portal_access(
        db, ctx, "auditor_portal.view", payload={"target": "dda"},
    )

    base_query = (
        "SELECT e.id, m.codigo, m.nombre, m.familia, "
        "m.descripcion, m.requisito_base, m.categoria_minima, "
        "e.aplicabilidad, e.justificacion_no_aplica, "
        "e.estado_implementacion, e.observaciones, "
        "e.aprobado_por, e.fecha_aprobacion, "
        "e.client_review_status, e.client_review_note, e.client_reviewed_at "
        "FROM dda_entries e "
        "JOIN ens_measures m ON m.id = e.measure_id "
        "WHERE e.project_id = :pid AND e.deleted_at IS NULL"
    )
    params = {"pid": str(ctx.project_id)}
    if family:
        base_query += " AND m.familia = :fam"
        params["fam"] = family
    base_query += " ORDER BY m.codigo"

    rows = (await db.execute(sa_text(base_query), params)).all()
    medidas = [
        {
            "id": str(row[0]),
            "codigo": row[1],
            "nombre": row[2],
            "familia": row[3],
            "descripcion": row[4],
            "requisito_base": row[5],
            "categoria_minima": row[6],
            "aplicabilidad": row[7],
            "justificacion_no_aplica": row[8],
            "estado_implementacion": row[9],
            "observaciones": row[10],
            "aprobado_por": row[11],
            "fecha_aprobacion": row[12].isoformat() if row[12] else None,
            "client_review_status": row[13],
            "client_review_note": row[14],
            "client_reviewed_at": row[15].isoformat() if row[15] else None,
        }
        for row in rows
    ]

    # Detect signed state of DdA
    signed_row = (await db.execute(sa_text(
        "SELECT created_at FROM dda_project_signatures "
        "WHERE project_id = :pid LIMIT 1"
    ), {"pid": str(ctx.project_id)})).first()

    await db.commit()
    return {
        "project_id": str(ctx.project_id),
        "filter_family": family,
        "total": len(medidas),
        "is_signed": signed_row is not None,
        "signed_at": signed_row[0].isoformat() if signed_row else None,
        "medidas": medidas,
    }


@router.get("/{token}/magerit")
async def auditor_portal_magerit(
    token: str, request: Request, db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """MAGERIT read-only · assets + threats + risks aggregated per analysis.

    Phase 5.3 · summary + per-asset summary + per-threat assessment.
    NO edit capabilities · NO admin orchestration · pure inspection.
    Cliente review status visible.
    """
    ctx = await _validate_token_peek(token, request, db)
    await _log_portal_access(
        db, ctx, "auditor_portal.view", payload={"target": "magerit"},
    )

    # Latest analysis (assume 1 per project · multi-analysis future scope)
    analysis_row = (await db.execute(sa_text(
        "SELECT id, name, status, created_at, snapshot_frozen_at "
        "FROM magerit_analysis "
        "WHERE project_id = :pid AND deleted_at IS NULL "
        "ORDER BY created_at DESC LIMIT 1"
    ), {"pid": str(ctx.project_id)})).first()

    if not analysis_row:
        await db.commit()
        return {
            "project_id": str(ctx.project_id),
            "analysis": None,
            "assets": [],
            "risks_total": 0,
        }

    analysis_id = analysis_row[0]
    analysis = {
        "id": str(analysis_id),
        "name": analysis_row[1],
        "status": analysis_row[2],
        "created_at": analysis_row[3].isoformat() if analysis_row[3] else None,
        "frozen_at": analysis_row[4].isoformat() if analysis_row[4] else None,
    }

    # Assets · tipo + DICAT visible + cliente review status
    asset_rows = (await db.execute(sa_text(
        "SELECT a.id, a.code, a.name, a.asset_type_code, a.owner, "
        "a.value_d, a.value_i, a.value_c, a.value_a, a.value_t, "
        "a.accumulated_d, a.accumulated_i, a.accumulated_c, "
        "a.accumulated_a, a.accumulated_t, "
        "a.client_review_status, a.client_reviewed_at "
        "FROM magerit_assets a "
        "WHERE a.analysis_id = :aid AND a.deleted_at IS NULL "
        "ORDER BY a.code"
    ), {"aid": str(analysis_id)})).all()
    assets = [
        {
            "id": str(row[0]),
            "code": row[1],
            "name": row[2],
            "asset_type_code": row[3],
            "owner": row[4],
            "valuation": {
                "d": row[5], "i": row[6], "c": row[7], "a": row[8], "t": row[9],
            },
            "accumulated": {
                "d": float(row[10]) if row[10] is not None else None,
                "i": float(row[11]) if row[11] is not None else None,
                "c": float(row[12]) if row[12] is not None else None,
                "a": float(row[13]) if row[13] is not None else None,
                "t": float(row[14]) if row[14] is not None else None,
            },
            "client_review_status": row[15],
            "client_reviewed_at": row[16].isoformat() if row[16] else None,
        }
        for row in asset_rows
    ]

    # Risks aggregated · count by severity
    # magerit_threat_assessment NO tiene soft-delete (sin columna deleted_at) →
    # filtrar por deleted_at reventaba la vista del auditor (500). Defecto real
    # detectado en la sim full-cloth (auditor portal · vista MAGERIT).
    risk_counts_row = (await db.execute(sa_text(
        "SELECT count(*) FROM magerit_threat_assessment "
        "WHERE analysis_id = :aid"
    ), {"aid": str(analysis_id)})).first()

    await db.commit()
    return {
        "project_id": str(ctx.project_id),
        "analysis": analysis,
        "assets": assets,
        "risks_total": risk_counts_row[0] if risk_counts_row else 0,
    }


# ══════════════════════════════════════════════════════════════════════
# Phase 5 read-only views · Cluster B · Plan + Evidence + E-041
# ══════════════════════════════════════════════════════════════════════

@router.get("/{token}/plan")
async def auditor_portal_plan(
    token: str, request: Request, db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Plan adecuación read-only · Gantt + WBS tasks + critical path.

    Phase 5.4 · ProjectPlan + WbsTask tables · responsables + dependencies +
    deliverable_e_code visible · NO edit capabilities · pure inspection.
    """
    ctx = await _validate_token_peek(token, request, db)
    await _log_portal_access(
        db, ctx, "auditor_portal.view", payload={"target": "plan"},
    )

    plan_row = (await db.execute(sa_text(
        "SELECT id, version, categoria, start_date, end_date_estimated, "
        "end_date_actual, total_effort_marcos_hours, total_effort_platform_hours, "
        "total_duration_weeks, critical_path_length_weeks, estado, "
        "baseline_date, aprobado_at "
        "FROM project_plans "
        "WHERE project_id = :pid AND deleted_at IS NULL "
        "ORDER BY version DESC LIMIT 1"
    ), {"pid": str(ctx.project_id)})).first()

    if not plan_row:
        await db.commit()
        return {
            "project_id": str(ctx.project_id),
            "plan": None,
            "tasks": [],
        }

    plan_id = plan_row[0]
    plan = {
        "id": str(plan_id),
        "version": plan_row[1],
        "categoria": plan_row[2],
        "start_date": plan_row[3].isoformat() if plan_row[3] else None,
        "end_date_estimated": plan_row[4].isoformat() if plan_row[4] else None,
        "end_date_actual": plan_row[5].isoformat() if plan_row[5] else None,
        "total_effort_marcos_hours": (
            float(plan_row[6]) if plan_row[6] is not None else None
        ),
        "total_effort_platform_hours": (
            float(plan_row[7]) if plan_row[7] is not None else None
        ),
        "total_duration_weeks": plan_row[8],
        "critical_path_length_weeks": plan_row[9],
        "estado": plan_row[10],
        "baseline_date": plan_row[11].isoformat() if plan_row[11] else None,
        "aprobado_at": plan_row[12].isoformat() if plan_row[12] else None,
    }

    task_rows = (await db.execute(sa_text(
        "SELECT id, task_code, task_name, phase, start_date, end_date, "
        "duration_days, effort_marcos_hours, responsible, "
        "deliverable_e_code, status, is_critical_path, progress_pct "
        "FROM wbs_tasks "
        "WHERE project_plan_id = :pid AND deleted_at IS NULL "
        "ORDER BY task_code"
    ), {"pid": str(plan_id)})).all()
    tasks = [
        {
            "id": str(row[0]),
            "task_code": row[1],
            "task_name": row[2],
            "phase": row[3],
            "start_date": row[4].isoformat() if row[4] else None,
            "end_date": row[5].isoformat() if row[5] else None,
            "duration_days": row[6],
            "effort_marcos_hours": (
                float(row[7]) if row[7] is not None else None
            ),
            "responsible": row[8],
            "deliverable_e_code": row[9],
            "status": row[10],
            "is_critical_path": bool(row[11]) if row[11] is not None else False,
            "progress_pct": row[12] or 0,
        }
        for row in task_rows
    ]

    await db.commit()
    return {
        "project_id": str(ctx.project_id),
        "plan": plan,
        "tasks": tasks,
    }


@router.get("/{token}/evidence")
async def auditor_portal_evidence(
    token: str, request: Request, db: AsyncSession = Depends(get_db),
    measure_code: str | None = None,
) -> dict[str, Any]:
    """Evidence vault read-only · per medida groupings + counts + signed hashes.

    Phase 5.5 · evidence table · measure_code grouping · filter measure_code.
    Sólo evidencias vigentes · NO deleted · scan_status clean | quarantined visible.
    """
    ctx = await _validate_token_peek(token, request, db)
    await _log_portal_access(
        db, ctx, "auditor_portal.view", payload={"target": "evidence"},
    )

    # Counts per medida (grouped)
    grouped_query = (
        "SELECT measure_code, count(*) AS total "
        "FROM evidence "
        "WHERE project_id = :pid AND deleted_at IS NULL "
        "AND measure_code IS NOT NULL "
        "GROUP BY measure_code ORDER BY measure_code"
    )
    grouped_rows = (await db.execute(sa_text(grouped_query), {
        "pid": str(ctx.project_id),
    })).all()
    grouped = [
        {"measure_code": row[0], "total": row[1]} for row in grouped_rows
    ]

    # Item list (optionally filtered)
    base_query = (
        "SELECT id, measure_code, evidence_type_id, nombre_tipo, "
        "fichero_nombre_original, fichero_mime_type, "
        "fichero_tamano_bytes, fecha_evidencia, fecha_caducidad, "
        "vigente, scan_status, hash_sha256 "
        "FROM evidence "
        "WHERE project_id = :pid AND deleted_at IS NULL"
    )
    params = {"pid": str(ctx.project_id)}
    if measure_code:
        base_query += " AND measure_code = :mc"
        params["mc"] = measure_code
    base_query += " ORDER BY fecha_evidencia DESC NULLS LAST, created_at DESC"

    item_rows = (await db.execute(sa_text(base_query), params)).all()
    items = [
        {
            "id": str(row[0]),
            "measure_code": row[1],
            "evidence_type_id": row[2],
            "nombre_tipo": row[3],
            "fichero_nombre_original": row[4],
            "fichero_mime_type": row[5],
            "fichero_tamano_bytes": row[6],
            "fecha_evidencia": row[7].isoformat() if row[7] else None,
            "fecha_caducidad": row[8].isoformat() if row[8] else None,
            "vigente": bool(row[9]),
            "scan_status": row[10],
            "hash_sha256": row[11],
        }
        for row in item_rows
    ]

    await db.commit()
    return {
        "project_id": str(ctx.project_id),
        "filter_measure_code": measure_code,
        "total_items": len(items),
        "grouped_by_measure": grouped,
        "items": items,
    }


@router.get("/{token}/e041")
async def auditor_portal_e041(
    token: str, request: Request, db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """E-041 declaración conformidad read-only · firma Ed25519 verify status.

    Phase 5.6 · basic_declarations row · signed_at + signed_hash + published_url
    + responsible info + cliente review status (ClientReviewMixinB).
    Multiple types soportados: initial (BÁSICA · firma cliente) ·
    commitment_pre_certification (MEDIA/ALTA pre-auditor).
    """
    ctx = await _validate_token_peek(token, request, db)
    await _log_portal_access(
        db, ctx, "auditor_portal.view", payload={"target": "e041"},
    )

    rows = (await db.execute(sa_text(
        "SELECT id, declaration_type, status, "
        "published_evidence_url, responsible_person_name, "
        "responsible_person_email, signed_at, signed_hash, "
        "anniversary_year, created_at, "
        "client_reviewed_at, client_concerns_note "
        "FROM basic_declarations "
        "WHERE project_id = :pid "
        "ORDER BY created_at DESC"
    ), {"pid": str(ctx.project_id)})).all()

    declarations = [
        {
            "id": str(row[0]),
            "declaration_type": row[1],
            "status": row[2],
            "published_evidence_url": row[3],
            "responsible_person_name": row[4],
            "responsible_person_email": row[5],
            "signed_at": row[6].isoformat() if row[6] else None,
            "signed_hash": row[7],
            "anniversary_year": row[8],
            "created_at": row[9].isoformat() if row[9] else None,
            "client_reviewed_at": row[10].isoformat() if row[10] else None,
            "client_concerns_note": row[11],
            "is_signed": bool(row[6] and row[7]),
        }
        for row in rows
    ]

    await db.commit()
    return {
        "project_id": str(ctx.project_id),
        "total": len(declarations),
        "declarations": declarations,
    }


# ══════════════════════════════════════════════════════════════════════
# Phase 5 read-only views · Cluster C · Audit Log + Pentest + Documents
# ══════════════════════════════════════════════════════════════════════

@router.get("/{token}/audit-log")
async def auditor_portal_audit_log(
    token: str, request: Request, db: AsyncSession = Depends(get_db),
    accion: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Audit log inmutable read-only · hash chain trazabilidad ENS.

    Phase 5.7 · audit_log rows filtered por project_id explícito (auditor scope
    bounded · NO cross-project leak). Visible: accion + tabla + usuario +
    timestamp + payload_new + hash_current. Hash chain inviolable preserved
    (R6) · trigger fn_audit_log_verify_chain available para ENAC verify.
    """
    ctx = await _validate_token_peek(token, request, db)
    await _log_portal_access(
        db, ctx, "auditor_portal.view", payload={"target": "audit_log"},
    )

    safe_limit = max(1, min(limit, 500))
    base_query = (
        "SELECT id, seq, tabla, accion, usuario, timestamp, "
        "payload_new, hash_current "
        "FROM audit_log "
        "WHERE project_id = :pid"
    )
    params: dict[str, Any] = {"pid": str(ctx.project_id)}
    if accion:
        base_query += " AND accion = :accion"
        params["accion"] = accion
    base_query += " ORDER BY seq DESC LIMIT :lim"
    params["lim"] = safe_limit

    rows = (await db.execute(sa_text(base_query), params)).all()
    entries = [
        {
            "id": str(row[0]),
            "seq": row[1],
            "tabla": row[2],
            "accion": row[3],
            "usuario": row[4],
            "timestamp": row[5].isoformat() if row[5] else None,
            "payload_new": row[6],
            "hash_current": (row[7][:16] + "…") if row[7] else None,
        }
        for row in rows
    ]

    # Verify chain status para auditor confidence
    total_row = (await db.execute(sa_text(
        "SELECT count(*) FROM audit_log WHERE project_id = :pid"
    ), {"pid": str(ctx.project_id)})).first()
    total_count = total_row[0] if total_row else 0

    await db.commit()
    return {
        "project_id": str(ctx.project_id),
        "filter_accion": accion,
        "total_for_project": total_count,
        "returned": len(entries),
        "limit": safe_limit,
        "entries": entries,
    }


@router.get("/{token}/pentest")
async def auditor_portal_pentest(
    token: str, request: Request, db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Pentest M08 verification runs read-only · findings counts per run.

    Phase 5.8 · verification_runs rows ordered by created_at DESC · aggregated
    counts (critical · high · medium · low · info) + security_score.
    BÁSICA/MEDIA graceful empty if no runs · ALTA owns full pentest.
    """
    ctx = await _validate_token_peek(token, request, db)
    await _log_portal_access(
        db, ctx, "auditor_portal.view", payload={"target": "pentest"},
    )

    rows = (await db.execute(sa_text(
        "SELECT id, category, mode, status, scheduled_start, "
        "completed_at, total_findings, confirmed_findings, "
        "critical_count, high_count, medium_count, low_count, "
        "info_count, security_score, external_pentester_name, "
        "external_pentester_cert, created_at "
        "FROM verification_runs "
        "WHERE project_id = :pid AND deleted_at IS NULL "
        "ORDER BY created_at DESC"
    ), {"pid": str(ctx.project_id)})).all()

    runs = [
        {
            "id": str(row[0]),
            "category": row[1],
            "mode": row[2],
            "status": row[3],
            "scheduled_start": row[4].isoformat() if row[4] else None,
            "completed_at": row[5].isoformat() if row[5] else None,
            "total_findings": row[6] or 0,
            "confirmed_findings": row[7] or 0,
            "severity_counts": {
                "critical": row[8] or 0,
                "high": row[9] or 0,
                "medium": row[10] or 0,
                "low": row[11] or 0,
                "info": row[12] or 0,
            },
            "security_score": row[13],
            "external_pentester_name": row[14],
            "external_pentester_cert": row[15],
            "created_at": row[16].isoformat() if row[16] else None,
        }
        for row in rows
    ]

    await db.commit()
    return {
        "project_id": str(ctx.project_id),
        "total_runs": len(runs),
        "runs": runs,
    }


@router.get("/{token}/documents")
async def auditor_portal_documents(
    token: str, request: Request, db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Documents canonical 10 docs ENAC + dossier ZIP signed link metadata.

    Phase 5.9 · audit_preparation_runs · per run estado dossier_generated +
    timestamps + signed_zip availability. Listed last 5 runs ordenadas DESC.
    Dossier signed ZIP descargable via existing endpoint
    POST /audit-prep/projects/{pid}/dossier/generate-signed-zip (Cluster 1
    Phase 1 · NO duplicar binary streaming aquí · enlace metadata only).
    """
    ctx = await _validate_token_peek(token, request, db)
    await _log_portal_access(
        db, ctx, "auditor_portal.view", payload={"target": "documents"},
    )

    runs = (await db.execute(sa_text(
        "SELECT id, estado, categoria, created_at, "
        "dossier_generated_at, started_at, completed_at "
        "FROM audit_preparation_runs "
        "WHERE project_id = :pid AND deleted_at IS NULL "
        "ORDER BY created_at DESC LIMIT 5"
    ), {"pid": str(ctx.project_id)})).all()

    items = [
        {
            "id": str(row[0]),
            "estado": row[1],
            "categoria": row[2],
            "created_at": row[3].isoformat() if row[3] else None,
            "dossier_generated_at": (
                row[4].isoformat() if row[4] else None
            ),
            "started_at": row[5].isoformat() if row[5] else None,
            "completed_at": row[6].isoformat() if row[6] else None,
            "signed_zip_available": row[4] is not None,
        }
        for row in runs
    ]

    await db.commit()
    return {
        "project_id": str(ctx.project_id),
        "total_runs": len(items),
        "runs": items,
        # Endpoint TOKEN-GATED (GET · magic-link autoriza · sin cookie admin) ·
        # alineado con lo que descarga DocumentsView. Antes apuntaba al endpoint
        # admin require_owner → engañoso (401/403 para el auditor) · #1 Ejecutable 8.
        "signed_zip_endpoint": (
            f"/api/v1/public/auditor-portal/{token}/dossier.zip"
        ),
    }


# ══════════════════════════════════════════════════════════════════════
# Phase 6 · Cross-motor wire-in download endpoints
# ══════════════════════════════════════════════════════════════════════
#
# Cada endpoint:
# 1. Valida token via _validate_token_peek
# 2. Delegates a service M03/M04/M07/M27/M08/M09 existing function
# 3. Emits emit_auditor_event con canonical action + metadata
# 4. Returns Response binary (FileResponse · Response · StreamingResponse)
#
# Canonical events documented en audit_events.py.

@router.get("/{token}/dossier.zip")
async def auditor_portal_dossier_zip(
    token: str, request: Request, db: AsyncSession = Depends(get_db),
    run_id: uuid.UUID | None = None,
) -> Any:
    """Dossier ZIP firmado Ed25519 download · reusa Cluster 1 Phase 1 generator.

    Phase 6.3 · M09 dossier_generator.generate_dossier(sign_manifest=True).
    Emits auditor.download.documents_zip metadata={run_id, size_bytes}.

    Si run_id NO supplied · uses last run para project (mirror admin convenience
    endpoint /audit-prep/projects/{id}/dossier/generate-signed-zip).
    """
    from fastapi.responses import Response
    from sqlalchemy import desc, select as sa_select
    from backend.app.models.audit_prep import AuditPreparationRun
    from backend.app.motors.m09_audit_prep import dossier_generator
    from backend.app.motors.m09_audit_prep.audit_events import (
        AUDITOR_DOWNLOAD_DOCUMENTS_ZIP,
    )

    ctx = await _validate_token_peek(token, request, db)

    # Find run
    if run_id is not None:
        run_query = sa_select(AuditPreparationRun).where(
            AuditPreparationRun.id == run_id,
            AuditPreparationRun.project_id == ctx.project_id,
        )
    else:
        run_query = (
            sa_select(AuditPreparationRun)
            .where(AuditPreparationRun.project_id == ctx.project_id)
            .order_by(desc(AuditPreparationRun.created_at))
            .limit(1)
        )
    run = (await db.execute(run_query)).scalar_one_or_none()
    if run is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="No existe ningún AuditPreparationRun para este proyecto",
        )

    try:
        data = await dossier_generator.generate_dossier(
            db, ctx.project_id, run.id, force=False, sign_manifest=True,
        )
    except dossier_generator.DossierError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )

    await emit_auditor_event(
        db, ctx, AUDITOR_DOWNLOAD_DOCUMENTS_ZIP,
        target="documents_zip",
        metadata={"run_id": str(run.id), "size_bytes": len(data)},
    )
    await db.commit()

    return Response(
        content=data,
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f'attachment; filename="dossier_auditoria_{run.id}_signed.zip"'
            ),
            "X-Run-Id": str(run.id),
            "X-Dossier-Signed": "ed25519",
        },
    )


@router.get("/{token}/audit-log.csv")
async def auditor_portal_audit_log_csv(
    token: str, request: Request, db: AsyncSession = Depends(get_db),
    accion: str | None = None,
    limit: int = 1000,
) -> Any:
    """Audit log CSV export read-only · project-bounded.

    Phase 6.3 · streams CSV con audit_log rows filtered por project_id.
    Emits auditor.download.audit_log_csv metadata={filter_accion, rows_returned}.

    NO incluye hash_current full · only seq + accion + tabla + timestamp +
    payload_new (auditor inspection scope · chain integrity verificable via
    separate fn_audit_log_verify_chain function).
    """
    from fastapi.responses import StreamingResponse
    from backend.app.motors.m09_audit_prep.audit_events import (
        AUDITOR_DOWNLOAD_AUDIT_LOG_CSV,
    )

    ctx = await _validate_token_peek(token, request, db)
    safe_limit = max(1, min(limit, 5000))

    base_query = (
        "SELECT seq, tabla, accion, usuario, timestamp, "
        "payload_new "
        "FROM audit_log "
        "WHERE project_id = :pid"
    )
    params: dict[str, Any] = {"pid": str(ctx.project_id)}
    if accion:
        base_query += " AND accion = :accion"
        params["accion"] = accion
    base_query += " ORDER BY seq DESC LIMIT :lim"
    params["lim"] = safe_limit

    rows = (await db.execute(sa_text(base_query), params)).all()

    await emit_auditor_event(
        db, ctx, AUDITOR_DOWNLOAD_AUDIT_LOG_CSV,
        target="audit_log_csv",
        metadata={
            "filter_accion": accion,
            "rows_returned": len(rows),
            "limit": safe_limit,
        },
    )
    await db.commit()

    def _csv_stream():
        import csv
        import io
        buf = io.StringIO()
        writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["seq", "tabla", "accion", "usuario", "timestamp", "payload_new"])
        yield buf.getvalue()
        for row in rows:
            buf.seek(0)
            buf.truncate()
            writer.writerow([
                row[0],
                row[1] or "",
                row[2] or "",
                row[3] or "",
                row[4].isoformat() if row[4] else "",
                __import__("json").dumps(row[5]) if row[5] else "",
            ])
            yield buf.getvalue()

    return StreamingResponse(
        _csv_stream(),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                f'attachment; filename="audit_log_{ctx.project_id}.csv"'
            ),
        },
    )


@router.get("/{token}/evidence/{evidence_id}/download")
async def auditor_portal_evidence_download(
    token: str,
    evidence_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Evidence file individual download · FileResponse via fichero_path.

    Phase 6.3 · M07 evidence row · project_id MUST match token ctx.project_id
    (defence-in-depth) · scan_status SHOULD be clean (otherwise 422 quarantined).
    Emits auditor.download.evidence_file metadata={evidence_id, measure_code,
    file_name, file_size}.
    """
    from pathlib import Path
    from fastapi.responses import FileResponse
    from backend.app.motors.m09_audit_prep.audit_events import (
        AUDITOR_DOWNLOAD_EVIDENCE_FILE,
    )

    ctx = await _validate_token_peek(token, request, db)

    row = (await db.execute(sa_text(
        "SELECT id, project_id, measure_code, fichero_path, "
        "fichero_nombre_original, fichero_mime_type, fichero_tamano_bytes, "
        "scan_status, deleted_at "
        "FROM evidence WHERE id = :eid"
    ), {"eid": str(evidence_id)})).first()

    if row is None or row[8] is not None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Evidence not found",
        )
    if str(row[1]) != str(ctx.project_id):
        # Token scope bounded · NEVER expose cross-project evidence
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Evidence outside auditor token scope",
        )
    if row[7] in ("infected", "quarantined"):
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Evidence quarantined (scan_status={row[7]})",
        )
    fichero_path = row[3]
    if not fichero_path:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Evidence has no file attachment",
        )

    abs_path = Path(fichero_path)
    if not abs_path.is_absolute():
        # _REPO_ROOT pattern (M07 antivirus_scan_service._abs_path)
        from backend.app.motors.m07_evidence.antivirus_scan_service import _abs_path
        candidate = _abs_path(fichero_path)
        abs_path = candidate if candidate else abs_path

    if not abs_path.exists():
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Evidence file missing on disk",
        )

    await emit_auditor_event(
        db, ctx, AUDITOR_DOWNLOAD_EVIDENCE_FILE,
        target="evidence_file",
        metadata={
            "evidence_id": str(evidence_id),
            "measure_code": row[2],
            "file_name": row[4],
            "file_size": row[6],
        },
    )
    await db.commit()

    return FileResponse(
        path=str(abs_path),
        media_type=row[5] or "application/octet-stream",
        filename=row[4] or f"evidence_{evidence_id}",
    )
