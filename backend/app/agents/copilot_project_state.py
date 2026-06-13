"""Project-state composer for the copilots (2026-06-09).

Serializa el estado dinámico de UN proyecto en un bloque listo para inyectar en
el system prompt, de modo que el chat (cliente y admin) CONOZCA el proyecto en
el que está: fase actual, progreso, próximas acciones, bloqueos y (admin) gaps
de evidencia + métricas de cumplimiento.

Reutiliza infraestructura existente (OPS-026 DRY):
  - ``compute_workflow_state`` (m11_copiloto.workflow_state_scanner): el motor
    puro per-proyecto ya existente (fase + progreso + acciones admin/cliente +
    bloqueos + evidence_gap_measures). Es ``role_filter``-aware, así que el
    bloque cliente NUNCA incluye jerga ENS ni internals (R29) y el admin recibe
    el detalle completo (R30).
  - ``_get_project_context`` (m11_copiloto.api): métricas numéricas admin (DdA
    por estado, evidencias, findings, pentest, última simulación). Solo se
    inyecta para role=admin (R30 · contiene jerga ENS prohibida al cliente).

Contrato: el CALLER debe haber fijado el contexto RLS del proyecto antes
(``_set_project_rls`` en admin · ``_resolve_project_meta_scoped`` en cliente).
Best-effort: cualquier fallo devuelve "" → degradación grácil, nunca bloquea
la respuesta del copiloto.
"""
from __future__ import annotations

import logging
import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_MAX_ACTIONS = 3  # top-N acciones a listar (evita prompt verboso)
_MAX_BLOCKERS = 4
_MAX_EVIDENCE_GAPS = 8

_WAITING_ON_LABEL = {
    "admin": "Marcos",
    "cliente": "el cliente",
    "external_auditor": "el auditor ENAC externo",
    "system": "el sistema",
}


def _coerce_uuid(project_id) -> Optional[uuid.UUID]:
    if project_id is None:
        return None
    if isinstance(project_id, uuid.UUID):
        return project_id
    try:
        return uuid.UUID(str(project_id))
    except (ValueError, TypeError):
        return None


