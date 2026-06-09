"""#45 OlaIII · Vista cruzada estado-implementación × pagos.

Las dos mitades ya existían sueltas (roadmap de fases vs hitos de cobro). Este
servicio las CRUZA: para cada hito de contrato (``ContractMilestone``) sitúa su
fase de workflow (``workflow_phase_index``) frente a la fase actual del proyecto
(``projects.fase``) y deriva un estado de pago legible — *pagado / pendiente (la
fase ya se alcanzó) / próximo (la fase aún no llega)* — más la fecha prevista de
cobro (#28 ``scheduled_date``) y la marca de vencido.

Pure-functional + un builder async que compone ``projects`` + ``contract_milestones``
(ADR-025: NO tabla nueva, deriva on-query). Reutilizable por el endpoint admin
(detalle completo) y el del portal cliente (subconjunto amable R29).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.workflow_phase import WorkflowPhase

# Etiquetas de fase legibles (cliente-friendly · R29 · sin jerga ENS interna).
PHASE_LABELS: dict[str, str] = {
    "pre_venta": "Pre-venta",
    "onboarding": "Inicio del proyecto",
    "diagnostico": "Diagnóstico",
    "analisis_riesgos": "Análisis de riesgos",
    "adecuacion": "Adecuación",
    "implantacion": "Implantación",
    "dda_final": "Declaración de aplicabilidad final",
    "verificacion": "Verificación",
    "conformidad": "Certificación",
    "retainer_cierre": "Cierre y mantenimiento",
}

_ORDERED_VALUES = [p.value for p in WorkflowPhase.ordered()]
# Estados liquidados (no exigen cobro futuro). Se usan tanto en derive_payment_state
# (etiqueta de línea) como en el cómputo de totales, para que NO haya incoherencia
# entre una línea mostrada como "Pagado" y su importe cayendo en pendiente (#45 fix).
_SETTLED_STATUSES = ("paid", "refunded")


def phase_label(phase_index: int) -> str:
    """Etiqueta legible de una fase por su índice 0-based (clamp a rango)."""
    if phase_index < 0 or phase_index >= len(_ORDERED_VALUES):
        return f"Fase {phase_index}"
    return PHASE_LABELS.get(_ORDERED_VALUES[phase_index], _ORDERED_VALUES[phase_index])


def current_phase_index(fase: str | None) -> int:
    """Índice 0-based de la fase actual del proyecto (0 si desconocida)."""
    if not fase:
        return 0
    try:
        return _ORDERED_VALUES.index(fase)
    except ValueError:
        return 0


def derive_payment_state(phase_reached: bool, status: str) -> str:
    """Estado de pago legible cruzando avance × estado del hito.

    - ``paid``      el hito está cobrado (status paid/refunded).
    - ``due``       la fase que dispara el cobro YA se alcanzó pero no está pagado.
    - ``upcoming``  la fase aún no llega · pago futuro previsto.
    """
    if status in _SETTLED_STATUSES:
        return "paid"
    return "due" if phase_reached else "upcoming"


def is_overdue(scheduled_date: date | None, status: str, today: date) -> bool:
    """Vencido = fecha prevista pasada y aún sin liquidar."""
    if status in _SETTLED_STATUSES:
        return False
    return bool(scheduled_date and scheduled_date < today)


def _amount_with_vat(amount: Decimal, vat_percent: Decimal) -> Decimal:
    return (amount * (Decimal("100") + vat_percent) / Decimal("100")).quantize(
        Decimal("0.01")
    )


async def build_implementation_payments(
    db: AsyncSession,
    project_id,
    *,
    today: date | None = None,
) -> dict:
    """Compone la vista cruzada para un proyecto. Asume contexto RLS ya fijado
    por el endpoint (admin escala a fulkro · cliente fija current_project_id)."""
    from datetime import datetime, timezone

    today = today or datetime.now(timezone.utc).date()

    proj = (
        await db.execute(
            text(
                "SELECT id, nombre, categoria_objetivo, fase FROM projects "
                "WHERE id = :pid AND deleted_at IS NULL"
            ),
            {"pid": str(project_id)},
        )
    ).first()
    if proj is None:
        return {
            "project_id": str(project_id),
            "found": False,
            "milestones": [],
            "totals": _empty_totals(),
        }

    cur_idx = current_phase_index(proj[3])
    rows = (
        await db.execute(
            text(
                "SELECT id, milestone_index, milestone_name, workflow_phase_index, "
                "amount_eur, vat_percent, percent_of_total, scheduled_date, status, "
                "paid_at, billed_at, metadata_jsonb "
                "FROM contract_milestones "
                "WHERE project_id = :pid AND deleted_at IS NULL "
                "ORDER BY milestone_index ASC"
            ),
            {"pid": str(project_id)},
        )
    ).all()

    milestones: list[dict] = []
    total_amount = Decimal("0")
    paid_amount = Decimal("0")
    overdue_count = 0
    next_due_date: date | None = None

    for r in rows:
        phase_idx = int(r[3])
        amount = Decimal(str(r[4]))
        vat = Decimal(str(r[5] if r[5] is not None else "21.00"))
        status_val = r[8] or "pending"
        scheduled = r[7]
        phase_reached = cur_idx >= phase_idx
        state = derive_payment_state(phase_reached, status_val)
        overdue = is_overdue(scheduled, status_val, today)
        meta = r[11] or {}
        description = meta.get("description") if isinstance(meta, dict) else None

        total_amount += amount
        if status_val in _SETTLED_STATUSES:
            paid_amount += amount
        if overdue:
            overdue_count += 1
        if state != "paid" and scheduled is not None:
            if next_due_date is None or scheduled < next_due_date:
                next_due_date = scheduled

        milestones.append(
            {
                "milestone_id": str(r[0]),
                "milestone_index": int(r[1]),
                "milestone_name": r[2],
                "description": description,
                "workflow_phase_index": phase_idx,
                "phase_label": phase_label(phase_idx),
                "amount_eur": f"{amount:.2f}",
                "vat_percent": f"{vat:.2f}",
                "amount_with_vat_eur": f"{_amount_with_vat(amount, vat):.2f}",
                "percent_of_total": (
                    f"{Decimal(str(r[6])):.2f}" if r[6] is not None else None
                ),
                "scheduled_date": scheduled.isoformat() if scheduled else None,
                "status": status_val,
                "payment_state": state,
                "phase_reached": phase_reached,
                "is_overdue": overdue,
                "paid_at": r[9].isoformat() if r[9] else None,
                "billed_at": r[10].isoformat() if r[10] else None,
            }
        )

    pending_amount = total_amount - paid_amount
    return {
        "project_id": str(proj[0]),
        "project_name": proj[1] or "Proyecto",
        "categoria": proj[2],
        "current_phase": proj[3],
        "current_phase_index": cur_idx,
        "current_phase_label": phase_label(cur_idx),
        "found": True,
        "milestones": milestones,
        "totals": {
            "total_eur": f"{total_amount:.2f}",
            "paid_eur": f"{paid_amount:.2f}",
            "pending_eur": f"{pending_amount:.2f}",
            "overdue_count": overdue_count,
            "next_due_date": next_due_date.isoformat() if next_due_date else None,
        },
    }


def _empty_totals() -> dict:
    return {
        "total_eur": "0.00",
        "paid_eur": "0.00",
        "pending_eur": "0.00",
        "overdue_count": 0,
        "next_due_date": None,
    }


__all__ = [
    "PHASE_LABELS",
    "phase_label",
    "current_phase_index",
    "derive_payment_state",
    "is_overdue",
    "build_implementation_payments",
]
