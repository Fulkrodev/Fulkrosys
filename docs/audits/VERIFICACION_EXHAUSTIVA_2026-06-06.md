# Verificación exhaustiva FULKRO — 2026-06-06

> Petición Marcos: "asegúrate de que todo el sistema, cada portal, cada tarea, cada
> herramienta funciona a la perfección… que el sistema hace todo el ENS para los 3
> niveles". Este documento es el resultado **empírico** de esa verificación + las
> correcciones aplicadas. Rama `batch2-fase0-recorrido` (worktree `fulkro-portales`).

## Metodología

1. **Workflow adversarial de 10 dimensiones** (29 agentes · 1.6M tokens · read-only):
   audita cada portal/tarea/tool + el motor ENS 3 niveles, con **verificación
   adversarial** de cada finding critical/high (refutar antes de creer).
2. **Re-verificación contra el árbol correcto**. Hallazgo crítico de proceso: varios
   agentes leyeron el checkout primario `~/fulkro` (rama radar-v3-pr · SIN las
   correcciones de las olas) en vez de `~/fulkro-portales`. Por eso **3 de 4
   "críticos" del workflow eran FALSOS POSITIVOS**. Toda corrección se re-verificó
   con `grep`/lectura/curl contra `fulkro-portales` antes de actuar (OPS-052).

## Veredictos por dimensión (tras corrección)

| Dimensión | Veredicto real | Nota |
|-----------|----------------|------|
| **Motor ENS 3 niveles** | 🟢 sólido | DdA 73 medidas · aplicabilidad BÁSICA=46 / MEDIA=64 / ALTA=73 (monótona) verificada en BD viva. State machine acompañamiento por nivel (BÁSICA autodecl 808/809 vs MEDIA/ALTA ENAC). Cierre firmado por Dirección. |
| **Portal cliente** | 🟢 sólido | cliente-mínimo correcto · herramientas/plantillas por tarea · sin CTAs muertos · 0 findings. |
| **Portal admin** | 🟡 by-design | Generación de documentos es manual por fase (admin orquesta · NO bug · acceso vía dashboard quick-links + ProjectTabs). |
| **Gestor documental** | 🟢 sólido (corregido) | "ROTO" era FALSO (lee ~/fulkro). m24/m21 ya persisten `minio://` (FRENTE B). **Corregidos 2 MEDIUM reales**: audit_log + whitelist extensión en upload cliente. |
| **Portal auditor ENAC** | 🟢 sólido (corregido) | "no descarga dossier" FALSO (FE ya usa GET token-gated). Corregidos metadata `signed_zip_endpoint` + `available_sections` 9→11. |
| **Pentest autónomo (m08)** | 🟢 sólido | orquestador F1 + ZFP 5 gates fail-closed + anti-injection F3 + reporte dossier/simulacro. Ejecución real de binarios = deploy-gated (PE-3 · DEC-6 · NO bug). |
| **Compliance dogfooding** | 🟢 sólido (corregido) | **F1 REAL corregido**: `check_audit_logs_continuity` usaba `created_at` (columna es `timestamp`) → crasheaba. Ahora green ("audit_log fresh") en BD viva. |
| **Frontend íntegro** | 🟢 sólido | 0 findings · tokens Fulkro (sin colores crudos en 409 tsx) · cards sólidas WCAG AA+ · 0 dead links · nav completa · huérfanos intencionales. |
| **Copilotos (FRENTE E)** | 🟢 (construido) | generador `generate_system_knowledge.py` EXISTE + 5 tests coherencia PASS (el "ausente" era FALSO). **N6 memoria construida** (ver abajo). PI-guard + sanitización de contexto F4. |
| **Integridad BD** | 🟡 deploy | **F2 REAL corregido**: alembic env.py no cargaba .env → `alembic current` ahora conecta. DB-DRIFT/version_num(32) = FRENTE K deploy (OK Marcos). |

## Bugs REALES corregidos esta sesión (todos verificados empíricamente)

