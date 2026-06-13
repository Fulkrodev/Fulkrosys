"""Adaptive dashboard service · SAN-E v3 MB-7 atom 7.1.

Cross-motor data aggregation for /client-portal/dashboard adaptive view:
M21 (client/project) + M01 (categoria) + workflow + M02 (magerit) +
M03 (DdA) + M07 (evidencias) + M19 (risk) + M27 (conformity) +
M23 (retainer) + M29 (mensajeria) + M18 (notificaciones).

Q5.2 + Q5.3 plan v6 estricto: NO role dimension. Cliente todos R/W
full · M30 contactos invisibles cliente (admin-only).

Returns AdaptiveDashboardView con context (tier + phase + archetype +
sector) + today_actions (0-5 priorizadas) + workflow_summary + recent
messages + new docs count + upcoming invoice + notifications.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.workflow_phase import WorkflowPhase


# Ejecutable 8 OLA 0 (#13): orden canónico desde WorkflowPhase (única fuente de
# verdad). Antes esta tupla estaba DRIFTED (magerit/dda/auditoria/retainer_activo)
# vs el enum real (analisis_riesgos/adecuacion/dda_final/...): las fases medias
# recibían acciones vacías y _phase_step devolvía None (la "fase X de Y" del
# cliente quedaba rota). projects.fase usa los valores canónicos.
_PHASE_ORDER: tuple[str, ...] = tuple(p.value for p in WorkflowPhase.ordered())


@dataclass
class AdaptiveAction:
    """Single actionable card for 'Tu trabajo de hoy' zone."""

    id: str
    title: str
    description: str
    href: str
    icon: str
    estimated_minutes: int
    priority: str  # high / medium / low
    requires_step_up: bool = False


@dataclass
class DashboardContext:
    """4-dimensional context: tier + phase + archetype + sector. NO role."""

    client_id: str
    client_name: Optional[str]
    project_id: str
    project_name: Optional[str]
    categoria_objetivo: Optional[str]  # BASICA / MEDIA / ALTA
    current_phase: Optional[str]
    archetype: Optional[str]  # SaaS / Consulting / Hybrid
    sector: Optional[str]
    days_to_certification: Optional[int]
    phase_step: Optional[int]  # 1..10
    phase_total: int = 10


@dataclass
class AdaptiveDashboardView:
    context: DashboardContext
    today_actions: list[AdaptiveAction] = field(default_factory=list)
    workflow_summary: dict = field(default_factory=dict)
    recent_messages: list[dict] = field(default_factory=list)
    new_documents_count: int = 0
    upcoming_invoice: Optional[dict] = None
    notifications_unread: int = 0
    whatsapp_thread_id: Optional[str] = None  # placeholder · MB-8 wire


async def _set_rls_for_client(db: AsyncSession, client_id: uuid.UUID) -> None:
    """SET LOCAL ROLE fulkro_app_bypassrls + set tenant context para RLS."""
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))


async def _fetch_project(
    db: AsyncSession, client_id: uuid.UUID,
) -> Optional[dict]:
    """Latest project for client · returns mapping or None."""
    row = (await db.execute(
        text(
            "SELECT id, nombre, categoria_objetivo, lifecycle_state, "
            "archetype, fecha_objetivo_certificacion, fase, "
            "created_at "
            "FROM projects "
            "WHERE client_id = :cid AND deleted_at IS NULL "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {"cid": str(client_id)},
    )).mappings().first()
    return dict(row) if row else None


async def _fetch_client_info(
    db: AsyncSession, client_id: uuid.UUID,
) -> tuple[Optional[str], Optional[str]]:
    """Return (nombre, sector) for the client."""
    row = (await db.execute(
        text("SELECT nombre, sector FROM clients WHERE id = :cid"),
        {"cid": str(client_id)},
    )).first()
    if not row:
        return None, None
    return row[0], row[1]


def _phase_step(phase: Optional[str]) -> Optional[int]:
    if not phase:
        return None
    try:
        return _PHASE_ORDER.index(phase) + 1
    except ValueError:
        return None


def _days_to_cert(target: Optional[datetime]) -> Optional[int]:
    if not target:
        return None
    now = datetime.now(timezone.utc)
    if target.tzinfo is None:
        target = target.replace(tzinfo=timezone.utc)
    delta = target - now
    return max(0, delta.days)


async def _count_pending_dda_measures(
    db: AsyncSession, project_id: str,
) -> int:
    row = (await db.execute(
        text(
            "SELECT count(*) FROM dda_entries "
            "WHERE project_id = :pid AND deleted_at IS NULL "
            # FIX: 'pendiente'/'en_curso' NO son valores de EstadoImplementacion
            # (no_valorado|no_implantada|parcial|implantada|no_aplica) → la KPI
            # daba SIEMPRE 0. Pendientes = aplicables aún no implantadas.
            "AND estado_implementacion IN ('no_valorado', 'no_implantada', 'parcial')"
        ),
        {"pid": project_id},
    )).first()
    return int(row[0] or 0) if row else 0


async def _count_evidence_pending(
    db: AsyncSession, project_id: str,
) -> int:
    row = (await db.execute(
        text(
            "SELECT count(*) FROM evidence "
            "WHERE project_id = :pid AND deleted_at IS NULL "
            "AND (vigente IS NULL OR vigente = false)"
        ),
        {"pid": project_id},
    )).first()
    return int(row[0] or 0) if row else 0


async def _count_open_risks(db: AsyncSession, project_id: str) -> int:
    row = (await db.execute(
        text(
            "SELECT count(*) FROM project_risks "
            "WHERE project_id = :pid AND deleted_at IS NULL "
            # FIX: el enum de ProjectRisk.status es español (identificado|
            # monitorizado|materializado|cerrado) → los literales ingleses daban
            # SIEMPRE 0. Riesgos abiertos = todo lo que no esté cerrado.
            "AND status IN ('identificado', 'monitorizado', 'materializado')"
        ),
        {"pid": project_id},
    )).first()
    return int(row[0] or 0) if row else 0


async def _count_magerit_assets_pending(
    db: AsyncSession, project_id: str,
) -> int:
    """Count assets pending client review · JOIN magerit_analysis."""
    row = (await db.execute(
        text(
            "SELECT count(*) FROM magerit_assets a "
            "JOIN magerit_analysis ma ON ma.id = a.analysis_id "
            "WHERE ma.project_id = :pid AND a.deleted_at IS NULL "
            "AND (a.client_review_status IS NULL "
            "OR a.client_review_status = 'pending')"
        ),
        {"pid": project_id},
    )).first()
    return int(row[0] or 0) if row else 0


async def _count_recent_documents(
    db: AsyncSession, project_id: str, since_days: int = 7,
) -> int:
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=int(since_days))
    row = (await db.execute(
        text(
            "SELECT count(*) FROM documents "
            "WHERE project_id = :pid AND deleted_at IS NULL "
            "AND created_at > :cutoff"
        ),
        {"pid": project_id, "cutoff": cutoff},
    )).first()
    return int(row[0] or 0) if row else 0


async def _fetch_recent_messages(
    db: AsyncSession, project_id: str, limit: int = 3,
) -> list[dict]:
    rows = (await db.execute(
        text(
            "SELECT id, sender_type, content, created_at "
            "FROM chat_messages "
            "WHERE project_id = :pid AND deleted_at IS NULL "
            "ORDER BY created_at DESC LIMIT :lim"
        ),
        {"pid": project_id, "lim": limit},
    )).mappings().all()
    return [
        {
            "id": str(r["id"]),
            "sender_type": r["sender_type"],
            "preview": (r["content"] or "")[:140],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


async def _count_unread_notifications(
    db: AsyncSession, project_id: str,
) -> int:
    row = (await db.execute(
        text(
            "SELECT count(*) FROM client_notifications "
            "WHERE project_id = :pid AND read_at IS NULL "
            "AND dismissed_at IS NULL"
        ),
        {"pid": project_id},
    )).first()
    return int(row[0] or 0) if row else 0


def _build_today_actions(
    phase: Optional[str],
    *,
    dda_pending: int,
    evidence_pending: int,
    risks_open: int,
    magerit_pending: int,
    categoria: Optional[str] = None,
) -> list[AdaptiveAction]:
    """Build up to 5 actions prioritized by phase + counters.

    Returns empty list if nothing actionable (caller shows celebratoria card).
    """
    actions: list[AdaptiveAction] = []

    if phase == "onboarding":
        actions.append(AdaptiveAction(
            id="onboarding_complete",
            title="Completar onboarding adaptativo",
            description="Te quedan preguntas pendientes en el onboarding",
            href="/client-portal/onboarding",
            icon="ClipboardList",
            estimated_minutes=10,
            priority="high",
        ))
    elif phase == "diagnostico":
        actions.append(AdaptiveAction(
            id="diagnosis_stakeholders",
            title="Confirmar stakeholders identificados",
            description="Revisa los stakeholders y procesos del diagnóstico",
            href="/client-portal/dda",
            icon="Users",
            estimated_minutes=15,
            priority="high",
        ))
    elif phase == "analisis_riesgos" and magerit_pending > 0:
        actions.append(AdaptiveAction(
            id="magerit_validate_assets",
            title=f"Validar {magerit_pending} activos MAGERIT",
            description="Confirma los activos inventariados",
            href="/client-portal/magerit",
            icon="Server",
            estimated_minutes=20,
            priority="high",
        ))
    elif phase in ("adecuacion", "dda_final") and dda_pending > 0:
        actions.append(AdaptiveAction(
            id="dda_review_measures",
            title=f"Revisar {dda_pending} medidas DdA",
            description="Medidas de aplicabilidad pendientes",
            href="/client-portal/dda",
            icon="ListChecks",
            estimated_minutes=25,
            priority="high",
        ))
    elif phase == "implantacion" and evidence_pending > 0:
        actions.append(AdaptiveAction(
            id="implantacion_evidence",
            title=f"Subir {evidence_pending} evidencias",
            description="Evidencias de implantación pendientes",
            href="/client-portal/evidencias",
            icon="Upload",
            estimated_minutes=30,
            priority="high",
        ))
    elif phase == "verificacion":
        # Ejecutable 8 OLA 0 (#14): gate por categoría. BÁSICA es autodeclaración
        # (CCN-STIC 808 · sin pentest, sin ENAC) → mostrar pentest confundía y
        # restaba credibilidad ante el órgano de contratación.
        if (categoria or "").strip().upper() in ("BASICA", "BÁSICA"):
            actions.append(AdaptiveAction(
                id="basica_autoevaluacion_808",
                title="Revisar la autoevaluación (CCN-STIC 808)",
                description=(
                    "Repasa la autoevaluación antes de firmar la Declaración "
                    "de Conformidad"
                ),
                href="/client-portal/conformidad",
                icon="ClipboardCheck",
                estimated_minutes=15,
                priority="high",
            ))
        else:
            actions.append(AdaptiveAction(
                id="verification_pentest",
                title="Autorizar pentest",
                description="Firma autorización de pentest para iniciar verificación",
                href="/client-portal/pentest-authorization",
                icon="Shield",
                estimated_minutes=5,
                priority="high",
                requires_step_up=True,
            ))
    elif phase == "conformidad":
        actions.append(AdaptiveAction(
            id="conformity_sign",
            title="Firmar conformidad ENS final",
            description="Conformidad final pendiente de firma",
            href="/client-portal/conformidad",
            icon="BadgeCheck",
            estimated_minutes=10,
            priority="high",
            requires_step_up=True,
        ))
    elif phase == "retainer_cierre":
        actions.append(AdaptiveAction(
            id="retainer_offer",
            title="Aceptar retainer post-certificación",
            description="Oferta de mantenimiento disponible",
            href="/client-portal/retainer-checkin",
            icon="Repeat",
            estimated_minutes=15,
            priority="medium",
        ))

    if risks_open > 0 and len(actions) < 5:
        actions.append(AdaptiveAction(
            id="risk_review",
            title=f"Revisar {risks_open} riesgos abiertos",
            description="Riesgos pendientes de tratamiento",
            href="/client-portal/dda",
            icon="AlertTriangle",
            estimated_minutes=15,
            priority="medium",
        ))

    if evidence_pending > 0 and phase != "implantacion" and len(actions) < 5:
        actions.append(AdaptiveAction(
            id="evidence_pending",
            title=f"Subir {evidence_pending} evidencias pendientes",
            description="Evidencias pendientes de aportar",
            href="/client-portal/evidencias",
            icon="FileUp",
            estimated_minutes=20,
            priority="medium",
        ))

    return actions[:5]


def _archetype_message(archetype: Optional[str]) -> str:
    if archetype == "saas_only":
        return "Como SaaS Only, enfocaremos proveedores cloud y boundary lógico."
    if archetype == "consulting":
        return "Como Consulting, enfocaremos arquitectura de datos del cliente."
    if archetype == "hybrid":
        return "Como Híbrido, enfocaremos segmentación del boundary."
    return ""


async def get_adaptive_dashboard(
    db: AsyncSession,
    client_id: uuid.UUID,
    client_user_id: uuid.UUID | None = None,
) -> AdaptiveDashboardView:
    """Build the adaptive dashboard view for a client.

    Q5.2 + Q5.3 plan v6: NO role dimension. All users of the client
    see the same view. M30 contactos NEVER surfaced here (admin-only).
    """
    await _set_rls_for_client(db, client_id)

    project = await _fetch_project(db, client_id)
    client_name, client_sector = await _fetch_client_info(db, client_id)

    if not project:
        context = DashboardContext(
            client_id=str(client_id),
            client_name=client_name,
            project_id="",
            project_name=None,
            categoria_objetivo=None,
            current_phase=None,
            archetype=None,
            sector=client_sector,
            days_to_certification=None,
            phase_step=None,
        )
        return AdaptiveDashboardView(context=context)

    project_id = str(project["id"])
    phase = project.get("fase") or project.get("lifecycle_state")
    context = DashboardContext(
        client_id=str(client_id),
        client_name=client_name,
        project_id=project_id,
        project_name=project.get("nombre"),
        categoria_objetivo=project.get("categoria_objetivo"),
        current_phase=phase,
        archetype=project.get("archetype"),
        sector=client_sector,
        days_to_certification=_days_to_cert(
            project.get("fecha_objetivo_certificacion")
        ),
        phase_step=_phase_step(phase),
    )

    dda_pending = await _count_pending_dda_measures(db, project_id)
    evidence_pending = await _count_evidence_pending(db, project_id)
    risks_open = await _count_open_risks(db, project_id)
    magerit_pending = await _count_magerit_assets_pending(db, project_id)
    recent_docs = await _count_recent_documents(db, project_id)
    recent_messages = await _fetch_recent_messages(db, project_id)
    unread = await _count_unread_notifications(db, project_id)

    today_actions = _build_today_actions(
        phase,
        dda_pending=dda_pending,
        evidence_pending=evidence_pending,
        risks_open=risks_open,
        magerit_pending=magerit_pending,
        categoria=project.get("categoria_objetivo"),
    )

    workflow_summary = {
        "phase": phase,
        "phase_step": _phase_step(phase),
        "phase_total": 10,
        "dda_pending": dda_pending,
        "evidence_pending": evidence_pending,
        "risks_open": risks_open,
        "magerit_assets_pending": magerit_pending,
        "archetype_hint": _archetype_message(project.get("archetype")),
    }

    return AdaptiveDashboardView(
        context=context,
        today_actions=today_actions,
        workflow_summary=workflow_summary,
        recent_messages=recent_messages,
        new_documents_count=recent_docs,
        upcoming_invoice=None,
        notifications_unread=unread,
        whatsapp_thread_id=None,
    )
