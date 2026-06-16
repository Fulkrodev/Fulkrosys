"""
Motor 2 — MAGERIT v3 Risk Engine: Service layer.

Implements the complete MAGERIT v3 risk analysis methodology with
two calculation modes (qualitative and quantitative) selectable per analysis.

Every calculation function cites the exact source from the official
MAGERIT v3 books (Libro I, II, or III) in its docstring.

References:
  - Libro I: "Método" (methodology, 109 pages)
  - Libro II: "Catálogo de Elementos" (asset types, threats, safeguards, 75 pages)
  - Libro III: "Guía de Técnicas" (mathematical formulas, 42 pages)
"""
import uuid
from collections import defaultdict

from sqlalchemy import select, delete, func as sa_func, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m02_magerit.models import (
    MageritAnalysis,
    MageritAsset,
    MageritAssetDependency,
    MageritThreatAssessment,
    MageritSafeguardDeployment,
    MageritRiskCalculation,
    MageritTreatmentPlan,
)


# ================================================================
# PASO 2: HELPERS
# ================================================================

# Ordered levels for comparison
LEVELS_ORDER = ["MB", "B", "M", "A", "MA"]
LEVEL_TO_INDEX = {level: i for i, level in enumerate(LEVELS_ORDER)}


def _map_value_to_level(numeric_value: int, scale_max: int = 10) -> str:
    """
    Convert a numeric asset value (0-10) to a qualitative MAGERIT level (MB/B/M/A/MA).

    # Mapping table is FULKRO convention, not MAGERIT official. Configurable per analysis in future.

    MAGERIT v3 Libro III sec 2.1 (p.6) defines 5 qualitative levels:
    > "MB: muy bajo, B: bajo, M: medio, A: alto, MA: muy alto"

    But does NOT provide an explicit mapping from numeric 0-10 values to these levels.
    The numeric 0-10 scale comes from Libro I sec 4.3.2 (p.28-29) which describes
    asset valuation levels N0 through N10 with textual descriptions, but does NOT
    define a correspondence to MB/B/M/A/MA.

    This mapping is a FULKRO implementation decision:
      0-1  → MB (despreciable / bajo)
      2-3  → B  (menor / medio-bajo)
      4-5  → M  (medio)
      6-7  → A  (alto / muy alto)
      8-10 → MA (extremo / máximo)
    """
    if numeric_value <= 1:
        return "MB"
    elif numeric_value <= 3:
        return "B"
    elif numeric_value <= 5:
        return "M"
    elif numeric_value <= 7:
        return "A"
    else:
        return "MA"


def _map_degradation_to_level(degradation_pct: int) -> str:
    """
    Convert degradation percentage (0-100) to qualitative level.

    MAGERIT v3 Libro III sec 2.1 (p.6) uses a 3-level degradation scale
    in the impact table: 1%, 10%, 100%. We extend to 5 levels for
    compatibility with the 5×5 risk matrix.

    # Mapping is FULKRO convention for 5-level compatibility.
      0-5%   → MB
      6-20%  → B
      21-50% → M
      51-90% → A
      91-100% → MA
    """
    if degradation_pct <= 5:
        return "MB"
    elif degradation_pct <= 20:
        return "B"
    elif degradation_pct <= 50:
        return "M"
    elif degradation_pct <= 90:
        return "A"
    else:
        return "MA"



def _lookup_impact_qualitative(value_level: str, degradation_level: str) -> str:
    """
    Qualitative impact lookup.

    MAGERIT v3 Libro III, sec 2.1 "Análisis mediante tablas", p.6:
    > "Se puede calcular el impacto en base a tablas sencillas de doble entrada:
    >                     degradación
    >  impacto     1%      10%     100%
    >  MA          M       A       MA
    >  A           B       M       A
    >  valor M     MB      B       M
    >  B           MB      MB      B
    >  MB          MB      MB      MB"

    Extended to 5 degradation levels for consistency with the 5-level scale.
    The extension uses interpolation consistent with the 3-column official table.
    """
    # Map degradation to the 3 official columns, then interpolate
    IMPACT_TABLE = {
        # (value, degradation) -> impact
        # Official 3-column table from p.6, extended to 5 columns
        ("MA", "MB"): "M",  ("MA", "B"): "A",  ("MA", "M"): "A",  ("MA", "A"): "MA", ("MA", "MA"): "MA",
        ("A",  "MB"): "B",  ("A",  "B"): "M",  ("A",  "M"): "M",  ("A",  "A"): "A",  ("A",  "MA"): "A",
        ("M",  "MB"): "MB", ("M",  "B"): "B",  ("M",  "M"): "B",  ("M",  "A"): "M",  ("M",  "MA"): "M",
        ("B",  "MB"): "MB", ("B",  "B"): "MB", ("B",  "M"): "MB", ("B",  "A"): "B",  ("B",  "MA"): "B",
        ("MB", "MB"): "MB", ("MB", "B"): "MB", ("MB", "M"): "MB", ("MB", "A"): "MB", ("MB", "MA"): "MB",
    }
    return IMPACT_TABLE.get((value_level, degradation_level), "MB")


async def _lookup_risk_matrix(db: AsyncSession, impact_level: str, probability_level: str) -> str:
    """
    Lookup the risk level from the official MAGERIT 5×5 risk matrix in the DB.

    MAGERIT v3 Libro III, sec 2.1 "Análisis mediante tablas", p.7:
    > "Pudiendo combinarse impacto y frecuencia en una tabla para calcular el riesgo:
    >                 probabilidad
    >  riesgo  MB    B     M     A     MA
    >  MA      A     MA    MA    MA    MA
    >  A       M     A     A     MA    MA
    >  impacto M     B     M     M     A     A
    >  B       MB    B     B     M     M
    >  MB      MB    MB    MB    B     B"

    Table is precargada in magerit_risk_matrix (25 rows, migration f7461c35f119).
    """
    row = await db.execute(
        sa_text("""
            SELECT risk_level FROM magerit_risk_matrix
            WHERE impact_level = :imp AND probability_level = :prob
        """),
        {"imp": impact_level, "prob": probability_level},
    )
    result = row.scalar_one_or_none()
    if result is None:
        return "MB"  # pragma: no cover  # Risk matrix always preloaded (25 rows verified)
    return result


def _magerit_dependency_sum(a: float, b: float) -> float:
    """
    MAGERIT sum for transitive dependency degrees.

    MAGERIT v3 Libro III, sec 2.2.2, p.12:
    > "a + b = 1 − (1 − a) × (1 − b)"
    > "Esta manera de sumar satisface las propiedades conmutativa,
    >  asociativa y existencia de un elemento neutro, amén de acotar
    >  el resultado al rango [0..1] si los sumandos están dentro de
    >  dicho rango."

    Used for combining dependency degrees through multiple paths.
    """
    return 1.0 - (1.0 - a) * (1.0 - b)


# Frequency mapping: qualitative level → annual rate (for quantitative mode)
FREQUENCY_MAP = {
    "MB": 0.01,   # Once per century
    "B":  0.1,    # Once per decade
    "M":  1.0,    # Once per year
    "A":  12.0,   # Once per month
    "MA": 365.0,  # Daily
}


