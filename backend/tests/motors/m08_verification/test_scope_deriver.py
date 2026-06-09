"""M8 v5.1 — Tests de scope_deriver."""
from __future__ import annotations

import uuid

import pytest

from backend.app.database import set_tenant_context
from backend.app.models.onboarding import DiscoveredAsset
from backend.app.motors.m08_verification.scope_deriver import (
    DEFAULT_SCAN_WINDOW,
    EmptyScopeError,
    derive_scope,
)
from backend.tests.conftest import setup_test_project


# ────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────

async def _create_asset(
    db, project_id: str,
    *, nombre="srv01", tipo="HW",
    ip=None, services=None, fuente="manual",
):
    asset = DiscoveredAsset(
        project_id=uuid.UUID(project_id),
        nombre=nombre,
        tipo_magerit=tipo,
        fuente_conector=fuente,
        criticidad_propuesta="media",
        metadata_extra={
            "ip": ip,
            "services": services or [],
        },
    )
    db.add(asset)
    await db.flush()
    return asset


# ────────────────────────────────────────────────────────────────────
# Tests
# ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_derive_scope_empty_project_default(db):
    """Sin assets y require_assets=False (default) devuelve scope vacio."""
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    scope, derived = await derive_scope(
        db, uuid.UUID(project_id), category="BASICO",
    )
    assert scope["targets"] == []
    assert scope["scan_window"] == DEFAULT_SCAN_WINDOW
    assert scope["totals"]["discovered_assets"] == 0
    assert derived["scan_window_source"] == "default"


@pytest.mark.asyncio
async def test_derive_scope_empty_with_require_raises(db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    with pytest.raises(EmptyScopeError):
        await derive_scope(
            db, uuid.UUID(project_id), category="BASICO",
            require_assets=True,
        )


@pytest.mark.asyncio
async def test_derive_scope_extracts_ips_and_web_apps(db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    await _create_asset(
        db, project_id, nombre="web01", tipo="HW",
        ip="10.0.1.5", services=["http", "https", "ssh"],
    )
    await _create_asset(
        db, project_id, nombre="db01", tipo="HW",
        ip="10.0.1.10", services=["postgresql"],
    )
    scope, derived = await derive_scope(
        db, uuid.UUID(project_id), category="MEDIO",
    )
    assert "10.0.1.5" in scope["targets"]
    assert "10.0.1.10" in scope["targets"]
    # Tiene https → web_apps con scheme https
    assert any("https://" in url for url in scope["web_apps"])
    # SSH accessible
    assert "10.0.1.5" in scope["ssh_accessible"]


@pytest.mark.asyncio
async def test_derive_scope_classifies_cloud_assets(db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    await _create_asset(
        db, project_id, nombre="user1@x.es", tipo="m365_user",
        fuente="microsoft_365",
    )
    await _create_asset(
        db, project_id, nombre="prod-bucket", tipo="aws_s3_bucket",
        fuente="aws",
    )
    scope, _ = await derive_scope(
        db, uuid.UUID(project_id), category="MEDIO",
    )
    # Cloud assets en su bucket dedicado, no en targets
    assert len(scope["cloud_accounts"]) == 2
    assert all(a["asset_name"] in {"user1@x.es", "prod-bucket"}
               for a in scope["cloud_accounts"])


@pytest.mark.asyncio
async def test_derive_scope_totals_correct(db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    for i in range(3):
        await _create_asset(
            db, project_id, nombre=f"srv{i}",
            ip=f"10.0.1.{i+1}", services=["ssh"],
        )
    scope, _ = await derive_scope(
        db, uuid.UUID(project_id), category="BASICO",
    )
    assert scope["totals"]["discovered_assets"] == 3
    assert scope["totals"]["targets"] == 3
    assert scope["totals"]["ssh"] == 3
