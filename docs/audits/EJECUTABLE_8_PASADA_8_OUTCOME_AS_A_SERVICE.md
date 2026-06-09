# Ejecutable 8 · Pasada 8 · Outcome-as-a-Service Verification

> Filosofía: el cliente **VE RESULTADOS**, el sistema **LLEVA el trabajo** proactivamente (NO es un SaaS de dashboards estáticos donde el cliente opera ENS). Cliente VE/AUTORIZA/FIRMA/RECIBE; NO opera la implantación técnica.
> Verificación empírica por lectura de código + reproducción de errores en `.venv` WSL. Fecha: 2026-05-30.

---

## 0. Veredicto

**Cliente-mínimo VE/AUTORIZA/FIRMA/RECIBE bien implementada: 7/7 fases con RESULTADO visible.** Proactividad cron REAL (Celery beat 23+ tasks). El motor "lleva-fase-por-fase" existe (`workflow_state_scanner.compute_workflow_state`, determinista, 10 fases) + `adaptive_dashboard_service._build_today_actions` + nudges diarios. **PERO** hay fallos silenciosos clave que degradan partes del sistema a "SaaS pasivo" donde debería ser proactivo (coach cliente roto en runtime, SSE realtime degradado a polling).

## 1. Resultado visible per fase del cliente

| Fase cliente | RESULTADO que ve | Motor / componente | Estado |
|---|---|---|---|
| PRE_VENTA | Propuesta PDF (vía outreach email) | m13 proposal_service + m10 proposal_pdf | ✅ |
| CONTRATO | Firma canvas TIER 1 | m14 + m05_signing (`firmas-pendientes`) | ✅ (SSE roto F-08-02) |
| IMPLANTACIÓN | `ClientDashboardV3` (Hero paso X/Y + countdown + `TodayActionsCards`) + plan | `adaptive_dashboard_service._build_today_actions` | ✅ (F-08-01) |
| DRY-RUN | Simulacro en `cumplimiento` aggregator | m09 simulacro_pre_enac | ✅ |
| ENAC AUDIT | `AuditAccompanimentClienteView` read-only | m_audit_accompaniment | ✅ (SSE roto F-08-02) |
| CERTIFICACIÓN | `conformidad` 6 secciones tier-aware | m27 | ✅ |
| RETAINER | `retainer-checkin` | m23 + m_compliance_monitor | ✅ (drift ruta F-08-04) |

→ **7/7 fases con resultado visible.**

## 2. Proactividad (lo que se dispara solo)

- **2.A · Cron REAL** (`core/celery_app.py`, 23+ tasks, stub graceful): backup m26 · retainer m23 · evidence-freshness m07 06:00 **(STUB, F-08-03)** · compliance daily/weekly/monthly/quarterly (crea `ComplianceAlert` reales) · cloud-connectors · **coach-nudges m11 09:15 REAL** · client-inactivity · churn · m13 auto-import-radar-leads REAL · m27 biannual/dpc.
- **2.B · nudge_scheduler**: `compute_pending_nudges` + `dispatch_nudges` usa `description_cliente` correcto — **funciona**.
- **2.C · Alertas anticipatorias**: m_compliance_monitor REAL (self-monitoring FULKRO dogfooding) · m07 freshness **STUB** · M18 `alert_service` existe pero **m07 no lo invoca** (F-08-03).
- **2.D · SSE dispatcher**: in-memory + `event_id` + ring-buffer + Last-Event-ID; `CLIENTE_EVENT_TYPES` + `event_matches_audience` cubre workflow/m01/m02/m17.plan/cloud-remediation/chat/pentest/notification. **GAP: `signing.*` + accompaniment NO incluidos** (F-08-02).

## 3. ¿Lleva al cliente fase por fase? — PARCIAL

- Dashboard `today_actions` **FUNCIONA**; nudges diarios **FUNCIONAN**.
- Coach `/coach` + `/coach/next-step` **ROTO** (F-08-01): `AttributeError` silencioso → cliente siempre ve "Todo al día". El copilot **admin** (`/copilot/hint`) SÍ funciona — asimetría runtime.
- No hay trigger event-driven on-phase-change proactivo (F-08-05); depende del cron diario.

## 4. Boundaries de inteligencia

- **Deterministas (R1)**: workflow_state_scanner, today_actions, gap engine, detector pliegos, next-step O(1).
- **LLM acotado (R2/R3, temp ≤ 0.2)**: `/coach` RAG, propuesta PDF, outreach.
- **Límite cliente-mínimo**: cap priority HIGH, cooldown 24h, NUNCA autoría ENS por el cliente.
- **Autonomía del sistema**: auto-import radar leads / auto-resolve / recurring-billing. Firma + autorización pentest **requieren al cliente** (ADR-014/020).

## 5. Hallazgos TAGGED → Pasada 16

| ID | Sev | Hallazgo | Acción Pasada 16 |
|----|-----|----------|------------------|
| **F-08-01** | HIGH | Coach cliente `/coach` + `/coach/next-step` rotos: `ActionHint` no tiene `cliente_description` ni `template_id` → `AttributeError` silencioso (except bare), siempre "Todo al día" | `portal_api.py:330-332` usar `top.description_cliente`, eliminar/mapear `top.template_id`; revisar L481; quitar except bare o loguear. Test: fase IMPLANTACIÓN devuelve acción no-nula |
| **F-08-02** | HIGH | SSE realtime cliente falla para `signing.*` y `m_audit_accompaniment`: dispatchados por m05 pero NO en `CLIENTE_EVENT_TYPES` → certificación + firmas-pendientes degradan a polling 30s | Añadir `signing.requested/signed/declined` + eventos accompaniment a `CLIENTE_EVENT_TYPES` (`core/sse_dispatcher.py`) + rama `event_matches_audience` |
| **F-08-03** | MEDIUM | `m07 check_expiring_evidence` STUB: no consulta `fecha_caducidad` ni alerta a M18 | Query Evidence `fecha_caducidad < now+30d` en `m07_evidence/tasks.py` + push M18 EscalationService (`evidencia_critica_caducada`; infra existe) |
| **F-08-04** | LOW | Drift ruta: `adaptive_dashboard_service` enlaza `retainer-offer` inexistente (real: `retainer-checkin`) | `adaptive_dashboard_service.py:339` corregir href |
| **F-08-05** | LOW | No hay trigger event-driven on-phase-change proactivo; depende del cron diario | Suscribir consumidor a `phase_changed` (trigger ya existe) → nudge inmediato. NO crítico pre-piloto |

## 6. Commands unavailable (honestidad)

- No ejecuté pytest m11/m07/m05 end-to-end (verificación por lectura + repro `AttributeError` en venv).
- No leí cuerpo de m27 biannual/dpc alert tasks (solo registro `beat_schedule`).
- No verifiqué BD live con proyectos en fases intermedias (DB drift reservado Pasada 16).

## Conclusión

La **columna proactiva del sistema es sólida** (cron real 23+ tasks + nudge_scheduler + workflow_state determinista + cliente-mínimo 7/7 fases con resultado visible), pero **dos fallos silenciosos HIGH** (coach cliente roto F-08-01, SSE realtime degradado F-08-02) hacen que partes del producto se comporten como SaaS pasivo donde el diseño promete proactividad. Ambos son fixes acotados de runtime → Pasada 16.
