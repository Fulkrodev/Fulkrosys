"""Shared fixtures for FULKRO motor tests.

# ===================================================================
# RLS AND TEST SETUP — CRITICAL DOCUMENTATION
# ===================================================================
#
# The database user fulkro_app is NOSUPERUSER, meaning PostgreSQL
# RLS policies are enforced. This is the production-correct behavior.
#
# Problem: test setup needs to INSERT into RLS-protected tables
# (projects, systems, etc.) without tenant context, which RLS blocks.
#
# Solution: SET LOCAL ROLE fulkro_app_bypassrls (superuser, table owner) within the
# same transaction to bypass RLS during setup, then RESET ROLE to
# return to fulkro_app before exercising the SUT.
#
# The helper _admin_setup(db) context manager handles this:
#   async with _admin_setup(db):
#       # INSERTs here bypass RLS (role = fulkro superuser)
#   # After context: role = fulkro_app (RLS enforced)
#
# NEVER use _admin_setup around assertions about SUT behavior.
# The SUT must always execute as fulkro_app with RLS enforced.
# ===================================================================
"""
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root if present, mirroring the pattern used
# by scripts/demo_*.py and corpus/rd311_embed.py. Required for tests
# marked @pytest.mark.llm that read ANTHROPIC_API_KEY directly via
# os.environ; without this they fail with HTTP 401 unless the operator
# exports the variable manually before invoking pytest.
_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)

# Suite fiable · sin FULKRO_RUN_LLM_TESTS=1 NINGUNA llamada LLM real.
# El .env (cargado arriba) trae ANTHROPIC_API_KEY real → base.py _call_llm
# tomaría el camino de red (router.complete → anthropic streaming → ssl.recv);
# un stall TLS cuelga la suite indefinidamente (el per-test --timeout NO corta
# un worker-thread bloqueado en socket). Con la key vacía, _call_llm cae a su
# _mock_response (el diseño CI existente: "the mock activates when there is no
# Anthropic API key configured (CI/tests)"). delenv NO — vaciar el env var
# anula la cascada pydantic .env (misma nota que en el fixture patched_settings).
# Opt-in (nightly dedicado) restaura la key real y corre los @pytest.mark.llm
# (ver pytest_collection_modifyitems más abajo).
if os.environ.get("FULKRO_RUN_LLM_TESTS") != "1":
    os.environ["ANTHROPIC_API_KEY"] = ""

# Disable workflow gates in the test suite so existing tests that
# exercise a single motor in isolation do not need to satisfy the full
# prerequisite chain (signed categorisation, frozen DdA, completed
# audit-prep, etc.). Production deployments leave this unset so gates
# are enforced by default.
os.environ.setdefault("FULKRO_SKIP_WORKFLOW_GATES", "1")

# FASE 9.D · LECCIÓN-OPS-004 · skip startup_checks en tests para no
# requerir claves Ed25519 reales en disco ni DATABASE_URL en runs
# sintéticos (algunas variantes CI montan DB en memoria). Production
# deja unset → run_startup_checks ejecuta los hardening checks.
os.environ.setdefault("FULKRO_TESTING", "1")

# Ejecutable 8 Pasada 16: la suite corre contra la BD de TEST `fulkro_test`, construida DESDE
# `alembic upgrade head` + seed por `scripts/build_test_db.sh` — NO contra la BD live `fulkro`.
# Mata la deuda histórica conftest-reusa-BD-live (raíz del drift + data-pollution de tests que
# asertan agregados globales: timesheet, llm_top_consumers). Reproducible desde migraciones.
# Opt-out (volver a BD live): export FULKRO_USE_LIVE_DB=1.
if os.environ.get("FULKRO_USE_LIVE_DB") != "1":
    _TEST_DB = os.environ.get("FULKRO_TEST_DB_NAME", "fulkro_test")
    for _k in ("DATABASE_URL", "DATABASE_URL_SYNC", "DATABASE_MIGRATE_URL"):
        _v = os.environ.get(_k, "")
        if _v.endswith("/fulkro"):
            os.environ[_k] = _v[: -len("/fulkro")] + "/" + _TEST_DB

