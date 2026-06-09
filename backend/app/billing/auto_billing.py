"""AutoBillingService · trigger workflow milestone-completion (MB-18.2 ADR-040).

Workflow:

    autoservice = AutoBillingService(db)

    # Tras completar fase X:
    outcomes = await autoservice.handle_phase_completion(
        project_id=project.id,
        completed_phase_index=4,
    )
    # Returns: [BillMilestoneOutcome per milestone billed]

    # Marcos marca paid manual:
    paid = await autoservice.mark_milestone_paid(
        milestone_id=milestone.id,
        by_user_id=marcos.id,
        payment_reference="REF-12345",
    )
    # → workflow advance projects.fase si milestone.blocking_next_phase

Política conservadora:
- ``BillingService.generate_invoice`` puede fallar (tenant context · IVA
  cálculo · etc) · captura excepción per-milestone para no abortar resto.
- Notificaciones via ``NotificationOrchestrator`` (MB-16) y AlertService
  (MB-13.4) son best-effort · fallo NO debe bloquear flujo billing.
- Workflow advance: UPDATE simple ``projects.fase`` (NO transition_to_phase
  callable inexistente · DEC-MB18-WORKFLOW-TRANSITION-CALLABLE).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.billing.manual_transfer import ManualTransferProvider
from backend.app.core.workflow_phase import WorkflowPhase
from backend.app.models.billing_milestones import ContractMilestone
from backend.app.models.commercial import Invoice
from backend.app.motors.m15_billing.billing_service import (
    BillingError,
    BillingService,
)
from backend.app.motors.m18_communication.alert_service import AlertService
from backend.app.notifications import NotificationOrchestrator
from backend.app.notifications.deep_links import DeepLinkGenerator

logger = logging.getLogger(__name__)


class AutoBillingError(Exception):
    """Error genérico AutoBillingService."""


@dataclass
class BillMilestoneOutcome:
    milestone_id: UUID
    milestone_name: str
    status: str  # "billed" | "failed" | "skipped"
    invoice_id: UUID | None = None
    invoice_number: str | None = None
    amount_eur: str | None = None
    error: str | None = None


class AutoBillingService:
    """Auto-bill milestone-completion + mark paid workflow advance."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        billing_service: BillingService | None = None,
        transfer_provider: ManualTransferProvider | None = None,
        orchestrator: NotificationOrchestrator | None = None,
        alert_service: AlertService | None = None,
        deep_links: DeepLinkGenerator | None = None,
    ):
        self.db = db
        self._billing = billing_service or BillingService()
        self._transfer = transfer_provider or ManualTransferProvider()
        self._orchestrator = orchestrator or NotificationOrchestrator(db)
        self._alerts = alert_service or AlertService(db)
        self._deep_links = deep_links or DeepLinkGenerator()

    async def handle_phase_completion(
        self,
        *,
        project_id: UUID,
        completed_phase_index: int,
    ) -> list[BillMilestoneOutcome]:
        """Auto-bill milestones eligible para fase recién completada."""
        result = await self.db.execute(
            select(ContractMilestone).where(
                ContractMilestone.project_id == project_id,
                ContractMilestone.workflow_phase_index == completed_phase_index,
                ContractMilestone.billing_trigger == "phase_complete",
                ContractMilestone.status == "pending",
                ContractMilestone.auto_billing_enabled.is_(True),
                ContractMilestone.deleted_at.is_(None),
            )
        )
        milestones = result.scalars().all()
        if not milestones:
            logger.info(
                "handle_phase_completion project=%s phase=%d · 0 milestones eligible",
                project_id, completed_phase_index,
            )
            return []

        outcomes: list[BillMilestoneOutcome] = []
        for m in milestones:
            outcome = await self._bill_milestone(m)
            outcomes.append(outcome)
        return outcomes

    async def _bill_milestone(
        self, milestone: ContractMilestone,
    ) -> BillMilestoneOutcome:
        try:
            client_id = await self._resolve_client_id(milestone.project_id)
            if client_id is None:
                raise AutoBillingError(
                    f"project {milestone.project_id} sin client_id"
                )

            concept = (
                f"Hito {milestone.milestone_index + 1}: {milestone.milestone_name}"
            )
            lineas: list[dict[str, Any]] = [{
                "descripcion": concept,
                "cantidad": Decimal("1"),
                "precio_unitario": milestone.amount_eur,
                "hito_asociado": milestone.milestone_name,
            }]
            invoice = await self._billing.generate_invoice(
                self.db,
                client_id=client_id,
                project_id=milestone.project_id,
                contract_id=milestone.contract_id,
                concepto=concept,
                lineas=lineas,
                tipo="ordinaria",
                iva_percent=float(milestone.vat_percent),
                hito_asociado=milestone.milestone_name,
            )
        except (BillingError, AutoBillingError) as exc:
            logger.exception(
                "AutoBilling _bill_milestone failed milestone=%s",
                milestone.id,
            )
            return BillMilestoneOutcome(
                milestone_id=milestone.id,
                milestone_name=milestone.milestone_name,
                status="failed",
                error=str(exc)[:500],
            )

        milestone.status = "invoice_issued"
        milestone.billed_at = datetime.now(timezone.utc)
        milestone.invoice_id = invoice.id
        await self.db.flush()

        await self._notify_milestone_billed(milestone, invoice)
        await self._alert_marcos_milestone_billed(milestone, invoice)

        return BillMilestoneOutcome(
            milestone_id=milestone.id,
            milestone_name=milestone.milestone_name,
            status="billed",
            invoice_id=invoice.id,
            invoice_number=invoice.numero_correlativo,
            amount_eur=str(milestone.amount_eur),
        )

    async def mark_milestone_paid(
        self,
        *,
        milestone_id: UUID,
        by_user_id: UUID | None = None,
        payment_reference: str | None = None,
        payment_notes: str | None = None,
        paid_at: datetime | None = None,
    ) -> ContractMilestone:
        """Marca milestone paid + workflow advance si blocking + notify."""
        milestone = await self.db.get(ContractMilestone, milestone_id)
        if milestone is None:
            raise AutoBillingError(f"Milestone {milestone_id} not found")
        if milestone.status == "paid":
            logger.info(
                "mark_milestone_paid milestone=%s already paid · skip",
                milestone_id,
            )
            return milestone

        milestone.status = "paid"
        milestone.paid_at = paid_at or datetime.now(timezone.utc)
        milestone.paid_marked_by_user_id = by_user_id
        milestone.payment_reference = payment_reference
        milestone.payment_notes = payment_notes
        await self.db.flush()

        if milestone.invoice_id is not None:
            await self.db.execute(
                update(Invoice)
                .where(Invoice.id == milestone.invoice_id)
                .values(estado_pago="paid")
            )

        await self._notify_payment_received(milestone)

        if milestone.blocking_next_phase:
            await self._advance_workflow_phase(
                project_id=milestone.project_id,
                target_phase_index=milestone.workflow_phase_index + 1,
            )

        return milestone

    async def _advance_workflow_phase(
        self,
        *,
        project_id: UUID,
        target_phase_index: int,
    ) -> None:
        """UPDATE simple projects.fase si target válido (DEC-MB18-WORKFLOW-
        TRANSITION-CALLABLE).

        NO dispatch signal · NO trigger downstream motors · adopta
        enfoque pragmático MB-18 simplificado. Refactor callable
        centralizado diferido MB-19+.
        """
        ordered = WorkflowPhase.ordered()
        if target_phase_index < 0 or target_phase_index >= len(ordered):
            logger.info(
                "advance_workflow_phase target=%d out of range · skip",
                target_phase_index,
            )
            return
        next_phase = ordered[target_phase_index].value
        try:
            old_row = await self.db.execute(
                text("SELECT fase FROM projects WHERE id = :pid"),
                {"pid": str(project_id)},
            )
            old_phase = old_row.scalar_one_or_none()
            await self.db.execute(
                text(
                    "UPDATE projects SET fase = :phase, updated_at = NOW() "
                    "WHERE id = :pid"
                ),
                {"phase": next_phase, "pid": str(project_id)},
            )
            await self.db.flush()
            logger.info(
                "workflow phase advanced project=%s → %s",
                project_id, next_phase,
            )
            # SSE realtime (auditoría 2026-06-07): el UPDATE raw NO dispara el listener
            # ORM (dashboard_events._on_project_update) → los portales no se enteraban
            # del avance de fase por pago hasta el siguiente refetch (30s). Emitimos
            # explícito · best-effort (un fallo SSE NO debe abortar el flujo billing).
            if old_phase != next_phase:
                try:
                    from backend.app.core.sse_dispatcher import sse_dispatcher
                    await sse_dispatcher.dispatch(
                        channel=f"project:{project_id}",
                        event_type="phase_changed",
                        data={
                            "project_id": str(project_id),
                            "old_phase": old_phase,
                            "new_phase": next_phase,
                        },
                    )
                except Exception:
                    logger.exception("SSE phase_changed dispatch failed (best-effort)")
        except Exception:
            logger.exception(
                "advance_workflow_phase failed project=%s target=%s",
                project_id, next_phase,
            )

    async def _resolve_client_id(self, project_id: UUID) -> UUID | None:
        row = (await self.db.execute(
            text("SELECT client_id FROM projects WHERE id = :pid"),
            {"pid": str(project_id)},
        )).first()
        return row[0] if row else None

    async def _notify_milestone_billed(
        self,
        milestone: ContractMilestone,
        invoice: Invoice,
    ) -> None:
        try:
            from backend.app.notifications.motor_adapters import (
                notify_milestone_billed,
            )
        except ImportError:
            logger.debug(
                "notify_milestone_billed adapter not available · skip notify"
            )
            return

        try:
            recipients = await self._resolve_client_user_recipients(
                milestone.project_id
            )
            project_name = await self._resolve_project_name(milestone.project_id)
            payment_due_str: str | None = None
            if invoice.fecha_vencimiento is not None:
                payment_due_str = invoice.fecha_vencimiento.isoformat()

            for recipient in recipients:
                await notify_milestone_billed(
                    self.db,
                    recipient_user_id=recipient["id"],
                    recipient_email=recipient["email"],
                    recipient_name=recipient["name"],
                    project_id=milestone.project_id,
                    project_name=project_name,
                    invoice_id=invoice.id,
                    invoice_number=invoice.numero_correlativo or "",
                    milestone_index=milestone.milestone_index,
                    milestone_name=milestone.milestone_name,
                    amount_eur=milestone.amount_eur,
                    payment_due_date=payment_due_str,
                )
        except Exception:
            logger.exception(
                "notify_milestone_billed failed milestone=%s",
                milestone.id,
            )

    async def _notify_payment_received(
        self, milestone: ContractMilestone,
    ) -> None:
        try:
            from backend.app.notifications.motor_adapters import (
                notify_payment_received,
            )
        except ImportError:
            return
        try:
            recipients = await self._resolve_client_user_recipients(
                milestone.project_id
            )
            project_name = await self._resolve_project_name(milestone.project_id)
            for recipient in recipients:
                await notify_payment_received(
                    self.db,
                    recipient_user_id=recipient["id"],
                    recipient_email=recipient["email"],
                    recipient_name=recipient["name"],
                    project_id=milestone.project_id,
                    project_name=project_name,
                    milestone_name=milestone.milestone_name,
                    amount_eur=milestone.amount_eur,
                )
        except Exception:
            logger.exception(
                "notify_payment_received failed milestone=%s",
                milestone.id,
            )

    async def _alert_marcos_milestone_billed(
        self,
        milestone: ContractMilestone,
        invoice: Invoice,
    ) -> None:
        try:
            await self._alerts.trigger_alert(
                project_id=milestone.project_id,
                severity="info",
                category="contract_milestone",
                title=(
                    f"Hito facturado: {milestone.milestone_name} · "
                    f"{milestone.amount_eur} €"
                ),
                description=(
                    f"Factura {invoice.numero_correlativo} emitida "
                    f"automáticamente · esperando transferencia."
                ),
                action_url=self._deep_links._build(
                    "/admin/finance/pending-payments"
                ),
                triggered_by="auto_billing",
                metadata={
                    "milestone_id": str(milestone.id),
                    "invoice_id": str(invoice.id),
                    "amount_eur": str(milestone.amount_eur),
                },
            )
        except Exception:
            logger.exception(
                "alert_milestone_billed failed milestone=%s",
                milestone.id,
            )

    async def _resolve_client_user_recipients(
        self, project_id: UUID,
    ) -> list[dict[str, Any]]:
        """Resuelve client_users del proyecto para notificación.

        Estrategia: client_users que pertenecen al cliente del proyecto
        (vía join projects.client_id → client_users.client_id). Filtra
        deleted_at IS NULL.
        """
        result = await self.db.execute(
            text(
                "SELECT cu.id, cu.email, COALESCE(cu.full_name, cu.email) AS name "
                "FROM client_users cu "
                "JOIN projects p ON p.client_id = cu.client_id "
                "WHERE p.id = :pid AND cu.deleted_at IS NULL"
            ),
            {"pid": str(project_id)},
        )
        return [
            {"id": row[0], "email": row[1], "name": row[2]}
            for row in result.all()
        ]

    async def _resolve_project_name(self, project_id: UUID) -> str:
        row = (await self.db.execute(
            text("SELECT nombre FROM projects WHERE id = :pid"),
            {"pid": str(project_id)},
        )).first()
        return row[0] if row else "tu proyecto"


__all__ = [
    "AutoBillingService",
    "AutoBillingError",
    "BillMilestoneOutcome",
]
