"""Agent 21 — Detector Discrepancias."""
from backend.app.agents.base import AgentBase
from backend.app.agents.prompts.agent_21_discrepancias import PROMPT


class DetectorDiscrepanciasAgent(AgentBase):
    AGENT_ID = 21
    AGENT_NAME = "Detector Discrepancias"
    MODEL = "sonnet-4.5"
    TEMPERATURE = 0.1
    SPECIFIC_PROMPT = PROMPT

    async def detect_discrepancies(self, db, project_id, sources: dict) -> dict:
        return await self.invoke(
            db,
            project_id=project_id,
            user_message=(
                "Analiza las fuentes de informacion del proyecto y detecta "
                "discrepancias e incoherencias."
            ),
            context=sources,
            structured_output=True,
        )
