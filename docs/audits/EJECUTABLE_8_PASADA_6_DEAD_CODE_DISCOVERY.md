# Ejecutable 8 · Pasada 6 · Dead Code Discovery

**Fecha**: 2026-05-30 · **Branch**: `fix/radar-sector-widen-and-cleanup-20260529`
**Metodología**: cross-reference grep cuantitativo + verificación file-by-file (apertura real). CERO assumptions. NO fix-forward (findings TAGGED para Pasada 16).
**Entorno**: WSL2 Ubuntu, repo `/home/usuario/fulkro`.

---

## 0. Resumen ejecutivo

El repositorio está **notablemente limpio de dead code estructural**. Limpiezas previas (Sesión 10 agentes, README S10.5 project-mock, radar-v9 archive) están EFECTIVAMENTE aplicadas en disco. Los "sospechosos" del briefing resultan ser:
- **copilot/copiloto/copiloto-cliente** → NO dead code, sino **inconsistencia de naming** (3 dirs todos usados).
- **project-mock.ts** → YA ELIMINADO.
- Dead code real residual: **scripts demo/load-test one-off** + **rama git `fulkro-1.0` obsoleta** + **drift documental ADR**.

---

## 1. Backend orphans — routers no montados

**Verificación**: `comm -23 <(ls motors) <(grep app.motors main.py)` → **salida vacía**. Los 42 dirs de motor están TODOS referenciados.

| Hecho | Evidencia |
|-------|-----------|
| 41 ficheros `api.py` en motors | `find backend/app/motors -name api.py` = 41 |
| 181 `include_router` en main.py | `grep -c include_router backend/app/main.py` = 181 |
| 42 módulos motor referenciados | `grep -oE 'app.motors.[a-z0-9_]+' main.py \| sort -u` = 42 |
| `m26_backup` montado vía `backup_router` | `main.py:402` |
| `m29_client_messaging` usa `api_admin.py`+`api_client.py` (NO api.py) — montados | `main.py:291,294` |
| `m_compliance` usa 6 `*_api.py` (dpa/ropa/rgpd/compliance_admin/cookies/measure_translation) — montados | `main.py:58,62,65,68,71,106` |
| `m_legal` montado (no es "dead" pese a dormant cross-compliance) | `main.py:33` import + `main.py:385` include |

**CONCLUSIÓN**: **0 motores con router huérfano**. Ningún `api.py` queda sin montar.

---

## 2. Agentes — deprecated/reservado vs ficheros físicos

**Registry** (`backend/app/agents/registry.py`): 31 IDs. Activos: A4,A6,A11,A12,A14,A17,A18,A19,A20,A21,A27,A31 (12) + A2 scaffolding. A15/A26 `externalized_to_motor` (m23_retainer). A9/A10 `reservado`. 14 deprecated.

**Ficheros físicos** (`agent_*.py`): 13 (.py) + 1 dir (`agent_14_copiloto`):
`agent_02_pliegos, agent_04_redactor, agent_06_contratos, agent_11_auditor_virtual, agent_11_wrapper, agent_12_coach_cliente, agent_17_cualificador, agent_18_reunion, agent_19_propuestas, agent_20_negociacion, agent_21_api, agent_21_discrepancias, agent_21_service, agent_27_clasificador, agent_31_enriquecedor_dda`.

**Mapping `_AGENT_CLASSES`** (`agents/api.py:23-49`): IDs 2,4,6,11,12,14,17,18,19,20,21,27,31 → clase física. Coincide exactamente.

| Verificación | Resultado |
|--------------|-----------|
| Deprecated IDs (1,3,5,7,8,13,16,22,23,24,25,28,29,30) | **SIN fichero `agent_*.py` físico** (ya limpiados) |
| A15/A26 externalized | viven en `m23_retainer.agent_15_vigilancia` / `m23_retainer.agent_26` (registry.py:133,197), NO en `agents/` |
| Prompts huérfanos | `agents/prompts/` = 13 ficheros, todos corresponden a clase activa. **0 huérfanos** |
| `agent_11_wrapper.py` usado | `audit_dry_run_service.py` + `main.py` |
| `agent_21_api/service` usado | `main.py` + `test_agent_21_service.py` |
| `agent_21_discrepancias.DetectorDiscrepanciasAgent` (legacy LLM wrapper) | referenciado en `workflows_simple.py`, `m11_copiloto/inline_agents_api.py`, `_AGENT_CLASSES`. Registry lo marca "preservado para reasoning narrativo opcional" → **KEEP-JUSTIFIED** (no es A21 determinista real, que es `agent_21_service`) |

**CONCLUSIÓN**: **0 agentes huérfanos, 0 prompts huérfanos**. Cleanup Sesión 10 verificado efectivo.

---

## 3. Frontend orphans — copilot/copiloto + project-mock

