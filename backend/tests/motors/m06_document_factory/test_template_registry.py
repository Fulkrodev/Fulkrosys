"""Tests for the M06 template_registry — the 54 extracted Jinja2 templates."""
import pytest

from backend.app.motors.m06_document_factory.template_registry import (
    TEMPLATE_REGISTRY,
    get_template,
    list_templates,
    load_template_module,
)


# Codes whose body Marcos has redacted in fulkro_dev/. Anything not listed
# here is expected to live only in the YAML metadata catalog as a stub.
PRESENT_PROCEDURES = [
    "E-200", "E-201", "E-202", "E-203", "E-204", "E-204-A", "E-205",
    "E-206", "E-207", "E-209", "E-210", "E-211", "E-212", "E-213",
    "E-217", "E-218", "E-219", "E-220", "E-221", "E-231",
]


CLUSTER_A_1DFTRIS_IDS = [
    # Sub-atom 1.D.F.tris Cluster A · governance SGSI + ruta basica + retainer
    "E-002", "E-003", "E-012", "E-041", "E-042", "E-043", "E-090", "E-614", "E-615",
]

CLUSTER_B_1DFTRIS_IDS = [
    # Sub-atom 1.D.F.tris.B-bis Cluster B · SGSI core ruta normal
    "E-150", "E-160", "E-170", "E-180",
]

CLUSTER_D_1DFTRIS_IDS = [
    # Sub-atom 1.D.F.tris Cluster D · continuity + LMS + audits + verification
    "E-401", "E-402", "E-403", "E-404", "E-405", "E-406",
    "E-500", "E-501", "E-502", "E-503", "E-504",
    "E-700", "E-701",
    "E-705", "E-706", "E-707", "E-708", "E-709",
]

CLUSTER_E_1DI_IDS = [
    # Sub-atom 1.D.I · proveedores supply chain ENS op.ext.* (reactivated pre-1.E
    # scope reorder · FULKRO empresa privada licitando publico · sub-lote 1.B.7.1.1
    # architect-VERBATIM curated reactivated REGISTRY-ONLY pure)
    "E-600", "E-601", "E-602", "E-603", "E-604",
]


class TestTemplateRegistry:
    def test_registry_has_at_least_109_templates(self):
        """Floor ratchet · sub-atom 1.D.I cierre Cluster A+B+D+E wire-up.

        Cluster A 9 + Cluster B 4 SGSI core + Cluster D 18 + Cluster E 5 proveedores
        = 36 nuevas entries sobre base 73 pre-1.D.F.tris · 109 final.
        """
        assert len(TEMPLATE_REGISTRY) >= 109

    def test_cluster_a_1dftris_governance_retainer_present(self):
        """Cluster A · 9 plantillas governance SGSI + ruta basica + retainer."""
        for code in CLUSTER_A_1DFTRIS_IDS:
            assert code in TEMPLATE_REGISTRY, f"Missing Cluster A 1.D.F.tris {code}"

    def test_cluster_b_1dftris_sgsi_core_present(self):
        """Cluster B · 4 plantillas SGSI core ruta normal (B-bis IMPLEMENT FULL)."""
        for code in CLUSTER_B_1DFTRIS_IDS:
            assert code in TEMPLATE_REGISTRY, f"Missing Cluster B 1.D.F.tris.B-bis {code}"

    def test_cluster_d_1dftris_continuity_lms_audits_present(self):
        """Cluster D · 18 plantillas continuidad BCP/DRP + LMS + auditorias + verificacion."""
        for code in CLUSTER_D_1DFTRIS_IDS:
            assert code in TEMPLATE_REGISTRY, f"Missing Cluster D 1.D.F.tris {code}"

    def test_cluster_e_1di_proveedores_supply_chain_present(self):
        """Cluster E · 5 plantillas proveedores supply chain ENS op.ext.* (1.D.I)."""
        for code in CLUSTER_E_1DI_IDS:
            assert code in TEMPLATE_REGISTRY, f"Missing Cluster E 1.D.I {code}"

    def test_all_27_policies_present(self):
        for code in range(100, 127):
            assert f"E-{code}" in TEMPLATE_REGISTRY, f"Missing policy E-{code}"

    def test_present_procedures(self):
        for code in PRESENT_PROCEDURES:
            assert code in TEMPLATE_REGISTRY, f"Missing procedure {code}"

    def test_commercial_templates_present(self):
        for code in ("P-001", "C-001", "C-003"):
            assert code in TEMPLATE_REGISTRY, f"Missing commercial {code}"

    def test_core_deliverables_present(self):
        for code in ("E-001", "E-040", "E-050", "E-400"):
            assert code in TEMPLATE_REGISTRY, f"Missing deliverable {code}"

    def test_get_template_known(self):
        meta = get_template("E-100")
        assert meta is not None
        assert meta["type"] == "policies"

    def test_get_template_unknown(self):
        assert get_template("E-999") is None

    def test_list_templates_filter_by_type(self):
        policies = list_templates(template_type="policies")
        assert len(policies) >= 27
        for p in policies:
            assert p["type"] == "policies"


