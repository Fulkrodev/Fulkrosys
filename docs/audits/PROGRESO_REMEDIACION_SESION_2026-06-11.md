# PROGRESO REMEDIACIÓN ENS — Sesión 2026-06-11 (vivo)

> **Principio (orden del usuario):** ignorar las auto-memorias `.claude` (pueden estar desactualizadas meses). **Todo lo de aquí está verificado EMPÍRICAMENTE contra el código/BD reales en esta sesión.** Re-verificar siempre en el repo, nunca asumir desde memoria. Documentar en el repo (docs/), no en memorias. **Cero alucinación.**

## ⭐ HANDOFF — LEER PRIMERO (estado para retomar en sesión nueva · 2026-06-11 23:xx)

### Estado del servidor y del repo
- **prod Hetzner = `main` = `62990aec`** · DESPLEGADO y VERIFICADO sano (9 containers healthy · alembic head `fase0_rls_leak_fix_001` · `/api/v1/health`). **Local `main` == `origin/main` == prod**. (Antes `af53e2cd`; el `origin/main` LOCAL puede quedar STALE tras fetch sin cred → la verdad es `git ls-remote` con el PAT.)
- Working repo: `/home/usuario/fulkro` rama `main`. BD dev/test: container `fulkro-postgres-1` localhost:5433. `fulkro_test` se reconstruye con `scripts/build_test_db.sh` (drop→init-roles→alembic head→seed). Stack docker arriba.

### ⚠️ HALLAZGO CRÍTICO ESTA SESIÓN (2026-06-12) · P0 leak cross-tenant en prod — CERRADO + desplegado
- **Cazado al traer `fulkro_test` (estaba STALE pre-FASE-0 en `unify_pricing_fiscal_rls_001`) al head real**: el "6003 passed" de la sesión anterior se midió contra un esquema SIN las migraciones FASE 0 → el endurecimiento RLS de R06/R08 nunca se probó. Al ponerlo al día: 24 fallos.
- **Verificado empíricamente (conexión REAL `fulkro_app`)**: `fulkro_app` (rol runtime, NOSUPERUSER) veía filas de OTROS clientes en **7 tablas** (signing_intents/events/otp_codes, copilot_conversations/messages, email_log, oauth_state_tokens). Causa: `init-roles:100 GRANT fulkro_app_bypassrls TO fulkro_app` (necesario para SET LOCAL ROLE) → `fulkro_app` es MIEMBRO del rol bypass → las policies `*_admin_bypass USING(true) TO fulkro_app_bypassrls` de R06 aplican TAMBIÉN a `fulkro_app` (permisivas = OR) → ve todo.
- **Fix desplegado (`f6f39f26`)**: migración `fase0_rls_leak_fix_001` DROP de las 7 `admin_bypass` (el rol bypass sigue saltando RLS por su ATRIBUTO, patrón canónico R08) + restaura `email_log` system-wide (`client_id IS NULL`). **Verificado en prod: 0 admin_bypass · email_log con IS NULL · aislamiento real.**
- **Lección reforzada**: NUNCA medir verde de suite contra `fulkro_test` posiblemente stale → reconstruir con `build_test_db.sh` antes de confiar en el verde. Las policies `admin_bypass USING(true) TO <bypass-role>` son un ANTIPATRÓN cuando el rol runtime es miembro del bypass.

