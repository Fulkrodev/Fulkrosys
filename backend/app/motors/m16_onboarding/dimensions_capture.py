"""Motor 16 · Captura distribuida de 19 dimensiones desde onboarding (sub-atom 1.C.D.A.0.3 v3.8).

Bridge entre m16_onboarding (templates adaptive JSON per sector/role) y
M01 dimensions service (canónico · projects table 19 dims).

Approach pragmático (OPS-029 caso 9 + OPS-045 caso 4 sostenidos):
  - NO modificamos 70 templates existing (10 sectores × 7 roles)
  - Definimos 10 question_id canónicas + mapping a project dimensions
  - Cualquier template que use estos question_id (o admin añade via override
    futura) automatically alimenta la canónica projects.* via aplicación
    post-submit
  - Aplicar via OnboardingClientService.submit_session → apply_dimensions_from_responses

Las 10 dimensiones técnicas/legales canónicas:
  q-madurez-ens-actual     → projects.madurez_ens_actual
  q-equipo-ti-tamano       → projects.equipo_ti_tamano
  q-dpo-designado          → projects.dpo_designado
  q-aplica-nis2            → projects.aplica_nis2
  q-aplica-dora            → projects.aplica_dora
  q-aplica-ai-act          → projects.aplica_ai_act
  q-procesa-datos-sensibles → projects.procesa_datos_sensibles_rgpd9
  q-arquitectura-sistemas  → projects.arquitectura_sistemas
  q-multi-tenancy          → projects.multi_tenancy
  q-compromiso-interno     → projects.compromiso_interno
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m01_categorization.dimensions_service import (
    DimensionsService,
    ProjectDimensionsServiceError,
)

logger = logging.getLogger(__name__)


# Mapping canónico question_id → project dimension column.
# Las question_id siguen pattern m16 (q-<snake_case_with_hyphens>).
CANONICAL_DIM_QUESTION_MAPPING: dict[str, str] = {
    "q-madurez-ens-actual": "madurez_ens_actual",
    "q-equipo-ti-tamano": "equipo_ti_tamano",
    "q-dpo-designado": "dpo_designado",
    "q-aplica-nis2": "aplica_nis2",
    "q-aplica-dora": "aplica_dora",
    "q-aplica-ai-act": "aplica_ai_act",
    "q-procesa-datos-sensibles": "procesa_datos_sensibles_rgpd9",
    "q-arquitectura-sistemas": "arquitectura_sistemas",
    "q-multi-tenancy": "multi_tenancy",
    "q-compromiso-interno": "compromiso_interno",
}


# Las 10 preguntas canónicas con tooltip ENS contextual (R30 sostenido).
# Templates pueden importar estos diccionarios para incluir las questions
# en su flow sin duplicar texto · evita drift entre templates.
CANONICAL_DIM_QUESTIONS_DEFINITIONS: dict[str, dict[str, Any]] = {
    "q-madurez-ens-actual": {
        "type": "single_select",
        "section": "madurez",
        "label": "¿Cuál es vuestra madurez ENS actual?",
        "tooltip": (
            "Nivel de madurez ENS actual. L0 = no implementado nada · "
            "L5 = ENS optimizado con mejora continua. Auditor evalúa salto desde "
            "L actual hasta target requerido por categoría."
        ),
        "options": [
            {"value": "L0", "label": "L0 · sin ENS · cero implementado"},
            {"value": "L1", "label": "L1 · inicial ad-hoc · procesos informales"},
            {"value": "L2", "label": "L2 · repetible · procesos básicos documentados"},
            {"value": "L3", "label": "L3 · definido · políticas + procedimientos"},
            {"value": "L4", "label": "L4 · gestionado · métricas + indicadores"},
            {"value": "L5", "label": "L5 · optimizado · mejora continua"},
        ],
    },
    "q-equipo-ti-tamano": {
        "type": "single_select",
        "section": "tecnicas",
        "label": "Tamaño de vuestro equipo TI propio",
        "tooltip": (
            "Tamaño del equipo TI propio del cliente. Si sin equipo · Marcos "
            "asume responsable TI virtual con riesgo mayor. Afecta velocidad "
            "implementación + responsable RACI."
        ),
        "options": [
            {"value": "sin_equipo", "label": "Sin equipo TI propio (externalizado)"},
            {"value": "1_3", "label": "Pequeño (1-3 personas)"},
            {"value": "4_10", "label": "Mediano (4-10 personas)"},
            {"value": "11_30", "label": "Grande (11-30 personas)"},
            {"value": "gt30", "label": "Enterprise (>30 personas)"},
        ],
    },
    "q-dpo-designado": {
        "type": "single_select",
        "section": "legales",
        "label": "¿Tenéis DPO designado?",
        "tooltip": (
            "Data Protection Officer (RGPD art.37-39). Obligatorio si procesas "
            "datos especiales a gran escala · monitorización sistemática · "
            "admin pública. Puede ser interno o externo (consultor)."
        ),
        "options": [
            {"value": "interno", "label": "DPO interno designado"},
            {"value": "externo", "label": "DPO externo contratado"},
            {"value": "no_designado", "label": "No designado todavía"},
        ],
    },
    "q-aplica-nis2": {
        "type": "single_select",
        "section": "legales",
        "label": "¿Aplica NIS2 a vuestra organización?",
        "tooltip": (
            "Directiva UE 2022/2555 sobre ciberseguridad. Aplica si la empresa "
            "opera en sectores críticos (energía · sanidad · transporte · banca · "
            "admin pública · digital infrastructure)."
        ),
        "options": [
            {"value": "no", "label": "No aplica"},
            {"value": "esencial", "label": "Sí · entidad esencial"},
            {"value": "importante", "label": "Sí · entidad importante"},
        ],
    },
    "q-aplica-dora": {
        "type": "single_select",
        "section": "legales",
        "label": "¿Aplica DORA a vuestra organización?",
        "tooltip": (
            "Reglamento UE 2022/2554 sobre resiliencia operativa digital del "
            "sector financiero. Aplica si tu empresa procesa servicios "
            "financieros o es proveedor ICT crítico de entidades financieras."
        ),
        "options": [
            {"value": "no", "label": "No aplica"},
            {"value": "entidad_financiera", "label": "Sí · entidad financiera"},
            {"value": "proveedor_ict_critico", "label": "Sí · proveedor ICT crítico"},
        ],
    },
    "q-aplica-ai-act": {
        "type": "single_select",
        "section": "legales",
        "label": "¿Aplica AI Act a vuestros sistemas?",
        "tooltip": (
            "Reglamento UE 2024/1689 sobre IA. Alto riesgo = sistemas IA en "
            "Anexo III. GPAI = modelos propósito general. Limitado = chatbots "
            "públicos requieren transparencia."
        ),
        "options": [
            {"value": "no", "label": "No aplica · no usamos IA"},
            {"value": "alto_riesgo", "label": "Sí · alto riesgo (Anexo III)"},
            {"value": "gpai", "label": "Sí · GPAI propósito general"},
            {"value": "limitado", "label": "Sí · riesgo limitado (transparencia)"},
        ],
    },
    "q-procesa-datos-sensibles": {
        "type": "boolean",
        "section": "legales",
        "label": "¿Procesáis datos sensibles RGPD art.9?",
        "tooltip": (
            "Datos especiales · biométricos · salud · político · religioso · "
            "sexual orientation · racial · sindical · genético. Si procesas "
            "alguno · DPIA obligatorio + DPO recomendado."
        ),
    },
    "q-arquitectura-sistemas": {
        "type": "single_select",
        "section": "tecnicas",
        "label": "¿Cuál es vuestra arquitectura predominante?",
        "tooltip": (
            "Modelo arquitectónico predominante. Afecta scope pentest · "
            "controles infra · responsabilidades proveedor cloud."
        ),
        "options": [
            {"value": "on_premise", "label": "On-premise (servidores propios)"},
            {"value": "hibrido", "label": "Híbrido (on-premise + cloud)"},
            {"value": "cloud_native", "label": "Cloud-native (SaaS · serverless)"},
            {"value": "multi_cloud", "label": "Multi-cloud (2+ proveedores)"},
            {"value": "hyperscaler", "label": "Hyperscaler exclusivo"},
        ],
    },
    "q-multi-tenancy": {
        "type": "single_select",
        "section": "tecnicas",
        "label": "Modelo multi-tenancy",
        "tooltip": (
            "Si una instancia atiende a múltiples clientes (multi-tenant) "
            "requiere controles adicionales de isolación · separación datos · "
            "etc. (ENS Anexo II mp.com.4 + mp.info.*)."
        ),
        "options": [
            {"value": "single", "label": "Single-tenant (un cliente/instancia)"},
            {"value": "multi_tenant", "label": "Multi-tenant compartido"},
            {"value": "marketplace", "label": "Marketplace · agregador"},
        ],
    },
    "q-compromiso-interno": {
        "type": "single_select",
        "section": "operacional",
        "label": "Nivel de compromiso interno con el proyecto ENS",
        "tooltip": (
            "Cuán implicado/comprometido está el cliente con el proceso. "
            "Reluctante = cumple por obligación legal · proactivo = quiere "
            "mejorar genuinamente."
        ),
        "options": [
            {"value": "proactivo", "label": "Proactivo · lideramos el proceso"},
            {"value": "reactivo", "label": "Reactivo · respondemos cuando se pide"},
            {"value": "reluctante", "label": "Reluctante · cumplimos por obligación"},
        ],
    },
}


def _normalize_qid(q_id: str) -> str:
    """Unifica separadores tras el prefijo ``q-``.

    Drift histórico: la question canónica de DPO es ``q-dpo-designado`` (guion)
    pero las 10 plantillas ``*-legal_dpo-*`` la escriben ``q-dpo_designado``
    (underscore) → el lookup exacto fallaba y la dimensión ``dpo_designado``
    nunca se capturaba. Normalizando underscores→guiones SOLO para el match
    canónico evitamos eso sin reescribir las plantillas (OPS-029 sostenido) y
    sin riesgo de colisión (sólo afecta a las 10 question_ids canónicas).
    """
    if q_id.startswith("q-"):
        return "q-" + q_id[2:].replace("_", "-")
    return q_id


def extract_dimension_updates_from_responses(
    responses: dict[str, Any],
) -> dict[str, Any]:
    """Extrae respuestas que matchean CANONICAL_DIM_QUESTION_MAPPING.

    Tolera el drift guion/underscore de las question_ids (ver ``_normalize_qid``).

    Args:
        responses: dict question_id → answer (post-submit onboarding)

    Returns:
        dict project_column → value (subset · sólo question_ids canónicas)
    """
    # Índice normalizado: separadores unificados → primer valor visto.
    norm_responses: dict[str, Any] = {}
    for key, val in responses.items():
        norm_responses.setdefault(_normalize_qid(key), val)

    updates: dict[str, Any] = {}
    for q_id, project_col in CANONICAL_DIM_QUESTION_MAPPING.items():
        # Match exacto primero (plantillas correctas), luego normalizado.
        value = responses.get(q_id, norm_responses.get(_normalize_qid(q_id)))
        if value is None:
            continue
        updates[project_col] = value
    return updates


async def apply_dimensions_from_responses(
    db: AsyncSession,
    project_id: uuid.UUID,
    responses: dict[str, Any],
    updated_by: uuid.UUID,
) -> dict[str, Any] | None:
    """Aplica dimensiones desde respuestas onboarding al project canónico.

    Returns dict updates aplicados (o None si no había nada que aplicar).
    NO levanta excepción si project no existe · se logea warning (OPS-040
    pattern non-invasive · NO rompe motor origen m16).
    """
    updates = extract_dimension_updates_from_responses(responses)
    if not updates:
        return None

    try:
        service = DimensionsService(db)
        await service.patch_dimensions_partial(
            project_id=project_id,
            partial_dict=updates,
            updated_by=updated_by,
        )
        logger.info(
            "m16 → projects dims applied · project=%s · keys=%s",
            project_id,
            list(updates.keys()),
        )
        return updates
    except ProjectDimensionsServiceError as exc:
        logger.warning(
            "m16 → projects dims skip · project=%s · reason=%s",
            project_id,
            exc,
        )
        return None
    except Exception as exc:  # pragma: no cover · safety net OPS-040
        logger.warning(
            "m16 → projects dims FAILED · project=%s · err=%s",
            project_id,
            exc,
        )
        return None
