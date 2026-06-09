"""M8 v5.1 — Zero False Positives engine (5 gates).

Pipeline para cada candidato (FindingCandidate) que viene de los
runners:

    raw → Gate 1 (dedup) → Gate 2 (FP filter) → Gate 3 (correlación)
        → Gate 4 (re-test si conf < 0.85) → Gate 5 (clasificación)
        → VerificationFinding (persistido) o rejected (descartado)

Cada gate es testeable en aislamiento (ver tests/test_zfp_engine.py).

Salida final:
- ``confidence_score`` (0.0-1.0)
- ``zfp_gate5_classification`` ∈ {confirmed, probable, needs_review, rejected}

Solo ``confirmed`` y ``probable`` van al informe E-702 cliente.
``needs_review`` espera revision Marcos. ``rejected`` queda solo en
log para audit trail.
"""
from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m08_verification.fp_patterns.learner import (
    find_matching_patterns,
    increment_match,
)
from backend.app.motors.m08_verification.tools.base import FindingCandidate


# ────────────────────────────────────────────────────────────────────
# Estructura intermedia ZFP
# ────────────────────────────────────────────────────────────────────

@dataclass
class ZfpFinding:
    """Estado de un finding mientras pasa por los 5 gates.

    Acumula tool_sources, raw_outputs, scores intermedios, etc. antes
    de persistir como VerificationFinding.
    """
    finding_hash: str
    title: str
    description: str
    severity: str
    affected_host: str
    affected_port: int | None
    affected_service: str | None
    affected_url: str | None
    cve_id: str | None = None
    cvss_score: float | None = None
    cvss_vector: str | None = None
    cwe_id: str | None = None
    affected_service_version: str | None = None
    affected_os: str | None = None

    # Acumuladores
    tool_sources: list[str] = field(default_factory=list)
    raw_outputs: list[dict[str, Any]] = field(default_factory=list)
    tool_metadata: list[dict[str, Any]] = field(default_factory=list)

    # ZFP gates state
    confidence_score: float = 0.50
    zfp_gate1_dedup: bool = False
    zfp_gate2_fp_filter: bool = False
    zfp_gate3_cross_tool: int = 0           # n tools que reportan
    zfp_gate4_retest: str = "not_tested"    # not_tested|confirmed|not_confirmed|not_applicable
    zfp_gate5_classification: str = "needs_review"

    # FP info (si gate 2 lo filtra)
    fp_pattern_id: uuid.UUID | None = None
    fp_reason: str | None = None

    # Bonuses (para audit)
    has_known_cve: bool = False
    has_public_exploit: bool = False
    version_in_affected_range: bool = False


# ────────────────────────────────────────────────────────────────────
# Gate 1 — Dedup
# ────────────────────────────────────────────────────────────────────

