# Ejecutable 8 · Pasada 3 · Frontend Deep Dive

> Inventario empírico exhaustivo de `frontend/` basado SOLO en output real de comandos (find/ls/Read). Fecha: 2026-05-30. Filesystem WSL-sobre-Windows.

## 1. Comandos ejecutados (evidencia empírica)

| Comando | Resultado |
|---------|-----------|
| `find frontend/app \( -name page.tsx -o -name page.ts \) \| wc -l` | **163** pages |
| `find frontend/app -name layout.tsx \| wc -l` | **9** layouts |
| `find frontend/components -name '*.tsx' \| wc -l` | **408** componentes .tsx |
| `find frontend/components -name '*.ts' \| wc -l` | 2 .ts adicionales |
| `find frontend/hooks -type f \( -name '*.ts' -o -name '*.tsx' \) \| wc -l` | **61** hooks |
| `find frontend/lib/api -maxdepth 1 -name '*.ts' \| wc -l` | **83** módulos API client |
| `ls frontend/store / frontend/types` | NO existen (top-level) |
| `wc -l frontend/middleware.ts` | 213 LOC |

## 2. Estructura `frontend/app` (route groups / portales)

App Router con 7 route groups + páginas root no-agrupadas:

```
frontend/app/
├── (admin)/admin/...                 92 pages   [owner-gated middleware]
│   ├── dashboard, clients, projects, compliance, pipeline, retainers,
│   │   meetings, finance, operations, llm-observability, system-health,
│   │   workflow-command-center, magic-links, magerit-analyses, ...
│   └── projects/[id]/...  (~57 sub-pages project-scoped: dda, magerit,
│       plan, evidence, dossier, audit, conformity, contratos, mcps, ...)
├── (client-portal)/client-portal/... 38 pages   [cliente-role-gated]
│   ├── dashboard, dda, magerit, plan, evidencias, conformidad,
│   │   cumplimiento, firmas-hub, firmas-pendientes, cloud-connections,
│   │   certificacion, registros/[tipo], settings/mfa, workflow, ...
├── (portal)/...                       15 pages   [magic-link token-gated, NO middleware]
│   ├── auditor-portal/[token]/...    12 pages (summary, dda, magerit,
│   │     evidence, plan, e041, audit, audit-log, documents, pentest,
│   │     draft-report, audit/dda-evidence-gaps)
│   ├── pentester-portal/[token]       1
│   ├── remediation/[token]            1
│   └── verify-auth/[token]            1
├── (radar)/radar/...                  4 pages    [owner+ens_radar_owner-gated]
│   └── (index), clusters, leads, runs
├── (legal)/...                        8 pages    [público]
│   └── cookies, derechos-rgpd, dpa-template, imprint, privacy,
│       sub-processors, terms, trust
├── (public)/...                       2 pages    [público token]
│   └── download/[token], sign/[token]
└── root no-agrupado                   4 pages
    ├── page.tsx (raíz /)
    ├── login/page.tsx
    ├── forbidden/page.tsx
    └── docs/verify-signature/page.tsx
```

## 3. INVENTARIO REAL pages por portal/sección

| Portal / Sección (route group) | # pages | Gating |
|--------------------------------|--------:|--------|
| `(admin)` — admin owner | **92** | middleware: role=owner |
| `(client-portal)` — portal cliente | **38** | middleware: role cliente (rw) |
| `(portal)` — auditor/pentester/remediation/verify-auth | **15** | magic-link token URL (NO middleware) |
| &nbsp;&nbsp;↳ auditor-portal/[token] | 12 | magic-link AUDITOR_PORTAL_ENAC |
| &nbsp;&nbsp;↳ pentester-portal / remediation / verify-auth | 3 | magic-link token |
| `(radar)` — ENS Radar | **4** | middleware: owner + is_ens_radar_owner |
| `(legal)` — páginas legales | **8** | público |
| `(public)` — download/sign token | **2** | público token |
| root no-agrupado (/, login, forbidden, docs/verify-signature) | **4** | público / mixto |
| **TOTAL** | **163** | |

(Suma de control: 92+38+15+4+8+2+4 = 163 ✅ coincide con `wc -l`.)

## 4. Layouts (9) — materializan portales

```
layout.tsx                                          (root global)
(admin)/layout.tsx
(admin)/admin/projects/[id]/layout.tsx              (project-scoped sidebar)
(admin)/admin/workflow-command-center/projects/[id]/layout.tsx
(client-portal)/client-portal/layout.tsx
(portal)/layout.tsx
(legal)/layout.tsx
(public)/layout.tsx
(radar)/layout.tsx
```

## 5. Componentes (408 .tsx + 2 .ts · ~95 subdirectorios)

Subdirectorios principales bajo `frontend/components/` y propósito aparente:

