# AUDIT 1.E.2.bis RECALIBRATED · Empirical State Verification

**Status**: ✅ Phase 0 verification completa · gate verde · auto-arranque Phase A
**Date**: 2026-05-24
**Methodology**: OPS-052 strengthened Phase 0 doctrine · find/cat/ls/wc/head/tail (NO grep tool · 1 grep CLI exception for line numbers)

---

## Verdict empírico

**SCOPE DRASTICALLY REDUCED per Phase 0 findings**: backend client_users management + personalización ~95% production-grade existing. Phase C+D scope frontend-only mostly. NO new backend migrations. NO new motors.

**ETA recalibrated**: **~5-6h cumulative** (vs 6-10h nominal · savings ~40%) · NO 7ª OPS-052 manifestation triggered.

| Phase | Briefing nominal | Reality empírica | Scope adjust |
|-------|-------------------|-------------------|--------------|
| A · Project CRUD | 1-1.5h | ~30-45 min | Backend POST existing · frontend modal + delete UI |
| B · Info display | 45-60 min | ~30 min minor polish | Backend GET production · enhance dashboard hero |
| C · Client_users | 1.5-2.5h | ~1-1.5h frontend-only | Backend cockpit_router 5 endpoints existing |
| D · Personalización | 2-3h | ~1-1.5h frontend-only | Backend admin_branding_api 3 endpoints existing |
| E · Cliente portal | 30-60 min | ~30 min verify | Cliente portal 28+ pages production existing |
| F · E2E + close | 30 min | ~30 min | Validation doc + CLAUDE.md cierre |
| **Total** | **6-10h** | **~5-6h** | **Savings ~40%** |

---

## Step 1 · Client_users model + auth pool

### File: `backend/app/models/client_portal.py`

```python
class ClientUser(FullMixin, Base):
    __tablename__ = "client_users"
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"),
        nullable=False, index=True,
    )
    email + password_hash + full_name + dni
    must_change_password + last_login + locked_until
    failed_attempts + created_by_marcos + deactivated_at
    # SAN-E MB-8 WhatsApp opt-in 5 fields
    whatsapp_number + whatsapp_verified_at + whatsapp_opt_in_at + ...
    # SAN-E MB-9.bis cookie consent 7 fields (AEPD 2020)
    consent_functional + consent_analytics + consent_marketing + ...
    
    __table_args__ = (
        Index("uq_client_users_client_email", "client_id", "email", unique=True),
    )
```

**Findings**:
- ✅ ADR-013 v3 single-user-RW · client_users separado de auth_users (Marcos owner)
- ✅ FK `client_id` (NOT `project_id`) · 1 client = N projects · cliente_user accede todos los projects del client
- ✅ Soft delete via `deactivated_at` (NO hard delete · ENAC trazabilidad)
- ✅ Lockout protection (`locked_until` + `failed_attempts`)
- ✅ Password policy (`must_change_password` flag forced primer login)
- ✅ UNIQUE(`client_id`, `email`) constraint

**Pool isolation**: ClientUser != AuthUser (Marcos owner) · doble pool ADR-013 sostained.

---

## Step 2 · Cliente portal routes existing

### Cliente portal structure: 28+ pages production

```
frontend/app/(client-portal)/client-portal/
  login/ · billing/ · account/ · retainer-checkin/ · policies/
  firmas-hub/ · files/ · tasks/ · transparency/ · dda/
  registros/ · evidencias/ · onboarding/ · workflow/ · actas/
  magerit/ · pentest-authorization/ · chat/ · dashboard/
  inbox/ · whatsapp/ · firma/ · incidents/ · dpc-anual/
  conformidad/
```

✅ Cliente portal **production-grade** (refactor 1.D.F.bis.III cumulative · R29 sostained).

---

## Step 3 · Cliente login flow + auto-redirect

### Backend: `backend/app/motors/m21_portal_cliente/api.py`

```python
auth_router = APIRouter(prefix="/client-auth", tags=["Portal Cliente Auth"])

@auth_router.post("/login", response_model=LoginResponse)
async def client_login(body: LoginBody, ...):
    user, token, csrf_token, exp = await auth_service.login(
        db, body.email, body.password, ip=ip, user_agent=ua,
    )
    _set_client_session_cookies(response, ...)  # httpOnly + CSRF
    return LoginResponse(
        access_token=token, expires_at=exp.isoformat(),
        must_change_password=user.must_change_password,
        full_name=user.full_name,
    )
```

