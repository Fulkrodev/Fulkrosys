"""DeliverableTextAuditor golden dataset evaluator · sub-atom 1.E.1.B.3.D Path C-light.

Skeleton evaluator que evalúa golden entries dataset `deliverable_text_auditor`
(10 entries v1 curated por Marcos en B.3.C). Real LLM wiring DEFERRED a
Future-1.E.1.dossier-pack-10docs (DeliverableTextAuditor capability build) ·
HOY: deterministic checks only (key_phrases · forbidden detection) · NO LLM
en critical path (R1 sostained).

Comportamiento:
  - Si actual_provider is None (default · capability_pending_build) → entry
    skipped explícito con reason
  - Si actual_provider provee output dict (mock OR future real LLM) → eval
    deterministic checks: verdict_match · required_missing · forbidden_present
    sin estar correctly flagged

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

    Currently skeleton path (NO real LLM wired):
      - actual=None significa actual_provider declined → entry SKIPPED
        con reason explícita (capability_pending_build)
      - actual=dict (mock OR future real) → deterministic checks ejecutan

    Real LLM wiring activates cuando DeliverableTextAuditor capability
    construida en Future-1.E.1.dossier-pack-10docs sub-atom.
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


# Side-effect registration · activated al importar el package
register_evaluator(_AGENT_NAME, deliverable_text_auditor_evaluator)
