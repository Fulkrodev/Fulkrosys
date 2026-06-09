"""Tests del service core Motor 6 -- Document Factory.

Pattern consistent with M4 and M19 test_service.py.
"""
import pytest
from uuid import uuid4
from pathlib import Path

from sqlalchemy import text

from backend.app.database import set_tenant_context
from backend.app.models.document_factory import Template
from backend.app.motors.m06_document_factory.service import DocumentFactoryService
from backend.app.motors.m06_document_factory.exceptions import (
    TemplateNotFoundError,
    TemplateInactiveError,
    DocumentNotFoundError,
)
from backend.tests.conftest import setup_test_project, _admin_setup


# ================================================================
# HELPERS
# ================================================================

async def _setup_doc_env(db):
    """Create project + set RLS. Returns (svc, project_id)."""
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(db, client_id=client_id, project_id=project_id)
    svc = DocumentFactoryService(db)
    return svc, project_id


async def _sync_catalog(svc):
    """Sync catalog templates to DB. Returns summary."""
    return await svc.load_template_metadata_from_catalog()


def _full_policy_context() -> dict:
    """Full context satisfying all required vars for policy templates."""
    return {
        "cliente": {
            "razon_social": "Test Corp",
            "nif": "B12345678",
            "organo_aprobador_politicas": "Comite de Seguridad",
            "domicilio_social": "Calle Test 1, Madrid",
            "persona_contacto": {"nombre": "Juan Perez", "cargo": "CTO"},
        },
        "proyecto": {
            "fecha_aprobacion_inicial": "2026-01-01",
            "version_actual": "1.0",
            "codigo_documento_base": "E-100",
        },
        "responsables": {
            "responsable_seguridad": {"nombre": "Ana Garcia", "cargo": "CISO"},
        },
        "marcos": {"nif": "12345678A"},
        "propuesta": {"fecha_emision": "2026-01-01"},
        "contrato": {"fecha_firma": "2026-01-01", "honorarios_eur": "5000"},
    }


async def _create_template_directly(db, codigo="T-TEST", **overrides):
    """Create a template directly in DB for unit testing."""
    defaults = dict(
        codigo=codigo,
        nombre=f"Test Template {codigo}",
        categoria="politica",
        familia_ens="org",
        aplica_desde="basica",
        version_actual="1.0",
        is_active=True,
    )
    defaults.update(overrides)
    tpl = Template(**defaults)
    db.add(tpl)
    await db.flush()
    return tpl


# ================================================================
# CATALOG SYNC
# ================================================================

class TestCatalogSync:

    @pytest.mark.asyncio
    async def test_sync_catalog_creates_templates(self, db):
        svc, _ = await _setup_doc_env(db)
        result = await _sync_catalog(svc)
        total = result["created"] + result["updated"]
        assert total >= 60
        assert result["catalog_version"] == "1.0"

    @pytest.mark.asyncio
    async def test_sync_catalog_idempotent(self, db):
        svc, _ = await _setup_doc_env(db)
        r1 = await _sync_catalog(svc)
        r2 = await _sync_catalog(svc)
        assert r2["created"] == 0
        total_r1 = r1["created"] + r1["updated"]
        assert r2["updated"] == total_r1

    @pytest.mark.asyncio
    async def test_sync_catalog_updates_existing(self, db):
        svc, _ = await _setup_doc_env(db)
        # Create first
        await _sync_catalog(svc)
        # Sync again — all should be updates
        r2 = await _sync_catalog(svc)
        assert r2["updated"] > 0
        assert r2["created"] == 0


# ================================================================
# TEMPLATE READ
# ================================================================

