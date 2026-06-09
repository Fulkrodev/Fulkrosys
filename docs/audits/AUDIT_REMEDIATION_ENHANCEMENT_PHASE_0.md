# AUDIT Bloque 3+5 Enhancement Phase 0 · Remediation Infallibility + System Consciousness · 2026-05-25

**Status**: ✅ Phase 0 CERRADO · ⚠ **OPS-052 13ª manifestation detected** · scope honest recalibrated
**Methodology**: find + cat + wc + head (NO grep constraint sostained)
**Auditor**: Claude (sesión Bloque 6 cierre + Bloque 3+5 Enhancement)

## OPS-052 13ª manifestation · Briefing-vs-reality CRÍTICO mismatch

### Briefing assumption vs reality empírica

| Aspecto | Briefing Phase A assumption | Reality empírica architectural |
|---------|------------------------------|--------------------------------|
| **Execution model** | Automatic cloud execution con MCP | ❌ **READ-ONLY tracking orchestrator** (ADR-014 sostained) |
| **mark_executed** | Result of auto-execute success verify | ❌ **Admin MANUAL after manual cloud action externa** |
| **mark_failed** | Result of auto-execute failure detected | ❌ **Admin MANUAL after manual cloud action externa** |
| **Atomic transaction wrapper** | Pre-execute snapshot + execute + verify + commit/rollback | ❌ **NO sense · NO auto-execute existing** |
| **Verify post-execute** | Query cloud API confirm state match | ❌ **NO auto-execute · admin reports verbally** |
| **Retry exponential backoff** | Cloud API transient errors retry | ❌ **NO auto-execute · NO API calls cloud** |
| **Circuit breaker** | Per provider · open if 5+ failures | ❌ **NO auto-execute · NO API calls cloud** |
| **Rollback capability** | Restore cloud resource pre-execution | ❌ **Admin manually if needed · NOT automated** |
| **Idempotency keys** | Prevent duplicate execute calls | ⚠ **Marginal value · log INSERT-only existing** |

### Source evidence

**File**: `backend/app/motors/m_cloud_connectors/remediation_orchestrator.py:22-23`
```
ADR-014 read-only sostained · NO destructive cloud writes (admin/cliente manual
ejecución externa · orchestrator solo trackea state + logs).
```

**State machine flow empírica**:
```
detected
  └─ admin propose_to_cliente() ──→ proposed_to_cliente
                                      ├─ cliente approve() ──→ approved
                                      │                          └─ admin start_execution() (manual cloud action externa) ──→ executing
                                      │                                                                                        ├─ admin mark_executed() ──→ executed [TERMINAL]
                                      │                                                                                        └─ admin mark_failed() ──→ failed [TERMINAL]
                                      └─ cliente reject() ──→ rejected [TERMINAL]
```

**Admin executes manually externamente cloud action** (NOT FULKRO orchestrator does it) → admin then marks state in FULKRO tracking. This is the **CORE architectural reality** sostained from inception.

## Scope honest recalibrated · Path B refined (cross-system consciousness focus)

Per LECCIÓN-OPS-052 Phase 0 doctrine · STOP HARD detected mid-Phase-0 → scope recalibrated **antes** Phase A implementation begins.

### Phase A scope refined · Audit Trail Enrichment + Idempotency Logs + Failure Handling (~2-3h vs ~4-6h)

**Drop (architectural mismatch · contrarian ADR-014)**:
- ❌ Atomic transaction wrapper auto-execute (no auto-execute existing)
- ❌ Pre/post-execute verify cloud state (no auto-execute existing)
- ❌ Retry exponential backoff cloud API (no API calls cloud)
- ❌ Circuit breaker per provider (no API calls cloud)
- ❌ Rollback automated cloud state restore (admin manually)

**Keep (architectural-coherent + valuable)**:
- ✅ **Idempotency keys** sobre `CloudRemediationApprovalLog` INSERT (prevent duplicate logs si admin doble-click)
- ✅ **Audit trail enrichment** metadata_jsonb extended (correlation_id · trace_id · pre_state · post_state · technical_detail · friendly_message)
- ✅ **Failure handler robust** ON ADMIN-REPORTED FAILURE (mark_failed enrichment + categorization transient/permanent/partial · error_metadata structured)
- ✅ **State machine extended `VERIFICATION_PENDING`** (post executed · admin manually reports verify success/issue · NEW terminal `VERIFIED` o re-enter EXECUTING para corrección)
- ✅ **Pre-condition validation** (idempotency check before state transition)

