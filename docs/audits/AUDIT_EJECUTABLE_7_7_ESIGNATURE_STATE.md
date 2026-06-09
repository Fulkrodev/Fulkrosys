# AUDIT EJECUTABLE 7.7 · E-signature TIER 1 Canvas + Ed25519 + audit_log

**Fecha**: 2026-05-27
**Sesión**: 3B-4 Ejecutable 7.7
**Tipo**: Phase 0 Empirical State Verification MANDATORY (OPS-052 Phase 0)
**Outcome**: STOP HARD scope refined REFACTOR+EXTEND m05_signing motor

---

## Empirical findings cumulative

### Motor m05_signing EXISTING production-grade (audit-first reveal 80%+ infrastructure)

- **Status**: production-grade · SAN-E v3.MB-5.2 · ADR-020 IMPLEMENTED FULLY · 1,840 LOC · 9 files
- **Tablas DB existentes** (motor-specific ORM):
  - `signing_intents` · 1 row per intent firma cliente (project_id + signable_type + document_hash + status state machine)
  - `signing_events` · INMUTABLE log con Ed25519 signature_ed25519 (LargeBinary) + hash chain (event_hash_sha256 + previous_signature_hash)
  - `signing_otp_codes` · ephemeral OTP storage step-up (TTL 5 min · 5 attempts max)
- **Cryptography**: process-level Ed25519 keypair (var/keys/) reusable
- **Hash chain**: SHA256(message + previous_hash + signature) per project · `verify_chain_integrity` admin endpoint detect tampering
- **Signable types catalog**: 11 types canónicos (`dda` · `magerit_validation` · `pentest_authorization` · `conformidad_ens` · `acta_comite` · `retainer_offer` · `retainer_quarterly_signoff` · `policy_approval` · `incident_close` · `dpc_anual` · `renewal` · `document_generic`)
- **REQUIRES_STEP_UP_OTP frozenset**: 6 types criticos (dda · pentest · conformidad · dpc_anual · renewal · retainer_quarterly_signoff)
- **API endpoints existentes**:
  - Cliente `/api/v1/portal/signing/intents` POST create
  - Cliente `/api/v1/portal/signing/intents/{id}/request-otp` POST
  - Cliente `/api/v1/portal/signing/intents/{id}/verify-otp` POST
  - Cliente `/api/v1/portal/signing/intents/{id}/sign` POST
  - Cliente `/api/v1/portal/signing/intents/{id}/reject` POST
  - Cliente `/api/v1/portal/signing/intents/{id}` GET detail
  - Cliente `/api/v1/portal/signing/projects/{id}/history` GET firmas hub
  - Admin `/api/v1/admin/signing/projects/{id}/chain-integrity` GET
- **Frontend existing**: `/client-portal/firmas-hub/page.tsx` (signature cards visualization) + `/client-portal/firma/page.tsx` (página explicativa eIDAS · ADR-009 + ADR-010)
- **Router wiring**: `backend/app/main.py` líneas 124-126 + 696-700

### Audit findings vs request user

| Deliverable user | Existing infrastructure m05_signing | Delta NEW required |
|------------------|-----------------------------------|-------------------|
| Ed25519 system signature | ✅ EXISTS (`keypair.py` + `sign()` method) | reuse zero new |
| Hash chain audit_log | ✅ EXISTS (`signing_events` + `verify_chain_integrity`) | reuse zero new |
| audit_log canonical events (Sub-atom 5.A 3-way OR) | ❌ existing usa `signing_events` motor-specific NO `audit_log` central | EMIT también audit_log central per Sub-atom 5.A |
| Canvas dibujo manual frontend | ❌ NOT exists | NEW SignatureCanvas + react-signature-canvas |
| Captura nombre + apellido | ❌ NOT exists | NEW fields persistencia |
| Storage signature image | ❌ NOT exists | NEW DB column base64 (S3 Future-X FASE J) |
| NO MFA re-prompt | ❌ Existing OTP step-up cliente | NEW TIER 1 path bypass OTP cuando canvas data provided |
| PDF embed última page signature | ❌ NOT exists | NEW PDF generators extend bloque "Firma del cliente" |
| Admin trigger request | ❌ Existing intent creation es cliente-initiated solo | NEW admin endpoint trigger intent |
| Accompaniment state machine integration | ❌ NOT wired m05_signing ↔ m_audit_accompaniment | NEW link per states que requieran firma |
| /client-portal/firmas-pendientes page | ❌ Existing es `/firmas-hub` (history overview) | NEW page focus pending action |
| Frontend cliente SSE auto-update | ❌ NOT wired signing → SSE | NEW SSE dispatch on signature events |

### react-signature-canvas dependency

- **Status**: NOT installed empirical (verified `frontend/package.json` no match)
- **Action**: `npm install react-signature-canvas` Phase 7.7.2

### Multi-head alembic state