def compute_finding_hash(c: FindingCandidate) -> str:
    """Hash estable para dedup.

    SHA-256(host + ':' + port + '|' + type + '|' + cve)
    type = first(cve_id, cwe_id, title-normalizado)
    """
    host = (c.get("affected_host") or "unknown").strip().lower()
    port = c.get("affected_port") or 0
    cve = (c.get("cve_id") or "").strip().upper()
    cwe = (c.get("cwe_id") or "").strip().upper()
    title_normalized = "".join(
        ch.lower() for ch in (c.get("title") or "")
        if ch.isalnum() or ch in ("_", "-")
    )
    type_id = cve or cwe or title_normalized
    raw = f"{host}:{port}|{type_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def gate1_dedup(
    candidates: list[FindingCandidate],
) -> list[ZfpFinding]:
    """Agrupa candidates por finding_hash. Cada grupo se convierte en
    UN ZfpFinding con tool_sources mergeados."""
    by_hash: dict[str, ZfpFinding] = {}
    for cand in candidates:
        h = compute_finding_hash(cand)
        if h in by_hash:
            existing = by_hash[h]
            tool = cand.get("tool") or "unknown"
            if tool not in existing.tool_sources:
                existing.tool_sources.append(tool)
            existing.raw_outputs.append({
                "tool": tool,
                "excerpt": cand.get("raw_output_excerpt", "")[:500],
                "metadata": cand.get("tool_metadata") or {},
            })
            existing.tool_metadata.append(cand.get("tool_metadata") or {})
            # Promote severity al maximo
            existing.severity = _max_severity(
                existing.severity, cand.get("severity", "info"),
            )
            # Si falta CVE, completarlo desde otra fuente
            if not existing.cve_id and cand.get("cve_id"):
                existing.cve_id = cand["cve_id"]
                existing.has_known_cve = True
            existing.zfp_gate1_dedup = True
            continue

        zf = ZfpFinding(
            finding_hash=h,
            title=cand.get("title", "(sin titulo)"),
            description=cand.get("description", ""),
            severity=cand.get("severity", "info"),
            affected_host=cand.get("affected_host", "unknown"),
            affected_port=cand.get("affected_port"),
            affected_service=cand.get("affected_service"),
            affected_url=cand.get("affected_url"),
            cve_id=cand.get("cve_id"),
            cvss_score=cand.get("cvss_score"),
            cvss_vector=cand.get("cvss_vector"),
            cwe_id=cand.get("cwe_id"),
            affected_service_version=cand.get("affected_service_version"),
            affected_os=cand.get("affected_os"),
            has_known_cve=bool(cand.get("cve_id")),
        )
        zf.tool_sources.append(cand.get("tool") or "unknown")
        zf.raw_outputs.append({
            "tool": cand.get("tool") or "unknown",
            "excerpt": cand.get("raw_output_excerpt", "")[:500],
            "metadata": cand.get("tool_metadata") or {},
        })
        zf.tool_metadata.append(cand.get("tool_metadata") or {})
        by_hash[h] = zf

    # Marcar gate1 como aplicado para todos
    for zf in by_hash.values():
        zf.zfp_gate1_dedup = True
    return list(by_hash.values())


# ────────────────────────────────────────────────────────────────────
# Gate 2 — FP filter
# ────────────────────────────────────────────────────────────────────

async def gate2_fp_filter(
    db: AsyncSession,
    findings: list[ZfpFinding],
) -> tuple[list[ZfpFinding], list[ZfpFinding]]:
    """Devuelve (kept, rejected_as_fp).

    Para cada finding, busca patrones FP que matchean. Si hay match,
    incrementa times_matched + marca el finding como rejected.
    """
    kept: list[ZfpFinding] = []
    rejected: list[ZfpFinding] = []
    for f in findings:
        cand_view: FindingCandidate = {
            "tool": f.tool_sources[0] if f.tool_sources else None,
            "title": f.title,
            "description": f.description,
            "severity": f.severity,
            "affected_port": f.affected_port,
            "tool_metadata": (f.tool_metadata[0] if f.tool_metadata else {}),
        }
        matches = await find_matching_patterns(db, cand_view)
        if matches:
            # Match al primer patron — incrementar contador, marcar rejected
            await increment_match(db, matches[0].id)
            f.fp_pattern_id = matches[0].id
            f.fp_reason = matches[0].reason
            f.zfp_gate2_fp_filter = True
            f.zfp_gate5_classification = "rejected"
            f.confidence_score = 0.0
            rejected.append(f)
        else:
            f.zfp_gate2_fp_filter = True  # gate aplicado, no filtrado
            kept.append(f)
    return kept, rejected


# ────────────────────────────────────────────────────────────────────
# Gate 3 — Correlation (cross-tool)
# ────────────────────────────────────────────────────────────────────

def gate3_correlation(findings: list[ZfpFinding]) -> None:
    """Anota zfp_gate3_cross_tool y ajusta confidence segun spec §3.4."""
    for f in findings:
        n_sources = len(f.tool_sources)
        f.zfp_gate3_cross_tool = n_sources
        # Score base 0.50
        score = 0.50
        if n_sources >= 3:
            score += 0.40
        elif n_sources == 2:
            score += 0.30
        elif f.has_known_cve:
            score += 0.20
        # Bonus
        if f.has_public_exploit:
            score += 0.10
        if f.version_in_affected_range:
            score += 0.10
        f.confidence_score = round(min(score, 1.0), 2)


# ────────────────────────────────────────────────────────────────────
# Gate 4 — Re-test (solo si conf < 0.85)
# ────────────────────────────────────────────────────────────────────

