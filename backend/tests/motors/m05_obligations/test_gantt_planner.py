"""Tests for Motor 5 -- Gantt Planner pure algorithm.

All tests are sync (no DB, no async).  Validates business-day math,
topological sorting, date chaining, and serialisation.
"""
from __future__ import annotations

import json
import uuid
from datetime import date

import pytest

from backend.app.motors.m05_obligations.gantt_planner import (
    _add_workdays,
    _next_workday,
    _topological_sort,
    build_gantt_plan,
)
from backend.app.motors.m05_obligations.gantt_types import CircularDependencyError


# ── _add_workdays ─────────────────────────────────────────────────────


class TestAddWorkdays:

    def test_add_workdays_skips_weekends(self):
        # Friday 2025-01-03 + 1 workday => Monday 2025-01-06
        friday = date(2025, 1, 3)
        result = _add_workdays(friday, 1)
        assert result == date(2025, 1, 6)
        assert result.weekday() == 0  # Monday

    def test_add_workdays_zero_returns_same(self):
        d = date(2025, 1, 6)  # Monday
        assert _add_workdays(d, 0) == d

    def test_add_workdays_full_week(self):
        # Monday + 5 workdays = next Monday
        monday = date(2025, 1, 6)
        result = _add_workdays(monday, 5)
        assert result == date(2025, 1, 13)
        assert result.weekday() == 0  # Monday

    def test_add_workdays_two_weeks(self):
        # Monday + 10 workdays = Monday two weeks later
        monday = date(2025, 1, 6)
        result = _add_workdays(monday, 10)
        assert result == date(2025, 1, 20)


# ── _next_workday ─────────────────────────────────────────────────────


class TestNextWorkday:

    def test_next_workday_saturday_to_monday(self):
        saturday = date(2025, 1, 4)
        assert _next_workday(saturday) == date(2025, 1, 6)

    def test_next_workday_sunday_to_monday(self):
        sunday = date(2025, 1, 5)
        assert _next_workday(sunday) == date(2025, 1, 6)

    def test_next_workday_weekday_unchanged(self):
        wednesday = date(2025, 1, 8)
        assert _next_workday(wednesday) == wednesday


# ── _topological_sort ─────────────────────────────────────────────────


class TestTopologicalSort:

    def test_simple_chain(self):
        # A -> B -> C
        obls = {
            "A": {"dependencias_template_ids": []},
            "B": {"dependencias_template_ids": ["A"]},
            "C": {"dependencias_template_ids": ["B"]},
        }
        result = _topological_sort(obls)
        assert result.index("A") < result.index("B") < result.index("C")

    def test_independent_nodes(self):
        obls = {
            "X": {"dependencias_template_ids": []},
            "Y": {"dependencias_template_ids": []},
            "Z": {"dependencias_template_ids": []},
        }
        result = _topological_sort(obls)
        assert set(result) == {"X", "Y", "Z"}

    def test_detects_cycle(self):
        obls = {
            "A": {"dependencias_template_ids": ["B"]},
            "B": {"dependencias_template_ids": ["A"]},
        }
        with pytest.raises(CircularDependencyError):
            _topological_sort(obls)

    def test_ignores_external_predecessors(self):
        # B depends on EXTERNAL which is not in the dict
        obls = {
            "A": {"dependencias_template_ids": []},
            "B": {"dependencias_template_ids": ["EXTERNAL", "A"]},
        }
        result = _topological_sort(obls)
        assert result.index("A") < result.index("B")
        assert len(result) == 2


# ── build_gantt_plan ──────────────────────────────────────────────────


class TestBuildGanttPlan:

    def _make_obl(
        self,
        template_id: str,
        esfuerzo: float = 8.0,
        deps: list[str] | None = None,
        measure_code: str = "org.1",
    ) -> dict:
        return {
            "obligation_id": uuid.uuid4(),
            "template_id": template_id,
            "measure_code": measure_code,
            "titulo": f"Tarea {template_id}",
            "modo_ejecucion": "consultor_genera",
            "estado": "pending",
            "esfuerzo_estimado": esfuerzo,
            "dependencias_template_ids": deps or [],
        }

    def test_empty_obligations(self):
        pid = uuid.uuid4()
        kickoff = date(2025, 1, 6)
        plan = build_gantt_plan(pid, [], kickoff)
        assert plan.tareas == []
        assert plan.duracion_total_dias_laborables == 0
        assert plan.fecha_fin_estimada == kickoff

    def test_single_obligation_dates(self):
        """Single task of 8h at 8h/week = 5 workdays."""
        pid = uuid.uuid4()
        kickoff = date(2025, 1, 6)  # Monday
        obl = self._make_obl("T1", esfuerzo=8.0)

        plan = build_gantt_plan(pid, [obl], kickoff, dedicacion_horas_semana=8.0)

        assert len(plan.tareas) == 1
        t = plan.tareas[0]
        # daily capacity = 8/5 = 1.6h, duration = ceil(8/1.6) = 5 days
        assert t.duracion_dias_laborables == 5
        assert t.fecha_inicio == date(2025, 1, 6)  # Monday
        # 5 workdays from Monday: Mon-Fri = same week Friday
        assert t.fecha_fin == date(2025, 1, 10)  # Friday

    def test_chain_dependencies(self):
        """B depends on A: B must start after A finishes."""
        pid = uuid.uuid4()
        kickoff = date(2025, 1, 6)  # Monday
        a = self._make_obl("A", esfuerzo=8.0)
        b = self._make_obl("B", esfuerzo=8.0, deps=["A"])

        plan = build_gantt_plan(pid, [a, b], kickoff, dedicacion_horas_semana=8.0)

        assert len(plan.tareas) == 2
        task_a = next(t for t in plan.tareas if t.template_id == "A")
        task_b = next(t for t in plan.tareas if t.template_id == "B")

        # A: Mon 6 - Fri 10
        assert task_a.fecha_fin == date(2025, 1, 10)
        # B starts next workday after A ends (Monday 13)
        assert task_b.fecha_inicio == date(2025, 1, 13)

    def test_kickoff_on_weekend_starts_monday(self):
        """If kickoff falls on Saturday, first task starts Monday."""
        pid = uuid.uuid4()
        kickoff = date(2025, 1, 4)  # Saturday
        obl = self._make_obl("T1", esfuerzo=1.6)

        plan = build_gantt_plan(pid, [obl], kickoff, dedicacion_horas_semana=8.0)

        assert plan.tareas[0].fecha_inicio == date(2025, 1, 6)  # Monday
        assert plan.fecha_kickoff == date(2025, 1, 6)

    def test_to_json_dict_serializable(self):
        """to_json_dict() must produce a JSON-serializable dict."""
        pid = uuid.uuid4()
        kickoff = date(2025, 1, 6)
        obl = self._make_obl("T1", esfuerzo=4.0)

        plan = build_gantt_plan(pid, [obl], kickoff)
        d = plan.to_json_dict()

        # Must not raise
        serialized = json.dumps(d)
        assert "tareas" in d
        assert len(d["tareas"]) == 1
        assert d["project_id"] == str(pid)

    def test_total_esfuerzo_horas(self):
        """total_esfuerzo_horas() sums all task efforts."""
        pid = uuid.uuid4()
        kickoff = date(2025, 1, 6)
        obls = [
            self._make_obl("A", esfuerzo=4.0),
            self._make_obl("B", esfuerzo=6.0),
        ]

        plan = build_gantt_plan(pid, obls, kickoff)
        assert plan.total_esfuerzo_horas() == 10.0
