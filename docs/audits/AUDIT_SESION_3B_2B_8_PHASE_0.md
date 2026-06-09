# AUDIT · Sesión 3B-2B.8 Phase 0 · Cliente Portal Current State Re-validation Empirical

**Fecha**: 2026-05-26 post Sesión 3B-2B.6 CERRADO DEFINITIVO
**Baseline**: `docs/audits/AUDIT_CLIENTE_PORTAL_COMPLETENESS.md` (828 LOC · commit 6ddd7ad)
**Scope**: empirical re-validation TOP 5 BLOQUEANTES + ALTA gaps + WIRED OK preserved + NEW gaps post-3B-2B.6
**Methodology**: grep + filesystem + Read tool · NO speculative claims (OPS-049 honest)

---

## TL;DR · Re-validation Conclusion

**TOP 5 BLOQUEANTES STILL APPLY EMPIRICAL** (post-Sesión 3B-2B.6 work · auditor portal NO impactó cliente portal scope):

| # | BLOQUEANTE | Status post-3B-2B.6 | Effort estimado | Status post-CLUSTER 1 |
|---|-----------|--------------------|------------------|------------------------|
| 1 | M01 Categorización sync NOT WIRED | ❌ STILL APPLY | ~3-5h Path A | ✅ **RESOLVED commit `29da928` Phase 1A** |
| 2 | M02 MAGERIT sync NOT WIRED | ⚠️ PARTIAL (page exists · sync NO) | ~3-5h Path A | ✅ **RESOLVED commit `3a03155` Phase 1B** |
| 3 | Cloud connectors grid UI cliente MISSING | ❌ STILL APPLY | ~4-6h Path A | ✅ **RESOLVED commit `d894aed` Phase 1C** (Opción C steady-state) |
| 4 | Copiloto proactivity 25% (hardcoded quick-actions) | ❌ STILL APPLY | ~3-5h Path A | ✅ **RESOLVED commit `e87964a` Phase 1D** (workflow state-aware) |
| 5 | M04 Plan Gantt cliente preview missing | ❌ STILL APPLY | ~3-5h Path A | ✅ **RESOLVED commit `4d3fb18` Phase 1E** (M17 READ-ONLY Gantt cliente) |

**🎉 ALL 5 BLOQUEANTES RESOLVED · CLUSTER 1 PATH A CERRADO 2026-05-26 · 5/5 phases shipped sequential.**

**TOP 3 ALTA gaps STILL APPLY**: DRP cliente UI · BIA cliente form · AuditLog NOT wired NotificationOrchestrator. Reframe CLUSTER 2 (questionnaire input + review/approve · NO creator mode · cliente-mínimo filosofía).

**NEW gaps surface post-3B-2B.6**: NONE crítico · auditor portal isolated correctly (separate `(portal)` route group · NO impacta cliente portal).

**WIRED OK preserved**: M07 Evidence flow · cloud remediations SSE · NotificationOrchestrator + post_signoff_hooks · TooltipENS (61 occurrences) · Sesión 3B-2B.4 cliente_id FK RLS.

**Recommendation**: Path A 5 items proceder · estimado ~20-28h cumulative aligned con architect brief.

---

## DIMENSION 1 · TOP 5 BLOQUEANTES Re-validation Empirical

### #1 M01 Categorización sync NOT WIRED

**Evidence empirical**:
- Grep `m01.categorizacion.completed` o `categorizacion_completed` en `backend/app/motors/m01_categorization/`: **0 matches**
- Grep `sse_dispatcher.dispatch` en `backend/app/motors/m01_categorization/`: **0 matches**
- Find frontend pages `*categoriz*` en `frontend/app/(client-portal)/`: **0 matches**
- `useClientProjectEvents` declared event types: `step_completed` + `step_unblocked` + `step_blocked` + cloud_remediation_* + heartbeat · **NO m01.* event types**

**Status**: ❌ **STILL APPLY** · cero cambios post-3B-2B.6 · admin completa M01 → cliente NO ve dimensiones reflected.

**Path A scope sostenido**: backend SSE emit + cliente GET endpoint + frontend display (~3-5h estimado).

---

### #2 M02 MAGERIT sync NOT WIRED

