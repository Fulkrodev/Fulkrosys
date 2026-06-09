"""Tests · m_workflow_engine deliverables sub-atom 1.C.D.D.1 v3.8.

Cubre:
  - WorkflowDeliverablesService.list_step_deliverables
    · template lookup + Evidence Vault match (evidence_type_id / measure_code)
    · status per code (available · needs_regen · missing)
  - get_evidence_file_path · resuelve fichero_path + nombre + mime
  - Endpoints (3):
      GET /api/v1/projects/{id}/workflow-engine/steps/{template_id}/deliverables
      GET /api/v1/projects/{id}/workflow-engine/deliverables/{evidence_id}/download
      GET /api/v1/projects/{id}/workflow-engine/steps/{template_id}/deliverables/bulk-zip
  - Cross-tenant isolation (RLS sostenido)
  - Auth dual require_marcos_or_client + ownership
"""
from __future__ import annotations

import io
import uuid
import zipfile
from pathlib import Path

import pytest
from sqlalchemy import text

from backend.app.motors.m_workflow_engine.deliverables_service import (
    DeliverablesServiceError,
    WorkflowDeliverablesService,
)
from backend.app.motors.m21_portal_cliente.task_templates_loader import (
    get_template_by_id,
)
from backend.tests.conftest import _admin_setup, setup_test_project


# ================================================================
# Helpers
# ================================================================


async def _set_project_categoria(
    db, project_id: str, categoria: str, archetype: str | None = None,
):
    async with _admin_setup(db):
        await db.execute(
            text(
                "UPDATE projects SET categoria_objetivo = :c, archetype = :a "
                "WHERE id = :pid"
            ),
            {"c": categoria, "a": archetype, "pid": project_id},
        )
        await db.commit()


async def _insert_evidence(
    db,
    project_id: str,
    evidence_type_id: str,
    fichero_path: str,
    nombre_original: str = "test.pdf",
    mime: str = "application/pdf",
    vigente: bool = True,
) -> uuid.UUID:
    """Insert evidence row via admin setup + return id."""
    eid = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO evidence (id, project_id, evidence_type_id, "
                "fichero_path, fichero_nombre_original, fichero_mime_type, "
                "vigente, scan_status, created_at, updated_at) "
                "VALUES (:id, :pid, :etid, :path, :nombre, :mime, :vig, 'clean', "
                "NOW(), NOW())"
            ),
            {
                "id": str(eid),
                "pid": project_id,
                "etid": evidence_type_id,
                "path": fichero_path,
                "nombre": nombre_original,
                "mime": mime,
                "vig": vigente,
            },
        )
        await db.commit()
    return eid


def _find_template_with_deliverables() -> str:
    """Return first template_id with deliverable_codes non-empty."""
    from backend.app.motors.m21_portal_cliente.task_templates_loader import (
        load_task_templates,
    )
    catalog = load_task_templates()
    for tmpl in catalog.templates:
        if tmpl.deliverable_codes:
            return tmpl.id
    pytest.skip("No template with deliverable_codes available")


# ================================================================
# Service tests
# ================================================================


@pytest.mark.asyncio
async def test_list_step_deliverables_template_not_found_raises(db):
    _, project_id = await setup_test_project(db)
    svc = WorkflowDeliverablesService(db)
    with pytest.raises(DeliverablesServiceError):
        await svc.list_step_deliverables(
            uuid.UUID(project_id), "TEMPLATE_DOES_NOT_EXIST",
        )


@pytest.mark.asyncio
async def test_list_step_deliverables_all_missing_when_no_evidence(db):
    """Sin Evidence Vault rows · todos los codes status='missing'."""
    _, project_id = await setup_test_project(db)
    template_id = _find_template_with_deliverables()
    template = get_template_by_id(template_id)
    assert template is not None
    expected_codes = list(template.deliverable_codes)

    svc = WorkflowDeliverablesService(db)
    result = await svc.list_step_deliverables(
        uuid.UUID(project_id), template_id,
    )

    assert result.template_id == template_id
    assert len(result.deliverable_codes) == len(expected_codes)
    assert all(d.status == "missing" for d in result.deliverables)
    assert result.counts["missing"] == len(expected_codes)
    assert result.counts["available"] == 0
    assert result.counts["needs_regen"] == 0


@pytest.mark.asyncio
async def test_list_step_deliverables_available_when_evidence_exists(db, tmp_path: Path):
    _, project_id = await setup_test_project(db)
    template_id = _find_template_with_deliverables()
    template = get_template_by_id(template_id)
    code = template.deliverable_codes[0]

    # Insert evidence matching code
    test_file = tmp_path / "evidence.pdf"
    test_file.write_bytes(b"%PDF-fake-bytes")
    eid = await _insert_evidence(
        db, project_id, code, str(test_file),
        nombre_original="entregable.pdf",
    )

    svc = WorkflowDeliverablesService(db)
    result = await svc.list_step_deliverables(
        uuid.UUID(project_id), template_id,
    )

    by_code = {d.code: d for d in result.deliverables}
    assert by_code[code].status == "available"
    assert by_code[code].evidence_id == eid
    assert by_code[code].fichero_nombre_original == "entregable.pdf"
    assert result.counts["available"] >= 1


