# Ejecutable 8 · Pasada 2 · Backend Deep Dive

> Inventario empírico exhaustivo de `backend/`. Todas las cifras provienen de output real de comandos (`find`, `ls`, `wc -l`, lectura de ficheros). CERO asunción de cifras stale.

## 1. Estructura de `backend/app/` (directorios reales, sin `__pycache__`)

```
backend/app
├── admin_settings
├── agents/            (+ agent_14_copiloto, models, prompts, schemas, services)
├── api/               (+ v1)
├── assets/            (+ brand)
├── auth
├── billing
├── core/              (ai, branding, clients, email, encryption, feature_flags,
│                       pricing, storage, workflow_state)
├── corpus
├── dev
├── middleware
├── models
├── motors/            (43 motores reales — ver §2)
├── notifications/     (+ templates)
├── retainer
├── security
├── services
└── templates
```

Ficheros raíz de `backend/app/`: `config.py`, `database.py`, `fulkro_identity.py`, `main.py`, `mcp_client.py`, `startup_checks.py`, `__init__.py`.

`backend/app/normas/` y `backend/app/plugins/` **NO existen** (la tarea preguntaba por ellos — ausentes).

Hay un segundo árbol relevante fuera de `app/`: **`backend/mcp_servers/`** (servidores MCP pentest) y **`backend/migrations/`** (Alembic).

## 2. Inventario REAL de motores

**Conteo empírico**: `find backend/app/motors -maxdepth 1 -type d | wc -l` = **45**. Restando el propio dir `motors/` y `__pycache__` → **43 motores reales**.

Nota sobre numeración: existen "pares paralelos" que comparten prefijo numérico pero son motores independientes (patrón documentado en código `m05_signing` "sibling de m05_obligations"): **m05_obligations + m05_signing**, **m10_audit_sim + m10_ens_radar**, **m21_diagnosis + m21_portal_cliente**. Por eso hay 43 dirs aunque la numeración llegue a m31.

