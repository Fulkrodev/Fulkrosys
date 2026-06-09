# ADR-053 · Cloud-First Architecture · Unified `m_cloud_connectors` layer sobre M16 OAuth

**Status**: Accepted · 2026-05-21 (sub-atom 1.D.X v3.12 CERRADO Skeleton CORE+)
**Cement**: OPS-045 29ª aplicación consecutiva pattern audit-first reveals 85-90% infra existing

## Context

FULKRO operaba históricamente sobre información **declarada por el cliente** vía
wizard onboarding + cuestionarios + entrevistas. Esto generaba 2 problemas
estructurales pre-piloto:

1. **Retainer post-certificación = papel**: durante la fase Retainer (M23 ·
   post-certification monitoring) Marcos no podía verificar continuamente si
   la implementación seguía vigente. El cliente podía haber cambiado MFA,
   abierto buckets públicos, deshabilitado backups · y FULKRO no se enteraba
   hasta la próxima auditoría bienal (art. 31 RD 311/2022).

2. **Diagnóstico inicial sesgado**: el cliente "completaba" el cuestionario
   M16 onboarding con respuestas optimistas o desinformadas. Marcos arrancaba
   el plan de adecuación M04 con baseline incorrecto · re-trabajo post-pentest.

Plan v3.11 original propuso 14 sub-fases C/D/E/F/G/etc. para crear un motor
`m_cloud_discovery` completo con OAuth flows nuevos. **Audit-first 1.D.X.A reveló
~85-90% de la infraestructura ya existing** en M16 onboarding (5 OAuth flows
production-grade: Microsoft 365 · Google Workspace · Azure · AWS · GitHub) +
M22 Discovery (assets + identities DTOs) + M27 Conformity catalogs (ENS measures
+ severity rules) + m24_idms (manual upload Excel fallback).

## Decision

Construir **`m_cloud_connectors`** como **unified layer ADDITIVE** sobre M16
OAuth existing · NO duplicar:

### Arquitectura (4 sub-fases + cierre)

**Sub-fase B · Backend foundation** (commit `336a1d6` · 2692 LOC · 25 tests):
- 4 tablas project-scoped (`cloud_connectors` · `cloud_resources` · `cloud_gaps`
  · `cloud_sync_jobs`) · RLS enforced project_id (LECCION-OPS-008)
- `CloudConnector` con FK opcional a `connector_configs` (M16 ConnectorConfig
  existing) · ON DELETE SET NULL · NO duplicar OAuth state (ADR-025 sostener)
- `CloudConnectorService` idempotent (UPSERT on UNIQUE(project_id, provider))
  con `trigger_sync` mock_mode + real adapter mode (delega a M16 BaseConnector
  vía `connectors/registry.py` lookup)
- 9 endpoints REST (6 admin project-scoped + 3 cliente portal) · `require_owner`
  + `require_client_user` (ADR-013 doble pool auth)
- Mensajería cliente friendly_message server-side (R29 sostener)

**Sub-fase H · Diagnostic Gap Engine deterministic R1** (commit `5b254ea` ·
1425 LOC · 32 tests):
- `gap_rules.py` · catálogo 8 reglas pure-function detectors sobre CloudResource
  lists (op.acc.6 MFA · op.acc.5 privilegios · op.exp.1 inventario · op.exp.8
  logging · mp.info.3 cifrado · mp.s.2 buckets públicos · op.cont.3 backup ·
  org.1 documental)
- Categorización ENS estricta BASICA ⊂ MEDIA ⊂ ALTA con superset enforcement
- Severity alineada con `gap_severity_rules_v1.yaml` + `medidas_criticas_nucleares`
  existing (CCN-STIC 803/808)
- `DiagnosticGapEngine.run_diagnosis()` UPSERT idempotente 1-row-per-
  (project_id, ens_measure_code) + auto-resolve gaps que dejan de emitir
- **R1 INVIOLABLE**: pipeline 100% deterministic · LLM 0 invocaciones · test
  verify con `patch('anthropic.Anthropic')` + `anthropic_mock.call_count == 0`
- `_render_explanation` pure Python format (NO LLM en pipeline base · LLM
  enrichment opcional endpoint dedicado T1 polish)
- Endpoint `POST /admin/projects/{id}/cloud-diagnosis/run` · idempotente

**Sub-fase I · Cliente onboarding NEW primer paso** (commit `95923f0` ·
866 LOC · 3 E2E specs):
- Component `CloudConnectFirstStep.tsx` · grid de 6 provider cards super mega
  fácil (R29 sostener firmísimo · cero presión)
