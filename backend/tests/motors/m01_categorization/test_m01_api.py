"""
Tests for Motor 1 — Categorization Engine REST API (HTTP integration tests).

Tests exercise the actual FastAPI endpoints via httpx AsyncClient,
covering the full HTTP request/response cycle including Pydantic
validation, RLS tenant context, and database persistence.

Each test that validates ENS logic cites RD 311/2022 Anexo I.
"""
import uuid
import pytest
from sqlalchemy import text

from backend.tests.conftest import setup_test_project, _admin_setup


# ================================================================
# SYSTEM CRUD (2 tests)
# ================================================================

class TestSystemHTTP:
    """HTTP tests for system creation and listing."""

    @pytest.mark.asyncio
    async def test_create_system_returns_201(self, async_client, db):
        """POST /systems devuelve 201 con system_id."""
        _, project_id = await setup_test_project(db)

        response = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Sistema HTTP Test", "descripcion": "Desc", "frontera": "Local"},
        )
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data
        assert data["nombre"] == "Sistema HTTP Test"
        assert data["project_id"] == project_id

    @pytest.mark.asyncio
    async def test_list_systems_returns_empty_initially(self, async_client, db):
        """GET /systems de proyecto nuevo devuelve lista vacia 200."""
        _, project_id = await setup_test_project(db)

        response = await async_client.get(
            f"/api/v1/categorization/projects/{project_id}/systems"
        )
        assert response.status_code == 200
        assert response.json() == []


# ================================================================
# DATA LOADING (2 tests)
# ================================================================

class TestDataLoadingHTTP:
    """HTTP tests for information types and services batch loading."""

    @pytest.mark.asyncio
    async def test_create_information_types_batch_returns_201(self, async_client, db):
        """POST /information-types con 2 items devuelve 201."""
        _, project_id = await setup_test_project(db)
        sys_resp = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Sistema IT"},
        )
        system_id = sys_resp.json()["id"]

        response = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/information-types",
            json={"items": [
                {"nombre": "Datos personales", "valoracion_d": "MEDIO", "valoracion_i": "ALTO",
                 "valoracion_c": "ALTO", "valoracion_a": "MEDIO", "valoracion_t": "BAJO"},
                {"nombre": "Info gestion", "valoracion_d": "BAJO", "valoracion_i": "MEDIO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
            ]},
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data) == 2
        assert data[0]["nombre"] == "Datos personales"
        assert data[0]["valoracion_i"] == "ALTO"

    @pytest.mark.asyncio
    async def test_invalid_dicat_value_returns_422(self, async_client, db):
        """POST /information-types con valor DICAT invalido devuelve 422.

        Pydantic Literal['BAJO','MEDIO','ALTO'] rechaza valores fuera de rango.
        """
        _, project_id = await setup_test_project(db)
        sys_resp = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Sistema 422"},
        )
        system_id = sys_resp.json()["id"]

        response = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/information-types",
            json={"items": [
                {"nombre": "Bad", "valoracion_d": "INVALIDO"},
            ]},
        )
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"


# ================================================================
# CATEGORIZATION (5 tests)
# ================================================================

class TestCategorizationHTTP:
    """HTTP tests for the categorization endpoint."""

    async def _setup_system_with_data(self, async_client, db, info_types):
        """Helper: create project + system + load info_types."""
        _, project_id = await setup_test_project(db)
        sys_resp = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Sistema Cat"},
        )
        system_id = sys_resp.json()["id"]
        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/information-types",
            json={"items": info_types},
        )
        return system_id

    @pytest.mark.asyncio
    async def test_categorize_basic_all_low(self, async_client, db):
        """Todas dimensiones BAJO -> BASICA.

        RD 311/2022 Anexo I: 'La categoria del sistema vendra determinada
        por la valoracion mas alta de cualquiera de sus dimensiones.'
        """
        system_id = await self._setup_system_with_data(async_client, db, [
            {"nombre": "Info", "valoracion_d": "BAJO", "valoracion_i": "BAJO",
             "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
        ])
        response = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/categorize",
            json={},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["categoria_resultante"] == "BASICA", (
            f"Todas BAJO -> BASICA (RD 311/2022 Anexo I), got {data['categoria_resultante']}"
        )

    @pytest.mark.asyncio
    async def test_categorize_media_one_medium(self, async_client, db):
        """D=MEDIO resto BAJO -> MEDIA por regla del maximo.

        RD 311/2022 Anexo I.
        """
        system_id = await self._setup_system_with_data(async_client, db, [
            {"nombre": "Info", "valoracion_d": "MEDIO", "valoracion_i": "BAJO",
             "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
        ])
        response = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/categorize",
            json={},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["categoria_resultante"] == "MEDIA"
        assert data["determining_dimension"] == "D"

    @pytest.mark.asyncio
    async def test_categorize_alta_one_high(self, async_client, db):
        """C=ALTO resto BAJO -> ALTA por regla del maximo.

        RD 311/2022 Anexo I.
        """
        system_id = await self._setup_system_with_data(async_client, db, [
            {"nombre": "Info", "valoracion_d": "BAJO", "valoracion_i": "BAJO",
             "valoracion_c": "ALTO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
        ])
        response = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/categorize",
            json={},
        )
        assert response.status_code == 200
        assert response.json()["categoria_resultante"] == "ALTA"

    @pytest.mark.asyncio
    async def test_categorize_409_when_no_data(self, async_client, db):
        """Categorizar sin datos devuelve 409.

        Prerequisito: al menos 1 information_type o 1 service.
        """
        _, project_id = await setup_test_project(db)
        sys_resp = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Sistema vacio"},
        )
        system_id = sys_resp.json()["id"]

        response = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/categorize",
            json={},
        )
        assert response.status_code == 409, f"Expected 409, got {response.status_code}: {response.text}"

    @pytest.mark.asyncio
    async def test_categorize_max_across_info_and_services(self, async_client, db):
        """Info BAJO + Service ALTO -> ALTA por regla del maximo.

        RD 311/2022 Anexo I: el maximo se toma sobre TODAS las valoraciones.
        """
        _, project_id = await setup_test_project(db)
        sys_resp = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Sistema mix"},
        )
        system_id = sys_resp.json()["id"]

        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/information-types",
            json={"items": [
                {"nombre": "Info baja", "valoracion_d": "BAJO", "valoracion_i": "BAJO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
            ]},
        )
        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/services",
            json={"items": [
                {"nombre": "Svc critico", "valoracion_d": "ALTO", "valoracion_i": "BAJO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
            ]},
        )

        response = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/categorize",
            json={},
        )
        assert response.status_code == 200
        assert response.json()["categoria_resultante"] == "ALTA"