import pytest  # noqa: E402 (must come after env var set)
from fastapi import Request  # noqa: E402
from httpx import AsyncClient, ASGITransport  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402

from backend.app.config import get_settings  # noqa: E402

settings = get_settings()


def _ensure_m6_signing_dev_key() -> None:
    """Genera el keypair Ed25519 dev de m06 (firma documental) si falta.

    Dev-only · NO secreto (prod usa clave real vía env/HSM). m06 lo carga de
    disco (var/keys/), a diferencia de auth/ML que vienen de env. Reproducible:
    un fresh clone / CI sin la clave no debe fallar los tests de firma m06.
    """
    from pathlib import Path as _P

    keys_dir = _P(__file__).resolve().parents[2] / "var" / "keys"
    priv = keys_dir / "m6_signing_dev.ed25519.pem"
    pub = keys_dir / "m6_signing_dev.ed25519.pub.pem"
    if priv.exists() and pub.exists():
        return
    from cryptography.hazmat.primitives import serialization as _ser
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    keys_dir.mkdir(parents=True, exist_ok=True)
    key = Ed25519PrivateKey.generate()
    priv.write_bytes(key.private_bytes(
        _ser.Encoding.PEM, _ser.PrivateFormat.PKCS8, _ser.NoEncryption(),
    ))
    pub.write_bytes(key.public_key().public_bytes(
        _ser.Encoding.PEM, _ser.PublicFormat.SubjectPublicKeyInfo,
    ))


_ensure_m6_signing_dev_key()


# El hook ``pytest_collection_modifyitems`` que antes vivía aquí (el que salta
# los tests ``@pytest.mark.llm``) se ha FUSIONADO con el del final del fichero.
# Motivo: había DOS definiciones del mismo hook en este módulo (F811 de ruff);
# Python se quedaba con la segunda y esta primera estaba MUERTA, así que el
# skip de los tests LLM no se aplicaba. Ver la definición única al final.


@asynccontextmanager
async def _admin_setup(db: AsyncSession):
    """Temporarily escalate to superuser role for test data setup.

    Uses SET LOCAL ROLE fulkro_app_bypassrls (superuser, table owner) to bypass RLS
    within the current transaction. RESET ROLE restores fulkro_app
    after setup. The entire transaction rolls back at end of test,
    so no data persists.

    Usage:
        async with _admin_setup(db):
            await db.execute(text("INSERT INTO projects ..."))
        # Role is now fulkro_app again (RLS enforced)
    """
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    try:
        yield
    finally:
        await db.execute(text("RESET ROLE"))


@pytest.fixture
async def client(async_client):
    """Alias de ``async_client``. Ejecutable 8 Pasada 16 (F-PASADA9-07): varios módulos
    (m_cloud_connectors/test_remediation_api, m14_contracts/test_adendas_audit_trail_api,
    billing/test_api) declaran fixtures que dependen de un fixture ``client`` para el
    AsyncClient, pero el canónico es ``async_client`` → 'fixture client not found' (15 errores).
    Este alias lo resuelve sin tocar cada módulo."""
    return async_client


@pytest.fixture
async def async_client(db):
    """HTTP client that shares the test DB session with endpoints.

    Uses FastAPI dependency_overrides to inject the test's DB session
    into endpoints that call get_db(). Endpoints execute as fulkro_app
    (NOSUPERUSER) with RLS enforced.

    IMPORTANT: app is imported lazily (inside the fixture, not at module
    level) so that coverage.py can instrument the api modules BEFORE
    they are imported.
    """
    from backend.app.main import app
    from backend.app.database import get_db

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


