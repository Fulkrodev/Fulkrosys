# FULKRO · Production Readiness Punch-List (2026-06-07)

Consolidación de 2 auditorías exhaustivas (24 frentes · ~3.3M tokens subagentes) para
dejar el sistema ENS **perfecto end-to-end (BÁSICA/MEDIA/ALTA) + blindado + DB
producción-ready + portales sincronizados + gestor documental + copiloto guía todo**.

Worktree: `/home/usuario/fulkro-portales` (branch `batch2-fase0-recorrido`).

Leyenda estado: ✅ hecho · �doing · ⬜ pendiente.

---

## P0 · Seguridad — bloqueantes (inhackeable + no tumbar)

- ⬜ **DB superuser escalation (raíz)**: `fulkro_app` es miembro de `fulkro` (superuser) vía `GRANT fulkro TO fulkro_app` (init-roles.sql:40) → `SET ROLE fulkro` escala a superuser → RLS + inmutabilidad audit_log R6 = barreras blandas. Fix: role `fulkro_app_bypassrls` NOSUPERUSER+BYPASSRLS; reemplazar los 175 `SET LOCAL ROLE fulkro` runtime. *(sensible · migración + verificación)*
- ✅ **Endpoints SET ROLE fulkro sin require_owner** (commit 468be7c3): operations.py + audit_search.py ahora `dependencies=[Depends(require_owner)]`. Verif: CLIENTE /operations/overview → 401 · MARCOS → 200.
- ⬜ **RLS faltante 4 tablas tenant**: bia_analyses, awareness_sessions, invoices_aapp, aepd_notifications · + audit_accompaniment_{state,transitions,artifacts} (cliente-reachable). Fix: migración ENABLE+FORCE RLS + policy project_isolation + set_tenant_context en m_audit_accompaniment.
- ⬜ **FORCE RLS** en 26 tablas RLS-enabled-not-forced (signing_events/intents, chat_messages, client_*, etc.).
- ✅ **app_secret_key default validado** (commit 468be7c3): `verify_app_secret_key()` en startup_checks · fatal en producción si default/débil (<32 chars). Dev solo warning.
- ⬜ **Uploads sin antivirus + sin magic-bytes** (m21 evidencias + portal_documents + m24 IDMS · `documents` sin scan_status). Fix: ClamAV scan_evidence_file_task + python-magic + bloquear preview/download si scan_status!=clean.
- 🟡 **Límite de body** (commit 468be7c3): `BodySizeLimitMiddleware` global · 413 si Content-Length > tope (FULKRO_MAX_REQUEST_BODY_MB, default 100MB) ANTES de leer en memoria. Pendiente: streaming per-endpoint (m07/m21) + Caddy prod.
- ⬜ **SSE pool-exhaustion DoS**: authenticate_request global retiene conexión DB durante todo el stream (~15-30 EventSource tumban la app). Fix: whitelist rutas SSE del Depends(get_db) global / sesión efímera para auth.
- ⬜ **Rate limiting de borde ausente** (Caddyfile dev-only). Fix: Caddyfile.prod rate_limit + max_size + conn-limit + HSTS/TLS.
- ⬜ **Cap coste LLM no funcional** (feature-label mismatch copilot_rate_limit vs service.py:467) + endpoints m11 copilot_chat/stream/conversation sin enforce. Fix: unificar label + enforce_rate_limit_or_raise.
- ⬜ **Celery sin task_time_limit/soft_time_limit** + OAuth token sin timeout → cola congelada (plazos AEPD/CCN 72h + backups R8).
- ⬜ HSTS + TrustedHost + docs off en prod (sec-surface menores).

## P0 · DB producción-ready

- ✅ **~~4 heads Alembic~~ FALSO POSITIVO** (verificado 2026-06-07): `alembic heads` = **1 solo head** (`milestone_scheduled_date_28_001`). Las 3 revisiones que el audit estático marcó como heads están EN la cadena. `upgrade head` NO es ambiguo · producción arranca. (Lección: verificar empíricamente los hallazgos de los workflows.)
- ⬜ **Gate aceptación**: build_test_db.sh end-to-end sobre BD vacía → ~248 tablas/~3645 cols + `alembic check` sin diff. (Pendiente ejecutar sobre BD limpia · la BD dev está drifted.)
- ⬜ **alembic check FALLA** (verificado real). Drift ORM↔BD-dev:
  - `annual_review_records` (tabla creada por migración `annual_review_e4_001`, SIN modelo ORM) → fix: crear modelo ORM espejo.
  - `dda_entries.annual_review_record_id` (col en migración `annual_review_e4_001`, SIN campo ORM) → añadir a DdaEntry.
  - `projects.supervision_mode` (en BD-dev por **DDL directo · NINGUNA migración la crea**) → fix DOBLE: añadir a Project ORM + NUEVA migración que la cree (para que fresh build la tenga).
  - Índices drift menores: `golden_eval_runs` (triggered_at DESC), `knowledge_documents`, `precliente_consents` (rename), `projects.audit_passed_at` → alinear Index() en modelos.
