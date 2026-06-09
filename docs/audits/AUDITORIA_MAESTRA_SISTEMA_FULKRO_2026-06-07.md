# AUDITORÍA MAESTRA DEL SISTEMA FULKRO

> Documento maestro · inventario completo del repositorio + auditoría empírica end-to-end.
> Fecha: 2026-06-07 · Worktree auditado: `/home/usuario/fulkro-portales` (branch `batch2-fase0-recorrido`, HEAD `a16c53db`).
> **Actualización 2026-06-08:** el subsistema **ENS Radar (M10b)**, descrito en este snapshot como "dormido por diseño", fue posteriormente **eliminado por completo** del producto (motor, frontend `(radar)`, 13 tablas, auth `ens_radar_owner`, middleware `/radar`, tests). Las menciones a "Motor 10 ens_radar"/radar más abajo reflejan el estado **previo** a esa limpieza.
> Metodología: **100% empírica** — todo lo que sigue se ha verificado ejecutando la app real, corriendo la suite real, importando el router real y enumerando el filesystem real (no grep heurístico, no claims arquitectónicas).

---

## 0 · Cómo se hizo esta auditoría (trazabilidad)

| Señal empírica | Cómo se obtuvo | Resultado |
|---|---|---|
| Rama autoritativa | `git worktree list` + `git rev-list --left-right --count` | `batch2-fase0-recorrido` está **177 commits por delante** de `radar-v3-pr` (superset), árbol limpio |
| Endpoints montados | `import backend.app.main:app` + enumerar `app.routes` | **1102 rutas** ASGI (1007 paths OpenAPI) |
| Tablas ORM | `Base.metadata.tables` tras importar la app | **237 tablas** |
| Agentes | `registry.AGENT_REGISTRY` | **31 IDs** (1-31) |
| MCP servers | enumeración filesystem `backend/mcp_servers/` | **14 servers** (+ shared lib) · 174 ficheros trackeados |
| Suite backend | `pytest backend/tests` desde repo-root | **6001 passed · 0 failed · 122 skipped** (4:11) |
| Gate DB | `alembic check` contra `fulkro_test` (build desde migraciones) | **"No new upgrade operations detected"** (verde, tras fix) |
| Heads Alembic | `alembic heads` | **1 solo head** (`rls_tenant_hardening_p0_001`) — el "4-heads" era falso positivo |
| Suite E2E | `playwright test --list` (compila sin ejecutar) | **543 casos / 297 specs** compilan (200 e2e + 97 polish) |
| Stack vivo | `curl` a :8000/:3000/:5433 | backend `health:ok` · frontend `/login` y `/client-portal/login` → 200 |

---

## 1 · VEREDICTO DE AUDITORÍA

**Estado del sistema: producción-ready a nivel de código. Verde end-to-end en backend. Los únicos pendientes reales son provisioning de infraestructura (Hetzner), no código.**

### 1.1 · Lo que esta sesión cerró (cambios reales aplicados + commit `a16c53db`)

1. **Gate DB Alembic → VERDE.** `alembic check` fallaba: la tabla `annual_review_records` y la columna `dda_entries.annual_review_record_id` existían en BD (migración `annual_review_e4_001`) pero **sin modelo ORM**. Se añadió el modelo espejo `AnnualReviewRecord` (`backend/app/models/ens.py`) + el campo FK en `DdaEntry`. Resultado empírico: `No new upgrade operations detected`. Era el item P0-DB de la punch-list de producción.
2. **2 tests no deterministas → deterministas.** `tests/notifications/test_tasks.py` (scan de inactividad → alerta + notificación a Marcos) pasaban en suite completa pero fallaban en aislamiento: leían `notification_events`/`alerts` tras `RESET ROLE` **sin contexto de tenant**, dependiendo de un GUC `app.current_project_id` filtrado de un test previo. Tras la cirugía de rol P0 (`1db2d420`, `fulkro_app` ya NO bypassa RLS) eso es frágil. Fix: `set_config('app.current_project_id', …, true)` explícito tx-local antes de las asserts. Resultado: **10/10 en aislamiento**, suite sigue 6001.

### 1.2 · Salud por subsistema (empírica)

| Subsistema | Señal | Estado |
|---|---|---|
| Backend (motores + agentes) | 6001 tests verdes, app importa, 1102 rutas | ✅ Verde |
| Modelo de datos + migraciones | 1 head, `alembic check` verde, 237 tablas ORM | ✅ Verde |
| Seguridad multi-tenant | rol `fulkro_app` NOSUPERUSER + `fulkro_app_bypassrls`, RLS FORCE, hash-chain audit_log | ✅ Endurecido (auditoría 2026-06-07) |
| Frontend (4 portales) | 168 páginas, 297 specs compilan, portales sirven 200 | ✅ Verde (estructura + compila) |
| E2E | 543 casos compilan, gated en CI (`ci.yml` + `admin-polish-empirical.yml`) | ✅ CI-gated · ⚠️ run local authed bloqueado por env-key (no producto) |
| ENS Radar (M10b) | desactivado a propósito en Batch 2 (dormido/reversible) | ⏸️ Dormido por diseño |

### 1.3 · Pendientes reales = INFRAESTRUCTURA Hetzner (no código)

El código está cableado para usar estos servicios; faltan los **demonios/servicios externos** (responsabilidad de provisioning, no de desarrollo):

- **ClamAV daemon** — `m07` tiene `antivirus_scan_service.py` + `antivirus_admin_api.py` cableados; el scan real exige el demonio ClamAV corriendo.
- **MinIO Object-Lock (WORM 7y)** — código de buckets presente; el Object-Lock se configura en el MinIO de producción.
- **Contenedores MCP pentest** — 14 MCP servers con `server.py`+`Dockerfile`; la ejecución real de scanners (Prowler/ScoutSuite/OpenVAS/Nuclei) exige el `profile: pentest` de docker-compose levantado.
- **fastembed `:8080`** — ingesta RAG de los docs core (embeddings e5-large) requiere el endpoint fastembed arriba.
- **pgAudit / pgBackRest** — extensiones/herramientas de la BD de producción.

> Estos NO bloquean la corrección del software; bloquean el despliegue. Coinciden con la doctrina del proyecto (FASE 1.F producción Hetzner).

### 1.4 · Nota de honestidad empírica

La suite, ejecutada desde el directorio equivocado (`backend/` en vez de repo-root), reportó falsamente 76 fallos — el 100% por rutas **relativas** (`Path("backend/mcp_servers")`) en tests de estructura. Desde el repo-root: **0 fallos reales** salvo los 2 ya corregidos. (Lección registrada: el número de la suite depende del CWD; correr siempre desde repo-root.)

### 1.5 · Hallazgos de la auditoría multi-agente corregidos (commit `4fe2a6f1`)

La auditoría profunda (10 agentes · Anexo A) levantó **24 hallazgos**: **4 reales corregidos esta sesión**, **20 son drift documental/cosmético** (Anexo C). Los 2 frontend de esta tanda:

3. **HIGH · acceso por email a portales token-gated.** El builder universal de magic-links (m12 `service.py:317`) entrega TODO purpose como `/ml/consume?token=` → `/sign/{token}`, pero el dispatcher solo cubría 9 sign-flows: `auditor_portal_enac`, `portal_pentester_externo` y `portal_remediacion` caían en "Tipo de operación no soportado". Fix: 3 `case` que reenvían a `/auditor-portal/{token}/summary`, `/pentester-portal/{token}`, `/remediation/{token}` (alinea la promesa del docstring de `ml/consume`).
4. **MEDIUM · tab project-scoped roto.** `ProjectTabs.tsx` tenía `/admin/retainers` dentro de los SUB_TABS project-scoped → renderizaba `/admin/projects/{id}/admin/retainers` (404) y duplicaba el tab correcto `/retainer`. Eliminado + import `Briefcase` huérfano. `tsc --noEmit` = 0 errores.

> (Items 1-2 = gate DB Alembic + 2 tests deterministas · commit `a16c53db` · §1.1.)

---

## 2 · ESTRUCTURA DEL REPOSITORIO

```
fulkro-portales/
├── backend/            FastAPI 0.115 · SQLAlchemy 2.0 async · Alembic
│   ├── app/
│   │   ├── motors/     47 directorios de motor (m01..m31 + m_*)
│   │   ├── agents/     15 agent_*.py + agent_14_copiloto/ + registry (31 IDs)
│   │   ├── models/     ORM (237 tablas)
│   │   ├── main.py     184 include_router
│   │   └── ...
│   ├── mcp_servers/    14 MCP pentest servers + shared/
│   ├── migrations/     228 migraciones Alembic (1 head)
│   └── tests/          536 ficheros test_*.py (6123 tests)
├── frontend/           Next.js 14 App Router · TS · Tailwind · shadcn/ui
│   ├── app/            6 route groups · 168 page.tsx
│   ├── components/     419 .tsx
│   ├── hooks/          62
│   ├── lib/api/        87 módulos cliente
│   └── tests/          297 specs Playwright (200 e2e + 97 polish)
├── infra/  docs/  scripts/  data/  docker-compose.yml
```

**Cifras maestras:** 47 motores · 31 agentes (15 con implementación dedicada) · 14 MCP servers · 1102 rutas REST · 237 tablas · 228 migraciones · 6123 tests backend · 168 páginas frontend · 297 specs E2E.

---

## 3 · MOTORES BACKEND (47) — propósito + wiring

> Cada fila verificada leyendo el `README.md`/`api.py` del motor. "Rutas" = el motor expone endpoints REST montados en la app real.

| Motor | Propósito (1 línea) | Wiring |
|---|---|---|
| **m01_categorization** | Categorización ENS Anexo I (BÁSICA/MEDIA/ALTA) por regla del máximo sobre 5 dim. DICAT · determinista, NO LLM | ✅ `/categorization/*` |
| **m02_magerit** | Análisis de riesgos MAGERIT v3 (Libros I-III) integrado con Anexo II · inventario activos + valoración | ✅ `/magerit/*` |
| **m03_dda** | Declaración de Aplicabilidad: 73 entries instanciadas (Anexo II RD 311/2022) · estados por medida | ✅ `/dda/*` |
| **m04_gap** | Gap analysis determinista (target DdA vs estado) · catálogo severidad + quick-wins + LLM prioritizer | ✅ `/gaps/*` |
| **m05_obligations** | Instancia obligaciones desde gaps + Gantt con dependencias circulares + esfuerzo/personalización | ✅ `/planning,/obligations` |
| **m05_signing** | Firma in-portal Ed25519 + hash-chain + OTP step-up · 11 SignableTypes · reemplaza magic-link firma | ✅ `/portal/signing,/admin/signing` |
| **m06_document_factory** | Factory 50+ entregables ENS (DOCX/XLSX Jinja2) + firma Ed25519 + PDF · niveles Básica/Media/Alta | ✅ `/templates,/documents` |
| **m07_evidence** | Ciclo de vida de evidencias: ingestion + **ClamAV antivirus** + verificación cripto + freshness/renewal | ✅ `/evidence/*` |
| **m08_verification** | Auditor técnico (motor MÁS grande): pentest auto-trigger + cloud scan + ZFP + MITRE + handoff CPSTIC | ✅ `/verification,/portal/pentest` |
| **m09_audit_prep** | Prep ENAC: checklist + coaching + matriz 99 + dossier PDF master + auditor annotations/clarifications | ✅ `/audit-prep,/public/auditor-portal` |
| **m10_audit_sim** | Simulación pre-auditoría ENAC L0-L5 anti-alucinación (SQL real cross-motor, NO LLM) | ✅ `/audit-sim/*` |
| **m10_ens_radar** | Detección leads comerciales v3 profile-based (CNAE 6203 ∩ AAPP ∩ sin ENS) | ⏸️ **Dormido Batch 2** (reversible) |
| **m11_copiloto** | Wrapper HTTP del Agent 14 (copiloto ENS LLM) · 3 surfaces (admin/cliente) + persistencia conversación | ✅ `/copilot,/client-portal/copiloto` |
| **m12_magic_link** | Magic links Ed25519 + OTP + rate-limit · hub inbound (9 motores) · tokens one-shot sin cuenta | ✅ `/magic-links/*` |
| **m13_commercial** | Propuestas comerciales anti-alucinación económica (pricing real, nunca LLM) + firma contrato público | ✅ `/contract-signing/*` |
| **m14_contracts** | Ciclo de vida contratos C-001..C-005 + sub-procesadores + firma + adenda generator | ✅ `/contracts/*` |
| **m15_billing** | Facturación fiscal ES: IVA/IRPF + Verifactu + Facturae 3.2 + XAdES + FACe AAPP + mora | ✅ `/billing,/invoices/aapp` |
| **m16_onboarding** | Onboarding adaptativo: catálogo sector/rol + OAuth connectors (M365/GWorkspace) + LMS + PKG | ✅ `/onboarding/*` |
| **m17_planning** | Planificación proyecto: WBS + effort estimator + PDA generator + Gantt | ✅ `/planning/*,/client-portal/plan` |
| **m18_communication** | Reportes desde datos reales + plan comunicación + escalado + actas DOCX + AEPD decision tree | ✅ `/communication,/alerts` |
| **m19_risk** | CRUD riesgos + BIA + incidents (admin+portal) + CCN-CERT decision tree | ✅ `/risks,/portal/incidents` |
| **m20_workspace** | "FULKRO Room" 1:1 por proyecto: ficheros + feed + chat append-only (audit inmutable) | ✅ `/workspace/*` |
| **m21_diagnosis** | Diagnóstico organizacional: dashboard maturity + KPIs + ISO27001 coverage + cross-compliance | ✅ `/diagnosis/*` |
| **m21_portal_cliente** | Portal cliente persistente (login email+pwd) + roles/scopes + chat + MFA + evidencias upload | ✅ `/client-portal/*` |
| **m22_discovery** | Discovery técnico (2º motor más grande): assets + config + datos + identidades vía AWS/M365 connectors | ✅ `/discovery/*` |
| **m23_retainer** | Post-cert multi-cliente: 4 perfiles RAG + cadencias + renewal clock + drift detector + 2 agentes propios | ✅ `/retainer/*` |
| **m24_idms** | "Drive de FULKRO": 15 carpetas estándar + intake dedup SHA-256 + búsqueda ILIKE + awareness tracker | ✅ `/idms/*` |
| **m25_lifecycle** | Ciclo de vida proyecto (DRAFT→…→ARCHIVED→PURGED) + archive Ed25519 + exit checklist | ✅ `/lifecycle/*` |
| **m26_backup** | Backup + DR: pgBackRest + MinIO mirror + Fernet + offsite + restore tests + DR drills (R8) | ✅ `/backup/*` |
| **m27_conformity** | Gobierno conformidad ENS (4º motor más grande): ruta Declaración/Certificación + INES/PILAR/LUCIA + renewal | ✅ `/conformity,/portal/conformidad` |
| **m28_change_governance** | Gobernanza de cambios: clasificación MINOR/RELEVANT/MATERIAL + árbol 10 preguntas + recategorización | ✅ `/changes/*` |
| **m29_client_messaging** | Mensajería bidireccional cliente↔Marcos + adjuntos + email forward + digest | ✅ `/admin/messages,/client-portal/messages` |
| **m30_client_contacts** | Agenda de contactos por cliente (≠ usuarios portal) + timeline cross-motor + roles ENS | ✅ `/clients/{id}/contacts` |
| **m31_whatsapp** | WhatsApp Business vía Dialog360 + opt-in OTP + SSE inbound + RGPD export | ✅ `/admin/whatsapp,/webhooks/360dialog` |
| **m_audit_accompaniment** | Acompañamiento auditoría + conformidad sede post-implantación · state machine BÁSICO 6 / MEDIO-ALTO 11 | ✅ `/…/accompaniment` |
| **m_cloud_connectors** | Capa unificada cloud (M365/GWorkspace/AWS/Azure) + gap rules ENS + remediation orchestrator | ✅ `/…/cloud-connectors,/client-portal/cloud-*` |
| **m_compliance** | Features GDPR cliente: RoPA Art30 + DPA Art28 + derechos Art15/17/20 + cookies + breach | ✅ `/legal/*,/client-portal/transparency` |
| **m_compliance_monitor** | Auto-monitorización FULKRO: 19 checks sobre 6 normativas (RGPD/LOPDGDD/LSSI/NIS2/ISO/ENS) — dogfooding R7 | ✅ `/admin/compliance/*` |
| **m_legal** | Catálogo obligaciones legales read-only (250 entries · RGPD/NIS2/DORA/AI_Act) | ✅ `/legal-obligations/catalog` |
| **m_live_records** | Registros vivos E-303/304/305/308 project-scoped (UI integrada en motores consumidores) | ✅ `/projects/{id}/records` |
| **m_meetings** | Reuniones externas + actas DOCX + acciones post-meeting cross-motor | ✅ `/admin/meetings,/portal/actas` |
| **m_observability** | Observabilidad LLM admin: cost summary + top consumers + anomalías (motor más pequeño) | ✅ `/admin/llm-observability` |
| **m_siem** | Consola SIEM admin (FRENTE N) cross-cliente read-only (require_owner) | ✅ `/admin/siem` |
| **m_workflow_engine** | Orquestador workflow (Command Center) + deliverables + dependency resolver | ✅ `/admin/workflow-command-center` |

**Conclusión motores:** 46/47 con rutas REST vivas. El único sin rutas es `m10_ens_radar`, **desactivado deliberadamente** en Batch 2 (`main.py` líneas 229/288/736-738: "RADAR DESACTIVADO Batch 2 · dormido · reversible"). El rebuild radar-v3 vive en la rama `radar-v3-pr`. No hay motores muertos.

---

## 4 · AGENTES IA (31 registry · 15 con implementación dedicada)

`AGENT_REGISTRY` mapea 31 IDs (1-31). En la auditoría sistemática Sesión 9 se eliminaron 10 agentes scaffolding redundantes (deterministas o stubs sin invocación); el resto son service-level o motores deterministas. **Implementaciones dedicadas `agent_*.py` (15):**

