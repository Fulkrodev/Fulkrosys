# FULKRO Backlog · post-SAN-D consolidado

**Fecha**: 2026-05-07
**Status**: SAN-D resolved · SAN-E roadmap activo
**Source**: ADRs 035-045 deferrables + master plan post-cliente real

═══════════════════════════════════════════════════════════════

## SAN-D items resueltos · 9 mega-bloques

### MB-13 (resuelto · ADR-035)
- ✅ Sistema vivo NextActionCard
- ✅ AlertService SSE event-driven
- ✅ alert_queue table + AlertBell component
- ✅ Celery beat 13 tasks daily/weekly

### MB-14 (resuelto · ADR-038)
- ✅ Portal cliente workspace 6 pages
- ✅ ClientTaskService + 18 templates YAML
- ✅ ChatService SLA <2h + WebSocket
- ✅ Audit hash chain ClientUserAudit

### MB-15 (resuelto · ADR-037)
- ✅ AI Auditor A11 dry-run pre-ENAC
- ✅ Magerit Libro II catálogo + auto-mapping
- ✅ Sector overlays (sector_salud · aapp · fintech · industria)

### MB-16 (resuelto · ADR-039)
- ✅ NotificationOrchestrator email + portal SSE
- ✅ Postmark provider + DND timezone-aware
- ✅ wa.me link info-mode (NO Meta API)
- ✅ Opt-outs preferences

### MB-17 (resuelto · ADR-036)
- ✅ UI condicional categoría B/M/A + arquetipos PYME
- ✅ feature_flags YAML-driven
- ✅ ProjectCategoryBanner + ClientCategoryBanner
- ⚠️ 4 specs MB-17 client portal authguard refactor · **NO refactorizadas
  MB-19.16** · siguen funcionales con `page.route()` mocks · cobertura UI
  preserved · refactor a `loginAsClient` real diferido SAN-E.5 (ver
  DEC-MB17-AUTHGUARD-COSECHA-DEFERRED categoría I)

### MB-18 (resuelto · ADR-040)
- ✅ AutoBillingService + ManualTransferProvider
- ✅ MilestoneFactory.create_milestones_for_contract
- ✅ RetainerStateMachine + ChurnPredictor heurístico
- ✅ Frontend admin/finance · cliente billing IBAN info

### MB-19.A (resuelto · ADR-041)
- ✅ CRM workflow comercial m13_commercial extension
- ✅ LeadService + CommercialWorkflowService
- ✅ ProposalService.generate_revision/accept/supersede
- ✅ ContractSigningFlow + FIRMA_CONTRATO purpose
- ✅ Auto-import RadarLead Celery beat
- ✅ CRM kanban API + frontend wiring

### MB-19.B (resuelto · ADR-042)
- ✅ MagicLinkPolicyEnforcer 35 purposes (33 legitimate + 2 deprecated soft)
- ✅ magic_link_migration_log table audit trail
- ✅ Migration data script ONBOARDING/APORTE_EVIDENCIA → client_tasks
- ✅ cockpit_create_user EXTENSION first_login_ttl_hours + welcome event hook
- ✅ Deprecation warnings sites legacy m05/m16

### MB-19.C (resuelto · ADR-043/044/045)
- ✅ Audit empírico 13/13 puntos visión Marcos
- ✅ ADR-043 SAN-D learnings (10 lecciones)
- ✅ ADR-044 commercial readiness checklist
- ✅ ADR-045 deploy handoff procedure
- ✅ Cosecha A · RecentActivityCard implementation (commit 89462fd · 9 tests)
- ✅ Cosecha B · LeadDetailPage /admin/pipeline/leads/[id] (commit 3d31466 · 7 tests)
- ✅ Cosecha C · E2E specs A+B + cleanup (commit 19eb08b · 5 E2E tests)
- ⚠️ Cosecha 4 specs MB-17 authguard refactor · **NO ejecutada MB-19.16**
  (DEC-MB17-AUTHGUARD-COSECHA-DEFERRED · diferida SAN-E.5)