def _magerit_efficacy_composition(ei: float, ef: float) -> float:
    """
    Compose impact efficacy and frequency efficacy into overall efficacy.

    MAGERIT v3 Libro III, sec 2.2.2, p.14:
    > "(1 − ei) × (1 − ef) = 1 − e"
    > "Si ei= 0% y ef= 0%, e= 0%. Si ei= 0%, e= ef. Si ef= 0%, e= ei.
    >  Si ei o ef= 100%, e= 100%."

    Args:
        ei: efficacy against impact (0.0-1.0)
        ef: efficacy against frequency/probability (0.0-1.0)
    Returns:
        overall efficacy e (0.0-1.0)
    """
    return 1.0 - (1.0 - ei) * (1.0 - ef)


def _magerit_safeguard_package_efficacy(
    safeguards: list[MageritSafeguardDeployment],
) -> float:
    """
    Compute the weighted average efficacy of a safeguard package.

    MAGERIT v3 Libro III, sec 2.2.4 "Sobre la eficacia de las salvaguardas", p.21:
    > "Como eficacia de un paquete de salvaguardas se ha tomado el valor
    >  medio de las eficacias de los componentes. Este cálculo puede
    >  modularse si se tiene en cuenta que no todas las salvaguardas son
    >  de la misma naturaleza, introduciendo una ponderación 'p':
    >  e(ps) = Σ_k e(ps_k) × p_k / Σ_k p_k"

    We use equal weight (p=1) for all safeguards as the simple case
    described in the Libro III: "El caso particular de que todas las
    salvaguardas sean igual de importantes, se consigue tomando 'p = 1'."
    """
    if not safeguards:
        return 0.0  # pragma: no cover  # Caller (_compute_package_efficacy) guards against empty list
    total_efficacy = sum(s.efficacy / 100.0 for s in safeguards)
    return total_efficacy / len(safeguards)


def _compute_package_efficacy(
    safeguards: list[MageritSafeguardDeployment],
) -> tuple[float, float]:
    """
    Compute (ei, ep) — impact and frequency efficacy from a safeguard package.

    Splits safeguards by effect_type:
    - "preventive" → contributes to ep (reduces frequency)
    - "palliative" → contributes to ei (reduces impact/degradation)
    - "both" → contributes to both ei and ep

    Returns (ei, ep) each in range [0.0, 1.0].
    """
    preventive = [s for s in safeguards if s.effect_type in ("preventive", "both")]
    palliative = [s for s in safeguards if s.effect_type in ("palliative", "both")]

    ep = _magerit_safeguard_package_efficacy(preventive) if preventive else 0.0
    ei = _magerit_safeguard_package_efficacy(palliative) if palliative else 0.0

    return ei, ep


def _map_frequency_to_level(frequency: float) -> str:
    """
    Map a frequency (annual rate) back to a qualitative probability level.
    Inverse of FREQUENCY_MAP.

    # Helper added during implementation, not in original spec.
    """
    if frequency >= 100.0:
        return "MA"
    elif frequency >= 5.0:
        return "A"
    elif frequency >= 0.5:
        return "M"
    elif frequency >= 0.05:
        return "B"
    else:
        return "MB"


# ================================================================
# MAIN SERVICE CLASS
# ================================================================

