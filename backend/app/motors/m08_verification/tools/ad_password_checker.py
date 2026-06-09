"""M8 v5.1 — AD password policy checker (via LDAP).

Si el cliente tiene Active Directory accesible (puerto 389/636) y
M22 ha capturado credenciales LDAP read-only del bind, este runner
consulta la politica de contrasenas:

- minPwdLength
- pwdProperties (complexity bit)
- maxPwdAge / minPwdAge
- lockoutThreshold
- lockoutDuration

Y compara con el baseline op.acc.5 del ENS.

Si LDAP no esta accesible (caso comun en cliente sin AD), devuelve
RunnerResult con findings=[] sin error fatal — la pipeline de M8 lo
marca como tool no-aplicable para ese proyecto.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

try:
    from ldap3 import Server, Connection, ALL, NTLM, SUBTREE
    HAS_LDAP3 = True
except ImportError:  # pragma: no cover
    HAS_LDAP3 = False

from .base import (
    FindingCandidate,
    RunnerResult,
    RunnerInvocationError,
    RunnerNotInstalled,
    excerpt,
    hash_output,
    normalize_severity,
)


# Baseline ENS para password policy (op.acc.5)
ENS_PASSWORD_BASELINE = {
    "min_length": 12,           # "minPwdLength" >= 12
    "complexity_required": True,# pwdProperties bit 0x1
    "max_age_days": 90,         # maxPwdAge <= 90 dias
    "lockout_threshold": 5,     # despues de 5 fallos
    "lockout_duration_min": 15, # minimo
}


class AdPasswordChecker:
    TOOL = "ad_password_policy"
    DEFAULT_TIMEOUT_SECONDS = 30

    @classmethod
    def is_available(cls) -> bool:
        return HAS_LDAP3

    @classmethod
    def ensure_available(cls) -> None:
        if not cls.is_available():
            raise RunnerNotInstalled(
                "ldap3 no esta instalado. pip install ldap3>=2.9"
            )

    @classmethod
    async def run(
        cls,
        targets: list[str],          # [ldap_url, ...]
        *,
        timeout_seconds: int | None = None,
        bind_user: str | None = None,
        bind_password: str | None = None,
        base_dn: str | None = None,
    ) -> RunnerResult:
        started = datetime.now(timezone.utc)

        # SAN-B.MB-7.bis · MCP wire-up · fallback subprocess transparente
        from backend.app.mcp_client import try_invoke_mcp_or_none
        from backend.app.motors.m08_verification.tools.base import (
            runner_result_from_mcp,
        )
        if bind_user and bind_password and base_dn:
            mcp_resp = await try_invoke_mcp_or_none(
                server="cracking", tool="ad_password_policy_check",
                args={
                    "target": targets[0] if targets else "",
                    "bind_user": bind_user,
                    "bind_password": bind_password,
                    "base_dn": base_dn,
                },
                timeout_seconds=timeout_seconds or cls.DEFAULT_TIMEOUT_SECONDS,
            )
            if mcp_resp is not None:
                return runner_result_from_mcp(mcp_resp, cls.TOOL, targets, started)

        cls.ensure_available()
        findings: list[FindingCandidate] = []
        raw_dump = []

        for ldap_url in targets:
            try:
                policy, raw = cls._fetch_policy(
                    ldap_url, bind_user, bind_password, base_dn,
                )
                raw_dump.append(raw)
                findings.extend(cls._evaluate_policy(policy, ldap_url))
            except RunnerInvocationError as exc:
                raw_dump.append(f"=== {ldap_url} === ERROR: {exc}")

        raw_bytes = "\n\n".join(raw_dump).encode("utf-8")
        return RunnerResult(
            tool=cls.TOOL,
            targets=targets,
            started_at=started,
            finished_at=datetime.now(timezone.utc),
            return_code=0,
            raw_output=raw_bytes,
            raw_output_hash=hash_output(raw_bytes),
            raw_output_path=None,
            findings=findings,
        )

    @classmethod
    def _fetch_policy(
        cls,
        ldap_url: str,
        bind_user: str | None,
        bind_password: str | None,
        base_dn: str | None,
    ) -> tuple[dict[str, Any], str]:
        if not bind_user or not bind_password:
            return {}, f"=== {ldap_url} === SKIP (sin credenciales)"
        try:
            server = Server(ldap_url, get_info=ALL)
            conn = Connection(
                server, user=bind_user, password=bind_password,
                authentication=NTLM if "\\" in (bind_user or "") else None,
                auto_bind=True,
            )
        except Exception as exc:
            raise RunnerInvocationError(f"LDAP bind fallo: {exc}") from exc

        try:
            base = base_dn or server.info.naming_contexts[0]
        except Exception:
            base = base_dn or "DC=example,DC=local"

        try:
            conn.search(
                base, "(objectClass=domainDNS)",
                attributes=[
                    "minPwdLength", "pwdProperties",
                    "maxPwdAge", "minPwdAge",
                    "lockoutThreshold", "lockoutDuration",
                ],
                search_scope=SUBTREE,
            )
            entries = list(conn.entries)
        except Exception as exc:
            raise RunnerInvocationError(f"LDAP search fallo: {exc}") from exc
        finally:
            try:
                conn.unbind()
            except Exception:
                pass

        if not entries:
            return {}, f"=== {ldap_url} === sin entradas domainDNS"

        e = entries[0]
        policy = {
            "min_length": int(e.minPwdLength.value or 0),
            "complexity_required": bool((int(e.pwdProperties.value or 0) & 1)),
            "max_age_days": _ad_filetime_to_days(e.maxPwdAge.value),
            "lockout_threshold": int(e.lockoutThreshold.value or 0),
            "lockout_duration_min": _ad_filetime_to_minutes(e.lockoutDuration.value),
        }
        return policy, f"=== {ldap_url} ===\n{policy}"

    @classmethod
    def _evaluate_policy(
        cls, policy: dict[str, Any], host: str,
    ) -> list[FindingCandidate]:
        if not policy:
            return []
        findings: list[FindingCandidate] = []
        if policy["min_length"] < ENS_PASSWORD_BASELINE["min_length"]:
            findings.append(_ad_finding(
                "AD: longitud minima de contrasena insuficiente",
                f"minPwdLength={policy['min_length']} < baseline ENS "
                f"({ENS_PASSWORD_BASELINE['min_length']}).",
                "high", host,
            ))
        if not policy["complexity_required"] and ENS_PASSWORD_BASELINE["complexity_required"]:
            findings.append(_ad_finding(
                "AD: complejidad de contrasena no exigida",
                "El bit pwdProperties=0x1 (complexity) no esta activo.",
                "medium", host,
            ))
        if policy["max_age_days"] > ENS_PASSWORD_BASELINE["max_age_days"]:
            findings.append(_ad_finding(
                "AD: maxPwdAge excede baseline",
                f"maxPwdAge={policy['max_age_days']} dias > "
                f"{ENS_PASSWORD_BASELINE['max_age_days']} dias.",
                "low", host,
            ))
        if policy["lockout_threshold"] == 0 or policy["lockout_threshold"] > ENS_PASSWORD_BASELINE["lockout_threshold"]:
            findings.append(_ad_finding(
                "AD: bloqueo de cuenta sin umbral o muy permisivo",
                f"lockoutThreshold={policy['lockout_threshold']} (0=sin "
                f"bloqueo). Baseline ENS: <={ENS_PASSWORD_BASELINE['lockout_threshold']}.",
                "high", host,
            ))
        return findings

    @classmethod
    def parse_output(cls, raw: bytes) -> list[FindingCandidate]:
        # No re-parseable: el output es solo dump textual de la policy.
        return []


def _ad_filetime_to_days(value: int | None) -> int:
    """AD almacena edades como negativos en intervalos de 100ns. -864e9 = 1 dia."""
    if not value:
        return 0
    interval_per_day = 864_000_000_000  # 100ns
    return int(abs(int(value)) // interval_per_day)


def _ad_filetime_to_minutes(value: int | None) -> int:
    if not value:
        return 0
    interval_per_min = 600_000_000  # 100ns
    return int(abs(int(value)) // interval_per_min)


def _ad_finding(
    title: str, description: str, severity: str, host: str,
) -> FindingCandidate:
    return {
        "title": title,
        "description": description,
        "severity": normalize_severity(severity),
        "cve_id": None,
        "cvss_score": None,
        "cvss_vector": None,
        "cwe_id": "CWE-521",  # Weak Password Requirements
        "affected_host": host,
        "affected_port": 389,
        "affected_service": "ldap",
        "affected_service_version": None,
        "affected_url": None,
        "affected_os": "windows",
        "raw_output_excerpt": excerpt(description),
        "tool": "ad_password_policy",
        "tool_metadata": {"baseline": "op.acc.5"},
    }
