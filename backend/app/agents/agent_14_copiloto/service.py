"""Core service for Agent 14 — ENS Copilot.

Pipeline: detect_filters -> hybrid_search -> build_messages -> LLM -> validate -> log.

Sub-fase 5.5.F integración M30 (plan v4.2 5.5.4.1): si
``query.project_id`` está presente, se deriva ``client_id`` via
``get_project_owner()`` y se inyecta sección "Contactos del
cliente" en el mensaje ``user`` con líneas formateadas por
``ClientContactService.get_for_copilot_context``.
"""
import asyncio
import hashlib
import json
import logging
import uuid
from typing import AsyncIterator

from sqlalchemy import text as sa_text

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.ai.llm_router import get_default_llm_router
from backend.app.corpus.retrieval import hybrid_search, HybridResult
from backend.app.models.knowledge import LLMInteractionLog

from backend.app.agents.agent_14_copiloto.prompts import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    build_base_system_prompt,
)
from backend.app.agents.agent_14_copiloto.types import (
    CopilotQuery,
    CopilotResponse,
    PageContext,
)
from backend.app.agents.agent_14_copiloto.filters import detect_filters
from backend.app.agents.agent_14_copiloto.citation_validator import (
    assess_grounding,
    extract_citations,
    is_not_in_corpus,
)

# NEW8 corpus_gap threshold: max cosine sim of best vector hit (raw,
# pre-RRF). Below this we mark the response as low-confidence retrieval so
# the frontend can show a "fuente no disponible aún en corpus" badge AND
# the system prompt switches to the fallback branch (no hallucination,
# point to official external sources instead).
# Default 0.45 · override via env FULKRO_CORPUS_GAP_CONFIDENCE_THRESHOLD
# (settings.corpus_gap_confidence_threshold · SAN-B.MB-6.6).
from backend.app.config import get_settings as _get_settings_cgt

CORPUS_GAP_CONFIDENCE_THRESHOLD = _get_settings_cgt().corpus_gap_confidence_threshold


CORPUS_GAP_FALLBACK_PROMPT = """\

## INSTRUCCIÓN CRÍTICA · posible fuente no disponible en corpus

La consulta del usuario podría requerir fuentes específicas que NO están \
aún en el corpus RAG de FULKRO (confidence < 0.45 en retrieval vectorial).

REGLAS ESTRICTAS para esta respuesta:

1. NO inventes contenido. NO digas "según mi conocimiento general" ni \
   "en general la normativa indica". NO uses tu pre-training para llenar \
   el hueco.
2. Indica EXPLÍCITAMENTE al usuario que esta información requiere una \
   fuente que aún no está en el corpus de FULKRO.
3. Sugiere fuentes oficiales externas relevantes según la temática:
   - CCN-STIC (guías técnicas ENS): https://www.ccn-cert.cni.es/series-ccn-stic.html
   - BOE (RD 311/2022 y normativa derivada): https://www.boe.es/buscar/
   - AEPD (RGPD/LOPDGDD): https://www.aepd.es/
   - Reglamento eIDAS UE 910/2014: https://eur-lex.europa.eu/
4. Estructura tu respuesta así:
   "Esta consulta requiere fuentes que aún no están disponibles en el \
    corpus de FULKRO. Te recomiendo consultar directamente: [URL \
    relevante a la temática]. Si necesitas un análisis específico \
    aplicado a tu proyecto, Marcos puede ingestar la fuente bajo demanda."
5. Mantén tono profesional · NO te disculpes excesivamente.
"""

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_user_message(question: str, chunks: list[HybridResult]) -> str:
    """Build the user message with RAG context chunks."""
    context_parts = ["CONTEXTO RAG:\n"]
    for i, c in enumerate(chunks, 1):
        label = c.measure_code or c.article_ref or c.heading_path or c.document_title
        context_parts.append(f"--- CHUNK {i} [{label}] ---")
        context_parts.append(c.content[:1200])
        context_parts.append("")
    context_parts.append(f"PREGUNTA: {question}")
    return "\n".join(context_parts)


