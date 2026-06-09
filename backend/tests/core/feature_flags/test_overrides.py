"""Tests feature_flag_overrides service layer (ADR-037 · MB-10 Atom 10.2.D).

Cubre:
- grant_override creates row con scope correcto
- revoke_override soft delete (revoked_at NOT NULL · revoked_by_user_id required)
- resolve_project_features merges YAML defaults + active overrides
- expires_at past naturally filtered out
- subsequent reads reflect mutation immediately (no stale cache)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from backend.app.core.feature_flags.service import (
    grant_override,
    list_overrides,
    resolve_project_features,
    revoke_override,
)
from backend.app.models.core import Project
from backend.tests.conftest import _admin_setup


pytestmark = pytest.mark.asyncio


async def _seed_client_with_project(
    db,
    *,
    categoria: str = "BASICA",
    archetype: str | None = None,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Create client + project + admin user + set RLS tenant context.

    Returns (client_id, project_id, admin_user_id).
    """
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, 'Test Cli', :cif, now())"
            ),
            {"id": str(client_id), "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, "
                "categoria_objetivo, archetype, created_at) "
                "VALUES (:id, :cid, 'Test Proj', :cat, :arch, now())"
            ),
            {
                "id": str(project_id),
                "cid": str(client_id),
                "cat": categoria,
                "arch": archetype,
            },
        )
        await db.execute(
            text(
                "INSERT INTO auth_users "
                "(id, email, password_hash, role, created_at) "
                "VALUES (:id, :em, 'x', 'owner', now())"
            ),
            {"id": str(admin_id), "em": f"admin-{admin_id.hex[:8]}@test"},
        )
    await db.execute(
        text("SELECT set_config('app.current_client_id', :v, true)"),
        {"v": str(client_id)},
    )
    await db.execute(
        text("SELECT set_config('app.current_project_id', :v, true)"),
        {"v": str(project_id)},
    )
    await db.flush()
    return client_id, project_id, admin_id


async def _load_project_with_client(db, project_id: uuid.UUID) -> Project:
    stmt = (
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.client))
    )
    return (await db.execute(stmt)).scalar_one()


async def test_grant_override_creates_row(db):
    """grant_override inserts row con scope project_id."""
    _client_id, project_id, admin_id = await _seed_client_with_project(db)

    override = await grant_override(
        db,
        feature_key="alta_pentest_cpstic",
        override_value=True,
        granted_by_user_id=admin_id,
        project_id=project_id,
        reason="test grant",
    )

    assert override.id is not None
    assert override.feature_key == "alta_pentest_cpstic"
    assert override.override_value is True
    assert override.project_id == project_id
    assert override.client_id is None
    assert override.granted_by_user_id == admin_id
    assert override.revoked_at is None
    assert override.reason == "test grant"


async def test_grant_override_scope_required(db):
    """grant_override sin project_id ni client_id raise ValueError."""
    with pytest.raises(ValueError, match="project_id OR client_id"):
        await grant_override(
            db,
            feature_key="test",
            override_value=True,
            granted_by_user_id=None,
        )


async def test_revoke_override_soft_delete(db):
    """revoke_override sets revoked_at + revoked_by_user_id (soft delete)."""
    _client_id, project_id, admin_id = await _seed_client_with_project(db)

    override = await grant_override(
        db,
        feature_key="alta_red_team",
        override_value=True,
        granted_by_user_id=admin_id,
        project_id=project_id,
    )

    revoked = await revoke_override(
        db,
        override_id=override.id,
        revoked_by_user_id=admin_id,
        reason="no longer needed",
    )

    assert revoked is not None
    assert revoked.revoked_at is not None
    assert revoked.revoked_by_user_id == admin_id
    assert revoked.reason == "no longer needed"


async def test_revoke_override_missing_returns_none(db):
    """revoke_override de id inexistente retorna None (no raise)."""
    result = await revoke_override(
        db,
        override_id=uuid.uuid4(),
        revoked_by_user_id=uuid.uuid4(),
    )
    assert result is None


