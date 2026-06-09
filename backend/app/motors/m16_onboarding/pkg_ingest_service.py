"""Ingesta pipelines: onboarding responses + discovery results -> PKG nodes."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.onboarding import ConnectorConfig, OnboardingResponse, OnboardingSession

from . import pkg_service as pkg
from .enums import SessionState


class PKGIngestError(ValueError):
    pass


# Capa de normalización drift #6: claves alias por concepto (mismo concepto, vocabulario
# divergente entre sectores). q-proveedor_identidad≡q-email_identidad; q-cloud_provider
# (singular) y q-cloud_uso ≡ q-cloud_providers. DPO acepta boolean True (drift de valor).
_IDP_NODE = {"node_type": "asset", "label_from": "answer", "properties": {"asset_subtype": "identity_provider"}}
_CLOUD_NODE = {"node_type": "asset", "label_from": "each_answer", "properties": {"asset_subtype": "cloud_provider"}}

QUESTION_NODE_MAP = {
    "q-sponsor_ejecutivo": {
        "node_type": "person",
        "label_from": "answer",
        "properties": {"role": "sponsor"},
    },
    "q-email_identidad": _IDP_NODE,
    "q-proveedor_identidad": _IDP_NODE,
    "q-cloud_providers": _CLOUD_NODE,
    "q-cloud_provider": _CLOUD_NODE,
    "q-cloud_uso": _CLOUD_NODE,
    "q-dpo_designado": {
        "node_type": "person",
        "label_from": "static",
        "static_label": "DPO",
        "condition": lambda answer: answer is True or answer in ("interno", "externo"),
        "properties": {"role": "dpo"},
    },
}


async def ingest_from_onboarding(
    session: AsyncSession,
    project_id: uuid.UUID,
    onboarding_session_id: uuid.UUID,
) -> dict:
    """Ingest onboarding responses into PKG."""
    r = await session.execute(
        select(OnboardingSession).where(OnboardingSession.id == onboarding_session_id)
    )
    onb = r.scalar_one_or_none()
    if onb is None:
        raise PKGIngestError(f"Onboarding session {onboarding_session_id} no existe")
    if onb.estado != SessionState.COMPLETED.value:
        raise PKGIngestError(f"Session no completada (estado: {onb.estado})")

    r = await session.execute(
        select(OnboardingResponse).where(OnboardingResponse.session_id == onboarding_session_id)
    )
    responses = {resp.question_id: resp.answer_value for resp in r.scalars().all()}

    nodes_created = 0

    for question_id, mapping in QUESTION_NODE_MAP.items():
        if question_id not in responses:
            continue

        answer_raw = responses[question_id]
        answer = answer_raw.get("value") if isinstance(answer_raw, dict) else answer_raw

        if answer is None:
            continue

        if "condition" in mapping and not mapping["condition"](answer):
            continue

        if mapping["label_from"] == "answer":
            labels = [str(answer)]
        elif mapping["label_from"] == "static":
            labels = [mapping["static_label"]]
        elif mapping["label_from"] == "each_answer":
            labels = answer if isinstance(answer, list) else [answer]
        else:
            labels = [str(answer)]

        for label in labels:
            if not label or not str(label).strip():
                continue
            await pkg.add_node(
                session, project_id,
                node_type=mapping["node_type"],
                label=str(label).strip(),
                external_id=f"onb:{onboarding_session_id}:{question_id}:{label}",
                properties={
                    **mapping.get("properties", {}),
                    "source": "onboarding",
                    "source_session_id": str(onboarding_session_id),
                    "source_question_id": question_id,
                },
            )
            nodes_created += 1

    await session.flush()

    return {
        "session_id": onboarding_session_id,
        "nodes_created": nodes_created,
        "edges_created": 0,
    }


async def ingest_from_discovery(
    session: AsyncSession,
    project_id: uuid.UUID,
    connector_config_id: uuid.UUID,
) -> dict:
    """Ingest discovery summary into PKG."""
    r = await session.execute(
        select(ConnectorConfig).where(ConnectorConfig.id == connector_config_id)
    )
    config = r.scalar_one_or_none()
    if config is None:
        raise PKGIngestError(f"ConnectorConfig {connector_config_id} no existe")

    summary = config.discovery_result_summary
    if not summary:
        raise PKGIngestError("No hay resultados de discovery")

    nodes_created = 0
    provider = config.provider

    if summary.get("total_assets", 0) > 0:
        await pkg.add_node(
            session, project_id,
            node_type="asset",
            label=f"{provider} discovery ({summary['total_assets']} assets)",
            external_id=f"discovery:{connector_config_id}:summary",
            properties={
                "source": "discovery", "provider": provider,
                "total_assets": summary["total_assets"],
                "asset_types": summary.get("asset_types", []),
            },
        )
        nodes_created += 1

    if summary.get("total_identities", 0) > 0:
        await pkg.add_node(
            session, project_id,
            node_type="identity",
            label=f"{provider} identities ({summary['total_identities']})",
            external_id=f"discovery:{connector_config_id}:identities",
            properties={
                "source": "discovery", "provider": provider,
                "total_identities": summary["total_identities"],
                "identity_types": summary.get("identity_types", []),
            },
        )
        nodes_created += 1

    await session.flush()

    return {
        "connector_config_id": connector_config_id,
        "provider": provider,
        "nodes_created": nodes_created,
    }
