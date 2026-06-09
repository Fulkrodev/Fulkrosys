"""Agent 6 - Analista Contratos Proveedor (Sesion 9 Paso 2.4).

A6 analiza contratos que el CLIENTE de Marcos tiene firmados con SUS
proveedores (hosting, SaaS, desarrolladores, limpieza oficinas, etc.)
y detecta gaps ENS + RGPD. Genera texto de adenda listo para firmar.

DIFERENCIA vs M14 Contracts:
- M14 (+A20): GENERA contratos Marcos <-> cliente desde cero
  (C-001/C-002/C-003).
- A6: ANALIZA contratos cliente <-> proveedor EXISTENTES (externos,
  firmados antes de entrar FULKRO) para detectar gaps compliance.

Output JSON strict con compliance_score + checklist clausulas
obligatorias + gaps sectoriales + TEXTO COMPLETO DE ADENDA lista
para enviar al proveedor.

- Sonnet 4.6 temperature 0.1 max_tokens 4000.
- Prompt caching activado (system ~3-4k tokens, reusable cuando
  Marcos analiza 10+ proveedores del mismo cliente en cascada).
- Validator: schema strict con enums obligatorios.
- Retry=1 con fallback determinista (regex basico) si LLM falla.
"""
from __future__ import annotations

import logging
import os
import pathlib
import re
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.base import AgentBase
from backend.app.agents.prompts.agent_06_contratos import PROMPT

logger = logging.getLogger(__name__)


# Schema enums
_COMPLIANCE_LEVELS = {"conforme", "parcial", "no_conforme", "critico"}
_CLAUSE_QUALITY = {"completo", "incompleto", "ausente"}
_SEVERITIES = {"critico", "alto", "medio", "bajo"}
_ACTIONS = {
    "firmar_adenda",
    "renegociar_contrato",
    "buscar_proveedor_alternativo",
    "aceptar_riesgo_documentado",
}
_URGENCIES = {"inmediata", "1_mes", "1_trimestre", "1_ano"}
_ENS_CATEGORIES = {"BASICA", "MEDIA", "ALTA"}
_PROVIDER_ROLES = {
    "hosting", "saas", "desarrollo", "integrador",
    "limpieza", "consultoria", "otro",
}
_CLIENT_SECTORS = {"sanidad", "aapp", "fintech", "otro"}

_REQUIRED_KEYS: tuple[str, ...] = (
    "compliance_score",
    "compliance_level",
    "mandatory_clauses_check",
    "sector_specific_gaps",
    "addendum_text",
    "recommendation",
    "red_flags",
)

# IDs canonicos de clausulas obligatorias (el LLM DEBE cubrir todas las
# aplicables en mandatory_clauses_check).
_BASE_CLAUSE_IDS: tuple[str, ...] = (
    "art_28_dpa",
    "confidencialidad",
    "duracion_contrato",
    "medidas_seguridad_informacion",
    "subcontratacion_regulada",
    "devolucion_destruccion_datos",
)
_ENS_MEDIA_PLUS_CLAUSE_IDS: tuple[str, ...] = (
    "notificacion_incidente_72h",
    "medidas_tecnicas_organizativas_ens",
    "derecho_auditoria",
    "ubicacion_datos",
)
_ENS_ALTA_CLAUSE_IDS: tuple[str, ...] = (
    "certificacion_ens_proveedor",
    "continuidad_negocio",
    "clearance_personal",
)

# Sonnet 4.6 pricing (USD/Mtoken). Cache rates incluidas.
_SONNET_46_USD_IN: float = 3.0
_SONNET_46_USD_OUT: float = 15.0
_SONNET_46_USD_CACHE_WRITE: float = 3.75
_SONNET_46_USD_CACHE_READ: float = 0.30
_USD_TO_EUR: float = 0.93

_MAX_CONTRACT_CHARS: int = 12000  # tope conservador para evitar bloat tokens_in