**Evidence empirical**:
- Cliente page exists: `frontend/app/(client-portal)/client-portal/magerit/page.tsx` (sub-atom 1.D.F.bis.III.A v3.11 · "indispensable-cliente-only" pattern · READ-ONLY display + form aportar info)
- Grep `useClientProjectEvents` en `frontend/components/client-portal/magerit/`: **0 matches** · NO SSE wiring
- Grep `m02.magerit.updated` en backend: **0 matches** · NO backend emit
- ClientSseEventType enum: NO `m02.*` event type

**Status**: ⚠️ **PARTIAL** · cliente page existe + display read-only OK · pero SYNC bi-direccional NO wired (cliente debe refrescar manual cuando admin actualiza).

**Path A scope sostenido**: SSE emit + frontend subscribe + visual refresh (~3-5h estimado).

---

### #3 Cloud connectors grid UI cliente MISSING

**Evidence empirical**:
- Find `frontend/app/(client-portal)/client-portal/cloud-connections` o `*cloud*`: **0 matches**
- Cliente portal has 31 pages totales · NONE matches "cloud" o "connection" patterns
- Backend CloudConnector API ready confirmed previous audit (m_cloud_connectors motor · 3 endpoints REST)
- OAuth callback page exists: `frontend/app/(client-portal)/client-portal/onboarding/oauth-callback/page.tsx`

**Status**: ❌ **STILL APPLY** · zero changes post-3B-2B.6 · backend ready pero NO frontend UI cliente.

**Path A scope sostenido**: cliente `/cloud-connections` page + grid display + OAuth flow integration + remediation visibility (~4-6h estimado).

---

### #4 Copiloto proactivity 25% (hardcoded quick-actions)

**Evidence empirical**:
- Grep `_suggest_next_hint\|workflow_state_scanner` en `backend/app/motors/m11_copiloto/`: **0 matches**
- `_QUICK_ACTIONS_BY_CONTEXT` dict hardcoded en `backend/app/motors/m11_copiloto/api.py:248`
- 6 hardcoded context keys: default · magerit · obligations · conformity · diagnosis · evidence
- NO state-aware logic · NO workflow phase detection · NO role-based suggestion

**Status**: ❌ **STILL APPLY** · hardcoded prefill_query per context (e.g. "Top 5 riesgos" estático) · NO proactivity workflow-state aware.

**Path A scope sostenido**: NEW `workflow_state_scanner.py` pure functional + `_suggest_next_hint()` upgrade invoke state + frontend CopilotDock display contextual hint (~3-5h estimado).

---

### #5 M04 Plan Gantt cliente preview missing

**Evidence empirical**:
- Find `frontend/app/(client-portal)/client-portal/plan` o `*gantt*`: **0 matches**
- Cliente portal pages NO incluyen ningún Gantt-related page
- M04 backend exists (m04_gap motor · plan_generator existing en m17_planning)
- Cliente `/workflow` página exists (generic workflow display) pero NO specific Plan Gantt

**Status**: ❌ **STILL APPLY** · zero changes post-3B-2B.6 · MEDIA spec exige Gantt interactivo per ENS audit prep.

**Path A scope sostenido**: backend cliente endpoint READ-ONLY + Gantt component admin reuse en READ-ONLY mode + filter "mis tareas" toggle (~3-5h estimado).

---

## DIMENSION 2 · ALTA gaps Re-check

### #6 DRP cliente UI MISSING

**Evidence empirical**:
- Find `*drp*` o `*disaster*` en `frontend/app/(client-portal)/`: **0 matches dedicados**
- Grep `DisasterRecoveryPlan` cross-frontend: **0 matches en cliente portal**
- Only mention en registros: `frontend/app/(client-portal)/client-portal/registros/[tipo]/page.tsx:76` string `"codigo_ejercicio_drp"` (NOT a dedicated DRP page)

**Status**: ❌ **STILL APPLY** · NO bloqueante MEDIA piloto · bloqueante ALTA piloto futuro.

**Defer**: Future-1.E.X.drp-cliente-ui-alta (~5-8h post-MEDIA piloto).

---

### #7 BIA cliente form MISSING

**Evidence empirical**:
- Find `*bia*` o `*business-impact*` en `frontend/app/(client-portal)/`: **0 matches**
- Grep `BusinessImpactAnalysis` cross-frontend: **0 matches**

**Status**: ❌ **STILL APPLY** · NO bloqueante MEDIA piloto · bloqueante ALTA piloto futuro.

