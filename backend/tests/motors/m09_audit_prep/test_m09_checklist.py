"""Tests M9-A: checklist pre-audit + cross-validation + cleanup + API."""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text as sa_text

from backend.app.models.documents import Document, Evidence
from backend.app.models.ens import DdaEntry, EnsMeasure
from backend.app.motors.m08_verification.models import (
    VerificationFinding, VerificationRun,
)
from backend.app.motors.m09_audit_prep import checklist_service, cleanup_service
from backend.tests.conftest import _admin_setup, setup_test_project

BASE = "/api/v1/audit-prep"


# ================== Helpers ==================

async def _create_document(
    db, project_id: str, template_codigo: str,
    nombre: str = None,
    estado: str = "aprobado",
    aprobado_por: str | None = "marcos",
    fecha_aprobacion: date | None = None,
    signature: str | None = "ed25519:stub",
    tipo: str = "INTERNO",
) -> Document:
    d = Document(
        project_id=uuid.UUID(project_id),
        template_codigo=template_codigo,
        nombre=nombre or f"Doc {template_codigo}",
        estado=estado,
        aprobado_por=aprobado_por,
        fecha_aprobacion=fecha_aprobacion or date.today(),
        signature_ed25519=signature,
        tipo=tipo,
    )
    async with _admin_setup(db):
        db.add(d)
        await db.flush()
    return d


async def _get_or_create_ens_measure(db, codigo: str) -> uuid.UUID:
    r = await db.execute(
        select(EnsMeasure).where(EnsMeasure.codigo == codigo)
    )
    m = r.scalar_one_or_none()
    if m is not None:
        return m.id
    async with _admin_setup(db):
        m = EnsMeasure(
            codigo=codigo, nombre=f"Medida {codigo}", marco="anexo_ii",
        )
        db.add(m)
        await db.flush()
    return m.id


async def _create_dda_entry(
    db, project_id: str, measure_code: str,
    aplicabilidad: str = "aplica",
    estado_implementacion: str = "implantado",
) -> DdaEntry:
    m_id = await _get_or_create_ens_measure(db, measure_code)
    entry = DdaEntry(
        project_id=uuid.UUID(project_id),
        measure_id=m_id,
        aplicabilidad=aplicabilidad,
        estado_implementacion=estado_implementacion,
    )
    async with _admin_setup(db):
        db.add(entry)
        await db.flush()
    return entry


async def _create_evidence(
    db, project_id: str, measure_code: str,
    vigente: bool = True,
    fecha_caducidad: date | None = None,
    tipo: str = "evidencia_control",
) -> Evidence:
    m_id = await _get_or_create_ens_measure(db, measure_code)
    ev = Evidence(
        project_id=uuid.UUID(project_id),
        measure_id=m_id,
        measure_code=measure_code,
        tipo=tipo,
        vigente=vigente,
        fecha_evidencia=date.today(),
        fecha_caducidad=fecha_caducidad or (date.today() + timedelta(days=180)),
        hash_sha256="a" * 64,
    )
    async with _admin_setup(db):
        db.add(ev)
        await db.flush()
    return ev


