"""Agent 18 — Reunion Exploratoria (Sesion 9 Paso 2.2).

Panel IA live que recalcula en tiempo real (Sonnet 4.6) los outputs
de una reunion exploratoria a partir de 6 bloques de notas A-F que
Marcos teclea en vivo. Output JSON strict (no DOCX, no narrativa
larga) con latencia objetivo <5s.

Validador (sin importes): schema strict con enums obligatorios.
Retry=1 con fallback determinista "UNKNOWN" si el LLM no produce
JSON valido o incumple el schema.
"""
from __future__ import annotations

import logging
import os
import pathlib
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.base import AgentBase
from backend.app.agents.prompts.agent_18_reunion_exploratoria import PROMPT

logger = logging.getLogger(__name__)


# Schema enums
_CATEGORIAS = {"BASICA", "MEDIA", "ALTA", "UNKNOWN"}
_MADUREZ = {"L0", "L1", "L2", "L3", "L4", "L5"}
_VIABILIDAD = {"holgada", "ajustada", "inviable", "desconocida"}
_IMPACTO = {"alto", "medio", "bajo"}
_ESFUERZO = {"1h", "1d", "1w"}

_REQUIRED_KEYS: tuple[str, ...] = (
    "categoria_ens",
    "confianza_categoria",
    "rationale_categoria",
    "madurez_actual",
    "horas_marcos_estimadas",
    "viabilidad_temporal",
    "riesgos_detectados",
    "quick_wins_sugeridas",
    "preguntas_pendientes",
)

# Sonnet 4.6 pricing (USD/Mtoken). Informativo.
# Prompt caching (ephemeral TTL 5 min):
#   - cache_creation = 1.25x base input  -> 3.75 USD/M
#   - cache_read     = 0.10x base input  -> 0.30 USD/M
_SONNET_46_USD_IN: float = 3.0
_SONNET_46_USD_OUT: float = 15.0
_SONNET_46_USD_CACHE_WRITE: float = 3.75
_SONNET_46_USD_CACHE_READ: float = 0.30
_USD_TO_EUR: float = 0.93


class Agent18MeetingError(Exception):
    """Error irrecuperable del Agente 18 tras agotar reintentos."""


