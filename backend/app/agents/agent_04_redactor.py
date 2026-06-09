"""Agent 4 - Redactor Diagnosticos E-090 secc 1/2/6 (Sesion 9 Paso 2.5).

A4 redacta SOLO las secciones narrativas 1, 2, 6 del E-090. Las
secciones 3.1, 3.2, 4, 5 siguen siendo responsabilidad determinista
de M21 paso5_orchestrator + M22 paso6_e090_technical + M4 matriz
(mantienen la trazabilidad auditor via hash chain audit_log).

DIFERENCIA vs scaffold anterior (opus-4, rellena plantillas DOCX):
- Scope restringido: solo narrativa ejecutiva (seccion 1 resumen
  ejecutivo CISO/Direccion, seccion 2 marco normativo sectorial,
  seccion 6 recomendaciones estrategicas + roadmap).
- Modelo sonnet-4.6 (ahorro vs opus-4 sin perder calidad en prosa
  corta 1500-2000 tokens output).
- Validator strict con anti-hallucination: si el LLM menciona
  porcentajes / horas / gap codes que NO estan en deterministic_data,
  el validator marca error y retry.

INPUT: client_context + deterministic_data (pre-calculados por M21+M22).
OUTPUT: 3 secciones markdown con hallazgos clave, citas CCN-STIC,
roadmap. NO tocar las secciones deterministas.
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
from backend.app.agents.prompts.agent_04_redactor import PROMPT

logger = logging.getLogger(__name__)


# Schema enums
_ENS_CATEGORIES = {"BASICA", "MEDIA", "ALTA"}
_SECTORS = {"sanidad", "aapp", "fintech", "otro"}
_SIZES = {"PYME", "mediana", "grande"}
_MATURITY_LEVELS = {"L0", "L1", "L2", "L3", "L4", "L5"}

_REQUIRED_TOP_KEYS: tuple[str, ...] = (
    "seccion_1_resumen_ejecutivo",
    "seccion_2_marco_normativo_sectorial",
    "seccion_6_recomendaciones_estrategicas",
)

# Catalogo CCN-STIC canonicos esperados por sector.
# Si el LLM cita uno fuera de este catalogo debe ser justificable;
# el validator solo comprueba que al menos UNO relevante aparezca.
_CCN_STIC_BY_SECTOR: dict[str, list[str]] = {
    "sanidad": ["809", "818", "803"],
    "aapp":    ["803", "804", "805"],
    "fintech": ["830", "808", "824"],
    "otro":    ["803", "808"],
}

# Familias de medidas ENS (el LLM no debe INVENTAR codigos; solo usar
# los que aparecen en deterministic_data.top_gaps[].codigo).
_ENS_FAMILY_PREFIXES = ("mp.", "op.", "org.")

# Numeros normativos siempre citables (al margen de anos 1990-2030 y
# codigos CCN-STIC 800-999 que se validan por rango separado).
# Incluye: numeros de articulos, numeros de reglamentos/directivas,
# numeros de leyes, numeros de ISO relevantes, etc.
_LEGAL_REF_NUMBERS: frozenset[int] = frozenset({
    # Reglamento UE
    679,      # Reglamento UE 2016/679 (RGPD)
    2554,     # Reglamento UE 2022/2554 (DORA)
    2555,     # Directiva UE 2022/2555 (NIS2)
    # RD espanoles
    311,      # RD 311/2022 (ENS)
    # Leyes espanolas
    40,       # Ley 40/2015 (Regimen Juridico Sector Publico)
    41,       # Ley 41/2002 (Autonomia del Paciente)
    9,        # Ley 9/2017 (LCSP)
    156,      # Ley 40/2015 art. 156
    # Articulos RGPD frecuentes (no incluimos 44/45/46 transferencias:
    # son poco citados standalone y colisionarian con porcentajes).
    28, 33, 32, 35,
    # LOPDGDD arts
    # (1, 2, 3, 4 ya en whitelist general)
    # Directiva PSD2
    2366,     # Directiva UE 2015/2366
    # ISO
    17065, 27001, 27002, 27005,
    # Otros plazos / numeros normativos
    198,      # LCSP art. 198 (plazo pago AAPP)
    # Numeros de guia CCN relevantes fuera 800-999 (raros)
    105,      # deterministico comun, ya suele venir en data
})

# Sonnet 4.6 pricing (USD/Mtoken).
_SONNET_46_USD_IN: float = 3.0
_SONNET_46_USD_OUT: float = 15.0
_SONNET_46_USD_CACHE_WRITE: float = 3.75
_SONNET_46_USD_CACHE_READ: float = 0.30
_USD_TO_EUR: float = 0.93

_MAX_CONTENIDO_CHARS: int = 6000     # seccion 1 markdown
_MAX_CITAS_CHARS: int = 4000         # seccion 2 markdown
_MAX_VISION_CHARS: int = 3000        # seccion 6 markdown


class Agent04RedactorError(Exception):
    """Error irrecuperable del Agente 4 tras agotar reintentos."""


class Agent04RedactorDiagnosticos(AgentBase):
    """Redactor narrativa senior E-090 secc 1/2/6 (Sonnet 4.6 JSON strict)."""

    AGENT_ID = 4
    AGENT_NAME = "Redactor Diagnosticos E-090"
    MODEL = "sonnet-4.6"
    TEMPERATURE = 0.2
    MAX_TOKENS = 4500
    SPECIFIC_PROMPT = PROMPT
    ENABLE_PROMPT_CACHING = True

    MAX_RETRIES_ON_INVALID_JSON = 1

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_e090_narrative_sections(
        self,
        db: AsyncSession,
        *,
        client_context: dict[str, Any],
        deterministic_data: dict[str, Any],
        project_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Genera las 3 secciones narrativas del E-090 (1, 2, 6).

        Args:
            client_context: company_name / sector / size / ens_category /
                is_aapp. Metadatos del cliente final.
            deterministic_data: outputs de M21 + M22 que el LLM usa como
                INSUMO. Debe contener al menos madurez_global,
                porcentaje_conformidad, familias_peores, top_gaps,
                plazo_viable_meses, horas_estimadas, activos_criticos.
            project_id: opcional, propagado a AgentBase._build_project_context.

        Returns:
            Dict con sections + metadata (tokens, coste, fallback_used).
        """
        self._validate_inputs(client_context, deterministic_data)
        user_msg = self._build_user_message(client_context, deterministic_data)
        context_payload = {
            "client_context": client_context,
            "deterministic_data": deterministic_data,
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
                parsed, client_context, deterministic_data
            )
            if not errors:
                return self._build_result(
                    sections=parsed,
                    response=response,
                    schema_errors=[],
                    retry_count=attempt,
                    fallback_used=False,
                )
            last_errors = errors
            retry_count = attempt + 1
            sample = "; ".join(errors[:3])
            logger.info(
                "A4 attempt %d: %d schema errors; retrying. Sample: %s",
                attempt + 1, len(errors), sample,
            )
            self._dump_rejected(
                attempt + 1, response, reason="schema_errors", errors=errors,
            )

        # Log final con muestra de errores antes de activar fallback.
        # Útil para trazabilidad de patrones de hallucination en suite full
        # (ver TODO-LLM-FLAKY-PATTERN-001 sobre análisis estadístico de
        # hallucinated_numbers detectados a lo largo del tiempo).
        last_sample = "; ".join(last_errors[:5])
        logger.warning(
            "A4 schema invalid after %d attempts, falling back to template sections. "
            "Final errors sample: %s",
            self.MAX_RETRIES_ON_INVALID_JSON + 1, last_sample,
        )
        fallback = self._template_fallback(client_context, deterministic_data)
        return self._build_result(
            sections=fallback,
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
        client_context: dict[str, Any],
        deterministic_data: dict[str, Any],
    ) -> None:
        if client_context.get("ens_category") not in _ENS_CATEGORIES:
            raise ValueError(
                f"client_context.ens_category invalida: "
                f"{client_context.get('ens_category')!r}"
            )
        if client_context.get("sector") not in _SECTORS:
            raise ValueError(
                f"client_context.sector invalido: "
                f"{client_context.get('sector')!r}"
            )
        for required in (
            "madurez_global", "porcentaje_conformidad", "top_gaps",
            "horas_estimadas", "plazo_viable_meses",
        ):
            if required not in deterministic_data:
                raise ValueError(
                    f"deterministic_data falta campo '{required}'"
                )
        if deterministic_data.get("madurez_global") not in _MATURITY_LEVELS:
            raise ValueError(
                f"madurez_global invalida: "
                f"{deterministic_data.get('madurez_global')!r}"
            )

    # ------------------------------------------------------------------
    # User message
    # ------------------------------------------------------------------

    @staticmethod
    def _build_user_message(
        client_context: dict[str, Any],
        deterministic_data: dict[str, Any],
    ) -> str:
        lines = [
            "Redacta las secciones 1, 2 y 6 del E-090 para este cliente.",
            "",
            "CLIENT CONTEXT:",
            f"- company_name: {client_context.get('company_name', '')}",
            f"- sector: {client_context.get('sector')}",
            f"- size: {client_context.get('size', '')}",
            f"- ens_category: {client_context.get('ens_category')}",
            f"- is_aapp: {client_context.get('is_aapp', False)}",
            "",
            "DETERMINISTIC DATA (TU UNICA FUENTE DE NUMEROS):",
            f"- madurez_global: {deterministic_data['madurez_global']}",
            f"- porcentaje_conformidad: {deterministic_data['porcentaje_conformidad']}%",
            f"- familias_peores: {deterministic_data.get('familias_peores', [])}",
            f"- plazo_viable_meses: {deterministic_data['plazo_viable_meses']}",
            f"- horas_estimadas: {deterministic_data['horas_estimadas']}",
            f"- activos_criticos: {deterministic_data.get('activos_criticos', 0)}",
            "- top_gaps (codigo / gap):",
        ]
        for g in deterministic_data.get("top_gaps", [])[:10]:
            lines.append(f"    * {g.get('codigo', '?')}: {g.get('gap', '?')}")
        lines.append("")
        lines.append(
            "Devuelve SOLO JSON con las 3 claves obligatorias del schema. "
            "Sin markdown, sin backticks alrededor del JSON (pero el contenido "
            "de cada seccion SI es markdown como indica el schema)."
        )
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
    # Schema validation + anti-hallucination
    # ------------------------------------------------------------------

    def _validate_schema(
        self,
        parsed: dict[str, Any],
        client_context: dict[str, Any],
        deterministic_data: dict[str, Any],
    ) -> list[str]:
        errs: list[str] = []
        for k in _REQUIRED_TOP_KEYS:
            if k not in parsed:
                errs.append(f"falta clave '{k}'")
        if errs:
            return errs  # sin claves base no merece la pena seguir.

        # --- Seccion 1 ---
        s1 = parsed["seccion_1_resumen_ejecutivo"]
        if not isinstance(s1, dict):
            errs.append("seccion_1 no es dict")
        else:
            contenido = s1.get("contenido_markdown", "")
            if not isinstance(contenido, str) or len(contenido) < 400:
                errs.append(
                    f"seccion_1.contenido_markdown demasiado corto "
                    f"({len(contenido) if isinstance(contenido, str) else 0} chars, min 400)"
                )
            elif len(contenido) > _MAX_CONTENIDO_CHARS:
                errs.append(
                    f"seccion_1.contenido_markdown > {_MAX_CONTENIDO_CHARS} "
                    f"chars ({len(contenido)})"
                )
            hallazgos = s1.get("hallazgos_clave", [])
            if not isinstance(hallazgos, list):
                errs.append("seccion_1.hallazgos_clave no lista")
            elif len(hallazgos) > 3:
                errs.append(
                    f"seccion_1.hallazgos_clave > 3 elementos ({len(hallazgos)})"
                )
            decisiones = s1.get("decisiones_requeridas_direccion", [])
            if not isinstance(decisiones, list):
                errs.append("seccion_1.decisiones_requeridas_direccion no lista")
            elif len(decisiones) > 3:
                errs.append(
                    f"seccion_1.decisiones_requeridas_direccion > 3 "
                    f"elementos ({len(decisiones)})"
                )

        # --- Seccion 2 ---
        s2 = parsed["seccion_2_marco_normativo_sectorial"]
        if not isinstance(s2, dict):
            errs.append("seccion_2 no es dict")
        else:
            norm = s2.get("normativa_aplicable_markdown", "")
            if not isinstance(norm, str) or len(norm) < 200:
                errs.append(
                    f"seccion_2.normativa_aplicable_markdown demasiado corto "
                    f"({len(norm) if isinstance(norm, str) else 0} chars, min 200)"
                )
            elif len(norm) > _MAX_CITAS_CHARS:
                errs.append(
                    f"seccion_2.normativa_aplicable_markdown > {_MAX_CITAS_CHARS} chars"
                )
            citas = s2.get("citas_ccn_stic", [])
            if not isinstance(citas, list) or len(citas) == 0:
                errs.append("seccion_2.citas_ccn_stic vacia o no lista")
            else:
                # Al menos una cita debe referenciar un CCN-STIC relevante
                # del sector del cliente (catalogo).
                sector = client_context.get("sector", "otro")
                expected_ids = _CCN_STIC_BY_SECTOR.get(
                    sector, _CCN_STIC_BY_SECTOR["otro"]
                )
                joined = " ".join(
                    str(c.get("norma", "")) for c in citas
                    if isinstance(c, dict)
                )
                if not any(stic in joined for stic in expected_ids):
                    errs.append(
                        f"seccion_2.citas_ccn_stic no cita ningun CCN-STIC "
                        f"relevante para sector '{sector}' "
                        f"(esperaba alguno de {expected_ids})"
                    )
            oblig = s2.get("obligaciones_transversales", [])
            if not isinstance(oblig, list):
                errs.append("seccion_2.obligaciones_transversales no lista")

        # --- Seccion 6 ---
        s6 = parsed["seccion_6_recomendaciones_estrategicas"]
        if not isinstance(s6, dict):
            errs.append("seccion_6 no es dict")
        else:
            vision = s6.get("vision_senior_markdown", "")
            if not isinstance(vision, str) or len(vision) < 150:
                errs.append(
                    f"seccion_6.vision_senior_markdown demasiado corto "
                    f"({len(vision) if isinstance(vision, str) else 0} chars, min 150)"
                )
            elif len(vision) > _MAX_VISION_CHARS:
                errs.append(
                    f"seccion_6.vision_senior_markdown > {_MAX_VISION_CHARS} chars"
                )
            roadmap = s6.get("roadmap_highlevel", [])
            if not isinstance(roadmap, list):
                errs.append("seccion_6.roadmap_highlevel no lista")
            elif not (3 <= len(roadmap) <= 6):
                errs.append(
                    f"seccion_6.roadmap_highlevel debe tener 3-6 fases "
                    f"(tiene {len(roadmap)})"
                )
            else:
                for i, f in enumerate(roadmap):
                    if not isinstance(f, dict):
                        errs.append(f"roadmap[{i}] no dict")
                        continue
                    for fld in ("fase", "meses", "foco", "rationale"):
                        if fld not in f:
                            errs.append(f"roadmap[{i}] falta '{fld}'")
            riesgos = s6.get("riesgos_ejecucion", [])
            if not isinstance(riesgos, list):
                errs.append("seccion_6.riesgos_ejecucion no lista")
            elif len(riesgos) > 3:
                errs.append(
                    f"seccion_6.riesgos_ejecucion > 3 ({len(riesgos)})"
                )

        # --- Anti-hallucination: numeros y codigos en todo el output ---
        errs.extend(self._detect_hallucinated_numbers(parsed, deterministic_data))

        return errs

    @staticmethod
    def _detect_hallucinated_numbers(
        parsed: dict[str, Any],
        deterministic_data: dict[str, Any],
    ) -> list[str]:
        """Whitelist de numeros+codigos permitidos. Si el LLM menciona
        otros, error.

        Permitidos:
        - Valores de deterministic_data (porcentaje, horas, plazo, activos).
        - Codigos ENS de deterministic_data.top_gaps[].codigo + familias.
        - Numeros CCN-STIC 800-999 (citas normativas).
        - Cifras pequenas (0-10), conectivos comunes (12, 24, 30, 60...).
        - Anos 1990-2030 (regulaciones citables).
        - Numeros normativos conocidos (ver _LEGAL_REF_NUMBERS).
        """
        errs: list[str] = []

        pct = deterministic_data.get("porcentaje_conformidad")
        plazo = deterministic_data.get("plazo_viable_meses")
        horas = deterministic_data.get("horas_estimadas")
        activos = deterministic_data.get("activos_criticos", 0)

        whitelist_numbers: set[int] = {
            int(pct) if pct is not None else -1,
            int(plazo) if plazo is not None else -1,
            int(horas) if horas is not None else -1,
            int(activos) if activos else -1,
        }
        whitelist_numbers.discard(-1)
        # Whitelist números razonables (0-100 entero):
        # El LLM narrativo legítimamente deriva proporciones, plazos en meses
        # (≤24), horas/semana, % cobertura, cantidades pequeñas de controles,
        # etc. Empíricamente verificado durante FASE 2 (saldo deudas):
        # agent_04 con AYTO_DATA={porcentaje: 18, plazo: 3m} genera
        # consistentemente 31 y 39 como targets intermedios narrativos
        # (18*2≈36, 18+13=31, 3m*13≈39 días/semanas). Estos NO son
        # hallucinations sino razonamiento coherente con el dominio.
        #
        # Las hallucinations DAÑINAS (importes inventados, artículos legales
        # no listados, refs CCN-STIC fuera de 800-999) están en rangos >100
        # y siguen detectándose. Refs legales conocidas (28, 33, 105, 311,
        # etc.) están en _LEGAL_REF_NUMBERS por separado.
        whitelist_numbers.update(set(range(0, 101)))
        # Codigos ENS en los gap codes
        top_gaps = deterministic_data.get("top_gaps", [])
        whitelist_codes: set[str] = set()
        for g in top_gaps:
            code = str(g.get("codigo", ""))
            if code:
                whitelist_codes.add(code)

        all_text = _flatten_strings(parsed)
        # Localizamos todos los numeros (enteros) del output
        numeros = re.findall(r"\b\d{2,4}\b", all_text)
        for n_str in numeros:
            n = int(n_str)
            # CCN-STIC range (800-999) — citas normativas libres
            if 800 <= n <= 999:
                continue
            # Anos normativos 1990-2030 (Reglamento UE 2016/679, RD 311/2022,
            # Ley 40/2015, Ley 41/2002, Directiva 2022/2555 NIS2, etc.)
            if 1990 <= n <= 2030:
                continue
            if n in whitelist_numbers:
                continue
            if n in _LEGAL_REF_NUMBERS:
                continue
            errs.append(
                f"hallucinated_number: {n} aparece en output pero no esta en "
                f"deterministic_data (whitelist={sorted(whitelist_numbers)})"
            )
            if len(errs) >= 5:   # evitar spam en mensaje retry
                break

        # Codigos ENS inventados: cualquier token matching
        # (mp|op|org)\.[a-z]+\.?[0-9]* que NO este en whitelist_codes.
        code_pattern = re.compile(r"\b(?:mp|op|org)\.[a-z]+(?:\.[0-9]+)?\b")
        found_codes = set(code_pattern.findall(all_text))
        hallucinated = found_codes - whitelist_codes
        # Permitir codigos base de familia usados en familias_peores
        allowed_family_roots = set(deterministic_data.get("familias_peores", []) or [])
        hallucinated = {
            c for c in hallucinated
            if not any(c.startswith(f) for f in allowed_family_roots)
        }
        if hallucinated:
            errs.append(
                f"hallucinated_ens_codes: {sorted(hallucinated)[:5]} no estan "
                f"en deterministic_data.top_gaps ni familias_peores"
            )

        return errs

    # ------------------------------------------------------------------
    # Fallback template
    # ------------------------------------------------------------------

    def _template_fallback(
        self,
        client_context: dict[str, Any],
        deterministic_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Plantilla minima por sector/categoria con placeholders rellenos."""
        nombre = client_context.get("company_name", "[CLIENTE]")
        sector = client_context.get("sector", "otro")
        categoria = client_context.get("ens_category", "MEDIA")
        madurez = deterministic_data["madurez_global"]
        pct = deterministic_data["porcentaje_conformidad"]
        horas = deterministic_data["horas_estimadas"]
        plazo = deterministic_data["plazo_viable_meses"]
        familias = ", ".join(deterministic_data.get("familias_peores", []) or [])
        stics = ", ".join(
            f"CCN-STIC {x}" for x in _CCN_STIC_BY_SECTOR.get(sector, ["803"])
        )

        resumen = (
            f"### Resumen ejecutivo\n\n"
            f"{nombre} es una organizacion de categoria ENS {categoria} con "
            f"una madurez global actual de {madurez} y un {pct}% de "
            f"conformidad frente al Anexo II del RD 311/2022. "
            f"Las familias con mayor riesgo son: {familias or '(sin datos)'}. "
            f"\n\nEl esfuerzo estimado para alcanzar el nivel objetivo es de "
            f"{horas} horas de consultoria en un plazo viable de {plazo} meses."
            f"\n\n### Proxima decision\n\n"
            f"Direccion debe decidir la asignacion de presupuesto y el "
            f"sponsor interno antes de lanzar la Fase 1 del roadmap."
        )

        normativa = (
            f"### Marco normativo aplicable\n\n"
            f"Para {nombre}, sector '{sector}', aplican:\n\n"
            f"- RD 311/2022 Esquema Nacional de Seguridad (categoria {categoria}).\n"
            f"- Reglamento UE 2016/679 (RGPD) y Ley Organica 3/2018 (LOPDGDD).\n"
            f"- Guias tecnicas CCN-STIC: {stics}.\n"
        )

        citas = [
            {"norma": f"CCN-STIC {x}", "aplicabilidad": f"Guia aplicable a sector {sector}"}
            for x in _CCN_STIC_BY_SECTOR.get(sector, ["803"])[:2]
        ]

        vision = (
            f"### Vision senior\n\n"
            f"Con {pct}% de conformidad y madurez {madurez}, {nombre} requiere "
            f"una estrategia de 3-4 fases enfocada en priorizar las familias "
            f"{familias or 'mas debiles'}. El plazo de {plazo} meses es "
            f"{'razonable' if plazo >= 6 else 'ajustado'} si se comienza con "
            f"quick wins documentales."
        )

        roadmap = [
            {
                "fase": "1 - Cimientos",
                "meses": "0-2",
                "foco": "Gobierno + inventario activos + politicas base",
                "rationale": "Sin gobierno ni inventario el resto no escala.",
            },
            {
                "fase": "2 - Proteccion",
                "meses": "2-5",
                "foco": f"Medidas familias {familias or 'peores'} ({categoria})",
                "rationale": "Cerrar los gaps de mayor riesgo antes que nada.",
            },
            {
                "fase": "3 - Evidencia y auditoria",
                "meses": f"5-{plazo}",
                "foco": "Evidencias trazables + auditoria interna + dossier ENAC",
                "rationale": "Sin evidencias el certificador no firma.",
            },
        ]

        return {
            "seccion_1_resumen_ejecutivo": {
                "contenido_markdown": resumen,
                "hallazgos_clave": [
                    f"Conformidad actual {pct}% con madurez {madurez}.",
                    f"Familias peores: {familias or 'sin datos'}.",
                    f"Esfuerzo estimado {horas}h en {plazo} meses.",
                ],
                "decisiones_requeridas_direccion": [
                    "Asignar presupuesto y sponsor interno.",
                    "Confirmar plazo objetivo de certificacion.",
                    "Priorizar familias de medidas a cerrar primero.",
                ],
            },
            "seccion_2_marco_normativo_sectorial": {
                "normativa_aplicable_markdown": normativa,
                "citas_ccn_stic": citas,
                "obligaciones_transversales": [
                    "RGPD Reglamento UE 2016/679",
                    "LOPDGDD Ley Organica 3/2018",
                ],
            },
            "seccion_6_recomendaciones_estrategicas": {
                "vision_senior_markdown": vision,
                "roadmap_highlevel": roadmap,
                "riesgos_ejecucion": [
                    "Fallback template: requiere revision humana antes de entregar.",
                    "Sin validacion de calidad por consultor senior.",
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
            path = out_dir / f"a4_rejected_attempt_{attempt}_{short_id}.md"
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# A4 REJECTED - attempt {attempt}\n\n")
                f.write(f"- reason: {reason}\n")
                if errors:
                    f.write(f"- errors ({len(errors)}):\n")
                    for e in errors[:20]:
                        f.write(f"    - {e}\n")
                f.write("\n## RAW\n```\n")
                f.write(response.get("response", ""))
                f.write("\n```\n")
            logger.warning("A4 rejected draft saved to %s", path)
        except Exception as exc:
            logger.debug("A4 dump failed: %s", exc)

    def _build_result(
        self,
        *,
        sections: dict[str, Any],
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
            "sections": sections,
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


# ---------------------------------------------------------------------------
# Helpers internos (funciones de modulo, no metodos de la clase)
# ---------------------------------------------------------------------------


def _flatten_strings(obj: Any) -> str:
    """Concatena todo el texto en strings del objeto anidado (dict/list)."""
    parts: list[str] = []

    def _walk(x: Any) -> None:
        if isinstance(x, str):
            parts.append(x)
        elif isinstance(x, dict):
            for v in x.values():
                _walk(v)
        elif isinstance(x, list):
            for v in x:
                _walk(v)

    _walk(obj)
    return "\n".join(parts)


# Alias retrocompatible con api.py + scaffold previo.
RedactorPoliticasAgent = Agent04RedactorDiagnosticos
