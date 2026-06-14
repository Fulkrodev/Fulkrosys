"""Tests M9-B: dossier ZIP + matriz 99 + coaching + API."""
from __future__ import annotations

import io
import json
import uuid
import zipfile
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text as sa_text

from backend.app.models.documents import Document, Evidence
from backend.app.models.ens import DdaEntry, EnsMeasure
from backend.app.motors.m08_verification.models import (
    VerificationFinding, VerificationRun,
)
from backend.app.motors.m09_audit_prep import (
    coaching,
    dossier_generator,
    matriz_99,
)
from backend.tests.conftest import _admin_setup, setup_test_project

BASE = "/api/v1/audit-prep"


# ================== Helpers ==================

async def _create_document(
    db, project_id: str, template_codigo: str, nombre: str | None = None,
) -> Document:
    d = Document(
        project_id=uuid.UUID(project_id),
        template_codigo=template_codigo,
        nombre=nombre or f"Doc {template_codigo}",
        estado="aprobado",
        aprobado_por="marcos",
        fecha_aprobacion=date.today(),
        signature_ed25519="ed25519:stub",
        tipo="INTERNO",
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
    estado_implementacion: str = "implantada",
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
        fecha_caducidad=date.today() + timedelta(days=180),
        hash_sha256="a" * 64,
    )
    async with _admin_setup(db):
        db.add(ev)
        await db.flush()
    return ev


