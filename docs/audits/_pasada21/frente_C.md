# FRENTE C · Mantenimiento (Fase 8) ↔ RETAINER — Auditoría READ-ONLY (Pasada 21)

> Método: clasificación justificada leyendo el **cuerpo** del código (no nombres ni firmas).
> 1 = real y ejecutable · 2 = parcial / no cableado / dead-code real-pero-no-invocado · 3 = stub / placeholder.
> Sub-preguntas: **a** artefacto/documento generado · **b** evidencia IDMS por medida · **c** audit_log R6 hash-chain · **d** escala por nivel/tier · **e** frontend accionable (cliente/admin).

## Hallazgo transversal CRÍTICO: el Celery beat de retainer NO ejecuta nada

`backend/app/core/celery_app.py:116-135` registra dos entradas beat de retainer:
- `retainer-renewal-check` → `m23.update_all_renewal_statuses` (diario 07:00)
- `retainer-monthly-invoices` → `m23.generate_monthly_invoices` (día 1, 04:00)

Pero los **cuerpos** de ambas tasks son log-only (`backend/app/motors/m23_retainer/tasks.py`):
- `update_all_renewal_statuses` (tasks.py:42-49): `logger.info(...)` + `return {"status":"updated"}`. NO toca BD.
- `generate_monthly_invoices` (tasks.py:104-111): `logger.info(...)` + `return {"status":"scheduled"}`. NO toca BD.
- `check_overdue_activities` (tasks.py:31-39): igual, log-only.
- `renewal_trigger_daily` (tasks.py:114-123), `agent_26_weekly_analysis` (126-133), `generate_annual_reports` (235-242): log-only stubs.

Mientras tanto, los **servicios reales existen pero no están cableados al beat**:
- `RetainerService.update_renewal_status` (retainer_service.py:547-563) y `_renewal_status_from_days` (529-545, calcula T_MINUS_90/60/30/LAPSED) → reales, pero el beat los ignora.
- `RetainerService.generate_monthly_invoices_for_all` (retainer_service.py:881-912) → real, no beat-wired.
- `billing_integration.run_retainer_billing_cycle` (billing_integration.py:163-212) → real, idempotente, precio por tier desde `pricing_catalog`, crea `RetainerBillingEvent`. Su docstring afirma "Llamado desde Celery beat el 1 de cada mes a las 06:00" pero `grep` confirma **0 invocaciones** (solo su propia definición + `__all__`).

Tasks que SÍ tienen cuerpo real (no stubs): `execute_scheduled_activity` (tasks.py:52-101, llama `RetainerService.execute_activity`), `generate_quarterly_reports` (136-232), `ccn_stic_daily_scrape` (245-277), `drift_weekly_compute` (404-444), `media/basica digest` (280-401). PERO `execute_scheduled_activity`, `generate_quarterly_reports`, `drift_weekly_compute` **no tienen entrada en `beat_schedule`** → solo invocables on-demand.

---

## Tabla de findings

