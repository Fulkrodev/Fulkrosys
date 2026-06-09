"""M8 v5.1 — testssl.sh runner.

- Comando default: ``testssl.sh --jsonfile <out> --quiet --color 0 <host:port>``
- Timeout: 15 minutos por host
- Parser: JSON con array de findings (cada uno tiene severity)
- Filtra los findings con severity OK/INFO/DEBUG (no son hallazgos)

testssl emite categorias como: OK, INFO, LOW, MEDIUM, HIGH, CRITICAL.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone

from .base import (
    BaseRunner,
    FindingCandidate,
    RunnerNotInstalled,
    RunnerResult,
    excerpt,
    normalize_severity,
    run_subprocess,
)


# Severities testssl que SI se reportan como findings (descarta OK/DEBUG)
SEVERITY_INCLUDE = {"LOW", "MEDIUM", "HIGH", "CRITICAL", "INFO", "WARN"}


class TestsslRunner(BaseRunner):
    TOOL = "testssl"
    BINARY = "testssl"
    BINARY_CANDIDATES = ("testssl", "testssl.sh")
    DEFAULT_TIMEOUT_SECONDS = 15 * 60  # 15 min

    @classmethod
    def _resolve_binary(cls) -> str | None:
        """Devuelve el primer binario disponible en PATH entre los candidatos."""
        for candidate in cls.BINARY_CANDIDATES:
            if shutil.which(candidate):
                return candidate
        return None

    @classmethod
    def is_available(cls) -> bool:
        return cls._resolve_binary() is not None

    @classmethod
    def ensure_available(cls) -> None:
        if not cls.is_available():
            raise RunnerNotInstalled(
                f"{cls.TOOL}: ninguno de {list(cls.BINARY_CANDIDATES)} "
                f"esta en PATH. Instale el paquete testssl.sh o use el "
                f"container fulkro-scanner."
            )

    @classmethod
    async def run(
        cls,
        targets: list[str],
        *,
        timeout_seconds: int | None = None,
    ) -> RunnerResult:
        started = datetime.now(timezone.utc)

        # SAN-B.MB-7.bis · MCP wire-up · fallback subprocess transparente
        from backend.app.mcp_client import try_invoke_mcp_or_none
        mcp_resp = await try_invoke_mcp_or_none(
            server="webpentest", tool="testssl_scan",
            args={"target": targets[0] if targets else ""},
            timeout_seconds=timeout_seconds or cls.DEFAULT_TIMEOUT_SECONDS,
        )
        if mcp_resp is not None:
            return cls.from_mcp_response(mcp_resp, targets, started)

        cls.ensure_available()
        binary = cls._resolve_binary() or cls.BINARY
        all_findings: list[FindingCandidate] = []
        all_raw: list[bytes] = []
        rcs: list[int] = []
        timed_out_global = False
        for host in targets:
            cmd = [
                binary, "--jsonfile-pretty", "/dev/stdout",
                "--quiet", "--color", "0", host,
            ]
            rc, stdout, stderr, t_o = await run_subprocess(
                cmd,
                timeout_seconds=(timeout_seconds or cls.DEFAULT_TIMEOUT_SECONDS),
            )
            rcs.append(rc)
            all_raw.append(stdout)
            try:
                all_findings.extend(cls.parse_output(stdout, default_host=host))
            except Exception:  # pragma: no cover
                pass
            if t_o:
                timed_out_global = True
        return cls.make_result(
            targets=targets, started_at=started,
            return_code=max(rcs) if rcs else 0,
            raw_output=b"\n".join(all_raw),
            findings=all_findings,
            timed_out=timed_out_global,
        )

    @classmethod
    def parse_output(
        cls,
        raw: bytes,
        default_host: str = "unknown",
    ) -> list[FindingCandidate]:
        if not raw:
            return []
        text = raw.decode("utf-8", errors="replace").strip()
        if not text:
            return []
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # testssl puede emitir multiples objetos JSON
            data = []
            for chunk in text.split("\n}\n"):
                chunk = chunk.strip()
                if not chunk:
                    continue
                if not chunk.endswith("}"):
                    chunk += "}"
                try:
                    data.append(json.loads(chunk))
                except json.JSONDecodeError:
                    continue
        # Algunos formatos devuelven dict con 'scanResult' lista
        if isinstance(data, dict):
            scan_results = data.get("scanResult", [])
            if isinstance(scan_results, list) and scan_results:
                entries = []
                for sr in scan_results:
                    target = sr.get("targetHost") or default_host
                    target_port = sr.get("targetPort") or 443
                    for category in (
                        "protocols", "cipherTests", "serverDefaults",
                        "vulnerabilities", "cipherOrder", "fs",
                        "rating", "headerResponse", "ciphers",
                    ):
                        section = sr.get(category) or []
                        if isinstance(section, list):
                            for it in section:
                                entries.append({**it, "_host": target, "_port": target_port})
                data = entries
            else:
                data = [data]

        findings: list[FindingCandidate] = []
        for entry in data:
            if not isinstance(entry, dict):
                continue
            sev_raw = (entry.get("severity") or "").upper()
            if sev_raw not in SEVERITY_INCLUDE:
                continue
            host = entry.get("_host") or entry.get("host") or default_host
            port = entry.get("_port") or entry.get("port")
            try:
                port = int(port) if port else 443
            except (ValueError, TypeError):
                port = 443
            finding_id = entry.get("id") or entry.get("name") or "ssl_finding"
            cve_field = entry.get("cve") or ""
            cve_id = cve_field.split()[0] if cve_field and cve_field.startswith("CVE-") else None
            findings.append({
                "title": f"TLS/SSL: {finding_id}",
                "description": (
                    entry.get("finding") or entry.get("info")
                    or f"testssl reporto {finding_id} sobre {host}:{port}"
                ),
                "severity": normalize_severity(sev_raw.lower()),
                "cve_id": cve_id,
                "cvss_score": None,
                "cvss_vector": None,
                "cwe_id": entry.get("cwe"),
                "affected_host": host,
                "affected_port": port,
                "affected_service": "tls",
                "affected_service_version": None,
                "affected_url": None,
                "affected_os": None,
                "raw_output_excerpt": excerpt(json.dumps(entry)),
                "tool": "testssl",
                "tool_metadata": {
                    "testssl_id": finding_id,
                    "exploit": entry.get("exploit"),
                },
            })
        return findings
