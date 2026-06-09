"""Agent 12 - Coach Cliente EVALUADOR (Sesion 9 Paso 2.8).

SCOPE EVALUADOR (no generador): A12 NO genera preguntas de coaching.
M9 coaching.COACHING_QUESTIONS (determinista, ~80 preguntas auditor
por rol) sigue siendo la fuente unica. A12 evalua las respuestas del
cliente a esas preguntas.

Caso de uso: Marcos envia 15 preguntas coaching a CISO cliente via
magic link. CISO responde 15 textos libres. A12 evalua cada uno con
rubrica L0-L5 + feedback accionable para Marcos.

Output JSON strict con:
- score_global 0-100 + madurez_respuesta L0-L5.
- dimension_scores (completitud, exactitud, evidencia_referenciada).
- gaps_detectados (max 4) categorizados.
- respuesta_ideal_template (150-400 palabras) modelando CISO senior.
- next_actions_cliente (max 3) accionables.
- feedback_marcos (nota interna).

- Sonnet 4.6 temperature 0.2 max_tokens 2500.
- Prompt caching activado (system prompt ~3-4k reusable por todas
  las respuestas del proyecto, 15+ invocaciones tipicas).
- Validator: schema strict + coherencia madurez vs scores (si los
  3 scores <30 no puede ser L4-L5) + anti-hallucination
  (no inventar sistemas/evidencias ausentes de la respuesta cliente).
- Retry=1 con fallback de scoring keyword basico.
"""
from __future__ import annotations

import logging
import os
import pathlib
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.base import AgentBase
from backend.app.agents.prompts.agent_12_coach_cliente import PROMPT

logger = logging.getLogger(__name__)


# Schema enums
_MATURITY_LEVELS = {"L0", "L1", "L2", "L3", "L4", "L5"}
_SECTORS = {"sanidad", "aapp", "fintech", "otro"}
_ENS_CATEGORIES = {"BASICA", "MEDIA", "ALTA"}
_ROLES = {"CISO", "RSEG", "CTO", "direccion", "tech"}
_GAP_TIPOS = {
    "falta_evidencia",
    "respuesta_vaga",
    "dato_inconsistente",
    "alcance_no_claro",
    "cita_normativa_incorrecta",
}
_URGENCIAS = {"inmediata", "1_semana", "antes_audit"}

_REQUIRED_KEYS: tuple[str, ...] = (
    "score_global",
    "madurez_respuesta",
    "dimension_scores",
    "gaps_detectados",
    "respuesta_ideal_template",
    "next_actions_cliente",
    "feedback_marcos",
)

_DIMENSION_KEYS: tuple[str, ...] = (
    "completitud",
    "exactitud",
    "evidencia_referenciada",
)

# Catalogo de entidades/productos sospechosas que el LLM NO debe
# inventar en respuesta_ideal_template si no aparecen en la respuesta
# del cliente.
_SUSPICIOUS_ENTITIES: tuple[str, ...] = (
    "splunk", "qradar", "sentinel", "wazuh", "graylog",
    "veeam", "commvault", "acronis", "rubrik",
    "cisco", "fortinet", "palo alto", "checkpoint",
    "crowdstrike", "sentinelone", "carbon black",
    "azure ad", "okta", "cyberark", "hashicorp vault",
    "duo security", "rsa", "yubikey",
    "proofpoint", "mimecast", "barracuda",
    "tenable", "qualys", "rapid7",
)

# Sonnet 4.6 pricing
_SONNET_46_USD_IN: float = 3.0
_SONNET_46_USD_OUT: float = 15.0
_SONNET_46_USD_CACHE_WRITE: float = 3.75
_SONNET_46_USD_CACHE_READ: float = 0.30
_USD_TO_EUR: float = 0.93


class Agent12CoachError(Exception):
    """Error irrecuperable del Agente 12 tras agotar reintentos."""


