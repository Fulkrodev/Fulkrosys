"""Tests para FASE C Phase A · M14 workflow_hooks event-driven adenda trigger.

Cubre 3 superficies:
  1. ``template_id_triggers_adenda`` pure function detection
  2. ``maybe_dispatch_adenda_on_step_completed`` hook end-to-end (mocked
     AdendaGenerator) verificando: matched template fires · unmatched skips
     · graceful failure NO raise · audit trail stamped
  3. ``maybe_dispatch_adenda_on_materiality_assessed`` cascade hook
     verificando: MATERIAL + overlay/renewal fires · MATERIAL sin esos
     flags skip · RELEVANT/MINOR skip

Mock strategy:
  - Adenda actually generation requires MinIO + DB + template rendering.
    Para tests rápidos · patch ``AdendaGenerator.generate`` para retornar
    ``AdendaGenerationResult`` sintético + crear ``ProviderAddendum`` row
    explícito · permite verificar audit trail stamping logic real.
  - Verificar invocation count + args coherencia con flags trigger.

LECCION-OPS-027 sostener: usa real ORM columns (provider.name/type/scope/
criticality · client.nombre/cif · NO razon_social/nif).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.m14_providers import Provider, ProviderAddendum
from backend.app.motors.m14_contracts.adenda_generator import (
    AdendaGenerationResult,
    TEMPLATE_CODE,
)
from backend.app.motors.m14_contracts.workflow_hooks import (
    PROVIDER_TEMPLATE_MARKERS,
    _resolve_normativas_for_provider,
    maybe_dispatch_adenda_on_materiality_assessed,
    maybe_dispatch_adenda_on_step_completed,
    template_id_triggers_adenda,
)
from backend.tests.conftest import _admin_setup, setup_test_project


# ════════════════════════════════════════════════════════════════════
# Pure function detection tests
# ════════════════════════════════════════════════════════════════════


class TestTemplateIdDetection:
    """Pure function template_id_triggers_adenda · sin DB."""

    @pytest.mark.parametrize("template_id", [
        "ARCHETYPE_PROVEEDOR_FINANCIERO_DORA_DUAL",  # real existing M21
        "ARCHETYPE_SAAS_ONLY_OP_EXT_CHECKLIST",  # real existing M21
        "ENR_PB_01_SECTOR_PUBLICO_LCSP",  # real existing M21
        "PROVIDER_EVALUATION_COMPLETED",  # future template
        "provider_lifecycle_done",  # lowercase ok (uppercase normalized)
        "ADMIN_MANUAL_TRIGGER_CHECK_PROVIDER",  # admin synthetic marker
    ])
    def test_matches_provider_patterns(self, template_id: str) -> None:
        assert template_id_triggers_adenda(template_id) is True

    @pytest.mark.parametrize("template_id", [
        "PHASE3_BASICA_REVIEW_DIAGNOSIS",
        "PHASE5_BASICA_APPROVE_PDA",
        "DDA_FINAL_SIGNATURE",
        "MAGERIT_ASSET_FREEZE",
        "",  # empty edge
        "SOMETHING_UNRELATED",
    ])
    def test_skips_non_provider_patterns(self, template_id: str) -> None:
        assert template_id_triggers_adenda(template_id) is False

    def test_markers_consistency(self) -> None:
        """Sanity: markers list contiene los esperados sin duplicados."""
        assert "PROVEEDOR" in PROVIDER_TEMPLATE_MARKERS
        assert "PROVIDER" in PROVIDER_TEMPLATE_MARKERS
        assert "LCSP" in PROVIDER_TEMPLATE_MARKERS
        assert "OP_EXT" in PROVIDER_TEMPLATE_MARKERS
        assert len(PROVIDER_TEMPLATE_MARKERS) == len(set(PROVIDER_TEMPLATE_MARKERS))


# ════════════════════════════════════════════════════════════════════
# Normativas resolver tests
# ════════════════════════════════════════════════════════════════════


class TestResolveNormativas:
    """Pure helper _resolve_normativas_for_provider · ADR-046 v3 cross-compliance."""

    def _make_provider(self, *, type: str, criticality: str) -> Provider:
        return Provider(
            project_id=uuid.uuid4(),
            name="Test Provider",
            type=type,
            scope="test scope",
            criticality=criticality,
        )

    def test_cloud_critico_adds_nis2(self) -> None:
        provider = self._make_provider(type="cloud", criticality="CRITICO")
        assert _resolve_normativas_for_provider(provider) == ["ENS", "RGPD", "NIS2"]

    def test_cloud_alto_no_nis2(self) -> None:
        provider = self._make_provider(type="cloud", criticality="ALTO")
        assert _resolve_normativas_for_provider(provider) == ["ENS", "RGPD"]

    def test_saas_critico_no_nis2(self) -> None:
        provider = self._make_provider(type="saas", criticality="CRITICO")
        assert _resolve_normativas_for_provider(provider) == ["ENS", "RGPD"]

    def test_on_prem_medio_only_ens(self) -> None:
        provider = self._make_provider(type="on-prem", criticality="MEDIO")
        assert _resolve_normativas_for_provider(provider) == ["ENS"]

    def test_consultoria_bajo_only_ens(self) -> None:
        provider = self._make_provider(type="consultoria", criticality="BAJO")
        assert _resolve_normativas_for_provider(provider) == ["ENS"]


# ════════════════════════════════════════════════════════════════════
# Hook 1 · maybe_dispatch_adenda_on_step_completed
# ════════════════════════════════════════════════════════════════════


def _make_mock_result(addendum_id: uuid.UUID, code: str) -> AdendaGenerationResult:
    now = datetime.now(timezone.utc)
    return AdendaGenerationResult(
        addendum_id=addendum_id,
        addendum_code=code,
        minio_object_key=f"corpus/addendums/mock/{code}.docx",
        signed_url=f"https://mock-minio/{code}.docx",
        signed_url_expires_at=now,
        normativas_cubiertas=["ENS"],
        docx_size_bytes=20000,
        generated_at=now,
        template_code=TEMPLATE_CODE,
    )


async def _create_provider(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    name: str = "Test Provider",
    type: str = "cloud",
    criticality: str = "CRITICO",
) -> Provider:
    async with _admin_setup(db):
        provider = Provider(
            project_id=project_id,
            name=name,
            type=type,
            scope="test scope",
            criticality=criticality,
        )
        db.add(provider)
        await db.flush()
    return provider


async def _persist_mock_addendum(
    db: AsyncSession,
    project_id: uuid.UUID,
    provider_id: uuid.UUID,
    addendum_code: str,
) -> uuid.UUID:
    """Persist a real ProviderAddendum row para audit trail stamping testing."""
    async with _admin_setup(db):
        addendum = ProviderAddendum(
            project_id=project_id,
            provider_id=provider_id,
            addendum_code=addendum_code,
            normativas_cubiertas=["ENS"],
            generated_from_template_code=TEMPLATE_CODE,
        )
        db.add(addendum)
        await db.flush()
        addendum_id = addendum.id
    return addendum_id


class TestHookOnStepCompleted:

    @pytest.mark.asyncio
    async def test_unmatched_template_returns_empty_no_db_call(
        self, db: AsyncSession,
    ) -> None:
        """Template id NO matching · early-return sin DB lookup providers."""
        _, project_id = await setup_test_project(db)
        result = await maybe_dispatch_adenda_on_step_completed(
            db=db,
            project_id=uuid.UUID(project_id),
            completed_template_id="DDA_FINAL_SIGNATURE",
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_matched_template_no_providers_returns_empty(
        self, db: AsyncSession,
    ) -> None:
        """Template matches · pero project NO tiene providers · skip silencioso."""
        _, project_id_str = await setup_test_project(db)
        result = await maybe_dispatch_adenda_on_step_completed(
            db=db,
            project_id=uuid.UUID(project_id_str),
            completed_template_id="ENR_PB_01_SECTOR_PUBLICO_LCSP",
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_matched_template_with_providers_fires_per_provider(
        self, db: AsyncSession,
    ) -> None:
        """Template matches + 2 providers · genera 1 adenda per provider."""
        _, project_id_str = await setup_test_project(db)
        project_uuid = uuid.UUID(project_id_str)

        p1 = await _create_provider(db, project_uuid, name="Cloud Critico SL")
        p2 = await _create_provider(
            db, project_uuid, name="SaaS Alto SL",
            type="saas", criticality="ALTO",
        )

        # Pre-create addendum rows que AdendaGenerator.generate mock devolvera
        addendum_id_1 = await _persist_mock_addendum(
            db, project_uuid, p1.id, "ADENDA-ENS-2026-9001",
        )
        addendum_id_2 = await _persist_mock_addendum(
            db, project_uuid, p2.id, "ADENDA-ENS-2026-9002",
        )

        mock_gen = AsyncMock()
        mock_gen.side_effect = [
            _make_mock_result(addendum_id_1, "ADENDA-ENS-2026-9001"),
            _make_mock_result(addendum_id_2, "ADENDA-ENS-2026-9002"),
        ]

        with patch(
            "backend.app.motors.m14_contracts.adenda_generator.AdendaGenerator.generate",
            mock_gen,
        ):
            result = await maybe_dispatch_adenda_on_step_completed(
                db=db,
                project_id=project_uuid,
                completed_template_id="ARCHETYPE_PROVEEDOR_FINANCIERO_DORA_DUAL",
            )

        assert mock_gen.await_count == 2
        assert len(result) == 2

        for entry in result:
            assert entry["trigger"] == "workflow_step_completed"
            assert entry["completed_template_id"] == "ARCHETYPE_PROVEEDOR_FINANCIERO_DORA_DUAL"
            assert "addendum_code" in entry
            assert "addendum_id" in entry

    @pytest.mark.asyncio
    async def test_audit_trail_metadata_stamped(
        self, db: AsyncSession,
    ) -> None:
        """Genera adenda + verifica metadata triggers_history contiene entry."""
        _, project_id_str = await setup_test_project(db)
        project_uuid = uuid.UUID(project_id_str)
        provider = await _create_provider(db, project_uuid)

        addendum_id = await _persist_mock_addendum(
            db, project_uuid, provider.id, "ADENDA-ENS-2026-9010",
        )

        mock_gen = AsyncMock(return_value=_make_mock_result(
            addendum_id, "ADENDA-ENS-2026-9010",
        ))

        with patch(
            "backend.app.motors.m14_contracts.adenda_generator.AdendaGenerator.generate",
            mock_gen,
        ):
            await maybe_dispatch_adenda_on_step_completed(
                db=db,
                project_id=project_uuid,
                completed_template_id="ENR_PB_01_SECTOR_PUBLICO_LCSP",
            )

        addendum = await db.get(ProviderAddendum, addendum_id)
        assert addendum is not None
        await db.refresh(addendum)
        meta = dict(addendum.metadata_ or {})

        assert meta["last_trigger"] == "workflow_step_completed"
        assert "last_auto_generated_at" in meta
        history = meta.get("triggers_history") or []
        assert len(history) == 1
        assert history[0]["trigger"] == "workflow_step_completed"
        assert history[0]["completed_template_id"] == "ENR_PB_01_SECTOR_PUBLICO_LCSP"

    @pytest.mark.asyncio
    async def test_graceful_failure_per_provider_continues_chain(
        self, db: AsyncSession,
    ) -> None:
        """Si 1 provider raises · sigue procesando rest sin propagate."""
        _, project_id_str = await setup_test_project(db)
        project_uuid = uuid.UUID(project_id_str)

        p1 = await _create_provider(db, project_uuid, name="P1 fail")
        p2 = await _create_provider(db, project_uuid, name="P2 success")
        addendum_id_2 = await _persist_mock_addendum(
            db, project_uuid, p2.id, "ADENDA-ENS-2026-9020",
        )

        # Mock: primer call raises · segundo ok
        mock_gen = AsyncMock()
        mock_gen.side_effect = [
            RuntimeError("simulated MinIO outage"),
            _make_mock_result(addendum_id_2, "ADENDA-ENS-2026-9020"),
        ]

        with patch(
            "backend.app.motors.m14_contracts.adenda_generator.AdendaGenerator.generate",
            mock_gen,
        ):
            result = await maybe_dispatch_adenda_on_step_completed(
                db=db,
                project_id=project_uuid,
                completed_template_id="ARCHETYPE_SAAS_ONLY_OP_EXT_CHECKLIST",
            )

        # Hook NUNCA raise · solo log warning + skip failing provider
        assert mock_gen.await_count == 2
        # Solo 1 entry succeeded (p2)
        assert len(result) == 1
        assert result[0]["provider_id"] == str(p2.id)


# ════════════════════════════════════════════════════════════════════
# Hook 2 · maybe_dispatch_adenda_on_materiality_assessed
# ════════════════════════════════════════════════════════════════════


class TestHookOnMaterialityAssessed:

    @pytest.mark.asyncio
    async def test_minor_level_skip(self, db: AsyncSession) -> None:
        _, project_id_str = await setup_test_project(db)
        result = await maybe_dispatch_adenda_on_materiality_assessed(
            db=db,
            project_id=uuid.UUID(project_id_str),
            assessment_result={
                "materiality_level": "MINOR",
                "impact_vector": {"overlay": True, "renewal": True},
            },
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_relevant_level_skip(self, db: AsyncSession) -> None:
        _, project_id_str = await setup_test_project(db)
        result = await maybe_dispatch_adenda_on_materiality_assessed(
            db=db,
            project_id=uuid.UUID(project_id_str),
            assessment_result={
                "materiality_level": "RELEVANT",
                "impact_vector": {"overlay": True, "renewal": True},
            },
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_material_no_cascade_flags_skip(self, db: AsyncSession) -> None:
        """MATERIAL pero impact_vector NO incluye overlay/renewal · skip."""
        _, project_id_str = await setup_test_project(db)
        result = await maybe_dispatch_adenda_on_materiality_assessed(
            db=db,
            project_id=uuid.UUID(project_id_str),
            assessment_result={
                "materiality_level": "MATERIAL",
                "impact_vector": {
                    "evidence": True, "document": True, "control": True,
                    "overlay": False, "renewal": False,
                    "roles": False, "risk_analysis": False, "dda": False,
                    "category": False, "extraordinary": False,
                },
            },
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_material_with_overlay_fires(self, db: AsyncSession) -> None:
        _, project_id_str = await setup_test_project(db)
        project_uuid = uuid.UUID(project_id_str)
        provider = await _create_provider(db, project_uuid, name="Material Cascade SL")
        addendum_id = await _persist_mock_addendum(
            db, project_uuid, provider.id, "ADENDA-ENS-2026-9030",
        )

        mock_gen = AsyncMock(return_value=_make_mock_result(
            addendum_id, "ADENDA-ENS-2026-9030",
        ))
        change_id = uuid.uuid4()

        with patch(
            "backend.app.motors.m14_contracts.adenda_generator.AdendaGenerator.generate",
            mock_gen,
        ):
            result = await maybe_dispatch_adenda_on_materiality_assessed(
                db=db,
                project_id=project_uuid,
                assessment_result={
                    "materiality_level": "MATERIAL",
                    "materiality_score": 75,
                    "change_id": change_id,
                    "impact_vector": {
                        "overlay": True,
                        "renewal": False,
                        "evidence": False, "document": False, "control": False,
                        "roles": False, "risk_analysis": False, "dda": False,
                        "category": False, "extraordinary": False,
                    },
                },
            )

        assert len(result) == 1
        assert result[0]["trigger"] == "materiality_material_cascade"
        assert result[0]["materiality_change_id"] == str(change_id)
        assert result[0]["materiality_flags"] == ["overlay"]

    @pytest.mark.asyncio
    async def test_material_with_renewal_and_overlay_both_in_trace(
        self, db: AsyncSession,
    ) -> None:
        _, project_id_str = await setup_test_project(db)
        project_uuid = uuid.UUID(project_id_str)
        provider = await _create_provider(db, project_uuid, name="Renewal+Overlay SL")
        addendum_id = await _persist_mock_addendum(
            db, project_uuid, provider.id, "ADENDA-ENS-2026-9040",
        )

        mock_gen = AsyncMock(return_value=_make_mock_result(
            addendum_id, "ADENDA-ENS-2026-9040",
        ))

        with patch(
            "backend.app.motors.m14_contracts.adenda_generator.AdendaGenerator.generate",
            mock_gen,
        ):
            result = await maybe_dispatch_adenda_on_materiality_assessed(
                db=db,
                project_id=project_uuid,
                assessment_result={
                    "materiality_level": "MATERIAL",
                    "change_id": uuid.uuid4(),
                    "impact_vector": {
                        "overlay": True, "renewal": True,
                        "evidence": False, "document": False, "control": False,
                        "roles": False, "risk_analysis": False, "dda": False,
                        "category": False, "extraordinary": False,
                    },
                },
            )

        assert len(result) == 1
        assert result[0]["materiality_flags"] == ["overlay", "renewal"]

        # Verify metadata stamping cascade
        addendum = await db.get(ProviderAddendum, addendum_id)
        meta = dict(addendum.metadata_ or {})
        assert meta["last_trigger"] == "materiality_material_cascade"
        history = meta["triggers_history"]
        assert history[-1]["materiality_flags_triggered"] == ["overlay", "renewal"]
        assert history[-1]["materiality_level"] == "MATERIAL"
