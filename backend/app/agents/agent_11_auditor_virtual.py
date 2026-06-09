"""Agent 11 - Auditor Virtual Suplementario (Sesion 9 Paso 2.6).

A11 NO reemplaza M10 `audit_simulator`. M10 sigue evaluando las 58
preguntas ENAC deterministas L0-L5 con matching de evidencias. A11
anade encima 3 capas de valor senior:

1) PAC priorizado sector-aware: toma las NC mayores + NC menores que
   M10 ya detecto y construye un Plan de Accion Correctivo en 3-5
   fases con responsables, esfuerzos y camino critico.

2) Preguntas contextuales sector: 3-5 preguntas adicionales que un
   auditor ENAC real podria hacer (RGPD art. 9 si sanidad; LCSP /
   FACe / DIR3 si AAPP; DORA si fintech) con criterios L0-L5.

3) Narrativa ejecutiva dry-run: resumen markdown 400-600 palabras con
   veredicto + probabilidad_certificacion_primera + riesgos.

ENTRADAS: m10_audit_result (determinista intacto) + client_context.
SALIDA: PAC + preguntas_contextuales + narrativa + metadata LLM.

- Opus 4.7 temperature 0.1 max_tokens 8000 (Opus aporta valor
  diferencial en priorizacion + narrativa senior vs Sonnet).
- Prompt caching activado (system prompt ~5-6k tokens).
- Validator: schema strict + anti-hallucination codigos ENS: los
  nc_origen referenciados DEBEN estar en m10_audit_result.
- Retry=1 con fallback determinista (PAC tabular reglas fijas).
"""
from __future__ import annotations

import logging
import os
import pathlib
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.base import AgentBase
from backend.app.agents.prompts.agent_11_auditor_virtual import PROMPT

logger = logging.getLogger(__name__)


# Schema enums
_ENS_CATEGORIES = {"BASICA", "MEDIA", "ALTA"}
_SECTORS = {"sanidad", "aapp", "fintech", "otro"}
_PRIORIDADES = {"critica", "alta", "media", "baja"}
_VEREDICTOS = {
    "listo_auditar", "listo_con_riesgos", "no_listo_plazo", "muy_lejos",
}

_REQUIRED_TOP_KEYS: tuple[str, ...] = (
    "pac_priorizado",
    "preguntas_contextuales_sector",
    "narrativa_ejecutiva",
)

# Opus 4.7 pricing (USD/Mtoken).
_OPUS_47_USD_IN: float = 15.0
_OPUS_47_USD_OUT: float = 75.0
_OPUS_47_USD_CACHE_WRITE: float = 18.75  # 1.25x base
_OPUS_47_USD_CACHE_READ: float = 1.50    # 0.10x base
_USD_TO_EUR: float = 0.93


class Agent11AuditError(Exception):
    """Error irrecuperable del Agente 11 tras agotar reintentos."""


