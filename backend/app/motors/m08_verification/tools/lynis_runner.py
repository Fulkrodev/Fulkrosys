"""M8 v5.1 — Lynis runner (hardening Linux).

- Comando default: ``lynis audit system --quick --no-colors``
- Timeout: 20 minutos
- Parser: report.dat (key=value lines) + suggestion[]/warning[] arrays
- Severity: warning → high, suggestion → medium, info → info

Modos soportados:
- ``local`` (default): ejecuta Lynis en el host FULKRO via subprocess.
- ``remote``: ejecuta Lynis vía SSH (paramiko) en host cliente que ya
  tiene Lynis provisionado localmente. Cierra TODO-M8-G2 (SAN-B.MB-3.bis.2).
"""
from __future__ import annotations

import asyncio
import re
import socket
from datetime import datetime, timezone
from typing import Any, Literal

from .base import (
    BaseRunner,
    FindingCandidate,
    RunnerResult,
    excerpt,
    normalize_severity,
    run_subprocess,
)


_REPORT_LINE = re.compile(r"^([a-z0-9_]+)\[\]?=(.*)$", re.IGNORECASE)

LYNIS_REMOTE_CMD = (
    "lynis audit system --quick --no-colors "
    "--logfile /dev/null --report-file /dev/stdout"
)


