"""FULKRO agent framework.

Sesion 9 (2026-04-23): tras auditoria solapamiento se eliminaron
10 agentes scaffolding redundantes con motores. Registry documenta
status por id (activo/scaffolding/deprecated/reservado).
"""

from backend.app.agents.base import AgentBase  # noqa: F401
from backend.app.agents.registry import (  # noqa: F401
    AGENT_REGISTRY,
    get_agent_info,
    list_active_agents,
    list_agents,
)
