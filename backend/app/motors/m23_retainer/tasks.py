"""M23 Retainer — tasks programadas (Sprint C5).

Tareas Celery que disparan flujos reactivos del retainer:
- check_overdue_activities: marca actividades vencidas
- update_all_renewal_statuses: actualiza T_MINUS_* / LAPSED
- execute_scheduled_activity: ejecuta una actividad invocando M8/M10/M18
"""
from __future__ import annotations

from loguru import logger

from backend.app.core.celery_app import celery_app


# Mapeo tipo_actividad -> motor/funcion
ACTIVITY_EXECUTORS: dict[str, str] = {
    "vigilancia_vulnerabilidades": "m08_verification.create_run",
    "auditoria_interna": "m10_audit_sim.run_simulation",
    "reporte_trimestral": "m18_communication.quarterly",
    "reporte_anual": "m18_communication.annual",
    "comite_seguridad": "m18_communication.monthly",
    "simulacro_phishing": "m08_verification.create_run",
    "prueba_continuidad": "m09_audit_prep.continuity_drill",
    "revision_privilegios": "m21_diagnosis.privilege_review",
    "revision_proveedores": "m21_diagnosis.vendor_review",
    "revision_ar_dda": "m03_dda.annual_review",
    "formacion_anual": "m16_onboarding.training",
}


@celery_app.task(name="m23.check_overdue_activities")
def check_overdue_activities() -> dict:
    """#35 · Marca actividades vencidas (fecha_programada < hoy, estado
    programada/en_curso → vencida). Scheduled: daily 08:00. Antes stub log-only.
    """
    import asyncio

    from sqlalchemy import text

    from backend.app.database import async_session
    from backend.app.motors.m23_retainer.retainer_service import RetainerService

    async def _run() -> dict:
        async with async_session() as session:
            try:
                # Vista global cross-cliente (regla 13) · bypass RLS.
                await session.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
                svc = RetainerService()
                overdue = await svc.get_overdue_activities(session)
                for a in overdue:
                    a.estado = "vencida"
                await session.flush()
                await session.commit()
                return {"marked": len(overdue)}
            except Exception:
                await session.rollback()
                raise

    try:
        result = asyncio.run(_run())
        logger.info("M23 check_overdue_activities · {} marcadas vencida", result["marked"])
        return {"status": "ok", "motor": "m23", **result}
    except Exception as exc:
        logger.error("M23 check_overdue_activities fatal · {}", exc)
        return {"status": "failed", "motor": "m23", "error": str(exc)}


@celery_app.task(name="m23.update_all_renewal_statuses")
def update_all_renewal_statuses() -> dict:
    """#35 · Recorre retainers activos y actualiza renewal_status
    (T_MINUS_180..30 / LAPSED). Scheduled: daily 07:00. Antes stub log-only.
    """
    import asyncio

    from sqlalchemy import select, text

    from backend.app.database import async_session
    from backend.app.models.retainer import RetainerContract
    from backend.app.motors.m23_retainer.retainer_service import RetainerService

    async def _run() -> dict:
        async with async_session() as session:
            try:
                await session.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
                ids = list((await session.execute(
                    select(RetainerContract.id).where(
                        RetainerContract.estado == "active",
                        RetainerContract.deleted_at.is_(None),
                    )
                )).scalars().all())
                svc = RetainerService()
                by_status: dict[str, int] = {}
                for rid in ids:
                    rc = await svc.update_renewal_status(session, rid)
                    st = rc.renewal_status or "none"
                    by_status[st] = by_status.get(st, 0) + 1
                await session.commit()
                return {"updated": len(ids), "by_status": by_status}
            except Exception:
                await session.rollback()
                raise

    try:
        result = asyncio.run(_run())
        logger.info("M23 update_all_renewal_statuses · {} retainers", result["updated"])
        return {"status": "ok", "motor": "m23", **result}
    except Exception as exc:
        logger.error("M23 update_all_renewal_statuses fatal · {}", exc)
        return {"status": "failed", "motor": "m23", "error": str(exc)}


