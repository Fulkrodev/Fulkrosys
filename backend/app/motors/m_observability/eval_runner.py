"""Golden datasets eval runner · sub-atom 1.E.1.B.3.B.

Agent-agnostic runner que carga golden dataset · evalúa cada entry contra
output real del agente (LLM call when API key available · skip otherwise) ·
computa pass_rate · genera reporte markdown/json · exit code basado en
regression thresholds.

CLI usage:
  python -m backend.app.motors.m_observability.eval_runner \\
      --agent agent_11_auditor_virtual --version v1 \\
      --skip-llm-if-no-key --report-out /tmp/report.md

Exit codes:
  0 = pass_rate ≥ pass_rate_warn_below (verde)
  1 = warn (regression detectada · pass_rate < pass_rate_warn_below)
  2 = alert (pass_rate < pass_rate_alert_below · critical)

Skeleton phase (B.3.B): runner infrastructure + CLI · 0 golden entries
todavía · evaluator stub returns pass=True per entry vacío. Real evaluators
agent-specific en B.3.D post-curation Marcos B.3.C.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from backend.app.motors.m_observability.golden_datasets_loader import (
    GoldenDataset,
    GoldenDatasetEntry,
    GoldenDatasetLoadError,
    load_golden_dataset,
)


# ════════════════════════════════════════════════════════════════════
# Result dataclasses
# ════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class EntryEvalResult:
    """Per-entry eval outcome.

    B.3.D Path C-light extensions (optional · backward-compat con skeleton
    evaluator que retorna tuple[bool, str]):
      - verdict_match · True/False/None si evaluator compara verdicts
      - required_missing · list[str] phrases required ausentes en actual
      - forbidden_present_unflagged · list[str] phrases forbidden presentes
        sin estar correctly flagged por el auditor
      - actual_summary · dict resumen output real (e.g. verdict + counts)
      - skipped · True si evaluator declined evaluación (capability pending)
      - skip_reason · texto reason si skipped=True
    """

    entry_id: str
    category: str
    passed: bool
    diff_summary: str
    duration_ms: int = 0
    verdict_match: bool | None = None
    required_missing: list[str] = field(default_factory=list)
    forbidden_present_unflagged: list[str] = field(default_factory=list)
    actual_summary: dict[str, Any] | None = None
    skipped: bool = False
    skip_reason: str | None = None


@dataclass(frozen=True)
class DatasetEvalReport:
    """Aggregate eval outcome para todo el dataset.

    total_entries: cuántas entries fueron EVALUADAS (passed + failed).
    entries_in_dataset: cuántas entries existen en el dataset (curated).
    entries_skipped = entries_in_dataset - total_entries.
    """

    agent_name: str
    version: str
    total_entries: int
    passed: int
    failed: int
    pass_rate: float
    severity: str  # "ok" | "warn" | "alert"
    entries_in_dataset: int = 0
    entry_results: list[EntryEvalResult] = field(default_factory=list)


# ════════════════════════════════════════════════════════════════════
# Evaluator registry (agent-agnostic dispatch)
# ════════════════════════════════════════════════════════════════════


# Evaluator callable: (entry, actual_output) → tuple[bool, str] OR EntryEvalResult
# B.3.B legacy returns tuple · B.3.D Path C-light evaluators puede retornar
# EntryEvalResult directo para usar campos estructurados (verdict_match · etc).
EvaluatorReturn = Any  # tuple[bool, str] | EntryEvalResult
EvaluatorFn = Callable[[GoldenDatasetEntry, dict[str, Any]], EvaluatorReturn]

# B.3.D Path C-light populates this con skeleton evaluators (NO LLM call)
_AGENT_EVALUATORS: dict[str, EvaluatorFn] = {}


def register_evaluator(agent_name: str, fn: EvaluatorFn) -> None:
    """Register custom evaluator per agente · used en B.3.D."""
    _AGENT_EVALUATORS[agent_name] = fn


def _default_skeleton_evaluator(
    entry: GoldenDatasetEntry, actual: dict[str, Any],
) -> tuple[bool, str]:
    """Skeleton default · checks rubric.structure_check + key_phrases.

    B.3.B placeholder · real evaluators agent-specific en B.3.D.
    """
    diffs: list[str] = []

    # Structure check: actual debe ser dict (NO None · NO list)
    if entry.rubric.structure_check and not isinstance(actual, dict):
        diffs.append(f"structure_check failed · actual type={type(actual).__name__}")
        return False, "; ".join(diffs)

    # Key phrases required · actual stringified MUST contain ALL
    actual_str = json.dumps(actual, ensure_ascii=False).lower()
    for phrase in entry.expected_output.key_phrases_required:
        if phrase.lower() not in actual_str:
            diffs.append(f"missing required phrase '{phrase}'")

    # Key phrases forbidden · actual stringified MUST contain NONE
    for phrase in entry.expected_output.key_phrases_forbidden:
        if phrase.lower() in actual_str:
            diffs.append(f"contains forbidden phrase '{phrase}'")

    passed = not diffs
    return passed, "; ".join(diffs) if diffs else "ok"


# ════════════════════════════════════════════════════════════════════
# Runner
# ════════════════════════════════════════════════════════════════════


def _classify_severity(
    pass_rate: float, dataset: GoldenDataset,
) -> str:
    """ok / warn / alert basado en regression_thresholds."""
    if pass_rate < dataset.regression_thresholds.pass_rate_alert_below:
        return "alert"
    if pass_rate < dataset.regression_thresholds.pass_rate_warn_below:
        return "warn"
    return "ok"


def run_eval(
    agent_name: str,
    version: str = "v1",
    *,
    skip_llm_if_no_key: bool = True,
    actual_provider: Callable[
        [GoldenDatasetEntry], dict[str, Any] | None,
    ] | None = None,
    root: Path | None = None,
) -> DatasetEvalReport:
    """Execute eval pipeline · returns aggregate DatasetEvalReport.

    Parameters:
      actual_provider: optional callable que recibe entry · retorna actual
                       output dict (or None to skip entry). B.3.D wires
                       real LLM call provider · B.3.B usa skeleton stub.
      root: optional override del GOLDEN_DATASETS_ROOT (tests + sandbox).

    Skeleton behavior: cuando dataset.entries == [] → returns report con
    total=0 · pass_rate=1.0 (vacuously true) · severity="ok".
    """
    dataset = load_golden_dataset(agent_name, version, root=root)
    evaluator = _AGENT_EVALUATORS.get(agent_name, _default_skeleton_evaluator)

    results: list[EntryEvalResult] = []
    passed = 0
    failed = 0

    # Skip flag check
    has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
    skip_llm = skip_llm_if_no_key and not has_api_key

    for entry in dataset.entries:
        # B.3.D Path C-light: when NO actual_provider · let evaluator decide
        # skip semantics passing actual=None. Custom evaluators (e.g.
        # deliverable_text_auditor) retornan EntryEvalResult(skipped=True,
        # skip_reason="capability_pending_build"). Default skeleton evaluator
        # returns tuple → tratado como failed (legacy · only for synthetic
        # datasets sin custom evaluator).
        if actual_provider is None:
            if skip_llm and agent_name not in _AGENT_EVALUATORS:
                # NO custom evaluator + skip flag → continue (counts neither)
                continue
            actual = None  # evaluator decides skip semantics
        else:
            actual = actual_provider(entry)
            if actual is None:
                # provider declined (e.g. no API key) · skip entry
                continue

        raw = evaluator(entry, actual)
        # Support both return types · tuple[bool, str] (B.3.B legacy) OR
        # EntryEvalResult directo (B.3.D Path C-light structured fields).
        if isinstance(raw, EntryEvalResult):
            result = raw
        else:
            is_pass, diff = raw
            result = EntryEvalResult(
                entry_id=entry.id,
                category=entry.category,
                passed=is_pass,
                diff_summary=diff,
            )
        results.append(result)
        # Skipped entries NO cuentan en passed/failed denominator
        if result.skipped:
            continue
        if result.passed:
            passed += 1
        else:
            failed += 1

    total = passed + failed
    pass_rate = 1.0 if total == 0 else (passed / total)
    severity = _classify_severity(pass_rate, dataset)

    return DatasetEvalReport(
        agent_name=agent_name,
        version=version,
        total_entries=total,
        passed=passed,
        failed=failed,
        pass_rate=pass_rate,
        severity=severity,
        entries_in_dataset=len(dataset.entries),
        entry_results=results,
    )


def compute_regression_score(report: DatasetEvalReport) -> float:
    """Equivalente a report.pass_rate · helper público para callers."""
    return report.pass_rate


# ════════════════════════════════════════════════════════════════════
# Report formatters
# ════════════════════════════════════════════════════════════════════


def format_eval_report_markdown(report: DatasetEvalReport) -> str:
    """Render Markdown report · human-readable + CI artifact friendly."""
    lines: list[str] = []
    lines.append(f"# Golden eval report · {report.agent_name} {report.version}")
    lines.append("")
    severity_label = {
        "ok": "✅ OK",
        "warn": "⚠️ WARN",
        "alert": "🛑 ALERT",
    }.get(report.severity, report.severity)
    lines.append(f"**Severity**: {severity_label}")
    lines.append(f"**Pass rate**: {report.pass_rate:.2%}")
    lines.append(
        f"**Total evaluated**: {report.total_entries} "
        f"(passed={report.passed} · failed={report.failed})",
    )
    if report.entries_in_dataset > 0:
        lines.append(
            f"**Entries in dataset**: {report.entries_in_dataset} "
            f"(skipped={report.entries_in_dataset - report.total_entries})",
        )
    lines.append("")
    if report.entries_in_dataset == 0:
        lines.append(
            "_Skeleton dataset · 0 entries curated todavía · "
            "B.3.C curation Marcos input pending._",
        )
    elif report.total_entries == 0:
        lines.append(
            "_All entries skipped · likely B.3.D actual_provider not wired or "
            "ANTHROPIC_API_KEY missing · skeleton infrastructure phase._",
        )
    else:
        lines.append("## Per-entry results")
        lines.append("")
        lines.append("| Entry ID | Category | Result | Diff summary |")
        lines.append("|----------|----------|--------|--------------|")
        for r in report.entry_results:
            mark = "✅" if r.passed else "❌"
            diff = r.diff_summary.replace("|", "\\|")[:100]
            lines.append(
                f"| `{r.entry_id}` | {r.category} | {mark} | {diff} |",
            )
    return "\n".join(lines) + "\n"


def format_eval_report_json(report: DatasetEvalReport) -> str:
    return json.dumps(
        {
            "agent_name": report.agent_name,
            "version": report.version,
            "total_entries": report.total_entries,
            "entries_in_dataset": report.entries_in_dataset,
            "passed": report.passed,
            "failed": report.failed,
            "pass_rate": report.pass_rate,
            "severity": report.severity,
            "entry_results": [
                {
                    "entry_id": r.entry_id,
                    "category": r.category,
                    "passed": r.passed,
                    "diff_summary": r.diff_summary,
                }
                for r in report.entry_results
            ],
        },
        ensure_ascii=False,
        indent=2,
    )


# ════════════════════════════════════════════════════════════════════
# ComplianceAlert integration shell (B.3.D Path C-light)
# ════════════════════════════════════════════════════════════════════


def maybe_create_regression_alert(
    report: DatasetEvalReport,
    *,
    threshold_warn: float = 0.8,
    threshold_alert: float = 0.6,
    alert_factory: Callable[..., Any] | None = None,
) -> dict[str, Any] | None:
    """Create ComplianceAlert si regression detectada.

    Skip si all entries skipped (capability_pending · no real eval yet).
    HIGH severity si pass_rate < threshold_alert · MEDIUM si <threshold_warn.

    Parameters:
      alert_factory: dependency-injected callable (test seam · default None
                     uses production m_compliance_monitor.service factory si
                     disponible · gracefully no-op si motor not wired).

    Returns dict descriptor del alert creado (o None si no creado).
    """
    non_skipped = [r for r in report.entry_results if not r.skipped]
    if not non_skipped:
        # All entries skipped · NO alert · capability pending build
        return None

    if report.pass_rate >= threshold_warn:
        return None

    severity = "HIGH" if report.pass_rate < threshold_alert else "MEDIUM"
    failed_entry_ids = [r.entry_id for r in non_skipped if not r.passed]
    descriptor = {
        "norma": "INTERNAL_GOLDEN_EVAL",
        "severity": severity,
        "message": (
            f"Golden eval regression · agent={report.agent_name} "
            f"version={report.version} · pass_rate={report.pass_rate:.1%} "
            f"< threshold_warn={threshold_warn:.0%}"
        ),
        "metadata": {
            "agent_name": report.agent_name,
            "dataset_version": report.version,
            "pass_rate": report.pass_rate,
            "failed_entry_ids": failed_entry_ids,
            "entries_in_dataset": report.entries_in_dataset,
            "entries_evaluated": report.total_entries,
        },
    }

    # Test seam: alert_factory permite inyectar mock en tests · default None
    # intenta wire a m_compliance_monitor (graceful fail si motor not init).
    if alert_factory is not None:
        try:
            alert_factory(**descriptor)
        except Exception:  # noqa: BLE001
            pass  # graceful · test-driven behavior
    return descriptor


# ════════════════════════════════════════════════════════════════════
# CLI entry
# ════════════════════════════════════════════════════════════════════


def _exit_code_for_severity(severity: str) -> int:
    return {"ok": 0, "warn": 1, "alert": 2}.get(severity, 0)


def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="m_observability.eval_runner",
        description="FULKRO golden datasets eval runner · sub-atom 1.E.1.B.3",
    )
    parser.add_argument(
        "--agent", default=None,
        help="Agent name (e.g. agent_11_auditor_virtual) · required unless --list",
    )
    parser.add_argument(
        "--version", default="v1",
        help="Dataset version slug (default v1)",
    )
    parser.add_argument(
        "--skip-llm-if-no-key", action="store_true", default=True,
        help="Graceful skip si ANTHROPIC_API_KEY missing (default True)",
    )
    parser.add_argument(
        "--report-out", default=None,
        help="Path para escribir report (default stdout)",
    )
    parser.add_argument(
        "--format", choices=["markdown", "json"], default="markdown",
        help="Report format (default markdown)",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List available datasets en lugar de ejecutar eval",
    )
    args = parser.parse_args(argv)

    if args.list:
        from backend.app.motors.m_observability.golden_datasets_loader import (
            list_available_datasets,
        )
        for agent, version in list_available_datasets():
            print(f"{agent}\t{version}")
        return 0

    if not args.agent:
        parser.error("--agent required unless --list")

    try:
        report = run_eval(
            args.agent, args.version,
            skip_llm_if_no_key=args.skip_llm_if_no_key,
        )
    except GoldenDatasetLoadError as exc:
        print(f"ERROR · {exc}", file=sys.stderr)
        return 3

    rendered = (
        format_eval_report_json(report)
        if args.format == "json"
        else format_eval_report_markdown(report)
    )

    if args.report_out:
        Path(args.report_out).write_text(rendered, encoding="utf-8")
        print(f"Report written to {args.report_out}", file=sys.stderr)
    else:
        print(rendered)

    print(
        f"severity={report.severity} pass_rate={report.pass_rate:.2%} "
        f"total={report.total_entries}",
        file=sys.stderr,
    )
    return _exit_code_for_severity(report.severity)


if __name__ == "__main__":
    sys.exit(_cli())