**Findings**:
- ✅ Cookie-based auth httpOnly `fulkro_session` + `fulkro_csrf` (CSRF triple binding ADR-019)
- ✅ Cliente login → portal session valid 12h JWT
- ✅ `must_change_password` flag forced first login
- ✅ Failed attempts lockout protection
- 🟡 NO auto-redirect a `/client-portal/[project_id]/dashboard` per project — cliente goes a `/client-portal/dashboard` general que internally resuelve `client_id` → project via `LIMIT 1`

Per cliente portal convention current: **1 cliente = 1 proyecto típico** (LIMIT 1 query). Multi-project per client = Future-1.E.2.bis.multi-project-cliente-portal demand-driven.

---

## Step 4 · Client_users management endpoints existing (cockpit_router)

### File: `backend/app/motors/m21_portal_cliente/api.py:cockpit_router`

```python
cockpit_router = APIRouter(
    prefix="/clients/{client_id}/users",
    tags=["Cockpit - Usuarios cliente"],
    dependencies=[Depends(require_owner)],  # Marcos-only
)
```

| Endpoint | Method | Function |
|----------|--------|----------|
| `/clients/{client_id}/users` | POST | `cockpit_create_user` (auth_service.create_user + email invite + temp_password) |
| `/clients/{client_id}/users` | GET | `cockpit_list_users` |
| `/clients/{client_id}/users/{user_id}/resend-invite` | POST | `cockpit_resend_invite` (reset password + email) |
| `/clients/{client_id}/users/{user_id}/reset-password` | POST | `cockpit_reset_password` |
| `/clients/{client_id}/users/{user_id}` | DELETE | `cockpit_deactivate_user` (soft · sets `deactivated_at`) |

**Findings**:
- ✅ **5 endpoints production-grade existing** · POST + GET + RESET + RESEND + DELETE
- ✅ Email invitation HTML template existing `_render_primer_acceso_html`
- ✅ NotificationOrchestrator hook `_enqueue_client_user_invited` post-create
- ✅ ADR-013 v3 cleanup applied (NO role/scopes columns · single-user-RW uniform)
- ✅ require_owner enforced · Marcos-only

**Phase C SCOPE REDUCED**: NO backend additions needed · solo frontend tab page + components + lib api + hook.

---

## Step 5 · Project tabs structure existing

### Frontend: `/admin/projects/[id]/*` 30+ sub-routes existing

```
aepd · archetype · audit · audit-dry-run · awareness · backup-policy
bia · billing · changes · cloud-connectors · communication · conformity
contratos · dda · diagnosis · dimensiones · discovery · discrepancies
documents · dossier · equipo · evidence · exit · feature-flags · financial
implementation · magerit · mcps · obligations · onboarding · planes-accion
policies · providers · retainer · risks · roles · timeline · transparency
workspace · dashboard
```

**Findings**:
- ✅ 30+ project-scoped pages existing
- ❌ **NO** `users` tab existing per project (gap Phase C frontend)
- ❌ **NO** `personalizacion` o `settings` tab per project (gap Phase D frontend)
- ✅ Layout pattern existing `/admin/projects/[id]/layout.tsx` (ProjectFeaturesProvider + ProjectHeader + ProjectCategoryBanner + QuickActions + ProjectTabs + ActiveProjectSync + ProjectBreadcrumb · post 1.E.2 cierre)

---

## Step 6 · Project model · personalización fields baseline

### Files: `backend/app/models/core.py`

**Client model fields** (personalización per cliente):
```python
class Client:
    nombre + cif + sector + provincia + numero_empleados
    contacto_email + contacto_telefono + lead_source
    # Branding (admin_branding_api consume estos campos):
    logo_path + logo_mime_type + logo_sha256
    primary_color + secondary_color + footer_text
    # DPA compliance:
    dpa_signed_at + dpa_version + dpa_signed_minio_path
```

**Project model fields** (19 dimensiones Anexo L existing · NO branding direct):
```python
class Project:
    client_id (FK) + nombre + fase + categoria_objetivo + estado
    lifecycle_state + certified_at + grace_period_*
    sponsor_id + archetype + archetype_confidence
    lucia_enabled + whatsapp_enabled
    # 19 dimensiones (Anexo L · sub-atom 1.C.D.A.0 v3.8):
    tamano_empleados + madurez_ens_actual + geografia_operacion
    procesa_datos_sensibles_rgpd9 + aplica_nis2 + aplica_dora + aplica_ai_act
    dpo_designado + arquitectura_sistemas + multi_tenancy
    equipo_ti_tamano + certificaciones_previas + urgencia_certificacion
    presupuesto_disponible + compromiso_interno + horas_cliente_semana
```

