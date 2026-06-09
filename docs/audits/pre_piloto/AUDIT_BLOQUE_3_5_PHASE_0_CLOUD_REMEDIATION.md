# AUDIT Bloque 3+5 Phase 0 · Cloud Remediation Feature Complete

**Status**: ✅ Phase 0 empirical re-verification CRÍTICO complete
**Date**: 2026-05-24
**Methodology**: find/cat/wc/head/tail/ls (NO grep) · OPS-052 strengthened doctrine
**HEAD base**: 1f3ad50 (post-Bloque 2 cierre)

---

## Verdict empírico CRÍTICO

**ADR-025 27ª aplicación · NO new "RemediationProposal" model needed**. CloudGap existing model **YA cubre 80% del proposal entity needs**:
- ✅ `suggested_action` field (deterministic · NO LLM)
- ✅ `auto_fixable` flag · `cliente_can_see` flag (KEY para cliente UI)
- ✅ `resolved_at` + `resolved_by_user_id` + `resolution_note` + `evidence_link_id`
- ✅ `raw_evidence` JSONB (ENAC trazabilidad)
- ✅ `explanation_es` (LLM enriched primer-principios)

**Gap específico vs full remediation flow**:
- 🟡 Falta `approval_status` (proposed · pending_approval · approved · rejected · executing · executed · failed)
- 🟡 Falta `proposed_to_cliente_at` + `cliente_approval_at` + `cliente_approval_user_id` timestamps
- 🟡 Falta dedicated `cloud_remediation_approval_logs` table para audit trail inmutable (state transitions)

**Scope refined MAJOR (Phase 0 OPS-045 50ª)**:
- **NEW plan**: extend CloudGap (3 cols) + NEW `cloud_remediation_approval_logs` table (audit trail) + orchestrator service usando CloudGap como proposal entity
- **NOT plan**: greenfield RemediationProposal model + duplicate fields
- **ETA refined**: ~3-5h backend (vs ~6-10h nominal · ahorro ~40% adicional sobre nominal audit) + ~3-5h frontend cliente UI

**Total refined cumulative Bloque 3+5**: **~6-10h** sostained pero scope distribuido distinto:
- Backend hoy: ~2-3.5h (extend CloudGap + new audit log table + orchestrator service + endpoints + tests)
- Frontend cliente mañana: ~3-5h (page + components + integration)

---

## Stats baseline existing 100% leveraged

### m_cloud_connectors (~4903 LOC) · production-grade ya verificado Audit #9
- `models.py` 397 LOC · 5 models (CloudConnector + CloudResource + **CloudGap** + CloudSyncJob + CloudDigestSnapshot)
- `api.py` 855 LOC · 6+ admin endpoints project-scoped
- `api_cliente.py` 267 LOC · 3 cliente endpoints (require_client_user · R29 firmísimo)
- `service.py` 554 LOC · CloudConnectorService + CloudConnectorNotFoundError + CloudGapNotFoundError + ...
- `diagnostic_gap_engine.py` 291 LOC · deterministic R1 produce CloudGap rows automated
- `gap_rules.py` 449 LOC · 8 reglas pure-function detectors
- `digest_service.py` 416 LOC · monthly snapshot
- `integrations.py` 960 LOC · cross-motor M03/M04/M07 K-light
- `tasks.py` 246 LOC · Celery scheduled

### m08_verification/remediation (~838 LOC) · production-grade
- `guide_generator.py` 363 LOC · Haiku PYME-friendly JSON
- `retest_runner.py` 347 LOC · retest quirurgico (ssl · cve · web · hardening · port)
- `sla_calculator.py` 100 LOC · SLA enforcement