class Agent06ContractAnalysisError(Exception):
    """Error irrecuperable del Agente 6 tras agotar reintentos."""


class Agent06AnalistaContratos(AgentBase):
    """Analista contratos proveedor cliente (Sonnet 4.6 JSON strict)."""

    AGENT_ID = 6
    AGENT_NAME = "Analista de Contratos"
    MODEL = "sonnet-4.6"
    TEMPERATURE = 0.1
    MAX_TOKENS = 4000
    SPECIFIC_PROMPT = PROMPT
    # Caching activado: system prompt ~3-4k tokens con catalogo
    # clausulas obligatorias reusable cuando Marcos analiza 10+
    # proveedores del mismo cliente en una sesion.
    ENABLE_PROMPT_CACHING = True

    MAX_RETRIES_ON_INVALID_JSON = 1

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def analyze_provider_contract(
        self,
        db: AsyncSession,
        *,
        contract_text: str,
        provider_name: str,
        provider_role: str,
        criticality: str,
        data_processed: str,
        ens_category: str,
        client_sector: str,
        provider_id: uuid.UUID | str | None = None,
        project_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Analiza un contrato cliente <-> proveedor y genera adenda.

        Args:
            contract_text: texto plano del contrato (idealmente tras OCR
                limpio). Se trunca a 12000 chars para evitar bloat.
            provider_name: nombre razon social proveedor.
            provider_role: hosting / saas / desarrollo / integrador /
                limpieza / consultoria / otro.
            criticality: alta / media / baja (criticidad operativa).
            data_processed: datos_pacientes / datos_empleados /
                datos_clientes / ninguno.
            ens_category: BASICA / MEDIA / ALTA del cliente.
            client_sector: sanidad / aapp / fintech / otro.

        Returns:
            Dict con el ContractAnalysisResult + metadata (tokens,
            coste, cache_*, retry_count, fallback_used).
        """
        if ens_category not in _ENS_CATEGORIES:
            raise ValueError(f"ens_category invalida: {ens_category!r}")
        if client_sector not in _CLIENT_SECTORS:
            raise ValueError(f"client_sector invalido: {client_sector!r}")
        if provider_role not in _PROVIDER_ROLES:
            raise ValueError(f"provider_role invalido: {provider_role!r}")

        truncated = (contract_text or "")[:_MAX_CONTRACT_CHARS]
        if not truncated.strip():
            # Contrato vacio -> fallback directo sin gastar LLM.
            return self._build_result(
                analysis=self._empty_contract_fallback(provider_name),
                response={
                    "tokens_input": 0, "tokens_output": 0,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                    "latency_ms": 0, "model": self.MODEL,
                },
                schema_errors=["contract_text vacio"],
                retry_count=0,
                fallback_used=True,
            )

        user_msg = self._build_user_message(
            contract_text=truncated,
            provider_name=provider_name,
            provider_role=provider_role,
            criticality=criticality,
            data_processed=data_processed,
            ens_category=ens_category,
            client_sector=client_sector,
        )
        context_payload = {
            "provider_name": provider_name,
            "provider_role": provider_role,
            "criticality": criticality,
            "data_processed": data_processed,
            "ens_category": ens_category,
            "client_sector": client_sector,
            "provider_id": str(provider_id) if provider_id else None,
            "contract_chars": len(truncated),
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
            errors = self._validate_schema(parsed, ens_category, client_sector)
            if not errors:
                return self._build_result(
                    analysis=parsed,
                    response=response,
                    schema_errors=[],
                    retry_count=attempt,
                    fallback_used=False,
                )
            last_errors = errors
            retry_count = attempt + 1
            logger.info(
                "A6 attempt %d: %d schema errors; retrying",
                attempt + 1, len(errors),
            )
            self._dump_rejected(
                attempt + 1, response, reason="schema_errors", errors=errors,
            )

        logger.warning(
            "A6 schema invalid after %d attempts, falling back to regex analysis",
            self.MAX_RETRIES_ON_INVALID_JSON + 1,
        )
        fallback = self._regex_fallback(
            contract_text=truncated,
            provider_name=provider_name,
            ens_category=ens_category,
        )
        return self._build_result(
            analysis=fallback,
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
        *,
        contract_text: str,
        provider_name: str,
        provider_role: str,
        criticality: str,
        data_processed: str,
        ens_category: str,
        client_sector: str,
    ) -> str:
        lines = [
            "Analiza este contrato cliente <-> proveedor y detecta gaps ENS/RGPD.",
            "",
            "CONTEXTO:",
            f"- provider_name: {provider_name}",
            f"- provider_role: {provider_role}",
            f"- criticality: {criticality}",
            f"- data_processed: {data_processed}",
            f"- ens_category cliente: {ens_category}",
            f"- client_sector: {client_sector}",
            "",
            "TEXTO DEL CONTRATO:",
            contract_text,
            "",
            "Devuelve SOLO JSON con las 7 claves obligatorias del schema. "
            "Sin markdown, sin backticks.",
        ]
        return "\n".join(lines)

    @staticmethod
    def _retry_hint(errors: list[str]) -> str:
        if not errors:
            return ""
        hint = "\n\nRECORDATORIO TRAS REINTENTO: detecte estos errores de schema: "
        hint += "; ".join(errors[:5])
        hint += ". Corrige y responde de nuevo solo con JSON valido."
        return hint

    # ------------------------------------------------------------------
    # Schema validation
    # ------------------------------------------------------------------

    def _validate_schema(
        self,
        parsed: dict[str, Any],
        ens_category: str,
        client_sector: str,
    ) -> list[str]:
        errs: list[str] = []
        for k in _REQUIRED_KEYS:
            if k not in parsed:
                errs.append(f"falta clave '{k}'")

        score = parsed.get("compliance_score")
        try:
            s = int(score)
            if not (0 <= s <= 100):
                errs.append(f"compliance_score fuera de rango [0,100]: {s}")
        except (TypeError, ValueError):
            errs.append(f"compliance_score no entero: {score!r}")

        lvl = parsed.get("compliance_level")
        if lvl not in _COMPLIANCE_LEVELS:
            errs.append(f"compliance_level invalido: {lvl!r}")

        clauses = parsed.get("mandatory_clauses_check")
        expected_clause_ids = set(_BASE_CLAUSE_IDS)
        if ens_category in ("MEDIA", "ALTA"):
            expected_clause_ids.update(_ENS_MEDIA_PLUS_CLAUSE_IDS)
        if ens_category == "ALTA":
            expected_clause_ids.update(_ENS_ALTA_CLAUSE_IDS)

        if not isinstance(clauses, list):
            errs.append("mandatory_clauses_check debe ser lista")
        else:
            seen_ids: set[str] = set()
            for i, c in enumerate(clauses):
                if not isinstance(c, dict):
                    errs.append(f"mandatory_clauses_check[{i}] no es dict")
                    continue
                for field in ("clause_id", "clause_name", "present", "quality"):
                    if field not in c:
                        errs.append(
                            f"mandatory_clauses_check[{i}] falta {field}"
                        )
                if c.get("quality") not in _CLAUSE_QUALITY:
                    errs.append(
                        f"mandatory_clauses_check[{i}].quality invalido: "
                        f"{c.get('quality')!r}"
                    )
                if not isinstance(c.get("present"), bool):
                    errs.append(
                        f"mandatory_clauses_check[{i}].present no es bool"
                    )
                cid = c.get("clause_id")
                if cid:
                    seen_ids.add(cid)
            missing_required = expected_clause_ids - seen_ids
            if missing_required:
                errs.append(
                    "mandatory_clauses_check no cubre todas las clausulas "
                    f"obligatorias para ENS={ens_category}: "
                    f"faltan {sorted(missing_required)[:5]}"
                )

        sector_gaps = parsed.get("sector_specific_gaps")
        if not isinstance(sector_gaps, list):
            errs.append("sector_specific_gaps debe ser lista")
        elif len(sector_gaps) > 5:
            errs.append(f"sector_specific_gaps > 5 elementos ({len(sector_gaps)})")
        else:
            for i, g in enumerate(sector_gaps):
                if not isinstance(g, dict):
                    errs.append(f"sector_specific_gaps[{i}] no es dict")
                    continue
                for field in ("requirement", "description", "severity"):
                    if field not in g:
                        errs.append(f"sector_specific_gaps[{i}] falta {field}")
                if g.get("severity") not in _SEVERITIES:
                    errs.append(
                        f"sector_specific_gaps[{i}].severity invalido: "
                        f"{g.get('severity')!r}"
                    )

        addendum = parsed.get("addendum_text")
        if not isinstance(addendum, str):
            errs.append("addendum_text no string")
        elif len(addendum) > 3500:
            errs.append(f"addendum_text > 3500 chars ({len(addendum)})")

        rec = parsed.get("recommendation")
        if not isinstance(rec, dict):
            errs.append("recommendation no dict")
        else:
            if rec.get("action") not in _ACTIONS:
                errs.append(
                    f"recommendation.action invalido: {rec.get('action')!r}"
                )
            if rec.get("urgency") not in _URGENCIES:
                errs.append(
                    f"recommendation.urgency invalido: {rec.get('urgency')!r}"
                )
            rat = rec.get("rationale")
            if not isinstance(rat, str):
                errs.append("recommendation.rationale no string")
            elif len(rat) > 400:
                errs.append(
                    f"recommendation.rationale > 400 chars ({len(rat)})"
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
                elif len(f) > 250:
                    errs.append(f"red_flags[{i}] > 250 chars ({len(f)})")

        return errs

    # ------------------------------------------------------------------
    # Fallbacks (LLM falla o contrato vacio)
    # ------------------------------------------------------------------

    @staticmethod
    def _empty_contract_fallback(provider_name: str) -> dict[str, Any]:
        return {
            "compliance_score": 0,
            "compliance_level": "critico",
            "mandatory_clauses_check": [],
            "sector_specific_gaps": [],
            "addendum_text": (
                f"No se puede generar adenda: el texto del contrato con "
                f"{provider_name} esta vacio o no ha sido aportado. Solicitar "
                "el texto integral del contrato firmado al cliente antes de "
                "proceder con el analisis."
            ),
            "recommendation": {
                "action": "renegociar_contrato",
                "urgency": "inmediata",
                "rationale": (
                    "Sin texto de contrato no hay base analitica. Solicitar "
                    "copia al cliente antes de cualquier accion."
                ),
            },
            "red_flags": [
                f"Contrato con {provider_name} no disponible: imposible "
                "auditar gaps sin texto base."
            ],
        }

    def _regex_fallback(
        self,
        *,
        contract_text: str,
        provider_name: str,
        ens_category: str,
    ) -> dict[str, Any]:
        """Analisis tabular con regex cuando el LLM falla.

        No intenta ser exhaustivo — solo marca presencia/ausencia basica
        y sugiere renegociar. La adenda sera un placeholder con warning.
        """
        text_low = contract_text.lower()

        patterns: dict[str, tuple[str, list[str]]] = {
            "art_28_dpa": (
                "Acuerdo encargado tratamiento RGPD art. 28",
                [r"\bart[\s\.]*28\b", r"encargad[oa]\s+del?\s+tratamiento"],
            ),
            "confidencialidad": (
                "Clausula de confidencialidad",
                [r"confidencialidad"],
            ),
            "duracion_contrato": (
                "Duracion del contrato",
                [r"duraci[oó]n", r"vigencia"],
            ),
            "medidas_seguridad_informacion": (
                "Obligaciones de seguridad de la informacion",
                [r"medidas?\s+de\s+seguridad", r"confidencialidad.*integridad"],
            ),
            "subcontratacion_regulada": (
                "Subcontratacion regulada",
                [r"subcontrataci[oó]n", r"subencargado"],
            ),
            "devolucion_destruccion_datos": (
                "Devolucion/destruccion datos al terminar",
                [r"devoluci[oó]n.*datos", r"destruc[sc]i[oó]n.*datos"],
            ),
            "notificacion_incidente_72h": (
                "Notificacion de incidente en <72h",
                [r"72\s*hora", r"setenta\s+y\s+dos\s+hora"],
            ),
            "medidas_tecnicas_organizativas_ens": (
                "Medidas tecnicas y organizativas ENS",
                [r"medidas?\s+t[eé]cnicas?\s+y\s+organizativas", r"\bens\b"],
            ),
            "derecho_auditoria": (
                "Derecho de auditoria del cliente",
                [r"derecho\s+de\s+auditor[ií]a", r"auditor[ií]a\s+sobre"],
            ),
            "ubicacion_datos": (
                "Garantias ubicacion datos UE",
                [r"(uni[oó]n\s+europea|UE|espac?io\s+econ[oó]mico)"],
            ),
        }
        if ens_category == "ALTA":
            patterns.update({
                "certificacion_ens_proveedor": (
                    "Certificacion ENS del proveedor",
                    [r"certificaci[oó]n\s+ens"],
                ),
                "continuidad_negocio": (
                    "Continuidad de negocio",
                    [r"continuidad\s+de\s+negocio", r"plan\s+de\s+continuidad"],
                ),
                "clearance_personal": (
                    "Clearance personal acceso",
                    [r"clearance", r"habilitaci[oó]n\s+de\s+seguridad"],
                ),
            })

        checks: list[dict[str, Any]] = []
        present_count = 0
        total = len(patterns)
        for cid, (name, regexes) in patterns.items():
            present = any(re.search(r, text_low) for r in regexes)
            if present:
                present_count += 1
            checks.append({
                "clause_id": cid,
                "clause_name": name,
                "present": present,
                "quality": "completo" if present else "ausente",
                "evidence_excerpt": "" if not present else "(regex fallback sin cita textual)",
                "gap_description": "" if present else f"No se detecta '{name}' via regex.",
            })

        pct = int(round((present_count / max(1, total)) * 100))
        if pct >= 85:
            level = "conforme"
        elif pct >= 60:
            level = "parcial"
        elif pct >= 30:
            level = "no_conforme"
        else:
            level = "critico"

        return {
            "compliance_score": pct,
            "compliance_level": level,
            "mandatory_clauses_check": checks,
            "sector_specific_gaps": [],
            "addendum_text": (
                f"[FALLBACK REGEX - requiere revision manual]\n\n"
                f"Analisis automatico detecto {present_count}/{total} "
                f"clausulas presentes en contrato con {provider_name}. "
                "El LLM fallo al generar adenda; se recomienda reanalisis "
                "o redaccion manual por asesoria juridica. Clausulas "
                "faltantes a anadir: "
                + ", ".join(c["clause_name"] for c in checks if not c["present"])
                + "."
            )[:3500],
            "recommendation": {
                "action": "renegociar_contrato",
                "urgency": "1_mes",
                "rationale": (
                    "Analisis automatico incompleto (LLM fallo, regex fallback). "
                    "Revisar manualmente antes de tomar decisiones contractuales."
                ),
            },
            "red_flags": [
                "Analisis generado por fallback regex: precision limitada, "
                "reanalizar con LLM disponible o revisar a mano.",
            ],
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
            path = out_dir / f"a6_rejected_attempt_{attempt}_{short_id}.md"
            raw = response.get("response") or ""
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# A6 REJECTED - attempt {attempt}\n\n")
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
            logger.warning("A6 rejected draft saved to %s", path)
        except Exception as exc:
            logger.debug("A6 dump failed: %s", exc)

    def _build_result(
        self,
        *,
        analysis: dict[str, Any],
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
            "analysis": analysis,
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
AnalistaContratosAgent = Agent06AnalistaContratos
