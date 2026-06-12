"""R14 parte 2 · acuse de recibo de normativa por empleado (mp.per.3).

Cubre el alta + listado + cobertura (summary) y el aislamiento RLS por proyecto.
"""
import pytest

from backend.tests.conftest import setup_test_project

_BASE = "/api/v1/projects"


def _ack(codigo, nombre, **kw):
    base = {
        "documento_codigo": codigo,
        "empleado_nombre": nombre,
        "fecha_acuse": "2026-06-12",
    }
    base.update(kw)
    return base


class TestPolicyAcknowledgments:
    @pytest.mark.asyncio
    async def test_create_list_summary(self, async_client, db):
        _, project_id = await setup_test_project(db)

        # alta de 3 acuses (2 docs · 2 empleados distintos)
        for body in (
            _ack("E-100", "Ana Pérez", empleado_identidad="ana@demo.example",
                 documento_version="1.0", medio="portal"),
            _ack("E-100", "Luis Gómez", documento_version="1.0"),
            _ack("E-103", "Ana Pérez", documento_version="2.0", medio="manuscrita"),
        ):
            r = await async_client.post(
                f"{_BASE}/{project_id}/policy-acknowledgments", json=body,
            )
            assert r.status_code == 201, r.text

        # listado completo
        lst = await async_client.get(f"{_BASE}/{project_id}/policy-acknowledgments")
        assert lst.status_code == 200
        assert len(lst.json()) == 3

        # filtro por documento
        only100 = await async_client.get(
            f"{_BASE}/{project_id}/policy-acknowledgments",
            params={"documento_codigo": "E-100"},
        )
        assert only100.status_code == 200
        assert len(only100.json()) == 2
        assert all(a["documento_codigo"] == "E-100" for a in only100.json())

        # cobertura
        summ = await async_client.get(
            f"{_BASE}/{project_id}/policy-acknowledgments/summary"
        )
        assert summ.status_code == 200
        s = summ.json()
        assert s["total_acuses"] == 3
        assert s["empleados_distintos"] == 2  # Ana + Luis
        cov = {(r["documento_codigo"], r["documento_version"]): r["acuses"]
               for r in s["por_documento"]}
        assert cov[("E-100", "1.0")] == 2
        assert cov[("E-103", "2.0")] == 1

    @pytest.mark.asyncio
    async def test_rls_isolation_between_projects(self, async_client, db):
        _, project_a = await setup_test_project(db)
        _, project_b = await setup_test_project(db)

        r = await async_client.post(
            f"{_BASE}/{project_a}/policy-acknowledgments",
            json=_ack("E-100", "Ana Pérez"),
        )
        assert r.status_code == 201, r.text

        # el proyecto B NO ve los acuses del A (RLS project-scoped)
        lst_b = await async_client.get(f"{_BASE}/{project_b}/policy-acknowledgments")
        assert lst_b.status_code == 200
        assert lst_b.json() == []

        lst_a = await async_client.get(f"{_BASE}/{project_a}/policy-acknowledgments")
        assert len(lst_a.json()) == 1
