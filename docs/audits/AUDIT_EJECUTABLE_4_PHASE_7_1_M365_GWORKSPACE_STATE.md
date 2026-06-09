# AUDIT Ejecutable 4 Phase 7.1.0 · M365 + GWorkspace + SharePoint Connectors State Empirical

**Fecha**: 2026-05-27
**Sesión**: Ejecutable 4 · Sesión 3B-2B.7 Cloud Connections (Opción C scope refined)
**Status**: Phase 7.1.0 audit COMPLETO · proceed Phase 7.1.1 implementation polish

## Architecture empirical · m_cloud_connectors

Single unified module `backend/app/motors/m_cloud_connectors/` (7058 LOC total):
- `base_connector.py` (129 LOC) · thin adapter sobre M16 BaseConnector
- `integrations.py` (960 LOC) · M03/M04/M07 cross-motor integration
- `gap_rules.py` (449 LOC) · 8 deterministic detector rules
- `models.py` (605 LOC) · CloudConnector/CloudResource/CloudGap/CloudSyncJob ORM
- `service.py` (554 LOC) · orchestration layer
- `api.py` (855 LOC) · admin endpoints
- `api_cliente.py` (480 LOC) · cliente-mínimo R29 friendly_message
- `remediation_orchestrator.py` (785 LOC) · remediation OPTIONAL flow
- `remediation_api.py` (524 LOC) · remediation endpoints
- `diagnostic_gap_engine.py` (291 LOC) · orchestrates rule execution
- `digest_service.py` (416 LOC) · MoM digest snapshots
- `system_consciousness_hooks.py` (419 LOC) · lifecycle hooks
- `tasks.py` (246 LOC) · Celery tasks
- `schemas.py` (254 LOC) · Pydantic DTOs

Provider concrete impls live en `backend/app/motors/m16_onboarding/connectors/`:
- `microsoft365.py` (123 LOC) · Graph API client_credentials
- `google_workspace.py` (105 LOC) · Admin SDK service account
- `aws_connector.py` · DEFER Future-3B-2B-7-EXPANDED
- `azure_connector.py` · DEFER Future-3B-2B-7-EXPANDED
- `github_connector.py` · DEFER Future-3B-2B-7-EXPANDED

## M365 connector empirical gaps (microsoft365.py)

**Endpoints actual**:
- ✅ `/oauth2/v2.0/token` (client_credentials OAuth)
- ✅ `/organization` (validate_credentials)
- ✅ `/users` (identity discovery basic)
- ✅ `/groups` (identity discovery)
- ✅ `/deviceManagement/managedDevices` (endpoint assets)

**Gaps críticos cliente-mínimo + ENS detection**:

| Field/Endpoint | ENS measure impacto | Status |
|----------------|--------------------|--------|
| `mfa_enabled` per user | op.acc.6 nuclear CRITICAL | ❌ NO emitido · `detect_users_without_mfa` ciego |
| `is_privileged` per user | op.acc.5 HIGH | ❌ NO emitido · `detect_excess_privileged_users` ciego |
| SharePoint sites discovery | mp.s.2 (public sites) + mp.info.3 (sensitive data) | ❌ NO endpoint `/sites` |
| Conditional access policies | op.acc.6 reinforcement | ❌ NO endpoint `/policies/conditionalAccessPolicies` |
| Token expiration handling | OAuth resilience | ❌ Cached forever sin refresh |
| Pagination follow | discovery completeness | ❌ Solo `$top=999` · NO `@odata.nextLink` |

## GWorkspace connector empirical gaps (google_workspace.py)

**Endpoints actual**:
- ✅ `/oauth2.googleapis.com/token` (token endpoint)
- ✅ `/admin/directory/v1/users` (identity discovery con `isEnrolledIn2Sv` + `isAdmin`)
- ✅ `/admin/directory/v1/groups` (groups)
- ✅ `/customer/my_customer/devices/mobile` (mobile devices)

**Gaps menores cliente-mínimo + ENS detection**:

