# AUDIT CLUSTER 6 PHASE 6A · MFA TOTP cliente · Empirical State (Sesión 3B-2B.8)

**Fecha**: 2026-05-27
**Branch**: `radar-v9`
**Status**: ✅ Audit-first MANDATORY done · proceed Phase 6A.1 refined

---

## Empirical findings (60-70% infrastructure existing)

### Backend libraries
- ✅ `pyotp>=2.9` already in `backend/pyproject.toml`
- ✅ `backend/app/auth/totp_svc.py` (admin TOTP service) canonical reusable:
  - `generate_secret()` → base32 random
  - `verify_code(secret, code)` → 6-digit with +/- 1 step drift window
  - `provisioning_uri(secret, account_name)` → otpauth:// URI for QR
- ❌ `qrcode` / `Pillow` NOT in dependencies (use otpauth:// URI + frontend renders SVG inline · no extra deps)

### Backend models
- ✅ `auth_totp_secrets` table exists (admin · `auth_users` FK)
- ❌ NO `client_user_totp_secrets` table (cliente OFF per SAN-E v3.MB-1.1 historical)
- ❌ NO `client_user_backup_codes` table

### Backend services
- ✅ `auth_service.login()` (m21_portal_cliente) extant · password verify + lockout
- ✅ `_log_audit` + `_log_audit_chain` helpers · 3-way OR pattern via `AuditLogService`
- ✅ EmailSender canonical `backend/app/core/email/sender.py` · `send(db, to=, subject=, html_body=, ...)`
- ✅ `ClientUserAudit` model (legacy + hash chain MB-14.2)

### Frontend
- ✅ `/client-portal/settings/notifications/page.tsx` extant (Phase 5E shipped)
- ✅ `/client-portal/account/notifications/page.tsx` extant
- ❌ NO `/client-portal/settings/mfa/page.tsx` (NEW Phase 6A)
- ❌ NO QR rendering library frontend (use inline SVG QR renderer · ~80 LOC pure JS no deps)

---

## Phase 6A.1 implementation refined

### Delta scope (NEW)
1. Migration `cluster6_client_mfa_001`:
   - `client_user_totp_secrets` table (client_user_id FK · secret · verified bool)
   - `client_user_backup_codes` table (client_user_id FK · code_hash · used_at nullable)
   - `client_users` ADD column `mfa_enabled boolean DEFAULT false`
2. Service `backend/app/motors/m21_portal_cliente/mfa_service.py` NEW:
   - `initiate(db, user)` → secret + otpauth_uri (NOT verified yet)
   - `confirm(db, user, code)` → verify first code · generate 10 backup codes single-use
   - `verify_login(db, user, code)` → TOTP or backup code · returns success bool
   - `disable(db, user, code)` → require current TOTP + audit log
3. API `backend/app/motors/m21_portal_cliente/mfa_api.py` NEW endpoints:
   - `POST /client-portal/settings/mfa/initiate` (require_client_user) → {secret, otpauth_uri}
   - `POST /client-portal/settings/mfa/confirm` (require_client_user) → {backup_codes}
   - `POST /client-portal/settings/mfa/disable` (require_client_user)
   - `GET /client-portal/settings/mfa/status` (require_client_user)
4. Login flow `auth_service.login()` modification:
   - If `user.mfa_enabled = true` + no `mfa_code` provided → raise `MfaRequiredError` (HTTP 401 special)
   - If `mfa_code` provided → verify via `mfa_service.verify_login`
5. Email template inline HTML `_render_mfa_enrolled_email` → cliente confirmation + backup codes reminder
6. Frontend `/client-portal/settings/mfa/page.tsx` NEW:
   - "Activar verificación 2 pasos" stepper (initiate → QR + secret → confirm code → backup codes display + download)
   - Disable flow (require code)
7. Frontend login update: si 401 + `requires_mfa: true` → mostrar input TOTP step 2
8. audit_log emit: `mfa.initiated` · `mfa.confirmed` · `mfa.verified` · `mfa.failed` · `mfa.backup_code_used` · `mfa.disabled`
9. Tests:
   - Backend (~8): initiate + confirm + login MFA required + login MFA verify + backup code + disable + lockout MFA fails + RLS isolation
   - Frontend (TBD inline)

### Reuse OPS-026 DRY
- Backend totp_svc admin (`generate_secret`, `verify_code`, `provisioning_uri`) → REUSED via direct import
- EmailSender canonical → REUSED
- audit_log helpers (_log_audit + _log_audit_chain) → REUSED Sub-atom 5.A 3-way OR

### Architectural decisions
- **NO new QR backend dependency** · provide otpauth:// URI · frontend SVG render minimal
- **Backup codes** · 10 single-use · displayed ONCE post-confirm · PDF download deferred Future-X
- **Lockout MFA** · 5 fails consecutive → 15min cooldown (mirror admin pattern)
- **Login 2-step** · password OK + mfa_enabled → 401 with `requires_mfa:true` body marker · cliente UI prompts TOTP step

---

## ETA refined

**Briefing nominal**: ~3-5h
**Empirical refined**: ~2-2.5h (-40% to -50% · OPS-045 57ª manifestation)

Reasons:
- pyotp + totp_svc admin DRY reuse (-1h)
- EmailSender canonical existing (-30 min)
- audit_log helpers existing (-30 min)
- QR via frontend SVG inline (no library install · -15 min)
- ADR-013 doble pool pattern existing (no new auth scaffold)

---

## OPS-052 manifestation 43ª

Briefing Phase 6A correctly anticipated MFA infrastructure delta. Audit revealed admin TOTP `auth/totp_svc.py` reusable canonical · saving full scaffolding effort. Refined scope reflects 60-70% pre-existing.
