"""Motor 2 — MAGERIT · cliente in-portal API · SAN-E v3.MB-5.4.

ADR-020 v6 Q5.3: cliente revisa inventory activos MAGERIT in-portal · NO
edita valoración DICAT (admin owns) · solo review (revisada_ok ·
con_pregunta · suggest_change). Replica pattern m03_dda/portal_api.

Sub-atom 5.4.A scope (foundation):
- GET /portal/magerit/projects/{project_id}/summary
- GET /portal/magerit/projects/{project_id}/assets (list richer)
- GET /portal/magerit/assets/{asset_id} (detail richer)
- POST /portal/magerit/assets/{asset_id}/review

Sub-atom 5.4.C (DEFERRED): document-hash + signing wire-up.
Sub-atom posterior (DEFERRED): risks (magerit_threat_assessment) review.

Auth: ClientUser via cookie + CSRF triple binding (alineado m03 portal).
RLS: magerit_analysis enforce project_id · _ensure_project_belongs_to_client.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import case, func, select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, set_tenant_context
from backend.app.models.client_portal import ClientUser
import hashlib

from backend.app.motors.m02_magerit.models import (
    MageritAnalysis,
    MageritAsset,
    MageritThreat,
    MageritThreatAssessment,
)
from backend.app.motors.m21_portal_cliente.api import get_current_client_user
from backend.app.motors.m21_portal_cliente.ownership import ensure_owned_via_project


router = APIRouter(
    prefix="/portal/magerit",
    tags=["Motor 2 - MAGERIT cliente in-portal"],
)


# ====================================================================
# Schemas
# ====================================================================


class MageritSummaryResponse(BaseModel):
    project_id: uuid.UUID
    analysis_id: uuid.UUID | None
    analysis_name: str | None
    analysis_status: str | None
    # Assets section (5.4.A)
    total_assets: int
    assets_by_type: dict[str, int]
    reviewed_count: int
    pending_review_count: int
    questions_count: int
    suggestions_count: int
    completion_percentage: int
    # Risks section (5.4.B)
    total_risks: int
    risks_by_severity: dict[str, int]
    risks_reviewed_count: int
    risks_pending_review_count: int
    risks_questions_count: int
    risks_suggestions_count: int
    risks_completion_percentage: int
    # Combined readiness
    ready_for_validation_sign: bool
    last_signed_at: datetime | None


class MageritAssetClientView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    analysis_id: uuid.UUID
    code: str
    name: str
    asset_type_code: str
    description: str | None
    owner: str | None

    # Valoración DICAT (admin · cliente VE · NO edit per Q5.3)
    value_d: int | None
    value_i: int | None
    value_c: int | None
    value_a: int | None
    value_t: int | None

    # Valores acumulados (post-propagación dependencias · admin computed)
    accumulated_d: float | None
    accumulated_i: float | None
    accumulated_c: float | None
    accumulated_a: float | None
    accumulated_t: float | None

    # Cliente review
    client_review_status: str | None
    client_review_note: str | None
    client_reviewed_at: datetime | None


class ClientAssetReviewRequest(BaseModel):
    action: str = Field(
        ..., description="revisada_ok | con_pregunta | suggest_change",
    )
    note: str | None = Field(None, max_length=2000)


class MageritRiskClientView(BaseModel):
    """Cliente view de un análisis riesgo (asset + threat + degradación + review).

    Sub-atom 5.4.B · MageritThreatAssessment JOIN MageritAsset + MageritThreat.
    Severidad derivada de probability × max(degradation_*) (no almacenada).
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    analysis_id: uuid.UUID

    # Asset linked
    asset_id: uuid.UUID
    asset_code: str
    asset_name: str
    asset_type_code: str

    # Threat linked
    threat_code: str
    threat_name: str
    threat_group_code: str
    threat_description: str | None
    affected_dimensions: list[str] | None

    # Análisis MAGERIT
    probability: str  # MB · B · M · A · MA
    degradation_d: int | None
    degradation_i: int | None
    degradation_c: int | None
    degradation_a: int | None
    degradation_t: int | None
    max_degradation: int  # max(degradation_*) computed
    severity: str  # baja · media · alta · critica · derived

    # Cliente review
    client_review_status: str | None
    client_review_note: str | None
    client_reviewed_at: datetime | None

    last_modified_at: datetime | None


