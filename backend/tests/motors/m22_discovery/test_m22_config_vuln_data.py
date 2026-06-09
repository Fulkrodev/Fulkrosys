"""Tests M22-B Configuration + Vulnerability + Data Discovery.

Unit-level para analyzers; integration-level vía API con checkers/fetchers
inyectados por monkeypatch para evitar I/O real (TLS/DNS/cloud).
"""
from __future__ import annotations

import uuid

import pytest

from backend.app.motors.m22_discovery import (
    config_discovery,
    data_discovery,
    orchestrator,
    vuln_discovery,
)
from backend.tests.conftest import setup_test_project

BASE = "/api/v1/discovery"


# =========== Helpers de mocking ===========

def make_tls_checker(results_by_fqdn: dict[str, list[dict]]):
    async def checker(fqdn: str) -> list[dict]:
        return results_by_fqdn.get(fqdn, [])
    return checker


def make_dns_checker(results_by_domain: dict[str, list[dict]]):
    async def checker(domain: str) -> list[dict]:
        return results_by_domain.get(domain, [])
    return checker


def make_cloud_checker(results_by_provider: dict[str, list[dict]]):
    async def checker(provider: str, config: dict) -> list[dict]:
        return results_by_provider.get(provider, [])
    return checker


def make_data_fetcher(results_by_provider: dict[str, list[dict]]):
    async def fetcher(provider: str, config: dict) -> list[dict]:
        return results_by_provider.get(provider, [])
    return fetcher


def patch_extras(monkeypatch, fqdns=None, domains=None, tls=None, dns=None,
                 cloud=None, data=None):
    """Wrap execute_run para inyectar ExecuteExtras con checkers/fetchers mock."""
    original = orchestrator.execute_run

    async def patched(session, run_id, fetcher=None, extras=None):
        extras = orchestrator.ExecuteExtras(
            fqdns=fqdns or [], domains=domains or [],
            tls_checker=tls, dns_checker=dns, cloud_checker=cloud,
            data_fetcher=data,
        )
        return await original(session, run_id, fetcher=fetcher, extras=extras)

    monkeypatch.setattr(orchestrator, "execute_run", patched)


# =========== Unit: TLS/DNS analyzers ===========

class TestConfigUnit:
    def test_alert_severity_from_critica(self):
        # Direct helper: gap_severidad critica genera alerta
        from backend.app.models.discovery import DiscoveredConfiguration
        c = DiscoveredConfiguration(
            id=uuid.uuid4(), project_id=uuid.uuid4(),
            discovery_run_id=uuid.uuid4(), fuente_conector="tls",
            sistema="ex.com", control_id="tls_version",
            estado="fail", gap_severidad="critica",
            herramienta_deteccion="testssl_sh",
            medidas_ens_afectadas=["mp.com.2"], raw_output={},
        )
        alert = config_discovery._alert_from_config(c)
        assert alert is not None
        assert alert.severidad == "critica"
        assert alert.codigo == "CFG_TLS_VERSION"


# =========== Integration: Configurations via API ===========

