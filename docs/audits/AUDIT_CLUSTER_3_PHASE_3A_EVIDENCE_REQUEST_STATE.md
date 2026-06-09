# AUDIT CLUSTER 3 Phase 3A · Evidence Request System Empirical State

**Sesión**: 3B-2B.8 CLUSTER 3 Phase 3A
**Fecha**: 2026-05-26
**Ejecutor**: Phase 3A.0 OPS-052 micro-audit mandatory
**Status**: ✅ **Audit complete · scope refined backend MVP workflow state machine · NO STOP HARD**

---

## Resumen ejecutivo

Briefing Phase 3A asumió necesidad de full Evidence request system con admin/cliente UI completos · workflow states (pending_cliente · pending_review · approved · rejected) · plantillas · mark-no-aplicable · trazabilidad audit_log. Empirical reality:

- ✅ **Evidence model existe** (`backend/app/models/documents.py:96`) · persists files · NO workflow request lifecycle
- ✅ **M07 Evidence vault API** (`m07_evidence/api.py`) · upload + list + expiring + renew + verify endpoints (admin)
- ✅ **Cliente upload endpoint** (`m21_portal_cliente/evidencias_upload_api.py`) · multipart upload portal · audit_log hash chain · NO request linkage
- ✅ **DdA Evidence Gap admin endpoint** (`m09/dda_evidence_gap_api.py:155-219`) · admin `request-more-evidence` triggers ClientNotification(type='evidence_request') · ONE-SHOT (NO state tracking)
- ✅ **EvidenceRenewalRequest model** exists pero scope renewal flow ONLY (NOT initial admin→cliente request)
- ✅ **emit_client_notification + SSE wire Phase 2D** ready (DRY central function · auto SSE + audit_log Sub-atom 5.A)
- ❌ **NO `evidence_request` table** con workflow state machine
- ❌ **NO admin Outbox UI** · NO cliente Inbox UI tasks list pending_cliente
- ❌ **NO linkage Evidence uploaded ↔ original request** (state transition pending_cliente → pending_review)
- ❌ **NO admin approve/reject endpoint** sobre request lifecycle
- ❌ **NO `mark_no_aplicable` cliente endpoint**

**Gap identified**: empirical infra notification one-shot existing (ClientNotification spam-free pattern admin → cliente · single message) · NO workflow lifecycle backend tracking. Phase 3A adds canonical workflow state machine + linkage Evidence ↔ request.

**Filosofía cliente-mínimo guard CRITICAL**:
- Cliente SUBE evidence cuando Marcos pide · NO opera Evidence vault directamente
- Cliente MARK-NA si no aplica con motivo (NO técnico ENS)
- Marcos VALIDA / RECHAZA con motivo claro
- Cliente NO ve admin orchestration internals · solo "Marcos pide X documento · deadline Y"

ETA refined: ~3-5h backend MVP vs briefing 5-8h (-30% to -40% OPS-045 57ª manifestation · audit-first reveals: Evidence vault + ClientNotification + SSE wire Phase 2D already wired · solo workflow state machine + endpoints).

Cliente UI deferred CLUSTER 6 chronological navigation backbone (pattern Phase 2F · architecturally coherent).

---

## Phase 3A.0.1 · Existing infrastructure empirical map

### Evidence vault (M07)
- `m07_evidence/api.py` admin CRUD evidence files
- `m07_evidence/ingestion_service.py` upload pipeline + ClamAV scan
- `m07_evidence/signing.py` Ed25519 signing
- `m07_evidence/types.py` evidence types catalog

### Evidence model (documents.py:96)
- Fields: project_id + measure_id + control_id + tipo + fuente + fichero_path + hash_sha256 + fecha_evidencia + fecha_caducidad + vigente + scan_status
- Motor 7 extensions: evidence_type_id + measure_code + obligation_id + scan_*
- NO workflow request linkage column

