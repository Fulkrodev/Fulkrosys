# AUDIT Ejecutable 6 Phase 11.0 · Sync Hardening State Empirical

**Fecha**: 2026-05-27
**Sesión**: Ejecutable 6 · Sesión 3B-2B.11 Sync Hardening P1 items 1+4+5 críticos
**Status**: Phase 11.0 audit COMPLETO · proceed Phase 11.1 implementation

## Item 1 · SSE reconnection resilience (60% greenfield · 40% existing)

### Existing infrastructure empirical

- **Frontend**: `frontend/hooks/useClientProjectEvents.ts` (388 LOC) usa native browser `EventSource` API
- **Backend**: `backend/app/api/v1/sse_client_api.py` (111 LOC) + `sse_api.py` (86 LOC) endpoints SSE
- **Dispatcher**: `backend/app/core/sse_dispatcher.py` (238 LOC) singleton in-memory pub-sub
- **Browser EventSource** auto-reconnects default ~3s linear (NO jitter)
- **error handler**: `source.onerror = () => { /* EventSource auto-reconnects */ }` · NO custom logic

### Gaps empirical (Phase 11.1 scope)

| Gap | Status | Impact |
|-----|--------|--------|
| Per-event `event_id` sequencing | ❌ NO sequencing | Cannot identify gaps post-disconnect |
| Replay buffer per channel | ❌ NO buffer | Events lost during disconnect window |
| `Last-Event-ID` backend handling | ❌ NO handler | Browser sends header pero backend ignores |
| Custom backoff jitter | ❌ Default 3s linear | Thundering-herd risk multi-client reconnect |
| `subscribe()` signature accepts `last_event_id` | ❌ NO param | Cannot resume from cursor |

### Phase 11.1 scope refined

- Backend: extend `SseDispatcher.dispatch` con `event_id` UUID generation + ring-buffer per channel (`deque(maxlen=100)`)
- Backend: extend `SseDispatcher.subscribe(channel, last_event_id=None)` con replay logic
- Backend: SSE endpoints honor `Last-Event-ID` header desde Request
- Frontend: NO custom backoff needed - browser EventSource native + `Last-Event-ID` automatic
- Tests: ring-buffer cap respect + backfill on resume + event_id propagation

## Item 4 · Concurrent admin races (20% greenfield · 80% existing PROTECTED)

### CRITICAL EMPIRICAL FINDING (>30% briefing mismatch · OPS-052 manifestación 71ª)

**audit_log chain race CONDITION ALREADY PROTECTED** via PostgreSQL trigger:

```sql
-- Migration d4f8b2a90001_audit_log_hash_chain_trigger.py line 66
CREATE OR REPLACE FUNCTION fn_audit_log_hash_chain() RETURNS trigger
LANGUAGE plpgsql AS $fn$
DECLARE
    last_hash TEXT;
    payload   TEXT;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtext('audit_log_chain'));  -- ✅ SERIALIZES all inserts
    SELECT hash_current INTO last_hash FROM audit_log
      WHERE seq = (SELECT MAX(seq) FROM audit_log WHERE seq < NEW.seq);
    ...
```

`pg_advisory_xact_lock` at trigger BEFORE INSERT serializes ALL audit_log inserts globally per transaction. Race condition impossible · R6 hash chain inviolable preserved at trigger level.

**Briefing assumed**: "audit_log chain_index calc current pattern (likely SELECT MAX without FOR UPDATE)"
**Empirical reveals**: chain race ALREADY solved via advisory lock pattern (correct architectural choice · advisory lock is the canonical PostgreSQL approach for global serialization vs FOR UPDATE row-lock)

### Other critical mutations empirical state

| Mutation | Race protection | Phase 11.2 scope |
|----------|-----------------|------------------|
| `audit_log` insert chain | ✅ `pg_advisory_xact_lock` | SKIP (already protected) |
| `corrective_loops` state transition | ❌ NO advisory lock | ADD advisory lock pattern (mirror audit_log) |
| `NotificationEvent.retry_count` increment | ❌ Python-side `event.retry_count += 1` | Document risk + recommend atomic SQL UPDATE |
| `project_lifecycle_events` phase transition | ❓ INVESTIGATE | Verify pattern · add lock si needed |
| FOR UPDATE row locks in motors | ❌ Empirical grep returns 0 files | NOT systemic · per-case |

### Phase 11.2 scope refined