async def build_project_state_block(
    db: AsyncSession,
    project_id,
    role: str,
) -> str:
    """Devuelve el bloque "Estado actual del proyecto" listo para el prompt.

    Args:
        db: sesión async con el contexto RLS del proyecto YA fijado por el caller.
        project_id: UUID (o str) del proyecto activo.
        role: ``"admin"`` o ``"cliente"`` · filtra el contenido (R29/R30).

    Returns:
        Bloque markdown (str) o "" si no hay project_id o algo falla.
    """
    pid = _coerce_uuid(project_id)
    if pid is None:
        return ""

    role_filter = role if role in ("admin", "cliente") else None

    try:
        from backend.app.motors.m11_copiloto.workflow_state_scanner import (
            WorkflowScannerOptions,
            compute_workflow_state,
        )

        state = await compute_workflow_state(
            db, pid, WorkflowScannerOptions(role_filter=role_filter),
        )
    except Exception:  # noqa: BLE001 · best-effort
        logger.exception(
            "copilot project_state · compute_workflow_state falló · project_id=%s",
            project_id,
        )
        return ""

    lines: list[str] = [
        "## Estado actual del proyecto (datos EN VIVO de la plataforma)",
        "Usa estos datos para responder \"¿qué me falta?\", \"¿en qué punto "
        "estoy?\", \"¿qué hago ahora?\". NO los inventes ni los contradigas.",
        f"- Fase actual: {state.current_phase}",
    ]
    if state.categoria_objetivo:
        lines.append(f"- Categoría ENS: {state.categoria_objetivo}")
    if state.audit_passed_at:
        lines.append(f"- Auditoría/cierre superado: {state.audit_passed_at}")

    # Progreso de la fase actual (best-effort · heurístico del scanner).
    cur = next(
        (p for p in state.phase_progress if p.phase == state.current_phase),
        None,
    )
    if cur is not None:
        lines.append(
            f"- Progreso de la fase actual: {cur.completion_percentage}% "
            f"({cur.status})",
        )
    completed = sum(
        1 for p in state.phase_progress if p.status == "completed"
    )
    if state.phase_progress:
        lines.append(
            f"- Fases completadas: {completed}/{len(state.phase_progress)}",
        )

    # Próximas acciones (role-appropriate · description_cliente vs _admin).
    actions = (
        state.next_admin_actions if role == "admin"
        else state.next_cliente_actions
    )
    desc_attr = "description_admin" if role == "admin" else "description_cliente"
    action_lines = []
    for a in actions[:_MAX_ACTIONS]:
        desc = (getattr(a, desc_attr, "") or "").strip()
        if desc:
            action_lines.append(f"  - [{a.priority}] {desc}")
    if action_lines:
        header = (
            "- Próximos pasos para Marcos:" if role == "admin"
            else "- Lo que te toca ahora (sin prisa):"
        )
        lines.append(header)
        lines.extend(action_lines)

    # Bloqueos.
    if state.blockers:
        lines.append("- Bloqueos detectados:")
        for b in state.blockers[:_MAX_BLOCKERS]:
            who = _WAITING_ON_LABEL.get(b.waiting_on, b.waiting_on)
            lines.append(f"  - {b.description} (a la espera de: {who})")

    # Gaps de evidencia · SOLO admin (códigos ENS = jerga R30 · prohibido cliente).
    if role == "admin" and state.evidence_gap_measures:
        gaps = ", ".join(state.evidence_gap_measures[:_MAX_EVIDENCE_GAPS])
        lines.append(f"- Medidas ENS sin evidencia válida (top): {gaps}")

    # Métricas numéricas de cumplimiento · SOLO admin (R30 · jerga ENS).
    if role == "admin":
        numbers = await _admin_numbers_block(db, pid)
        if numbers:
            lines.extend(numbers)

    return "\n".join(lines)


async def _admin_numbers_block(
    db: AsyncSession, project_id: uuid.UUID,
) -> list[str]:
    """Métricas numéricas admin reutilizando ``_get_project_context`` (DRY).

    Best-effort: si el import o la query fallan devuelve []. Lazy import para
    evitar ciclo a nivel de módulo (m11.api importa agents).
    """
    try:
        from backend.app.motors.m11_copiloto.api import _get_project_context

        ctx = await _get_project_context(db, project_id)
    except Exception:  # noqa: BLE001 · best-effort
        logger.exception(
            "copilot project_state · _get_project_context falló · project_id=%s",
            project_id,
        )
        return []

    out: list[str] = []
    dda = ctx.get("dda") or {}
    dda_total = dda.get("total") or 0
    if dda_total:
        impl = (dda.get("by_estado") or {}).get("implantada", 0)
        pct = int(impl / dda_total * 100) if dda_total else 0
        out.append(
            f"- DdA: {dda_total} medidas · {impl} implantadas ({pct}%)",
        )
    ev = ctx.get("evidence") or {}
    if ev.get("total"):
        out.append(
            f"- Evidencias: {ev.get('total', 0)} total · "
            f"{ev.get('vigente', 0)} vigentes",
        )
    findings = (ctx.get("findings") or {}).get("total")
    if findings:
        out.append(f"- Findings abiertos: {findings}")
    pentest = (ctx.get("pentest") or {}).get("findings_total")
    if pentest:
        out.append(f"- Pentest findings (confirmados/probables): {pentest}")
    sim = ctx.get("last_audit_sim")
    if sim and sim.get("score_global") is not None:
        out.append(
            f"- Última auditoría simulada: score {sim.get('score_global')}/100 · "
            f"recomendación {sim.get('recomendacion')}",
        )
    return out
