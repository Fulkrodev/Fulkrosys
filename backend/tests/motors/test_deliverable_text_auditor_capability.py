"""S1 fix · tests de la capability DeliverableTextAuditor (mock LLM · sin red)."""
from backend.app.motors.m_observability import (
    deliverable_text_auditor_capability as cap,
)


class _FakeResp:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeRouter:
    def __init__(self, content: str) -> None:
        self._c = content

    def complete(self, **_kw):
        return _FakeResp(self._c)


def test_no_api_key_returns_none(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert cap.audit_deliverable_sync("texto entregable", "BASICA") is None


def test_empty_text_returns_none(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert cap.audit_deliverable_sync("   ", "BASICA") is None


def test_parses_and_validates_verdict(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    canned = (
        '{"verdict": "FAIL_CRITICAL", "issues_critical": ["confunde DoA con '
        'conformidad"], "issues_moderate": [], "key_phrases_found": '
        '["anexo ii", "op.acc.5"]}'
    )
    monkeypatch.setattr(
        "backend.app.core.ai.llm_router.get_default_llm_router",
        lambda: _FakeRouter(canned),
    )
    out = cap.audit_deliverable_sync("DECLARACIÓN DE APLICABILIDAD...", "BASICA")
    assert out is not None
    assert out["verdict"] == "FAIL_CRITICAL"
    assert out["issues_critical"]
    assert "anexo ii" in out["key_phrases_found"]


def test_invalid_verdict_nulled(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setattr(
        "backend.app.core.ai.llm_router.get_default_llm_router",
        lambda: _FakeRouter('{"verdict": "MAYBE", "issues_critical": []}'),
    )
    out = cap.audit_deliverable_sync("texto", "MEDIA")
    assert out is not None
    assert out["verdict"] is None


def test_fenced_json_parsed(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    fenced = '```json\n{"verdict": "PASS_AUDITOR_READY"}\n```'
    monkeypatch.setattr(
        "backend.app.core.ai.llm_router.get_default_llm_router",
        lambda: _FakeRouter(fenced),
    )
    out = cap.audit_deliverable_sync("texto", "ALTA")
    assert out is not None
    assert out["verdict"] == "PASS_AUDITOR_READY"
