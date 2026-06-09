"""Agent 17 - Cualificador Comercial post-contacto (Sesion 9 Paso 2.3).

A17 scorea leads **despues** del primer contacto con respuestas de
Marcos a 8 preguntas humanas (sponsor, presupuesto, plazo real,
referencia). Es la capa de cualificacion del pipeline comercial
(tras el primer contacto).

Output JSON strict con 6 dimensiones + clasificacion A/B/C/
DESCARTAR + priority + recommendation accionable + red flags.

- Sonnet 4.6 temperature 0.1 max_tokens 2000.
- Prompt caching activado (system ~2k tokens reutilizable).
- Validator: schema strict con enums obligatorios.
- Retry=1 con fallback determinista de scoring simple si LLM falla.
- Persistencia opcional: si ``lead_id`` se pasa, actualiza
  ``leads.lead_score / clasificacion_abc / estado``.
"""
from __future__ import annotations

import logging
import os
import pathlib
import uuid
from typing import Any

from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.base import AgentBase
from backend.app.agents.prompts.agent_17_cualificador import PROMPT

logger = logging.getLogger(__name__)


# Schema enums
_CLASSIFICATIONS = {"A", "B", "C", "DESCARTAR"}
_PRIORITIES = {"ardiendo", "caliente", "tibio", "frio"}
_NEXT_ACTIONS = {
    "agendar_exploratoria",
    "enviar_propuesta",
    "enviar_material_educativo",
    "seguimiento_dias",
    "contactar_referencia",
    "aparcar",
    "descartar",
}
_WHEN_VALUES = {"hoy", "esta_semana", "proxima_semana", "en_2_semanas", "en_1_mes", "en_3_meses"}

_REQUIRED_KEYS: tuple[str, ...] = (
    "lead_score",
    "classification",
    "priority",
    "recommendation",
    "dimension_scores",
    "next_actions",
    "red_flags",
    "rationale",
)

_DIMENSION_KEYS: tuple[str, ...] = (
    "urgencia",
    "presupuesto",
    "sponsor_power",
    "fit_producto",
    "madurez_ens",
    "calidad_lead",
)

# Pesos dimensiones (suman 1.0). Reflejan la guia comercial de
# Marcos: presion temporal + dinero real + quien firma dominan.
_DIMENSION_WEIGHTS: dict[str, float] = {
    "urgencia": 0.25,
    "presupuesto": 0.20,
    "sponsor_power": 0.20,
    "fit_producto": 0.15,
    "madurez_ens": 0.10,
    "calidad_lead": 0.10,
}

# Sonnet 4.6 pricing (USD/Mtoken). Incluye cache rates.
_SONNET_46_USD_IN: float = 3.0
_SONNET_46_USD_OUT: float = 15.0
_SONNET_46_USD_CACHE_WRITE: float = 3.75
_SONNET_46_USD_CACHE_READ: float = 0.30
_USD_TO_EUR: float = 0.93


class Agent17QualificationError(Exception):
    """Error irrecuperable del Agente 17 tras agotar reintentos."""