async def gate4_retest(
    findings: list[ZfpFinding],
    *,
    retest_callback=None,
    enable_llm_capa3_retest: bool = False,
) -> None:
    """Si confidence < 0.85, ejecuta re-test especifico via callback.

    El callback es ``async (zfp_finding) -> 'confirmed'|'not_confirmed'|'not_applicable'``.

    Resolución de callback:
    - ``retest_callback`` explícito → usa ese callable.
    - ``retest_callback is None`` y ``enable_llm_capa3_retest=True`` →
      usa ``llm_classifier.retest_zfp_via_llm`` (Capa 3 LLM Haiku 4.5).
      Cierre SAN-B.MB-3.ter.3.
    - ``retest_callback is None`` y flag False → marca ``not_tested``
      (comportamiento legacy preservado para tests + callers existentes).
    """
    if retest_callback is None and enable_llm_capa3_retest:
        from backend.app.motors.m08_verification.llm_classifier import (
            retest_zfp_via_llm,
        )
        retest_callback = retest_zfp_via_llm

    for f in findings:
        if f.confidence_score >= 0.85:
            f.zfp_gate4_retest = "not_applicable"
            continue
        if retest_callback is None:
            f.zfp_gate4_retest = "not_tested"
            continue
        try:
            result = await retest_callback(f)
        except Exception:
            result = "not_tested"
        f.zfp_gate4_retest = result
        if result == "confirmed":
            f.confidence_score = round(min(f.confidence_score + 0.25, 1.0), 2)
        elif result == "not_confirmed":
            f.confidence_score = round(max(f.confidence_score - 0.30, 0.0), 2)


# ────────────────────────────────────────────────────────────────────
# Gate 5 — Classification
# ────────────────────────────────────────────────────────────────────

def gate5_classify(findings: list[ZfpFinding]) -> None:
    """Clasifica segun confidence_score:

        >= 0.90  → confirmed   (al informe)
        0.70-0.89 → probable   (al informe con nota)
        0.50-0.69 → needs_review (Marcos lo ve, no va al informe)
        < 0.50    → rejected   (queda en log)
    """
    for f in findings:
        if f.zfp_gate5_classification == "rejected":
            # Ya rechazado por gate 2; no tocar
            continue
        c = f.confidence_score
        if c >= 0.90:
            f.zfp_gate5_classification = "confirmed"
        elif c >= 0.70:
            f.zfp_gate5_classification = "probable"
        elif c >= 0.50:
            f.zfp_gate5_classification = "needs_review"
        else:
            f.zfp_gate5_classification = "rejected"


# ────────────────────────────────────────────────────────────────────
# Pipeline completo
# ────────────────────────────────────────────────────────────────────

async def run_zfp_pipeline(
    db: AsyncSession,
    candidates: list[FindingCandidate],
    *,
    retest_callback=None,
    enable_llm_capa3_retest: bool = False,
) -> tuple[list[ZfpFinding], list[ZfpFinding]]:
    """Pipeline completo: 5 gates en orden.

    Returns (final_findings_to_persist, rejected_findings).
    Los rejected solo se devuelven para el log de audit.

    ``enable_llm_capa3_retest=True`` activa LLM Haiku Capa 3 retest
    callback en gate4 cuando ``retest_callback`` no se provea explícito.
    """
    deduped = gate1_dedup(candidates)
    kept, rejected_fp = await gate2_fp_filter(db, deduped)
    gate3_correlation(kept)
    await gate4_retest(
        kept,
        retest_callback=retest_callback,
        enable_llm_capa3_retest=enable_llm_capa3_retest,
    )
    gate5_classify(kept)

    # Tras gate 5, los que clasificaron 'rejected' (por confidence)
    # se mueven al bucket rejected.
    final_kept = [f for f in kept if f.zfp_gate5_classification != "rejected"]
    final_rejected = rejected_fp + [
        f for f in kept if f.zfp_gate5_classification == "rejected"
    ]
    return final_kept, final_rejected


# ────────────────────────────────────────────────────────────────────
# Severity helpers
# ────────────────────────────────────────────────────────────────────

_SEVERITY_RANK = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def _max_severity(a: str, b: str) -> str:
    return a if _SEVERITY_RANK.get(a, 0) >= _SEVERITY_RANK.get(b, 0) else b
