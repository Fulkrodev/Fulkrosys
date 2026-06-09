"""Measure Translation Service · CLUSTER 3 Phase 3C gap translation layer.

Sesión 3B-2B.8 CLUSTER 3 Phase 3C · canonical translation function reusable
cross-motors (DdA + Evidence + Controls + Cloud gaps).

R1 sostained: pure functional · NO LLM · NO HTTP · NO side-effects · deterministic.
Returns MeasureTranslation dataclass.

Filosofía cliente-mínimo R29/R30:
- Admin VE technical detail (codigo · familia · fuente_oficial · descripcion)
- Cliente VE cliente-friendly title + explanation primer-principios (NO ENS lingo)
- Same source data (ens_measures) · single function returns both audiences

Pattern: curated TRANSLATION_OVERRIDES dict (high-frequency measures Marcos
expertise) + graceful fallback ens_measures.nombre + descripcion para
non-curated codes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.ens import EnsMeasure


@dataclass(frozen=True)
class MeasureTranslation:
    """Canonical measure translation result (deterministic R1)."""

    measure_code: str
    nombre: str                       # ENS official name (admin)
    cliente_friendly_title: str        # R29 Spanish (cliente)
    cliente_friendly_explanation: str  # primer-principios cliente
    admin_technical_detail: str        # Marcos technical detail
    familia: Optional[str] = None
    categoria_minima: Optional[str] = None
    fuente_oficial: Optional[str] = None
    has_curated_override: bool = False

    def to_admin_dict(self) -> dict:
        """Full detail · admin audience."""
        return {
            "measure_code": self.measure_code,
            "nombre": self.nombre,
            "cliente_friendly_title": self.cliente_friendly_title,
            "cliente_friendly_explanation": self.cliente_friendly_explanation,
            "admin_technical_detail": self.admin_technical_detail,
            "familia": self.familia,
            "categoria_minima": self.categoria_minima,
            "fuente_oficial": self.fuente_oficial,
            "has_curated_override": self.has_curated_override,
        }

    def to_cliente_dict(self) -> dict:
        """Cliente-friendly only · R29 firmísimo · NO admin_technical_detail leak."""
        return {
            "measure_code": self.measure_code,
            "cliente_friendly_title": self.cliente_friendly_title,
            "cliente_friendly_explanation": self.cliente_friendly_explanation,
            "categoria_minima": self.categoria_minima,
        }


# ════════════════════════════════════════════════════════════════════
# Curated translation overrides · high-frequency measures Marcos expertise
# Expandable demand-driven post-piloto (Future-1.E.translation-overrides-expand)
# ════════════════════════════════════════════════════════════════════

TRANSLATION_OVERRIDES: dict[str, dict[str, str]] = {
    "op.acc.5": {
        "cliente_friendly_title": "Cuentas y contraseñas seguras",
        "cliente_friendly_explanation": (
            "Cada persona debe tener su cuenta única con una contraseña "
            "robusta. Esto evita que alguien acceda con credenciales "
            "compartidas o adivinables."
        ),
    },
    "op.acc.6": {
        "cliente_friendly_title": "Inicio de sesión seguro (MFA)",
        "cliente_friendly_explanation": (
            "Los usuarios con acceso administrativo deben usar un segundo "
            "paso al iniciar sesión (por ejemplo, un código de móvil). "
            "Así, aunque alguien obtenga la contraseña, no podrá entrar."
        ),
    },
    "op.acc.4": {
        "cliente_friendly_title": "Permisos según el rol",
        "cliente_friendly_explanation": (
            "Cada persona accede solo a lo que necesita para su trabajo. "
            "Esto reduce el riesgo si una cuenta es comprometida."
        ),
    },
    "mp.s.4": {
        "cliente_friendly_title": "Antivirus en equipos y servidores",
        "cliente_friendly_explanation": (
            "Todos los equipos críticos deben tener antivirus activo y "
            "actualizado. Te ayuda a detectar amenazas antes de que "
            "causen problemas."
        ),
    },
    "mp.s.5": {
        "cliente_friendly_title": "Análisis automático de archivos subidos",
        "cliente_friendly_explanation": (
            "Cuando se sube un archivo a la plataforma, lo analizamos "
            "automáticamente buscando virus o contenido malicioso."
        ),
    },
    "org.4": {
        "cliente_friendly_title": "Política de seguridad firmada",
        "cliente_friendly_explanation": (
            "Tu organización debe tener un documento aprobado donde se "
            "establecen las reglas básicas de seguridad. Tú firmas que "
            "lo aplicarás, sin prisa por tu parte."
        ),
    },
    "mp.info.6": {
        "cliente_friendly_title": "Copias de seguridad (backup)",
        "cliente_friendly_explanation": (
            "Tener copias de seguridad de la información crítica te "
            "permite recuperarte rápido en caso de incidente, fallo "
            "de hardware o ransomware."
        ),
    },
    "op.cont.2": {
        "cliente_friendly_title": "Plan de continuidad ante incidentes",
        "cliente_friendly_explanation": (
            "Si algo grave pasa (incidente, fallo, ataque), tener un plan "
            "claro acelera la recuperación y reduce el impacto en tu negocio."
        ),
    },
    "op.exp.2": {
        "cliente_friendly_title": "Configuración base de seguridad",
        "cliente_friendly_explanation": (
            "Los sistemas se configuran con valores seguros desde el "
            "principio · sin opciones innecesariamente abiertas o débiles."
        ),
    },
    "mp.com.4": {
        "cliente_friendly_title": "Comunicaciones cifradas",
        "cliente_friendly_explanation": (
            "La información viaja cifrada (HTTPS, VPN) por las redes. "
            "Así nadie puede leerla en tránsito."
        ),
    },
    "op.mon.1": {
        "cliente_friendly_title": "Detección de eventos sospechosos",
        "cliente_friendly_explanation": (
            "Monitorizamos los eventos clave en sistemas para detectar "
            "accesos extraños o actividad sospechosa lo antes posible."
        ),
    },
    "mp.per.1": {
        "cliente_friendly_title": "Personas autorizadas claramente",
        "cliente_friendly_explanation": (
            "Las personas con acceso a información sensible están "
            "claramente identificadas y autorizadas formalmente."
        ),
    },
    "mp.per.3": {
        "cliente_friendly_title": "Formación en seguridad para tu equipo",
        "cliente_friendly_explanation": (
            "Tu equipo recibe formación periódica de concienciación en "
            "ciberseguridad. La mayoría de incidentes empieza con una "
            "decisión humana."
        ),
    },
}


# Familia → cliente-friendly category description (fallback aid)
FAMILIA_HINTS_CLIENTE: dict[str, str] = {
    "org": "organización y reglas internas",
    "op.acc": "control de accesos",
    "op.exp": "operación de sistemas",
    "op.mon": "monitorización",
    "op.cont": "continuidad y recuperación",
    "mp.if": "instalaciones y entorno físico",
    "mp.per": "personas y formación",
    "mp.s": "protección de software",
    "mp.info": "protección de la información",
    "mp.com": "protección de las comunicaciones",
    "mp.eq": "protección de equipos",
}


def _build_cliente_friendly_fallback(
    measure: EnsMeasure,
) -> tuple[str, str]:
    """Build R29 friendly title + explanation desde ens_measures (NO override).

    Returns (cliente_friendly_title, cliente_friendly_explanation).
    """
    nombre = (measure.nombre or measure.codigo).strip()
    familia_hint = FAMILIA_HINTS_CLIENTE.get(measure.familia or "", "")

    cliente_title = nombre

    descripcion_safe = (measure.descripcion or "").strip()
    if descripcion_safe:
        cliente_explanation = (
            f"{descripcion_safe[:400]}"
            + ("..." if len(descripcion_safe) > 400 else "")
        )
    else:
        if familia_hint:
            cliente_explanation = (
                f"Esta medida del marco ENS aplica a tu proyecto en el "
                f"ámbito de {familia_hint}. Marcos te explica los detalles "
                "en el panel si tienes dudas."
            )
        else:
            cliente_explanation = (
                "Esta medida del marco ENS aplica a tu proyecto. Marcos "
                "te explica los detalles en el panel si tienes dudas."
            )

    return cliente_title, cliente_explanation


async def translate_measure_to_cliente_friendly(
    db: AsyncSession,
    measure_code: str,
) -> Optional[MeasureTranslation]:
    """Canonical translation function · pure functional R1.

    1. Lookup ens_measures por codigo
    2. Apply curated TRANSLATION_OVERRIDES si existe
    3. Fallback safe desde ens_measures.nombre + descripcion + familia_hint
    4. Returns MeasureTranslation o None si measure_code not found

    Args:
      db: AsyncSession
      measure_code: ENS codigo (ej "op.acc.6")

    Returns MeasureTranslation con admin + cliente fields, o None.
    """
    if not measure_code or not measure_code.strip():
        return None

    code_clean = measure_code.strip()

    measure = (await db.execute(
        select(EnsMeasure).where(EnsMeasure.codigo == code_clean)
    )).scalar_one_or_none()

    if measure is None:
        return None

    nombre = measure.nombre or code_clean
    descripcion = measure.descripcion or ""

    override = TRANSLATION_OVERRIDES.get(code_clean)
    if override is not None:
        cliente_title = override["cliente_friendly_title"]
        cliente_explanation = override["cliente_friendly_explanation"]
        has_override = True
    else:
        cliente_title, cliente_explanation = _build_cliente_friendly_fallback(
            measure,
        )
        has_override = False

    admin_detail_parts = [
        f"ENS codigo: {code_clean}",
        f"Nombre: {nombre}",
    ]
    if measure.familia:
        admin_detail_parts.append(f"Familia: {measure.familia}")
    if measure.categoria_minima:
        admin_detail_parts.append(f"Categoría mínima: {measure.categoria_minima}")
    if measure.fuente_oficial:
        admin_detail_parts.append(f"Fuente: {measure.fuente_oficial}")
    if descripcion:
        admin_detail_parts.append(f"Descripción: {descripcion}")

    admin_technical_detail = " · ".join(admin_detail_parts)

    return MeasureTranslation(
        measure_code=code_clean,
        nombre=nombre,
        cliente_friendly_title=cliente_title,
        cliente_friendly_explanation=cliente_explanation,
        admin_technical_detail=admin_technical_detail,
        familia=measure.familia,
        categoria_minima=measure.categoria_minima,
        fuente_oficial=measure.fuente_oficial,
        has_curated_override=has_override,
    )