class TestTemplateBodies:
    @pytest.mark.parametrize("template_id", list(TEMPLATE_REGISTRY.keys()))
    def test_each_template_has_body(self, template_id):
        mod = load_template_module(template_id)
        assert mod is not None
        assert hasattr(mod, "TEMPLATE_BODY")
        assert len(mod.TEMPLATE_BODY) >= 500, (
            f"{template_id} body too short: {len(mod.TEMPLATE_BODY)} chars"
        )

    @pytest.mark.parametrize("template_id", list(TEMPLATE_REGISTRY.keys()))
    def test_each_template_has_jinja2_placeholders(self, template_id):
        mod = load_template_module(template_id)
        assert "{{" in mod.TEMPLATE_BODY, (
            f"{template_id} has no Jinja2 placeholders"
        )

    @pytest.mark.parametrize("template_id", [
        tid for tid, meta in TEMPLATE_REGISTRY.items()
        if meta["type"] in ("policies", "procedures")
    ])
    def test_policy_or_procedure_references_ens(self, template_id):
        """SGSI templates must cite the regulatory backbone — ENS, MAGERIT, RGPD,
        LOPDGDD, the Anexo II measure codes, or the parent policy that does."""
        mod = load_template_module(template_id)
        body = mod.TEMPLATE_BODY
        markers = (
            "op.", "org.", "mp.",            # Anexo II measure codes
            "311/2022", "ENS",               # ENS itself
            "Anexo", "RGPD", "LOPDGDD",      # cross-regulation
            "CCN", "Politica", "Política",   # CCN-STIC and parent policy refs
            "politica_madre", "politica",    # YAML front-matter parent ref
        )
        has_ens = any(m in body for m in markers)
        assert has_ens, f"{template_id} has no regulatory references"

    def test_each_template_metadata_consistent(self):
        for tid, meta in TEMPLATE_REGISTRY.items():
            mod = load_template_module(tid)
            assert mod.TEMPLATE_ID == tid, (
                f"{tid} module reports id {mod.TEMPLATE_ID}"
            )
            assert mod.TEMPLATE_TYPE == meta["type"]


def test_e155_documento_alcance_present_and_flagged():
    """F-14-05 (Ejecutable 8 Pasada 16): E-155 Documento de Alcance del SGSI
    registrado (type deliverables), loadable, con estructura CCN-STIC 805/809 y
    el wording normativo genérico MARCADO para revisión consultor (requisito
    Marcos: no presentar contenido normativo inventado como definitivo)."""
    assert "E-155" in TEMPLATE_REGISTRY
    meta = TEMPLATE_REGISTRY["E-155"]
    assert meta["type"] == "deliverables", "E-155 NO debe ser policies (contadores tier)"
    mod = load_template_module("E-155")
    assert mod.TEMPLATE_ID == "E-155"
    body = mod.TEMPLATE_BODY
    up = body.upper()
    # Estructura CCN-STIC 805/809
    assert "ALCANCE DEL" in up
    assert "EXCLUSIONES" in up
    assert "CCN-STIC 805" in body and "CCN-STIC 809" in body
    # Requisito Marcos: secciones normativas genéricas marcadas para su revisión
    assert "REVISIÓN CONSULTOR" in body
    assert "PENDIENTE REVISIÓN CONSULTOR" in body  # banner estado_revision
