# AUDIT Ejecutable 5 Phase 10.0 · Sesión 3B-2B.10 Simulacro Pre-ENAC State Empirical

**Fecha**: 2026-05-27
**Sesión**: Ejecutable 5 · Sesión 3B-2B.10 Audit Simulacro Pre-ENAC orchestrator delgado
**Status**: Phase 10.0 audit COMPLETO · proceed Phase 10.1 implementation

## 5 EXISTING services empirical verified (reuse candidates)

| # | Service | File | LOC | Signature verified |
|---|---------|------|-----|--------------------|
| 1 | `AuditDryRunService.execute_dry_run` | `agents/services/audit_dry_run_service.py:83` | 355 | `async (self, project_id: UUID, executor_id: UUID \| None = None) → DryRunResult` |
| 2 | `compute_dda_evidence_gaps` | `m09_audit_prep/dda_evidence_gap_service.py:334` | 598 | `async (db, project_id, *, options=None) → DdaEvidenceGapMatrix` |
| 3 | `compute_workflow_state` | `m11_copiloto/workflow_state_scanner.py:546` | - | `async (db, project_id, options=None) → WorkflowState` · role_filter via options |
| 4 | `generate_draft_audit_report` | `m09_audit_prep/draft_report_generator.py:855` | 886 | `async (db, project_id, *, options=None) → DraftReportBytes` |
| 5 | `AuditDryRunDashboard` | `frontend/components/audit-dry-run/AuditDryRunDashboard.tsx` | 266 | React tanstack-query · current single-view layout |

**OPS-026 DRY status**: All 5 services explicitly document Sesión 3B-2B.10 simulacro Pre-ENAC engine como reusable consumer target (docstrings + comments inline). Architect briefing 100% aligned con empirical.

## Briefing mismatches < 30% (NO STOP HARD per OPS-052)

1. **Path mismatch**: briefing `frontend/components/audit-prep/` → empirical `frontend/components/audit-dry-run/` (minor · just folder naming)
2. **AuditDryRunService location**: briefing implies M10+A11 motor · empirical `agents/services/` (architecturally correct as orchestrator agent)
3. **Ed25519 vs SHA-256**: briefing "hash chain Ed25519 verify R6" · empirical PostgreSQL trigger uses **SHA-256** via `digest(payload, 'sha256')` (existing `fn_audit_log_hash_chain` + `fn_audit_log_verify_chain` desde migration `d4f8b2a90001`). Ed25519 is M05 PDF signing (separate concern). **Decisión adapt**: integrity_checker usa SHA-256-based `fn_audit_log_verify_chain` + supplementary verify · NOT Ed25519 (R6 hash chain inviolable preserved · algorithm differs)

## fn_audit_log_verify_chain PostgreSQL function (HUGE OPS-045 reveal)

**Discovery empirical**: integrity checker es ~75% EXISTING en PostgreSQL nativo.

Migration `d4f8b2a90001_audit_log_hash_chain_trigger.py` ya creó:

```sql
CREATE FUNCTION fn_audit_log_verify_chain(
    OUT total BIGINT,
    OUT first_bad_seq BIGINT,
    OUT ok BOOLEAN
) ...
```

Iterates rows by `seq` order · computes expected hash · compares con `hash_current` · returns first bad seq si chain corrupted.

**Triggers immutability**:
- `tg_audit_log_no_update` · BEFORE UPDATE rejects (RAISE EXCEPTION)
- `tg_audit_log_no_delete` · BEFORE DELETE rejects
- `tg_audit_log_hash_chain` · BEFORE INSERT computes hash

**audit_log schema empirical (13 cols)**:
- `id` uuid · `tabla` varchar · `registro_id` uuid · `accion` varchar · `usuario` varchar · `timestamp` timestamptz · `payload_old` jsonb · `payload_new` jsonb · `hash_prev` varchar · `hash_current` varchar · `seq` bigint · `project_id` uuid · `client_id` uuid

R6 hash chain **canónicamente preserved** post Sub-atom 5.A 3-way OR (project_id + client_id added · hash function unchanged).

## NEW services scope refined (post-audit)

### Phase 10.1 · audit_log_integrity_checker
- **Scope refined**: Pure functional wrapper sobre existing `fn_audit_log_verify_chain` + add project-scoped variant (filter rows WHERE project_id = X)
- **NEW file**: `m09_audit_prep/audit_log_integrity_checker.py` (~80 LOC)
- **Function**: `async check_audit_log_integrity(db, project_id=None, since_seq=None) → IntegrityReport`
- **Dataclass**: `IntegrityReport(ok: bool, total_rows: int, first_bad_seq: int | None, project_id: UUID | None, since_seq: int | None)`
- **Tests scope**: 4-6 tests (happy path global + per-project + tampered detection + immutability trigger verify + since_seq filter)