### HECHO + desplegado esta sesión (de 26 R-items: ~10 cerrados)
- **R02** E-040/SoA cierre real (render verificado con .docx real · 0 huecos · 16 familias Anexo II) · **R01/R06/R07/R08/R09** ya estaban (FASE 0).
- **R04** citas E-012 (categorización art.40+AnexoI / DA art.28+AnexoII) + E-012→acta_comite en signable_types.
- **R24-parcial**: footer "FULKRO" fuera del cuerpo (E-002/E-003/E-012) · clave canónica `responsable_sistema_informacion`→`responsable_sistema` (E-002/E-012/E-042).
- **R03** acta E-012: plantilla con doble firma competente (RInfo+RServ APRUEBAN art.40.2 · RSeg conforme) + **backend** `request_acta_double_signature`/`get_acta_double_signature_status` en `m01/signature_integration.py` (reusa m05 dos-intents · sin migración · gate aprobada=ambos signed · testeado).
- **F3-parcial**: drift sistémico **E-050→E-150** ("Plan de Adecuación") cerrado en E-012/E-003/E-041/E-042/E-043/E-090/E-614/E-615 + tests.
- **BUG REAL de prod arreglado** (no era de la remediación): el **copiloto del cliente daba 500** (R09 hizo project_id obligatorio para tier cliente; `client_copilot_stub.py` + `m11/portal_api.py` no lo pasaban). Fix: resolver project_id server-side + guarda anti-500. **Lección clave: se cazó mirando el CÓDIGO/comportamiento real, no el verde de los tests (los tests estaban stale y daban por bueno el 500).**
- Suite completa: **6003 passed / 0 fail**.

### HECHO + desplegado 2026-06-12 (commits `b5442482` R05 + `f6f39f26` P0 + `62990aec` m30)
- ✅ **R05** (E-155 emitible · NC_MAYOR) CERRADO: modelo de scope estructurado (`services.tipo` finalista/instrumental + tablas `system_sites` sede_fisica/region_cloud+dirección+país + `scope_exclusions`) · migración `e155_scope_model_001` (additive, RLS hija-vía-systems fail-closed, validada scratch + 0 drift) · builder `build_e155_alcance_context` (m06/`alcance_generator.py`) con dims DICAT reales + gate `E155ScopeEmptyError` · endpoint `POST /projects/{id}/alcance-sgsi/generate` (409 vacío, `enforce_gates=False`) · CRUD scope en m01 (`/categorization/systems/{id}/sites`+`/exclusions`+`/services/{id}/tipo`) · plantilla reescrita sin BORRADOR/sin 11 notas REVISIÓN CONSULTOR · docx recompilado · render-test 0 fugas Jinja · 9 tests + `test_template_registry` actualizado (era stale).
- ✅ **P0 leak fix** (`fase0_rls_leak_fix_001`) + ✅ **m30 fix** (dependency `_set_client_rls_context`) — ver sección crítica arriba.
- Suite **6011 passed / 0 fail** · CI verde · CD verde · prod verificado por SSH.

### HECHO + desplegado 2026-06-12 · TANDA 2 (F3 entero + R03-wiring + R24 + F4·R10)
Commits en prod: F3-citas `90a03aed` · F3-plantillas `eafb479b` · R03-wiring `14b15b89` · R24 `a496f851`. R10 commiteado local (pendiente push).
- ✅ **F3 ENTERO**: citas/drift (R17 UI 809→808, R18 fuente 808/824, R21 backups→mp.info.6, R22 limpieza E-220) + plantillas (R12 mp.info numeración RD3/2010→311/2022 + cifrado→mp.si.2/firma + mp.s.1→correo en E-104/107/119/103/100/232; R16 E-041 73→52/68/73 + E-052→E-050 + art.35→Anexo III; R19 E-222 802→Anexo II/804). 8 docx recompilados.
- ✅ **R03-wiring**: acta E-012 canónica con la plantilla m06 (doble firma art.40.2) · `build_e012_context` (m06/`acta_e012_generator.py`) · endpoints `acta-e012.pdf/.docx` repointados al pipeline m06 (render_docx, no PDFRenderer estricto) · 2 endpoints NEW `request-double-signature`/`double-signature-status` · variantes B (provisional.docx) y C (markdown monofirma) deprecadas.
- ✅ **R24**: NEW acta **E-010** "Decisión de Adecuación de la Dirección" (org.1) firmable · SignableType `acta_decision_direccion` · paso `decision` en fase0_governance. (fecha_nombramiento independiente = refinamiento menor diferido.)
- ✅ **F4·R10**: E-235 sellado emitible (mp.info.5→mp.info.4 · valla reestructurada: el cuerpo ya compila · E-235.docx creado · placeholders resueltos).
- Suite **6014 passed / 0 fail** (cada item con gate full-suite antes de push).