### Frontend admin existing
- `/admin/projects/[id]/cloud-connectors/page.tsx` EXISTS (Audit #4 + 1.D.X.J)
- Components admin cloud-connectors panel + sync UI + gap list

### Frontend cliente
- `/(client-portal)/client-portal/*` 28 pages
- 🔴 NO `/client-portal/remediaciones/` page existing (gap)
- 🔴 NO `/client-portal/cloud-connectors/` page existing (probable gap minor)
- ✅ `useClientProjectEvents` hook (SSE) existing · reuse

### Sync infrastructure (Audit #9)
- SSE dispatcher 150 LOC audience-aware
- NotificationOrchestrator 427 LOC + 13 templates
- workflow_step_notifications graceful pattern
- m21 ClientNotification model + notifications_inbox_api

---

## Scope refinement post-Phase 0

### Backend HOY (~2-3.5h cumulative)

**1. Migration extend CloudGap + new audit log table** (~30 min)
- ALTER TABLE cloud_gaps:
  - ADD COLUMN approval_status VARCHAR(30) DEFAULT 'detected'
    (detected · proposed_to_cliente · approved · rejected · executing · executed · failed)
  - ADD COLUMN proposed_to_cliente_at TIMESTAMPTZ NULL
  - ADD COLUMN cliente_approval_at TIMESTAMPTZ NULL
  - ADD COLUMN cliente_approval_user_id UUID NULL
- CREATE TABLE cloud_remediation_approval_logs:
  - id UUID PK · gap_id FK · action VARCHAR · actor_user_id UUID · actor_type VARCHAR · timestamp + notes + metadata JSONB
  - RLS per project_id (via gap.project_id JOIN)
  - Indexes (gap_id · timestamp DESC · action)

**2. Models extend + new** (~30 min)
- Extend `CloudGap` ORM:
  - `approval_status: Mapped[str]` enum-like
  - `proposed_to_cliente_at: Mapped[datetime | None]`
  - `cliente_approval_at: Mapped[datetime | None]`
  - `cliente_approval_user_id: Mapped[uuid.UUID | None]`
- NEW `CloudRemediationApprovalLog` model

**3. Orchestrator service** (~1h)
- NEW `backend/app/motors/m_cloud_connectors/remediation_orchestrator.py` (~250 LOC):
  - `propose_to_cliente(gap_id, admin_user_id)` → set status + timestamp + log row + emit SSE event
  - `cliente_approve(gap_id, cliente_user_id, note)` → set status + log row + emit SSE event
  - `cliente_reject(gap_id, cliente_user_id, note)` → similar
  - `execute_remediation(gap_id, admin_user_id, executed_notes)` → log + status
  - `mark_executed(gap_id, admin_user_id, evidence_link_id)` → resolved_at + status
  - `mark_failed(gap_id, admin_user_id, error_notes)` → status + log
  - Per state transition emit SSE event audience-aware (admin/cliente)
  - Graceful pattern (reuse `_maybe_dispatch_notifications` style)

**4. API endpoints admin** (~30 min)
- POST `/admin/projects/{pid}/cloud-gaps/{gid}/propose-to-cliente`
- POST `/admin/projects/{pid}/cloud-gaps/{gid}/execute`
- POST `/admin/projects/{pid}/cloud-gaps/{gid}/mark-failed`
- GET `/admin/projects/{pid}/cloud-gaps/{gid}/audit-log` · list approval logs

**5. API endpoints cliente** (~15 min)
- POST `/client-portal/cloud-gaps/{gid}/approve`
- POST `/client-portal/cloud-gaps/{gid}/reject`

**6. Tests backend** (~45 min · 7-10 tests)
- test_propose_to_cliente_transitions_status
- test_propose_creates_audit_log_row
- test_propose_emits_sse_event_cliente
- test_cliente_approve_transitions_status
- test_cliente_cannot_approve_other_project
- test_execute_requires_approved_status
- test_audit_trail_complete_per_transition
- test_rls_per_project_scoped
- test_graceful_failure_doesnt_break

### Frontend cliente MAÑANA (~3-5h)
- NEW page `/client-portal/remediaciones/page.tsx`
- NEW components: `RemediationCard` + `RemediationsList` + `ApprovalModal`
- WIRE useClientProjectEvents SSE para `cloud_remediation_proposed` real-time
- API client `lib/api/cloud-remediations.ts`

### Admin frontend MAÑANA (~30 min · polish only)
- WIRE existing `/admin/projects/[id]/cloud-connectors/page.tsx` add "Propose to cliente" button per CloudGap row
- WIRE audit log expandable per gap
- NEW component opcional `GapProposalAuditTrail` reusing FASE C SubcontractsPanel pattern

---

## OPS-052 10ª manifestation NOT TRIGGERED

Phase 0 reveals scope refined sostained pattern audit-first OPS-045 50ª aplicación:
- Backend orchestrator scope reduce ~40% adicional sobre Audit #9 (already reduced from nominal)
- Models DON'T duplicate · extend CloudGap existing
- Frontend cliente UI ETA mantained ~3-5h
- 10ª OPS-052 manifestation NOT triggered ✅

ETA cumulative Bloque 3+5: **~5.5-8.5h total** (vs ~6-10h Audit #9 nominal · ahorro ~15% Phase 0)

---

## Implementation plan HOY · 3 commits

### Commit 1 · Migration + Models extend (~45 min)
- Migration alembic NEW · ALTER cloud_gaps + CREATE cloud_remediation_approval_logs + RLS + indexes
- Extend CloudGap model + NEW CloudRemediationApprovalLog model
- Update schemas.py si needed (new Pydantic types)

### Commit 2 · Orchestrator service + tests core (~1h)
- NEW `remediation_orchestrator.py` 250 LOC
- 7-10 backend tests verde

### Commit 3 · API endpoints admin + cliente + integration tests (~1h)
- Admin endpoints (propose-to-cliente · execute · mark-failed · audit-log)
- Cliente endpoints (approve · reject)
- Integration tests

**Total**: ~2.5-3h backend HOY · STOP HARD final del día post commit 3.

---

## Risk identification

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| CloudGap extend migration regression cross 5790 LOC | LOW-MEDIUM | HIGH | Migration additive only · NO drop columns · default values |
| Orchestrator scope creep mid-implementation | LOW | MEDIUM | Strict scope commit boundaries 45min/1h/1h |
| SSE event_type new conflict existing | LOW | LOW | Audience-aware filtering existing supports extension |
| Cliente auth `require_client_user` not project-scoped | LOW | MEDIUM | Verify RLS during integration test |

---

## Cross-ref

- Audit #9 source: `docs/audits/pre_piloto/AUDIT_08_CLOUD_REMEDIATION.md`
- Audit #10 sync source: `docs/audits/pre_piloto/AUDIT_09_ADMIN_CLIENTE_SYNC.md`
- Plan v3: `docs/audits/pre_piloto/PLAN_MACRO_v3_PRE_PILOTO_REFINED.md`
- CloudGap source: `backend/app/motors/m_cloud_connectors/models.py:211`
- DiagnosticGapEngine: `backend/app/motors/m_cloud_connectors/diagnostic_gap_engine.py`
- ADR-025 cement (NO new tables when extension possible)
- ADR-031 ENAC trazabilidad raw_evidence
- 1.D.G EXPANDED workflow_hooks pattern reuse

---

## Honest notes

1. Phase 0 NO inspeccionó gap_rules.py 8 reglas detalle · audit demand-driven cuando wire
2. Migration alembic strategy verified pattern existing (additive only · safe)
3. Cliente UI MAÑANA scope mantained ~3-5h · NO Phase 0 reduction
4. Frontend admin existing reuse · solo polish ~30 min
