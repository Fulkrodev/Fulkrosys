"""LMS (Learning Management System) — modelo simple para Mini-LMS.

Una sola tabla `lms_assignments` que registra:
- a quien se le asigna que curso
- cuando lo inicio / cuando lo completo
- score del cuestionario y si aprobo
- rutas a las evidencias generadas (E-502 asistencia + E-503 cuestionario)

El catalogo de cursos vive en docs/catalogs/lms_courses_v1.json y NO
requiere tabla — se carga al inicio y se referencia por codigo
(LMS-001, LMS-002, LMS-003).
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Float, ForeignKey, Integer, String, Text,
    UniqueConstraint, Index,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, FullMixin


class LmsAssignment(FullMixin, Base):
    """Asignacion de curso LMS a un empleado/asistente.

    Estados: assigned -> in_progress -> completed | failed | expired
    """
    __tablename__ = "lms_assignments"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "asistente_email", "course_codigo",
            name="uq_lms_project_asistente_course",
        ),
        Index(
            "ix_lms_project_estado",
            "project_id", "estado",
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False,
    )
    course_codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    # LMS-001 | LMS-002 | LMS-003
    course_titulo: Mapped[str] = mapped_column(String(300), nullable=False)
    course_duracion_minutos: Mapped[int] = mapped_column(Integer, nullable=False)

    asistente_nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    asistente_email: Mapped[str] = mapped_column(String(255), nullable=False)
    asistente_cargo: Mapped[str | None] = mapped_column(String(200))
    asistente_organizacion: Mapped[str | None] = mapped_column(String(200))

    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="assigned",
        server_default="assigned",
    )
    # assigned | in_progress | completed | failed | expired

    asignado_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
    )
    iniciado_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    completado_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    due_date: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    quiz_score: Mapped[float | None] = mapped_column(Float)
    quiz_pass: Mapped[bool | None] = mapped_column(Boolean)
    quiz_respuestas: Mapped[dict | None] = mapped_column(JSONB)
    # {"q1":"a","q2":"b",...}
    quiz_correcciones: Mapped[dict | None] = mapped_column(JSONB)
    # {"q1":{"correcta":"b","tu_respuesta":"a","ok":false}, ...}

    e502_path: Mapped[str | None] = mapped_column(String(500))
    e502_hash: Mapped[str | None] = mapped_column(String(64))
    e503_path: Mapped[str | None] = mapped_column(String(500))
    e503_hash: Mapped[str | None] = mapped_column(String(64))

    # §5.5 audit C6 · URI canónica minio://{bucket}/{key} de la copia archivada
    # al bucket WORM inmutable (fulkro-evidence-worm). NULL si MinIO no está
    # configurado (dev) — la copia local sigue siendo la fuente de lectura.
    e502_worm_uri: Mapped[str | None] = mapped_column(String(500))
    e503_worm_uri: Mapped[str | None] = mapped_column(String(500))

    # §5.5 audit C6 · contador de envíos del cuestionario. submit_quiz lo
    # incrementa y rechaza nuevos envíos al alcanzar max_attempts (por curso).
    intentos: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
    )

    notas: Mapped[str | None] = mapped_column(Text)
