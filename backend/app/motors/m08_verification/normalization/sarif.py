"""SARIF 2.1.0 — esquema común cross-motor (doc §3 Capa 3).

Todos los hallazgos de cualquier motor se normalizan a SARIF (Static
Analysis Results Interchange Format, OASIS 2.1.0) para tener un esquema
único, dedup-able y exportable a auditoría. Funciones puras y
deterministas (testables sin BD ni red).

`FindingCandidate` (shape tools/base.py) ↔ SARIF Result:

    severity → SARIF level:  critical/high → "error" · medium → "warning"
                             low/info → "note"
    cvss_score → properties["security-severity"] (string numérica, 0-10)
    cve_id/cwe_id → result.taxa / properties
    affected_host:affected_port → physicalLocation.artifactLocation.uri
    source_engine → run.tool.driver.name

Ref SARIF: https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html
"""
from __future__ import annotations

from typing import Any

SARIF_VERSION = "2.1.0"
SARIF_SCHEMA = (
    "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/"
    "Schemata/sarif-schema-2.1.0.json"
)

# severity canónica → SARIF level
_SEVERITY_TO_LEVEL = {
    "critical": "error",
    "high": "error",
    "medium": "warning",
    "low": "note",
    "info": "note",
}
# SARIF level → severity canónica (inversa · best-effort)
_LEVEL_TO_SEVERITY = {
    "error": "high",
    "warning": "medium",
    "note": "low",
    "none": "info",
}


def _get(f: Any, *keys: str, default=None):
    """Lee la primera key presente de un dict o atributo de objeto."""
    for k in keys:
        if isinstance(f, dict):
            if k in f and f[k] is not None:
                return f[k]
        elif getattr(f, k, None) is not None:
            return getattr(f, k)
    return default


def _artifact_uri(host: str | None, port: int | None, url: str | None) -> str:
    if url:
        return str(url)
    if host and port:
        return f"tcp://{host}:{port}"
    if host:
        return str(host)
    return "unknown://target"


def findings_to_sarif(
    findings: list[Any],
    *,
    tool_name: str = "fulkro-m8-autopilot",
    tool_version: str = "2.0",
    run_id: str | None = None,
) -> dict[str, Any]:
    """Convierte una lista de FindingCandidate/dict a un SARIF Log 2.1.0.

    Determinista: misma entrada → mismo SARIF (orden preservado, sin
    timestamps ni randoms). Agrupa por motor en un único `run` con
    `tool.driver.rules` deduplicadas por rule_id.
    """
    rules: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []

    for f in findings:
        severity = str(_get(f, "severity", default="info")).lower()
        level = _SEVERITY_TO_LEVEL.get(severity, "note")
        title = _get(f, "title", default="(sin título)")
        description = _get(f, "description", default="") or ""
        cve = _get(f, "cve_id", "cve")
        cwe = _get(f, "cwe_id", "cwe")
        cvss = _get(f, "cvss_score", "cvss")
        epss = _get(f, "epss_score", "epss")
        host = _get(f, "affected_host", "host")
        port = _get(f, "affected_port", "port")
        url = _get(f, "affected_url", "url")
        rule_id = (
            _get(f, "rule_id")
            or (str(cve).upper() if cve else None)
            or (str(cwe).upper() if cwe else None)
            or title
        )
        rule_id = str(rule_id)
        source_engine = _get(f, "source_engine", "tool", default=tool_name)

        if rule_id not in rules:
            rules[rule_id] = {
                "id": rule_id,
                "name": title,
                "shortDescription": {"text": title},
                "properties": {
                    k: v for k, v in (("cve", cve), ("cwe", cwe)) if v
                },
            }

        props: dict[str, Any] = {"engine": source_engine}
        if cvss is not None:
            # SARIF security-severity es string numérica 0.0-10.0
            props["security-severity"] = str(cvss)
        if epss is not None:
            props["epss"] = float(epss)
        if cve:
            props["cve"] = cve
        if cwe:
            props["cwe"] = cwe
        if _get(f, "verification_level"):
            props["verification-level"] = _get(f, "verification_level")

        results.append({
            "ruleId": rule_id,
            "level": level,
            "message": {"text": f"{title}. {description}".strip()},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": _artifact_uri(host, port, url)},
                },
            }],
            "properties": props,
        })

    driver: dict[str, Any] = {
        "name": tool_name,
        "version": tool_version,
        "informationUri": "https://fulkro.es",
        "rules": list(rules.values()),
    }
    run: dict[str, Any] = {"tool": {"driver": driver}, "results": results}
    if run_id:
        run["properties"] = {"runId": run_id}

    return {
        "$schema": SARIF_SCHEMA,
        "version": SARIF_VERSION,
        "runs": [run],
    }