| Motor (dir) | Propósito (docstring/código empírico) | Fase(s) ENS |
|---|---|---|
| m01_categorization | Categorización ENS Anexo I (regla del máximo, determinista, NO LLM) | FASE 1 |
| m02_magerit | MAGERIT v3 análisis riesgos (cualitativo + cuantitativo) | FASE 2 |
| m03_dda | Declaración de Aplicabilidad (DdA) Anexo II RD 311/2022 | FASE 3 |
| m04_gap | Gap Analysis: estado actual vs target del DdA, gaps priorizados | FASE 3 / FASE 5 |
| m05_obligations | Instanciación + personalización + Gantt de obligaciones (medidas) | FASE 5 |
| m05_signing | Firma in-portal Ed25519 + hash chain + OTP step-up (sibling de m05_obligations) | FASE 4 / FASE 6 (firma documental/evidencias) |
| m06_document_factory | Document Factory: plantillas DOCX→PDF Jinja2 + firma Ed25519 (políticas, procedimientos, comercial, entregables) | FASE 4 |
| m07_evidence | Gestión de evidencias: ingesta, clasificación, freshness, renewal, antivirus, requests | FASE 6 |
| m08_verification | Verificación técnica M8 v5.1: orquestador fases + ZFP + mapeo ENS + integraciones M3/M5/M7/M9 + runners (prowler/scoutsuite/openvas/nuclei/lynis/nmap/zap) | FASE 5 / FASE 6 |
| m09_audit_prep | Preparación auditoría: dossier_generator, internal_auditor, corrective_loop, simulacro_pre_enac, draft_report, audit_log_integrity | FASE 6 / FASE 7 |
| m10_audit_sim | Auditor virtual ENAC simulación pre-auditoría, eval L0-L5 determinista anti-alucinación SQL | FASE 7 |
| m10_ens_radar | ENS Radar: captación leads cross-cliente, scoring, scraping, outreach, detectores pliegos (admin pre-sales, NO ciclo ENS) | Transversal pre-venta (fuera del ciclo ENS) |
| m11_copiloto | Copiloto conversacional RAG: conversation_service, nudge_scheduler, inline_agents, coach_tasks | Transversal (soporte) |
| m12_magic_link | Magic links Ed25519 P-256 para clientes (23 purposes) | Transversal (infra cliente) |
| m13_commercial | Comercial: pricing, proposal, discount, cualificación pre-venta | Transversal pre-venta |
| m14_contracts | Contratos: contract_service, adenda_generator, legal_templates, providers (gaps ENS+RGPD terceros) | FASE 0 (gobierno/terceros) / pre-venta |
| m15_billing | Facturación: billing, FACe submitter, Facturae, invoices AAPP | Transversal (negocio) |
| m16_onboarding | Adaptive onboarding cliente: sessions, connectors, templates | FASE 0 (arranque/alcance) |
| m17_planning | Planificación: WBS catalog, effort_estimator, PDA generator, gantt | FASE 0 (plan adecuación CCN-STIC 806) |
| m18_communication | Comunicación/alertas: AEPD connector + decision tree, alert_service | FASE 8 (incidentes/notificación) |
| m19_risk | Project Risk Management: CRUD ProjectRisk + catalog | FASE 2 (gestión riesgos proyecto) |
| m20_workspace | Workspace service (espacio de trabajo colaborativo) | Transversal |
| m21_diagnosis | Diagnóstico organizacional: stakeholders, processes, quickwins, cross_compliance | FASE 0 (gobierno/roles/contexto) |
| m21_portal_cliente | Portal cliente: auth, branding, audit_log, audit_api (sibling de m21_diagnosis) | Transversal (UI cliente) |
| m22_discovery | Discovery: asset/config/data discovery, continuity, DFD, alerts | FASE 2 / FASE 0 (inventario/contexto) |
| m23_retainer | Retainer post-cert: agent_15_vigilancia, agent_26, billing_integration, addendum_v22 | FASE 8 (mantenimiento) |
| m24_idms | IDMS gestión documental + awareness_tracker (concienciación) | FASE 4 / FASE 8 |
| m25_lifecycle | Lifecycle/cierre: backup_builder, exit_checklist, api_paso4 | FASE 7 / cierre implantación |
| m26_backup | Backup & DR: pgBackRest full/incremental/WAL | FASE 5 / FASE 8 (mp.info backup) |
| m27_conformity | Conformity Lifecycle: invariantes addendum v2.2, submissions, adaptadores CCN | FASE 7 / FASE 8 |
| m28_change_governance | Gobierno cambios: materiality_engine, impact_assessor, extraordinary_audit | FASE 8 (gestión cambios/re-cert) |
| m29_client_messaging | Mensajería bidireccional cliente↔admin | Transversal (UI cliente) |
| m30_client_contacts | Contactos cliente: CRUD + interacciones (13 métodos) | Transversal (CRM) |
| m31_whatsapp | WhatsApp opt-in flow (OTP + templates) | Transversal (comunicación) |
| m_audit_accompaniment | Acompañamiento auditoría post-implantación: state machine BÁSICO 6 / MEDIO-ALTO 11 estados + advisory lock | FASE 7 / FASE 8 |
| m_cloud_connectors | Cloud connectors: link/create + sync orchestration (OAuth read-only) | FASE 2 / FASE 5 (descubrimiento cloud) |
| m_compliance | Compliance transversal: breach, cookies, DPA, admin (RGPD/legal) | Transversal (compliance) |
| m_compliance_monitor | Monitorización continua: check runs + alert lifecycle | FASE 8 (monitorización) |
| m_legal | Catálogo obligaciones legales read-only (RGPD/NIS2/DORA/AI Act) | Transversal (cross-compliance, dormant) |
| m_live_records | Live records CRUD genérico (E-303/304/305/308 registros) | FASE 6 (registros) |
| m_meetings | Meetings CRUD + workflow + log_interaction M30 | Transversal |
| m_observability | Observability: eval_runner, evaluators, golden_datasets (LLM cost/eval) | Transversal (utility admin) |
| m_workflow_engine | Workflow engine: wrappers sobre client_tasks (NO storage propio, ADR-025) | Transversal (orquestación) |

