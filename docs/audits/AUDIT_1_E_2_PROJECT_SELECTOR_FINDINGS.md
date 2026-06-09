# AUDIT 1.E.2 · Project-Selector UX · Empirical Current State

**Status**: ✅ Phase 0 verification completa · gate verde · auto-arranque Phase A
**Date**: 2026-05-23
**Methodology**: OPS-052 strengthened Phase 0 doctrine · find/cat/ls/wc/head/tail only (NO grep)

---

## Verdict empírico

**ActiveProjectContext**: ❌ NO existing · greenfield ✅
**State management pattern**: ✅ Zustand existing (auth-store + copilot-store) · reuse pattern
**Backend project_id scoping**: ✅ Production-grade (M21 chat + M9 dossier + M6 templates ya scoped)
**Login flow post-MFA**: 🟡 Current = `/admin/dashboard` (cross-cliente generic · CHANGE needed to project selector landing per Marcos directive)
**Cliente portal R29**: ✅ Already client-scoped natively · NO changes needed
**Project-scoped layout existing**: ✅ `/admin/projects/[id]/layout.tsx` con ProjectFeaturesProvider · POLISH añade ActiveProjectProvider

**No 6ª OPS-052 risk manifested** · briefing assumptions aligned with reality empírica.

---

## Step 1 · Login flow + post-auth redirect

### Files
- `frontend/app/login/page.tsx` (50 LOC · public auth landing)
- `frontend/components/auth/LoginForm.tsx` (LoginForm con WebAuthn + TOTP + bootstrap MFA)
- `frontend/lib/auth/redirect.ts` (resolvePostLoginRedirect + getDefaultPathForRole)
- `frontend/middleware.ts` (Edge middleware · session JWT Ed25519 verify)

### Current redirect logic empírica

```typescript
// frontend/lib/auth/redirect.ts (verbatim)
export function getDefaultPathForRole(role: string): string {
  if (isAdminRole(role)) return "/admin/dashboard";
  if (isClientRole(role)) return "/client-portal/dashboard";
  return "/login";
}
```

```typescript
// frontend/middleware.ts root "/" handler (verbatim)
if (pathname === "/") {
  if (!claims) return redirectTo(request, "/login");
  if (isAdminRole(claims.role)) {
    return redirectTo(request, "/admin/dashboard");  // ← target current
  }
  if (isClientRole(claims.role)) {
    return redirectTo(request, "/client-portal/dashboard");
  }
}
```

**Gap identificado Phase B**: Login post-MFA → `/admin/dashboard` (cross-cliente). Marcos directive = `/admin/projects` (selector landing) OR last-used project (L3 hybrid).

## Step 2 · Admin routes structure

22 top-level admin pages (cross-project · R23 legitimate top-level multi-cliente per directive Marcos earlier 1.C.E):
```
/admin/dashboard /admin/pipeline /admin/clients /admin/projects
/admin/meetings /admin/retainers /admin/copilot /admin/operations
/admin/compliance /admin/messages /admin/notifications /admin/finance
/admin/alerts /admin/inbox /admin/llm-observability /admin/magerit-analyses
/admin/magic-links /admin/settings /admin/timesheet /admin/whatsapp
/admin/workflow-command-center /admin/copilot
```

### `/admin/projects/` sub-routes (per-project · production-grade)

30+ project-scoped pages:
```
[id]/aepd  [id]/archetype  [id]/audit  [id]/audit-dry-run  [id]/awareness
[id]/backup-policy  [id]/bia  [id]/billing  [id]/changes  [id]/cloud-connectors
[id]/communication  [id]/conformity  [id]/contratos  [id]/dda  [id]/diagnosis
[id]/dimensiones  [id]/discovery  [id]/discrepancies  [id]/documents  [id]/dossier
[id]/equipo  [id]/evidence  [id]/exit  [id]/feature-flags  [id]/financial
[id]/implementation  [id]/magerit  [id]/mcps  [id]/obligations  [id]/onboarding
[id]/planes-accion  [id]/policies  [id]/providers  [id]/retainer  [id]/risks
[id]/roles  [id]/timeline  [id]/transparency  [id]/workspace  [id]/dashboard
```

## Step 3 · Project routes existing

### `frontend/app/(admin)/admin/projects/page.tsx` (current)

Listado simple de clients con link `/admin/projects/{DEMO_PROJECT_ID}/summary`. Uses `useClients()` hook · NO project selection state · NO "select project to enter" UX. Each client card navigates directly.

**Gap Phase C**: Enhance with selector cards + setActiveProject action onClick + filter/search + ENS category badges.

### `frontend/app/(admin)/admin/projects/[id]/layout.tsx` (existing)