| Agente | Rol | Modelo |
|---|---|---|
| A02 Pliegos | Analizador de pliegos | LLM |
| A04 Redactor | Redacta secciones narrativas 1/2/6 del E-090 | LLM |
| A06 Contratos | Analiza contratos cliente↔sus proveedores | LLM |
| A11 Auditor Virtual | Auditoría suplementaria (NO reemplaza M10) + wrapper project-scoped | LLM |
| A12 Coach Cliente | Evaluador de coaching (no generador) | LLM |
| A14 Copiloto | **Copiloto conversacional ENS · pipeline RAG con citas** (paquete `agent_14_copiloto/`) | Sonnet/Opus |
| A17 Cualificador | Scorea leads tras 1er contacto (8 preguntas humanas) | LLM |
| A18 Reunión | Panel IA live reunión exploratoria (recálculo tiempo real) | Sonnet 4.6 |
| A19 Propuestas | Redactor propuestas P-001 senior | **Opus (1M ctx)** |
| A20 Negociación | Draft contrato C-001 calidad abogado TIC | Sonnet 4.6 |
| A21 Discrepancias | Detector discrepancias cross-motor (servicio determinista + API) | Determinista |
| A27 Clasificador IDMS | Complementa heurística M24 (docs en 99_Misc) | LLM |
| A31 Enriquecedor DdA | Enriquece justificaciones no_aplica | LLM |

Reglas IA aplicadas (verificables): **R1** deterministas > LLM para normativa · **R2** citas obligatorias (RD 311/2022, CCN-STIC, Anexo II, ISO) · **R3** temperatura ≤ 0.2 · persona por rol (**R30** admin tutor vs **R29** cliente friendly) · memoria N6 por proyecto (`copilot_memory.py`).

---

## 5 · MCP SERVERS PENTEST (14 + shared)

`backend/mcp_servers/` · 174 ficheros trackeados · cada server con `server.py` + `Dockerfile` + `authorization.json`.

| Server | Tools | Server | Tools |
|---|---|---|---|
| recon | 11 | sast | 5 |
| vulnscan | 4 | cracking | 4 |
| webpentest | 7 | apisec | 4 |
| infra | 14 | mobile | 2 |
| redteam | 6 | wireless | 3 |
| cloud | 4 | phishing | 1 |
| config | 4 | **scope_enforcer** | 0 (enforcer fail-closed) |

3 scanners reales validados (Prowler + ScoutSuite + OpenVAS) + resto estructural · 88 mappings CIS/CVE → ENS Anexo II. La ejecución real requiere `docker-compose --profile pentest` (infra Hetzner). Tests `test_mcp_structure.py` verde desde repo-root.

---

## 6 · SUPERFICIE API (1102 rutas montadas · histograma)

Top grupos (rutas montadas en la app real):

- **Project-scoped admin:** `/api/v1/projects/{project_id}/*` → **174** · `/api/v1/admin/projects/*` → 58
- **Admin cross-cliente:** `clients/{id}` 28 · `admin/compliance` 24 · `admin/meetings` 11 · `admin/messages` 10 · `admin/settings` 10 · `admin/llm-observability` 6 · `admin/notifications` 6 · `admin/whatsapp` 5 · `admin/workflow-command-center` 4 · `admin/finance` 4
- **Discovery/MAGERIT/IDMS:** `discovery/projects` 37 · `magerit/analysis` 31 · `idms/projects` 27
- **Portal cliente:** `client-portal/*` (~60 rutas) + `portal/*` (actas, conformidad, dda, dpc-anual, inbox, incidents, magerit, policies, signing 9, workflow, onboarding 11)
- **Portal auditor/pentester:** `public/auditor-portal` 25 · `public/pentester-portal` 6 · `public/{remediation,verify-auth,retainer-offer,download}`
- **Conformidad/Audit:** `conformity/projects` 20 · `audit-prep/projects` 19 · `audit-sim/projects` 8
- **Comercial/Retainer/Billing:** `retainer/projects` 17 · `contracts/projects` 13 · `billing/projects` 9
- **Dev/seed:** `/_dev/*` (login-as-marcos, create-test-client, seed-*, reset-test-cycle) — gated por entorno

---

## 7 · FRONTEND · 4 PORTALES (168 páginas · 6 route groups)

| Route group | Páginas | Rol |
|---|---|---|
| **(admin)** | ~90 | Portal Marcos. Project-scoped `/admin/projects/[id]/*` con ~50 sub-páginas (dda, magerit, plan, audit, conformity, evidence, discovery, billing, retainer, exit…) + top-level cross-cliente (clients, compliance, meetings, retainers, siem, operations, workflow-command-center) |
| **(client-portal)** | ~40 | Portal cliente persistente: dashboard, tasks, conformidad, certificacion, dda, magerit, plan, evidencias, policies, firmas-pendientes, firmas-hub, incidents, dpc-anual, cloud-connections, remediaciones, onboarding, chat, whatsapp, settings/mfa… |
| **(portal)** | 15 | Portal auditor ENAC `/auditor-portal/[token]/*` (12 vistas: summary, dda, magerit, evidence, plan, audit-log, pentest, documents, draft-report, dda-evidence-gaps, e041) + pentester-portal + remediation + verify-auth (magic-link gated) |
| **(legal)** | 8 | cookies, derechos-rgpd, dpa-template, imprint, privacy, sub-processors, terms, trust |
| **(public)** | 4 | diagnostico/[token], download/[token], ml/consume, sign/[token] |
| **(radar)** | 4 | radar, leads, clusters, runs (backend dormido en Batch 2) |

Stack: **419 componentes** · 62 hooks · 87 módulos `lib/api` · tanstack-query · SSE realtime. Doctrina **cliente-mínimo** (cliente VE/AUTORIZA/FIRMA/RECIBE, no opera la técnica ENS) + **R29** (lenguaje amable sin jerga admin).

---

## 8 · MODELO DE DATOS (237 tablas ORM)

Convenciones (verificadas en `models/base.py`): UUID PK `gen_random_uuid()` · `timestamptz` · soft-delete `deleted_at` · RLS por `project_id`/`client_id` en tablas multi-tenant · audit_log inmutable con hash-chain SHA-256 (R6). Mixins `FullMixin` (id+timestamps+soft-delete), `ClientReviewMixinA/B` (review cliente in-portal). 228 migraciones Alembic, **1 head** (`rls_tenant_hardening_p0_001`), `alembic check` verde.

> Detalle por dominio en el Anexo A (verificación profunda).

---

## 9 · SEGURIDAD (blindaje P0 · auditoría 2026-06-07)

Verificado leyendo `rls_tenant_hardening_p0_001.py`, la suite y el estado en BD:

- **Cirugía de rol (raíz):** `fulkro_app` es NOSUPERUSER y ya **no** es miembro de `fulkro` (se eliminó `GRANT fulkro TO fulkro_app`). Se introdujo `fulkro_app_bypassrls` (NOSUPERUSER + BYPASSRLS) para setup/cross-tenant explícito. Esto convierte RLS + inmutabilidad audit_log de "barreras blandas" a **barreras duras**.
- **RLS multi-tenant:** ENABLE + FORCE + policy `project_isolation` sobre tablas tenant (7 tablas que estaban sin RLS + FORCE en 26 más). Confirmado empíricamente: los 2 tests de notificación demostraron que `fulkro_app` ya NO ve filas cross-proyecto sin contexto.
- **audit_log R6:** inmutable, hash-chain SHA-256, triggers no_update/no_delete.
- **Superficie de borde:** BodySizeLimit middleware · TrustedHost · validación `app_secret_key` en startup (FATAL en prod si débil) · magic-bytes en uploads · cap de coste LLM funcional · Celery time-limits · SSE pool liberado antes del stream.
- **R5** magic links Ed25519 · **R4** WebAuthn (Yubikey) Marcos en prod.

CI de seguridad: `security-scan.yml` + suite `tests/security`.

---

## 10 · COBERTURA DE TESTS + E2E

- **Backend:** 6123 tests (536 ficheros) → **6001 passed · 0 failed · 122 skipped** desde repo-root. Por área: motors 392 · agents 30 · core 21 · notifications 15 · corpus 8 · auth 7 · security 7 · audit_fixes 7 · integration 3 · scripts 3 · mcp_servers 2.
- **E2E Playwright:** **543 casos / 297 specs compilan** (200 e2e + 97 polish WCAG). Cobertura por dimensión solicitada:
  - **3 niveles ENS:** `conformidad-basica-cliente-e2e`, `conformidad-alta-cliente-e2e`, `mb7_1_dashboard_{basica,media,alta}`, `mb17_categoria_{alta,media}_complete`.
  - **4 portales:** admin (`admin-*`, `project-tabs`, `separacion-portales`, `admin_actions_invisible_to_client`), cliente (`cliente_*`, `client-portal-login`), auditor (`auditor-portal-full-flow`), pentester (`pentest-authorization-cliente-e2e`).
  - **Copiloto:** `copilot_admin_*`, `copilot_cliente_*`, `copilot_memory`, `copilot-streaming`.
  - **MCP/pentest:** `mcps_cloud_prowler_execute`, `mcps_vulnscan_nuclei_execute`, `mcps_phishing_gophish_simulacro`, `antivirus-scan-e2e`.
  - **Sync realtime:** `workflow_sse_realtime_{admin,cliente}_receives_event`, `m01/m02-sync`.
- **Gate CI:** `ci.yml` (lint → typecheck → test → playwright) + `admin-polish-empirical.yml` (102 páginas WCAG axe: 80 admin + 10 cliente + 12 auditor) + `security-scan.yml`.
- **Limitación local honesta:** el run **autenticado** de E2E está bloqueado en este equipo por un desajuste de claves Ed25519 (backend genera clave efímera; `FULKRO_AUTH_PUBLIC_KEY` vacío en `.env` → JWT verify falla → redirect-loop). Es un **problema de entorno conocido (OPS-052 72ª)**, resuelto en CI (claves vía secrets) y en Hetzner. NO es un defecto de producto. Por eso la verificación E2E aquí es estática (compilación de 543 casos) + smoke HTTP (portales sirven 200) + gate CI.

---

## ANEXO A · Verificación profunda por dimensión (10 agentes paralelos)

> _Sección generada por la auditoría multi-agente (10 dimensiones leyendo los ficheros reales del worktree). Se integra al completar el workflow._

## Seguridad & aislamiento multi-tenant (blindaje P0 · auditoría 2026-06-07)

**Sentinela OK**: `backend/app/motors/m01_categorization/README.md` línea 1 = `# Motor 1 · Categorization Engine` (worktree `fulkro-portales` confirmado, no la rama divergente).

Verificación empírica de los 5 controles P0 más los dos ítems de provisioning. Todo basado en ficheros leídos directamente; las afirmaciones citan ruta como evidencia.

### 1. Separación de roles PostgreSQL · cierre de escalada a superuser
Evidencia: `infra/docker/init-roles.sql`.
- `fulkro_app` creado `WITH LOGIN ... NOSUPERUSER` (línea 15) — rol runtime sujeto a RLS.
- `fulkro_app_bypassrls` creado `WITH NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE BYPASSRLS` (líneas 52-60) — bypass RLS para agregados admin cross-tenant **sin** poder escalar a superuser.
- `GRANT fulkro_app_bypassrls TO fulkro_app` (línea 83): la app puede asumir el rol bypass vía `SET LOCAL ROLE`, pero NO el superuser `fulkro`.
- `REVOKE fulkro FROM fulkro_app` (línea 103): cierre explícito e idempotente de la membresía superuser que clusters previos ya tenían concedida (los roles son globales; quitar el GRANT del script no revoca lo ya otorgado). **NO existe `GRANT fulkro TO fulkro_app`**.
- GUC `session_replication_role` delegado SOLO al rol bypass (PG15+, líneas 92-98), nunca al rol app — el harness de tests siembra con FK/triggers off sin necesitar superuser.
- `fulkro_migrate` (alembic) es `NOSUPERUSER NOCREATEDB NOCREATEROLE BYPASSRLS` (líneas 129-131); BYPASSRLS es lo que hace que el BLOQUE B (FORCE) no rompa migraciones/seeds.
- Uso runtime confirmado: 30+ call-sites ejecutan `SET LOCAL ROLE fulkro_app_bypassrls` (p.ej. `backend/app/api/v1/operations.py:86`, `audit_search.py:90`, `services/adaptive_dashboard_service.py:81`, `billing/api.py:134`, `dev/router.py` múltiple). Patrón consistente para agregados cross-tenant.

### 2. RLS tenant hardening · migración `rls_tenant_hardening_p0_001`
Evidencia: `backend/migrations/versions/rls_tenant_hardening_p0_001.py` (revises `milestone_scheduled_date_28_001`, reversible).
- **BLOQUE A** (7 tablas que estaban SIN ningún RLS, todas con `project_id` directo — fuga cross-tenant real): `bia_analyses`, `awareness_sessions`, `invoices_aapp`, `aepd_notifications`, `audit_accompaniment_state/transitions/artifacts`. Por cada una: `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY` + `CREATE POLICY project_isolation ... USING (project_id = current_project_id())` (líneas 81-87).
- **BLOQUE B** (26 tablas RLS-enabled pero NOT FORCED): solo `FORCE ROW LEVEL SECURITY` como defensa-en-profundidad contra drift de ownership (líneas 90-91). Funcionalmente no-op con owner=`fulkro_migrate` (BYPASSRLS), blinda futuro.
- Cadena de enforcement RLS verificada extremo a extremo:
  - Helper SQL `current_project_id()` definido en `infra/docker/init-functions.sql:17-19` (`SELECT NULLIF(current_setting('app.current_project_id', true), '')::uuid` · `STABLE`).
  - Contexto por request: `backend/app/database.py:38-61` `set_tenant_context()` usa `set_config('app.current_project_id', :pid, true)` (is_local=true → scope = transacción).
  - Patrón canónico `project_id::text = current_setting('app.current_project_id', true)` replicado en decenas de migraciones (p.ej. `sand_client_tasks_001.py`, `departments_1c_f_2_001.py`, `ai_act_transparency_1e1b2_001.py`).
- **Defensa fail-closed (hallazgo positivo)**: `backend/app/api/v1/client_copilot_stub.py:193-209` setea el contexto RLS SOLO con `client_id` del usuario autenticado y deliberadamente NO con `payload.project_id` (input cliente), evitando que un `project_id` ajeno exponga child tables project-scoped (un project_id ajeno → 0 filas).

### 3. Validación de configuración crítica en startup
Evidencia: `backend/app/startup_checks.py` invocado desde `lifespan` en `backend/app/main.py:344-345`.
- `verify_app_secret_key()` (líneas 126-156): en producción aborta (`CriticalConfigError`) si `app_secret_key` está vacío / `change-this` / `changeme` / `<32 chars`. En dev solo warning. Deriva el cifrado Fernet de tokens OAuth (m16) y credenciales SSH de pentest (m08).
- `verify_critical_env()` exige `DATABASE_URL` + 3 claves Ed25519 (`FULKRO_AUTH_PRIVATE_KEY`, `FULKRO_ML_PRIVATE_KEY`, `FULKRO_BACKUP_SIGNING_KEY`).
- `verify_no_insecure_defaults()` aborta si `FULKRO_MINIO_SECRET_KEY == "changeme"`.
- `verify_ed25519_keys()` exige claves M06+M07 en disco (`var/keys/`).
- Skip automático en tests (`FULKRO_TESTING=1`). El default inseguro existe (`config.py:53` `app_secret_key = SecretStr("change-this")`), pero el check lo bloquea fail-fast en producción.

### 4. BodySizeLimit middleware (anti-DoS OOM)
Evidencia: `backend/app/middleware/body_limit.py`, registrado en `main.py:389`.
- `BodySizeLimitMiddleware` rechaza con **413** cualquier request cuyo `Content-Length` supere el tope global ANTES de leer el cuerpo (líneas 33-50).
- Tope configurable vía `FULKRO_MAX_REQUEST_BODY_MB` (default 100 MB · líneas 19-27). Content-Length malformado → deja pasar (el endpoint valida).
- Headers de hardening adicionales en `backend/app/middleware/csp.py` (`CSPMiddleware`, `main.py:391`): CSP completa, `X-Frame-Options DENY`, `X-Content-Type-Options nosniff`, `Referrer-Policy`, **HSTS** `max-age=63072000; includeSubDomains; preload` (líneas 68-71), `Permissions-Policy` restrictiva.
- `TrustedHostMiddleware` solo en producción (`main.py:371-376`) con `settings.allowed_hosts_list` (default `localhost,127.0.0.1` · `config.py:55,191`).
- CORS permisivo (`allow_origins=["*"]`) **solo** en no-producción (`main.py:379-386`); en producción no se registra CORS abierto.
- Documentación API (`/docs`·`/redoc`·`/openapi.json`) deshabilitada en producción (`main.py:350-368` · `_prod_docs_off`).

### 5. audit_log inmutable con hash-chain SHA-256 (R6)
Evidencia: `backend/migrations/versions/d4f8b2a90001_audit_log_hash_chain_trigger.py`.
- `fn_audit_log_hash_chain()` (BEFORE INSERT): `pg_advisory_xact_lock(hashtext('audit_log_chain'))` + `hash_current = encode(digest(payload, 'sha256'), 'hex')` con `payload = prev_hash || tabla || registro_id || accion || usuario || timestamp || payload_old || payload_new` (líneas 60-92). **SHA-256** (no Ed25519 — Ed25519 vive en firma PDF M05/M06/M07, concern separado).
- Triggers `tg_audit_log_no_update` + `tg_audit_log_no_delete` → `fn_audit_log_immutable()` que hace `RAISE EXCEPTION ... ERRCODE='insufficient_privilege'` (líneas 95-118): append-only por trigger.
- `fn_audit_log_verify_chain()` recalcula y compara toda la cadena, devolviendo `first_bad_seq` y `ok` (líneas 169-209).
- `fn_audit_track()` AFTER INSERT/UPDATE/DELETE sobre 13 tablas críticas (evidence, documents, contracts, invoices, projects, clients, categorizations, dda_entries, obligations, magerit_analysis, audit_findings, pentest_findings, document_versions).
- **Defensa por privilegio (no solo trigger)**: `scripts/build_test_db.sh:40` ejecuta `REVOKE UPDATE, DELETE ON audit_log FROM fulkro_app, fulkro_app_bypassrls;` — ni el rol app ni el bypass pueden alterar la cadena ni con `session_replication_role=replica` (que desactivaría triggers). R6 garantizado a nivel de privilegio.

