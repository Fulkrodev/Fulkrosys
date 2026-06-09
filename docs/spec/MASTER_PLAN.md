# FULKRO Master Plan · post-SAN-D consolidado

**Fecha**: 2026-05-07
**Status**: SAN-D CERRADO · ready primer cliente real (post-Sesión 12 deploy)
**Tag**: `s13-fase-14-cliente-real-ready` (aplicado MB-19.18)

═══════════════════════════════════════════════════════════════

## Visión

FULKRO es plataforma SaaS español de **consultoría ENS auditable ENAC** para
PYMEs · primer cliente real piloto post-Sesión 12 deploy Hetzner.

Diferenciadores vs competencia:
- **AI auditor profesional contextualizado** (Magerit Libro II + sector overlays)
- **Portal cliente workspace continuo** (NO magic-link spam)
- **Auto-billing transferencia bancaria** (NO Stripe overhead PYME)
- **Soft-deprecation policies** (compat backward sites legacy)
- **Auditable ENAC** (audit hash chain + ADRs documentados)

═══════════════════════════════════════════════════════════════

## Stats SAN-D consolidadas

### Sesiones completadas

| Sesión | Status | Mega-bloques | Tag final |
|--------|:------:|:------------:|-----------|
| SAN-A | Cerrada | A1 (categorización + reno medidas) | s10-* |
| SAN-B | Cerrada | MB-1 a MB-12 (Motors 1-12 + portal magic-links) | s11-* |
| SAN-C | Cerrada | MB-1 a MB-11.6 (workflow phase + auditoría schedules + Lucia federation + arquetipos PYME) | s12-* |
| **SAN-D** | **CERRADA** | **MB-13 a MB-19.A/B/C (9 mega-bloques)** | **s13-fase-14-cliente-real-ready** |

### Métricas SAN-D

- **9 mega-bloques** cerrados verdaderos (MB-13 a MB-19.C)
- **8 ADRs** documentados (035-042) + 3 nuevos 19.C (043 learnings · 044 commercial · 045 deploy)
- **~394 tests** SAN-D acumulados verde · 3505+ total backend
- **0 regresión** cumulative introducida
- **~36+ Playwright specs** stack real verde (post-19.16 cosechas)
- **13/13 puntos visión Marcos** cubiertos (`docs/audit/SAN_D_FINAL_AUDIT.md`)
- **45 deferrables** documentados ADRs (futuras sesiones SAN-E)

### Mega-bloques SAN-D detalle

| MB | Tag | Scope | ADR principal |
|----|-----|-------|---------------|
| MB-13 | s13-mb13-orquestador-vivo-cerrado | Sistema vivo NextActionCard + AlertService SSE event-driven | ADR-035 |
| MB-14 | s13-mb14-portal-workspace-cerrado | Portal cliente workspace + ClientTaskService + ChatService SLA <2h + 18 templates YAML | ADR-038 |
| MB-15 | s13-mb15-auditor-threat-cerrado | AI auditor A11 dry-run + Magerit Libro II catálogo + sector_salud/aapp/fintech overlays | ADR-037 |
| MB-16 | s13-mb16-omnichannel-cerrado | NotificationOrchestrator email Postmark + wa.me link DND aware + opt-outs preferences | ADR-039 |
| MB-17 | s13-mb17-ui-adaptativa-cerrada | UI condicional categoría B/M/A + arquetipos PYME · feature_flags YAML-driven | ADR-036 |
| MB-18 | s13-mb18-auto-billing-cerrado | AutoBillingService transferencia manual + RetainerStateMachine + ChurnPredictor heurístico | ADR-040 |
| MB-19.A | s13-mb19a-crm-cerrado | CRM workflow comercial m13_commercial extension + ContractSigningFlow + auto-import RadarLead Celery beat | ADR-041 |
| MB-19.B | s13-mb19b-magic-link-cerrado | MagicLinkPolicyEnforcer + magic-link migration script + cockpit_create_user extension | ADR-042 |
| MB-19.C | s13-fase-14-cliente-real-ready | Audit final 13/13 + cosechas (4 specs MB-17 + RecentActivityCard + LeadDetailPage) + ADRs 043/044/045 + tag final | ADR-043/044/045 |

═══════════════════════════════════════════════════════════════

## Arquitectura consolidada SAN-D

### Backend motores (m01-m30 + m_meetings)

