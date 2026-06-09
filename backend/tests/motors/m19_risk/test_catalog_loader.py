"""Tests for Motor 19 catalog_loader module.

Verifies YAML loading, validation, risk counts by category,
and error handling for missing/malformed catalogs.
"""
from uuid import uuid4

import pytest
import yaml

from backend.app.motors.m19_risk.catalog_loader import (
    load_catalog,
    get_catalog_version,
    get_catalog_total_risks,
    get_risks_by_categoria,
    get_risk_by_codigo,
    catalog_to_project_risk_data,
    VALID_CATEGORIES,
)
from backend.app.motors.m19_risk.exceptions import (
    CatalogNotFoundError,
    CatalogParseError,
)


class TestLoadCatalog:

    def test_load_catalog_default_path_ok(self):
        """Catalog loads successfully from default path."""
        catalog = load_catalog()
        assert isinstance(catalog, dict)
        assert "riesgos_base" in catalog
        assert "version" in catalog

    def test_load_catalog_returns_30_risks(self):
        """Catalog contains exactly 30 base risks."""
        catalog = load_catalog()
        assert len(catalog["riesgos_base"]) == 30

    def test_load_catalog_has_6_categorias(self):
        """All 6 valid categories are represented in the catalog."""
        catalog = load_catalog()
        categorias = {r["categoria"] for r in catalog["riesgos_base"]}
        assert categorias == VALID_CATEGORIES

    def test_load_catalog_missing_file_raises_CatalogNotFoundError(self, tmp_path):
        """Loading from nonexistent path raises CatalogNotFoundError."""
        fake_path = tmp_path / "nonexistent.yaml"
        with pytest.raises(CatalogNotFoundError):
            load_catalog(catalog_path=fake_path)

    def test_load_catalog_malformed_yaml_raises_CatalogParseError(self, tmp_path):
        """Malformed YAML raises CatalogParseError."""
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("riesgos_base: [{{invalid yaml")
        with pytest.raises(CatalogParseError):
            load_catalog(catalog_path=bad_file)

    def test_load_catalog_not_dict_root_raises_CatalogParseError(self, tmp_path):
        """YAML with list at root raises CatalogParseError."""
        bad_file = tmp_path / "list_root.yaml"
        bad_file.write_text("- item1\n- item2\n")
        with pytest.raises(CatalogParseError, match="root is not a dict"):
            load_catalog(catalog_path=bad_file)

    def test_load_catalog_missing_riesgos_base_raises_CatalogParseError(self, tmp_path):
        """YAML dict without riesgos_base key raises CatalogParseError."""
        bad_file = tmp_path / "no_key.yaml"
        bad_file.write_text("version: '1.0'\nother_key: []\n")
        with pytest.raises(CatalogParseError, match="Missing 'riesgos_base'"):
            load_catalog(catalog_path=bad_file)

    def test_load_catalog_riesgos_base_not_list_raises_CatalogParseError(self, tmp_path):
        """riesgos_base as string (not list) raises CatalogParseError."""
        bad_file = tmp_path / "not_list.yaml"
        bad_file.write_text("riesgos_base: 'not a list'\n")
        with pytest.raises(CatalogParseError, match="not a list"):
            load_catalog(catalog_path=bad_file)

    def test_load_catalog_risk_missing_required_field_raises(self, tmp_path):
        """Risk entry missing required field raises CatalogParseError."""
        bad_file = tmp_path / "missing_field.yaml"
        content = {
            "version": "1.0",
            "riesgos_base": [
                {"codigo": "R-001", "titulo": "Test"}
                # Missing: numero, descripcion, categoria, etc.
            ]
        }
        bad_file.write_text(yaml.dump(content))
        with pytest.raises(CatalogParseError, match="missing required field"):
            load_catalog(catalog_path=bad_file)

    def test_load_catalog_risk_invalid_categoria_raises(self, tmp_path):
        """Risk with invalid categoria raises CatalogParseError."""
        bad_file = tmp_path / "bad_cat.yaml"
        content = {
            "version": "1.0",
            "riesgos_base": [{
                "codigo": "R-001",
                "numero": 1,
                "titulo": "Test",
                "descripcion": "Desc",
                "categoria": "INVENTADA",
                "probabilidad_default": 0.5,
                "impacto_dias_default": 10,
                "impacto_euros_default": 1000,
                "owner_default": "PM",
                "trigger_condicion": "test",
                "mitigation_plan": {},
                "contingency_plan": {},
            }]
        }
        bad_file.write_text(yaml.dump(content))
        with pytest.raises(CatalogParseError, match="invalid categoria"):
            load_catalog(catalog_path=bad_file)


class TestCatalogHelpers:

    def test_get_catalog_version_returns_version(self):
        """get_catalog_version returns the version string."""
        catalog = load_catalog()
        version = get_catalog_version(catalog)
        assert isinstance(version, str)
        assert version != "unknown"

    def test_get_catalog_version_unknown_when_missing(self):
        """get_catalog_version returns 'unknown' for dict without version."""
        version = get_catalog_version({"riesgos_base": []})
        assert version == "unknown"

    def test_get_catalog_total_risks(self):
        """get_catalog_total_risks returns 30."""
        catalog = load_catalog()
        assert get_catalog_total_risks(catalog) == 30

    def test_get_risks_by_categoria_returns_correct_count(self):
        """Each category has the expected number of risks."""
        catalog = load_catalog()
        expected = {
            "cliente": 5,
            "personas": 6,
            "presupuesto": 3,
            "normativo": 6,
            "tecnico": 5,
            "comercial": 5,
        }
        for cat, count in expected.items():
            risks = get_risks_by_categoria(catalog, cat)
            assert len(risks) == count, f"Category {cat}: expected {count}, got {len(risks)}"

    def test_get_risk_by_codigo_returns_risk(self):
        """get_risk_by_codigo returns the correct risk entry."""
        catalog = load_catalog()
        risk = get_risk_by_codigo(catalog, "R-001")
        assert risk is not None
        assert risk["codigo"] == "R-001"

    def test_get_risk_by_codigo_not_found_returns_none(self):
        """get_risk_by_codigo returns None for nonexistent codigo."""
        catalog = load_catalog()
        assert get_risk_by_codigo(catalog, "R-999") is None

    def test_catalog_to_project_risk_data_maps_all_fields(self):
        """catalog_to_project_risk_data maps catalog fields to model fields."""
        catalog = load_catalog()
        risk_entry = catalog["riesgos_base"][0]
        project_id = uuid4()
        data = catalog_to_project_risk_data(risk_entry, project_id)

        assert data["project_id"] == project_id
        assert data["risk_code"] == risk_entry["codigo"]
        assert data["titulo"] == risk_entry["titulo"]
        assert data["descripcion"] == risk_entry.get("descripcion")
        assert data["categoria"] == risk_entry["categoria"]
        assert data["probabilidad"] == risk_entry["probabilidad_default"]
        assert data["impacto_dias"] == risk_entry["impacto_dias_default"]
        assert data["impacto_euros"] == risk_entry["impacto_euros_default"]
        assert data["owner"] == risk_entry["owner_default"]
        assert data["status"] == "identificado"
        assert data["mitigation_plan"] == risk_entry["mitigation_plan"]
        assert data["contingency_plan"] == risk_entry["contingency_plan"]
