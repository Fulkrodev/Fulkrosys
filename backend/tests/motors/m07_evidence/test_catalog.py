"""Tests for Motor 7 evidence types catalog and loader."""
import pytest

from backend.app.motors.m07_evidence.catalog_loader import (
    load_catalog,
    get_type_by_id,
    get_types_by_categoria,
    get_types_for_measure,
    get_all_categorias,
    reset_cache,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    """Reset catalog cache between tests."""
    reset_cache()
    yield
    reset_cache()


class TestCatalogLoading:

    def test_loads_catalog_with_12_types(self):
        catalog = load_catalog()
        assert len(catalog.types) >= 12

    def test_no_duplicate_ids(self):
        catalog = load_catalog()
        ids = [t.id for t in catalog.types]
        assert len(ids) == len(set(ids)), f"Duplicate IDs found: {[x for x in ids if ids.count(x) > 1]}"

    def test_all_mime_types_valid(self):
        catalog = load_catalog()
        for t in catalog.types:
            for mime in t.mime_types_permitidos:
                assert "/" in mime, f"Invalid MIME type '{mime}' in {t.id}"

    def test_all_extensions_start_with_dot(self):
        catalog = load_catalog()
        for t in catalog.types:
            for ext in t.extensiones_permitidas:
                assert ext.startswith("."), f"Extension '{ext}' in {t.id} missing dot"

    def test_caducidad_realistic(self):
        """All caducidad values are null or between 1 and 3650 days."""
        catalog = load_catalog()
        for t in catalog.types:
            if t.caducidad_dias is not None:
                assert 1 <= t.caducidad_dias <= 3650, (
                    f"Unrealistic caducidad {t.caducidad_dias} in {t.id}"
                )


class TestCatalogQueries:

    def test_get_by_id_known(self):
        t = get_type_by_id("EVT-politica_firmada-001")
        assert t is not None
        assert t.nombre == "Politica firmada"
        assert t.categoria == "politica"

    def test_get_by_id_unknown(self):
        assert get_type_by_id("EVT-nonexistent-999") is None

    def test_get_by_categoria_informe(self):
        informes = get_types_by_categoria("informe")
        assert len(informes) >= 3
        for t in informes:
            assert t.categoria == "informe"

    def test_get_for_measure_org1(self):
        types = get_types_for_measure("org.1")
        assert len(types) >= 2
        ids = [t.id for t in types]
        assert "EVT-politica_firmada-001" in ids
        assert "EVT-acta_comite-001" in ids

    def test_critical_categories_present(self):
        """Key categories must exist: politica, acta, captura, export, certificado, informe."""
        categorias = get_all_categorias()
        expected = {"politica", "acta", "captura", "export", "certificado", "informe"}
        assert expected.issubset(categorias), f"Missing categories: {expected - categorias}"