@celery_app.task(name="m23.execute_scheduled_activity")
def execute_scheduled_activity(activity_id: str) -> dict:
    """Ejecuta una actividad programada · MB-7.bis atom 7.bis.3.

    Wire real RetainerService.execute_scheduled_activity (already
    implements per-tipo branching: vigilancia_vulnerabilidades →
    VerificationService.create_run, auditoria_interna → AuditSimulator,
    reportes → ReportGenerator). Cadences set in CADENCES_BY_PROFILE.

    On-demand · invoked by Celery beat for scheduled retainer activities.
    """
    import asyncio
    import uuid as _uuid

    from backend.app.database import async_session
    from backend.app.motors.m23_retainer.retainer_service import (
        RetainerService,
    )

    async def _run():
        async with async_session() as session:
            try:
                svc = RetainerService()
                result = await svc.execute_activity(
                    session, _uuid.UUID(activity_id),
                )
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise

    try:
        result = asyncio.run(_run())
        logger.info(
            "M23 execute_scheduled_activity · activity={} status={}",
            activity_id, result.get("status"),
        )
        return {"motor": "m23", **result}
    except Exception as exc:
        logger.error(
            "M23 execute_scheduled_activity · {} failed: {}",
            activity_id, exc,
        )
        return {
            "activity_id": activity_id,
            "status": "failed",
            "error": str(exc)[:300],
            "executors_available": list(ACTIVITY_EXECUTORS.keys()),
        }


@celery_app.task(name="m23.dispatch_due_activities")
def dispatch_due_activities() -> dict:
    """Ejecutable 8 OLA 0 (#15) · Encola execute_scheduled_activity por cada
    actividad de retainer DUE.

    Antes: execute_scheduled_activity (por activity_id) existía pero NADA lo
    encolaba → el ciclo de mantenimiento del retainer (anuales/bienales art. 31
    + CCN-STIC 817) era 100% manual. Este dispatcher (beat diario) selecciona las
    actividades en estado 'programada' con fecha_programada <= hoy y las despacha
    una a una vía .delay (cada ejecución corre en su propia task · no bloquea).
    """
    import asyncio
    from datetime import date as _date

    from sqlalchemy import select

    from backend.app.database import async_session
    from backend.app.models.retainer import RetainerActivity

    async def _due_ids() -> list[str]:
        async with async_session() as session:
            rows = await session.execute(
                select(RetainerActivity.id).where(
                    RetainerActivity.estado == "programada",
                    RetainerActivity.fecha_programada <= _date.today(),
                    RetainerActivity.deleted_at.is_(None),
                )
            )
            return [str(r[0]) for r in rows.all()]

    try:
        due = asyncio.run(_due_ids())
    except Exception as exc:
        logger.error("M23 dispatch_due_activities · query failed: {}", exc)
        return {"motor": "m23", "dispatched": 0, "error": str(exc)[:300]}

    dispatched = 0
    for activity_id in due:
        try:
            execute_scheduled_activity.delay(activity_id)
            dispatched += 1
        except Exception as exc:
            logger.error(
                "M23 dispatch · enqueue {} failed: {}", activity_id, exc,
            )
    logger.info(
        "M23 dispatch_due_activities · dispatched {}/{}", dispatched, len(due),
    )
    return {"motor": "m23", "dispatched": dispatched, "due": len(due)}


@celery_app.task(name="m23.generate_monthly_invoices")
def generate_monthly_invoices() -> dict:
    """#31 · Genera factura mensual para todos los retainers activos (M23 -> M15).

    Scheduled: primer dia del mes 04:00 (cron 0 4 1 * *). Antes era stub
    log-only (riesgo de revenue: el retainer no se facturaba sin intervencion
    manual). Ahora invoca el ciclo real run_retainer_billing_cycle (mismo patron
    asyncio.run + async_session + commit que execute_scheduled_activity).
    """
    import asyncio

    from backend.app.database import async_session
    from backend.app.motors.m23_retainer.billing_integration import (
        run_retainer_billing_cycle,
    )

    async def _run() -> dict:
        async with async_session() as session:
            try:
                result = await run_retainer_billing_cycle(session)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise

    try:
        result = asyncio.run(_run())
        logger.info(
            "M23 generate_monthly_invoices · {} retainers · {} facturados",
            result.get("retainers_total", 0),
            len(result.get("generated", [])),
        )
        return {"status": "ok", "motor": "m23", "target": "m15", **result}
    except Exception as exc:
        logger.error("M23 generate_monthly_invoices fatal · {}", exc)
        return {"status": "failed", "motor": "m23", "error": str(exc)}


