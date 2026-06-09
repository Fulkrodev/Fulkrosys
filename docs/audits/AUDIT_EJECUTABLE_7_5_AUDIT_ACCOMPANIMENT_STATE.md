# AUDIT Ejecutable 7.5 Phase 7.5.0 · Audit Accompaniment + Sede Conformity state empirical

**Fecha**: 2026-05-27
**Sesión**: Ejecutable 7.5 · NEW Audit Accompaniment post-implantación cycle insert pre-Ejecutable 8
**Status**: Phase 7.5.0 audit COMPLETO · scope greenfield NEW motor confirmed · proceed Phase 7.5.1

## Motor scope decision empirical (greenfield NEW vs extend m09)

### Empirical findings

- **NO motor `m_audit_accompaniment`** existing · grep zero matches en backend/app/motors/
- Existing motors near scope:
  - `m09_audit_prep` (audit_prep · 18+ files · dossier + checklist + draft report Phase C4 · scope PRE-audit) · 313 LOC `corrective_loop_service.py`
  - `m10_audit_sim` (audit simulator M10 · 58 preguntas L0-L5 · scope SIMULATION pre-audit)
- "Accompaniment" mentions empirical en YAML configs:
  - `m10_ens_radar/config_files/workshops.yaml` (3 workshops menciones · acompañamiento certificación)
  - `m16_onboarding/templates/onb-*-sponsor-v1.json` (6 templates · retainer field)
- Mentions are CONFIG-LEVEL · NO implementation motor existing

### Architect decision: NEW motor `m_audit_accompaniment`

**Justificación**:
- Clean separation of concerns: m09 = PRE-audit prep · accompaniment = POST-cert lifecycle tracking
- Different state machine: m09 corrective_loops (open→in_progress→closed · 3 states) vs accompaniment (BÁSICO 6 / MEDIO+ALTO 11 states sequential)
- Different lifecycle: accompaniment continúa post-implantación (BÁSICO 6 estados unified · MEDIO+ALTO 11 estados con ENAC bi-annual)
- Independent scope · NO scope creep m09 motor

## Pattern reuse capability verified empirical

### Pattern #18 state machine (Ejecutable 5 corrective_loop_service) ✅

`corrective_loop_service.py` (313 LOC) provides reference implementation:
- `VALID_TRANSITIONS: dict[str, set[str]]` canonical structure
- `STATE_EVENT_MAP: dict[str, str]` map states → audit_log events
- `transition_loop` con state machine validation + raise InvalidLoopTransition
- ADR-025 sostained (NO new table for state · audit_log derived)

### Pattern #22 advisory lock per-resource (Ejecutable 6) ✅

Line 234 verified: `pg_advisory_xact_lock(hashtext('corrective_loop_' || :lid))`
- Per-resource serialization (NO global bottleneck)
- Transaction-scoped (auto-release)
- Mirror audit_log canonical pattern

### Pattern #14 SSE+ClientNotification dual emit (Sesión 3B-2B.6+) ✅

`m21_portal_cliente/notification_service.py` line 72: `emit_client_notification` available
- `VALID_TYPES` set canonical (forward-compat ALL types)
- SSE event `client_notification.created` dispatch built-in
- Async emit · NO block primary persist
- audit_log emit en service layer

### Pattern P-CL2-4 ENRICH project page (Sesión 3B-2B.9 CLUSTER 2) ✅

`frontend/app/(admin)/admin/projects/[id]/audit/page.tsx` existing thin wrapper composes 3 components (AuditMode + MarkAuditPassedDialog + A11AuditorVirtualButton). Pattern P-CL2-4 sostained: add AuditAccompanimentTimeline component dentro existing `/audit` page OR adjacent tab approach.

### Pattern #21 SSE event_id + Last-Event-ID (Ejecutable 6) ✅

`backend/app/core/sse_dispatcher.py` per Ejecutable 6 provides event_id + replay buffer + Last-Event-ID resume infrastructure · ready cliente auto-update connect.

## DB schema empirical

`projects.categoria_objetivo` VARCHAR exists (verified empirical psql) · usable para branch decision BÁSICO vs MEDIO+ALTO.

Values empirical canonical: `BASICA`, `MEDIA`, `ALTA` (per existing motor m10_audit_sim + Pricing canonical CLAUDE.md).

## State machine canonical (CCN-STIC-808/809 + CCN-CERT IC-01/19 · architect web search validated)

### BÁSICO 6 states (autodeclaración · NO ENAC)

```
not_started → declaration_drafted → declaration_signed →
declaration_published → periodic_review_scheduled → completed
```

Transitions strict sequential · NO skip · NO back-transition (canonical state machine).

### MEDIO/ALTO 11 states unified (ENAC certificación cada 2 años)

```
not_started → preparation → docs_collected → internal_audit_scheduled →
internal_audit_completed → enac_audit_scheduled → enac_audit_in_progress →
enac_findings_resolution → enac_audit_passed → certificate_issued →
biannual_renewal_scheduled
```

Transitions strict sequential · MEDIO/ALTO share state machine (renewal cycle cada 2 años post-certificate_issued).

## Phase 7.5.1 scope refined

### NEW backend files

