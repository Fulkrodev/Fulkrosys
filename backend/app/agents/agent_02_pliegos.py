"""Agent 2 — Analizador de Pliegos."""
from backend.app.agents.base import AgentBase
from backend.app.agents.prompts.agent_02_pliegos import PROMPT


class AnalizadorPliegosAgent(AgentBase):
    AGENT_ID = 2
    AGENT_NAME = "Analizador de Pliegos"
    MODEL = "sonnet-4.5"
    TEMPERATURE = 0.1
    SPECIFIC_PROMPT = PROMPT

    async def analyze_pliego(
        self, db, pliego_text: str, expediente_metadata: dict | None = None
    ) -> dict:
        return await self.invoke(
            db,
            user_message=(
                "Analiza este pliego de contratacion publica y extrae los requisitos ENS:\n\n"
                + pliego_text[:12000]
            ),
            context=expediente_metadata,
            structured_output=True,
        )
