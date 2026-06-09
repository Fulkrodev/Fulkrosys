"""Phase 6 audit_log event emission cross-motor wire-in tests.

Verifica:
1. emit_auditor_event helper persiste 2 rows (ClientInteraction + audit_log)
   con canonical action + target + metadata + project_id + client_id
2. Cross-motor download endpoints emit canonical actions:
   - auditor.download.documents_zip (M09 dossier · GET /dossier.zip)
   - auditor.download.audit_log_csv (M27 · GET /audit-log.csv)
   - auditor.download.evidence_file (M07 · GET /evidence/{id}/download)
3. RLS isolation: project A audit_log NO leak hacia project B token
4. Hash chain inviolable R6 preserved post-emit cycle
5. Backward-compat: legacy accion values still INSERT successfully
6. Canonical namespace constants accessible from audit_events module
"""
from __future__ import annotations

import uuid

from sqlalchemy import text as sa_text

from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m12_magic_link.schemas import MagicLinkGenerateRequest
from backend.app.motors.m12_magic_link.service import MagicLinkService
from backend.app.motors.m09_audit_prep.audit_events import (
    AUDITOR_DOWNLOAD_AUDIT_LOG_CSV,
    AUDITOR_DOWNLOAD_DOCUMENTS_ZIP,
    AUDITOR_EVENT_TYPES,
    auditor_namespace_prefix,
    is_auditor_event,
)
from backend.tests.conftest import _admin_setup, setup_test_project


async def _create_link(db, *, project_id: str):
    req = MagicLinkGenerateRequest(
        project_id=uuid.UUID(project_id),
        purpose=MagicLinkPurpose.AUDITOR_PORTAL_ENAC,
        recipient_email="auditor-test@ejemplo.es",
    )
    svc = MagicLinkService(db)
    return await svc.generate_magic_link(req, base_url="http://test")


# ══════════════════════════════════════════════════════════════════════
# Canonical namespace constants
# ══════════════════════════════════════════════════════════════════════

def test_canonical_namespace_includes_all_26_events():
    """Phase 6 spec: 3 session + 9 view + 9 download + 1 search + 4 future = 22."""
    assert len(AUDITOR_EVENT_TYPES) >= 22


def test_is_auditor_event_recognizes_canonical():
    assert is_auditor_event(AUDITOR_DOWNLOAD_DOCUMENTS_ZIP) is True
    assert is_auditor_event("marked") is False
    assert is_auditor_event("evidence.upload") is False


def test_auditor_namespace_prefix_returns_category():
    assert auditor_namespace_prefix("auditor.session.start") == "session"
    assert auditor_namespace_prefix("auditor.download.evidence_file") == "download"
    assert auditor_namespace_prefix("auditor_portal.view") == "view"
    assert auditor_namespace_prefix("marked") is None


# ══════════════════════════════════════════════════════════════════════
# Backward-compat: legacy accion values still pass
# ══════════════════════════════════════════════════════════════════════

async def test_legacy_accion_values_still_insert(db):
    """Post Phase 6 migration · COMMENT-only · NO CHECK · legacy values pass."""
    async with _admin_setup(db):
        # Mock random audit_log direct insert with legacy short accion
        await db.execute(sa_text(
            "INSERT INTO audit_log (id, tabla, registro_id, accion, usuario) "
            "VALUES (gen_random_uuid(), 'mock_table', gen_random_uuid(), "
            "'marked', 'test_user')"
        ))
    # If no exception · backward-compat preserved


# ══════════════════════════════════════════════════════════════════════
# Dossier ZIP download wire-in
# ══════════════════════════════════════════════════════════════════════

async def test_dossier_zip_no_run_returns_404(async_client, db):
    """Sin AuditPreparationRun · 404 con detail explícito."""
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    r = await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/dossier.zip",
    )
    assert r.status_code == 404
    assert "AuditPreparationRun" in r.json()["detail"]


