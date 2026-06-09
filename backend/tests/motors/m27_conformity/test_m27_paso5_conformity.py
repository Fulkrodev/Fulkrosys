"""Tests M27 Paso 5 — Conformity Lifecycle persistido.

Cubre:
- Materiality tree + score + threshold
- initialize_conformity_route BASICA vs MEDIA + overlay hints
- basic_declaration (firma + published_url)
- enac_certification prepare
- material_change + extraordinary_audit auto-triggered
- recategorization
- role_topology con 5 patrones + excepciones CCN-STIC 801
- role_exception_memo
- renewal_campaign auto 21 meses
- pce_overlay catalog + 6 overlays cargables
- Adapters: PILAR mgr XML, INES XLSX, CLARA ingester
- TEST-PCE-01 Cloud Azure E2E
- TEST-PCE-02 µCeENS Ayuntamiento E2E
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

import pytest
from openpyxl import load_workbook
from sqlalchemy import select, text as sa_text

from backend.app.database import set_tenant_context
from backend.app.models.conformity_lifecycle import (
    EffortEstimateRow,
    ExtraordinaryAuditRow,
)
from backend.app.motors.m27_conformity.adapters.clara_ingester import (
    CLARA_TO_ENS_MAP,
    ingest_clara_output,
    parse_clara_xml,
)
from backend.app.motors.m27_conformity.adapters.ines_adapter import (
    generate_ines_snapshot,
)
from backend.app.motors.m27_conformity.adapters.pilar_adapter import (
    generate_mgr_file,
)
from backend.app.motors.m27_conformity.catalogs import (
    OVERLAY_TYPES,
    get_extra_measures,
    load_all_catalogs,
    load_overlay_catalog,
    suggest_overlays_by_hints,
)
from backend.app.motors.m27_conformity.conformity_service_paso5 import (
    ConformityError,
    ConformityServicePaso5,
    MATERIALITY_QUESTIONS,
    MATERIALITY_THRESHOLD,
    compute_materiality_score,
)
from backend.tests.conftest import _admin_setup, setup_test_project


# ══════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════


async def _setup_project(db, *, categoria: str = "MEDIA"):
    client_id, project_id = await setup_test_project(db)
    cid = uuid.UUID(client_id)
    pid = uuid.UUID(project_id)
    async with _admin_setup(db):
        await db.execute(sa_text(
            "UPDATE projects SET categoria_objetivo = :cat "
            "WHERE id = :pid"
        ), {"pid": project_id, "cat": categoria})
    await set_tenant_context(db, client_id=cid, project_id=pid)
    return cid, pid


async def _setup_project_with_system(db, *, categoria: str = "MEDIA"):
    cid, pid = await _setup_project(db, categoria=categoria)
    async with _admin_setup(db):
        sid = uuid.uuid4()
        await db.execute(sa_text(
            "INSERT INTO systems (id, project_id, nombre, created_at) "
            "VALUES (:sid, :pid, 'Sistema Test', now())"
        ), {"sid": str(sid), "pid": str(pid)})
        await db.execute(sa_text(
            "INSERT INTO information_types (id, system_id, nombre, "
            "valoracion_d, valoracion_i, valoracion_c, valoracion_a, "
            "valoracion_t, created_at) "
            "VALUES (gen_random_uuid(), :sid, 'Datos operativos', "
            "'MEDIO', 'MEDIO', 'BAJO', 'MEDIO', 'BAJO', now())"
        ), {"sid": str(sid)})
    return cid, pid, sid


# ══════════════════════════════════════════════════════════════════════
# Materiality tree
# ══════════════════════════════════════════════════════════════════════


class TestMaterialityTree:
    def test_ten_questions_defined(self):
        assert len(MATERIALITY_QUESTIONS) == 10

    def test_total_weights_exceed_threshold(self):
        total = sum(w for _, w, _ in MATERIALITY_QUESTIONS)
        assert total >= 1.0

    def test_score_low_under_threshold(self):
        answers = {"permanent_change": True}
        score = compute_materiality_score(answers)
        assert score < MATERIALITY_THRESHOLD

    def test_score_high_over_threshold(self):
        answers = {
            "affects_critical_systems": True,
            "outsourced_abroad": True,
            "changes_categorization": True,
        }
        score = compute_materiality_score(answers)
        assert score >= MATERIALITY_THRESHOLD

    def test_score_capped_at_1(self):
        answers = {k: True for k, _, _ in MATERIALITY_QUESTIONS}
        assert compute_materiality_score(answers) <= 1.0

    def test_score_edge_exactly_threshold(self):
        # affects_critical(0.25) + changes_categorization(0.30) + affects_personal(0.20) = 0.75
        # but we want exactly threshold: critical(0.25) + permanent(0.10) + personal(0.20) + users(0.10) = 0.65 (>=0.6)
        answers = {
            "affects_critical_systems": True,  # 0.25
            "affects_personal_data_high": True,  # 0.20
            "large_scale_users": True,  # 0.10
            "permanent_change": True,  # 0.10
        }
        score = compute_materiality_score(answers)
        assert score >= MATERIALITY_THRESHOLD  # 0.65 >= 0.6


# ══════════════════════════════════════════════════════════════════════
# PCE catalogs
# ══════════════════════════════════════════════════════════════════════


class TestPCECatalogs:
    # Sub-lote 1.B.8.A AMEND-016 v2: OVERLAY_TYPES reducido de 6 a 3 (cloud_*
    # only) · uceens_* scope-out (LECCION-OPS-032 target empresa privada
    # licitando AAPP).
    def test_three_overlays_registered(self):
        assert len(OVERLAY_TYPES) == 3

    def test_all_catalogs_loadable(self):
        catalogs = load_all_catalogs()
        assert len(catalogs) == 3
        for t, c in catalogs.items():
            assert c["overlay_type"] == t
            assert c.get("extra_measures")

    def test_cloud_azure_has_15_measures(self):
        catalog = load_overlay_catalog("cloud_azure_es")
        assert len(catalog["extra_measures"]) == 15

    def test_suggest_overlay_from_hints_azure(self):
        matches = suggest_overlays_by_hints(["Usamos Azure AD", "Microsoft 365"])
        assert "cloud_azure_es" in matches

    # Removed test_suggest_overlay_from_hints_ayuntamiento (uceens_* scope-out
    # post 1.B.8.A AMEND-016 v2).

    def test_suggest_overlay_empty_hints(self):
        assert suggest_overlays_by_hints([]) == []

    def test_get_extra_measures_by_category(self):
        basica = get_extra_measures("cloud_azure_es", min_category="BASICA")
        media = get_extra_measures("cloud_azure_es", min_category="MEDIA")
        assert len(basica) < len(media)


# ══════════════════════════════════════════════════════════════════════
# Route initialization
# ══════════════════════════════════════════════════════════════════════


class TestRouteInitialization:
    @pytest.mark.asyncio
    async def test_init_route_basica_creates_declaracion(self, db):
        _, pid = await _setup_project(db, categoria="BASICA")
        svc = ConformityServicePaso5()
        route = await svc.initialize_conformity_route(db, pid)
        assert route.route_type == "declaracion_basica"
        assert route.expiration_date is None

    @pytest.mark.asyncio
    async def test_init_route_media_creates_certificacion(self, db):
        _, pid = await _setup_project(db, categoria="MEDIA")
        svc = ConformityServicePaso5()
        route = await svc.initialize_conformity_route(db, pid)
        assert route.route_type == "certificacion_enac"
        assert route.expiration_date is not None

    @pytest.mark.asyncio
    async def test_init_route_generates_effort_estimates(self, db):
        _, pid = await _setup_project(db, categoria="MEDIA")
        await ConformityServicePaso5().initialize_conformity_route(db, pid)
        res = await db.execute(
            select(EffortEstimateRow).where(EffortEstimateRow.project_id == pid)
        )
        estimates = list(res.scalars().all())
        assert len(estimates) >= 4  # categorizacion, dda, implantacion, audit, retainer

    @pytest.mark.asyncio
    async def test_init_route_duplicate_raises(self, db):
        _, pid = await _setup_project(db, categoria="MEDIA")
        svc = ConformityServicePaso5()
        await svc.initialize_conformity_route(db, pid)
        with pytest.raises(ConformityError, match="activa ya existe"):
            await svc.initialize_conformity_route(db, pid)

    @pytest.mark.asyncio
    async def test_init_route_records_overlay_hints(self, db):
        _, pid = await _setup_project(db, categoria="MEDIA")
        svc = ConformityServicePaso5()
        route = await svc.initialize_conformity_route(
            db, pid, detected_overlay_hints=["Microsoft 365", "Azure AD"],
        )
        assert "cloud_azure_es" in (route.metadata_jsonb or {}).get(
            "suggested_overlays", [],
        )


# ══════════════════════════════════════════════════════════════════════
# Basic Declaration
# ══════════════════════════════════════════════════════════════════════


class TestBasicDeclaration:
    @pytest.mark.asyncio
    async def test_basic_declaration_generates_signed_hash(self, db):
        _, pid = await _setup_project(db, categoria="BASICA")
        svc = ConformityServicePaso5()
        await svc.initialize_conformity_route(db, pid)
        # #41 (FRENTE D): el cierre BÁSICA exige la autoevaluación 808.
        rep_id = uuid.uuid4()
        await db.execute(sa_text(
            "INSERT INTO documents (id, project_id, nombre, template_codigo, "
            "created_at, updated_at) VALUES (:id, :pid, "
            "'E-808C Autoevaluación', 'E-808C', now(), now())"
        ), {"id": str(rep_id), "pid": str(pid)})
        decl = await svc.process_basic_declaration(
            db, pid,
            responsible_person_name="RSEG Test",
            responsible_person_email="rseg@test.es",
            published_url="https://test.es/ens-declaration",
            self_assessment_report_id=rep_id,
        )
        assert decl.signed_hash is not None
        assert len(decl.signed_hash) == 64
        assert decl.status == "signed"

    @pytest.mark.asyncio
    async def test_basic_declaration_wrong_route_type_rejected(self, db):
        _, pid = await _setup_project(db, categoria="MEDIA")
        svc = ConformityServicePaso5()
        await svc.initialize_conformity_route(db, pid)
        with pytest.raises(ConformityError, match="declaracion_basica"):
            await svc.process_basic_declaration(
                db, pid,
                responsible_person_name="x", responsible_person_email="a@b.c",
            )

    @pytest.mark.asyncio
    async def test_basic_declaration_publish_requires_self_assessment(self, db):
        """#41 (FRENTE D): publicar/firmar el cierre BÁSICA sin la autoevaluación
        808 (self_assessment_report_id) → ConformityError."""
        _, pid = await _setup_project(db, categoria="BASICA")
        svc = ConformityServicePaso5()
        await svc.initialize_conformity_route(db, pid)
        with pytest.raises(ConformityError, match="808"):
            await svc.process_basic_declaration(
                db, pid,
                responsible_person_name="Dirección",
                responsible_person_email="direccion@cliente.es",
                published_url="https://cliente.es/ens",
                self_assessment_report_id=None,
            )

    @pytest.mark.asyncio
    async def test_basic_declaration_signed_by_direccion_dedicated_type(self, db):
        """#44 (FRENTE D): la Declaración BÁSICA se etiqueta con el SignableType
        dedicado y firmante=DIRECCIÓN (no RSeg) en el payload de submission."""
        from backend.app.motors.m05_signing.signable_types import (
            REQUIRES_STEP_UP_OTP,
            SIGNABLE_TYPES,
        )

        assert "declaracion_conformidad_basica" in SIGNABLE_TYPES
        assert "declaracion_conformidad_basica" in REQUIRES_STEP_UP_OTP

        _, pid = await _setup_project(db, categoria="BASICA")
        svc = ConformityServicePaso5()
        await svc.initialize_conformity_route(db, pid)
        rep_id = uuid.uuid4()
        await db.execute(sa_text(
            "INSERT INTO documents (id, project_id, nombre, template_codigo, "
            "created_at, updated_at) VALUES (:id, :pid, "
            "'E-808C Autoevaluación', 'E-808C', now(), now())"
        ), {"id": str(rep_id), "pid": str(pid)})
        decl = await svc.process_basic_declaration(
            db, pid,
            responsible_person_name="Dirección General",
            responsible_person_email="direccion@cliente.es",
            published_url="https://cliente.es/ens",
            self_assessment_report_id=rep_id,
        )
        assert decl.self_assessment_report_id == rep_id
        # payload de submission etiquetado con el tipo dedicado + Dirección
        row = (await db.execute(sa_text(
            "SELECT submission_payload_jsonb FROM conformity_submissions "
            "WHERE project_id = :pid ORDER BY created_at DESC LIMIT 1"
        ), {"pid": str(pid)})).first()
        payload = row[0] if isinstance(row[0], dict) else __import__("json").loads(row[0])
        assert payload["signable_type"] == "declaracion_conformidad_basica"
        assert payload["signer_role"] == "direccion"


# ══════════════════════════════════════════════════════════════════════
# ENAC Certification
# ══════════════════════════════════════════════════════════════════════


class TestEnacCertification:
    @pytest.mark.asyncio
    async def test_prepare_enac_creates_submission(self, db):
        _, pid = await _setup_project(db, categoria="ALTA")
        svc = ConformityServicePaso5()
        await svc.initialize_conformity_route(db, pid)
        sub = await svc.prepare_enac_certification(
            db, pid, auditor_entity="AENOR S.A.U. (ENAC-001)",
        )
        assert sub.submission_type == "enac_dossier"
        assert sub.status == "submitted"


# ══════════════════════════════════════════════════════════════════════
# Material changes + recategorization
# ══════════════════════════════════════════════════════════════════════


class TestMaterialChanges:
    @pytest.mark.asyncio
    async def test_material_change_low_score_not_material(self, db):
        _, pid = await _setup_project(db)
        svc = ConformityServicePaso5()
        mc = await svc.detect_material_change(
            db, pid,
            change_type="location_change",
            description="Nueva sede Barcelona sin impacto en sistemas productivos",
            answers={"permanent_change": True},
        )
        assert mc.is_material is False
        assert mc.triggered_extraordinary_audit is False

    @pytest.mark.asyncio
    async def test_material_change_high_score_triggers_audit(self, db):
        _, pid = await _setup_project(db)
        svc = ConformityServicePaso5()
        mc = await svc.detect_material_change(
            db, pid,
            change_type="outsourcing",
            description="Externalizacion completa de hosting a cloud externo",
            answers={
                "affects_critical_systems": True,
                "outsourced_abroad": True,
                "new_attack_surface": True,
                "permanent_change": True,
            },
        )
        assert mc.is_material is True
        assert mc.triggered_extraordinary_audit is True
        assert mc.extraordinary_audit_id is not None
        # Verify audit created
        res = await db.execute(
            select(ExtraordinaryAuditRow).where(
                ExtraordinaryAuditRow.project_id == pid,
            )
        )
        audits = list(res.scalars().all())
        assert len(audits) == 1
        assert audits[0].scheduled_for > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_recategorization_basica_to_media(self, db):
        _, pid = await _setup_project(db)
        svc = ConformityServicePaso5()
        row = await svc.create_recategorization(
            db, pid,
            old_category="BASICA", new_category="MEDIA",
            approved_by="marcos",
        )
        assert row.status == "approved"
        assert row.old_category == "BASICA"
        assert row.new_category == "MEDIA"

    @pytest.mark.asyncio
    async def test_recategorization_invalid_category_raises(self, db):
        _, pid = await _setup_project(db)
        svc = ConformityServicePaso5()
        with pytest.raises(ConformityError, match="invalida"):
            await svc.create_recategorization(
                db, pid, old_category="LOW", new_category="HIGH",
            )


# ══════════════════════════════════════════════════════════════════════
# PCE overlay application
# ══════════════════════════════════════════════════════════════════════


class TestOverlayApplication:
    @pytest.mark.asyncio
    async def test_apply_cloud_azure_overlay(self, db):
        _, pid = await _setup_project(db, categoria="MEDIA")
        svc = ConformityServicePaso5()
        row = await svc.apply_pce_overlay(
            db, pid, overlay_type="cloud_azure_es",
        )
        assert row.overlay_type == "cloud_azure_es"
        assert (row.extra_measures_jsonb or {}).get("count", 0) > 0

    # Removed test_apply_uceens_ayuntamiento_overlay (uceens_* scope-out
    # post 1.B.8.A AMEND-016 v2 · LECCION-OPS-032).

    @pytest.mark.asyncio
    async def test_apply_invalid_overlay_raises(self, db):
        _, pid = await _setup_project(db, categoria="MEDIA")
        svc = ConformityServicePaso5()
        with pytest.raises(ConformityError, match="overlay_type invalido"):
            await svc.apply_pce_overlay(db, pid, overlay_type="invalid_overlay")


# ══════════════════════════════════════════════════════════════════════
# Role topology
# ══════════════════════════════════════════════════════════════════════


class TestRoleTopology:
    @pytest.mark.asyncio
    async def test_pattern_startup_unipersonal(self, db):
        _, pid = await _setup_project(db)
        svc = ConformityServicePaso5()
        topo = await svc.generate_role_topology(
            db, pid, total_persons=1,
            roles_assigned={
                "rseg": "P1", "responsable_sistema": "P1",
                "responsable_informacion": "P1",
            },
        )
        assert topo.pattern == "startup_unipersonal"
        assert topo.exceptions_count == 3  # 3 conflicts

    @pytest.mark.asyncio
    async def test_pattern_pyme_basica(self, db):
        _, pid = await _setup_project(db)
        svc = ConformityServicePaso5()
        topo = await svc.generate_role_topology(
            db, pid, total_persons=8,
            roles_assigned={
                "rseg": "Alice", "responsable_sistema": "Bob",
                "responsable_informacion": "Carol",
            },
        )
        assert topo.pattern == "pyme_basica"
        assert topo.exceptions_count == 0

    @pytest.mark.asyncio
    async def test_pattern_pyme_media(self, db):
        _, pid = await _setup_project(db)
        topo = await ConformityServicePaso5().generate_role_topology(
            db, pid, total_persons=30,
            roles_assigned={"rseg": "x", "responsable_informacion": "y"},
        )
        assert topo.pattern == "pyme_media"

    @pytest.mark.asyncio
    async def test_pattern_empresa_grande(self, db):
        _, pid = await _setup_project(db)
        topo = await ConformityServicePaso5().generate_role_topology(
            db, pid, total_persons=500,
            roles_assigned={"rseg": "x"},
        )
        assert topo.pattern == "empresa_grande"

    @pytest.mark.asyncio
    async def test_pattern_admin_publica_from_sector(self, db):
        _, pid = await _setup_project(db)
        topo = await ConformityServicePaso5().generate_role_topology(
            db, pid, total_persons=100,
            roles_assigned={"rseg": "x"},
            sector="Ayuntamiento de Lleida",
        )
        assert topo.pattern == "admin_publica"

    @pytest.mark.asyncio
    async def test_role_exception_memo_creation(self, db):
        _, pid = await _setup_project(db)
        svc = ConformityServicePaso5()
        topo = await svc.generate_role_topology(
            db, pid, total_persons=1,
            roles_assigned={"rseg": "X", "responsable_informacion": "X"},
        )
        memo = await svc.create_role_exception_memo(
            db, pid,
            role_topology_id=topo.id,
            exception_description="RSEG = Responsable Informacion",
            justification="Empresa de 1 persona. Unica alternativa viable.",
            compensating_controls="Supervision externa trimestral + auditoria anual",
            approved_by="marcos",
        )
        assert memo.role_topology_id == topo.id


# ══════════════════════════════════════════════════════════════════════
# Renewal campaign
# ══════════════════════════════════════════════════════════════════════


class TestRenewalCampaign:
    @pytest.mark.asyncio
    async def test_renewal_auto_triggers_campaign(self, db):
        _, pid = await _setup_project(db, categoria="MEDIA")
        svc = ConformityServicePaso5()
        await svc.initialize_conformity_route(db, pid)
        camp = await svc.trigger_renewal_campaign(db, pid, auto_triggered=True)
        assert camp.campaign_type == "recertification_bianual"
        assert camp.auto_triggered is True
        # scheduled_for debe ser futuro
        assert camp.scheduled_for > datetime.now(timezone.utc)


# ══════════════════════════════════════════════════════════════════════
# CLARA ingester
# ══════════════════════════════════════════════════════════════════════


SAMPLE_CLARA_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<ClaraReport host="SRV-01" date="2026-04-20">
  <check id="CLARA-W-PWD-01" status="PASS">Password complexity OK</check>
  <check id="CLARA-W-FW-01" status="FAIL">Windows Firewall off</check>
  <check id="CLARA-L-SSH-01" status="PASS">SSH hardening OK</check>
</ClaraReport>"""


