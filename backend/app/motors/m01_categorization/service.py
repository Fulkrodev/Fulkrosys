"""
Motor 1 — Categorization Engine (DETERMINISTIC).

Implements the ENS system categorization per Anexo I of RD 311/2022.
No LLM. Pure Python implementation of the maximum rule.

The category of a system is determined by the highest impact level
across all five security dimensions (DICAT) for all information
types and services within scope.

Dimensions:
  D - Disponibilidad (Availability)
  I - Integridad (Integrity)
  C - Confidencialidad (Confidentiality)
  A - Autenticidad (Authenticity)
  T - Trazabilidad (Traceability)

Categories:
  BASICA - All dimensions are BAJO
  MEDIA  - Highest dimension is MEDIO
  ALTA   - Highest dimension is ALTO
"""
import uuid
from dataclasses import dataclass
from datetime import date
from enum import Enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.core import (
    Categorization,
    InformationType,
    Service,
)


class ImpactLevel(str, Enum):
    """Impact level for a security dimension."""
    BAJO = "BAJO"
    MEDIO = "MEDIO"
    ALTO = "ALTO"

    @property
    def numeric(self) -> int:
        return {"BAJO": 1, "MEDIO": 2, "ALTO": 3}[self.value]


class Category(str, Enum):
    """System category per ENS Anexo I."""
    BASICA = "BASICA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"


# Dimension catalog per RD 311/2022 Anexo I
DIMENSIONS = {
    "D": {
        "code": "D",
        "name": "Disponibilidad",
        "name_full": "Disponibilidad",
        "description": (
            "Propiedad o característica de los activos consistente en que las "
            "entidades o procesos autorizados tienen acceso a los mismos cuando "
            "lo requieren. [RD 311/2022 Anexo IV]"
        ),
    },
    "I": {
        "code": "I",
        "name": "Integridad",
        "name_full": "Integridad de los datos",
        "description": (
            "Propiedad o característica consistente en que el activo de "
            "información no ha sido alterado de manera no autorizada. "
            "[RD 311/2022 Anexo IV]"
        ),
    },
    "C": {
        "code": "C",
        "name": "Confidencialidad",
        "name_full": "Confidencialidad de los datos",
        "description": (
            "Propiedad o característica consistente en que la información ni "
            "se pone a disposición, ni se revela a individuos, entidades o "
            "procesos no autorizados. [RD 311/2022 Anexo IV]"
        ),
    },
    "A": {
        "code": "A",
        "name": "Autenticidad",
        "name_full": "Autenticidad",
        "description": (
            "Propiedad o característica consistente en que una entidad es "
            "quien dice ser o bien que garantiza la fuente de la que proceden "
            "los datos. [RD 311/2022 Anexo IV]"
        ),
    },
    "T": {
        "code": "T",
        "name": "Trazabilidad",
        "name_full": "Trazabilidad del servicio y de los datos",
        "description": (
            "Propiedad o característica consistente en que las actuaciones de "
            "una entidad pueden ser imputadas exclusivamente a dicha entidad. "
            "[RD 311/2022 Anexo IV]"
        ),
    },
}


@dataclass
class DimensionAssessment:
    """Assessment of a single dimension."""
    dimension: str  # D, I, C, A, T
    level: ImpactLevel
    justification: str = ""


@dataclass
class CategorizationResult:
    """Result of the categorization computation."""
    category: Category
    dimension_assessments: dict[str, ImpactLevel]  # {D: ALTO, I: MEDIO, ...}
    determining_dimension: str  # The dimension that set the category
    justification: str


def _level_to_category(level: ImpactLevel) -> Category:
    """Map an impact level to the corresponding category."""
    return {
        ImpactLevel.BAJO: Category.BASICA,
        ImpactLevel.MEDIO: Category.MEDIA,
        ImpactLevel.ALTO: Category.ALTA,
    }[level]


# #5 (Sub-bloque E) · rango ordinal de categorías para el "piso" heredado AAPP.
_CATEGORY_RANK = {
    Category.BASICA: 1,
    Category.MEDIA: 2,
    Category.ALTA: 3,
}