## 3. Agentes IA (`backend/app/agents/registry.py` — taxonomía canónica)

**Conteo empírico**: 28 ficheros `agent_*.py` físicos (15 implementaciones en `agents/` + 13 prompts en `agents/prompts/`). El registry define **31 IDs** (1-31).

Distribución por estado (del registry.py completo):

| Estado | Count | IDs |
|---|---|---|
| activo (LLM/determinista real, invocable) | 12 | A4, A6, A11, A12, A14, A17, A18, A19, A20, A21, A27, A31 |
| scaffolding_covered_by_engine | 1 | A2 |
| externalized_to_motor | 2 | A15, A26 |
| deprecated | 14 | A1, A3, A5, A7, A8, A13, A16, A22, A23, A24, A25, A28, A29, A30 |
| reservado | 2 | A9, A10 |
| **TOTAL** | **31** | |

Detalle de agentes vivos (activo):

| ID | Nombre | Modelo | Motor | Propósito |
|---|---|---|---|---|
| A4 | Redactor Diagnósticos E-090 | sonnet-4.6 | m22 | Narrativa senior E-090 secs 1/2/6, validator anti-hallucination |
| A6 | Analista de Contratos | sonnet-4.6 | m14 | Gaps ENS+RGPD + adenda jurídica |
| A11 | Auditor Interno Virtual | opus-4.7 | m10 | PAC priorizado + preguntas sector + narrativa dry-run |
| A12 | Coach Cliente Evaluador | sonnet-4.6 | m09 | Scorea respuestas cliente L0-L5 |
| A14 | Copiloto Conversacional | sonnet-4.5 | m11 | Chat RAG ENS |
| A17 | Cualificador Comercial | sonnet-4.6 | m13 | Cualificación 6 dimensiones |
| A18 | Reunión Exploratoria | sonnet-4.6 | m13 | Panel IA live JSON strict |
| A19 | Redactor de Propuestas | opus-4.7 | m13 | Propuesta P-001 (16k tokens) |
| A20 | Negociador Contractual | sonnet-4.6 | m14 | Cláusulas C-001 dinámicas |
| A21 | Detector Discrepancias | deterministic | m04 | DiscrepancyDetectorService cross-motor SQL (R1: determinista) |
| A27 | Clasificador IDMS | haiku-4.5 | m24 | Clasifica documentos folder 00-13/99 |
| A31 | Enriquecedor DdA no_aplica | sonnet-4.6 | m03 | Narrativa 60-200 palabras justificaciones DdA |

Agentes externalizados (funcionalidad real en motor, stub LLM eliminado Sesión 10):
- A15 Vigilancia Normativa → `m23_retainer.agent_15_vigilancia` (RSS monitor operativo, NO LLM)
- A26 Coach Auditoría/Crisis → `m23_retainer.agent_26` (analizador determinista retainers, 4 reglas)

## 4. MCP Servers (`backend/mcp_servers/`)

**Conteo empírico**: `find backend/mcp_servers -maxdepth 1 -type d | wc -l` = **16** → restando el propio dir = **15 subdirectorios**.

De los 15: **12 son servidores pentest reales** + **3 son infraestructura compartida** (config, shared, scope_enforcer).

Cada servidor tiene estructura idéntica y real: `Dockerfile` + `server.py` + `requirements.txt` + `authorization.json` + `tools/`. Los tools son wrappers MCP reales con modos `fixture`/`mock`/`real` y `scope_check` fail-closed (verificado en `cloud/tools/prowler_tool.py`, 201 LOC).