class TestTemplateRead:

    @pytest.mark.asyncio
    async def test_get_template_by_codigo(self, db):
        svc, _ = await _setup_doc_env(db)
        await _sync_catalog(svc)
        tpl = await svc.get_template_by_codigo("E-100")
        assert tpl.codigo == "E-100"
        assert tpl.categoria == "politica"

    @pytest.mark.asyncio
    async def test_get_template_not_found_raises(self, db):
        svc, _ = await _setup_doc_env(db)
        with pytest.raises(TemplateNotFoundError):
            await svc.get_template_by_codigo("FAKE-999")

    @pytest.mark.asyncio
    async def test_list_templates_filter_by_categoria(self, db):
        svc, _ = await _setup_doc_env(db)
        await _sync_catalog(svc)
        pols = await svc.list_templates(categoria="politica")
        assert len(pols) >= 20
        for t in pols:
            assert t.categoria == "politica"

    @pytest.mark.asyncio
    async def test_list_templates_filter_by_familia(self, db):
        svc, _ = await _setup_doc_env(db)
        await _sync_catalog(svc)
        orgs = await svc.list_templates(familia_ens="org")
        assert len(orgs) >= 1
        for t in orgs:
            assert t.familia_ens == "org"


# ================================================================
# DOCUMENT GENERATION
# ================================================================

class TestGenerate:

    @pytest.mark.asyncio
    async def test_generate_document_creates_docx(self, db):
        svc, pid = await _setup_doc_env(db)
        await _sync_catalog(svc)
        context = _full_policy_context()
        result = await svc.generate_document(
            project_id=pid,
            template_codigo="E-100",
            context=context,
            generate_pdf=False,
            sign=True,
            generated_by="Test",
        )
        assert result["template_codigo"] == "E-100"
        assert result["docx_path"] is not None
        assert Path(result["docx_path"]).exists()

    @pytest.mark.asyncio
    async def test_generate_document_creates_db_row(self, db):
        svc, pid = await _setup_doc_env(db)
        await _sync_catalog(svc)
        context = _full_policy_context()
        await svc.generate_document(pid, "E-100", context, generate_pdf=False, sign=False)
        docs = await svc.list_documents(pid)
        assert len(docs) >= 1

    @pytest.mark.asyncio
    async def test_generate_document_emits_audit_log(self, db):
        """F-14-03 (Ejecutable 8 Pasada 16): generate_document emite audit_log
        canónico 'document.generated' (Sub-atom 5.A · trazabilidad ENAC)."""
        svc, pid = await _setup_doc_env(db)
        await _sync_catalog(svc)
        ctx = _full_policy_context()
        res = await svc.generate_document(
            pid, "E-100", ctx, generate_pdf=False, sign=False,
        )
        async with _admin_setup(db):
            r = await db.execute(
                text(
                    "SELECT count(*) FROM audit_log "
                    "WHERE accion='document.generated' "
                    "AND registro_id=:rid AND project_id=:pid"
                ),
                {"rid": str(res["document_id"]), "pid": str(pid)},
            )
        assert r.scalar() == 1

    @pytest.mark.asyncio
    async def test_generate_document_persists_durable_minio_storage_path(self, db):
        """#31 (FRENTE B): el binario generado se sube a MinIO y el Document
        queda con storage_path canónico minio:// → descargable por
        cliente/admin/auditor sin depender del disco local efímero (que en
        prod desaparece al reiniciar el contenedor · causa del 503)."""
        from unittest.mock import patch
        svc, pid = await _setup_doc_env(db)
        await _sync_catalog(svc)
        ctx = _full_policy_context()
        with patch(
            "backend.app.core.storage.minio_client.put_object",
        ) as put_mock:
            res = await svc.generate_document(
                pid, "E-100", ctx, generate_pdf=False, sign=False,
            )
        assert put_mock.call_count == 1
        args = put_mock.call_args.args
        assert args[0] == "fulkro-documents"
        assert isinstance(args[2], (bytes, bytearray)) and len(args[2]) > 0
        assert res["storage_path"] is not None
        assert res["storage_path"].startswith("minio://fulkro-documents/")
        doc = await svc.get_document(res["document_id"])
        assert doc.storage_path == res["storage_path"]

    @pytest.mark.asyncio
    async def test_generate_document_minio_down_is_graceful(self, db):
        """#31: si MinIO no está disponible, la generación NO falla; storage_path
        queda None (degradación graceful · OPS-049 honest path)."""
        from unittest.mock import patch
        svc, pid = await _setup_doc_env(db)
        await _sync_catalog(svc)
        ctx = _full_policy_context()
        with patch(
            "backend.app.core.storage.minio_client.put_object",
            side_effect=RuntimeError("minio down"),
        ):
            res = await svc.generate_document(
                pid, "E-100", ctx, generate_pdf=False, sign=False,
            )
        assert res["document_id"] is not None
        assert res["storage_path"] is None

    @pytest.mark.asyncio
    async def test_generate_document_computes_hash(self, db):
        svc, pid = await _setup_doc_env(db)
        await _sync_catalog(svc)
        ctx = _full_policy_context()
        result = await svc.generate_document(pid, "E-100", ctx, generate_pdf=False, sign=False)
        assert result.get("rendered_hash") is not None
        assert len(result["rendered_hash"]) == 64

    @pytest.mark.asyncio
    async def test_generate_document_signs_when_true(self, db):
        svc, pid = await _setup_doc_env(db)
        await _sync_catalog(svc)
        ctx = _full_policy_context()
        result = await svc.generate_document(pid, "E-100", ctx, generate_pdf=False, sign=True)
        assert result.get("signature_ed25519") is not None

    @pytest.mark.asyncio
    async def test_generate_document_skips_signing_when_false(self, db):
        svc, pid = await _setup_doc_env(db)
        await _sync_catalog(svc)
        ctx = _full_policy_context()
        result = await svc.generate_document(pid, "E-100", ctx, generate_pdf=False, sign=False)
        assert result.get("signature_ed25519") is None

    @pytest.mark.asyncio
    async def test_generate_document_inactive_raises(self, db):
        svc, pid = await _setup_doc_env(db)
        tpl = await _create_template_directly(db, "INACTIVE-01", is_active=False, docx_path="/fake")
        with pytest.raises(TemplateInactiveError):
            await svc.generate_document(pid, "INACTIVE-01", {}, generate_pdf=False, sign=False)

    @pytest.mark.asyncio
    async def test_generate_document_unknown_raises(self, db):
        svc, pid = await _setup_doc_env(db)
        with pytest.raises(TemplateNotFoundError):
            await svc.generate_document(pid, "FAKE-999", {}, generate_pdf=False, sign=False)

    @pytest.mark.asyncio
    async def test_generate_document_context_snapshot_saved(self, db):
        svc, pid = await _setup_doc_env(db)
        await _sync_catalog(svc)
        ctx = _full_policy_context()
        await svc.generate_document(pid, "E-100", ctx, generate_pdf=False, sign=False)
        docs = await svc.list_documents(pid)
        assert len(docs) >= 1
        doc = docs[0]
        assert doc.context_snapshot is not None


