"""Regresión: el webhook de WhatsApp (360dialog) DEBE autenticarse.

Bug histórico (2026-06-11): el handler decía "signature verified" en el
comentario pero NO verificaba nada (`dialog_360_webhook_secret` sin usar) → un
tercero que conociera la URL podía inyectar mensajes "entrantes" falsos del
cliente. Fix v1: token compartido fail-closed (query ?token= o header
X-Webhook-Token) cuando hay secret configurado.

Hardening §1.4 (2026-06-15): se añade verificación de firma HMAC-SHA256 del raw
body (header `X-Hub-Signature-256`, formato Meta/WhatsApp Cloud). El token
compartido se mantiene como fallback de compatibilidad. La firma del body es la
defensa real (el token viaja en URL/header y puede filtrarse en logs/proxies).
"""
from __future__ import annotations

import hashlib
import hmac
from types import SimpleNamespace

from pydantic import SecretStr

from backend.app.motors.m31_whatsapp import api as wa_api


class _FakeReq:
    def __init__(
        self,
        q: str | None = None,
        h: str | None = None,
        sig: str | None = None,
    ):
        self.query_params = {"token": q} if q else {}
        self.headers = {}
        if h:
            self.headers["X-Webhook-Token"] = h
        if sig:
            self.headers["X-Hub-Signature-256"] = sig


def _settings(secret: str, production: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        dialog_360_webhook_secret=SecretStr(secret), is_production=production,
    )


def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(
        secret.encode("utf-8"), body, hashlib.sha256,
    ).hexdigest()


def test_open_when_no_secret(monkeypatch):
    # Dev/mock (sin secret) → verificación omitida (True).
    monkeypatch.setattr(wa_api, "get_settings", lambda: _settings(""))
    assert wa_api._webhook_authorized(_FakeReq(), b"{}") is True


def test_closed_when_no_secret_in_production(monkeypatch):
    # La ruta es pública en el auth global: en producción, sin secret, NADA
    # autentica el webhook → se rechaza todo (fail-closed).
    monkeypatch.setattr(
        wa_api, "get_settings", lambda: _settings("", production=True),
    )
    assert wa_api._webhook_authorized(_FakeReq(), b"{}") is False


def test_webhook_path_is_public_in_global_auth():
    # 360dialog llega sin sesión: si la ruta no está en la whitelist del auth
    # global, el middleware devuelve 401 antes de llegar al handler.
    from backend.app.auth.global_dep import _is_whitelisted

    assert _is_whitelisted("/api/v1/webhooks/360dialog")


def test_rejects_missing_or_bad_token(monkeypatch):
    monkeypatch.setattr(wa_api, "get_settings", lambda: _settings("s3cr3t-token"))
    assert wa_api._webhook_authorized(_FakeReq(), b"{}") is False
    assert wa_api._webhook_authorized(_FakeReq(q="wrong"), b"{}") is False
    assert wa_api._webhook_authorized(_FakeReq(h="wrong"), b"{}") is False


def test_accepts_good_token_query_or_header(monkeypatch):
    monkeypatch.setattr(wa_api, "get_settings", lambda: _settings("s3cr3t-token"))
    assert wa_api._webhook_authorized(_FakeReq(q="s3cr3t-token"), b"{}") is True
    assert wa_api._webhook_authorized(_FakeReq(h="s3cr3t-token"), b"{}") is True


def test_accepts_valid_hmac_signature(monkeypatch):
    secret = "s3cr3t-token"
    monkeypatch.setattr(wa_api, "get_settings", lambda: _settings(secret))
    body = b'{"messages":[{"from":"34600000000","text":{"body":"hola"}}]}'
    assert wa_api._webhook_authorized(_FakeReq(sig=_sign(secret, body)), body) is True


def test_rejects_hmac_signature_for_tampered_body(monkeypatch):
    secret = "s3cr3t-token"
    monkeypatch.setattr(wa_api, "get_settings", lambda: _settings(secret))
    body = b'{"messages":[{"from":"34600000000","text":{"body":"hola"}}]}'
    sig = _sign(secret, body)
    tampered = b'{"messages":[{"from":"34999999999","text":{"body":"spoof"}}]}'
    # Firma válida para `body` pero el body recibido es otro → rechazo.
    assert wa_api._webhook_authorized(_FakeReq(sig=sig), tampered) is False


def test_rejects_hmac_signature_with_wrong_secret(monkeypatch):
    monkeypatch.setattr(wa_api, "get_settings", lambda: _settings("real-secret"))
    body = b"{}"
    bad_sig = _sign("attacker-secret", body)
    assert wa_api._webhook_authorized(_FakeReq(sig=bad_sig), body) is False