| Servidor MCP | py files / LOC | Tools (muestra) | real/estructural |
|---|---|---|---|
| infra | 17 / 632 | bloodhound, certipy, impacket, kerbrute, lynis, metasploit, netexec, responder | REAL (más completo) |
| recon | 14 / 604 | amass, nmap, masscan, naabu, httpx, shodan, spiderfoot, subfinder, theharvester, searchsploit | REAL |
| cloud | 7 / 489 | prowler, scoutsuite, pacu, kube_security | REAL (prowler/scoutsuite validados) |
| webpentest | 10 / 352 | (web pentest tools) | REAL |
| vulnscan | 7 / 339 | nuclei, openvas, trivy, grype | REAL (openvas validado) |
| redteam | 9 / 293 | (redteam) | REAL |
| cracking | 7 / 264 | (cracking) | REAL |
| sast | 8 / 200 | (SAST) | REAL |
| apisec | 7 / 184 | (API security) | estructural/ligero |
| wireless | 6 / 150 | (wireless) | estructural/ligero |
| mobile | 5 / 100 | (mobile) | estructural/ligero |
| phishing | 4 / 79 | (phishing) | estructural/ligero |
| **shared** | 6 / 565 | mcp_protocol, scope_check (infra común) | infra (NO servidor) |
| **config** | 7 / 172 | (config/registry) | infra (NO servidor) |
| **scope_enforcer** | 3 / 141 | (autorización) | infra (NO servidor) |

Los 3 "reales validados" que cita CLAUDE.md (Prowler + ScoutSuite + OpenVAS) están confirmados empíricamente: existen como tools en cloud/ (prowler, scoutsuite) y vulnscan/ (openvas), y tienen runners gemelos en `m08_verification/tools/` (prowler_runner, scoutsuite_runner, openvas_runner + mappers CIS/ENS).

## 5. Infraestructura transversal

- **`api/`**: `v1/` con 21 routers de composición (action_plans, dashboard, projects, operations, workflow, sse_api, sse_client_api, mcps, mcps_execute, corpus, audit_search, etc.). NOTA: la mayoría de routers reales viven dentro de cada motor (`motors/mXX/api.py`), no en `api/v1/`.
- **`auth/`**: 11 módulos — service, dependencies, crypto, csrf, rate_limit, totp_svc, webauthn_svc, global_dep (doble pool ADR-013).
- **`security/`**: 2 ficheros — `llm_prompt_injection_guard.py` + `__init__.py` (delgado).
- **`services/`**: 2 services top-level — adaptive_dashboard_service, admin_dashboard_service.
- **`core/`**: ai, branding, clients, email, encryption, feature_flags, pricing, storage, workflow_state + celery_app, sse_dispatcher, pdf_renderer, workflow_gates/phase/templates/schemas, dashboard_events, legal.
- **`models/`**: **57 ficheros ORM** (audit_log, auth, ens, magerit-via-core, conformity_lifecycle, copilot, auditor_annotations, auditor_clarifications, m14_providers, m25_exit_checklist, m27_renewal_milestone, m28_role_assignment, etc.).
- **`main.py`**: 869 LOC, **181 `include_router`** (router wiring real montado).

## 6. CIFRAS EMPÍRICAS (todas de comando real)

| Métrica | Valor empírico | Comando |
|---|---|---|
| Motores reales | **43** | `find motors -maxdepth 1 -type d` = 45 menos motors/ y __pycache__ |
| Agentes IDs (registry) | **31** | lectura registry.py |
| — activo | 12 | registry |
| — scaffolding_covered_by_engine | 1 (A2) | registry |
| — externalized_to_motor | 2 (A15,A26) | registry |
| — deprecated | 14 | registry |
| — reservado | 2 (A9,A10) | registry |
| Ficheros agent_*.py físicos | 28 (15 impl + 13 prompts) | `find agents -name agent_*.py` |
| MCP servers (subdirs) | 15 (12 pentest + 3 infra) | `find mcp_servers -maxdepth 1 -type d` = 16 menos raíz |
| MCP "reales validados" | 3 (Prowler, ScoutSuite, OpenVAS) confirmados | tools + m08 runners |
| Routers montados (include_router) | **181** | main.py |
| Modelos ORM | **57** | `find models -maxdepth 1 *.py` sin __init__ |
| Migraciones Alembic | **210** | `find migrations/versions -name *.py` sin __init__ |
| Ficheros test_*.py | **484** | `find backend -name test_*.py` |

