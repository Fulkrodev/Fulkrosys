"""Adaptadores MCP → FindingCandidate (doc §3 · normalización cross-motor).

La capa MCP (`mcp_client.invoke_mcp` + `shared.output_normalizer.normalize_finding`)
devuelve findings con shape: {tool, title, severity, description, cve (list),
cvss, host, port, protocol, evidence, raw_output_hash, command_executed,
remediation, timestamp, raw_data}.

El backbone M8 (ZFP, SARIF, enrichment, persistencia) trabaja sobre
`FindingCandidate` (tools/base.py): {title, severity, affected_host, cve_id,
cvss_score, affected_port, tool, tool_metadata, ...}.

Estos adaptadores traducen entre ambos, preservando la trazabilidad del
motor (source_engine + engine_version desde meta) — clave del determinismo
y de la evidencia auditable. Puro y determinista.
"""
from __future__ import annotations

from typing import Any


def _first_cve(cve: Any) -> str | None:
    if isinstance(cve, str):
        return cve or None
    if isinstance(cve, (list, tuple)) and cve:
        return str(cve[0]) or None
    return None


def mcp_finding_to_candidate(
    raw: dict[str, Any],
    *,
    server: str,
    tool: str,
    target: str | None = None,
    engine_version: str | None = None,
) -> dict[str, Any]:
    """Un finding normalizado MCP → FindingCandidate canónico.

    `server`/`tool` identifican el motor; se persisten en source_engine
    (`{server}:{tool}`) y tool para trazabilidad determinista (doc §4).
    """
    source_engine = f"{server}:{tool}"
    host = raw.get("host") or raw.get("affected_host") or target or "unknown"
    return {
        "title": raw.get("title") or "(sin título)",
        "description": raw.get("description") or raw.get("evidence") or "",
        "severity": str(raw.get("severity") or "info").lower(),
        "cve_id": _first_cve(raw.get("cve") or raw.get("cve_id")),
        "cvss_score": raw.get("cvss") if isinstance(raw.get("cvss"), (int, float)) else raw.get("cvss_score"),
        "cvss_vector": raw.get("cvss_vector"),
        "cwe_id": raw.get("cwe") or raw.get("cwe_id"),
        "affected_host": str(host),
        "affected_port": raw.get("port") or raw.get("affected_port"),
        "affected_service": raw.get("service") or raw.get("affected_service"),
        "affected_service_version": raw.get("affected_service_version") or raw.get("version"),
        "affected_url": raw.get("url") or raw.get("affected_url"),
        "affected_os": raw.get("os") or raw.get("affected_os"),
        "raw_output_excerpt": str(raw.get("evidence") or raw.get("raw_output_excerpt") or "")[:500],
        "tool": source_engine,
        "source_engine": source_engine,
        "engine_version": engine_version,
        "rule_id": raw.get("rule_id") or raw.get("template_id") or raw.get("check_id"),
        "remediation_summary": raw.get("remediation") or "",
        "tool_metadata": {
            "server": server,
            "tool": tool,
            "raw_output_hash": raw.get("raw_output_hash"),
            "command_executed": raw.get("command_executed") or raw.get("command"),
            "ens_measures": raw.get("ens_measures") or [],
            "cve_refs": raw.get("cve") if isinstance(raw.get("cve"), list) else (
                [raw["cve_id"]] if raw.get("cve_id") else []
            ),
        },
    }


def mcp_result_to_candidates(
    mcp_response: dict[str, Any] | None,
    *,
    server: str,
    tool: str,
    target: str | None = None,
) -> list[dict[str, Any]]:
    """Respuesta completa de `invoke_mcp`/`try_invoke_mcp_or_none` → candidates.

    Acepta el dict {_fallback, server, tool, data: {findings: [...]}, meta}.
    Si es None (USE_MCP_REAL=false) o _fallback=True → devuelve [] (el caller
    decide degradar; fail-closed: ausencia de datos ≠ ausencia de hallazgos,
    el run se marca parcial).
    """
    if not mcp_response or mcp_response.get("_fallback"):
        return []
    data = mcp_response.get("data") or {}
    meta = mcp_response.get("meta") or {}
    engine_version = meta.get("version") or meta.get("engine_version")
    findings = data.get("findings")
    if findings is None and isinstance(data, list):
        findings = data
    findings = findings or []
    return [
        mcp_finding_to_candidate(
            f, server=server, tool=tool, target=target,
            engine_version=engine_version,
        )
        for f in findings
        if isinstance(f, dict)
    ]