# ================================================================
# INHERITED AAPP FLOOR (#5 · Sub-bloque E)
# ================================================================

class TestInheritedFloorHTTP:
    """HTTP tests · suelo AAPP endpoints (PUT/GET) + categorización e2e + cabo."""

    @pytest.mark.asyncio
    async def test_put_floor_sets_and_elevates(self, async_client, db):
        """PUT suelo MEDIA en proyecto sin categoría → persiste + eleva a MEDIA."""
        _, project_id = await setup_test_project(db)
        r = await async_client.put(
            f"/api/v1/categorization/projects/{project_id}/inherited-floor",
            json={"categoria_heredada_aapp": "MEDIA"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["categoria_heredada_aapp"] == "MEDIA"
        assert data["categoria_objetivo"] == "MEDIA"
        assert data["categoria_objetivo_elevated"] is True
        assert data["level"] == "N1"
        assert data["regenerated"] == []

    @pytest.mark.asyncio
    async def test_put_floor_does_not_lower_categoria_objetivo(self, async_client, db):
        """categoria_objetivo=ALTA + PUT suelo MEDIA → sigue ALTA (no baja)."""
        _, project_id = await setup_test_project(db)
        async with _admin_setup(db):
            await db.execute(
                text("UPDATE projects SET categoria_objetivo='ALTA' WHERE id=:pid"),
                {"pid": project_id},
            )
        r = await async_client.put(
            f"/api/v1/categorization/projects/{project_id}/inherited-floor",
            json={"categoria_heredada_aapp": "MEDIA"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["categoria_objetivo"] == "ALTA"
        assert data["categoria_objetivo_elevated"] is False

    @pytest.mark.asyncio
    async def test_get_floor_roundtrip(self, async_client, db):
        """GET devuelve el suelo fijado por PUT."""
        _, project_id = await setup_test_project(db)
        await async_client.put(
            f"/api/v1/categorization/projects/{project_id}/inherited-floor",
            json={"categoria_heredada_aapp": "ALTA"},
        )
        r = await async_client.get(
            f"/api/v1/categorization/projects/{project_id}/inherited-floor",
        )
        assert r.status_code == 200
        assert r.json()["categoria_heredada_aapp"] == "ALTA"

    @pytest.mark.asyncio
    async def test_categorize_respects_floor_e2e(self, async_client, db):
        """#5 e2e · DICAT todo BAJO + suelo MEDIA → categoriza MEDIA + cita herencia.

        Cubre compute_for_system: el suelo del proyecto se resuelve y aplica en
        la categorización per-system (RD 311/2022 Anexo I + herencia AAPP).
        """
        _, project_id = await setup_test_project(db)
        await async_client.put(
            f"/api/v1/categorization/projects/{project_id}/inherited-floor",
            json={"categoria_heredada_aapp": "MEDIA"},
        )
        sys_resp = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Sistema Floor"},
        )
        system_id = sys_resp.json()["id"]
        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/information-types",
            json={"items": [
                {"nombre": "Info", "valoracion_d": "BAJO", "valoracion_i": "BAJO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
            ]},
        )
        r = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/categorize",
            json={},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["categoria_resultante"] == "MEDIA", (
            "el suelo AAPP eleva BASICA→MEDIA en la categorización per-system"
        )
        assert "herencia de la AAPP" in (data["justification"] or "")

    @pytest.mark.asyncio
    async def test_put_floor_n2_with_plan_regenerates(self, async_client, db):
        """#5 cabo N2 · plan borrador existente + suelo MEDIA → eleva + regenera
        el plan a la categoría nueva (la verificación profunda está en
        test_floor_elevation_levels.py)."""
        _, project_id = await setup_test_project(db)
        async with _admin_setup(db):
            await db.execute(
                text("UPDATE projects SET categoria_objetivo='BASICA' WHERE id=:p"),
                {"p": project_id},
            )
            await db.execute(
                text(
                    "INSERT INTO project_plans "
                    "(id, project_id, version, categoria, estado, created_at) "
                    "VALUES (:id, :pid, 1, 'BASICA', 'active', now())"
                ),
                {"id": str(uuid.uuid4()), "pid": project_id},
            )
        r = await async_client.put(
            f"/api/v1/categorization/projects/{project_id}/inherited-floor",
            json={"categoria_heredada_aapp": "MEDIA"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["level"] == "N2"
        assert data["categoria_objetivo"] == "MEDIA"
        assert "plan" in data["regenerated"]
        active = (await db.execute(
            text(
                "SELECT categoria FROM project_plans "
                "WHERE project_id = :p AND deleted_at IS NULL"
            ),
            {"p": project_id},
        )).all()
        assert len(active) == 1 and active[0][0] == "MEDIA"


# ================================================================
# RESULT + ACTA + DIMENSIONS (4 tests)
# ================================================================

class TestResultActaDimensionsHTTP:
    """HTTP tests for result, acta E-012, and dimensions endpoints."""

    @pytest.mark.asyncio
    async def test_get_result_404_if_not_categorized(self, async_client, db):
        """GET /result sin categorizacion devuelve 404."""
        _, project_id = await setup_test_project(db)
        sys_resp = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Sistema sin cat"},
        )
        system_id = sys_resp.json()["id"]

        response = await async_client.get(
            f"/api/v1/categorization/systems/{system_id}/result"
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_result_returns_persisted_categorization(self, async_client, db):
        """Tras categorize, GET /result devuelve la misma categorizacion."""
        _, project_id = await setup_test_project(db)
        sys_resp = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Sistema persistido"},
        )
        system_id = sys_resp.json()["id"]
        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/information-types",
            json={"items": [
                {"nombre": "Info", "valoracion_d": "MEDIO", "valoracion_i": "BAJO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
            ]},
        )
        cat_resp = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/categorize",
            json={"aprobado_por": "Test User"},
        )
        assert cat_resp.status_code == 200

        result_resp = await async_client.get(
            f"/api/v1/categorization/systems/{system_id}/result"
        )
        assert result_resp.status_code == 200
        data = result_resp.json()
        assert data["categoria_resultante"] == "MEDIA"
        assert data["aprobado_por"] == "Test User"

    @pytest.mark.asyncio
    async def test_acta_e012_returns_markdown_and_metadata(self, async_client, db):
        """GET /acta-e012 devuelve markdown_content + metadata.

        CCN-STIC 803: el acta debe contener la categoria, la valoracion
        por dimensiones, y la base normativa (RD 311/2022).
        """
        _, project_id = await setup_test_project(db)
        sys_resp = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Sistema Acta"},
        )
        system_id = sys_resp.json()["id"]
        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/information-types",
            json={"items": [
                {"nombre": "Datos", "valoracion_d": "ALTO", "valoracion_i": "MEDIO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
            ]},
        )
        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/categorize",
            json={"aprobado_por": "Marcos Mata"},
        )

        response = await async_client.get(
            f"/api/v1/categorization/systems/{system_id}/acta-e012"
        )
        assert response.status_code == 200
        data = response.json()
        assert "markdown_content" in data
        assert "metadata" in data
        assert "E-012" in data["markdown_content"]
        assert "Real Decreto 311/2022" in data["markdown_content"]
        assert data["metadata"]["category"] == "ALTA"

    @pytest.mark.asyncio
    async def test_acta_e012_409_if_not_categorized(self, async_client, db):
        """GET /acta-e012 sin categorizacion previa devuelve 409."""
        _, project_id = await setup_test_project(db)
        sys_resp = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Sistema sin acta"},
        )
        system_id = sys_resp.json()["id"]

        response = await async_client.get(
            f"/api/v1/categorization/systems/{system_id}/acta-e012"
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_dimensions_summary_max_rule(self, async_client, db):
        """GET /dimensions aplica regla del maximo sobre multiples info_types.

        Info type 1: D=BAJO. Info type 2: D=ALTO. max_d debe ser ALTO.
        RD 311/2022 Anexo I.
        """
        _, project_id = await setup_test_project(db)
        sys_resp = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Sistema dims"},
        )
        system_id = sys_resp.json()["id"]
        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/information-types",
            json={"items": [
                {"nombre": "Info baja", "valoracion_d": "BAJO", "valoracion_i": "MEDIO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
                {"nombre": "Info alta", "valoracion_d": "ALTO", "valoracion_i": "BAJO",
                 "valoracion_c": "MEDIO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
            ]},
        )

        response = await async_client.get(
            f"/api/v1/categorization/systems/{system_id}/dimensions"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["max_d"] == "ALTO", (
            f"max_d esperado ALTO (RD 311/2022 maximo), got {data['max_d']}"
        )
        assert data["max_i"] == "MEDIO"
        assert data["projected_category"] == "ALTA"
        assert data["info_types_count"] == 2



# ================================================================
# 404 EDGE CASES (3 tests for full api.py coverage)
# ================================================================

class TestNotFoundHTTP:
    """Tests for 404 responses when resources do not exist."""

    @pytest.mark.asyncio
    async def test_create_system_404_if_project_not_found(self, async_client, db):
        """POST /systems con project_id inexistente devuelve 404."""
        fake_project_id = str(uuid.uuid4())
        response = await async_client.post(
            f"/api/v1/categorization/projects/{fake_project_id}/systems",
            json={"nombre": "Test", "descripcion": "Test"},
        )
        assert response.status_code == 404, (
            f"Expected 404 for nonexistent project, got {response.status_code}"
        )

    @pytest.mark.asyncio
    async def test_list_systems_404_if_project_not_found(self, async_client, db):
        """GET /systems con project_id inexistente devuelve 404."""
        fake_project_id = str(uuid.uuid4())
        response = await async_client.get(
            f"/api/v1/categorization/projects/{fake_project_id}/systems"
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_system_endpoints_404_if_system_not_found(self, async_client, db):
        """Endpoints con system_id inexistente devuelven 404."""
        fake_system_id = str(uuid.uuid4())

        r1 = await async_client.get(
            f"/api/v1/categorization/systems/{fake_system_id}/result"
        )
        assert r1.status_code == 404

        r2 = await async_client.get(
            f"/api/v1/categorization/systems/{fake_system_id}/dimensions"
        )
        assert r2.status_code == 404



# ================================================================
# REPLACE SEMANTICS (2 tests for idempotency)
# ================================================================

class TestReplaceSemanticsHTTP:
    """Tests for replace-mode batch endpoints (TODO-11)."""

    @pytest.mark.asyncio
    async def test_post_information_types_replaces_existing(self, async_client, db):
        """Calling POST /information-types twice replaces the first batch.

        First call: load 2 items. Second call: load 3 different items.
        Result: only the 3 from the second call should exist.
        """
        _, project_id = await setup_test_project(db)
        sys_resp = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Sistema Replace IT"},
        )
        system_id = sys_resp.json()["id"]

        # First batch: 2 items
        r1 = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/information-types",
            json={"items": [
                {"nombre": "Info A", "valoracion_d": "BAJO", "valoracion_i": "BAJO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
                {"nombre": "Info B", "valoracion_d": "MEDIO", "valoracion_i": "BAJO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
            ]},
        )
        assert r1.status_code == 201
        assert len(r1.json()) == 2

        # Second batch: 3 different items (should REPLACE, not append)
        r2 = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/information-types",
            json={"items": [
                {"nombre": "Info X", "valoracion_d": "ALTO", "valoracion_i": "BAJO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
                {"nombre": "Info Y", "valoracion_d": "BAJO", "valoracion_i": "ALTO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
                {"nombre": "Info Z", "valoracion_d": "BAJO", "valoracion_i": "BAJO",
                 "valoracion_c": "ALTO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
            ]},
        )
        assert r2.status_code == 201
        data = r2.json()
        assert len(data) == 3, (
            f"Replace: expected 3 items (2nd batch), got {len(data)}"
        )
        names = {item["nombre"] for item in data}
        assert names == {"Info X", "Info Y", "Info Z"}, (
            f"Replace: expected only 2nd batch items, got {names}"
        )

    @pytest.mark.asyncio
    async def test_post_services_replaces_existing(self, async_client, db):
        """Calling POST /services twice replaces the first batch."""
        _, project_id = await setup_test_project(db)
        sys_resp = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Sistema Replace Svc"},
        )
        system_id = sys_resp.json()["id"]

        # First batch: 1 service
        r1 = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/services",
            json={"items": [
                {"nombre": "Svc Old", "valoracion_d": "BAJO", "valoracion_i": "BAJO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
            ]},
        )
        assert r1.status_code == 201

        # Second batch: 2 services (should REPLACE)
        r2 = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/services",
            json={"items": [
                {"nombre": "Svc New A", "valoracion_d": "ALTO", "valoracion_i": "BAJO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
                {"nombre": "Svc New B", "valoracion_d": "BAJO", "valoracion_i": "ALTO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
            ]},
        )
        assert r2.status_code == 201
        data = r2.json()
        assert len(data) == 2, (
            f"Replace: expected 2 services (2nd batch), got {len(data)}"
        )
        names = {item["nombre"] for item in data}
        assert names == {"Svc New A", "Svc New B"}, (
            f"Replace: expected only 2nd batch services, got {names}"
        )



# ================================================================
# UNIQUENESS TESTS (2 tests for system name per project)
# ================================================================

class TestSystemUniquenessHTTP:
    """Tests for unique system name per project constraint."""

    @pytest.mark.asyncio
    async def test_create_system_duplicate_name_returns_409(self, async_client, db):
        """Crear 2 sistemas con mismo nombre en mismo proyecto devuelve 409.

        La unicidad (project_id, nombre) garantiza referencias univocas en
        actas E-012 y trazabilidad de auditoria.
        """
        _, project_id = await setup_test_project(db)

        # Primer sistema: 201
        r1 = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Servidor Documentacion", "descripcion": "Original"},
        )
        assert r1.status_code == 201

        # Segundo con MISMO nombre y MISMO proyecto: 409
        r2 = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Servidor Documentacion", "descripcion": "Duplicado"},
        )
        assert r2.status_code == 409, f"Expected 409, got {r2.status_code}: {r2.text}"
        assert "ya existe" in r2.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_system_same_name_different_projects_allowed(self, async_client, db):
        """Mismo nombre de sistema en proyectos distintos es permitido.

        La unicidad es (project_id, nombre), no global. Un cliente puede
        tener 'Servidor Documentacion' en sus proyectos A y B.
        """

        # Create first project + system
        _, project_id_a = await setup_test_project(db)
        r1 = await async_client.post(
            f"/api/v1/categorization/projects/{project_id_a}/systems",
            json={"nombre": "Servidor Compartido"},
        )
        assert r1.status_code == 201

        # Create second project (different client via setup_test_project)
        _, project_id_b = await setup_test_project(db)

        # Same name but different project: should be 201
        r2 = await async_client.post(
            f"/api/v1/categorization/projects/{project_id_b}/systems",
            json={"nombre": "Servidor Compartido"},
        )
        assert r2.status_code == 201, (
            f"Same name in different project should be allowed. "
            f"Got {r2.status_code}: {r2.text}"
        )



# ================================================================
# SOFT DELETE TESTS (5 tests)
# ================================================================

class TestSoftDeleteHTTP:
    """Tests for soft delete endpoints and behavior."""

    @pytest.mark.asyncio
    async def test_soft_delete_system_returns_204_and_cascades(self, async_client, db):
        """DELETE /systems/{id} soft-deletes system + cascades to info_types + services."""
        from backend.tests.conftest import _admin_setup

        _, project_id = await setup_test_project(db)
        # Create system
        sr = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Sistema a borrar"},
        )
        system_id = sr.json()["id"]

        # Load 2 info_types + 1 service
        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/information-types",
            json={"items": [
                {"nombre": "IT1", "valoracion_d": "BAJO", "valoracion_i": "BAJO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
                {"nombre": "IT2", "valoracion_d": "MEDIO", "valoracion_i": "BAJO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
            ]},
        )
        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/services",
            json={"items": [
                {"nombre": "SVC1", "valoracion_d": "ALTO", "valoracion_i": "BAJO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
            ]},
        )

        # Soft delete the system
        r = await async_client.delete(f"/api/v1/categorization/systems/{system_id}")
        assert r.status_code == 204

        # System should NOT appear in list
        list_r = await async_client.get(
            f"/api/v1/categorization/projects/{project_id}/systems"
        )
        assert len(list_r.json()) == 0, "Soft-deleted system should not appear in list"

        # Verify data still in DB via admin
        async with _admin_setup(db):
            row = await db.execute(
                text("SELECT deleted_at FROM systems WHERE id = :sid"),
                {"sid": system_id},
            )
            sys_del = row.scalar()
            assert sys_del is not None, "System deleted_at should be set"

            it_count = (await db.execute(
                text("SELECT COUNT(*) FROM information_types WHERE system_id = :sid AND deleted_at IS NOT NULL"),
                {"sid": system_id},
            )).scalar()
            assert it_count == 2, f"2 info_types should be soft-deleted, got {it_count}"

            svc_count = (await db.execute(
                text("SELECT COUNT(*) FROM services WHERE system_id = :sid AND deleted_at IS NOT NULL"),
                {"sid": system_id},
            )).scalar()
            assert svc_count == 1, f"1 service should be soft-deleted, got {svc_count}"

    @pytest.mark.asyncio
    async def test_soft_delete_information_type_returns_204(self, async_client, db):
        """DELETE /information-types/{id} soft-deletes a single info_type."""
        _, project_id = await setup_test_project(db)
        sr = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Sistema IT del"},
        )
        system_id = sr.json()["id"]
        itr = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/information-types",
            json={"items": [
                {"nombre": "Para borrar", "valoracion_d": "ALTO", "valoracion_i": "BAJO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
            ]},
        )
        it_id = itr.json()[0]["id"]

        r = await async_client.delete(
            f"/api/v1/categorization/systems/{system_id}/information-types/{it_id}"
        )
        assert r.status_code == 204

    @pytest.mark.asyncio
    async def test_soft_delete_service_returns_204(self, async_client, db):
        """DELETE /services/{id} soft-deletes a single service."""
        _, project_id = await setup_test_project(db)
        sr = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Sistema Svc del"},
        )
        system_id = sr.json()["id"]
        svcr = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/services",
            json={"items": [
                {"nombre": "Para borrar", "valoracion_d": "MEDIO", "valoracion_i": "BAJO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
            ]},
        )
        svc_id = svcr.json()[0]["id"]

        r = await async_client.delete(
            f"/api/v1/categorization/systems/{system_id}/services/{svc_id}"
        )
        assert r.status_code == 204

    @pytest.mark.asyncio
    async def test_categorization_ignores_soft_deleted_items(self, async_client, db):
        """TEST CRITICO: compute_for_system ignora items soft-deleted.

        Crea 2 info_types: uno ALTO (determina ALTA) y uno BAJO.
        Soft-delete el de ALTO. Re-categoriza: ahora debe ser BASICA.
        Esto valida que el calculo ENS respeta soft delete.

        RD 311/2022 Anexo I: la categoria se determina por la valoracion
        mas alta de los items ACTIVOS del sistema.
        """
        _, project_id = await setup_test_project(db)
        sr = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Sistema soft cat"},
        )
        system_id = sr.json()["id"]

        # Load 2 info_types: one ALTO, one BAJO
        itr = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/information-types",
            json={"items": [
                {"nombre": "Info critica", "valoracion_d": "ALTO", "valoracion_i": "BAJO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
                {"nombre": "Info normal", "valoracion_d": "BAJO", "valoracion_i": "BAJO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
            ]},
        )
        alto_id = itr.json()[0]["id"]

        # Categorize: should be ALTA
        cat1 = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/categorize",
            json={},
        )
        assert cat1.json()["categoria_resultante"] == "ALTA"

        # Soft-delete the ALTO info_type
        r = await async_client.delete(
            f"/api/v1/categorization/systems/{system_id}/information-types/{alto_id}"
        )
        assert r.status_code == 204

        # Re-categorize: should now be BASICA (only BAJO remains)
        cat2 = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/categorize",
            json={},
        )
        assert cat2.json()["categoria_resultante"] == "BASICA", (
            f"After soft-deleting ALTO item, category should be BASICA "
            f"(RD 311/2022 Anexo I), got {cat2.json()['categoria_resultante']}"
        )

    @pytest.mark.asyncio
    async def test_replace_mode_soft_deletes_old_items(self, async_client, db):
        """POST batch replace soft-deletes old items instead of physical delete."""
        from backend.tests.conftest import _admin_setup

        _, project_id = await setup_test_project(db)
        sr = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Sistema replace soft"},
        )
        system_id = sr.json()["id"]

        # First batch: 2 items
        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/information-types",
            json={"items": [
                {"nombre": "Old A", "valoracion_d": "BAJO", "valoracion_i": "BAJO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
                {"nombre": "Old B", "valoracion_d": "MEDIO", "valoracion_i": "BAJO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
            ]},
        )

        # Second batch (replace): 1 item
        r2 = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/information-types",
            json={"items": [
                {"nombre": "New C", "valoracion_d": "ALTO", "valoracion_i": "BAJO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
            ]},
        )
        assert len(r2.json()) == 1

        # Verify old items still in DB with deleted_at via admin
        async with _admin_setup(db):
            old_count = (await db.execute(
                text(
                    "SELECT COUNT(*) FROM information_types "
                    "WHERE system_id = :sid AND deleted_at IS NOT NULL"
                ),
                {"sid": system_id},
            )).scalar()
            assert old_count == 2, f"2 old items should be soft-deleted, got {old_count}"

            active_count = (await db.execute(
                text(
                    "SELECT COUNT(*) FROM information_types "
                    "WHERE system_id = :sid AND deleted_at IS NULL"
                ),
                {"sid": system_id},
            )).scalar()
            assert active_count == 1, f"1 new item should be active, got {active_count}"


    @pytest.mark.asyncio
    async def test_soft_delete_already_deleted_system_returns_404(self, async_client, db):
        """DELETE on already-deleted system returns 404."""
        _, project_id = await setup_test_project(db)
        sr = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Sistema doble delete"},
        )
        system_id = sr.json()["id"]

        # First delete: 204
        r1 = await async_client.delete(f"/api/v1/categorization/systems/{system_id}")
        assert r1.status_code == 204

        # Second delete: 404 (already deleted, _get_system_with_rls can still find it
        # but system.deleted_at is not None)
        r2 = await async_client.delete(f"/api/v1/categorization/systems/{system_id}")
        assert r2.status_code == 404

    @pytest.mark.asyncio
    async def test_soft_delete_nonexistent_info_type_returns_404(self, async_client, db):
        """DELETE on nonexistent info_type returns 404."""
        _, project_id = await setup_test_project(db)
        sr = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Sistema 404 IT"},
        )
        system_id = sr.json()["id"]
        fake_id = str(uuid.uuid4())

        r = await async_client.delete(
            f"/api/v1/categorization/systems/{system_id}/information-types/{fake_id}"
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_soft_delete_nonexistent_service_returns_404(self, async_client, db):
        """DELETE on nonexistent service returns 404."""
        _, project_id = await setup_test_project(db)
        sr = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Sistema 404 Svc"},
        )
        system_id = sr.json()["id"]
        fake_id = str(uuid.uuid4())

        r = await async_client.delete(
            f"/api/v1/categorization/systems/{system_id}/services/{fake_id}"
        )
        assert r.status_code == 404



