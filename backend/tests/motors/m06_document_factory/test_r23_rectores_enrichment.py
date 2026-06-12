"""R23 · enriquecimiento de los rectores E-160 (Manual SGSI) + E-170 (Plan Director).

Verifica empíricamente (BD real · docx generado):
- Las tablas de firma incluyen el NOMBRE del firmante (sponsor/RSEG) + fecha
  (antes salían vacías).
- El Plan Director incluye una tabla Capex/Opex con cifras reales derivadas de
  effort_estimates (esfuerzo × tarifa), no el placeholder «pendiente».
- E-codes exactos en la tabla de niveles documentales (E-200..E-235).
"""
from __future__ import annotations

import io
import uuid

from sqlalchemy import text as sa_text

from backend.app.database import set_tenant_context
from backend.app.motors.m06_document_factory.rectores_generator import (
    build_rectores_context,
    generate_manual_sgsi_docx,
    generate_plan_director_docx,
)
from backend.tests.conftest import _admin_setup, setup_test_project


def _docx_text(bio: io.BytesIO) -> str:
    from docx import Document as Docx
    d = Docx(bio)
    parts = [p.text for p in d.paragraphs]
    for t in d.tables:
        for row in t.rows:
            for cell in row.cells:
                parts.append(cell.text)
    return "\n".join(parts)


async def _setup(db, categoria: str = "MEDIA"):
    client_id, project_id = await setup_test_project(db)
    cid, pid = uuid.UUID(client_id), uuid.UUID(project_id)
    sid = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(sa_text(
            "UPDATE projects SET categoria_objetivo=:c WHERE id=:p"
        ), {"c": categoria, "p": project_id})
        await db.execute(sa_text(
            "INSERT INTO systems (id, project_id, nombre, created_at) "
            "VALUES (:s,:p,'Sede electrónica',now())"
        ), {"s": str(sid), "p": project_id})
        await db.execute(sa_text(
            "INSERT INTO categorizations (id, system_id, categoria_resultante, created_at) "
            "VALUES (gen_random_uuid(), :s, :c, now())"
        ), {"s": str(sid), "c": categoria})
        for full_name, role_cat, role_title in [
            ("María Dirección", "sponsor", "Directora General"),
            ("Carlos Seguridad", "responsable_seguridad", "RSEG"),
        ]:
            await db.execute(sa_text(
                "INSERT INTO client_contacts (id, client_id, full_name, email, "
                "role_category, role_title, is_active, created_at) "
                "VALUES (gen_random_uuid(), :c, :n, :e, :rc, :rt, true, now())"
            ), {"c": client_id, "n": full_name, "e": f"{role_cat}@cli.es",
                "rc": role_cat, "rt": role_title})
        for phase, hours, cost in [
            ("categorizacion", 24, 2400), ("dda", 60, 6000),
            ("implantacion", 120, 12000), ("audit", 40, 4000),
            ("retainer_year", 100, 10000),
        ]:
            await db.execute(sa_text(
                "INSERT INTO effort_estimates (id, project_id, phase, "
                "estimated_hours, estimated_cost, created_at) "
                "VALUES (gen_random_uuid(), :p, :ph, :h, :co, now())"
            ), {"p": project_id, "ph": phase, "h": hours, "co": cost})
    await set_tenant_context(db, client_id=cid, project_id=pid)
    return cid, pid


async def test_manual_sgsi_firmantes_and_ecodes(db):
    _, pid = await _setup(db)
    ctx = await build_rectores_context(db, pid)
    assert ctx.sponsor_name == "María Dirección"
    assert ctx.rseg_name == "Carlos Seguridad"
    text = _docx_text(generate_manual_sgsi_docx(ctx))
    # Firmantes poblados en la tabla de aprobación.
    assert "María Dirección" in text
    assert "Carlos Seguridad" in text
    # E-codes exactos.
    assert "E-200..E-235" in text
    assert "E-100..E-126" in text


async def test_plan_director_capex_opex_and_firmantes(db):
    _, pid = await _setup(db)
    ctx = await build_rectores_context(db, pid)
    assert len(ctx.effort_rows) == 5
    text = _docx_text(generate_plan_director_docx(ctx))
    # Capex/Opex con cifras reales (effort × tarifa), no «pendiente».
    assert "Capex" in text and "Opex" in text
    assert "12.000 €" in text  # implantación
    assert "10.000 €/año" in text  # retainer anual
    assert "pendiente de cuantificación" not in text
    # Firmantes poblados.
    assert "María Dirección" in text
    assert "Carlos Seguridad" in text


async def test_plan_director_capex_opex_fallback_without_effort(db):
    client_id, project_id = await setup_test_project(db)
    cid, pid = uuid.UUID(client_id), uuid.UUID(project_id)
    await set_tenant_context(db, client_id=cid, project_id=pid)
    ctx = await build_rectores_context(db, pid)
    assert ctx.effort_rows == []
    text = _docx_text(generate_plan_director_docx(ctx))
    assert "pendiente de cuantificación" in text  # degradación honesta