### HECHO 2026-06-12 · TANDA 3 (F4-resto: R11 + R13 + R14-backend + R25)
Commits local (gate full-suite + push pendiente al cierre de la tanda): R11 `00cdbab0` · R13 `652b90b2` · test-fix adenda `b56908a5` · R14 `3904fce2` · R25 `b6ccc336`.
- ✅ **R11** (firma en POS): `fix_docx_templates.py` deriva `PROCEDURE_DOCX` del registry (37 POS empíricos · el plan decía "38" nominal) y les añade bloque de firma de 2 columnas **ELABORADO (consultor) / APROBADO (RSEG-RSIS)** vía `{{ firmas.* }}` (los entregables conservan su bloque de 3 col). Además el header cae al título canónico del registry (E-401/E-700/E-705 estaban SIN header). 98 .docx con cambio real recompilados (las 35 sin cambio semántico revertidas a HEAD). Render-test 37 POS = 0 fugas + aprobador=RSEG; m06 636→.
- ✅ **R13** (2º bloque jinja perdido): el compilador (`extract_jinja_body.search()`) solo compilaba el 1er bloque ```jinja → descartaba en SILENCIO el 2º. **3 plantillas afectadas**: E-100 (anexo de roles art.11 → FUSIONADO como anexo · token fantasma `ABSORB_INTO_E100` purgado en E-100/E-104/E-221 · `numero_empleados` blindado con `default(50,true)`), E-203 (su 2º doc era **E-PF-001** Concienciación/Formación mp.per.3/4 → SEPARADO a plantilla+`.py`+registry), E-207 (su 2º doc era **E-IT-001** Hardening op.exp.2/3 → SEPARADO igual). GUARDA: el extractor ahora FALLA si hay >1 valla ```jinja; `_md_for` usa el `body_path` canónico del registry (resuelve las 4 variantes sectoriales de E-100). Render-test 7 docx 0 fugas + edge-cases numero_empleados; m06 642.
- ✅ **R14 backend** (gobernanza org.2 + purga legacy): NEW `governance_context.build_governance_context` deriva de m30 los 5 roles art.11 + comité + DPO con fallback "(pendiente designación)" + `numero_empleados` + `proxima_revision=fecha+12m`; **wired** en `generate_document` como base aditiva (deep-merge, caller gana) → E-002/E-003 + anexo E-100 siempre rendibles. Purga "Marcos Mata García" hardcodeado en `internal_auditor.py` → `fulkro_identity`. 3 tests unit + 995 m06/m09/m14. **PENDIENTE R14 parte 2** (documentado): modelo acuse de recibo per-empleado mp.per.3 (migración+API+UI).
- ✅ **R25** (niveles doc + POS-set): LEVEL_2/LEVEL_3 ahora se DERIVAN del registry (LEVEL_3 listaba 14 de 39 POS, con `E-204A` mal escrito; LEVEL_2 omitía E-120/E-122/E-127). NEW POS-set acumulativo por categoría (BÁSICA⊆MEDIA⊆ALTA · `procedures_for_categoria()` · ALTA=todos, MEDIA=sin refuerzos solo-ALTA [E-235], BÁSICA=núcleo curado) espejando `POLICIES_*`. Tests drift-guard + monotonía. m06 651.

### HECHO 2026-06-12 · R14 parte 2 (acuse mp.per.3) → FASE 4 COMPLETA
Commit local `0c03468b` (push tras gate). NEW modelo `PolicyAcknowledgment` + migración `policy_ack_mp_per3_001` (RLS fail-closed project/client · validada scratch · 0 drift nuevo en `alembic check`) + 3 endpoints admin (POST/GET/summary) + 2 tests. **FASE 4 (R10+R11+R13+R14+R22+R25) cerrada y desplegada.** UI acuse del personal → simulaciones.