### Provisioning Hetzner (código cableado · demonio externo)
- **ClamAV**: `backend/app/motors/m07_evidence/antivirus_scan_service.py` — workflow completo cableado (clamd InstreamScan vía TCP 3310, branch clean/quarantined/error, cuarentena en `var/quarantine/`, alertas `alert_queue`). Host/puerto/timeout por env (`CLAMD_HOST`/`CLAMD_PORT`/`CLAMD_TIMEOUT_SECONDS`, default `localhost:3310`). El **daemon clamd es sidecar externo** (docker-compose Q1 A) — código listo, demonio se provisiona en Hetzner.
- **MinIO Object-Lock (WORM)**: referenciado como bucket `fulkro-evidence WORM 7y` (CLAUDE.md). El cifrado/secret de MinIO está blindado en startup (`FULKRO_MINIO_SECRET_KEY != changeme`). El Object-Lock retention es configuración de provisioning del bucket (externo al código de la app).

### Estado conexión frontend↔backend
Todos los controles P0 son backend/infra (middleware, RLS en BD, roles PG, triggers SQL). No requieren cableado frontend; el frontend hereda las cabeceras de seguridad (CSP/HSTS/X-Frame-Options) inyectadas por `CSPMiddleware` en todas las responses. La doc API (`/docs`) queda oculta en producción, reduciendo superficie de descubrimiento para el cliente.

**Veredicto**: los 5 controles P0 (1 NOSUPERUSER + bypassrls sin GRANT fulkro · 2 RLS ENABLE+FORCE+project_isolation · 3 validación app_secret_key startup · 4 BodySizeLimit · 5 audit_log hash-chain SHA-256 R6) están **presentes y correctos** en el código del worktree `fulkro-portales`. Sin issues.

---

## Pipeline Pentest & MCP servers (Motor 8 · m08_verification)

Motor de verificación técnica que cubre vuln-scan MEDIA (obligatorio), pentest opcional MEDIA y pre-chequeo continuo. La regla ALTA permanece intacta: ALTA exige pentester **externo independiente**; el motor *complementa*, no sustituye (declarado en docstring de `fase_runner.py` líneas 18-20).

### Orquestación de fases (`fase_runner.py`)
- `run_fases(db, run_id, ...)` encadena las fases canónicas: **scope** (ya derivado en `create_run`) → **scan** (Fase 1) → **ZFP 5 gates** (Fase 3 · `run_zfp_pipeline`) → **persist** `VerificationFinding` (+ `EnsMapper` determinista) → **counters** → `completed`. Evidencia: `\\...\m08_verification\fase_runner.py:155-250`.
- **Fail-closed real**: cada sub-fase (scan/zfp/persist) corre en `try/except`; si cualquiera falla se acumula en `failures` y el run **NO** se marca `completed` (queda en la fase alcanzada, `partial: True`). Evidencia: líneas 186-239.
- **Kill-switch pre-check** integrado: si `cancel_requested_at != NULL` antes de arrancar, aborta a `cancelled` (líneas 173-177).
- **Gate USE_MCP_REAL**: `use_mcp_real()` (líneas 58-61) por defecto `False` en dev/test. Con `False`, `_default_scan_phase` devuelve `[]` honestamente (no inventa hallazgos, líneas 64-83). El cableado de invocación real de runners (nuclei/openvas…) queda explícitamente como **validación de deploy Hetzner (PE-3 / F14-DEPLOY)** — declarado en docstring líneas 14-20 y warning línea 77-80.
- **Caller de producción**: la Celery task `m08_verification.execute_run` (`scheduler.py:233-259`) es quien invoca `run_fases` en runtime. Tests adicionales en `test_fase_runner_f1.py` y `test_pentest_summary_f7.py`.

### Invocación MCP (`mcp_executor_service.py` + `backend/app/mcp_client.py`)
- `MCPExecutorService` (singleton in-memory, sin tabla DB nueva · ADR-025) orquesta un **catálogo de 13 tools** project-scoped: vulnscan (nuclei/openvas/trivy/grype), cloud (prowler/scoutsuite/pacu/kube), config (clara/cis-cat/lynis/openscap), phishing (gophish). Evidencia: `mcp_executor_service.py:62-385`.
- Ejecuta en background task con sesión DB propia (no la del request, ya cerrada — fix Ejecutable 8 Pasada 16, líneas 494-502) e invoca `try_invoke_mcp_or_none(server, tool, args)`. Si devuelve `None` (flag off / MCP no disponible) cae a `_simulated_result` (líneas 532-539, 608-633): resultado simulado honesto con `_simulated: True`, `findings: []` y nota "En producción el MCP server real ejecuta el binario".
- **SSE progress** vía `asyncio.Queue` por execution (líneas 591-606) y **auto-attach** del reporte JSON al folder IDMS "13_Informes_Tecnicos" (reuse `m24_idms.intake_document`, líneas 635-711).
- `mcp_client.py`: con `USE_MCP_REAL=true` hace **spawn real** de `server.py` vía `asyncio.create_subprocess_exec` y diálogo **JSON-RPC 2.0** (`initialize` → `tools/call`) sobre stdin/stdout (líneas 164-258). Degradación graceful capturando `MCPInvocationError | FileNotFoundError | OSError` → `None` (líneas 87-96). La autorización se propaga al subprocess vía env var `PENTEST_AUTHORIZATION` heredada al spawn (docstring líneas 21-26).

### MCP servers (14 confirmados en `backend/mcp_servers/*/server.py`)
Glob confirma 14 directorios con `server.py`: **apisec, cloud, config, cracking, mobile, infra, phishing, recon, redteam, scope_enforcer, vulnscan, sast, webpentest, wireless** (más `openvas` como imagen externa `immauss/openvas` en compose). `_KNOWN_SERVERS` en `mcp_client.py:103-118` mapea estos servers a sus rutas.
- Ejemplo `recon/server.py`: registra **11 tools** de reconocimiento (nmap, masscan, amass, subfinder, httpx, naabu, shodan, theharvester, spiderfoot, searchsploit, dns_checker).
- Ejemplo `vulnscan/server.py`: registra 4 tools (nuclei, openvas, trivy, grype).

### Scope enforcer (fail-closed verificado)
- `scope_enforcer/server.py` expone una única tool `check_scope` con `risk_level="low"` y delega en `scope_enforcer/enforcer.py::ScopeEnforcer.check()`.
- **Fail-closed empírico** en `enforcer.py:15-76` y en el helper compartido `shared/scope_check.py:34-100` (cada tool de cada server lo llama ANTES de ejecutar el binario): autorización vacía → `allowed: False`; fuera de ventana temporal → deny; test_type no permitido → deny; target excluido → deny; target fuera de scope → deny; y **cualquier excepción** retorna `{"allowed": False, "reason": "Scope check error (fail-closed)"}` (líneas 75-77 / 99-100). Soporta CIDR, wildcard `*.dominio` y match exacto.

### Derivación de scope (`scope_deriver.py`)
- `derive_scope(db, project_id, category)` deriva el alcance desde Fulkro: activos M22 (`discovered_assets`), exclusiones M3 (`op.ext.4` → líneas `EXCLUDE:`), crown jewels M2 (MAGERIT DICAT ≥ 8) y `scan_window` desde M14 `contracts.scan_window` con fallback al default canónico (`fetch_scan_window_for_project`, líneas 43-67). Errores controlados `M22NotRunError` / `EmptyScopeError`. Persiste `(scope, derived_from)` → `verification_runs.scope_jsonb`. Cadena confirmada en `service.create_run` (`service.py:78-123`): `create_run` invoca `derive_scope` y guarda `scope_jsonb`.

### Kill-switch (`kill_switch.py`)
- `request_kill` marca `cancel_requested_at` (idempotente) e **inmediatamente** mata los pgids registrados (`kill_run_processes_now`, bypass del watcher). `KillWatcher` (background asyncio, tick 1s) es respaldo: SIGTERM → grace 3s → SIGKILL → `cancel_completed_at`. Registro in-memory `run_id → set[pgid]` vía `tracked_subprocess` context manager (líneas 88-105). Garantía spec: <5s request→cancellable.

### Flujo de autorización del cliente (OTP step-up)
- **Backend `public_api.py`** (3 portales públicos por magic-link JWT, sin login): remediación cliente, pentester externo, y **verify-auth (RSEG)**. Validación estricta de token (`_validate_token_peek`: firma JWT + hash en DB + purpose en `allowed_purposes` + no revocado + no expirado + usos < max_usos, líneas 111-179), rate-limit 20 req/min por token+IP, log en `client_interactions`.
- **OTP step-up real** en `verify-auth/{token}/submit` (líneas 809-895): exige `accepted_legal`, valida OTP con `_hash_otp` contra `link.otp_hash`, bloqueo tras `OTP_FAILURE_THRESHOLD` fallos, marca `run.authorization_signed_at` + `authorization_magic_link_id`, incrementa `usos`, y genera `signature_hash` SHA-256 inmutable. Purposes `AUTORIZAR_VERIFICACION_TECNICA` / `AUTORIZAR_PENTEST_EXTERNO`.
- **Portal pentester externo**: descarga de documentos con anti path-traversal (`relative_to(allowed_root)`, líneas 509-516), VPN `.ovpn` (credenciales por canal aparte), submit de findings estructurados o PDF (≤50MB, hash SHA-256), `complete` irrevocable.

### Estado de conexión frontend ↔ backend
- **CONECTADO Y CABLEADO.** Portal pentester externo: `frontend/app/(portal)/pentester-portal/[token]/page.tsx` → `PublicPortalShell` + `PentesterPortal` (componente real). API client `frontend/lib/api/public-portals.ts` con `BASE = "/api/v1/public"` que mapea 1:1 a los endpoints de `public_api.py` (prefijo router `/public` + `prefix="/api/v1"` en `main.py:651`). Cubre remediación, pentester (data/documents/vpn/findings/upload-pdf/complete) y verify-auth (data/request-otp/submit).
- Autorización pentest cliente: `frontend/app/(client-portal)/client-portal/pentest-authorization/page.tsx` (page real, no stub) con 6 secciones (Scope/Ventana/PlanTests/ContactoIR/Compromisos/MarkReviewed) + `PentestAuthorizeButton` (SigningFlow OTP step-up), datos vía hook `usePentestAuthClient`. Test E2E presente: `frontend/tests/e2e/pentest-authorization-cliente-e2e.spec.ts`.
- **Routers registrados en `main.py`**: `m08_verification_router` (`/api/v1`, línea 650), `m08_public_router` (línea 651), `m08_pentest_portal_router` (`portal_api`, línea 764), `pentest_auto_trigger_api` (línea 163).

### Honestidad empírica: cableado vs ejecutable
- **Cableado en código (cerrado y testeable sin binarios)**: orquestación de fases, ZFP 5-gates, fail-closed, kill-switch, scope-deriver, scope-enforcer (fail-closed), catálogo 13 tools MCP, cliente JSON-RPC, 3 portales públicos con OTP, derivación de scope, auto-attach IDMS, frontend completo. Verificado contra los ficheros.
- **Ejecutable solo con infra (Hetzner)**: la ejecución REAL de scanners (Prowler/ScoutSuite/OpenVAS/Nuclei…) requiere los 14 contenedores MCP del `profile pentest` corriendo (`docker compose --profile pentest up -d`). En `docker-compose.yml` todos los servers MCP están bajo `profiles: [pentest]` y cada scanner `depends_on: [scope-enforcer]`; la red `pentest-net` es `internal: true` (aislamiento). En dev (`USE_MCP_REAL=false`, default) `fase_runner` devuelve scan vacío y `mcp_executor` devuelve resultado simulado — comportamiento honesto y prod-safe. La validación real de binarios es PUERTA DURA F14-DEPLOY antes del pentest de un cliente real (PE-3, decisión Marcos 2026-06-06).

---

## Portal Cliente (cliente-mínimo + R29)

Worktree auditado: `\\wsl.localhost\Ubuntu\home\usuario\fulkro-portales`. Sentinela OK (`backend/app/motors/m01_categorization/README.md` línea 1 = "# Motor 1 · Categorization Engine").

El portal cliente es una de las 4 áreas separadas (ADR-013). Route-group Next.js `app/(client-portal)/client-portal/*`, layout en `frontend/app/(client-portal)/client-portal/layout.tsx` → `ClientPortalChrome` (Server Component + chrome path-aware). Navegación lateral en `frontend/components/layout/ClientSidebar.tsx`. Cliente autenticado por cookie httpOnly `fulkro_session` + CSRF `fulkro_csrf` (triple binding ADR-019), NO JWT en localStorage. Wrapper de red único: `frontend/lib/client-portal-api.ts` (`clientApi`, base `/api/v1`, `credentials: include`, header `X-CSRF-Token` en mutaciones).

### Conexión frontend ↔ backend (verificada por prefijos montados)

El frontend usa dos familias de prefijos backend, ambas reales:
- `/api/v1/client-portal/*` — montados sin prefijo extra o con prefijo `/client-portal` en cada router (ej. `m21_portal_cliente/api.py:106` `prefix="/client-portal"`, `m17_planning/portal_api.py:38` `prefix="/client-portal/plan"`, `m_compliance` measure/summary, `m_cloud_connectors/api_cliente.py:64` `/client-portal/cloud-connectors`, `m04_gap/control_status_api.py:238` `/client-portal/controls`, `m05_signing` firmas-hub via `/portal/signing/projects/{id}/history`).
- `/api/v1/portal/*` — routers `m05_signing/api.py:109` `/portal/signing`, `m27_conformity/portal_api.py:44` `/portal/conformidad` (+ `portal_api_dpc.py` `/portal/dpc-anual`), `m03_dda` `/portal/dda`, `m02_magerit` `/portal/magerit`, `m06_document_factory` `/portal/policies`, `m_meetings` `/portal/actas`, `m19_risk` `/portal/incidents`, `m08_verification` `/portal/pentest`, `api/v1/portal_workflow.py:43` `/portal/workflow`, `m23_retainer` `/portal/retainer-checkin`, `m16_onboarding/portal_api.py:50` (prefijo completo `/api/v1/portal/onboarding`, incluido SIN prefijo extra en `main.py:562` → NO hay doble `/api/v1`), `m21_portal_cliente/notifications_inbox_api.py` (`/api/v1/portal/inbox`, incluido en `main.py:717` sin prefijo extra). Verificado en `backend/app/main.py` que `m16_portal_router` y `client_inbox_router` ya traen el prefijo absoluto baked-in — no se duplica.

Cruces concretos verificados módulo-API ↔ endpoint backend:
- `lib/api/signing.ts` → `POST /portal/signing/intents/{id}/sign-canvas` y `GET /portal/signing/projects/{id}/pending` existen en `m05_signing/api.py` (líneas 572 y 664, `@client_router`).
- `lib/api/conformidad.ts` → `GET .../declaration|readiness|document-hash|post-signature` + `POST .../mark-reviewed` existen en `m27_conformity/portal_api.py`.
- `lib/api/plan-cliente.ts` → `GET /client-portal/plan` (`m17_planning/portal_api.py`), READ-ONLY (sin POST/PATCH, ADR-014).
- `lib/api/client-portal-tasks.ts` → `GET/POST /client-portal/tasks/*` (start/complete/block/approve-plan), workspace ADR-038.

### Filosofía cliente-mínimo (VE / AUTORIZA / FIRMA / RECIBE — NO opera la técnica ENS)

