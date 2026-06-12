# Motor 8 · Verificación Técnica (v5.1)

Auditor virtual de seguridad técnica para ENS. Orquesta pentest auto-trigger + scan cloud + análisis ZFP (Zero False Positive engine) + MITRE ATT&CK mapping + handoff a pentester externo certificado CPSTIC. Motor MÁS GRANDE de FULKRO (13.8K LOC · 56 files · 6 subdirs).

## Funcionalidades

- **Verification runs** orchestración multi-fase (`create_run` + auto-derive scope vía `scope_deriver.py`).
- **Pentest auto-trigger** (`pentest_auto_trigger.py` + `pentest_auto_trigger_api.py` + `pentest_auto_trigger_events.py`) dispara pentest cuando se cumplen condiciones (vulns críticas · review window · cliente policy).
- **Cloud orchestrator** (`cloud_orchestrator.py`) coordina scans cloud (AWS/Azure/GCP) vía scanner adapters MCP (Prowler/ScoutSuite). *(NOTA #22: NO usa SSH ni "LUCIA" — no existen en m08; LUCIA es la notificación de incidentes de m19/m27, otra cosa.)*
- **ZFP engine** (`zfp_engine.py`) Zero False Positive deduplication + correlation engine.
- **MITRE ATT&CK mapper** (`mitre_mapper.py`) clasifica findings per technique ID + tactic.
- **ENS mapper** (`ens_mapper.py`) traduce findings técnicos → medidas ENS Anexo II afectadas.
- **LLM classifier** (`llm_classifier.py`) refinamiento contextual de findings con LLM (severidad · falso-positivo).
- **External pentester handoff** (`external/handoff_builder.py` + `external/findings_ingester.py`) handoff package + ingest findings externos (PDF + structured payload).
- **Remediation orchestration** (`remediation/`) subdir: retest runner · SLA calculator · prioritization.
- **Vulnerability orchestrator** (`vuln_orchestrator.py`) coordinación phases.
- **Kill switch** (`kill_switch.py`) SIGTERM <5s para runs en curso.
- **Scheduler** (`scheduler.py`) programación scans periódicos.
- **SSH credentials crypto** (`ssh_credentials_crypto.py`) Fernet AES-128-CBC para credenciales scan.
- **Reports** (`reports/`) subdir generación reportes PDF post-run.
- **Integrations** subdir (`integrations/`): M03 DdA updater · M05 Obligations creator (remediation auto-tasks).
- **FP patterns** (`fp_patterns/`) subdir patterns aprendidos false-positive (futuro ML M8-G1).
- **Tools** (`tools/`) subdir wrappers de herramientas (scanner adapters: nuclei · openvas · trivy · prowler · scoutsuite).
- **Portal cliente** (`portal_api.py`) cliente ve pentest scope + ventana + plan + IR + compromisos (per ADR-020 Q5.3 v6).
- **Public api** (`public_api.py`) endpoints públicos verificación post-handoff.

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 13.839 (**LARGEST motor FULKRO**) |
| Files | 56 (+6 subdirs: `external/` · `fp_patterns/` · `integrations/` · `remediation/` · `reports/` · `tools/`) |
| Status | **production-grade · autopilot v2.0 CABLEADO end-to-end** (ZFP · kill-switch · scope · MCP executor · classifier · remediation + orquestador determinista). El orquestador (`autopilot/orchestrator.orchestrate_run`) reemplaza el viejo stub: lo invocan tanto `scheduler.task_execute_run` (Celery nocturno) como `autopilot_api.start_autopilot` (botón admin "Continuar" + SSE live). Probado end-to-end en `tests/.../test_autopilot_integration.py` (pipeline MEDIO completo · ALTO pausa Gate 2 · EPSS escala · anti-injection · evidencia R6 verificada · evidence-pack ENAC). Arquitectura: `docs/spec/M8_PENTEST_PIPELINE_ENS_ALTO_v2.md` |

### Frontera Fulkro (≈90% automático) vs humano (≈10%)

Entre **Gate 1** (autorización/scope · decisión humana) y **Gate 2** (atestación · solo ALTO) **todo lo hace Fulkro** sin intervención: sesión efímera + manifest → arsenal MCP (nmap · nuclei · openvas · trivy · testssl · zap · prowler · scoutsuite · lynis · semgrep…) → ZFP 1-5 (dedup · FP · cross-tool · retest · clasificación) → enrich CVSS/EPSS → mapeo ENS Anexo II + MITRE ATT&CK → Finding canónico + Verdict agéntico (advisory · anti-injection) → asset graph → evidencia R6 append-only → coverage% + golden drift → revocar sesión. **BÁSICO/MEDIO completan solos** (`autopilot_status=completed`). **ALTO pausa en `paused_gate2`** esperando la atestación del pentester acreditado (OSCP/CPSTIC) — `POST /verification/runs/{rid}/attest` — que es el único paso humano (explotación manual cualificada). En dev (`USE_MCP_REAL=false`) el escaneo no corre de verdad → run PARCIAL 0% (frontera honesta); con MCP real (Hetzner) o `candidates_override` (tests/lever) → findings + coverage reales.
| Tests | `backend/tests/motors/m08_verification/` |
| API prefix | `/api/v1/verification/*` (14 endpoints) + portal-api cliente + public-api |
| RBAC | Cat A · Marcos-only admin · cliente vía portal-api · publico vía public-api |

## Key files

- `api.py` · 14 endpoints HTTP (CRUD runs + findings + retest + handoff + ingest + report + heatmap + score + delta + kill)
- `portal_api.py` · endpoints cliente portal (in-portal review scope + IR + compromisos)
- `public_api.py` · endpoints públicos verificación
- `service.py` · `VerificationService` core orchestration
- `cloud_orchestrator.py` · ejecución scans cloud
- `zfp_engine.py` · Zero False Positive engine
- `mitre_mapper.py` · ATT&CK technique classifier
- `ens_mapper.py` · findings → medidas ENS Anexo II
- `llm_classifier.py` · refinamiento LLM
- `pentest_auto_trigger*.py` · trigger automation
- `vuln_orchestrator.py` · phase coordination
- `scope_deriver.py` · auto-derive scope per project
- `kill_switch.py` · SIGTERM <5s
- `scheduler.py` · scans periódicos
- `ssh_credentials_crypto.py` · Fernet encryption SSH creds
- `models.py` · ORM (VerificationRun · VerificationFinding · ExternalPentesterHandoff · FalsePositivePatterns · RemediationRetests)
- `schemas.py` · Pydantic in/out
- `external/` subdir · findings_ingester · handoff_builder
- `integrations/` subdir · m3_dda_updater · m5_obligations (remediation auto-tasks)
- `remediation/` subdir · retest_runner · sla_calculator
- `reports/` subdir · PDF generation
- `fp_patterns/` subdir · patrones FP aprendidos (futuro ML M8-G1)
- `tools/` subdir · scanner adapters · LUCIA wrappers

## DB tables

Motor-specific (ORM en `models.py`):

- `verification_runs` · runs con phase + estado + scope
- `verification_findings` · findings con MITRE + ENS mapping + state
- `external_pentester_handoffs` · handoffs pentester externo CPSTIC
- `false_positive_patterns` · patterns FP aprendidos
- `remediation_retests` · retest runs post-remediation

RLS por `verification_runs` + `verification_findings`.

## Cross-motor integration

- **Inbound** (motores que consumen M08):
  - M09 Audit Prep (audita verificación pre-ENAC)
  - M10 Audit Sim (simulación auditoría)
  - M11 Copiloto (queries técnicas LLM)
  - M23 Retainer (pentest retainer mensual scope)
- **Outbound** (motores que M08 consume):
  - M02 MAGERIT (cross-check riesgos identificados)
  - M06 Document Factory (genera reportes técnicos)
  - M12 Magic Link (notificación cliente)
  - M14 Contracts (scan_window overrides)
  - M18 Communication (alertas + reports cliente)
  - M21 Portal Cliente (in-portal review pentest scope)
- **LLM agents**: A21 Detector SQL (cross-motor) + LLM classifier propio

## Limitaciones conocidas

### Backlog formal items diferidos (no bloqueantes MVP)

- **TODO-M8-G1 [MEDIA]**: Learn FP automáticamente vía ML model · diferido post-MVP.
- **TODO-M8-G2 [BAJA]**: Lynis-SSH wrapper hosts remotos · alternative scanner.
- **TODO-M8-G3 [MEDIA]**: `scan_window` via M14 contract overrides · expansion de policy enforcement.

## ADRs referenced

- ADR-020 · cliente in-portal review pentest scope + ventana + plan + IR + compromisos (Q5.3 v6)
- ADR-037 · referenced en código motor

## Cement OPS

Motor MÁS GRANDE FULKRO · 13.8K LOC · 6 subdirs · 14 endpoints CRUD/orchestration. Hub upstream pesado: 4 motores upstream consume + 6 motores downstream consumidos. Patrón v5.1: NO 501 stubs · todos endpoints contra BD real. Kill switch SIGTERM <5s invariante (runs no-stoppables = riesgo cliente).
