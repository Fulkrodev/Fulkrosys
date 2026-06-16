"""Motor 12 — Magic Link API endpoints.

Capa HTTP fina sobre MagicLinkService. Patron de seguridad:
- Endpoint /consume cachea MagicLinkError generico y devuelve 403 uniforme
- El motivo exacto del fallo se registra en logs (no en response) para
  evitar information leakage al atacante
- Endpoints protegidos (generate, revoke, status) requieren tenant context
- Endpoint publico /consume valida solo por token (sin tenant context)
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db, set_tenant_context
from backend.app.motors.m12_magic_link.schemas import (
    MagicLinkGenerateRequest,
    MagicLinkGenerateResponse,
    MagicLinkGenerateAndSendResponse,
    MagicLinkConsumeRequest,
    MagicLinkConsumeResponse,
    MagicLinkListItem,
    MagicLinkPublicStatus,
)
from backend.app.motors.m12_magic_link.service import (
    MagicLinkService,
    MagicLinkError,
    MagicLinkNotFoundError,
)
from backend.app.config import get_settings

router = APIRouter(prefix="/magic-links", tags=["Motor 12 - Magic Links"])


# ================================================================
# HELPERS
# ================================================================

async def _set_project_rls(project_id: UUID, db: AsyncSession):
    """Set RLS context for magic_links table via project owner lookup.

    Uses get_project_owner() SECURITY DEFINER function (same pattern
    as Motor 2 endpoints).
    """
    from sqlalchemy import text
    client_id = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
    )).scalar()
    if not client_id:
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, client_id=client_id, project_id=project_id)


# ================================================================
# ENDPOINT 1: Generate magic link (protegido)
# ================================================================

@router.post(
    "/generate",
    response_model=MagicLinkGenerateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_magic_link(
    body: MagicLinkGenerateRequest,
    response: "Response",
    db: AsyncSession = Depends(get_db),
    _owner=Depends(require_owner),
):
    """Genera un nuevo magic link. Requiere tenant context (RLS).

    El token plano se devuelve UNA SOLA VEZ en la response. El OTP
    (si el purpose lo requiere) tambien se devuelve una sola vez.

    SAN-D MB-19.9 · ADR-042 · response header `X-Deprecated-Purpose` con
    razón si purpose es soft-deprecated (ONBOARDING_INICIAL/APORTE_EVIDENCIA).
    Backward compat: NO bloquea · cliente externo recibe warning.
    """
    await _set_project_rls(body.project_id, db)

    # ADR-042 · check policy pre-generation para incluir header Deprecation
    # si aplica (sin afectar lógica generación · enforcer corre también
    # dentro de svc.generate_magic_link · doble-check uniforme).
    from backend.app.motors.m12_magic_link.policy_enforcer import (
        MagicLinkPolicyEnforcer,
    )
    enforcer = MagicLinkPolicyEnforcer()
    _, policy_status, policy_reason = enforcer.validate_purpose(body.purpose)
    if policy_status == "deprecated_soft":
        response.headers["X-Deprecated-Purpose"] = policy_reason
        response.headers["X-Deprecation-Refs"] = "ADR-042"

    settings = get_settings()
    svc = MagicLinkService(db)
    try:
        ml_response = await svc.generate_magic_link(body, base_url=settings.app_base_url)
        await db.commit()
        return ml_response
    except ValueError as e:  # pragma: no cover — Pydantic validates purpose enum before this
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )


# ================================================================
# ENDPOINT 1.bis: Generate + SEND magic link por email (#11 · botón manual)
# ================================================================

@router.post(
    "/generate-and-send",
    response_model=MagicLinkGenerateAndSendResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_and_send_magic_link(
    body: MagicLinkGenerateRequest,
    db: AsyncSession = Depends(get_db),
    _owner=Depends(require_owner),
):
    """#11 · Genera el magic link y lo ENVÍA por email en un solo paso (manual).

    Hasta ahora la plataforma generaba el enlace + renderizaba la plantilla de
    email, pero Marcos lo enviaba a mano (copia/pega). Este endpoint cierra ese
    fleco: un botón que genera + dispara el envío real vía EmailSender (mock en
    dev · SMTP/Postmark en prod). El envío lo decide Marcos (manual), NO es
    automático. El token plano sólo existe aquí (en BD vive hasheado), por eso
    el envío ocurre en la generación y no como reenvío por id.

    Reutiliza MagicLinkService.generate + render_email_for_magic_link +
    EmailSender.send (OPS-026 DRY). Si el purpose no tiene plantilla de email
    el enlace SÍ se genera y se reporta email_sent=False + email_error (honesto).

    SEGURIDAD (review adversarial): el OTP NUNCA viaja en el mismo email que el
    enlace (anularía el segundo factor). Para purposes con OTP el email lleva
    SOLO el enlace y el OTP se devuelve en la response (`otp`) para que Marcos lo
    transmita por canal separado — coherente con el modelo del motor ("OTP por
    canal separado"). El INSERT del enlace respeta RLS (fulkro_app), igual que
    /generate; el rol fulkro se usa SOLO para el lookup de nombres y se revierte.
    """
    from sqlalchemy import text

    from backend.app.core.email.sender import get_email_sender
    from backend.app.motors.m12_magic_link.emails.renderer import (
        render_email_for_magic_link,
    )

    # Resolver client_id + nombres bajo rol fulkro, luego REVERTIR a fulkro_app
    # para que la generación (INSERT magic_links) respete RLS como en /generate.
    client_id = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(body.project_id)}
    )).scalar()
    if not client_id:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    name_row = (await db.execute(
        text(
            "SELECT p.nombre, c.nombre, c.cif FROM projects p "
            "LEFT JOIN clients c ON c.id = p.client_id WHERE p.id = :pid"
        ),
        {"pid": str(body.project_id)},
    )).first()
    await db.execute(text("RESET ROLE"))  # vuelve a fulkro_app · RLS enforced

    await set_tenant_context(db, client_id=client_id, project_id=body.project_id)

    settings = get_settings()
    svc = MagicLinkService(db)
    ml = await svc.generate_magic_link(body, base_url=settings.app_base_url)

    proyecto_nombre = (name_row[0] if name_row else None) or "Proyecto ENS"
    cliente_razon = (name_row[1] if name_row else None) or ""
    cliente_cif = (name_row[2] if name_row else None) or ""

    email_sent = False
    email_backend = ""
    email_message_id: str | None = None
    email_error: str | None = None
    try:
        subject, html, text_body = render_email_for_magic_link(
            purpose=body.purpose,
            link_url=ml.url,
            expires_at=ml.expires_at,
            cliente={"razon_social": cliente_razon, "cif": cliente_cif},
            proyecto={"nombre": proyecto_nombre},
            destinatario={
                "nombre": "",
                "cargo": "",
                "email": str(body.recipient_email),
            },
            otp=None,  # NUNCA el OTP en el email del enlace · va por canal aparte
        )
        if body.custom_subject:
            subject = body.custom_subject
        sender = get_email_sender()
        result = await sender.send(
            db,
            to=str(body.recipient_email),
            subject=subject,
            html_body=html,
            text_body=text_body,
            template_used=f"magic_link:{body.purpose.value}",
            magic_link_id=ml.magic_link_id,
            client_id=client_id,
            cc=body.cc_emails,
        )
        email_sent = result.ok
        email_backend = result.backend_used
        email_message_id = result.message_id
        if not result.ok:
            email_error = result.error
    except ValueError as exc:
        # purpose sin plantilla de email · el enlace ya está generado (honesto)
        email_error = f"sin plantilla de email para purpose: {exc}"
        logger.warning("generate-and-send sin plantilla: {}", str(exc))

    await db.commit()
    return MagicLinkGenerateAndSendResponse(
        magic_link_id=ml.magic_link_id,
        url=ml.url,
        expires_at=ml.expires_at,
        purpose=ml.purpose,
        action_label=ml.action_label,
        otp=ml.otp,  # presente sólo si el purpose lo requiere · relay canal aparte
        email_sent=email_sent,
        email_backend=email_backend,
        email_message_id=email_message_id,
        email_error=email_error,
        recipient_email=str(body.recipient_email),
    )


# ================================================================
# ENDPOINT 2: Consume magic link (PUBLICO — sin auth)
# ================================================================

@router.post(
    "/consume",
    response_model=MagicLinkConsumeResponse,
    status_code=status.HTTP_200_OK,
)
async def consume_magic_link(
    body: MagicLinkConsumeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Consume un magic link presentando el token (+ OTP si requerido).

    Endpoint PUBLICO sin auth. Patron de seguridad: cualquier error
    de validacion devuelve 403 con mensaje generico para no revelar
    al atacante por que fallo. El motivo exacto va a logs internos.
    """
    enriched = body.model_copy(update={
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    })

    # Consume does NOT need tenant context — it looks up by token_hash
    # using a direct query that bypasses RLS (token_hash is unique across
    # all projects). The RLS policy on magic_links requires project context,
    # so we need admin access for the lookup.
    from sqlalchemy import text
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))

    svc = MagicLinkService(db)
    try:
        response = await svc.consume_magic_link(enriched)
        await db.commit()
        return response
    except MagicLinkError as e:
        logger.warning(
            "Magic link consume failed: {}: {}",
            type(e).__name__, str(e),
        )
        # Commit otp_failures increment if applicable
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid magic link",
        )