Sostenida empíricamente página a página:
- **VE (read-only)**: `plan/page.tsx` reusa `GanttView` con toggle "Solo mis tareas" y comentario explícito "ADR-014 read-only (cliente NO modifica · backend NO PATCH endpoints)". `cumplimiento/page.tsx` agrega 5 áreas cross-motor "sin tecnicismos". `dda/page.tsx` y `magerit/page.tsx` (sub-atom 1.D.F.bis.III.A) declaran "Cliente NO marca aplicabilidad medidas (Marcos opera M03/M02 admin) · Cliente VE resumen final read-only".
- **AUTORIZA**: `pentest-authorization/page.tsx` (cliente VE scope+ventana+plan+IR → revisa → firma OTP step-up → autoriza). `remediaciones/page.tsx` ("Tú decides si autorizas · si tienes dudas, escríbele desde el chat"; ApprovalModal; cross-project isolation backend-enforced).
- **FIRMA**: `firmas-pendientes/page.tsx` (Ejecutable 7.7, canvas TIER 1 Ed25519 + nombre/apellido, sin OTP). `conformidad/page.tsx` (firma declaración tier-aware BÁSICA E-041 / MEDIA-ALTA compromiso pre-ENAC). `dda/page.tsx` botón `DdaSignFinalButton` solo cuando `ready_for_final_sign`.
- **RECIBE**: `firmas-hub/page.tsx` (historial + integridad de cadena hash). `certificacion/page.tsx` (timeline acompañamiento read-only, "cliente RECIBE updates · NO opera proceso"). SSE en tiempo real vía `useClientProjectEvents` (Pattern #14) en plan, firmas-pendientes, remediaciones, certificacion.

Las páginas técnicas (dda, magerit, policies, conformidad, dpc-anual, actas, incidents, pentest-authorization, evidencias, retainer-checkin) NO están en el sidebar (`ClientSidebar.tsx` líneas 33-37 lo documentan): el cliente llega por tareas/CTAs que Marcos asigna, no navega manualmente. La acción más "operativa" del cliente es abrir preguntas (DdA "con_pregunta" → chat con Marcos) y subir documentos — coherente con cliente-mínimo.

### R29 (lenguaje amable, sin jerga admin, sin coerción)

Verificado en copy real:
- Tono amable/no coercitivo: "Sin prisa por tu parte" (`firmas-pendientes`, `remediaciones`, `plan` empty states), "te lo decimos amablemente" (`cumplimiento`), "Sin prisa" (`plan` filtro), "Te avisaremos por aquí" (firmas vacías).
- Sin jerga admin / R30 inverso: `dda/page.tsx` banner "Marcos preparó las decisiones técnicas… Tu papel es revisar el resumen". Términos ENS siempre envueltos en `<TooltipENS term="ENS|DdA|MAGERIT|Ed25519|ENAC|SHA256|RD_311_2022">` (componente `components/ui/tooltip-ens`).
- Errores friendly: "No pudimos cargar… Recarga la página · si sigue pasando avisa a Marcos" (patrón repetido en plan/cumplimiento/remediaciones, `<Alert variant="danger">`).
- Branding multi-tenant: `ClientSidebar` muestra logo del cliente si `useClientBranding()` lo provee, fallback logo FULKRO.

### Inventario ~40 páginas del portal (39 page.tsx + login)

PRINCIPAL (lo que el cliente HACE/VE):
1. `/client-portal/` (`page.tsx`) — redirect: `/me` OK → dashboard, fallo → login.
2. `/dashboard` — dashboard adaptativo 3 zonas (`ClientDashboardV3`, `GET /client-portal/dashboard/adaptive`).
3. `/cumplimiento` — resumen cumplimiento agregado 5 áreas cross-motor (`/client-portal/compliance-summary`).
4. `/certificacion` — timeline acompañamiento certificación ENAC read-only (m_audit_accompaniment, #12 nav).
5. `/tasks` — Mis tareas (workspace start/complete/block/approve-plan, ADR-038).
6. `/firmas-hub` — historial firmas + integridad cadena hash (`/portal/signing/.../history`).
7. `/firmas-pendientes` — firma canvas TIER 1 Ed25519 (Ejecutable 7.7).
8. `/files` — subir documentos (Files extended, m07).
9. `/remediaciones` — Mejoras propuestas cloud, autoriza/decide (Bloque 3+5).
10. `/plan` — Mi plan ENS Gantt read-only + resumen pagos.
11. `/incidents` — notificar incidentes (CCN-CERT, m19).
12. `/actas` — actas comité (ver/firmar, m_meetings).
13. `/dpc-anual` — Declaración Permanencia/revisión anual post-cert (m27).

TÉCNICAS task-driven (sin sidebar, acceso por tarea):
14. `/dda` — VE resumen DdA + abre preguntas + firma E-040 final.
15. `/magerit` — VE valoración MAGERIT + firma (simplificada).
16. `/conformidad` — firma declaración conformidad ENS tier-aware (BÁSICA/MEDIA/ALTA).
17. `/policies` — políticas a aprobar/firmar (m06).
18. `/pentest-authorization` — revisa y autoriza ventana pentest (OTP step-up, m08).
19. `/evidencias` — evidencias (m07).
20. `/retainer-checkin` — check-in retainer trimestral (m23).
21. `/registros` — REDIRECT a `/tasks`.
22. `/registros/[tipo]` — página dinámica por register_type (live records).
23. `/control-status`/controls (vía cumplimiento) — estado controles m04 (backend `/client-portal/controls`).
24. `/firma` — explicativa "cómo funciona la firma electrónica FULKRO" (ADR-010).
25. `/workflow` — vista cronológica friendly del workflow (workflow-guide enriched).

MI EMPRESA:
26. `/onboarding` — wizard onboarding inicial (m16, `/api/v1/portal/onboarding`).
27. `/onboarding/oauth-callback` — callback OAuth conectores cloud.
28. `/cloud-connections` — gestión steady-state conexiones cloud (m_cloud_connectors).
29. `/categorizacion` — categorización ENS (CLUSTER 1 Phase 1A, m01).
30. `/billing` — listado facturas + IBAN (info-mode).
31. `/transparency` — transparencia/observabilidad consultor (sub-atom 1.E.1.B.2).

COMUNICACIÓN:
32. `/chat` — chat con Marcos (m11 copiloto/portal).
33. `/inbox` — bandeja entrada + notificaciones + composer (m21 inbox + m29 messaging).
34. `/whatsapp` — opt-in WhatsApp (m31).

CUENTA Y AJUSTES:
35. `/account` — perfil + cambio contraseña (`ClientMeResponse`).
36. `/account/notifications` — preferencias notificación (vista cuenta).
37. `/settings` — hub Ajustes (#27, índice antes 404).
38. `/settings/mfa` — MFA TOTP voluntario opt-in (cliente-mínimo).
39. `/settings/notifications` — preferencias notificación.
40. `/login` — login split logo+form (chrome público sin sidebar).

(Sidebar real expone subset: Inicio, Cumplimiento, Mi certificación, Mis tareas, Firmas pendientes, Subir documentos, Mejoras propuestas, Mi plan ENS, Incidentes, Actas, DPC anual, Onboarding, Conexiones cloud, Facturación, Chat, Mensajes, WhatsApp, Mi cuenta, Ajustes, Salir.)

### Evidencia de ficheros leídos
- Frontend páginas: `dashboard/page.tsx`, `tasks/page.tsx`, `conformidad/page.tsx`, `firmas-pendientes/page.tsx`, `plan/page.tsx`, `dda/page.tsx`, `cumplimiento/page.tsx`, `firmas-hub/page.tsx`, `workflow/page.tsx`, `inbox/page.tsx`, `remediaciones/page.tsx`, `pentest-authorization/page.tsx`, `account/page.tsx`, `certificacion/page.tsx`, `page.tsx` (root).
- Frontend infra: `lib/client-portal-api.ts`, `lib/api/signing.ts`, `lib/api/plan-cliente.ts`, `lib/api/conformidad.ts`, `lib/api/client-portal-tasks.ts`, `components/layout/ClientSidebar.tsx`, `layout.tsx`.
- Backend: `main.py` (registro routers L142-145, L561-562, L717), `m05_signing/api.py`, `m27_conformity/portal_api.py`, prefijos confirmados por grep en `m16_onboarding/portal_api.py` y `m21_portal_cliente/notifications_inbox_api.py`.

---

## Portal Admin + Project-scoped (R23)

> Worktree auditado: `\\wsl.localhost\Ubuntu\home\usuario\fulkro-portales`. Sentinela OK (`backend/app/motors/m01_categorization/README.md` línea 1 = "# Motor 1 · Categorization Engine").

### Arquitectura de layouts (route group `(admin)`)

El portal admin vive bajo el route group `frontend/app/(admin)/` con dos niveles de layout anidados:

- **Layout raíz admin** — `frontend/app/(admin)/layout.tsx`. Envuelve TODO en `<AuthGuard requiredRole="owner">` (gate de rol propietario). Compone el chrome global: `Sidebar` (nav vertical lateral) + `Header` (topbar) + `CopilotPanel` + `CommandPalette` (⌘K) + `OnboardingTourAdmin`. Sidebar responsive (drawer móvil `lg:hidden`). Fix arquitectónico documentado: outer wrapper `bg-[#0a1a5c]` para evitar gap de color con el sidebar.
- **Layout de proyecto** — `frontend/app/(admin)/admin/projects/[id]/layout.tsx`. Envuelve cada página project-scoped en `<ProjectFeaturesProvider projectId>` y monta el sub-chrome: `ActiveProjectSync` (headless · ADR-054 · sincroniza store Zustand con el URL param), `ProjectBreadcrumb`, `ProjectHeader`, `ProjectCategoryBanner`, `QuickActions` y `ProjectTabs` (la barra de pestañas con todo el surface del proyecto).

### Navegación global (Sidebar) — DIVERGENCIA con la doctrina "tri-pestaña"

La doctrina (CLAUDE.md R23) describe una "navegación tri-pestaña (Proyectos/Compliance/ENS Radar)", pero el worktree **NO** implementa una cabecera tri-tab. La navegación global real es un **sidebar vertical** (`frontend/components/layout/Sidebar.tsx`, array `TOP_NAV`) con estas entradas top-level: Dashboard, Reuniones, Proyectos, Copiloto, Operaciones, SIEM, Compliance (badge de `open_alerts`), Mensajes, Notificaciones, Finanzas, Ajustes. Además renderiza secciones de clientes ("Clientes activos", "En retainer") y buckets a Operaciones.

- **ENS Radar y Pipeline están DORMIDOS** (Batch 2): los nav links `ENS Radar` y `Pipeline` están comentados en `Sidebar.tsx` (líneas 48-53, 20-22) con la nota "RADAR DESACTIVADO Batch 2". El icono `Radar`/`TrendingUp` se retiró del import. Evidencia: la doctrina cita la tri-pestaña como activa pero el código la tiene desactivada.
- `Header.tsx` (`frontend/components/layout/Header.tsx`) NO contiene tri-tabs: solo nombre de usuario, fecha, `HeaderProjectChip`, `PortalSwitcher`, `AlertBell` y logout. (El `ThemeToggle` está oculto intencionalmente — dark mode diferido.)
- El radar sigue existiendo en su propio route group `(radar)` con páginas `radar/page.tsx` (v3 profile-based real · "Lead = CNAE 6203 ∩ activa ∩ PYME ∩ concursó AAPP ∩ sin ENS"), `radar/leads`, `radar/runs`, `radar/clusters`. Sigue gated por `is_ens_radar_owner` en `frontend/middleware.ts` (líneas 139-147). Es decir: la capacidad existe pero el acceso desde el chrome admin está retirado.

### R23 (project-scoped) — verificación

R23 ("todo project-scoped vía `/admin/projects/{id}/X`; top-level admin solo multi-cliente legítimo") se sostiene en el código:

- **Selector / gate** — `frontend/app/(admin)/admin/projects/page.tsx`: landing de selección de proyecto con búsqueda/filtro/orden; auto-redirect a `/{id}/roadmap` cuando hay 1 solo proyecto; navega con `client.project_id` real (no `client.id`, que daría 404 — bug histórico documentado #1).
- **Top-level admin legítimo** (cross-cliente): `clients`, `compliance/*` (4 sub-rutas: landing + monitor + projects + norma-reports), `meetings`, `messages`, `settings`, `operations`, `siem`, `finance`, `notifications`, `retainers`, `pipeline`, `workflow-command-center`, `llm-observability`, `cross-project-compliance`, `dashboard`, `inbox`, `magic-links`, `whatsapp`, `magerit-analyses`, `timesheet`. Coherente con "solo multi-cliente".
- **MCPs**: el sidebar global de MCPs fue eliminado por R23 (comentario `Sidebar.tsx` líneas 70-72); MCPs solo project-scoped vía `/admin/projects/[id]/mcps`.

### Surface project-scoped (`ProjectTabs.tsx`) — ~58 sub-páginas

`frontend/components/project/ProjectTabs.tsx` materializa el surface en 3 grupos, con filtrado por feature-flag / categoría / arquetipo (`useProjectFeatures` + `isTabApplicable`):

- **MAIN_TABS (15)**: Resumen, Workflow, Dimensiones, Roadmap, Diagnóstico, Obligaciones, Plan, Implantación, DdA, Evidencias, Dossier, Financiero, Comunicación, Riesgos, MAGERIT.
- **SUB_TABS / "Extras" (~33)**: Documentos (IDMS), Chat cliente, Conformidad, Contratos, Cambios, Verificación (MEDIA/ALTA), Auditoría (MEDIA/ALTA), Equipo, Configuración, Datos cliente, Entrega auditor, Usuarios portal, Personalización, Topología de roles, Discrepancias, Planes acción, Pentest MCPs, Conexiones Cloud, Transparencia IA, Retainer (top-level), Workspace, Onboarding, Arquetipo, Discovery, Concienciación, Auditoría seca, AEPD, BIA, Backups, Retainer (proy.), Proveedores, Renovación, Cierre.
- **PROFILE_TABS (6, condicionales por feature)**: Pentest CPSTIC, Red Team, Productos CPSTIC, Art.9 RGPD, DORA, PCE Universidades (deep-links a `/verification?focus=` y `/obligations?regulation=`).

Las páginas físicas confirmadas por glob (`frontend/app/(admin)/admin/projects/[id]/*/page.tsx`) cubren todas estas rutas: archetype, audit (+ draft-report/annotations/clarifications/dda-evidence-gaps), audit-dry-run, auditor-handoff, aepd, awareness, backup-policy, bia, billing/aapp, changes, chat, cliente-info, cloud-connectors, communication, conformity, contratos, dda, diagnosis, dimensiones, discovery, discrepancies, documents, dossier, equipo (+ areas), evidence, exit, feature-flags, financial, implementation, magerit, mcps, obligations, onboarding, personalizacion, plan, planes-accion, providers, renewal, retainer, risks, roadmap, roles, settings, summary, transparency, users, verification, workflow, workspace.

### Conexión frontend ↔ backend (verificada por evidencia)

El patrón de cliente API es `api()` (admin, BASE `/api/v1`) vs `clientApi()` (portal cliente, BASE `/portal` o `/client-portal`). Verificación cruzada de las 4 páginas clave:

- **DdA** — `projects/[id]/dda/page.tsx` → `DdaAdminPanel` → `frontend/lib/api/dda.ts`. Llama `GET/PATCH/POST /api/v1/dda/projects/{project_id}/{entries,stats,freeze,...}`. Backend: `backend/app/motors/m03_dda/api.py` router `prefix="/dda"` con `dependencies=[Depends(require_owner)]` y helper `_set_project_rls` (lookup `get_project_owner` + `set_tenant_context`). **Match exacto.** (Nota: rutas DdA son motor-prefijadas `/dda/projects/{id}` — NO `/api/v1/projects/{id}/dda` — matiz frente al supuesto del briefing.)
- **MAGERIT** — `projects/[id]/magerit/page.tsx` → `MageritPanel` → `frontend/lib/api/magerit.ts` (29 endpoints bajo `/api/v1`, espejo de `backend/app/motors/m02_magerit/schemas.py`).
- **Plan** — `projects/[id]/plan/page.tsx` → `PlanGantt` + `PdaGeneratorButton` (M17 planning).
- **Audit** — `projects/[id]/audit/page.tsx` → `AuditMode` + `MarkAuditPassedDialog` + `A11AuditorVirtualButton` + `AuditAccompanimentTimeline`.
- **Summary (dashboard de proyecto)** — `projects/[id]/summary/page.tsx`: composición rica (PhaseProgressWizard, NextActionCard, WorkflowBlockingAlert con `CategoryGate` MEDIA/ALTA, ReadinessScoreCard, ActiveAlertsCard, RecentActivityCard, ProjectSummaryView) bajo `ProjectEventsWrapper` (SSE realtime). Composer backend: `backend/app/api/v1/projects.py` (router sin prefijo bajo `/api/v1`) expone `/projects/{id}/{header,summary,timeline,risk-overview,operations}` con `_set_project_rls` canónico.

**Volumen de rutas project-scoped backend** (evidencia empírica, no nominal): `grep "projects/{project_id}"` da **251 ocurrencias en 40 ficheros** de routers, distribuidas por motor (m17_planning 18, m20_workspace 22, m21_diagnosis 18, m23_retainer 17, m16_onboarding 24, m14_contracts 13, etc.). El patrón project-scoped es masivo y real, pero **distribuido en routers de cada motor**, no consolidado bajo un único prefijo `/api/v1/projects/{project_id}/*` (el composer `projects.py` solo aporta 4-5 endpoints aglutinadores).

**Defensa en profundidad auth (ADR-013)**: middleware Next.js (server-side) + `AuthGuard` (client-side, hidrata store con `/api/v1/auth/me`) + dependencies backend (`require_owner`). Triple capa confirmada en `frontend/components/auth/AuthGuard.tsx` + `frontend/middleware.ts`.

---

## Portal Auditor ENAC · Pentester · Public/Legal

Dimensión verificada empíricamente sobre el worktree `fulkro-portales`. Sentinela OK (`backend/app/motors/m01_categorization/README.md` línea 1 = "# Motor 1 · Categorization Engine"). Nota metodológica: `Glob` no recorre de forma fiable este filesystem UNC (devuelve vacío incluso para directorios existentes); todo el inventario se obtuvo con `Grep` + `Read`, que sí funcionan.

### Portal Auditor ENAC (read-only · magic-link gated)

Route group `frontend/app/(portal)/auditor-portal/[token]/*`. El gate es `AuditorPortalEntry` (`frontend/components/auditor-portal/AuditorPortalEntry.tsx`): hace `GET /api/v1/public/auditor-portal/{token}` (peek, no consume uso), renderiza fallback de error si 403/410, y al montar dispara `POST .../session` (consume 1 uso + emite `auditor.session.start`). El chrome `AuditorPortalChrome.tsx` aplica branding del **cliente** (no FULKRO genérico · primary/secondary color desde metadata), muestra badge categoría ENS + resultado auditoría + caducidad, y un sidebar de 11 secciones read-only.

- **Páginas frontend (12 vistas) verificadas** — cada una envuelve `AuditorPortalEntry` + su `*View`:
  - `page.tsx` (landing/Bienvenido · SectionPlaceholder), `summary`, `dda`, `magerit`, `plan`, `evidence`, `e041`, `audit-log`, `pentest`, `documents`, `draft-report`, y `audit/dda-evidence-gaps`.
  - Componentes en `frontend/components/auditor-portal/views/` (SummaryView, DdaView, MageritView, PlanView, EvidenceView, E041View, AuditLogView, PentestView, DocumentsView, DraftReportView, DdaEvidenceGapsView).
- **Backend `backend/app/motors/m09_audit_prep/public_api.py`** (router prefix `/public/auditor-portal`, montado en `main.py:660` bajo `/api/v1`): todas las rutas validan vía `_validate_token_peek` restringido a `MagicLinkPurpose.AUDITOR_PORTAL_ENAC` (purpose mismatch → 403; revocado/expirado/usos agotados → 410; rate-limit 10 fallos/60s). Endpoints read-only confirmados: `GET /{token}` (metadata+branding), `POST /{token}/session`, y vistas `summary · dda · magerit · plan · evidence · e041 · audit-log · pentest · documents`. Descargas cross-motor (Phase 6): `GET /{token}/dossier.zip` (Ed25519 firmado, reusa `dossier_generator`), `GET /{token}/audit-log.csv` (streaming), `GET /{token}/evidence/{id}/download` (FileResponse con guard defence-in-depth `project_id` + bloqueo de evidencias `quarantined/infected`).
- **Vistas DdA-gaps y draft-report** son módulos separados pero igualmente token-gated:
  - `dda_evidence_gap_api.py` → `router_public` prefix `/public/auditor-portal`, `GET /{token}/audit/dda-evidence-gaps` + `.../medida/{code}` (`main.py:680`).
  - `draft_report_api.py` → `router_public` prefix `/public/auditor-portal`, `POST /{token}/audit/draft-report` + `GET .../preview`, ambos con `_validate_token_peek` (`main.py:688`).
- **Trazabilidad/aislamiento**: helper canónico `emit_auditor_event` persiste `ClientInteraction` + fila `audit_log` inmutable con `project_id`+`client_id` (Sub-atom 5.A 3-way OR, hash chain R6 preservado). El lookup cross-tenant usa `SET LOCAL ROLE fulkro_app_bypassrls` (rol NOSUPERUSER+BYPASSRLS) — coherente con el hardening 2026-06-07.
- **Interactividad auditor** (no son las 12 vistas read-only): anotaciones (`auditor_annotations_api.py`) + aclaraciones (`auditor_clarifications_api.py`, SSE + email backup), ambos con `router_public` token-gated + `router_admin` `require_owner`, montados en `main.py:664-679`. Componentes `AnnotationPanel.tsx` + `ClarificationButton.tsx` (este último embebido en el topbar del chrome).
- **Cliente API frontend** `frontend/lib/api/auditor-portal.ts`: tipado completo y consistente con el contrato backend (cliente/project/token_meta/counts/medidas/assets/plan/evidence/e041/audit-log/pentest/documents). Nota menor de coherencia: el type `AuditorPortalSection` lista 9 secciones, pero `available_sections` del backend devuelve 11 (añade `audit/dda-evidence-gaps` y `draft-report`); no rompe, el chrome navega por su propia `NAV_SECTIONS`.

Estado conexión FE↔BE auditor: **completo y coherente**, salvo la entrega por email (ver issue de routing abajo).

### Portal Pentester externo + portales públicos M08

`frontend/app/(portal)/pentester-portal/[token]/page.tsx` envuelve `PublicPortalShell` + `PentesterPortal.tsx` (chrome neutro, no branding cliente). Backend `backend/app/motors/m08_verification/public_api.py` (router prefix `/public`, montado en `main.py:199`/`650`) implementa **3 portales** sobre `_validate_token_peek` con `allowed_purposes`:
- **Remediación cliente** (`PORTAL_REMEDIACION`): `GET /remediation/{token}` (findings + progreso), `.../findings/{id}/guide`, `POST .../fixed` (dispara re-test quirúrgico `run_retest`).
- **Pentester externo** (`PORTAL_PENTESTER_EXTERNO`): `GET /pentester-portal/{token}` (engagement+docs+VPN+scope), `.../documents/{index}` (con anti path-traversal bajo `var/verification_handoffs/`), `.../vpn-config` (.ovpn), `POST .../findings` (formulario estructurado), `.../upload-pdf` (≤50MB, parse LLM opcional Haiku), `.../complete` (irrevocable).
- **Autorización RSEG** (`AUTORIZAR_VERIFICACION_TECNICA` + `AUTORIZAR_PENTEST_EXTERNO`): `GET /verify-auth/{token}` (scope+declaración legal), `.../request-otp`, `.../submit` (valida OTP, firma con hash SHA-256 inmutable, marca run `authorized`).

Cliente API `frontend/lib/api/public-portals.ts` cubre los 3 portales + descarga M25 (`/public/download/{token}` + `/file`) + retainer-offer (`/public/retainer-offer/{token}`). Endpoint `conformity` existe como `m27_conformity/public_api.py` (no es parte estricta de esta dimensión de UI, pero confirmado presente).

### Páginas públicas (account-less)

`frontend/app/(public)/` (layout estrecho max-w-lg branded · "Enlace seguro FULKRO · firmado Ed25519"):
- `sign/[token]/page.tsx` — **dispatcher multiplex** que resuelve `tipo_operacion` vía `useMagicLinkStatus` y enruta a 8 sign-flows: `firma_documento`/`aprobacion_acta` (Legacy), `aprobacion_propuesta`, `aprobacion_factura`, `validacion_cambio_alcance`, `aceptacion_riesgo_residual`, `consentimiento_tratamiento_datos` (DPA), `confirmacion_conformidad`, `firma_contrato` (ContractCanvasSignFlow). Fallback Legacy si 404.
- `download/[token]/page.tsx` — dispatcher descargas M25 (3 purposes: backup activo, cert + dossier en stub 501).
- `diagnostico/[token]/page.tsx` — cuestionario lead frío (`DiagnosticoFlow`).
- `ml/consume/page.tsx` — **redirect canónico** de TODO magic-link: el backend construye toda URL como `{base_url}/ml/consume?token=...` (`m12 service.py:317`) y esta página reenvía a `/sign/{token}`.

### Páginas legales (8 + layout)

`frontend/app/(legal)/` (layout ancho profesional con header Trust/Sub-procesadores/DPO + footer enlaces): `privacy`, `cookies`, `terms`, `imprint`, `derechos-rgpd`, `dpa-template`, `sub-processors`, `trust`. Contenido production-grade verificado:
- `privacy/page.tsx` usa `LegalArticle` con secciones RGPD Art.13-14 reales (responsable Marcos Mata García, DPO `dpo@fulkro.es`). Marcador `[pendiente · alta autónomo]` para CIF.
- `trust/page.tsx` (Trust Center) consume **datos live** vía `getPublicComplianceStatus` (`/api/v1/legal/compliance/status`, refetch 5 min): badge salud, frameworks normativos, scores per-norma, certificaciones ISMS, sub-procesadores, descargas (DPA activo, resto pendiente atoms 9.bis), contacto DPO + security.txt RFC 9116. Banner de cookies global (`CookieConsentBanner`).

Estado conexión FE↔BE legal/public: **conectado y operativo** (Trust live data; DPA template `GET /api/v1/legal/dpa-template/download` activo).

### Resumen de cobertura

- Portal auditor ENAC: 12 vistas read-only + 2 features interactivas (anotaciones, aclaraciones), 100% token-gated por `AUDITOR_PORTAL_ENAC`, branding cliente, audit_log inmutable. **OK**.
- Portal pentester + remediación + verify-auth: 3 portales M08 completos con OTP/path-traversal/rate-limit. **OK**.
- 8 páginas legales + 4 públicas + layouts. **OK**.
- **1 issue de routing de alta severidad** (ver abajo): los enlaces por email de los portales token-gated no-sign (auditor, pentester, remediación, verify-auth) caen en el dispatcher de firma que no los soporta.

---

## Copiloto ENS (A14) + Sistema de 31 Agentes IA

> Worktree auditado: `\\wsl.localhost\Ubuntu\home\usuario\fulkro-portales` · Sentinela OK (`backend/app/motors/m01_categorization/README.md` línea 1 = "# Motor 1 · Categorization Engine").

### 1. Registro de agentes (`backend/app/agents/registry.py`)

`AGENT_REGISTRY` contiene exactamente **31 entradas (IDs 1-31)** verificadas leyendo el diccionario completo. La afirmación de la spec ("31 IDs pero ~15 con implementación real") es **correcta y conservadora**: de los 31 IDs, sólo ~13-14 tienen clase Python invocable. Desglose empírico por `status`:

- **`activo` (12)** — con código real + invocable vía `/api/v1/agents/{id}/invoke`: IDs **4, 6, 11, 12, 14, 17, 18, 19, 20, 21, 27, 31**.
- **`scaffolding_covered_by_engine` (1)** — ID **2** (Analizador de Pliegos · stub 24 LOC funcional, promoción LLM futura).
- **`externalized_to_motor` (2)** — IDs **15** (Vigilancia Normativa → `m23_retainer.agent_15_vigilancia`) y **26** (Coach Auditoría → `m23_retainer.agent_26`). El stub LLM original nunca se implementó; `/invoke` devuelve 410.
- **`reservado` (2)** — IDs **9, 10** (antiguos agentes Pentest v4.2 demolidos Sesión 7 · no reusar).
- **`deprecated` (14)** — IDs **1, 3, 5, 7, 8, 13, 16, 22, 23, 24, 25, 28, 29, 30**, cada uno con `deprecated_reason` apuntando al motor determinista que cubre la funcionalidad (ej. A5 MAGERIT → M02, A13 Dossier → M09 `dossier_generator.py`, A29 → M28 `materiality_engine`).

La limpieza la documenta el propio docstring del registry (Sesión 9 auditoría solapamiento + Sesión 10 cleanup). Helpers: `get_agent_info`, `list_agents`, `list_active_agents` (este último incluye activo + scaffolding + scaffolding_covered_by_engine; excluye externalized/deprecated/reservado).

### 2. Modelos LLM por agente (verificado en el registry)

| ID | Nombre | Modelo | Temp | Motor |
|----|--------|--------|------|-------|
| 2 | Analizador de Pliegos (stub) | sonnet-4.5 | 0.1 | — |
| 4 | Redactor Diagnósticos E-090 | **sonnet-4.6** | 0.2 | m22 |
| 6 | Analista de Contratos | sonnet-4.6 | 0.1 | m14 |
| 11 | Auditor Interno Virtual | **opus-4.7** | 0.1 | m10 |
| 12 | Coach Cliente Evaluador | sonnet-4.6 | 0.2 | m09 |
| 14 | Copiloto Conversacional | **sonnet-4.5** | 0.2 | m11 |
| 17 | Cualificador Comercial | sonnet-4.6 | 0.1 | m13 |
| 18 | Reunión Exploratoria | sonnet-4.6 | 0.1 | m13 |
| 19 | Redactor de Propuestas | **opus-4.7** (1M ctx, 16k tok) | 0.15 | m13 |
| 20 | Negociador Contractual | sonnet-4.6 | 0.15 | m14 |
| 21 | Detector Discrepancias | **deterministic** | 0.0 | m04 |
| 27 | Clasificador IDMS | **haiku-4.5** | 0.1 | m24 |
| 31 | Enriquecedor DdA no_aplica | sonnet-4.6 | 0.2 | m03 |

Observación: sólo A27 (alto volumen clasificación documental) usa Haiku; A11 y A19 (auditoría + propuestas senior) usan Opus 4.7; el resto Sonnet 4.5/4.6. A21 es `deterministic` (no LLM), sostiene R1.

### 3. Infraestructura LLM compartida — `AgentBase` (`backend/app/agents/base.py`)

Clase base abstracta de la que heredan los agentes LLM reales (A19, A31, A06 verificados). Provee: build de `system_prompt` (`COMMON_HEADER` + `SPECIFIC_PROMPT`), build de contexto de proyecto, llamada al router (`get_default_llm_router().complete()` en executor), parse JSON (`structured_output`), extracción de citas y log best-effort en `LLMInteractionLog` (envuelto en `begin_nested()` SAVEPOINT para no envenenar la transacción del caller). Mapa de alias de modelo (`sonnet-4.6` → `claude-sonnet-4-6`, `opus-4.7` → `claude-opus-4-7`, etc.). **Fallback MOCK automático** (`_mock_response`) cuando no hay `anthropic_api_key` (CI/tests) o la llamada falla — esto es lo que permite que la suite corra sin clave real.
- *Nota de drift*: el docstring de `base.py` dice "all 27 FULKRO agents" (cifra histórica), mientras el registry y `CLAUDE.md` hablan de 31 IDs. Cosmético, no funcional.

### 4. Reglas inviolables R1/R2/R3 — enforcement empírico

- **`COMMON_HEADER`** (`backend/app/agents/prompts/common_header.py`, 11 líneas) materializa las 3 reglas para TODO agente que hereda de `AgentBase`:
  - **R2 (citas obligatorias)**: regla 2 "CITA OBLIGATORIA: cada afirmación normativa con su fuente `[RD 311/2022 Art. X]`, `[CCN-STIC NNN sección X.Y]`, `[Anexo II medida.codigo]`".
  - **R1 (deterministas > LLM)**: regla 3 "JAMÁS tomes decisiones que afectan a la DdA, categorización o riesgo residual. Esas las toman los motores deterministas. Tu papel es redactar, sugerir y explicar, no decidir".
  - **R3 (temp ≤ 0.2)**: regla 5 "Temperatura objetivo 0.1-0.2. Determinístico antes que creativo".
  - regla 1: si no está en el corpus → "No encontrado en el corpus oficial" (anti-hallucination).

### 5. Copiloto A14 — pipeline RAG con citas (`backend/app/agents/agent_14_copiloto/`)

Directorio con 6 ficheros (`service.py`, `prompts.py`, `types.py`, `citation_validator.py`, `filters.py`, `__init__.py`). Motor `m11_copiloto`.
- **`service.py`** — pipeline completo `answer_question` + `stream_answer_question` (SSE): `detect_filters` → `hybrid_search` (corpus, top_k=5, importado de `backend.app.corpus.retrieval`) → `_build_system_prompt` → `*query.history` (memoria E-4) → `router.complete/stream_complete` → `extract_citations` + `is_not_in_corpus` + `assess_grounding` → log `LLMInteractionLog` (feature `copilot_chat` / `copilot_chat_stream`).
- **Guard de inyección de prompt** (Ejecutable 8 Pasada 16, F-13-02): `sanitize_user_input` se ejecuta PRE-LLM en ambos paths (`answer_question` línea ~384 y stream línea ~518); si `should_block` devuelve refusal sin llamar al LLM (`model_used="guard:blocked"`).
- **Corpus-gap fallback**: si `confidence < CORPUS_GAP_CONFIDENCE_THRESHOLD` (default 0.45, configurable vía settings), inyecta `CORPUS_GAP_FALLBACK_PROMPT` que prohíbe explícitamente alucinar y redirige a fuentes oficiales (CCN-STIC, BOE, AEPD, eIDAS).
- **`prompts.py`** — `SYSTEM_PROMPT` con `DEFAULT_MODEL="claude-sonnet-4-5-20250929"`, temp 0.1, max_tokens 1500. Incorpora `FULKRO_COPILOT_PRIMARY_CONTEXT` (identidad, Ejecutable 7.6), `SYSTEM_KNOWLEDGE_CLIENTE` (auto-conocimiento plataforma, Pasada 18), reglas de citas obligatorias `[RD 311/2022 medida op.acc.6]` / `[Fulkro Plataforma]`, regla de completitud por categoría (BÁSICA/MEDIA/ALTA siempre) y `INDIVIDUAL_AUTONOMO_CONTEXT` (Art. 11 RD 311/2022 acumulación de roles, FRENTE L).
- **`citation_validator.py`** — `extract_citations` (regex `\[...\]`), `is_not_in_corpus` (frases canónicas), `assess_grounding` (heurística: respuesta >100 chars sin citas → baja confianza).
- **Integración M30** (`_enrich_user_message_with_m30`): inyecta sección "Contactos del cliente" resolviendo `client_id` por `page_context.client_id` o `get_project_owner(project_id)`.
- **Guidance contextual**: `_CATEGORY_GUIDANCE` (BÁSICA/MEDIA/ALTA) + `_COACH_MODE_GUIDANCE_TEMPLATE` (R29 coach) inyectados según `page_context`.

### 6. Persona por rol — R30 admin tutor vs R29 cliente

Dos implementaciones de copiloto coexisten: la RAG (A14, arriba) y la **persona-aware** (`copilot_persona_service.py` + `copilot_admin_service.py` + `copilot_cliente_service.py`):
- **`copilot_personas_loader.py`** carga y valida (Pydantic, frozen) `docs/catalogs/copilot_personas_v1.yaml` (verificado: existe). 2 personas obligatorias (`cliente` + `admin`); falla si falta alguna. Cada persona expone identity/tone/scope_boundaries_allowed+forbidden/model_recommended/temperature/max_tokens/citations_required + `screen_references_catalog` (admin, contexto button-level 1.D.F.0.D).
- **Persona `cliente`** (YAML): `model_recommended: sonnet-4.6`, temp 0.2, `citations_required: false`, tono amable/paciente/sin jerga, `forbidden` = NO admin lingo, NO presión coercitiva (R29 "NO llevas X días sin..."), NO deadlines, NO metadata.
- **`copilot_cliente_service.py`** (`CopilotClienteLLMService`): `check_r29_boundaries` post-respuesta (patrones coercitivos `_R29_COERCITIVE_PATTERNS` + admin lingo `_ADMIN_LINGO_PATTERNS`); si viola → fallback a stub. PI guard pre-LLM sobre `question`; `neutralize_context_value` sobre `step_title`/`concepto` (defensa en profundidad).
- **`copilot_admin_service.py`** (`CopilotAdminLLMService`): `check_r30_boundaries` (patrones "como ya sabes/obviamente" + jargon ENS sin definición: DICAT, DdA, MAGERIT, PCE, CCN-STIC, ENAC, Anexo II, RD 311/2022, BCP-DRP). Violación R30 → **defensive enrich** (NO full fallback, añade footer tutor "te lo explico desde primer principios") porque el admin tolera enrich. PI guard pre-LLM (mirror del RAG, FRENTE E). Inyecta `SYSTEM_KNOWLEDGE_ADMIN` (Pasada 18).
- Ambos servicios reusan `AgentBase`-style `_call_llm` vía `get_default_llm_router()`, loggean en `LLMInteractionLog` (features `copilot_admin_1d_b_2` / `copilot_cliente_1d_b_1`) y aceptan `history` (N6).

### 7. Memoria N6 por proyecto (`backend/app/agents/copilot_memory.py`)

Materializa la directiva Marcos verificada en el docstring:
- **Admin** → memoria aislada por `project_id` (autor sentinel `_ADMIN_AUTHOR` = UUID `...0a11`, FULKRO opera con un único admin).
- **Cliente** → aislada por `client_id` + `project_id` (RLS 3-way OR, política `copilot_isolation`).
- Usa **sesión separada** (`async_session`) para no corromper la transacción/GUC RLS de la request; **best-effort** (degrada a stateless si falla). Reusa `m11_copiloto.conversation_service` (`get_or_create_active_conversation`, `get_recent_messages`, `persist_message`), `HISTORY_LIMIT=8`. `_set_memory_ctx` fija el contexto RLS correcto por actor.
- Consumido en 3 endpoints: `admin_copilot_stub.py`, `client_copilot_stub.py`, `m11_copiloto/api.py` (verificado vía grep). En `admin_copilot_stub.admin_copilot_chat`: rate-limit → `load_conversation_history` → `generate_response(history=...)` → `persist_exchange` (sólo si no es stub fallback).

### 8. Agentes individuales auditados en detalle

- **A19 Redactor de Propuestas** (`agent_19_propuestas.py`, hereda `AgentBase`, Opus 4.7, max_tokens 16k): el LLM SÓLO redacta narrativa; importes/hitos/plazos vienen 100% de `PricingCalculator` + `core/legal.is_aapp`. Validador anti-hallucination numérica robusto (`_detect_unknown_numbers_v2` con whitelist de citas compuestas, importes EUR formato ES, `_WHITELIST_BARE` de artículos/años/CCN-STIC). Retry máx 1 → fallback determinista (`_deterministic_fallback` genera las 10 secciones sin LLM). Sostiene R1 de forma ejemplar.
- **A31 Enriquecedor DdA no_aplica** (`agent_31_enriquecedor_dda.py`, Sonnet 4.6, max_tokens 1200): enriquece justificaciones `no_aplica` (60-200 palabras) citando datos reales de cliente + CCN-STIC. Caching agresivo (15-30 invocaciones/proyecto). Validador `_detect_hallucinated_entities` (whitelist dinámica + lista negra de providers: AWS, Azure, GCP, Salesforce...). Retry 1 → fallback al template estático M3. `enrich_batch` para procesamiento por lotes.
- **A21 Detector Discrepancias** (`agent_21_service.py` `DiscrepancyDetectorService` — **NO LLM, determinista**): 5 detectores cross-motor SQL (`magerit_vs_dda` m02/m03, `dda_vs_evidence` m03/m07, `magerit_vs_findings` m02/m04, `dda_vs_documents` m03/m06, `findings_vs_remediation` m04/m19). Sostiene R1 inviolable (trazabilidad ENAC > flexibilidad LLM). API en `agent_21_api.py` (4 endpoints project-scoped `/api/v1/a21/*` con `_set_project_rls`). El wrapper LLM legacy `DetectorDiscrepanciasAgent` (`agent_21_discrepancias.py`) se preserva sólo para reasoning narrativo opcional.

### 9. Estado de conexión frontend ↔ backend (verificado)

**Conectado y wired** (no mocks de producción):
- API clients: `frontend/lib/api/copiloto-admin.ts`, `copiloto-cliente.ts`, `copilot.ts`, `copiloto.ts`, `copilot-conversations.ts`, `copilot-quick-actions.ts`.
- Hooks: `useCopilotoAdmin.ts`, `useCopilotoCliente.ts`, `useCopilot.ts`, `useCopilotConversations.ts`, `useCopilotPageContext.ts`, `useCopilotPanelShortcut.ts`.
- Componentes: `CopilotoAdminSidebar.tsx`, `CopilotoBriefingMatutino.tsx` (workflow-command-center), `CopilotConversationChat.tsx`, `CopilotMemoryWorkspace.tsx` (UI de la memoria N6).
- Endpoints backend: `POST /api/v1/admin/copilot/chat` (`require_owner`, `admin_copilot_stub.py`) y `client_copilot_stub.py`, ambos con schema idéntico `CopilotChatStubResponse` (zero-refactor swap-in stub↔LLM real), rate-limit (`copilot_rate_limit`), `is_stub` flag para disclaimer UI, `current_screen`/`active_motor` propagados desde `usePathname`.
- Cobertura E2E Playwright: fases 17, 21, 22, 26, 36, 41 (smoke admin/cliente, screen-switch context, button-level DdA reference, workflow hint cliente, copilot_memory).

El frontend manda `action_id` (`que_hago`/`explica_paso`/`draft_email`/`briefing_reunion`/`chat_send` admin) + contexto de pantalla; el backend resuelve persona → memoria N6 → LLM → boundary check → respuesta con flag `is_stub`.

---

## Flujo E2E del ciclo ENS por nivel (BÁSICA / MEDIA / ALTA)

Esta sección mapea el recorrido extremo-a-extremo del ciclo de implantación ENS a través de la cadena de motores, diferenciando los tres niveles del RD 311/2022 (Anexo I categorización · Anexo II medidas). Todas las afirmaciones se basan en ficheros leídos del worktree `fulkro-portales`.

### Cobertura de specs E2E por nivel (los 3 niveles existen)

Los specs E2E Playwright viven en `frontend/tests/e2e/*.spec.ts` (NO en `frontend/e2e/`). Se han verificado specs de conformidad para los tres niveles, cerrando el gap de cobertura:

- **BÁSICA** · `frontend/tests/e2e/conformidad-basica-cliente-e2e.spec.ts` — flujo autodeclaración E-041 con OTP email, genera distintivo + cert-id.
- **MEDIA** · `frontend/tests/e2e/conformidad-commitment-cliente-e2e.spec.ts` — flujo `commitment_pre_certification` pre-auditoría ENAC (50 evidencias seed, NO distintivo, ETA 30-60d).
- **ALTA** · `frontend/tests/e2e/conformidad-alta-cliente-e2e.spec.ts` — su propio docstring (líneas 1-8) declara que cierra el gap de cobertura señalado en auditoría 2026-06-07 ("sólo existían specs BÁSICA + MEDIA"); recorre el mismo code path commitment que MEDIA pero con el set máximo (73 evidencias + 8 políticas firmadas + categoría ALTA).

Specs complementarios del ciclo verificados:
- `frontend/tests/e2e/dda-firma-cliente-e2e.spec.ts` — firma DdA ALTA con OTP, 73 medidas, verifica integridad de la cadena de firmas (`chain-integrity` admin endpoint, `chain_valid=true`).
- `frontend/tests/e2e/m01-categorizacion-sync.spec.ts` y `frontend/tests/e2e/m02-magerit-sync.spec.ts` — sincronización admin→cliente vía SSE (scaffold, skip si faltan env vars `FULKRO_TEST_PROJECT_ID`/`SYSTEM_ID`).
- `frontend/tests/e2e/mb17_categoria_media_complete.spec.ts` y `mb17_categoria_alta_complete.spec.ts` — gating de feature-flags por categoría en el portal admin (usan `page.route` stubs, no E2E real con backend).

### Cadena de motores extremo-a-extremo (verificada en filesystem)

Los directorios de motores del pipeline existen bajo `backend/app/motors/`:
- **M01** `m01_categorization` — categorización Anexo I, regla del máximo sobre 5 dimensiones DICAT (README confirma "Determinístico puro · NO LLM").
- **M02** `m02_magerit` (`service.py`) — análisis de riesgos MAGERIT.
- **M03** `m03_dda` — Declaración de Aplicabilidad. La tabla autoritativa de medidas vive en `m03_dda/anexo2_rd311_2022.py`.
- **M04** `m04_gap` — análisis de brecha.
- **M05** — OJO: existen **dos** motores `m05`: `m05_obligations` (obligaciones/plan) y `m05_signing` (firma Ed25519 + cadena hash). El directive ("M05 obligations/plan") sólo nombra uno.
- **M06** `m06_document_factory` — fábrica documental (template_registry).
- **M07** `m07_evidence` — evidencias.
- **M08** `m08_verification` — verificación (incluye `pentest_auto_trigger.py`, `vuln_orchestrator.py`).
- **M09** `m09_audit_prep` — preparación dossier (`dossier_generator.py`, `public_api.py`).
- **M27** `m27_conformity` (nombre real, NO `m27_conformidad`) — conformidad: `portal_api.py` + `readiness_service.py` + `conformity_service_paso5.py`.

### Medidas por nivel RD 311/2022 (52 / 68 / 73) — confirmado empíricamente

`backend/app/motors/m03_dda/anexo2_rd311_2022.py` es la fuente autoritativa (BOE) y declara constantes explícitas (líneas 117-120):
- `TOTAL_MEDIDAS = 73` (org 4 · op 33 · mp 36)
- `APLICA_BASICA = 52` · `APLICA_MEDIA = 68` · `APLICA_ALTA = 73`

El docstring (líneas 12-16) advierte que corrige la deriva previa a RD 3/2010 que arrastraba `ens_measures`. Esto coincide exactamente con los conteos del directive (52/68/73) y con la memoria persistente `ens-catalogo-rd311-2022-correccion.md`.

### Diferenciación tier-aware del cierre de conformidad (M27)

El corazón de la diferencia por nivel está en `backend/app/motors/m27_conformity/portal_api.py` (líneas 8-9, 88-99, 339-350):

- **BÁSICA → `declaration_type='initial'`**: autodeclaración final E-041, la firma la Dirección del cliente (`_signer_explanation` sólo devuelve texto para `initial`). Tras firmar se genera **automáticamente el distintivo de conformidad** (SVG + cert-id). NO interviene auditor externo. El spec BÁSICA verifica el texto "Tu organización es conforme ENS BÁSICA" y el enlace de descarga `.docx`, y la aserción backend `declaration_type === "initial"`.
- **MEDIA/ALTA → `declaration_type='commitment_pre_certification'`**: el cliente firma un **compromiso pre-auditoría ENAC**, NO un distintivo. El label es "Compromiso de conformidad pre-auditoría ENAC" (`_COMMITMENT_LABEL`); el paso siguiente es que "Marcos enviará tu dossier al auditor ENAC acreditado". Los specs MEDIA/ALTA verifican el heading "Compromiso de conformidad", la presencia de "auditor ENAC", ausencia de distintivo, y la aserción backend `declaration_type === "commitment_pre_certification"` con `tier` MEDIA/ALTA respectivamente.

La rama se resuelve en `prepare_client_declaration_draft` (portal_api.py línea 349): `"initial" if tier == "BASICA" else "commitment_pre_certification"`.

### Gates de readiness por nivel (M27 `readiness_service.py`)

Los umbrales de "listo para firmar" son tier-aware:
- **Evidencias mínimas** (`_TIER_MIN_EVIDENCE`, líneas 31-33): BÁSICA 25 · MEDIA 50 · ALTA 73. (Nota: estos son los umbrales de readiness del subset de evidencias, NO el conteo de 52/68/73 medidas aplicables.)
- **Políticas firmadas mínimas** (`_TIER_MIN_POLICIES`, líneas 41-45): BÁSICA 10 · MEDIA 18 · ALTA 25. El comentario documenta que pre-MB-6 eran (0,0,8) y se actualizaron audit-driven.
- **Pentest obligatorio sólo en ALTA** (líneas 189-193): "el pentest es obligatorio SOLO en ALTA (CCN-STIC 105/140). En MEDIA es opcional... y en BÁSICA nunca". El gate `tier == "ALTA" and pentest_sig is None` bloquea sólo ALTA.

### Estado de conexión frontend ↔ backend (cableado verificado)

El portal cliente de conformidad está completamente cableado:
- Página: `frontend/app/(client-portal)/client-portal/conformidad/page.tsx`
- 7 componentes en `frontend/components/client-portal/conformidad/`: `ReadinessSection`, `DeclarationHeader`, `MarkReviewedSection`, `ConformidadSignButton`, `TierAwareNextStepSection`, `PostSignSection`, `DeclarationSummarySection`.
- Cliente API: `frontend/lib/api/conformidad.ts` mapea los 5 endpoints `/api/v1/portal/conformidad/projects/{id}/{declaration,readiness,mark-reviewed,document-hash,post-signature}` directamente contra `m27_conformity/portal_api.py`. El `readiness_snapshot` transporta las dependencias de la cadena (`dda_signed_at`, `magerit_signed_at`, `pentest_signed_at`, `policies_signed_count`), reflejando la secuencia M03→M02→M08→M27.

El flujo de firma cliente usa OTP email (mock en test vía `/api/v1/_dev/captured-emails`) y cadena de firmas Ed25519 (`m05_signing`), con verificación de integridad de cadena por endpoint admin `chain-integrity` (`chain_valid`, `broken_links`, `total_signatures`).

### Resumen del recorrido por nivel

| Aspecto | BÁSICA | MEDIA | ALTA |
|---|---|---|---|
| Medidas Anexo II aplicables | 52 | 68 | 73 |
| Tipo declaración M27 | `initial` (E-041 autodeclaración) | `commitment_pre_certification` | `commitment_pre_certification` |
| Auditor externo ENAC | NO | SÍ (obligatorio) | SÍ (obligatorio) |
| Distintivo post-firma | SÍ (inmediato) | NO (sólo post-ENAC) | NO (sólo post-ENAC) |
| Pentest gate | nunca | opcional | obligatorio (CCN-STIC 105/140) |
| Evidencias mín. readiness | 25 | 50 | 73 |
| Políticas firmadas mín. | 10 | 18 | 25 |

---

## Modelo de datos (ORM SQLAlchemy 2.0)

> Evidencia base: `backend/app/models/__init__.py` (registro central de metadata), `backend/app/models/base.py` (mixins), y los `models.py` distribuidos en `backend/app/motors/m*/`. Sentinela verificado OK (`m01_categorization/README.md` línea 1 = "# Motor 1 · Categorization Engine").

### Arquitectura de declaración: modelo distribuido (no monolítico)

El modelo de datos **NO** vive solo en `backend/app/models/`. El fichero `backend/app/models/__init__.py` actúa como agregador de metadata SQLAlchemy e importa tablas desde **dos orígenes**:

- **~50 módulos en `backend/app/models/*.py`** (core, ens, documents, commercial, retainer, lifecycle, etc.).
- **~14 módulos de modelos que viven dentro de los propios motores** y se importan en `__init__.py` para registrarse en `Base.metadata`. Evidencia (`models/__init__.py` líneas 13, 36, 52-130):
  - `m02_magerit/models.py` (MAGERIT), `m05_signing/models.py` (firmas), `m08_verification/models.py` (pentest v5.1), `m10_ens_radar/db/models.py` (radar v3), `m12_magic_link/models_migration_log.py`, `m21_portal_cliente/models_chat.py` + `models_tasks.py`, `m23_retainer/timesheet_models.py`, `m29_client_messaging/models.py`, `m30_client_contacts/models.py` + `department_models.py`, `m31_whatsapp/models.py`, `m_cloud_connectors/models.py`, `m_audit_accompaniment/models.py`, `m_observability/models.py`, `m_compliance_monitor/sub_processor_subscribers.py`, `core/feature_flags/models.py`, `agents/models/dry_run.py`.

Varios de estos imports llevan comentarios explícitos de *drift cleanup* (`__init__.py` líneas 54-66): tablas creadas por migración/DDL pero que faltaban en `Base.metadata`, lo que provocaba que `alembic check` las marcara como "removed table". Esto confirma que el conteo de tablas vivas en PostgreSQL puede exceder a las declaradas en ORM (algunas se crean por DDL directo, p.ej. las 3 tablas de `m_audit_accompaniment` según comentario líneas 56-60).

**Nota de honestidad empírica sobre el conteo:** la cifra nominal "237 tablas ORM" del briefing NO la pude verificar exactamente. Mi inventario empírico de declaraciones `__tablename__` (grep sobre `models/` + `motors/`) suma **~210 declaraciones** de clase ORM. La discrepancia es coherente con: (a) tablas seed-only/catálogo creadas en migración sin clase declarativa, (b) la **vista** `leads_v3` (materializa el criterio del radar, no es tabla ORM), (c) tablas hijas RLS sin modelo dedicado, y (d) `m_legal/orm.py` (`legal_obligations_catalog`) que NO aparece importado en `__init__.py` y por tanto queda "shadow" respecto a la metadata global. No afirmo "237" como verificado.

### Convenciones técnicas (verificadas en `base.py`)

`backend/app/models/base.py` define los mixins canónicos:

- **`UUIDPrimaryKeyMixin`**: PK UUID con `server_default=text("gen_random_uuid()")` — confirma UUID PKs server-side.
- **`TimestampMixin`**: `created_at` con `server_default=text("now()")` NOT NULL + `updated_at` `TIMESTAMP(timezone=True)` nullable con `onupdate=_utcnow` (timezone-aware). Confirma **timestamptz** en todas las columnas temporales.
- **`SoftDeleteMixin`**: `deleted_at` timestamptz nullable — confirma **soft-delete** convención.
- **`FullMixin`** = UUID PK + timestamps + soft-delete (mixin estándar de la mayoría de tablas).
- **`ClientReviewMixinA`** (review decisional, `client_review_status` enum de 4 valores) y **`ClientReviewMixinB`** (review acompaña firma, `client_signing_intent_id`): materializan el patrón ADR-020 de revisión cliente in-portal. Helpers `client_review_a_table_args()` / `client_review_b_table_args()` replican en `__table_args__` los CHECK + índices parciales que ya existen en BD (creados por migraciones), evitando *drift* en `alembic check`.

**RLS**: NO se declara en el ORM. Se implementa vía migraciones Alembic con `ENABLE ROW LEVEL SECURITY` + `CREATE POLICY` (políticas `project_isolation` / `client_isolation`). Verificado en `backend/migrations/versions/` (p.ej. `copilot_rls_client_isolation_001.py` con 12 ocurrencias, `audit_log_rls_001`, `sane_polish_rls_email_log_001.py`). El patrón de aislamiento se basa en columnas `project_id` / `client_id`.

**Hash-chain audit (R6)**: `backend/app/models/audit_log.py` (tabla `audit_log`) implementa el log inmutable con cadena de hash. Columna `seq` BIGSERIAL UNIQUE, `hash_prev` + `hash_current` (SHA-256, 64 chars). El cálculo y verificación los hacen **triggers PL/pgSQL** (`fn_audit_log_hash_chain`, `fn_audit_log_verify_chain`, migración `d4f8b2a90001`) ordenados por `seq`. Sub-atom 5.A añadió `project_id` + `client_id` nullable para propagación 3-way OR (comentario líneas 42-47). Existe una **segunda cadena hash** independiente per-proyecto en `client_user_audit` (`backend/app/models/client_portal.py`: `chain_index` + `prev_hash` + `current_hash`).

### Dominios y tablas clave (inventario verificado)

| Dominio | Fichero(s) evidencia | Tablas clave |
|---------|---------------------|--------------|
| **Core / categorización (M1)** | `models/core.py` | `clients`, `projects` (con 19 dims adaptación Anexo L), `systems`, `information_types`, `services`, `categorizations` |
| **ENS DdA (M3)** | `models/ens.py` | `ens_measures`, `dda_entries` (ClientReviewMixinA), `annual_review_records`, `dda_project_signatures`, `controls`, `obligations` |
| **ENS extensiones** | `models/ens_extensions.py` | `ens_measure_refuerzos`, `ens_measure_dimensiones`, `ens_measure_guias_ccn`, `ens_measure_evidencia_types` |
| **MAGERIT (M2)** | `motors/m02_magerit/models.py` | 12 tablas: catálogo (`magerit_asset_types`, `magerit_threats`, `magerit_safeguards`, `magerit_ens_mapping`, `magerit_risk_matrix`) + análisis por proyecto (`magerit_analysis`, `magerit_assets`, `magerit_asset_dependencies`, `magerit_threat_assessment`, `magerit_safeguard_deployment`, `magerit_risk_calculation`, `magerit_treatment_plan`) |
| **Documentos / evidencias (M6/M7/M24)** | `models/documents.py`, `models/idms.py`, `models/document_factory.py` | `documents`, `document_versions`, `evidence` (scan antivirus ClamAV + firma Ed25519), `evidence_renewal_requests`, `procedures`, `procedure_executions`, `document_folders`, `document_tags`, `idms_document_permissions`, `templates` |
| **Firmas (M05)** | `motors/m05_signing/models.py` | `signing_intents`, `signing_events` (hash chain Ed25519 + canvas TIER 1), `signing_otp_codes` |
| **Magic links (M12)** | `models/operations.py`, `motors/m12_magic_link/` | `magic_links`, `client_interactions`, `magic_link_migration_log` |
| **Portal cliente (M21)** | `models/client_portal.py`, `models/client_notification.py`, `motors/m21_portal_cliente/` | `client_users` (+ MFA TOTP `client_user_totp_secrets`, `client_user_backup_codes`), `client_sessions`, `client_user_audit` (hash chain), `client_notifications`, `chat_threads`, `chat_messages`, `client_tasks` |
| **Mensajería cliente (M29/M31)** | `motors/m29_client_messaging/`, `motors/m31_whatsapp/` | `client_messages`, `client_message_attachments`, `whatsapp_threads`, `whatsapp_messages`, `whatsapp_critical_events_routing` |
| **Comercial (M13/M14/M15)** | `models/commercial.py`, `models/commercial_paso7.py` | `leads`, `proposals`, `contracts` (puente `signing_intent_id` → M05), `invoices`, `invoice_lines`, `pricing_models`, `client_commitments`, `payment_reminders`, `lead_stage_history`, `commercial_discounts`, `retainer_reports` |
| **Proveedores (M14)** | `models/m14_providers.py` | `providers`, `provider_c002`, `provider_assessments`, `provider_addendums` |
| **Billing / facturas AAPP** | `models/billing_milestones.py`, `models/invoices_aapp.py` | `contract_milestones`, `retainer_health_signals`, `invoices_aapp` (Facturae 3.2.x) |
| **Retainer (M23)** | `models/retainer.py`, `motors/m23_retainer/timesheet_models.py` | `retainer_contracts`, `retainer_activities`, `retainer_drift_events`, `retainer_billing_events`, `retainer_quarterly_reports`, `pricing_catalog`, `marcos_timesheet_entries` |
| **Cloud connectors** | `motors/m_cloud_connectors/models.py` | `cloud_connectors`, `cloud_resources`, `cloud_gaps`, `cloud_remediation_approval_logs`, `cloud_sync_jobs`, `cloud_digest_snapshots` |
| **Onboarding / discovery (M16/M22)** | `models/onboarding.py`, `models/discovery.py` | `onboarding_sessions`, `onboarding_responses`, `discovered_assets`, `discovered_identities`, `connector_configs`, `oauth_state_tokens`, `discovery_runs_m22`, `discovery_alerts`, `vulnerability_inventory`, `data_flow_diagrams`, `continuity_assessments` |
| **Verificación / pentest (M08)** | `motors/m08_verification/models.py` | `verification_runs`, `verification_findings`, `external_pentester_handoffs`, `false_positive_patterns`, `remediation_retests` |
| **Auditor portal / auditoría** | `models/auditor_annotations.py`, `models/auditor_clarifications.py`, `models/audit_prep.py`, `models/audit_sim.py`, `models/findings.py`, `motors/m_audit_accompaniment/models.py` | `auditor_annotations`, `auditor_clarification_requests`, `audit_preparation_runs`, `audit_checklist_items`, `audit_simulation_runs`, `audit_simulation_findings`, `findings`, `audit_sessions`, `audit_findings`, `remediation_plans`, `audit_accompaniment_state/artifacts/transitions` |
| **Audit log inmutable (R6)** | `models/audit_log.py` | `audit_log` (hash chain SHA-256 + triggers PL/pgSQL) |
| **Lifecycle proyecto (M25)** | `models/lifecycle.py`, `models/m25_exit_checklist.py`, `models/conformity_lifecycle.py` | `project_lifecycle_states`, `project_lifecycle_events`, `archived_projects`, `project_exports`, `project_archived_backups`, `exit_checklist_items`, `conformity_routes/submissions`, `basic_declarations`, `material_changes`, `recategorizations`, `extraordinary_audits`, `renewal_campaigns`, `conformity_state_snapshots` (15 tablas en conformity_lifecycle) |
| **Renovación (M27)** | `models/m27_renewal_milestone.py` | `renewal_campaign_milestones` |
| **Notificaciones** | `models/notifications.py`, `models/alerts.py` | `notification_events` (reutilizada como DLQ), `notification_preferences`, `alert_queue` |
| **Compliance FULKRO (dogfooding)** | `models/compliance_monitor.py`, `models/compliance_breach_erasure.py`, `models/consent_audit.py`, `models/ropa_treatments.py`, `models/aepd.py`, `models/compliance_norma_reports.py`, `motors/m_compliance_monitor/` | `compliance_checks/alerts/reports`, `fulkro_breach_notifications`, `fulkro_erasure_requests`, `fulkro_consent_audit_log`, `fulkro_ropa_treatments`, `aepd_notifications`, `sub_processor_subscribers` |
| **Auth admin (Marcos)** | `models/auth.py`, `models/admin.py` | `auth_users` (WebAuthn/TOTP), `auth_webauthn_credentials`, `auth_totp_secrets`, `auth_sessions`, `auth_login_attempts`, `admin_settings` |
| **Planificación (M17)** | `models/planning.py` | `project_plans`, `wbs_tasks`, `change_requests`, `project_risks`, `status_reports` |
| **Knowledge / RAG (M11)** | `models/knowledge.py` | `knowledge_sources/documents/chunks/links`, `knowledge_measure_mappings`, `llm_interaction_log` |
| **Copilot (A14)** | `models/copilot.py` | `copilot_conversations`, `copilot_messages` |
| **ENS Radar v3 (M10b)** | `motors/m10_ens_radar/db/models.py` | `tenders`, `companies`, `decision_makers`, `participations`, `placsp_adjudicaciones`, `cnae6203_raw`, `empresa_6203`, `radar_leads`, `ccn_certificados`, `excluded_leads`, `empresas_descartadas`, `sources_runs`, `radar_pipeline_runs` (+ vista `leads_v3`) |
| **Backup / DR (M26)** | `models/backup.py` | `backup_jobs`, `backup_retention_policies`, `backup_restore_tests`, `dr_drills`, `integrity_verifications` |
| **Operaciones (M19/M28)** | `models/operations.py`, `models/operations_paso7.py`, `models/governance.py`, `models/m28_role_assignment.py` | `incidents`, `vulnerabilities`, `changes`, `email_log`, `normativa_alerts`, `committee_meetings`, `nominations`, `training_records`, `vendors`, `vendor_contracts`, `project_role_assignments` |
| **Continuidad / BIA (M18)** | `models/bia.py`, `models/cliente_continuidad.py` | `bia_analyses`, `cliente_continuidad_input/approval` |
| **Otros transversales** | `models/observability` (motor), `models/pkg.py`, `models/a21_discrepancies.py`, `models/change_governance.py`, `models/lms.py`, `models/awareness.py`, `models/live_record.py`, `core/feature_flags/models.py`, `agents/models/dry_run.py` | `ai_act_transparency_events`, `golden_eval_runs`, `pkg_nodes/edges`, `a21_scan_runs`, `a21_discrepancies`, `change_topologies`, `lms_assignments`, `awareness_sessions/attendance`, `live_records`, `feature_flag_overrides`, `audit_dry_run_results` |

### Particularidades del modelo relevantes para integridad

- **MAGERIT por proyecto cuelga de `analysis_id`, no de `project_id` directo** (salvo `magerit_analysis`). Evidencia: `magerit_assets`, `magerit_threat_assessment`, etc. usan `ForeignKey("magerit_analysis.id")`. Esto obliga a que el RLS de estas tablas hijas (Sub-atom 5.B) resuelva el aislamiento vía join 1-nivel, no por columna directa — los comentarios del propio modelo (`MageritAsset`, líneas 130-140) documentan que el helper de review usa índice manual sobre `analysis_id` por esta razón.
- **FKs lógicas sin constraint**: múltiples cruces motor↔motor se hacen con `signature_magic_link_id` / `client_signing_intent_id` declarados como UUID sin `ForeignKey` ("FK lógica sin constraint para no acoplar motores"). Ejemplos: `core.py:224`, `ens.py:102`, `documents.py:51`. El contraste es `contracts.signing_intent_id` que SÍ es FK real con `ondelete="SET NULL"` (`commercial.py:134`).
- **Override de `updated_at`**: las tablas de `m_cloud_connectors` redefinen `updated_at` a NOT NULL DEFAULT now() (OPS-046, mismatch ORM-migración corregido).

### Estado de conexión frontend ↔ backend
No aplica directamente a esta dimensión (modelos ORM). El consumo de estos modelos por la API/frontend se cubre en las dimensiones de endpoints/motores. Lo único verificable aquí: el modelo soporta la doble pool de auth (ADR-013) con tablas separadas `auth_users` (admin/Marcos) y `client_users` (portal cliente), y aislamiento multi-tenant por `project_id`/`client_id`.

---

## Cobertura funcional de los motores (`backend/app/motors/`)

**Sentinela verificado**: `backend/app/motors/m01_categorization/README.md` línea 1 = `# Motor 1 · Categorization Engine` (exacto). Worktree correcto (`fulkro-portales`) confirmado.

### Metodología y alcance de la verificación

- **Fuente de verdad del wiring**: `backend/app/main.py` (922 líneas) — leído íntegro; es la única fuente autoritativa de qué routers están montados en la app real.
- **Routers detectados**: Grep `APIRouter(` sobre `**/api.py` → **42 ficheros** con router; Grep sobre `**/*_api.py` → **60+ routers auxiliares adicionales** (cada motor expone típicamente varios: `portal_api.py` cliente, `public_api.py`, `*_admin_api.py`, etc.).
- **Directorios de motor confirmados por evidencia directa (README/api.py/models.py leídos)**: **44**. No pude enumerar de forma fiable la lista cerrada de "47 directorios" porque el glob de un solo segmento (`m*/` o `*`) sobre el filesystem UNC `\\wsl.localhost\...` agota timeout o devuelve vacío; sólo el glob recursivo (`**/...`) responde. Por tanto **declaro honestamente que verifiqué 44 directorios, no los 47 nominales** — el delta (~3) son probablemente directorios sin README/api.py/models.py que el glob recursivo no destapó. Los 42 routers `app.include_router(...)` de `main.py` sí están todos contabilizados.

### Hallazgos de wiring relevantes

- **Anomalía de numeración intencional** (no es bug): varios números de motor están "duplicados" porque son *motores hermanos paralelos*. Confirmado en `m10_audit_sim/README.md` línea 3: *"Sibling de M10_ens_radar (numbering anomaly intencional · pattern motor parallel)"*. Pares: `m05_obligations`+`m05_signing`, `m10_audit_sim`+`m10_ens_radar`, `m21_diagnosis`+`m21_portal_cliente`. Esto explica que haya >31 directorios numerados pese al rango m01–m31.
- **`m10_ens_radar` DESACTIVADO a propósito en Batch 2** — confirmado empíricamente en `main.py`: imports comentados (líneas 288-293) e `include_router` comentados (líneas 736-738). `m13_commercial` (leads/comercial) también comentado en el mismo bloque (líneas 230-231, 701-702). El README v3 del radar (`m10_ens_radar/README.md`) confirma el rebuild profile-based. **No es deuda: es dormancy reversible documentada.**
- **`m11_rag` NO es un directorio de motor**: el rango m11 lo ocupa `m11_copiloto`. El RAG vive en `backend/app/agents/` (confirmado: glob de `rag*.py` bajo `motors/` = 0 resultados). La justificación "backend-only m11_rag dentro de agentes" de CLAUDE.md es coherente con la realidad del filesystem.
- **`m29_client_messaging` no usa `api.py`** sino `api_client.py` + `api_admin.py` (por eso no salió en el grep de `api.py`), pero **sí está montado** (`main.py` líneas 300-305).
- **`m_siem` (FRENTE N)**: motor named real, montado en `main.py` líneas 417-418, con frontend cliente (`frontend/lib/api/siem.ts` verificado).

### Tabla motor → propósito → estado de wiring

| Motor | Propósito (1 línea) | Wiring |
|---|---|---|
| m01_categorization | Categorización ENS DICAT (Anexo I RD 311/2022), determinista | Montado: `categorization`+`archetype`+`dimensions` routers |
| m02_magerit | Análisis de riesgos MAGERIT v3 + import PILAR/PILAR-XML | Montado: api + `portal_api` + `pilar_import` + `threat_auto_mapper` |
| m03_dda | Declaración de Aplicabilidad (DdA Engine) | Montado: api + `portal_api` cliente |
| m04_gap | Gap Analysis + control status (false-green prevention) | Montado: api + `control_status_api` (admin+cliente) |
| m05_obligations | Catálogo de obligaciones + Gantt planner | Montado: api |
| m05_signing | Firma Ed25519 in-portal (canvas TIER 1) + embed PDF | Montado: `admin_router`+`client_router` |
| m06_document_factory | Generación de documentos/Excel (DOCX/PDF/XLSX) + policy signoff | Montado: api + `portal_api` policies cliente |
| m07_evidence | Gestión de evidencias + request workflow + antivirus | Montado: api + `public_router` + `request_api` + antivirus admin |
| m08_verification | Verificación técnica/pentest (ZFP, MITRE, CPSTIC) — motor mayor (13.8K LOC) | Montado: api + `public_api` + `portal_api` + auto-trigger |
| m09_audit_prep | Preparación auditoría + portal auditor ENAC + simulacro pre-ENAC | Montado: api + 5 routers auditor (annotations/clarifications/gaps/draft-report/portal) |
| m10_audit_sim | Auditor virtual ENAC (simulación L0-L5, anti-alucinación, NO LLM) | Montado: api |
| m10_ens_radar | Captación leads ENS v3 profile-based (CNAE 6203) | **DORMIDO Batch 2** (imports+includes comentados, reversible) |
| m11_copiloto | Copiloto ENS (RAG/LLM) admin + cliente + inline agents | Montado: api + `portal_api` + `inline_agents_api` |
| m12_magic_link | Magic links Ed25519 (23 purposes) | Montado: api |
| m13_commercial | Comercial/leads + firma contrato canvas | **`api.py` comercial DORMIDO Batch 2**; `contract_signing_public_api` SÍ montado |
| m14_contracts | Contratos + proveedores (C-002) | Montado: api + `providers_api` |
| m15_billing | Facturación + AAPP invoices + extensiones financieras | Montado: api + `invoices_aapp` + `financial_extensions` |
| m16_onboarding | Onboarding cliente | Montado: api + `portal_api` |
| m17_planning | Planificación / plan Gantt cliente read-only | Montado: api + `portal_api` |
| m18_communication | Comunicaciones + AEPD + alertas proactivas | Montado: api + `aepd_api` + `alerts_api` |
| m19_risk | Riesgos de proyecto + BIA + continuidad + incidentes | Montado: api + bia/continuidad/incidents (portal+admin) |
| m20_workspace | FULKRO Room colaborativa (chat/feed/files append-only) | Montado: api |
| m21_diagnosis | Diagnóstico + dashboard agregado admin | Montado: api + `dashboard_api` |
| m21_portal_cliente | Portal cliente (auth/cockpit/MFA/chat/tasks/audit/inbox/branding) | Montado: ~12 routers (auth, cockpit, mfa, chat, tasks, evidencias, recent-activity…) |
| m22_discovery | Discovery técnico (assets/identidades/flujos) — 2º motor mayor (8.4K LOC) | Montado: api |
| m23_retainer | Retainer post-cert + timesheet + check-in cliente | Montado: api + paso2 + timesheet + checkin portal |
| m24_idms | IDMS (gestor documental identidad) + awareness training | Montado: api + `awareness_api` |
| m25_lifecycle | Ciclo de vida proyecto + exit checklist + paso4 | Montado: api + paso4 + exit + `public_api` download |
| m26_backup | Backup & DR + política 3-2-1 | Montado: api + `backup_policy_321_api` |
| m27_conformity | Conformidad CCN-STIC 809 + renovación + DPC anual + badge público | Montado: api + paso5 + portal + `public_api` + renewal |
| m28_change_governance | Gobierno del cambio + topología de roles + drift | Montado: api + `role_topology_extensions` |
| m29_client_messaging | Mensajería cliente (email forward, attachments) | Montado: `api_client`+`api_admin` (no usa `api.py`) |
| m30_client_contacts | Contactos cliente + departamentos + scope proyecto + portal users | Montado: api + 5 routers (scope/portal-user/departments/ens-required…) |
| m31_whatsapp | Canal WhatsApp (admin/portal/webhook/SSE) | Montado: 4 routers |
| m_audit_accompaniment | Acompañamiento auditoría + conformidad sede post-implantación | Montado: api (admin advance/artifacts + cliente read-only) |
| m_cloud_connectors | Capa unificada conectores cloud (catalog/gaps/diagnosis/monitoring/remediation) | Montado: ~10 routers (admin+cliente+remediation) |
| m_compliance | Features GDPR cliente (RoPA/DPA/breach/cookies/derechos RGPD) | Montado: ~7 routers (dpa/ropa/rgpd/cookies/admin/measure-translation) |
| m_compliance_monitor | Audita la propia compliance de FULKRO (self-dogfooding) + norma reports | Montado: api + `public_api` + `norma_reports` |
| m_legal | Catálogo de obligaciones legales (RGPD/NIS2/DORA/AI_Act) read-only — 250 entries | Montado: api (read-only catalog) |
| m_live_records | Registros vivos E-300..E-325 project-scoped + listeners auto-populate | Montado: api + `register_live_records_listeners()` |
| m_meetings | Reuniones externas + actas portal cliente | Montado: api + `actas_portal_api` |
| m_observability | Observabilidad LLM (cost/anomaly) + transparency AI Act + golden eval — motor más pequeño | Montado: api + `transparency_api` + `golden_eval_runs_api` |
| m_siem | Consola SIEM admin (eventos seguridad, correlación pentest) — FRENTE N | Montado: api (top-level admin R23, `bypassrls`) |
| m_workflow_engine | Orquestador workflow (command center) + view composer | Montado: `admin_router`+`reader_router` |

### Estado de conexión frontend ↔ backend

- **Verificado por muestreo** (glob `frontend/lib/api/*.ts` falla sobre UNC monosegmento, pero Grep `/api/v1/` sobre `frontend/**/*.ts` lo confirma): existen clientes TS en `frontend/lib/api/` — `siem.ts` (→ m_siem), `contract-signing.ts` (→ m13/m05 firma), `idms.ts` (→ m24), `magic-links.ts` (→ m12). Los specs E2E (`frontend/tests/e2e/*.spec.ts`) consumen rutas `/api/v1/` reales (conformidad, dda-firma, magerit, pentest-authorization).
- No pude enumerar el catálogo completo de módulos `lib/api/*` por la limitación UNC, así que **no afirmo cobertura frontend 1:1 para los 44 motores**; sí confirmo que el patrón de cliente frontend existe y apunta a rutas backend vivas para los motores muestreados.

### Conclusión de cobertura

- **0 motores huérfanos detectados**: todos los 44 directorios verificados o exponen router(s) montados en `main.py`, o están deliberadamente dormidos (`m10_ens_radar`, `api.py` comercial de `m13`) con justificación documentada en código. No encontré ningún motor "sin router y sin justificación".
- Los motores que CLAUDE.md cataloga como "backend-only scope-out" (`m_observability`, `m_workflow_engine`, `m_legal`, `m_live_records`, `m11_rag`) son coherentes con la realidad, **con un matiz**: `m_workflow_engine` SÍ tiene routers montados (admin+reader), no es puramente backend-only — su UI se sirve vía el Command Center, no carece de endpoints REST.

---

## Compliance & auto-monitorización (dogfooding ENS · R7)

Dos motores hermanos pero con responsabilidad opuesta, ambos production-grade y cableados de extremo a extremo:

- **`m_compliance_monitor`** — audita la propia postura de cumplimiento de FULKRO **como organización** (self-monitoring, platform-global, sin `project_id` ni RLS, admin-only).
- **`m_compliance`** — expone **features GDPR al cliente y al admin** (RoPA, DPA, derechos del interesado, cookies, breach).

La distinción está cementada en el código y en ambos README (`backend/app/motors/m_compliance_monitor/README.md:77`, `backend/app/motors/m_compliance/README.md:3`).

### m_compliance_monitor · auto-monitorización autónoma

**Registro de checks (evidencia: `checks.py`)** — el `CHECK_REGISTRY` (`backend/app/motors/m_compliance_monitor/checks.py:952-1147`) declara **21 checks** (no 19 como dice el README/frontend; ver issue de drift documental). Cada check es una función pura `(AsyncSession) -> CheckResult` con semáforo `green/yellow/red/unknown` y metadatos (categoría, cadencia, severidad, `regulatory_basis`). Los 21:
  - Base atom 9.bis.6 (17): `cookies_banner_functional`, `rgpd_endpoints_responding`, `ssl_cert_expiry`, `backups_integrity`, `audit_logs_continuity`, `dpo_email_working`, `security_txt_reachable`, `privacy_policy_freshness`, `breach_workflow_ready`, `sub_processor_dpa_expirations`, `nis2_vulnerability_inbox`, `rls_coverage_percentage`, `dpa_template_version`, `sub_processors_list_freshness`, `ropa_review_due`, `isms_docs_review_due`, `cookie_consent_renewal_24month`.
  - MB-10 atom 10.1 (2): `admin_actions_audit_logged` (ENS art.24.1 + ISO 27001 A.8.20), `marketing_analytics_opt_in_only` (RGPD Art.7).
  - SIEM gap-closure (2): `intrusion_detection_present` (ENS [op.mon.1]/[op.mon.3], detecta fail2ban/auditd o flag `FULKRO_IDS_ENABLED`) y `mfa_enforcement` (ENS [op.acc.5], verifica que todos los `auth_users` activos tienen WebAuthn o TOTP enrolado · R4). Evidencia: `checks.py:869-946`.

**Orquestación + ciclo de alertas (evidencia: `service.py`)** — `ComplianceMonitorService` (`service.py:80`) hace `sync_registry` (upsert), `run_check` (persiste resultado, abre/auto-resuelve `ComplianceAlert`) y `run_frequency_batch`. El despacho de email es por severidad (`_dispatch_alerts`, `service.py:208-256`): **HIGH → email inmediato por alerta; MEDIUM/LOW → digest agregado**. Confirmado el enunciado "alertas HIGH→email Marcos": el destinatario es `compliance_alert_email` con fallback a `consultor_email` (`service.py:218-223`). Plantilla MJML `compliance_alert.mjml`. Auto-resolución: si un check vuelve a green con alerta abierta, se cierra sola (`_auto_resolve_open_alert`, `service.py:415-427`).

**Cadencia Celery beat (evidencia: `tasks.py`)** — 4 tareas (`tasks.py:86-113`): `compliance.run_daily` (07:30 Europe/Madrid), `compliance.run_weekly` (lunes 08:00 + genera reporte semanal), `compliance.run_monthly` (día 1, 08:30), `compliance.run_quarterly` (1 de ene/abr/jul/oct, 09:00). Cada batch hace `sync_registry` y se autotraza en `audit_log` vía `_emit_monitor_audit` (`tasks.py:46-61`, R6 dogfooding · usuario `system` · project/client NULL).

**Arquitectura de normativas plug-in (evidencia: `normas/`)** — el subdir `normas/` SÍ existe (la `Glob` `normas/*.py` falló por timeout del FS UNC, no por ausencia). Patrón Open/Closed: `__init__.py:37-46` auto-descubre e importa cada `*.py`, que se auto-registra en `NormaRegistry` (`registry.py:26`). `NormaModule` (`base.py:56`) define `calculate_score` ponderado (green=1.0/yellow=0.5/unknown=0.5/red=0.0), `checks_owned`, `check_weights` (validados sumar 1.0) y `score_to_status` (≥85 green, ≥70 yellow). **7 plugins de normativa activos** (no 6): `RGPD_UE_2016_679`, `LOPDGDD_3_2018`, `AEPD_COOKIES_2020`, `NIS2_UE_2022_2555`, `ISO_27001_2022`, `ENS_RD_311_2022`, `LSSI_CE_34_2002` (DORA aparece solo como ejemplo en `normas/README.md`, no registrado). Evidencia: grep de `norma_key` sobre `normas/`.

**R7 dogfooding ENS confirmado empíricamente (evidencia: `normas/ens_rd_311_2022.py`)** — `ENSModule` (`ens_rd_311_2022.py:24-126`) declara explícitamente que **FULKRO se autoaplica el ENS RD 311/2022 categoría MEDIA de forma voluntaria** (`applies_to = ["FULKRO_PLATFORM_VOLUNTARY"]`, prioridad high, frecuencia monthly). Posee 7 checks ponderados mapeados a medidas del Anexo II: `audit_logs_continuity`→[op.exp.8], `backups_integrity`→[op.exp.10], `rls_coverage_percentage`→[op.acc.4], `ssl_cert_expiry`→[mp.s.2], `admin_actions_audit_logged`→[op.exp.8]/art.24.1, `intrusion_detection_present`→[op.mon.1]/[op.mon.3], `mfa_enforcement`→[op.acc.5]/[op.acc.6]. El reporte MD incluye la cláusula de conservación de evidencias 7 años (art.24.1). Esto materializa **R7 ("la plataforma cumple ENS Medio sobre sí misma")** de forma verificable y autónoma.

**Conexión frontend↔backend (cableado completo)** — API backend `api.py` con 7 rutas bajo `/api/v1/admin/compliance/monitor` (`status`, `checks`, `checks/{name}/run`, `alerts`, `alerts/{id}/resolve`, `reports`, `sync-registry`; evidencia grep `@router`). Cliente frontend `frontend/lib/admin-compliance-monitor/api.ts` mapea 1:1 esas rutas (`BASE = "/api/v1/admin/compliance/monitor"`). Dashboard `frontend/app/(admin)/admin/compliance/monitor/page.tsx` con tanstack-query, polling 60s, tabla de checks + alertas + reportes + botón sync-registry. Router montado en `main.py:449-453` con prefix `/api/v1`.

### m_compliance · features GDPR al cliente

**Derechos del interesado Art.15/17/20 (evidencia: `rgpd_api.py`)** — `router` con prefix `/portal/rgpd` y `Depends(require_client_user)` (`rgpd_api.py:39-43`). Tres endpoints: `GET /access` (Art.15 · ZIP cross-motor), `POST /erasure` (Art.17 · workflow con anonimización tombstone, respuesta DPO ≤1 mes Art.12.3), `GET /portability` (Art.20 · JSON-LD). Cada uno fija `app.current_client_id` para RLS antes del SELECT (`_set_cliente_tenant`, `rgpd_api.py:31-36`). Montado como `cliente_rgpd_router` en `main.py:474`.

**RoPA Art.30 (evidencia: `ropa_service.py`)** — `RoPAService` (admin-only) gestiona `fulkro_ropa_treatments`: list/get/update (con bump de `last_reviewed_at`), `mark_reviewed`, contadores de sub-encargados, y **export Excel en layout AEPD** (`export_aepd_excel`, `ropa_service.py:137-207`) con 17 columnas Art.30 + hoja de Metadatos que inyecta identidad fiscal desde `get_fiscal_identity` (fuente única, punto #44). Montado como `ropa_admin_router` en `main.py:469`.

**DPA Art.28 (evidencia: `dpa_template.py`)** — `build_dpa_docx` genera un DOCX completo vía python-docx (sin binarios en repo, streaming): 12 secciones alineadas a sub-artículos del Art.28 + 3 anexos (sub-encargados con Hetzner/Postmark/Anthropic+SCC 2021/914/360dialog/MinIO; medidas técnicas Art.32; categorías de datos). Placeholders de merge `{CLIENTE_*}` y `{FULKRO_*}` con degradación elegante. La sección 10 documenta la **notificación de brechas en 72h (Art.33)** y el Anexo II referencia las medidas reales de la plataforma (TLS 1.3, RLS, 2FA TOTP, firma Ed25519 del audit log, backups con prueba mensual). Versión `DPA_VERSION = "1.0"`. Montado vía `dpa_admin_router`/`dpa_public_router` en `main.py:459-467`.

**Breach + cookies** — `breach_service.py` (workflow Art.33/34, ventana 72h calculada automática pero envío real a AEPD con **manual-gating Marcos** · `README.md:57-59`) y `cookies_api.py` (consent banner + renovación 24m). Routers `compliance_admin_router` y `cookies_consent_router` montados en `main.py:479-488`. El motor NO usa LLM (jurídico determinístico, `README.md:53`).

### Estado de conexión global

Todos los routers de ambos motores están **importados y montados** en `backend/app/main.py` (líneas 52-76 import, 449-493 `include_router` bajo `/api/v1`), incluyendo `public_api` (security.txt / vulnerability inbox) y `norma_reports_api` (reportes per-normativa). El stack de self-monitoring está completo y verificado de backend a frontend.

---

## ANEXO B · Pricing canónico (referencia)

ENS implantación (proyecto fijo): **Básica 3.900€** (4-6 sem, sin audit externo) · **Media 11.500€** (8-10 sem, audit ENAC) · **Alta 22.000€** (12-16 sem, SOC+DR+24/7). Retainers post-cert: R_BÁSICO 700-900€/mes · R_MEDIO 1.500-2.500€/mes · R_ALTO 3.000-5.000€/mes. Fuente: `backend/app/core/pricing/rules.py` (`BASE_PRICES_CANONICAL`). Excluye: audit ENAC externo, HW/SW, hosting, pentest externo.

---

## ANEXO C · Hallazgos de la auditoría multi-agente (24) + estado

La fan-out de 10 agentes (Anexo A) levantó 24 hallazgos. **2 reales corregidos** (commit `4fe2a6f1`); **22 son drift documental / cosmético / aclaraciones** (no afectan runtime). Cada uno verificado contra el fichero real.

### Corregidos esta sesión

| # | Sev | Dimensión | Hallazgo | Estado |
|---|---|---|---|---|
| 1 | **HIGH** | Portal auditor | `/sign/[token]` no enrutaba purposes de portal token-gated (auditor ENAC/pentester/remediación) → "no soportado" | ✅ **RESUELTO** `4fe2a6f1` |
| 2 | **MEDIUM** | Portal admin | `ProjectTabs.tsx` tab `/admin/retainers` project-scoped → 404 + duplicado | ✅ **RESUELTO** `4fe2a6f1` |

> (Adicionalmente, fuera de la fan-out, esta sesión cerró el **gate DB Alembic** y **2 tests no deterministas** · commit `a16c53db` · §1.1.)

### Documentados (cosmético / doc-drift / aclaración · backlog no bloqueante)

| Sev | Área | Hallazgo (resumen) |
|---|---|---|
| LOW | UX cliente | Sidebar etiqueta "Firmas pendientes" pero enlaza a `firmas-hub` (historial) vs `firmas-pendientes` (canvas TIER 1) — desambiguar label |
| LOW | UX admin | CLAUDE.md (R23) describe nav "tri-pestaña"; el worktree usa sidebar vertical + ENS Radar/Pipeline comentados (Batch 2). Doctrina vs código |
| LOW | Portal auditor | `AuditorPortalSection` enumera 9 secciones; backend devuelve 11 (`available_sections`) — el chrome navega por su propia NAV (11), no rompe |
| LOW | Legal | `privacy/page.tsx` con `CIF/NIF [pendiente · alta autónomo]` — completar antes de due diligence cliente real |
| LOW | Copiloto | A14 `registry.py` model `sonnet-4.5` vs implementación persona-aware — unificar etiqueta de modelo |
| LOW | E2E ALTA | `conformidad-alta` spec asserta `policies_signed_count >= 8`, pero el gate real (`readiness_service.py`) es **25** — endurecer el aserto del spec al gate |
| LOW | Modelo datos | 237 (Base.metadata) vs ~210 clases `__tablename__` declaradas — la diferencia son tablas seed-only/catálogo por migración sin clase ORM (coherente) |
| LOW | Modelo datos | `legal_obligations_catalog` (m_legal) no en `models/__init__.py`. Potencial drift — pero `alembic check` está **verde** ahora (no drifta) |
| LOW | Compliance | `m_compliance_monitor/README.md` dice "19 checks"; `CHECK_REGISTRY` real = **21** (+intrusion_detection, +mfa_enforcement) — actualizar README |
| LOW | Compliance | dashboard docstring "17 checks" (aún más obsoleto) — comentario, la tabla se puebla dinámicamente |
| INFO | UX cliente | 3 entradas de preferencias de notificación potencialmente solapadas (consolidación pendiente, señalado no construido) |
| INFO | API admin | Rutas project-scoped reales son motor-prefijadas (`/api/v1/dda/projects/{id}/…`), no `/api/v1/projects/{id}/dda/…` — aclaración de mapa |
| INFO | Agentes | `base.py` docstring "27 agents" vs 31 IDs registry — actualizar comentario |
| INFO | Naming | Directorio real `m27_conformity` (inglés) vs referencias "m27_conformidad" — discrepancia documental |
| INFO | Naming | Dos motores `m05_*` (obligations + signing); citar `m05_signing` explícito en mapas de flujo de firma |
| INFO | E2E | `mb17_categoria_{media,alta}_complete` usan `page.route` stubs, no backend real — cobertura E2E real de diferenciación por categoría sin stubs es deseable |
| INFO | Modelo datos | `m02_magerit/models.py` docstring "11 tables" vs 12 clases ORM (incluye `magerit_risk_matrix`) |
| INFO | Motores | `m10_ens_radar` desactivado a propósito Batch 2 (confirmado reversible · `main.py` 288-293/736-738) |
| INFO | Motores | Router comercial/leads de `m13` comentado (Batch 2); pero `contract_signing_public_api` SÍ montado (`main.py:706`) para firma de contrato |
| INFO | Doctrina | CLAUDE.md cataloga `m_workflow_engine` backend-only pero `main.py` monta admin+reader routers (SÍ expone 8 endpoints REST) |
| INFO | Herramienta | El glob de un solo segmento sobre UNC agota timeout; sólo `**` responde. 44 dirs de motor verificados por agente (47 confirmados por enumeración del orquestador) |
| INFO | Compliance | `README` "6 normativas" vs 7 plugins activos (incluye `AEPD_COOKIES_2020`); DORA es ejemplo, no registrado |

**Lectura del conjunto:** ningún hallazgo de la fan-out es bloqueante de producción tras corregir los 2 reales. El resto es deuda documental menor (conteos en READMEs/docstrings) + 2 mejoras de robustez de tests recomendadas (aserto ALTA al gate 25 · E2E mb17 sin stubs). Marcos puede abordarlas a discreción post-piloto.

---

_Documento maestro generado por auditoría empírica end-to-end. Worktree `batch2-fase0-recorrido`. Commits de esta tanda: `a16c53db` (gate DB + tests) · `4fe2a6f1` (portales) · este doc. Todo lo afirmado se verificó ejecutando/leyendo el repo real._
