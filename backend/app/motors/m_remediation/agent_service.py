"""Control-plane del agente on-prem · m_remediation (ADR-055 Fase 3).

Flujo:
  admin issue_enrollment → (token de un solo uso)
  agente redeem_enrollment(token, su_pubkey) → (agent_token + server_pubkey pin)
  admin/servicio enqueue_command(agent, host_job) → comando FIRMADO por el servidor
  agente poll_commands(agent_token) → recibe comandos firmados (marca delivered)
  agente report_command(result FIRMADO por el agente) → avanza el job
  admin revoke_agent → kill-switch (deja de recibir comandos)

Resolución del agente por token CRUZA RLS vía funciones SECURITY DEFINER
(fn_resolve_remediation_agent / fn_resolve_remediation_enrollment). El token ES
la autenticación; tras resolverlo se fija el contexto de proyecto (set_tenant_context).
"""
from __future__ import annotations

import hashlib
import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.audit_writer import emit_audit_log
from backend.app.database import set_tenant_context
from backend.app.motors.m_remediation.agent_models import (
    RemediationAgent,
    RemediationAgentCommand,
    RemediationAgentCommandStatus,
    RemediationAgentStatus,
)
from backend.app.motors.m_remediation.agent_protocol import (
    PLAYBOOK_ALLOWLIST,
    generate_keypair,
    public_from_private,
    sign_payload,
    verify_payload,
)
from backend.app.motors.m_remediation.catalog import get_action_spec
from backend.app.motors.m_remediation.models import (
    TERMINAL_JOB_STATES,
    RemediationJob,
    RemediationJobStatus,
)
from backend.app.motors.m_remediation.policy import global_remediation_enabled
from backend.app.motors.m_remediation.service import (
    AuthorizationRequiredError,
    RemediationDisabledError,
)

logger = logging.getLogger(__name__)

_SERVER_KEYPAIR: tuple[bytes, bytes] | None = None


def get_server_keypair() -> tuple[bytes, bytes]:
    """Keypair Ed25519 del servidor (firma comandos). (priv32, pub32).

    PROD: define `FULKRO_REMEDIATION_SIGNING_KEY` (hex de 32 bytes) para que la
    clave sea ESTABLE entre reinicios (los agentes fijan la pública en el
    enrollment). Sin env → clave efímera (solo dev · los agentes no verificarían
    tras un reinicio del servidor).
    """
    global _SERVER_KEYPAIR
    if _SERVER_KEYPAIR is not None:
        return _SERVER_KEYPAIR
    seed = os.getenv("FULKRO_REMEDIATION_SIGNING_KEY")
    if seed:
        priv = bytes.fromhex(seed.strip())
        pub = public_from_private(priv)
    else:
        priv, pub = generate_keypair()
        logger.warning(
            "FULKRO_REMEDIATION_SIGNING_KEY no definido · usando clave efímera "
            "(solo dev · en prod los agentes no podrán verificar tras reinicio)",
        )
    _SERVER_KEYPAIR = (priv, pub)
    return _SERVER_KEYPAIR


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AgentServiceError(Exception):
    pass


class EnrollmentError(AgentServiceError):
    pass


class AgentAuthError(AgentServiceError):
    pass


_OUTCOME_TO_JOB_STATUS: dict[str, RemediationJobStatus] = {
    "succeeded": RemediationJobStatus.SUCCEEDED,
    "skipped_compliant": RemediationJobStatus.SKIPPED_COMPLIANT,
    "rolled_back": RemediationJobStatus.ROLLED_BACK,
    "failed": RemediationJobStatus.FAILED,
}


class RemediationAgentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── admin · enrollment ────────────────────────────────────────────────

    async def issue_enrollment(
        self,
        *,
        project_id: uuid.UUID,
        hostname: str,
        created_by_user_id: uuid.UUID | None = None,
        client_id: uuid.UUID | None = None,
        ttl_minutes: int = 60,
    ) -> tuple[RemediationAgent, str]:
        """Crea un agente PENDING + token de enrollment de un solo uso.

        Devuelve (agent, token_plaintext). El token solo se muestra una vez.
        """
        token = secrets.token_urlsafe(32)
        agent = RemediationAgent(
            project_id=project_id,
            client_id=client_id,
            hostname=hostname,
            status=RemediationAgentStatus.PENDING.value,
            enrollment_token_hash=_sha256(token),
            enrollment_expires_at=_now() + timedelta(minutes=ttl_minutes),
            created_by_user_id=created_by_user_id,
        )
        self.db.add(agent)
        await self.db.flush()
        await self._audit(agent, "remediation.agent.enroll_issued")
        return agent, token

    async def redeem_enrollment(
        self,
        *,
        token: str,
        agent_pubkey_hex: str,
        agent_version: str | None = None,
    ) -> tuple[RemediationAgent, str, str]:
        """El agente canjea el token + fija su pubkey. Devuelve
        (agent, agent_token_plaintext, server_pubkey_hex).
        """
        row = (
            await self.db.execute(
                text(
                    "SELECT agent_id, project_id, status, expires_at "
                    "FROM fn_resolve_remediation_enrollment(:th)"
                ),
                {"th": _sha256(token)},
            )
        ).first()
        if row is None:
            raise EnrollmentError("Token de enrollment inválido.")
        agent_id, project_id, status, expires_at = row
        if status != RemediationAgentStatus.PENDING.value:
            raise EnrollmentError("Token ya canjeado o agente revocado.")
        if expires_at is not None and expires_at < _now():
            raise EnrollmentError("Token de enrollment caducado.")

        await set_tenant_context(self.db, project_id=project_id)
        agent = await self.db.get(RemediationAgent, agent_id)
        if agent is None:
            raise EnrollmentError("Agente no encontrado.")

        agent_token = secrets.token_urlsafe(32)
        agent.status = RemediationAgentStatus.ACTIVE.value
        agent.agent_pubkey_hex = agent_pubkey_hex
        agent.agent_token_hash = _sha256(agent_token)
        agent.enrollment_token_hash = None  # un solo uso
        agent.enrolled_at = _now()
        agent.last_heartbeat_at = _now()
        agent.agent_version = agent_version
        agent.capabilities = sorted(PLAYBOOK_ALLOWLIST)
        await self.db.flush()
        await self._audit(agent, "remediation.agent.enrolled")

        _, server_pub = get_server_keypair()
        return agent, agent_token, server_pub.hex()

    # ── agente · auth ─────────────────────────────────────────────────────

    async def authenticate_agent(self, agent_token: str) -> RemediationAgent:
        """Resuelve el agente por su token bearer (cruza RLS) + fija contexto."""
        row = (
            await self.db.execute(
                text(
                    "SELECT agent_id, project_id, status, agent_pubkey_hex "
                    "FROM fn_resolve_remediation_agent(:th)"
                ),
                {"th": _sha256(agent_token)},
            )
        ).first()
        if row is None:
            raise AgentAuthError("Token de agente inválido.")
        agent_id, project_id, status, _pub = row
        if status != RemediationAgentStatus.ACTIVE.value:
            raise AgentAuthError("Agente revocado o no activo.")
        await set_tenant_context(self.db, project_id=project_id)
        agent = await self.db.get(RemediationAgent, agent_id)
        if agent is None:
            raise AgentAuthError("Agente no encontrado.")
        return agent

    # ── encolar comando firmado (desde un host job) ───────────────────────

    def _command_payload(self, cmd: RemediationAgentCommand) -> dict:
        return {
            "command_id": str(cmd.id),
            "agent_id": str(cmd.agent_id),
            "project_id": str(cmd.project_id),
            "playbook_id": cmd.playbook_id,
            "params": cmd.params or {},
            "issued_at": cmd.issued_at.isoformat() if cmd.issued_at else "",
        }

    async def enqueue_command(
        self, *, agent: RemediationAgent, job: RemediationJob,
    ) -> RemediationAgentCommand:
        """Encola un comando FIRMADO para el agente desde un host job.

        Guards (fail-closed):
          - kill-switch global ON
          - agente ACTIVE
          - playbook en la allowlist
          - GUARDED → requiere autorización previa
        """
        if not global_remediation_enabled():
            raise RemediationDisabledError(
                "Remediación deshabilitada por kill-switch global.",
            )
        if agent.status != RemediationAgentStatus.ACTIVE.value:
            raise AgentServiceError("Agente no activo.")
        if job.action_type not in PLAYBOOK_ALLOWLIST:
            raise AgentServiceError(
                f"Playbook no permitido: {job.action_type}",
            )
        spec = get_action_spec(job.action_type)
        if spec is not None and spec.tier.value == "guarded" and job.authorized_at is None:
            raise AuthorizationRequiredError(
                "Playbook GUARDED · requiere autorización previa.",
            )

        cmd = RemediationAgentCommand(
            project_id=agent.project_id,
            agent_id=agent.id,
            job_id=job.id,
            playbook_id=job.action_type,
            params=job.params,
            status=RemediationAgentCommandStatus.PENDING.value,
            server_signature="",
        )
        self.db.add(cmd)
        await self.db.flush()  # asigna id + issued_at

        priv, _ = get_server_keypair()
        cmd.server_signature = sign_payload(priv, self._command_payload(cmd))
        await self.db.flush()
        await self._audit_cmd(cmd, "remediation.agent.command_issued")
        return cmd

    # ── agente · poll + report ────────────────────────────────────────────

    async def poll_commands(self, agent: RemediationAgent) -> list[dict]:
        """Devuelve los comandos pendientes (los marca delivered) + heartbeat."""
        res = await self.db.execute(
            select(RemediationAgentCommand)
            .where(
                RemediationAgentCommand.agent_id == agent.id,
                RemediationAgentCommand.status
                == RemediationAgentCommandStatus.PENDING.value,
            )
            .order_by(RemediationAgentCommand.created_at.asc())
        )
        cmds = list(res.scalars().all())
        _, server_pub = get_server_keypair()
        out: list[dict] = []
        for cmd in cmds:
            cmd.status = RemediationAgentCommandStatus.DELIVERED.value
            cmd.delivered_at = _now()
            out.append(
                {
                    "command_id": str(cmd.id),
                    "payload": self._command_payload(cmd),
                    "server_signature": cmd.server_signature,
                    "server_pubkey_hex": server_pub.hex(),
                }
            )
        agent.last_heartbeat_at = _now()
        await self.db.flush()
        return out

    async def report_command(
        self,
        *,
        agent: RemediationAgent,
        command_id: uuid.UUID,
        result: dict,
        report_signature: str,
    ) -> RemediationAgentCommand:
        """El agente reporta el resultado (firmado por él) · avanza el job."""
        cmd = await self.db.get(RemediationAgentCommand, command_id)
        if cmd is None or cmd.agent_id != agent.id:
            raise AgentServiceError("Comando no encontrado.")

        report_payload = {"command_id": str(cmd.id), "result": result}
        if not agent.agent_pubkey_hex or not verify_payload(
            bytes.fromhex(agent.agent_pubkey_hex), report_payload, report_signature,
        ):
            raise AgentAuthError("Firma del report inválida · rechazado.")

        cmd.result = result
        cmd.report_signature = report_signature
        cmd.status = RemediationAgentCommandStatus.REPORTED.value
        cmd.reported_at = _now()
        await self.db.flush()

        # Avanzar el host job según el outcome reportado.
        if cmd.job_id is not None:
            job = await self.db.get(RemediationJob, cmd.job_id)
            if job is not None and job.status not in TERMINAL_JOB_STATES:
                outcome = str(result.get("outcome", "failed"))
                target = _OUTCOME_TO_JOB_STATUS.get(
                    outcome, RemediationJobStatus.FAILED,
                )
                job.status = target.value
                job.finished_at = _now()
                job.result = result
                if target == RemediationJobStatus.FAILED:
                    job.error_message = str(result.get("error", "fallo en el agente"))
                await self.db.flush()

        await self._audit_cmd(cmd, "remediation.agent.command_reported")
        return cmd

    # ── admin · gestión ───────────────────────────────────────────────────

    async def list_agents(self, project_id: uuid.UUID) -> list[RemediationAgent]:
        res = await self.db.execute(
            select(RemediationAgent)
            .where(
                RemediationAgent.project_id == project_id,
                RemediationAgent.deleted_at.is_(None),
            )
            .order_by(RemediationAgent.created_at.desc())
        )
        return list(res.scalars().all())

    async def revoke_agent(self, agent_id: uuid.UUID) -> RemediationAgent:
        agent = await self.db.get(RemediationAgent, agent_id)
        if agent is None:
            raise AgentServiceError("Agente no encontrado.")
        agent.status = RemediationAgentStatus.REVOKED.value
        agent.revoked_at = _now()
        agent.agent_token_hash = None  # invalida el canal
        await self.db.flush()
        await self._audit(agent, "remediation.agent.revoked")
        return agent

    # ── audit ─────────────────────────────────────────────────────────────

    async def _audit(self, agent: RemediationAgent, accion: str) -> None:
        await emit_audit_log(
            self.db,
            tabla="remediation_agents",
            registro_id=agent.id,
            accion=accion[:60],
            project_id=agent.project_id,
            client_id=agent.client_id,
            payload_new={"hostname": agent.hostname, "status": agent.status},
        )

    async def _audit_cmd(
        self, cmd: RemediationAgentCommand, accion: str,
    ) -> None:
        await emit_audit_log(
            self.db,
            tabla="remediation_agent_commands",
            registro_id=cmd.id,
            accion=accion[:60],
            project_id=cmd.project_id,
            payload_new={
                "playbook_id": cmd.playbook_id,
                "status": cmd.status,
                "agent_id": str(cmd.agent_id),
            },
        )
