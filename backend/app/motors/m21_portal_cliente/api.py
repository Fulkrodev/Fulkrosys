"""M21 Portal Cliente — API (auth + portal views + cockpit Marcos)."""
from __future__ import annotations

import base64
import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import io

logger = logging.getLogger(__name__)

from fastapi import (
    APIRouter, Cookie, Depends, Header, HTTPException, Query, Request, Response,
    status,
)
from fastapi.responses import StreamingResponse
from pathlib import Path as _Path
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth import crypto
from backend.app.auth.dependencies import require_owner
from backend.app.config import get_settings
from backend.app.database import get_db
from backend.app.models.auth import User
from backend.app.models.client_portal import (
    ClientUser, ClientUserAudit,
)
from backend.app.motors.m21_portal_cliente import auth_service
from backend.app.motors.m21_portal_cliente.auth_service import AuthError
from backend.app.motors.m21_portal_cliente.scopes import PORTAL_SCOPE


bearer_scheme = HTTPBearer(auto_error=False)
CLIENT_SESSION_COOKIE = "fulkro_session"
CLIENT_CSRF_COOKIE = "fulkro_csrf"
CLIENT_CSRF_HEADER = "x-csrf-token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


# ════════════════════════════════════════════════════════════════════
# Cookie helpers (BLOQUE 1 Mini-Fase 3.5 — auth unificado cookie httpOnly)
# ════════════════════════════════════════════════════════════════════

def _set_client_session_cookies(
    response: Response,
    *,
    session_token: str,
    csrf_token: str,
    expires_at: datetime,
) -> None:
    """Setea cookies httpOnly fulkro_session + no-httpOnly fulkro_csrf
    post-login cliente.

    Patrón triple binding (ADR-019, BLOQUE 4 Mini-Fase 3.5): el csrf
    también está embebido como claim ``csrf`` del JWT session_token.
    Validación posterior en get_current_client_user requiere los 3
    sincronizados (header X-CSRF-Token == cookie fulkro_csrf == JWT
    claim). Replica patrón admin (backend/app/auth/api.py:64 +
    dependencies.py:53-65).

    Cookie común con admin (mismo nombre fulkro_session, misma keypair
    Ed25519) — dispatch backend distingue por sub claim del JWT (admin
    UUID literal vs cliente "client:<uuid>").

    Compat backward intencional durante BLOQUES 1-4: access_token sigue
    en LoginResponse body. BLOQUE 5 frontend lo eliminará.
    """
    max_age = int((expires_at - datetime.now(timezone.utc)).total_seconds())
    if max_age < 0:
        max_age = 0
    secure_cookies = get_settings().is_production
    response.set_cookie(
        key=CLIENT_SESSION_COOKIE,
        value=session_token,
        max_age=max_age,
        httponly=True,
        secure=secure_cookies,
        samesite="strict",
        path="/",
    )
    response.set_cookie(
        key=CLIENT_CSRF_COOKIE,
        value=csrf_token,
        max_age=max_age,
        httponly=False,  # Frontend JS lee para enviar en X-CSRF-Token
        secure=secure_cookies,
        samesite="strict",
        path="/",
    )


def _clear_client_session_cookies(response: Response) -> None:
    """Borra ambas cookies (session + csrf) en logout cliente."""
    for key in (CLIENT_SESSION_COOKIE, CLIENT_CSRF_COOKIE):
        response.delete_cookie(key=key, path="/", samesite="strict")


auth_router = APIRouter(prefix="/client-auth", tags=["Portal Cliente Auth"])
portal_router = APIRouter(
    prefix="/client-portal", tags=["Portal Cliente"],
)
cockpit_router = APIRouter(
    prefix="/clients/{client_id}/users",
    tags=["Cockpit - Usuarios cliente"],
    # H32 fix (sub-fase 5.A FASE 5 — audit pre-FASE 5): cockpit es
    # Marcos-only (gestión users de cualquier cliente). Sin require_owner
    # un cliente autenticado podría escalate y crear/borrar usuarios en
    # su propio cliente. Global dep auth + ownership check explícito aquí.
    dependencies=[Depends(require_owner)],
)
# Acceso de soporte trazado (impersonation READ-ONLY admin → portal cliente).
# Router separado del cockpit (prefijo distinto · no cuelga de /users).
# require_owner: SOLO el admin abre la puerta de soporte.
support_router = APIRouter(
    prefix="/clients/{client_id}",
    tags=["Cockpit - Acceso de soporte"],
    dependencies=[Depends(require_owner)],
)


# ════════════════════════════════════════════════════════════════════
# Dependencies
# ════════════════════════════════════════════════════════════════════

async def get_current_client_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    fulkro_session: str | None = Cookie(
        None, alias=CLIENT_SESSION_COOKIE,
    ),
    cookie_csrf: str | None = Cookie(
        None, alias=CLIENT_CSRF_COOKIE,
    ),
    header_csrf: str | None = Header(None, alias=CLIENT_CSRF_HEADER),
    db: AsyncSession = Depends(get_db),
) -> ClientUser:
    """Verifica sesión cliente con dual auth + CSRF triple binding.

    Auth (BLOQUE 2 Mini-Fase 3.5):
    - Acepta cookie fulkro_session (preferida) o Authorization Bearer.
    - Cookie tiene prioridad: browser maneja automática, no
      manipulable por JS attacker.
    - Bearer support permanece hasta BLOQUE 7 final cleanup.

    CSRF (BLOQUE 4 Mini-Fase 3.5, patrón triple binding ADR-019):
    - Solo aplica a métodos NO seguros (POST/PUT/DELETE/PATCH).
    - GET/HEAD/OPTIONS pasan sin CSRF (idempotentes).
    - Valida que header X-CSRF-Token == cookie fulkro_csrf == JWT
      claim "csrf" (las 3 sincronizadas). Si cualquier mismatch → 403.
    - Replica patrón admin dependencies.py:53-65.
    """
    token: str | None = None
    if fulkro_session:
        token = fulkro_session
    elif credentials and credentials.credentials:
        token = credentials.credentials

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing session cookie or bearer token",
        )
    try:
        user, _session = await auth_service.verify_session(db, token)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc),
        )

    # CSRF triple binding en métodos mutating
    if request.method.upper() not in SAFE_METHODS:
        try:
            payload = crypto.decode_token(token)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token (CSRF check)",
            )
        payload_csrf = payload.get("csrf")
        if (
            not header_csrf
            or not cookie_csrf
            or not payload_csrf
            or not crypto.constant_time_eq(header_csrf, payload_csrf)
            or not crypto.constant_time_eq(cookie_csrf, payload_csrf)
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="csrf token mismatch",
            )

    return user


# ADR-013 v3 single-user-RW: usuarios portal cliente tienen acceso uniforme
# read+write a todos los recursos de su cliente. Reemplaza require_scope(X)
# del legacy multi-role · pre-MB-3 cleanup.
require_active_client_user = get_current_client_user


# ════════════════════════════════════════════════════════════════════
# Schemas
# ════════════════════════════════════════════════════════════════════

class LoginBody(BaseModel):
    email: EmailStr
    password: str
    # CLUSTER 6 Phase 6A · MFA TOTP code o backup code (opcional).
    # Si cliente opt-in MFA · primer request omite mfa_code → 401 con
    # ``requires_mfa: True`` · segundo request envía code.
    mfa_code: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: str
    must_change_password: bool
    full_name: Optional[str]


class ChangePasswordBody(BaseModel):
    old_password: str
    # Sin min_length: la política (8-16 + complejidad) la aplica
    # auth_service.validate_password_policy con un mensaje claro (autoridad
    # backend). max_length 128 = cota de sanidad anti-abuso.
    new_password: str = Field(..., max_length=128)


class CreateUserBody(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=3, max_length=255)
    dni: Optional[str] = None


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: Optional[str]
    must_change_password: bool
    last_login: Optional[str]
    locked: bool
    deactivated: bool


def _user_to_out(user: ClientUser) -> UserOut:
    locked = bool(
        user.locked_until
        and user.locked_until.replace(tzinfo=None).timestamp()
        > datetime.now(timezone.utc).replace(tzinfo=None).timestamp()
    )
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        must_change_password=user.must_change_password,
        last_login=user.last_login.isoformat() if user.last_login else None,
        locked=locked,
        deactivated=user.deactivated_at is not None,
    )


# ════════════════════════════════════════════════════════════════════
# /client-auth — login, logout, password
# ════════════════════════════════════════════════════════════════════