class TestClaraIngester:
    def test_parse_clara_xml(self):
        results = parse_clara_xml(SAMPLE_CLARA_XML)
        assert len(results) == 3
        assert any(r["clara_id"] == "CLARA-W-PWD-01" for r in results)

    def test_clara_map_covers_multiple_ens_measures(self):
        assert "op.acc.3" in CLARA_TO_ENS_MAP["CLARA-W-PWD-01"]
        assert "mp.com.2" in CLARA_TO_ENS_MAP["CLARA-W-FW-01"]

    @pytest.mark.asyncio
    async def test_ingest_creates_evidences(self, db):
        _, pid = await _setup_project(db)
        result = await ingest_clara_output(
            db, pid, content=SAMPLE_CLARA_XML,
        )
        assert result["parsed_count"] == 3
        assert result["evidences_created_count"] >= 3
        assert "op.acc.3" in result["ens_measures_touched"]


# ══════════════════════════════════════════════════════════════════════
# PILAR adapter
# ══════════════════════════════════════════════════════════════════════


class TestPilarAdapter:
    @pytest.mark.asyncio
    async def test_generate_mgr_file_xml(self, db):
        _, pid, _ = await _setup_project_with_system(db)
        artifact = await generate_mgr_file(db, pid)
        assert artifact["tool"] == "PILAR"
        assert artifact["artifact_content"].startswith(b"<?xml")
        assert b"PilarImport" in artifact["artifact_content"]
        assert b"Activos" in artifact["artifact_content"]
        # Hash deterministico sha256
        recalc = hashlib.sha256(artifact["artifact_content"]).hexdigest()
        assert recalc == artifact["artifact_hash"]