async def _create_pentest_finding(
    db, project_id: str,
    measure_codes: list[str],
    severidad: str = "high",
    confidence: str = "confirmed",
):
    """Crea un VerificationRun + VerificationFinding (M8 v5.1) para pruebas.

    Mapea:
    - ``severidad`` -> ``severity``
    - ``confidence='confirmed'`` -> ``zfp_gate5_classification``, ``confidence_score=0.95``
    - ``measure_codes`` -> ``ens_measures`` + ``ens_primary_measure``
    """
    score = 0.95 if confidence == "confirmed" else (
        0.80 if confidence == "probable" else 0.60
    )
    project_uuid = uuid.UUID(project_id)
    async with _admin_setup(db):
        run = VerificationRun(
            project_id=project_uuid,
            category="BASICO",
            mode="internal",
            status="completed",
            scope_jsonb={"targets": ["test.example.es"], "web_apps": [], "exclusions": []},
            tools_used=["nuclei"],
            completed_at=datetime.now(timezone.utc),
            total_findings=1,
            confirmed_findings=1 if confidence == "confirmed" else 0,
        )
        db.add(run)
        await db.flush()
        vf = VerificationFinding(
            project_id=project_uuid,
            run_id=run.id,
            finding_hash=f"test_{uuid.uuid4().hex[:16]}",
            title=f"Test pentest finding {severidad}",
            description="Finding sintetico creado por fixture de test",
            severity=severidad,
            affected_host="test.example.es",
            tool_sources=["nuclei"],
            raw_outputs=[{"tool": "nuclei", "excerpt": "test"}],
            confidence_score=score,
            zfp_gate1_dedup=True,
            zfp_gate2_fp_filter=True,
            zfp_gate3_cross_tool=1,
            zfp_gate4_retest="not_applicable",
            zfp_gate5_classification=confidence,
            ens_measures=[
                {"measure": c, "title": f"Medida {c}", "method": "rule"}
                for c in measure_codes
            ],
            ens_primary_measure=measure_codes[0] if measure_codes else None,
            remediation_summary="Aplicar parche del fabricante",
            status="open",
        )
        db.add(vf)
        await db.flush()
    return vf


# ================== Deliverables ==================

class TestDeliverables:
    @pytest.mark.asyncio
    async def test_empty_project_all_missing(self, async_client, db):
        _, project_id = await setup_test_project(db)
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"categoria": "BASICA"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        deliv = body["checklist_results"]["entregables"]
        # El catalogo BASICA tiene 41 entregables post-Paso 4 (catalogo
        # completo segun spec §2.15). Antes eran 9 minimos.
        assert deliv["total"] >= 9
        assert deliv["present"] == 0
        assert "E-012" in deliv["missing"]
        assert "E-040" in deliv["missing"]
        assert "E-050" in deliv["missing"]

    @pytest.mark.asyncio
    async def test_some_present(self, async_client, db):
        _, project_id = await setup_test_project(db)
        await _create_document(db, project_id, "E-012")
        await _create_document(db, project_id, "E-040")
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"categoria": "BASICA"},
        )
        deliv = r.json()["checklist_results"]["entregables"]
        assert deliv["present"] == 2
        assert "E-012" not in deliv["missing"]

    @pytest.mark.asyncio
    async def test_categoria_media_requires_more(self, async_client, db):
        _, project_id = await setup_test_project(db)
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"categoria": "MEDIA"},
        )
        deliv = r.json()["checklist_results"]["entregables"]
        assert deliv["total"] > 9  # MEDIA tiene mas
        assert "E-400" in deliv["missing"]
        assert "E-702" in deliv["missing"]

    @pytest.mark.asyncio
    async def test_invalid_categoria(self, async_client, db):
        _, project_id = await setup_test_project(db)
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"categoria": "Z"},
        )
        assert r.status_code == 422


# ================== Evidence freshness ==================

