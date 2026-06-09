# AUDIT CLUSTER 2 Phase 2F · M_drp + M_bia Cliente Questionnaire+Approve Empirical State

**Sesión**: 3B-2B.8 CLUSTER 2 Path B Phase 2F
**Fecha**: 2026-05-26
**Ejecutor**: Phase 2F.0 OPS-052 micro-audit mandatory
**Status**: ✅ **Audit complete · scope refined backend MVP cliente questionnaire+approve · NO STOP HARD**

---

## Resumen ejecutivo

Briefing Phase 2F asumió ALTA gaps DRP+BIA REFRAMED · cliente questionnaire input + Marcos draft + cliente approve binding decision. Empirical reality:

- ✅ **BIA admin infrastructure existing** · `m19_risk/bia_api.py` + `models/bia.py` BiaAnalysis schema (service_name + rto/rpo_hours + daily_impact_eur + stakeholders + minimum_resources)
- ✅ **BIA frontend admin** · `/admin/projects/[id]/bia/page.tsx` admin works
- ✅ **DRP document template existing** · `E403_drp_plan_recuperacion_desastres.py + .md` (m06 document factory · jinja2 docxtpl render)
- ❌ **NO DRP backend table/API** (only document template · NO state tracking)
- ❌ **NO cliente-facing BIA infrastructure** (NO `/client-portal/bia` page · NO cliente endpoints)
- ❌ **NO cliente-facing DRP infrastructure** (NO endpoints · NO models)
- ❌ **NO questionnaire input pattern** · admin currently creates BIA entries directly · cliente NO input mechanism

**Filosofía cliente-mínimo guard CRITICAL**:
- Cliente NUNCA creates BIA technical entries directly
- Cliente provides QUESTIONNAIRE input raw (RTO targets · downtime tolerance · procesos críticos)
- Marcos PREPARA BIA/DRP based on cliente input + Marcos expertise
- Cliente PREVIEW Marcos draft + APPROVE/COMMENT (binding decision · NO edit)

**Briefing target: ALTA projects**. Piloto target MEDIA. ALTA gaps real-piloto = post-piloto. BUT Phase 2F backend MVP + minimum cliente endpoints can ship for forward-compat ALTA scenarios (Marcos asks: "when ALTA project comes, infrastructure ready").

Scope refined: backend MVP only (~1.5-2h) · cliente UI deferred CLUSTER 6 navigation backbone (curated R29 friendly task list per phase). ETA -33% vs briefing 2-3h nominal (OPS-045 56ª manifestation · audit-first reveals: backend MVP scope sufficient · UI tied to navigation backbone CLUSTER 6).

---

## Phase 2F.0.1 · Empirical infrastructure map

### Existing BIA admin (m19_risk)

`backend/app/motors/m19_risk/bia_api.py`:
- POST `/projects/{id}/bia/analyses` (create BIA entry · require_owner)
- GET `/projects/{id}/bia/analyses` (list entries)
- GET `/projects/{id}/bia/summary` (aggregate)

`backend/app/models/bia.py` BiaAnalysis schema:
- project_id + service_name + rto_hours + rpo_hours
- daily_impact_eur + stakeholders + minimum_resources
- last_reviewed_at

**Note**: tabla bia_analyses es admin working table · NO touch desde cliente. Phase 2F cliente input lives en NEW separate table (clean separation).

### Existing DRP infrastructure (NO backend state)

`backend/app/motors/m06_document_factory/templates/deliverables/E403_drp_plan_recuperacion_desastres.{py,md}`:
- Document template solo (jinja2 + docxtpl render output)
- NO model · NO API · NO state tracking

### Cliente portal status

- NO `/client-portal/bia` page
- NO `/client-portal/drp` page
- NO `/client-portal/continuidad` page

---

## Phase 2F.0.2 · Cliente-mínimo questionnaire schema design

### Tabla NEW · `cliente_continuidad_input` (1 row per project · upsert)

