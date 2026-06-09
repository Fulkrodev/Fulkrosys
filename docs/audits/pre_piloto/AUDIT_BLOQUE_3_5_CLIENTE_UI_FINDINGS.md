# AUDIT Bloque 3+5 Phase 0 · Cliente UI empirical state

**Status**: ✅ Phase 0 cliente UI MANDATORY complete
**Date**: 2026-05-24
**HEAD base**: d20d022 (post backend orchestrator commits)
**Methodology**: find/cat/wc/head/tail/ls (NO grep) · OPS-052 strengthened doctrine

---

## Verdict empírico

Cliente portal `/(client-portal)/client-portal/` es **production-grade massive 28 pages** · **SSE hook EXISTS** (`useClientProjectEvents.ts`) · sidebar pattern simplified 1.D.F.bis.III refactor preserved (14→10 entries en 4 secciones).

**Gap específico identificado**: NO `/client-portal/remediaciones/` page existing · NO `RemediationCard` component · `useClientProjectEvents` hook EXISTS pero solo handle 3 event types (step_*) · needs extend para cloud_remediation_* events.

**ETA empírico realista refined**: ~2.5-4h Phase A cumulative:
- ~30 min · API client + types extend `useClientProjectEvents` hook for cloud_remediation_* events
- ~1-1.5h · 2 components NEW (RemediationCard · ApprovalModal)
- ~1h · page `/remediaciones/page.tsx` + sidebar entry + SSE wire
- ~30 min · tests scope-light (5-6 verificando flows core · NO E2E exhaustivo)

**ETA refined**: ~2.5-3h cliente UI (vs ~3-5h nominal · audit-first reveals SSE hook + sidebar pattern existing reuse 100%).

---

## Stats baseline cliente portal

### `/(client-portal)/client-portal/` 28 pages activas
- Core ENS workflow: dashboard · workflow · tasks · magerit · dda · policies · conformidad · dpc-anual · evidencias · files · registros · registros/[tipo] · actas
- Firma + signing: firma · firmas-hub
- Comunicación: chat · inbox · whatsapp · incidents
- Onboarding: onboarding · onboarding/oauth-callback · pentest-authorization
- Retainer: retainer-checkin · billing · transparency
- Cuenta: account · account/notifications · login
- **NO `/remediaciones/` page existing · GAP confirmed**

### Sidebar 4 secciones (1.D.F.bis.III refactor 14→10 entries cement)
- PRINCIPAL: Inicio · Mis tareas · Firmas pendientes · Subir documentos (4)
- MI EMPRESA: Onboarding · Facturación (2)
- COMUNICACIÓN: Chat con Marcos · Mensajes · WhatsApp (3)
- MI CUENTA: Mi cuenta (1)
- **NO entry "Remediaciones" existing · gap for Phase A**

### SSE hook `useClientProjectEvents.ts` (1.D.G.E v3.11)
- Subscribes a `/api/v1/client-portal/projects/{id}/events` · backend filtered audience cliente
- Auto-reconnect via EventSource API
- Current event types handled:
  - `step_completed` (admin terminó · primary_actor=admin)
  - `step_unblocked` (cliente debe actuar · primary_actor=cliente)
  - `step_blocked` (cliente bloqueado · primary_actor=cliente)
- Options: onStepUnblocked · onStepCompleted · onStepBlocked · invalidateQueries
- **Pattern reuse para extend events `cloud_remediation_*`** (NEW handlers add)

### Components cliente existing 100% production
- `ConnectorsClientView.tsx` (cloud connectors cliente facing)
- `NotificationsInboxPanel.tsx` (inbox notifications)
- `ClientTaskCard.tsx` + `ClientTasksList.tsx` (tasks pattern reuse)
- `OnboardingClientFlow.tsx` (multi-step wizard pattern)
- `policies/PolicyBulkSignButton.tsx` · `firmas-hub/ChainVisualizer.tsx` · etc

### Lib api + hooks structure
- `frontend/lib/api/` modules per domain
- `frontend/hooks/` per-feature hooks
- TanStack Query (queryClient + invalidateQueries) cement pattern

