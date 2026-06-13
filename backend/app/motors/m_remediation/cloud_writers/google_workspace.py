"""Writer de remediación Google Workspace (Drive API) · m_remediation (ADR-055).

Restringe la compartición externa de una unidad compartida (Drive API · capacidad
real: restrictions.domainUsersOnly). Credenciales = service account con delegación
de dominio del conector ({service_account_info, admin_email}).

`target_ref` = driveId de la unidad compartida. Operaciones Drive por helpers
(`_drive_get`/`_drive_patch`/`_get_token`) mockeables en test. Validación contra
dominio vivo en el alta del cliente.
"""
from __future__ import annotations

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

DRIVE = "https://www.googleapis.com/drive/v3"

_ACTIONS: dict[str, dict[str, str]] = {
    "google_drive_restrict_external": {
        "assertion": "external_sharing_restricted",
    },
}


class GoogleWorkspaceRemediationWriter:
    provider = "google_workspace"

    def __init__(self, credentials: dict) -> None:
        self.service_account_info = credentials.get("service_account_info")
        self.admin_email = credentials.get("admin_email")
        self._token: str | None = None

    def _build_token_sync(self) -> str:
        from google.oauth2 import service_account  # type: ignore

        creds = service_account.Credentials.from_service_account_info(
            self.service_account_info,
            scopes=["https://www.googleapis.com/auth/drive"],
            subject=self.admin_email,
        )
        from google.auth.transport.requests import Request  # type: ignore

        creds.refresh(Request())
        return creds.token

    async def _get_token(self) -> str:
        if self._token:
            return self._token
        self._token = await asyncio.to_thread(self._build_token_sync)
        return self._token

    async def _drive_get(self, drive_id: str) -> dict:
        token = await self._get_token()
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(
                f"{DRIVE}/drives/{drive_id}",
                headers={"Authorization": f"Bearer {token}"},
                params={"useDomainAdminAccess": "true", "fields": "id,restrictions"},
            )
            r.raise_for_status()
            return r.json()

    async def _drive_patch(self, drive_id: str, body: dict) -> dict:
        token = await self._get_token()
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.patch(
                f"{DRIVE}/drives/{drive_id}",
                headers={"Authorization": f"Bearer {token}"},
                params={"useDomainAdminAccess": "true"},
                json=body,
            )
            r.raise_for_status()
            return r.json() if r.content else {}

    def _cfg(self, action_type: str) -> dict[str, str]:
        cfg = _ACTIONS.get(action_type)
        if cfg is None:
            raise ValueError(f"Acción Google no soportada por el writer: {action_type}")
        return cfg

    async def read_state(self, action_type, target_ref, params) -> dict:
        cfg = self._cfg(action_type)
        drive = await self._drive_get(target_ref)
        restrictions = drive.get("restrictions", {}) or {}
        return {
            cfg["assertion"]: bool(restrictions.get("domainUsersOnly")),
            "prev_restrictions": restrictions,
        }

    async def apply(self, action_type, target_ref, params) -> dict:
        self._cfg(action_type)
        await self._drive_patch(target_ref, {"restrictions": {"domainUsersOnly": True}})
        return {"applied": {"domainUsersOnly": True}}

    async def rollback(self, action_type, target_ref, state_before) -> dict:
        self._cfg(action_type)
        prev = (state_before or {}).get("prev_restrictions", {}) or {}
        await self._drive_patch(
            target_ref,
            {"restrictions": {"domainUsersOnly": bool(prev.get("domainUsersOnly", False))}},
        )
        return {"restored": prev}