# ================================================================
# CATEGORIZATION HISTORY TESTS (5 tests)
# ================================================================

class TestCategorizationHistoryHTTP:
    """Tests for categorization history with immutable snapshots."""

    @pytest.mark.asyncio
    async def test_compute_persists_version_with_snapshot(self, async_client, db):
        """POST categorize persists a version with input_snapshot."""
        from backend.tests.conftest import _admin_setup

        _, project_id = await setup_test_project(db)
        sr = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Sistema hist 1"},
        )
        system_id = sr.json()["id"]
        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/information-types",
            json={"items": [
                {"nombre": "Info A", "valoracion_d": "ALTO", "valoracion_i": "BAJO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
            ]},
        )
        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/categorize",
            json={"aprobado_por": "Marcos"},
        )

        # Verify via DB that input_snapshot was saved
        async with _admin_setup(db):
            row = await db.execute(
                text("SELECT input_snapshot, version FROM categorizations WHERE system_id = :sid"),
                {"sid": system_id},
            )
            cat = row.mappings().first()
            assert cat is not None
            assert cat["input_snapshot"] is not None
            assert "information_types" in cat["input_snapshot"]
            assert len(cat["input_snapshot"]["information_types"]) == 1
            assert cat["input_snapshot"]["information_types"][0]["valoraciones"]["D"] == "ALTO"
            assert cat["version"] == 1

    @pytest.mark.asyncio
    async def test_history_returns_all_versions_ordered_desc(self, async_client, db):
        """GET /history devuelve todas las versiones DESC por timestamp."""
        _, project_id = await setup_test_project(db)
        sr = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Sistema hist multi"},
        )
        system_id = sr.json()["id"]

        # Version 1: BAJO -> BASICA
        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/information-types",
            json={"items": [
                {"nombre": "Info", "valoracion_d": "BAJO", "valoracion_i": "BAJO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
            ]},
        )
        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/categorize", json={},
        )

        # Version 2: MEDIO -> MEDIA (replace info_types)
        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/information-types",
            json={"items": [
                {"nombre": "Info v2", "valoracion_d": "MEDIO", "valoracion_i": "BAJO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
            ]},
        )
        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/categorize", json={},
        )

        # Version 3: ALTO -> ALTA
        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/information-types",
            json={"items": [
                {"nombre": "Info v3", "valoracion_d": "ALTO", "valoracion_i": "BAJO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
            ]},
        )
        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/categorize", json={},
        )

        # GET history
        r = await async_client.get(
            f"/api/v1/categorization/systems/{system_id}/history"
        )
        assert r.status_code == 200
        history = r.json()
        assert len(history) == 3, f"Expected 3 versions, got {len(history)}"
        # DESC order: latest first
        assert history[0]["categoria_resultante"] == "ALTA"
        assert history[1]["categoria_resultante"] == "MEDIA"
        assert history[2]["categoria_resultante"] == "BASICA"

    @pytest.mark.asyncio
    async def test_history_version_detail_includes_snapshot(self, async_client, db):
        """GET /history/{id} includes full input_snapshot."""
        _, project_id = await setup_test_project(db)
        sr = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Sistema hist detail"},
        )
        system_id = sr.json()["id"]
        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/information-types",
            json={"items": [
                {"nombre": "Datos criticos", "valoracion_d": "ALTO", "valoracion_i": "MEDIO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
            ]},
        )
        cat_r = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/categorize", json={},
        )
        cat_id = cat_r.json()["id"]

        # GET version detail
        r = await async_client.get(
            f"/api/v1/categorization/systems/{system_id}/history/{cat_id}"
        )
        assert r.status_code == 200
        data = r.json()
        assert data["input_snapshot"] is not None
        assert len(data["input_snapshot"]["information_types"]) == 1
        assert data["input_snapshot"]["information_types"][0]["nombre"] == "Datos criticos"
        assert data["input_snapshot"]["information_types"][0]["valoraciones"]["D"] == "ALTO"

    @pytest.mark.asyncio
    async def test_history_isolation_rls(self, async_client, db):
        """Client A cannot see categorization history of Client B."""
        _, project_a = await setup_test_project(db)
        _, project_b = await setup_test_project(db)

        # Create system + categorize for project A
        sr_a = await async_client.post(
            f"/api/v1/categorization/projects/{project_a}/systems",
            json={"nombre": "Sistema A"},
        )
        system_a = sr_a.json()["id"]
        await async_client.post(
            f"/api/v1/categorization/systems/{system_a}/information-types",
            json={"items": [
                {"nombre": "Info A", "valoracion_d": "ALTO", "valoracion_i": "BAJO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
            ]},
        )
        await async_client.post(
            f"/api/v1/categorization/systems/{system_a}/categorize", json={},
        )

        # Create system + categorize for project B
        sr_b = await async_client.post(
            f"/api/v1/categorization/projects/{project_b}/systems",
            json={"nombre": "Sistema B"},
        )
        system_b = sr_b.json()["id"]
        await async_client.post(
            f"/api/v1/categorization/systems/{system_b}/information-types",
            json={"items": [
                {"nombre": "Info B", "valoracion_d": "BAJO", "valoracion_i": "BAJO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
            ]},
        )
        await async_client.post(
            f"/api/v1/categorization/systems/{system_b}/categorize", json={},
        )

        # History of A should only show A categorization
        r = await async_client.get(
            f"/api/v1/categorization/systems/{system_a}/history"
        )
        assert r.status_code == 200
        assert len(r.json()) == 1
        assert r.json()[0]["categoria_resultante"] == "ALTA"

    @pytest.mark.asyncio
    async def test_history_preserves_after_input_changes(self, async_client, db):
        """TEST CRITICO: snapshot is immutable after input changes.

        1. Create info_type ALTO, categorize (v1 snapshot has ALTO)
        2. Replace info_type with BAJO, categorize (v2 snapshot has BAJO)
        3. Verify v1 snapshot STILL shows ALTO (not BAJO)

        This validates real audit immutability.
        """
        _, project_id = await setup_test_project(db)
        sr = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Sistema immutable test"},
        )
        system_id = sr.json()["id"]

        # Version 1: ALTO
        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/information-types",
            json={"items": [
                {"nombre": "Info original", "valoracion_d": "ALTO", "valoracion_i": "BAJO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
            ]},
        )
        v1_resp = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/categorize", json={},
        )
        v1_id = v1_resp.json()["id"]
        assert v1_resp.json()["categoria_resultante"] == "ALTA"

        # Replace info_type with BAJO (replace mode soft-deletes old, inserts new)
        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/information-types",
            json={"items": [
                {"nombre": "Info cambiada", "valoracion_d": "BAJO", "valoracion_i": "BAJO",
                 "valoracion_c": "BAJO", "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
            ]},
        )
        v2_resp = await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/categorize", json={},
        )
        v2_id = v2_resp.json()["id"]
        assert v2_resp.json()["categoria_resultante"] == "BASICA"

        # CRITICAL CHECK: v1 snapshot must STILL show ALTO
        v1_detail = await async_client.get(
            f"/api/v1/categorization/systems/{system_id}/history/{v1_id}"
        )
        assert v1_detail.status_code == 200
        v1_snapshot = v1_detail.json()["input_snapshot"]
        assert v1_snapshot is not None
        assert v1_snapshot["information_types"][0]["valoraciones"]["D"] == "ALTO", (
            f"IMMUTABILITY FAILURE: v1 snapshot should show ALTO but shows "
            f"{v1_snapshot['information_types'][0]['valoraciones']['D']}"
        )

        # v2 snapshot should show BAJO
        v2_detail = await async_client.get(
            f"/api/v1/categorization/systems/{system_id}/history/{v2_id}"
        )
        v2_snapshot = v2_detail.json()["input_snapshot"]
        assert v2_snapshot["information_types"][0]["valoraciones"]["D"] == "BAJO"


    @pytest.mark.asyncio
    async def test_history_version_404_if_not_found(self, async_client, db):
        """GET /history/{fake_id} returns 404."""
        _, project_id = await setup_test_project(db)
        sr = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Sistema hist 404"},
        )
        system_id = sr.json()["id"]
        fake_id = str(uuid.uuid4())
        r = await async_client.get(
            f"/api/v1/categorization/systems/{system_id}/history/{fake_id}"
        )
        assert r.status_code == 404