@celery_app.task(name="m23.renewal_trigger_daily")
def renewal_trigger_daily() -> dict:
    """#35 · Scan diario de renovación bianual: dispara alertas 6m/campañas
    3m/alertas 1m pre-aniversario (18m/21m/23m post-certificación). Scheduled:
    daily 05:00. Cableado al servicio real run_renewal_bianual_check (antes stub).
    """
    import asyncio

    from backend.app.database import async_session
    from backend.app.motors.m27_conformity.renewal_scheduler import (
        run_renewal_bianual_check,
    )

    async def _run() -> dict:
        async with async_session() as session:
            try:
                res = await run_renewal_bianual_check(session)
                await session.commit()
                return {
                    "processed_projects": res.processed_projects,
                    "alerts_6m": len(res.alerts_6m),
                    "campaigns_3m": len(res.campaigns_created_3m),
                    "alerts_1m": len(res.alerts_1m),
                    "errors": len(res.errors),
                }
            except Exception:
                await session.rollback()
                raise

    try:
        result = asyncio.run(_run())
        logger.info(
            "M23 renewal_trigger_daily · {} proyectos · 6m={} 3m={} 1m={}",
            result["processed_projects"], result["alerts_6m"],
            result["campaigns_3m"], result["alerts_1m"],
        )
        return {"status": "ok", "motor": "m23", **result}
    except Exception as exc:
        logger.error("M23 renewal_trigger_daily fatal · {}", exc)
        return {"status": "failed", "motor": "m23", "error": str(exc)}


@celery_app.task(name="m23.agent_26_weekly_analysis")
def agent_26_weekly_analysis() -> dict:
    """#35 · Agente 26 análisis semanal de retainers (4 reglas deterministas:
    overdue · drift crítico · renovación urgente · candidato upgrade). Scheduled:
    lunes 07:00. Cableado a summary_for_marcos (antes stub log-only).
    """
    import asyncio

    from backend.app.database import async_session
    from backend.app.motors.m23_retainer.agent_26 import summary_for_marcos

    async def _run() -> dict:
        async with async_session() as session:
            try:
                summary = await summary_for_marcos(session)
                await session.commit()
                return summary
            except Exception:
                await session.rollback()
                raise

    try:
        summary = asyncio.run(_run())
        logger.info(
            "M23 agent_26_weekly_analysis · {} alertas", summary.get("total_alerts", 0),
        )
        return {"status": "ok", "motor": "m23", "agent": "26", **summary}
    except Exception as exc:
        logger.error("M23 agent_26_weekly_analysis fatal · {}", exc)
        return {"status": "failed", "motor": "m23", "agent": "26", "error": str(exc)}


@celery_app.task(name="m23.generate_quarterly_reports")
def generate_quarterly_reports() -> dict:
    """Atom 4.bis · genera reportes trimestrales para projects con retainer activo.

    Scheduled: 1er dia habil de abril/julio/octubre/enero 09:00.
    Idempotent per (project_id, period_quarter) · usa RetainerCheckinService
    existing.

    Returns:
        {"status": "ok", "generated": N, "skipped": M, "errors": E,
         "period_quarter": "YYYY-QN"}
    """
    import asyncio
    import uuid

    logger.info("M23 atom 4.bis: generating quarterly reports E-801")

    async def _run() -> dict:
        from sqlalchemy import text as sa_text
        from backend.app.database import async_session
        from backend.app.motors.m23_retainer.retainer_checkin_service import (
            NoActiveRetainerError,
            RetainerCheckinService,
            compute_quarter_label,
        )
        from datetime import date

        period_quarter = compute_quarter_label(date.today())
        generated = 0
        skipped = 0
        errors: list[dict] = []

        async with async_session() as db:
            try:
                row = await db.execute(sa_text(
                    "SELECT DISTINCT project_id FROM retainer_contracts "
                    "WHERE estado = 'active' AND deleted_at IS NULL"
                ))
                project_ids = [r[0] for r in row.fetchall()]
            except Exception as exc:
                logger.error(f"M23 atom 4.bis: project scan failed · {exc}")
                return {
                    "status": "scan_failed",
                    "error": str(exc),
                    "period_quarter": period_quarter,
                }

            svc = RetainerCheckinService(db)
            for pid in project_ids:
                try:
                    report = await svc.generate_quarterly_report_draft(
                        project_id=uuid.UUID(str(pid)),
                        period_quarter=period_quarter,
                    )
                    if report.admin_curation_status == "draft":
                        generated += 1
                    else:
                        skipped += 1
                except NoActiveRetainerError:
                    skipped += 1
                except Exception as exc:
                    errors.append({"project_id": str(pid), "error": str(exc)})
                    logger.warning(
                        f"M23 atom 4.bis: project={pid} failed · {exc}"
                    )

            try:
                await db.commit()
            except Exception as exc:
                await db.rollback()
                logger.error(f"M23 atom 4.bis: commit failed · {exc}")
                return {
                    "status": "commit_failed",
                    "error": str(exc),
                    "period_quarter": period_quarter,
                    "generated": generated,
                    "skipped": skipped,
                    "errors": len(errors),
                }

        return {
            "status": "ok",
            "motor": "m23",
            "report_code": "E-801",
            "period_quarter": period_quarter,
            "projects_scanned": len(project_ids),
            "generated": generated,
            "skipped": skipped,
            "errors": len(errors),
            "error_details": errors[:10],
        }

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error(f"M23 atom 4.bis: task fatal · {exc}")
        return {"status": "failed", "motor": "m23", "error": str(exc)}