class TestEvidenceFreshness:
    @pytest.mark.asyncio
    async def test_evidence_vigente(self, async_client, db):
        _, project_id = await setup_test_project(db)
        await _create_dda_entry(db, project_id, "op.acc.5", "aplica", "implantado")
        await _create_evidence(db, project_id, "op.acc.5")
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"categoria": "BASICA"},
        )
        evid = r.json()["checklist_results"]["evidencias"]
        assert evid["vigentes"] >= 1
        assert evid["caducadas"] == 0

    @pytest.mark.asyncio
    async def test_evidence_caducada(self, async_client, db):
        _, project_id = await setup_test_project(db)
        await _create_dda_entry(db, project_id, "op.acc.5", "aplica", "implantado")
        await _create_evidence(
            db, project_id, "op.acc.5",
            fecha_caducidad=date.today() - timedelta(days=30),
        )
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"categoria": "BASICA"},
        )
        evid = r.json()["checklist_results"]["evidencias"]
        assert evid["caducadas"] >= 1

    @pytest.mark.asyncio
    async def test_evidence_proxima_caducar_30d(self, async_client, db):
        _, project_id = await setup_test_project(db)
        await _create_dda_entry(db, project_id, "mp.com.2", "aplica", "implantado")
        await _create_evidence(
            db, project_id, "mp.com.2",
            fecha_caducidad=date.today() + timedelta(days=15),
        )
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"categoria": "BASICA"},
        )
        evid = r.json()["checklist_results"]["evidencias"]
        assert evid["proximas_caducar"] >= 1

    @pytest.mark.asyncio
    async def test_evidence_faltante(self, async_client, db):
        _, project_id = await setup_test_project(db)
        await _create_dda_entry(db, project_id, "op.acc.6", "aplica", "implantado")
        # NO creamos evidencia
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"categoria": "BASICA"},
        )
        evid = r.json()["checklist_results"]["evidencias"]
        assert evid["faltantes"] >= 1

    @pytest.mark.asyncio
    async def test_no_aplica_no_requiere_evidencia(self, async_client, db):
        _, project_id = await setup_test_project(db)
        await _create_dda_entry(
            db, project_id, "mp.info.3", "no_aplica", "no_aplica",
        )
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"categoria": "BASICA"},
        )
        evid = r.json()["checklist_results"]["evidencias"]
        # no_aplica no cuenta en total
        assert evid["faltantes"] == 0


# ================== Cross-validation ==================

class TestCrossValidation:
    @pytest.mark.asyncio
    async def test_dda_implantado_sin_evidencia_contradiccion(
        self, async_client, db,
    ):
        _, project_id = await setup_test_project(db)
        await _create_dda_entry(
            db, project_id, "op.acc.5", "aplica", "implantado",
        )
        # NO creamos evidencia
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"categoria": "BASICA"},
        )
        body = r.json()
        contras = body["checklist_results"]["contradicciones"]
        assert len(contras) >= 1
        assert any(c["medida"] == "op.acc.5" for c in contras)
        assert any(c["severidad"] == "error" for c in contras)

    @pytest.mark.asyncio
    async def test_dda_implantado_con_evidencia_ok(self, async_client, db):
        _, project_id = await setup_test_project(db)
        await _create_dda_entry(
            db, project_id, "op.acc.5", "aplica", "implantado",
        )
        await _create_evidence(db, project_id, "op.acc.5")
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"categoria": "BASICA"},
        )
        contras = r.json()["checklist_results"]["contradicciones"]
        # op.acc.5 NO deberia aparecer como contradiccion
        assert not any(c["medida"] == "op.acc.5" for c in contras)

    @pytest.mark.asyncio
    async def test_dda_en_proceso_sin_evidencia_warning(
        self, async_client, db,
    ):
        _, project_id = await setup_test_project(db)
        await _create_dda_entry(
            db, project_id, "mp.sw.1", "aplica", "en_proceso",
        )
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"categoria": "BASICA"},
        )
        contras = r.json()["checklist_results"]["contradicciones"]
        matches = [c for c in contras if c["medida"] == "mp.sw.1"]
        assert matches
        assert matches[0]["severidad"] == "warning"

    @pytest.mark.asyncio
    async def test_pentest_finding_contradice_dda_implantado(
        self, async_client, db,
    ):
        _, project_id = await setup_test_project(db)
        await _create_dda_entry(
            db, project_id, "mp.sw.2", "aplica", "implantado",
        )
        await _create_evidence(db, project_id, "mp.sw.2")
        # Pero pentest encuentra un finding high confirmado
        await _create_pentest_finding(
            db, project_id, ["mp.sw.2"],
            severidad="high", confidence="confirmed",
        )
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"categoria": "BASICA"},
        )
        contras = r.json()["checklist_results"]["contradicciones"]
        # Debe haber contradiccion por pentest
        pt_contras = [
            c for c in contras
            if c.get("evidencia_estado") == "pentest_high_finding"
        ]
        assert len(pt_contras) >= 1


# ================== Readiness score ==================

