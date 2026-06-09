"""Motor 28 — Materiality engine (addendum §8.4).

Arbol de decision determinista de 10 preguntas binarias. El engine NO opina
ni inventa; solo aplica reglas fijas sobre las respuestas.
"""
from __future__ import annotations

from typing import Literal


IMPACT_QUESTIONS: tuple[str, ...] = (
    "affects_evidence",
    "affects_documentation",
    "affects_controls",
    "affects_overlay",
    "affects_roles",
    "affects_risk_analysis",
    "affects_dda",
    "affects_category",
    "affects_renewal",
    "requires_extraordinary",
)

MaterialityLevel = Literal["MINOR", "RELEVANT", "MATERIAL"]


_MATERIAL_TRIGGERS = {
    "affects_risk_analysis",
    "affects_dda",
    "affects_category",
    "affects_renewal",
    "requires_extraordinary",
}
_RELEVANT_TRIGGERS = {
    "affects_evidence", "affects_documentation",
    "affects_controls", "affects_overlay", "affects_roles",
}


def assess(answers: dict[str, bool]) -> dict:
    """Run the deterministic decision tree on the 10 binary answers.

    Returns the canonical assessment dict with impact_vector, materiality
    score/level, required documents, workflows, signoffs, customer actions
    and deadline policy.
    """
    missing = [q for q in IMPACT_QUESTIONS if q not in answers]
    if missing:
        raise ValueError(f"Missing answers for: {missing}")

    vector = {q: bool(answers[q]) for q in IMPACT_QUESTIONS}
    triggered = {q for q, v in vector.items() if v}

    if triggered & _MATERIAL_TRIGGERS:
        level: MaterialityLevel = "MATERIAL"
        score = 70 + 5 * len(triggered & _MATERIAL_TRIGGERS)
    elif triggered & _RELEVANT_TRIGGERS:
        level = "RELEVANT"
        score = 30 + 5 * len(triggered & _RELEVANT_TRIGGERS)
    else:
        level = "MINOR"
        score = 5 * len(triggered)

    score = min(100, score)

    documents = ["E-046"]
    workflows: list[str] = []
    signoffs = ["rseg"]
    customer_actions: list[str] = []

    if level == "MATERIAL":
        documents.append("E-615")
        signoffs.extend(["sponsor", "comite"])
        deadline = "1d"
        customer_actions.append("Convocar comite extraordinario en 24h")
    elif level == "RELEVANT":
        documents.append("E-047")
        signoffs.append("sponsor")
        deadline = "5d"
        customer_actions.append("Aprobar cambio en proxima reunion")
    else:
        deadline = "10d"

    if vector["affects_category"]:
        workflows.append("recategorization")
        documents.append("E-048")
    if vector["requires_extraordinary"]:
        workflows.append("extraordinary_audit")
    if vector["affects_renewal"]:
        workflows.append("renewal_revalidation")
    if vector["affects_dda"]:
        workflows.append("dda_update")
    if vector["affects_risk_analysis"]:
        workflows.append("ar_rebaseline")
    if vector["affects_overlay"]:
        workflows.append("overlay_revalidation")
    if vector["affects_roles"]:
        workflows.append("role_topology_review")

    return {
        "impact_vector": {
            "evidence": vector["affects_evidence"],
            "document": vector["affects_documentation"],
            "control": vector["affects_controls"],
            "overlay": vector["affects_overlay"],
            "roles": vector["affects_roles"],
            "risk_analysis": vector["affects_risk_analysis"],
            "dda": vector["affects_dda"],
            "category": vector["affects_category"],
            "renewal": vector["affects_renewal"],
            "extraordinary": vector["requires_extraordinary"],
        },
        "materiality_score": score,
        "materiality_level": level,
        "required_documents": sorted(set(documents)),
        "required_workflows": sorted(set(workflows)),
        "required_signoffs": sorted(set(signoffs)),
        "customer_actions": customer_actions,
        "deadline_policy": deadline,
    }


def classify_change(materiality_level: MaterialityLevel) -> str:
    """Map materiality_level to change-class label."""
    return {"MINOR": "MINOR", "RELEVANT": "RELEVANT", "MATERIAL": "MATERIAL"}[materiality_level]