| ID | Bug | Fix | Verif. |
|----|-----|-----|--------|
| **F1** | `m_compliance_monitor/checks.py:287` `MAX(created_at)` (col es `timestamp`) → ColumnNotFound | → `MAX(timestamp)` | green en BD viva · 50 tests |
| **F2** | `migrations/env.py` leía `DATABASE_MIGRATE_URL` sin `load_dotenv` → auth fail | + `load_dotenv` | `alembic current` conecta (head milestone_scheduled_date_28_001) |
| **F3** | auditor `signed_zip_endpoint` apuntaba al endpoint admin require_owner | → token-gated `/{token}/dossier.zip` | live 200 |
| **F4** | copilotos interpolaban `project_nombre`/`step_title`/`concepto` sin escapar (PI-guard solo cubría `question`) | NEW `neutralize_context_value` en admin + cliente | test inyección |
| **F5** | auditor `available_sections` 9 (faltaban gaps + draft-report) | → 11 | live |
| **DOC-1** | upload cliente sin audit_log ENAC | + `AuditLogService.log_action(DOCUMENT_UPLOAD)` best-effort | m21 tests 8 PASS |
| **DOC-2** | upload cliente sin whitelist extensión | + `_ALLOWED_DOC_EXTS` | m21 tests 8 PASS |

## Construido

- **FRENTE E · N6 memoria del copiloto entre conversaciones** (directiva Marcos):
  admin recuerda por `project_id`, cliente por `client_id`+`project_id`. NEW
  `copilot_memory.py` (sesión separada best-effort · RLS 3-way OR por actor) +
  `_call_llm`/`generate_response` aceptan `history` + wiring en ambos endpoints.
  Tests `test_copilot_memory_n6.py` 4 PASS. Suite copiloto 139 PASS.
- **FRENTE M · `POST /_dev/auditor-portal-token`** (M2 requerido): mintea magic-link
  AUDITOR_PORTAL_ENAC real (JWT+OTP) para el actor auditor de los specs E2E
  MEDIA/ALTA. Verificado live (200 · JWT 334 chars + otp).

## Falsos positivos del workflow (corregidos por re-verificación · NO eran bugs)

- "Gestor documental ROTO (sin MinIO)" → m24:282/289 + m21:599/608 ya hacen
  `put_object()` + `minio://` (FRENTE B). Leído de `~/fulkro`.
- "generate_system_knowledge.py ausente" → existe + 5 tests PASS.
- "Auditor no descarga dossier" → DocumentsView ya hace GET token-gated.

## Gaps reales restantes (honestos · NO bloqueantes piloto · priorizados)

1. **FRENTE M specs 3 niveles** (gate de coronación): el endpoint auditor-token ya
   está; faltan `cycle-seed.ts` + 3 specs maestras (8 fases × BÁSICA/MEDIA/ALTA).
   Requiere build de producción en :3100 + bucle de iteración. (L)
2. **DB-DRIFT + version_num VARCHAR(32)** → FRENTE K deploy Hetzner (requiere OK
   Marcos para migración · PROHIBIDO stamp).
3. **`portal_documents_upload` sin test E2E** (por eso el audit es best-effort) ·
   añadir test de endpoint con auth cliente. (S)
4. **M05 `_CATEGORY_HIERARCHY` dead-code** · la correctitud ENS por nivel ya la
   garantiza el gating de la DdA aguas arriba (las plantillas de obligación no
   tienen dimensión de nivel). Limpieza cosmética. (S)
5. **perfil individual/autónomo sin test cross-3-niveles** (FRENTE L código shipped;
   falta cobertura). (S)
6. **CCN-STIC-809 corpus** `pending_manual` (PDF lo descarga Marcos · ToS). (S)
7. **`proactive_triggers` event-dispatch**: el comportamiento proactivo cronológico
   ya vive en system-prompts + next_hint + beat nudge diario; el dispatcher por
   evento es refinamiento. (S)

## Doctrinas honradas

OPS-052 (audit-first + re-verificación empírica · cazó 3 falsos positivos) ·
OPS-026 DRY (reuso conversation_service, AuditLogService, neutralize) · OPS-049
honest path (gaps restantes documentados sin ocultar) · R6 hash chain preservado ·
RLS 3-way OR · ADR-013 doble pool · ADR-014 read-only OAuth · cliente-mínimo.

## Commits

`630ead1e` (5 fixes + auditor-token) · `8d0a68a2` (N6 memoria) · `51e1f3fc`
(gestor documental audit+whitelist) · este doc.