class Agent12CoachClienteEvaluador(AgentBase):
    """Coach cliente evaluador de respuestas a M9 (Sonnet 4.6 JSON strict)."""

    AGENT_ID = 12
    AGENT_NAME = "Coach Cliente Evaluador"
    MODEL = "sonnet-4.6"
    TEMPERATURE = 0.2
    MAX_TOKENS = 2500
    SPECIFIC_PROMPT = PROMPT
    ENABLE_PROMPT_CACHING = True

    MAX_RETRIES_ON_INVALID_JSON = 1

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def evaluate_client_response(
        self,
        db: AsyncSession,
        *,
        pregunta_coaching: dict[str, Any],
        respuesta_cliente: dict[str, Any],
        client_context: dict[str, Any],
        project_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Evalua una respuesta de cliente a pregunta coaching M9."""
        self._validate_inputs(pregunta_coaching, respuesta_cliente, client_context)
        user_msg = self._build_user_message(
            pregunta_coaching, respuesta_cliente, client_context,
        )
        context_payload = {
            "pregunta_coaching": pregunta_coaching,
            "respuesta_cliente": respuesta_cliente,
            "client_context": client_context,
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
            errors = self._validate_schema(parsed, respuesta_cliente)
            if not errors:
                return self._build_result(
                    evaluation=parsed,
                    response=response,
                    schema_errors=[],
                    retry_count=attempt,
                    fallback_used=False,
                )
            last_errors = errors
            retry_count = attempt + 1
            logger.info(
                "A12 attempt %d: %d schema errors; retrying",
                attempt + 1, len(errors),
            )
            self._dump_rejected(
                attempt + 1, response, reason="schema_errors", errors=errors,
            )

        logger.warning(
            "A12 schema invalid after %d attempts, falling back to keyword scoring",
            self.MAX_RETRIES_ON_INVALID_JSON + 1,
        )
        fallback = self._keyword_fallback(
            pregunta_coaching, respuesta_cliente, client_context,
        )
        return self._build_result(
            evaluation=fallback,
            response=last_response,
            schema_errors=last_errors,
            retry_count=retry_count,
            fallback_used=True,
        )

    async def evaluate_batch(
        self,
        db: AsyncSession,
        *,
        items: list[dict[str, Any]],
        client_context: dict[str, Any],
        project_id: uuid.UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Batch helper: evalua lista de (pregunta, respuesta).

        Cada item en `items` debe tener `pregunta_coaching` +
        `respuesta_cliente`. Caching reutilizado desde la primera.
        """
        results: list[dict[str, Any]] = []
        for item in items:
            r = await self.evaluate_client_response(
                db,
                pregunta_coaching=item["pregunta_coaching"],
                respuesta_cliente=item["respuesta_cliente"],
                client_context=client_context,
                project_id=project_id,
            )
            results.append(r)
        return results

    # Alias retrocompat con scaffold previo
    async def evaluate_response(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        question: str,
        response: str,
    ) -> dict[str, Any]:
        """Firma legacy: question + response planos. Se recomienda usar
        `evaluate_client_response` con dicts estructurados.
        """
        return await self.evaluate_client_response(
            db,
            pregunta_coaching={
                "id": "LEGACY",
                "role": "tech",
                "texto": question,
                "criterio_L5_ideal": "",
            },
            respuesta_cliente={"texto": response, "rol_cliente": "staff"},
            client_context={
                "company_name": "",
                "sector": "otro",
                "ens_category": "MEDIA",
            },
            project_id=project_id,
        )

    # ------------------------------------------------------------------
    # Input validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_inputs(
        pregunta: dict[str, Any],
        respuesta: dict[str, Any],
        ctx: dict[str, Any],
    ) -> None:
        for k in ("id", "role", "texto"):
            if k not in pregunta:
                raise ValueError(f"pregunta_coaching falta '{k}'")
        if not isinstance(respuesta.get("texto"), str):
            raise ValueError("respuesta_cliente.texto debe ser string")
        if ctx.get("sector") not in _SECTORS:
            raise ValueError(
                f"client_context.sector invalido: {ctx.get('sector')!r}"
            )
        if ctx.get("ens_category") not in _ENS_CATEGORIES:
            raise ValueError(
                f"client_context.ens_category invalida: {ctx.get('ens_category')!r}"
            )

    # ------------------------------------------------------------------
    # User message
    # ------------------------------------------------------------------

    @staticmethod
    def _build_user_message(
        pregunta: dict[str, Any],
        respuesta: dict[str, Any],
        ctx: dict[str, Any],
    ) -> str:
        lines = [
            "Evalua la respuesta del cliente a esta pregunta coaching ENAC.",
            "",
            "PREGUNTA COACHING (de M9 determinista):",
            f"- id: {pregunta.get('id', '')}",
            f"- role: {pregunta.get('role', '')}",
            f"- texto: {pregunta.get('texto', '')}",
            f"- criterio_L5_ideal: {pregunta.get('criterio_L5_ideal', '(no aportado)')}",
            "",
            "RESPUESTA DEL CLIENTE:",
            f"- rol_cliente: {respuesta.get('rol_cliente', 'staff')}",
            "- texto:",
            respuesta.get("texto", ""),
            "",
            "CLIENT CONTEXT:",
            f"- company_name: {ctx.get('company_name', '')}",
            f"- sector: {ctx.get('sector')}",
            f"- ens_category: {ctx.get('ens_category')}",
            "",
            "Devuelve SOLO JSON con las 7 claves obligatorias del schema. "
            "Sin markdown exterior, sin backticks.",
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
    # Schema validation + coherencia madurez + anti-hallucination
    # ------------------------------------------------------------------

    def _validate_schema(
        self,
        parsed: dict[str, Any],
        respuesta_cliente: dict[str, Any],
    ) -> list[str]:
        errs: list[str] = []
        for k in _REQUIRED_KEYS:
            if k not in parsed:
                errs.append(f"falta clave '{k}'")
        if errs:
            return errs

        # score_global
        score = parsed.get("score_global")
        try:
            s = int(score)
            if not (0 <= s <= 100):
                errs.append(f"score_global fuera [0,100]: {s}")
        except (TypeError, ValueError):
            errs.append(f"score_global no entero: {score!r}")

        mad = parsed.get("madurez_respuesta")
        if mad not in _MATURITY_LEVELS:
            errs.append(f"madurez_respuesta invalida: {mad!r}")

        # dimension_scores
        dims = parsed.get("dimension_scores")
        if not isinstance(dims, dict):
            errs.append("dimension_scores no dict")
        else:
            for dk in _DIMENSION_KEYS:
                v = dims.get(dk)
                try:
                    iv = int(v)
                    if not (0 <= iv <= 100):
                        errs.append(
                            f"dimension_scores.{dk} fuera [0,100]: {iv}"
                        )
                except (TypeError, ValueError):
                    errs.append(f"dimension_scores.{dk} no entero: {v!r}")

        # Coherencia madurez vs dimension_scores
        if isinstance(dims, dict) and mad in _MATURITY_LEVELS:
            errs.extend(self._check_madurez_coherence(mad, dims))

        # gaps_detectados
        gaps = parsed.get("gaps_detectados")
        if not isinstance(gaps, list):
            errs.append("gaps_detectados no lista")
        elif len(gaps) > 4:
            errs.append(f"gaps_detectados > 4 elementos ({len(gaps)})")
        else:
            for i, g in enumerate(gaps):
                if not isinstance(g, dict):
                    errs.append(f"gaps_detectados[{i}] no dict")
                    continue
                if g.get("tipo") not in _GAP_TIPOS:
                    errs.append(
                        f"gaps_detectados[{i}].tipo invalido: {g.get('tipo')!r}"
                    )
                desc = g.get("descripcion", "")
                if not isinstance(desc, str) or len(desc) > 250:
                    errs.append(
                        f"gaps_detectados[{i}].descripcion invalida o >250 chars"
                    )

        # respuesta_ideal_template
        tmpl = parsed.get("respuesta_ideal_template", "")
        if not isinstance(tmpl, str):
            errs.append("respuesta_ideal_template no string")
        else:
            words = len(tmpl.split())
            if words < 100:
                errs.append(
                    f"respuesta_ideal_template muy corta ({words} palabras, min 100)"
                )
            elif words > 500:
                errs.append(
                    f"respuesta_ideal_template muy larga ({words} palabras, max 500)"
                )

        # next_actions_cliente
        actions = parsed.get("next_actions_cliente")
        if not isinstance(actions, list):
            errs.append("next_actions_cliente no lista")
        elif len(actions) > 3:
            errs.append(f"next_actions_cliente > 3 ({len(actions)})")
        else:
            for i, a in enumerate(actions):
                if not isinstance(a, dict):
                    errs.append(f"next_actions_cliente[{i}] no dict")
                    continue
                for fld in ("accion", "evidencia_a_aportar", "urgencia"):
                    if fld not in a:
                        errs.append(f"next_actions_cliente[{i}] falta {fld}")
                if a.get("urgencia") not in _URGENCIAS:
                    errs.append(
                        f"next_actions_cliente[{i}].urgencia invalida: "
                        f"{a.get('urgencia')!r}"
                    )

        # feedback_marcos
        fm = parsed.get("feedback_marcos", "")
        if not isinstance(fm, str):
            errs.append("feedback_marcos no string")
        elif len(fm) > 250:
            errs.append(f"feedback_marcos > 250 chars ({len(fm)})")

        # Anti-hallucination en respuesta_ideal_template:
        # el LLM NO puede inventar sistemas/productos que no esten en
        # la respuesta del cliente.
        if isinstance(tmpl, str):
            errs.extend(self._detect_hallucinated_systems(tmpl, respuesta_cliente))

        return errs

    @staticmethod
    def _check_madurez_coherence(
        mad: str, dims: dict[str, Any],
    ) -> list[str]:
        """Si los 3 scores dimension <30 -> NO puede ser L4/L5.
        Si los 3 scores >=85 -> NO puede ser L0/L1."""
        errs: list[str] = []
        try:
            vals = [int(dims.get(k, 0)) for k in _DIMENSION_KEYS]
        except (TypeError, ValueError):
            return errs  # otros validators ya marcaran el error
        if all(v < 30 for v in vals) and mad in {"L4", "L5"}:
            errs.append(
                f"madurez '{mad}' incoherente: los 3 dimension_scores <30 "
                f"({vals}) indican nivel inicial L0-L2"
            )
        if all(v >= 85 for v in vals) and mad in {"L0", "L1"}:
            errs.append(
                f"madurez '{mad}' incoherente: los 3 dimension_scores >=85 "
                f"({vals}) indican nivel gestionado L4-L5"
            )
        return errs

    @staticmethod
    def _detect_hallucinated_systems(
        template: str, respuesta_cliente: dict[str, Any],
    ) -> list[str]:
        """Detecta productos comerciales inventados en el template ideal.

        El template ideal debe modelar una respuesta senior pero no
        puede atribuir al cliente sistemas/productos que no estan en su
        respuesta. Excepcion: si el template dice 'un SIEM' generico o
        'herramienta de backup' generico, esta bien. Solo se vetan los
        nombres de marca especificos.
        """
        errs: list[str] = []
        respuesta_text_low = str(respuesta_cliente.get("texto", "")).lower()
        template_low = template.lower()

        for entity in _SUSPICIOUS_ENTITIES:
            if entity in template_low and entity not in respuesta_text_low:
                errs.append(
                    f"hallucinated_system: '{entity}' aparece en "
                    f"respuesta_ideal_template pero no en la respuesta "
                    f"del cliente"
                )
                if len(errs) >= 3:
                    return errs
        return errs

    # ------------------------------------------------------------------
    # Fallback keyword
    # ------------------------------------------------------------------

    def _keyword_fallback(
        self,
        pregunta: dict[str, Any],
        respuesta: dict[str, Any],
        ctx: dict[str, Any],
    ) -> dict[str, Any]:
        """Scoring simple por deteccion de keywords en la respuesta."""
        text = str(respuesta.get("texto", "")).lower()
        words = text.split()
        word_count = len(words)

        # Heuristicas
        has_technical = any(kw in text for kw in (
            "mfa", "siem", "backup", "cifrad", "isoaaa", "iso", "rto", "rpo",
            "politica", "procedimiento", "log", "auditoria", "simulacro",
        ))
        has_evidence = any(kw in text for kw in (
            "documento", "captura", "log", "informe", "certificado",
            "contrato", "acta", "acuerdo",
        ))
        has_metric = any(kw in text for kw in (
            "%", "porcenta", "mensual", "trimestral", "anual", "minutos",
            "horas", "72h", "24h",
        ))

        # Dimension scores basados en heuristicas
        if word_count < 15:
            completitud = 20
            exactitud = 30
            evidencia = 10
            mad = "L1"
        elif word_count < 40:
            completitud = 45 + (20 if has_technical else 0)
            exactitud = 50
            evidencia = 30 if has_evidence else 15
            mad = "L2" if has_technical else "L1"
        elif word_count < 80:
            completitud = 60 + (15 if has_metric else 0)
            exactitud = 60
            evidencia = 50 if has_evidence else 30
            mad = "L3" if (has_technical and has_evidence) else "L2"
        else:
            completitud = 70 + (15 if has_metric else 0)
            exactitud = 70 if has_technical else 55
            evidencia = 65 if has_evidence else 40
            mad = "L4" if (has_technical and has_evidence and has_metric) else "L3"

        score_global = int(round(
            completitud * 0.4 + exactitud * 0.3 + evidencia * 0.3
        ))

        gaps: list[dict[str, Any]] = []
        if not has_evidence:
            gaps.append({
                "tipo": "falta_evidencia",
                "descripcion": (
                    "La respuesta no referencia documento, log, acta ni "
                    "certificado concreto para validar la afirmacion."
                ),
            })
        if word_count < 30:
            gaps.append({
                "tipo": "respuesta_vaga",
                "descripcion": (
                    f"Respuesta muy breve ({word_count} palabras). Un "
                    "auditor ENAC espera detalle operativo y ejemplo."
                ),
            })
        if not has_metric:
            gaps.append({
                "tipo": "dato_inconsistente",
                "descripcion": (
                    "No hay metrica concreta (frecuencia, porcentaje, RTO/RPO). "
                    "Necesario para demostrar madurez gestionada."
                ),
            })

        template = (
            "Un CISO senior respondera a la pregunta del auditor citando: "
            "(1) el documento o politica formal aprobada que regula el "
            "proceso, con referencia normativa aplicable; (2) los sistemas "
            "concretos del alcance a los que aplica (dentro de los que "
            "menciono el cliente); (3) la frecuencia de revision y la "
            "evidencia disponible (log, acta, informe) que el auditor "
            "puede verificar en la reunion; (4) el responsable designado "
            "y la base legal o normativa de la medida. El ejemplo concreto "
            "debe incluir al menos una metrica operativa (numero, "
            "porcentaje, RTO/RPO) y el proceso de escalamiento en caso "
            "de incidente."
        )
        # Asegurar minimo 100 palabras
        while len(template.split()) < 105:
            template += (
                " Adicionalmente, el CISO senior menciona la ultima "
                "revision documentada y el proximo hito de auditoria "
                "interna asociado."
            )

        actions = [
            {
                "accion": "Aportar documento/politica formal aprobada",
                "evidencia_a_aportar": "PDF firmado + version + fecha",
                "urgencia": "1_semana",
            },
        ]
        if not has_metric:
            actions.append({
                "accion": "Incluir metrica concreta del proceso (frecuencia/RTO/RPO)",
                "evidencia_a_aportar": "KPIs del periodo anterior",
                "urgencia": "1_semana",
            })

        feedback = (
            f"Fallback keyword scoring (LLM fallo). Cliente {ctx.get('company_name', '')} "
            f"contesta {word_count} palabras; revisar manualmente antes de usar."
        )[:250]

        return {
            "score_global": score_global,
            "madurez_respuesta": mad,
            "dimension_scores": {
                "completitud": int(completitud),
                "exactitud": int(exactitud),
                "evidencia_referenciada": int(evidencia),
            },
            "gaps_detectados": gaps[:4],
            "respuesta_ideal_template": template,
            "next_actions_cliente": actions[:3],
            "feedback_marcos": feedback,
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
            path = out_dir / f"a12_rejected_attempt_{attempt}_{short_id}.md"
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# A12 REJECTED - attempt {attempt}\n\n")
                f.write(f"- reason: {reason}\n")
                if errors:
                    f.write(f"- errors ({len(errors)}):\n")
                    for e in errors[:20]:
                        f.write(f"    - {e}\n")
                f.write("\n## RAW\n```\n")
                f.write(response.get("response", ""))
                f.write("\n```\n")
            logger.warning("A12 rejected draft saved to %s", path)
        except Exception as exc:
            logger.debug("A12 dump failed: %s", exc)

    def _build_result(
        self,
        *,
        evaluation: dict[str, Any],
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
            "evaluation": evaluation,
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


# Alias retrocompatible con api.py + scaffold previo.
CoachClienteAgent = Agent12CoachClienteEvaluador
