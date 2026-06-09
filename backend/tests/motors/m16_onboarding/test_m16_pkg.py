"""Tests del Project Knowledge Graph (PKG-lite)."""
import uuid

import pytest

from backend.app.motors.m16_onboarding import pkg_service as pkg
from backend.tests.conftest import setup_test_project


async def _seed_project(db):
    _, project_id = await setup_test_project(db)
    return uuid.UUID(project_id)


class TestPKGNodes:

    @pytest.mark.asyncio
    async def test_add_node(self, db):
        pid = await _seed_project(db)
        nid = await pkg.add_node(db, pid, "person", "Ana Lopez", properties={"role": "sponsor"})
        assert nid is not None
        node = await pkg.get_node(db, nid)
        assert node["label"] == "Ana Lopez"
        assert node["node_type"] == "person"

    @pytest.mark.asyncio
    async def test_add_node_invalid_type(self, db):
        pid = await _seed_project(db)
        with pytest.raises(pkg.PKGError, match="no valido"):
            await pkg.add_node(db, pid, "invalid_type", "X")

    @pytest.mark.asyncio
    async def test_upsert_by_external_id(self, db):
        pid = await _seed_project(db)
        id1 = await pkg.add_node(db, pid, "asset", "Server v1", external_id="srv-001")
        id2 = await pkg.add_node(db, pid, "asset", "Server v2", external_id="srv-001")
        assert id1 == id2
        node = await pkg.get_node(db, id1)
        assert node["label"] == "Server v2"

    @pytest.mark.asyncio
    async def test_get_nodes_by_type(self, db):
        pid = await _seed_project(db)
        await pkg.add_node(db, pid, "person", "Ana")
        await pkg.add_node(db, pid, "person", "Pedro")
        await pkg.add_node(db, pid, "asset", "Server")

        people = await pkg.get_nodes_by_type(db, pid, "person")
        assert len(people) == 2
        assets = await pkg.get_nodes_by_type(db, pid, "asset")
        assert len(assets) == 1

    @pytest.mark.asyncio
    async def test_delete_node_cascades_edges(self, db):
        pid = await _seed_project(db)
        n1 = await pkg.add_node(db, pid, "person", "Ana")
        n2 = await pkg.add_node(db, pid, "system", "ERP")
        await pkg.add_edge(db, pid, n1, n2, "owns")

        await pkg.delete_node(db, n1)
        await db.flush()

        edges = await pkg.get_edges_for_node(db, n2)
        assert len(edges) == 0

    @pytest.mark.asyncio
    async def test_bulk_upsert(self, db):
        pid = await _seed_project(db)
        ids = await pkg.bulk_upsert_nodes(db, pid, [
            {"node_type": "asset", "label": "A1", "external_id": "a1"},
            {"node_type": "asset", "label": "A2", "external_id": "a2"},
            {"node_type": "person", "label": "P1"},
        ])
        assert len(ids) == 3


class TestPKGEdges:

    @pytest.mark.asyncio
    async def test_add_edge(self, db):
        pid = await _seed_project(db)
        n1 = await pkg.add_node(db, pid, "person", "Ana")
        n2 = await pkg.add_node(db, pid, "system", "ERP")
        eid = await pkg.add_edge(db, pid, n1, n2, "owns")
        assert eid is not None

    @pytest.mark.asyncio
    async def test_add_edge_invalid_type(self, db):
        pid = await _seed_project(db)
        n1 = await pkg.add_node(db, pid, "person", "Ana")
        n2 = await pkg.add_node(db, pid, "system", "ERP")
        with pytest.raises(pkg.PKGError, match="no valido"):
            await pkg.add_edge(db, pid, n1, n2, "invalid_edge")

    @pytest.mark.asyncio
    async def test_duplicate_edge_upserts(self, db):
        pid = await _seed_project(db)
        n1 = await pkg.add_node(db, pid, "person", "Ana")
        n2 = await pkg.add_node(db, pid, "system", "ERP")
        e1 = await pkg.add_edge(db, pid, n1, n2, "owns")
        e2 = await pkg.add_edge(db, pid, n1, n2, "owns", properties={"since": "2026"})
        assert e1 == e2