class TestReadinessScore:
    def test_score_100_all_ok(self):
        results = {
            "entregables": {"total": 9, "present": 9, "missing": []},
            "evidencias": {"total": 10, "vigentes": 10},
            "contradicciones": [],
            "firmas": {"total": 5, "firmadas": 5},
            "registros_operativos": {"ok": True, "meses_cubiertos": 6, "meses_requeridos": 6},
        }
        assert checklist_service.calculate_readiness_score(results) == 100

    def test_score_0_nothing_present(self):
        results = {
            "entregables": {"total": 9, "present": 0, "missing": []},
            "evidencias": {"total": 10, "vigentes": 0},
            "contradicciones": [{"severidad": "error"}],
            "firmas": {"total": 5, "firmadas": 0},
            "registros_operativos": {"ok": False, "meses_cubiertos": 0, "meses_requeridos": 6},
        }
        assert checklist_service.calculate_readiness_score(results) == 0

    def test_score_penalizes_critical_contradictions(self):
        results = {
            "entregables": {"total": 9, "present": 9},
            "evidencias": {"total": 10, "vigentes": 10},
            "contradicciones": [{"severidad": "error"}],
            "firmas": {"total": 5, "firmadas": 5},
            "registros_operativos": {"ok": True, "meses_cubiertos": 6, "meses_requeridos": 6},
        }
        # Sin el +20 de "sin contradicciones críticas"
        assert checklist_service.calculate_readiness_score(results) == 80

    def test_score_partial_deliverables(self):
        results = {
            "entregables": {"total": 10, "present": 5},  # 50% -> 15 puntos
            "evidencias": {"total": 10, "vigentes": 10},  # 30
            "contradicciones": [],  # 20
            "firmas": {"total": 5, "firmadas": 5},  # 10
            "registros_operativos": {"ok": True, "meses_cubiertos": 6, "meses_requeridos": 6},  # 10
        }
        assert checklist_service.calculate_readiness_score(results) == 85


# ================== Cleanup ==================

class TestCleanup:
    @pytest.mark.asyncio
    async def test_cleanup_detects_draft(self, async_client, db):
        _, project_id = await setup_test_project(db)
        await _create_document(
            db, project_id, "E-012",
            estado="borrador", aprobado_por=None,
        )
        # Crear run + ejecutar cleanup
        async with _admin_setup(db):
            run = await checklist_service.create_run(
                db, uuid.UUID(project_id), "BASICA",
            )
            items = await cleanup_service.run_cleanup(db, run)
        codes = {i.categoria_check for i in items}
        assert "cleanup_borrador" in codes

    @pytest.mark.asyncio
    async def test_cleanup_detects_duplicate(self, async_client, db):
        _, project_id = await setup_test_project(db)
        await _create_document(db, project_id, "E-012", nombre="v1")
        await _create_document(db, project_id, "E-012", nombre="v2")
        async with _admin_setup(db):
            run = await checklist_service.create_run(
                db, uuid.UUID(project_id), "BASICA",
            )
            items = await cleanup_service.run_cleanup(db, run)
        codes = {i.categoria_check for i in items}
        assert "cleanup_duplicado" in codes

    @pytest.mark.asyncio
    async def test_cleanup_detects_future_date(self, async_client, db):
        _, project_id = await setup_test_project(db)
        await _create_document(
            db, project_id, "E-040",
            fecha_aprobacion=date.today() + timedelta(days=30),
        )
        async with _admin_setup(db):
            run = await checklist_service.create_run(
                db, uuid.UUID(project_id), "BASICA",
            )
            items = await cleanup_service.run_cleanup(db, run)
        codes = {i.categoria_check for i in items}
        assert "cleanup_fecha" in codes

    @pytest.mark.asyncio
    async def test_cleanup_all_ok(self, async_client, db):
        _, project_id = await setup_test_project(db)
        await _create_document(
            db, project_id, "E-012",
            estado="aprobado", aprobado_por="marcos",
        )
        async with _admin_setup(db):
            run = await checklist_service.create_run(
                db, uuid.UUID(project_id), "BASICA",
            )
            items = await cleanup_service.run_cleanup(db, run)
        # Con un documento aprobado unique no debe haber items
        codes = {i.categoria_check for i in items}
        assert "cleanup_borrador" not in codes
        assert "cleanup_duplicado" not in codes


