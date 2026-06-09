"""Agent 14 — Copiloto Conversacional.

This package hosts the production RAG pipeline for the ENS copilot
(service.py, prompts.py, filters.py, types.py, citation_validator.py).

The ``CopilotoAgent`` class registered here is a thin AgentBase wrapper
so the agent is discoverable by the 27-agent framework; the production
answer path still runs through ``service.answer_question``.
"""
from backend.app.agents.base import AgentBase
from backend.app.agents.prompts.agent_14_copiloto import PROMPT


class CopilotoAgent(AgentBase):
    AGENT_ID = 14
    AGENT_NAME = "Copiloto Conversacional"
    MODEL = "sonnet-4.5"
    TEMPERATURE = 0.2
    SPECIFIC_PROMPT = PROMPT


__all__ = ["CopilotoAgent"]
