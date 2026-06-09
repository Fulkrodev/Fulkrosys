"""Endpoints REST Motor 16 — admin (Marcos) + client (interlocutor via magic link)."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from backend.app.models.onboarding import OnboardingSession

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status as http_status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.precliente_consent import PreClienteDiagnosticConsent
from backend.app.motors.m16_onboarding.art13_precliente import (
    ART13_PRECLIENTE_TEXT,
    ART13_PRECLIENTE_VERSION,
)

from sqlalchemy import select, text

from backend.app.database import get_db, set_tenant_context
from backend.app.auth.dependencies import require_owner

from .catalog_loader import get_template_by_id, list_available_sectors, load_all_templates
from .enums import Role, Sector, SessionState
from .schemas import (
    CancelSessionBody,
    CancelSessionResponse,
    CatalogResponse,
    CreatePreclienteSessionBody,
    CreatePreclienteSessionResponse,
    CreateSessionBody,
    CreateSessionResponse,
    MarkSessionSentResponse,
    PreclienteEmailTemplate,
    SessionDetail,
    SessionSummary,
    TemplateSummary,
)
from .service import (
    OnboardingServiceError,
    cancel_session,
    create_session,
    get_session_detail,
    list_sessions_by_project,
    mark_session_sent,
)
from .precliente_email import build_precliente_invitation_email
from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose

router = APIRouter(prefix="/onboarding", tags=["Motor 16 - Onboarding"])


# ==== RLS HELPER ====

async def _set_project_rls(project_id: uuid.UUID, db: AsyncSession):
    """Set RLS context for onboarding_sessions via project owner lookup."""
    client_id = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
    )).scalar()
    if not client_id:
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, client_id=client_id, project_id=project_id)


# ==== CATALOG ====

@router.get("/catalog", response_model=CatalogResponse)
async def get_catalog() -> CatalogResponse:
    """Lista las plantillas de onboarding in-portal disponibles.

    Batch B: la plantilla del diagnóstico previo (sector sintético PRECLIENTE)
    se EXCLUYE del catálogo admin · es para el lead account-less, no para la
    creación de sesiones in-portal desde el panel.
    L-2 (FRENTE L): el sector sintético INDIVIDUAL (autónomo) también se EXCLUYE
    del dropdown admin · se dispara por el flujo del perfil autónomo, no manual.
    """
    _SYNTHETIC_SECTORS = {Sector.PRECLIENTE, Sector.INDIVIDUAL}
    templates = [
        t for t in load_all_templates() if t.sector not in _SYNTHETIC_SECTORS
    ]
    summaries = [
        TemplateSummary(
            id=t.id, version=t.version, sector=t.sector, role=t.role,
            nombre=t.nombre, descripcion=t.descripcion,
            tiempo_estimado_minutos=t.tiempo_estimado_minutos,
            language=t.language, total_questions=len(t.questions),
        )
        for t in templates
    ]
    return CatalogResponse(
        total=len(summaries),
        templates=summaries,
        available_sectors=[
            s for s in list_available_sectors() if s not in _SYNTHETIC_SECTORS
        ],
    )


@router.get("/catalog/{template_id}")
async def get_template_detail(template_id: str):
    """Detalle completo de una plantilla (incluye preguntas)."""
    t = get_template_by_id(template_id)
    if t is None:
        raise HTTPException(status_code=404, detail=f"Plantilla {template_id} no existe")
    return t.model_dump()


# ==== SESSIONS (admin) ====

@router.post(
    "/projects/{project_id}/sessions",
    response_model=CreateSessionResponse,
    dependencies=[Depends(require_owner)],
)
async def create_session_endpoint(
    project_id: uuid.UUID,
    body: CreateSessionBody,
    session: AsyncSession = Depends(get_db),
) -> CreateSessionResponse:
    """Crea una nueva onboarding session + magic link M12."""
    await _set_project_rls(project_id, session)
    try:
        result = await create_session(
            db=session,
            project_id=project_id,
            sector=body.sector,
            role=body.role,
            interlocutor_email=str(body.interlocutor_email),
            interlocutor_name=body.interlocutor_name,
            ttl_hours=body.ttl_hours,
            language=body.language,
            metadata_extra=body.metadata_extra,
        )
    except OnboardingServiceError as exc:
        raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    await session.commit()
    return CreateSessionResponse(**result)


@router.post(
    "/precliente/sessions",
    response_model=CreatePreclienteSessionResponse,
    dependencies=[Depends(require_owner)],
)
async def create_precliente_session_endpoint(
    body: CreatePreclienteSessionBody,
    session: AsyncSession = Depends(get_db),
) -> CreatePreclienteSessionResponse:
    """Batch B · trigger admin del diagnóstico previo (lead account-less).

    Sobre un proyecto ligero YA existente (su creación queda como costura · fuera
    de alcance), emite la sesión precliente + magic-link account-less (purpose
    DIAGNOSTICO_PRECLIENTE · plantilla onb-precliente-sponsor-v1) y devuelve el
    magic_link_url + la plantilla de email branded para que Marcos la envíe A
    MANO (NO auto-send · LSSI + sin SMTP en dev).
    """
    # #7.3 · si viene lead_id, crea/reusa el PROYECTO LIGERO del lead (la costura
    # antes fuera de alcance) y formaliza la traza lead↔onboarding.
    lead_id_for_session = None
    if body.lead_id is not None:
        from backend.app.models.commercial import Lead
        from backend.app.motors.m13_commercial.services.commercial_workflow_service import (
            CommercialWorkflowService,
        )
        lead = await session.get(Lead, body.lead_id)
        if lead is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Lead {body.lead_id} no encontrado",
            )
        project = await CommercialWorkflowService(session).create_lightweight_project_for_lead(lead)
        project_id = project.id
        lead_id_for_session = lead.id
    else:
        project_id = body.project_id

    await _set_project_rls(project_id, session)
    try:
        result = await create_session(
            db=session,
            project_id=project_id,
            sector=Sector.PRECLIENTE,
            role=Role.SPONSOR,
            interlocutor_email=str(body.interlocutor_email),
            interlocutor_name=body.interlocutor_name,
            ttl_hours=body.ttl_hours,
            language=body.language,
            metadata_extra=None,
            purpose=MagicLinkPurpose.DIAGNOSTICO_PRECLIENTE,
            lead_id=lead_id_for_session,
        )
    except OnboardingServiceError as exc:
        raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    await session.commit()

    email = build_precliente_invitation_email(
        lead_name=body.interlocutor_name,
        magic_link_url=result["magic_link_url"],
    )
    return CreatePreclienteSessionResponse(
        session_id=result["session_id"],
        magic_link_id=result["magic_link_id"],
        magic_link_url=result["magic_link_url"],
        expires_at=result["expires_at"],
        state=result["state"],
        email=PreclienteEmailTemplate(**email),
    )


@router.get(
    "/projects/{project_id}/sessions",
    response_model=list[SessionSummary],
    dependencies=[Depends(require_owner)],
)
async def list_sessions_endpoint(
    project_id: uuid.UUID,
    state: Optional[SessionState] = Query(None),
    role: Optional[Role] = Query(None),
    session: AsyncSession = Depends(get_db),
) -> list[SessionSummary]:
    """Lista sessions del proyecto con filtros opcionales."""
    await _set_project_rls(project_id, session)
    results = await list_sessions_by_project(session, project_id, state_filter=state, role_filter=role)
    return [SessionSummary(**r) for r in results]


@router.get(
    "/sessions/{session_id}",
    response_model=SessionDetail,
    dependencies=[Depends(require_owner)],
)
async def get_session_endpoint(
    session_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> SessionDetail:
    try:
        result = await get_session_detail(session, session_id)
    except OnboardingServiceError as exc:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc))
    return SessionDetail(**result)


@router.post(
    "/sessions/{session_id}/mark-sent",
    response_model=MarkSessionSentResponse,
    dependencies=[Depends(require_owner)],
)
async def mark_sent_endpoint(
    session_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> MarkSessionSentResponse:
    """Marcos marca que ya envio el magic link al cliente."""
    try:
        result = await mark_session_sent(session, session_id)
    except OnboardingServiceError as exc:
        raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    await session.commit()
    return MarkSessionSentResponse(**result)


@router.post(
    "/sessions/{session_id}/cancel",
    response_model=CancelSessionResponse,
    dependencies=[Depends(require_owner)],
)
async def cancel_session_endpoint(
    session_id: uuid.UUID,
    body: CancelSessionBody,
    session: AsyncSession = Depends(get_db),
) -> CancelSessionResponse:
    try:
        result = await cancel_session(session, session_id, body.reason)
    except OnboardingServiceError as exc:
        raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    await session.commit()
    return CancelSessionResponse(**result)


@router.get(
    "/projects/{project_id}/sessions/expired",
    response_model=list[SessionSummary],
    dependencies=[Depends(require_owner)],
)
async def list_expired_sessions_endpoint(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> list[SessionSummary]:
    """List expired sessions that may need renewal."""
    await _set_project_rls(project_id, session)
    results = await list_sessions_by_project(session, project_id, state_filter=SessionState.EXPIRED)
    return [SessionSummary(**r) for r in results]


# ================================================================
# CLIENT-SIDE ENDPOINTS (M16-B)
# ================================================================

from fastapi import Header
from .client_service import (
    OnboardingAuthError,
    OnboardingClientError,
    OnboardingGoneError,
    authenticate_client_session,
    consume_magic_link_and_start,
    get_next_question,
    save_answer,
    submit_onboarding,
)
from .schemas import (
    ClientProgressResponse,
    ConsumeBody,
    ConsumeResponse,
    FinalSubmitBody,
    FinalSubmitResponse,
    NextQuestionResponse,
    SubmitAnswerBody,
    SubmitAnswerResponse,
)
# Batch B fix F-18: hashing canónico del token M12 (debe coincidir byte a byte
# para resolver el project_id del magic-link vía SECURITY DEFINER).
from backend.app.motors.m12_magic_link.service import _hash_token


async def _set_rls_from_onboarding_session(
    db: AsyncSession, session_id: uuid.UUID,
) -> None:
    """Fix F-18 (account-less · /me/*): resuelve (client_id, project_id) desde el
    session_id YA presente en el header, vía SECURITY DEFINER, y SETEA el contexto
    tenant ANTES de la lectura RLS de onboarding_sessions. Sin esto, en prod
    (fulkro_app · current_project_id()=NULL) la lectura es ciega (0 filas).
    Si el session_id no existe → no setea (authenticate_client_session dará el
    401 canónico)."""
    row = (await db.execute(
        text("SELECT client_id, project_id FROM get_onboarding_session_owner(:sid)"),
        {"sid": str(session_id)},
    )).first()
    if row is not None:
        await set_tenant_context(db, client_id=row.client_id, project_id=row.project_id)


async def require_onboarding_auth(
    x_onboarding_session_id: uuid.UUID = Header(...),
    x_onboarding_session_secret: str = Header(..., min_length=20),
    session: AsyncSession = Depends(get_db),
) -> OnboardingSession:
    """Dependency: validate client session_secret."""
    await _set_rls_from_onboarding_session(session, x_onboarding_session_id)
    try:
        return await authenticate_client_session(
            session, x_onboarding_session_id, x_onboarding_session_secret,
        )
    except OnboardingGoneError as exc:
        raise HTTPException(status_code=http_status.HTTP_410_GONE, detail=str(exc))
    except OnboardingAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


async def require_onboarding_auth_with_consent(
    onb: OnboardingSession = Depends(require_onboarding_auth),
    session: AsyncSession = Depends(get_db),
) -> OnboardingSession:
    """Gate Batch A diagnóstico previo (capa legal): exige consentimiento Art. 13
    registrado para la sesión ANTES de responder el cuestionario. Sin consent
    registrado → 403 'consent_required'. El consentimiento se registra vía
    POST /onboarding/me/consent (tras ver GET /onboarding/me/consent-text).
    """
    has_consent = (await session.execute(
        select(PreClienteDiagnosticConsent.id).where(
            PreClienteDiagnosticConsent.onboarding_session_id == onb.id,
            PreClienteDiagnosticConsent.consented.is_(True),
        ).limit(1)
    )).first()
    if has_consent is None:
        raise HTTPException(status_code=403, detail="consent_required")
    return onb


# ── Batch A diagnóstico previo · capa legal (Art. 13 + consentimiento) ──
class ConsentTextResponse(BaseModel):
    version: str
    text: str


class ConsentBody(BaseModel):
    consented: bool


class ConsentRecordResponse(BaseModel):
    recorded: bool
    version: str


@router.get("/me/consent-text", response_model=ConsentTextResponse)
async def consent_text_endpoint(
    onb=Depends(require_onboarding_auth),
) -> ConsentTextResponse:
    """Texto Art. 13 versionado que el lead ve ANTES de responder."""
    return ConsentTextResponse(
        version=ART13_PRECLIENTE_VERSION, text=ART13_PRECLIENTE_TEXT,
    )


@router.post("/me/consent", response_model=ConsentRecordResponse)
async def record_consent_endpoint(
    body: ConsentBody,
    request: Request,
    onb=Depends(require_onboarding_auth),
    session: AsyncSession = Depends(get_db),
) -> ConsentRecordResponse:
    """Registra el consentimiento del lead (append-only · version + IP + UA).

    El servidor FIJA la versión que sirve (ART13_PRECLIENTE_VERSION · integridad
    legal · no se confía la versión al cliente). interés legítimo art. 6.1.f.
    """
    if not body.consented:
        raise HTTPException(status_code=400, detail="consent_not_accepted")
    consent = PreClienteDiagnosticConsent(
        onboarding_session_id=onb.id,
        interlocutor_email=onb.interlocutor_email,
        consent_text_version=ART13_PRECLIENTE_VERSION,
        legal_basis="interes_legitimo_art_6_1_f",
        consented=True,
        consent_scope="diagnostic_questionnaire_data_processing",
        consented_at=datetime.now(timezone.utc),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    session.add(consent)
    await session.commit()
    return ConsentRecordResponse(
        recorded=True, version=ART13_PRECLIENTE_VERSION,
    )


@router.post("/consume", response_model=ConsumeResponse)
async def consume_endpoint(
    body: ConsumeBody,
    session: AsyncSession = Depends(get_db),
) -> ConsumeResponse:
    """Client enters with token (+OTP if required). Returns session_secret."""
    # Fix F-18 (account-less · /consume): el session_id vive DENTRO del magic-link
    # (chicken-and-egg · magic_links es RLS project_isolation). Resuelve el
    # project_id desde el token_hash vía SECURITY DEFINER y SETEA el contexto
    # ANTES de que consume lea magic_links + onboarding_sessions bajo RLS. Si el
    # token no resuelve → no setea → consume queda ciego → 401 (token inválido).
    project_id = (await session.execute(
        text("SELECT get_magic_link_project_by_token(:th)"),
        {"th": _hash_token(body.token)},
    )).scalar()
    if project_id is not None:
        await set_tenant_context(session, project_id=project_id)
    try:
        result = await consume_magic_link_and_start(session, body.token, body.otp)
    except OnboardingAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except OnboardingGoneError as exc:
        raise HTTPException(status_code=http_status.HTTP_410_GONE, detail=str(exc))
    except OnboardingClientError as exc:
        raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    await session.commit()
    return ConsumeResponse(**result)


@router.get("/me/next-question", response_model=NextQuestionResponse)
async def next_question_endpoint(
    onb=Depends(require_onboarding_auth_with_consent),
    session: AsyncSession = Depends(get_db),
) -> NextQuestionResponse:
    try:
        result = await get_next_question(session, onb)
    except OnboardingClientError as exc:
        raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    return NextQuestionResponse(**result)


@router.post("/me/responses", response_model=SubmitAnswerResponse)
async def save_answer_endpoint(
    body: SubmitAnswerBody,
    onb=Depends(require_onboarding_auth_with_consent),
    session: AsyncSession = Depends(get_db),
) -> SubmitAnswerResponse:
    try:
        result = await save_answer(session, onb, body.question_id, body.answer_value)
    except OnboardingClientError as exc:
        raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    await session.commit()
    return SubmitAnswerResponse(**result)


@router.post("/me/submit", response_model=FinalSubmitResponse)
async def submit_endpoint(
    body: FinalSubmitBody,
    onb=Depends(require_onboarding_auth),
    session: AsyncSession = Depends(get_db),
) -> FinalSubmitResponse:
    try:
        result = await submit_onboarding(session, onb, body.allow_partial)
    except OnboardingClientError as exc:
        raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    await session.commit()
    return FinalSubmitResponse(**result)


@router.get("/me/progress", response_model=ClientProgressResponse)
async def client_progress_endpoint(
    onb=Depends(require_onboarding_auth),
    session: AsyncSession = Depends(get_db),
) -> ClientProgressResponse:
    from sqlalchemy import distinct
    from backend.app.models.onboarding import OnboardingResponse

    total = onb.total_questions or 0
    answered = onb.answered_questions or 0
    progress = round(100.0 * answered / total, 1) if total > 0 else 0.0

    r = await session.execute(
        select(distinct(OnboardingResponse.section)).where(OnboardingResponse.session_id == onb.id)
    )
    answered_sections = [row[0] for row in r.all()]

    return ClientProgressResponse(
        session_id=onb.id,
        state=onb.estado,
        total_questions=total,
        answered_questions=answered,
        progress_percentage=progress,
        sections_completed=answered_sections,
        sections_partial=[],
    )


# ================================================================
# CONNECTOR ENDPOINTS (M16-C)
# ================================================================

from .connectors.base import ConnectorProvider
# Trigger connector registration via imports
from .connectors import microsoft365 as _m365  # noqa: F401
from .connectors import github_connector as _gh  # noqa: F401
from .connectors import google_workspace as _gw  # noqa: F401
from .connectors import aws_connector as _aws  # noqa: F401
from .connectors import azure_connector as _az  # noqa: F401
from .discovery_service import (
    DiscoveryServiceError,
    configure_connector,
    list_connectors,
    run_discovery,
    validate_connector,
)


class ConfigureConnectorBody(BaseModel):
    provider: ConnectorProvider
    credentials: dict
    scopes: Optional[str] = None


@router.post(
    "/projects/{project_id}/connectors/configure",
    dependencies=[Depends(require_owner)],
)
async def configure_connector_endpoint(
    project_id: uuid.UUID,
    body: ConfigureConnectorBody,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    try:
        result = await configure_connector(session, project_id, body.provider, body.credentials, body.scopes)
    except DiscoveryServiceError as exc:
        raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    await session.commit()
    return result


@router.post(
    "/projects/{project_id}/connectors/{provider}/validate",
    dependencies=[Depends(require_owner)],
)
async def validate_connector_endpoint(
    project_id: uuid.UUID,
    provider: ConnectorProvider,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    try:
        result = await validate_connector(session, project_id, provider)
    except DiscoveryServiceError as exc:
        raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    await session.commit()
    return result


@router.post(
    "/projects/{project_id}/connectors/{provider}/discover",
    dependencies=[Depends(require_owner)],
)
async def run_discovery_endpoint(
    project_id: uuid.UUID,
    provider: ConnectorProvider,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    try:
        result = await run_discovery(session, project_id, provider)
    except DiscoveryServiceError as exc:
        raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    await session.commit()
    return result


@router.get(
    "/projects/{project_id}/connectors",
    dependencies=[Depends(require_owner)],
)
async def list_connectors_endpoint(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    return await list_connectors(session, project_id)


# ================================================================
# PKG ENDPOINTS (M16-E)
# ================================================================

from . import pkg_service as pkg
from .pkg_ingest_service import PKGIngestError, ingest_from_onboarding, ingest_from_discovery


@router.get(
    "/projects/{project_id}/pkg/summary",
    dependencies=[Depends(require_owner)],
)
async def pkg_summary_endpoint(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    return await pkg.get_project_summary(session, project_id)


@router.get(
    "/projects/{project_id}/pkg/nodes",
    dependencies=[Depends(require_owner)],
)
async def pkg_list_nodes_endpoint(
    project_id: uuid.UUID,
    node_type: Optional[str] = Query(None),
    label: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    if node_type:
        return await pkg.get_nodes_by_type(session, project_id, node_type, label_contains=label)
    nodes = []
    for nt in sorted(pkg.NODE_TYPES):
        nodes.extend(await pkg.get_nodes_by_type(session, project_id, nt, label_contains=label))
    return nodes[:500]


@router.get(
    "/projects/{project_id}/pkg/nodes/{node_id}",
    dependencies=[Depends(require_owner)],
)
async def pkg_node_detail_endpoint(
    project_id: uuid.UUID,
    node_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    node = await pkg.get_node(session, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="Nodo no encontrado")
    return node


@router.get(
    "/projects/{project_id}/pkg/nodes/{node_id}/neighbors",
    dependencies=[Depends(require_owner)],
)
async def pkg_neighbors_endpoint(
    project_id: uuid.UUID,
    node_id: uuid.UUID,
    edge_type: Optional[str] = Query(None),
    direction: str = Query("both", pattern="^(outgoing|incoming|both)$"),
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    return await pkg.get_neighbors(session, node_id, edge_type, direction)


@router.post(
    "/projects/{project_id}/pkg/ingest-from-onboarding/{session_id}",
    dependencies=[Depends(require_owner)],
)
async def pkg_ingest_onboarding_endpoint(
    project_id: uuid.UUID,
    session_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    try:
        result = await ingest_from_onboarding(session, project_id, session_id)
    except PKGIngestError as exc:
        raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))


    await session.commit()
    return result
# ================================================================
# PKG TOOLS ENDPOINTS (M16-F)
# ================================================================

from .pkg_tools_registry import call_tool as _call_tool, list_tools as _list_tools


@router.get("/tools")
async def list_pkg_tools_endpoint():
    """List PKG tools available for M11 Copiloto. Anthropic tool-use format."""
    tools = _list_tools()
    return {"tools": tools, "total": len(tools)}


@router.post(
    "/projects/{project_id}/tools/{tool_name}",
    dependencies=[Depends(require_owner)],
)
async def call_pkg_tool_endpoint(
    project_id: uuid.UUID,
    tool_name: str,
    session: AsyncSession = Depends(get_db),
):
    """Invoke a specific PKG tool against a project."""
    await _set_project_rls(project_id, session)
    try:
        result = await _call_tool(tool_name, {"project_id": str(project_id)}, session)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await session.commit()
    return result


@router.post(
    "/projects/{project_id}/pkg/ingest-from-discovery/{provider}",
    dependencies=[Depends(require_owner)],
)
async def pkg_ingest_discovery_endpoint(
    project_id: uuid.UUID,
    provider: str,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    from backend.app.models.onboarding import ConnectorConfig as CC
    r = await session.execute(
        select(CC).where(CC.project_id == project_id, CC.provider == provider)
    )
    config = r.scalar_one_or_none()
    if config is None:
        raise HTTPException(status_code=404, detail=f"Connector {provider} no configurado")
    try:
        result = await ingest_from_discovery(session, project_id, config.id)
    except PKGIngestError as exc:
        raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))


    await session.commit()
    return result
def _suggest_dicat_by_sector(sector, assets_count, identities_count):
    """Sugerencia conservadora D/I/C/A/T según sector + tamaño."""
    sug = {"D": "MEDIO", "I": "MEDIO", "C": "MEDIO", "A": "MEDIO", "T": "MEDIO"}
    if not sector:
        return sug
    s = sector.lower()
    if "salud" in s or "sanita" in s:
        sug.update({"C": "ALTO", "I": "ALTO"})
    elif "fintech" in s or "financi" in s or "banca" in s:
        sug.update({"C": "ALTO", "I": "ALTO", "T": "ALTO"})
    elif "administrac" in s or "publ" in s or "aapp" in s:
        sug.update({"D": "ALTO", "I": "ALTO", "T": "ALTO"})
    elif "industria" in s or "energi" in s:
        sug.update({"D": "ALTO", "I": "ALTO"})
    if identities_count > 500 and sug["D"] == "MEDIO":
        sug["D"] = "ALTO"
    return sug


# ═══════════════════════════════════════════════════════════════
# Mini-LMS endpoints (Sesion 6)
# ═══════════════════════════════════════════════════════════════

from . import lms_service as lms

class LmsAssignBody(BaseModel):
    course_codigo: str
    empleados: list[dict]


class LmsQuizSubmitBody(BaseModel):
    respuestas: dict[str, str]
    cliente_razon: str


class LmsAttendanceBody(BaseModel):
    cliente_razon: str


def _serialize_lms_assignment(a) -> dict:
    return {
        "id": str(a.id),
        "project_id": str(a.project_id),
        "course_codigo": a.course_codigo,
        "course_titulo": a.course_titulo,
        "course_duracion_minutos": a.course_duracion_minutos,
        "asistente_nombre": a.asistente_nombre,
        "asistente_email": a.asistente_email,
        "asistente_cargo": a.asistente_cargo,
        "asistente_organizacion": a.asistente_organizacion,
        "estado": a.estado,
        "asignado_at": a.asignado_at.isoformat() if a.asignado_at else None,
        "iniciado_at": a.iniciado_at.isoformat() if a.iniciado_at else None,
        "completado_at": a.completado_at.isoformat() if a.completado_at else None,
        "due_date": a.due_date.isoformat() if a.due_date else None,
        "quiz_score": a.quiz_score,
        "quiz_pass": a.quiz_pass,
        "e502_path": a.e502_path,
        "e502_hash": a.e502_hash,
        "e503_path": a.e503_path,
        "e503_hash": a.e503_hash,
    }


@router.get("/lms/courses")
async def lms_list_courses():
    """Catalogo publico de cursos LMS disponibles (sin respuestas)."""
    return {"courses": lms.list_courses()}


@router.get("/lms/courses/{codigo}")
async def lms_get_course(codigo: str):
    course = lms.get_course(codigo)
    if course is None:
        raise HTTPException(status_code=404, detail=f"Curso '{codigo}' no encontrado")
    # No exponer respuestas correctas en GET publico
    public = {k: v for k, v in course.items() if k != "quiz"}
    public["quiz"] = {
        "pass_score": course.get("quiz", {}).get("pass_score", 70),
        "preguntas": [
            {
                "id": q["id"],
                "enunciado": q["enunciado"],
                "opciones": q["opciones"],
            }
            for q in course.get("quiz", {}).get("preguntas", [])
        ],
    }
    return public


@router.post(
    "/projects/{project_id}/lms/assign",
    dependencies=[Depends(require_owner)],
)
async def lms_assign(
    project_id: uuid.UUID,
    body: LmsAssignBody,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    try:
        assignments = await lms.LmsService(session).assign_to_employees(
            project_id, body.course_codigo, body.empleados,
        )
    except lms.LmsValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except lms.LmsNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await session.commit()
    return {"assignments": [_serialize_lms_assignment(a) for a in assignments]}


@router.get(
    "/projects/{project_id}/lms/assignments",
    dependencies=[Depends(require_owner)],
)
async def lms_list_assignments(
    project_id: uuid.UUID,
    course_codigo: str | None = Query(None),
    estado: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    items = await lms.LmsService(session).list_by_project(
        project_id, course_codigo=course_codigo, estado=estado,
    )
    return {"assignments": [_serialize_lms_assignment(a) for a in items]}


@router.post(
    "/lms/assignments/{assignment_id}/attendance",
    dependencies=[Depends(require_owner)],
)
async def lms_record_attendance(
    assignment_id: uuid.UUID,
    body: LmsAttendanceBody,
    session: AsyncSession = Depends(get_db),
):
    row = (await session.execute(
        text("SELECT project_id FROM lms_assignments WHERE id = :aid AND deleted_at IS NULL"),
        {"aid": str(assignment_id)},
    )).first()
    if not row:
        raise HTTPException(status_code=404, detail="Asignacion no encontrada")
    await _set_project_rls(row[0], session)
    try:
        a = await lms.LmsService(session).record_attendance(
            assignment_id, cliente_razon=body.cliente_razon,
        )
    except lms.LmsStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except lms.LmsError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await session.commit()
    return _serialize_lms_assignment(a)


@router.post(
    "/lms/assignments/{assignment_id}/submit-quiz",
    dependencies=[Depends(require_owner)],
)
async def lms_submit_quiz(
    assignment_id: uuid.UUID,
    body: LmsQuizSubmitBody,
    session: AsyncSession = Depends(get_db),
):
    row = (await session.execute(
        text("SELECT project_id FROM lms_assignments WHERE id = :aid AND deleted_at IS NULL"),
        {"aid": str(assignment_id)},
    )).first()
    if not row:
        raise HTTPException(status_code=404, detail="Asignacion no encontrada")
    await _set_project_rls(row[0], session)
    try:
        a = await lms.LmsService(session).submit_quiz(
            assignment_id,
            respuestas=body.respuestas,
            cliente_razon=body.cliente_razon,
        )
    except lms.LmsStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except lms.LmsValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except lms.LmsError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await session.commit()
    return _serialize_lms_assignment(a)


@router.get(
    "/projects/{project_id}/lms/progress",
    dependencies=[Depends(require_owner)],
)
async def lms_progress(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    return await lms.LmsService(session).get_progress(project_id)


# ═══════════════════════════════════════════════════════════════
# GAP 1: Export onboarding → M1 Categorization
# ═══════════════════════════════════════════════════════════════

@router.get(
    "/projects/{project_id}/onboarding/export-categorization",
    dependencies=[Depends(require_owner)],
)
async def export_for_categorization(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    """Exporta datos del onboarding útiles para pre-rellenar M1 categorización.

    Retorna: sector, sistemas/servicios descubiertos, identidades,
    dimensiones DICAT sugeridas heurística por sector+tamaño.
    """
    await _set_project_rls(project_id, session)

    from backend.app.models.onboarding import (
        DiscoveredAsset, DiscoveredIdentity, OnboardingSession,
    )
    from collections import Counter

    ob = (await session.execute(
        select(OnboardingSession).where(
            OnboardingSession.project_id == project_id,
        ).order_by(OnboardingSession.created_at.desc()).limit(1)
    )).scalar_one_or_none()
    sector = ob.sector if ob else None

    assets = list((await session.execute(
        select(DiscoveredAsset).where(
            DiscoveredAsset.project_id == project_id,
            DiscoveredAsset.deleted_at.is_(None),
        )
    )).scalars().all())

    identities = list((await session.execute(
        select(DiscoveredIdentity).where(
            DiscoveredIdentity.project_id == project_id,
            DiscoveredIdentity.deleted_at.is_(None),
        )
    )).scalars().all())

    asset_types = Counter(getattr(a, "tipo", None) or "unknown" for a in assets)
    dicat = _suggest_dicat_by_sector(sector, len(assets), len(identities))

    def _name(a):
        return getattr(a, "nombre", None) or getattr(a, "name", None) or ""

    sistemas = [
        {"nombre": _name(a), "tipo": getattr(a, "tipo", None)}
        for a in assets
        if (getattr(a, "tipo", "") or "").lower() in ("system", "server", "application", "host")
    ][:50]
    servicios = [
        {"nombre": _name(a), "tipo": getattr(a, "tipo", None)}
        for a in assets
        if (getattr(a, "tipo", "") or "").lower() in ("service", "api", "endpoint")
    ][:50]

    return {
        "project_id": str(project_id),
        "sector": sector,
        "sistemas": sistemas,
        "servicios": servicios,
        "asset_types_breakdown": dict(asset_types),
        "identities_count": len(identities),
        "dimensiones_sugeridas": dicat,
        "total_assets": len(assets),
    }