class LynisRunner(BaseRunner):
    TOOL = "lynis"
    BINARY = "lynis"
    DEFAULT_TIMEOUT_SECONDS = 20 * 60  # 20 min

    @classmethod
    async def run(
        cls,
        targets: list[str],          # ignorado en local; usado como host_label remote
        *,
        timeout_seconds: int | None = None,
        host_label: str = "local",
        mode: Literal["local", "remote"] = "local",
        ssh_credentials: dict | None = None,
    ) -> RunnerResult:
        if mode == "remote":
            if ssh_credentials is None:
                raise ValueError(
                    "lynis remote mode requires ssh_credentials dict "
                    "(use ssh_credentials_crypto.decrypt_credentials)"
                )
            return await cls._run_remote(
                ssh_credentials=ssh_credentials,
                targets=targets,
                timeout_seconds=timeout_seconds or cls.DEFAULT_TIMEOUT_SECONDS,
                host_label=host_label,
            )

        started = datetime.now(timezone.utc)

        # SAN-B.MB-7.bis · MCP wire-up · fallback subprocess transparente
        from backend.app.mcp_client import try_invoke_mcp_or_none
        mcp_resp = await try_invoke_mcp_or_none(
            server="infra", tool="lynis_audit",
            args={"target": targets[0] if targets else host_label},
            timeout_seconds=timeout_seconds or cls.DEFAULT_TIMEOUT_SECONDS,
        )
        if mcp_resp is not None:
            return cls.from_mcp_response(mcp_resp, targets or [host_label], started)

        cls.ensure_available()
        cmd = [
            cls.BINARY, "audit", "system", "--quick",
            "--no-colors", "--logfile", "/dev/null",
            "--report-file", "/dev/stdout",
        ]
        rc, stdout, stderr, timed_out = await run_subprocess(
            cmd, timeout_seconds=(timeout_seconds or cls.DEFAULT_TIMEOUT_SECONDS),
        )
        try:
            findings = cls.parse_output(stdout, host=host_label)
            error = None
        except Exception as exc:  # pragma: no cover
            findings = []
            error = f"parse error: {exc}"
        return cls.make_result(
            targets=targets or [host_label], started_at=started, return_code=rc,
            raw_output=stdout, findings=findings, error=error, timed_out=timed_out,
        )

    @classmethod
    async def _run_remote(
        cls,
        ssh_credentials: dict,
        targets: list[str],
        timeout_seconds: int,
        host_label: str,
    ) -> RunnerResult:
        """Ejecuta Lynis remoto vía SSH (paramiko).

        Cliente debe haber provisionado Lynis localmente en el target host
        (``apt install lynis`` o equivalente). FULKRO ssh + execute · no
        copia binario remoto.

        Errores estructurados (NO crash):
        - ``ssh_auth_failed``: credenciales rechazadas
        - ``ssh_connect_failed``: red, host inaccesible, timeout connect
        - ``lynis_not_provisioned``: ``which lynis`` retorna != 0
        - ``ssh_command_timeout``: ejecución superó timeout_seconds
        """
        import paramiko  # lazy import to avoid hard dep on import-time

        started = datetime.now(timezone.utc)
        host = ssh_credentials["host"]
        port = ssh_credentials.get("port", 22)
        user = ssh_credentials["user"]
        auth_method = ssh_credentials.get("auth_method", "key")
        targets_out = targets or [f"{host_label}:{host}"]

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            connect_kwargs: dict[str, Any] = {
                "hostname": host,
                "port": port,
                "username": user,
                "timeout": 30,
            }
            if auth_method == "key":
                connect_kwargs["key_filename"] = ssh_credentials["key_path_local"]
            elif auth_method == "password":
                connect_kwargs["password"] = ssh_credentials["password"]
            else:
                raise ValueError(
                    f"auth_method desconocido: {auth_method!r}"
                )
            await asyncio.to_thread(client.connect, **connect_kwargs)
        except paramiko.AuthenticationException as exc:
            return cls.make_result(
                targets=targets_out, started_at=started, return_code=-1,
                raw_output=b"", findings=[],
                error=f"ssh_auth_failed: {exc}", timed_out=False,
            )
        except (paramiko.SSHException, socket.error, OSError, TimeoutError, ValueError) as exc:
            return cls.make_result(
                targets=targets_out, started_at=started, return_code=-1,
                raw_output=b"", findings=[],
                error=f"ssh_connect_failed: {exc}", timed_out=False,
            )

        try:
            # Verify Lynis provisionado en remote
            stdin_, stdout_, stderr_ = await asyncio.to_thread(
                client.exec_command, "command -v lynis"
            )
            which_rc = await asyncio.to_thread(
                stdout_.channel.recv_exit_status
            )
            if which_rc != 0:
                return cls.make_result(
                    targets=targets_out, started_at=started, return_code=-1,
                    raw_output=b"", findings=[],
                    error="lynis_not_provisioned: cliente debe instalar lynis "
                          "en el target host (ej. 'apt install lynis').",
                    timed_out=False,
                )

            # Execute Lynis
            try:
                _, stdout_, stderr_ = await asyncio.wait_for(
                    asyncio.to_thread(client.exec_command, LYNIS_REMOTE_CMD),
                    timeout=timeout_seconds,
                )
                rc = await asyncio.wait_for(
                    asyncio.to_thread(stdout_.channel.recv_exit_status),
                    timeout=timeout_seconds,
                )
                raw_output = await asyncio.to_thread(stdout_.read)
            except asyncio.TimeoutError:
                return cls.make_result(
                    targets=targets_out, started_at=started, return_code=-1,
                    raw_output=b"", findings=[],
                    error=f"ssh_command_timeout: lynis remoto excedio "
                          f"{timeout_seconds}s", timed_out=True,
                )

            try:
                findings = cls.parse_output(raw_output, host=host_label)
                error = None
            except Exception as exc:  # pragma: no cover
                findings = []
                error = f"parse error: {exc}"

            return cls.make_result(
                targets=targets_out, started_at=started, return_code=rc,
                raw_output=raw_output, findings=findings, error=error,
                timed_out=False,
            )
        finally:
            try:
                client.close()
            except Exception:  # pragma: no cover
                pass

    @classmethod
    def parse_output(
        cls,
        raw: bytes,
        host: str = "local",
    ) -> list[FindingCandidate]:
        """Parsea report.dat de Lynis. Cada warning[]/suggestion[] es
        un finding."""
        if not raw:
            return []
        text = raw.decode("utf-8", errors="replace")
        warnings_raw: list[str] = []
        suggestions_raw: list[str] = []
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = _REPORT_LINE.match(line)
            if not m:
                continue
            key, value = m.group(1).lower(), m.group(2)
            if key == "warning":
                warnings_raw.append(value)
            elif key == "suggestion":
                suggestions_raw.append(value)

        findings: list[FindingCandidate] = []
        for w in warnings_raw:
            test_id, message = _split_lynis_entry(w)
            findings.append({
                "title": f"Lynis WARNING {test_id}",
                "description": message or "Lynis emitio warning",
                "severity": normalize_severity("high"),
                "cve_id": None,
                "cvss_score": None,
                "cvss_vector": None,
                "cwe_id": None,
                "affected_host": host,
                "affected_port": None,
                "affected_service": "system",
                "affected_service_version": None,
                "affected_url": None,
                "affected_os": "linux",
                "raw_output_excerpt": excerpt(w),
                "tool": "lynis",
                "tool_metadata": {"lynis_test_id": test_id, "kind": "warning"},
            })
        for s in suggestions_raw:
            test_id, message = _split_lynis_entry(s)
            findings.append({
                "title": f"Lynis SUGGESTION {test_id}",
                "description": message or "Lynis sugiere mejora de hardening",
                "severity": normalize_severity("medium"),
                "cve_id": None,
                "cvss_score": None,
                "cvss_vector": None,
                "cwe_id": None,
                "affected_host": host,
                "affected_port": None,
                "affected_service": "system",
                "affected_service_version": None,
                "affected_url": None,
                "affected_os": "linux",
                "raw_output_excerpt": excerpt(s),
                "tool": "lynis",
                "tool_metadata": {"lynis_test_id": test_id, "kind": "suggestion"},
            })
        return findings


def _split_lynis_entry(value: str) -> tuple[str, str]:
    """Lynis warning/suggestion: ``TEST-ID|message|severity|solution``."""
    parts = value.split("|", 3)
    test_id = parts[0] if parts else "UNKNOWN"
    message = parts[1] if len(parts) > 1 else ""
    return test_id, message
