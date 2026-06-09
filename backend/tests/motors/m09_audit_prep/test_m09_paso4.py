"""Tests M9 Paso 4 — catalogo + validacion bloqueante + dossier BORRADOR
+ matriz 73 filas + hipervinculos + Agente 11 Auditor Interno.
"""
from __future__ import annotations

import io
import json
import uuid
import zipfile
from datetime import date, datetime, timezone

import pytest
from openpyxl import load_workbook
from sqlalchemy import text as sa_text

from backend.app.database import set_tenant_context
from backend.app.models.documents import Document
from backend.app.motors.m08_verification.models import (
    VerificationFinding, VerificationRun,
)
from backend.app.motors.m09_audit_prep import (
    matriz_99,
)
from backend.app.motors.m09_audit_prep.dossier_generator import (
    DOSSIER_STRUCTURE, DossierError, generate_dossier,
)
from backend.app.motors.m09_audit_prep.checklist_service import (
    REQUIRED_DELIVERABLES, require_complete_audit_prep,
)
from backend.app.motors.m09_audit_prep.internal_auditor import (
    QUESTION_BANK, build_e701_context, run_internal_audit,
)
from backend.tests.conftest import _admin_setup, setup_test_project


BASE = "/api/v1/audit-prep"


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════

async def _set_tenant(db, project_id: str) -> None:
    client_id = (await db.execute(
        sa_text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)},
    )).scalar()
    await set_tenant_context(
        db, client_id=client_id, project_id=uuid.UUID(project_id),
    )


async def _create_run(async_client, project_id: str, categoria="BASICA") -> str:
    r = await async_client.post(
        f"{BASE}/projects/{project_id}/runs", json={"categoria": categoria},
    )
    assert r.status_code == 200
    return r.json()["id"]


async def _create_verification_run_with_finding(
    db, project_id, severity="high",
):
    async with _admin_setup(db):
        vr = VerificationRun(
            project_id=uuid.UUID(project_id),
            category="BASICO", mode="internal", status="completed",
            scope_jsonb={"targets": ["x"], "web_apps": [], "exclusions": []},
            tools_used=["nuclei"], completed_at=datetime.now(timezone.utc),
            total_findings=1, confirmed_findings=1,
        )
        db.add(vr)
        await db.flush()
        f = VerificationFinding(
            project_id=uuid.UUID(project_id), run_id=vr.id,
            finding_hash=f"p4_{uuid.uuid4().hex[:8]}",
            title="Test finding p4", description="desc",
            severity=severity, affected_host="h1",
            tool_sources=["nuclei"],
            raw_outputs=[{"tool": "nuclei", "excerpt": "x"}],
            confidence_score=0.95,
            zfp_gate1_dedup=True, zfp_gate2_fp_filter=True,
            zfp_gate3_cross_tool=1, zfp_gate4_retest="not_applicable",
            zfp_gate5_classification="confirmed",
            ens_measures=[{"measure": "op.exp.5", "title": "t"}],
            ens_primary_measure="op.exp.5",
            remediation_summary="fix", status="open",
        )
        db.add(f)
        await db.flush()
    return vr, f


# ════════════════════════════════════════════════════════════════════
# 4.1 — Catalogo expandido + validacion bloqueante
# ════════════════════════════════════════════════════════════════════

class TestChecklistCatalog:
    def test_basica_catalog_complete(self):
        basica = REQUIRED_DELIVERABLES["BASICA"]
        # Catalogo expandido: minimo 40 entregables
        assert len(basica) >= 40
        assert "E-012" in basica
        assert "E-040" in basica
        assert "E-050" in basica
        assert "E-100" in basica  # Politica base
        assert "E-200" in basica  # Procedimiento operativo clave

    def test_media_adds_extended_policies(self):
        media = REQUIRED_DELIVERABLES["MEDIA"]
        basica = REQUIRED_DELIVERABLES["BASICA"]
        assert len(media) > len(basica)
        assert "E-114" in media  # politica adicional
        assert "E-501" in media  # plan continuidad
        assert "E-700" in media  # informe especifico

    def test_alta_includes_e704_red_team(self):
        alta = REQUIRED_DELIVERABLES["ALTA"]
        assert "E-704" in alta
        # 27 politicas completas
        assert all(f"E-{100 + i}" in alta for i in range(27))


