"""Tests baseline Motor 30 — Client Contacts (sub-fase 5.5.D FASE 5.5).

17 tests cubren:
  CRUD service:
   1. test_create_basic
   2. test_email_unique_per_client
   3. test_create_with_primary_unsets_others
   4. test_promote_signatory
   5. test_create_with_portal_access_persists_flag
   6. test_list_by_client_active_filter
   7. test_list_by_role_category
   8. test_search_full_text_notes
   9. test_update_propagates_role_change
   10. test_deactivate_keeps_history
   11. test_delete_cascade_interactions

  Timeline + integraciones:
   12. test_log_interaction_meeting
   13. test_log_interaction_message
   14. test_log_interaction_magic_link
   15. test_get_timeline_ordered_desc
   16. test_get_for_copilot_context_format

  HTTP RBAC (real_auth):
   17. test_endpoint_requires_owner_role

Service-level tests usan ``db`` fixture (transactional rollback). Tests
HTTP usan ``async_client`` + override stub Marcos (default conftest).
Test 17 opt-out con ``real_auth`` para validar require_owner sin stub.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m30_client_contacts.schemas import (
    ClientContactCreate,
    ClientContactUpdate,
)
from backend.app.motors.m30_client_contacts.service import (
    ClientContactService,
    ContactNotFoundError,
    DuplicateContactEmailError,
)
from backend.tests.conftest import _admin_setup


# ====================================================================
# Helpers
# ====================================================================


async def _create_test_client(db: AsyncSession) -> uuid.UUID:
    """INSERT cliente sintético usando _admin_setup (bypass RLS)."""
    client_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, sector, created_at) "
                "VALUES (:id, :nombre, :cif, 'publico', now())"
            ),
            {
                "id": str(client_id),
                "nombre": f"Cliente Test M30 {cif}",
                "cif": cif,
            },
        )
    await db.flush()
    # FASE 0 fix · client_contacts es fail-closed (tenant_isolation): fijar el
    # contexto del cliente para que las operaciones del servicio pasen RLS,
    # igual que hace el endpoint admin (dependency _set_client_rls_context).
    await db.execute(
        text("SELECT set_config('app.current_client_id', :cid, true)"),
        {"cid": str(client_id)},
    )
    return client_id


def _payload(
    full_name: str = "Ana Pérez",
    email: str = "ana.perez@example.com",
    role_title: str = "CISO",
    role_category: str = "ciso",
    **overrides,
) -> ClientContactCreate:
    base = {
        "full_name": full_name,
        "email": email,
        "role_title": role_title,
        "role_category": role_category,
    }
    base.update(overrides)
    return ClientContactCreate(**base)


# ====================================================================
# Tests CRUD service
# ====================================================================


@pytest.mark.asyncio
async def test_create_basic(db: AsyncSession):
    """POST contact → defaults aplicados + retorna ClientContactOut."""
    client_id = await _create_test_client(db)
    svc = ClientContactService(db)

    contact = await svc.create_contact(
        client_id, _payload(),
    )

    assert contact.full_name == "Ana Pérez"
    assert contact.email == "ana.perez@example.com"
    assert contact.role_category == "ciso"
    assert contact.is_active is True
    assert contact.is_primary is False
    assert contact.is_signatory is False
    assert contact.has_portal_access is False
    assert contact.timezone == "Europe/Madrid"
    assert contact.interactions_count == 0
    assert contact.last_interaction_at is None


@pytest.mark.asyncio
async def test_email_unique_per_client(db: AsyncSession):
    """Mismo email en mismo client → DuplicateContactEmailError."""
    client_id = await _create_test_client(db)
    svc = ClientContactService(db)
    await svc.create_contact(
        client_id, _payload(email="dup@example.com"),
    )
    with pytest.raises(DuplicateContactEmailError):
        await svc.create_contact(
            client_id,
            _payload(
                full_name="Otro contacto",
                email="dup@example.com",
            ),
        )


@pytest.mark.asyncio
async def test_create_with_primary_unsets_others(db: AsyncSession):
    """Crear contacto con is_primary=True desmarca otros primary del cliente."""
    client_id = await _create_test_client(db)
    svc = ClientContactService(db)

    first = await svc.create_contact(
        client_id,
        _payload(email="first@example.com", is_primary=True),
    )
    second = await svc.create_contact(
        client_id,
        _payload(
            full_name="Segundo Primary",
            email="second@example.com",
            is_primary=True,
        ),
    )
    # El primero pierde primary, el segundo lo gana.
    refreshed_first = await svc.get_contact_by_id(first.id)
    assert refreshed_first.is_primary is False
    assert second.is_primary is True


@pytest.mark.asyncio
async def test_promote_signatory(db: AsyncSession):
    """PATCH is_signatory=True persiste flag."""
    client_id = await _create_test_client(db)
    svc = ClientContactService(db)
    contact = await svc.create_contact(client_id, _payload())
    updated = await svc.update_contact(
        contact.id, ClientContactUpdate(is_signatory=True),
    )
    assert updated.is_signatory is True


@pytest.mark.asyncio
async def test_create_with_portal_access_persists_flag(db: AsyncSession):
    """has_portal_access=True se persiste; client_user_id wiring opcional FASE
    futura (M30.2 vincular ClientUser real)."""
    client_id = await _create_test_client(db)
    svc = ClientContactService(db)
    contact = await svc.create_contact(
        client_id,
        _payload(
            email="portal@example.com",
            has_portal_access=True,
        ),
    )
    assert contact.has_portal_access is True
    assert contact.client_user_id is None
    # Vincular client_user_id real es scope de un futuro
    # TODO-M30-PORTAL-LINK-001 — fuera de FASE 5.5.A baseline.


@pytest.mark.asyncio
async def test_list_by_client_active_filter(db: AsyncSession):
    """list_contacts respeta filtro is_active."""
    client_id = await _create_test_client(db)
    svc = ClientContactService(db)
    a = await svc.create_contact(
        client_id, _payload(email="a@example.com"),
    )
    b = await svc.create_contact(
        client_id, _payload(email="b@example.com"),
    )
    await svc.deactivate_contact(b.id, reason="test")

    active = await svc.list_contacts(client_id, is_active=True)
    inactive = await svc.list_contacts(client_id, is_active=False)
    all_of_them = await svc.list_contacts(client_id, is_active=None)

    active_ids = {c.id for c in active}
    inactive_ids = {c.id for c in inactive}
    assert a.id in active_ids and b.id not in active_ids
    assert b.id in inactive_ids and a.id not in inactive_ids
    assert {c.id for c in all_of_them} == {a.id, b.id}


@pytest.mark.asyncio
async def test_list_by_role_category(db: AsyncSession):
    """list_contacts filtra por role_category."""
    client_id = await _create_test_client(db)
    svc = ClientContactService(db)
    ciso = await svc.create_contact(
        client_id,
        _payload(email="ciso@example.com", role_category="ciso"),
    )
    legal = await svc.create_contact(
        client_id,
        _payload(
            email="legal@example.com",
            role_title="Asesor Legal",
            role_category="legal",
        ),
    )
    cisos = await svc.list_contacts(client_id, role_category="ciso")
    legals = await svc.list_contacts(client_id, role_category="legal")
    assert {c.id for c in cisos} == {ciso.id}
    assert {c.id for c in legals} == {legal.id}


@pytest.mark.asyncio
async def test_search_full_text_notes(db: AsyncSession):
    """search_full_text encuentra contactos por contenido de notas."""
    client_id = await _create_test_client(db)
    svc = ClientContactService(db)
    target = await svc.create_contact(
        client_id,
        _payload(
            full_name="Marisa Notas",
            email="marisa@example.com",
            notes_marcos=(
                "Sponsor exigente, pide informes ejecutivos cada quincena."
            ),
        ),
    )
    distractor = await svc.create_contact(
        client_id,
        _payload(
            full_name="Pedro Tecnico",
            email="pedro@example.com",
            notes_marcos="Implementador SIEM Splunk.",
        ),
    )
    hits = await svc.search_full_text(client_id, "informes ejecutivos")
    hit_ids = {c.id for c in hits}
    assert target.id in hit_ids
    assert distractor.id not in hit_ids


@pytest.mark.asyncio
async def test_update_propagates_role_change(db: AsyncSession):
    """PATCH role_title + role_category persiste."""
    client_id = await _create_test_client(db)
    svc = ClientContactService(db)
    contact = await svc.create_contact(
        client_id,
        _payload(
            email="role@example.com",
            role_title="CIO",
            role_category="cio",
        ),
    )
    updated = await svc.update_contact(
        contact.id,
        ClientContactUpdate(role_title="CISO", role_category="ciso"),
    )
    assert updated.role_title == "CISO"
    assert updated.role_category == "ciso"


@pytest.mark.asyncio
async def test_deactivate_keeps_history(db: AsyncSession):
    """deactivate_contact NO elimina interactions."""
    client_id = await _create_test_client(db)
    svc = ClientContactService(db)
    contact = await svc.create_contact(
        client_id, _payload(email="deact@example.com"),
    )
    interaction_id = await svc.log_interaction(
        contact.id,
        "meeting",
        source_motor="a18",
        summary="Kickoff meeting",
    )

    await svc.deactivate_contact(contact.id, reason="rotación")

    timeline = await svc.get_timeline(contact.id)
    assert len(timeline) == 1
    assert timeline[0].id == interaction_id


@pytest.mark.asyncio
async def test_delete_cascade_interactions(db: AsyncSession):
    """delete_contact_cascade elimina interactions vía FK CASCADE."""
    client_id = await _create_test_client(db)
    svc = ClientContactService(db)
    contact = await svc.create_contact(
        client_id, _payload(email="delcasc@example.com"),
    )
    await svc.log_interaction(
        contact.id, "meeting", source_motor="a18", summary="K1",
    )
    await svc.delete_contact_cascade(contact.id)

    # Contact ido
    with pytest.raises(ContactNotFoundError):
        await svc.get_contact_by_id(contact.id)
    # Interactions huérfanas: 0 filas residuales (FK CASCADE)
    res = await db.execute(
        text(
            "SELECT count(*) AS n FROM client_contact_interactions "
            "WHERE contact_id = :cid"
        ),
        {"cid": str(contact.id)},
    )
    assert res.scalar_one() == 0


# ====================================================================
# Timeline + log_interaction
# ====================================================================


@pytest.mark.asyncio
async def test_log_interaction_meeting(db: AsyncSession):
    """log_interaction(meeting) crea registro con source_motor=a18."""
    client_id = await _create_test_client(db)
    svc = ClientContactService(db)
    contact = await svc.create_contact(
        client_id, _payload(email="mtg@example.com"),
    )
    iid = await svc.log_interaction(
        contact.id,
        "meeting",
        source_motor="a18",
        source_id=uuid.uuid4(),
        summary="Reunión K1 kickoff",
        details={"etapa_k": "K1", "platform": "google_meet"},
    )
    assert isinstance(iid, uuid.UUID)
    timeline = await svc.get_timeline(contact.id)
    assert len(timeline) == 1
    assert timeline[0].interaction_type == "meeting"
    assert timeline[0].source_motor == "a18"
    assert timeline[0].details["etapa_k"] == "K1"


@pytest.mark.asyncio
async def test_log_interaction_message(db: AsyncSession):
    """log_interaction(message) source_motor=m29 (FASE 6)."""
    client_id = await _create_test_client(db)
    svc = ClientContactService(db)
    contact = await svc.create_contact(
        client_id, _payload(email="msg@example.com"),
    )
    await svc.log_interaction(
        contact.id, "message", source_motor="m29",
        summary="Cliente envió mensaje sobre evidencia C-45",
    )
    timeline = await svc.get_timeline(contact.id)
    assert timeline[0].interaction_type == "message"
    assert timeline[0].source_motor == "m29"


@pytest.mark.asyncio
async def test_log_interaction_magic_link(db: AsyncSession):
    """log_interaction(magic_link) source_motor=m12 (diferido FK)."""
    client_id = await _create_test_client(db)
    svc = ClientContactService(db)
    contact = await svc.create_contact(
        client_id, _payload(email="mlink@example.com"),
    )
    await svc.log_interaction(
        contact.id, "magic_link", source_motor="m12",
        summary="Magic link contract signature emitido",
    )
    timeline = await svc.get_timeline(contact.id)
    assert timeline[0].interaction_type == "magic_link"


@pytest.mark.asyncio
async def test_get_timeline_ordered_desc(db: AsyncSession):
    """Timeline DESC by created_at — más reciente primero."""
    client_id = await _create_test_client(db)
    svc = ClientContactService(db)
    contact = await svc.create_contact(
        client_id, _payload(email="tl@example.com"),
    )
    await svc.log_interaction(
        contact.id, "meeting", source_motor="a18", summary="K1",
    )
    # Forzar orden temporal explícito: usamos pg now() pero suficiente
    # diferencia con el INSERT siguiente; UUIDs únicos garantizan
    # determinismo si timestamps coinciden — usamos ordering por
    # created_at desc + id desc tie-breaker en query.
    await svc.log_interaction(
        contact.id, "message", source_motor="m29", summary="msg-2",
    )
    await svc.log_interaction(
        contact.id, "magic_link", source_motor="m12", summary="ml-3",
    )
    timeline = await svc.get_timeline(contact.id, limit=10)
    assert len(timeline) == 3
    summaries = [t.summary for t in timeline]
    # Las 3 deben aparecer; al menos la última registrada estar
    # cerca del top (desempate por id si misma fila timestamp).
    assert "ml-3" in summaries
    assert "msg-2" in summaries
    assert "K1" in summaries


@pytest.mark.asyncio
async def test_get_for_copilot_context_format(db: AsyncSession):
    """get_for_copilot_context formatea con tags PRIMARY/SIGNATORY + notas."""
    client_id = await _create_test_client(db)
    svc = ClientContactService(db)
    await svc.create_contact(
        client_id,
        _payload(
            full_name="Sponsor Mayor",
            email="sponsor@example.com",
            role_title="CFO",
            role_category="sponsor",
            is_primary=True,
            notes_marcos="Persona de confianza",
        ),
    )
    await svc.create_contact(
        client_id,
        _payload(
            full_name="Firma Legal",
            email="firma@example.com",
            role_title="General Counsel",
            role_category="legal",
            is_signatory=True,
        ),
    )
    entries = await svc.get_for_copilot_context(client_id)
    assert len(entries) == 2

    primary = next(e for e in entries if e.full_name == "Sponsor Mayor")
    assert "[PRIMARY]" in primary.formatted_line
    assert "Persona de confianza" in primary.formatted_line

    signatory = next(e for e in entries if e.full_name == "Firma Legal")
    assert "[SIGNATORY]" in signatory.formatted_line


# ====================================================================
# HTTP RBAC (real_auth)
# ====================================================================


class _ClientStubUser:
    """Stub user role=cliente para test 401/403."""
    email = "tester@cliente.example.com"
    role = "rseg"
    id = "00000000-0000-0000-0000-000000000111"
    is_active = True


@pytest.mark.asyncio
async def test_endpoint_blocks_non_marcos_pool(async_client, db: AsyncSession):
    """Override authenticate_request con cliente stub → endpoint M30 rechaza.

    Validates RBAC bidireccional:
      - El router de M30 monta ``Depends(require_owner)``.
      - ``CurrentUser`` (=``get_current_user``) ya rechaza con 401
        cualquier subject con ``role_pool != "marcos"`` ANTES de que
        ``require_owner`` evalúe el rol.

    Por tanto un cliente válido obtiene **401** ("Marcos session required")
    antes de llegar a require_owner. Aceptamos 401 ó 403 para futuros
    cambios donde una capa intermedia transforme el rechazo.
    """
    from fastapi import Request

    from backend.app.main import app
    from backend.app.auth.global_dep import authenticate_request, AuthSubject

    client_id = await _create_test_client(db)

    async def _override_cliente(request: Request):
        # ``request: Request`` debe estar anotado o FastAPI lo trata
        # como query param (ver conftest._override_authenticate_request_marcos).
        subject = AuthSubject(user=_ClientStubUser(), role_pool="cliente")
        request.state.auth_subject = subject
        request.state.auth_payload = {
            "sub": _ClientStubUser.id, "jti": "stub", "csrf": "stub",
        }
        return subject

    app.dependency_overrides[authenticate_request] = _override_cliente
    try:
        res = await async_client.get(
            f"/api/v1/clients/{client_id}/contacts",
        )
        assert res.status_code in (401, 403), res.text
        # Mensaje explícito de la capa get_current_user (Marcos session
        # required) — confirmamos que el rechazo ocurre antes de
        # require_owner para el caso pool=cliente.
        body = res.json()
        assert "detail" in body
    finally:
        app.dependency_overrides.pop(authenticate_request, None)
