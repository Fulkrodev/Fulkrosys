# Ejecutable 8 · Pasada 21 — Cobertura ENS REAL de Fulkro

> **Tipo:** auditoría READ-ONLY (no se construyó nada · no se propuso plan).
> **Fecha:** 2026-06-02 · **Branch:** radar-v3-pr · **Método:** lectura del CUERPO de cada
> servicio/modelo/endpoint/plantilla/migración (PROHIBIDO concluir por grep/keyword). Toda
> clasificación cita `file:line` del cuerpo real.
> **Pregunta de fondo:** ¿Fulkro implementa ENS **de verdad** —produce los artefactos, gestiona
> las medidas, genera las evidencias y las traza— como un consultor con el manual delante, o sólo
> tiene las pantallas?
>
> **Detalle por ítem (tablas completas con `file:line`):**
> - [Frente A · 73 medidas Anexo II](_pasada21/frente_A.md)
> - [Frente B · Entregables por fase 0–7](_pasada21/frente_B.md)
> - [Frente C · Mantenimiento ↔ Retainer](_pasada21/frente_C.md)
> - [Frente D · Compliance propio Fulkro](_pasada21/frente_D.md)

---

## 0. Veredicto ejecutivo

**Fulkro implementa ENS de verdad en el TRAMO DE IMPLANTACIÓN (Fases 0–7), y mayormente "de pantalla + dead-code" en el TRAMO DE MANTENIMIENTO (Fase 8 / retainer).** No es un shell: el núcleo certificable —SoA real per-proyecto sobre las 73 medidas, fábrica documental con datos del cliente + firma Ed25519, evidencia ligada a medida, dossier de auditor, máquina de estados de cierre ENAC, y un portal de compliance propio (dogfooding) con lógica genuina— **existe y es funcional**. Los huecos se concentran en (1) **dos defectos normativos del cierre BÁSICA**, (2) **el ciclo vivo del retainer que no se ejecuta automáticamente** (servicios reales sin cablear al beat + integraciones production-grade que son dead-code), y (3) varias medidas técnicas que se cubren **documentalmente** sin verificación automática (admisible en el modelo consultor, pero hay que saberlo).

| Frente | Veredicto neto | ¿Bloquea certificar? |
|---|---|---|
| **A · 73 medidas** | SoA/DdA real (clase 1). Medidas técnicas cubiertas por plantilla+DdA+evidencia manual. 1 hueco normativo (op.exp.8) + 1 stub (semáforo per-medida). | **No bloquea MEDIA.** ALTA: falta TSA real (mp.info.4). |
| **B · Fases 0–7** | Implantación sólida (clase 1 en F0/F1/F3/F4/F6 + cierre MEDIA/ALTA). | **BLOQUEA cierre BÁSICA conforme** (firmante + AMPARO). |
| **C · Retainer/Fase 8** | Servicios reales pero **el beat dispara stubs**; LUCIA y recert son dead-code; revisión anual AR y autoevaluación 808 **no existen**. | **Bloquea "mantenimiento vivo"**; no bloquea la certificación inicial. |
| **D · Dogfooding** | Real, no shell. 19 checks con lógica genuina, 7 normas, presign MinIO real. | No bloquea. Gap: el monitor no se auto-traza en R6. |

---

## 1. El corazón de Frente A: ¿existe UN registro de medidas real? — **SÍ**

Confirmado leyendo el cuerpo:

- **Catálogo canónico** `docs/catalogs/ens_measures_catalog_v1.yaml` → tabla `ens_measures` (`backend/app/models/ens.py:16-44`): 79 entradas con `aplica_basica/media/alta`, `categoria_minima`, `dimensiones_aplicables`, refuerzos por categoría.
- **SoA per-proyecto** `dda_entries` (`models/ens.py:48-72`): por medida → `aplicabilidad`, `justificacion_no_aplica`, `refuerzos_aplicados` (JSONB), `estado_implementacion`, `responsable`, `aprobado_por`, `fecha_aprobacion` + revisión cliente (ClientReviewMixinA).
- **Generación atómica** `m03_dda/service.py:71-168` `generate_dda()`: crea las 79 entries, escala por categoría (`_measure_applies:466-482`), no-aplica con justificación template, **refuerzos leídos por categoría** desde `ens_measure_refuerzos.applicable_categories ? :cat` (`_applicable_reinforcements:484-505`). Freeze/unfreeze con gate ≥80% valoradas (`:299-367`).
- **Refuerzos R1–R9 seedeados de verdad**: parser determinista del BOE (RD 311/2022 Anexo II) en `backend/scripts/seed_ens_measure_refuerzos.py` + migración `san_c_seed_ens_refuerzos_dimensiones.py` (~133 filas / 48 medidas), con `source_chunk_id` FK para trazabilidad ENAC. **Caveat de runtime:** la migración es "tolerante a corpus ausente" (no-op si el RD 311 no está ingerido en `knowledge_chunks`) → en una BD fresca hay que re-ejecutar el seed. El mecanismo es real; su población depende del estado de la BD.

