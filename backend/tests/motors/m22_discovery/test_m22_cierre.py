"""Tests M22-C Logs + DataFlow + Continuity + Report → CIERRE M22."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend.app.motors.m22_discovery import (
    continuity_service,
    dataflow_service,
    log_assessment,
    orchestrator,
    report_generator,
)
from backend.tests.conftest import setup_test_project

BASE = "/api/v1/discovery"


# =========== Helpers ===========

def patch_extras(monkeypatch, logging_data=None, continuity_data=None,
                 fqdns=None, domains=None, tls=None, dns=None,
                 cloud=None, data=None):
    original = orchestrator.execute_run

    async def patched(session, run_id, fetcher=None, extras=None):
        extras = orchestrator.ExecuteExtras(
            fqdns=fqdns or [], domains=domains or [],
            tls_checker=tls, dns_checker=dns, cloud_checker=cloud,
            data_fetcher=data,
            logging_data=logging_data, continuity_data=continuity_data,
        )
        return await original(session, run_id, fetcher=fetcher, extras=extras)

    monkeypatch.setattr(orchestrator, "execute_run", patched)


async def _create_run(async_client, project_id, modules=("logs",)):
    r = await async_client.post(
        f"{BASE}/projects/{project_id}/runs",
        json={"modules": list(modules), "connector_sources": {}, "execute": False},
    )
    return r.json()["id"]


# =========== Log Assessment ===========

class TestLogAssessment:
    @pytest.mark.asyncio
    async def test_logging_with_siem_L3(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        logging_data = {
            "siem": {"tiene": True, "producto": "wazuh"},
            "fuentes": [
                {"sistema": "firewall", "tipo": "syslog", "retencion_dias": 180},
                {"sistema": "m365", "tipo": "audit_log", "retencion_dias": 180},
            ],
            "cobertura": {
                "servidores": 85, "red": 90, "aplicaciones": 80, "endpoints": 80,
            },
            "retencion_minima_dias": 180,
            "categoria_ens": "media",
            "alertas": {"activas": True, "revisadas_por": "responsable_ti",
                        "casos_uso": 6},
            "op_exp_8_controles": {
                "registro_accesos_usuarios": True,
                "registro_cambios_configuracion": True,
                "registro_actividad_privilegiada": True,
                "trazabilidad_acciones_usuario": True,
                "proteccion_integridad_logs": True,
                "sincronizacion_relojes_ntp": True,
            },
        }
        patch_extras(monkeypatch, logging_data=logging_data)
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"modules": ["logs"], "connector_sources": {}, "execute": True},
        )
        assert r.status_code == 200, r.text
        assert r.json()["progress"]["logs"]["status"] == "completed"
        assert r.json()["progress"]["logs"]["nivel_madurez"] == "L3"

        la = (await async_client.get(
            f"{BASE}/projects/{project_id}/logging"
        )).json()
        assert la["tiene_siem"] is True
        assert la["cumple_op_exp_8"] is True
        assert la["nivel_madurez_logging"] == "L3"

    @pytest.mark.asyncio
    async def test_logging_no_siem_L0_with_alerts(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        logging_data = {
            "siem": {"tiene": False},
            "cobertura": {"servidores": 10, "red": 10,
                          "aplicaciones": 0, "endpoints": 0},
            "retencion_minima_dias": 30,
            "categoria_ens": "media",
        }
        patch_extras(monkeypatch, logging_data=logging_data)
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"modules": ["logs"], "connector_sources": {}, "execute": True},
        )
        assert r.status_code == 200
        assert r.json()["progress"]["logs"]["nivel_madurez"] == "L0"

        # Debe generar alertas LOG_NO_SIEM + LOG_RETENCION + LOG_OP_EXP_8
        alerts = (await async_client.get(
            f"{BASE}/projects/{project_id}/alerts?modulo=logs"
        )).json()
        codes = {a["codigo"] for a in alerts}
        assert "LOG_NO_SIEM" in codes
        assert "LOG_RETENCION_INSUFICIENTE" in codes
        assert "LOG_OP_EXP_8_INCUMPLE" in codes

    @pytest.mark.asyncio
    async def test_op_exp_8_gaps_detected(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        logging_data = {
            "siem": {"tiene": True, "producto": "graylog"},
            "cobertura": {"servidores": 60, "red": 60,
                          "aplicaciones": 60, "endpoints": 60},
            "retencion_minima_dias": 200,
            "categoria_ens": "media",
            "op_exp_8_controles": {
                "registro_accesos_usuarios": True,
                # faltan los otros 5 -> gaps
            },
        }
        patch_extras(monkeypatch, logging_data=logging_data)
        await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"modules": ["logs"], "connector_sources": {}, "execute": True},
        )
        la = (await async_client.get(
            f"{BASE}/projects/{project_id}/logging"
        )).json()
        assert la["cumple_op_exp_8"] is False
        assert len(la["gaps_op_exp_8"]) >= 4

    @pytest.mark.asyncio
    async def test_post_logging_via_api(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        run_id = await _create_run(async_client, project_id, modules=["logs"])
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/logging",
            json={
                "run_id": run_id,
                "logging_data": {
                    "siem": {"tiene": True, "producto": "splunk"},
                    "cobertura": {"servidores": 95, "red": 95,
                                  "aplicaciones": 90, "endpoints": 95},
                    "retencion_minima_dias": 730,
                    "categoria_ens": "alta",
                    "alertas": {"activas": True, "revisadas_por": "equipo_soc",
                                "casos_uso": 15},
                    "op_exp_8_controles": {c: True for c in log_assessment.OP_EXP_8_CHECKS},
                },
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["tiene_siem"] is True
        assert body["nivel_madurez_logging"] == "L4"


# =========== Data Flow ===========

class TestDataFlow:
    @pytest.mark.asyncio
    async def test_generate_all_dfds(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        # Sembrar assets + data stores con fetchers mock
        from backend.app.motors.m16_onboarding.connectors.base import (
            DiscoveryResult, DiscoveredAssetDTO,
        )

        async def asset_fetcher(p, cfg):
            return DiscoveryResult(
                provider=p, success=True,
                assets=[
                    DiscoveredAssetDTO(
                        external_id="a1", name="WebApp", asset_type="aws_ec2_instance",
                        provider=p, raw_data={},
                    ),
                ],
            )

        async def data_fetcher(p, cfg):
            return [{
                "nombre": "bucket-prod", "tipo": "cloud_storage",
                "ubicacion": "aws:s3:bucket-prod",
                "sample_text": "DNI 12345678Z",
                "cifrado_en_reposo": True,
            }]

        monkeypatch.setattr(orchestrator, "_default_fetcher", asset_fetcher)
        patch_extras(monkeypatch, data=data_fetcher)

        # Paso 1: assets + data (para sembrar)
        await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={
                "modules": ["assets", "data"],
                "connector_sources": {"aws": {}},
                "execute": True,
            },
        )

        # Paso 2: generate dataflows
        run_id = await _create_run(async_client, project_id, modules=["dataflow"])
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/dataflows/generate",
            json={"run_id": run_id},
        )
        assert r.status_code == 200
        assert r.json()["generated"] >= 1

        lst = (await async_client.get(
            f"{BASE}/projects/{project_id}/dataflows"
        )).json()
        assert len(lst) >= 1
        # Al menos un DFD debe tener >= 2 nodos (process + data_store)
        assert any(len(d["nodos"]) >= 2 for d in lst), lst
        # Todos con mermaid
        for d in lst:
            assert d["mermaid_code"] is not None
            assert "flowchart" in d["mermaid_code"]

    def test_mermaid_generation_unit(self):
        nodos = [
            {"id": "ext1", "tipo": "external_entity", "nombre": "User"},
            {"id": "p1", "tipo": "process", "nombre": "App"},
            {"id": "ds1", "tipo": "data_store", "nombre": "DB"},
        ]
        flujos = [
            {"origen": "ext1", "destino": "p1", "protocolo": "HTTPS"},
            {"origen": "p1", "destino": "ds1", "protocolo": "TLS"},
        ]
        code = dataflow_service.generate_mermaid(nodos, flujos)
        assert "flowchart LR" in code
        assert "ext1([\"User\"])" in code
        assert "p1[\"App\"]" in code
        assert "ds1[(\"DB\")]" in code
        assert "-->|HTTPS|" in code

    def test_security_observations_unencrypted(self):
        nodos = [{"id": "p1", "tipo": "process", "nombre": "App"}]
        flujos = [{"origen": "x", "destino": "p1", "protocolo": "HTTP"}]
        obs = dataflow_service._detect_security_observations(nodos, flujos, [])
        assert any("sin cifrar" in o.lower() for o in obs)


# =========== Continuity ===========

class TestContinuity:
    @pytest.mark.asyncio
    async def test_continuity_with_drp_L3(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        recent = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        continuity_data = {
            "backups": [
                {"sistema": "BD prod", "frecuencia": "diaria",
                 "destino": "S3-offsite", "cifrado": True,
                 "retencion_dias": 30, "ultima_prueba": recent,
                 "prueba_exitosa": True, "offsite": True,
                 "rto_horas": 4, "rpo_horas": 24},
            ],
            "drp": {"tiene": True, "documentado": True, "probado": True,
                    "ultima_prueba": recent},
            "slas": [{"proveedor": "AWS", "servicio": "RDS",
                      "sla_disponibilidad": "99.99%"}],
            "rto_global_horas": 4,
            "rpo_global_horas": 24,
            "categoria_ens": "media",
        }
        patch_extras(monkeypatch, continuity_data=continuity_data)
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={
                "modules": ["continuity"], "connector_sources": {}, "execute": True,
            },
        )
        assert r.status_code == 200, r.text
        assert r.json()["progress"]["continuity"]["nivel_madurez"] in {"L3", "L4", "L5"}

        ca = (await async_client.get(
            f"{BASE}/projects/{project_id}/continuity"
        )).json()
        assert ca["tiene_drp"] is True
        assert ca["tiene_backup_cifrado"] is True
        assert ca["tiene_backup_offsite"] is True

    @pytest.mark.asyncio
    async def test_continuity_no_drp_alerts_media(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        continuity_data = {
            "backups": [{"sistema": "X", "cifrado": False,
                         "destino": "local", "retencion_dias": 7}],
            "drp": {"tiene": False, "documentado": False, "probado": False},
            "categoria_ens": "media",
        }
        patch_extras(monkeypatch, continuity_data=continuity_data)
        await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"modules": ["continuity"], "connector_sources": {}, "execute": True},
        )
        alerts = (await async_client.get(
            f"{BASE}/projects/{project_id}/alerts?modulo=continuity"
        )).json()
        codes = {a["codigo"] for a in alerts}
        assert "CONT_NO_DRP" in codes
        assert "CONT_BACKUP_SIN_CIFRAR" in codes

    @pytest.mark.asyncio
    async def test_continuity_backup_offsite_detected(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        continuity_data = {
            "backups": [
                {"sistema": "BD", "destino": "s3://backup-bucket",
                 "cifrado": True, "retencion_dias": 90,
                 "prueba_exitosa": True, "ultima_prueba": datetime.now(timezone.utc).isoformat()},
            ],
            "drp": {"tiene": True, "documentado": True, "probado": True},
            "categoria_ens": "media",
        }
        patch_extras(monkeypatch, continuity_data=continuity_data)
        await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"modules": ["continuity"], "connector_sources": {}, "execute": True},
        )
        ca = (await async_client.get(
            f"{BASE}/projects/{project_id}/continuity"
        )).json()
        assert ca["tiene_backup_offsite"] is True

    @pytest.mark.asyncio
    async def test_continuity_post_via_api(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        run_id = await _create_run(async_client, project_id, modules=["continuity"])
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/continuity",
            json={
                "run_id": run_id,
                "continuity_data": {
                    "backups": [
                        {"sistema": "BD1", "cifrado": True,
                         "destino": "s3", "prueba_exitosa": True,
                         "ultima_prueba": datetime.now(timezone.utc).isoformat()},
                    ],
                    "drp": {"tiene": True, "documentado": True, "probado": True},
                    "categoria_ens": "media",
                },
            },
        )
        assert r.status_code == 200
        assert r.json()["nivel_madurez_continuidad"] in {"L3", "L4"}

    def test_calculate_maturity_unit(self):
        # No backup + no DRP → L0
        assert continuity_service._calculate_maturity(
            tiene_drp=None, drp_probado=None, backups=[],
            tiene_offsite=False, all_encrypted=False, prueba_exitosa=None,
            spofs=[], rto=None, rpo=None,
        ) == "L0"
        # Backup + DRP tiene pero no probado → L2
        assert continuity_service._calculate_maturity(
            tiene_drp=True, drp_probado=False,
            backups=[{"sistema": "x", "cifrado": True}],
            tiene_offsite=False, all_encrypted=True, prueba_exitosa=None,
            spofs=[], rto=None, rpo=None,
        ) == "L2"


# =========== Technical Report ===========

class TestReport:
    @pytest.mark.asyncio
    async def test_report_all_sections(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        # Ejecutar discovery completo con fetchers basicos
        logging_data = {
            "siem": {"tiene": True, "producto": "wazuh"},
            "cobertura": {"servidores": 60, "red": 60,
                          "aplicaciones": 60, "endpoints": 60},
            "retencion_minima_dias": 180,
            "categoria_ens": "media",
        }
        continuity_data = {
            "backups": [{"sistema": "BD", "cifrado": True, "destino": "s3"}],
            "drp": {"tiene": True, "documentado": True, "probado": False},
            "categoria_ens": "media",
        }
        patch_extras(monkeypatch, logging_data=logging_data,
                     continuity_data=continuity_data)
        await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={
                "modules": ["logs", "continuity", "dataflow"],
                "connector_sources": {}, "execute": True,
            },
        )
        r = await async_client.get(f"{BASE}/projects/{project_id}/report")
        assert r.status_code == 200
        body = r.json()
        assert "resumen_ejecutivo" in body
        assert "assets" in body
        assert "identities" in body
        assert "configurations" in body
        assert "vulnerabilities" in body
        assert "data_stores" in body
        assert "logging" in body
        assert "continuity" in body
        assert "alerts" in body
        assert "recomendaciones" in body
        assert body["logging"]["tiene_siem"] is True

    @pytest.mark.asyncio
    async def test_report_docx_download(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        patch_extras(monkeypatch, logging_data={"categoria_ens": "media"})
        await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"modules": ["logs"], "connector_sources": {}, "execute": True},
        )
        r = await async_client.get(f"{BASE}/projects/{project_id}/report/docx")
        if r.status_code == 501:
            pytest.skip("docxtpl no disponible")
        assert r.status_code == 200
        assert "openxmlformats" in r.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_report_recommendations_prioritized(
        self, async_client, db, monkeypatch,
    ):
        _, project_id = await setup_test_project(db)
        # Logs L0/L1 + no DRP + MFA low → varias recomendaciones
        logging_data = {
            "siem": {"tiene": False},
            "cobertura": {"servidores": 10, "red": 10,
                          "aplicaciones": 0, "endpoints": 0},
            "retencion_minima_dias": 10,
            "categoria_ens": "media",
        }
        continuity_data = {
            "backups": [],
            "drp": {"tiene": False, "documentado": False, "probado": False},
            "categoria_ens": "media",
        }
        patch_extras(monkeypatch, logging_data=logging_data,
                     continuity_data=continuity_data)
        await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"modules": ["logs", "continuity"],
                  "connector_sources": {}, "execute": True},
        )
        r = await async_client.get(f"{BASE}/projects/{project_id}/report")
        recs = r.json()["recomendaciones"]
        assert len(recs) >= 2
        prios = [x["prioridad"] for x in recs]
        # urgente o alta deben estar presentes
        assert "alta" in prios or "urgente" in prios
        # Ordenado: urgente antes que alta
        prio_order = {"urgente": 0, "alta": 1, "media": 2, "baja": 3}
        for i in range(len(recs) - 1):
            assert prio_order.get(recs[i]["prioridad"], 9) <= prio_order.get(
                recs[i + 1]["prioridad"], 9,
            )

    @pytest.mark.asyncio
    async def test_summary_endpoint(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        patch_extras(monkeypatch, logging_data={"categoria_ens": "media"})
        await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"modules": ["logs"], "connector_sources": {}, "execute": True},
        )
        r = await async_client.get(f"{BASE}/projects/{project_id}/summary")
        assert r.status_code == 200
        body = r.json()
        assert "resumen_ejecutivo" in body
        assert "alerts_top" in body
        assert "recomendaciones" in body


# =========== Cross: M22 CERRADO — todos los modulos ejecutan ===========

class TestM22Closed:
    @pytest.mark.asyncio
    async def test_all_8_modules_run(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        patch_extras(
            monkeypatch,
            logging_data={"siem": {"tiene": True}, "categoria_ens": "media",
                          "cobertura": {"servidores": 60, "red": 60,
                                        "aplicaciones": 60, "endpoints": 60},
                          "retencion_minima_dias": 200},
            continuity_data={"backups": [{"sistema": "BD", "cifrado": True,
                                           "destino": "s3"}],
                             "drp": {"tiene": True, "documentado": True,
                                     "probado": True},
                             "categoria_ens": "media"},
        )
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={
                "modules": [
                    "assets", "identities", "configurations",
                    "vulnerabilities", "data", "logs", "dataflow", "continuity",
                ],
                "connector_sources": {},
                "execute": True,
            },
        )
        assert r.status_code == 200, r.text
        prog = r.json()["progress"]
        assert prog["assets"]["status"] == "completed"
        assert prog["identities"]["status"] == "completed"
        assert prog["configurations"]["status"] == "completed"
        assert prog["vulnerabilities"]["status"] == "awaiting_import"
        assert prog["data"]["status"] == "completed"
        assert prog["logs"]["status"] == "completed"
        assert prog["dataflow"]["status"] == "completed"
        assert prog["continuity"]["status"] == "completed"
