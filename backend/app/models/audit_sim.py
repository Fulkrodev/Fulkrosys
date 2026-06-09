"""M10 — Audit Simulation: runs + findings.

Auditor virtual ENAC: evalúa medidas del Anexo II ENS RD 311/2022
contra evidencia real (documentos M6, evidencias M7, DdA M3, pentest M8).
Evaluación DETERMINISTA L0-L5, NO LLM.
"""
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, FullMixin


class AuditSimulationRun(FullMixin, Base):
    """Simulación de auditoría ENAC completa sobre un proyecto."""
    __tablename__ = "audit_simulation_runs"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True,
    )

    # Configuración
    categoria: Mapped[str] = mapped_column(String(10), nullable=False)
    # "BASICA", "MEDIA", "ALTA"

    # Estado: pending → running → completed | failed
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    # Métricas de evaluación
    total_measures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    measures_evaluated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Resultados por evaluación
    conformes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    no_conformes_mayores: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    no_conformes_menores: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    observaciones: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    no_aplica: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Scores
    score_global: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0-100
    nivel_madurez_global: Mapped[str] = mapped_column(String(5), default="L0", nullable=False)
    # L0=inexistente, L1=inicial, L2=definido, L3=gestionado, L4=medido, L5=optimizado

    # Desglose por familia del Anexo II
    scores_por_familia: Mapped[dict | None] = mapped_column(JSONB)
    # {"org": {"score": 80, "nivel": "L3", "conformes": 3, ...}, ...}

    # Contradicciones detectadas (DdA dice implantado pero no evidencia, etc.)
    contradicciones_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Informe
    informe_path: Mapped[str | None] = mapped_column(String(500))

    # Recomendación final
    recomendacion: Mapped[str | None] = mapped_column(String(50))
    # "apto_para_auditoria" | "requiere_remediacion_menor"
    # "requiere_remediacion_mayor" | "no_presentar"

    started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class AuditSimulationFinding(FullMixin, Base):
    """Hallazgo individual sobre una medida ENS durante la simulación."""
    __tablename__ = "audit_simulation_findings"

    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("audit_simulation_runs.id"), nullable=False, index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True,
    )

    # Medida evaluada
    measure_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    measure_name: Mapped[str] = mapped_column(String(300), nullable=False)
    measure_family: Mapped[str] = mapped_column(String(20), nullable=False)
    # "org", "op.pl", "op.acc", "op.exp", "op.ext", "op.cont", "op.mon",
    # "mp.if", "mp.per", "mp.eq", "mp.com", "mp.info", "mp.sw", "mp.s"

    # Pregunta del auditor (catálogo)
    pregunta_auditor: Mapped[str] = mapped_column(Text, nullable=False)
    criterio_aceptacion: Mapped[str] = mapped_column(Text, nullable=False)

    # Evaluación de evidencia
    documento_esperado: Mapped[str | None] = mapped_column(String(20))  # E-XXX
    documento_encontrado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    evidencia_encontrada: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    evidencia_vigente: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    evidencia_suficiente: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Evaluación final
    evaluacion: Mapped[str] = mapped_column(String(30), nullable=False)
    # "conforme" | "no_conforme_mayor" | "no_conforme_menor"
    # | "observacion" | "no_aplica"

    # Madurez L0-L5
    nivel_madurez: Mapped[str] = mapped_column(String(5), nullable=False, default="L0")

    # Hallazgo (si no conforme)
    hallazgo_descripcion: Mapped[str | None] = mapped_column(Text)
    accion_requerida: Mapped[str | None] = mapped_column(Text)
    plazo_sugerido_dias: Mapped[int | None] = mapped_column(Integer)

    # Contradicción detectada
    contradiccion_detectada: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    contradiccion_detalle: Mapped[str | None] = mapped_column(Text)

    # Referencias a evidencias encontradas
    evidencia_ids: Mapped[list | None] = mapped_column(JSONB)
    # [UUID, UUID, ...]

    # Referencia a pentest finding (si aplica)
    pentest_finding_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
