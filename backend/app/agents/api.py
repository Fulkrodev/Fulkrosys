"""FastAPI router for the FULKRO IA agents.

Sesion 9 (2026-04-23): 10 agentes deprecated tras auditoria
solapamiento (ver registry.py). Sus entradas en ``_AGENT_CLASSES``
se eliminaron; el endpoint generico ``/{id}/invoke`` devuelve 410
Gone si se llama con un id deprecated (vs 404 genuino para ids
desconocidos).
"""
import importlib
from typing import Type
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.base import AgentBase
from backend.app.agents.registry import AGENT_REGISTRY, get_agent_info, list_agents
from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db

# FIX seguridad (bug-hunt 2026-06-14): los 13 agentes IA son admin-only (ADR-013/
# ADR-020 · A2/A4/A6/A11/A17/A18/A27/A31 invocan LLM real). El gate global solo
# AUTENTICA (admite también el pool cliente); sin require_owner a nivel de router
# un client_user autenticado podía invocar agentes admin (abuso de coste LLM).
# El copiloto cliente (A14) se expone aparte vía m11_copiloto/portal_api con
# require_client_user, así que esto NO lo afecta.
router = APIRouter(
    prefix="/api/v1/agents", tags=["agents"],
    dependencies=[Depends(require_owner)],
)


_AGENT_CLASSES: dict[int, str] = {
    2:  "agent_02_pliegos.AnalizadorPliegosAgent",
    4:  "agent_04_redactor.RedactorPoliticasAgent",
    6:  "agent_06_contratos.AnalistaContratosAgent",
    # IDs 1, 3, 5, 7, 8 deprecated Sesion 9 (auditoria solapamiento).
    # IDs 9 y 10 reservados (Pentest v4.2 demolido Sesion 7).
    11: "agent_11_auditor_virtual.AuditorInternoVirtualAgent",
    12: "agent_12_coach_cliente.CoachClienteAgent",
    # ID 13 deprecated Sesion 9 (M9 dossier_generator cubre 100%).
    14: "agent_14_copiloto.CopilotoAgent",
    # ID 15 externalized_to_motor (Sesion 10 cleanup): funcionalidad RSS
    # monitor real en m23_retainer.agent_15_vigilancia (413 LOC).
    # ID 16 deprecated Sesion 9 (M21 quickwins + A18).
    17: "agent_17_cualificador.CualificadorComercialAgent",
    18: "agent_18_reunion.AsistenteReunionExploratoriaAgent",
    19: "agent_19_propuestas.RedactorPropuestasAgent",
    20: "agent_20_negociacion.AsistenteNegociacionAgent",
    21: "agent_21_discrepancias.DetectorDiscrepanciasAgent",
    # IDs 22, 23, 24, 25 deprecated Sesion 9 (redundantes con M21/M22).
    # ID 26 externalized_to_motor (Sesion 10 cleanup): analizador retainers
    # determinista en m23_retainer.agent_26 (311 LOC + 3 tests + Celery task
    # m23.agent_26_weekly_analysis + endpoints /api/v1/retainer/agent-26/*).
    27: "agent_27_clasificador.ClasificadorIDMSAgent",
    # ID 28 deprecated Sesion 10 cleanup (M27 Conformity Lifecycle cubre).
    # ID 29 deprecated Sesion 10 cleanup (M28 materiality_engine cubre).
    # ID 30 deprecated Sesion 10 cleanup (M23 retainer_service + agent_26 cubren).
    31: "agent_31_enriquecedor_dda.Agent31EnriquecedorDdA",
}


def _get_agent_class(agent_id: int) -> Type[AgentBase] | None:
    """Return the agent class for the given id, or None if unknown."""
    mapping = _AGENT_CLASSES.get(agent_id)
    if not mapping:
        return None
    module_name, class_name = mapping.rsplit(".", 1)
    mod = importlib.import_module(f"backend.app.agents.{module_name}")
    return getattr(mod, class_name, None)