# ================================================================
# ACTA E-012 PDF/DOCX TESTS (5 tests)
# ================================================================

class TestActaPDFHTTP:
    """Tests for Acta E-012 PDF and DOCX generation endpoints."""

    async def _setup_categorized_system(self, async_client, db):
        """Helper: create system + info_types + categorize. Returns system_id."""
        _, project_id = await setup_test_project(db)
        sr = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Sistema PDF Test", "descripcion": "Test para PDF"},
        )
        system_id = sr.json()["id"]
        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/information-types",
            json={"items": [
                {"nombre": "Datos criticos", "valoracion_d": "ALTO",
                 "valoracion_i": "MEDIO", "valoracion_c": "BAJO",
                 "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
            ]},
        )
        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/categorize",
            json={"aprobado_por": "Test User"},
        )
        return system_id

    @pytest.mark.asyncio
    async def test_generate_acta_pdf_returns_valid_pdf(self, async_client, db):
        """GET /acta-e012.pdf returns application/pdf with valid magic bytes."""
        system_id = await self._setup_categorized_system(async_client, db)

        r = await async_client.get(
            f"/api/v1/categorization/systems/{system_id}/acta-e012.pdf"
        )
        assert r.status_code == 200, f"Got {r.status_code}: {r.text[:200]}"
        assert r.headers["content-type"] == "application/pdf"
        assert r.content[:5] == b"%PDF-", (
            f"Invalid PDF magic bytes: {r.content[:10]}"
        )
        assert len(r.content) > 1000, (
            f"PDF too small ({len(r.content)} bytes), likely empty"
        )

    @pytest.mark.asyncio
    async def test_generate_acta_docx_returns_valid_docx(self, async_client, db):
        """GET /acta-e012.docx returns valid DOCX (ZIP with word/document.xml)."""
        import zipfile
        import io

        system_id = await self._setup_categorized_system(async_client, db)

        r = await async_client.get(
            f"/api/v1/categorization/systems/{system_id}/acta-e012.docx"
        )
        assert r.status_code == 200
        assert "wordprocessingml" in r.headers["content-type"]
        # DOCX is a ZIP file
        assert r.content[:2] == b"PK", "DOCX must start with PK (ZIP magic)"
        # Verify it contains word/document.xml
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        assert "word/document.xml" in zf.namelist(), (
            f"DOCX missing word/document.xml. Files: {zf.namelist()[:5]}"
        )

    @pytest.mark.asyncio
    async def test_acta_pdf_contains_key_data(self, async_client, db):
        """PDF contains system name, category, and RD 311/2022 reference."""
        import pdfplumber
        import io

        system_id = await self._setup_categorized_system(async_client, db)

        r = await async_client.get(
            f"/api/v1/categorization/systems/{system_id}/acta-e012.pdf"
        )
        assert r.status_code == 200

        pdf = pdfplumber.open(io.BytesIO(r.content))
        full_text = " ".join(page.extract_text() or "" for page in pdf.pages)
        pdf.close()

        assert "Sistema PDF Test" in full_text, (
            f"PDF should contain system name. Text: {full_text[:200]}"
        )
        assert "ALTA" in full_text, (
            f"PDF should contain category ALTA. Text: {full_text[:200]}"
        )
        assert "311/2022" in full_text, (
            f"PDF should contain RD 311/2022 reference. Text: {full_text[:200]}"
        )

    @pytest.mark.asyncio
    async def test_acta_pdf_404_when_system_not_found(self, async_client, db):
        """GET /acta-e012.pdf with nonexistent system returns 404."""
        fake_id = str(uuid.uuid4())
        r = await async_client.get(
            f"/api/v1/categorization/systems/{fake_id}/acta-e012.pdf"
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_acta_pdf_404_when_no_categorization(self, async_client, db):
        """GET /acta-e012.pdf on uncategorized system returns 404."""
        _, project_id = await setup_test_project(db)
        sr = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Sistema sin categorizar"},
        )
        system_id = sr.json()["id"]

        r = await async_client.get(
            f"/api/v1/categorization/systems/{system_id}/acta-e012.pdf"
        )
        assert r.status_code == 404



