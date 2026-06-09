"""Tests for Motor 6 template catalog loader."""
import pytest
import yaml

from backend.app.motors.m06_document_factory.catalog_loader import (
    load_catalog,
    get_template_metadata,
    list_templates_by_categoria,
    list_templates_by_familia,
    get_catalog_version,
    get_total_templates,
    _normalize_placeholders,
    get_required_vars,
)
from backend.app.motors.m06_document_factory.exceptions import CatalogLoadError


class TestLoadCatalog:

    def test_load_catalog_default_path_ok(self):
        catalog = load_catalog()
        assert isinstance(catalog, dict)
        assert "templates" in catalog

    def test_total_templates_gte_60(self):
        catalog = load_catalog()
        assert len(catalog["templates"]) >= 60

    def test_get_total_templates(self):
        catalog = load_catalog()
        assert get_total_templates(catalog) >= 60

    def test_get_catalog_version(self):
        catalog = load_catalog()
        v = get_catalog_version(catalog)
        assert isinstance(v, str)
        assert v != "unknown"

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(CatalogLoadError):
            load_catalog(catalog_path=tmp_path / "missing.yaml")

    def test_malformed_yaml_raises(self, tmp_path):
        f = tmp_path / "bad.yaml"
        f.write_text("[{{invalid")
        with pytest.raises(CatalogLoadError):
            load_catalog(catalog_path=f)

    def test_missing_templates_key_raises(self, tmp_path):
        f = tmp_path / "no_key.yaml"
        f.write_text(yaml.dump({"version": "1.0"}))
        with pytest.raises(CatalogLoadError):
            load_catalog(catalog_path=f)

    def test_E100_exists_and_is_politica(self):
        catalog = load_catalog()
        meta = get_template_metadata(catalog, "E-100")
        assert meta is not None
        assert meta["categoria"] == "politica"
        assert meta["nombre"] == "Politica de Seguridad de la Informacion"

    def test_E204_exists_and_is_procedimiento(self):
        catalog = load_catalog()
        meta = get_template_metadata(catalog, "E-204")
        assert meta is not None
        assert meta["categoria"] == "procedimiento"

    def test_P001_exists_and_is_comercial(self):
        catalog = load_catalog()
        meta = get_template_metadata(catalog, "P-001")
        assert meta is not None
        assert meta["categoria"] == "comercial"

    def test_E400_exists_and_is_entregable(self):
        catalog = load_catalog()
        meta = get_template_metadata(catalog, "E-400")
        assert meta is not None
        assert meta["categoria"] == "entregable"

    def test_unknown_codigo_returns_none(self):
        catalog = load_catalog()
        assert get_template_metadata(catalog, "FAKE-999") is None

    def test_list_by_categoria_politica(self):
        catalog = load_catalog()
        pols = list_templates_by_categoria(catalog, "politica")
        assert len(pols) >= 20
        for p in pols:
            assert p["categoria"] == "politica"

    def test_list_by_familia_org(self):
        catalog = load_catalog()
        orgs = list_templates_by_familia(catalog, "org")
        assert len(orgs) >= 1
        for o in orgs:
            assert o.get("familia_ens") == "org"

    def test_root_not_dict_raises(self, tmp_path):
        f = tmp_path / "list.yaml"
        f.write_text("- item1\n- item2\n")
        with pytest.raises(CatalogLoadError, match="root is not a dict"):
            load_catalog(catalog_path=f)

    def test_templates_not_list_raises(self, tmp_path):
        f = tmp_path / "str.yaml"
        f.write_text(yaml.dump({"templates": "not_a_list"}))
        with pytest.raises(CatalogLoadError, match="not a list"):
            load_catalog(catalog_path=f)

    def test_missing_required_field_raises(self, tmp_path):
        f = tmp_path / "bad.yaml"
        f.write_text(yaml.dump({"version": "1.0", "templates": [{"codigo": "X"}]}))
        with pytest.raises(CatalogLoadError, match="missing field"):
            load_catalog(catalog_path=f)

    def test_invalid_categoria_raises(self, tmp_path):
        f = tmp_path / "bad_cat.yaml"
        content = {"version": "1.0", "templates": [{
            "codigo": "X-001", "nombre": "T", "categoria": "INVENTADA",
            "aplica_desde": "basica", "version_actual": "1.0", "is_active": True,
        }]}
        f.write_text(yaml.dump(content))
        with pytest.raises(CatalogLoadError, match="invalid categoria"):
            load_catalog(catalog_path=f)

    def test_invalid_aplica_desde_raises(self, tmp_path):
        f = tmp_path / "bad_aplica.yaml"
        content = {"version": "1.0", "templates": [{
            "codigo": "X-001", "nombre": "T", "categoria": "politica",
            "aplica_desde": "INVENTADA", "version_actual": "1.0", "is_active": True,
        }]}
        f.write_text(yaml.dump(content))
        with pytest.raises(CatalogLoadError, match="invalid aplica_desde"):
            load_catalog(catalog_path=f)

    def test_placeholders_requeridos_exists(self):
        catalog = load_catalog()
        meta = get_template_metadata(catalog, "E-100")
        assert meta is not None
        ph = meta.get("placeholders_requeridos")
        assert ph is not None
        assert len(ph) > 0

    def test_normalized_placeholders_exist_after_load(self):
        """load_catalog normalizes placeholders into 'placeholders' key."""
        catalog = load_catalog()
        meta = get_template_metadata(catalog, "E-100")
        assert meta is not None
        ph = meta.get("placeholders")
        assert ph is not None
        assert len(ph) > 0
        # Each value should be a dict with description and required
        first_key = list(ph.keys())[0]
        assert "description" in ph[first_key]
        assert "required" in ph[first_key]