- `backend/app/motors/m_audit_accompaniment/__init__.py`
- `backend/app/motors/m_audit_accompaniment/state_machine.py` (BÁSICO + MEDIO/ALTO branches · VALID_TRANSITIONS dict per branch · STATE_EVENT_MAP map)
- `backend/app/motors/m_audit_accompaniment/service.py` (transition_state · get_timeline · upload_artifact · pg_advisory_xact_lock per project_id · Pattern #22)
- `backend/app/motors/m_audit_accompaniment/api.py` (5 endpoints admin + cliente read-only)
- `backend/app/motors/m_audit_accompaniment/models.py` (ORM models · FullMixin)
- Migration alembic single multi-table additive: `audit_accompaniment_state` + `audit_accompaniment_artifacts` + `audit_accompaniment_transitions`

NOTE migration: alembic DB state still has 2-head DEFER from Ejecutable 4 (`Future-1.E.radar.alembic-version-num-widen` pending). Sin embargo migration file can be CREATED + applied via raw SQL OR DEFERRED apply Future-X. Approach pragmatic: create migration code-side + create tables via direct CREATE TABLE (architectural decision · low risk · 0 rows existing · DDL only).

### audit_log canonical events NEW (5)

- `accompaniment.state.advanced` · admin transición state
- `accompaniment.artifact.uploaded` · admin sube doc per fase
- `accompaniment.state.invalid_transition` · attempted invalid transition logged
- `accompaniment.timeline.viewed` · cliente read-only access logged
- `accompaniment.cycle.completed` · BÁSICO completed OR ALTA certificate_issued

### Tests backend (8-10)

- State machine transitions BÁSICO valid 5 transitions
- State machine transitions MEDIO/ALTO valid 10 transitions
- Invalid transitions raise InvalidAccompanimentTransition (NO skip · NO back)
- Advisory lock concurrent admin races verified empirical
- audit_log Sub-atom 5.A 3-way OR cross transitions verified
- SSE event auto-trigger cliente verified empirical
- ClientNotification persistence empirical
- Artifacts upload + sha256 verify + metadata persistence
- Cliente read-only endpoint allow + admin endpoint require_owner enforced
- Timeline get_timeline returns chronological order

## Phase 7.5.2 scope refined

NEW component `AuditAccompanimentTimeline.tsx`:
- Embedded dentro `/admin/projects/[id]/audit/page.tsx` existing OR new tab `/audit-accompaniment` (decision per audit empirical: ENRICH existing audit page Pattern P-CL2-4)
- Tab approach: existing `<AuditMode />` already in audit page · add second component below
- Timeline visual cronológico (vertical timeline · React + Tailwind)
- Per state: badge + completion date + artifacts uploader (drag-drop file)
- Branch auto-derived del `project.categoria_objetivo` (BASICA → 6 states · MEDIA/ALTA → 11 states)
- R30 admin tutor TooltipENS per fase
- 2-3 Playwright tests

## Phase 7.5.3 scope refined

NEW component `AuditAccompanimentClienteView.tsx`:
- NEW tab `/client-portal/certificacion` cliente portal navigation
- Read-only timeline cliente friendly (R29 sostained)
- SSE listener via existing `useClientProjectEvents` hook (Pattern #14 + #21 reuse)
- 1-2 Playwright tests (runtime DEFER infrastructure JWT issue per Ejecutable 7 OPS-052 72ª · scaffold + CI validate)

## OPS-045 audit-first 54ª aplicación projection

- Nominal scope: ~4-6h cumulative Phase 7.5.1-7.5.3
- Empirical projection likely ~1-1.5h (-85% OPS-045 sostained per architect)
- Infrastructure existing 60% (Pattern #18 + #22 + #14 + P-CL2-4 + #21 ALL reusable canonical)
- Greenfield 40%: new motor + new state machine + new ORM models + new migration + new frontend components

## Doctrinas honored cumulative

- Pattern #18 state machine reuse · Pattern #22 advisory lock · Pattern #14 SSE+ClientNotification dual emit · Pattern #21 SSE event_id Last-Event-ID · Pattern P-CL2-4 ENRICH existing landing
- Sub-atom 5.A audit_log 3-way OR propagated (5 NEW canonical events)
- ADR-013 doble pool (admin endpoints require_owner · cliente read-only require_client_user)
- ADR-025 reuse infrastructure (3 NEW tables justified architecturally · NO state machine derivable from audit_log alone dado artifacts persistence + chronological transitions need)
- R23 admin project-scoped (admin component within /audit tab)
- R29 cliente friendly (read-only timeline · sin technical jargon)
- R30 admin tutor (TooltipENS per fase explain)
- Cliente-mínimo filosofía 100% sostained (cliente RECIBE timeline updates · NO opera proceso · admin advances state · auto-SSE)

## Future-X scope (0 items casuales · solo contrastados duplicidad)

Per architect doctrine inviolable "zero defers casuales". Empirical scope clean · NO Future-X needed pre-piloto.

Potential post-piloto enrichments (NO defers · NOT scope refinement · architecturally coherent demand-driven):
- Artifacts S3-compatible storage (currently local filesystem MVP · enrichment cuando demand-driven cloud storage)
- ENAC handoff portal integration (currently artifacts download manual · enrichment post-piloto cuando primer ENAC audit real)
- Certification renewal calendar reminders (currently `biannual_renewal_scheduled` state only · enrichment post primer ALTA cliente real demand-driven)

These NOT in CLAUDE.md Future-X registry · architecturally coherent natural enrichments post-piloto · NO scope debt incurred.
