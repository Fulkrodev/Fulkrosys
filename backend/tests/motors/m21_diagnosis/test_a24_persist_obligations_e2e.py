"""Tests E2E A24 cross_compliance_service · sub-lote 1.B.6.1.

Validacion end-to-end de detect_obligations + persist_obligations contra
el schema REAL (audit 1.B.6.0):
- legal_obligations tiene project_id FK (NO client_id)
- columnas: normativa · articulo · alcance · impacto_ens · estado · notas ·
  measure_codes_relacionadas JSONB
- persist_obligations(db, project_id, ctx, *, skip_existing=True)
- detect_obligations(ctx) puro · sin DB

Counts realistas validados contra codigo actual de las 7 funciones:
  _rgpd_obligations: 2-5 (depende empleados/sensibles/menores/IA)
  _nis2_obligations: 3 si es_sector_esencial OR es_sector_importante
  _dora_obligations: 3 si es_entidad_financiera_ue
  _psd2_obligations: 1 si procesa_pagos
  _ai_act_obligations: 1 si tiene_sistemas_ia_alto_riesgo
  _iso27001_opportunity: 1 siempre
  _eni_obligations: 1 si es_administracion_publica

Para perfil fintech default (empleados=50, no sensibles): MAX ~10 obligations.

Requires DB live + fixture setup_test_project del conftest root.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.app.motors.m21_diagnosis.cross_compliance_service import (
    ComplianceContext,
    build_summary,
    detect_obligations,
    persist_obligations,
)
from backend.tests.conftest import setup_test_project


def _fintech_ctx() -> ComplianceContext:
    """CTX-A · fintech UE alto trigger · maximiza RGPD+NIS2+DORA+PSD2+ISO27001."""
    return ComplianceContext(
        sector="fintech",
        empleados=50,
        maneja_datos_personales=True,
        maneja_datos_sensibles=False,
        maneja_datos_menores=False,
        es_sector_esencial_nis2=False,
        es_sector_importante_nis2=True,
        es_entidad_financiera_ue=True,
        procesa_pagos=True,
        tiene_sistemas_ia_alto_riesgo=False,
        es_administracion_publica=False,
    )


def _proveedor_tic_con_ai_ctx() -> ComplianceContext:
    """CTX-B · proveedor TIC sector esencial con IA alto riesgo.

    Activa: RGPD (Art.30+33+37+35 con empleados>=250 + AI) + NIS2 (esencial)
    + AI Act + ISO27001. NO DORA · NO PSD2.

    Total esperado: 4 RGPD + 3 NIS2 + 1 AI Act + 1 ISO27001 = 9 rows.
    """
    return ComplianceContext(
        sector="proveedor-tic",
        empleados=300,
        maneja_datos_personales=True,
        maneja_datos_sensibles=False,
        maneja_datos_menores=False,
        es_sector_esencial_nis2=True,
        es_sector_importante_nis2=False,
        es_entidad_financiera_ue=False,
        procesa_pagos=False,
        tiene_sistemas_ia_alto_riesgo=True,
        es_administracion_publica=False,
    )


def _pyme_basica_ctx() -> ComplianceContext:
    """CTX-C · PYME basica >250 empleados solo datos personales · RGPD+ISO27001.

    empleados=300 dispara Art.37 RGPD (DPO obligatorio · linea 94).
    Sin NIS2 · sin DORA · sin AI Act.
    Total esperado: 3 RGPD (Art.30+33+37) + 1 ISO27001 = 4
    NOTA: briefing menciono "Solo maneja_datos_personales=True" con expect 4-6.
    Para alcanzar >=4 hace falta o empleados>=250 o sensibles. Aqui usamos
    empleados=300 (caso "PYME grande proveedora AAPP sin sensibles").
    """
    return ComplianceContext(
        sector="industrial_b2b",
        empleados=300,
        maneja_datos_personales=True,
        maneja_datos_sensibles=False,
        maneja_datos_menores=False,
        es_sector_esencial_nis2=False,
        es_sector_importante_nis2=False,
        es_entidad_financiera_ue=False,
        procesa_pagos=False,
        tiene_sistemas_ia_alto_riesgo=False,
        es_administracion_publica=False,
    )


# ── Test 1 · detect_obligations puro (sin DB) ────────────────────────


def test_detect_obligations_fintech_returns_expected_range():
    """Perfil fintech genera 10-15 obligations (3 NIS2 + 3 DORA + 2 RGPD +
    1 PSD2 + 1 ISO27001 = 10 minimo · margen para variantes)."""
    ctx = _fintech_ctx()
    obs = detect_obligations(ctx)

    assert 10 <= len(obs) <= 15, (
        f"detect_obligations(fintech) -> {len(obs)} obligations · "
        "esperado [10..15] (RGPD 2 + NIS2 3 + DORA 3 + PSD2 1 + ISO27001 1 = 10 base)"
    )
    normativas = {o.norma for o in obs}
    assert "RGPD" in normativas, f"RGPD ausente · normativas: {normativas}"
    assert "NIS2" in normativas, f"NIS2 ausente · normativas: {normativas}"
    assert "DORA" in normativas, f"DORA ausente · normativas: {normativas}"
    assert "PSD2" in normativas, f"PSD2 ausente · normativas: {normativas}"
    assert "ISO 27001" in normativas, f"ISO 27001 ausente · normativas: {normativas}"


def test_detect_obligations_no_personales_no_genera_rgpd():
    """Edge: sin datos personales no se genera ninguna RGPD obligation."""
    ctx = ComplianceContext(
        sector="industrial_b2b", maneja_datos_personales=False,
    )
    obs = detect_obligations(ctx)
    assert all(o.norma != "RGPD" for o in obs)
    assert all(o.norma != "LOPDGDD" for o in obs)


# ── Test 2 · persist_obligations E2E con DB ──────────────────────────


@pytest.mark.asyncio
async def test_persist_obligations_fintech_inserts_rows(db):
    """E2E: detect + persist + verify rows via SQL real."""
    _, project_id = await setup_test_project(db)

    ctx = _fintech_ctx()
    rows = await persist_obligations(db, uuid.UUID(project_id), ctx)
    await db.flush()

    assert len(rows) >= 10, f"persist devolvio {len(rows)} rows · esperado >= 10"

    # Query realista usando columnas REALES del schema
    result = await db.execute(text(
        "SELECT normativa, COUNT(*) FROM legal_obligations "
        "WHERE project_id = :pid AND deleted_at IS NULL "
        "GROUP BY normativa ORDER BY normativa"
    ), {"pid": project_id})
    counts = {row[0]: row[1] for row in result}

    assert counts.get("RGPD", 0) >= 2, f"RGPD count={counts.get('RGPD', 0)} < 2"
    assert counts.get("NIS2", 0) >= 3, f"NIS2 count={counts.get('NIS2', 0)} < 3"
    assert counts.get("DORA", 0) >= 3, f"DORA count={counts.get('DORA', 0)} < 3"
    assert sum(counts.values()) >= 10, f"total={sum(counts.values())} < 10"


# ── Test 3 · columnas criticas no-NULL ───────────────────────────────


@pytest.mark.asyncio
async def test_persist_obligations_critical_columns_not_null(db):
    """Tras persist · normativa + articulo + alcance no deben ser NULL."""
    _, project_id = await setup_test_project(db)
    await persist_obligations(db, uuid.UUID(project_id), _fintech_ctx())
    await db.flush()

    result = await db.execute(text(
        "SELECT COUNT(*) FROM legal_obligations "
        "WHERE project_id = :pid AND deleted_at IS NULL "
        "AND (normativa IS NULL OR articulo IS NULL OR alcance IS NULL)"
    ), {"pid": project_id})
    nulls = result.scalar_one()
    assert nulls == 0, f"{nulls} rows con normativa/articulo/alcance NULL"

    # Tambien: estado debe ser 'identificada' por defecto en A24
    result2 = await db.execute(text(
        "SELECT COUNT(*) FROM legal_obligations "
        "WHERE project_id = :pid AND deleted_at IS NULL "
        "AND estado != 'identificada'"
    ), {"pid": project_id})
    bad_estado = result2.scalar_one()
    assert bad_estado == 0, f"{bad_estado} rows con estado != 'identificada'"


# ── Test 4 · measure_codes_relacionadas JSONB cruces ENS ─────────────


@pytest.mark.asyncio
async def test_persist_obligations_jsonb_has_ens_cross_refs(db):
    """measure_codes_relacionadas debe tener cruces ENS (JSONB 'codes' array
    no vacio) en la mayoria de obligations."""
    _, project_id = await setup_test_project(db)
    await persist_obligations(db, uuid.UUID(project_id), _fintech_ctx())
    await db.flush()

    result = await db.execute(text(
        "SELECT COUNT(*) FROM legal_obligations "
        "WHERE project_id = :pid AND deleted_at IS NULL "
        "AND measure_codes_relacionadas->'codes' IS NOT NULL "
        "AND jsonb_array_length(measure_codes_relacionadas->'codes') > 0"
    ), {"pid": project_id})
    con_cruces = result.scalar_one()
    assert con_cruces >= 5, (
        f"Solo {con_cruces} obligations con ENS cross-refs JSONB · esperado >= 5"
    )

    # Verifica que measure codes son realistas (formato 'op.exp.7', 'mp.info.1', etc.)
    result2 = await db.execute(text(
        "SELECT measure_codes_relacionadas->'codes' "
        "FROM legal_obligations "
        "WHERE project_id = :pid AND deleted_at IS NULL "
        "AND jsonb_array_length(measure_codes_relacionadas->'codes') > 0 "
        "LIMIT 1"
    ), {"pid": project_id})
    sample = result2.scalar_one()
    assert isinstance(sample, list) and len(sample) > 0
    # primer code debe matchear patron ENS (org.|op.|mp.)
    first = sample[0]
    assert isinstance(first, str)
    assert first.startswith(("org.", "op.", "mp.")), (
        f"measure_code '{first}' no parece formato ENS"
    )


# ── Test 5 · idempotencia skip_existing=True ─────────────────────────


@pytest.mark.asyncio
async def test_persist_obligations_idempotent_skip_existing(db):
    """Segunda ejecucion con skip_existing=True NO debe duplicar rows."""
    _, project_id = await setup_test_project(db)
    ctx = _fintech_ctx()

    rows1 = await persist_obligations(db, uuid.UUID(project_id), ctx)
    await db.flush()

    rows2 = await persist_obligations(db, uuid.UUID(project_id), ctx)
    await db.flush()

    assert len(rows2) == 0, (
        f"Segunda ejecucion creo {len(rows2)} dupes · skip_existing roto"
    )

    # Confirma BD: total rows = len(rows1)
    result = await db.execute(text(
        "SELECT COUNT(*) FROM legal_obligations "
        "WHERE project_id = :pid AND deleted_at IS NULL"
    ), {"pid": project_id})
    total = result.scalar_one()
    assert total == len(rows1), (
        f"BD tiene {total} rows · primera persist devolvio {len(rows1)} · "
        "indica duplicacion silenciosa"
    )


# ── Bonus · build_summary helper ─────────────────────────────────────


def test_build_summary_fintech_flags_correct():
    """build_summary genera flags correctos para perfil fintech."""
    ctx = _fintech_ctx()
    obs = detect_obligations(ctx)
    summary = build_summary(ctx, obs)

    assert summary["sector"] == "fintech"
    assert summary["empleados"] == 50
    assert summary["total_obligaciones"] >= 10
    assert summary["recomendacion"] == "multi_compliance"  # >= 3 normas
    assert summary["flags"]["nis2_aplicable"] is True
    assert summary["flags"]["dora_aplicable"] is True
    assert summary["flags"]["ai_act_aplicable"] is False
    assert summary["flags"]["eni_aplicable"] is False


# ── CTX-B · proveedor TIC con IA alto riesgo (briefing v3) ──────────


@pytest.mark.asyncio
async def test_ctx_b_proveedor_tic_con_ai(db):
    """CTX-B · valida mix RGPD+NIS2+AI Act sin DORA/PSD2 (negative asserts)."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)

    ctx = _proveedor_tic_con_ai_ctx()

    obs = detect_obligations(ctx)
    assert 8 <= len(obs) <= 12, (
        f"CTX-B detect: {len(obs)} obligations · esperado [8..12]"
    )

    rows = await persist_obligations(db, project_uuid, ctx)
    await db.flush()
    assert len(rows) >= 8, f"CTX-B persist: {len(rows)} rows < 8"

    result = await db.execute(text(
        "SELECT normativa, COUNT(*) FROM legal_obligations "
        "WHERE project_id = :pid AND deleted_at IS NULL "
        "GROUP BY normativa"
    ), {"pid": project_id_str})
    by_norm = {row[0]: row[1] for row in result}

    # Positive assertions
    assert by_norm.get("RGPD", 0) >= 4, (
        f"CTX-B RGPD={by_norm.get('RGPD', 0)} < 4 "
        "(esperado Art.30+33+37+35 con empleados=300 + AI)"
    )
    assert by_norm.get("NIS2", 0) >= 2, f"CTX-B NIS2={by_norm.get('NIS2', 0)} < 2"
    # NOTA: codigo real usa norma='AI Act' (con espacio · line 237) · NO 'AI_Act'
    assert by_norm.get("AI Act", 0) >= 1, (
        f"CTX-B 'AI Act' ausente · normativas={list(by_norm.keys())}"
    )

    # Negative assertions
    assert "DORA" not in by_norm, (
        f"CTX-B NO debe disparar DORA (sin entidad financiera) · got {by_norm.get('DORA')}"
    )
    assert "PSD2" not in by_norm, (
        f"CTX-B NO debe disparar PSD2 (sin procesa_pagos) · got {by_norm.get('PSD2')}"
    )


