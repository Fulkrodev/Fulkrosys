"""L-9 (FRENTE L) · el copiloto conoce el perfil AUTÓNOMO (Art. 11 RD 311/2022).

Acumulación de roles permitida con justificación documentada · nunca como
simplificación sin más · nunca infiere que ENAC la acepta sin justificación.
"""
from __future__ import annotations

from backend.app.agents.agent_14_copiloto.prompts import (
    INDIVIDUAL_AUTONOMO_CONTEXT,
    SYSTEM_PROMPT,
)


def test_l9_individual_context_in_system_prompt():
    assert "Art. 11" in SYSTEM_PROMPT
    assert "ACUMULACION DE ROLES" in SYSTEM_PROMPT
    assert "autonomo" in SYSTEM_PROMPT.lower()


def test_l9_context_constant_has_key_guardrails():
    import re

    # normaliza espacios (el prompt usa continuaciones de línea con \)
    c = re.sub(r"\s+", " ", INDIVIDUAL_AUTONOMO_CONTEXT)
    # permitido PERO con justificación documentada (no simplificación sin más)
    assert "PERMITE" in c and "justificacion documentada" in c
    assert "NUNCA" in c
    # cita normativa + CCN-STIC 801
    assert "RD 311/2022 Art. 11" in c and "CCN-STIC 801" in c
    # los 3 niveles + ENAC externo no incluido en MEDIA/ALTA
    assert "TRES niveles" in c and "ENAC externo NO esta incluido" in c