# ================================================================
# DOCUMENT LIFECYCLE
# ================================================================

class TestDocumentLifecycle:

    @pytest.mark.asyncio
    async def test_list_documents_by_project(self, db):
        svc, pid = await _setup_doc_env(db)
        docs = await svc.list_documents(pid)
        assert docs == []

    @pytest.mark.asyncio
    async def test_get_document_not_found_raises(self, db):
        svc, _ = await _setup_doc_env(db)
        with pytest.raises(DocumentNotFoundError):
            await svc.get_document(uuid4())

    @pytest.mark.asyncio
    async def test_soft_delete_document(self, db):
        svc, pid = await _setup_doc_env(db)
        await _sync_catalog(svc)
        ctx = _full_policy_context()
        result = await svc.generate_document(pid, "E-100", ctx, generate_pdf=False, sign=False)
        doc_id = result["document_id"]
        await svc.soft_delete_document(doc_id)
        with pytest.raises(DocumentNotFoundError):
            await svc.get_document(doc_id)

    @pytest.mark.asyncio
    async def test_mark_as_delivered(self, db):
        svc, pid = await _setup_doc_env(db)
        await _sync_catalog(svc)
        ctx = _full_policy_context()
        result = await svc.generate_document(pid, "E-100", ctx, generate_pdf=False, sign=False)
        doc = await svc.mark_as_delivered(result["document_id"])
        assert doc.estado == "entregado"


