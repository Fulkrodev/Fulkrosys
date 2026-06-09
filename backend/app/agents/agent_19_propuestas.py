"""Agent 19 — Redactor de Propuestas (Sesion 9 Paso 1).

Convierte un proyecto + pricing determinista en un draft P-001 con calidad
senior-expert usando Claude Opus 4.7 (1M ctx, 16k output tokens).

Principio: el agente SOLO redacta narrativa. Los importes, hitos, plazos y
decisiones legales (AAPP vs privado) vienen 100% de PricingCalculator y
core/legal.is_aapp. Si el output del LLM contiene numeros que NO aparecen
en el pricing determinista, la respuesta se rechaza y se reintenta
(max 2). Si tras los reintentos sigue alucinando, se devuelve fallback
determinista.
"""
from __future__ import annotations

import logging
import os
import pathlib
import re
import uuid
from dataclasses import asdict, is_dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.base import AgentBase
from backend.app.agents.prompts.agent_19_propuestas import PROMPT
from backend.app.core.legal import is_aapp, is_aapp_by_fields
from backend.app.core.pricing import PricingCalculator
from backend.app.core.pricing.calculator import ImplantacionPricing

logger = logging.getLogger(__name__)


# Claves JSON obligatorias del output del LLM. Validamos presencia estricta.
REQUIRED_SECTIONS: tuple[str, ...] = (
    "resumen_ejecutivo",
    "alcance_proyecto",
    "metodologia_10_fases",
    "cronograma_textual",
    "justificacion_extras",
    "pricing_desglose",
    "hitos_pago",
    "garantias",
    "proximos_pasos",
    "referencias_legales",
)


# Pricing input blended per claude-opus-4-7[1m]:
#   input  USD/Mtoken, output USD/Mtoken, EUR/USD ~ 0.93
# Se usa solo para el log informativo de coste estimado; no afecta facturacion real.
_OPUS_47_USD_PER_MTOKEN_INPUT: float = 15.0
_OPUS_47_USD_PER_MTOKEN_OUTPUT: float = 75.0
_USD_TO_EUR: float = 0.93


class Agent19ProposalError(Exception):
    """Error irrecuperable del Agente 19 tras agotar reintentos."""