async def setup_test_project(db):
    """Create a client + project in DB and return (client_id, project_id).

    Uses _admin_setup to bypass RLS for the INSERT into projects table.
    Sets app.current_project_id and app.current_client_id session vars
    so subsequent queries under fulkro_app (RLS enforced) see the new
    rows — mirrors production middleware pattern (SAN-B.MB-2.1).
    """
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    unique_cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'Test Client', :cif, now())"
        ), {"id": str(client_id), "cif": unique_cif})
        await db.execute(text(
            "INSERT INTO projects (id, client_id, nombre, created_at) "
            "VALUES (:id, :cid, 'Test Project', now())"
        ), {"id": str(project_id), "cid": str(client_id)})
    # Set tenant context (post-_admin_setup, runs as fulkro_app).
    await db.execute(
        text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": str(project_id)},
    )
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_id)},
    )
    await db.flush()
    return str(client_id), str(project_id)


async def asigna_rseg(db, project_id: str, nombre: str = "RSEG") -> str:
    """Asigna un Responsable de la Seguridad al cliente del proyecto.

    N4 · desde el bloque N, congelar la DdA exige que `aprobado_por` sea el RSEG
    nombrado (RD 311/2022 art. 11: responsabilidades diferenciadas). Los tests
    que congelan una DdA necesitan que ese contacto exista; antes valia cualquier
    cadena porque nadie la comprobaba.
    """
    import uuid as _uuid
    async with _admin_setup(db):
        cid = (await db.execute(
            text("SELECT client_id FROM projects WHERE id = :p"),
            {"p": str(project_id)},
        )).scalar()
        await db.execute(text(
            "INSERT INTO client_contacts (id, client_id, full_name, email, "
            "role_title, role_category, role_ens_required, is_active, created_at) "
            "VALUES (:id, :cid, :n, :e, 'RSEG', 'tecnico', "
            "'responsable_seguridad', true, now())"
        ), {"id": str(_uuid.uuid4()), "cid": str(cid), "n": nombre,
            "e": f"{_uuid.uuid4().hex[:8]}@test.local"})
    await db.flush()
    return nombre


@pytest.fixture
async def db():
    """Provide a transactional DB session as fulkro_app (NOSUPERUSER).

    RLS is enforced. Use _admin_setup(db) for data setup that needs
    to bypass RLS. The entire transaction rolls back after the test.
    """
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        yield session
        await session.close()
        await trans.rollback()
    await engine.dispose()


@pytest.fixture
async def analysis_factory(db):
    """Factory to create a test analysis with project and client.

    Uses _admin_setup for the client+project INSERT (RLS-protected).
    Sets app.current_project_id session var before MageritService runs
    so the magerit_analysis RLS policy (project_isolation) lets the
    INSERT through under fulkro_app role (mirrors production middleware
    behaviour).
    """
    async def _create(calculation_mode="qualitative"):
        client_id = uuid.uuid4()
        project_id = uuid.uuid4()
        unique_cif = f"B{uuid.uuid4().hex[:8].upper()}"
        async with _admin_setup(db):
            await db.execute(text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'Test Client', :cif, now())"
            ), {"id": str(client_id), "cif": unique_cif})
            await db.execute(text(
                "INSERT INTO projects (id, client_id, nombre, created_at) "
                "VALUES (:id, :cid, 'Test Project', now())"
            ), {"id": str(project_id), "cid": str(client_id)})

        # Set tenant context — magerit_analysis has RLS (SAN-B.MB-2.1).
        # Uso `set_config(key, value, is_local=true)` porque asyncpg
        # no soporta SET LOCAL con prepared-statement parameters.
        await db.execute(
            text("SELECT set_config('app.current_project_id', :pid, true)"),
            {"pid": str(project_id)},
        )
        await db.execute(
            text("SELECT set_config('app.current_client_id', :cid, true)"),
            {"cid": str(client_id)},
        )

        from backend.app.motors.m02_magerit.service import MageritService
        svc = MageritService(db)
        analysis = await svc.create_analysis(
            project_id=project_id,
            name=f"Test Analysis {uuid.uuid4().hex[:8]}",
            calculation_mode=calculation_mode,
        )
        await db.flush()
        return analysis, svc
    return _create