### HECHO 2026-06-12 · F5 parcial (R15 + R20-citas)
Commits local R15 `89ca698c` + R20-citas `31d4e829` (push `31d4e829` · prod al día).
- ✅ **R15** (gate cierre BÁSICA · NC_MAYOR): `process_basic_declaration` ahora VALIDA `self_assessment_report_id` contra `documents` (E-808* real de ESTE proyecto) en vez de aceptar cualquier UUID. OPS-052: el generador SÍ existe (run_simulation + generate_report_docx + m06 generate E-808); el hueco era la no-validación. 5 tests + m27/m10 178.
- ✅ **R20-citas** (NC_MENOR): E-401/402/403 dejan de citar CCN-STIC-808 como guía de continuidad → UNE-ISO 22301:2020; E-405/406 op.cont.4→op.cont.3 (pruebas); E-400 POL-104→POL-109. .md corregidas + .docx parcheados directos (rebuild_docx_templates gfm-smart CORROMPE el jinja de tablas multi-{{ }} de E-400 → deuda de tooling anotada). Render-test 6/6 = 0 fugas.

### SIGUIENTE PASO (orden): R20-builders → R26 → F6 (R23) → 3 simulaciones + auditor + docs
**Hallazgos empíricos para la próxima tanda (scope mayor · cada item con builder/modelo/migración):**
- **R20-builders** (~2-3h): `build_bia_context` + `build_continuity_context` para poblar RTO/RPO/ejercicios (hoy vacíos) en E-400/401/etc. Requiere fuente de datos de procesos críticos (BIA input · hoy no hay tabla · vendría de cuestionario/cliente). `excel_generators/bia_business_impact.py` existe como referencia.
- **R15** (autoevaluación 808 cierre BÁSICA · NC_MAYOR · ~4-6h · el corazón del cierre): el generador NO existe. Piezas YA presentes a reusar: `m10_audit_sim/audit_questions.py` `AUDIT_QUESTIONS` = checklist CCN-STIC 808 con `aplica:[BASICA/MEDIA/ALTA]`+`criterio` por medida; `m10_audit_sim/audit_simulator.py` `AuditSimulatorService.run_simulation` evalúa medidas vs DdA+evidencia. El gate `m27_conformity/conformity_service_paso5.py:316` HOY solo comprueba `self_assessment_report_id is None` (no valida contra tabla). **A construir:** generador que filtre `AUDIT_QUESTIONS` a BÁSICA + evalúe estado (reusar audit_simulator) → `Document` firmado por DIRECCIÓN + trazado; **endurecer** el gate para validar `self_assessment_report_id` = Document real + firmado (FK + estado). Files: generador 808 (nuevo), audit_questions.py, conformity_service_paso5.py + api_paso5.py, schema/FK. **UI:** paso de cierre Básica.
- **R20** (BIA/RTO/RPO + ISO 22301 · ~3-5h): existen `excel_generators/bia_business_impact.py` + plantillas E-400 (BIA) / E-401 (estrategias continuidad) / E-403 (DRP). Verificar qué builder server-side falta para poblarlas con procesos críticos+RTO+RPO reales y añadir citas ISO 22301 (cláusulas 8.2.2 BIA / 8.2.3 estrategias). Continuidad es refuerzo ALTA (op.cont.*).
- **R26** (certificado ENAC descargable + NC estructuradas · ~3-5h · NC_MENOR): infra parcialmente ya presente (OPS-052): `build_distintivo_context` YA puebla client_domicilio + services/information_summary; modelos `Finding`/`AuditFinding`/`RemediationPlan` (severidad+estado) YA existen. Gaps reales: (a) **certificado ENAC** MEDIA/ALTA como `Document` descargable adjunto a `route_state REGISTERED` (PDF nº+vigencia 2 años · reusar distintivo_generator); (b) promover NC E-321/E-322 de JSONB a `AuditFinding` (OPS-026: reusar, NO nuevo modelo). **OJO E-040 — IDENTIDAD SISTÉMICA CONFLICTIVA**: el registry titula E-040 "INFORME FINAL DE ADECUACIÓN", PERO `m03_dda` lo FIRMA como la DdA y `m09 dossier` (DELIVERABLE_TO_FOLDER + is_canonical "# SoA/DdA" + folder 04_DECLARACION_APLICABILIDAD) + tests lo tratan como SoA/DdA. Un relabel naïf en dossier_generator ROMPE m03 + tests. R26 "fijar UNA identidad de E-040" exige un pase dedicado que reconcilie m03+m09+registry+tests a la vez (E-040 = Informe Final que INCLUYE la SoA, firmado RSEG · R02 lo dejó con 16 familias Anexo II) · NO es un fix de etiqueta.
- **R23** (rectores E-150/160/170 · ~2-3h · F6): `rectores_generator.py` existe; enriquecer el contenido real (Plan de Adecuación / Manual SGSI / Plan Director) más allá del esqueleto actual.
- **3 simulaciones** (API-e2e admin+cliente BÁSICA/MEDIA/ALTA · subir docs→lectura IA→firmar→entregables · EXCEPTO pentest OSCP) + revisión auditor ENAC por nivel + documentación escrita + validación final (alembic scratch + suite + deploy). **Scope grande · idealmente con presupuesto de contexto fresco.**