class TestConfigurations:
    @pytest.mark.asyncio
    async def test_tls_pass(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        tls = make_tls_checker({"api.example.com": [{
            "control_id": "tls_version",
            "estado": "pass",
            "valor_actual": "TLS 1.3",
            "valor_esperado": "TLS 1.2+",
            "medidas_ens": ["mp.com.2"],
        }]})
        patch_extras(monkeypatch, fqdns=["api.example.com"], tls=tls)
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"modules": ["configurations"], "connector_sources": {},
                  "execute": True},
        )
        assert r.status_code == 200, r.text
        assert r.json()["progress"]["configurations"]["count"] == 1
        lst = (await async_client.get(
            f"{BASE}/projects/{project_id}/configurations"
        )).json()
        assert len(lst) == 1
        assert lst[0]["estado"] == "pass"
        assert lst[0]["control_id"] == "tls_version"

    @pytest.mark.asyncio
    async def test_tls_fail_old_version_generates_alert(
        self, async_client, db, monkeypatch,
    ):
        _, project_id = await setup_test_project(db)
        tls = make_tls_checker({"legacy.example.com": [{
            "control_id": "tls_version",
            "estado": "fail",
            "valor_actual": "TLS 1.0",
            "valor_esperado": "TLS 1.2+",
            "gap_severidad": "critica",
            "medidas_ens": ["mp.com.2"],
        }]})
        patch_extras(monkeypatch, fqdns=["legacy.example.com"], tls=tls)
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"modules": ["configurations"], "connector_sources": {},
                  "execute": True},
        )
        assert r.status_code == 200
        assert r.json()["progress"]["configurations"]["alerts"] == 1
        alerts = (await async_client.get(
            f"{BASE}/projects/{project_id}/alerts?severidad=critica"
        )).json()
        codes = {a["codigo"] for a in alerts}
        assert "CFG_TLS_VERSION" in codes

    @pytest.mark.asyncio
    async def test_tls_warning_expiry(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        tls = make_tls_checker({"ex.com": [{
            "control_id": "tls_certificate_expiry",
            "estado": "warning",
            "valor_actual": "15 dias",
            "valor_esperado": ">= 30 dias",
            "gap_severidad": "media",
            "medidas_ens": ["mp.com.2"],
        }]})
        patch_extras(monkeypatch, fqdns=["ex.com"], tls=tls)
        await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"modules": ["configurations"], "connector_sources": {},
                  "execute": True},
        )
        lst = (await async_client.get(
            f"{BASE}/projects/{project_id}/configurations?estado=warning"
        )).json()
        assert len(lst) == 1
        assert lst[0]["gap_severidad"] == "media"
        # gap media NO deberia generar alerta
        alerts = (await async_client.get(
            f"{BASE}/projects/{project_id}/alerts"
        )).json()
        assert all(a["modulo"] != "configurations" for a in alerts)

    @pytest.mark.asyncio
    async def test_dns_spf_fail(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        dns = make_dns_checker({"example.com": [{
            "control_id": "spf_record",
            "estado": "fail",
            "valor_actual": "(sin SPF)",
            "valor_esperado": "v=spf1 ... -all",
            "gap_severidad": "alta",
            "medidas_ens": ["mp.com.1"],
        }]})
        patch_extras(monkeypatch, domains=["example.com"], dns=dns)
        await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"modules": ["configurations"], "connector_sources": {},
                  "execute": True},
        )
        lst = (await async_client.get(
            f"{BASE}/projects/{project_id}/configurations"
        )).json()
        assert len(lst) == 1
        assert lst[0]["control_id"] == "spf_record"
        assert "mp.com.1" in lst[0]["medidas_ens_afectadas"]

    @pytest.mark.asyncio
    async def test_cloud_m365_secure_score(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        cloud = make_cloud_checker({"microsoft_365": [{
            "sistema": "tenant-abc",
            "control_id": "m365_secure_score_overall",
            "control_description": "M365 Secure Score global",
            "estado": "fail",
            "valor_actual": "45/100",
            "valor_esperado": ">= 70/100",
            "gap_severidad": "alta",
            "medidas_ens": ["op.exp.8"],
        }]})
        patch_extras(monkeypatch, cloud=cloud)
        await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={
                "modules": ["configurations"],
                "connector_sources": {"microsoft_365": {}},
                "execute": True,
            },
        )
        lst = (await async_client.get(
            f"{BASE}/projects/{project_id}/configurations?fuente=m365_secure_score"
        )).json()
        assert len(lst) == 1
        assert lst[0]["gap_severidad"] == "alta"

    @pytest.mark.asyncio
    async def test_configurations_summary(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        tls = make_tls_checker({
            "a.com": [{"control_id": "tls_version", "estado": "pass",
                       "medidas_ens": ["mp.com.2"]}],
            "b.com": [{"control_id": "tls_version", "estado": "fail",
                       "gap_severidad": "critica", "medidas_ens": ["mp.com.2"]}],
            "c.com": [{"control_id": "hsts_enabled", "estado": "warning",
                       "gap_severidad": "baja", "medidas_ens": ["mp.com.2"]}],
        })
        patch_extras(monkeypatch, fqdns=["a.com", "b.com", "c.com"], tls=tls)
        await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"modules": ["configurations"], "connector_sources": {},
                  "execute": True},
        )
        s = (await async_client.get(
            f"{BASE}/projects/{project_id}/configurations/summary"
        )).json()
        assert s["total"] == 3
        assert s["by_estado"]["pass"] == 1
        assert s["by_estado"]["fail"] == 1
        assert s["by_estado"]["warning"] == 1
        assert s["by_gap_severidad"].get("critica") == 1