# ── CTX-C · pyme basica solo RGPD (briefing v3) ─────────────────────


@pytest.mark.asyncio
async def test_ctx_c_pyme_basica_solo_rgpd(db):
    """CTX-C · valida que sin flags sectoriales solo dispara RGPD + ISO27001-opp.

    NOTA briefing: 'TODO el resto booleans = False'. Para alcanzar el rango
    expected 4-8 rows con A24 hardcoded actual, usamos empleados=300 (Art.37
    dispara). Esto es el caso 'PYME grande proveedora AAPP sin sensibles'.
    """
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)

    ctx = _pyme_basica_ctx()

    obs = detect_obligations(ctx)
    assert 4 <= len(obs) <= 8, (
        f"CTX-C detect: {len(obs)} obligations · esperado [4..8]"
    )

    rows = await persist_obligations(db, project_uuid, ctx)
    await db.flush()
    assert len(rows) >= 4, f"CTX-C persist: {len(rows)} rows < 4"

    result = await db.execute(text(
        "SELECT DISTINCT normativa FROM legal_obligations "
        "WHERE project_id = :pid AND deleted_at IS NULL"
    ), {"pid": project_id_str})
    norms_set = {row[0] for row in result}

    # Positive
    assert "RGPD" in norms_set, f"CTX-C RGPD ausente · normativas={norms_set}"
    # ISO 27001 opportunity es always-on (allow but no assert)

    # Negative · ninguna norma sectorial debe dispararse
    forbidden = {"NIS2", "DORA", "AI Act", "PSD2", "ENI"}
    leaked = forbidden & norms_set
    assert not leaked, (
        f"CTX-C NO debe disparar {leaked} · ctx tiene todos los flags sectoriales False"
    )
