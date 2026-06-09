"""Tests 7 modelos legales DOCX · SAN-C.MB-10.2.

Cobertura: cada generator produce DOCX OOXML válido con datos cliente
+ proyecto + RSEG/DPO + provider (cuando aplica). Catálogo verifica
estructura canónica (códigos C-100..C-160 únicos · 3 con
requires_provider).
"""
from __future__ import annotations

import io
import uuid
import zipfile

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m14_contracts.legal_templates import (
    LEGAL_TEMPLATES,
    LegalContext,
    build_legal_context,
    generate_legal_docx,
    get_legal_template,
    list_legal_templates,
)
from backend.tests.conftest import _admin_setup


def test_legal_templates_count_is_7():
    assert len(list_legal_templates()) == 7


def test_legal_template_codes_are_unique_and_canonical():
    codes = [t.code for t in LEGAL_TEMPLATES]
    assert len(codes) == len(set(codes))
    expected = {"C-100", "C-110", "C-120", "C-130", "C-140", "C-150", "C-160"}
    assert set(codes) == expected


def test_legal_template_requires_provider_subset():
    """Solo C-130 (cadena suministro) · C-150 (DPA) · C-160 (pentesting) requieren provider."""
    requires = {t.slug for t in LEGAL_TEMPLATES if t.requires_provider}
    expected = {
        "clausulas_terceros_ens",
        "dpa_data_processing_agreement",
        "contrato_marco_pentesting",
    }
    assert requires == expected


def test_get_unknown_legal_template_raises():
    with pytest.raises(KeyError, match=r"(?i)legal.*template.*no existe"):
        get_legal_template("inexistente_xxx")


@pytest.mark.parametrize("template", LEGAL_TEMPLATES, ids=lambda t: t.slug)
def test_generate_legal_docx_produces_valid_docx(template):
    """Cada generator produce DOCX OOXML válido con título canónico embebido."""
    ctx = LegalContext(
        project_id=uuid.uuid4(),
        client_name="Acme S.L.",
        client_cif="B12345678",
        client_representante="Carlos Director",
        rseg_name="Ana RSEG",
        dpo_name="Bob DPO",
        provider_name="Partner Pentest S.L.",
        provider_cif="B98765432",
        provider_role="pentester acreditado",
    )
    bio = generate_legal_docx(template.slug, ctx)
    assert isinstance(bio, io.BytesIO)
    data = bio.getvalue()
    assert len(data) > 1500

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        assert "word/document.xml" in zf.namelist()
        doc_xml = zf.read("word/document.xml").decode("utf-8")
        # Título canónico embebido
        first_word = template.title.split()[0]
        assert first_word in doc_xml or template.code in doc_xml
        # Cliente siempre presente
        assert "Acme S.L." in doc_xml


@pytest.mark.asyncio
async def test_build_legal_context_with_real_project(db: AsyncSession):
    """build_legal_context resuelve cliente + RSEG/DPO desde BD."""
    from backend.app.database import set_tenant_context

    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"

    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO clients (id, nombre, cif, sector, created_at) "
                "VALUES (:cid, :nombre, :cif, 'publico', now())"
            ),
            {"cid": str(client_id), "nombre": f"Test Legal {cif}", "cif": cif},
        )
        await db.execute(
            text(
                "INSERT INTO projects (id, client_id, nombre, fase, created_at) "
                "VALUES (:pid, :cid, :nombre, 'pre_venta', now())"
            ),
            {
                "pid": str(project_id),
                "cid": str(client_id),
                "nombre": "Test Legal Project",
            },
        )

    await set_tenant_context(db, client_id=client_id, project_id=project_id)
    ctx = await build_legal_context(db, project_id, provider_name="Test Partner")
    assert ctx.project_id == project_id
    assert "Test Legal" in ctx.client_name
    assert ctx.provider_name == "Test Partner"


@pytest.mark.asyncio
async def test_build_legal_context_brings_domicilio_persona(db: AsyncSession):
    """#9 · build_legal_context trae domicilio_fiscal + persona_contacto (#7.5)."""
    from backend.app.database import set_tenant_context

    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, domicilio_fiscal, "
            "persona_contacto, created_at) "
            "VALUES (:cid, :n, :cif, :dom, :pc, now())"
        ), {"cid": str(client_id), "n": f"Cli {cif}", "cif": cif,
            "dom": "Calle Mayor 1, 28013 Madrid", "pc": "Ana García López"})
        await db.execute(text(
            "INSERT INTO projects (id, client_id, nombre, fase, created_at) "
            "VALUES (:pid, :cid, 'P', 'pre_venta', now())"
        ), {"pid": str(project_id), "cid": str(client_id)})

    await set_tenant_context(db, client_id=client_id, project_id=project_id)
    ctx = await build_legal_context(db, project_id)
    assert ctx.client_domicilio == "Calle Mayor 1, 28013 Madrid"
    assert ctx.client_persona_contacto == "Ana García López"