# =========== Vulnerability Discovery ===========

class TestVulnUnit:
    def test_map_ens_tls(self):
        medidas = vuln_discovery.map_ens_measures(
            "Weak TLS cipher", "SSL/TLS certificate misconfiguration",
        )
        assert "mp.com.2" in medidas
        assert "mp.com.3" in medidas

    def test_map_ens_xss_sqli(self):
        medidas = vuln_discovery.map_ens_measures(
            "Reflected XSS in login", "Input not sanitized, SQL injection possible",
        )
        assert "mp.sw.1" in medidas
        assert "mp.sw.2" in medidas

    def test_severity_from_cvss_critical(self):
        assert vuln_discovery._severity_from_cvss(9.8, None) == "critica"

    def test_severity_from_cvss_high(self):
        assert vuln_discovery._severity_from_cvss(7.5, None) == "alta"

    def test_severity_from_raw_string(self):
        assert vuln_discovery._severity_from_cvss(None, "HIGH") == "alta"
        assert vuln_discovery._severity_from_cvss(None, "critical") == "critica"


class TestVulnImport:
    @pytest.mark.asyncio
    async def test_import_openvas(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        # Crear run sin ejecutar
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"modules": ["vulnerabilities"], "connector_sources": {},
                  "execute": False},
        )
        run_id = r.json()["id"]

        openvas_findings = [
            {
                "host": "10.0.0.5",
                "severity": "9.8",
                "threat": "critical",
                "description": "SSL weak cipher detected",
                "nvt": {
                    "name": "Weak SSL/TLS ciphers",
                    "cvss_base": "9.8",
                    "refs": {"ref": [{"type": "cve", "id": "CVE-2024-1111"}]},
                },
            },
        ]
        imp = await async_client.post(
            f"{BASE}/projects/{project_id}/vulnerabilities/import",
            json={"run_id": run_id, "source": "openvas", "findings": openvas_findings},
        )
        assert imp.status_code == 200
        assert imp.json()["imported"] == 1
        assert imp.json()["alerts_generated"] == 1

        lst = (await async_client.get(
            f"{BASE}/projects/{project_id}/vulnerabilities"
        )).json()
        assert len(lst) == 1
        assert lst[0]["cve_id"] == "CVE-2024-1111"
        assert lst[0]["cvss_severity"] == "critica"
        # ENS mapping auto
        assert "mp.com.2" in lst[0]["medidas_ens_afectadas"]

    @pytest.mark.asyncio
    async def test_import_nuclei(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"modules": ["vulnerabilities"], "connector_sources": {},
                  "execute": False},
        )
        run_id = r.json()["id"]

        nuclei = [{
            "template-id": "cve-2023-9999",
            "matched-at": "https://vuln.example.com/api",
            "info": {
                "name": "SQL injection via id param",
                "severity": "high",
                "description": "SQLi in /api?id=1",
                "classification": {
                    "cve-id": ["CVE-2023-9999"],
                    "cvss-score": 8.1,
                    "cvss-metrics": "CVSS:3.1/AV:N/AC:L/PR:N",
                },
            },
        }]
        imp = await async_client.post(
            f"{BASE}/projects/{project_id}/vulnerabilities/import",
            json={"run_id": run_id, "source": "nuclei", "findings": nuclei},
        )
        assert imp.status_code == 200
        lst = (await async_client.get(
            f"{BASE}/projects/{project_id}/vulnerabilities?cvss_severity=alta"
        )).json()
        assert len(lst) == 1
        assert lst[0]["cve_id"] == "CVE-2023-9999"
        assert "mp.sw.1" in lst[0]["medidas_ens_afectadas"]

    @pytest.mark.asyncio
    async def test_import_trivy(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"modules": ["vulnerabilities"], "connector_sources": {},
                  "execute": False},
        )
        run_id = r.json()["id"]

        trivy = {
            "Results": [
                {
                    "Target": "my-image:latest",
                    "Vulnerabilities": [
                        {
                            "VulnerabilityID": "CVE-2022-1234",
                            "Title": "libssl outdated",
                            "Description": "openssl patch required",
                            "Severity": "HIGH",
                            "CVSS": {"nvd": {"V3Score": 7.8}},
                            "FixedVersion": "1.1.1t",
                        },
                    ],
                },
            ],
        }
        imp = await async_client.post(
            f"{BASE}/projects/{project_id}/vulnerabilities/import",
            json={"run_id": run_id, "source": "trivy", "findings": [trivy]},
        )
        assert imp.status_code == 200
        assert imp.json()["imported"] == 1
        lst = (await async_client.get(
            f"{BASE}/projects/{project_id}/vulnerabilities"
        )).json()
        assert lst[0]["remediacion_sugerida"] == "1.1.1t"
        assert lst[0]["asset_afectado"] == "my-image:latest"

    @pytest.mark.asyncio
    async def test_import_generic_and_update_status(
        self, async_client, db, monkeypatch,
    ):
        _, project_id = await setup_test_project(db)
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"modules": ["vulnerabilities"], "connector_sources": {},
                  "execute": False},
        )
        run_id = r.json()["id"]

        imp = await async_client.post(
            f"{BASE}/projects/{project_id}/vulnerabilities/import",
            json={
                "run_id": run_id, "source": "customtool",
                "findings": [
                    {"titulo": "Outdated library", "cvss_score": 5.5,
                     "asset_afectado": "host1"},
                ],
            },
        )
        assert imp.status_code == 200
        lst = (await async_client.get(
            f"{BASE}/projects/{project_id}/vulnerabilities"
        )).json()
        fid = lst[0]["id"]
        upd = await async_client.patch(
            f"{BASE}/projects/{project_id}/vulnerabilities/{fid}",
            json={"estado": "mitigated"},
        )
        assert upd.status_code == 200
        assert upd.json()["estado"] == "mitigated"

    @pytest.mark.asyncio
    async def test_vuln_summary(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"modules": ["vulnerabilities"], "connector_sources": {},
                  "execute": False},
        )
        run_id = r.json()["id"]
        findings = [
            {"titulo": "SQL injection", "cvss_score": 9.5, "cve_id": "CVE-1"},
            {"titulo": "Weak TLS", "cvss_score": 7.1, "cve_id": "CVE-2"},
            {"titulo": "Info disclosure", "cvss_score": 3.1},
        ]
        await async_client.post(
            f"{BASE}/projects/{project_id}/vulnerabilities/import",
            json={"run_id": run_id, "source": "generic", "findings": findings},
        )
        s = (await async_client.get(
            f"{BASE}/projects/{project_id}/vulnerabilities/summary"
        )).json()
        assert s["total"] == 3
        assert s["by_severity"]["critica"] == 1
        assert s["by_severity"]["alta"] == 1
        assert s["by_severity"]["baja"] == 1