# ================================================================
# _normalize_placeholders
# ================================================================


class TestNormalizePlaceholders:

    def test_none_returns_empty_dict(self):
        assert _normalize_placeholders(None) == {}

    def test_legacy_string_format(self):
        raw = {"cliente.nif": "NIF de la entidad"}
        result = _normalize_placeholders(raw)
        assert result == {
            "cliente.nif": {"description": "NIF de la entidad", "required": False},
        }

    def test_new_dict_format(self):
        raw = {
            "cliente.nif": {"description": "NIF de la entidad", "required": True},
        }
        result = _normalize_placeholders(raw)
        assert result["cliente.nif"]["required"] is True
        assert result["cliente.nif"]["description"] == "NIF de la entidad"

    def test_new_dict_format_default_required_false(self):
        raw = {
            "cliente.nif": {"description": "NIF de la entidad"},
        }
        result = _normalize_placeholders(raw)
        assert result["cliente.nif"]["required"] is False

    def test_mixed_legacy_and_new_format(self):
        raw = {
            "a": "desc A",
            "b": {"description": "desc B", "required": True},
        }
        result = _normalize_placeholders(raw)
        assert result["a"]["required"] is False
        assert result["b"]["required"] is True

    def test_non_dict_raises(self):
        with pytest.raises(CatalogLoadError, match="must be a dict"):
            _normalize_placeholders("not a dict")

    def test_invalid_value_type_raises(self):
        with pytest.raises(CatalogLoadError, match="invalid value type"):
            _normalize_placeholders({"key": 42})

    def test_missing_description_in_dict_value_raises(self):
        with pytest.raises(CatalogLoadError, match="missing 'description'"):
            _normalize_placeholders({"key": {"required": True}})


# ================================================================
# get_required_vars
# ================================================================


class TestGetRequiredVars:

    def test_extracts_required_only(self):
        phs = {
            "a": {"description": "A", "required": True},
            "b": {"description": "B", "required": False},
            "c": {"description": "C", "required": True},
        }
        result = get_required_vars(phs)
        assert result == ["a", "c"]

    def test_none_required_returns_empty(self):
        phs = {
            "a": {"description": "A", "required": False},
            "b": {"description": "B"},
        }
        result = get_required_vars(phs)
        assert result == []