- ⬜ **Índices capacidad**: audit_log (tabla,registro_id)+(tabla,ts), MAGERIT FKs, project_id/client_id en ~34 tablas multi-tenant. Pool: pool_pre_ping + pool_recycle + pool_timeout. Celery engines → NullPool.
- ⬜ pgAudit on + timestamptz radar (31 cols naive).

## P1 · Lifecycle E2E 3 niveles (specs + producto)

- ✅ **conformidad BÁSICA + MEDIA** verde (commit bbc2ae35).
- ✅ **DdA firma** (bug producto gate + seed v3.11 + cadena R6 · commit cf022ae1).
- ⬜ **conformidad BÁSICA post-firma URLs rotas** (distintivo/cert-id/docx → prefijo inexistente /api/v1/m27/ + admin-only) → cliente no accede al distintivo. Fix: public badge URL + endpoint cliente docx. + E-041/E-180 naming + spec ALTA.
- ⬜ **actas**: pipeline admin inexistente (servicio sí, API/UI no) → portal vacío. Fix: actas_admin_api + página admin + sidebar cliente + seed + descarga.
- ⬜ **firmas-hub**: heading drift (Mis firmas ENS→regex) + signable types hardcoded 6 (no category-aware) + BÁSICA muestra firmas incorrectas.
- ⬜ spec drift: policies (Mis firmas regex), magerit (networkidle→tolerant), pentest (staging exact + seed reset), incidents (heading regex + sidebar), categoria-admin (/^Auditoría$/i + wizard heading), workflow client (rewrite a /workflow-guide).
- ⬜ dpc-anual: sidebar link + resolver contradicción 2 specs.
- ⬜ pentesting-system: create_run pending muerto (botón no ejecuta) + fase_runner devuelve [] (MCP no cableado) + sin audit_log + cliente no ve hallazgos.

## P1 · Portal sync admin↔cliente + hitos→pago

- ⬜ auto_billing.py:248 avance fase por pago NO emite phase_changed → portales no realtime.
- ⬜ certificación cliente sin realtime (accompaniment.state.advanced no escuchado).
- ⬜ cobro hito SSE a canal muerto client_user:{id} → bandeja/panel no refrescan.
- ⬜ phase_changed en after_commit (no after_update · risk rollback).

## P1 · Copiloto guía todo (per-rol + per-proyecto)

- ✅ conversacional + system_knowledge + memoria N6 + persona por rol (confirmado).
- ⬜ unificar 2 copilotos cliente (CopilotoDock agent_14 vs CopilotoClienteBottomRight stub) → uno canónico con memoria N6 cableada en stream.
- ⬜ dock global en layout cliente (hoy solo /workflow).
- ⬜ guía inline (CopilotGuidedFlow/banner) en TODAS las tareas: pentest, policies, dpc-anual, plan, magerit, categorizacion, actas (hoy faltan).
- ⬜ quick-actions + inferContext extender a todas las rutas de tarea.

## P1 · Gestor documental + rastreo + capacidad

- ✅ m07 cross-tenant (commit 468be7c3): replicado guard de m24 (contextvar _capture_subject + role_pool=="cliente" ⇒ caller_client_id == project_owner, 404). Pendiente m07 streaming/commit aparte.
- ⬜ evidencias_upload: db.commit() (hoy flush · pierde audit R6) + persistir MinIO (no filesystem efímero).
- ⬜ WORM real (BUCKET_EVIDENCE_WORM código muerto · Object Lock 7y · Art.24 ENS).
- ⬜ IDMS version race → advisory lock Pattern #22 + unique(document_id,version).
- ⬜ rastreo: client_compliance_summary bugs (tabla/columna inexistente → 0 siempre) + gap matrix cuenta evidencia scan_status no-clean (coverage inflada al auditor) + unificar fuente de verdad cobertura per-medida + vista cliente "qué evidencia falta por medida".

## P1 · Templates / entregables

- ⬜ deliverable_codes no expuesto en portal → sin botón "descargar plantilla".
- ⬜ 7 plantillas LCSP (L001-L007) sin registrar en template_registry.
- ⬜ 3 catálogos desincronizados (registry 112 vs catalog 84 vs task_templates).

## P1 · Completeness tareas cliente

- ⬜ ClientTaskCard ignora managed_by_fulkro → cliente ve botones de tareas que gestiona Fulkro.
- ⬜ 3 tareas cliente-actor con cta_url /admin (DPIA, FINTECH, EDUCACION).
- ⬜ set-test-project-category no regenera tareas + anclas #conformity/#diagnosis muertas.

---

**Orden de ejecución**: P0 seguridad código-level (require_owner, secret-key, headers, body-limit, m07 cross-tenant) → P0 DB (4-head merge + RLS + índices) → P1 E2E specs → P1 producto (conformidad URLs, copiloto global, hitos→pago, actas, templates, rastreo). Cada incremento verificado + commit.
