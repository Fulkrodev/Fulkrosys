"""DPA endpoint + template tests (atom 9.bis.3).

3 tests:
- DPA public download endpoint returns DOCX without auth
- DPA template embeds FULKRO controller data + cliente placeholders
- DPA admin sign endpoint updates clients.dpa_signed_* columns
"""
from __future__ import annotations

import uuid
import zipfile
from datetime import datetime, timezone
from io import BytesIO

import pytest
from sqlalchemy import text

from backend.app.motors.m_compliance.dpa_template import (
    DEFAULT_FIELDS,
    DPA_VERSION,
    build_dpa_docx,
)


@pytest.mark.asyncio
async def test_dpa_template_download_public_no_auth(async_client) -> None:
    """DPA template is downloadable without authentication."""
    r = await async_client.get("/api/v1/legal/dpa-template/download")
    assert r.status_code == 200
    ctype = r.headers.get("content-type", "")
    assert "wordprocessingml" in ctype
    # docx is a zip file.
    buf = BytesIO(r.content)
    assert zipfile.is_zipfile(buf)


def test_dpa_template_populated_fulkro_data() -> None:
    """Builder substitutes FULKRO + placeholder fields into the DOCX."""
    buf = build_dpa_docx({"CLIENTE_NOMBRE": "Acme Tests S.L."})
    body = _extract_docx_text(buf)
    # FULKRO identification pre-populated.
    assert "Marcos Mata García" in body
    assert "dpo@fulkro.es" in body
    assert "Madrid (España)" in body
    # Caller-overridden field flows through.
    assert "Acme Tests S.L." in body
    # Other fields remain as placeholders.
    assert DEFAULT_FIELDS["CLIENTE_CIF"] in body
    # Article 28 sections present.
    assert "Artículo 28" in body
    assert "Anexo I" in body
    assert "Anexo II" in body
    assert "Anexo III" in body
    assert f"Versión {DPA_VERSION}" in body


@pytest.mark.asyncio
async def test_dpa_sign_records_signature(async_client, db) -> None:
    """Admin sign endpoint updates clients.dpa_signed_*."""
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    client_id = uuid.uuid4()
    # Insert as superuser (RLS bypass via session role).
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    await db.execute(
        text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'Acme Tests', :cif, now())"
        ),
        {"id": str(client_id), "cif": cif},
    )
    await db.execute(text("RESET ROLE"))
    await db.flush()

    payload = {
        "dpa_version": "1.0",
        "signed_minio_path": (
            f"fulkro-documents/clients/{client_id}/dpa/signed-2026-05-12.pdf"
        ),
        "cliente_signature_timestamp": (
            datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc).isoformat()
        ),
        "fulkro_signature_timestamp": (
            datetime(2026, 5, 12, 13, 0, tzinfo=timezone.utc).isoformat()
        ),
    }
    # Auth required — patch dependency to bypass require_owner.
    from backend.app.main import app
    from backend.app.auth.dependencies import require_owner
    from backend.app.models.auth import User

    async def _fake_user() -> User:
        u = User()
        u.id = uuid.uuid4()
        u.email = "marcos@fulkro.es"
        return u

    app.dependency_overrides[require_owner] = _fake_user
    try:
        r = await async_client.post(
            f"/api/v1/admin/clients/{client_id}/dpa/sign", json=payload
        )
    finally:
        app.dependency_overrides.pop(require_owner, None)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["client_id"] == str(client_id)
    assert data["dpa_version"] == "1.0"
    assert data["dpa_signed_minio_path"] == payload["signed_minio_path"]

    # Verify persisted (endpoint commits internally; read on a fresh select).
    row = await db.execute(
        text("SELECT dpa_signed_at, dpa_version FROM clients WHERE id = :id"),
        {"id": str(client_id)},
    )
    record = row.first()
    assert record is not None
    assert record[0] is not None
    assert record[1] == "1.0"

    # Cleanup so other tests don't see the cif.
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    await db.execute(
        text("DELETE FROM clients WHERE id = :id"), {"id": str(client_id)}
    )
    await db.execute(text("RESET ROLE"))
    await db.flush()


def _extract_docx_text(buf: BytesIO) -> str:
    """Return the concatenated text content of a DOCX (BytesIO)."""
    from docx import Document

    buf.seek(0)
    doc = Document(buf)
    parts: list[str] = []
    for p in doc.paragraphs:
        parts.append(p.text)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    parts.append(p.text)
    return "\n".join(parts)
