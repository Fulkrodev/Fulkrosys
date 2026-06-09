"""FULKRO core pricing module.

Transversal a M13 Propuestas, M14 Contratos y M15 Billing. Encapsula
las reglas oficiales de pricing del Apendice M spec v2.2:

- Precios base por categoria: BASICA 3.900, MEDIA 9.500, ALTA 25.000+.
- Extras deterministas para MEDIA (sector_regulado, multi_ubicacion,
  madurez_l0_l1, sistemas_adicionales).
- Hitos oficiales: 3 hitos Basica (30/40/30), 5 hitos Media
  (26/21/21/21/11), 7 hitos Alta.
- Retainer tiers R_MICRO..R_CRITICAL con SLA y cuota mensual.
- Bolsa flex con tramos de descuento por volumen.
- Recargo urgencia +30% si plazo <6 semanas.
- Quick scan 1.500 EUR + 100% descontable si firma C-001.
- Auditoria interna: 2.500 Basica / 5.500 Media.

Paso 6 conecta esto extremo a extremo con templates P-001, C-001, C-003
y facturas milestone + bolsa + quick_scan + audit.
"""
from backend.app.core.pricing.calculator import (  # noqa: F401
    ImplantacionPricing,
    PricingCalculator,
    RetainerPricing,
    BolsaPricing,
    MilestonePricing,
    PricingError,
)
from backend.app.core.pricing.rules import (  # noqa: F401
    BASE_PRICES,
    EXTRAS_IMPLANTACION_MEDIA,
    SECTORES_REGULADOS,
    HITOS_BASICA,
    HITOS_MEDIA,
    HITOS_ALTA,
    BOLSA_FLEX_TIERS,
    RETAINER_TIERS,
    URGENCY_SURCHARGE_PCT,
    URGENCY_THRESHOLD_DAYS,
    QUICK_SCAN_PRICE,
    AUDIT_INTERNA_PRICES,
)