### Existing one-shot notification (m09/dda_evidence_gap_api)
- admin `POST /admin/projects/{id}/audit/request-more-evidence` body{medida_codes, message_to_client}
- → emit_client_notification(type='evidence_request', title="Aportar evidencias adicionales · N medidas")
- → audit_log accion='admin.evidence_request.triggered'
- → NO state tracking · NO request workflow · cliente uploads via portal generic + NO linkage

### Cliente upload endpoint
- `POST /client-portal/evidencias/upload` multipart file + description + related_measure
- → Path storage var/evidences/client_uploads/{project_id}/{uuid}.{ext}
- → AuditLogService.log_action EVIDENCE_UPLOAD hash chain
- NO request_id linkage · cliente uploads contextless

---

## Phase 3A.0.2 · Workflow state machine design

### NEW Table `evidence_requests`

```sql
CREATE TABLE evidence_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    client_user_id UUID,                       -- nullable · puede ser broadcast
    measure_code VARCHAR(40),                  -- linked ENS medida code
    control_id UUID REFERENCES controls(id),   -- linked control
    tipo_documento VARCHAR(100),               -- catalog: 'política', 'log', 'screenshot', etc.
    titulo VARCHAR(255) NOT NULL,              -- admin-defined task title
    descripcion TEXT,                          -- admin context for cliente
    plantilla_url VARCHAR(500),                -- optional template link
    deadline_date DATE,                        -- cliente target submit by
    status VARCHAR(30) NOT NULL DEFAULT 'pending_cliente',
    -- States: pending_cliente · pending_review · approved · rejected · cancelled · marked_na
    created_by_user_id UUID NOT NULL,          -- admin who created request
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Resolution metadata
    cliente_uploaded_at TIMESTAMPTZ,           -- cuando cliente subió evidence
    evidence_id UUID REFERENCES evidence(id),  -- linked Evidence row uploaded
    cliente_na_motivo TEXT,                    -- cuando cliente marked_na
    admin_validated_at TIMESTAMPTZ,            -- admin approve/reject timestamp
    admin_validated_by_user_id UUID,
    admin_rejection_motivo TEXT,               -- cuando rejected con motivo claro

    CONSTRAINT ck_evidence_request_status
      CHECK (status IN ('pending_cliente', 'pending_review', 'approved',
                        'rejected', 'cancelled', 'marked_na'))
);

CREATE INDEX ix_evidence_requests_project_id ON evidence_requests(project_id);
CREATE INDEX ix_evidence_requests_status ON evidence_requests(status);
CREATE INDEX ix_evidence_requests_client_user_id ON evidence_requests(client_user_id)
  WHERE client_user_id IS NOT NULL;

-- RLS isolation per project (Sub-atom 5.A pattern)
ALTER TABLE evidence_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_requests FORCE ROW LEVEL SECURITY;
CREATE POLICY evidence_requests_isolation ON evidence_requests
    USING (project_id = current_project_id());
GRANT SELECT, INSERT, UPDATE, DELETE ON evidence_requests TO fulkro_app;
```

### State transitions canonical

```
pending_cliente ─cliente upload─→ pending_review ─admin approve─→ approved
                                                ↘ admin reject ────→ rejected
                ─cliente mark-na──────────────────────────────────→ marked_na
                ─admin cancel────────────────────────────────────────→ cancelled

rejected ─cliente re-upload─→ pending_review (re-cycle 1 vez · puede)
```

State guards:
- `pending_cliente` → `pending_review` (cliente upload OR admin sets)
- `pending_cliente` → `marked_na` (cliente clicks no aplicable + motivo)
- `pending_cliente` → `cancelled` (admin cancels)
- `pending_review` → `approved` (admin approve)
- `pending_review` → `rejected` (admin reject + motivo)
- `rejected` → `pending_review` (cliente re-upload)
- terminal: `approved`, `marked_na`, `cancelled`

---

## Phase 3A.0.3 · API endpoints proposed