- **m01_categorization** · ENS BASICA/MEDIA/ALTA categorización inicial
- **m02_magerit** · Magerit Libro II catálogo amenazas + auto-mapping per asset
- **m03_dda** · Declaración de Aplicabilidad (DdA) generación + signing
- **m04_gap** · Gap analysis vs medidas ENS
- **m05_obligations** · Library obligaciones cliente_aporta + APORTE_EVIDENCIA (deprecated soft ADR-042)
- **m06_document_factory** · Generación documentos legales (políticas · procedimientos)
- **m07_evidence** · Catálogo evidencias + freshness check Celery beat
- **m08_verification** · Verificación técnica + pentesting integration (CPSTIC ALTA)
- **m09_audit_prep** · Preparación auditoría schedules
- **m10_audit_sim** · Simulación auditoría dry-run pre-ENAC
- **m10_ens_radar** · ENS Radar leads scout + 7 niveles temperatura + workflow estado_contacto 8 estados (FASE 8.5 C2 v2)
- **m11_copiloto** · Copiloto AI consultor (sectores + arquetipos)
- **m12_magic_link** · Magic Link Engine 35 purposes + PolicyEnforcer ADR-042 + migration script (MB-19.B)
- **m13_commercial** · CRM workflow lead→cliente extension MB-19.A + LeadService + CommercialWorkflowService + ContractSigningFlow + ProposalService.generate_revision
- **m14_contracts** · Contracts engine + 7 templates legales DOCX
- **m15_billing** · Billing engine (Apéndice M v2.2 pricing) + Verifactu compliance
- **m16_onboarding** · Onboarding sessions + 3 sectores templates (deprecated soft ADR-042)
- **m17_planning** · Plan adecuación PdA generación
- **m18_communication** · Communication services + AlertService MB-13.4 + minutes_service
- **m19_risk** · Risk triggers + Magerit integration
- **m20_workspace** · Workspace project tools
- **m21_diagnosis** · Diagnosis engine
- **m21_portal_cliente** · Portal cliente auth + tasks + chat + audit + evidencias upload
- **m22_discovery** · Discovery wizard
- **m23_retainer** · Retainer contracts + state machine + churn predictor MB-18.4
- **m24_idms** · Identity Management Service (awareness)
- **m25_lifecycle** · Project Lifecycle Paso 4 + grace period 8 meses
- **m26_backup** · Backup pgbackrest + ZIP generation + DESCARGA_BACKUP magic-link
- **m27_conformity** · Conformity lifecycle + biannual audit alert (RD 311/2022 art.31)
- **m28_change_governance** · Change governance + VALIDACION_CAMBIO_ALCANCE
- **m29_client_messaging** · Client messaging + digest admin daily + cleanup attachments
- **m30_client_contacts** · Client contacts profesionales (independiente de ClientUser)
- **m_meetings** · Meeting management + post-action dispatch (propuesta · create_project · k6_signature · email_summary)

### Frontend stack

- Next.js 14.2 App Router · React Server Components
- TanStack React Query · Tailwind CSS · shadcn/ui
- @dnd-kit/core (kanban CRM MB-19.5)
- Playwright stack real (E2E loginAsMarcos + loginAsClient)
- 44+ pages generated · admin · client-portal · sign-flow magic-link

### Infraestructura

- PostgreSQL 16 + pgvector
- Redis 7 (Celery broker + result backend)
- Celery worker + beat scheduler (13 tasks daily/weekly Europe/Madrid)
- Postmark (email transactional)
- Hetzner CPX21 producción (Sesión 12 · ADR-045)

### Servicios cross-motor

- `NotificationOrchestrator` (m18 + notifications/) · email + portal SSE + DND
- `MagicLinkService` (m12) · Ed25519 JWT + OTP + geo + 35 purposes
- `MagicLinkPolicyEnforcer` (m12 · ADR-042) · 33 legitimate + 2 deprecated soft
- `LeadService` (m13_commercial · MB-19.2) · 8 estados workflow comercial
- `CommercialWorkflowService` (m13_commercial · MB-19.2) · auto-conversion lead→cliente
- `ProposalService` (m13_commercial · MB-19.3 extended) · generate_revision + supersede
- `ContractSigningFlow` (m13_commercial · MB-19.4) · OTP+geo firma legal
- `AutoBillingService` (billing · MB-18.0/2/3) · MilestoneFactory + ManualTransferProvider
- `RetainerStateMachine` + `ChurnPredictor` (retainer · MB-18.4)
- `ClientTaskService` (m21 · MB-14.3) · 18 templates YAML lifecycle pending→done

═══════════════════════════════════════════════════════════════

## Próximos pasos post-SAN-D

### Sesión 12 · Deploy Hetzner (post-tag · ANTES primer cliente real)

Procedimiento canónico ADR-045 · 10 fases · estimado 8-10h:

