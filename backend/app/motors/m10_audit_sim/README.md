# Motor 10 · Audit Simulation Engine

Auditor virtual ENAC que simula la auditoría real ANTES de la auditoría: evaluación determinista L0-L5 sobre las medidas del Anexo II ENS, anti-alucinación pura (búsquedas SQL reales contra M03/M06/M07/M08, NO LLM).

## Funcionalidades

- **Simulación pre-auditoría** L0-L5 maturity scoring per medida Anexo II.
- **Preguntas auditor virtual** estructuradas per familia (`audit_questions.py` · catalogizadas por familia ENS).
- **AuditSimulatorService** (`audit_simulator.py`) core orchestration con queries reales cross-motor M03 DdA + M06 Document Factory + M07 Evidence + M08 Verification.
- **Filtering preguntas per categoría** sistema (BÁSICA/MEDIA/ALTA → preguntas relevantes).
- **Anti-alucinación**: respuestas extraídas de BD real · NO LLM-generated · readiness gap puro determinista.
- **Familias ENS** mapeadas (`FAMILIA_LABEL`) para presentación cliente-friendly.

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 1.518 |
| Files | 4 |
| Status | production-grade |
| Tests | `backend/tests/motors/m10_audit_sim/` |
| API prefix | `/api/v1/audit-sim/*` |
| RBAC | Cat A · Marcos-only (`require_owner`) |

## Key files

- `api.py` · endpoints HTTP (run simulation + get questions + scoring)
- `audit_questions.py` · `AUDIT_QUESTIONS` + `FAMILIA_LABEL` + helpers per categoría/familia
- `audit_simulator.py` · `AuditSimulatorService` core + `AuditSimError`

⚠️ NO existe `service.py` único · core en `audit_simulator.py`.

## DB tables

N/A motor-specific · usa modelo `AuditSimulationRun` (`backend/app/models/audit_sim.py`). RLS por `audit_simulation_runs`.

## Cross-motor integration

- **Inbound**: M23 Retainer (retainer mensual incluye simulación)
- **Outbound**: M08 Verification (cross-check vuln state)
- **LLM agents**: ninguno (motor determinístico estricto · cement anti-alucinación)

## ADRs referenced

(no ADRs referenciados directamente en código)

## Cement OPS

Invariante anti-alucinación: NUNCA LLM-generated para evaluación L0-L5 · siempre query BD real (anti-alucinación cement institutional ENAC).