class Agent11AuditorVirtual(AgentBase):
    """Auditor virtual suplementario a M10 (Opus 4.7 JSON strict)."""

    AGENT_ID = 11
    AGENT_NAME = "Auditor Interno Virtual"
    MODEL = "opus-4.7"
    TEMPERATURE = 0.1
    MAX_TOKENS = 8000
    SPECIFIC_PROMPT = PROMPT
    ENABLE_PROMPT_CACHING = True

    MAX_RETRIES_ON_INVALID_JSON = 1

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_supplementary_audit(
        self,
        db: AsyncSession,
        *,
        m10_audit_result: dict[str, Any],
        client_context: dict[str, Any],
        project_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Genera PAC + preguntas sector + narrativa suplementarios."""
        self._validate_inputs(m10_audit_result, client_context)
        user_msg = self._build_user_message(m10_audit_result, client_context)
        context_payload = {
            "m10_audit_result": m10_audit_result,
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
            errors = self._validate_schema(
                parsed, m10_audit_result, client_context
            )
            if not errors:
                return self._build_result(
                    audit=parsed,
                    response=response,
                    schema_errors=[],
                    retry_count=attempt,
                    fallback_used=False,
                )
            last_errors = errors
            retry_count = attempt + 1
            logger.info(
                "A11 attempt %d: %d schema errors; retrying",
                attempt + 1, len(errors),
            )
            self._dump_rejected(
                attempt + 1, response, reason="schema_errors", errors=errors,
            )

        logger.warning(
            "A11 schema invalid after %d attempts, falling back to deterministic PAC",
            self.MAX_RETRIES_ON_INVALID_JSON + 1,
        )
        fallback = self._deterministic_fallback(m10_audit_result, client_context)
        return self._build_result(
            audit=fallback,
            response=last_response,
            schema_errors=last_errors,
            retry_count=retry_count,
            fallback_used=True,
        )

    # ------------------------------------------------------------------
    # Input validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_inputs(
        m10_audit_result: dict[str, Any],
        client_context: dict[str, Any],
    ) -> None:
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
        for required in ("score_conformidad", "categoria_ens", "nc_mayores", "nc_menores"):
            if required not in m10_audit_result:
                raise ValueError(
                    f"m10_audit_result falta campo '{required}'"
                )

    # ------------------------------------------------------------------
    # User message
    # ------------------------------------------------------------------

    @staticmethod
    def _build_user_message(
        m10_audit_result: dict[str, Any],
        client_context: dict[str, Any],
    ) -> str:
        nc_mayores = m10_audit_result.get("nc_mayores", []) or []
        nc_menores = m10_audit_result.get("nc_menores", []) or []

        lines = [
            "Genera el audit suplementario (PAC + preguntas sector + narrativa).",
            "",
            "CLIENT CONTEXT:",
            f"- company_name: {client_context.get('company_name', '')}",
            f"- sector: {client_context.get('sector')}",
            f"- size: {client_context.get('size', '')}",
            f"- ens_category: {client_context.get('ens_category')}",
            f"- is_aapp: {client_context.get('is_aapp', False)}",
            f"- target_audit_date: {client_context.get('target_audit_date', 'no definida')}",
            "",
            "M10 AUDIT RESULT (deterministico, NO modificar):",
            f"- score_conformidad: {m10_audit_result.get('score_conformidad')}%",
            f"- categoria_ens: {m10_audit_result.get('categoria_ens')}",
            f"- preguntas_L5 / L4 / L3 / L2 / L1 / L0: "
            f"{m10_audit_result.get('preguntas_L5', 0)} / "
            f"{m10_audit_result.get('preguntas_L4', 0)} / "
            f"{m10_audit_result.get('preguntas_L3', 0)} / "
            f"{m10_audit_result.get('preguntas_L2', 0)} / "
            f"{m10_audit_result.get('preguntas_L1', 0)} / "
            f"{m10_audit_result.get('preguntas_L0', 0)}",
            f"- total_preguntas: {m10_audit_result.get('preguntas_respondidas_total', 0)}",
            "",
            f"NC MAYORES ({len(nc_mayores)} items, SOLO puedes referenciarlas con nc_origen):",
        ]
        for nc in nc_mayores[:10]:
            lines.append(f"    * {nc.get('codigo', '?')}: {nc.get('descripcion', '?')}")
        lines.append("")
        lines.append(f"NC MENORES ({len(nc_menores)} items):")
        for nc in nc_menores[:20]:
            lines.append(f"    * {nc.get('codigo', '?')}: {nc.get('descripcion', '?')}")
        lines.append("")
        lines.append(
            "Devuelve SOLO JSON con las 3 claves obligatorias (pac_priorizado, "
            "preguntas_contextuales_sector, narrativa_ejecutiva). Sin markdown "
            "exterior, sin backticks."
        )
        return "\n".join(lines)

    @staticmethod
    def _retry_hint(errors: list[str]) -> str:
        if not errors:
            return ""
        hint = "\n\nRECORDATORIO TRAS REINTENTO: detecte errores de schema: "
        hint += "; ".join(errors[:5])
        hint += ". Corrige y responde solo con JSON valido."
        return hint

    # ------------------------------------------------------------------
    # Schema validation + anti-hallucination
    # ------------------------------------------------------------------

    def _validate_schema(
        self,
        parsed: dict[str, Any],
        m10_audit_result: dict[str, Any],
        client_context: dict[str, Any],
    ) -> list[str]:
        errs: list[str] = []
        for k in _REQUIRED_TOP_KEYS:
            if k not in parsed:
                errs.append(f"falta clave '{k}'")
        if errs:
            return errs

        # --- PAC priorizado ---
        pac = parsed["pac_priorizado"]
        if not isinstance(pac, dict):
            errs.append("pac_priorizado no dict")
        else:
            fases = pac.get("fases")
            if not isinstance(fases, list):
                errs.append("pac_priorizado.fases no lista")
            elif not (3 <= len(fases) <= 5):
                errs.append(
                    f"pac_priorizado.fases debe tener 3-5 fases "
                    f"({len(fases)})"
                )
            else:
                seen_phase_nums: set[int] = set()
                seen_action_ids: set[str] = set()
                for i, f in enumerate(fases):
                    if not isinstance(f, dict):
                        errs.append(f"fases[{i}] no dict")
                        continue
                    fn = f.get("fase_num")
                    if not isinstance(fn, int):
                        errs.append(f"fases[{i}].fase_num no entero: {fn!r}")
                    else:
                        if fn in seen_phase_nums:
                            errs.append(f"fases[{i}].fase_num duplicado: {fn}")
                        if fn != i + 1:
                            errs.append(
                                f"fases[{i}].fase_num={fn} no consecutivo "
                                f"(esperado {i+1})"
                            )
                        seen_phase_nums.add(fn)
                    for fld in ("titulo", "periodo_semanas", "acciones", "objetivo_fase"):
                        if fld not in f:
                            errs.append(f"fases[{i}] falta {fld}")
                    acciones = f.get("acciones", [])
                    if not isinstance(acciones, list):
                        errs.append(f"fases[{i}].acciones no lista")
                    else:
                        for j, a in enumerate(acciones):
                            if not isinstance(a, dict):
                                errs.append(f"fases[{i}].acciones[{j}] no dict")
                                continue
                            for fld in (
                                "id", "nc_origen", "accion",
                                "responsable_sugerido", "esfuerzo_dias",
                                "evidencia_esperada", "prioridad",
                                "rationale_sector",
                            ):
                                if fld not in a:
                                    errs.append(
                                        f"fases[{i}].acciones[{j}] falta '{fld}'"
                                    )
                            if a.get("prioridad") not in _PRIORIDADES:
                                errs.append(
                                    f"fases[{i}].acciones[{j}].prioridad invalida: "
                                    f"{a.get('prioridad')!r}"
                                )
                            action_id = a.get("id")
                            if isinstance(action_id, str):
                                if action_id in seen_action_ids:
                                    errs.append(
                                        f"id accion duplicado: {action_id}"
                                    )
                                seen_action_ids.add(action_id)
                            esf = a.get("esfuerzo_dias")
                            if not isinstance(esf, (int, float)) or esf < 0:
                                errs.append(
                                    f"fases[{i}].acciones[{j}].esfuerzo_dias "
                                    f"invalido: {esf!r}"
                                )
            camino = pac.get("camino_critico")
            if camino is not None and not isinstance(camino, list):
                errs.append("pac_priorizado.camino_critico no lista")

        # --- Preguntas contextuales sector ---
        preguntas = parsed["preguntas_contextuales_sector"]
        sector = client_context.get("sector", "otro")
        if not isinstance(preguntas, list):
            errs.append("preguntas_contextuales_sector no lista")
        elif not (3 <= len(preguntas) <= 5):
            errs.append(
                f"preguntas_contextuales_sector debe tener 3-5 items "
                f"({len(preguntas)})"
            )
        else:
            at_least_one_sector = False
            for i, q in enumerate(preguntas):
                if not isinstance(q, dict):
                    errs.append(f"preguntas[{i}] no dict")
                    continue
                for fld in (
                    "codigo", "pregunta", "sector_aplicable",
                    "criterio_L5", "criterio_L0",
                    "evidencia_esperada", "rationale_sector",
                ):
                    if fld not in q:
                        errs.append(f"preguntas[{i}] falta {fld}")
                if q.get("sector_aplicable") == sector:
                    at_least_one_sector = True
                ev = q.get("evidencia_esperada")
                if not isinstance(ev, list):
                    errs.append(f"preguntas[{i}].evidencia_esperada no lista")
                elif len(ev) > 3:
                    errs.append(
                        f"preguntas[{i}].evidencia_esperada > 3 ({len(ev)})"
                    )
            if sector != "otro" and not at_least_one_sector:
                errs.append(
                    f"preguntas_contextuales_sector no incluye ninguna con "
                    f"sector_aplicable='{sector}' (cliente es {sector})"
                )

        # --- Narrativa ejecutiva ---
        narr = parsed["narrativa_ejecutiva"]
        if not isinstance(narr, dict):
            errs.append("narrativa_ejecutiva no dict")
        else:
            resumen = narr.get("resumen_markdown", "")
            if not isinstance(resumen, str) or len(resumen) < 300:
                errs.append(
                    f"narrativa.resumen_markdown muy corto "
                    f"({len(resumen) if isinstance(resumen, str) else 0} chars, min 300)"
                )
            elif len(resumen) > 5000:
                errs.append(
                    f"narrativa.resumen_markdown > 5000 chars ({len(resumen)})"
                )
            if narr.get("veredicto") not in _VEREDICTOS:
                errs.append(
                    f"narrativa.veredicto invalido: {narr.get('veredicto')!r}"
                )
            pct = narr.get("probabilidad_certificacion_primera")
            if not isinstance(pct, (int, float)) or not (0 <= pct <= 100):
                errs.append(
                    f"narrativa.probabilidad_certificacion_primera fuera [0,100]: {pct!r}"
                )
            tmin = narr.get("tiempo_minimo_estimado_semanas")
            if not isinstance(tmin, int) or tmin < 0:
                errs.append(
                    f"narrativa.tiempo_minimo_estimado_semanas invalido: {tmin!r}"
                )
            riesgos = narr.get("riesgos_principales")
            if not isinstance(riesgos, list):
                errs.append("narrativa.riesgos_principales no lista")
            elif len(riesgos) > 3:
                errs.append(
                    f"narrativa.riesgos_principales > 3 ({len(riesgos)})"
                )

        # --- Anti-hallucination: nc_origen DEBE venir del m10_audit_result ---
        errs.extend(self._detect_hallucinated_codes(parsed, m10_audit_result))

        return errs

    @staticmethod
    def _detect_hallucinated_codes(
        parsed: dict[str, Any],
        m10_audit_result: dict[str, Any],
    ) -> list[str]:
        """Los action.nc_origen DEBEN estar en m10_audit_result."""
        errs: list[str] = []
        known_codes: set[str] = set()
        for nc in (m10_audit_result.get("nc_mayores", []) or []):
            code = str(nc.get("codigo", "")).strip()
            if code:
                known_codes.add(code)
        for nc in (m10_audit_result.get("nc_menores", []) or []):
            code = str(nc.get("codigo", "")).strip()
            if code:
                known_codes.add(code)

        pac = parsed.get("pac_priorizado", {})
        if not isinstance(pac, dict):
            return errs
        for fase in pac.get("fases", []) or []:
            if not isinstance(fase, dict):
                continue
            for a in fase.get("acciones", []) or []:
                if not isinstance(a, dict):
                    continue
                nc_origen = str(a.get("nc_origen", "")).strip()
                if not nc_origen:
                    continue
                # "multiple" / "varios" / "general" / "n/a" son aceptables
                if nc_origen.lower() in ("multiple", "varios", "n/a", "general", ""):
                    continue
                if nc_origen not in known_codes:
                    errs.append(
                        f"hallucinated_nc_origen: accion.nc_origen='{nc_origen}' "
                        f"no esta en m10_audit_result (conocidos: "
                        f"{sorted(known_codes)[:5]}...)"
                    )
                    if len(errs) >= 5:
                        return errs
        return errs

    # ------------------------------------------------------------------
    # Fallback deterministico
    # ------------------------------------------------------------------

    def _deterministic_fallback(
        self,
        m10_audit_result: dict[str, Any],
        client_context: dict[str, Any],
    ) -> dict[str, Any]:
        nc_mayores = m10_audit_result.get("nc_mayores", []) or []
        nc_menores = m10_audit_result.get("nc_menores", []) or []
        score = m10_audit_result.get("score_conformidad", 0)
        sector = client_context.get("sector", "otro")

        acciones_f1: list[dict[str, Any]] = []
        for i, nc in enumerate(nc_mayores[:8]):
            code = nc.get("codigo", f"NC-{i}")
            acciones_f1.append({
                "id": f"PAC-F1-{i+1:03d}",
                "nc_origen": code,
                "accion": f"Cerrar NC mayor {code}: {nc.get('descripcion', '')}"[:200],
                "responsable_sugerido": "RSEG",
                "esfuerzo_dias": 5,
                "evidencia_esperada": "Documento actualizado + evidencia implantacion",
                "prioridad": "critica",
                "rationale_sector": (
                    "NC mayor bloquea certificacion. Prioridad maxima en todos los sectores."
                )[:200],
            })
        acciones_f2: list[dict[str, Any]] = []
        for i, nc in enumerate(nc_menores[:8]):
            code = nc.get("codigo", f"NC-{i}")
            acciones_f2.append({
                "id": f"PAC-F2-{i+1:03d}",
                "nc_origen": code,
                "accion": f"Corregir NC menor {code}: {nc.get('descripcion', '')}"[:200],
                "responsable_sugerido": "RSEG",
                "esfuerzo_dias": 2,
                "evidencia_esperada": "Evidencia correctiva + sign-off",
                "prioridad": "media",
                "rationale_sector": (
                    "NC menor no bloquea pero requiere correccion formal."
                )[:200],
            })

        fases = [
            {
                "fase_num": 1,
                "titulo": "Bloqueantes auditoria inmediata",
                "periodo_semanas": "0-4",
                "acciones": acciones_f1 or [
                    {
                        "id": "PAC-F1-001",
                        "nc_origen": "general",
                        "accion": "Sin NC mayores detectadas; confirmar alcance.",
                        "responsable_sugerido": "RSEG",
                        "esfuerzo_dias": 1,
                        "evidencia_esperada": "Acta de revision.",
                        "prioridad": "baja",
                        "rationale_sector": "Nada critico a cerrar.",
                    }
                ],
                "objetivo_fase": "Cerrar todas las NC mayores antes de auditoria externa.",
            },
            {
                "fase_num": 2,
                "titulo": "Correcciones NC menor y mejoras",
                "periodo_semanas": "4-8",
                "acciones": acciones_f2 or [
                    {
                        "id": "PAC-F2-001",
                        "nc_origen": "general",
                        "accion": "Consolidar evidencias de controles ya implantados.",
                        "responsable_sugerido": "RSEG",
                        "esfuerzo_dias": 3,
                        "evidencia_esperada": "Dossier consolidado.",
                        "prioridad": "media",
                        "rationale_sector": "Preparacion dossier auditor.",
                    }
                ],
                "objetivo_fase": "Cerrar NC menores y consolidar evidencias.",
            },
            {
                "fase_num": 3,
                "titulo": "Auditoria interna y certificacion",
                "periodo_semanas": "8-12",
                "acciones": [
                    {
                        "id": "PAC-F3-001",
                        "nc_origen": "general",
                        "accion": "Auditoria interna completa + revision dossier ENAC.",
                        "responsable_sugerido": "RSEG + Auditor externo",
                        "esfuerzo_dias": 5,
                        "evidencia_esperada": "Informe auditoria interna firmado.",
                        "prioridad": "alta",
                        "rationale_sector": "Pre-auditoria ENAC real.",
                    }
                ],
                "objetivo_fase": "Llegar a auditoria externa con dossier completo.",
            },
        ]

        preguntas_base = [
            {
                "codigo": "A11-GEN-001",
                "pregunta": "Como se gestiona el cese de relacion con proveedores criticos (eliminacion o devolucion de datos)?",
                "sector_aplicable": sector,
                "criterio_L5": "Procedimiento documentado + evidencia aplicada en caso real.",
                "criterio_L0": "Sin procedimiento ni evidencia.",
                "evidencia_esperada": [
                    "Clausula contractual",
                    "Log baja accesos",
                    "Acta devolucion/destruccion",
                ],
                "rationale_sector": "Auditor ENAC verifica cierres contractuales [RGPD art. 28].",
            },
            {
                "codigo": "A11-GEN-002",
                "pregunta": "Hay evidencia de revision periodica de accesos con cese de privilegios?",
                "sector_aplicable": sector,
                "criterio_L5": "Revision trimestral con logs + acta.",
                "criterio_L0": "Sin revision documentada.",
                "evidencia_esperada": [
                    "Log revisiones",
                    "Lista cambios aplicados",
                ],
                "rationale_sector": "op.acc requiere revision periodica documentada.",
            },
            {
                "codigo": "A11-GEN-003",
                "pregunta": "Se realiza simulacro de incidente con direccion involucrada?",
                "sector_aplicable": sector,
                "criterio_L5": "Simulacro anual con direccion + informe.",
                "criterio_L0": "Sin simulacro ni participacion directiva.",
                "evidencia_esperada": [
                    "Informe simulacro",
                    "Lista asistencia direccion",
                ],
                "rationale_sector": "Compromiso direccion se verifica en simulacro.",
            },
        ]

        if score >= 85 and not nc_mayores:
            veredicto = "listo_auditar"
            prob = 85
            tmin = 4
        elif score >= 65:
            veredicto = "listo_con_riesgos"
            prob = 60
            tmin = 8
        elif score >= 40:
            veredicto = "no_listo_plazo"
            prob = 30
            tmin = 16
        else:
            veredicto = "muy_lejos"
            prob = 10
            tmin = 26

        narrativa = (
            f"### Dry-run auditoria ENAC suplementario\n\n"
            f"Con un score de conformidad de {score}% y {len(nc_mayores)} no "
            f"conformidades mayores detectadas por M10, el cliente "
            f"{client_context.get('company_name', '')} se encuentra en estado "
            f"'{veredicto.replace('_', ' ')}'. Este analisis suplementario "
            f"complementa la evaluacion determinista de M10 (58 preguntas "
            f"ENAC) con un PAC priorizado y preguntas contextuales del "
            f"sector {sector}.\n\n"
            f"### Recomendacion\n\n"
            f"El plazo minimo estimado para llegar a auditoria externa ENAC "
            f"con razonables probabilidades es de {tmin} semanas, priorizando "
            f"el cierre de NC mayores en la Fase 1.\n\n"
            f"### Fallback\n\n"
            f"Este texto ha sido generado por el fallback determinista de "
            f"A11 al fallar la validacion schema del LLM. Revisar manualmente "
            f"antes de entregar al cliente."
        )

        return {
            "pac_priorizado": {
                "fases": fases,
                "camino_critico": [
                    a["id"] for a in acciones_f1[:3]
                ] or ["PAC-F1-001"],
            },
            "preguntas_contextuales_sector": preguntas_base[:3],
            "narrativa_ejecutiva": {
                "resumen_markdown": narrativa,
                "veredicto": veredicto,
                "probabilidad_certificacion_primera": prob,
                "tiempo_minimo_estimado_semanas": tmin,
                "riesgos_principales": [
                    "Fallback template: revisar manualmente antes de entregar.",
                    f"{len(nc_mayores)} NC mayores pendientes (criticas para certificacion).",
                ],
            },
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
            path = out_dir / f"a11_rejected_attempt_{attempt}_{short_id}.md"
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# A11 REJECTED - attempt {attempt}\n\n")
                f.write(f"- reason: {reason}\n")
                if errors:
                    f.write(f"- errors ({len(errors)}):\n")
                    for e in errors[:20]:
                        f.write(f"    - {e}\n")
                f.write("\n## RAW\n```\n")
                f.write(response.get("response", ""))
                f.write("\n```\n")
            logger.warning("A11 rejected draft saved to %s", path)
        except Exception as exc:
            logger.debug("A11 dump failed: %s", exc)

    def _build_result(
        self,
        *,
        audit: dict[str, Any],
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
            (tokens_in / 1_000_000) * _OPUS_47_USD_IN
            + (cache_creation / 1_000_000) * _OPUS_47_USD_CACHE_WRITE
            + (cache_read / 1_000_000) * _OPUS_47_USD_CACHE_READ
            + (tokens_out / 1_000_000) * _OPUS_47_USD_OUT
        ) * _USD_TO_EUR
        return {
            "audit": audit,
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
AuditorInternoVirtualAgent = Agent11AuditorVirtual
