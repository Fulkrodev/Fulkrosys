# M8 — Pipeline de Pentesting Hiper-Automatizado (Autopilot) · Arquitectura de implementación v2.0

> **Documento de referencia de implementación.** Traduce `Fulkro-M8-Pipeline-Pentesting-ENS-Alto-v2.md` (diseño) al código real de FULKRO, registrando las decisiones de implementación, las desviaciones honestas fundamentadas y la frontera de verificación dev↔Hetzner. Construido sobre auditoría empírica Fase-0 (5 costuras de integración) — OPS-045/OPS-052.

## 0. Contexto y por qué

El motor M8 actual (v5.1) tiene el **arsenal completo** (15 MCP servers · recon/vulnscan/sast/cloud/infra/redteam/apisec/...) y las vías de **handoff externo + ingesta + informes + remediación** vivas, pero el **orquestador interno autopilot está sin cablear** (`scheduler.task_execute_run` = stub Checkpoint 2) y faltan las piezas "enterprise" del diseño v2.0: modelo canónico Finding/Verdict/EvidenceRecord, SARIF, EPSS, determinismo demostrable (run_manifest_hash + golden runs), capa agéntica anti prompt-injection, niveles de verificación explícitos, máquina de estados del hallazgo, conector efímero y observabilidad (coverage%/FP-rate/MTTR/drift).

Objetivo: dejar el pentesting automático **funcionando de cabo a rabo** según el doc v2.0, sin romper lo vivo, válido ante auditoría ENAC, fail-closed y honesto.

## 1. Principio rector (honesto)

"Perfecto" = **máxima cobertura demostrable de lo automatizable + evidencia rigurosa, reproducible y trazable + cierre verificado**. NO "cero vulnerabilidades". Zero-False-Positive **no es un claim global**: es una propiedad **solo de lo que ha pasado el Gate 4 (verificación activa)**.

7 principios de diseño (doc §0): determinismo del backbone (no del LLM) · evidence-first · fail-closed · safe-by-default · zero standing access · backbone = ancla de confianza · honest boundaries.

## 2. Frontera de verificación dev ↔ Hetzner (honest boundary)

| Capa | Verificable en dev (WSL) ahora | Requiere Hetzner/Docker/targets reales |
|---|---|---|
| Modelo de datos + migración | ✅ (alembic upgrade BD vacía + alembic check) | — |
| SARIF / CVSS / EPSS / dedup / mapeo ENS | ✅ (unit pure-logic + fixtures) | feed EPSS online (cache offline en dev) |
| 5 gates + máquina de estados + manifest/golden | ✅ (unit determinista) | — |
| Agente anti-injection (estructura + guards) | ✅ (unit con LLM mock) | LLM real Opus 4.8 (key) |
| Orquestador autopilot (lógica, fail-closed, fases) | ✅ (con `USE_MCP_REAL=false` → fallback simulado) | binarios escáner reales vía MCP (`USE_MCP_REAL=true`) |
| Conector efímero (lifecycle, revocación, TTL) | ✅ (lógica + scheduler) | provisión real dentro del perímetro cliente |
| Observabilidad + evidencia ENAC | ✅ (agregados + hash chain R6) | — |
| Frontend (botón, progreso SSE, coverage%, gates) | ✅ (build + render) | — |

**Regla:** ningún binario se reporta "ejecutado" si no se ejecutó. En dev, `USE_MCP_REAL=false` → resultados simulados/fail-closed explícitamente etiquetados. En Hetzner FASE J, `USE_MCP_REAL=true` activa los servers MCP reales.

## 3. Decisiones de implementación (fundamentadas)

### D1 · Modelo de datos: ELEVAR, no duplicar
`verification_findings` ya es ~95% el "Finding (hecho determinista)" del doc. Lo **elevamos** a Finding canónico añadiendo columnas (`epss_score`, `verification_level`, `finding_state`, `dedup_group_id`, `first_seen/last_seen`, `source_engine/engine_version/rule_id`, `asset_node_id`, `sarif_ref`, `risk_accepted_expires_at/by`). Esto preserva los 343 tests + 4 portales vivos. Lo "actual" queda intacto como capa de compatibilidad y se eleva, no se destruye.

- **NEW `m8_verdicts`** (`Verdict`): anotación del agente, **advisory**. Nunca muta el Finding. `model_version`, `prompt_hash`, `input_refs`, `triage` (jsonb), `structured_output_valid`, `decision_log_ref`, `human_override`.
- **NEW `m8_evidence_records`** (`EvidenceRecord`): **append-only** enganchado al trigger R6 existente (`fn_audit_track` mirror al `audit_log` hash-chaineado + `fn_audit_log_immutable` reject UPDATE/DELETE) = exactamente "EvidenceRecord append-only pgAudit" del doc, sin inventar substrato.
- **EXTEND `verification_runs`**: `run_manifest_hash`, `golden_run_id`, `coverage_pct`, `assets_in_scope`, `assets_scanned`, `autopilot_status`, `autopilot_phase`, `partial_run`, `tools_attempted`, `tools_failed`, `ephemeral_session_id/expires_at/revoked_at`.

### D2 · Grafo de activos: PKG-lite, no Apache AGE
El doc cita "Apache AGE", pero FULKRO ya decidió **PKG-lite** (`pkg_nodes`/`pkg_edges` + `pkg_service.add_node/add_edge/traverse_bfs`, decisión en `docs/decisions/pkg_lite_vs_apache_age.md`), usado por M22. Reutilizamos PKG-lite para el grafo de activos M8 (blast-radius/MTTR vía `traverse_bfs`). Satisface la intención del doc (grafo versionado de activos) sin introducir AGE. **Desviación honesta y fundamentada.**

