"""Tests M22 Paso 6 — Servicios (asset discoverer + config detector +
vuln inventory + data flow mapper + E-090 tecnica + orquestador DataForma)."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text as sa_text

from backend.app.database import set_tenant_context
from backend.app.models.diagnosis import BusinessProcess, Stakeholder
from backend.app.models.discovery import (
    DataFlowDiagram,
    DiscoveredConfiguration,
    DiscoveredDataStore,
    DiscoveryAlert,
    DiscoveryRun,
    VulnerabilityFinding,
)
from backend.app.models.onboarding import DiscoveredAsset, DiscoveredIdentity
from backend.app.motors.m16_onboarding.connectors.base import DiscoveredAssetDTO
from backend.app.motors.m02_magerit.models import MageritAnalysis, MageritAsset
from backend.app.motors.m22_discovery import (
    paso6_asset_discoverer,
    paso6_config_detector,
    paso6_data_flow_mapper,
    paso6_e090_technical,
    paso6_orchestrator,
    paso6_vuln_inventory,
)
from backend.app.motors.m22_discovery.paso6_aws_connector import (
    CloudTrailStatus,
    RDSInstanceConfig,
    S3BucketConfig,
)
from backend.app.motors.m22_discovery.paso6_demo_mocks import (
    build_aws_connector_dataforma,
    build_m365_connector_dataforma,
    dataforma_m365_defender_alerts,
    dataforma_password_policy,
    dataforma_security_hub_findings,
)
from backend.tests.conftest import _admin_setup, setup_test_project


async def _set_tenant(db, project_id):
    client_id = (await db.execute(
        sa_text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)},
    )).scalar()
    await set_tenant_context(
        db, client_id=client_id,
        project_id=uuid.UUID(project_id) if isinstance(project_id, str) else project_id,
    )


async def _mk_run(db, project_id) -> uuid.UUID:
    """Crea un DiscoveryRun minimo."""
    run = DiscoveryRun(
        project_id=project_id,
        modules=["assets", "identities", "configurations"],
        connector_sources={},
        status="running",
        progress={},
        triggered_by="test",
    )
    db.add(run)
    await db.flush()
    return run.id


# ════════════════════════════════════════════════════════════════════
# Asset Discoverer (owner resolution + location + MAGERIT feed)
# ════════════════════════════════════════════════════════════════════

class TestAssetDiscoverer:
    def test_infer_location_cloud(self):
        dto = DiscoveredAssetDTO(
            external_id="i-1", name="srv", asset_type="aws_ec2_instance",
            provider="aws", raw_data={"region": "eu-west-1"},
        )
        loc = paso6_asset_discoverer.infer_location(dto)
        assert loc == "aws:eu-west-1"

    def test_infer_location_saas(self):
        dto = DiscoveredAssetDTO(
            external_id="dev-1", name="laptop", asset_type="m365_device",
            provider="microsoft_365", raw_data={},
        )
        assert paso6_asset_discoverer.infer_location(dto) == "saas:microsoft_365"

    def test_resolve_owner_by_email(self):
        sh = Stakeholder(
            project_id=uuid.uuid4(), nombre="Elena Sanchez",
            email="elena@ex.es", departamento="sistemas",
        )
        dto = DiscoveredAssetDTO(
            external_id="s", name="srv", asset_type="aws_ec2_instance",
            provider="aws", raw_data={"owner_email": "elena@ex.es"},
        )
        owner_id, owner_name = paso6_asset_discoverer.resolve_owner(
            dto, {"elena@ex.es": sh, "dept:sistemas": sh},
        )
        assert owner_name == "Elena Sanchez"

    def test_resolve_owner_by_department(self):
        sh = Stakeholder(
            project_id=uuid.uuid4(), nombre="Elena Sanchez",
            email="elena@ex.es", departamento="sistemas",
        )
        dto = DiscoveredAssetDTO(
            external_id="s", name="srv", asset_type="aws_ec2_instance",
            provider="aws", raw_data={"department": "sistemas"},
        )
        _, owner_name = paso6_asset_discoverer.resolve_owner(
            dto, {"dept:sistemas": sh},
        )
        assert owner_name == "Elena Sanchez"

    @pytest.mark.asyncio
    async def test_discover_and_enrich_persists_assets(self, db):
        _, project_id_str = await setup_test_project(db)
        project_id = uuid.UUID(project_id_str)
        await _set_tenant(db, project_id_str)
        async with _admin_setup(db):
            run_id = await _mk_run(db, project_id)
            # Stakeholder M21 para owner resolution
            sh = Stakeholder(
                project_id=project_id, nombre="Elena Sanchez",
                email="elena.sanchez@dataforma.es", departamento="sistemas",
            )
            db.add(sh)
            await db.flush()

            dtos = [
                DiscoveredAssetDTO(
                    external_id="i-prod-01", name="df-app-prod-01",
                    asset_type="aws_ec2_instance", provider="aws",
                    raw_data={
                        "owner_email": "elena.sanchez@dataforma.es",
                        "environment": "prod",
                        "region": "eu-west-1",
                    },
                ),
                DiscoveredAssetDTO(
                    external_id="bucket-pub", name="dataforma-public",
                    asset_type="aws_s3_bucket", provider="aws",
                    raw_data={"region": "eu-west-1", "public": True},
                ),
            ]
            summary = await paso6_asset_discoverer.discover_and_enrich(
                db, project_id, run_id, "aws", dtos,
            )
        assert summary["created"] == 2
        assert summary["assigned_owner"] == 1  # uno con owner_email
        assert "HW" in summary["by_tipo_magerit"] or "D" in summary["by_tipo_magerit"]

    @pytest.mark.asyncio
    async def test_feed_magerit_creates_analysis_and_assets(self, db):
        _, project_id_str = await setup_test_project(db)
        project_id = uuid.UUID(project_id_str)
        await _set_tenant(db, project_id_str)
        async with _admin_setup(db):
            run_id = await _mk_run(db, project_id)
            dtos = [
                DiscoveredAssetDTO(
                    external_id="i-1", name="app-server",
                    asset_type="aws_ec2_instance", provider="aws",
                    raw_data={"environment": "prod"},
                ),
                DiscoveredAssetDTO(
                    external_id="b-1", name="bucket-1",
                    asset_type="aws_s3_bucket", provider="aws",
                    raw_data={"has_pii": True},
                ),
            ]
            await paso6_asset_discoverer.discover_and_enrich(
                db, project_id, run_id, "aws", dtos,
            )
            feed = await paso6_asset_discoverer.feed_magerit_assets(
                db, project_id,
            )
        assert feed["magerit_created"] == 2
        assert feed["total_discovered"] == 2
        # Segunda llamada no duplica
        async with _admin_setup(db):
            feed2 = await paso6_asset_discoverer.feed_magerit_assets(
                db, project_id,
            )
        assert feed2["magerit_created"] == 0


# ════════════════════════════════════════════════════════════════════
# Config Detector ENS baseline
# ════════════════════════════════════════════════════════════════════

class TestConfigDetector:
    @pytest.mark.asyncio
    async def test_mfa_coverage_reports_gap(self, db):
        _, project_id_str = await setup_test_project(db)
        project_id = uuid.UUID(project_id_str)
        await _set_tenant(db, project_id_str)
        async with _admin_setup(db):
            run_id = await _mk_run(db, project_id)
            # 10 identidades: 3 con MFA, 7 sin (30% cov), 1 privilegiada SIN MFA
            for i in range(10):
                db.add(DiscoveredIdentity(
                    project_id=project_id,
                    discovery_run_id=run_id,
                    fuente_conector="microsoft_365",
                    directorio="entra_id",
                    username=f"u{i}",
                    mfa_activo=(i < 3),
                    tipo_cuenta="privilegiada" if i == 5 else "standard",
                    es_privilegiada=(i == 5),
                ))
            await db.flush()
            configs = await paso6_config_detector.detect_mfa_coverage(
                db, project_id, run_id, ens_category="MEDIA",
            )
        assert len(configs) == 2
        by_control = {c.control_id: c for c in configs}
        general = by_control["op.acc.6_mfa_general"]
        assert general.gap_severidad in {"alta", "critica", "media"}
        priv = by_control["op.acc.6_mfa_privilegiadas"]
        assert priv.estado == "gap"
        assert priv.gap_severidad in {"alta", "critica"}

    @pytest.mark.asyncio
    async def test_encryption_at_rest_detects_unencrypted_s3(self, db):
        _, project_id_str = await setup_test_project(db)
        project_id = uuid.UUID(project_id_str)
        await _set_tenant(db, project_id_str)
        async with _admin_setup(db):
            run_id = await _mk_run(db, project_id)
            s3 = [
                S3BucketConfig(
                    name="b1", region="eu-west-1",
                    encryption_enabled=True, encryption_algorithm="AES256",
                    public_access_blocked=True, versioning_enabled=True,
                    logging_enabled=True,
                ),
                S3BucketConfig(
                    name="b2", region="eu-west-1",
                    encryption_enabled=False, encryption_algorithm=None,
                    public_access_blocked=True, versioning_enabled=True,
                    logging_enabled=False,
                ),
            ]
            rds = [
                RDSInstanceConfig(
                    instance_id="db1", engine="postgres", region="eu-west-1",
                    storage_encrypted=True, backup_retention_period=14,
                    multi_az=True, publicly_accessible=False,
                ),
            ]
            configs = await paso6_config_detector.detect_encryption_at_rest(
                db, project_id, run_id, s3, rds, ens_category="MEDIA",
            )
        # 2 s3 + 1 rds + 1 global = 4
        assert len(configs) == 4
        gaps = [c for c in configs if c.estado == "gap"]
        assert len(gaps) >= 1  # al menos el bucket b2

    @pytest.mark.asyncio
    async def test_logging_enabled_flags_missing_cloudtrail(self, db):
        _, project_id_str = await setup_test_project(db)
        project_id = uuid.UUID(project_id_str)
        await _set_tenant(db, project_id_str)
        async with _admin_setup(db):
            run_id = await _mk_run(db, project_id)
            configs = await paso6_config_detector.detect_logging_enabled(
                db, project_id, run_id,
                cloudtrail_status=[],
                azure_activity_enabled=True,
            )
        assert len(configs) == 2
        ct_cfg = next(c for c in configs if c.control_id == "op.exp.8_cloudtrail")
        assert ct_cfg.gap_severidad == "alta"
        az_cfg = next(c for c in configs if c.control_id == "op.exp.8_azure_activity")
        assert az_cfg.estado == "ok"

    @pytest.mark.asyncio
    async def test_backup_config_retention_below_target(self, db):
        _, project_id_str = await setup_test_project(db)
        project_id = uuid.UUID(project_id_str)
        await _set_tenant(db, project_id_str)
        async with _admin_setup(db):
            run_id = await _mk_run(db, project_id)
            rds = [
                RDSInstanceConfig(
                    instance_id="db-ok", engine="pg", region="eu-west-1",
                    storage_encrypted=True, backup_retention_period=30,
                    multi_az=True, publicly_accessible=False,
                ),
                RDSInstanceConfig(
                    instance_id="db-no-bkp", engine="pg", region="eu-west-1",
                    storage_encrypted=True, backup_retention_period=0,
                    multi_az=False, publicly_accessible=False,
                ),
            ]
            configs = await paso6_config_detector.detect_backup_config(
                db, project_id, run_id, rds, ens_category="MEDIA",
            )
        per_rds = [c for c in configs if c.control_id == "op.cont.3_rds_backup"]
        assert len(per_rds) == 2
        gap = next(c for c in per_rds if "db-no-bkp" in c.sistema)
        assert gap.gap_severidad == "alta"


# ════════════════════════════════════════════════════════════════════
# Vulnerability Inventory + M8 feed
# ════════════════════════════════════════════════════════════════════

class TestVulnInventory:
    @pytest.mark.asyncio
    async def test_import_security_hub_persists_findings(self, db):
        _, project_id_str = await setup_test_project(db)
        project_id = uuid.UUID(project_id_str)
        await _set_tenant(db, project_id_str)
        async with _admin_setup(db):
            run_id = await _mk_run(db, project_id)
            findings = dataforma_security_hub_findings()
            vs, alerts = await paso6_vuln_inventory.import_security_hub(
                db, project_id, run_id, findings,
            )
        assert len(vs) == 15
        altas = [v for v in vs if v.cvss_severity == "alta"]
        assert len(altas) >= 4
        # Marcamos origen paso6
        assert all(v.raw_finding.get("origen_m22_paso6") is True for v in vs)
        # Alertas solo para alta/critica
        assert len(alerts) >= len(altas)

    @pytest.mark.asyncio
    async def test_import_m365_defender_persists(self, db):
        _, project_id_str = await setup_test_project(db)
        project_id = uuid.UUID(project_id_str)
        await _set_tenant(db, project_id_str)
        async with _admin_setup(db):
            run_id = await _mk_run(db, project_id)
            alerts_v2 = dataforma_m365_defender_alerts()
            vs, _ = await paso6_vuln_inventory.import_m365_defender(
                db, project_id, run_id, alerts_v2,
            )
        assert len(vs) == 1
        assert vs[0].cvss_severity == "alta"
        assert vs[0].fuente == "m365_defender"

    @pytest.mark.asyncio
    async def test_feed_m8_initial_context_summary(self, db):
        _, project_id_str = await setup_test_project(db)
        project_id = uuid.UUID(project_id_str)
        await _set_tenant(db, project_id_str)
        async with _admin_setup(db):
            run_id = await _mk_run(db, project_id)
            await paso6_vuln_inventory.import_security_hub(
                db, project_id, run_id, dataforma_security_hub_findings(),
            )
            context = await paso6_vuln_inventory.feed_m8_initial_context(
                db, project_id,
            )
        assert context["total"] == 15
        assert context["m8_ready"] is True
        assert len(context["top_10"]) <= 10
        # Top sorted por severidad
        first_sevs = [item["severidad"] for item in context["top_10"][:5]]
        assert "alta" in first_sevs or "critica" in first_sevs


# ════════════════════════════════════════════════════════════════════
# Data Flow Mapper por proceso critico
# ════════════════════════════════════════════════════════════════════

class TestDataFlowMapper:
    @pytest.mark.asyncio
    async def test_map_critical_process_generates_dfd(self, db):
        _, project_id_str = await setup_test_project(db)
        project_id = uuid.UUID(project_id_str)
        await _set_tenant(db, project_id_str)
        async with _admin_setup(db):
            run_id = await _mk_run(db, project_id)
            # Proceso critico M21
            p = BusinessProcess(
                project_id=project_id,
                nombre="Gestion de historia clinica electronica",
                descripcion="HCE hospitalaria",
                criticidad="alta",
                sistemas_involucrados={"sistemas": ["HIS", "EHR"]},
                rto_horas=4, rpo_horas=1,
                propietario="Elena Sanchez",
            )
            db.add(p)
            # Asset descubierto que matchea sistema
            a = DiscoveredAsset(
                project_id=project_id,
                discovery_run_id=run_id,
                fuente_conector="aws",
                tipo_magerit="SW",
                nombre="HIS EHR",
                identificador="i-his",
                criticidad_propuesta="alta",
                ubicacion="aws:eu-west-1",
                metadata_extra={"tags": ["his"]},
            )
            db.add(a)
            # Data store con datos personales
            ds = DiscoveredDataStore(
                project_id=project_id,
                discovery_run_id=run_id,
                fuente_conector="aws",
                tipo="rds",
                nombre="HCE Database",
                ubicacion="aws:eu-west-1",
                clasificacion_inicial="reservada",
                patrones_detectados=["NHC"],
                tiene_datos_personales=True,
                tiene_datos_salud=True,
                cifrado_en_reposo=False,  # gap
                cifrado_en_transito=True,
                control_acceso="interno",
            )
            db.add(ds)
            # Stakeholder owner
            db.add(Stakeholder(
                project_id=project_id, nombre="Elena Sanchez",
                email="elena@ex.es", departamento="sistemas",
            ))
            await db.flush()

            dfds = await paso6_data_flow_mapper.map_flows_for_critical_processes(
                db, project_id, run_id,
            )
        assert len(dfds) == 1
        d = dfds[0]
        assert d.tipo == "proceso"
        assert "Gestion de historia clinica" in d.nombre
        # Observacion por datos personales sin cifrado
        assert any("sin cifrado" in o for o in d.observaciones_seguridad)
        assert "flowchart TD" in d.mermaid_code

    def test_generate_mermaid_bpmn_shapes(self):
        nodos = [
            {"id": "in1", "tipo": "external_entity", "nombre": "Usuario"},
            {"id": "p1", "tipo": "process", "nombre": "HCE"},
            {"id": "ds1", "tipo": "data_store", "nombre": "HCE DB"},
        ]
        flujos = [
            {"origen": "in1", "destino": "p1", "datos": "request", "protocolo": "HTTPS", "cifrado": True},
            {"origen": "p1", "destino": "ds1", "datos": "datos", "protocolo": "TLS", "cifrado": True},
        ]
        code = paso6_data_flow_mapper.generate_mermaid_bpmn("HCE", nodos, flujos)
        assert "flowchart TD" in code
        assert "in1([" in code
        assert "ds1[(" in code
        assert "p1[" in code
        assert "-->" in code


# ════════════════════════════════════════════════════════════════════
# E-090 Seccion 3.2 Tecnica
# ════════════════════════════════════════════════════════════════════

class TestE090Technical:
    def test_compute_maturity_level_mapping(self):
        assert paso6_e090_technical.compute_maturity_level(0) == "L0"
        assert paso6_e090_technical.compute_maturity_level(20) == "L1"
        assert paso6_e090_technical.compute_maturity_level(40) == "L2"
        assert paso6_e090_technical.compute_maturity_level(60) == "L3"
        assert paso6_e090_technical.compute_maturity_level(80) == "L4"
        assert paso6_e090_technical.compute_maturity_level(95) == "L5"

    def test_compute_technical_maturity_considers_all_drivers(self):
        result = paso6_e090_technical.compute_technical_maturity(
            identities={"mfa_coverage_pct": 70.0},
            data_stores={"cifrado_at_rest_pct": 60.0},
            configurations={"ok_pct": 50.0},
            vulns={"critica": 1, "alta": 2, "total_abiertas": 3},
        )
        assert 0 <= result["score_pct"] <= 100
        assert result["nivel"] in {"L0", "L1", "L2", "L3", "L4", "L5"}
        assert result["drivers"]["vulns_penalty"] == 1 * 5 + 2 * 2

    @pytest.mark.asyncio
    async def test_build_technical_section_with_data(self, db):
        _, project_id_str = await setup_test_project(db)
        project_id = uuid.UUID(project_id_str)
        await _set_tenant(db, project_id_str)
        async with _admin_setup(db):
            run_id = await _mk_run(db, project_id)
            # Identidades con y sin MFA
            for i in range(10):
                db.add(DiscoveredIdentity(
                    project_id=project_id,
                    discovery_run_id=run_id,
                    fuente_conector="microsoft_365",
                    directorio="entra_id",
                    username=f"u{i}",
                    mfa_activo=(i < 7),
                    tipo_cuenta="standard",
                ))
            # Assets variados
            for i in range(5):
                db.add(DiscoveredAsset(
                    project_id=project_id,
                    discovery_run_id=run_id,
                    fuente_conector="aws",
                    tipo_magerit="HW" if i < 3 else "SW",
                    nombre=f"asset-{i}",
                    identificador=f"id-{i}",
                    criticidad_propuesta="media",
                    ubicacion="aws:eu-west-1",
                ))
            await db.flush()
            section = await paso6_e090_technical.build_technical_section(
                db, project_id,
            )
        assert section["inventario_activos"]["total"] == 5
        assert section["estado_identidades"]["mfa_coverage_pct"] == 70.0
        assert "madurez_tecnica" in section
        assert "nivel" in section["madurez_tecnica"]

    def test_merge_with_organizational_appends_quick_wins(self):
        tech = {
            "madurez_tecnica": {"nivel": "L1", "score_pct": 20.0},
            "top_gaps": [
                {
                    "control_id": "op.acc.6_mfa_privilegiadas",
                    "sistema": "cuentas_privilegiadas",
                    "severidad": "alta",
                    "actual": "33%", "esperado": "100%",
                    "medidas_ens": ["op.acc.6"],
                },
            ],
        }
        org = {"quick_wins": [{"titulo": "M21 qw"}]}
        merged = paso6_e090_technical.merge_with_organizational(tech, org)
        assert "seccion_32_tecnica" in merged
        assert len(merged["quick_wins"]) == 2
        assert any("L1" in r for r in merged["recomendaciones_fase2"])


# ════════════════════════════════════════════════════════════════════
# Orquestador end-to-end DataForma
# ════════════════════════════════════════════════════════════════════

class TestDataFormaEndToEnd:
    @pytest.mark.asyncio
    async def test_dataforma_full_paso6(self, db):
        _, project_id_str = await setup_test_project(db)
        project_id = uuid.UUID(project_id_str)
        await _set_tenant(db, project_id_str)

        async with _admin_setup(db):
            # Seed un proceso critico M21 para tener DFD
            db.add(BusinessProcess(
                project_id=project_id,
                nombre="Gestion de historia clinica electronica",
                descripcion="HCE",
                criticidad="alta",
                sistemas_involucrados={"sistemas": ["HIS"]},
                rto_horas=4, rpo_horas=1,
                propietario="Elena Sanchez",
            ))
            db.add(Stakeholder(
                project_id=project_id, nombre="Elena Sanchez",
                email="elena.sanchez@dataforma.es",
                departamento="sistemas",
            ))
            await db.flush()

            m365 = build_m365_connector_dataforma()
            aws = build_aws_connector_dataforma()
            report = await paso6_orchestrator.run_full_paso6(
                db, project_id,
                m365_connector=m365, aws_connector=aws,
                ens_category="MEDIA",
                password_policy=dataforma_password_policy(),
                security_hub_findings=dataforma_security_hub_findings(),
                m365_defender_alerts=dataforma_m365_defender_alerts(),
                azure_activity_enabled=True,
                vault_enabled=False,
            )

        # Verificaciones principales
        assert set(report["connectors_used"]) == {"microsoft_365", "aws"}
        assert report["m365"]["identities"] == 24
        assert report["m365"]["ca_enabled"] == 2
        assert report["aws"]["identities"] == 5
        assert report["aws"]["s3_unencrypted"] == 3
        assert report["aws"]["cloudtrail_logging_ok"] == 1
        assert report["magerit_feed"]["magerit_created"] >= 20
        assert report["config_checks"]["total"] >= 10
        assert report["config_checks"]["gaps_alta_critica"] >= 3
        # Vulns: 15 security hub + 1 defender = 16
        assert report["vulns"]["by_source"]["aws_security_hub"] == 15
        assert report["vulns"]["by_source"]["m365_defender"] == 1
        assert report["data_flows"]["dfds_generados"] >= 1
        assert report["e090_tecnica"]["madurez_nivel"] in {"L0", "L1", "L2"}
        assert report["e090_tecnica"]["total_activos"] >= 20