**Tres matices que impiden llamarlo "control-model completo":**
1. **Dualidad de nivel de madurez.** `estado_implementacion` es de **4 estados** (no CMM L1–L5). El CMM L0–L5 real vive en OTRO motor (`m04_gap/enums.py:23-66`, target por categoría L2/L3/L4) y se guarda en `Finding.metadata_jsonb`, **no en la entry DdA**. La SoA y el motor de madurez no comparten el campo de nivel.
2. **Semáforo per-medida = STUB.** `m04_gap/control_status_service.py:112-121`: el filtro por `measure_code` es un `pass` ("*match ALL documents project mientras compute MVP*") → el cumplimiento por medida agrega TODOS los documentos del proyecto. **Verificado en cuerpo.**
3. **Evidencia↔medida sí existe** pero por `evidence.measure_code` (`m07_evidence/ingestion_service.py:80-167`), no como campo en `dda_entries`.

---

## 2. Frente A — síntesis por familia (extracto; tabla completa en el anexo)

| Familia | Clase | Cuerpo leído | Lectura |
|---|:--:|---|---|
| org.1–4 (PSI/Normativa/POS) | **1** | `m06_document_factory/service.py:267-436` (docxtpl + Ed25519 + PDF + audit_log + gate DdA-frozen) | Genera documentos reales con datos cliente |
| op.pl.1 MAGERIT | **1** | `m02_magerit/service.py` | Real, **pero no escala informal/semiformal/formal por nivel (d)** |
| op.acc.5 privilegios | **1** | `m_cloud_connectors/gap_rules.py:134-180` | Detecta exceso de privilegiados en el cloud del cliente |
| op.acc.6 MFA | **2** | `m_cloud_connectors/gap_rules.py:96-131` | Detecta `mfa_enabled=False` pero **NO distingue admins-Media vs todos-Alta** |
| op.acc.3 segregación | **2** | `m28_change_governance/topology_service.py` | Roles RSeg/RSis documentados, no enforce |
| op.exp.5 cambios | **1** | `m28.../materiality_engine.py:40-125` | Materialidad determinista real |
| **op.exp.8 logs ≥12m + NTP** | **3** | (ausente; sólo en copy/preguntas) | **HUECO NORMATIVO**: la retención 12m de `m26_backup/service.py:170` es de FULKRO, no del cliente |
| op.ext.1 cláusulas ENS terceros | **1** | `m14_contracts/legal_templates.py:82-90` (C-130, CCN-STIC 823) | Contratos con cláusulas ENS a subcontratistas |
| op.cont.1 BIA | **1** | `m19_risk/bia_service.py:24-60` | CRUD BIA real (RTO/RPO/impacto) |
| gatings SOLO-ALTA (op.ext.3, op.cont.2-4, mp.eq.3, mp.info.4) | **1 (gating)** | `m03_dda/service.py:466-482` | Se activan vía `aplica_alta` en la DdA ✓ |
| mp.per formación | **1** | `m24_idms/awareness_tracker.py:25-55` | Sesiones + asistencia con coverage % |
| mp.info.3 firma-e | **1** | `m05_signing/api.py:259,547` | Ed25519 + OTP + audit_log + hash chain |
| **mp.info.4 sellos tiempo (ALTA)** | **2** | (sin integración TSA) | Gating ALTA correcto, pero **sin TSA real** |
| **mp.info.6 backup cliente** | **2** | `m26_backup/service.py:46-307` | **Bookkeeping** (no ejecuta pgBackRest; respalda a FULKRO, no al cliente) |
| mp.s.2 web/vuln-scan | **1** | `m08_verification/mcp_executor_service.py:62` | nuclei/prowler + auto-attach a IDMS (si `USE_MCP_REAL`) |
| mp.sw "no aplica + justif" | **1** | `m03_dda/service.py:138-156` | Confirmado: no-desarrolla → NO_APLICA con justificación |
| op.pl.2-5, mp.if, mp.eq, mp.com, mp.si, mp.s.4, op.mon (detección) | **2** | plantillas E1xx/E2xx + DdA | Cubierto documentalmente, sin verificación técnica automática |