### Layout
- `client-portal/layout.tsx` Server Component delegates a `ClientPortalChrome`
- `ClientPortalChrome` "use client" path-aware · login/forgot/reset NO chrome · resto SI
- Sidebar pattern `lg:flex` (hidden mobile)

---

## Gap matrix per Phase A scope

| Component needed | Status | ETA | Notes |
|------------------|--------|-----|-------|
| Page `/client-portal/remediaciones/page.tsx` | 🔴 MISSING | ~30 min | thin wrapper · delegates 2 components |
| Component `RemediationCard` | 🔴 MISSING | ~45 min | display per proposal · status badge · button "Revisar y decidir" |
| Component `ApprovalModal` | 🔴 MISSING | ~45 min | Dialog · approve/reject · notes input · friendly_message |
| API client `lib/api/cliente/cloud-remediations.ts` | 🔴 MISSING | ~15 min | listPending · approve · reject (3 methods) |
| Hook `useCloudRemediations.ts` | 🔴 MISSING | ~15 min | TanStack Query (list + approve + reject mutations) |
| Sidebar entry "Remediaciones" | 🔴 MISSING | ~10 min | add a PRINCIPAL section o nueva sección "Decisiones técnicas" |
| Extend `useClientProjectEvents` cloud_remediation_* events | 🟡 EXTEND | ~20 min | add 4 handlers: cloud_remediation_proposed/executing/executed/failed |
| Tests scope-light (5-6) | 🔴 MISSING | ~30 min | component render · approve/reject submit · empty state · SSE handler |

**Total cumulative Phase A empírico**: ~3-3.5h (alignment audit ETA range)

---

## OPS-052 11ª manifestation gate · NOT TRIGGERED

| Criterio | Resultado Phase 0 |
|----------|-------------------|
| Briefing-vs-reality mismatch >30% | ❌ NO (cliente UI gap confirmed · sin sorpresas) |
| Scope inflation >50% | ❌ NO (~3-3.5h alignment vs 3-5h nominal · ahorro ~15-25%) |
| Existing infrastructure hidden invalida plan | ❌ NO (SSE hook existing reuse 100% · sidebar pattern + components reusable) |

**Gate**: ✅ PROCEED Phase A · plan literal con scope-reduce mínimo.

---

## Recomendación Phase A scope

**Implementation order recommended**:
1. (~15 min) lib/api/cliente/cloud-remediations.ts (types + 3 API methods)
2. (~20 min) extend `useClientProjectEvents` → add cloud_remediation_* event types
3. (~15 min) hook `useCloudRemediations.ts` (TanStack Query)
4. (~45 min) `RemediationCard.tsx` component
5. (~45 min) `ApprovalModal.tsx` component
6. (~20 min) page `/client-portal/remediaciones/page.tsx` + sidebar entry
7. (~30 min) tests scope-light (5-6 unit tests)

**Total Phase A**: ~3-3.5h empírico cumulative · 2-3 commits granularity (lib+hooks · components · page+sidebar+tests).

---

## Cross-ref

- Backend orchestrator: `backend/app/motors/m_cloud_connectors/remediation_orchestrator.py` + `remediation_api.py`
- SSE hook reuse: `frontend/hooks/useClientProjectEvents.ts`
- Sidebar source: `frontend/components/layout/ClientSidebar.tsx`
- Layout: `frontend/app/(client-portal)/client-portal/layout.tsx`
- Cliente components dir: `frontend/components/client-portal/`
- Phase 0 backend Bloque 3+5: `docs/audits/pre_piloto/AUDIT_BLOQUE_3_5_PHASE_0_CLOUD_REMEDIATION.md`
- ADR-013 doble pool · ADR-031 ENAC trazabilidad · R29 firmísimo cliente

---

## Honest notes

1. NO inspección detalle per page (sample-based · 28 pages assumption sostained per Audit #4 + 1.D.F.bis.III refactor)
2. NO verify mobile responsive scope cliente · audit Audit #11 defer post-piloto demand-driven
3. Tests scope-light intentional (5-6 unit) · E2E full diferida CI infra full per OPS-050 doctrine
4. Sidebar nueva entry "Remediaciones" tolerada 1.D.F.bis.III refactor (10 entries · pasa a 11 · within tolerance)