def _raise_if_deprecated(agent_id: int) -> None:
    """Raise 410 Gone si el id esta deprecated en el registry, 404 si unknown."""
    info = get_agent_info(agent_id)
    if info is None:
        raise HTTPException(
            status_code=404, detail=f"Agente {agent_id} no registrado"
        )
    status = info.get("status", "activo")
    if status == "deprecated":
        raise HTTPException(
            status_code=410,
            detail=(
                f"Agente {agent_id} ({info.get('name', '?')}) deprecated. "
                f"Motivo: {info.get('deprecated_reason', 'sin motivo registrado')}"
            ),
        )
    if status == "reservado":
        raise HTTPException(
            status_code=404,
            detail=f"Agente {agent_id} reservado (no invocable)",
        )
    if status == "externalized_to_motor":
        external = info.get("external_location", "motor desconocido")
        note = info.get("note", "")
        raise HTTPException(
            status_code=410,
            detail=(
                f"Agente {agent_id} ({info.get('name', '?')}) "
                f"externalizado a {external}. {note}".strip()
            ),
        )


# ---------------------------------------------------------------------------
# Generic endpoints
# ---------------------------------------------------------------------------

@router.get("/")
async def list_all_agents() -> dict:
    """List all 27 registered agents with metadata."""
    return {"agents": list_agents(), "total": len(AGENT_REGISTRY)}


@router.get("/{agent_id}")
async def get_agent_info_endpoint(agent_id: int) -> dict:
    """Return metadata for a single agent."""
    info = get_agent_info(agent_id)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Agente {agent_id} no encontrado")
    return {"agent_id": agent_id, **info}


