# OLA 0 · Progreso de construcción (Ejecutable 8 · batch2-fase0-recorrido)

> Tracker vivo. Deriva de `BUILD_PLAN_MAESTRO.md`. Read-only audit cerrado → fase BUILD.
> Verificación en este entorno = import/compile + lógica pura + comportamiento dirigido
> (Postgres down aquí → suite DB-backed + tsc/navegador = entorno local de Marcos).
> SIN commits · SIN migraciones · SIN tocar BD live (regla del brief).

## ✅ Hecho + verificado (este lote)

| # | Frente | Cambio | Ficheros | Verif. |
|---|---|---|---|---|
| FR-2 | Copilotos (seguridad) | PI-guard cableado en chats persona admin+cliente (antes el cliente externo llegaba al LLM sin filtro anti-inyección) | `agents/copilot_cliente_service.py`, `agents/copilot_admin_service.py` | guard bloquea jailbreak / pasa ENS ✅ |
| FR-1 | Onboarding | `apply_dimensions_from_responses` (dead-code) cableado en `submit_onboarding` → las 10 dims se escriben | `m16_onboarding/client_service.py`, `portal_api.py` | 10 dims, extracción, firma threaded ✅ |
| #2+#3 | Incidentes (BLOQUEANTE) | `POST /admin/incidents/{project_id}/report` (decision-tree + LUCIA/INCIBE Art.33 + audit_log) + máquina de estados unificada a CCN-STIC 817 | `m19_risk/incident_admin_api.py` | ruta registrada, `created→…`, `detected` fuera ✅ |
| #11 | Comercial | Hitos creados con `scheduled_date` real (antes NULL en prod) | `m13_commercial/services/commercial_workflow_service.py:523` | fecha poblada por fase/categoría ✅ |
| #4 | Gestor doc (BLOQUEANTE/FR-3) | Upload cliente persiste el binario REAL en MinIO (antes `storage_path=NULL` → descarga 404) | `m21_portal_cliente/api.py` | `put_object`/`minio://` contrato simétrico ✅ |
| #5 | Aislamiento (seguridad) | m24: `_set_project_rls` enforce tenant del caller (ClientUser A ya NO accede a docs de B) vía contextvar + dep router | `m24_idms/api.py` | router deps + guard presentes ✅ |
| #1 | Portal auditor (BLOQUEANTE) | Descarga dossier ZIP por endpoint TOKEN-GATED (GET) en vez del admin require_owner (401) + retirado debug que filtraba el path interno al auditor | `m09_audit_prep/public_api.py` (ya existía), `auditor-portal/views/DocumentsView.tsx` | ruta GET resuelta, sin refs colgantes ✅ |
| #13 | Sync cliente (live bug) | `_PHASE_ORDER` ← canónico `WorkflowPhase.ordered()`: las fases SAN-C (analisis_riesgos/adecuacion/dda_final) recuperan acciones + "fase X de Y" | `services/adaptive_dashboard_service.py` | pure-func: steps + acciones por fase ✅ |
| #14 | Sync cliente | Gate categoría: BÁSICA→autoeval 808, MEDIA/ALTA→pentest | `services/adaptive_dashboard_service.py` | pure-func: BÁSICA≠pentest ✅ |
| #21 | Copilotos | Purga 27 docs sintéticos `example.invalid` (corpus honesto: 35 reales, 13 ingested) | `corpus/catalog.py` | 0 sintéticos ✅ |
| #15 | Retainer | **Dispatcher** `m23.dispatch_due_activities` (encola `execute_scheduled_activity` por actividad DUE · el ciclo era 100% manual) + beat diario | `m23_retainer/tasks.py`, `core/celery_app.py` | import + dispatcher presente ✅ |
| #16/#17 | Retainer | Beats añadidos: `renewal_trigger_daily` (recert bienal), `drift_weekly_compute` + `agent_26_weekly_analysis` | `core/celery_app.py` | refs resuelven ✅ |
| **BEAT-BUG** | Infra (deploy-blocker) | **9 beats rotos** referenciaban el path punteado del módulo (`backend.app...tasks.X`) en vez del nombre registrado → `NotRegistered` al arrancar beat. Corregidos: 4 backup (R8), 4 retainer, 1 evidence. Latente pre-piloto (beat nunca arrancó) | `core/celery_app.py` | 34/34 refs resuelven · **0 dotted paths** ✅ |
| #6/#7 | Portal auditor | Botones de descarga token-gated: evidencia individual (`EvidenceView`, oculta si cuarentena) + Exportar CSV del audit-log (`AuditLogView`, respeta filtro). Completan la cadena documental del auditor junto con #1 dossier | `auditor-portal/views/EvidenceView.tsx`, `AuditLogView.tsx` | refs `/api/v1/public/...` consistentes ✅ (FE: tsc local) |
| **J-GAP3** | Compliance (FRENTE J) | Bug de casing: FE `FULKRO_OWN_NORMA_KEYS` minúsculas vs plugins MAYÚSCULAS → 3 cards "Sin datos" perpetuo. Normalizado `.toLowerCase()` en filtro+find (sin tocar BD · alt. PE-1) | `admin/compliance/page.tsx` | bug confirmado fresco + fix ✅ (FE: tsc local) |
| **J-GAP1 (#49)** | Compliance (FRENTE J) | `run_norma_report` + `mark_reviewed` ahora emiten `audit_log` R6 (reusa `_emit_monitor_audit`) | `m_compliance_monitor/norma_reports_api.py` | import OK sin circular · 2 emits ✅ |
| #12/#24/#18 | Nav · acceso desde dashboard | Cliente: "Mi certificación" enlazada (página existía huérfana) + icono distinto "Mejoras propuestas" (Wrench ≠ ShieldCheck). Admin: "Chat cliente" (m21) en `ProjectTabs` (antes huérfano) | `layout/ClientSidebar.tsx`, `project/ProjectTabs.tsx` | entradas + iconos consistentes ✅ (FE: tsc local) |
| #10 | FRENTE A · estética | Email primer-acceso REESCRITO: violeta de marca #6C63FF + fondos sólidos + márgenes + copy correcto (era "enlace de un solo uso" engañoso · es login+contraseña temporal) + firma `fulkro_identity`. Primer touchpoint del cliente | `m21_portal_cliente/api.py` | render: violeta + sin azul + firma ✅ |
| #25 | FRENTE A · fiscal | QR Verifactu parametrizable `verifactu_qr_base_url` (default pre-prod · override prod `www2.aeat.es` por ENV · antes hardcodeado → inescaneable en prod) | `config.py`, `m15_billing/billing_service.py` | setting + builder ✅ |
| #23/#22 | Honestidad · "nada falso" | #23 sidebar admin: retirados counts FALSOS hardcodeados (3/12 · Client no expone lifecycle_state), acceso a Operaciones conservado. #22 README m08 honesto: orquestador `task_execute_run` = STUB (no "Checkpoints 1+2+3 implementados") + SSH/LUCIA inexistentes corregidos | `layout/Sidebar.tsx`, `m08_verification/README.md` | ediciones aplicadas ✅ |
| #19/#30 | FRENTE A | #19 copy auditor neutro (sin "fase 5 del despliegue" ante ENAC). #30 CCN-STIC 809 (Declaración Conformidad · cierre BÁSICA) registrado en corpus (`pending_manual`) | `auditor-portal/SectionPlaceholder.tsx`, `corpus/catalog.py` | 809 en catálogo ✅ |
| **J-GAP2** | Compliance (FRENTE J) | Los 4 beats de compliance (`_run_batch`) emiten `audit_log` R6 (`compliance.batch.run`) — antes no se auto-trazaban. FRENTE J: GAP-1/2/3 cerrados | `m_compliance_monitor/tasks.py` | import + emit ✅ |
| #26 | FRENTE A · ajustes | WhatsApp de Marcos editable desde el panel (E.164 validado · backend + zod + input) + dispatcher prefiere el setting persistido (fallback env) | `admin_settings/schemas.py`, `m21/chat_service.py`, `lib/admin-settings/schemas.ts`, `NotificationsTab.tsx` | backend verificado · FE consistente (tsc local) ✅ |
| #27/#29 | Acceso desde dashboard · retainer | #27 hub `/client-portal/settings` (notif+MFA+cuenta+WhatsApp en cards SÓLIDAS) + entrada sidebar (antes 404 sin índice). #29 endpoint `GET /retainer/active-client-ids` + bucket "En retainer" REAL en sidebar admin (antes siempre vacío) | `client-portal/settings/page.tsx` (NEW), `layout/ClientSidebar.tsx`, `m23_retainer/api.py`, `layout/Sidebar.tsx` | #29 backend verificado · FE consistente ✅ |

| #20 | FRENTE A · portal auditor | Doble header / triple footer ELIMINADO: `(portal)/layout.tsx` → **passthrough**; chrome neutro extraído a `PublicPortalShell` (pentester+remediación+verify-auth) ; `FulkroFooter` global → `GlobalFulkroFooter` que NO renderiza en rutas de portal público (auditor/pentester/remediation/verify-auth · neutros por diseño). Resultado: 1 header + 1 footer por portal | `(portal)/layout.tsx`, `components/layout/PublicPortalShell.tsx` (NEW), `components/layout/GlobalFulkroFooter.tsx` (NEW), `app/layout.tsx`, 3 pages portal | tsc 0 err ✅ |
| #28 | FRENTE A · ajustes cliente | Fusión de los 2 sistemas de notificación en UNA página: `settings/notifications` ahora renderiza ambas secciones (canales+horario `PreferencesForm` ADR-039 + qué-avisos+WhatsApp `NotificationPreferencesForm` CLUSTER 5); `account/notifications` → redirect. Entrada única vía hub Ajustes (#27) | `settings/notifications/page.tsx`, `account/notifications/page.tsx` | tsc 0 err ✅ |

**Hallazgo extra anotado (no tocado):** incidentes mezclan idioma de severidad — `classify` español (`baja/media/alta`) vs `create`+LUCIA inglés (`critical/high`). Follow-up de coherencia.

## ✅ FRENTE A COMPLETO (2026-06-06)

Todos los ítems S de FRENTE A cerrados y verificados (tsc/lectura). Items #19, #26, #27, #29, #30 ya estaban hechos (ver tabla arriba); #20 + #28 cerrados hoy. La antigua sección "⏳ Pendiente OLA 0" queda obsoleta. Siguiente: **FRENTE B** (ciclo documental).

## ✅ FRENTE B COMPLETO · ciclo documental (2026-06-06)

Cierra "el cliente Y el auditor descargan TODO". 4 ítems · 3 commits · 9 tests nuevos (round-trip real MinIO) · tsc 0 · ZERO regresión.

| # | Cambio | Ficheros | Commit | Verif. |
|---|---|---|---|---|
| **#31 (G4)** | M06 sube copia DURABLE del binario a MinIO + fija `storage_path=minio://` (las rutas locales son efímeras → 503 en prod). Cliente download PREFIERE storage_path. Best-effort graceful si MinIO caído. Document = misma tabla IDMS → sin migración | `m06_document_factory/service.py`, `m21_portal_cliente/api.py` | `a68f423a` | 2 tests (persist + graceful) ✅ |
| **#32 (G2)** | NEW endpoint admin `GET /idms/projects/{id}/idms/documents/{doc}/download` (StreamingResponse · resuelve minio:// + fallback local · RLS #5) + botón Descargar en `DocumentList` | `m24_idms/api.py`, `lib/api/idms.ts`, `components/idms/DocumentList.tsx` | `a68f423a` | 2 tests round-trip real ✅ |
| **#33 (F11-04)** | Dossier FIRMADO (sign_manifest) embebe binarios REALES (PDF/DOCX) desde MinIO (leverage #31), no solo .json. DEC-4 topes (50MB/doc · 500MB total · default · omisión graceful anotada en manifest) | `m09_audit_prep/dossier_generator.py` | `a4781658` | 2 tests (embebe + borrador sin binarios) ✅ |
| **#34 (F1-002)** | Preview del contrato ANTES de firmar (cierra "contrato mudo"). `get_contract_document_for_preview` (NO consume magic-link · WYSIWYS content_hash==documento_sha256) + GET `/contract-signing/preview` + botón en `ContractCanvasSignFlow` | `m13_commercial/services/contract_signing_flow.py`, `contract_signing_public_api.py`, `lib/api/contract-signing.ts`, `ContractCanvasSignFlow.tsx` | `49a0d040` | 3 tests (WYSIWYS + HTTP + token inválido) ✅ |

**DEC-4 pendiente confirmación Marcos**: topes dossier (default 50MB/doc · 500MB total) — el código funciona con defaults razonables + omisión graceful; solo falta confirmar el número.

## ✅ FRENTE D COMPLETO · parón GATE-7 + cierre BÁSICA firmado (2026-06-06)

Materializa la Premisa #1. 5 ítems · 2 commits · 5 tests nuevos · ZERO regresión.

| # | Cambio | Commit |
|---|---|---|
| **#42** | Simulacro pre-ENAC persiste NC reales en su audit_log (critical/high/coverage/loops) — antes solo total_gaps → el gate leía 0 a ciegas | `612acc6c` |
| **#40 + #43** | NEW GATE-7 `require_clean_audit_sim` (core/workflow_gates · raw SQL) cableado en `m_audit_accompaniment.transition_state`: bloquea enac_audit_scheduled/declaration_signed con NC mayores + exige simulacro antes de internal_audit_completed · escape-hatch admin `allow_open_nc` (trazado nc_override) · WorkflowGateError→409 | `612acc6c` |
| **#44** | NEW SignableType `declaracion_conformidad_basica` (firmado por Dirección · cierre E-808C CCN-STIC 809 · step-up OTP) · payload submission etiquetado signer_role=direccion | `ce0613ef` |
| **#41** | El cierre BÁSICA (publish/firma) EXIGE la autoevaluación 808 (self_assessment_report_id obligatorio · raise si falta) | `ce0613ef` |

## 🟡 FRENTE C · retainer vivo (PARCIAL · 2026-06-06)

| # | Estado | Nota |
|---|--------|------|
| **#37** E-802 anual | ✅ HECHO (`1119f3e5`) | task real + beat 15-ene + `generate_annual_report_draft` idempotente · +2 beat tests pre-existentes reparados |
| **#35** reloj LUCIA 24/72h | ✅ HECHO (`7332b052`) | beat m19.check_incident_notification_deadlines (cada hora · escala M18 al acercarse/vencer plazo Art.33 no notificado · idempotente · sin migración · trigger M18 nuevo) |
| **#36** reaprobación firmada Dirección | ⏳ BLOQUEADO drift | depende de `annual_review_records` que NO está en la BD dev drifteada (migración #4 sin aplicar aquí) · resolver tras DB-DRIFT (FRENTE K) o aplicar la migración · luego: SignableType + endpoint approve + audit_log Dirección |
| **#55** recat real | ⏳ RIESGO ALTO | `open_recategorization` es stub 23 LOC · recat real = cirugía cross-motor M01+M03 que toca `categoria` (invariante 1=1) · requiere diseño cuidado (posible input arquitecto) |

**Siguiente recomendado**: cerrar C#36/#35 tras DB-DRIFT · **F (pentest · el grande)** · G (FE/UX) · H/I · L · M · K. #55 + F1 orquestador + K deploy + PE-2/PE-3 son trabajos grandes/decisión-gated.

## PE-2 · auditoría de mensajería CONFIRMADA (2026-06-06)

Antes de fusionar (condición Marcos), verificado en código:
- **m21 chat** (`chat_threads`+`chat_messages`) + **m29_client_messaging**
  (`client_messages`+`client_message_attachments`) = MISMO concepto (chat
  cooperativo cliente↔Marcos in-portal). m29 aporta adjuntos+búsqueda+email-fwd.
  → **SÍ se consolidan** (m21 canónico).
- **m31_whatsapp** (`whatsapp_threads`+`whatsapp_messages`, dialog_360, delivery
  tracking outbound/inbound) = canal WhatsApp EXTERNO, NO chat in-portal.
  → **NO se fusiona** (es otra cosa · validó la cautela de Marcos).

Migración m29→m21 = PARO ESPECIAL: additive/reversible, mostrar antes, validar
en `fulkro_test`, NUNCA live, preservar histórico (0 mensajes/adjuntos perdidos).

## DEC-4 · CONFIRMADA + endurecida (2026-06-06 · commit `941fc688`)
Defaults 50MB/doc · 500MB total OK · ahora (a) configurables por nivel ENS+ENV,
(b) artefactos CANÓNICOS (Conformidad/SoA/pentest/certificado) NUNCA omitidos
(whitelist) · solo se omite volumen secundario.

## PE-3 · CONFIRMADA con matices (2026-06-06)
USE_MCP_REAL=false en dev correcto (no bug · binarios = deploy Hetzner). PERO:
- FRENTE F se cierra como **"código cerrado · validación-real pendiente deploy"**,
  NO "F hecho". La ejecución real de binarios contra el sistema de semillas en
  Hetzner es PUERTA DURA antes del pentest de cualquier cliente real.
- Regla ALTA intacta: el motor cubre vuln-scan MEDIA (obligatorio) + pentest
  opcional MEDIA + pre-chequeo continuo · ALTA exige pentester EXTERNO
  INDEPENDIENTE · el motor COMPLEMENTA, no sustituye.

## 🟡 FRENTE F · pentest autónomo (KEYSTONE hecho · 2026-06-06 · commit `e1e62194`)

| Ítem | Estado |
|------|--------|
| **F1** orquestador `fase_runner` + `task_execute_run` (era STUB) | ✅ código cerrado |
| **F2** persist ZfpFinding→VerificationFinding + counters | ✅ |
| **F8** seeds golden (Log4Shell + TLS1.0) → ZFP → persist (CI, sin binarios) | ✅ 3 tests |
| **F3** anti-injection LLM (temp 0.0 + delimitador + downgrade guard) | ✅ HECHO (`af94a3d2`) |
| **F7** simulacro pentest_summary · **F9** dossier compliance_declaration | ✅ HECHO (`f489599d` · cierran "reporta a auditoría" mp.s.2) |
| F5 EPSS · F6 accepted-risk expiry (migración additive) | ⏳ siguiente (PARO ESPECIAL · migración a mostrar) |
| F10 frontend RunScanButton (tsc) · **F14-DEPLOY binarios reales** | ⏳ deploy Hetzner (PE-3 puerta dura) |

**PE-3 (Marcos)**: F1/F2/F8 = CÓDIGO + ORQUESTACIÓN + SIMULACIÓN cerrados · NO es
"pentest probado". Ejecución REAL de binarios (USE_MCP_REAL=true vs sistema de
semillas en Hetzner · F14) = **PUERTA DURA** antes del pentest de un cliente real.
ALTA exige pentester EXTERNO INDEPENDIENTE · el motor COMPLEMENTA, no sustituye.
NO reusa `vuln_orchestrator` (DEPRECADO #19 · su test guard sigue verde).

## ✅ FRENTE N · SIEM (2026-06-06 · commits `7e1f4cf4` + `131a704f`)

Decisión Marcos: meter SIEM con frontend, foco pentest. Implementado como capa
LIGERA de correlación (NO Wazuh · veredicto SIEM_INVESTIGATION.md). Sin tablas
nuevas (ADR-025 · ON-QUERY) · reglas R1 deterministas.
- NEW motor `m_siem` · aggregate_security_events (M8 pentest + M19 incidentes +
  M18 escalados + compliance_alerts · normaliza severidad ES/EN) +
  compute_correlations (3 reglas: ≥3 críticos pentest · incidente+vuln misma
  superficie · incidente sin notificar LUCIA Art.33) + siem_overview (op.mon.2).
- API `/admin/siem/overview` + `/events` (require_owner · read-only · cross-cliente).
- Frontend `/admin/siem` (tiles severidad + correlaciones + timeline · fondos
  sólidos FRENTE G · nav entry) + check op.mon dogfooding (op.mon.1).
- ENS: op.mon.1 (detección/correlación) + op.mon.2 (métricas). NO sustituye SOC
  24/7 ni SIEM acreditado ALTA (Wazuh/externo · queda en el plan).
- Pendiente SIEM post-piloto: ingestión logs SO/red (fail2ban/auditd Hetzner) ·
  Wazuh read-only ALTA · SSE realtime de correlaciones.

## ✅ Workflow de cierre · verificación adversarial (2026-06-06 · ultracode)

`fulkro-closure-audit` (12 agentes paralelo · read-only). La verificación
adversarial del SIEM (frente más nuevo) detectó un bug real MEDIUM + 3 low →
TODOS corregidos (commit `00df5086`):
- conteos del overview se calculaban sobre la lista truncada por limit → ahora
  `security_event_counts` con COUNT GROUP BY exacto (independiente del display).
- correlaciones R1/R2: barrido amplio (CORRELATION_SCAN_CAP) + R2 exige vuln
  pentest crítica + incidente activo (precisión).
Resto verificado SÓLIDO (cableado, columnas, invariantes ADR-014/025/R1/R6).
Frentes B/D/C/F/L: confianza por pytest-por-commit (5 agentes de verify no
emitieron salida estructurada · flakiness del schema · no re-ejecutados).

## ✅ FRENTE J resto + FRENTE L núcleo + cierres FE (2026-06-06)

- **J#3** (`2508398b`): /admin/compliance/monitor · window.prompt → Dialog shadcn
  (Textarea + validación + loading · a11y/axe-CI). 0 window.prompt reales.
- **J#2** (`0f4ae8e1`): NEW norma-reports/[norma_key]/page.tsx · cierra el
  dead-link (404) · último reporte MD + histórico + marcar revisado · reusa
  norma-api.ts. 0 eslabones muertos en norma-reports.
- **L núcleo** (`47b0b909`+`72f43b1b`+`581634c4`): L-4 arquetipo AUTONOMO_INDIVIDUAL
  + L-7 pricing autónomo + L-8 DdA proporcionalidad micro + L-9 copiloto Art.11.

Pendiente J/L (autónomo · datos/system-project): J#4/5 dogfooding (necesita
projects system-row · riesgo RLS) · L-3/5/6 plantillas (onboarding/task/catalog
YAML/JSON) · L-10 conformity individual_mode.

## ✅ FRENTE L COMPLETO · perfil individual/autónomo 3 niveles (2026-06-06)

L-2 Sector.INDIVIDUAL + L-3 onboarding autónomo + L-4 arquetipo AUTONOMO_INDIVIDUAL
+ L-5 task templates (gate ALTA bloqueante + Art.11) + L-7 pricing autónomo + L-8
DdA proporcionalidad micro + L-9 copiloto Art.11 + L-10 conformity individual_mode.
Commits `47b0b909`+`72f43b1b`+`581634c4`+`f36b441a`+`01049006`. Pendiente solo L-6
(flag aplica_micro en E-502/E-002/E-403 · doc-filter menor · nice-to-have).

## 🔒 LO QUE QUEDA · requiere intervención de Marcos (cierre autónomo agotado)

Todo lo cerrable en autónomo a nivel verificado está HECHO. Lo restante necesita:
- **PARO ESPECIAL · migraciones** (su OK · validar `fulkro_test` · nunca live):
  DB-DRIFT→aplicar a BD dev (desbloquea C#36 · la migración #4 ya existe) · F5/F6
  pentest (additive) · chat m29→m21. Árbol Alembic = head único limpio ·
  DATABASE_MIGRATE_URL (fulkro_migrate) disponible para validar.
- **G + M (frontend visual)**: fondos sólidos + acceso dashboard + Playwright 3
  niveles · requieren la app levantada (uvicorn :8000 + next :3100) + ojos.
- **J#4/5 dogfooding**: requiere fila `projects` system (is_system · RLS) ·
  decisión de diseño.
- **C#55 recat** (cross-motor M01+M03 · toca categoria/1=1) + **H#54 AEPD** (DEC-5).

## Decisiones de Marcos (gating OLAS 1+)
DEC-1 N4 gestor propio · DEC-2 consolidar mensajería (migración) · DEC-3 OTP reaprobación anual · DEC-4 tope ZIP dossier · DEC-5 canal AEPD · DEC-6 flags MCP prod-safe.

## PARO-ESPECIAL (requieren OK explícito)
PE-1 norma_key lowercase (live-DB) · PE-2 fusión m29→m21 (migración) · PE-3 orquestador pentest end-to-end (ejecución binarios MCP).
