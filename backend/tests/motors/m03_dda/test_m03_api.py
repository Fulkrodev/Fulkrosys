"""Tests HTTP Motor 3 — DdA Engine REST API."""
import pytest
from uuid import uuid4

from sqlalchemy import text

from backend.tests.conftest import setup_test_project, _admin_setup, asigna_rseg

BASE = "/api/v1/dda"


async def _generate_dda_http(async_client, db, category="BASICA"):
    """Setup project + generate DdA via HTTP. Returns (project_id, gen_response)."""
    _, project_id = await setup_test_project(db)
    # N4 · congelar exige RSEG nombrado; se asigna aqui para todo el fichero.
    await asigna_rseg(db, project_id, "RSEG")
    r = await async_client.post(
        f"{BASE}/generate",
        json={"project_id": project_id, "system_category": category, "responsable": "RSEG"},
    )
    assert r.status_code == 201, f"Generate failed: {r.status_code} {r.text}"
    return project_id, r.json()


async def _implement_via_db(db, project_id, count):
    """Implement N applicable entries directly in DB."""
    async with _admin_setup(db):
        result = await db.execute(
            text(
                "SELECT id FROM dda_entries "
                "WHERE project_id = :pid AND aplicabilidad != 'no_aplica' "
                "AND deleted_at IS NULL ORDER BY id LIMIT :n"
            ),
            {"pid": project_id, "n": count},
        )
        ids = [str(row[0]) for row in result.fetchall()]
        for eid in ids:
            await db.execute(
                text("UPDATE dda_entries SET estado_implementacion = 'implantada' WHERE id = :id"),
                {"id": eid},
            )
    await db.flush()
    return len(ids)


class TestGenerateEndpoint:

    @pytest.mark.asyncio
    async def test_generate_201(self, async_client, db):
        """H1: POST /generate returns 201 with 73 entries."""
        pid, data = await _generate_dda_http(async_client, db, "BASICA")
        assert data["total_entries"] == 73
        assert data["system_category"] == "BASICA"

    @pytest.mark.asyncio
    async def test_generate_invalid_category_422(self, async_client, db):
        """H2: Invalid category returns 422."""
        _, project_id = await setup_test_project(db)
        r = await async_client.post(
            f"{BASE}/generate",
            json={"project_id": project_id, "system_category": "INEXISTENTE"},
        )
        assert r.status_code == 422


class TestEntriesEndpoint:

    @pytest.mark.asyncio
    async def test_list_entries_73(self, async_client, db):
        """H3: GET entries returns 73 entries."""
        pid, _ = await _generate_dda_http(async_client, db)
        r = await async_client.get(f"{BASE}/projects/{pid}/entries")
        assert r.status_code == 200
        assert len(r.json()) == 73

    @pytest.mark.asyncio
    async def test_list_entries_filter_marco(self, async_client, db):
        """H4: Filter by marco=org returns 4 entries."""
        pid, _ = await _generate_dda_http(async_client, db)
        r = await async_client.get(f"{BASE}/projects/{pid}/entries?marco=org")
        assert r.status_code == 200
        assert len(r.json()) == 4

    @pytest.mark.asyncio
    async def test_list_entries_404_nonexistent(self, async_client, db):
        """H5: 404 for nonexistent project."""
        r = await async_client.get(f"{BASE}/projects/{uuid4()}/entries")
        assert r.status_code == 404


class TestStatsEndpoint:

    @pytest.mark.asyncio
    async def test_stats_returns_completion(self, async_client, db):
        """H6: GET stats returns completion fields."""
        pid, _ = await _generate_dda_http(async_client, db)
        r = await async_client.get(f"{BASE}/projects/{pid}/stats")
        assert r.status_code == 200
        data = r.json()
        assert "completion_pct" in data
        assert data["total_medidas"] == 73
        assert data["completion_pct"] == 0.0


