"""Writer de remediación Azure (ARM) · m_remediation (ADR-055).

Endurecimiento de recursos Azure vía Azure Resource Manager (management.azure.com).
Credenciales = SP del conector ({tenant_id, client_id, client_secret}). La identidad
(MFA) de Azure es Entra → se cubre con el writer Microsoft 365 (mismo Graph).

`target_ref` = resourceId completo de la cuenta de almacenamiento
(/subscriptions/.../resourceGroups/.../providers/Microsoft.Storage/storageAccounts/X).

Operaciones ARM por helpers (`_arm_get`/`_arm_patch`/`_get_token`) mockeables en test.
Validación contra suscripción viva en el alta del cliente.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

ARM = "https://management.azure.com"
STORAGE_API = "2023-01-01"

# action_type → (propiedad ARM, valor objetivo, clave de assertion)
_ACTIONS: dict[str, dict[str, Any]] = {
    "azure_storage_disable_public_blob": {
        "prop": "allowBlobPublicAccess",
        "target": False,
        "assertion": "public_blob_disabled",
    },
    "azure_storage_require_https": {
        "prop": "supportsHttpsTrafficOnly",
        "target": True,
        "assertion": "https_required",
    },
}


class AzureRemediationWriter:
    provider = "azure"

    def __init__(self, credentials: dict) -> None:
        self.tenant_id = credentials["tenant_id"]
        self.client_id = credentials["client_id"]
        self.client_secret = credentials["client_secret"]
        self.login_base = credentials.get(
            "login_base", "https://login.microsoftonline.com",
        )
        self._token: str | None = None

    async def _get_token(self) -> str:
        if self._token:
            return self._token
        url = f"{self.login_base}/{self.tenant_id}/oauth2/v2.0/token"
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(url, data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "https://management.azure.com/.default",
            })
            r.raise_for_status()
            self._token = r.json()["access_token"]
            return self._token

    async def _arm_get(self, resource_id: str) -> dict:
        token = await self._get_token()
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(
                f"{ARM}{resource_id}",
                headers={"Authorization": f"Bearer {token}"},
                params={"api-version": STORAGE_API},
            )
            r.raise_for_status()
            return r.json()

    async def _arm_patch(self, resource_id: str, body: dict) -> dict:
        token = await self._get_token()
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.patch(
                f"{ARM}{resource_id}",
                headers={"Authorization": f"Bearer {token}"},
                params={"api-version": STORAGE_API},
                json=body,
            )
            r.raise_for_status()
            return r.json() if r.content else {}

    def _cfg(self, action_type: str) -> dict[str, Any]:
        cfg = _ACTIONS.get(action_type)
        if cfg is None:
            raise ValueError(f"Acción Azure no soportada por el writer: {action_type}")
        return cfg

    async def read_state(self, action_type, target_ref, params) -> dict:
        cfg = self._cfg(action_type)
        res = await self._arm_get(target_ref)
        current = res.get("properties", {}).get(cfg["prop"])
        return {
            cfg["assertion"]: current == cfg["target"],
            "prev_value": current,
        }

    async def apply(self, action_type, target_ref, params) -> dict:
        cfg = self._cfg(action_type)
        await self._arm_patch(
            target_ref, {"properties": {cfg["prop"]: cfg["target"]}},
        )
        return {"applied": {cfg["prop"]: cfg["target"]}}

    async def rollback(self, action_type, target_ref, state_before) -> dict:
        cfg = self._cfg(action_type)
        prev = (state_before or {}).get("prev_value")
        await self._arm_patch(target_ref, {"properties": {cfg["prop"]: prev}})
        return {"restored": {cfg["prop"]: prev}}