async def _create_pentest_finding(
    db, project_id: str, measure_codes: list[str],
    severidad: str = "high",
    title: str = "Test finding CVE-2024-X",
):
    """Crea un VerificationRun + VerificationFinding (M8 v5.1) para pruebas."""
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
            confirmed_findings=1,
        )
        db.add(run)
        await db.flush()
        vf = VerificationFinding(
            project_id=project_uuid,
            run_id=run.id,
            finding_hash=f"test_{uuid.uuid4().hex[:16]}",
            title=title,
            description="Finding sintetico creado por fixture de test",
            severity=severidad,
            affected_host="test.example.es",
            cve_id="CVE-2024-X",
            tool_sources=["nuclei"],
            raw_outputs=[{"tool": "nuclei", "excerpt": "test"}],
            confidence_score=0.95,
            zfp_gate1_dedup=True,
            zfp_gate2_fp_filter=True,
            zfp_gate3_cross_tool=1,
            zfp_gate4_retest="not_applicable",
            zfp_gate5_classification="confirmed",
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


async def _create_run(async_client, project_id: str, categoria: str = "BASICA"):
    r = await async_client.post(
        f"{BASE}/projects/{project_id}/runs",
        json={"categoria": categoria},
    )
    assert r.status_code == 200, f"status={r.status_code} body={r.text}"
    body = r.json()
    assert body is not None, f"empty body status={r.status_code}"
    assert "id" in body, f"body without id: {body}"
    return body["id"]


async def _set_tenant(db, project_id: str) -> None:
    """Activa tenant context en la sesion para leer con RLS."""
    from backend.app.database import set_tenant_context
    client_id = (await db.execute(
        sa_text("SELECT get_project_owner(:pid)"),
        {"pid": project_id},
    )).scalar()
    await set_tenant_context(
        db, client_id=client_id, project_id=uuid.UUID(project_id),
    )


# ================== Coaching ==================

class TestCoaching:
    def test_get_questions_direccion(self):
        qs = coaching.get_questions_by_role("direccion")
        assert len(qs) >= 5
        assert all("pregunta" in q and "medida" in q for q in qs)

    def test_get_questions_nonexistent_role(self):
        qs = coaching.get_questions_by_role("nonexistent")
        assert qs == []

    def test_get_all_roles(self):
        roles = coaching.get_all_roles()
        assert set(roles) == {
            "direccion", "responsable_seguridad",
            "administrador_sistemas", "dpo_legal",
        }

    def test_get_questions_by_measure_op_acc_5(self):
        qs = coaching.get_questions_by_measure("op.acc.5")
        assert len(qs) >= 1
        assert all(q["medida"] == "op.acc.5" for q in qs)
        # Debe venir con role incluido
        assert all("role" in q for q in qs)

    def test_coaching_pack_basica_excludes_dpo(self):
        pack = coaching.generate_coaching_pack("BASICA")
        assert "direccion" in pack["questions_by_role"]
        assert "dpo_legal" not in pack["questions_by_role"]
        assert pack["total_questions"] > 0

    def test_coaching_pack_media_includes_dpo(self):
        pack = coaching.generate_coaching_pack("MEDIA")
        assert "dpo_legal" in pack["questions_by_role"]


# ================== Matriz 99 ==================

class TestMatriz99:
    @pytest.mark.asyncio
    async def test_xlsx_bytes_returned(self, async_client, db):
        _, project_id = await setup_test_project(db)
        await _create_dda_entry(db, project_id, "op.acc.5")
        await _set_tenant(db, project_id)
        data = await matriz_99.generate_matriz_99(
            db, uuid.UUID(project_id), "BASICA",
        )
        assert isinstance(data, bytes)
        assert data[:2] == b"PK"

    @pytest.mark.asyncio
    async def test_matriz_99_data_has_rows(self, async_client, db):
        _, project_id = await setup_test_project(db)
        await _create_dda_entry(db, project_id, "op.acc.5")
        await _create_dda_entry(db, project_id, "mp.com.2")
        await _create_evidence(db, project_id, "op.acc.5")
        await _set_tenant(db, project_id)
        rows = await matriz_99.generate_matriz_99_data(
            db, uuid.UUID(project_id), "BASICA",
        )
        codes = {r["codigo"] for r in rows}
        assert "op.acc.5" in codes
        row_acc5 = next(r for r in rows if r["codigo"] == "op.acc.5")
        assert row_acc5["estado_dda"] == "implantada"
        assert row_acc5["vigente"] == "Sí"

    @pytest.mark.asyncio
    async def test_matriz_99_shows_pentest_finding(self, async_client, db):
        _, project_id = await setup_test_project(db)
        await _create_dda_entry(db, project_id, "mp.sw.1")
        await _create_pentest_finding(db, project_id, ["mp.sw.1"])
        await _set_tenant(db, project_id)
        rows = await matriz_99.generate_matriz_99_data(
            db, uuid.UUID(project_id), "BASICA",
        )
        sw1 = next(
            (r for r in rows if r["codigo"] == "mp.sw.1"), None,
        )
        if sw1 is None:
            pytest.skip("mp.sw.1 no aplica a BASICA por defecto")
        assert "CVE-2024-X" in sw1["finding_pentest"] or \
               "Test finding" in sw1["finding_pentest"]

    @pytest.mark.asyncio
    async def test_xlsx_has_header_row(self, async_client, db):
        from openpyxl import load_workbook
        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        data = await matriz_99.generate_matriz_99(
            db, uuid.UUID(project_id), "BASICA",
        )
        wb = load_workbook(io.BytesIO(data))
        ws = wb.active
        first_row = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
        assert "Código medida" in first_row
        assert "Estado DdA" in first_row

    @pytest.mark.asyncio
    async def test_matriz_99_rows_filter_by_categoria(self, async_client, db):
        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        rows_basica = await matriz_99.generate_matriz_99_data(
            db, uuid.UUID(project_id), "BASICA",
        )
        rows_alta = await matriz_99.generate_matriz_99_data(
            db, uuid.UUID(project_id), "ALTA",
        )
        assert len(rows_alta) >= len(rows_basica)


# ================== Dossier Generator ==================

class TestDossierGenerator:
    def test_dossier_structure_has_15_entries(self):
        # 15 tematicas (00-14 · +14_REMEDIACION ADR-055) + 99 = 16
        assert len(dossier_generator.DOSSIER_STRUCTURE) == 16

    def test_classify_folder_e012(self):
        assert dossier_generator.classify_folder("E-012") == "02_CATEGORIZACION"

    def test_classify_folder_e101_politica(self):
        assert dossier_generator.classify_folder("E-101") == "06_NORMATIVA"

    def test_classify_folder_e204_procedimiento(self):
        assert dossier_generator.classify_folder("E-204") == "07_PROCEDIMIENTOS"

    def test_classify_folder_e702_pentest(self):
        assert dossier_generator.classify_folder("E-702") == "13_INFORMES_TECNICOS"

    def test_classify_folder_none_fallback(self):
        assert (
            dossier_generator.classify_folder(None)
            == "08_REGISTROS_OPERACION"
        )

    @pytest.mark.asyncio
    async def test_generate_dossier_has_14_folders(self, async_client, db):
        _, project_id = await setup_test_project(db)
        run_id = await _create_run(async_client, project_id, "BASICA")
        await _set_tenant(db, project_id)
        data = await dossier_generator.generate_dossier(
            db, uuid.UUID(project_id), uuid.UUID(run_id), force=True,
        )
        z = zipfile.ZipFile(io.BytesIO(data))
        names = set(z.namelist())
        for folder in [
            "00_INDICE", "01_GOBIERNO", "02_CATEGORIZACION",
            "03_ANALISIS_RIESGOS", "04_DECLARACION_APLICABILIDAD",
            "05_PLAN_ADECUACION", "06_NORMATIVA", "07_PROCEDIMIENTOS",
            "08_REGISTROS_OPERACION", "09_EVIDENCIAS_POR_MEDIDA",
            "10_PLAN_CONTINUIDAD",
            "11_FORMACION", "12_PROVEEDORES", "13_INFORMES_TECNICOS",
            "14_REMEDIACION", "99_MATRIZ_CRUZADA",
        ]:
            assert any(n.startswith(folder + "/") for n in names), (
                f"falta carpeta: {folder}"
            )

    @pytest.mark.asyncio
    async def test_dossier_has_manifest_and_matriz(self, async_client, db):
        _, project_id = await setup_test_project(db)
        run_id = await _create_run(async_client, project_id, "BASICA")
        await _set_tenant(db, project_id)
        data = await dossier_generator.generate_dossier(
            db, uuid.UUID(project_id), uuid.UUID(run_id), force=True,
        )
        z = zipfile.ZipFile(io.BytesIO(data))
        names = set(z.namelist())
        assert "MANIFEST.json" in names
        assert "00_INDICE/indice_maestro.md" in names
        assert "00_INDICE/resumen_ejecutivo.md" in names
        assert "99_MATRIZ_CRUZADA/matriz_medidas_evidencias.xlsx" in names

        # MANIFEST con hashes
        manifest = json.loads(z.read("MANIFEST.json"))
        assert manifest["run_id"] == run_id
        assert "files" in manifest
        assert all("sha256" in f for f in manifest["files"])
        assert all(len(f["sha256"]) == 64 for f in manifest["files"])
        # Estructura debe referenciar las 16 carpetas (00-14 + 99)
        assert len(manifest["dossier_structure"]) == 16

    @pytest.mark.asyncio
    async def test_dossier_classifies_e012_to_categorizacion(
        self, async_client, db,
    ):
        _, project_id = await setup_test_project(db)
        await _create_document(db, project_id, "E-012", nombre="Acta categorizacion")
        run_id = await _create_run(async_client, project_id, "BASICA")
        await _set_tenant(db, project_id)
        data = await dossier_generator.generate_dossier(
            db, uuid.UUID(project_id), uuid.UUID(run_id), force=True,
        )
        z = zipfile.ZipFile(io.BytesIO(data))
        names = list(z.namelist())
        e012_files = [
            n for n in names
            if "02_CATEGORIZACION" in n and "E-012" in n
        ]
        assert len(e012_files) >= 1

    @pytest.mark.asyncio
    async def test_dossier_classifies_e101_to_normativa(
        self, async_client, db,
    ):
        _, project_id = await setup_test_project(db)
        await _create_document(
            db, project_id, "E-101", nombre="Politica accesos",
        )
        run_id = await _create_run(async_client, project_id, "BASICA")
        await _set_tenant(db, project_id)
        data = await dossier_generator.generate_dossier(
            db, uuid.UUID(project_id), uuid.UUID(run_id), force=True,
        )
        z = zipfile.ZipFile(io.BytesIO(data))
        names = list(z.namelist())
        e101_files = [
            n for n in names
            if "06_NORMATIVA" in n and "E-101" in n
        ]
        assert len(e101_files) >= 1

    @pytest.mark.asyncio
    async def test_executive_summary_has_readiness(
        self, async_client, db,
    ):
        _, project_id = await setup_test_project(db)
        run_id = await _create_run(async_client, project_id, "BASICA")
        await _set_tenant(db, project_id)
        data = await dossier_generator.generate_dossier(
            db, uuid.UUID(project_id), uuid.UUID(run_id), force=True,
        )
        z = zipfile.ZipFile(io.BytesIO(data))
        exec_md = z.read("00_INDICE/resumen_ejecutivo.md").decode("utf-8")
        assert "Readiness score" in exec_md
        assert "Categoria ENS" in exec_md


# ================== API ==================

class TestAPI:
    @pytest.mark.asyncio
    async def test_api_generate_dossier(self, async_client, db):
        _, project_id = await setup_test_project(db)
        run_id = await _create_run(async_client, project_id, "BASICA")
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs/{run_id}/generate-dossier?force=true",
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["size_bytes"] > 0
        assert body["estado"] == "dossier_generated"

    @pytest.mark.asyncio
    async def test_api_download_dossier(self, async_client, db):
        _, project_id = await setup_test_project(db)
        run_id = await _create_run(async_client, project_id, "BASICA")
        r = await async_client.get(
            f"{BASE}/projects/{project_id}/runs/{run_id}/dossier?force=true",
        )
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/zip"
        z = zipfile.ZipFile(io.BytesIO(r.content))
        assert "MANIFEST.json" in z.namelist()

    @pytest.mark.asyncio
    async def test_api_dossier_index(self, async_client, db):
        _, project_id = await setup_test_project(db)
        run_id = await _create_run(async_client, project_id, "BASICA")
        r = await async_client.get(
            f"{BASE}/projects/{project_id}/runs/{run_id}/dossier/index",
        )
        assert r.status_code == 200
        body = r.json()
        assert len(body["structure"]) == 16

    @pytest.mark.asyncio
    async def test_api_download_matriz_99(self, async_client, db):
        _, project_id = await setup_test_project(db)
        run_id = await _create_run(async_client, project_id, "BASICA")
        r = await async_client.get(
            f"{BASE}/projects/{project_id}/runs/{run_id}/matriz-99",
        )
        assert r.status_code == 200
        assert "spreadsheetml" in r.headers.get("content-type", "")
        assert r.content[:2] == b"PK"

    @pytest.mark.asyncio
    async def test_api_coaching_roles(self, async_client, db):
        r = await async_client.get(f"{BASE}/coaching/roles")
        assert r.status_code == 200
        assert "direccion" in r.json()["roles"]

    @pytest.mark.asyncio
    async def test_api_coaching_questions_by_role(self, async_client, db):
        r = await async_client.get(
            f"{BASE}/coaching/questions/responsable_seguridad",
        )
        assert r.status_code == 200
        assert r.json()["total"] >= 5

    @pytest.mark.asyncio
    async def test_api_coaching_role_not_found(self, async_client, db):
        r = await async_client.get(f"{BASE}/coaching/questions/nonexistent")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_api_coaching_questions_by_measure(self, async_client, db):
        r = await async_client.get(
            f"{BASE}/coaching/questions/by-measure/op.acc.5",
        )
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    @pytest.mark.asyncio
    async def test_api_coaching_pack(self, async_client, db):
        _, project_id = await setup_test_project(db)
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/coaching-pack",
            json={"categoria": "MEDIA"},
        )
        assert r.status_code == 200
        assert r.json()["total_questions"] > 0

    @pytest.mark.asyncio
    async def test_api_m09_summary(self, async_client, db):
        _, project_id = await setup_test_project(db)
        r = await async_client.get(f"{BASE}/projects/{project_id}/summary")
        assert r.status_code == 200
        assert r.json()["has_runs"] is False

    @pytest.mark.asyncio
    async def test_api_m09_summary_after_run(self, async_client, db):
        _, project_id = await setup_test_project(db)
        await _create_run(async_client, project_id, "BASICA")
        r = await async_client.get(f"{BASE}/projects/{project_id}/summary")
        body = r.json()
        assert body["has_runs"] is True
        assert body["total_runs"] == 1