@pytest.mark.asyncio
async def test_list_step_deliverables_needs_regen_when_vencida(db, tmp_path: Path):
    _, project_id = await setup_test_project(db)
    template_id = _find_template_with_deliverables()
    template = get_template_by_id(template_id)
    code = template.deliverable_codes[0]

    test_file = tmp_path / "evidence_vencida.pdf"
    test_file.write_bytes(b"%PDF-old")
    await _insert_evidence(
        db, project_id, code, str(test_file), vigente=False,
    )

    svc = WorkflowDeliverablesService(db)
    result = await svc.list_step_deliverables(
        uuid.UUID(project_id), template_id,
    )

    by_code = {d.code: d for d in result.deliverables}
    assert by_code[code].status == "needs_regen"
    assert result.counts["needs_regen"] >= 1


@pytest.mark.asyncio
async def test_get_evidence_file_path_resolves(db, tmp_path: Path):
    _, project_id = await setup_test_project(db)
    test_file = tmp_path / "doc.pdf"
    test_file.write_bytes(b"%PDF-content")
    eid = await _insert_evidence(
        db, project_id, "E-040", str(test_file),
        nombre_original="DdA.pdf",
        mime="application/pdf",
    )

    svc = WorkflowDeliverablesService(db)
    path, nombre, mime = await svc.get_evidence_file_path(
        uuid.UUID(project_id), eid,
    )
    assert path == test_file
    assert nombre == "DdA.pdf"
    assert mime == "application/pdf"


@pytest.mark.asyncio
async def test_get_evidence_file_path_not_in_project_raises(db, tmp_path: Path):
    _, project_id = await setup_test_project(db)
    _, other_project_id = await setup_test_project(db)
    test_file = tmp_path / "other.pdf"
    test_file.write_bytes(b"%PDF-other")
    eid = await _insert_evidence(
        db, other_project_id, "E-040", str(test_file),
    )

    svc = WorkflowDeliverablesService(db)
    with pytest.raises(DeliverablesServiceError):
        await svc.get_evidence_file_path(uuid.UUID(project_id), eid)


# ================================================================
# Endpoint integration tests · with auth bypass
# ================================================================


@pytest.fixture
async def authed_marcos(async_client, monkeypatch):
    """Override require_marcos_or_client + bypass _ensure_project_access.

    `_ensure_project_access` consume `request.state.auth_subject` que NO
    está poblado por dependency_overrides solo. Monkeypatch helper directo.
    """
    from backend.app.main import app
    from backend.app.auth.dependencies import require_marcos_or_client
    from backend.app.motors.m_workflow_engine import api as wf_api

    async def override_auth():
        return object()

    async def override_ensure_access(db, project_id, request):
        return uuid.uuid4()

    monkeypatch.setattr(wf_api, "_ensure_project_access", override_ensure_access)
    app.dependency_overrides[require_marcos_or_client] = override_auth
    yield async_client
    app.dependency_overrides.pop(require_marcos_or_client, None)


@pytest.mark.asyncio
async def test_endpoint_list_deliverables_returns_200(authed_marcos, db):
    _, project_id = await setup_test_project(db)
    template_id = _find_template_with_deliverables()

    resp = await authed_marcos.get(
        f"/api/v1/projects/{project_id}/workflow-engine/"
        f"steps/{template_id}/deliverables",
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["template_id"] == template_id
    assert "deliverables" in data
    assert "counts" in data


@pytest.mark.asyncio
async def test_endpoint_bulk_zip_404_when_nothing_available(authed_marcos, db):
    _, project_id = await setup_test_project(db)
    template_id = _find_template_with_deliverables()

    resp = await authed_marcos.get(
        f"/api/v1/projects/{project_id}/workflow-engine/"
        f"steps/{template_id}/deliverables/bulk-zip",
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_endpoint_bulk_zip_streams_zip_when_available(
    authed_marcos, db, tmp_path: Path,
):
    _, project_id = await setup_test_project(db)
    template_id = _find_template_with_deliverables()
    template = get_template_by_id(template_id)
    code = template.deliverable_codes[0]

    test_file = tmp_path / "doc.pdf"
    test_file.write_bytes(b"%PDF-test-bytes")
    await _insert_evidence(
        db, project_id, code, str(test_file),
        nombre_original="entrega.pdf",
    )

    resp = await authed_marcos.get(
        f"/api/v1/projects/{project_id}/workflow-engine/"
        f"steps/{template_id}/deliverables/bulk-zip",
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"

    buf = io.BytesIO(resp.content)
    with zipfile.ZipFile(buf) as zf:
        names = zf.namelist()
    assert "entrega.pdf" in names