| Item | Clase | file:line (cuerpo) | a | b | c | d | e | Qué falta |
|------|:----:|--------------------|:-:|:-:|:-:|:-:|:-:|-----------|
| **Revisión anual del análisis de riesgos** (re-aprobar aunque no haya cambios) | **3** | NO EXISTE servicio. `m23` cadence `revision_ar_dda` → `m03_dda.annual_review` (tasks.py:26) **método inexistente**; `RetainerService.execute_activity` (retainer_service.py:412-509) solo cablea vigilancia/auditoria/reportes, `revision_ar_dda` cae en `else` "requiere ejecución manual" (491-493). m02_magerit/m03_dda sin `annual_review`/`rebaseline` | ✗ | ✗ | ✗ | parcial (sólo aparece en cadencia por tier) | ✗ | Todo: motor de re-baseline AR, re-aprobación con firma, artefacto E-043/renovación, evidencia IDMS, audit_log |
| **Autoevaluación de seguimiento anual** (muestreo CCN-STIC 808) | **3** | NO EXISTE. Ninguna implementación de muestreo/autoevaluación 808 en m25/m27/m23 (grep limpio). DPC anual NO es esto | ✗ | ✗ | ✗ | ✗ | ✗ | Servicio completo de autoevaluación con muestreo de criterios 808 + reporte |
| **Revisión por la Dirección** (incidentes, cambios, NC) | **2** | Parcial vía DPC anual: `dpc_anual_service.aggregate_dpc_context_snapshot` (dpc_anual_service.py:236-328) agrega SLA+Recovery+Incidents+Roadmap 12m; firma cliente M05 (process_dpc_signoff 462-487). NO hay acta de "Revisión por la Dirección" formal ni gestión de NC | ✓ (DPC firmado, hash SHA-256) | parcial (snapshot jsonb, no por-medida) | ✗ (m27 sin audit_log) | ✓ (Q5.A todos tiers) | ✓ `/client-portal/dpc-anual` | Acta formal de revisión por la dirección; tratamiento de no-conformidades; lessons_learned (placeholder en 304); audit_log |
| **Renovación bienal + alerta T-90** (Básica: nueva Declaración / Media-Alta: recert ENAC) | **1 (alerta) / 2 (campaña recert)** | T-90 REAL: `biannual_alert_task._check_biannual_audits_due` (biannual_alert_task.py:35-99) consulta `audit_schedules.next_audit_due <= today+90` → alert con severity critical<30d/warning. `next_audit_due` se puebla real en `schedule_biannual_audit` (audit_schedule_service.py:47-112, conformity_date+730d). **Campaña recert `run_renewal_bianual_check` (renewal_scheduler.py:43-82) es real (6m/3m/1m, crea campaña+dossier) pero NUNCA cableado a beat ni API — solo lo invocan un test y un demo** | ✓ alert / parcial campaña | ✗ | ✗ | parcial | ✓ admin `/conformity` + `/renewal`, cliente `/certificacion` | Cablear `run_renewal_bianual_check` a beat (hoy dead-code); generar nueva Declaración Básica anual automatizada |
| **Notificación incidentes a INCIBE-CERT vía LUCIA (CCN-STIC 817)**, inmediata Alto/Muy Alto/Crítico | **2** | Integración LUCIA REAL: `lucia_federation.submit_incident` (lucia_federation.py:190-321) hace `httpx.post` OAuth real a `lucia.ccn-cert.cni.es/api`, con fallback honesto `pending_credentials` + artefacto JSON canónico CCN-STIC 845. **PERO `submit_incident` NO se invoca desde ningún flujo** (grep: solo definición + README). El decision tree `evaluate_routing` (ccn_cert_decision_tree.py:59-105) produce `action_required="auto_submit_lucia"` como **string JSONB que nadie ejecuta**. `create_incident` (incident_workflow_service.py:131-188) inserta `notificado_lucia=false` y no dispara nada. Sin deadline-clock 24h/72h activo | ✓ (artefacto JSON 845, sólo si se llamara) | ✗ | ✗ | ✓ (decision tree usa severity + lucia_enabled + tier) | parcial (cliente VE incidents resolved/closed; NO botón "notificar LUCIA") | **Cablear `submit_incident` al alta de incidente Alto/Crítico**; reloj de deadline 24h/72h; audit_log de la notificación; gestión credenciales cliente |
| **Revisión de SoA ante cambios de alcance** (re-trigger categorización+SoA) | **2** | Motor materialidad REAL: `materiality_engine.assess` (materiality_engine.py:40-120) árbol determinista, devuelve `required_workflows=["recategorization","ar_rebaseline","dda_update",...]`. **Pero son etiquetas-string, NO se orquestan.** `open_recategorization` (recategorization_service.py:8-23) y `open_extraordinary_audit` (extraordinary_audit_service.py:8-23) son **stubs puros** (return dict, sin lógica). API (api.py:249-287) persiste `RecategorizationRow status="pending", new_dda_id=None, analysis_report_id=None` — fila de tracking, **NO re-ejecuta M01 categorización ni regenera SoA/DdA**. Único cascade cableado: `maybe_dispatch_adenda_on_materiality_assessed` (M14, adenda comercial, no SoA ENS). `reschedule_on_substantial_change` (audit_schedule_service.py:115-165) sí reprograma auditoría real | parcial (E-046/E-615 listados, no generados) | ✗ | ✗ | ✓ (materiality MINOR/RELEVANT/MATERIAL) | ✓ admin `/changes` | Orquestación real de `recategorization`/`ar_rebaseline`/`dda_update`: re-correr categorización + regenerar SoA/DdA; hoy sólo tracking |
| **Tiers de retainer** (R_MICRO…R_CRITICAL) | **1 (catálogo+precio) / 2 (billing recurrente)** | Tiers NO nominales: `CADENCES_BY_PROFILE` (retainer_service.py:36-97) 5 tiers con cadencias reales por actividad; `SLA_BY_PROFILE` (99-105), `HOURS_BY_PROFILE` (107-113); `generate_annual_activities` (253-303) materializa actividades por tier (real). Precio real en `precio_mensual` (create_retainer 138-175) y por tier en `pricing_catalog` (`_get_tier_price` billing_integration.py:46-60). Billing **manual** real: endpoint `POST /retainer/generate-monthly-invoice` (api.py:460-479) → `generate_monthly_invoice` (826-879) → M15 `BillingService.generate_invoice` (real, correlativo + Verifactu hash + IVA/IRPF). **Billing recurrente automático = STUB** (beat task log-only, ver hallazgo transversal) | ✓ factura real (M15 + QR Verifactu) | n/a | parcial (M15 Verifactu hash, no audit_log R6) | ✓ tiers reales (cadencia/SLA/horas/precio) | ✓ admin `/retainers`, `/retainers/churn-risk`, cliente `/retainer-checkin` | Cablear ciclo mensual automático al beat (hoy dispara stub); 3 implementaciones reales sin wiring |