@pytest.fixture
def patched_settings(monkeypatch):
    """Helper canónico para tests que controlan credenciales Settings.

    Reemplaza el patrón legacy monkeypatch.delenv/setenv en tests
    que ejecutan código refactorizado a get_settings(). El @lru_cache
    de get_settings() hace que monkeypatch.{set,del}env aplicado
    tras el primer get_settings() no afecte. Este fixture setea env
    vars + limpia cache para que la próxima instanciación de Settings
    devuelva los valores deseados.

    NOTA arquitectónica setenv vs delenv: setenv("X", "") (no delenv)
    es deliberado. Pydantic-settings con env_file=".env" usa cascada
    env vars > .env > defaults; delenv permitiría que pydantic
    re-lea .env como fallback (que en CI/dev tiene claves reales).
    setenv con valor explícito anula esa cascada.

    NOTA arquitectónica singleton: además de cache_clear sobre
    get_settings, el fixture resetea el singleton _default_router de
    llm_router. Ese singleton captura _api_key en __init__ y queda
    stateful: una vez creado con un valor (incluso "" o una clave
    de prueba inválida), no se actualiza al cambiar Settings/env.
    Sin este reset, un test que construya el singleton con clave
    inválida (ej. test_get_default_llm_router_returns_singleton con
    "sk-test-key") contamina tests posteriores que reusen el
    singleton (ej. test_prioritize_*_real_llm en otro archivo) →
    HTTP 401 invalid x-api-key. Reset antes y después garantiza
    aislamiento bidireccional.

    Uso:
        def test_xxx(db, patched_settings):
            patched_settings(anthropic_api_key="")
            # get_settings().anthropic_api_key.get_secret_value() == ""
    """
    from backend.app.config import get_settings
    from backend.app.core.ai.llm_router import reset_default_llm_router

    def apply(**kwargs):
        for key, value in kwargs.items():
            env_name = key.upper()
            monkeypatch.setenv(env_name, str(value) if value is not None else "")
        get_settings.cache_clear()
        reset_default_llm_router()

    yield apply
    get_settings.cache_clear()
    reset_default_llm_router()


# ════════════════════════════════════════════════════════════════════
# AUTH OVERRIDE PARA TESTS MOTOR (sub-fase 4.D, ADR-021)
# ════════════════════════════════════════════════════════════════════
#
# Por defecto todos los tests usan dependency_override de
# ``authenticate_request`` → AuthSubject Marcos stub. Permite que
# 49 tests motor existing (sin auth setup) sigan pasando tras wire
# global dep en main.py (sub-fase 4.D.4).
#
# Tests que validan auth REAL (5 files críticos: admin_settings,
# auth/*, m21_portal_cliente) opt-out vía ``pytestmark = pytest.mark.real_auth``.
#
# Cobertura H17 anti-pattern parcialmente mitigada — resolución
# completa diferida a TODO-TESTS-AUTH-COVERAGE-001 [BAJA · post-deploy].
# ════════════════════════════════════════════════════════════════════


class _StubMarcosUser:
    """Stub User Marcos para dependency_override default tests motor.

    Email = ``marcos@fulkro.es`` para que las dependencies owner pasen
    durante tests motor (TODO-RBAC-PER-ENDPOINT-001 sub-bloque RBAC.E).
    """

    email = "marcos@fulkro.es"
    role = "owner"
    id = "00000000-0000-0000-0000-000000000099"
    is_active = True


async def _override_authenticate_request_marcos(request: Request):
    """Override default global dep: retorna AuthSubject Marcos stub.

    Los 49 motor tests sin auth real heredan este override
    automáticamente cuando ``authenticate_request`` se activa global
    en sub-fase 4.D.4.

    Sub-fase TODO-RBAC-PER-ENDPOINT-001: además de retornar el subject,
    populamos ``request.state.auth_subject`` para que las dependencies
    downstream (``require_owner``/``require_marcos_or_client``/etc.)
    puedan lookup por ``state`` igual que el real ``authenticate_request``.

    Nota: el parámetro ``request: Request`` debe estar anotado para que
    FastAPI lo inyecte (sin annotation lo trata como query param).
    """
    from backend.app.auth.global_dep import AuthSubject

    subject = AuthSubject(user=_StubMarcosUser(), role_pool="marcos")
    request.state.auth_subject = subject
    # Compatibilidad pre-4.D call sites que leen auth_payload (e.g.
    # auth/api.py::logout extrae jti). Stub seguro.
    request.state.auth_payload = {
        "sub": _StubMarcosUser.id,
        "jti": "stub-jti",
        "csrf": "stub-csrf",
    }
    return subject


