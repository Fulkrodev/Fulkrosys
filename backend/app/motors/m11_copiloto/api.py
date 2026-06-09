"""Motor 11 -- ENS Copilot API endpoints.

Sprint C3: expansión de 1 a 8 endpoints.
- /copilot/chat (quick, sin persistencia — compat)
- CRUD conversaciones persistentes
- Chat dentro de conversación con historial
- Contexto y resumen del proyecto
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.agent_14_copiloto.service import (
    answer_question,
    stream_answer_question,
)
from backend.app.agents.agent_14_copiloto.types import CopilotQuery, PageContext
from backend.app.agents.copilot_project_state import build_project_state_block
from backend.app.database import get_db, set_tenant_context
from backend.app.models.audit_sim import AuditSimulationRun
from backend.app.models.copilot import CopilotConversation, CopilotMessage
from backend.app.motors.m11_copiloto.conversation_service import (
    get_recent_messages,
)
from backend.app.models.documents import Evidence
from backend.app.models.ens import DdaEntry
from backend.app.models.findings import Finding
from backend.app.motors.m08_verification.models import VerificationFinding
from backend.app.auth.dependencies import require_owner
from backend.app.agents.copilot_rate_limit import (
    CopilotRateLimitExceeded,
    enforce_rate_limit_or_raise,
)


router = APIRouter(
    tags=["Motor 11 - Copiloto ENS"],
    # TODO-RBAC-PER-ENDPOINT-001 Cat A: Marcos-only.
    dependencies=[Depends(require_owner)],
)


async def _set_project_rls(project_id: uuid.UUID, db: AsyncSession) -> uuid.UUID:
    """Sets RLS tenant context para project_id · returns owning client_id.

    Sesión 3B-2B.4 Phase 2.2 · return value used to populate
    CopilotConversation.client_id (foundation memoria per cliente).
    """
    client_id = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
    )).scalar()
    if not client_id:
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, client_id=client_id, project_id=project_id)
    return uuid.UUID(str(client_id)) if not isinstance(client_id, uuid.UUID) else client_id


async def _set_client_rls(client_id: uuid.UUID, db: AsyncSession) -> None:
    """Sets RLS tenant context para CROSS-PROJECT per cliente queries.

    Sesión 3B-2B.4 Phase 2.3 (OPTION 1) · audit Phase 1.5 finding A fix.

    Sets app.current_client_id = client_id AND explicitly clears
    app.current_project_id (empty string → current_project_id() returns NULL).
    Esto habilita policy `copilot_isolation` OR clause:
      client_id = current_client_id()
    a satisfacerse cleanly sin interferencia de stale project context
    desde requests previos sharing same session/transaction.

    Defence-in-depth: caller debe ADEMÁS filtrar WHERE client_id = :client_id
    en query SQL (belt + suspenders).
    """
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_id)},
    )
    # Explicit clear · current_project_id() returns NULL via NULLIF('', '')::uuid
    await db.execute(
        text("SELECT set_config('app.current_project_id', '', true)"),
    )


# ══════════════════ Schemas ══════════════════

class PageContextSchema(BaseModel):
    url: Optional[str] = None
    client_id: Optional[str] = None
    project_phase: Optional[str] = None
    active_motor: Optional[str] = None


class CopilotChatRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    project_id: Optional[str] = None
    model: Optional[str] = None
    max_tokens: Optional[int] = Field(None, ge=100, le=4000)
    page_context: Optional[PageContextSchema] = None


class QuickAction(BaseModel):
    id: str
    label: str
    icon: str
    prefill_query: str


def _to_page_context(schema: Optional[PageContextSchema]) -> Optional[PageContext]:
    if schema is None:
        return None
    return PageContext(
        url=schema.url,
        client_id=schema.client_id,
        project_phase=schema.project_phase,
        active_motor=schema.active_motor,
        # current_screen = pathname (para el screen_references_catalog admin).
        current_screen=schema.url,
    )


async def _build_admin_page_context(
    db: AsyncSession,
    schema: Optional[PageContextSchema],
    project_id: Optional[str],
) -> Optional[PageContext]:
    """PageContext admin enriquecido con estado de proyecto EN VIVO (role=admin).

    2026-06-09 · si hay project_id, fija el contexto RLS y compone el bloque
    "Estado actual del proyecto" (compute_workflow_state + métricas) para que el
    copiloto admin conozca el proyecto activo. Best-effort: si el proyecto no es
    accesible (404 RLS) o algo falla, se omite el estado sin romper el chat.
    """
    pc = _to_page_context(schema) or PageContext()
    if pc.current_screen is None:
        pc.current_screen = pc.url
    if project_id:
        try:
            await _set_project_rls(uuid.UUID(str(project_id)), db)
            state = await build_project_state_block(db, project_id, "admin")
            pc.project_state = state or None
        except HTTPException:
            # Proyecto no encontrado / no accesible → chat sigue sin estado.
            pass
        except Exception:  # noqa: BLE001 · best-effort
            logger.exception("admin project_state build failed · pid={}", project_id)
    return pc


class CopilotChatResponse(BaseModel):
    answer: str
    citations_found: list[str]
    chunk_ids_used: list[str]
    not_in_corpus: bool
    low_grounding_confidence: bool
    model_used: str
    tokens_input: int
    tokens_output: int
    latency_ms: int
    interaction_log_id: Optional[int] = None


class CreateConversationBody(BaseModel):
    titulo: str = Field(..., min_length=2, max_length=300)
    modelo_default: Optional[str] = Field(None, max_length=60)
    autor: str = Field("marcos", max_length=200)


class ConversationChatBody(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)
    model: Optional[str] = None
    max_tokens: Optional[int] = Field(None, ge=100, le=4000)
    include_project_context: bool = True


# ══════════════════ Serializers ══════════════════

def _serialize_conv(c: CopilotConversation) -> dict:
    return {
        "id": str(c.id),
        "project_id": str(c.project_id) if c.project_id else None,
        # Sesión 3B-2B.4 Phase 2.2 · cliente scope visible para memoria
        # per cliente queries · backward-compat null para rows legacy
        # antes backfill.
        "client_id": str(c.client_id) if c.client_id else None,
        "titulo": c.titulo,
        "modelo_default": c.modelo_default,
        "autor": c.autor,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _serialize_msg(m: CopilotMessage) -> dict:
    return {
        "id": str(m.id),
        "conversation_id": str(m.conversation_id),
        "role": m.role,
        "content": m.content,
        "citations": m.citations,
        "chunk_ids_used": m.chunk_ids_used,
        "model_used": m.model_used,
        "tokens_input": m.tokens_input,
        "tokens_output": m.tokens_output,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


# ══════════════════ Endpoint compat ══════════════════

@router.post("/copilot/chat", response_model=CopilotChatResponse)
async def copilot_chat(
    body: CopilotChatRequest,
    db: AsyncSession = Depends(get_db),
    owner=Depends(require_owner),
):
    """Chat rápido sin persistencia (endpoint original)."""
    # Cap coste LLM admin (auditoría 2026-06-07 · etiqueta copilot_chat ya contada)
    try:
        await enforce_rate_limit_or_raise(db=db, user_id=owner.id, tier="admin")
    except CopilotRateLimitExceeded as exc:
        raise HTTPException(status_code=429, detail=exc.status.blocked_reason or "Rate limit")
    query = CopilotQuery(
        question=body.question,
        project_id=body.project_id,
        requested_model=body.model,
        max_tokens=body.max_tokens,
        page_context=await _build_admin_page_context(
            db, body.page_context, body.project_id,
        ),
        role="admin",
    )
    try:
        result = await answer_question(db, query)
        await db.commit()
        return CopilotChatResponse(
            answer=result.answer,
            citations_found=result.citations_found,
            chunk_ids_used=result.chunk_ids_used,
            not_in_corpus=result.not_in_corpus,
            low_grounding_confidence=result.low_grounding_confidence,
            model_used=result.model_used,
            tokens_input=result.tokens_input,
            tokens_output=result.tokens_output,
            latency_ms=result.latency_ms,
            interaction_log_id=result.interaction_log_id,
        )
    except Exception as exc:
        logger.exception("Copilot chat error: {}", exc)
        raise HTTPException(status_code=500, detail=f"Error en copiloto: {exc}")


@router.post("/copilot/chat/stream")
async def copilot_chat_stream(
    body: CopilotChatRequest,
    db: AsyncSession = Depends(get_db),
    owner=Depends(require_owner),
):
    """Chat con streaming SSE de tokens desde el LLM (anthropic/claude-sonnet)."""
    # Cap coste LLM admin antes de abrir el stream (copilot_chat_stream contada)
    try:
        await enforce_rate_limit_or_raise(db=db, user_id=owner.id, tier="admin")
    except CopilotRateLimitExceeded as exc:
        raise HTTPException(status_code=429, detail=exc.status.blocked_reason or "Rate limit")
    query = CopilotQuery(
        question=body.question,
        project_id=body.project_id,
        requested_model=body.model,
        max_tokens=body.max_tokens,
        page_context=await _build_admin_page_context(
            db, body.page_context, body.project_id,
        ),
        role="admin",
    )

    async def _generator():
        try:
            async for frame in stream_answer_question(db, query):
                yield frame
            await db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Copilot stream error: {}", exc)
            import json as _json
            payload = _json.dumps({"type": "error", "error": str(exc)}, ensure_ascii=False)
            yield f"data: {payload}\n\n"

    return StreamingResponse(
        _generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ══════════════════ Quick actions catalog ══════════════════

_QUICK_ACTIONS_BY_CONTEXT: dict[str, list[dict]] = {
    "default": [
        {"id": "summary_active_project", "label": "Resumen del proyecto activo",
         "icon": "FileText", "prefill_query": "Dame un resumen del estado actual del proyecto."},
        {"id": "today_focus", "label": "¿Qué toca hoy?",
         "icon": "Calendar", "prefill_query": "¿Qué tareas o hitos del proyecto deberían atenderse hoy?"},
        {"id": "dda_status", "label": "Estado DdA",
         "icon": "ListChecks", "prefill_query": "¿Cuál es el estado de la declaración de aplicabilidad del proyecto?"},
    ],
    "magerit": [
        {"id": "magerit_top_risks", "label": "Top 5 riesgos",
         "icon": "AlertTriangle", "prefill_query": "Dame los 5 riesgos MAGERIT con mayor impacto residual del proyecto."},
        {"id": "magerit_untreated", "label": "Riesgos sin tratamiento",
         "icon": "ShieldAlert", "prefill_query": "Lista los riesgos del proyecto que no tienen plan de tratamiento."},
        {"id": "magerit_critical_assets", "label": "Activos críticos",
         "icon": "Server", "prefill_query": "¿Cuáles son los activos críticos del proyecto y por qué?"},
        {"id": "magerit_summary", "label": "Resumen MAGERIT",
         "icon": "BarChart3", "prefill_query": "Dame un resumen del análisis MAGERIT del proyecto."},
    ],
    "obligations": [
        {"id": "obligations_pending", "label": "Obligaciones pendientes",
         "icon": "Clock", "prefill_query": "¿Qué obligaciones del ENS quedan pendientes en el proyecto?"},
        {"id": "obligations_due", "label": "Próximos vencimientos",
         "icon": "CalendarClock", "prefill_query": "Dame las obligaciones con vencimiento en los próximos 30 días."},
        {"id": "obligations_by_family", "label": "Cumplimiento por familia ENS",
         "icon": "Layers", "prefill_query": "Resumen de cumplimiento por familia de medidas ENS."},
    ],
    "conformity": [
        {"id": "conformity_status", "label": "Estado conformidad",
         "icon": "BadgeCheck", "prefill_query": "¿Cuál es el estado de conformidad ENS del proyecto?"},
        {"id": "conformity_findings", "label": "Hallazgos abiertos",
         "icon": "AlertCircle", "prefill_query": "Lista los hallazgos de conformidad abiertos del proyecto."},
        {"id": "conformity_roadmap", "label": "Roadmap",
         "icon": "Map", "prefill_query": "¿Qué roadmap de conformidad recomiendas para el proyecto?"},
    ],
    "diagnosis": [
        {"id": "diagnosis_summary", "label": "Resumen diagnóstico",
         "icon": "FileSearch", "prefill_query": "Resumen del diagnóstico inicial del proyecto."},
        {"id": "diagnosis_gaps", "label": "Brechas detectadas",
         "icon": "GitPullRequestArrow", "prefill_query": "Brechas más relevantes detectadas en el diagnóstico."},
    ],
    "evidence": [
        {"id": "evidence_pending", "label": "Evidencias pendientes",
         "icon": "FileX", "prefill_query": "Lista las evidencias pendientes de aportar."},
        {"id": "evidence_expiring", "label": "Evidencias por caducar",
         "icon": "TimerReset", "prefill_query": "Evidencias que caducan en los próximos 30 días."},
    ],
}


@router.get("/copilot/quick-actions")
async def get_quick_actions(
    context: Optional[str] = Query(None, max_length=40),
    project_id: Optional[uuid.UUID] = Query(None),
) -> list[QuickAction]:
    """Catalog of suggested copilot prompts filtered by active page context.

    No DB / LLM — pure look-up. ``context`` matches one of the keys in the
    hardcoded catalog (magerit, obligations, conformity, diagnosis,
    evidence). Unknown or missing context returns the ``default`` set.
    """
    key = (context or "default").lower()
    actions = _QUICK_ACTIONS_BY_CONTEXT.get(key) or _QUICK_ACTIONS_BY_CONTEXT["default"]
    return [QuickAction(**a) for a in actions]


# ══════════════════ Workflow state hint (Sesión 3B-2B.8 Phase 1D) ══════════════════


class BlockerOut(BaseModel):
    """Bloqueo del workflow (cross-actor) · expuesto al sidebar admin (FASE 2)."""

    motor: str
    description: str
    waiting_on: str  # admin · cliente · external_auditor · system


class WorkflowHintResponse(BaseModel):
    """Top action hint cliente o admin · workflow-aware."""

    has_action: bool
    message: str  # description per role
    priority: str  # urgent · normal · low
    target_url: Optional[str] = None
    motor: Optional[str] = None
    action: Optional[str] = None
    current_phase: str
    # FASE 2 gobierno: blockers del scanner (separación roles · cadencia comité ·
    # DdA-firma · pentest · ENAC) agrupables por waiting_on en el sidebar admin.
    # La lógica vive en _detect_blockers (NO se recalcula · solo se expone).
    blockers: list[BlockerOut] = []
    # #22 Ola 5 · medidas aplicables SIN evidencia válida (cruce semáforo #20) ·
    # admin R30 (códigos ENS · jerga · NUNCA cliente). El front las pinta como
    # "te faltan evidencias en …".
    evidence_gaps: list[str] = []


@router.get("/copilot/hint", response_model=WorkflowHintResponse)
async def get_copilot_hint_admin(
    project_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> WorkflowHintResponse:
    """Workflow-aware next-action hint (admin role) · Phase 1D.

    Reuse pure functional workflow_state_scanner.compute_workflow_state
    (mirror compute_dda_evidence_gaps Phase C3 pattern). Backward-compat:
    si scanner raises → returns has_action=False sin pánico (try/except).
    """
    from backend.app.motors.m11_copiloto.workflow_state_scanner import (
        WorkflowScannerOptions,
        compute_workflow_state,
        top_action_for_role,
    )

    await _set_project_rls(project_id, db)
    try:
        state = await compute_workflow_state(
            db, project_id,
            options=WorkflowScannerOptions(role_filter="admin"),
        )
    except Exception:
        logger.exception("compute_workflow_state failed · backward-compat fallback")
        return WorkflowHintResponse(
            has_action=False,
            message="Sin sugerencias proactivas en este momento.",
            priority="low",
            current_phase="unknown",
        )

    # FASE 2: expone state.blockers (NO recalcula · _detect_blockers ya los puso).
    blockers_out = [
        BlockerOut(motor=b.motor, description=b.description, waiting_on=b.waiting_on)
        for b in state.blockers
    ]

    top = top_action_for_role(state, "admin")
    if top is None:
        return WorkflowHintResponse(
            has_action=False,
            message="Todo al día · sin acciones pendientes.",
            priority="low",
            current_phase=state.current_phase,
            blockers=blockers_out,
            evidence_gaps=state.evidence_gap_measures,
        )

    # audit_log emit copilot.hint.generated · Sub-atom 5.A pattern
    # NO bloquea response (best-effort try/except)
    try:
        import json as _json
        await db.execute(text(
            "INSERT INTO audit_log (id, tabla, registro_id, accion, usuario, "
            "project_id, payload_new, timestamp) "
            "VALUES (gen_random_uuid(), 'copilot_hints', :pid, "
            "'copilot.hint.generated', 'admin', :pid, :payload, now())"
        ), {
            "pid": str(project_id),
            "payload": _json.dumps({
                "role": "admin",
                "phase": state.current_phase,
                "priority": top.priority,
                "action": top.action,
                "motor": top.motor,
            }),
        })
        await db.commit()
    except Exception:
        logger.exception("audit_log copilot.hint.generated emit failed")

    # #22 · cruce del semáforo: nombra las medidas con evidencia pendiente.
    message = top.description_admin
    if state.evidence_gap_measures:
        message += (
            " · Te faltan evidencias en: "
            + ", ".join(state.evidence_gap_measures)
            + "."
        )

    return WorkflowHintResponse(
        has_action=True,
        message=message,
        priority=top.priority,
        target_url=top.target_url,
        motor=top.motor,
        action=top.action,
        current_phase=state.current_phase,
        blockers=blockers_out,
        evidence_gaps=state.evidence_gap_measures,
    )


# ══════════════════ Projects list para selector de memoria (#23) ══════════════════

@router.get("/copilot/projects")
async def list_copilot_memory_projects(
    db: AsyncSession = Depends(get_db),
):
    """Lista proyectos activos para el selector de memoria del copiloto admin (#23).

    Admin-only (router require_owner). Devuelve el project_id REAL (NO el
    client_id) · imprescindible porque los endpoints de conversación van keyed
    por project_id (get_project_owner).

    RLS empírico (audit #23): `projects` tiene FORCE RLS con policy
    `client_id = current_client_id()` y `clients` NO tiene RLS. Por eso NO se
    puede hacer un JOIN directo sin contexto (deny-by-default → 0 filas). Se
    itera por cliente (legible sin RLS) fijando el contexto de cada uno para
    revelar SU proyecto · production-safe sin SET ROLE ni migración. Volumen
    acotado (cartera de Marcos · 1 proyecto/cliente R27).
    """
    clients = (await db.execute(text(
        "SELECT id, nombre FROM clients WHERE deleted_at IS NULL ORDER BY nombre ASC"
    ))).fetchall()

    out: list[dict] = []
    for client_id, client_name in clients:
        # Fija el contexto RLS de este cliente (transaction-local) para que la
        # policy `client_isolation` de projects revele sus proyectos.
        await db.execute(
            text("SELECT set_config('app.current_client_id', :cid, true)"),
            {"cid": str(client_id)},
        )
        rows = (await db.execute(text(
            """
            SELECT id, nombre, categoria_objetivo, fase
            FROM projects
            WHERE client_id = :cid
              AND deleted_at IS NULL
              AND (lifecycle_state IS NULL
                   OR lifecycle_state NOT IN ('ARCHIVED', 'PURGED'))
            ORDER BY created_at DESC
            """
        ), {"cid": str(client_id)})).fetchall()
        for pid, pnombre, categoria, fase in rows:
            out.append({
                "project_id": str(pid),
                "nombre": pnombre,
                "categoria_objetivo": categoria,
                "fase": fase,
                "cliente_nombre": client_name,
            })

    # Limpia el contexto de cliente al terminar (no filtrar a queries posteriores
    # de la misma transacción · defence-in-depth).
    await db.execute(text("SELECT set_config('app.current_client_id', '', true)"))

    return {"projects": out}


# ══════════════════ Push proactivo admin · briefing (#22 Ola 5) ══════════════════

@router.get("/copilot/admin-nudges")
async def list_admin_nudges(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Avisos proactivos admin recientes (in-app) para el briefing del copiloto.

    Los escribe el beat coach-scan-pending-admin-nudges como NotificationEvent
    event_type='admin.copilot.nudge'. Lectura cross-project admin → bypass RLS
    via SET LOCAL ROLE fulkro_app_bypassrls (mirror /admin/notifications · notifications/api.py).
    Discriminador limpio por event_type · NO mezcla con notificaciones cliente.
    """
    await db.execute(
        text("SELECT set_config('app.current_role_pool', 'marcos', true)")
    )
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    rows = (await db.execute(text(
        "SELECT id, project_id, payload_jsonb, created_at "
        "FROM notification_events "
        "WHERE event_type = :et AND deleted_at IS NULL "
        "ORDER BY created_at DESC LIMIT :lim"
    ), {"et": "admin.copilot.nudge", "lim": limit})).mappings().all()

    nudges = []
    for r in rows:
        payload = r["payload_jsonb"] or {}
        nudges.append({
            "id": str(r["id"]),
            "project_id": str(r["project_id"]) if r["project_id"] else None,
            "project_nombre": payload.get("project_nombre"),
            "title": payload.get("title"),
            "message": payload.get("message"),
            "motor": payload.get("motor"),
            "phase": payload.get("phase"),
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        })
    return {"nudges": nudges}


# ══════════════════ Conversations CRUD ══════════════════

@router.post(
    "/projects/{project_id}/copilot/conversations",
    status_code=http_status.HTTP_201_CREATED,
)
async def create_conversation(
    project_id: uuid.UUID,
    body: CreateConversationBody,
    db: AsyncSession = Depends(get_db),
):
    # Sesión 3B-2B.4 Phase 2.2 · capture client_id derived desde RLS lookup
    # · populate CopilotConversation.client_id habilita memoria per cliente
    # queries (cross-project) sin re-JOIN projects en hot path.
    client_id = await _set_project_rls(project_id, db)
    conv = CopilotConversation(
        project_id=project_id,
        client_id=client_id,
        titulo=body.titulo,
        modelo_default=body.modelo_default,
        autor=body.autor,
    )
    db.add(conv)
    await db.flush()
    return _serialize_conv(conv)


@router.get("/projects/{project_id}/copilot/conversations")
async def list_conversations(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    res = await db.execute(
        select(CopilotConversation)
        .where(
            CopilotConversation.project_id == project_id,
            CopilotConversation.deleted_at.is_(None),
        )
        .order_by(CopilotConversation.created_at.desc())
    )
    return {"conversations": [_serialize_conv(c) for c in res.scalars().all()]}


@router.get("/clients/{client_id}/copilot/conversations")
async def list_conversations_per_client(
    client_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List todas conversaciones del cliente cross-project · memoria per cliente.

    Sesión 3B-2B.4 Phase 2.2 · audit Phase 0 D2 gap A foundation. Permite
    Marcos super-vision recall context "hablé con cliente X hace 3 meses
    sobre Y" sin tener que recordar qué proyecto activo.

    Phase 2.3 (OPTION 1 · audit Phase 1.5 finding A fix):
    - Sets _set_client_rls(client_id) PRIMERO · habilita RLS OR clause
      `client_id = current_client_id()` (policy `copilot_isolation`)
    - Mantiene WHERE client_id = :client_id explicit filter (defence-in-depth)
    - require_owner gate-keeps acceso admin Marcos only
    """
    await _set_client_rls(client_id, db)
    res = await db.execute(
        select(CopilotConversation)
        .where(
            CopilotConversation.client_id == client_id,
            CopilotConversation.deleted_at.is_(None),
        )
        .order_by(CopilotConversation.created_at.desc())
        .limit(limit)
    )
    return {"conversations": [_serialize_conv(c) for c in res.scalars().all()]}


@router.get("/projects/{project_id}/copilot/conversations/{conversation_id}")
async def get_conversation(
    project_id: uuid.UUID,
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    conv = (await db.execute(
        select(CopilotConversation).where(
            CopilotConversation.id == conversation_id,
            CopilotConversation.project_id == project_id,
        )
    )).scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    msgs = (await db.execute(
        select(CopilotMessage)
        .where(CopilotMessage.conversation_id == conversation_id)
        .order_by(CopilotMessage.created_at.asc())
    )).scalars().all()
    return {
        **_serialize_conv(conv),
        "messages": [_serialize_msg(m) for m in msgs],
    }


@router.delete("/projects/{project_id}/copilot/conversations/{conversation_id}")
async def delete_conversation(
    project_id: uuid.UUID,
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    conv = (await db.execute(
        select(CopilotConversation).where(
            CopilotConversation.id == conversation_id,
            CopilotConversation.project_id == project_id,
        )
    )).scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return {"ok": True}


@router.post(
    "/projects/{project_id}/copilot/conversations/{conversation_id}/chat",
    status_code=http_status.HTTP_201_CREATED,
)
async def conversation_chat(
    project_id: uuid.UUID,
    conversation_id: uuid.UUID,
    body: ConversationChatBody,
    db: AsyncSession = Depends(get_db),
    owner=Depends(require_owner),
):
    """Envía mensaje a una conversación y persiste user+assistant."""
    # Cap coste LLM admin (auditoría 2026-06-07)
    try:
        await enforce_rate_limit_or_raise(db=db, user_id=owner.id, tier="admin")
    except CopilotRateLimitExceeded as exc:
        raise HTTPException(status_code=429, detail=exc.status.blocked_reason or "Rate limit")
    await _set_project_rls(project_id, db)
    conv = (await db.execute(
        select(CopilotConversation).where(
            CopilotConversation.id == conversation_id,
            CopilotConversation.project_id == project_id,
        )
    )).scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # E-4 · memoria por proyecto entre conversaciones: precarga los últimos
    # turnos de ESTE hilo ANTES de persistir el mensaje actual (si no, la
    # pregunta se duplicaría en el historial). El copiloto recuerda el hilo.
    prior_messages = await get_recent_messages(
        db, conversation_id=conversation_id, limit=8
    )
    history = [
        {"role": m.role, "content": m.content}
        for m in prior_messages
        if m.role in ("user", "assistant")
    ]

    # Persistir mensaje user
    user_msg = CopilotMessage(
        conversation_id=conversation_id,
        project_id=project_id,
        role="user",
        content=body.content,
    )
    db.add(user_msg)
    await db.flush()

    # Llamar al copiloto (con contexto opcional + memoria del hilo)
    # 2026-06-09 · RLS ya fijado arriba (_set_project_rls) · compone el estado
    # EN VIVO del proyecto (role=admin) cuando se pide contexto de proyecto.
    project_state = None
    if body.include_project_context:
        try:
            project_state = (
                await build_project_state_block(db, project_id, "admin")
            ) or None
        except Exception:  # noqa: BLE001 · best-effort
            logger.exception(
                "conversation_chat project_state failed · pid={}", project_id,
            )
    query = CopilotQuery(
        question=body.content,
        project_id=str(project_id) if body.include_project_context else None,
        requested_model=body.model or conv.modelo_default,
        max_tokens=body.max_tokens,
        page_context=PageContext(project_state=project_state),
        role="admin",
        history=history,
    )
    try:
        result = await answer_question(db, query)
    except Exception as exc:
        logger.exception("Conversation chat error: {}", exc)
        raise HTTPException(status_code=500, detail=f"Error en copiloto: {exc}")

    # Persistir mensaje assistant
    assistant_msg = CopilotMessage(
        conversation_id=conversation_id,
        project_id=project_id,
        role="assistant",
        content=result.answer,
        citations={"list": result.citations_found},
        chunk_ids_used={"list": result.chunk_ids_used},
        model_used=result.model_used,
        tokens_input=result.tokens_input,
        tokens_output=result.tokens_output,
    )
    db.add(assistant_msg)
    await db.flush()

    return {
        "user_message": _serialize_msg(user_msg),
        "assistant_message": _serialize_msg(assistant_msg),
        "answer": result.answer,
        "citations_found": result.citations_found,
        "not_in_corpus": result.not_in_corpus,
    }


# ══════════════════ Project context + summary ══════════════════

async def _get_project_context(db: AsyncSession, project_id: uuid.UUID) -> dict:
    """Recolecta contexto estructurado del proyecto para grounding del LLM."""
    # DdA status
    dda_rows = (await db.execute(
        select(DdaEntry.estado_implementacion, func.count(DdaEntry.id)).where(
            DdaEntry.project_id == project_id,
            DdaEntry.deleted_at.is_(None),
        ).group_by(DdaEntry.estado_implementacion)
    )).all()
    dda_summary = {row[0] or "sin_estado": row[1] for row in dda_rows}

    # Evidence status
    evidence_count = (await db.execute(
        select(func.count(Evidence.id)).where(
            Evidence.project_id == project_id,
            Evidence.deleted_at.is_(None),
        )
    )).scalar() or 0
    evidence_vigente = (await db.execute(
        select(func.count(Evidence.id)).where(
            Evidence.project_id == project_id,
            Evidence.vigente.is_(True),
            Evidence.deleted_at.is_(None),
        )
    )).scalar() or 0

    # Findings
    findings_count = (await db.execute(
        select(func.count(Finding.id)).where(
            Finding.project_id == project_id,
            Finding.deleted_at.is_(None),
        )
    )).scalar() or 0

    # Findings de verificacion tecnica v5.1 abiertos.
    pentest_count = (await db.execute(
        select(func.count(VerificationFinding.id)).where(
            VerificationFinding.project_id == project_id,
            VerificationFinding.deleted_at.is_(None),
            VerificationFinding.status.in_(("open", "needs_review")),
            VerificationFinding.zfp_gate5_classification.in_(
                ("confirmed", "probable"),
            ),
        )
    )).scalar() or 0

    # Last audit sim
    last_sim = (await db.execute(
        select(AuditSimulationRun).where(
            AuditSimulationRun.project_id == project_id,
        ).order_by(AuditSimulationRun.completed_at.desc().nulls_last()).limit(1)
    )).scalar_one_or_none()

    return {
        "project_id": str(project_id),
        "dda": {"by_estado": dda_summary, "total": sum(dda_summary.values())},
        "evidence": {"total": evidence_count, "vigente": evidence_vigente},
        "findings": {"total": findings_count},
        "pentest": {"findings_total": pentest_count},
        "last_audit_sim": {
            "score_global": last_sim.score_global if last_sim else None,
            "recomendacion": last_sim.recomendacion if last_sim else None,
            "nivel_madurez_global": last_sim.nivel_madurez_global if last_sim else None,
        } if last_sim else None,
    }


@router.post("/projects/{project_id}/copilot/context")
async def get_project_context(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Contexto estructurado del proyecto (grounding para LLM)."""
    await _set_project_rls(project_id, db)
    return await _get_project_context(db, project_id)


@router.get("/projects/{project_id}/copilot/summary")
async def get_project_summary(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Resumen del proyecto en lenguaje natural para Marcos."""
    await _set_project_rls(project_id, db)
    ctx = await _get_project_context(db, project_id)
    # Resumen determinista (no LLM)
    dda_total = ctx["dda"]["total"]
    dda_impl = ctx["dda"]["by_estado"].get("implantado", 0)
    pct = int(dda_impl / dda_total * 100) if dda_total else 0

    lines = [
        f"Proyecto {project_id}",
        f"DdA: {dda_total} medidas — {dda_impl} implantadas ({pct}%).",
        f"Evidencias: {ctx['evidence']['total']} total — {ctx['evidence']['vigente']} vigentes.",
        f"Findings abiertos: {ctx['findings']['total']}.",
        f"Pentest findings: {ctx['pentest']['findings_total']}.",
    ]
    if ctx["last_audit_sim"]:
        s = ctx["last_audit_sim"]
        lines.append(
            f"Última auditoría simulada: score {s['score_global']}/100, "
            f"nivel {s['nivel_madurez_global']}, recomendación: {s['recomendacion']}."
        )
    return {"summary": "\n".join(lines), "context": ctx}
