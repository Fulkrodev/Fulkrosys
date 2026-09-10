"""DeliverableTextAuditor golden dataset evaluator · sub-atom 1.E.1.B.3.D Path C-light.

Evalúa las 10 golden entries del dataset `deliverable_text_auditor` (v1, curadas
por Marcos en B.3.C). La capability real está construida y cableada (campaña
auditoría 2026-06-17 · S1): `golden_eval_runs_service.execute_eval_run_sync`
pasa como `actual_provider` la función que invoca
`deliverable_text_auditor_capability.audit_deliverable_sync` (LLM Sonnet,
temp ≤0.2 R3). Con ANTHROPIC_API_KEY presente el provider devuelve el dict
veredicto y este evaluador ejecuta los checks; sin key devuelve None y el entry
se salta legítimamente (NO se inventa veredicto · honest path).

El evaluador en sí es DETERMINISTA (R1 sostained · NO llama al LLM): sobre el
`actual` recibido comprueba verdict_match · key_phrases_required · key_phrases
prohibidas no-flagged.

Comportamiento:
  - actual is None (sin API key o sin texto) → entry skipped explícito con reason
  - actual=dict (capability real o mock test) → checks deterministas:
    verdict_match · required_missing · forbidden_present sin flag

Pattern OPS-026 DRY · sostiene _default_skeleton_evaluator existing en
eval_runner · agrega structured fields (EntryEvalResult extension) +
verdict_match check + correctly-flagged-forbidden detection.

Registered al import via `evaluators/__init__.py` side-effect.
"""
from __future__ import annotations

import json
from typing import Any

from backend.app.motors.m_observability.eval_runner import (
    EntryEvalResult,
    register_evaluator,
    register_synthetic_output,
)
from backend.app.motors.m_observability.golden_datasets_loader import (
    GoldenDatasetEntry,
)


_AGENT_NAME = "deliverable_text_auditor"


def _stringify_for_match(actual: Any) -> str:
    """Render actual output as case-insensitive searchable string."""
    if actual is None:
        return ""
    if isinstance(actual, str):
        return actual.lower()
    try:
        return json.dumps(actual, ensure_ascii=False).lower()
    except (TypeError, ValueError):
        return str(actual).lower()


def _flagged_in_issues(phrase: str, actual: Any) -> bool:
    """Verifica si phrase aparece en issues_critical/moderate del actual.

    Sostiene: "forbidden phrase OK si auditor lo FLAGGED como issue" · NO
    es failure si A11/DeliverableTextAuditor detectó correctamente la jerga.
    """
    if not isinstance(actual, dict):
        return False
    phrase_lower = phrase.lower()
    for key in ("issues_critical", "issues_moderate"):
        issues = actual.get(key) or []
        if not isinstance(issues, list):
            continue
        for issue in issues:
            if phrase_lower in str(issue).lower():
                return True
    return False


def deliverable_text_auditor_evaluator(
    entry: GoldenDatasetEntry,
    actual: Any,
) -> EntryEvalResult:
    """Structured evaluator · returns EntryEvalResult directo.

    Capability real ya cableada (S1 · ver docstring de módulo):
      - actual=None significa que el provider declinó (sin ANTHROPIC_API_KEY o
        sin texto en el entry) → entry SKIPPED con reason explícita
      - actual=dict (capability real audit_deliverable_sync o mock test) →
        deterministic checks ejecutan
    """
    if actual is None:
        return EntryEvalResult(
            entry_id=entry.id,
            category=entry.category,
            passed=False,
            diff_summary="skipped · capability pending build",
            skipped=True,
            skip_reason=(
                "deliverable_text_auditor capability pending build · "
                "Future-1.E.1.dossier-pack-10docs"
            ),
        )

    # ── Deterministic checks (NO LLM en critical path · R1 sostained) ──

    actual_text = _stringify_for_match(actual)

    # 1. Verdict match (si actual tiene verdict field)
    expected_verdict = entry.expected_output.verdict
    actual_verdict: str | None = None
    if isinstance(actual, dict):
        v = actual.get("verdict")
        if isinstance(v, str):
            actual_verdict = v
    verdict_match: bool | None
    if expected_verdict is None:
        verdict_match = None  # No expected · NO check
    else:
        verdict_match = actual_verdict == expected_verdict

    # 2. key_phrases_required · MUST appear in actual stringified
    required = entry.expected_output.key_phrases_required
    required_missing = [
        phrase for phrase in required
        if phrase.lower() not in actual_text
    ]

    # 3. key_phrases_forbidden · MUST NOT appear OR MUST be flagged como issue
    forbidden = entry.expected_output.key_phrases_forbidden
    forbidden_present_unflagged: list[str] = []
    for phrase in forbidden:
        if phrase.lower() in actual_text:
            if not _flagged_in_issues(phrase, actual):
                forbidden_present_unflagged.append(phrase)

    # 4. Pass = verdict_match (si applicable) AND no missing AND no unflagged
    verdict_pass = verdict_match is True or verdict_match is None
    passed = (
        verdict_pass
        and len(required_missing) == 0
        and len(forbidden_present_unflagged) == 0
    )

    # 5. Diff summary
    diffs: list[str] = []
    if verdict_match is False:
        diffs.append(
            f"verdict mismatch · expected={expected_verdict} "
            f"actual={actual_verdict}"
        )
    if required_missing:
        diffs.append(
            f"missing required phrases: {required_missing[:3]}"
            + (f" +{len(required_missing) - 3} more"
               if len(required_missing) > 3 else "")
        )
    if forbidden_present_unflagged:
        diffs.append(
            f"forbidden unflagged: {forbidden_present_unflagged[:3]}"
            + (f" +{len(forbidden_present_unflagged) - 3} more"
               if len(forbidden_present_unflagged) > 3 else "")
        )

    return EntryEvalResult(
        entry_id=entry.id,
        category=entry.category,
        passed=passed,
        diff_summary="; ".join(diffs) if diffs else "ok",
        verdict_match=verdict_match,
        required_missing=required_missing,
        forbidden_present_unflagged=forbidden_present_unflagged,
        actual_summary={
            "verdict": actual_verdict,
            "issues_critical_count": (
                len(actual.get("issues_critical") or [])
                if isinstance(actual, dict) else None
            ),
        },
    )


def salida_sintetica(entry: GoldenDatasetEntry) -> dict[str, Any]:
    """Salida perfecta para `entry` con la forma de `audit_deliverable_sync`.

    BLOQUE D · D2. Este diccionario estaba escrito a mano dentro de
    `.github/workflows/evals.yml`, en el gate de auto-consistencia del
    arnés. Se ha traído aquí sin cambiar un solo campo: la forma de la
    salida de un agente es conocimiento de su evaluador, no del fichero de
    CI, y con cuatro datasets el YAML no puede conocer cuatro esquemas.

    Lo usa el gate del arnés para comprobar que dataset y evaluador siguen
    siendo compatibles. NO llama al modelo ni pretende parecerse a lo que
    el modelo respondería: es el techo, la respuesta que aprueba por
    construcción.
    """
    esperado = entry.expected_output
    return {
        "verdict": esperado.verdict,
        "issues_critical": list(esperado.issues_critical),
        "issues_moderate": list(esperado.issues_moderate),
        "key_phrases_found": list(esperado.key_phrases_required),
    }


# Side-effect registration · activated al importar el package
register_evaluator(_AGENT_NAME, deliverable_text_auditor_evaluator)
register_synthetic_output(_AGENT_NAME, salida_sintetica)