async def _resolve_client_id_from_project(
    session: AsyncSession, project_id: str | uuid.UUID,
) -> uuid.UUID | None:
    """Helper sub-fase 5.5.F: derive client_id desde project_id."""
    pid = project_id if isinstance(project_id, uuid.UUID) else uuid.UUID(str(project_id))
    cid = (await session.execute(
        sa_text("SELECT get_project_owner(:pid)"),
        {"pid": str(pid)},
    )).scalar()
    if cid is None:
        return None
    return cid if isinstance(cid, uuid.UUID) else uuid.UUID(str(cid))


async def _build_m30_contacts_section(
    session: AsyncSession, client_id: uuid.UUID,
) -> str:
    """Sub-fase 5.5.F integración A14↔M30 (plan v4.2 5.5.4.1).

    Devuelve sección formateada con contactos cliente activos para
    inyectar al user message. Vacío si no hay contactos.
    """
    from backend.app.motors.m30_client_contacts.service import (
        ClientContactService,
    )

    entries = await ClientContactService(session).get_for_copilot_context(
        client_id,
    )
    if not entries:
        return ""
    lines = ["## Contexto cliente (Contactos M30)"]
    for e in entries:
        lines.append(e.formatted_line)
    return "\n".join(lines)


def _prompt_hash(messages: list[dict]) -> str:
    """SHA-256 hash of the full prompt for deduplication logging."""
    raw = "".join(m.get("content", "") for m in messages)
    return hashlib.sha256(raw.encode()).hexdigest()


async def _enrich_user_message_with_m30(
    session: AsyncSession,
    page_context: PageContext | None,
    project_id: str | uuid.UUID | None,
    base_user_message: str,
) -> str:
    """Prepend the M30 client-contacts section if a client_id can be resolved.

    Precedencia de resolución de client_id (de mayor a menor prioridad):
        1. ``page_context.client_id`` — explícito desde el frontend.
           Ruta principal para vistas que ya conocen el cliente activo
           (p.ej. ``/clients/<id>`` o ``/copilot?client_id=<id>``) sin
           necesidad de pasar por un proyecto.
        2. ``project_id`` — derivado vía ``get_project_owner(project_id)``.
           Ruta legacy/compat para endpoints donde el contexto natural es
           el proyecto (`/projects/<id>/copilot/...`).
        3. None — no se inyecta sección M30 y se devuelve el mensaje tal cual.

    Razón de la precedencia: el frontend puede saber el cliente activo
    aunque no haya un proyecto en contexto (vista cross-project), por lo
    que ``page_context.client_id`` debe ganar siempre. Solo cuando el
    frontend no lo envía caemos al lookup por proyecto.

    Args:
        session: AsyncSession activa (con RLS aplicada por el caller si toca).
        page_context: PageContext opcional enviado por el frontend.
        project_id: project_id legacy si se conoce.
        base_user_message: mensaje original a enriquecer.

    Returns:
        Mensaje enriquecido con sección "Contexto cliente (Contactos M30)"
        si se resuelve client_id Y el cliente tiene contactos vivos. En
        cualquier otro caso, el mensaje original sin cambios.
    """
    client_id: uuid.UUID | None = None
    if page_context and page_context.client_id:
        try:
            client_id = uuid.UUID(str(page_context.client_id))
        except (ValueError, TypeError):
            client_id = None
    if client_id is None and project_id:
        client_id = await _resolve_client_id_from_project(session, project_id)
    if client_id is None:
        return base_user_message
    contacts_section = await _build_m30_contacts_section(session, client_id)
    if not contacts_section:
        return base_user_message
    return contacts_section + "\n\n" + base_user_message


