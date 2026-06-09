"""Tests · LLM enrichment SOLO afecta explanation_es (R1 INVIOLABLE).

Verifica:
- run_diagnosis NO invoca LLM (call to anthropic API mock counter == 0)
- Decisión severity + gap_type + raw_evidence es DETERMINISTIC
- Re-ejecutar diagnóstico con misma input produce mismo resultado
"""
from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import text

from backend.app.motors.m_cloud_connectors import (
    CloudConnectorProvider,
    CloudConnectorService,
    DiagnosticGapEngine,
)
from backend.tests.conftest import setup_test_project


async def _seed_resources_with_no_mfa(
    db, *, project_id: uuid.UUID, n_no_mfa: int = 3,
) -> None:
    """Crea connector + N usuarios sin MFA + 2 con MFA · seed determinístico."""
    svc = CloudConnectorService(db)
    connector = await svc.link_or_create_connector(
        project_id=project_id,
        provider=CloudConnectorProvider.MICROSOFT_365,
    )

    rows = []
    for i in range(n_no_mfa):
        rows.append({
            "id": str(uuid.uuid4()),
            "project_id": str(project_id),
            "connector_id": str(connector.id),
            "resource_type": "identity.user",
            "resource_external_id": f"user_no_mfa_{i}",
            "resource_name": f"User No MFA {i}",
            "attributes": '{"mfa_enabled": false, "is_active": true}',
        })
    for i in range(2):
        rows.append({
            "id": str(uuid.uuid4()),
            "project_id": str(project_id),
            "connector_id": str(connector.id),
            "resource_type": "identity.user",
            "resource_external_id": f"user_ok_{i}",
            "resource_name": f"User OK {i}",
            "attributes": '{"mfa_enabled": true, "is_active": true}',
        })

    for r in rows:
        await db.execute(
            text(
                "INSERT INTO cloud_resources "
                "(id, project_id, connector_id, resource_type, "
                "resource_external_id, resource_name, attributes) "
                "VALUES (:id, :project_id, :connector_id, :resource_type, "
                ":resource_external_id, :resource_name, "
                "CAST(:attributes AS JSONB))"
            ),
            r,
        )
    await db.flush()


@pytest.mark.asyncio
async def test_run_diagnosis_no_llm_call(db):
    """R1 INVIOLABLE: pipeline NO invoca anthropic.messages.create."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    await _seed_resources_with_no_mfa(db, project_id=pid)

    # Patch anthropic SDK al nivel del módulo · si el engine intentara
    # llamarlo, el mock contaría y este test fallaría
    with patch("anthropic.Anthropic") as anthropic_mock:
        engine = DiagnosticGapEngine(db)
        report = await engine.run_diagnosis(project_id=pid, category="BASICA")

    # 0 invocaciones a LLM
    assert anthropic_mock.call_count == 0
    # Pero gaps SI se generaron por reglas deterministic
    assert report.findings_emitted > 0
    assert "op.acc.6" in report.gap_codes


@pytest.mark.asyncio
async def test_run_diagnosis_idempotent_same_input_same_output(db):
    """Re-ejecutar 2x produce idéntico report (decisiones puras + UPSERT)."""
    _, project_id_str = await setup_test_project(db)
    pid = uuid.UUID(project_id_str)

    await _seed_resources_with_no_mfa(db, project_id=pid)
    engine = DiagnosticGapEngine(db)

    r1 = await engine.run_diagnosis(project_id=pid, category="MEDIA")
    r2 = await engine.run_diagnosis(project_id=pid, category="MEDIA")

    # Mismas reglas evaluadas + mismas medidas con gap
    assert r1.rules_evaluated == r2.rules_evaluated
    assert sorted(r1.gap_codes) == sorted(r2.gap_codes)
    # En la 2a iteración · gaps fueron actualizados (UPSERT) NO recreados
    assert r2.gaps_created == 0
    assert r2.gaps_updated >= r1.gaps_created