async def test_resolve_feature_flag_merges_yaml_plus_override(db):
    """resolve_project_features aplica override sobre YAML eval."""
    _client_id, project_id, admin_id = await _seed_client_with_project(
        db, categoria="BASICA"
    )
    project = await _load_project_with_client(db, project_id)

    baseline = await resolve_project_features(db, project)
    assert baseline["alta_pentest_cpstic"] is False  # BASICA: no aplica YAML

    await grant_override(
        db,
        feature_key="alta_pentest_cpstic",
        override_value=True,
        granted_by_user_id=admin_id,
        project_id=project_id,
    )
    merged = await resolve_project_features(db, project)
    assert merged["alta_pentest_cpstic"] is True  # override gana


async def test_expires_at_naturally_filtered(db):
    """expires_at past → override NO contribuye a resolve."""
    _client_id, project_id, admin_id = await _seed_client_with_project(
        db, categoria="BASICA"
    )
    project = await _load_project_with_client(db, project_id)

    expired = datetime.now(timezone.utc) - timedelta(hours=1)
    await grant_override(
        db,
        feature_key="alta_pentest_cpstic",
        override_value=True,
        granted_by_user_id=admin_id,
        project_id=project_id,
        expires_at=expired,
    )

    features = await resolve_project_features(db, project)
    assert features["alta_pentest_cpstic"] is False  # YAML default sigue


async def test_subsequent_read_reflects_mutation(db):
    """Tras grant/revoke, próxima read refleja estado actual sin cache stale."""
    _client_id, project_id, admin_id = await _seed_client_with_project(
        db, categoria="BASICA"
    )
    project = await _load_project_with_client(db, project_id)

    override = await grant_override(
        db,
        feature_key="alta_red_team",
        override_value=True,
        granted_by_user_id=admin_id,
        project_id=project_id,
    )
    granted_state = await resolve_project_features(db, project)
    assert granted_state["alta_red_team"] is True

    await revoke_override(
        db,
        override_id=override.id,
        revoked_by_user_id=admin_id,
    )
    revoked_state = await resolve_project_features(db, project)
    assert revoked_state["alta_red_team"] is False


async def test_client_level_override_applies_to_all_projects(db):
    """Override scope client_id afecta todos proyectos del cliente."""
    client_id, project_id, admin_id = await _seed_client_with_project(
        db, categoria="BASICA"
    )

    await grant_override(
        db,
        feature_key="alta_pentest_cpstic",
        override_value=True,
        granted_by_user_id=admin_id,
        client_id=client_id,
    )

    project = await _load_project_with_client(db, project_id)
    features = await resolve_project_features(db, project)
    assert features["alta_pentest_cpstic"] is True


async def test_project_override_wins_over_client_override(db):
    """Project-level override es más específico · gana sobre client-level."""
    client_id, project_id, admin_id = await _seed_client_with_project(
        db, categoria="BASICA"
    )

    await grant_override(
        db,
        feature_key="alta_red_team",
        override_value=True,
        granted_by_user_id=admin_id,
        client_id=client_id,
    )
    await grant_override(
        db,
        feature_key="alta_red_team",
        override_value=False,
        granted_by_user_id=admin_id,
        project_id=project_id,
    )

    project = await _load_project_with_client(db, project_id)
    features = await resolve_project_features(db, project)
    assert features["alta_red_team"] is False  # project wins


async def test_list_overrides_active_only_by_default(db):
    """list_overrides include_revoked=False filtra revocados."""
    _client_id, project_id, admin_id = await _seed_client_with_project(db)

    o1 = await grant_override(
        db,
        feature_key="alta_pentest_cpstic",
        override_value=True,
        granted_by_user_id=admin_id,
        project_id=project_id,
    )
    o2 = await grant_override(
        db,
        feature_key="alta_red_team",
        override_value=True,
        granted_by_user_id=admin_id,
        project_id=project_id,
    )
    await revoke_override(
        db, override_id=o2.id, revoked_by_user_id=admin_id
    )

    active = await list_overrides(db, project_id=project_id)
    assert len(active) == 1
    assert active[0].id == o1.id

    all_rows = await list_overrides(
        db, project_id=project_id, include_revoked=True
    )
    assert len(all_rows) == 2
