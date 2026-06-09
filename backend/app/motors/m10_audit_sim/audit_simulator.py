"""M10 Audit Simulator — auditor virtual ENAC determinista.

Evalúa cada medida del Anexo II aplicable a la categoría del proyecto
cruzando evidencias REALES:
- Documents (M6) por template_codigo
- Evidence (M7) por measure_code + vigencia
- DdaEntry (M3) por aplicabilidad + estado_implementacion
- PentestFinding (M8) por mapeo_ens_jsonb

Reglas de evaluación DETERMINISTAS (NO LLM):
- DdA aplicabilidad = "no_aplica"              → no_aplica
- Ni documento ni evidencia                    → no_conforme_mayor (L0)
- Documento sin evidencia                      → no_conforme_menor (L1)
- Evidencia caducada                           → no_conforme_menor (L2)
- Documento + evidencia vigente + suficiente   → conforme (L3)
- Pentest finding mayor contra la medida       → contradicción / downgrade
- DdA = "implantado" sin evidencia             → contradicción
"""
from __future__ import annotations

import io
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit_sim import (
    AuditSimulationFinding,
    AuditSimulationRun,
)
from backend.app.models.documents import Document, Evidence
from backend.app.models.ens import DdaEntry, EnsMeasure
from backend.app.motors.m08_verification.integrations.m3_dda_updater import (
    get_findings_by_measure as get_verif_findings_by_measure,
)

from .audit_questions import FAMILIA_LABEL, get_questions_for_categoria


EVIDENCE_VALID_DAYS = 365
EVIDENCE_CURRENT_DAYS = 180


class AuditSimError(Exception):
    pass


