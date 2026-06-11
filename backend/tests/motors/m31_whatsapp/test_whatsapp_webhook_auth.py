"""Regresión: el webhook de WhatsApp (360dialog) DEBE autenticarse.

Bug histórico (2026-06-11): el handler decía "signature verified" en el
comentario pero NO verificaba nada (`dialog_360_webhook_secret` sin usar) → un
tercero que conociera la URL podía inyectar mensajes "entrantes" falsos del
cliente. Fix: token compartido fail-closed (query ?token= o header
X-Webhook-Token) cuando hay secret configurado.
"""
from __future__ import annotations

from types import SimpleNamespace

from pydantic import SecretStr

from backend.app.motors.m31_whatsapp import api as wa_api


class _FakeReq:
    def __init__(self, q: str | None = None, h: str | None = None):
        self.query_params = {"token": q} if q else {}
        self.headers = {"X-Webhook-Token": h} if h else {}


def _settings(secret: str) -> SimpleNamespace:
    return SimpleNamespace(dialog_360_webhook_secret=SecretStr(secret))


def test_open_when_no_secret(monkeypatch):
    # Dev/mock (sin secret) → verificación omitida (True).
    monkeypatch.setattr(wa_api, "get_settings", lambda: _settings(""))
    assert wa_api._webhook_authorized(_FakeReq()) is True


def test_rejects_missing_or_bad_token(monkeypatch):
    monkeypatch.setattr(wa_api, "get_settings", lambda: _settings("s3cr3t-token"))
    assert wa_api._webhook_authorized(_FakeReq()) is False
    assert wa_api._webhook_authorized(_FakeReq(q="wrong")) is False
    assert wa_api._webhook_authorized(_FakeReq(h="wrong")) is False


def test_accepts_good_token_query_or_header(monkeypatch):
    monkeypatch.setattr(wa_api, "get_settings", lambda: _settings("s3cr3t-token"))
    assert wa_api._webhook_authorized(_FakeReq(q="s3cr3t-token")) is True
    assert wa_api._webhook_authorized(_FakeReq(h="s3cr3t-token")) is True
