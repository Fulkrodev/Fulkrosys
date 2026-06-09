# AUDIT Phase 1C · OAuth Cloud Connectors Empirical State

**Sesión**: 3B-2B.8 CLUSTER 1 Phase 1C
**Fecha**: 2026-05-26
**Ejecutor**: Phase 1C.0 OPS-052 Phase 0 micro-audit (mandatory pre-implementation)
**Status**: ✅ **ADDRESSED · Phase 1C Opción C shipped commit `d894aed`** (CLUSTER 1 cierre validation 2026-05-26)

> **Historical note**: original status was 🛑 STOP HARD recalibrate (OPS-052 21ª manifestation). Architect approved **Opción C** scope refined: NEW `/cloud-connections` steady-state mgmt page · reusa `CloudConnectFirstStep` component-level · disconnect chat-mediated (ADR-014 sostained · NO endpoint cliente). Shipped: 6/6 backend tests PASS · 140/140 m21 regression · 4 Future-X captured (consolidation · self-service disconnect · per-connector remediation grouping · headerless mode CloudConnectFirstStep).

---

## Resumen ejecutivo

Briefing Phase 1C asumió "NEW page from scratch · 5 endpoints backend · 5 providers (M365+Google+AWS+Azure+GCP)" pero empirical reveals **infrastructure ALREADY ~70-80% covered**:

- ✅ **2 implementaciones cliente cloud-connect existing en paralelo** (`CloudConnectFirstStep` 1.D.X.I + `ConnectorsClientView` 1.D.X.B older)
- ✅ Backend cliente API ready (3 cliente endpoints + admin-only revoke per ADR-013/-014)
- ✅ OAuth callback page existing redirige a `/onboarding` (NOT a una NEW page `/cloud-connections`)
- ✅ Remediations cliente UI existing en `/remediaciones` (Spanish naming · NOT `/remediations` briefing assumption)
- ❌ **GCP NOT supported** · empirical providers: M365 + Google Workspace + Azure + AWS + GitHub + MANUAL_IMPORT
- ❌ **DELETE disconnect cliente NOT exists** · admin-only revoke por ADR-014 read-only enforcement implication

OPS-045 49ª aplicación: ahorro empírico potencial ~70% Phase 1C nominal ETA (~4-6h → ~1-2h selective enhancement).

---

## Phase 1C.0.1 · OAuth callback page (existing)

**Path**: [frontend/app/(client-portal)/client-portal/onboarding/oauth-callback/page.tsx](../../frontend/app/(client-portal)/client-portal/onboarding/oauth-callback/page.tsx)

- Suspense wrapper + `OAuthCallbackInner` reads `code` + `state` + `project_id` + `connector` query params
- POST `oauthCallback(projectId, connectorType, { code, state })` → `@/lib/client-onboarding/api`
- Success → router.push(`/client-portal/onboarding?connector=...&connected=true`) (NOT a `/cloud-connections` route)
- Error path: pre `<Card>` con XCircle + raw errorMsg + "Volver al portal" CTA

**Implicación**: Phase 1C briefing assumed callback redirects to NEW `/cloud-connections` page. Empirical: redirige `/onboarding`. NEW page conflicts unless OAuth callback URL changes (breaking change para connectors ya conectados pre-Phase 1C).

---

## Phase 1C.0.2 · Backend CloudConnector API empirical

**Path**: [backend/app/motors/m_cloud_connectors/api_cliente.py](../../backend/app/motors/m_cloud_connectors/api_cliente.py)