@pytest.mark.asyncio
async def test_contract_client_prefill_endpoint(async_client, db: AsyncSession):
    """#9 · el endpoint de prefill devuelve los datos del cliente del proyecto."""
    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, domicilio_fiscal, "
            "persona_contacto, created_at) "
            "VALUES (:cid, :n, :cif, :dom, :pc, now())"
        ), {"cid": str(client_id), "n": f"Cli {cif}", "cif": cif,
            "dom": "Av. Test 2", "pc": "Bob Apoderado"})
        await db.execute(text(
            "INSERT INTO projects (id, client_id, nombre, fase, created_at) "
            "VALUES (:pid, :cid, 'P', 'pre_venta', now())"
        ), {"pid": str(project_id), "cid": str(client_id)})

    r = await async_client.get(
        f"/api/v1/contracts/projects/{project_id}/contracts/client-prefill"
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["razon_social"] == f"Cli {cif}"
    assert body["cif"] == cif
    assert body["domicilio_fiscal"] == "Av. Test 2"
    assert body["persona_contacto"] == "Bob Apoderado"


@pytest.mark.asyncio
async def test_generate_contract_freezes_alcance_snapshot(db: AsyncSession):
    """#10 B1 · generate_contract congela el alcance COMERCIAL en alcance_snapshot
    desde Proposal.alcance (categoría + dimensiones · §1 del contrato)."""
    import json as _json

    from backend.app.database import set_tenant_context
    from backend.app.motors.m14_contracts.contract_service import ContractService

    client_id = uuid.uuid4()
    project_id = uuid.uuid4()
    proposal_id = uuid.uuid4()
    lead_id = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:c, :n, :cif, now())"
        ), {"c": str(client_id), "n": f"Cli {cif}", "cif": cif})
        await db.execute(text(
            "INSERT INTO projects (id, client_id, nombre, fase, created_at) "
            "VALUES (:p, :c, 'P', 'onboarding', now())"
        ), {"p": str(project_id), "c": str(client_id)})
        await db.execute(text(
            "INSERT INTO leads (id, empresa_nombre, created_at) "
            "VALUES (:l, 'Cli SL', now())"
        ), {"l": str(lead_id)})
        await db.execute(text(
            "INSERT INTO proposals (id, lead_id, project_id, version, "
            "categoria_objetivo, alcance, importe_total, estado, created_at) "
            "VALUES (:id, :lid, :pid, 1, 'MEDIA', :alc, 11500, 'won', now())"
        ), {"id": str(proposal_id), "lid": str(lead_id), "pid": str(project_id),
            "alc": _json.dumps({"empleados": 30, "sistemas": 5, "ubicaciones": 2})})

    await set_tenant_context(db, client_id=client_id, project_id=project_id)
    c = await ContractService().generate_contract(
        db, proposal_id=proposal_id, project_id=project_id, plantilla_id="C-001",
        cliente_firmante_nombre="Ana", cliente_firmante_cargo="CEO",
    )
    snap = c.alcance_snapshot
    assert snap is not None
    assert snap["categoria"] == "MEDIA"
    assert snap["empleados"] == 30
    assert snap["sistemas"] == 5
    assert snap["importe_total"] == 11500.0


def test_canonical_contract_docx_is_redacted_not_dump():
    """#42 · el DOCX canónico C-100 es un contrato REDACTADO: 8 cláusulas del
    esqueleto + tabla de hitos + alcance §1 + emisor/cliente + complemento A20."""
    ctx = LegalContext(
        project_id=uuid.uuid4(),
        client_name="Guadaltel S.A.",
        client_cif="A41000000",
        client_domicilio="Av. Innovación 1, 41020 Sevilla",
        client_persona_contacto="Ana García López",
        fulkro_name="Marcos Mata García",
        fulkro_cif="77171140E",
        fulkro_domicilio="Paseo de la Dirección 46, 28039 Madrid",
        categoria="MEDIA",
        importe_total=11500.0,
        hitos=[
            {"code": "hito_1_firma", "pct": 50.0, "description": "Firma del contrato", "amount": 5750.0},
            {"code": "hito_5_certificacion", "pct": 50.0, "description": "Certificación", "amount": 5750.0},
        ],
        alcance={"categoria": "MEDIA", "sistemas": 5, "ubicaciones": 2,
                 "empleados": 30, "exclusiones": ["Sistemas OT industriales"]},
        llm_clauses={"clauses_draft": "Cláusula específica: el Cliente facilitará "
                     "acceso a su tenant M365 en modo lectura."},
    )
    data = generate_legal_docx("contrato_prestacion_servicios", ctx).getvalue()
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        xml = zf.read("word/document.xml").decode("utf-8")

    # Esqueleto legal (8 cláusulas estáticas)
    for needle in ["1. Objeto", "2. Plazos y honorarios", "Propiedad intelectual",
                   "Limitación de responsabilidad", "Seguro de RC",
                   "Incompatibilidad implantador"]:
        assert needle in xml, f"falta cláusula: {needle}"
    # §1 alcance comercial (del snapshot)
    assert "categoría ENS MEDIA" in xml
    assert "Sistemas OT industriales" in xml  # exclusión
    # §2 tabla de hitos (importes formateados € español)
    assert "5.750,00" in xml
    assert "Firma del contrato" in xml
    assert "TOTAL" in xml
    # emisor (#44) + cliente (#9)
    assert "77171140E" in xml          # NIF Marcos
    assert "Paseo de la Dirección 46" in xml  # domicilio emisor
    assert "A41000000" in xml          # CIF cliente
    assert "Ana García López" in xml   # persona contacto
    # Agent 20 como COMPLEMENTO (sección 9 · no toca el esqueleto)
    assert "Cláusulas específicas del caso" in xml
    assert "tenant M365" in xml
    # #42 ajustes legales: cláusula de protección de datos (art. 28 RGPD · remite al DPA)
    assert "Protección de datos personales" in xml
    assert "art. 28 RGPD" in xml
    # no concurrencia FUERA del esqueleto (la añade Agent 20 caso a caso)
    assert "No concurrencia" not in xml
    # la fecha del encabezado es de GENERACIÓN, no de firma
    assert "Fecha de generación" in xml
    # NO es un volcado de parámetros
    assert "Parámetros XYZPR" not in xml
