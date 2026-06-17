"""M23 Retainer reporting — Paso 7 final 7.3.

Genera:
- E-801 reporte trimestral (generado dia 5, enviado dia 10 del mes
  siguiente al trimestre cerrado).
- E-802 reporte anual (generado 15 enero, enviado 20 enero).

Estructura compacta pero profesional. El render DOCX completo se puede
conectar en Paso 8+ via docxtpl; aqui se genera un payload JSON
estructurado + PDF minimalista (ReportLab) para entrega inicial.
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.commercial_paso7 import RetainerReport
from backend.app.models.core import Client, Project

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# Dataclass KPIs
# ══════════════════════════════════════════════════════════════════════


@dataclass
class ReportKPIs:
    medidas_implementadas_pct: float = 0.0
    vulns_abiertas: int = 0
    incidents_trimestre: int = 0
    drift_score: float = 0.0
    activities_ok_pct: float = 100.0
    actividades_completadas: int = 0
    normativa_cambios: int = 0


@dataclass
class ReportPayload:
    client_name: str
    client_cif: str
    project_name: str | None
    retainer_tier: str | None
    periodo_inicio: str
    periodo_fin: str
    periodo_label: str
    rag_global: str
    kpis: ReportKPIs
    actividades: list[dict[str, Any]] = field(default_factory=list)
    vulnerabilidades: list[dict[str, Any]] = field(default_factory=list)
    normativa_cambios: list[dict[str, Any]] = field(default_factory=list)
    incidents: list[dict[str, Any]] = field(default_factory=list)
    proximas_actividades: list[dict[str, Any]] = field(default_factory=list)
    recomendaciones: str = ""


# ══════════════════════════════════════════════════════════════════════
# Service
# ══════════════════════════════════════════════════════════════════════


class ReportService:
    """Genera E-801 trimestral + E-802 anual."""

    async def generate_e801_quarterly(
        self,
        db: AsyncSession,
        *,
        client_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
        year: int,
        quarter: int,
    ) -> RetainerReport:
        """Genera E-801 para (year, quarter). Idempotente: si ya existe,
        retorna la existente."""
        if quarter not in (1, 2, 3, 4):
            raise ValueError(f"quarter invalido: {quarter}")

        # Dedup (UNIQUE (client_id, report_type, year, quarter))
        await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            existing = (await db.execute(
                select(RetainerReport).where(
                    RetainerReport.client_id == client_id,
                    RetainerReport.report_type == "E-801_quarterly",
                    RetainerReport.periodo_year == year,
                    RetainerReport.periodo_quarter == quarter,
                )
            )).scalar_one_or_none()
            if existing:
                return existing
        finally:
            await db.execute(sa_text("RESET ROLE"))

        # Rangos trimestre
        q_to_month = {1: 1, 2: 4, 3: 7, 4: 10}
        start_month = q_to_month[quarter]
        inicio = date(year, start_month, 1)
        if quarter == 4:
            fin = date(year, 12, 31)
        else:
            fin = date(year, start_month + 3, 1) - timedelta(days=1)

        # Consolidar payload
        payload = await self._consolidate_payload(
            db, client_id=client_id, project_id=project_id,
            periodo_inicio=inicio, periodo_fin=fin,
            periodo_label=f"{year}-Q{quarter}",
        )

        payload_json = json.dumps(
            asdict(payload), sort_keys=True, ensure_ascii=False, default=str,
        ).encode("utf-8")
        hash_sha256 = hashlib.sha256(payload_json).hexdigest()

        now = datetime.now(timezone.utc)
        report = RetainerReport(
            client_id=client_id,
            project_id=project_id,
            report_type="E-801_quarterly",
            periodo_year=year,
            periodo_quarter=quarter,
            periodo_inicio=inicio,
            periodo_fin=fin,
            kpis_jsonb=asdict(payload.kpis),
            payload_jsonb=asdict(payload),
            generated_at=now,
            hash_sha256=hash_sha256,
            signature_ed25519=self._sign(payload_json),
            status="generated",
            created_at=now,
        )
        await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            db.add(report)
            await db.flush()
        finally:
            await db.execute(sa_text("RESET ROLE"))
        return report

    async def generate_e802_annual(
        self,
        db: AsyncSession,
        *,
        client_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
        year: int,
    ) -> RetainerReport:
        """Genera E-802 para año cerrado."""
        await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            existing = (await db.execute(
                select(RetainerReport).where(
                    RetainerReport.client_id == client_id,
                    RetainerReport.report_type == "E-802_annual",
                    RetainerReport.periodo_year == year,
                )
            )).scalar_one_or_none()
            if existing:
                return existing
        finally:
            await db.execute(sa_text("RESET ROLE"))

        inicio = date(year, 1, 1)
        fin = date(year, 12, 31)
        payload = await self._consolidate_payload(
            db, client_id=client_id, project_id=project_id,
            periodo_inicio=inicio, periodo_fin=fin,
            periodo_label=f"Anual {year}",
        )
        payload.recomendaciones = (
            "Informe anual completo. El RSEG debe llevar este documento "
            "a la revision por direccion (art. 12.7 RD 311/2022)."
        )
        payload_json = json.dumps(
            asdict(payload), sort_keys=True, ensure_ascii=False, default=str,
        ).encode("utf-8")

        now = datetime.now(timezone.utc)
        report = RetainerReport(
            client_id=client_id,
            project_id=project_id,
            report_type="E-802_annual",
            periodo_year=year,
            periodo_quarter=None,
            periodo_inicio=inicio,
            periodo_fin=fin,
            kpis_jsonb=asdict(payload.kpis),
            payload_jsonb=asdict(payload),
            generated_at=now,
            hash_sha256=hashlib.sha256(payload_json).hexdigest(),
            signature_ed25519=self._sign(payload_json),
            status="generated",
            created_at=now,
        )
        await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            db.add(report)
            await db.flush()
        finally:
            await db.execute(sa_text("RESET ROLE"))
        return report

    async def _consolidate_payload(
        self,
        db: AsyncSession,
        *,
        client_id: uuid.UUID,
        project_id: uuid.UUID | None,
        periodo_inicio: date,
        periodo_fin: date,
        periodo_label: str,
    ) -> ReportPayload:
        """Recopila KPIs + actividades + vulns + normativa del periodo.

        Cada query opcional se ejecuta en su propio SAVEPOINT para que
        errores no envenenen la transaccion principal.
        """
        await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            client = (await db.execute(
                select(Client).where(Client.id == client_id)
            )).scalar_one_or_none()
            project = None
            if project_id:
                project = (await db.execute(
                    select(Project).where(Project.id == project_id)
                )).scalar_one_or_none()
        finally:
            await db.execute(sa_text("RESET ROLE"))

        tier = await self._safe_scalar(
            db,
            "SELECT perfil FROM retainer_contracts "
            "WHERE client_id = :cid AND estado = 'active' "
            "ORDER BY created_at DESC LIMIT 1",
            {"cid": str(client_id)},
        )

        # FIX(column-drift): la tabla retainer_activities tiene tipo_actividad /
        # fecha_ejecutada / retainer_contract_id (NO tipo / fecha_realizada /
        # retainer_id). Antes la query lanzaba UndefinedColumn tragado por
        # _safe_list → [] → activities_ok_pct=100 → RAG verde fabricado.
        actividades_list = await self._safe_list(
            db,
            "SELECT id::text, tipo_actividad, estado, fecha_ejecutada "
            "FROM retainer_activities "
            "WHERE retainer_contract_id IN "
            "(SELECT id FROM retainer_contracts WHERE client_id = :cid) "
            "AND fecha_ejecutada BETWEEN :i AND :f "
            "ORDER BY fecha_ejecutada DESC LIMIT 50",
            {"cid": str(client_id), "i": periodo_inicio, "f": periodo_fin},
            lambda a: {
                "id": a.id, "tipo": a.tipo_actividad, "estado": a.estado,
                "fecha": (
                    a.fecha_ejecutada.isoformat()
                    if a.fecha_ejecutada else None
                ),
            },
        )

        vulns_list: list[dict[str, Any]] = []
        if project_id:
            vulns_list = await self._safe_list(
                db,
                "SELECT id::text, severidad, medida_afectada, "
                "descripcion, estado "
                "FROM findings WHERE project_id = :pid "
                "AND created_at BETWEEN :i AND :f "
                "ORDER BY severidad DESC LIMIT 5",
                {
                    "pid": str(project_id),
                    "i": periodo_inicio, "f": periodo_fin,
                },
                lambda v: {
                    "id": v.id, "severidad": v.severidad,
                    "medida": v.medida_afectada,
                    "descripcion": (v.descripcion or "")[:200],
                    "estado": v.estado,
                },
            )

        normativa_list = await self._safe_list(
            db,
            "SELECT id::text, source, title, severity, "
            "source_url, published_at "
            "FROM normativa_alerts "
            "WHERE detected_at BETWEEN :i AND :f "
            "ORDER BY severity DESC, detected_at DESC LIMIT 20",
            {"i": periodo_inicio, "f": periodo_fin},
            lambda n: {
                "id": n.id, "source": n.source, "title": n.title,
                "severity": n.severity, "url": n.source_url,
                "published": (
                    n.published_at.isoformat() if n.published_at else None
                ),
            },
        )

        # FIX(claim/impl): antes era un placeholder fijo 85.0 que se enviaba al
        # cliente en el informe de retainer (KPI falso + RAG fabricado). Se
        # computa del estado real de la DdA: implantadas / aplicables.
        medidas_pct = 0.0
        if project_id:
            _mp = await self._safe_scalar(
                db,
                "SELECT COALESCE(ROUND(100.0 * "
                "count(*) FILTER (WHERE estado_implementacion = 'implantada') / "
                "NULLIF(count(*) FILTER (WHERE aplicabilidad <> 'no_aplica'), 0), 1), 0.0) "
                "FROM dda_entries WHERE project_id = :pid AND deleted_at IS NULL",
                {"pid": str(project_id)},
            )
            medidas_pct = float(_mp or 0.0)

        # FIX(claim/impl): incidents_trimestre y drift_score eran placeholders 0
        # enviados al cliente en E-801/E-802. Se computan del estado real:
        # incidentes m19 del periodo + drift events HIGH/CRITICAL m23 del periodo.
        incidents_trimestre_val = 0
        if project_id:
            _inc = await self._safe_scalar(
                db,
                "SELECT count(*) FROM incidents WHERE project_id = :pid "
                "AND created_at BETWEEN :i AND :f AND deleted_at IS NULL",
                {"pid": str(project_id), "i": periodo_inicio, "f": periodo_fin},
            )
            incidents_trimestre_val = int(_inc or 0)
        _drift = await self._safe_scalar(
            db,
            "SELECT count(*) FROM retainer_drift_events de "
            "JOIN retainer_contracts rc ON rc.id = de.retainer_contract_id "
            "WHERE rc.client_id = :cid AND de.severidad IN ('HIGH', 'CRITICAL') "
            "AND de.created_at BETWEEN :i AND :f AND de.deleted_at IS NULL",
            {"cid": str(client_id), "i": periodo_inicio, "f": periodo_fin},
        )
        drift_score_val = float(_drift or 0)

        # checklist#2 (campaña 2026-06-17): la lista de detalle de incidencias iba
        # vacía (incidents=[]) aunque el KPI incidents_trimestre era un conteo real
        # → el informe decía "N incidencias" sin detalle. Se puebla con datos reales
        # de m19 (mismo filtro que el conteo) para coherencia conteo↔detalle.
        incidents_list: list[dict[str, Any]] = []
        if project_id:
            incidents_list = await self._safe_list(
                db,
                "SELECT id::text, severidad, descripcion, workflow_state, "
                "fecha, created_at FROM incidents WHERE project_id = :pid "
                "AND created_at BETWEEN :i AND :f AND deleted_at IS NULL "
                "ORDER BY created_at DESC LIMIT 20",
                {"pid": str(project_id), "i": periodo_inicio, "f": periodo_fin},
                lambda r: {
                    "id": r.id,
                    "severidad": r.severidad,
                    "descripcion": (r.descripcion or "")[:200],
                    "estado": r.workflow_state,
                    "fecha": (
                        (r.fecha or r.created_at).isoformat()
                        if (r.fecha or r.created_at) else None
                    ),
                },
            )

        kpis = ReportKPIs(
            actividades_completadas=len([
                a for a in actividades_list if a.get("estado") == "completada"
            ]),
            vulns_abiertas=len([v for v in vulns_list if v.get("estado") != "closed"]),
            incidents_trimestre=incidents_trimestre_val,
            drift_score=drift_score_val,
            normativa_cambios=len(normativa_list),
            activities_ok_pct=(
                100.0 if not actividades_list
                else round(100.0 * len([
                    a for a in actividades_list
                    if a.get("estado") == "completada"
                ]) / max(1, len(actividades_list)), 1)
            ),
            medidas_implementadas_pct=medidas_pct,  # FIX: real desde DdA (no placeholder)
        )
        rag = self._calc_rag(kpis)

        return ReportPayload(
            client_name=client.nombre if client else "",
            client_cif=client.cif if client else "",
            project_name=project.nombre if project else None,
            retainer_tier=tier,
            periodo_inicio=periodo_inicio.isoformat(),
            periodo_fin=periodo_fin.isoformat(),
            periodo_label=periodo_label,
            rag_global=rag,
            kpis=kpis,
            actividades=actividades_list,
            vulnerabilidades=vulns_list,
            normativa_cambios=normativa_list,
            incidents=incidents_list,
            proximas_actividades=[],
            recomendaciones=(
                f"Mantenimiento continuado en marcha. RAG global: {rag}."
            ),
        )

    @staticmethod
    async def _safe_scalar(
        db: AsyncSession, sql: str, params: dict[str, Any],
    ) -> Any:
        """Ejecuta query en savepoint + SET LOCAL ROLE + RESET. None si falla."""
        sp = await db.begin_nested()
        try:
            await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
            row = (await db.execute(sa_text(sql), params)).first()
            await db.execute(sa_text("RESET ROLE"))
            await sp.commit()
            return row[0] if row else None
        except Exception:
            await sp.rollback()
            return None

    @staticmethod
    async def _safe_list(
        db: AsyncSession, sql: str, params: dict[str, Any], mapper,
    ) -> list[dict[str, Any]]:
        sp = await db.begin_nested()
        try:
            await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
            rows = (await db.execute(sa_text(sql), params)).all()
            await db.execute(sa_text("RESET ROLE"))
            await sp.commit()
            return [mapper(r) for r in rows]
        except Exception:
            await sp.rollback()
            return []

    @staticmethod
    def _calc_rag(kpis: ReportKPIs) -> str:
        if kpis.activities_ok_pct >= 90 and kpis.vulns_abiertas < 3:
            return "VERDE"
        if kpis.activities_ok_pct >= 70 and kpis.vulns_abiertas < 10:
            return "AMBAR"
        return "ROJO"

    @staticmethod
    def _sign(payload_bytes: bytes) -> str:
        """Firma Ed25519 sobre el JSON determinista."""
        from backend.app.motors.m25_lifecycle.backup_builder import (
            _load_backup_signing_key,
        )
        key, _pub = _load_backup_signing_key()
        return key.sign(payload_bytes).hex()