class Agent19Proposals(AgentBase):
    """Agente 19: redactor de propuestas P-001 con LLM real (Opus 4.7)."""

    AGENT_ID = 19
    AGENT_NAME = "Redactor de Propuestas"
    MODEL = "opus-4.7"
    TEMPERATURE = 0.15
    MAX_TOKENS = 16000
    SPECIFIC_PROMPT = PROMPT
    # Caching activado (FASE B Path A · 2026-05-23): system prompt
    # ~3-4k tokens (PROMPT 73 LOC + COMMON_HEADER) reusable en cascada
    # retry (MAX_RETRIES_ON_HALLUCINATION=1 · 2 calls back-to-back con
    # MISMO system prompt cuando hallucinate numérico) + sesiones Marcos
    # redactando propuestas varios leads en una tarde. Ephemeral TTL 5 min.
    ENABLE_PROMPT_CACHING = True

    MAX_RETRIES_ON_HALLUCINATION = 1

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_proposal(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        sistemas_en_alcance: int | None = None,
        sedes: int | None = None,
        madurez_pct: int | None = None,
        dias_hasta_plazo: int | None = None,
        sector_override: str | None = None,
        categoria_override: str | None = None,
        retainer_tier: str | None = None,
    ) -> dict[str, Any]:
        """Genera el draft P-001 completo para un proyecto dado.

        Devuelve un dict con la estructura:
            {
              "proposal_draft": {secciones_dict},
              "pricing_snapshot": {...},
              "is_aapp": bool,
              "validation": {"numbers_ok": bool, "unknown_amounts": [...], "retry_count": int},
              "tokens_input": int,
              "tokens_output": int,
              "cost_eur_estimated": float,
              "latency_ms": int,
              "model": str,
              "fallback_used": bool,
            }
        """
        # 1. Recolectar contexto proyecto + cliente + M1/M21/M22
        context = await self._build_full_context(
            db,
            project_id=project_id,
            sistemas_en_alcance=sistemas_en_alcance,
            sedes=sedes,
            madurez_pct=madurez_pct,
            dias_hasta_plazo=dias_hasta_plazo,
            sector_override=sector_override,
            categoria_override=categoria_override,
            retainer_tier=retainer_tier,
        )

        # 2. Calcular pricing deterministico
        pricing = context["pricing"]
        known_amounts = self._build_known_amounts(pricing, context)

        # 3. Llamar al LLM con retry en caso de alucinacion numerica
        retry_count = 0
        last_unknowns: list[str] = []
        last_response: dict[str, Any] = {}
        for attempt in range(self.MAX_RETRIES_ON_HALLUCINATION + 1):
            response = await self.invoke(
                db,
                project_id=project_id,
                user_message=self._user_message(context, retry_hint=last_unknowns if attempt > 0 else None),
                context=self._public_context_for_prompt(context),
                structured_output=True,
            )
            last_response = response
            parsed = response.get("parsed")
            if not isinstance(parsed, dict):
                last_unknowns = ["<output no es JSON valido con 10 claves requeridas>"]
                retry_count = attempt + 1
                self._dump_rejected_draft(
                    attempt + 1, response, reason="json_invalid",
                )
                continue
            if not all(k in parsed for k in REQUIRED_SECTIONS):
                missing = [k for k in REQUIRED_SECTIONS if k not in parsed]
                last_unknowns = [f"<faltan claves obligatorias: {missing}>"]
                retry_count = attempt + 1
                self._dump_rejected_draft(
                    attempt + 1, response, reason=f"missing_keys={missing}",
                )
                continue
            unknowns = self._detect_unknown_numbers_v2(parsed, known_amounts)
            if not unknowns:
                return self._build_result(
                    proposal_draft=parsed,
                    context=context,
                    response=response,
                    retry_count=attempt,
                    unknowns=[],
                    fallback_used=False,
                )
            last_unknowns = unknowns
            retry_count = attempt + 1
            logger.info(
                "A19 attempt %d: %d unknown numbers detected; retrying",
                attempt + 1, len(unknowns),
            )
            self._dump_rejected_draft(
                attempt + 1, response, reason="unknown_numbers", unknowns=unknowns,
            )

        # 4. Agotados reintentos: fallback determinista
        logger.warning(
            "A19 hallucinated numbers after %d attempts, falling back to deterministic narrative",
            self.MAX_RETRIES_ON_HALLUCINATION + 1,
        )
        fallback_draft = self._deterministic_fallback(context)
        return self._build_result(
            proposal_draft=fallback_draft,
            context=context,
            response=last_response,
            retry_count=retry_count,
            unknowns=last_unknowns,
            fallback_used=True,
        )

    # ------------------------------------------------------------------
    # Debug: dump drafts rechazados a /tmp para inspeccion humana
    # ------------------------------------------------------------------

    def _dump_rejected_draft(
        self,
        attempt: int,
        response: dict[str, Any],
        *,
        reason: str,
        unknowns: list[str] | None = None,
    ) -> None:
        """Guarda un draft rechazado en /tmp para inspeccion. Best-effort,
        opt-in via env var ``FULKRO_AGENT_DEBUG_DUMPS`` (off en produccion
        por defecto).

        Se activa siempre que un intento del LLM se rechace por:
        - JSON invalido
        - Faltan claves obligatorias
        - Numeros no-whitelist (alucinacion)
        """
        if not os.environ.get("FULKRO_AGENT_DEBUG_DUMPS"):
            return
        try:
            import uuid as _uuid
            out_dir = pathlib.Path("/tmp")
            short_id = _uuid.uuid4().hex[:8]
            path = out_dir / f"a19_rejected_attempt_{attempt}_{short_id}.md"
            raw = response.get("response") or ""
            tokens_in = response.get("tokens_input", 0)
            tokens_out = response.get("tokens_output", 0)
            model = response.get("model", self.MODEL)
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# A19 REJECTED DRAFT — attempt {attempt}\n\n")
                f.write(f"- reason: {reason}\n")
                f.write(f"- model: {model}\n")
                f.write(f"- tokens_in / out: {tokens_in} / {tokens_out}\n")
                f.write(f"- latency_ms: {response.get('latency_ms', 0)}\n")
                if unknowns:
                    f.write(f"- unknowns ({len(unknowns)}):\n")
                    for u in unknowns[:50]:
                        f.write(f"    - {u}\n")
                f.write("\n---\n\n")
                f.write("## RAW LLM RESPONSE\n\n")
                f.write("```\n")
                f.write(raw)
                f.write("\n```\n")
            logger.warning("A19 rejected draft saved to %s", path)
        except Exception as exc:
            logger.debug("A19 dump rejected failed: %s", exc)

    # ------------------------------------------------------------------
    # Context builder
    # ------------------------------------------------------------------

    async def _build_full_context(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
        sistemas_en_alcance: int | None,
        sedes: int | None,
        madurez_pct: int | None,
        dias_hasta_plazo: int | None,
        sector_override: str | None,
        categoria_override: str | None,
        retainer_tier: str | None,
    ) -> dict[str, Any]:
        project_row = (
            await db.execute(
                sql_text(
                    "SELECT id, nombre, client_id, categoria_objetivo, fase, estado "
                    "FROM projects WHERE id = :pid"
                ),
                {"pid": str(project_id)},
            )
        ).fetchone()
        if not project_row:
            raise Agent19ProposalError(f"Proyecto {project_id} no encontrado")

        client_ctx = await self._fetch_client(db, client_id=project_row[2])
        m1_ctx = await self._fetch_m1_categorization(db, project_id=project_id)
        m21_ctx = await self._fetch_m21_stakeholders(db, project_id=project_id)
        m22_ctx = await self._fetch_m22_discovery(db, project_id=project_id)

        sector = (
            sector_override
            or client_ctx.get("sector")
            or m21_ctx.get("sector")
        )
        categoria = (
            categoria_override
            or project_row[3]
            or m1_ctx.get("categoria")
            or "MEDIA"
        )

        # Resolucion de sistemas/sedes si no vienen en args
        eff_sistemas = (
            sistemas_en_alcance
            if sistemas_en_alcance is not None
            else max(int(m22_ctx.get("sistemas_count", 1) or 1), 1)
        )
        eff_sedes = (
            sedes
            if sedes is not None
            else max(int(m22_ctx.get("sedes_count", 1) or 1), 1)
        )
        eff_madurez = (
            madurez_pct
            if madurez_pct is not None
            else m21_ctx.get("madurez_pct")
        )

        calc = PricingCalculator()
        pricing = calc.calculate_implantacion(
            categoria,
            cliente=client_ctx,
            sector=sector,
            sistemas_en_alcance=eff_sistemas,
            sedes=eff_sedes,
            madurez_pct=eff_madurez,
            dias_hasta_plazo=dias_hasta_plazo,
        )

        retainer = None
        if retainer_tier:
            try:
                retainer = calc.calculate_retainer(
                    retainer_tier,
                    sector_regulado=bool(client_ctx.get("sector_regulado")),
                )
            except Exception as exc:
                logger.debug("A19: retainer calc failed for tier %s: %s", retainer_tier, exc)

        # AAPP detection: re-evaluate even if client obj lacks fields
        aapp_flag = is_aapp(client_ctx) or is_aapp_by_fields(
            cif=client_ctx.get("cif"),
            tipo_organizacion=client_ctx.get("tipo_organizacion"),
            razon_social=client_ctx.get("razon_social") or client_ctx.get("nombre"),
        )

        return {
            "project_id": str(project_id),
            "project_nombre": project_row[1],
            "project_fase": project_row[4],
            "project_estado": project_row[5],
            "categoria": pricing.categoria,
            "client": client_ctx,
            "sector": sector,
            "is_aapp": aapp_flag,
            "m1": m1_ctx,
            "m21": m21_ctx,
            "m22": m22_ctx,
            "sistemas_en_alcance": eff_sistemas,
            "sedes": eff_sedes,
            "madurez_pct": eff_madurez,
            "dias_hasta_plazo": dias_hasta_plazo,
            "pricing": pricing,
            "retainer": retainer,
        }

    async def _fetch_client(
        self, db: AsyncSession, client_id: uuid.UUID | str | None
    ) -> dict[str, Any]:
        if not client_id:
            return {}
        try:
            row = (
                await db.execute(
                    sql_text(
                        "SELECT id, nombre, cif, sector, provincia "
                        "FROM clients WHERE id = :cid"
                    ),
                    {"cid": str(client_id)},
                )
            ).fetchone()
        except Exception as exc:
            logger.debug("A19: client fetch failed: %s", exc)
            return {"id": str(client_id)}
        if not row:
            return {"id": str(client_id)}
        # tipo_organizacion no existe en el schema actual; se deriva de nombre
        # (is_aapp usa nombre como razon_social fallback).
        return {
            "id": str(row[0]),
            "nombre": row[1],
            "cif": row[2],
            "sector": row[3],
            "provincia": row[4],
            "razon_social": row[1],
            "tipo_organizacion": None,
        }

    async def _fetch_m1_categorization(
        self, db: AsyncSession, project_id: uuid.UUID
    ) -> dict[str, Any]:
        try:
            row = (
                await db.execute(
                    sql_text(
                        "SELECT categoria_final, score_d, score_i, score_c, score_a, score_t "
                        "FROM categorization_results "
                        "WHERE project_id = :pid "
                        "ORDER BY created_at DESC LIMIT 1"
                    ),
                    {"pid": str(project_id)},
                )
            ).fetchone()
        except Exception as exc:
            logger.debug("A19: M1 fetch failed: %s", exc)
            return {}
        if not row:
            return {}
        return {
            "categoria": row[0],
            "dimensiones": {
                "D": row[1], "I": row[2], "C": row[3], "A": row[4], "T": row[5],
            },
        }

    async def _fetch_m21_stakeholders(
        self, db: AsyncSession, project_id: uuid.UUID
    ) -> dict[str, Any]:
        try:
            rows = (
                await db.execute(
                    sql_text(
                        "SELECT COUNT(*), "
                        "COUNT(*) FILTER (WHERE rol_mapeado IS NOT NULL) "
                        "FROM stakeholders WHERE project_id = :pid"
                    ),
                    {"pid": str(project_id)},
                )
            ).fetchone()
        except Exception as exc:
            logger.debug("A21: stakeholders fetch failed: %s", exc)
            rows = (0, 0)
        try:
            diag = (
                await db.execute(
                    sql_text(
                        "SELECT madurez_pct, sector, empleados_total "
                        "FROM organizational_diagnoses "
                        "WHERE project_id = :pid "
                        "ORDER BY created_at DESC LIMIT 1"
                    ),
                    {"pid": str(project_id)},
                )
            ).fetchone()
        except Exception:
            diag = None
        return {
            "stakeholders_count": int(rows[0] or 0),
            "stakeholders_mapeados": int(rows[1] or 0),
            "madurez_pct": int(diag[0]) if diag and diag[0] is not None else None,
            "sector": diag[1] if diag else None,
            "empleados": int(diag[2]) if diag and diag[2] is not None else None,
        }

    async def _fetch_m22_discovery(
        self, db: AsyncSession, project_id: uuid.UUID
    ) -> dict[str, Any]:
        counts: dict[str, int] = {}
        queries = [
            ("sistemas_count", "SELECT COUNT(*) FROM discovered_assets WHERE project_id = :pid"),
            ("dataflows_count", "SELECT COUNT(*) FROM data_flow_diagrams WHERE project_id = :pid"),
            ("vulns_count", "SELECT COUNT(*) FROM vulnerability_inventory WHERE project_id = :pid"),
        ]
        for key, sql in queries:
            try:
                value = (
                    await db.execute(sql_text(sql), {"pid": str(project_id)})
                ).scalar()
                counts[key] = int(value or 0)
            except Exception as exc:
                logger.debug("A22: %s fetch failed: %s", key, exc)
                counts[key] = 0
        # sedes_count no siempre existe; default 1
        try:
            sedes = (
                await db.execute(
                    sql_text(
                        "SELECT COUNT(DISTINCT location) FROM discovered_assets "
                        "WHERE project_id = :pid AND location IS NOT NULL"
                    ),
                    {"pid": str(project_id)},
                )
            ).scalar() or 1
        except Exception:
            sedes = 1
        counts["sedes_count"] = int(sedes or 1)
        return counts

    # ------------------------------------------------------------------
    # Prompt context serialization
    # ------------------------------------------------------------------

    def _user_message(
        self, context: dict[str, Any], retry_hint: list[str] | None = None
    ) -> str:
        base = (
            "Genera el draft P-001 completo en formato JSON con las 10 claves "
            "obligatorias. Los importes en euros, horas y porcentajes DEBEN "
            "coincidir EXACTO con los campos del bloque `pricing` dentro de "
            "`DATOS ESTRUCTURADOS`. No introduzcas cifras que no esten en "
            "ese bloque. Si no dispones de un dato, escribe literalmente "
            "\"[dato no disponible]\"."
        )
        if retry_hint:
            joined = ", ".join(retry_hint[:8])
            base += (
                "\n\nRECORDATORIO TRAS REINTENTO: en la version anterior "
                f"introdujiste numeros/expresiones no presentes en el pricing: {joined}. "
                "Revisa cada cifra. Si no esta en `pricing`, no la uses."
            )
        return base

    def _public_context_for_prompt(self, ctx: dict[str, Any]) -> dict[str, Any]:
        """Subset serializable (dataclass -> dict) del contexto, para el prompt."""
        pricing = ctx["pricing"]
        pricing_dict = self._serialize_pricing(pricing)
        retainer_dict = None
        if ctx.get("retainer") is not None:
            retainer_dict = asdict(ctx["retainer"])
            retainer_dict = _stringify_decimals(retainer_dict)
        return {
            "categoria": ctx["categoria"],
            "is_aapp": ctx["is_aapp"],
            "client": ctx["client"],
            "sector": ctx["sector"],
            "sistemas_en_alcance": ctx["sistemas_en_alcance"],
            "sedes": ctx["sedes"],
            "madurez_pct": ctx["madurez_pct"],
            "dias_hasta_plazo": ctx["dias_hasta_plazo"],
            "m1_categorization": ctx["m1"],
            "m21_diagnosis": ctx["m21"],
            "m22_discovery": ctx["m22"],
            "pricing": pricing_dict,
            "retainer": retainer_dict,
        }

    def _serialize_pricing(self, p: ImplantacionPricing) -> dict[str, Any]:
        return {
            "categoria": p.categoria,
            "base_eur": f"{p.base:.2f}",
            "extras": [
                {"code": e.code, "description": e.description, "amount_eur": f"{e.amount:.2f}"}
                for e in p.extras
            ],
            "urgency_surcharge_eur": f"{p.urgency_surcharge:.2f}",
            "total_eur": f"{p.total:.2f}",
            "iva_percent": 21,
            "iva_eur": f"{float(p.total) * 0.21:.2f}",
            "total_con_iva_eur": f"{float(p.total) * 1.21:.2f}",
            "hitos": [
                {
                    "code": h.code,
                    "pct": f"{float(h.pct_display):.2f}",
                    "description": h.description,
                    "amount_eur": f"{h.amount:.2f}",
                }
                for h in p.hitos
            ],
            "garantia": p.garantia,
            "hours_range": list(p.hours_range),
            "payment_days": p.payment_days,
            "is_aapp": p.is_aapp,
            "breakdown_text": p.breakdown_text,
        }

    # ------------------------------------------------------------------
    # Number whitelist + hallucination detection — validator v2
    # ------------------------------------------------------------------
    #
    # Estrategia:
    #   1) Regex de citas compuestas (RD 311/2022, Art. 32, CCN-STIC 808,
    #      ISO 27001, Directiva 2022/2555, Anexo II, "24 meses", "95%"...)
    #      → cualquier numero dentro de esas spans es legitimo.
    #   2) Regex de importes con unidad EUR/€/euros → parse formato ES
    #      → comparar con ``known_amounts`` del PricingCalculator +
    #      importes extraidos de la cadena ``garantia``. Si no cuadra,
    #      se flaggea como importe alucinado.
    #   3) Tokens numericos residuales → comparar con WHITELIST_BARE
    #      (artículos, años, porcentajes redondos, medidas ENS, CCN-STIC
    #      catalogo, horas/semanas comunes) + re-parse contra
    #      ``known_amounts`` (por si el LLM omitió la unidad EUR).
    #
    # Los regex usan boundaries alfa-numericas para no partir un CIF
    # ("B95A9EDC2") en sub-tokens ("95", "9").
    # ------------------------------------------------------------------

    # Importe con unidad obligatoria: "14.200,00 EUR", "3.692 EUR", "1.000 €"
    _IMPORT_ES_RE = re.compile(
        r"(?<![A-Za-z0-9])"
        r"(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?|\d+(?:\.\d+))"
        r"\s*(€|EUR|euros?)",
        re.IGNORECASE,
    )

    # Citas compuestas: si el match cubre el número, el número es legítimo
    _CITA_COMPUESTA_RE = re.compile(
        r"("
        r"art(?:[íi]culo|\.)?\s*\d+(?:\.\d+)?"
        r"|\d{4}/\d{3,4}"                             # 2016/679
        r"|\d{1,3}/\d{4}"                             # 311/2022 / 9/2017
        r"|CCN[-\s]?STIC\s*\d{3}"
        r"|CCN[-\s]?CERT\s*(?:IS|IC|IA)[-\s]?\d+"
        r"|ISO(?:/IEC)?[-\s]?\d{4,5}"
        r"|UNE[-\s]?EN[-\s]?\d{4,5}"
        r"|RD\s*\d+/\d{4}"
        r"|Real\s+Decreto[-\s]*(?:ley\s+)?\d+/\d{4}"
        r"|Ley\s+(?:Org[áa]nica\s+)?\d+/\d{4}"
        r"|LO\s*\d+/\d{4}"
        r"|Directiva\s*(?:\(UE\)\s*)?\d{4}/\d{3,4}"
        r"|Reglamento\s*(?:\(UE\)\s*)?\d{4}/\d{3,4}"
        r"|Anexo\s+[IVX]+"
        r"|seccion\s+\d+(?:\.\d+)*"
        r"|secci[oó]n\s+\d+(?:\.\d+)*"
        r"|semanas?\s*\d+"                            # "semana 3" / "semanas 8-10"
        r"|h\d+"                                      # hito codes h1..hN
        r"|\d{1,4}\s*(?:horas?|semanas?|meses?|d[ií]as?|a[ñn]os?)"
        r"|\d{1,3}(?:[.,]\d{1,2})?\s*%"              # 26% o 26,00% o 21.5%
        r"|\d+\s*(?:sistemas?|sedes?|empleados?|medidas?|fases?|hitos?)"
        r"|hito\s*\d+"                                # "hito 3"
        r"|[Ff]ase\s*\d+"                             # "Fase 7"
        r"|[PCDAF]-\d{3,4}"                           # P-001 / C-001 / D-001 etc.
        r"|[vV]\d+(?:\.\d+)?"                         # v2.2 / v3 / V1.0 versiones
        r"|versi[oó]n\s+\d+(?:\.\d+)*"                # "version 2.2"
        r"|cat[eé]goria\s+\d+"                        # "categoría 2"
        r"|Ap[eé]ndice\s+[MNOPQRSTUV]\w*"             # "Apéndice M v2.2"
        r"|MAGERIT\s*v?\d+"                           # MAGERIT v3
        r")",
        re.IGNORECASE,
    )

    # Token numerico con boundaries que no parten identificadores
    # alfanumericos (ej. CIF B95A9EDC2) ni decimales embebidos.
    _NUMBER_TOKEN_RE = re.compile(
        r"(?<![A-Za-z0-9/])"
        r"\d+(?:[.,]\d+)*"
        r"(?![A-Za-z0-9/])"
    )

    # Citas "bare" — el número suelto (p. ej. "808", "311", "2022") es
    # aceptable sin contexto circundante.
    _WHITELIST_BARE: frozenset[str] = frozenset(
        # Normativa española base — números de Ley/RD sueltos
        {"311", "1720", "1007", "6/2022", "1/2022"}
        # Artículos 1..60 (RD 311/2022 tiene 57 + RGPD 99 pero pocos citados)
        | {str(i) for i in range(1, 61)}
        # Artículos de segundo nivel comunes (LCSP 198.4, RD ...)
        | {"198.4", "198", "156"}
        # LCSP / LRJSP / LPAC / LOPDGDD / LSSI-CE / Ley 8/2011
        | {"9/2017", "40/2015", "39/2015", "3/2018", "34/2002", "8/2011"}
        # RGPD / NIS2 / DORA / eIDAS
        | {"679", "2016/679", "2022/2555", "2022/2554", "910/2014",
           "1619/2012"}
        # Años comunes (2000-2035)
        | {str(y) for y in range(2000, 2036)}
        # CCN-STIC (470 PILAR + serie 400 gestion incidentes + serie 500 bastionado +
        # serie 800 completa + PCE)
        | {"400", "401", "402", "403", "405", "410", "440", "470",
           "500", "501", "502", "508", "517", "541", "570", "599",
           "800", "801", "802", "803", "804", "805", "806",
           "807", "808", "809", "810", "815", "817", "820", "821",
           "822", "823", "824", "825", "830", "883", "884", "885"}
        # CCN-CERT IS-XX (47 = IS-47 sanidad)
        | {"47"}
        # Medidas ENS Anexo II (variantes por version)
        | {"73", "75", "80"}
        # Porcentajes redondos típicos en propuestas
        | {"0", "5", "10", "15", "20", "21", "25", "30", "40", "50",
           "60", "70", "75", "80", "90", "95", "100"}
        # Duraciones (horas/semanas/meses comunes)
        | {"6", "8", "12", "18", "24", "36", "42", "48",
           "110", "150", "200"}
    )

    @staticmethod
    def _parse_spanish_amount(raw: str) -> Decimal:
        """'14.200,00' → Decimal(14200.00); '3.692' → Decimal(3692);
        '1.000,5' → Decimal(1000.5). Acepta decimal EN tipo '14.2'
        diferenciando por longitud del grupo tras el punto."""
        s = raw.strip()
        if "," in s and "." in s:
            # Formato ES: miles con ., decimales con ,
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        elif "." in s:
            parts = s.split(".")
            # Si TODAS las partes tras el primer punto son de 3 dígitos
            # asumimos miles ES: "14.200" / "3.692.500"
            if all(len(p) == 3 for p in parts[1:]):
                s = s.replace(".", "")
            # else: decimal EN ("3.14"), dejar tal cual
        return Decimal(s)

    def _build_known_amounts(
        self, pricing: ImplantacionPricing, context: dict[str, Any]
    ) -> set[Decimal]:
        """Set de importes Decimal válidos para un draft dado."""
        amounts: set[Decimal] = set()

        def _add(v: Any) -> None:
            if v is None:
                return
            try:
                amounts.add(Decimal(str(v)).quantize(Decimal("0.01")))
            except Exception:
                pass

        _add(pricing.base)
        _add(pricing.total)
        _add(pricing.urgency_surcharge)
        for e in pricing.extras:
            _add(e.amount)
        for h in pricing.hitos:
            _add(h.amount)
            # Hito con IVA (Opus suele recalcular: importe × 1.21). Anadimos
            # el valor redondeado a Entero y a 2 decimales para cubrir
            # diferencias de precision.
            h_iva = float(h.amount) * 1.21
            _add(h_iva)
            _add(round(h_iva))
        _add(float(pricing.total) * 0.21)        # IVA
        _add(float(pricing.total) * 1.21)        # total con IVA
        # Precios unitarios de extras (Opus a veces cita el unitario en
        # extras con multiplicador, p. ej. "1.200 EUR por sistema adicional").
        try:
            from backend.app.core.pricing.rules import (
                EXTRAS_IMPLANTACION_MEDIA,
                BASE_PRICES,
            )
            for price in EXTRAS_IMPLANTACION_MEDIA.values():
                _add(price)
            for price in BASE_PRICES.values():
                _add(price)
        except Exception:
            pass
        # Importes presentes dentro del texto de garantia (p. ej. "1.000 EUR")
        garantia_text = pricing.garantia or ""
        for m in self._IMPORT_ES_RE.finditer(garantia_text):
            try:
                amounts.add(
                    self._parse_spanish_amount(m.group(1)).quantize(Decimal("0.01"))
                )
            except Exception:
                pass
        retainer = context.get("retainer")
        if retainer is not None:
            _add(retainer.cuota_mensual)
            _add(retainer.total_mensual)
            _add(retainer.tarifa_hora_adicional)
        return amounts

    def validate_numbers_v2(
        self, text: str, *, known_amounts: set[Decimal]
    ) -> list[str]:
        """API pública para validar un trozo de texto libre contra un set
        de importes conocidos + whitelists internas. Devuelve lista de
        tokens ``unknown`` (vacía si todo OK).

        Usado tanto por la lógica interna de retry (:func:`_detect_unknown_numbers_v2`)
        como por scripts de inspección post-mortem sobre drafts dumpeados.
        """
        return self._detect_unknowns_in_text(text, known_amounts)

    def _detect_unknown_numbers_v2(
        self,
        parsed: dict[str, Any],
        known_amounts: set[Decimal],
    ) -> list[str]:
        """Barre las 10 secciones y devuelve tokens unknowns con prefijo
        de sección para que el log sea accionable."""
        unknowns: list[str] = []
        for key in REQUIRED_SECTIONS:
            content = parsed.get(key)
            if not isinstance(content, str):
                continue
            for tok in self._detect_unknowns_in_text(content, known_amounts):
                unknowns.append(f"{key}:{tok}")
        return unknowns

    def _detect_unknowns_in_text(
        self, text: str, known_amounts: set[Decimal]
    ) -> list[str]:
        """Logic central: clasifica cada token numérico como
        (a) dentro de cita compuesta → OK,
        (b) importe con EUR legítimo → OK si coincide con known_amounts,
        (c) bare number en whitelist → OK,
        (d) bare number que parsea a importe conocido → OK,
        (e) else → unknown."""
        safe_spans: list[tuple[int, int]] = []

        # (a) Citas compuestas
        for m in self._CITA_COMPUESTA_RE.finditer(text):
            safe_spans.append((m.start(), m.end()))

        unknowns: list[str] = []
        covered_importe_spans: list[tuple[int, int]] = []

        # (b) Importes con unidad EUR/€
        for m in self._IMPORT_ES_RE.finditer(text):
            raw = m.group(1)
            span = (m.start(), m.end())
            covered_importe_spans.append(span)
            try:
                parsed_amount = self._parse_spanish_amount(raw).quantize(Decimal("0.01"))
            except Exception:
                unknowns.append(f"importe_unparseable:{raw}")
                continue
            if any(abs(parsed_amount - k) <= Decimal("1.00") for k in known_amounts):
                safe_spans.append(span)
            else:
                unknowns.append(f"importe:{raw}")

        # (c+d+e) Tokens numéricos residuales
        for m in self._NUMBER_TOKEN_RE.finditer(text):
            start, end = m.start(), m.end()
            # Dentro de span seguro o ya contabilizado como importe?
            if any(s <= start and end <= e for s, e in safe_spans):
                continue
            if any(s <= start and end <= e for s, e in covered_importe_spans):
                # Ya reportado arriba (o ya validado como importe OK)
                continue
            token = m.group(0)
            if token in self._WHITELIST_BARE:
                continue
            # Re-parse para normalizar y comparar con whitelist bare /
            # known_amounts. Para bare tokens (sin unidad EUR cercana)
            # usamos match exacto (tolerancia 0.01) — la tolerancia de
            # 1 EUR se reserva para el caso "importe con EUR" (IVA
            # rounding).
            try:
                parsed_amount = self._parse_spanish_amount(token).quantize(Decimal("0.01"))
            except Exception:
                parsed_amount = None
            if parsed_amount is not None:
                if any(abs(parsed_amount - k) < Decimal("0.015") for k in known_amounts):
                    continue
                # Normaliza a forma entera: "26,00" -> "26" / "100,00" -> "100"
                if parsed_amount == parsed_amount.to_integral_value():
                    int_form = str(int(parsed_amount))
                    if int_form in self._WHITELIST_BARE:
                        continue
                # Tambien probar forma decimal: "26.00" / "21.00"
                if f"{parsed_amount:.2f}" in self._WHITELIST_BARE:
                    continue
            unknowns.append(token)

        return unknowns

    # ------------------------------------------------------------------
    # Fallback determinista (si LLM falla 3 veces o crashea)
    # ------------------------------------------------------------------

    def _deterministic_fallback(self, ctx: dict[str, Any]) -> dict[str, str]:
        p: ImplantacionPricing = ctx["pricing"]
        aapp = ctx["is_aapp"]
        client = ctx.get("client") or {}
        nombre = client.get("nombre") or client.get("razon_social") or "Cliente"
        sector = ctx.get("sector") or "sin sector declarado"
        categoria = p.categoria
        sedes = ctx.get("sedes")
        sistemas = ctx.get("sistemas_en_alcance")
        iva = float(p.total) * 0.21
        total_iva = float(p.total) * 1.21
        payment = p.payment_days

        extras_txt = "; ".join(
            f"{e.description} ({e.amount:.2f} EUR)" for e in p.extras
        ) or "sin extras aplicados"
        hitos_lines = "\n".join(
            f"- {h.code} ({h.description}): {float(h.pct_display):.0f}% = {h.amount:.2f} EUR"
            for h in p.hitos
        )

        return {
            "resumen_ejecutivo": (
                f"Propuesta comercial P-001 de FULKRO para {nombre} "
                f"(sector {sector}). Objetivo: implantacion ENS categoria {categoria} "
                f"sobre {sistemas} sistema(s) y {sedes} sede(s). Inversion total: "
                f"{p.total:.2f} EUR sin IVA ({total_iva:.2f} EUR con IVA 21%)."
            ),
            "alcance_proyecto": (
                f"Alcance: {sistemas} sistemas, {sedes} sedes. Categoria ENS {categoria}. "
                f"Sector: {sector}."
            ),
            "metodologia_10_fases": (
                "Metodologia estandar ENS en 10 fases: (1) Categorizacion RD 311/2022 "
                "Anexo I; (2) Analisis MAGERIT v3; (3) DdA Anexo II; (4) Gap analysis; "
                "(5) Plan adecuacion; (6) Politicas/procedimientos; (7) Implantacion "
                "controles; (8) Evidencias; (9) Auditoria interna CCN-STIC 808; "
                "(10) Preparacion auditoria externa ENAC."
            ),
            "cronograma_textual": (
                f"Duracion estimada: {p.hours_range[0]}-{p.hours_range[1]} horas de trabajo "
                f"del equipo FULKRO. Plazo tipico: {p.hours_range[1] // 5 + 2} semanas. "
                + ("Plazo corto por urgencia aplicada." if p.urgency_surcharge > 0 else "")
            ),
            "justificacion_extras": f"Extras aplicados: {extras_txt}.",
            "pricing_desglose": (
                f"Base categoria {categoria}: {p.base:.2f} EUR. "
                f"Extras: {extras_txt}. "
                f"Recargo urgencia: {p.urgency_surcharge:.2f} EUR. "
                f"Total sin IVA: {p.total:.2f} EUR. IVA 21%: {iva:.2f} EUR. "
                f"Total con IVA: {total_iva:.2f} EUR."
            ),
            "hitos_pago": (
                f"Hitos de pago oficiales (PricingCalculator Apendice M v2.2):\n{hitos_lines}\n"
                f"Plazo pago: {payment} dias."
            ),
            "garantias": p.garantia,
            "proximos_pasos": (
                "1. Firma P-001 antes de caducidad (30 dias). "
                "2. Firma C-001 (contrato marco). "
                "3. Kick-off semana 0. "
                + ("Via FACe + DIR3 si aplica." if aapp else "Transferencia primer hito al firmar.")
            ),
            "referencias_legales": (
                "[RD 311/2022 ENS]. [CCN-STIC 803 Valoracion]. [CCN-STIC 804 Implantacion]. "
                "[CCN-STIC 808 Auditoria]. "
                + ("[Ley 9/2017 LCSP Art. 198.4 — 60d pago AAPP]. [FACe RD 1619/2012]." if aapp else "[LOPDGDD/RGPD].")
            ),
        }

    # ------------------------------------------------------------------
    # Result shaping
    # ------------------------------------------------------------------

    def _build_result(
        self,
        *,
        proposal_draft: dict[str, Any],
        context: dict[str, Any],
        response: dict[str, Any],
        retry_count: int,
        unknowns: list[str],
        fallback_used: bool,
    ) -> dict[str, Any]:
        tokens_in = int(response.get("tokens_input", 0) or 0)
        tokens_out = int(response.get("tokens_output", 0) or 0)
        cost_eur = (
            (tokens_in / 1_000_000) * _OPUS_47_USD_PER_MTOKEN_INPUT
            + (tokens_out / 1_000_000) * _OPUS_47_USD_PER_MTOKEN_OUTPUT
        ) * _USD_TO_EUR
        return {
            "proposal_draft": proposal_draft,
            "pricing_snapshot": self._serialize_pricing(context["pricing"]),
            "is_aapp": context["is_aapp"],
            "validation": {
                "numbers_ok": not unknowns,
                "unknown_amounts": unknowns,
                "retry_count": retry_count,
            },
            "tokens_input": tokens_in,
            "tokens_output": tokens_out,
            "cost_eur_estimated": round(cost_eur, 4),
            "latency_ms": int(response.get("latency_ms", 0) or 0),
            "model": response.get("model", self.MODEL),
            "fallback_used": fallback_used,
            "context_summary": {
                "categoria": context["categoria"],
                "sector": context["sector"],
                "is_aapp": context["is_aapp"],
                "sistemas_en_alcance": context["sistemas_en_alcance"],
                "sedes": context["sedes"],
                "madurez_pct": context["madurez_pct"],
                "dias_hasta_plazo": context["dias_hasta_plazo"],
                "retainer_tier": (context.get("retainer").tier if context.get("retainer") else None),
            },
        }


def _stringify_decimals(obj: Any) -> Any:
    """Recursivo: convierte Decimal a str para JSON."""
    if isinstance(obj, Decimal):
        return f"{obj:.2f}"
    if isinstance(obj, dict):
        return {k: _stringify_decimals(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_stringify_decimals(x) for x in obj]
    if is_dataclass(obj):
        return _stringify_decimals(asdict(obj))
    return obj


# Alias retrocompatible con scaffold previo
RedactorPropuestasAgent = Agent19Proposals
