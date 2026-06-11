# PROGRESO REMEDIACIÓN ENS — Sesión 2026-06-11 (vivo)

> **Principio (orden del usuario):** ignorar las auto-memorias `.claude` (pueden estar desactualizadas meses). **Todo lo de aquí está verificado EMPÍRICAMENTE contra el código/BD reales en esta sesión.** Re-verificar siempre en el repo, nunca asumir desde memoria. Documentar en el repo (docs/), no en memorias. **Cero alucinación.**

## HECHOS VERIFICADOS EMPÍRICAMENTE (esta sesión · sustituyen a cualquier memoria)

- **Rama de trabajo:** `fix/ens-enac-remediation-f0` (desde `main` `3226c404` == `origin/main` == prod Hetzner desplegado hoy 13:16). Remoto: `Fulkrodev/Fulkrosys` (privado).
- **Alembic:** TREE head = `unify_pricing_fiscal_rls_001` → (mis migraciones) `rls_fail_closed_hardening_001` → `rls_canonical_policies_002` (head actual, **1 solo head linear**, py_compile OK).
- **BD dev (localhost:5433, DB `fulkro`) está ATRASADA** en `milestone_scheduled_date_28_001` (drift conocido). `alembic upgrade head` como `fulkro_app` **FALLA**: `must be owner of table bia_analyses` → **las migraciones requieren rol OWNER**. Hay `DATABASE_MIGRATE_URL` (fulkro_migrate) en `.env`; alembic env.py por defecto usa `DATABASE_URL_SYNC` (fulkro_app) → de ahí el fallo. Para validar el chain completo: **scratch DB + conectar como `fulkro_migrate`/superuser `fulkro`**.
- **Roles BD:** `fulkro` (superuser, pass `changeme`), `fulkro_app` (NOSUPERUSER NOBYPASSRLS · runtime pool cliente), `fulkro_app_bypassrls` (NOSUPERUSER BYPASSRLS · escape admin), `fulkro_migrate` (owner). Init fuera de alembic en `infra/docker/init-{roles,functions,extensions}.sql`.
- **GUC:** `current_project_id()` lee `app.current_project_id`; `current_client_id()` lee `app.current_client_id` (sufijo `_id`). `set_tenant_context` en `backend/app/database.py` usa `set_config`.
- **Patrón bypass admin = `SET LOCAL ROLE fulkro_app_bypassrls`** (NO `OR ... IS NULL` en la policy). ~35+ call-sites.
- **Stack docker local ARRIBA:** postgres (5433), redis (6379), minio (9000/9001), clamav (3310), zap/`fulkro-scanner` (8090). Container PG = `fulkro-postgres-1` img `fulkro/postgres:pg16`.
- **Upload de documentación del cliente (m07_evidence):** `api.py:180` = `file.read()` + store MinIO + antivirus ClamAV + validación MIME. **`ai_classifier_service.py` es SOLO keyword-matching sobre `filename` + `content_preview` opcional, y NO está cableado al upload** (`grep suggest_classification` = 0 llamadas en el pipeline). **SIN OCR** (no tesseract/pytesseract en deps; `pdfplumber`/`python-docx`/`openpyxl` existen pero se usan para GENERAR documentos, no leer uploads). → **la lectura IA de los docs que sube el cliente HAY QUE CONSTRUIRLA.**
- **Acceso infra:** GitHub vía PAT en `C:\Users\Usuario\.fulkro_gh_pat` + `GH_TOKEN` inline. Hetzner prod `root@49.13.136.91` solo vía WSL `ssh fulkro` (key WSL `~/.ssh/fulkro_hetzner`); SSH a prod **bloqueado por el clasificador** (necesita allow-rule del usuario).

## HECHO (commit `4dfcb799` en la rama)