### (histórico) SIGUIENTE PASO previo: F4-resto → F5 → F6 → 3 simulaciones + auditor + docs
**F4 pendiente (hallazgos empíricos para la próxima tanda):**
- **R11** (firma 38 POS): 0/38 procedures tienen bloque de firma. `fix_docx_templates.py` aplica `append_sigblock` solo a `SIGBLOCK_TEMPLATES` (línea ~322); añadir los procedures a ese conjunto (ELABORADO=consultor / APROBADO=RSEG-RSIS con `{{ firmas.* }}`) + recompilar los 38 docx.
- **R13** (E-100 2º bloque jinja): E-100 tiene **2 bloques ```jinja**; `JINJA_BLOCK = r"```jinja\s*(.+?)```"` (non-greedy) en `build_sgsi_core_templates.py:43` compila SOLO el 1º → el 2º (documento de roles art.11, "ABSORB_INTO_E100") se PIERDE. Crear código real E-100B (o Anexo I de E-100) + catalogarlo + arreglar las 3 refs `{{base}}-ABSORB_INTO_E100` en E-104 + el code en E-100. extract_jinja_body soporta solo 1 bloque → o se fusiona en el 1º o se separa E-100B a su propio fichero.
- **R14** (builder org.2 + acuse mp.per.3): context builder server-side de roles art.11 + comité + DPO (fallback "(pendiente designación)") + modelo de acuse de recibo per-empleado (mp.per.3). Borrar "Marcos Mata García" legacy en `m09_audit_prep/internal_auditor.py:598,602`.
- **R25** (documentation_levels): `documentation_levels.py` LEVEL_2/LEVEL_3 omiten POS + tracking POS-set acumulativo por categoría.
**F5**: R15 (generador cuestionario CCN-STIC 808 cierre BÁSICA · corazón del cierre · NO existe) · R20 (builders BIA/RTO/RPO + citas ISO 22301) · R26 (certificado ENAC descargable + NC estructuradas).
**F6**: R23 (enriquecer rectores E-150/160/170). **Luego**: 3 simulaciones (API-e2e admin+cliente) + revisión auditor + docs + deploy final.
- **F3-resto**: R12 (citas mp.info E-104/107/119/103/100/232) · R16 (E-041 cross-refs) · R17 (E-808 rename "Revisión Anual" + UI `ConformityWizard.tsx:68`/`ProjectCategoryBanner.tsx:36` 809→808) · R18 (`m10_audit_sim/audit_questions.py` 802→808 + retención 6→12m op.exp.8) · R19 (E-222 citas 802→Anexo II) · R21 (`m22_discovery/paso6_config_detector.py` op.cont.3).
- **F4**: R10 (E-235 mp.info.5→mp.info.4 + compilar `var/templates_docx/E-235.docx`) · R11 (`fix_docx_templates.py` añadir `procedures` a append_sigblock · 0/38 POS con firma hoy) · R13 (E-100 2º bloque jinja que no compila) · R14 (builder roles art.11 org.2 + acuse mp.per.3) · R22 (limpiar andamiaje E-220) · R25 (`documentation_levels.py` + POS-set).
- **F5**: R15 (generador cuestionario CCN-STIC 808 cierre BÁSICA · corazón del cierre · no existe) · R20 (builders BIA/continuidad + citas ISO22301) · R26 (certificado ENAC descargable + NC estructuradas).
- **F6**: R23 (enriquecer rectores E-150/160/170).
- **VALIDACIÓN FINAL** (ver sección abajo): alembic scratch + **3 simulaciones Playwright** (BÁSICA/MEDIA/ALTA · admin+cliente · e2e · subir docs→lectura IA·firmar) + revisión auditor ENAC + documentación escrita.

### REGLAS INVIOLABLES (orden del usuario · reforzadas esta sesión)
1. **Verificar EMPÍRICAMENTE contra el código/BD reales, NO contra los tests** (pueden estar stale; hoy un test verde ocultaba un 500 en prod). Cero alucinación.
2. `ruff check` + pytest ANTES de cada commit. Commits a `main`. Deploy a prod (push origin main → CD) SOLO tras validar y con OK del usuario.
3. Migraciones requieren rol `fulkro_migrate` (owner) y validarse sobre **BD scratch vacía** (`alembic upgrade head` limpio + `alembic check` sin diff). PROHIBIDO `stamp`.

### HERRAMIENTAS y GOTCHAS creados/aprendidos esta sesión (reutilizar)
- **Recompilar docx**: `PYTHONPATH=. .venv/bin/python backend/scripts/rebuild_docx_templates.py E-041 E-042 ...` (genérico · gfm-smart · solo toca esos docx). Para E-040: `backend/scripts/build_informe_final_template.py`. Render-test E-040: `backend/scripts/render_test_e040.py [--synth]`.
- **Pipeline docx**: `.md` lleva valla ` ```jinja ` que es el DELIMITADOR del build (`extract_jinja_body` la strippea) → **NO quitar la valla**. pandoc con **`gfm-smart`** (el `smart` de `gfm` curva las comillas Jinja `'1.0'` y rompe el render). Post-proceso `fix_docx_templates.py` (header/footer/sigblock). Los `.docx` son **binarios trackeados en git** (no hay rebuild en CI). **Loop-tables `{% for %}` COLAPSAN en pandoc → usar listas con bullets**; tablas estáticas gateadas necesitan línea en blanco tras `{% if %}`.
- **Normativa**: **E-050 = Informe de Auditoría Interna del SGSI** · **E-150 = Plan de Adecuación** (NO confundir). Categorización = art.40 RD 311/2022 + Anexo I; Declaración de Aplicabilidad = art.28 + Anexo II.
- **Doble firma E-012**: `m01/signature_integration.py` `request_acta_double_signature(session, system_id)` + `get_acta_double_signature_status`. Roles competentes en `m30/roles_ens.py` (`responsable_informacion`/`responsable_servicio`). Resuelve firmantes vía `project_role_assignments`+`client_contacts`.
- **Copilot rate-limit (R09)**: el cap del cliente es POR PROYECTO (`get_rate_limit_status` EXIGE project_id para tier cliente). Resolver con `_resolve_project_meta_scoped` (en `m11/portal_api.py`). Todos los call-sites cliente arreglados.
- **GOTCHA DE SHELL (importante)**: en `wsl.exe bash -lc "..."` los **paréntesis, `;`, y comillas anidadas ROMPEN el quoting**. Solución: escribir el comando a un script `out/*.sh` (out/ está gitignored) y ejecutar `wsl.exe bash -lc 'bash out/x.sh'`. Mensajes de commit con paréntesis → `git commit -F fichero`.
- **Verificar deploy en el servidor real** (no solo el CD): `ssh fulkro` → `cd /opt/fulkro && git rev-parse --short HEAD` + `docker compose -f docker-compose.prod.yml --env-file .env.prod ps` (healthy) + curl `/api/v1/health` dentro del contenedor backend.

