# ADR-054 · Project-Scoped Admin UX · Active Project Context Pattern

**Status**: Accepted · 2026-05-23 (sub-atom 1.E.2 Phase A · post Phase 0 verification)
**Cement**: OPS-045 41ª-42ª aplicación · reuse Zustand pattern existing · sostiene R23

## Context

Pre-1.E.2 estado empírico admin UX FULKRO:

1. **Post-login post-MFA redirect**: middleware + redirect.ts envían admin a `/admin/dashboard` (cross-cliente generic · enumera KPIs de TODOS los clientes activos)
2. **Sidebar global**: TOP_NAV 15 items cross-project (Dashboard · Pipeline · Clientes · Proyectos · etc) + ClientSection middle (active + retainer clients enumerated)
3. **Per-project navigation**: `/admin/projects/[id]/*` 30+ sub-routes production-grade · pero NO concepto de "active project" persistente cross navigation
4. **No project switcher persistent**: cada navegación a project requiere click desde /admin/projects/[id]/ structure · NO breadcrumb permanent · NO dropdown switcher

Marcos directive 2026-05-23 (insight cliente piloto MEDIA onboarding workflow):
> "Post-login → project selector landing (NO dashboard overview generalista). Active project context global persistent cross-admin. Toda memoria/copiloto/gestor documental/info proyecto = scoped per project. Switcher dropdown fluido entre projects en sidebar. Breadcrumb permanent project-scoped. Cliente portal R29 sostained client-scoped (NO cambia). Foundation 2+ cliente onboarding path."

Sub-atom 1.E.2 implementa este pattern · este ADR captura decisiones arquitecturales canonical.

## Decision

### 1. State management · Zustand pattern reuse

`ActiveProjectStore` ⊆ Zustand stores existing (auth-store + copilot-store). Persist middleware con localStorage para `lastUsedProjectId` cross-session.

```typescript
// frontend/lib/stores/active-project-store.ts (NEW)
interface ActiveProject {
  id: string;
  name: string;
  clientId: string;
  clientName: string;
  ensCategory: "BASICA" | "MEDIA" | "ALTA" | null;
  status: string;
  lastAccessedAt: number;
}

interface ActiveProjectStore {
  activeProject: ActiveProject | null;
  lastUsedProjectId: string | null;
  setActiveProject(p: ActiveProject | null): void;
  clearActiveProject(): void;
}
```

**Rationale**: Zustand pattern canonical FULKRO (2 stores existing · auth + copilot). NO architecture innovation · 2-line `create(persist(...))` reuse pattern. Persist middleware sostiene L3 hybrid post-login.

### 2. Post-login redirect · L3 hybrid (last-used OR selector)

```typescript
// frontend/lib/auth/redirect.ts ENHANCE
export function getDefaultPathForRole(role: string): string {
  if (isAdminRole(role)) {
    // L3 hybrid: read lastUsedProjectId from persist storage
    if (typeof window !== "undefined") {
      try {
        const raw = localStorage.getItem("fulkro-active-project");
        if (raw) {
          const { state } = JSON.parse(raw);
          if (state?.lastUsedProjectId) {
            return `/admin/projects/${state.lastUsedProjectId}/dashboard`;
          }
        }
      } catch { /* fall through to selector */ }
    }
    return "/admin/projects";  // selector landing default
  }
  if (isClientRole(role)) return "/client-portal/dashboard";
  return "/login";
}
```

**Edge cases**:
- SSR/middleware (`pathname === "/"`): always falls back to `/admin/projects` selector landing (no localStorage on server). Acceptable: client-side LoginForm completion will hydrate L3 on next navigation.
- localStorage empty (first-time login OR cleared): defaults to selector landing.
- `lastUsedProjectId` invalid (project deleted/inaccessible): selector landing handles gracefully (project NOT in user accessible list).

**Rationale L3 vs L1 (always selector) vs L2 (always last-used)**:
- L1 every login adds friction Marcos cuando trabaja consecutivos días mismo cliente
- L2 always lastUsed breaks when Marcos needs jump between clients · selector landing not accessible
- L3 hybrid best UX · returning to same client = zero-friction · explicit switch via sidebar dropdown OR navigate `/admin/projects` selector

### 3. Sidebar persistent · ActiveProjectBanner + ProjectSwitcherDropdown

`Sidebar.tsx` enhance:
- TOP section above TOP_NAV: `<ActiveProjectBanner />` showing client + project name + ENS category badge
- Banner clickable → `<ProjectSwitcherDropdown />` (DropdownMenu shadcn/ui · reuse PortalSwitcher pattern)
- Dropdown lists accessible projects · click → setActiveProject + navigate
- Empty state (no active project) → banner says "Selecciona un proyecto" + button → `/admin/projects`

**Rationale**: Banner visible 100% admin pages cross-navigation · Marcos siempre sabe "qué cliente/proyecto estoy operando". Dropdown switcher sin friction (NO navigation /admin/projects required to switch).

### 4. Routing guard · `/admin/projects/[id]/layout.tsx` activeProject sync