- **FASE 0 · R06** RLS fail-OPEN→fail-CLOSED: `signing_intents/events/otp_codes` + `copilot_conversations/messages` + `email_log` + `oauth_state_tokens`. Migración `rls_fail_closed_hardening_001` + edits oauth (`m16_onboarding/portal_api.py` → bypassrls en connect/callback) + 2 endpoints admin verify (`m05_signing/api.py` `admin_verify_chain_integrity`/`admin_verify_intent_signature` → bypassrls; los detecté yo, el agente no). **PROBADO empírico (BD viva, rolled back):** `fulkro_app` sin contexto **0 filas** (antes 17 = todos los clientes), con contexto **solo su proyecto** (5 filas, 1 proyecto).
- **FASE 0 · R08** canonizar 5 policies `admin_all USING(true)` (change_topologies, conformity_state_snapshots, client_contacts, client_contact_interactions, ai_act_transparency_events). Migración `rls_canonical_policies_002`.
- **FASE 0 · R09** writer central `backend/app/core/audit_writer.py::emit_audit_log` (DRY · respeta hash-chain R6 + aislamiento 5.A 3-way · NO toca `llm_interaction_log` cuya exención RLS es deliberada) + rate-limit LLM fail-closed tier cliente (`copilot_rate_limit.py`: `project_id` obligatorio para tier cliente).
- **FASE 0 · R07** (commit `383bdcc8`) helper central `backend/app/auth/tenant_scope.py::ensure_client_project_scope` (ownership project∈client + `set_tenant_context`, DRY del patrón duplicado en 11+ ficheros) + 3 tests PASS (`backend/tests/auth/test_tenant_scope_r07.py`). Con R06/R08 fail-closed, olvidar contexto ya NO fuga (0 filas); este helper evita el fallo silencioso. **FASE 0 (aislamiento) COMPLETA.**
- **FASE 1 · R01** (commit `c8777b37`) `backend/app/motors/m06_document_factory/informe_final_generator.py::build_informe_final_context` — el SoA E-040 ya NO renderiza vacío. Agrega cumplimiento por familia (16 familias · m03 `dda_entries`+`ens_measures.familia`) + activos (m02 `magerit_assets.asset_type_code`) + riesgos + dimensiones + cliente. Endpoint `POST /projects/{id}/informe-final/generate` (DRY · `DocumentFactoryService`) con GATE 409 si DdA vacía. **Probado empírico (BD viva, proyecto real): 16/16 familias pobladas, total 73/73.** Núcleo verificado; enriquecimiento best-effort (nunca dato falso). PENDIENTE menor: `riesgos.intrinsecos/residuales` dio 0 (best-effort · verificar columnas `magerit_risk_calculation` en R02).

## DEPLOY PARCIAL HECHO (FASE 0 + R01) — 2026-06-11 ~17:48

- **`main` desplegado**: merge `4da8fe38` (8 commits) → `git push origin main` → CD Hetzner.
- **3 workflows VERDE**: Deploy a Hetzner (CD) ✅ 1m7s · CI ✅ (tests, sin regresión) · Security Scan ✅.
- **Gate validado antes del push**: `alembic upgrade head` sobre **BD vacía** (scratch como fulkro_migrate) aplica la cadena COMPLETA limpia → head `rls_canonical_policies_002`, **243 tablas**, 12 policies fail-closed. App importa (1131 rutas).
- **PENDIENTE confirmar en BD viva de prod** (SSH bloqueado por clasificador · requiere aprobación explícita nombrando prod, no basta la regla `Bash(wsl.exe:*)`). Comando para que lo corra Marcos: `ssh fulkro 'cd /opt/fulkro && docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T postgres psql -U fulkro_migrate -d fulkro -tAc "SELECT version_num FROM alembic_version"'` → debe dar `rls_canonical_policies_002`.

## HECHO (commit `0146eb7d`) · FASE 1 · R02 cierre real E-040

