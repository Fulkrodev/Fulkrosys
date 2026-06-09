"""F-18-01 · copiloto cliente setea app.current_client_id (contexto RLS).

Gap (confirmado por probe SQL A/B en el findings register): el runtime conecta
como ``fulkro_app`` (RLS activa) y NO hay middleware que setee
``app.current_client_id`` (``authenticate_request`` solo pone
``app.current_user``). Los paths del copiloto cliente usaban ``get_db`` plano
sin ``set_tenant_context`` → la política ``client_isolation`` de ``projects``
cegaba la fila del cliente → 404 / contexto vacío a su dueño legítimo
(fail-closed, NO fuga).

Estos tests son PROD-FIELES a propósito: NO usan ``setup_test_project`` (que
setea ``app.current_client_id`` en la sesión compartida → falso verde, el
atajo que enmascaró el bug). Siembran datos vía ``_admin_setup`` (bypass RLS
solo para el INSERT) dejando la sesión SIN contexto, replicando producción.

El test de ``/chat/stream`` usa una sesión con **commit real** porque el
harness normal (``db`` fixture) une la sesión a una transacción externa con
rollback → ``db.commit()`` NO termina la transacción y NO tira el GUC
``is_local`` (verificado empíricamente). Solo un commit real (conexión real,
como prod ``/chat/stream``) tira el GUC → es el único modo de DEMOSTRAR que el
re-set tras commit funciona de verdad (no basta un assert 200 ciego).
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.config import get_settings
from backend.app.database import set_tenant_context
from backend.app.motors.m11_copiloto.portal_api import (
    _resolve_project_meta,
    _resolve_project_meta_scoped,
)
from backend.tests.conftest import _admin_setup


# ════════════════════════════════════════════════════════════════════
# Helpers · siembra SIN contexto (prod-fiel) sobre la sesión harness
# ════════════════════════════════════════════════════════════════════


async def _seed_client_project_no_ctx(
    db: AsyncSession,
) -> tuple[uuid.UUID, uuid.UUID]:
    """INSERT client + project vía _admin_setup (bypass RLS) · NO setea ctx.

    A diferencia de ``setup_test_project``, NO llama ``set_config`` de
    ``app.current_client_id`` → la sesión queda como en producción (ciega
    hasta que el SUT setee el contexto).
    """
    cid = uuid.uuid4()
    pid = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'F1801 Client', :cif, now())"
            ),
            {"id": str(cid), "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, categoria_objetivo, "
                "fase, created_at) VALUES "
                "(:id, :cid, 'F1801 Project', 'media', 'implantacion', now())"
            ),
            {"id": str(pid), "cid": str(cid)},
        )
    return cid, pid


async def _ensure_client_user_no_ctx(
    db: AsyncSession, *, user_id: uuid.UUID, client_id: uuid.UUID, email: str,
) -> None:
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO client_users (id, client_id, email, password_hash, "
                "full_name, must_change_password, created_at) "
                "VALUES (:uid, :cid, :email, 'x', 'Test', false, now())"
            ),
            {"uid": str(user_id), "cid": str(client_id), "email": email},
        )


# ════════════════════════════════════════════════════════════════════
# 1 · A/B nivel-helper · réplica exacta de la probe SQL del register
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_resolve_meta_blind_without_ctx_sees_with_ctx(db: AsyncSession):
    """A (sin ctx) = ciego (None) · B (+set_tenant_context) = ve · datos idénticos.

    Esta es la prueba SQL/RLS del gap: la ÚNICA diferencia A↔B es la llamada a
    ``set_config('app.current_client_id', ...)``. No es ausencia de datos; es
    ausencia de contexto.
    """
    cid, pid = await _seed_client_project_no_ctx(db)

    # A · prod-réplica · lo que hacía el copiloto (sin contexto)
    a_pid, _a_cat = await _resolve_project_meta(db, cid)
    assert a_pid is None, "A debe ser ciego (RLS oculta projects sin ctx)"

    # B · el fix · _resolve_project_meta_scoped setea ctx antes de resolver
    b_pid, b_cat = await _resolve_project_meta_scoped(db, cid)
    assert b_pid == str(pid), "B debe ver el proyecto del cliente"
    assert b_cat == "media", "B resuelve también categoria_objetivo"


# ════════════════════════════════════════════════════════════════════
# 2-3 · Endpoints deterministas prod-fieles (sin LLM) · /coach/next-step + /hint
# ════════════════════════════════════════════════════════════════════


@pytest.fixture
async def _stub_client_user(async_client: AsyncClient):
    """Override get_current_client_user con stub · client_id seteado por el test."""
    from backend.app.main import app
    from backend.app.motors.m21_portal_cliente.api import get_current_client_user

    class _Stub:
        id = uuid.UUID("00000000-0000-0000-0000-0000000018a1")
        email = "f1801@example.test"
        client_id: uuid.UUID | None = None

    stub = _Stub()

    async def _override():
        return stub

    app.dependency_overrides[get_current_client_user] = _override
    yield async_client, stub
    app.dependency_overrides.pop(get_current_client_user, None)


@pytest.mark.asyncio
async def test_coach_next_step_prod_faithful_sees_project(
    _stub_client_user, db: AsyncSession,
):
    """PROD-FIEL: sin el fix → 404 (ciego); con el fix → 200 que ve su fase.

    Siembra sin ctx (NO setup_test_project). El endpoint debe setear el
    contexto él mismo (el fix) para resolver el proyecto y NO devolver 404.
    """
    cli, stub = _stub_client_user
    cid, pid = await _seed_client_project_no_ctx(db)
    stub.client_id = cid
    await _ensure_client_user_no_ctx(db, user_id=stub.id, client_id=cid, email=stub.email)

    resp = await cli.get("/api/v1/client-portal/copiloto/coach/next-step")

    assert resp.status_code == 200, resp.text  # sin fix sería 404 ciego
    body = resp.json()
    assert body["current_phase"] == "implantacion"


@pytest.mark.asyncio
async def test_hint_prod_faithful_sees_phase(
    _stub_client_user, db: AsyncSession,
):
    """PROD-FIEL: /hint ve el proyecto y su fase (sin fix → 'sin proyecto activo')."""
    cli, stub = _stub_client_user
    cid, pid = await _seed_client_project_no_ctx(db)
    stub.client_id = cid
    await _ensure_client_user_no_ctx(db, user_id=stub.id, client_id=cid, email=stub.email)

    resp = await cli.get("/api/v1/client-portal/copiloto/hint")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    # implantacion tiene acciones cliente (sign_dda) → ve fase real, no pre_venta ciego
    assert body["current_phase"] == "implantacion", body
    assert body["has_action"] is True, body


# ════════════════════════════════════════════════════════════════════
# 6 · Path 6 (stub) · build_client_context · ciego sin ctx, ve con ctx
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_build_client_context_blind_without_ctx_sees_with_ctx(db: AsyncSession):
    """Path 6 (client_copilot_stub → generate_response → build_client_context).

    Cubre la rama LLM que el test de endpoint NO ejercita sin llm_enabled()
    (ver comentario en client_copilot_stub.py). Inequívoco: sin ctx el context
    es genérico; con ctx (lo que setea el fix) es el del proyecto real.
    """
    from backend.app.agents.copilot_persona_service import CopilotPersonaService

    cid, pid = await _seed_client_project_no_ctx(db)
    svc = CopilotPersonaService("cliente")

    # A · sin contexto (prod sin fix) → genérico (RLS ciega projects)
    ctx_blind = await svc.build_client_context(db, pid)
    assert ctx_blind["project_category"] == "(categoría ENS)", ctx_blind
    assert ctx_blind["client_company"] == "(empresa cliente)", ctx_blind

    # B · con contexto (lo que setea el fix antes de generate_response) → real
    await set_tenant_context(db, client_id=cid, project_id=pid)
    ctx_seen = await svc.build_client_context(db, pid)
    assert ctx_seen["project_category"] == "media", ctx_seen
    assert "F1801 Project" in ctx_seen["project_context"], ctx_seen


# ════════════════════════════════════════════════════════════════════
# Helpers · siembra con COMMIT REAL (conexión real · prod-fiel /chat/stream)
# ════════════════════════════════════════════════════════════════════


async def _seed_committed(engine, cid, pid, uid, cif) -> None:
    async with engine.connect() as conn:
        s = AsyncSession(bind=conn, expire_on_commit=False)
        await s.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        await s.execute(
            text("INSERT INTO clients (id, nombre, cif, created_at) "
                 "VALUES (:id, 'F1801 RC', :cif, now())"),
            {"id": str(cid), "cif": cif},
        )
        await s.execute(
            text("INSERT INTO projects (id, client_id, nombre, categoria_objetivo, "
                 "fase, created_at) VALUES (:id, :cid, 'F1801 RP', 'media', "
                 "'implantacion', now())"),
            {"id": str(pid), "cid": str(cid)},
        )
        if uid is not None:
            await s.execute(
                text("INSERT INTO client_users (id, client_id, email, password_hash, "
                     "full_name, must_change_password, created_at) "
                     "VALUES (:uid, :cid, :email, 'x', 'T', false, now())"),
                {"uid": str(uid), "cid": str(cid), "email": f"rc-{uid}@test"},
            )
        await s.execute(text("RESET ROLE"))
        await s.commit()


async def _cleanup_committed(engine, cid, pid, uid) -> None:
    async with engine.connect() as conn:
        s = AsyncSession(bind=conn, expire_on_commit=False)
        await s.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        # audit_log es append-only POR DISEÑO (R6 · triggers + privilegio revocado
        # UPDATE/DELETE · auditoría 2026-06-07). NO se borra: las filas de test son
        # inocuas y fulkro_test se reconstruye desde cero (build_test_db).
        if uid is not None:
            await s.execute(text("DELETE FROM client_users WHERE id = :uid"), {"uid": str(uid)})
        # 2026-06-09 · el chat cliente ahora crea conversación/mensajes (memoria
        # N6) que referencian el proyecto · bórralos antes que projects (FK).
        await s.execute(text("DELETE FROM copilot_messages WHERE project_id = :pid"), {"pid": str(pid)})
        await s.execute(text("DELETE FROM copilot_conversations WHERE project_id = :pid"), {"pid": str(pid)})
        await s.execute(text("DELETE FROM projects WHERE id = :pid"), {"pid": str(pid)})
        await s.execute(text("DELETE FROM clients WHERE id = :cid"), {"cid": str(cid)})
        await s.execute(text("RESET ROLE"))
        await s.commit()


# ════════════════════════════════════════════════════════════════════
# 4 · /chat/stream re-set tras commit REAL · mecanismo (ambos brazos)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_chat_stream_reset_survives_real_commit_mechanism():
    """Un db.commit() REAL (como prod /chat/stream) tira el GUC is_local →
    lectura project-scoped CIEGA. El re-set (lo que hace el fix dentro del
    generador) lo restaura → VE el proyecto. Ambos brazos sobre datos idénticos.
    """
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    cid, pid, cif = uuid.uuid4(), uuid.uuid4(), f"B{uuid.uuid4().hex[:8].upper()}"
    try:
        await _seed_committed(engine, cid, pid, None, cif)
        async with engine.connect() as conn:
            db = AsyncSession(bind=conn, expire_on_commit=False)
            await set_tenant_context(db, client_id=cid, project_id=pid)
            await db.commit()  # REAL commit (prod pre-stream) → tira el GUC is_local

            blind = (await db.execute(
                text("SELECT id FROM projects WHERE client_id = :cid "
                     "AND deleted_at IS NULL"), {"cid": str(cid)},
            )).first()
            assert blind is None, "ARM A · ciego tras commit real (GUC tirado)"

            await set_tenant_context(db, client_id=cid, project_id=pid)  # re-set del fix
            sees = (await db.execute(
                text("SELECT id FROM projects WHERE client_id = :cid "
                     "AND deleted_at IS NULL"), {"cid": str(cid)},
            )).first()
            assert sees is not None and str(sees[0]) == str(pid), \
                "ARM B · el re-set restaura el contexto → ve el proyecto"
            await db.rollback()
    finally:
        await _cleanup_committed(engine, cid, pid, None)
        await engine.dispose()


# ════════════════════════════════════════════════════════════════════
# 5 · /chat/stream endpoint · lectura DENTRO del stream tras commit real VE proyecto
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_chat_stream_generator_sees_project_after_commit(monkeypatch):
    """DEMUESTRA: el generador real de /chat/stream, TRAS el db.commit() previo
    al stream, re-setea contexto y una lectura project-scoped DENTRO del stream
    VE el proyecto (no solo responde 200). Sesión con commit REAL (prod-fiel).
    """
    from backend.app.main import app
    from backend.app.database import get_db
    from backend.app.motors.m11_copiloto import portal_api
    from backend.app.motors.m21_portal_cliente.api import get_current_client_user

    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    cid, pid, uid = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    captured: dict = {}

    async def _fake_stream(db, query):
        # Corre DENTRO del generador, DESPUÉS del db.commit() pre-stream.
        setting = (await db.execute(
            text("SELECT current_setting('app.current_client_id', true)"),
        )).scalar()
        captured["client_id_setting"] = setting
        row = (await db.execute(
            text("SELECT id FROM projects WHERE client_id = :cid "
                 "AND deleted_at IS NULL"), {"cid": str(cid)},
        )).first()
        captured["seen_project"] = str(row[0]) if row else None
        yield 'data: {"type":"done"}\n\n'

    monkeypatch.setattr(portal_api, "stream_answer_question", _fake_stream)

    class _Stub:
        id = uid
        email = f"rc-{uid}@test"
        client_id = cid

    async def _override_user():
        return _Stub()

    async def _override_db():
        async with engine.connect() as conn:
            db = AsyncSession(bind=conn, expire_on_commit=False)
            yield db

    try:
        await _seed_committed(engine, cid, pid, uid, cif)
        app.dependency_overrides[get_db] = _override_db
        app.dependency_overrides[get_current_client_user] = _override_user

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/client-portal/copiloto/chat/stream",
                json={"question": "hola, una pregunta"},
            )
        assert resp.status_code == 200, resp.text
        # La prueba real: contexto vivo + lectura project-scoped DENTRO del stream
        assert captured.get("client_id_setting") == str(cid), captured
        assert captured.get("seen_project") == str(pid), captured
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_client_user, None)
        await _cleanup_committed(engine, cid, pid, uid)
        await engine.dispose()
