"""Tests for Agent 14 filter detection — sync, no DB required."""
from backend.app.agents.agent_14_copiloto.filters import detect_filters


class TestMeasureCodeDetection:
    """Detect ENS measure codes in user questions."""

    def test_detects_op_acc_code(self):
        f = detect_filters("¿Qué exige op.acc.6 del ENS?")
        assert f.only_with_measure_code is True
        assert "op.acc.6" in f.measure_codes_mentioned

    def test_detects_mp_if_code(self):
        f = detect_filters("Explica mp.if.3 sobre proteccion de informacion")
        assert f.only_with_measure_code is True
        assert "mp.if.3" in f.measure_codes_mentioned

    def test_detects_org_code(self):
        f = detect_filters("¿Qué dice org.1 sobre la politica de seguridad?")
        assert f.only_with_measure_code is True
        assert "org.1" in f.measure_codes_mentioned

    def test_medida_keyword_triggers_filter(self):
        f = detect_filters("¿Cuáles son las medidas del marco organizativo?")
        assert f.only_with_measure_code is True


class TestSourceCodeDetection:
    """Detect source document references."""

    def test_detects_rd_311_2022(self):
        f = detect_filters("¿Qué dice el RD 311/2022 sobre criptografia?")
        assert "RD_311_2022" in f.source_codes

    def test_detects_ccn_stic_guide(self):
        f = detect_filters("Segun la CCN-STIC 804, ¿qué categorias existen?")
        assert "CCN_STIC_804" in f.source_codes

    def test_detects_nist(self):
        f = detect_filters("¿Cómo se compara el ENS con NIST?")
        assert "NIST" in f.source_codes

    def test_no_filters_on_generic_question(self):
        f = detect_filters("¿Qué es la seguridad informática?")
        assert f.only_with_measure_code is False
        assert f.source_codes == []
        assert f.measure_codes_mentioned == []