### Phase 10.2 · corrective_loop_service
- **Scope refined**: NEW state machine · canonical canonical `open → in_progress → closed`
- **NEW file**: `m09_audit_prep/corrective_loop_service.py` (~150 LOC)
- **Pattern**: P-CL2-3 (state machine) + Pattern Phase 1D (pure functional · NO HTTP coupling)
- **State persistence**: Reuse existing `audit_log` events (NO new table · OPS-026 DRY · ADR-025 sostained) + optional `corrective_loop_state` derive from events
- **Functions**:
  - `async open_loop_for_gap(db, project_id, gap_id, gap_type, severity) → LoopState`
  - `async transition_loop(db, loop_id, to_state) → LoopState`
  - `async list_open_loops(db, project_id) → list[LoopState]`
  - `async close_loop(db, loop_id, resolution_note) → LoopState`
- **Tests scope**: 4-6 tests (open → in_progress → closed cycle + invalid transitions guard + audit_log events emitted + per-project filter)

### Phase 10.3 · SimulacroPreEnacService orchestrator delgado
- **Scope refined**: Pure functional orchestrator composing 5 existing + 2 nuevos · ~80 LOC
- **NEW file**: `m09_audit_prep/simulacro_pre_enac_service.py` (~80 LOC)
- **Function**: `async run_simulacro_pre_enac(db, project_id) → SimulacroReport`
- **Pipeline**:
  1. AuditDryRunService.execute_dry_run · 30-90s
  2. compute_dda_evidence_gaps · gap matrix
  3. compute_workflow_state(role_filter='admin')
  4. check_audit_log_integrity NEW (Phase 10.1)
  5. open_loop_for_gap NEW (Phase 10.2) per critical gap detected
  6. generate_draft_audit_report con title_override='Simulacro Pre-ENAC'
- **Tests scope**: 3-4 tests (orchestrator happy path + composition + PDF generated + audit_log events emitted)

### Phase 10.4 · Frontend AuditDryRunDashboard extend tab
- **Scope refined**: Wrap existing dashboard en Tabs · add tab "Simulacro Pre-ENAC"
- **MODIFY file**: `frontend/components/audit-dry-run/AuditDryRunDashboard.tsx` (266 → ~400 LOC)
- **NEW file**: `frontend/components/audit-dry-run/SimulacroPreEnacTab.tsx` (~150 LOC)
- **NEW API client**: `frontend/lib/api/simulacro-pre-enac.ts` (~50 LOC)
- **NEW backend endpoint**: `POST /api/v1/admin/projects/{id}/simulacro-pre-enac/execute` + `GET .../report`
- **Tests Playwright**: 3 (tab renders + trigger executes + report visualization)
- **WCAG axe-CI 0 violations target**

## Pattern reuse formalized (OPS-026 DRY · ADR-025 sostained)

- **Pattern Phase C3 pure functional reuse**: compute_dda_evidence_gaps + compute_workflow_state + generate_draft_audit_report all pure functional · NO HTTP coupling · accept db session + project_id · reusable cross-context
- **Pattern P-CL2-4 ENRICH existing landing**: AuditDryRunDashboard extend tab NO new route (per architect briefing)
- **Pattern #18 state machine (3B-2B.8 Phase 3A reuse)**: corrective_loop open→in_progress→closed transitions canonical
- **Sub-atom 5.A audit_log 3-way OR**: simulacro events propagate project_id + client_id (cross-suite visibility)

## OPS-045 audit-first 51ª aplicación projection

- Nominal scope: ~6-9h cumulative Phase 10.1-10.4
- Empirical projection likely ~1.5-2h (-85% sostained · per architect briefing)
- Infrastructure existing 70-75% (5 services ready · `fn_audit_log_verify_chain` ya existe · audit_events.py canonical namespace ya extends)

## Sub-atom 5.A audit_log canonical events NEW

Adding to `m09_audit_prep/audit_events.py`:
- `SIMULACRO_PRE_ENAC_EXECUTED = "simulacro.pre_enac.executed"`
- `SIMULACRO_PRE_ENAC_REPORT_GENERATED = "simulacro.pre_enac.report_generated"`
- `AUDIT_INTEGRITY_CHECKED = "audit.integrity.checked"`
- `CORRECTIVE_LOOP_OPENED = "corrective.loop.opened"`
- `CORRECTIVE_LOOP_IN_PROGRESS = "corrective.loop.in_progress"`
- `CORRECTIVE_LOOP_CLOSED = "corrective.loop.closed"`

6 NEW canonical events · 39 cumulative auditor portal events post-Sesión 3B-2B.10.

## Cross-suite regression preserved

- Existing audit_dry_run tests · NO modification (read-only consumer)
- Existing dda_evidence_gap tests · NO modification
- Existing workflow_state_scanner tests · NO modification
- Existing draft_report_generator tests · NO modification
- NEW tests scope: ~13-16 tests cumulative Phase 10.1-10.4
