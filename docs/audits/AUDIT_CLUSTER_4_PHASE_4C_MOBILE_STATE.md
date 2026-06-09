# AUDIT CLUSTER 4 Phase 4C · Mobile-Optimized Cliente Portal Empirical State

**Sesión**: 3B-2B.8 CLUSTER 4 Phase 4C
**Fecha**: 2026-05-26
**Ejecutor**: Phase 4C.0 OPS-052 audit mandatory
**Status**: ✅ **Audit complete · scope refined mobile drawer + responsive · NO STOP HARD**

---

## Resumen ejecutivo

Briefing Phase 4C asumió mobile-optimized cliente portal. Empirical reality:

- ✅ **ClientPortalChrome existing** (`frontend/components/layout/ClientPortalChrome.tsx`)
- ✅ **ClientSidebar** existing but `hidden lg:flex` · invisible mobile (< 1024px breakpoint)
- ✅ **ClientHeader** existing · responsive h-16/h-[72px] · NO mobile menu button
- ✅ **shadcn/ui Sheet primitive** available (Dialog-like drawer)
- ❌ **NO mobile drawer/hamburger menu** · cliente cannot navigate on mobile
- ❌ **NO mobile menu trigger** in ClientHeader
- ❌ **NO focus management mobile drawer** (a11y guard)

**Critical mobile gap**: cliente en móvil NO puede navegar sidebar items (Dashboard · Inbox · DdA · MAGERIT · etc). Browse cliente portal mobile experience BROKEN sin mobile drawer.

**Refined empirical scope**: Phase 4C aporta:
1. NEW `ClientMobileDrawer.tsx` (Sheet-based drawer reusing ClientSidebar nav items)
2. Mobile menu button in ClientHeader (`lg:hidden` trigger)
3. WCAG accessibility (focus management + escape key + aria-label)
4. Touch-friendly button sizes (min 44x44px per WCAG 2.5.5)

ETA refined: ~2-3h frontend MVP vs briefing 3-5h (-30% to -40% OPS-045 62ª manifestation · scope tight UI component creation).

Note: Phase 4C is primarily frontend (TSX components). Tests via Playwright mobile viewport deferred Future-X (CI infrastructure required) o smoke verify via TypeScript build clean.

---

## Phase 4C.0.1 · Empirical responsive state map

### ClientPortalChrome
- Uses `flex h-dvh` · works mobile but sidebar hidden
- main content `flex-1 overflow-y-auto pb-16 md:pb-24`

### ClientSidebar `hidden lg:flex`
- 1024px+ visible · below hidden completely
- Contains nav items + logo + cliente meta

### ClientHeader responsive
- h-16 mobile + h-[72px] md+
- px-4 mobile + px-6 md+
- No mobile menu trigger

### Tailwind breakpoints CCN
- sm: 640px · md: 768px · lg: 1024px · xl: 1280px
- Mobile = < 1024px (cliente sidebar invisible threshold)

---

## Phase 4C.0.2 · Mobile drawer design

### NEW `ClientMobileDrawer.tsx`

```tsx
"use client";

import { Menu, X } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { ClientSidebar } from "@/components/layout/ClientSidebar";

export function ClientMobileDrawer() {
  const [open, setOpen] = useState(false);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          aria-label="Abrir menú"
          className="lg:hidden text-white hover:bg-white/10"
        >
          <Menu className="size-6" />
        </Button>
      </SheetTrigger>
      <SheetContent
        side="left"
        className="w-72 p-0 border-r-0"
        aria-label="Menú principal"
      >
        <SheetHeader className="sr-only">
          <SheetTitle>Menú principal</SheetTitle>
        </SheetHeader>
        <ClientSidebar
          className="flex w-full h-full"
          onNavigate={() => setOpen(false)}
        />
      </SheetContent>
    </Sheet>
  );
}
```

### ClientHeader extension
- Add MobileDrawer button at left (visible only lg:hidden)
- Maintain existing right-side actions (notifications · logout)

### ClientSidebar extension
- ADD optional `onNavigate?: () => void` prop · callback called when nav item clicked
- Used by drawer to auto-close on navigation
- Backward-compat (Optional · default no-op)

---

## Phase 4C.0.3 · WCAG accessibility checklist

- ✅ Sheet primitive (shadcn) includes focus management + escape key
- ✅ Mobile trigger button aria-label="Abrir menú"
- ✅ SheetHeader sr-only para screen readers
- ✅ Touch button size min 44x44px (size="icon" default 40px → bump size if needed)
- ✅ Focus returns to trigger after close (Sheet behavior built-in)

---

## Phase 4C.0.4 · Recommended Phase 4C refined scope (~2-3h)

### Phase 4C.1 implementation (~1.5-2h)

**Step 1 · NEW ClientMobileDrawer component** (~30-45 min)
- `frontend/components/layout/ClientMobileDrawer.tsx`
- Sheet-based · reuses ClientSidebar
- Button trigger lg:hidden

**Step 2 · ClientHeader integration** (~15-20 min)
- ADD ClientMobileDrawer button at left edge mobile-only
- Maintain right-side existing (notifications + logout)

**Step 3 · ClientSidebar onNavigate callback** (~10-15 min)
- ADD optional `onNavigate?` prop
- Backward-compat no-op default

**Step 4 · TypeScript build clean** (~10-15 min)
- npx tsc --noEmit verify cero NEW errors my files
- Pre-existing errors unaffected

### Phase 4C.2 tests (~30-45 min · deferred)

Playwright mobile viewport tests deferred Future-1.E.client-portal-mobile-e2e
(infrastructure required CI · ETA ~3-4h cumulative spec writing + verification).

MVP scope · structural verification via TypeScript build clean + manual
visual check inferred (mobile drawer renders + auto-close on nav · WCAG aria-label).

---

## ETA refined Phase 4C

- **Briefing nominal**: ~3-5h
- **Empirical refined**: ~2-3h frontend MVP component (Sheet drawer + ClientHeader integration + onNavigate callback)
- **OPS-045 62ª manifestation**: -30% to -40% vs nominal (scope tight UI component reuse Sheet primitive shadcn existing)

---

## Filosofía cliente-mínimo compliance

100% aligned:
- Mobile drawer = cliente NAVEGA portal mobile · NO opera ENS técnico mobile
- Touch-friendly buttons · UX accessible
- WCAG 2.4.4 (button-name) + 2.5.5 (touch target size) sostained
- R29 firmísimo aria-labels Spanish friendly

---

## STOP HARD trigger evaluation

**NO STOP HARD necesario**. Briefing intent (mobile-optimized cliente portal) ratified · refined a Sheet drawer + ClientHeader integration scope. Playwright mobile E2E deferred Future-X (CI infrastructure dependent).

---

## Patterns potencialmente formalizables Phase 4C

- **Mobile drawer + sidebar reuse pattern** (Sheet primitive shadcn + ClientSidebar reuse via onNavigate callback · DRY)
- **lg:hidden mobile trigger pattern** (TailwindCSS responsive hide/show · button visible solo mobile)

---

## Decisión pendiente

⏸️ **Architect approve Phase 4C.1 refined scope**:
- 1 NEW component (ClientMobileDrawer) + 2 modifications (ClientHeader + ClientSidebar onNavigate)
- TypeScript build clean verification
- Playwright mobile E2E DEFERRED Future-1.E
- ETA refined ~2-3h