- ⚠️ Performance audit · **baseline metodológico documentado · load test
  real NO ejecutado** (DEC-MB19C-LOAD-TEST-EJECUCION-DEFERRED · diferido
  SAN-E.4 con cliente piloto real)
- ✅ Tag final s13-fase-14-cliente-real-ready aplicado HEAD 3fe15fc
- ✅ HANDOFF_SESION_12.md (10 fases procedure detallado)

═══════════════════════════════════════════════════════════════

## SAN-E roadmap (post-cliente real piloto)

### SAN-E.1 · Auditoría compliance RGPD interna (5-8h)

**Objetivo**: FULKRO operativo full RGPD compliance para auditor externo
verificación cliente B2B.

- [ ] DPIA (Data Protection Impact Assessment) FULKRO mismo
- [ ] ROPA (Registro Operaciones Tratamiento) actualizado · 14 trámites
- [ ] DPA template (acuerdo encargado tratamiento) preparado para clientes
- [ ] Checklist GDPR art.32 medidas técnicas + organizativas
- [ ] Política privacidad publicada `/legal/privacidad` · v2 RGPD-aligned
- [ ] Cookies banner conforme directiva ePrivacy + GDPR

### SAN-E.2 · ISO 27001 readiness FULKRO mismo (15-25h)

**Objetivo**: FULKRO certificado ISO 27001 · valor diferencial vs competencia.

- [ ] Gap analysis vs Anexo A (114 controles)
- [ ] ROADMAP implementación priorizado (alta · media · baja prioridad)
- [ ] Statement of Applicability (SoA) FULKRO
- [ ] Pre-auditoría ISO interna · ready certificación
- [ ] Documentación políticas + procedimientos ISO-aligned (10+ documentos)
- [ ] Risk assessment ISO 27005 (compatible Magerit Libro II FULKRO)

### SAN-E.3 · Soberanía datos · cifrado at-rest (8-12h)

**Objetivo**: Cumplimiento soberanía datos UE · FULKRO operativo
cliente AAPP (datos reservados).

- [ ] PostgreSQL TDE (Transparent Data Encryption · pg_tde extension)
- [ ] Backup encryption-at-rest verified (pgbackrest TLS in-transit + encryption-at-rest)
- [ ] Pentesting interno básico (web + API · OWASP Top 10 baseline)
- [ ] Vulnerability scanning automated (Trivy CI/CD · Snyk dependencias)
- [ ] Hetzner Falkenstein · datos UE garantizados (verified)
- [ ] Logs transit encryption (TLS 1.3 forced)

### SAN-E.4 · Performance tuning bajo carga real (10-15h)

**Objetivo**: FULKRO operativo > 50 clientes simultáneos sin degradación UX.

- [ ] Post-baseline Sesión 19.17 audit (`docs/audit/SAN_D_PERFORMANCE.md`)
- [ ] Optimizations identificadas durante MB-19.17 aplicadas
- [ ] Bulk operations + indices avanzados Postgres
- [ ] N+1 queries detection + fix (sqlalchemy_explain · sentry trace)
- [ ] CDN edge caching estáticos frontend (Cloudflare gratis tier)
- [ ] Redis caching layer endpoints frecuentes (`/admin/dashboard` · `/projects/{id}/dashboard`)

### SAN-E.5 · Multi-cliente improvements (5-10h)

**Objetivo**: Iteración basada en feedback empírico cliente piloto.

- [ ] Feedback piloto consolidado (sprint review post-onboarding)
- [ ] UX improvements basados en uso real (heatmaps · session replays)
- [ ] Bugfixes prioridad descubiertos producción
- [ ] Documentación cliente expandida (FAQs · video tutoriales)
- [ ] Plantillas legales actualizadas (basadas en cliente real input)

═══════════════════════════════════════════════════════════════

## Deferrables consolidados ADRs 035-042 (47 entradas)

> Actualización post-MB-19.18: +2 deferrables verificación final
> (DEC-MB17-AUTHGUARD-COSECHA-DEFERRED · DEC-MB19C-LOAD-TEST-EJECUCION-DEFERRED)
> Total 47 entradas · ver Categoría I.