| Field/Endpoint | ENS measure impacto | Status |
|----------------|--------------------|--------|
| `mfa_enabled` per user | op.acc.6 nuclear CRITICAL | ✅ Set via `isEnrolledIn2Sv` |
| `is_privileged` per user | op.acc.5 HIGH | ✅ Set via `isAdmin` |
| Shared drives discovery | mp.s.2 + mp.info.3 (Drive Google equivalent SharePoint) | ❌ NO endpoint `/drives.list` |
| JWT signing service account | Production OAuth | ❌ Assumes pre-generated access_token |
| Pagination follow | discovery completeness | ❌ Solo `maxResults=500` · NO `nextPageToken` |

## Cliente-mínimo filosofía verify

✅ `api_cliente.py` `require_client_user` (ADR-013 doble pool)
✅ `CloudConnectorPublicSummary` schema · NO leak scopes/IDs internos M16
✅ `friendly_message` R29 sostained · sin presión coercitiva · congrats tone
✅ `request-disconnect` chat-mediated (Pattern Phase 1C · ADR-014 sostained · NO destructive cliente)
✅ `audit_log` Sub-atom 5.A 3-way OR propagated
✅ `ClientDigestView` schema filtered · NO admin sensitive leak

## Pattern reuse sostained

✅ Pattern #14 SSE+ClientNotification dual emit (cloud.connector.* events)
✅ Pattern #15 proactive nudge scheduler (digest_service)
✅ Pattern #20 gap translation cliente-friendly (gap_rules.py R29 templates)
✅ Sub-atom 5.A audit_log 3-way OR propagated (api_cliente.py _emit_audit_log)

## Polish scope refined per architect approve Opción C

**Phase 7.1.1 implementation (~30-60 min empirical likely OPS-045 sostained)**:

1. **M365 polish · mfa_enabled detection**:
   - Approach pragmatic: enumerate `/reports/authenticationMethods/userRegistrationDetails` (single API call · returns per-user MFA registration status)
   - Fallback: assume `mfa_enabled=None` (unknown · gap rule defensive defaults FALSE only if explicit False)

2. **M365 polish · is_privileged detection**:
   - Approach pragmatic: enumerate `/directoryRoles` + per-role `/directoryRoles/{id}/members` · build set of privileged user IDs · set `is_privileged=True` para users en set
   - Cost: 1 API call + N (typically <20 roles) sub-calls

3. **M365 polish · SharePoint sites discovery**:
   - Endpoint: `/sites?search=*` · returns sites collection
   - Asset_type: `asset.sharepoint_site`
   - Attributes: `public_access` (from site.sharingCapability) · `is_public` (from siteCollection.root.webId access)

4. **GWorkspace polish · Shared drives discovery**:
   - Endpoint: `/drives` (Drive API · NOT Admin SDK) · requires additional scope
   - Asset_type: `asset.shared_drive`
   - Attributes: `public_access` (from sharing settings)

5. **Provider agent guidance constant**:
   - New: `CONNECTOR_PROVIDER_ENS_GUIDANCE` map provider → list ens_measure_codes detectable
   - Used by: future audit reports + cliente onboarding UI explanation

6. **Remediation OPTIONAL flow**:
   - Already existing 785 LOC orchestrator · verify cliente decision flow (apply/skip)
   - Pattern #14 SSE+ClientNotification ya implementado

## OPS-045 audit-first projection

- Nominal scope brief: ~3-5h M365+GWorkspace polish
- Empirical projection likely: ~30-60 min (-85% per architect briefing)
- Infrastructure existing 85%+ (api_cliente + gap_rules + remediation already exist)
- Polish scope LIMITED a connector-level enrichment (additive · NO breaking)

## Phase 7.2 DEFER scope expansion (architect approve · 7 items NEW Sesión 3B-2B.7-EXPANDED)

Documented post-piloto demand-driven cuando cliente real demande.

## Phase 7.3 E2E tests M365 + GWorkspace cross-provider

Scaffold tests (NO requires real M365/GWorkspace sandbox · mock providers) · runnable post Future-1.E.radar.alembic-version-num-widen applied.