class Agent17CualificadorComercial(AgentBase):
    """Cualificador comercial post-contacto (Sonnet 4.6 JSON strict)."""

    AGENT_ID = 17
    AGENT_NAME = "Cualificador Comercial"
    MODEL = "sonnet-4.6"
    TEMPERATURE = 0.1
    MAX_TOKENS = 2000
    SPECIFIC_PROMPT = PROMPT
    # Caching activado: system prompt ~2k tokens se reusa a lo largo
    # de la sesion comercial (Marcos puede cualificar 5-10 leads
    # seguidos en 1 tarde).
    ENABLE_PROMPT_CACHING = True

    MAX_RETRIES_ON_INVALID_JSON = 1

    # Mapping classification -> Lead.estado tras cualificar.
    _ESTADO_POR_CLASSIFICATION: dict[str, str] = {
        "A": "cualificando",
        "B": "reunion_exploratoria",
        "C": "educar",
        "DESCARTAR": "descartado",
    }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def qualify_lead(
        self,
        db: AsyncSession,
        *,
        lead_context: dict[str, Any],
        qualification_answers: dict[str, Any],
        lead_id: uuid.UUID | str | None = None,
        project_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Cualifica un lead post-contacto.

        Args:
            lead_context: metadatos empresa + origen del lead.
            qualification_answers: respuestas de Marcos a las 8
                preguntas humanas (contract_status, ens_category_expected,
                deadline, sponsor, budget, tech_team, existing_frameworks,
                lead_quality).
            lead_id: si se pasa, persiste el resultado en ``leads`` via
                update de lead_score / clasificacion_abc / estado.
            project_id: contexto opcional.

        Returns:
            Dict con el QualificationResult + metadata (tokens, coste,
            cache_*, retry_count, fallback_used).
        """
        user_msg = self._build_user_message(lead_context, qualification_answers)
        context_payload = {
            "lead_context": lead_context,
            "qualification_answers": qualification_answers,
            "lead_id": str(lead_id) if lead_id else None,
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
            errors = self._validate_schema(parsed)
            if not errors:
                if lead_id is not None:
                    await self._persist_to_lead(db, lead_id, parsed)
                return self._build_result(
                    qualification=parsed,
                    response=response,
                    schema_errors=[],
                    retry_count=attempt,
                    fallback_used=False,
                )
            last_errors = errors
            retry_count = attempt + 1
            logger.info(
                "A17 attempt %d: %d schema errors; retrying",
                attempt + 1, len(errors),
            )
            self._dump_rejected(
                attempt + 1, response, reason="schema_errors", errors=errors,
            )

        logger.warning(
            "A17 schema invalid after %d attempts, falling back to deterministic scoring",
            self.MAX_RETRIES_ON_INVALID_JSON + 1,
        )
        fallback_qual = self._deterministic_fallback(
            lead_context, qualification_answers
        )
        if lead_id is not None:
            await self._persist_to_lead(db, lead_id, fallback_qual)
        return self._build_result(
            qualification=fallback_qual,
            response=last_response,
            schema_errors=last_errors,
            retry_count=retry_count,
            fallback_used=True,
        )

    # ------------------------------------------------------------------
    # User message
    # ------------------------------------------------------------------

    @staticmethod
    def _build_user_message(
        lead_context: dict[str, Any], qualification_answers: dict[str, Any]
    ) -> str:
        lines: list[str] = [
            "Cualifica este lead comercial post-contacto.",
            "",
            "LEAD CONTEXT:",
        ]
        for key in (
            "company_name", "company_sector", "company_size",
            "origin",
        ):
            if key in lead_context and lead_context[key] not in (None, ""):
                lines.append(f"- {key}: {lead_context[key]}")
        lines.append("")
        lines.append("QUALIFICATION ANSWERS (8 preguntas humanas tras primer contacto):")
        for key in (
            "contract_status", "ens_category_expected", "deadline",
            "sponsor", "budget", "tech_team", "existing_frameworks",
            "lead_quality",
        ):
            if key in qualification_answers:
                val = qualification_answers[key]
                lines.append(f"- {key}: {val}")
        lines.append("")
        lines.append(
            "Devuelve SOLO JSON con las 8 claves obligatorias del schema. "
            "Sin markdown, sin backticks."
        )
        return "\n".join(lines)

    @staticmethod
    def _retry_hint(errors: list[str]) -> str:
        if not errors:
            return ""
        hint = "\n\nRECORDATORIO TRAS REINTENTO: en la version anterior "
        hint += "detecte estos errores de schema: "
        hint += "; ".join(errors[:5])
        hint += ". Corrige y responde de nuevo solo con JSON valido."
        return hint

    # ------------------------------------------------------------------
    # Schema validation
    # ------------------------------------------------------------------

    def _validate_schema(self, parsed: dict[str, Any]) -> list[str]:
        errs: list[str] = []
        for k in _REQUIRED_KEYS:
            if k not in parsed:
                errs.append(f"falta clave '{k}'")

        score = parsed.get("lead_score")
        try:
            s = int(score)
            if not (0 <= s <= 100):
                errs.append(f"lead_score fuera de rango [0,100]: {s}")
        except (TypeError, ValueError):
            errs.append(f"lead_score no entero: {score!r}")

        cls = parsed.get("classification")
        if cls not in _CLASSIFICATIONS:
            errs.append(f"classification invalida: {cls!r}")

        pri = parsed.get("priority")
        if pri not in _PRIORITIES:
            errs.append(f"priority invalida: {pri!r}")

        rec = parsed.get("recommendation")
        if not isinstance(rec, str) or len(rec) == 0:
            errs.append("recommendation vacia o no string")
        elif len(rec) > 250:
            errs.append(f"recommendation > 250 chars ({len(rec)})")

        rat = parsed.get("rationale")
        if not isinstance(rat, str):
            errs.append("rationale no string")
        elif len(rat) > 400:
            errs.append(f"rationale > 400 chars ({len(rat)})")

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

        nxt = parsed.get("next_actions")
        if not isinstance(nxt, list):
            errs.append("next_actions debe ser lista")
        elif len(nxt) > 3:
            errs.append(f"next_actions > 3 elementos ({len(nxt)})")
        else:
            for i, a in enumerate(nxt):
                if not isinstance(a, dict):
                    errs.append(f"next_actions[{i}] no es dict")
                    continue
                if a.get("action") not in _NEXT_ACTIONS:
                    errs.append(
                        f"next_actions[{i}].action invalido: {a.get('action')!r}"
                    )
                if a.get("when") not in _WHEN_VALUES:
                    errs.append(
                        f"next_actions[{i}].when invalido: {a.get('when')!r}"
                    )

        flags = parsed.get("red_flags")
        if not isinstance(flags, list):
            errs.append("red_flags debe ser lista")
        elif len(flags) > 3:
            errs.append(f"red_flags > 3 elementos ({len(flags)})")
        else:
            for i, f in enumerate(flags):
                if not isinstance(f, str):
                    errs.append(f"red_flags[{i}] no es string")
                elif len(f) > 200:
                    errs.append(f"red_flags[{i}] > 200 chars ({len(f)})")

        # Coherencia classification <-> lead_score (soft, solo si
        # todo lo demas valido).
        if not errs:
            try:
                s = int(parsed["lead_score"])
                cls = parsed["classification"]
                ranges = {
                    "A": (70, 100),
                    "B": (40, 69),
                    "C": (20, 39),
                    "DESCARTAR": (0, 19),
                }
                lo, hi = ranges[cls]
                if not (lo <= s <= hi):
                    errs.append(
                        f"classification '{cls}' incoherente con lead_score {s} "
                        f"(rango esperado [{lo},{hi}])"
                    )
            except (TypeError, ValueError, KeyError):
                pass

        return errs

    # ------------------------------------------------------------------
    # Fallback determinista
    # ------------------------------------------------------------------

    def _deterministic_fallback(
        self,
        lead_context: dict[str, Any],
        qualification_answers: dict[str, Any],
    ) -> dict[str, Any]:
        """Scoring fijo por tablas cuando el LLM falla.

        Mapea valores categoricos de qualification_answers a puntos
        0-100 por dimension y combina con _DIMENSION_WEIGHTS.
        """
        dims = {
            "urgencia": self._score_urgencia(qualification_answers),
            "presupuesto": self._score_presupuesto(qualification_answers),
            "sponsor_power": self._score_sponsor(qualification_answers),
            "fit_producto": self._score_fit(lead_context, qualification_answers),
            "madurez_ens": self._score_madurez(qualification_answers),
            "calidad_lead": self._score_calidad(lead_context, qualification_answers),
        }
        weighted = sum(dims[k] * _DIMENSION_WEIGHTS[k] for k in _DIMENSION_KEYS)
        lead_score = int(round(max(0, min(100, weighted))))

        if lead_score >= 70:
            classification = "A"
            priority = "caliente" if lead_score < 85 else "ardiendo"
            action = "agendar_exploratoria"
            when = "esta_semana"
            rec = "Lead prioritario: agendar reunion exploratoria esta semana."
        elif lead_score >= 40:
            classification = "B"
            priority = "tibio"
            action = "agendar_exploratoria"
            when = "en_2_semanas"
            rec = "Potencial real pero faltan piezas: reunion exploratoria en 2 semanas."
        elif lead_score >= 20:
            classification = "C"
            priority = "frio"
            action = "enviar_material_educativo"
            when = "esta_semana"
            rec = "No esta listo: educar con contenido y mantener en pipeline."
        else:
            classification = "DESCARTAR"
            priority = "frio"
            action = "aparcar"
            when = "en_3_meses"
            rec = "Sin presupuesto, sin sponsor, sin plazo. Aparcar 6 meses."

        red_flags = self._detect_red_flags(qualification_answers, dims)

        return {
            "lead_score": lead_score,
            "classification": classification,
            "priority": priority,
            "recommendation": rec[:250],
            "dimension_scores": dims,
            "next_actions": [{"action": action, "when": when}],
            "red_flags": red_flags[:3],
            "rationale": (
                f"Fallback determinista (LLM fallo). Score ponderado "
                f"{lead_score}/100 sobre 6 dimensiones con pesos "
                f"25/20/20/15/10/10. Clasificacion {classification} por rango."
            )[:400],
        }

    @staticmethod
    def _score_urgencia(a: dict[str, Any]) -> int:
        cs = a.get("contract_status", "desconocido")
        dl = a.get("deadline", "sin_plazo")
        cs_map = {"adjudicado": 80, "licitando": 60, "explorando": 30, "desconocido": 10}
        dl_map = {"30d": 95, "3m": 80, "6m": 55, "12m": 30, "sin_plazo": 10}
        return int(round((cs_map.get(cs, 10) + dl_map.get(dl, 10)) / 2))

    @staticmethod
    def _score_presupuesto(a: dict[str, Any]) -> int:
        return {"asignado": 90, "estudiando": 50, "ninguno": 5}.get(
            a.get("budget", "ninguno"), 5
        )

    @staticmethod
    def _score_sponsor(a: dict[str, Any]) -> int:
        return {"claro": 90, "difuso": 45, "sin_identificar": 10}.get(
            a.get("sponsor", "sin_identificar"), 10
        )

    @staticmethod
    def _score_fit(ctx: dict[str, Any], a: dict[str, Any]) -> int:
        # Sector regulado + categoria esperada ayudan al fit.
        sector = str(ctx.get("company_sector", "") or "").lower()
        cat = a.get("ens_category_expected", "desconocida")
        base = 50
        if any(k in sector for k in ("sanidad", "financ", "banc", "admin", "public", "fintech")):
            base += 20
        if cat in ("BASICA", "MEDIA", "ALTA"):
            base += 15
        return min(100, base)

    @staticmethod
    def _score_madurez(a: dict[str, Any]) -> int:
        frameworks = a.get("existing_frameworks") or []
        if not isinstance(frameworks, list):
            frameworks = []
        return min(100, 20 + 20 * len(frameworks))

    @staticmethod
    def _score_calidad(ctx: dict[str, Any], a: dict[str, Any]) -> int:
        origin_map = {
            "referencia": 90, "frio": 30, "evento": 55,
        }
        origin_score = origin_map.get(ctx.get("origin", "frio"), 30)
        lq_map = {"referencia": 90, "calido": 60, "frio": 25}
        lq_score = lq_map.get(a.get("lead_quality", "frio"), 25)
        return int(round((origin_score + lq_score) / 2))

    @staticmethod
    def _detect_red_flags(a: dict[str, Any], dims: dict[str, int]) -> list[str]:
        flags: list[str] = []
        if dims["presupuesto"] <= 10:
            flags.append("Sin presupuesto asignado: baja probabilidad de cierre a corto plazo.")
        if dims["sponsor_power"] <= 20:
            flags.append("Sin sponsor identificado: venta compleja, requiere mapeo decision chain.")
        if a.get("deadline") == "sin_plazo" and a.get("contract_status") == "explorando":
            flags.append("Solo explorando sin plazo: baja presion temporal, riesgo de infinite loop.")
        return flags

    # ------------------------------------------------------------------
    # Persistencia (opcional, si lead_id se pasa)
    # ------------------------------------------------------------------

    async def _persist_to_lead(
        self,
        db: AsyncSession,
        lead_id: uuid.UUID | str,
        qualification: dict[str, Any],
    ) -> None:
        """Actualiza lead_score / clasificacion_abc / estado del Lead.

        Best-effort: si el update falla (lead no existe, RLS, etc.) se
        loguea pero NO se propaga para no invalidar el resultado A17.
        """
        try:
            estado = self._ESTADO_POR_CLASSIFICATION.get(
                qualification.get("classification", ""), None
            )
            cls_abc = qualification.get("classification", "")
            # DESCARTAR no cabe en clasificacion_abc (char(1)).
            cls_short = cls_abc if cls_abc in ("A", "B", "C") else "C"
            await db.execute(
                sql_text(
                    "UPDATE leads SET lead_score = :score, "
                    "clasificacion_abc = :cls, "
                    "estado = COALESCE(:estado, estado), "
                    "fecha_ultima_actualizacion = now() "
                    "WHERE id = :lid"
                ),
                {
                    "score": float(qualification.get("lead_score", 0)),
                    "cls": cls_short,
                    "estado": estado,
                    "lid": str(lead_id),
                },
            )
            await db.flush()
        except Exception as exc:
            logger.warning(
                "A17 persist_to_lead failed for lead %s: %s", lead_id, exc
            )

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
            path = out_dir / f"a17_rejected_attempt_{attempt}_{short_id}.md"
            raw = response.get("response") or ""
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# A17 REJECTED - attempt {attempt}\n\n")
                f.write(f"- reason: {reason}\n")
                f.write(f"- tokens_in/out: {response.get('tokens_input', 0)} / "
                        f"{response.get('tokens_output', 0)}\n")
                if errors:
                    f.write(f"- errors ({len(errors)}):\n")
                    for e in errors[:20]:
                        f.write(f"    - {e}\n")
                f.write("\n## RAW\n```\n")
                f.write(raw)
                f.write("\n```\n")
            logger.warning("A17 rejected draft saved to %s", path)
        except Exception as exc:
            logger.debug("A17 dump failed: %s", exc)

    def _build_result(
        self,
        *,
        qualification: dict[str, Any],
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
            "qualification": qualification,
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


# Alias retrocompatible con api.py + scaffold previo
CualificadorComercialAgent = Agent17CualificadorComercial
