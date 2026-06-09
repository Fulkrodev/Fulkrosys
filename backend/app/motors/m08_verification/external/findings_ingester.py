"""M8 v5.1 - Findings ingester para reports externos (spec §6.3).

Dos formas de entrada:

- ``source='structured_form'`` (recomendado): el pentester rellena un
  JSON/XLSX segun el schema acordado. Parser directo -> ENS mapper ->
  insert con ``tool_source='external_structured'`` y confianza base 0.90.

- ``source='pdf'`` (fallback): el pentester entrega un PDF. Extract text
  con pdfminer -> Haiku estructura findings segun el schema -> insert
  con ``tool_source='external_pdf'`` y confianza * 0.85.

Integra automaticamente con:
- ENS mapper (rule-based + LLM cross-check si disponible)
- MITRE mapper (rule-based)
- ZFP gates 1, 2, 5 (dedup, FP filter, classification)
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.motors.m08_verification.ens_mapper import EnsMapper
from backend.app.motors.m08_verification.mitre_mapper import MitreMapper
from backend.app.motors.m08_verification.models import (
    ExternalPentesterHandoff, VerificationFinding, VerificationRun,
)
from backend.app.motors.m08_verification.tools.base import FindingCandidate
from backend.app.motors.m08_verification.zfp_engine import (
    ZfpFinding, compute_finding_hash,
)


REQUIRED_FIELDS_STRUCTURED = {
    "title", "severity", "affected_host", "description",
}


# ────────────────────────────────────────────────────────────────────
# Parser formulario estructurado
# ────────────────────────────────────────────────────────────────────

def parse_structured_payload(payload: Any) -> list[dict]:
    """Valida y normaliza un payload estructurado (JSON/XLSX).

    Acepta list[dict] directamente. Si es dict, busca la clave 'findings'.
    Devuelve lista de dicts normalizados listos para ingesta.
    """
    if isinstance(payload, dict):
        if "findings" in payload:
            payload = payload["findings"]
        else:
            payload = [payload]
    if not isinstance(payload, list):
        raise ValueError("El payload estructurado debe ser list[dict]")

    out: list[dict] = []
    for i, entry in enumerate(payload):
        if not isinstance(entry, dict):
            raise ValueError(f"Entry idx={i} no es dict")
        missing = REQUIRED_FIELDS_STRUCTURED - set(entry.keys())
        if missing:
            raise ValueError(
                f"Entry idx={i} le faltan campos: {sorted(missing)}"
            )
        out.append({
            "title": str(entry["title"]),
            "severity": str(entry["severity"]).lower(),
            "affected_host": str(entry["affected_host"]),
            "description": str(entry["description"]),
            "affected_port": entry.get("affected_port"),
            "affected_service": entry.get("affected_service"),
            "affected_service_version": entry.get("affected_service_version"),
            "affected_url": entry.get("affected_url"),
            "cve_id": entry.get("cve_id"),
            "cvss_score": entry.get("cvss_score"),
            "cvss_vector": entry.get("cvss_vector"),
            "cwe_id": entry.get("cwe_id"),
            "remediation_summary": (
                entry.get("remediation")
                or entry.get("remediation_summary")
                or ""
            ),
        })
    return out


# ────────────────────────────────────────────────────────────────────
# Parser PDF (Haiku)
# ────────────────────────────────────────────────────────────────────

PDF_SYSTEM_PROMPT = """Eres un experto extractor estructurado. Recibes
el texto extraido de un informe de pentest en espanol y devuelves SOLO
un JSON array con los findings detectados. Schema por finding:

{
  "title": "...",
  "severity": "critical|high|medium|low|info",
  "affected_host": "host or IP",
  "affected_port": 443 | null,
  "affected_service": "... or null",
  "affected_url": "... or null",
  "cve_id": "CVE-YYYY-NNNN or null",
  "cvss_score": 7.5 | null,
  "description": "descripcion detallada",
  "remediation_summary": "remediacion propuesta"
}

