"""M8 v5.1 — ScoutSuite runner multi-cloud (Sesion 10 Paso 4.2).

ScoutSuite (NCC Group) audita cuentas cloud AWS/Azure/GCP/Aliyun/Oracle.
El runner cubre AWS (complementario a Prowler), Azure y GCP (coberturas
unicas). Emite findings normalizados al mismo schema ``FindingCandidate``
que el resto de tools M8.

Output nativo ScoutSuite es un directorio con:
    scoutsuite-report/
      scoutsuite-results/
        scoutsuite_results_<provider>-<account_id>.js   (JS wrapper JSON)

La estructura dentro del ``.js`` es:
    scoutsuite_results = {
      "provider_code": "aws" | "azure" | "gcp",
      "account_id": "...",
      "services": {
        "<service>": {
          "findings": {
            "<finding_id>": {
              "description": "...",
              "level": "info" | "warning" | "danger",
              "checked_items": N, "flagged_items": M,
              "items": [<resource_id>, ...],
              "rationale": "...",
              "remediation": "...",
              "dashboard_name": "..."
            }
          }
        }
      }
    }

Tres modos de ejecucion (mismo contrato que Prowler 4.1):

- ``fixture``: lee JSON con la estructura ScoutSuite directamente (fixtures
  sin el wrapper ``scoutsuite_results =`` para que sean JSON validos).
- ``mock`` (AWS only): moto levanta IAM+CloudTrail+EC2 seed, el runner
  introspecta y produce JSON con la forma ScoutSuite. Azure/GCP no tienen
  equivalente moto reutilizable -> ``mock`` con provider distinto de AWS
  devuelve resultado vacio + warning.
- ``real``: ejecuta ``scout <provider> --no-browser --report-dir <tmp>``.
  Requiere binario ``scout`` en PATH y credenciales del provider.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Sequence

from .base import (
    BaseRunner,
    FindingCandidate,
    RunnerResult,
    excerpt,
    is_binary_available,
    normalize_severity,
    run_subprocess,
)
from .scoutsuite_cloud_ens_mapper import (
    detect_provider_from_check,
    describe_ens_measure,
    map_check_to_ens,
)

logger = logging.getLogger(__name__)


ScoutSuiteMode = Literal["fixture", "mock", "real"]


# Mapeo level ScoutSuite -> severity normalizada FULKRO
_LEVEL_TO_SEVERITY: dict[str, str] = {
    "danger": "high",     # ScoutSuite 'danger' = problema serio (no critical por defecto)
    "warning": "medium",
    "info": "info",
}


# ────────────────────────────────────────────────────────────────────
# Runner
# ────────────────────────────────────────────────────────────────────


class ScoutSuiteRunner(BaseRunner):
    TOOL = "scoutsuite"
    BINARY = "scout"
    DEFAULT_TIMEOUT_SECONDS = 60 * 60  # 60 min

    # ══════════════════════════════════════════════════════════════
    # API publica
    # ══════════════════════════════════════════════════════════════

    @classmethod
    async def run(
        cls,
        targets: Sequence[str],
        *,
        timeout_seconds: int | None = None,
        provider: str = "aws",
    ) -> RunnerResult:
        return await cls.run_mode(
            targets, mode="real", timeout_seconds=timeout_seconds, provider=provider,
        )

    @classmethod
    async def run_mode(
        cls,
        targets: Sequence[str],
        *,
        mode: ScoutSuiteMode = "fixture",
        timeout_seconds: int | None = None,
        provider: str = "aws",
        fixture_path: Path | None = None,
        services: Sequence[str] = (),
    ) -> RunnerResult:
        started = datetime.now(timezone.utc)
        targets_list = list(targets)

        # SAN-B.MB-7.bis · MCP wire-up (real mode only · fixture/mock para tests)
        if mode == "real":
            from backend.app.mcp_client import try_invoke_mcp_or_none
            mcp_resp = await try_invoke_mcp_or_none(
                server="cloud", tool="scoutsuite_audit",
                args={"target": targets_list[0] if targets_list else "", "provider": provider},
                timeout_seconds=timeout_seconds or cls.DEFAULT_TIMEOUT_SECONDS,
            )
            if mcp_resp is not None:
                return cls.from_mcp_response(mcp_resp, targets_list, started)

        if mode == "fixture":
            return cls._run_fixture(targets_list, started, fixture_path)
        if mode == "mock":
            return cls._run_mock(targets_list, started, provider, services)
        if mode == "real":
            return await cls._run_real(
                targets_list, started,
                provider=provider, timeout_seconds=timeout_seconds,
                services=services,
            )
        raise ValueError(f"scoutsuite: mode invalido {mode!r}")

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
    # Modo mock — AWS only via moto
    # ══════════════════════════════════════════════════════════════

    @classmethod
    def _run_mock(
        cls,
        targets: list[str],
        started: datetime,
        provider: str,
        services: Sequence[str],
    ) -> RunnerResult:
        if provider != "aws":
            return cls.make_result(
                targets=targets, started_at=started, return_code=0,
                raw_output=b"", findings=[],
                error=(
                    f"scoutsuite mock: provider {provider!r} no soportado via "
                    f"moto. Use mode=fixture para Azure/GCP."
                ),
            )
        try:
            from moto import mock_aws  # type: ignore
        except ImportError:
            return cls.make_result(
                targets=targets, started_at=started, return_code=0,
                raw_output=b"moto not installed", findings=[],
                error="moto no instalado: pip install 'moto[iam,s3,ec2]>=5.0'",
            )

        with mock_aws():
            cls._seed_mock_aws_environment(services)
            payload = cls._introspect_mock_aws_as_scoutsuite(services)

        raw = json.dumps(payload).encode("utf-8")
        findings = cls.parse_output(raw)
        return cls.make_result(
            targets=targets, started_at=started, return_code=0,
            raw_output=raw, findings=findings,
        )

    @staticmethod
    def _seed_mock_aws_environment(services: Sequence[str]) -> None:
        """Crea recursos AWS con riesgos tipicos ScoutSuite."""
        import boto3  # type: ignore

        region = "eu-central-1"
        # IAM: usuario con password + sin MFA + multi access keys
        if not services or "iam" in services:
            iam = boto3.client("iam", region_name=region)
            iam.create_user(UserName="fulkro-admin")
            iam.create_login_profile(
                UserName="fulkro-admin", Password="AdminTemp1!",
                PasswordResetRequired=False,
            )
            # Crear dos access keys (multi-keys warning)
            iam.create_access_key(UserName="fulkro-admin")
            iam.create_access_key(UserName="fulkro-admin")
        # CloudTrail: ningun trail global (findings "no-global-trail")
        # Moto tiene CloudTrail backend; no creamos ningun trail para
        # reproducir la condicion.

    @staticmethod
    def _introspect_mock_aws_as_scoutsuite(services: Sequence[str]) -> dict:
        """Genera el JSON ScoutSuite desde el estado moto."""
        import boto3  # type: ignore

        region = "eu-central-1"
        account_id = "123456789012"
        payload: dict[str, Any] = {
            "last_run": {"time": datetime.now(timezone.utc).isoformat()},
            "provider_code": "aws",
            "provider_name": "Amazon Web Services",
            "account_id": account_id,
            "services": {},
        }

        iam_findings: dict[str, dict] = {}
        if not services or "iam" in services:
            iam = boto3.client("iam", region_name=region)
            users = iam.list_users().get("Users", [])
            mfaless_items: list[str] = []
            multi_key_items: list[str] = []
            for user in users:
                name = user["UserName"]
                arn = user["Arn"]
                try:
                    iam.get_login_profile(UserName=name)
                    has_console = True
                except iam.exceptions.NoSuchEntityException:
                    has_console = False
                if has_console:
                    if not iam.list_mfa_devices(UserName=name).get("MFADevices", []):
                        mfaless_items.append(arn)
                keys = iam.list_access_keys(UserName=name).get("AccessKeyMetadata", [])
                active_keys = [k for k in keys if k.get("Status") == "Active"]
                if len(active_keys) > 1:
                    multi_key_items.append(arn)
            if mfaless_items:
                iam_findings["iam-user-with-password-and-no-mfa"] = {
                    "description": "IAM user with console access and no MFA",
                    "level": "danger", "checked_items": len(users),
                    "flagged_items": len(mfaless_items), "items": mfaless_items,
                }
            if multi_key_items:
                iam_findings["iam-user-with-multiple-access-keys"] = {
                    "description": "IAM user with more than one active key",
                    "level": "warning", "checked_items": len(users),
                    "flagged_items": len(multi_key_items), "items": multi_key_items,
                }

        cloudtrail_findings: dict[str, dict] = {}
        if not services or "cloudtrail" in services:
            ct = boto3.client("cloudtrail", region_name=region)
            trails = ct.describe_trails().get("trailList", [])
            global_trails = [t for t in trails if t.get("IsMultiRegionTrail")]
            if not global_trails:
                cloudtrail_findings["cloudtrail-no-global-trail"] = {
                    "description": "No multi-region CloudTrail configured",
                    "level": "danger", "checked_items": 1, "flagged_items": 1,
                    "items": [],
                }

        if iam_findings:
            payload["services"]["iam"] = {"findings": iam_findings}
        if cloudtrail_findings:
            payload["services"]["cloudtrail"] = {"findings": cloudtrail_findings}
        return payload

    # ══════════════════════════════════════════════════════════════
    # Modo real — subprocess scout
    # ══════════════════════════════════════════════════════════════

    @classmethod
    async def _run_real(
        cls,
        targets: list[str],
        started: datetime,
        *,
        provider: str,
        timeout_seconds: int | None,
        services: Sequence[str],
    ) -> RunnerResult:
        if not is_binary_available(cls.BINARY):
            return cls.make_result(
                targets=targets, started_at=started, return_code=0,
                raw_output=b"scout binary not available", findings=[],
                error="scoutsuite_not_installed",
            )
        if not cls._provider_credentials_available(provider):
            return cls.make_result(
                targets=targets, started_at=started, return_code=0,
                raw_output=b"provider credentials missing", findings=[],
                error=f"{provider}_credentials_missing",
            )

        with tempfile.TemporaryDirectory(prefix="scoutsuite-") as tmpdir:
            report_dir = Path(tmpdir)
            cmd = [cls.BINARY, provider, "--no-browser", "--report-dir", str(report_dir)]
            if services:
                cmd += ["--services", *services]
            rc, stdout, stderr, timed_out = await run_subprocess(
                cmd, timeout_seconds=(timeout_seconds or cls.DEFAULT_TIMEOUT_SECONDS),
            )
            # Busca el scoutsuite_results_<provider>-<id>.js generado
            raw_payload = cls._read_scoutsuite_report_dir(report_dir, provider)

        findings = cls.parse_output(raw_payload) if raw_payload else []
        return cls.make_result(
            targets=targets, started_at=started, return_code=rc,
            raw_output=raw_payload or stdout, findings=findings,
            error=(stderr.decode(errors="replace") if rc != 0 else None),
            timed_out=timed_out,
        )

    @staticmethod
    def _provider_credentials_available(provider: str) -> bool:
        if provider == "aws":
            return bool(os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY")) \
                or os.path.exists(os.path.expanduser("~/.aws/credentials"))
        if provider == "azure":
            return bool(os.getenv("AZURE_TENANT_ID") or os.path.exists(os.path.expanduser("~/.azure/credentials")))
        if provider == "gcp":
            return bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
        return False

    @staticmethod
    def _read_scoutsuite_report_dir(report_dir: Path, provider: str) -> bytes:
        """Lee scoutsuite_results_<provider>-*.js y extrae el JSON."""
        candidates = list(report_dir.rglob(f"scoutsuite_results_{provider}-*.js"))
        if not candidates:
            return b""
        content = candidates[0].read_text(encoding="utf-8", errors="replace")
        # Strip wrapper 'scoutsuite_results = ' si existe
        idx = content.find("=")
        if idx != -1 and content[:idx].strip() == "scoutsuite_results":
            content = content[idx + 1:].strip().rstrip(";")
        return content.encode("utf-8")

    # ══════════════════════════════════════════════════════════════
    # Parser — JSON ScoutSuite anidado -> FindingCandidate planos
    # ══════════════════════════════════════════════════════════════

    @classmethod
    def parse_output(cls, raw: bytes) -> list[FindingCandidate]:
        if not raw:
            return []
        text = raw.decode("utf-8", errors="replace").strip()
        # Tolerante al wrapper 'scoutsuite_results = {...};'
        if text.startswith("scoutsuite_results"):
            idx = text.find("=")
            if idx != -1:
                text = text[idx + 1:].strip().rstrip(";")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return []
        if not isinstance(payload, dict):
            return []
        services_map = payload.get("services", {}) or {}
        if not isinstance(services_map, dict):
            return []

        provider = payload.get("provider_code") or "cloud"
        account = payload.get("account_id") or ""
        findings_out: list[FindingCandidate] = []

        for service_name, svc_body in services_map.items():
            if not isinstance(svc_body, dict):
                continue
            svc_findings = svc_body.get("findings", {}) or {}
            if not isinstance(svc_findings, dict):
                continue
            for finding_id, body in svc_findings.items():
                if not isinstance(body, dict):
                    continue
                flagged = int(body.get("flagged_items", 0) or 0)
                if flagged == 0:
                    # findings con 0 items flaggeados son "passes" informativos
                    continue
                level = str(body.get("level", "info")).lower()
                severity = normalize_severity(_LEVEL_TO_SEVERITY.get(level, level))
                items = body.get("items") or []
                if not isinstance(items, list):
                    items = []
                ens_measures = map_check_to_ens(finding_id)
                detected_provider = detect_provider_from_check(finding_id) or provider
                raw_snippet = json.dumps({"finding_id": finding_id, **body})
                if items:
                    # Un finding por item (cada resource afectado = finding)
                    for resource in items:
                        findings_out.append(cls._build_finding(
                            finding_id=finding_id, provider=detected_provider,
                            service=service_name, severity=severity,
                            resource=str(resource), account=account,
                            body=body, ens_measures=ens_measures,
                            raw_excerpt=excerpt(raw_snippet),
                        ))
                else:
                    # Finding sin items (config global del servicio)
                    findings_out.append(cls._build_finding(
                        finding_id=finding_id, provider=detected_provider,
                        service=service_name, severity=severity,
                        resource=f"{detected_provider}:{service_name}",
                        account=account, body=body, ens_measures=ens_measures,
                        raw_excerpt=excerpt(raw_snippet),
                    ))
        return findings_out

    @classmethod
    def _build_finding(
        cls, *, finding_id: str, provider: str, service: str, severity: str,
        resource: str, account: str, body: dict, ens_measures: list[str],
        raw_excerpt: str,
    ) -> FindingCandidate:
        return {
            "title": body.get("description", finding_id)[:200],
            "description": (body.get("rationale") or body.get("description") or "")[:1000],
            "severity": severity,
            "cve_id": None, "cvss_score": None, "cvss_vector": None, "cwe_id": None,
            "affected_host": resource or "cloud",
            "affected_port": None,
            "affected_service": service,
            "affected_service_version": None,
            "affected_url": None,
            "affected_os": None,
            "raw_output_excerpt": raw_excerpt,
            "tool": "scoutsuite",
            "tool_metadata": {
                "provider": provider,
                "account_id": account,
                "check_id": finding_id,
                "service": service,
                "level": body.get("level"),
                "dashboard_name": body.get("dashboard_name"),
                "remediation": body.get("remediation"),
                "flagged_items": body.get("flagged_items"),
                "checked_items": body.get("checked_items"),
                "ens_measures": ens_measures,
                "ens_measures_labels": [describe_ens_measure(m) for m in ens_measures],
            },
        }

    # ══════════════════════════════════════════════════════════════
    # Reporting helper
    # ══════════════════════════════════════════════════════════════

    @classmethod
    def summarize(cls, findings: list[FindingCandidate]) -> dict[str, Any]:
        by_sev: dict[str, int] = {}
        ens_hits: dict[str, int] = {}
        per_provider: dict[str, int] = {}
        for f in findings:
            sev = str(f.get("severity", "info"))
            by_sev[sev] = by_sev.get(sev, 0) + 1
            md = f.get("tool_metadata", {}) or {}
            prov = md.get("provider") or "unknown"
            per_provider[prov] = per_provider.get(prov, 0) + 1
            for m in md.get("ens_measures", []):
                ens_hits[m] = ens_hits.get(m, 0) + 1
        return {
            "total": len(findings),
            "by_severity": by_sev,
            "by_provider": per_provider,
            "ens_measures_hit": ens_hits,
            "ens_measures_unique": sorted(ens_hits.keys()),
        }