**Defer**: Future-1.E.X.bia-cliente-form-alta (~5-8h post-MEDIA piloto).

---

### #8 AuditLog NOT connected to NotificationOrchestrator

**Evidence empirical**:
- Grep `audit_log` en `backend/app/motors/m21_portal_cliente/notification_service.py`: **0 matches** · NO direct wire-in
- Grep `audit_log` en `backend/app/api/v1/notification_orchestrator*.py`: file NOT found en path
- Post-signoff_hooks references `audit_log` indirect: 0 (verified m07_evidence + m23_retainer + m19_risk usage of `notifications.post_signoff_hooks` · NOT cross-wired audit_log)

**Status**: ⚠️ **PARTIAL** · M30 interactions tracked manually · NotificationOrchestrator dispatch NO emite audit_log entry para auditor portal trace.

**Defer**: Future-1.E.X.auditlog-orchestrator-wire (~2-3h post-MEDIA piloto) · NO bloqueante MEDIA (Sesión 3B-2B.6 Sub-atom 5.A RLS hardening prereq cumplido).

---

## DIMENSION 3 · WIRED OK Preserved Check

### M07 Evidence flow 100% cliente

**Evidence**:
- `frontend/app/(client-portal)/client-portal/evidencias/page.tsx` exists + functional
- Backend M07 vault + signing + audit log emit confirmed `m07_evidence/antivirus_scan_service.py:316` invokes `post_signoff_hooks`

**Status**: ✅ **PRESERVED** · NO regression.

### Cloud remediations SSE real-time cliente

**Evidence**:
- `frontend/app/(client-portal)/client-portal/remediaciones/page.tsx` uses `useClientProjectEvents` ✓
- `frontend/components/client-portal/remediations/{ApprovalModal,RemediationCard}.tsx` exists
- Cloud remediation event types declared en `useClientProjectEvents.ts:20-26`

**Status**: ✅ **PRESERVED** · Sesión 3B-2B.4 Path B work intact.

### NotificationOrchestrator + post_signoff_hooks

**Evidence**:
- `backend/app/notifications/post_signoff_hooks` invoked desde 3 motors: m07_evidence + m23_retainer + m19_risk (verified grep)

**Status**: ✅ **PRESERVED** · NO regression.

### TooltipENS occurrences

**Evidence**:
- Grep `TooltipENS` en `frontend/components/`: **61 occurrences** (consistent con baseline · cross-component reuse R30 inverso pattern)

**Status**: ✅ **PRESERVED**.

### RLS cliente_id FK isolation (Sesión 3B-2B.4 Phase 2)

**Evidence**: Sub-atom 5.A audit_log RLS pattern ADD COLUMN project_id/client_id + 3-way OR clause already applied · cliente_id FK isolation cliente portal preserved (memoria `copilot-rls-three-way-clause.md`).

**Status**: ✅ **PRESERVED**.

---

## DIMENSION 4 · NEW gaps Post-Sesión 3B-2B.6

### 4.1 Auditor portal impact cliente portal?

**Evidence empirical**:
- Auditor portal lives en `frontend/app/(portal)/auditor-portal/[token]/` (12 page wrappers · separate route group)
- Cliente portal lives en `frontend/app/(client-portal)/client-portal/` (31 page wrappers · separate route group)
- ZERO file overlap entre ambas trees
- ZERO shared layout o navigation (cada uno tiene su Chrome separate)
- Backend public_api auditor (m09_audit_prep/public_api.py) NO shares router prefix con cliente (m21_portal_cliente)

**Status**: ✅ **NO impact** · arquitecturalmente bien aislado · Sesión 3B-2B.6 trabajo NO regresó cliente portal.

### 4.2 Compliance portal nested route surface cliente?

**Evidence**:
- Cliente has `/client-portal/cumplimiento/page.tsx` (existing pre-3B-2B.6)
- NO new compliance nested routes added post-3B-2B.6
- Compliance admin lives en `frontend/app/(admin)/admin/compliance/*` (separate)

**Status**: ✅ **NO new gap** · cumplimiento cliente page preserved · Future-1.E.compliance-portal-route-group still deferred si Option A migration demand-driven.

### 4.3 /client-portal/files page state vs M07 vault