### ACCESO (verificado en disco esta sesión)
- **PAT Fulkrodev**: `/mnt/c/Users/Usuario/.fulkro_gh_pat` (Windows `C:\Users\Usuario\.fulkro_gh_pat`). NO está en `~/.fulkro_gh_pat` de WSL. Push: `git push "https://x-access-token:$(tr -d '\r\n ' < /mnt/c/Users/Usuario/.fulkro_gh_pat)@github.com/Fulkrodev/Fulkrosys.git" main`. **La API REST de GitHub SÍ funciona con este PAT** (`api.github.com/repos/Fulkrodev/Fulkrosys/actions/runs`). `gh` NO está instalado en WSL. El `GITHUB_TOKEN` del entorno es inválido.
- **SSH prod**: `ssh fulkro` (key WSL `~/.ssh/fulkro_hetzner` · `root@49.13.136.91` · dir `/opt/fulkro`). El clasificador lo gatea → pedir OK nombrando prod (el usuario ya autorizó el uso de la SSH key).
- **BD dev DSN async**: `postgresql+asyncpg://fulkro_app:fulkro_app_dev_password@localhost:5433/fulkro`. Migraciones: `DATABASE_MIGRATE_URL` (fulkro_migrate). Para saltar RLS en harness/scripts: `SET ROLE fulkro_app_bypassrls`. Roles: `fulkro` (superuser, NO conecta por TCP sin pass), `fulkro_app` (runtime), `fulkro_app_bypassrls` (escape), `fulkro_migrate` (owner migraciones).