def sarif_to_findings(sarif: dict[str, Any]) -> list[dict[str, Any]]:
    """Convierte un SARIF Log 2.1.0 a lista de FindingCandidate (dicts).

    Inversa best-effort de `findings_to_sarif`. Robusto a SARIF de
    herramientas externas (semgrep, trivy, nuclei -sarif, etc.).
    """
    out: list[dict[str, Any]] = []
    for run in sarif.get("runs", []) or []:
        driver = (run.get("tool", {}) or {}).get("driver", {}) or {}
        engine = driver.get("name", "unknown")
        # index rules by id para enriquecer
        rule_index = {
            r.get("id"): r for r in (driver.get("rules", []) or []) if r.get("id")
        }
        for res in run.get("results", []) or []:
            rule_id = res.get("ruleId")
            rule = rule_index.get(rule_id, {})
            props = res.get("properties", {}) or {}
            level = (res.get("level") or "warning").lower()
            sev = _LEVEL_TO_SEVERITY.get(level, "info")
            # security-severity numérica eleva la severity si presente
            sec_sev = props.get("security-severity")
            cvss = None
            if sec_sev is not None:
                try:
                    cvss = float(sec_sev)
                    if cvss >= 9.0:
                        sev = "critical"
                    elif cvss >= 7.0:
                        sev = "high"
                    elif cvss >= 4.0:
                        sev = "medium"
                    elif cvss > 0:
                        sev = "low"
                except (TypeError, ValueError):
                    cvss = None
            msg = (res.get("message", {}) or {}).get("text", "") or ""
            locs = res.get("locations", []) or []
            uri = None
            if locs:
                uri = (
                    (locs[0].get("physicalLocation", {}) or {})
                    .get("artifactLocation", {}) or {}
                ).get("uri")
            host, port = _parse_uri(uri)
            out.append({
                "title": (rule.get("name") or rule_id or msg[:80] or "(sin título)"),
                "description": msg,
                "severity": sev,
                "cve_id": props.get("cve") or rule.get("properties", {}).get("cve"),
                "cwe_id": props.get("cwe") or rule.get("properties", {}).get("cwe"),
                "cvss_score": cvss,
                "epss_score": props.get("epss"),
                "affected_host": host or "unknown",
                "affected_port": port,
                "affected_url": uri if uri and "://" in uri and not uri.startswith("tcp://") else None,
                "rule_id": rule_id,
                "source_engine": props.get("engine") or engine,
                "tool": props.get("engine") or engine,
                "verification_level": props.get("verification-level"),
                "raw_output_excerpt": msg[:500],
            })
    return out


def _parse_uri(uri: str | None) -> tuple[str | None, int | None]:
    """Extrae (host, port) de un artifactLocation.uri."""
    if not uri:
        return None, None
    s = uri
    if "://" in s:
        s = s.split("://", 1)[1]
    # quitar path
    s = s.split("/", 1)[0]
    if ":" in s:
        host, _, port_s = s.rpartition(":")
        try:
            return host or None, int(port_s)
        except ValueError:
            return s, None
    return s or None, None
