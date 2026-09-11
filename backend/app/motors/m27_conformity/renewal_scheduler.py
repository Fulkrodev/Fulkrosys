"""M27 Renewal bianual auto-trigger (Paso 7 final 7.4).

Celery task diario que evalua fechas de aniversario de certificacion
y dispara 3 alertas + campana + dossier renewal conforme al calendario
18m/21m/23m previo al vencimiento bianual.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.conformity_lifecycle import (
    RenewalCampaignRow,
)
from backend.app.models.core import Project
from backend.app.motors.m27_conformity.bienio import (
    proxima_fecha_bienal,
)

logger = logging.getLogger(__name__)


# Dias antes de aniversario bianual (24 meses = 730 dias)
ALERT_6M_BEFORE_DAYS = 180   # dia 550 desde certificacion -> 6m antes
ALERT_3M_BEFORE_DAYS = 90    # dia 640 -> 3m antes (crear campana)
ALERT_1M_BEFORE_DAYS = 30    # dia 700 -> 1m antes (segunda alerta)
# O1 · ver m27_conformity/bienio.py: el plazo es de ANYOS (art. 31).


@dataclass
class RenewalCheckResult:
    processed_projects: int = 0
    alerts_6m: list[str] = field(default_factory=list)
    campaigns_created_3m: list[str] = field(default_factory=list)
    alerts_1m: list[str] = field(default_factory=list)
    errors: list[dict[str, str]] = field(default_factory=list)
    run_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


async def run_renewal_bianual_check(
    db: AsyncSession,
    *,
    today: date | None = None,
) -> RenewalCheckResult:
    """Evalua todos los proyectos certificados y dispara alertas segun
    el calendario 18m/21m/23m post-certificacion (equivalente a 6m/3m/1m
    pre-aniversario bianual).

    ``today`` se inyecta para fast-forward en tests/demo.
    """
    today = today or date.today()
    result = RenewalCheckResult()

    await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
    try:
        # Proyectos certificados con certified_at != NULL
        projects = (await db.execute(
            select(Project).where(
                Project.certified_at.is_not(None),
                Project.deleted_at.is_(None),
                Project.lifecycle_state.in_(("CERTIFIED", "RETAINER", "ACTIVE")),
            )
        )).scalars().all()
    finally:
        await db.execute(sa_text("RESET ROLE"))

    result.processed_projects = len(projects)

    for project in projects:
        try:
            await _evaluate_one_project(db, project, today, result)
        except Exception as exc:  # pragma: no cover
            logger.exception("renewal check failed for %s", project.id)
            result.errors.append({
                "project_id": str(project.id),
                "error": str(exc),
            })

    return result


async def _evaluate_one_project(
    db: AsyncSession,
    project: Project,
    today: date,
    result: RenewalCheckResult,
) -> None:
    """Evalua 3 checkpoints (6m/3m/1m) para un proyecto."""
    certified_at = project.certified_at
    if not certified_at:
        return

    aniversario = proxima_fecha_bienal(certified_at)
    days_to_aniversario = (aniversario - today).days

    project_id_str = str(project.id)

    # Cruce-de-umbral con guarda de idempotencia por hito (espeja el patrón
    # correcto de m25 lifecycle_paso4 '>= THRESHOLD and not _has_event_for(...)').
    # Antes se disparaba por IGUALDAD EXACTA (== N días) sin elif independiente:
    # si el beat no corría el día exacto (worker caído, deploy), days_to saltaba
    # de 181→179 y el hito se perdía PARA SIEMPRE. Ahora cada hito cruzado pendiente
    # dispara una sola vez (sin elif → varios hitos cruzados disparan cada uno).

    # 6m antes -> alerta Marcos (interna, sin campana todavia). Banda 6m..3m:
    # una vez cruzado el umbral de 3m la acción relevante es la campaña, no la alerta.
    if (
        days_to_aniversario <= ALERT_6M_BEFORE_DAYS
        and days_to_aniversario > ALERT_3M_BEFORE_DAYS
        and not await _campaign_exists(db, project.id, "recertification_bianual")
        and not await _renewal_event_exists(db, project.id, "alert_6m_marcos")
    ):
        await _log_renewal_event(
            db, project_id=project.id, event_type="alert_6m_marcos",
            details={"days_to_aniversario": days_to_aniversario},
        )
        result.alerts_6m.append(project_id_str)

    # 3m antes -> crear campana + dossier renewal. Idempotente vía _get_active_campaign
    # (solo crea si no hay campaña activa). Banda 3m..1m.
    if (
        days_to_aniversario <= ALERT_3M_BEFORE_DAYS
        and days_to_aniversario > ALERT_1M_BEFORE_DAYS
    ):
        existing = await _get_active_campaign(db, project.id)
        if existing is None:
            campaign = await _create_renewal_campaign(db, project, today)
            result.campaigns_created_3m.append(project_id_str)
            # Dossier M9 tipo renewal (best effort - no bloqueante)
            await _try_generate_renewal_dossier(db, project, campaign.id)

    # 1m antes -> segunda alerta Marcos. Guarda de idempotencia explícita.
    if (
        days_to_aniversario <= ALERT_1M_BEFORE_DAYS
        and days_to_aniversario >= 0
        and not await _renewal_event_exists(db, project.id, "alert_1m_marcos")
    ):
        await _log_renewal_event(
            db, project_id=project.id, event_type="alert_1m_marcos",
            details={"days_to_aniversario": days_to_aniversario},
        )
        result.alerts_1m.append(project_id_str)


async def _renewal_event_exists(
    db: AsyncSession, project_id: uuid.UUID, renewal_type: str,
) -> bool:
    """Guarda de idempotencia: ¿ya se registró este hito de renovación?

    Los eventos de renovación viven en project_lifecycle_events con
    event_type='warning_sent' (reutilizado) y se distinguen por
    metadata_jsonb->>'renewal' (e.g. 'alert_6m_marcos'/'alert_1m_marcos').
    """
    from backend.app.models.lifecycle import ProjectLifecycleEvent

    await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
    try:
        res = await db.execute(
            select(ProjectLifecycleEvent.id).where(
                ProjectLifecycleEvent.project_id == project_id,
                ProjectLifecycleEvent.event_type == "warning_sent",
                ProjectLifecycleEvent.metadata_jsonb["renewal"].astext
                == renewal_type,
            ).limit(1)
        )
        return res.scalar_one_or_none() is not None
    finally:
        await db.execute(sa_text("RESET ROLE"))


async def _campaign_exists(
    db: AsyncSession, project_id: uuid.UUID, campaign_type: str,
) -> bool:
    await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
    try:
        res = await db.execute(
            select(RenewalCampaignRow.id).where(
                RenewalCampaignRow.project_id == project_id,
                RenewalCampaignRow.campaign_type == campaign_type,
                RenewalCampaignRow.status.in_(("planned", "in_progress")),
            ).limit(1)
        )
        return res.scalar_one_or_none() is not None
    finally:
        await db.execute(sa_text("RESET ROLE"))


async def _get_active_campaign(
    db: AsyncSession, project_id: uuid.UUID,
) -> RenewalCampaignRow | None:
    await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
    try:
        res = await db.execute(
            select(RenewalCampaignRow).where(
                RenewalCampaignRow.project_id == project_id,
                RenewalCampaignRow.status.in_(("planned", "in_progress")),
            ).order_by(RenewalCampaignRow.created_at.desc().nulls_last()).limit(1)
        )
        return res.scalar_one_or_none()
    finally:
        await db.execute(sa_text("RESET ROLE"))


async def _create_renewal_campaign(
    db: AsyncSession, project: Project, today: date,
) -> RenewalCampaignRow:
    """Crea campana bianual auto-triggered 3m antes."""
    now = datetime.now(timezone.utc)
    aniversario = proxima_fecha_bienal(project.certified_at)
    campaign = RenewalCampaignRow(
        project_id=project.id,
        campaign_type="recertification_bianual",
        scheduled_for=datetime(
            aniversario.year, aniversario.month, aniversario.day,
            tzinfo=timezone.utc,
        ),
        auto_triggered=True,
        status="planned",
        result_jsonb={
            "auto_triggered_at_day_640": True,
            "reason": "3m antes de aniversario bianual",
            "certification_date": project.certified_at.isoformat(),
        },
        created_at=now,
    )
    await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
    try:
        db.add(campaign)
        await db.flush()
    finally:
        await db.execute(sa_text("RESET ROLE"))
    return campaign


async def _try_generate_renewal_dossier(
    db: AsyncSession, project: Project, campaign_id: uuid.UUID,
) -> None:
    """Intenta generar dossier M9 tipo renewal. Best-effort."""
    sp = await db.begin_nested()
    try:
        from backend.app.motors.m09_audit_prep.dossier_generator import (
            generate_dossier, DossierError,
        )
        from backend.app.models.audit_prep import AuditPreparationRun
        res = await db.execute(
            select(AuditPreparationRun).where(
                AuditPreparationRun.project_id == project.id,
            ).order_by(AuditPreparationRun.created_at.desc().nulls_last()).limit(1)
        )
        run = res.scalar_one_or_none()
        if run is None:
            await sp.rollback()
            return
        # Dossier best effort (force=True para renewal sobre estado actual)
        try:
            _ = await generate_dossier(
                db, project_id=project.id, run_id=run.id, force=True,
            )
            # Vincular campaign -> dossier
            await db.execute(sa_text(
                "UPDATE renewal_campaigns SET dossier_run_id = :rid "
                "WHERE id = :cid"
            ), {"rid": str(run.id), "cid": str(campaign_id)})
        except DossierError:
            pass
        await sp.commit()
    except Exception:  # pragma: no cover
        await sp.rollback()


async def _log_renewal_event(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    event_type: str,
    details: dict[str, Any],
) -> None:
    """Registra evento en project_lifecycle_events con event_type warning_sent.

    Reutiliza la tabla de Paso 4 lifecycle porque "warning_sent" ya es
    valor valido en el CHECK constraint y encaja para alertas Marcos.
    """
    from backend.app.models.lifecycle import ProjectLifecycleEvent
    now = datetime.now(timezone.utc)
    event = ProjectLifecycleEvent(
        project_id=project_id,
        event_type="warning_sent",
        event_date=now,
        performed_by="celery",
        metadata_jsonb={"renewal": event_type, **details},
        notification_sent_to=["marcosmata@fulkro.es"],
        created_at=now,
    )
    await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
    try:
        db.add(event)
        await db.flush()
    finally:
        await db.execute(sa_text("RESET ROLE"))