### D3 · Reutilización del arsenal MCP (OPS-045/OPS-026)
No se reinventan herramientas. El orquestador invoca el arsenal existente vía `try_invoke_mcp_or_none(server, tool, args)` → `normalize_finding()` (shape canónico). `USE_MCP_REAL` gobierna real vs fallback. Tools que el doc añade y aún no están como adapter (katana, gospider, gitleaks/trufflehog, OSV/CodeQL/Snyk) se registran como `MCPTool` estructurales (code-complete, ejecución real en Hetzner).

### D4 · Conector efímero sobre lo existente
Reutiliza `scope_enforcer` (fail-closed `check_scope`), `derive_scope`, `require_pentest_authorisation` (magic-link `AUTORIZAR_PENTEST_EXTERNO` 72h/OTP/1-uso), `vpn_manager`, `encrypt_credentials` (Fernet). NEW: lifecycle explícito (create → authorize → revoke) + authorization.json firmado (HMAC) + TTL auto-revoke (scheduler) + `ephemeral_*` cols en run.

## 4. Mapa doc → módulos (de cabo a rabo)

| Doc | Módulo de implementación |
|---|---|
| §3 Capa 1 Recon · Capa 2 detección | `autopilot/phases.py` (orquesta arsenal MCP recon→detección) |
| §3 Capa 3 SARIF/CVSS/EPSS/dedup/ENS | `normalization/sarif.py` · `enrichment/cvss_epss.py` · `zfp_engine.py` (dedup) · `ens_mapper.py` |
| §4 Modelo Finding/Verdict/EvidenceRecord | `models.py` (elevado) + `canonical.py` (Verdict/EvidenceRecord helpers) |
| §5 5 gates + niveles verificación | `zfp_engine.py` (extendido · verification_level) |
| §6 máquina de estados | `finding_state_machine.py` |
| §7 capa agéntica anti-injection | `agent/triage_agent.py` + `agent/injection_guard.py` |
| §8 SLA + aceptación de riesgo | `remediation/sla_calculator.py` (existe) + `remediation/risk_acceptance.py` (NEW) |
| §9 disparadores/periodicidad | `scheduler.py` (continuo/periódico/cambio) |
| §10 fiabilidad fail-closed | `autopilot/orchestrator.py` (checkpoint/partial/degradación) |
| §11 determinismo | `determinism/manifest.py` (run_manifest_hash + golden) |
| §12 observabilidad | `observability/metrics.py` (coverage/FP/MTTR/drift) |
| §13-14 autopilot + 2 gates | `autopilot/orchestrator.py` + frontend gates |
| §16 evidencia ENAC | `m8_evidence_records` + `reports/` + `observability` |

## 5. Máquina de estados del hallazgo (doc §6)

```
detected → triaged → verified → reported → in_remediation → retested → closed
                 ↘ false_positive (desmentido activo u override humano · NUNCA por LLM)
                 ↘ risk_accepted (justificación + caducidad + re-revisión)
```
`closed` solo tras `retested` con delta que confirma remediación. `false_positive` exige verificación activa que desmiente u override humano logueado. `risk_accepted` terminal con `risk_accepted_expires_at`.

## 6. Pipeline 5 gates con niveles de verificación (doc §5)

1. Detección (motores deterministas) 2. Dedup/correlación 3. Umbral confianza (`<θ`→anexo técnico, **nunca se descarta**) 4. **Verificación** (`verification_level` ∈ {passive, active_safe, exploitation}) — **aquí vive el Zero-FP** 5. Triage agéntico (+ validación humana en Alto).

## 7. Defensa anti prompt-injection (doc §7 · regla dura)

- Contenido derivado del objetivo = **dato, nunca instrucción** (canal delimitado, jamás concatenado al system prompt).
- El `Verdict` **JAMÁS** reduce severidad/estado del `Finding` por debajo de lo determinista. Solo verificación activa que desmiente (determinista) u override humano logueado.
- Agente sin autoridad para alterar scope, parar el scan o tocar el manifest.
- Output estructurado inválido → **fail-closed**: el verdict no se aplica, el finding permanece.
- Meta-contenido sospechoso de manipulación = **finding de seguridad** elevado al humano.

## 8. Los dos gates humanos (irreductibles para Alto · doc §14)

- **Gate 1** — Autorización + alcance (RoE). Una vez por engagement. Cliente firma in-portal (M05, OTP). Ya existe (`PentestAuthorizeButton` + `require_pentest_authorisation`).
- **Gate 2** — Validación cualificada + atestación (solo Alto). OSCP/CPSTIC valida la parte adversarial irreductible y firma. NEW: gate de atestación admin.

## 9. Fases de entrega

0. ✅ Auditoría empírica · 1. Modelo canónico · 2. SARIF/CVSS/EPSS · 3. 5 gates + state machine · 4. Determinismo + asset graph · 5. Agente anti-injection · 6. Orquestador autopilot + conector efímero · 7. Remediación + risk acceptance · 8. Observabilidad + evidencia ENAC · 9. Frontend · 10. Tests + verificación.

## 10. Verificación

- `cd backend && ../.venv/bin/alembic upgrade head` sobre BD vacía/scratch + `alembic check` sin diff.
- Unit pure-logic: SARIF normalize, EPSS thresholding, gates, state machine transitions, manifest hash determinista, injection_guard (dato≠instrucción), risk acceptance caducidad.
- Smoke: orquestador con `USE_MCP_REAL=false` (fallback simulado) end-to-end → run completado + findings persistidos + evidence_records + manifest + coverage%.
- R6: `fn_audit_log_verify_chain()` ok=true tras run (evidence_records hash-chaineados).