# ══════════════════════════════════════════════════════════════════════
# INES adapter
# ══════════════════════════════════════════════════════════════════════


class TestInesAdapter:
    @pytest.mark.asyncio
    async def test_generate_ines_xlsx_has_5_sheets(self, db):
        _, pid, _ = await _setup_project_with_system(db)
        artifact = await generate_ines_snapshot(db, pid, year=2026)
        assert artifact["tool"] == "INES"
        assert len(artifact["sheets"]) == 5
        # Parse the XLSX
        import io
        wb = load_workbook(io.BytesIO(artifact["artifact_content"]))
        sheet_names = set(wb.sheetnames)
        assert "01_Identificacion" in sheet_names
        assert "02_Activos" in sheet_names
        assert "05_Resumen" in sheet_names


# ══════════════════════════════════════════════════════════════════════
# TEST-PCE-01 and TEST-PCE-02 (E2E)
# ══════════════════════════════════════════════════════════════════════


class TestPCEEndToEnd:
    @pytest.mark.asyncio
    async def test_pce_01_cloud_azure_e2e(self, db):
        """Cliente MEDIA con hints Azure -> ruta certif + overlay azure
        aplicado con 15 medidas."""
        _, pid = await _setup_project(db, categoria="MEDIA")
        svc = ConformityServicePaso5()
        route = await svc.initialize_conformity_route(
            db, pid, detected_overlay_hints=["Azure AD", "Microsoft 365"],
        )
        assert route.route_type == "certificacion_enac"
        assert "cloud_azure_es" in (route.metadata_jsonb or {}).get(
            "suggested_overlays", [],
        )

        overlay = await svc.apply_pce_overlay(
            db, pid, overlay_type="cloud_azure_es",
        )
        measures = (overlay.extra_measures_jsonb or {}).get("measures", [])
        # MEDIA -> BASICA + MEDIA (no ALTA)
        assert len(measures) >= 8  # at least basicas + medias
        codes = [m["code"] for m in measures]
        assert any("pce-az" in c for c in codes)

    # Removed test_pce_02_uceens_ayuntamiento_e2e (uceens_* scope-out
    # post 1.B.8.A AMEND-016 v2 · LECCION-OPS-032).


# ══════════════════════════════════════════════════════════════════════
# Conformity status aggregator
# ══════════════════════════════════════════════════════════════════════


class TestConformityStatus:
    @pytest.mark.asyncio
    async def test_status_includes_counts(self, db):
        _, pid = await _setup_project(db, categoria="MEDIA")
        svc = ConformityServicePaso5()
        await svc.initialize_conformity_route(db, pid)
        await svc.detect_material_change(
            db, pid,
            change_type="legal_change",
            description="Nueva regulacion GDPR",
            answers={"affects_critical_systems": True, "requires_new_contracts": True},
        )
        await svc.apply_pce_overlay(db, pid, overlay_type="cloud_azure_es")
        status = await svc.get_conformity_status(db, pid)
        assert status["route"]["route_type"] == "certificacion_enac"
        assert status["overlays_count"] >= 1