@pytest.fixture(autouse=True)
def auth_override_default(request):
    """Autouse fixture: override ``authenticate_request`` por defecto.

    Tests con marker ``real_auth`` opt-out (no se aplica override) —
    validan flow auth real con cookies emitidas por endpoints
    /api/v1/_dev/login-as-marcos o /api/v1/auth/login.
    """
    if request.node.get_closest_marker("real_auth"):
        yield
        return

    from backend.app.main import app
    from backend.app.auth.global_dep import authenticate_request

    app.dependency_overrides[authenticate_request] = (
        _override_authenticate_request_marcos
    )
    yield
    app.dependency_overrides.pop(authenticate_request, None)


# Marcadores de dependencia de base de datos
# ------------------------------------------
# 2.717 funciones de test en 377 ficheros piden el fixture `db`, que abre una
# conexion contra PostgreSQL. Anotarlas una a una con @pytest.mark.requires_db
# no se mantendria: cada test nuevo nacería sin marcar y el marcador iría
# quedándose atrás en silencio, que es justo lo que le pasó antes (estaba
# puesto a mano en 5 ficheros y ni siquiera registrado en pyproject, así que
# pytest lo ignoraba con un PytestUnknownMarkWarning y no filtraba nada).
#
# Se deriva del unico hecho que no puede desincronizarse: si un test pide el
# fixture `db`, necesita base de datos. Los 5 usos manuales existentes siguen
# siendo validos; esto los complementa, no los sustituye.
_DB_FIXTURES = {"db"}


def pytest_collection_modifyitems(config, items):
    """Hook ÚNICO de colección. Hace DOS cosas, en este orden:

    1. Marca ``requires_db`` todo test que solicite un fixture de base de datos.
    2. Salta los tests ``@pytest.mark.llm`` salvo opt-in explícito.

    OJO · esto era un F811 de ruff: este hook estaba DEFINIDO DOS VECES en este
    mismo fichero (aquí y más arriba, junto a ``_ensure_m6_signing_dev_key``).
    pytest sólo ve el último nombre que queda en el módulo, de modo que la
    definición de arriba estaba muerta y su comportamiento —el skip de los
    tests LLM— se había perdido en silencio. Esta función fusiona las dos y
    recupera ese skip. NO añadas una segunda definición: amplía ésta.

    Detalle del punto 2: los tests ``@pytest.mark.llm`` hacen llamadas REALES a
    la API de Anthropic (red + coste + flaky · un stall de streaming cuelga la
    suite indefinidamente · el timeout per-test NO lo corta porque el bloqueo
    vive en un worker-thread en el socket). Se SALTAN por defecto · opt-in
    explícito con ``FULKRO_RUN_LLM_TESTS=1`` (p.ej. nightly dedicado).

    El marcado ``requires_db`` se aplica SIEMPRE, también en modo opt-in LLM:
    la vieja definición hacía ``return`` temprano y, de haberse fusionado sin
    cuidado, ese return se habría llevado por delante el punto 1.
    """
    # 1 · derivar requires_db del fixture solicitado (siempre)
    for item in items:
        if _DB_FIXTURES & set(getattr(item, "fixturenames", ())):
            item.add_marker(pytest.mark.requires_db)

    # 2 · skip de los tests LLM salvo opt-in
    if os.environ.get("FULKRO_RUN_LLM_TESTS") == "1":
        return
    skip_llm = pytest.mark.skip(
        reason="llamada LLM real · opt-in con FULKRO_RUN_LLM_TESTS=1",
    )
    for item in items:
        if "llm" in item.keywords:
            item.add_marker(skip_llm)
