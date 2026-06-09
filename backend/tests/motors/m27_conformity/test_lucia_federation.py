"""Tests LUCIA federación · SAN-C.MB-10.3.

Cobertura:

* Encriptación/desencriptación credentials con Fernet
* Construcción payload canónico CCN-STIC 845 + hash determinístico
* Submit incident sin credenciales → status pending_credentials + persist
* Submit incident con credenciales mock httpx → status sent + remote ID
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import httpx
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m27_conformity.lucia_federation import (
    LuciaIncidentPayload,
    build_canonical_payload,
    decrypt_credentials_field,
    encrypt_credentials_field,
    hash_payload,
    submit_incident,
)
from backend.tests.conftest import _admin_setup


def _master_key() -> str:
    return Fernet.generate_key().decode()


def _sample_payload() -> LuciaIncidentPayload:
    return LuciaIncidentPayload(
        incident_id=uuid.uuid4(),
        severity="ALTA",
        title="Compromiso credenciales privilegiadas",
        description="Detección de credenciales admin en pastebin público.",
        detected_at=datetime(2026, 5, 5, 10, 30, tzinfo=timezone.utc),
        affected_systems=["Sede electrónica", "BBDD principal"],
        timeline=[
            {"at": "2026-05-05T10:30Z", "event": "Detección"},
            {"at": "2026-05-05T10:45Z", "event": "Contención iniciada"},
        ],
        classification="CCN-CERT-A1-CREDENCIALES",
        impact_assessment="Acceso no autorizado potencial sin confirmación uso.",
        contention_actions=["Rotación credenciales", "Revisión accesos 7d"],
    )


def test_fernet_roundtrip_credentials():
    key = _master_key()
    plaintext = "client_secret_test_xxx_zzz"
    cipher = encrypt_credentials_field(plaintext, key)
    assert cipher != plaintext
    assert decrypt_credentials_field(cipher, key) == plaintext


def test_canonical_payload_hash_determinist():
    payload = _sample_payload()
    canonical_a = build_canonical_payload(payload)
    canonical_b = build_canonical_payload(payload)
    assert canonical_a == canonical_b
    assert hash_payload(canonical_a) == hash_payload(canonical_b)
    assert canonical_a["@schema"] == "CCN-STIC-845-incident-v1"
    assert canonical_a["severity"] == "ALTA"


@pytest.mark.asyncio
async def test_submit_without_credentials_returns_pending(db: AsyncSession):
    """Sin credenciales registradas → pending_credentials + persist."""
    from backend.app.database import set_tenant_context

    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"

    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, sector, created_at) "
                "VALUES (:cid, :nombre, :cif, 'publico', now())"
            ),
            {"cid": str(client_id), "nombre": f"Test L {cif}", "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, fase, created_at) "
                "VALUES (:pid, :cid, 'Lucia test', 'verificacion', now())"
            ),
            {"pid": str(project_id), "cid": str(client_id)},
        )

    await set_tenant_context(db, client_id=client_id, project_id=project_id)
    payload = _sample_payload()
    result = await submit_incident(db, project_id, payload, _master_key())

    assert result.status == "pending_credentials"
    assert result.submission_id_remote is None
    assert result.artifact_hash
    assert "manual" in (result.error_detail or "").lower() or "manual" in (result.error_detail or "")


@pytest.mark.asyncio
async def test_submit_with_credentials_mock_httpx_returns_sent(db: AsyncSession):
    """Con credenciales registradas + httpx mock → status sent + remote_id."""
    from backend.app.database import set_tenant_context

    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    master_key = _master_key()

    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, sector, created_at) "
                "VALUES (:cid, :nombre, :cif, 'publico', now())"
            ),
            {"cid": str(client_id), "nombre": f"Test LL {cif}", "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, fase, created_at) "
                "VALUES (:pid, :cid, 'Lucia mock', 'verificacion', now())"
            ),
            {"pid": str(project_id), "cid": str(client_id)},
        )
        # Persist credenciales (con Fernet local · NO la master key real)
        await db.execute(
            text(
                "INSERT INTO lucia_credentials "
                "(project_id, organization_id_lucia, client_id_oauth, "
                " client_secret_encrypted, endpoint_base_url) "
                "VALUES (:pid, 'ORG-TEST', 'oauth-client', :sec, "
                "        'https://lucia-test.local/api')"
            ),
            {
                "pid": str(project_id),
                "sec": encrypt_credentials_field("test-secret-123", master_key),
            },
        )

    # Mock transport httpx
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Organization-Id"] == "ORG-TEST"
        body = json.loads(request.content)
        assert body["@schema"] == "CCN-STIC-845-incident-v1"
        return httpx.Response(
            201,
            json={"submission_id": "LUCIA-SUB-123", "status": "received"},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as mock_client:
        await set_tenant_context(db, client_id=client_id, project_id=project_id)
        payload = _sample_payload()
        result = await submit_incident(
            db, project_id, payload, master_key, http_client=mock_client
        )

    assert result.status == "sent"
    assert result.submission_id_remote == "LUCIA-SUB-123"
    assert result.error_detail is None
