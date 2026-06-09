"""Agent 20 — Negociador Contractual (Sesion 9 Paso 2.1).

Convierte una Proposal aprobada (P-001) en un draft de contrato C-001 con
calidad de abogado TIC senior usando Claude Sonnet 4.6 (max_tokens 12.000,
temperature 0.15).

Principio identico a A19:
- LLM SOLO redacta narrativa legal.
- Todos los importes vienen de PricingCalculator via la Proposal de
  entrada (total / hitos / extras / garantia).
- Validador anti-alucinacion reutiliza ``backend.app.agents.validators``
  (parser ES + whitelist citas normativas + known_amounts).
- Retry max 1 -> fallback determinista con clausulas estandar.
- Integracion M14 ContractService.generate_contract_apendice_m con
  parametro ``narrative_mode``.
"""
from __future__ import annotations

import logging
import os
import pathlib
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.base import AgentBase
from backend.app.agents.prompts.agent_20_negociacion import PROMPT
from backend.app.agents.validators import (
    IMPORT_ES_RE,
    detect_unknowns_in_text,
    parse_spanish_amount,
)
from backend.app.core.legal import is_aapp, is_aapp_by_fields

logger = logging.getLogger(__name__)


REQUIRED_SECTIONS: tuple[str, ...] = (
    "preambulo",
    "objeto_alcance",
    "precio_hitos",
    "garantia",
    "incompatibilidad",
    "sector_especifico",
    "duracion_vigencia",
    "obligaciones_post_contratacion",
    "rescision_incumplimiento",
    "jurisdiccion_ley_aplicable",
)


# Sonnet 4.6 blended pricing approx (USD/Mtoken). Solo informativo.
_SONNET_46_USD_PER_MTOKEN_INPUT: float = 3.0
_SONNET_46_USD_PER_MTOKEN_OUTPUT: float = 15.0
_USD_TO_EUR: float = 0.93


class Agent20ContractError(Exception):
    """Error irrecuperable del Agente 20 tras agotar reintentos."""


