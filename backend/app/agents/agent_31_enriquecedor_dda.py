"""Agent 31 - Enriquecedor DdA no_aplica (Sesion 9 Paso 2.7).

PRIMER AGENTE NUEVO desde cero de Sesion 9. Id 31 reservado en la
auditoria STEP B. Cierra TODO-M3-G1 y reasigna TODO-A14-G1.

Contexto: M3 DdA engine hoy genera justificacion de no_aplica con un
template estatico de 22 palabras genericas:

    "La medida {codigo} ({nombre}) no resulta de aplicacion al
    presente sistema, clasificado en categoria {system_category}..."

Ese texto pasa una auditoria ENS basica pero es pobre: no cita el
contexto real del cliente (cloud_providers, alcance, frameworks
heredados). A31 enriquece esas justificaciones con narrativa
contextual 60-200 palabras que cita datos REALES del input + CCN-STIC
aplicable. Sigue siendo prosa juridica seca sin invenciones.

Caso de uso: Marcos ejecuta M3 genera_dda -> 15-30 medidas no_aplica.
A31 se invoca una vez por medida. System prompt se cachea; primera
medida paga cache write (~20s), medidas 2..N pagan cache read (~2-3s)
+ output corto 500-800 tokens.

- Sonnet 4.6 temperature 0.2 max_tokens 1200 (output corto).
- Prompt caching activado (system ~3-4k tokens reutilizable por todo
  el proyecto).
- Validator anti-hallucination: no menciones empresas/productos/
  direcciones que NO esten en client_context o system_context_from_m22.
- Retry=1 con fallback al template estatico actual si LLM falla.
"""
from __future__ import annotations

import logging
import os
import pathlib
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.base import AgentBase
from backend.app.agents.prompts.agent_31_enriquecedor_dda import PROMPT

logger = logging.getLogger(__name__)


# Schema enums
_ENS_CATEGORIES = {"BASICA", "MEDIA", "ALTA"}
_SECTORS = {"sanidad", "aapp", "fintech", "otro"}
_BASE_REASONS = {
    "scope_exclusion",
    "cloud_only",
    "outsourced",
    "not_applicable_sector",
    "compensated_by_other",
}
_HOSTING_MODELS = {"cloud_saas", "cloud_iaas", "on_premise", "hybrid"}

_REQUIRED_KEYS: tuple[str, ...] = (
    "justificacion_enriquecida",
    "ccn_stic_referenciada",
    "elementos_contexto_usados",
    "confianza",
)

# CCN-STIC sugerida por base_reason (el LLM puede referenciar otra
# del catalogo CCN-STIC 800-899 pero al menos una CCN-STIC debe
# aparecer cuando aplique).
_CCN_STIC_BY_BASE_REASON: dict[str, list[str]] = {
    "scope_exclusion":          ["803"],
    "cloud_only":               ["803", "823"],
    "outsourced":               ["823"],
    "not_applicable_sector":    ["803"],
    "compensated_by_other":     ["804"],
}

# Sonnet 4.6 pricing.
_SONNET_46_USD_IN: float = 3.0
_SONNET_46_USD_OUT: float = 15.0
_SONNET_46_USD_CACHE_WRITE: float = 3.75
_SONNET_46_USD_CACHE_READ: float = 0.30
_USD_TO_EUR: float = 0.93

_MIN_WORDS: int = 60
_MAX_WORDS: int = 200


class Agent31EnrichmentError(Exception):
    """Error irrecuperable del Agente 31 tras agotar reintentos."""