```sql
CREATE TABLE cliente_continuidad_input (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    client_user_id UUID NOT NULL,
    submitted_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Questionnaire mínimo (cliente provides input · friendly fields)
    procesos_criticos JSONB,           -- array{nombre, descripcion}
    rto_horas_tolerancia INT,           -- horas tolerables sin servicio
    rpo_horas_tolerancia INT,           -- horas tolerables pérdida datos
    impacto_diario_eur NUMERIC(12,2),   -- pérdida diaria estimate
    activos_core JSONB,                 -- array{nombre, tipo}
    notas_cliente TEXT,                 -- comentarios libres
    completed BOOLEAN DEFAULT FALSE,

    -- RLS coherence
    UNIQUE(project_id)  -- 1 row per project (upsert pattern)
);

-- RLS isolation per project (Sub-atom 5.A pattern)
ALTER TABLE cliente_continuidad_input ENABLE ROW LEVEL SECURITY;
CREATE POLICY cliente_continuidad_input_isolation ON cliente_continuidad_input
    USING (project_id = current_project_id());
```

### Tabla NEW · `cliente_continuidad_approval` (audit trail)

```sql
CREATE TABLE cliente_continuidad_approval (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    client_user_id UUID NOT NULL,
    artifact_type VARCHAR(20) NOT NULL,  -- 'bia' | 'drp'
    draft_id UUID,                        -- reference admin's BiaAnalysis OR document
    action VARCHAR(20) NOT NULL,          -- 'approved' | 'rejected' | 'comment'
    comment_text TEXT,                    -- cliente feedback
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS isolation
ALTER TABLE cliente_continuidad_approval ENABLE ROW LEVEL SECURITY;
CREATE POLICY cliente_continuidad_approval_isolation ON cliente_continuidad_approval
    USING (project_id = current_project_id());
```

---

## Phase 2F.0.3 · Cliente endpoints proposed (filosofía cliente-mínimo)

| Endpoint | Method | Purpose | Filosofía |
|----------|--------|---------|-----------|
| `/client-portal/continuidad/questionnaire` | GET | Cliente sees own submission | RECIBE/VE · ✅ |
| `/client-portal/continuidad/questionnaire` | POST | Cliente submits questionnaire input (upsert) | INPUT raw · NO ENS técnico · ✅ |
| `/client-portal/continuidad/drafts` | GET | List Marcos drafts (BIA + DRP) ready for review | RECIBE/PREVIEW · ✅ |
| `/client-portal/continuidad/drafts/{id}/approve` | POST | Cliente approves binding decision | APROBA · ✅ |
| `/client-portal/continuidad/drafts/{id}/comment` | POST | Cliente requests changes (NO edit) | COMMENT · ✅ |

**Cliente NUNCA**:
- ❌ Create BIA analysis entry direct (admin only via existing m19_risk/bia_api)
- ❌ Edit BIA/DRP technical content (only approve/comment)
- ❌ Delete BIA entries
- ❌ Trigger document generation (admin only)

---

## Phase 2F.0.4 · audit_log emit Sub-atom 5.A 3-way OR

Accion canonical proposed:
- `cliente.continuidad.input` (cliente submits questionnaire · upsert)
- `cliente.continuidad.preview` (cliente views Marcos draft)
- `cliente.continuidad.approve` (cliente approves binding)
- `cliente.continuidad.comment` (cliente requests changes)

audit_log Sub-atom 5.A 3-way OR (project_id + client_id propagated · forward-compat ENAC trazabilidad).

---

## Phase 2F.0.5 · Recommended Phase 2F refined scope (~1.5-2h)

### Phase 2F.1 implementation backend MVP (~1-1.5h)

**Step 1 · Migration** (~15-20 min)
- alembic migration NEW `cliente_continuidad_input_001`
- 2 NEW tables · RLS policies · indices

**Step 2 · Models + Service** (~20-25 min)
- `backend/app/models/cliente_continuidad.py` 2 models
- `backend/app/motors/m19_risk/cliente_continuidad_service.py` service:
  - `upsert_input(db, project_id, client_user_id, payload) → ClienteContinuidadInput`
  - `get_input(db, project_id) → Optional[ClienteContinuidadInput]`
  - `list_drafts(db, project_id) → list[draft_meta]` (consume bia_analyses + document factory queries)
  - `record_approval(db, project_id, client_user_id, artifact_type, draft_id, action, comment)`

**Step 3 · Cliente API + audit_log** (~25-30 min)
- `backend/app/motors/m19_risk/cliente_continuidad_api.py` 5 endpoints (GET/POST questionnaire + GET drafts + POST approve + POST comment)
- audit_log emit Sub-atom 5.A 3-way OR each endpoint (raw SQL pattern reuse existing)
- ADR-013 doble pool · require_client_user · NO admin endpoints leaked