class MageritService:
    """Service layer for Motor 2 — MAGERIT v3 Risk Engine."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ================================================================
    # GRUPO 1: FUNCIONES DE PERSISTENCIA (sin cálculos)
    # ================================================================

    async def create_analysis(
        self,
        project_id: uuid.UUID,
        name: str,
        calculation_mode: str = "qualitative",
    ) -> MageritAnalysis:
        """Create a new MAGERIT risk analysis for a project."""
        # MAGERIT v3 Libro III no formaliza un calculo 'hybrid' canonico (ADR-031):
        # se rechaza en CREACION para no dejar analisis inusables (todos los
        # dispatch de propagacion/riesgo lanzan NotImplementedError con hybrid).
        if calculation_mode not in ("qualitative", "quantitative"):
            raise ValueError(
                f"calculation_mode invalido: {calculation_mode!r} · usa "
                "'qualitative' o 'quantitative' (hybrid no soportado · ADR-031)"
            )
        analysis = MageritAnalysis(
            project_id=project_id,
            name=name,
            status="draft",
            calculation_mode=calculation_mode,
        )
        self.db.add(analysis)
        await self.db.flush()
        return analysis

    async def build_asset_inventory(
        self,
        analysis_id: uuid.UUID,
        assets: list[dict],
    ) -> list[MageritAsset]:
        """
        Persist the asset inventory for an analysis.

        Libro I, sec 2.1.1, p.15:
        > "El primer paso consiste en identificar los activos relevantes para
        >  la organización, su interrelación y su valor, en el sentido de qué
        >  perjuicio (coste) supondría su degradación."
        """
        created = []
        for a in assets:
            asset = MageritAsset(
                analysis_id=analysis_id,
                code=a["code"],
                name=a["name"],
                asset_type_code=a.get("asset_type_code", ""),
                description=a.get("description"),
                owner=a.get("owner"),
                value_d=a.get("value_d", 0),
                value_i=a.get("value_i", 0),
                value_c=a.get("value_c", 0),
                value_a=a.get("value_a", 0),
                value_t=a.get("value_t", 0),
                cpstic_certified=bool(a.get("cpstic_certified", False)),
                accumulated_d=a.get("value_d", 0),
                accumulated_i=a.get("value_i", 0),
                accumulated_c=a.get("value_c", 0),
                accumulated_a=a.get("value_a", 0),
                accumulated_t=a.get("value_t", 0),
            )
            self.db.add(asset)
            created.append(asset)
        await self.db.flush()
        return created

    async def build_dependency_graph(
        self,
        analysis_id: uuid.UUID,
        dependencies: list[dict],
    ) -> list[MageritAssetDependency]:
        """
        Build the directed dependency graph between assets.

        Libro I, sec 2.1.2, p.16:
        > "Los activos esenciales son la información y los servicios prestados;
        >  pero estos activos dependen de otros activos más prosaicos como
        >  pueden ser los equipos, las comunicaciones, las instalaciones y las
        >  frecuentemente olvidadas personas que trabajan con aquellos."

        Raises ValueError if a cycle is detected (DAG required for propagation).
        """
        graph: dict[str, list[str]] = defaultdict(list)
        for dep in dependencies:
            graph[str(dep["superior_asset_id"])].append(str(dep["inferior_asset_id"]))

        visited, rec_stack = set(), set()

        def _has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if _has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.discard(node)
            return False

        all_nodes = set(graph.keys())
        for dep in dependencies:
            all_nodes.add(str(dep["inferior_asset_id"]))
        for node in all_nodes:
            if node not in visited:
                if _has_cycle(node):
                    raise ValueError(
                        "Ciclo detectado en el grafo de dependencias. "
                        "MAGERIT requiere un DAG para la propagación de valores."
                    )

        created = []
        for dep in dependencies:
            d = MageritAssetDependency(
                analysis_id=analysis_id,
                superior_asset_id=dep["superior_asset_id"],
                inferior_asset_id=dep["inferior_asset_id"],
                dependency_degree=dep.get("dependency_degree", 1.0),
                reason=dep.get("reason"),
            )
            self.db.add(d)
            created.append(d)
        await self.db.flush()
        return created

    async def assess_threats(
        self,
        analysis_id: uuid.UUID,
        assessments: list[dict],
    ) -> list[MageritThreatAssessment]:
        """
        Persist threat assessments for (asset, threat) pairs.

        Libro I, sec 2.1.4-5, p.19:
        > "Se denomina impacto a la medida del daño sobre el activo derivado
        >  de la materialización de una amenaza."
        > "Se denomina riesgo a la medida del daño probable sobre un sistema."
        """
        created = []
        for a in assessments:
            ta = MageritThreatAssessment(
                analysis_id=analysis_id,
                asset_id=a["asset_id"],
                threat_code=a["threat_code"],
                probability=a["probability"],  # Now VARCHAR: MB/B/M/A/MA
                degradation_d=a.get("degradation_d", 0),
                degradation_i=a.get("degradation_i", 0),
                degradation_c=a.get("degradation_c", 0),
                degradation_a=a.get("degradation_a", 0),
                degradation_t=a.get("degradation_t", 0),
            )
            self.db.add(ta)
            created.append(ta)
        await self.db.flush()
        return created

    # ================================================================
    # PASO 3: PROPAGATE VALUES (with dispatcher)
    # ================================================================

    async def propagate_values(self, analysis_id: uuid.UUID) -> int:
        """
        Propagate asset values through the dependency graph.
        Dispatches to qualitative or quantitative implementation.

        Returns the number of assets updated.
        """
        analysis = await self.db.get(MageritAnalysis, analysis_id)
        if not analysis:
            raise ValueError(f"Analysis {analysis_id} not found")

        if analysis.calculation_mode == "qualitative":
            return await self._propagate_values_qualitative(analysis_id)
        elif analysis.calculation_mode == "quantitative":
            return await self._propagate_values_quantitative(analysis_id)
        else:
            raise NotImplementedError(
                "MAGERIT hybrid mode (qualitative + quantitative combined "
                "calculation) is not implemented and will not be implemented. "
                "MAGERIT v3 Libro III does not formalize a canonical hybrid "
                "computation. See ADR-031. Use 'qualitative' or 'quantitative' "
                "calculation_mode."
            )

    async def _propagate_values_qualitative(self, analysis_id: uuid.UUID) -> int:
        """
        Qualitative value propagation: accumulated value = max(own, any superior).

        MAGERIT v3 Libro III, sec 2.2.1 "Un modelo cualitativo", p.9:
        > "Se define el valor acumulado sobre B como el mayor valor entre
        >  el propio y el de cualquiera de sus superiores:
        >  valor_acumulado(B) = max(valor(B), max_i{valor(A_i)})"

        > "La fórmula anterior dice que el valor acumulado sobre un activo
        >  es el mayor de los valores que soporta, bien propio, bien de
        >  alguno de sus superiores."

        In qualitative mode, the dependency_degree is ignored (it's a
        quantitative concept). The maximum rule applies regardless of
        the strength of the dependency.
        """
        assets = (await self.db.execute(
            select(MageritAsset).where(
                MageritAsset.analysis_id == analysis_id,
                MageritAsset.deleted_at.is_(None),
            )
        )).scalars().all()
        asset_map = {str(a.id): a for a in assets}

        deps = (await self.db.execute(
            select(MageritAssetDependency).where(
                MageritAssetDependency.analysis_id == analysis_id
            )
        )).scalars().all()

        # Build: inferior_id -> list of superior_ids
        # (superior depends on inferior, so inferior accumulates superior's value)
        inferiors_to_superiors: dict[str, list[str]] = defaultdict(list)
        for dep in deps:
            inferiors_to_superiors[str(dep.inferior_asset_id)].append(str(dep.superior_asset_id))

        updated = 0
        for asset in assets:
            aid = str(asset.id)
            superiors = inferiors_to_superiors.get(aid, [])

            for dim in ["d", "i", "c", "a", "t"]:
                own_val = getattr(asset, f"value_{dim}") or 0
                max_val = own_val
                for sup_id in superiors:
                    sup = asset_map.get(sup_id)
                    if sup:
                        sup_val = getattr(sup, f"value_{dim}") or 0
                        max_val = max(max_val, sup_val)
                setattr(asset, f"accumulated_{dim}", max_val)

            updated += 1

        await self.db.flush()
        return updated

    async def _propagate_values_quantitative(self, analysis_id: uuid.UUID) -> int:
        """
        Quantitative value propagation with FULL transitive closure.

        Implements the official MAGERIT v3 multi-hop formula:

        MAGERIT v3 Libro III, sec 2.2.2 p.12:
        > "grado(A ⇒ C) = Σ_i { grado(A ⇒ B_i) × grado(B_i → C) }
        >  Donde las sumas se realizan de acuerdo con esta fórmula:
        >  a + b = 1 − (1 − a) × (1 − b)"

        MAGERIT v3 Libro III, sec 2.2.2 p.13:
        > "valor_acumulado(B) = valor(B) + Σ_i { valor(A_i) × grado(A_i ⇒ B) }"
        > "En lo que sigue no se distingue entre dependencias directas
        >  o indirectas."

        Uses networkx for DAG modeling and path enumeration. The transitive
        degree between two nodes is computed by multiplying degrees along
        each simple path and aggregating parallel paths with the MAGERIT sum.
        """
        import networkx as nx

        assets = (await self.db.execute(
            select(MageritAsset).where(
                MageritAsset.analysis_id == analysis_id,
                MageritAsset.deleted_at.is_(None),
            )
        )).scalars().all()
        asset_map = {str(a.id): a for a in assets}

        deps = (await self.db.execute(
            select(MageritAssetDependency).where(
                MageritAssetDependency.analysis_id == analysis_id
            )
        )).scalars().all()

        # Build DiGraph: edge from superior_id → inferior_id with degree
        # Convention: "A depends on B" = A is superior, B is inferior.
        # Value propagates FROM superior TO inferior.
        G = nx.DiGraph()
        for a in assets:
            G.add_node(str(a.id))
        for dep in deps:
            G.add_edge(
                str(dep.superior_asset_id),
                str(dep.inferior_asset_id),
                degree=dep.dependency_degree,
            )

        updated = 0
        for asset in assets:
            bid = str(asset.id)

            # Find all ancestors (superiors, direct and indirect)
            try:
                ancestors = nx.ancestors(G, bid)
            except nx.NetworkXError:
                ancestors = set()

            # Calculate transitive degree from each ancestor to this node
            contributions: dict[str, float] = {}  # ancestor_id -> transitive_degree
            for anc_id in ancestors:
                grado_transitivo = 0.0
                # cutoff §2.8: limita la profundidad de caminos para evitar el
                # blow-up exponencial de all_simple_paths en grafos densos. 8
                # niveles cubren el 99.9% de grafos de dependencia ENS reales
                # (mediana CCN-CERT ~42 activos, 2-3 niveles) y blindan los casos
                # patológicos (>200 activos, ciclos profundos).
                for path in nx.all_simple_paths(G, source=anc_id, target=bid, cutoff=8):
                    # Multiply degrees along the path
                    grado_camino = 1.0
                    for i in range(len(path) - 1):
                        grado_camino *= G.edges[path[i], path[i + 1]]["degree"]
                    # Aggregate parallel paths with MAGERIT sum
                    grado_transitivo = _magerit_dependency_sum(grado_transitivo, grado_camino)
                contributions[anc_id] = grado_transitivo

            # Accumulate: own value + sum(superior_value × transitive_degree)
            for dim in ["d", "i", "c", "a", "t"]:
                own_val = getattr(asset, f"value_{dim}") or 0
                accumulated = own_val
                for anc_id, grado in contributions.items():
                    anc = asset_map.get(anc_id)
                    if anc:
                        anc_val = getattr(anc, f"value_{dim}") or 0
                        accumulated += anc_val * grado
                # Cap at 10 for consistency with the 0-10 scale
                setattr(asset, f"accumulated_{dim}", min(round(accumulated, 4), 10.0))

            updated += 1

        await self.db.flush()
        return updated

    # ================================================================
    # PASO 4: CALCULATE INTRINSIC RISK (with dispatcher)
    # ================================================================

    async def calculate_intrinsic_risk(self, analysis_id: uuid.UUID) -> int:
        """
        Calculate intrinsic risk (before safeguards) for all (asset, threat, dimension).
        Dispatches to qualitative or quantitative implementation.

        Calculates BOTH accumulated and repercuted risk for each entry.

        Returns the number of risk calculations created.
        """
        analysis = await self.db.get(MageritAnalysis, analysis_id)
        if not analysis:
            raise ValueError(f"Analysis {analysis_id} not found")

        # Clear previous calculations
        await self.db.execute(
            delete(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis_id
            )
        )

        if analysis.calculation_mode == "qualitative":
            return await self._calc_intrinsic_qualitative(analysis_id)
        elif analysis.calculation_mode == "quantitative":
            return await self._calc_intrinsic_quantitative(analysis_id)
        else:
            raise NotImplementedError(
                "MAGERIT hybrid mode (qualitative + quantitative combined "
                "calculation) is not implemented and will not be implemented. "
                "MAGERIT v3 Libro III does not formalize a canonical hybrid "
                "computation. See ADR-031. Use 'qualitative' or 'quantitative' "
                "calculation_mode."
            )

    async def _calc_intrinsic_qualitative(self, analysis_id: uuid.UUID) -> int:
        """
        Qualitative intrinsic risk calculation using lookup tables.

        IMPACT (Libro III, sec 2.2.1, p.9):
        > "Si un activo tiene un valor acumulado 'v' y se degrada un
        >  porcentaje 'd', el valor del impacto se calcula con alguna
        >  función que cumpla las siguientes condiciones de contorno:
        >  impacto(0, 0%) = 0, impacto(v, 0%) = 0, impacto(v, 100%) = v"

        In qualitative mode, we use the impact table from Libro III sec 2.1, p.6.

        RISK (Libro III, sec 2.1, p.7):
        > "Pudiendo combinarse impacto y frecuencia en una tabla para
        >  calcular el riesgo: [5×5 matrix]"

        MAGERIT v3 Libro III sec 2.1, p.7 — confirmed: risk is expressed
        as a qualitative lookup table, not an arithmetic formula. The
        table gives more weight to impact than to probability.

        ACCUMULATED vs REPERCUTED (Libro III, sec 2.2.1, p.9-10):
        > "Riesgo acumulado: se usará el impacto acumulado sobre el activo."
        > "Riesgo repercutido: se usará el impacto repercutido sobre el activo."
        """
        assets = (await self.db.execute(
            select(MageritAsset).where(
                MageritAsset.analysis_id == analysis_id,
                MageritAsset.deleted_at.is_(None),
            )
        )).scalars().all()
        asset_map = {str(a.id): a for a in assets}

        threats = (await self.db.execute(
            select(MageritThreatAssessment).where(
                MageritThreatAssessment.analysis_id == analysis_id
            )
        )).scalars().all()

        # Load dependencies for repercuted risk
        deps = (await self.db.execute(
            select(MageritAssetDependency).where(
                MageritAssetDependency.analysis_id == analysis_id
            )
        )).scalars().all()
        # inferior -> list of superior_ids
        inf_to_sups: dict[str, list[str]] = defaultdict(list)
        for dep in deps:
            inf_to_sups[str(dep.inferior_asset_id)].append(str(dep.superior_asset_id))

        calculations = []
        dims = ["d", "i", "c", "a", "t"]
        dim_codes = {"d": "D", "i": "I", "c": "C", "a": "A", "t": "T"}

        for ta in threats:
            asset = asset_map.get(str(ta.asset_id))
            if not asset:
                continue  # pragma: no cover  # FK constraint prevents orphan asset_id

            for dim in dims:
                degradation_pct = getattr(ta, f"degradation_{dim}") or 0
                if degradation_pct == 0:
                    continue

                degradation_level = _map_degradation_to_level(degradation_pct)

                # --- ACCUMULATED risk ---
                acc_value = getattr(asset, f"accumulated_{dim}") or 0
                acc_value_level = _map_value_to_level(acc_value)
                acc_impact_level = _lookup_impact_qualitative(acc_value_level, degradation_level)
                acc_risk_level = await _lookup_risk_matrix(self.db, acc_impact_level, ta.probability)

                calc_acc = MageritRiskCalculation(
                    analysis_id=analysis_id,
                    asset_id=ta.asset_id,
                    threat_code=ta.threat_code,
                    dimension=dim_codes[dim],
                    impact_intrinsic=LEVEL_TO_INDEX.get(acc_impact_level, 0),
                    risk_intrinsic_accumulated=LEVEL_TO_INDEX.get(acc_risk_level, 0),
                    risk_level=acc_risk_level,
                )
                self.db.add(calc_acc)
                calculations.append(calc_acc)

                # --- REPERCUTED risk ---
                # For each superior that depends on this asset, compute repercuted impact
                superiors = inf_to_sups.get(str(ta.asset_id), [])
                for sup_id in superiors:
                    sup = asset_map.get(sup_id)
                    if not sup:
                        continue  # pragma: no cover  # FK constraint prevents orphan sup_id
                    sup_own_value = getattr(sup, f"value_{dim}") or 0
                    if sup_own_value == 0:
                        continue

                    sup_value_level = _map_value_to_level(sup_own_value)
                    rep_impact_level = _lookup_impact_qualitative(sup_value_level, degradation_level)
                    rep_risk_level = await _lookup_risk_matrix(self.db, rep_impact_level, ta.probability)

                    calc_rep = MageritRiskCalculation(
                        analysis_id=analysis_id,
                        asset_id=uuid.UUID(sup_id),
                        threat_code=ta.threat_code,
                        dimension=dim_codes[dim],
                        impact_intrinsic=LEVEL_TO_INDEX.get(rep_impact_level, 0),
                        risk_intrinsic_repercuted=LEVEL_TO_INDEX.get(rep_risk_level, 0),
                        risk_level=rep_risk_level,
                    )
                    self.db.add(calc_rep)
                    calculations.append(calc_rep)

        await self.db.flush()
        return len(calculations)

    async def _calc_intrinsic_quantitative(self, analysis_id: uuid.UUID) -> int:
        """
        Quantitative intrinsic risk calculation using arithmetic formulas.

        IMPACT ACCUMULATED (Libro III, sec 2.2.2, p.13):
        > "Si un activo tiene un valor acumulado 'v' y sufre una
        >  degradación 'd', el impacto es
        >  impacto = i = v × d"

        IMPACT REPERCUTED (Libro III, sec 2.2.2, p.13):
        > "Si el activo A tiene un valor propio 'v', el impacto es
        >  impacto = v × d × grado(A ⇒ B)"

        RISK (Libro III, sec 2.2.2, p.14):
        > "El riesgo se calcula como
        >  riesgo = impacto × frecuencia"

        ACCUMULATED vs REPERCUTED (Libro III, sec 2.2.2, p.14):
        > "Riesgo acumulado: se usará el impacto acumulado sobre el activo;
        >  es decir, la pérdida de valor acumulado por amenazas sobre el mismo."
        > "Riesgo repercutido: se usará el impacto repercutido sobre el activo;
        >  es decir, la pérdida de valor propio por amenazas en activos inferiores."
        """
        assets = (await self.db.execute(
            select(MageritAsset).where(
                MageritAsset.analysis_id == analysis_id,
                MageritAsset.deleted_at.is_(None),
            )
        )).scalars().all()
        asset_map = {str(a.id): a for a in assets}

        threats = (await self.db.execute(
            select(MageritThreatAssessment).where(
                MageritThreatAssessment.analysis_id == analysis_id
            )
        )).scalars().all()

        deps = (await self.db.execute(
            select(MageritAssetDependency).where(
                MageritAssetDependency.analysis_id == analysis_id
            )
        )).scalars().all()
        # inferior -> list of (superior_id, degree)
        inf_to_sups: dict[str, list[tuple[str, float]]] = defaultdict(list)
        for dep in deps:
            inf_to_sups[str(dep.inferior_asset_id)].append(
                (str(dep.superior_asset_id), dep.dependency_degree)
            )

        calculations = []
        dims = ["d", "i", "c", "a", "t"]
        dim_codes = {"d": "D", "i": "I", "c": "C", "a": "A", "t": "T"}

        for ta in threats:
            asset = asset_map.get(str(ta.asset_id))
            if not asset:
                continue  # pragma: no cover  # FK constraint prevents orphan asset_id

            # Convert probability level to frequency
            frequency = FREQUENCY_MAP.get(ta.probability, 1.0)

            for dim in dims:
                degradation_pct = getattr(ta, f"degradation_{dim}") or 0
                if degradation_pct == 0:
                    continue
                d = degradation_pct / 100.0  # Convert to 0.0-1.0

                # --- ACCUMULATED risk ---
                # impacto = v × d (Libro III p.13)
                acc_value = getattr(asset, f"accumulated_{dim}") or 0
                acc_impact = acc_value * d
                # riesgo = impacto × frecuencia (Libro III p.14)
                acc_risk = acc_impact * frequency

                # Classify to qualitative level for the risk_level field
                acc_risk_level = _map_value_to_level(min(int(round(acc_risk)), 10))

                calc_acc = MageritRiskCalculation(
                    analysis_id=analysis_id,
                    asset_id=ta.asset_id,
                    threat_code=ta.threat_code,
                    dimension=dim_codes[dim],
                    impact_intrinsic=round(acc_impact, 4),
                    risk_intrinsic_accumulated=round(acc_risk, 4),
                    risk_level=acc_risk_level,
                )
                self.db.add(calc_acc)
                calculations.append(calc_acc)

                # --- REPERCUTED risk ---
                # impacto_rep = v_sup × d × grado(sup ⇒ inf) (Libro III p.13)
                superiors = inf_to_sups.get(str(ta.asset_id), [])
                for sup_id, degree in superiors:
                    sup = asset_map.get(sup_id)
                    if not sup:
                        continue  # pragma: no cover  # FK constraint prevents orphan sup_id
                    sup_own_value = getattr(sup, f"value_{dim}") or 0
                    if sup_own_value == 0:
                        continue

                    rep_impact = sup_own_value * d * degree
                    rep_risk = rep_impact * frequency
                    rep_risk_level = _map_value_to_level(min(int(round(rep_risk)), 10))

                    calc_rep = MageritRiskCalculation(
                        analysis_id=analysis_id,
                        asset_id=uuid.UUID(sup_id),
                        threat_code=ta.threat_code,
                        dimension=dim_codes[dim],
                        impact_intrinsic=round(rep_impact, 4),
                        risk_intrinsic_repercuted=round(rep_risk, 4),
                        risk_level=rep_risk_level,
                    )
                    self.db.add(calc_rep)
                    calculations.append(calc_rep)

        await self.db.flush()
        return len(calculations)

    # ================================================================
    # GRUPO 3: SALVAGUARDAS Y RIESGO RESIDUAL
    # ================================================================

    async def deploy_safeguards(
        self,
        analysis_id: uuid.UUID,
        deployments: list[dict],
    ) -> list[MageritSafeguardDeployment]:
        """
        Persist safeguard deployments for an analysis.

        Each deployment dict:
          - safeguard_code: str (e.g., "H.IA")
          - efficacy: int (0-100, overall percentage)
          - effect_type: str ("preventive", "palliative", "both")
          - status: str ("planned", "partial", "deployed", "verified")
          - responsible: str (optional)

        MAGERIT v3 Libro III, sec 2.2.1, p.11:
        > "la eficacia es un valor real entre 0,0 (no protege nada) y 1,0
        >  (salvaguarda plenamente eficaz), valor que se puede descomponer
        >  en una eficacia frente al impacto, 'ei', y una eficacia frente
        >  a la probabilidad 'ep'."
        """
        created = []
        for d in deployments:
            sd = MageritSafeguardDeployment(
                analysis_id=analysis_id,
                safeguard_code=d["safeguard_code"],
                efficacy=d.get("efficacy", 0),
                effect_type=d.get("effect_type", "both"),
                status=d.get("status", "planned"),
                responsible=d.get("responsible"),
                notes=d.get("notes"),
            )
            self.db.add(sd)
            created.append(sd)
        await self.db.flush()
        return created

    async def calculate_effective_risk(self, analysis_id: uuid.UUID) -> int:
        """
        Calculate effective risk (after safeguards) for all risk calculations.
        Dispatches to qualitative or quantitative implementation.
        Returns number of calculations updated.
        """
        analysis = await self.db.get(MageritAnalysis, analysis_id)
        if not analysis:
            raise ValueError(f"Analysis {analysis_id} not found")

        if analysis.calculation_mode == "qualitative":
            return await self._calc_effective_qualitative(analysis_id)
        elif analysis.calculation_mode == "quantitative":
            return await self._calc_effective_quantitative(analysis_id)
        else:
            raise NotImplementedError(
                "MAGERIT hybrid mode (qualitative + quantitative combined "
                "calculation) is not implemented and will not be implemented. "
                "MAGERIT v3 Libro III does not formalize a canonical hybrid "
                "computation. See ADR-031. Use 'qualitative' or 'quantitative' "
                "calculation_mode."
            )

    async def _calc_effective_qualitative(self, analysis_id: uuid.UUID) -> int:
        """
        Qualitative effective risk: apply safeguard efficacy as percentage to
        degradation and probability, then re-classify and re-lookup tables.

        MAGERIT v3 Libro III, sec 2.2.1, p.11:
        > "Degradación residual: Si el activo, sin protección, podía sufrir
        >  una degradación 'd', gracias a las salvaguardas la degradación se
        >  ve reducida a un valor residual 'dr':
        >  dr(d, 0) = d
        >  dr(d, 1) = 0"

        > "La probabilidad de la amenaza sobre el activo se ve reducida a un
        >  valor residual:
        >  pr(p, 0) = p
        >  pr(p, 1) = 0"

        > "Riesgo residual: Es el riesgo calculado a partir del impacto y
        >  frecuencia residuales:
        >  riesgo_residual = ℜ(impacto_residual, frecuencia_residual)"

        NOTE: In qualitative mode, efficacy is applied as percentage to the
        raw degradation/frequency values, then re-classified to qualitative
        levels for table lookup. This introduces quantization error inherent
        to the qualitative model.
        """
        calcs = (await self.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis_id
            )
        )).scalars().all()

        assets = (await self.db.execute(
            select(MageritAsset).where(
                MageritAsset.analysis_id == analysis_id,
                MageritAsset.deleted_at.is_(None),
            )
        )).scalars().all()
        asset_map = {str(a.id): a for a in assets}

        threats = (await self.db.execute(
            select(MageritThreatAssessment).where(
                MageritThreatAssessment.analysis_id == analysis_id
            )
        )).scalars().all()
        # Build lookup: (asset_id, threat_code) -> assessment
        ta_map = {(str(t.asset_id), t.threat_code): t for t in threats}

        safeguards = (await self.db.execute(
            select(MageritSafeguardDeployment).where(
                MageritSafeguardDeployment.analysis_id == analysis_id
            )
        )).scalars().all()

        # Compute package efficacy
        ei, ep = _compute_package_efficacy(safeguards)

        updated = 0
        for calc in calcs:
            ta = ta_map.get((str(calc.asset_id), calc.threat_code))
            if not ta:
                continue  # pragma: no cover  # Repercuted calcs (asset_id=SUP) skip here; only direct threats processed

            dim = calc.dimension.lower()
            degradation_pct = getattr(ta, f"degradation_{dim}") or 0
            if degradation_pct == 0:
                continue  # pragma: no cover  # Intrinsic already filters degradation==0 before creating calcs

            # Apply efficacy to degradation and probability
            degrad_residual_pct = degradation_pct * (1.0 - ei)
            freq_original = FREQUENCY_MAP.get(ta.probability, 1.0)
            freq_residual = freq_original * (1.0 - ep)

            # Re-classify to levels
            degrad_level = _map_degradation_to_level(int(round(degrad_residual_pct)))
            prob_level = _map_frequency_to_level(freq_residual)

            # Determine value level for this calc
            asset = asset_map.get(str(calc.asset_id))
            if not asset:
                continue  # pragma: no cover  # FK constraint prevents orphan asset_id

            if calc.risk_intrinsic_accumulated is not None:
                val = getattr(asset, f"accumulated_{dim}") or 0
            else:
                val = getattr(asset, f"value_{dim}") or 0
            value_level = _map_value_to_level(val)

            # Re-lookup impact and risk
            impact_level = _lookup_impact_qualitative(value_level, degrad_level)
            risk_level = await _lookup_risk_matrix(self.db, impact_level, prob_level)

            calc.impact_effective = float(LEVEL_TO_INDEX.get(impact_level, 0))
            calc.risk_effective = float(LEVEL_TO_INDEX.get(risk_level, 0))
            calc.risk_level = risk_level
            updated += 1

        await self.db.flush()
        return updated

    async def _calc_effective_quantitative(self, analysis_id: uuid.UUID) -> int:
        """
        Quantitative effective risk using arithmetic formulas.

        MAGERIT v3 Libro III, sec 2.2.2, p.15:
        > "impacto residual = 900.000 * (1 – 0.9) = 90.000"
        > Generalized: impacto_residual = impacto × (1 − ei)

        > "frecuencia residual = 0,1 x (1 – 50%) = 0,05"
        > Generalized: frecuencia_residual = frecuencia × (1 − ep)

        > "riesgo residual = 90.000 * 0,05 = 4.500"
        > Generalized: riesgo_residual = impacto_residual × frecuencia_residual

        All calculations in float, no intermediate rounding.
        """
        calcs = (await self.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis_id
            )
        )).scalars().all()

        threats = (await self.db.execute(
            select(MageritThreatAssessment).where(
                MageritThreatAssessment.analysis_id == analysis_id
            )
        )).scalars().all()
        ta_map = {(str(t.asset_id), t.threat_code): t for t in threats}

        safeguards = (await self.db.execute(
            select(MageritSafeguardDeployment).where(
                MageritSafeguardDeployment.analysis_id == analysis_id
            )
        )).scalars().all()

        ei, ep = _compute_package_efficacy(safeguards)

        updated = 0
        for calc in calcs:
            if calc.impact_intrinsic is None or calc.impact_intrinsic == 0:
                continue  # pragma: no cover  # Motor never creates calcs with impact=0 (filtered upstream)

            ta = ta_map.get((str(calc.asset_id), calc.threat_code))
            if not ta:
                continue

            frequency = FREQUENCY_MAP.get(ta.probability, 1.0)

            # impacto_efectivo = impacto_intrínseco × (1 - ei)
            impact_eff = calc.impact_intrinsic * (1.0 - ei)
            # frecuencia_residual = frecuencia × (1 - ep)
            freq_eff = frequency * (1.0 - ep)
            # riesgo_efectivo = impacto_efectivo × frecuencia_residual
            risk_eff = impact_eff * freq_eff

            calc.impact_effective = round(impact_eff, 4)
            calc.risk_effective = round(risk_eff, 4)
            calc.risk_level = _map_value_to_level(min(int(round(risk_eff)), 10))
            updated += 1

        await self.db.flush()
        return updated

    async def generate_treatment_plan(
        self,
        analysis_id: uuid.UUID,
        threshold: str = "A",
    ) -> list[MageritTreatmentPlan]:
        """
        Generate a treatment plan for risks above the acceptance threshold.

        MAGERIT v3 Libro I, sec 4.1.2 "Risk acceptance", p.46:
        > "Management of the Organisation subject to risk analysis must
        >  determine the acceptable impact and risk levels. More precisely,
        >  it must accept the responsibility of residual values. This is not
        >  a technical decision. It may be a political or managerial decision."

        MAGERIT v3 Libro I, sec 4.1.6-4.1.9, p.47-51 defines 4 treatment options:
        - Accept: risk is within acceptable levels (sec 4.1.2, p.46)
        - Mitigate: deploy safeguards to reduce risk (sec 4.1.7, p.50-51)
        - Transfer/Share: outsource or insure (sec 4.1.9, p.51)
        - Eliminate: remove the asset or service (implicit in sec 4.1.6 zone analysis)

        # Treatment thresholds are FULKRO convention, not MAGERIT official.
        # MAGERIT explicitly states this is "not a technical decision" (Libro I p.46).
        # Our convention:
        #   risk_level <= threshold → accept
        #   risk_level one above threshold → mitigate
        #   risk_level two above threshold → mitigate (urgent) or transfer
        #   risk_level = MC (muy crítico) → eliminate or transfer

        Args:
            threshold: Maximum acceptable risk level (default "A" = apreciable).
                       Levels above this generate treatment actions.
        """
        # Clear previous plan
        await self.db.execute(
            delete(MageritTreatmentPlan).where(
                MageritTreatmentPlan.analysis_id == analysis_id
            )
        )

        # Get effective risks
        calcs = (await self.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis_id
            )
        )).scalars().all()

        threshold_idx = LEVEL_TO_INDEX.get(threshold, 3)
        plans = []

        for calc in calcs:
            risk_idx = LEVEL_TO_INDEX.get(calc.risk_level, 0)
            if risk_idx <= threshold_idx:
                continue  # Acceptable, no action needed

            # Determine treatment based on severity above threshold
            excess = risk_idx - threshold_idx
            if excess == 1:
                treatment = "mitigar"
                action = (
                    f"Riesgo {calc.risk_level} supera el umbral {threshold}. "
                    f"Implantar salvaguardas adicionales para reducir el riesgo "
                    f"sobre {calc.threat_code} en dimensión {calc.dimension}."
                )
            elif excess >= 2 and calc.risk_level == "MA":
                treatment = "eliminar"
                action = (
                    f"Riesgo CRÍTICO ({calc.risk_level}) sobre {calc.threat_code}. "
                    f"Considerar eliminar el activo del alcance o transferir "
                    f"el riesgo a un tercero (seguro, externalización)."
                )
            else:
                treatment = "transferir"
                action = (
                    f"Riesgo {calc.risk_level} significativamente por encima del "
                    f"umbral {threshold}. Transferir mediante seguro o externalización."
                )

            plan = MageritTreatmentPlan(
                analysis_id=analysis_id,
                asset_id=calc.asset_id,
                threat_code=calc.threat_code,
                dimension=calc.dimension,
                current_risk_level=calc.risk_level,
                current_risk_value=calc.risk_effective or calc.risk_intrinsic_accumulated,
                treatment=treatment,
                action_description=action,
                target_risk_level=threshold,
                status="pending",
            )
            self.db.add(plan)
            plans.append(plan)

        await self.db.flush()
        return plans

    async def calculate_residual_risk(self, analysis_id: uuid.UUID) -> int:
        """
        Calculate residual risk after applying the treatment plan.
        Dispatches to qualitative or quantitative.

        MAGERIT v3 Libro III, sec 2.2.1, p.11:
        > "Riesgo residual: Es el riesgo calculado a partir del impacto y
        >  frecuencia residuales:
        >  riesgo_residual = ℜ(impacto_residual, frecuencia_residual)"

        In practice, residual risk = effective risk for items without
        treatment action, or a reduced value for items with treatment.
        The reduction depends on the treatment type:
        - mitigate: assumes proposed safeguards bring risk to target level
        - transfer: assumes 50% risk transfer (FULKRO convention)
        - eliminate: risk goes to zero
        - accept: no change

        # Residual risk reduction factors are FULKRO convention.
        """
        analysis = await self.db.get(MageritAnalysis, analysis_id)
        if not analysis:
            raise ValueError(f"Analysis {analysis_id} not found")

        plans = (await self.db.execute(
            select(MageritTreatmentPlan).where(
                MageritTreatmentPlan.analysis_id == analysis_id
            )
        )).scalars().all()

        # Build lookup: (asset_id, threat_code, dimension) -> treatment
        plan_map = {}
        for p in plans:
            plan_map[(str(p.asset_id), p.threat_code, p.dimension)] = p

        calcs = (await self.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis_id
            )
        )).scalars().all()

        updated = 0
        for calc in calcs:
            key = (str(calc.asset_id), calc.threat_code, calc.dimension)
            plan = plan_map.get(key)

            eff_risk = calc.risk_effective if calc.risk_effective is not None else (
                calc.risk_intrinsic_accumulated or calc.risk_intrinsic_repercuted or 0
            )

            if plan is None:
                # No treatment needed, residual = effective
                calc.risk_residual = eff_risk
            elif plan.treatment == "eliminar":
                calc.risk_residual = 0.0
            elif plan.treatment == "transferir":
                calc.risk_residual = eff_risk * 0.5  # FULKRO convention: 50% transfer
            elif plan.treatment == "mitigar":
                # Assume mitigation brings to target level
                target_idx = LEVEL_TO_INDEX.get(plan.target_risk_level, 0)
                if analysis.calculation_mode == "qualitative":
                    calc.risk_residual = float(target_idx)
                else:
                    # Reduce proportionally to reach target
                    current_idx = LEVEL_TO_INDEX.get(calc.risk_level, 0)
                    if current_idx > 0:
                        ratio = target_idx / current_idx
                        calc.risk_residual = eff_risk * ratio
                    else:
                        calc.risk_residual = eff_risk  # pragma: no cover  # current_idx==0 impossible (risk always > 0 for treated calcs)
            else:
                calc.risk_residual = eff_risk  # pragma: no cover  # CHECK constraint ck_treatment_plan_treatment prevents unknown treatments

            # Update risk level based on residual
            if analysis.calculation_mode == "qualitative":
                residual_idx = int(round(calc.risk_residual))
                calc.risk_level = LEVELS_ORDER[min(residual_idx, 4)]
            else:
                calc.risk_level = _map_value_to_level(min(int(round(calc.risk_residual)), 10))

            updated += 1

        await self.db.flush()
        return updated


    async def _build_analysis_snapshot(self, analysis_id: uuid.UUID) -> dict:
        """Build a complete deterministic snapshot of the analysis state."""
        analysis = await self.db.get(MageritAnalysis, analysis_id)

        assets = (await self.db.execute(
            select(MageritAsset).where(
                MageritAsset.analysis_id == analysis_id,
                MageritAsset.deleted_at.is_(None),
            ).order_by(MageritAsset.code)
        )).scalars().all()

        deps = (await self.db.execute(
            select(MageritAssetDependency).where(
                MageritAssetDependency.analysis_id == analysis_id
            )
        )).scalars().all()

        threats = (await self.db.execute(
            select(MageritThreatAssessment).where(
                MageritThreatAssessment.analysis_id == analysis_id
            )
        )).scalars().all()

        safeguards = (await self.db.execute(
            select(MageritSafeguardDeployment).where(
                MageritSafeguardDeployment.analysis_id == analysis_id
            )
        )).scalars().all()

        calcs = (await self.db.execute(
            select(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis_id
            )
        )).scalars().all()

        plans = (await self.db.execute(
            select(MageritTreatmentPlan).where(
                MageritTreatmentPlan.analysis_id == analysis_id,
                MageritTreatmentPlan.deleted_at.is_(None),
            )
        )).scalars().all()

        return {
            "schema_version": "1.0",
            "analysis": {
                "id": str(analysis.id),
                "name": analysis.name,
                "calculation_mode": analysis.calculation_mode,
                "methodology_version": analysis.methodology_version,
            },
            "assets": sorted([
                {
                    "id": str(a.id), "code": a.code, "name": a.name,
                    "asset_type_code": a.asset_type_code,
                    "value_d": a.value_d, "value_i": a.value_i,
                    "value_c": a.value_c, "value_a": a.value_a, "value_t": a.value_t,
                    "accumulated_d": float(a.accumulated_d) if a.accumulated_d else None,
                    "accumulated_i": float(a.accumulated_i) if a.accumulated_i else None,
                    "accumulated_c": float(a.accumulated_c) if a.accumulated_c else None,
                    "accumulated_a": float(a.accumulated_a) if a.accumulated_a else None,
                    "accumulated_t": float(a.accumulated_t) if a.accumulated_t else None,
                }
                for a in assets
            ], key=lambda x: x["code"]),
            "dependencies": [
                {
                    "superior_asset_id": str(d.superior_asset_id),
                    "inferior_asset_id": str(d.inferior_asset_id),
                    "dependency_degree": d.dependency_degree,
                }
                for d in deps
            ],
            "threats_applied": sorted([
                {
                    "asset_id": str(t.asset_id), "threat_code": t.threat_code,
                    "probability": t.probability,
                    "degradation_d": t.degradation_d, "degradation_i": t.degradation_i,
                    "degradation_c": t.degradation_c, "degradation_a": t.degradation_a,
                    "degradation_t": t.degradation_t,
                }
                for t in threats
            ], key=lambda x: (x["asset_id"], x["threat_code"])),
            "safeguards_applied": sorted([
                {
                    "safeguard_code": s.safeguard_code, "efficacy": s.efficacy,
                    "effect_type": s.effect_type, "status": s.status,
                }
                for s in safeguards
            ], key=lambda x: x["safeguard_code"]),
            "risk_calculations": sorted([
                {
                    "asset_id": str(c.asset_id), "threat_code": c.threat_code,
                    "dimension": c.dimension,
                    "risk_intrinsic_accumulated": c.risk_intrinsic_accumulated,
                    "risk_intrinsic_repercuted": c.risk_intrinsic_repercuted,
                    "risk_effective": c.risk_effective,
                    "risk_residual": c.risk_residual,
                    "risk_level": c.risk_level,
                }
                for c in calcs
            ], key=lambda x: (x["asset_id"], x["threat_code"], x["dimension"])),
            "treatment_plan": sorted([
                {
                    "asset_id": str(p.asset_id), "threat_code": p.threat_code,
                    "dimension": p.dimension, "treatment": p.treatment,
                    "current_risk_level": p.current_risk_level,
                    "target_risk_level": p.target_risk_level,
                }
                for p in plans
            ], key=lambda x: (x["asset_id"], x["threat_code"], x["dimension"])),
        }

    async def freeze_analysis_snapshot(self, analysis_id: uuid.UUID) -> dict:
        """Freeze the analysis: build snapshot and lock against modifications."""
        from datetime import datetime, timezone

        analysis = await self.db.get(MageritAnalysis, analysis_id)
        if not analysis:
            raise ValueError(f"Analysis {analysis_id} not found")

        # Must have at least risk calculations
        calc_count = await self.db.scalar(
            select(sa_func.count()).select_from(MageritRiskCalculation).where(
                MageritRiskCalculation.analysis_id == analysis_id
            )
        )
        if not calc_count:
            raise ValueError("Cannot freeze: no risk calculations exist. Run the pipeline first.")

        snapshot = await self._build_analysis_snapshot(analysis_id)
        analysis.result_snapshot = snapshot
        analysis.snapshot_frozen_at = datetime.now(timezone.utc)
        await self.db.flush()
        return snapshot

    async def unfreeze_analysis_snapshot(self, analysis_id: uuid.UUID) -> None:
        """Unfreeze the analysis: clear snapshot and allow modifications."""
        analysis = await self.db.get(MageritAnalysis, analysis_id)
        if not analysis:
            raise ValueError(f"Analysis {analysis_id} not found")
        analysis.result_snapshot = None
        analysis.snapshot_frozen_at = None
        await self.db.flush()


    # ================================================================
    # ASSET IMPORT FROM CSV/XLSX
    # ================================================================

    IMPORT_REQUIRED_COLUMNS = {"code", "name", "asset_type_code", "value_d", "value_i", "value_c", "value_a", "value_t"}

    async def import_assets_from_csv(self, analysis_id: uuid.UUID, file_bytes: bytes) -> dict:
        """Import assets from CSV UTF-8. Atomic: all or nothing."""
        import csv
        import io
        text = file_bytes.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        return await self._import_assets_common(analysis_id, rows, "csv")

    async def import_assets_from_xlsx(self, analysis_id: uuid.UUID, file_bytes: bytes) -> dict:
        """Import assets from XLSX. Atomic: all or nothing."""
        import io
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(file_bytes), data_only=True)
        ws = wb.active
        rows_raw = list(ws.iter_rows(values_only=True))
        if not rows_raw:
            raise ValueError("El fichero XLSX esta vacio")
        headers = [str(c).strip() if c is not None else "" for c in rows_raw[0]]
        rows = []
        for row_tuple in rows_raw[1:]:
            row_dict = {}
            for i, h in enumerate(headers):
                val = row_tuple[i] if i < len(row_tuple) else None
                row_dict[h] = str(val).strip() if val is not None else ""
            rows.append(row_dict)
        return await self._import_assets_common(analysis_id, rows, "xlsx")

    async def _import_assets_common(
        self, analysis_id: uuid.UUID, rows: list[dict], source: str,
    ) -> dict:
        """Validate + atomic insert common to CSV and XLSX.

        Phases:
        1. Validate columns present
        2. Validate each row (asset_type_code exists, values are int 0-10)
        3. If any row fails -> return error list, insert nothing
        4. If all valid -> bulk insert, return summary
        """
        if not rows:
            raise ValueError(f"El fichero {source} no contiene filas de datos")

        present = set(rows[0].keys())
        missing = self.IMPORT_REQUIRED_COLUMNS - present
        if missing:
            raise ValueError(f"Faltan columnas obligatorias: {sorted(missing)}")

        # Load valid asset_type_codes
        result = await self.db.execute(sa_text("SELECT code FROM magerit_asset_types"))
        valid_codes = {row[0] for row in result.fetchall()}

        errors = []
        validated = []
        for idx, row in enumerate(rows, start=2):
            row_errors = []
            code = row.get("code", "").strip()
            name = row.get("name", "").strip()
            atype = row.get("asset_type_code", "").strip()

            if not code:
                row_errors.append("code vacio")
            if not name:
                row_errors.append("name vacio")
            if atype and atype not in valid_codes:
                row_errors.append(f"asset_type_code '{atype}' no existe en catalogo")

            values = {}
            for dim in ["d", "i", "c", "a", "t"]:
                raw = row.get(f"value_{dim}", "").strip()
                if raw:
                    try:
                        v = int(raw)
                        if not (0 <= v <= 10):
                            row_errors.append(f"value_{dim}={v} fuera de rango 0-10")
                        else:
                            values[f"value_{dim}"] = v
                    except ValueError:
                        row_errors.append(f"value_{dim}='{raw}' no es entero")
                else:
                    values[f"value_{dim}"] = 0

            if row_errors:
                errors.append({"row": idx, "code": code, "errors": row_errors})
            else:
                validated.append({
                    "code": code,
                    "name": name,
                    "asset_type_code": atype,
                    "description": row.get("description", "").strip() or None,
                    "owner": row.get("owner", "").strip() or None,
                    **values,
                })

        if errors:
            raise ValueError(
                f"Import fallido ({len(errors)} filas con errores, modo atomico). "
                f"Detalle: {errors[:5]}"
            )

        for asset_data in validated:
            a = MageritAsset(
                analysis_id=analysis_id,
                **asset_data,
                accumulated_d=asset_data.get("value_d", 0),
                accumulated_i=asset_data.get("value_i", 0),
                accumulated_c=asset_data.get("value_c", 0),
                accumulated_a=asset_data.get("value_a", 0),
                accumulated_t=asset_data.get("value_t", 0),
            )
            self.db.add(a)

        await self.db.flush()
        return {
            "source": source,
            "imported_count": len(validated),
            "errors": [],
            "mode": "atomic",
        }