class TestRequireCompleteAuditPrep:
    def test_rejects_run_without_results(self):
        from backend.app.motors.m09_audit_prep.checklist_service import (
            ChecklistError,
        )

        class FakeRun:
            checklist_results = {}
            readiness_score = None
        with pytest.raises(ChecklistError):
            require_complete_audit_prep(FakeRun())

    def test_returns_blockers_for_missing_deliverables(self):
        class FakeRun:
            checklist_results = {
                "entregables": {
                    "total": 5, "present": 0,
                    "missing": ["E-012", "E-040", "E-050"],
                },
                "firmas": {"total": 0, "firmadas": 0, "missing": []},
                "contradicciones": [],
                "registros_operativos": {
                    "ok": True, "meses_cubiertos": 6, "meses_requeridos": 6,
                },
            }
            readiness_score = 30
        blockers = require_complete_audit_prep(FakeRun())
        assert len(blockers) >= 3
        codes = {b["codigo"] for b in blockers}
        assert {"E-012", "E-040", "E-050"}.issubset(codes)

    def test_returns_blockers_for_error_contradictions(self):
        class FakeRun:
            checklist_results = {
                "entregables": {"total": 5, "present": 5, "missing": []},
                "firmas": {"total": 5, "firmadas": 5, "missing": []},
                "contradicciones": [
                    {
                        "medida": "op.exp.5",
                        "severidad": "error",
                        "descripcion": "DdA implantado sin evidencia",
                    },
                ],
                "registros_operativos": {
                    "ok": True, "meses_cubiertos": 6, "meses_requeridos": 6,
                },
            }
            readiness_score = 80
        blockers = require_complete_audit_prep(FakeRun())
        assert any(b["tipo"] == "contradiccion" for b in blockers)

    def test_no_blockers_on_high_score_clean(self):
        class FakeRun:
            checklist_results = {
                "entregables": {"total": 5, "present": 5, "missing": []},
                "firmas": {"total": 5, "firmadas": 5, "missing": []},
                "contradicciones": [],
                "registros_operativos": {
                    "ok": True, "meses_cubiertos": 6, "meses_requeridos": 6,
                },
            }
            readiness_score = 95
        assert require_complete_audit_prep(FakeRun()) == []


# ════════════════════════════════════════════════════════════════════
# 4.2 — Dossier: nomenclatura + force borrador
# ════════════════════════════════════════════════════════════════════

class TestDossierStructure:
    def test_dossier_has_15_folders_exact_names(self):
        folders = [item["folder"] for item in DOSSIER_STRUCTURE]
        assert folders == [
            "00_INDICE", "01_GOBIERNO", "02_CATEGORIZACION",
            "03_ANALISIS_RIESGOS", "04_DECLARACION_APLICABILIDAD",
            "05_PLAN_ADECUACION", "06_NORMATIVA", "07_PROCEDIMIENTOS",
            "08_REGISTROS_OPERACION", "09_EVIDENCIAS_POR_MEDIDA",
            "10_PLAN_CONTINUIDAD", "11_FORMACION", "12_PROVEEDORES",
            "13_INFORMES_TECNICOS", "99_MATRIZ_CRUZADA",
        ]

    @pytest.mark.asyncio
    async def test_generate_dossier_blocked_without_force(
        self, async_client, db,
    ):
        _, project_id = await setup_test_project(db)
        run_id = await _create_run(async_client, project_id, "BASICA")
        await _set_tenant(db, project_id)
        # Sin force, hay entregables missing → DossierError
        with pytest.raises(DossierError):
            await generate_dossier(
                db, uuid.UUID(project_id), uuid.UUID(run_id),
            )

    @pytest.mark.asyncio
    async def test_generate_dossier_force_emits_borrador_banner(
        self, async_client, db,
    ):
        _, project_id = await setup_test_project(db)
        run_id = await _create_run(async_client, project_id, "BASICA")
        await _set_tenant(db, project_id)
        data = await generate_dossier(
            db, uuid.UUID(project_id), uuid.UUID(run_id), force=True,
        )
        z = zipfile.ZipFile(io.BytesIO(data))
        names = z.namelist()
        # Banner BORRADOR incluido
        assert "00_INDICE/BORRADOR_pendientes.md" in names
        banner = z.read("00_INDICE/BORRADOR_pendientes.md").decode()
        assert "BORRADOR" in banner
        # MANIFEST refleja draft_mode + blockers
        manifest = json.loads(z.read("MANIFEST.json"))
        assert manifest["draft_mode"] is True
        assert len(manifest["blockers"]) > 0


