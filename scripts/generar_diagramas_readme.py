#!/usr/bin/env python3
"""Genera los diagramas del README en español y en inglés.

    python3 scripts/generar_diagramas_readme.py
    -> docs/assets/diagramas/{es,en}/{hero,arquitectura,ciclo,rag,ia,seguridad}.svg

Un solo origen para las dos lenguas: cada diagrama se dibuja una vez y los
textos salen de un diccionario. Las animaciones son SMIL, que GitHub reproduce
aunque el SVG vaya dentro de <img>. Cada diagrama trae su propio fondo oscuro,
así se lee igual con el tema claro que con el oscuro. Las cifras que aparecen
son las del README, cada una con su comando en la sección de métricas.
"""
from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "docs" / "assets" / "diagramas"

FUENTE = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
C = {
    "fondo1": "#0e0a22", "fondo2": "#1a1440", "caja": "#1d1838", "borde": "#352d66",
    "v1": "#6C63FF", "v2": "#8B83FF", "rosa": "#e879f9", "verde": "#34d399",
    "ambar": "#fbbf24", "texto": "#ffffff", "suave": "#c4c0e8", "tenue": "#8f89c2",
}


def t(x, y, texto, tam=15, color="texto", peso=400, ancla="start", fuente=FUENTE, extra=""):
    return (f'<text x="{x}" y="{y}" font-family="{fuente}" font-size="{tam}" '
            f'font-weight="{peso}" fill="{C.get(color, color)}" text-anchor="{ancla}" {extra}>'
            f"{escape(texto)}</text>")


def caja(x, y, w, h, r=14, relleno="caja", borde="borde", extra=""):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" '
            f'fill="{C.get(relleno, relleno)}" stroke="{C.get(borde, borde)}" stroke-width="1.5" {extra}/>')


def lienzo(w, h, cuerpo, titulo):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(titulo)}">
<defs>
  <linearGradient id="fondo" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{C['fondo1']}"/><stop offset="1" stop-color="{C['fondo2']}"/></linearGradient>
  <linearGradient id="marca" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{C['v1']}"/><stop offset="1" stop-color="{C['rosa']}"/></linearGradient>
  <radialGradient id="halo"><stop offset="0" stop-color="{C['v1']}" stop-opacity=".55"/>
    <stop offset="1" stop-color="{C['v1']}" stop-opacity="0"/></radialGradient>
  <marker id="flecha" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
    <path d="M0,0 L10,5 L0,10 z" fill="{C['v2']}"/></marker>