| Subdir | Propósito aparente |
|--------|--------------------|
| `ui` | primitivas shadcn/ui (botones, cards, tablas, dialogs) |
| `admin` (+ audit, clients, clients/branding, copilot, feature-flags, finance, projects, retainers) | componentes admin portal |
| `client-portal` (+ ~20 subdirs: actas, compliance, conformidad, dashboard, dda, dpc-anual, files, firmas-hub, footer, header, incidents, inline-agents, magerit, pentest, policies, remediations, retainer-checkin, tutorial, whatsapp, workflow) | portal cliente |
| `auditor-portal` (+ annotations, clarifications, views) | portal auditor ENAC |
| `pentester-portal`, `remediation-portal`, `verify-auth`, `sign-flows`, `public` | portales token-gated |
| `ens-radar` | ENS Radar captación leads |
| `copilot` / `copiloto` / `copiloto-cliente` | copilotos LLM (admin + cliente) |
| `m03_dda`, `m14_contracts`, `m28_change_governance` | componentes motor-específicos |
| `agents`, `mcps`, `verification`, `discovery`, `diagnosis`, `dimensions`, `documents`, `live-records`, `magic-links`, `notifications`, `observability`, `onboarding`, `operations`, `pipeline`, `project`, `project-wizard`(+steps), `providers`, `renewal`, `retainer`, `roles`, `signatures`, `shared`(+signing), `transparency`, `workflow`(+command-center, deliverables, guide-client), `workspace`, `idms`, `cloud-connectors`, `conformity`, `contracts`, `changes`, `dashboard`, `data`, `dev`, `exit`, `feature-flags`, `financial`, `legal`, `layout`, `brand`, `auth`, `alerts`, `audit`, `audit-dry-run`, `admin-meetings` | resto dominio funcional |

## 6. Hooks · lib/api · stores · types

- **Hooks**: 61 archivos en `frontend/hooks/`.
- **lib/api**: **83** módulos client (uno por dominio/motor). Ejemplos: `ens-radar.ts`, `dda.ts`, `magerit.ts`, `auditor-portal.ts`, `simulacro-pre-enac.ts`, `audit-accompaniment.ts`, `signing.ts`, `notifications-dlq.ts`, `client-mfa.ts`, `cloud-connectors-admin.ts`/`-client.ts`, `copiloto-admin.ts`/`-cliente.ts`, etc.
- **lib top-level dirs**: ~44 directorios bajo `frontend/lib/` (admin-*, client-*, api, auth, branding, contexts, ens-radar, legal, m_live_records, notifications, portal-workflow, schemas, stores, types, etc.).
- **Stores (Zustand)**: 3 archivos en `frontend/lib/stores/`: `active-project-store.ts`, `auth-store.ts`, `copilot-store.ts`. NO existe `frontend/store/` top-level.
- **Types**: 1 archivo en `frontend/lib/types/`. NO existe `frontend/types/` top-level.

## 7. Middleware / portales auth (frontend/middleware.ts · 213 LOC)

Protección server-side vía JWT Ed25519 (jose, algo EdDSA) verificado con `FULKRO_AUTH_PUBLIC_KEY`, cookie httpOnly `fulkro_session`:

- `/admin/*` → requiere `isAdminRole` (owner). Cliente → redirect a `/client-portal/dashboard`.
- `/radar/*` → requiere owner **+** `is_ens_radar_owner` (else 403 /forbidden).
- `/client-portal/*` → requiere role cliente; owner → redirect `/admin/dashboard`. Excepciones públicas: `/client-portal/login`, `/client-portal/forgot-password`.
- `/` raíz → redirect según role (admin→/admin/dashboard, cliente→/client-portal/dashboard, else /login).
- Resto (sign, download, auditor-portal, pentester-portal, remediation, verify-auth, legal) → `NextResponse.next()` **público** (gating real por magic-link token en la URL, NO en middleware). Referencias ADR-013/015/018.

`next.config.mjs` (37 LOC): `reactStrictMode`, rewrite `/api/:path*` → `FULKRO_BACKEND_URL` (default localhost:8000), headers seguridad básicos (X-Frame-Options DENY, nosniff, Referrer-Policy, Permissions-Policy). CSP estricta DIFERIDA (TODO-SEC-CSP-001).

## 8. Los 4 portales/audiencias y su separación en App Router

| Audiencia | Route group | Auth |
|-----------|-------------|------|
| **Admin (Marcos owner)** | `(admin)` | middleware role=owner |
| **Cliente** | `(client-portal)` | middleware role cliente |
| **Auditor ENAC** | `(portal)/auditor-portal/[token]` | magic-link token (NO middleware) |
| **Radar (captación leads)** | `(radar)` | middleware owner + is_ens_radar_owner |

Portales auxiliares token-gated adicionales: pentester (`(portal)/pentester-portal`), remediación (`(portal)/remediation`), verify-auth, download/sign (`(public)`), legal (`(legal)` público).

## 9. CIFRAS EMPIRICAL (resumen)

- **Pages total: 163** (admin 92 · client-portal 38 · portal 15 · radar 4 · legal 8 · public 2 · root 4)
- **Layouts: 9**
- **Componentes: 408 .tsx (+2 .ts) en ~95 subdirs**
- **Hooks: 61**
- **lib/api modules: 83**
- **Stores Zustand: 3** · **lib/types: 1 archivo** · **lib top-dirs: ~44**

## 10. Discrepancias vs cifras stale

- **CLAUDE.md "120+ páginas activas"** → REAL **163 pages** (subestimado; +35% sobre el "120+").
- **CLAUDE.md "331+ componentes TSX"** → REAL **408 .tsx** (subestimado; +23%).
- **CLAUDE.md "52+ hooks"** → REAL **61 hooks** (subestimado).
- **CLAUDE.md "54+ módulos lib/api/*"** → REAL **83 módulos** lib/api (subestimado ~+54%).
- **CLAUDE.md "125+ archivos lib/*"** → no recontado por archivo (sólo ~44 dirs); no contradicho.
- **README "5-7 pages a conectar"** → NO verificable empíricamente con find (es una métrica de "conectividad backend", no de existencia de archivos); las 163 pages existen como archivos. Métrica probablemente stale/orientativa, NO refleja el inventario real de ficheros.
- **CLAUDE.md "4 portales (admin/cliente/auditor/radar)"** → CONFIRMADO + portales auxiliares token (pentester, remediation, verify-auth, public/sign-download, legal).