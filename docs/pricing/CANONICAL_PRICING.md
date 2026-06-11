# FULKRO Pricing Canonical · UNIFICADO 2026-06-11

**Status**: FUENTE ÚNICA · un solo juego de precios en todo el sistema (no hay precios "sombra").
**Validated by**: Marcos (matagarciamarcos@gmail.com)
**Fuente de verdad editable**: tabla `pricing_config` (BD) · editable desde `/admin/settings/pricing`.

---

## Principio: una sola fuente, propagación total

Editar el precio en `/admin/settings/pricing` lo cambia **en todo el sistema**:

```
pricing_config (BD, editable)
   │  refresh_pricing_from_db (arranque) + set_pricing_config (edición admin)
   ▼
rules.BASE_PRICES  ==  rules.BASE_PRICES_CANONICAL   (mutación in-place)
   ├──► PricingCalculator (propuesta apéndice M · contrato · factura · agents 19/20)
   ├──► m13 PRICING_CATALOG  (deriva el base de get_base_prices() · ya NO hay 22.000 hardcoded)
   └──► m23 pricing_catalog (tabla · set_pricing_config la actualiza también)
```

No quedan números divergentes. La migración `unify_pricing_fiscal_rls_001` alineó la
tabla `pricing_catalog` y los tests fijan los mismos valores.

## ENS Categorías · implantación (proyecto fijo)

| Categoría | Precio (fuente única) | Ceiling sector complejo | Plazo implantación | Audit externo |
|-----------|-----------------------|-------------------------|--------------------|---------------|
| **Básica** | **3.200€** | 4.500€ | 2-4 semanas | NO (autoevaluación CCN-STIC 809) |
| **Media** | **10.700€** | 13.000€ | 2-4 sem (+ 8-16 sem total con ENAC) | SÍ ENAC obligatorio (coste cliente aparte) |
| **Alta** | **22.800€** | 28.000€ | 4-6 sem (+ 12-20 sem total con ENAC) | SÍ ENAC + SOC + DR + monitorización 24/7 |

> Estos valores = `pricing_config` (BD) = `rules.BASE_PRICES` = `rules.BASE_PRICES_CANONICAL`.
> Para cambiarlos: `/admin/settings/pricing` (se propagan solos · no tocar constantes a mano).

### Extras implantación MEDIA (aditivos sobre el base)

| Extra | Importe |
|-------|--------:|
| Sector regulado (sanidad/banca/fintech/energía…) | +2.000€ |
| Multi-ubicación (>1 sede) | +1.500€ |
| Madurez inicial L0/L1 (diagnóstico <30%) | +2.500€ |
| Por sistema adicional en alcance (>1) | +1.200€ |
| Urgencia (<6 semanas desde firma) | +30% |

## Retainers post-certificación (mensual · 5 tiers · fuente única `RETAINER_TIERS` = `pricing_catalog`)

| Tier (código) | Cuota/mes | Target cliente | Inclusiones core |
|---------------|----------:|----------------|------------------|
| **R_MICRO** | **150€** | Post-Básica · vigilancia mínima | Vigilancia CCN-CERT + reporte trimestral + comité semestral |
| **R_LITE** | **300€** | Micro/pyme ≤25 usuarios | Comité semestral + auditoría interna anual + vuln mensual · SLA 72h |
| **R_STD** | **700€** | Media · pyme 26-150 usuarios | Comité trimestral + CISO externo + vuln semanal · SLA 48h · **base del negocio** |
| **R_PLUS** | **1.200€** | Media complejo / Alta | Comité mensual + pentest anual + phishing trimestral · SLA 24h |
| **R_CRITICAL** | **3.000€** | Alta / infra crítica | SOC + DR drills + pentest + auditoría anual · SLA 8h 24/7 |

> Extra sector regulado +300€/mes desde R_PLUS. El número **único** de R_STD es **700€** (antes
> había una divergencia 400€ en `rules.py` vs 700€ en el catálogo · resuelta).

## Exclusiones explícitas (NO incluidas en precio FULKRO)

- **Auditoría externa ENAC** · obligatorio Media/Alta · responsabilidad cliente · ~3-8k€ Media · ~8-15k€ Alta
- **Hardware/software licensing** · WAF · EDR · SIEM · backup infra · responsabilidad cliente
- **Hosting/cloud** · cliente paga directamente a su proveedor
- **Pentesting externo** · si lo exige el sector · cliente contrata empresa especializada
- **Formación in-house** · pertenece a R_STD+ (R_MICRO/R_LITE solo vigilancia)

## Posicionamiento competitivo (vs Audidat, líder)

- Audidat Básica 3-8k€ · **FULKRO 3.200€** (lower) · Audidat Media 8-18k€ · **FULKRO 10.700€** (mid)
- Audidat Alta 18k€+ · **FULKRO 22.800€** (mid). Serio · auditor-ready · plataforma propia + automation.

## Source-of-truth (código)

- **Constantes**: `backend/app/core/pricing/rules.py` → `BASE_PRICES` / `BASE_PRICES_CANONICAL` / `RETAINER_TIERS`
- **Fuente editable**: tabla `pricing_config` (BD) · `backend/app/core/pricing/repository.py`
- **Catálogo comercial**: `backend/app/motors/m13_commercial/pricing_service.py` (deriva de la fuente única)
- **Catálogo retainer/billing**: `backend/app/motors/m23_retainer/pricing_catalog_seed.py`
- **Migración de unificación**: `backend/migrations/versions/unify_pricing_fiscal_rls_001.py`

## Reglas materializadas

- **R1 INVIOLABLE**: pricing determinista · NO LLM. Los extras/ajustes son funciones puras.
- **Fuente única**: editar en `/admin/settings/pricing` propaga a TODOS los consumidores (sin precios sombra).
- **ADR-025**: sin tablas nuevas · `pricing_config` existente es la fuente editable.
