"""Cliente Portal API · m_cloud_connectors (sub-atom 1.D.X.B v3.12).

4 endpoints REST cliente (auth: ``require_client_user`` · ADR-013):

  GET  /api/v1/client-portal/cloud-connectors                       list project resumen
  POST /api/v1/client-portal/cloud-connectors/connect/{provider}    init OAuth flow (reuse M16)
  GET  /api/v1/client-portal/cloud-connectors/providers/catalog     catalog UI cards
  POST /api/v1/client-portal/cloud-connectors/{id}/request-disconnect
       Sesión 3B-2B.8 Phase 1C · audit_log + chat thread mediation (ADR-014 sostained
       · NO actual disconnect cliente · admin actua post chat).

Diseño R29 firmísimo:
- NO exponer scopes técnicos ni IDs internos M16
- friendly_message generado por provider/status (sin presión coercitiva)
- OAuth flow init delega a M16 portal_api existing (NO duplicar)
- Cliente "Salta y conecta después" siempre OK · backend NO impone gates

ADR-013 doble pool auth: pool cliente vía ``require_client_user``.
ADR-014 read-only OAuth sostained: request-disconnect NO ejecuta revoke · chat-mediated.
ADR-025 reuse infrastructure: ChatService + sse_dispatcher + audit_log existing (sub-atom 5.A).
"""
from __future__ import annotations

import json as _json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_client_user
from backend.app.database import get_db, set_tenant_context
from backend.app.models.auth import User as AuthUser
from backend.app.motors.m_cloud_connectors.models import (
    CloudConnector,
    CloudConnectorProvider,
    CloudConnectorStatus,
)
from backend.app.motors.m_cloud_connectors.digest_service import (
    build_client_digest_view,
    get_latest_digest_for_project,
    get_previous_digest_for_project,
)
from backend.app.motors.m_cloud_connectors.schemas import (
    ClientDigestResponse,
    ClientDigestView,
    CloudConnectorClientListResponse,
    CloudConnectorPublicSummary,
    ProviderCatalogItem,
    ProviderCatalogResponse,
)
from backend.app.motors.m_cloud_connectors.service import (
    CloudConnectorService,
    list_provider_catalog,
)


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/client-portal/cloud-connectors",
    tags=["Cloud Connectors (1.D.X.B) - Cliente"],
)


# ==================================================================
# Helpers cliente
# ==================================================================


def _friendly_message(status: str, provider: str, resources_count: int) -> str:
    """Mensaje cliente-friendly R29 (sin presión · congrats tone)."""
    pretty_provider = provider.replace("_", " ").title()
    if status == CloudConnectorStatus.CONNECTED.value:
        if resources_count == 0:
            return (
                f"✓ {pretty_provider} conectado · sincronizando información en breve."
            )
        return (
            f"✓ {pretty_provider} conectado · {resources_count} elementos detectados."
        )
    if status == CloudConnectorStatus.SYNCING.value:
        return f"Sincronizando {pretty_provider} · esto tarda unos segundos."
    if status == CloudConnectorStatus.SYNC_ERROR.value:
        return (
            f"{pretty_provider} tuvo un problema al sincronizar · "
            "tu consultor lo revisará."
        )
    if status == CloudConnectorStatus.REVOKED.value:
        return f"{pretty_provider} desconectado · puedes volver a conectarlo cuando quieras."
    if status == CloudConnectorStatus.EXPIRED.value:
        return f"{pretty_provider} requiere reautorizar · es rápido."
    return f"{pretty_provider} esperando autorización."


async def _emit_audit_log(
    db: AsyncSession,
    *,
    accion: str,
    project_id: uuid.UUID,
    client_id: uuid.UUID,
    user_email: str | None,
    payload: dict,
    registro_id: uuid.UUID | None = None,
) -> None:
    """Emit audit_log entry cliente.cloud_connector.* · Sub-atom 5.A 3-way OR pattern.

    Mirrors pattern Phase 1A+1B (m02_magerit.portal_api · m21_portal_cliente.api) ·
    project_id + client_id propagated · payload JSON serializable.
    """
    await db.execute(text(
        "INSERT INTO audit_log (id, tabla, registro_id, accion, usuario, "
        "project_id, client_id, payload_new, timestamp) "
        "VALUES (gen_random_uuid(), 'cloud_connectors', :rid, "
        ":accion, :user, :pid, :cid, :payload, now())"
    ), {
        "rid": str(registro_id) if registro_id is not None else str(project_id),
        "accion": accion,
        "user": (user_email or "cliente")[:255],
        "pid": str(project_id),
        "cid": str(client_id),
        "payload": _json.dumps(payload),
    })