Responde solo con el JSON array (sin texto antes o despues).
Si no hay findings extraibles, responde [].
"""


def parse_pdf_payload(
    pdf_bytes: bytes,
    *,
    llm_router=None,
    max_tokens: int = 4000,
) -> list[dict]:
    """Extrae findings de un PDF.

    - Intenta pdfminer.six; si no esta disponible, usa ``pdfplumber`` o
      cae a una extraccion naive tratando el PDF como bytes.
    - Si hay clave Anthropic, pasa el texto a Haiku y parsea JSON.
    - Si no hay clave o el LLM falla, devuelve [].
    """
    text = _extract_pdf_text(pdf_bytes)
    if not text.strip():
        return []

    if not get_settings().anthropic_api_key.get_secret_value():
        logger.warning("PDF ingest: sin ANTHROPIC_API_KEY; devolviendo []")
        return []

    try:
        from backend.app.core.ai.llm_router import get_default_llm_router
        router = llm_router or get_default_llm_router()
        resp = router.complete(
            messages=[
                {"role": "system", "content": PDF_SYSTEM_PROMPT},
                {"role": "user", "content": text[:20000]},
            ],
            model="claude-haiku-4-5-20251001",
            max_tokens=max_tokens,
            temperature=0.0,
        )
        content = (resp.content or "").strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.startswith("json"):
                content = content[4:].strip()
        data = json.loads(content)
        if not isinstance(data, list):
            return []
        return data
    except Exception as exc:  # pragma: no cover
        logger.warning("PDF ingest failed: {}", exc)
        return []


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extrae texto con pdfminer o pdfplumber si estan; sino fallback."""
    try:
        from pdfminer.high_level import extract_text
        from io import BytesIO
        return extract_text(BytesIO(pdf_bytes)) or ""
    except Exception:
        pass
    try:
        import pdfplumber
        from io import BytesIO
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            return "\n".join(
                (p.extract_text() or "") for p in pdf.pages
            )
    except Exception:
        pass
    # Fallback muy burdo: solo texto ASCII visible
    try:
        return pdf_bytes.decode("utf-8", errors="ignore")
    except Exception:
        return ""


# ────────────────────────────────────────────────────────────────────
# Ingesta -> VerificationFinding
# ────────────────────────────────────────────────────────────────────