class TestUpdateEndpoint:

    @pytest.mark.asyncio
    async def test_patch_entry(self, async_client, db):
        """H7: PATCH entry updates estado."""
        pid, _ = await _generate_dda_http(async_client, db)
        # Get an entry_id
        entries_r = await async_client.get(f"{BASE}/projects/{pid}/entries")
        aplicable = [e for e in entries_r.json() if e["aplicabilidad"] != "no_aplica"][0]
        entry_id = aplicable["id"]

        r = await async_client.patch(
            f"{BASE}/entries/{entry_id}",
            json={"estado_implementacion": "implantada"},
        )
        assert r.status_code == 200
        assert r.json()["version"] == 2

    @pytest.mark.asyncio
    async def test_patch_nonexistent_404(self, async_client, db):
        """H8: PATCH nonexistent entry returns 404."""
        r = await async_client.patch(
            f"{BASE}/entries/{uuid4()}",
            json={"estado_implementacion": "implantada"},
        )
        assert r.status_code == 404


class TestFreezeEndpoint:

    @pytest.mark.asyncio
    async def test_freeze_incomplete_400(self, async_client, db):
        """H9: Freeze fails when <80% valoradas."""
        pid, _ = await _generate_dda_http(async_client, db)
        r = await async_client.post(f"{BASE}/projects/{pid}/freeze?aprobado_por=RSEG")
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_freeze_after_implementation(self, async_client, db):
        """H10: Freeze succeeds after implementing 85%."""
        pid, gen_data = await _generate_dda_http(async_client, db)
        need = int(gen_data["aplicables"] * 0.85)
        await _implement_via_db(db, pid, need)

        r = await async_client.post(f"{BASE}/projects/{pid}/freeze?aprobado_por=RSEG")
        assert r.status_code == 200
        assert r.json()["frozen_entries"] == 73

    @pytest.mark.asyncio
    async def test_patch_after_freeze_409(self, async_client, db):
        """H11: PATCH after freeze returns 409."""
        pid, gen_data = await _generate_dda_http(async_client, db)
        need = int(gen_data["aplicables"] * 0.85)
        await _implement_via_db(db, pid, need)
        await async_client.post(f"{BASE}/projects/{pid}/freeze?aprobado_por=RSEG")

        entries_r = await async_client.get(f"{BASE}/projects/{pid}/entries")
        entry_id = entries_r.json()[0]["id"]

        r = await async_client.patch(
            f"{BASE}/entries/{entry_id}",
            json={"estado_implementacion": "parcial"},
        )
        assert r.status_code == 409


class TestUnfreezeEndpoint:

    @pytest.mark.asyncio
    async def test_unfreeze_after_freeze(self, async_client, db):
        """H11b: Unfreeze returns 204 after freeze."""
        pid, gen_data = await _generate_dda_http(async_client, db)
        need = int(gen_data["aplicables"] * 0.85)
        await _implement_via_db(db, pid, need)
        await async_client.post(f"{BASE}/projects/{pid}/freeze?aprobado_por=RSEG")

        r = await async_client.post(f"{BASE}/projects/{pid}/unfreeze")
        assert r.status_code == 204


class TestEntryByMeasureEndpoint:

    @pytest.mark.asyncio
    async def test_get_entry_by_measure(self, async_client, db):
        """H12b: GET entry by measure code."""
        pid, _ = await _generate_dda_http(async_client, db)
        r = await async_client.get(f"{BASE}/projects/{pid}/measures/org.1")
        assert r.status_code == 200
        assert r.json()["measure_codigo"] == "org.1"

    @pytest.mark.asyncio
    async def test_get_entry_by_measure_404(self, async_client, db):
        """H12c: 404 for nonexistent measure code."""
        pid, _ = await _generate_dda_http(async_client, db)
        r = await async_client.get(f"{BASE}/projects/{pid}/measures/FAKE.99")
        assert r.status_code == 404


class TestCatalogEndpoint:

    @pytest.mark.asyncio
    async def test_catalog_returns_73(self, async_client, db):
        """H12: GET catalog returns 73 measures."""
        r = await async_client.get(f"{BASE}/measures/catalog")
        assert r.status_code == 200
        assert len(r.json()) == 73
        first = r.json()[0]
        assert "codigo" in first
        assert "nombre" in first
        assert "aplica_basica" in first