| Endpoint | Existe | Notas |
|----------|:------:|-------|
| GET `/api/v1/client-portal/cloud-connectors` | ✅ | list per project · resumen R29 friendly_message |
| POST `/api/v1/client-portal/cloud-connectors/connect/{provider}` | ✅ | init OAuth → delega M16 `/api/v1/portal/connectors/{provider}/authorize` (ADR-025) |
| GET `/api/v1/client-portal/cloud-connectors/providers/catalog` | ✅ | catalog UI cards |
| GET `/api/v1/client-portal/cloud-monitoring/digest/latest` | ✅ | digest mensual cliente filtered (NO leak admin sensitive) |
| GET `/api/v1/client-portal/cloud-connectors/{id}/status` | ❌ | NO separate endpoint · status incluido en list response per-connector |
| GET `/api/v1/client-portal/cloud-connectors/{provider}/callback` | ❌ | NO en api_cliente · OAuth callback handled por M16 portal_api backend |
| DELETE `/api/v1/client-portal/cloud-connectors/{id}` | ❌ | **admin-only** revoke en `/api/v1/admin/projects/{pid}/cloud-connectors/{cid}` |

**Implicación**: Briefing assumed 5 cliente endpoints; empirical: 3 cliente + admin-only revoke. ADR-014 read-only OAuth + ADR-013 doble pool implication: disconnect cliente puede scope-out (cliente solicita disconnect via chat → Marcos revokes admin).

---

## Phase 1C.0.3 · Cloud connectors UI existing (DOS implementaciones paralelas)

### Implementación A · `CloudConnectFirstStep` (1.D.X.I sub-atom · 406 LOC)
**Path**: [frontend/components/client-portal/CloudConnectFirstStep.tsx](../../frontend/components/client-portal/CloudConnectFirstStep.tsx)

- Hero R29 friendly + "Saltar por ahora" CTA
- Grid catalog backend providers (6 providers · responsive `sm:grid-cols-2 lg:grid-cols-3`)
- Status badges + `friendly_message` server-side + `data-testid` coverage
- 3 modal helpers: HelpModal + SecurityModal + ManualUploadHint
- WCAG aware (role="dialog" + aria-modal + aria-label)
- Connect flow: POST `/connect/{provider}` → oauth_redirect OR manual_upload
- API client: `cloud-connectors-client.ts` (cliente-scoped wrapper)

### Implementación B · `ConnectorsClientView` (1.D.X.B older · 349 LOC)
**Path**: [frontend/components/client-portal/ConnectorsClientView.tsx](../../frontend/components/client-portal/ConnectorsClientView.tsx)

- Grid 5 providers hardcoded local meta (github + microsoft + azure + aws + google + base)
- Connect Warning Dialog + AWS IAM Key Dialog separate (AWS NO OAuth · IAM key form)
- "Sincronizar" CTA per connector (RefreshCw)
- API client: `useOnboardingClient` hooks → diferente backend path
- NO modal helpers · NO friendly_message · NO data-testid uniform

### Integration: `/client-portal/onboarding` (4-tab)
**Path**: [frontend/app/(client-portal)/client-portal/onboarding/page.tsx](../../frontend/app/(client-portal)/client-portal/onboarding/page.tsx)

Tabs: `connect` (renders `CloudConnectFirstStep`) + `wizard` + `connectors` (renders `ConnectorsClientView`) + `lms` cursos.

**Implicación duplicación**: A+B implementan misma feature con diferentes datos backend · OPS-026 DRY violation latente · candidate refactor consolidación.

---

## Phase 1C.0.4 · Providers empirical