### Categoría A · Hard-deprecation diferida (5 entradas)

- **DEC-MB19B-HARD-DEPRECATION-410-GONE** · MB-20+ · Magic-link ONBOARDING/APORTE 410 Gone
- **DEC-MB19B-MIGRATION-CRON-AUTOMATIC** · MB-20+ · Celery automatic migration runs
- **DEC-MB18-INVOICE-RECTIFICATIVA-AUTO** · MB-19+ · existing M15 manual
- **DEC-MB18-DUNNING-AUTOMATION** · MB-19+ · escalating reminders
- **DEC-MB18-VAT-MULTI-RATE** · MB-19+ · IVA múltiples tasas

### Categoría B · Integraciones externas premium (8 entradas)

- **DEC-MB18-STRIPE-PAYMENT-GATEWAY** · MB-19+ · si volumen >€20k/mes
- **DEC-MB18-REDSYS-TPV** · MB-19+ · si cliente AAPP firma
- **DEC-MB18-TINK-OPEN-BANKING** · MB-19+ · si volumen >50 facturas/mes
- **DEC-MB18-WEBHOOKS-PAYMENT-EVENTS** · MB-19+
- **DEC-MB16-WHATSAPP-META-API** · NUNCA · contradice modelo Marcos
- **DEC-MB19B-HARD-DEPRECATION-EMAIL** · MB-20+ · email warning lifecycle
- **DEC-MB19B-MIGRATION-DASHBOARD-ADMIN** · MB-20+ · admin /migration UI
- **DEC-MB19B-PORTAL-DIRECT-LINKS** · MB-19.C · ya implementado parcial

### Categoría C · ML / IA / scoring (6 entradas)

- **DEC-MB18-CHURN-PREDICTOR-ML** · MB-19+ · cero datos training pre-piloto
- **DEC-MB19A-LEAD-SCORING-ML** · post-SAN-D
- **DEC-MB19A-PROPOSAL-AI-REGENERATE** · MB-19+ · agent_19 invocation revisions
- **DEC-MB19A-PROPOSAL-AB-TESTING** · post-SAN-D
- **DEC-MB16-NLP-INTENT-DETECTION** · post-SAN-D · classify cliente queries
- **DEC-MB17-SECTOR-AUTO-DETECTION** · post-SAN-D · ML sector classify desde nombre/CIF

### Categoría D · Multi-tenant + multi-cliente (6 entradas)

- **DEC-MB19B-MULTI-WORKSPACE-MIGRATION** · post-SAN-D · multi-workspace cliente
- **DEC-MB19A-MULTI-USER-ASSIGNMENT** · post-SAN-D · multi-consultor
- **DEC-MB18-MULTI-CURRENCY** · MB-19+ · si cliente extranjero
- **DEC-MB17-MULTI-LANGUAGE-i18n** · post-SAN-D · catalán · gallego · euskera
- **DEC-MB14-MULTI-PROJECT-CLIENT** · post-SAN-D · cliente con N projects activos simultáneos
- **DEC-MB13-MULTI-CONSULTOR-DASHBOARD** · post-SAN-D · vista cross-consultor

### Categoría E · Admin reporting + dashboards (5 entradas)

- **DEC-MB19A-CRM-DASHBOARD-ROI** · post-SAN-D · /admin/crm/conversions ROI per source
- **DEC-MB19A-INBOX-CROSS-PROJECT** · post-SAN-D · vista inbox cross-project
- **DEC-MB13-RECENT-ACTIVITY-CARD** · MB-19.16 ✅ resuelto MB-19.C
- **DEC-MB14-DASHBOARD-CHURN-FORECAST** · post-SAN-D
- **DEC-MB18-FINANCE-DASHBOARD-ADVANCED** · post-SAN-D · MRR · ARR · LTV charts

### Categoría F · Acceso externo + auditor (4 entradas)

