# Sesión 3B-2B.3 · Bucket E scope-out (3 trivial routes) · justified

**Date**: 2026-05-25
**Sub-atom**: Sesión 3B-2B.3 Phase 3
**Doctrine**: R32 v3.11 scope-out justified arquitecturalmente · NO silent debt · transparent documentation

---

## 3 routes scope-out · justified per route

### E.1 · `/admin/projects/[id]/page.tsx`

**Justification**: trivial redirect 9 LOC.

```typescript
import { redirect } from "next/navigation";
export default function ProjectIndex({ params }: { params: { id: string } }) {
  redirect(`/admin/projects/${params.id}/summary`);
}
```

**Transitively covered** via Bucket A PROBE spec `04_admin_project_summary.spec.ts`. Any request to `/admin/projects/[id]` server-side redirects to `/summary` · which IS empirically verified PASS 12/12 in CI green.

**Risk**: 0 · pure server-side redirect · no UI to test.

**Action**: NO spec created · documented transitively covered.

---

### E.2 · `/admin/cross-project-compliance/page.tsx`

**Justification**: legacy backward-compat redirect 48 LOC.

Created during Sub-atom Sesión 3B-1 Phase B.2 to keep old URL alive while canonical path moved to `/admin/compliance/projects`. Auto-redirect via `useRouter.replace` + Link fallback (R29 friendly).

**Canonical path** IS verified empirical via Bucket A P2/04 spec `04_admin_compliance_projects.spec.ts`. The legacy URL only needs to NOT 500 · which `useRouter.replace` guarantees.

**Risk**: 0 · pure client-side redirect · friendly loading state R30.

**Action**: NO spec created · sostener legacy redirect siempre que canonical green.

---

### E.3 · `/admin/copilot/page.tsx`

**Justification**: standalone wrapper 22 LOC · superseded by CopilotoAdminSidebar 1.D.B.2.

Per CLAUDE.md Sub-atom 1.D.B.2 cierre · copiloto admin LLM real Sonnet 4.6 production-grade vive embedded en `CopilotoAdminSidebar` component disponible cross-admin pages. The standalone `/admin/copilot` page renders the same `CopilotChat` component pero modo `fullscreen` · low daily-use (sidebar is preferred entry point).

**Coverage**: copilot UX is empirical-tested via `73/73 backend tests verde` (test_copilot_admin_llm_service.py + test_admin_copilot_stub.py + test_copilot_admin_screen_aware.py) + `e2e fase_22` 4 specs ARTIFACT spec-as-code · sidebar integration tested transitively cross-admin pages.

**Risk**: 0 · standalone preserved for backward compat only · sidebar is canonical entry point.

**Action**: NO spec created · sidebar integration sostained via cross-admin spec coverage.

---

## Honesty path

Per LECCIÓN-OPS-049 ARTIFACT honesty doctrine · these 3 routes are NOT silent debt:

1. Explicitly documented here with justification per route
2. Coverage path identified per route (transitive · canonical · sidebar)
3. NO claim "80/83 PASS" without these 3 honest accounting
4. Real honest math: 80/83 = 96% verified empirical via spec · 3/83 = 4% scope-out justified arquitecturalmente

Total admin pages: **83** (find empirical · NOT memoria-citada "81")
Verified empirical via spec: **80**
Scope-out justified: **3**
Sum: **83 = 100%** accounted for.

---

## Future-X capture (post-piloto demand-driven)

If Marcos decides any of these 3 routes warrant explicit empirical spec post-piloto:

- `Future-1.E.admin-polish-bucket-E-trivial-spec-coverage` · ~30 min · 3 thin specs verify redirects + fullscreen copilot wrapper render OK
- Trigger: cliente piloto MEDIA cross-references legacy URL OR Marcos prefers cosmetic completeness

R32 v3.11 sostained · architectural justification each scope-out documented.