</defs>
<rect width="{w}" height="{h}" rx="18" fill="url(#fondo)"/>
{cuerpo}
</svg>
"""


def flujo(x1, y1, x2, y2, dur=1.6, color="v2"):
    """Línea discontinua que avanza: el sentido del dato."""
    return (f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{C[color]}" stroke-width="2" fill="none" '
            f'stroke-dasharray="6 7" marker-end="url(#flecha)" opacity=".85">'
            f'<animate attributeName="stroke-dashoffset" from="26" to="0" dur="{dur}s" '
            f'repeatCount="indefinite"/></path>')


def particula(camino, dur, retraso=0.0, color="rosa", r=4.5):
    return (f'<circle r="{r}" fill="{C[color]}"><animateMotion dur="{dur}s" begin="{retraso}s" '
            f'repeatCount="indefinite" path="{camino}"/>'
            f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.1;.9;1" dur="{dur}s" '
            f'begin="{retraso}s" repeatCount="indefinite"/></circle>')


def logo(x, y, s=1.0):
    return (f'<g transform="translate({x},{y}) scale({s})">'
            f'<polygon points="48,78 14,78 48,26" fill="{C["v1"]}"/>'
            f'<polygon points="48,78 82,78 48,26" fill="{C["v2"]}" opacity=".8"/>'
            f'<rect x="18" y="21" width="60" height="9" rx="4.5" fill="#fff"/>'
            f'<circle cx="48" cy="26" r="5" fill="{C["v1"]}"/></g>')


# ─────────────────────────────── textos ────────────────────────────────
FASES = {
    "es": [("Categorización", "m01", "Acta · E-012"), ("Riesgos", "m02", "MAGERIT v3"),
           ("Aplicabilidad", "m03", "DdA · 73 medidas"), ("Plan", "m17", "E-150 · Gantt"),
           ("Implantación", "m07", "Evidencia · WORM"), ("Verificación", "m10", "Simulacro · pre-ENAC"),
           ("Conformidad", "m27", "Declaración · E-041")],
    "en": [("Categorisation", "m01", "Record · E-012"), ("Risk", "m02", "MAGERIT v3"),
           ("Applicability", "m03", "SoA · 73 measures"), ("Plan", "m17", "E-150 · Gantt"),
           ("Implementation", "m07", "WORM · evidence"), ("Verification", "m10", "Pre-audit · rehearsal"),
           ("Conformity", "m27", "Declaration · E-041")],
}

TX = {
    "es": {
        "hero_t": "Implantación del Esquema Nacional de Seguridad, de punta a punta",
        "hero_s": "Motores deterministas · capa de IA con RAG · cuatro portales · evidencia firmada",
        "hero_c": "44 motores · 1.203 operaciones de API · 253 tablas · 6.895 tests",
        "arq_titulo": "Arquitectura", "quien": "QUIÉN ENTRA",
        "portales": [("Administración", "el consultor · WebAuthn o TOTP"),
                     ("Cliente", "ve, autoriza y firma · MFA"),
                     ("Auditor", "sólo lectura · enlace Ed25519 + OTP"),
                     ("Público", "verifica el distintivo firmado")],
        "front": "Next.js 15 · App Router · 167 páginas · tiempo real por SSE",
        "puerta": "Una sola puerta: authenticate_request en 1.204 de 1.204 rutas · JWT Ed25519 · CSRF · contexto RLS por petición",
        "api": "FastAPI · 1.203 operaciones · 44 motores de dominio",
        "grupos": [("Ciclo ENS", ["Categorización", "MAGERIT", "DdA", "Brechas", "Plan", "Evidencias", "Simulacro", "Conformidad"]),
                   ("Documentos y firma", ["123 plantillas", "Firma Ed25519", "Enlaces mágicos", "Gestor documental"]),
                   ("Inteligencia", ["Copiloto RAG", "12 agentes", "Router de LLM", "Observabilidad"]),
                   ("Operación", ["Nube read-only", "Verificación MCP", "Copias cifradas", "Monitor ENS"])],
        "asinc": "Celery + Redis · 20 tareas programadas · difusión SSE con reenvío",
        "datos": [("PostgreSQL 16", "253 tablas · RLS en 185 · pgvector"),
                  ("MinIO", "7 buckets · Object Lock WORM 7 años"),
                  ("API de Anthropic", "sólo a través del router")],
        "ciclo_titulo": "El ciclo ENS: cada fase consume lo que produjo la anterior",
        "puerta_fase": "puerta", "motor": "motor",
        "rag_titulo": "RAG normativo: recuperación medida, respuesta anclada",
        "ingesta": "INGESTA · una vez", "consulta": "CONSULTA · en cada pregunta",
        "ing": [("Fuentes oficiales", "BOE RD 311/2022 · RGPD", "DORA · NIS2 · eIDAS"),
                ("Parser determinista", "artículos y anexos", "73 códigos de medida"),
                ("1.031 fragmentos", "127 del RD 311", "904 de la UE"),
                ("e5-large · 1024 d", "multilingüe", "prefijo passage:"),
                ("pgvector", "índice HNSW coseno", "m=16 · ef=64")],
        "con": [("Pregunta", "+ pantalla actual", "+ estado del proyecto"),
                ("Embedding", "prefijo query:", "mismo modelo"),
                ("Top-30 → top-5", "por coseno", "vectorial sola"),
                ("Prompt con reglas", "cita obligatoria", "temperatura ≤ 0,2"),
                ("Router de LLM", "reintentos 429", "caché de prompts"),
                ("Validación", "citas extraídas", "anclaje ≥ 30 %")],
        "eval_t": "EVALUACIÓN · 49 consultas etiquetadas",
        "eval": [("acierto@5", "0,959"), ("recall@5", "0,824"), ("MRR", "0,752")],
        "eval_n": "La fusión léxica se retiró: perdía 0,157 de recall@5, IC 95 % que no cruza el cero.",
        "ia_titulo": "La capa de IA: los motores deciden, el modelo redacta",
        "ia_motor": "Motor determinista", "ia_motor_s": "regla normativa · trazable",
        "ia_dec": "Decisión normativa", "ia_dec_s": "categoría · aplicabilidad · plazos",
        "ia_firma": "Entregables firmables", "ia_firma_s": "DdA, actas y declaración: sin texto del modelo",
        "ia_decide": "decide", "ia_redacta": "redacta",
        "ia_agente": "12 agentes activos", "ia_agente_s": "contexto del proyecto",
        "ia_json": "Salida estructurada", "ia_json_s": "JSON con esquema",
        "ia_ok": "valida", "ia_retry": "3 reintentos", "ia_plant": "Plantilla de reserva",
        "ia_marca": "generado_por", "ia_marca_s": "modelo · plantilla · sin clave",
        "ia_ui": "La interfaz avisa si el texto no es del modelo",
        "ia_guard": ["temperatura ≤ 0,2", "citas obligatorias", "guardia anti-inyección",
                     "filtro de tono al cliente", "coste de cada llamada registrado"],
        "seg_titulo": "Seguridad en profundidad",
        "seg": [("Identidad", "WebAuthn o TOTP · MFA de cliente · enlaces Ed25519 con OTP"),
                ("Sesión", "JWT Ed25519 en cookie httpOnly · CSRF por petición"),
                ("Aislamiento", "RLS en 185 de 253 tablas · 192 políticas · rol sin superusuario"),
                ("Integridad", "registro de auditoría con cadena SHA-256 · sin UPDATE ni DELETE"),
                ("Custodia", "antivirus · SHA-256 · firma Ed25519 · WORM 7 años"),
                ("Operación", "copias cifradas · monitor ENS Medio sobre sí misma")],
    },
    "en": {
        "hero_t": "Implementing Spain's National Security Framework, end to end",
        "hero_s": "Deterministic engines · AI layer with RAG · four portals · signed evidence",
        "hero_c": "44 engines · 1,203 API operations · 253 tables · 6,895 tests",
        "arq_titulo": "Architecture", "quien": "WHO COMES IN",
        "portales": [("Admin", "the consultant · WebAuthn or TOTP"),
                     ("Client", "reviews, approves, signs · MFA"),
                     ("Auditor", "read only · Ed25519 link + OTP"),
                     ("Public", "verifies the signed badge")],
        "front": "Next.js 15 · App Router · 167 pages · real time over SSE",
        "puerta": "One door: authenticate_request on 1,204 of 1,204 routes · Ed25519 JWT · CSRF · per-request RLS context",
        "api": "FastAPI · 1,203 operations · 44 domain engines",
        "grupos": [("ENS lifecycle", ["Categorisation", "MAGERIT", "SoA", "Gaps", "Plan", "Evidence", "Rehearsal", "Conformity"]),
                   ("Documents & signing", ["123 templates", "Ed25519 signing", "Magic links", "Document store"]),
                   ("Intelligence", ["RAG copilot", "12 agents", "LLM router", "Observability"]),
                   ("Operations", ["Read-only cloud", "MCP verification", "Encrypted backups", "ENS monitor"])],
        "asinc": "Celery + Redis · 20 scheduled jobs · SSE fan-out with replay",
        "datos": [("PostgreSQL 16", "253 tables · RLS on 185 · pgvector"),
                  ("MinIO", "7 buckets · Object Lock WORM 7 years"),
                  ("Anthropic API", "only through the router")],
        "ciclo_titulo": "The ENS lifecycle: each phase consumes what the previous one produced",
        "puerta_fase": "gate", "motor": "engine",
        "rag_titulo": "Regulatory RAG: measured retrieval, grounded answers",
        "ingesta": "INGESTION · once", "consulta": "QUERY · every question",
        "ing": [("Official sources", "BOE RD 311/2022 · GDPR", "DORA · NIS2 · eIDAS"),
                ("Deterministic parser", "articles and annexes", "73 measure codes"),
                ("1,031 chunks", "127 from RD 311", "904 from the EU"),
                ("e5-large · 1024 d", "multilingual", "passage: prefix"),
                ("pgvector", "HNSW cosine index", "m=16 · ef=64")],
        "con": [("Question", "+ current screen", "+ project state"),
                ("Embedding", "query: prefix", "same model"),
                ("Top-30 → top-5", "by cosine", "vector only"),
                ("Ruled prompt", "citations required", "temperature ≤ 0.2"),
                ("LLM router", "429 retries", "prompt caching"),
                ("Validation", "citations extracted", "grounding ≥ 30%")],
        "eval_t": "EVALUATION · 49 hand-labelled queries",
        "eval": [("hit@5", "0.959"), ("recall@5", "0.824"), ("MRR", "0.752")],
        "eval_n": "Lexical fusion was removed: it lost 0.157 recall@5, with a 95% CI that excludes zero.",
        "ia_titulo": "The AI layer: engines decide, the model drafts",
        "ia_motor": "Deterministic engine", "ia_motor_s": "regulatory rule · traceable",
        "ia_dec": "Regulatory decision", "ia_dec_s": "category · applicability · deadlines",
        "ia_firma": "Signable deliverables", "ia_firma_s": "SoA, records, declaration: no model text",
        "ia_decide": "decides", "ia_redacta": "drafts",
        "ia_agente": "12 active agents", "ia_agente_s": "project context",
        "ia_json": "Structured output", "ia_json_s": "schema-bound JSON",
        "ia_ok": "valid", "ia_retry": "3 retries", "ia_plant": "Fallback template",
        "ia_marca": "generado_por", "ia_marca_s": "model · template · no key",
        "ia_ui": "The UI warns when the text is not from the model",
        "ia_guard": ["temperature ≤ 0.2", "citations required", "prompt-injection guard",
                     "client tone filter", "cost of every call logged"],
        "seg_titulo": "Defence in depth",
        "seg": [("Identity", "WebAuthn or TOTP · client MFA · Ed25519 links with OTP"),
                ("Session", "Ed25519 JWT in httpOnly cookie · per-request CSRF"),
                ("Isolation", "RLS on 185 of 253 tables · 192 policies · non-superuser role"),
                ("Integrity", "audit log with SHA-256 hash chain · no UPDATE or DELETE"),
                ("Custody", "antivirus · SHA-256 · Ed25519 signature · 7-year WORM"),
                ("Operations", "encrypted backups · ENS Medium monitor on itself")],
    },
}


# ────────────────────────────── diagramas ──────────────────────────────
def hero(lengua):
    x = TX[lengua]
    w, h = 1200, 400
    partes = [
        '<circle cx="980" cy="70" r="260" fill="url(#halo)"><animate attributeName="opacity" '
        'values=".5;1;.5" dur="7s" repeatCount="indefinite"/></circle>',
        '<circle cx="160" cy="380" r="220" fill="url(#halo)" opacity=".6"><animate attributeName="opacity" '
        'values=".8;.35;.8" dur="9s" repeatCount="indefinite"/></circle>',
        logo(56, 44, 0.9),
        t(150, 104, "fulkro", 58, peso=800, extra='letter-spacing="-1"'),
        t(60, 168, x["hero_t"], 28, peso=700),
        t(60, 204, x["hero_s"], 18, "suave"),
        t(60, 236, x["hero_c"], 15, "tenue", fuente=MONO),
    ]
    fases = FASES[lengua]
    n, x0, paso, y = len(fases), 60, 158, 318
    partes.append(f'<line x1="{x0 + 60}" y1="{y}" x2="{x0 + 60 + paso * (n - 1)}" y2="{y}" '
                  f'stroke="{C["borde"]}" stroke-width="3"/>')
    ciclo = 7.0
    camino = f"M{x0 + 60},{y} L{x0 + 60 + paso * (n - 1)},{y}"
    partes.append(particula(camino, ciclo, 0, "rosa", 6))
    for i, (nombre, motor, _) in enumerate(fases):
        cx = x0 + 60 + paso * i
        b = i * ciclo / n
        partes.append(
            f'<g><rect x="{cx - 66}" y="{y - 26}" width="132" height="52" rx="26" fill="{C["caja"]}" '
            f'stroke="{C["borde"]}" stroke-width="1.5"><animate attributeName="stroke" '
            f'values="{C["borde"]};{C["rosa"]};{C["borde"]}" keyTimes="0;.12;.3" dur="{ciclo}s" '
            f'begin="{b}s" repeatCount="indefinite"/></rect>'
            f'{t(cx, y - 3, nombre, 14, peso=600, ancla="middle")}'
            f'{t(cx, y + 15, motor, 11, "tenue", ancla="middle", fuente=MONO)}</g>')
    return lienzo(w, h, "\n".join(partes), "Fulkro")


def arquitectura(lengua):
    x = TX[lengua]
    w, h = 1200, 900
    p = [t(40, 52, x["arq_titulo"], 24, peso=700), t(40, 92, x["quien"], 12, "tenue", 700,
                                                        extra='letter-spacing="2"')]
    for i, (nom, sub) in enumerate(x["portales"]):
        bx = 40 + i * 282
        p += [caja(bx, 104, 266, 70), f'<rect x="{bx}" y="104" width="5" height="70" rx="2.5" fill="url(#marca)"/>',
              t(bx + 20, 134, nom, 17, peso=700), t(bx + 20, 158, sub, 13, "suave")]
        p.append(flujo(bx + 133, 176, bx + 133, 206, 1.4))
    p += [caja(40, 208, 1120, 50), t(600, 239, x["front"], 16, peso=600, ancla="middle")]
    p.append(flujo(600, 260, 600, 290))
    p += [caja(40, 292, 1120, 50, relleno="#241b52", borde=C["v1"]),
          t(600, 323, x["puerta"], 14.5, peso=600, ancla="middle")]
    p.append(flujo(600, 344, 600, 374))
    p += [caja(40, 376, 1120, 300), t(64, 410, x["api"], 18, peso=700)]
    for gi, (grupo, chips) in enumerate(x["grupos"]):
        gx = 64 + gi * 272
        p += [t(gx, 446, grupo.upper(), 12, "v2", 700, extra='letter-spacing="1.5"')]
        dos = len(chips) > 4
        for ci, chip in enumerate(chips):
            col, fil = (ci // 4, ci % 4) if dos else (0, ci)
            ancho = 119 if dos else 248
            cx, cy = gx + col * 129, 460 + fil * 52
            p += [caja(cx, cy, ancho, 44, r=8, relleno="#251f4a"),
                  t(cx + 12, cy + 27, chip, 13 if dos else 13.5, "suave")]
    p.append(flujo(600, 678, 600, 708))
    p += [caja(40, 710, 1120, 46), t(600, 739, x["asinc"], 15, "suave", 500, ancla="middle")]
    for i, (nom, sub) in enumerate(x["datos"]):
        bx = 40 + i * 378
        p.append(flujo(bx + 181, 758, bx + 181, 786, 1.8))
        p += [caja(bx, 788, 362, 78), t(bx + 22, 820, nom, 17, peso=700), t(bx + 22, 846, sub, 13.5, "suave")]
    return lienzo(w, h, "\n".join(p), x["arq_titulo"])


def ciclo(lengua):
    x, fases = TX[lengua], FASES[lengua]
    w, h = 1200, 330
    p = [t(40, 52, x["ciclo_titulo"], 22, peso=700)]
    n, x0, ancho, hueco, y = len(fases), 40, 142, 21, 96
    dur = 8.4
    for i, (nombre, motor, entrega) in enumerate(fases):
        bx = x0 + i * (ancho + hueco)
        b = i * dur / n
        p.append(
            f'<rect x="{bx}" y="{y}" width="{ancho}" height="176" rx="14" fill="{C["caja"]}" '
            f'stroke="{C["borde"]}" stroke-width="1.5"><animate attributeName="stroke" '
            f'values="{C["borde"]};{C["rosa"]};{C["borde"]}" keyTimes="0;.1;.28" dur="{dur}s" '
            f'begin="{b}s" repeatCount="indefinite"/></rect>')
        p += [f'<circle cx="{bx + 30}" cy="{y + 32}" r="16" fill="url(#marca)"/>',
              t(bx + 30, y + 38, str(i + 1), 15, peso=800, ancla="middle"),
              t(bx + 14, y + 82, nombre, 14, peso=700),
              t(bx + 14, y + 104, f'{x["motor"]} {motor}', 12, "tenue", fuente=MONO)]
        palabras = entrega.split(" · ")
        for k, trozo in enumerate(palabras):
            p.append(t(bx + 14, y + 138 + k * 18, trozo, 12.5, "suave"))
        if i < n - 1:
            gx = bx + ancho + hueco / 2
            p += [f'<rect x="{gx - 7}" y="{y + 81}" width="14" height="14" rx="3" '
                  f'transform="rotate(45 {gx} {y + 88})" fill="{C["v1"]}"/>']
    p.append(t(600, 306, "◆ = " + x["puerta_fase"], 12, "tenue", ancla="middle"))
    return lienzo(w, h, "\n".join(p), x["ciclo_titulo"])


def rag(lengua):
    x = TX[lengua]
    w, h = 1200, 700
    p = [t(40, 52, x["rag_titulo"], 22, peso=700)]

    def fila(y, etiqueta, pasos, dur, color):
        out = [t(40, y - 14, etiqueta, 12, "tenue", 700, extra='letter-spacing="2"')]
        n = len(pasos)
        ancho = (1120 - (n - 1) * 22) / n
        for i, (a, b, c) in enumerate(pasos):
            bx = 40 + i * (ancho + 22)
            out += [caja(bx, y, ancho, 104), t(bx + 14, y + 30, a, 15, peso=700),
                    t(bx + 14, y + 56, b, 13, "suave"), t(bx + 14, y + 78, c, 13, "suave")]
            if i < n - 1:
                out.append(flujo(bx + ancho + 2, y + 52, bx + ancho + 20, y + 52, 1.2))
        camino = f"M40,{y + 118} L1160,{y + 118}"
        out += [f'<line x1="40" y1="{y + 118}" x2="1160" y2="{y + 118}" stroke="{C["borde"]}" '
                f'stroke-width="2" stroke-dasharray="2 6"/>', particula(camino, dur, 0, color),
                particula(camino, dur, dur / 2, color)]
        return out

    p += fila(110, x["ingesta"], x["ing"], 6, "v2")
    p += fila(290, x["consulta"], x["con"], 5, "rosa")
    p.append(f'<path d="M1056,216 C1056,262 505,244 505,286" stroke="{C["v2"]}" stroke-width="2" '
             f'fill="none" stroke-dasharray="6 7" marker-end="url(#flecha)" opacity=".7">'
             f'<animate attributeName="stroke-dashoffset" from="26" to="0" dur="1.6s" repeatCount="indefinite"/></path>')
    p += [caja(40, 470, 1120, 196, relleno="#18142f", borde=C["v1"]),
          t(64, 506, x["eval_t"], 12, "v2", 700, extra='letter-spacing="2"')]
    for i, (k, v) in enumerate(x["eval"]):
        bx = 64 + i * 250
        p += [t(bx, 572, v, 44, peso=800), t(bx, 600, k, 14, "suave", fuente=MONO)]
    p += [t(840, 548, "recall@5", 13, "tenue", fuente=MONO)]
    barras = [("vec", 0.824, C["verde"]), ("rrf", 0.667, C["tenue"])]
    for i, (nom, v, col) in enumerate(barras):
        by = 560 + i * 30
        p += [t(840, by + 14, nom, 12, "tenue", fuente=MONO),
              f'<rect x="880" y="{by}" width="0" height="18" rx="4" fill="{col}">'
              f'<animate attributeName="width" from="0" to="{int(260 * v)}" dur="1.6s" fill="freeze" begin="{0.3 + i * .3}s"/></rect>',
              t(880 + int(260 * v) + 10, by + 14, f"{v:.3f}".replace(".", "," if lengua == "es" else "."), 12, "suave", fuente=MONO)]
    p.append(t(64, 640, x["eval_n"], 14, "suave"))
    return lienzo(w, h, "\n".join(p), x["rag_titulo"])


def ia(lengua):
    x = TX[lengua]
    w, h = 1200, 520
    p = [t(40, 52, x["ia_titulo"], 22, peso=700)]
    # fila 1 · el motor decide
    p += [caja(40, 88, 330, 104), f'<rect x="40" y="88" width="5" height="104" rx="2.5" fill="{C["verde"]}"/>',
          t(64, 126, x["ia_motor"], 18, peso=700), t(64, 152, x["ia_motor_s"], 14, "suave"),
          t(64, 176, "R1 · " + x["ia_decide"], 13, "verde", fuente=MONO)]
    p.append(flujo(372, 140, 426, 140))
    p += [caja(428, 88, 300, 104), t(448, 126, x["ia_dec"], 17, peso=700), t(448, 152, x["ia_dec_s"], 13.5, "suave")]
    p.append(flujo(730, 140, 784, 140))
    p += [caja(786, 88, 374, 104, relleno="#16302a", borde=C["verde"]),
          t(806, 126, x["ia_firma"], 17, peso=700), t(806, 152, x["ia_firma_s"], 13.5, "suave")]
    p.append(particula("M372,140 L786,140", 3.0, 0, "verde"))
    # fila 2 · el modelo redacta
    p += [caja(40, 226, 330, 104), '<rect x="40" y="226" width="5" height="104" rx="2.5" fill="url(#marca)"/>',
          t(64, 264, x["ia_agente"], 18, peso=700), t(64, 290, x["ia_agente_s"], 14, "suave"),
          t(64, 314, "R2 · R3 · " + x["ia_redacta"], 13, "rosa", fuente=MONO)]
    p.append(flujo(372, 278, 426, 278))
    p += [caja(428, 226, 300, 104), t(448, 264, x["ia_json"], 17, peso=700), t(448, 290, x["ia_json_s"], 14, "suave")]
    p.append(flujo(730, 278, 784, 278))
    p.append(t(738, 268, x["ia_ok"], 12, "verde", fuente=MONO))
    p += [caja(786, 226, 374, 104, relleno="#1f1845", borde=C["v2"]),
          t(806, 262, x["ia_marca"], 19, "v2", 700, fuente=MONO), t(806, 288, x["ia_marca_s"], 13.5, "suave"),
          t(806, 314, x["ia_ui"], 13.5, "texto")]
    p.append(particula("M372,278 L786,278", 3.0, 0.6, "rosa"))
    # reserva
    p += [f'<path d="M578,332 L578,366" stroke="{C["ambar"]}" stroke-width="2" stroke-dasharray="4 5" marker-end="url(#flecha)"/>',
          t(588, 354, x["ia_retry"], 12, "ambar", fuente=MONO),
          caja(428, 368, 300, 56, relleno="#2a2210", borde=C["ambar"]), t(448, 402, x["ia_plant"], 15, peso=600),
          f'<path d="M730,396 C770,396 770,340 800,332" stroke="{C["ambar"]}" stroke-width="2" fill="none" '
          f'stroke-dasharray="4 5" marker-end="url(#flecha)"/>']
    for i, chip in enumerate(x["ia_guard"]):
        bx = 40 + i * 226
        p += [caja(bx, 456, 214, 32, r=16, relleno="#241d4a"), t(bx + 107, 477, chip, 12.5, "suave", ancla="middle")]
    return lienzo(w, h, "\n".join(p), x["ia_titulo"])


def seguridad(lengua):
    x = TX[lengua]
    capas = x["seg"]
    colores = [C["v1"], C["v2"], C["rosa"], C["verde"], C["ambar"], C["suave"]]
    w, h = 1200, 120 + len(capas) * 62
    p = [t(40, 52, x["seg_titulo"], 22, peso=700)]
    fondo = 84 + len(capas) * 62 - 12
    p += [f'<line x1="70" y1="84" x2="70" y2="{fondo}" stroke="{C["borde"]}" stroke-width="2" stroke-dasharray="2 6"/>',
          particula(f"M70,78 L70,{fondo}", 4.5, 0, "rosa", 6)]
    for i, (nom, desc) in enumerate(capas):
        y = 84 + i * 62
        p += [f'<rect x="100" y="{y}" width="1060" height="50" rx="12" fill="{C["caja"]}" stroke="{C["borde"]}" '
              f'stroke-width="1.5"><animate attributeName="stroke" values="{C["borde"]};{colores[i]};{C["borde"]}" '
              f'keyTimes="0;.12;.3" dur="4.5s" begin="{i * 0.75}s" repeatCount="indefinite"/></rect>',
              f'<rect x="100" y="{y}" width="6" height="50" rx="3" fill="{colores[i]}"/>',
              f'<circle cx="70" cy="{y + 25}" r="7" fill="{C["fondo1"]}" stroke="{colores[i]}" stroke-width="2"/>',
              t(126, y + 31, nom, 16, peso=700), t(290, y + 31, desc, 14.5, "suave")]
    return lienzo(w, h, "\n".join(p), x["seg_titulo"])


DIAGRAMAS = {"hero": hero, "arquitectura": arquitectura, "ciclo": ciclo, "rag": rag,
             "ia": ia, "seguridad": seguridad}

if __name__ == "__main__":
    for lengua in ("es", "en"):
        d = SALIDA / lengua
        d.mkdir(parents=True, exist_ok=True)
        for nombre, fn in DIAGRAMAS.items():
            (d / f"{nombre}.svg").write_text(fn(lengua), encoding="utf-8")
            print(d / f"{nombre}.svg")
