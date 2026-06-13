"""Tests del control-plane del agente · m_remediation (ADR-055 Fase 3).

Ciclo completo: issue → redeem → enqueue (firmado) → poll → report (firmado) →
job avanza → revoke (kill-switch). Más caminos de error (token malo · firma de
report inválida · GUARDED sin autorización · kill-switch global).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.motors.m_remediation.agent_service as agent_service_mod
from backend.app.motors.m_remediation.agent_protocol import (
    generate_keypair,
    sign_payload,
    validate_command,
    verify_payload,
)
from backend.app.motors.m_remediation.agent_service import (
    AgentAuthError,
    EnrollmentError,
    RemediationAgentService,
    get_server_keypair,
)
from backend.app.motors.m_remediation.models import RemediationJobStatus
from backend.app.motors.m_remediation.service import (
    AuthorizationRequiredError,
    RemediationDisabledError,
    RemediationService,
)
from backend.tests.conftest import setup_test_project


@pytest.fixture(autouse=True)
def _server_key_and_global(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FULKRO_REMEDIATION_ENABLED", "true")
    monkeypatch.setenv("FULKRO_REMEDIATION_SIGNING_KEY", "11" * 32)
    agent_service_mod._SERVER_KEYPAIR = None
    yield
    agent_service_mod._SERVER_KEYPAIR = None


async def _enroll_active_agent(db: AsyncSession, project_uuid: uuid.UUID):
    """Helper: issue + redeem → (agent, agent_token, apriv, apub)."""
    svc = RemediationAgentService(db)
    agent, token = await svc.issue_enrollment(
        project_id=project_uuid, hostname="host-1",
    )
    apriv, apub = generate_keypair()
    agent, agent_token, server_pub_hex = await svc.redeem_enrollment(
        token=token, agent_pubkey_hex=apub.hex(), agent_version="1.0.0",
    )
    assert agent.status == "active"
    assert server_pub_hex == get_server_keypair()[1].hex()
    return agent, agent_token, apriv, apub


@pytest.mark.asyncio
async def test_full_agent_cycle(db: AsyncSession) -> None:
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    svc = RemediationAgentService(db)
    rem = RemediationService(db)

    agent, agent_token, apriv, _apub = await _enroll_active_agent(db, project_uuid)

    # Host job SAFE_AUTO.
    job = await rem.create_job(
        project_id=project_uuid,
        action_type="harden_sshd_root_login",
        source_kind="host_finding",
        agent_id=agent.id,
        target_ref="srv-1",
    )
    assert job.tier == "safe_auto"

    # Encolar comando firmado.
    cmd = await svc.enqueue_command(agent=agent, job=job)
    assert cmd.server_signature
    server_pub = get_server_keypair()[1]
    payload = svc._command_payload(cmd)
    assert verify_payload(server_pub, payload, cmd.server_signature)

    # Poll: el agente recibe el comando y valida (allowlist + firma).
    commands = await svc.poll_commands(agent)
    assert len(commands) == 1
    c = commands[0]
    # El guard del agente NO lanza para un comando válido.
    validate_command(
        server_public_raw=bytes.fromhex(c["server_pubkey_hex"]),
        command_payload=c["payload"],
        signature_hex=c["server_signature"],
    )

    # Report firmado por el agente → job avanza a succeeded.
    result = {"outcome": "succeeded", "detail": "PermitRootLogin no"}
    report_payload = {"command_id": c["command_id"], "result": result}
    report_sig = sign_payload(apriv, report_payload)
    reported = await svc.report_command(
        agent=agent,
        command_id=uuid.UUID(c["command_id"]),
        result=result,
        report_signature=report_sig,
    )
    assert reported.status == "reported"

    advanced = await rem.get_job(job.id)
    assert advanced.status == RemediationJobStatus.SUCCEEDED.value

    # Poll de nuevo → ya no hay pendientes.
    assert await svc.poll_commands(agent) == []


@pytest.mark.asyncio
async def test_redeem_bad_token_fails(db: AsyncSession) -> None:
    await setup_test_project(db)
    svc = RemediationAgentService(db)
    _, apub = generate_keypair()
    with pytest.raises(EnrollmentError):
        await svc.redeem_enrollment(
            token="token-inexistente", agent_pubkey_hex=apub.hex(),
        )


@pytest.mark.asyncio
async def test_revoke_is_killswitch(db: AsyncSession) -> None:
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    svc = RemediationAgentService(db)
    agent, agent_token, _apriv, _apub = await _enroll_active_agent(db, project_uuid)

    await svc.revoke_agent(agent.id)
    # Tras revocar, el token deja de autenticar.
    with pytest.raises(AgentAuthError):
        await svc.authenticate_agent(agent_token)


@pytest.mark.asyncio
async def test_report_bad_signature_rejected(db: AsyncSession) -> None:
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    svc = RemediationAgentService(db)
    rem = RemediationService(db)
    agent, _agent_token, _apriv, _apub = await _enroll_active_agent(db, project_uuid)
    job = await rem.create_job(
        project_id=project_uuid, action_type="harden_sshd_root_login",
        source_kind="host_finding", agent_id=agent.id, target_ref="srv-1",
    )
    cmd = await svc.enqueue_command(agent=agent, job=job)

    # Firma de otra clave (no la del agente) → rechazada.
    other_priv, _ = generate_keypair()
    result = {"outcome": "succeeded"}
    bad_sig = sign_payload(other_priv, {"command_id": str(cmd.id), "result": result})
    with pytest.raises(AgentAuthError):
        await svc.report_command(
            agent=agent, command_id=cmd.id, result=result, report_signature=bad_sig,
        )


@pytest.mark.asyncio
async def test_guarded_requires_authorization(db: AsyncSession) -> None:
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    svc = RemediationAgentService(db)
    rem = RemediationService(db)
    agent, _t, _ap, _au = await _enroll_active_agent(db, project_uuid)

    job = await rem.create_job(
        project_id=project_uuid, action_type="apply_package_security_update",
        source_kind="host_finding", agent_id=agent.id, target_ref="srv-1",
    )
    assert job.tier == "guarded"
    assert job.status == RemediationJobStatus.AWAITING_AUTHORIZATION.value

    # Sin autorizar → enqueue rechazado.
    with pytest.raises(AuthorizationRequiredError):
        await svc.enqueue_command(agent=agent, job=job)

    # Autorizar → ahora encola.
    await rem.authorize_job(job.id, user_id=uuid.uuid4())
    job = await rem.get_job(job.id)
    cmd = await svc.enqueue_command(agent=agent, job=job)
    assert cmd.server_signature


@pytest.mark.asyncio
async def test_killswitch_global_off_blocks_enqueue(
    db: AsyncSession, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, pid = await setup_test_project(db)
    project_uuid = uuid.UUID(pid)
    svc = RemediationAgentService(db)
    rem = RemediationService(db)
    agent, _t, _ap, _au = await _enroll_active_agent(db, project_uuid)
    job = await rem.create_job(
        project_id=project_uuid, action_type="harden_sshd_root_login",
        source_kind="host_finding", agent_id=agent.id, target_ref="srv-1",
    )
    monkeypatch.delenv("FULKRO_REMEDIATION_ENABLED", raising=False)
    with pytest.raises(RemediationDisabledError):
        await svc.enqueue_command(agent=agent, job=job)