---

## 3. Frente B — síntesis por fase (extracto; tabla completa en el anexo)

| Fase / entregable | Clase | Cuerpo leído | Lectura |
|---|:--:|---|---|
| F0 Actas roles/comité/alcance (E-002/003/155) | **1** | `templates/policies/E002_*.md:57-198`, `E003_*.md:9-122`, `rectores_generator.py:58-150` | Jinja2 real con datos cliente, category-aware |
| F0 Plan Adecuación 806 (E-150) | **2** | `m17_planning/pda_generator.py:69-228` | Real pero placeholders: `conformes=0` (:173), `cost=0` (:208), `info_types/services=[]` (:219-220) |
| F0 Acta de DECISIÓN adoptar ENS | **3** | (sin template propio) | Absorbida por PSI E-100 + Acta comité E-003 |
| F1 Categorización 5 dims + Anexo I | **1** | `m01_categorization/service.py:137-215` (regla del máximo) | Determinista real. **No emite audit_log (c)** |
| F1 Herencia cliente público (AAPP) | **3** | (ausente; `is_aapp_developer` es arquetipo comercial) | **Hueco**: no modela herencia de la AAPP contratante |
| F1 Firma RInf+RSer | **2** | `m01.../signature_integration.py:75-141` | **Un solo firmante**, no fuerza doble RInf+RSer |
| F2 MAGERIT v3 | **1** | `m02_magerit/service.py:434-1414` (quali+quanti+residual+freeze) | Completo. **No escala por nivel (d)** |
| F2 Aceptación riesgo residual Dirección | **2** | `m02.../service.py:1100-1192` | Sólo texto en plantillas; sin artefacto firmado de aceptación |
| F3 SoA/DdA + firma RSeg (E-040) | **1** | `m03_dda/service.py:71-168` + `signature_integration.py:110-195` | Real, category-aware, gate freeze, firma magic-link RSEG |
| F4 PSI+Normativa+POS | **1** | `template_catalog_v1.yaml` + `m06.../service.py:267-436` | 84 plantillas, scaling por catálogo `aplica_desde` (42 básica/23 media/9 alta). Auto-selección por nivel = manual (producto) |
| F6 Evidencias IDMS + dossier | **1** | `m24_idms/idms_service.py:30-450`, `m09/dossier_generator.py` | 15 carpetas, tag por medida, dossier ZIP + MANIFEST con hashes |
| F7 Máquina de estados cierre | **1** | `m_audit_accompaniment/state_machine.py:25-134` | BÁSICO 6 / MEDIO-ALTO 11 estados, branch por categoría, audit_log 3-way OR |
| **F7 BÁSICA pentest excluido** | **1 ✓** | `state_machine.py:34-41` | **Correcto**: pentest no aparece en branch BÁSICO |
| **F7 BÁSICA Declaración 809 firmante** | **2 ✗** | `m27_conformity/distintivo_generator.py:369-382` + `E180_*.md:81-88` | **DEFECTO**: E-180 firma **RSEG**; CCN-STIC 809 Anexo A exige **DIRECCIÓN/órgano superior**. El artefacto correcto existe en paralelo (E-041, representante legal art.33.2) pero NO es el del cierre de producto |
| F7 BÁSICA distintivo Pantone Orange | **1 ✓** | `distintivo_generator.py:217-256` (#FE5000 único) | Correcto CCN-STIC 809 |
| **F7 BÁSICA comunicación CCN/AMPARO** | **3** | (ausente) | **HUECO**: no hay envío/registro a AMPARO |
| F7 MEDIA/ALTA flujo ENAC + portal auditor | **1** | `state_machine.py:60-86` + `m09/auditor_*_api.py` + `AuditAccompanimentTimeline.tsx` | Documental→campo→PAC→verificación→certificado→bienal. Portal auditor real |

---

## 4. Frente C — síntesis del retainer (extracto; tabla completa en el anexo)

**Hallazgo transversal CRÍTICO (verificado en cuerpo):** el Celery beat de retainer dispara **stubs log-only**.
`celery_app.py:116-135` programa `retainer-renewal-check` y `retainer-monthly-invoices`, pero sus cuerpos
en `m23_retainer/tasks.py` (`update_all_renewal_statuses:42-49`, `generate_monthly_invoices:104-111`,
`check_overdue_activities:31-39`, `renewal_trigger_daily:114-123`) son `logger.info(...) + return {...}`
**sin tocar BD**. Los servicios reales existen pero no están cableados. (Sí es real `execute_scheduled_activity:52-101`, que llama `RetainerService.execute_activity`, pero no tiene entrada en el beat → sólo on-demand.)

| Item | Clase | Cuerpo leído | Qué pasa |
|---|:--:|---|---|
| Revisión anual del análisis de riesgos | **3** | `tasks.py:26` apunta a `m03_dda.annual_review` (**método inexistente**); cae en `else` manual (`retainer_service.py:491`) | **No existe motor** de re-baseline/re-aprobación del AR |
| Autoevaluación seguimiento anual (808) | **3** | (ausente) | **No existe** muestreo de criterios 808 |
| Revisión por la Dirección | **2** | `dpc_anual_service.py:236-328` (DPC firmado M05) | Proxy parcial; sin acta formal ni gestión de NC |
| Renovación bienal + alerta T-90 | **1 / 2** | T-90 REAL `biannual_alert_task.py:35-99` sobre `audit_schedules.next_audit_due`; campaña `renewal_scheduler.py:43-82` real **pero dead-code (sin beat/API)** | La alerta funciona; la campaña recert no se auto-dispara |
| Notificación LUCIA/INCIBE (817) | **2** | `lucia_federation.py:190-321` httpx OAuth **real** + payload 845; decision tree `ccn_cert_decision_tree.py:59-105` emite string `auto_submit_lucia` | **Dead-code**: `submit_incident` no se invoca desde ningún flujo; `create_incident` inserta `notificado_lucia=false` y no dispara nada |
| Re-SoA ante cambio de alcance | **2** | `materiality_engine.assess:40-120` real; `open_recategorization:8-23` y `open_extraordinary_audit:8-23` **stubs puros**; API persiste `new_dda_id=None` | Sólo trackea; **no re-corre M01 ni regenera SoA** |
| Tiers de retainer | **1 / 2** | `CADENCES_BY_PROFILE:36-97`, `SLA/HOURS_BY_PROFILE`, `generate_annual_activities:253-303`; billing manual real (api.py:460→M15 Verifactu) | Tiers **NO nominales** (cadencia/SLA/horas/precio reales). Billing recurrente automático = **stub beat** |

**audit_log R6 en mantenimiento:** m27 (DPC/bienal/LUCIA/renewal) e incidentes **NO emiten audit_log**. El ciclo vivo queda mayormente fuera de la cadena inmutable; sólo `m19/cliente_continuidad_api:144-174` emite.

---

## 5. Frente D — síntesis del dogfooding (tabla completa en el anexo)

**Veredicto: real, no shell.** 0 checks clase 3 (ningún "verde" fabricado). De los **19 checks** (`m_compliance_monitor/checks.py`): ~9 clase 1 sólida (I/O real) y ~10 clase 2 por *dependencia de infra aún no desplegada* o *proxy débil* — pero cuando no pueden evaluar devuelven `unknown`/`yellow` honesto (0.5), no un pase.

- **Clase 1 fuertes:** `ssl_cert_expiry` (`checks.py:191` socket+ssl real), `backups_integrity` (`:237` `SELECT MAX FROM backup_jobs`), `audit_logs_continuity` (`:278` lee `audit_log`), `rls_coverage_percentage` (`:481` `pg_class.relrowsecurity ∩ information_schema` — el más fuerte), `admin_actions_audit_logged` (`:739` `COUNT FROM audit_log`), `marketing_analytics_opt_in_only` (`:821` inspecciona `os.environ`), `cookies_banner_functional`/`rgpd_endpoints_responding`/`security_txt_reachable` (HTTP real).
- **Clase 2 (degradan honesto):** dependen de tablas/columnas/ficheros creados en atoms posteriores (`fulkro_ropa_treatments`, `email_log`, `consent_renewal_due`, MD de políticas) o usan `st_mtime` como proxy de "revisión".
- **7 normas** (RGPD/LOPDGDD/LSSI-CE/NIS2/ISO27001/ENS/cookies): **todas clase 1**, agregan outcomes reales desde `compliance_checks` con pesos que suman 1.0 (`normas/base.py:205`), generan Markdown real mapeado a artículos.
- **Presign genuino:** `reports_service.py:148` → `minio_client.py:53,148` usa `client.presigned_get_object(expires=7d)` del SDK `minio.Minio` real (no string falso). Semáforo, alertas+auto-resolve, emails MJML, scheduling Celery y frontend tanstack: todo cableado.

**Único gap sustantivo (producto):** el monitor **no escribe audit_log** para sus propias acciones admin (run-check/resolve-alert/sync/generate-report hacen `db.commit()` sin fila R6; no hay middleware global de audit). Incoherencia de dogfooding: la plataforma vende trazabilidad R6 y su propio órgano de compliance no se auto-traza.

---

## 6. Lectura de desarrollador-ENS senior: hueco-normativo-real vs hueco-de-producto

### A) HUECOS NORMATIVOS REALES (el ENS exige algo que el sistema NO produce/gestiona)

| # | Hueco | Frente | `file:line` | ¿Bloquea? |
|---|---|---|---|---|
| N1 | **Declaración BÁSICA firmada por RSEG, no por Dirección** (CCN-STIC 809 Anexo A exige órgano superior) | B | `m27_conformity/distintivo_generator.py:369-382`, `E180_*.md:81-88` | **Sí — cierre BÁSICA** |
| N2 | **Comunicación a CCN vía AMPARO ausente** (cierre del ciclo BÁSICA) | B | (ausente) | **Sí — cierre BÁSICA** |
| N3 | **Revisión anual del análisis de riesgos** inexistente (re-aprobación periódica art.) | C | `tasks.py:26` (método inexistente) | Mantenimiento (no la cert inicial) |
| N4 | **Autoevaluación de seguimiento anual (CCN-STIC 808)** inexistente | C | (ausente) | Mantenimiento |
| N5 | **op.exp.8 — retención de logs ≥12 meses + NTP del cliente** no rastreada (sólo copy) | A | (ausente; `m26.../service.py:170` es de FULKRO) | MEDIA: expuesto, mitigable con evidencia manual |
| N6 | **Notificación inmediata LUCIA Alto/Crítico** no se dispara (integración real pero dead-code) | C | `lucia_federation.py:190-321` nunca invocado | Obligación legal en mantenimiento |
| N7 | **Herencia de categorización de la AAPP contratante** no modelada (target FULKRO) | B | `m01` (ausente; `pyme_archetypes.py:130`) | Degrada; no bloquea categoría |
| N8 | **Aceptación formal de riesgo residual por la Dirección** sin artefacto firmado | B | `m02.../service.py:1100-1192` (sólo texto) | Degrada MEDIA/ALTA |
| N9 | **Acta de Revisión por la Dirección + gestión de NC** sin flujo formal | C | proxy DPC `dpc_anual_service.py:236-328` | Mantenimiento |
| N10 | **MAGERIT no escala informal/semi/formal por nivel** (proporcionalidad CCN-STIC 803) | A/B | `m02_magerit/service.py` (siempre full) | No bloquea (cumple de más) |
| N11 | **mp.info.4 sellos de tiempo (ALTA) sin TSA real** | A | (gating OK, sin integración) | ALTA: documentar o integrar |

### B) HUECOS DE PRODUCTO (el motor existe; falta cablear/persistir/UI/orquestar)

| # | Hueco | Frente | `file:line` |
|---|---|---|---|
| P1 | **Billing recurrente del retainer no se ejecuta** (3 implementaciones reales, beat = stub log-only) | C | `tasks.py:104-111` vs `billing_integration.py:163-212` |
| P2 | **Reloj de renovación T_MINUS_* nunca avanza por beat** (`update_all_renewal_statuses` stub) | C | `tasks.py:42-49` vs `retainer_service.py:529-563` |
| P3 | **Campaña recert bienal dead-code** (no cableada a beat/API) | C | `renewal_scheduler.py:43-82` |
| P4 | **Re-SoA ante cambio material sólo trackea** (recat/extraordinary = stubs) | C | `recategorization_service.py:8-23` |
| P5 | **Semáforo per-medida agrega TODOS los docs** (`pass` en el filtro) | A | `control_status_service.py:112-121` |
| P6 | **Dualidad nivel de madurez** (4 estados DdA vs CMM L0-L5 en `m04_gap`, no compartido) | A | `m04_gap/enums.py:23-66` |
| P7 | **op.acc.6 MFA no escala rol/nivel** (admins-Media vs todos-Alta) | A | `gap_rules.py:96-131` |
| P8 | **Monitor de compliance no se auto-traza en R6** | D | `m_compliance_monitor/api.py` (sin audit_log) |
| P9 | **m01 categorización y core m03 DdA no emiten audit_log** (sólo vía firma m12 / materialización m06) | B | `m01.../service.py`, `m03.../service.py` |
| P10 | **PdA con placeholders** (`conformes=0`, `cost=0`, info/services vacíos) | B | `pda_generator.py:173,208,219-220` |
| P11 | **mp.info.6 backup del cliente sólo documental** (m26 respalda a FULKRO) | A | `m26_backup/service.py:46-307` |
| P12 | **Selección de set documental por nivel = manual** (capacidad existe, automatización no) | B | `documentation_levels.py` + `m06` |
| P13 | **Refuerzos R1-R9 dependen de seed condicional al corpus** (no-op si RD 311 no ingerido) | A | `san_c_seed_ens_refuerzos_dimensiones.py` |

---

## 7. Matriz de bloqueo por nivel de certificación

| Nivel | ¿Puede Fulkro llevar HOY a un cliente a certificar? | Bloqueantes a cerrar |
|---|---|---|
| **BÁSICA** (autodeclaración 808/809) | **NO conforme al 100%** | N1 (firmante Dirección, no RSEG) + N2 (AMPARO). Ambos son de cierre; el resto del expediente BÁSICA es sólido. |
| **MEDIA** (ENAC) | **Sí, con reservas menores** | N5 (op.exp.8 vía evidencia manual) + P5 (fiabilidad del panel por medida). El flujo ENAC + dossier + portal auditor están reales. |
| **ALTA** (ENAC + refuerzos) | **Sí en lo documental; reservas técnicas** | N11 (TSA mp.info.4) + verificación técnica de op.cont.2-4/mp.eq.3 (gating correcto, ejecución documental). |
| **MANTENIMIENTO** (Fase 8, post-cert) | **NO entrega ciclo vivo automático** | N3/N4/N6/N9 + P1/P2/P3/P4. Hoy: sólo alertas T-90/DPC funcionan solas; el resto es clic manual o dead-code. |

---

## 8. Priorización (¿qué bloquea certificar de verdad?)

**P0 — bloquea cierre BÁSICA conforme (normativo, arreglo acotado):**
1. N1 · Declaración de conformidad firmada por **Dirección/órgano superior** (unificar en E-041; deprecar la firma RSEG de E-180 en `distintivo_generator.py:369`).
2. N2 · Comunicación/registro al CCN vía **AMPARO**.

**P1 — habilita "mantenimiento ENS real" (mayoría producto/wiring + 1 legal):**
3. P1/P2 · Cablear billing recurrente y `update_all_renewal_statuses` al beat (reemplazar los stubs log-only).
4. N6 · Cablear `submit_incident` LUCIA al alta de incidente Alto/Crítico (**obligación legal de notificación inmediata**).
5. N3 · Construir la **revisión anual del análisis de riesgos** (motor inexistente).

**P2 — robustez/fiabilidad:**
6. P5 · Filtrar el semáforo por `measure_code` (hoy `pass`).
7. P8/P9 · Emitir audit_log R6 en monitor de compliance, categorización y DdA-core (coherencia de la cadena inmutable que la plataforma vende).
8. N4/N9 · Autoevaluación 808 + acta de Revisión por la Dirección con NC.
9. N5 · Check/artefacto dedicado de op.exp.8 (retención ≥12m + NTP).

**Reservas para ALTA:** N11 (TSA) + N8 (aceptación residual firmada) + N7 (herencia AAPP).

---

## 9. Conclusión

El repo **hace** lo que dice en el tramo que importa para firmar el primer cliente: la SoA es real, las medidas están registradas y escaladas por nivel, los documentos se generan con datos del cliente y se firman, la evidencia se liga a medida y se exporta en dossier, y el dogfooding evalúa estado real. **No es un escaparate.** Pero hay dos defectos normativos concretos que **bloquean cerrar una BÁSICA conforme** (firmante de la Declaración + AMPARO), y el **retainer no ejecuta el ciclo vivo de mantenimiento de forma automática** (servicios reales sin cablear + LUCIA/recert dead-code + revisión anual del AR inexistente). El patrón dominante de los huecos es **de producto/wiring** (código real sin enchufar), no de fachada — con la excepción de op.exp.8, la herencia AAPP, la revisión anual del AR y la autoevaluación 808, que son **huecos normativos que requieren construir**, no sólo cablear.

> **Fin del mapa de Pasada 21.** No se construyó nada. Anexos con tablas íntegras por ítem en `docs/audits/_pasada21/frente_{A,B,C,D}.md`.