- Add `pg_advisory_xact_lock(hashtext('corrective_loops_' || project_id))` pattern in `transition_loop` (mirror audit_log pattern · per-project serialization avoids global bottleneck)
- Document NotificationEvent retry_count race risk + add atomic SQL UPDATE recommendation
- Tests backend (~3-4): concurrent corrective_loops transition simulation + ordered state machine + audit_log chain inviolable preserved post concurrent

## Item 5 · DLQ minimal notifications (100% greenfield)

### Existing infrastructure empirical

- **NotificationOrchestrator** `backend/app/notifications/orchestrator.py` (427 LOC)
- **Celery tasks** `backend/app/notifications/tasks.py` (392 LOC) · `max_retries=3, countdown=60`
- **NotificationEvent** model existing con `status`, `retry_count`, `error`, `channels_attempted`, `channels_failed` columns
- **EmailSender retry** built-in (2s · 8s · 32s exponencial existing per orchestrator docstring)
- **NO `notification_dead_letter` table** empirical · grep results 0 matches

### Phase 11.3 scope confirmed

- NEW Alembic migration · `notification_dead_letter` table (event_type + payload + channels_attempted + last_error + retry_count + created_at + resolved_at + resolved_by_user_id)
- NotificationOrchestrator extend: si `notification_event.status='failed'` AND `retry_count >= MAX_RETRIES` → persist DLQ row
- Backend API: `GET /admin/notifications/dlq` (list) + `POST /admin/notifications/dlq/{id}/reprocess` (re-queue) + `POST /admin/notifications/dlq/{id}/resolve` (mark resolved manual)
- Frontend admin: widget visibility failed notifications (count + recent list)
- Tests backend (~3-4): retry cycle + DLQ persistence + admin visibility + manual reprocess endpoint
- audit_log emit `notification.dlq.persisted` + `notification.dlq.reprocessed` + `notification.dlq.resolved`

## OPS-045 audit-first 52ª aplicación projection

- Nominal scope: ~9-11h cumulative Phase 11.1-11.3
- Empirical projection likely ~1.5-2h (-85% sostained per architect briefing)
- Infrastructure existing 40-80% per item (Item 1: 40% · Item 4: 80% PROTECTED · Item 5: 0%)

## Scope refined per empirical findings

| Phase | Briefing scope | Empirical scope | Reduction |
|-------|---------------|-----------------|-----------|
| 11.1 SSE resilience | Custom backoff + resume token + backfill (~30-45 min) | event_id + ring-buffer + Last-Event-ID handling (~25-35 min) | -15% |
| 11.2 Concurrent races | audit_log FOR UPDATE + workflow_step (~30-45 min) | corrective_loops advisory lock + audit_log race CONFIRMED protected (~20-25 min) | -50% (audit_log already protected) |
| 11.3 DLQ minimal | NEW table + admin + reprocess (~30-45 min) | NEW table + extend orchestrator + admin widget + reprocess (~25-35 min) | -10% |

## Doctrinas honored

- **OPS-052 manifestación 71ª**: Phase 11.0 audit-first reveals audit_log chain race ALREADY PROTECTED via advisory lock (briefing assumption wrong · scope refined NO STOP HARD warranted dado item 4 broader scope)
- **OPS-026 DRY**: corrective_loops advisory lock pattern reuse del audit_log existing pattern
- **OPS-049 honest path**: Briefing mismatch documented transparent (>30% on sub-item · NOT on overall Item 4 scope)
- **R6 hash chain inviolable**: Empirical preserved via advisory lock at trigger level
- **Sub-atom 5.A audit_log 3-way OR**: All NEW events propagate project_id + client_id

## DEFER items 7/9/10 post-piloto Future-X (contrastados duplicidad)

Per architect briefing · 3 items DEFER post-piloto demand-driven · NO defers casuales:

1. `Future-Sesión-3B-2B.11.item-7-cliente-portal-multi-device-sync` (~2-3h post-piloto · duplicidad cubre 80% via SSE realtime existing)
2. `Future-Sesión-3B-2B.11.item-9-llm-deterministic-replay` (~3-5h post-piloto · duplicidad cubre via temperature ≤0.2 R3 + prompt cache existing)
3. `Future-Sesión-3B-2B.11.item-10-cross-region-failover` (~5-8h post-piloto · duplicidad cubre via single-region Hetzner FASE J + backup mensual probado R8)