`CloudConnectorProvider` enum ([backend/app/motors/m_cloud_connectors/models.py:40](../../backend/app/motors/m_cloud_connectors/models.py#L40)):

| Provider | Briefing | Empirical | Auth flow |
|----------|:--------:|:---------:|-----------|
| MICROSOFT_365 | ✅ | ✅ | OAuth |
| GOOGLE_WORKSPACE | ✅ | ✅ | OAuth |
| AZURE | ✅ | ✅ | OAuth |
| AWS | ✅ | ✅ | **IAM access key (NOT OAuth)** · STS GetCallerIdentity |
| GCP | ✅ | ❌ | NOT supported · GCP missing del enum |
| GITHUB | ❌ | ✅ | OAuth |
| MANUAL_IMPORT | ❌ | ✅ | CSV/Excel upload via m24_idms |

---

## Remediations cliente UI existing

**Path**: [frontend/app/(client-portal)/client-portal/remediaciones/page.tsx](../../frontend/app/(client-portal)/client-portal/remediaciones/page.tsx) (Spanish naming · NOT `/remediations`)

Implementa briefing Phase 1C.2 INTENT empirical:
- `RemediationCard` per gap · 3 secciones (pendientes/en-progreso/resueltas)
- SSE subscribe `useClientProjectEvents` con cloud_remediation_* event types
- `ApprovalModal` para approve/reject decision
- R29 firmísimo · friendly Spanish · NO presión

Briefing Phase 1C.2 "per connector card · Expandable accordion · Remediations pendientes" = **architectural drift**: actual UX separa Remediations dedicated page (clearer mental model) vs nested per-connector.

---

## Recomendaciones scope refinement (architect approve required)

### Opción A · SCOPE-OUT Phase 1C entirely (recomendada)
Empirical: feature **YA cubierta funcionalmente** vía `/onboarding` tabs A+B + `/remediaciones` dedicated. ROI Phase 1C marginal vs siguientes Phases (1D Copilot proactivity · 1E Magic-link auditor flow).
- ETA: 0h (skip)
- Risk: 0 destructive
- Sostiene OPS-045 audit-first · NO greenfield duplicación

### Opción B · CONSOLIDATE A+B duplicates (refactor)
Refactor `ConnectorsClientView` → reusar/delete a favor `CloudConnectFirstStep`. OPS-026 DRY enforcement. Onboarding tabs `connect` + `connectors` merge into single tab.
- ETA: ~3-4h
- Risk: medium (touches onboarding tabs + hooks layer · backwards compatibility cliente conectado)
- Sostiene OPS-026

### Opción C · NEW `/cloud-connections` steady-state mgmt page (briefing original refined)
NEW page reusa `CloudConnectFirstStep` component-level (NO duplicar) · diferencia onboarding "first-time" vs cloud-connections "steady-state daily mgmt". Add per-connector remediation count badge (link `/remediaciones?filter=connector_id`). Add cliente "Solicitar disconnect" button → opens chat con Marcos (NO endpoint cliente · ADR-014 sostenido).
- ETA: ~1.5-2h (reuse existing component · NO new logic)
- Risk: low (additive)
- Sostiene ADR-014 + ADR-025 + OPS-026

### Opción D · EXTEND `/remediaciones` con per-connector grouping (briefing 1C.2 intent)
Modify `/remediaciones` page existing add `groupBy(connector)` view toggle · NO new page. Cliente sees remediations clustered by source.
- ETA: ~1-1.5h
- Risk: low (UX-only change)
- Sostiene OPS-026

---

## ETA cumulative Phase 1C delta

| Option | ETA | Patterns reuse | Risk |
|--------|-----|----------------|------|
| A scope-out | 0h | n/a | 0 |
| B consolidate refactor | 3-4h | OPS-026 DRY | medium |
| C NEW steady-state page | 1.5-2h | reuse component A | low |
| D extend remediaciones | 1-1.5h | reuse SSE + RemediationCard | low |

vs briefing nominal **~4-6h** Phase 1C original.

---

## STOP HARD trigger justification (OPS-052 21ª manifestation cumulative)

Phase 0 micro-audit reveals mismatch >30%:
- ❌ Briefing "NEW page from scratch" vs empirical 2 implementaciones paralelas existing
- ❌ Briefing "5 endpoints" vs empirical 3 cliente + admin-only revoke
- ❌ Briefing "GCP provider" vs empirical NOT supported
- ❌ Briefing "DELETE disconnect cliente" vs empirical admin-only ADR-014 implication
- ❌ Briefing "/remediations path" vs empirical Spanish `/remediaciones`

Per `CLAUDE.md` doctrine: **"STOP HARD architect briefing recalibrate"** invoked. Awaiting architect approval scope refined entre A/B/C/D antes Phase 1C.1 implementation.

---

## Decisión pendiente

> ⏸️ **Marcos / architect**: ¿Cuál opción A/B/C/D apruebas para Phase 1C? O combina (ej: A + future-X consolidate B).
