"""
Tests for Motor 1 — Categorization Engine.

8 mandatory test cases per v2.1 requirements.
"""
import pytest
from backend.app.motors.m01_categorization.service import (
    Category,
    ImpactLevel,
    compute_category,
    elevate_to_floor,
)


class TestComputeCategory:
    """Tests for the deterministic categorization function."""

    def test_all_bajo_returns_basica(self):
        """Sistema con todas las dimensiones BAJO -> categoría BÁSICA."""
        result = compute_category({
            "D": "BAJO", "I": "BAJO", "C": "BAJO", "A": "BAJO", "T": "BAJO"
        })
        assert result.category == Category.BASICA
        assert "BASICA" in result.justification
        assert "regla del máximo" in result.justification

    def test_all_medio_returns_media(self):
        """Sistema con todas las dimensiones MEDIO -> categoría MEDIA."""
        result = compute_category({
            "D": "MEDIO", "I": "MEDIO", "C": "MEDIO", "A": "MEDIO", "T": "MEDIO"
        })
        assert result.category == Category.MEDIA

    def test_all_alto_returns_alta(self):
        """Sistema con todas las dimensiones ALTO -> categoría ALTA."""
        result = compute_category({
            "D": "ALTO", "I": "ALTO", "C": "ALTO", "A": "ALTO", "T": "ALTO"
        })
        assert result.category == Category.ALTA

    def test_one_medio_rest_bajo_returns_media(self):
        """4 dimensiones BAJO y 1 MEDIO -> categoría MEDIA (regla del máximo)."""
        result = compute_category({
            "D": "BAJO", "I": "BAJO", "C": "MEDIO", "A": "BAJO", "T": "BAJO"
        })
        assert result.category == Category.MEDIA
        assert result.determining_dimension == "C"
        assert "Confidencialidad" in result.justification

    def test_one_alto_rest_medio_returns_alta(self):
        """4 dimensiones MEDIO y 1 ALTO -> categoría ALTA."""
        result = compute_category({
            "D": "MEDIO", "I": "MEDIO", "C": "MEDIO", "A": "ALTO", "T": "MEDIO"
        })
        assert result.category == Category.ALTA
        assert result.determining_dimension == "A"

    def test_mixed_1_alto_2_medio_2_bajo_returns_alta(self):
        """1 ALTO, 2 MEDIO, 2 BAJO -> categoría ALTA."""
        result = compute_category({
            "D": "ALTO", "I": "MEDIO", "C": "MEDIO", "A": "BAJO", "T": "BAJO"
        })
        assert result.category == Category.ALTA
        assert result.determining_dimension == "D"
        assert "Disponibilidad" in result.justification

    def test_invalid_level_raises_valueerror(self):
        """Dimensión con valor inválido -> error ValueError."""
        with pytest.raises(ValueError, match="Nivel de impacto inválido"):
            compute_category({
                "D": "BAJO", "I": "INVALIDO", "C": "BAJO", "A": "BAJO", "T": "BAJO"
            })

    def test_missing_dimensions_raises_valueerror(self):
        """Faltan dimensiones -> error ValueError."""
        with pytest.raises(ValueError, match="faltan dimensiones"):
            compute_category({
                "D": "BAJO", "I": "BAJO", "C": "BAJO"
            })


class TestCategorizationResultFields:
    """Additional tests for result structure."""

    def test_result_contains_all_dimensions(self):
        """Result includes all 5 dimension assessments."""
        result = compute_category({
            "D": "MEDIO", "I": "BAJO", "C": "ALTO", "A": "BAJO", "T": "MEDIO"
        })
        assert len(result.dimension_assessments) == 5
        assert result.dimension_assessments["C"] == ImpactLevel.ALTO
        assert result.dimension_assessments["D"] == ImpactLevel.MEDIO

    def test_case_insensitive_input(self):
        """Input levels are case-insensitive."""
        result = compute_category({
            "D": "bajo", "I": "Medio", "C": "ALTO", "A": "bajo", "T": "medio"
        })
        assert result.category == Category.ALTA

    def test_acta_e012_generation(self):
        """The E-012 act is generated correctly."""
        from backend.app.motors.m01_categorization.service import CategorizationService
        result = compute_category({
            "D": "MEDIO", "I": "MEDIO", "C": "MEDIO", "A": "BAJO", "T": "BAJO"
        })
        # Use a mock-free approach: directly call the class method
        svc = CategorizationService.__new__(CategorizationService)
        acta = svc.generate_acta_e012(result, "Proyecto Test", "Sistema Test")
        assert "E-012" in acta
        assert "MEDIA" in acta
        assert "Real Decreto 311/2022" in acta
        assert "Proyecto Test" in acta

    def test_compute_category_raises_on_unknown_dimensions(self):
        """compute_category() rechaza dimensiones desconocidas con ValueError.

        El RD 311/2022 Anexo I define exactamente 5 dimensiones: D, I, C, A, T.
        Cualquier dimension adicional debe ser rechazada explicitamente para
        evitar que datos malformados pasen silenciosamente al calculo.

        Cita: RD 311/2022 Anexo I (Disponibilidad, Integridad, Confidencialidad,
        Autenticidad, Trazabilidad).
        """
        with pytest.raises(ValueError, match="dimensiones desconocidas"):
            compute_category({
                "D": "BAJO",
                "I": "BAJO",
                "C": "BAJO",
                "A": "BAJO",
                "T": "BAJO",
                "X": "ALTO",  # dimension invalida
            })


