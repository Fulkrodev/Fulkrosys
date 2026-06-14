"""Writer de remediación Microsoft 365 / Entra (Graph) · m_remediation (ADR-055).

Acciones de identidad vía Conditional Access (Graph). Credenciales = las del
conector M16 ({tenant_id, client_id, client_secret} · client_credentials).

Las operaciones Graph pasan por helpers (`_list_policies`/`_create_policy`/
`_update_policy`/`_delete_policy`/`_get_token`) para poder mockearlas en test sin
tenant real. La validación contra un tenant vivo se hace en el alta del cliente.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

GRAPH = "https://graph.microsoft.com/v1.0"

# action_type → configuración de la política de Acceso Condicional.
_POLICIES: dict[str, dict[str, str]] = {
    # FIX: displayNames DISTINTOS para las dos variantes del control MFA. Antes
    # ambas usaban "FULKRO-Require-MFA" y read_state/apply/rollback localizan la
    # política por displayName → al ejecutar la variante report-only sobre un
    # enforce ya activo, apply DEGRADABA la política de obligatoria (enabled) a
    # solo-informe sin que el operador lo percibiera (op.acc.6 desactivado de
    # hecho · verify lo daba verde). Políticas independientes evitan el cruce.
    "require_mfa_conditional_access": {
        "display": "FULKRO-Require-MFA-Report",
        "assertion": "mfa_required",
        "state": "enabledForReportingButNotEnforced",
        "kind": "mfa",
    },
    "require_mfa_enforce": {
        "display": "FULKRO-Require-MFA-Enforce",
        "assertion": "mfa_enforced",
        "state": "enabled",
        "kind": "mfa",
    },
    "disable_legacy_protocol": {
        "display": "FULKRO-Block-Legacy-Auth",
        "assertion": "legacy_auth_disabled",
        "state": "enabled",
        "kind": "legacy",
    },
}


class Microsoft365RemediationWriter:
    provider = "microsoft_365"

    def __init__(self, credentials: dict) -> None:
        self.tenant_id = credentials["tenant_id"]
        self.client_id = credentials["client_id"]
        self.client_secret = credentials["client_secret"]
        self.login_base = credentials.get(
            "login_base", "https://login.microsoftonline.com",
        )
        self._token: str | None = None

    # ── Graph helpers (mockeables en test) ────────────────────────────────

    async def _get_token(self) -> str:
        if self._token:
            return self._token
        url = f"{self.login_base}/{self.tenant_id}/oauth2/v2.0/token"
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(url, data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "https://graph.microsoft.com/.default",
            })
            r.raise_for_status()
            self._token = r.json()["access_token"]
            return self._token

    async def _graph(self, method: str, path: str, json: dict | None = None) -> dict:
        token = await self._get_token()
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.request(
                method, f"{GRAPH}{path}",
                headers={"Authorization": f"Bearer {token}"},
                json=json,
            )
            r.raise_for_status()
            if r.status_code == 204 or not r.content:
                return {}
            return r.json()

    async def _list_policies(self) -> list[dict]:
        data = await self._graph("GET", "/identity/conditionalAccess/policies")
        return data.get("value", [])

    async def _create_policy(self, body: dict) -> dict:
        return await self._graph("POST", "/identity/conditionalAccess/policies", json=body)

    async def _update_policy(self, policy_id: str, body: dict) -> dict:
        return await self._graph(
            "PATCH", f"/identity/conditionalAccess/policies/{policy_id}", json=body,
        )

    async def _delete_policy(self, policy_id: str) -> dict:
        return await self._graph(
            "DELETE", f"/identity/conditionalAccess/policies/{policy_id}",
        )

    # ── cuerpo de la política CA ──────────────────────────────────────────

    @staticmethod
    def _build_body(cfg: dict[str, str]) -> dict[str, Any]:
        if cfg["kind"] == "legacy":
            conditions = {
                "users": {"includeUsers": ["All"]},
                "applications": {"includeApplications": ["All"]},
                "clientAppTypes": ["exchangeActiveSync", "other"],
            }
            grant = {"operator": "OR", "builtInControls": ["block"]}
        else:
            conditions = {
                "users": {"includeUsers": ["All"]},
                "applications": {"includeApplications": ["All"]},
                "clientAppTypes": ["all"],
            }
            grant = {"operator": "OR", "builtInControls": ["mfa"]}
        return {
            "displayName": cfg["display"],
            "state": cfg["state"],
            "conditions": conditions,
            "grantControls": grant,
        }

    # ── interfaz RemediationWriter ────────────────────────────────────────

    def _cfg(self, action_type: str) -> dict[str, str]:
        cfg = _POLICIES.get(action_type)
        if cfg is None:
            raise ValueError(f"Acción M365 no soportada por el writer: {action_type}")
        return cfg

    async def read_state(self, action_type, target_ref, params) -> dict:
        cfg = self._cfg(action_type)
        pols = await self._list_policies()
        match = next((p for p in pols if p.get("displayName") == cfg["display"]), None)
        compliant = bool(match and match.get("state") == cfg["state"])
        return {
            cfg["assertion"]: compliant,
            "policy_id": match.get("id") if match else None,
            "existing": match,
        }

    async def apply(self, action_type, target_ref, params) -> dict:
        cfg = self._cfg(action_type)
        pols = await self._list_policies()
        match = next((p for p in pols if p.get("displayName") == cfg["display"]), None)
        if match:
            await self._update_policy(match["id"], {"state": cfg["state"]})
            return {"updated": match["id"]}
        created = await self._create_policy(self._build_body(cfg))
        return {"created": created.get("id")}

    async def rollback(self, action_type, target_ref, state_before) -> dict:
        cfg = self._cfg(action_type)
        existing = (state_before or {}).get("existing")
        pols = await self._list_policies()
        match = next((p for p in pols if p.get("displayName") == cfg["display"]), None)
        if not match:
            return {"noop": True}
        if existing:
            await self._update_policy(
                match["id"], {"state": existing.get("state", "disabled")},
            )
            return {"restored": True}
        await self._delete_policy(match["id"])
        return {"deleted": True}