class AuditSimulatorService:
    """Ejecuta simulación de auditoría ENAC completa."""

    # ══════════════════ Orquestación ══════════════════

    async def run_simulation(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        categoria: str,
    ) -> AuditSimulationRun:
        cat = (categoria or "").upper()
        if cat not in ("BASICA", "MEDIA", "ALTA"):
            raise AuditSimError(f"Categoría inválida: {categoria}")

        preguntas = get_questions_for_categoria(cat)

        run = AuditSimulationRun(
            project_id=project_id,
            categoria=cat,
            estado="running",
            total_measures=len(preguntas),
            started_at=datetime.now(timezone.utc),
        )
        db.add(run)
        await db.flush()

        findings: list[AuditSimulationFinding] = []
        for code, question in preguntas.items():
            finding = await self._evaluate_measure(
                db, project_id=project_id, run_id=run.id,
                measure_code=code, question=question,
            )
            findings.append(finding)
            db.add(finding)
        await db.flush()

        # Agregados
        run.measures_evaluated = len(findings)
        run.conformes = sum(1 for f in findings if f.evaluacion == "conforme")
        run.no_conformes_mayores = sum(1 for f in findings if f.evaluacion == "no_conforme_mayor")
        run.no_conformes_menores = sum(1 for f in findings if f.evaluacion == "no_conforme_menor")
        run.observaciones = sum(1 for f in findings if f.evaluacion == "observacion")
        run.no_aplica = sum(1 for f in findings if f.evaluacion == "no_aplica")
        run.contradicciones_count = sum(1 for f in findings if f.contradiccion_detectada)

        run.score_global = self._calculate_score(findings)
        run.nivel_madurez_global = self._global_maturity(findings)
        run.scores_por_familia = self._scores_by_family(findings)
        run.recomendacion = self._determine_recommendation(
            run.score_global, run.no_conformes_mayores,
        )
        run.estado = "completed"
        run.completed_at = datetime.now(timezone.utc)
        await db.flush()
        return run

    # ══════════════════ Evaluación por medida ══════════════════

    async def _evaluate_measure(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        run_id: uuid.UUID,
        measure_code: str,
        question: dict,
    ) -> AuditSimulationFinding:
        familia = question["familia"]
        measure_name = question.get("nombre") or measure_code
        doc_esperado = question.get("documento_esperado")

        # 1) DdA entry (si existe)
        dda = await self._get_dda_entry(db, project_id, measure_code)
        aplicabilidad = (dda.aplicabilidad or "").lower() if dda else ""
        estado_impl = (dda.estado_implementacion or "").lower() if dda else ""

        if aplicabilidad == "no_aplica":
            return AuditSimulationFinding(
                run_id=run_id,
                project_id=project_id,
                measure_code=measure_code,
                measure_name=measure_name,
                measure_family=familia,
                pregunta_auditor=question["pregunta"],
                criterio_aceptacion=question["criterio"],
                documento_esperado=doc_esperado,
                documento_encontrado=False,
                evidencia_encontrada=False,
                evidencia_vigente=False,
                evidencia_suficiente=False,
                evaluacion="no_aplica",
                nivel_madurez="L0",
                evidencia_ids=[],
            )

        # 2) Documento esperado (Documents por template_codigo)
        documento_encontrado = False
        if doc_esperado:
            documento_encontrado = await self._has_document(db, project_id, doc_esperado)

        # 3) Evidencias vinculadas a la medida
        evidencias = await self._find_evidences(db, project_id, measure_code)
        evidencia_encontrada = bool(evidencias)
        evidencia_vigente = False
        evidencia_suficiente = False
        evidencia_ids: list[str] = []
        if evidencia_encontrada:
            evidencia_ids = [str(e.id) for e in evidencias]
            evidencia_vigente = self._any_evidence_current(evidencias)
            evidencia_suficiente = self._sufficient_evidence(evidencias, question)

        # 4) Pentest finding mayor contra esta medida
        pentest_finding = await self._find_pentest_finding(db, project_id, measure_code)
        pentest_finding_id = pentest_finding.id if pentest_finding else None

        # 5) Contradicciones
        contradiccion = False
        contradiccion_detalle = None
        if estado_impl == "implantado" and not evidencia_encontrada:
            contradiccion = True
            contradiccion_detalle = (
                "DdA declara 'implantado' pero no hay evidencia en Evidence Vault "
                f"para {measure_code}."
            )
        elif pentest_finding and estado_impl == "implantado":
            contradiccion = True
            severidad = (pentest_finding.severidad or "").lower()
            contradiccion_detalle = (
                f"DdA declara 'implantado' pero pentest encontró hallazgo "
                f"{severidad or 'relevante'} contra {measure_code}."
            )

        # 6) Evaluación final (reglas deterministas)
        evaluacion = self._evaluate(
            has_document=documento_encontrado,
            has_evidence=evidencia_encontrada,
            evidence_current=evidencia_vigente,
            evidence_sufficient=evidencia_suficiente,
            pentest_major=bool(pentest_finding),
            expected_doc=bool(doc_esperado),
        )

        # Si hay contradicción fuerte, degrada
        if contradiccion and evaluacion == "conforme":
            evaluacion = "observacion"

        # 7) Madurez
        nivel_madurez = self._calculate_maturity_level(
            has_document=documento_encontrado,
            has_evidence=evidencia_encontrada,
            evidence_current=evidencia_vigente,
            evidence_sufficient=evidencia_suficiente,
            has_recent_records=evidencia_vigente and evidencia_suficiente,
        )

        # 8) Hallazgo / acción
        hallazgo, accion, plazo = self._hallazgo_for(evaluacion, measure_code, doc_esperado)

        return AuditSimulationFinding(
            run_id=run_id,
            project_id=project_id,
            measure_code=measure_code,
            measure_name=measure_name,
            measure_family=familia,
            pregunta_auditor=question["pregunta"],
            criterio_aceptacion=question["criterio"],
            documento_esperado=doc_esperado,
            documento_encontrado=documento_encontrado,
            evidencia_encontrada=evidencia_encontrada,
            evidencia_vigente=evidencia_vigente,
            evidencia_suficiente=evidencia_suficiente,
            evaluacion=evaluacion,
            nivel_madurez=nivel_madurez,
            hallazgo_descripcion=hallazgo,
            accion_requerida=accion,
            plazo_sugerido_dias=plazo,
            contradiccion_detectada=contradiccion,
            contradiccion_detalle=contradiccion_detalle,
            evidencia_ids=evidencia_ids,
            pentest_finding_id=pentest_finding_id,
        )

    # ══════════════════ SQL helpers ══════════════════

    async def _get_dda_entry(
        self, db: AsyncSession, project_id: uuid.UUID, measure_code: str
    ) -> DdaEntry | None:
        res = await db.execute(
            select(DdaEntry)
            .join(EnsMeasure, EnsMeasure.id == DdaEntry.measure_id)
            .where(
                DdaEntry.project_id == project_id,
                EnsMeasure.codigo == measure_code,
            )
            .limit(1)
        )
        return res.scalar_one_or_none()

    async def _has_document(
        self, db: AsyncSession, project_id: uuid.UUID, template_codigo: str
    ) -> bool:
        res = await db.execute(
            select(Document.id).where(
                Document.project_id == project_id,
                Document.template_codigo == template_codigo,
            ).limit(1)
        )
        return res.scalar_one_or_none() is not None

    async def _find_evidences(
        self, db: AsyncSession, project_id: uuid.UUID, measure_code: str
    ) -> list[Evidence]:
        res = await db.execute(
            select(Evidence).where(
                Evidence.project_id == project_id,
                Evidence.measure_code == measure_code,
            )
        )
        return list(res.scalars().all())

    async def _find_pentest_finding(
        self, db: AsyncSession, project_id: uuid.UUID, measure_code: str
    ):
        """Devuelve el primer finding high/critical abierto de la medida.

        Alimenta la simulacion de auditoria interna para reflejar
        contradicciones entre DdA 'implantado' y hallazgos reales de
        verificacion v5.1 sobre la misma medida.
        """
        by_measure = await get_verif_findings_by_measure(db, project_id)
        for f in by_measure.get(measure_code, []):
            sev = (f.severity or "info").lower()
            status = (f.status or "open").lower()
            if sev in ("critical", "high") and status in ("open", "needs_review"):
                return f
        return None

    def _any_evidence_current(self, evidencias: list[Evidence]) -> bool:
        """Evidencia vigente si:
        - vigente=True Y (fecha_caducidad futura O sin caducidad)
        - O fecha_evidencia dentro de EVIDENCE_CURRENT_DAYS
        """
        today = date.today()
        threshold = today - timedelta(days=EVIDENCE_CURRENT_DAYS)
        for e in evidencias:
            # fecha_caducidad explícita
            if e.fecha_caducidad and e.fecha_caducidad < today:
                continue
            if e.vigente is False:
                continue
            fecha_ref = e.fecha_evidencia or (e.created_at.date() if e.created_at else None)
            if not fecha_ref:
                # Sin fecha pero marcada vigente: conservador, la contamos
                return True
            if fecha_ref >= threshold:
                return True
        return False

    def _sufficient_evidence(
        self, evidencias: list[Evidence], question: dict
    ) -> bool:
        """Al menos una evidencia vigente (boolean flag) sin caducar."""
        today = date.today()
        return any(
            e.vigente and (not e.fecha_caducidad or e.fecha_caducidad >= today)
            for e in evidencias
        )

    # ══════════════════ Reglas deterministas ══════════════════

    @staticmethod
    def _evaluate(
        *,
        has_document: bool,
        has_evidence: bool,
        evidence_current: bool,
        evidence_sufficient: bool,
        pentest_major: bool,
        expected_doc: bool,
    ) -> str:
        if pentest_major and not evidence_sufficient:
            return "no_conforme_mayor"
        if not has_document and not has_evidence:
            return "no_conforme_mayor"
        if expected_doc and not has_document:
            return "no_conforme_menor"
        if has_evidence and not evidence_current:
            return "no_conforme_menor"
        if has_evidence and evidence_current and evidence_sufficient:
            if pentest_major:
                return "observacion"
            return "conforme"
        if has_evidence and evidence_current and not evidence_sufficient:
            return "observacion"
        return "no_conforme_menor"

    @staticmethod
    def _calculate_maturity_level(
        *,
        has_document: bool,
        has_evidence: bool,
        evidence_current: bool,
        evidence_sufficient: bool,
        has_recent_records: bool = False,
        has_metrics: bool = False,
    ) -> str:
        if not has_document and not has_evidence:
            return "L0"
        if has_document and not has_evidence:
            return "L1"
        if has_evidence and not evidence_current:
            return "L2"
        if has_evidence and evidence_current and evidence_sufficient:
            if has_recent_records and has_metrics:
                return "L4"
            if has_recent_records:
                return "L3"
            return "L3"
        return "L2"

    @staticmethod
    def _calculate_score(findings: list[AuditSimulationFinding]) -> int:
        puntos = {"conforme": 100, "observacion": 75, "no_conforme_menor": 25, "no_conforme_mayor": 0}
        evaluables = [f for f in findings if f.evaluacion != "no_aplica"]
        if not evaluables:
            return 0
        total = sum(puntos.get(f.evaluacion, 0) for f in evaluables)
        return round(total / len(evaluables))

    @staticmethod
    def _global_maturity(findings: list[AuditSimulationFinding]) -> str:
        evaluables = [f for f in findings if f.evaluacion != "no_aplica"]
        if not evaluables:
            return "L0"
        niveles = [int(f.nivel_madurez[1:]) for f in evaluables if f.nivel_madurez.startswith("L")]
        if not niveles:
            return "L0"
        avg = sum(niveles) / len(niveles)
        return f"L{round(avg)}"

    @staticmethod
    def _scores_by_family(
        findings: list[AuditSimulationFinding],
    ) -> dict[str, dict]:
        result: dict[str, dict] = {}
        puntos = {"conforme": 100, "observacion": 75, "no_conforme_menor": 25, "no_conforme_mayor": 0}
        for f in findings:
            if f.evaluacion == "no_aplica":
                continue
            fam = f.measure_family
            entry = result.setdefault(fam, {
                "score": 0, "nivel": "L0",
                "conformes": 0, "observaciones": 0,
                "no_conformes_mayores": 0, "no_conformes_menores": 0,
                "evaluadas": 0, "label": FAMILIA_LABEL.get(fam, fam),
            })
            entry["evaluadas"] += 1
            entry["score"] += puntos.get(f.evaluacion, 0)
            if f.evaluacion == "conforme":
                entry["conformes"] += 1
            elif f.evaluacion == "observacion":
                entry["observaciones"] += 1
            elif f.evaluacion == "no_conforme_mayor":
                entry["no_conformes_mayores"] += 1
            elif f.evaluacion == "no_conforme_menor":
                entry["no_conformes_menores"] += 1
        for fam, entry in result.items():
            if entry["evaluadas"]:
                entry["score"] = round(entry["score"] / entry["evaluadas"])
        return result

    @staticmethod
    def _determine_recommendation(score: int, nc_mayores: int) -> str:
        if score >= 85 and nc_mayores == 0:
            return "apto_para_auditoria"
        if score >= 70 and nc_mayores <= 2:
            return "requiere_remediacion_menor"
        if score >= 50 or nc_mayores <= 5:
            return "requiere_remediacion_mayor"
        return "no_presentar"

    @staticmethod
    def _hallazgo_for(
        evaluacion: str, measure_code: str, doc_esperado: str | None,
    ) -> tuple[str | None, str | None, int | None]:
        if evaluacion == "conforme":
            return None, None, None
        if evaluacion == "observacion":
            return (
                f"Medida {measure_code}: cumple pero con margen de mejora.",
                "Fortalecer evidencia (métricas, revisiones periódicas).",
                60,
            )
        if evaluacion == "no_conforme_menor":
            return (
                f"Medida {measure_code}: evidencia parcial, caducada o documento faltante.",
                f"Aportar evidencia vigente"
                + (f" y documento {doc_esperado}" if doc_esperado else ""),
                30,
            )
        if evaluacion == "no_conforme_mayor":
            return (
                f"Medida {measure_code}: sin documento ni evidencia, o hallazgo crítico de pentest.",
                "Implantar la medida desde cero y aportar evidencia completa.",
                15,
            )
        return None, None, None

    # ══════════════════ Consultas ══════════════════

    async def get_run(self, db: AsyncSession, run_id: uuid.UUID) -> AuditSimulationRun | None:
        res = await db.execute(select(AuditSimulationRun).where(AuditSimulationRun.id == run_id))
        return res.scalar_one_or_none()

    async def list_runs(
        self, db: AsyncSession, project_id: uuid.UUID
    ) -> list[AuditSimulationRun]:
        res = await db.execute(
            select(AuditSimulationRun)
            .where(AuditSimulationRun.project_id == project_id)
            .order_by(AuditSimulationRun.created_at.desc())
        )
        return list(res.scalars().all())

    async def list_findings(
        self,
        db: AsyncSession,
        run_id: uuid.UUID,
        evaluacion: str | None = None,
        familia: str | None = None,
        nivel: str | None = None,
    ) -> list[AuditSimulationFinding]:
        stmt = select(AuditSimulationFinding).where(
            AuditSimulationFinding.run_id == run_id,
        )
        if evaluacion:
            stmt = stmt.where(AuditSimulationFinding.evaluacion == evaluacion)
        if familia:
            stmt = stmt.where(AuditSimulationFinding.measure_family == familia)
        if nivel:
            stmt = stmt.where(AuditSimulationFinding.nivel_madurez == nivel)
        stmt = stmt.order_by(
            AuditSimulationFinding.measure_family,
            AuditSimulationFinding.measure_code,
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def get_finding(
        self, db: AsyncSession, finding_id: uuid.UUID,
    ) -> AuditSimulationFinding | None:
        res = await db.execute(
            select(AuditSimulationFinding).where(AuditSimulationFinding.id == finding_id)
        )
        return res.scalar_one_or_none()

    async def get_summary(
        self, db: AsyncSession, project_id: uuid.UUID
    ) -> dict[str, Any]:
        runs = await self.list_runs(db, project_id)
        if not runs:
            return {"runs_count": 0, "last_run": None, "trend": None}

        last = runs[0]
        trend = None
        if len(runs) >= 2:
            prev = runs[1]
            trend = {
                "score_delta": last.score_global - prev.score_global,
                "conformes_delta": last.conformes - prev.conformes,
                "nc_mayores_delta": last.no_conformes_mayores - prev.no_conformes_mayores,
            }

        return {
            "runs_count": len(runs),
            "last_run": {
                "id": str(last.id),
                "categoria": last.categoria,
                "score_global": last.score_global,
                "nivel_madurez_global": last.nivel_madurez_global,
                "conformes": last.conformes,
                "no_conformes_mayores": last.no_conformes_mayores,
                "no_conformes_menores": last.no_conformes_menores,
                "observaciones": last.observaciones,
                "no_aplica": last.no_aplica,
                "contradicciones_count": last.contradicciones_count,
                "recomendacion": last.recomendacion,
                "completed_at": last.completed_at.isoformat() if last.completed_at else None,
            },
            "trend": trend,
        }

    # ══════════════════ Informe DOCX ══════════════════

    async def generate_report_docx(
        self, db: AsyncSession, run_id: uuid.UUID,
    ) -> bytes:
        from docx import Document as DocxDocument

        run = await self.get_run(db, run_id)
        if not run:
            raise AuditSimError(f"Run {run_id} no encontrado")
        findings = await self.list_findings(db, run_id)

        doc = DocxDocument()
        doc.add_heading(f"Informe de auditoría interna ENS — {run.categoria}", level=0)
        doc.add_paragraph(f"Fecha: {run.completed_at or run.started_at or datetime.now(timezone.utc)}")
        doc.add_paragraph(f"Medidas evaluadas: {run.measures_evaluated}/{run.total_measures}")

        doc.add_heading("Resumen ejecutivo", level=1)
        doc.add_paragraph(f"Score global: {run.score_global}/100")
        doc.add_paragraph(f"Nivel de madurez global: {run.nivel_madurez_global}")
        doc.add_paragraph(f"Conformes: {run.conformes}")
        doc.add_paragraph(f"No conformes mayores: {run.no_conformes_mayores}")
        doc.add_paragraph(f"No conformes menores: {run.no_conformes_menores}")
        doc.add_paragraph(f"Observaciones: {run.observaciones}")
        doc.add_paragraph(f"No aplica: {run.no_aplica}")
        doc.add_paragraph(f"Contradicciones detectadas: {run.contradicciones_count}")
        doc.add_paragraph(f"Recomendación: {run.recomendacion or '-'}")

        doc.add_heading("Puntuación por familia (Anexo II)", level=1)
        for fam, data in (run.scores_por_familia or {}).items():
            label = data.get("label") or FAMILIA_LABEL.get(fam, fam)
            doc.add_paragraph(
                f"• {fam} ({label}): {data.get('score', 0)}/100 — "
                f"{data.get('conformes', 0)} conformes, "
                f"{data.get('no_conformes_mayores', 0)} NC mayores, "
                f"{data.get('no_conformes_menores', 0)} NC menores, "
                f"{data.get('observaciones', 0)} obs."
            )

        doc.add_heading("Detalle por medida", level=1)
        current_family = None
        for f in findings:
            if f.measure_family != current_family:
                current_family = f.measure_family
                doc.add_heading(
                    f"{current_family} — {FAMILIA_LABEL.get(current_family, current_family)}",
                    level=2,
                )
            p = doc.add_paragraph()
            p.add_run(f"{f.measure_code}  [{f.evaluacion.upper()}] ({f.nivel_madurez}) — {f.measure_name}\n").bold = True
            p.add_run(f"Pregunta: {f.pregunta_auditor}\n")
            if f.hallazgo_descripcion:
                p.add_run(f"Hallazgo: {f.hallazgo_descripcion}\n")
            if f.accion_requerida:
                p.add_run(f"Acción: {f.accion_requerida} (plazo: {f.plazo_sugerido_dias} días)\n")
            if f.contradiccion_detectada:
                p.add_run(f"CONTRADICCIÓN: {f.contradiccion_detalle}\n")

        # Contradicciones consolidadas
        contradicciones = [f for f in findings if f.contradiccion_detectada]
        if contradicciones:
            doc.add_heading("Contradicciones detectadas", level=1)
            for f in contradicciones:
                doc.add_paragraph(f"• {f.measure_code}: {f.contradiccion_detalle}")

        # Plan de acciones correctivas
        doc.add_heading("Plan de acciones correctivas", level=1)
        for f in findings:
            if f.accion_requerida:
                doc.add_paragraph(
                    f"• [{f.measure_code}] {f.accion_requerida} "
                    f"(plazo: {f.plazo_sugerido_dias} días)"
                )

        doc.add_heading("Conclusión", level=1)
        doc.add_paragraph(
            f"Con un score global de {run.score_global}/100, nivel {run.nivel_madurez_global}, "
            f"la recomendación es: {run.recomendacion}."
        )

        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()
