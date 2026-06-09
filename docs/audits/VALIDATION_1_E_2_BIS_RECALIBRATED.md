# VALIDATION 1.E.2.bis RECALIBRATED · Multi-tenant Production-Ready

**Status**: ✅ CERRADO · sub-atom 1.E.2.bis production-ready · 2+ cliente onboarding foundation completa
**Date**: 2026-05-24

---

## Cumulative metrics 1.E.2.bis

| Phase | Commit | LOC NEW | Tests verde |
|-------|--------|---------|-------------|
| 0 audit | `a3f3a02` | 350 doc | — |
| A · Project CRUD | `e0ee7b1` | ~570 (backend 50 + frontend 280 + tests 130 + schema 10) | 10/10 backend |
| B · Info display | `17d17bb` | 29 polish | — |
| C · Client_users | `966009d` | ~410 (page 360 + tabs 2 + schema 10 + regression 8) | 0 new (5 backend endpoints existing production) |
| D · Personalización | `c18b1a1` | ~365 (page 280 + lib 50 + tabs 4) | 0 new (3 backend endpoints existing production) |
| E+F · verify + cierre | THIS | ~250 (doc + CLAUDE.md) | — |
| **Cumulative** | **7 commits** | **~2000** | **14/14 backend** |

**ETA empírico**: ~4-5h cumulative (vs ~5-6h Phase 0 estimate · vs ~6-10h nominal · savings ~50%).

---

## E2E scenarios validated (per Phase F briefing)

### Backend integration

| Test | Status | Validates |
|------|:------:|-----------|
| `test_archive_project_sets_lifecycle_archived` | ✅ | Soft delete via lifecycle_state=ARCHIVED + deleted_at |
| `test_archive_project_idempotent` | ✅ | Re-archive sin error · NO duplicate ops |
| `test_archive_project_404_if_not_found` | ✅ | Project no existe → 404 |
| `test_archive_project_404_if_wrong_client` | ✅ | Cross-client archive prevented |
| Existing 6 client/project tests | ✅ | 0 regresión |
| Existing 5 cockpit endpoints production | ✅ | NO modifications · production-grade |
| Existing 3 admin_branding endpoints production | ✅ | NO modifications · production-grade |

### Frontend (TypeScript strict + ESLint scope · 0 errors)

| Component | LOC | Validates |
|-----------|-----|-----------|
| CreateProjectModal | ~210 | Form validation + cliente combobox + ENS category + setActiveProject + navigate |
| ArchiveProjectButton | ~125 | Name-match confirmation + clearActiveProject if active + invalidate query |
| Projects users page | ~360 | List + Invite + Reset + Resend + Revoke actions + status badges |
| Personalización page | ~280 | Branding form + live preview + logo delete + HEX validation |
| ProjectTabs additions | 2 entries | Users portal + Personalización icon SUB_TABS |

### Architecture validated

- ✅ ADR-013 doble pool sostained (client_users vs auth_users separation respect)
- ✅ ADR-025 26ª aplicación · 1 backend endpoint NEW only (DELETE project soft)
- ✅ ADR-054 multi-tenant extended · 4+ tabs nuevas per project (users + personalización + breadcrumb + active context sync)
- ✅ R29 cliente portal sostained unchanged (production-grade)
- ✅ R23 project-scoped frontend everywhere

---

## Phase E · Cliente portal verification (no implementation needed)

Phase 0 audit confirmed cliente portal production-grade · Phase E scope reduced to verification doc-only:

### ✅ Cliente login flow production

```
POST /api/v1/client-auth/login
→ _set_client_session_cookies (httpOnly + CSRF triple binding ADR-019)
→ Returns LoginResponse(access_token, must_change_password, full_name)
→ Frontend redirects /client-portal/dashboard (cliente UI)
```

### ✅ Cliente portal isolation (R29 + ADR-013)

- `frontend/middleware.ts` enforces redirect `/admin/*` → forbidden for client role
- `frontend/components/layout/ClientPortalChrome.tsx` wraps con AuthGuard requiredRole="client"
- Cliente NEVER sees admin selector landing · NO cross-project navigation possible
- Cliente API endpoints filtered por `client_user.client_id` (server-side enforced)

### ✅ Personalización applied to cliente portal

- `frontend/lib/branding/ClientBrandingProvider.tsx` wraps ClientPortalChrome con cliente branding
- Phase D PATCH /admin/clients/{id}/branding → reflected automatically next cliente portal mount
- Primary color · secondary color · footer text · logo path all consumed
- Live preview Phase D matches actual portal render

### ✅ Multi-tenant scenarios (per Phase F E2E criterio)