**Scope ampliado a "cierre real"** (Marcos: el SoA debe renderizar completo o no sirve para ENAC). Hallazgos empíricos que CORRIGEN el briefing original de R02:
- **El render usa el `.docx` COMPILADO, no el `.md`** (`rendering.py:186` `DocxTemplate`). El `.md` se compila a `.docx` con pandoc (`build_*_templates.py`), y `extract_jinja_body` **STRIPEA la valla ` ```jinja `** → la valla es delimitador REQUERIDO, **NO se quita** (el `.docx` no la renderiza literal · verificado empírico). El briefing "quitar valla" era erróneo.
- **E-040 no estaba en ningún build script** → creado `backend/scripts/build_informe_final_template.py` (recompilador reproducible · pandoc `gfm-smart` + post-proceso `fix_docx_templates` solo a E-040.docx). Los `.docx` son **binarios trackeados en git** (sin rebuild CI).
- **`magerit_risk_calculation` no estaba roto**: join `analysis_id`→`magerit_analysis.project_id` correcto; el COUNT dio 0 porque la tabla estaba VACÍA. Refinado intrínseco≠residual con columnas reales (`risk_residual`/`risk_level`) + `magerit_treatment_plan`.
- **Mismatch de claves builder↔plantilla** (hallazgo nuevo): la categoría salía EN BLANCO (`proyecto.categoria_ens` vs `informe.categoria`); fases/gaps/excepciones a nivel raíz vs `informe.*`. Alineado el contrato completo.
- **Loop-tables colapsan en pandoc** (defecto pre-existente, ver E-600): sedes/fases/cuerpo-normativo/gaps/excepciones → listas con bullets; tablas estáticas gateadas necesitan blank-line tras `{% if %}`.
- **`default('1.0')`** rompía el render (smart-quotes de pandoc curvaban las comillas Jinja) → eliminado + `gfm-smart`.
- Editado: cita E-200→E-AR-001, plazos 6-8→8-16 sem, autor→`fulkro_identity`, POL-1xx→cuerpo normativo data-driven (documents del proyecto), +op.nub/op.mon (16 familias).
- **Render-test empírico** (`render_test_e040.py` demo + `--synth`): 0 jinja-literal, 0 pipes literales, Anexo II 73/73, sigblock único (duplicado corregido), autor "Marcos Mata · Consultor de Fulkro". 625 m06 + 262 m09/deliverables PASS · 0 regresión · ruff OK.
- Gates `{% if/else %}` con nota honesta "se incorpora como Anexo X" cuando el motor de origen aún no tiene datos → nunca tabla en blanco/ceros.

## RETOMAR EN: FASE 2 · R03 (doble firma E-012 RInfo+RServ)

Siguiente: F2 gobierno firmable (R03 doble firma E-012 + freeze cripto · R05 E-155 emitible · R24 coherencia + acta decisión Dirección · R04 citas art.40 + signable). R03 requiere migración (tabla `acta_signatures`) → rol `fulkro_migrate` + validar sobre scratch DB antes de cualquier push. Ver PLAN_MAESTRO F2.

## PENDIENTE

- **FASE 0 · R07** — dependency central `require_client_project_scope` (resuelve proyecto activo + valida ownership client_user + `SET LOCAL` contexto en la transacción) + test de cobertura que falle si una ruta del pool cliente no la usa. Hoy el patrón `_ensure_project_belongs_to_client` + `set_tenant_context` está duplicado en 20+ ficheros. NO rewire masivo: pieza central + test que marca pendientes. (El agente de spec falló por corte de red.)
- **OCR/IA lectura de docs del cliente** — servicio de extracción (pdfplumber PDF-texto + OCR tesseract para escaneos/imágenes + docx/xlsx/csv/txt) cableado al upload de tareas del cliente (m07_evidence / m24_idms / tareas). Flujo: el cliente sube doc en una tarea → el sistema lo lee (agente) → clasifica/extrae. Construir + UI.
- **FASE 1 · R01/R02** — E-040 `build_informe_final_context` (SoA hoy renderiza VACÍO) + limpieza plantilla (valla jinja, autor hardcode, POL-1xx, plazos).
  - **Plantilla:** `backend/app/motors/m06_document_factory/templates/deliverables/E040_informe_final_de_adecuacion_al_ens.{md,py}`. Patrón a espejar: `build_rectores_context` en `rectores_generator.py`.
  - **CONTRATO del context (`informe.*`) — verificado leyendo la plantilla:**
    - `informe.cumplimiento.{familia}.{aplicables,implantadas,porcentaje}` para 14 familias (`org, op_pl, op_acc, op_exp, op_ext, op_cont, op_mon, op_nub, mp_if, mp_per, mp_eq, mp_com, mp_si, mp_sw, mp_info, mp_s`) + `total` ← **fuente: `m03_dda` `dda_entries`** (group by prefijo de medida; aplicables = aplicabilidad='aplica', implantadas = estado='implantada').
    - `informe.activos.{servicios,informacion,software,hardware,comunicaciones,soportes,auxiliar,instalaciones,personal,total}` ← **m02 MAGERIT** (activos por tipo).
    - `informe.riesgos.{amenazas,pares_analizados,intrinsecos,residuales,por_encima_umbral}` ← **m02 MAGERIT**.
    - `informe.dimensiones.{confidencialidad,integridad,trazabilidad,autenticidad,disponibilidad}.{nivel,justificacion}` ← **m01 Categorization** (DICAT).
    - `informe.auditoria_interna.{auditor,fecha,independencia,nc_mayores,nc_mayores_estado,nc_menores,nc_menores_estado,observaciones,oportunidades}` ← **m09 audit interna**.
    - `informe.cumplimiento_global` (% global), `informe.version`, `informe.fecha_emision`, `informe.fecha_aprobacion_categoria`.
    - listas: `excepciones[]` (exc.{justificacion,mitigacion,norma,vigencia}) ← **E-310 m_live_records / m05_obligations**; `gaps[]` (gap.{descripcion,medida_ens,riesgo,accion,plazo}) ← **m04_gap**; `fases[]` (fase.{nombre,descripcion,estado,duracion_real}) ← **m17 plan/WBS**; `exclusiones[]` ← **E-155 alcance**.
    - `cliente.{razon_social, organo_aprobador_politicas}` ← **clients + admin_settings**.
  - **REGLA:** verificar los nombres de campo ORM reales de cada motor ANTES de escribir el builder (NO asumir). Gate: bloquear emisión si `cumplimiento.total.aplicables == 0` (tablas vacías). ALTA: añadir render de `refuerzos_aplicados (+R1..+R9)` por medida (hoy no afloran).
- **FASE 2 · R03/R04/R05/R24** — gobierno firmable: doble firma E-012 (RInfo+RServ, hoy firma rol equivocado + monofirma), E-155 de BORRADOR a emitible + servicios finalistas/instrumentales, coherencia cross-familia + acta decisión Dirección.
- **FASE 3 · R12/R16/R17/R18/R19/R21** — citas normativas/drift (mp.info RD3/2010→311/2022, 802→808, 808→ISO22301, op.cont.3, op.exp.8 retención, 808 vs 809 UI).
- **FASE 4 · R10/R11/R13/R14/R22/R25** — generabilidad + firma POS (E-235 mp.info.4 + .docx, firma en 38 POS, E-100 roles art.11 que desaparecen, builder org.2 + acuse mp.per.3, limpieza E-220, documentation_levels + POS-set).
- **FASE 5 · R15/R20/R26** — cierre Básica 808 real (no existe), builders BIA/continuidad, certificado ENAC descargable + hallazgos NC estructurados.
- **FASE 6 · R23** — enriquecimiento rectores E-150/E-160/E-170.

## VALIDACIÓN FINAL — criterio de aceptación del usuario (literal)

**Parte 1 — probar TODO ejecutándolo** (no solo tests unitarios):
- `alembic upgrade head` sobre **scratch DB limpia** como `fulkro_migrate`/owner = el chain completo aplica sin error (valida también mis migraciones end-to-end).
- Arrancar backend + frontend; ejercitar flujos reales.

**Parte 2 — 3 SIMULACIONES de cliente vía Playwright**, LO MÁS REALISTAS POSIBLES (lo más parecido a un caso real), **interactuando como LAS DOS PARTES** (admin = Marcos **y** cliente) en cada caso, **caso a caso, end-to-end, SIEMPRE por proyecto**, usando **TODOS los recursos** disponibles de admin y de cliente. Para cada nivel: seed de cliente/proyecto + recorrer el **flujo de implantación ENS ENTERO** del cliente (todas sus tareas, subir documentación donde toque → probar la lectura IA, firmar, etc.) Y todas las acciones del admin (categorizar, generar entregables, avanzar workflow, solicitar firmas, revisar evidencias, etc.):
- **Cliente ENS BÁSICA** — flujo completo (autodeclaración 808/809).
- **Cliente ENS MEDIA** — flujo completo (ruta ENAC) **EXCEPTO pentest externo OSCP**.
- **Cliente ENS ALTA** — flujo completo **EXCEPTO pentest externo OSCP**.

**Parte 3 — tras cada simulación, revisar los resultados/entregables como AUDITOR ENAC** → ¿perfectos de verdad?

**Parte 4 — DOCUMENTAR por escrito** todo el flujo de cada cliente (qué se hace en cada momento) + resultados empíricos de las 3 simulaciones.

**Parte 5 — DEPLOY FINAL:** merge → `main` → CD Hetzner (todos los cambios reflejados en el servidor).

## NOTA DE PROCESO
- Antes de cada compactación de contexto: actualizar este documento con lo hecho + lo que queda.
- Commits en la rama `fix/ens-enac-remediation-f0`; deploy a `main` solo al final, tras validación empírica verde.