# Sesión 3B-2B.8 CLUSTER 4 Phase 4A · coach mode guidance template
# Inject coach context cuando page_context.coach_mode=True · reuse
# compute_workflow_state next_cliente_actions current_phase.
_COACH_MODE_GUIDANCE_TEMPLATE = (
    "## Modo coach activo\n\n"
    "El cliente está en la fase ENS: **{phase}**.\n"
    "Su próxima tarea: {pending_action}\n\n"
    "Ajustes obligatorios en tu respuesta:\n"
    "- Tono coach amigable · primer-principios cliente · NO ENS técnico sin "
    "TooltipENS\n"
    "- Explica qué le toca al cliente y POR QUÉ importa (impacto compliance)\n"
    "- \"Sin prisa por tu parte\" R29 firmísimo · NO presión coercitiva\n"
    "- Cliente NO genera contenido ENS · solo recibe / aprueba / firma · "
    "Marcos owns content authoritative\n"
    "- Si cliente pregunta algo fuera de su fase actual · responde + sugiere "
    "amigablemente su tarea actual cuando aplique"
)


# Sesión 3B-2B.8 CLUSTER 2 Phase 2E · category-aware guidance per categoría
# proyecto cliente · LLM tailorea explanations sin model switching (Future-
# 1.E.copilot-model-per-category demand-driven post-piloto · LLM cost concern).
_CATEGORY_GUIDANCE: dict[str, str] = {
    "BASICA": (
        "## Categoría del proyecto cliente · BÁSICA\n\n"
        "El proyecto del cliente está categorizado como **BÁSICA** (RD 311/2022 Anexo I).\n"
        "Ajustes obligatorios en tu respuesta:\n"
        "- Lenguaje simplificado · evita jerga técnica avanzada.\n"
        "- Enfatiza que NO se requiere auditoría externa ENAC · solo "
        "self-declaration E-041 + distintivo.\n"
        "- Menciona únicamente medidas BÁSICA aplicables (ignora MEDIA/ALTA cuando "
        "respondas qué le aplica al cliente).\n"
        "- Tono \"sin prisa\" R29 · cliente cumple compliance ligero · NO ENS "
        "técnico complejo expectation."
    ),
    "MEDIA": (
        "## Categoría del proyecto cliente · MEDIA\n\n"
        "El proyecto del cliente está categorizado como **MEDIA** (RD 311/2022 Anexo I).\n"
        "Ajustes obligatorios en tu respuesta:\n"
        "- Lenguaje audit-ready · cliente firmará compromiso pre-auditoría ENAC obligatoria.\n"
        "- Menciona auditoría externa ENAC cuando relevante (declaración conformidad "
        "ANTES auditor externo).\n"
        "- Medidas BÁSICA + MEDIA aplicables (ignora ALTA cuando respondas qué le toca).\n"
        "- Tono profesional pero accessible R29 · cliente espera trazabilidad ENAC."
    ),
    "ALTA": (
        "## Categoría del proyecto cliente · ALTA\n\n"
        "El proyecto del cliente está categorizado como **ALTA** (RD 311/2022 Anexo I).\n"
        "Ajustes obligatorios en tu respuesta:\n"
        "- Enfatiza vigilancia 24/7 SOC obligatoria · DR (Disaster Recovery) drills + BIA.\n"
        "- Audit annual ENAC + pentest externo recurrente requeridos.\n"
        "- Todas las medidas BÁSICA + MEDIA + ALTA aplicables.\n"
        "- Tono detallado · cliente espera depth técnico R29 manteniendo friendly tone "
        "(NO admin lingo · TooltipENS para acrónimos)."
    ),
}


