"""LUCIA federación CCN-CERT real · SAN-C.MB-10.3.

LUCIA es la herramienta CCN-CERT para gestión de incidentes de
seguridad. La federación permite a entidades del sector público y NIS2
notificar incidentes significativos vía API REST.

Diseño FULKRO:

* FULKRO **NO** tiene credenciales propias LUCIA · es consultor privado.
* El cliente (entidad sector público / NIS2) aporta sus credenciales
  OAuth (organization_id + client_id + client_secret) registradas en
  CCN-CERT.
* FULKRO orquesta el flow: validar formato CCN-STIC 845 + submit +
  polling status + audit trail.

Fallback honesto: si el cliente no aporta credenciales (caso típico
hasta que las gestiona), las submissions se persisten en estado
``pending_credentials`` con artefacto JSON canónico que el cliente
puede subir manualmente al portal LUCIA web vía certificado FNMT/DNIe.

Refs: SAN-C.MB-10.3 · CCN-STIC 845
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx
from cryptography.fernet import Fernet
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession


LUCIA_BASE_URL_DEFAULT = "https://lucia.ccn-cert.cni.es/api"
SUBMISSION_TIMEOUT_S = 30


@dataclass(slots=True)
class LuciaCredentials:
    """Credenciales OAuth del cliente registradas en LUCIA."""

    project_id: uuid.UUID
    organization_id: str
    client_id: str
    client_secret: str  # plaintext en memoria · cifrado at-rest en BD
    refresh_token: str | None = None
    endpoint_base_url: str = LUCIA_BASE_URL_DEFAULT


@dataclass(slots=True)
class LuciaIncidentPayload:
    """Payload incidente formato CCN-STIC 845."""

    incident_id: uuid.UUID
    severity: str  # BAJA · MEDIA · ALTA · CRITICA
    title: str
    description: str
    detected_at: datetime
    affected_systems: list[str]
    timeline: list[dict[str, Any]]
    classification: str  # taxonomy CCN-CERT
    impact_assessment: str
    contention_actions: list[str]


@dataclass(slots=True)
class LuciaSubmissionResult:
    """Resultado de un submit (real o mock pending_credentials)."""

    submission_id_local: uuid.UUID
    submission_id_remote: str | None
    status: str
    artifact_path: str | None
    artifact_hash: str
    error_detail: str | None = None


def _fernet_from_master_key(master_key: str) -> Fernet:
    return Fernet(master_key.encode())


def encrypt_credentials_field(plaintext: str, master_key: str) -> str:
    return _fernet_from_master_key(master_key).encrypt(plaintext.encode()).decode()


def decrypt_credentials_field(ciphertext: str, master_key: str) -> str:
    return _fernet_from_master_key(master_key).decrypt(ciphertext.encode()).decode()


def build_canonical_payload(payload: LuciaIncidentPayload) -> dict[str, Any]:
    """Construye payload JSON canónico CCN-STIC 845."""
    return {
        "@schema": "CCN-STIC-845-incident-v1",
        "incident_id": str(payload.incident_id),
        "severity": payload.severity,
        "title": payload.title,
        "description": payload.description,
        "detected_at": payload.detected_at.astimezone(timezone.utc).isoformat(),
        "affected_systems": payload.affected_systems,
        "timeline": payload.timeline,
        "classification": payload.classification,
        "impact_assessment": payload.impact_assessment,
        "contention_actions": payload.contention_actions,
    }


def hash_payload(canonical: dict[str, Any]) -> str:
    body = json.dumps(canonical, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(body).hexdigest()


# ── BD helpers ─────────────────────────────────────────────────────────


async def fetch_credentials(
    db: AsyncSession,
    project_id: uuid.UUID,
    master_key: str,
) -> LuciaCredentials | None:
    """Carga credenciales LUCIA del proyecto si existen + descifra."""
    row = await db.execute(
        sa_text(
            "SELECT organization_id_lucia, client_id_oauth, "
            "       client_secret_encrypted, refresh_token_encrypted, "
            "       endpoint_base_url "
            "FROM lucia_credentials WHERE project_id = :pid"
        ),
        {"pid": str(project_id)},
    )
    record = row.first()
    if record is None:
        return None
    secret = decrypt_credentials_field(record[2], master_key)
    refresh = (
        decrypt_credentials_field(record[3], master_key) if record[3] else None
    )
    return LuciaCredentials(
        project_id=project_id,
        organization_id=record[0],
        client_id=record[1],
        client_secret=secret,
        refresh_token=refresh,
        endpoint_base_url=record[4] or LUCIA_BASE_URL_DEFAULT,
    )


async def persist_submission(
    db: AsyncSession,
    project_id: uuid.UUID,
    incident_id: uuid.UUID | None,
    canonical_payload: dict[str, Any],
    status: str,
    submission_id_remote: str | None = None,
    response_payload: dict[str, Any] | None = None,
    error_detail: str | None = None,
) -> uuid.UUID:
    """Inserta lucia_submissions row · devuelve id local."""
    submission_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    await db.execute(
        sa_text(
            "INSERT INTO lucia_submissions "
            "(id, project_id, incident_id, submission_id_remote, status, "
            " payload_jsonb, response_jsonb, error_detail, submitted_at) "
            "VALUES (:id, :pid, :iid, :rid, :st, "
            "        CAST(:pl AS jsonb), CAST(:rsp AS jsonb), :err, :sub)"
        ),
        {
            "id": str(submission_id),
            "pid": str(project_id),
            "iid": str(incident_id) if incident_id else None,
            "rid": submission_id_remote,
            "st": status,
            "pl": json.dumps(canonical_payload),
            "rsp": json.dumps(response_payload) if response_payload else None,
            "err": error_detail,
            "sub": now if status not in {"pending_credentials"} else None,
        },
    )
    return submission_id


# ── Federation client ─────────────────────────────────────────────────


async def submit_incident(
    db: AsyncSession,
    project_id: uuid.UUID,
    payload: LuciaIncidentPayload,
    master_key: str,
    *,
    db_incident_id: uuid.UUID | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> LuciaSubmissionResult:
    """Submit un incidente a LUCIA federación.

    Si el proyecto tiene credenciales registradas (``lucia_credentials``),
    realiza POST real con OAuth bearer · si no, persiste el payload con
    status ``pending_credentials`` para que el cliente lo suba manualmente
    al portal LUCIA web (fallback honesto).

    ``db_incident_id`` es el FK a ``incidents`` table (opcional · si el
    submit nace de un incident persistido). ``payload.incident_id`` es
    el ID semántico CCN-STIC 845 que se incluye en el payload JSON.
    """
    canonical = build_canonical_payload(payload)
    artifact_hash = hash_payload(canonical)
    artifact_path = (
        f"exports/lucia/{project_id}/incident_{payload.incident_id}_"
        f"{artifact_hash[:8]}.json"
    )

    # Validar FK: solo settear si existe en incidents · evita FK violation
    fk_incident_id = db_incident_id
    if fk_incident_id is not None:
        check = await db.execute(
            sa_text("SELECT 1 FROM incidents WHERE id = :iid LIMIT 1"),
            {"iid": str(fk_incident_id)},
        )
        if check.first() is None:
            fk_incident_id = None

    creds = await fetch_credentials(db, project_id, master_key)

    if creds is None:
        sub_id = await persist_submission(
            db,
            project_id=project_id,
            incident_id=fk_incident_id,
            canonical_payload=canonical,
            status="pending_credentials",
        )
        return LuciaSubmissionResult(
            submission_id_local=sub_id,
            submission_id_remote=None,
            status="pending_credentials",
            artifact_path=artifact_path,
            artifact_hash=artifact_hash,
            error_detail=(
                "Cliente no ha aportado credenciales LUCIA. Subir el "
                "JSON canónico manualmente al portal LUCIA con certificado "
                "FNMT/DNIe."
            ),
        )

    own_client = http_client is None
    client = http_client or httpx.AsyncClient(timeout=SUBMISSION_TIMEOUT_S)
    try:
        try:
            resp = await client.post(
                f"{creds.endpoint_base_url.rstrip('/')}/v1/incidents",
                json=canonical,
                headers={
                    "Authorization": f"Bearer {creds.client_secret}",
                    "X-Organization-Id": creds.organization_id,
                    "Content-Type": "application/json",
                },
            )
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            sub_id = await persist_submission(
                db,
                project_id=project_id,
                incident_id=fk_incident_id,
                canonical_payload=canonical,
                status="error",
                error_detail=f"HTTP error: {exc!s}",
            )
            return LuciaSubmissionResult(
                submission_id_local=sub_id,
                submission_id_remote=None,
                status="error",
                artifact_path=artifact_path,
                artifact_hash=artifact_hash,
                error_detail=str(exc),
            )

        if resp.status_code in (200, 201, 202):
            response_data = resp.json()
            remote_id = response_data.get("submission_id") or response_data.get("id")
            sub_id = await persist_submission(
                db,
                project_id=project_id,
                incident_id=fk_incident_id,
                canonical_payload=canonical,
                status="sent",
                submission_id_remote=remote_id,
                response_payload=response_data,
            )
            return LuciaSubmissionResult(
                submission_id_local=sub_id,
                submission_id_remote=remote_id,
                status="sent",
                artifact_path=artifact_path,
                artifact_hash=artifact_hash,
            )
        else:
            sub_id = await persist_submission(
                db,
                project_id=project_id,
                incident_id=fk_incident_id,
                canonical_payload=canonical,
                status="error",
                error_detail=(
                    f"LUCIA HTTP {resp.status_code}: {resp.text[:500]}"
                ),
            )
            return LuciaSubmissionResult(
                submission_id_local=sub_id,
                submission_id_remote=None,
                status="error",
                artifact_path=artifact_path,
                artifact_hash=artifact_hash,
                error_detail=f"HTTP {resp.status_code}",
            )
    finally:
        if own_client:
            await client.aclose()
