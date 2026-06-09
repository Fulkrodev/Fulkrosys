# Ejecutable 8 · Batch 2 · Audit del gap "Cablear FASE 0 gobierno al recorrido"

> **Estado: AUDIT CERRADO · IMPLEMENTACIÓN EN PAUSA** (decisión Marcos 2026-06-01).
> Se pausa hasta que el rebuild del RADAR (otra ventana, rama `radar-v3-rebuild`)
> esté cerrado y estable. Esta rama (`batch2-fase0-recorrido`) vive en un
> **git worktree aislado** en `/home/usuario/fulkro-portales`. NO mergear hasta
> que Marcos lo indique. La próxima sesión **arranca leyendo este fichero**.
>
> Base del worktree: commit `ed3ab619` de `radar-v3-rebuild` (sin arrastrar el
> working tree sucio del radar). Solo lectura realizada · 0 código de producción tocado.

---

## 1. Diagnóstico (preciso, con file:line)

**El composer de gobierno EXISTE, completo y puro:**
- `backend/app/motors/m17_planning/fase0_governance.py:49` ·
  `compute_fase0_governance_state(db, project_id)` → dict JSON-serializable:
  `steps[]` (kickoff→alcance→roles→comité→plan), `next_step`, `progress_pct`,
  `fase0_completa`, `branch`, `categoria`.
- **Branch por categoría ya implementado** (`fase0_governance.py:58`): `BASICO`
  vs `MEDIO_ALTO`. Comité (E-003, WBS-004) solo MEDIA/ALTA (`:40-41`).
  Separación RSeg≠RSis bloquea paso roles si obligatoria y no conforme
  (`:106-111`). Cadencia comité (`:112-115`).
- Reúne lo existente sin duplicar: tabla `documents` (E-155 alcance / E-002
  roles / E-003 comité / E-150 plan), `m30 validate_role_segregation`,
  `m_meetings evaluate_comite_cadence`.
- Expuesto vía endpoint propio: `backend/app/motors/m17_planning/api.py:156`
  `GET /planning/projects/{id}/fase0-governance` · **admin-only** (router
  `dependencies=[Depends(require_owner)]`, `api.py:22`). Tests:
  `backend/tests/motors/m17_planning/test_fase0_governance.py`.

**El cerebro del copiloto proactivo NO lo usa (gap central):**
- `backend/app/motors/m11_copiloto/workflow_state_scanner.py:546` ·
  `compute_workflow_state` alimenta **6 consumidores** del recorrido proactivo:
  `/copilot/hint` admin (`m11_copiloto/api.py`), coach cliente
  (`m11_copiloto/portal_api.py`), `m11_copiloto/nudge_scheduler.py`,
  `agents/agent_14_copiloto`, simulacro pre-ENAC (`m09_audit_prep/
  simulacro_pre_enac_service.py`).
- Emite acciones desde catálogo **estático por fase** (`_PHASE_ACTIONS`,
  `workflow_state_scanner.py:109`) — 1 acción admin + 1 cliente por cada una de
  las 10 fases. Fases tempranas NO mencionan gobierno:
  - `PRE_VENTA` → solo `prepare_contract` (`:114`)
  - `ONBOARDING` → `review_onboarding_responses` / `complete_onboarding` (`:130,143`)
  - `ADECUACION` → `finalize_categorization` / `draft_dda` (`:215,226`)
- `compute_workflow_state` **nunca llama** a `compute_fase0_governance_state`
  (grep cross-codebase = 0 cruces).
- `_detect_blockers` (`workflow_state_scanner.py:451`) NO contempla separación
  de roles ni cadencia del comité — solo DdA-firma (IMPLANTACION), pentest-auth
  (ALTA) y review-ENAC (CONFORMIDAD).

**El frontend tampoco lo consume:**
- `grep "fase0-governance" / "Fase0" / "gobierno"` en `frontend/` =
  **0 consumidores reales** (hits = `m28_change_governance` y comentario
  sign-flow, no relacionados). **Endpoint huérfano de UI.**

**Conclusión:** el composer calcula exactamente "kickoff→alcance→roles→comité→
plan, adaptado a categoría" — literalmente lo que pide la visión ("reusando el
branch de `compute_fase0_governance_state`") — pero vive en un endpoint admin
aislado que **ningún recorrido consume**. Copiloto proactivo, timeline
cronológica y guía cliente están ciegos al gobierno.

**¿Migración? NO.** Ambos son composers read-only sobre tablas existentes
(`documents`, `projects`, m30 contacts, m_meetings actas). Integrar =
composición pura-funcional, cero schema change. (Si el plan detallado revelara
necesidad de migración → PARAR y avisar a Marcos, NO crearla. No se ve necesaria.)