@auth_router.post("/login", response_model=LoginResponse)
async def client_login(
    body: LoginBody,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    try:
        user, token, csrf_token, exp = await auth_service.login(
            db, body.email, body.password,
            ip=ip, user_agent=ua,
            mfa_code=body.mfa_code,
        )
        await db.commit()
    except auth_service.MfaRequiredError as mfa_exc:
        # 2-step login signal · UI prompt step 2. 2026-06-09 · incluye
        # ``mfa_method`` ('email'|'totp') para que la UI muestre el copy correcto
        # ("te hemos enviado un código a tu email" vs "código de tu app").
        # En method=email el código YA se envió en auth_service.login (persiste
        # con este commit antes de devolver el 401).
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Verificación 2 pasos requerida",
                "requires_mfa": True,
                "mfa_method": getattr(mfa_exc, "method", "email"),
            },
        )
    except AuthError as exc:
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc),
        )
    # BLOQUE 1+4 Mini-Fase 3.5: setear cookies session (httpOnly) +
    # csrf (no httpOnly). access_token sigue en body por compat
    # backward (BLOQUE 5 frontend lo eliminará).
    _set_client_session_cookies(
        response,
        session_token=token,
        csrf_token=csrf_token,
        expires_at=exp,
    )
    return LoginResponse(
        access_token=token, expires_at=exp.isoformat(),
        must_change_password=user.must_change_password,
        full_name=user.full_name,
    )


@auth_router.post("/logout")
async def client_logout(
    response: Response,
    user: ClientUser = Depends(get_current_client_user),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    fulkro_session: str | None = Cookie(None, alias=CLIENT_SESSION_COOKIE),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    # Extraer token desde cookie (preferido, BLOQUE 1 MF3.5) o Bearer
    # (legacy). Coherente con get_current_client_user wrapper.
    token: str | None = None
    if fulkro_session:
        token = fulkro_session
    elif credentials and credentials.credentials:
        token = credentials.credentials
    if not token:
        # Defensa: get_current_client_user habría rechazado antes,
        # pero check defensivo por si la dependency cambia.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No session token available for logout",
        )
    payload = crypto.decode_token(token)
    jti = payload.get("jti")
    ip = request.client.host if request and request.client else None
    ok = await auth_service.logout(db, jti, ip=ip)
    await db.commit()
    # BLOQUE 1+4 Mini-Fase 3.5: borrar ambas cookies (session + csrf)
    # además de invalidar sesión BD. Si cliente vino con Bearer
    # (legacy), delete_cookie es no-op pero no falla.
    _clear_client_session_cookies(response)
    return {"logged_out": ok}


@auth_router.post("/change-password")
async def client_change_password(
    body: ChangePasswordBody,
    user: ClientUser = Depends(get_current_client_user),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    try:
        await auth_service.change_password(
            db, user.id, body.old_password, body.new_password,
            ip=(request.client.host if request and request.client else None),
        )
        await db.commit()
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"password_changed": True}


# ════════════════════════════════════════════════════════════════════
# /client-portal — views single-user-RW (ADR-013 v3)
# ════════════════════════════════════════════════════════════════════

@portal_router.get("/me")
async def portal_me(
    request: Request,
    user: ClientUser = Depends(get_current_client_user),
) -> dict[str, Any]:
    # Acceso de soporte: el claim `support` del JWT (lo stashea authenticate_request
    # en request.state.auth_payload) → el frontend pinta el banner "Sesión de
    # soporte". `support_expires_at` desde el claim `exp` (cuándo caduca · 45min).
    payload = getattr(request.state, "auth_payload", {}) or {}
    is_support = payload.get("support") is True
    support_expires_at = None
    if is_support and payload.get("exp"):
        support_expires_at = datetime.fromtimestamp(
            int(payload["exp"]), tz=timezone.utc,
        ).isoformat()
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "scope": PORTAL_SCOPE,
        "must_change_password": user.must_change_password,
        "is_support_access": is_support,
        "support_expires_at": support_expires_at,
    }


