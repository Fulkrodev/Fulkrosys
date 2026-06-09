# FULKRO Pricing Canonical · 2026-05-24

**Status**: ARCHITECT-VALIDATED · supersedes Apéndice M spec v2.1/v2.2 base values
**Capture date**: 2026-05-24 (Bloque 6 Pricing Canonical phase)
**Validated by**: Marcos (marcosmata@fulkro.es) · 2026-05-24

---

## ENS Categorías · implantación (proyecto fijo)

| Categoría | Baseline catálogo | Ceiling sector complejo | Plazo típico | Audit externo |
|-----------|-------------------|------------------------|--------------|---------------|
| **Básica** | **3.900€** | 4.500€ | 2-4 semanas implantación | NO (autoevaluación CCN-STIC 809) |
| **Media** | **11.500€** | 14.000€ | 2-4 semanas implantación (+ 8-16 sem total con ENAC) | SÍ ENAC obligatorio (cost cliente aparte) |
| **Alta** | **22.000€** | 30.000€ | 4-6 semanas implantación (+ 12-20 sem total con ENAC) | SÍ ENAC obligatorio + SOC + DR + monitorización 24/7 |

> **NOTA · precio del PRIMER PILOTO MEDIA** · El **primer piloto MEDIA se cotiza a 9.500€** (decisión de negocio,
> coincide con la misión pre-piloto). **11.500€ es el canónico de catálogo general** para Media.
> El código (`backend/app/core/pricing/rules.py` → `BASE_PRICES`) cotiza **9.500€** al cliente del piloto
> **a propósito**: es el precio que entra en la propuesta project-scoped (`generate_proposal_apendice_m`) y
> en el contrato que firma el cliente (`generate_contract_apendice_m`). `BASE_PRICES_CANONICAL` conserva el
> 11.500€ como objetivo de catálogo general post-migración (vía Pricing Engine futuro). **No es una
> contradicción ni deuda**: son dos números con propósito distinto (piloto vs catálogo general).

## Retainers post-certificación (mensual)

| Tier | Rango | Target cliente | Inclusiones core |
|------|-------|----------------|------------------|
| **R_BÁSICO** | **700-900€/mes** | Post-Básica · pyme <25 usuarios | Mantenimiento autoevaluación · vigilancia CCN-CERT · reporte trimestral |
| **R_MEDIO** | **1.500-2.500€/mes** | Post-Media · pyme 25-150 usuarios | Monitorización + audits seguimiento + CISO externo + vuln semanal |
| **R_ALTO** | **3.000-5.000€/mes** | Post-Alta · 150+ usuarios · multi-sede | SOC liaison + DR drills + audit annual + pentest anual + red team |

## Exclusiones explícitas (NO incluidas en precio FULKRO)

- **Auditoría externa ENAC** · obligatorio Media/Alta · responsabilidad cliente · ~3-8k€ Media · ~8-15k€ Alta
- **Hardware/software licensing** · WAF · EDR · SIEM · backup infra · responsabilidad cliente
- **Hosting/cloud** · cliente paga directly su provider
- **Penetration testing externo** · si exigido por sector · cliente contrata empresa especializada
- **Formación in-house** · pertenece a R_MEDIO+ retainer (R_BÁSICO solo vigilancia · NO formación)

## Posicionamiento competitivo

- **Más barato que midpoint Audidat** (líder competidor):
  - Audidat Básica: 3-8k€ · FULKRO 3.900€ (lower-mid)
  - Audidat Media: 8-18k€ · FULKRO 11.500€ (mid)
  - Audidat Alta: 18k€+ · FULKRO 22.000€ baseline (mid)
- **NO regalado · serio · auditor-ready** · plataforma + automation differentiator
- **Diferenciadores FULKRO**:
  1. Plataforma propia (vs consultor pure-service)
  2. Cloud remediation feature event-driven (Bloque 3+5)
  3. Monitoring multi-tenant (Bloque 4)
  4. Dossier auto-generated 100% production-grade M9 + M27 wire (Future-dossier-pack)
  5. Workflow cross-actor sync ultra-sincronizado (1.D.G EXPANDED)
  6. Cloud-first architecture (1.D.X · 5 motores K-full · ADR-053)

## Adjustment factors (Pricing Engine · Future-1.E.pricing-intelligence-engine)

Cuando Pricing Engine motor se construya post-piloto · estos factores aplicables sobre baseline:

- **Sector complexity multiplier**:
  - Sanidad/Finanzas/AAPP críticas: **1.2-1.4x** (alto cumplimiento + scrutiny ENAC)
  - Industria/Servicios estándar: **1.0x** baseline
  - Comercio/Retail básico: **0.9x** (descuento ligero · low complexity)

