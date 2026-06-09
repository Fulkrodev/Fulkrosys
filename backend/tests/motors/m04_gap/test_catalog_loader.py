"""Tests for Motor 4 gap severity catalog loader."""
import pytest
import yaml

from backend.app.motors.m04_gap.catalog_loader import (
    load_catalog,
    get_medida_rule,
    is_nuclear,
    get_severidad_for_categoria,
    get_esfuerzo_for_categoria,
    is_quick_win_for_categoria,
    get_catalog_version,
    get_total_medidas,
    VALID_SEVERIDADES,
)
from backend.app.motors.m04_gap.exceptions import (
    SeverityCatalogNotFoundError,
    SeverityCatalogParseError,
)


class TestLoadCatalog:

    def test_load_catalog_default_path_ok(self):
        catalog = load_catalog()
        assert isinstance(catalog, dict)
        assert "medidas" in catalog
        assert "thresholds" in catalog
        assert "medidas_criticas_nucleares" in catalog

    def test_load_catalog_returns_73_medidas(self):
        catalog = load_catalog()
        assert len(catalog["medidas"]) == 73

    def test_load_catalog_has_16_familias(self):
        catalog = load_catalog()
        familias = {m["familia"] for m in catalog["medidas"]}
        expected = {
            "org", "op.pl", "op.acc", "op.exp", "op.ext", "op.nub",
            "op.cont", "op.mon", "mp.if", "mp.per", "mp.eq", "mp.com",
            "mp.si", "mp.sw", "mp.info", "mp.s",
        }
        assert familias == expected

    def test_load_catalog_missing_file_raises(self, tmp_path):
        with pytest.raises(SeverityCatalogNotFoundError):
            load_catalog(catalog_path=tmp_path / "nonexistent.yaml")

    def test_load_catalog_malformed_yaml_raises(self, tmp_path):
        bad = tmp_path / "bad.yaml"
        bad.write_text("medidas: [{{invalid")
        with pytest.raises(SeverityCatalogParseError):
            load_catalog(catalog_path=bad)

    def test_load_catalog_missing_medidas_key_raises(self, tmp_path):
        f = tmp_path / "no_medidas.yaml"
        f.write_text(yaml.dump({"thresholds": {}, "medidas_criticas_nucleares": []}))
        with pytest.raises(SeverityCatalogParseError, match="Missing 'medidas'"):
            load_catalog(catalog_path=f)

    def test_load_catalog_missing_thresholds_raises(self, tmp_path):
        f = tmp_path / "no_thresh.yaml"
        f.write_text(yaml.dump({"medidas": [], "medidas_criticas_nucleares": []}))
        with pytest.raises(SeverityCatalogParseError, match="Missing 'thresholds'"):
            load_catalog(catalog_path=f)

    def test_load_catalog_invalid_severidad_in_medida_raises(self, tmp_path):
        f = tmp_path / "bad_sev.yaml"
        content = {
            "version": "1.0",
            "medidas_criticas_nucleares": [],
            "thresholds": {"quick_win_max_horas": 24, "quick_win_min_severidad_numeric": 4},
            "medidas": [{
                "codigo": "org.1", "nombre": "Test", "familia": "org",
                "marco": "organizativo", "aplica_desde": "basica",
                "severidad_base": {"basica": "INVENTADA", "media": "alta", "alta": "alta"},
                "esfuerzo_horas_base": {"basica": 8, "media": 16, "alta": 24},
                "quick_win": False,
                "guia_remediacion": "", "evidencia_tipica": "", "notas_auditor": "",
            }],
        }
        f.write_text(yaml.dump(content))
        with pytest.raises(SeverityCatalogParseError, match="invalid severidad"):
            load_catalog(catalog_path=f)

    def test_load_catalog_missing_required_field_raises(self, tmp_path):
        f = tmp_path / "missing_field.yaml"
        content = {
            "version": "1.0",
            "medidas_criticas_nucleares": [],
            "thresholds": {"quick_win_max_horas": 24},
            "medidas": [{"codigo": "org.1"}],  # Missing most fields
        }
        f.write_text(yaml.dump(content))
        with pytest.raises(SeverityCatalogParseError, match="missing field"):
            load_catalog(catalog_path=f)


    def test_load_catalog_root_not_dict_raises(self, tmp_path):
        """YAML with list root raises CatalogParseError."""
        f = tmp_path / "list.yaml"
        f.write_text("- item1\n- item2\n")
        with pytest.raises(SeverityCatalogParseError, match="root is not a dict"):
            load_catalog(catalog_path=f)

    def test_load_catalog_missing_nucleares_key_raises(self, tmp_path):
        """Missing medidas_criticas_nucleares key raises."""
        f = tmp_path / "no_nuc.yaml"
        f.write_text(yaml.dump({"medidas": [], "thresholds": {}}))
        with pytest.raises(SeverityCatalogParseError, match="Missing 'medidas_criticas_nucleares'"):
            load_catalog(catalog_path=f)

    def test_load_catalog_medidas_not_list_raises(self, tmp_path):
        """medidas as string raises."""
        f = tmp_path / "str.yaml"
        f.write_text(yaml.dump({
            "medidas": "not_a_list",
            "medidas_criticas_nucleares": [],
            "thresholds": {},
        }))
        with pytest.raises(SeverityCatalogParseError, match="not a list"):
            load_catalog(catalog_path=f)

    def test_load_catalog_invalid_severidad_base_structure_raises(self, tmp_path):
        """severidad_base with wrong keys raises."""
        f = tmp_path / "bad_struct.yaml"
        content = {
            "version": "1.0",
            "medidas_criticas_nucleares": [],
            "thresholds": {"quick_win_max_horas": 24},
            "medidas": [{
                "codigo": "org.1", "nombre": "T", "familia": "org",
                "marco": "organizativo", "aplica_desde": "basica",
                "severidad_base": {"wrong_key": "alta"},  # Missing basica/media/alta
                "esfuerzo_horas_base": {"basica": 8, "media": 16, "alta": 24},
                "quick_win": False,
                "guia_remediacion": "", "evidencia_tipica": "", "notas_auditor": "",
            }],
        }
        f.write_text(yaml.dump(content))
        with pytest.raises(SeverityCatalogParseError, match="invalid severidad_base structure"):
            load_catalog(catalog_path=f)