# ================================================================
# DASHBOARD
# ================================================================

class TestDashboard:

    @pytest.mark.asyncio
    async def test_dashboard_empty_returns_zeros_no_404(self, db):
        """CRITICAL: Empty project returns dashboard with zeros, NOT 404."""
        svc, pid = await _setup_doc_env(db)
        dash = await svc.get_dashboard(pid)
        assert dash["total_documents"] == 0

    @pytest.mark.asyncio
    async def test_dashboard_counts_after_generate(self, db):
        svc, pid = await _setup_doc_env(db)
        await _sync_catalog(svc)
        ctx = _full_policy_context()
        await svc.generate_document(pid, "E-100", ctx, generate_pdf=False, sign=False)
        dash = await svc.get_dashboard(pid)
        assert dash["total_documents"] == 1


# ================================================================
# EDGE CASES (coverage)
# ================================================================

class TestEdgeCases:

    @pytest.mark.asyncio
    async def test_list_templates_filter_aplica_desde(self, db):
        svc, _ = await _setup_doc_env(db)
        await _sync_catalog(svc)
        basicas = await svc.list_templates(aplica_desde="basica")
        assert len(basicas) > 0
        for t in basicas:
            assert t.aplica_desde == "basica"

    @pytest.mark.asyncio
    async def test_list_templates_filter_is_active(self, db):
        svc, _ = await _setup_doc_env(db)
        await _sync_catalog(svc)
        active = await svc.list_templates(is_active=True)
        assert len(active) >= 60

    @pytest.mark.asyncio
    async def test_get_template_by_id_not_found(self, db):
        svc, _ = await _setup_doc_env(db)
        with pytest.raises(TemplateNotFoundError):
            await svc.get_template_by_id(uuid4())

    @pytest.mark.asyncio
    async def test_get_template_by_id_success(self, db):
        svc, _ = await _setup_doc_env(db)
        await _sync_catalog(svc)
        # Get E-100 by codigo, then by id
        tpl = await svc.get_template_by_codigo("E-100")
        found = await svc.get_template_by_id(tpl.id)
        assert found.codigo == "E-100"

    @pytest.mark.asyncio
    async def test_preview_render_detects_missing(self, db):
        svc, pid = await _setup_doc_env(db)
        await _sync_catalog(svc)
        result = await svc.preview_render("E-100", {})
        assert len(result["placeholders_missing"]) > 0
        assert result["preview_ok"] is False

    @pytest.mark.asyncio
    async def test_preview_render_all_present(self, db):
        svc, pid = await _setup_doc_env(db)
        await _sync_catalog(svc)
        ctx = _full_policy_context()
        result = await svc.preview_render("E-100", ctx)
        # All top-level keys present
        assert len(result["placeholders_provided"]) > 0

    @pytest.mark.asyncio
    async def test_list_documents_filter_by_estado(self, db):
        svc, pid = await _setup_doc_env(db)
        await _sync_catalog(svc)
        ctx = _full_policy_context()
        await svc.generate_document(pid, "E-100", ctx, generate_pdf=False, sign=False)
        # Filter by estado=generado
        docs = await svc.list_documents(pid, estado="generado")
        assert len(docs) >= 1
        for d in docs:
            assert d.estado == "generado"

    @pytest.mark.asyncio
    async def test_list_documents_filter_by_template_codigo(self, db):
        svc, pid = await _setup_doc_env(db)
        await _sync_catalog(svc)
        ctx = _full_policy_context()
        await svc.generate_document(pid, "E-100", ctx, generate_pdf=False, sign=False)
        docs = await svc.list_documents(pid, template_codigo="E-100")
        assert len(docs) >= 1

    @pytest.mark.asyncio
    async def test_generate_with_pdf(self, db):
        """Generate with PDF conversion enabled."""
        svc, pid = await _setup_doc_env(db)
        await _sync_catalog(svc)
        ctx = _full_policy_context()
        result = await svc.generate_document(pid, "E-100", ctx, generate_pdf=True, sign=False)
        # PDF may succeed (LibreOffice installed) or warn
        assert result["docx_path"] is not None