- Hero amistoso: "Tranquilo · solo lectura · 5 minutos. Puedes saltar y
  conectar después." + tooltips Help + Security primer-principios
- Tab "Conecta sistemas" como **default first tab** en `/client-portal/onboarding`
- Skip button → switches a Wizard tab (R29 sin presión coercitiva)
- Init OAuth flow delega a M16 portal_api existing (NO duplicar PKCE · ADR-025
  sostener)
- Manual upload fallback siempre disponible (link a `/client-portal/files`
  via m24_idms intake)

**Sub-fase J · Admin UI project-scoped** (commit `779f4e0` · 1345 LOC ·
3 E2E specs):
- Page `/admin/projects/{id}/cloud-connectors` con 4 Tabs (Conectores · Recursos
  · Gaps · Monitoring) + 4 KPI cards hero
- Tab Conectores: list + sync button + revoke + drill-down ver recursos
- Tab Gaps: filters severity + include_resolved + "Ejecutar diagnóstico"
  button + GapCard con resolve mutation
- Tab Monitoring: preview retainer L · sub-fase L wire posterior
- ProjectTabs entry "Conexiones Cloud" Cloud icon en SUB_TABS (R23 sostener)

**Sub-fase K-light · Integrations 3 motores** (commit `7399c42` · 772 LOC ·
10 tests):
- Approach pragmático **ADDITIVE · 0 breaking changes en M03/M04/M07**
- 3 funciones puras en `integrations.py`:
  - `get_measure_cloud_status` / `get_measures_cloud_status_bulk` (M03 DdA
    enrichment · returns implemented/missing/misconfigured/documental/unknown)
  - `iter_gaps_for_plan_actions` (M04 Plan auto-populate suggestions sorted
    por severity)
  - `iter_evidences_for_attach` (M07 Evidence auto-attach desde cloud resources
    con mapping ENS measure → resource_types)
- 3 endpoints REST `/admin/projects/{id}/cloud-integrations/*` para UI consumption
- Motores fuente NO modificados · siguen funcionando 100% sin cloud (manual
  fallback m24_idms intacto)

**Sub-fase L-light · M23 Retainer monitoring continuous** (commit `23783fa` ·
419 LOC · 7 tests):
- 2 Celery tasks registradas en `celery_app.py` beat_schedule:
  - `cloud_connectors.daily_diagnosis` · daily 04:00 ES · re-ejecuta
    `DiagnosticGapEngine` per project con CloudConnector activo (post-backup
    pre-business hours)
  - `cloud_connectors.monthly_digest` · día 1 mes 09:00 ES · genera
    compliance snapshot per project en `lifecycle_state=RETAINER`
- L-light scope: snapshots-only + diagnosis re-run · auto-send M06 templates
  + WhatsApp alerts diferidos T1 polish post-piloto
- Compliance score determinístico: `100 - critical*10 - high*5 - medium*2 - low*1`

### Cliente-side flow primer paso

1. Cliente recibe magic link · login portal · llega a `/client-portal/onboarding`
2. Tab "Conecta sistemas" activo por defecto (NEW · pre-1.D.X era "Wizard")
3. Cliente ve 6 cards (M365 · Google · Azure · AWS · GitHub · Excel manual)
4. Click "Conectar" en provider → OAuth flow M16 existing (read-only siempre ·
   ADR-014) → callback persiste M16 ConnectorConfig
5. Backend trigger sync (sub-fase L daily o admin manual) → DiscoveryResult M16
   normalizado a CloudResource records con checksum SHA-256
6. DiagnosticGapEngine corre per categoría ENS del proyecto · UPSERT
   CloudGap records · auto-resolve los que dejan de emitir

### Admin-side flow

1. Marcos abre `/admin/projects/{id}/cloud-connectors`
2. Ve 4 KPI cards hero (conectores activos · recursos · gaps críticos/altos)
3. Tab Conectores: ver status real-time · forzar sync · revocar
4. Tab Recursos: drill-down por connector · tabla con tipo/external_id/detected_at
5. Tab Gaps: filtros severity · ejecutar diagnóstico · resolver con note opcional
6. M03 DdA cliente view consume `/cloud-integrations/measure-status?codes=` para
   enriquecer cada medida con `cloud_status` (implemented/missing/etc)
7. M04 Plan service puede iterar gaps como suggestions vía `/plan-suggestions`

## Consequences

### Positivas