# ================================================================
# ENDPOINT 3: Revoke magic link (protegido)
# ================================================================

@router.post(
    "/{magic_link_id}/revoke",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_magic_link(
    magic_link_id: UUID,
    db: AsyncSession = Depends(get_db),
    _owner=Depends(require_owner),
):
    """Revoca un magic link activo. Idempotente. Solo owner (admin)."""
    # Need admin to look up the link first (RLS chicken-and-egg).
    # require_owner garantiza que el caller es admin antes del bypass de RLS.
    from sqlalchemy import text
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))

    svc = MagicLinkService(db)
    try:
        await svc.revoke_magic_link(magic_link_id)
        await db.commit()
    except MagicLinkNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Magic link not found",
        )


# ================================================================
# ENDPOINT 5: List magic links (admin · FASE 4.5 sub-bloque B.1)
# ================================================================

@router.get(
    "",
    response_model=list[MagicLinkListItem],
)
async def list_magic_links(
    project_id: UUID | None = None,
    purpose: str | None = None,
    active_only: bool = False,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_owner),
):
    """List magic links filtered (admin only · pattern require_owner).

    Filtros opcionales:
    - project_id: scope a un proyecto concreto
    - purpose: filtrar por tipo_operacion (string del enum backend)
    - active_only: solo links no revocados, no expirados, no agotados
    - limit: max rows (default 50)

    Bypassa RLS via SET LOCAL ROLE fulkro_app_bypassrls porque admin puede ver
    todos los proyectos. Coherente con pattern m29 admin endpoints.
    """
    from sqlalchemy import text
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))

    svc = MagicLinkService(db)
    links = await svc.list_magic_links(
        project_id=project_id,
        purpose=purpose,
        active_only=active_only,
        limit=limit,
    )
    return [
        MagicLinkListItem(
            id=link.id,
            project_id=link.project_id,
            tipo_operacion=link.tipo_operacion,
            recipient_email=link.recipient_email,
            cc_emails=link.cc_emails,
            custom_subject=link.custom_subject,
            expira_at=link.expira_at,
            max_usos=link.max_usos,
            usos=link.usos,
            revocado=link.revocado,
            revoked_at=link.revoked_at,
            sent_to_contact_id=link.sent_to_contact_id,
            created_at=link.created_at,
        )
        for link in links
    ]


