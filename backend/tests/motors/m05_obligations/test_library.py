"""Tests for Motor 5 obligations library loader.

Verifies JSON loading, Pydantic validation, template counts,
dependency resolution, and query helpers.
"""
from collections import Counter

import pytest

from backend.app.motors.m05_obligations.library_loader import (
    load_library,
    reload_library,
    get_all_templates,
    get_template_by_id,
    get_templates_for_measure,
    get_templates_count_by_measure,
    resolve_dependencies,
    LibraryLoadError,
    TemplateNotFoundError,
    LIBRARY_PATH,
)
from backend.app.motors.m05_obligations.types import (
    ObligationsLibrary,
    CATEGORIES_VALID,
    EXECUTION_MODES_VALID,
    ENTREGABLE_TIPOS_VALID,
    MAGIC_LINK_TEMPLATES_VALID,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear lru_cache before each test for isolation."""
    load_library.cache_clear()
    yield
    load_library.cache_clear()


# ── Loading & validation ────────────────────────────────────────────


class TestLibraryLoading:

    def test_library_loads_successfully(self):
        lib = load_library()
        assert isinstance(lib, ObligationsLibrary)
        assert lib.version == "3.0"

    def test_library_has_30_templates(self):
        lib = load_library()
        assert len(lib.templates) >= 150

    def test_no_duplicate_ids(self):
        lib = load_library()
        ids = [t.id for t in lib.templates]
        assert len(ids) == len(set(ids)), f"Duplicate IDs found: {[x for x, c in Counter(ids).items() if c > 1]}"

    def test_library_file_exists(self):
        assert LIBRARY_PATH.exists(), f"Library file not at {LIBRARY_PATH}"

    def test_missing_file_raises_error(self, tmp_path):
        fake = tmp_path / "nonexistent.json"
        with pytest.raises(LibraryLoadError, match="not found"):
            load_library(path=fake)

    def test_invalid_json_raises_error(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{invalid json")
        with pytest.raises(LibraryLoadError, match="Cannot parse"):
            load_library(path=bad)

    def test_reload_library_clears_cache(self):
        lib1 = load_library()
        lib2 = reload_library()
        assert lib1.version == lib2.version
        assert len(lib1.templates) == len(lib2.templates)


# ── Domain validation ───────────────────────────────────────────────


class TestDomainValidation:

    def test_all_modes_valid(self):
        lib = load_library()
        for t in lib.templates:
            assert t.modo_ejecucion in EXECUTION_MODES_VALID, (
                f"{t.id}: invalid modo_ejecucion '{t.modo_ejecucion}'"
            )

    def test_all_entregable_tipos_valid(self):
        lib = load_library()
        for t in lib.templates:
            assert t.entregable_tipo in ENTREGABLE_TIPOS_VALID, (
                f"{t.id}: invalid entregable_tipo '{t.entregable_tipo}'"
            )

    def test_all_categories_valid(self):
        lib = load_library()
        for t in lib.templates:
            assert t.categoria in CATEGORIES_VALID, (
                f"{t.id}: invalid categoria '{t.categoria}'"
            )

    def test_all_magic_links_valid(self):
        lib = load_library()
        for t in lib.templates:
            assert t.magic_link_template in MAGIC_LINK_TEMPLATES_VALID, (
                f"{t.id}: invalid magic_link_template '{t.magic_link_template}'"
            )

    def test_effort_hours_realistic(self):
        """All effort values between 1 and 200 hours."""
        lib = load_library()
        for t in lib.templates:
            assert 1 <= t.esfuerzo_horas <= 200, (
                f"{t.id}: unrealistic esfuerzo_horas={t.esfuerzo_horas}"
            )

    def test_all_have_acceptance_criteria(self):
        lib = load_library()
        for t in lib.templates:
            assert len(t.criterios_aceptacion) >= 1, (
                f"{t.id}: missing criterios_aceptacion"
            )

    def test_all_have_normative_sources(self):
        lib = load_library()
        for t in lib.templates:
            assert len(t.fuente_normativa) >= 1, (
                f"{t.id}: missing fuente_normativa"
            )


# ── Deliverable E-code hygiene (WAVE C1 · §4.4/364) ─────────────────


class TestDeliverableCodeHygiene:
    """E-050 es canónicamente el "Informe de Auditoría Interna del SGSI"
    (F3.2 spec · E-050.docx · m09 internal_auditor). NINGUNA obligación de la
    librería debe (re)usar E-050 para otro entregable distinto."""

    def test_no_obligation_misuses_e050(self):
        lib = load_library()
        offenders = [
            t.id for t in lib.templates
            if "E-050" in (t.entregable_esperado or "")
        ]
        assert offenders == [], (
            "E-050 está reservado al Informe de Auditoría Interna del SGSI; "
            f"obligaciones que lo reutilizan mal: {offenders}"
        )

    def test_risk_analysis_and_inventory_recoded(self):
        """Las dos obligaciones que colisionaban en E-050 (§4.4/364) ya no lo
        referencian y describen su entregable real."""
        ar = get_template_by_id("OBL-op.pl.1-001")
        assert "E-050" not in ar.entregable_esperado
        assert "MAGERIT" in ar.entregable_esperado

        inv = get_template_by_id("OBL-op.exp.1-001")
        assert "E-050" not in inv.entregable_esperado
        assert "nventario" in inv.entregable_esperado


# ── Critical measures coverage ──────────────────────────────────────


class TestCriticalCoverage:

    def test_org1_has_templates(self):
        templates = get_templates_for_measure("org.1")
        assert len(templates) >= 3

    def test_op_acc_6_has_templates(self):
        templates = get_templates_for_measure("op.acc.6")
        assert len(templates) >= 4

    def test_op_exp_7_has_templates(self):
        templates = get_templates_for_measure("op.exp.7")
        assert len(templates) >= 2

    def test_op_cont_measures_covered(self):
        """Continuity measures op.cont.1/2/3 all have templates."""
        for code in ["op.cont.1", "op.cont.2", "op.cont.3"]:
            templates = get_templates_for_measure(code)
            assert len(templates) >= 1, f"No templates for {code}"


# ── Query helpers ───────────────────────────────────────────────────


class TestQueryHelpers:

    def test_get_all_templates_returns_list(self):
        templates = get_all_templates()
        assert isinstance(templates, list)
        assert len(templates) >= 150

    def test_get_template_by_id_found(self):
        tpl = get_template_by_id("OBL-org.1-001")
        assert tpl.id == "OBL-org.1-001"
        assert tpl.measure_code == "org.1"

    def test_get_template_by_id_not_found(self):
        with pytest.raises(TemplateNotFoundError):
            get_template_by_id("OBL-nonexistent-999")

    def test_get_templates_for_measure_returns_correct(self):
        templates = get_templates_for_measure("mp.com.2")
        ids = {t.id for t in templates}
        assert "OBL-mp.com.2-001" in ids
        assert "OBL-mp.com.2-002" in ids

    def test_get_templates_for_measure_with_category(self):
        templates = get_templates_for_measure("org.1", category="organizativo")
        assert len(templates) >= 3
        templates_bad = get_templates_for_measure("org.1", category="operacional")
        assert len(templates_bad) == 0

    def test_get_templates_count_by_measure(self):
        counts = get_templates_count_by_measure()
        assert isinstance(counts, dict)
        assert counts["org.1"] >= 3
        assert counts["op.acc.6"] >= 4
        assert sum(counts.values()) >= 250


# ── Dependency resolution ───────────────────────────────────────────


class TestDependencyResolution:

    def test_all_dependencies_resolvable(self):
        """Every template's dependencies point to existing templates."""
        lib = load_library()
        all_ids = {t.id for t in lib.templates}
        for t in lib.templates:
            for dep in t.dependencias_template_ids:
                assert dep in all_ids, (
                    f"{t.id} depends on missing template {dep}"
                )

    def test_no_circular_dependencies(self):
        """No template creates a circular dependency chain."""
        lib = load_library()
        for t in lib.templates:
            # Should not raise CircularDependencyError
            resolve_dependencies(t.id, library=lib)

    def test_resolve_dependencies_chain(self):
        """OBL-op.cont.3-001 depends on cont.2 which depends on cont.1."""
        deps = resolve_dependencies("OBL-op.cont.3-001")
        dep_ids = [d.id for d in deps]
        assert "OBL-op.cont.1-001" in dep_ids
        assert "OBL-op.cont.2-001" in dep_ids
        # cont.1 must come before cont.2 (topological order)
        assert dep_ids.index("OBL-op.cont.1-001") < dep_ids.index("OBL-op.cont.2-001")

    def test_resolve_dependencies_empty_for_root(self):
        """A template with no dependencies returns empty list."""
        deps = resolve_dependencies("OBL-org.1-001")
        assert deps == []

    def test_resolve_dependencies_single(self):
        """OBL-org.1-002 depends only on OBL-org.1-001."""
        deps = resolve_dependencies("OBL-org.1-002")
        assert len(deps) == 1
        assert deps[0].id == "OBL-org.1-001"