class Agent20NegociadorContractual(AgentBase):
    """Negociador Contractual LLM (Sonnet 4.6) que produce clausulas C-001."""

    AGENT_ID = 20
    AGENT_NAME = "Negociador Contractual"
    MODEL = "sonnet-4.6"
    TEMPERATURE = 0.15
    MAX_TOKENS = 12000
    SPECIFIC_PROMPT = PROMPT
    # Caching activado (FASE B Path A · 2026-05-23): system prompt
    # ~3-4k tokens (PROMPT 117 LOC + COMMON_HEADER) reusable en cascada
    # retry (MAX_RETRIES_ON_HALLUCINATION=1) cuando A20 genera C-001
    # narrativo y caen unknowns numéricos · 2 calls back-to-back MISMO
    # system prompt. También sesión Marcos generando C-001 varios deals
    # mismo período. Ephemeral TTL 5 min.
    ENABLE_PROMPT_CACHING = True

    MAX_RETRIES_ON_HALLUCINATION = 1

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_contract_clauses(
        self,
        db: AsyncSession,
        proposal_id: uuid.UUID,
        *,
        cliente: Any = None,
        cliente_firmante_nombre: str | None = None,
        cliente_firmante_cargo: str | None = None,
    ) -> dict[str, Any]:
        """Produce el draft contractual C-001 narrativo. Devuelve dict con
        ``clauses_draft`` + metadata de validacion / tokens / coste.
        """
        context = await self._build_full_context(
            db,
            proposal_id=proposal_id,
            cliente=cliente,
            cliente_firmante_nombre=cliente_firmante_nombre,
            cliente_firmante_cargo=cliente_firmante_cargo,
        )
        known_amounts = self._build_known_amounts(context)
        extra_bare = self._build_extra_whitelist(context)

        retry_count = 0
        last_unknowns: list[str] = []
        last_response: dict[str, Any] = {}

        for attempt in range(self.MAX_RETRIES_ON_HALLUCINATION + 1):
            response = await self.invoke(
                db,
                project_id=context.get("project_id"),
                user_message=self._user_message(
                    context, retry_hint=last_unknowns if attempt > 0 else None
                ),
                context=self._public_context_for_prompt(context),
                structured_output=True,
            )
            last_response = response
            parsed = response.get("parsed")
            if not isinstance(parsed, dict):
                last_unknowns = ["<output no es JSON valido con 10 claves requeridas>"]
                retry_count = attempt + 1
                self._dump_rejected_draft(attempt + 1, response, reason="json_invalid")
                continue
            if not all(k in parsed for k in REQUIRED_SECTIONS):
                missing = [k for k in REQUIRED_SECTIONS if k not in parsed]
                last_unknowns = [f"<faltan claves obligatorias: {missing}>"]
                retry_count = attempt + 1
                self._dump_rejected_draft(
                    attempt + 1, response, reason=f"missing_keys={missing}",
                )
                continue
            unknowns = self._detect_unknown_numbers(parsed, known_amounts, extra_bare)
            if not unknowns:
                return self._build_result(
                    clauses_draft=parsed,
                    context=context,
                    response=response,
                    retry_count=attempt,
                    unknowns=[],
                    fallback_used=False,
                )
            last_unknowns = unknowns
            retry_count = attempt + 1
            logger.info(
                "A20 attempt %d: %d unknown numbers detected; retrying",
                attempt + 1, len(unknowns),
            )
            self._dump_rejected_draft(
                attempt + 1, response, reason="unknown_numbers", unknowns=unknowns,
            )

        logger.warning(
            "A20 hallucinated numbers after %d attempts, falling back to deterministic clauses",
            self.MAX_RETRIES_ON_HALLUCINATION + 1,
        )
        fallback_draft = self._deterministic_fallback(context)
        return self._build_result(
            clauses_draft=fallback_draft,
            context=context,
            response=last_response,
            retry_count=retry_count,
            unknowns=last_unknowns,
            fallback_used=True,
        )

    # ------------------------------------------------------------------
    # Debug dump (opt-in env var)
    # ------------------------------------------------------------------

    def _dump_rejected_draft(
        self,
        attempt: int,
        response: dict[str, Any],
        *,
        reason: str,
        unknowns: list[str] | None = None,
    ) -> None:
        """Guarda un draft rechazado en /tmp para inspeccion.

        Opt-in via ``FULKRO_AGENT_DEBUG_DUMPS`` (off en produccion).
        """
        if not os.environ.get("FULKRO_AGENT_DEBUG_DUMPS"):
            return
        try:
            import uuid as _uuid
            out_dir = pathlib.Path("/tmp")
            short_id = _uuid.uuid4().hex[:8]
            path = out_dir / f"a20_rejected_attempt_{attempt}_{short_id}.md"
            raw = response.get("response") or ""
            tokens_in = response.get("tokens_input", 0)
            tokens_out = response.get("tokens_output", 0)
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# A20 REJECTED DRAFT — attempt {attempt}\n\n")
                f.write(f"- reason: {reason}\n")
                f.write(f"- tokens_in / out: {tokens_in} / {tokens_out}\n")
                if unknowns:
                    f.write(f"- unknowns ({len(unknowns)}):\n")
                    for u in unknowns[:50]:
                        f.write(f"    - {u}\n")
                f.write("\n---\n\n## RAW LLM RESPONSE\n\n```\n")
                f.write(raw)
                f.write("\n```\n")
            logger.warning("A20 rejected draft saved to %s", path)
        except Exception as exc:
            logger.debug("A20 dump rejected failed: %s", exc)

    # ------------------------------------------------------------------
    # Context builder — carga desde la Proposal aprobada
    # ------------------------------------------------------------------

    async def _build_full_context(
        self,
        db: AsyncSession,
        *,
        proposal_id: uuid.UUID,
        cliente: Any,
        cliente_firmante_nombre: str | None,
        cliente_firmante_cargo: str | None,
    ) -> dict[str, Any]:
        row = (
            await db.execute(
                sql_text(
                    "SELECT id, lead_id, project_id, categoria_objetivo, "
                    "importe_total, importe_desglose, hitos_pago, alcance, "
                    "notas_marcos, validez_hasta "
                    "FROM proposals WHERE id = :pid"
                ),
                {"pid": str(proposal_id)},
            )
        ).fetchone()
        if not row:
            raise Agent20ContractError(
                f"Proposal {proposal_id} no encontrada"
            )
        categoria = (row[3] or "").upper()
        importe_total = Decimal(str(row[4] or 0))
        desglose = row[5] or {}
        hitos = (row[6] or {}).get("hitos", [])
        alcance = row[7] or {}
        notas = row[8] or ""

        # Cliente: preferir arg, fallback a lead + clients tabla
        cliente_ctx = await self._resolve_client(db, row[1], cliente=cliente)
        project_id = row[2]
        sector = alcance.get("sector") or cliente_ctx.get("sector")
        sistemas = int(alcance.get("sistemas_en_alcance") or 1)
        sedes = int(alcance.get("sedes") or 1)
        dias_hasta_plazo = alcance.get("dias_hasta_plazo")
        urgency = Decimal(str(desglose.get("urgency_surcharge", 0) or 0))

        aapp = is_aapp(cliente_ctx) or is_aapp_by_fields(
            cif=cliente_ctx.get("cif"),
            tipo_organizacion=cliente_ctx.get("tipo_organizacion"),
            razon_social=cliente_ctx.get("razon_social") or cliente_ctx.get("nombre"),
        )

        # Extraer garantia literal del notas_marcos (formato Paso 6 M13)
        garantia_text = ""
        if "Garantia:" in notas:
            garantia_text = notas.split("Garantia:", 1)[1].strip()
        else:
            # Fallback: intentar lookup en rules
            try:
                from backend.app.core.pricing.rules import GARANTIAS_COMERCIALES
                garantia_text = GARANTIAS_COMERCIALES.get(categoria, "")
            except Exception:
                garantia_text = ""

        return {
            "proposal_id": str(proposal_id),
            "project_id": project_id,
            "categoria": categoria,
            "client": cliente_ctx,
            "cliente_firmante_nombre": cliente_firmante_nombre or "[por designar]",
            "cliente_firmante_cargo": cliente_firmante_cargo or "[por designar]",
            "is_aapp": aapp,
            "sector": sector,
            "sistemas_en_alcance": sistemas,
            "sedes": sedes,
            "dias_hasta_plazo": dias_hasta_plazo,
            "importe_total": importe_total,
            "importe_desglose": desglose,
            "hitos": hitos,
            "urgency_surcharge": urgency,
            "garantia_text": garantia_text,
            "validez_hasta": str(row[9]) if row[9] else None,
        }

    async def _resolve_client(
        self, db: AsyncSession, lead_id: Any, *, cliente: Any
    ) -> dict[str, Any]:
        if cliente:
            if isinstance(cliente, dict):
                return {
                    "id": cliente.get("id"),
                    "nombre": cliente.get("nombre") or cliente.get("razon_social"),
                    "razon_social": cliente.get("razon_social") or cliente.get("nombre"),
                    "cif": cliente.get("cif"),
                    "sector": cliente.get("sector"),
                    "tipo_organizacion": cliente.get("tipo_organizacion"),
                    "provincia": cliente.get("provincia"),
                }
            return {
                "id": getattr(cliente, "id", None),
                "nombre": getattr(cliente, "nombre", None) or getattr(cliente, "razon_social", None),
                "razon_social": (
                    getattr(cliente, "razon_social", None)
                    or getattr(cliente, "nombre", None)
                ),
                "cif": getattr(cliente, "cif", None),
                "sector": getattr(cliente, "sector", None),
                "tipo_organizacion": getattr(cliente, "tipo_organizacion", None),
                "provincia": getattr(cliente, "provincia", None),
            }
        # Fallback: lead → buscar por CIF en clients
        if lead_id is None:
            return {}
        try:
            lead = (
                await db.execute(
                    sql_text(
                        "SELECT empresa_nombre, empresa_cif, sector "
                        "FROM leads WHERE id = :lid"
                    ),
                    {"lid": str(lead_id)},
                )
            ).fetchone()
            if not lead:
                return {}
            return {
                "nombre": lead[0],
                "razon_social": lead[0],
                "cif": lead[1],
                "sector": lead[2],
            }
        except Exception as exc:
            logger.debug("A20 resolve_client fallback failed: %s", exc)
            return {}

    # ------------------------------------------------------------------
    # Known amounts + whitelist extendida
    # ------------------------------------------------------------------

    def _build_known_amounts(self, context: dict[str, Any]) -> set[Decimal]:
        amounts: set[Decimal] = set()

        def _add(v: Any) -> None:
            if v is None:
                return
            try:
                amounts.add(Decimal(str(v)).quantize(Decimal("0.01")))
            except Exception:
                pass

        total = context["importe_total"]
        _add(total)
        _add(context["urgency_surcharge"])
        _add(float(total) * 0.21)
        _add(float(total) * 1.21)
        # Base + extras (del importe_desglose)
        desglose = context.get("importe_desglose") or {}
        _add(desglose.get("base"))
        for extra in desglose.get("extras") or []:
            if isinstance(extra, dict):
                _add(extra.get("amount"))
        _add(desglose.get("iva_importe"))
        _add(desglose.get("total_con_iva"))
        # Hitos
        for h in context.get("hitos") or []:
            if isinstance(h, dict):
                amt = h.get("amount")
                _add(amt)
                # Hito con IVA (Sonnet suele recalcular)
                try:
                    amt_d = float(amt or 0)
                    _add(amt_d * 1.21)
                    _add(round(amt_d * 1.21))
                except Exception:
                    pass
        # Importes dentro de la cadena garantia (MEDIA incluye "1.000 EUR")
        garantia = context.get("garantia_text") or ""
        for m in IMPORT_ES_RE.finditer(garantia):
            try:
                amounts.add(
                    parse_spanish_amount(m.group(1)).quantize(Decimal("0.01"))
                )
            except Exception:
                pass
        # Threshold de mediacion previa (100.000 EUR) mencionado en la
        # clausula jurisdiccion_ley_aplicable del prompt.
        _add(100000)
        _add(100000.00)
        # Precios unitarios de extras (Sonnet puede citarlos)
        try:
            from backend.app.core.pricing.rules import (
                BASE_PRICES,
                EXTRAS_IMPLANTACION_MEDIA,
            )
            for price in EXTRAS_IMPLANTACION_MEDIA.values():
                _add(price)
            for price in BASE_PRICES.values():
                _add(price)
        except Exception:
            pass
        return amounts

    def _build_extra_whitelist(self, context: dict[str, Any]) -> set[str]:
        """Tokens bare adicionales aceptables en un contrato C-001."""
        extras = {
            # Vigencia / plazos legales
            "30", "60", "90", "15",
            # Años comunes LCSP / morosidad
            "2004", "198", "198.4",
            # Garantia bianual / quinquenal / decenal
            "5", "10",
            # IVA
            "21",
            # Limite mediacion jurisdiccion
            "100",
            "100.000", "100000",
        }
        # Categoria puede aparecer como "73 medidas" / "75 medidas" / "80 medidas"
        extras |= {"73", "75", "80"}
        return extras

    # ------------------------------------------------------------------
    # Prompt serialization
    # ------------------------------------------------------------------

    def _user_message(
        self, context: dict[str, Any], retry_hint: list[str] | None = None
    ) -> str:
        base = (
            "Genera el draft contractual C-001 completo en JSON con las 10 "
            "claves obligatorias descritas en el prompt del sistema. Respeta "
            "EXACTAMENTE los importes del bloque ``pricing`` de los DATOS "
            "ESTRUCTURADOS. La clausula ``incompatibilidad`` es obligatoria "
            "(ISO 17065 + CCN-CERT IC-01/19) y no puede omitirse."
        )
        if retry_hint:
            joined = ", ".join(retry_hint[:8])
            base += (
                "\n\nRECORDATORIO TRAS REINTENTO: en la version anterior "
                f"introdujiste numeros/expresiones no presentes en el pricing: {joined}. "
                "Revisa cada cifra. Si no esta en ``pricing``, no la uses."
            )
        return base

    def _public_context_for_prompt(self, ctx: dict[str, Any]) -> dict[str, Any]:
        hitos_out = []
        for h in ctx.get("hitos") or []:
            if not isinstance(h, dict):
                continue
            hitos_out.append({
                "code": h.get("code"),
                "pct": h.get("pct"),
                "description": h.get("description"),
                "amount_eur": f"{Decimal(str(h.get('amount') or 0)):.2f}",
            })
        desglose = ctx.get("importe_desglose") or {}
        extras_out = []
        for e in desglose.get("extras") or []:
            if isinstance(e, dict):
                extras_out.append({
                    "code": e.get("code"),
                    "description": e.get("description"),
                    "amount_eur": f"{Decimal(str(e.get('amount') or 0)):.2f}",
                })
        total = ctx["importe_total"]
        return {
            "proposal_id": ctx["proposal_id"],
            "categoria": ctx["categoria"],
            "is_aapp": ctx["is_aapp"],
            "sector": ctx["sector"],
            "client": ctx["client"],
            "cliente_firmante_nombre": ctx["cliente_firmante_nombre"],
            "cliente_firmante_cargo": ctx["cliente_firmante_cargo"],
            "sistemas_en_alcance": ctx["sistemas_en_alcance"],
            "sedes": ctx["sedes"],
            "dias_hasta_plazo": ctx["dias_hasta_plazo"],
            "validez_hasta": ctx["validez_hasta"],
            "pricing": {
                "categoria": ctx["categoria"],
                "base_eur": (
                    f"{Decimal(str(desglose.get('base') or 0)):.2f}"
                    if desglose.get("base") is not None else None
                ),
                "extras": extras_out,
                "urgency_surcharge_eur": f"{Decimal(str(ctx['urgency_surcharge'])):.2f}",
                "urgent": ctx["urgency_surcharge"] > 0,
                "total_eur": f"{Decimal(str(total)):.2f}",
                "iva_percent": 21,
                "iva_eur": f"{float(total) * 0.21:.2f}",
                "total_con_iva_eur": f"{float(total) * 1.21:.2f}",
                "hitos": hitos_out,
                "garantia": ctx["garantia_text"],
                "payment_days": 60 if ctx["is_aapp"] else 30,
            },
        }

    # ------------------------------------------------------------------
    # Deteccion de unknowns (delegada a validators.py)
    # ------------------------------------------------------------------

    def _detect_unknown_numbers(
        self,
        parsed: dict[str, Any],
        known_amounts: set[Decimal],
        extra_whitelist: set[str],
    ) -> list[str]:
        unknowns: list[str] = []
        for key in REQUIRED_SECTIONS:
            content = parsed.get(key)
            if not isinstance(content, str):
                continue
            for tok in detect_unknowns_in_text(
                content, known_amounts, extra_whitelist=extra_whitelist
            ):
                unknowns.append(f"{key}:{tok}")
        return unknowns

    # ------------------------------------------------------------------
    # Fallback deterministico
    # ------------------------------------------------------------------

    def _deterministic_fallback(self, ctx: dict[str, Any]) -> dict[str, str]:
        cliente = ctx.get("client") or {}
        nombre = cliente.get("nombre") or cliente.get("razon_social") or "Cliente"
        cif = cliente.get("cif") or "[CIF no disponible]"
        aapp = ctx["is_aapp"]
        cat = ctx["categoria"]
        sector = ctx.get("sector") or "sin sector declarado"
        total = ctx["importe_total"]
        total_iva = float(total) * 1.21
        iva = float(total) * 0.21
        garantia = ctx.get("garantia_text") or ""
        hitos = ctx.get("hitos") or []
        urgencia = ctx["urgency_surcharge"]

        hitos_lines = "\n".join(
            f"- {h.get('code','?')}: {h.get('description','')} "
            f"{h.get('pct','?')}% = {h.get('amount','?')} EUR"
            for h in hitos if isinstance(h, dict)
        )

        regimen_aapp = (
            "AAPP — Ley 9/2017 LCSP Art. 198.4 (pago 60 dias naturales), "
            "FACe y Facturae obligatorios, DIR3 requerido."
            if aapp else
            "privado — Ley 3/2004 morosidad (pago 30 dias)."
        )

        return {
            "preambulo": (
                f"Contrato de servicios de consultoria ENS (C-001) entre "
                f"FULKRO como Consultor y {nombre} (CIF {cif}) como Cliente. "
                f"Antecedente: propuesta P-001 aceptada. Objeto general: "
                f"adecuacion al Esquema Nacional de Seguridad categoria {cat} "
                f"[RD 311/2022 Art. 2]."
            ),
            "objeto_alcance": (
                f"Alcance: {ctx['sistemas_en_alcance']} sistemas, "
                f"{ctx['sedes']} sedes. Sector: {sector}. Categoria ENS {cat}."
            ),
            "precio_hitos": (
                f"Importe total sin IVA: {total:.2f} EUR. IVA 21%: {iva:.2f} EUR. "
                f"Total con IVA: {total_iva:.2f} EUR. Regimen: {regimen_aapp}\n\n"
                f"Hitos:\n{hitos_lines}"
                + (f"\n\nRecargo urgencia: {urgencia:.2f} EUR." if urgencia > 0 else "")
            ),
            "garantia": garantia or "Garantia estandar FULKRO segun categoria {cat}.",
            "incompatibilidad": (
                "FULKRO manifiesta y el Cliente acepta que, en aplicacion de "
                "ISO/IEC 17065 y de la nota CCN-CERT IC-01/19 sobre "
                "independencia del auditor ENS, el Consultor no podra realizar "
                "la auditoria externa de certificacion ENAC sobre los sistemas "
                "objeto del presente contrato. Clausula de orden publico, "
                "no derogable por acuerdo de las Partes."
            ),
            "sector_especifico": (
                f"Regimen sectorial {sector}. "
                + (
                    "[Art. 28 RGPD] encargado de tratamiento de datos de salud "
                    "(Art. 9 RGPD). [CCN-CERT IS-47] sanitario. "
                    if "sanid" in (sector or "").lower()
                    else ""
                )
                + ("[DORA Reglamento UE 2022/2554] resiliencia operativa digital. " if "fintech" in (sector or "").lower() else "")
                + ("[LCSP Ley 9/2017] + [Ley 40/2015 Art. 156.2]. " if aapp else "[Codigo de Comercio]. ")
            ),
            "duracion_vigencia": (
                "Entrada en vigor: firma dentro de 30 dias naturales de la "
                "P-001. Duracion: hasta entrega del dossier + 60 dias de "
                "acompanamiento auditoria externa. Sin prorroga tacita."
            ),
            "obligaciones_post_contratacion": (
                "Tras la certificacion, el Cliente tendra opcion (no obligacion) "
                "de suscribir el contrato C-003 Retainer. Traspaso documental "
                "completo independiente de retainer. Confidencialidad 5 anos."
            ),
            "rescision_incumplimiento": (
                "Causas de rescision: retraso >30 dias imputable, impago >15 "
                "dias, revelacion de informacion confidencial. Liquidacion a "
                "prorrata del trabajo ejecutado."
            ),
            "jurisdiccion_ley_aplicable": (
                "Ley espanola. "
                + (
                    "Juzgados Contencioso-Administrativos de Madrid."
                    if aapp else
                    "Juzgados Mercantiles de Madrid; sumision expresa."
                )
            ),
        }

    # ------------------------------------------------------------------
    # Result shaping
    # ------------------------------------------------------------------

    def _build_result(
        self,
        *,
        clauses_draft: dict[str, Any],
        context: dict[str, Any],
        response: dict[str, Any],
        retry_count: int,
        unknowns: list[str],
        fallback_used: bool,
    ) -> dict[str, Any]:
        tokens_in = int(response.get("tokens_input", 0) or 0)
        tokens_out = int(response.get("tokens_output", 0) or 0)
        cost_eur = (
            (tokens_in / 1_000_000) * _SONNET_46_USD_PER_MTOKEN_INPUT
            + (tokens_out / 1_000_000) * _SONNET_46_USD_PER_MTOKEN_OUTPUT
        ) * _USD_TO_EUR
        return {
            "clauses_draft": clauses_draft,
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
                "proposal_id": context["proposal_id"],
                "categoria": context["categoria"],
                "sector": context["sector"],
                "is_aapp": context["is_aapp"],
                "importe_total": float(context["importe_total"]),
                "urgency": float(context["urgency_surcharge"]),
            },
        }


# Alias retro-compatible con el scaffold previo
AsistenteNegociacionAgent = Agent20NegociadorContractual
