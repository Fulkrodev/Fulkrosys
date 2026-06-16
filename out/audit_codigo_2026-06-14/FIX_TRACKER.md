# FULKRO — Tracker de resolución de hallazgos (auditoría 2026-06-15)

> Documento vivo. Se va **tachando** (`[x]`) cada hallazgo según se resuelve.
> Fuente: auditoría de código (lectura íntegra del repo, sin grep) — capítulo 14
> `Desktop/FULKRO_AUDITORIA_CODIGO_2026-06-15.md` y secciones en
> `out/audit_codigo_2026-06-14/sections/`.

## 🔬 RE-VERIFICACIÓN CÓDIGO-REAL vs TRACKER (2026-06-15 · workflow 9 agentes)

Marcos exigió (con razón) contrastar contra el CÓDIGO REAL (=Hetzner commit, confirmado
`git rev-parse` local==prod) en vez de fiarse del tracker. Resultado empírico de los 67
ítems que figuraban como abiertos: **16 YA_CERRADOS (líneas stale)** · **12 FALSOS POSITIVOS**
· **29 COSMÉTICOS** · **10 BUGS REALES (0 high · 4 medium · 6 low)**.

→ **7 corregidos + desplegados en `095f1bba` (w3n · DEPLOY #16)**: IDMS forja procedencia
(subido_por desde auth) · m_audit_accompaniment artifacts /tmp→var/ · MCP creds redact
(run_command redact=) · 422 "[object Object]"→detailToMessage · SigningFlow guard doble-submit
+429 status · pgBackRest stanza unify · m09 internal_auditor WARNING latente.

→ **3 DEFER honestos (NO blind-deployable · documentados)**:
  - `§5 373` Docker non-root + quitar [dev]: la imagen instala `.[dev]` que contiene
    **python-gvm = RUNTIME de OpenVAS** (openvas_runner.py:209) → quitar [dev] requiere PRIMERO
    mover python-gvm (auditar moto/otros) a deps de runtime; y `USER` non-root requiere
    `chown` coordinado del volumen `vardata` EXISTENTE en Hetzner (no se puede vía CD ciego).
  - `§1 362` lucia_federation client_secret como Bearer: OAuth incorrecto, pero el contrato
    real de la API CCN-CERT LUCIA no es verificable desde el repo (fallback pending_credentials).
  - `§2.7 342` registros cliente: contradicción copy("el consultor lleva registros")↔código
    (cliente puede crear/archivar). Decisión de producto: alinear a read-only cliente.

→ Los 29 COSMÉTICOS + 6 LOW restantes NO afectan a seguridad/datos/legal (deuda/UX).

### CONTINUACIÓN (Marcos: "todo funcional, bien wireado, con su frontend, muy estético")
1. `§2.7 342` registros → cliente read-only (backend require_owner POST/PATCH + FE ocultar create/archive).
2. Botones FE que w3m dejó deshabilitados ("próximamente") → o cablear funcionalidad REAL
   (EvidenceVault upload admin con form tipo+medida · IncidentDetail descarga E-CCN-NOTIFY ·
   VulnsTab pentest→m08) o confirmar con Marcos que el disable honesto basta pre-piloto.
3. `§5 373` Docker hardening (recategorizar python-gvm a runtime + non-root + chown Hetzner).
4. **PASE ESTÉTICO/UX GLOBAL** (Marcos 2026-06-15): TODAS las páginas de TODOS los sitios
   (admin · client-portal · auditor-portal · landing) deben quedar estéticas, intuitivas,
   legibles ("se lea clarito") y con MÁRGENES respetados/consistentes. Enfoque: (a) fijar la
   convención de contenedor/spacing/tipografía desde los tokens `--fulkro-*` + Tailwind ya
   existentes (no inventar), (b) auditar violaciones (márgenes inconsistentes, contraste/tamaños
   de fuente, layouts no intuitivos, paleta cruda vs tokens §4.5), (c) corregir por sitio en
   oleadas. Es trabajo amplio multi-página → estructurar con audit multi-agente + fixes por tanda.

---

## ✅ ESTADO FINAL CAMPAÑA (2026-06-15 · cierre)

**Todos los hallazgos REALES code-fixables están resueltos y desplegados a prod.**
Oleadas w2n…w3j (22 commits) · **13 despliegues a Hetzner** (todos CD verde · `app.fulkro.es` 200 · gate ruff+compileall activo desde w3e) · 1 migración de integridad nueva por deploy donde tocaba.

**Gate de cierre (verde)**:
- **Suite completa: 6237 passed · 101 skipped · 0 FALLOS** (5:14 · mock-by-default · post w3k-w3m · +3 tests guardia ENS).
- Schema: BD VACÍA → `alembic upgrade head` limpio → `alembic check` = **"No new upgrade operations detected"** (el drift `projects.supervision_mode` es columna HUÉRFANA muerta del phantom Ejecutable-8 · no en ORM/código/migración · NO aparece en fresh-deploy · inocua).
- ruff limpio en TODO `backend/` · tsc 0 errores en frontend.
- **Verificación adversarial de cierre** (workflow `audit-closure-verify` · 12 agentes · 58 checks): encontró **15 bugs reales que MIS PROPIOS fixes NO habían cerrado** (3 HIGH incl. un IDOR cross-tenant REAL explotable en m20, el cap de coste cliente evadido por la vía dominante, y mapeos ENS erróneos impresos en el informe ENAC). **TODOS corregidos** en w3k (3 HIGH) + w3l (mediums) + w3m (fake-completitud/latentes). Es la prueba de que la verificación adversarial valía la pena: 3 de mis fixes tenían holes.

**Resuelto por sección**: §1 seguridad (IDOR/RLS/cripto/XSS/privilegio/ofensivo) 100% · §2 bugs 2.1-2.8 (funcionales + esquema + cara-cliente + fugas 500 + GET-side-effect + commits + UI + perf) · §3.1 mocks (firma_documento + acta REALES · mata el mock de firma legal) · §4.4/§4.5 críticos (cap LLM real + Decimal fiscal + firma canónica + ENS mappings) · §5 gate de deploy + drift Alembic + dead-code · §6 pentest code-fixable (puente + race + kill-switch + Dockerfiles + scope/firma).

**Lo que queda ABIERTO (`[ ]`) es deliberado · NO son bugs sin arreglar** (doctrina 6 · distinguir bug de límite infra/scope):
- **[i] INFRA/Hetzner/cert** (no código · documentado honesto): binarios pentest reales (USE_MCP_REAL), provisión box ofensiva, pgBackRest stanza/bucket, credenciales MCP por args, passwords dev, imagen backend root, deps alpha, artefactos FS-local (LMS/actas/tmp → MinIO en deploy), m_compliance_monitor checks host-dependientes, lucia Bearer, XAdES/FACe.
- **COSMÉTICO/DEUDA** (deferido · bajo valor · no rompe nada): docstrings drift, naming legacy, patrones frontend (paleta/TanStack/a11y parcial/casts), duplicidades DRY, conteos desactualizados, heurísticas, code smells, N+1 m29, polling sin backoff, hooks menores, schedulers día-exacto, rutas WSL hardcoded en scripts.
- **STUBS honestos** (declarados incompletos · NO falsa-completitud): M8 semantic mapper / bloodhound metadata / nmap wire-up, m_observability golden eval, download-token 501, TokenScaffold, m13 tasks vacío, botones FE placeholder. Frontera honesta documentada.
- **FALSOS POSITIVOS verificados** (código manda): tablas-sin-RLS (las 160 tenant SÍ tienen RLS) · Lead CheckConstraint (declarado w2y) · JSON citations (consistente por módulo) · m_audit_sim export (sólo LIMIT 1) · Caddy split (ya divide) · .dockerignore (existe) · agente allowlist (7==7) · invoices GET / notifications commit / m23 commit (ya correctos).
- **DECISIONES DE PRODUCTO** (NO FIX · documentado): autopilot mode=internal sin magic-link (dogfooding · no toca infra cliente) · arquitectura MCP dual (spawn in-process vs compose) · convenciones RLS/taxonomías coexistentes.
- **DEFER architecturalmente coherente**: M02/M03 portal db.get-antes-de-validar (fail-closed HOY por RLS · IDOR sólo si futuro bypassrls) · sub-encargados DPA (deriva de RoPA nombres = Future-X) · per-project RTO/RPO desde BIA · `controls`/radar orphans (drop destructivo en prod no justificado).

---

## 🟢 CAMPAÑA audit-roundup 2026-06-16 (continuación · rama fix/audit-roundup-2026-06-16)

Segunda pasada sobre la auditoría: se **re-triaron los 113 ítems pendientes `[ ]`** del tracker y se **re-verificaron contra el código real** los `[x]` críticos de seguridad (workflow de 28 agentes + 2 workflows de consolidación → `CONSOLIDATED_TRIAGE_2026-06-16.md`, 182 ítems con veredicto+evidencia). Resultado: **22 bugs REALES + ~34 cosméticos baratos CORREGIDOS**, más **1 bug de PRODUCCIÓN nuevo** (no estaba en los 113) que destapó la suite al avanzar la BD de test al head. El resto (22 falsos positivos + 17 decisiones de producto + ~47 líneas stale ya correctas + 9 infra/cert) queda **confirmado SIN acción** o **abierto deliberado** (infra/needs-Marcos). 12 commits en la rama, sin push (pendiente OK de Marcos).

### Bugs reales corregidos (TIER-1 → commit)

| Ítem (sección tracker) | Fix | Commit |
|---|---|---|
| **[HIGH] §2.2/223 esquema desglose propuesta** (`concepto/importe` vs `code/description/amount`) | Puente de esquemas en consumidores m13/m15: billing buscaba el hito por `nombre`/`importe` y **fallaba SIEMPRE** en propuestas Apéndice-M → `BillingError` → **facturación rota**; lookup ahora con fallback `nombre→description→code` + `importe→amount`, y el render DOCX igual | **`fff16e51`** (W1) |
| §2.2/226 severidad incidente m19 ES↔EN | classify escribía español (`critica`) en columna consumida en inglés → routing CCN-CERT no disparaba; normalizado a vocab canónico inglés | **`63d549c4`** (W2) |
| §2.8/274 scheduler renovación bianual `==` día-exacto | umbral `<=` + guarda de idempotencia por hito (espejo m25) → catch-up real si el beat no corre ese día; sin pérdida de hitos 6m/3m/1m | **`63d549c4`** (W2) |
| §2.8/272 distintivo público O(n) LIMIT 1000 | keyset scan en vez de scan lineal | **`63d549c4`** (W2) |
| §4.5/390c DLQ `reprocess` no re-encolaba (no-op silencioso) | re-dispatch real de la notificación + audit_log; ya no marca `queued` y se queda colgado | **`08f02256`** (W3) |
| §4.3 email `DIAGNOSTICO_PRECLIENTE` (#38) sin plantilla → ValueError | `PurposeEmailConfig` añadida + test corregido (asumía el bug) | **`08f02256`** (W3) |
| §4.1/341 labels signable types (14 vs 18 · OTP BÁSICA salía "Documento") | `get_signable_label` cae al mapa canónico de 18 | **`08f02256`** (W3) |
| §1.4 `corpus.py` sin `require_owner` (sesión cliente listaba corpus/stats) | `dependencies=[require_owner]` (low: corpus normativo público) | **`08f02256`** (W3) |
| §3.3 m12 `return None` inalcanzable | línea muerta eliminada | **`08f02256`** (W3) |
| §4.5/388b AWS rollback CloudTrail nombre hardcoded | lee el nombre real desde `_state_before` (no borra el trail equivocado) | **`b17d514e`** (W4) |
| §4.5/387 citations copiloto clave divergente (`items`/`ids` vs `list`) | clave canónica `items` + normalización en lectura | **`b17d514e`** (W4) |
| §4.5/390a auth/api accede `_PRIVATE_PEM` + re-implementa `jwt.encode` | mint JWT vía helper de `crypto` + accessor público para JWKS | **`b17d514e`** (W4) |
| §4.5/384 R29 `"llevas"` substring → falsos positivos | regex con límite de palabra (`llevas razón` pasa) | **`b17d514e`** (W4) |
| §3.2/305 m8 evidencia `E-702` hardcoded (nunca `E-704` external) + bloodhound descripción sobre-vende | rama por tipo de run + descripción honesta del tool | **`b17d514e`** (W4) |
| §4.1/343 drift constantes eventos C3/C4 M09 (re-declaradas) | import desde `audit_events.py` (cero cambio de valor) | **`e73b7e27`** (W5) |
| §4.3 identidad Fulkro hardcodeada + versiones `0.1.0` + `_coerce_id` dup + A19 logger mal etiquetado (`A21:`/`A22:`) | cluster identity/version/event-const/code-smell | **`e73b7e27`** (W5) |
| §3.2/314 CTA RetainerOpsCenter "Agente 26 · priorizar" fake-success | refetch real de `/agent-26/summary`+`/alerts` (era `setTimeout`+toast mentiroso) | **`03ea982c`** (W6) |
| §3.2/314 CTA RetainerDashboard toast falso | toast real | **`03ea982c`** (W6) |
| §4.5/378 arrays de fases FE con drift vs enum BE | `WorkflowPhase`/`PHASE_ORDER` alineados al enum canónico de 10 (stepper cliente ya resalta) | **`03ea982c`** (W6) |
| §1.8/180 contraseñas temporales en toast efímero 10-15s | `Dialog` persistente + botón Copiar (patrón `PortalUserPanel`) | **`75cf44c2`** (W8) |
| §3.1/295 `useCreateLead` mock puro (dead code) | función mock borrada (sin consumidores) | **`75cf44c2`** (W8) |
| §4.5/383 wrappers `api`/`clientApi` sin timeout + §4.5/379 `continuidad.ts` read/write divergente + tailwind shade 400 + §2.8 base64 ineficiente + OPS-044 (4 clientes cliente con `api()` admin) + plazo `+7d` post-firma inventado | cluster FE: `AbortSignal.timeout`, tipos unificados, `primary.400`, swap a `clientApi`, polling backoff | **`be7a7b74`** (W7) |
| §4.4/367B landing legal `[completar]` (Titular+Domicilio) + §4.4/366 sub-encargados DPA divergentes RoPA + EvidenceVault | landing rellenado (Titular/Domicilio conocidos, NIF queda) + DPA deriva Anexo I de RoPA + **EvidenceVault upload real** | **`015a7079`** (W9-1) |

### 🔴 BUG DE PRODUCCIÓN encontrado por la suite (NO estaba en los 113)

Al avanzar la BD de test al head, la suite destapó que la migración `fulkro_pii_rls_002` (campaña anterior, w3l) **rompía el consentimiento de cookies ANÓNIMO en fulkro.es**: la policy RLS de `fulkro_consent_audit_log` era fail-closed contra `current_client_id()`, pero un visitante anónimo del landing inserta con `tenant_client_id = NULL` → la policy rechazaba el INSERT → **500 al aceptar cookies** → incumplimiento LSSI/AEPD (no se podía registrar el consentimiento legalmente exigible). **Fix**: migración **`anon_consent_rls_001`** (USING/WITH CHECK `tenant_client_id = current_client_id() OR tenant_client_id IS NULL`) — el visitante anónimo NULL pasa y el **aislamiento tenant queda intacto** (un cliente sólo ve lo suyo) + test de guardia. Commit **`4bfa1a6f`**.

### Pentest real en Hetzner (Opción 1)

Commit **`30da58ec`** añade **trivy/grype/checkov/scoutsuite** a la imagen backend (verificado con `scanner-verify.Dockerfile`; `checkov`/`scoutsuite` vía `pipx` aislado para no contaminar el venv) + doc `USE_MCP_REAL` + runbook **`docs/operations/PENTEST_REAL_SCANNERS_HETZNER.md`**. Encaje: `m_remediation` actúa sobre **postura cloud + host** (no AD ni red-team), así que este set (vuln/IaC/cloud-posture) es el que aporta; **nikto/OpenVAS/AD diferidos** (infra ofensiva on-demand, Opción 2/3).

### EvidenceVault cerrado de verdad

Nuevo endpoint **`GET /evidence/projects/{id}/upload-catalog`** + **formulario admin real** (tipo + medida) en commit **`015a7079`** → el botón ya **NO es un disabled "próximamente"**; el backend `POST /evidence/projects/{id}/upload` (que ya existía) queda cableado a una UI funcional.

### Confirmado SIN acción (veredictos del re-triaje contra código real)

- **22 FALSO_POSITIVO verificados**: `mcps.py` YA tenía `require_owner` · `_dev/login-as-marcos` doble-gate · `corpus.py` (auth global cubre) · ZAP `disablekey` sólo dev · insert permisivo `WITH CHECK(true)` intencional (triggers/hash-chain) · `marcos_timesheet_entries` skip-RLS documentado · `personalization.py` sin sink HTML · `enroll_endpoint_edr` GUARDED · agente allowlist 7==7 · `fn_audit_log_verify_chain` ya correcto · drift signable CHECK ya ampliado · etc.
- **17 PRODUCT_DECISION**: m8 semantic mapper stub honesto (cae a LLM Haiku) · download-token 501 pre-cliente · FKs lógicas sin constraint (desacople inter-motor documentado) · autopilot `mode=internal` sin magic-link (dogfooding) · arquitectura MCP dual · taxonomías RLS coexistentes · etc.
- **~47 líneas stale** ya correctas en el código (declaradas resueltas en oleadas previas pero el tracker no lo reflejaba).

### Abierto deliberado (NO son bugs)

- **NIF/CIF** en imprint/privacy + landing: `[needs-marcos]` (dato real inexistente · alta de autónomo en curso). Cuando exista → `FULKRO_NIF` en `fulkro_identity` + sustituir los 4 placeholders.
- **`projects.supervision_mode`**: columna huérfana del phantom migration `cluster6_supervision_mode_001` (purgado). **Empíricamente limpia en fresh deploy** (BD vacía → `upgrade head` = 0 columnas extra · `alembic check` sólo la marca en BDs longevas que la arrastran). Inocua (sin ORM/código/migración).
- **Audit §5.2** (4 ítems de diseño cloud intencional): sin representación previa en el tracker; documentados como decisión de arquitectura, no deuda.
- **OpenVAS/ZAP/arsenal AD**: infra ofensiva Opción 2/3 on-demand (box Hetzner dedicada). Diferido a demanda real.
- **Docker non-root**: documentado; requiere `chown` coordinado del volumen `vardata` existente en Hetzner (no aplicable vía CD ciego).

### Gate

Suite backend **verde** (re-confirmada) · frontend **`tsc` 0** · **`ruff` limpio** en los ficheros tocados · **`alembic head = anon_consent_rls_001`** (1 head, fresh `upgrade head` limpio) · **12 commits** en la rama `fix/audit-roundup-2026-06-16` · **sin push** (pendiente OK de Marcos para deploy).

---

## CONTEXTO PARA RETOMAR (leer primero al continuar)

- **Rama de trabajo**: `fix/audit-2026-06-15` (rama de `main`). **⚠️ YA MERGEADA Y DESPLEGADA**: 2026-06-15 Marcos ordenó push+deploy → `main` FF a `34331dba` + push GitHub + CD desplegó a Hetzner prod (verde, `app.fulkro.es` 200). Ver sección 🚀 DEPLOY al final. La rama sigue viva para continuar la campaña; los próximos commits van sobre `main` (ya FF) o sobre la rama → re-deploy con el mismo flujo.
- **Modo**: commit por oleada. Push+deploy bajo orden de Marcos (el último fue 2026-06-15). Cada commit lleva `Co-Authored-By: Claude Opus 4.8`.
- **Doctrinas (de Marcos, inviolables)**:
  1. **El código manda**, no los docs/ADR/CLAUDE.md ni la propia auditoría. Verificar SIEMPRE
     cada hallazgo contra el código real antes de tocar (hay falsos positivos).
  2. **Un test verde NO prueba corrección.** Los tests pueden estar mal planteados/obsoletos.
     Si un test asume el comportamiento erróneo, **se corrige el test** para reflejar la realidad.
  3. **Entender Fulkro como conjunto** — cada arreglo debe encajar coherente con el sistema.
  4. **Multitenant: cliente = proyecto (1:1).** Aislamiento POR PROYECTO en todo fix de seguridad/RLS/IDOR.
  5. **No romper. Infra/BD persistentes.** Que TODO funcione, sin stubs/placeholders/bugs, bien cableado.
  6. Distinguir bug de límite intencional (scope-out) o dependiente de infra/cert externos (Hetzner).
- **Puerta de tests**: `bash scripts/build_test_db.sh` (una vez) + `python -m pytest <módulo> -q`
  desde repo-root con `.venv` activado, vía `wsl.exe -e bash -lc '...'`.
- **Estados**: `[x]` HECHO (commit) · `[~]` FALSO POSITIVO / ya correcto (no tocar) ·
  `[i]` INFRA/CERT-dependiente (documentar, no falsear) · `[ ]` PENDIENTE.

### Próximos pasos sugeridos (siguiente sesión)
1. Continuar **oleada seguridad §1** (IDOR m20 workspace; RLS-bajo-fulkro_app m19/m30/m_compliance/m27/feature_flags; gate pentest M8; XSS emails MJML + dangerouslySetInnerHTML; OTP WhatsApp `random`→`secrets`; webhook 360dialog HMAC).
2. Luego **bugs §2** restantes (m26 celery, m23 reports, NotificationOrchestrator SSE, WhatsApp dispatch, m02 hybrid/dedup, m04 fallback/req_all_signed, m_live_records UUID, simulacro hardcoded, m27 PCE catalogs, loguru, etc.).
3. **Mocks vivos §3.1** (LegacyDocumentSignFlow, useCreateLead/useLeads, etc.).
4. **Dead code §3.3 + deuda §4** (seguro) · **UI/perf/a11y §6**.
5. Cada oleada: verificar → arreglar → corregir tests si procede → `pytest` módulo → commit → tachar aquí.
6. Al final: suite completa + `ruff` + `mypy` + alembic `upgrade head` sobre BD vacía (gate infra).

---

## §1 SEGURIDAD / MULTITENANT-RLS

### 1.1 IDOR portal cliente bajo `fulkro_app_bypassrls`
- [x] **m29 adjuntos** — IDOR HIGH cross-tenant: `mark_upload_complete`/`get_download_url` sin atar a `message_id`. **`540c6e3d`** (binding `attachment.message_id==message_id` + 4 call-sites).
- [x] **m21_diagnosis** — IDOR cross-project download-docx/quick-wins: binding `project_id`. **`540c6e3d`**.
- [x] **m20 workspace** — `get_file`/`delete_file` (**`w2c`**) + `mark_feed_read`/`message_thread`/`accept|start|end_videocall` (**`w2i`**): todos con binding `*.workspace_id == ws.id` (workspace 1:1 proyecto). m20 §1.1 cerrado.
- [x] **m28 `assign_role`** — ahora ata `ClientContact.client_id == project_client_id` (cliente=proyecto); un contact client-scoped de otro tenant no se puede asignar. **`w2b`**.
- [~] **M02/M03 portal** — **FP verificado en el cierre adversarial (NO es IDOR)**: los endpoints resource-only (m02 asset/risk, m03 entry) resuelven el project_id DESDE el recurso (asset→analysis→project, entry→project · no desde input) y validan `_ensure_project_belongs_to_client` contra `user.client_id` (patrón m29) ANTES de leer/mutar. NO replican el bug de m20 (que comparaba contra el owner del proyecto). Único matiz: devuelven 403 en vez de 404 cross-tenant (oráculo de existencia · severidad baja · opcional homogeneizar a 404).
- [~] Mitigaciones ejemplares ya presentes (referencia, no bug): `_assert_thread_in_project`, `_set_cliente_context_for_gap`.

### 1.2 RLS-bajo-fulkro_app (endpoints project-scoped sin set_tenant_context)
- [x] **m19** `continuity_test_execution_api._ensure_project_rls` → `get_project_owner` (SECURITY DEFINER, fix chicken-and-egg) + import muerto Project retirado. **`w2d`**.
- [x] **m30** `portal_user_api.py` + `project_scope_api.py` → ahora fijan `set_tenant_context` (helper `_set_project_rls`/_get_client_id_for_project) en todos los handlers (evita lista/estado vacío en prod + aísla por proyecto). **`w2d`**.
- [x] **m_compliance** `reject_erasure` → `SET LOCAL ROLE fulkro_app_bypassrls` + `RESET ROLE` (mirror del approve) para leer el email del rechazo. **`w2g`**.
- [x] **m27** GET `get_status`/`route_history`/`get_renewal`/`list_exports` ahora `if _set_project_rls is None → 404`; `admin_badge_svg` ahora SÍ llama `_set_project_rls` antes de construir el distintivo. **`w2h`**. (audit-schedule/lucia/ines: verificar en próxima pasada si quedan GET sin check.)
- [x] **core/feature_flags/dependencies.py** `_load_project_with_client` → get_project_owner + set_tenant_context antes del SELECT (las 3 deps corren como Depends antes del endpoint → 404 espurio bajo RLS). **`w2g`**.

### 1.3 RLS fail-open / herencia de rol (mayormente ya corregido; riesgo en downgrade)
- [~] Hash R6 bifurcado cross-tenant — ya corregido `audit_hash_chain_secdef_001` (riesgo solo si downgrade).
- [~] Fuga RLS herencia de rol — ya corregido `fase0_rls_leak_fix_001`.
- [~] RLS fail-OPEN histórica — ya corregido `rls_fail_closed_hardening_001` + canonical.
- [ ] **Tablas project-scoped creadas sin RLS en su migración** — VERIFICADO real (agente reportó ~32 tablas pero se contradice con #1 que dice magerit_assets/threat SÍ tienen RLS). REQUIERE verificación empírica contra la BD (pg_policies + relrowsecurity) antes de migración → NO fiarse del listado del agente. QUEUED oleada RLS-coverage w2s (empírica + migración única).
- [~] **`insert_permissive WITH CHECK(true)`** en `unify_pricing_fiscal_rls_001` y `audit_log_rls_001` — **FALSO POSITIVO**: intencional. INSERT permisivo necesario para triggers (hash-chain audit_log con project_id/client_id NULL) + jobs admin; el aislamiento se aplica en el USING (lectura), no en WITH CHECK. pricing_config es global (sin client_id). Patrón consistente (oauth_state_rls_001). Tests isolation verifican.
- [x] **`client_messages` `OR current_client_id() IS NULL`** — fail-OPEN → fail-CLOSED. Migración `client_messages_rls_failclosed_001`: policy única `client_messages_tenant_isolation TO fulkro_app USING/CHECK(client_id=current_client_id())`, SIN `OR ... IS NULL` y SIN admin_bypass. **`w2r`**. ⚠️ HALLAZGO NUEVO (la BD real manda): una policy `admin_bypass TO fulkro_app_bypassrls USING(true)` FUGA al pool cliente (fulkro_app miembro INHERIT) → NO usar; admin bypasea por el ATRIBUTO BYPASSRLS (SET ROLE). Ver memoria `rls-admin-bypass-policy-leaks.md`. m29 25 PASS.

### 1.4 Asimetrías y superficies de privilegio
- [i] Rol `fulkro_migrate` sigue miembro de `fulkro` (necesario para ALTER) — límite de diseño, documentar.
- [~] Endpoints `_dev` alto privilegio (`login-as-marcos`) — **FALSO POSITIVO**: doble gate fail-closed robusto (router no se monta si `is_production`; cada endpoint llama `_require_non_production()`→404; `is_production` = propiedad read-only con match exacto APP_ENV=="production"; default "development"). No hay path de exposición por misconfig.
- [x] **m02 `pilar_import_api.py` SIN `require_owner` ni RLS** — router SÍ se registra (main.py:598). Ahora `dependencies=[require_owner]` + `_ensure_analysis_exists` fija contexto RLS vía `get_magerit_analysis_owner()` SECURITY DEFINER + `set_tenant_context` (mirror m02/api.py). **`w2o`**.
- [~] **`PATCH /dda/entries/{id}` activa `fulkro_app_bypassrls`** — **FALSO POSITIVO**: router gateado con `dependencies=[require_owner]` (Marcos-only single-operator). El bypassrls para lookup por id es intencional (patrón M12). Sin riesgo IDOR en modelo single-operator.
- [x] **Router A21 `agent_21_api.py`** — ahora `dependencies=[require_owner]` a nivel router (los 4 endpoints eran alcanzables por cualquier autenticado; `_set_project_rls` sólo valida existencia, NO autoriza). Mirror agents/api.py. **`w2o`**.
- [x] **`mcps.py`** (inventario pentest) → `dependencies=[require_owner]` (revelaba el arsenal ofensivo a cualquier sesión). **`w2p`**. · [x] **`projects.py`** (Project Composer) → `dependencies=[require_owner]` (sesión cliente leía cualquier proyecto por UUID; `_set_project_rls` fijaba contexto al owner sin verificar llamante). **`w2p`**. · [~] **`corpus.py`** FALSO POSITIVO (auth global cubre · corpus normativo compartido sin project_id · ingest por scripts).
- [~] **ZAP dev** `api.disablekey=true` — **FALSO POSITIVO**: sólo en `docker-compose.yml` perfil `scanner` (opt-in dev); `docker-compose.prod.yml` no define ZAP. Sin riesgo en prod.
- [x] **Webhook 360dialog** sin HMAC `X-Hub-Signature-256` → ahora verifica firma HMAC-SHA256 del raw body (formato Meta/WhatsApp Cloud) + token compartido como fallback compat; fail-closed 403 si hay secret y no casa. Tests a la nueva firma + 3 casos HMAC. **`w2o`**.

### 1.5 Criptografía / claves / firma
- [x] Claves Ed25519 efímeras si falta env — fail-fast en PROD vía `is_production()` añadido a los 4 loaders sin guard (auth/crypto · m12 magic_link · m25 backup_builder · m_remediation agent_service). M05/M06/M07 ya lo tenían (signing_keys canónico). Dev/test mantienen efímero. **`w2q`**.
- [x] `verify_signature` (auth/api) `except (InvalidSignature, Exception)` → `except InvalidSignature` (no enmascarar bugs). **`w2q`**.
- [x] **M07** verification_service re-verifica la firma Ed25519 (firma_timestamp persistido · migración w3a). **`w3a`** · ANTES: (`signature_valid=None`) — VERIFICADO real (high). El payload firmado incluye un timestamp que NO se persiste → no se puede reconstruir. FIX = añadir columna `firma_timestamp` + persistir en ingestion + reconstruir+verify. QUEUED oleada migraciones w2s.
- [i] Timestamping RFC3161 no valida cadena TSA — límite documentado.
- [x] `secure=False` hardcoded MinIO → `secure=settings.minio_use_tls` (default False dev; MINIO_USE_TLS=true prod). **`w2q`**.
- [x] `request_otp` reseteaba `attempts=0` al re-solicitar (CRÍTICO: esquivaba el bloqueo max_attempts → fuerza bruta ilimitada 6 dígitos). Eliminado el reset; el contador persiste entre regeneraciones. **`w2q`**.
- [x] `sign()` OTP-legacy sin advisory lock → añade `pg_advisory_xact_lock` per-documento (Pattern #22, como sign_canvas). **`w2q`**.
- [x] OTP magic link con expiración propia (otp_expires_at TTL 15min · check en consume). **`w3a`** · ANTES: (vive lo que el link) — VERIFICADO real (medium · M05 sí lo aísla con TTL 5min). FIX = columna `otp_expires_at` + check en consume. QUEUED oleada migraciones w2s.
- [x] **OTP WhatsApp** `random.choices` → `secrets.choice` (CSPRNG). **`w2e`**. PENDIENTE menor: OTP en claro en BD + sin rate-limit (endurecer aparte).
- [i] **Geo-restriction magic links declarada pero NO aplicada** — DEFER-INFRA: requiere lib GeoIP (MaxMind/IP2Location, coste+datos). Ya documentado honestamente como "preparado, no aplicado" (README + comentario + docstring). NO falsear; activar post-infra GeoIP.
- [x] Heurística idempotencia cifrado por prefijo "gAAAAA" (migración 90dd52c1dfd9) → try-decrypt robusto (upgrade+downgrade). **`w2q`**.
- [ ] Credenciales por args en MCP servers (visibles en process list) — usar stdin/env/ficheros.
- [ ] Clave firma remediación efímera en dev — fail-fast/verificar.
- [ ] **Datos sensibles en localStorage sin cifrar** (borrador findings pentester) — no persistir en claro.
- [ ] Credenciales AWS IAM larga vida en estado React — preferir OAuth read-only.
- [x] `os.environ` no thread-safe en `offensive_engagement` → ContextVar task-local (auth) + env per-spawn box. **`w3f`**.

### 1.6 XSS / inyección HTML / sub-comandos
- [x] **XSS emails m_compliance** — `mjml_compiler` activaba autoescape salvo `.mjml` → variables sin escapar. Ahora `select_autoescape(enabled=("mjml","html","xml"))`; sin plantillas con HTML-crudo (no rompe nada). **`w2f`** (pend. test).
- [x] **`BillingHistory` `dangerouslySetInnerHTML` + `manual_transfer.render_html_block`** — `render_html_block` ahora `html.escape()` sobre TODOS los campos dinámicos (institution/iban/holder/concept/bic/reference) → la salida que renderiza BillingHistory queda garantizada segura EN EL ORIGEN. (El path vivo hoy sólo pasa config-admin + nº correlativo, pero la función acepta `concept_override` → defensa real.) **`w2n`**.
- [x] **`SignDPAFlow`** href `descarga_pdf_url` — nuevo helper `isSafeHref()` (whitelist http/https + relativas, bloquea `javascript:`/`data:`/`vbscript:`) aplicado al `<a href>`. Defensa en profundidad: el purpose está deprecado→422 hoy, pero el `<a>` existe en el código. **`w2n`**.
- [~] `personalization.py` desactiva autoescape Jinja2 — **FALSO POSITIVO verificado**: la `descripcion` renderizada se consume SÓLO como texto React/JSON (`ObligationBoard.tsx` sin `dangerouslySetInnerHTML`; backend api.py:234 JSON + gantt_service texto) — NO hay sink HTML/PDF/docx. Forzar autoescape corrompería el texto cliente (`&`→`&amp;` literal). El comentario del código es correcto. NO tocar.
- [x] `agent_15_vigilancia` `<a href>` con title/url de feeds RSS externos — ahora `html.escape()` del title/source + validación de protocolo del href (sólo http/https → resto "#"). **`w2s`**. 21 PASS.
- [x] Inyección en sub-comandos MCP (`atomic_red_team`/`sliver`/`metasploit`/`impacket`) — helper `reject_unsafe_args()` (rechaza `; & | ` `` ` `` ` $ < > \n`) aplicado a las 8 wrappers que interpolan args en el intérprete de la tool (msfconsole -qx / powershell -Command / sliver --command). Defensa-en-profundidad sobre scope+approval. **`w2t`**.
- [x] `DataFlowTab` mermaid.live — ahora botón con `window.confirm()` explícito antes de enviar la arquitectura a servicio externo (admin-only). **`w2s`**.
- [~] `NotificationsTab` override JSON sin validar schema — **FALSO POSITIVO**: el backend valida con Pydantic (extra=forbid + EmailStr) → 422 fail-closed antes de persistir. Sólo es mejora UX (opcional).

### 1.7 Bypass de scope / autorización subsistema ofensivo
- [x] **Gate autorización M8** — `create_run` gateaba `mode=="external"` (literal muerto) → ahora `mode=="external_handoff"` (el modo que toca infra); test corregido a la realidad (usaba el modo inexistente). **`w2b`**.
- [x] Bypass parcial scope `public_api.py` VPN config — guard anti path-traversal (resolve+relative_to var/verification_vpn) como /documents/{index}. **`w2t`**. (rate limiter in-memory: acotado, low.)
- [x] Bypass scope phishing `launch` sin payload — ahora launch exige payload.targets y valida cada uno (antes `and payload` lo saltaba). **`w2t`**.
- [x] Exclusiones scope CIDR + IPv6 — `extract_host()` IPv6-aware + exclusiones con `ip_network` (CIDR). **`w2t`**.
- [x] `scope_enforcer` duplica `shared.scope_check` + no verifica firma — matching unificado en `evaluate_target_scope` (enforcer delega) + `load_authorization` verifica HMAC `PENTEST_AUTHORIZATION_SIG` fail-closed. **`w2t`** (cierra solape §6).
- [~] `enroll_endpoint_edr` ejecuta comando arbitrario — **FALSO POSITIVO**: GUARDED (requiere autorización) + firma Ed25519 servidor + allowlist (server+agente) + el cmd lo provee el cliente (string conocido del vendor EDR). Diseño intencional gateado.
- [x] Agente on-prem perms+backoff — `STATE_DIR.chmod(0o700)` antes de escribir la clave + backoff exponencial con jitter en el poll. **`w2t`**. (drift `agent_protocol` sig_hex vs signature_hex = cosmético · funcionalmente idéntico · agente standalone no importa backend · deuda menor.)

### 1.8 Hardening / configuración
- [i] CSP estricta frontend NO implementada (`TODO-SEC-CSP-001`, FASE 13).
- [ ] CSP backend `script-src 'unsafe-inline' 'unsafe-eval'` (justificado Next, sin nonce).
- [ ] Passwords dev en claro versionadas (mitigado prod) — revisar.
- [~] `COPY . .` frontend sin `.dockerignore` — **FP**: `frontend/.dockerignore` EXISTE (excluye node_modules/.next/out/.env*.local/test-results/…). (nit opcional: añadir `.env` pelado.)
- [ ] CORS `*`+credentials en no-prod (acotado por guard).
- [ ] `trusted_timestamps` append-only solo por convención (migración da UPDATE/DELETE, sin triggers).
- [ ] `SignFlow`/`SigningFlow` detección 429 por string-match + sin guard doble-submit + sin AbortController.
- [ ] `m_compliance_monitor check_rls_coverage_percentage` superficial (solo `relrowsecurity`).
- [ ] Contraseñas temporales en claro en UI admin (toast 10-15s) — revisar.

---

## §2 BUGS / INCOHERENCIAS LÓGICAS

### 2.1 Bugs funcionales
- [x] **M09 firmas faltantes nunca bloquean dossier** — `firmas["pendientes"]`. **`9675cd50`**.
- [x] **m23 drift compute** `activo`→`active`. **`9675cd50`**.
- [x] **m23 reportes retainer** — `report_renderer` consultaba `period_type='quarterly'` pero el modelo/escritor persisten `'trimestral'` (verificado: retainer.py:172 + checkin INSERT 'trimestral' + tests `=='trimestral'/'anual'`). Renderer → `'trimestral'`. **`w2j`**.
- [x] **m26 Celery** firmas aceptan id (alineadas). **`w2y`** · (backup/DR stub Hetzner [i]) · ANTES: — `POST /jobs` despacha tasks con `args=[id]` pero las firmas son zero-arg → TypeError. VERIFICADO real (critical-rated · pero m26 backup/DR es stub Hetzner [i]). FIX = alinear firmas (aceptar id) + integración DB start/complete. QUEUED w2w (parte infra [i]).
- [x] **WhatsApp workflow nunca se envía** — `dispatch_critical_event` se llamaba con kwargs erróneos (client_user/message/target_url vs client_user_id/payload) → TypeError tragado por except amplio. Corregido. **`w2u`**.
- [x] **NotificationOrchestrator SSE muerto** — `_dispatch_portal_sse` por defecto → `project:{event.project_id}` (canal vivo del portal) en vez de `client_user:{id}`; test corregido a la realidad (usaba el canal muerto). **`w2l`**.
- [x] **m_workflow_engine `done` vs `completed`** — TERMINAL_STEP_STATUSES. **`9675cd50`**.
- [x] **m_workflow_engine `propagate_unblock`** — ahora se invoca tras commit en `advance_step` (best-effort) → pasos dependientes blocked→available. **`w2u`**.
- [x] **m27 pilar_adapter degrada I/C/A/T a BAJO** — SELECT 5 dims. **`9675cd50`**.
- [~] **m27 catálogos PCE muertos** — VERIFICADO real PERO el fix one-liner (añadir a OVERLAY_TYPES) ROMPE: el loader hace `f"pce_{overlay_type}.yaml"` → `pce_pce_nis2.yaml` FileNotFound (test lo cazó). Requiere rewiring coherente (fichero+overlay_type+KNOWN_OVERLAYS+campo YAML+detect codes). NO core ENS (NIS2/SSG extra). REVERTIDO en w2u + nota en código. DEFER rewiring dedicado.
- [x] **m30 bug orden de rutas** `/validate-roles-ens` (`:uuid`). **`9675cd50`**. — pendiente sub: `import_csv` KeyError→500.
- [x] **m02 XXE** — `parse_xml` (lxml etree.fromstring) sin protección → XXE/SSRF/billion-laughs. Parser endurecido (resolve_entities=False+no_network+load_dtd=False). **`w2u`**. · [~] **m02 `hybrid`** = INTENCIONAL (NotImplementedError documentado ADR-031 + tests de contrato permanente). · [ ] **m02 dedup** import_to_analysis crea duplicados en re-import (sin unique (analysis_id,code)) → DEFER w2v.
- [x] **m04 fallback determinista** — vocab severidad mayor/menor/info → canónico critica/alta/media/baja/informativa (catalog_loader usa {alta,critica}; el anterior NUNCA casaba). Tests del fallback usaban vocab ficticio → corregidos. **`w2u`**.
- [x] **m04 `req_all_signed`** exige status=signed (join signing_intent.status). **`w2y`** · ANTES: (debe ser estado `signed`) → DEFER w2w (requiere join a signing_intent.status).
- [~] **M10 nivel máximo L3/L5** — conservador a propósito (sin métricas reales). NO bug. + `estado_impl=="implantada"` correcto.
- [x] **m28 estado persistido vs retornado** — devolver `audit_row.status`. **`9675cd50`**.
- [~] **m_audit_accompaniment ciclo MEDIO/ALTO** — `is_terminal_state` nunca True es ARGUABLE-INTENCIONAL (ciclo de renovación bianual perpetuo · biannual_renewal_scheduled→preparation por diseño). El dual-emit (SSE+ClientNotification) es enhancement menor (el SSE ya emite en canal project:{id} al que el portal se suscribe). DEFER (no romper el ciclo de renovación). w2w revisar dual-emit si demanda.
- [x] **m_live_records typo** `leciones_aprendidas`→`lecciones_aprendidas` (orphan · extra=forbid rechazaba el dato). **`w2u`**. · [ ] creator UUID cero + listeners created_by=None → DEFER w2w (requiere inspección modelos Incident/Change/ProviderAssessment para fuente del creator).
- [x] **simulacro_pre_enac `get_last_simulacro_report`** — critical_gaps/high_gaps/coverage_pct/current_phase ya NO hardcodeados a 0 → leen payload_new real (service.py:319-321 sí los persiste · GATE-7). **`w2u`**.
- [x] **`LegacyDocumentSignFlow` MOCK en producción** sirviendo `/sign/[token]` — RESUELTO **`w3c`** (ver §3.1: firma_documento real · Ed25519 m05).
- [ ] **`useCreateLead` mock puro** (ver §3.1).
- [ ] **m23 regla NPS muerta** (`nps_last_score` siempre None) — VERIFICADO real (gather_signals no consulta nps_responses) → DEFER w2w (añadir query).
- [x] **m21_diagnosis `m1_m2_feeds`** "AI Act"→"AI" peso. **`9675cd50`**.
- [x] **A20 fallback f-string sin interpolar** — `garantia or "...{cat}."` sin prefijo f → ahora f-string. **`w2u`**.
- [ ] **Shadowing `i` en `corpus_ingest_v2.py`** (solo log · minor) → DEFER.
- [x] **Logging Celery roto (loguru `%`-style)** — m29 tasks.py 2 logs `%d/%s`→`{}` (loguru usa `.format`). **`w2u`**. (m_observability/notifications: grep NO encontró %-style loguru → el agente sobre-listó.)
- [x] **`_fw_read` frágil a `ufw`** — regex ahora casa `443/tcp DENY`. **`w2u`**. · [~] `_pkg_read compliant=False` = INTENCIONAL (comentado: permite la actualización GUARDED cuando se solicita) → revisar el verify-loop del agente antes de tocar (host-dependent · DEFER).

### 2.2 Incoherencias firma SQL / esquema / drift catálogo↔CHECK
- [~] `fn_audit_log_verify_chain()` usada como tabla-función y como escalar — **FP (ya corregido w2y)**: los 3 call-sites en app/ usan la forma tabla `SELECT ... FROM fn_...()` correcta.
- [x] Invariante muerto `NEVER_ACTIVE_AND_EXPIRED_TOGETHER` (siempre False · rama `state==ACTIVE and state in TERMINAL_STATES`) — retirado del tuple + branch. **`w3d`**.
- [~] Drift catálogo-Python↔CHECK en `signable_type` — **FP (ya corregido)**: migración `signable_type_widen_001` (2026-06-14) amplió el CHECK a los 18 tipos del catálogo. CHECK efectivo == catálogo.
- [x] `DiagnosisRun.project_id` UUID indexado SIN ForeignKey — **FK añadida `w3a`** (`fk_diagnosis_runs_project_id` CASCADE).
- [ ] FKs lógicas masivas sin constraint (`client_signing_intent_id`, `pkg_node_id`, etc.) — acoplamiento laxo.
- [ ] CheckConstraint 8 estados `Lead`/`LeadStageHistory` mencionado pero NO declarado.
- [~] `leads.estado_contacto` (8) diverge de `radar_leads.estado_contacto` (10) — **FP (muerto)**: radar fue eliminado (`drop_ens_radar_001` · `radar_leads` sin ORM). Sólo vive `leads` (8 estados).
- [ ] Esquema desglose divergente propuesta (`concepto/importe` vs `code/description/amount`).
- [x] Mapping medidas pentest corregido (op.exp.10→op.exp.3/7 ai_classifier + ens_mapper backups). **`w3j`** · ANTES: (`op.exp.3/7` vs `op.exp.10`).
- [ ] Fragmentación RAG m23 (green/verde/VERDE) → emojis no mapean.
- [ ] Severidad inglés/español incoherente m19 incident.
- [ ] m_siem `siem_overview` cap 2000 vs `/events` limit 200 (subestima correlaciones).
- [ ] Coexisten 2-3 convenciones RLS (`current_project_id()` vs raw vs `current_role_pool`).
- [ ] 2 taxonomías categoría (BASICA/MEDIA/ALTA vs BASICO/MEDIO/ALTO) en `verification/`.
- [x] `admin_cross_project_compliance.py` tablas corregidas (evidence_requests/severidad/conformity_routes) + SAVEPOINT. **`w3j`** · ANTES: (silenciados por except).
- [~] Decisión "NO RLS" `marcos_timesheet_entries` — **FP (intencional)**: tabla admin-only cross-cliente (CapacityTile/RetainerOpsCenter) · skip RLS documentado (`sane_polish_rls_email_log_001`). Acceso sólo admin-side.
- [ ] Doble migración `phase_changed` + discrepancias filename↔revision id (cosmético).

### 2.3 Incoherencias normativas (cara cliente/auditor)
- [~] **`DeclarationHeader` "73 medidas Anexo II" para BÁSICA** — **FP (ya corregido w2w)**: `MEDIDAS_POR_CATEGORIA = {BASICA:52, MEDIA:68, ALTA:73}` por tier.
- [ ] Plazos post-firma divergentes (`+7/+30-60` hardcoded vs backend) — cosmético/bajo (`TierAwareNextStepSection` duplica timeline `<ol>` junto al prose backend `next_step_post_signature`). DEFER cosmético (copy informativo · no legal/fiscal).
- [x] Copy "hash chain Ed25519" cuando audit log es SHA-256 — **`w2w`** (SummaryView) + **`w3d`** (SigningFlow "firma Ed25519 + cadena SHA-256").

### 2.4 Fuga de detalle interno en errores 500
- [x] Copiloto expone `str(exc)` — copiloto agent_14 (producer SSE) + m11 stream → genérico+log. **`w3g`**. (agents/api.py + agent_21 ValueError→400 = mensajes de validación, FP; A18 ya `w2x`.)
- [~] `RemediationClienteView`/`RemediationPortal` error crudo — **FP**: ya muestran mensaje genérico + toast friendly (console.error el detalle).
- [x] `except Exception` aapp-billing/status → narrow + logger.warning. **`w3g`**. (adenda-check: FP · captura excepciones NOMBRADAS best-effort documentadas.)

### 2.5 GET con side-effect de escritura
- [~] `invoices_aapp_api.get_late_interest` muta+commitea en GET — **FP (ya corregido)**: ahora cómputo puro read-only (comentario §2.5).
- [x] `renewal_extensions_api` GET con efectos (crea campaign+milestones+commit) — GET /timeline + /auditor-info read-only (timeline/ventana EFÍMEROS · materialización sólo en POST/scheduler). **`w3g`**.

### 2.6 Persistencia: commits faltantes / huérfano
- [~] `get_db()` sin commit automático — patrón conocido (no bug en sí; revisar consumidores).
- [~] `notifications/api.py` `update_my_preferences` flush sin commit — **FP (ya corregido)**: `await db.commit()` presente (comentario §2.6).
- [~] m23 retainer transition/scan sin commit — **FP**: todos los endpoints de mutación + tasks commitean (verificado).
- [x] M07 `ingestion_service` persiste fichero ANTES del flush DB (huérfano) — fichero tras flush. **`w2v`**.

### 2.7 Bugs/robustez UI (riesgo bajo)
- [x] División por cero: `firmas-hub`, `PolicyHeader` (NaN%) — guardas `total>0`. **`w2y`**.
- [x] `CheckinDetail` TypeError si falta `evidence_freshness` — optional-chain. **`w2y`**.
- [x] `WorkflowBlockersPanel` error en verde — feedback {text,isError} rojo en error. **`w3i`**.
- [x] `VerifyAuthPortal` aria-describedby + "Reenviar OTP" + error bruto — id helper + cooldown 30s + quita detalle crudo. **`w3g`**.
- [x] `AuthGuard` render null silencioso ante 500 — AuthErrorCard + Reintentar. **`w3i`**.
- [ ] N+1 queries m29 `_list_threads` — perf bajo (chats por proyecto · volumen pequeño). DEFER perf.
- [x] `utils.ts formatDate/formatDay` sin guarda fecha inválida — guarda añadida. **`w2y`**.
- [ ] hooks menores (`useClientProjectEvents` accompaniment callback · `useMeeting savingNotes` · `useOnboardingAdmin`) — DEFER cosmético (no rompen flujo).
- [x] Doble suscripción SSE `AdminChatPanel`/`AdminClarificationsInbox` — una sola conexión vía hook callbacks. **`w3i`**.
- [x] `oauth-callback`/`/sign/[token]` muestran string crudo — oauth genérico **`w3i`** + sign dispatcher real **`w3c`**.
- [ ] Polling sin backoff + counts parciales (inbox/notifications) — DEFER cosmético (UX menor).
- [x] `ClientNotification.created_at` naive sobre columna tz-aware — `datetime.now(timezone.utc)`. **`w2y`**.

### 2.8 Rendimiento / escalabilidad
- [x] m02 `_propagate_values_quantitative` exponencial — `all_simple_paths(cutoff=8)`. **`w2z`**.
- [x] m04 N queries Evidence por medida — batch. **`w2z`**.
- [x] m_live_records exports cap 10.000 truncado SILENCIOSO → captura total + logger.warning si trunca. **`w3h`**. (m_audit_sim: FP, sólo LIMIT 1.)
- [ ] m27 distintivo público linear scan O(n) LIMIT 1000.
- [ ] base64 client-side ineficiente (UploadDocumentModal/IDMS).
- [ ] Schedulers por igualdad exacta de días (sin catch-up si cron no corre ese día).

---

## §3 CÓDIGO MUERTO / MOCKS

### 3.1 Mocks vivos en superficies "producción"
- [x] **`LegacyDocumentSignFlow` (MOCK FIRMA FALSA — PIEZA Nº1 "PRODUCTO TERMINADO")** · CERRADO:
   - [x] **`aprobacion_acta` REAL** (**`w2m`**): NEW endpoint público `POST /api/v1/minutes-signing/approve` (`minutes_public_api.py`) consume el magic-link (valida OTP/caducidad/usos) + registra la firma real del asistente vía `MinutesService.register_signature` (atómico + SSE). NEW `ApproveActaFlow.tsx` + `lib/api/minutes-signing.ts`; dispatcher enruta `aprobacion_acta`→ApproveActaFlow. 3 tests (happy + OTP 403 + no-acepta 422) + 17 m18 = 20 PASS.
   - [x] **`firma_documento` REAL** (**`w3c`**): el dispatcher enruta `firma_documento`→`DocumentSigningFlow` (real). NEW `m05 SigningService.sign_document_external()` (firma Ed25519 + hash chain R6 de firmante externo sin client_user · actor_type=system · identidad en el mensaje firmado · sobre el hash congelado del snapshot · reusa primitivos de sign() DRY). NEW endpoint público `POST /api/v1/document-signing/sign` (patrón w2m: consume magic-link → valida OTP/purpose → mapea scope.document_type→SignableType → firma · rollback total + SSE). Cubre acta E-012 (m01) · MAGERIT E-028 (m02) · DdA E-040 (m03) · k6 (m_meetings) · cambio fase (m19) · conformidad (m27). NEW `DocumentSigningFlow.tsx` + `lib/api/document-signing.ts`; `sign-flow-purposes.spec.ts` actualizado (firma_documento ya NO espera el mock). 5 tests (firma real+chain válida · genérico · OTP 403 · no-acepta 422 · purpose 400) + 41/41 m05 + tsc 0. (Mock `LegacyDocumentSignFlow` queda SOLO como fallback offline E2E para tokens inexistentes/404 · no es path de firma real.)
   - HISTÓRICO investigación (cada consumidor tenía su mecanismo · resuelto vía endpoint genérico que mapea scope.document_type):
       · **acta E-012 (m01)**: YA existe camino REAL nuevo (R03 doble firma competente RInfo+RServ vía **m05 signing_intents** Ed25519 + hash chain R6, `signable_ref_id=categorization.id`, `signature_integration.py:189+`). El viejo `FIRMA_DOCUMENTO` magic-link→mock está SUPERSEDED → habría que enrutar al flujo m05 real (o `/portal/firmas-pendientes`) y retirar la rama mock.
       · **DdA (m19 triggers)** y **k6 (m_meetings)**: verificar si usan m05 signing_intents o necesitan endpoint propio.
       PLAN: por consumidor, identificar el camino real (m05 intent vs otro) → enrutar `/sign/[token]` firma_documento al flujo real correcto (probable reuse de `ContractCanvasSignFlow`/SignatureCanvas + m05 sign_canvas) → quitar `LegacyDocumentSignFlow` + `mockSignPayload` + fallback de error honesto + E2E. (Dedicado · firma legal · no rushear.)
   **Plan (backend a completar):**
   1. Backend m18 `POST /minutes/{id}/sign` real YA existe (registra firma por magic_link_id) + `/signing-status`. Falta endpoint análogo de consumo para `firma_documento` (DdA/E-012/k6) que registre firma Ed25519 + audit log + avance workflow.
   2. Backend: enriquecer el **status público del magic-link** (`useMagicLinkStatus`) para devolver, en `firma_documento`/`aprobacion_acta`, el contexto del documento (minutes_id/doc_code/title/preview/requires_otp/magic_link_id).
   3. Frontend: 2 componentes reales (`ApproveActaFlow` → POST /minutes/{id}/sign; `DocumentSignFlow` → endpoint firma_documento) que reemplacen al mock; idealmente reusar `ContractCanvasSignFlow` (canvas Ed25519 real ya existe).
   4. Quitar `LegacyDocumentSignFlow` + `mockSignPayload` (public-portal-fixtures) + el fallback de error → tarjeta honesta "enlace no válido/caducado" (NO firma falsa).
   5. Actualizar E2E `sign-flow-purposes.spec.ts` + `magic-link.spec.ts` a los flujos reales.
   ⚠️ Feature dedicada (~backend+frontend+tests). NO rushear (firma = legal/ENAC).
- [ ] `useCreateLead` mock puro + `useLeads`→`MOCK_LEADS` gated NODE_ENV pero en bundle.
- [ ] `lib/mock.ts` (KPIs/leads ficticios) + `lib/types.ts` "mocked for now".
- [ ] `copiloto-admin.ts`+`useCopilotoAdmin` apuntan a stub (`is_stub`) coexistiendo con RAG real.
- [ ] `contacto.html` `#leadForm` sin backend (honeypot no validado).
- [ ] `/admin/pipeline` `DevHint` "Leads mock".
- [ ] M8/M22 demos "DataForma" sin scanners reales.

### 3.2 Stubs honestos / incompleto declarado
- [i] M15 XAdES/FACe stubs (cert FNMT + API FACe) — INFRA/CERT.
- [ ] M8 capa semántica ENS mapper STUB (`_semantic_match` devuelve []).
- [ ] M8 stubs: `bloodhound_analyze` solo metadatos; `create_evidence_for_finding` hardcodea "E-702"; `nmap_runner` sin wire-up; `vuln_orchestrator.py` deprecado.
- [i] m26 `monthly_restore_test`/`run_dr_drill` stubs — Hetzner.
- [ ] m_observability golden eval skeleton.
- [ ] m17/M9 `internal_auditor.py` (A11/E-701) latente sin caller.
- [i] m20 videocalls sin LiveKit real (`future`).
- [ ] `/download/[token]` certificado M27 + dossier M09 stubs 501.
- [ ] `TokenScaffold` placeholder (5 rutas FASE 9).
- [ ] `m13 tasks.py` vacío (scaffold Celery).
- [i] m_legal subsistema dormant (scope-out T2).
- [ ] Botones/CTAs placeholder FE: EvidenceVault, VulnsTab, IncidentDetail, DiscoveryPanel, RetainerDashboard/OpsCenter.

### 3.3 Código legacy / huérfano
- [~] `m10/launch_productivo_subatom_n.py` — **FP (ya no existe)**: el fichero no está en el repo.
- [~] `corpus_ingest.py` v1 — **MANTENER**: `clean_ccn_watermarks` lo importa `test_corpus_clean.py` + `corpus/catalog.py`. NO borrar.
- [x] `create_rls_policies.py`/`rls_policies.sql` legacy (`ALTER ROLE fulkro BYPASSRLS` · FOOTGUN) — **borrados `w3e`** (zero-refs).
- [x] `rename_sgsi_ids.py` one-shot consumido — **borrado `w3e`** (zero-refs).
- [~] Constantes muertas `startup_checks.py` (_M06/_M07/_KEYS_DIR) — **FP (ya eliminadas)**: el comentario en startup_checks.py:25 lo confirma.
- [ ] Migración vacía nombre engañoso `83e27091b489` + `.replace("'","'")` no-op.
- [ ] Tabla `controls` huérfana (0 lecturas) — clase ORM `Control` sin uso; borrarla requiere también migración drop de la tabla → DEFER (bajo valor · no footgun).
- [ ] Tablas radar en árbol migraciones pese a drop + vars `ENS_RADAR_*` en `.env.example`.
- [ ] `PortalSwitcher` inerte (return null).
- [ ] m14 deprecado vivo (`send_for_client_signature`/`register_client_signature` + schema muerto).
- [ ] Dead code m12 (`return None` inalcanzable; `migration_mappings.yaml` 2/23).
- [ ] Definido sin consumidor: `cancel_videocall`, `check_access`/`my_accessible_documents`, `whatsapp_critical_events_routing`, `MeetingPermissionError`.
- [ ] Excepciones declaradas y no lanzadas (varias) + helpers/constantes sin usar (varias).
- [ ] Imports muertos frontend (lint).
- [ ] Código dormido `/admin/pipeline/*` + `_components/*Tab.tsx` huérfanos + `/admin/inbox` stub.

---

## §4 DEUDA TÉCNICA / TODO-FIXME (lo seguro primero)

### 4.1 Duplicidad / divergencia (DRY)
- [ ] Doble linaje m21_diagnosis (PKG vs ORM Paso 5).
- [ ] Doble archival m25 (`ArchivedProject` vs `ProjectArchivedBackup`) + `delete_project_data(force)` sin 2º gate.
- [ ] Doble fuente esfuerzo m17 (`estimate_effort` vs `estimate_full`).
- [ ] Doble fuente labels signable types (backend 18/14, frontend 12/7).
- [ ] Catálogos SignableType divergentes FE↔BE + mapas duplicados.
- [ ] Drift constantes eventos C3/C4 M09 (re-declaradas vs import).
- [ ] Schemas frontend espejo manual (sin generación; riesgo drift).
- [ ] 4 clientes "cliente" usan `api()` admin path absoluto (rompe OPS-044).
- [ ] `__init__.py` single point of failure de drift modelos.
- [ ] Duplicidad conectores cloud (`CloudConnectFirstStep` vs `ConnectorsClientView`).
- [ ] Naming legacy `_trigger_cliente_aporta_magic_link` (ya no genera magic link).

### 4.2 TODO/FIXME explícitos
- [i] `TODO-SEC-CSP-001` (FASE 13) · [ ] `TODO-RBAC-PER-ENDPOINT-001` · [i] `TODO-FACE-XADES/API` ·
  [ ] `TODO-FE-DARK-MODE` · [ ] `TODO-FASE-X-MAGIC-LINK-PORTAL-INTEGRATION-001` · [ ] `workflow.ts /transition` MB-18 ·
  [ ] `useWorkspace` videollamadas · [ ] DEPRECATED `generate_acta_e012`, `vuln_orchestrator.py`.

### 4.3 Drift documental (docstrings vs código)
- [ ] policy_enforcer "deprecated_soft NO bloquea" es hard-reject real (impacto funcional: `/generate` 422).
- [ ] Cobertura plantillas email incompleta (`DIAGNOSTICO_PRECLIENTE` #38 → ValueError).
- [ ] Pricing docstring obsoleto (5500/9500/17500) vs canónico (fuente `pricing_config`).
- [ ] Conteos endpoints/fases/purposes desactualizados (varios) — cosmético salvo los funcionales.
- [ ] Identidad Fulkro hardcodeada en varias salidas sin usar `fulkro_identity` (minutes_docx, email_forward, draft_report, etc.).
- [ ] Versiones `0.1.0` hardcoded + `suite_passing=81` stub.

### 4.4 Calidad de datos / contenido
- [ ] `obligations_library.json` solapamiento + colisión E-050.
- [ ] Datos compliance en migración `sane_mb9bis_ropa_001` (mitigado).
- [ ] Sub-encargados hardcoded en DOCX DPA vs RoPA.
- [needs-marcos] **`landing/aviso-legal.html` + `privacidad.html` placeholders `[completar]`** (LSSI/RGPD) — NIF/CIF + nombre titular + domicilio fiscal: NO fabricables (alta autónomo en curso · ver NEEDS-MARCOS). Email/teléfono YA correctos (coinciden con fulkro_identity).
- [x] `aggregate_dpc_context_snapshot` backup_jobs marcado backup_scope=platform + rto_rpo_source. **`w3j`** · ANTES: (uptime/rto/rpo).
- [x] `process_basic_declaration` firma sobre `str()` de tuplas (no JSON canónico) → JSON canónico (sort_keys). **`w3d`**.
- [ ] Matches frágiles por string (LIKE id, nombre proyecto, split "Garantía:").
- [x] Decimal→float al persistir importes — Invoice/InvoiceLine (m15) + RetainerBillingEvent/líneas (m23) persisten Decimal directo (Numeric(12,2)). **`w3d`**. (float() de display/JSON/DOCX se dejan · no persisten.)
- [i] Migraciones destructivas/irreversibles (downgrade NotImplemented/DROP+recreate) — documentar.

### 4.5 Deuda de patrón / consistencia frontend
- [ ] Paleta cromática mixta (Tailwind crudo vs tokens `--fulkro-*`).
- [ ] Componentes sin TanStack (BrandingForm, ChurnRiskWidget, etc.).
- [ ] Accesibilidad parcial (focus-trap/ESC, aria-label tablas, skip-link).
- [ ] Arrays de fases hardcoded FE con drift vs enum BE.
- [ ] Casts forzados de tipos + `continuidad.ts` read/write divergente + `tailwind.config` shade 400.
- [ ] Acoplamiento cross-route por path relativo.
- [ ] Duplicidad ruta admin `/implementation` y `/obligations` mismo board + doble redirect cliente.
- [ ] Contradicción registros (`registros/page` redirige pero `registros/[tipo]` crea/archiva).
- [ ] Wrappers `api`/`clientApi` sin timeout/AbortController + `ClientApiError` formatea mal 422.
- [ ] Heurísticas A21 gruesas + falsos positivos R29 (`"llevas"`).
- [x] **m11 inline agents cliente sin rate-limit** + `_suggestion_cache` sin purga — enforce cap cliente (429) + feature_override "inline_cliente_*" (cap los cuenta) + cache poda TTL+512. **`w3h`**.
- [x] **`cost_usd` no poblado en LLMInteractionLog** → cap mensual no acumula — NEW core/ai/pricing.py + poblado en todos los write sites (base.py + copilot cliente/admin + agent_14 chat[_stream]). **`w3h`**.
- [ ] JSON citations divergente (`items`/`ids`/`list`).
- [ ] Heurísticas backend (lucia Bearer, aws rollback nombre hardcoded, bridge substrings, PII regex sin Luhn).
- [ ] Contadores denormalizados + `KnowledgeChunk.embedding` fallback Vector→LargeBinary.
- [ ] Code smells menores (acceso `_PRIVATE_PEM`, MV owner, `_coerce_id` dup, `dlq.reprocess` no re-encola, A19 logger mal etiquetado).

---

## §5 INFRA / HETZNER (no falsear; documentar o arreglar lo que sea código)
- [i] Frontera honesta pentest (`USE_MCP_REAL` binarios solo Hetzner).
- [x] Dockerfiles MCP: best-effort con log visible + verificación command -v (build falla sin binario primario). **`w3f`** · ANTES: (`2>/dev/null||true`, `@latest`, imports rotos) — arreglable en repo.
- [i] Provisioner ofensivo on-demand Hetzner.
- [i] m26 backup/DR stubs Hetzner (+ wiring Celery roto §2.1).
- [i] m15 facturación AAPP XAdES/FACe.
- [i] PDF maestro pandoc/LibreOffice.
- [ ] m_compliance_monitor checks dependientes del host con rutas relativas frágiles.
- [ ] `lucia_federation` usa `client_secret` como Bearer.
- [i] WORM solo si bucket creado de cero.
- [ ] **Rutas absolutas/WSL hardcodeadas** (`/home/usuario/fulkro`, `/mnt/c/...`) en scripts/ingestores → portabilidad.
- [ ] Scripts `build_*` guarda parcial (`search()` pierde si >1 valla).
- [x] **Head Alembic divergente entre scripts** — **`w3e`**: era drift de COMENTARIO (los comandos usan `upgrade head` dinámico · `alembic heads`=1). Comentarios/log dejan de nombrar revisión obsoleta (provision-entrypoint x2 + deploy-hetzner).
- [ ] Topología multi-head Alembic + `alembic-version-num-widen` (revision ids 33>VARCHAR(32)).
- [ ] Mismatch stanza pgBackRest (`fulkro` vs `fulkro-prod`) + `pg1-user` divergente.
- [ ] Incoherencia bucket backup (`fulkro-backups` vs `backup-vault-fulkro`).
- [~] Caddyfile.prod proxya todo a `app:8000` — **FP**: YA divide (`handle /api/* → app:8000` con matcher SSE · `handle → frontend:3000`). Service `app` = alias de red de `backend` (compose). (`rate_limit` módulo = mejora opcional.)
- [x] **`deploy.yml` sin gate de tests previo** → NEW job `gate` (ruff pin + compileall · `deploy: needs:[gate]`). **`w3e`**. (gate de tests completo sigue local · BD en runner pendiente.)
- [ ] Duplicación `admin-polish-empirical.yml` (3 jobs sin matrix).
- [ ] Imagen backend monolítica como root, instala `.[dev]` en prod, sin USER no-root.
- [ ] Deps frontend alpha (`react-signature-canvas`) en prod + rangos `^` amplios + sin `tsc --noEmit`.
- [ ] `FULKRO_SKIP_WORKFLOW_GATES` bypass prereqs (riesgo si en prod).

### 5.5 Artefactos en filesystem local (no MinIO/WORM)
- [ ] Evidencias LMS E-502/503 en `var/documents_lms` + re-submit quizzes sin límite.
- [ ] m_audit_accompaniment en `/tmp` por defecto (pérdida en contenedor).
- [ ] Actas E-005 en `var/documents_minutes`.
- [ ] `deliverables_service` asume FS local (404 si MinIO `minio://`).
- [ ] `intake` IDMS permite `subido_por` arbitrario (procedencia no autenticada).

---

## §6 PENTEST/RED-TEAM — gaps detectados (auditoría de código wf_61c0b375, 2026-06-15)
Madurez global honesta ~60%. Cerebro determinista + frontend sólidos; ejecución real y puentes, no.
**Código-fixable (NO esperan a Hetzner):**
- [x] **Puente pentest→remediación**: NEW propose_remediations_from_findings (host findings → RemediationJobs). **`w3b`** · ANTES roto: (host findings). Falta `propose_remediations_from_findings()` + routing finding→host→agente. Hoy 100% manual.
- [x] **MCP `requires_approval` ahora se enforce** (fail-closed en `shared/mcp_protocol.py _handle_tool_call`): las 16 tools destructivas (metasploit/sliver/sqlmap/pacu/gophish…) se rechazan salvo `params.approved=true`. **`w2k`**.
- [x] **Firma de scope decorativa** — `shared.scope_check.load_authorization` ahora verifica la firma HMAC `PENTEST_AUTHORIZATION_SIG` (import perezoso de `verify_authorization`) fail-closed: firma presente e inválida/no verificable → auth vacío → todo denegado. **`w2t`**. (+ scope_enforcer deja de duplicar la lógica.)
- [x] **Carrera `os.environ["PENTEST_AUTHORIZATION"]`** → ContextVar task-local (`pentest_authorization_context` · invoke_mcp inyecta en env del hijo). **`w3f`**.
- [x] **Kill-switch no alcanza** procesos `invoke_mcp` → con run_id en el contexto, spawn en propio process group (start_new_session) + `tracked_subprocess(run_id, pid)` → killpg alcanza al server.py + hijos. **`w3f`**.
- [~] **Agente on-prem allowlist desync** — **FP**: `agent_protocol.PLAYBOOK_ALLOWLIST` (7) == `host_playbooks.HOST_PLAYBOOKS` REGISTRY (7) · sin desync (la auditoría asumió `agent/playbooks.py` que no existe).
- [ ] **Autopilot `mode="internal"` no exige magic-link cliente** — NO FIX (decisión de producto: "internal" = dogfooding Fulkro · no toca infra cliente · el gate vive en external_handoff que SÍ la toca · w2b). Documentado.
- [x] **MCP Dockerfiles no reproducibles** (recon/infra/redteam/webpentest): `2>/dev/null||true` → best-effort con log VISIBLE + capa `command -v` que falla el build si falta binario primario. **`w3f`**.
- [ ] **Arquitectura MCP dual**: 14 contenedores compose perfil `pentest` que el backend NUNCA invoca (usa spawn in-process); prod no despliega MCP. Decidir modelo.
- [ ] UX (no bug): doble enum categoría BASICO/MEDIO/ALTO vs BASICA/MEDIA/ALTA + 2 flujos de lanzamiento coexistiendo.
**Infra Hetzner (NO código · documentar):** [i] `USE_MCP_REAL=false` default → sin binarios el pentest corre en vacío · [i] faltan binarios en imagen (openvas/trivy/grype/zap/nikto/amass/checkov/kube-bench/scoutsuite) · [i] box ofensiva Hetzner mock · [i] `FULKRO_REMEDIATION_SIGNING_KEY` estable en prod.
**Sólido (NO tocar):** máquina estados findings, gates 1-5+verification_level, manifest SHA-256+golden drift, EvidenceRecord R6 append-only, injection guard + Verdict advisory (nunca baja severidad), ciclo remediación cloud fail-closed, blindaje cripto agente (Ed25519+allowlist+dry-run+revocación), retest honesto, c.13/c.14 honesto.

## REGISTRO DE COMMITS (oleadas) — rama fix/audit-2026-06-15
- `9675cd50` — w1a: 7 bugs funcionales §2.1 (839 tests módulos verdes).
- `540c6e3d` — w2a: IDOR HIGH m29 adjuntos + binding m21_diagnosis (114 verdes).
- `fe00632a` — w2b: gate pentest M8 (HIGH) + IDOR m28 assign_role (395 verdes).
- `249f1a24` — w2c: m20 workspace get_file/delete_file binding (38 verdes).
- `7a5a60ab` — w2d: RLS m19 continuity + m30 project_scope/portal_user (205 verdes).
- `3b91362a` — w2e: OTP WhatsApp → secrets (CSPRNG).
- `193f402e` — w2f: XSS emails MJML autoescape (99 verdes).
- `752d6dc9` — w2g: RLS m_compliance reject_erasure + feature_flags deps (43+ verdes).
- `2a61ad7f` — w2h: RLS m27 conformity GETs sin check None (verdes).
- `20abe502` — w2i: m20 feed/thread/videocall binding (verdes). → §1.1 m20 cerrado, §1.2 RLS cerrado.
- `4dbbbd31` — w2j: m23 report_renderer period_type quarterly→trimestral.
- `f9953182` — cleanup: borrar 161 docs auditoría/histórico obsoletos (code-refs solo comentarios, verificado).
- `c14239c4` — w2k: MCP requires_approval enforce fail-closed (-32003 si no approved).
- `f510f5f8` — w2l: NotificationOrchestrator SSE al canal vivo project:{id} (client_user:{id} era canal muerto).
- `34331dba` — w2m: **FEATURE** firma REAL aprobacion_acta vía magic-link (quita el mock LegacyDocumentSignFlow). Backend endpoint público + ApproveActaFlow + 3 tests (20 m18 PASS).
- `b43114c1` — w2n: XSS §1.6 — `manual_transfer.render_html_block` `html.escape()` campos dinámicos (cubre BillingHistory) + `isSafeHref()` en `SignDPAFlow`. manual_transfer 11 PASS. (personalization autoescape = falso positivo verificado, NO tocado.)
- `0bf127d2` — w2o: privilegio §1.4 — webhook 360dialog HMAC-SHA256 raw body (+token fallback) + gate `require_owner` en m02 pilar_import_api (+RLS context) y router A21. Smoke app.main 1200 rutas; webhook 6 PASS; m02 pilar + A21 29 PASS.
- `0005c3fa` — w2p: privilegio §1.4 — owner-gate `mcps.py` (inventario pentest) + `projects.py` (Project Composer · leía cualquier proyecto por UUID). mcps+project-scoping 32 PASS. (FP: insert WITH CHECK · dda PATCH · _dev · corpus · ZAP.)
- `2f5bbe3b` — w2q: cripto §1.5 — Ed25519 fail-fast prod (4 loaders) + verify_signature except acotado + request_otp no-reset attempts (CRÍTICO) + sign() advisory lock + MinIO TLS setting + migración cifrado try-decrypt. 442 PASS. (Defer migraciones: M07 re-verify · OTP TTL. [i] geo GeoIP.)
- `3be9d71b` — w2r: RLS §1.3 — migración client_messages fail-OPEN→fail-CLOSED (`OR current_client_id() IS NULL` eliminado). HALLAZGO NUEVO empírico: admin_bypass policy FUGA al pool cliente (INHERIT) → memoria rls-admin-bypass-policy-leaks. m29 25 PASS. (FP: cobertura RLS "32 tablas" → las 160 tenant-scoped YA tienen RLS.)
- `88250262` — w2s: XSS/fuga §1.6 — agent15 digest href escape+protocolo + DataFlowTab mermaid.live confirm. 21 PASS. (FP: NotificationsTab.)
- `c1d43631` — w2t: §1.7 ofensivo + §1.6 MCP-injection — scope CIDR/IPv6 + firma HMAC verify + enforcer DRY + gophish launch scope + vpn path-traversal + agente perms/backoff + 8 wrappers reject_unsafe_args. 533 PASS 4 skip. (FP: enroll_endpoint_edr.)
- `1272663c` — w2u: §2.1 bugs funcionales — m02 XXE (parser endurecido) + whatsapp kwargs + propagate_unblock + m04 vocab severidad (+tests) + simulacro hardcoded + agent20 fstring + _fw_read regex + m_live_records typo + m29 loguru. build_test_db OK (254 tablas) + alembic check sin drift + 877+ módulos PASS. (Revert m27 PCE; FP m02 hybrid.)
- (repo limpiado de 23 artefactos de auditoría antes de empezar.)

- `e62c5d56` — w2v: §2.5/§2.6/§2.4 — GET late-interest read-only + commits (notifications prefs, retainer transition+scan-churn) + m07 fichero tras flush (anti-huérfano) + agent_11 gate+leak + agent_21 leak. 333 PASS.
- `f3410ffe` — w2w: §2.3/§2.4 cara-cliente — DeclarationHeader medidas por categoría (52/68/73) + readiness "Anexo II" sin nº + SummaryView "hash chain SHA-256" + remediation errores friendly R29. 152 m27 PASS · tsc 0.
- `3ced7538` — w2x: §2.4 — agents SSE leak→internal_error + providers/compliance except:pass→narrow+logger. 169 PASS. (DEFER §2.5 renewal-extensions GET-init · plazos DRY.)

- `4285c3f1` — w2y: §2.1/§2.2/§2.7 — m04 req_all_signed exige status='signed' (+test) + m26 celery sigs (id opcional) + fn_audit_log_verify_chain call-sites (SELECT ok FROM) + Lead CheckConstraint ORM + UI guards (formatDate inválida, div/0 PolicyHeader+firmas-hub, CheckinDetail optional-chain, ClientNotification tz-aware). 544 PASS · alembic check sin diff. (DEFER: m23 NPS · m_live_records creator · DiagnosisRun FK.)

- `03496435` — w2z: §2.8 m02 cutoff + m04 N+1 batch · §3.3 borrado m10 dead script + startup_checks constantes muertas + m14 dead methods · §4.3 docstrings pricing+policy_enforcer. 505 PASS. (DEFER: m27 índice, DiagnosisRun FK, Control orphan intencional. NEEDS-MARCOS: NIF. NO FIX: useCreateLead/lib-mock.)

### 🚀 DEPLOY A PRODUCCIÓN #3/#4/#5/#6 — 2026-06-15 (code-only, sin migración)
- #3 w2v+w2w (`1272663c..f3410ffe`, CD success · health 200).
- #4 w2x (`f3410ffe..3ced7538`, CD success · health 200).
- #5 w2y (`3ced7538..4285c3f1`, CD success · health 200).
- #6 w2z (`4285c3f1..03496435`, CD en curso). Gate: ruff + import + tests por módulo.

- `09a49085` — w3a: §1.5/§2.2 MIGRACIÓN aditiva (audit_2026_06_15_s15_columns_001) — evidence.firma_timestamp (M07 re-verify firma Ed25519 real) + magic_links.otp_expires_at (OTP TTL 15min) + FK diagnosis_runs.project_id. alembic upgrade+check OK · 210+93 PASS. DEPLOY #7 (migración aplicada en prod vía provision · health 200).
- `978218ba` — w3b: §6 puente pentest→remediación — bridge.propose_remediations_from_findings (host findings → RemediationJobs · antes sólo CloudGap) + endpoint llama ambos. 79 PASS. (DEFER §6 agent/Hetzner: allowlist desync, kill-switch tracked_subprocess, MCP Dockerfiles pin. NO FIX: autopilot internal dogfooding.)
- `bc3e9009` — w3c: **FEATURE §3.1** firma_documento REAL (mata el mock de firma legal ENS) — m05 sign_document_external (Ed25519 + hash chain R6 firmante externo sin client_user) + endpoint público POST /api/v1/document-signing/sign (consume magic-link → firma · cubre acta E-012/MAGERIT E-028/DdA E-040/k6/conformidad) + DocumentSigningFlow.tsx + dispatcher + spec actualizado. 5 tests + 41/41 m05 + tsc 0. DEPLOY #9.
- `0dea8d8a` — w3d: §2.2/§4.4 — invariante muerto NEVER_ACTIVE_AND_EXPIRED_TOGETHER retirado (m27) + process_basic_declaration firma JSON canónico (no str(tuple)) + importes fiscales Decimal directo (m15/m23 · no float→imprecisión VeriFactu) + copy SigningFlow "firma Ed25519 + cadena SHA-256". Test report_renderer anual corregido (period_type 'quarterly'→'trimestral'). 334/334 m15+m23+m27 PASS.
- `4d386e01` — w3e: §5 gate de deploy (ruff+compileall · deploy needs:gate) + drift head Alembic (deja de nombrar revisión obsoleta · x3) + borrado scripts legacy (create_rls_policies+rls_policies.sql FOOTGUN BYPASSRLS + rename_sgsi_ids one-shot).
- `3f3c6d7c` — w3f: §6 pentest — race PENTEST_AUTHORIZATION os.environ→ContextVar task-local + kill-switch alcanza subprocess MCP (start_new_session + tracked_subprocess) + Dockerfiles MCP con verificación command -v (build falla sin binario primario · log visible). 348 m08 PASS. DEPLOY #10.
- `4735ed3e` — w3g: §2.5 renewal GET /timeline+/auditor-info read-only (timeline efímero · no crea+commit) + §2.4 fuga str(exc) copiloto (agent_14+m11) → genérico+log + financial except narrow+log + §2.7 VerifyAuthPortal (cooldown reenvío OTP + aria-describedby + quita error crudo). 703 PASS · tsc 0. DEPLOY #11.
- `85a8dfb7` — w3h: §4.5 cap LLM REAL — NEW core/ai/pricing.py + cost_usd poblado en todos los write sites (antes None → cap mensual muerto) + agentes inline cliente con rate-limit (429) + feature_override "inline_cliente_*" + cache poda + §2.8 export truncado logueado. 454 PASS + 5 pricing NEW.
- `ee97de31` — w3i: §2.7 frontend — doble SSE eliminado (useProjectEvents sirve chat/clarificación · 1 conexión) + AuthGuard error 500→AuthErrorCard reintento + WorkflowBlockersPanel feedback error en rojo + oauth-callback genérico. tsc 0. DEPLOY #12.

### 🔬 Verificación adversarial de cierre (workflow 12 agentes) → 15 bugs reales encontrados + corregidos
- `f9dffbe0` — **w3k (3 HIGH)**: [IDOR cross-tenant m20 workspace REAL · cliente A leía/borraba ficheros de B · fix dependency ownership cliente→proyecto en los 23 endpoints] + [cap coste LLM cliente evadido por la vía DOMINANTE (chat /client-portal/copiloto) que se logueaba como etiqueta admin → feature role-aware copilot_cliente_chat + envenenaba el cap admin] + [mapeos ENS erróneos impresos en informe ENAC (op.acc.6 "Acceso local" RD3/2010 · op.exp.5 "Gestión de vulnerabilidades" inexistente) → títulos resueltos desde catálogo RD 311/2022 + op.exp.5→op.exp.4 + ai_classifier mp.s.7 fantasma/mp.s.4 DoS/mp.com.4 corregidos + test de guardia]. DEPLOY #14.
- `f2e2900d` — **w3l (mediums)**: admin_compliance 5/5 COUNT en SAVEPOINT + heurística conformidad por RouteState (no substring · falsos verdes) en ambos gemelos · m08 verify_auth OTP expiry · auth /totp/verify rate-limit+lockout · RLS en fulkro_consent_audit_log + fulkro_erasure_requests (migración fulkro_pii_rls_002) · m13 create_version recalcula IVA+hitos + docx extras dual-schema.
- `a7be335b` — **w3m (fake-completitud + latente)**: EvidenceVault/VulnsTab/IncidentDetail botones que fingían → honestos (disabled/relabel) · m19 trigger latente marcado WARNING (firma DdA autoritativa = m03). DEPLOY #15.

### ⚠️ NEEDS-MARCOS (datos que NO puedo fabricar · pendientes de Marcos)
- **NIF/CIF** en `frontend/app/(legal)/imprint/page.tsx` + `privacy/page.tsx`: hoy "[pendiente · alta autónomo en curso]". El NIF real NO existe aún (registro autónomo en curso). Cuando Marcos lo tenga: añadir `FULKRO_NIF` a `backend/app/fulkro_identity.py` + `frontend/lib/fulkro-identity.ts` y sustituir los 2 placeholders. (§4.4 · riesgo legal LSSI/RGPD hasta entonces.)

### 🚀 DEPLOY A PRODUCCIÓN #2 — 2026-06-15 (oleadas w2n–w2u)
- **Push GitHub**: `main` FF `34331dba..1272663c` (8 commits campaña §1 completa + §2.1, 1 migración `client_messages_rls_failclosed_001`). Push vía PAT MINGW (gotcha: SOLO MINGW directo).
- **Gate pre-deploy**: ruff limpio (ficheros campaña) + `alembic check` "No new upgrade operations" + build_test_db.sh upgrade head sobre BD limpia (254 tablas + seed + corpus) + import app.main (1200 rutas) + tests por módulo verdes (manual_transfer/m31/m29/m05/m12/remediation/mcp/m08/m04/m27/m02/m09/m_workflow/notifications…).
- **CD GitHub Actions** (run 27550304962): **success** → SSH Hetzner → git pull --ff-only + compose build + up -d. La migración aplica vía servicio `provision` (alembic upgrade head idempotente · gate depends_on de los servicios app).
- **Hetzner prod**: `https://app.fulkro.es/api/v1/health` = **200** post-deploy.

### 🚀 DEPLOY A PRODUCCIÓN — 2026-06-15
- **Push GitHub**: `main` FF lineal `78579eff..34331dba` (15 commits campaña, 0 migraciones). Remoto verificado = `34331dba`.
- **CD GitHub Actions** (`deploy.yml`, run 27541643679): **success** → SSH Hetzner → git pull --ff-only + compose build + up -d.
- **Hetzner prod** (`/opt/fulkro`): HEAD = `34331dba` ✓ · contenedores recreados healthy (backend/frontend/celery/postgres) · público `https://app.fulkro.es/api/v1/health` = **200**.
- Gate pre-deploy: ruff limpio (ficheros campaña) + import app.main (1200 rutas) + 166 tests enfocados PASS (acta/SSE/MCP/IDOR) + frontend tsc 0 errores.
- **GOTCHA push**: el `git push` con PAT DEBE hacerse desde **MINGW Bash directo** (`git -C //wsl.localhost/...`). Vía `wsl.exe -- bash -lc '...'` la variable PAT llega VACÍA (quoting bridge) → URL con password vacío → "Invalid username or token". El PAT de Fulkrodev SÍ funciona para la REST API de Actions (contradice memoria previa).

### Pendientes destacados §1 (para cerrar §1 del todo)
- [x] BillingHistory `dangerouslySetInnerHTML` + manual_transfer.render_html_block (FE/BE XSS). **`w2n`**.
- [x] webhook 360dialog HMAC X-Hub-Signature-256 (§1.4). **`w2o`**.
- [x] m11 inline agents con rate-limit + cost_usd poblado (cap mensual real). **`w3h`**.
- [ ] verify_signature except amplio · M07 re-verify firma · secure=False MinIO (revisar prod).
- [ ] §1.4 restantes: `PATCH /dda/entries/{id}` (confirmar require_owner basta) · `corpus.py`/`mcps.py`/`projects.py` sin auth · `_dev/login-as-marcos` doble gate · ZAP `disablekey` dev.
- [ ] §1.5 cripto (Ed25519 fail-fast prod · verify_signature except acotar · M07 re-verify · secure=False MinIO · request_otp endurecer · geo-restriction magic links).
- [ ] §1.6 restantes: `agent_15_vigilancia` `<a href>` feeds externos · inyección sub-comandos MCP · DataFlowTab mermaid.live · NotificationsTab JSON sin schema.

### NOTA verificación m23 reports (§2.1) para la próxima
report_service usa report_type "E-801_quarterly"/"E-802_annual"; las activities usan
frecuencia "trimestral"/"anual". Leer `report_renderer` (render_quarterly_report_docx /
render_annual_report_docx) y ver POR QUÉ sale "informe parcial sin datos": confirmar el
campo real por el que filtra activities (frecuencia vs report_type vs period). NO asumir
swap quarterly→trimestral sin leer el renderer (el report_type ya es *_quarterly inglés).