@router.post("/{agent_id}/invoke")
async def invoke_agent(
    agent_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generic agent invocation.

    Body schema: {project_id?: UUID, message: str, params?: dict, structured_output?: bool, extra_context?: str}.

    Devuelve 410 Gone si el id esta marcado deprecated en el registry;
    404 si el id es desconocido o reservado; 404 si el id es valido pero
    aun no tiene clase Python registrada en ``_AGENT_CLASSES``.
    """
    _raise_if_deprecated(agent_id)
    agent_class = _get_agent_class(agent_id)
    if agent_class is None:
        raise HTTPException(status_code=404, detail=f"Agente {agent_id} no implementado")

    project_id_raw = body.get("project_id")
    project_id = UUID(project_id_raw) if project_id_raw else None

    agent = agent_class()
    await db.commit()
    return await agent.invoke(
        db,
        project_id=project_id,
        user_message=body.get("message", ""),
        context=body.get("params"),
        structured_output=bool(body.get("structured_output", False)),
        extra_context=body.get("extra_context", ""),
    )


# ---------------------------------------------------------------------------
# Specific endpoints (shortcuts for agents with distinctive flows)
# ---------------------------------------------------------------------------

@router.post("/2/analyze-pliego")
async def analyze_pliego(body: dict, db: AsyncSession = Depends(get_db)) -> dict:
    from backend.app.agents.agent_02_pliegos import AnalizadorPliegosAgent

    agent = AnalizadorPliegosAgent()
    await db.commit()
    return await agent.analyze_pliego(db, body["pliego_text"], body.get("metadata"))


@router.post("/4/generate-e090-narrative")
async def generate_e090_narrative(body: dict, db: AsyncSession = Depends(get_db)) -> dict:
    """Redactor narrativa senior E-090 secs 1/2/6 (Sonnet 4.6 JSON strict).

    SCOPE RESTRINGIDO: solo genera las secciones NARRATIVAS 1, 2 y 6. Las
    secciones deterministas 3.1 (M21 paso5_orchestrator), 3.2 (M22
    paso6_e090_technical), 4 (matriz M4 Gap) y 5 (madurez por medida)
    NO se tocan aqui para preservar trazabilidad ENAC.

    Body schema::

        {
          "client_context": {
            "company_name": "DataForma S.L.",
            "sector": "sanidad|aapp|fintech|otro",
            "size": "PYME|mediana|grande",
            "ens_category": "BASICA|MEDIA|ALTA",
            "is_aapp": false
          },
          "deterministic_data": {
            "madurez_global": "L0|L1|L2|L3|L4|L5",
            "porcentaje_conformidad": 32,
            "familias_peores": ["mp.s", "op.exp"],
            "plazo_viable_meses": 8,
            "horas_estimadas": 105,
            "activos_criticos": 14,
            "top_gaps": [{"codigo": "op.exp.3", "gap": "configuracion no gestionada"}]
          },
          "project_id": "<uuid>"?
        }

    Devuelve 3 secciones markdown + metadata (tokens, coste, cache_*,
    fallback_used).
    """
    from backend.app.agents.agent_04_redactor import (
        Agent04RedactorDiagnosticos,
    )

    client_context = body.get("client_context")
    deterministic_data = body.get("deterministic_data")
    if not isinstance(client_context, dict) or not client_context:
        raise HTTPException(
            status_code=400,
            detail="Se requiere 'client_context' dict",
        )
    if not isinstance(deterministic_data, dict) or not deterministic_data:
        raise HTTPException(
            status_code=400,
            detail="Se requiere 'deterministic_data' dict con outputs M21+M22",
        )

    project_id_raw = body.get("project_id")
    project_id = UUID(project_id_raw) if project_id_raw else None

    agent = Agent04RedactorDiagnosticos()
    try:
        result = await agent.generate_e090_narrative_sections(
            db,
            client_context=client_context,
            deterministic_data=deterministic_data,
            project_id=project_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


    await db.commit()
    return result
@router.post("/11/run-supplementary-audit")
async def run_supplementary_audit(body: dict, db: AsyncSession = Depends(get_db)) -> dict:
    """Auditor suplementario a M10 (Opus 4.7 JSON strict).

    Scope: A11 anade 3 capas sobre el output determinista de M10:
    1) PAC priorizado sector-aware (3-5 fases).
    2) 3-5 preguntas contextuales del sector.
    3) Narrativa ejecutiva dry-run con veredicto.

    Body schema::

        {
          "m10_audit_result": {
            "score_conformidad": 72,
            "categoria_ens": "MEDIA",
            "nc_mayores": [{"codigo": "op.exp.4", "descripcion": "..."}],
            "nc_menores": [{"codigo": "op.pl.3", "descripcion": "..."}],
            "preguntas_L5": 12, "preguntas_L4": 18, ..., "preguntas_L0": 2,
            "preguntas_respondidas_total": 58
          },
          "client_context": {
            "company_name": "DataForma S.L.",
            "sector": "sanidad|aapp|fintech|otro",
            "size": "PYME|mediana|grande",
            "ens_category": "BASICA|MEDIA|ALTA",
            "is_aapp": false,
            "target_audit_date": "2026-09-15"
          },
          "project_id": "<uuid>"?
        }

    Devuelve SupplementaryAuditResult + tokens + coste + cache_* +
    fallback_used.
    """
    from backend.app.agents.agent_11_auditor_virtual import (
        Agent11AuditorVirtual,
    )

    m10_audit_result = body.get("m10_audit_result")
    client_context = body.get("client_context")
    if not isinstance(m10_audit_result, dict) or not m10_audit_result:
        raise HTTPException(
            status_code=400,
            detail="Se requiere 'm10_audit_result' dict (output M10)",
        )
    if not isinstance(client_context, dict) or not client_context:
        raise HTTPException(
            status_code=400,
            detail="Se requiere 'client_context' dict",
        )

    project_id_raw = body.get("project_id")
    project_id = UUID(project_id_raw) if project_id_raw else None

    agent = Agent11AuditorVirtual()
    try:
        result = await agent.generate_supplementary_audit(
            db,
            m10_audit_result=m10_audit_result,
            client_context=client_context,
            project_id=project_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


    await db.commit()
    return result
@router.post("/6/analyze-contract")
async def analyze_contract(body: dict, db: AsyncSession = Depends(get_db)) -> dict:
    """Analista contratos cliente <-> proveedor (Sonnet 4.6 JSON strict).

    Body schema::

        {
          "contract_text": "<texto plano contrato, tope 12000 chars>",
          "provider_name": "AWS Europe SARL",
          "provider_role": "hosting|saas|desarrollo|integrador|limpieza|consultoria|otro",
          "criticality": "alta|media|baja",
          "data_processed": "datos_pacientes|datos_empleados|datos_clientes|ninguno",
          "ens_category": "BASICA|MEDIA|ALTA",
          "client_sector": "sanidad|aapp|fintech|otro",
          "provider_id": "<uuid>"?,
          "project_id": "<uuid>"?
        }

    Devuelve ContractAnalysisResult + tokens + coste + cache_* + fallback_used.
    """
    from backend.app.agents.agent_06_contratos import (
        Agent06AnalistaContratos,
    )

    required = (
        "contract_text", "provider_name", "provider_role",
        "criticality", "data_processed", "ens_category", "client_sector",
    )
    for k in required:
        if k not in body:
            raise HTTPException(
                status_code=400, detail=f"Falta campo requerido '{k}'"
            )

    provider_id_raw = body.get("provider_id")
    project_id_raw = body.get("project_id")

    agent = Agent06AnalistaContratos()
    try:
        result = await agent.analyze_provider_contract(
            db,
            contract_text=body["contract_text"],
            provider_name=body["provider_name"],
            provider_role=body["provider_role"],
            criticality=body["criticality"],
            data_processed=body["data_processed"],
            ens_category=body["ens_category"],
            client_sector=body["client_sector"],
            provider_id=UUID(provider_id_raw) if provider_id_raw else None,
            project_id=UUID(project_id_raw) if project_id_raw else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


    await db.commit()
    return result
# Endpoints /5/suggest-threats, /7/prioritize-gaps y /16/quick-wins
# eliminados en Sesion 9 (auditoria solapamiento agentes). Logica
# conceptual absorbida por motores M02 / M04 / M21 respectivamente.
# Consumidores externos que llamasen a estos paths reciben 404
# estandar de FastAPI (no existen).


@router.post("/17/qualify-lead")
async def qualify_lead(body: dict, db: AsyncSession = Depends(get_db)) -> dict:
    """Cualificador comercial post-contacto (Sonnet 4.6 JSON strict).

    Body schema::

        {
          "lead_context": {
            "company_name": str,
            "company_sector": str,
            "company_size": str,
            "origin": "referencia|frio|evento"
          },
          "qualification_answers": {
            "contract_status": "adjudicado|licitando|explorando|desconocido",
            "ens_category_expected": "BASICA|MEDIA|ALTA|desconocida",
            "deadline": "30d|3m|6m|12m|sin_plazo",
            "sponsor": "claro|difuso|sin_identificar",
            "budget": "asignado|estudiando|ninguno",
            "tech_team": "propio|externalizado|ninguno",
            "existing_frameworks": ["RGPD", ...],
            "lead_quality": "referencia|calido|frio"
          },
          "lead_id": "<uuid>"?       // si viene, persiste en leads.lead_score/clasificacion_abc/estado
        }

    Devuelve QualificationResult + tokens + coste + cache_* + fallback_used.
    """
    from backend.app.agents.agent_17_cualificador import (
        Agent17CualificadorComercial,
    )

    lead_context = body.get("lead_context")
    qualification_answers = body.get("qualification_answers")
    if not isinstance(lead_context, dict) or not lead_context:
        raise HTTPException(
            status_code=400,
            detail="Se requiere 'lead_context' dict con metadatos empresa",
        )
    if not isinstance(qualification_answers, dict) or not qualification_answers:
        raise HTTPException(
            status_code=400,
            detail="Se requiere 'qualification_answers' dict con las 8 respuestas humanas",
        )

    lead_id_raw = body.get("lead_id")
    lead_id = UUID(lead_id_raw) if lead_id_raw else None

    agent = Agent17CualificadorComercial()
    await db.commit()
    return await agent.qualify_lead(
        db,
        lead_context=lead_context,
        qualification_answers=qualification_answers,
        lead_id=lead_id,
    )


@router.post("/18/meeting-update")
async def meeting_update(body: dict, db: AsyncSession = Depends(get_db)) -> dict:
    """Panel IA live K.4 reunion exploratoria (Sonnet 4.6 JSON strict).

    Body schema::

        {
          "blocks": {
            "A_contexto": "...",
            "B_informacion": "...",
            "C_madurez": "...",
            "D_plazos": "...",
            "E_presupuesto": "...",
            "F_equipo": "..."
          },
          "blocks_filled": ["A", "B"],    // optional; auto-derived
          "meeting_id": "<uuid>",         // optional
          "project_id": "<uuid>"          // optional
        }

    Devuelve el insight estructurado + tokens + coste + fallback_used.
    """
    from backend.app.agents.agent_18_reunion import Agent18ReunionExploratoria

    blocks = body.get("blocks")
    if not isinstance(blocks, dict) or not blocks:
        raise HTTPException(
            status_code=400, detail="Se requiere 'blocks' dict con bloques A-F"
        )

    blocks_filled = body.get("blocks_filled")
    meeting_id_raw = body.get("meeting_id")
    project_id_raw = body.get("project_id")
    meeting_id = UUID(meeting_id_raw) if meeting_id_raw else None
    project_id = UUID(project_id_raw) if project_id_raw else None

    agent = Agent18ReunionExploratoria()
    await db.commit()
    return await agent.analyze_meeting_blocks(
        db,
        blocks=blocks,
        blocks_filled=blocks_filled,
        meeting_id=meeting_id,
        project_id=project_id,
    )


@router.post("/18/meeting-update/stream")
async def meeting_update_stream(body: dict, db: AsyncSession = Depends(get_db)):
    """SSE stream A18 meeting update (TODO-A18-LATENCY RESOLVED · FASE 7.A.5).

    Endpoint POST + StreamingResponse text/event-stream.

    Frontend conecta via fetch + ReadableStream parser (no EventSource
    nativo porque EventSource solo soporta GET y los bloques A-F son
    payload grande). Pattern coherente OpenAI streaming completions.

    SSE events emitidos:
      event: progress  data: {"phase": "thinking", "ts": ...}
      event: progress  data: {"phase": "validating_schema", ...}
      event: insight   data: <insight JSON full>
      event: done      data: {"latency_ms": ..., "tokens": ...}

    Wraps invocacion sincrona (analyze_meeting_blocks). SSE phase-level
    (event: progress / insight / done) operativo en MVP. Real LLM
    token-by-token streaming requiere refactor `base._call_llm` a
    `Anthropic.messages.stream()` · cross-cutting affecta TODOS los
    agentes heredando AgentBase. Diferido a S13 ·
    TODO-A18-TOKEN-STREAM-001 backlog formal (progress/backlog_formal.md).

    El TTFT mejora porque emitimos `progress: thinking` inmediato
    antes de esperar al LLM completo. Frontend renderiza skeleton
    + spinner hasta llegar `event: insight`.

    Body schema (igual que /18/meeting-update sync)::

        {
          "blocks": {"A_contexto": "...", ...},
          "blocks_filled": ["A","B"],
          "meeting_id": "<uuid>",
          "project_id": "<uuid>"
        }
    """
    import asyncio
    import json
    import time

    from fastapi.responses import StreamingResponse

    from backend.app.agents.agent_18_reunion import Agent18ReunionExploratoria

    blocks = body.get("blocks")
    if not isinstance(blocks, dict) or not blocks:
        raise HTTPException(
            status_code=400,
            detail="Se requiere 'blocks' dict con bloques A-F",
        )

    blocks_filled = body.get("blocks_filled")
    meeting_id_raw = body.get("meeting_id")
    project_id_raw = body.get("project_id")
    meeting_id = UUID(meeting_id_raw) if meeting_id_raw else None
    project_id = UUID(project_id_raw) if project_id_raw else None

    async def _stream():
        start = time.monotonic()

        # Event 1: progress thinking — TTFT inmediato
        yield (
            "event: progress\n"
            f"data: {json.dumps({'phase': 'thinking', 'ts': time.time()})}\n\n"
        )
        # Forzar flush con sleep mínimo (SSE buffer)
        await asyncio.sleep(0.01)

        # Run sync agent invoke (LLM call ~5-15s)
        agent = Agent18ReunionExploratoria()
        try:
            result = await agent.analyze_meeting_blocks(
                db,
                blocks=blocks,
                blocks_filled=blocks_filled,
                meeting_id=meeting_id,
                project_id=project_id,
            )
        except Exception as exc:  # noqa: BLE001
            yield (
                "event: error\n"
                f"data: {json.dumps({'error': str(exc)})}\n\n"
            )
            return

        # Event 2: progress validating
        yield (
            "event: progress\n"
            f"data: {json.dumps({'phase': 'validating_schema'})}\n\n"
        )

        # Event 3: insight final
        insight = result.get("insight", {})
        yield (
            "event: insight\n"
            f"data: {json.dumps(insight, ensure_ascii=False)}\n\n"
        )

        # Event 4: done con métricas
        latency_ms = int((time.monotonic() - start) * 1000)
        done_payload = {
            "latency_ms": latency_ms,
            "tokens_input": result.get("tokens_input"),
            "tokens_output": result.get("tokens_output"),
            "schema_valid": result.get("schema_valid"),
            "fallback_used": result.get("fallback_used"),
        }
        yield (
            "event: done\n"
            f"data: {json.dumps(done_payload)}\n\n"
        )

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering
            "Connection": "keep-alive",
        },
    )


@router.post("/12/evaluate-response")
async def evaluate_coaching_response(body: dict, db: AsyncSession = Depends(get_db)) -> dict:
    """Coach evaluador de respuestas cliente a preguntas M9 coaching.

    Scope evaluador (NO generador): M9 coaching.COACHING_QUESTIONS sigue
    siendo la fuente unica de preguntas. A12 solo evalua.

    Body schema::

        {
          "pregunta_coaching": {
            "id": "Q_CISO_042",
            "role": "CISO|RSEG|CTO|direccion|tech",
            "texto": "...",
            "criterio_L5_ideal": "..."
          },
          "respuesta_cliente": {
            "texto": "texto libre 10-2000 chars",
            "rol_cliente": "CISO|director|sysadmin|staff"
          },
          "client_context": {
            "company_name": "DataForma S.L.",
            "sector": "sanidad|aapp|fintech|otro",
            "ens_category": "BASICA|MEDIA|ALTA"
          },
          "project_id": "<uuid>"?
        }

    Devuelve EvaluationResult + tokens + coste + cache_* + fallback_used.
    """
    from backend.app.agents.agent_12_coach_cliente import (
        Agent12CoachClienteEvaluador,
    )

    pregunta = body.get("pregunta_coaching")
    respuesta = body.get("respuesta_cliente")
    client_context = body.get("client_context")

    if not isinstance(pregunta, dict) or not pregunta:
        raise HTTPException(
            status_code=400,
            detail="Se requiere 'pregunta_coaching' dict",
        )
    if not isinstance(respuesta, dict) or not respuesta:
        raise HTTPException(
            status_code=400,
            detail="Se requiere 'respuesta_cliente' dict con texto",
        )
    if not isinstance(client_context, dict) or not client_context:
        raise HTTPException(
            status_code=400,
            detail="Se requiere 'client_context' dict",
        )

    project_id_raw = body.get("project_id")
    project_id = UUID(project_id_raw) if project_id_raw else None

    agent = Agent12CoachClienteEvaluador()
    try:
        result = await agent.evaluate_client_response(
            db,
            pregunta_coaching=pregunta,
            respuesta_cliente=respuesta,
            client_context=client_context,
            project_id=project_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


    await db.commit()
    return result
@router.post("/12/evaluate-batch")
async def evaluate_coaching_batch(body: dict, db: AsyncSession = Depends(get_db)) -> dict:
    """Batch evaluar multiples respuestas del mismo proyecto.

    Body schema::

        {
          "items": [
            {"pregunta_coaching": {...}, "respuesta_cliente": {...}},
            ...
          ],
          "client_context": {...},
          "project_id": "<uuid>"?
        }

    System prompt cached desde la primera invocacion -> coste
    dramaticamente menor en invocaciones 2..N.
    """
    from backend.app.agents.agent_12_coach_cliente import (
        Agent12CoachClienteEvaluador,
    )

    items = body.get("items")
    client_context = body.get("client_context")

    if not isinstance(items, list) or not items:
        raise HTTPException(
            status_code=400, detail="'items' debe ser lista no vacia",
        )
    if not isinstance(client_context, dict) or not client_context:
        raise HTTPException(
            status_code=400, detail="'client_context' debe ser dict",
        )

    project_id_raw = body.get("project_id")
    project_id = UUID(project_id_raw) if project_id_raw else None

    agent = Agent12CoachClienteEvaluador()
    try:
        results = await agent.evaluate_batch(
            db,
            items=items,
            client_context=client_context,
            project_id=project_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return {"results": results, "count": len(results)}


@router.post("/31/enrich-measure")
async def enrich_dda_measure(body: dict, db: AsyncSession = Depends(get_db)) -> dict:
    """Enriquece una justificacion DdA no_aplica (Sonnet 4.6 JSON strict).

    Body schema::

        {
          "measure_id": "mp.if.7",
          "measure_name": "Registro de entrada y salida",
          "measure_family": "mp.if",
          "base_reason": "cloud_only|scope_exclusion|outsourced|not_applicable_sector|compensated_by_other",
          "client_context": {
            "company_name": "DataForma",
            "sector": "sanidad|aapp|fintech|otro",
            "ens_category": "BASICA|MEDIA|ALTA",
            "is_aapp": false,
            "alcance_texto": "HCE + sede electronica"
          },
          "system_context_from_m22": {
            "hosting_model": "cloud_saas|cloud_iaas|on_premise|hybrid",
            "cloud_providers": ["AWS EU-West"],
            "physical_offices": [{"address": "...", "role": "admin_only"}],
            "frameworks_heredados": ["ISO 27001"],
            "outsourced_services": ["hosting"]
          },
          "project_id": "<uuid>"?
        }

    Devuelve EnrichmentResult + tokens + coste + cache_* + fallback_used.
    """
    from backend.app.agents.agent_31_enriquecedor_dda import (
        Agent31EnriquecedorDdA,
    )

    required = ("measure_id", "measure_name", "base_reason", "client_context")
    for k in required:
        if k not in body:
            raise HTTPException(
                status_code=400, detail=f"Falta campo '{k}'",
            )
    system_ctx = body.get("system_context_from_m22", {}) or {}
    if not isinstance(body["client_context"], dict):
        raise HTTPException(
            status_code=400, detail="client_context debe ser dict",
        )

    project_id_raw = body.get("project_id")
    project_id = UUID(project_id_raw) if project_id_raw else None

    agent = Agent31EnriquecedorDdA()
    try:
        result = await agent.enrich_no_aplica_justification(
            db,
            measure_id=body["measure_id"],
            measure_name=body["measure_name"],
            measure_family=body.get(
                "measure_family",
                body["measure_id"].rsplit(".", 1)[0],
            ),
            base_reason=body["base_reason"],
            client_context=body["client_context"],
            system_context_from_m22=system_ctx,
            project_id=project_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


    await db.commit()
    return result
@router.post("/31/enrich-batch")
async def enrich_dda_batch(body: dict, db: AsyncSession = Depends(get_db)) -> dict:
    """Batch enrich multiples medidas no_aplica de un proyecto.

    Body schema::

        {
          "measures": [
            {"measure_id": "mp.if.7", "measure_name": "...", "measure_family": "mp.if", "base_reason": "cloud_only"},
            ...
          ],
          "client_context": {...},
          "system_context_from_m22": {...},
          "project_id": "<uuid>"?
        }

    Invoca A31 una vez por medida. System prompt cached desde la
    primera invocacion -> coste drammatic menor en invocaciones 2..N.
    """
    from backend.app.agents.agent_31_enriquecedor_dda import (
        Agent31EnriquecedorDdA,
    )

    measures = body.get("measures")
    client_context = body.get("client_context")
    system_ctx = body.get("system_context_from_m22", {}) or {}

    if not isinstance(measures, list) or not measures:
        raise HTTPException(
            status_code=400, detail="measures debe ser lista no vacia",
        )
    if not isinstance(client_context, dict) or not client_context:
        raise HTTPException(
            status_code=400, detail="client_context debe ser dict",
        )

    project_id_raw = body.get("project_id")
    project_id = UUID(project_id_raw) if project_id_raw else None

    agent = Agent31EnriquecedorDdA()
    try:
        results = await agent.enrich_batch(
            db,
            measures=measures,
            client_context=client_context,
            system_context_from_m22=system_ctx,
            project_id=project_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return {"results": results, "count": len(results)}


@router.post("/27/classify-document")
async def classify_document_idms(body: dict, db: AsyncSession = Depends(get_db)) -> dict:
    """Clasifica un documento ambiguo en el catalogo 15 carpetas FULKRO.

    Body schema::

        {
          "document_name": "acta_reunion_15_marzo.docx",
          "content_excerpt": "primeros 500-2000 chars del contenido",
          "deterministic_attempt": {          # opcional (output M24)
            "suggested_folder": "99_Misc",
            "confidence": 0.3
          },
          "client_context": {                 # opcional, default otro/MEDIA
            "sector": "sanidad|aapp|fintech|otro",
            "ens_category": "BASICA|MEDIA|ALTA"
          },
          "document_id": "<uuid>"?,
          "project_id": "<uuid>"?
        }

    Devuelve ClassificationResult + tokens + coste + cache_* + fallback_used.
    """
    from backend.app.agents.agent_27_clasificador import (
        Agent27ClasificadorIDMS,
    )

    if "document_name" not in body:
        raise HTTPException(status_code=400, detail="document_name requerido")
    if "content_excerpt" not in body:
        raise HTTPException(status_code=400, detail="content_excerpt requerido")

    document_id_raw = body.get("document_id")
    project_id_raw = body.get("project_id")

    agent = Agent27ClasificadorIDMS()
    try:
        result = await agent.classify_document(
            db,
            document_name=body["document_name"],
            content_excerpt=body["content_excerpt"],
            deterministic_attempt=body.get("deterministic_attempt"),
            client_context=body.get("client_context"),
            document_id=UUID(document_id_raw) if document_id_raw else None,
            project_id=UUID(project_id_raw) if project_id_raw else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


    await db.commit()
    return result
@router.post("/27/classify-batch")
async def classify_documents_batch(body: dict, db: AsyncSession = Depends(get_db)) -> dict:
    """Batch clasifica multiples documentos ambiguos (coste dominado por caching).

    Body schema::

        {
          "documents": [
            {"document_name": "...", "content_excerpt": "...", "deterministic_attempt": {...}?},
            ...
          ],
          "client_context": {"sector": "...", "ens_category": "..."},
          "project_id": "<uuid>"?
        }
    """
    from backend.app.agents.agent_27_clasificador import (
        Agent27ClasificadorIDMS,
    )

    documents = body.get("documents")
    if not isinstance(documents, list) or not documents:
        raise HTTPException(
            status_code=400, detail="'documents' debe ser lista no vacia",
        )

    project_id_raw = body.get("project_id")
    project_id = UUID(project_id_raw) if project_id_raw else None

    agent = Agent27ClasificadorIDMS()
    try:
        results = await agent.classify_batch(
            db,
            documents=documents,
            client_context=body.get("client_context"),
            project_id=project_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return {"results": results, "count": len(results)}