# =========== Data Discovery ===========

class TestDataSensitivity:
    def test_pattern_dni_detected(self):
        clasif, patrones, flags = data_discovery.analyze_sensitivity(
            "Empleado con DNI 12345678Z en la nomina"
        )
        assert clasif == "confidencial"
        tipos = {p["tipo"] for p in patrones}
        assert "DNI_NIE" in tipos
        assert flags["tiene_datos_personales"] is True

    def test_pattern_iban_detected(self):
        clasif, patrones, flags = data_discovery.analyze_sensitivity(
            "Transferencia a ES7620770024003102575766"
        )
        assert clasif == "confidencial"
        tipos = {p["tipo"] for p in patrones}
        assert "IBAN_ES" in tipos
        assert flags["tiene_datos_financieros"] is True

    def test_pattern_credit_card_reservada(self):
        clasif, patrones, flags = data_discovery.analyze_sensitivity(
            "Tarjeta: 4111 1111 1111 1111"
        )
        assert clasif == "reservada"
        tipos = {p["tipo"] for p in patrones}
        assert "TARJETA_CREDITO" in tipos
        assert flags["tiene_datos_financieros"] is True

    def test_pattern_salud(self):
        clasif, patrones, flags = data_discovery.analyze_sensitivity(
            "Historia clinica con diagnostico codificado CIE-10"
        )
        assert clasif == "reservada"
        assert flags["tiene_datos_salud"] is True

    def test_no_patterns(self):
        clasif, patrones, flags = data_discovery.analyze_sensitivity(
            "Solo datos corporativos publicos sin sensibilidad alguna"
        )
        assert clasif == "sin_clasificar"
        assert patrones == []
        assert flags["tiene_datos_personales"] is False

    def test_max_classification_wins(self):
        # DNI (confidencial) + tarjeta (reservada) -> reservada
        clasif, _, _ = data_discovery.analyze_sensitivity(
            "Fila con DNI 12345678Z y tarjeta 4111 1111 1111 1111"
        )
        assert clasif == "reservada"


