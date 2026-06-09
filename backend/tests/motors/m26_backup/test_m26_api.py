"""Tests HTTP Motor 26 — Backup & DR REST API.

Platform-global endpoints (no RLS, no tenant context).
"""
import pytest
from uuid import uuid4

BASE = "/api/v1/backup"


class TestStatusEndpoint:

    @pytest.mark.asyncio
    async def test_get_status(self, async_client, db):
        """H1: GET /status returns health semaphore."""
        r = await async_client.get(f"{BASE}/status")
        assert r.status_code == 200
        data = r.json()
        assert "health" in data
        assert data["health"] in ("green", "yellow", "red")


class TestJobsEndpoint:

    @pytest.mark.asyncio
    async def test_list_jobs(self, async_client, db):
        """H2: GET /jobs returns list (may include seed data)."""
        r = await async_client.get(f"{BASE}/jobs")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    @pytest.mark.asyncio
    async def test_trigger_backup_201(self, async_client, db):
        """H3: POST /jobs creates pending backup job."""
        r = await async_client.post(
            f"{BASE}/jobs",
            json={"backup_type": "postgres_full"},
        )
        assert r.status_code == 201
        data = r.json()
        assert data["backup_type"] == "postgres_full"
        assert data["status"] == "pending"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_list_jobs_filtered(self, async_client, db):
        """H4: GET /jobs?backup_type= filters correctly."""
        # Create a job with unique type
        await async_client.post(
            f"{BASE}/jobs",
            json={"backup_type": "test_filter_type"},
        )
        r = await async_client.get(f"{BASE}/jobs?backup_type=test_filter_type")
        assert r.status_code == 200
        for job in r.json():
            assert job["backup_type"] == "test_filter_type"


class TestRetentionPoliciesEndpoint:

    @pytest.mark.asyncio
    async def test_list_retention_policies(self, async_client, db):
        """H5: GET /retention-policies returns list."""
        r = await async_client.get(f"{BASE}/retention-policies")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    @pytest.mark.asyncio
    async def test_seed_policies_idempotent(self, async_client, db):
        """H6: POST /retention-policies/seed is idempotent."""
        r1 = await async_client.post(f"{BASE}/retention-policies/seed")
        assert r1.status_code == 200
        assert r1.json()["seeded"] == 6

        r2 = await async_client.post(f"{BASE}/retention-policies/seed")
        assert r2.status_code == 200
        assert r2.json()["seeded"] == 6


class TestRestoreTestsEndpoint:

    @pytest.mark.asyncio
    async def test_list_restore_tests(self, async_client, db):
        """H7: GET /restore-tests returns list."""
        r = await async_client.get(f"{BASE}/restore-tests")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    @pytest.mark.asyncio
    async def test_create_restore_test_201(self, async_client, db):
        """H8: POST /restore-tests creates pending test."""
        r = await async_client.post(
            f"{BASE}/restore-tests",
            json={"test_type": "full_db"},
        )
        assert r.status_code == 201
        assert r.json()["status"] == "pending"


class TestDrDrillsEndpoint:

    @pytest.mark.asyncio
    async def test_create_dr_drill_201(self, async_client, db):
        """H9: POST /dr-drills creates planned drill."""
        r = await async_client.post(
            f"{BASE}/dr-drills",
            json={"rto_objective_seconds": 14400, "rpo_objective_seconds": 86400},
        )
        assert r.status_code == 201
        data = r.json()
        assert data["status"] == "planned"
        assert data["rto_objective_seconds"] == 14400


class TestIntegrityChecksEndpoint:

    @pytest.mark.asyncio
    async def test_create_integrity_check_201(self, async_client, db):
        """H10: POST /integrity-checks creates pending check."""
        r = await async_client.post(
            f"{BASE}/integrity-checks",
            json={"verification_type": "hash_sampling", "sample_size": 50},
        )
        assert r.status_code == 201
        data = r.json()
        assert data["verification_type"] == "hash_sampling"
        assert data["status"] == "pending"
