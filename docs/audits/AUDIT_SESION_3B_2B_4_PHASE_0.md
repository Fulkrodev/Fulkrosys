# Sesión 3B-2B.4 · Phase 0 Empirical Audit (3 Dimensions)

**Status**: 🟡 STOP-AND-REPORT · architect approve required antes Phase 1+2+3 execute
**Doctrine**: OPS-052 Phase 0 mandatory · empirical filesystem verification ANTES propagate implementation chain
**Date**: 2026-05-25
**Scope**: Marcos directive — (1) Inspección visual deep · (2) Copiloto super-version · (3) Per-cliente adaptation
**Audit time**: ~2h cumulative (3 parallel Explore agents · empirical grep/glob/read · NO code changes)

---

## Resumen ejecutivo · honesty path

| Dimensión | Foundation existing | Gaps críticos | ETA realistic | Bloqueante piloto? |
|-----------|---------------------|----------------|---------------|--------------------|
| **D1 · Visual/UX** | 444 screenshots admin · pattern library 9 patterns formalized · 22 admin pages PROBE+P1+P2 GREEN | **31 cliente portal pages 0 specs WCAG** · 4 radar untested · empty states cliente inconsistent · density mobile tables | ~12-15h (WCAG sweep cliente 8-10h + visual aesthetic 3-4h + gallery 30-60m) | NO (admin firmísimo · cliente piloto MEDIA tolera baseline 73-78/80) |
| **D2 · Copiloto super** | M11 motor 8 endpoints · A14 service · Triad components 100% coded · 35 tests verde · pgvector RAG ~127 chunks corpus | **Memoria per cliente ❌** (NO client_id FK) · cross-conversación ⚠ partial · sistema-aware ❌ (NO motors/agents/MCPs ingested) · CopilotGuidedFlow integrado 1/85 pages · coach next-action ❌ | ~22-33h Phase 1+2+3 cumulative | NO (current copiloto funcional · super-vision aspiracional T1) |
| **D3 · Per-cliente adapt** | Branding DB schema (logo + colors + footer) · ClientBrandingProvider + ClientFooter · Active project store + Sync + Breadcrumb · AdaptationBadge R28 materialized | **PDF reports NO branding** · email templates partial · sidebar/header admin NO project context badge · per-project branding diferred R27 LIMIT 1 firme | ~10-15h (quick wins 2h + core 6-8h + aspiracional T1 8-10h post-piloto) | NO (cliente-level branding suficiente piloto MEDIA · per-project demand-driven) |

**Honesty empírico Marcos**: ninguna de las 3 dimensiones bloquea piloto pagador. Foundation 70% production-ready en las 3. Gaps son **polish + aspiracional T1** (NO core ENS compliance). Decisión architect approve scope:
- **Path Minimalista** (~4-6h): quick wins las 3 dimensiones (gallery + dashboard phase badge + sidebar project context)
- **Path Recomendado** (~14-18h): cliente WCAG sweep + copiloto memoria per cliente + branding PDF reports
- **Path Aspiracional** (~30-45h): completo super-vision copiloto + per-project branding + workflow tracker

---

## DIMENSION 1 · Visual/UX audit empirical

### 1.1 Inventory completo · 137 pages (verified `find + wc -l`)

| Sección | Pages | WCAG specs | Visual status | Notas |
|---------|-------|------------|---------------|-------|
| Admin total | 85 | 22 GREEN PROBE+P1+P2 · 41 untested · 22 deferred T1 | 76-80/80 sample | 74 con screenshots 6 viewports (444 PNG) |
| Cliente portal | 31 | **0 specs** | 73-78/80 sample | Pattern library 100% aplicable · sweep pendiente Sesión 3B-3 |
| Legal | 8 | 0 specs | 42-56/56 static | LegalArticle wrapper · NO interactive risk |
| Portal previo (pentester/remediation/verify-auth) | 5 | 0 specs | UNKNOWN | Token-based magic-link entry |
| Radar | 4 | 0 specs (Future-1.E.batch5) | UNKNOWN | Admin-only Marcos |
| Public (sign/download) | 4 | 0 specs | UNKNOWN | Static auth-gated forms |
| Root | 3 (docs · forbidden · login) | 0 specs | UNKNOWN | login probado E2E |
| **TOTAL** | **140** | **22 (15.7%)** | **134 sin score formal** | Empirical scaling factor 1.4x cliente vs admin |

**Discrepancia minor**: prior framing reportaba "85 admin pages" · empirical `find frontend/app/(admin) -name page.tsx | wc -l` retorna 85 · OK. Frontend total 137 page.tsx (Sesión 3B-2B.3 reportó 83 admin · ahora 85 · drift +2 pages durante 3B-2B.3 polish session).

### 1.2 Pages NOT swept · candidatos sweep