# ================================================================
# ENDPOINT 6: Public status by token (público · FASE 4.5 sub-bloque B.1)
# ================================================================

@router.get(
    "/by-token/{token}",
    response_model=MagicLinkPublicStatus,
)
async def get_magic_link_by_token(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Resuelve token plaintext → contexto público del magic link.

    Endpoint PÚBLICO (sin auth) para sign-flows pre-consume. NO consume
    usos ni expone secretos. Devuelve subset estricto:
    tipo_operacion, scope, expira_at, max_usos, usos, revocado,
    recipient_email_hint (enmascarado).

    Si token no existe o link soft-deleted → 404 sin detail (uniforme
    con /consume para evitar enumeration).
    """
    from sqlalchemy import text
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))

    svc = MagicLinkService(db)
    try:
        data = await svc.get_status_by_token(token)
    except MagicLinkNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Magic link not found",
        )
    return MagicLinkPublicStatus(**data)


# ================================================================
# ENDPOINT 4: Get magic link status (protegido, dashboard)
# ================================================================

@router.get(
    "/{magic_link_id}/status",
)
async def get_magic_link_status(
    magic_link_id: UUID,
    db: AsyncSession = Depends(get_db),
    _owner=Depends(require_owner),
):
    """Devuelve estado semantico del magic link para dashboard admin.

    Solo owner (admin): bypassa RLS, así que require_owner evita fuga de
    recipient_email/estado cross-tenant a usuarios no-admin.
    """
    from sqlalchemy import text
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))

    svc = MagicLinkService(db)
    try:
        return await svc.get_magic_link_status(magic_link_id)
    except MagicLinkNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Magic link not found",
        )
