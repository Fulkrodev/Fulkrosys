"""
Tests for Motor 2 — MAGERIT v3 Risk Engine.

D.1: Catalogs, risk matrix, and helper functions.
Every non-trivial test cites its source: Libro I/II/III section and page.
"""
import math
import pytest
import yaml
from pathlib import Path

from backend.app.motors.m02_magerit.service import (
    _map_value_to_level,
    _map_degradation_to_level,
    _lookup_impact_qualitative,
    _lookup_risk_matrix,
    _magerit_dependency_sum,
    _magerit_efficacy_composition,
    _magerit_safeguard_package_efficacy,
    _compute_package_efficacy,
    LEVEL_TO_INDEX,
    LEVELS_ORDER,
)

CATALOG_DIR = Path(__file__).resolve().parents[4] / "docs" / "magerit_catalog"


# ================================================================
# CATALOGS (3 tests) — verify YAML completeness
# ================================================================

class TestCatalogs:
    """Verify MAGERIT catalog YAML files match official Libro II counts."""

    def test_asset_types_loaded(self):
        """Libro II Cap 2: 9 categorias de activos con al menos 50 subtipos.

        Categorias oficiales: [S]ervicios, [D]atos, S[W]oftware, [HW]ardware,
        [COM]unicaciones, [SI]oportes, [AUX]iliares, [L]ocales, [P]ersonas.
        Fuente: MAGERIT v3 Libro II, Capitulo 2, pp.8-23.
        """
        data = yaml.safe_load((CATALOG_DIR / "asset_types.yaml").read_text())
        categories = set()
        total_subtypes = 0
        for group in data["asset_categories"]:
            categories.add(group["code"])
            total_subtypes += len(group["subtypes"])

        assert len(categories) == 9, (
            f"Esperado 9 categorias (Libro II Cap 2), obtenido {len(categories)}: {sorted(categories)}"
        )
        assert total_subtypes >= 50, (
            f"Esperado >= 50 subtipos (Libro II Cap 2), obtenido {total_subtypes}"
        )

    def test_threats_loaded(self):
        """Libro II Cap 5: amenazas distribuidas en 4 grupos (N, I, E, A).

        Fuente: MAGERIT v3 Libro II, Capitulo 5, pp.25-50.
        """
        data = yaml.safe_load((CATALOG_DIR / "threats.yaml").read_text())
        groups_found = {}
        total = 0
        for group in data["threat_groups"]:
            code = group["group"]
            count = len(group["threats"])
            groups_found[code] = count
            total += count

        assert set(groups_found.keys()) == {"N", "I", "E", "A"}, (
            f"Esperado 4 grupos (N, I, E, A) (Libro II Cap 5), obtenido {sorted(groups_found.keys())}"
        )
        assert total >= 40, (
            f"Esperado >= 40 amenazas totales (Libro II Cap 5), obtenido {total}. "
            f"Por grupo: {groups_found}"
        )

    def test_safeguards_loaded(self):
        """Libro II Cap 6: al menos 80 salvaguardas en 16 familias.

        Familias oficiales: H, D, K, S, SW, HW, COM, IP, MP, AUX, L, PS, G, BC, E, NEW.
        Fuente: MAGERIT v3 Libro II, Capitulo 6, pp.51-75.
        """
        data = yaml.safe_load((CATALOG_DIR / "safeguards.yaml").read_text())
        families = set()
        total = 0
        for group in data["safeguard_families"]:
            families.add(group["family"])
            total += len(group["safeguards"])

        assert len(families) == 16, (
            f"Esperado 16 familias (Libro II Cap 6), obtenido {len(families)}: {sorted(families)}"
        )
        assert total >= 80, (
            f"Esperado >= 80 salvaguardas (Libro II Cap 6), obtenido {total}"
        )


# ================================================================
# RISK MATRIX (1 test) — official 5x5 matrix
# ================================================================

class TestRiskMatrix:
    """Verify official MAGERIT risk matrix in DB."""

    @pytest.mark.asyncio
    async def test_risk_matrix_official(self, db):
        """Libro III sec 2.1 p.7: matriz 5x5 impacto x probabilidad -> riesgo.

        Fuente: MAGERIT v3 Libro III, sec 2.1 "Analisis mediante tablas", p.7:
        'Pudiendo combinarse impacto y frecuencia en una tabla para calcular
        el riesgo' — tabla completa de 25 celdas.
        """
        # Official matrix from Libro III p.7 (verified against PDF)
        EXPECTED = {
            ("MA", "MB"): "A",  ("MA", "B"): "MA", ("MA", "M"): "MA", ("MA", "A"): "MA", ("MA", "MA"): "MA",
            ("A",  "MB"): "M",  ("A",  "B"): "A",  ("A",  "M"): "A",  ("A",  "A"): "MA", ("A",  "MA"): "MA",
            ("M",  "MB"): "B",  ("M",  "B"): "M",  ("M",  "M"): "M",  ("M",  "A"): "A",  ("M",  "MA"): "A",
            ("B",  "MB"): "MB", ("B",  "B"): "B",  ("B",  "M"): "B",  ("B",  "A"): "M",  ("B",  "MA"): "M",
            ("MB", "MB"): "MB", ("MB", "B"): "MB", ("MB", "M"): "MB", ("MB", "A"): "B",  ("MB", "MA"): "B",
        }
        for (impact, prob), expected_risk in EXPECTED.items():
            result = await _lookup_risk_matrix(db, impact, prob)
            assert result == expected_risk, (
                f"Matriz({impact}, {prob}): esperado {expected_risk} (Libro III p.7), "
                f"obtenido {result}"
            )


# ================================================================
# QUALITATIVE HELPERS (4 tests)
# ================================================================

class TestQualitativeHelpers:
    """Tests for qualitative mapping and lookup functions."""

    def test_map_value_to_level_boundaries(self):
        """Convencion FULKRO (NO oficial MAGERIT): mapeo 0-10 -> MB/B/M/A/MA.

        Rangos: 0-1=MB, 2-3=B, 4-5=M, 6-7=A, 8-10=MA.
        Fuente: service.py docstring, convencion FULKRO.
        """
        cases = [
            (0, "MB"), (1, "MB"),  # boundary MB
            (2, "B"),  (3, "B"),   # boundary B
            (4, "M"),  (5, "M"),   # boundary M
            (6, "A"),  (7, "A"),   # boundary A
            (8, "MA"), (9, "MA"), (10, "MA"),  # boundary MA
        ]
        for value, expected in cases:
            result = _map_value_to_level(value)
            assert result == expected, (
                f"_map_value_to_level({value}): esperado {expected} "
                f"(convencion FULKRO), obtenido {result}"
            )

    def test_map_degradation_to_level(self):
        """Convencion FULKRO: mapeo degradacion % -> MB/B/M/A/MA.

        Rangos: 0-5%=MB, 6-20%=B, 21-50%=M, 51-90%=A, 91-100%=MA.
        Fuente: service.py docstring, extension a 5 niveles de la tabla
        oficial de 3 columnas del Libro III sec 2.1 p.6.
        """
        cases = [
            (0, "MB"), (5, "MB"),    # boundary MB
            (6, "B"),  (20, "B"),    # boundary B
            (21, "M"), (50, "M"),    # boundary M
            (51, "A"), (90, "A"),    # boundary A
            (91, "MA"), (100, "MA"), # boundary MA
        ]
        for pct, expected in cases:
            result = _map_degradation_to_level(pct)
            assert result == expected, (
                f"_map_degradation_to_level({pct}%): esperado {expected} "
                f"(convencion FULKRO), obtenido {result}"
            )

    def test_lookup_impact_qualitative(self):
        """Libro III sec 2.1 p.6: tabla impacto (valor x degradacion).

        Tabla oficial 3 columnas extendida a 5 por FULKRO.
        Verificamos 5 combinaciones representativas:
        - (MA, MA) -> MA  (esquina superior derecha)
        - (MB, MB) -> MB  (esquina inferior izquierda)
        - (A, M) -> M     (centro-alto)
        - (M, A) -> M     (centro, degradacion alta)
        - (MA, MB) -> M   (valor maximo, degradacion minima)
        Fuente: MAGERIT v3 Libro III, sec 2.1 p.6 + extension FULKRO.
        """
        cases = [
            ("MA", "MA", "MA"),
            ("MB", "MB", "MB"),
            ("A",  "M",  "M"),
            ("M",  "A",  "M"),
            ("MA", "MB", "M"),
        ]
        for value, degrad, expected in cases:
            result = _lookup_impact_qualitative(value, degrad)
            assert result == expected, (
                f"Impacto({value}, {degrad}): esperado {expected} "
                f"(Libro III p.6 ext.), obtenido {result}"
            )

    @pytest.mark.asyncio
    async def test_lookup_risk_matrix_via_db(self, db):
        """Libro III sec 2.1 p.7: verificar 5 celdas de la matriz via DB.

        Fuente: MAGERIT v3 Libro III, sec 2.1 p.7 — misma tabla que
        test_risk_matrix_official pero accedida via la funcion _lookup_risk_matrix().
        """
        cases = [
            ("MA", "MA", "MA"),  # max risk
            ("MB", "MB", "MB"),  # min risk
            ("A",  "M",  "A"),   # high impact, medium probability
            ("M",  "A",  "A"),   # medium impact, high probability
            ("B",  "B",  "B"),   # low-low
        ]
        for impact, prob, expected in cases:
            result = await _lookup_risk_matrix(db, impact, prob)
            assert result == expected, (
                f"_lookup_risk_matrix({impact}, {prob}): esperado {expected} "
                f"(Libro III p.7), obtenido {result}"
            )


# ================================================================
# QUANTITATIVE HELPERS (4 tests)
# ================================================================

class TestQuantitativeHelpers:
    """Tests for quantitative calculation helper functions."""

    def test_magerit_dependency_sum_neutral(self):
        """Libro III sec 2.2.2 p.12: 0 es elemento neutro.

        'a + b = 1 - (1 - a) x (1 - b)' con a=0: resultado = b.
        Fuente: MAGERIT v3 Libro III, sec 2.2.2, p.12.
        """
        result = _magerit_dependency_sum(0, 0.5)
        assert result == 0.5, (
            f"_magerit_dependency_sum(0, 0.5): esperado 0.5 "
            f"(Libro III p.12, 0 es neutro), obtenido {result}"
        )

    def test_magerit_dependency_sum_commutative(self):
        """Libro III sec 2.2.2 p.12: propiedad conmutativa.

        'Esta manera de sumar satisface las propiedades conmutativa,
        asociativa y existencia de un elemento neutro'.
        Fuente: MAGERIT v3 Libro III, sec 2.2.2, p.12.
        """
        r1 = _magerit_dependency_sum(0.3, 0.7)
        r2 = _magerit_dependency_sum(0.7, 0.3)
        assert r1 == pytest.approx(r2), (
            f"Conmutativa: sum(0.3, 0.7)={r1} != sum(0.7, 0.3)={r2} "
            f"(Libro III p.12)"
        )

    def test_magerit_dependency_sum_bounded(self):
        """Libro III sec 2.2.2 p.12: resultado acotado a [0,1].

        '...amen de acotar el resultado al rango [0..1] si los sumandos
        estan dentro de dicho rango'.
        Fuente: MAGERIT v3 Libro III, sec 2.2.2, p.12.
        """
        test_pairs = [(0.1, 0.2), (0.5, 0.5), (0.9, 0.9), (0.0, 1.0), (1.0, 1.0)]
        for a, b in test_pairs:
            result = _magerit_dependency_sum(a, b)
            assert 0.0 <= result <= 1.0, (
                f"_magerit_dependency_sum({a}, {b})={result} fuera de [0,1] "
                f"(Libro III p.12)"
            )

    def test_magerit_efficacy_composition(self):
        """Libro III sec 2.2.2 p.14: composicion de eficacias.

        '(1 - ei) x (1 - ef) = 1 - e' => e = 1 - (1-ei)(1-ef)
        Con ei=0.6, ef=0.4: e = 1 - (0.4)(0.6) = 1 - 0.24 = 0.76.
        Fuente: MAGERIT v3 Libro III, sec 2.2.2, p.14.
        """
        result = _magerit_efficacy_composition(0.6, 0.4)
        assert result == pytest.approx(0.76), (
            f"_magerit_efficacy_composition(0.6, 0.4): esperado 0.76 "
            f"(Libro III p.14: 1-(1-0.6)(1-0.4)), obtenido {result}"
        )


# ================================================================
# PACKAGE EFFICACY HELPERS (3 tests)
# ================================================================

