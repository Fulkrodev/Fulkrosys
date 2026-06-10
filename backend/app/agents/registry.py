"""Registry of the FULKRO IA agents.

Sesion 9 (2026-04-23): auditoria sistematica detecto 10 agentes
scaffolding redundantes con motores deterministas o stubs muertos
sin invocacion. Se eliminaron codigo + prompts + endpoints
especificos; los IDs quedan registrados aqui con status=deprecated
para mantener compatibilidad historica (no reusar). Ver commit
limpieza y progress/backlog_formal.md "Auditoria solapamiento
agentes" para el razonamiento por agente.

Sesion 10 cleanup (2026-04-24): A15 y A26 stubs eliminados. La
funcionalidad real vive en motores (m23_retainer para ambos), con
nombres de clase distintos y firmas distintas al agente LLM
originalmente previsto. Ver status ``externalized_to_motor``.

Status de un ID:
    activo:                agente con codigo real + invocable via
                           /api/v1/agents/{id}/invoke.
    scaffolding:           agente con fichero stub + TODO formal
                           para implementacion LLM real (ver
                           backlog_formal.md). Invocable pero
                           devuelve placeholder hasta implementar.
    scaffolding_covered_by_engine:
                           agente con fichero stub basico
                           funcional (endpoint + prompt) cuya
                           funcionalidad plena esta cubierta de
                           forma parcial por un motor determinista
                           pero el agente mantiene valor comercial
                           futuro (promocion a LLM real planeada).
                           Invocable. Ver ``note`` para el plan de
                           promocion.
    externalized_to_motor: funcionalidad real vive en un motor
                           (``external_location``). El stub LLM
                           original NO se implemento jamas; se
                           elimino para evitar confusion. El
                           endpoint /invoke devuelve 410 con
                           puntero al motor real.
    reservado:             id libre reservado (A9/A10 por
                           demolicion Pentest v4.2 en Sesion 7).
    deprecated:            agente eliminado por redundante con
                           motor (ver ``deprecated_reason``).
                           ``get_agent_info`` sigue devolviendo la
                           entrada para mostrar motivo en vez de
                           404 mudo.
"""