class ClientRiskReviewRequest(BaseModel):
    action: str = Field(
        ..., description="revisada_ok | con_pregunta | suggest_change",
    )
    note: str | None = Field(None, max_length=2000)


class MageritDocumentHashResponse(BaseModel):
    """Document hash determinista para SigningIntent · atom 5.4.C."""

    project_id: uuid.UUID
    analysis_id: uuid.UUID | None
    document_hash_sha256: str
    canonical_length: int
    assets_count: int
    risks_count: int
    last_modified_at: datetime | None
    ready_for_signing: bool


_PROBABILITY_NUMERIC: dict[str, int] = {
    "MB": 1, "B": 2, "M": 3, "A": 4, "MA": 5,
}


def _compute_max_degradation(r: MageritThreatAssessment) -> int:
    degs = [
        r.degradation_d, r.degradation_i, r.degradation_c,
        r.degradation_a, r.degradation_t,
    ]
    return max((d for d in degs if d is not None), default=0)


def _compute_severity(probability: str, max_deg: int) -> str:
    """Severidad cualitativa simple para UX cliente · NO es cálculo MAGERIT
    formal (MageritRiskCalculation tiene el cálculo formal admin)."""
    score = _PROBABILITY_NUMERIC.get(probability, 3) * max_deg
    if score >= 350:
        return "critica"
    if score >= 200:
        return "alta"
    if score >= 80:
        return "media"
    return "baja"


VALID_REVIEW_ACTIONS = {
    "revisada_ok",
    "con_pregunta",
    "suggest_change",
}


# ====================================================================
# Helpers
# ====================================================================


async def _ensure_project_belongs_to_client(
    db: AsyncSession,
    project_id: uuid.UUID,
    user: ClientUser,
) -> None:
    """Verify project ownership + sets tenant context for RLS."""
    row = await db.execute(
        sa_text("SELECT client_id FROM projects WHERE id = :pid"),
        {"pid": str(project_id)},
    )
    hit = row.first()
    if hit is None:
        raise HTTPException(status_code=404, detail="Project no existe")
    if hit[0] != user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Project no pertenece al cliente del usuario",
        )
    await set_tenant_context(
        db, client_id=user.client_id, project_id=project_id,
    )


async def _get_active_analysis_id(
    db: AsyncSession, project_id: uuid.UUID,
) -> uuid.UUID | None:
    """Returns latest non-deleted analysis id for project."""
    row = await db.execute(
        select(MageritAnalysis)
        .where(MageritAnalysis.project_id == project_id)
        .where(MageritAnalysis.deleted_at.is_(None))
        .order_by(MageritAnalysis.created_at.desc())
        .limit(1)
    )
    analysis = row.scalar_one_or_none()
    return analysis.id if analysis else None


async def _to_risk_client_view(
    db: AsyncSession,
    assessment: MageritThreatAssessment,
    asset: MageritAsset | None,
    threat: MageritThreat | None,
) -> MageritRiskClientView:
    """Serialize threat_assessment + asset + threat → cliente view (sub-atom 5.4.B).

    `asset` puede ser None en el borde RLS post-review (el contexto de tenant
    `current_project_id()` se pierde si la conexión del pool vuelve sin él):
    en ese caso degradamos los campos del activo en vez de crashear (la acción
    de review YA se persistió · NO devolvemos 500). Defensa ante el 500
    intermitente de POST /risks/{id}/review observado en E2E (1 ocurrencia).
    """
    max_deg = _compute_max_degradation(assessment)
    severity = _compute_severity(assessment.probability, max_deg)
    affected_dims = None
    if threat and threat.affected_dimensions:
        ad = threat.affected_dimensions
        if isinstance(ad, list):
            affected_dims = list(ad)
        elif isinstance(ad, dict):
            affected_dims = list(ad.values())
    return MageritRiskClientView(
        id=assessment.id,
        analysis_id=assessment.analysis_id,
        asset_id=asset.id if asset else assessment.asset_id,
        asset_code=asset.code if asset else "",
        asset_name=asset.name if asset else "",
        asset_type_code=asset.asset_type_code if asset else "",
        threat_code=assessment.threat_code,
        threat_name=threat.name if threat else assessment.threat_code,
        threat_group_code=threat.group_code if threat else "",
        threat_description=threat.description if threat else None,
        affected_dimensions=affected_dims,
        probability=assessment.probability,
        degradation_d=assessment.degradation_d,
        degradation_i=assessment.degradation_i,
        degradation_c=assessment.degradation_c,
        degradation_a=assessment.degradation_a,
        degradation_t=assessment.degradation_t,
        max_degradation=max_deg,
        severity=severity,
        client_review_status=assessment.client_review_status,
        client_review_note=assessment.client_review_note,
        client_reviewed_at=assessment.client_reviewed_at,
        last_modified_at=assessment.updated_at,
    )