class TestDataDiscoveryAPI:
    @pytest.mark.asyncio
    async def test_data_store_creates_pkg_node_and_alert(
        self, async_client, db, monkeypatch,
    ):
        _, project_id = await setup_test_project(db)
        fetcher = make_data_fetcher({"aws": [{
            "nombre": "bucket-confidencial",
            "tipo": "cloud_storage",
            "ubicacion": "aws:s3:bucket-confidencial",
            "sample_text": "usuarios con DNI 12345678Z y NSS 28/12345678/01",
            "cifrado_en_reposo": False,
            "volumen_estimado_gb": 150.0,
        }]})
        patch_extras(monkeypatch, data=fetcher)
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={
                "modules": ["data"],
                "connector_sources": {"aws": {}},
                "execute": True,
            },
        )
        assert r.status_code == 200, r.text
        assert r.json()["progress"]["data"]["count"] == 1
        assert r.json()["progress"]["data"]["alerts"] == 1

        lst = (await async_client.get(
            f"{BASE}/projects/{project_id}/data-stores"
        )).json()
        assert len(lst) == 1
        store = lst[0]
        assert store["clasificacion_inicial"] == "confidencial"
        assert store["tiene_datos_personales"] is True
        assert store["pkg_node_id"] is not None

        # Alerta confidencial sin cifrado
        alerts = (await async_client.get(
            f"{BASE}/projects/{project_id}/alerts?modulo=data"
        )).json()
        assert any(a["codigo"] == "DATA_CONFIDENCIAL_SIN_CIFRADO" for a in alerts)

    @pytest.mark.asyncio
    async def test_data_summary(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        fetcher = make_data_fetcher({"aws": [
            {
                "nombre": "b1", "tipo": "cloud_storage",
                "ubicacion": "aws:s3:b1",
                "sample_text": "DNI 12345678Z",
                "cifrado_en_reposo": True, "volumen_estimado_gb": 10.0,
            },
            {
                "nombre": "b2", "tipo": "cloud_storage",
                "ubicacion": "aws:s3:b2",
                "sample_text": "Historia clinica y diagnostico",
                "cifrado_en_reposo": True, "volumen_estimado_gb": 5.0,
            },
            {
                "nombre": "b3", "tipo": "cloud_storage",
                "ubicacion": "aws:s3:b3",
                "sample_text": "sin datos sensibles",
                "cifrado_en_reposo": True, "volumen_estimado_gb": 2.5,
            },
        ]})
        patch_extras(monkeypatch, data=fetcher)
        await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={
                "modules": ["data"],
                "connector_sources": {"aws": {}},
                "execute": True,
            },
        )
        s = (await async_client.get(
            f"{BASE}/projects/{project_id}/data-stores/summary"
        )).json()
        assert s["total"] == 3
        assert s["con_datos_personales"] == 2  # b1 (DNI) + b2 (salud -> personales)
        assert s["con_datos_salud"] == 1
        assert s["by_clasificacion"]["reservada"] == 1  # b2
        assert s["by_clasificacion"]["confidencial"] == 1  # b1
        assert s["by_clasificacion"]["sin_clasificar"] == 1  # b3
        assert s["volumen_total_gb"] == 17.5

    @pytest.mark.asyncio
    async def test_data_filter_clasificacion(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        fetcher = make_data_fetcher({"aws": [
            {"nombre": "b1", "tipo": "cloud_storage",
             "ubicacion": "aws:s3:b1", "sample_text": "DNI 12345678Z",
             "cifrado_en_reposo": True},
            {"nombre": "b2", "tipo": "cloud_storage",
             "ubicacion": "aws:s3:b2", "sample_text": "publico",
             "cifrado_en_reposo": True},
        ]})
        patch_extras(monkeypatch, data=fetcher)
        await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={
                "modules": ["data"],
                "connector_sources": {"aws": {}},
                "execute": True,
            },
        )
        r = await async_client.get(
            f"{BASE}/projects/{project_id}/data-stores?clasificacion=confidencial"
        )
        items = r.json()
        assert len(items) == 1
        assert items[0]["nombre"] == "b1"

    @pytest.mark.asyncio
    async def test_data_soft_delete(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        fetcher = make_data_fetcher({"aws": [{
            "nombre": "b1", "tipo": "cloud_storage",
            "ubicacion": "aws:s3:b1", "sample_text": "whatever",
            "cifrado_en_reposo": True,
        }]})
        patch_extras(monkeypatch, data=fetcher)
        await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={
                "modules": ["data"],
                "connector_sources": {"aws": {}},
                "execute": True,
            },
        )
        lst = (await async_client.get(
            f"{BASE}/projects/{project_id}/data-stores"
        )).json()
        sid = lst[0]["id"]
        d = await async_client.delete(
            f"{BASE}/projects/{project_id}/data-stores/{sid}"
        )
        assert d.status_code == 200
        gone = await async_client.get(
            f"{BASE}/projects/{project_id}/data-stores/{sid}"
        )
        assert gone.status_code == 404


