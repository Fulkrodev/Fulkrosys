"""M8 v5.1 — OpenVAS runner (Sesion 10 Paso 4.3).

Wrapper Greenbone GVM (Greenbone Vulnerability Manager) para scanning de
vulnerabilidades. Escala el stub 43 LOC original a runner completo con 3
modos analogos a Prowler/ScoutSuite:

- ``fixture`` (default tests): lee XML GMP pre-grabado. Determinista,
  sin Docker ni python-gvm requerido.
- ``mock``: fixture minimal sintetico (sin XML externo). Util para smoke
  tests rapidos.
- ``real``: conecta al container Greenbone Community Edition via GMP
  (TLS sobre TCP 9390 por default) usando ``python-gvm``. Crea target,
  lanza task, poll hasta completar, recupera report XML, parsea.

Requisitos para modo real (checkeados degradandose controlado):
  1. ``python-gvm`` instalado (en dev deps).
  2. Container OpenVAS corriendo en ``GVM_HOST:GVM_PORT``.
  3. Credenciales ``GVM_USERNAME`` + ``GVM_PASSWORD`` en env.
  4. Feed NVT sincronizado (container debe llevar ~45 min vivo).

Si falta 1/2/3 el runner devuelve ``RunnerResult`` con ``error`` y
``findings=[]`` sin levantar excepciones — consistente con el resto de
tools M8.

Docker compose para levantar el container local esta en
``backend/mcp_servers/docker-compose.pentest.yml`` (servicio ``openvas``),
y hay un helper bash en ``backend/scripts/start_openvas_container.sh``.
"""
from __future__ import annotations

import logging
import os
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Sequence

from .base import (
    BaseRunner,
    FindingCandidate,
    RunnerResult,
    excerpt,
    normalize_severity,
)
from .openvas_ens_mapper import (
    describe_ens_measure,
    map_finding_to_ens,
)

logger = logging.getLogger(__name__)


OpenVASMode = Literal["fixture", "mock", "real"]


# Mapping threat GMP -> severity normalizada.
_THREAT_TO_SEVERITY: dict[str, str] = {
    "high": "high",
    "medium": "medium",
    "low": "low",
    "log": "info",
    "debug": "info",
    "false positive": "info",
}


# Config IDs canonicos de Greenbone (ver docs oficial).
DEFAULT_SCAN_CONFIGS: dict[str, str] = {
    "full_and_fast": "daba56c8-73ec-11df-a475-002264764cea",
    "full_and_very_deep": "698f691e-7489-11df-9d8c-002264764cea",
    "system_discovery": "8715c877-47a0-438d-98a3-27c7a6ab2196",
}