- **Madurez digital discount**:
  - ISO 27001 previo certificado: **0.85x** (15% descuento · 70-80% controles ya implementados)
  - Sin ISO previo · cero docs: **1.0x** baseline
  - Madurez L0/L1 (M22 diagnosis_score <30%): **1.15x** (extra effort docs from scratch)

- **Tamaño empresa adjustment**:
  - Por sistema adicional en alcance: **+1.200€** baseline (TBD post-engine impl real testing)
  - Por sede adicional: **+1.500€** baseline
  - Por sector regulado multi-aplicación: **+2.000€** baseline

- **Plazo urgencia surcharge**:
  - <6 semanas plazo desde firma: **+30% surcharge** (urgencia · M13 quick scan + acelerado)
  - 6-10 semanas: baseline 1.0x
  - >12 semanas planificado: ligero descuento posible negociado caso a caso

## Comparativa estado legacy (honesty notes)

**Discrepancias detectadas durante captura canonical 2026-05-24**:

| Fuente | BASICA | MEDIA | ALTA | Status |
|--------|--------|-------|------|--------|
| **Canónico catálogo general (architect-validated)** | **3.900€** | **11.500€** | **22.000€** | ✅ CURRENT · objetivo catálogo / `BASE_PRICES_CANONICAL` |
| `backend/app/core/pricing/rules.py` → `BASE_PRICES` (path que firma el cliente) | 3.900€ | **9.500€** | 25.000€ | ✅ INTENCIONAL · 9.500€ es el precio del primer piloto MEDIA (ver NOTA arriba) · NO cambiar pre-piloto |
| `backend/app/motors/m13_commercial/pricing_service.py` → `PRICING_CATALOG` (v2.1) | 6.500€ | 22.000€ | 48.000€ | 🔴 LEGACY · path ALTERNO que NO alimenta propuesta/contrato del piloto · Future-1.E.pricing.migrate-m13-legacy |
| `backend/app/motors/m23_retainer/pricing_catalog_seed.py` (2026-04-21) | 5.500€ | 9.500€ | n/a | 🔴 LEGACY · Future-1.E.pricing.migrate-m23-retainer-canonical |

> **Aclaración path client-facing (verificado empíricamente 2026-06-08)**: la propuesta project-scoped y el
> contrato que firma el cliente usan `generate_proposal_apendice_m` → `PricingCalculator` → `BASE_PRICES`
> (**MEDIA = 9.500€**). El `PRICING_CATALOG` de `pricing_service.py` (`media_hitos` base 22.000€) es un path
> **distinto** (endpoint legacy `POST /projects/{id}/proposals/generate`) que NO alimenta la propuesta ni el
> contrato del piloto. Caveat residual: `regenerate_for_categoria` (usado solo en elevación de suelo AAPP `#5`,
> N2) sí pasa por el path `PRICING_CATALOG` — fuera de alcance de este fix, sin tocar código.

**Action items Future**:
- **Future-1.E.pricing.migrate-m13-legacy** · update `pricing_service.py` PRICING_CATALOG values to canonical + tests update (~2-3h)
- **Future-1.E.pricing.migrate-m23-retainer-canonical** · update `pricing_catalog_seed.py` to canonical R_BÁSICO/R_MEDIO/R_ALTO names + values (~1-2h)
- **Future-1.E.pricing-intelligence-engine** · build dynamic Pricing Engine motor with adjustment factors (~10-15h post-piloto)
- **Future-1.E.pricing.tests-update-canonical** · update existing M13/M14/M15 tests that assert legacy values (~1-2h)

## Cross-references

- **Spec original**: `docs/spec/ENS_PLATFORM_MASTER_SPEC_v2.1 (2).md` Apéndice M
- **Backend canonical**: `backend/app/core/pricing/rules.py` BASE_PRICES
- **Retainer seed**: `backend/app/motors/m23_retainer/pricing_catalog_seed.py`
- **CLAUDE.md reference**: sección "Pricing Canonical (2026-05-24 validated)"
- **ADR**: futuro ADR-055 Pricing Engine cuando motor real construido

## Reglas materializadas

- **R1 INVIOLABLE** sostenida: pricing deterministic · NO LLM promote · adjustment factors via Engine futura serán pure functions
- **R32 v3.11** sostenida: scope-out Pricing Engine pre-piloto · canonical doc + constants suficientes · build motor demand-driven post-piloto
- **ADR-025** sostenida: NO new tables · canonical constants en `backend/app/core/pricing/rules.py` existing + retainer seed existing
- **OPS-049 honesty path**: discrepancias legacy capturadas explícitamente · NO silent overwrite · Future-X items captured cross-referenced
