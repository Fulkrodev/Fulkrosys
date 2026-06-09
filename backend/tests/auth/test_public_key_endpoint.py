"""Tests SAN-B.MB-7.4 · /api/v1/auth/public-key + /verify-signature.

Cubre:
- GET /public-key sin auth (whitelist) · returns PEM + algorithm + key_id
- POST /verify-signature valid → {valid: true}
- POST /verify-signature invalid signature → {valid: false}
- POST /verify-signature malformed base64 → {valid: false} (no crash)
"""
from __future__ import annotations

import base64

import pytest
from cryptography.hazmat.primitives import serialization

from backend.app.auth import crypto


@pytest.mark.asyncio
async def test_get_public_key_no_auth_required(async_client):
    """GET /public-key debe responder 200 sin cookies/headers auth."""
    res = await async_client.get("/api/v1/auth/public-key")
    assert res.status_code == 200
    body = res.json()
    assert body["algorithm"] == "ed25519"
    assert body["format"] == "PEM"
    assert "BEGIN PUBLIC KEY" in body["public_key"]
    assert "END PUBLIC KEY" in body["public_key"]
    assert len(body["key_id"]) == 16  # SHA256 truncated 16 chars


@pytest.mark.asyncio
async def test_verify_signature_valid_returns_true(async_client):
    """Firma válida con la PRIVATE_PEM real → {valid: true}."""
    payload = b"FULKRO test artifact bytes"
    private_key = serialization.load_pem_private_key(crypto._PRIVATE_PEM, password=None)
    signature = private_key.sign(payload)

    res = await async_client.post(
        "/api/v1/auth/verify-signature",
        json={
            "payload_b64": base64.b64encode(payload).decode("ascii"),
            "signature_b64": base64.b64encode(signature).decode("ascii"),
        },
    )
    assert res.status_code == 200
    assert res.json() == {"valid": True}


@pytest.mark.asyncio
async def test_verify_signature_invalid_returns_false(async_client):
    """Firma random → {valid: false} (sin crash)."""
    payload = b"FULKRO test"
    fake_signature = b"\x00" * 64  # Ed25519 signature size 64 bytes

    res = await async_client.post(
        "/api/v1/auth/verify-signature",
        json={
            "payload_b64": base64.b64encode(payload).decode("ascii"),
            "signature_b64": base64.b64encode(fake_signature).decode("ascii"),
        },
    )
    assert res.status_code == 200
    assert res.json() == {"valid": False}


@pytest.mark.asyncio
async def test_verify_signature_malformed_base64_returns_false(async_client):
    """Base64 malformed → {valid: false} (sin 500)."""
    res = await async_client.post(
        "/api/v1/auth/verify-signature",
        json={
            "payload_b64": "!!!not-base64!!!",
            "signature_b64": "also-bad",
        },
    )
    assert res.status_code == 200
    assert res.json() == {"valid": False}


@pytest.mark.asyncio
async def test_verify_signature_payload_mismatch_returns_false(async_client):
    """Firma de payload A · verify contra payload B → false."""
    payload_a = b"original payload"
    payload_b = b"different payload"
    private_key = serialization.load_pem_private_key(crypto._PRIVATE_PEM, password=None)
    signature_a = private_key.sign(payload_a)

    res = await async_client.post(
        "/api/v1/auth/verify-signature",
        json={
            "payload_b64": base64.b64encode(payload_b).decode("ascii"),
            "signature_b64": base64.b64encode(signature_a).decode("ascii"),
        },
    )
    assert res.status_code == 200
    assert res.json() == {"valid": False}