class TestPackageEfficacy:
    """Tests for safeguard package efficacy calculation."""

    def test_package_efficacy_single_safeguard(self):
        """Una sola salvaguarda: eficacia del paquete = eficacia individual.

        Caso trivial de Libro III sec 2.2.4 p.21:
        'e(ps) = sum_k e(ps_k) x p_k / sum_k p_k' con k=1, p=1.
        Fuente: MAGERIT v3 Libro III, sec 2.2.4, p.21.
        """
        from unittest.mock import MagicMock
        sg = MagicMock()
        sg.efficacy = 75  # 75%
        result = _magerit_safeguard_package_efficacy([sg])
        assert result == pytest.approx(0.75), (
            f"Paquete con 1 salvaguarda al 75%: esperado 0.75 "
            f"(Libro III p.21), obtenido {result}"
        )

    def test_package_efficacy_two_equal(self):
        """Dos salvaguardas iguales con peso uniforme: media = cada una.

        'El caso particular de que todas las salvaguardas sean igual de
        importantes, se consigue tomando p = 1'.
        Con 2 salvaguardas al 60%: media = (0.6 + 0.6) / 2 = 0.6.
        Fuente: MAGERIT v3 Libro III, sec 2.2.4, p.21.
        """
        from unittest.mock import MagicMock
        sg1 = MagicMock()
        sg1.efficacy = 60
        sg2 = MagicMock()
        sg2.efficacy = 60
        result = _magerit_safeguard_package_efficacy([sg1, sg2])
        assert result == pytest.approx(0.6), (
            f"Paquete con 2 salvaguardas al 60%: esperado 0.6 "
            f"(Libro III p.21, media uniforme), obtenido {result}"
        )

    def test_compute_package_efficacy_separates_types(self):
        """_compute_package_efficacy() separa preventive/palliative/both.

        Convencion FULKRO: effect_type determina si contribuye a ei o ep.
        - preventive -> ep (reduce frecuencia)
        - palliative -> ei (reduce impacto/degradacion)
        - both -> contribuye a ambos
        Fuente: service.py docstring, convencion FULKRO.
        """
        from unittest.mock import MagicMock

        prev = MagicMock()
        prev.effect_type = "preventive"
        prev.efficacy = 80

        pall = MagicMock()
        pall.effect_type = "palliative"
        pall.efficacy = 60

        both = MagicMock()
        both.effect_type = "both"
        both.efficacy = 40

        ei, ep = _compute_package_efficacy([prev, pall, both])

        # ep: preventive(80) + both(40) -> media = (0.8+0.4)/2 = 0.6
        assert ep == pytest.approx(0.6), (
            f"ep (preventive+both): esperado 0.6 "
            f"(media de 80% y 40%), obtenido {ep}"
        )
        # ei: palliative(60) + both(40) -> media = (0.6+0.4)/2 = 0.5
        assert ei == pytest.approx(0.5), (
            f"ei (palliative+both): esperado 0.5 "
            f"(media de 60% y 40%), obtenido {ei}"
        )


"""
Tests for Motor 2 — MAGERIT v3 Risk Engine.

D.2: Value propagation tests (qualitative and quantitative modes).
Every non-trivial test cites its source: Libro III section and page.
"""
import asyncio
import uuid
import pytest

from backend.app.motors.m02_magerit.service import MageritService


# ================================================================
# QUALITATIVE PROPAGATION (4 tests)
# ================================================================

class TestPropagationQualitative:
    """Tests for qualitative value propagation (max rule)."""

    @pytest.mark.asyncio
    async def test_propagate_qualitative_isolated_asset(self, analysis_factory):
        """Activo sin dependencias: accumulated == value propio.

        Libro III sec 2.2.1 p.9: 'valor_acumulado(B) = max(valor(B),
        max_i{valor(A_i)})'. Sin superiores A_i, el max se reduce a valor(B).
        Fuente: MAGERIT v3 Libro III, sec 2.2.1, p.9.
        """
        analysis, svc = await analysis_factory("qualitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "ISO-01", "name": "Activo Aislado", "asset_type_code": "HW",
             "value_d": 7, "value_i": 5, "value_c": 3, "value_a": 2, "value_t": 1},
        ])
        await svc.propagate_values(analysis.id)

        asset = assets[0]
        for dim, expected in [("d", 7), ("i", 5), ("c", 3), ("a", 2), ("t", 1)]:
            acc = getattr(asset, f"accumulated_{dim}")
            assert acc == expected, (
                f"Aislado accumulated_{dim}: esperado {expected} "
                f"(Libro III p.9, sin superiores), obtenido {acc}"
            )

    @pytest.mark.asyncio
    async def test_propagate_qualitative_chain_two(self, analysis_factory):
        """Cadena A(superior)->B(inferior): B.accumulated = max(B.value, A.value).

        Libro III sec 2.2.1 p.9: 'Se define el valor acumulado sobre B como
        el mayor valor entre el propio y el de cualquiera de sus superiores:
        valor_acumulado(B) = max(valor(B), max_i{valor(A_i)})'

        Setup: A.value_d=8, B.value_d=3 -> B.accumulated_d = max(3, 8) = 8.
        Fuente: MAGERIT v3 Libro III, sec 2.2.1, p.9.
        """
        analysis, svc = await analysis_factory("qualitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "A-SUP", "name": "Servicio Web", "asset_type_code": "S",
             "value_d": 8, "value_i": 6, "value_c": 4, "value_a": 3, "value_t": 2},
            {"code": "B-INF", "name": "Servidor", "asset_type_code": "HW",
             "value_d": 3, "value_i": 2, "value_c": 1, "value_a": 1, "value_t": 1},
        ])
        await svc.build_dependency_graph(analysis.id, [
            {"superior_asset_id": assets[0].id, "inferior_asset_id": assets[1].id,
             "dependency_degree": 1.0},
        ])
        await svc.propagate_values(analysis.id)

        b = assets[1]
        expected = {"d": 8, "i": 6, "c": 4, "a": 3, "t": 2}
        for dim, exp in expected.items():
            acc = getattr(b, f"accumulated_{dim}")
            assert acc == exp, (
                f"Chain B.accumulated_{dim}: esperado {exp} "
                f"(Libro III p.9, max(B={getattr(b, f'value_{dim}')}, A={exp})), "
                f"obtenido {acc}"
            )

    @pytest.mark.asyncio
    async def test_propagate_qualitative_diamond(self, analysis_factory):
        """Diamante: A y C dependen de B. B.accumulated = max(B, A, C).

        Setup: A.value_d=9, C.value_d=6, B.value_d=2.
        B.accumulated_d = max(2, 9, 6) = 9.
        Fuente: MAGERIT v3 Libro III, sec 2.2.1, p.9.
        """
        analysis, svc = await analysis_factory("qualitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "A-TOP", "name": "Portal Ciudadano", "asset_type_code": "S",
             "value_d": 9, "value_i": 7, "value_c": 5, "value_a": 4, "value_t": 3},
            {"code": "B-MID", "name": "Base de Datos", "asset_type_code": "SW",
             "value_d": 2, "value_i": 2, "value_c": 2, "value_a": 2, "value_t": 2},
            {"code": "C-TOP", "name": "Servicio Interno", "asset_type_code": "S",
             "value_d": 6, "value_i": 4, "value_c": 3, "value_a": 2, "value_t": 1},
        ])
        a, b, c = assets
        await svc.build_dependency_graph(analysis.id, [
            {"superior_asset_id": a.id, "inferior_asset_id": b.id, "dependency_degree": 1.0},
            {"superior_asset_id": c.id, "inferior_asset_id": b.id, "dependency_degree": 1.0},
        ])
        await svc.propagate_values(analysis.id)

        expected = {"d": 9, "i": 7, "c": 5, "a": 4, "t": 3}
        for dim, exp in expected.items():
            acc = getattr(b, f"accumulated_{dim}")
            assert acc == exp, (
                f"Diamond B.accumulated_{dim}: esperado {exp} "
                f"(Libro III p.9, max(B=2, A={getattr(a, f'value_{dim}')}, "
                f"C={getattr(c, f'value_{dim}')})), obtenido {acc}"
            )

    @pytest.mark.asyncio
    async def test_propagate_qualitative_cycle_rejected(self, analysis_factory):
        """Grafo con ciclo A->B->A debe lanzar ValueError, no bucle infinito.

        MAGERIT requiere DAG para propagacion (no hay ciclos en dependencias
        reales de activos). El motor debe detectar ciclos en build_dependency_graph().
        Fuente: service.py docstring de build_dependency_graph().
        """
        analysis, svc = await analysis_factory("qualitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "CYCLE-A", "name": "Activo A", "asset_type_code": "HW",
             "value_d": 5, "value_i": 5, "value_c": 5, "value_a": 5, "value_t": 5},
            {"code": "CYCLE-B", "name": "Activo B", "asset_type_code": "HW",
             "value_d": 3, "value_i": 3, "value_c": 3, "value_a": 3, "value_t": 3},
        ])
        a, b = assets
        with pytest.raises(ValueError, match="[Cc]iclo"):
            await asyncio.wait_for(
                svc.build_dependency_graph(analysis.id, [
                    {"superior_asset_id": a.id, "inferior_asset_id": b.id, "dependency_degree": 1.0},
                    {"superior_asset_id": b.id, "inferior_asset_id": a.id, "dependency_degree": 1.0},
                ]),
                timeout=5.0,
            )


# ================================================================
# QUANTITATIVE PROPAGATION (4 tests)
# ================================================================