# ════════════════════════════════════════════════════════════════════
# TODO-M6-G1 + TODO-M6-G2: distincion required vs optional +
# formato normalizado dict en el catalogo productivo (83 templates).
# ════════════════════════════════════════════════════════════════════


class TestCatalogG1G2Hardening:
    """Valida que el catalogo productivo cumple con los invariantes
    declarados en Paso 4.5 para M6-G1 y M6-G2."""

    def test_no_legacy_list_format_in_catalog(self):
        """Ningun template usa la vieja representacion list[str]."""
        import yaml
        from backend.app.motors.m06_document_factory.catalog_loader import (
            CATALOG_PATH,
        )
        data = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))
        offenders = [
            t["codigo"] for t in data["templates"]
            if isinstance(t.get("placeholders_requeridos"), list)
        ]
        assert offenders == [], (
            f"Legacy list format detected in: {offenders}"
        )

    def test_every_placeholder_has_required_flag(self):
        """Cada placeholder es dict con 'description' y 'required'."""
        import yaml
        from backend.app.motors.m06_document_factory.catalog_loader import (
            CATALOG_PATH,
        )
        data = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))
        missing = []
        for t in data["templates"]:
            phs = t.get("placeholders_requeridos")
            if phs is None:
                continue
            for k, v in phs.items():
                if not isinstance(v, dict):
                    missing.append(f"{t['codigo']}:{k}:not_dict")
                elif "required" not in v:
                    missing.append(f"{t['codigo']}:{k}:no_required")
                elif "description" not in v:
                    missing.append(f"{t['codigo']}:{k}:no_description")
        assert missing == [], f"Placeholders mal formados: {missing[:10]}"

    def test_legal_critical_placeholders_marked_required(self):
        """Placeholders de identidad legal deben estar required=true
        en templates comerciales y entregables legales."""
        import yaml
        from backend.app.motors.m06_document_factory.catalog_loader import (
            CATALOG_PATH,
        )
        LEGAL_CRITICAL_KEYS = (
            "cliente.razon_social",
            "cliente.nif",
        )
        data = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))
        violations = []
        for t in data["templates"]:
            cat = t.get("categoria")
            if cat not in ("comercial", "entregable", "politica"):
                continue
            phs = t.get("placeholders_requeridos") or {}
            for key in LEGAL_CRITICAL_KEYS:
                spec = phs.get(key)
                if spec is None:
                    continue
                if isinstance(spec, dict) and not spec.get("required", False):
                    violations.append(f"{t['codigo']}:{key}")
        assert violations == [], (
            f"Placeholders legales SIN required=true: {violations[:10]}"
        )


class TestAplicaMicroL6:
    """L-6 · filtro de proporcionalidad micro/autonomo (aplica_micro)."""

    def test_list_applicable_micro_excludes_team_scale(self):
        from backend.app.motors.m06_document_factory.catalog_loader import (
            list_applicable_for_size,
        )
        cat = load_catalog()
        total = len(cat["templates"])
        micro = list_applicable_for_size(cat, "micro")
        codes_micro = {t["codigo"] for t in micro}
        # E-PF-001 (plan de formacion escala-equipo) se omite para micro
        assert "E-PF-001" not in codes_micro
        assert len(micro) == total - 1

    def test_list_applicable_non_micro_returns_all(self):
        from backend.app.motors.m06_document_factory.catalog_loader import (
            list_applicable_for_size,
        )
        cat = load_catalog()
        total = len(cat["templates"])
        for size in ("pequeno", "mediano", "grande", None):
            assert len(list_applicable_for_size(cat, size)) == total

    def test_aplica_micro_must_be_bool(self):
        from backend.app.motors.m06_document_factory.catalog_loader import (
            load_catalog as _lc,
        )
        # el catalogo real valida sin error (E-PF-001 usa bool false)
        _lc()