## 7. MAPPING motores ↔ 8 FASES ENS (RD 311/2022)

| Fase ENS | Motores que la cubren | ¿Huérfana? |
|---|---|---|
| **FASE 0** Arranque/Alcance/Gobierno (roles RInf/RSer/RSeg/RSis/ASS/POC, comité, plan adecuación 806) | m16_onboarding (arranque), m17_planning (plan adecuación), m21_diagnosis (roles/stakeholders/contexto), m14_contracts (gobierno terceros) | ⚠️ PARCIAL — no hay motor dedicado de "comité/gobierno seguridad"; está disperso. Posible gap Pasada 10 |
| **FASE 1** Categorización (Anexo I, CITAD) | m01_categorization | OK |
| **FASE 2** Análisis y gestión de riesgos (MAGERIT v3) | m02_magerit, m19_risk, m22_discovery (inventario activos), m_cloud_connectors | OK |
| **FASE 3** Declaración de Aplicabilidad (SoA, 73 medidas) | m03_dda, m04_gap | OK |
| **FASE 4** Marco documental (PSI/Normativa/POS, 805/821/822) | m06_document_factory, m24_idms, m05_signing (firma docs) | OK |
| **FASE 5** Implantación 73 medidas Anexo II | m05_obligations, m08_verification, m26_backup, m_cloud_connectors | OK |
| **FASE 6** Evidencias y registros (dossier per marco) | m07_evidence, m_live_records, m09_audit_prep (dossier) | OK |
| **FASE 7** Cierre (BÁSICA autoeval+Decl. Conformidad 809 / MEDIA-ALTA auditoría ENAC) | m10_audit_sim, m09_audit_prep (simulacro/draft report), m27_conformity, m25_lifecycle, m_audit_accompaniment | OK |
| **FASE 8** Mantenimiento (revisión anual, auditoría interna, renovación bienal, incidentes INCIBE-CERT) | m23_retainer, m_compliance_monitor, m28_change_governance, m18_communication (incidentes/AEPD), m27_conformity, m_audit_accompaniment | OK |

**Motores fuera del ciclo ENS (transversales/negocio/pre-venta)**: m10_ens_radar, m11_copiloto, m12_magic_link, m13_commercial, m15_billing, m20_workspace, m21_portal_cliente, m29_client_messaging, m30_client_contacts, m31_whatsapp, m_compliance, m_legal, m_meetings, m_observability, m_workflow_engine.

**Fase con cobertura más débil (posible gap Pasada 10)**: FASE 0 gobierno/comité de seguridad — no hay motor dedicado, la responsabilidad se reparte entre m16/m17/m21/m14. El resto de las 8 fases tiene al menos un motor evidente.

## 8. Discrepancias vs cifras stale

Ver sección dedicada. Resumen: CLAUDE.md (42 motores / 31 agentes / 160 migraciones / ~52 modelos / ~879 endpoints) y README (28 motores / 2769 tests / 11 agentes LLM) ambos divergen de lo contado empíricamente hoy.

## Conclusión

Backend con **43 motores reales** (no 42 ni 28), **31 IDs de agente** en registry de los cuales solo **12 activos** + 1 scaffolding + 2 externalizados (15 vivos efectivos, NO 11), **15 dirs MCP** (12 pentest + 3 infra) con **3 servidores cloud/vuln validados reales**, **181 routers** montados, **57 modelos ORM**, **210 migraciones**, **484 ficheros de test**. El ciclo ENS de 8 fases está cubierto por motores con la única debilidad relativa en FASE 0 (gobierno/comité), candidata a revisión en Pasada 10.