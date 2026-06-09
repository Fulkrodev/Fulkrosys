"""FRENTE E · N6 · memoria del copiloto ENTRE conversaciones, por proyecto.

Directiva Marcos: el copiloto ADMIN recuerda todo el proyecto entre
conversaciones (aislado por ``project_id``) y el copiloto CLIENTE igual para el
suyo (aislado por ``client_id`` + ``project_id`` · RLS 3-way OR).

Diseño (seguridad + robustez):
- SESIÓN SEPARADA (``async_session``) para las operaciones de memoria · un fallo
  aquí NUNCA corrompe la transacción de la request ni resetea el GUC RLS
  ``is_local`` del flujo cliente (que NO debe commitearse a mitad de request).
- BEST-EFFORT: si la persistencia/lectura falla (RLS, BD, etc.) se degrada al
  comportamiento stateless actual SIN romper la respuesta del copiloto.
- Contexto RLS correcto por actor (política ``copilot_isolation`` 3-way OR):
  · CLIENTE → ``set_tenant_context(client_id=...)`` (rama client).
  · ADMIN   → ``set_tenant_context(project_id=...)`` (rama project · client_id NULL).

Reusa el ``conversation_service`` de m11 (CLUSTER 4 Phase 4E · no duplicar).
"""
from __future__ import annotations

import logging
import uuid
from typing import Optional

from backend.app.database import async_session, set_tenant_context
from backend.app.motors.m11_copiloto.conversation_service import (
    get_or_create_active_conversation,
    get_recent_messages,
    persist_message,
)

logger = logging.getLogger(__name__)

# Autor sentinel del copiloto admin · FULKRO opera con un único admin (Marcos ·
# ADR-013 + ADR-020). La conversación admin se clava por (project_id, autor).
_ADMIN_AUTHOR = uuid.UUID("00000000-0000-0000-0000-000000000a11")

HISTORY_LIMIT = 8


async def _set_memory_ctx(
    session, *, project_id: Optional[uuid.UUID], client_id: Optional[uuid.UUID]
) -> None:
    """Fija el contexto RLS correcto según el actor (3-way OR)."""
    if client_id is not None:
        await set_tenant_context(session, client_id=client_id)
    elif project_id is not None:
        await set_tenant_context(session, project_id=project_id)


async def load_conversation_history(
    *,
    project_id: Optional[uuid.UUID],
    client_user_id: Optional[uuid.UUID] = None,
    client_id: Optional[uuid.UUID] = None,
    limit: int = HISTORY_LIMIT,
) -> tuple[Optional[uuid.UUID], list[dict]]:
    """Resuelve la conversación activa + devuelve historial reciente.

    Returns ``(conversation_id, history)`` donde history = lista cronológica
    ``[{role, content}, ...]`` lista para inyectar antes del mensaje actual.
    Best-effort: ``(None, [])`` si algo falla.
    """
    if project_id is None:
        return None, []
    author = client_user_id or _ADMIN_AUTHOR
    try:
        async with async_session() as s:
            await _set_memory_ctx(s, project_id=project_id, client_id=client_id)
            conv = await get_or_create_active_conversation(
                s,
                project_id=project_id,
                client_user_id=author,
                client_id=client_id,
            )
            msgs = await get_recent_messages(s, conversation_id=conv.id, limit=limit)
            history = [
                {"role": m.role, "content": m.content}
                for m in msgs
                if m.role in ("user", "assistant") and m.content
            ]
            await s.commit()
            return conv.id, history
    except Exception:  # best-effort · degrada a stateless
        logger.exception("copilot N6 load_conversation_history best-effort failed")
        return None, []


async def persist_exchange(
    *,
    conversation_id: Optional[uuid.UUID],
    project_id: Optional[uuid.UUID],
    user_text: Optional[str],
    assistant_text: Optional[str],
    client_id: Optional[uuid.UUID] = None,
) -> None:
    """Persiste el turno (usuario + asistente) · sesión separada · best-effort."""
    if conversation_id is None or project_id is None:
        return
    try:
        async with async_session() as s:
            await _set_memory_ctx(s, project_id=project_id, client_id=client_id)
            if user_text and user_text.strip():
                await persist_message(
                    s,
                    conversation_id=conversation_id,
                    project_id=project_id,
                    role="user",
                    content=user_text.strip()[:8000],
                )
            if assistant_text and assistant_text.strip():
                await persist_message(
                    s,
                    conversation_id=conversation_id,
                    project_id=project_id,
                    role="assistant",
                    content=assistant_text.strip()[:8000],
                )
            await s.commit()
    except Exception:  # best-effort · la respuesta ya se entregó al usuario
        logger.exception("copilot N6 persist_exchange best-effort failed")
