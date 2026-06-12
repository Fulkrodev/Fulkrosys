"""R20 · builders BIA/Continuidad/DRP → render E-400/E-401/E-403 con RTO/RPO reales.

Verifica empíricamente (BD real + .docx compilado real):
- build_bia_context / build_continuity_context / build_drp_context producen
  procesos críticos con RTO/RPO/criticidad/estrategias/ubicaciones/proveedores
  desde bia_analyses + cuestionario + system_sites + providers.
- Los E-400/E-401/E-403 renderizan con esos datos (no tablas vacías) y SIN fugas
  Jinja (`{{`/`{%`). Si el loop-table de E-400 colapsa, este test lo caza.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import text as sa_text

from backend.app.database import set_tenant_context
from backend.app.motors.m06_document_factory.continuity_generator import (
    build_bia_context,
    build_continuity_context,
    build_drp_context,
)
from backend.app.motors.m06_document_factory.service import DocumentFactoryService
from backend.app.motors.m19_risk.bia_service import create_bia_entry
from backend.tests.conftest import _admin_setup, setup_test_project


def _docx_text(path: str) -> str:
    from docx import Document as Docx
    d = Docx(path)
    parts = [p.text for p in d.paragraphs]
    for t in d.tables:
        for row in t.rows:
            for cell in row.cells:
                parts.append(cell.text)
    return "\n".join(parts)


async def _setup(db, categoria: str = "ALTA"):
    client_id, project_id = await setup_test_project(db)
    cid, pid = uuid.UUID(client_id), uuid.UUID(project_id)
    sid = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(sa_text(
            "UPDATE projects SET categoria_objetivo=:c WHERE id=:p"
        ), {"c": categoria, "p": project_id})
        await db.execute(sa_text(
            "UPDATE clients SET nombre='Ayuntamiento de Pruebas', cif='P1234567A', "
            "domicilio_fiscal='Plaza Mayor 1, 28001 Madrid' WHERE id=:c"
        ), {"c": client_id})
        await db.execute(sa_text(
            "INSERT INTO systems (id, project_id, nombre, created_at) "
            "VALUES (:s,:p,'Sistema',now())"
        ), {"s": str(sid), "p": project_id})
        await db.execute(sa_text(
            "INSERT INTO system_sites (id, system_id, nombre, tipo, direccion, pais, created_at) "
            "VALUES (gen_random_uuid(), :s, 'CPD Madrid', 'sede_fisica', 'Calle Mayor 1', 'España', now())"
        ), {"s": str(sid)})
        await db.execute(sa_text(
            "INSERT INTO system_sites (id, system_id, nombre, tipo, pais, created_at) "
            "VALUES (gen_random_uuid(), :s, 'AWS eu-west-1', 'region_cloud', 'Irlanda', now())"
        ), {"s": str(sid)})
        await db.execute(sa_text(
            "INSERT INTO providers (id, project_id, name, type, scope, criticality, created_at) "
            "VALUES (gen_random_uuid(), :p, 'AWS', 'cloud', 'Hosting cloud', 'CRITICO', now())"
        ), {"p": project_id})
    await set_tenant_context(db, client_id=cid, project_id=pid)
    # Registra el catálogo de plantillas en la tabla `templates` (el seed no lo hace).
    await DocumentFactoryService(db).load_template_metadata_from_catalog()
    await create_bia_entry(
        db, pid, "Tramitación electrónica", rto_hours=4, rpo_hours=1,
        daily_impact_eur=Decimal("50000"),
    )
    await create_bia_entry(db, pid, "Registro de entrada", rto_hours=24, rpo_hours=4)
    return cid, pid


async def _gen_text(db, pid, template_codigo, ctx) -> str:
    svc = DocumentFactoryService(db)
    result = await svc.generate_document(
        project_id=pid, template_codigo=template_codigo, context=ctx,
        generate_pdf=False, sign=False, generated_by="test",
    )
    return _docx_text(result["docx_path"])


async def test_bia_context_and_render_e400(db):
    _, pid = await _setup(db)
    ctx = await build_bia_context(db, pid)
    by_name = {p["nombre"]: p for p in ctx["bia"]["procesos"]}
    assert by_name["Tramitación electrónica"]["rto"] == "4 horas"
    assert by_name["Tramitación electrónica"]["criticidad"] == "CRÍTICO"
    assert by_name["Registro de entrada"]["criticidad"] == "ALTO"

    text = await _gen_text(db, pid, "E-400", ctx)
    assert "Tramitación electrónica" in text, "E-400 no renderizó los procesos (loop colapsado?)"
    assert "4 horas" in text
    assert "{{" not in text and "{%" not in text


async def test_continuity_render_e401(db):
    _, pid = await _setup(db)
    ctx = await build_continuity_context(db, pid)
    assert len(ctx["procesos_criticos"]) == 2
    assert len(ctx["estrategias"]) == 2
    assert any(u["nombre"] == "AWS eu-west-1" for u in ctx["ubicaciones_alternas"])
    assert ctx["proveedores_criticos"][0]["nombre"] == "AWS"

    text = await _gen_text(db, pid, "E-401", ctx)
    assert "Tramitación electrónica" in text
    assert "Redundancia activa" in text
    assert "{{" not in text and "{%" not in text


async def test_drp_render_e403(db):
    _, pid = await _setup(db)
    ctx = await build_drp_context(db, pid)
    assert len(ctx["sistemas_criticos"]) == 2
    assert ctx["ubicaciones"]["primario"]["nombre"] == "CPD Madrid"
    assert ctx["ubicaciones"]["secundario"]["nombre"] == "AWS eu-west-1"

    text = await _gen_text(db, pid, "E-403", ctx)
    assert "Tramitación electrónica" in text
    assert "CPD Madrid" in text
    assert "{{" not in text and "{%" not in text
