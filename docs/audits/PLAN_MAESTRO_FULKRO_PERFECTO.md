# PLAN MAESTRO — FULKRO 100% PERFECTO · Outcome-as-a-Service

> **Objetivo:** dejar FULKRO cerrado, sin gaps, sin dead-code, sin eslabones muertos —
> coronado como el mejor sistema de implantación ENS (RD 311/2022) para los 3 niveles
> (BÁSICA / MEDIA / ALTA) **e incluso a nivel individual/autónomo**, con pentest +
> escaneo de vulnerabilidades **autónomos (LLM + MCP)** que reportan a la auditoría.
> **Fuentes:** `GAP_REPORT_MAESTRO.md` (17 dims + matriz 73×3 + 64 gaps), recorrido por
> 12 flujos E2E (`BUILD_PLAN_MAESTRO.md`, 55 ítems), `OLA_0_PROGRESS.md` (lo ya hecho).
> ENS Radar = FUERA de alcance (vive aparte, dormido). Rama `batch2-fase0-recorrido`.

---

## 0. DÓNDE ESTAMOS (baseline honesto · 2026-06-05)

**Ya cerrado y verificado (OLA 0 núcleo · 13 ítems + 1 deploy-blocker):**
FR-1 (onboarding escribe las 10 dims) · FR-2 (PI-guard en chats persona) · #1 (dossier
auditor token-gated) · #2/#3 (incidentes Art.33 alcanzables + state machine unificada) ·
#4 (upload cliente → MinIO) · #5 (aislamiento cross-tenant m24) · #11 (hitos con fecha) ·
#13/#14 (drift de fase + gate categoría) · #21 (purga corpus sintético) · #15/#16/#17
(dispatcher retainer + beats) · **BEAT-BUG** (9 beats rotos por nombre → 0 dotted paths).

**Veredicto de certificabilidad HOY:**
- **BÁSICA** → certificable (autoevaluación 808 + Declaración Dirección 809). Falta pulir el cierre firmado (FRENTE D).
- **MEDIA** → certificable ENAC; vuln-scan real existe. Falta cerrar ciclo documental + retainer vivo + parón gate.
- **ALTA** → 2 gaps reales: firma cualificada eIDAS (mp.info.3 R4) + TSA real (mp.info.4) + pentest externo (proceso humano). Decisión de scope (DEC ALTA).

**Lo que el sistema YA tiene production-grade** (no hay que construirlo): chat N5, firma
canvas Ed25519, fiscal_identity, audit_log hash-chain R6, RLS fail-closed, ZFP engine +
14 MCP fail-closed + kill-switch, portal auditor (11 vistas), simulacro pre-ENAC, retainer
billing. El trabajo restante es **cablear, pulir y cerrar**, no reconstruir.

---

## 1. DEFINICIÓN DE "PERFECTO / CORONADO" (criterios de cierre)

