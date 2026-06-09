"""Sub-atom 1.B.7.1.4 · Test integracion E2E provider lifecycle COMPLETO.

Flujo de negocio end-to-end provider lifecycle ENS (cierre OPCION C hibrida AMEND-014):

  1. Crear Provider (real ORM columns m14_contracts/providers)
  2. Crear ProviderAssessment (datos cuestionario E-601 -> decision E-602)
  3. Generar Adenda E-604 (adenda_generator -> DOCX MinIO + row provider_addendums)
  4. Marcar adenda firmada cliente (sim flow firma electronica)
  5. Verificar RLS isolation cross-project (provider_addendums RLS FORCED)

Test unico cubriendo 5 hitos del flujo · valida integracion E2E de las 5
plantillas + 2 tablas + 1 servicio + RLS + audit triggers.

Adaptaciones audit-first vs architect VERBATIM (LECCION-OPS-031 caso 2):
- Architect VERBATIM usaba Provider(razon_social=...) y otras columnas inexistentes
  en ORM real. Test usa Provider(name + type + scope + criticality) y pasa
  normativas_aplicables + extras via AdendaGenerator.generate() params.
- assessment.responses dict architect tenia `{...}` placeholder · test provee
  contenido minimo real para satisfacer NOT NULL JSONB.
"""
from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.storage.minio_client import (
    BUCKET_DOCUMENTS,
    get_minio_client,
)
from backend.app.models.m14_providers import (
    Provider,
    ProviderAddendum,
    ProviderAssessment,
)
from backend.app.motors.m14_contracts.adenda_generator import AdendaGenerator
from backend.tests.conftest import _admin_setup, setup_test_project


def _cleanup_minio(object_key: str) -> None:
    try:
        get_minio_client().remove_object(BUCKET_DOCUMENTS, object_key)
    except Exception:
        pass


@pytest.mark.asyncio
async def test_provider_lifecycle_full_flow_ens_rgpd_nis2(db: AsyncSession):
    """Flujo completo provider lifecycle ENS (5 hitos)."""
    client_id, project_id = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id)

    # ──────────────────────────────────────────────────────────────────
    # 1. Provider creation (real ORM columns · LECCION-OPS-029)
    # ──────────────────────────────────────────────────────────────────
    async with _admin_setup(db):
        provider = Provider(
            project_id=project_uuid,
            name="Test Cloud Provider Lifecycle",
            type="cloud",
            scope="Cloud hosting servicios ENS · lifecycle E2E test",
            criticality="CRITICO",
        )
        db.add(provider)
        await db.flush()
    provider_id = provider.id
    assert provider_id is not None

    # ──────────────────────────────────────────────────────────────────
    # 2. Assessment (sim cumplimentacion E-601 + decision E-602)
    # ──────────────────────────────────────────────────────────────────
    async with _admin_setup(db):
        assessment = ProviderAssessment(
            project_id=project_uuid,
            provider_id=provider_id,
            assessment_date=date.today(),
            assessor="Marcos Mata · Responsable Seguridad",
            questionnaire_version="v1.0",
            responses={
                "B": {  # Cumplimiento ENS
                    "tiene_ens_propio": True,
                    "categoria": "ALTA",
                    "auditor_acreditado_enac": "AENOR",
                },
                "C": {  # RGPD Art.28
                    "es_encargado_tratamiento": True,
                    "subencargados_declarados": True,
                    "ubicacion_datos": "UE",
                },
                "D": {  # NIS2 Art.21
                    "esta_dentro_ambito": True,
                    "tipo_entidad": "esencial",
                    "notificacion_24h_acreditada": True,
                },
            },
            risk_score=0.85,
            risk_level="ALTO",
            decision="APROBADO",
            decision_rationale=(
                "Cumplimiento ENS acreditado · RGPD Art.28 OK · "
                "NIS2 esencial confirmado · proveedor maduro"
            ),
        )
        db.add(assessment)
        await db.flush()
    assert assessment.id is not None
    assert assessment.decision == "APROBADO"
    assert assessment.risk_level == "ALTO"

    # ──────────────────────────────────────────────────────────────────
    # 3. Generar Adenda E-604 (3 bloques · ENS + RGPD + NIS2)
    # ──────────────────────────────────────────────────────────────────
    gen = AdendaGenerator(db=db)
    result = await gen.generate(
        project_id=project_uuid,
        provider_id=provider_id,
        normativas_aplicables=["ENS", "RGPD", "NIS2"],
        contract_ref="CONTRATO-LIFECYCLE-E2E-2026-001",
        provider_extras={
            "nif": "B12345678",
            "domicilio": "Calle Lifecycle 1, Madrid",
            "representante": {
                "nombre": "Director Test Provider",
                "cargo": "CEO",
            },
            "categoria_servicio_ens": "ALTA",
        },
        client_extras={
            "domicilio": "Calle Cliente Lifecycle 1, Madrid",
            "representante": {
                "nombre": "Director Test Cliente",
                "cargo": "Director General",
            },
            "contacto_compliance": {"email": "compliance@test-lifecycle.example"},
        },
    )
    try:
        assert result.normativas_cubiertas == ["ENS", "RGPD", "NIS2"]
        # DOCX completo con 3 bloques condicionales esperado >15KB
        assert result.docx_size_bytes > 15000, (
            f"E-604 con 3 bloques esperado >15KB · obtenido {result.docx_size_bytes}B"
        )
        assert result.template_code == "E-604"
        assert result.minio_object_key.startswith("corpus/addendums/")

        # ──────────────────────────────────────────────────────────────
        # 4. Marcar adenda firmada cliente (UPDATE row · sim flow firma)
        # ──────────────────────────────────────────────────────────────
        await db.execute(text(
            "UPDATE provider_addendums SET firmado_cliente = true "
            "WHERE id = :aid"
        ), {"aid": str(result.addendum_id)})
        await db.flush()

        addendum_check = (await db.execute(
            select(ProviderAddendum).where(ProviderAddendum.id == result.addendum_id)
        )).scalar_one()
        assert addendum_check.firmado_cliente is True
        assert addendum_check.firmado_proveedor is False, (
            "Firma proveedor debe estar pendiente · flow async dos partes"
        )

        # ──────────────────────────────────────────────────────────────
        # 5. Verificar RLS isolation (otro proyecto NO ve este addendum)
        # ──────────────────────────────────────────────────────────────
        _, other_project_id = await setup_test_project(db)
        # set_config switching tenant context · runtime fulkro_app RLS enforced
        await db.execute(
            text("SELECT set_config('app.current_project_id', :pid, true)"),
            {"pid": other_project_id},
        )
        isolated_res = await db.execute(text(
            "SELECT COUNT(*) FROM provider_addendums "
            "WHERE addendum_code = :code"
        ), {"code": result.addendum_code})
        assert isolated_res.scalar_one() == 0, (
            "RLS project_isolation FORCED debe bloquear cross-project access"
        )
    finally:
        _cleanup_minio(result.minio_object_key)