class TestInheritedFloorAapp:
    """#5 (Sub-bloque E) · suelo de categoría heredado de la AAPP.

    Piso DURO: la categoría solo puede SUBIR por encima del suelo, nunca
    declararse por debajo (Anexo I = máximo; la herencia es restricción
    adicional por encima). La justificación cita la herencia SOLO cuando eleva.
    """

    _ALL_BAJO = {"D": "BAJO", "I": "BAJO", "C": "BAJO", "A": "BAJO", "T": "BAJO"}
    _ALL_MEDIO = {"D": "MEDIO", "I": "MEDIO", "C": "MEDIO", "A": "MEDIO", "T": "MEDIO"}
    _ALL_ALTO = {"D": "ALTO", "I": "ALTO", "C": "ALTO", "A": "ALTO", "T": "ALTO"}

    def test_basica_floor_media_eleva_a_media(self):
        """Básica computed + suelo MEDIA -> MEDIA (el piso ELEVA)."""
        result = compute_category(self._ALL_BAJO, inherited_floor="MEDIA")
        assert result.category == Category.MEDIA
        assert "herencia de la AAPP" in result.justification
        assert "ELEVA" in result.justification

    def test_alta_floor_media_no_baja_se_queda_alta(self):
        """ALTA computed + suelo MEDIA -> ALTA (el máximo manda · el piso NO baja)."""
        result = compute_category(self._ALL_ALTO, inherited_floor="MEDIA")
        assert result.category == Category.ALTA
        # No hubo elevación por herencia -> NO se cita la herencia.
        assert "herencia de la AAPP" not in result.justification

    def test_media_floor_media_se_queda_media_sin_citar(self):
        """MEDIA computed + suelo MEDIA -> MEDIA (sin elevación, sin cita)."""
        result = compute_category(self._ALL_MEDIO, inherited_floor="MEDIA")
        assert result.category == Category.MEDIA
        assert "herencia de la AAPP" not in result.justification

    def test_basica_floor_alta_eleva_a_alta(self):
        """Básica computed + suelo ALTA -> ALTA (eleva dos niveles)."""
        result = compute_category(self._ALL_BAJO, inherited_floor="ALTA")
        assert result.category == Category.ALTA
        assert "herencia de la AAPP" in result.justification

    def test_floor_none_backward_compat(self):
        """Suelo None -> idéntico a hoy (BÁSICA), sin cita de herencia."""
        result = compute_category(self._ALL_BAJO, inherited_floor=None)
        assert result.category == Category.BASICA
        assert "herencia de la AAPP" not in result.justification
        assert "regla del máximo" in result.justification

    def test_floor_basica_es_noop(self):
        """Suelo BASICA (rank 1) nunca eleva -> no-op."""
        result = compute_category(self._ALL_BAJO, inherited_floor="BASICA")
        assert result.category == Category.BASICA
        assert "herencia de la AAPP" not in result.justification

    def test_floor_invalido_degrada_a_noop(self):
        """Suelo inválido/legacy ('M') degrada a None -> no eleva ni rompe."""
        result = compute_category(self._ALL_BAJO, inherited_floor="M")
        assert result.category == Category.BASICA

    def test_justificacion_eleva_contrasta_dicat_vs_final(self):
        """La justificación al elevar contrasta categoría DICAT con la final."""
        result = compute_category(self._ALL_BAJO, inherited_floor="MEDIA")
        assert "BASICA" in result.justification  # lo que daría la regla del máximo
        assert "MEDIA" in result.justification    # categoría final elevada
        assert "Administración" in result.justification


class TestElevateToFloorHelper:
    """elevate_to_floor: max(current, floor) por rank · solo ELEVA, nunca baja."""

    def test_eleva_cuando_floor_mayor(self):
        assert elevate_to_floor("BASICA", "MEDIA") == "MEDIA"
        assert elevate_to_floor("BASICA", "ALTA") == "ALTA"
        assert elevate_to_floor("MEDIA", "ALTA") == "ALTA"

    def test_no_baja_cuando_floor_menor_o_igual(self):
        assert elevate_to_floor("ALTA", "MEDIA") == "ALTA"
        assert elevate_to_floor("MEDIA", "MEDIA") == "MEDIA"
        assert elevate_to_floor("ALTA", "BASICA") == "ALTA"

    def test_floor_none_devuelve_current(self):
        assert elevate_to_floor("BASICA", None) == "BASICA"
        assert elevate_to_floor(None, None) is None

    def test_current_none_devuelve_floor(self):
        assert elevate_to_floor(None, "MEDIA") == "MEDIA"

    def test_current_legacy_desconocido_devuelve_floor(self):
        # 'M' no es categoría canónica -> el suelo manda (mínimo garantizado).
        assert elevate_to_floor("M", "ALTA") == "ALTA"
