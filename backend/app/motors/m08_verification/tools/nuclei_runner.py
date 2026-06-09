"""M8 v5.1 — Nuclei runner (ProjectDiscovery).

- Comando default: ``nuclei -u <target> -j -o <out>``
- Timeout: 45 minutos por defecto
- Parser: NDJSON (un finding por linea)
- Severity: viene en el JSON ('info', 'low', 'medium', 'high', 'critical')

Cada finding nuclei mapea a un FindingCandidate. El tool_metadata
incluye template_id, matcher_name, etc. para poder filtrar por FP
patterns en el ZFP gate 2.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .base import (
    BaseRunner,
    FindingCandidate,
    RunnerResult,
    excerpt,
    normalize_severity,
    run_subprocess,
)


class NucleiRunner(BaseRunner):
    TOOL = "nuclei"
    BINARY = "nuclei"
    DEFAULT_TIMEOUT_SECONDS = 45 * 60  # 45 min

    @classmethod
    async def run(
        cls,
        targets: list[str],
        *,
        timeout_seconds: int | None = None,
        templates: str | None = None,        # ruta o tag, ej: "cves/2024"
        severity: str | None = None,         # filtro: "critical,high"
        rate_limit: int = 150,
    ) -> RunnerResult:
        started = datetime.now(timezone.utc)

        # SAN-B.MB-7.bis · MCP wire-up · fallback subprocess transparente
        from backend.app.mcp_client import try_invoke_mcp_or_none
        mcp_resp = await try_invoke_mcp_or_none(
            server="vulnscan", tool="nuclei_scan",
            args={
                "target": targets[0] if targets else "",
                "severity": severity or "critical,high,medium",
                "rate_limit": rate_limit,
            },
            timeout_seconds=timeout_seconds or cls.DEFAULT_TIMEOUT_SECONDS,
        )
        if mcp_resp is not None:
            return cls.from_mcp_response(mcp_resp, targets, started)

        cls.ensure_available()
        cmd = [cls.BINARY, "-jsonl", "-silent", "-rate-limit", str(rate_limit)]
        for t in targets:
            cmd.extend(["-u", t])
        if templates:
            cmd.extend(["-t", templates])
        if severity:
            cmd.extend(["-severity", severity])
        rc, stdout, stderr, timed_out = await run_subprocess(
            cmd, timeout_seconds=(timeout_seconds or cls.DEFAULT_TIMEOUT_SECONDS),
        )
        try:
            findings = cls.parse_output(stdout)
            error = None
        except Exception as exc:  # pragma: no cover
            findings = []
            error = f"parse error: {exc}"
        return cls.make_result(
            targets=targets, started_at=started, return_code=rc,
            raw_output=stdout, findings=findings,
            error=error or (stderr.decode(errors="replace") if rc != 0 else None),
            timed_out=timed_out,
        )

    @classmethod
    def parse_output(cls, raw: bytes) -> list[FindingCandidate]:
        """Parsea NDJSON de nuclei. Tolera lineas malformadas."""
        if not raw:
            return []
        text = raw.decode("utf-8", errors="replace")
        findings: list[FindingCandidate] = []
        for line in text.splitlines():
            line = line.strip()
            if not line or not line.startswith("{"):
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            findings.append(_nuclei_entry_to_candidate(entry))
        return findings


def _nuclei_entry_to_candidate(entry: dict[str, Any]) -> FindingCandidate:
    info = entry.get("info", {}) or {}
    classification = info.get("classification", {}) or {}
    matched_at = entry.get("matched-at") or entry.get("host") or ""
    severity = normalize_severity(info.get("severity") or "")
    cve_list = classification.get("cve-id") or []
    cwe_list = classification.get("cwe-id") or []
    cve_id = cve_list[0] if isinstance(cve_list, list) and cve_list else None
    cwe_id = cwe_list[0] if isinstance(cwe_list, list) and cwe_list else None
    cvss = classification.get("cvss-score")
    try:
        cvss_score = float(cvss) if cvss is not None else None
    except (ValueError, TypeError):
        cvss_score = None

    # Extraer host:port:url
    host = entry.get("host") or ""
    port = None
    url = None
    if matched_at.startswith("http://") or matched_at.startswith("https://"):
        url = matched_at
        # parse host + port
        from urllib.parse import urlparse
        try:
            parsed = urlparse(matched_at)
            host = parsed.hostname or host
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
        except Exception:
            pass
    elif ":" in matched_at:
        h, _, p = matched_at.partition(":")
        host = h or host
        try:
            port = int(p.split("/")[0])
        except ValueError:
            port = None

    template_id = entry.get("template-id") or info.get("name") or "unknown"
    title = info.get("name") or template_id
    description = (
        info.get("description")
        or f"Nuclei detecto '{title}' en {matched_at}."
    )

    return {
        "title": title,
        "description": description,
        "severity": severity,
        "cve_id": cve_id,
        "cvss_score": cvss_score,
        "cvss_vector": classification.get("cvss-metrics"),
        "cwe_id": cwe_id,
        "affected_host": host or matched_at,
        "affected_port": port,
        "affected_service": None,
        "affected_service_version": None,
        "affected_url": url,
        "affected_os": None,
        "raw_output_excerpt": excerpt(json.dumps(entry)),
        "tool": "nuclei",
        "tool_metadata": {
            "template_id": template_id,
            "matcher_name": entry.get("matcher-name"),
            "tags": info.get("tags") or [],
            "reference": info.get("reference") or [],
        },
    }