- **DEC-MB19B-AUDITOR-EXTERNAL-INVITE-FLOW** · post-SAN-D · PRIMER_ACCESO_AUDITOR purpose
- **DEC-MB15-AUDITOR-PUBLIC-DASHBOARD** · post-SAN-D · auditor read-only metrics
- **DEC-MB14-CLIENT-AUDIT-EXPORT** · post-SAN-D · cliente exporta su audit log
- **DEC-MB12-PENTESTER-EXTERNAL-COLLAB** · post-SAN-D · multi-pentester team

### Categoría G · Seguridad + compliance avanzados (5 entradas)

- **DEC-MB19B-ROTATION-KEYS-ED25519** · post-SAN-D + ENS art.31 verificación bienal
- **DEC-MB14-ZERO-TRUST-ARCH** · post-SAN-D · zero-trust client portal
- **DEC-MB12-MFA-CLIENT-PORTAL** · post-SAN-D · TOTP cliente opcional
- **DEC-MB18-SAT-VERIFACTU-FULL** · MB-19+ · Verifactu adaptive
- **DEC-MB14-SCIM-USER-PROVISIONING** · post-SAN-D · SCIM enterprise SSO

### Categoría H · Performance + scaling (4 entradas)

- **DEC-MB13-CACHING-LAYER-REDIS** · MB-20+ · post-baseline performance
- **DEC-MB14-WEBSOCKET-CHAT-SCALE** · post-SAN-D · si concurrent chats >50
- **DEC-MB18-BILLING-BULK-INVOICES** · post-SAN-D · si >100 facturas/mes
- **DEC-MB10-RADAR-INDEX-OPTIMIZATION** · post-SAN-D · si tenders DB >100k

### Categoría I · Deferrables verificación final MB-19.C (2 entradas)

- **DEC-MB17-AUTHGUARD-COSECHA-DEFERRED** · SAN-E.5 · 4 specs MB-17 client
  portal (`mb17_arquetipo_sector_salud.spec.ts:130` + `mb17_client_portal_categoria.spec.ts:50/74/99`)
  refactor `page.route()` mocks → `loginAsClient` real auth diferido
  SAN-E.5. Razón: requiere extension `globalSetup.ts` crear projects
  fixtures con categorías diferentes BASICA/MEDIA-salud/ALTA + ClientUsers
  asociados · scope no-trivial NO encajaba MB-19.16 turbo. 4 specs siguen
  funcionales con mocks · cobertura UI preserved · 34 passed cumulative
  Playwright TODAS suites (verificación post-tag · 0 fail · 0 regresión).
- **DEC-MB19C-LOAD-TEST-EJECUCION-DEFERRED** · SAN-E.4 · load test real
  con locust/pytest-benchmark NO ejecutado MB-19.17. Solo baseline
  metodológico documentado en `docs/audit/SAN_D_PERFORMANCE.md`. Razón:
  sin datos representativos cliente real · benchmarks artificiales
  sub-estiman patrones reales (concurrencia + caching cold/warm + N+1
  queries específicas flow real). Ejecución empírica diferida SAN-E.4
  con cliente piloto operando · acceptance criteria p95<500ms / p99<1s
  validados con tráfico real. Scripts existing `backend/scripts/performance_smoke_s7.py`
  + `backend/scripts/load_test_50_retainers_billing.py` reutilizables
  como baseline starter SAN-E.4.

### Categoría J · Cosméticos + UX (2 entradas)

- **DEC-MB19A-PROPOSAL-GAMIFICATION** · NUNCA · cero alineación B2B ENS
- **DEC-MB19A-CONTRACT-SIGNING-VIDEO-IDV** · post-SAN-D · video IDV opcional

═══════════════════════════════════════════════════════════════

## Inline policy

**0 TODO/FIXME inline en código** · todo deferrable usa convención
`# Future:` con session ref (`SAN-D MB-X-DEFERRED` o `SAN-E.X-PLANNED`).

Backlog mantenido manual + ADRs · git log + tags como fuente de verdad
estado SAN-D.

═══════════════════════════════════════════════════════════════