def _build_screen_actions_block(role: str, screen_path: str | None) -> str | None:
    """Lookup the role's screen_references_catalog → bloque de botones activos.

    2026-06-09 · reusa el catálogo de personas (admin ~43 pantallas con botones ·
    cliente per /client-portal/*) para que el copiloto referencie los BOTONES
    CONCRETOS de la pantalla actual. Devuelve None si no hay screen o no matchea
    (el builder degrada a guidance conceptual). Best-effort · NUNCA lanza.
    """
    if not screen_path:
        return None
    try:
        from backend.app.agents.copilot_personas_loader import (
            get_persona,
            lookup_screen_reference,
        )

        persona = get_persona(role if role in ("admin", "cliente") else "cliente")
        ref = lookup_screen_reference(persona, screen_path)
    except Exception:  # noqa: BLE001 · best-effort
        return None
    if ref is None:
        return None
    bullets = "\n".join(f"  - {a}" for a in ref.actions)
    return (
        f"## Pantalla activa: {ref.screen_name} (motor {ref.motor})\n"
        f"{ref.context_hints}\n"
        f"Botones/acciones disponibles en esta pantalla "
        f"(referéncialos por su nombre exacto cuando guíes al usuario):\n"
        f"{bullets}"
    )


def _build_system_prompt(
    page_context: PageContext | None,
    corpus_gap: bool = False,
    role: str = "cliente",
) -> str:
    """Compose the system prompt, role-aware (cliente | admin) y enriquecido con
    contexto de página activa, botones de pantalla, estado de proyecto en vivo y
    la rama de fallback corpus_gap.

    2026-06-09 · ``role`` selecciona el bloque de conocimiento de plataforma
    (cliente vs admin) y el screen_references_catalog. Antes el prompt empotraba
    SIEMPRE el portal cliente → el admin recibía el mapa equivocado.

    El fallback corpus_gap se anexa cuando ``corpus_gap`` es True (prohíbe
    alucinar · apunta a fuentes oficiales externas). Phase 2E · category-aware
    guidance + Phase 4A coach mode se conservan.
    """
    base = build_base_system_prompt(role)
    if page_context:
        lines: list[str] = []
        if page_context.url:
            lines.append(f"- URL activa: {page_context.url}")
        if page_context.active_motor:
            lines.append(f"- Motor activo: {page_context.active_motor}")
        if page_context.project_phase:
            lines.append(f"- Fase del proyecto: {page_context.project_phase}")
        if lines:
            base = base + "\n\n## Contexto activo del usuario\n" + "\n".join(lines)

        # 2026-06-09 · botones de la pantalla activa (screen_references_catalog).
        # Usa current_screen explícito o, si falta, la URL del page_context.
        screen_block = _build_screen_actions_block(
            role, page_context.current_screen or page_context.url,
        )
        if screen_block:
            base = base + "\n\n" + screen_block

        # 2026-06-09 · estado dinámico del proyecto (pre-compuesto por el caller
        # con copilot_project_state.build_project_state_block · role-filtered).
        if page_context.project_state:
            base = base + "\n\n" + page_context.project_state

        # Phase 2E · category-aware guidance
        category_guidance = _CATEGORY_GUIDANCE.get(
            (page_context.ens_category or "").upper(),
        )
        if category_guidance:
            base = base + "\n\n" + category_guidance

        # Phase 4A · coach mode guidance injection
        if page_context.coach_mode:
            phase = page_context.coach_current_phase or "actual"
            pending = (
                page_context.coach_pending_action
                or "revisa lo que tienes pendiente · sin prisa por tu parte"
            )
            coach_block = _COACH_MODE_GUIDANCE_TEMPLATE.format(
                phase=phase, pending_action=pending,
            )
            base = base + "\n\n" + coach_block

    if corpus_gap:
        base = base + CORPUS_GAP_FALLBACK_PROMPT
    return base


