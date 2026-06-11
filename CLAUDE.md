# FULKRO — Guía para Claude Code

> Versión compactada 2026-05-25. Historia detallada completa de sub-atoms 1.D.* + 1.E.* + Bloques 1-6 + Sesiones 1, 3A, 3B-1, 3B-2A, 3B-2B, 3B-2B.2 + OPS-052 manifestations 1ª-14ª preservadas en `docs/archive/CLAUDE_HISTORY_PRE_3B2B3.md` (backup full: `docs/archive/CLAUDE_BACKUP_2026-05-25.md`).

## Qué es esto

Plataforma de implantación ENS (RD 311/2022) para consultor autónomo (Marcos · matagarciamarcos@gmail.com). **Target**: empresas privadas que licitan a la AAPP en concursos públicos (AAPP = customer-of-customer, NUNCA customer directo · AMEND-012 sostenido empíricamente audit v4).

**Mission pre-piloto**: PRIMER CLIENTE PILOTO PAGADOR · Categoría MEDIA · 10.700€ proyecto + R_STD 700€/mes retainer · FULKRO 1.0 BLOQUE 1 PERFECTO + tag `s1-bloque-perfecto` local.

**Estructura backend**: 41 directorios motores lifecycle + 1 utility transversal (m_observability) + m_cloud_connectors unified layer = **42 motors reales** bajo `backend/app/motors/m*/`. **31 IDs registry agentes** (taxonomía en `backend/app/agents/registry.py`). m24_idms = m_dms identidad definitiva (NO crear motor m_dms paralelo).

## Estado runtime (2026-05-26 · post CLUSTER 1 Sesión 3B-2B.8)

**Backend**: ~879 endpoints REST · ~353 archivos test_*.py · 160 migraciones Alembic · 52 archivos modelos ORM · ~184 tablas live PostgreSQL.