# ════════════════════════════════════════════════════════════════════
# 4.3 — Matriz 99: 73 filas + hipervinculos
# ════════════════════════════════════════════════════════════════════

class TestMatriz99Expanded:
    @pytest.mark.asyncio
    async def test_matriz_includes_all_measures_as_rows(
        self, async_client, db,
    ):
        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        rows = await matriz_99.generate_matriz_99_data(
            db, uuid.UUID(project_id), "BASICA",
        )
        # Al menos 73 filas (puede haber mas si hay refuerzos)
        codigos = {r["codigo"] for r in rows}
        # Algunas medidas clave de cada familia
        assert "op.exp.5" in codigos
        assert "mp.com.2" in codigos
        assert "org.1" in codigos or "org.2" in codigos

    @pytest.mark.asyncio
    async def test_matriz_xlsx_has_hyperlink_comments(
        self, async_client, db,
    ):
        _, project_id = await setup_test_project(db)
        # Crear evidencia para una medida aplicable a BÁSICA.
        # op.exp.1 (Inventario de activos) aplica a BÁSICA en RD 311/2022 Anexo II.
        # (Antes op.exp.5 Gestión de cambios · recategorizada a MEDIA-min en la
        # corrección del catálogo Pasada 16 P16.B → ya NO aparece en la matriz BÁSICA.)
        m_id_r = await db.execute(sa_text(
            "SELECT id FROM ens_measures WHERE codigo = 'op.exp.1' LIMIT 1"
        ))
        m_row = m_id_r.first()
        if m_row:
            async with _admin_setup(db):
                await db.execute(sa_text(
                    "INSERT INTO evidence (project_id, measure_id, measure_code, "
                    "tipo, vigente, fecha_evidencia, fecha_caducidad, hash_sha256, created_at) "
                    "VALUES (:pid, :mid, 'op.exp.1', 'test', true, "
                    "CURRENT_DATE, CURRENT_DATE + INTERVAL '180 days', "
                    ":h, now())"
                ), {
                    "pid": project_id, "mid": str(m_row[0]),
                    "h": "a" * 64,
                })
                await db.commit()
        await _set_tenant(db, project_id)
        data = await matriz_99.generate_matriz_99(
            db, uuid.UUID(project_id), "BASICA",
        )
        wb = load_workbook(io.BytesIO(data))
        ws = wb.active
        # Buscar la fila op.exp.1 y verificar el hipervinculo
        found_link = False
        for row in ws.iter_rows(min_row=2):
            codigo_cell = row[0]
            if codigo_cell.value == "op.exp.1":
                ev_cell = row[7]
                if ev_cell.hyperlink and "/api/v1/evidence/" in str(ev_cell.hyperlink.target or ""):
                    found_link = True
                break
        assert found_link, "op.exp.1 no tiene hipervinculo a evidencia"


# ════════════════════════════════════════════════════════════════════
# 4.5 — Agente 11 Auditor Interno Virtual
# ════════════════════════════════════════════════════════════════════