class TestPKGQueries:

    @pytest.mark.asyncio
    async def test_get_neighbors_outgoing(self, db):
        pid = await _seed_project(db)
        ana = await pkg.add_node(db, pid, "person", "Ana")
        erp = await pkg.add_node(db, pid, "system", "ERP")
        crm = await pkg.add_node(db, pid, "system", "CRM")
        await pkg.add_edge(db, pid, ana, erp, "owns")
        await pkg.add_edge(db, pid, ana, crm, "owns")

        neighbors = await pkg.get_neighbors(db, ana, direction="outgoing")
        assert len(neighbors) == 2

    @pytest.mark.asyncio
    async def test_traverse_bfs(self, db):
        pid = await _seed_project(db)
        a = await pkg.add_node(db, pid, "person", "A")
        b = await pkg.add_node(db, pid, "system", "B")
        c = await pkg.add_node(db, pid, "asset", "C")
        await pkg.add_edge(db, pid, a, b, "owns")
        await pkg.add_edge(db, pid, b, c, "depends_on")

        subgraph = await pkg.traverse_bfs(db, a, max_depth=2)
        assert subgraph["total_nodes"] == 3
        assert subgraph["total_edges"] == 2

    @pytest.mark.asyncio
    async def test_project_summary(self, db):
        pid = await _seed_project(db)
        await pkg.add_node(db, pid, "person", "Ana")
        await pkg.add_node(db, pid, "person", "Pedro")
        await pkg.add_node(db, pid, "asset", "Server")

        summary = await pkg.get_project_summary(db, pid)
        assert summary["total_nodes"] == 3
        assert summary["nodes_by_type"]["person"] == 2
        assert summary["nodes_by_type"]["asset"] == 1


class TestPKGAPI:

    @pytest.mark.asyncio
    async def test_summary_empty(self, async_client, db):
        _, project_id = await setup_test_project(db)
        r = await async_client.get(f"/api/v1/onboarding/projects/{project_id}/pkg/summary")
        assert r.status_code == 200
        assert r.json()["total_nodes"] == 0

    @pytest.mark.asyncio
    async def test_list_nodes(self, async_client, db):
        _, project_id = await setup_test_project(db)
        pid = uuid.UUID(project_id)
        await pkg.add_node(db, pid, "person", "Test Person")
        await db.flush()

        r = await async_client.get(f"/api/v1/onboarding/projects/{project_id}/pkg/nodes?node_type=person")
        assert r.status_code == 200
        assert len(r.json()) == 1

    @pytest.mark.asyncio
    async def test_node_detail_404(self, async_client, db):
        _, project_id = await setup_test_project(db)
        r = await async_client.get(f"/api/v1/onboarding/projects/{project_id}/pkg/nodes/{uuid.uuid4()}")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_neighbors(self, async_client, db):
        _, project_id = await setup_test_project(db)
        pid = uuid.UUID(project_id)
        n1 = await pkg.add_node(db, pid, "person", "Owner")
        n2 = await pkg.add_node(db, pid, "system", "App")
        await pkg.add_edge(db, pid, n1, n2, "owns")
        await db.flush()

        r = await async_client.get(
            f"/api/v1/onboarding/projects/{project_id}/pkg/nodes/{n1}/neighbors?direction=outgoing"
        )
        assert r.status_code == 200
        assert len(r.json()) == 1

    @pytest.mark.asyncio
    async def test_ingest_onboarding_requires_completed(self, async_client, db):
        _, project_id = await setup_test_project(db)
        r = await async_client.post(
            f"/api/v1/onboarding/projects/{project_id}/pkg/ingest-from-onboarding/{uuid.uuid4()}"
        )
        assert r.status_code == 422
