"""OAuth service per provider (SAN-E v3.MB-4.2.bis · Q2-A).

Real OAuth flows para 5 providers + AWS especial (IAM access key paste).

Providers:
- GitHub Apps (no PKCE)
- Microsoft 365 (Azure AD app · Graph API · PKCE)
- Azure (Azure AD app · ARM API · PKCE)
- Google Workspace (Admin SDK · PKCE)
- Base custom (Marcos configura · PKCE)

AWS especial:
- NO OAuth standard · paste IAM access key + secret + region
- STS GetCallerIdentity validation
- Encrypted via Fernet token_encryption (existing)

Token encryption: usa backend.app.motors.m16_onboarding.token_encryption
(Fernet AES-128-CBC + HMAC-SHA256, key derivada de app_secret_key).
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.models.onboarding import ConnectorConfig
from backend.app.motors.m16_onboarding.token_encryption import (
    encrypt_credentials,
)


logger = logging.getLogger(__name__)


SUPPORTED_OAUTH_PROVIDERS = {"github", "microsoft", "azure", "google", "base"}


@dataclass
class ProviderConfig:
    """Configuración estática per provider."""
    authorize_url: str
    token_url: str
    scopes: str
    requires_pkce: bool


def _provider_configs() -> dict[str, ProviderConfig]:
    """Provider configs · interpolados con tenant_id si aplica."""
    settings = get_settings()
    ms_tenant = settings.microsoft_tenant_id or "common"
    az_tenant = settings.azure_tenant_id or "common"

    return {
        "github": ProviderConfig(
            authorize_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            scopes="repo,read:org,user:email",
            requires_pkce=False,
        ),
        "microsoft": ProviderConfig(
            authorize_url=(
                f"https://login.microsoftonline.com/{ms_tenant}/oauth2/v2.0/authorize"
            ),
            token_url=(
                f"https://login.microsoftonline.com/{ms_tenant}/oauth2/v2.0/token"
            ),
            scopes=(
                "offline_access User.Read Group.Read.All Directory.Read.All"
            ),
            requires_pkce=True,
        ),
        "azure": ProviderConfig(
            authorize_url=(
                f"https://login.microsoftonline.com/{az_tenant}/oauth2/v2.0/authorize"
            ),
            token_url=(
                f"https://login.microsoftonline.com/{az_tenant}/oauth2/v2.0/token"
            ),
            scopes=(
                "https://management.azure.com/user_impersonation offline_access"
            ),
            requires_pkce=True,
        ),
        "google": ProviderConfig(
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            scopes=(
                "https://www.googleapis.com/auth/admin.directory.user.readonly "
                "https://www.googleapis.com/auth/admin.directory.group.readonly"
            ),
            requires_pkce=True,
        ),
        "base": ProviderConfig(
            authorize_url=settings.base_oauth_authorize_url or "",
            token_url=settings.base_oauth_token_url or "",
            scopes=settings.base_oauth_scopes or "",
            requires_pkce=True,
        ),
    }


def _get_client_credentials(connector_type: str) -> tuple[str, str]:
    """Devuelve (client_id, client_secret) per provider desde settings."""
    settings = get_settings()
    if connector_type == "github":
        return settings.github_client_id, settings.github_client_secret.get_secret_value()
    if connector_type == "microsoft":
        return settings.microsoft_client_id, settings.microsoft_client_secret.get_secret_value()
    if connector_type == "azure":
        return settings.azure_client_id, settings.azure_client_secret.get_secret_value()
    if connector_type == "google":
        return settings.google_client_id, settings.google_client_secret.get_secret_value()
    if connector_type == "base":
        return settings.base_client_id, settings.base_client_secret.get_secret_value()
    raise ValueError(f"Unknown OAuth provider: {connector_type}")


# =====================================================================
# Authorize URL builder
# =====================================================================

class OAuthError(Exception):
    """Errores en flow OAuth (config faltante · token exchange fail · etc)."""


def build_authorize_url(
    *,
    connector_type: str,
    state: str,
    redirect_uri: str,
    code_challenge: str | None = None,
) -> str:
    """Construye authorize URL del provider con state + scopes + PKCE optional.

    Raises:
        OAuthError: si provider no soportado o config faltante.
    """
    if connector_type not in SUPPORTED_OAUTH_PROVIDERS:
        raise OAuthError(f"Provider no soportado para OAuth: {connector_type}")

    cfg = _provider_configs()[connector_type]
    if not cfg.authorize_url:
        raise OAuthError(
            f"Provider {connector_type} sin authorize_url configurado · revisar settings",
        )

    client_id, _ = _get_client_credentials(connector_type)
    if not client_id:
        raise OAuthError(
            f"{connector_type.upper()}_CLIENT_ID no configurado en settings",
        )

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": cfg.scopes,
        "state": state,
    }
    if cfg.requires_pkce:
        if not code_challenge:
            raise OAuthError(
                f"{connector_type} requiere PKCE pero code_challenge faltante",
            )
        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = "S256"

    return f"{cfg.authorize_url}?{urlencode(params)}"


# =====================================================================
# Code exchange
# =====================================================================

@dataclass
class TokenExchangeResult:
    """Resultado de token exchange · pre-encrypt."""
    access_token: str
    refresh_token: str | None
    expires_in: int | None
    token_type: str
    raw: dict[str, Any]


async def exchange_code(
    *,
    connector_type: str,
    code: str,
    redirect_uri: str,
    code_verifier: str | None = None,
) -> TokenExchangeResult:
    """Intercambia authorization code por tokens.

    Raises:
        OAuthError: si token endpoint responde error o respuesta inválida.
    """
    if connector_type not in SUPPORTED_OAUTH_PROVIDERS:
        raise OAuthError(f"Provider no soportado: {connector_type}")

    cfg = _provider_configs()[connector_type]
    client_id, client_secret = _get_client_credentials(connector_type)

    payload: dict[str, Any] = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    if cfg.requires_pkce and code_verifier:
        payload["code_verifier"] = code_verifier

    headers = {"Accept": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(cfg.token_url, data=payload, headers=headers)
    except httpx.HTTPError as exc:
        raise OAuthError(f"Token exchange HTTP error: {exc}") from exc

    if response.status_code != 200:
        raise OAuthError(
            f"Token exchange failed ({response.status_code}): {response.text[:200]}",
        )

    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        raise OAuthError(f"Token endpoint returned non-JSON: {exc}") from exc

    if "error" in data:
        raise OAuthError(
            f"Token exchange error: {data.get('error_description', data['error'])}",
        )

    access_token = data.get("access_token")
    if not access_token:
        raise OAuthError("Token exchange response sin access_token")

    return TokenExchangeResult(
        access_token=access_token,
        refresh_token=data.get("refresh_token"),
        expires_in=data.get("expires_in"),
        token_type=data.get("token_type", "Bearer"),
        raw=data,
    )


# =====================================================================
# Persist connector config
# =====================================================================

async def persist_oauth_connector(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    connector_type: str,
    tokens: TokenExchangeResult,
    scopes: str | None = None,
) -> ConnectorConfig:
    """Guarda/actualiza ConnectorConfig con tokens cifrados Fernet."""
    creds = {
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "token_type": tokens.token_type,
        "expires_in": tokens.expires_in,
    }
    encrypted = encrypt_credentials(creds)

    res = await db.execute(
        select(ConnectorConfig).where(
            ConnectorConfig.project_id == project_id,
            ConnectorConfig.provider == connector_type,
        )
    )
    existing = res.scalar_one_or_none()

    if existing is not None:
        existing.encrypted_credentials = encrypted
        existing.scopes = scopes or existing.scopes
        existing.status = "configured"
        await db.flush()
        return existing

    record = ConnectorConfig(
        project_id=project_id,
        provider=connector_type,
        encrypted_credentials=encrypted,
        scopes=scopes,
        status="configured",
    )
    db.add(record)
    await db.flush()
    return record


# =====================================================================
# AWS especial (NO OAuth · IAM access key paste)
# =====================================================================

async def aws_validate_credentials(
    *,
    access_key_id: str,
    secret_access_key: str,
    region: str,
) -> dict[str, Any]:
    """Valida AWS credentials via STS GetCallerIdentity.

    Returns: dict con account_id · arn · user_id si valid.

    Raises:
        OAuthError: si credentials invalid (botocore.exceptions.ClientError).
    """
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError as exc:
        raise OAuthError(f"boto3 not available: {exc}") from exc

    try:
        sts = boto3.client(
            "sts",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region,
        )
        identity = sts.get_caller_identity()
    except (ClientError, BotoCoreError) as exc:
        raise OAuthError(f"AWS credentials inválidas: {exc}") from exc

    return {
        "account_id": identity.get("Account"),
        "arn": identity.get("Arn"),
        "user_id": identity.get("UserId"),
    }


async def persist_aws_connector(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    access_key_id: str,
    secret_access_key: str,
    region: str,
    identity_summary: dict[str, Any],
) -> ConnectorConfig:
    """Guarda/actualiza AWS ConnectorConfig con credentials cifradas Fernet."""
    creds = {
        "access_key_id": access_key_id,
        "secret_access_key": secret_access_key,
        "region": region,
        "auth_method": "iam_access_key",
    }
    encrypted = encrypt_credentials(creds)

    res = await db.execute(
        select(ConnectorConfig).where(
            ConnectorConfig.project_id == project_id,
            ConnectorConfig.provider == "aws",
        )
    )
    existing = res.scalar_one_or_none()

    summary = {
        "auth_method": "iam_access_key",
        "account_id": identity_summary.get("account_id"),
        "arn": identity_summary.get("arn"),
        "region": region,
    }

    if existing is not None:
        existing.encrypted_credentials = encrypted
        existing.scopes = region
        existing.status = "configured"
        existing.discovery_result_summary = summary
        await db.flush()
        return existing

    record = ConnectorConfig(
        project_id=project_id,
        provider="aws",
        encrypted_credentials=encrypted,
        scopes=region,
        status="configured",
        discovery_result_summary=summary,
    )
    db.add(record)
    await db.flush()
    return record
