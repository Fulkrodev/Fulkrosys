"""M23 Retainer Management Service.

4 perfiles (addendum v2.2 §6.4.6) con cadencias explícitas:
- R_LITE: micro/pyme ≤25 usuarios, B/M simple
- R_STD: pyme 26-150 usuarios, M, base del negocio
- R_PLUS: 150-500 usuarios, multi-sede/cloud, M/A
- R_CRITICAL: A o cambio alto o incidentes, continuidad intensa

Renewal clock (7 estados): null → T_MINUS_180 → T_MINUS_120 → T_MINUS_90
→ T_MINUS_60 → T_MINUS_30 → LAPSED | RENEWED.

Drift detector: 10 dimensiones × 4 severidades.

Dashboard multi-cliente usa SET LOCAL ROLE fulkro_app_bypassrls para bypass RLS
(regla 13: vista global de Marcos sobre todos los clientes).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.core import Client, Project
from backend.app.models.retainer import (
    RetainerActivity,
    RetainerContract,
    RetainerDriftEvent,
)


# ══════════════════ Catálogos por perfil ══════════════════

CADENCES_BY_PROFILE: dict[str, dict[str, dict]] = {
    "R_MICRO": {
        "comite_seguridad": {"frecuencia": "semestral", "meses": [6, 12]},
        "reporte_trimestral": {"frecuencia": "trimestral",
                                "meses": [3, 6, 9, 12]},
        "revision_privilegios": {"frecuencia": "anual", "meses": [10]},
        "revision_proveedores": {"frecuencia": "anual", "meses": [8]},
        "vigilancia_vulnerabilidades": {"frecuencia": "mensual"},
        "simulacro_phishing": {"frecuencia": "anual", "meses": [9]},
        "prueba_continuidad": {"frecuencia": "anual", "meses": [11]},
        "revision_ar_dda": {"frecuencia": "anual", "meses": [7]},
        "formacion_anual": {"frecuencia": "anual", "meses": [5]},
    },
    "R_LITE": {
        "comite_seguridad": {"frecuencia": "semestral", "meses": [6, 12]},
        "reporte_trimestral": {"frecuencia": "trimestral", "meses": [3, 6, 9, 12]},
        "revision_privilegios": {"frecuencia": "semestral", "meses": [6, 12]},
        "revision_proveedores": {"frecuencia": "anual", "meses": [6]},
        "vigilancia_vulnerabilidades": {"frecuencia": "mensual"},
        "simulacro_phishing": {"frecuencia": "anual", "meses": [9]},
        "prueba_continuidad": {"frecuencia": "anual", "meses": [10]},
        "auditoria_interna": {"frecuencia": "anual", "meses": [8]},
        "revision_ar_dda": {"frecuencia": "anual", "meses": [7]},
        "formacion_anual": {"frecuencia": "anual", "meses": [5]},
    },
    "R_STD": {
        "comite_seguridad": {"frecuencia": "trimestral", "meses": [3, 6, 9, 12]},
        "reporte_trimestral": {"frecuencia": "trimestral", "meses": [3, 6, 9, 12]},
        "revision_privilegios": {"frecuencia": "trimestral", "meses": [3, 6, 9, 12]},
        "revision_proveedores": {"frecuencia": "semestral", "meses": [6, 12]},
        "vigilancia_vulnerabilidades": {"frecuencia": "semanal"},
        "simulacro_phishing": {"frecuencia": "semestral", "meses": [5, 11]},
        "prueba_continuidad": {"frecuencia": "anual", "meses": [9]},
        "auditoria_interna": {"frecuencia": "anual", "meses": [7]},
        "revision_ar_dda": {"frecuencia": "anual", "meses": [6]},
        "formacion_anual": {"frecuencia": "anual", "meses": [4]},
    },
    "R_PLUS": {
        "comite_seguridad": {"frecuencia": "mensual"},
        "reporte_trimestral": {"frecuencia": "trimestral", "meses": [3, 6, 9, 12]},
        "revision_privilegios": {"frecuencia": "trimestral", "meses": [3, 6, 9, 12]},
        "revision_proveedores": {"frecuencia": "trimestral", "meses": [3, 6, 9, 12]},
        "vigilancia_vulnerabilidades": {"frecuencia": "semanal"},
        "simulacro_phishing": {"frecuencia": "trimestral", "meses": [3, 6, 9, 12]},
        "prueba_continuidad": {"frecuencia": "anual", "meses": [8]},
        "auditoria_interna": {"frecuencia": "anual", "meses": [6]},
        "revision_ar_dda": {"frecuencia": "anual", "meses": [5]},
        "formacion_anual": {"frecuencia": "anual", "meses": [3]},
    },
    "R_CRITICAL": {
        "comite_seguridad": {"frecuencia": "mensual"},
        "reporte_trimestral": {"frecuencia": "mensual"},
        "revision_privilegios": {"frecuencia": "mensual"},
        "revision_proveedores": {"frecuencia": "trimestral", "meses": [3, 6, 9, 12]},
        "vigilancia_vulnerabilidades": {"frecuencia": "semanal"},
        "simulacro_phishing": {"frecuencia": "trimestral", "meses": [3, 6, 9, 12]},
        "prueba_continuidad": {"frecuencia": "anual", "meses": [7]},
        "auditoria_interna": {"frecuencia": "anual", "meses": [5]},
        "revision_ar_dda": {"frecuencia": "anual", "meses": [4]},
        "formacion_anual": {"frecuencia": "anual", "meses": [2]},
    },
}

SLA_BY_PROFILE: dict[str, int] = {
    "R_MICRO": 120,
    "R_LITE": 72,
    "R_STD": 48,
    "R_PLUS": 24,
    "R_CRITICAL": 8,
}

HOURS_BY_PROFILE: dict[str, float] = {
    "R_MICRO": 12.0,
    "R_LITE": 25.0,
    "R_STD": 40.0,
    "R_PLUS": 80.0,
    "R_CRITICAL": 150.0,
}

# #33 · Mapeo de los 5 tiers TÉCNICOS (cadencia/SLA/horas reales · fuente de
# verdad del negocio) a los 3 tiers COMERCIALES que Marcos usa de cara al cliente
# (R_BÁSICO/R_MEDIO/R_ALTO). NO renombra los técnicos ni toca BD · es solo capa de
# presentación (se inyecta en respuestas/oferta). Decisión Marcos: mantener 5 + mapear.
COMMERCIAL_TIER_LABELS: dict[str, str] = {
    "R_MICRO": "R_BÁSICO",
    "R_LITE": "R_BÁSICO",
    "R_STD": "R_MEDIO",
    "R_PLUS": "R_ALTO",
    "R_CRITICAL": "R_ALTO",
}


def tier_to_commercial(technical_tier: str) -> str:
    """#33 · Label comercial (R_BÁSICO/R_MEDIO/R_ALTO) de un tier técnico.
    Tier desconocido → devuelve el propio valor (degradación elegante)."""
    return COMMERCIAL_TIER_LABELS.get(technical_tier, technical_tier)

VALID_PROFILES = tuple(CADENCES_BY_PROFILE.keys())

DRIFT_DIMENSIONS = (
    "infraestructura", "identidad", "proveedores", "normativa", "overlay",
    "cpstic", "roles", "continuidad", "evidencias", "contratos",
)
DRIFT_SEVERITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
DRIFT_IMPACTS = ("EVIDENCE", "DOCUMENT", "CONTROL", "ROUTE", "AUDIT")

VALID_ACTIVITY_STATES = {
    "programada", "en_curso", "completada", "cancelada", "vencida",
}


class RetainerError(Exception):
    pass


class RetainerService:
    """Gestión de retainers post-certificación."""

    # ═══════════════ LIFECYCLE ═══════════════

    async def create_retainer(
        self,
        db: AsyncSession,
        client_id: uuid.UUID,
        project_id: uuid.UUID,
        perfil: str,
        precio_mensual: float,
        inicio: date,
        fin: date | None = None,
        contract_id: uuid.UUID | None = None,
        next_renewal_date: date | None = None,
        modalidad: str = "mensual",
    ) -> RetainerContract:
        if perfil not in VALID_PROFILES:
            raise RetainerError(
                f"Perfil inválido: {perfil}. Válidos: {sorted(VALID_PROFILES)}"
            )
        contract = RetainerContract(
            client_id=client_id,
            project_id=project_id,
            contract_id=contract_id,
            perfil=perfil,
            modalidad=modalidad,
            precio_mensual=precio_mensual,
            inicio=inicio,
            fin=fin,
            renovacion_automatica=True,
            sla_respuesta_horas=SLA_BY_PROFILE[perfil],
            estado="active",
            next_renewal_date=next_renewal_date,
            renewal_status=None,
            rag_status="green",
            horas_consumidas_total=0.0,
            horas_previstas_anual=HOURS_BY_PROFILE[perfil],
        )
        db.add(contract)
        await db.flush()
        return contract

    async def get_retainer(
        self, db: AsyncSession, retainer_id: uuid.UUID,
    ) -> RetainerContract | None:
        res = await db.execute(
            select(RetainerContract).where(RetainerContract.id == retainer_id)
        )
        return res.scalar_one_or_none()

    async def get_retainer_by_project(
        self, db: AsyncSession, project_id: uuid.UUID,
    ) -> RetainerContract | None:
        res = await db.execute(
            select(RetainerContract).where(RetainerContract.project_id == project_id)
        )
        return res.scalar_one_or_none()

    async def list_retainers(
        self,
        db: AsyncSession,
        estado: str | None = None,
        perfil: str | None = None,
        rag: str | None = None,
    ) -> list[RetainerContract]:
        stmt = select(RetainerContract)
        if estado:
            stmt = stmt.where(RetainerContract.estado == estado)
        if perfil:
            stmt = stmt.where(RetainerContract.perfil == perfil)
        if rag:
            stmt = stmt.where(RetainerContract.rag_status == rag)
        stmt = stmt.order_by(RetainerContract.created_at.desc())
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def update_retainer_profile(
        self,
        db: AsyncSession,
        retainer_id: uuid.UUID,
        new_profile: str,
        reason: str | None = None,
    ) -> RetainerContract:
        if new_profile not in VALID_PROFILES:
            raise RetainerError(
                f"Perfil inválido: {new_profile}. Válidos: {sorted(VALID_PROFILES)}"
            )
        r = await self.get_retainer(db, retainer_id)
        if not r:
            raise RetainerError(f"Retainer {retainer_id} no encontrado")
        r.perfil = new_profile
        r.sla_respuesta_horas = SLA_BY_PROFILE[new_profile]
        r.horas_previstas_anual = HOURS_BY_PROFILE[new_profile]
        await db.flush()
        return r

    async def pause_retainer(
        self, db: AsyncSession, retainer_id: uuid.UUID,
    ) -> RetainerContract:
        r = await self.get_retainer(db, retainer_id)
        if not r:
            raise RetainerError(f"Retainer {retainer_id} no encontrado")
        r.estado = "paused"
        await db.flush()
        return r

    async def cancel_retainer(
        self, db: AsyncSession, retainer_id: uuid.UUID,
    ) -> RetainerContract:
        r = await self.get_retainer(db, retainer_id)
        if not r:
            raise RetainerError(f"Retainer {retainer_id} no encontrado")
        r.estado = "cancelled"
        await db.flush()
        return r

    # ═══════════════ ACTIVITIES ═══════════════

    async def generate_annual_activities(
        self,
        db: AsyncSession,
        retainer_id: uuid.UUID,
        year: int,
    ) -> list[RetainerActivity]:
        r = await self.get_retainer(db, retainer_id)
        if not r:
            raise RetainerError(f"Retainer {retainer_id} no encontrado")
        if not r.perfil or r.perfil not in CADENCES_BY_PROFILE:
            raise RetainerError(f"Perfil inválido: {r.perfil}")

        cadencias = CADENCES_BY_PROFILE[r.perfil]
        created: list[RetainerActivity] = []
        for tipo, cfg in cadencias.items():
            freq = cfg["frecuencia"]
            if freq == "mensual":
                meses = list(range(1, 13))
            elif freq == "semanal":
                # 52 actividades/año — registra 1 por mes como representante
                meses = list(range(1, 13))
            elif freq == "trimestral":
                meses = cfg.get("meses", [3, 6, 9, 12])
            elif freq == "semestral":
                meses = cfg.get("meses", [6, 12])
            elif freq == "anual":
                meses = cfg.get("meses", [6])
            else:
                meses = []

            for mes in meses:
                try:
                    fecha = date(year, mes, 1)
                except ValueError:
                    continue
                activity = RetainerActivity(
                    retainer_contract_id=r.id,
                    project_id=r.project_id,
                    tipo_actividad=tipo,
                    titulo=f"{tipo.replace('_', ' ').title()} ({year}-{mes:02d})",
                    descripcion=f"Actividad {freq} según perfil {r.perfil}",
                    fecha_programada=fecha,
                    estado="programada",
                    horas_estimadas=self._default_hours(tipo),
                    prioridad="normal",
                )
                db.add(activity)
                created.append(activity)

        await db.flush()
        return created

    @staticmethod
    def _default_hours(tipo: str) -> float:
        estimates = {
            "auditoria_interna": 8.0,
            "revision_ar_dda": 6.0,
            "comite_seguridad": 2.0,
            "simulacro_phishing": 3.0,
            "prueba_continuidad": 6.0,
            "revision_privilegios": 2.0,
            "revision_proveedores": 3.0,
            "vigilancia_vulnerabilidades": 1.0,
            "vigilancia_normativa": 1.0,
            "formacion_anual": 4.0,
            "reporte_trimestral": 2.0,
            "reporte_anual": 4.0,
            "revision_topologia_roles": 2.0,
            "revision_overlay": 2.0,
        }
        return estimates.get(tipo, 1.5)

    async def list_activities(
        self,
        db: AsyncSession,
        retainer_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        estado: str | None = None,
        tipo: str | None = None,
        desde: date | None = None,
        hasta: date | None = None,
    ) -> list[RetainerActivity]:
        stmt = select(RetainerActivity)
        if retainer_id:
            stmt = stmt.where(RetainerActivity.retainer_contract_id == retainer_id)
        if project_id:
            stmt = stmt.where(RetainerActivity.project_id == project_id)
        if estado:
            stmt = stmt.where(RetainerActivity.estado == estado)
        if tipo:
            stmt = stmt.where(RetainerActivity.tipo_actividad == tipo)
        if desde:
            stmt = stmt.where(RetainerActivity.fecha_programada >= desde)
        if hasta:
            stmt = stmt.where(RetainerActivity.fecha_programada <= hasta)
        stmt = stmt.order_by(RetainerActivity.fecha_programada.asc().nulls_last())
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def get_activity(
        self, db: AsyncSession, activity_id: uuid.UUID,
    ) -> RetainerActivity | None:
        res = await db.execute(
            select(RetainerActivity).where(RetainerActivity.id == activity_id)
        )
        return res.scalar_one_or_none()

    async def start_activity(
        self, db: AsyncSession, activity_id: uuid.UUID,
    ) -> RetainerActivity:
        a = await self.get_activity(db, activity_id)
        if not a:
            raise RetainerError(f"Activity {activity_id} no encontrada")
        if a.estado not in ("programada", "vencida"):
            raise RetainerError(
                f"Solo actividades programada/vencida pueden iniciarse (actual: {a.estado})"
            )
        a.estado = "en_curso"
        await db.flush()
        return a

    async def complete_activity(
        self,
        db: AsyncSession,
        activity_id: uuid.UUID,
        horas_consumidas: float,
        resultado: str | None = None,
    ) -> RetainerActivity:
        a = await self.get_activity(db, activity_id)
        if not a:
            raise RetainerError(f"Activity {activity_id} no encontrada")
        if a.estado not in ("en_curso", "programada"):
            raise RetainerError(
                f"Solo activas pueden completarse (actual: {a.estado})"
            )
        a.estado = "completada"
        a.fecha_ejecutada = date.today()
        a.horas_consumidas = float(horas_consumidas)
        a.resultado = resultado

        # Sumar al retainer
        r = await self.get_retainer(db, a.retainer_contract_id)
        if r:
            r.horas_consumidas_total = (r.horas_consumidas_total or 0.0) + float(horas_consumidas)
        await db.flush()
        return a

    # ══════════════════ Sprint C5: Activity executor ══════════════════

    # Mapeo tipo_actividad → función ejecutora (lazy imports)
    ACTIVITY_EXECUTORS: dict[str, str] = {
        "vigilancia_vulnerabilidades": "m08_continuous",
        "auditoria_interna": "m10_audit_sim",
        "reporte_trimestral": "m18_quarterly",
        "reporte_anual": "m18_annual",
        "comite_seguridad": "m18_monthly",
        "revision_ar_dda": "m03_dda.annual_review",  # #4 · revisión anual AR/DdA
    }

    async def execute_activity(
        self,
        db: AsyncSession,
        activity_id: uuid.UUID,
    ) -> dict:
        """Ejecuta una actividad programada invocando el motor correspondiente.

        Best-effort: si el motor destino no está disponible, marca la
        activity como `en_curso` y delega ejecución manual a Marcos.
        Usado por el scheduler Celery (m23.execute_scheduled_activity).
        """
        a = await self.get_activity(db, activity_id)
        if not a:
            raise RetainerError(f"Activity {activity_id} no encontrada")
        if a.estado not in ("programada", "vencida"):
            raise RetainerError(
                f"Activity {activity_id} no está programada (estado={a.estado})"
            )

        a.estado = "en_curso"
        await db.flush()

        tipo = a.tipo_actividad or ""
        project_id = a.project_id
        result: dict = {"activity_id": str(activity_id), "tipo": tipo}

        try:
            if tipo == "vigilancia_vulnerabilidades":
                # Dispara un VerificationRun en modo 'internal' para
                # el proyecto. Los runners reales se activan cuando el
                # Checkpoint 4 conecta Celery beat + el orquestador.
                from backend.app.motors.m08_verification.service import (
                    VerificationService,
                )
                svc = VerificationService(db)
                run = await svc.create_run(
                    project_id=project_id,
                    category=(
                        (await db.execute(text(
                            "SELECT categoria_ens FROM projects WHERE id=:pid"
                        ), {"pid": str(project_id)})).scalar()
                        or "BASICO"
                    ),
                    mode="internal",
                    created_by="m23_retainer",
                )
                result["motor"] = "m08_verification"
                result["verification_run_id"] = str(run.id)
                result["output"] = (
                    f"VerificationRun {run.id} creado en modo internal "
                    "para vigilancia continuada."
                )
            elif tipo == "auditoria_interna":
                from backend.app.motors.m10_audit_sim.audit_simulator import (
                    AuditSimulatorService,
                )
                # Categoría por defecto MEDIA (Marcos puede override)
                sim = AuditSimulatorService()
                run = await sim.run_simulation(
                    db, project_id=project_id, categoria="MEDIA",
                )
                result["motor"] = "m10_audit_sim"
                result["audit_run_id"] = str(run.id)
                result["score"] = run.score_global
            elif tipo in ("reporte_trimestral", "reporte_anual", "comite_seguridad"):
                from backend.app.motors.m18_communication.report_generator import (
                    ReportGeneratorService,
                )
                gen = ReportGeneratorService()
                tipo_map = {
                    "reporte_trimestral": "quarterly_direccion",
                    "reporte_anual": "quarterly_direccion",
                    "comite_seguridad": "monthly_comite",
                }
                report = await gen.generate_report(
                    db, project_id=project_id, tipo=tipo_map[tipo],
                )
                result["motor"] = "m18_report"
                result["report_id"] = str(report.id)
            elif tipo == "revision_ar_dda":
                # #4 · revisión anual del AR/DdA (mantenimiento Fase 8)
                from backend.app.motors.m03_dda.service import DdaService

                review = await DdaService(db).annual_review(project_id)
                result["motor"] = "m03_dda"
                result["annual_review_record_id"] = review["annual_review_record_id"]
                result["new_version"] = review["new_version"]
                result["output"] = (
                    f"Revisión anual AR/DdA · v{review['previous_version']}→"
                    f"v{review['new_version']} · pendiente reaprobación Dirección."
                )
            else:
                result["motor"] = "unknown"
                result["message"] = "Tipo no automatizable; requiere ejecución manual"

            # Completar activity tras ejecución exitosa
            await self.complete_activity(
                db, activity_id,
                horas_consumidas=self._default_hours(tipo),
                resultado=f"auto: {result.get('motor', '?')}",
            )
            result["status"] = "completed"
        except Exception as exc:
            result["status"] = "failed"
            result["error"] = str(exc)[:300]
            # Revertir a programada para que Marcos ejecute manual
            a.estado = "programada"
            await db.flush()

        return result

    async def get_overdue_activities(
        self,
        db: AsyncSession,
        retainer_id: uuid.UUID | None = None,
    ) -> list[RetainerActivity]:
        today = date.today()
        stmt = select(RetainerActivity).where(
            RetainerActivity.fecha_programada < today,
            RetainerActivity.estado.in_(("programada", "en_curso")),
        )
        if retainer_id:
            stmt = stmt.where(RetainerActivity.retainer_contract_id == retainer_id)
        stmt = stmt.order_by(RetainerActivity.fecha_programada.asc())
        res = await db.execute(stmt)
        return list(res.scalars().all())

    # ═══════════════ RENEWAL CLOCK ═══════════════

    @staticmethod
    def _renewal_status_from_days(days_to_renewal: int | None) -> str | None:
        if days_to_renewal is None:
            return None
        if days_to_renewal <= 0:
            return "LAPSED"
        if days_to_renewal <= 30:
            return "T_MINUS_30"
        if days_to_renewal <= 60:
            return "T_MINUS_60"
        if days_to_renewal <= 90:
            return "T_MINUS_90"
        if days_to_renewal <= 120:
            return "T_MINUS_120"
        if days_to_renewal <= 180:
            return "T_MINUS_180"
        return None

    async def update_renewal_status(
        self, db: AsyncSession, retainer_id: uuid.UUID,
    ) -> RetainerContract:
        r = await self.get_retainer(db, retainer_id)
        if not r:
            raise RetainerError(f"Retainer {retainer_id} no encontrado")
        if not r.next_renewal_date:
            r.renewal_status = None
            await db.flush()
            return r
        if r.renewal_status == "RENEWED":
            return r
        today = date.today()
        days = (r.next_renewal_date - today).days
        r.renewal_status = self._renewal_status_from_days(days)
        await db.flush()
        return r

    async def mark_renewed(
        self,
        db: AsyncSession,
        retainer_id: uuid.UUID,
        new_renewal_date: date,
    ) -> RetainerContract:
        r = await self.get_retainer(db, retainer_id)
        if not r:
            raise RetainerError(f"Retainer {retainer_id} no encontrado")
        r.renewal_status = "RENEWED"
        r.next_renewal_date = new_renewal_date
        await db.flush()
        return r

    # ═══════════════ DRIFT DETECTOR ═══════════════

    async def register_drift(
        self,
        db: AsyncSession,
        retainer_id: uuid.UUID,
        project_id: uuid.UUID,
        dimension: str,
        descripcion: str,
        severidad: str,
        impacto: str,
    ) -> RetainerDriftEvent:
        if dimension not in DRIFT_DIMENSIONS:
            raise RetainerError(
                f"Dimensión inválida: {dimension}. Válidas: {list(DRIFT_DIMENSIONS)}"
            )
        if severidad not in DRIFT_SEVERITIES:
            raise RetainerError(
                f"Severidad inválida: {severidad}. Válidas: {list(DRIFT_SEVERITIES)}"
            )
        if impacto not in DRIFT_IMPACTS:
            raise RetainerError(
                f"Impacto inválido: {impacto}. Válidos: {list(DRIFT_IMPACTS)}"
            )
        drift = RetainerDriftEvent(
            retainer_contract_id=retainer_id,
            project_id=project_id,
            dimension=dimension,
            descripcion=descripcion,
            severidad=severidad,
            impacto=impacto,
            estado="open",
        )
        db.add(drift)
        await db.flush()

        # CRITICAL → forzar rag_status red inmediatamente
        r = await self.get_retainer(db, retainer_id)
        if r and severidad == "CRITICAL":
            r.rag_status = "red"
            await db.flush()
        return drift

    async def list_drifts(
        self,
        db: AsyncSession,
        retainer_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        estado: str | None = None,
        severidad: str | None = None,
    ) -> list[RetainerDriftEvent]:
        stmt = select(RetainerDriftEvent)
        if retainer_id:
            stmt = stmt.where(RetainerDriftEvent.retainer_contract_id == retainer_id)
        if project_id:
            stmt = stmt.where(RetainerDriftEvent.project_id == project_id)
        if estado:
            stmt = stmt.where(RetainerDriftEvent.estado == estado)
        if severidad:
            stmt = stmt.where(RetainerDriftEvent.severidad == severidad)
        stmt = stmt.order_by(RetainerDriftEvent.created_at.desc())
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def resolve_drift(
        self, db: AsyncSession, drift_id: uuid.UUID,
    ) -> RetainerDriftEvent:
        res = await db.execute(
            select(RetainerDriftEvent).where(RetainerDriftEvent.id == drift_id)
        )
        d = res.scalar_one_or_none()
        if not d:
            raise RetainerError(f"Drift {drift_id} no encontrado")
        d.estado = "resolved"
        d.resuelto_at = datetime.now(timezone.utc)
        await db.flush()
        return d

    # ═══════════════ RAG CALCULATOR ═══════════════

    async def calculate_rag(
        self, db: AsyncSession, retainer_id: uuid.UUID,
    ) -> str:
        r = await self.get_retainer(db, retainer_id)
        if not r:
            raise RetainerError(f"Retainer {retainer_id} no encontrado")

        overdue = await self.get_overdue_activities(db, retainer_id)
        overdue_count = len(overdue)

        drifts_open = await self.list_drifts(db, retainer_id=retainer_id, estado="open")
        crit_count = sum(1 for d in drifts_open if d.severidad == "CRITICAL")
        high_count = sum(1 for d in drifts_open if d.severidad == "HIGH")
        med_count = sum(1 for d in drifts_open if d.severidad == "MEDIUM")

        # RED
        if (
            overdue_count > 2
            or crit_count > 0
            or r.renewal_status == "LAPSED"
        ):
            rag = "red"
        # AMBER
        elif (
            overdue_count >= 1
            or high_count > 0
            or med_count >= 2
            or r.renewal_status in ("T_MINUS_60", "T_MINUS_30")
        ):
            rag = "amber"
        else:
            rag = "green"

        r.rag_status = rag
        await db.flush()
        return rag

    # ═══════════════ DASHBOARD MULTI-CLIENTE ═══════════════

    async def get_dashboard(self, db: AsyncSession) -> dict[str, Any]:
        """Dashboard multi-cliente para Marcos (regla 13 — sin RLS).

        Usa SET LOCAL ROLE fulkro_app_bypassrls para bypass de RLS en esta transacción.
        """
        # Bypass RLS
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            retainers = list((await db.execute(
                select(RetainerContract).where(
                    RetainerContract.estado != "cancelled",
                )
            )).scalars().all())

            # Pre-cargar clientes y proyectos
            client_map: dict[uuid.UUID, Client] = {}
            project_map: dict[uuid.UUID, Project] = {}
            if retainers:
                client_ids = list({r.client_id for r in retainers if r.client_id})
                project_ids = list({r.project_id for r in retainers if r.project_id})
                if client_ids:
                    clients = (await db.execute(
                        select(Client).where(Client.id.in_(client_ids))
                    )).scalars().all()
                    client_map = {c.id: c for c in clients}
                if project_ids:
                    projects = (await db.execute(
                        select(Project).where(Project.id.in_(project_ids))
                    )).scalars().all()
                    project_map = {p.id: p for p in projects}

            today = date.today()
            clients_out: list[dict] = []
            green = amber = red = 0
            mes_actividades = 0
            mes_horas = 0.0
            mes_eur = 0.0

            for r in retainers:
                rag = r.rag_status or "green"
                if rag == "green":
                    green += 1
                elif rag == "amber":
                    amber += 1
                elif rag == "red":
                    red += 1

                # Próxima actividad
                next_act = (await db.execute(
                    select(RetainerActivity).where(
                        RetainerActivity.retainer_contract_id == r.id,
                        RetainerActivity.estado == "programada",
                        RetainerActivity.fecha_programada >= today,
                    ).order_by(RetainerActivity.fecha_programada.asc()).limit(1)
                )).scalar_one_or_none()

                # Actividades del mes en curso
                mes_start = today.replace(day=1)
                next_month = (mes_start.replace(day=28) + timedelta(days=4)).replace(day=1)
                mes_acts = (await db.execute(
                    select(RetainerActivity).where(
                        RetainerActivity.retainer_contract_id == r.id,
                        RetainerActivity.fecha_programada >= mes_start,
                        RetainerActivity.fecha_programada < next_month,
                    )
                )).scalars().all()
                mes_activities_count = len(mes_acts)
                mes_horas_tenant = sum(float(a.horas_estimadas or 0) for a in mes_acts)
                mes_actividades += mes_activities_count
                mes_horas += mes_horas_tenant
                mes_eur += float(r.precio_mensual or 0)

                client = client_map.get(r.client_id) if r.client_id else None
                project = project_map.get(r.project_id) if r.project_id else None

                clients_out.append({
                    "retainer_id": str(r.id),
                    "client_id": str(r.client_id) if r.client_id else None,
                    "client_nombre": client.nombre if client else None,
                    "client_sector": client.sector if client else None,
                    "project_id": str(r.project_id) if r.project_id else None,
                    "project_nombre": project.nombre if project else None,
                    "perfil": r.perfil,
                    "rag": rag,
                    "estado": r.estado,
                    "mrr": float(r.precio_mensual or 0),
                    "renewal_status": r.renewal_status,
                    "next_renewal_date": r.next_renewal_date.isoformat() if r.next_renewal_date else None,
                    "horas_consumidas_total": float(r.horas_consumidas_total or 0),
                    "horas_previstas_anual": float(r.horas_previstas_anual or 0),
                    "proxima_actividad": {
                        "tipo": next_act.tipo_actividad,
                        "fecha": next_act.fecha_programada.isoformat() if next_act.fecha_programada else None,
                        "countdown_dias": (next_act.fecha_programada - today).days if next_act.fecha_programada else None,
                    } if next_act else None,
                })

            return {
                "total_clientes": len(retainers),
                "green": green,
                "amber": amber,
                "red": red,
                "clientes": clients_out,
                "mes_actual": {
                    "actividades": mes_actividades,
                    "horas_estimadas": round(mes_horas, 1),
                    "eur_a_facturar": round(mes_eur, 2),
                },
            }
        finally:
            await db.execute(text("RESET ROLE"))

    async def list_all_retainers_admin(
        self,
        db: AsyncSession,
        estado: str | None = None,
        perfil: str | None = None,
        rag: str | None = None,
    ) -> list[RetainerContract]:
        """Listado global sin RLS (regla 13)."""
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            return await self.list_retainers(db, estado=estado, perfil=perfil, rag=rag)
        finally:
            await db.execute(text("RESET ROLE"))

    # ══════════════════ GAP 2: Recurring billing M23 → M15 ══════════════════

    async def generate_monthly_invoice(
        self,
        db: AsyncSession,
        retainer_id: uuid.UUID,
    ) -> dict:
        """Genera factura mensual para un retainer activo.

        Invoca M15 BillingService con concepto "Retainer {perfil} — {mes año}",
        1 línea con precio_mensual. Best-effort: devuelve error si retainer
        inactivo, precio=0, o falta project_id.
        """
        r = await self.get_retainer(db, retainer_id)
        if not r:
            raise RetainerError(f"Retainer {retainer_id} no encontrado")
        if r.estado != "active":
            raise RetainerError(
                f"Retainer {retainer_id} no está activo (estado={r.estado})"
            )
        if not r.precio_mensual or float(r.precio_mensual) <= 0:
            raise RetainerError(
                f"Retainer {retainer_id} sin precio_mensual válido"
            )
        if not r.project_id or not r.client_id:
            raise RetainerError(
                f"Retainer {retainer_id} sin project_id/client_id"
            )

        from backend.app.motors.m15_billing.billing_service import BillingService

        today = date.today()
        mes_nombre = today.strftime("%B %Y")
        billing = BillingService()
        invoice = await billing.generate_invoice(
            db,
            client_id=r.client_id,
            project_id=r.project_id,
            contract_id=r.contract_id,
            concepto=f"Retainer {r.perfil} — {mes_nombre}",
            lineas=[{
                "descripcion": f"Servicio retainer {r.perfil} ({mes_nombre})",
                "cantidad": 1,
                "precio_unitario": float(r.precio_mensual),
                "hito_asociado": "retainer_mensual",
            }],
            hito_asociado="retainer_mensual",
        )
        return {
            "invoice_id": str(invoice.id),
            "numero_correlativo": invoice.numero_correlativo,
            "total": float(invoice.total) if invoice.total else 0.0,
            "retainer_id": str(r.id),
            "perfil": r.perfil,
            "periodo": mes_nombre,
        }

    async def generate_monthly_invoices_for_all(
        self,
        db: AsyncSession,
    ) -> dict:
        """Invoca generate_monthly_invoice para todos los retainers activos.

        Usado por el scheduler mensual (m23.generate_monthly_invoices).
        Bypass RLS para ver todos los retainers (admin-level).
        """
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            retainers = await self.list_retainers(db, estado="active")
        finally:
            await db.execute(text("RESET ROLE"))

        results = []
        errors = []
        for r in retainers:
            try:
                inv = await self.generate_monthly_invoice(db, r.id)
                results.append(inv)
            except Exception as exc:
                errors.append({
                    "retainer_id": str(r.id),
                    "error": str(exc)[:200],
                })
        return {
            "total_retainers": len(retainers),
            "invoices_created": len(results),
            "errors": errors,
            "results": results,
        }