@celery_app.task(name="m23.generate_annual_reports")
def generate_annual_reports() -> dict:
    """#37 (FRENTE C) · genera informes ANUALES E-802 para projects con retainer
    activo (año anterior). Mismo patrón real que el trimestral (E-801).

    Scheduled: 15 enero 10:00 Europe/Madrid. Idempotente per (project_id, año).
    """
    import asyncio
    import uuid
    from datetime import date

    logger.info("M23 #37: generating annual reports E-802")

    async def _run() -> dict:
        from sqlalchemy import text as sa_text
        from backend.app.database import async_session
        from backend.app.motors.m23_retainer.retainer_checkin_service import (
            NoActiveRetainerError,
            RetainerCheckinService,
        )

        year = date.today().year - 1
        generated = 0
        skipped = 0
        errors: list[dict] = []

        async with async_session() as db:
            try:
                row = await db.execute(sa_text(
                    "SELECT DISTINCT project_id FROM retainer_contracts "
                    "WHERE estado = 'active' AND deleted_at IS NULL"
                ))
                project_ids = [r[0] for r in row.fetchall()]
            except Exception as exc:
                logger.error(f"M23 #37: project scan failed · {exc}")
                return {"status": "scan_failed", "error": str(exc), "year": year}

            svc = RetainerCheckinService(db)
            for pid in project_ids:
                try:
                    report = await svc.generate_annual_report_draft(
                        project_id=uuid.UUID(str(pid)), year=year,
                    )
                    if report.admin_curation_status == "draft":
                        generated += 1
                    else:
                        skipped += 1
                except NoActiveRetainerError:
                    skipped += 1
                except Exception as exc:
                    errors.append({"project_id": str(pid), "error": str(exc)})
                    logger.warning(f"M23 #37: project={pid} failed · {exc}")

            try:
                await db.commit()
            except Exception as exc:
                await db.rollback()
                logger.error(f"M23 #37: commit failed · {exc}")
                return {
                    "status": "commit_failed", "error": str(exc), "year": year,
                    "generated": generated, "skipped": skipped,
                    "errors": len(errors),
                }

        return {
            "status": "ok", "motor": "m23", "report_code": "E-802", "year": year,
            "projects_scanned": len(project_ids), "generated": generated,
            "skipped": skipped, "errors": len(errors), "error_details": errors[:10],
        }

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error(f"M23 #37: task fatal · {exc}")
        return {"status": "failed", "motor": "m23", "error": str(exc)}


@celery_app.task(name="m23.ccn_stic_daily_scrape")
def ccn_stic_daily_scrape() -> dict:
    """A15 Vigilancia Normativa extension · CCN-STIC index scrape (atom 7.bis.2).

    Scheduled: daily 04:00 Europe/Madrid. Respeta robots.txt + rate limit 2s.
    """
    import asyncio

    from backend.app.database import async_session
    from backend.app.motors.m23_retainer.ccn_stic_scraper import (
        scrape_and_persist,
    )

    async def _run():
        async with async_session() as session:
            try:
                result = await scrape_and_persist(session)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise

    try:
        summary = asyncio.run(_run())
        logger.info(
            "M23 CCN-STIC scrape · {} indexed / {} new / {} skipped",
            summary["indexed"], summary["new"], summary["skipped"],
        )
        return {"status": "ok", "motor": "m23", **summary}
    except Exception as exc:
        logger.error("M23 CCN-STIC scrape · task fatal · {}", exc)
        return {"status": "failed", "motor": "m23", "error": str(exc)}