# ════════════════════════════════════════════════════════════════════
# M27 Declaración Conformidad wire #7 (Future-1.E.1.dossier-pack.C-hybrid)
# ════════════════════════════════════════════════════════════════════


class TestM27ConformityDeclarationWire:
    """Wire M9 dossier ↔ M27 process_basic_declaration (Path Hybrid Phase C)."""

    def test_deliverable_e041_classified_to_gobierno(self):
        assert (
            dossier_generator.classify_folder("E-041") == "01_GOBIERNO"
        )

    def test_deliverable_e042_classified_to_gobierno(self):
        assert (
            dossier_generator.classify_folder("E-042") == "01_GOBIERNO"
        )

    def test_deliverable_e043_classified_to_gobierno(self):
        assert (
            dossier_generator.classify_folder("E-043") == "01_GOBIERNO"
        )

    def test_deliverable_e701_classified_to_informes(self):
        assert (
            dossier_generator.classify_folder("E-701")
            == "13_INFORMES_TECNICOS"
        )

    @pytest.mark.asyncio
    async def test_collect_conformity_declarations_empty(
        self, async_client, db,
    ):
        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        decls = await dossier_generator._collect_conformity_declarations(
            db, uuid.UUID(project_id),
        )
        assert decls == []

    @pytest.mark.asyncio
    async def test_collect_conformity_declarations_with_declaration(
        self, async_client, db,
    ):
        from backend.app.motors.m27_conformity.conformity_service_paso5 import (
            ConformityServicePaso5,
        )

        _, project_id = await setup_test_project(db)
        pid = uuid.UUID(project_id)
        # Set categoria BASICA + tenant for M27 route init
        async with _admin_setup(db):
            await db.execute(sa_text(
                "UPDATE projects SET categoria_objetivo = 'BASICA' "
                "WHERE id = :pid"
            ), {"pid": project_id})
        await _set_tenant(db, project_id)
        svc = ConformityServicePaso5()
        await svc.initialize_conformity_route(db, pid)
        # #41 (FRENTE D): el cierre BÁSICA exige la autoevaluación 808.
        rep_id = uuid.uuid4()
        await db.execute(sa_text(
            "INSERT INTO documents (id, project_id, nombre, template_codigo, "
            "created_at, updated_at) VALUES (:id, :pid, "
            "'E-808C Autoevaluación', 'E-808C', now(), now())"
        ), {"id": str(rep_id), "pid": str(pid)})
        await svc.process_basic_declaration(
            db, pid,
            responsible_person_name="RSEG Test",
            responsible_person_email="rseg@test.es",
            published_url="https://test.es/ens-declaration",
            self_assessment_report_id=rep_id,
        )

        decls = await dossier_generator._collect_conformity_declarations(
            db, pid,
        )
        assert len(decls) == 1
        d = decls[0]
        assert d["template_codigo"] == "E-041"
        assert d["responsible_person_name"] == "RSEG Test"
        assert d["responsible_person_email"] == "rseg@test.es"
        assert d["published_evidence_url"] == (
            "https://test.es/ens-declaration"
        )
        assert d["signed_hash"] is not None
        assert len(d["signed_hash"]) == 64
        assert d["status"] == "signed"
        assert d["carpeta_destino"] == "01_GOBIERNO"
        assert d["submission"] is not None
        assert d["submission"]["submission_type"] == "basic_declaration"
        assert d["submission"]["external_system"] == "webpage_cliente"

    @pytest.mark.asyncio
    async def test_dossier_includes_declaration_artifacts(
        self, async_client, db,
    ):
        from backend.app.motors.m27_conformity.conformity_service_paso5 import (
            ConformityServicePaso5,
        )

        _, project_id = await setup_test_project(db)
        pid = uuid.UUID(project_id)
        async with _admin_setup(db):
            await db.execute(sa_text(
                "UPDATE projects SET categoria_objetivo = 'BASICA' "
                "WHERE id = :pid"
            ), {"pid": project_id})
        await _set_tenant(db, project_id)
        svc = ConformityServicePaso5()
        await svc.initialize_conformity_route(db, pid)
        # #41 (FRENTE D): el cierre BÁSICA exige la autoevaluación 808.
        rep_id = uuid.uuid4()
        await db.execute(sa_text(
            "INSERT INTO documents (id, project_id, nombre, template_codigo, "
            "created_at, updated_at) VALUES (:id, :pid, "
            "'E-808C Autoevaluación', 'E-808C', now(), now())"
        ), {"id": str(rep_id), "pid": str(pid)})
        await svc.process_basic_declaration(
            db, pid,
            responsible_person_name="RSEG Pilot",
            responsible_person_email="rseg@pilot.es",
            published_url="https://pilot.es/ens",
            self_assessment_report_id=rep_id,
        )

        run_id = await _create_run(async_client, project_id, "BASICA")
        await _set_tenant(db, project_id)
        data = await dossier_generator.generate_dossier(
            db, pid, uuid.UUID(run_id), force=True,
        )
        z = zipfile.ZipFile(io.BytesIO(data))
        names = list(z.namelist())
        decl_files = [
            n for n in names
            if n.startswith("01_GOBIERNO/declaracion_conformidad/")
            and n.endswith(".json")
        ]
        assert len(decl_files) == 1
        payload = json.loads(z.read(decl_files[0]))
        assert payload["template_codigo"] == "E-041"
        assert payload["status"] == "signed"
        assert payload["responsible_person_name"] == "RSEG Pilot"

        # MANIFEST refleja contador
        manifest = json.loads(z.read("MANIFEST.json"))
        assert manifest.get("total_declarations") == 1

    @pytest.mark.asyncio
    async def test_executive_summary_mentions_declarations(
        self, async_client, db,
    ):
        from backend.app.motors.m27_conformity.conformity_service_paso5 import (
            ConformityServicePaso5,
        )

        _, project_id = await setup_test_project(db)
        pid = uuid.UUID(project_id)
        async with _admin_setup(db):
            await db.execute(sa_text(
                "UPDATE projects SET categoria_objetivo = 'BASICA' "
                "WHERE id = :pid"
            ), {"pid": project_id})
        await _set_tenant(db, project_id)
        svc = ConformityServicePaso5()
        await svc.initialize_conformity_route(db, pid)
        rep_id = uuid.uuid4()
        await db.execute(sa_text(
            "INSERT INTO documents (id, project_id, nombre, template_codigo, "
            "created_at, updated_at) VALUES (:id, :pid, "
            "'E-808C Autoevaluación', 'E-808C', now(), now())"
        ), {"id": str(rep_id), "pid": str(pid)})
        await svc.process_basic_declaration(
            db, pid,
            responsible_person_name="RSEG Exec",
            responsible_person_email="exec@test.es",
            published_url="https://test.es/ens",
            self_assessment_report_id=rep_id,
        )
        run_id = await _create_run(async_client, project_id, "BASICA")
        await _set_tenant(db, project_id)
        data = await dossier_generator.generate_dossier(
            db, pid, uuid.UUID(run_id), force=True,
        )
        z = zipfile.ZipFile(io.BytesIO(data))
        exec_md = z.read(
            "00_INDICE/resumen_ejecutivo.md",
        ).decode("utf-8")
        assert "Declaraciones de Conformidad" in exec_md
        assert "1 firmadas" in exec_md or "1 firmadas)" in exec_md

    @pytest.mark.asyncio
    async def test_generate_declaracion_conformidad_via_m27_basica(
        self, async_client, db,
    ):
        _, project_id = await setup_test_project(db)
        pid = uuid.UUID(project_id)
        async with _admin_setup(db):
            await db.execute(sa_text(
                "UPDATE projects SET categoria_objetivo = 'BASICA' "
                "WHERE id = :pid"
            ), {"pid": project_id})
        await _set_tenant(db, project_id)
        from backend.app.motors.m27_conformity.conformity_service_paso5 import (
            ConformityServicePaso5,
        )
        await ConformityServicePaso5().initialize_conformity_route(db, pid)

        rep_id = uuid.uuid4()
        await db.execute(sa_text(
            "INSERT INTO documents (id, project_id, nombre, template_codigo, "
            "created_at, updated_at) VALUES (:id, :pid, "
            "'E-808C Autoevaluación', 'E-808C', now(), now())"
        ), {"id": str(rep_id), "pid": str(pid)})
        result = await dossier_generator.generate_declaracion_conformidad_via_m27(
            db, pid,
            responsible_person_name="RSEG Wire",
            responsible_person_email="wire@test.es",
            published_url="https://wire.test.es/ens",
            self_assessment_report_id=rep_id,
        )
        assert result["template_codigo"] == "E-041"
        assert result["carpeta_destino"] == "01_GOBIERNO"
        assert result["status"] == "signed"
        assert result["signed_hash"] is not None
        assert result["submission_id"] is not None

    @pytest.mark.asyncio
    async def test_generate_declaracion_via_m27_media_rejected(
        self, async_client, db,
    ):
        _, project_id = await setup_test_project(db)
        pid = uuid.UUID(project_id)
        async with _admin_setup(db):
            await db.execute(sa_text(
                "UPDATE projects SET categoria_objetivo = 'MEDIA' "
                "WHERE id = :pid"
            ), {"pid": project_id})
        await _set_tenant(db, project_id)
        from backend.app.motors.m27_conformity.conformity_service_paso5 import (
            ConformityServicePaso5,
        )
        await ConformityServicePaso5().initialize_conformity_route(db, pid)

        # MEDIA route = certificacion_enac · process_basic_declaration rejects
        with pytest.raises(dossier_generator.DossierError):
            await dossier_generator.generate_declaracion_conformidad_via_m27(
                db, pid,
                responsible_person_name="RSEG MEDIA",
                responsible_person_email="media@test.es",
                published_url="https://media.test.es/ens",
            )

    @pytest.mark.asyncio
    async def test_dossier_index_includes_declarations(
        self, async_client, db,
    ):
        from backend.app.motors.m27_conformity.conformity_service_paso5 import (
            ConformityServicePaso5,
        )

        _, project_id = await setup_test_project(db)
        pid = uuid.UUID(project_id)
        async with _admin_setup(db):
            await db.execute(sa_text(
                "UPDATE projects SET categoria_objetivo = 'BASICA' "
                "WHERE id = :pid"
            ), {"pid": project_id})
        await _set_tenant(db, project_id)
        svc = ConformityServicePaso5()
        await svc.initialize_conformity_route(db, pid)
        await svc.process_basic_declaration(
            db, pid,
            responsible_person_name="RSEG Idx",
            responsible_person_email="idx@test.es",
            published_url=None,
        )
        run_id = await _create_run(async_client, project_id, "BASICA")
        await _set_tenant(db, project_id)
        idx = await dossier_generator.build_index_data(
            db, pid, uuid.UUID(run_id),
        )
        assert idx["total_declarations"] == 1
        assert len(idx["declarations"]) == 1
        assert idx["declarations"][0]["template_codigo"] == "E-041"