async def _to_asset_client_view(
    asset: MageritAsset,
) -> MageritAssetClientView:
    """Serialize MageritAsset → cliente view (atom 5.4.A · DRY pattern)."""
    return MageritAssetClientView(
        id=asset.id,
        analysis_id=asset.analysis_id,
        code=asset.code,
        name=asset.name,
        asset_type_code=asset.asset_type_code,
        description=asset.description,
        owner=asset.owner,
        value_d=asset.value_d,
        value_i=asset.value_i,
        value_c=asset.value_c,
        value_a=asset.value_a,
        value_t=asset.value_t,
        accumulated_d=(
            float(asset.accumulated_d) if asset.accumulated_d is not None else None
        ),
        accumulated_i=(
            float(asset.accumulated_i) if asset.accumulated_i is not None else None
        ),
        accumulated_c=(
            float(asset.accumulated_c) if asset.accumulated_c is not None else None
        ),
        accumulated_a=(
            float(asset.accumulated_a) if asset.accumulated_a is not None else None
        ),
        accumulated_t=(
            float(asset.accumulated_t) if asset.accumulated_t is not None else None
        ),
        client_review_status=asset.client_review_status,
        client_review_note=asset.client_review_note,
        client_reviewed_at=asset.client_reviewed_at,
    )


# ====================================================================
# Endpoints
# ====================================================================