1. Pre-deploy local validation
2. Hetzner CPX21 provisioning
3. Software stack (Docker · Postgres 16 · Redis · nginx)
4. Domain + HTTPS Let's Encrypt
5. Variables entorno producción
6. Migrations apply (alembic upgrade head)
7. Database seed initial
8. Smoke production (10 checks)
9. Backup + monitoring
10. Handoff Marcos operativo

### SAN-E roadmap (post-cliente real piloto)

Después del primer cliente real cierro · iteración guiada por feedback:

#### SAN-E.1 · Auditoría compliance RGPD interna (5-8h)

- DPIA (Data Protection Impact Assessment) FULKRO mismo
- ROPA (Registro Operaciones Tratamiento) actualizado
- DPA template para clientes (encargado tratamiento)
- Checklist GDPR art.32 medidas técnicas + organizativas

#### SAN-E.2 · ISO 27001 readiness FULKRO mismo (15-25h)

- Gap analysis vs Anexo A (114 controles)
- ROADMAP implementación priorizado (alta · media · baja prioridad)
- Statement of Applicability (SoA) FULKRO
- Pre-auditoría ISO interna · ready certificación post-cliente

#### SAN-E.3 · Soberanía datos · cifrado at-rest (8-12h)

- PostgreSQL TDE (Transparent Data Encryption · Citus o pg_tde)
- Backup encryption-at-rest verified
- Pentesting interno básico (web + API · OWASP Top 10 baseline)
- Vulnerability scanning automated (Trivy · Snyk)

#### SAN-E.4 · Performance tuning bajo carga real (10-15h)

- Post-baseline Sesión 19.17 audit (`docs/audit/SAN_D_PERFORMANCE.md`)
- Optimizations identificadas durante MB-19.17 aplicadas
- Bulk operations + indices avanzados
- N+1 queries detection + fix (sqlalchemy_explain)

#### SAN-E.5 · Multi-cliente improvements (5-10h)

- Feedback piloto consolidado (sprint review post-onboarding)
- UX improvements basados en uso real
- Bugfixes prioridad descubiertos producción
- Documentación cliente expandida (FAQs · video tutoriales)

#### Deferrables consolidados (45 entradas) · ver ADRs 035-042

- Hard-deprecation magic-link 410 Gone (DEC-MB19B-HARD-DEPRECATION · MB-20+)
- Stripe / Redsys / Tink integrations (DEC-MB18 · MB-20+ si volumen justifica)
- A/B testing proposals (DEC-MB19A · post-SAN-D · cero datos training)
- ML scoring leads (DEC-MB19A · post-SAN-D · cero datos histórico)
- Multi-currency billing (DEC-MB18 · MB-19+ si cliente extranjero)
- WhatsApp Meta Business API (DEC-MB16 · NUNCA · contradice modelo Marcos)
- + 39 deferrables más documentados ADRs 035-042

### Tags próximos esperados

- `s14-deploy-hetzner-cerrado` (Sesión 12)
- `s15-cliente-piloto-onboarded` (Sesión 13 · primer cliente real activo)
- `s16-sane1-rgpd-interna-cerrada` (SAN-E.1)
- `s17-sane2-iso27001-ready` (SAN-E.2)
- ...

═══════════════════════════════════════════════════════════════

## Lecciones SAN-D consolidadas (ADR-043 detalle)

10 lecciones aplicables SAN-E roadmap:

1. Audit empírico per atom > tests pasando
2. Provider abstraction desde día 1
3. YAML-driven > if/else hardcoded
4. Hybrid policies > "todo o nada"
5. Atomic commits per concern · NO bulk
6. STOP intermedio reportar > ejecutar fuera scope
7. Convención idioma es decisión arquitectónica (español hispano)
8. Reuso > recreación cuando dominio existe cohesivo
9. Soft-deprecation > hard-deprecation cuando legacy activos
10. Documentación de decisiones inmediata · NO post-hoc

### Patrón iterativo SAN-E (template)

```
PER MEGA-BLOQUE SAN-E:
  1. Audit pre-impl 30 min (briefing vs realidad código)
  2. STOP intermedio si >2 discrepancias arquitectónicas
  3. Pivot vN+1 documentado en ADR + briefing v3
  4. Atom 0: ADR draft + estructura
  5. Atoms 1+: implementación con V-CHECK 11 verificaciones
  6. Cosechas in-place de deferrables compatibles scope
  7. Tests stack real Playwright + pytest backend per atom
  8. Smoke curl + tsc + npm build per atom
  9. Atom final: V-CHECK acumulado + tag intermedio + handoff next
```

═══════════════════════════════════════════════════════════════

**FIN MASTER PLAN POST-SAN-D**

Próxima actualización · post-Sesión 12 deploy + cliente real piloto
onboarded · v2.0 incorporando feedback empírico producción.