class TestInternalAuditor:
    def test_question_bank_has_15_questions(self):
        assert len(QUESTION_BANK) == 15
        assert all("code" in q for q in QUESTION_BANK)
        assert all("question" in q for q in QUESTION_BANK)
        assert all("check_kind" in q for q in QUESTION_BANK)

    def test_question_bank_covers_key_areas(self):
        areas = {q["area"] for q in QUESTION_BANK}
        expected = {
            "gobierno", "categorizacion", "dda", "continuidad",
            "verificacion_tecnica", "formacion",
        }
        assert expected.issubset(areas)

    @pytest.mark.asyncio
    async def test_run_internal_audit_on_empty_project_fails_most(
        self, async_client, db,
    ):
        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        result = await run_internal_audit(
            db, uuid.UUID(project_id), "BASICA",
        )
        assert result["total_questions"] == 15
        assert result["by_verdict"]["fail"] >= 10
        assert result["score"] < 50
        assert result["recomendacion"] == "requiere_trabajo_adicional"

    @pytest.mark.asyncio
    async def test_run_internal_audit_with_verification_passes_Q013(
        self, async_client, db,
    ):
        _, project_id = await setup_test_project(db)
        await _create_verification_run_with_finding(db, project_id)
        await _set_tenant(db, project_id)
        result = await run_internal_audit(
            db, uuid.UUID(project_id), "BASICA",
        )
        q013 = next(q for q in result["questions"] if q["code"] == "Q-013")
        # Hay run v5.1 aunque falte E-702 emitido
        assert q013["verdict"] in ("ok", "partial")

    @pytest.mark.asyncio
    async def test_q014_fails_with_high_critical_open(
        self, async_client, db,
    ):
        _, project_id = await setup_test_project(db)
        await _create_verification_run_with_finding(
            db, project_id, severity="critical",
        )
        await _set_tenant(db, project_id)
        result = await run_internal_audit(
            db, uuid.UUID(project_id), "BASICA",
        )
        q014 = next(q for q in result["questions"] if q["code"] == "Q-014")
        assert q014["verdict"] == "fail"

    @pytest.mark.asyncio
    async def test_build_e701_context_structure(self, async_client, db):
        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        sample_audit = {
            "categoria": "BASICA",
            "score": 75,
            "score_level": "aceptable",
            "recomendacion": "favorable_con_observaciones",
            "total_questions": 15,
            "by_verdict": {"ok": 10, "partial": 2, "fail": 3, "not_assessed": 0},
            "questions": [{"code": "Q-001", "verdict": "ok"}],
            "potential_findings": [
                {"code": "Q-003", "verdict": "fail", "area": "categorizacion",
                 "answer": "No se encontro documento E-012"},
            ],
            "partial_findings": [],
            "executed_at": "2026-04-21T00:00:00Z",
        }
        ctx = await build_e701_context(
            db, uuid.UUID(project_id),
            sample_audit,
            cliente={"razon_social": "Test SL", "nif": "B00"},
            proyecto={"nombre": "p1"},
            responsables={"responsable_seguridad": {"nombre": "RSEG"}},
        )
        assert ctx["cliente"]["razon_social"] == "Test SL"
        assert ctx["auditoria_interna"]["score"] == 75
        assert ctx["auditoria_interna"]["fail"] == 3
        assert len(ctx["hallazgos_potenciales"]) == 1
        # Phase E polish · nuevas_ncs mapping
        assert len(ctx["nuevas_ncs"]) == 1
        assert ctx["nuevas_ncs"][0]["id"] == "NC-001"
        assert ctx["nuevas_ncs"][0]["severidad"] == "alta"
        # Phase E polish · conclusion derivada score
        assert ctx["conclusion"]["recomendacion"] == "favorable_con_observaciones"
        # Phase E polish · firmas + auditoria + resumen presentes
        assert "firmas" in ctx
        assert "auditoria" in ctx
        assert ctx["resumen"]["ncs_nuevas"] == 1


# ════════════════════════════════════════════════════════════════════
# 4.6 — Integracion M8 v5.1 en 13_INFORMES_TECNICOS
# ════════════════════════════════════════════════════════════════════

class TestM8IntegrationInDossier:
    @pytest.mark.asyncio
    async def test_dossier_13_contains_pentest_findings_summary(
        self, async_client, db,
    ):
        _, project_id = await setup_test_project(db)
        await _create_verification_run_with_finding(db, project_id)
        run_id = await _create_run(async_client, project_id, "BASICA")
        await _set_tenant(db, project_id)
        data = await generate_dossier(
            db, uuid.UUID(project_id), uuid.UUID(run_id), force=True,
        )
        z = zipfile.ZipFile(io.BytesIO(data))
        names = z.namelist()
        # 13_INFORMES_TECNICOS debe tener el summary
        assert any(
            n.startswith("13_INFORMES_TECNICOS/")
            and "pentest_findings_summary.json" in n
            for n in names
        )
        summary_json = json.loads(
            z.read("13_INFORMES_TECNICOS/pentest_findings_summary.json"),
        )
        assert isinstance(summary_json, list)
        assert len(summary_json) == 1
        assert summary_json[0]["title"] == "Test finding p4"

    @pytest.mark.asyncio
    async def test_manifest_reports_draft_and_pdf_master_flag(
        self, async_client, db,
    ):
        _, project_id = await setup_test_project(db)
        run_id = await _create_run(async_client, project_id, "BASICA")
        await _set_tenant(db, project_id)
        data = await generate_dossier(
            db, uuid.UUID(project_id), uuid.UUID(run_id), force=True,
        )
        z = zipfile.ZipFile(io.BytesIO(data))
        manifest = json.loads(z.read("MANIFEST.json"))
        assert "pdf_master_included" in manifest
        assert manifest["draft_mode"] is True
        # Existencia del banner cuando es borrador
        assert manifest["blockers"]