@router.get(
    "/projects/{project_id}/summary",
    response_model=MageritSummaryResponse,
)
async def get_magerit_summary(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> MageritSummaryResponse:
    """Summary inventory cliente · counts + review distribution + readiness."""
    await _ensure_project_belongs_to_client(db, project_id, user)

    analysis_row = await db.execute(
        select(MageritAnalysis)
        .where(MageritAnalysis.project_id == project_id)
        .where(MageritAnalysis.deleted_at.is_(None))
        .order_by(MageritAnalysis.created_at.desc())
        .limit(1)
    )
    analysis = analysis_row.scalar_one_or_none()
    if analysis is None:
        return MageritSummaryResponse(
            project_id=project_id,
            analysis_id=None,
            analysis_name=None,
            analysis_status=None,
            total_assets=0,
            assets_by_type={},
            reviewed_count=0,
            pending_review_count=0,
            questions_count=0,
            suggestions_count=0,
            completion_percentage=0,
            total_risks=0,
            risks_by_severity={},
            risks_reviewed_count=0,
            risks_pending_review_count=0,
            risks_questions_count=0,
            risks_suggestions_count=0,
            risks_completion_percentage=0,
            ready_for_validation_sign=False,
            last_signed_at=None,
        )

    counts_row = (await db.execute(
        select(
            func.count(MageritAsset.id).label("total"),
            func.count(
                case((MageritAsset.client_review_status == "revisada_ok", 1))
            ).label("reviewed"),
            func.count(
                case((MageritAsset.client_review_status == "con_pregunta", 1))
            ).label("questions"),
            func.count(
                case((MageritAsset.client_review_status == "suggest_change", 1))
            ).label("suggestions"),
        )
        .where(MageritAsset.analysis_id == analysis.id)
        .where(MageritAsset.deleted_at.is_(None))
    )).one()
    total, reviewed, questions, suggestions = counts_row
    pending = total - reviewed - questions - suggestions
    completion = int((reviewed * 100) / total) if total > 0 else 0

    by_type_rows = (await db.execute(
        select(
            MageritAsset.asset_type_code,
            func.count(MageritAsset.id),
        )
        .where(MageritAsset.analysis_id == analysis.id)
        .where(MageritAsset.deleted_at.is_(None))
        .group_by(MageritAsset.asset_type_code)
    )).all()
    assets_by_type = {code: int(count) for code, count in by_type_rows}

    # Risks counts (sub-atom 5.4.B)
    risks_counts_row = (await db.execute(
        select(
            func.count(MageritThreatAssessment.id).label("rtotal"),
            func.count(
                case((MageritThreatAssessment.client_review_status == "revisada_ok", 1))
            ).label("rreviewed"),
            func.count(
                case((MageritThreatAssessment.client_review_status == "con_pregunta", 1))
            ).label("rquestions"),
            func.count(
                case((MageritThreatAssessment.client_review_status == "suggest_change", 1))
            ).label("rsuggestions"),
        )
        .where(MageritThreatAssessment.analysis_id == analysis.id)
    )).one()
    r_total, r_reviewed, r_questions, r_suggestions = risks_counts_row
    r_pending = r_total - r_reviewed - r_questions - r_suggestions
    r_completion = int((r_reviewed * 100) / r_total) if r_total > 0 else 0

    # Compute severity distribution (Python-side · simple)
    risks_rows = (await db.execute(
        select(MageritThreatAssessment)
        .where(MageritThreatAssessment.analysis_id == analysis.id)
    )).scalars().all()
    severity_dist: dict[str, int] = {"baja": 0, "media": 0, "alta": 0, "critica": 0}
    for r in risks_rows:
        max_deg = _compute_max_degradation(r)
        sev = _compute_severity(r.probability, max_deg)
        severity_dist[sev] = severity_dist.get(sev, 0) + 1

    last_signed_row = await db.execute(
        sa_text(
            "SELECT MAX(se.created_at) FROM signing_events se "
            "JOIN signing_intents si ON si.id = se.signing_intent_id "
            "WHERE si.project_id = :pid AND si.signable_type = "
            "'magerit_validation' AND se.event_type = 'signature_generated'"
        ),
        {"pid": str(project_id)},
    )
    last_signed = last_signed_row.scalar_one_or_none()

    # Sesión 3B-2B.8 Phase 1B · audit_log emit cliente.magerit.viewed con
    # project_id + client_id Sub-atom 5.A 3-way OR pattern.
    import json as _json
    await db.execute(sa_text(
        "INSERT INTO audit_log (id, tabla, registro_id, accion, usuario, "
        "project_id, client_id, payload_new, timestamp) "
        "VALUES (gen_random_uuid(), 'magerit_analysis', :pid, "
        "'cliente.magerit.viewed', :user, :pid, :cid, :payload, now())"
    ), {
        "pid": str(project_id),
        "user": (user.email or "cliente")[:255],
        "cid": str(user.client_id),
        "payload": _json.dumps({
            "analysis_id": str(analysis.id),
            "total_assets": int(total or 0),
            "total_risks": int(r_total or 0),
        }),
    })
    await db.commit()

    return MageritSummaryResponse(
        project_id=project_id,
        analysis_id=analysis.id,
        analysis_name=analysis.name,
        analysis_status=analysis.status,
        total_assets=int(total or 0),
        assets_by_type=assets_by_type,
        reviewed_count=int(reviewed or 0),
        pending_review_count=int(pending or 0),
        questions_count=int(questions or 0),
        suggestions_count=int(suggestions or 0),
        completion_percentage=completion,
        total_risks=int(r_total or 0),
        risks_by_severity=severity_dist,
        risks_reviewed_count=int(r_reviewed or 0),
        risks_pending_review_count=int(r_pending or 0),
        risks_questions_count=int(r_questions or 0),
        risks_suggestions_count=int(r_suggestions or 0),
        risks_completion_percentage=r_completion,
        ready_for_validation_sign=(
            total > 0 and pending == 0
            and (r_total == 0 or r_pending == 0)
        ),
        last_signed_at=last_signed,
    )


@router.get(
    "/projects/{project_id}/assets",
    response_model=list[MageritAssetClientView],
)
async def list_magerit_assets(
    project_id: uuid.UUID,
    asset_type: str | None = Query(None),
    review_status: str | None = Query(
        None,
        description=(
            "Filter por client_review_status · pendiente_revision · "
            "revisada_ok · con_pregunta · suggest_change"
        ),
    ),
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> list[MageritAssetClientView]:
    """Lista activos MAGERIT cliente review · richer detail."""
    await _ensure_project_belongs_to_client(db, project_id, user)

    analysis_id = await _get_active_analysis_id(db, project_id)
    if analysis_id is None:
        return []

    stmt = (
        select(MageritAsset)
        .where(MageritAsset.analysis_id == analysis_id)
        .where(MageritAsset.deleted_at.is_(None))
    )
    if asset_type:
        stmt = stmt.where(MageritAsset.asset_type_code == asset_type)
    if review_status:
        if review_status == "pendiente_revision":
            stmt = stmt.where(MageritAsset.client_review_status.is_(None))
        else:
            stmt = stmt.where(
                MageritAsset.client_review_status == review_status
            )

    stmt = stmt.order_by(MageritAsset.code)
    rows = (await db.execute(stmt)).scalars().all()
    return [await _to_asset_client_view(a) for a in rows]


@router.get(
    "/assets/{asset_id}",
    response_model=MageritAssetClientView,
)
async def get_magerit_asset_detail(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> MageritAssetClientView:
    """Detail asset · cliente expand view."""
    asset = await db.get(MageritAsset, asset_id)
    if asset is None or asset.deleted_at is not None:
        raise HTTPException(status_code=404, detail="No encontrado")

    # Resolve project_id via analysis
    analysis = await db.get(MageritAnalysis, asset.analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="No encontrado")
    await ensure_owned_via_project(db, analysis.project_id, user)

    return await _to_asset_client_view(asset)


@router.post(
    "/assets/{asset_id}/review",
    response_model=MageritAssetClientView,
)
async def review_magerit_asset(
    asset_id: uuid.UUID,
    body: ClientAssetReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> MageritAssetClientView:
    """Cliente review action · acepta · pregunta · sugiere cambio."""
    if body.action not in VALID_REVIEW_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"action invalid · uno de {sorted(VALID_REVIEW_ACTIONS)}"
            ),
        )
    if body.action in {"con_pregunta", "suggest_change"} and not (
        body.note or ""
    ).strip():
        raise HTTPException(
            status_code=400,
            detail=f"action='{body.action}' requiere note no vacia",
        )

    asset = await db.get(MageritAsset, asset_id)
    if asset is None or asset.deleted_at is not None:
        raise HTTPException(status_code=404, detail="No encontrado")

    analysis = await db.get(MageritAnalysis, asset.analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="No encontrado")
    await ensure_owned_via_project(db, analysis.project_id, user)

    asset.client_review_status = body.action
    asset.client_review_note = body.note
    asset.client_reviewed_at = datetime.now(UTC)
    asset.client_reviewed_by_user_id = user.id
    await db.flush()
    # HIGH #5 · que la duda/sugerencia del cliente sobre el activo LLEGUE a admin
    # (audit_log · feeds admin + recent-activity · 3-way OR Sub-atom 5.A).
    if body.action in {"con_pregunta", "suggest_change"}:
        import json as _json
        await db.execute(sa_text(
            "INSERT INTO audit_log (id, tabla, registro_id, accion, usuario, "
            "project_id, client_id, payload_new, timestamp) VALUES "
            "(gen_random_uuid(), 'magerit_assets', :rid, 'magerit.review.flagged', "
            ":usr, :pid, :cid, CAST(:payload AS jsonb), now())"
        ), {
            "rid": str(asset.id), "usr": f"cliente:{user.id}"[:255],
            "pid": str(analysis.project_id), "cid": str(user.client_id),
            "payload": _json.dumps({
                "action": body.action,
                "note": (body.note or "")[:2000],
                "asset_name": getattr(asset, "name", None),
            }),
        })
    await db.commit()

    return await _to_asset_client_view(asset)


# ====================================================================
# Risks endpoints (sub-atom 5.4.B)
# ====================================================================


@router.get(
    "/projects/{project_id}/risks",
    response_model=list[MageritRiskClientView],
)
async def list_magerit_risks(
    project_id: uuid.UUID,
    severity: str | None = Query(None),
    review_status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> list[MageritRiskClientView]:
    """List análisis riesgos (MageritThreatAssessment) cliente review."""
    await _ensure_project_belongs_to_client(db, project_id, user)

    analysis_id = await _get_active_analysis_id(db, project_id)
    if analysis_id is None:
        return []

    stmt = (
        select(MageritThreatAssessment, MageritAsset)
        .join(
            MageritAsset, MageritAsset.id == MageritThreatAssessment.asset_id,
        )
        .where(MageritThreatAssessment.analysis_id == analysis_id)
        .where(MageritAsset.deleted_at.is_(None))
    )
    if review_status:
        if review_status == "pendiente_revision":
            stmt = stmt.where(
                MageritThreatAssessment.client_review_status.is_(None)
            )
        else:
            stmt = stmt.where(
                MageritThreatAssessment.client_review_status == review_status
            )
    stmt = stmt.order_by(MageritAsset.code, MageritThreatAssessment.threat_code)

    rows = (await db.execute(stmt)).all()

    # Fetch threats catalog map (single query)
    threat_codes = list({r[0].threat_code for r in rows})
    threats_stmt = select(MageritThreat).where(
        MageritThreat.code.in_(threat_codes)
    )
    threats_rows = (await db.execute(threats_stmt)).scalars().all()
    threats_map: dict[str, MageritThreat] = {t.code: t for t in threats_rows}

    result: list[MageritRiskClientView] = []
    for assessment, asset in rows:
        threat = threats_map.get(assessment.threat_code)
        view = await _to_risk_client_view(db, assessment, asset, threat)
        # Apply severity filter post-compute (severity is derived)
        if severity and view.severity != severity:
            continue
        result.append(view)
    return result


@router.post(
    "/risks/{risk_id}/review",
    response_model=MageritRiskClientView,
)
async def review_magerit_risk(
    risk_id: uuid.UUID,
    body: ClientRiskReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> MageritRiskClientView:
    """Cliente review action sobre análisis riesgo."""
    if body.action not in VALID_REVIEW_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"action invalid · uno de {sorted(VALID_REVIEW_ACTIONS)}",
        )
    if body.action in {"con_pregunta", "suggest_change"} and not (
        body.note or ""
    ).strip():
        raise HTTPException(
            status_code=400,
            detail=f"action='{body.action}' requiere note no vacia",
        )

    assessment = await db.get(MageritThreatAssessment, risk_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="No encontrado")

    analysis = await db.get(MageritAnalysis, assessment.analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="No encontrado")
    await ensure_owned_via_project(db, analysis.project_id, user)

    # Cargar asset + threat JUSTO tras fijar el contexto de tenant (RLS recién
    # seteado por _ensure_project_belongs_to_client → current_project_id() está
    # activo y current con certeza) y ANTES de mutar/flush/commit. Con
    # expire_on_commit=False los objetos cargados aquí sobreviven al commit.
    #
    # Por qué ANTES y no después del commit (bug 500 intermitente E2E ·
    # POST /risks/{id}/review · 1 ocurrencia): set_config(..., true) es
    # transaction-local. Si el asset se cargaba tras un flush/IO que pudiera
    # reciclar el contexto, RLS filtraba la fila (asset=None) → AttributeError
    # en _to_risk_client_view → 500. Cargándolo aquí el contexto está garantizado.
    asset = await db.get(MageritAsset, assessment.asset_id)
    threat = (await db.execute(
        select(MageritThreat).where(
            MageritThreat.code == assessment.threat_code
        )
    )).scalar_one_or_none()

    assessment.client_review_status = body.action
    assessment.client_review_note = body.note
    assessment.client_reviewed_at = datetime.now(UTC)
    assessment.client_reviewed_by_user_id = user.id

    await db.commit()

    # _to_risk_client_view tolera asset=None (degrada · NO 500) como red de
    # seguridad adicional ante cualquier borde RLS residual.
    return await _to_risk_client_view(db, assessment, asset, threat)


# ====================================================================
# Document hash (sub-atom 5.4.C · SigningIntent pre-firma)
# ====================================================================


@router.get(
    "/projects/{project_id}/document-hash",
    response_model=MageritDocumentHashResponse,
)
async def get_magerit_document_hash(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> MageritDocumentHashResponse:
    """SHA256 deterministic state inventory + análisis riesgos · pre-firma.

    Hash incluye:
    - project_id + analysis_id
    - per asset (sorted by code): DICAT values + review status
    - per risk (sorted by asset+threat): probability + degradations + review
    """
    await _ensure_project_belongs_to_client(db, project_id, user)

    analysis_id = await _get_active_analysis_id(db, project_id)

    if analysis_id is None:
        return MageritDocumentHashResponse(
            project_id=project_id,
            analysis_id=None,
            document_hash_sha256=hashlib.sha256(b"").hexdigest(),
            canonical_length=0,
            assets_count=0,
            risks_count=0,
            last_modified_at=None,
            ready_for_signing=False,
        )

    assets_stmt = (
        select(MageritAsset)
        .where(MageritAsset.analysis_id == analysis_id)
        .where(MageritAsset.deleted_at.is_(None))
        .order_by(MageritAsset.code)
    )
    assets = (await db.execute(assets_stmt)).scalars().all()

    risks_stmt = (
        select(MageritThreatAssessment, MageritAsset)
        .join(
            MageritAsset,
            MageritAsset.id == MageritThreatAssessment.asset_id,
        )
        .where(MageritThreatAssessment.analysis_id == analysis_id)
        .order_by(MageritAsset.code, MageritThreatAssessment.threat_code)
    )
    risks_rows = (await db.execute(risks_stmt)).all()

    canonical_parts: list[str] = [
        f"project_id:{project_id}",
        f"analysis_id:{analysis_id}",
        f"assets_count:{len(assets)}",
        f"risks_count:{len(risks_rows)}",
    ]
    last_modified: datetime | None = None
    all_assets_reviewed = len(assets) > 0
    all_risks_reviewed = True  # vacuously true if no risks

    for a in assets:
        review = a.client_review_status or "pending"
        canonical_parts.append(
            f"AS:{a.code}|d={a.value_d or 0}|i={a.value_i or 0}|"
            f"c={a.value_c or 0}|a={a.value_a or 0}|t={a.value_t or 0}|"
            f"review={review}"
        )
        if a.client_review_status is None:
            all_assets_reviewed = False
        ts_candidates = [t for t in (a.updated_at, a.client_reviewed_at) if t]
        if ts_candidates:
            asset_max = max(ts_candidates)
            if last_modified is None or asset_max > last_modified:
                last_modified = asset_max

    if risks_rows:
        all_risks_reviewed = True
        for assessment, asset in risks_rows:
            review = assessment.client_review_status or "pending"
            canonical_parts.append(
                f"RG:{asset.code}-{assessment.threat_code}|"
                f"prob={assessment.probability}|"
                f"dd={assessment.degradation_d or 0}|"
                f"di={assessment.degradation_i or 0}|"
                f"dc={assessment.degradation_c or 0}|"
                f"da={assessment.degradation_a or 0}|"
                f"dt={assessment.degradation_t or 0}|"
                f"review={review}"
            )
            if assessment.client_review_status is None:
                all_risks_reviewed = False
            ts_candidates = [
                t for t in (assessment.updated_at, assessment.client_reviewed_at) if t
            ]
            if ts_candidates:
                risk_max = max(ts_candidates)
                if last_modified is None or risk_max > last_modified:
                    last_modified = risk_max

    canonical = "\n".join(canonical_parts)
    document_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    return MageritDocumentHashResponse(
        project_id=project_id,
        analysis_id=analysis_id,
        document_hash_sha256=document_hash,
        canonical_length=len(canonical),
        assets_count=len(assets),
        risks_count=len(risks_rows),
        last_modified_at=last_modified,
        ready_for_signing=all_assets_reviewed and all_risks_reviewed,
    )
