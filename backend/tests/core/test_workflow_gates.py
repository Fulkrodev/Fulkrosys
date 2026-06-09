"""Unit tests for workflow gates.

Each test temporarily re-enables gates (``FULKRO_SKIP_WORKFLOW_GATES``
is forced off) so the raise-path is exercised.
"""
from __future__ import annotations

import uuid

import pytest

from backend.app.core.workflow_gates import (
    WorkflowGateError,
    require_complete_audit_prep,
    require_frozen_dda,
    require_frozen_dda_if_needed,
    require_magerit_analysis,
    require_pentest_authorisation,
    require_signed_categorization,
    require_some_evidence,
)


@pytest.fixture
def gates_enforced(monkeypatch):
    monkeypatch.setenv("FULKRO_SKIP_WORKFLOW_GATES", "0")
    yield


@pytest.mark.asyncio
async def test_require_signed_categorization_raises_when_missing(db, gates_enforced):
    random_pid = uuid.uuid4()
    with pytest.raises(WorkflowGateError) as ei:
        await require_signed_categorization(db, random_pid)
    assert ei.value.gate == "signed_categorization"


@pytest.mark.asyncio
async def test_require_frozen_dda_raises_when_empty(db, gates_enforced):
    random_pid = uuid.uuid4()
    with pytest.raises(WorkflowGateError) as ei:
        await require_frozen_dda(db, random_pid)
    assert ei.value.gate == "frozen_dda"


@pytest.mark.asyncio
async def test_frozen_dda_bypassed_for_commercial_kind(db, gates_enforced):
    random_pid = uuid.uuid4()
    # Should NOT raise — commercial kinds skip the gate.
    await require_frozen_dda_if_needed(db, random_pid, "comercial")
    await require_frozen_dda_if_needed(db, random_pid, "anexo")


@pytest.mark.asyncio
async def test_require_complete_audit_prep_raises(db, gates_enforced):
    with pytest.raises(WorkflowGateError) as ei:
        await require_complete_audit_prep(db, uuid.uuid4())
    assert ei.value.gate == "complete_audit_prep"


@pytest.mark.asyncio
async def test_require_some_evidence_raises(db, gates_enforced):
    with pytest.raises(WorkflowGateError) as ei:
        await require_some_evidence(db, uuid.uuid4(), minimum=1)
    assert ei.value.gate == "require_some_evidence"


@pytest.mark.asyncio
async def test_require_magerit_analysis_raises(db, gates_enforced):
    with pytest.raises(WorkflowGateError) as ei:
        await require_magerit_analysis(db, uuid.uuid4())
    assert ei.value.gate == "magerit_analysis"


@pytest.mark.asyncio
async def test_require_pentest_authorisation_raises(db, gates_enforced):
    with pytest.raises(WorkflowGateError) as ei:
        await require_pentest_authorisation(db, uuid.uuid4())
    assert ei.value.gate == "pentest_authorisation"


@pytest.mark.asyncio
async def test_gates_skipped_when_env_set(db, monkeypatch):
    monkeypatch.setenv("FULKRO_SKIP_WORKFLOW_GATES", "1")
    # All gates should return None without raising even with no data.
    await require_signed_categorization(db, uuid.uuid4())
    await require_frozen_dda(db, uuid.uuid4())
    await require_complete_audit_prep(db, uuid.uuid4())
    await require_some_evidence(db, uuid.uuid4())
    await require_magerit_analysis(db, uuid.uuid4())
    await require_pentest_authorisation(db, uuid.uuid4())