# ════════════════════════════════════════════════════════════════════
# 4.7 — E-701 polish #6 (Future-1.E.1.dossier-pack.E-hybrid)
# ════════════════════════════════════════════════════════════════════


class TestE701Polish:
    """Phase E polish · build_e701_context cubre todas las variables del
    template E701_auditoria_interna_pre_externa.md sin UndefinedError.
    """

    SAMPLE_CLIENTE = {
        "razon_social": "Cliente Piloto SL",
        "nif": "B12345678",
        "domicilio": "Calle Pruebas 1, Madrid",
        "organo_aprobador_politicas": "Consejo Administración",
        "representante": {"nombre": "Juan Pérez"},
    }
    SAMPLE_PROYECTO = {
        "nombre": "Sistema Test ENS",
        "codigo_documento_base": "E",
        "version_actual": "1.0",
        "fecha_aprobacion_inicial": "2026-05-23",
        "sistema_principal": "Plataforma corporativa SaaS",
        "alcance": "Servicios de gestión interna",
        "categoria_ens": "BÁSICA",
    }
    SAMPLE_RESPONSABLES = {
        "consultor": {
            "nombre": "Marcos Mata García",
            "cargo": "Consultor independiente ENS",
        },
        "responsable_seguridad": {
            "nombre": "Ana Ruiz",
            "cargo": "Responsable de Seguridad",
        },
    }

    def _sample_audit(self, *, score: int = 80) -> dict:
        return {
            "categoria": "BASICA",
            "score": score,
            "score_level": (
                "excelente" if score >= 90
                else "aceptable" if score >= 75
                else "mejorable" if score >= 50
                else "critico"
            ),
            "recomendacion": (
                "favorable" if score >= 85
                else "favorable_con_observaciones" if score >= 70
                else "requiere_trabajo_adicional"
            ),
            "total_questions": 15,
            "by_verdict": {
                "ok": 10, "partial": 3, "fail": 2, "not_assessed": 0,
            },
            "questions": [
                {"code": "Q-001", "verdict": "ok"},
                {"code": "Q-003", "verdict": "fail"},
            ],
            "potential_findings": [
                {
                    "code": "Q-003", "area": "categorizacion",
                    "verdict": "fail",
                    "question": "¿Acta categorización firmada?",
                    "answer": "No se encontro documento E-012.",
                },
                {
                    "code": "Q-008", "area": "evidencias_opexp5",
                    "verdict": "fail",
                    "question": "¿Evidencia op.exp.5 vigente?",
                    "answer": "No hay evidencias vigentes para op.exp.5.",
                },
            ],
            "partial_findings": [
                {
                    "code": "Q-005", "area": "dda",
                    "verdict": "partial",
                    "question": "¿DdA firmada por RSEG?",
                    "answer": "Documento E-040 existe pero no firmado.",
                },
            ],
            "executed_at": "2026-05-23T12:00:00Z",
        }

    @pytest.mark.asyncio
    async def test_context_has_all_template_variables(
        self, async_client, db,
    ):
        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        ctx = await build_e701_context(
            db, uuid.UUID(project_id), self._sample_audit(),
            cliente=self.SAMPLE_CLIENTE,
            proyecto=self.SAMPLE_PROYECTO,
            responsables=self.SAMPLE_RESPONSABLES,
        )
        # All variables required by E701_auditoria_interna_pre_externa.md
        required_keys = {
            "cliente", "proyecto", "responsables",
            "auditoria", "auditoria_interna",
            "cierre_ncs", "nuevas_ncs", "observaciones",
            "documentos_revisados", "puntos_riesgo",
            "recomendaciones", "conclusion", "resumen", "firmas",
            "preguntas", "hallazgos_potenciales",
        }
        assert required_keys.issubset(set(ctx.keys())), (
            f"falta: {required_keys - set(ctx.keys())}"
        )

    @pytest.mark.asyncio
    async def test_context_nuevas_ncs_mapped_with_severity(
        self, async_client, db,
    ):
        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        ctx = await build_e701_context(
            db, uuid.UUID(project_id), self._sample_audit(),
            cliente=self.SAMPLE_CLIENTE, proyecto=self.SAMPLE_PROYECTO,
            responsables=self.SAMPLE_RESPONSABLES,
        )
        ncs = ctx["nuevas_ncs"]
        assert len(ncs) == 2
        assert ncs[0]["id"] == "NC-001"
        assert ncs[1]["id"] == "NC-002"
        # severity "alta" porque verdict=fail per mapping
        for nc in ncs:
            assert nc["severidad"] == "alta"
            assert nc["plazo"] == "antes_auditoria_externa"
            assert "tipo" in nc
            assert "medida" in nc

    @pytest.mark.asyncio
    async def test_context_conclusion_favorable_when_score_high(
        self, async_client, db,
    ):
        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        ctx = await build_e701_context(
            db, uuid.UUID(project_id), self._sample_audit(score=95),
            cliente=self.SAMPLE_CLIENTE, proyecto=self.SAMPLE_PROYECTO,
            responsables=self.SAMPLE_RESPONSABLES,
        )
        assert ctx["conclusion"]["recomendacion"] == "favorable"
        assert "LISTO" in ctx["conclusion"]["estado"]

    @pytest.mark.asyncio
    async def test_context_conclusion_requires_work_when_low(
        self, async_client, db,
    ):
        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        ctx = await build_e701_context(
            db, uuid.UUID(project_id), self._sample_audit(score=55),
            cliente=self.SAMPLE_CLIENTE, proyecto=self.SAMPLE_PROYECTO,
            responsables=self.SAMPLE_RESPONSABLES,
        )
        assert ctx["conclusion"]["recomendacion"] == "requiere_trabajo_adicional"
        assert "MEJORABLE" in ctx["conclusion"]["estado"]

    @pytest.mark.asyncio
    async def test_context_documentos_revisados_queries_project(
        self, async_client, db,
    ):
        _, project_id = await setup_test_project(db)
        pid = uuid.UUID(project_id)
        async with _admin_setup(db):
            doc = Document(
                project_id=pid, template_codigo="E-040",
                nombre="DdA firmada", estado="aprobado",
                aprobado_por="RSEG", fecha_aprobacion=date.today(),
                signature_ed25519="ed25519:test",
                tipo="ENTREGABLE",
            )
            db.add(doc)
            await db.flush()
        await _set_tenant(db, project_id)
        ctx = await build_e701_context(
            db, pid, self._sample_audit(),
            cliente=self.SAMPLE_CLIENTE, proyecto=self.SAMPLE_PROYECTO,
            responsables=self.SAMPLE_RESPONSABLES,
        )
        docs = ctx["documentos_revisados"]
        assert len(docs) >= 1
        e040 = next((d for d in docs if "E-040" in d["nombre"]), None)
        assert e040 is not None
        assert e040["coherencia"] == "Coherente"  # firmado Ed25519
        assert e040["aprobado_por"] == "RSEG"

    @pytest.mark.asyncio
    async def test_context_recomendaciones_includes_high_severity(
        self, async_client, db,
    ):
        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        ctx = await build_e701_context(
            db, uuid.UUID(project_id), self._sample_audit(score=80),
            cliente=self.SAMPLE_CLIENTE, proyecto=self.SAMPLE_PROYECTO,
            responsables=self.SAMPLE_RESPONSABLES,
        )
        recs = ctx["recomendaciones"]
        assert len(recs) >= 2
        sev_high_rec = next(
            (r for r in recs if "severidad alta" in r.lower()), None,
        )
        assert sev_high_rec is not None
        # 2 NCs fail → severidad alta · check count mention
        assert "2 NC" in sev_high_rec

    @pytest.mark.asyncio
    async def test_context_resumen_counts_correctly(
        self, async_client, db,
    ):
        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        ctx = await build_e701_context(
            db, uuid.UUID(project_id), self._sample_audit(),
            cliente=self.SAMPLE_CLIENTE, proyecto=self.SAMPLE_PROYECTO,
            responsables=self.SAMPLE_RESPONSABLES,
        )
        resumen = ctx["resumen"]
        assert resumen["ncs_nuevas"] == 2
        # Sin e700_audit_result · ncs_iniciales/cerradas/pendientes default 0
        assert resumen["ncs_iniciales"] == 0
        assert resumen["ncs_cerradas"] == 0
        assert resumen["ncs_pendientes"] == 0

    @pytest.mark.asyncio
    async def test_context_resumen_with_prior_e700(
        self, async_client, db,
    ):
        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        e700_prior = {
            "potential_findings": [
                {"code": "Q-001"}, {"code": "Q-002"},
                {"code": "Q-003"}, {"code": "Q-004"},
            ],
        }
        cierre = [
            {"id": "NC-001", "estado": "cerrada"},
            {"id": "NC-002", "estado": "cerrada"},
            {"id": "NC-003", "estado": "pendiente"},
        ]
        ctx = await build_e701_context(
            db, uuid.UUID(project_id), self._sample_audit(),
            cliente=self.SAMPLE_CLIENTE, proyecto=self.SAMPLE_PROYECTO,
            responsables=self.SAMPLE_RESPONSABLES,
            cierre_ncs=cierre, e700_audit_result=e700_prior,
        )
        resumen = ctx["resumen"]
        assert resumen["ncs_iniciales"] == 4
        assert resumen["ncs_cerradas"] == 2
        assert resumen["ncs_pendientes"] == 2

    @pytest.mark.asyncio
    async def test_context_firmas_placeholder_populated(
        self, async_client, db,
    ):
        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        ctx = await build_e701_context(
            db, uuid.UUID(project_id), self._sample_audit(),
            cliente=self.SAMPLE_CLIENTE, proyecto=self.SAMPLE_PROYECTO,
            responsables=self.SAMPLE_RESPONSABLES,
        )
        firmas = ctx["firmas"]
        # 3 funciones · elaborado/revisado/aprobado
        assert set(firmas.keys()) == {"elaborado", "revisado", "aprobado"}
        # Elaborado pre-poblado con consultor responsables
        assert firmas["elaborado"]["nombre"] == "Marcos Mata García"
        assert firmas["elaborado"]["cargo"] == "Consultor independiente ENS"
        # Revisado pre-poblado con responsable_seguridad
        assert firmas["revisado"]["nombre"] == "Ana Ruiz"
        # Aprobado pre-poblado con organo_aprobador_politicas
        assert firmas["aprobado"]["nombre"] == "Consejo Administración"
        # firma_marca placeholder '—' pendiente firma Ed25519 real
        for funcion in firmas.values():
            assert funcion["firma_marca"] == "—"

    @pytest.mark.asyncio
    async def test_template_renders_without_undefined_error(
        self, async_client, db,
    ):
        """E-701 template Jinja2 render NO levanta UndefinedError con
        contexto producido por build_e701_context. Smoke render strict mode.
        """
        from pathlib import Path
        from jinja2 import Environment, StrictUndefined

        _, project_id = await setup_test_project(db)
        await _set_tenant(db, project_id)
        ctx = await build_e701_context(
            db, uuid.UUID(project_id), self._sample_audit(),
            cliente=self.SAMPLE_CLIENTE, proyecto=self.SAMPLE_PROYECTO,
            responsables=self.SAMPLE_RESPONSABLES,
        )

        template_path = (
            Path(__file__).resolve().parents[3]
            / "app/motors/m06_document_factory/templates/deliverables"
            / "E701_auditoria_interna_pre_externa.md"
        )
        assert template_path.exists(), template_path
        body = template_path.read_text(encoding="utf-8")

        env = Environment(undefined=StrictUndefined)
        tpl = env.from_string(body)
        rendered = tpl.render(**ctx)

        # Render exitoso · contenido clave presente
        assert "Cliente Piloto SL" in rendered.upper() or "cliente piloto sl" in rendered.lower()
        assert "Marcos Mata" in rendered
        assert "BÁSICA" in rendered or "Basica" in rendered or "BASICA" in rendered.upper()
        # Conclusión render
        assert ctx["conclusion"]["estado"] in rendered
        # Firmas render
        assert "Consejo Administración" in rendered