def _chunk_to_preview(chunk: HybridResult, preview_chars: int = 200) -> dict:
    """Serialize a HybridResult into the compact preview form used in done frames.

    Multi-tenant note: ``knowledge_chunks`` es corpus público compartido
    (RD 311/2022, CCN-STIC, BOE, eIDAS) — el modelo en
    ``backend/app/models/knowledge.py`` no tiene columna ``client_id`` por
    diseño. Mostrar el preview a cualquier cliente NO viola aislamiento
    porque el contenido es info regulatoria pública. El aislamiento
    multi-tenant aplica a tablas con datos del cliente
    (``copilot_conversations``, ``copilot_messages``, ``dda_entries``,
    ``evidence``…) protegidas vía RLS por ``_set_project_rls``.
    """
    source = (
        chunk.measure_code
        or chunk.article_ref
        or chunk.heading_path
        or chunk.document_title
        or "Fuente"
    )
    return {
        "chunk_id": chunk.chunk_id,
        "source": source,
        "preview": (chunk.content or "")[:preview_chars],
        "score": round(chunk.rrf_score, 6),
    }


def _match_citation_to_chunk(
    raw: str, chunks: list[HybridResult]
) -> tuple[HybridResult | None, str | None]:
    """Best-effort match of a raw citation string to one of the RAG chunks.

    Tries measure_code first, then article_ref, then heading_path, then
    document_title — case insensitive substring match against the raw
    citation text. Returns (chunk_or_none, measure_code_or_none).
    """
    needle = raw.lower()
    measure_hit: str | None = None
    for c in chunks:
        if c.measure_code and c.measure_code.lower() in needle:
            measure_hit = c.measure_code
            return c, measure_hit
    for c in chunks:
        if c.article_ref and c.article_ref.lower() in needle:
            return c, None
    for c in chunks:
        if c.heading_path and c.heading_path.lower() in needle:
            return c, None
    for c in chunks:
        title = (c.document_title or "").lower()
        if title and any(tok in needle for tok in title.split() if len(tok) > 4):
            return c, None
    return None, None


def _normalize_citation_label(raw: str) -> str:
    """Cheap normalization of a citation label for de-duplication keys."""
    return " ".join(raw.lower().split())


# ---------------------------------------------------------------------------
# S14 · Suggested actions (deterministas · R1 · sin LLM)
# ---------------------------------------------------------------------------

# Mapa motor activo (derivado del screen actual en el frontend) → siguiente
# paso lógico del ciclo ENS. Rutas verificadas contra
# frontend/app/(admin)/admin/projects/[id]/*  (NO fabricadas).
_ADMIN_NEXT_STEP: dict[str, tuple[str, str]] = {
    "magerit": ("dda", "Ir a la Declaración de Aplicabilidad"),
    "obligations": ("evidence", "Ir a evidencias"),
    "conformity": ("renewal", "Ir a renovación"),
    "diagnosis": ("plan", "Ir al plan de adecuación"),
    "evidence": ("dossier", "Ir al dossier ENS"),
}


