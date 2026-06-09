"""#10 B2 · borrador E-155 (contexto alcance.* + render end-to-end).

Con el catálogo de plantillas seedeado + el DOCX base E-155 (cerrado el hueco
#10 B2), el borrador E-155 SE GENERA al firmar y vuelca el alcance comercial
congelado del contrato (#10 B1 · sistemas/ubicaciones/exclusiones) bajo
``alcance.*``, en vez de fallbacks vacíos.
"""
from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import text

from backend.app.database import set_tenant_context
from backend.app.motors.m13_commercial.services.fase0_bootstrap import (
    build_e155_draft_context,
    generate_e155_draft_best_effort,
)
from backend.tests.conftest import _admin_setup


def test_build_e155_draft_context_shape():
    """#10 B2 · claves bajo alcance.* (alineadas con el .md) + volcado del snapshot."""
    snap = {
        "categoria": "MEDIA", "sistemas": 5, "ubicaciones": 2,
        "exclusiones": ["Sistemas OT industriales", "Apps de terceros no integradas"],
    }
    ctx = build_e155_draft_context(
        client_nombre="Acme SL", client_cif="B12345678",
        client_domicilio="Calle Mayor 1, Madrid", categoria="MEDIA",
        system_frontera="Implantación inicial · alcance completo SGSI",
        alcance_snapshot=snap,
    )
    assert ctx["cliente"]["razon_social"] == "Acme SL"
    assert ctx["cliente"]["nif"] == "B12345678"
    assert ctx["cliente"]["domicilio_social"] == "Calle Mayor 1, Madrid"
    assert ctx["proyecto"]["categoria_ens"] == "MEDIA"
    assert ctx["categorizacion"]["nivel_global"] == "MEDIA"
    assert ctx["proyecto"]["servicio_principal"].startswith("Implantación")
    # alcance.* alineado con el .md + datos REALES del snapshot (no fallbacks).
    alc = ctx["alcance"]
    assert alc["servicios"][0]["nombre"].startswith("Implantación")
    assert "5" in alc["sistemas"][0]["nombre"]        # nº sistemas del snapshot
    assert "2" in alc["sedes"][0]["nombre"]           # nº ubicaciones del snapshot
    exclusiones = [e["elemento"] for e in alc["exclusiones"]]
    assert "Sistemas OT industriales" in exclusiones  # exclusión REAL nombrada
    assert "Apps de terceros no integradas" in exclusiones


def test_build_e155_draft_context_empty_fallbacks():
    """Sin snapshot → alcance.* mínimo (el .md aplica sus fallbacks `else '—'`)."""
    ctx = build_e155_draft_context(
        client_nombre=None, client_cif=None, client_domicilio=None,
        categoria=None, system_frontera=None, alcance_snapshot=None,
    )
    assert ctx["cliente"]["razon_social"] == "Cliente"
    assert "Administración Pública" in ctx["proyecto"]["servicio_principal"]
    alc = ctx["alcance"]
    # Sin snapshot: sin nº de sistemas/sedes y sin exclusiones.
    assert "sistemas" not in alc
    assert "sedes" not in alc
    assert alc["exclusiones"] == []


@pytest.mark.asyncio
async def test_generate_e155_draft_best_effort_generates_with_snapshot(db):
    """#10 B2 cerrado · con templates seedeados + DOCX base + alcance_snapshot
    poblado, el borrador SE GENERA (True) en vez de omitirse en silencio."""
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    snap = {
        "categoria": "MEDIA", "sistemas": 5, "ubicaciones": 2,
        "exclusiones": ["Sistemas OT industriales"],
    }
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:c, 'X', :cif, now())"
        ), {"c": str(client_id), "cif": cif})
        await db.execute(text(
            "INSERT INTO projects (id, client_id, nombre, categoria_objetivo, "
            "fase, created_at) VALUES (:p, :c, 'P', 'MEDIA', 'onboarding', now())"
        ), {"p": str(project_id), "c": str(client_id)})
        await db.execute(text(
            "INSERT INTO contracts (id, project_id, plantilla_id, estado, "
            "alcance_snapshot, created_at) VALUES (:id, :p, 'C-001', 'vigente', "
            "CAST(:snap AS jsonb), now())"
        ), {"id": str(uuid.uuid4()), "p": str(project_id), "snap": json.dumps(snap)})

    await set_tenant_context(db, client_id=client_id, project_id=project_id)
    ok = await generate_e155_draft_best_effort(db, project_id=project_id)
    assert ok is True  # templates seedeados + DOCX base → el borrador se genera
    # La sesión sigue usable (savepoint commit limpio · no aborta la tx).
    assert (await db.execute(text("SELECT 1"))).scalar() == 1