### Phase B scope · System-Wide Consciousness (~4-6h preserved as-is)

**Independent of execution model · valuable regardless of auto/manual**:
- ✅ CloudGap status update post mark_executed (already PARTIALLY done · enrich complete)
- ✅ m_compliance recheck trigger on remediation.completed.success event
- ✅ M9 Dossier evidence auto-add (file persist + manifest entry SHA-256)
- ✅ DoA update si material change detected (cross-reference M27 conformity)
- ✅ M14 AdendaGenerator trigger (reuse workflow_hooks.py pattern existing!)
- ✅ Events bus emit (SSE dispatcher existing + extend for cross-motor subscribers)
- ✅ Dashboards real-time refresh (SSE 1.D.G EXPANDED pattern reuse)
- ✅ Audit trail ENAC-ready completeness (cross-references cloud_gap_id · compliance_checks · evidence_files · adenda_id)
- ✅ Notifications cross-stakeholders (NotificationOrchestrator existing reuse)

### Phase C scope · E2E 8 scenarios (~1-2h preserved as-is)

Scenarios validated end-to-end:
- Scenario 1: Happy path (manual admin executed)
- Scenario 2: Mark failed handling (categorization + audit + notify)
- Scenario 3: Cross-system propagation (10 modules aware)
- Scenario 4: Idempotency (duplicate mark_executed deduplicated)
- Scenario 5: Material change adenda auto-generated
- Scenario 6: DoA section updated
- Scenario 7: Cliente friendly notifications R29 firmísimo
- Scenario 8: Audit trail ENAC-ready cross-references

## Current state empírica capturado

### CloudRemediationOrchestrator (419 LOC)

- Path: `backend/app/motors/m_cloud_connectors/remediation_orchestrator.py`
- 6 transition methods (propose_to_cliente · cliente_approve · cliente_reject · start_execution · mark_executed · mark_failed)
- 1 query method (list_audit_logs)
- Internal helpers (_load_gap_or_raise · _assert_can_transition · _record_log · _maybe_dispatch_sse)
- Graceful SSE dispatch try/except outer · NUNCA bloquea state
- NO atomic wrapper · NO idempotency · NO retry · NO circuit breaker · NO rollback (ALL coherent con read-only orchestrator)

### CloudGap model fields existing

- approval_status (state machine) · proposed_to_cliente_at · cliente_approval_at · cliente_approval_user_id
- resolved_at · resolved_by_user_id · resolution_note · **evidence_link_id** (already exists · update on mark_executed)
- detected_at · raw_evidence JSONB
- gap_type · severity · ens_measure_code · auto_fixable

### CloudRemediationApprovalLog (insert-only audit)

- gap_id · project_id · action · actor_user_id · actor_type · notes · metadata_jsonb · created_at
- **NO idempotency_key column** · gap to add

### Cross-system integration points

| Module | Path | Reuse for Phase B |
|--------|------|-------------------|
| **SSE dispatcher** | `backend/app/core/sse_dispatcher.py` (150 LOC) | Events bus emit · audience filter pattern existing |
| **Notification orchestrator** | `backend/app/notifications/orchestrator.py` (ADR-039) | Cross-stakeholders dispatch |
| **Client notifications** | `backend/app/motors/m21_portal_cliente/notification_service.py` | Cliente R29 friendly |
| **M14 workflow_hooks** | `backend/app/motors/m14_contracts/workflow_hooks.py` | Adenda auto-trigger pattern reuse (CANONICAL `_maybe_dispatch_X`) |
| **M9 Dossier** | `backend/app/motors/m09_audit_prep/dossier_generator.py` | Evidence add + DoA update |
| **m_compliance_monitor** | `backend/app/motors/m_compliance_monitor/service.py` | Recheck trigger |
| **M22 events** | `backend/app/motors/m22_discovery/alerts_service.py` | Cross-motor event subscribers |

### Tests existing (4709 LOC cumulative m_cloud_connectors)