class TestCatalogHelpers:

    def test_get_medida_rule_returns_correct_rule(self):
        catalog = load_catalog()
        rule = get_medida_rule(catalog, "op.acc.6")
        assert rule is not None
        assert rule["codigo"] == "op.acc.6"
        assert "severidad_base" in rule

    def test_get_medida_rule_unknown_returns_none(self):
        catalog = load_catalog()
        assert get_medida_rule(catalog, "FAKE.99") is None

    def test_is_nuclear_for_critical_measures(self):
        catalog = load_catalog()
        assert is_nuclear(catalog, "op.acc.6") is True
        assert is_nuclear(catalog, "mp.info.3") is True
        assert is_nuclear(catalog, "op.exp.7") is True
        # Non-nuclear
        assert is_nuclear(catalog, "org.4") is False

    def test_get_severidad_for_categoria(self):
        catalog = load_catalog()
        # op.acc.6 should be critica for media systems
        sev = get_severidad_for_categoria(catalog, "op.acc.6", "MEDIA")
        assert sev == "critica"

    def test_is_quick_win_for_categoria(self):
        catalog = load_catalog()
        # org.1 in BASICA: critica severity + 8h effort = quick win
        assert is_quick_win_for_categoria(catalog, "org.1", "BASICA") is True

    def test_get_severidad_unknown_medida_returns_none(self):
        catalog = load_catalog()
        assert get_severidad_for_categoria(catalog, "FAKE.99", "MEDIA") is None

    def test_get_esfuerzo_unknown_medida_returns_none(self):
        catalog = load_catalog()
        assert get_esfuerzo_for_categoria(catalog, "FAKE.99", "MEDIA") is None

    def test_get_total_medidas_is_73(self):
        catalog = load_catalog()
        assert get_total_medidas(catalog) == 73

    def test_get_catalog_version(self):
        catalog = load_catalog()
        v = get_catalog_version(catalog)
        assert v == "1.0"
