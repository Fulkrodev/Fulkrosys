"""R26 · promoción NC E-321/E-322 → audit_sessions/audit_findings + PAC + RLS.

Verifica empíricamente (BD real · RLS enforced):
- promote_audit_ncs proyecta E-321→AuditSession y E-322→AuditFinding con los
  campos mapeados, idempotente (re-promover no duplica).
- validate_pac_constraints: NC mayor exige PAC ≤90d (MEDIA/ALTA) · menor sin PAC.
- AuditFinding queda AISLADO por proyecto (RLS child via audit_sessions) — el
  test de fuga es el criterio crítico (un proyecto NO ve las NC de otro).
- E-322 huérfana (sin E-321) crea sesión sintética (no se pierde la NC).
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import select, text as sa_text

from backend.app.database import set_tenant_context
from backend.app.models.findings import AuditFinding, AuditSession
from backend.app.models.live_record import LiveRecord
from backend.app.motors.m_live_records.nc_promotion import (
    list_structured_ncs,
    promote_audit_ncs,
    validate_pac_constraints,
)
from backend.tests.conftest import _admin_setup, setup_test_project

_ACTOR = uuid.UUID("00000000-0000-0000-0000-0000000000aa")


async def _project(db, *, categoria: str = "MEDIA"):
    client_id, project_id = await setup_test_project(db)
    cid, pid = uuid.UUID(client_id), uuid.UUID(project_id)
    async with _admin_setup(db):
        await db.execute(sa_text(
            "UPDATE projects SET categoria_objetivo = :c WHERE id = :p"
        ), {"c": categoria, "p": project_id})
    await set_tenant_context(db, client_id=cid, project_id=pid)
    return cid, pid


def _live(pid, register_type, data) -> LiveRecord:
    return LiveRecord(
        project_id=pid, register_type=register_type, entry_data=data,
        status="active", created_by=_ACTOR, updated_by=_ACTOR,
    )


def _e321(cod="AUD-2026-01"):
    return {
        "codigo_auditoria_ext": cod, "entidad_acreditada": "AENOR ENAC 001/C-SI",
        "fecha_inicio": "2026-03-01", "fecha_fin": "2026-03-05",
        "categoria_ens_evaluada": "MEDIA", "alcance": "Sede electrónica",
        "resultado": "conforme_con_observaciones", "certificado_emitido": False,
    }


def _e322(cod="NC-01", aud="AUD-2026-01", sev="mayor", compromiso="2026-04-15"):
    return {
        "codigo_hallazgo": cod, "auditoria_codigo": aud, "severidad": sev,
        "medida_ens_afectada": "op.exp.8", "descripcion": "Logs sin retención 12m",
        "accion_correctiva": "Ampliar retención a 12 meses", "responsable": "RSEG",
        "fecha_compromiso": compromiso, "fecha_cierre_real": None, "estado": "abierto",
    }


async def test_promote_maps_and_is_idempotent(db):
    _, pid = await _project(db, categoria="MEDIA")
    db.add(_live(pid, "E-321", _e321()))
    db.add(_live(pid, "E-322", _e322()))
    await db.flush()

    res = await promote_audit_ncs(db, pid)
    assert res["sessions_promoted"] == 1
    assert res["findings_promoted"] == 1

    session = (await db.execute(select(AuditSession).where(
        AuditSession.project_id == pid))).scalar_one()
    assert session.codigo_externo == "AUD-2026-01"
    assert session.auditor == "AENOR ENAC 001/C-SI"
    assert session.tipo == "externa"

    finding = (await db.execute(select(AuditFinding).where(
        AuditFinding.audit_session_id == session.id))).scalar_one()
    assert finding.codigo_externo == "NC-01"
    assert finding.severidad == "mayor"
    assert finding.medida_afectada == "op.exp.8"
    assert finding.accion_correctiva == "Ampliar retención a 12 meses"
    assert finding.fecha_compromiso == date(2026, 4, 15)

    # Idempotente: re-promover NO duplica.
    res2 = await promote_audit_ncs(db, pid)
    assert res2["findings_promoted"] == 1
    n = len((await db.execute(select(AuditFinding).where(
        AuditFinding.audit_session_id == session.id))).scalars().all())
    assert n == 1


async def test_orphan_nc_creates_synthetic_session(db):
    _, pid = await _project(db, categoria="ALTA")
    db.add(_live(pid, "E-322", _e322(cod="NC-X", aud="AUD-NO-REG")))
    await db.flush()
    res = await promote_audit_ncs(db, pid)
    assert res["findings_promoted"] == 1
    assert res["sessions_promoted"] == 1
    session = (await db.execute(select(AuditSession).where(
        AuditSession.codigo_externo == "AUD-NO-REG"))).scalar_one()
    assert session is not None


async def test_pac_violation_surfaced_when_over_90d(db):
    _, pid = await _project(db, categoria="MEDIA")
    db.add(_live(pid, "E-321", _e321()))
    # compromiso > inicio(2026-03-01) + 90d → viola PAC.
    db.add(_live(pid, "E-322", _e322(compromiso="2026-09-01")))
    await db.flush()
    res = await promote_audit_ncs(db, pid)
    assert res["pac_ok"] is False
    assert any("90 días" in v or "90 d" in v for v in res["pac_violations"])


def test_validate_pac_constraints_rules():
    base = date(2026, 3, 1)
    # mayor MEDIA dentro de plazo + acción → ok
    assert validate_pac_constraints(
        severidad="mayor", categoria="MEDIA", accion_correctiva="x",
        fecha_compromiso=base + timedelta(days=30), fecha_deteccion=base,
    ) == []
    # mayor sin acción → viola
    assert validate_pac_constraints(
        severidad="mayor", categoria="MEDIA", accion_correctiva="",
        fecha_compromiso=base + timedelta(days=30), fecha_deteccion=base,
    )
    # mayor fuera de plazo → viola
    assert validate_pac_constraints(
        severidad="mayor", categoria="ALTA", accion_correctiva="x",
        fecha_compromiso=base + timedelta(days=120), fecha_deteccion=base,
    )
    # menor → sin requisito PAC
    assert validate_pac_constraints(
        severidad="menor", categoria="MEDIA", accion_correctiva="",
        fecha_compromiso=None, fecha_deteccion=base,
    ) == []


async def test_audit_findings_rls_isolation(db):
    """Fuga cross-proyecto: el proyecto B NO ve las NC del proyecto A."""
    _, pid_a = await _project(db, categoria="MEDIA")
    db.add(_live(pid_a, "E-321", _e321()))
    db.add(_live(pid_a, "E-322", _e322()))
    await db.flush()
    await promote_audit_ncs(db, pid_a)

    # Contexto A: ve su NC.
    visible_a = (await db.execute(select(AuditFinding))).scalars().all()
    assert len(visible_a) >= 1

    # Crea proyecto B y cambia contexto → NO debe ver las NC de A.
    cid_b, pid_b = await setup_test_project(db)
    await set_tenant_context(
        db, client_id=uuid.UUID(cid_b), project_id=uuid.UUID(pid_b),
    )
    visible_b = (await db.execute(select(AuditFinding))).scalars().all()
    assert visible_b == [], "FUGA: el proyecto B ve las NC del proyecto A"

    items_b = await list_structured_ncs(db, uuid.UUID(pid_b))
    assert items_b == []