class Agent18ReunionExploratoria(AgentBase):
    """Panel IA live reunion exploratoria (Sonnet 4.6 JSON strict)."""

    AGENT_ID = 18
    AGENT_NAME = "Reunion Exploratoria"
    MODEL = "sonnet-4.6"
    TEMPERATURE = 0.1
    MAX_TOKENS = 3000
    SPECIFIC_PROMPT = PROMPT
    # Caching activado: system prompt COMMON_HEADER + PROMPT A18 ~5k tokens
    # se cachea con TTL 5 min. Primera llamada de la reunion paga cache
    # creation (~15-18s, 1.25x base); updates posteriores pagan cache read
    # (~3-5s, 0.1x base). Ver progress/backlog_formal.md nota latencia A18.
    ENABLE_PROMPT_CACHING = True

    MAX_RETRIES_ON_INVALID_JSON = 1

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def analyze_meeting_blocks(
        self,
        db: AsyncSession,
        blocks: dict[str, str],
        blocks_filled: list[str] | None = None,
        *,
        meeting_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Produce JSON insight a partir de 6 bloques A-F.

        Returns dict con insight + schema_valid + tokens + coste + fallback_used.
        """
        blocks_norm = self._normalize_blocks(blocks)
        if blocks_filled is None:
            blocks_filled = [
                k[0].upper() for k, v in blocks_norm.items()
                if isinstance(v, str) and len(v.strip()) >= 5
            ]

        user_msg = self._build_user_message(blocks_norm, blocks_filled)
        context_payload = {
            "blocks": blocks_norm,
            "blocks_filled": blocks_filled,
            "meeting_id": str(meeting_id) if meeting_id else None,
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
                return self._build_result(
                    insight=parsed,
                    response=response,
                    schema_errors=[],
                    retry_count=attempt,
                    fallback_used=False,
                )
            last_errors = errors
            retry_count = attempt + 1
            logger.info(
                "A18 attempt %d: %d schema errors; retrying",
                attempt + 1, len(errors),
            )
            self._dump_rejected(
                attempt + 1, response, reason="schema_errors", errors=errors,
            )

        logger.warning(
            "A18 schema invalid after %d attempts, falling back to UNKNOWN",
            self.MAX_RETRIES_ON_INVALID_JSON + 1,
        )
        fallback_insight = self._deterministic_fallback(blocks_norm, blocks_filled)
        return self._build_result(
            insight=fallback_insight,
            response=last_response,
            schema_errors=last_errors,
            retry_count=retry_count,
            fallback_used=True,
        )

    # ------------------------------------------------------------------
    # Block normalization + user message
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_blocks(blocks: dict[str, str]) -> dict[str, str]:
        canonical_keys = (
            "A_contexto",
            "B_informacion",
            "C_madurez",
            "D_plazos",
            "E_presupuesto",
            "F_equipo",
        )
        return {k: str(blocks.get(k, "") or "") for k in canonical_keys}

    @staticmethod
    def _build_user_message(
        blocks: dict[str, str], blocks_filled: list[str]
    ) -> str:
        lines = [
            "Bloques actuales de la reunion (Markdown de Marcos):",
        ]
        for key in (
            "A_contexto", "B_informacion", "C_madurez",
            "D_plazos", "E_presupuesto", "F_equipo",
        ):
            content = blocks.get(key, "").strip()
            letter = key[0]
            if content:
                lines.append(f"## Bloque {letter} ({key})")
                lines.append(content)
            else:
                lines.append(f"## Bloque {letter} ({key}) - (vacio)")
        lines.append("")
        lines.append(
            f"blocks_filled: {blocks_filled}. Devuelve SOLO JSON con las "
            "9 claves obligatorias del schema. Sin markdown, sin backticks."
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

        cat = parsed.get("categoria_ens")
        if cat not in _CATEGORIAS:
            errs.append(f"categoria_ens invalida: {cat!r}")

        conf = parsed.get("confianza_categoria")
        try:
            conf_val = float(conf)
            if not (0.0 <= conf_val <= 1.0):
                errs.append(f"confianza_categoria fuera de rango [0,1]: {conf_val}")
        except (TypeError, ValueError):
            errs.append(f"confianza_categoria no numerico: {conf!r}")

        rat = parsed.get("rationale_categoria")
        if not isinstance(rat, str):
            errs.append("rationale_categoria debe ser string")
        elif len(rat) > 250:
            errs.append(
                f"rationale_categoria > 250 chars ({len(rat)})"
            )

        mad = parsed.get("madurez_actual")
        if mad not in _MADUREZ:
            errs.append(f"madurez_actual invalida: {mad!r}")

        horas = parsed.get("horas_marcos_estimadas")
        if not isinstance(horas, dict):
            errs.append("horas_marcos_estimadas debe ser dict")
        else:
            for k in ("min", "max"):
                try:
                    v = int(horas.get(k))
                    if v < 0 or v > 500:
                        errs.append(
                            f"horas_marcos_estimadas.{k} fuera rango [0,500]: {v}"
                        )
                except (TypeError, ValueError):
                    errs.append(
                        f"horas_marcos_estimadas.{k} no entero: {horas.get(k)!r}"
                    )
            if not isinstance(horas.get("rationale"), str):
                errs.append("horas_marcos_estimadas.rationale debe ser string")

        viab = parsed.get("viabilidad_temporal")
        if viab not in _VIABILIDAD:
            errs.append(f"viabilidad_temporal invalida: {viab!r}")

        riesgos = parsed.get("riesgos_detectados")
        if not isinstance(riesgos, list):
            errs.append("riesgos_detectados debe ser lista")
        elif len(riesgos) > 3:
            errs.append(f"riesgos_detectados tiene > 3 elementos ({len(riesgos)})")
        else:
            for i, r in enumerate(riesgos):
                if not isinstance(r, dict):
                    errs.append(f"riesgos[{i}] no es dict")
                    continue
                for field in ("titulo", "impacto", "descripcion"):
                    if field not in r:
                        errs.append(f"riesgos[{i}] falta {field}")
                if r.get("impacto") not in _IMPACTO:
                    errs.append(f"riesgos[{i}].impacto invalido: {r.get('impacto')!r}")

        quicks = parsed.get("quick_wins_sugeridas")
        if not isinstance(quicks, list):
            errs.append("quick_wins_sugeridas debe ser lista")
        elif len(quicks) > 3:
            errs.append(f"quick_wins_sugeridas > 3 elementos ({len(quicks)})")
        else:
            for i, q in enumerate(quicks):
                if not isinstance(q, dict):
                    errs.append(f"quick_wins[{i}] no es dict")
                    continue
                for field in ("titulo", "esfuerzo", "impacto"):
                    if field not in q:
                        errs.append(f"quick_wins[{i}] falta {field}")
                if q.get("esfuerzo") not in _ESFUERZO:
                    errs.append(
                        f"quick_wins[{i}].esfuerzo invalido: {q.get('esfuerzo')!r}"
                    )

        preg = parsed.get("preguntas_pendientes")
        if not isinstance(preg, list):
            errs.append("preguntas_pendientes debe ser lista")
        elif len(preg) > 5:
            errs.append(f"preguntas_pendientes > 5 elementos ({len(preg)})")
        elif any(not isinstance(p, str) for p in preg):
            errs.append("preguntas_pendientes contiene no-strings")

        return errs

    # ------------------------------------------------------------------
    # Fallback determinista
    # ------------------------------------------------------------------

    def _deterministic_fallback(
        self, blocks: dict[str, str], blocks_filled: list[str]
    ) -> dict[str, Any]:
        """Si el LLM falla, devolvemos un insight minimo con UNKNOWN."""
        preguntas = []
        if "A" not in blocks_filled:
            preguntas.append(
                "Cuentame un poco el contexto: a que sector pertenece la empresa y cual es el objetivo de esta reunion?"
            )
        if "B" not in blocks_filled:
            preguntas.append(
                "Que sistemas de informacion entran en el alcance de la certificacion?"
            )
        if "C" not in blocks_filled:
            preguntas.append(
                "Teneis politicas de seguridad documentadas? Alguna certificacion ISO 27001 previa?"
            )
        if "D" not in blocks_filled:
            preguntas.append(
                "Cual es el plazo comprometido? Hay una fecha concreta (licitacion, auditoria) detras?"
            )
        if "F" not in blocks_filled:
            preguntas.append(
                "Quien seria el interlocutor principal y quien firma desde direccion?"
            )
        if not preguntas:
            preguntas.append(
                "Hay algun aspecto del proyecto que no hayamos cubierto todavia?"
            )
        return {
            "categoria_ens": "UNKNOWN",
            "confianza_categoria": 0.0,
            "rationale_categoria": "Informacion insuficiente para estimar categoria con confianza.",
            "madurez_actual": "L0",
            "horas_marcos_estimadas": {
                "min": 0,
                "max": 0,
                "rationale": "Sin datos suficientes para estimar horas.",
            },
            "viabilidad_temporal": "desconocida",
            "riesgos_detectados": [],
            "quick_wins_sugeridas": [],
            "preguntas_pendientes": preguntas[:5],
        }

    # ------------------------------------------------------------------
    # Debug dump + result shaping
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
            path = out_dir / f"a18_rejected_attempt_{attempt}_{short_id}.md"
            raw = response.get("response") or ""
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# A18 REJECTED — attempt {attempt}\n\n")
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
            logger.warning("A18 rejected draft saved to %s", path)
        except Exception as exc:
            logger.debug("A18 dump failed: %s", exc)

    def _build_result(
        self,
        *,
        insight: dict[str, Any],
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
            "insight": insight,
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


# Alias retrocompatible con scaffold previo
AsistenteReunionExploratoriaAgent = Agent18ReunionExploratoria