def _parse_floor(inherited_floor: str | None) -> Category | None:
    """Parse the AAPP inherited-floor category. None/empty/invalid → None (no-op).

    Defensive: an unrecognised value (e.g. legacy 'M'/'A'/'B') degrades to None
    so the floor never lowers nor breaks the max rule.
    """
    if not inherited_floor:
        return None
    try:
        return Category(inherited_floor.strip().upper())
    except ValueError:
        return None


def elevate_to_floor(current: str | None, floor: str | None) -> str | None:
    """Return ``max(current, floor)`` by ENS category rank · solo ELEVA, nunca baja.

    The canonical Variante 2 helper (reused by provisioning + the signing
    conversion + the inherited-floor endpoint) so the project ``categoria_objetivo``
    never sits below the AAPP inherited floor. ``floor`` None/unknown → ``current``
    unchanged. ``current`` None/unknown → the floor (the floor is a hard minimum).
    """
    parsed_floor = _parse_floor(floor)
    if parsed_floor is None:
        return current
    parsed_current = _parse_floor(current)
    if parsed_current is None:
        return parsed_floor.value
    if _CATEGORY_RANK[parsed_floor] > _CATEGORY_RANK[parsed_current]:
        return parsed_floor.value
    return current


def compute_category(
    assessments: dict[str, str],
    inherited_floor: str | None = None,
) -> CategorizationResult:
    """
    Compute system category from dimension assessments.

    This is the DETERMINISTIC core of Motor 1.
    Implements the maximum rule from RD 311/2022 Anexo I:
    "La categoría del sistema vendrá determinada por la valoración
    más alta que haya recibido cualquiera de sus dimensiones de seguridad."

    #5 (Sub-bloque E) · ``inherited_floor`` is the category the AAPP assigned to
    the service (BASICA/MEDIA/ALTA, or None). It acts as a HARD floor: the result
    can only RISE above it, never be declared below it. It enters as one more
    value to maximise — coherent with the Anexo I max rule. When it elevates the
    category, the justification cites the inheritance explicitly.

    Args:
        assessments: dict mapping dimension code to impact level string.
                     e.g. {"D": "MEDIO", "I": "BAJO", "C": "ALTO", "A": "BAJO", "T": "MEDIO"}
        inherited_floor: AAPP inherited-floor category (BASICA/MEDIA/ALTA) or None.

    Returns:
        CategorizationResult with the computed category.

    Raises:
        ValueError: if any dimension is missing or has an invalid value.
    """
    required = {"D", "I", "C", "A", "T"}
    provided = set(assessments.keys())

    if provided != required:
        missing = required - provided
        extra = provided - required
        parts = []
        if missing:
            parts.append(f"faltan dimensiones: {missing}")
        if extra:
            parts.append(f"dimensiones desconocidas: {extra}")
        raise ValueError(f"Valoración DICAT incompleta: {'; '.join(parts)}")

    # Validate and parse levels
    parsed: dict[str, ImpactLevel] = {}
    for dim, level_str in assessments.items():
        try:
            parsed[dim] = ImpactLevel(level_str.upper())
        except ValueError:
            valid = [l.value for l in ImpactLevel]
            raise ValueError(
                f"Nivel de impacto inválido para dimensión {dim}: "
                f"'{level_str}'. Valores válidos: {valid}"
            )

    # Apply maximum rule (RD 311/2022 Anexo I)
    max_level = max(parsed.values(), key=lambda l: l.numeric)
    max_dims = [d for d, l in parsed.items() if l == max_level]
    determining = max_dims[0]  # First dimension at max level
    dicat_category = _level_to_category(max_level)  # categoría por la sola regla DICAT
    category = dicat_category

    # #5 · suelo heredado de la AAPP. Piso DURO: la categoría solo SUBE por
    # encima del suelo, nunca por debajo (Anexo I = máximo; la herencia es una
    # restricción ADICIONAL por encima). Entra como un valor más a maximizar.
    floor = _parse_floor(inherited_floor)
    elevated_by_floor = (
        floor is not None and _CATEGORY_RANK[floor] > _CATEGORY_RANK[dicat_category]
    )
    if elevated_by_floor:
        category = floor

    # Build justification
    dim_summary = ", ".join(
        f"{d}={parsed[d].value}" for d in ["D", "I", "C", "A", "T"]
    )
    if elevated_by_floor:
        det_name = DIMENSIONS[determining]["name"]
        # La cita de la herencia es lo que el auditor ENAC quiere ver: el porqué
        # normativo de declarar por encima de la regla del máximo DICAT.
        justification = (
            f"La valoración DICAT por la regla del máximo (Anexo I del "
            f"RD 311/2022) determinaría categoría {dicat_category.value} "
            f"(dimensión determinante {det_name} [{determining}] con nivel "
            f"{max_level.value}). No obstante, la categoría se ELEVA a "
            f"{category.value} por herencia de la AAPP contratante: no puede "
            f"declararse por debajo de la categoría que la Administración "
            f"asignó al servicio al que da soporte. "
            f"Valoración DICAT: {dim_summary}."
        )
    elif len(max_dims) == 1:
        det_name = DIMENSIONS[determining]["name"]
        justification = (
            f"La categoría del sistema es {category.value} conforme al "
            f"Anexo I del RD 311/2022 (regla del máximo). "
            f"La dimensión determinante es {det_name} ({determining}) "
            f"con nivel {max_level.value}. "
            f"Valoración DICAT: {dim_summary}."
        )
    else:
        det_names = ", ".join(DIMENSIONS[d]["name"] for d in max_dims)
        justification = (
            f"La categoría del sistema es {category.value} conforme al "
            f"Anexo I del RD 311/2022 (regla del máximo). "
            f"Las dimensiones determinantes son {det_names} "
            f"({', '.join(max_dims)}) con nivel {max_level.value}. "
            f"Valoración DICAT: {dim_summary}."
        )

    return CategorizationResult(
        category=category,
        dimension_assessments=parsed,
        determining_dimension=determining,
        justification=justification,
    )


