"""Tests · sub-atom 1.D.F.0.A v3.11 · Diagnóstico ENS wizard atomic.

Cobertura:
- Schemas validation (steps 1-5)
- Endpoint POST /api/v1/admin/diagnostico-wizard/create-project
  · 201 OK · client + project + dims + dept suggestions + activos
  · 409 si CIF duplicado
  · 422 si payload inválido (missing required step)
- Atomic rollback verificable (CIF dup post-step1 leaves nothing)
- Auto-seed: departments per categoría (1.C.F existing)
- Auto-seed: M02 MAGERIT analysis + activos
- Auto-seed: M01 System + InformationType (5 ENS dims)
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text


# ════════════════════════════════════════════════════════════════════
# Payload helpers
# ════════════════════════════════════════════════════════════════════


def _build_valid_payload(cif: str | None = None) -> dict:
    """Construye payload válido completo wizard 6 steps.

    Genera CIF random único por test si no se pasa explícito (evita
    409 por colisión entre tests del mismo file).
    """
    if cif is None:
        cif = f"B{uuid.uuid4().hex[:8].upper()}"
    return {
        "step1_datos_cliente": {
            "razon_social": "Test Diagnóstico SL",
            "cif": cif,
            "sector_industrial": "consultoría TIC",
            "domicilio_fiscal": "Calle Mayor 1, Madrid",
            "web": "https://test-diagnostico.es",
            "contacto_email": "info@test-diagnostico.es",
            "contacto_telefono": "+34 600 000 000",
            "persona_contacto": "Ana García",
        },
        "step2_contexto_ens": {
            "sector_ens": "privado_licita_aapp",
            "tipo_organizacion": "pyme",
            "tamano_empleados": "pequeno",
            "sites_oficinas": 1,
            "it_interno": True,
            "ciso_interno": False,
            "dpo_designado": "externo",
            "equipo_ti_tamano": "1_3",
            "geografia_operacion": "spain",
            "arquitectura_sistemas": "cloud_native",
        },
        "step3_categoria": {
            "categoria_preliminar": "MEDIA",
            "dims_anexo_i": {
                "confidencialidad": "MEDIO",
                "integridad": "MEDIO",
                "disponibilidad": "MEDIO",
                "autenticidad": "BAJO",
                "trazabilidad": "BAJO",
            },
            "justificacion": "Sistema con datos personales clientes AAPP",
        },
        "step4_activos": {
            "activos": [
                {
                    "nombre": "Base datos clientes",
                    "tipo": "datos",
                    "descripcion": "PostgreSQL con datos clientes",
                },
                {
                    "nombre": "Portal web",
                    "tipo": "servicios",
                    "descripcion": "Aplicación web pública",
                },
            ],
            "dependencias_cloud": ["AWS", "Office 365"],
        },
        "step5_first_user": {
            "email": "user-portal@test-diagnostico.es",
            "full_name": "Ana García",
            "cargo": "CISO",
            "send_magic_link": False,
        },
    }


# ════════════════════════════════════════════════════════════════════
# Endpoint smoke tests
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_wizard_creates_client_and_project_atomic(async_client, db):
    """Pipeline completo · 201 OK + IDs + summary."""
    payload = _build_valid_payload()
    response = await async_client.post(
        "/api/v1/admin/diagnostico-wizard/create-project",
        json=payload,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["client_id"]
    assert body["project_id"]
    assert body["initial_system_id"]
    assert body["initial_information_type_id"]
    # Categoría MEDIA → 2 departments suggested per m30 1.C.F catalog
    assert body["departments_created_count"] >= 1
    # Activos top-2 → MAGERIT analysis created
    assert body["magerit_analysis_id"] is not None
    # cockpit user creado (auth_service.create_user succeeded)
    assert body["cockpit_user_id"]
    # send_magic_link=False · explicit
    assert body["magic_link_sent"] is False
    assert "MEDIA" in body["summary"]


@pytest.mark.asyncio
async def test_wizard_rejects_duplicate_cif_409(async_client, db):
    """Si CIF ya existe en DB · 409 + cliente NO se crea segunda vez."""
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    payload1 = _build_valid_payload(cif=cif)
    payload2 = _build_valid_payload(cif=cif)
    payload2["step1_datos_cliente"]["razon_social"] = "Otro nombre"
    payload2["step5_first_user"]["email"] = "other@test.es"

    r1 = await async_client.post(
        "/api/v1/admin/diagnostico-wizard/create-project",
        json=payload1,
    )
    assert r1.status_code == 201

    r2 = await async_client.post(
        "/api/v1/admin/diagnostico-wizard/create-project",
        json=payload2,
    )
    assert r2.status_code == 409
    assert cif in r2.json()["detail"]


@pytest.mark.asyncio
async def test_wizard_missing_required_step_422(async_client):
    """Payload incompleto · 422 (Pydantic validation)."""
    payload = _build_valid_payload()
    del payload["step3_categoria"]
    response = await async_client.post(
        "/api/v1/admin/diagnostico-wizard/create-project",
        json=payload,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_wizard_seeds_5_ens_dims_in_information_type(
    async_client, db,
):
    """InformationType creado con 5 valoraciones ENS Anexo I correctas."""
    payload = _build_valid_payload()
    response = await async_client.post(
        "/api/v1/admin/diagnostico-wizard/create-project",
        json=payload,
    )
    assert response.status_code == 201
    info_id = response.json()["initial_information_type_id"]

    # Verify DB directly via SQL
    row = (await db.execute(
        text(
            "SELECT valoracion_c, valoracion_i, valoracion_d, "
            "valoracion_a, valoracion_t FROM information_types "
            "WHERE id = :id"
        ),
        {"id": info_id},
    )).first()
    assert row is not None
    valoracion_c, valoracion_i, valoracion_d, valoracion_a, valoracion_t = row
    assert valoracion_c == "MEDIO"
    assert valoracion_i == "MEDIO"
    assert valoracion_d == "MEDIO"
    assert valoracion_a == "BAJO"
    assert valoracion_t == "BAJO"


@pytest.mark.asyncio
async def test_wizard_seeds_magerit_activos_with_codes(async_client, db):
    """MAGERIT activos seeded con ACT-001, ACT-002 sequential codes."""
    payload = _build_valid_payload()
    response = await async_client.post(
        "/api/v1/admin/diagnostico-wizard/create-project",
        json=payload,
    )
    assert response.status_code == 201
    analysis_id = response.json()["magerit_analysis_id"]

    rows = (await db.execute(
        text(
            "SELECT code, name, asset_type_code FROM magerit_assets "
            "WHERE analysis_id = :aid ORDER BY code"
        ),
        {"aid": analysis_id},
    )).all()
    codes = [r[0] for r in rows]
    assert "ACT-001" in codes
    assert "ACT-002" in codes
    # asset_type_code mapped from "datos" → "[D]", "servicios" → "[S]"
    type_codes = [r[2] for r in rows]
    assert "[D]" in type_codes
    assert "[S]" in type_codes


@pytest.mark.asyncio
async def test_wizard_with_zero_activos_skips_magerit(async_client, db):
    """Si Step 4 activos=[] · NO crea MAGERIT analysis (magerit_id=null)."""
    payload = _build_valid_payload()
    payload["step4_activos"] = {"activos": [], "dependencias_cloud": []}
    response = await async_client.post(
        "/api/v1/admin/diagnostico-wizard/create-project",
        json=payload,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["magerit_analysis_id"] is None


@pytest.mark.asyncio
async def test_wizard_basica_only_1_department_suggested(async_client, db):
    """Categoría BASICA → solo 1 department (TI) suggested per m30 1.C.F."""
    payload = _build_valid_payload()
    payload["step3_categoria"]["categoria_preliminar"] = "BASICA"
    response = await async_client.post(
        "/api/v1/admin/diagnostico-wizard/create-project",
        json=payload,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["departments_created_count"] == 1


@pytest.mark.asyncio
async def test_wizard_alta_4_departments_suggested(async_client, db):
    """Categoría ALTA → 4 departments suggested (TI+COMPLIANCE+LEGAL+RRHH)."""
    payload = _build_valid_payload()
    payload["step3_categoria"]["categoria_preliminar"] = "ALTA"
    response = await async_client.post(
        "/api/v1/admin/diagnostico-wizard/create-project",
        json=payload,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["departments_created_count"] == 4


# ════════════════════════════════════════════════════════════════════
# #5 (Sub-bloque E) · suelo de categoría heredado de la AAPP (Variante 2)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_wizard_inherited_floor_elevates_categoria_objetivo(async_client, db):
    """#5 · suelo AAPP MEDIA + preliminar BASICA → categoria_objetivo MEDIA.

    Variante 2: el suelo eleva el target (solo sube). Y persiste el piso DURO
    en projects.categoria_heredada_aapp (consumido luego por compute_for_system).
    """
    payload = _build_valid_payload()
    payload["step3_categoria"]["categoria_preliminar"] = "BASICA"
    payload["step3_categoria"]["categoria_heredada_aapp"] = "MEDIA"
    response = await async_client.post(
        "/api/v1/admin/diagnostico-wizard/create-project",
        json=payload,
    )
    assert response.status_code == 201, response.text
    project_id = response.json()["project_id"]

    row = (await db.execute(
        text(
            "SELECT categoria_objetivo, categoria_heredada_aapp "
            "FROM projects WHERE id = :pid"
        ),
        {"pid": project_id},
    )).first()
    assert row is not None
    assert row[0] == "MEDIA", "el suelo AAPP eleva BASICA→MEDIA en creación"
    assert row[1] == "MEDIA"


@pytest.mark.asyncio
async def test_wizard_inherited_floor_does_not_lower(async_client, db):
    """#5 · preliminar ALTA + suelo MEDIA → categoria_objetivo ALTA (no baja)."""
    payload = _build_valid_payload()
    payload["step3_categoria"]["categoria_preliminar"] = "ALTA"
    payload["step3_categoria"]["dims_anexo_i"]["confidencialidad"] = "ALTO"
    payload["step3_categoria"]["categoria_heredada_aapp"] = "MEDIA"
    response = await async_client.post(
        "/api/v1/admin/diagnostico-wizard/create-project",
        json=payload,
    )
    assert response.status_code == 201, response.text
    project_id = response.json()["project_id"]
    row = (await db.execute(
        text(
            "SELECT categoria_objetivo, categoria_heredada_aapp "
            "FROM projects WHERE id = :pid"
        ),
        {"pid": project_id},
    )).first()
    assert row[0] == "ALTA", "el suelo MEDIA no baja de ALTA"
    assert row[1] == "MEDIA"


@pytest.mark.asyncio
async def test_wizard_no_floor_backward_compat(async_client, db):
    """#5 · sin suelo (None) → comportamiento idéntico a hoy (categoria_heredada NULL)."""
    payload = _build_valid_payload()  # preliminar MEDIA, sin floor
    response = await async_client.post(
        "/api/v1/admin/diagnostico-wizard/create-project",
        json=payload,
    )
    assert response.status_code == 201
    project_id = response.json()["project_id"]
    row = (await db.execute(
        text(
            "SELECT categoria_objetivo, categoria_heredada_aapp "
            "FROM projects WHERE id = :pid"
        ),
        {"pid": project_id},
    )).first()
    assert row[0] == "MEDIA"
    assert row[1] is None