async def _resolve_client_project_id(
    db: AsyncSession,
    client_user: AuthUser,
) -> uuid.UUID:
    """Lookup project_id activo del cliente vía client_id (pattern m21).

    Cliente piloto single-project. Si múltiples projects → toma el más reciente.
    """
    cid = getattr(client_user, "client_id", None)
    if cid is None:
        raise HTTPException(
            status_code=403, detail="Cliente sin client_id asociado",
        )
    row = (await db.execute(
        text(
            "SELECT id FROM projects WHERE client_id = :cid "
            "AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 1"
        ),
        {"cid": str(cid)},
    )).fetchone()
    if not row:
        raise HTTPException(
            status_code=404, detail="Project no encontrado para este cliente",
        )
    return uuid.UUID(str(row[0]))


# ==================================================================
# Catalog providers (mismo catalog admin · public cliente)
# ==================================================================


@router.get("/providers/catalog", response_model=ProviderCatalogResponse)
async def get_providers_catalog_client(
    client_user: AuthUser = Depends(require_client_user),
) -> ProviderCatalogResponse:
    """Catalog providers · cliente consume para grid cards onboarding."""
    return ProviderCatalogResponse(
        items=[ProviderCatalogItem(**p) for p in list_provider_catalog()],
    )


# ==================================================================
# List connectors (cliente vista resumida)
# ==================================================================


@router.get("", response_model=CloudConnectorClientListResponse)
async def list_my_cloud_connectors(
    client_user: AuthUser = Depends(require_client_user),
    db: AsyncSession = Depends(get_db),
) -> CloudConnectorClientListResponse:
    """Lista conectores del project del cliente · resumen R29 friendly."""
    project_id = await _resolve_client_project_id(db, client_user)
    await set_tenant_context(db, project_id=project_id)

    svc = CloudConnectorService(db)
    connectors = await svc.list_connectors(
        project_id=project_id, include_revoked=False,
    )
    items = [
        CloudConnectorPublicSummary(
            id=c.id,
            provider=c.provider,
            status=c.status,
            last_sync_at=c.last_sync_at,
            resources_count=c.last_sync_resources_count,
            friendly_message=_friendly_message(
                c.status, c.provider, c.last_sync_resources_count,
            ),
        )
        for c in connectors
    ]

    # Sesión 3B-2B.8 Phase 1C · audit_log emit cliente.cloud_connector.viewed
    # con project_id + client_id Sub-atom 5.A 3-way OR pattern.
    await _emit_audit_log(
        db,
        accion="cliente.cloud_connector.viewed",
        project_id=project_id,
        client_id=client_user.client_id,  # type: ignore[arg-type]
        user_email=client_user.email,
        payload={
            "connectors_count": len(items),
            "connected_count": sum(
                1 for c in connectors if c.status == CloudConnectorStatus.CONNECTED.value
            ),
        },
    )
    await db.commit()

    return CloudConnectorClientListResponse(
        items=items, project_id=project_id,
    )


# ==================================================================
# Init OAuth flow (delega a M16 portal_api existing reuse · ADR-025)
# ==================================================================


# B1 · mapeo del provider del catálogo cliente (CloudConnectorProvider) al
# connector_type de M16 onboarding (SUPPORTED_OAUTH_PROVIDERS). El flujo OAuth
# real (state + authorize_url + callback) vive ÍNTEGRAMENTE en M16 portal_api:
# el frontend llama a POST /portal/onboarding/projects/{pid}/connectors/
# {connector_type}/oauth-init con este connector_type y obtiene el authorize_url
# real. ADR-025: NO duplicar el OAuth state aquí.
_M16_OAUTH_CONNECTOR_TYPE: dict[str, str] = {
    CloudConnectorProvider.MICROSOFT_365.value: "microsoft",
    CloudConnectorProvider.GOOGLE_WORKSPACE.value: "google",
    CloudConnectorProvider.AZURE.value: "azure",
    CloudConnectorProvider.GITHUB.value: "github",
}