class Agent31EnriquecedorDdA(AgentBase):
    """Enriquecedor justificaciones DdA no_aplica (Sonnet 4.6 JSON strict)."""

    AGENT_ID = 31
    AGENT_NAME = "Enriquecedor DdA no_aplica"
    MODEL = "sonnet-4.6"
    TEMPERATURE = 0.2
    MAX_TOKENS = 1200
    SPECIFIC_PROMPT = PROMPT
    # Caching criticamente importante: 15-30 invocaciones por proyecto
    # con el mismo system prompt. Primera paga write (~20s), resto lee.
    ENABLE_PROMPT_CACHING = True

    MAX_RETRIES_ON_INVALID_JSON = 1

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def enrich_no_aplica_justification(
        self,
        db: AsyncSession,
        *,
        measure_id: str,
        measure_name: str,
        measure_family: str,
        base_reason: str,
        client_context: dict[str, Any],
        system_context_from_m22: dict[str, Any],
        project_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Enriquece la justificacion de una medida DdA no_aplica."""
        self._validate_inputs(
            base_reason, client_context, system_context_from_m22,
        )
        user_msg = self._build_user_message(
            measure_id=measure_id,
            measure_name=measure_name,
            measure_family=measure_family,
            base_reason=base_reason,
            client_context=client_context,
            system_context_from_m22=system_context_from_m22,
        )
        context_payload = {
            "measure_id": measure_id,
            "measure_name": measure_name,
            "base_reason": base_reason,
            "client_context": client_context,
            "system_context_from_m22": system_context_from_m22,
        }

        retry_count = 0
        last_errors: list[str] = []
        last_response: dict[str, Any] = {}

        for attempt in range(self.MAX_RETRIES_ON_INVALID_JSON + 1):
            msg = (
                user_msg + self._retry_hint(last_errors)
                if attempt > 0
                else user_msg
            )
            response = await self.invoke(
                db,
                project_id=project_id,
                user_message=msg,
                context=context_payload,
                structured_output=True,
            )
            last_response = response
            parsed = response.get("parsed")
            if not isinstance(parsed, dict):
                last_errors = ["output no es JSON valido"]
                retry_count = attempt + 1
                self._dump_rejected(attempt + 1, response, reason="json_invalid")
                continue
            errors = self._validate_schema(
                parsed, client_context, system_context_from_m22,
            )
            if not errors:
                return self._build_result(
                    enrichment=parsed,
                    response=response,
                    schema_errors=[],
                    retry_count=attempt,
                    fallback_used=False,
                )
            last_errors = errors
            retry_count = attempt + 1
            logger.info(
                "A31 attempt %d: %d schema errors; retrying",
                attempt + 1, len(errors),
            )
            self._dump_rejected(
                attempt + 1, response, reason="schema_errors", errors=errors,
            )

        logger.warning(
            "A31 schema invalid after %d attempts, falling back to static template",
            self.MAX_RETRIES_ON_INVALID_JSON + 1,
        )
        fallback = self._template_fallback(
            measure_id=measure_id,
            measure_name=measure_name,
            base_reason=base_reason,
            client_context=client_context,
        )
        return self._build_result(
            enrichment=fallback,
            response=last_response,
            schema_errors=last_errors,
            retry_count=retry_count,
            fallback_used=True,
        )

    async def enrich_batch(
        self,
        db: AsyncSession,
        *,
        measures: list[dict[str, Any]],
        client_context: dict[str, Any],
        system_context_from_m22: dict[str, Any],
        project_id: uuid.UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Batch helper: invoca enrich_no_aplica_justification por medida.

        El system prompt se cachea desde la primera invocacion; las 2-N
        reutilizan el cache (coste dramaticamente menor).

        Args:
            measures: lista de {measure_id, measure_name, measure_family,
                base_reason}.

        Returns:
            Lista de resultados en el mismo orden que measures.
        """
        results: list[dict[str, Any]] = []
        for m in measures:
            result = await self.enrich_no_aplica_justification(
                db,
                measure_id=m["measure_id"],
                measure_name=m["measure_name"],
                measure_family=m.get(
                    "measure_family", m["measure_id"].rsplit(".", 1)[0]
                ),
                base_reason=m["base_reason"],
                client_context=client_context,
                system_context_from_m22=system_context_from_m22,
                project_id=project_id,
            )
            results.append(result)
        return results

    # ------------------------------------------------------------------
    # Input validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_inputs(
        base_reason: str,
        client_context: dict[str, Any],
        system_context_from_m22: dict[str, Any],
    ) -> None:
        if base_reason not in _BASE_REASONS:
            raise ValueError(f"base_reason invalido: {base_reason!r}")
        if client_context.get("sector") not in _SECTORS:
            raise ValueError(
                f"client_context.sector invalido: "
                f"{client_context.get('sector')!r}"
            )
        if client_context.get("ens_category") not in _ENS_CATEGORIES:
            raise ValueError(
                f"client_context.ens_category invalida: "
                f"{client_context.get('ens_category')!r}"
            )
        hm = system_context_from_m22.get("hosting_model")
        if hm is not None and hm not in _HOSTING_MODELS:
            raise ValueError(
                f"system_context_from_m22.hosting_model invalido: {hm!r}"
            )

    # ------------------------------------------------------------------
    # User message
    # ------------------------------------------------------------------

    @staticmethod
    def _build_user_message(
        *,
        measure_id: str,
        measure_name: str,
        measure_family: str,
        base_reason: str,
        client_context: dict[str, Any],
        system_context_from_m22: dict[str, Any],
    ) -> str:
        lines = [
            "Enriquece la justificacion de no aplicabilidad para esta medida.",
            "",
            "MEDIDA:",
            f"- measure_id: {measure_id}",
            f"- measure_name: {measure_name}",
            f"- measure_family: {measure_family}",
            f"- base_reason: {base_reason}",
            "",
            "CLIENT CONTEXT:",
            f"- company_name: {client_context.get('company_name', '')}",
            f"- sector: {client_context.get('sector')}",
            f"- ens_category: {client_context.get('ens_category')}",
            f"- is_aapp: {client_context.get('is_aapp', False)}",
            f"- alcance_texto: {client_context.get('alcance_texto', '')}",
            "",
            "SYSTEM CONTEXT (M22 discovery determinista, TU UNICA FUENTE DE HECHOS):",
            f"- hosting_model: {system_context_from_m22.get('hosting_model', 'desconocido')}",
            f"- cloud_providers: {system_context_from_m22.get('cloud_providers', [])}",
            f"- physical_offices: {system_context_from_m22.get('physical_offices', [])}",
            f"- frameworks_heredados: {system_context_from_m22.get('frameworks_heredados', [])}",
            f"- outsourced_services: {system_context_from_m22.get('outsourced_services', [])}",
            "",
            "Devuelve SOLO JSON con las 4 claves obligatorias. Sin markdown, sin backticks.",
        ]
        return "\n".join(lines)

    @staticmethod
    def _retry_hint(errors: list[str]) -> str:
        if not errors:
            return ""
        hint = "\n\nRECORDATORIO TRAS REINTENTO: detecte errores: "
        hint += "; ".join(errors[:5])
        hint += ". Corrige y responde solo con JSON valido."
        return hint

    # ------------------------------------------------------------------
    # Schema validation + anti-hallucination
    # ------------------------------------------------------------------

    def _validate_schema(
        self,
        parsed: dict[str, Any],
        client_context: dict[str, Any],
        system_context_from_m22: dict[str, Any],
    ) -> list[str]:
        errs: list[str] = []
        for k in _REQUIRED_KEYS:
            if k not in parsed:
                errs.append(f"falta clave '{k}'")
        if errs:
            return errs

        # justificacion_enriquecida
        just = parsed.get("justificacion_enriquecida", "")
        if not isinstance(just, str):
            errs.append("justificacion_enriquecida no string")
        else:
            word_count = len(just.split())
            if word_count < _MIN_WORDS:
                errs.append(
                    f"justificacion_enriquecida muy corta "
                    f"({word_count} palabras, min {_MIN_WORDS})"
                )
            elif word_count > _MAX_WORDS:
                errs.append(
                    f"justificacion_enriquecida muy larga "
                    f"({word_count} palabras, max {_MAX_WORDS})"
                )

        ccn = parsed.get("ccn_stic_referenciada")
        if ccn is not None and not isinstance(ccn, str):
            errs.append("ccn_stic_referenciada no es string ni null")

        elementos = parsed.get("elementos_contexto_usados")
        if not isinstance(elementos, list):
            errs.append("elementos_contexto_usados no lista")
        elif len(elementos) == 0:
            errs.append("elementos_contexto_usados vacio (debe citar al menos 1)")

        conf = parsed.get("confianza")
        try:
            c = float(conf)
            if not (0.0 <= c <= 1.0):
                errs.append(f"confianza fuera [0,1]: {c}")
        except (TypeError, ValueError):
            errs.append(f"confianza no numerica: {conf!r}")

        # Anti-hallucination: no mencionar empresas/productos/direcciones
        # ausentes del input.
        if isinstance(just, str):
            errs.extend(self._detect_hallucinated_entities(
                just, client_context, system_context_from_m22,
            ))

        return errs

    @staticmethod
    def _detect_hallucinated_entities(
        text: str,
        client_context: dict[str, Any],
        system_context_from_m22: dict[str, Any],
    ) -> list[str]:
        """Detecta empresas/productos inventados.

        Whitelist:
        - Cualquier string presente en cloud_providers, frameworks_heredados,
          outsourced_services, physical_offices o client_context.
        - Proveedores genericos muy comunes SIEMPRE permitidos (pais/
          estandar): UE, EEE, RGPD, ENS, AEPD, CCN, ENAC, ISO, etc.

        Detecta:
        - Menciones tipicas de providers cloud / software no incluidos en
          el whitelist dinamico: Google, Microsoft, Azure, AWS, Oracle,
          Salesforce, GCP, Dropbox, OneDrive, Office365, SharePoint, etc.
        """
        errs: list[str] = []

        # Construir whitelist a partir del input
        wl_items: list[str] = []
        for v in system_context_from_m22.get("cloud_providers", []) or []:
            wl_items.append(str(v))
        for v in system_context_from_m22.get("frameworks_heredados", []) or []:
            wl_items.append(str(v))
        for v in system_context_from_m22.get("outsourced_services", []) or []:
            wl_items.append(str(v))
        for o in system_context_from_m22.get("physical_offices", []) or []:
            if isinstance(o, dict):
                wl_items.append(str(o.get("address", "")))
        # Nombre cliente + alcance texto
        wl_items.append(str(client_context.get("company_name", "")))
        wl_items.append(str(client_context.get("alcance_texto", "")))

        wl_text = " ".join(wl_items).lower()

        # Listado de entidades sospechosas comunes. Si aparecen en el
        # output pero NO en el whitelist, error.
        SUSPICIOUS_ENTITIES = [
            "aws", "azure", "gcp", "google cloud", "google workspace",
            "oracle cloud", "salesforce", "dropbox", "onedrive",
            "sharepoint", "office 365", "office365", "microsoft 365",
            "slack", "atlassian", "workday", "okta", "sap",
            "mailchimp", "hubspot", "zendesk", "servicenow",
            "vmware", "nutanix", "netsuite",
        ]
        text_low = text.lower()
        for ent in SUSPICIOUS_ENTITIES:
            if ent in text_low and ent not in wl_text:
                errs.append(
                    f"hallucinated_entity: '{ent}' aparece en el texto "
                    f"pero no esta en client_context ni system_context_from_m22"
                )
                if len(errs) >= 3:
                    break
        return errs

    # ------------------------------------------------------------------
    # Fallback template
    # ------------------------------------------------------------------

    @staticmethod
    def _template_fallback(
        *,
        measure_id: str,
        measure_name: str,
        base_reason: str,
        client_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Fallback al template M3 actual (determinista) con metadata extra."""
        categoria = client_context.get("ens_category", "MEDIA")
        # Replica textual del template estatico M3 service.
        text = (
            f"La medida {measure_id} ({measure_name}) no resulta de "
            f"aplicacion al presente sistema, clasificado en categoria "
            f"{categoria} conforme al Anexo I del RD 311/2022. El Anexo II "
            f"establece los criterios de aplicabilidad por categoria. La "
            f"circunstancia '{base_reason}' motiva su exclusion del alcance "
            f"del SGSI conforme al criterio de delimitacion establecido en "
            f"la CCN-STIC 803. No se identifican circunstancias que "
            f"justifiquen su aplicacion voluntaria en este ambito."
        )
        # Asegurar minimo 60 palabras
        words = text.split()
        if len(words) < _MIN_WORDS:
            text += (
                " El responsable de seguridad confirmara esta no aplicabilidad "
                "en la revision periodica de la Declaracion de Aplicabilidad "
                "correspondiente al ciclo de certificacion vigente."
            )
        return {
            "justificacion_enriquecida": text,
            "ccn_stic_referenciada": "CCN-STIC 803",
            "elementos_contexto_usados": ["fallback_template"],
            "confianza": 0.3,
        }

    # ------------------------------------------------------------------
    # Debug + result shape
    # ------------------------------------------------------------------

    def _dump_rejected(
        self,
        attempt: int,
        response: dict[str, Any],
        *,
        reason: str,
        errors: list[str] | None = None,
    ) -> None:
        if not os.environ.get("FULKRO_AGENT_DEBUG_DUMPS"):
            return
        try:
            import uuid as _uuid
            out_dir = pathlib.Path("/tmp")
            short_id = _uuid.uuid4().hex[:8]
            path = out_dir / f"a31_rejected_attempt_{attempt}_{short_id}.md"
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# A31 REJECTED - attempt {attempt}\n\n")
                f.write(f"- reason: {reason}\n")
                if errors:
                    f.write(f"- errors ({len(errors)}):\n")
                    for e in errors[:20]:
                        f.write(f"    - {e}\n")
                f.write("\n## RAW\n```\n")
                f.write(response.get("response", ""))
                f.write("\n```\n")
            logger.warning("A31 rejected draft saved to %s", path)
        except Exception as exc:
            logger.debug("A31 dump failed: %s", exc)

    def _build_result(
        self,
        *,
        enrichment: dict[str, Any],
        response: dict[str, Any],
        schema_errors: list[str],
        retry_count: int,
        fallback_used: bool,
    ) -> dict[str, Any]:
        tokens_in = int(response.get("tokens_input", 0) or 0)
        tokens_out = int(response.get("tokens_output", 0) or 0)
        cache_creation = int(response.get("cache_creation_input_tokens", 0) or 0)
        cache_read = int(response.get("cache_read_input_tokens", 0) or 0)
        cost_eur = (
            (tokens_in / 1_000_000) * _SONNET_46_USD_IN
            + (cache_creation / 1_000_000) * _SONNET_46_USD_CACHE_WRITE
            + (cache_read / 1_000_000) * _SONNET_46_USD_CACHE_READ
            + (tokens_out / 1_000_000) * _SONNET_46_USD_OUT
        ) * _USD_TO_EUR
        return {
            "enrichment": enrichment,
            "schema_valid": not schema_errors,
            "schema_errors": schema_errors,
            "retry_count": retry_count,
            "tokens_input": tokens_in,
            "tokens_output": tokens_out,
            "cache_creation_input_tokens": cache_creation,
            "cache_read_input_tokens": cache_read,
            "cost_eur_estimated": round(cost_eur, 5),
            "latency_ms": int(response.get("latency_ms", 0) or 0),
            "model": response.get("model", self.MODEL),
            "fallback_used": fallback_used,
        }