**Evidence**:
- `files/page.tsx` enriched sub-atom 1.C.G.B v3.10 (gestor documental cliente · sidebar tree + upload + filter)
- Cliente upload modal · file preview · folder filter wired
- Hybrid tabs docs + evidence + search functional

**Status**: ✅ **PRESERVED** · M07 vault flow intact + cliente UX enhanced previous sub-atom.

---

## DIMENSION 5 · Path A Refined Scope (Recommendation)

### Confirmed scope · 5 items × estimated effort

| Phase | Item | Estimated effort | Confidence |
|-------|------|-----------------|-----------|
| 1A | M01 Categorización sync (backend SSE + cliente GET + frontend display) | 3-5h | HIGH (pattern useClientProjectEvents reuse) |
| 1B | M02 MAGERIT sync (backend SSE + frontend subscribe + page exists) | 3-5h | HIGH (page exists · only SSE wire pending) |
| 1C | Cloud connectors grid UI cliente (page NEW + grid + OAuth flow + remediations) | 4-6h | MEDIUM (backend ready · UI nueva from scratch) |
| 1D | Copilot workflow state-aware proactivity (NEW workflow_state_scanner + _suggest_next_hint upgrade + frontend CopilotDock) | 3-5h | MEDIUM (NEW pure functional service · _suggest_next_hint refactor) |
| 1E | M04 Plan Gantt cliente preview (backend endpoint + Gantt READ-ONLY + filter mis tareas) | 3-5h | MEDIUM (Gantt component admin reuse needed verification) |
| **TOTAL Path A** | 5 items + CLUSTER 1 cierre regression/WCAG | **~20-28h** | **architect target aligned** |

### Risk surfaces

1. **Workflow state scanner complexity** (Phase 1D) · workflow_state derivation cross 9 motors. **Mitigation**: scope pure functional inicial · expand iteration.
2. **Gantt component admin reuse** (Phase 1E) · si admin Gantt component está bound a admin-only stores · refactor needed. **Mitigation**: pre-Phase 1E micro-audit `frontend/components/m17_planning/` Gantt structure.
3. **Cloud OAuth flow E2E** (Phase 1C) · multi-provider (M365 + Google + AWS + Azure + GCP) · pre-existing OAuth callback may need wire-up adjust. **Mitigation**: Phase 1C.1 pre-audit existing callback page.

### Patterns aplicables CLUSTER 1

- emit_auditor_event helper pattern (Sesión 3B-2B.6 Phase 6) · NO directamente reusable (auditor scope) pero pattern coherent para emit_client_event equivalent si needed
- compute_dda_evidence_gaps pure functional pattern (Sesión 3B-2B.6 Phase C3) · DIRECTLY REUSABLE para `compute_workflow_state` Phase 1D pattern mirror
- ClientSseEventType union pattern (`useClientProjectEvents.ts:28-33`) · expand añadiendo `m01.categorizacion.completed` + `m02.magerit.updated` + `cloud.connector.connected` + `copilot.hint.updated` (5 NEW event types target)

---

## DIMENSION 6 · Path A Scope ANTE architect approve

**Recommended proceed** · Path A 5 items confirmados empirical · estimated effort ~20-28h aligned con architect brief.

**Defer Future-X confirmados** (no bloqueantes MEDIA):
- Future-1.E.X.drp-cliente-ui-alta (~5-8h post-MEDIA piloto)
- Future-1.E.X.bia-cliente-form-alta (~5-8h post-MEDIA piloto)
- Future-1.E.X.auditlog-orchestrator-wire (~2-3h post-MEDIA piloto)

**No NEW gaps surface post-3B-2B.6** · arquitecturalmente todo bien aislado.

---

## Sign-off Phase 0

- **Methodology**: empirical grep + filesystem + Read tool · cero speculative claims (OPS-049)
- **Time budget Phase 0**: ~2h efectivos (target ~2-3h architect) · within range
- **Architect approve gate next**: Phase 1A · M01 Categorización sync admin↔cliente
- **Tag pending**: post-CLUSTER 1 cierre · Sesión 3B-2B.8 CLUSTER 1 commits 5-7 anticipados

**STOP-AND-REPORT** · architect approve Path A 5 items antes proceed Phase 1A.

---

**FIN Phase 0 Mega-Audit · cliente portal current state empirical re-validated** · branch `radar-v9` · post Sesión 3B-2B.6 CERRADO DEFINITIVO.