**Findings**:
- ✅ Client model: branding completo existing (logo + 2 colors + footer)
- ❌ Project model: **NO** per-project branding fields (currently at CLIENT level)
- ✅ Project model: 19 dimensiones Anexo L · `lucia_enabled` + `whatsapp_enabled` toggles per project

**Decision Phase D**: Use **client-level branding** existing (admin_branding_api production). NO new project-level branding migration. Per multi-project per client (future) · same branding cross-projects = acceptable piloto MEDIA (1 cliente = 1 proyecto típico). Future-1.E.2.bis.per-project-branding capturable demand-driven.

### File: `backend/app/motors/m21_portal_cliente/admin_branding_api.py`

```python
router = APIRouter(
    prefix="/admin/clients", tags=["admin - Client Branding"],
    dependencies=[Depends(require_owner)],
)

GET    /admin/clients/{client_id}/branding
PATCH  /admin/clients/{client_id}/branding
DELETE /admin/clients/{client_id}/branding/logo
```

**Findings**:
- ✅ **3 endpoints production-grade existing** · GET + PATCH + DELETE logo
- ✅ ClientBrandingService validation (hex regex · footer max length)
- ✅ Logo upload likely via separate endpoint (need verify)

**Phase D SCOPE REDUCED**: NO backend additions needed · solo frontend "Personalización" tab page + components + lib api + hook.

---

## Step 7 · Settings/Personalización page existing detection

```
find frontend/app/(admin)/admin/projects/[id] -name "*settings*" → 0 results
find frontend/app/(admin)/admin/projects/[id] -name "*personalizacion*" → 0 results
find frontend/app/(admin)/admin/projects/[id] -name "*config*" → 0 results
```

✅ **Greenfield frontend pages** Phase C + Phase D · NO existing scaffolding · clean slate.

---

## Step 8 · Project CRUD endpoints

### File: `backend/app/core/clients/api.py`

```python
@router.post("/{client_id}/projects", response_model=ProjectOut, status_code=201)
async def create_project(client_id, body: ProjectCreate, db):
    project = Project(
        client_id=client_id,
        nombre=body.nombre,
        categoria_objetivo=body.categoria_objetivo,
        fase=body.fase,
    )
    db.add(project)
    await db.commit()
    return project

@router.get("/{client_id}/projects", response_model=list[ProjectOut])
async def list_projects(client_id, db): ...
```

**Findings**:
- ✅ **POST `/clients/{client_id}/projects`** create existing
- ✅ **GET `/clients/{client_id}/projects`** list existing
- ❌ **NO** DELETE project endpoint (gap Phase A · suggest add via `lifecycle_state=ARCHIVED` + `deleted_at`)
- ✅ Soft delete pattern · `deleted_at` column existing en projects table (audit FASE C previous + dossier-pack cierre cumulative)

**Phase A SCOPE**: 
- Frontend modal CreateProjectModal (form + submit POST · setActiveProject + navigate)
- Backend `DELETE /clients/{client_id}/projects/{project_id}` NEW (soft via deleted_at + lifecycle_state=ARCHIVED)
- Frontend DeleteProjectButton + confirmation modal (name-match input)

---

## Gate evaluation per briefing

| Rule | Status | Decision |
|------|:------:|----------|
| Cliente portal completo (login + redirect + dashboard) | ✅ | Phase E reduce a verification + 0-2 polish items |
| Client_users management endpoints + UI existing | 🟡 Backend ✅ · Frontend ❌ | Phase C frontend-only ~1-1.5h |
| Personalización fields + endpoints + UI existing | 🟡 Backend ✅ (client-level) · Frontend ❌ · per-project N/A demand-driven | Phase D frontend-only ~1-1.5h |
| Cumulative scope > 12h post-Phase 0 | ❌ ~5-6h empírico | NO STOP HARD · auto-arranque Phase A |
| 7ª OPS-052 manifests mayor mismatch | ❌ Aligned | NO recalibration HARD |

**Verdict**: ✅ ALL gates green · proceed Phase A auto-arranque.

---

## Phase A-F refined implementation approach