---

## 2. Opciones de integración (A/B/C) con file:line

| Opción | Qué hace | Punto de inyección | Trade-off |
|---|---|---|---|
| **A · Inyectar en el scanner** | `compute_workflow_state` llama a `compute_fase0_governance_state` en fases tempranas; si gobierno incompleto, el `next_step` (roles/alcance/comité/plan) sustituye/precede la acción genérica + emite blockers (separación/cadencia). | `workflow_state_scanner.py:570` (tras `phase_actions`) + `_detect_blockers:451` | Máxima cobertura: los 6 consumidores heredan gobierno gratis (admin + cliente + nudge). Acopla el scanner (hoy dependency-light, raw SQL) a m30 + m_meetings. |
| **B · Campo nuevo en WorkflowState** | Añadir `fase0_governance: dict \| None` a `WorkflowState` sin tocar las acciones por fase; cronológica + copiloto lo renderizan como sección aparte. | `WorkflowState` dataclass `workflow_state_scanner.py:77` + `to_dict` | No altera la lógica de acciones existente (menor riesgo de regresión en tests del scanner). Frontend debe renderizar el bloque nuevo explícitamente. |
| **C · Solo frontend** | Panel "FASE 0 · Gobierno" en el recorrido admin que consume el endpoint existente `/fase0-governance`. Backend intacto. | `frontend` (admin `/projects/[id]/workflow` o `/summary`) | Cero riesgo backend. PERO copiloto proactivo y cliente siguen ciegos (endpoint admin-only) → NO cumple "copiloto proactivo señalando siguiente paso". |

---

## 3. Decisiones de producto PENDIENTES del criterio de Marcos

1. **Opción A / B / C** (cuál de las tres rutas de integración).
2. **¿Admin-only o también cliente?** El endpoint es `require_owner`. ¿El
   cliente ve el progreso de gobierno (R29) o es interno de Marcos (R30)?
   (A lo daría a ambos vía `role_filter`; C es admin-only.)
3. **¿Qué fases activan gobierno?** Cruza PRE_VENTA→ONBOARDING→ADECUACION (el
   "Plan de adecuación" E-150 = fase ADECUACION). ¿Surfacear mientras
   `fase0_completa=False` independientemente de la fase, o acotarlo a tempranas?
4. **¿Dónde se renderiza?** La entrada admin hoy cae en `/summary`
   (`projects/[id]/page.tsx:8` redirect), no en `/workflow`. ¿Panel/sección de
   gobierno en summary, en workflow, o ambos?

---

## 4. Scope de suite acotado (cuando se implemente · SIN radar/m13)

El árbol principal `radar-v3-rebuild` está mid-refactor (radar m10 + m13). En el
worktree se corre SOLO el scope del gap:
- `backend/tests/motors/m11_copiloto/` (14 ficheros · clave
  `test_workflow_state_scanner.py`, `test_copilot_hint_endpoints.py`,
  `test_nudge_scheduler.py`, `test_portal_copilot_tenant_context.py`)
- `backend/tests/motors/m17_planning/` (6 ficheros · clave `test_fase0_governance.py`)
- `backend/tests/core/` (`test_workflow_state.py`, `test_workflow_phase_10.py`,
  `test_workflow_gates*.py`, `test_workflow_blocking.py`)

Runner aislado: intérprete `/home/usuario/fulkro/.venv/bin/python` (deps) con
`cwd=/home/usuario/fulkro-portales` (source = worktree aislado · NO editable
install → el cwd decide el origen del código). NO correr suite completa.

---

## 5. Disciplina de worktree (recordatorio operativo)

- El shell **resetea cwd a `/home/usuario/fulkro` tras cada comando** → CADA
  bash debe empezar con `cd /home/usuario/fulkro-portales &&` y confirmar `pwd`.
- NO tocar Alembic ni DB (migración del radar `radar_v3_drop_ens_machinery_001.py`
  sin aplicar en el árbol del radar · no existe en este worktree).
- NO mergear · NO tocar el árbol del radar · el merge lo hace Marcos cuando el
  radar esté cerrado y estable.

---

## 6. FASE 1 IMPLEMENTADA (2026-06-01 · rebase sobre `radar-v3-pr`)

**Decisiones cementadas (Marcos):** Opción A (inyectar en scanner · prepend
urgent) · **solo admin** · fases `{PRE_VENTA, ONBOARDING, DIAGNOSTICO,
ANALISIS_RIESGOS, ADECUACION} AND fase0_completa=False` · render `/workflow`
vía `CopilotoAdminSidebar` (el `next_step` llega gratis por `/copilot/hint`).