### Worktree (no confundir)
El repo canónico es **`/home/usuario/fulkro` rama `main`** (lo desplegado en prod). La divergencia con `/home/usuario/fulkro-portales` que mencionan memorias viejas es HISTÓRICA (ya mergeado a main). Trabajar SIEMPRE en `/home/usuario/fulkro`.

---

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

## FASE 2 EN CURSO · progreso (audit empírico hecho · 4 agentes read-only · `out/f2_audit.md`)

**Hallazgos clave F2** (verificados):
- **Worktree canónico = `/home/usuario/fulkro` rama `main`** (head Alembic `rls_canonical_policies_002`, lo desplegado en prod). La divergencia con `fulkro-portales` es histórica (ya mergeado a main). BD live dev atrasada en `milestone_scheduled_date_28_001`.
- **E-012 tiene 3 variantes incoherentes**: (A) plantilla m06 `.md` (la canónica/rica), (B) `backend/app/templates/acta_e012_provisional.docx` (la que renderizan los endpoints m01 `api.py:800/914`), (C) generador inline `m01/service.py:419-483 generate_acta_e012` (monofirma RSeg). El flujo de firma m01 (`signature_integration.py`) usa magic-link M12 `FIRMA_DOCUMENTO` (texto libre) → **monofirma**, NO usa m05.
- **m05_signing**: `signing_intents`/`signing_events`(hash chain R6 inmutable, GRANT solo INSERT)/`signing_otp_codes`. `acta_comite` ya es SignableType (E-006/E-012). NO existe tabla de doble firma. Roles canónicos en `m30/roles_ens.py`: `responsable_informacion` (RI), `responsable_servicio` (RS), `responsable_seguridad` (RSEG), `responsable_sistema` (RSIS).
- **E-155**: BORRADOR; 11 notas `⚠ REVISIÓN CONSULTOR` están en comentarios Jinja `{# #}` (NO renderizan); `alcance.*` (servicios/sedes/sistemas/exclusiones) SIN fuente de datos ni builder; sin modelo de scope estructurado; sin tipo finalista/instrumental.

