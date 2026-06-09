"""Tests para OAuthService (SAN-E v3.MB-4.2.bis · Q2-A).

Mocks HTTP via respx · boto3 via mock object para AWS especial.
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import httpx
import pytest
import respx
from sqlalchemy import text as sa_text

from backend.app.config import get_settings
from backend.app.models.onboarding import ConnectorConfig
from backend.app.motors.m16_onboarding import oauth_service
from backend.app.motors.m16_onboarding.token_encryption import (
    decrypt_credentials,
)
from backend.tests.conftest import setup_test_project


pytestmark = pytest.mark.asyncio


def _override_github_settings():
    """Inyecta credentials github en settings cache."""
    settings = get_settings()
    settings.github_client_id = "fake_github_client_id"
    # SecretStr re-asignar
    from pydantic import SecretStr
    settings.github_client_secret = SecretStr("fake_github_client_secret")


async def test_build_authorize_url_includes_state():
    _override_github_settings()
    url = oauth_service.build_authorize_url(
        connector_type="github",
        state="my_state_token",
        redirect_uri="http://localhost/cb",
    )
    assert "github.com/login/oauth/authorize" in url
    assert "state=my_state_token" in url
    assert "client_id=fake_github_client_id" in url
    assert "redirect_uri=http%3A%2F%2Flocalhost%2Fcb" in url
    assert "response_type=code" in url


async def test_build_authorize_url_unknown_provider_raises():
    with pytest.raises(oauth_service.OAuthError, match="no soportado"):
        oauth_service.build_authorize_url(
            connector_type="bogus",
            state="x",
            redirect_uri="http://localhost",
        )


@respx.mock
async def test_exchange_code_returns_tokens():
    _override_github_settings()
    respx.post("https://github.com/login/oauth/access_token").mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "gho_fake_access_token",
                "refresh_token": "ghr_fake_refresh",
                "token_type": "Bearer",
                "expires_in": 3600,
            },
        ),
    )
    result = await oauth_service.exchange_code(
        connector_type="github",
        code="fake_code",
        redirect_uri="http://localhost/cb",
    )
    assert result.access_token == "gho_fake_access_token"
    assert result.refresh_token == "ghr_fake_refresh"
    assert result.expires_in == 3600


@respx.mock
async def test_persist_oauth_connector_encrypts_tokens(db):
    _, project_id = await setup_test_project(db)

    tokens = oauth_service.TokenExchangeResult(
        access_token="gho_secret",
        refresh_token="ghr_secret",
        expires_in=3600,
        token_type="Bearer",
        raw={"access_token": "gho_secret"},
    )
    record = await oauth_service.persist_oauth_connector(
        db,
        project_id=uuid.UUID(project_id),
        connector_type="github",
        tokens=tokens,
    )
    assert record.id is not None
    assert record.provider == "github"
    # Tokens deben estar cifrados (no plaintext)
    assert b"gho_secret" not in record.encrypted_credentials
    decrypted = decrypt_credentials(record.encrypted_credentials)
    assert decrypted["access_token"] == "gho_secret"


async def test_aws_validate_credentials_via_mock_boto3():
    """Boto3 se importa lazy dentro de la función · mock vía boto3.client patch."""
    fake_identity = {
        "Account": "123456789012",
        "Arn": "arn:aws:iam::123456789012:user/test",
        "UserId": "AIDXXX",
    }
    mock_sts = MagicMock()
    mock_sts.get_caller_identity.return_value = fake_identity

    import boto3
    with patch.object(boto3, "client", return_value=mock_sts):
        result = await oauth_service.aws_validate_credentials(
            access_key_id="AKIAXXXXXXXXXXXXXXXX",
            secret_access_key="fakeSecret_123456789_paste_here_for_testing",
            region="eu-west-1",
        )
    assert result["account_id"] == "123456789012"
    assert "test" in result["arn"]