class OpenvasRunner(BaseRunner):
    TOOL = "openvas"
    BINARY = "gvm-cli"   # client CLI; daemon es 'gvmd' aparte
    DEFAULT_TIMEOUT_SECONDS = 30 * 60  # 30 min por scan

    # ══════════════════════════════════════════════════════════════
    # API publica
    # ══════════════════════════════════════════════════════════════

    @classmethod
    async def run(
        cls,
        targets: Sequence[str],
        *,
        timeout_seconds: int | None = None,
        scan_config: str = "full_and_fast",
    ) -> RunnerResult:
        return await cls.run_mode(
            targets, mode="real", timeout_seconds=timeout_seconds,
            scan_config=scan_config,
        )

    @classmethod
    async def run_mode(
        cls,
        targets: Sequence[str],
        *,
        mode: OpenVASMode = "fixture",
        timeout_seconds: int | None = None,
        scan_config: str = "full_and_fast",
        fixture_path: Path | None = None,
    ) -> RunnerResult:
        started = datetime.now(timezone.utc)
        targets_list = list(targets)

        # SAN-B.MB-7.bis · MCP wire-up (real mode only · fixture/mock para tests)
        if mode == "real":
            from backend.app.mcp_client import try_invoke_mcp_or_none
            mcp_resp = await try_invoke_mcp_or_none(
                server="vulnscan", tool="openvas_scan",
                args={"target": targets_list[0] if targets_list else "", "scan_config": scan_config},
                timeout_seconds=timeout_seconds or cls.DEFAULT_TIMEOUT_SECONDS,
            )
            if mcp_resp is not None:
                return cls.from_mcp_response(mcp_resp, targets_list, started)

        if mode == "fixture":
            return cls._run_fixture(targets_list, started, fixture_path)
        if mode == "mock":
            return cls._run_mock(targets_list, started, fixture_path)
        if mode == "real":
            return await cls._run_real(
                targets_list, started,
                scan_config=scan_config,
                timeout_seconds=timeout_seconds or cls.DEFAULT_TIMEOUT_SECONDS,
            )
        raise ValueError(f"openvas: mode invalido {mode!r}")

    # ══════════════════════════════════════════════════════════════
    # Modo fixture
    # ══════════════════════════════════════════════════════════════

    @classmethod
    def _run_fixture(
        cls,
        targets: list[str],
        started: datetime,
        fixture_path: Path | None,
    ) -> RunnerResult:
        if fixture_path is None or not fixture_path.exists():
            return cls.make_result(
                targets=targets, started_at=started, return_code=0,
                raw_output=b"", findings=[],
                error=f"fixture path no existe: {fixture_path!r}",
            )
        raw = fixture_path.read_bytes()
        findings = cls.parse_output(raw)
        return cls.make_result(
            targets=targets, started_at=started, return_code=0,
            raw_output=raw, findings=findings,
        )

    # ══════════════════════════════════════════════════════════════
    # Modo mock — XML sintetico inline o fixture
    # ══════════════════════════════════════════════════════════════

    @classmethod
    def _run_mock(
        cls,
        targets: list[str],
        started: datetime,
        fixture_path: Path | None,
    ) -> RunnerResult:
        if fixture_path and fixture_path.exists():
            return cls._run_fixture(targets, started, fixture_path)
        raw = cls._synthetic_mock_xml()
        findings = cls.parse_output(raw)
        return cls.make_result(
            targets=targets, started_at=started, return_code=0,
            raw_output=raw, findings=findings,
        )

    @staticmethod
    def _synthetic_mock_xml() -> bytes:
        return (
            '<?xml version="1.0"?>'
            '<get_reports_response status="200" status_text="OK">'
            '<report id="mock-report"><results>'
            '<result><name>Mock HTTP Server Info</name>'
            '<host>127.0.0.1</host><port>80/tcp</port>'
            '<nvt oid="mock.0.0.0.1"><name>HTTP Server Info</name>'
            '<family>Service detection</family><cvss_base>0.0</cvss_base></nvt>'
            '<threat>Log</threat><severity>0.0</severity>'
            '<description>mock synthetic finding</description>'
            '</result>'
            '</results></report>'
            '</get_reports_response>'
        ).encode("utf-8")

    # ══════════════════════════════════════════════════════════════
    # Modo real — GMP via python-gvm
    # ══════════════════════════════════════════════════════════════

    @classmethod
    async def _run_real(
        cls,
        targets: list[str],
        started: datetime,
        *,
        scan_config: str,
        timeout_seconds: int,
    ) -> RunnerResult:
        try:
            from gvm.connections import TLSConnection  # type: ignore
            from gvm.protocols.gmp import Gmp  # type: ignore
            from gvm.transforms import EtreeTransform  # type: ignore
        except ImportError as exc:
            return cls.make_result(
                targets=targets, started_at=started, return_code=0,
                raw_output=b"", findings=[],
                error=f"python-gvm no instalado: {exc}",
            )

        gvm_host = os.environ.get("GVM_HOST", "")
        gvm_port = int(os.environ.get("GVM_PORT", "9390") or 9390)
        gvm_user = os.environ.get("GVM_USERNAME", "")
        gvm_pass = os.environ.get("GVM_PASSWORD", "")
        if not gvm_host or not gvm_user or not gvm_pass:
            return cls.make_result(
                targets=targets, started_at=started, return_code=0,
                raw_output=b"", findings=[],
                error=(
                    "gvm_credentials_missing: set GVM_HOST + GVM_USERNAME + "
                    "GVM_PASSWORD. Container: docker compose -f "
                    "backend/mcp_servers/docker-compose.pentest.yml up -d openvas"
                ),
            )

        scan_config_id = DEFAULT_SCAN_CONFIGS.get(
            scan_config, DEFAULT_SCAN_CONFIGS["full_and_fast"],
        )

        import asyncio
        try:
            raw_xml = await asyncio.to_thread(
                cls._gmp_full_scan_cycle,
                TLSConnection, Gmp, EtreeTransform,
                hostname=gvm_host, port=gvm_port,
                username=gvm_user, password=gvm_pass,
                targets=targets, scan_config_id=scan_config_id,
                timeout_seconds=timeout_seconds,
            )
        except Exception as exc:  # pragma: no cover — requiere container real
            return cls.make_result(
                targets=targets, started_at=started, return_code=1,
                raw_output=b"", findings=[],
                error=f"gmp_scan_failed: {type(exc).__name__}: {exc}",
            )
        findings = cls.parse_output(raw_xml) if raw_xml else []
        return cls.make_result(
            targets=targets, started_at=started, return_code=0,
            raw_output=raw_xml or b"", findings=findings,
        )

    @staticmethod
    def _gmp_full_scan_cycle(
        TLSConnection, Gmp, EtreeTransform,
        *, hostname: str, port: int, username: str, password: str,
        targets: list[str], scan_config_id: str, timeout_seconds: int,
    ) -> bytes:  # pragma: no cover — requiere container real
        """Ciclo completo GMP (sincrono). NO se ejecuta en tests unitarios."""
        import time

        conn = TLSConnection(hostname=hostname, port=port, timeout=30)
        with Gmp(connection=conn, transform=EtreeTransform()) as gmp:
            gmp.authenticate(username=username, password=password)
            target_resp = gmp.create_target(
                name=f"fulkro-target-{uuid.uuid4().hex[:8]}",
                hosts=targets,
            )
            target_id = target_resp.get("id")

            task_resp = gmp.create_task(
                name=f"fulkro-scan-{uuid.uuid4().hex[:8]}",
                config_id=scan_config_id,
                target_id=target_id,
            )
            task_id = task_resp.get("id")

            gmp.start_task(task_id)

            deadline = time.monotonic() + timeout_seconds
            while time.monotonic() < deadline:
                status_resp = gmp.get_task(task_id)
                status = status_resp.findtext(".//status", default="")
                if status in ("Done", "Stopped", "Interrupted"):
                    break
                time.sleep(30)

            report_resp = gmp.get_report(task_id)
            return ET.tostring(report_resp, encoding="utf-8")

    # ══════════════════════════════════════════════════════════════
    # Parser XML GMP -> FindingCandidate
    # ══════════════════════════════════════════════════════════════

    @classmethod
    def parse_output(cls, raw: bytes) -> list[FindingCandidate]:
        if not raw:
            return []
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            return []

        findings: list[FindingCandidate] = []
        for result in root.iter("result"):
            name = (result.findtext("name") or "").strip()

            host_el = result.find("host")
            host_text = ""
            hostname = ""
            if host_el is not None:
                if host_el.text:
                    host_text = host_el.text.strip()
                hostname_el = host_el.find("hostname")
                if hostname_el is not None and hostname_el.text:
                    hostname = hostname_el.text.strip()
            affected_host = hostname or host_text or "unknown"

            port_full = (result.findtext("port") or "").strip()
            port_num: int | None = None
            if "/" in port_full:
                try:
                    port_num = int(port_full.split("/")[0])
                except ValueError:
                    port_num = None

            nvt = result.find("nvt")
            nvt_oid = nvt.get("oid") if nvt is not None else ""
            nvt_name = (nvt.findtext("name") if nvt is not None else "") or name
            nvt_family = (nvt.findtext("family") if nvt is not None else "") or ""
            cvss_str = (nvt.findtext("cvss_base") if nvt is not None else "") or ""
            try:
                cvss = float(cvss_str) if cvss_str else 0.0
            except ValueError:
                cvss = 0.0
            cve_refs: list[str] = []
            if nvt is not None:
                refs_el = nvt.find("refs")
                if refs_el is not None:
                    for ref in refs_el.findall("ref"):
                        if ref.get("type") == "cve" and ref.get("id"):
                            cve_refs.append(ref.get("id"))

            threat = (result.findtext("threat") or "").strip().lower()
            severity_raw = (result.findtext("severity") or "0").strip()
            try:
                severity_num = float(severity_raw)
            except ValueError:
                severity_num = 0.0
            normalized = normalize_severity(_THREAT_TO_SEVERITY.get(threat, "info"))

            description = (result.findtext("description") or "").strip()

            ens_measures = map_finding_to_ens(nvt_family, nvt_name, cvss)

            findings.append({
                "title": nvt_name[:200],
                "description": description[:1000],
                "severity": normalized,
                "cve_id": cve_refs[0] if cve_refs else None,
                "cvss_score": cvss if cvss > 0 else None,
                "cvss_vector": None,
                "cwe_id": None,
                "affected_host": affected_host,
                "affected_port": port_num,
                "affected_service": None,
                "affected_service_version": None,
                "affected_url": None,
                "affected_os": None,
                "raw_output_excerpt": excerpt(ET.tostring(result, encoding="unicode")),
                "tool": "openvas",
                "tool_metadata": {
                    "nvt_oid": nvt_oid,
                    "nvt_family": nvt_family,
                    "threat": threat,
                    "severity_cvss": severity_num,
                    "cve_refs": cve_refs,
                    "ens_measures": ens_measures,
                    "ens_measures_labels": [describe_ens_measure(m) for m in ens_measures],
                },
            })
        return findings

    # ══════════════════════════════════════════════════════════════
    # Reporting helper
    # ══════════════════════════════════════════════════════════════

    @classmethod
    def summarize(cls, findings: list[FindingCandidate]) -> dict[str, Any]:
        by_sev: dict[str, int] = {}
        by_family: dict[str, int] = {}
        ens_hits: dict[str, int] = {}
        cve_count = 0
        for f in findings:
            sev = str(f.get("severity", "info"))
            by_sev[sev] = by_sev.get(sev, 0) + 1
            md = f.get("tool_metadata", {}) or {}
            fam = md.get("nvt_family") or "unknown"
            by_family[fam] = by_family.get(fam, 0) + 1
            if md.get("cve_refs"):
                cve_count += len(md["cve_refs"])
            for m in md.get("ens_measures", []):
                ens_hits[m] = ens_hits.get(m, 0) + 1
        return {
            "total": len(findings),
            "by_severity": by_sev,
            "by_family": by_family,
            "cve_references_total": cve_count,
            "ens_measures_hit": ens_hits,
            "ens_measures_unique": sorted(ens_hits.keys()),
        }


# Alias camelcase para quien lo busque por nombre canonico Greenbone.
OpenVASRunner = OpenvasRunner