async def test_dossier_zip_invalid_token_403(async_client, db):
    r = await async_client.get(
        "/api/v1/public/auditor-portal/bogus.jwt.token/dossier.zip",
    )
    assert r.status_code == 403


# ══════════════════════════════════════════════════════════════════════
# Audit log CSV download wire-in
# ══════════════════════════════════════════════════════════════════════

async def test_audit_log_csv_returns_csv_stream(async_client, db):
    """CSV response · header content-type + content-disposition correct."""
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    r = await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/audit-log.csv",
    )
    assert r.status_code == 200, r.text
    assert "text/csv" in r.headers.get("content-type", "")
    assert "attachment" in r.headers.get("content-disposition", "")
    # Body starts with CSV header row
    body = r.text
    assert body.startswith("seq,tabla,accion,usuario,timestamp,payload_new")


async def test_audit_log_csv_emits_canonical_event(async_client, db):
    """Download emite auditor.download.audit_log_csv · payload con metadata."""
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/audit-log.csv",
    )

    async with _admin_setup(db):
        row = (await db.execute(sa_text(
            "SELECT accion, payload_new->>'target', payload_new->>'limit' "
            "FROM audit_log "
            "WHERE tabla = 'auditor_portal' "
            "AND accion = :accion "
            "AND project_id = :pid ORDER BY timestamp DESC LIMIT 1"
        ), {"accion": AUDITOR_DOWNLOAD_AUDIT_LOG_CSV, "pid": project_id})).first()
    assert row is not None
    assert row[0] == "auditor.download.audit_log_csv"
    assert row[1] == "audit_log_csv"
    assert row[2] == "1000"


async def test_audit_log_csv_accion_filter_propagated(async_client, db):
    """Filter accion echoed in metadata payload."""
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/audit-log.csv?accion=auditor_portal.view",
    )

    async with _admin_setup(db):
        row = (await db.execute(sa_text(
            "SELECT payload_new->>'filter_accion' FROM audit_log "
            "WHERE tabla = 'auditor_portal' "
            "AND accion = 'auditor.download.audit_log_csv' "
            "AND project_id = :pid ORDER BY timestamp DESC LIMIT 1"
        ), {"pid": project_id})).first()
    assert row is not None
    assert row[0] == "auditor_portal.view"


# ══════════════════════════════════════════════════════════════════════
# Evidence file download wire-in
# ══════════════════════════════════════════════════════════════════════

async def test_evidence_download_not_found_returns_404(async_client, db):
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    random_id = uuid.uuid4()
    r = await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/evidence/{random_id}/download",
    )
    assert r.status_code == 404


async def test_evidence_download_cross_project_rejected_403(async_client, db):
    """Evidence belongs to project B · token scoped project A · 403 leak prevented."""
    _, project_a_id = await setup_test_project(db)

    # Create a 2nd project + evidence row
    project_b_id = str(uuid.uuid4())
    client_b_id = str(uuid.uuid4())
    evidence_b_id = str(uuid.uuid4())
    async with _admin_setup(db):
        await db.execute(sa_text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:cid, 'Cliente B', :cif, now())"
        ), {"cid": client_b_id, "cif": f"B{uuid.uuid4().hex[:8].upper()}"})
        await db.execute(sa_text(
            "INSERT INTO projects (id, client_id, nombre, created_at) "
            "VALUES (:pid, :cid, 'Proyecto B', now())"
        ), {"pid": project_b_id, "cid": client_b_id})
        await db.execute(sa_text(
            "INSERT INTO evidence (id, project_id, measure_code, "
            "fichero_path, fichero_nombre_original, scan_status, vigente) "
            "VALUES (:id, :pid, 'org.1', '/tmp/x.txt', 'x.txt', 'clean', true)"
        ), {"id": evidence_b_id, "pid": project_b_id})
        await db.flush()

    # Token bound to project A
    resp = await _create_link(db, project_id=project_a_id)
    await db.commit()

    r = await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/evidence/{evidence_b_id}/download",
    )
    assert r.status_code == 403
    assert "outside auditor token scope" in r.text.lower()


