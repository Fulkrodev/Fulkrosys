"""Fix del drift de keys/valores en el scoring de madurez (#6).

Demuestra que un sector que HOY NO puntuaba (porque usa otro vocabulario que las
SCORING_RULES viejas) ahora SÍ puntúa tras la capa de normalización, con guards
anti-falso-verde + los criterios de consultor de Marcos:
- backup `scripts_manuales` = 0 (no continuidad fiable ENS).
- DPO `no_obligatorio` = NEUTRO (ni puntúa ni cuenta como carencia).
- bug `max_possible` inflado arreglado (1 concepto = 1 entrada, max real).

Ver docs/audits/AUDIT_PUNTO_6_DRIFT_SCORING_RULES.md (tabla aprobada).
"""
from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import text

from backend.app.database import set_tenant_context
from backend.app.motors.m16_onboarding.enums import SessionState
from backend.app.motors.m21_diagnosis.compliance_service import detect_compliance_obligations
from backend.app.motors.m21_diagnosis.maturity_service import calculate_maturity
from backend.tests.conftest import _admin_setup, setup_test_project


async def _tenant(db):
    client_id, project_id = await setup_test_project(db)
    await set_tenant_context(db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id))
    return uuid.UUID(project_id)


async def _seed_session(db, project_id, *, sector="educacion_privada", role="ti_cto",
                        interlocutor="Ana Directora", answers=None):
    sid = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO onboarding_sessions "
            "(id, project_id, sector, estado, template_id_str, interlocutor_nombre, created_at) "
            "VALUES (:id, :pid, :sec, :estado, :tid, :inter, now())"
        ), {"id": str(sid), "pid": str(project_id), "sec": sector,
            "estado": SessionState.COMPLETED.value,
            "tid": f"onb-{sector}-{role}-v1", "inter": interlocutor})
        for qid, val in (answers or {}).items():
            await db.execute(text(
                "INSERT INTO onboarding_responses "
                "(id, session_id, question_id, section, answer_value, answered_at, updated_at) "
                "VALUES (:id, :sid, :qid, 'x', CAST(:v AS jsonb), now(), now())"
            ), {"id": str(uuid.uuid4()), "sid": str(sid), "qid": qid, "v": json.dumps(val)})
    await db.flush()
    return sid


@pytest.mark.asyncio
async def test_educacion_privada_now_scores(db):
    """Vocabulario de educacion_privada (hoy 0) → ahora puntúa en 4 dominios."""
    pid = await _tenant(db)
    await _seed_session(db, pid, answers={
        "q-mfa_implantado": "completo",                     # alias de q-mfa_universal → +3
        "q-backup_estrategia": "3_2_1",                      # valor que la regla ignoraba → +2
        "q-dpo_designado": True,                             # boolean → +2 (no in[interno,externo])
        "q-experiencia_previa_certificacion": "iso27001",   # alias → +1
    })
    d = (await calculate_maturity(db, pid))["domains"]

    assert d["op_acc"]["points"] >= 3, d["op_acc"]   # mfa completo
    assert d["op_cont"]["points"] == 2, d["op_cont"]  # backup 3_2_1
    assert d["mp_info"]["points"] >= 2, d["mp_info"]  # dpo True
    assert d["org"]["points"] >= 1, d["org"]          # experiencia + sponsor (interlocutor)
    # Bug max_possible inflado arreglado: backup = 1 concepto → op_cont max = 2 (no 5).
    assert d["op_cont"]["max_possible"] == 2, d["op_cont"]


@pytest.mark.asyncio
async def test_guard_anti_falso_verde_bad_answers_zero(db):
    """Anti-falso-verde: respuestas 'malas' NO puntúan (no es verde por casualidad)."""
    pid = await _tenant(db)
    await _seed_session(db, pid, answers={
        "q-mfa_implantado": "no",
        "q-backup_estrategia": "ninguno",
        "q-dpo_designado": False,
    })
    d = (await calculate_maturity(db, pid))["domains"]
    assert d["op_cont"]["points"] == 0
    assert d["op_acc"]["points"] == 0
    assert d["mp_info"]["points"] == 0


@pytest.mark.asyncio
async def test_guard_scripts_manuales_zero(db):
    """CRITERIO Marcos: backup por script manual = 0 (no continuidad fiable ENS)."""
    pid = await _tenant(db)
    await _seed_session(db, pid, answers={"q-backup_estrategia": "scripts_manuales"})
    d = (await calculate_maturity(db, pid))["domains"]
    assert d["op_cont"]["points"] == 0
    # Es un 0 REAL (carencia), no neutro: la regla se evaluó → max_possible cuenta.
    assert d["op_cont"]["max_possible"] == 2


@pytest.mark.asyncio
async def test_dpo_no_obligatorio_is_neutral(db):
    """CRITERIO Marcos: DPO no_obligatorio = NEUTRO → NO cuenta en max_possible.

    Con dpo=no_obligatorio + contratos=todos, mp_info debe salir 2/2 (L5): el DPO
    no penaliza. Contrasta con test_dpo_no_is_carencia (dpo=no → 2/4, L3).
    """
    pid = await _tenant(db)
    await _seed_session(db, pid, answers={
        "q-dpo_designado": "no_obligatorio",
        "q-contratos_art28_estado": "todos",
    })
    mp = (await calculate_maturity(db, pid))["domains"]["mp_info"]
    assert mp["points"] == 2, mp
    assert mp["max_possible"] == 2, mp   # DPO excluido del max (neutro), solo cuenta contratos
    assert mp["level"] == 5, mp


@pytest.mark.asyncio
async def test_dpo_no_is_carencia(db):
    """Contraste: dpo=no SÍ es carencia → cuenta en max_possible y arrastra el dominio."""
    pid = await _tenant(db)
    await _seed_session(db, pid, answers={
        "q-dpo_designado": "no",
        "q-contratos_art28_estado": "todos",
    })
    mp = (await calculate_maturity(db, pid))["domains"]["mp_info"]
    assert mp["points"] == 2, mp
    assert mp["max_possible"] == 4, mp   # dpo (0/2) + contratos (2/2)
    assert mp["level"] == 3, mp          # 50% → L3 (la neutralidad de no_obligatorio sube a L5)


@pytest.mark.asyncio
async def test_compliance_iso_normalization(db):
    """Cross-compliance ISO27001 dispara con alias + normaliza `iso_27001`→`iso27001`."""
    # saas_tech tiene ISO27001 (opcional) en su catálogo → la regla puede activarlo.
    pid = await _tenant(db)
    await _seed_session(db, pid, sector="saas_tech",
                        answers={"q-certificacion_iso": ["iso_27001"]})  # underscore + alias key
    res = await detect_compliance_obligations(db, pid, "saas_tech")
    iso = [n for n in res["applicable"] if n["code"] == "ISO27001"]
    assert iso, res
    assert iso[0]["cross_compliance_opportunity"] is True