```tsx
export default function ProjectLayout({ children, params }: ...) {
  return (
    <ProjectFeaturesProvider projectId={params.id}>
      <div className="flex flex-col gap-7">
        <ProjectHeader projectId={params.id} />
        <ProjectCategoryBanner />
        <QuickActions />
        <ProjectTabs projectId={params.id} />
        <div>{children}</div>
      </div>
    </ProjectFeaturesProvider>
  );
}
```

Layout production-grade existing. POLISH Phase C añade ActiveProjectProvider wrap + routing guard si activeProject mismatch.

## Step 4 · State management pattern empirical

### Zustand existing pattern (canonical reuse)

`frontend/lib/stores/auth-store.ts` (Zustand · 21 LOC):
```typescript
import { create } from "zustand";

interface AuthState {
  user: MeResponse | null;
  csrfToken: string | null;
  ready: boolean;
  setUser: (user: MeResponse | null) => void;
  setCsrf: (csrf: string | null) => void;
  setReady: (ready: boolean) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  csrfToken: null,
  ready: false,
  setUser: (user) => set({ user }),
  setCsrf: (csrfToken) => set({ csrfToken }),
  setReady: (ready) => set({ ready }),
  logout: () => set({ user: null, csrfToken: null }),
}));
```

`frontend/lib/stores/copilot-store.ts` (Zustand · 47 LOC con `panelContext.projectId`)

### `frontend/lib/contexts/ProjectFeaturesContext.tsx` (React Context API · feature flags only)

NOT global active project state · solo per-project feature flags via TanStack Query. NO scope creep · ActiveProjectStore será NEW separate file.

**Phase A decision**: Use **Zustand** pattern (consistent with auth-store + copilot-store · NO architecture innovation).

## Step 5 · Sidebar/Nav structure

### `frontend/components/layout/Sidebar.tsx` (329 LOC)

```typescript
// Top section: logo
// TOP_NAV: 15 nav items (cross-project admin pages)
const TOP_NAV: NavItem[] = [
  { label: "Dashboard", href: ROUTES.dashboard, icon: Home },
  { label: "ENS Radar", href: ROUTES.radar, icon: Radar },
  { label: "Pipeline", href: ROUTES.pipeline, icon: TrendingUp },
  { label: "Clientes", href: ROUTES.clients, icon: Users },
  // ... 11 more
];

// Middle section: ClientSection (active clients + retainer clients)
// Bottom: command palette button (⌘K)
```

**Gap Phase C**: 
- ❌ NO active project banner top
- ❌ NO project switcher dropdown
- ✅ ClientSection enumerates clients · Phase C can REUSE same data + enhance with "active project" highlight + click → setActiveProject

### Existing pattern reference · `PortalSwitcher.tsx`

```typescript
// frontend/components/auth/PortalSwitcher.tsx (verbatim · 50+ LOC)
// Dropdown topbar admin ↔ radar with DropdownMenu shadcn/ui
// Visible solo si user.is_owner
// Atajo ⌘. toggle
```

**Phase C reuse**: Same DropdownMenu pattern para project switcher en sidebar top section.

## Step 6 · Copiloto memoria M21 ChatThread scoping

### `backend/app/motors/m21_portal_cliente/models_chat.py`

```python
class ChatThread(FullMixin, Base):
    """Chat thread cliente↔admin · 1 thread per proyecto típico."""
    __tablename__ = "chat_threads"
    __table_args__ = (
        Index("ix_chat_threads_project_status", "project_id", "status"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,  # ← NOT NULL · DB-level scoping enforced
    )
    # ...
```

✅ **Project-scoped natively at DB level**. RLS + index `ix_chat_threads_project_status`. Frontend `useCopilotStore.panelContext.projectId` accepts opcional · need wire activeProject context.

## Step 7 · Gestor documental M9 + M6 scoping

Per audit FASE C cumulative previous:
- M9 `dossier_generator.generate_dossier(db, project_id, run_id, ...)` ✅ scoped
- M9 `_collect_documents(db, project_id)` ✅ scoped
- M6 `DocumentFactoryService.generate_document(project_id, ...)` ✅ scoped
- M27 declarations + M28 changes + M14 contracts ✅ scoped (audit FASE C previous)

✅ Backend scoping production-grade · no fixes needed Phase D · solo verify frontend wire uses activeProject context.

---

## Gate evaluation

| Rule | Result |
|------|--------|
| Phase 0 reveals ActiveProjectContext NOT existing | ✅ Confirmed empírico · proceed Phase A architecture |
| EXISTING Zustand pattern | ✅ auth-store + copilot-store · reuse same pattern Phase A |
| Backend project_id scoping production-grade | ✅ Confirmed (M21 chat NOT NULL + M9 + M6) · Phase D scope reduce (verify only) |
| Login flow already redirects to project landing | ❌ Current `/admin/dashboard` · Phase B implement L3 hybrid redirect |
| Copiloto/gestor mixed scoping | ❌ Already strict scoped backend · Phase D scope reduce |
| 6ª OPS-052 risk MANIFESTED | ❌ NO mismatch · briefing aligned · proceed |