AGENT_REGISTRY = {
    1: {
        "name": "Parser Normativo",
        "status": "deprecated",
        "deprecated_reason": (
            "Corpus RD311 + CCN-STIC ya ingerido deterministicamente "
            "(backend/app/corpus/rd311_ingest.py, 127 chunks e5-large). "
            "Sin plan ampliar corpus con LLM parsing."
        ),
    },
    2: {
        "name": "Analizador de Pliegos",
        "status": "scaffolding_covered_by_engine",
        "model": "sonnet-4.5",
        "temperature": 0.1,
        "motor": None,
        "description": "Extrae requisitos ENS de pliegos de licitacion",
        "capabilities": ["ENS", "pliegos_PLACSP"],
        "external_location": None,
        "note": (
            "Clase + endpoint /api/v1/agents/2/analyze-pliego + prompt "
            "basico existen (24 LOC stub funcional). Potencial promocion "
            "futura a LLM real pleno: analizar pliegos PLACSP pre-venta "
            "para detectar requisitos ENS + encaje FULKRO (1-2h vs 1-2d "
            "analisis manual). Valor comercial directo. "
            "Implementar post-"
            "Sesion 13 con primer cliente piloto y pliegos reales."
        ),
    },
    3: {
        "name": "Scoping y Categorizacion",
        "status": "deprecated",
        "deprecated_reason": (
            "Redundante con A18 Reunion Exploratoria (Paso 2.2 Sesion 9), "
            "que cubre el caso pre-proyecto K.4 con panel live JSON strict."
        ),
    },
    4:  {"name": "Redactor Diagnosticos E-090",      "status": "activo", "model": "sonnet-4.6", "temperature": 0.2,  "motor": "m22", "description": "Redactor narrativa senior E-090 secs 1/2/6 (NO toca 3.1/3.2/4/5 — determinista M21+M22+M4). Sonnet 4.6 + caching + validator anti-hallucination numerica", "capabilities": ["DPC_anual", "continuity", "redactor"]},
    5: {
        "name": "Analista MAGERIT",
        "status": "deprecated",
        "deprecated_reason": (
            "M02 MAGERIT cubre 95% del camino estandar (67 tipos activo + "
            "57 amenazas + 98 salvaguardas catalogadas). Long-tail de activos "
            "exoticos se trata a mano, no justifica agente dedicado."
        ),
    },
    6:  {"name": "Analista de Contratos",            "status": "activo", "model": "sonnet-4.6", "temperature": 0.1,  "motor": "m14", "description": "Analista contratos proveedor cliente: detecta gaps ENS+RGPD + genera adenda juridica formal (Sonnet 4.6 + caching)", "capabilities": ["contratos_terceros", "ENS_evidencias", "RGPD"]},
    7: {
        "name": "Gap Analyzer Priorizacion",
        "status": "deprecated",
        "deprecated_reason": (
            "Redundante con M04 Gap Analysis. Logica LLM contextual "
            "migrada a TODO-M4-G1 como metodo prioritize_with_llm interno "
            "dentro de M04 service (no agente separado)."
        ),
    },
    8: {
        "name": "Planificador Obligaciones",
        "status": "deprecated",
        "deprecated_reason": (
            "Redundante con M05 Obligations: enrich_description_with_llm "
            "+ instantiation_service + gantt_service ya personalizan y "
            "planifican obligaciones."
        ),
    },
    # IDs 9 y 10 reservados (antiguos agentes Pentest v4.2 demolidos en
    # Sesion 7. Si M8 v5.1 necesita un agente, se asigna nuevo ID 31+).
    9:  {"name": "(reservado)",                      "status": "reservado", "deprecated_reason": "Pentest v4.2 demolido Sesion 7 — ID no reusar."},
    10: {"name": "(reservado)",                      "status": "reservado", "deprecated_reason": "Pentest v4.2 demolido Sesion 7 — ID no reusar."},
    11: {"name": "Auditor Interno Virtual",          "status": "activo", "model": "opus-4.7",   "temperature": 0.1,  "motor": "m10", "description": "Auditor suplementario a M10: PAC priorizado + preguntas sector + narrativa dry-run (Opus 4.7 + caching). NO reemplaza las 58 preguntas ENAC deterministas", "capabilities": ["auditor_virtual", "inconsistency_detection", "audit", "ENS"]},
    12: {"name": "Coach Cliente Evaluador",          "status": "activo", "model": "sonnet-4.6", "temperature": 0.2,  "motor": "m09", "description": "Coach evaluador: scorea respuestas cliente a preguntas M9 determinista (L0-L5 + 3 dimensiones + gaps + respuesta_ideal_template + next_actions). Sonnet 4.6 + caching. NO genera preguntas", "capabilities": ["coach", "proactive_nudges", "context_aware"]},
    13: {
        "name": "Generador Dossier Final",
        "status": "deprecated",
        "deprecated_reason": (
            "M9 dossier_generator.py cubre 100% la compilacion dossier "
            "auditor seccion 2.15. Determinismo es feature (hash chain "
            "audit_log para trazabilidad ENAC); un LLM introduciria "
            "no-determinismo no deseado."
        ),
    },
    14: {"name": "Copiloto Conversacional",          "status": "activo", "model": "sonnet-4.5", "temperature": 0.2,  "motor": "m11", "description": "Chat RAG para preguntas de Marcos sobre ENS", "capabilities": ["rag", "q_and_a", "context_aware", "magerit", "obligations", "conformity", "diagnosis", "evidence"]},
    15: {
        "name": "Vigilancia Normativa",
        "status": "externalized_to_motor",
        "external_location": "backend.app.motors.m23_retainer.agent_15_vigilancia",
        "note": (
            "RSS monitor operativo (CCN-CERT + BOE + AEPD + ENISA + "
            "CCN-STIC scrape futuro) con 11 funciones, daily digest "
            "email, persistence a normativa_alerts. Usa clase "
            "Agente15Vigilancia (no AgentBase). El stub LLM original "
            "(haiku-4.5, check_for_changes/assess_impact) nunca se "
            "implemento real y se elimino en Sesion 10 cleanup — "
            "funcion conceptualmente distinta (diff LLM contenido vs "
            "monitor RSS operativo)."
        ),
    },
    16: {
        "name": "Generador Quick Wins",
        "status": "deprecated",
        "deprecated_reason": (
            "Triple solape: M21 quickwins.generate_quick_wins + "
            "A18 quick_wins_sugeridas en panel live. No justifica agente."
        ),
    },
    17: {"name": "Cualificador Comercial",           "status": "activo", "model": "sonnet-4.6", "temperature": 0.1,  "motor": "m13", "description": "Cualificador post-contacto: 6 dimensiones + A/B/C/DESCARTAR + priority + next_actions + red_flags (Sonnet 4.6, prompt caching)", "capabilities": ["qualifier", "lead_questions", "sector_adaptive"]},
    18: {"name": "Reunion Exploratoria",             "status": "activo", "model": "sonnet-4.6", "temperature": 0.1,  "motor": "m13", "description": "Panel IA live JSON strict (Sonnet 4.6) durante reunion exploratoria K.4", "capabilities": ["reunion", "acta_summary", "context_aware"]},
    19: {"name": "Redactor de Propuestas",           "status": "activo", "model": "opus-4.7",   "temperature": 0.15, "motor": "m13", "description": "Genera propuesta P-001 senior-expert (Opus 4.7 1M ctx, 16k tokens)", "capabilities": ["propuestas", "retainer_optimal", "sector_adaptive"]},
    20: {"name": "Negociador Contractual",           "status": "activo", "model": "sonnet-4.6", "temperature": 0.15, "motor": "m14", "description": "Clausulas C-001 dinamicas LLM (Sonnet 4.6, AAPP/privado, garantia por categoria, incompatibilidad)", "capabilities": ["negociacion", "counter_arguments", "contratos_terceros"]},
    21: {"name": "Detector Discrepancias",           "status": "activo", "model": "deterministic", "temperature": 0.0, "motor": "m04", "description": "DiscrepancyDetectorService DETERMINISTA cross-motor SQL (1.D.A v3.10 ENS-only · sostiene R1 inviolable motores deterministas > LLM normativas). 5 detectores: magerit_vs_dda · dda_vs_evidence · magerit_vs_findings · dda_vs_documents · findings_vs_remediation. Legacy LLM wrapper DetectorDiscrepanciasAgent preservado para reasoning narrativo opcional.", "capabilities": ["discrepancias_ens_only", "cross_motor_sql", "deterministic_inconsistency_detection", "auditor_ens_perspective"]},
    22: {
        "name": "Analista Stakeholders",
        "status": "deprecated",
        "deprecated_reason": (
            "Redundante con M21 stakeholder_service + stakeholders_service "
            "(build_graph, detect_role_conflicts, find_decision_chain, "
            "get_ens_responsibles)."
        ),
    },
    23: {
        "name": "Mapeador Procesos",
        "status": "deprecated",
        "deprecated_reason": (
            "Redundante con M21 process_service + processes_service "
            "(inventory_processes, seed_sector_processes, feed_bia con "
            "plantillas sectoriales)."
        ),
    },
    24: {
        "name": "Detector Obligaciones Cruzadas",
        "status": "deprecated",
        "deprecated_reason": (
            "Redundante con M21 cross_compliance_service (RGPD / NIS2 / "
            "DORA / PSD2 / AI Act / ISO27001 / ENI). detect_obligations "
            "deterministico cubre el caso."
        ),
    },
    25: {
        "name": "Generador DFD",
        "status": "deprecated",
        "deprecated_reason": (
            "Redundante con M22 dataflow_service (generate_mermaid, "
            "generate_dfd, generate_all_dfds) que genera DFDs Mermaid "
            "desde entidades descubiertas."
        ),
    },
    26: {
        "name": "Coach Auditoria/Crisis",
        "status": "externalized_to_motor",
        "external_location": "backend.app.motors.m23_retainer.agent_26",
        "note": (
            "Analizador determinista retainers (4 reglas: overdue, drift "
            "CRITICAL, renewal urgente, upgrade candidate). 3 tests, "
            "Celery task m23.agent_26_weekly_analysis, endpoints "
            "/api/v1/retainer/agent-26/summary + /alerts. El stub LLM "
            "original (opus-4, generate_audit_simulation/crisis_scenario) "
            "nunca se implemento real y se elimino en Sesion 10 cleanup "
            "— funcion radicalmente distinta (coach ENAC LLM vs gestor "
            "retainers determinista). NO renombrar el real para "
            "minimizar churn (rompe 3 tests + Celery + endpoints)."
        ),
    },
    27: {"name": "Clasificador IDMS",                "status": "activo", "model": "haiku-4.5",  "temperature": 0.1,  "motor": "m24", "description": "Clasificador documentos IDMS complementa heuristica M24 para nombres ambiguos. Haiku 4.5 alto volumen + caching. Propone folder 00-13/99 + tags + alternativas + requires_human_review", "capabilities": ["clasificador", "upload_categorize", "context_aware"]},
    28: {
        "name": "Asistente de Conformidad",
        "status": "deprecated",
        "external_location": "backend.app.motors.m27_conformity",
        "deprecated_reason": (
            "Funcionalidad cubierta por M27 Conformity Lifecycle "
            "determinista (13 tablas + rutas + submissions + overlays "
            "PCE + topologias de rol + 5 adaptadores CCN). LLM "
            "anadiria no-determinismo en proceso que requiere "
            "trazabilidad auditor ENAC via hash chain audit_log. No "
            "implementar. Stub eliminado en Sesion 10 cleanup."
        ),
    },
    29: {
        "name": "Evaluador de Impacto de Cambios",
        "status": "deprecated",
        "external_location": "backend.app.motors.m28_change_governance.materiality_engine",
        "deprecated_reason": (
            "Funcionalidad cubierta por M28 materiality_engine "
            "determinista (125 LOC, arbol 10 preguntas + workflows "
            "derivados). LLM anadiria subjetividad donde "
            "determinismo es valor (impacto cambios afecta a re-"
            "certificacion ENS). No implementar. Stub eliminado en "
            "Sesion 10 cleanup."
        ),
    },
    30: {
        "name": "Operador de Retainer",
        "status": "deprecated",
        "external_location": "backend.app.motors.m23_retainer.retainer_service",
        "deprecated_reason": (
            "Funcionalidad cubierta por M23 retainer_service (912 "
            "LOC) + agent_26 analyzer (311 LOC, 4 reglas overdue/"
            "drift/renewal/upgrade). Priorizacion ops + drift + "
            "health_score + capacity multi-cliente resuelto "
            "deterministicamente. LLM no aporta valor incremental. "
            "No implementar. Stub eliminado en Sesion 10 cleanup."
        ),
    },
    # A31 nuevo en Sesion 9 Paso 2.7. Primer agente creado desde cero
    # tras auditoria STEP B (cierra TODO-M3-G1 + reasigna TODO-A14-G1).
    31: {"name": "Enriquecedor DdA no_aplica",       "status": "activo", "model": "sonnet-4.6", "temperature": 0.2,  "motor": "m03", "description": "Enriquece justificaciones DdA no_aplica con narrativa contextual 60-200 palabras (cita cloud_providers, frameworks heredados, CCN-STIC). Sonnet 4.6 + caching agresivo (15-30 invocaciones/proyecto)", "capabilities": ["enriquecedor_dda", "ccn_stic_grounding", "sector_adaptive"]},
}


def get_agent_info(agent_id: int) -> dict | None:
    """Return registry info for a given agent id, or None if missing.

    Entries devueltas incluyen ``status`` in {activo, scaffolding,
    deprecated, reservado}. Consumidores deben comprobar el campo
    antes de intentar invocar: solo ``activo`` y ``scaffolding``
    tienen clase Python importable.
    """
    return AGENT_REGISTRY.get(agent_id)


def list_agents() -> list[dict]:
    """Return the registry as a sorted list of dicts with the id embedded."""
    return [{"id": k, **v} for k, v in sorted(AGENT_REGISTRY.items())]


def list_active_agents() -> list[dict]:
    """Agentes con codigo importable e invocable.

    Incluye ``activo`` + ``scaffolding`` + ``scaffolding_covered_by_engine``.
    Excluye ``externalized_to_motor`` (sin clase en _AGENT_CLASSES) y
    ``deprecated`` / ``reservado``.
    """
    invokable_statuses = (
        "activo",
        "scaffolding",
        "scaffolding_covered_by_engine",
    )
    return [
        {"id": k, **v}
        for k, v in sorted(AGENT_REGISTRY.items())
        if v.get("status") in invokable_statuses
    ]
