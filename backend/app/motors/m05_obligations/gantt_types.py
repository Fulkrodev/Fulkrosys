"""Motor 5 -- Gantt Planner -- data types.

Dataclasses for the Gantt planning pipeline.  Pure data, no DB or async.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date


@dataclass
class GanttTask:
    """A single scheduled obligation in the Gantt plan."""

    obligation_id: uuid.UUID
    template_id: str
    measure_code: str
    titulo: str
    modo_ejecucion: str | None
    estado: str | None
    esfuerzo_horas: float
    fecha_inicio: date
    fecha_fin: date
    duracion_dias_laborables: int
    predecesores_template_ids: list[str] = field(default_factory=list)


@dataclass
class GanttPlan:
    """Complete Gantt plan for a project."""

    project_id: uuid.UUID
    fecha_kickoff: date
    fecha_fin_estimada: date
    duracion_total_dias_laborables: int
    dedicacion_cliente_horas_semana: float
    tareas: list[GanttTask] = field(default_factory=list)

    def total_esfuerzo_horas(self) -> float:
        """Sum of effort hours across all tasks."""
        return sum(t.esfuerzo_horas for t in self.tareas)

    def to_json_dict(self) -> dict:
        """Serialise the plan to a JSON-compatible dict."""
        return {
            "project_id": str(self.project_id),
            "fecha_kickoff": self.fecha_kickoff.isoformat(),
            "fecha_fin_estimada": self.fecha_fin_estimada.isoformat(),
            "duracion_total_dias_laborables": self.duracion_total_dias_laborables,
            "dedicacion_cliente_horas_semana": self.dedicacion_cliente_horas_semana,
            "total_esfuerzo_horas": self.total_esfuerzo_horas(),
            "tareas": [
                {
                    "obligation_id": str(t.obligation_id),
                    "template_id": t.template_id,
                    "measure_code": t.measure_code,
                    "titulo": t.titulo,
                    "modo_ejecucion": t.modo_ejecucion,
                    "estado": t.estado,
                    "esfuerzo_horas": t.esfuerzo_horas,
                    "fecha_inicio": t.fecha_inicio.isoformat(),
                    "fecha_fin": t.fecha_fin.isoformat(),
                    "duracion_dias_laborables": t.duracion_dias_laborables,
                    "predecesores_template_ids": t.predecesores_template_ids,
                }
                for t in self.tareas
            ],
        }


class CircularDependencyError(ValueError):
    """Raised when a cycle is detected in the obligation dependency graph."""