**Verdict**: ✅ ALL gates green · proceed Phase A architecture decisions auto-arranque.

---

## Phase A implementation approach (decided post Phase 0)

### A.1 · ActiveProjectStore (Zustand · `frontend/lib/stores/active-project-store.ts` NEW)

```typescript
import { create } from "zustand";
import { persist } from "zustand/middleware";

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
  setActiveProject: (p: ActiveProject | null) => void;
  clearActiveProject: () => void;
  restoreLastUsed: () => void;
}

export const useActiveProjectStore = create<ActiveProjectStore>()(
  persist(
    (set) => ({
      activeProject: null,
      lastUsedProjectId: null,
      setActiveProject: (p) =>
        set({ activeProject: p, lastUsedProjectId: p?.id ?? null }),
      clearActiveProject: () => set({ activeProject: null }),
      restoreLastUsed: () => {/* hydrated by persist middleware */},
    }),
    {
      name: "fulkro-active-project",  // localStorage key
      // sessionStorage for "memory only while tab open" vs localStorage cross-session
      partialize: (state) => ({ lastUsedProjectId: state.lastUsedProjectId }),
    },
  ),
);
```

### A.2 · Post-login redirect L3 hybrid

```typescript
// frontend/lib/auth/redirect.ts ENHANCE
export function getDefaultPathForRole(role: string): string {
  if (isAdminRole(role)) {
    // L3 hybrid: check lastUsedProjectId in localStorage
    const lastUsedRaw = (typeof window !== "undefined" 
      && localStorage.getItem("fulkro-active-project"));
    if (lastUsedRaw) {
      try {
        const { state } = JSON.parse(lastUsedRaw);
        if (state?.lastUsedProjectId) {
          return `/admin/projects/${state.lastUsedProjectId}/dashboard`;
        }
      } catch { /* fall through to selector landing */ }
    }
    return "/admin/projects";  // selector landing default
  }
  if (isClientRole(role)) return "/client-portal/dashboard";
  return "/login";
}
```

NOTE: middleware.ts root "/" redirect also updated · SSR-safe (no localStorage on server · always falls back to /admin/projects · client-side LoginForm handles L3).

### A.3 · Sidebar enhancement scope

- TOP section: Add `<ActiveProjectBanner />` component (above TOP_NAV)
- New component: `<ProjectSwitcherDropdown />` (clickable banner → dropdown lists all clients/projects)
- Banner shows: cliente name + project name + ENS category badge

### A.4 · Routing guard

`/admin/projects/[id]/layout.tsx` ENHANCE:
```tsx
"use client";
// New: client component wrapper hydrates activeProject from URL param
// If activeProject?.id !== params.id → fetch project + setActiveProject
```

### A.5 · Cliente portal R29 unchanged

NO modifications · cliente sees only own project via `/client-portal/*` routes · client portal middleware enforces.

---

## Empirical ETA recalibrate

Per briefing nominal estimate `~3.5-5.5h` cumulative · Phase 0 reveals **EXISTING infrastructure** (Zustand pattern + project [id] layout + backend scoping production):

- Phase A architecture decisions: ~30 min (NO new pattern · reuse Zustand)
- Phase B backend additions: ~0h (scope-out · frontend localStorage suffices · backend already scoped)
- Phase C frontend implementation: ~1.5-2h (Zustand store + sidebar enhance + redirect logic + routing guard · NO greenfield landing page · enhance existing)
- Phase D project-scoping verify: ~30 min (scope reduced · backend confirmed scoped · spot-check frontend hooks)
- Phase E E2E validation: ~30-45 min
- **Total empírico: ~3-3.75h cumulative** (vs ~3.5-5.5h nominal · alignment ~15% margin) · NO over-estimation 5ª OPS-052 manifest

**Confidence ETA**: high · briefing nominal aligned with reality empírica.

---

## Cross-ref

- `frontend/lib/stores/auth-store.ts` (Zustand pattern reference)
- `frontend/lib/stores/copilot-store.ts` (Zustand pattern reference 2)
- `frontend/lib/contexts/ProjectFeaturesContext.tsx` (existing project-scoped pattern)
- `frontend/components/auth/PortalSwitcher.tsx` (DropdownMenu pattern reference)
- `frontend/components/layout/Sidebar.tsx` (Sidebar architecture target enhance)
- `frontend/app/(admin)/admin/projects/[id]/layout.tsx` (existing project layout)
- `backend/app/motors/m21_portal_cliente/models_chat.py` (ChatThread.project_id scoped)
- ADR-013 (auth doble pool · admin + client)
- ADR-053 (Cloud-First Architecture · project-scoping precedent)
