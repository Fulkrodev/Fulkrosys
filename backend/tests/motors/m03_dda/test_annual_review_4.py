"""#4 Ola8 · revisión anual del AR/DdA (mantenimiento Fase 8).

annual_review snapshotea las 73 medidas, registra el ciclo en
annual_review_records, bumpa la versión de las dda_entries y exige reaprobación
de Dirección (limpia aprobado_por).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import set_tenant_context
from backend.app.motors.m03_dda.enums import CategoriaSistema
from backend.app.motors.m03_dda.service import DdaService
from backend.tests.conftest import setup_test_project


@pytest.mark.asyncio
async def test_annual_review_bumps_version_and_records(db: AsyncSession):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(db, client_id=client_id, project_id=project_id)
    pid = uuid.UUID(project_id)
    svc = DdaService(db)
    await svc.generate_dda(
        project_id=pid,
        system_category=CategoriaSistema.MEDIA,
        responsable="RSEG Test",
    )  # crea las entries DdA (v1)

    # Aprobar (congelar) para verificar que annual_review limpia la aprobación
    await db.execute(
        sa_text(
            "UPDATE dda_entries SET aprobado_por='Dirección', "
            "fecha_aprobacion=now() WHERE project_id=:pid AND deleted_at IS NULL"
        ),
        {"pid": project_id},
    )
    await db.flush()

    result = await svc.annual_review(pid)

    assert result["new_version"] == result["previous_version"] + 1
    assert result["estado"] == "pending_director_approval"
    rec_id = result["annual_review_record_id"]

    # Record persistido en estado pending
    row = (
        await db.execute(
            sa_text(
                "SELECT estado, dda_version_to FROM annual_review_records WHERE id=:id"
            ),
            {"id": rec_id},
        )
    ).first()
    assert row is not None
    assert row[0] == "pending"
    assert row[1] == result["new_version"]

    # Entries: versión bumpeada + aprobación limpiada (exige reaprobación) + enlazadas
    versions = (
        await db.execute(
            sa_text(
                "SELECT DISTINCT version FROM dda_entries "
                "WHERE project_id=:pid AND deleted_at IS NULL"
            ),
            {"pid": project_id},
        )
    ).scalars().all()
    assert list(versions) == [result["new_version"]]

    still_approved = (
        await db.execute(
            sa_text(
                "SELECT count(*) FROM dda_entries WHERE project_id=:pid "
                "AND aprobado_por IS NOT NULL AND deleted_at IS NULL"
            ),
            {"pid": project_id},
        )
    ).scalar()
    assert still_approved == 0  # reaprobación pendiente

    linked = (
        await db.execute(
            sa_text(
                "SELECT count(*) FROM dda_entries WHERE annual_review_record_id=:rid"
            ),
            {"rid": rec_id},
        )
    ).scalar()
    assert linked > 0


def test_revision_ar_dda_wired_in_executors():
    # #4 · el scheduler reconoce el tipo de actividad.
    # Fix campaña 2026-06-17: el catálogo ACTIVITY_EXECUTORS se movió de
    # RetainerService (atributo de clase · eliminado en el fix S4) a
    # m23_retainer.tasks · fuente veraz del status del scheduler (ver nota S4 en
    # retainer_service.py). El test apuntaba al atributo viejo → AttributeError.
    from backend.app.motors.m23_retainer.tasks import ACTIVITY_EXECUTORS

    assert ACTIVITY_EXECUTORS.get("revision_ar_dda") == "m03_dda.annual_review"


def test_e808_autoevaluacion_registered():
    # #4 · el artefacto E-808 (autoevaluación 808 anual) está en el catálogo m06
    import pathlib

    import backend.app.motors.m06_document_factory as m06
    from backend.app.motors.m06_document_factory.template_registry import (
        TEMPLATE_REGISTRY,
    )

    assert "E-808" in TEMPLATE_REGISTRY
    assert TEMPLATE_REGISTRY["E-808"]["type"] == "deliverables"
    body_path = (
        pathlib.Path(m06.__file__).parent
        / "templates"
        / TEMPLATE_REGISTRY["E-808"]["body_path"]
    )
    assert body_path.exists()
    body = body_path.read_text(encoding="utf-8")
    assert "CCN-STIC 808" in body
    assert "Declaración de Aplicabilidad" in body