### 3.1 project-mock.ts → YA ELIMINADO ✅
`ls frontend/lib/project-mock.ts` → **No such file or directory**. README S10.5 cumplido.

### 3.2 copilot/copiloto/copiloto-cliente → INCONSISTENCIA NAMING, NO dead code

| Dir | Componentes | Importado por | Estado |
|-----|-------------|---------------|--------|
| `components/copilot/` | CitationPopover, CopilotComposer, CopilotMessage(s), CopilotPanel, QuickActionButtons | `app/(admin)/layout.tsx` (CopilotPanel) | **USADO** (UI copiloto admin) |
| `components/copiloto/` | CopilotoDock.tsx | `components/layout/ClientPortalChrome.tsx` | **USADO** (dock compartido) |
| `components/copiloto-cliente/` | CopilotoClienteBottomRight.tsx | `app/(client-portal)/client-portal/workflow/page.tsx` | **USADO** (widget bottom-right) |
| `components/admin/copilot/` | CopilotGuidedFlow, HelpModal, OnboardingTourAdmin, phaseGuides.ts | (admin flows) | **USADO** |

**HALLAZGO**: convivencia `copilot` (inglés, admin chat panel) vs `copiloto`/`copiloto-cliente` (español, dock/widget cliente) es **DEUDA DE NAMING / fragmentación**, NO dead code. Riesgo de confusión de mantenimiento. Acción Pasada 16: KEEP funcional, considerar consolidación de naming (low priority, NO bloqueante).

---

## 4. Scripts / migraciones obsoletas

### 4.1 Scripts archivados (correcto)
`backend/scripts/_archive/`: `generate_propuesta_pdf.py` + dir `radar_v9/` (radar_orphan_cleanup, radar_rescore_dry_run, radar_sonnet_vs_haiku_comparison, rescore_radar_leads + README). Archive efectivo ✅.

### 4.2 Scripts demo/load-test NO referenciados (candidatos archivo)
`grep` en tests/.github/docs → **0 referencias** para:
- `demo_s8_paso1..6,paso8` (~7 scripts) + `demo_s7_paso7_full.py` + `run_all_demos.sh`
- `load_test_100_magic_links.py` + `load_test_50_retainers_billing.py`

Son scripts one-off de demo/carga histórica. **Candidatos a `_archive`** (no bloqueante).

### 4.3 Migraciones radar_widen DUPLICADAS (ligado a drift Alembic — Pasada 16)
210 migraciones. Detectadas DOS migraciones widen del mismo concepto:
- `radar_widen_sector_text_001_widen_llm_sector_to_text.py` (tracked)
- `radar_widen_llm_freetext_text_001_widen_persona_canal_company_sector.py` (**UNTRACKED**, nueva en branch actual)
Más `sane_ens_radar_schema_widen_001.py` + `audit_log_accion_widen_001.py`.

Esto se cruza con el **drift Alembic BLOQUEANTE #1** (BD live stampeada 3 revs pre-merge). **SOLO DOCUMENTO** — reservado a Pasada 16. NO toco BD ni migraciones.

---

## 5. Cross-branch divergence

`git rev-list --left-right --count`:

| Comparación | Izq (atrás) | Der (adelante) | Lectura |
|-------------|-------------|----------------|---------|
| `main...fix/radar-sector-widen-and-cleanup-20260529` | 0 | **13** | branch actual = main + 13 commits, fast-forward limpio |
| `radar-v9...fix/...` | 27 | 108 | branch actual diverge fuerte de radar-v9 |
| `main...radar-v9` | 95 | 27 | radar-v9 tiene 27 commits no en main + main 95 no en radar-v9 |
| `main...fulkro-1.0` | 230 | **1** | **`fulkro-1.0` OBSOLETA**: 230 commits detrás de main, solo 1 adelante |

**HALLAZGO**: rama `fulkro-1.0` es **rama muerta candidata a borrado** (230 detrás, 1 adelante — claramente abandonada). `radar-v9` mantiene divergencia activa. NO mergeo nada.

---

## 6. ADRs — drift documental

`ls docs/architecture/ADR-*` → **exactamente 9 ficheros físicos**: ADR-046 a ADR-054.
Pese a que CLAUDE.md cita ADR-001, ADR-003, ADR-009..014, ADR-020, ADR-025, ADR-031, ADR-038, ADR-046..054. **ADR-001..045 NO existen en disco** (drift documental — referencias en CLAUDE.md sin fichero respaldo). Confirma hallazgo Pasada 5.

---

## 7. Findings priorizados Pasada 16

Ver array `findings`. Resumen: 0 dead code crítico backend. Acciones mayoritariamente `archive` (scripts demo) / `delete` (rama fulkro-1.0) / `documentar` (drift ADR + naming copilot). Drift Alembic/migraciones widen = **reservado Pasada 16 #1**.