### Admin endpoints (require_owner · ADR-013)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/admin/projects/{id}/evidence-requests` | POST | Create new request (admin defines tarea) |
| `/admin/projects/{id}/evidence-requests` | GET | List requests (filterable by status) |
| `/admin/projects/{id}/evidence-requests/{req_id}` | GET | Get request detail |
| `/admin/projects/{id}/evidence-requests/{req_id}/approve` | POST | Approve uploaded evidence |
| `/admin/projects/{id}/evidence-requests/{req_id}/reject` | POST | Reject with motivo |
| `/admin/projects/{id}/evidence-requests/{req_id}/cancel` | POST | Cancel pending request |

### Cliente endpoints (require_client_user · ADR-013 doble pool)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/client-portal/evidence-requests` | GET | List own pending tasks · R29 friendly |
| `/client-portal/evidence-requests/{req_id}` | GET | View task detail (no admin lingo) |
| `/client-portal/evidence-requests/{req_id}/upload` | POST | Upload file + auto-link Evidence |
| `/client-portal/evidence-requests/{req_id}/mark-na` | POST | Cliente marks no aplicable + motivo |

### Patterns reused

- **emit_client_notification + SSE wire Phase 2D**: admin creates request → cliente sees notif realtime
- **Cloud digest reuse Pattern #14**: SSE + ClientNotification dual emit
- **Sub-atom 5.A audit_log**: cross all state transitions (admin.evidence_req.created · cliente.evidence_req.uploaded · admin.evidence_req.approved · etc)
- **Pattern #15 DRY central fn**: emit_client_notification automatically dispatches SSE on creation

---

## Phase 3A.0.4 · audit_log accion canonical

- `admin.evidence_req.created` · admin creates new request
- `cliente.evidence_req.viewed` · cliente views own task
- `cliente.evidence_req.uploaded` · cliente uploads + auto-transition pending_review
- `cliente.evidence_req.markna` · cliente marks no aplicable
- `admin.evidence_req.approved` · admin approves submitted evidence
- `admin.evidence_req.rejected` · admin rejects with motivo
- `admin.evidence_req.cancelled` · admin cancels pending

All emit Sub-atom 5.A 3-way OR (project_id + client_id propagated).

---

## Phase 3A.0.5 · Recommended Phase 3A refined scope (~3-5h)

### Phase 3A.1 implementation backend MVP (~2.5-3.5h)

**Step 1 · Migration** (~25-30 min)
- alembic migration NEW `evidence_requests_001`
- 1 NEW table + indexes + RLS + GRANT
- Down revision = `cliente_continuidad_001` (Phase 2F head)

**Step 2 · Model** (~10-15 min)
- `backend/app/models/evidence_request.py` EvidenceRequest mapping
- Register in `models/__init__.py`

**Step 3 · Service** (~30-45 min)
- `backend/app/motors/m07_evidence/request_service.py`:
  - `create_request(...)`: admin creates · status=pending_cliente · emit ClientNotification
  - `list_requests(project_id, status_filter, client_user_id?)`: filterable
  - `get_request(request_id)`: by id (RLS enforced)
  - `cliente_upload(request_id, evidence_id)`: state transition pending_cliente → pending_review · validates current state
  - `cliente_mark_na(request_id, motivo)`: state transition → marked_na · validates current state
  - `admin_approve(request_id, user_id)`: state transition → approved · validates current state
  - `admin_reject(request_id, user_id, motivo)`: state transition → rejected · validates motivo provided
  - `admin_cancel(request_id, user_id)`: state transition → cancelled · validates current state

**Step 4 · Admin API + audit_log** (~30-40 min)
- `backend/app/motors/m07_evidence/request_admin_api.py` 6 endpoints
- audit_log emit per endpoint Sub-atom 5.A
- ClientNotification emit on create + on approve + on reject (cliente sees status updates)

**Step 5 · Cliente API + audit_log** (~30-40 min)
- `backend/app/motors/m07_evidence/request_cliente_api.py` 4 endpoints (list + detail + upload + mark-na)
- audit_log emit Sub-atom 5.A 3-way OR
- ADR-013 require_client_user
- R29 friendly responses (NO admin lingo)

**Step 6 · Router wiring** (~5-10 min)
- `backend/app/main.py` include both routers (admin + cliente)