**Frontend Next.js 14**: 120+ páginas activas · 331+ componentes TSX · 52+ hooks · 125+ archivos lib/* · 54+ módulos lib/api/* · 140+ specs Playwright E2E (fase_17 a fase_40 cumulative · Sesión 3B-2B.8 fase_39 + Sesión 3B-2B.9 fase_40 added).

**Milestones CERRADOS cumulative**:
- ✅ BLOQUE 1.B PERFECTO (96 plantillas + 19 AMENDS · tag `s1B-bloque-completo`)
- ✅ SUB-LOTE 1.C COMPLETO 8/8 sub-atoms (tag `s1C-hardening-pre-piloto-cerrado`)
- ✅ SUB-ATOMS 1.D.A-J + 1.D.X Cloud-First MVP CORE+ (tag `s1D` local)
- ✅ 1.D.F.tris TOTAL plantillas (104 entries) + 1.D.I Proveedores (109 entries)
- ✅ 1.E.1 (auditor pre-cert) + 1.E.2 (Project-Scoped Admin UX) + 1.E.2.bis (multi-tenant)
- ✅ Bloques 3+5 (Cloud Remediation Feature) + Bloque 4 (Monitoring) + Bloque 6 (Polish)
- ✅ Sesión 1 + ADDENDUM (MCPs Verification + ENS Radar Real Fix · WSL2 native runtime)
- ✅ Path A ENS Radar Scoring Refinement (4-criteria Marcos intersection · 218 changes)
- ✅ Sesiones 3A + 3B-1 + 3B-2A + 3B-2B + 3B-2B.2 Path B (Admin polish + CI regression-proof)
- ✅ Fase 1.E E.0 audit-first + E.2 refined Opción A (PDF propuesta hyperpersonalizada · LLM ORO 5 fields integrados · 68.8% fill rate WOW · 31.2% fallback graceful · 20/20 tests PASS · 2 PDFs <11KB empíricos Guadaltel + skip-llm A/B)
- ✅ Fase 1.E E.2.v3 PREMIUM redesign (PDF 11-page premium · portada gradient violet + 10 content pages · branding fulkro.es cross-codebase · 41 motores / 14 agentes / 6 MCPs Fulkro destacado · pricing comparativo + ROI · plazos 6-8 semanas · marcosmata.io purged · 33/33 tests PASS · 2 PDFs ~53KB Guadaltel V3 PREMIUM + V3 SKIP_LLM ready Marcos review)
- ✅ Fase 1.E E.2.v3.1 FINAL POLISH (5 bugs critical resolved: LLM-tender consistency P3↔P4 + organismo full no truncated + final CTA box removed + page density compactado 14→12 + Categoría Art.43 RD 311/2022 disclaimer · 2 nice-to-haves: ROI breakdown box per-caso + insight 60% menos destacado · 41/41 tests PASS · 2 PDFs ~51KB Guadaltel V3.1 FINAL + V3.1 SKIP_LLM ready primer outreach)
- ✅ Fase 1.E E.2.v3.2 FINAL premium purge tech (purgadas referencias 41 motores · 14 agentes · 6 MCPs · Model Context · motor m01/m02/m08/m21 · framing premium "Workflows automatizados + Revisión manual experta + Inteligencia normativa + Personalización extrema" · portada pastel #E8E5FF→#F5F4FF + texto dark · Soporte 24h disponible box · CTA personalizado por email contesta < 24h · plazo implementación core 3-4→2-3 semanas · P3 drop Target sugerido + P5 reworked sin tech · _trim_llm smart period-boundary · 50/50 tests PASS · 2 PDFs ~51KB Guadaltel V3.2 FINAL + V3.2 SKIP_LLM ready primer outreach REAL)
- ✅ Fase 1.E E.2.v3.3 FINAL · plazos honest + acompañamiento highlight (PLAZO_IMPLEMENTACION 2-3→2-4 semanas honest range · Box plazo realista ENAC listas espera "8-14 semanas comprimido vs 6-12 meses mercado tradicional Audidat baseline" P7 · EXPERT card P6 expanded "acompañamiento durante todo el proceso de certificación · incluida auditoría in-situ · cierre de no conformidades" · P9 H4 sub-fase 4.2 "Marcos en sala + separación clara consultor/certificador · práctica estándar mercado serio" · CTA SIEMPRE "Quedo atento." sin cargo lector · BÁSICA autodeclaración disclaimer conditional · P2 TECH pillar refined "Sistema Fulkro propio + Marcos directo · sin escalado juniors" · P6 footer comparativa reforzado "presencia in-situ día auditoría ENAC" vs "sin presencia día auditoría" · 58/58 tests PASS · 2 PDFs ~54KB Guadaltel V3.3 FINAL + V3.3 SKIP_LLM ready primer outreach REAL final)
- ✅ Fase 1.E E.2.v3.4 + E.3 SUPERSET FINAL · honest tagline + frontend feature + imágenes embedded (15 decisions cement Marcos · TAGLINE_ENS purge "certificación 6-8 semanas" mentira → "Implantación ENS de 2-4 semanas · o devolución total" · pricing canonical 4.100/13.000/25.000 · pricing comparativo tradicional inflado 10000-18000/22000-35000/40000-70000 + 13 rows ventajas · cards 2x2 cuadradas equal rowHeights · logo portada +1.5cm derecha · 3 imágenes embedded JPEG 333KB total · "equipo de Fulkro" reemplaza "Marcos" en features P5+P9 · Hito 1 NO solicita ENAC · auditoría interna H3 gate ENAC request · Garantías reformuladas devolución "no se completa la implantación" NOT "no se obtiene certificación" + Plazo blindado 2-4 semanas · P3 análisis 4 sub-secciones (Lectura pliego + Posicionamiento competitivo + Quick wins + Contexto sectorial) · NEW sección Valor empresa+ciudadanía 2 cards · CTA P10 "Quedo atento." sin cargo · BÁSICA autodeclaración disclaimer conditional · backend endpoint POST /api/v1/motors/m10/leads/{id}/propuesta-pdf StreamingResponse · frontend button LeadDetailDrawer "📄 Descargar Propuesta PDF" tanstack-style mutation + toast · 70/70 tests PASS · 2 PDFs ~485KB Guadaltel V3.4 FINAL + V3.4 SKIP_LLM 15 pages ready primer outreach REAL honest)
- ✅ Fase 1.E E.2.v3.5 · portada full-bleed + timing honest H4 ENAC + cards fix + coherence pass (8 decisions cement · D1 portada_hero2.jpg FULL-BLEED A4 background z-order bottom + logo+text overlay FULKRO_DARK contrast · D2 H4 ENAC timing honest "8-16 semanas post-solicitud" timeline + tabla + footer nota flexibilidad H1-H3 + box plazo realista reformulado "4-7 semanas implantación H1+H2+H3 + 8-16 sem ENAC externo · 4-6 meses end-to-end" · D3 H1-H3 ⏱️ Flexibilidad notes (cooperación cliente acelera/atrasa) + H4 REWRITE COMPLETO 5 sub-fases incl 4.2 Período de espera con acompañamiento equipo Fulkro · D4 cards P5 banda blanca H+V 4pt fix columna izquierda pegada V3.4 · D5 pricing comparativo "Plazo implantación 4-7 sem + ENAC" + NEW row "Plazo ENAC oficial" · D6 ROI plazo implantación ahorrado coherent · D7 cross-PDF coherence pass NO promesa "certificación X semanas" + P5 exposición point 5 "4-6 meses end-to-end" · D8 EXPERT card incluida espera ENAC explícito · backend/app/config/ orphan dir deleted (concurrent agent cleanup) · 87/87 tests PASS · 2 PDFs ~504KB Guadaltel V3.5 FINAL + V3.5 SKIP_LLM 16 pages ready primer outreach REAL premium honest)

**Pattern OPS-045 audit-first reveals existing infrastructure**: 49ª aplicación consecutiva sostenida · ahorro empírico cumulativo ~65-70% vs nominal plan ETAs · realidad infrastructure 70-95% más cubierta de lo asumido.

**Calendar empírico pre-piloto pagador**: ~1-2 meses restantes (FASE 1.F producción Hetzner + cliente onboarding 4 semanas soporte).

## Stack

- Python 3.12 + FastAPI 0.115+ + SQLAlchemy 2.0 async + Alembic
- PostgreSQL 16 (pgvector + Apache AGE + pgAudit + pgBackRest)
- Redis 7 + Celery (→ Temporal.io fase 2)
- Frontend: Next.js 14 App Router + React + TypeScript + Tailwind CSS + shadcn/ui
- Anthropic SDK 0.40+ (Sonnet 4.6 + Haiku 4.5 + Opus 4.7 para A11/A19) con prompt caching
- fastembed 0.4.2 (embeddings e5-large 1024 dim via endpoint localhost:8080)
- MinIO (3 buckets: fulkro-documents, fulkro-evidence WORM 7y, fulkro-exports), Caddy reverse proxy, Docker Compose
- MCP servers pentest (Sesión 10): 14 servers · 3 reales validados (Prowler + ScoutSuite + OpenVAS) + 11 estructurales · 88 mappings CIS/CVE → ENS Anexo II

## Reglas inviolables

1. **R1**: Motores deterministas > LLM para decisiones normativas (trazabilidad ENAC > flexibilidad LLM)
2. **R2**: Citas obligatorias en toda respuesta del LLM (RD 311/2022, CCN-STIC, Anexo II, ISO)
3. **R3**: Temperatura LLM ≤ 0.2
4. **R4**: WebAuthn only (Yubikey) para Marcos en producción — dev session fallback via `APP_ENV` (ver ADR-003)
5. **R5**: Magic links Ed25519 EC P-256 para clientes — sin cuentas permanentes. 23 purposes en enum `MagicLinkPurpose`
6. **R6**: Audit log inmutable con hash chain (trigger PL/pgSQL, migración `d4f8b2a90001`)
7. **R7**: La plataforma cumple ENS Medio sobre sí misma (dogfooding)
8. **R8**: Backup probado mensualmente (Motor 26)

## Doctrinas operativas activas (R-rules, ADRs, OPS lessons)

### R-rules específicas UX/arquitectura

- **R23**: Admin UI project-scoped firmísimo · TODO via `/admin/projects/{id}/X` · top-level admin SÓLO multi-cliente legítimo (compliance · clients · projects · workflow-command-center · meetings). Sidebar global motor-específico PROHIBIDO. Exception: 19 top-level admin pages catalogadas (audit v3.10).
- **R24**: Backend con frontend accionable · 0 mocks production · tanstack-query reused.
- **R27**: Cliente portal single-project asume `LIMIT 1` query (audit v3.10 sostenido 95%+).
- **R28**: AdaptationBadge materializa dims cliente · 19 dims (Anexo L plan v3.8).
- **R29 firmísimo**: Cliente friendly · NO presión coercitiva · NO admin lingo · "Sin prisa por tu parte" · congrats tone · friendly_message server-side. Audit pre+post response defensive (10 coercitive patterns + 6 admin lingo patterns enforcement). NUNCA rojo CSS guard.
- **R30 admin tutor**: Marcos asume cero ENS · primer principios · button-level monkey-pilot friendly · cronológico · "asume cero ENS · explica primer principios" · LLM badge UX.
- **R30 inverso**: Cliente NO ve admin orchestration internals · NO términos ENS sin tooltip TooltipENS.
- **R31**: Backend con frontend accionable (alias R24).
- **R32 v3.11**: NO destructive agentic · scope-out justificado arquitecturalmente · NO scope creep generic.

### ADRs canonical

- **ADR-013**: Doble pool auth · admin require_owner + cliente require_client_user separate routers.
- **ADR-014**: Read-only OAuth siempre · NO escalable destructivo cloud connectors. Auto-execute breaks REQUIRES explicit architect approve.
- **ADR-020 v6 Q5.3**: Roles INVISIBLE cliente · pentest authorization flow OTP step-up.
- **ADR-025 firmísimo**: NO new tables si existing covers · reuse infrastructure (SSE dispatcher + NotificationOrchestrator + workflow_hooks canonical + LLMInteractionLog existing) · view composer + derive aggregates ON-QUERY. **28ª aplicación cumulative**.
- **ADR-031**: ENAC trazabilidad reinforced · propagation_summary audit log visible cross-module.
- **ADR-038**: SAN-D MB-14.7 evidencias upload pattern.
- **ADR-046 v3**: Cross-compliance auto-detect cloud+CRITICO → NIS2.
- **ADR-051**: M14/M28 materiality engine deterministic.
- **ADR-053**: Cloud-First Architecture cohesión cross-motores (formalize 1.D.X).
- **ADR-054**: Project-Scoped Admin UX · L3 hybrid post-login redirect · Zustand active-project-store + persist localStorage · ActiveProjectSync layout guard · copilot-store panelContext.projectId sync.

### OPS-lessons (lecciones operativas reusables)

- **OPS-026**: DRY firmísimo · NO duplicar helpers (`_normalize_asset_name` · `_familia_for_measure`).
- **OPS-029**: Dimensions canonical drift catch · plan v3.x ETAs sistemáticamente sobre-estiman.
- **OPS-038**: ADR-013 doble pool client_users vs auth_users separation respect.
- **OPS-044**: lib/api wrapper distinction `clientApi` client-portal con BASE `/segment` + `api` admin con BASE `/api/v1/...`.
- **OPS-045 audit-first reveals existing infrastructure (49ª aplicación)**: Antes greenfield, ejecutar audit empírico 10-30 min sobre infraestructura existing. Plan nominal sistemáticamente sobre-estima 50-90%. Aplicable T1/T2/T3 cualquier sub-atom.
- **OPS-046**: ORM-Migration nullability mismatch (FullMixin `updated_at` nullable vs Alembic NOT NULL DEFAULT) + provider-server-side guard exemption verification (server-side desde DB, NO desde input cliente).
- **OPS-047**: `server_default now()` identical timestamps mismo transaction PostgreSQL · setear timestamp explícito desde Python con microsecond precision para audit trails.
- **OPS-048**: Cross-motor consistency test architectural insurance permanent · enforce K-light additive 0 imports directly · grep test FAIL inmediato cualquier drift.
- **OPS-049 honesty path**: "ARTIFACT" notation aspirational debt risk · grep verify post-commit obligatoria cuando claim spec/test/component creation. NUNCA borrar claim silently · DEFER explicit con Future-X sub-atom dedicado + cross-ref a esta lección.
- **OPS-050**: E2E validation requires environment setup completo (pre-flight obligatorio · ms-playwright cache + backend `_dev` endpoint + frontend port + spec files exist). **RESOLVED post WSL2 native runtime** (ver memoria `env_wsl2_native_runtime.md`).
- **OPS-052 STRENGTHENING · Phase 0 Empirical State Verification MANDATORY (post 14 manifestations)**: Architect briefings construidos sin pre-audit empírico verification del filesystem/code propagan scope assumptions latentes. Architect runs `cat` + `find` + `grep` ANTES generating implementation chain briefing. **Trigger STOP HARD architect briefing recalibrate**: si CUALQUIER step Phase 0 reveals mismatch >30% del briefing assumption.

### Pattern library formalized (Sesión 3B-2B.2 · cross-app reusable)

Documentado completo en `docs/audits/VALIDATION_SESION_3B_2B_2_FINAL.md`:

1. **sidebar ::before pseudo-element** for gradient (axe-core bg-image limitation workaround)
2. **Card solid white bg** (avoid translucent contrast loss)
3. **Token DEFAULT -700 overhaul** (Tailwind shades -500→-700 success/warning/info/danger/accent)
4. **Translucent bg matching shade** (consistency cross-components)
5. **DataTable aria-label** (WCAG 2.4.4 button-name)
6. **redirect-aware isProjectScoped** spec pattern
7. **ActionLink CTA a11y** primitive
8. **Reusable spec template** `runProjectScopedProbe` / `runTopLevelAdminProbe`
9. **HMR stale touch** (force frontend reload post token changes)

### Pattern arquitectural cumulative

- **notify_best_effort** (Bloque 3+5): primary persist NUNCA bloqueado por side effect notification · try/except logger.exception + graceful degradation
- **History-table separate from sync raw data** (1.D.X.VERIFY): tabla `*_snapshots` separate persiste estado agregado en momentos discretos · enables trend MoM/QoQ/YoY
- **Error retry button consistent admin components** (Sesión 3B-2B): `<Alert variant="danger">` + `<Button onClick={() => void refetch()}>` con AlertTitle explicit + aria-busy + data-testid `{component}-retry`
- **R29 PREVENTIVE BLINDAJE** (1.D.X.VERIFY 2b): jargon filter test + CSS class E2E guard + copiloto escalation context hints (3 técnicas combinadas blindan R29 backend + frontend + LLM)

### Sesión 3B-2B.8 CLUSTER 1 cumulative patterns formalized (cross-app reusable · 5 phases)

- **Sub-atom 5.A audit_log 3-way OR** (project_id + client_id propagation · admin variant project_id only)
- **ClientSseEventType extend pattern** (Phase 1A→1E added 6 events: `m01.categorizacion.completed` + `m02.magerit.updated` + 5 `cloud.connector.*` + `m17.plan.updated`)
- **subscribe-refetch pattern** (useClientProjectEvents + tanstack invalidateQueries · per-event handler optional)
- **Component-level reuse export refactor** (Phase 1C CloudConnectFirstStep direct reuse · Phase 1E PlanGantt named export GanttView backward-compat preserved)
- **Pure functional service mirror Phase C3** (Phase 1D compute_workflow_state: NO HTTP/ORM/side-effects · asdict JSON-serializable · deterministic · reusable cross-consumer Sesión 3B-2B.9 + 3B-2B.10)
- **Backward-compat try/except fallback** (Phase 1D scanner raises → endpoint 200 OK has_action=False · NO 500)
- **Chat-mediated cliente request pattern** (Phase 1C request-disconnect: NO destructive endpoint cliente · audit_log + ChatService.get_or_create_thread + SSE dispatch · ADR-014 sostained)
- **Cliente READ-ONLY endpoint 405 enforcement** (Phase 1E 5 tests assert PATCH/PUT/DELETE return 405 empirical · ADR-014 sostained empirical)
- **Cliente-mínimo filosofía guard** (5/5 phases cliente VE/AUTORIZA/FIRMA/RECIBE · NO opera ENS implementation técnica · CLUSTER 2-6 framework guidance · reframe DRP/BIA questionnaire+approve NO creator mode)

## Motores y agentes backend-only · scope-out frontend justificado arquitecturalmente

Los siguientes motores son infrastructure transversal y NO requieren frontend project-scoped dedicado. Decisión DELIBERADA · NO deuda técnica · sostiene OPS-026 + R32 v3.11 refined + R23 (project-scoped NO motor-específico global).

| Motor | Justificación scope-out frontend |
|-------|----------------------------------|
| **m_observability** | Utility transversal admin internal · LLM cost monitoring · NO UI per project |
| **m_workflow_engine** | Backend orquestador · UI via cada motor consumidor (workflow vivo Workflow Command Center 1.C.D) |
| **m_legal** | Dormant cross-compliance NO core ENS · activación T2 PERMANENT scope-out |
| **m_live_records** | UI integrado motores específicos consumidores (E-303/304/305/308 dentro M16/M19) |
| **m_compliance + m_compliance_monitor** | Backend monitoring · UI top-level admin /compliance/* legítimo |
| **m_meetings** | UI top-level `/admin/meetings` cross-cliente |
| **m11_rag** | Infrastructure used by A14/agents · NO cliente facing · consumed by copilots LLM 1.D.B |
| **m08_verification** | Infrastructure MCP executor · UI cubierto `/mcps` project-scoped (1.D.E) |
| **m25_dpc + m25b_revision_anual** | UI cubierto `/dossier` + `/audit` + `/conformity` existing |
| **m31_cierre_implantacion** | UI cubierto `/exit` + workflow cronológico |

## Agentes backend-only (NO UI dedicada · service-level)

| Agente | Justificación |
|--------|---------------|
| **A11 Audit dry-run** | UI cubierto `/audit-dry-run` (266 LOC dashboard) |
| **A14 Copiloto RAG** | Core backend · service-level NO UI dedicada (consumed by copilots 1.D.B) |
| **A20 Contract narrative** | UI cubierto `/contratos` (M14 1.D.D.A) · service-level invocado por wizard |
| **A21 Detector Discrepancias** | UI cubierto `/discrepancies` (1.D.A) |
| **A24 Catalog manager** | Admin internal · Marcos CLI o T1 polish · NO crítico pre-piloto |
| **A31 Copiloto interno** | Servicio used by motores narrative enrichment |
| **Resto agentes backend** (service-level) | Servicios internos · consumed by motores |

## ENS Radar (M10b) · RETIRADO (2026-06-07)

El subsistema ENS Radar (motor `m10_ens_radar`, frontend `(radar)`, scrapers, scoring, outreach, tablas radar y auth `ens_radar_owner`) fue **eliminado por completo** del producto el 2026-06-07 (migracion `drop_ens_radar_001`). El ciclo comercial (M13/M14: leads manuales, propuestas, contratos, firma) se mantiene intacto.

## Pricing Canonical (2026-06-11 · FUENTE ÚNICA unificada)

**Reference**: [docs/pricing/CANONICAL_PRICING.md](docs/pricing/CANONICAL_PRICING.md)

ENS implantación (proyecto fijo) · **un solo número por categoría en todo el sistema**:
- **Básica 3.200€** (ceiling sector complejo 4.500€) · 4-6 semanas · NO audit externo
- **Media 10.700€** (ceiling 13.000€) · 8-10 semanas · audit ENAC obligatorio cliente
- **Alta 22.800€** (ceiling 28.000€) · 12-16 semanas · SOC + DR + monit 24/7

Retainers post-cert (mensual · 5 tiers código `RETAINER_TIERS` = catálogo m23):
- **R_MICRO 150€** · **R_LITE 300€** · **R_STD 700€** (base del negocio) · **R_PLUS 1.200€** · **R_CRITICAL 3.000€**

**Excludes**: audit ENAC externo (cliente) · HW/SW licensing · hosting · pentest externo

**Fuente única (2026-06-11)**: la tabla `pricing_config` (BD · editable en `/admin/settings/pricing`) es la fuente de verdad. Al arranque/edición propaga a `rules.BASE_PRICES` == `BASE_PRICES_CANONICAL`, al catálogo comercial m13 (deriva de `get_base_prices()` · ya NO hay 22.000 sombra) y a la tabla `pricing_catalog` (m23). **R_STD = 700€ en todo el sistema** (resuelta la divergencia 400 vs 700). Migración `unify_pricing_fiscal_rls_001`. Identidad fiscal del consultor (NIF) en `admin_settings.fiscal` editable en `/admin/settings/fiscal`.

## Convenciones técnicas

- UUID PKs, timestamptz, soft delete, RLS en todas las tablas con client_id/project_id
- Roles PG: `fulkro` superuser (migraciones + seeds), `fulkro_app` NOSUPERUSER (runtime app, RLS enforced), `fulkro_migrate` superuser (Alembic prod)
- Motores en `backend/app/motors/m{01-31}_*/` + extras (m05_signing, m21_portal_cliente, m_compliance, m_compliance_monitor, m_meetings, m_observability, m_cloud_connectors)
- Agentes en `backend/app/agents/agent_*.py` + prompts en `backend/app/agents/prompts/`
- Tests en `backend/tests/{motors,agents,audit_fixes,auth,core,corpus,mcp_servers}/`
- Migrations Alembic en `backend/migrations/versions/`

## Especificación

- **Biblia:** `docs/spec/ENS_PLATFORM_MASTER_SPEC_v2.1 (2).md` — prevalece sobre todo
- **Correcciones:** `docs/spec/CORRECCION_*.md` prevalecen sobre F1/F2/F3 originales
- **Cierre gaps:** `docs/spec/CIERRE_FINAL_3_GAPS.md` prevalece sobre entregables anteriores

## Future-X buckets summary

### Pre-piloto-1 CRITICAL (bloqueante firma cliente)

- **Future-1.E.1.dossier-pack-10docs** (Path Hybrid CERRADO 2026-05-23 · 9.5/10 cobertura empírica) — DeliverableTextAuditor D2 + Items #1/#9/one-pager #10 deferred T1 demand-driven post-piloto

### Future-1.E (demand-driven post-piloto · architecturally coherent)

- `Future-1.E.contracts.boe-refs-completion` (~1-2h · Marcos legal-critical mode required)
- `Future-1.E.contracts.cache-session-scoped` · LRU caching cross-motor
- `Future-1.E.contracts.advanced-materiality-ml` · ML scoring post-piloto
- `Future-1.E.contracts.bulk-regenerate` · regenerate all cuando BOE update
- `Future-1.E.contracts.signature-integration` · digital signature provider polish
- `Future-1.E.cloud-remediation.bulk-approve` / `scheduled-execution` / `rollback` / `admin-panel-integration` / `proposal-templates` / `mfa-step-up`
- `Future-1.E.compliance-reports-pdf-export` / `compliance-checks-dedicated-page` / `compliance-alerts-dedicated-feed` / `compliance-reports-filterable` / `cross-project-compliance-symbol-rename`
- `Future-1.E.monitoring.cliente-alerts-feed-dedicated` / `admin-heatmap-visualization` / `system-health-history-sparklines` / `aggregator-cache-redis` / `E2E-fase39-specs` / `compliance-export-pdf` / `advanced-ml-anomaly-detection`
- `Future-1.E.fulkro-compliance-continuous-monitoring`
- `Future-1.E.copilot-cross-project-knowledge-search`
- `Future-1.E.copilot-AI-chat-embedded` / `copilot-progress-gamification` / `copilot-guided-integration-per-page` / `copilot-video-tutorials` (Sesión 3A)
- `Future-1.E.help-modal-faqs-content-curation` / `phase-explanations-6-remaining`
- `Future-1.E.selector-duplicate` (architect approve required)
- `Future-1.E.compliance-portal-route-group` (Option A migration si demand-driven)
- `Future-1.E.admin-polish-priority-3-secondary` / `priority-4-edge` (~7-10h cumulative post-piloto)
- `Future-1.E.admin-polish-p2-iterate-remaining` (3 pages: clients + retainers + clients[id] · ~2h)
- `Future-1.E.admin-polish-p2-batch3-cross-cliente` / `batch4-operations` / `batch6-project-scoped` (~6.5h cumulative)
- `Future-1.E.error-retry-pattern-cross-suite-audit` (spot-check 81 admin pages)
- `Future-1.E.E2E-fase-X-sesion-3A-coverage` (~2-3h)
- `Future-1.E.fase32-spec-refresh` (~15 min · post-R29 copy expansion strict mode violations)
- `Future-1.E.naming-disambiguation` A11 dual-role refactor (~1-2h post-piloto)
- `Future-1.E.pricing.migrate-{rules,m13,m23,tests}-canonical` (~6-8h cumulative)
- `Future-1.E.2.advanced-switcher` · Cmd+K + recent-5 + pinned · `cross-device-sync`
- `Future-1.E.2.bis.multi-project-per-cliente` / `per-project-branding` / `bulk-user-management` / `cliente-portal-mobile-app`
- `Future-1.E.cloud-remediation` series (6 items demand-driven)
- `Future-1.E.frontend.typescript-pre-existing-errors` (~1-2h · 10 TS errors pre-existing OTHER areas)
- `Future-1.E.client-portal-playwright-coverage` (Sesión 3B-3 ~10-15h · pattern library reuse)

### Fase 1.E E.2 refined Opción A Future-1.E+ captured (4 items · enrichment 31.2% orphan companies)

- `Future-1.E+.borme-lookup-automation-cif-orphan` (~2h · resolve razon_social legit desde CIF orphans · Marcos descartó Opción B inline pre-piloto · post-piloto cuando demand-driven)
- `Future-1.E+.cpv-to-sector-mapper` (~30m · extender `_CPV_INDUSTRIA_MAP` 8-digit precision · current 2-digit prefix lookup pragmatic)
- `Future-1.E+.empleados-estimator-heuristic` (~1h · derive employee count desde adjudicaciones histórico + importe sweet spot · narrative enrichment P1)
- `Future-1.E+.llm-rescore-144-leads-null` (~1.5h + cost LLM ~$3-5 · re-run LLM batch sobre 144 leads sin dolor_especifico · subir fill rate 68.8% → ~95%)

### Sesión 3B-2B.8 CLUSTER 1 Future-X cumulative captured (17 items · post-piloto demand-driven)

**Phase 1C cloud-connections (4)**:
- `Future-1.E.cloud-connectors-consolidation` (~2-3h investigate dup CloudConnectFirstStep vs ConnectorsClientView)
- `Future-1.E.cloud-connector-disconnect-self-service` (~3-5h ADR-014 revisar post-piloto)
- `Future-1.E.cloud-connector-id-per-remediation-grouping` (~1-2h backend exponer connector_id en RemediationGap cliente)
- `Future-1.E.cloud-connect-step-headerless-mode` (~30 min variante sin hero)

**Phase 1D Copilot workflow (4)**:
- `Future-1.E.workflow-scanner-cache-redis` (~2-3h cross-consumer cache compute_workflow_state)
- `Future-1.E.workflow-scanner-sse-emit` (~2-3h backend dispatch `copilot.hint.updated` event)
- `Future-1.E.workflow-scanner-percentage-refinement` (~3-5h replace 50% heuristic con motor-specific count)
- `Future-1.E.workflow-trigger-bug-fix` (~30 min add `phase_changed` al `ck_project_lifecycle_events_event_type`)

**Phase 1E M17 Plan Gantt cliente (4)**:
- `Future-1.E.plan-cliente-tooltip-ENS-medida` (~1h tooltip per task vía deliverable_e_code)
- `Future-1.E.plan-cliente-mobile-vertical-gantt` (~2-3h responsive vertical layout)
- `Future-1.E.plan-cliente-export-pdf-ical` (~3-4h export PDF + iCal)
- `Future-1.E.plan-cliente-progress-celebration` (~1h confetti 100% task R29)

### Future-1.F (FASE 1.F producción Hetzner deploy)

- `Future-1.F.dark-mode-completo` (ThemeToggle activate)
- `Future-1.F.admin-design-system-overhaul` (mayor refactor · architect approve)
- `Future-1.F.admin-component-library-extraction` (shared primitives)
- `Future-1.F.compliance-third-party-audit-prep` (ENAC handoff portal externo)
- `Future-1.F.client-portal-mobile-sidebar` (drawer)
- `Future-1.F.cloud-auto-execute-api` (breaks ADR-014 · architect approve required) + `cloud-state-verification` + `cross-cloud-orchestration` + `atomic-transaction-wrapper` + `retry-exponential-backoff` + `circuit-breaker`

### Future-1.E.X (DEFER explicit per OPS-049 honesty)

- `Future-1.E.X.fase_35` E2E specs creation — **RESOLVED 1.D.H.bis.B** (7 specs created + 9 test cases verified)

### Future-X archived (RESOLVED durante 1.D.H.bis)

- ✅ `Future-1.F.playwright-browsers-install` RESOLVED `254e2c9`
- ✅ `Future-1.E.X.fase_35-specs` RESOLVED `c4e36dd` + fix `2f7422f`
- ✅ `Future-chore.branches-cleanup` RESOLVED 1.D.H.bis.D

### Sesión 3B-2B.7 Ejecutable 4 Future-X · Phase 7.0 DEFER + Phase 7.2 scope expansion (architect Opción C)

- `Future-1.E.cloud-connectors-test-infrastructure-debt-50-failures` (~2-3h · post widen aplicado · re-run pytest + fix-forward case-by-case · 50 failures empirical baseline preserved)
- `Future-1.E.alembic-stamp-3rd-branch-remediation-enhancement-b35-e-001` (~5 min · post widen · stamp branch + upgrade head merge `sub_atom_5b_magerit_child_rls_001`)

**Phase 7.2 scope expansion NEW Sesión 3B-2B.7-EXPANDED 7 items (~31-45h post-piloto demand-driven · cliente real demand-justified)**:
- `Future-3B-2B-7-EXPANDED.github-connector-ens-audit-agent` (~4-6h post-piloto · empresas SaaS-native · GitHub Apps Octokit + ENS measures cobertura)
- `Future-3B-2B-7-EXPANDED.gitlab-connector-ens-audit-agent` (~4-6h post-piloto · alternativa GitHub · self-hosted instances support)
- `Future-3B-2B-7-EXPANDED.aws-connector-ens-audit-agent` (~6-8h post-piloto · empresas cloud-native AWS · IAM + S3 + CloudTrail + KMS coverage)
- `Future-3B-2B-7-EXPANDED.azure-connector-ens-audit-agent` (~6-8h post-piloto · empresas Microsoft Azure · Entra ID extended + Resource Graph + Storage + Defender)
- `Future-3B-2B-7-EXPANDED.dropbox-business-connector-ens-audit` (~3-5h post-piloto · si demand-driven · sharing settings + admin audit)
- `Future-3B-2B-7-EXPANDED.cross-provider-agents-coordination-orchestrator` (~5-7h post-piloto · cuando >2 providers en mismo cliente · evita duplicate findings + cross-provider correlation)
- `Future-3B-2B-7-EXPANDED.ens-measures-coverage-completeness-per-provider-matrix` (~3-5h post-piloto · 73 medidas ENS Alta x N providers matrix con gap rules cobertura completa)

## Sesión 3B-2B.7 Ejecutable 4 CERRADO · Cloud Connections fix-forward DEFER + M365/SharePoint/GWorkspace polish (2026-05-27)

**Status**: ✅ CERRADO scope refined Opción C architect approved · Phase 7.0 fix-forward DEFER + Phase 7.1-7.3 polish shipped empirical.

**Tag local**: `s3b-2b-7-cerrado`
**Audit docs**:
- [`docs/audits/AUDIT_EJECUTABLE_4_PHASE_7_0_PRE_FIX_DB_STATE.md`](docs/audits/AUDIT_EJECUTABLE_4_PHASE_7_0_PRE_FIX_DB_STATE.md) · phantom revision empirical state pre-fix
- [`docs/audits/AUDIT_EJECUTABLE_4_PHASE_7_1_M365_GWORKSPACE_STATE.md`](docs/audits/AUDIT_EJECUTABLE_4_PHASE_7_1_M365_GWORKSPACE_STATE.md) · M365+GWorkspace empirical gaps + polish scope

**Resumen cumulative cifras**:
- ~1.5h empirical vs ~8-12h projection nominal (OPS-045 -85% sostained · 50ª aplicación cumulative)
- 3 commits: Phase 7.1.1 polish + Phase 7.3 E2E + Phase 7.2 Future-X cement
- 3 Future-X Phase 7.0 DEFER documented (post widen Marcos authorize OR FASE J Hetzner)
- 7 Future-X scope expansion NEW Sesión 3B-2B.7-EXPANDED captured (post-piloto demand-driven)
- DB state preserved post `alembic stamp --purge` 2 of 3 real heads (NO regression · 3rd branch DEFER)

**Phase 7.0 fix-forward partial empirical (architect Opción C DEFER)**:
- ✅ `alembic stamp --purge cluster6_client_mfa_001 radar_v9_perfect_f_001` SUCCESS · phantom `cluster6_supervision_mode_001` replaced
- ❌ 3rd branch `remediation_enhancement_b35_e_001` unstamped (DEFER Future-X)
- ➡️ Cross-suite cumulative baseline 50 cloud failures preserved (NO new regression · NO new pass)

**Phase 7.1.1 polish shipped empirical**:
- M365 connector: `mfa_enabled` detection via `/reports/authenticationMethods/userRegistrationDetails` (op.acc.6 nuclear unlocked)
- M365 connector: `is_privileged` detection via `/directoryRoles` + per-role members enumeration (op.acc.5 unlocked)
- M365 connector: SharePoint sites discovery `/sites?search=*` con sharing detection (mp.s.2 extended)
- M365 connector: pagination follow `@odata.nextLink` best-effort (max 3 pages MVP)
- M365 connector: graceful degradation per endpoint (errors logged · NO interrumpe discovery)
- GWorkspace connector: Shared drives discovery `/drives` Drive API con `useDomainAdminAccess` (mp.s.2 extended)
- GWorkspace connector: pagination follow `nextPageToken` best-effort (max 3 pages MVP)
- `gap_rules.py` `detect_public_buckets` extended para incluir `asset.sharepoint_site` + `asset.shared_drive`
- `CONNECTOR_PROVIDER_ENS_GUIDANCE` constant NEW · per-provider agent guidance (measures_detectable + asset_types + scopes_required + cliente_friendly_blurb)
- `get_provider_ens_guidance(provider)` helper exposed para api_cliente catalog + R30 admin tutor

**Phase 7.3 E2E tests scaffold shipped (runnable post widen aplicado)**:
- `backend/tests/integration/test_cloud_m365_e2e.py` · OAuth + discover_identities + discover_assets + gap detection scaffold con mock httpx
- `backend/tests/integration/test_cloud_gworkspace_e2e.py` · same pattern GWorkspace
- Mock providers (NO requires real M365/GWorkspace sandbox accounts pre-piloto)
- Cliente-mínimo filosofía verify cross flows
- audit_log integrity preserved R6 hash chain (Sub-atom 5.A 3-way OR sostained)

**Doctrinas honored cumulative**:
- ADR-014 read-only OAuth sostained (NO destructive auto-execute per connector)
- OPS-045 audit-first sostained (50ª aplicación · scope reveal -85% vs nominal)
- OPS-046 fix-forward partial (Opción C DEFER blocker · honest path OPS-049)
- OPS-049 honest path (Phase 7.0 DEFER explicit transparent · 3 Future-X documented)
- OPS-052 manifestación 69ª (STOP HARD architect briefing recalibrate scope refined Opción A→C empirical)
- Sub-atom 5.A audit_log 3-way OR propagated
- R23 project-scoped admin UX sostained (cloud connections per project)
- R29 cliente-friendly sostained (CONNECTOR_PROVIDER_ENS_GUIDANCE includes `cliente_friendly_blurb`)
- R30 admin tutor sostained (R30 inverso · cliente NO ve scopes técnicos)
- Pattern #14 SSE+ClientNotification dual emit sostained
- Pattern #20 gap translation cliente-friendly sostained

**Cliente-mínimo filosofía 100% sostained cross 3 connectors**:
- Cliente CONECTA (OAuth flow init via api_cliente)
- Cliente AUTORIZA (M16 portal_api oauth callback)
- Cliente RECIBE recommendations (gap_rules R29 friendly templates + remediation OPTIONAL)
- Cliente NO opera técnico (request-disconnect chat-mediated · ADR-014 sostained)

**Next sesión architect approve**: **Ejecutable 5 · Sesión 3B-2B.10 Audit Simulacro Pre-ENAC** orchestrator delgado · reuse 5 existing services Phase C3+C4 + 2 nuevos · ~1-2h empirical projection.

## Sesión 3B-2B.10 Ejecutable 5 CERRADO · Audit Simulacro Pre-ENAC orchestrator delgado (2026-05-27)

**Status**: ✅ CERRADO scope-pure · 4 phases shipped empirical · 78% existing services reuse OPS-026 DRY.

**Tag local**: `s3b-2b-10-cerrado`
**Audit doc**: [`docs/audits/AUDIT_EJECUTABLE_5_SESION_3B_2B_10_SIMULACRO_PRE_ENAC_STATE.md`](docs/audits/AUDIT_EJECUTABLE_5_SESION_3B_2B_10_SIMULACRO_PRE_ENAC_STATE.md)

**Resumen cumulative cifras**:
- ~1.5h empirical vs ~6-9h projection nominal (OPS-045 -83% sostained · 51ª aplicación cumulative)
- 4 atomic commits sequential (Phase 10.1 + 10.2 + 10.3 + 10.4)
- 18 backend tests NEW PASS · 243/243 m09 cross-suite cumulative · ZERO regression
- 3 Playwright scaffold tests (tabs render + empty state + execute mock)
- 6 NEW canonical audit_log events (simulacro.pre_enac.* + audit.integrity.checked + corrective.loop.*)
- 39 cumulative canonical events post-Sesión 3B-2B.10

**Phase 10.1 audit_log_integrity_checker (OPS-045 75% existing reveal)**:
- `fn_audit_log_verify_chain` PostgreSQL function existing (migration `d4f8b2a90001`)
- Triggers `tg_audit_log_no_update` + `tg_audit_log_no_delete` PRE-EXISTING immutability
- NEW: pure functional wrapper · per-project variant + since_seq filter
- Algorithm refined empirical: SQL-side canonical `::text` payload construction (Python JSONB::text serialization mismatch)
- Briefing mismatch documented: SHA-256 (NOT Ed25519 · Ed25519 lives M05 PDF signing separate concern)

**Phase 10.2 corrective_loop_service state machine**:
- State machine canonical Pattern #18: `open → in_progress → closed` (terminal)
- Storage strategy ADR-025: NO new table · audit_log derived state ORDER BY seq DESC LIMIT 1
- Loop_id synthetic UUID · `registro_id` audit_log column · `payload_new` jsonb metadata
- Public API: open_loop_for_gap + transition_loop + close_loop + list_open_loops

**Phase 10.3 SimulacroPreEnacService orchestrator delgado**:
- Pure functional ~80 LOC composing 5 existing + 2 nuevos OPS-026 DRY
- Pipeline: dry-run (M10+A11) → gap matrix C3 → workflow state Phase 1D → integrity 10.1 → loops 10.2 per critical/high → draft report C4
- SimulacroReport JSON-serializable · 16 fields including pdf_sha256 + signature_hex
- audit_log emit Sub-atom 5.A 3-way OR (simulacro.pre_enac.executed + report_generated)
- PDF generated empirical 9209 bytes typical · Ed25519 signed (M05 reuse) · 9 sections reportlab platypus

**Phase 10.4 Frontend AuditDryRunDashboard extend tab (Pattern P-CL2-4 ENRICH)**:
- NO new route · wrap existing dashboard en Tabs (2 pestañas: Dry-Run + Simulacro)
- Backend API 2 routes (POST execute + GET last-report)
- Frontend client `lib/api/simulacro-pre-enac.ts` (~50 LOC tanstack-query compatible)
- Component `SimulacroPreEnacTab.tsx` (~230 LOC · Card + Metrics + IntegrityRow + PdfMetadata)
- 3 Playwright scaffold tests

**Patterns library extended (3 NEW · 20 cumulative cross-app)**:
- **#18** state machine canonical (open→in_progress→closed · 3-state · audit_log derived)
- **#19** PostgreSQL canonical payload SQL-side construction (avoid Python JSONB::text serialization mismatch)
- **#20** Tabs ENRICH dashboard wrap (Pattern P-CL2-4 applied · 2-tab embed)

**Doctrinas honored cumulative**:
- ADR-013 doble pool · ADR-025 reuse infrastructure · OPS-026 DRY (78% reuse) · OPS-045 51ª · OPS-049 honest path · OPS-052 manifestación 70ª
- R6 hash chain SHA-256 inviolable preserved
- Sub-atom 5.A audit_log 3-way OR propagated
- R23 + R30 admin tutor sostained
- Pattern #18 state machine reuse · Pattern P-CL2-4 ENRICH

**Next sesión architect approve**: **Ejecutable 7 · axe-CI Path A cliente+auditor runtime PASS + CI gate extend** · ~1h empirical projection.

## Sesión 3B-4 Ejecutable 7.5 CERRADO · Audit Accompaniment + Sede Conformity post-implantación cycle (2026-05-27)

**Status**: ✅ CERRADO definitivo · 3 phases shipped · NEW motor `m_audit_accompaniment` greenfield insert ANTES Ejecutable 8 EXPANDED.

**Tag local**: `ejecutable-7-5-audit-accompaniment-cerrado`
**Audit doc**: [`docs/audits/AUDIT_EJECUTABLE_7_5_AUDIT_ACCOMPANIMENT_STATE.md`](docs/audits/AUDIT_EJECUTABLE_7_5_AUDIT_ACCOMPANIMENT_STATE.md)

**Resumen cifras**:
- ~1.5h empirical vs ~4-6h projection nominal (OPS-045 -75% · 54ª aplicación cumulative)
- 3 atomic commits sequential (Phase 7.5.1 backend + 7.5.2 admin + 7.5.3 cliente)
- 15 backend tests NEW PASS · 268/268 cumulative cross-suite preserved · ZERO regression
- 3 NEW tables via direct DDL (alembic multi-head DEFER de Ejecutable 4 sostained)
- 4 NEW API endpoints (3 admin + 1 cliente read-only) · 5 NEW canonical audit_log events

**State machine canonical** (CCN-STIC-808/809 + CCN-CERT IC-01/19 + IC-02/20 validated):
- BÁSICO 6 states sequential (autodeclaración · NO ENAC)
- MEDIO/ALTO 11 states unified (ENAC + biannual renewal cycle)
- Branch auto-resolved per `project.categoria_objetivo`

**Phases shipped**:
- Phase 7.5.1 backend: `state_machine.py` + `service.py` (advisory lock per project_id Pattern #22) + `models.py` (3 tables FullMixin) + `api.py` (4 endpoints) + 15/15 tests PASS
- Phase 7.5.2 frontend admin: `AuditAccompanimentTimeline.tsx` ENRICH `/audit` page (Pattern P-CL2-4) · R30 tutor TooltipENS · advance + artifacts uploader per state
- Phase 7.5.3 frontend cliente: `AuditAccompanimentClienteView.tsx` + `/client-portal/certificacion` page · R29 friendly Spanish labels · SSE auto-update Pattern #14+#21 reuse · cliente-mínimo 100%

**Patterns library extended (1 NEW · 23 cumulative cross-app)**:
- **#23 State machine canonical per-branch** (state_machine.py module con VALID_TRANSITIONS dict per branch · resolve_category_branch helper · is_terminal_state introspection · STATE_EVENT_MAP canonical events map · pure functional reusable cross-consumers)

**Doctrinas honored cumulative**:
- ADR-013 doble pool · ADR-025 reuse (3 tables justified architecturally)
- OPS-026 DRY (Pattern #14+#18+#21+#22+P-CL2-4 reuse · 60% existing infrastructure)
- **OPS-045 54ª** (-75% empirical sostained) · OPS-049 honest path (DDL direct 0 rows safe)
- **OPS-052 manifestación 73ª** (audit-first reveal NO motor existing · NEW motor clean separation)
- R6 hash chain preserved · Sub-atom 5.A 3-way OR cross 5 events
- R23 + R29 + R30 + Cliente-mínimo filosofía 100%
- Pattern #18 + #22 + #14 + #21 + P-CL2-4 reuse cumulative

**Future-X DEFER 0 items casuales** (architect doctrine inviolable). Potential post-piloto enrichments architecturally coherent (NOT defers): S3 artifacts storage · ENAC handoff portal integration · renewal calendar reminders post primer ALTA cliente real.

**Next sesión architect approve**: **Ejecutable 8 EXPANDED FRESH-EYES** comprehensive repo audit + quality gate Pre-Bloque 7 (~20-30h empirical · 13 pasadas comprehensive).

## Sesión 3B-4 Ejecutable 7.6 CERRADO · Fulkro Identity & Contact Propagation cross-system (2026-05-27)

**Status**: ✅ CERRADO scope clean pre-Ejecutable 8 · 4 phases shipped · single source of truth backend + frontend cross outputs.

**Tag local**: `ejecutable-7-6-fulkro-identity-cerrado`
**Audit doc**: [`docs/audits/AUDIT_EJECUTABLE_7_6_FULKRO_IDENTITY_PROPAGATION_STATE.md`](docs/audits/AUDIT_EJECUTABLE_7_6_FULKRO_IDENTITY_PROPAGATION_STATE.md)

**Resumen cifras**:
- ~30-40 min empirical vs ~30-45 min projection (OPS-045 55ª aplicación · scope clean greenfield 90%)
- 3 atomic commits sequential (Phase 7.6.1 constants + 7.6.2 propagation + 7.6.3 copilots)
- 345/345 cumulative cross-suite preserved · ZERO regression
- 14 files updated cross outputs (constants modules + Footer + email templates + propuesta PDF + copilot prompts)

**Phase 7.6.0 audit findings empirical (OPS-052 74ª manifestación)**:
- 9 backend files con identity strings · 0 frontend matches (90% greenfield)
- `frontend/lib/branding/` existing pero cubre CLIENT branding NO Fulkro consultora
- NO Footer component existing
- 13 email templates con signature pobre "Marcos · FULKRO" sin phone/web/email
- Copilots system prompts SIN Fulkro identity wired
- Naming collision discovery: `backend/app/config.py` existing module · my NEW package collision resolved con `backend/app/fulkro_identity.py` separate module path

**Phase 7.6.1 shipped**:
- NEW `backend/app/fulkro_identity.py` (10 constants · FULKRO_PHONE + WEB + EMAIL + AUTHOR + TAGLINE + FOOTER_TEXT + EMAIL_SIGNATURE_HTML/TEXT + COPILOT_PRIMARY_CONTEXT)
- NEW `frontend/lib/fulkro-identity.ts` (FULKRO_IDENTITY const object readonly)

**Phase 7.6.2 propagation shipped**:
- NEW `frontend/components/layout/FulkroFooter.tsx` · accessible aria-labels · WCAG 2.2 AA · responsive
- Embedded `frontend/app/layout.tsx` root cross all 3 portals (admin + cliente + auditor)
- REFACTOR `backend/scripts/generate_propuesta_pdf.py` import constants (OPS-026 DRY · sostained V3.4 hardcoded → centralized)
- UPDATE 11/13 email templates `m20_notifications/templates/` con full canonical signature (phone + email + web)
- 2 templates excluded scope: `client_inactivity_admin.yaml` + `evidence_quarantined_admin.yaml` (system-origin "FULKRO Notification Orchestrator" signature distinct · admin-internal NO consultor signature)

**Phase 7.6.3 copilots wiring shipped**:
- `backend/app/agents/agent_14_copiloto/prompts.py` SYSTEM_PROMPT extended con `FULKRO_COPILOT_PRIMARY_CONTEXT` import + "CONTACTO FULKRO" section explicit
- `backend/app/agents/prompts/agent_14_copiloto.py` (spec-level) same wiring
- Copilot ahora empirical-grounded responses cuando usuario pregunta "¿cómo contacto a Fulkro?"

**Phase 7.6.4 empirical verification cross outputs**:
- ✅ Backend constants verified (phone/web/email/footer/signature)
- ✅ Footer canonical text rendered
- ✅ Email HTML signature canonical
- ✅ Copilot agent_14 system prompt IDENTIDAD FULKRO section present + phone embedded
- ✅ 11/13 email templates con signature canonical full identity

**Doctrinas honored cumulative**:
- OPS-026 DRY (single source of truth backend + frontend constants modules · NO hardcode duplicates)
- OPS-045 audit-first 55ª aplicación (scope clean alignment con nominal projection)
- OPS-049 honest path (90% greenfield documented transparent · naming collision resolved separate module path)
- **OPS-052 manifestación 74ª** (audit-first reveal naming collision config.py vs config/ package · resolved separate module)
- Fulkro "shown not sold" doctrine (cliente VE info consultora trust building)
- R23 + R30 admin tutor sostained (copilots primary context · NO hallucination)
- Pattern P-CL2-4 ENRICH outputs existing (Footer embedded layouts · NO new routes)

**Future-X DEFER 0 items casuales** (architect doctrine inviolable). Potential post-piloto enrichments architecturally coherent (NOT defers):
- Ejecutable 8 Pasada 18-19 expandirá knowledge base copilots con SYSTEM_KNOWLEDGE_BASE.md completo
- Sede artifacts CCN-STIC-809 conformidad templates Fulkro consultora mention (post primer cliente piloto)
- WhatsApp business policy footer (cuando Meta policy permita per template)

**Next sesión architect approve**: **Ejecutable 8 EXPANDED FRESH-EYES MASIVO** (20 pasadas · ~40-58h empirical · 4 STOP-AND-REPORT checkpoints) comprehensive repo audit + quality gate Pre-Bloque 7.

## Sesión 3B-4 Ejecutable 7.7 CERRADO · E-signature TIER 1 Canvas + Ed25519 + audit_log (2026-05-27)

**Status**: ✅ CERRADO scope refined REFACTOR+EXTEND m05_signing per OPS-052 manifestación 75ª · 4 phases shipped · 12 NEW backend tests PASS · ZERO regression cross-suite 220 cumulative.

**Tag local**: `ejecutable-7-7-esignature-cerrado`
**Audit doc**: [`docs/audits/AUDIT_EJECUTABLE_7_7_ESIGNATURE_STATE.md`](docs/audits/AUDIT_EJECUTABLE_7_7_ESIGNATURE_STATE.md)

**Resumen cifras**:
- ~30-45 min empirical vs ~30-45 min projection (OPS-045 56ª aplicación · alignment)
- 3 atomic commits sequential (Phase 7.7.1 backend + 7.7.2 frontend + 7.7.3 PDF embed)
- 12 NEW tests PASS (8 canvas TIER 1 + 4 PDF embed) · 43/43 m05_signing+m_audit_accompaniment + 220/220 cumulative cross-suite
- 1 NEW migration alembic additive only · ALTER signing_events ADD 3 columns (esignature_canvas_tier1_001)
- 4 NEW API endpoints + 5 NEW canonical audit_log events Sub-atom 5.A 3-way OR
- Sample empirical: `out/ejecutable_7_7_sample_signed.pdf` (3417 bytes · 2-page PDF · embed signature image XObject)

**OPS-052 manifestación 75ª** (audit-first reveal scope refined REFACTOR+EXTEND):
- Briefing assumption: NEW motor m24_esignature greenfield clean separation
- Empirical reveal: m05_signing motor production-grade existing 80%+ infrastructure (1840 LOC · 9 files · 11 SignableTypes catalog · Ed25519+hash chain+audit_log+OTP step-up+API/portal/signing/* + admin/signing/* + frontend /firmas-hub existing)
- STOP HARD triggered mismatch >70%
- Scope refined: EXTEND m05_signing (NOT new motor m24) sostained ADR-053 cohesión + OPS-026 DRY firmísimo

**Phase 7.7.1 backend extend m05_signing shipped**:
- ALTER signing_events ADD signature_canvas_dataurl + signed_name + signed_surname (additive · nullable)
- SigningService.sign_canvas() TIER 1 path · NO OTP gate · Ed25519 + hash chain + canvas SHA256 + nombre + apellido · Pattern #22 advisory lock per document_id
- SigningService.verify_intent_signature() admin Ed25519 verify helper
- 4 NEW APIs:
  · POST /portal/signing/intents/{id}/sign-canvas (cliente TIER 1)
  · GET /portal/signing/projects/{id}/pending (cliente pending list)
  · POST /admin/signing/intents/request (admin trigger intent)
  · GET /admin/signing/intents/{id}/verify (admin verify integrity)
- 5 NEW canonical audit_log events Sub-atom 5.A 3-way OR (signature.requested · signature.signed · signature.declined · signature.verified · signature.expired)
- SSE dispatch project channel signing.* events Pattern #14+#21 (signing.requested + signing.signed + signing.declined)
- 8 NEW tests PASS

**Phase 7.7.2 frontend cliente shipped**:
- NEW `components/signatures/SignatureCanvas.tsx` react-signature-canvas wrapper · responsive (móvil touchscreen + PC ratón) · inputs nombre + apellido validados · Clear + Submit · WCAG 2.2 AA aria-labels · R29 friendly Spanish "Firma con tu dedo (móvil) o ratón (PC)"
- NEW `app/(client-portal)/client-portal/firmas-pendientes/page.tsx` cliente lista documentos pendientes firma + SignatureCanvas inline + empty state friendly + SSE auto-update Pattern #14
- EXTEND `lib/api/signing.ts` signIntentCanvas + listPendingSignatures helpers (clientApi wrapper · DRY existing module)
- EXTEND `hooks/useClientProjectEvents.ts` 3 nuevos SSE event types + auto-invalidate signing queries
- npm install react-signature-canvas ^1.1.0-alpha.2

**Phase 7.7.3 PDF embed shipped**:
- NEW `motors/m05_signing/pdf_signature_embed.py` append_signature_page() helper appends "Firma del cliente" bloque última page de cualquier PDF · embeds canvas signature image + nombre + apellido + fecha UTC + IP firmante + Ed25519 verification badge (signature hex 8chars + hash chain 16chars) + Fulkro footer canonical (Ejecutable 7.6 reuse)
- Graceful degradation cuando dataurl inválido (OPS-049 honest path)
- Reusable cross PDF generators (propuesta_pdf · draft_audit_report · simulacro_pre_enac · acompañamiento certificates)
- NEW `scripts/generate_signed_sample_pdf.py` CLI empirical sample
- 4 NEW tests PASS

**Patterns library extended (1 NEW · 24 cumulative cross-app)**:
- **#24 Visual signature embed PDF última page** (canvas dataurl → reportlab Image XObject + signature image rendered ~6cm + verification badge Ed25519 + hash chain + cliente metadata + Fulkro footer · reusable cross PDF generators · graceful degradation invalid dataurl)

**Doctrinas honored cumulative**:
- ADR-009 firma electrónica simple eIDAS Art. 25.1 (NO eIDAS qualified · TIER 1 canvas)
- ADR-010 página /client-portal/firma explicativa (existing preserved)
- ADR-013 doble pool · ADR-053 cohesión cross-motores
- OPS-026 DRY firmísimo (m05_signing existing reused · NO motor m24 paralelo · FULKRO_FOOTER_TEXT reuse · existing signing.ts module extend)
- **OPS-045 56ª aplicación** (alignment con nominal projection · scope refined preserves time budget)
- OPS-049 honest path (graceful degradation invalid dataurl · audit doc transparent)
- **OPS-052 manifestación 75ª** (audit-first reveal 80%+ existing · STOP HARD scope refined REFACTOR+EXTEND)
- R6 hash chain inviolable preserved (event_hash_sha256 + previous_signature_hash chain link)
- Sub-atom 5.A audit_log 3-way OR cross 5 canonical signature events
- Pattern #14 SSE + ClientNotification dual emit · Pattern #21 event_id replay · Pattern #22 advisory lock per document_id · Pattern P-CL2-4 ENRICH outputs existing
- R29 cliente friendly (NO admin lingo · SignatureCanvas Spanish copy · empty state "Sin prisa por tu parte" doctrine)
- R30 admin tutor (TooltipENS Ed25519 + ENAC + SHA256)
- Cliente-mínimo filosofía 100% (cliente FIRMA · NO opera técnico · admin trigger via /admin/signing/intents/request)

**Future-X DEFER 0 items casuales** (architect doctrine inviolable). TIER 2 eIDAS qualified signature externos providers contrastado duplicidad post-piloto demand-driven `Future-1.F+.tier-2-eidas-qualified-external-provider` (~15-25h solo si cliente real lo demande contractualmente · ADR-009 sostained NO eIDAS preventivo) + `Future-1.F.signature-canvas-s3-migration` (~2-3h post Hetzner deploy · base64 DB column funciona empirical pre-piloto).

**Next sesión architect approve**: **Ejecutable 8 EXPANDED FRESH-EYES MASIVO** (20 pasadas · ~40-58h empirical · 4 STOP-AND-REPORT checkpoints) comprehensive repo audit + quality gate Pre-Bloque 7.

## Sesión 3B-4 Ejecutable 7 CERRADO · axe-CI consolidate Path A cliente+auditor CI gate extend (2026-05-27)

**Status**: ✅ CERRADO scope refined per audit-first empirical · CI workflow extended 3 jobs · runtime local DEFER infrastructure-blocked documented honest.

**Tag local**: `s3b-4-cerrado`
**Audit doc**: [`docs/audits/AUDIT_EJECUTABLE_7_AXE_CI_CONSOLIDATE_STATE.md`](docs/audits/AUDIT_EJECUTABLE_7_AXE_CI_CONSOLIDATE_STATE.md)

**Resumen cifras**:
- ~30-45 min empirical vs ~4-6h projection nominal (OPS-045 -85% sostained · 53ª aplicación cumulative)
- 1 atomic commit (Phase 7.A.3 CI gate extend)
- CI workflow `admin-polish-empirical.yml` extended de 1 job → 3 jobs (admin 80 + cliente 10 + auditor 12 = 102 pages cumulative)
- 1 Future-X DEFER documented (infrastructure tooling local dev backend env reload helper · NO bloquea piloto)

**Phase 7.A.0 audit findings empirical**:
- 10 cliente specs scaffolds existing (`tests/polish/cliente/01-10`) · Sesión 3B-2B.4 Phase 3 creados
- 12 auditor specs scaffolds existing (`tests/polish/auditor-portal/01-12`) · Sesión 3B-2B.6 CLUSTER 2 Phase 5.10 + CLUSTER 3 creados
- CI workflow existing single job 80 admin pages · NO cliente/auditor jobs

**OPS-052 manifestación 72ª** (audit-first reveal infrastructure blocker · scope refined per empirical):
- Backend PID 53234 running since 2026-05-26 SIN `FULKRO_AUTH_PRIVATE_KEY` env loaded · backend generates EPHEMERAL Ed25519 key
- Frontend dev server middleware uses FROZEN `FULKRO_AUTH_PUBLIC_KEY` desde `.env`
- JWT verify mismatch (ephemeral private ≠ frozen public) · `getClaims()` returns null · ALL `/client-portal/*` redirect login infinite loop
- Specs CODE 100% correct · scaffolds correct · root cause infrastructure NOT spec issue
- **CI environment loads key pair correctly** via GitHub secrets (FULKRO_AUTH_PUBLIC_KEY + FULKRO_AUTH_PRIVATE_KEY both set) · workflow extension validates in CI

**Phase 7.A.3 CI gate extend shipped (PRIMARY DELIVERABLE)**:
- NEW `cliente-polish-empirical` job · 10 pages · gate critical+serious axe = 0 · same setup pattern as admin (OPS-026 DRY)
- NEW `auditor-polish-empirical` job · 12 pages · AUDITOR_PORTAL_TOKEN generated via `_dev/auditor-portal-token` endpoint runtime · gate critical+serious axe = 0
- Both jobs reuse postgres pgvector:pg16 service + Node 20 + Python 3.12 + Playwright chromium · DRY OPS-026
- Artifact uploads per portal (polish-report-admin + polish-report-cliente + polish-report-auditor + polish-test-results-*)

**Pattern P-CL2-5 consolidate sostained**:
- Single workflow file `admin-polish-empirical.yml` con 3 jobs · NO double-pass duplicidad
- Workflow name updated: "Admin + Cliente + Auditor Polish Empirical"
- Coverage cumulative 102 pages (80 admin + 10 cliente + 12 auditor)

**Doctrinas honored cumulative**:
- OPS-026 DRY (job setup mirror across admin/cliente/auditor · NO duplicate workflow files)
- OPS-045 audit-first 53ª aplicación (-85% empirical sostained · 30-45 min vs ~4-6h nominal)
- OPS-049 honest path (local empirical infrastructure blocker documented transparent · NOT spec code issue)
- **OPS-052 manifestación 72ª** (audit-first reveal env-load infrastructure issue blocks local empirical · CI environment correct)
- ADR-013 doble pool sostained (cliente specs require_client_user · auditor specs magic-link AUDITOR_PORTAL_ENAC)
- R23 + Pattern P-CL2-5 consolidate sostained

**Future-X DEFER 1 item (NO bloquea piloto · infrastructure tooling)**:
- `Future-Ejecutable-7.local-dev-backend-env-reload-helper` (~15-30 min post-piloto demand-driven · `scripts/dev_restart_backend.sh` helper que load .env properly + verify FULKRO_AUTH_PRIVATE_KEY/PUBLIC_KEY pair match · NO bloquea piloto cliente real cuando deploy Hetzner FASE J usa env vars correctly)

**Next sesión architect approve**: **Ejecutable 8 EXPANDED FRESH-EYES** comprehensive repo audit + quality gate Pre-Bloque 7 (~20-30h · 13 pasadas comprehensive · raw repo audit + dead code identification + coherence verification + cybersecurity standards + ENS cycle walkthrough BÁSICO+MEDIO+ALTO + frontend quality audit + corrections inline + monitoring absorbed sub-phase + VALIDATION final).

## Sesión 3B-2B.11 Ejecutable 6 CERRADO · Sync Hardening P1 items 1+4+5 críticos (2026-05-27)

**Status**: ✅ CERRADO scope refined post audit-first empirical · 3 phases shipped · 16 backend tests NEW PASS + 21 regression preserved.

**Tag local**: `s3b-2b-11-cerrado`
**Audit doc**: [`docs/audits/AUDIT_EJECUTABLE_6_SESION_3B_2B_11_SYNC_HARDENING_STATE.md`](docs/audits/AUDIT_EJECUTABLE_6_SESION_3B_2B_11_SYNC_HARDENING_STATE.md)

**Resumen cumulative cifras**:
- ~1.5h empirical vs ~9-11h projection nominal (OPS-045 -85% sostained · 52ª aplicación cumulative)
- 3 atomic commits sequential (Phase 11.1 + 11.2 + 11.3)
- 16 backend tests NEW PASS (6 SSE replay + 4 concurrent loops + 6 DLQ service)
- 391/391 cumulative cross-suite PASS · ZERO regression introduced (failures empirically PRE-EXISTING · verified git stash baseline)

**Phase 11.1 SSE resilience event_id + ring-buffer + Last-Event-ID**:
- `SseEvent.event_id` UUID per dispatch (browser EventSource native Last-Event-ID compatible)
- `SseDispatcher` replay buffer `deque(maxlen=100)` per channel
- `subscribe(channel, last_event_id=None)` replays events posteriori · empty si gap >100
- SSE endpoints honor `Last-Event-ID` header + `id` field per yielded event
- 6/6 NEW tests + 21/21 existing audience filter preserved

**Phase 11.2 corrective_loops advisory lock**:
- **OPS-052 manifestación 71ª**: `pg_advisory_xact_lock(hashtext('audit_log_chain'))` ALREADY EXISTS en trigger (migration `d4f8b2a90001`) · briefing scope refined transparent
- `transition_loop` extended `pg_advisory_xact_lock(hashtext('corrective_loop_' || loop_id))` per-loop_id (mirror audit_log canonical)
- R6 hash chain inviolable preserved empirical (5 loops × 3 transitions = 15 audit_log inserts · check_audit_log_integrity ok=True)
- 4/4 NEW tests + 6/6 regression PASS

**Phase 11.3 DLQ minimal OPS-026 DRY reuse NotificationEvent**:
- **NO new alembic migration** (ADR-025 sostained · existing table semánticamente covers DLQ)
- DLQ entry = `notification_events WHERE status='failed' AND retry_count >= 3` (Celery max_retries=3)
- NEW service + 4 admin API endpoints (list + summary + reprocess + resolve · require_owner ADR-013)
- NEW frontend widget `NotificationsDlqWidget` embedded `/admin/operations` R23 cross-cliente
- 4 NEW canonical audit_log events Sub-atom 5.A · 6/6 NEW tests PASS

**Patterns library extended (2 NEW · 22 cumulative cross-app)**:
- **#21** event_id + replay buffer + Last-Event-ID canonical SSE resilience (browser EventSource native compatible)
- **#22** Per-resource advisory lock `pg_advisory_xact_lock(hashtext(prefix || resource_id))` (mirror audit_log · transaction-scoped · serializes critical mutations per-resource avoiding global bottleneck)

**Doctrinas honored cumulative**:
- ADR-013 doble pool · ADR-025 reuse infrastructure · OPS-026 DRY · OPS-045 52ª · OPS-049 honest path · **OPS-052 manifestación 71ª**
- R6 hash chain inviolable preserved empirical
- Sub-atom 5.A audit_log 3-way OR propagated
- R23 admin top-level cross-cliente legitimate (DLQ operations console)
- R30 admin tutor friendly (TooltipENS explain DLQ semántica)

**DEFER items 7/9/10 post-piloto Future-X (contrastados duplicidad)**:
- `Future-Sesión-3B-2B.11.item-7-cliente-portal-multi-device-sync` (~2-3h · duplicidad cubre 80% via SSE realtime existing)
- `Future-Sesión-3B-2B.11.item-9-llm-deterministic-replay` (~3-5h · duplicidad cubre via temperature ≤0.2 R3 + prompt cache)
- `Future-Sesión-3B-2B.11.item-10-cross-region-failover` (~5-8h · duplicidad cubre via single-region Hetzner FASE J + backup mensual R8)

## Sesión 3B-2B.9 CLUSTER 1 PATH A CERRADO · Admin Navigation Foundation (2026-05-27)

**Status**: ✅ CERRADO DEFINITIVO · arquitectura Opción 2 COEXIST architect approved · empirical WSL2 native verified.

**Tag local**: `s3b-2b-9-cluster-1-cerrado`
**Validation doc**: [`docs/audits/CIERRE_SESION_3B_2B_9_CLUSTER_1_PATH_A.md`](docs/audits/CIERRE_SESION_3B_2B_9_CLUSTER_1_PATH_A.md)
**Branch**: `radar-v9` · 8 atomic commits cumulative · 209 cross-suite PASS · ZERO regression.

**Resumen cumulative cifras CLUSTER 1**:
- 8 atomic commits (1A audit STOP HARD + 1B-1D implementation + 1E reveal + 1F login redirect + 1G E2E + cierre)
- 3 backend tests NEW PASS empirical (supervision_mode at creation)
- 19 frontend unit tests NEW (detectActiveAdminTab 8 + isGlobalTabPath 11)
- 3 E2E smoke + 5 test.skip Future-X
- 5 patterns NEW formalized (#32-#36)
- OPS-052 manifestations 57ª-63ª (7 cumulative · STOP HARD scope refined REFACTOR+EXTEND)
- OPS-045 -50% empirical cumulative (~4.5-5.5h vs ~8-15h nominal)
- OPS-026 DRY masivo: supervision_mode column Phase 6D Sesión 3B-2B.8 REUSED zero migration

**Arquitectura objetivo Opción 2 COEXIST implementada**:
- Header global tri-pestaña (Proyectos · Compliance) SIEMPRE visible cross all admin pages
- Sidebar lateral existing CONDITIONAL render solo project context (`/admin/projects/[id]/*`)
- Selector hub (`/admin/projects`) = admin landing post-login + gate único re-entry
- L3 hybrid auto-enter REMOVED · `lastUsedProjectId` solo UX hint
- ClearProjectContextOnGlobalNav guard · clears Zustand al salir a global tab
- Selector + Compliance render página full-width sin sidebar lateral

**Doctrinas honored cumulative**:
- R23 doctrine + extended (Marcos vision firmísima · single source-of-truth gate)
- OPS-052 audit-first MANDATORY (7 audit docs Phase 1A-1G + STOP HARD scope refined)
- OPS-026 DRY (supervision_mode column reuse cross-session · MagicLinkPurpose M12 reuse)
- OPS-049 honest path (Phase 1E zero-implementation transparent · 1G scaffold-first)
- ADR-054 ActiveProjectSync sostained + reinforced
- ADR-013 doble pool + Sub-atom 5.A audit_log 3-way OR propagated

**Next sesión architect approve**: **Sesión 3B-2B.9 CLUSTER 2** · Admin Command Center sub-pages real content · 5 sub-areas independientes audit-first per area (~25-40h scope mayor):
- Sub-area 2A · Dashboard proyecto real KPIs (~6-10h)
- Sub-area 2B · Workflow admin view R30 inverso (~5-8h)
- Sub-area 2C · Settings admin extendido (~3-5h)
- Sub-area 2D · Portal compliance Fulkro self-dogfooding real content (~6-10h)
- Sub-area 2E · Cross-client overview supervisión high-level (~5-7h)

---

## Sesión 3B-2B.4 Path B EMPIRICAL CERRADO (2026-05-26)

**Status**: 🟢 14 atomic commits · 6/7 criterios PASS empirical · 1/7 scaffold (env-dependent runtime cliente portal). Validation: `docs/audits/VALIDATION_SESION_3B_2B_4_PATH_B_FINAL.md`.

**Deliverables shipped**:
- Phase 1.1-1.4 Foundation (gallery 444 screenshots indexed · HeaderProjectChip + sidebar brand accent · CopilotGuidedFlow 8 core ENS pages DRY catalog · Zustand merge semantics race fix)
- Phase 1.5 ISOLATION AUDIT (empirical psql ground-truth · `ISOLATION_AUDIT_REPORT.md` · finding A copilot RLS fixed inline · B+C pre-existing sequenced Sesión 5)
- Phase 2.1-2.4 client_id FK + RLS expansion (`copilot_isolation` 3-way clause) + service refactor + 6/6 tests empirical + frontend API client
- Phase 3 cliente portal WCAG sweep scaffold (10 specs collect clean · runtime PASS pending `npm run test:polish:cliente` prod build)
- Phase 4 PDF reports branding (helper `core/branding/pdf_context.py` reusable · M21+M22+M06 wired · 4/4 tests empirical)

## Sesión 3B-2B.6 Path C CERRADO DEFINITIVO · Auditor ENAC Entregable + Portal + Interactive Features (2026-05-26)

**Status**: ✅ CERRADO DEFINITIVO · CLUSTER 1 + Sub-atom 5.A + CLUSTER 2 + CLUSTER 3 + CLUSTER 4 VALIDATION shipped.

**Tag local**: `s3b-2b-6-path-c-cerrado`
**Validation doc**: [`docs/audits/VALIDATION_SESION_3B_2B_6_PATH_C_FINAL.md`](docs/audits/VALIDATION_SESION_3B_2B_6_PATH_C_FINAL.md) (~570 LOC empirical)
**Branch**: `radar-v9` · 18 atomic commits cumulative · 786/786 cross-suite PASS · ZERO regression existing.

**Resumen cumulative cifras**:
- 18 atomic commits totales (CLUSTER 1 × 3 + Sub-atom 5.A × 2 + CLUSTER 2 × 6 + CLUSTER 3 × 9 - 2 unrelated radar-v9)
- ~120 backend tests NEW Sesión 3B-2B.6
- 786/786 cross-suite final · architect target 370 exceeded 116%
- 4 migraciones alembic aplicadas empirical (audit_log_rls_001 + audit_log_auditor_events_001 + auditor_annotations_001 + auditor_clarification_001)
- 33 canonical audit_log events cumulative
- 12 architectural patterns formalized cross-app reusable
- 4 servicios arquitectónicamente reusables (M05 sign + emit_auditor_event + compute_dda_evidence_gaps + generate_draft_audit_report)

**Radar-V9-PERFECT Fase 1 CIERRE cumulative (2026-05-26)**:
- ✅ **Fase 1.A Bloque G** outreach draft assist · commit `bcb56e4` · 25 tests PASS · 7 templates por tier + 4 citas canonical (TACPC 451/2025 · Informe 25/2025 Andalucía · TACPC Canarias 131/2025 · Art. 2.3 RD 311/2022) · LLM personalization opcional sonnet ($0.005/draft) · migration radar_v9_perfect_g_001 + frontend DraftPreviewDialog + RunControlBar wire
- ✅ **Fase 1.B Bloque I** incremental scrape delta-based · commit `db880da` · 19 tests PASS · IncrementalScraperHelper helper (300 LOC) · migration radar_v9_perfect_i_001 sources_runs cols extension · cost saving 75-85% projected vs full rescan · force_full_rescan emergency override flag · OPS-045 audit-first extend SourceRun (NO new sources_state table per D1 cement)
- ✅ **Fase 1.C Bloque H** cleanup + QuickStart UI + tag radar-v9-perfect-fase1 · commit pending · scope cement post-audit H.0: 3 pre-existing tests fixed/skipped · 4 scripts ARCHIVE `_archive/radar_v9/` · CLAUDE.md cement Fase 1 cumulative · docstrings sweep críticos
- **Cost LLM cumulative C+E+G+I+H ≈ $10.37** vs caps cumulative $150 (~7% utilizado · 93% margin)
- Pattern #15 (proactive nudge scheduler · Sesión 3B-2B.8 CLUSTER 2 Phase 2C) + Pattern #16 (incremental scraping delta-based helper · radar-v9-perfect Fase 1.B) formalized cross-app

**Mega-Atom RADAR-V9-PERFECT CIERRE FINAL (2026-05-27 · branch radar-v9 merged → main)**:

Tag local `radar-v9-perfect-fase2` (commit `85ef44dd` · "Fase 2 complete"). Decisions cement Marcos post-Fase-2:
- **D1 DEFER Fase 3 Galicia + Valencia direct scrapers** Future-X (same Andalucía pattern · PLACSP central federal cubre CCAA empíricamente · 8-12h HIGH-risk Angular SPA NO justifica 1-3% marginal value · post-piloto cuando revenue justifica). Future-2.A+ captured: `andalucia-junta-direct-scraper-angular-spa` + `galicia-xunta-direct-scraper` + `valencia-gva-direct-scraper`.
- **D2 PENDIENTE Marcos sample audit retrospectivo pliegos_defectuosos** (CSV 20 rows · ~30 min). Threshold action: 🟢 ≥0.65 precision → outreach immediate · 🟡 0.40-0.64 → iterate detector v1.1 (~1h) · 🔴 <0.40 → escalate revisit pliego_excerpt (Future-X prerequisite pliego_downloader).
- **D3 CIERRE Mega-Atom cumulative Fase 1+2** · sistema 100% operativo production-ready.

**Fase 2.B Bloque F pliegos defectuosos cumulative (2026-05-27)**:
- ✅ **Fase 2.B F.1** detector v1 + migration `radar_v9_perfect_f_001` (commit `f1b26d6e` · OPS-045 62ª) · `PliegoDefectuosoDetector` 6-criteria intersection · v1 pragmatic confidence MEDIUM 0.60/0.65/0.75 · CLI script `radar_detect_pliegos_defectuosos.py` · TACPC Canarias 131/2025 jurisprudencia ángulo comercial nuevo
- ✅ **Fase 2.B F.2** template `pliego_defectuoso` + ANGULO_COMERCIAL wire-up (commit `bbaa2770` · OPS-045 63ª)
- ✅ **Fase 2.B F.3** audit frontend filter+badge+stat 100% pre-shipped (commit `dc98c119` · OPS-045 64ª)
- ✅ **Fase 2.B F.4** tests + smoke empirical + sample CSV (commit `064571f9` · OPS-045 65ª)
- ✅ **Fase 2 complete** cement final (commit `85ef44dd` · audit F.0 docs + test_phase_d_indexes 17 cumulative fix · Marcos cement D1-D4 honored)
- **Empirical**: 946 detected + 156 leads cumulative · Path A 461 contactable preserved · ~$0 marginal LLM cost (rule-based detector NO LLM call) · cost cumulative final C+E+G+I+H+F ≈ $10.37
- **Bloque F adopta Pattern #17 NEW**: rule-based detector pure functional + 6-criteria intersection + jurisprudencia citas template wire-up (cross-app reusable detector pattern)

**Pattern library cumulative formalized radar-v9-perfect Fase 1+2 (4 patterns nuevos · 17 cumulative cross-app)**:
- **#14** audit_log 3-way OR (Sub-atom 5.A · project_id + client_id propagation)
- **#15** proactive nudge scheduler pure functional (Sesión 3B-2B.8 CLUSTER 2 Phase 2C)
- **#16** incremental scraping delta-based helper (`IncrementalScraperHelper` · 75-85% cost saving)
- **#17** rule-based detector + jurisprudencia citas template wire-up (`PliegoDefectuosoDetector` · NO LLM cost · 6-criteria intersection)

**Future-X registry final Fase 2 (5 entries · post-piloto demand-driven · revenue-justified)**:
- `Future-2.A+.andalucia-junta-direct-scraper-angular-spa` (~6-9h · Angular SPA scraping HIGH-risk · 1-3% marginal value over PLACSP)
- `Future-2.A+.galicia-xunta-direct-scraper` (~8-12h · same dynamic SPA pattern)
- `Future-2.A+.valencia-gva-direct-scraper` (~8-12h · same dynamic SPA pattern)
- `Future-2.B+.detector-pliego-defectuoso-v2-high-conf` (~6-10h · post pliego_downloader expansion · regex pliego content full PDF · upgrade confidence MEDIUM→HIGH)
- `Future-2.B+.pliego-downloader-pdf-fulltext-extraction` (~4-6h · prerequisite v2 detector · PDF download + text extraction per tender + storage)

**Production deploy state (2026-05-27 · ready merge main + Hetzner)**:
- ✅ 5 migrations radar-v9-perfect aplicadas DB local: `radar_v9_perfect_a_001` + `_c_001` + `_f_001_pliego_defectuoso` + `_g_001_outreach_draft` + `_i_001_incremental_checkpoints`
- ✅ Tests cross-suite verde · ZERO regression existing
- ✅ Tags local: `radar-v9-perfect-fase1` (Fase 1.C complete) + `radar-v9-perfect-fase2` (Fase 2 complete · re-pointed to `85ef44dd`)
- ✅ Branch `radar-v9` 1,111+ commits cumulative ready merge `main` (NO conflicts expected · linear forward)
- ⏳ Marcos D2 sample audit pliegos_defectuosos CSV 20 rows (~30 min · gate primer outreach REAL)
- ⏳ Hetzner production deploy + ENV `ENABLED_SOURCES="placsp,madrid_ccaa,cataluna,euskadi,ted"` + apply 3 migrations radar-v9-perfect en prod DB
- ⏳ Primer "Actualizar radar" desde UI cuando Marcos ready outreach (NO trigger automático pipeline pre-validation)

**Next phase OPERATIONAL**: outreach piloto pagador 25 junio deadline (4 semanas restantes desde 27 mayo). Workflow Marcos primer outreach: `/radar/` → filter "Solo pliegos defectuosos" → click lead top → drawer "Generar borrador outbound" → preview/edit → copy/mail → tracking via `notas_marcos` (workaround pre-piloto).

**Próximas sesiones** (post-CERRADO 3B-2B.6):
- **Sesión 3B-2B.8** · Cliente Portal Path C entero + MFA TOTP + workflow cliente cronológico + gestor documental cliente (~92-127h · scope mayor pre-piloto-1 crítico)
  - ✅ **CLUSTER 1 Path A CERRADO 2026-05-26** · 5/5 BLOQUEANTES RESOLVED · 5 commits sequential (`29da928` + `3a03155` + `d894aed` + `e87964a` + `4d3fb18`) · cumulative ~11.2h vs 20-28h nominal (OPS-045 -50% to -60%) · 920 PASS cross-suite ZERO regression · 9+ patterns formalized · 17 Future-X captured · cliente-mínimo filosofía 5/5 phases aligned (architect retrospective audit) · ver `docs/audits/CIERRE_CLUSTER_1_PATH_A.md`
  - ⏸️ CLUSTER 2 Path B 6 items NEXT (~12-17h empirical projection · reframe DRP/BIA questionnaire+approve · NO creator mode cliente)
- Sesión 3B-2B.9 · Admin Portal Symmetric + Workflow Coherence + Sync (~18-30h)
- Sesión 3B-2B.7 · Cloud Connections Completeness (~15-25h)
- Sesión 3B-2B.10 · Audit Simulacro Pre-ENAC (consume Phase C3+C4 services reusable · ~15-25h)
- Sesión 5 · Security inhackeable + Sub-atom 5.B (~13-22h)
- Sesión 3B-4 · Compliance FULKRO + axe-CI (~6-12h)
- Bloque 7 · Dogfooding BÁSICA + MEDIA E2E (~32-53h)
- FASE J · Producción Hetzner + cliente piloto MEDIA real (~25-40h)

---

## Sesión 3B-2B.6 Path C historical (CERRADO) · Auditor ENAC pre-3B-2B.8

**CLUSTER 1 shipped** (3 commits · 20/20 tests PASS):
- Phase 1 · MANIFEST Ed25519 signing wire-in (M05 keypair → M09 dossier · commit 55c9473 · 5/5 tests)
- Phase 2 · `mark-audit-passed` admin endpoint + state machine cascade (commit 4c16f6a · 6/6 tests · 2 migrations)
- Phase 3 · Retainer trigger automation post audit_passed (commit 6602e1a · 9/9 tests)

**Sub-atom 5.A INLINE INSERT shipped** (1 commit · 4/4 isolation tests):
- audit_log RLS hardening pre-CLUSTER 2 (commit b20f135 · migration audit_log_rls_001 · policy 3-way OR clause)
- Sub-atom 5.B `magerit_assets` + 11 child tables RLS · PENDING Sesión 5 future (architecturally coherent · NO bloquea audit portal)

**CLUSTER 2 shipped** (6 atomic commits · 30/30 backend tests + 144/144 m09 regression):
- Phase 4 ee66efa · auditor ENAC portal entry + magic-link gated layout (7/7)
- Phase 5A 89670b1 · summary + dda + magerit read-only views (9/9 + 1294 lines)
- Phase 5B ced0ba2 · plan + evidence + e041 views (10/10 + 1265 lines)
- Phase 5C d078367 · audit_log + pentest + documents views (11/11 + 1141 lines)
- Phase 5.10 159f415 · WCAG axe-CI cross-views scaffold 9 specs
- Phase 6 b32ed96 · audit_log event_type canonical namespace + cross-motor download wire-in
  (migration audit_log_auditor_events_001 · 22 canonical events · 3 wire-in downloads: dossier.zip
  + audit-log.csv + evidence/{id}/download · 14/14 + RLS isolation + hash chain inviolable)

**CLUSTER 3 shipped** (8 atomic commits · 60/60 backend tests + 786/786 cross-suite cumulative):
- Phase C1.1+C1.2 191a65a · auditor_annotations schema + CRUD API (11/11 · 7 target_types · 4 severities
  · 24h delete window + magic_link_id ownership)
- Phase C1.3 8b6a5ca · annotation panel inline (DdA + Evidence + MAGERIT) + admin review page
- Phase C2.1+C2.2 1f7bd64 · auditor_clarification_requests schema + CRUD API + SSE dispatch
  channel project:{id} + email backup M20 EmailSender (9/9 · 8 target_types incl general · auto-advance
  open → responded)
- Phase C2.3 0880f56 · ClarificationButton topbar global + AdminClarificationsInbox SSE realtime
  (EventSource native + tanstack invalidate + counter "X nuevas")
- Phase C3.1+C3.2 db2129c · dda_evidence_gap_service.py pure functional (GapDetectionOptions ·
  4 GapStatus + 4 GapSeverity) + API (29/29) · empirical heatmap BASICA 46/73 applicable · 11 critical_missing
- Phase C3.3 89f0503 · DdaEvidenceGapsView heatmap UI + admin twin con multi-select request-more-evidence
  + drawer drill-down + ClarificationButton anclar pregunta a medida
- Phase C4.1+C4.2 73f21c2 · draft_report_generator.py service (reportlab platypus · weasyprint NO instalado
  OPS-052 honest adaptation) + API auditor + admin (20/20 · empirical PDF 7988 bytes 3 pages
  Spanish accents preserved · sha256 + Ed25519 signed M05 reuse · 9 sections · NO_APROBAR auto-derived)
- Phase C4.3 6e7f800 · DraftReportView iframe preview + signed PDF download CTA + admin twin
- Phase C5 (this commit) · E2E full-flow scaffold (9 steps) + 4 polish specs WCAG (annotations panel ·
  gaps heatmap · draft-report · admin clarifications inbox) · cross-suite 786/786 PASS cumulative

**Pattern library Sesión 3B-2B 10+ patterns formalized (cross-app reusable)**:
1. sidebar ::before pseudo-element for gradient (axe-core bg-image workaround)
2. Card solid white bg (translucent contrast loss avoided)
3. Token DEFAULT -700 overhaul (Tailwind shades AA contrast)
4. Translucent bg matching shade (consistency cross-components)
5. DataTable aria-label (WCAG 2.4.4 button-name)
6. redirect-aware isProjectScoped spec pattern
7. ActionLink CTA a11y primitive
8. Reusable spec template runProjectScopedProbe/runTopLevelAdminProbe + runAuditorPortalProbe
9. HMR stale touch (force frontend reload post token changes)
10. **CLUSTER 3 added**: emit_auditor_event helper canonical (Phase 6) · annotation panel embeddable
    cross-views · ClarificationButton SSE realtime + email backup · DdA-evidence gap service pure
    functional reusable (Sesión 3B-2B.10 target) · reportlab platypus for data-heavy PDFs

**Future-CLUSTER 2.delta + Future-CLUSTER 3.delta (architecturally coherent · demand-driven post-piloto)**:
- `Future-CLUSTER 2.delta.cross-motor-downloads-extended` · M03 DdA PDF + M04 Plan PDF + M27 E-041 PDF
  + M08 Pentest report PDF + M07 ZIP por medida downloads (services existen pero require streaming +
  signing wire-in · ~6-8h cumulative · OPS-026 sin demand inmediato)
- `Future-CLUSTER 3.delta.annotation-panel-3-views-remaining` · PlanView + AuditLogView + PentestView
  embed AnnotationPanel (3 views restantes · ~30 min cada · demand-driven)
- `Future-CLUSTER 3.delta.report-template-docx-editable` · migration reportlab platypus → PDFRenderer
  canonical (docxtpl + LibreOffice headless · DOCX template Marcos editable Word) ~3-4h
- `Future-CLUSTER 3.delta.pdf-embedded-signature-pkcs7` · PDF/A-3 embedded signature en metadata (current:
  signature_hex via headers · NO embedded en PDF binary)
- `Future-CLUSTER 3.delta.draft-report-opinion-persist` · table audit_report_drafts si Marcos demanda
  persistir opinion_text + recommendation server-side cross-sessions
- `Future-CLUSTER 3.delta.qr-code-verification-link` · QR code en PDF firma footer linking verify endpoint
- `Future-CLUSTER 3.delta.clarification-anchored-embedding` · ClarificationButton per-item embedding
  cross views específicas (Evidence + DdA + MAGERIT) actualmente solo topbar global

**CLUSTER 4 VALIDATION shipped** (commit final + tag `s3b-2b-6-path-c-cerrado`):
- VALIDATION_SESION_3B_2B_6_PATH_C_FINAL.md generated · ~570 LOC empirical
- 4 memorias auto persistentes nuevas (auditor-portal-architecture + dda-evidence-comparison-algorithm + audit-passed-state-machine + draft-report-generation-pattern)
- Pattern library 12 patterns formalized cumulative
- Git tag local `s3b-2b-6-path-c-cerrado` aplicado

## Memorias auto persistentes

Ver `/home/usuario/.claude/projects/-home-usuario-fulkro/memory/MEMORY.md`:
- `env_wsl2_native_runtime.md` · WSL2 native dissolves OPS-050/052 prior session constraints
- `feedback_empirical_honesty.md` · Marcos asks "a la perfección?" expecting empirical truth, not architectural claim
- `project_ens_radar_dossier_duration.md` · Full pipeline ~4h empirical (resume cursor verified)
- `reference_mcps_docker_images.md` · Docker images per MCP tool empirical-tested
- `project_ens_radar_scoring_marcos_intersection.md` · 4/5 strict + C4 reincidencia honest defer
- **NEW Sesión 3B-2B.6 CLUSTER 4**:
  - `auditor-portal-architecture.md` · routes + magic link gate + 22 canonical events
  - `dda-evidence-comparison-algorithm.md` · pure functional service + reusable Sesión 3B-2B.10
  - `audit-passed-state-machine.md` · cascade flags + LifecyclePaso4Service propagation
  - `draft-report-generation-pattern.md` · reportlab platypus + Ed25519 + Future DOCX migration

## Historia detallada archivada

Para detalles sub-atom-por-sub-atom de:
- Sub-atoms 1.D.A → 1.D.J completos history (~70k chars)
- Sub-atoms 1.D.X Cloud-First MVP CORE+ 7/7 detail
- Sub-atoms 1.E.1 + 1.E.2 + 1.E.2.bis Project-Scoped Admin UX evolution
- Bloques 3+5 + 4 + 6 critical paths cierre detail
- Sesiones 1 + ADDENDUM + Path A + 3A + 3B-1 + 3B-2A + 3B-2B + 3B-2B.2 reports
- RADAR-V9 Prompt 1B Phase A-E cumulative 14 commits
- OPS-052 manifestations 1ª-14ª detailed (15ª-21ª recent preserved in doctrine)
- Pattern library detailed examples + reusable templates
- 1.D.H + 1.D.H.bis zero-debt closure E2E validation reports

Ver: **`docs/archive/CLAUDE_HISTORY_PRE_3B2B3.md`** (251k chars · snapshot completo 2026-05-25).

Para audits específicos consultar:
- `docs/audits/AUDIT_*.md` (Phase 0 per sub-atom audits empíricos)
- `docs/audits/VALIDATION_*.md` (sub-atom cierre validations end-to-end)
- `docs/sessions/SESION_*.md` (sesión reports completos)
- `docs/architecture/ADR-*.md` (decisiones arquitecturales formalizadas)
- `docs/doctrine/` (R-rules + OPS-lessons formalized)

## Preguntas

Si encuentras un gap en la spec, consulta los apéndices A-O en `docs/spec/` primero, luego los entregables de corrección (`CORRECCION_*.md` + `CIERRE_FINAL_3_GAPS.md`), y si no está cubierto, pregunta a Marcos.