- **Diferencial competitivo único España**: FULKRO es el único consultor ENS
  con cloud-first auto-detection · resto del mercado opera con cuestionarios
  declarativos.
- **Retainer real (no papel)**: monitoring continuo + alertas críticas detectan
  drift entre auditorías bienales.
- **Diagnóstico verdadero pre-baseline**: Marcos arranca M04 Plan con datos
  reales · NO con declaraciones optimistas.
- **Compatibility intacta**: motores M03/M04/M07 siguen funcionando 100% sin
  cloud (manual fallback m24_idms) · adopción gradual cliente-by-cliente.
- **ADR-025 sostenido firmísimo**: NO duplicar OAuth · NO duplicar Discovery
  DTOs · reuse 5 connectors M16 production-grade.
- **R1 INVIOLABLE sostenido**: DiagnosticGapEngine 100% deterministic · LLM 0
  invocaciones en pipeline base · trazabilidad ENAC asegurada via raw_evidence
  JSONB.

### Negativas / Mitigaciones

- **Complejidad operativa Celery beat**: 2 nuevos tasks daily/monthly aumentan
  carga DB. Mitigación: scheduled fuera horario business (04:00 ES) · idempotent
  con auto-resolve · degradación silenciosa si Celery no instalado (stub fallback).
- **Privacy concerns**: clientes pueden preocuparse por conexión cloud.
  Mitigación: tooltips Security explícitos · read-only siempre (ADR-014) ·
  revocable en 1 click · tokens cifrados Fernet AES-128.
- **Cobertura inicial limitada**: 8 reglas detectoras solo cubren subset de las
  73 medidas Anexo II. Mitigación: T1 polish post-piloto demand-driven · sub-fases
  K-full / L-full diferidas hasta validación con cliente real.

### Deferred T1 demand-driven post-piloto

- Integration motores **M01/M02/M19/M22/M27** con cloud data (3 críticos M03/M04/M07
  cubren MVP)
- Sub-fases originales plan v3.11 C/D/E/F/G/etc. agregando connectors nuevos
- Auto-fix actions cloud (campo `auto_fixable` preparado · execución futuro)
- WhatsApp + Email alerts on critical change (notifications module wire)
- M06 auto-send digest mensual via template `retainer_monthly_digest.docx`
- Tests E2E sandbox dedicada (specs integrados en B+I+J sub-fases)

## Compatibility / Backwards

- Motores M03/M04/M07 **NO modificados** · APIs intactas · contratos preservados
- Manual fallback siempre disponible via `/client-portal/files` (m24_idms intake)
- Projects sin cloud connectors funcionan idéntico a pre-1.D.X
- Celery stub fallback OK (dev sin Redis funciona)
- TS strict + ESLint 0 errors · 0 regresiones cumulative (74/74 backend tests
  verde)

## Commits cumulative (8 commits · ~17h empírico vs ~25-30h nominal · ahorro ~40%)

| Sub-fase | Commit | LOC | Tests |
|---|---|---|---|
| B · Backend foundation | `336a1d6` | 2692 | 25 verde |
| H · Diagnostic Gap Engine R1 | `5b254ea` | 1425 | 32 verde |
| I · Cliente onboarding NEW | `95923f0` | 866 (TS) | 3 E2E specs |
| J · Admin UI 4 Tabs | `779f4e0` | 1345 (TS) | 3 E2E specs |
| K-light · Integrations M03/M04/M07 | `7399c42` | 772 | 10 verde |
| L-light · Retainer Celery tasks | `23783fa` | 419 | 7 verde |
| N · ADR + CLAUDE.md cierre | (this) | — | — |
| **Cumulative** | | **~7500 LOC** | **74 backend + 6 E2E specs** |

## References

- OPS-045 29ª aplicación · audit-first reveals infrastructure existing pattern
- ADR-013 doble pool auth (admin / cliente)
- ADR-014 read-only OAuth siempre (NO escalable destructivo)
- ADR-025 reuse existing models · NO duplicar tablas
- LECCION-OPS-008 RLS project_id en TODAS las tablas tenants
- `docs/catalogs/ens_measures_catalog_v1.yaml` (79 medidas Anexo II)
- `docs/catalogs/gap_severity_rules_v1.yaml` (CCN-STIC 803/808 + nucleares)
- `backend/app/motors/m16_onboarding/connectors/` (5 OAuth providers existing)
- `backend/app/motors/m_cloud_connectors/` (esta capa unified · sub-atom 1.D.X)
