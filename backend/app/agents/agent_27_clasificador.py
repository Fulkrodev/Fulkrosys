"""Agent 27 - Clasificador IDMS (Sesion 9 Paso 3.2).

Complementa (NO reemplaza) la heuristica determinista M24
`_auto_classify_folder`. Cuando un documento queda en `99_Misc`
por falta de match de keywords, A27 intenta desambiguar leyendo el
contenido del documento (ya extraido por M24 al intake).

Modelo: Haiku 4.5 (claude-haiku-4-5). Razon: clasificacion corta +
alto volumen (potencialmente 50-200 docs por proyecto en batch
inicial) + coste critico. Output JSON ~400 tokens.

Output incluye:
- suggested_folder_code (00-13 o 99 del catalogo §2.15).
- confidence 0-1.
- requires_human_review (True si confidence <0.85 o hay alternativas).
- suggested_tags measure_ens / sector / normativa (max 5).
- alternative_folders (max 2, si confidence principal <0.8).

Integracion M24 opcional (opt-in): tras intake determinista, si el
documento quedo en 99 Misc o cualquier folder con heuristica debil,
el caller invoca A27 y aplica la propuesta actualizando folder_id +
creando DocumentTag(source='llm') + dejando status=draft para que
Marcos apruebe la clasificacion.

Prompt caching ENABLED: system prompt ~3k tokens con catalogo 15
carpetas + heuristicas sector se reutiliza en batch (50+ docs).
"""
from __future__ import annotations

import logging
import os
import pathlib
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.base import AgentBase
from backend.app.agents.prompts.agent_27_clasificador_idms import PROMPT

logger = logging.getLogger(__name__)


# Catalogo canonico de folder codes (15 del esqueleto §2.15 FULKRO).
VALID_FOLDER_CODES: frozenset[str] = frozenset({
    "00", "01", "02", "03", "04", "05", "06", "07",
    "08", "09", "10", "11", "12", "13", "99",
})

FOLDER_NAMES: dict[str, str] = {
    "00": "Contractual",
    "01": "Gobierno",
    "02": "Categorizacion",
    "03": "Analisis_Riesgos",
    "04": "Declaracion_Aplicabilidad",
    "05": "Plan_Adecuacion",
    "06": "Normativa",
    "07": "Procedimientos",
    "08": "Registros_Operativos",
    "09": "Evidencias",
    "10": "Continuidad",
    "11": "Formacion",
    "12": "Proveedores",
    "13": "Informes_Tecnicos",
    "99": "Misc",
}

# Enums auxiliares
_VALID_TAG_TYPES = {"measure_ens", "sector", "normativa"}
_VALID_SECTORS = {"sanidad", "aapp", "fintech", "otro"}
_VALID_ENS_CATEGORIES = {"BASICA", "MEDIA", "ALTA"}

_REQUIRED_KEYS: tuple[str, ...] = (
    "suggested_folder_code",
    "suggested_folder_name",
    "confidence",
    "reasoning",
    "suggested_tags",
    "alternative_folders",
    "requires_human_review",
)

# Haiku 4.5 pricing (USD/Mtoken)
_HAIKU_45_USD_IN: float = 0.80
_HAIKU_45_USD_OUT: float = 4.00
_HAIKU_45_USD_CACHE_WRITE: float = 1.00   # 1.25x base
_HAIKU_45_USD_CACHE_READ: float = 0.08    # 0.10x base
_USD_TO_EUR: float = 0.93

# Umbrales
_AUTO_APPROVABLE_THRESHOLD: float = 0.85
_ALT_REVIEW_THRESHOLD: float = 0.50


class Agent27ClassificationError(Exception):
    """Error irrecuperable del Agente 27 tras agotar reintentos."""


