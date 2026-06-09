"""Tests for public legal/trust endpoints (atom 9.bis.5).

5 tests:
- 1: GET /legal/compliance/status returns 200 without auth + JSON shape
- 2: status reflects current ComplianceCheck rows (frameworks always present)
- 3: POST /legal/sub-processor-notifications/subscribe stores row + consent
- 4: subscribe rejects invalid email format with 422
- 5: subscribe requires consent=true (400 otherwise)
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from backend.app.motors.m_compliance_monitor.sub_processor_subscribers import (
    SubProcessorSubscriber,
)


BASE = "/api/v1/legal"


@pytest.mark.asyncio
async def test_compliance_status_public_no_auth(async_client) -> None:
    r = await async_client.get(f"{BASE}/compliance/status")
    assert r.status_code == 200
    data = r.json()
    # Shape contract — every key must be present.
    for key in (
        "overall_health",
        "last_check",
        "compliance_frameworks",
        "sub_processors_count",
        "last_breach_reported",
        "isms_certifications",
        "monitor_summary",
    ):
        assert key in data, f"missing key: {key}"
    assert isinstance(data["compliance_frameworks"], list)
    assert isinstance(data["isms_certifications"], list)


@pytest.mark.asyncio
async def test_compliance_status_returns_frameworks_list(async_client) -> None:
    r = await async_client.get(f"{BASE}/compliance/status")
    assert r.status_code == 200
    data = r.json()
    names = {f["name"] for f in data["compliance_frameworks"]}
    # Six declared frameworks (RGPD, LOPDGDD, LSSI-CE, NIS2, AEPD cookies, ENS).
    assert {"RGPD UE 2016/679", "LOPDGDD 3/2018", "NIS2 UE 2022/2555"}.issubset(names)
    # Sub-processor count never returns 0 (fallback constant is 5).
    assert data["sub_processors_count"] >= 5
    # ISMS certifications include ISO 27001:2022 in preparedness state.
    iso_names = {c["name"] for c in data["isms_certifications"]}
    assert "ISO 27001:2022" in iso_names


@pytest.mark.asyncio
async def test_sub_processor_subscribe_stores_row(async_client, db) -> None:
    payload = {"email": "Cliente@example.com", "consent": True}
    r = await async_client.post(
        f"{BASE}/sub-processor-notifications/subscribe",
        json=payload,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["subscribed"] is True
    assert data["email"] == "cliente@example.com"  # normalised lowercase

    # Verify persisted via a fresh query (subscribe path commits inside the
    # endpoint; the test transaction sees it because we share the engine).
    row = (
        await db.execute(
            select(SubProcessorSubscriber).where(
                SubProcessorSubscriber.email == "cliente@example.com"
            )
        )
    ).scalar_one_or_none()
    assert row is not None
    assert row.consent_given_at is not None
    # Cleanup so subsequent test runs don't hit unique conflict.
    await db.delete(row)
    await db.flush()


@pytest.mark.asyncio
async def test_sub_processor_subscribe_rejects_invalid_email(async_client) -> None:
    r = await async_client.post(
        f"{BASE}/sub-processor-notifications/subscribe",
        json={"email": "not-an-email", "consent": True},
    )
    # Pydantic EmailStr validation fires at request parse → 422.
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_sub_processor_subscribe_requires_consent(async_client) -> None:
    r = await async_client.post(
        f"{BASE}/sub-processor-notifications/subscribe",
        json={"email": "willing@example.com", "consent": False},
    )
    assert r.status_code == 400
    assert "consent" in r.json().get("detail", "").lower()
