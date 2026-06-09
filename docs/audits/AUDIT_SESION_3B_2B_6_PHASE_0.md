# Sesión 3B-2B.6 · Phase 0 Empirical Foundation Audit · 8 dimensions

**Status**: 🟡 STOP-AND-REPORT · architect approve Path A/B/C antes Phase 1+ execute
**Doctrine**: OPS-052 Phase 0 mandatory · empirical filesystem verification + psql ground-truth ANTES propagate implementation chain
**Date**: 2026-05-26
**Scope**: Marcos directive · NEW Sesión 3B-2B.6 · Auditor ENAC Entregable (ZIP-default) + Optional Portal (magic-link gated) + Audit-Passed State Machine + Retainer Trigger
**Method**: 4 parallel Explore agents (DIM 1+2 · 3+4 · 5+6 · 7+8) + cross-check con file paths + grep empirical

---

## TL;DR · honesty bottom-line

| Dimension | Foundation reusable | Critical gaps | Bloqueante piloto MEDIA cierre |
|-----------|---------------------|---------------|--------------------------------|
| **DIM 1 · Auditor-handoff admin page** | ~75% (MagicLinkGenerator + History reused 100%) | NO portal entry point · NO auditor_sessions · NO session cookie post-consume | SÍ (gap NEW build) |
| **DIM 2 · M12 magic_links** | ~95% crypto layer + table schema | No session creation post-consume (token-bounded read-only stateless OK · or new sessions table) | NO (foundation crypto sólida) |
| **DIM 3 · Dossier ZIP** | ~70% (M09 audit_prep · DOSSIER_STRUCTURE 15 folders · endpoints generate+download exist · DossierPreview frontend) | 🔴 **MANIFEST.json NO firmado Ed25519** · NO cover letter PDF signed · evidence validity index missing | SÍ (entregable ENAC incompleto) |
| **DIM 4 · Conformity state machine** | ~60% (M27 RouteState 16 states · transitions enum present · M05 E-041 signature OK) | 🔴 NO admin endpoint "mark audit-passed" · NO project.lifecycle_state advance automation · LUCIA federation dormant | SÍ (cierre piloto bloqueado) |
| **DIM 5 · M14+M23 retainer trigger** | ~85% (state machines + M25 lifecycle accept_retainer_offer existing) | NO automatic trigger post-audit_passed → retainer offer (manual admin action) · email notifications post-cert manual | NO (manual OK pre-piloto) |
| **DIM 6 · Portal reference architecture** | ~95% (`/(portal)/pentester-portal/[token]/` pattern reusable 1:1) | None blocking · pattern proven existing 2 portals (pentester + remediation + verify-auth) | NO |
| **DIM 7 · Audit log infrastructure** | ~100% (audit_log table + 3 PL/pgSQL triggers + fn_audit_log_verify_chain) | NO auditor-specific events emitted yet (no call sites for auditor_view_dossier · auditor_download · auditor_sign_approval) | NO (additive) |
| **DIM 8 · Integration map** | ~90% cumulative cross-dim | NO new tables needed · 1 column migration (project.audit_passed_at) + 1 index | n/a |

**Honesty empírico**: foundation Sesión 3B-2B.6 es **~85% reusable cumulative cross-8-dims**. Critical 4 gaps bloqueantes piloto MEDIA cierre ciclo:
1. Dossier MANIFEST NO firmado Ed25519 (~2-3h M05 wire-in)
2. NO admin endpoint mark-audit-passed (~3-4h endpoint + service)
3. NO auditor portal entry (`/auditor/[token]/*` route group missing) (Path B only · ~10-15h)
4. NO retainer trigger automation post-audit_passed (~2-3h workflow hook)

---

## DIM 1 · Auditor-handoff admin page