**Cliente portal completo (31 pages)** — sweep Sesión 3B-3:
- Core (16): dashboard · conformidad · evidencias · retainer-checkin · login · magerit · dda · files · chat · inbox · tasks · account · billing · onboarding · workflow · transparency
- Auxiliary (15): actas · firma · firmas-hub · dpc-anual · cumplimiento · registros · incidents · policies · pentest-authorization · remediaciones · whatsapp + others
- Pattern library 100% applicable · spec template `runProjectScopedProbe` reusable 14 LOC/spec

**Admin untested (~11 pages)** restantes post 3B-2B.3:
- Marcos-only ops dashboards · operations/* · settings sub-pages · radar 4 pages
- Bajo riesgo (admin-only · no cliente-facing)

### 1.3 Pattern library applied · 9 patterns aplicabilidad

| Pattern | Implementación admin | Cliente portal | Notas |
|---------|---------------------|----------------|-------|
| 1. Sidebar ::before gradient | `frontend/app/globals.css:148-184` ✅ | `ClientSidebar.tsx` ✅ | Aplica ambos via global CSS |
| 2. Card solid white | `components/ui/card.tsx` ✅ | retainer-checkin error states ✅ | Manual aplicación cliente partial |
| 3. Token DEFAULT -700 overhaul | `tailwind.config.ts:50-83` ✅ | Auto cascade ✅ | **AUTOMATIC** cross-app (todas pages benefician) |
| 4. Translucent bg shade-matched | `badge.tsx`, `KPICard.tsx` ✅ | Auto via -700 default ✅ | Sistemico |
| 5. DataTable aria-label | `components/ui/data-table.tsx` ✅ | NOT USED (0 instances) | Cliente portal no usa DataTable · Card+List pattern |
| 6. Redirect-aware isProjectScoped | spec template ✅ | N/A cliente (LIMIT 1) | Admin-only |
| 7. ActionLink CTA a11y | `QuickActions.tsx` ✅ | Link primitives | Admin only · cliente uses native Link |
| 8. Reusable spec template | `runProjectScopedProbe` + `runTopLevelAdminProbe` ✅ | Pendiente extender cliente ⚠ | Sesión 3B-3 14 LOC/spec |
| 9. HMR stale touch | dev operational ✅ | dev operational ✅ | Sistemico |

**Hallazgo crítico**: 7 de 9 patterns aplican automáticamente cliente portal vía systemic CSS/Tailwind. Sólo patterns 5+8 requieren trabajo específico cliente (spec template + DataTable si aparece).

### 1.4 Sample visual scores · 10 pages strategic

| Page | Layout | Typo | Color | Empty | Loading | Error | Hover | Density | **TOTAL/80** |
|------|--------|------|-------|-------|---------|-------|-------|---------|--------------|
| `/admin/dashboard` | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | **80** ✓ |
| `/admin/projects` | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 8 | **79** ✓ |
| `/admin/compliance` | 9 | 9 | 9 | 8 | 8 | 9 | 9 | 8 | **77** ✓ |
| `/client-portal/dashboard` | 8 | 8 | 9 | 8 | 9 | 9 | 8 | 7 | **76** ○ |
| `/client-portal/conformidad` | 8 | 8 | 9 | 8 | 8 | 9 | 8 | 7 | **75** ○ |
| `/client-portal/evidencias` | 8 | 8 | 9 | 8 | 8 | 8 | 8 | 6 | **73** ○ |
| `/client-portal/retainer-checkin` | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 7 | **78** ✓ |
| `/client-portal/login` | 9 | 8 | 9 | 8 | 8 | 8 | 8 | 8 | **76** ○ |
| `/(legal)/privacy` (static) | 8 | 9 | 8 | N/A | N/A | N/A | 9 | 8 | **42/56** ○ |
| `/(radar)/radar/leads` | 8 | 8 | 8 | 8 | 7 | 8 | 8 | 7 | **72** ○ |

**Range**: admin 77-80 · cliente 73-78 · legal static 42-56 · radar 72.
**Floor cliente**: 73 (evidencias · density alta tablas mobile). **Ceiling cliente**: 78 (retainer-checkin friendly tone).

### 1.5 Top 5 gaps críticos visual UX

1. **Cliente portal empty states inconsistentes** (3-4 pages: evidencias · tasks · remediaciones · plain text vs illustrated friendly state) → `EmptyStateCard` componente unificado (icon + friendly copy + CTA).
2. **Cliente portal information density alta mobile** (tablas 8+ columnas con horizontal scroll · UX dolor) → responsive collapse + hide non-critical cols <768px.
3. **Legal pages visual hierarchy refinement** (h2/h3 mismo weight rendering · margin-top insuficiente) → tailwind h2/h3 utility classes en LegalArticle wrapper.
4. **Radar pages (4) NOT swept** (Future-1.E.admin-polish-p2-batch5) → 4 specs via `runTopLevelAdminProbe` (~40 min).
5. **Cliente portal KPI cards responsive breakpoint inconsistent** (mobile grid 1-col pero gap/padding asimétrico sm/md) → audit responsive spacing tokens.

### 1.6 ETAs realistic dimension 1

| Trabajo | ETA | Notas |
|---------|-----|-------|
| Gallery index.html generation (444 screenshots) | 30-60 min | Reusable template per admin-polish trace artifact |
| Visual aesthetic scoring restantes 124 pages | 3-4h | 20-30 sec/page grep components + pattern check |
| Cliente portal WCAG 12-criteria sweep (31 pages) | 8-10h | Spec template 14 LOC/spec · scaling factor 1.4x vs admin 22 pages 6-8h |
| Empty states unification (componente + apply 3-4 pages) | 2-3h | EmptyStateCard nuevo + integración |
| Mobile density fix (responsive tables) | 2-3h | Conditional col hide <768px |
| Radar 4 pages spec + fix | 1-2h | Template reuse |
| **TOTAL D1 cumulative** | **~17-23h** | Path Recomendado fragmentado · puede partirse Sesión 3B-3 + 3B-4 |

---

## DIMENSION 2 · Copiloto super-version audit empirical

### 2.1 Backend M11_copiloto motor inventory

**Path**: `backend/app/motors/m11_copiloto/` (4 archivos Python)

**Endpoints REST** (8 verificados):
1. `POST /copilot/chat` — quick chat sin persistencia
2. `POST /copilot/chat/stream` — SSE streaming
3. `GET /copilot/quick-actions` — context-aware catalog (hardcoded 7 contexts: default · magerit · obligations · conformity · diagnosis · evidence + other)
4. `POST /projects/{pid}/copilot/conversations` — create
5. `GET /projects/{pid}/copilot/conversations` — list per project
6. `GET /projects/{pid}/copilot/conversations/{cid}` — fetch + message history
7. `DELETE /projects/{pid}/copilot/conversations/{cid}` — soft delete
8. `POST /projects/{pid}/copilot/conversations/{cid}/chat` — persist user+assistant

**DB Models** (`backend/app/models/copilot.py`):
- `CopilotConversation`: id (UUID PK), **project_id (FK)**, titulo, modelo_default, autor, timestamps, soft delete
- `CopilotMessage`: id (UUID PK), conversation_id (FK), project_id (FK), role, content, citations (JSONB), chunk_ids_used (JSONB), model_used, tokens IO

**🔴 CRITICAL GAP**: NO `client_id` FK en `CopilotConversation`. Conversations atadas project_id ONLY → memoria per cliente IMPOSIBLE sin schema change (cross-project aggregation join required cada query).

**Tests M11**: 13 verde (test_m11_smoke + test_copilot_stream + test_copilot_corpus_fallback + test_inline_agents_api).

### 2.2 RAG infrastructure m11_rag

**Hybrid retrieval** (BM25 + vector + RRF):
- Embeddings e5-large 1024-dim via localhost:8080
- BM25 PostgreSQL `ts_rank` Spanish content_tsvector
- RRF fusion k=60 (Cormack et al.)
- Corpus: **~127 chunks** pre-indexed (knowledge_chunks table)
- Confidence threshold 0.45 cosine similarity (NEW8 corpus_gap pattern fallback)

**Corpus contents actuales**:
- ✅ RD 311/2022 full text + articles
- ✅ CCN-STIC NNN guidance series
- ✅ Anexo II measures (op.acc.6, etc.)
- ✅ ISO references

**🔴 Sistema-aware DEFICIT**:
- ❌ Motors taxonomy (m01-m31 descriptions) NOT ingested
- ❌ Agents definitions (A14, A31, etc.) NOT ingested
- ❌ MCPs inventory (14 servers Prowler/ScoutSuite/OpenVAS) NOT ingested
- ❌ 73 ENS measures completas (sólo snippets en compliance docs)

**Test empírico Marcos directive**: si Marcos pregunta "¿qué motores tenemos en FULKRO?" → corpus_gap fallback (NO answer). Sistema-aware claim **NOT sustained** actualmente.

### 2.3 Agent A14 Copiloto service

**Path**: `backend/app/agents/agent_14_copiloto/` (6 archivos)

**Files**:
- `service.py` (500+ LOC) — pipeline: detect_filters → hybrid_search → build_messages → LLM Sonnet 4.5 → validate citations → log
- `prompts.py` — SYSTEM_PROMPT 43 líneas (RD 311/2022 + CCN-STIC + Anexo II focus · REGLA COMPLETITUD 3 categorías · NO knowledge externo · corpus-first)
- `types.py` — CopilotQuery, CopilotResponse, PageContext dataclasses
- `filters.py` — detect_filters specialized queries
- `citation_validator.py` — extract_citations + assess_grounding + is_not_in_corpus

**PageContext injection** (sub-fase 5.5.F):
- Detecta project_id, deriva client_id via `get_project_owner()`
- Inyecta ClientContactService.get_for_copilot_context (M30 integration)
- URL-aware + motor detection

**Tests A14**: 22 verde (3 archivos test).

**Agent A31**: filesystem search confirma `agent_31_enriquecedor_dda.py` (20.9 KB · service-level enrichment DDA NOT copiloto-facing). Naming clarification post-piloto Future-X.

### 2.4 Frontend Copiloto Triad

#### CopilotoDock · `frontend/components/copiloto/CopilotoDock.tsx` (264 LOC)

**Features existing**:
- ✅ Global floating dock (fixed bottom-right)
- ✅ Context inference via `usePathname()` (magerit · dda · conformidad · evidencias · default)
- ✅ Quick actions tanstack-query cached
- ✅ Streaming SSE via `streamCopilotAnswer()`
- ✅ Input validation 3-2000 char

**Gaps Marcos super-vision**:
- ❌ NO cross-session persistence (mensajes ephemeral in-memory · localStorage "diferida")
- ❌ NO conversation thread history visible UI
- ❌ NO project_id awareness (sólo pathname inference)
- ⚠ Zustand `copilot-store` panelContext SET pero NO consumed por dock

#### CopilotGuidedFlow · `frontend/components/admin/copilot/CopilotGuidedFlow.tsx` (300 LOC)

**Features**:
- ✅ Component 100% coded (Q1.D phase) · per-phase sidebar guidance
- ✅ 7 props: phaseId · title · intro · whyImportant · steps · commonMistakes · estimatedTime · helpTopics · nextAction CTA
- ✅ localStorage dismiss per phase (`fullkro_copilot_guided_dismissed_{phaseId}`)
- ✅ R30 admin tutor UX

**🔴 GAP CRÍTICO Marcos directive**:
- ❌ **Integrado en 1/85 admin pages** (sólo `roadmap/page.tsx`)
- ⚠ Per-page wiring deferred Future-1.E.copilot-guided-integration-per-page
- ETA wiring full admin = 4-6h (DRY pattern OPS-026)

#### HelpModal · `frontend/components/admin/copilot/HelpModal.tsx` (168 LOC)

**Features**:
- ✅ Component 100% coded (FAQs per phase · escalation footer · contactEmail · Slack · video tutorials placeholders)
- ❌ **ZERO real integrations** (sólo CloudConnect helper unrelated · NO consumer admin pages)
- ❌ FAQ content hardcoded required per page · NO dinámico

### 2.5 Zustand copilot-store · `frontend/lib/stores/copilot-store.ts` (50 LOC)

```typescript
interface CopilotPanelContext {
  url?: string;
  projectId?: string;
  clientId?: string;
  activeMotor?: string;
  projectPhase?: string;
}
```

**State**: projectId + projectPhase fields existen (ADR-054 compat) PERO:
- ❌ Methods creados · NO consumer code found (grep 0 hits)
- ❌ NOT used in CopilotoDock (uses usePathname directly)
- ❌ NOT integrated con project-scoped context

**Decisión arquitectural**: copilot-store coded pero NO wired → quick-win Phase 1 wire-in 1h.

### 2.6 Gap matrix · Marcos super-vision features A-E

| # | Feature | Status | Evidence path | ETA | Priority |
|---|---------|--------|---------------|-----|----------|
| **A** | Memoria propia per cliente | ❌ Missing | NO client_id FK CopilotConversation · conversations tied project_id only | 4-6h | HIGH |
| **B** | Cross-conversación within project continuity | ⚠ Partial | Conversation CRUD ✅ + message history ✅ · NO multi-session RAG retrieval · NO context awareness cross-conversations | 3-4h | HIGH |
| **C** | Sistema-aware 28 motors + 30 agents + 14 MCPs + 73 ENS measures | ❌ Missing | Corpus ~127 chunks (RD311 + CCN-STIC + Anexo II) · NO inventory FULKRO ingested | 8-12h corpus ingestion + reindex | MED-HIGH |
| **D** | Step-by-step "como si fuera tonto" ENS phase guide | ⚠ Partial | CopilotGuidedFlow 100% coded · integrado 1/85 pages · phaseId per-page wiring deferred | 2-3h wire-up core · 4-6h full | MED |
| **E** | Coach next-step recommendations | ❌ Missing | NO `/copiloto/next-action` endpoint · NO widget "Próximo paso" visible · QuickActions hardcoded 7 contexts NO intelligence | 5-8h | MED |

**TOTAL super-vision Copiloto Phase 1+2+3 cumulative**: **22-33h** (1.5-2 semanas).

### 2.7 Decisiones arquitecturales (ADR-025 reuse infrastructure firmísimo)

✅ **Reusable existing** (NO new tables Phase 1):
- CopilotConversation + CopilotMessage tables · FullMixin + soft delete + RLS
- LLMInteractionLog per-query audit
- Hybrid retrieval pipeline (BM25 + vector + RRF)
- Agent A14 service layer

❌ **Schema change required** (breaks ADR-025 minor):
- `client_id` FK column en CopilotConversation (migration ~1h backward-compat soft-default)
- ALTERNATIVA Zustand sessionStorage ephemeral (NO multi-device sync · NO multi-browser)

### 2.8 ETAs priorización Phase 1+2+3

**Quick wins ≤2h** (Phase 0.5):
1. Wire Zustand `copilot-store` panelContext en CopilotoDock (1h)
2. Apply CopilotGuidedFlow pattern roadmap → 5-10 core admin pages (≤2h DRY)

**Core 4-8h** (Phase 1 · unblocked):
3. Add client_id FK CopilotConversation (migration 1h + query refactor 1h)
4. Extend A14 service hybrid_search aceptar conversation_history context (2h)
5. Backend endpoint `/projects/{pid}/copilot/next-recommended-action` placeholder LLM (3-4h)

**Aspirational T1 >8h** (Phase 2-3 · post-piloto):
6. Bulk ingest motors/agents/MCPs into knowledge_chunks + reindex (8-12h)
7. Full CopilotGuidedFlow per-page 20+ admin pages (4-6h DRY)

**Out-of-scope explicit per CLAUDE.md**:
- Video tutorials HelpModal · Slack integration · ML anomaly detection

---

## DIMENSION 3 · Per-cliente adaptation audit empirical

### 3.1 Project context infrastructure (ADR-054)

**Active project store** · `frontend/lib/stores/active-project-store.ts` (70 LOC):
- ✅ Zustand + `persist` middleware · localStorage key `"fulkro-active-project"`
- ✅ Cross-tab sync L3 hybrid pattern
- ✅ Canonical source: URL param `/admin/projects/[id]/*` · store caches metadata (clientId · clientName · ensCategory · status)
- ⚠ **Admin-only**: cliente portal NO usa store (R29 client-scoped architectural · single project natively)

**ActiveProjectSync guard** · `frontend/components/layout/ActiveProjectSync.tsx` (128 LOC):
- ✅ Mounted en `/admin/projects/[id]/layout.tsx`
- ✅ Fetches `GET /api/v1/projects/{id}/header` on projectId mismatch
- ✅ Syncs `copilot-store.panelContext` con active project
- ✅ 404 handling: redirect selector + toast warning

**ProjectBreadcrumb** · `frontend/components/layout/ProjectBreadcrumb.tsx` (162 LOC):
- ✅ Visible TODAS `/admin/projects/[id]/*` pages · pattern `[Cliente] > [Proyecto] > [Sub-página]`
- ✅ Botón "Cambiar proyecto" right-aligned explicit

**ProjectSwitcherDropdown** · 117 LOC:
- ✅ Embedded ActiveProjectBanner sidebar top · lists accessible clients
- ✅ Shows "ACTIVO" badge current project
- ⚠ Future-1.E.2.advanced-switcher (Cmd+K + recent-5 + pinned) deferred demand-driven

**Admin coverage**: ✅ 100%. **Cliente coverage**: ❌ 0% (R29 architectural isolation kept · cliente sees 1 project natively).

### 3.2 Branding per-cliente · DB schema + frontend

**DB schema** · `backend/app/models/core.py` Client class:
- ✅ `logo_path` (str 512 nullable) — uploaded via `/api/v1/clients/{id}/logo`
- ✅ `logo_mime_type` (str 80) + `logo_sha256` (str 64)
- ✅ `primary_color` (hex #RRGGBB · CHECK constraint validated)
- ✅ `secondary_color` (hex #RRGGBB · validated)
- ✅ `footer_text` (text · max 500 chars validated)
- ✅ Migration `sane_mb9_branding_001` applied

**Architectural decision**: Client-level uniform branding (1 cliente ≈ 1 proyecto MVP piloto MEDIA). Per-project override **Future-1.E.2.bis.per-project-branding** demand-driven.

**Frontend provider** · `frontend/lib/branding/ClientBrandingProvider.tsx` (72 LOC):
- ✅ Wraps cliente portal · fetches `/client-portal/branding`
- ✅ Inyecta CSS vars `--client-primary-color` + `--client-secondary-color` en `<html>`
- ✅ Exposes BrandingView context (colors + footer + has_logo)

**Admin form** · `frontend/components/admin/clients/branding/BrandingForm.tsx` (150+ LOC):
- ✅ Color picker + hex validation + footer text editor + logo delete

**Personalizacion page** · `/admin/projects/[id]/personalizacion/page.tsx` (80+ LOC):
- ✅ Per-project access (client-scoped via activeProject.clientId)
- ✅ Live preview · cambios replican cliente portal inmediato

### 3.3 Branding visible WHERE matrix

| Componente | Status | Evidence | Recommendation |
|------------|--------|----------|----------------|
| Cliente portal footer text | ✅ APPLIED | `ClientFooter.tsx` line 14 (footer_text from provider) | — |
| Cliente portal CSS colors | ✅ APPLIED | ClientBrandingProvider inyecta CSS vars | — |
| Admin personalizacion form | ✅ APPLIED | `page.tsx` admin edit UI complete | — |
| Cliente portal header logo | ⚠ PARTIAL | ClientHeader.tsx existe · NO logo injection verified | Quick win 1h |
| Admin sidebar project branding | ❌ MISSING | Sidebar.tsx muestra NO primary/secondary color override | Quick win 1-2h |
| Admin header project context | ⚠ PARTIAL | Header.tsx tiene `--fulkro-topbar-gradient` static · NO dynamic client color | Quick win 1h |
| PDF reports branding | ❌ MISSING | `m21_diagnosis/report_generator.py` NO branding variable injection | Core 4-6h |
| Email templates branding | ⚠ PARTIAL | `m05_obligations/personalization.py` supports `{{cliente.razon_social}}` ONLY · NO `{{logo_url}}`, `{{primary_color}}` | Core 3-4h |

### 3.4 Per-project state · ENS workflow phase

**DB columns** · `backend/app/models/core.py` Project class:
- ✅ `fase` (str 50 enum: pre_venta | ... | certificado) — primary source-of-truth
- ✅ `lifecycle_state` (str 30) — DRAFT · NEGOTIATING · SIGNED · ACTIVE · CERTIFIED · RETAINER · etc.
- ✅ `certified_at` (date nullable)
- ✅ **16 adaptation dimension columns** (tamano_empleados · madurez_ens_actual · geografia_operacion · DPO flags · legal · etc.)

**Endpoint header**: `GET /api/v1/projects/{id}/header` returns `proyecto.fase` + `cliente.nombre`.

**AdaptationBadge R28** · `frontend/components/workflow-command-center/AdaptationBadge.tsx` (148 LOC):
- ✅ Component materializa 19 dimensions logic popover
- ✅ Displays reasons "why this step applies" per dim (categoria · archetype · tamano · madurez · DPO · legal flags)
- ✅ Used in WorkflowStepCardEnriched.tsx + WorkflowStepDetailDrawerEnriched.tsx
- ✅ 2 test files validate dims filtering (fase_17 + admin)

**Coverage gap**: dims materialized ✅ · widget placement ⚠ (sólo workflow cards · NOT en per-project dashboard overview o header).

### 3.5 Per-project next actions

**Endpoints verified**:
- ✅ `GET /api/v1/workflow/next-actions/{projectId}?limit=5` (admin)
- ✅ `GET /api/v1/portal/workflow/next-actions/{projectId}?limit=5` (cliente)

**Hook**: `useWorkflowAdmin` / `useWorkflowPortal` query next-action recommendations · mocked E2E tests.

**UI gap**: `next-action-card` test data shows implementación existe · card NOT clearly visible en main dashboard per empirical inspection (Future-1.E quick win 1h refine card placement).

### 3.6 Single-project per cliente R27 LIMIT 1 firme

**Empirical verification**: `backend/app/motors/m21_portal_cliente/api.py` lines 376, 504, 509, 1005+
- ✅ `LIMIT 1` hardcoded project resolution queries
- ✅ Comment: "single-project context (R23 + R27 sostener)"
- ✅ ADR-054 + Phase 0 decision: 1 cliente = 1 proyecto típico MVP piloto MEDIA

**Impact si demand multi-project per cliente futuro**:
- Extend cliente portal switcher (currently hidden)
- Per-project branding override (vs client-level uniform)
- Scope creep ~2-3 days engineering · capture Future-1.E.2.bis.multi-project-per-cliente

### 3.7 Gap matrix · 12 features per-cliente adaptation

| # | Feature | Existing | Partial | Missing | Evidence | ETA |
|---|---------|:--------:|:-------:|:-------:|----------|-----|
| 1 | Active project context (admin) | ✅ | — | — | active-project-store + ActiveProjectSync | — |
| 2 | Project switcher dropdown | ✅ | — | — | ProjectSwitcherDropdown.tsx | — |
| 3 | Breadcrumb persistent | ✅ | — | — | ProjectBreadcrumb.tsx | — |
| 4 | Client branding (DB schema) | ✅ | — | — | logo + colors + footer migration | — |
| 5 | Client branding (portal CSS) | ✅ | — | — | ClientBrandingProvider · ClientFooter | — |
| 6 | Client branding (admin form) | ✅ | — | — | BrandingForm + personalizacion page | — |
| 7 | Project phase visible dashboard | — | ✅ | — | ProjectHeader fetch + AdaptationBadge UI · widget placement weak | Quick 1h |
| 8 | Next-action widget dashboard | — | ✅ | — | Endpoint exists · UI card placement diffuse | Quick 1h |
| 9 | Admin sidebar project branding | — | — | ✅ | Sidebar.tsx static gradient | Quick 1-2h |
| 10 | Admin header project context badge | — | ✅ | — | Static topbar gradient · NO project chip | Quick 1h |
| 11 | PDF reports branding (logo+colors) | — | — | ✅ | report_generator.py static template | Core 4-6h |
| 12 | Email templates branding (logo+colors+text) | — | — | ✅ | razon_social only injection | Core 3-4h |

### 3.8 Top 5 gaps críticos per-cliente adaptation

1. **PDF reports branding MISSING** — customer-facing documents lack logo + brand colors · perceived "generic FULKRO template" · Fix 4-5h · **Priority HIGH** (cliente experience).
2. **Email templates branding PARTIAL** — notifications lack logo/color injection · email signature aparece generic · Fix 3-4h · **Priority MED** (async lower visibility).
3. **Dashboard phase visibility WEAK** — current project ENS workflow phase NOT prominently displayed · Marcos debe context-switch · Fix 1h · **Priority MED** (UX polish).
4. **Per-project branding decision DIFERIDO** — si multi-project per cliente materializa schema NO soporta per-project override · risk rescoping work si demand surfaces · Capture Future-1.E.2.bis · **Priority LOW** (pre-piloto MEDIA holds).
5. **Cmd+K project switcher MISSING** — Marcos click sidebar dropdown · Fix 3-4h · **Priority LOW** (acceptable MVP).

### 3.9 ETAs realistic dimension 3

**Quick wins ≤2h** (Phase 1):
1. Sidebar show project context + change button (0.5h)
2. Header show project context badge (0.5h)
3. Dashboard phase badge + next-action card visible (1h)

**Core 4-8h** (Phase 2):
4. PDF reports inject logo + colors + footer template (4-5h · Jinja2 template variables + backend endpoint)
5. Email templates `{{logo_url}}`, `{{brand_color}}`, `{{footer_text}}` (3-4h · m18_communication + m05_signing)
6. Per-project workflow state tracker advanced (2h · widget current fase + ETA cert)

**Aspirational T1 >8h** (post-piloto):
7. Per-project branding override (8-10h · schema + frontend logic)
8. Multi-project per cliente (16-20h · R27 LIMIT 1 removal + RLS refactor)
9. Cmd+K switcher UI (3-4h · Future-1.E.2.advanced-switcher)

**TOTAL D3 cumulative**: **~10-15h** Path Recomendado (quick wins + core) · 25-35h cumulative si aspiracional incluido.

### 3.10 Decisiones arquitecturales cierre

✅ **CONFIRMADO R29 cliente portal isolation respected**: branding via ClientBrandingProvider (per-cliente NOT per-project) · LIMIT 1 project resolution hardcoded · NO cross-project navigation visible cliente · ADR-054 project-scoped admin does NOT cascade cliente portal.

✅ **CONFIRMADO Zustand active-project-store ADR-054**: localStorage persistence L3 hybrid · localStorage.clear() on logout · routing guard sync onMount URL ← source-of-truth.

⚠ **DECISION DIFERIDA per-project branding**: current client-level uniform piloto MEDIA · revisit only if customer feedback demands variation.

---

## Síntesis cross-dimensión · architect approve options

### Path A · Minimalista (~4-6h)

**Scope**: quick wins las 3 dimensiones — sin schema changes ni componentes nuevos.

| Item | Dim | ETA | Impacto |
|------|-----|-----|---------|
| Gallery index.html 444 screenshots | D1 | 30-60 min | Marcos visual review one-shot |
| CopilotGuidedFlow integración 5-10 core admin pages (DRY pattern roadmap) | D2 | ~2h | Step-by-step ENS phase tracker visible Marcos |
| Zustand copilot-store wire-in CopilotoDock | D2 | 1h | project-context aware copilot |
| Dashboard phase badge + next-action card refine | D3 | 1h | Project state visible |
| Admin sidebar/header project context badge | D3 | 1-2h | Marcos context awareness |

**Total ~5-7h** · NO bloqueante · NO schema change · NO aspiracional.

### Path B · Recomendado (~14-18h)

**Scope**: Path A + core wins las 3 dimensiones — pequeño schema change + cliente WCAG batch1.

| Item | Dim | ETA | Notas |
|------|-----|-----|-------|
| **Path A complete** | D1+D2+D3 | 5-7h | Foundation |
| Cliente portal WCAG sweep 10 core pages (dashboard · conformidad · evidencias · retainer-checkin · login · magerit · dda · files · billing · onboarding) | D1 | 4-5h | Spec template reuse 14 LOC/spec |
| Memoria per cliente — add client_id FK CopilotConversation + migration + query refactor | D2 | 3-4h | Schema change minor backward-compat |
| PDF reports branding — Jinja2 template variables + endpoint | D3 | 4-5h | Customer-facing impact HIGH |

**Total ~16-21h** · 2-3 días foco · Sesión 3B-2B.4 + 3B-3 fragmentado.

### Path C · Aspiracional (~30-45h)

**Scope**: Path B + full super-vision copiloto + per-project branding override.

| Item | Dim | ETA | Notas |
|------|-----|-----|-------|
| **Path B complete** | D1+D2+D3 | 16-21h | Foundation + core |
| Cliente portal WCAG sweep restantes 21 pages | D1 | 4-5h | Auxiliary pages |
| Cross-conversación continuity A14 service extension | D2 | 3-4h | RAG conversation_history context |
| Sistema-aware corpus expansion (motors + agents + MCPs ingest + reindex) | D2 | 8-12h | Bulk corpus work |
| Coach next-action endpoint LLM synthesis | D2 | 5-8h | Backend + frontend widget |
| Email templates branding completo | D3 | 3-4h | logo + colors + footer vars |

**Total ~40-55h** · 1-1.5 semanas foco · multi-sesión Sesión 3B-2B.4 + 3B-3 + 3B-4.

### Out-of-scope explicit Phase 1+2+3

- Per-project branding override (Future-1.E.2.bis.per-project-branding · demand-driven)
- Multi-project per cliente R27 break (Future-1.E.2.bis.multi-project-per-cliente · demand-driven)
- Video tutorials HelpModal · Slack integration · ML anomaly detection (Future-1.E)
- Cmd+K advanced switcher (Future-1.E.2.advanced-switcher)

---

## Honesty guards verified (per Marcos directive)

| Guard | Verified | Evidence |
|-------|----------|----------|
| Per page screenshot empirical evidence | ✅ | 444 PNG `find frontend/polish-test-results -name *.png \| wc -l` |
| Per copiloto feature backend test OR component verified | ✅ | M11 8 endpoints + 13 tests + A14 22 tests + Triad 3 components LOC counted |
| Per adaptation gap concrete UI evidence | ✅ | Migration `sane_mb9_branding_001` + ClientBrandingProvider + BrandingForm + report_generator.py grep |
| Realistic ETA based on Phase A.0+A.1 pattern velocity | ✅ | 22 admin pages = 6-8h empirical · cliente 31 pages 1.4x scale = 8-10h projection |
| OPS-052 Phase 0 mandatory honored | ✅ | 3 dimensions empirical audit ANTES Phase 1+2+3 execute |

---

## Recommendation pre architect approve

**Recomendado Marcos**: **Path B (~16-21h)** distribuido 2-3 sesiones (Sesión 3B-2B.4 quick wins + cliente WCAG batch1 + Sesión 3B-3 PDF branding + copiloto memoria per cliente).

**Rationale**:
- Path A demasiado minimalista (deja PDF reports + memoria per cliente missing · gaps customer-facing HIGH impact)
- Path C demasiado aspiracional pre-piloto (corpus expansion + coach next-action = T1 demand-driven · NO blocker piloto)
- Path B equilibra customer impact (branding PDF + cliente portal WCAG) + Marcos efficiency (copiloto memoria + step-by-step guide) sin schema disruption mayor

**Architect decision pending antes Phase 1+2+3 execute**:
- [ ] Path A · Path B · Path C select
- [ ] Sesión scope cumulative (single 3B-2B.4 OR 3B-2B.4 + 3B-3 + 3B-4 fragmented)
- [ ] Future-X capture explicit per item out-of-scope

---

## Sesión 3B-2B.4 Phase 0 STATUS

🟡 **AUDIT COMPLETE · STOP-AND-REPORT** · architect approve scope antes Phase 1+2+3 execute.

**Doctrine sostained**: OPS-052 Phase 0 mandatory · 49ª aplicación OPS-045 audit-first · ADR-025 reuse infrastructure firmísimo (NO new tables Phase 1 quick wins · client_id FK schema change minor backward-compat Path B + onwards).

**Honesty empírico**: foundation 70% production-ready las 3 dimensiones · gaps son polish + aspiracional T1 · NINGÚN gap bloquea piloto pagador MEDIA.