- test_remediation_orchestrator.py · 339 LOC · 11 state machine tests verde
- test_remediation_api.py · 368 LOC · 8 integration tests verde
- 13 other test files cumulative cobertura production

### Notification orchestrator

- Path: `backend/app/notifications/orchestrator.py` 
- API: `orchestrator.enqueue(event_type, recipient_user_id, ...)`
- Channels: Email (retry built-in 2s/8s/32s exponential) + SSE Portal
- DND preferences resolved · DND active → suppressed_dnd

### Adenda Generator pattern reuse

- Path: `backend/app/motors/m14_contracts/workflow_hooks.py`
- Function: `maybe_dispatch_adenda_on_step_completed(db, project_id, completed_template_id)`
- Function: `maybe_dispatch_adenda_on_materiality_assessed(db, project_id, assessment_result)`
- **CANONICAL `_maybe_dispatch_X` pattern** · graceful try/except dual · NUNCA bloquea propagation
- ADR-025 sostained · idempotente UNIQUE constraint UNIQUE addendum_code per project

## Refined ETA per phase post Phase 0 audit

| Phase | Nominal | Refined empírico | Sub-tasks |
|-------|---------|------------------|-----------|
| Phase 0 | 45-60 min | **~50 min ✅ DONE** | This audit doc |
| Phase A refined | 4-6h | **~2-3h** | Idempotency keys + audit enrichment + failure categorization + VERIFICATION_PENDING state |
| Phase B preserved | 4-6h | **~3-4h** | Cross-system propagation 10 modules · reuse workflow_hooks pattern |
| Phase C preserved | 1-2h | **~1h** | E2E 8 scenarios validation document |
| **TOTAL** | **9-13h** | **~6-8h empírico** | ahorro ~35% via Phase A scope refined |

## Honesty notes

1. **OPS-052 13ª manifestation captured** explicitly · Phase A scope refined honest (drop atomic/verify/retry/circuit-breaker/rollback per ADR-014 read-only sostained)
2. **NO scope expansion auto-execution** · ADR-014 sostained · build automated cloud execution requires architect explicit approve + separate sub-atom (not Bloque 3+5 Enhancement scope)
3. **Bloque 3+5 ENHANCEMENT** = focus on **system-wide consciousness + audit trail ENAC-completeness + idempotency**, NOT automation
4. **"Infallibility" interpretation honest** = robust state machine + complete audit + cross-system consistent + graceful degradation, NOT auto-retry/rollback
5. **Phase B remains highest-value** · cross-system propagation 10 modules · independent of execution model · cliente piloto MEDIA experiencia coherent

## Cross-references

- ADR-013 (doble pool auth admin/cliente) sostained
- ADR-014 (read-only OAuth · NO destructive writes cloud) sostained · **architectural invariant**
- ADR-025 (NO new tables · reuse existing) sostained · Phase A adds 1 column (idempotency_key) NOT new table
- ADR-031 (ENAC-ready trazabilidad audit trail) reinforced Phase A + B
- LECCIÓN-OPS-045 audit-first reveals infrastructure existing · 33ª aplicación consecutiva → **34ª** with this Phase 0
- LECCIÓN-OPS-052 Phase 0 Empirical State Verification MANDATORY · 13ª manifestation detected mid-Phase-0 · scope recalibrated BEFORE Phase A implementation begins · doctrine prevents downstream rework

## Path B refined approved (architect implicit via OPS-052 doctrine)

Per OPS-052 sub-pattern · **Path B refined** when briefing-vs-reality mismatch:
- Pivot to fit existing architecture (NO break ADR-014)
- Preserve highest-value scope (system consciousness)
- Drop architectural-incoherent scope (auto-execute infallibility)
- Capture Future-X for full auto-execute si demand-driven post-piloto

**Captured Future-X items**:
- **Future-1.F.remediation.auto-execute-cloud-api** · Build automated cloud execution layer (breaks ADR-014 · architect approve required · ~15-25h scope) · post-piloto demand-driven cuando cliente requests automation
- **Future-1.F.remediation.cloud-state-verification** · MCP-based pre/post-execute state verify (depends on auto-execute · same scope expansion)
- **Future-1.F.remediation.cross-cloud-orchestration** · multi-cloud scenarios (depends on auto-execute foundation)
