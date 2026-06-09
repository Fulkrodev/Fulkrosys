# AUDIT #1 · Frontend polish a muerte

**Status**: ✅ Audit empírico completo · Bloque 1 Mega-baseline item 11/11
**Date**: 2026-05-24
**Scope item**: pre-piloto #1 · "Frontend polish a muerte · UX consistency · design quality"

---

## Verdict empírico

**Frontend Next.js 14 es MASSIVE production-grade**:
- **129 pages.tsx** activas (admin + cliente + radar + portal pentester)
- **363 components TSX** distribuidos en domain-specific (admin · client · radar · ens-radar · m14_contracts · m28_change_governance · etc)
- **28 design system components** UI primitives (button · card · dialog · table · skeleton · etc · shadcn/ui based)
- **R29 firmísimo cliente portal** (1.D.F.bis.III refactor "indispensable-only" · sidebar 14→10 · banners simplified)
- **R30 admin tutor** sostained (CopilotoAdminSidebar · WorkflowBlockersPanel · screen-aware copiloto 38 screens catalog)

**Gap específico identificado**: polish scope es **subjective / quality-of-life** vs structural · NO bloqueador funcional cliente piloto MEDIA. UX consistency mostly OK · pero design system iteration could improve:
- Empty states consistency across 129 pages (some custom · some EmptyState shared)
- Loading skeleton patterns variation
- Error boundary coverage cliente portal (R29 friendly)
- Mobile responsive cliente (R29 sostained 1.D.F.bis.III)
- Color tokens consistency · accessibility WCAG AA contrast

**ETA empírico realista refined**:
- **Quick wins iterativos** (~10-15h): empty states + skeleton consistency + error boundaries
- **Major refactor design system** (~25-35h): NOT recommended pre-piloto · churn riesgo regresiones
- **Mobile responsive cliente polish** (~5-8h): R29 cement sostained · audit pequeño per page
- **Total recomendado pre-piloto**: ~15-25h iterative quick wins (vs ~25-30h nominal major refactor)

---

## Stats baseline

### Pages 129
- `/(admin)/admin/*` ~70 pages · workflow command center + projects/[id]/* + cross-cliente top-level
- `/(client-portal)/client-portal/*` 28 pages (per Audit #4 · indispensable-only refactor)
- `/(radar)/radar/*` 4 pages (ENS Radar portal separado · per Audit #1)
- `/(portal)/pentester-portal/*` (per find · external pentester partner)
- Others: auth · login · public

### Components 363 TSX total
- Domain-specific: m14_contracts · m28_change_governance · m_cloud_connectors · m19_risk · m22_discovery · m21_portal_cliente · etc
- Cross-domain: workflow (WorkflowBlockersPanel + WorkflowTimelineAdmin + StepCardEnriched) · copilot (CopilotoAdminSidebar + CopilotoClienteBottomRight + screen-aware) · navigation (Sidebar · Breadcrumb · ProjectSwitcherDropdown · ActiveProjectBanner)
- Recent FASE C: SubcontractsPanel + AdendaRow expandable

### Design system 28 UI primitives (shadcn/ui based)
- Layout: card · table · sheet · dialog · tabs · skeleton · stepper · scan-status-badge
- Input: button · input · textarea · select · switch · label
- Feedback: alert · empty-state · EmptyStateUpcoming · badge · progress · tooltip · tooltip-ens · info-tag
- Navigation: dropdown-menu · popover · avatar
- Data: data-table · data-table-pagination · data-table-skeleton

### Recent polish refactors (cumulative)
- 1.D.F.bis.III · cliente portal indispensable-only refactor (6 commits)
- 1.D.G EXPANDED · workflow cross-actor + real-time sync + UI blockers
- 1.E.2 · Project-Scoped Admin UX (ADR-054 · ActiveProjectBanner + breadcrumb)
- 1.E.2.bis · multi-tenant per-cliente personalización (branding)
- FASE B · prompt caching admin observability
- FASE C · contracts SubcontractsPanel + audit trail UI

---

## Gap categories empírico

### Category 1 · Empty states consistency
- Some pages use `EmptyState` shared component
- Some pages custom inline empty
- **ETA**: ~3-5h sweep + standardize · low risk · iterative quick win

### Category 2 · Loading skeleton variation
- Some pages use `Skeleton` shared
- Some pages use ad-hoc spinners (Loader2)
- **ETA**: ~2-3h sweep + standardize · low risk

### Category 3 · Error boundary cliente portal R29
- Some pages handle errors via Alert
- Cliente portal R29 cement: friendly error messages NUNCA presión
- Gap: error boundary global cliente missing OR partial
- **ETA**: ~2-3h cliente portal error boundary global + per-page R29 friendly messages

### Category 4 · Mobile responsive cliente
- 1.D.F.bis.III refactor + R29 sostained mobile-friendly
- NO comprehensive audit per page · sample-based assumption
- **ETA**: ~5-8h sample 10-15 pages cliente + adjust grid breakpoints

### Category 5 · Color tokens + WCAG AA accessibility
- Design tokens defined in Tailwind config + CSS variables
- Accessibility audit NO ejecutado recently
- **ETA**: ~3-5h Lighthouse audit + adjust contrast critical pages cliente

### Category 6 · Major refactor design system (NOT recommended pre-piloto)
- shadcn/ui upgrade · component prop refactor cross-codebase
- Risk: regresiones cross-componentes 363 archivos
- **ETA**: ~25-35h · Future-1.F demand-driven post-piloto

---

## Recomendación

**Pre-piloto quick wins iterativos (~10-15h)**:
1. **HIGH** (~3-5h): Empty states sweep + standardize cross 129 pages
2. **HIGH** (~2-3h): Loading skeleton sweep + standardize
3. **MEDIUM** (~2-3h): Error boundary cliente portal R29 friendly
4. **MEDIUM** (~3-5h): WCAG AA accessibility audit + adjust critical pages

**Defer post-piloto demand-driven**:
- Mobile responsive cliente exhaustive (~5-8h · 1.D.F.bis.III base sufficient)
- Major design system refactor (~25-35h · Future-1.F)

**Total pre-piloto recomendado**: ~10-15h iterative · NO major refactor.

---

## Cross-ref

- Pages: `frontend/app/`
- Components: `frontend/components/`
- Design system: `frontend/components/ui/`
- Recent refactors cumulative reference: CLAUDE.md sub-atoms 1.D.F.bis.III · 1.D.G · 1.E.2 · 1.E.2.bis · FASE B · FASE C
- shadcn/ui base
- Tailwind config + CSS tokens

---

## Honest notes

1. NO inspección per page exhaustiva · sample-based + structure metrics
2. Quality assessment subjective · Marcos puede priorizar diferentes categories
3. ETA ranges amplios depending priority Marcos
4. Major refactor design system FIRMÍSIMO defer post-piloto (churn risk · 363 components blast radius)