1. **Premisa #1**: un auditor ENAC, en acta, aprueba la implantación del CLIENTE y el cliente CERTIFICA (en BÁSICA: la autoevaluación 808 + Declaración Dirección resisten que el órgano de contratación pida evidencias).
2. **Outcome-as-a-Service**: el cliente VE / AUTORIZA / FIRMA / RECIBE y hace el mínimo; todo el peso operativo en el admin (Marcos), que orquesta y verifica.
3. **0→100% por nivel** (BÁSICA/MEDIA/ALTA **+ individual**), todo **accionable por frontend**, intuitivo, marca Fulkro (#6C63FF), sin saturación.
4. **0 placeholders · 0 dead-code · 0 eslabones muertos** (cada transición con disparador real + frontend).
5. **Documentos descargables** por cliente y auditor (cadena documental completa).
6. **Pentest + vuln-scan autónomos** (LLM + MCP) que **reportan a la auditoría** (dossier + simulacro pre-ENAC).
7. **Invariantes duros preservados**: 1 proyecto = 1 cliente · RLS fail-closed · R6 hash-chain · ADR-014 read-only OAuth.
8. **Walkthrough E2E** 0→100% por nivel verde (backend verificable + navegador Marcos).

---

## 2. MAPA DE FRENTES — TODO LO QUE QUEDA

Cada frente: objetivo · ítems (ID del build plan) · tamaño · dependencias · criterio "hecho".

### FRENTE A · Cierre de eslabones + FE rápido (OLA 0/1 restante) — **16 ítems S · ~1-2 días**
Lo que queda del set seguro (sin migración, sin decisión). En curso.
- **#6** botón descarga evidencia individual portal auditor (endpoint token-gated ya existe). `EvidenceView.tsx`.
- **#7** botón "Exportar CSV" del audit-log del auditor (endpoint ya existe). `AuditLogView.tsx`.
- **#10** email primer-acceso → renderer m12 `PRIMER_ACCESO_CLIENTE` + paleta violeta (borrar HTML azul `_render_primer_acceso_html`). `m21_portal_cliente/api.py`.
- **#12** entrada sidebar cliente "Mi certificación" (página huérfana `/client-portal/certificacion`). `ClientSidebar.tsx`.
- **#18** entrada `/chat` "Chat cliente" en `ProjectTabs` (página existe, huérfana en nav). 
- **#19** landing portal auditor: quitar copy "fase 5 del despliegue" (señal de obra ante ENAC). 
- **#20** `layout.tsx` passthrough portal auditor (mata doble header/triple footer). 
- **#22** README m08: corregir "orquestador implementado" (es STUB) + borrar SSH/LUCIA inexistente. 
- **#23** sidebar admin: quitar counts hardcodeados (Archivables=3/Archivados=12); `filterRetainer` real. 
- **#24** icono distinto "Mejoras propuestas" (Wrench) ≠ "Cumplimiento" (ShieldCheck) en `ClientSidebar`. 
- **#25** parametrizar `VERIFACTU_QR_BASE_URL` (pre-prod AEAT → prod `www2.aeat.es`). `billing_service.py` + `config.py`. 
- **#26** `marcos_whatsapp_number` editable desde admin settings (hoy solo env). 
- **#27** hub `/client-portal/settings` (N8 cliente) + entrada sidebar. 
- **#28** fusionar los 2 forms de notificaciones cliente en uno (dep #27). 
- **#29** endpoint `/retainer/active-client-ids` + bucket "En retainer" real en sidebar. 
- **#30** entrada catálogo `CCN-STIC-809` (corpus · pending_manual critical). 
**Done:** cada FE accionable, sin huérfanos en nav, sin counts falsos, email violeta, sin copy de obra.

### FRENTE B · Ciclo documental completo (OLA 2) — **4 ítems M · ~2-3 días · dep FRENTE A**
Cierra "el cliente Y el auditor descargan TODO".
- **#31 (G4)** M06 docs → ingest IDMS post-generación (`storage_path=minio://`). Hoy docs M06 con path local → 503.
- **#33 (F11-04)** bundlar binarios reales (PDF/DOCX) al dossier ZIP cuando `sign_manifest=True` (hoy solo JSON metadata) — **dep DEC-4 (tope tamaño)**.
- **#32 (G2)** endpoint admin IDMS `/documents/{id}/download` + botón (gestor admin sin descarga).
- **#34 (F1-002)** preview/descarga del DOCX del contrato in-page antes de firmar (hoy se firma sin ver el texto; el doc va por email).
**Done:** test round-trip MinIO + ZIP con binarios reales (no `.json`) + preview firma.

### FRENTE C · Retainer vivo + incidentes mantenimiento (OLA 3) — **5 ítems M/L · dep OLA 0/1**
El mantenimiento ENS post-cert que vigila que se sigue cumpliendo.
- **#35** beat reloj deadline 24/72h notificación LUCIA Art.33 (dep #2 incidentes).
- **#36 (F9-G3)** reaprobación anual firmada por Dirección: SignableType + endpoint approve + audit_log (dep #15).
- **#37 (F9-G5)** `generate_annual_reports` E-802 real + beat (patrón quarterly).
- **#55 (F9-G6)** `open_recategorization` real (M01 + DdA v2 + audit) — hoy stub 23 LOC.
- audit_log en `annual_review` + dashboard retainer adaptativo por nivel (anuales/bienales del manual + 817).
**Done:** el retainer ejecuta el ciclo solo, adaptado al nivel; reaprobación firmada; recat real.

### FRENTE D · Parón pre-auditoría como GATE + cierre BÁSICA firmado (OLA 4) — **5 ítems M · encadenada**
Aquí se materializa la Premisa #1 ("que el auditor lo apruebe ANTES de la ENAC").
- **#40** GATE-7 `require_clean_audit_sim`: bloquea solicitud ENAC / firma con NC mayores abiertas (con escape-hatch admin).
- **#41** plantilla E-808C cierre BÁSICA + `self_assessment_report_id` NOT NULL (dep #40).
- **#44** SignableType `DECLARACION_CONFORMIDAD_BASICA` + SigningIntent firmado por **Dirección** (no RSeg) (dep #41).
- **#42** expandir payload del simulacro (no hardcodear 0; leer del JSONB real).
- **#43** exigir run de simulacro completado antes de marcar `internal_audit_completed` (dep #40).
**Done:** no se solicita ENAC ni se firma conformidad con NC mayores; BÁSICA cierra con Declaración firmada por Dirección descargable.

### FRENTE E · Copilotos "winning" (OLA 5) — **4 ítems M**
Conocimiento íntegro + proactivo + memoria + anti-alucinación.
- **#45 (N6) · memoria compartida ENTRE CONVERSACIONES, por proyecto, en AMBOS copilotos** (decisión Marcos reiterada): el copiloto **admin** recuerda todo el proyecto entre conversaciones (aislado por `project_id`) y el copiloto **cliente** igual para el suyo (aislado por `client_id`+`project_id` · RLS). Reusa `history` en CopilotQuery + `get_recent_messages` + persistencia de hilos. Cada copiloto retoma donde lo dejó, por proyecto.
- **#46** ingest de las 73 medidas ENS como chunks consultables (`measure_code`) — hoy viven en YAML, no en el RAG (dep #30 corpus 809).
- **#47** clasificador de categoría en filtros + calibrar umbral corpus_gap 0.45→0.60 con flag (frena alucinación de tema adyacente — riesgo Premisa #1: confundir refuerzos por nivel).
- **🔨 N2 (auto-actualización)**: el conocimiento del copiloto se actualiza cada vez que se añade algo al sistema (hook de ingest incremental cuando se crea plantilla/medida/doc). Diseño: trigger post-commit → re-embed + upsert chunk. **(Nuevo, M/L.)**
- **🔨 GUÍA "A PRUEBA DE MONOS" · proactiva + cronológica (decisión Marcos):** ambos copilotos guían **paso a paso, ordenados cronológicamente, explicándolo TODO al máximo**, diciendo exactamente qué hacer en cada paso — de modo que **alguien sin conocimiento de ENS pueda implantarlo a la perfección**. **ADMIN**: las tareas de implantación de Marcos (R30 tutor · asume cero ENS · primer principios · nivel-botón), **adaptadas al cliente + su nivel ENS + sus dimensiones**. **CLIENTE**: sus tareas (aprobar/conectar/rellenar/firmar · R29 amable). Ambos **PROACTIVOS** (se adelantan y ordenan qué/cómo/cuándo, como un jefe — no solo responden). Reusa `compute_workflow_state` (catálogo de acción por fase) + nudges cron, ahora con **copy paso-a-paso exhaustivo por fase × nivel × dimensiones del cliente**. **(M/L · es el "winning" del copiloto.)**
**Done:** un usuario **sin conocimiento de ENS** completa la implantación de su nivel guiado paso a paso por el copiloto (admin→Marcos, cliente→cliente); cita fuente, no inventa, recuerda el proyecto, es proactivo, y su corpus se mantiene solo.

### FRENTE F · 🔨 PENTEST AUTÓNOMO + VULN-SCAN + REPORTE A AUDITORÍA (LLM + MCP) — **EL GRAN FRENTE · L/XL**
El sistema audita/pentestea solo los sistemas conectados, detecta CVEs al máximo, propone
remediaciones bajo aprobación del cliente, y **mete el resultado en el dossier del auditor**.

> **📐 ARQUITECTURA AUTORITATIVA: `docs/spec/M8_PENTEST_PIPELINE_ENS_ALTO_v2.md`** — integra
> el documento M8 v2.0 de Marcos (7 principios de diseño · capas 0-6 · modelo de datos
> canónico **Finding (hecho) / Verdict (advisory) / EvidenceRecord (append-only pgAudit)** ·
> pipeline de **5 gates** · máquina de estados del hallazgo · **modelo de amenazas del agente
> + anti-injection INDIRECTA desde el objetivo** · SLA por severidad CVSS+EPSS · aceptación de
> riesgo con caducidad · determinismo demostrable (run-manifest + golden runs) · fail-closed ·
> **2 gates humanos** (RoE + atestación OSCP en Alto) · mapeo ENAC) **mapeado al m08 REAL** con
> **14 pasos de construcción F1-F14**. El backbone YA existe (ZFP 5-gates, kill-switch, scope/
> RoE, MCP executor, llm_classifier, remediation/retest, ens_mapper, modelos). Falta: **F1
> cablear el orquestador** (keystone · `task_execute_run` STUB) + capa de rigor (SARIF, EPSS,
> grafo AGE, run-manifest/golden-runs, EvidenceRecord pgAudit, anti-injection del agente,
> recon/SAST/SCA completos, atestación Gate-2). Regla dura: el LLM **sugiere**, nunca degrada
> un finding determinista (defensa anti-injection). "Perfecto" = **cobertura demostrable +
> evidencia reproducible + cierre verificado**, no "cero vulns".
- **#38 (F5-02 · N1)** **ensamblar el orquestador interno**: `task_execute_run` (hoy STUB) → encadena runners (nuclei/openvas/trivy + recon) → ZFP engine (5 gates, fail-closed) → persiste `VerificationFinding`. Cablear los callers de `run_zfp_pipeline` / `run_vuln_audit` / `run_cloud_audit` (hoy 0 callers de producción). **"Reporte a un botón."**
- **#39 (F5-03 · N7)** **registro de vulnerabilidades automatizado** poblado desde el scan interno (subproducto de #38).
- **#48 (F5-05)** catálogo MCP **ofensivo para ALTA** (recon / infra / SAST) con gate de categoría.
- **LLM experto + grounded + determinista**: el LLM decide por dónde atacar y razona, pero anclado en la base de conocimiento del pentest + del sistema (anti-alucinación, temperatura ≤0.2), nunca "cosas raras". Reusa A11/A19.
- **Remediaciones bajo aprobación del cliente**, curadas para que no fallen (reusar el remediation_orchestrator + ADR-014 read-only por defecto; auto-execute solo con aprobación explícita).
- **Semillas / sistema de prueba**: entorno semilla con vulnerabilidades conocidas para validar que el pipeline las detecta; pulir hasta verde.
- **Reporte → auditoría**: el informe de pentest/vuln-scan entra en el **dossier del auditor** (FRENTE B) y alimenta el **simulacro pre-ENAC** (FRENTE D) como evidencia de mp.s.2 (vuln-scan MEDIA / pentest).
- **Encaje compliance (decisión-consultor, ya en el plan)**: vuln-scan **obligatorio MEDIA** (Fulkro lo cubre) · pentest **opcional MEDIA** · en **ALTA el pentest debe ser de un tercero EXTERNO independiente** → el motor de Fulkro **complementa** (continuo / pre-auditoría / endurecimiento), **no sustituye** al externo en ALTA. Esto se declara explícito en el dossier.
- **PARO-ESPECIAL PE-3**: la ejecución REAL de binarios MCP + persistencia de findings se activa **deploy-time en Hetzner** con `USE_MCP_REAL=True` (los defaults `False` de hoy son prod-safe, no bugs → DEC-6). El cableado del caller es construible ya; la ejecución real es de despliegue.
**Done:** un botón "Escanear/Pentestear" sobre los sistemas conectados → findings reales → remediaciones aprobables por el cliente → informe firmado en el dossier; semillas detectadas al 100%.

### FRENTE G · Frontend íntegro + UX/marca pulido total (OLA 7) — **2 ítems L + barrido**
La sensación "serie/innovación", no "de salida".
- **#51 (F8-G1)** migrar **596 usos de colores crudos** (blue/emerald) → tokens Fulkro en ~8 componentes cliente; contraste correcto (fondo claro→texto oscuro); fuentes/labels/botones grandes; sin saturación; todo ordenado.
- **#52 (F8-G7)** `ConformityWizard isCompleted` real (queries tanstack existentes).
- **Barrido de cobertura fase-a-fase** por nivel y portal (admin/cliente/auditor): mapear rutas/componentes contra las 8 fases del manual; **listar y construir las pantallas que falten** por nivel. (Auditoría FE dedicada · M.)
- **Pasada de UX una-a-una** de las peores pantallas (reportadas en el gap report).
- **🔨 NADA TRANSPARENTE · TODO ORDENADO (decisión Marcos):** fondos **sólidos** (no translúcidos que pierden contraste), **márgenes/padding bien puestos**, nada cortado ni desbordado, sin sobresaturar las páginas, super estético y fácil de acceder. Aplica a admin y cliente.
- **🔨 ACCESO TOTAL DESDE EL MAIN DASHBOARD (decisión Marcos · "sea como sea"):** **TODO** accesible desde el dashboard principal del cliente y del admin respectivamente — sidebar nav completo **+ quick-links/cards** de acceso en el propio dashboard a cada feature/fase. **Cero páginas huérfanas o inalcanzables.** (Cruza con FRENTE A: #12 "Mi certificación", #18 chat, #27 ajustes, #29 retainer — todos enlazados desde dashboard/nav.)
**Done:** cobertura FE 100% por fase/nivel/portal + design system aplicado + **fondos sólidos + márgenes correctos + nada cortado** + **0 features inalcanzables desde el main dashboard** + 0 pantallas "de salida".

### FRENTE H · Legal / fiscal / RGPD (D15) — **3 ítems M**
- **#35** reloj 24/72h LUCIA (ya en FRENTE C) + endpoint create_incident (ya hecho en #2; falta el reloj).
- **#54 (F12-BREACH-AEPD)** `notify_aepd` → preparar payload sede + email interno Marcos + `pending_sede_submission` (dep **DEC-5**).
- **Verifactu real AEAT** (remisión real, no solo registro+QR pre-producción) — **decisión-producción** (hoy preproducción correcta para pre-piloto).
- RGPD conexiones cloud: políticas de privacidad/consentimiento/seguridad de la conexión (read-only OAuth ADR-014) — verificar/cerrar.
**Done:** notificación de incidentes con reloj legal; canal AEPD correcto; Verifactu prod al desplegar.

### FRENTE I · Chat / notificaciones / ajustes consolidado (D12/N5/N8) — **decisión + migración**
- **#27/#28** hub Ajustes cliente + fusión forms notif (ya en FRENTE A).
- **#26** WhatsApp admin editable (ya en FRENTE A).
- **DEC-2 + PE-2**: consolidar los **3 sistemas de mensajería paralelos** (m21 + m29 + m31) en m21 como canal único, fusionando adjuntos+búsqueda de m29 (tabla `chat_message_attachments` + migración). **Requiere tu OK** (migración = PARO-ESPECIAL).
- N8 admin: pestaña de Ajustes por portal y por proyecto (proponer qué va ahí una vez auditado).
**Done:** un solo sistema de chat, notificaciones bilaterales fluidas, ajustes por portal/proyecto.

### FRENTE J · Compliance dogfooding cerrado (D8) — **2 ítems S**
- **#49** `_emit_monitor_audit` en `run_norma_report` + `mark_reviewed` (2 acciones sin audit_log).
- **#50** audit_log en los beats `_run_batch` (helper a módulo compartido).
- M03/M09 propios "Próximamente" → contenido real (o DEC-1 N4).
**Done:** Fulkro se autocertifica ENS Medio (dogfooding) con trazabilidad R6 completa.

### FRENTE K · Producción FASE J (Hetzner) + DB-DRIFT — **XL · despliegue**
- Deploy Hetzner + Docker + Caddy + Postgres/Redis/MinIO + Celery **beat/worker reales** (validar los beats arreglados hoy con un arranque real).
- ENV producción: `FULKRO_AUTH_*`/`ML_*` keys persistentes, `USE_MCP_REAL`/`cloud_mock` (DEC-6), `VERIFACTU_QR_BASE_URL` prod, `ENABLED_SOURCES`.
- **DB-DRIFT-01** (de Ejecutable 8 Pasada 16): la BD live está stampeada con revisiones aplicadas por DDL directo; alinear con el árbol Alembic (criterio: `upgrade head` sobre BD vacía = 248 tablas / 3645 cols + `alembic check` sin diff; **PROHIBIDO stamp**). Migración real que capture el DDL del radar_widen.
- **Re-seed catálogo** `ens_measures` en la BD del piloto (las correcciones de aplicabilidad solo aterrizan en seed fresco; verificar `SELECT codigo,aplica_* FROM ens_measures`).
- Storage cutover MinIO → Hetzner (uploads cliente #4 + binarios dossier).
**Done:** sistema corriendo en Hetzner, beats reales verdes, BD alineada, seed correcto.

### FRENTE L · Nivel "INDIVIDUAL / autónomo" para los **3 NIVELES** (decisión Marcos) — **M/L · producto**
"El mejor sistema ENS para todos los niveles **hasta individualmente**" — y el perfil individual cubre **BÁSICA, MEDIA y ALTA**, no solo BÁSICA.
- Perfil de **autónomo / microempresa** como **dimensión de cliente** (NO categoría ENS nueva): alcance mínimo guiado, marco documental ligero, copiloto que asume cero ENS y lleva de la mano paso a paso — pero soportando los **3 niveles**.
- Por nivel: **BÁSICA** → autoevaluación 808 + Declaración Dirección 809; **MEDIA/ALTA** → cierre ENAC (con su firma/TSA/pentest según nivel). Pricing individual por nivel.
- Reusa todo (categorización, SoA por nivel, plantillas, distintivo Pantone 021C) recortado al caso individual.
- **Spec detallada:** la genera el workflow de diseño `fulkro-new-directives-design` (FRENTE L expandido).
**Done:** un autónomo puede llegar a su conformidad en **cualquiera de los 3 niveles** con guía del copiloto + mínimo input; verificado por Playwright (FRENTE M).

### FRENTE M · 🔨 Playwright E2E que SIMULA los 3 niveles hasta perfecto (GATE DE ACEPTACIÓN) — **L · test**
Decisión Marcos: todo debe funcionar a la perfección y **probarse con Playwright** simulando los workflows completos de **ENS BÁSICO, MEDIO y ALTO** hasta que los 3 pasen perfectos.
- 3 specs maestras (o parametrizadas) que recorren las **8 fases** (arranque → categorización → riesgos → SoA → marco documental → implantación → evidencias → cierre) por nivel, con los 3 actores (admin orquesta · cliente aprueba/conecta/firma · auditor revisa).
- Assertions por fase y por nivel: medidas aplicables correctas, cierre correcto (BÁSICA autodeclaración vs MEDIA/ALTA ENAC), descargas, firma, dossier.
- Fixtures/seed por nivel; reusa el patrón E2E existente (fase_N + helpers/auth-real + globalSetup test-client).
- **Spec detallada:** la genera el workflow de diseño (FRENTE M).
**Done:** `npm run test:e2e` simula BÁSICA + MEDIA + ALTA end-to-end y **los 3 pasan verdes** — gate de "coronación".

---

## 3. DECISIONES QUE NECESITO DE TI (gatean frentes)

| ID | Decisión | Impacto |
|----|----------|---------|
| **DEC-ALTA** ✅ **RESUELTO** | **SÍ — los 3 niveles entran completos** (Marcos 2026-06-05) | Se abordan firma cualificada eIDAS (mp.info.3 R4) + TSA real (mp.info.4) + catálogo MCP ofensivo ALTA. BÁSICA + MEDIA + ALTA + **perfil individual para los 3** — todos perfectos y probados con Playwright (FRENTE M). |
| **DEC-1** | N4 gestor documental propio Fulkro | Reusar IDMS "Fulkro-Self" (1-2h) vs gestor dedicado. |
| **DEC-2** | Consolidar mensajería m21+m29+m31 (→ PE-2 migración) | Un solo chat. |
| **DEC-3** | OTP step-up en reaprobación anual firmada por Dirección | Trazabilidad reforzada. |
| **DEC-4** | Tope tamaño dossier ZIP (~500MB) + fallback binario ausente | Entrega ENAC. |
| **DEC-5** | Canal AEPD Art.33 (sede FNMT + alerta interna) | RGPD breaches propias. |
| **DEC-6** | `USE_MCP_REAL`/`cloud_mock` solo deploy-time Hetzner | Confirma que los defaults False de hoy son correctos (no bugs). |

## 4. PARO-ESPECIAL (migración / DB-live · requieren OK explícito)

| ID | Qué | Alternativa |
|----|-----|-------------|
| **PE-1** | `norma_key` lowercase sobre filas live (dogfooding) | Hacerlo en el **FE filter** (lowercase ambos lados) como DO-NOW, sin tocar DB. |
| **PE-2** | Fusión m29→m21: tabla `chat_message_attachments` + migración datos | Dep DEC-2. |
| **PE-3** | Ejecución real binarios MCP + persistir findings | Deploy-time Hetzner (DEC-6). El caller es construible ya. |
| **DB-DRIFT** | Alinear BD live con árbol Alembic (FRENTE K) | Migración real, nunca stamp. |

---

## 5. ESFUERZO TOTAL + ORDEN RECOMENDADO

**Conteo de lo que queda** (post OLA 0 núcleo): ~16 ítems S (FRENTE A) + ~25 ítems M/L
(FRENTES B-J) + 6 decisiones + 4 PARO-ESPECIAL + producción (K) + individual (L).

**Estimación honesta** (rangos; OPS-045: el audit-first suele reducir 50-90% porque la
infra ya existe): FRENTE A ~1-2 días · B ~2-3 d · C ~2-3 d · D ~2-3 d · E ~3-4 d ·
**F (pentest) ~5-8 d** (el grande) · G ~3-5 d · H ~1-2 d · I ~2-3 d (+migración) · J ~0.5 d ·
K (producción) ~3-5 d · L ~2-3 d. **Total ≈ 4-6 semanas de construcción efectiva** según
decisiones (sin ALTA reduce; con ALTA + individual completos es el extremo alto).

**Orden recomendado (cada frente: audit-first → construir → verificar):**
1. **FRENTE A** (cierre eslabones + FE rápido) — desbloquea Premisa #1, todo S. *(en curso)*
2. **FRENTE B** (ciclo documental) — que cliente y auditor descarguen TODO.
3. **FRENTE D** (parón GATE + cierre BÁSICA firmado) — la Premisa #1 fuerte.
4. **FRENTE C** (retainer vivo) — mantenimiento ENS automático.
5. **FRENTE E** (copilotos winning) — el "jefe" que guía fase-a-fase.
6. **FRENTE F** (pentest autónomo LLM+MCP) — el gran diferenciador.
7. **FRENTE G** (FE/UX total) — la corona estética.
8. **FRENTE H, I, J** (legal, chat consolidado, dogfooding) — en paralelo donde no haya dep.
9. **FRENTE L** (individual) — el nivel extra.
10. **FRENTE K** (Hetzner) — producción final + DB-DRIFT + re-seed + storage cutover.

---

## 6. DEFINICIÓN DE "DONE" FINAL (la coronación)

- [ ] Walkthrough E2E 0→100% **verde por nivel** (BÁSICA + MEDIA + ALTA + individual): backend verificable (pytest/ASGI) + demostración navegador (Marcos).
- [ ] **0 placeholders / 0 dead-code / 0 eslabones muertos** (grep + lectura).
- [ ] Cliente **descarga** toda su documentación; auditor **descarga** el dossier con binarios.
- [ ] **Pentest + vuln-scan autónomos** producen informe que **entra en el dossier** y el simulacro pre-ENAC; semillas detectadas 100%; remediaciones aprobables por el cliente.
- [ ] **Parón GATE** impide solicitar ENAC / firmar con NC mayores; BÁSICA cierra con Declaración firmada por Dirección.
- [ ] **Retainer** ejecuta el ciclo de mantenimiento solo, adaptado al nivel.
- [ ] **Copilotos** guían fase-a-fase, citan fuente, recuerdan el proyecto, corpus auto-actualizado.
- [ ] **FE** íntegro, intuitivo, marca Fulkro, sin pantallas "de salida".
- [ ] Invariantes: 1=1 · RLS fail-closed · R6 hash-chain · ADR-014 read-only — intactos.
- [ ] **Producción Hetzner** corriendo: beats reales verdes, BD alineada (Alembic check sin diff), seed correcto, Verifactu prod.
- [ ] **Un auditor ENAC aprobaría** la implantación de un cliente real (Premisa #1).

> Cuando todas esas casillas estén marcadas, FULKRO está coronado.

---

## ACTUALIZACIÓN 2026-06-06 · Directivas Marcos (refuerzo de frentes E · F · G · M)

> Marcos refuerza explícitamente, además de DEC-ALTA=SÍ (3 niveles + individual). Estas líneas son **vinculantes** y se suman a las specs del ANEXO siguiente.

**FRENTE E (copilotos) — refuerzo "monkey-proof + proactivo + memoria por proyecto":**
- El copiloto **ADMIN** debe **guiar a Marcos paso a paso, cronológicamente, como si no supiera nada** ("hasta un mono sin conocimiento implanta el ENS"): en cada paso dice exactamente *qué hacer ahora*, **adaptado al cliente, su nivel ENS (BÁSICA/MEDIA/ALTA) y sus dimensiones/datos**. Explicación al máximo, ordenada por fase del ciclo.
- El copiloto **CLIENTE** hace lo mismo para **las tareas del cliente** (qué le toca: conectar, aprobar, firmar, subir evidencia), guía cronológica y al máximo de claridad, adaptada a su nivel.
- **Ambos PROACTIVOS**: orientan sin que se les pregunte (next-step nudge contextual a la fase/estado real).
- **Memoria compartida entre conversaciones**: el copiloto admin recuerda **por proyecto**; el copiloto cliente recuerda **por cliente/proyecto**. (N6 + persistencia de historia.)
- Base de conocimiento **auto-actualizable** (N2) cuando cambia el sistema/portales (ver ANEXO FRENTE E).

**FRENTE F (pentest) — spec canónica = documento M8 v2.0:**
- Construir según **[`M8_PENTEST_PIPELINE_REFERENCE_v2.md`](M8_PENTEST_PIPELINE_REFERENCE_v2.md)** (arquitectura de referencia v2.0 aportada por Marcos): zero standing access + conector efímero, 6 capas, modelo de datos `Finding`/`Verdict`/`EvidenceRecord`, 5 gates de verificación, máquina de estados del hallazgo, **defensa anti prompt-injection del agente**, 2 gates humanos (autorización + atestación OSCP solo Alto), determinismo por `run_manifest_hash` + golden runs, fail-closed transversal, SLA por severidad (CVSS+EPSS), aceptación de riesgo con caducidad, cobertura % como métrica de honestidad. Sobre `m08_verification` existente (audit-first §20 del doc).

**FRENTE G (frontend) — refuerzo estético + acceso:**
- **Nada translúcido/transparente**: cards y superficies **sólidas** (sin pérdida de contraste). Márgenes correctos, **nada cortado**, sin sobresaturar páginas, súper estético, todo ordenado y fácil de acceder.
- **TODO accesible desde el main dashboard** del cliente y del admin respectivamente (la forma la decide el constructor: tiles/quick-actions/nav). Cero pantallas huérfanas sin ruta desde el dashboard.

**FRENTE M (Playwright) — gate de aceptación final:**
- Simular **BÁSICA + MEDIA + ALTA** end-to-end (8 fases) **hasta que los 3 pasen perfectos**. Es el criterio "DONE" verde por nivel (incluye perfil individual).

---


## ANEXO — FRENTES NUEVOS E · L · M · J (synth arquitecto · 2026-06-05)

> Consolida 4 specs de frentes nuevos sobre la rama `batch2-fase0-recorrido` (worktree `fulkro-portales`). Estado real verificado con `grep -n`/`ls` sobre el árbol (file:line citados abajo). Reusa infraestructura existente; respeta 1=1 (categoria_objetivo única), RLS, R6 (hash chain audit_log), ADR-014 (read-only OAuth · cliente no opera técnico). **2 correcciones de briefing aplicadas tras auditoría empírica — ver notas ⚠.**

---

### FRENTE E · Copilotos con conocimiento íntegro + auto-actualizable

**Premisa**: el copiloto admin conoce TODO el sistema admin real y el copiloto cliente TODO el portal cliente real; la base de plataforma se auto-regenera en build/import-time desde las fuentes canónicas del código, con test de coherencia que bloquea PR si diverge.

**Estado real (verificado)**
- `backend/app/agents/system_knowledge.py:28,65` — constantes ESTÁTICAS `SYSTEM_KNOWLEDGE_CLIENTE`/`SYSTEM_KNOWLEDGE_ADMIN` (mantenimiento manual, comentario explícito).
- `system_knowledge_generator.py` **NO existe** (verificado `ls` → No such file). Cero generadores en repo.
- `docs/SYSTEM_KNOWLEDGE_BASE.md` existe (fuente-única manual §6 sin script).
- Inyección viva: `agents/agent_14_copiloto/prompts.py` + `copilot_admin_service.py:255` + `copilot_cliente_service.py:194`. Capa ON-QUERY real `copilot_persona_service.py:108-203` (no tocar).
- Fuentes canónicas parseables: `ClientSidebar.tsx:78` (`CLIENT_NAV_SECTIONS`), `Sidebar.tsx:45` (`TOP_NAV`), `core/workflow_phase.py` (`WorkflowPhase.ordered()`), `agents/registry.py`, `fulkro_identity.py`.
- **CCN-STIC 809 AUSENTE del corpus** (verificado: `grep "809" catalog.py` → 0 hits) → cierre BÁSICA bloqueado por corpus_gap fallback.

**Pasos construibles**
| # | Acción | Ficheros | Esfuerzo |
|---|--------|----------|----------|
| E1 | BUILD generador puro `generate_system_knowledge()` (regex TSX nav + `WorkflowPhase.ordered()` + `fulkro_identity` + `AGENT_REGISTRY` + glob `motors/*/service.py` con `ast.get_docstring`). Sin BD/HTTP. `@lru_cache(maxsize=1)` | `backend/app/agents/system_knowledge_generator.py` (NEW) | M |
| E2 | MODIFY: constantes se producen llamando al generador en import-time, con try/except → fallback texto hardcoded + `logger.warning`. Backward-compat 100% (cero cambios en callers) | `system_knowledge.py` | S |
| E3 | BUILD test coherencia sin BD: labels nav cliente/admin presentes, todas las fases, `FULKRO_PHONE`. Falla si diverge | `backend/tests/agents/test_system_knowledge_coherence.py` (NEW) | S |
| E4 | MODIFY: bloque admin del generador (motores activos por glob+docstring, agentes activos por registry, tareas Marcos desde `copilot_personas_v1.yaml`) | `system_knowledge_generator.py` | M |
| E5 | BUILD: entrada CCN-STIC 809 `pending_manual` + script ingest reusando pipeline `ccn_pdf_ingest.py`. PDF lo descarga Marcos (ToS) | `corpus/catalog.py`, `backend/scripts/ingest_ccn_809.py` (NEW) | M |
| E6 | MODIFY doc §6: estructura ahora automática; solo copy ⚠REVISIÓN CONSULTOR manual | `docs/SYSTEM_KNOWLEDGE_BASE.md` | S |

**Dependencias**: stdlib (`pathlib`/`ast`/`re`, Py3.12). Formato estable array TS en sidebars. Capa on-query NO se toca. 809 PDF = descarga manual Marcos.
**Riesgos**: parser TSX frágil → mitigado por try/except E2 + test E3 caza divergencia en CI. Glob motores puede captar módulos parciales → filtrar por `__init__.py`, dir-name fallback. 809 bloqueado por CCN-CERT → corpus_gap ya correcto. Coste startup despreciable (lru_cache). **No duplicar capa on-query** (portfolio/estado vivo).
**Hecho**: (a) `pytest test_system_knowledge_coherence.py` PASS sin BD; (b) añadir entrada ficticia a `CLIENT_NAV_SECTIONS` → test FALLA, revertir → PASS (prueba lectura del fichero real); (c) `grep "CCN-STIC-809" catalog.py` ≥1 hit; (d) imports de los 3 callers siguen funcionando sin tocarlos.

---

### FRENTE L · Perfil INDIVIDUAL/autónomo · BÁSICA · MEDIA · ALTA

**Premisa**: `perfil_autonomo` como dimensión ORTOGONAL a la categoría ENS (NO nueva categoría · respeta 1=1 sobre `categoria_objetivo`). Empresa 1-3 personas que licita AAPP: BÁSICA autodeclaración 808+809 sin ENAC · MEDIA MAGERIT liviano+ENAC · ALTA marco completo+ENAC. Copiloto asume cero ENS (R30).

**Estado real (verificado)**
- `models/core.py:71` `categoria_objetivo` (columna central, nunca duplicar) · `core.py:123` `tamano_empleados`.
- `effort_estimator.py:85-86` `SIZE_FACTOR["micro"]=0.7` + `classify_size_by_employees` → recorte -30% YA existe.
- `m_audit_accompaniment/state_machine.py:8-9` branch BÁSICA→7 estados autodeclaración / MEDIA-ALTA→11 estados ENAC YA modelado.
- DdA `_measure_applies()` per-nivel + WBS gateado por nivel YA existen.
- `pricing/rules.py:35` `BASE_PRICES_CANONICAL` (BÁSICA 3.900 / MEDIA 11.500 / ALTA canonical) presente → base del descuento.
- **⚠ CORRECCIÓN BRIEFING**: la spec afirmó `archetype_workflow_adjustments` "función orphan, cero consumidores". **FALSO**: se consume en `m01_categorization/archetype_api.py:97` y `:129` (verificado). PASO L2 NO "rescata un orphan": debe **cablearla al `m_workflow_engine`** (hoy solo el archetype_api la usa para *display*, no afecta el workflow real).
- **GAP confirmado**: `PymeArquetipo` (`pyme_archetypes.py:46`) NO tiene `AUTONOMO`. Cero campos `perfil_empresa`/`is_autonomo`/`company_type` en ORM (verificado 0 hits). Dimensión unipersonal no existe como primera clase.

**Pasos construibles**
| # | Acción | Ficheros | Esfuerzo |
|---|--------|----------|----------|
| L1 | MODIFY: campo `perfil_empresa` nullable additive en Project + migration + wizard backend | `models/core.py`, `migrations/.../perfil_empresa_autonomo_001.py` (NEW), `admin_diagnostico_wizard.py` | S |
| L2 | MODIFY: `PymeArquetipo.AUTONOMO` + **cablear `archetype_workflow_adjustments` al `m_workflow_engine.engine.py`** (apply_archetype_variant) — corrección scope | `pyme_archetypes.py`, `m_workflow_engine/engine.py` | S |
| L3 | MODIFY: flag `scope_reducido` per archetype autónomo en m05 obligations (marcar `simplificado=variante_ligera`, NUNCA excluir medidas) | `m05_obligations/instantiation_service.py`, `instantiation_types.py` | M |
| L4 | BUILD: plantilla onboarding autónomo + bifurcación catalog_loader por `perfil_empresa` | `m16_onboarding/templates/onb-generico-autonomo-v1.json` (NEW), `catalog_loader.py` | M |
| L5 | MODIFY: `PERFIL_AUTONOMO_DISCOUNT` 15% sobre `BASE_PRICES_CANONICAL` + `calculate_for_autonomo()` + flag trazabilidad `perfil_autonomo_discount_applied` | `pricing/rules.py`, `calculator.py` | S |
| L6 | MODIFY: persona copiloto autónomo + prompt Art.11 RD 311/2022 (acumulación roles) | `copilot_personas_loader.py`, `prompts/agent_14_copiloto.py` | S |
| L7 | MODIFY: campo `perfil_empresa` wizard Step 2 + tooltip Art.11 | `admin/projects/new/page.tsx`, `wizard/StepContextoENS.tsx` | S |
| L8 | MODIFY: `AdaptationBadge` 'Perfil Autónomo' (dim nueva, no duplicar) + badge BÁSICA-autodeclaración portal cliente | `AdaptationBadge.tsx`, `client-portal/dashboard/page.tsx` | S |
| L9 | BUILD: tests transversales (archetype, pricing autónomo, planning micro ≤0.7×, DdA BÁSICA 38-48, state machine BÁSICA autodecl) | 4 ficheros `tests/...` (NEW) | M |

**Dependencias**: Alembic multi-head (ejecutable-8-db-drift) → L1 nullable additive, aplicar tras widen o rama separada (DDL directo + stamp patrón OPS-052). Pricing sobre `BASE_PRICES_CANONICAL` explícito. AdaptationBadge: nuevo slot, no duplicar 28 dims.
**Riesgos**: **NORMATIVO Art.11 RD 311/2022** — acumulación roles permitida pero MEDIA/ALTA el auditor ENAC puede cuestionar independencia funcional → copiloto lo presenta como "permitido con declaración explícita de conflicto gestionado", NUNCA simplificación sin más. **DdA BÁSICA**: op.pl.2 / mp.org.2 simplificables NO eliminables (excluir invalida autodeclaración 808). Descuento NO recalcula propuestas enviadas (flag). Bifurcación onboarding depende de que `perfil_empresa` llegue por `metadata_extra`.
**Hecho**: (a) BÁSICA autónomo E2E backend: create-project perfil=autonomo+cat=BASICA → archetype=autonomo → DdA 38-48 aplicables → state machine BÁSICO termina en `declaration_signed` sin ENAC; (b) MEDIA: plan WBS `client_size=micro` horas_consultor ≤77h (0.7×110); (c) `calculate_for_autonomo('ALTA')` < 22.000 con breakdown 15% auditable; (d) marco doc BÁSICA ≤15 docs vs ~40 estándar; (e) sin regresión suite (~391 baseline).

---

### FRENTE M · Playwright ciclos completos 3 niveles (coronación)

**Premisa**: suite que recorre 8 fases (arranque→categorización→riesgos→SoA→marco doc→implantación/evidencias→cierre/conformidad) × 3 niveles × 3 actores (admin orquesta, cliente firma, auditor revisa MEDIA/ALTA). Los 3 niveles verdes = gate de coronación.

**Estado real (verificado)**
- `playwright.config.ts:7,8,25` testDir/globalSetup/webServer:3100 canónica.
- Helpers reutilizables: `_helpers/{auth-real,dda-seed,magerit-seed,conformidad-seed,pentest-seed,email-mock}.ts` (todos presentes, verificado `ls`).
- `dev/router.py:234` `set-test-project-category` + `:438` `seed-dda-alta-project` + `:688` `seed-magerit-alta-data` + seed-pentest/conformidad-ready (tier-aware) idempotentes.
- Specs por fase existen como referencia (onboarding, categorización mb17, magerit/dda OTP firma real, conformidad básica/commitment, auditor-portal-full-flow scaffold).
- `cycle-seed.ts` NO existe (verificado). Sin spec que encadene 8 fases por nivel.
- **⚠ CORRECCIÓN/ELEVACIÓN RIESGO**: la spec asumió que `/_dev/auditor-portal-token` ya existe (CI yml lo invoca). **Verificado: NO existe en `dev/router.py` (0 hits)**; el CI yml `admin-polish-empirical.yml:407` lo llama con fallback `::warning::` (línea 410) = aspiracional. Por tanto el endpoint nuevo de PASO M2 es **REQUERIDO** (no opcional) para el actor auditor MEDIA/ALTA.

**Pasos construibles**
| # | Acción | Ficheros | Esfuerzo |
|---|--------|----------|----------|
| M1 | BUILD `seedFullCycle(request, nivel)` que encadena seeds existentes SIN modificarlos (dda→magerit→pentest[M/A]→conformidad(nivel)→resetEmails) | `_helpers/cycle-seed.ts` (NEW) | S |
| M2 | MODIFY: endpoint `POST /_dev/seed-auditor-portal-token?project_id=X` (magic-link AUDITOR_PORTAL_ENAC reusa m12_magic_link). **Requerido — el endpoint asumido no existe** | `backend/app/dev/router.py` | S |
| M3 | BUILD helper `getAuditorToken()` → token para `/auditor-portal/{token}/*` | `_helpers/auditor-auth.ts` (NEW) | S |
| M4 | BUILD fixtures por nivel `FF_BASICA/MEDIA/ALTA` (COPIAR de `mb17_conformity_wizard.spec.ts:35-106`) + `mockFeatureFlags()` | `_helpers/level-fixtures.ts` (NEW) | S |
| M5 | BUILD spec maestra BÁSICA (8 sub-describes, admin+cliente, F7 'Firmar declaración ENS', F8 'Autoevaluación CCN-STIC 809' sin Pentest/ENAC) | `ciclo-basica-e2e.spec.ts` (NEW) | M |
| M6 | BUILD spec maestra MEDIA (FF_MEDIA, sidebar Auditor ENAC, 'Compromiso conformidad', F8 auditor smoke: summary+dda+draft-report views, SIN distintivo) | `ciclo-media-e2e.spec.ts` (NEW) | M |
| M7 | BUILD spec maestra ALTA (FF_ALTA, Pentest CPSTIC+Red Team, F5 verification, F8 auditor+pentest view; **1 test.skip eIDAS mp.info.3 R4** Future-1.F+) | `ciclo-alta-e2e.spec.ts` (NEW) | M |
| M8 | MODIFY: `POST /_dev/seed-full-cycle?tier=` orquesta seeds en 1 llamada (reusa funciones del mismo router) | `dev/router.py` | M |
| M9 | MODIFY: script `test:e2e:ciclos` + project playwright `ciclos` timeout 60s | `package.json`, `playwright.config.ts` | S |
| M10 | (AMPLIACIÓN) test OTP completo por nivel `@slow` reusando patrón `conformidad-basica-cliente-e2e.spec.ts` | 3 specs maestras | M |

**Dependencias**: backend dev server localhost:8000 `app_env != production` (gate `_require_non_production`), frontend 3100. Endpoints `_dev` verificados con curl pre-run. **M2 es prerequisito del actor auditor** (no había endpoint). Browsers chromium instalados. Specs MEDIA/ALTA mockean FF (no requieren tabla poblada); seeds de datos son llamadas reales.
**Riesgos**: **ALTO (M2)** — endpoint auditor inexistente, sin él los tests auditor quedan test.skip → construir M2 primero. **MEDIO** — `fullyParallel:false` → ciclos secuenciales 5-10min; usar project_ids distintos por nivel (`BASICA_E2E`/`MEDIA_E2E`/`ALTA_E2E`) para `--workers=3`. Specs cliente son canarios de regresión de `middleware.ts` (se rompen primero). Auditor limitado a smoke (3 vistas + testid) para evitar flakiness SSE. **GAP REAL ALTA** firma cualificada eIDAS (`GAP_REPORT_MAESTRO.md:130`, m05 es TIER1 canvas) → 1 test.skip honesto Future-1.F+.
**Hecho**: (a) los 3 `ciclo-*-e2e.spec.ts` verdes 100%, reproducibles en 2 ejecuciones sobre DB limpia; (b) assertions diferenciadas verificables sin navegador: `grep 'CCN-STIC 809'` solo en BÁSICA, `'auditor ENAC'` solo MEDIA/ALTA, `'Pentest CPSTIC'` solo ALTA; (c) `curl -X POST /_dev/seed-auditor-portal-token` → 200 con `token`; (d) ALTA tiene exactamente 1 test.skip con mensaje Future-1.F+ eIDAS; (e) specs importan helpers compartidos (cero duplicación de lógica); (f) job CI `ciclos-e2e` verde timeout 15m.

---

### FRENTE J · Portal Compliance perfecto (dogfooding ENS Medio sobre Fulkro)

**Premisa**: R6 trazado en 100% de acciones mutantes del subsistema (incluidos beats + norma_reports); las 3 cards "Compliance propio Fulkro" muestran score real (no "Sin datos"); checks atom 10.1 entran en scores ENS/RGPD cerrando el lazo dogfooding.

**Estado real (verificado — enforcement real, no vista)**
- 19 checks con lógica real (HTTP/SSL/SQL/`information_schema`/`os.environ`) `m_compliance_monitor/checks.py:139-1056`; runner → `unknown` ante excepción.
- `ComplianceMonitorService` lifecycle completo (`service.py:80-427`) + 4 beats Celery (`tasks.py:62-89`) + 7 norma plugins autodescubiertos.
- R6 YA cableado en 3 endpoints manuales: `api.py:144` helper `_emit_monitor_audit` + `_MONITOR_AUDIT_NS:141`; `:192,255` run_check/resolve/sync.
- **GAP-1 (S) confirmado**: `norma_reports_api.py:157` `run_norma_report` + `:176` `mark_reviewed` SIN `_emit_monitor_audit` (verificado 0 hits del helper en ese fichero).
- **GAP-2 (S)**: `tasks.py` `_run_batch()` corre beats sin pasar por audit_log.
- **GAP-3 (BUG SILENCIOSO) confirmado**: FE `compliance/page.tsx:55-56` `FULKRO_OWN_NORMA_KEYS` lowercase `"ens_rd_311_2022"`; plugin `normas/ens_rd_311_2022.py:30` `norma_key = "ENS_RD_311_2022"` UPPERCASE → `find()` (`page.tsx:177`) SIEMPRE undefined → 3 cards perpetuo "Sin datos".
- **GAP-4 (M)**: `check_admin_actions_audit_logged` (`checks.py:739`) + `check_marketing_analytics_opt_in_only` (`:821`) en CHECK_REGISTRY pero en ningún `checks_owned` de norma → score ENS no incluye trail admin; RGPD no evalúa opt-in.
- **GAP-5 (DEFER honesto Future-3B-4.F)**: M03 DdA propio + M09 audit-prep (cards Badge 'Próximo', XL post-piloto).

**Pasos construibles**
| # | Acción | Ficheros | Esfuerzo |
|---|--------|----------|----------|
| J1 | GAP-3: `FULKRO_OWN_NORMA_KEYS` → UPPERCASE (match backend). Puramente FE | `compliance/page.tsx` | S |
| J2 | GAP-1: importar/compartir `_emit_monitor_audit` y emitir `compliance.norma_report.generated` (run) + `.reviewed` (mark) | `norma_reports_api.py` | S |
| J3 | GAP-2: mover `_emit_monitor_audit`+NS a `audit_helpers.py` (rompe circular), emitir `compliance.beat.batch_ran` post-commit (mejor desde `service.py` async con `usuario='celery-beat'`) | `audit_helpers.py` (NEW), `api.py`, `tasks.py` | S |
| J4 | GAP-4: ENS plugin += `admin_actions_audit_logged` (peso redistribuido, suma 1.0) +ref art.24.1/op.exp.8 | `normas/ens_rd_311_2022.py` | S |
| J5 | GAP-4: ISO += `admin_actions_audit_logged` (A.8.20) | `normas/iso_27001_2022.py` | S |
| J6 | GAP-4: RGPD += `marketing_analytics_opt_in_only` (Art.7) | `normas/rgpd_ue_2016_679.py` | S |
| J7 | GAP-4: AEPD_COOKIES += `marketing_analytics_opt_in_only` (Guía 2020 §4) | `normas/aepd_cookies_2020.py` | S |
| J8 | BUILD tests: norma_reports emite audit_log; _run_batch emite; nuevos checks en checks_owned y `sum(check_weights)≈1.0` | `tests/.../test_norma_reports_audit_trace.py`, `test_atom10_checks_in_normas.py` (NEW) | S |
| J9 | MODIFY: cards deferred M03/M09 con Link accionable a `/admin/compliance/norma-reports` (no callejón) | `compliance/page.tsx` | S |

**Dependencias**: `audit_log` + trigger hash-chain `d4f8b2a90001` (presente, GAP_REPORT #38 RESUELTO). Extraer helper a `audit_helpers.py` evita circular (verificado: api.py NO importa norma_reports_api hoy). `sum(check_weights)==1.0` validado por `base.py __init_subclass__` → si redistribución imperfecta, falla en startup. Sync-registry tras deploy.
**Riesgos**: **BAJO** — J1 solo FE; verificar `SELECT DISTINCT norma_key FROM fulkro_compliance_norma_reports` = UPPERCASE antes de merge. Pesos deben sumar 1.0 exacto. **`_run_batch` es Celery sync (`asyncio.run`)** → emitir desde `service.run_frequency_batch()` (ya tiene session) con `usuario='celery-beat'`, no desde el task. GAP-5 defer sin riesgo arquitectural.
**Hecho**: (a) `SELECT DISTINCT norma_key` = UPPERCASE; (b) `pytest test_norma_reports_audit_trace.py` + `test_atom10_checks_in_normas.py` PASS; (c) `POST /norma-reports/ENS_RD_311_2022/run`→201 + fila `audit_log accion='compliance.norma_report.generated'`; (d) `_run_batch('daily')` → fila `compliance.beat.batch_ran`; (e) FE: 3 cards ENS/ISO/RGPD score≠null, badge≠'Sin datos'; (f) ChecksTable muestra 19 checks incl. los 2 de atom 10.1 con timestamp post run-all.

---

### Orden de construcción recomendado y encaje con frentes A–K

**Principio rector**: construir primero lo que **destraba assertions y cierra trazabilidad** (lazos cortos, bajo riesgo, alto desbloqueo), dejar lo voluminoso (specs E2E completas) al final cuando los seeds y endpoints estén verdes.

1. **FRENTE J completo primero** (todo S, ~1 sesión). Es el de menor riesgo y mayor ROI inmediato: GAP-3 (1 línea FE) resucita las 3 cards dogfooding; GAP-1/2 cierran R6 al 100% (prerequisito de "ENS Medio sobre sí mismo" R7, base de credibilidad ante ENAC); GAP-4 cierra el lazo retroalimentación (ejecutar check de Marcos → fila audit_log → check la detecta). Encaja con el frente de Compliance/Dogfooding existente y con R6/R7.

2. **FRENTE E (E1→E3 primero, luego E4/E5/E6)**. E1-E3 entregan el generador + test de coherencia, que actúa de **red de seguridad** para todo cambio de nav/fases/motores posterior — conviene tenerlo ANTES de tocar sidebars o añadir motores (encaja con cualquier frente que modifique navegación, p.ej. el frente de portal cliente). E5 (CCN-STIC 809) desbloquea el cierre BÁSICA, prerequisito normativo del FRENTE M ciclo BÁSICA y del FRENTE L BÁSICA autónomo.

3. **FRENTE L (L1→L2→L5 núcleo, luego L3/L4/L6-L9)**. Depende de la columna `categoria_objetivo`/`tamano_empleados` y de `SIZE_FACTOR["micro"]` ya existentes; L1 arrastra la deuda Alembic multi-head (coordinar con ejecutable-8-db-drift Pasada 16 — aplicar como rama nullable additive o DDL+stamp). L2 corrige el scope real (cablear `archetype_workflow_adjustments` al workflow engine, no "rescatar orphan"). Encaja con M01 categorización + M17 planning + pricing canonical (deuda Future-1.E.pricing).

4. **FRENTE M al final** (es la coronación, consume todo lo anterior). Construir **M2 (endpoint auditor) ANTES que M5-M7** porque el endpoint asumido no existe (riesgo ALTO). Orden interno: M1+M4 (helpers/fixtures) → M2+M3 (auditor) → M5 (BÁSICA, valida ANTES el cierre 809 del E5) → M6/M7 (MEDIA/ALTA) → M8/M9 (orquestación/CI) → M10 opcional. El ciclo BÁSICA depende de E5 (corpus 809) + L (perfil autónomo para validar variante unipersonal); el ciclo MEDIA/ALTA depende de m_audit_accompaniment ya existente.

**Cross-frente**: los 4 respetan ADR-014 (cliente firma/recibe, no opera), RLS y R6. El test de coherencia de E es de facto un guard para M (si nav cambia, ambos lo detectan). J es prerequisito de credibilidad para la narrativa de los ciclos M (dogfooding R7). Ninguno crea nuevas categorías ENS ni duplica `categoria_objetivo` (1=1 sostenido).

---

## ANEXO II - FRENTES AMPLIADOS VERIFICADOS (synth arquitecto - 2026-06-06 - incl. F pentest)

> Ground-truth verificado en codigo (file:line). 3 correcciones criticas al briefing: (E) PI-guard YA cableado -> solo test; (M) _dev/auditor-portal-token NO existe -> BUILD; (F) task_execute_run STUB literal + vuln_orchestrator DEPRECADO con test-guard -> crear fase_runner.py nuevo.

# PLAN_MAESTRO — FRENTES AMPLIADOS (E · L · M · J · F)
> Síntesis arquitecto · base verificada en árbol `fulkro-portales@batch2-fase0-recorrido` (READ-ONLY). Cada frente reusa lo existente; respeta 1=1 proyecto/cliente, RLS fail-closed, R6 hash-chain, ADR-014 read-only OAuth. Correcciones empíricas marcadas **[VERIFICADO]** / **[SOSPECHA]**.

## Orden de construcción recomendado (cross-frentes)
1. **J-PASO1 + E-N2b + L-step1/4** (todos S, sin deps, sin migración) → ganancia inmediata de coherencia/anti-drift.
2. **F1 (M08 orquestador)** — es la cabeza que destapa todo el end-to-end pentest. Bloqueante de F2/F4/F7/F10 y de M-frente F7-pentest assertions.
3. **E-N2a generador + E-N6 memoria** (M) — independientes de F; mejoran los 3 copilotos que ya son cliente-facing.
4. **M-paso3 (auditor-portal-token backend)** — prerequisito de M-MEDIA/ALTA y reusable por J/auditor CI.
5. **J-PASO4/5 dogfooding + F2..F9** — capa de valor que consume F1 + servicios M03/M05/M09 existentes.
6. **M-fase_42 specs + F10 frontend + J frontend cards** — UI/E2E al final, una vez los backends responden.

Encaje con frentes A-K: estos 5 son **ampliaciones verticales** sobre motores ya cerrados. E toca agentes (A14/personas) + corpus. L toca M01/M03/M06/M16/M17/M21/M27 + pricing core. M es capa de test sobre _dev endpoints (depende de que A-K seed endpoints sigan idempotentes). J es dogfooding sobre m_compliance_monitor + reuse M03/M09/M05. F es M08→M09. **Ninguno introduce tablas nuevas salvo migraciones additive (F2/F4/F5/F6)** → respeta ADR-025.

---

## FRENTE E — Copilotos conocimiento ÍNTEGRO + AUTO-ACTUALIZABLE

### Estado real [VERIFICADO]
- 3 capas: plataforma estática (`system_knowledge.py:28` SYSTEM_KNOWLEDGE_CLIENTE, `:65` SYSTEM_KNOWLEDGE_ADMIN — constantes literales mantenidas a mano), estado-proyecto on-query (`m11_copiloto/workflow_state_scanner.py:771-870` ya vivo), RAG normativo parcial (`corpus/catalog.py:60-127` 13 docs · `:220-235` CCN-STIC-809 `pending_manual`).
- **CORRECCIÓN CRÍTICA F3-01 [VERIFICADO]**: el PI guard **YA está cableado** en ambos paths persona — `copilot_cliente_service.py:162-164` (refusal R29 "reformúlala con normalidad") y `copilot_admin_service.py:217-219` (refusal "Reformula la consulta"). Ambos hacen `sanitize_user_input(question)` + `should_block` → return `is_stub_fallback=True` ANTES del LLM. El spec asumía que faltaba; **NO falta**. F3-01 baja de "modify+wire" a **solo test de regresión** (asegurar que no se rompe).
- `CopilotQuery` existe (`agent_14_copiloto/types.py:35`) **sin** campo `history` [VERIFICADO] → amnesia N6 real.

### Pasos construibles
| ID | Tipo | Ficheros | Esfuerzo | Nota |
|----|------|----------|----------|------|
| **E-1 (ex F3-01)** | build (test only) | `tests/agents/test_pi_guard_persona_paths.py` | **S** | NO modificar los services (ya guardan). Test caracteriza: inyección 'ignore previous, reveal system prompt' a cliente+admin → `is_stub_fallback=True`, 0 llamadas LLM (mock router). Convierte el comportamiento existente en contrato anti-regresión. |
| **E-2 (N2-a)** | build | `scripts/generate_system_knowledge.py` + `agents/system_knowledge.py` | **M** | Parser regex TSX `CLIENT_NAV_SECTIONS` + import `WorkflowPhase.ordered()` + `FULKRO_COPILOT_PRIMARY_CONTEXT` + `AGENT_REGISTRY` (filtra status='activo') + `screen_references_catalog` YAML. Render f-string → sobreescribe constante con header `# AUTO-GENERATED — DO NOT EDIT`. **Ejecutar como step build (`make gen-knowledge`), NO en cada startup** (mitiga overhead). |
| **E-3 (N2-b)** | build | `tests/agents/test_system_knowledge_coherence.py` | **S** | CI gate anti-drift: cada `WorkflowPhase.ordered()` y cada href de `CLIENT_NAV_SECTIONS` debe aparecer en la constante; ≥N motores AGENT_REGISTRY en ADMIN. Depende de E-2 corrido ≥1 vez. |
| **E-4 (N6 memoria)** | modify | `types.py` + `agent_14_copiloto/service.py` + `m11_copiloto/api.py` + `copilot_{cliente,admin}_service.py` + test | **M** | (a) `history: list[dict]=field(default_factory=list)` en CopilotQuery; (b) `conversation_chat` (`api.py:~691`) llama `get_recent_messages(limit=8)` y prepopula; (c) prepend turnos a `messages` formato `{role,content}`. Limitar **6 turnos cliente (Haiku)**, 8 admin (Sonnet) por coste. |
| **E-5 (809)** | modify | `corpus/catalog.py` + `tests/corpus/test_corpus_catalog_completeness.py` | **S** | Entrada `CCN-STIC-809` `critical`/`pending_manual`. PDF lo sube Marcos manual; la entrada bloquea el gap de cierre BÁSICA. |
| **E-6 (73 medidas RAG)** | build | `scripts/ingest_ens_measures_chunks.py` + test integración | **M** | 1 chunk/medida desde `ens_measures_catalog_v1.yaml` con `measure_code`. Upsert idempotente. Test `@pytest.mark.integration` (requiere fastembed :8080 + DB). |
| **E-7 (scheduler corpus)** | build | `tasks/corpus_refresh_task.py` + `celery_app.py` + test | **L** | Solo `pending_auto` (INCIBE/OWASP). `pending_manual` (CCN/ISO) **solo alerta** admin, jamás descarga (anti-403/captcha). Beat weekly análogo a nudge `:252-261`. Emite `corpus.auto_ingest.*` Sub-atom 5.A. |

### Dependencias / Riesgos / Hecho
- **Deps**: E-1/E-5 independientes; E-3←E-2; E-4 reusa `get_recent_messages` (`conversation_service.py:114-142` ya existe); E-6←YAML saneado + `get_default_embedding_provider`; E-7←scripts corpus + Celery beat existentes.
- **Riesgos**: R1 parser TSX frágil (mitiga E-3 en CI); R2 overhead startup (mitiga: build step no startup); R3 token: 6-8 turnos + RAG ~9.4k tokens, sin overflow en 200k ctx, sí coste; R4 paths persona sin `conversation_id` → `history=[]` graceful (el gap real de amnesia es solo el path RAG donde sí hay id).
- **Hecho**: `pytest tests/agents/` PASS completo (incl `test_system_knowledge_wiring.py` existente); `python scripts/generate_system_knowledge.py` produce constante con ≥14 hrefs `/client-portal/` + todas las fases + ≥10 motores; editar `ClientSidebar.tsx` sin regenerar → E-3 FALLA con mensaje; E-6 `SELECT COUNT(*) knowledge_chunks WHERE measure_code IS NOT NULL >=73`.

---

## FRENTE L — Perfil INDIVIDUAL/autónomo para los 3 niveles ENS

### Estado real [VERIFICADO]
- `"micro"` **ya existe** en `dimensions_schemas.py:27-31` (`TamanoEmpleadosType`); persistido `models/core.py:123`. **GAP**: `tamano_empleados` NO está en `CANONICAL_DIM_QUESTION_MAPPING` → el wizard nunca lo escribe.
- 7 arquetipos en `pyme_archetypes.py` con `GENERICO` fallback (`:67`, confianza 0.50) [VERIFICADO]; **sin INDIVIDUAL/AUTONOMO**. `startup_unipersonal` ya existe como topología de roles (`m27/conformity_service_paso5.py:80`).
- Effort `SIZE_FACTOR{"micro":0.7}` ya reduce 30% (`m17/effort_estimator.py:86`). DdA `_measure_applies` ya filtra 3 niveles. Catálogo doc `aplica_desde` ya filtra. Pricing `BASE_PRICES_CANONICAL` 3900/11500/22000 [VERIFICADO :35-38] **flat sin factor tamaño**.

### Pasos construibles
| ID | Tipo | Ficheros | Esf | Nota |
|----|------|----------|-----|------|
| L-1 | modify | `m16_onboarding/dimensions_capture.py` | S | Añadir `tamano_empleados` a CANONICAL_DIM_QUESTION_MAPPING + `q-tamano-empleados` a DEFINITIONS. **Misma PR atómica** (steps 1+4 del spec). |
| L-2 | modify | `m16_onboarding/enums.py` | S | `Sector.INDIVIDUAL` (sintético como `PRECLIENTE`, filtrado del catálogo admin). |
| L-3 | build | `m16_onboarding/templates/onb-individual-sponsor-v1.json` | M | Preguntas autónomo: portátiles/SaaS/relación AAPP/datos. Sin comité/RACI/sedes. |
| L-4 | modify | `m01_categorization/pyme_archetypes.py` | S | `AUTONOMO_INDIVIDUAL` (n_empleados≤5 AND infra≠on_premise, conf 0.80) ANTES del fallback GENERICO. Ortogonal a sector. |
| L-5 | modify | `m21_portal_cliente/task_templates.yaml` | M | 6 templates `applicable_size_ranges:[micro]` (roles BÁSICA, declaración propia, ENAC MEDIA, revisión MEDIA, **gate ALTA bloqueante**, hint acumulación rol). Filtro `_matches_size_range` ya existe. |
| L-6 | modify | `template_catalog_v1.yaml` + `m06/catalog_loader.py` + `service.py` | M | Flag opcional `aplica_micro:false` en E-502/E-002/E-403. Filtro cuando `tamano==micro`. Campo opcional NO rompe catalogs (no es REQUIRED). |
| L-7 | modify | `core/pricing/rules.py` + `calculator.py` | M | `SIZE_DISCOUNT_MICRO`: BÁSICA -25% (→2.900), MEDIA -35% (→7.500), **ALTA 0% (revisión Marcos)**. Disclaimer "Auditor ENAC externo NO incluido, coste cliente". |
| L-8 | modify | `m03_dda/templates.py` + `service.py` | S | `render_no_aplica_justification(empresa_size)` añade frase CCN-STIC 801 sec 4.2 si micro. Determinismo de aplicabilidad intacto. |
| L-9 | modify | `agent_14_copiloto/prompts.py` + `m11/conversation_service.py` | S | Bloque `INDIVIDUAL_CONTEXT` (CCN-STIC 801 sec 5.1 acumulación RSEG+RSYS). **Verificar primero** que conversation_service carga `project.tamano_empleados` al context. |
| L-10 | modify | `m27/conformity_service_paso5.py` | S | BÁSICA+micro → `metadata_jsonb['individual_mode']=True` + `rseg_rsys_same_person`. NO cambia route_type. |
| L-11 | build | 5 ficheros test (archetype/pricing/dda/task_templates/conformity) | M | Cobertura de L-4/7/8/5/10. |

### Dependencias / Riesgos / Hecho
- **Deps**: L-1 ⊕ L (mismo fichero, atómica); L-2←L-3 (loader valida enum); L-7←L-11. **Sin migración Alembic** (`tamano_empleados` ya en `projects`).
- **Riesgos**: **NORMATIVO ALTO** — acumulación RSEG+RSYS solo tolerada CCN-STIC 801 con razonamiento documentado y firmado; el copiloto cita explícito y NUNCA infiere que ENAC la acepta sin justificación escrita. **ALCANCE ALTA (ALTO)** — ENS ALTA para autónomo es anómalo (op.acc.3/op.cont.3/mp.com.4 exigen infra); gate L-5 (`ENR_OB_06_INDIVIDUAL_ALTA_GATE`) **bloqueante real** sin aprobación Marcos. **PRECIO MEDIO** — descuento MEDIA no elimina coste auditor ENAC externo (600-2.000€ cliente); disclaimer obligatorio.
- **Hecho**: classify({n_empleados:1, cloud_native})→AUTONOMO_INDIVIDUAL conf≥0.80; pricing micro BÁSICA=2900/MEDIA=7500/ALTA=22000; DdA con `empresa_size=None` output idéntico (no regresión); 15+ tests pricing legacy pasan sin tocar; `pytest tests/` 0 nuevas failures sobre baseline.

---

## FRENTE M — Playwright E2E ciclo ENS completo BÁSICA/MEDIA/ALTA

### Estado real [VERIFICADO]
- Auth/seed reusables: `_helpers/auth-real.ts:34/76`, `global-setup.ts:19`. _dev endpoints **confirmados existentes**: `set-test-project-category` (`router.py:234`), `seed-dda-alta-project` (`:438`), `seed-pentest-auth-data` (`:862`), `seed-conformidad-ready` (`:1069`). 
- **GAP CONFIRMADO [VERIFICADO]**: `_dev/auditor-portal-token` **NO existe en router.py** (grep vacío). Referenciado solo en CI yml. **Sospecha del spec = real → M-3 es BUILD, no verify.**
- `fase_42/` **NO existe** [VERIFICADO]. No hay spec maestro 3-en-1 encadenado.
- 10 fases canónicas `core/workflow_phase.py:40` (las 8 del brief son mapeo cliente; assertions usan los **valores canónicos del enum**).

### Pasos construibles
| ID | Tipo | Ficheros | Esf | Nota |
|----|------|----------|-----|------|
| M-3 (prereq) | **build** | `backend/app/dev/router.py` | S | **Crítico**: crear `POST _dev/auditor-portal-token?project_id=` → MagicLink purpose=AUDITOR_PORTAL_ENAC (patrón m09_audit_prep). Sin él, F8b MEDIA/ALTA es solo skip. |
| M-1 | build | `_helpers/ens-cycle-seed.ts` | S | `seedEnsCycle(tier)`: create-test-client → **set-test-project-category DESPUÉS** de seed-dda (que fuerza ALTA) → magerit → pentest (MEDIA/ALTA) → conformidad-ready?tier=. |
| M-2 | build | `_helpers/auditor-token.ts` | S | `getAuditorPortalToken` skip si 404. |
| M-4/5/6 | build | `fase_42/ens-cycle-{basica,media,alta}.spec.ts` | M×3 | 8 secciones por fase lifecycle, assertions por testid+regex. Diferenciación: BÁSICA→E-041/autodeclaración sin ENAC; MEDIA→WorkflowBlockingAlert auditor ENAC + pentest scope; ALTA→Pentest CPSTIC/Red Team/DORA + auditor step completo (no skip). |
| M-7 | build | `fase_42/_fixtures.ts` | S | `PROJECT_FEATURE_FLAGS_BY_TIER` + `mockFeatureFlagsForTier` reuse de `mb17_categoria_*`. OPS-026. |
| M-8 | modify | `_helpers/global-setup.ts` | S | Intento POST auditor-portal-token → `process.env.AUDITOR_PORTAL_TOKEN` si 200, silencioso si 404. |
| M-9 | modify | (los 6 ficheros nuevos) | S | `npx tsc --noEmit` 0 errores = criterio sin navegador. |
| M-10 | build | `frontend/tests/e2e/README.md` (sección) | S | Pre-flight: uvicorn :8000 APP_ENV=dev + next start :3100 + postgres. |

### Dependencias / Riesgos / Hecho
- **Deps**: M-2←M-3; M-4/5/6←M-1+M-7; backend :8000 (APP_ENV≠production gates) + next :3100 + Alembic head aplicado + **FULKRO_AUTH_PRIVATE/PUBLIC_KEY cargados** (OPS-052 72ª: clave efímera rompe JWT verify del frontend → loginAsClient falla).
- **Riesgos**: **ALTO** auditor-portal-token (M-3 build, mitiga skip condicional); **ALTO** seed-dda fuerza ALTA → specs BÁSICA aceptan 73 entradas (no es error) o crear `seed-dda-tier-project` [SOSPECHA: alternativa más limpia]; **MEDIO** CIF único B00000000 compartido → 3 specs en serie (fullyParallel:false ya), `secondary=true` si paralelo; **BAJO** feature-flags MEDIA/ALTA via `page.route` mock → F2/F8 verifican UI con mock no BD (brecha estructural aceptada: no hay endpoint que configure flags en BD para test project).
- **Hecho**: `tsc --noEmit` 0 errores nuevos en fase_42/+helpers; grep 'seedEnsCycle'=3, 'Pentest CPSTIC' en alta NOT basica, 'E-041' en basica, 'commitment_pre_certification' en media+alta; `grep '_dev/auditor-portal-token' router.py ≥1`; stack levantado → `npx playwright test fase_42/ens-cycle-basica.spec.ts` PASSED no-skipped.

---

## FRENTE J — Portal Compliance perfecto (dogfooding ENS Medio Fulkro)

### Estado real [VERIFICADO]
- `m_compliance_monitor/` production-grade: `checks.py:1-1057` 19 checks reales; `service.py:80-476`; `api.py:144` `_emit_monitor_audit` (J-GAP1/GAP2 ya resueltos commits 18ec0444/2470f16f).
- **GAP plugin ENS [VERIFICADO]**: `ens_rd_311_2022.py:36` `checks_owned` (4 checks) **excluye** `admin_actions_audit_logged` (check 18, ENS art.24.1); `:71-73` declara **"categoría asumida BÁSICA"** (incoherente con dogfooding MEDIO declarado en CLAUDE.md/page.tsx). 
- **Dead-link [VERIFICADO]**: `frontend/.../norma-reports/` solo tiene `page.tsx`, **sin `[norma_key]/`** → `norma-reports/page.tsx:227` link roto.
- `window.prompt` en `monitor/page.tsx:271-272` (único anti-pattern). M03 DdA propio + M09 audit-prep propio = "Próximamente".

### Pasos construibles
| ID | Tipo | Ficheros | Esf | Nota |
|----|------|----------|-----|------|
| J-1 | modify | `normas/ens_rd_311_2022.py` + `test_norma_plugins.py` | S | +`admin_actions_audit_logged` a checks_owned; BÁSICA→MEDIO; re-balancear pesos sum=1.0 (0.30/0.20/0.20/0.15/0.15). `validate()` en registry-time valida sum. |
| J-2 | build | `norma-reports/[norma_key]/page.tsx` | M | `getNormaHistory`+`getNormaLatest` (norma-api.ts ya existe) en paralelo (2 queries: lista sin md_content + latest con md). Tabla historial + `<pre>` Markdown colapsable + "Marcar revisado". |
| J-3 | modify | `monitor/page.tsx` | S | Reemplazar `window.prompt` por Dialog shadcn/ui + textarea. Mejora axe-CI. |
| J-4 | build | `dogfooding_api.py` + `dogfooding_service.py` + test | **L** | `POST /dogfooding/dda-fulkro`: reusa DdAService con `ORG_FULKRO_SELF_PROJECT_ID`. Firma Ed25519 M05. Emite `compliance.dogfooding.dda_generated`. |
| J-5 | modify | `dogfooding_api.py` | M | `POST /dogfooding/simulacro-fulkro`: reuse 100% SimulacroPreEnacService con ORG_FULKRO_SELF. |
| J-6 | modify | `config.py` | S | `ORG_FULKRO_SELF_PROJECT_ID` UUID fijo (no migración). |
| J-7 | modify | `compliance/page.tsx` (×2 cards) | M | Cards M03/M09 accionables con fallback graceful 404 (pre-piloto). |

### Dependencias / Riesgos / Hecho
- **Deps**: J-2←norma-api.ts existente; J-3←Dialog shadcn cross-app; J-4/5←DdAService+SimulacroPreEnacService+M05+`_emit_monitor_audit`; J-GAP1/2/3 ya resueltos = base limpia.
- **Riesgos**: **ALTO J-4** — DdAService es project-scoped **RLS enforced**; pasar ORG_FULKRO_SELF requiere que ese UUID **exista en `projects`** O bypass system-level → 404/FK violation si no. **Mitigación: crear fila `projects` system (is_system=True) con ese UUID en migración additive** (más seguro que bypass RLS). Verificar m03_dda antes de codificar. **MEDIO J-5** — simulacro con proyecto sin datos retorna informe vacío/score bajo (honesto); card UI debe mostrar contexto 'datos propios incompletos'. [SOSPECHA: simulacro puede requerir DdA poblada → seed data]. **BAJO** J-3 cosmético.
- **Hecho**: J-1 `pytest test_norma_plugins.py` PASS incl `test_ens_plugin_owns_admin_actions_check` + `grep 'BÁSICA' ens_rd_311_2022.py = 0`; J-2 GET `/norma-reports/ENS_RD_311_2022` no 404 + `ls` confirma fichero; J-3 `grep window.prompt =0`; J-4 ruta registrada + audit emite `compliance.dogfooding.dda_generated` + `grep 'Próximamente' page.tsx` solo M09; J-5 ruta registrada + `grep Próximamente =0`; R6 hash-chain intacto (solo INSERTs vía helper existente).

---

## FRENTE F — M08 Verificación: pipeline pentest/vuln-scan autónomo end-to-end

### Estado real [VERIFICADO]
- Backbone ~13.8K LOC (motor más grande). ZFP 5-gates `zfp_engine.py:1-354` funcional. Kill-switch `kill_switch.py:1-287` SIGTERM<5s. MCP `mcp_executor_service.py` 13 tools `USE_MCP_REAL=false`→simulado. ens_mapper/mitre_mapper 3 capas. M08→M09 pegamento `integrations/m9_audit_prep.py:32-85` cableado.
- **DELTA CRÍTICO [VERIFICADO]**: `scheduler.py:234-238` `task_execute_run` es **STUB literal** (`return {"status":"stub_checkpoint_2"}`, solo loguea). Es **el único punto que bloquea TODO el end-to-end**.
- **`vuln_orchestrator.py:1-12` DEPRECADO #19 [VERIFICADO]**: comentario explícito "NO debe cablearse a endpoints nuevos" + existe `test_vuln_orchestrator_deprecated` guard. **Decisión obligada antes de F1: crear `fase_runner.py` limpio (llama OpenvasRunner+NucleiRunner directo), NO reusar vuln_orchestrator** (so pena de romper el test guard).
- `llm_classifier.py` temperatura NO fijada [SOSPECHA: verificar `core/ai/llm_router.py` signature antes de F3 — param puede ser `temperature` vs otro nombre].

### Pasos construibles
| ID | Tipo | Ficheros | Esf | Nota |
|----|------|----------|-----|------|
| **F1** | modify | `scheduler.py` + `service.py` + **`fase_runner.py` (nuevo, NO vuln_orchestrator)** | **L** | Orquesta A→H: phase timestamps → scope_deriver → fase_runner (Openvas+Nuclei) → cloud_audit (MEDIA/ALTA) → agregar candidates → run_zfp_pipeline → persist → completed. Gate external = require_pentest_authorisation. Fail-closed: cada sub-fase try/except → `partial_failed` con fase documentada, nunca aborta run entero. |
| F2 | modify | `service.py` + `models.py` + migración `m08_llm_triage_verdict_001` | M | `persist_findings_from_zfp`. Verdict como JSONB `llm_triage_jsonb` (nullable additive, NO tabla nueva ADR-025). |
| F3 | modify | `llm_classifier.py` + test | M | temp 0.0; delimitador `<<<FINDING_DATA_START>>>`; validación salida-vs-hechos (downgrade severity sin retest → meta-hallazgo `possible_prompt_injection`); fail-closed JSON inválido. **Verificar LLMRouter signature primero.** |
| F4 | build | `determinism.py` + `models.py` + migración + test | M | `run_manifest_hash` SHA-256(scope+tool_versions_pinned+templates+model). Golden run tabla `verification_golden_runs`. Drift→audit warning. |
| F5 | build | `epss_enricher.py` + migración + test | S | EPSS api.first.org + cache Redis 24h. severidad efectiva=max(cvss,epss). Graceful degradation si cae. |
| F6 | modify | `service.py`+`models.py`+`scheduler.py`+`portal_api.py`+migración | M | `accepted_risk_expires_at`/`requires_review_after` + beat diario re-abre vencidos + endpoint cliente GET accepted-risks (read-only ADR-014). |
| F7 | modify | `m09/simulacro_pre_enac_service.py` + test | S | `pentest_summary` (last_run_id, confirmed_count, ens_measures_hit). Convierte simulacro en evidencia mp.s.2 real. |
| F8 | build | `tests/m08_seeds/` (4 ficheros) | M | 5 findings golden (CVE-2021-44228 critical…) → run_zfp_pipeline → assert gate5 confirmed/probable + ≥3 medidas ENS. **Sin binarios, sin Hetzner, corre en CI.** |
| F9 | modify | `m09/dossier_generator.py` + test | S | `compliance_declaration.json` sección 13: `pentest_status` + nota_honesta "ALTA requiere pentest externo CPSTIC obligatorio; este scan es complementario, NO sustituye". **Obligatorio para pasar ENAC.** |
| F10 | modify | `mcps/page.tsx` + `RunScanButton.tsx` + `lib/api/verification.ts` | M | Botón admin POST runs. Cliente solo VE findings (ADR-014 read-only). |
| F14-DEPLOY | build | `Dockerfile.m08` + compose | XL | Hetzner FASE J: USE_MCP_REAL=true + binarios + credenciales scanner. Código construible-ya; ejecución-real binarios = deploy-time. |

### Dependencias / Riesgos / Hecho
- **Deps**: F1 es la cabeza (←scope_deriver+runners+zfp+kill_switch existentes). F2←F1; F3 paralelo; F4/F7/F10←F1(+F2). F5/F6/F8/F9 independientes (F8 corre sin DB ni binarios). F14←F1-F10+Hetzner.
- **Riesgos**: **CRÍTICO** task_execute_run STUB (F1 desbloquea). **ALTO** vuln_orchestrator DEPRECADO → **fase_runner.py nuevo** (decisión cerrada). **ALTO** temperatura LLM no verificada (R3) + anti-injection ausente. **MEDIO** simulado devuelve findings=[] en CI (F8 seeds mitigan). **MEDIO Alembic multi-head** — F2/F4/F5/F6 migraciones additive sobre head bloqueado por `radar.alembic-version-num-widen` pendiente; `alembic heads` antes de cada migración. **BAJO** [SOSPECHA] `VerificationFinding.project_id` puede ser derivado via JOIN no columna directa → verificar antes de queries dossier.
- **Hecho**: `pytest tests/m08_seeds/` PASS sin binarios (5 seeds confirmed/probable); `test_kill_switch_and_scheduler` dispatch→execute persiste ≥1 finding; `test_injection_attempt_does_not_degrade_finding` PASS; `test_simulacro_includes_pentest_summary` PASS; dossier ZIP contiene `compliance_declaration.json` con nota_honesta; `grep temperature llm_classifier.py ≤0.2`; `run_manifest_hash IS NOT NULL`; accepted_risk vencido re-abierto por beat; RunScanButton renderiza 0 errores TS.