@portal_router.get("/project")
async def portal_project(
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    # Project del cliente · archetype añadido (MB-17.4 ADR-036) para
    # que ClientCategoryBanner pueda detectar sector_salud y mostrar
    # banner art.9 RGPD reforzado · campo no sensible.
    r = await db.execute(text(
        "SELECT id, nombre, categoria_objetivo, estado, lifecycle_state, "
        "archetype "
        "FROM projects WHERE client_id = :cid AND deleted_at IS NULL "
        "ORDER BY created_at DESC LIMIT 1"
    ), {"cid": str(user.client_id)})
    row = r.mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Sin proyecto")
    # ADR-013 v3 single-user-RW · cliente accede al proyecto completo.
    return dict(row)


@portal_router.get("/documents")
async def portal_documents(
    q: Optional[str] = Query(None, description="Search hybrid ILIKE · filename + full_text_content + metadata"),
    clasificacion: Optional[str] = Query(None, description="Filter by document type"),
    folder_id: Optional[uuid.UUID] = Query(None, description="Filter by IDMS folder (1.C.G.B v3.10)"),
    sort: str = Query("recent", description="recent | name | size"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List cliente documents · MB-6 atom 7 extended search + filter + pagination.

    Q2 D hybrid ILIKE · filename + full_text_content + metadata::text (context_snapshot
    jsonb cast). Q7 B documents tab separated · sin scan_status (admin uploads
    trusted boundary documentación).

    Sub-atom 1.C.G.B v3.10 · añade folder_id filter opcional + folder metadata
    (folder_name + virtual_path) para arborescencia cliente friendly /files/.
    """
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))

    base_sql = (
        "SELECT d.id, d.template_codigo as codigo, d.version_actual as version, "
        "d.created_at, d.estado, d.clasificacion, d.nombre, d.file_size_bytes, "
        "d.pdf_path, d.docx_path, d.storage_path, "
        "d.folder_id, df.name as folder_name, df.virtual_path as folder_path "
        "FROM documents d "
        "JOIN projects p ON d.project_id = p.id "
        "LEFT JOIN document_folders df ON d.folder_id = df.id "
        # Flag de visibilidad: el cliente NO ve documentos marcados solo-interno.
        "WHERE p.client_id = :cid AND d.deleted_at IS NULL AND d.interno = false"
    )
    params: dict[str, Any] = {"cid": str(user.client_id)}

    if q:
        base_sql += (
            " AND (d.nombre ILIKE :q OR d.template_codigo ILIKE :q "
            "OR COALESCE(d.full_text_content, '') ILIKE :q "
            "OR COALESCE(d.context_snapshot::text, '') ILIKE :q)"
        )
        params["q"] = f"%{q}%"

    if clasificacion:
        base_sql += " AND d.clasificacion = :clasif"
        params["clasif"] = clasificacion

    if folder_id is not None:
        base_sql += " AND d.folder_id = :fid"
        params["fid"] = str(folder_id)

    sort_clause = {
        "recent": "d.created_at DESC",
        "name": "d.nombre ASC",
        "size": "COALESCE(d.file_size_bytes, 0) DESC",
    }.get(sort, "d.created_at DESC")
    base_sql += f" ORDER BY {sort_clause} LIMIT :lim OFFSET :off"
    params["lim"] = limit
    params["off"] = offset

    r = await db.execute(text(base_sql), params)
    return [dict(row) for row in r.mappings().all()]


@portal_router.get("/folders/tree")
async def portal_folders_tree(
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Lista arborescencia carpetas IDMS del proyecto del cliente · 1.C.G.B v3.10.

    Cliente piloto típicamente tiene 1 proyecto · resolvemos vía client_id session.
    Multi-project T2 post-piloto when demand confirmed (sostiene R23).

    Returns flat list (id · parent_folder_id · name · virtual_path · is_standard ·
    standard_code · custom_order). Frontend reconstituye árbol jerárquico.
    R30 inverso · NO expone audit metadata admin (granted_by · timestamps internos).
    """
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))

    rows = await db.execute(
        text(
            "SELECT df.id, df.parent_folder_id, df.name, df.virtual_path, "
            "df.is_standard, df.standard_code, df.custom_order "
            "FROM document_folders df "
            "JOIN projects p ON df.project_id = p.id "
            "WHERE p.client_id = :cid AND df.deleted_at IS NULL "
            "ORDER BY df.is_standard DESC, df.custom_order ASC, df.standard_code ASC, df.name ASC"
        ),
        {"cid": str(user.client_id)},
    )
    return [dict(r) for r in rows.mappings().all()]


class ClientDocumentUploadBody(BaseModel):
    """Cliente upload document body · 1.C.G.B v3.10.

    Permission-limited vs admin IDMS intake:
    - NO tags ENS (admin gestiona taxonomía Anexo II)
    - NO clasificacion enum (admin asigna · cliente upload = 'evidencia' default)
    - SÍ description opcional friendly ("Adjunto: certificado ISO 27001")
    - SÍ folder_id opcional para organización
    """
    nombre: str = Field(..., min_length=1, max_length=255)
    contenido_base64: str = Field(..., min_length=1)
    tipo_mime: str = Field("application/octet-stream", max_length=100)
    folder_id: Optional[uuid.UUID] = None
    descripcion: Optional[str] = Field(None, max_length=500)


@portal_router.post("/documents/upload", status_code=status.HTTP_201_CREATED)
async def portal_documents_upload(
    body: ClientDocumentUploadBody,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Upload documento desde portal cliente · 1.C.G.B v3.10.

    Permission-limited vs admin IDMS intake (m24_idms):
    - Auth via get_current_client_user (client_id session enforced · NO trust gap)
    - Cliente proyecto resuelto vía single-project lookup (R23 + R27 sostener)
    - Multi-project T2 post-piloto cuando demand confirmed
    - R30 inverso · NO admin metadata audit visible cliente · solo nombre + description
    - Clasificacion fijada "evidencia" (admin podría reclasificar luego)
    """
    # Resolve project_id del cliente · single-project context
    proj_row = await db.execute(
        text("SELECT id FROM projects WHERE client_id = :cid AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 1"),
        {"cid": str(user.client_id)},
    )
    proj = proj_row.first()
    if not proj:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    project_id = proj[0]

    # Validate base64
    try:
        contenido = base64.b64decode(body.contenido_base64)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"contenido_base64 inválido: {exc}")

    # Whitelist de extensión (defense-in-depth · espejo de evidencias_upload_api ·
    # verificación adversarial: el upload cliente aceptaba cualquier tipo).
    _ALLOWED_DOC_EXTS = {
        ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".png", ".jpg", ".jpeg",
        ".txt", ".csv", ".zip", ".odt", ".ods", ".ppt", ".pptx",
    }
    _ext = (
        "." + body.nombre.rsplit(".", 1)[1].lower()
        if "." in body.nombre
        else ""
    )
    if _ext not in _ALLOWED_DOC_EXTS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Extensión {_ext or '(sin extensión)'} no permitida. "
                f"Permitidas: {sorted(_ALLOWED_DOC_EXTS)}"
            ),
        )

    # Validate folder_id pertenece al proyecto cliente (security · evita cross-project upload)
    if body.folder_id is not None:
        fid_row = await db.execute(
            text(
                "SELECT df.id FROM document_folders df "
                "JOIN projects p ON df.project_id = p.id "
                "WHERE df.id = :fid AND p.client_id = :cid AND df.deleted_at IS NULL"
            ),
            {"fid": str(body.folder_id), "cid": str(user.client_id)},
        )
        if fid_row.first() is None:
            raise HTTPException(status_code=404, detail="Carpeta no encontrada")

    # Hash + storage
    content_hash = hashlib.sha256(contenido).hexdigest()
    file_size = len(contenido)

    # Insert document directamente (NO via IDMSService para mantener boundary cliente)
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    doc_id = uuid.uuid4()
    nombre = body.descripcion or body.nombre

    # Ejecutable 8 OLA 0 (#4 · FR-3): persistir el binario REAL en MinIO. Antes el
    # endpoint decodificaba el base64, calculaba hash+size y DESCARTABA los bytes
    # (storage_path=NULL) → el cliente nunca podía descargar su propia evidencia
    # (404 en portal_document_download). Mismo contrato canónico
    # minio://{bucket}/{key} que el intake admin (#36 · m24 _persist_to_minio).
    # Upload real: si MinIO falla devolvemos 502 y NO insertamos metadata huérfana.
    from backend.app.core.storage.minio_client import (
        BUCKET_DOCUMENTS,
        put_object,
    )
    object_key = f"client-uploads/{project_id}/{doc_id}"
    try:
        put_object(
            bucket=BUCKET_DOCUMENTS,
            key=object_key,
            data=contenido,
            content_type=body.tipo_mime or "application/octet-stream",
            metadata={"project-id": str(project_id)},
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"MinIO no disponible: {exc}")
    storage_path = f"minio://{BUCKET_DOCUMENTS}/{object_key}"

    # NOTA: la tabla documents NO tiene columnas created_by/updated_by (verificado
    # contra information_schema). El INSERT previo las referenciaba → UndefinedColumn
    # 500 en upload real (ruta sin test E2E que lo cazara · bug latente · cazado por
    # la verificación). Se retiran · la autoría del cliente queda en el audit_log.
    await db.execute(
        text(
            "INSERT INTO documents ("
            "id, project_id, nombre, tipo, clasificacion, folder_id, "
            "content_hash, file_size_bytes, storage_path, estado, "
            "version_actual, created_at, updated_at"
            ") VALUES ("
            ":id, :pid, :nombre, :tipo, :clasif, :fid, "
            ":hash, :size, :spath, :estado, "
            ":ver, NOW(), NOW()"
            ")"
        ),
        {
            "id": str(doc_id),
            "pid": str(project_id),
            "nombre": nombre[:255],
            "tipo": body.tipo_mime,
            "clasif": "evidencia",
            "fid": str(body.folder_id) if body.folder_id else None,
            "hash": content_hash,
            "size": file_size,
            "spath": storage_path,
            "estado": "draft",
            "ver": "1.0",
        },
    )

    # ENAC traceability (R6 hash chain) · registra el upload del cliente en el
    # audit log (verificación adversarial: faltaba · evidencias_upload sí lo hace).
    # Best-effort: la persistencia del documento (primaria) NUNCA se bloquea por
    # un fallo del audit (notify_best_effort pattern · ruta sin test E2E aún).
    try:
        from backend.app.motors.m21_portal_cliente.audit_log_service import (
            AuditLogService,
        )
        await AuditLogService(db).log_action(
            project_id=project_id,
            client_user_id=user.id,
            action_type="DOCUMENT_UPLOAD",
            action_data={
                "document_id": str(doc_id),
                "nombre": nombre[:255],
                "tipo_mime": body.tipo_mime,
                "extension": _ext,
                "size_bytes": file_size,
                "content_hash": content_hash,
                "folder_id": str(body.folder_id) if body.folder_id else None,
            },
            client_id=user.client_id,
        )
    except Exception:
        logger.exception(
            "portal_documents_upload audit_log best-effort failed · doc_id=%s",
            doc_id,
        )

    await db.commit()
    # FIX P2-3 · realtime gestor documental: el admin ve el documento que el
    # cliente acaba de compartir sin refrescar (best-effort post-commit). Subida
    # de cliente → nunca ``interno`` (esos los marca el admin).
    from backend.app.core.document_events import notify_document_uploaded

    await notify_document_uploaded(
        project_id=project_id,
        document_id=doc_id,
        nombre=nombre,
        source="cliente",
        interno=False,
    )
    return {
        "id": str(doc_id),
        "nombre": nombre,
        "folder_id": str(body.folder_id) if body.folder_id else None,
        "content_hash": content_hash,
        "file_size_bytes": file_size,
    }


@portal_router.get("/documents/{document_id}/versions")
async def portal_document_versions(
    document_id: uuid.UUID,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List version history per document · MB-6 atom 7 Q6 B collapsed history.

    Reuse `document_versions` table existing (FK documents · RLS via parent
    project_id). Empty state si 0 rows (caller renderea "v1.0 inicial").
    """
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    # Validate document belongs to cliente via project.client_id
    doc_row = await db.execute(
        text(
            "SELECT d.id, d.version_actual, d.template_codigo, d.nombre, "
            "p.client_id FROM documents d "
            "JOIN projects p ON d.project_id = p.id "
            "WHERE d.id = :did AND d.deleted_at IS NULL"
        ),
        {"did": str(document_id)},
    )
    doc = doc_row.mappings().first()
    if doc is None or str(doc["client_id"]) != str(user.client_id):
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    versions_row = await db.execute(
        text(
            "SELECT id, version, hash_sha256, generado_por, generado_at, "
            "firmado_por, firmado_at FROM document_versions "
            "WHERE document_id = :did AND deleted_at IS NULL "
            "ORDER BY created_at DESC"
        ),
        {"did": str(document_id)},
    )
    history = [dict(r) for r in versions_row.mappings().all()]
    return {
        "document_id": str(document_id),
        "current_version": doc["version_actual"],
        "codigo": doc["template_codigo"],
        "nombre": doc["nombre"],
        "history": history,
    }


def _resolve_local_path(stored_path: str | None) -> _Path | None:
    """Resolve filesystem path · supports minio:// and local relative paths."""
    if not stored_path:
        return None
    if stored_path.startswith("minio://"):
        return None
    p = _Path(stored_path)
    if p.is_absolute():
        return p if p.exists() else None
    repo_root = _Path(__file__).resolve().parents[4]
    candidate = repo_root / stored_path
    return candidate if candidate.exists() else None


async def _fetch_document_for_cliente(
    db: AsyncSession,
    document_id: uuid.UUID,
    client_id: uuid.UUID,
) -> dict | None:
    res = await db.execute(
        text(
            "SELECT d.id, d.nombre, d.template_codigo, d.docx_path, d.pdf_path, "
            "d.storage_path, d.deleted_at, p.client_id "
            "FROM documents d JOIN projects p ON d.project_id = p.id "
            "WHERE d.id = :did"
        ),
        {"did": str(document_id)},
    )
    row = res.mappings().first()
    if row is None or row["deleted_at"] is not None:
        return None
    if str(row["client_id"]) != str(client_id):
        return None
    return dict(row)


@portal_router.get("/documents/{document_id}/preview")
async def portal_document_preview(
    document_id: uuid.UUID,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """PDF preview inline · same-origin iframe streaming · MB-6 atom 7 Q4 B.

    Returns Content-Disposition: inline (NO attachment) · X-Frame-Options:
    SAMEORIGIN. Only PDFs supported (Q4 B iframe cement · DOCX defer atom 7.bis).
    Local filesystem + MinIO both supported.
    """
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    row = await _fetch_document_for_cliente(db, document_id, user.client_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    pdf_path = row["pdf_path"]
    if not pdf_path:
        raise HTTPException(
            status_code=415,
            detail="Preview solo disponible para PDFs (descarga DOCX en su lugar)",
        )

    if pdf_path.startswith("minio://"):
        from backend.app.core.storage.minio_client import get_object
        rest = pdf_path[len("minio://"):]
        bucket, _, key = rest.partition("/")
        try:
            file_bytes = get_object(bucket, key)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"MinIO unreachable: {exc}")
    else:
        local = _resolve_local_path(pdf_path)
        if local is None:
            raise HTTPException(
                status_code=404,
                detail="Archivo PDF no disponible en almacenamiento",
            )
        file_bytes = local.read_bytes()

    base_name = (
        row["template_codigo"] or row["nombre"] or f"document_{document_id}"
    )
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{base_name}.pdf"',
            "X-Frame-Options": "SAMEORIGIN",
            "Cache-Control": "private, max-age=300",
        },
    )


@portal_router.get("/evidence")
async def portal_evidence_list(
    q: Optional[str] = Query(None, description="Search ILIKE filename + tipo + nombre_tipo"),
    scan_clean_only: bool = Query(False, description="Filter scan_status='clean'"),
    sort: str = Query("recent", description="recent | name | size"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List cliente evidencias · MB-6 atom 7 Q1 B scope + Q5 A filter + Q7 B tab.

    Drop-in ScanStatusBadge atom 6 (2ª aplicación) via scan_status field.
    """
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))

    base_sql = (
        "SELECT e.id, e.project_id, e.tipo, e.nombre_tipo, e.evidence_type_id, "
        "e.fichero_nombre_original, e.fichero_mime_type, e.fichero_tamano_bytes, "
        "e.measure_code, e.fecha_evidencia, e.fecha_caducidad, e.vigente, "
        "e.scan_status, e.scan_completed_at, e.created_at "
        "FROM evidence e JOIN projects p ON e.project_id = p.id "
        "WHERE p.client_id = :cid AND e.deleted_at IS NULL"
    )
    params: dict[str, Any] = {"cid": str(user.client_id)}

    if q:
        base_sql += (
            " AND (COALESCE(e.fichero_nombre_original, '') ILIKE :q "
            "OR COALESCE(e.tipo, '') ILIKE :q "
            "OR COALESCE(e.nombre_tipo, '') ILIKE :q "
            "OR COALESCE(e.measure_code, '') ILIKE :q "
            "OR COALESCE(e.metadata_extra::text, '') ILIKE :q)"
        )
        params["q"] = f"%{q}%"

    if scan_clean_only:
        base_sql += " AND e.scan_status = 'clean'"

    sort_clause = {
        "recent": "e.created_at DESC",
        "name": "e.fichero_nombre_original ASC NULLS LAST",
        "size": "COALESCE(e.fichero_tamano_bytes, 0) DESC",
    }.get(sort, "e.created_at DESC")
    base_sql += f" ORDER BY {sort_clause} LIMIT :lim OFFSET :off"
    params["lim"] = limit
    params["off"] = offset

    r = await db.execute(text(base_sql), params)
    return [dict(row) for row in r.mappings().all()]


async def _fetch_evidence_for_cliente(
    db: AsyncSession,
    evidence_id: uuid.UUID,
    client_id: uuid.UUID,
) -> dict | None:
    res = await db.execute(
        text(
            "SELECT e.id, e.fichero_nombre_original, e.fichero_mime_type, "
            "e.fichero_path, e.scan_status, e.deleted_at, p.client_id "
            "FROM evidence e JOIN projects p ON e.project_id = p.id "
            "WHERE e.id = :eid"
        ),
        {"eid": str(evidence_id)},
    )
    row = res.mappings().first()
    if row is None or row["deleted_at"] is not None:
        return None
    if str(row["client_id"]) != str(client_id):
        return None
    return dict(row)


@portal_router.get("/evidence/{evidence_id}/preview")
async def portal_evidence_preview(
    evidence_id: uuid.UUID,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Evidence PDF preview inline · MB-6 atom 7.

    Bloqueado si scan_status != 'clean' (atom 6 integration · Q5 A safety).
    Only PDFs (Q4 B iframe cement).
    """
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    row = await _fetch_evidence_for_cliente(db, evidence_id, user.client_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Evidencia no encontrada")
    if row["scan_status"] != "clean":
        raise HTTPException(
            status_code=403,
            detail=f"Evidencia no disponible para preview · scan_status='{row['scan_status']}'",
        )

    mime = row["fichero_mime_type"] or ""
    if not mime.startswith("application/pdf"):
        raise HTTPException(
            status_code=415,
            detail="Preview solo disponible para PDF · descarga para otros tipos",
        )

    local = _resolve_local_path(row["fichero_path"])
    if local is None:
        raise HTTPException(
            status_code=404,
            detail="Archivo no disponible en almacenamiento",
        )

    base_name = row["fichero_nombre_original"] or f"evidence_{evidence_id}.pdf"
    return StreamingResponse(
        io.BytesIO(local.read_bytes()),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{base_name}"',
            "X-Frame-Options": "SAMEORIGIN",
            "Cache-Control": "private, max-age=300",
        },
    )


@portal_router.get("/evidence/{evidence_id}/download")
async def portal_evidence_download(
    evidence_id: uuid.UUID,
    request: Request,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Cliente download evidencia · MB-6 atom 7 · same pattern documents.

    FIX P1-2: BLOQUEA scan_status != 'clean'. Antes permitía descargar
    quarantined/infected ("ver original") → se servía un fichero potencialmente
    malicioso al cliente, y 'scanning'/'error' (Celery/clamd caído) salían sin
    verificar. Se alinea con el preview hermano (línea ~925) y con el portal
    auditor m09 (422). audit ENAC log row añadido.
    """
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    row = await _fetch_evidence_for_cliente(db, evidence_id, user.client_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Evidencia no encontrada")
    if row["scan_status"] != "clean":
        raise HTTPException(
            status_code=403,
            detail=(
                f"Evidencia no disponible para descarga · "
                f"scan_status='{row['scan_status']}' (análisis antivirus "
                f"pendiente o no superado)."
            ),
        )

    local = _resolve_local_path(row["fichero_path"])
    if local is None:
        raise HTTPException(
            status_code=404,
            detail="Archivo no disponible en almacenamiento",
        )
    file_bytes = local.read_bytes()
    base_name = row["fichero_nombre_original"] or f"evidence_{evidence_id}"

    audit = ClientUserAudit(
        client_user_id=user.id,
        client_id=user.client_id,
        action="portal_evidence_download",
        ip_address=request.client.host if request.client else None,
        metadata_jsonb={
            "evidence_id": str(evidence_id),
            "filename": base_name,
            "size_bytes": len(file_bytes),
            "scan_status": row["scan_status"],
        },
    )
    db.add(audit)
    await db.commit()

    media_type = row["fichero_mime_type"] or "application/octet-stream"
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{base_name}"',
        },
    )


@portal_router.get("/documents/{document_id}/download")
async def portal_document_download(
    document_id: uuid.UUID,
    request: Request,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Descarga de documento por cliente portal · cross-tenant check via project.

    Cierra TODO-FASE-X-CLIENT-PORTAL-DOCUMENTS-DOWNLOAD-001 (alert literal
    en /client-portal/files frontend reemplazado por flujo real streaming
    desde MinIO + audit interaction log).

    Auth: cookie session ClientUser via get_current_client_user.
    ADR-013 v3 single-user-RW: cliente puede descargar todos los documentos
    de su cliente_id (RLS y cross-tenant check via project.client_id).
    """
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    res = await db.execute(
        text(
            "SELECT d.id, d.nombre, d.template_codigo, d.docx_path, "
            "       d.pdf_path, d.storage_path, d.deleted_at, "
            "       p.client_id "
            "FROM documents d "
            "JOIN projects p ON d.project_id = p.id "
            "WHERE d.id = :did"
        ),
        {"did": str(document_id)},
    )
    row = res.mappings().first()
    if row is None or row["deleted_at"] is not None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    if str(row["client_id"]) != str(user.client_id):
        # No exponer existencia cross-tenant.
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    file_path: str | None = (
        # #31 (FRENTE B): preferir storage_path canónico minio:// (durable) ·
        # los docx_path/pdf_path locales son efímeros (restart contenedor → 503).
        row["storage_path"] or row["pdf_path"] or row["docx_path"]
    )
    if not file_path:
        raise HTTPException(
            status_code=404,
            detail="Documento sin archivo asociado · pendiente generacion",
        )

    if file_path.startswith("minio://"):
        from backend.app.core.storage.minio_client import get_object
        rest = file_path[len("minio://"):]
        bucket, _, key = rest.partition("/")
        try:
            file_bytes = get_object(bucket, key)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"MinIO unreachable: {exc}")
    else:
        raise HTTPException(
            status_code=503,
            detail=(
                "Archivo no disponible en este entorno (local://). "
                "Verifique la configuracion de MinIO."
            ),
        )

    audit = ClientUserAudit(
        client_user_id=user.id,
        client_id=user.client_id,
        action="portal_document_download",
        ip_address=request.client.host if request.client else None,
        metadata_jsonb={
            "document_id": str(document_id),
            "template_codigo": row["template_codigo"],
            "size_bytes": len(file_bytes),
            "user_agent": request.headers.get("user-agent"),
        },
    )
    db.add(audit)
    await db.commit()

    base_name = (
        row["template_codigo"] or row["nombre"] or f"document_{document_id}"
    )
    ext = (
        ".pdf" if row["pdf_path"]
        else ".docx" if row["docx_path"]
        else ".bin"
    )
    media_type = (
        "application/pdf" if ext == ".pdf"
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if ext == ".docx" else "application/octet-stream"
    )

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{base_name}{ext}"',
        },
    )


@portal_router.get("/retainer")
async def portal_retainer(
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    # ADR-013 v3 single-user-RW · cliente accede a retainer completo del cliente.
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    r = await db.execute(text("""
        SELECT id, perfil, precio_mensual, estado, next_renewal_date,
               rag_status, inicio, fin, sla_respuesta_horas
        FROM retainer_contracts
        WHERE client_id = :cid AND deleted_at IS NULL
          AND estado = 'active'
        ORDER BY created_at DESC LIMIT 1
    """), {"cid": str(user.client_id)})
    row = r.mappings().first()
    if row is None:
        return {"retainer": None}
    return dict(row)


@portal_router.get("/invoices")
async def portal_invoices(
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    r = await db.execute(text("""
        SELECT id, numero_correlativo, fecha_emision, concepto,
               base_imponible, total, estado_pago
        FROM invoices
        WHERE client_id = :cid AND deleted_at IS NULL
        ORDER BY fecha_emision DESC LIMIT 50
    """), {"cid": str(user.client_id)})
    return [dict(row) for row in r.mappings().all()]


# ════════════════════════════════════════════════════════════════════
# /clients/{id}/users — Cockpit Marcos gestion usuarios
# ════════════════════════════════════════════════════════════════════

@cockpit_router.post("", response_model=dict)
async def cockpit_create_user(
    client_id: uuid.UUID,
    body: CreateUserBody,
    send_magic_link: bool = False,
    base_url: str = "https://portal.fulkro.es",
    first_login_ttl_hours: int | None = None,
    enqueue_welcome_notification: bool = False,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Crea usuario cliente.

    - ``send_magic_link=False`` (default, legacy): devuelve temp_password
      para que Marcos lo transmita por canal seguro.
    - ``send_magic_link=True`` (recomendado Paso 7+): genera magic link
      ``PRIMER_ACCESO_CLIENTE`` (TTL 24h, OTP), lo envia al email del
      usuario via EmailSender, y NO expone temp_password en response.

    SAN-D MB-19.10 · ADR-042 extensiones (cosecha m21 in-place):

    - ``first_login_ttl_hours``: override TTL magic-link PRIMER_ACCESO_CLIENTE
      default 24h (rango 24-168h · 7 días max). Útil si Marcos quiere
      ventana extendida para clientes que tarden en activar.
    - ``enqueue_welcome_notification``: si True · post-create + send,
      enqueue evento ``client_user_invited`` en NotificationOrchestrator
      (asociado primer Project activo del cliente · skip silente si no
      hay proyecto). DND aware · alimenta dashboard admin notification
      lifecycle.
    """
    try:
        user, temp_pwd = await auth_service.create_user(
            db, client_id=client_id,
            email=body.email, full_name=body.full_name,
            dni=body.dni,
        )
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    response: dict[str, Any] = {
        "user_id": str(user.id),
        "email": user.email,
        "scope": PORTAL_SCOPE,
        "must_change_password": True,
    }

    if not send_magic_link:
        await db.commit()
        response["temp_password"] = temp_pwd
        response["note"] = (
            "Envia el temp_password al usuario por canal seguro "
            "(recomendado: activa send_magic_link=True en Paso 7+)."
        )
        return response

    # MB-4.bis3 (ADR-020 v3 IMPLEMENTED FULLY): drop magic_link
    # PRIMER_ACCESO_CLIENTE · email simple con email + temp_password
    # (cliente login normal en /client-portal/login · must_change_password
    # forced en primer login).
    from backend.app.core.email import get_email_sender

    # Validación TTL preserved (no longer used for magic_link · keep compat
    # de la API admin para deprecation gradual)
    if first_login_ttl_hours is not None:
        if not (24 <= first_login_ttl_hours <= 168):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"first_login_ttl_hours fuera de rango (24-168) · "
                    f"recibido {first_login_ttl_hours}"
                ),
            )

    sender = get_email_sender()
    login_url = f"{base_url}/client-portal/login"
    email_result = await sender.send(
        db,
        to=user.email,
        subject=(
            f"Bienvenido a FULKRO — su cuenta del portal está lista "
            f"({body.full_name or user.email})"
        ),
        html_body=_render_primer_acceso_html(
            full_name=body.full_name or user.email,
            url=login_url,
            otp=temp_pwd,
            expires_at="(la contraseña no caduca · cambia en primer login)",
        ),
        text_body=(
            f"Bienvenido {body.full_name or user.email}.\n\n"
            f"Su cuenta del portal FULKRO está activa.\n\n"
            f"Acceda en: {login_url}\n"
            f"Email: {user.email}\n"
            f"Contraseña temporal: {temp_pwd}\n\n"
            f"Cambiará la contraseña en su primer acceso."
        ),
        template_used="account_invitation",
        magic_link_id=None,
        client_id=client_id,
        metadata={
            "scope": PORTAL_SCOPE,
            "temp_password_sent": True,
            "must_change_password": True,
        },
    )
    await db.commit()
    response["magic_link_id"] = None
    response["magic_link_sent_at"] = False
    response["email_delivery_ok"] = email_result.ok
    response["email_log_id"] = (
        str(email_result.email_log_id) if email_result.email_log_id else None
    )
    response["magic_link_expires_at"] = None
    response["temp_password_sent"] = True
    response["login_url"] = login_url

    # MB-19.10 · NotificationOrchestrator hook (welcome event lifecycle)
    # Post-MB-4.bis3: NO magic_link · helper recibe login_url para email body.
    notification_event_id = None
    if enqueue_welcome_notification:
        notification_event_id = await _enqueue_client_user_invited(
            db=db,
            client_id=client_id,
            client_user=user,
            login_url=login_url,
            magic_link_id=None,
            ttl_hours=0,
        )
    if notification_event_id is not None:
        response["notification_event_id"] = str(notification_event_id)

    # Temp password queda en BD pero NO se expone al caller.
    return response


async def _enqueue_client_user_invited(
    *,
    db: AsyncSession,
    client_id: uuid.UUID,
    client_user: ClientUser,
    login_url: str,
    magic_link_id: uuid.UUID | None,
    ttl_hours: int,
) -> uuid.UUID | None:
    """SAN-D MB-19.10 helper · enqueue evento client_user_invited en
    NotificationOrchestrator post-create user.

    Strategy:
    - Find primer Project activo del cliente (lifecycle_state IN
      DRAFT/SIGNED/ACTIVE/CERTIFIED/RETAINER · NOT ENDED_*/PURGED).
    - Si NO existe project · skip silente (cliente sin proyecto · cliente
      portal funcional sin notification dashboard).
    - enqueue evento type="client_user_invited" · category=onboarding ·
      recipient client_user · DND aware · template payload con magic_link_url
      + ttl_hours + portal scope.

    Returns:
        UUID NotificationEvent creado · None si skipped.
    """
    try:
        from backend.app.notifications.orchestrator import (
            NotificationOrchestrator,
        )
        from backend.app.models.core import Project as _Project
        from sqlalchemy import select as _select

        # Find primer Project activo
        stmt = (
            _select(_Project)
            .where(_Project.client_id == client_id)
            .where(_Project.deleted_at.is_(None))
            .where(_Project.lifecycle_state.notin_(
                ["ENDED_RENEWAL_OK", "ENDED_CHURN", "ARCHIVED", "PURGED"],
            ))
            .order_by(_Project.created_at.asc())
            .limit(1)
        )
        project = (await db.scalars(stmt)).first()
        if project is None:
            logger.info(
                "_enqueue_client_user_invited skip · client %s sin "
                "Project activo · welcome notification deferred",
                client_id,
            )
            return None

        orch = NotificationOrchestrator(db)
        event = await orch.enqueue(
            event_type="client_user_invited",
            recipient_user_id=client_user.id,
            recipient_email=client_user.email,
            subject=(
                f"FULKRO portal · Invitación enviada "
                f"({client_user.full_name or client_user.email})"
            ),
            html_body=(
                f"<p>Hola {client_user.full_name or client_user.email},</p>"
                f"<p>Tu acceso al portal FULKRO está listo. Recibirás "
                f"tu contraseña temporal en un email separado · accede en:</p>"
                f'<p><a href="{login_url}">Iniciar sesión en el portal</a></p>'
            ),
            text_body=(
                f"Hola {client_user.full_name or client_user.email},\n\n"
                f"Tu acceso al portal FULKRO está listo. Recibirás tu "
                f"contraseña temporal en un email separado · accede en:\n\n"
                f"{login_url}\n"
            ),
            project_id=project.id,
            template_used="client_user_invited",
            payload={
                "client_user_id": str(client_user.id),
                "scope": PORTAL_SCOPE,
                "login_url": login_url,
                "magic_link_id": (
                    str(magic_link_id) if magic_link_id else None
                ),
            },
        )
        return event.id if event else None
    except Exception as exc:
        # Best-effort · NotificationOrchestrator hook NO debe abortar
        # cockpit_create_user crítico de invite.
        logger.warning(
            "_enqueue_client_user_invited error · %s · cockpit_create_user "
            "continuó sin notification event",
            exc,
        )
        return None


@cockpit_router.post("/{user_id}/resend-invite")
async def cockpit_resend_invite(
    client_id: uuid.UUID,
    user_id: uuid.UUID,
    base_url: str = "https://portal.fulkro.es",
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Re-genera contraseña temporal cliente + re-envía email simple.

    Post-MB-4.bis3 (ADR-020 v3): NO magic link · reset password genera
    nueva contraseña temporal · email con email + nueva temp_password.
    Cliente debe cambiarla en primer login (must_change_password=True).
    """
    res = await db.execute(
        select(ClientUser).where(
            ClientUser.id == user_id, ClientUser.client_id == client_id,
        )
    )
    user = res.scalar_one_or_none()
    if user is None:
        raise HTTPException(404, "Usuario no encontrado")
    if user.deactivated_at is not None:
        raise HTTPException(400, "Usuario desactivado")

    from backend.app.core.email import get_email_sender

    try:
        new_temp = await auth_service.reset_password_by_marcos(db, user.id)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    sender = get_email_sender()
    login_url = f"{base_url}/client-portal/login"
    email_result = await sender.send(
        db,
        to=user.email,
        subject=(
            f"FULKRO — nueva contraseña temporal del portal "
            f"({user.full_name or user.email})"
        ),
        html_body=_render_primer_acceso_html(
            full_name=user.full_name or user.email,
            url=login_url,
            otp=new_temp,
            expires_at="(la contraseña no caduca · cambia en primer login)",
            resend=True,
        ),
        text_body=(
            f"Hola {user.full_name or user.email}.\n\n"
            f"Se ha regenerado tu contraseña temporal del portal FULKRO.\n\n"
            f"Acceso: {login_url}\n"
            f"Email: {user.email}\n"
            f"Contraseña temporal: {new_temp}\n\n"
            f"Cambiarás la contraseña en tu próximo login."
        ),
        template_used="account_invitation_resend",
        magic_link_id=None,
        client_id=client_id,
        metadata={"resend": True, "scope": PORTAL_SCOPE},
    )
    await db.commit()
    return {
        "user_id": str(user.id),
        "magic_link_id": None,
        "magic_link_expires_at": None,
        "email_delivery_ok": email_result.ok,
        "email_log_id": (
            str(email_result.email_log_id) if email_result.email_log_id else None
        ),
        "temp_password_regenerated": True,
        "must_change_password": True,
    }


def _render_primer_acceso_html(
    *, full_name: str, url: str, otp: str | None,
    expires_at: str, resend: bool = False,
) -> str:
    """HTML del email de primer acceso · #10.

    Antes: HTML crudo azul ``#0b5394`` con copy engañoso ("enlace de un solo
    uso" cuando en realidad es login + contraseña temporal · PRIMER_ACCESO_CLIENTE
    deprecado v3) y footer sin contacto real. Ahora: branding violeta de marca
    (#6C63FF), fondos sólidos, márgenes correctos, copy correcto, y firma desde
    ``fulkro_identity`` (fuente única · Ejecutable 7.6). Primer touchpoint del
    cliente → estético y profesional.
    """
    from backend.app.fulkro_identity import (
        FULKRO_BRAND_TAGLINE,
        FULKRO_EMAIL_SIGNATURE_HTML,
    )

    brand = "#6C63FF"
    header = "Nuevo acceso a tu portal" if resend else "Bienvenido a Fulkro"
    otp_block = (
        '<div style="margin:16px 0;padding:14px 16px;background:#F5F4FF;'
        'border:1px solid #E8E5FF;border-radius:8px;">'
        '<p style="margin:0 0 4px;font-size:13px;color:#555;">'
        'Tu contraseña temporal</p>'
        '<p style="margin:0;font-size:20px;font-weight:700;letter-spacing:1px;'
        f'color:#1a1a2e;font-family:monospace;">{otp}</p>'
        '</div>'
        if otp else ""
    )
    return (
        '<!DOCTYPE html><html><body style="margin:0;padding:0;background:#F4F4F8;">'
        '<div style="max-width:560px;margin:0 auto;padding:24px;'
        'font-family:Helvetica,Arial,sans-serif;color:#1a1a2e;">'
        '<div style="background:#ffffff;border-radius:12px;padding:32px;'
        'border:1px solid #ECECF2;">'
        f'<p style="margin:0 0 4px;font-size:13px;font-weight:700;color:{brand};'
        'letter-spacing:1px;">FULKRO</p>'
        f'<h1 style="margin:0 0 16px;font-size:22px;color:#1a1a2e;">'
        f'{header}, {full_name}</h1>'
        '<p style="margin:0 0 12px;font-size:15px;line-height:1.5;color:#33334d;">'
        'Tu cuenta del portal de Fulkro ya está lista. Accede con tu email y la '
        'contraseña temporal de abajo; te pediremos cambiarla en tu primer acceso.'
        '</p>'
        f'{otp_block}'
        '<p style="margin:24px 0;">'
        f'<a href="{url}" style="display:inline-block;background:{brand};'
        'color:#ffffff;padding:13px 28px;text-decoration:none;border-radius:8px;'
        'font-weight:600;font-size:15px;">Entrar al portal</a></p>'
        f'<p style="margin:0;font-size:13px;color:#777;">Nota: {expires_at}</p>'
        '</div>'
        '<div style="padding:20px 8px 0;font-size:12px;color:#888;line-height:1.5;">'
        f'<p style="margin:0 0 8px;">{FULKRO_BRAND_TAGLINE}</p>'
        f'{FULKRO_EMAIL_SIGNATURE_HTML}'
        '</div>'
        '</div></body></html>'
    )


@cockpit_router.get("", response_model=list[UserOut])
async def cockpit_list_users(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[UserOut]:
    users = await auth_service.list_users_by_client(db, client_id)
    return [_user_to_out(u) for u in users]


@cockpit_router.post("/{user_id}/reset-password")
async def cockpit_reset_password(
    client_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    try:
        temp = await auth_service.reset_password_by_marcos(db, user_id)
        await db.commit()
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"temp_password": temp, "must_change_password": True}


class UpdateUserBody(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


@cockpit_router.patch("/{user_id}", response_model=UserOut)
async def cockpit_update_user(
    client_id: uuid.UUID,
    user_id: uuid.UUID,
    body: UpdateUserBody,
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    """Marcos edita email/full_name de un ClientUser (require_owner · cockpit).

    Email duplicado en el mismo cliente → 409 controlado (pre-check · NO 500).
    """
    if body.email is None and body.full_name is None:
        raise HTTPException(
            status_code=400, detail="Indica email y/o full_name a actualizar.",
        )
    try:
        user = await auth_service.update_user(
            db, user_id,
            email=str(body.email) if body.email is not None else None,
            full_name=body.full_name,
        )
        await db.commit()
    except AuthError as exc:
        msg = str(exc)
        code = 409 if "Ya existe" in msg else 404
        raise HTTPException(status_code=code, detail=msg)
    return _user_to_out(user)


@cockpit_router.delete("/{user_id}")
async def cockpit_deactivate_user(
    client_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    try:
        await auth_service.deactivate_user(db, user_id)
        await db.commit()
    except AuthError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"deactivated": True}


class SupportAccessResponse(BaseModel):
    started: bool
    client_user_email: str
    expires_at: datetime


@support_router.post("/support-access", response_model=SupportAccessResponse)
async def open_support_access(
    client_id: uuid.UUID,
    request: Request,
    response: Response,
    admin: User = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
) -> SupportAccessResponse:
    """Abre una sesión de soporte READ-ONLY del admin sobre el portal del cliente.

    SOLO admin (require_owner · la puerta de soporte). Acuña una sesión de cliente
    (mint_support_session · claim support=true · TTL 45min · SIN password) para el
    ClientUser activo del cliente X, setea las cookies de cliente (el navegador del
    admin entra al portal de X en modo soporte) y registra support.access.started
    en audit_log (prueba legal art.15 RGPD: quién=admin + a quién=client_id + cuándo).

    El READ-ONLY lo enforce authenticate_request (chokepoint app-level · claim
    support). La salida: revoke explícito (logout → support.access.ended) o el TTL.
    """
    # Admin cross-cliente: SET LOCAL ROLE fulkro_app_bypassrls bypassa RLS (patrón auth_service ·
    # local · se resetea al fin de transacción). Autorizado por require_owner.
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))

    # ClientUser activo del cliente (RW único · ADR-013 v3).
    cu = (await db.execute(
        select(ClientUser).where(
            ClientUser.client_id == client_id,
            ClientUser.deactivated_at.is_(None),
            ClientUser.deleted_at.is_(None),
        ).order_by(ClientUser.created_at.desc()).limit(1)
    )).scalar_one_or_none()
    if cu is None:
        raise HTTPException(
            status_code=404,
            detail="El cliente no tiene un usuario de portal activo.",
        )
    # Proyecto del cliente para el audit (LIMIT 1 · R27 · puede ser None).
    project_id = (await db.execute(text(
        "SELECT id FROM projects WHERE client_id = :cid "
        "AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 1"
    ), {"cid": str(client_id)})).scalar()

    token, csrf_token, expires_at = await auth_service.mint_support_session(
        db, cu, admin.id,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    _set_client_session_cookies(
        response, session_token=token, csrf_token=csrf_token,
        expires_at=expires_at,
    )

    # audit_log support.access.started · Sub-atom 5.A 3-way OR · prueba legal.
    import json as _json
    await db.execute(text(
        "INSERT INTO audit_log (id, tabla, registro_id, accion, usuario, "
        "project_id, client_id, payload_new, timestamp) "
        "VALUES (gen_random_uuid(), 'client_sessions', :cid, "
        "'support.access.started', :usr, :pid, :cid, :payload, now())"
    ), {
        "cid": str(client_id),
        "pid": str(project_id) if project_id else None,
        "usr": (admin.email or "admin")[:255],
        "payload": _json.dumps({
            "admin_user_id": str(admin.id),
            "client_user_id": str(cu.id),
            "client_user_email": cu.email,
            "expires_at": expires_at.isoformat(),
            "ttl_minutes": 45,
        }),
    })
    await db.commit()
    return SupportAccessResponse(
        started=True, client_user_email=cu.email, expires_at=expires_at,
    )


# ════════════════════════════════════════════════════════════════════
# Adaptive dashboard · MB-7 atom 7.1 (Q5.2/Q5.3 cement · NO role)
# ════════════════════════════════════════════════════════════════════

@portal_router.get("/dashboard/adaptive")
async def portal_dashboard_adaptive(
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Cross-motor adaptive dashboard view · 4-dim context.

    Q5.2 plan v6 cement: all client users see the same view (NO role
    branching). Q5.3 plan v6 cement: M30 contactos NEVER surfaced here
    (admin-only). Reads from M21 + M01 + workflow + M02 + M03 + M07 +
    M19 + M18 (notifications).
    """
    from backend.app.services.adaptive_dashboard_service import (
        get_adaptive_dashboard,
    )

    view = await get_adaptive_dashboard(db, user.client_id, user.id)
    return {
        "context": {
            "client_id": view.context.client_id,
            "client_name": view.context.client_name,
            "project_id": view.context.project_id,
            "project_name": view.context.project_name,
            "categoria_objetivo": view.context.categoria_objetivo,
            "current_phase": view.context.current_phase,
            "archetype": view.context.archetype,
            "sector": view.context.sector,
            "days_to_certification": view.context.days_to_certification,
            "phase_step": view.context.phase_step,
            "phase_total": view.context.phase_total,
        },
        "today_actions": [
            {
                "id": a.id,
                "title": a.title,
                "description": a.description,
                "href": a.href,
                "icon": a.icon,
                "estimated_minutes": a.estimated_minutes,
                "priority": a.priority,
                "requires_step_up": a.requires_step_up,
            }
            for a in view.today_actions
        ],
        "workflow_summary": view.workflow_summary,
        "recent_messages": view.recent_messages,
        "new_documents_count": view.new_documents_count,
        "upcoming_invoice": view.upcoming_invoice,
        "notifications_unread": view.notifications_unread,
        "whatsapp_thread_id": view.whatsapp_thread_id,
    }


# ════════════════════════════════════════════════════════════════════
# Cliente branding endpoint · MB-9 atom 9.1 Q1.B
# ════════════════════════════════════════════════════════════════════

@portal_router.get("/branding")
async def portal_branding(
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Cliente reads its own brand metadata · graceful fallback null fields."""
    from backend.app.motors.m21_portal_cliente.branding_service import (
        ClientBrandingService,
    )

    svc = ClientBrandingService()
    view = await svc.get_for_client(db, user.client_id)
    if view is None:
        return {
            "client_id": str(user.client_id),
            "primary_color": None,
            "secondary_color": None,
            "footer_text": None,
            "logo_path": None,
            "has_logo": False,
        }
    return {
        "client_id": view.client_id,
        "primary_color": view.primary_color,
        "secondary_color": view.secondary_color,
        "footer_text": view.footer_text,
        "logo_path": view.logo_path,
        "has_logo": view.has_logo,
    }


# ════════════════════════════════════════════════════════════════════
# Sesión 3B-2B.8 CLUSTER 4 Phase 4D · Multi-tenant branding logo serve cliente
# ════════════════════════════════════════════════════════════════════


@portal_router.get("/branding/logo")
async def portal_branding_logo(
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
):
    """Cliente reads its OWN logo binary · multi-tenant isolated por client_id.

    Phase 4D · cliente NEVER reads cross-tenant logos (RLS enforced por
    require_client_user · user.client_id authoritative). Logo binary fetched
    desde MinIO storage via logo_path (bucket/key format).

    Returns:
      - 404 si cliente NO tiene logo configured (has_logo=False)
      - StreamingResponse con logo binary + correct mime_type cuando present
    """
    from fastapi.responses import Response as _Response

    from backend.app.motors.m21_portal_cliente.branding_service import (
        ClientBrandingService,
    )

    svc = ClientBrandingService()
    view = await svc.get_for_client(db, user.client_id)
    if view is None or not view.has_logo or not view.logo_path:
        raise HTTPException(status_code=404, detail="Logo no configurado")

    try:
        bucket, _, key = view.logo_path.partition("/")
        if not bucket or not key:
            raise HTTPException(
                status_code=404, detail="Logo path invalid",
            )

        from backend.app.core.storage.minio_client import get_object
        payload = get_object(bucket, key)
    except HTTPException:
        raise
    except Exception:  # pragma: no cover · best-effort
        logging.getLogger(__name__).exception(
            "Logo binary fetch failed · client_id=%s logo_path=%s",
            user.client_id, view.logo_path,
        )
        raise HTTPException(status_code=503, detail="Logo storage unavailable")

    mime_type = view.logo_mime_type or "image/png"
    return _Response(content=payload, media_type=mime_type)


# ════════════════════════════════════════════════════════════════════════
# Sesión 3B-2B.8 Phase 1A · M01 Categorización sync admin → cliente
# ════════════════════════════════════════════════════════════════════════

@portal_router.get("/categorizacion")
async def portal_categorizacion(
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Cliente reads project categorización · M01 sync admin → cliente.

    Returns:
    - project_id + nombre + categoria_objetivo (project-level summary)
    - systems list con per-system categoria_resultante + fecha + aprobado_por
    - last_updated_at (most recent categorization across systems)

    audit_log emit cliente.categorizacion.viewed (project_id + client_id
    Sub-atom 5.A 3-way OR pattern).
    """
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))

    project_row = (await db.execute(text(
        "SELECT id, nombre, categoria_objetivo "
        "FROM projects "
        "WHERE client_id = :cid AND deleted_at IS NULL "
        "ORDER BY created_at DESC LIMIT 1"
    ), {"cid": str(user.client_id)})).mappings().first()
    if project_row is None:
        raise HTTPException(status_code=404, detail="Sin proyecto")
    project_id = project_row["id"]

    system_rows = (await db.execute(text(
        "SELECT s.id, s.nombre, s.descripcion, "
        "c.id AS categorization_id, c.categoria_resultante, "
        "c.fecha_acta, c.aprobado_por, c.created_at "
        "FROM systems s "
        "LEFT JOIN LATERAL ("
        "  SELECT id, categoria_resultante, fecha_acta, aprobado_por, created_at "
        "  FROM categorizations "
        "  WHERE system_id = s.id AND deleted_at IS NULL "
        "  ORDER BY created_at DESC LIMIT 1"
        ") c ON true "
        "WHERE s.project_id = :pid AND s.deleted_at IS NULL "
        "ORDER BY s.created_at"
    ), {"pid": str(project_id)})).mappings().all()

    systems = [
        {
            "id": str(r["id"]),
            "nombre": r["nombre"],
            "descripcion": r["descripcion"],
            "categorization_id": (
                str(r["categorization_id"]) if r["categorization_id"] else None
            ),
            "categoria_resultante": r["categoria_resultante"],
            "fecha_acta": (
                r["fecha_acta"].isoformat() if r["fecha_acta"] else None
            ),
            "aprobado_por": r["aprobado_por"],
            "created_at": (
                r["created_at"].isoformat() if r["created_at"] else None
            ),
        }
        for r in system_rows
    ]

    last_updated_at = None
    for s in systems:
        if s["created_at"] and (
            last_updated_at is None or s["created_at"] > last_updated_at
        ):
            last_updated_at = s["created_at"]

    # Emit audit_log row con project_id + client_id Sub-atom 5.A 3-way OR pattern
    import json as _json
    await db.execute(text(
        "INSERT INTO audit_log (id, tabla, registro_id, accion, usuario, "
        "project_id, client_id, payload_new, timestamp) "
        "VALUES (gen_random_uuid(), 'categorizations', :pid, :accion, "
        ":user, :pid, :cid, :payload, now())"
    ), {
        "pid": str(project_id),
        "accion": "cliente.categorizacion.viewed",
        "user": (user.email or "cliente")[:255],
        "cid": str(user.client_id),
        "payload": _json.dumps({
            "systems_count": len(systems),
            "categoria_objetivo": project_row["categoria_objetivo"],
        }),
    })
    await db.commit()

    return {
        "project_id": str(project_id),
        "project_nombre": project_row["nombre"],
        "categoria_objetivo": project_row["categoria_objetivo"],
        "systems": systems,
        "last_updated_at": last_updated_at,
        "total_systems": len(systems),
        "categorized_systems": sum(
            1 for s in systems if s["categoria_resultante"]
        ),
    }


# ════════════════════════════════════════════════════════════════════
# Oferta de retainer post-certificación (in-portal · cookie) — defecto P0
# El backend (offer_retainer) emitía notificación a /client-portal/retainer
# pero la ruta + el endpoint NO existían (notificación a 404). Aquí se cubre.
# ════════════════════════════════════════════════════════════════════
_RETAINER_PRICING: dict[str, dict[str, Any]] = {
    "R_MICRO": {"label": "Micro", "precio_mensual": 150,
                "sla": "Soporte mensual · incidencias básicas"},
    "R_LITE": {"label": "Lite", "precio_mensual": 300,
               "sla": "Soporte mensual ampliado"},
    "R_STD": {"label": "Estándar", "precio_mensual": 700,
              "sla": "Comité trimestral · base del servicio (MEDIA)"},
    "R_PLUS": {"label": "Plus", "precio_mensual": 1200,
               "sla": "Soporte prioritario"},
    "R_CRITICAL": {"label": "Crítico", "precio_mensual": 3000,
                   "sla": "SOC + DR + monitorización 24/7"},
}
_TIER_RECOMMENDED: dict[str, list[str]] = {
    "BASICA": ["R_MICRO", "R_LITE"],
    "MEDIA": ["R_STD"],
    "ALTA": ["R_PLUS", "R_CRITICAL"],
}


class RetainerOfferTier(BaseModel):
    tier_code: str
    label: str
    precio_mensual: float
    sla: str
    recommended: bool


class RetainerOfferResponse(BaseModel):
    project_id: str
    project_name: str
    categoria: Optional[str]
    certified_at: Optional[str]
    lifecycle_state: Optional[str]
    recommended_tiers: list[str]
    tiers: list[RetainerOfferTier]


@portal_router.get(
    "/retainer-offer", response_model=RetainerOfferResponse,
)
async def get_retainer_offer(
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> RetainerOfferResponse:
    """Oferta de retainer post-certificación para el proyecto (único, R27) del
    cliente logueado. 404 si aún no está CERTIFIED/RETAINER."""
    await db.execute(
        text("SELECT set_config('app.current_client_id', :c, true)"),
        {"c": str(user.client_id)},
    )
    row = (await db.execute(text(
        "SELECT id, nombre, categoria_objetivo, lifecycle_state, certified_at "
        "FROM projects WHERE client_id=:c AND deleted_at IS NULL "
        "ORDER BY (lifecycle_state IN ('CERTIFIED','RETAINER')) DESC, "
        "created_at DESC LIMIT 1"
    ), {"c": str(user.client_id)})).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    project_id, nombre, cat, state, certified_at = row
    if state not in ("CERTIFIED", "RETAINER"):
        raise HTTPException(
            status_code=404,
            detail="El proyecto aún no está certificado · sin oferta de retainer.",
        )
    recommended = _TIER_RECOMMENDED.get((cat or "").upper(), ["R_STD"])
    tiers = [
        RetainerOfferTier(
            tier_code=k, label=v["label"],
            precio_mensual=float(v["precio_mensual"]),
            sla=v["sla"], recommended=(k in recommended),
        )
        for k, v in _RETAINER_PRICING.items()
    ]
    return RetainerOfferResponse(
        project_id=str(project_id), project_name=nombre or "Tu proyecto ENS",
        categoria=cat,
        certified_at=certified_at.isoformat() if certified_at else None,
        lifecycle_state=state, recommended_tiers=recommended, tiers=tiers,
    )


class RetainerDecisionIn(BaseModel):
    decision: str = Field(..., description="accept | decline | thinking")
    tier: Optional[str] = None


@portal_router.post("/retainer-offer/{project_id}/decision")
async def post_retainer_decision(
    project_id: uuid.UUID,
    body: RetainerDecisionIn,
    user: ClientUser = Depends(get_current_client_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """El cliente acepta/rechaza la oferta (in-portal · cookie). accept → crea
    retainer M23 + lifecycle_state=RETAINER. Reusa el servicio (el endpoint
    admin /lifecycle/decision es require_owner · no accesible al cliente)."""
    from backend.app.motors.m25_lifecycle.lifecycle_paso4 import (
        LifecyclePaso4Error, LifecyclePaso4Service,
    )
    await db.execute(
        text("SELECT set_config('app.current_client_id', :c, true)"),
        {"c": str(user.client_id)},
    )
    owner = (await db.execute(
        text("SELECT client_id FROM projects WHERE id=:p"), {"p": str(project_id)},
    )).scalar()
    if owner is None or str(owner) != str(user.client_id):
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    await db.execute(
        text("SELECT set_config('app.current_project_id', :p, true)"),
        {"p": str(project_id)},
    )
    precio = (
        float(_RETAINER_PRICING.get(body.tier or "", {}).get("precio_mensual", 0))
        if body.decision == "accept" else 0.0
    )
    try:
        result = await LifecyclePaso4Service().handle_retainer_decision(
            db, project_id, decision=body.decision, tier=body.tier,
            precio_mensual=precio, performed_by="cliente",
        )
    except LifecyclePaso4Error as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return result


__all__ = ["auth_router", "portal_router", "cockpit_router"]