**Rutas REALES verificadas** (no de memoria · leído propósito de cada page):
- kickoff → `/admin/projects/{id}/onboarding` (`OnboardingAdminPanel` · arranque)
- alcance (E-155) → `/admin/projects/{id}/documents` (IDMS)
- roles (E-002) → `/admin/projects/{id}/equipo` (`EnsRoleAssignModal` · **NO `/roles`**, que es solo topología)
- comite (E-003) → `/admin/meetings` (m_meetings · top-level)
- plan (E-150) → `/admin/projects/{id}/plan` (`PdaGeneratorButton`)

**Cambios (backend puro · cero frontend · sin migración):**
- `m11_copiloto/workflow_state_scanner.py`: `_FASE0_PHASES` + `_GOV_STEP_URL` +
  `_GOV_STEP_LABEL` + `_build_governance_hint()`; inyección en
  `compute_workflow_state` (import lazy de `compute_fase0_governance_state` ·
  prepend urgent en `next_admin_actions` · solo admin); param `governance` en
  `_detect_blockers` (default None · additive) + 2 blockers nuevos (m30
  separación, m_meetings cadencia).
- Tests: `test_workflow_state_scanner.py` (1 actualizado + 5 nuevos),
  `test_copilot_hint_endpoints.py` (1 actualizado).
- Suite acotada **388 passed, 0 failed** (m11_copiloto + m17_planning + core).

## 7. FASE 2 (DIFERIDA · pendiente · NO implementada en este batch)

Los 2 blockers de gobierno (separación RSeg≠RSis · cadencia comité) **ya se
emiten** en `WorkflowState.blockers` (correctos para consumidores no-UI:
`nudge_scheduler` + `simulacro_pre_enac_service`), pero **NO se exponen en UI**.
FASE 2 = solo exponerlos:

1. **Backend:** extender `WorkflowHintResponse` (`m11_copiloto/api.py:329`,
   `get_copilot_hint_admin`) con `blockers: list[...]` opcional, poblado desde
   `state.blockers` (filtrar a `waiting_on=="admin"` si se quiere solo gobierno).
2. **Frontend:** renderizar esos blockers en
   `CopilotoAdminSidebar.tsx` (en `/admin/projects/[id]/workflow`), junto al
   `next_step`. R30 admin tutor (TooltipENS separación/comité).
3. **Tests:** endpoint hint devuelve `blockers` cuando MEDIA/ALTA con separación
   no conforme; sidebar los pinta.

El backend de los blockers ya está listo desde FASE 1 → FASE 2 es un batch
pequeño (exponer + render). Otra sesión, tras OK de Marcos.

---

## 8. Diagnóstico previo (lead → cuestionario magic-link) · Batch A capa legal

Arquitectura cerrada (Marcos): **Opción A** (proyecto ligero · reusa m16 · sin
migración de `project_id`) · registro **dedicado** de consentimiento (NO
`fulkro_consent_audit_log`, que es de cookies) · base jurídica **interés legítimo
art. 6.1.f** (captación en frío).

Batch A (capa legal) shipped: purpose `DIAGNOSTICO_PRECLIENTE` (m12 · cat F · ttl
14d · no-OTP) + emisión magic-link account-less gated en `create_session`
(`m16 service.py` · default in-portal intacto) + tabla dedicada append-only
`precliente_diagnostic_consents` (`precliente_consent_001` · FK
onboarding_sessions · SIN RLS · GRANT SELECT,INSERT a fulkro_app = append-only) +
texto Art. 13 versionado + endpoints consent + gate (commit 4).

### 🔴 RIESGO RLS account-less (verificar en Batch B · patrón F-18)
`onboarding_sessions` **TIENE RLS** (`e41cd7163c02`) y el flujo account-less del
lead lee la sesión SIN contexto tenant: `authenticate_client_session`
(`client_service.py`) hace `SELECT ... FROM onboarding_sessions WHERE id=:sid`
sin `set_tenant_context`. En prod (`fulkro_app`, RLS activa, sin middleware
tenant) esa query podría ser **ciega** → mismo patrón fail-closed que **F-18**
(resolver/leer antes de setear contexto · ver [[project-ejecutable-8-f18-findings]]).
La tabla de consent es SIN RLS (escritura account-less OK), pero **antes del
envío real al lead (Batch B) hay que verificar empíricamente** que el flujo
account-less de SESIÓN funciona bajo RLS en prod (no solo en tests, donde el
fixture `db` setea `app.current_client_id` → falso verde). Si es ciego, aplicar
el mismo fix F-18 (set_tenant_context derivado de la sesión, o lectura
`SECURITY DEFINER`). NO bloquea Batch A.
