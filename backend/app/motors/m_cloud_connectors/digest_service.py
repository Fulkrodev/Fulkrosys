"""Digest service · monthly compliance snapshot per project (1.D.X.VERIFY 2a).

Extract de Celery task wrapper · ahora invocable manualmente:
  - Celery beat (`cloud_connectors.monthly_digest` día 1 mes 09:00 ES)
  - Admin manual (POST /admin/projects/{id}/cloud-monitoring/digest/generate)

R1 sostener · pipeline 100% determinístico SQL aggregate · NO LLM.
ADR-025 sostener · reuse CloudGap existing · 1 tabla nueva (digest_snapshots)
solo para historic trend MoM (commit 2b cliente).
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import desc, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit_log import AuditLog
from backend.app.motors.m_cloud_connectors.models import (
    CloudDigestSnapshot,
    CloudGap,
)


logger = logging.getLogger(__name__)


class DigestError(Exception):
    """Error genérico digest service."""


class DigestProjectNotFoundError(DigestError):
    """Project no existe o está deleted."""


def _compute_compliance_score(counts_by_severity: dict[str, int]) -> int:
    """Score 0-100 deterministic: 100 - critical*10 - high*5 - medium*2 - low*1.

    Pure function · testeable directamente sin DB.
    """
    return max(0,
        100
        - counts_by_severity.get("critical", 0) * 10
        - counts_by_severity.get("high", 0) * 5
        - counts_by_severity.get("medium", 0) * 2
        - counts_by_severity.get("low", 0) * 1,
    )


async def _aggregate_gap_counts(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict[str, int]:
    """SQL aggregate open gaps by severity · pure SQL · 0 LLM."""
    res = await db.execute(
        select(CloudGap.severity, text("COUNT(*) AS cnt"))
        .where(
            CloudGap.project_id == project_id,
            CloudGap.resolved_at.is_(None),
        )
        .group_by(CloudGap.severity)
    )
    return {row[0]: row[1] for row in res.all()}


async def _project_exists(
    db: AsyncSession, project_id: uuid.UUID,
) -> bool:
    res = await db.execute(
        text(
            "SELECT 1 FROM projects WHERE id = :pid AND deleted_at IS NULL"
        ),
        {"pid": str(project_id)},
    )
    return res.scalar() is not None


async def _emit_audit_log(
    db: AsyncSession,
    *,
    snapshot_id: uuid.UUID,
    triggered_by: str,
    user_id: Optional[uuid.UUID],
    project_id: uuid.UUID,
    compliance_score: int,
) -> None:
    """Append audit_log entry · hash chain integrity for ENS trazabilidad."""
    # audit_log.accion is VARCHAR(20) · short codes:
    # · digest_manual_adm = admin pulsó botón "Generar ahora" (max 20 chars)
    # · digest_celery     = Celery beat scheduled monthly
    accion = (
        "digest_manual_adm"
        if triggered_by == "admin_manual"
        else "digest_celery"
    )
    payload = {
        "project_id": str(project_id),
        "triggered_by": triggered_by,
        "compliance_score": compliance_score,
        "user_id": str(user_id) if user_id else None,
    }
    db.add(AuditLog(
        tabla="cloud_digest_snapshots",
        registro_id=snapshot_id,
        accion=accion,
        usuario=str(user_id) if user_id else "system",
        payload_new=payload,
    ))
    await db.flush()


async def generate_monthly_digest_for_project(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    triggered_by: str = "celery_monthly",
    triggered_by_user_id: Optional[uuid.UUID] = None,
) -> CloudDigestSnapshot:
    """Genera digest snapshot · persiste + audit_log + devuelve record.

    triggered_by valores válidos:
      - 'celery_monthly' · cron día 1 mes 09:00 ES
      - 'admin_manual' · admin pulsa botón "Generar ahora" en UI

    Raises:
        DigestProjectNotFoundError si project no existe.
    """
    if not await _project_exists(db, project_id):
        raise DigestProjectNotFoundError(
            f"Project {project_id} no existe o está deleted",
        )

    counts = await _aggregate_gap_counts(db, project_id)
    total = sum(counts.values())
    score = _compute_compliance_score(counts)

    snapshot_payload: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "compliance_score": score,
        "open_gaps_total": total,
        "open_gaps_by_severity": counts,
        "triggered_by": triggered_by,
    }

    # Set generated_at explícito en Python (microsecond precision) en lugar de
    # server_default now() transaccional · evita timestamps duplicados cuando
    # 2 generaciones ocurren en mismo transaction (tests + back-to-back manual
    # admin triggers · order DESC determinístico).
    snapshot = CloudDigestSnapshot(
        project_id=project_id,
        generated_at=datetime.now(timezone.utc),
        triggered_by=triggered_by,
        triggered_by_user_id=triggered_by_user_id,
        compliance_score=score,
        open_gaps_total=total,
        open_gaps_by_severity=counts,
        snapshot_jsonb=snapshot_payload,
    )
    db.add(snapshot)
    await db.flush()
    await db.refresh(snapshot)

    # Audit log entry · trazabilidad ENAC (RD 311/2022)
    await _emit_audit_log(
        db,
        snapshot_id=snapshot.id,
        triggered_by=triggered_by,
        user_id=triggered_by_user_id,
        project_id=project_id,
        compliance_score=score,
    )

    # Notification trigger · reuse 1.D.G.F NotificationOrchestrator pattern
    # (1.D.X.VERIFY 2b). Best-effort · NO bloquea snapshot creation si falla.
    try:
        await _notify_clients_digest_available(
            db,
            project_id=project_id,
            snapshot_id=snapshot.id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "digest notification failed (project=%s · snapshot=%s) · %s",
            project_id, snapshot.id, exc,
        )

    return snapshot


async def _notify_clients_digest_available(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    snapshot_id: uuid.UUID,
) -> None:
    """Emite ClientNotification per ClientUser del project (R29 friendly).

    Reuse m21_portal_cliente.notification_service.emit_client_notification
    (pattern 1.D.G.F existing). Type 'report_available' (VALID_TYPES m21).
    Best-effort · graceful degradation si ClientUser model lookup falla.
    """
    from sqlalchemy import select

    from backend.app.models.client_portal import ClientUser
    from backend.app.motors.m21_portal_cliente.notification_service import (
        emit_client_notification,
    )

    # Lookup ClientUser via project.client_id
    project_row = (await db.execute(
        text(
            "SELECT client_id FROM projects "
            "WHERE id = :pid AND deleted_at IS NULL"
        ),
        {"pid": str(project_id)},
    )).fetchone()
    if not project_row:
        return
    client_id = project_row[0]

    users_q = await db.execute(
        select(ClientUser).where(
            ClientUser.client_id == client_id,
            ClientUser.deactivated_at.is_(None),
        )
    )
    users = list(users_q.scalars().all())
    if not users:
        return

    title = "📊 Tu resumen mensual está listo"
    body = (
        "Marcos revisó tu sistema este mes · echa un vistazo al resumen "
        "cuando quieras. Sin prisa por tu lado."
    )
    target_url = "/client-portal/retainer-checkin"

    for user in users:
        try:
            await emit_client_notification(
                db,
                project_id=project_id,
                client_user_id=user.id,
                type="report_available",
                title=title,
                body=body,
                target_url=target_url,
                priority="normal",
                emitted_by_motor="m_cloud_connectors",
                payload={
                    "digest_snapshot_id": str(snapshot_id),
                    "source": "monthly_digest",
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "notification emit failed for user %s · %s", user.id, exc,
            )


async def get_latest_digest_for_project(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> Optional[CloudDigestSnapshot]:
    """Devuelve último snapshot por generated_at DESC (o None si nunca generado)."""
    res = await db.execute(
        select(CloudDigestSnapshot)
        .where(CloudDigestSnapshot.project_id == project_id)
        .order_by(desc(CloudDigestSnapshot.generated_at))
        .limit(1)
    )
    return res.scalar_one_or_none()


def build_client_digest_view(
    latest: Optional["CloudDigestSnapshot"],
    previous: Optional["CloudDigestSnapshot"],
    *,
    consultant_name: str = "Marcos",
) -> dict[str, Any]:
    """Construye ClientDigestView · FILTRADO R29 friendly · sin leak admin.

    Pure function · testeable sin DB · 0 LLM.

    Reglas trend (R29 sin rojo alarmante):
      - mejora (score sube) → emoji ↑ · color verde
      - igual (score ±2 puntos) → emoji ≈ · color ámbar
      - baja (score baja) → emoji ↓ · color naranja_suave (NUNCA rojo)
      - primer_resumen (sin previous) → emoji ✨ · color neutral

    NO incluye: triggered_by_user_id, raw snapshot_jsonb, severity breakdown,
    triggered_by internal codes, error details · todo eso queda admin-only.
    """
    if latest is None:
        return {
            "has_snapshot": False,
            "compliance_score": 100,
            "trend_label": "primer_resumen",
            "trend_emoji": "✨",
            "trend_color_hint": "neutral",
            "last_review_at": None,
            "changes_reviewed_count": 0,
            "consultant_name": consultant_name,
            "summary_friendly": (
                "Tu primer resumen mensual estará listo pronto. "
                "Marcos lo revisará y te avisará cuando esté disponible."
            ),
        }

    if previous is None:
        trend_label = "primer_resumen"
        trend_emoji = "✨"
        trend_color_hint = "neutral"
    else:
        delta = latest.compliance_score - previous.compliance_score
        if delta > 2:
            trend_label = "mejora"
            trend_emoji = "↑"
            trend_color_hint = "verde"
        elif delta < -2:
            # Color suave · NUNCA rojo (R29 sin presión)
            trend_label = "baja"
            trend_emoji = "↓"
            trend_color_hint = "naranja_suave"
        else:
            trend_label = "igual"
            trend_emoji = "≈"
            trend_color_hint = "ambar"

    summary_friendly = _build_summary_friendly_text(
        score=latest.compliance_score,
        trend_label=trend_label,
        changes_reviewed=latest.open_gaps_total,
        consultant_name=consultant_name,
    )

    return {
        "has_snapshot": True,
        "compliance_score": latest.compliance_score,
        "trend_label": trend_label,
        "trend_emoji": trend_emoji,
        "trend_color_hint": trend_color_hint,
        "last_review_at": latest.generated_at,
        "changes_reviewed_count": latest.open_gaps_total,
        "consultant_name": consultant_name,
        "summary_friendly": summary_friendly,
    }


def _build_summary_friendly_text(
    *,
    score: int,
    trend_label: str,
    changes_reviewed: int,
    consultant_name: str,
) -> str:
    """Genera texto breve R29 · pure function · sin jerga ENS · sin presión.

    Mensajes deliberadamente positivos · NO mencionan "compliance" técnico ni
    severidad de gaps · solo "elementos revisados" + tono celebración.
    """
    if changes_reviewed == 0:
        return (
            f"{consultant_name} ha revisado tu sistema este mes · "
            "todo en orden."
        )
    if trend_label == "mejora":
        return (
            f"{consultant_name} revisó {changes_reviewed} elemento(s) "
            "este mes · vamos mejorando."
        )
    if trend_label == "baja":
        return (
            f"{consultant_name} revisó {changes_reviewed} elemento(s) "
            "este mes · podemos comentarlos en la próxima reunión."
        )
    return (
        f"{consultant_name} revisó {changes_reviewed} elemento(s) "
        "este mes."
    )


async def get_previous_digest_for_project(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    before_id: Optional[uuid.UUID] = None,
) -> Optional[CloudDigestSnapshot]:
    """Devuelve snapshot ANTERIOR al actual (para Trend MoM commit 2b cliente).

    Si before_id provisto · devuelve el snapshot inmediatamente anterior a ese.
    Si None · devuelve el penúltimo (índice 2 ordered DESC).
    """
    stmt = (
        select(CloudDigestSnapshot)
        .where(CloudDigestSnapshot.project_id == project_id)
        .order_by(desc(CloudDigestSnapshot.generated_at))
    )
    if before_id is None:
        stmt = stmt.offset(1).limit(1)
    else:
        # Need a 2-step: get target's timestamp first
        target_q = await db.execute(
            select(CloudDigestSnapshot.generated_at)
            .where(CloudDigestSnapshot.id == before_id)
        )
        target_ts = target_q.scalar()
        if target_ts is None:
            return None
        stmt = stmt.where(
            CloudDigestSnapshot.generated_at < target_ts,
        ).limit(1)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()