- **Current heads** (6 cumulative): `08bf3e16ef34` · `1350b2466202` · `1b32bac44237` · `2ddffdcdddfc` · `7ebd575c4f66` · `8e02b4ed6004`
- **Strategy**: NEW migration depends on `2ddffdcdddfc` (latest fase8 mainline)
- **NO new heads creation**: Add ALTER TABLE solo NO CREATE TABLE (extend signing_events columns)

### Accompaniment state machine integration requirements

- **m_audit_accompaniment** Ejecutable 7.5 shipped · 2 branches:
  - BÁSICO 6 states (declaration_drafted → declaration_signed) · 1 signature gate
  - MEDIO/ALTO 11 states (multiple signature gates: docs_collected requires DdA + MAGERIT signatures · internal_audit_completed requires conformidad signature)
- **Mapping signable_type → required-at-state**:
  - `dda` required pre `STATE_BASICO_DECLARATION_SIGNED` + `STATE_MA_DOCS_COLLECTED`
  - `magerit_validation` required pre `STATE_MA_DOCS_COLLECTED`
  - `policy_approval` required pre `STATE_MA_INTERNAL_AUDIT_SCHEDULED`
  - `pentest_authorization` required pre `STATE_MA_ENAC_AUDIT_SCHEDULED` (MEDIO/ALTO)
  - `conformidad_ens` required pre `STATE_MA_ENAC_AUDIT_PASSED` + `STATE_BASICO_DECLARATION_PUBLISHED`
  - `dpc_anual` required pre `STATE_BASICO_PERIODIC_REVIEW_SCHEDULED`

### Pattern reuse cumulative

- **Pattern #14** SSE + ClientNotification dual emit (signature.signed → cliente realtime)
- **Pattern #18** state machine canonical (corrective_loop + accompaniment + signing existing)
- **Pattern #21** event_id + replay buffer (SSE signature events compatible)
- **Pattern #22** advisory lock per resource (lock per `document_id` to serialize concurrent admin requests)
- **Pattern #23** state machine canonical per-branch (Ejecutable 7.5 reuse)
- **Sub-atom 5.A** audit_log 3-way OR (project_id + client_id propagated)

---

## Scope refined REFACTOR+EXTEND (OPS-052 manifestación 75ª)

**Decisión**: NO crear motor m24_esignature paralelo. EXTEND m05_signing motor existing.

**Justificación**:
- ADR-053 Cloud-First Architecture cohesión cross-motores honored
- OPS-026 DRY firmísimo
- m05_signing es hub criptográfico canonical (5 motors upstream consume)
- m24_idms ya existing (NO collision posible)
- Existing 80%+ infrastructure dispensable reusable
- Cliente-mínimo filosofía + R29 + R30 ya aplicada existing flows

**Delta minimal change**:
1. ALTER TABLE `signing_events` ADD COLUMNS:
   - `signature_canvas_dataurl` TEXT NULL (base64 PNG · S3 Future-X FASE J)
   - `signed_name` VARCHAR(120) NULL
   - `signed_surname` VARCHAR(120) NULL
2. NEW endpoint `/api/v1/portal/signing/intents/{intent_id}/sign-canvas` (TIER 1 bypass OTP)
3. NEW endpoint `/api/v1/admin/signing/intents/request` (admin trigger intent + accompaniment state link)
4. NEW endpoint `/api/v1/portal/signing/projects/{id}/pending` (cliente list pending action)
5. SSE dispatch on `signing.signed` event channel project:{id}
6. audit_log canonical 5 events Sub-atom 5.A 3-way OR (signature.requested · signature.signed · signature.declined · signature.verified · signature.expired)
7. NEW `frontend/components/signatures/SignatureCanvas.tsx`
8. NEW `frontend/app/(client-portal)/client-portal/firmas-pendientes/page.tsx`
9. NEW backend helper `pdf_signature_embed.py` última page bloque "Firma del cliente"
10. Wire accompaniment state machine: block advance hasta required signatures done
11. npm install react-signature-canvas

**Future-X DEFER explicit (NO casual · contrastados duplicidad)**:
- TIER 2 eIDAS qualified signature (Marcos scope-out · ADR-009 inviolable per /firma page existing · NO eIDAS preventivo) → `Future-1.F+.tier-2-eidas-qualified-external-provider` (~15-25h post-piloto demand-driven solo si cliente real lo demande contractualmente)
- S3 storage migration signature canvas dataurl → `Future-1.F.signature-canvas-s3-migration` (~2-3h post Hetzner deploy · base64 DB column funciona empirically pre-piloto)

---

## STOP HARD verification

- Briefing assumption: NEW motor m24_esignature greenfield clean separation
- Empirical reveal: 80%+ infrastructure m05_signing existing production-grade
- **Mismatch >70%** · STOP HARD triggered
- **Scope refined**: REFACTOR+EXTEND m05_signing (NOT NEW motor)
- **ETA impact**: ~30-45 min projection maintained (scope refined preserves time budget)
- **Architectural integrity**: ADR-053 cohesion + OPS-026 DRY sostained

---

**Audit complete** · proceeding Phase 7.7.1 backend extension m05_signing.