def suggest_actions(query: CopilotQuery) -> list[dict]:
    """Acciones sugeridas deterministas, role-aware (R1 · sin LLM).

    Solo el copiloto admin con proyecto activo y un motor reconocido recibe un
    chip ``navigate`` al siguiente paso del ciclo ENS (sección project-scoped
    real). Sin contexto suficiente devuelve ``[]`` — nunca fabrica chips.
    """
    pc = query.page_context
    if query.role != "admin" or pc is None or not query.project_id:
        return []
    motor = (pc.active_motor or "").strip().lower()
    nxt = _ADMIN_NEXT_STEP.get(motor)
    if nxt is None:
        return []
    segment, label = nxt
    return [
        {
            "id": f"nav-{segment}",
            "label": label,
            "kind": "navigate",
            "payload": {"url": f"/admin/projects/{query.project_id}/{segment}"},
        }
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def answer_question(
    session: AsyncSession,
    query: CopilotQuery,
) -> CopilotResponse:
    """Full copilot pipeline: RAG retrieval -> LLM -> validation -> logging.

    Args:
        session: Async DB session for retrieval and logging.
        query: CopilotQuery with the user question and optional overrides.

    Returns:
        CopilotResponse with answer, citations, grounding info, and metrics.
    """
    # Ejecutable 8 Pasada 16 (F-13-02): LLM prompt-injection guard pre-LLM. Antes DEAD CODE
    # (0 callers en producción). Bloquea jailbreak/system-extraction antes de llegar al LLM.
    from backend.app.security.llm_prompt_injection_guard import sanitize_user_input
    _pi = sanitize_user_input(query.question)
    if _pi.should_block:
        logger.warning(
            "Copilot A14 PI guard blocked input · categorias=%s",
            [v.category for v in _pi.violations],
        )
        return CopilotResponse(
            answer=(
                "Lo siento, no puedo procesar esa solicitud. Si tienes una duda sobre tu "
                "proceso ENS, reformúlala con normalidad y te ayudo encantado."
            ),
            not_in_corpus=True,
            model_used="guard:blocked",
        )

    # 1. Detect filters from the question
    filters = detect_filters(query.question)

    # 2. Hybrid search for relevant chunks
    search_kwargs: dict = {
        "session": session,
        "query": query.question,
        "top_k": 5,
    }
    if filters.measure_codes_mentioned:
        search_kwargs["measure_codes"] = filters.measure_codes_mentioned
    elif filters.only_with_measure_code:
        search_kwargs["only_with_measure_code"] = True
    if filters.source_codes:
        search_kwargs["source_codes"] = filters.source_codes

    chunks = await hybrid_search(**search_kwargs)

    # 3. Build messages
    model = query.requested_model or DEFAULT_MODEL
    max_tokens = query.max_tokens or DEFAULT_MAX_TOKENS

    confidence = chunks[0].confidence if chunks else 0.0
    corpus_gap = confidence < CORPUS_GAP_CONFIDENCE_THRESHOLD

    user_message = _build_user_message(query.question, chunks)

    # Sub-fase 5.5.F integración M30: enrichment con contactos cliente
    # cuando se puede resolver client_id (page_context o project_id).
    user_message = await _enrich_user_message_with_m30(
        session, query.page_context, query.project_id, user_message,
    )

    messages = [
        {
            "role": "system",
            "content": _build_system_prompt(
                query.page_context, corpus_gap, role=query.role,
            ),
        },
        # E-4 · memoria: turnos previos del hilo entre system y la pregunta.
        *query.history,
        {"role": "user", "content": user_message},
    ]

    # 4. Call LLM via sync router wrapped in executor
    router = get_default_llm_router()
    loop = asyncio.get_event_loop()
    llm_result = await loop.run_in_executor(
        None,
        lambda: router.complete(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=DEFAULT_TEMPERATURE,
        ),
    )

    answer = llm_result.content

    # 5. Validate grounding and extract citations
    citations = extract_citations(answer)
    not_in_corpus = is_not_in_corpus(answer)
    low_grounding = assess_grounding(answer, chunks)
    chunk_ids = [c.chunk_id for c in chunks]

    # 6. Log the interaction
    from backend.app.core.ai.pricing import compute_cost_usd
    p_hash = _prompt_hash(messages)
    log_entry = LLMInteractionLog(
        project_id=query.project_id if query.project_id else None,
        # §4.5 audit-2026-06-15 · feature ROLE-AWARE: el chat del cliente
        # (portal_api · query.role=='cliente') se etiqueta copilot_cliente_chat
        # para que cuente en el cap CLIENTE y NO envenene el cap admin (antes se
        # logueaba 'copilot_chat' = etiqueta admin → la vía cliente dominante
        # escapaba su tope y contaminaba el de Marcos).
        feature=("copilot_cliente_chat" if query.role == "cliente" else "copilot_chat"),
        model=llm_result.model,
        prompt_hash=p_hash,
        prompt_preview=query.question[:500],
        response_preview=answer[:500],
        prompt_tokens=llm_result.prompt_tokens,
        completion_tokens=llm_result.completion_tokens,
        total_tokens=llm_result.total_tokens,
        cost_usd=compute_cost_usd(  # §4.5
            llm_result.model,
            llm_result.prompt_tokens,
            llm_result.completion_tokens,
        ),
        latency_ms=int(llm_result.latency_ms),
        status="success",
    )
    session.add(log_entry)
    await session.flush()

    # 7. Return structured response
    return CopilotResponse(
        answer=answer,
        citations_found=citations,
        chunk_ids_used=chunk_ids,
        not_in_corpus=not_in_corpus,
        low_grounding_confidence=low_grounding,
        model_used=llm_result.model,
        tokens_input=llm_result.prompt_tokens,
        tokens_output=llm_result.completion_tokens,
        latency_ms=int(llm_result.latency_ms),
        interaction_log_id=log_entry.id,
        actions=suggest_actions(query),
    )


async def stream_answer_question(
    session: AsyncSession,
    query: CopilotQuery,
) -> AsyncIterator[str]:
    """Stream the copilot answer as SSE frames.

    Emits (one per line, framed as ``data: {json}\\n\\n``):
    - ``{"type": "start", "chunks_used": n, "chunk_ids": [...], ...}``
    - ``{"type": "delta", "text": "..."}`` for each token arriving from the LLM
    - ``{"type": "citation", "data": {"raw": ..., "norm": ..., ...}}`` once per
      new citation detected mid-stream (best-effort match against RAG chunks)
    - ``{"type": "done", "data": {"answer": ..., "chunks_used": [...],
      "confidence": x, "corpus_gap": bool, ...}}``
    - ``{"type": "error", "error": "..."}`` if retrieval/LLM fails

    The caller (FastAPI endpoint) wraps this with ``StreamingResponse``.
    """
    def _frame(event: dict) -> str:
        return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    # Ejecutable 8 Pasada 16 (F-13-02): PI guard pre-LLM también en el path streaming.
    from backend.app.security.llm_prompt_injection_guard import sanitize_user_input
    _pi = sanitize_user_input(query.question)
    if _pi.should_block:
        logger.warning(
            "Copilot A14 stream PI guard blocked input · categorias=%s",
            [v.category for v in _pi.violations],
        )
        _refusal = (
            "Lo siento, no puedo procesar esa solicitud. Si tienes una duda sobre tu "
            "proceso ENS, reformúlala con normalidad y te ayudo encantado."
        )
        yield _frame({"type": "delta", "text": _refusal})
        yield _frame({"type": "done", "data": {"answer": _refusal, "corpus_gap": True}})
        return

    try:
        filters = detect_filters(query.question)
        search_kwargs: dict = {"session": session, "query": query.question, "top_k": 5}
        if filters.measure_codes_mentioned:
            search_kwargs["measure_codes"] = filters.measure_codes_mentioned
        elif filters.only_with_measure_code:
            search_kwargs["only_with_measure_code"] = True
        if filters.source_codes:
            search_kwargs["source_codes"] = filters.source_codes
        chunks = await hybrid_search(**search_kwargs)
    except Exception as exc:
        logger.exception("Copilot retrieval failed")
        yield _frame({"type": "error", "error": f"retrieval_failed: {exc}"})
        return

    model = query.requested_model or DEFAULT_MODEL
    max_tokens = query.max_tokens or DEFAULT_MAX_TOKENS
    confidence = chunks[0].confidence if chunks else 0.0
    corpus_gap = confidence < CORPUS_GAP_CONFIDENCE_THRESHOLD
    user_message = _build_user_message(query.question, chunks)
    user_message = await _enrich_user_message_with_m30(
        session, query.page_context, query.project_id, user_message,
    )
    messages = [
        {
            "role": "system",
            "content": _build_system_prompt(
                query.page_context, corpus_gap, role=query.role,
            ),
        },
        # E-4 · memoria: turnos previos del hilo entre system y la pregunta.
        *query.history,
        {"role": "user", "content": user_message},
    ]

    yield _frame({
        "type": "start",
        "chunks_used": len(chunks),
        "chunk_ids": [c.chunk_id for c in chunks],
        "measure_codes": filters.measure_codes_mentioned,
        "confidence": round(confidence, 6),
        "corpus_gap": corpus_gap,
    })

    router = get_default_llm_router()
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()
    SENTINEL = object()

    def _producer() -> None:
        try:
            for delta in router.stream_complete(
                messages=messages,
                model=model,
                max_tokens=max_tokens,
                temperature=DEFAULT_TEMPERATURE,
            ):
                loop.call_soon_threadsafe(queue.put_nowait, delta)
        except Exception:  # noqa: BLE001
            # §2.4 · NO exponer str(exc) al cliente (puede filtrar detalle del
            # router LLM). Log server-side + mensaje genérico en el frame SSE.
            logger.exception("Copiloto: stream LLM (producer) falló")
            loop.call_soon_threadsafe(
                queue.put_nowait,
                ("__error__", "Error en el copiloto. Inténtalo de nuevo."),
            )
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, SENTINEL)

    loop.run_in_executor(None, _producer)

    parts: list[str] = []
    seen_citations: set[str] = set()
    while True:
        item = await queue.get()
        if item is SENTINEL:
            break
        if isinstance(item, tuple) and len(item) == 2 and item[0] == "__error__":
            yield _frame({"type": "error", "error": item[1]})
            return
        parts.append(item)
        yield _frame({"type": "delta", "text": item})

        # Detect new citations as soon as the running text contains them.
        running = "".join(parts)
        for raw in extract_citations(running):
            key = _normalize_citation_label(raw)
            if key in seen_citations:
                continue
            seen_citations.add(key)
            chunk_match, measure = _match_citation_to_chunk(raw, chunks)
            yield _frame({
                "type": "citation",
                "data": {
                    "raw": raw,
                    "norm": key,
                    "measure": measure,
                    "chunk_id": chunk_match.chunk_id if chunk_match else None,
                    "preview": (chunk_match.content or "")[:200] if chunk_match else None,
                },
            })

    answer = "".join(parts)
    citations = extract_citations(answer)
    not_in_corpus = is_not_in_corpus(answer)
    low_grounding = assess_grounding(answer, chunks)

    try:
        from backend.app.core.ai.pricing import compute_cost_usd
        p_hash = _prompt_hash(messages)
        # §4.5 · el stream no devuelve usage exacto → estimación por longitud
        # (~4 chars/token) sobre pregunta + contexto RAG + respuesta, para que el
        # cap de tokens/coste mensual también contabilice esta vía (antes 0 → evasión).
        ctx_chars = sum(
            len(getattr(c, "text", "") or getattr(c, "content", "") or "")
            for c in chunks
        )
        est_in = max(1, (len(query.question) + ctx_chars) // 4)
        est_out = max(1, len(answer) // 4)
        log_entry = LLMInteractionLog(
            project_id=query.project_id if query.project_id else None,
            # §4.5 · feature ROLE-AWARE (ver answer_question).
            feature=(
                "copilot_cliente_chat_stream" if query.role == "cliente"
                else "copilot_chat_stream"
            ),
            model=model,
            prompt_hash=p_hash,
            prompt_preview=query.question[:500],
            response_preview=answer[:500],
            prompt_tokens=est_in,
            completion_tokens=est_out,
            total_tokens=est_in + est_out,
            cost_usd=compute_cost_usd(model, est_in, est_out),
            latency_ms=0,
            status="success",
        )
        session.add(log_entry)
        await session.flush()
        log_id = log_entry.id
    except Exception:  # noqa: BLE001
        log_id = None

    yield _frame({
        "type": "done",
        "data": {
            "answer": answer,
            "citations_found": citations,
            "chunk_ids_used": [c.chunk_id for c in chunks],
            "chunks_used": [_chunk_to_preview(c) for c in chunks],
            "not_in_corpus": not_in_corpus,
            "low_grounding_confidence": low_grounding,
            "confidence": round(confidence, 6),
            "corpus_gap": corpus_gap,
            "model_used": model,
            "interaction_log_id": log_id,
            "actions": suggest_actions(query),
        },
    })
