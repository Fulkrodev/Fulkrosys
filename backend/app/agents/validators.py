"""Validator v2 compartido para agentes LLM con output narrativo.

Extraido del validator de A19 Redactor Propuestas (Sesion 9 Paso 1).
Reutilizado por A20/A4/A14/A11 a partir de Sesion 9 Paso 2.

Dos responsabilidades:
1. Parser de importes formato ES ("14.200,00 EUR" -> Decimal).
2. Clasificador de tokens numericos en texto libre como
   (a) dentro de cita normativa compuesta (RD/Ley/CCN-STIC/ISO/Art/...)  -> OK
   (b) importe con unidad EUR/€/euros -> compara con ``known_amounts``
   (c) numero bare en WHITELIST_BARE (articulos, anos, porcentajes)      -> OK
   (d) re-parse contra ``known_amounts`` sin unidad                     -> OK
   (e) else -> UNKNOWN (probable alucinacion)

Los regex aplican boundaries alfanumericas para evitar partir
identificadores como CIFs (``B95A9EDC2``).
"""
from __future__ import annotations

import re
from decimal import Decimal
from typing import Iterable


# ══════════════════════════════════════════════════════════════════════════
# Regex compartidos
# ══════════════════════════════════════════════════════════════════════════

# Importe con unidad obligatoria: "14.200,00 EUR", "3.692 EUR", "1.000 €"
IMPORT_ES_RE = re.compile(
    r"(?<![A-Za-z0-9])"
    r"(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?|\d+(?:\.\d+))"
    r"\s*(€|EUR|euros?)",
    re.IGNORECASE,
)

# Citas compuestas: si el match cubre el número, el número es legítimo.
CITA_COMPUESTA_RE = re.compile(
    r"("
    r"art(?:[íi]culos?|\.|s\.?)?\s*\d+(?:\.\d+)?(?:\s*y\s+(?:siguientes|ss\.?))?"
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
    r"|semanas?\s*\d+"
    r"|h\d+"
    r"|\d{1,4}\s*(?:horas?|semanas?|meses?|d[ií]as?|a[ñn]os?)"
    r"|\d{1,3}(?:[.,]\d{1,2})?\s*%"
    r"|\d+\s*(?:sistemas?|sedes?|empleados?|medidas?|fases?|hitos?"
    r"|procedimientos?|politicas?|pol[ií]ticas?|evidencias?|riesgos?"
    r"|amenazas?|activos?|documentos?|controles?|preguntas?)"
    r"|hito\s*\d+"
    r"|[Ff]ase\s*\d+"
    r"|[PCDAF]-\d{3,4}"                           # P-001 / C-001 / D-001 etc.
    r"|[vV]\d+(?:\.\d+)?"                         # v2.2 / v3 / V1.0
    r"|versi[oó]n\s+\d+(?:\.\d+)*"
    r"|cat[eé]goria\s+\d+"
    r"|Ap[eé]ndice\s+[MNOPQRSTUV]\w*"
    r"|MAGERIT\s*v?\d+"
    r")",
    re.IGNORECASE,
)

# Token numerico con boundaries alfanuméricas (no parte CIF)
NUMBER_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9/])"
    r"\d+(?:[.,]\d+)*"
    r"(?![A-Za-z0-9/])"
)

# UUIDs (cuando el LLM cita la proposal_id o similar en el cuerpo del
# draft — ``ebf66f05-341e-4550-a14d-e5a3ea81a574``). Los guiones del
# UUID se interpretan como boundaries por NUMBER_TOKEN_RE y los
# sub-grupos numericos (p. ej. ``4550``) quedarian como unknowns
# espurios. Marcamos el span entero como safe.
UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)

# Numeracion de secciones/clausulas contractuales ("1.1", "5.3", "10.9").
# Cubre "Clausula 1.1", "1.1 Objeto", "5.3.2" etc. Limitado a N<=10,
# M<=99 para no solapar con importes tipo 14.200 (ES miles) o 3.692
# (hitos EUR).
CONTRACT_NUMBERING_RE = re.compile(
    r"(?<![A-Za-z0-9/])"
    r"\d{1,2}\.\d{1,2}(?:\.\d{1,2})?"
    r"(?![A-Za-z0-9/])"
)


# ══════════════════════════════════════════════════════════════════════════
# Whitelist de numeros "bare" (citas sueltas que son siempre legitimas)
# ══════════════════════════════════════════════════════════════════════════