**Files empirical**:
- `frontend/app/(admin)/admin/projects/[id]/auditor-handoff/page.tsx` (136 LOC · Sesión 3B-2B.3 Phase X.4e)
- `frontend/components/magic-links/MagicLinkGenerator.tsx` (382 LOC · reused FASE 4.5)
- `frontend/components/magic-links/MagicLinkHistoryTable.tsx` (230 LOC)
- `frontend/hooks/magic-link/index.ts` (~100 LOC · tanstack-query mutations)
- `frontend/lib/api/magic-links.ts` (62 LOC)
- `frontend/lib/magic-link-types.ts` (269 LOC · 35 purposes enum sync'd backend)
- `frontend/tests/polish/p2/05_admin_project_auditor_handoff.spec.ts` (verified GREEN Sesión 3B-2B.2)

**Functional current state**: project-scoped admin UI · Marcos genera magic-links manuales para 3 auditor purposes existing:
1. `respuesta_requerimiento_auditor` (TTL 48h · 1 use · OTP)
2. `descarga_dossier_final` (TTL 7d · 3 uses · OTP)
3. `revisar_informe_verificacion` (TTL 15d · 5 uses · OTP)

UI flow: Marcos → form → POST `/api/v1/magic-links/generate` → response shows plaintext token + OTP (once · never stored plaintext) + expiry. Tab "Histórico" lists active links con revoke action.

**Reusable** (~75%): generator + history components 100% reusable · backend endpoints 100% reusable · M30 ContactQuickPicker integration ready.

**Critical gaps**:
- ❌ No session creation post-consume (token-bounded request only · no cookie HttpOnly)
- ❌ No portal entry point (`/ml/consume?token=X` page exists para clients · NO for auditors)
- ❌ No auditor_sessions table (analogous to client_sessions)
- ❌ No RLS gate `/auditor/[project_id]/*` (Path B prereq)

---

## DIM 2 · M12 magic_links architecture

**Files empirical**:
- `backend/app/models/operations.py` · `MagicLink` ORM
- `backend/app/motors/m12_magic_link/` (service · API · purposes catalog)
- `backend/app/motors/m12_magic_link/purposes.py` · `MagicLinkPurpose` enum **36 values** (3 auditor + 32 automatic + 1 OFERTA_RETAINER)

**Schema** (`magic_links` table):
```
id UUID PK · project_id UUID FK · tipo_operacion VARCHAR(50) · scope JSONB
token_hash VARCHAR(64) · otp_hash VARCHAR(64) · expira_at TIMESTAMPTZ
max_usos INT default 1 · usos INT default 0 · revocado BOOL · revoked_at
otp_failures INT · recipient_email · allowed_countries JSONB
sent_to_contact_id UUID FK client_contacts.id · cc_emails TEXT[]
custom_subject · custom_body_intro · FullMixin audit columns
```

**Token generation flow** (verified):
1. POST `/api/v1/magic-links/generate` + `MagicLinkGenerateRequest`
2. `MagicLinkPolicyEnforcer` validates ADR-042 deprecation
3. JWT payload `{jti, sub=project_id, purpose, scope, iat, exp}` signed `pyjwt.encode(payload, FULKRO_ML_PRIVATE_KEY, algorithm="EdDSA")`
4. `token_hash = SHA-256(full_jwt_token)` persisted
5. OTP via `pyotp.TOTP(random_base32()).now()` · `otp_hash = SHA-256(otp_plaintext)` persisted
6. Audit log append to `client_interactions` (action='generated')
7. Response plaintext token + OTP **once** (never logged)

**Consume flow**: JWT signature verify → token_hash lookup → not revoked/expired/uses-remaining/OTP-OK → increment `usos` + audit log. **No session cookie set currently.**

**Reusable** (~95% as crypto layer): policy enforcer + JWT signing + audit chain 100% reused · `consume_magic_link()` returns purpose+scope+remaining_uses (Path A/B can use stateless verify per-request OR add session cookie layer).

**Critical gaps**:
- No auditor_sessions model (Path B might OR might not need · Path A pure ZIP doesn't)
- 36 purposes already includes `OFERTA_RETAINER` ✓ (retainer trigger ready) + `PORTAL_PENTESTER_EXTERNO` ✓ (template for `PORTAL_AUDITOR_EXTERNO` new enum)

---

## DIM 3 · M09 Dossier ZIP candidate state

**Files empirical**:
- `backend/app/motors/m09_audit_prep/dossier_generator.py` (DOSSIER_STRUCTURE constant lines 39-54)
- `backend/app/motors/m09_audit_prep/api.py` (lines 85-146 endpoints)
- `frontend/components/project/DossierPreview.tsx` (46 LOC)
- `frontend/app/(admin)/admin/projects/[id]/dossier/page.tsx` (Phase 1.3 enriched con CopilotGuidedFlow)

**Reality correction CLAUDE.md "10 docs canonical"**: refers to legacy `Future-1.E.1.dossier-pack-10docs` Path Hybrid DEFERRED T1. **Empirical actual**: 15 folders ENAC structure:

```
00_INDICE · 01_GOBIERNO · 02_CATEGORIZACION · 03_ANALISIS_RIESGOS
04_DECLARACION_APLICABILIDAD · 05_PLAN_ADECUACION · 06_NORMATIVA
07_PROCEDIMIENTOS · 08_REGISTROS_OPERACION · 09_EVIDENCIAS_POR_MEDIDA
10_PLAN_CONTINUIDAD · 11_FORMACION · 12_PROVEEDORES · 13_INFORMES_TECNICOS
99_MATRIZ_CRUZADA
```

**Endpoints existentes**:
- `POST /api/v1/audit-prep/projects/{pid}/runs/{rid}/generate-dossier?force=[bool]` → in-memory ZIP build · checklist validation · `force=false` blocks pending items · `force=true` adds `BORRADOR_pendientes.md`
- `GET /api/v1/audit-prep/projects/{pid}/runs/{rid}/dossier` → stream `application/zip` con `Content-Disposition: attachment; filename="dossier_auditoria_{run_id}.zip"`

**ZIP contents per file**: índices Markdown + PDF maestro (pandoc) + JSON docs · JSON evidence (organized `09_EVIDENCIAS_POR_MEDIDA/{measure_code}/{tipo}_{hash}.json`) · JSON registros (groupby mes) · JSON declaraciones M27 · XLSX matriz 99 + **MANIFEST.json** con SHA256 hashes.

**🔴 CRITICAL gap**: MANIFEST.json **NO firmado Ed25519** currently. Structure has metadata + file hashes pero NO signature field. Auditor ENAC requires verificación integridad · M05 signing service available pero **NOT wired** to M09.

**Other gaps**:
- ❌ Cover letter / executive summary PDF firmado (current resumen_ejecutivo.md no PDF · no firma)
- ❌ Evidence validity index (no `fecha_caducidad > now()` validator report)
- ❌ Per-medida coverage JSON summary (only XLSX matrix exists)

**Reusable** (~70%): 15-folder structure complete · ZIP build robust · sólo falta firma + cover letter + validity index.

---

## DIM 4 · Conformity wizard E-041 state machine

**Files empirical**:
- `backend/app/motors/m27_conformity/route_machine.py` (RouteState enum 16 states · 12 transitions)
- `backend/app/motors/m27_conformity/api.py` line 253 (transición parcial UNDER_REVIEW→CONFORMANT)
- `backend/app/motors/m27_conformity/audit_schedule_service.py` (updates last_audit_completed SIN state transition)
- `backend/app/motors/m27_conformity/api_paso5.py` line 87-90 (RecategorizeBody schema sin transition logic)
- `backend/app/motors/m25_lifecycle/lifecycle_paso4.py` (`mark_certified_on()` · `accept_retainer_offer()` · `retainer_offered` event)
- `backend/app/motors/m05_signing/` (Ed25519 E-041 signature flow complete)
- `frontend/components/conformity/ConformityWizard.tsx` (12 steps adaptativo per categoría)

**RouteState enum**:
```
ROUTE_PENDING → ROUTE_LOCKED → DECLARATION_IN_PROGRESS | CERTIFICATION_IN_PROGRESS
→ READY_FOR_DECLARATION | READY_FOR_AUDITOR → UNDER_REVIEW | SUSPENDED
→ OBSERVED | CORRECTION_REQUIRED | CONFORMANT → REGISTERED → ACTIVE
→ RENEWAL_DUE → RENEWAL_PENDING → ACTIVE | EXPIRED
```

**Project.lifecycle_state** column (`backend/app/models/core.py:77`):
```
DRAFT · NEGOTIATING · SIGNED · ACTIVE · CERTIFIED · RETAINER
ENDED_RENEWAL_OK · ENDED_CHURN · ARCHIVED · PURGED
```

**Transitions YA EXISTEN**:
- ✅ ROUTE_PENDING → ROUTE_LOCKED (lock_route endpoint)
- ✅ Route type dispatch DECLARATION vs CERTIFICATION
- ✅ UNDER_REVIEW → CONFORMANT transición code path
- ✅ CONFORMANT → REGISTERED → ACTIVE
- ✅ RENEWAL_DUE → RENEWAL_PENDING (renewal_scheduler.py)
- ✅ M05 E-041 firma Ed25519 cliente

**🔴 CRITICAL gaps**:
- ❌ NO admin endpoint `POST /admin/projects/{id}/conformity/audit-result` que ejecute UNDER_REVIEW → CONFORMANT transition + lifecycle_state CERTIFIED advance
- ❌ NO automatic distintivo SVG generation trigger (distintivo_generator.py exists pero invoked manually)
- ❌ LUCIA federation auto-publication CCN dormant (`lucy_federation.py` exists NOT wired)
- ❌ Material change detection → extraordinary audit trigger MaterialChangeRow flag exists sin callback

**Reusable** (~60%): state machine enum + route lifecycle + M05 signing OK · falta admin endpoint + automation triggers.

---

## DIM 5 · M14 + M23 retainer trigger wiring

**Files empirical**:
- `backend/app/motors/m14_contracts/contract_service.py` (7 states · C-001..C-005 templates incl. C-003 retainer)
- `backend/app/motors/m14_contracts/workflow_hooks.py:86-150` (`maybe_dispatch_adenda_on_step_completed()` PROVEEDOR/PROVIDER/LCSP automatic)
- `backend/app/motors/m23_retainer/retainer_service.py:16-73` (5 profiles · 7 renewal clock states)
- `backend/app/motors/m25_lifecycle/lifecycle_paso4.py` (`mark_certified_on()` · `accept_retainer_offer()`)
- `frontend/app/(admin)/admin/projects/[id]/retainer/page.tsx`
- `frontend/app/(client-portal)/client-portal/retainer-checkin/page.tsx` (quarterly comité CCN-STIC 805)

**M14 contracts states**: `draft → firmado_marcos → sent → firmado_cliente → vigente → vencido/rescindido` (deterministic state management · NOT event-driven directly · automatic ADENDA dispatch via workflow_hooks).

**M23 retainer profiles**: R_MICRO / R_LITE / R_STD / R_PLUS / R_CRITICAL (SLA hours + cadences monthly→annually). Renewal clock 7 states T_MINUS_180 → T_MINUS_0 → LAPSED/RENEWED.

**Project lifecycle**: `mark_certified_on()` sets `project.lifecycle_state = "CERTIFIED"` · `accept_retainer_offer()` transitions to `RETAINER` (manual user action via magic link `OFERTA_RETAINER`).

**Cliente portal retainer-checkin**: empty state si NO active retainer · CheckinCard + CheckinDetail layout · `useRetainerCheckin()` tanstack-query · ClientDigestCard mensual digest R29-friendly.

**Reusable** (~85%): M14 + M23 service layer + M25 lifecycle hooks complete · cliente UI offer view ready · M12 OFERTA_RETAINER purpose existing.

**Critical gap**:
- ❌ NO automatic trigger `audit_passed → retainer_offer` (current flow manual admin action calls `offer_retainer()`). Per R23 strict project-scoped + Marcos design choice · puede quedar manual pre-piloto · automation Phase 4 (~2-3h workflow hook).

---

## DIM 6 · Auditor portal reference architecture

**Files empirical**:
- `frontend/app/(radar)/layout.tsx` (top-level route group · capability `ens_radar_owner` · ADR-015)
- `frontend/app/(admin)/admin/compliance/page.tsx` (NOT top-level · consolidated 4 portal cards landing)
- `frontend/app/(portal)/pentester-portal/[token]/page.tsx` (13 LOC wrapper)
- `frontend/components/pentester-portal/PentesterPortal.tsx` (150+ LOC · token-validated · public API no auth · autosave localStorage · read-only constraint component-level)
- `frontend/app/(portal)/layout.tsx` ("Portal seguro · Enlace firmado Ed25519 · acceso restringido · no indexado" · robots noindex)
- `frontend/app/(portal)/remediation/[token]/*` (mismo pattern)
- `frontend/app/(portal)/verify-auth/[token]/*` (mismo pattern)

**Token-bounded portal pattern verified existing** (3 instances · pattern firmísimo). 100% reusable for auditor portal.

**Recommended auditor portal architecture**:
```
frontend/app/(portal)/auditor-portal/[token]/
├── page.tsx (wrapper · token validate + redirect dashboard)
├── layout.tsx (constrained chrome · audit-specific header)
├── dashboard/page.tsx (project summary + status)
├── dossier/page.tsx (14-folder navegable)
├── dossier/[folder]/page.tsx (folder contents + evidence)
├── magerit/page.tsx (read-only analysis)
├── pentest/page.tsx (E-702/E-703 findings)
├── evidence-vault/page.tsx (search by measure_code)
├── audit-log/page.tsx (immutable log + verify hash chain)
├── e-041/page.tsx (declaration view)
└── approval/page.tsx (final signature submission)
```

**Magic-link purpose new**: `PORTAL_AUDITOR_EXTERNO` (TTL 72h · max_uses 5-10 · requires_otp true).

**API endpoint pattern**: `/api/v1/auditor/{token}/*` · backend validates token + extracts project_id + auditor_email per-request · stateless (no session table needed Path B OR add `auditor_sessions` if multi-tab UX needed).

**Read-only enforcement**: API endpoints return 403 si endpoint not in auditor allowlist · component-level `<ReadOnlyGuard>` HOC disables form submits.

**Per-project per-cliente único R23**: token bound to single project_id · API filters `WHERE project_id = {token.project_id} AND project.client_id = {get_token_client_id(token)}`.

**Reusable** (~95%): pentester-portal pattern is template-exact · 200-300 LOC nuevo route wrapper + read-only HOC + magic-link purpose enum.

---

## DIM 7 · Audit log auditor actions

**Files empirical**:
- `backend/app/models/audit_log.py` (table schema)
- `backend/migrations/versions/1350b2466202_*.py` (initial schema con audit_log)
- `backend/migrations/versions/d4f8b2a90001_*.py` (hash chain triggers + seq BIGSERIAL)
- 3 PL/pgSQL functions: `fn_audit_log_hash_chain()` (BEFORE INSERT) · `fn_audit_log_immutable()` (BEFORE UPDATE/DELETE raises EXCEPTION) · `fn_audit_track()` (AFTER on 13 tracked tables)
- `fn_audit_log_verify_chain()` integrity verification

**Schema**:
```
audit_log: id UUID PK · tabla VARCHAR(100) · registro_id UUID · accion VARCHAR(20)
usuario VARCHAR(255) · timestamp TIMESTAMPTZ · payload_old JSONB · payload_new JSONB
hash_prev VARCHAR(64) · hash_current VARCHAR(64) · seq BIGSERIAL UNIQUE
```

**Tracked tables (13)**: evidence · documents · document_versions · contracts · invoices · projects · clients · categorizations · dda_entries · obligations · magerit_analysis · audit_findings · pentest_findings.

**Hash chain integrity** (R6 ENS inviolable verified empirical):
- `hash_current = SHA-256(prev_hash || tabla || registro_id || accion || usuario || timestamp || payload_old || payload_new)`
- `pg_advisory_xact_lock(hashtext(...))` evita race conditions
- BIGSERIAL seq deterministic ordering
- UPDATE/DELETE raises ERRCODE `insufficient_privilege` (immutable enforce)

**Actor types**: `usuario` VARCHAR captures admin email (Marcos) OR service session_user · NO role distinguishable directly · auditor sería new actor (no DB user · accessed via magic link).

**Gap auditor-specific events** (audit_log accion enum needs extend):
- ❌ `auditor_view_dossier`
- ❌ `auditor_download_zip`
- ❌ `auditor_view_evidence_medida`
- ❌ `auditor_view_magerit`
- ❌ `auditor_view_pentest`
- ❌ `auditor_sign_cert_approval` (state transition trigger)
- ❌ `auditor_request_clarification`
- ❌ `auditor_annotation`

**Recommendation**: Extend audit_log con nullable `auditor_id` (FK magic_link.id) + `auditor_email` (sent_to email). Unified hash chain + simpler verification. NO new sub-table.

**Reusable** (~100%): trigger infrastructure complete · solo emit new accion values from new endpoints.

---

## DIM 8 · Integration map foundation → new build

### Frontend routes new (Path B)
```
frontend/app/(portal)/auditor-portal/[token]/    ← NEW route group
├── layout.tsx (~80 LOC AuditorLayout)
├── page.tsx (~40 LOC token redirect)
├── dashboard/page.tsx (~120 LOC)
├── dossier/page.tsx (~150 LOC)
├── dossier/[folder]/page.tsx (~180 LOC)
├── magerit/page.tsx (~100 LOC)
├── evidence-vault/page.tsx (~200 LOC)
├── audit-log/page.tsx (~150 LOC)
├── e-041/page.tsx (~80 LOC)
└── approval/page.tsx (~180 LOC)
Total ~1280 LOC new frontend
```

### Backend endpoints new
```
POST /api/v1/admin/projects/{id}/dossier/zip-signed   ← Path A · sign manifest Ed25519
POST /api/v1/admin/projects/{id}/auditor-portal/grant ← Path B · create magic link + email
POST /api/v1/admin/projects/{id}/audit/mark-passed    ← Path A · state transition
GET  /api/v1/auditor/{token}/project                  ← Path B · token validate + project meta
GET  /api/v1/auditor/{token}/dossier                  ← Path B · 14-folder listing
GET  /api/v1/auditor/{token}/dossier/{folder}/files   ← Path B · folder contents
GET  /api/v1/auditor/{token}/evidence/{measure_code}  ← Path B · per-medida evidence
GET  /api/v1/auditor/{token}/magerit                  ← Path B · read-only snapshot
GET  /api/v1/auditor/{token}/audit-log                ← Path B · immutable trail
POST /api/v1/auditor/{token}/sign-approval            ← Path B · auditor signature + state trigger
POST /api/v1/auditor/{token}/download-zip             ← Path A+B · stream ZIP signed
Total ~700-900 LOC new backend (router + service)
```

### Database migrations new
**Path A**:
- Migration `audit_passed_metadata_001`: ADD COLUMN `projects.audit_passed_at TIMESTAMPTZ NULL` + `audit_passed_by VARCHAR(255) NULL` + index `audit_log(usuario, accion)` for auditor event filtering

**Path B (additional)**:
- Migration `auditor_portal_purpose_001`: NO schema change · solo adds `PORTAL_AUDITOR_EXTERNO` to enum config purposes.py (Python enum) · backward-compat

**NO new tables needed** (CRITICAL OPS-026 firmísimo · leverage magic_links + audit_log + archived_backups existing infrastructure 100%).

### Components new
- `<ReadOnlyGuard>` HOC (~60 LOC) frontend
- `<AuditorLayout>` (~120 LOC)
- `<DossierViewer>` (~250 LOC)
- `<EvidenceVaultSearch>` (~180 LOC)
- `<AuditLogViewer>` (~150 LOC)
- `<AuditorApprovalForm>` (~200 LOC)
- Hooks `useAuditorToken()` + `useAuditorSession()` (~150 LOC)

---

## 3 paths Marcos approve

### 🟢 Path A · Minimalista (~10-15h)

**Scope**: ZIP-default entregable completo · Marcos genera + email auditor · NO portal.

**Phase 1 · Dossier ZIP signed manifest** (~4-6h)
- Wire M05 signing service → M09 dossier_generator MANIFEST.json (add `signature_ed25519` + `public_key_pem`)
- Generate cover letter PDF signed (current resumen_ejecutivo.md → PDF + firma)
- Evidence validity index helper (`fecha_caducidad > now()` → JSON summary)
- Per-medida coverage JSON sidecar (alongside XLSX matrix 99)

**Phase 2 · Auditor handoff UI enhanced** (~2-3h)
- /admin/projects/[id]/auditor-handoff page expand
- "Generate ZIP signed" button → POST `/api/v1/admin/projects/{id}/dossier/zip-signed` → download + email link
- Email integration M18 con magic-link `descarga_dossier_final` purpose existing

**Phase 3 · Audit-passed admin button + state transitions** (~2-3h)
- `/admin/projects/[id]/audit` page extended con "Marcar auditoría pasada" button
- POST `/api/v1/admin/projects/{id}/audit/mark-passed` endpoint
- Payload: `{result, audit_report_ref, auditor_entity, auditor_signature_hash, marked_by}`
- Trigger UNDER_REVIEW → CONFORMANT route state advance
- Trigger `projects.lifecycle_state` DRAFT → CERTIFIED
- Audit log emit `audit_admin_mark_passed`
- Distintivo SVG generation automatic (M27 distintivo_generator wire)

**Phase 4 · Retainer trigger wiring** (~2-3h)
- Workflow hook on `audit_passed` event → call `lifecycle_paso4.offer_retainer()`
- Generate magic-link `OFERTA_RETAINER` purpose (existing)
- Email cliente con offer
- Cliente portal /retainer-checkin already shows offer (R29 friendly)

**Deliverable**: cliente piloto MEDIA cierra ciclo end-to-end · auditor recibe ZIP firmado + valida offline + Marcos admin marks passed + retainer offer ya cliente.

**Risk**: auditor que prefiera interactivo no tiene path (workaround: Marcos screenshot exports manual).

**Total ETA Path A**: **~10-15h** (4 phases · 6-10 commits)

---

### 🔵 Path B · Recomendado (~30-45h)

**Scope**: Path A complete + auditor portal optional access magic-link gated.

**Path A · ~10-15h** (Phase 1-4 complete)

**Phase 5 · Auditor portal magic-link gated entry** (~6-10h)
- Add `PORTAL_AUDITOR_EXTERNO` purpose to M12 purposes.py + config
- NEW frontend route `/auditor/[token]/*` (mirror pentester-portal pattern)
- AuditorLayout component (neutral chrome · "Portal seguro" header · robots noindex)
- Token validation middleware backend
- POST `/api/v1/admin/projects/{id}/auditor-portal/grant` admin endpoint
- Trigger from /admin/projects/[id]/auditor-handoff page "Generate portal access + send magic link"

**Phase 6 · Read-only constrained views** (~8-12h)
- Dashboard auditor (project summary + status timeline)
- DossierViewer (14-folder navegable · evidence preview per medida)
- MageritReader (read-only analysis snapshot)
- EvidenceVaultSearch (search by measure code)
- E-041 viewer (declaration + cliente signature visible)
- PentestFindingsViewer (M08 reports E-702/E-703)
- AuditLogViewer (immutable trail + verify hash chain button)
- AuditorApprovalForm (Ed25519 signature submission · trigger state transition)
- ReadOnlyGuard HOC + component-level disabled-submit guards

**Phase 7 · Audit log auditor events emission** (~2-3h)
- Extend audit_log emit per route hit:
  - `auditor_view_dossier` · `auditor_download_zip` · `auditor_view_evidence_medida`
  - `auditor_view_magerit` · `auditor_view_pentest` · `auditor_view_audit_log`
  - `auditor_sign_cert_approval` (state transition trigger)
- Add `auditor_email` denormalization to audit_log rows (FK magic_link.sent_to_email)
- fn_audit_log_verify_chain() works unchanged (hash chain unified)

**Phase 8 · WCAG axe-CI + tests** (~4-5h)
- 8-10 Playwright specs cliente portal pattern reused para auditor portal
- E2E flow test: admin grant → email → auditor opens link → consumes OTP → views dossier → downloads ZIP → signs approval → state transition fires
- Integration test audit_log chain verify post-auditor-events
- Backend unit tests endpoints

**Deliverable**: ZIP-default 80% + portal-optional 20% + state machine + retainer trigger crítico business model post-cert · cliente piloto MEDIA cierra ciclo end-to-end ROBUSTO.

**Risk**: scope mayor pero E2E completo · cubre auditor preferencias variables.

**Total ETA Path B**: **~30-45h** (~12-20 commits · ~4-6 sesiones dev)

---

### ⚪ Path C · Aspiracional (~50-70h)

**Scope**: Path B complete + auditor interactive features.

**Path B · ~30-45h** (Phase 1-8 complete)

**Phase 9 · Auditor annotations** (~6-8h)
- NEW table `auditor_annotations` (finding_id · comment_text · annotated_at · annotated_by_email)
- POST/GET endpoints per finding
- Frontend inline comment threads

**Phase 10 · Request more evidence query interface** (~4-6h)
- POST `/api/v1/auditor/{token}/request-clarification` ticket-style
- Notifies admin via M18 communication
- Cliente portal optional notification

**Phase 11 · DdA stated vs evidence actual comparison view** (~5-8h)
- GET `/api/v1/auditor/{token}/compliance/coverage` heatmap JSON
- Auto-detect coverage gaps per medida
- ComparisonHeatmap frontend canvas/D3

**Phase 12 · Auditor draft report generation** (~5-8h)
- Agent (M11 auditor virtual) reads annotations + findings + coverage
- Returns markdown draft ENAC format
- Frontend viewer + export DOCX
- Admin reviews + delivers cliente

**Risk**: scope creep · valor incremental incierto pre-piloto · auditor real feedback necesario antes invertir.

**Recommendation**: DEFER Path C aspirational features Future-X **post-piloto real auditor feedback**. NO bloqueante piloto cierre.

**Total ETA Path C**: **~50-70h** (12-15 cumulative commits adicional)

---

## Recommended architect approve · Path B Recomendado

### Rationale firmísimo

1. **ZIP-default cubre 80% casos auditor reales** (auditor recibe + valida offline · NO requiere portal interactivo) → Path A core deliverable
2. **Portal-optional cubre auditor que PREFIERE interactivo** (20% casos · auditor moderno + sees value en navegabilidad + audit log trazable + sign approval directo)
3. **State machine audit_passed → retainer_offer crítico business model post-cert** · sin él piloto MEDIA NO cierra ciclo end-to-end (retainer R_STD 700-1500€/mes recurrente vs proyecto fijo 11.500€)
4. **Foundation ~85% reusable** · marginal new build · OPS-045 audit-first sostained
5. **Path B unifica entregable empresarial robusto** · ZIP-default + portal-optional + state machine + retainer · 4 deliverables crítricos pre-piloto MEDIA

### Risks Path B vs A

| Risk | Path A | Path B | Mitigation |
|------|--------|--------|------------|
| Auditor real prefiere interactivo | NO portal · workaround Marcos manual | Portal disponible | Path B preferido |
| Scope creep | bajo | medio (30-45h) | OPS-052 Phase 0 cierre + atomic commits per phase |
| Pre-existing RLS gaps interfieren | bajo | medio (auditor session needs careful RLS) | Sesión 5 sub-atoms 5.A+5.B antes auditor portal deploy |
| ETA optimismo | bajo | medio | Foundation ~85% reusable + pentester-portal pattern template-exact |
| Cliente piloto retraso | bajo si retainer manual | medio si automation complejo | Phase 4 keep simple workflow hook · no estado machine compleja |

### Cumplimiento doctrinario

✅ OPS-026 DRY firmísimo (NO new tables · reuse magic_links + audit_log + archived_backups)
✅ OPS-045 audit-first reveals existing infrastructure (50ª aplicación · ~85% reusable verified empirical)
✅ OPS-049 honesty path (Path C explicit deferred post-piloto · NOT silencioso Future-X)
✅ OPS-052 Phase 0 mandatory (este audit) · architect approve antes Phase 1+ execute
✅ ADR-013 doble pool · auditor portal en `/(portal)/*` separate from admin/client
✅ ADR-025 reuse infrastructure firmísimo (29ª aplicación cumulative)
✅ R23 strict project-scoped · auditor portal per-project per-cliente único
✅ R29 cliente friendly (NA · auditor portal NOT cliente-facing pero similar neutral chrome pattern)
✅ R6 audit log inmutable hash chain preserved (auditor events emit unchanged)

---

## STOP-AND-REPORT closure

🟡 **Phase 0 audit COMPLETE empirical · architect approve Path A/B/C antes Phase 1+ execute**

**Recommended Path B** (~30-45h · 12-20 commits · 4-6 sesiones dev).

**Pre-requisites verified**:
- Foundation cumulative ~85% reusable cross-8-dims
- ZIP build + magic links + audit log + portal pattern infrastructure listos
- 4 critical gaps identified concretos · ETA estimates honest

**Optional Sesión 5 sequencing consideration**: si Path B selected, recomendable ejecutar Sesión 5 sub-atom 5.A (audit_log RLS) ANTES Path B Phase 7 (audit log auditor events emission) para defence-in-depth completo durante portal deploy. Sub-atom 5.B (magerit_assets RLS) compatible paralelo.

**Architect decision pending**:
- [ ] Path A · Minimalista (~10-15h ZIP-default only)
- [ ] Path B · Recomendado (~30-45h ZIP + portal optional + state machine + retainer) ⭐
- [ ] Path C · Aspiracional (~50-70h Path B + annotations + query + comparison + draft report)
