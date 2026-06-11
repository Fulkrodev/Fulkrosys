"""M8 v5.1 — Retest quirurgico tras 'Ya lo he arreglado' (spec §5.4).

Un retest NO vuelve a lanzar todo el pipeline v5.1. Ejecuta solo la
tool + parametros especificos del finding que se reporta como resuelto.
El resultado se persiste en ``remediation_retests``.

Tipos soportados (``retest_type``):
- ``ssl``       -> testssl sobre host:port
- ``cve``       -> nuclei -t cves/<CVE>.yaml -u host[:port]
- ``web``       -> zap scan puntual sobre url
- ``hardening`` -> lynis --tests <control_id>
- ``port``      -> nmap -p <port> host

Salida (``result``): fixed | still_present | error | inconclusive.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m08_verification.finding_state_machine import (
    STATE_EVENT_MAP, TERMINAL_STATES, FindingState, can_transition,
)
from backend.app.motors.m08_verification.models import (
    EvidenceRecord, RemediationRetest, VerificationFinding, VerificationRun,
)
from backend.app.motors.m08_verification.tools.base import RunnerNotInstalled


# Cadena canónica de avance de finding_state (doc §6 · state machine).
_FORWARD_CHAIN = (
    FindingState.DETECTED, FindingState.TRIAGED, FindingState.VERIFIED,
    FindingState.REPORTED, FindingState.IN_REMEDIATION, FindingState.RETESTED,
    FindingState.CLOSED,
)


def _advance_finding_state_to(finding: VerificationFinding, target: str) -> list[str]:
    """Avanza ``finding_state`` por la cadena canónica hasta ``target`` respetando
    VALID_TRANSITIONS. NO mueve estados terminales (closed/false_positive/
    risk_accepted). Devuelve los eventos canónicos de las transiciones aplicadas.
    """
    cur = finding.finding_state or FindingState.DETECTED
    if cur in TERMINAL_STATES:
        return []
    try:
        ci = _FORWARD_CHAIN.index(cur)
        ti = _FORWARD_CHAIN.index(target)
    except ValueError:
        return []
    if ti <= ci:
        return []
    events: list[str] = []
    for i in range(ci, ti):
        nxt = _FORWARD_CHAIN[i + 1]
        if not can_transition(_FORWARD_CHAIN[i], nxt):
            break
        ev = STATE_EVENT_MAP.get(nxt)
        if ev:
            events.append(ev)
    finding.finding_state = target
    return events


def _emit_retest_evidence(
    db: AsyncSession,
    finding: VerificationFinding,
    retest: RemediationRetest,
    run_manifest_hash: str | None,
    *,
    action: str,
    triggered_by: str,
    transitions: list[str] | None = None,
) -> None:
    """Evidencia R6 append-only de la verificación post-remediación · es lo que el
    auditor ENAC certifica como cierre del bucle (mp.s.2)."""
    db.add(EvidenceRecord(
        project_id=finding.project_id,
        client_id=None,
        run_id=finding.run_id,
        finding_id=finding.id,
        run_manifest_hash=run_manifest_hash,
        actor=triggered_by,
        action=action,
        component="m08:remediation.retest_runner",
        output_hash=finding.finding_hash,
        ens_relevance=finding.ens_primary_measure,
        payload={
            "result": retest.result,
            "retest_type": retest.retest_type,
            "retest_command": retest.retest_command,
            "retest_id": str(retest.id),
            "finding_state": finding.finding_state,
            "transitions": transitions or [],
        },
    ))


# ────────────────────────────────────────────────────────────────────
# Seleccion de retest
# ────────────────────────────────────────────────────────────────────

def choose_retest_type(finding: VerificationFinding | dict) -> str:
    """Elige el retest_type adecuado para un finding.

    Usa tool_sources primero (hint mas directo), luego title/fields.
    """
    def _get(obj, key, default=""):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    tool_sources = _get(finding, "tool_sources", []) or []
    if isinstance(tool_sources, list):
        tools = {(t or "").lower() for t in tool_sources}
    else:
        tools = {str(tool_sources).lower()}
    title = (_get(finding, "title", "") or "").lower()
    cve = _get(finding, "cve_id", None)
    url = _get(finding, "affected_url", None)

    if "testssl" in tools or "tls" in title or "ssl" in title:
        return "ssl"
    if cve or "nuclei" in tools:
        return "cve"
    if "zap" in tools or url:
        return "web"
    if "lynis" in tools or "hardening" in title or "config" in title:
        return "hardening"
    if "nmap" in tools or "port" in title:
        return "port"
    return "cve"  # fallback razonable


# ────────────────────────────────────────────────────────────────────
# Ejecutores por tipo
# ────────────────────────────────────────────────────────────────────

async def _retest_ssl(finding: VerificationFinding) -> tuple[str, str, str]:
    """testssl contra host:port. Si el finding_id concreto no aparece,
    se considera ``fixed``. Si sigue apareciendo, ``still_present``."""
    from backend.app.motors.m08_verification.tools.testssl_runner import TestsslRunner

    host = finding.affected_host
    port = finding.affected_port or 443
    target = f"{host}:{port}"
    cmd_str = f"testssl --jsonfile-pretty /dev/stdout --quiet --color 0 {target}"
    try:
        result = await TestsslRunner.run([target], timeout_seconds=300)
    except RunnerNotInstalled:
        return "error", cmd_str, "testssl no instalado"
    signature = _testssl_signature(finding)
    still = any(
        signature in (f.get("title", "") + "|" + f.get("description", "")).lower()
        for f in result.findings
    )
    detail = f"findings nuevos: {len(result.findings)}; signature='{signature}'"
    return ("still_present" if still else "fixed"), cmd_str, detail


def _testssl_signature(finding: VerificationFinding) -> str:
    """Signature para identificar si el mismo issue sigue reportandose."""
    meta = finding.raw_outputs or []
    if isinstance(meta, list) and meta:
        first = meta[0] or {}
        metadata = first.get("metadata") or {}
        sig = metadata.get("testssl_id") or ""
        if sig:
            return sig.lower()
    # Fallback: ultima palabra relevante del titulo
    t = (finding.title or "").lower()
    return t.split(":")[-1].strip()


async def _retest_cve(finding: VerificationFinding) -> tuple[str, str, str]:
    """nuclei -t cves/<CVE>.yaml -u host[:port]."""
    from backend.app.motors.m08_verification.tools.nuclei_runner import NucleiRunner

    host = finding.affected_host
    port = finding.affected_port
    target = finding.affected_url or (f"{host}:{port}" if port else host)
    cve = (finding.cve_id or "").upper()
    template = f"cves/{cve[:4]}/{cve}.yaml" if cve.startswith("CVE-") else None
    cmd_str = f"nuclei -jsonl -silent -u {target}" + (f" -t {template}" if template else "")
    try:
        result = await NucleiRunner.run(
            [target], timeout_seconds=300, templates=template,
        )
    except RunnerNotInstalled:
        return "error", cmd_str, "nuclei no instalado"
    hit = any(
        (cve and cve.lower() in (f.get("cve_id", "") or "").lower())
        or (finding.title.lower() in (f.get("title", "") or "").lower())
        for f in result.findings
    )
    detail = f"matches: {len(result.findings)}; CVE={cve or 'n/a'}"
    return ("still_present" if hit else "fixed"), cmd_str, detail


async def _retest_web(finding: VerificationFinding) -> tuple[str, str, str]:
    """ZAP scan puntual sobre la URL afectada.

    Ruta de invocacion (FASE 9.C):
    - USE_MCP_REAL=true: invoke_mcp(server="webpentest", tool="zap_spider_scan").
      Si la llamada MCP falla (MCPInvocationError) cae al runner subprocess.
    - USE_MCP_REAL=false (default): runner subprocess legacy (ZapRunner).
    """
    from backend.app.motors.m08_verification.tools.zap_runner import ZapRunner
    from backend.app.mcp_client import (
        MCPInvocation, MCPInvocationError, invoke_mcp, use_mcp_real,
    )

    url = finding.affected_url or f"https://{finding.affected_host}"

    # Path MCP real (Tier 2 9.C)
    if use_mcp_real():
        try:
            mcp_resp = await invoke_mcp(MCPInvocation(
                server="webpentest", tool="zap_spider_scan",
                args={"url": url}, timeout_seconds=600,
            ))
            if not mcp_resp.get("_fallback"):
                data = mcp_resp.get("data") or {}
                alerts = data.get("alerts", []) or []
                cmd_str = data.get("command") or f"mcp:webpentest:zap_spider_scan url={url}"
                still = any(
                    finding.title.lower().split(":")[0] in (a.get("title", "") or a.get("alert", "") or "").lower()
                    for a in alerts
                )
                detail = f"mcp_zap_alerts: {len(alerts)}"
                return ("still_present" if still else "fixed"), cmd_str, detail
        except MCPInvocationError:
            # Fallback transparente al subprocess runner.
            pass  # noqa: S110 — fallback intencional documentado

    # Path subprocess legacy (default)
    cmd_str = f"zap-cli quick-scan --self-contained {url}"
    try:
        result = await ZapRunner.run([url], timeout_seconds=600)
    except RunnerNotInstalled:
        return "error", cmd_str, "zap no disponible"
    still = any(
        finding.title.lower().split(":")[0] in (f.get("title", "") or "").lower()
        for f in result.findings
    )
    detail = f"zap_alerts: {len(result.findings)}"
    return ("still_present" if still else "fixed"), cmd_str, detail


async def _retest_hardening(finding: VerificationFinding) -> tuple[str, str, str]:
    """Lynis re-corre solo el control afectado."""
    from backend.app.motors.m08_verification.tools.lynis_runner import LynisRunner

    meta = finding.raw_outputs or []
    control_id = ""
    if isinstance(meta, list) and meta:
        md = (meta[0] or {}).get("metadata") or {}
        control_id = md.get("control_id") or md.get("test_id") or ""
    cmd_str = f"lynis audit system --tests {control_id}" if control_id else "lynis audit system --quick"
    try:
        result = await LynisRunner.run(
            [finding.affected_host or "localhost"],
            timeout_seconds=300,
            test_ids=[control_id] if control_id else None,
        )
    except RunnerNotInstalled:
        return "error", cmd_str, "lynis no instalado"
    except TypeError:
        # LynisRunner.run may not accept test_ids kwarg in older versions
        result = await LynisRunner.run(
            [finding.affected_host or "localhost"], timeout_seconds=300,
        )
    hit = any(
        (control_id and control_id in (f.get("title", "") + f.get("description", "")))
        or finding.title.lower() in (f.get("title", "") or "").lower()
        for f in result.findings
    )
    detail = f"controls_failed: {len(result.findings)}; control={control_id or 'n/a'}"
    return ("still_present" if hit else "fixed"), cmd_str, detail


async def _retest_port(finding: VerificationFinding) -> tuple[str, str, str]:
    """nmap puntual al puerto reportado.

    Ruta de invocacion (FASE 9.C):
    - USE_MCP_REAL=true: invoke_mcp(server="recon", tool="nmap_scan").
      Si la llamada MCP falla cae al runner subprocess.
    - USE_MCP_REAL=false (default): runner subprocess legacy (NmapRunner).
    """
    from backend.app.motors.m08_verification.tools.nmap_runner import NmapRunner
    from backend.app.mcp_client import (
        MCPInvocation, MCPInvocationError, invoke_mcp, use_mcp_real,
    )

    host = finding.affected_host
    port = finding.affected_port

    # Path MCP real (Tier 2 9.C)
    if use_mcp_real():
        try:
            mcp_args = {"target": host, "mode": "quick"}
            if port:
                mcp_args["ports"] = str(port)
            mcp_resp = await invoke_mcp(MCPInvocation(
                server="recon", tool="nmap_scan",
                args=mcp_args, timeout_seconds=300,
            ))
            if not mcp_resp.get("_fallback"):
                data = mcp_resp.get("data") or {}
                hosts = data.get("hosts", []) or []
                cmd_str = data.get("command") or f"mcp:recon:nmap_scan target={host}"
                still = False
                for h in hosts:
                    for p in h.get("ports", []) or []:
                        if (port is None or str(p.get("port")) == str(port)) and p.get("state") == "open":
                            still = True
                            break
                    if still:
                        break
                summary = data.get("summary") or {}
                open_ports = summary.get("open_ports", 0)
                detail = f"mcp_open_ports: {open_ports}; port={port}"
                return ("still_present" if still else "fixed"), cmd_str, detail
        except MCPInvocationError:
            pass  # fallback subprocess

    # Path subprocess legacy (default)
    cmd_str = f"nmap -Pn -p {port} {host}" if port else f"nmap -Pn {host}"
    try:
        result = await NmapRunner.run(
            [host], timeout_seconds=120,
            ports=[port] if port else None,
        )
    except RunnerNotInstalled:
        return "error", cmd_str, "nmap no instalado"
    except TypeError:
        result = await NmapRunner.run([host], timeout_seconds=120)
    still = any(
        (port is None or (f.get("affected_port") == port))
        and (f.get("severity") in ("medium", "high", "critical"))
        for f in result.findings
    )
    detail = f"open_ports_reported: {len(result.findings)}; port={port}"
    return ("still_present" if still else "fixed"), cmd_str, detail


_DISPATCHERS = {
    "ssl": _retest_ssl,
    "cve": _retest_cve,
    "web": _retest_web,
    "hardening": _retest_hardening,
    "port": _retest_port,
}


# ────────────────────────────────────────────────────────────────────
# API publica
# ────────────────────────────────────────────────────────────────────

async def run_retest(
    db: AsyncSession,
    finding: VerificationFinding,
    *,
    triggered_by: str = "marcos",
    retest_type: str | None = None,
) -> RemediationRetest:
    """Ejecuta el retest y persiste el resultado.

    - Escoge el tipo si no se indica explicitamente.
    - Invoca el dispatcher.
    - Crea un ``RemediationRetest`` con el resultado.
    - Si ``result == 'fixed'``, marca el finding como remediado/verificado.
    """
    rtype = retest_type or choose_retest_type(finding)
    dispatcher = _DISPATCHERS.get(rtype, _retest_cve)

    try:
        result, cmd_str, detail = await dispatcher(finding)
    except Exception as exc:  # pragma: no cover — red path
        result, cmd_str, detail = "error", "(dispatcher error)", str(exc)

    retest = RemediationRetest(
        id=uuid.uuid4(),
        finding_id=finding.id,
        triggered_by=triggered_by,
        retest_type=rtype,
        retest_command=cmd_str,
        result=result,
        result_detail=detail,
        executed_at=datetime.now(timezone.utc),
    )
    db.add(retest)

    # Manifest del run (para enlazar la evidencia · nullable si aún no existe).
    run_mh = None
    try:
        run_mh = (await db.execute(
            select(VerificationRun.run_manifest_hash).where(
                VerificationRun.id == finding.run_id,
            )
        )).scalar()
    except Exception:  # pragma: no cover — run sin manifest
        run_mh = None

    if result == "fixed":
        finding.status = "remediated"
        finding.remediated_at = datetime.now(timezone.utc)
        finding.remediated_verified = True
        finding.remediated_retest_run_id = retest.id
        # Pista canónica (doc §6): el re-test determinista es el "desmentido
        # activo" que cierra el bucle hasta CLOSED. + evidencia R6 inmutable.
        transitions = _advance_finding_state_to(finding, FindingState.CLOSED)
        _emit_retest_evidence(
            db, finding, retest, run_mh, action="finding.remediation_verified",
            triggered_by=triggered_by, transitions=transitions,
        )
    elif result == "still_present":
        # Sigue presente: confirmado en remediación (NO cerrado).
        transitions = _advance_finding_state_to(finding, FindingState.IN_REMEDIATION)
        _emit_retest_evidence(
            db, finding, retest, run_mh, action="finding.retest_still_present",
            triggered_by=triggered_by, transitions=transitions,
        )
    else:  # error | inconclusive → queda traza, sin cambio de estado
        _emit_retest_evidence(
            db, finding, retest, run_mh, action="finding.retest_inconclusive",
            triggered_by=triggered_by,
        )

    await db.flush()
    return retest


async def list_retests(
    db: AsyncSession, finding_id: uuid.UUID,
) -> list[RemediationRetest]:
    from sqlalchemy import select
    stmt = (
        select(RemediationRetest)
        .where(
            RemediationRetest.finding_id == finding_id,
            RemediationRetest.deleted_at.is_(None),
        )
        .order_by(RemediationRetest.executed_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