### Phase 3A.2 tests (~45-60 min)

**Backend tests (10-12 tests)**:
- create_request happy-path admin + ClientNotification emit
- create_request validates project + client_user exists
- list_requests filters by status correctly
- cliente_upload state transition pending_cliente → pending_review + Evidence linkage
- cliente_upload rejects if current state NOT pending_cliente (idempotency)
- cliente_mark_na state transition with motivo
- admin_approve happy-path + audit_log entry
- admin_reject requires motivo (raises ValueError sin motivo)
- admin_cancel + transitions
- Re-upload after rejection cycles back to pending_review
- RLS cross-project no leak (Sub-atom 5.A enforcement)
- audit_log entries cumulative per state transition

### Phase 3A.3 UI defer (DEFERRED CLUSTER 6 backbone)

Cliente UI tasks list pending + upload modal + mark-na flow deferred to CLUSTER 6 chronological navigation backbone (architecturally coherent pattern Phase 2F). Backend MVP serves forward-compat per phase.

**Future-X explicit captured (OPS-049 honesty)**:
- `Future-CLUSTER6.evidence-request-cliente-page` (~4-6h · cliente tasks UI + upload modal + mark-na flow + status badges R29 friendly)
- `Future-CLUSTER6.evidence-request-admin-outbox-page` (~3-5h · admin outbox UI · filterable by status · approve/reject modal · cancel button)

---

## ETA refined Phase 3A

- **Briefing nominal**: ~5-8h
- **Empirical refined**: ~3-5h backend MVP (UI deferred CLUSTER 6)
- **OPS-045 57ª manifestation**: -30% to -40% vs nominal (audit-first reveals Evidence vault + ClientNotification + SSE wire already wired · only workflow state machine + endpoints needed)

---

## Filosofía cliente-mínimo compliance

100% aligned:
- Cliente VE pending tasks (NO opera Evidence vault directamente)
- Cliente SUBE archivo cuando Marcos pide
- Cliente MARK-NA con motivo amigable si no aplica
- Marcos VALIDA/RECHAZA con motivo claro
- Cliente RECIBE update vía ClientNotification SSE realtime (Phase 2D wire)
- audit_log trace lifecycle · ENAC trazabilidad cumulative
- R29 firmísimo · R30 inverso cliente NO ve admin orchestration

**ZERO admin operations leaked cliente** · 100% workflow lifecycle pattern.

---

## STOP HARD trigger evaluation

**NO STOP HARD necesario**. Briefing scope intent (Evidence request lifecycle cliente-mínimo) ratified · refined to backend MVP scope + UI deferred CLUSTER 6 (architecturally coherent Phase 2F pattern).

Briefing assumption "Phase 3A includes UI" scope-refined "Phase 3A backend MVP only · UI CLUSTER 6 backbone":
- Backend MVP ships canonical workflow · UI ties to navigation backbone
- Empirical infra wire (emit_client_notification SSE + audit_log Sub-atom 5.A) already done Phase 2D · DRY consume

---

## Patterns potencialmente formalizables Phase 3A

- **Workflow state machine + canonical transition validation** (request status transitions guards · admin/cliente actions allowed per state · prevents inconsistencies)
- **Request ↔ Evidence linkage pattern** (evidence_request.evidence_id FK to evidence table · cliente upload auto-links · admin approve cycles status)
- **Rejection motivo claro UX** (admin must provide rejection_motivo · cliente SEES motivo amigable · ENS trazabilidad)
- **Re-upload cycle pattern** (rejected → re-upload → pending_review · idempotent · audit trail per re-attempt)

---

## Decisión pendiente

⏸️ **Architect approve Phase 3A.1 refined scope**:
- Backend MVP only · 1 NEW table + 10 endpoints (6 admin + 4 cliente) + 10-12 tests
- Cliente UI DEFERRED CLUSTER 6 (Future-CLUSTER6.evidence-request-{cliente,admin}-page)
- ETA refined ~3-5h
- Filosofía cliente-mínimo 100% aligned (workflow lifecycle · cliente NO opera Evidence vault)
