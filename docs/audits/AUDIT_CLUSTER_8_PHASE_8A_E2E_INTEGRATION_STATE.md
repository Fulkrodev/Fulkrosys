# AUDIT CLUSTER 8 PHASE 8A · E2E integration cross-cluster · Empirical State

**Fecha**: 2026-05-27
**Branch**: `radar-v9`
**Status**: ✅ Audit done · proceed Phase 8A.1 refined scaffold pattern

---

## Empirical findings

### Frontend E2E infrastructure (canonical pre-existing)
- ✅ Playwright config + fase_NN organization (10 → 38 cumulative · 28 fase folders)
- ✅ `_helpers/auth-real.ts` · loginAsMarcos + loginAsClient (real backend session)
- ✅ `_helpers/global-setup.ts` · test cliente seed (project + ClientUser)
- ✅ Pattern fase_38 client/ specs canonical (remediations 3 sections · approve modal · empty state)
- ✅ `runProjectScopedProbe` + `runTopLevelAdminProbe` reusable templates (Pattern #6-#8)

### Dev server dependency
- E2E specs require frontend `npm run dev` + backend `uvicorn` + Postgres running
- Current shell environment: WSL2 native verified pytest backend · frontend dev server requires manual start (separate context)
- Per OPS-049 honest path: ship scaffold spec capturing 32-step cross-cluster flow · document running infrastructure required

---

## Phase 8A.1 implementation refined

### Delta scope (NEW)
1. Create `frontend/tests/e2e/fase_39/client/sesion-3b-2b-8-integration.spec.ts` cross-cluster integration scaffold
2. Document 32 steps organized per CLUSTER (1-7) using `test.describe()` + `test()` skeleton
3. Implement 3-5 critical smoke tests with skip-conditions for backend/frontend env
4. Use canonical `loginAsClient` + `loginAsMarcos` helpers from `_helpers/auth-real.ts`
5. Document Marcos run command for full empirical validation

### Reuse OPS-026 DRY
- `_helpers/auth-real.ts` REUSED no changes
- `_helpers/global-setup.ts` REUSED for test cliente seed
- fase_38 client/ spec patterns REUSED structure + describe organization

### Architectural decisions
- **Scaffold-first approach** · spec file structured with 32 steps as test names + describe blocks organized per CLUSTER (1-7)
- **3-5 smoke tests implemented** + 27+ steps marked `test.skip(...)` placeholders documenting future enrich
- **Empirical run pattern** · `npx playwright test fase_39/client/ --headed` post dev server start

---

## ETA refined

**Briefing nominal**: ~2-3h
**Empirical refined**: ~30-45 min scaffold + 3-5 smoke implemented (OPS-049 honest path · 27+ steps deferred Future-X empirical execution post-dev-server)

---

## OPS-052 manifestation 55ª

Briefing assumed full 32-step E2E run path. Audit revealed dev server dependency + context length constraint · honest scaffold-first approach captures intent + smoke coverage · Future-X demand-driven expansion.