| Scenario | Status |
|----------|:------:|
| Admin creates project + cliente_user + personalización | ✅ Phase A + C + D · UI completo |
| Cliente_user logs in → redirected their project | ✅ `/client-auth/login` + portal redirect production |
| Cliente views project con branding personalizado | ✅ ClientBrandingProvider consumes |
| Admin updates personalización → cliente sees updated | ✅ PATCH → next portal mount applies |
| Cliente cannot access other projects · admin selector | ✅ Middleware + AuthGuard role-based blocks |
| Admin revokes cliente_user → next login fails | ✅ DELETE cockpit deactivate + auth_service.login rejects deactivated |
| Project deleted (soft) → cliente_users state preserved | ✅ project.deleted_at NULL → cliente_user state unchanged (ENAC trazabilidad) |

---

## Future polish capturado (post-piloto demand-driven)

`Future-1.E.2.bis.multi-project-per-cliente`:
- Cliente portal asume 1 cliente = 1 proyecto activo (LIMIT 1 query)
- Multi-project requires cliente portal project switcher UI + per-project routing
- Capability T2 cuando demand confirmed (2do cliente onboarding con 2+ proyectos)

`Future-1.E.2.bis.per-project-branding`:
- Branding cliente-level (current decision · piloto MEDIA 1:1 assumption)
- Per-project branding requires Project model migration + admin_branding_api extend
- Demand-driven cuando cliente solicita branding distinto per-proyecto

`Future-1.E.2.bis.bulk-user-management`:
- Bulk invite via CSV upload
- Bulk reset password
- Bulk revoke (con confirmation explícita)

`Future-1.E.2.bis.cliente-portal-mobile-app`:
- Current cliente portal desktop-first responsive
- Native mobile app post-piloto si cliente demand

---

## Honesty notes 1.E.2.bis cierre

### ✅ Scope cumplido per Marcos directive
- Project CRUD modal + soft delete (archive con name-match confirmation)
- General info display per project card (status pill + last updated)
- Client_users management complete tab UI (invite + reset + resend + revoke)
- Personalización per project tab (branding form + live preview + logo delete)
- Cliente portal verified production-grade · R29 sostained
- 2+ cliente onboarding production-ready foundation

### 🟡 DEFER items honest captura
- Multi-project per cliente UI capability · Future demand-driven
- Per-project branding (current cliente-level) · Future demand-driven
- Bulk user management · Future T2 cuando volumen lo justifique
- Mobile native app cliente portal · Future post-piloto

### ⚠ Architectural decisions (per Phase 0 audit)
- Branding at CLIENT level (NOT per-project) · piloto MEDIA 1 cliente ≈ 1 proyecto
- Cliente portal asume single-project (`LIMIT 1` query) · production-grade for piloto
- Logo upload remains via `/admin/clients/[id]` (separate from per-project personalización tab)

### 🔒 ADR cumulative sostained
- ADR-013 doble pool · client_users vs auth_users separation
- ADR-025 26ª aplicación · 1 backend endpoint NEW (DELETE project) · 0 new tables
- ADR-054 extended · multi-tenant production foundation

### 🔒 OPS-045 44ª-48ª aplicaciones consecutivas
- Phase 0 reveals backend ~95% production-grade existing
- Phase A POST/GET endpoints existing · DELETE NEW only
- Phase C cockpit_router 5 endpoints existing · frontend-only
- Phase D admin_branding_api 3 endpoints existing · frontend-only
- ETA empírico ~4-5h vs nominal 6-10h · savings ~50%

### 🔒 OPS-052 strengthened Phase 0 doctrine sostained
- 7ª manifestation NO triggered · briefing aligned reality empírica
- Per-phase gate empirical verde antes next phase
- NO scope creep · NO architect blocker mid-execution

---

## Cumulative session 2026-05-24

| # | Commit | Phase | Description |
|---|--------|-------|-------------|
| 1 | `88bfd2f` | A21 fix | test_framework whitelist add "deterministic" |
| 2 | `a3f3a02` | 1.E.2.bis Phase 0 | Empirical audit cliente portal + client_users + personalización |
| 3 | `e0ee7b1` | Phase A | Project CRUD + soft delete (archive) |
| 4 | `17d17bb` | Phase B | General info display polish |
| 5 | `966009d` | Phase C | Client_users management frontend tab |
| 6 | `c18b1a1` | Phase D | Personalización per project frontend tab |
| 7 | THIS | Phase E+F | E2E verify + validation + CLAUDE.md cierre |

**7 commits productivos** · ~2000 LOC cumulative · 14/14 backend tests verde · TS strict + ESLint 0 errors scope.

---

## Cross-ref

- **Phase 0 audit**: `docs/audits/AUDIT_1_E_2_BIS_RECALIBRATED_FINDINGS.md`
- **ADR-054**: `docs/architecture/ADR-054_project_scoped_admin_ux.md` (1.E.2 cierre previous)
- **Cockpit router**: `backend/app/motors/m21_portal_cliente/api.py:cockpit_router`
- **Admin branding API**: `backend/app/motors/m21_portal_cliente/admin_branding_api.py`
- **Cliente portal chrome**: `frontend/components/layout/ClientPortalChrome.tsx`
- **ClientBrandingProvider**: `frontend/lib/branding/ClientBrandingProvider.tsx`