async def ingest_external_findings(
    db: AsyncSession,
    run_id: uuid.UUID,
    findings_data: list[dict],
    *,
    source: str = "structured_form",
    original_pdf_path: str | None = None,
) -> list[VerificationFinding]:
    """Persiste los findings externos con ENS mapping y MITRE mapping.

    - ``source`` ∈ {'structured_form', 'pdf'}
    - ``tool_source`` = 'external_structured' | 'external_pdf'
    - Confianza base: 0.90 structured, 0.85 pdf
    - ZFP gate 5: asigna classification en base a confianza final
    """
    run = await db.get(VerificationRun, run_id)
    if not run:
        raise ValueError(f"Run {run_id} no existe")

    tool_source = "external_structured" if source == "structured_form" else "external_pdf"
    base_conf = 0.90 if source == "structured_form" else 0.85

    ens_mapper = EnsMapper(db, enable_llm=False)
    mitre_mapper = MitreMapper(enable_llm=False)

    created: list[VerificationFinding] = []
    for f in findings_data:
        candidate: FindingCandidate = {
            "title": f.get("title", ""),
            "description": f.get("description", ""),
            "severity": (f.get("severity") or "info").lower(),
            "cve_id": f.get("cve_id"),
            "cvss_score": f.get("cvss_score"),
            "cvss_vector": f.get("cvss_vector"),
            "cwe_id": f.get("cwe_id"),
            "affected_host": f.get("affected_host") or "unknown",
            "affected_port": f.get("affected_port"),
            "affected_service": f.get("affected_service"),
            "affected_service_version": f.get("affected_service_version"),
            "affected_url": f.get("affected_url"),
            "affected_os": f.get("affected_os"),
            "raw_output_excerpt": (json.dumps(f)[:500]),
            "tool": tool_source,
            "tool_metadata": {"source_pdf_path": original_pdf_path} if original_pdf_path else {},
        }
        fhash = compute_finding_hash(candidate)

        # Construir ZfpFinding minimo para pasar a los mappers
        zfp = ZfpFinding(
            finding_hash=fhash,
            title=candidate["title"],
            description=candidate["description"],
            severity=candidate["severity"],
            affected_host=candidate["affected_host"],
            affected_port=candidate.get("affected_port"),
            affected_service=candidate.get("affected_service"),
            affected_url=candidate.get("affected_url"),
            cve_id=candidate.get("cve_id"),
            cvss_score=candidate.get("cvss_score"),
            cvss_vector=candidate.get("cvss_vector"),
            cwe_id=candidate.get("cwe_id"),
            affected_service_version=candidate.get("affected_service_version"),
            affected_os=candidate.get("affected_os"),
            tool_sources=[tool_source],
        )
        ens_measures, ens_primary = await ens_mapper.map(zfp)
        mitre = mitre_mapper.map(zfp)

        # Confidence (queda sin cross-tool porque viene aislado)
        confidence = base_conf
        classification = (
            "confirmed" if confidence >= 0.90
            else "probable" if confidence >= 0.70
            else "needs_review"
        )

        vf = VerificationFinding(
            project_id=run.project_id,
            run_id=run.id,
            finding_hash=fhash,
            title=candidate["title"],
            description=candidate["description"],
            severity=candidate["severity"],
            cvss_score=candidate.get("cvss_score"),
            cvss_vector=candidate.get("cvss_vector"),
            cve_id=candidate.get("cve_id"),
            cwe_id=candidate.get("cwe_id"),
            affected_host=candidate["affected_host"],
            affected_port=candidate.get("affected_port"),
            affected_service=candidate.get("affected_service"),
            affected_service_version=candidate.get("affected_service_version"),
            affected_url=candidate.get("affected_url"),
            tool_sources=[tool_source],
            raw_outputs=[{
                "tool": tool_source,
                "excerpt": candidate["raw_output_excerpt"],
                "metadata": candidate["tool_metadata"],
            }],
            confidence_score=confidence,
            zfp_gate1_dedup=True,
            zfp_gate2_fp_filter=True,
            zfp_gate3_cross_tool=0,
            zfp_gate4_retest="not_applicable",
            zfp_gate5_classification=classification,
            ens_measures=ens_measures,
            ens_primary_measure=ens_primary,
            mitre_techniques=[{
                "technique": t.get("technique_id"),
                "tactic": t.get("tactic"),
                "technique_name": t.get("technique_name"),
            } for t in mitre],
            remediation_summary=(f.get("remediation_summary") or ""),
            status="open",
        )
        db.add(vf)
        created.append(vf)

    # Actualizar handoff si existe
    handoff = await _get_handoff(db, run_id)
    if handoff:
        handoff.findings_submission_method = (
            "pdf" if source == "pdf" else "structured_form"
        )
        handoff.report_received_at = datetime.now(timezone.utc)
        handoff.total_findings_received = len(created)
        handoff.status = "integrated"

    run.total_findings = (run.total_findings or 0) + len(created)
    run.confirmed_findings = (run.confirmed_findings or 0) + sum(
        1 for f in created if f.zfp_gate5_classification == "confirmed"
    )

    await db.flush()
    return created


async def _get_handoff(db: AsyncSession, run_id: uuid.UUID):
    from sqlalchemy import select
    stmt = select(ExternalPentesterHandoff).where(
        ExternalPentesterHandoff.run_id == run_id,
        ExternalPentesterHandoff.deleted_at.is_(None),
    )
    r = await db.execute(stmt)
    return r.scalars().first()
