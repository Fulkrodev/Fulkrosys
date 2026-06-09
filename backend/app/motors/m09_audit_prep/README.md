# Motor 9 · Audit Preparation (M9-A)

Auditor virtual interno · prepara cliente para auditoría ENAC real generando checklist, coaching, matriz 99 + dossier PDF master compilando todo el trabajo previo (M01 + M02 + M03 + M04 + M05 + M07 + M08). Permite al cliente llegar a la auditoría con readiness scoring + dossier consolidado.

## Funcionalidades

- **Checklist service** (`checklist_service.py`) genera checklist pre-auditoría con items rastreables (state · evidence linked · gap residual).
- **Internal auditor** (`internal_auditor.py`) auditor virtual ejecuta checks determinísticos + LLM-enriched sobre el proyecto.
- **Coaching** (`coaching.py`) prepara cliente con tips contextuales y best-practices ENS por área detectada débil.
- **Matriz 99** (`matriz_99.py`) genera matriz comparativa medidas Anexo II (99 fila/col) con estado per cliente.
- **Dossier generator** (`dossier_generator.py`) compila dossier de evidencias estructurado per medida.
- **PDF master generator** (`pdf_master_generator.py`) PDF consolidado pre-auditoría (categorización + DdA + gaps closed + obligations completed + risks treated + evidencias + pentests + matriz 99).
- **Cleanup service** (`cleanup_service.py`) post-auditoría limpia artefactos temporales + archive runs.
- **Readiness scoring** integrado en checklist (% coverage per área ENS).
- **Addendum v22** (`addendum_v22.py`) extensiones multi-norma (DORA · NIS2).

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 3.548 |
| Files | 10 |
| Status | production-grade |
| Tests | `backend/tests/motors/m09_audit_prep/` |
| API prefix | `/api/v1/audit-prep/*` |
| RBAC | Cat A · Marcos-only (`require_owner`) |

## Key files

- `api.py` · endpoints HTTP (run + checklist + readiness + dossier + matriz + cleanup)
- `checklist_service.py` · `get_run` + checklist generation per project
- `internal_auditor.py` · auditor virtual core (determinístico + LLM)
- `coaching.py` · tips contextuales cliente
- `matriz_99.py` · matriz comparativa 99 medidas
- `dossier_generator.py` · estructurado per medida
- `pdf_master_generator.py` · PDF consolidado pre-auditoría
- `cleanup_service.py` · post-auditoría archive + cleanup
- `addendum_v22.py` · extensiones multi-norma MB-9.bis

⚠️ NO existe `service.py` único · scope split en services especializados (checklist + auditor + coaching + dossier + cleanup + pdf_master).

## DB tables

N/A motor-specific (api.py sin `__tablename__` declarations) · usa modelos compartidos via integrations con M08/M24.

## Cross-motor integration

- **Inbound** (motores que consumen M09):
  - M21 Diagnosis (incluye readiness scoring en diagnosis dashboard)
  - M25 Lifecycle (audit-prep como milestone del lifecycle ENS cliente)
  - M27 Conformity (informe conformidad consume readiness M09)
- **Outbound** (motores que M09 consume):
  - M08 Verification (pentest results en dossier)
  - M24 IDMS (Information Documentation Management System · referencias cruzadas)
- **LLM agents**: A20 Audit Prep + internal_auditor LLM-enriched checks

## ADRs referenced

(no ADRs referenciados directamente en código motor)

## Cement OPS

Motor cumulative aggregator · consume outputs de 7+ motores upstream (M01/M02/M03/M04/M05/M07/M08) para producir dossier consolidado. Pattern services-specialized (no monolithic). PDF master es entregable cliente clave pre-ENAC · debe ser determinístico y reproducible (mismo input → mismo PDF).