Layout enhance (client component wrapper):
- On mount: si `activeProject?.id !== params.id` → fetch project header + `setActiveProject(...)`.
- Si fetch fails (project NOT accessible OR deleted): redirect `/admin/projects` con toast warning.
- Sync transparent · NO UI disruption.

**Rationale**: Sostiene 2 sources of truth (URL param + store) sincronizadas. URL es source of truth canonical · store es cache cross-navigation.

### 5. Breadcrumb persistent project-scoped

`<ProjectBreadcrumb />` NEW component visible TODOS `/admin/projects/[id]/*` pages:
- Pattern: `[Cliente] > [Proyecto] > [Sub-page]`
- Click `[Cliente]` → `/admin/clients/{client_slug}`
- Click `[Proyecto]` → `/admin/projects/{id}/dashboard`
- Click `[Sub-page]` = current (no-op)

**Rationale**: Marcos sabe siempre dónde está empírico · acelera regreso al dashboard del proyecto. Pattern análogo cliente portal `/client-portal/*` pero sólo TOP-level (client portal client-scoped natively NO necesita).

### 6. Cliente portal R29 unchanged

Cliente portal `/client-portal/*` 28+ pages stays **client-scoped natively**:
- Cliente solo tiene 1 proyecto activo por user account (ADR-013 doble pool)
- NO selector needed · cliente ve solo SU proyecto
- NO breadcrumb necesario (single-project context)
- R29 sostained sin presión coercitiva

**Rationale**: NO breaking change cliente UX existing (1.D.F.bis.III refactor cliente indispensable-only sostained). Foundation 2+ cliente onboarding NO afecta cliente UX (cada cliente ve su propio aislado).

### 7. Backend changes · scope-out (frontend-only sub-atom)

Backend ya project-scoped production-grade:
- M21 `ChatThread.project_id` NOT NULL FK (audit Phase 0 verified)
- M9 dossier_generator + M6 templates + M27 declarations + M14 contracts + M28 changes ya scoped
- Endpoint `/api/v1/projects/{id}/header` provee project + client + conformity snapshot (existing)

**Rationale ADR-025 22ª-23ª aplicación cumulative**: NO new tables · NO new backend endpoints · NO new motors. Sub-atom 1.E.2 = puro frontend state + UI polish.

## Consequences

### Positive
- ✅ Marcos workflow UX dramático mejorado: cero friction returning admin
- ✅ Foundation 2+ cliente onboarding production-ready
- ✅ Cross-navigation persistent project context sostiene activeProject single source of truth
- ✅ Cliente portal R29 NO breaking change (architectural isolation respect)
- ✅ Sostiene ADR-025 (NO new tables) + ADR-013 (doble pool) cumulative

### Negative
- 🟡 Increased complexity Sidebar.tsx · banner + dropdown additions ~50-80 LOC
- 🟡 Routing guard layout.tsx adds 1 fetch call onMount cuando activeProject mismatch URL param · negligible (cached por TanStack Query 60s staleTime)
- 🟡 localStorage persistence introduce cross-device sync gap: si Marcos login OTRO device, NO lastUsed memory · L3 falls back to selector (acceptable per design)

### Neutral
- 🔶 Pattern reusable T1+T2+T3 cualquier admin app FULKRO future
- 🔶 Capture Future-1.E.2.advanced-switcher: keyboard shortcut Cmd+K project switch · search filter projects · recent-5 quick access · pinned favorites

## Implementation phases (sub-atom 1.E.2)

| Phase | Scope | ETA empírico |
|-------|-------|--------------|
| 0 | Empirical state verification | ~30-45 min (done) |
| A | This ADR + design decisions | ~30 min (done) |
| B | Backend additions | ~0h scope-out |
| C | Frontend implementation (store + sidebar + redirect + guard) | ~1.5-2h |
| D | Project-scoping verify deep | ~30 min |
| E | E2E validation + cierre | ~30-45 min |
| **Total** | | **~3-3.75h cumulative** |

## Honesty notes

- Phase 0 verified empírico ANTES Phase A decisions (OPS-052 strengthened doctrine sostained · 6ª manifestation prevented)
- Zustand pattern reuse documented · audit reveal precedente existing
- ETA aligned with briefing nominal (~3.5-5.5h margin 15%) · NO 5ª/6ª manifestation
- Cliente portal R29 explicit NO breaking change · refactor 1.D.F.bis.III cumulative respect

## Cross-ref

- **Phase 0 audit**: `docs/audits/AUDIT_1_E_2_PROJECT_SELECTOR_FINDINGS.md`
- **Zustand patterns**: `frontend/lib/stores/auth-store.ts` + `frontend/lib/stores/copilot-store.ts`
- **Existing project layout**: `frontend/app/(admin)/admin/projects/[id]/layout.tsx`
- **DropdownMenu pattern**: `frontend/components/auth/PortalSwitcher.tsx`
- **ADR-013** doble pool auth (admin + client) preserved
- **ADR-025** NO new tables cumulative sostained
- **ADR-053** Cloud-First Architecture · project-scoping precedent
