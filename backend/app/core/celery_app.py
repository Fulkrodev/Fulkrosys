"""FULKRO Celery app + beat schedule.

Sprint C5 — Scheduler transversal. Las tareas programadas disparan los
flujos reactivos de M23 retainer, M26 backup, M07 evidence freshness, etc.

CONFIGURACIÓN REAL (producción):
    Requiere celery[redis]==5.x instalado y Redis corriendo en localhost:6379.
    Iniciar workers:  celery -A backend.app.core.celery_app worker -l info
    Iniciar beat:     celery -A backend.app.core.celery_app beat -l info

COMPORTAMIENTO EN DEV / TESTS:
    Si celery no está instalado, este módulo expone un `celery_app` stub
    con `.task`/`.shared_task` como decoradores identidad, para que
    las tasks.py de cada motor puedan importarse sin error.
"""
from __future__ import annotations

import os
from typing import Any, Callable


def _make_stub():
    """Stub mínimo compatible con la API @task/@shared_task."""
    class _StubApp:
        conf: dict[str, Any] = {}

        def task(self, *args: Any, **kwargs: Any) -> Callable:
            if args and callable(args[0]):
                return args[0]
            def deco(fn: Callable) -> Callable:
                return fn
            return deco

        shared_task = task  # alias

        def send_task(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover
            pass

    stub = _StubApp()
    stub.conf["beat_schedule"] = {}
    stub.conf["timezone"] = "Europe/Madrid"
    return stub


try:
    from celery import Celery
    from celery.schedules import crontab

    _REDIS_URL = os.environ.get("FULKRO_REDIS_URL", "redis://localhost:6379/1")
    _RESULT_URL = os.environ.get("FULKRO_REDIS_RESULT_URL", "redis://localhost:6379/2")

    celery_app = Celery(
        "fulkro",
        broker=_REDIS_URL,
        backend=_RESULT_URL,
        include=[
            "backend.app.motors.m07_evidence.tasks",
            # C#35 (FRENTE C) · reloj deadline notificación CCN-CERT/LUCIA Art.33
            "backend.app.motors.m19_risk.tasks",
            # H#54 (FRENTE H · DEC-5) · reloj deadline notificación AEPD RGPD Art.33 72h
            "backend.app.motors.m18_communication.aepd_tasks",
            "backend.app.motors.m23_retainer.tasks",
            "backend.app.motors.m25_lifecycle.tasks",
            "backend.app.motors.m26_backup.tasks",
            "backend.app.motors.m29_client_messaging.tasks",
            "backend.app.motors.m27_conformity.biannual_alert_task",
            # MB-6 atom 2 · DPC anual anniversary check art.25 RD 311/2022
            "backend.app.motors.m27_conformity.dpc_anual_alert_task",
            # SAN-D MB-16.4 · NotificationOrchestrator dispatch + scan
            # client_inactivity (cosecha CELERY-CLIENT-INACTIVITY MB-14
            # deferred · DECISIONS.md ADR-038 / ADR-039).
            "backend.app.notifications.tasks",
            # SAN-D MB-18.4 · RetainerChurnPredictor scan weekly
            # (ADR-040). Beat: Monday 09:30 Europe/Madrid.
            "backend.app.retainer.tasks",
            # M13 Commercial · CRM pipeline tasks (leads/propuestas/contratos).
            "backend.app.motors.m13_commercial.tasks",
            # SAN-E MB-9.bis atom 9.bis.6 · FULKRO Self-Monitoring System.
            # Daily/weekly/monthly/quarterly compliance checks + alerts.
            "backend.app.motors.m_compliance_monitor.tasks",
            # SAN-E MB-9.bis mini-atom 3 · per-norma compliance reports.
            "backend.app.motors.m_compliance_monitor.norma_tasks",
            # Sub-atom 1.D.X.L v3.12 · Cloud Connectors retainer monitoring
            # · daily diagnosis 04:00 + monthly digest día 1 09:00 ES.
            "backend.app.motors.m_cloud_connectors.tasks",
            # Sesión 3B-2B.8 CLUSTER 2 Phase 2C · Coach proactivo nudges
            # daily 09:15 ES (15 min after client_inactivity scan).
            "backend.app.motors.m11_copiloto.coach_tasks",
        ],
    )

    celery_app.conf.beat_schedule = {
        # M26 Backup: full weekly Sunday 02:00
        # Ejecutable 8 OLA 0 (#15-fix): nombre REGISTRADO (backup.* · las m26 tasks
        # usan @shared_task(name="backup.*")), no el path punteado (NotRegistered).
        # R8 (backup probado mensualmente) depende de que estos beats resuelvan.
        "backup-weekly-full": {
            "task": "backup.run_pgbackrest_full",
            "schedule": crontab(hour=2, minute=0, day_of_week="sunday"),
        },
        # M26 Backup: incremental daily 03:00
        "backup-daily-incremental": {
            "task": "backup.run_pgbackrest_incremental",
            "schedule": crontab(hour=3, minute=0),
        },
        # MB-10 Atom 10.6.C · ADR-043 cement:
        # M26 Backup: verify integrity weekly Sunday 03:00 (post-full backup).
        "backup-verify-integrity-weekly": {
            "task": "backup.verify_integrity",
            "schedule": crontab(hour=3, minute=0, day_of_week="sunday"),
        },
        # M26 Backup: monthly restore test 1st month 04:00 (stub execution ·
        # logs intention for ISMS audit trail · real orchestration DEFER MB-11
        # Hetzner Terraform + Ansible per ADR-043 cement).
        "backup-monthly-restore-test": {
            "task": "backup.monthly_restore_test",
            "schedule": crontab(hour=4, minute=0, day_of_month="1"),
        },
        # M26 Backup: run_dr_drill KEEP MANUAL admin trigger (quarterly admin
        # discretion · prevents accidental scheduled DR · per ADR-043 cement).
        # NO entry beat schedule · trigger via POST /backup/dr-drills.
        # M23 Retainer: check overdue daily 08:00
        # Ejecutable 8 OLA 0 (#15-fix): el "task" DEBE ser el nombre REGISTRADO
        # (las m23 tasks usan @celery_app.task(name="m23.*")), NO el path punteado
        # del módulo: con name= explícito, "backend.app...tasks.X" no está en el
        # registro → NotRegistered y el beat nunca corre. (Bug latente pre-piloto:
        # beat aún no se había arrancado. Mismo defecto en los beats m26/m07 ·
        # FLAGGED para Marcos.)
        "retainer-check-overdue": {
            "task": "m23.check_overdue_activities",
            "schedule": crontab(hour=8, minute=0),
        },
        # M23 Retainer: update renewal clock daily 07:00
        "retainer-renewal-check": {
            "task": "m23.update_all_renewal_statuses",
            "schedule": crontab(hour=7, minute=0),
        },
        # M7 Evidence: freshness check daily 06:00
        "evidence-freshness-check": {
            "task": "m07.check_expiring_evidence",
            "schedule": crontab(hour=6, minute=0),
        },
        # M23 → M15: recurring billing mensual (día 1, 04:00)
        "retainer-monthly-invoices": {
            "task": "m23.generate_monthly_invoices",
            "schedule": crontab(hour=4, minute=0, day_of_month="1"),
        },
        # #30 Ola8 · M23 Retainer: check-in/reporte trimestral E-801. 1er día de
        # Ene/Abr/Jul/Oct 09:00 ES. El task generate_quarterly_reports ya es real
        # (RetainerCheckinService · idempotente per project+quarter) · solo
        # faltaba la entrada en el beat para que se genere solo cada trimestre.
        "retainer-quarterly-reports": {
            "task": "m23.generate_quarterly_reports",
            "schedule": crontab(
                hour=9, minute=0, day_of_month="1", month_of_year="1,4,7,10"
            ),
        },
        # C#35 (FRENTE C) · M19 Risk: reloj Art.33 deadline notificación
        # CCN-CERT/LUCIA. Cada hora (un plazo de 24h exige aviso oportuno) ·
        # escala M18 cuando se acerca/vence un plazo no notificado (idempotente).
        "incident-notification-deadlines": {
            "task": "m19.check_incident_notification_deadlines",
            "schedule": crontab(minute=0),  # cada hora en punto
        },
        # H#54 (FRENTE H · DEC-5) · M18 AEPD: reloj RGPD Art.33 plazo 72h de
        # notificación a la AEPD. Cada hora · escala M18 cuando se acerca/vence
        # un plazo de brecha de datos aún no notificada (idempotente · gemelo C#35).
        "aepd-notification-deadlines": {
            "task": "m18.check_aepd_notification_deadlines",
            "schedule": crontab(minute=0),  # cada hora en punto
        },
        # #37 (FRENTE C) · M23 Retainer: informe ANUAL E-802 (año anterior).
        # 15 enero 10:00 ES. El task generate_annual_reports es real
        # (RetainerCheckinService.generate_annual_report_draft · idempotente per
        # project+año) · mismo patrón que el trimestral.
        "retainer-annual-reports": {
            "task": "m23.generate_annual_reports",
            "schedule": crontab(
                hour=10, minute=0, day_of_month="15", month_of_year="1"
            ),
        },
        # Ejecutable 8 OLA 0 (#15): dispatcher diario del ciclo de retainer ·
        # selecciona actividades 'programada' DUE y encola execute_scheduled_activity.
        # Sin esto el ciclo de mantenimiento (anuales/bienales) no se disparaba solo.
        "retainer-dispatch-due-activities": {
            "task": "m23.dispatch_due_activities",
            "schedule": crontab(hour=7, minute=30),
        },
        # #16 · reloj de renovación bienal ENAC (art. 31) · diario 05:00.
        "retainer-renewal-trigger-daily": {
            "task": "m23.renewal_trigger_daily",
            "schedule": crontab(hour=5, minute=0),
        },
        # #17 · cómputo de drift de las 10 dimensiones (salud ENS del retainer) ·
        # lunes 06:00 + análisis semanal agente 26 · lunes 06:30.
        "retainer-drift-weekly": {
            "task": "m23.drift_weekly_compute",
            "schedule": crontab(hour=6, minute=0, day_of_week="monday"),
        },
        "retainer-agent26-weekly": {
            "task": "m23.agent_26_weekly_analysis",
            "schedule": crontab(hour=6, minute=30, day_of_week="monday"),
        },
        # M25 Paso 4: grace period hitos 150/180/210/240 (diario 04:30)
        "lifecycle-grace-period-check": {
            "task": "m25.lifecycle_grace_period_check",
            "schedule": crontab(hour=4, minute=30),
        },
        # M25 Paso 4: backup ZIP expiration (diario 05:00)
        "lifecycle-backup-expiration-check": {
            "task": "m25.lifecycle_backup_expiration_check",
            "schedule": crontab(hour=5, minute=0),
        },
        # M29 Client Messaging: cleanup attachments expirados (semanal Sunday 04:00)
        "m29-cleanup-expired-attachments": {
            "task": "m29.cleanup_expired_attachments",
            "schedule": crontab(hour=4, minute=0, day_of_week="sunday"),
        },
        # M29 Client Messaging: digest diario admin (08:00 ES si unread > 0)
        "m29-digest-unread-admin": {
            "task": "m29.digest_unread_admin",
            "schedule": crontab(hour=8, minute=0),
        },
        # MB-13.4 · M27 Conformity: alerta auditoría bienal art.31
        # RD 311/2022 con horizonte 90 días (severity warning <90d /
        # critical <30d). Dedup vía metadata_jsonb->audit_schedule_id.
        "m27-biannual-audit-alerts": {
            "task": "m27_conformity.check_biannual_audits_due",
            "schedule": crontab(hour=8, minute=0),
        },
        # MB-6 atom 2 · M27 Conformity DPC anual anniversary check
        # art.25 RD 311/2022 · CCN-STIC 806 · 30 días antes anniversary
        # severity warning <30d / critical <7d · dedup via metadata_jsonb
        # ->anniversary_year. Daily 08:30 (30 min después biannual para
        # evitar solapar carga BD).
        "m27-dpc-anual-anniversaries": {
            "task": "m27_conformity.check_dpc_anual_anniversaries",
            "schedule": crontab(hour=8, minute=30),
        },
        # MB-16.4 · NotificationOrchestrator scan client_inactivity
        # daily 09:00 Europe/Madrid · cosecha deferrable MB-14
        # CELERY-CLIENT-INACTIVITY (ADR-039). Threshold configurable
        # via Settings.client_inactivity_threshold_days (default 14d).
        "notifications-scan-client-inactivity": {
            "task": "notifications.scan_client_inactivity",
            "schedule": crontab(hour=9, minute=0),
        },
        # MB-18.4 · RetainerChurnPredictor weekly scan (ADR-040).
        # Monday 09:30 Europe/Madrid · 30 min después scan
        # client_inactivity para no solapar carga DB.
        "retainer-scan-churn-weekly": {
            "task": "retainer.scan_churn_risk",
            "schedule": crontab(hour=9, minute=30, day_of_week="monday"),
        },
        # MB-9.bis atom 9.bis.6 · FULKRO Self-Monitoring. Daily checks
        # 07:30 Europe/Madrid (antes que retainer/backup batches).
        "compliance-run-daily": {
            "task": "compliance.run_daily",
            "schedule": crontab(hour=7, minute=30),
        },
        # MB-9.bis atom 9.bis.6 · Weekly batch + status report.
        # Monday 08:00 (después de daily run; produce report semanal).
        "compliance-run-weekly": {
            "task": "compliance.run_weekly",
            "schedule": crontab(hour=8, minute=0, day_of_week="monday"),
        },
        # MB-9.bis atom 9.bis.6 · Monthly batch. Día 1 mes 08:30.
        "compliance-run-monthly": {
            "task": "compliance.run_monthly",
            "schedule": crontab(hour=8, minute=30, day_of_month="1"),
        },
        # MB-9.bis atom 9.bis.6 · Quarterly batch. Día 1 de Ene/Abr/Jul/Oct
        # 09:00 Europe/Madrid.
        "compliance-run-quarterly": {
            "task": "compliance.run_quarterly",
            "schedule": crontab(
                hour=9, minute=0, day_of_month="1", month_of_year="1,4,7,10"
            ),
        },
        # Sub-atom 1.D.X.L v3.12 · Cloud Connectors retainer monitoring.
        # Daily 04:00 Europe/Madrid · re-ejecuta gap engine per project con
        # CloudConnector activo (post backup window · pre-business hours).
        "cloud-connectors-daily-diagnosis": {
            "task": "cloud_connectors.daily_diagnosis",
            "schedule": crontab(hour=4, minute=0),
        },
        # Día 1 mes 09:00 Europe/Madrid · genera compliance snapshot per
        # project en fase RETAINER (digest mensual base para M06 auto-send T1).
        "cloud-connectors-monthly-digest": {
            "task": "cloud_connectors.monthly_digest",
            "schedule": crontab(hour=9, minute=0, day_of_month="1"),
        },
        # Sesión 3B-2B.8 CLUSTER 2 Phase 2C · Coach proactivo nudge scan
        # daily 09:15 ES (15 min after notifications.scan_client_inactivity
        # 09:00 · prevents DB load overlap). Pattern #15 cumulative · pure
        # functional compute_pending_nudges + dispatch best-effort.
        "coach-scan-pending-nudges": {
            "task": "m11_copiloto.scan_pending_nudges",
            "schedule": crontab(hour=9, minute=15),
            "options": {"expires": 3600},  # 1h max wait if worker backlog
        },
        # #22 Ola 5 · Push proactivo ADMIN in-app · daily 08:45 ES (antes del
        # scan cliente · no solapa). Avisa a Marcos de proyectos urgent que
        # lleva >72h sin abrir (cooldown 7d · solo urgent · NO email).
        "coach-scan-pending-admin-nudges": {
            "task": "m11_copiloto.scan_pending_admin_nudges",
            "schedule": crontab(hour=8, minute=45),
            "options": {"expires": 3600},
        },
    }

    # MB-9.bis mini-atom 3 · Auto-append per-norma report entries from the
    # plugin registry. Each plugin contributes its own crontab via
    # ``get_scheduler_config()``. Pure side-effect import — registry is
    # populated when ``m_compliance_monitor.normas`` package loads.
    try:
        from backend.app.motors.m_compliance_monitor.norma_tasks import (
            build_beat_entries,
        )
        celery_app.conf.beat_schedule.update(build_beat_entries())
    except Exception as _exc:  # pragma: no cover — registry import failure
        pass
    celery_app.conf.timezone = "Europe/Madrid"
    # Disponibilidad (auditoría 2026-06-07 · "no tumbar el sistema"): límites de
    # tiempo globales para que una tarea colgada (LLM/HTTP/scanner sin respuesta)
    # NO ocupe un slot de worker indefinidamente. m07 ya define sus propios
    # límites por-tarea (25/30s · prevalecen). acks_late + prefetch=1 evitan
    # perder tareas largas al reiniciar el worker.
    celery_app.conf.task_soft_time_limit = int(
        os.environ.get("FULKRO_CELERY_SOFT_TIME_LIMIT", "300")  # 5 min · SoftTimeLimitExceeded
    )
    celery_app.conf.task_time_limit = int(
        os.environ.get("FULKRO_CELERY_TIME_LIMIT", "360")  # 6 min · SIGKILL hard
    )
    celery_app.conf.task_acks_late = True
    celery_app.conf.worker_prefetch_multiplier = 1
    # FIX P3-1: hardening adicional de cola/broker (disponibilidad).
    #  - reject_on_worker_lost: con acks_late, una task matada por time_limit/OOM
    #    se perdería en silencio; re-encolarla evita la pérdida.
    #  - result_expires: no acumular resultados en Redis indefinidamente (1 día).
    #  - broker_connection_retry_on_startup: reconecta si Redis tarda en arrancar.
    #  - worker_max_tasks_per_child: recicla el proceso hijo (mitiga fugas de mem).
    #  - visibility_timeout 600s (> task_time_limit 360s): re-entrega tareas no
    #    ack'd sin solaparse con las que aún corren.
    celery_app.conf.task_reject_on_worker_lost = True
    celery_app.conf.result_expires = 86400
    celery_app.conf.broker_connection_retry_on_startup = True
    celery_app.conf.worker_max_tasks_per_child = 200
    celery_app.conf.broker_transport_options = {"visibility_timeout": 600}

    # FIX P1-10: asyncpg/SQLAlchemy NO son fork-safe. El engine module-level
    # (database.py) se crea en import-time; con el prefork de Celery
    # (--concurrency=N) cada worker hijo HEREDA el mismo engine/pool → conexiones
    # asyncpg COMPARTIDAS entre procesos (errores intermitentes / corrupción).
    # Disponer el pool heredado en cada hijo (close=False: NO cierra las
    # conexiones del padre) fuerza a que cada proceso abra las suyas propias.
    try:
        from celery.signals import worker_process_init

        @worker_process_init.connect
        def _dispose_inherited_engine(**_kwargs):  # pragma: no cover — fork hook
            try:
                from backend.app.database import engine as _eng
                sync_eng = getattr(_eng, "sync_engine", None)
                if sync_eng is not None:
                    sync_eng.dispose(close=False)
                elif hasattr(_eng, "dispose"):
                    _eng.dispose(close=False)
            except Exception:
                pass
    except Exception:  # pragma: no cover — celery.signals no disponible
        pass

    CELERY_AVAILABLE = True
except ImportError:  # pragma: no cover — dev/test sin celery
    celery_app = _make_stub()
    CELERY_AVAILABLE = False


def get_beat_schedule() -> dict:
    """Expone el schedule para inspección/tests sin depender de Celery."""
    if CELERY_AVAILABLE:
        return dict(celery_app.conf.beat_schedule)
    # Schedule estático para inspección (si celery no está):
    return {
        "backup-weekly-full": {"task": "m26.run_pgbackrest_full", "cron": "0 2 * * 0"},
        "backup-daily-incremental": {"task": "m26.run_pgbackrest_incremental", "cron": "0 3 * * *"},
        "backup-verify-integrity-weekly": {"task": "m26.verify_backup_integrity", "cron": "0 3 * * 0"},
        "backup-monthly-restore-test": {"task": "m26.monthly_restore_test", "cron": "0 4 1 * *"},
        "retainer-check-overdue": {"task": "m23.check_overdue_activities", "cron": "0 8 * * *"},
        "retainer-renewal-check": {"task": "m23.update_all_renewal_statuses", "cron": "0 7 * * *"},
        "evidence-freshness-check": {"task": "m07.check_expiring_evidence", "cron": "0 6 * * *"},
        "retainer-monthly-invoices": {"task": "m23.generate_monthly_invoices", "cron": "0 4 1 * *"},
        "lifecycle-grace-period-check": {"task": "m25.lifecycle_grace_period_check", "cron": "30 4 * * *"},
        "lifecycle-backup-expiration-check": {"task": "m25.lifecycle_backup_expiration_check", "cron": "0 5 * * *"},
        "m29-cleanup-expired-attachments": {"task": "m29.cleanup_expired_attachments", "cron": "0 4 * * 0"},
        "m29-digest-unread-admin": {"task": "m29.digest_unread_admin", "cron": "0 8 * * *"},
        "notifications-scan-client-inactivity": {"task": "notifications.scan_client_inactivity", "cron": "0 9 * * *"},
        "retainer-scan-churn-weekly": {"task": "retainer.scan_churn_risk", "cron": "30 9 * * 1"},
        "compliance-run-daily": {"task": "compliance.run_daily", "cron": "30 7 * * *"},
        "compliance-run-weekly": {"task": "compliance.run_weekly", "cron": "0 8 * * 1"},
        "compliance-run-monthly": {"task": "compliance.run_monthly", "cron": "30 8 1 * *"},
        "compliance-run-quarterly": {"task": "compliance.run_quarterly", "cron": "0 9 1 1,4,7,10 *"},
        "cloud-connectors-daily-diagnosis": {"task": "cloud_connectors.daily_diagnosis", "cron": "0 4 * * *"},
        "cloud-connectors-monthly-digest": {"task": "cloud_connectors.monthly_digest", "cron": "0 9 1 * *"},
    }
