"""Tests CSPMiddleware (SAN-B.MB-7.3 · ADR-033).

Cubre:
- CSP header presente en todas las responses
- X-Frame-Options DENY
- X-Content-Type-Options nosniff
- Referrer-Policy strict-origin-when-cross-origin
- Directivas críticas: connect-src api.anthropic.com (Copilot streaming) ·
  img-src blob: (MinIO previews) · frame-ancestors none (anti-clickjacking)
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.middleware.csp import CSP_DIRECTIVES, CSPMiddleware, _format_csp


@pytest.fixture
def csp_app():
    app = FastAPI()
    app.add_middleware(CSPMiddleware)

    @app.get("/__csp_test__")
    async def smoke():
        return {"ok": True}

    return TestClient(app)


# ════════════════════════════════════════════════════════════════════
# Headers presence
# ════════════════════════════════════════════════════════════════════

def test_csp_header_present_on_response(csp_app):
    res = csp_app.get("/__csp_test__")
    assert res.status_code == 200
    assert "Content-Security-Policy" in res.headers


def test_x_frame_options_deny(csp_app):
    res = csp_app.get("/__csp_test__")
    assert res.headers.get("X-Frame-Options") == "DENY"


def test_x_content_type_options_nosniff(csp_app):
    res = csp_app.get("/__csp_test__")
    assert res.headers.get("X-Content-Type-Options") == "nosniff"


def test_referrer_policy_strict_origin(csp_app):
    res = csp_app.get("/__csp_test__")
    assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


# ════════════════════════════════════════════════════════════════════
# Directives content
# ════════════════════════════════════════════════════════════════════

def test_csp_allows_anthropic_api():
    """A14 Copilot streaming requires connect-src incluya api.anthropic.com."""
    csp_value = _format_csp(CSP_DIRECTIVES)
    assert "connect-src" in csp_value
    assert "https://api.anthropic.com" in csp_value


def test_csp_allows_minio_blob_images():
    """MinIO signed URLs como blob: URLs en img-src."""
    csp_value = _format_csp(CSP_DIRECTIVES)
    assert "img-src" in csp_value
    assert "blob:" in csp_value
    assert "data:" in csp_value


def test_csp_frame_ancestors_none():
    """Anti-clickjacking · frame-ancestors none."""
    csp_value = _format_csp(CSP_DIRECTIVES)
    assert "frame-ancestors 'none'" in csp_value


def test_csp_object_src_none():
    """No Flash/Java/embed permitido."""
    csp_value = _format_csp(CSP_DIRECTIVES)
    assert "object-src 'none'" in csp_value


def test_csp_unsafe_inline_justified_nextjs():
    """Next.js requiere unsafe-inline para hidration · justified ADR-033."""
    csp_value = _format_csp(CSP_DIRECTIVES)
    assert "script-src" in csp_value
    assert "'unsafe-inline'" in csp_value