# ================================================================
# ACTA E-012 JSON EXPORT TESTS (4 tests)
# ================================================================

class TestActaJSONHTTP:
    """Tests for Acta E-012 JSON export endpoint."""

    async def _setup_categorized(self, async_client, db):
        """Helper: system + info_type + service + categorize."""
        _, project_id = await setup_test_project(db)
        sr = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Sistema JSON", "descripcion": "Test JSON export"},
        )
        system_id = sr.json()["id"]
        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/information-types",
            json={"items": [
                {"nombre": "Datos personales", "valoracion_d": "ALTO",
                 "valoracion_i": "MEDIO", "valoracion_c": "BAJO",
                 "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
            ]},
        )
        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/services",
            json={"items": [
                {"nombre": "Portal ciudadano", "valoracion_d": "MEDIO",
                 "valoracion_i": "BAJO", "valoracion_c": "BAJO",
                 "valoracion_a": "BAJO", "valoracion_t": "BAJO"},
            ]},
        )
        await async_client.post(
            f"/api/v1/categorization/systems/{system_id}/categorize",
            json={"aprobado_por": "Marcos Mata"},
        )
        return system_id

    @pytest.mark.asyncio
    async def test_acta_json_returns_valid_schema(self, async_client, db):
        """GET /acta-e012.json returns all mandatory schema fields."""
        system_id = await self._setup_categorized(async_client, db)

        r = await async_client.get(
            f"/api/v1/categorization/systems/{system_id}/acta-e012.json"
        )
        assert r.status_code == 200
        data = r.json()

        # Verify all top-level mandatory fields
        assert data["schema"] == "fulkro.acta_e012"
        assert data["schema_version"] == "1.0"
        assert data["document_id"] == "E-012"
        assert "generated_at" in data
        assert "act" in data
        assert "client" in data
        assert "project" in data
        assert "system" in data
        assert "information_types" in data
        assert "services" in data
        assert "result" in data
        assert "justificacion" in data
        assert "normative_basis" in data

        # Verify nested mandatory fields
        assert data["act"]["version"] >= 1
        assert data["client"]["cif"] != ""
        assert data["result"]["categoria_final"] == "ALTA"
        assert data["result"]["determining_dimension"] == "D"
        assert len(data["information_types"]) == 1
        assert len(data["services"]) == 1

    @pytest.mark.asyncio
    async def test_acta_json_dimensions_match_categorization(self, async_client, db):
        """JSON dimensions match what GET /result returns (internal consistency)."""
        system_id = await self._setup_categorized(async_client, db)

        json_r = await async_client.get(
            f"/api/v1/categorization/systems/{system_id}/acta-e012.json"
        )
        result_r = await async_client.get(
            f"/api/v1/categorization/systems/{system_id}/result"
        )

        assert json_r.status_code == 200
        assert result_r.status_code == 200

        json_cat = json_r.json()["result"]["categoria_final"]
        result_cat = result_r.json()["categoria_resultante"]
        assert json_cat == result_cat, (
            f"JSON ({json_cat}) and /result ({result_cat}) must agree"
        )

    @pytest.mark.asyncio
    async def test_acta_json_404_when_no_categorization(self, async_client, db):
        """GET /acta-e012.json on uncategorized system returns 404."""
        _, project_id = await setup_test_project(db)
        sr = await async_client.post(
            f"/api/v1/categorization/projects/{project_id}/systems",
            json={"nombre": "Sin categorizar JSON"},
        )
        system_id = sr.json()["id"]

        r = await async_client.get(
            f"/api/v1/categorization/systems/{system_id}/acta-e012.json"
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_acta_json_404_when_system_not_found(self, async_client, db):
        """GET /acta-e012.json with nonexistent system returns 404."""
        fake_id = str(uuid.uuid4())
        r = await async_client.get(
            f"/api/v1/categorization/systems/{fake_id}/acta-e012.json"
        )
        assert r.status_code == 404