---

## audit_log R6 (hash-chain) — estado por motor de mantenimiento

- m19 `cliente_continuidad_api` **sí** emite audit_log 3-way OR (`_emit_audit_log`, cliente_continuidad_api.py:144-174).
- m19 `incident_workflow_service` + `incident_admin_api` → **NO** emiten audit_log (grep limpio en admin_api). Las transiciones de estado del incidente (CCN-STIC 817) quedan fuera de la cadena inmutable.
- m27 (DPC anual, bienal, LUCIA, renewal) → **NO** emiten audit_log (grep `audit_log` en m27 = 0 ficheros).
- m23/m15 billing → confían en el hash-chain Verifactu de la factura (M15), no en audit_log R6.

Conclusión c: la mayoría del ciclo vivo de mantenimiento (incidentes, DPC, bienal, LUCIA, recat) **no deja rastro en el audit_log R6 hash-chain**.

---

## Distinción hueco-normativo-real vs hueco-de-producto

**Huecos NORMATIVOS REALES (faltan controles que el ENS exige en la fase de mantenimiento):**
1. **Revisión anual del análisis de riesgos** — ausente por completo (clase 3). El RD 311/2022 (op.pl.1 + ciclo de mejora continua) exige revisión/re-aprobación periódica del AR; no existe motor. Riesgo de no-conformidad en auditoría bienal.
2. **Autoevaluación de seguimiento anual (CCN-STIC 808)** — ausente por completo (clase 3).
3. **Revisión por la Dirección formal + tratamiento de NC** — solo existe el proxy DPC (atestación de continuidad), no un acta de revisión por la dirección con NC/acciones correctivas (clase 2).

**Huecos de PRODUCTO (el control está construido pero no se ejecuta/cablea):**
4. **LUCIA / INCIBE-CERT** — la integración es código real production-grade (httpx OAuth + payload 845 + fallback), pero es **dead-code**: ningún flujo llama `submit_incident`, y el "auto_submit_lucia" es un string sin ejecutor. Para Alto/Crítico la notificación inmediata simplemente no se dispara.
5. **Renovación bienal — campaña recert** — `run_renewal_bianual_check` es real pero sin beat/API → no se auto-dispara (la alerta T-90 sí funciona, esa parte es clase 1).
6. **SoA ante cambios de alcance** — el motor de materialidad es real y determinista, pero los workflows que recomienda (`recategorization`, `ar_rebaseline`, `dda_update`) no se orquestan; recat/extraordinary son stubs + fila de tracking.
7. **Billing recurrente del retainer** — TRES implementaciones reales (`generate_monthly_invoices_for_all`, `run_retainer_billing_cycle`, endpoint manual) pero el **único camino automático (beat) es un stub log-only**. Sólo se factura si Marcos pulsa el botón por proyecto.

---

## Veredicto de prioridad: ¿bloquea que el retainer entregue mantenimiento ENS real?

**SÍ, parcialmente — el retainer NO entrega hoy un ciclo de mantenimiento ENS ejecutado automáticamente.** Estado neto:

- **Lo que funciona automático**: alerta T-90 bienal (art.31), alerta aniversario DPC anual (art.25), CCN-STIC scrape, drift weekly (si se cablea — ojo, varias tasks reales no están en `beat_schedule`).
- **Lo que requiere clic manual de Marcos** (real pero no automático): factura mensual del retainer (per-proyecto), generar actividades anuales, ejecutar actividad programada.
- **Lo que NO existe o es dead-code** (bloqueante para "mantenimiento vivo"): revisión anual del AR, autoevaluación 808, notificación LUCIA inmediata, campaña recert auto, re-SoA ante cambio de alcance.

**Bloqueantes de mayor severidad (producto, arreglo de wiring relativamente acotado):**
- P1 · Cablear billing recurrente al beat (reemplazar stub `generate_monthly_invoices` por `run_retainer_billing_cycle` o `generate_monthly_invoices_for_all`). Sin esto el retainer no factura solo.
- P1 · Cablear `update_all_renewal_statuses` al servicio real (hoy el reloj T_MINUS_* nunca avanza por beat).
- P1 · Cablear `submit_incident` LUCIA al alta de incidente Alto/Crítico (obligación legal de notificación inmediata).
- P2 · Cablear `run_renewal_bianual_check` al beat.
- P2 · Orquestar `recategorization`/`ar_rebaseline`/`dda_update` ante cambio material.

**Bloqueantes normativos (requieren construir motor, no solo wiring):**
- P1-normativo · Revisión anual del análisis de riesgos (re-aprobación).
- P2-normativo · Autoevaluación de seguimiento anual CCN-STIC 808.
- P2-normativo · Acta de Revisión por la Dirección + gestión de NC.
- Transversal · Emitir audit_log R6 en incidentes/DPC/bienal/LUCIA/recat (hoy fuera de la cadena inmutable).