@celery_app.task(name="m31.media_digest_daily")
def media_digest_daily() -> dict:
    """WhatsApp digest diario MEDIA tier · MB-8 closure tier coverage.

    Scheduled: daily 09:00 Europe/Madrid. Itera proyectos MEDIA con
    whatsapp_enabled=True + cliente opted-in · aggregate critical events
    last 24h · send 1 WA digest per project.
    """
    import asyncio

    from backend.app.database import async_session
    from backend.app.notifications.whatsapp_dispatcher import (
        send_media_daily_digest_for_project,
    )
    from sqlalchemy import text as _text

    async def _run():
        sent_count = 0
        skipped = 0
        async with async_session() as session:
            try:
                await session.execute(_text("SET LOCAL ROLE fulkro_app_bypassrls"))
                rows = (await session.execute(_text(
                    "SELECT p.id, cu.id "
                    "FROM projects p "
                    "JOIN client_users cu ON cu.client_id = p.client_id "
                    "WHERE p.categoria_objetivo = 'MEDIA' "
                    "AND p.whatsapp_enabled = true "
                    "AND p.deleted_at IS NULL "
                    "AND cu.whatsapp_opt_in_at IS NOT NULL"
                ))).fetchall()
                for project_id, client_user_id in rows:
                    summary = await send_media_daily_digest_for_project(
                        session,
                        project_id=project_id,
                        client_user_id=client_user_id,
                    )
                    if summary.sent:
                        sent_count += 1
                    else:
                        skipped += 1
                await session.commit()
            except Exception:
                await session.rollback()
                raise
        return sent_count, skipped

    try:
        sent, skipped = asyncio.run(_run())
        logger.info(
            "M31 MEDIA daily digest · sent={} skipped={}",
            sent, skipped,
        )
        return {
            "status": "ok", "motor": "m31",
            "sent": sent, "skipped": skipped,
        }
    except Exception as exc:
        logger.error("M31 MEDIA daily digest fatal · {}", exc)
        return {"status": "failed", "motor": "m31", "error": str(exc)}


@celery_app.task(name="m31.basica_digest_weekly")
def basica_digest_weekly() -> dict:
    """WhatsApp digest semanal BASICA tier · MB-8 atom 8.2 Q5.A+tier.

    Scheduled: Monday 09:00 Europe/Madrid. Itera proyectos BASICA con
    whatsapp_enabled=True + cliente opted-in · aggregate critical events
    last 7 days · send 1 WA digest per project.
    """
    import asyncio

    from backend.app.database import async_session
    from backend.app.notifications.whatsapp_dispatcher import (
        send_basica_digest_for_project,
    )
    from sqlalchemy import text as _text

    async def _run():
        sent_count = 0
        skipped = 0
        async with async_session() as session:
            try:
                await session.execute(_text("SET LOCAL ROLE fulkro_app_bypassrls"))
                rows = (await session.execute(_text(
                    "SELECT p.id, cu.id "
                    "FROM projects p "
                    "JOIN client_users cu ON cu.client_id = p.client_id "
                    "WHERE p.categoria_objetivo = 'BASICA' "
                    "AND p.whatsapp_enabled = true "
                    "AND p.deleted_at IS NULL "
                    "AND cu.whatsapp_opt_in_at IS NOT NULL"
                ))).fetchall()
                for project_id, client_user_id in rows:
                    summary = await send_basica_digest_for_project(
                        session,
                        project_id=project_id,
                        client_user_id=client_user_id,
                    )
                    if summary.sent:
                        sent_count += 1
                    else:
                        skipped += 1
                await session.commit()
            except Exception:
                await session.rollback()
                raise
        return sent_count, skipped

    try:
        sent, skipped = asyncio.run(_run())
        logger.info(
            "M31 BASICA weekly digest · sent={} skipped={}",
            sent, skipped,
        )
        return {
            "status": "ok", "motor": "m31",
            "sent": sent, "skipped": skipped,
        }
    except Exception as exc:
        logger.error("M31 BASICA weekly digest fatal · {}", exc)
        return {"status": "failed", "motor": "m31", "error": str(exc)}


@celery_app.task(name="m23.drift_weekly_compute")
def drift_weekly_compute() -> dict:
    """Drift auto-compute weekly · 10 dims (atom 7.bis.2 Q3.D).

    Scheduled: Monday 06:00 Europe/Madrid. Itera retainers activos +
    invoca DriftComputeService.compute_drift_for_retainer cross-motor.
    """
    import asyncio

    from backend.app.database import async_session
    from backend.app.motors.m23_retainer.drift_compute_service import (
        DriftComputeService,
    )

    async def _run():
        async with async_session() as session:
            try:
                svc = DriftComputeService()
                results = await svc.compute_drift_all_active(session)
                await session.commit()
                return results
            except Exception:
                await session.rollback()
                raise

    try:
        results = asyncio.run(_run())
        total_drifts = sum(r.drifts_registered for r in results)
        logger.info(
            "M23 drift compute · {} retainers · {} drifts registered",
            len(results), total_drifts,
        )
        return {
            "status": "ok",
            "motor": "m23",
            "retainers_computed": len(results),
            "total_drifts_registered": total_drifts,
        }
    except Exception as exc:
        logger.error("M23 drift compute · task fatal · {}", exc)
        return {"status": "failed", "motor": "m23", "error": str(exc)}
