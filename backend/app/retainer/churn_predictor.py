"""ChurnPredictor heurístico explicable (MB-18.4 ADR-040).

NO ML black-box · 6 reglas if/then auditables ENAC compliance.

Score 0-100 capped. Risk level mapping:
- 0-29 → low
- 30-59 → medium
- 60-79 → high
- 80-100 → critical

Reglas:
- +40 si days_since_portal_login > 60
- +25 si tasks_overdue_count > 3
- +25 si invoices_overdue_count > 0
- +20 si avg_response_time_hours > 48
- +15 si nps_last_score < 6
- +10 si renewal_in_days < 90

Persist ``RetainerHealthSignal`` row + alert AlertService category=
``retainer_overdue`` (existing) si critical.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.billing_milestones import RetainerHealthSignal
from backend.app.models.retainer import RetainerContract

logger = logging.getLogger(__name__)


THRESHOLD_DAYS_LOGIN = 60
THRESHOLD_TASKS_OVERDUE = 3
THRESHOLD_RESPONSE_HOURS = Decimal("48.00")
THRESHOLD_NPS_LOW = 6
THRESHOLD_RENEWAL_NEAR = 90


@dataclass
class ChurnSignals:
    days_since_portal_login: int | None = None
    days_since_chat_msg_client: int | None = None
    tasks_overdue_count: int = 0
    invoices_overdue_count: int = 0
    avg_response_time_hours: Decimal | None = None
    nps_last_score: int | None = None
    renewal_in_days: int | None = None


@dataclass
class ChurnComputation:
    score: Decimal
    risk_level: str
    factors: list[str] = field(default_factory=list)
    recommended_action: str = ""


def compute_churn_score(signals: ChurnSignals) -> ChurnComputation:
    """Aplica reglas heurísticas explicables · returns score + factors.

    Regla per signal · accumulate score · cap [0, 100] · derive
    risk_level + recommended_action mapping.
    """
    score = Decimal("0")
    factors: list[str] = []

    if (
        signals.days_since_portal_login is not None
        and signals.days_since_portal_login > THRESHOLD_DAYS_LOGIN
    ):
        score += Decimal("40")
        factors.append(
            f"days_since_portal_login>{THRESHOLD_DAYS_LOGIN} "
            f"(actual: {signals.days_since_portal_login})"
        )
    if signals.tasks_overdue_count > THRESHOLD_TASKS_OVERDUE:
        score += Decimal("25")
        factors.append(
            f"tasks_overdue>{THRESHOLD_TASKS_OVERDUE} "
            f"(actual: {signals.tasks_overdue_count})"
        )
    if signals.invoices_overdue_count > 0:
        score += Decimal("25")
        factors.append(
            f"invoices_overdue>0 "
            f"(actual: {signals.invoices_overdue_count})"
        )
    if (
        signals.avg_response_time_hours is not None
        and signals.avg_response_time_hours > THRESHOLD_RESPONSE_HOURS
    ):
        score += Decimal("20")
        factors.append(
            f"avg_response_time_hours>{THRESHOLD_RESPONSE_HOURS} "
            f"(actual: {signals.avg_response_time_hours})"
        )
    if (
        signals.nps_last_score is not None
        and signals.nps_last_score < THRESHOLD_NPS_LOW
    ):
        score += Decimal("15")
        factors.append(
            f"nps_last_score<{THRESHOLD_NPS_LOW} "
            f"(actual: {signals.nps_last_score})"
        )
    if (
        signals.renewal_in_days is not None
        and signals.renewal_in_days < THRESHOLD_RENEWAL_NEAR
    ):
        score += Decimal("10")
        factors.append(
            f"renewal_in_days<{THRESHOLD_RENEWAL_NEAR} "
            f"(actual: {signals.renewal_in_days})"
        )

    if score > 100:
        score = Decimal("100")

    if score >= 80:
        risk_level = "critical"
        recommended_action = (
            "Contacto urgente Marcos · agendar check-in directo + "
            "revisar bloqueos · evaluar pause/extender milestones."
        )
    elif score >= 60:
        risk_level = "high"
        recommended_action = (
            "Llamar al cliente esta semana · revisar tareas overdue · "
            "evaluar reasignación tareas internas."
        )
    elif score >= 30:
        risk_level = "medium"
        recommended_action = (
            "Monitorizar próximos 14 días · revisar último contacto + "
            "considerar email proactivo."
        )
    else:
        risk_level = "low"
        recommended_action = (
            "Cliente saludable · mantener cadencia comunicación habitual."
        )

    return ChurnComputation(
        score=score.quantize(Decimal("0.01")),
        risk_level=risk_level,
        factors=factors,
        recommended_action=recommended_action,
    )


class ChurnPredictor:
    """Computa score + persist RetainerHealthSignal per retainer activo.

    Strategy queries:
    - days_since_portal_login: last_login en client_users del cliente
      del proyecto (max).
    - tasks_overdue_count: client_tasks status='pending' due_date < now.
    - invoices_overdue_count: invoices estado_pago != 'paid'
      fecha_vencimiento < now AND project_id matches.
    - avg_response_time_hours: chat_threads.last_admin_response_at -
      last_client_message_at (cross MB-14.5).
    - nps_last_score: NULL si no hay nps_responses table o score
      reciente.
    - renewal_in_days: retainer.next_renewal_date - now.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def gather_signals(
        self,
        *,
        project_id: UUID,
        retainer: RetainerContract,
    ) -> ChurnSignals:
        signals = ChurnSignals()
        now = datetime.now(timezone.utc)

        # last_login from client_users del cliente
        login_row = (await self.db.execute(
            text(
                "SELECT MAX(last_login) FROM client_users "
                "WHERE client_id = :cid AND deleted_at IS NULL"
            ),
            {"cid": str(retainer.client_id)},
        )).first()
        if login_row and login_row[0] is not None:
            delta = now - login_row[0]
            signals.days_since_portal_login = max(0, delta.days)

        # last chat msg client from chat_threads (MB-14.5)
        chat_row = (await self.db.execute(
            text(
                "SELECT MAX(last_client_message_at) FROM chat_threads "
                "WHERE project_id = :pid AND deleted_at IS NULL"
            ),
            {"pid": str(project_id)},
        )).first()
        if chat_row and chat_row[0] is not None:
            delta = now - chat_row[0]
            signals.days_since_chat_msg_client = max(0, delta.days)

        # tasks overdue count (client_tasks MB-14.3)
        tasks_row = (await self.db.execute(
            text(
                "SELECT COUNT(*) FROM client_tasks "
                "WHERE project_id = :pid "
                "AND status = 'pending' "
                "AND due_date < CURRENT_DATE "
                "AND deleted_at IS NULL"
            ),
            {"pid": str(project_id)},
        )).first()
        signals.tasks_overdue_count = int(tasks_row[0] or 0) if tasks_row else 0

        # invoices overdue count (M15)
        invoices_row = (await self.db.execute(
            text(
                "SELECT COUNT(*) FROM invoices "
                "WHERE project_id = :pid "
                "AND (estado_pago IS NULL OR estado_pago != 'paid') "
                "AND fecha_vencimiento IS NOT NULL "
                "AND fecha_vencimiento < CURRENT_DATE "
                "AND deleted_at IS NULL"
            ),
            {"pid": str(project_id)},
        )).first()
        signals.invoices_overdue_count = (
            int(invoices_row[0] or 0) if invoices_row else 0
        )

        # avg response time hours (chat_threads MB-14.5)
        resp_row = (await self.db.execute(
            text(
                "SELECT AVG("
                "EXTRACT(EPOCH FROM "
                "(last_admin_response_at - last_client_message_at)"
                ") / 3600.0) "
                "FROM chat_threads "
                "WHERE project_id = :pid "
                "AND last_admin_response_at IS NOT NULL "
                "AND last_client_message_at IS NOT NULL "
                "AND last_admin_response_at >= last_client_message_at"
            ),
            {"pid": str(project_id)},
        )).first()
        if resp_row and resp_row[0] is not None:
            signals.avg_response_time_hours = (
                Decimal(str(resp_row[0])).quantize(Decimal("0.01"))
            )

        # renewal_in_days
        if retainer.next_renewal_date is not None:
            delta = retainer.next_renewal_date - now.date()
            signals.renewal_in_days = delta.days

        return signals

    async def compute_for_retainer(
        self,
        *,
        retainer: RetainerContract,
    ) -> RetainerHealthSignal:
        if retainer.project_id is None:
            raise ValueError(
                f"Retainer {retainer.id} sin project_id · cannot compute"
            )

        signals = await self.gather_signals(
            project_id=retainer.project_id,
            retainer=retainer,
        )
        computation = compute_churn_score(signals)

        health = RetainerHealthSignal(
            project_id=retainer.project_id,
            retainer_id=retainer.id,
            computed_at=datetime.now(timezone.utc),
            days_since_portal_login=signals.days_since_portal_login,
            days_since_chat_msg_client=signals.days_since_chat_msg_client,
            tasks_overdue_count=signals.tasks_overdue_count,
            invoices_overdue_count=signals.invoices_overdue_count,
            avg_response_time_hours=signals.avg_response_time_hours,
            nps_last_score=signals.nps_last_score,
            renewal_in_days=signals.renewal_in_days,
            churn_risk_score=computation.score,
            risk_level=computation.risk_level,
            primary_risk_factors=computation.factors,
            recommended_action=computation.recommended_action,
        )
        self.db.add(health)
        await self.db.flush()
        await self.db.refresh(health)
        return health

    async def scan_active_retainers(self) -> list[RetainerHealthSignal]:
        """Scan retainers active + compute signal per row.

        Returns lista signals creados (uno por retainer).
        Caller debe haber escalado a fulkro role + commit propio.
        """
        rows = (await self.db.execute(
            text(
                "SELECT id FROM retainer_contracts "
                "WHERE estado = 'active' "
                "AND project_id IS NOT NULL "
                "AND deleted_at IS NULL"
            )
        )).all()
        results: list[RetainerHealthSignal] = []
        for row in rows:
            retainer = await self.db.get(RetainerContract, row[0])
            if retainer is None:
                continue
            try:
                await self.db.execute(
                    text(
                        "SELECT set_config('app.current_project_id', "
                        ":pid, true)"
                    ),
                    {"pid": str(retainer.project_id)},
                )
                signal = await self.compute_for_retainer(retainer=retainer)
                results.append(signal)
            except Exception:
                logger.exception(
                    "compute_for_retainer failed retainer=%s",
                    retainer.id,
                )
        return results


__all__ = [
    "ChurnPredictor",
    "ChurnSignals",
    "ChurnComputation",
    "compute_churn_score",
    "THRESHOLD_DAYS_LOGIN",
    "THRESHOLD_TASKS_OVERDUE",
    "THRESHOLD_RESPONSE_HOURS",
    "THRESHOLD_NPS_LOW",
    "THRESHOLD_RENEWAL_NEAR",
]
