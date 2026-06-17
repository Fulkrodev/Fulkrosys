"""DeliverableTextAuditor capability (S1 fix campaña auditoría).

Audita el TEXTO de un entregable ENS (Declaración de Aplicabilidad, informe,
política…) y emite veredicto + issues. Es la capability BAJO PRUEBA del golden
dataset `deliverable_text_auditor` (m_observability) — el evaluador determinista
(deliverable_text_auditor_evaluator) la puntúa contra las 10 entradas curadas.

Antes: no existía → el evaluador recibía actual=None → TODAS las entradas se
saltaban → golden eval completaba vacuamente (entries_evaluated=0, pass_rate=1.0)
enmascarando regresiones del LLM. Ahora la capability existe y se cablea como
actual_provider en golden_eval_runs_service.

R3: temperature 0.0. Infra-gated: requiere ANTHROPIC_API_KEY (es el LLM bajo
prueba). Sin clave → devuelve None y el entry se salta legítimamente (no es
"capability pending build"). El veredicto usa el vocabulario EXACTO del dataset:
PASS_AUDITOR_READY | NEEDS_REVISION | FAIL_CRITICAL.
"""
from __future__ import annotations

import json
import os
from typing import Any

from loguru import logger

_SYSTEM_PROMPT = (
    "Eres un auditor experto de entregables del Esquema Nacional de Seguridad "
    "(RD 311/2022). Audita el TEXTO del entregable y emite un veredicto sobre su "
    "calidad para presentarlo a un auditor ENAC. Reglas críticas:\n"
    "- La Declaración de Aplicabilidad (DoA) NO es la Declaración de Conformidad; "
    "no debe confundirlas ni prometer certificación sin auditoría.\n"
    "- El alcance debe ser explícito; la tabla de aplicabilidad debe llevar "
    "estado + evidencia + responsable por medida; categorización DICAT justificada.\n"
    "- MEDIA exige MFA; ALTA exige SOC + DR + monitorización 24/7.\n"
    "- Lenguaje formal; frases vagas tipo 'se cumplirán las medidas' son rechazables.\n"
    "Veredicto EXACTO uno de: PASS_AUDITOR_READY (listo), NEEDS_REVISION "
    "(observaciones subsanables), FAIL_CRITICAL (deficiencias graves).\n"
    "Responde SOLO JSON: {\"verdict\": \"...\", \"issues_critical\": [\"...\"], "
    "\"issues_moderate\": [\"...\"], \"key_phrases_found\": [\"...\"]}. En "
    "key_phrases_found incluye TODAS las expresiones/códigos ENS que aparezcan en "
    "el entregable (p.ej. 'Real Decreto 311/2022', 'Anexo II', 'op.acc.5', 'mp.', "
    "dimensiones DICAT, 'alcance', 'responsable de seguridad', 'evidencia')."
)

_VALID_VERDICTS = {"PASS_AUDITOR_READY", "NEEDS_REVISION", "FAIL_CRITICAL"}


def audit_deliverable_sync(
    deliverable_text: str, ens_category: str = "BASICA",
) -> dict[str, Any] | None:
    """Audita un entregable ENS · dict {verdict, issues_*, key_phrases_found} o
    None si no hay LLM disponible (sin ANTHROPIC_API_KEY o fallo)."""
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        return None
    if not deliverable_text or not deliverable_text.strip():
        return None
    try:
        from backend.app.core.ai.llm_router import get_default_llm_router

        router = get_default_llm_router()
        resp = router.complete(
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": (
                    f"Categoría ENS objetivo: {ens_category}\n\n"
                    f"ENTREGABLE:\n{deliverable_text[:12000]}"
                )},
            ],
            model="claude-sonnet-4-6",
            max_tokens=1200,
            temperature=0.0,
        )
        text = resp.content.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        parsed = json.loads(text.strip())
    except Exception as exc:  # noqa: BLE001 — infra-gated, graceful skip
        logger.warning("audit_deliverable LLM no disponible/fallo: %s", exc)
        return None

    verdict = parsed.get("verdict")
    if verdict not in _VALID_VERDICTS:
        verdict = None
    return {
        "verdict": verdict,
        "issues_critical": list(parsed.get("issues_critical") or []),
        "issues_moderate": list(parsed.get("issues_moderate") or []),
        "key_phrases_found": list(parsed.get("key_phrases_found") or []),
    }