**Step 4 · Mount router + import wiring** (~5-10 min)
- `backend/app/main.py` include cliente_continuidad_api router
- Tags `["Portal Cliente - Continuidad"]`

### Phase 2F.2 tests (~30-45 min)

**Backend tests (5-6 tests)**:
- Test POST questionnaire upsert (create + update same row)
- Test GET questionnaire returns own data (no leak cross-project)
- Test GET drafts lists BIA entries + DRP document drafts existing
- Test POST approve creates approval record + audit_log entry
- Test POST comment creates approval record action='comment'
- Test ADR-013 admin pool denied (require_client_user enforced)

### Phase 2F.3 frontend UI scope-out (DEFERRED)

Cliente UI deferred to CLUSTER 6 navigation backbone (per-phase task curation · R29 friendly). Backend MVP Phase 2F serves forward-compat: cuando CLUSTER 6 implementa cliente navigation, endpoint backend ready.

**Future-X explicit captured (OPS-049 honesty)**:
- `Future-CLUSTER6.continuidad-cliente-page` (~3-5h · cliente UI questionnaire form + drafts preview · CLUSTER 6 backbone) · cluster 6 prerequisite

---

## ETA refined Phase 2F

- **Briefing nominal**: ~2-3h
- **Empirical refined**: ~1.5-2h backend MVP (deferred UI scope-out · architecturally coherent CLUSTER 6 backbone)
- **OPS-045 56ª manifestation**: -33% vs nominal (audit-first reveals BIA admin infra ready + DRP template ready · only cliente input/approval tables + 5 endpoints needed · UI deferred CLUSTER 6)

---

## Filosofía cliente-mínimo compliance

Phase 2F cliente endpoints cliente-mínimo 100% aligned:
- Cliente input QUESTIONNAIRE raw (RTO/RPO target preference · NOT technical BIA entry)
- Cliente RECIBE drafts Marcos preparados (admin owns content)
- Cliente APPROVE/COMMENT binding decision (NO edit · NO creator mode)
- audit_log trace approvals · ENAC trazabilidad
- R29 friendly Spanish · NO admin lingo · NO ENS sin TooltipENS
- R30 inverso · cliente NO ve admin BIA technical entries · solo drafts review

**ZERO admin operations leaked cliente** · 100% questionnaire+approve pattern.

---

## STOP HARD trigger evaluation

**NO STOP HARD necesario**. Briefing intent (ALTA gaps DRP+BIA cliente questionnaire+approve filosofía cliente-mínimo) ratified · refined to backend MVP scope + cliente UI deferred CLUSTER 6 (architecturally coherent).

**Briefing assumption "Phase 2F includes UI"** scope-refined "Phase 2F backend MVP only · UI CLUSTER 6":
- Backend MVP serves forward-compat ALTA scenarios + CLUSTER 6 backbone
- Cliente UI per-phase curation belongs to CLUSTER 6 chronological navigation
- Piloto target MEDIA (NOT ALTA) → ALTA UI demand-driven post-piloto
- Pattern OPS-045 audit-first reveals scope can be CLEAN backend-only Phase 2F

---

## Patterns potencialmente formalizables Phase 2F

- **Cliente questionnaire+approve pattern** (cliente INPUT raw + admin DRAFT + cliente APPROVE/COMMENT · NO creator mode · audit_log Sub-atom 5.A trace cliente binding decisions)
- **Upsert single-row per project** (cliente_continuidad_input UNIQUE(project_id) · cliente updates own questionnaire iteratively)
- **Architecturally coherent UI defer** (backend MVP ships + UI ties to navigation backbone CLUSTER 6 · NOT scope creep · NOT half-implementation OPS-049 honesty)

---

## Decisión pendiente

⏸️ **Architect approve Phase 2F.1 refined scope**:
- Backend MVP only · 2 NEW tables + 5 endpoints + 5-6 tests
- Cliente UI DEFERRED to CLUSTER 6 (Future-CLUSTER6.continuidad-cliente-page)
- ETA refined ~1.5-2h
- Filosofía cliente-mínimo 100% aligned (questionnaire+approve · NO creator mode)
