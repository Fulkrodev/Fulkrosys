"""Tests M10 Audit Simulation Engine.

Cubre:
- Catálogo de preguntas ENAC (58, 14 familias)
- Evaluación determinista L0-L5 con reglas explícitas (NO LLM)
- Contradicciones DdA / Evidence / Pentest
- Scores + recomendación
- Informe DOCX
- API endpoints
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import text

from backend.app.database import set_tenant_context
from backend.app.motors.m10_audit_sim.audit_questions import (
    AUDIT_QUESTIONS,
    get_families,
    get_questions_by_family,
    get_questions_for_categoria,
)
from backend.app.motors.m10_audit_sim.audit_simulator import AuditSimulatorService
from backend.tests.conftest import _admin_setup, setup_test_project


BASE = "/api/v1/audit-sim"


# ─────────── Helpers ───────────

async def _setup_tenant(db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(
        db,
        client_id=uuid.UUID(client_id),
        project_id=uuid.UUID(project_id),
    )
    return client_id, project_id


async def _seed_ens_measure(db, codigo: str, familia: str):
    """Inserta una EnsMeasure con el código dado (si no existe)."""
    async with _admin_setup(db):
        existing = await db.execute(
            text("SELECT id FROM ens_measures WHERE codigo = :c"),
            {"c": codigo},
        )
        if existing.scalar() is None:
            await db.execute(text(
                "INSERT INTO ens_measures (id, codigo, nombre, marco, familia, aplica_basica, aplica_media, aplica_alta, created_at) "
                "VALUES (gen_random_uuid(), :c, :n, 'ENS', :f, true, true, true, now())"
            ), {"c": codigo, "n": f"Medida {codigo}", "f": familia})
    await db.flush()


async def _seed_dda_entry(db, project_id: str, measure_code: str, aplicabilidad: str, estado_impl: str | None = None):
    async with _admin_setup(db):
        row = await db.execute(
            text("SELECT id FROM ens_measures WHERE codigo = :c"),
            {"c": measure_code},
        )
        measure_id = row.scalar()
        if not measure_id:
            raise RuntimeError(f"Seed ens_measure first: {measure_code}")
        await db.execute(text(
            "INSERT INTO dda_entries (id, project_id, measure_id, aplicabilidad, estado_implementacion, created_at) "
            "VALUES (gen_random_uuid(), :pid, :mid, :apl, :est, now())"
        ), {"pid": project_id, "mid": str(measure_id), "apl": aplicabilidad, "est": estado_impl})
    await db.flush()


async def _seed_document(db, project_id: str, template_codigo: str):
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO documents (id, project_id, nombre, template_codigo, estado, created_at) "
            "VALUES (gen_random_uuid(), :pid, :n, :tc, 'active', now())"
        ), {"pid": project_id, "n": f"Doc {template_codigo}", "tc": template_codigo})
    await db.flush()


async def _seed_evidence(db, project_id: str, measure_code: str, vigente: bool = True, dias_atras: int = 30):
    fecha = date.today() - timedelta(days=dias_atras)
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO evidence (id, project_id, measure_code, tipo, fecha_evidencia, vigente, created_at) "
            "VALUES (gen_random_uuid(), :pid, :mc, 'documento', :f, :v, now())"
        ), {"pid": project_id, "mc": measure_code, "f": fecha, "v": vigente})
    await db.flush()


# ─────────── Catálogo ───────────

def test_catalog_has_73_questions():
    # Cobertura completa RD 311/2022 Anexo II (alineado 2026-06-07 · antes 58 con
    # códigos RD 3/2010 derogados). nombre+aplica derivados de ANEXO_II_RD311.
    assert len(AUDIT_QUESTIONS) == 73


def test_catalog_covers_16_families():
    families = get_families()
    assert len(families) == 16
    expected = {"org", "op.pl", "op.acc", "op.exp", "op.ext", "op.nub", "op.cont",
                "op.mon", "mp.if", "mp.per", "mp.eq", "mp.com", "mp.si", "mp.sw",
                "mp.info", "mp.s"}
    assert set(families) == expected


def test_catalog_codes_match_anexo_ii_rd311():
    # Las 73 preguntas == las 73 medidas oficiales (sin códigos RD 3/2010).
    from backend.app.motors.m03_dda.anexo2_rd311_2022 import ANEXO_II_RD311

    assert set(AUDIT_QUESTIONS) == set(ANEXO_II_RD311)
    for legacy in ("op.exp.11", "op.acc.7", "mp.s.8", "mp.if.9"):
        assert legacy not in AUDIT_QUESTIONS


def test_all_questions_have_required_fields():
    for code, q in AUDIT_QUESTIONS.items():
        for field in ("pregunta", "criterio", "familia", "aplica", "nombre"):
            assert field in q, f"{code} missing {field}"
        assert q["aplica"]
        assert all(cat in ("BASICA", "MEDIA", "ALTA") for cat in q["aplica"])


def test_questions_basica_fewer_than_media():
    basica = get_questions_for_categoria("BASICA")
    media = get_questions_for_categoria("MEDIA")
    alta = get_questions_for_categoria("ALTA")
    assert len(basica) < len(media) < len(alta)
    assert (len(basica), len(media), len(alta)) == (52, 68, 73)  # RD 311/2022 Anexo II


def test_questions_alta_only_measures():
    # Medidas que solo aplican a ALTA en RD 311/2022 (op.cont.4 medios alternativos,
    # op.ext.3 cadena de suministro). Sustituye al antiguo op.acc.7 (código RD 3/2010).
    alta = get_questions_for_categoria("ALTA")
    basica = get_questions_for_categoria("BASICA")
    media = get_questions_for_categoria("MEDIA")
    for code in ("op.cont.4", "op.ext.3"):
        assert code in alta
        assert code not in basica
        assert code not in media


def test_questions_by_family_org_has_4():
    org = get_questions_by_family("org")
    assert len(org) == 4


# ─────────── Reglas deterministas (unit) ───────────

def test_evaluate_no_document_no_evidence_is_nc_mayor():
    r = AuditSimulatorService._evaluate(
        has_document=False, has_evidence=False,
        evidence_current=False, evidence_sufficient=False,
        pentest_major=False, expected_doc=True,
    )
    assert r == "no_conforme_mayor"


def test_evaluate_document_without_evidence_is_nc_menor():
    r = AuditSimulatorService._evaluate(
        has_document=True, has_evidence=False,
        evidence_current=False, evidence_sufficient=False,
        pentest_major=False, expected_doc=True,
    )
    assert r == "no_conforme_mayor" or r == "no_conforme_menor"
    # Con document pero sin evidence: no_conforme_menor (regla del briefing)
    # El algoritmo devuelve "no_conforme_mayor" si no hay nada;
    # si hay documento → no_conforme_menor
    # En nuestra lógica concreta (sin document + sin evidence → nc_mayor;
    # con document + sin evidence → no pasa por el primer branch; segundo branch
    # "expected_doc and not has_document" = False; luego evidencia: has_evidence=False
    # cae al último "return no_conforme_menor")
    assert r == "no_conforme_menor"


def test_evaluate_expired_evidence_is_nc_menor():
    r = AuditSimulatorService._evaluate(
        has_document=True, has_evidence=True,
        evidence_current=False, evidence_sufficient=False,
        pentest_major=False, expected_doc=True,
    )
    assert r == "no_conforme_menor"


def test_evaluate_full_compliance_is_conforme():
    r = AuditSimulatorService._evaluate(
        has_document=True, has_evidence=True,
        evidence_current=True, evidence_sufficient=True,
        pentest_major=False, expected_doc=True,
    )
    assert r == "conforme"


def test_evaluate_pentest_major_downgrades():
    r = AuditSimulatorService._evaluate(
        has_document=True, has_evidence=True,
        evidence_current=True, evidence_sufficient=True,
        pentest_major=True, expected_doc=True,
    )
    assert r == "observacion"


def test_evaluate_pentest_major_without_evidence_is_nc_mayor():
    r = AuditSimulatorService._evaluate(
        has_document=False, has_evidence=False,
        evidence_current=False, evidence_sufficient=False,
        pentest_major=True, expected_doc=False,
    )
    assert r == "no_conforme_mayor"


# ─────────── Madurez L0-L5 ───────────

def test_maturity_l0_nothing():
    r = AuditSimulatorService._calculate_maturity_level(
        has_document=False, has_evidence=False,
        evidence_current=False, evidence_sufficient=False,
    )
    assert r == "L0"


def test_maturity_l1_doc_only():
    r = AuditSimulatorService._calculate_maturity_level(
        has_document=True, has_evidence=False,
        evidence_current=False, evidence_sufficient=False,
    )
    assert r == "L1"


def test_maturity_l2_expired_evidence():
    r = AuditSimulatorService._calculate_maturity_level(
        has_document=True, has_evidence=True,
        evidence_current=False, evidence_sufficient=False,
    )
    assert r == "L2"


def test_maturity_l3_doc_evidence_current_sufficient():
    r = AuditSimulatorService._calculate_maturity_level(
        has_document=True, has_evidence=True,
        evidence_current=True, evidence_sufficient=True,
        has_recent_records=True,
    )
    assert r == "L3"


def test_maturity_l4_with_metrics():
    r = AuditSimulatorService._calculate_maturity_level(
        has_document=True, has_evidence=True,
        evidence_current=True, evidence_sufficient=True,
        has_recent_records=True, has_metrics=True,
    )
    assert r == "L4"


# ─────────── Score + recomendación ───────────

def test_score_all_conforme_is_100():
    class F: pass
    findings = []
    for _ in range(5):
        f = F(); f.evaluacion = "conforme"; f.nivel_madurez = "L3"
        findings.append(f)
    assert AuditSimulatorService._calculate_score(findings) == 100


def test_score_mixed():
    class F: pass
    vals = ["conforme", "conforme", "observacion", "no_conforme_menor", "no_conforme_mayor"]
    findings = []
    for v in vals:
        f = F(); f.evaluacion = v; f.nivel_madurez = "L2"
        findings.append(f)
    # (100+100+75+25+0)/5 = 60
    assert AuditSimulatorService._calculate_score(findings) == 60


def test_recommendation_apto_score_85():
    r = AuditSimulatorService._determine_recommendation(85, 0)
    assert r == "apto_para_auditoria"


def test_recommendation_minor_remediation():
    r = AuditSimulatorService._determine_recommendation(75, 2)
    assert r == "requiere_remediacion_menor"


def test_recommendation_no_presentar():
    r = AuditSimulatorService._determine_recommendation(30, 10)
    assert r == "no_presentar"


# ─────────── Simulación end-to-end ───────────

@pytest.mark.asyncio
async def test_run_simulation_empty_project_all_nc_mayor(db):
    _, project_id = await _setup_tenant(db)
    run = await AuditSimulatorService().run_simulation(
        db, project_id=uuid.UUID(project_id), categoria="BASICA",
    )
    assert run.estado == "completed"
    assert run.total_measures == 52  # BASICA aplicables RD 311/2022 Anexo II
    assert run.measures_evaluated == 52
    # Sin documentos ni evidencias: todos no_conforme_mayor
    assert run.no_conformes_mayores == 52
    assert run.score_global == 0
    assert run.recomendacion == "no_presentar"


@pytest.mark.asyncio
async def test_run_simulation_no_aplica_via_dda(db):
    _, project_id = await _setup_tenant(db)
    # Semillar medida + DdA no_aplica
    await _seed_ens_measure(db, "org.1", "org")
    await _seed_dda_entry(db, project_id, "org.1", "no_aplica")

    run = await AuditSimulatorService().run_simulation(
        db, project_id=uuid.UUID(project_id), categoria="BASICA",
    )
    # Al menos 1 no_aplica (la que seedimos)
    assert run.no_aplica >= 1


@pytest.mark.asyncio
async def test_run_simulation_conforme_with_document_and_evidence(db):
    _, project_id = await _setup_tenant(db)
    # org.1 tiene documento_esperado E-001
    await _seed_document(db, project_id, "E-001")
    await _seed_evidence(db, project_id, "org.1", vigente=True, dias_atras=30)

    run = await AuditSimulatorService().run_simulation(
        db, project_id=uuid.UUID(project_id), categoria="BASICA",
    )
    # org.1 debe salir conforme
    findings = await AuditSimulatorService().list_findings(
        db, run.id, familia="org",
    )
    org1 = next(f for f in findings if f.measure_code == "org.1")
    assert org1.evaluacion == "conforme"
    assert org1.nivel_madurez in ("L3", "L4")
    assert org1.documento_encontrado is True
    assert org1.evidencia_encontrada is True


@pytest.mark.asyncio
async def test_contradiction_dda_implantado_sin_evidencia(db):
    _, project_id = await _setup_tenant(db)
    await _seed_ens_measure(db, "op.acc.4", "op.acc")
    await _seed_dda_entry(db, project_id, "op.acc.4", "aplica", estado_impl="implantado")
    # NO seeds evidence → contradicción

    run = await AuditSimulatorService().run_simulation(
        db, project_id=uuid.UUID(project_id), categoria="BASICA",
    )
    findings = await AuditSimulatorService().list_findings(
        db, run.id, familia="op.acc",
    )
    target = next((f for f in findings if f.measure_code == "op.acc.4"), None)
    assert target is not None
    assert target.contradiccion_detectada is True
    assert run.contradicciones_count >= 1


@pytest.mark.asyncio
async def test_scores_por_familia_present(db):
    _, project_id = await _setup_tenant(db)
    run = await AuditSimulatorService().run_simulation(
        db, project_id=uuid.UUID(project_id), categoria="MEDIA",
    )
    assert run.scores_por_familia
    assert "org" in run.scores_por_familia
    assert "score" in run.scores_por_familia["org"]


@pytest.mark.asyncio
async def test_generate_report_docx_returns_bytes(db):
    _, project_id = await _setup_tenant(db)
    run = await AuditSimulatorService().run_simulation(
        db, project_id=uuid.UUID(project_id), categoria="BASICA",
    )
    content = await AuditSimulatorService().generate_report_docx(db, run.id)
    assert content[:2] == b"PK"  # DOCX = zip
    assert len(content) > 2000


# ─────────── API ───────────

@pytest.mark.asyncio
async def test_api_questions_catalog(async_client):
    r = await async_client.get(f"{BASE}/questions")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 73


@pytest.mark.asyncio
async def test_api_questions_filter_categoria(async_client):
    r = await async_client.get(f"{BASE}/questions?categoria=BASICA")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 52


@pytest.mark.asyncio
async def test_api_run_simulation(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.post(
        f"{BASE}/projects/{project_id}/runs",
        json={"categoria": "BASICA"},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["categoria"] == "BASICA"
    assert data["estado"] == "completed"
    assert data["total_measures"] == 52


@pytest.mark.asyncio
async def test_api_list_findings_filter_evaluacion(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.post(
        f"{BASE}/projects/{project_id}/runs",
        json={"categoria": "BASICA"},
    )
    run_id = r.json()["id"]

    r2 = await async_client.get(
        f"{BASE}/projects/{project_id}/runs/{run_id}/findings?evaluacion=no_conforme_mayor"
    )
    assert r2.status_code == 200
    findings = r2.json()["findings"]
    assert len(findings) >= 1
    assert all(f["evaluacion"] == "no_conforme_mayor" for f in findings)


@pytest.mark.asyncio
async def test_api_summary_with_trend(async_client, db):
    _, project_id = await setup_test_project(db)
    # Primera run
    await async_client.post(
        f"{BASE}/projects/{project_id}/runs", json={"categoria": "BASICA"},
    )
    # Segunda run
    await async_client.post(
        f"{BASE}/projects/{project_id}/runs", json={"categoria": "BASICA"},
    )

    r = await async_client.get(f"{BASE}/projects/{project_id}/summary")
    assert r.status_code == 200
    data = r.json()
    assert data["runs_count"] == 2
    assert data["trend"] is not None


@pytest.mark.asyncio
async def test_api_report_docx(async_client, db):
    _, project_id = await setup_test_project(db)
    r = await async_client.post(
        f"{BASE}/projects/{project_id}/runs", json={"categoria": "BASICA"},
    )
    run_id = r.json()["id"]
    r2 = await async_client.get(f"{BASE}/projects/{project_id}/runs/{run_id}/report/docx")
    assert r2.status_code == 200
    assert r2.content[:2] == b"PK"