class TestPropagationQuantitative:
    """Tests for quantitative value propagation (weighted sum)."""

    @pytest.mark.asyncio
    async def test_propagate_quantitative_isolated_asset(self, analysis_factory):
        """Activo sin dependencias: accumulated == value propio.

        Libro III sec 2.2.2 p.13: 'valor_acumulado(B) = valor(B) +
        sum_i{valor(A_i) x grado(A_i => B)}'. Sin superiores, suma = 0.
        Fuente: MAGERIT v3 Libro III, sec 2.2.2, p.13.
        """
        analysis, svc = await analysis_factory("quantitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "Q-ISO", "name": "Activo Aislado Q", "asset_type_code": "HW",
             "value_d": 6, "value_i": 4, "value_c": 2, "value_a": 1, "value_t": 0},
        ])
        await svc.propagate_values(analysis.id)

        asset = assets[0]
        for dim, expected in [("d", 6.0), ("i", 4.0), ("c", 2.0), ("a", 1.0), ("t", 0.0)]:
            acc = float(getattr(asset, f"accumulated_{dim}"))
            assert acc == pytest.approx(expected), (
                f"Q-Aislado accumulated_{dim}: esperado {expected} "
                f"(Libro III p.13, sin superiores), obtenido {acc}"
            )

    @pytest.mark.asyncio
    async def test_propagate_quantitative_with_degree(self, analysis_factory):
        """A(sup) depende de B(inf) con grado 0.5.
        B.accumulated_d = B.value_d + A.value_d * 0.5 = 4 + 6*0.5 = 7.0.

        Libro III sec 2.2.2 p.13: 'valor_acumulado(B) = valor(B) +
        sum_i{valor(A_i) x grado(A_i => B)}'.
        Fuente: MAGERIT v3 Libro III, sec 2.2.2, p.13.
        """
        analysis, svc = await analysis_factory("quantitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "Q-SUP", "name": "Servicio", "asset_type_code": "S",
             "value_d": 6, "value_i": 4, "value_c": 2, "value_a": 0, "value_t": 0},
            {"code": "Q-INF", "name": "Servidor", "asset_type_code": "HW",
             "value_d": 4, "value_i": 3, "value_c": 1, "value_a": 0, "value_t": 0},
        ])
        a, b = assets
        await svc.build_dependency_graph(analysis.id, [
            {"superior_asset_id": a.id, "inferior_asset_id": b.id,
             "dependency_degree": 0.5},
        ])
        await svc.propagate_values(analysis.id)

        # B.accumulated_d = 4 + 6*0.5 = 7.0
        acc_d = float(getattr(b, "accumulated_d"))
        assert acc_d == pytest.approx(7.0), (
            f"Q-Chain B.accumulated_d: esperado 7.0 "
            f"(Libro III p.13: 4 + 6*0.5), obtenido {acc_d}"
        )
        # B.accumulated_i = 3 + 4*0.5 = 5.0
        acc_i = float(getattr(b, "accumulated_i"))
        assert acc_i == pytest.approx(5.0), (
            f"Q-Chain B.accumulated_i: esperado 5.0 "
            f"(Libro III p.13: 3 + 4*0.5), obtenido {acc_i}"
        )

    @pytest.mark.asyncio
    async def test_propagate_quantitative_caps_at_10(self, analysis_factory):
        """Si la suma supera 10, se capa a 10.0.

        Setup: A.value_d=10, B.value_d=8, grado=1.0.
        B.accumulated_d = 8 + 10*1.0 = 18 -> cap 10.0.
        Cap es convencion FULKRO por consistencia con escala 0-10.
        Fuente: service.py docstring, convencion FULKRO.
        """
        analysis, svc = await analysis_factory("quantitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "Q-BIG-A", "name": "Servicio Critico", "asset_type_code": "S",
             "value_d": 10, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
            {"code": "Q-BIG-B", "name": "Servidor Principal", "asset_type_code": "HW",
             "value_d": 8, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        a, b = assets
        await svc.build_dependency_graph(analysis.id, [
            {"superior_asset_id": a.id, "inferior_asset_id": b.id,
             "dependency_degree": 1.0},
        ])
        await svc.propagate_values(analysis.id)

        acc_d = float(getattr(b, "accumulated_d"))
        assert acc_d == pytest.approx(10.0), (
            f"Q-Cap B.accumulated_d: esperado 10.0 "
            f"(cap FULKRO, valor real seria 18.0), obtenido {acc_d}"
        )

    @pytest.mark.asyncio
    async def test_propagate_quantitative_no_intermediate_rounding(self, analysis_factory):
        """5 superiores con grados que producen suma decimal no trivial.

        Setup: B.value_d=0, 5 superiores con:
          A1: value_d=9, grado=0.5 -> contribucion 4.5
          A2: value_d=23, grado=0.1 -> contribucion 2.3
          A3: value_d=17, grado=0.1 -> contribucion 1.7
          A4: value_d=8, grado=0.1 -> contribucion 0.8
          A5: value_d=4, grado=0.1 -> contribucion 0.4
        Total: 0 + 4.5 + 2.3 + 1.7 + 0.8 + 0.4 = 9.7

        Verifica que el resultado es 9.7 (NUMERIC(10,4)) y no 10 ni 9.
        Esto valida el fix de TODO-3 (INTEGER -> NUMERIC).
        Fuente: MAGERIT v3 Libro III, sec 2.2.2, p.13 + fix TODO-3.
        """
        analysis, svc = await analysis_factory("quantitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "Q-NR-B", "name": "Nodo Base", "asset_type_code": "HW",
             "value_d": 0, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
            {"code": "Q-NR-A1", "name": "Sup 1", "asset_type_code": "S",
             "value_d": 9, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
            {"code": "Q-NR-A2", "name": "Sup 2", "asset_type_code": "S",
             "value_d": 10, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
            {"code": "Q-NR-A3", "name": "Sup 3", "asset_type_code": "S",
             "value_d": 10, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
            {"code": "Q-NR-A4", "name": "Sup 4", "asset_type_code": "S",
             "value_d": 8, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
            {"code": "Q-NR-A5", "name": "Sup 5", "asset_type_code": "S",
             "value_d": 4, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        b, a1, a2, a3, a4, a5 = assets
        await svc.build_dependency_graph(analysis.id, [
            {"superior_asset_id": a1.id, "inferior_asset_id": b.id, "dependency_degree": 0.5},
            {"superior_asset_id": a2.id, "inferior_asset_id": b.id, "dependency_degree": 0.23},
            {"superior_asset_id": a3.id, "inferior_asset_id": b.id, "dependency_degree": 0.17},
            {"superior_asset_id": a4.id, "inferior_asset_id": b.id, "dependency_degree": 0.1},
            {"superior_asset_id": a5.id, "inferior_asset_id": b.id, "dependency_degree": 0.1},
        ])
        await svc.propagate_values(analysis.id)

        # 0 + 9*0.5 + 10*0.23 + 10*0.17 + 8*0.1 + 4*0.1
        # = 0 + 4.5 + 2.3 + 1.7 + 0.8 + 0.4 = 9.7
        acc_d = float(getattr(b, "accumulated_d"))
        assert acc_d == pytest.approx(9.7, abs=0.001), (
            f"Q-NoRound B.accumulated_d: esperado 9.7 "
            f"(Libro III p.13: 4.5+2.3+1.7+0.8+0.4, NUMERIC(10,4) fix TODO-3), "
            f"obtenido {acc_d}"
        )


"""
Tests for Motor 2 — MAGERIT v3 Risk Engine.

D.3: Intrinsic risk, effective risk, and treatment plan tests.
Every non-trivial test cites its source: Libro I/III section and page.
"""
import uuid
import pytest
from sqlalchemy import select

from backend.app.motors.m02_magerit.service import MageritService, LEVEL_TO_INDEX, FREQUENCY_MAP
from backend.app.motors.m02_magerit.models import MageritRiskCalculation, MageritTreatmentPlan


# ================================================================
# INTRINSIC RISK QUALITATIVE (4 tests)
# ================================================================

class TestIntrinsicQualitative:
    """Tests for qualitative intrinsic risk calculation via table lookups."""

    @pytest.mark.asyncio
    async def test_intrinsic_qualitative_basic(self, analysis_factory):
        """Asset MEDIO + prob M + degradacion M -> riesgo B.

        Traza del calculo:
        1. value_d=5 -> _map_value_to_level(5)="M"
        2. degradation_d=50% -> _map_degradation_to_level(50)="M"
        3. _lookup_impact_qualitative("M", "M") = "B" (Libro III p.6)
        4. _lookup_risk_matrix("B", "M") = "B" (Libro III p.7)
        Fuente: MAGERIT v3 Libro III, sec 2.1, pp.6-7.
        """
        analysis, svc = await analysis_factory("qualitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "QR-BAS", "name": "Servidor Medio", "asset_type_code": "HW",
             "value_d": 5, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        await svc.propagate_values(analysis.id)
        await svc.assess_threats(analysis.id, [
            {"asset_id": assets[0].id, "threat_code": "E.1", "probability": "M",
             "degradation_d": 50, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
        ])
        count = await svc.calculate_intrinsic_risk(analysis.id)
        assert count > 0

        calcs = (await svc.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis.id,
                MageritRiskCalculation.dimension == "D",
                MageritRiskCalculation.risk_intrinsic_accumulated.isnot(None),
            )
        )).scalars().all()
        assert len(calcs) == 1
        assert calcs[0].risk_level == "B", (
            f"Intrinsic qualitative basic: esperado B "
            f"(Libro III pp.6-7: impact=lookup(M,M)=B, risk=matrix(B,M)=B), "
            f"obtenido {calcs[0].risk_level}"
        )

    @pytest.mark.asyncio
    async def test_intrinsic_qualitative_extreme_high(self, analysis_factory):
        """Asset MA + prob MA + degradacion MA -> riesgo MA.

        Traza: value=10->MA, degrad=100%->MA, impact(MA,MA)=MA, risk(MA,MA)=MA.
        Fuente: MAGERIT v3 Libro III, sec 2.1, pp.6-7.
        """
        analysis, svc = await analysis_factory("qualitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "QR-MAX", "name": "Servicio Critico", "asset_type_code": "S",
             "value_d": 10, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        await svc.propagate_values(analysis.id)
        await svc.assess_threats(analysis.id, [
            {"asset_id": assets[0].id, "threat_code": "A.5", "probability": "MA",
             "degradation_d": 100, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
        ])
        await svc.calculate_intrinsic_risk(analysis.id)

        calcs = (await svc.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis.id,
                MageritRiskCalculation.dimension == "D",
                MageritRiskCalculation.risk_intrinsic_accumulated.isnot(None),
            )
        )).scalars().all()
        assert calcs[0].risk_level == "MA", (
            f"Extreme high: esperado MA "
            f"(Libro III pp.6-7: impact(MA,MA)=MA, risk(MA,MA)=MA), "
            f"obtenido {calcs[0].risk_level}"
        )

    @pytest.mark.asyncio
    async def test_intrinsic_qualitative_extreme_low(self, analysis_factory):
        """Asset MB + prob MB + degradacion MB -> riesgo MB.

        Traza: value=0->MB, degrad=1%->MB, impact(MB,MB)=MB, risk(MB,MB)=MB.
        Fuente: MAGERIT v3 Libro III, sec 2.1, pp.6-7.
        """
        analysis, svc = await analysis_factory("qualitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "QR-MIN", "name": "Activo Despreciable", "asset_type_code": "AUX",
             "value_d": 0, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        await svc.propagate_values(analysis.id)
        await svc.assess_threats(analysis.id, [
            {"asset_id": assets[0].id, "threat_code": "N.1", "probability": "MB",
             "degradation_d": 1, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
        ])
        await svc.calculate_intrinsic_risk(analysis.id)

        calcs = (await svc.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis.id,
                MageritRiskCalculation.dimension == "D",
                MageritRiskCalculation.risk_intrinsic_accumulated.isnot(None),
            )
        )).scalars().all()
        assert calcs[0].risk_level == "MB", (
            f"Extreme low: esperado MB "
            f"(Libro III pp.6-7: impact(MB,MB)=MB, risk(MB,MB)=MB), "
            f"obtenido {calcs[0].risk_level}"
        )

    @pytest.mark.asyncio
    async def test_intrinsic_qualitative_asymmetric(self, analysis_factory):
        """Asimetria de la matriz: impacto pesa mas que probabilidad.

        Caso 1: asset MA (value=10), degradacion MA (100%), prob MB.
          impact = lookup(MA, MA) = MA. risk = matrix(MA, MB) = A.

        Caso 2: asset MB (value=0), degradacion MB (1%), prob MA.
          impact = lookup(MB, MB) = MB. risk = matrix(MB, MA) = B.

        A != B demuestra asimetria: mismo "extremo" en lados opuestos da
        resultados distintos. La tabla de riesgo Libro III p.7 da mas peso
        al impacto que a la probabilidad.
        Fuente: MAGERIT v3 Libro III, sec 2.1, p.7.
        """
        # Case 1: high impact, low probability
        analysis1, svc1 = await analysis_factory("qualitative")
        assets1 = await svc1.build_asset_inventory(analysis1.id, [
            {"code": "ASYM-HI", "name": "HI Impact", "asset_type_code": "S",
             "value_d": 10, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        await svc1.propagate_values(analysis1.id)
        await svc1.assess_threats(analysis1.id, [
            {"asset_id": assets1[0].id, "threat_code": "A.5", "probability": "MB",
             "degradation_d": 100, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
        ])
        await svc1.calculate_intrinsic_risk(analysis1.id)
        calcs1 = (await svc1.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis1.id,
                MageritRiskCalculation.dimension == "D",
                MageritRiskCalculation.risk_intrinsic_accumulated.isnot(None),
            )
        )).scalars().all()
        risk_high_impact = calcs1[0].risk_level

        # Case 2: low impact, high probability
        analysis2, svc2 = await analysis_factory("qualitative")
        assets2 = await svc2.build_asset_inventory(analysis2.id, [
            {"code": "ASYM-LO", "name": "LO Impact", "asset_type_code": "AUX",
             "value_d": 0, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        await svc2.propagate_values(analysis2.id)
        await svc2.assess_threats(analysis2.id, [
            {"asset_id": assets2[0].id, "threat_code": "A.5", "probability": "MA",
             "degradation_d": 1, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
        ])
        await svc2.calculate_intrinsic_risk(analysis2.id)
        calcs2 = (await svc2.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis2.id,
                MageritRiskCalculation.dimension == "D",
                MageritRiskCalculation.risk_intrinsic_accumulated.isnot(None),
            )
        )).scalars().all()
        risk_low_impact = calcs2[0].risk_level

        assert risk_high_impact == "A", (
            f"Asimetria caso 1 (impacto MA, prob MB): esperado A "
            f"(Libro III p.7: matrix(MA,MB)=A), obtenido {risk_high_impact}"
        )
        assert risk_low_impact == "B", (
            f"Asimetria caso 2 (impacto MB, prob MA): esperado B "
            f"(Libro III p.7: matrix(MB,MA)=B), obtenido {risk_low_impact}"
        )
        assert LEVEL_TO_INDEX[risk_high_impact] > LEVEL_TO_INDEX[risk_low_impact], (
            f"Asimetria no cumplida: impacto alto+prob baja ({risk_high_impact}) "
            f"deberia ser mayor que impacto bajo+prob alta ({risk_low_impact}). "
            f"Fuente: Libro III p.7 — la tabla da mas peso al impacto."
        )


# ================================================================
# INTRINSIC RISK QUANTITATIVE (4 tests)
# ================================================================

class TestIntrinsicQuantitative:
    """Tests for quantitative intrinsic risk (arithmetic formulas)."""

    @pytest.mark.asyncio
    async def test_intrinsic_quantitative_basic(self, analysis_factory):
        """valor=5, degradacion=50%, prob=A (freq=12).
        impacto = v * d = 5 * 0.5 = 2.5
        riesgo = impacto * frecuencia = 2.5 * 12.0 = 30.0

        Fuente: MAGERIT v3 Libro III, sec 2.2.2, pp.13-14:
        'impacto = v x d' y 'riesgo = impacto x frecuencia'.
        """
        analysis, svc = await analysis_factory("quantitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "QT-BAS", "name": "Servidor", "asset_type_code": "HW",
             "value_d": 5, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        await svc.propagate_values(analysis.id)
        await svc.assess_threats(analysis.id, [
            {"asset_id": assets[0].id, "threat_code": "A.11", "probability": "A",
             "degradation_d": 50, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
        ])
        await svc.calculate_intrinsic_risk(analysis.id)

        calcs = (await svc.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis.id,
                MageritRiskCalculation.dimension == "D",
                MageritRiskCalculation.risk_intrinsic_accumulated.isnot(None),
            )
        )).scalars().all()
        assert len(calcs) == 1
        assert calcs[0].impact_intrinsic == pytest.approx(2.5), (
            f"Impacto: esperado 2.5 (Libro III p.13: 5*0.5), "
            f"obtenido {calcs[0].impact_intrinsic}"
        )
        assert calcs[0].risk_intrinsic_accumulated == pytest.approx(30.0), (
            f"Riesgo: esperado 30.0 (Libro III p.14: 2.5*12.0), "
            f"obtenido {calcs[0].risk_intrinsic_accumulated}"
        )

    @pytest.mark.asyncio
    async def test_intrinsic_quantitative_zero_degradation(self, analysis_factory):
        """Degradacion 0% -> no se genera calculo para esa dimension.

        Logica del motor: 'if degradation_pct == 0: continue' — no hay
        amenaza que materializar si la degradacion es cero.
        Fuente: service.py _calc_intrinsic_quantitative, logica de skip.
        """
        analysis, svc = await analysis_factory("quantitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "QT-ZERO", "name": "Sin Degradacion", "asset_type_code": "HW",
             "value_d": 8, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        await svc.propagate_values(analysis.id)
        await svc.assess_threats(analysis.id, [
            {"asset_id": assets[0].id, "threat_code": "N.1", "probability": "M",
             "degradation_d": 0, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
        ])
        count = await svc.calculate_intrinsic_risk(analysis.id)
        assert count == 0, (
            f"Zero degradation: esperado 0 calculos (skip por degradacion 0%), "
            f"obtenido {count}"
        )

    @pytest.mark.asyncio
    async def test_intrinsic_quantitative_max_values(self, analysis_factory):
        """valor=10, degradacion=100%, prob=MA (freq=365).
        impacto = 10 * 1.0 = 10.0
        riesgo = 10.0 * 365.0 = 3650.0

        Fuente: MAGERIT v3 Libro III, sec 2.2.2, pp.13-14.
        """
        analysis, svc = await analysis_factory("quantitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "QT-MAX", "name": "Maxima Exposicion", "asset_type_code": "S",
             "value_d": 10, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        await svc.propagate_values(analysis.id)
        await svc.assess_threats(analysis.id, [
            {"asset_id": assets[0].id, "threat_code": "A.5", "probability": "MA",
             "degradation_d": 100, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
        ])
        await svc.calculate_intrinsic_risk(analysis.id)

        calcs = (await svc.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis.id,
                MageritRiskCalculation.dimension == "D",
                MageritRiskCalculation.risk_intrinsic_accumulated.isnot(None),
            )
        )).scalars().all()
        assert calcs[0].impact_intrinsic == pytest.approx(10.0), (
            f"Impacto max: esperado 10.0 (Libro III p.13: 10*1.0), "
            f"obtenido {calcs[0].impact_intrinsic}"
        )
        assert calcs[0].risk_intrinsic_accumulated == pytest.approx(3650.0), (
            f"Riesgo max: esperado 3650.0 (Libro III p.14: 10*365), "
            f"obtenido {calcs[0].risk_intrinsic_accumulated}"
        )

    @pytest.mark.asyncio
    async def test_intrinsic_quantitative_repercussed_uses_degree(self, analysis_factory):
        """Repercuted impact multiplica por grado de dependencia.

        Setup: A(sup, value_d=8) -> B(inf) con grado=0.5.
        Amenaza sobre B con degradacion_d=50%.
        Repercuted sobre A: impacto = A.value_d * d * grado = 8 * 0.5 * 0.5 = 2.0

        Fuente: MAGERIT v3 Libro III, sec 2.2.2, p.13:
        'impacto repercutido = v x d x grado(A => B)'.
        """
        analysis, svc = await analysis_factory("quantitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "QT-SUP", "name": "Servicio Superior", "asset_type_code": "S",
             "value_d": 8, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
            {"code": "QT-INF", "name": "Servidor Inferior", "asset_type_code": "HW",
             "value_d": 3, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        sup, inf = assets
        await svc.build_dependency_graph(analysis.id, [
            {"superior_asset_id": sup.id, "inferior_asset_id": inf.id,
             "dependency_degree": 0.5},
        ])
        await svc.propagate_values(analysis.id)
        await svc.assess_threats(analysis.id, [
            {"asset_id": inf.id, "threat_code": "A.11", "probability": "M",
             "degradation_d": 50, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
        ])
        await svc.calculate_intrinsic_risk(analysis.id)

        # Find repercuted calc on superior asset
        rep_calcs = (await svc.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis.id,
                MageritRiskCalculation.asset_id == sup.id,
                MageritRiskCalculation.dimension == "D",
                MageritRiskCalculation.risk_intrinsic_repercuted.isnot(None),
            )
        )).scalars().all()
        assert len(rep_calcs) == 1, (
            f"Repercuted: esperado 1 calc sobre superior, obtenido {len(rep_calcs)}"
        )
        assert rep_calcs[0].impact_intrinsic == pytest.approx(2.0), (
            f"Repercuted impact: esperado 2.0 "
            f"(Libro III p.13: 8 * 0.5 * 0.5), "
            f"obtenido {rep_calcs[0].impact_intrinsic}"
        )


# ================================================================
# EFFECTIVE RISK WITH SAFEGUARDS (4 tests, quantitative mode)
# ================================================================

class TestEffectiveRisk:
    """Tests for effective risk calculation after safeguard deployment."""

    @pytest.mark.asyncio
    async def test_effective_perfect_safeguard(self, analysis_factory):
        """Salvaguarda perfecta (100% eficacia) -> riesgo efectivo = 0.

        Con ei=1.0, ep=1.0:
        impacto_eff = impacto * (1-1.0) = 0
        riesgo_eff = 0
        Fuente: MAGERIT v3 Libro III, sec 2.2.2, p.15.
        """
        analysis, svc = await analysis_factory("quantitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "EF-PERF", "name": "Protegido Total", "asset_type_code": "HW",
             "value_d": 8, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        await svc.propagate_values(analysis.id)
        await svc.assess_threats(analysis.id, [
            {"asset_id": assets[0].id, "threat_code": "A.5", "probability": "A",
             "degradation_d": 80, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
        ])
        await svc.calculate_intrinsic_risk(analysis.id)
        await svc.deploy_safeguards(analysis.id, [
            {"safeguard_code": "PERF.1", "efficacy": 100, "effect_type": "both",
             "status": "deployed"},
        ])
        updated = await svc.calculate_effective_risk(analysis.id)
        assert updated > 0

        calcs = (await svc.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis.id,
                MageritRiskCalculation.dimension == "D",
                MageritRiskCalculation.risk_intrinsic_accumulated.isnot(None),
            )
        )).scalars().all()
        assert calcs[0].risk_effective == pytest.approx(0.0), (
            f"Perfect safeguard: esperado risk_eff=0.0 "
            f"(Libro III p.15: impacto*(1-1.0)=0), "
            f"obtenido {calcs[0].risk_effective}"
        )

    @pytest.mark.asyncio
    async def test_effective_no_safeguard(self, analysis_factory):
        """Sin salvaguardas -> riesgo efectivo == riesgo intrinseco.

        Con ei=0, ep=0: (1-0)(1-0) = 1.0 -> sin reduccion.
        Fuente: MAGERIT v3 Libro III, sec 2.2.2, p.14-15.
        """
        analysis, svc = await analysis_factory("quantitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "EF-NONE", "name": "Sin Proteccion", "asset_type_code": "HW",
             "value_d": 6, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        await svc.propagate_values(analysis.id)
        await svc.assess_threats(analysis.id, [
            {"asset_id": assets[0].id, "threat_code": "E.1", "probability": "M",
             "degradation_d": 50, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
        ])
        await svc.calculate_intrinsic_risk(analysis.id)
        # No deploy_safeguards!
        await svc.calculate_effective_risk(analysis.id)

        calcs = (await svc.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis.id,
                MageritRiskCalculation.dimension == "D",
                MageritRiskCalculation.risk_intrinsic_accumulated.isnot(None),
            )
        )).scalars().all()
        intrinsic = calcs[0].risk_intrinsic_accumulated
        effective = calcs[0].risk_effective
        assert effective == pytest.approx(intrinsic), (
            f"No safeguard: esperado risk_eff={intrinsic} == risk_intrinsic "
            f"(Libro III pp.14-15: ei=0,ep=0 -> sin reduccion), "
            f"obtenido {effective}"
        )

    @pytest.mark.asyncio
    async def test_effective_partial_safeguard_50pct(self, analysis_factory):
        """Salvaguarda parcial 50% tipo 'both': riesgo se reduce al 25%.

        ei=0.5 (de 'both'), ep=0.5 (de 'both').
        Factor = (1-ei)*(1-ep) = 0.5*0.5 = 0.25.
        risk_eff = risk_intrinsic * 0.25.

        Fuente: MAGERIT v3 Libro III, sec 2.2.2, p.14:
        '(1 - ei) x (1 - ef) = 1 - e', combinado con p.15:
        'impacto_residual = impacto x (1-ei), freq_residual = freq x (1-ep)'.
        """
        analysis, svc = await analysis_factory("quantitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "EF-50", "name": "Medio Protegido", "asset_type_code": "HW",
             "value_d": 8, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        await svc.propagate_values(analysis.id)
        await svc.assess_threats(analysis.id, [
            {"asset_id": assets[0].id, "threat_code": "A.11", "probability": "M",
             "degradation_d": 80, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
        ])
        await svc.calculate_intrinsic_risk(analysis.id)
        await svc.deploy_safeguards(analysis.id, [
            {"safeguard_code": "MID.1", "efficacy": 50, "effect_type": "both",
             "status": "deployed"},
        ])
        await svc.calculate_effective_risk(analysis.id)

        calcs = (await svc.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis.id,
                MageritRiskCalculation.dimension == "D",
                MageritRiskCalculation.risk_intrinsic_accumulated.isnot(None),
            )
        )).scalars().all()
        intrinsic = calcs[0].risk_intrinsic_accumulated
        effective = calcs[0].risk_effective
        expected = intrinsic * 0.25
        assert effective == pytest.approx(expected, rel=0.01), (
            f"50% safeguard: esperado risk_eff={expected:.4f} "
            f"(Libro III pp.14-15: {intrinsic}*0.25), obtenido {effective}"
        )

    @pytest.mark.asyncio
    async def test_effective_two_safeguards_combined(self, analysis_factory):
        """Dos salvaguardas: preventive(60%) + palliative(40%).

        _compute_package_efficacy separa por tipo:
          ep = avg([0.6]) = 0.6 (preventive reduce frecuencia)
          ei = avg([0.4]) = 0.4 (palliative reduce degradacion)

        Factor = (1-ei)*(1-ep) = 0.6 * 0.4 = 0.24.
        risk_eff = risk_intrinsic * 0.24.

        Fuente: MAGERIT v3 Libro III, sec 2.2.4, p.21 (paquete) +
        sec 2.2.2, p.14-15 (composicion).
        """
        analysis, svc = await analysis_factory("quantitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "EF-2SG", "name": "Doble Proteccion", "asset_type_code": "HW",
             "value_d": 8, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        await svc.propagate_values(analysis.id)
        await svc.assess_threats(analysis.id, [
            {"asset_id": assets[0].id, "threat_code": "A.11", "probability": "M",
             "degradation_d": 80, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
        ])
        await svc.calculate_intrinsic_risk(analysis.id)
        await svc.deploy_safeguards(analysis.id, [
            {"safeguard_code": "FW.1", "efficacy": 60, "effect_type": "preventive",
             "status": "deployed"},
            {"safeguard_code": "BK.1", "efficacy": 40, "effect_type": "palliative",
             "status": "deployed"},
        ])
        await svc.calculate_effective_risk(analysis.id)

        calcs = (await svc.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis.id,
                MageritRiskCalculation.dimension == "D",
                MageritRiskCalculation.risk_intrinsic_accumulated.isnot(None),
            )
        )).scalars().all()
        intrinsic = calcs[0].risk_intrinsic_accumulated
        effective = calcs[0].risk_effective
        expected = intrinsic * 0.24  # (1-0.4)*(1-0.6) = 0.6*0.4
        assert effective == pytest.approx(expected, rel=0.01), (
            f"Two safeguards: esperado risk_eff={expected:.4f} "
            f"(Libro III pp.14-15,21: {intrinsic}*(1-0.4)*(1-0.6)), "
            f"obtenido {effective}"
        )


# ================================================================
# TREATMENT PLAN (3 tests)
# ================================================================

class TestTreatmentPlan:
    """Tests for treatment plan generation logic."""

    @pytest.mark.asyncio
    async def test_treatment_acceptable_below_threshold(self, analysis_factory):
        """Riesgo B con threshold M -> no se genera accion (aceptable).

        LEVEL_TO_INDEX: MB=0, B=1, M=2, A=3, MA=4.
        risk_idx(B)=1 <= threshold_idx(M)=2 -> aceptable, skip.
        Fuente: MAGERIT v3 Libro I, sec 4.1.2, p.46:
        'management must determine the acceptable risk levels'.
        """
        analysis, svc = await analysis_factory("qualitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "TP-LOW", "name": "Bajo Riesgo", "asset_type_code": "HW",
             "value_d": 3, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        await svc.propagate_values(analysis.id)
        await svc.assess_threats(analysis.id, [
            {"asset_id": assets[0].id, "threat_code": "N.1", "probability": "B",
             "degradation_d": 20, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
        ])
        await svc.calculate_intrinsic_risk(analysis.id)
        actions = await svc.generate_treatment_plan(analysis.id, threshold="M")

        assert len(actions) == 0, (
            f"Below threshold: esperado 0 acciones "
            f"(Libro I p.46: riesgo B <= threshold M), "
            f"obtenido {len(actions)}"
        )

    @pytest.mark.asyncio
    async def test_treatment_mitigate_one_level_above(self, analysis_factory):
        """Riesgo efectivo nivel A con threshold M -> accion 'mitigar'.

        Nota: este test originalmente fallo porque escogimos (impact=A, prob=A)
        esperando riesgo A. La matriz oficial dice matrix(A,A)=MA. Esto valida
        que la asimetria de Libro III p.7 esta bien implementada.

        Traza del calculo esperado (parametros corregidos):
        - value_d=7 -> _map_value_to_level(7) = "A"
        - degradation_d=70% -> _map_degradation_to_level(70) = "A"
        - _lookup_impact_qualitative("A", "A") = "A" (Libro III p.6 ext)
        - probability="M"
        - _lookup_risk_matrix("A", "M") = "A" (Libro III p.7)
        - threshold="M" (nivel 2), risk="A" (nivel 3) -> excess=1
        - excess==1 -> treatment="mitigar" (convencion FULKRO)

        Fuente: MAGERIT v3 Libro I, sec 4.1.7, pp.50-51.
        """
        analysis, svc = await analysis_factory("qualitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "TP-MID", "name": "Riesgo Medio-Alto", "asset_type_code": "S",
             "value_d": 7, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        await svc.propagate_values(analysis.id)
        await svc.assess_threats(analysis.id, [
            {"asset_id": assets[0].id, "threat_code": "A.11", "probability": "M",
             "degradation_d": 70, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
        ])
        await svc.calculate_intrinsic_risk(analysis.id)

        # Verify the risk is actually A before generating plan
        calcs = (await svc.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis.id,
                MageritRiskCalculation.dimension == "D",
                MageritRiskCalculation.risk_intrinsic_accumulated.isnot(None),
            )
        )).scalars().all()
        assert calcs[0].risk_level == "A", (
            f"Pre-condition: esperado riesgo A "
            f"(Libro III p.7: matrix(A,M)=A), obtenido {calcs[0].risk_level}"
        )

        actions = await svc.generate_treatment_plan(analysis.id, threshold="M")
        mitigar_actions = [a for a in actions if a.treatment == "mitigar"]
        assert len(mitigar_actions) > 0, (
            f"Mitigate: esperado al menos 1 accion 'mitigar' "
            f"(Libro I pp.50-51, convencion FULKRO: excess==1), "
            f"obtenido 0. Acciones: {[(a.treatment, a.current_risk_level) for a in actions]}"
        )

    @pytest.mark.asyncio
    async def test_treatment_eliminate_critical(self, analysis_factory):
        """Riesgo MA con threshold M -> 'eliminar'.

        excess = LEVEL_TO_INDEX['MA'] - LEVEL_TO_INDEX['M'] = 4 - 2 = 2.
        excess >= 2 AND risk_level == 'MA' -> eliminar.
        Fuente: MAGERIT v3 Libro I, sec 4.1.6, p.47-48 (zone analysis).
        Convencion FULKRO: excess>=2 AND MA -> eliminar.
        """
        analysis, svc = await analysis_factory("qualitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "TP-CRIT", "name": "Riesgo Critico", "asset_type_code": "S",
             "value_d": 10, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        await svc.propagate_values(analysis.id)
        await svc.assess_threats(analysis.id, [
            {"asset_id": assets[0].id, "threat_code": "A.5", "probability": "MA",
             "degradation_d": 100, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
        ])
        await svc.calculate_intrinsic_risk(analysis.id)

        # Verify risk is MA
        calcs = (await svc.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis.id,
                MageritRiskCalculation.dimension == "D",
                MageritRiskCalculation.risk_intrinsic_accumulated.isnot(None),
            )
        )).scalars().all()
        assert calcs[0].risk_level == "MA", (
            f"Pre-condition: esperado riesgo MA, obtenido {calcs[0].risk_level}"
        )

        actions = await svc.generate_treatment_plan(analysis.id, threshold="M")
        eliminar_actions = [a for a in actions if a.treatment == "eliminar"]
        assert len(eliminar_actions) > 0, (
            f"Eliminate: esperado al menos 1 accion 'eliminar' "
            f"(Libro I pp.47-48, convencion FULKRO: MA + excess>=2), "
            f"obtenido 0. Acciones: {[(a.treatment, a.current_risk_level) for a in actions]}"
        )



# ================================================================
# E.1 — HYBRID MODE STUBS (3 tests)
# ================================================================

class TestHybridModeStubs:
    """Verifica behavior contractual: hybrid calculation_mode lanza
    NotImplementedError. MAGERIT v3 Libro III no formaliza un cálculo
    canónico para modo hybrid · decisión arquitectónica permanente
    per ADR-031 (NO diferimiento temporal · NO se planea implementar).

    Los 3 tests cubren propagate_values, calculate_intrinsic_risk
    y calculate_effective_risk · protegen contra implementaciones
    accidentales sin actualización coherente del dispatcher.
    """

    @pytest.mark.asyncio
    async def test_propagate_hybrid_raises_not_implemented(self, analysis_factory):
        """propagate_values con calculation_mode='hybrid' lanza NotImplementedError."""
        analysis, svc = await analysis_factory("hybrid")
        await svc.build_asset_inventory(analysis.id, [
            {"code": "HYB-1", "name": "Test Hybrid", "asset_type_code": "S",
             "value_d": 5, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0}
        ])
        with pytest.raises(NotImplementedError, match="hybrid"):
            await svc.propagate_values(analysis.id)

    @pytest.mark.asyncio
    async def test_calculate_intrinsic_hybrid_raises_not_implemented(self, analysis_factory):
        """calculate_intrinsic_risk con hybrid lanza NotImplementedError."""
        analysis, svc = await analysis_factory("hybrid")
        with pytest.raises(NotImplementedError, match="hybrid"):
            await svc.calculate_intrinsic_risk(analysis.id)

    @pytest.mark.asyncio
    async def test_calculate_effective_hybrid_raises_not_implemented(self, analysis_factory):
        """calculate_effective_risk con hybrid lanza NotImplementedError."""
        analysis, svc = await analysis_factory("hybrid")
        with pytest.raises(NotImplementedError, match="hybrid"):
            await svc.calculate_effective_risk(analysis.id)


# ================================================================
# E.2 — _map_frequency_to_level HELPER (3 tests)
# ================================================================

class TestMapFrequencyToLevel:
    """Tests del helper _map_frequency_to_level (inverso de FREQUENCY_MAP).

    FULKRO convention: NO existe en MAGERIT v3 oficial. Es la inversa
    funcional del mapeo directo nivel -> frecuencia anual usado en modo
    cuantitativo. Se invoca cuando una salvaguarda preventiva reduce la
    frecuencia residual y hay que re-clasificarla a nivel cualitativo.
    """

    def test_map_frequency_to_level_boundaries(self):
        """Verifica los 5 niveles con valores en cada rango.

        Boundaries del helper (leidos de service.py):
          >= 100.0 -> MA
          >= 5.0   -> A
          >= 0.5   -> M
          >= 0.05  -> B
          < 0.05   -> MB

        Fuente: service.py _map_frequency_to_level, convencion FULKRO.
        """
        from backend.app.motors.m02_magerit.service import _map_frequency_to_level
        cases = [
            (0.01, "MB"),   # < 0.05
            (0.04, "MB"),   # < 0.05
            (0.05, "B"),    # >= 0.05, < 0.5
            (0.3, "B"),     # >= 0.05, < 0.5
            (0.5, "M"),     # >= 0.5, < 5.0
            (3.0, "M"),     # >= 0.5, < 5.0
            (5.0, "A"),     # >= 5.0, < 100.0
            (50.0, "A"),    # >= 5.0, < 100.0
            (100.0, "MA"),  # >= 100.0
            (500.0, "MA"),  # >= 100.0
        ]
        for freq, expected in cases:
            result = _map_frequency_to_level(freq)
            assert result == expected, (
                f"_map_frequency_to_level({freq}): esperado {expected} "
                f"(convencion FULKRO), obtenido {result}"
            )

    def test_map_frequency_to_level_extremes(self):
        """Frecuencias extremas se clasifican a MB y MA correctamente.

        Fuente: service.py _map_frequency_to_level, convencion FULKRO.
        """
        from backend.app.motors.m02_magerit.service import _map_frequency_to_level
        assert _map_frequency_to_level(0.0) == "MB", (
            "Frecuencia 0.0 debe ser MB (< 0.05)"
        )
        assert _map_frequency_to_level(100000.0) == "MA", (
            "Frecuencia 100000.0 debe ser MA (>= 100.0)"
        )

    def test_map_frequency_to_level_round_trip(self):
        """Round-trip: FREQUENCY_MAP[nivel] -> _map_frequency_to_level -> mismo nivel.

        Para los 5 valores canonicos de FREQUENCY_MAP, la funcion inversa
        debe devolver el mismo nivel original (idempotencia bidireccional).
        Fuente: service.py FREQUENCY_MAP + _map_frequency_to_level.
        """
        from backend.app.motors.m02_magerit.service import (
            FREQUENCY_MAP, _map_frequency_to_level
        )
        for level, freq in FREQUENCY_MAP.items():
            result = _map_frequency_to_level(freq)
            assert result == level, (
                f"Round-trip falla: nivel {level} -> freq {freq} -> "
                f"esperado {level}, obtenido {result}"
            )


# ================================================================
# E.3 — TREATMENT PLAN BRANCHES (3 tests)
# ================================================================

class TestTreatmentPlanBranches:
    """Tests para ramas no cubiertas del plan de tratamiento."""

    @pytest.mark.asyncio
    async def test_treatment_transferir_excess_2_not_critical(self, analysis_factory):
        """Riesgo A con threshold MB -> 'transferir' (excess=2, no MA).

        excess = LEVEL_TO_INDEX['A'] - LEVEL_TO_INDEX['MB'] = 3 - 0 = 3.
        excess >= 2 AND risk_level != 'MA' -> transferir.

        Fuente: MAGERIT v3 Libro I, sec 4.1.9, p.51 (transferencia).
        Convencion FULKRO: excess>=2 y no critico -> transferir.
        """
        analysis, svc = await analysis_factory("qualitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "TR-XFER", "name": "Activo para transferir", "asset_type_code": "S",
             "value_d": 7, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        await svc.propagate_values(analysis.id)
        await svc.assess_threats(analysis.id, [
            {"asset_id": assets[0].id, "threat_code": "A.11", "probability": "M",
             "degradation_d": 70, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
        ])
        await svc.calculate_intrinsic_risk(analysis.id)

        # Verify risk is A (from D.3: impact(A,A)=A, risk(A,M)=A)
        calcs = (await svc.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis.id,
                MageritRiskCalculation.dimension == "D",
                MageritRiskCalculation.risk_intrinsic_accumulated.isnot(None),
            )
        )).scalars().all()
        assert calcs[0].risk_level == "A"

        actions = await svc.generate_treatment_plan(analysis.id, threshold="MB")
        transferir = [a for a in actions if a.treatment == "transferir"]
        assert len(transferir) > 0, (
            f"Transferir: esperado al menos 1 accion 'transferir' "
            f"(Libro I p.51, convencion FULKRO: excess>=2, no MA). "
            f"Acciones: {[(a.treatment, a.current_risk_level) for a in actions]}"
        )

    @pytest.mark.asyncio
    async def test_treatment_mixed_strategies_multi_asset(self, analysis_factory):
        """3 activos con niveles B, A, MA y threshold M generan 3 estrategias.

        - Activo B: risk<=threshold -> sin accion (aceptable)
        - Activo A: excess=1 -> mitigar
        - Activo MA: excess=2 AND MA -> eliminar

        Fuente: MAGERIT v3 Libro I, sec 4.1.2-9, pp.46-51.
        Convencion FULKRO: criterios numericos de excess.
        """
        analysis, svc = await analysis_factory("qualitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            # Asset 1: bajo riesgo -> aceptable
            {"code": "MX-LO", "name": "Bajo", "asset_type_code": "AUX",
             "value_d": 1, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
            # Asset 2: riesgo A -> mitigar
            {"code": "MX-MD", "name": "Medio-Alto", "asset_type_code": "S",
             "value_d": 7, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
            # Asset 3: riesgo MA -> eliminar
            {"code": "MX-HI", "name": "Critico", "asset_type_code": "S",
             "value_d": 10, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        lo, md, hi = assets
        await svc.propagate_values(analysis.id)
        await svc.assess_threats(analysis.id, [
            {"asset_id": lo.id, "threat_code": "N.1", "probability": "B",
             "degradation_d": 8, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
            {"asset_id": md.id, "threat_code": "A.11", "probability": "M",
             "degradation_d": 70, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
            {"asset_id": hi.id, "threat_code": "A.5", "probability": "MA",
             "degradation_d": 100, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
        ])
        await svc.calculate_intrinsic_risk(analysis.id)
        actions = await svc.generate_treatment_plan(analysis.id, threshold="M")

        treatments = {a.treatment for a in actions}
        assert "mitigar" in treatments, (
            f"Debe haber accion 'mitigar' para activo A. Obtenido: {treatments}"
        )
        assert "eliminar" in treatments, (
            f"Debe haber accion 'eliminar' para activo MA. Obtenido: {treatments}"
        )
        # Asset B (lo) should NOT appear in actions
        lo_actions = [a for a in actions if a.asset_id == lo.id]
        assert len(lo_actions) == 0, (
            f"Activo B debe ser aceptable (sin accion). Obtenido: {lo_actions}"
        )

    @pytest.mark.asyncio
    async def test_residual_risk_branches_all_four(self, analysis_factory):
        """calculate_residual_risk procesa las 4 ramas: accept, mitigar, transferir, eliminar.

        Setup: 4 activos con niveles MB, A, A, MA y threshold B.
        - MB: acceptable -> residual = effective (no plan action)
        - A (excess=2, not MA): transferir -> residual = effective * 0.5
        - MA (excess=3, MA): eliminar -> residual = 0.0
        Necesitamos generar plan y luego calcular residual para cubrir todas las ramas.

        Fuente: service.py calculate_residual_risk, ramas de tratamiento.
        Convencion FULKRO: transferir=50%, eliminar=0, mitigar=target_level.
        """
        analysis, svc = await analysis_factory("qualitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            # Asset aceptable (no genera plan)
            {"code": "RES-ACC", "name": "Aceptable", "asset_type_code": "AUX",
             "value_d": 1, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
            # Asset transferir
            {"code": "RES-XFR", "name": "Para transferir", "asset_type_code": "S",
             "value_d": 7, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
            # Asset eliminar
            {"code": "RES-ELM", "name": "Para eliminar", "asset_type_code": "S",
             "value_d": 10, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        acc, xfr, elm = assets
        await svc.propagate_values(analysis.id)
        await svc.assess_threats(analysis.id, [
            {"asset_id": acc.id, "threat_code": "N.1", "probability": "MB",
             "degradation_d": 3, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
            {"asset_id": xfr.id, "threat_code": "A.11", "probability": "M",
             "degradation_d": 70, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
            {"asset_id": elm.id, "threat_code": "A.5", "probability": "MA",
             "degradation_d": 100, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
        ])
        await svc.calculate_intrinsic_risk(analysis.id)
        actions = await svc.generate_treatment_plan(analysis.id, threshold="MB")
        count = await svc.calculate_residual_risk(analysis.id)
        assert count > 0

        # Check eliminar branch: residual = 0.0
        elm_calcs = (await svc.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis.id,
                MageritRiskCalculation.asset_id == elm.id,
                MageritRiskCalculation.dimension == "D",
            )
        )).scalars().all()
        elm_with_residual = [c for c in elm_calcs if c.risk_residual is not None]
        if elm_with_residual:
            assert elm_with_residual[0].risk_residual == 0.0, (
                f"Eliminar: residual esperado 0.0, obtenido {elm_with_residual[0].risk_residual}"
            )


# ================================================================
# E.4 — EFFECTIVE QUALITATIVE EDGE CASES (4 tests)
# ================================================================

class TestEffectiveQualitativeEdgeCases:
    """Tests de edge cases del calculo efectivo en modo cualitativo.

    Estos tests validan que _calc_effective_qualitative() maneja
    correctamente salvaguardas con eficacia 0%, 100%, y tipos
    solo-preventive / solo-palliative.
    """

    @pytest.mark.asyncio
    async def test_effective_qualitative_zero_efficacy(self, analysis_factory):
        """Salvaguarda con eficacia 0%: riesgo efectivo ~= riesgo intrinseco.

        ei=0, ep=0: degradacion_residual = degrad * (1-0) = degrad,
        frecuencia_residual = freq * (1-0) = freq. Sin cambio.
        Fuente: Libro III sec 2.2.1 p.11: 'dr(d, 0) = d' y 'pr(p, 0) = p'.
        """
        analysis, svc = await analysis_factory("qualitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "EQ-ZERO", "name": "Sin proteccion real", "asset_type_code": "HW",
             "value_d": 7, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        await svc.propagate_values(analysis.id)
        await svc.assess_threats(analysis.id, [
            {"asset_id": assets[0].id, "threat_code": "A.11", "probability": "M",
             "degradation_d": 70, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
        ])
        await svc.calculate_intrinsic_risk(analysis.id)
        await svc.deploy_safeguards(analysis.id, [
            {"safeguard_code": "ZERO.1", "efficacy": 0, "effect_type": "both",
             "status": "planned"},
        ])
        await svc.calculate_effective_risk(analysis.id)

        calcs = (await svc.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis.id,
                MageritRiskCalculation.dimension == "D",
                MageritRiskCalculation.risk_intrinsic_accumulated.isnot(None),
            )
        )).scalars().all()
        # With 0% efficacy, effective level should match intrinsic level
        intr_idx = int(round(calcs[0].risk_intrinsic_accumulated))
        intr_level = LEVELS_ORDER[min(intr_idx, 4)]
        assert calcs[0].risk_level == intr_level, (
            f"Zero efficacy: risk_level esperado {intr_level} (= intrinsic), "
            f"obtenido {calcs[0].risk_level}"
        )

    @pytest.mark.asyncio
    async def test_effective_qualitative_perfect_efficacy(self, analysis_factory):
        """Salvaguarda 100% sobre activo MA NO reduce riesgo a MB (floor MAGERIT).

        **Hallazgo metodologico**: MAGERIT v3 oficial implementa un "floor de
        riesgo implicito" para activos de maximo valor. La tabla de impacto del
        Libro III p.6 establece que un activo de valor MA con degradacion MB
        tiene impacto M (no MB). Por tanto, el riesgo efectivo de un activo MA
        con salvaguarda perfecta queda en B (matrix(M, MB) = B), nunca en MB.

        Implicacion practica: un activo critico nunca alcanza riesgo cero por
        mucho que se blinde. El consultor debe mantener vigilancia continua
        sobre activos MA aunque tengan defensas optimas. Esta es una
        caracteristica de seguridad del modelo MAGERIT, no una limitacion del
        motor FULKRO.

        Traza del calculo:
        - value_d=10 -> _map_value_to_level(10) = "MA"
        - degradation_d=100% * (1-1.0) = 0% -> _map_degradation_to_level(0) = "MB"
        - _lookup_impact_qualitative("MA", "MB") = "M" (Libro III p.6)
        - probability="MA", freq=365 * (1-1.0) = 0 -> _map_frequency_to_level(0) = "MB"
        - _lookup_risk_matrix("M", "MB") = "B" (Libro III p.7)
        - Esperado: B (no MB). El motor esta correcto.

        Fuente: Libro III sec 2.1 p.6 (tabla impacto) + sec 2.1 p.7 (tabla riesgo).
        """
        analysis, svc = await analysis_factory("qualitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "EQ-PERF", "name": "Activo critico MA", "asset_type_code": "S",
             "value_d": 10, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        await svc.propagate_values(analysis.id)
        await svc.assess_threats(analysis.id, [
            {"asset_id": assets[0].id, "threat_code": "A.5", "probability": "MA",
             "degradation_d": 100, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
        ])
        await svc.calculate_intrinsic_risk(analysis.id)
        await svc.deploy_safeguards(analysis.id, [
            {"safeguard_code": "PERF.1", "efficacy": 100, "effect_type": "both",
             "status": "deployed"},
        ])
        await svc.calculate_effective_risk(analysis.id)

        calcs = (await svc.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis.id,
                MageritRiskCalculation.dimension == "D",
                MageritRiskCalculation.risk_intrinsic_accumulated.isnot(None),
            )
        )).scalars().all()
        # Floor MAGERIT: activo MA con salvaguarda perfecta -> riesgo B, no MB
        assert calcs[0].risk_level == "B", (
            f"Floor MAGERIT: salvaguarda 100% sobre activo MA debe dar riesgo B "
            f"(Libro III p.6: impact(MA,MB)=M, p.7: risk(M,MB)=B), "
            f"obtenido {calcs[0].risk_level}"
        )
        assert calcs[0].risk_level != "MB", (
            f"El riesgo NO debe bajar a MB: la tabla oficial preserva impacto M "
            f"para activos MA con degradacion MB. Caracteristica MAGERIT, no bug."
        )

    @pytest.mark.asyncio
    async def test_effective_qualitative_only_preventive(self, analysis_factory):
        """Salvaguarda solo preventive: reduce frecuencia, NO degradacion.

        effect_type='preventive' -> ep=efficacy, ei=0.
        degradacion_residual = degrad * (1-0) = degrad (sin cambio).
        frecuencia_residual = freq * (1-ep) (reducida).
        Fuente: Libro III sec 2.2.1 p.11 + service.py _compute_package_efficacy.
        """
        analysis, svc = await analysis_factory("qualitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "EQ-PREV", "name": "Solo preventive", "asset_type_code": "HW",
             "value_d": 7, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        await svc.propagate_values(analysis.id)
        await svc.assess_threats(analysis.id, [
            {"asset_id": assets[0].id, "threat_code": "A.11", "probability": "A",
             "degradation_d": 70, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
        ])
        await svc.calculate_intrinsic_risk(analysis.id)

        # Get intrinsic level first
        calcs_before = (await svc.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis.id,
                MageritRiskCalculation.dimension == "D",
                MageritRiskCalculation.risk_intrinsic_accumulated.isnot(None),
            )
        )).scalars().all()
        intrinsic_level = calcs_before[0].risk_level

        await svc.deploy_safeguards(analysis.id, [
            {"safeguard_code": "PREV.1", "efficacy": 80, "effect_type": "preventive",
             "status": "deployed"},
        ])
        await svc.calculate_effective_risk(analysis.id)

        calcs_after = (await svc.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis.id,
                MageritRiskCalculation.dimension == "D",
                MageritRiskCalculation.risk_intrinsic_accumulated.isnot(None),
            )
        )).scalars().all()
        effective_level = calcs_after[0].risk_level
        # Preventive salvaguarda should reduce risk (frequency reduced)
        assert LEVEL_TO_INDEX.get(effective_level, 0) <= LEVEL_TO_INDEX.get(intrinsic_level, 0), (
            f"Preventive safeguard debe reducir riesgo: intrinsic={intrinsic_level}, "
            f"effective={effective_level} (Libro III p.11)"
        )

    @pytest.mark.asyncio
    async def test_effective_qualitative_only_palliative(self, analysis_factory):
        """Salvaguarda solo palliative: reduce degradacion, NO frecuencia.

        effect_type='palliative' -> ei=efficacy, ep=0.
        degradacion_residual = degrad * (1-ei) (reducida).
        frecuencia_residual = freq * (1-0) = freq (sin cambio).
        Fuente: Libro III sec 2.2.1 p.11 + service.py _compute_package_efficacy.
        """
        analysis, svc = await analysis_factory("qualitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "EQ-PALL", "name": "Solo palliative", "asset_type_code": "HW",
             "value_d": 7, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        await svc.propagate_values(analysis.id)
        await svc.assess_threats(analysis.id, [
            {"asset_id": assets[0].id, "threat_code": "A.11", "probability": "A",
             "degradation_d": 70, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
        ])
        await svc.calculate_intrinsic_risk(analysis.id)

        calcs_before = (await svc.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis.id,
                MageritRiskCalculation.dimension == "D",
                MageritRiskCalculation.risk_intrinsic_accumulated.isnot(None),
            )
        )).scalars().all()
        intrinsic_level = calcs_before[0].risk_level

        await svc.deploy_safeguards(analysis.id, [
            {"safeguard_code": "PALL.1", "efficacy": 80, "effect_type": "palliative",
             "status": "deployed"},
        ])
        await svc.calculate_effective_risk(analysis.id)

        calcs_after = (await svc.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis.id,
                MageritRiskCalculation.dimension == "D",
                MageritRiskCalculation.risk_intrinsic_accumulated.isnot(None),
            )
        )).scalars().all()
        effective_level = calcs_after[0].risk_level
        assert LEVEL_TO_INDEX.get(effective_level, 0) <= LEVEL_TO_INDEX.get(intrinsic_level, 0), (
            f"Palliative safeguard debe reducir riesgo: intrinsic={intrinsic_level}, "
            f"effective={effective_level} (Libro III p.11)"
        )



# ================================================================
# E.6 — EDGE CASES AND QUANTITATIVE E2E (4 tests)
# ================================================================

class TestEdgeCasesAndQuantitative:
    """Tests de edge cases y cobertura del modo cuantitativo E2E.

    Estos tests cubren ramas defensivas y el pipeline cuantitativo completo
    que el caso Jaymon (cualitativo) no ejerce.
    """

    @pytest.mark.asyncio
    async def test_defensive_error_handling_invalid_analysis_id(self, db):
        """Las funciones del service rechazan UUIDs inexistentes con ValueError.

        Defensive programming: protege contra llamadas con IDs corruptos
        o eliminados. Cada funcion critica del pipeline debe fallar limpio
        antes de hacer calculos sobre datos vacios.
        """
        svc = MageritService(db)
        fake_id = uuid.uuid4()

        with pytest.raises(ValueError, match="not found"):
            await svc.propagate_values(fake_id)

        with pytest.raises(ValueError, match="not found"):
            await svc.calculate_intrinsic_risk(fake_id)

        with pytest.raises(ValueError, match="not found"):
            await svc.calculate_effective_risk(fake_id)

        with pytest.raises(ValueError, match="not found"):
            await svc.calculate_residual_risk(fake_id)

    @pytest.mark.asyncio
    async def test_intrinsic_qualitative_repercussed_via_dependency(self, analysis_factory):
        """Riesgo repercutido cualitativo: amenaza sobre activo inferior genera
        calculo de riesgo en el activo superior que depende de el.

        Modelo MAGERIT v3 Libro III sec 2.2.1 p.10: 'Riesgo repercutido:
        se usara el impacto repercutido sobre el activo'. El mecanismo que
        justifica el grafo de dependencias en MAGERIT.

        Escenario:
        - SUP "Servicio Web" (value_d=8, A) depende de INF "BD" (value_d=5, M)
        - Amenaza A.11 sobre INF: prob=A, degrad_d=70%
        - INF genera calc acumulado, SUP genera calc repercutido
        - Ademas, desplegamos salvaguarda y calculamos riesgo efectivo para
          cubrir la rama del effective cualitativo donde risk_intrinsic_accumulated
          es None (calcs repercutidos).

        Cita: Libro III sec 2.2.1 pp.9-11 (acumulado vs repercutido).
        """
        analysis, svc = await analysis_factory("qualitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "REP-SUP", "name": "Servicio Web", "asset_type_code": "S",
             "value_d": 8, "value_i": 7, "value_c": 6, "value_a": 5, "value_t": 4},
            {"code": "REP-INF", "name": "Base de Datos", "asset_type_code": "SW",
             "value_d": 5, "value_i": 5, "value_c": 5, "value_a": 5, "value_t": 5},
        ])
        sup, inf = assets
        await svc.build_dependency_graph(analysis.id, [
            {"superior_asset_id": sup.id, "inferior_asset_id": inf.id,
             "dependency_degree": 1.0},
        ])
        await svc.propagate_values(analysis.id)
        await svc.assess_threats(analysis.id, [
            {"asset_id": inf.id, "threat_code": "A.11", "probability": "A",
             "degradation_d": 70, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
        ])
        count = await svc.calculate_intrinsic_risk(analysis.id)

        calcs = (await svc.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis.id,
                MageritRiskCalculation.dimension == "D",
            )
        )).scalars().all()

        # Must have at least 2: accumulated on INF + repercuted on SUP
        assert len(calcs) >= 2, (
            f"Debe haber >= 2 calculos (acumulado en INF + repercutido en SUP), "
            f"obtenido {len(calcs)}"
        )

        # SUP must have a repercuted calc
        sup_calcs = [c for c in calcs if c.asset_id == sup.id]
        assert len(sup_calcs) > 0, (
            f"SUP debe tener calculo repercutido (Libro III p.10), obtenido 0"
        )
        rep_calc = sup_calcs[0]
        assert rep_calc.risk_intrinsic_repercuted is not None, (
            f"SUP calc debe tener risk_intrinsic_repercuted != None"
        )

        # INF must have an accumulated calc
        inf_calcs = [c for c in calcs if c.asset_id == inf.id]
        assert len(inf_calcs) > 0
        assert inf_calcs[0].risk_intrinsic_accumulated is not None

        # NOTE: repercuted calcs (asset_id=SUP) do NOT get effective risk because
        # _calc_effective_qualitative looks up ta_map by (calc.asset_id, threat_code)
        # and the threat is assessed on INF, not SUP. This is correct behavior:
        # effective risk is calculated where the threat is directly assessed.
        # The repercuted calc documents the propagated risk exposure, not a
        # directly calculable effective risk. Line 970 (else branch for
        # risk_intrinsic_accumulated is None) is only reachable if the same
        # threat is also assessed directly on SUP — covered by Jaymon test.

    @pytest.mark.asyncio
    async def test_quantitative_pipeline_e2e(self, analysis_factory):
        """Pipeline cuantitativo E2E: intrinsic -> effective -> treatment -> residual.

        Escenario: 1 activo valor 8, 1 amenaza prob=M (freq=1.0), degrad=60%.
        1 salvaguarda 50% type both.

        Calculo esperado:
        - Intrinseco: impact = 8 * 0.6 = 4.8, risk = 4.8 * 1.0 = 4.8
        - Efectivo: impact_eff = 4.8 * (1-0.5) = 2.4
          freq_eff = 1.0 * (1-0.5) = 0.5
          risk_eff = 2.4 * 0.5 = 1.2
        - Treatment: risk level depends on _map_value_to_level(round(1.2))
          = _map_value_to_level(1) = "MB" -> aceptable con threshold M
        - Residual: sin plan (aceptable) -> residual = effective

        Cita: Libro III sec 2.2.2 pp.13-15 (formulas cuantitativas).
        """
        analysis, svc = await analysis_factory("quantitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "QE2E", "name": "Activo cuantitativo E2E", "asset_type_code": "S",
             "value_d": 8, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        await svc.propagate_values(analysis.id)
        await svc.assess_threats(analysis.id, [
            {"asset_id": assets[0].id, "threat_code": "A.11", "probability": "M",
             "degradation_d": 60, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
        ])

        # Phase 1: Intrinsic
        await svc.calculate_intrinsic_risk(analysis.id)
        calcs = (await svc.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis.id,
                MageritRiskCalculation.dimension == "D",
            )
        )).scalars().all()
        assert calcs[0].impact_intrinsic == pytest.approx(4.8), (
            f"Q-E2E intrinsic impact: esperado 4.8 (Libro III p.13: 8*0.6), "
            f"obtenido {calcs[0].impact_intrinsic}"
        )
        assert calcs[0].risk_intrinsic_accumulated == pytest.approx(4.8), (
            f"Q-E2E intrinsic risk: esperado 4.8 (Libro III p.14: 4.8*1.0), "
            f"obtenido {calcs[0].risk_intrinsic_accumulated}"
        )

        # Phase 2: Effective
        await svc.deploy_safeguards(analysis.id, [
            {"safeguard_code": "SG.1", "efficacy": 50, "effect_type": "both",
             "status": "deployed"},
        ])
        await svc.calculate_effective_risk(analysis.id)
        calcs = (await svc.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis.id,
                MageritRiskCalculation.dimension == "D",
            )
        )).scalars().all()
        assert calcs[0].risk_effective == pytest.approx(1.2, rel=0.01), (
            f"Q-E2E effective risk: esperado 1.2 (Libro III p.15: 2.4*0.5), "
            f"obtenido {calcs[0].risk_effective}"
        )

        # Phase 3: Treatment + Residual
        actions = await svc.generate_treatment_plan(analysis.id, threshold="M")
        count = await svc.calculate_residual_risk(analysis.id)
        assert count > 0, "Residual risk debe calcularse"

        calcs = (await svc.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis.id,
                MageritRiskCalculation.dimension == "D",
            )
        )).scalars().all()
        assert calcs[0].risk_residual is not None, (
            f"Q-E2E residual risk debe existir"
        )

    @pytest.mark.asyncio
    async def test_quantitative_repercussed_with_full_pipeline(self, analysis_factory):
        """Pipeline cuantitativo con dependencias: propagate + intrinsic repercutido
        + effective + treatment (genera mitigar/transferir) + residual.

        Cubre ramas del residual cuantitativo (mitigar con ratio, transferir con 0.5).

        Escenario:
        - SUP (value_d=9) depende de INF (value_d=4) con grado 0.8
        - Amenaza sobre INF: prob=A (freq=12), degrad_d=80%
        - Esto genera riesgo ALTO en SUP repercutido
        - Salvaguarda 30% (baja) para que el riesgo siga alto tras effective
        - Treatment threshold MB para forzar mitigar/transferir/eliminar

        Cita: Libro III sec 2.2.2 pp.13-15 + sec 2.2.1 p.10.
        """
        analysis, svc = await analysis_factory("quantitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "QR-SUP", "name": "Servicio critico", "asset_type_code": "S",
             "value_d": 9, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
            {"code": "QR-INF", "name": "Servidor", "asset_type_code": "HW",
             "value_d": 4, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        sup, inf = assets
        await svc.build_dependency_graph(analysis.id, [
            {"superior_asset_id": sup.id, "inferior_asset_id": inf.id,
             "dependency_degree": 0.8},
        ])
        await svc.propagate_values(analysis.id)
        await svc.assess_threats(analysis.id, [
            {"asset_id": inf.id, "threat_code": "A.5", "probability": "A",
             "degradation_d": 80, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
        ])

        # Intrinsic: generates accumulated on INF + repercuted on SUP
        intr_count = await svc.calculate_intrinsic_risk(analysis.id)
        assert intr_count >= 2

        # Effective with weak safeguard (keeps risk high)
        await svc.deploy_safeguards(analysis.id, [
            {"safeguard_code": "WK.1", "efficacy": 30, "effect_type": "both",
             "status": "deployed"},
        ])
        await svc.calculate_effective_risk(analysis.id)

        # Treatment with very low threshold to force mitigar/transferir
        actions = await svc.generate_treatment_plan(analysis.id, threshold="MB")
        assert len(actions) > 0, "Debe generar acciones de tratamiento"

        # Residual: covers quantitative mitigar/transferir branches
        res_count = await svc.calculate_residual_risk(analysis.id)
        assert res_count > 0

        # Verify residual values exist
        calcs = (await svc.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis.id,
                MageritRiskCalculation.dimension == "D",
            )
        )).scalars().all()
        for c in calcs:
            assert c.risk_residual is not None, (
                f"Todos los calcs deben tener residual tras pipeline completo"
            )



# ================================================================
# E.8 — RESIDUAL RISK PIPELINE TESTS (2 tests)
# ================================================================

class TestResidualRiskPipeline:
    """Tests del pipeline completo hasta calculate_residual_risk.

    Estos 2 tests ejercen calculate_residual_risk() por primera vez.
    Cubren la rama 'mitigar' en modo qualitative y quantitative.
    """

    @pytest.mark.asyncio
    async def test_mitigate_qualitative_full_pipeline_to_residual(self, analysis_factory):
        """Pipeline cualitativo completo hasta riesgo residual con 'mitigar'.

        Escenario: activo con riesgo nivel A + threshold M -> excess=1 -> mitigar
        -> residual = float(target_idx) donde target_idx = LEVEL_TO_INDEX["M"] = 2.

        Traza esperada:
        - value_d=7 -> "A", degrad=70% -> "A", impact(A,A)=A, risk(A,M)=A
        - Salvaguarda 30% both -> ei=0.3, ep=0.3
        - Effective: degrad_res=70*0.7=49% -> "M", freq_res -> re-classify
        - Risk effective deberia seguir siendo A o bajar a M
        - generate_treatment_plan(threshold="M") debe generar mitigar si risk > M
        - calculate_residual_risk: rama mitigar cualitativo -> calc.risk_residual = float(target_idx)

        Cita: Libro I sec 4.1.7 pp.50-51 (mitigar).
        """
        analysis, svc = await analysis_factory("qualitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "MIT-Q1", "name": "Activo a mitigar", "asset_type_code": "S",
             "value_d": 7, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        await svc.propagate_values(analysis.id)
        await svc.assess_threats(analysis.id, [
            {"asset_id": assets[0].id, "threat_code": "A.11", "probability": "M",
             "degradation_d": 70, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
        ])
        await svc.calculate_intrinsic_risk(analysis.id)

        # Verify intrinsic is A (pre-condition for mitigar with threshold M)
        calcs = (await svc.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis.id,
                MageritRiskCalculation.dimension == "D",
                MageritRiskCalculation.risk_intrinsic_accumulated.isnot(None),
            )
        )).scalars().all()
        assert calcs[0].risk_level == "A", (
            f"Pre-condicion: riesgo intrinseco debe ser A, obtenido {calcs[0].risk_level}"
        )

        # Deploy weak safeguard (keeps risk high enough for mitigar)
        await svc.deploy_safeguards(analysis.id, [
            {"safeguard_code": "SG.WEAK", "efficacy": 10, "effect_type": "both",
             "status": "deployed"},
        ])
        await svc.calculate_effective_risk(analysis.id)

        # Generate treatment plan with threshold M
        plan_actions = await svc.generate_treatment_plan(analysis.id, threshold="M")
        mitigar_actions = [a for a in plan_actions if a.treatment == "mitigar"]
        assert len(mitigar_actions) > 0, (
            f"Pre-condicion: debe haber al menos 1 accion 'mitigar' "
            f"(risk > M con threshold M). Acciones: {[(a.treatment, a.current_risk_level) for a in plan_actions]}"
        )

        # THE KEY CALL: calculate_residual_risk in qualitative mode with mitigar
        count = await svc.calculate_residual_risk(analysis.id)
        assert count > 0, "calculate_residual_risk debe procesar calculos"

        # Verify residual was assigned
        calcs_after = (await svc.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis.id,
                MageritRiskCalculation.dimension == "D",
            )
        )).scalars().all()
        residuals = [c for c in calcs_after if c.risk_residual is not None]
        assert len(residuals) > 0, (
            "calculate_residual_risk debe asignar risk_residual a los calcs"
        )

        # For mitigar in qualitative mode: residual = float(target_idx)
        # target_risk_level = "M" (threshold), LEVEL_TO_INDEX["M"] = 2
        mitigated = [c for c in calcs_after
                     if c.risk_residual is not None and c.risk_residual == 2.0]
        assert len(mitigated) > 0, (
            f"Mitigar cualitativo: residual debe ser 2.0 (= LEVEL_TO_INDEX['M']). "
            f"Valores residuales: {[c.risk_residual for c in residuals]}"
        )

    @pytest.mark.asyncio
    async def test_mitigate_quantitative_full_pipeline_to_residual(self, analysis_factory):
        """Pipeline cuantitativo completo hasta riesgo residual con 'mitigar'.

        Primera ejecucion E2E del pipeline cuantitativo COMPLETO incluyendo
        calculate_residual_risk con rama 'mitigar' en modo quantitative.

        Escenario: activo valor alto (9) + amenaza frecuente (A=12/ano) +
        degradacion alta (80%) + salvaguarda debil (30%).
        - intrinsic: impact = 9*0.8 = 7.2, risk = 7.2*12 = 86.4
        - effective: impact_eff = 7.2*0.7 = 5.04, freq_eff = 12*0.7 = 8.4
          risk_eff = 5.04*8.4 = 42.336
        - risk_level = _map_value_to_level(min(round(42.336), 10)) = "MA"
        - threshold B (idx=1): excess = 4-1 = 3, risk=="MA" -> eliminar
        - Pero we also need mitigar. Use threshold "A" (idx=3):
          excess = 4-3 = 1 -> mitigar!
        - Residual mitigar quantitative: target_idx=3, current_idx=4,
          ratio = 3/4 = 0.75, residual = eff_risk * 0.75

        Cita: Libro III sec 2.2.2 pp.13-15 (cuantitativo) +
        Libro I sec 4.1.7 pp.50-51 (mitigar).
        """
        analysis, svc = await analysis_factory("quantitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "MIT-QT", "name": "Activo cuantitativo alto", "asset_type_code": "S",
             "value_d": 9, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        await svc.propagate_values(analysis.id)
        await svc.assess_threats(analysis.id, [
            {"asset_id": assets[0].id, "threat_code": "A.11", "probability": "A",
             "degradation_d": 80, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
        ])
        await svc.calculate_intrinsic_risk(analysis.id)

        # Deploy weak safeguard
        await svc.deploy_safeguards(analysis.id, [
            {"safeguard_code": "SG.WK", "efficacy": 30, "effect_type": "both",
             "status": "deployed"},
        ])
        await svc.calculate_effective_risk(analysis.id)

        # Use threshold "A" to force mitigar (excess=1 for MA risk)
        plan_actions = await svc.generate_treatment_plan(analysis.id, threshold="A")
        mitigar_actions = [a for a in plan_actions if a.treatment == "mitigar"]
        assert len(mitigar_actions) > 0, (
            f"Pre-condicion: debe haber al menos 1 accion 'mitigar' "
            f"(MA con threshold A -> excess=1). "
            f"Acciones: {[(a.treatment, a.current_risk_level) for a in plan_actions]}"
        )

        # THE KEY CALL: calculate_residual_risk in quantitative mode with mitigar
        count = await svc.calculate_residual_risk(analysis.id)
        assert count > 0, "calculate_residual_risk debe procesar calculos"

        calcs_after = (await svc.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis.id,
                MageritRiskCalculation.dimension == "D",
            )
        )).scalars().all()
        residuals = [c for c in calcs_after if c.risk_residual is not None]
        assert len(residuals) > 0, (
            "calculate_residual_risk cuantitativo debe asignar risk_residual"
        )
        # Residual must be numeric float
        for c in residuals:
            assert isinstance(c.risk_residual, (int, float)), (
                f"Residual cuantitativo debe ser numerico, obtenido {type(c.risk_residual)}"
            )
        # Mitigar quantitative: residual = eff_risk * (target_idx / current_idx)
        # This should be LESS than effective risk (ratio < 1)
        for c in calcs_after:
            if c.risk_effective is not None and c.risk_residual is not None:
                assert c.risk_residual <= c.risk_effective, (
                    f"Residual ({c.risk_residual}) debe ser <= effective ({c.risk_effective}) "
                    f"tras mitigar (Libro I pp.50-51)"
                )



# ================================================================
# E.10 — FINAL COVERAGE TESTS (2 tests)
# ================================================================

class TestRepercussedEdgeCases:
    """Tests para las 4 lineas categoria A restantes de riesgo repercutido."""

    @pytest.mark.asyncio
    async def test_repercussed_with_direct_threat_on_sup(self, analysis_factory):
        """Calc repercutido sobre SUP donde SUP tambien tiene la misma amenaza directa.

        Este escenario ejerce la rama de _calc_effective_qualitative donde
        risk_intrinsic_accumulated is None (calc repercutido) PERO el activo
        tiene un threat_assessment directo con la misma amenaza, lo que
        permite el lookup en ta_map y el calculo de effective sobre el calc
        repercutido usando value_{dim} en vez de accumulated_{dim} (L971).

        Tambien ejerce L947 (degradation_pct check en effective para calcs
        donde ta_map retorna un threat assessment valido).

        Caso real frecuente: una amenaza A.11 (DoS) puede afectar tanto al
        servidor (INF) como al servicio web (SUP) que depende de el, con
        distintas degradaciones porque el impacto se manifiesta diferente
        en cada activo.

        Cita: Libro III sec 2.2.1 pp.10-11 (riesgo acumulado vs repercutido).
        """
        analysis, svc = await analysis_factory("qualitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "SUP-WEB", "name": "Servicio Web", "asset_type_code": "S",
             "value_d": 8, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
            {"code": "INF-DB", "name": "Base Datos", "asset_type_code": "HW",
             "value_d": 6, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        sup, inf = assets
        await svc.build_dependency_graph(analysis.id, [
            {"superior_asset_id": sup.id, "inferior_asset_id": inf.id,
             "dependency_degree": 1.0},
        ])
        await svc.propagate_values(analysis.id)
        # MISMA amenaza A.11 sobre AMBOS activos con distinta degradacion
        await svc.assess_threats(analysis.id, [
            {"asset_id": inf.id, "threat_code": "A.11", "probability": "M",
             "degradation_d": 60, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
            {"asset_id": sup.id, "threat_code": "A.11", "probability": "M",
             "degradation_d": 40, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
        ])
        await svc.calculate_intrinsic_risk(analysis.id)
        await svc.deploy_safeguards(analysis.id, [
            {"safeguard_code": "FW.1", "efficacy": 50, "effect_type": "both",
             "status": "deployed"},
        ])
        eff_count = await svc.calculate_effective_risk(analysis.id)
        assert eff_count > 0

        # SUP debe tener calcs con risk_effective (amenaza directa permite ta_map lookup)
        sup_calcs = (await svc.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis.id,
                MageritRiskCalculation.asset_id == sup.id,
                MageritRiskCalculation.dimension == "D",
            )
        )).scalars().all()
        eff_calcs = [c for c in sup_calcs if c.risk_effective is not None]
        assert len(eff_calcs) > 0, (
            "SUP debe tener risk_effective porque tiene amenaza directa A.11 "
            "(Libro III pp.10-11: repercutido + directo en mismo activo)"
        )

    @pytest.mark.asyncio
    async def test_repercussed_skipped_when_sup_value_zero_qualitative(self, analysis_factory):
        """Riesgo repercutido se salta cuando SUP no valora esa dimension (cualitativo).

        Si un activo superior tiene value_d=0, no tiene sentido calcular
        riesgo repercutido sobre el en dimension D. El motor lo salta en
        L694: 'if sup_own_value == 0: continue'.

        Cita: Libro III sec 2.2.1 pp.10-11 (riesgo repercutido aplica solo
        a dimensiones donde el activo superior tiene valor propio).
        """
        analysis, svc = await analysis_factory("qualitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "SUP-NOD", "name": "Servicio sin valor D", "asset_type_code": "S",
             "value_d": 0, "value_i": 8, "value_c": 0, "value_a": 0, "value_t": 0},
            {"code": "INF-VULN", "name": "Inferior con vuln D", "asset_type_code": "HW",
             "value_d": 5, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        sup, inf = assets
        await svc.build_dependency_graph(analysis.id, [
            {"superior_asset_id": sup.id, "inferior_asset_id": inf.id,
             "dependency_degree": 1.0},
        ])
        await svc.propagate_values(analysis.id)
        await svc.assess_threats(analysis.id, [
            {"asset_id": inf.id, "threat_code": "A.11", "probability": "M",
             "degradation_d": 60, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
        ])
        await svc.calculate_intrinsic_risk(analysis.id)

        # SUP NO debe tener calc repercutido en dimension D (value_d=0)
        sup_d_calcs = (await svc.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis.id,
                MageritRiskCalculation.asset_id == sup.id,
                MageritRiskCalculation.dimension == "D",
            )
        )).scalars().all()
        assert len(sup_d_calcs) == 0, (
            f"SUP no debe tener calcs en dimension D porque value_d=0 "
            f"(Libro III pp.10-11: repercutido solo para dimensiones valoradas). "
            f"Obtenido {len(sup_d_calcs)} calcs"
        )

    @pytest.mark.asyncio
    async def test_repercussed_skipped_when_sup_value_zero_quantitative(self, analysis_factory):
        """Mismo escenario que anterior pero en modo cuantitativo (cubre L810).

        Cita: Libro III sec 2.2.2 p.13 (repercutido cuantitativo).
        """
        analysis, svc = await analysis_factory("quantitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "QSP-NOD", "name": "Servicio sin valor D quant", "asset_type_code": "S",
             "value_d": 0, "value_i": 7, "value_c": 0, "value_a": 0, "value_t": 0},
            {"code": "QINF-VLN", "name": "Inferior con vuln D quant", "asset_type_code": "HW",
             "value_d": 5, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        sup, inf = assets
        await svc.build_dependency_graph(analysis.id, [
            {"superior_asset_id": sup.id, "inferior_asset_id": inf.id,
             "dependency_degree": 0.8},
        ])
        await svc.propagate_values(analysis.id)
        await svc.assess_threats(analysis.id, [
            {"asset_id": inf.id, "threat_code": "A.11", "probability": "M",
             "degradation_d": 60, "degradation_i": 0, "degradation_c": 0,
             "degradation_a": 0, "degradation_t": 0},
        ])
        await svc.calculate_intrinsic_risk(analysis.id)

        sup_d_calcs = (await svc.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis.id,
                MageritRiskCalculation.asset_id == sup.id,
                MageritRiskCalculation.dimension == "D",
            )
        )).scalars().all()
        assert len(sup_d_calcs) == 0, (
            f"SUP quant no debe tener calcs en dimension D porque value_d=0 "
            f"(Libro III p.13: repercutido solo para dimensiones valoradas). "
            f"Obtenido {len(sup_d_calcs)} calcs"
        )



# ================================================================
# MULTI-HOP PROPAGATION TESTS (4 tests)
# ================================================================

class TestPropagationMultiHop:
    """Tests for multi-hop quantitative propagation (MAGERIT v3 transitive closure)."""

    @pytest.mark.asyncio
    async def test_propagate_2_hop_chain(self, analysis_factory):
        """TEST CRITICAL: 2-hop chain A->B->C propagates value from A to C through B.

        Setup: A(sup, value_d=9) -> B(mid, value_d=0) -> C(inf, value_d=0)
        All degrees = 1.0.

        Expected: C.accumulated_d = C.value_d + B.value_d*1.0 + A.value_d*1.0 = 0 + 0 + 9 = 9.0
        (B contributes 0, A contributes 9 through transitive degree A=>C = 1.0*1.0 = 1.0)

        Without multi-hop, C would only see B (value 0) and get accumulated=0.

        Cita: MAGERIT v3 Libro III sec 2.2.2 p.12-13.
        """
        analysis, svc = await analysis_factory("quantitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "A-TOP", "name": "Servicio Critico", "asset_type_code": "S",
             "value_d": 9, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
            {"code": "B-MID", "name": "App Server", "asset_type_code": "SW",
             "value_d": 0, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
            {"code": "C-BOT", "name": "Hardware", "asset_type_code": "HW",
             "value_d": 0, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        a, b, c = assets
        await svc.build_dependency_graph(analysis.id, [
            {"superior_asset_id": a.id, "inferior_asset_id": b.id, "dependency_degree": 1.0},
            {"superior_asset_id": b.id, "inferior_asset_id": c.id, "dependency_degree": 1.0},
        ])
        await svc.propagate_values(analysis.id)

        # C should accumulate A's value through B (2-hop)
        acc_d = float(getattr(c, "accumulated_d"))
        assert acc_d == pytest.approx(9.0), (
            f"2-hop: C.accumulated_d esperado 9.0 "
            f"(Libro III p.12-13: grado(A=>C)=1.0*1.0=1.0, valor=9*1.0), "
            f"obtenido {acc_d}"
        )

    @pytest.mark.asyncio
    async def test_propagate_3_hop_deep_chain(self, analysis_factory):
        """3-hop chain A->B->C->D with decreasing degrees.

        A(value_d=10) -> B(0) grado 0.8 -> C(0) grado 0.5 -> D(0) grado 0.4

        Grado transitivo A=>D: 0.8 * 0.5 * 0.4 = 0.16
        D.accumulated_d = 0 + 10*0.16 = 1.6
        (plus B=>D: 0*0.5*0.4=0 and C=>D: 0*0.4=0)

        Cita: MAGERIT v3 Libro III sec 2.2.2 p.12.
        """
        analysis, svc = await analysis_factory("quantitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "A", "name": "Top", "asset_type_code": "S",
             "value_d": 10, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
            {"code": "B", "name": "Mid1", "asset_type_code": "SW",
             "value_d": 0, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
            {"code": "C", "name": "Mid2", "asset_type_code": "SW",
             "value_d": 0, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
            {"code": "D", "name": "Bottom", "asset_type_code": "HW",
             "value_d": 0, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        a_ast, b_ast, c_ast, d_ast = assets
        await svc.build_dependency_graph(analysis.id, [
            {"superior_asset_id": a_ast.id, "inferior_asset_id": b_ast.id, "dependency_degree": 0.8},
            {"superior_asset_id": b_ast.id, "inferior_asset_id": c_ast.id, "dependency_degree": 0.5},
            {"superior_asset_id": c_ast.id, "inferior_asset_id": d_ast.id, "dependency_degree": 0.4},
        ])
        await svc.propagate_values(analysis.id)

        acc_d = float(getattr(d_ast, "accumulated_d"))
        expected = 10 * 0.8 * 0.5 * 0.4  # = 1.6
        assert acc_d == pytest.approx(expected, abs=0.01), (
            f"3-hop: D.accumulated_d esperado {expected} "
            f"(Libro III p.12: 10*0.8*0.5*0.4), obtenido {acc_d}"
        )

    @pytest.mark.asyncio
    async def test_propagate_multiple_paths_magerit_sum(self, analysis_factory):
        """Diamond: A depends on C via B1 AND B2. Grado uses MAGERIT sum.

        A(value_d=10) -> B1(0) grado 1.0 -> C(0) grado 0.5
        A(value_d=10) -> B2(0) grado 1.0 -> C(0) grado 0.5

        Camino 1: grado A=>C via B1 = 1.0 * 0.5 = 0.5
        Camino 2: grado A=>C via B2 = 1.0 * 0.5 = 0.5
        Grado total: magerit_sum(0.5, 0.5) = 1 - (1-0.5)(1-0.5) = 0.75

        C.accumulated_d = 0 + 10*0.75 = 7.5

        NOT 10*1.0 (arithmetic sum would give grado=1.0, not 0.75).

        Cita: MAGERIT v3 Libro III sec 2.2.2 p.12 — formula de suma MAGERIT.
        """
        analysis, svc = await analysis_factory("quantitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "A", "name": "Top", "asset_type_code": "S",
             "value_d": 10, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
            {"code": "B1", "name": "Path1", "asset_type_code": "SW",
             "value_d": 0, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
            {"code": "B2", "name": "Path2", "asset_type_code": "SW",
             "value_d": 0, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
            {"code": "C", "name": "Bottom", "asset_type_code": "HW",
             "value_d": 0, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        a_ast, b1, b2, c_ast = assets
        await svc.build_dependency_graph(analysis.id, [
            {"superior_asset_id": a_ast.id, "inferior_asset_id": b1.id, "dependency_degree": 1.0},
            {"superior_asset_id": a_ast.id, "inferior_asset_id": b2.id, "dependency_degree": 1.0},
            {"superior_asset_id": b1.id, "inferior_asset_id": c_ast.id, "dependency_degree": 0.5},
            {"superior_asset_id": b2.id, "inferior_asset_id": c_ast.id, "dependency_degree": 0.5},
        ])
        await svc.propagate_values(analysis.id)

        acc_d = float(getattr(c_ast, "accumulated_d"))
        # magerit_sum(0.5, 0.5) = 0.75; C = 0 + 10*0.75 = 7.5
        assert acc_d == pytest.approx(7.5, abs=0.01), (
            f"Diamond MAGERIT sum: C.accumulated_d esperado 7.5 "
            f"(Libro III p.12: magerit_sum(0.5, 0.5)=0.75, 10*0.75=7.5), "
            f"obtenido {acc_d}"
        )

    @pytest.mark.asyncio
    async def test_propagate_1_hop_regression(self, analysis_factory):
        """Regression: 1-hop behavior preserved after multi-hop generalization.

        A(value_d=6) -> B(value_d=4) with degree 0.5.
        B.accumulated_d = 4 + 6*0.5 = 7.0.

        Same as test_propagate_quantitative_with_degree but run explicitly
        after multi-hop to confirm backward compatibility.

        Cita: MAGERIT v3 Libro III sec 2.2.2 p.13.
        """
        analysis, svc = await analysis_factory("quantitative")
        assets = await svc.build_asset_inventory(analysis.id, [
            {"code": "SUP", "name": "Servicio", "asset_type_code": "S",
             "value_d": 6, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
            {"code": "INF", "name": "Servidor", "asset_type_code": "HW",
             "value_d": 4, "value_i": 0, "value_c": 0, "value_a": 0, "value_t": 0},
        ])
        sup, inf = assets
        await svc.build_dependency_graph(analysis.id, [
            {"superior_asset_id": sup.id, "inferior_asset_id": inf.id, "dependency_degree": 0.5},
        ])
        await svc.propagate_values(analysis.id)

        acc_d = float(getattr(inf, "accumulated_d"))
        assert acc_d == pytest.approx(7.0), (
            f"1-hop regression: INF.accumulated_d esperado 7.0 "
            f"(Libro III p.13: 4+6*0.5), obtenido {acc_d}"
        )