class Agent27ClasificadorIDMS(AgentBase):
    """Clasificador IDMS de documentos ambiguos (Haiku 4.5 JSON strict)."""

    AGENT_ID = 27
    AGENT_NAME = "Clasificador IDMS"
    MODEL = "haiku-4.5"
    TEMPERATURE = 0.1
    MAX_TOKENS = 600
    SPECIFIC_PROMPT = PROMPT
    ENABLE_PROMPT_CACHING = True

    MAX_RETRIES_ON_INVALID_JSON = 1

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def classify_document(
        self,
        db: AsyncSession,
        *,
        document_name: str,
        content_excerpt: str,
        deterministic_attempt: dict[str, Any] | None = None,
        client_context: dict[str, Any] | None = None,
        document_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Clasifica un documento ambiguo proponiendo folder + tags."""
        client_context = client_context or {
            "sector": "otro", "ens_category": "MEDIA",
        }
        self._validate_inputs(client_context)

        excerpt = (content_excerpt or "").strip()
        if not excerpt or len(excerpt) < 20:
            # Sin contenido util -> no gasta LLM
            return self._build_result(
                classification=self._empty_excerpt_fallback(document_name),
                response={
                    "tokens_input": 0, "tokens_output": 0,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                    "latency_ms": 0, "model": self.MODEL,
                },
                schema_errors=["content_excerpt vacio o <20 chars"],
                retry_count=0,
                fallback_used=True,
            )

        user_msg = self._build_user_message(
            document_name=document_name,
            content_excerpt=excerpt,
            deterministic_attempt=deterministic_attempt,
            client_context=client_context,
        )
        context_payload = {
            "document_name": document_name,
            "document_id": str(document_id) if document_id else None,
            "content_chars": len(excerpt),
            "deterministic_attempt": deterministic_attempt,
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
            errors = self._validate_schema(parsed)
            if not errors:
                # Post-process: forzar requires_human_review segun logica
                parsed = self._enforce_review_flag(parsed)
                return self._build_result(
                    classification=parsed,
                    response=response,
                    schema_errors=[],
                    retry_count=attempt,
                    fallback_used=False,
                )
            last_errors = errors
            retry_count = attempt + 1
            logger.info(
                "A27 attempt %d: %d schema errors; retrying",
                attempt + 1, len(errors),
            )
            self._dump_rejected(
                attempt + 1, response, reason="schema_errors", errors=errors,
            )

        logger.warning(
            "A27 schema invalid after %d attempts, falling back to Misc",
            self.MAX_RETRIES_ON_INVALID_JSON + 1,
        )
        return self._build_result(
            classification=self._misc_fallback(document_name),
            response=last_response,
            schema_errors=last_errors,
            retry_count=retry_count,
            fallback_used=True,
        )

    async def classify_batch(
        self,
        db: AsyncSession,
        *,
        documents: list[dict[str, Any]],
        client_context: dict[str, Any] | None = None,
        project_id: uuid.UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Clasifica una lista de documentos ambiguos.

        Cada item debe tener `document_name`, `content_excerpt` y
        opcionalmente `deterministic_attempt`, `document_id`. System
        prompt se cachea desde el primer item.
        """
        results: list[dict[str, Any]] = []
        for d in documents:
            r = await self.classify_document(
                db,
                document_name=d["document_name"],
                content_excerpt=d.get("content_excerpt", ""),
                deterministic_attempt=d.get("deterministic_attempt"),
                client_context=client_context,
                document_id=d.get("document_id"),
                project_id=project_id,
            )
            results.append(r)
        return results

    # ------------------------------------------------------------------
    # Input validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_inputs(client_context: dict[str, Any]) -> None:
        sector = client_context.get("sector")
        if sector not in _VALID_SECTORS:
            raise ValueError(
                f"client_context.sector invalido: {sector!r}. "
                f"Validos: {_VALID_SECTORS}"
            )
        cat = client_context.get("ens_category")
        if cat is not None and cat not in _VALID_ENS_CATEGORIES:
            raise ValueError(
                f"client_context.ens_category invalida: {cat!r}"
            )

    # ------------------------------------------------------------------
    # User message
    # ------------------------------------------------------------------

    @staticmethod
    def _build_user_message(
        *,
        document_name: str,
        content_excerpt: str,
        deterministic_attempt: dict[str, Any] | None,
        client_context: dict[str, Any],
    ) -> str:
        det_str = "(no aportado)"
        if deterministic_attempt:
            det_str = (
                f"folder={deterministic_attempt.get('suggested_folder', '?')} "
                f"confidence={deterministic_attempt.get('confidence', '?')}"
            )
        # Truncar a 2000 chars para no inflar tokens_in
        excerpt = content_excerpt[:2000]
        lines = [
            "Clasifica este documento en una de las 15 carpetas estandar.",
            "",
            f"DOCUMENT NAME: {document_name}",
            f"DETERMINISTIC ATTEMPT M24: {det_str}",
            "",
            "CLIENT CONTEXT:",
            f"- sector: {client_context.get('sector', 'otro')}",
            f"- ens_category: {client_context.get('ens_category', 'MEDIA')}",
            "",
            f"CONTENT EXCERPT (primeros {len(excerpt)} chars):",
            excerpt,
            "",
            "Devuelve SOLO JSON con las 7 claves obligatorias. "
            "Sin markdown exterior, sin backticks.",
        ]
        return "\n".join(lines)

    @staticmethod
    def _retry_hint(errors: list[str]) -> str:
        if not errors:
            return ""
        hint = "\n\nRECORDATORIO TRAS REINTENTO: errores: "
        hint += "; ".join(errors[:5])
        hint += ". Corrige y responde solo JSON valido."
        return hint

    # ------------------------------------------------------------------
    # Schema validation
    # ------------------------------------------------------------------

    def _validate_schema(self, parsed: dict[str, Any]) -> list[str]:
        errs: list[str] = []
        for k in _REQUIRED_KEYS:
            if k not in parsed:
                errs.append(f"falta clave '{k}'")
        if errs:
            return errs

        code = parsed.get("suggested_folder_code")
        if code not in VALID_FOLDER_CODES:
            errs.append(
                f"suggested_folder_code invalido: {code!r}. "
                f"Debe ser uno de {sorted(VALID_FOLDER_CODES)}"
            )
        name = parsed.get("suggested_folder_name")
        if not isinstance(name, str) or not name:
            errs.append("suggested_folder_name vacio o no string")

        conf = parsed.get("confidence")
        try:
            c = float(conf)
            if not (0.0 <= c <= 1.0):
                errs.append(f"confidence fuera [0,1]: {c}")
        except (TypeError, ValueError):
            errs.append(f"confidence no numerica: {conf!r}")

        reason = parsed.get("reasoning", "")
        if not isinstance(reason, str) or not reason:
            errs.append("reasoning vacio")
        elif len(reason) > 250:
            errs.append(f"reasoning > 250 chars ({len(reason)})")

        tags = parsed.get("suggested_tags", [])
        if not isinstance(tags, list):
            errs.append("suggested_tags no lista")
        elif len(tags) > 5:
            errs.append(f"suggested_tags > 5 ({len(tags)})")
        else:
            for i, t in enumerate(tags):
                if not isinstance(t, dict):
                    errs.append(f"suggested_tags[{i}] no dict")
                    continue
                if t.get("tag_type") not in _VALID_TAG_TYPES:
                    errs.append(
                        f"suggested_tags[{i}].tag_type invalido: "
                        f"{t.get('tag_type')!r}"
                    )
                if not isinstance(t.get("value"), str):
                    errs.append(f"suggested_tags[{i}].value no string")
                try:
                    tc = float(t.get("confidence", -1))
                    if not (0.0 <= tc <= 1.0):
                        errs.append(
                            f"suggested_tags[{i}].confidence fuera [0,1]: {tc}"
                        )
                except (TypeError, ValueError):
                    errs.append(
                        f"suggested_tags[{i}].confidence no numerica"
                    )

        alts = parsed.get("alternative_folders", [])
        if not isinstance(alts, list):
            errs.append("alternative_folders no lista")
        elif len(alts) > 2:
            errs.append(f"alternative_folders > 2 ({len(alts)})")
        else:
            for i, a in enumerate(alts):
                if not isinstance(a, dict):
                    errs.append(f"alternative_folders[{i}] no dict")
                    continue
                if a.get("folder_code") not in VALID_FOLDER_CODES:
                    errs.append(
                        f"alternative_folders[{i}].folder_code invalido: "
                        f"{a.get('folder_code')!r}"
                    )
                try:
                    ac = float(a.get("confidence", -1))
                    if not (0.0 <= ac <= 1.0):
                        errs.append(
                            f"alternative_folders[{i}].confidence fuera [0,1]: {ac}"
                        )
                except (TypeError, ValueError):
                    errs.append(
                        f"alternative_folders[{i}].confidence no numerica"
                    )

        if not isinstance(parsed.get("requires_human_review"), bool):
            errs.append("requires_human_review no es bool")

        return errs

    @staticmethod
    def _enforce_review_flag(parsed: dict[str, Any]) -> dict[str, Any]:
        """Fuerza coherencia de requires_human_review segun umbrales."""
        try:
            c = float(parsed.get("confidence", 0.0))
        except (TypeError, ValueError):
            c = 0.0
        alts = parsed.get("alternative_folders", []) or []
        any_alt_relevant = False
        for a in alts:
            if isinstance(a, dict):
                try:
                    ac = float(a.get("confidence", 0.0))
                    if ac >= _ALT_REVIEW_THRESHOLD:
                        any_alt_relevant = True
                        break
                except (TypeError, ValueError):
                    pass
        # Forzado: auto-aprobable solo si confidence alta y sin alternativas
        parsed["requires_human_review"] = (
            c < _AUTO_APPROVABLE_THRESHOLD or any_alt_relevant
        )
        return parsed

    # ------------------------------------------------------------------
    # Fallbacks
    # ------------------------------------------------------------------

    @staticmethod
    def _empty_excerpt_fallback(document_name: str) -> dict[str, Any]:
        return {
            "suggested_folder_code": "99",
            "suggested_folder_name": FOLDER_NAMES["99"],
            "confidence": 0.2,
            "reasoning": (
                f"Contenido vacio o insuficiente para '{document_name}'. "
                "Se asigna a 99_Misc hasta que el contenido este disponible."
            )[:250],
            "suggested_tags": [],
            "alternative_folders": [],
            "requires_human_review": True,
        }

    @staticmethod
    def _misc_fallback(document_name: str) -> dict[str, Any]:
        return {
            "suggested_folder_code": "99",
            "suggested_folder_name": FOLDER_NAMES["99"],
            "confidence": 0.1,
            "reasoning": (
                f"Fallback por fallo LLM clasificando '{document_name}'. "
                "Requiere revision manual."
            )[:250],
            "suggested_tags": [],
            "alternative_folders": [],
            "requires_human_review": True,
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
            path = out_dir / f"a27_rejected_attempt_{attempt}_{short_id}.md"
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# A27 REJECTED - attempt {attempt}\n\n")
                f.write(f"- reason: {reason}\n")
                if errors:
                    f.write(f"- errors ({len(errors)}):\n")
                    for e in errors[:20]:
                        f.write(f"    - {e}\n")
                f.write("\n## RAW\n```\n")
                f.write(response.get("response", ""))
                f.write("\n```\n")
            logger.warning("A27 rejected draft saved to %s", path)
        except Exception as exc:
            logger.debug("A27 dump failed: %s", exc)

    def _build_result(
        self,
        *,
        classification: dict[str, Any],
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
            (tokens_in / 1_000_000) * _HAIKU_45_USD_IN
            + (cache_creation / 1_000_000) * _HAIKU_45_USD_CACHE_WRITE
            + (cache_read / 1_000_000) * _HAIKU_45_USD_CACHE_READ
            + (tokens_out / 1_000_000) * _HAIKU_45_USD_OUT
        ) * _USD_TO_EUR
        return {
            "classification": classification,
            "schema_valid": not schema_errors,
            "schema_errors": schema_errors,
            "retry_count": retry_count,
            "tokens_input": tokens_in,
            "tokens_output": tokens_out,
            "cache_creation_input_tokens": cache_creation,
            "cache_read_input_tokens": cache_read,
            "cost_eur_estimated": round(cost_eur, 6),
            "latency_ms": int(response.get("latency_ms", 0) or 0),
            "model": response.get("model", self.MODEL),
            "fallback_used": fallback_used,
        }


# Alias retrocompatible con api.py + scaffold previo
ClasificadorIDMSAgent = Agent27ClasificadorIDMS