class CategorizationService:
    """Service layer for Motor 1 — Categorization Engine."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def compute_for_system(self, system_id: uuid.UUID) -> CategorizationResult:
        """
        Compute categorization for a system based on its information types
        and services valuations.
        """
        # Gather all ACTIVE valuations (soft-deleted items are excluded)
        info_types = (await self.db.execute(
            select(InformationType).where(
                InformationType.system_id == system_id,
                InformationType.deleted_at.is_(None),
            )
        )).scalars().all()

        services = (await self.db.execute(
            select(Service).where(
                Service.system_id == system_id,
                Service.deleted_at.is_(None),
            )
        )).scalars().all()

        if not info_types and not services:
            raise ValueError(  # pragma: no cover  # Endpoint api.py L239 pre-checks empty system before calling this
                f"Sistema {system_id} no tiene tipos de información ni "
                f"servicios valorados. No se puede categorizar."
            )

        # Find the maximum level per dimension across all info types and services
        max_per_dim = {"D": "BAJO", "I": "BAJO", "C": "BAJO", "A": "BAJO", "T": "BAJO"}

        for item in list(info_types) + list(services):
            for dim_attr, dim_code in [
                ("valoracion_d", "D"), ("valoracion_i", "I"),
                ("valoracion_c", "C"), ("valoracion_a", "A"),
                ("valoracion_t", "T"),
            ]:
                val = getattr(item, dim_attr, None)
                if val and val.upper() in ("BAJO", "MEDIO", "ALTO"):
                    current = ImpactLevel(max_per_dim[dim_code])
                    new = ImpactLevel(val.upper())
                    if new.numeric > current.numeric:
                        max_per_dim[dim_code] = new.value

        # Build immutable snapshot of the input used for this calculation
        self._last_snapshot = {
            "information_types": [
                {
                    "id": str(it.id),
                    "nombre": it.nombre,
                    "valoraciones": {
                        "D": it.valoracion_d,
                        "I": it.valoracion_i,
                        "C": it.valoracion_c,
                        "A": it.valoracion_a,
                        "T": it.valoracion_t,
                    },
                }
                for it in info_types
            ],
            "services": [
                {
                    "id": str(s.id),
                    "nombre": s.nombre,
                    "valoraciones": {
                        "D": s.valoracion_d,
                        "I": s.valoracion_i,
                        "C": s.valoracion_c,
                        "A": s.valoracion_a,
                        "T": s.valoracion_t,
                    },
                }
                for s in services
            ],
        }

        # #5 · resolver el suelo heredado de la AAPP del proyecto del sistema y
        # pasarlo como piso. Un solo punto: lo respetan automáticamente los 5
        # consumidores de compute_for_system (categorize + actas MD/PDF/DOCX/JSON).
        from sqlalchemy import text as sa_text
        inherited_floor = (await self.db.execute(
            sa_text(
                "SELECT p.categoria_heredada_aapp FROM projects p "
                "JOIN systems s ON s.project_id = p.id WHERE s.id = :sid"
            ),
            {"sid": str(system_id)},
        )).scalar()

        return compute_category(max_per_dim, inherited_floor=inherited_floor)

    async def save_categorization(
        self,
        system_id: uuid.UUID,
        result: CategorizationResult,
        aprobado_por: str | None = None,
        input_snapshot: dict | None = None,
    ) -> Categorization:
        """Persist the categorization result with version and input snapshot."""
        # Auto-increment version per system
        from sqlalchemy import text as sa_text
        version_row = await self.db.execute(
            sa_text(
                "SELECT COALESCE(MAX(version), 0) + 1 "
                "FROM categorizations WHERE system_id = :sid AND deleted_at IS NULL"
            ),
            {"sid": str(system_id)},
        )
        next_version = version_row.scalar()

        cat = Categorization(
            system_id=system_id,
            categoria_resultante=result.category.value,
            fecha_acta=date.today(),
            aprobado_por=aprobado_por,
            version=next_version,
            input_snapshot=input_snapshot,
        )
        self.db.add(cat)
        await self.db.flush()
        return cat

    def generate_acta_e012(
        self,
        result: CategorizationResult,
        project_name: str,
        system_name: str,
        rag_citation: str = "",
    ) -> str:
        """
        Generate the categorization act (E-012) in Markdown format.

        The E-012 is a formal document that records the categorization
        decision per CCN-STIC 803.
        """
        dims_table = "\n".join(
            f"| {code} | {DIMENSIONS[code]['name']} | "
            f"{result.dimension_assessments[code].value} | "
            f"{DIMENSIONS[code]['description'][:80]}... |"
            for code in ["D", "I", "C", "A", "T"]
        )

        acta = f"""# ACTA DE CATEGORIZACIÓN DEL SISTEMA — E-012

**Proyecto:** {project_name}
**Sistema:** {system_name}
**Fecha:** {date.today().isoformat()}
**Categoría resultante:** {result.category.value}

---

## 1. OBJETO

El presente documento constituye el Acta de Categorización del sistema de
información conforme al Anexo I del Real Decreto 311/2022, de 3 de mayo,
por el que se regula el Esquema Nacional de Seguridad.

## 2. VALORACIÓN POR DIMENSIONES DE SEGURIDAD

| Dimensión | Nombre | Nivel | Descripción |
|---|---|---|---|
{dims_table}

## 3. CATEGORÍA RESULTANTE

{result.justification}

## 4. BASE NORMATIVA

La categorización se realiza conforme a:
- Real Decreto 311/2022, Anexo I — Categorías de los sistemas
- CCN-STIC 803 — Valoración de sistemas en el ENS

{f'''### Cita del corpus normativo

{rag_citation}
''' if rag_citation else ''}

## 5. APROBACIÓN

El presente acta ha sido aprobado por el Responsable de la Seguridad
del sistema de información.

---
*Documento generado automáticamente por FULKRO Motor 1 (Categorization Engine)*
"""
        return acta