# ================== API ==================

class TestAPI:
    @pytest.mark.asyncio
    async def test_api_run_and_summary(self, async_client, db):
        _, project_id = await setup_test_project(db)
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"categoria": "BASICA"},
        )
        run_id = r.json()["id"]
        r2 = await async_client.get(
            f"{BASE}/projects/{project_id}/runs/{run_id}/summary",
        )
        assert r2.status_code == 200
        assert "readiness_score" in r2.json()
        assert r2.json()["interpretation"] in {
            "listo_auditoria", "ajustes_menores",
            "trabajo_significativo", "no_presentar",
        }

    @pytest.mark.asyncio
    async def test_api_list_items_filter(self, async_client, db):
        _, project_id = await setup_test_project(db)
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"categoria": "BASICA"},
        )
        run_id = r.json()["id"]
        # BASICA sin nada -> todos los deliverables son missing
        r2 = await async_client.get(
            f"{BASE}/projects/{project_id}/runs/{run_id}/items?estado=missing",
        )
        items = r2.json()
        # Catalogo BASICA expandido post-Paso 4: todos los entregables
        # aparecen como missing cuando el proyecto esta vacio.
        assert len(items) >= 9
        descs = " ".join(it.get("descripcion", "") for it in items)
        assert "E-012" in descs
        assert "E-040" in descs
        assert "E-050" in descs

    @pytest.mark.asyncio
    async def test_api_resolve_item(self, async_client, db):
        _, project_id = await setup_test_project(db)
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"categoria": "BASICA"},
        )
        run_id = r.json()["id"]
        items = (await async_client.get(
            f"{BASE}/projects/{project_id}/runs/{run_id}/items"
        )).json()
        item_id = items[0]["id"]
        r3 = await async_client.patch(
            f"{BASE}/projects/{project_id}/runs/{run_id}/items/{item_id}/resolve",
            json={"resuelto_por": "marcos"},
        )
        assert r3.status_code == 200
        assert r3.json()["resuelto"] is True
        assert r3.json()["resuelto_por"] == "marcos"

    @pytest.mark.asyncio
    async def test_api_contradictions_endpoint(self, async_client, db):
        _, project_id = await setup_test_project(db)
        await _create_dda_entry(
            db, project_id, "op.acc.5", "aplica", "implantado",
        )
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"categoria": "BASICA"},
        )
        run_id = r.json()["id"]
        r2 = await async_client.get(
            f"{BASE}/projects/{project_id}/runs/{run_id}/contradictions",
        )
        assert r2.status_code == 200
        assert len(r2.json()) >= 1

    @pytest.mark.asyncio
    async def test_api_readiness_quick(self, async_client, db):
        _, project_id = await setup_test_project(db)
        r = await async_client.get(
            f"{BASE}/projects/{project_id}/readiness?categoria=BASICA",
        )
        assert r.status_code == 200
        body = r.json()
        assert "readiness_score" in body
        assert body["categoria"] == "BASICA"

    @pytest.mark.asyncio
    async def test_api_cleanup(self, async_client, db):
        _, project_id = await setup_test_project(db)
        await _create_document(
            db, project_id, "E-012",
            estado="borrador", aprobado_por=None,
        )
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"categoria": "BASICA"},
        )
        run_id = r.json()["id"]
        r2 = await async_client.post(
            f"{BASE}/projects/{project_id}/runs/{run_id}/cleanup",
        )
        assert r2.status_code == 200
        assert r2.json()["items_created"] >= 1

    @pytest.mark.asyncio
    async def test_api_soft_delete_run(self, async_client, db):
        _, project_id = await setup_test_project(db)
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"categoria": "BASICA"},
        )
        run_id = r.json()["id"]
        d = await async_client.delete(
            f"{BASE}/projects/{project_id}/runs/{run_id}"
        )
        assert d.status_code == 200
        gone = await async_client.get(
            f"{BASE}/projects/{project_id}/runs/{run_id}"
        )
        assert gone.status_code == 404