# =========== Cross-module ===========

class TestOrchestratorIntegration:
    @pytest.mark.asyncio
    async def test_vulnerabilities_module_awaiting_import(
        self, async_client, db, monkeypatch,
    ):
        _, project_id = await setup_test_project(db)
        # Vulnerabilities no ejecuta en run; marca awaiting_import
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={"modules": ["vulnerabilities"], "connector_sources": {},
                  "execute": True},
        )
        body = r.json()
        assert body["progress"]["vulnerabilities"]["status"] == "awaiting_import"

    @pytest.mark.asyncio
    async def test_all_modules_executed(self, async_client, db, monkeypatch):
        _, project_id = await setup_test_project(db)
        tls = make_tls_checker({"api.example.com": [
            {"control_id": "tls_version", "estado": "pass",
             "medidas_ens": ["mp.com.2"]},
        ]})
        data = make_data_fetcher({"aws": [
            {"nombre": "bkt", "tipo": "cloud_storage",
             "ubicacion": "aws:s3:bkt", "sample_text": "DNI 12345678Z",
             "cifrado_en_reposo": True},
        ]})
        patch_extras(monkeypatch, fqdns=["api.example.com"], tls=tls, data=data)
        r = await async_client.post(
            f"{BASE}/projects/{project_id}/runs",
            json={
                "modules": ["configurations", "data", "vulnerabilities"],
                "connector_sources": {"aws": {}},
                "execute": True,
            },
        )
        body = r.json()
        assert body["progress"]["configurations"]["status"] == "completed"
        assert body["progress"]["data"]["status"] == "completed"
        assert body["progress"]["vulnerabilities"]["status"] == "awaiting_import"