WHITELIST_BARE: frozenset[str] = frozenset(
    # Normativa española base — números de Ley/RD sueltos
    {"311", "1720", "1007", "6/2022", "1/2022"}
    # Artículos 1..60 (RD 311/2022 tiene 57 + RGPD 99 pero pocos citados)
    | {str(i) for i in range(1, 61)}
    # Artículos de segundo nivel comunes (LCSP 198.4, RD ...)
    | {"198.4", "198", "156", "156.2", "198.4"}
    # LCSP / LRJSP / LPAC / LOPDGDD / LSSI-CE / Ley 8/2011
    | {"9/2017", "40/2015", "39/2015", "3/2018", "34/2002", "8/2011",
       "3/2004"}
    # RGPD / NIS2 / DORA / eIDAS
    | {"679", "2016/679", "2022/2555", "2022/2554", "910/2014",
       "1619/2012"}
    # Años comunes (2000-2035)
    | {str(y) for y in range(2000, 2036)}
    # CCN-STIC (470 PILAR + serie 400 + serie 500 + serie 800 + PCE)
    | {"400", "401", "402", "403", "405", "410", "440", "470",
       "500", "501", "502", "508", "517", "541", "570", "599",
       "800", "801", "802", "803", "804", "805", "806",
       "807", "808", "809", "810", "815", "817", "820", "821",
       "822", "823", "824", "825", "827", "830", "883", "884", "885"}
    # CCN-CERT IS-XX / IC-01/19 / IA-XX
    | {"47", "1", "19", "27"}
    # Medidas ENS Anexo II (variantes por version)
    | {"73", "75", "80"}
    # Porcentajes redondos
    | {"0", "5", "10", "15", "20", "21", "25", "30", "40", "50",
       "60", "70", "75", "80", "90", "95", "100"}
    # Duraciones (horas/semanas/meses comunes)
    | {"6", "8", "12", "18", "24", "36", "42", "48",
       "110", "150", "200"}
    # ISO común (no siempre detectado por CITA_COMPUESTA si falta el prefijo)
    | {"27001", "27002", "27005", "27017", "27018", "27701",
       "22301", "22320", "15408", "9001", "14001", "17065"}
)


# ══════════════════════════════════════════════════════════════════════════
# Parser de importes formato ES
# ══════════════════════════════════════════════════════════════════════════


def parse_spanish_amount(raw: str) -> Decimal:
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


# ══════════════════════════════════════════════════════════════════════════
# Detector principal
# ══════════════════════════════════════════════════════════════════════════


def detect_unknowns_in_text(
    text: str,
    known_amounts: set[Decimal],
    *,
    extra_whitelist: Iterable[str] | None = None,
    importe_tolerance: Decimal = Decimal("1.00"),
    bare_tolerance: Decimal = Decimal("0.015"),
) -> list[str]:
    """Devuelve la lista de tokens numericos no reconocidos en ``text``.

    Args:
        text: Texto libre a analizar (p. ej. una seccion del draft LLM).
        known_amounts: Set de importes ``Decimal`` considerados legitimos.
        extra_whitelist: Numeros bare adicionales permitidos por este agente
            (p. ej. retainer tiers si aplica). Union con ``WHITELIST_BARE``.
        importe_tolerance: Tolerancia para matches con unidad EUR/€/euros.
            Default 1 EUR — cubre redondeos de IVA 21% en hitos.
        bare_tolerance: Tolerancia para matches sin unidad. Default 0.015
            — estrictamente exacto (un decimo de centimo).

    Return:
        Lista de strings con el token no reconocido. Los matches cubiertos
        por citas compuestas o por la whitelist no entran en la lista.
    """
    whitelist_bare = (
        WHITELIST_BARE | frozenset(extra_whitelist or ())
    )
    safe_spans: list[tuple[int, int]] = []
    covered_importe_spans: list[tuple[int, int]] = []
    unknowns: list[str] = []

    # (a.1) UUIDs literales (p. ej. ``proposal_id`` citado en el texto)
    # — marcan span entero como seguro para no extraer sub-numeros de los
    # grupos hex entre guiones.
    for m in UUID_RE.finditer(text):
        safe_spans.append((m.start(), m.end()))

    # (a.2) Numeracion de secciones contractuales (1.1, 5.3, 10.9, 5.3.2)
    for m in CONTRACT_NUMBERING_RE.finditer(text):
        safe_spans.append((m.start(), m.end()))

    # (a) Citas compuestas — marcan spans seguros
    for m in CITA_COMPUESTA_RE.finditer(text):
        safe_spans.append((m.start(), m.end()))

    # (b) Importes con unidad EUR
    for m in IMPORT_ES_RE.finditer(text):
        raw = m.group(1)
        span = (m.start(), m.end())
        covered_importe_spans.append(span)
        try:
            parsed = parse_spanish_amount(raw).quantize(Decimal("0.01"))
        except Exception:
            unknowns.append(f"importe_unparseable:{raw}")
            continue
        if any(abs(parsed - k) <= importe_tolerance for k in known_amounts):
            safe_spans.append(span)
        else:
            unknowns.append(f"importe:{raw}")

    # (c+d+e) Tokens numericos residuales
    for m in NUMBER_TOKEN_RE.finditer(text):
        start, end = m.start(), m.end()
        if any(s <= start and end <= e for s, e in safe_spans):
            continue
        if any(s <= start and end <= e for s, e in covered_importe_spans):
            continue
        token = m.group(0)
        if token in whitelist_bare:
            continue
        try:
            parsed = parse_spanish_amount(token).quantize(Decimal("0.01"))
        except Exception:
            parsed = None
        if parsed is not None:
            if any(abs(parsed - k) < bare_tolerance for k in known_amounts):
                continue
            if parsed == parsed.to_integral_value():
                int_form = str(int(parsed))
                if int_form in whitelist_bare:
                    continue
            if f"{parsed:.2f}" in whitelist_bare:
                continue
        unknowns.append(token)

    return unknowns
