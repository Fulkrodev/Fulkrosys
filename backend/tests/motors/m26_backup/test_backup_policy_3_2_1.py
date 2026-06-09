"""Tests política 3-2-1 backup · SAN-C MB-11.5.

Cobertura combinatoria + endpoint stateless.
"""
from __future__ import annotations

import pytest

from backend.app.motors.m26_backup.backup_policy_3_2_1 import (
    BackupCopy,
    evaluate_3_2_1,
)


def test_compliant_with_3_copies_2_media_1_offsite():
    copies = [
        BackupCopy("prod", "disk", False),
        BackupCopy("backup_local", "disk", False),
        BackupCopy("backup_cloud", "cloud", True),
    ]
    r = evaluate_3_2_1(copies)
    assert r.compliant is True
    assert r.copies_count == 3
    assert "cloud" in r.media_types
    assert "disk" in r.media_types
    assert r.offsite_count == 1
    assert r.gaps == []


def test_non_compliant_only_2_copies():
    copies = [
        BackupCopy("a", "disk", False),
        BackupCopy("b", "cloud", True),
    ]
    r = evaluate_3_2_1(copies)
    assert r.compliant is False
    assert r.copies_count == 2
    assert any("Faltan copias" in g for g in r.gaps)


def test_non_compliant_3_copies_same_media_offsite():
    copies = [
        BackupCopy("a", "disk", False),
        BackupCopy("b", "disk", False),
        BackupCopy("c", "disk", True),
    ]
    r = evaluate_3_2_1(copies)
    assert r.compliant is False
    assert any("medios distintos" in g for g in r.gaps)


def test_non_compliant_3_copies_2_media_no_offsite():
    copies = [
        BackupCopy("a", "disk", False),
        BackupCopy("b", "tape", False),
        BackupCopy("c", "cloud", False),
    ]
    r = evaluate_3_2_1(copies)
    assert r.compliant is False
    assert any("offsite" in g for g in r.gaps)


def test_empty_copies_returns_full_gap_list():
    r = evaluate_3_2_1([])
    assert r.compliant is False
    assert r.copies_count == 0
    assert len(r.gaps) == 3


@pytest.mark.asyncio
async def test_endpoint_evaluate_321_compliant(async_client):
    response = await async_client.post(
        "/api/v1/backup-policy/3-2-1/evaluate",
        json={
            "copies": [
                {"label": "prod", "media_type": "disk", "is_offsite": False},
                {"label": "tape", "media_type": "tape", "is_offsite": False},
                {"label": "cloud", "media_type": "cloud", "is_offsite": True},
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["compliant"] is True
    assert data["offsite_count"] == 1


@pytest.mark.asyncio
async def test_endpoint_evaluate_321_non_compliant_returns_gaps(async_client):
    response = await async_client.post(
        "/api/v1/backup-policy/3-2-1/evaluate",
        json={"copies": [{"label": "prod", "media_type": "disk", "is_offsite": False}]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["compliant"] is False
    assert len(data["gaps"]) >= 1
