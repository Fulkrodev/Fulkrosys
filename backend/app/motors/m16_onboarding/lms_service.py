"""M16 — Mini-LMS — Service.

Carga el catalogo de cursos LMS desde
``docs/catalogs/lms_courses_v1.json`` y orquesta:

1. ``assign_to_employees`` — asignar curso a una lista de empleados
2. ``record_attendance``   — marca iniciado_at y genera evidencia E-502
3. ``submit_quiz``         — corrige respuestas, calcula score, marca
                             completado/failed, genera evidencia E-503
4. ``get_progress``        — % de empleados que completaron cada curso

Las evidencias E-502 y E-503 son DOCX programaticos con el header /
footer estandar y el bloque de firmas individual del asistente.
Diseno alineado con la calidad esperada por el auditor ENAC.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.lms import LmsAssignment


logger = logging.getLogger(__name__)

_CATALOG_PATH = (
    Path(__file__).resolve().parents[4]
    / "docs" / "catalogs" / "lms_courses_v1.json"
)
_BASE_DIR = Path(__file__).resolve().parents[4] / "var" / "documents_lms"


VALID_ESTADOS = {"assigned", "in_progress", "completed", "failed", "expired"}

# §5.5 audit C6 · retención WORM (Object Lock COMPLIANCE) de las evidencias
# formativas E-502/E-503 · inmutable para ENAC. Env-configurable (prod 7 años),
# coherente con m07_evidence. La durabilidad la garantiza el volumen vardata; el
# WORM añade la inmutabilidad de almacenamiento.
_WORM_RETENTION_DAYS = int(os.environ.get("FULKRO_WORM_RETENTION_DAYS", "2555"))

# §5.5 audit C6 · límite de envíos del cuestionario por defecto cuando el curso
# no define ``max_attempts`` en el catálogo. Evita reintentos ilimitados.
_DEFAULT_MAX_ATTEMPTS = 3


def _archive_to_worm(
    docx_bytes: bytes,
    project_id: uuid.UUID,
    assignment_id: uuid.UUID,
    course_codigo: str,
    evidencia: str,
) -> str | None:
    """Archiva la evidencia formativa al bucket WORM inmutable. Best-effort.

    Devuelve la URI ``minio://...`` del objeto WORM, o ``None`` si MinIO/WORM no
    está disponible (dev). NO bloquea la generación de la evidencia — la copia
    local sigue siendo la fuente de lectura. Mismo patrón que
    ``m07_evidence._archive_clean_evidence_to_worm``.
    """
    try:
        from backend.app.core.storage.minio_client import (
            BUCKET_EVIDENCE_WORM,
            put_object,
        )
        key = f"lms/{project_id}/{course_codigo}/{assignment_id}/{evidencia}.docx"
        res = put_object(
            BUCKET_EVIDENCE_WORM, key, docx_bytes,
            content_type=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
            metadata={"project-id": str(project_id), "evidencia": evidencia},
            worm_retention_days=_WORM_RETENTION_DAYS,
        )
        return f"minio://{res.bucket}/{res.key}"
    except Exception as exc:  # noqa: BLE001 — best-effort, dev sin MinIO
        logger.warning(
            "WORM archival %s LMS %s falló (best-effort): %s",
            evidencia, assignment_id, exc,
        )
        return None


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

class LmsCatalogError(Exception):
    pass


@lru_cache(maxsize=1)
def load_catalog(path: Path | None = None) -> dict[str, Any]:
    p = path or _CATALOG_PATH
    if not p.exists():
        raise LmsCatalogError(f"LMS catalog not found at {p}")
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "courses" not in data or not data["courses"]:
        raise LmsCatalogError("LMS catalog has no courses")
    return data


def reset_catalog_cache() -> None:
    load_catalog.cache_clear()


def get_course(codigo: str) -> dict[str, Any] | None:
    catalog = load_catalog()
    for c in catalog["courses"]:
        if c.get("codigo") == codigo:
            return c
    return None


def list_courses() -> list[dict[str, Any]]:
    """Return courses with safe summary (no quiz answers)."""
    catalog = load_catalog()
    out = []
    for c in catalog["courses"]:
        out.append({
            "codigo": c["codigo"],
            "titulo": c["titulo"],
            "descripcion": c["descripcion"],
            "duracion_minutos": c["duracion_minutos"],
            "audiencia": c.get("audiencia"),
            "obligatorio": c.get("obligatorio", False),
            "modulos_count": len(c.get("modulos", [])),
            "preguntas_count": len(c.get("quiz", {}).get("preguntas", [])),
            "evidencias_generadas": c.get("evidencias_generadas", []),
        })
    return out


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class LmsError(Exception):
    pass


class LmsNotFoundError(LmsError):
    pass


class LmsValidationError(LmsError):
    pass


class LmsStateError(LmsError):
    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hash_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class LmsService:
    """Servicio del mini-LMS."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ─── Catalog passthrough ────────────────────────────────────────────

    @staticmethod
    def list_courses() -> list[dict[str, Any]]:
        return list_courses()

    @staticmethod
    def get_course(codigo: str) -> dict[str, Any]:
        course = get_course(codigo)
        if course is None:
            raise LmsNotFoundError(f"Curso '{codigo}' no esta en el catalogo")
        return course

    # ─── Assignments ────────────────────────────────────────────────────

    async def assign_to_employees(
        self,
        project_id: uuid.UUID,
        course_codigo: str,
        empleados: list[dict],
        due_date: datetime | None = None,
    ) -> list[LmsAssignment]:
        """Asigna un curso a una lista de empleados.

        empleados: [{nombre, email, cargo?, organizacion?}, ...]
        Idempotente por (project_id, asistente_email, course_codigo):
        si la asignacion ya existe, se devuelve sin duplicar.
        """
        course = self.get_course(course_codigo)
        if not empleados:
            raise LmsValidationError("La lista de empleados no puede estar vacia")
        for i, e in enumerate(empleados):
            if not e.get("email"):
                raise LmsValidationError(f"Empleado {i}: falta 'email'")
            if not e.get("nombre"):
                raise LmsValidationError(f"Empleado {i}: falta 'nombre'")

        now = datetime.now(timezone.utc)
        assignments: list[LmsAssignment] = []
        for emp in empleados:
            email = emp["email"].strip().lower()
            existing = (await self.db.execute(
                select(LmsAssignment).where(
                    LmsAssignment.project_id == project_id,
                    LmsAssignment.asistente_email == email,
                    LmsAssignment.course_codigo == course_codigo,
                    LmsAssignment.deleted_at.is_(None),
                )
            )).scalar_one_or_none()
            if existing is not None:
                assignments.append(existing)
                continue

            a = LmsAssignment(
                project_id=project_id,
                course_codigo=course_codigo,
                course_titulo=course["titulo"],
                course_duracion_minutos=int(course["duracion_minutos"]),
                asistente_nombre=emp["nombre"],
                asistente_email=email,
                asistente_cargo=emp.get("cargo"),
                asistente_organizacion=emp.get("organizacion"),
                asignado_at=now,
                due_date=due_date,
                estado="assigned",
            )
            self.db.add(a)
            assignments.append(a)
        await self.db.flush()
        return assignments

    async def get(self, assignment_id: uuid.UUID) -> LmsAssignment:
        a = await self.db.get(LmsAssignment, assignment_id)
        if a is None or a.deleted_at is not None:
            raise LmsNotFoundError(f"Asignacion {assignment_id} no encontrada")
        return a

    async def list_by_project(
        self,
        project_id: uuid.UUID,
        course_codigo: str | None = None,
        estado: str | None = None,
    ) -> list[LmsAssignment]:
        stmt = select(LmsAssignment).where(
            LmsAssignment.project_id == project_id,
            LmsAssignment.deleted_at.is_(None),
        )
        if course_codigo:
            stmt = stmt.where(LmsAssignment.course_codigo == course_codigo)
        if estado:
            stmt = stmt.where(LmsAssignment.estado == estado)
        stmt = stmt.order_by(LmsAssignment.asignado_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ─── Asistencia (E-502) ─────────────────────────────────────────────

    async def record_attendance(
        self,
        assignment_id: uuid.UUID,
        cliente_razon: str,
    ) -> LmsAssignment:
        """Marca iniciado_at + genera evidencia E-502 (asistencia).

        E-502 acredita que el asistente accedio al contenido del curso.
        Idempotente: si ya esta in_progress o completed, se regenera el
        E-502 (caso util para regenerar tras correcciones).
        """
        a = await self.get(assignment_id)
        if a.estado not in {"assigned", "in_progress", "completed", "failed"}:
            raise LmsStateError(
                f"No se puede registrar asistencia en estado '{a.estado}'"
            )

        from backend.app.motors.m16_onboarding.lms_docx import (
            build_e502_attendance_docx,
        )
        docx_bytes = build_e502_attendance_docx(
            assignment=a, cliente_razon=cliente_razon,
        )
        out_dir = _BASE_DIR / str(a.project_id) / a.course_codigo / str(a.id)
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = out_dir / f"E-502_{a.course_codigo}_{ts}.docx"
        path.write_bytes(docx_bytes)

        a.e502_path = str(path)
        a.e502_hash = _hash_sha256(docx_bytes)
        # §5.5 audit C6 · archivado WORM inmutable best-effort (copia local intacta)
        a.e502_worm_uri = _archive_to_worm(
            docx_bytes, a.project_id, a.id, a.course_codigo, "E-502",
        )
        if a.iniciado_at is None:
            a.iniciado_at = datetime.now(timezone.utc)
        if a.estado == "assigned":
            a.estado = "in_progress"
        await self.db.flush()
        return a

    # ─── Cuestionario (E-503) ───────────────────────────────────────────

    async def submit_quiz(
        self,
        assignment_id: uuid.UUID,
        respuestas: dict[str, str],
        cliente_razon: str,
    ) -> LmsAssignment:
        """Corrige el quiz, calcula score, marca completado/failed y
        genera evidencia E-503 (cuestionario).

        §5.5 audit C6 · límite de intentos: un cuestionario ya aprobado
        (``completed``) NO se puede reenviar, y el número de envíos está
        limitado a ``max_attempts`` (definido por curso en el catálogo, con
        fallback ``_DEFAULT_MAX_ATTEMPTS``). Esto impide reintentos ilimitados
        para "adivinar" hasta aprobar.
        """
        a = await self.get(assignment_id)
        # Un quiz ya APROBADO no se reabre (evita re-aprobar / regenerar evidencia).
        if a.estado == "completed":
            raise LmsStateError(
                "El cuestionario ya está aprobado; no se puede reenviar."
            )
        if a.estado not in {"in_progress", "assigned", "failed"}:
            raise LmsStateError(
                f"No se puede enviar quiz en estado '{a.estado}'"
            )
        course = self.get_course(a.course_codigo)
        quiz = course.get("quiz", {})
        preguntas = quiz.get("preguntas", [])
        if not preguntas:
            raise LmsValidationError("El curso no tiene preguntas")
        pass_score = float(quiz.get("pass_score", 70))
        max_attempts = int(quiz.get("max_attempts", _DEFAULT_MAX_ATTEMPTS))

        # §5.5 audit C6 · bloqueo de reintentos: ya agotó los intentos permitidos.
        if (a.intentos or 0) >= max_attempts:
            raise LmsStateError(
                f"Has agotado los {max_attempts} intentos permitidos para "
                f"este cuestionario. Contacta con el responsable de formación."
            )

        if not isinstance(respuestas, dict) or not respuestas:
            raise LmsValidationError("Las respuestas deben ser un dict no vacio")

        correcciones: dict[str, dict[str, Any]] = {}
        aciertos = 0
        for q in preguntas:
            qid = q["id"]
            correcta = q["respuesta_correcta"]
            tu = (respuestas.get(qid) or "").strip().lower()
            ok = tu == correcta.strip().lower()
            if ok:
                aciertos += 1
            correcciones[qid] = {
                "tu_respuesta": tu,
                "correcta": correcta,
                "ok": ok,
                "explicacion": q.get("explicacion", ""),
            }

        score = round(100.0 * aciertos / len(preguntas), 1)
        passed = score >= pass_score

        # §5.5 audit C6 · registra el intento consumido.
        a.intentos = (a.intentos or 0) + 1
        a.quiz_score = score
        a.quiz_pass = passed
        a.quiz_respuestas = respuestas
        a.quiz_correcciones = correcciones

        # Generar E-503 (cuestionario)
        from backend.app.motors.m16_onboarding.lms_docx import (
            build_e503_quiz_docx,
        )
        docx_bytes = build_e503_quiz_docx(
            assignment=a,
            course=course,
            correcciones=correcciones,
            cliente_razon=cliente_razon,
        )
        out_dir = _BASE_DIR / str(a.project_id) / a.course_codigo / str(a.id)
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = out_dir / f"E-503_{a.course_codigo}_{ts}.docx"
        path.write_bytes(docx_bytes)
        a.e503_path = str(path)
        a.e503_hash = _hash_sha256(docx_bytes)
        # §5.5 audit C6 · archivado WORM inmutable best-effort (copia local intacta)
        a.e503_worm_uri = _archive_to_worm(
            docx_bytes, a.project_id, a.id, a.course_codigo, "E-503",
        )

        a.completado_at = datetime.now(timezone.utc)
        a.estado = "completed" if passed else "failed"
        await self.db.flush()
        return a

    # ─── Progreso global ────────────────────────────────────────────────

    async def get_progress(self, project_id: uuid.UUID) -> dict[str, Any]:
        """Resumen de progreso por curso para el proyecto."""
        all_assignments = await self.list_by_project(project_id)
        by_course: dict[str, dict[str, Any]] = {}
        for a in all_assignments:
            entry = by_course.setdefault(
                a.course_codigo,
                {
                    "course_codigo": a.course_codigo,
                    "course_titulo": a.course_titulo,
                    "total": 0,
                    "assigned": 0, "in_progress": 0,
                    "completed": 0, "failed": 0, "expired": 0,
                    "promedio_score": None,
                    "scores": [],
                },
            )
            entry["total"] += 1
            entry[a.estado] = entry.get(a.estado, 0) + 1
            if a.quiz_score is not None:
                entry["scores"].append(a.quiz_score)

        for entry in by_course.values():
            if entry["scores"]:
                entry["promedio_score"] = round(
                    sum(entry["scores"]) / len(entry["scores"]), 1,
                )
            entry.pop("scores", None)
            entry["pct_completados"] = (
                round(100.0 * entry["completed"] / entry["total"], 1)
                if entry["total"] else 0.0
            )

        return {
            "project_id": str(project_id),
            "by_course": list(by_course.values()),
            "total_assignments": len(all_assignments),
        }