**HECHO F2** (commits en `main` local, sin push):
- ✅ **F2.1 R04 + R24-parcial** (`33d8f905`): citas E-012 art.28→art.40 (categorización) + art.28 (DA); E-050→E-150 (Plan de Adecuación) en E-012/E-003; footer "generado por FULKRO" fuera del cuerpo en E-002/E-003/E-012; clave canónica `responsable_sistema_informacion`→`responsable_sistema` en E-002/E-012/E-042 (+ fixture + smoke); `_ECODE_TO_SIGNABLE_TYPE` registra E-003/E-012→acta_comite; recompilador genérico `rebuild_docx_templates.py` (gfm-smart). 625 m06 + 30 m05 PASS.
- ✅ **R03 plantilla** (`6428959f`): bloque de firmas E-012 → RInfo+RServ APRUEBAN (art.40.2) + RSeg CONFORME (no aprobador). Auditor-visible.
- ✅ **R03 backend servicio** (`ce0cd50c`): `request_acta_double_signature` + `get_acta_double_signature_status` en `m01/signature_integration.py`. Crea 2 `signing_intents` m05 `acta_comite` (RInfo+RServ, mismo hash freeze, `signable_ref_id=categorization.id`), gate `aprobada`=ambos signed, idempotente, resuelve firmantes vía `project_role_assignments`+`client_contacts`. SIN migración (reusa m05 Ed25519+hash chain R6). 4 tests NEW + 17 m01-signature PASS.

**PENDIENTE F2**:
- ⏳ **R03 resto** (wiring · hacer en fase de simulaciones donde se ejercita el flujo admin+cliente E2E): (a) endpoints API m01 que expongan `request_acta_double_signature`/`get_acta_double_signature_status`; (b) canonicalizar la GENERACIÓN del acta — los endpoints m01 `api.py:800/914` renderizan `acta_e012_provisional.docx` (variante B, firmantes incorrectos); cambiar a `DocumentFactoryService.generate_document("E-012", ctx)` (plantilla m06 ya corregida) → requiere construir el contexto m06 (`decision_categorizacion`/`responsables`/`comite_seguridad`/`proyecto`) desde los datos m01; deprecar variantes B y C (`m01/service.py:419-483`). (c) UI cliente firma vía portal m05 `/firmas-pendientes` existente.
- ⏳ **R05 E-155**: builder `build_e155_alcance_context` + modelo de scope mínimo (servicios.tipo finalista/instrumental, sedes.tipo sede_fisica/region_cloud, exclusiones) · quitar frontmatter BORRADOR · validación anti-placeholder · cablear dimensiones desde m01. Probable migración (tabla scope) → scratch DB.
- ⏳ **R24-resto**: acta de decisión de adecuación de la Dirección (org.1) firmable autónoma (plantilla nueva + SignableType + paso en `fase0_governance.py`); coherencia `fecha_nombramiento` (decisión Marcos).

## DEPLOY 2 HECHO + VERIFICADO en servidor real (2026-06-11 ~22:46)

- **`git push origin main`** → prod Hetzner = **`ff85a715`** (8 commits: R02 + F2.1 + R03 plantilla+backend + copilot-fix). CD ✅ + CI ✅ (GitHub Actions). **0 migraciones nuevas** (chain Alembic sin cambios · DB-safe).
- **Verificado por SSH (no por el estado del CD)**: contenedores backend/frontend/celery/postgres recreados + **(healthy)**; `/api/v1/health → 200`; `_resolve_project_meta_scoped` presente en el código desplegado.
- **BUG REAL de prod encontrado y arreglado durante la validación** (commit `ff85a715`): R09 (FASE 0, ya en prod) hizo `project_id` obligatorio para el cap cliente, pero `client_copilot_stub.py` + `m11/portal_api.py` no lo pasaban → **el copiloto del cliente daba 500 en prod**. Fix: resolver project_id server-side + guarda anti-500. La suite "pasaba" en CI porque los tests estaban stale/mal — se cazó contrastando el CÓDIGO real (lección: verificar comportamiento real, no solo verde). Suite completa: 6003 passed / 0 fail.

## NEXT (orden): R05 → R24-resto → R03-wiring → F3 (incl. E-050→E-150 sistémico en E-041/042/043/090/614/615) → F4 → F5 → F6 → 3 simulaciones Playwright + auditor + docs → deploy

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
