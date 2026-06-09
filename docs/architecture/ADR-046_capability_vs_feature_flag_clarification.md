# ADR-046 · Capability vs Feature Flag clarification + Q5.3 cement explicit

> Rename history: originally created as ADR-037 (MB-10 Atom 10.0 · 2026-05-13) ·
> renamed to ADR-046 post-audit (B1.2 · OPS-063 cement) to resolve collision
> con existing inline ADR-037 (AI Auditor pro · SAN-D MB-15) en `docs/spec/DECISIONS.md`.

## Status: ACCEPTED 2026-05-13

## Context

Pre-audit Atom 10.2 (MB-10) reveló:

1. Yo (Claude) cementé concepto "M32 Capabilities" memoria sin spec literal
2. Master plan real = `docs/master_plan/fulkro_26_motores_v1.md` (M01-M26 + M27-M31 incrementals)
3. M32 mencionado SOLO docs ISMS Block 1 como placeholder textual sin scope semántico
4. ADR-036 SAN-D MB-17 ya cementó `core/feature_flags/` infrastructure widely-used (8+ componentes)
5. ADR-036 explícitamente difirió `feature_flag_overrides` table a "MB-19+"
6. Mi propuesta inicial Atom 10.2 (capability table granted/revoked + client_id + audit_log) = semantically equivalent al deferred ADR-036

## Decision

### Architectural unification

1. **M32 in ISMS compliance docs** = LOGICAL motor concept (terminology ISMS preservada)
2. **Implementation LIVES IN** `backend/app/core/feature_flags/` (ADR-036 infrastructure)
3. **NEW table `feature_flag_overrides`** materializa ADR-036 deferred (MB-10 Atom 10.2)
4. **NO separate `m32_capabilities/` motor** · NO 2 paralelos divergence risk
5. **Frontend `useProjectFeatures` transparent merge** overrides · NO new hook

### Schema feature_flag_overrides

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | Standard (FullMixin pattern) |
| project_id | UUID FK projects (nullable) | Project-level override |
| client_id | UUID FK clients (nullable) | Client-level override (tenant-wide) |
| feature_key | VARCHAR | Override target |
| override_value | JSONB | Boolean OR complex value |
| granted_at | TIMESTAMPTZ | Audit |
| expires_at | TIMESTAMPTZ NULLABLE | Expiry natural filter |
| granted_by_user_id | UUID FK auth_users | Audit |
| revoked_at | TIMESTAMPTZ NULLABLE | Soft delete pattern |
| revoked_by_user_id | UUID FK auth_users NULLABLE | Audit |
| reason | TEXT NULLABLE | Optional grant/revoke justification |

CHECK constraint: `(project_id IS NOT NULL OR client_id IS NOT NULL)` — al menos uno definido.

RLS policy USING:
```
client_id = current_client_id()
OR project_id IN (SELECT id FROM projects WHERE client_id = current_client_id())
OR current_client_id() IS NULL
```

OPS-054 sostained: `ALTER TABLE ... OWNER TO fulkro_migrate` pre-ENABLE RLS.

audit_log integration: triggers BD existentes capturan INSERT/UPDATE/DELETE automaticamente (hash chain `fn_audit_log_hash_chain`). NO `audit_log_id FK` necesario — chain via `tabla='feature_flag_overrides'` + `registro_id=overrides.id`.

### Q5.3 cement explicit literal

**Roles ENS staff** (Responsable Seguridad · Sponsor · RSEG · Auditor interno) cataloged via M30 contactos · **INVISIBLE cliente UI** · admin-only management.

**Capabilities (feature_flag_overrides)** tiered scope:

- **ADMIN management UI**: visible (Atom 10.3 admin UI grants/revokes overrides)
- **CLIENT UI capabilities visibility**: INVISIBLE cliente per Q5.3 pattern sostained
  - Cliente sees ENABLED features as if natural (no "premium granted by admin" labels)
  - NO list "your capabilities" cliente-facing
  - Capabilities work transparent behind `useProjectFeatures` hook

**Result**: Atom 10.4 cliente UI = SKIP (Q5.3 cement INVISIBLE applied)

### Migration path forward

- **Atom 10.2** (this MB-10): `feature_flag_overrides` table + helpers + admin API
- **Atom 10.3** (this MB-10): admin UI extension existing `/admin/projects/[id]/features` panel
- **Atom 10.4** (this MB-10): SKIP per Q5.3 cement
- **Forward**: ISMS docs reference "M32" preserved as LOGICAL term · NO file/folder rename needed

## Consequences

### Positive

- Single source of truth feature evaluation (`core/feature_flags/`)
- 8+ frontend components UNCHANGED (`useProjectFeatures` transparent merge)
- ADR-036 deferred materializado · debt resolved
- Q5.3 cement explicit documented · forward unambiguous
- Effort savings ~40% vs original Atom 10.2 estimate (~3-4h vs 5-7h)
- NO motor duplicado architecturally clean
- ISMS terminology preserved (M32 LOGICAL concept)

### Negative

- ISMS docs reference "motor M32" without filesystem motor folder · acceptable (LOGICAL motor concept)
- Si future need for client-level entitlements distinct from feature flags → could revisit (deferred)
- New `docs/architecture/` directory established (ADR-as-file pattern vs existing inline `docs/spec/DECISIONS.md`)

## References

- ADR-036 SAN-D MB-17 · `core/feature_flags/` infrastructure
- `docs/compliance/04-ISMS_ISO27001/Information_Security_Policy_FULKRO.md:26`
- `docs/compliance/04-ISMS_ISO27001/Asset_Register_FULKRO.md:80`
- Q5.3 cement (Roles ENS INVISIBLE cliente · M30 stakeholders admin-only)
- OPS-026 audit-first sostained 28ª aplicación (this audit win)
- OPS-050 cement 8ª vez (MEMORY drift M32 vaporware detected)