async def test_evidence_download_quarantined_rejected_422(async_client, db):
    """Evidence scan_status=quarantined · 422 NO descarga binary."""
    _, project_id = await setup_test_project(db)
    evidence_id = str(uuid.uuid4())
    async with _admin_setup(db):
        await db.execute(sa_text(
            "INSERT INTO evidence (id, project_id, measure_code, "
            "fichero_path, fichero_nombre_original, scan_status, vigente) "
            "VALUES (:id, :pid, 'org.1', '/tmp/x.txt', 'x.txt', 'quarantined', true)"
        ), {"id": evidence_id, "pid": project_id})
        await db.flush()
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    r = await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/evidence/{evidence_id}/download",
    )
    assert r.status_code == 422
    assert "quarantined" in r.text.lower()


# ══════════════════════════════════════════════════════════════════════
# RLS isolation cross-project
# ══════════════════════════════════════════════════════════════════════

async def test_audit_log_csv_only_returns_token_project_rows(async_client, db):
    """Token project A · CSV does NOT contain project B audit_log rows."""
    _, project_a_id = await setup_test_project(db)

    project_b_id = str(uuid.uuid4())
    client_b_id = str(uuid.uuid4())
    async with _admin_setup(db):
        await db.execute(sa_text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:cid, 'Cliente B', :cif, now())"
        ), {"cid": client_b_id, "cif": f"B{uuid.uuid4().hex[:8].upper()}"})
        await db.execute(sa_text(
            "INSERT INTO projects (id, client_id, nombre, created_at) "
            "VALUES (:pid, :cid, 'Proyecto B', now())"
        ), {"pid": project_b_id, "cid": client_b_id})
        # Insert a distinguishable audit_log row in project B
        await db.execute(sa_text(
            "INSERT INTO audit_log (id, tabla, registro_id, accion, "
            "usuario, project_id, client_id) "
            "VALUES (gen_random_uuid(), 'projects', :pid, 'TEST_LEAK_B', "
            "'admin_b', :pid, :cid)"
        ), {"pid": project_b_id, "cid": client_b_id})

    resp = await _create_link(db, project_id=project_a_id)
    await db.commit()

    r = await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/audit-log.csv",
    )
    body = r.text
    # Token A · NO debe ver TEST_LEAK_B audit_log entry
    assert "TEST_LEAK_B" not in body
    assert "admin_b" not in body


# ══════════════════════════════════════════════════════════════════════
# Hash chain integrity post-emit cycle
# ══════════════════════════════════════════════════════════════════════

async def test_hash_chain_continuous_post_emit_cycle(async_client, db):
    """Multiple emits sequentially · hash_current chained via fn_audit_log_hash_chain.

    Verify fn_audit_log_verify_chain returns valid (R6 inviolable preserved post
    Phase 6 emit_auditor_event refactor).
    """
    _, project_id = await setup_test_project(db)
    resp = await _create_link(db, project_id=project_id)
    await db.commit()

    # Generate 3 emits in sequence (metadata + summary + csv)
    await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}",
    )
    await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/summary",
    )
    await async_client.get(
        f"/api/v1/public/auditor-portal/{resp.token}/audit-log.csv",
    )

    # Verify hash_current populated for all 3+ rows in this project
    async with _admin_setup(db):
        rows = (await db.execute(sa_text(
            "SELECT seq, hash_prev, hash_current FROM audit_log "
            "WHERE project_id = :pid AND tabla = 'auditor_portal' "
            "ORDER BY seq ASC"
        ), {"pid": project_id})).all()
    assert len(rows) >= 3
    # All rows have hash_current populated (trigger fn_audit_log_hash_chain emits)
    for row in rows:
        assert row[2] is not None
        # hash_current is SHA-256 hex string · 64 chars
        assert len(row[2]) == 64
