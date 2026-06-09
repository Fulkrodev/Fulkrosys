"""M22 Paso 6 — Microsoft 365 / Entra ID OAuth2 connector (authorization_code).

Enriquece el conector base M16 con:
- Authorization code flow (no client_credentials) para tenants con usuarios reales
- Scopes MVP: User.Read.All, Group.Read.All, Directory.Read.All,
  Reports.Read.All, SecurityEvents.Read.All
- Discoveries especificos Paso 6:
  · Usuarios (activos/inactivos/privilegiados)
  · Politicas de Acceso Condicional (CA)
  · Secure Score actual
  · MFA por usuario (v2.0 beta authenticationMethods)
  · Dispositivos Intune (managedDevices)
- Token cifrado en ConnectorConfig.encrypted_credentials
- Refresh token automatico si el access_token ha expirado

Para demos / tests sin credenciales reales, inyectar `fetcher_mock` al
construir la instancia — devuelve DTOs directamente sin tocar la red.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable, Optional

import httpx

from backend.app.motors.m16_onboarding.connectors.base import (
    ConnectorProvider,
    DiscoveredAssetDTO,
    DiscoveredIdentityDTO,
    DiscoveryResult,
)

logger = logging.getLogger(__name__)


GRAPH_BASE = "https://graph.microsoft.com/v1.0"
GRAPH_BETA = "https://graph.microsoft.com/beta"
LOGIN_BASE = "https://login.microsoftonline.com"

# Scopes MVP Paso 6 (delegated + application, se negocian via admin consent)
REQUIRED_SCOPES = [
    "User.Read.All",
    "Group.Read.All",
    "Directory.Read.All",
    "Reports.Read.All",
    "SecurityEvents.Read.All",
    "DeviceManagementManagedDevices.Read.All",
    "Policy.Read.All",
    "offline_access",
]

# Margen de refresh antes de expirar access_token (en segundos)
REFRESH_MARGIN_SECONDS = 120


# ════════════════════════════════════════════════════════════════════
# DTOs especificos Paso 6
# ════════════════════════════════════════════════════════════════════

@dataclass
class ConditionalAccessPolicy:
    policy_id: str
    display_name: str
    state: str  # enabled | disabled | enabledForReportingButNotEnforced
    users_in_scope: list[str] = field(default_factory=list)
    grant_controls: list[str] = field(default_factory=list)
    session_controls: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)


@dataclass
class SecureScoreSnapshot:
    score: float
    max_score: float
    percentage: float
    controls_implemented: int
    controls_total: int
    captured_at: datetime
    raw: dict = field(default_factory=dict)


@dataclass
class M365DiscoveryResult:
    """Resultado enriquecido Paso 6 sobre DiscoveryResult estandar."""
    identities: list[DiscoveredIdentityDTO] = field(default_factory=list)
    assets: list[DiscoveredAssetDTO] = field(default_factory=list)
    conditional_access_policies: list[ConditionalAccessPolicy] = field(default_factory=list)
    secure_score: Optional[SecureScoreSnapshot] = None
    mfa_by_user: dict[str, bool] = field(default_factory=dict)
    privileged_users: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_discovery_result(self, provider: str = "microsoft_365") -> DiscoveryResult:
        return DiscoveryResult(
            provider=provider,
            success=len(self.errors) == 0,
            assets=list(self.assets),
            identities=list(self.identities),
            errors=list(self.errors),
            summary={
                "total_assets": len(self.assets),
                "total_identities": len(self.identities),
                "ca_policies": len(self.conditional_access_policies),
                "ca_policies_enabled": sum(
                    1 for p in self.conditional_access_policies if p.state == "enabled"
                ),
                "secure_score_pct": (
                    self.secure_score.percentage
                    if self.secure_score is not None else None
                ),
                "privileged_count": len(self.privileged_users),
                "mfa_covered": sum(1 for v in self.mfa_by_user.values() if v),
                "mfa_total": len(self.mfa_by_user),
            },
        )


# ════════════════════════════════════════════════════════════════════
# Fetcher abstraction (production = httpx, tests = mock)
# ════════════════════════════════════════════════════════════════════

#: (path, params) -> dict
GraphFetcher = Callable[[str, Optional[dict]], Awaitable[dict]]


def authorization_url(
    tenant_id: str, client_id: str, redirect_uri: str, state: str,
    scopes: Optional[list[str]] = None,
) -> str:
    """Construye la URL de consentimiento OAuth2 para el admin del tenant."""
    from urllib.parse import urlencode
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "response_mode": "query",
        "scope": " ".join(scopes or REQUIRED_SCOPES),
        "state": state,
    }
    return f"{LOGIN_BASE}/{tenant_id}/oauth2/v2.0/authorize?{urlencode(params)}"


async def exchange_code_for_tokens(
    tenant_id: str, client_id: str, client_secret: str,
    code: str, redirect_uri: str,
    http_client: Optional[httpx.AsyncClient] = None,
) -> dict:
    """Intercambia authorization_code por access_token + refresh_token.

    Devuelve dict con: access_token, refresh_token, expires_in, token_type,
    scope, expires_at (isoformat calculado en cliente).
    """
    url = f"{LOGIN_BASE}/{tenant_id}/oauth2/v2.0/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    close_client = False
    if http_client is None:
        http_client = httpx.AsyncClient(timeout=30)
        close_client = True
    try:
        r = await http_client.post(url, data=payload)
        r.raise_for_status()
        data = r.json()
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=int(data.get("expires_in", 3600)),
        )
        data["expires_at"] = expires_at.isoformat()
        return data
    finally:
        if close_client:
            await http_client.aclose()


async def refresh_access_token(
    tenant_id: str, client_id: str, client_secret: str, refresh_token: str,
    http_client: Optional[httpx.AsyncClient] = None,
) -> dict:
    """Refresca access_token usando refresh_token (rotacion automatica)."""
    url = f"{LOGIN_BASE}/{tenant_id}/oauth2/v2.0/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    close_client = False
    if http_client is None:
        http_client = httpx.AsyncClient(timeout=30)
        close_client = True
    try:
        r = await http_client.post(url, data=payload)
        r.raise_for_status()
        data = r.json()
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=int(data.get("expires_in", 3600)),
        )
        data["expires_at"] = expires_at.isoformat()
        return data
    finally:
        if close_client:
            await http_client.aclose()


def needs_refresh(token_payload: dict) -> bool:
    """True si el access_token expira en menos de REFRESH_MARGIN_SECONDS."""
    exp = token_payload.get("expires_at")
    if not exp:
        return True
    try:
        expires = datetime.fromisoformat(exp)
    except (TypeError, ValueError):
        return True
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    return (expires - now).total_seconds() < REFRESH_MARGIN_SECONDS


# ════════════════════════════════════════════════════════════════════
# Connector enriquecido
# ════════════════════════════════════════════════════════════════════

class M365Paso6Connector:
    """Conector Paso 6 con discoveries enriquecidos.

    En produccion, credenciales incluyen tenant_id, client_id, client_secret,
    refresh_token, access_token, expires_at.

    En tests/demos, se puede inyectar `fetcher` (async callable) que recibe
    (path, params) y devuelve el JSON esperado — ver `paso6_demo_mocks`.
    """

    provider = ConnectorProvider.MICROSOFT_365

    def __init__(
        self,
        credentials: dict,
        fetcher: Optional[GraphFetcher] = None,
    ) -> None:
        self.credentials = dict(credentials or {})
        self._fetcher = fetcher
        self._http_client: Optional[httpx.AsyncClient] = None

    # --- Auth helpers ---

    async def ensure_fresh_token(self) -> None:
        """Refresca access_token si ha expirado. No hace nada si usamos fetcher mock."""
        if self._fetcher is not None:
            return
        if not needs_refresh(self.credentials):
            return
        refresh_token = self.credentials.get("refresh_token")
        if not refresh_token:
            raise RuntimeError("No hay refresh_token disponible para M365")
        data = await refresh_access_token(
            tenant_id=self.credentials["tenant_id"],
            client_id=self.credentials["client_id"],
            client_secret=self.credentials["client_secret"],
            refresh_token=refresh_token,
        )
        self.credentials.update(data)

    async def _graph_get(self, path: str, params: Optional[dict] = None) -> dict:
        if self._fetcher is not None:
            return await self._fetcher(path, params)
        await self.ensure_fresh_token()
        token = self.credentials.get("access_token")
        if not token:
            raise RuntimeError("No hay access_token tras refresh")
        base = GRAPH_BETA if path.startswith("/beta/") else GRAPH_BASE
        rel = path[len("/beta/"):] if path.startswith("/beta/") else path
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(
                f"{base}{rel}",
                headers={"Authorization": f"Bearer {token}"},
                params=params or {},
            )
            r.raise_for_status()
            return r.json()

    # --- Discovery methods ---

    async def discover_users(self) -> list[DiscoveredIdentityDTO]:
        out: list[DiscoveredIdentityDTO] = []
        data = await self._graph_get("/users", {
            "$select": (
                "id,displayName,mail,userPrincipalName,accountEnabled,"
                "userType,assignedPlans,createdDateTime"
            ),
            "$top": "999",
        })
        for u in data.get("value", []):
            out.append(DiscoveredIdentityDTO(
                external_id=u["id"],
                email=u.get("mail") or u.get("userPrincipalName"),
                display_name=u.get("displayName") or "Unknown",
                identity_type="user",
                provider="microsoft_365",
                is_active=u.get("accountEnabled", True),
                raw_data=u,
            ))
        return out

    async def discover_groups(self) -> list[DiscoveredIdentityDTO]:
        out: list[DiscoveredIdentityDTO] = []
        data = await self._graph_get("/groups", {
            "$select": "id,displayName,groupTypes,securityEnabled,mailEnabled",
            "$top": "999",
        })
        for g in data.get("value", []):
            out.append(DiscoveredIdentityDTO(
                external_id=g["id"],
                email=None,
                display_name=g.get("displayName") or "Unknown Group",
                identity_type="group",
                provider="microsoft_365",
                raw_data=g,
            ))
        return out

    async def discover_directory_role_assignments(self) -> set[str]:
        """user_ids con rol de administrador (directoryRoles/members)."""
        privileged: set[str] = set()
        try:
            roles = await self._graph_get("/directoryRoles", None)
        except Exception as exc:
            logger.warning("M365 directoryRoles: %s", exc)
            return privileged
        for role in roles.get("value", []):
            role_id = role.get("id")
            if not role_id:
                continue
            try:
                members = await self._graph_get(
                    f"/directoryRoles/{role_id}/members", None,
                )
            except Exception as exc:
                logger.warning("M365 role %s members failed: %s", role_id, exc)
                continue
            for m in members.get("value", []):
                uid = m.get("id")
                if uid:
                    privileged.add(uid)
        return privileged

    async def discover_mfa_state_per_user(
        self, user_ids: list[str],
    ) -> dict[str, bool]:
        """Consulta authenticationMethods por usuario (beta endpoint).

        Un usuario tiene MFA si posee al menos un metodo strong
        (microsoftAuthenticatorAuthenticationMethod, fido2AuthenticationMethod,
        phoneAuthenticationMethod).
        """
        strong = {
            "#microsoft.graph.microsoftAuthenticatorAuthenticationMethod",
            "#microsoft.graph.fido2AuthenticationMethod",
            "#microsoft.graph.phoneAuthenticationMethod",
            "#microsoft.graph.softwareOathAuthenticationMethod",
            "#microsoft.graph.windowsHelloForBusinessAuthenticationMethod",
        }
        out: dict[str, bool] = {}
        for uid in user_ids:
            try:
                data = await self._graph_get(
                    f"/beta/users/{uid}/authentication/methods", None,
                )
            except Exception as exc:
                logger.warning("MFA state %s: %s", uid, exc)
                out[uid] = False
                continue
            methods = data.get("value", [])
            out[uid] = any(
                (m.get("@odata.type") in strong) for m in methods
            )
        return out

    async def discover_conditional_access_policies(
        self,
    ) -> list[ConditionalAccessPolicy]:
        out: list[ConditionalAccessPolicy] = []
        try:
            data = await self._graph_get("/identity/conditionalAccess/policies", None)
        except Exception as exc:
            logger.warning("CA policies failed: %s", exc)
            return out
        for p in data.get("value", []):
            conditions = p.get("conditions") or {}
            users = conditions.get("users") or {}
            grant = (p.get("grantControls") or {}).get("builtInControls") or []
            session = (p.get("sessionControls") or {})
            out.append(ConditionalAccessPolicy(
                policy_id=p.get("id", ""),
                display_name=p.get("displayName", ""),
                state=p.get("state", "unknown"),
                users_in_scope=list(users.get("includeUsers") or []),
                grant_controls=list(grant),
                session_controls=[
                    k for k, v in session.items() if v is not None
                ],
                raw=p,
            ))
        return out

    async def discover_secure_score(self) -> Optional[SecureScoreSnapshot]:
        try:
            data = await self._graph_get(
                "/security/secureScores", {"$top": "1"},
            )
        except Exception as exc:
            logger.warning("Secure Score failed: %s", exc)
            return None
        items = data.get("value") or []
        if not items:
            return None
        latest = items[0]
        score = float(latest.get("currentScore", 0))
        max_score = float(latest.get("maxScore", 0))
        pct = round(100.0 * score / max_score, 1) if max_score else 0.0
        ctrls_impl = 0
        ctrls_total = 0
        for c in latest.get("controlScores", []) or []:
            ctrls_total += 1
            if (c.get("score") or 0) > 0:
                ctrls_impl += 1
        created_raw = latest.get("createdDateTime")
        try:
            captured = datetime.fromisoformat(
                (created_raw or "").replace("Z", "+00:00")
            )
        except (TypeError, ValueError):
            captured = datetime.now(timezone.utc)
        return SecureScoreSnapshot(
            score=score, max_score=max_score, percentage=pct,
            controls_implemented=ctrls_impl, controls_total=ctrls_total,
            captured_at=captured, raw=latest,
        )

    async def discover_devices(self) -> list[DiscoveredAssetDTO]:
        out: list[DiscoveredAssetDTO] = []
        try:
            data = await self._graph_get(
                "/deviceManagement/managedDevices",
                {"$top": "999"},
            )
        except Exception as exc:
            logger.warning("Intune devices failed: %s", exc)
            return out
        for d in data.get("value", []):
            os_name = d.get("operatingSystem") or ""
            compliance = d.get("complianceState") or ""
            out.append(DiscoveredAssetDTO(
                external_id=d["id"],
                name=d.get("deviceName") or "Unknown Device",
                asset_type="m365_device",
                provider="microsoft_365",
                tags=[os_name, compliance] if compliance else [os_name],
                raw_data=d,
            ))
        return out

    # --- Orquestacion completa Paso 6 ---

    async def run_paso6_discovery(self) -> M365DiscoveryResult:
        result = M365DiscoveryResult()
        try:
            users = await self.discover_users()
        except Exception as exc:
            result.errors.append(f"users: {exc}")
            users = []
        try:
            groups = await self.discover_groups()
        except Exception as exc:
            result.errors.append(f"groups: {exc}")
            groups = []
        try:
            devices = await self.discover_devices()
        except Exception as exc:
            result.errors.append(f"devices: {exc}")
            devices = []
        try:
            ca = await self.discover_conditional_access_policies()
        except Exception as exc:
            result.errors.append(f"ca: {exc}")
            ca = []
        try:
            score = await self.discover_secure_score()
        except Exception as exc:
            result.errors.append(f"secure_score: {exc}")
            score = None
        try:
            privileged = await self.discover_directory_role_assignments()
        except Exception as exc:
            result.errors.append(f"privileged: {exc}")
            privileged = set()

        # Marcar usuarios privilegiados
        for ident in users:
            if ident.external_id in privileged:
                ident.is_privileged = True

        # MFA per user (en produccion: solo para privilegiados +
        # muestra aleatoria de usuarios para evitar ratelimit).
        user_ids_for_mfa = [u.external_id for u in users]
        try:
            mfa_map = await self.discover_mfa_state_per_user(user_ids_for_mfa)
        except Exception as exc:
            result.errors.append(f"mfa: {exc}")
            mfa_map = {}
        for ident in users:
            if ident.external_id in mfa_map:
                ident.mfa_enabled = mfa_map[ident.external_id]

        result.identities = list(users) + list(groups)
        result.assets = list(devices)
        result.conditional_access_policies = ca
        result.secure_score = score
        result.mfa_by_user = mfa_map
        result.privileged_users = sorted(privileged)
        return result


__all__ = [
    "REQUIRED_SCOPES",
    "ConditionalAccessPolicy",
    "SecureScoreSnapshot",
    "M365DiscoveryResult",
    "M365Paso6Connector",
    "authorization_url",
    "exchange_code_for_tokens",
    "refresh_access_token",
    "needs_refresh",
]