### Phase A · Project CRUD (~30-45 min)
1. Backend NEW: `DELETE /clients/{client_id}/projects/{project_id}` soft delete endpoint
2. Frontend NEW: CreateProjectModal.tsx (form: cliente combobox + name + category + sector + submit POST)
3. Frontend NEW: DeleteProjectButton.tsx + confirmation modal (name-match input)
4. Frontend ENHANCE: ProjectsPage selector landing add "Nuevo proyecto" button + delete action per card
5. Tests: 2-3 backend (DELETE soft + RLS + cascade verify) · NO unit tests frontend (Playwright only · ARTIFACT spec)

### Phase B · General info display (~30 min)
1. Frontend ENHANCE: ProjectCard add status badge + last updated relative time
2. Frontend ENHANCE: Dashboard hero per project shows cliente + project + ENS category prominent
3. Pattern reuse existing GET `/projects/{id}/header` cache TanStack Query
4. No new backend · no new endpoints

### Phase C · Client_users management (~1-1.5h)
1. Frontend NEW tab `/admin/projects/[id]/users/page.tsx`
2. Components NEW: ClientUsersTable + InviteClientUserModal + RevokeConfirmModal + ResetPasswordButton
3. lib/api/client-users-admin.ts NEW (5 methods reuse cockpit_router endpoints)
4. hooks/useClientUsersAdmin.ts NEW
5. Add `users` entry to ProjectTabs SUB_TABS navigation
6. **Reuse**: backend cockpit_router 5 endpoints production · NO new backend
7. Tests: 0 backend (existing) · ARTIFACT spec fase_37 admin

### Phase D · Personalización (~1-1.5h)
1. Frontend NEW tab `/admin/projects/[id]/personalizacion/page.tsx`
2. Components NEW: BrandingSettings (logo + 2 colors + footer · preview) + ProjectMetadataSettings (sector · status · ENS reconfig modal con warning)
3. lib/api/personalizacion-admin.ts NEW (3 methods reuse admin_branding_api + project PATCH)
4. hooks/usePersonalizacion.ts NEW
5. Add `personalizacion` entry to ProjectTabs SUB_TABS
6. **Reuse**: admin_branding_api 3 endpoints + clients PATCH client fields + (futuro per-project capability scope-out demand-driven)
7. Tests: 0 backend (existing) · ARTIFACT spec fase_37 admin

### Phase E · Cliente portal verify (~30 min)
1. Verify cliente login flow → portal dashboard (M21 production)
2. Verify R29 sostained · NO admin selector visible cliente side
3. Verify branding applied cliente portal (PortalLayout consume client_id branding)
4. Tests: 0-2 integration tests si gaps detected
5. NO regression admin scope (1.E.2 cierre)

### Phase F · E2E + close (~30 min)
1. VALIDATION_1_E_2_BIS_RECALIBRATED.md doc
2. CLAUDE.md 1.E.2.bis CERRADO section
3. Future polish captured

---

## OPS-052 + OPS-045 cumulative aplicaciones

- **OPS-045 44ª aplicación** (cumulative post 1.E.2 cierre 43ª) · Phase 0 reveals 5 endpoints cockpit_router + 3 endpoints admin_branding_api existing · scope-out duplicar backend infrastructure
- **OPS-052 strengthened Phase 0 doctrine** sostained · 7ª manifestation NO triggered · briefing nominal aligned with reality empírica (savings ~40% via audit-first)
- **ADR-013** doble pool sostained · client_users vs auth_users separation respect
- **ADR-025** 26ª aplicación cumulative sostained · NO new backend tables · NO new motors · 1 backend endpoint NEW only (soft delete project)
- **ADR-054** extended · multi-tenant production (project CRUD + client_users + personalización + activeProject context cumulative)

---

## Cross-ref

- **Phase 0 audit FASE C previous**: `docs/audits/AUDIT_FASE_C_M14_M28_FINDINGS.md`
- **1.E.2 cierre previous**: `docs/audits/VALIDATION_1_E_2_PROJECT_SELECTOR.md` + ADR-054
- **ClientUser model**: `backend/app/models/client_portal.py:21`
- **Cockpit router**: `backend/app/motors/m21_portal_cliente/api.py:cockpit_router`
- **Admin branding API**: `backend/app/motors/m21_portal_cliente/admin_branding_api.py`
- **Project CRUD**: `backend/app/core/clients/api.py:create_project`
- **Cliente portal 28+ pages**: `frontend/app/(client-portal)/client-portal/*`