@router.post("/connect/{provider}", status_code=201)
async def init_connect_flow(
    provider: str,
    client_user: AuthUser = Depends(require_client_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Crea CloudConnector PENDING_OAUTH y delega init flow a M16 portal_api.

    Cliente UI redirige a authorize_url devuelto por M16 (NO duplicar OAuth
    state · ADR-025 sostener firmísimo).

    Returns:
        {"connector_id": "...", "provider": "...", "next_step": "..."}
    """
    # Validar provider
    try:
        provider_enum = CloudConnectorProvider(provider)
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail=f"Provider no soportado: {provider}",
        ) from exc

    project_id = await _resolve_client_project_id(db, client_user)
    await set_tenant_context(db, project_id=project_id)

    svc = CloudConnectorService(db)
    connector = await svc.link_or_create_connector(
        project_id=project_id,
        provider=provider_enum,
        m16_connector_config_id=None,  # cliente completará flow
        scopes=None,
    )

    # Sesión 3B-2B.8 Phase 1C · audit_log emit cliente.cloud_connector.connect_initiated
    # con project_id + client_id Sub-atom 5.A 3-way OR pattern.
    await _emit_audit_log(
        db,
        accion="cliente.cloud_connector.connect_initiated",
        project_id=project_id,
        client_id=client_user.client_id,  # type: ignore[arg-type]
        user_email=client_user.email,
        registro_id=connector.id,
        payload={
            "provider": provider,
            "connector_id": str(connector.id),
            "requires_oauth": provider_enum != CloudConnectorProvider.MANUAL_IMPORT,
        },
    )
    await db.commit()

    # MANUAL_IMPORT no necesita OAuth flow
    if provider_enum == CloudConnectorProvider.MANUAL_IMPORT:
        return {
            "connector_id": str(connector.id),
            "provider": provider,
            "next_step": "manual_upload",
            "message": "Sube tu Excel/CSV en la siguiente pantalla.",
        }

    # AWS usa credenciales (Access Key solo-lectura), NO OAuth · el flujo real
    # vive en M16 awsCredentials (pestaña Conexiones). Indicamos al frontend que
    # pida las credenciales en vez de redirigir a un authorize_url inexistente.
    if provider_enum == CloudConnectorProvider.AWS:
        return {
            "connector_id": str(connector.id),
            "provider": provider,
            "next_step": "aws_credentials",
            "message": (
                "AWS se conecta pegando una Access Key con permisos de solo "
                "lectura · lo hacemos en la pestaña Conexiones."
            ),
        }

    # OAuth providers · el frontend llama al endpoint M16 oauth-init REAL con el
    # connector_type mapeado + su redirect_uri y obtiene el authorize_url (el
    # state OAuth lo crea M16, fuente única · ADR-025 ADR-014 sostenidos).
    m16_connector_type = _M16_OAUTH_CONNECTOR_TYPE.get(provider)
    if m16_connector_type is None:
        raise HTTPException(
            status_code=400,
            detail=f"Provider {provider} no soporta conexión OAuth desde el portal.",
        )
    return {
        "connector_id": str(connector.id),
        "provider": provider,
        "next_step": "oauth_redirect",
        "m16_connector_type": m16_connector_type,
        "message": "Te llevamos a autorizar de forma segura · solo lectura.",
    }


# ==================================================================
# Request disconnect (Sesión 3B-2B.8 Phase 1C · chat-mediated)
# ==================================================================
# ADR-014 read-only OAuth sostained: cliente NO ejecuta revoke. El endpoint
# solo registra intent + crea chat thread con Marcos · admin decide y revoca.
# Sub-atom 5.A pattern (project_id + client_id 3-way OR audit_log).


class DisconnectRequestBody(BaseModel):
    """Payload cliente · solicitar desconexión conector cloud (chat-mediated)."""

    justification: str = Field(
        ..., min_length=1, max_length=1000,
        description="Razón cliente para desconectar · enviada a Marcos vía chat.",
    )


class DisconnectRequestResponse(BaseModel):
    """Respuesta R29 friendly · confirmación request registrada."""

    thread_id: str
    provider: str
    connector_id: str
    friendly_message: str


@router.post(
    "/{connector_id}/request-disconnect",
    response_model=DisconnectRequestResponse,
    status_code=202,
)
async def request_disconnect_connector(
    connector_id: uuid.UUID,
    body: DisconnectRequestBody,
    client_user: AuthUser = Depends(require_client_user),
    db: AsyncSession = Depends(get_db),
) -> DisconnectRequestResponse:
    """Cliente solicita desconectar conector · ADR-014 sostained.

    Effects (idempotent · best-effort SSE+notify):
      1. Validate connector pertenece al project del cliente
      2. audit_log INSERT cliente.cloud_connector.disconnect_requested (5.A)
      3. ChatService.get_or_create_thread + post_message con justification
      4. SSE dispatch cloud.connector.disconnect_requested (admin + cliente)

    NO ejecuta revoke · admin actua post chat (ADR-014 read-only enforce).
    """
    project_id = await _resolve_client_project_id(db, client_user)
    await set_tenant_context(db, project_id=project_id)

    # Lookup connector + validar pertenencia project
    connector = await db.get(CloudConnector, connector_id)
    if connector is None or connector.project_id != project_id:
        raise HTTPException(
            status_code=404, detail="Conector no encontrado en este proyecto",
        )

    provider_value = connector.provider
    pretty_provider = provider_value.replace("_", " ").title()
    justification = body.justification.strip()

    # 1) audit_log emit cliente.cloud_connector.disconnect_requested
    await _emit_audit_log(
        db,
        accion="cliente.cloud_connector.disconnect_requested",
        project_id=project_id,
        client_id=client_user.client_id,  # type: ignore[arg-type]
        user_email=client_user.email,
        registro_id=connector.id,
        payload={
            "provider": provider_value,
            "connector_id": str(connector.id),
            "justification_preview": justification[:200],
            "status_at_request": connector.status,
        },
    )

    # 2) Chat thread mediation · ADR-025 reuse ChatService existing
    from backend.app.motors.m21_portal_cliente.chat_service import (
        ChatService,
    )

    chat_svc = ChatService(db)
    thread = await chat_svc.get_or_create_thread(
        project_id=project_id,
        client_user_id=getattr(client_user, "id", None),
        subject=f"Desconectar {pretty_provider}",
    )
    chat_content = (
        f"Solicito desconectar **{pretty_provider}**.\n\n"
        f"Razón:\n{justification}\n\n"
        f"_Solicitud automática desde /cloud-connections · "
        f"connector_id {connector.id}_"
    )
    await chat_svc.post_message(
        thread_id=thread.id,
        sender_type="client",
        content=chat_content,
        sender_user_id=getattr(client_user, "id", None),
        metadata={
            "source": "cloud_connector_disconnect_request",
            "connector_id": str(connector.id),
            "provider": provider_value,
        },
    )

    # 3) SSE dispatch cloud.connector.disconnect_requested (admin + cliente subscribe)
    try:
        from backend.app.core.sse_dispatcher import sse_dispatcher

        await sse_dispatcher.dispatch(
            channel=f"project:{project_id}",
            event_type="cloud.connector.disconnect_requested",
            data={
                "connector_id": str(connector.id),
                "provider": provider_value,
                "thread_id": str(thread.id),
                "audience": "both",
            },
        )
    except Exception:
        # notify_best_effort pattern · SSE NO bloquea persistencia
        logger.exception("SSE dispatch cloud.connector.disconnect_requested failed")

    await db.commit()

    return DisconnectRequestResponse(
        thread_id=str(thread.id),
        provider=provider_value,
        connector_id=str(connector.id),
        friendly_message=(
            f"Solicitud registrada · Marcos ha sido notificado y te "
            f"contactará por chat para confirmar la desconexión de "
            f"{pretty_provider}."
        ),
    )


# ==================================================================
# Cliente digest visibility (sub-fase 1.D.X.VERIFY 2b)
# ==================================================================
# CRITICAL filter: schema ClientDigestView SEPARADO de AdminDigestSnapshot.
# Build mediante helper puro `build_client_digest_view` · NUNCA serializar
# CloudDigestSnapshot ORM directo (leak admin sensitive fields).


digest_router = APIRouter(
    prefix="/client-portal/cloud-monitoring",
    tags=["Cloud Connectors (1.D.X.VERIFY 2b) - Cliente Digest"],
)


@digest_router.get(
    "/digest/latest", response_model=ClientDigestResponse,
)
async def get_client_latest_digest(
    client_user: AuthUser = Depends(require_client_user),
    db: AsyncSession = Depends(get_db),
) -> ClientDigestResponse:
    """Cliente view del último digest mensual · FILTERED R29 friendly.

    NO leak admin sensitive: triggered_by_user_id, snapshot_jsonb raw,
    triggered_by internal codes, error details. Solo score + trend +
    summary_friendly + count alto-nivel.

    Si never generado → has_snapshot=False + empty state friendly.
    """
    project_id = await _resolve_client_project_id(db, client_user)
    await set_tenant_context(db, project_id=project_id)

    latest = await get_latest_digest_for_project(db, project_id)
    previous = (
        await get_previous_digest_for_project(
            db, project_id, before_id=latest.id,
        )
        if latest is not None
        else None
    )

    view_dict = build_client_digest_view(latest, previous)
    return ClientDigestResponse(digest=ClientDigestView(**view_dict))
