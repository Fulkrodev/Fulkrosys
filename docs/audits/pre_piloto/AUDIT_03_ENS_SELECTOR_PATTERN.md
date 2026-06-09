# AUDIT #2 · ENS selector pattern como ENS Radar

**Status**: ✅ Audit empírico completo · Bloque 1 Mega-baseline item 3/11
**Date**: 2026-05-24
**Scope item**: pre-piloto #2 · "ENS selector pattern · como tiene ENS Radar"

---

## Verdict empírico

**ENS Radar** usa patrón **multi-filter table-based selector** (LeadsTable.tsx · 7 temperaturas + estado chips + búsqueda + multinacional toggle · 100% client-side filter sobre página cargada). **ProjectSwitcherDropdown** (1.E.2 admin) usa patrón **dropdown navigation switcher** (DropdownMenu shadcn/ui · click trigger → lista clients accesibles · navigate URL).

**Gap específico identificado**: NO existe selector unificado tipo "ENS Category Filter" cross-cliente (BÁSICA/MEDIA/ALTA) consistente. Patrones distintos según contexto:
- ENS Radar: filters tabla leads
- ProjectSwitcher: navigation entre clients
- ENS Category: scattered en distintos componentes per-motor

**ETA empírico realista refined**: ~3-6h si unificación necesaria · pero **PROBABLE SCOPE-OUT** si Marcos clarifica que necesita es feature-specific filter (no genérico).

---

## Patterns identificados existing

### Pattern 1 · ENS Radar LeadsTable (multi-filter table)
- File: `frontend/components/ens-radar/LeadsTable.tsx`
- 7 temperaturas (vence_pronto · ardiendo_sostenido · ardiendo · caliente · tibio · frio · ya_certificada)
- Estado chips multi-select (nuevo · limbo · aprobado · descartado)
- Búsqueda CIF/nombre input
- Toggle "Ver multinacionales" (icp_passed)
- **Filtering client-side** sobre página cargada (limit=2000)
- Cement FASE 4 · accionables primero (Nuevo + Limbo defaults)

### Pattern 2 · ProjectSwitcherDropdown (1.E.2 admin navigation)
- File: `frontend/components/layout/ProjectSwitcherDropdown.tsx`
- DropdownMenu shadcn/ui
- `useClients()` hook · 1 client ≈ 1 project típico (piloto MEDIA)
- Navigate URL pattern (`/admin/projects/{slug}/dashboard`)
- Embedded en ActiveProjectBanner header
- ADR-054 project-scoped admin UX

### Pattern 3 · ENS Category scattered (per-motor)
- M01 Categorization · BÁSICA/MEDIA/ALTA picker
- M03 DdA · estado filter (pendiente · in_progress · implementada · etc)
- M27 Conformity · marco filter
- **NO selector unificado** · cada motor ad-hoc

---

## Interpretación gap "ENS selector como ENS Radar"

### Hipótesis A · Marcos quiere selector temperaturas tipo ENS Radar PERO para otra entidad (clients · projects · medidas)
- ETA: ~2-4h adaptar LeadsTable pattern · NO new component
- Probable target: "Categories dashboard" cross-cliente filterable
- Use case poco claro pre-piloto MEDIA (admin solo)

### Hipótesis B · Marcos quiere unify project + client + category selectors en sidebar
- ETA: ~5-8h refactor sidebar + navigation
- Conflict con 1.E.2 ADR-054 just-completed
- Risk: regresión sidebar simplificación 1.D.F.bis.III

### Hipótesis C · Marcos quiere portal-style "ENS Selector" como navigation primary entre 3 categorías (BÁSICA/MEDIA/ALTA)
- ETA: ~3-5h new top-level nav
- Use case: Marcos comercial muestra portal por categoría target
- Probable pero NO confirmado

---

## Recomendación

**STOP-AND-CLARIFY architect** · gap interpretación ambiguo · ETA 2-8h depending hipótesis.

**Default pre-piloto (si NO clarification)**: scope-out PERMANENT · cada selector ad-hoc (per-motor) actualmente sirve · refactor unification riesgo regresión >> beneficio inmediato.

**Future-1.E.ens-selector-pattern-unification** capturado:
- ETA empírico ~3-6h
- Pre-condición: Marcos clarifica hipótesis A/B/C
- Post-piloto demand-driven cuando 2do cliente onboarding emerge real need

---

## Cross-ref

- ENS Radar selector: `frontend/components/ens-radar/LeadsTable.tsx`
- Project switcher: `frontend/components/layout/ProjectSwitcherDropdown.tsx`
- ADR-054 Project-Scoped Admin UX (1.E.2)
- 1.D.F.bis.III sidebar refactor 14→10 entries (recent)

---

## Honest notes

1. Gap interpretación ambiguo · audit no resuelve sin Marcos clarification
2. 3 hipótesis distintas · ETA 2-8h range amplio
3. Recomendación default scope-out es honest path · NO refactor especulativo
