#!/usr/bin/env python3
"""Convierte `var/recorrido/recorrido.json` en `docs/RECORRIDO_COMPLETO.md`.

El arnes (`scripts/recorrer_todo.cjs`) MIDE; este fichero solo REDACTA. Estan
separados a proposito: asi no hay ni una cifra del informe que no venga de una
medida, y volver a redactar no exige volver a recorrer 167 paginas.

Uso:  python3 scripts/recorrido_informe.py
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / "var" / "recorrido" / "recorrido.json"
BLANCA = RAIZ / "docs" / "recorrido" / "lista_blanca_vacias.json"
# Preambulo escrito a mano. Las TABLAS las genera la medida; el JUICIO sobre lo
# que significan lo escribe una persona, y conviene que se vea cual es cual.
# Si no existe, el informe sale solo con las tablas y lo dice.
HALLAZGOS = RAIZ / "docs" / "recorrido" / "hallazgos.md"
SALIDA = RAIZ / "docs" / "RECORRIDO_COMPLETO.md"

ETIQUETA = {
    "verificada": "verificada",
    "verificada-con-incidencia": "verificada · con incidencia",
    "rebote-esperado": "te echa, y debe echarte",
    "vacia-justificada": "vacía justificada",
    "vacia": "VACÍA SIN JUSTIFICAR",
    "fallida": "FALLIDA",
    "no-verificada": "NO VERIFICADA",
}
SIMBOLO = {
    "verificada": "ok",
    "verificada-con-incidencia": "ok·inc",
    "rebote-esperado": "echa·ok",
    "vacia-justificada": "vacía·ok",
    "vacia": "VACÍA",
    "fallida": "FALLO",
    "no-verificada": "NO VERIF",
}


def tabla(filas: list[list[str]], cabecera: list[str]) -> str:
    """Tabla Markdown sencilla (sin alinear: el ancho lo pone el contenido)."""
    out = ["| " + " | ".join(cabecera) + " |",
           "|" + "|".join(["---"] * len(cabecera)) + "|"]
    for f in filas:
        out.append("| " + " | ".join(str(c).replace("|", "\\|") for c in f) + " |")
    return "\n".join(out)


def main() -> None:
    if not ENTRADA.exists():
        raise SystemExit(f"No existe {ENTRADA}. Ejecuta 'make recorrer-todo' primero.")
    d = json.loads(ENTRADA.read_text(encoding="utf-8"))
    blanca = json.loads(BLANCA.read_text(encoding="utf-8")) if BLANCA.exists() else {}
    res = d["resultados"]

    # La lista blanca se aplica AQUI ademas de en el arnes, y por un motivo
    # practico: la lista se escribe DESPUES de la primera medicion (hay que ver
    # que paginas salen vacias para poder justificarlas una a una), asi que la
    # medida guardada puede ser anterior al fichero. Es la MISMA regla y el
    # MISMO fichero que aplica `scripts/recorrer_todo.cjs` al medir, de modo que
    # la siguiente ejecucion de `make recorrer-todo` da exactamente estos
    # numeros por si sola.
    #
    # Solo puede ASCENDER una "vacia" a "vacia justificada". Nunca toca una
    # fallida ni una no verificada: si la lista blanca pudiera tapar un fallo,
    # seria el agujero por el que se cuela justo lo que este bloque persigue.
    reclasificadas = 0
    for r in res:
        if r["estado"] == "vacia" and r["patron"] in blanca:
            r["estado"] = "vacia-justificada"
            r["razones"] = [blanca[r["patron"]]]
            reclasificadas += 1

    def cuenta(estado: str) -> int:
        return sum(1 for r in res if r["estado"] == estado)

    verificadas = (cuenta("verificada") + cuenta("verificada-con-incidencia")
                   + cuenta("vacia-justificada") + cuenta("rebote-esperado"))
    no_verificadas = cuenta("no-verificada")
    fallidas = cuenta("fallida") + cuenta("vacia")

    L: list[str] = []
    A = L.append

    A("# Recorrido completo de la aplicación")
    A("")
    A(f"**Generado**: {d['generado']} · **Duración**: {d['duracionSegundos']} s · "
      f"**Contra**: {d['base']}")
    A("")
    A("Reproducirlo entero:")
    A("")
    A("```")
    A("make demo && make recorrer-todo")
    A("```")
    A("")
    A("> La regla que manda sobre todas las demás en este documento: **una página "
      "que carga no es una página que funciona.** Un HTTP 200 lo devuelve igual "
      "una pantalla llena de datos que un cascarón que dice «no hay nada». Aquí "
      "no se mide *responde*: se mide **qué se ve**, **qué falla por debajo** y "
      "**si alguien puede llegar pinchando**.")
    A("")

    if HALLAZGOS.exists():
        A(HALLAZGOS.read_text(encoding="utf-8").strip())
        A("")
        A("---")
        A("")

    # ── los tres números ────────────────────────────────────────────────────
    A("## Los tres números")
    A("")
    A(tabla([
        ["**Verificadas**", verificadas,
         "se abrieron con la persona dueña y traen contenido real "
         "(incluye las vacías justificadas una a una)"],
        ["**No verificadas por falta de dato**", no_verificadas,
         "no había dato sembrado con el que resolver la ruta · **jamás cuentan "
         "como aprobadas**"],
        ["**Fallidas**", fallidas,
         "no se abren, rebotan, revientan, o renderizan un estado vacío sin "
         "justificar"],
    ], ["", "Páginas", "Qué significa"]))
    A("")
    A(f"Total del inventario: **{d['inventario']['total']}** páginas, de las que "
      f"**{d['inventario']['dinamicas']}** llevan parámetro en la ruta.")
    A("")

    # ── inventario ──────────────────────────────────────────────────────────
    A("## 1 · El inventario es el árbol, no una lista")
    A("")
    A("Las rutas no están escritas a mano en ningún sitio: se **derivan** de "
      "`frontend/app` recorriendo cada `page.tsx` y quitando los grupos de ruta "
      "`(nombre)`, que organizan ficheros pero no aparecen en la URL. "
      "Escribir la lista a mano es exactamente como se llega a un informe que "
      "recorre 40 URL inventadas y declara «todo verde»: lo que no está en la "
      "lista no falla nunca. Con la lista derivada, una página nueva entra sola "
      "en el recorrido y una borrada desaparece sola.")
    A("")
    A(tabla([[g, n] for g, n in sorted(d["inventario"]["porGrupo"].items(),
                                       key=lambda x: -x[1])],
            ["Grupo de ruta", "Páginas"]))
    A("")

    sembrado = d["catalogo"]["sembradoPorElArnes"]
    sin_dato = d["catalogo"]["sinDato"]
    A("### Los identificadores de las 83 rutas dinámicas")
    A("")
    A("Una ruta con `[id]` no se puede recorrer sin un identificador que **exista** "
      "en la base. Inventarse un UUID no vale: la pantalla de «no encontrado» "
      "devuelve HTTP 200 y la ruta entraría en verde sin haberse comprobado. Por "
      "eso hay un catálogo (`scripts/recorrido_identificadores.py`) que lee la "
      "base y, para los portales por token, **acuña enlaces de verdad** con el "
      "mismo servicio que usa la aplicación: el token y su código de un solo uso "
      "son los que recibiría una persona real.")
    A("")
    if sembrado:
        A("**Tres familias de rutas no tenían ni un dato con el que recorrerlas.** "
          "El arnés las siembra por la vía de servicio de la propia aplicación, y "
          "queda dicho aquí porque es un hallazgo sobre el sembrado del demo, no "
          "un detalle de fontanería: `make demo` deja estas páginas sin nada que "
          "enseñar.")
        A("")
        A(tabla([[f"`{k}`", v] for k, v in sorted(sembrado.items())],
                ["Identificador", "Cómo se obtiene y por qué hizo falta"]))
        A("")
    if sin_dato:
        A("Y estas no se pudieron resolver ni sembrando — sus páginas van a **NO "
          "VERIFICADA**:")
        A("")
        A(tabla([[f"`{k}`", v] for k, v in sorted(sin_dato.items())],
                ["Identificador", "Motivo"]))
        A("")
    else:
        A("No queda ningún identificador sin resolver: las 83 rutas dinámicas se "
          "recorren contra dato real.")
        A("")

    # ── resultados por grupo ────────────────────────────────────────────────
    A("## 2 · Resultado página a página")
    A("")
    A("`ok` = contenido real · `ok·inc` = se ve, pero algo falló por debajo · "
      "`vacía·ok` = vacía y justificada abajo · `VACÍA` = dice «no hay datos» y "
      "**no aprueba** · `FALLO` = no se puede usar · `NO VERIF` = sin dato para "
      "resolver la ruta.")
    A("")
    por_grupo: dict[str, list] = defaultdict(list)
    for r in res:
        por_grupo[r["grupo"]].append(r)

    for grupo in sorted(por_grupo, key=lambda g: -len(por_grupo[g])):
        filas = []
        for r in sorted(por_grupo[grupo], key=lambda x: x["patron"]):
            nota = r["razones"][0] if r["razones"] else ""
            filas.append([f"`{r['patron']}`", r["persona"],
                          SIMBOLO[r["estado"]], nota[:150]])
        n_ok = sum(1 for r in por_grupo[grupo]
                   if r["estado"].startswith("verificada")
                   or r["estado"] in ("vacia-justificada", "rebote-esperado"))
        A(f"### `{grupo}` · {n_ok}/{len(por_grupo[grupo])}")
        A("")
        A(tabla(filas, ["Ruta", "Persona", "", "Nota"]))
        A("")

    # ── vacías ──────────────────────────────────────────────────────────────
    A("## 3 · El criterio anti vacuidad")
    A("")
    A("Una página que renderiza «no hay datos» **no pasa**. Es la misma "
      "enfermedad de siempre: tiene forma de comprobación y no comprueba nada. "
      "Cada página clasificada como vacía tiene que estar en una lista blanca "
      "**con su motivo escrito una a una**, o cuenta como fallo.")
    A("")
    justificadas = [r for r in res if r["estado"] == "vacia-justificada"]
    sin_justificar = [r for r in res if r["estado"] == "vacia"]
    if justificadas:
        A(f"### Lista blanca · {len(justificadas)} páginas legítimamente vacías")
        A("")
        A("Fuente: `docs/recorrido/lista_blanca_vacias.json`.")
        A("")
        A(tabla([[f"`{r['patron']}`", blanca.get(r["patron"], r["razones"][0])]
                 for r in sorted(justificadas, key=lambda x: x["patron"])],
                ["Ruta", "Por qué está vacía a propósito"]))
        A("")
    A("**Cómo se decide, y dónde está el juicio.** Se mide dentro de `<main>` "
      "—no del `body`— porque la barra lateral y la cabecera son marco, no "
      "contenido: en la primera pasada, clasificar sobre el `body` entero contó "
      "33 páginas vacías donde no las había (basta un widget lateral que diga "
      "«Sin datos» para condenar una página con tres tarjetas de normativa). "
      "Una página se declara vacía si `<main>` no tiene filas de tabla, ni "
      "celdas, ni campos de formulario y baja de 900 caracteres; o si anuncia "
      "que está vacía y además `<main>` no llega a 1.200 caracteres. **Ese "
      "1.200 es un juicio, no una medida**, y por eso la tabla de abajo publica "
      "las señales de cada página: para que se pueda discutir el número en vez "
      "de tener que creérselo.")
    A("")
    if sin_justificar:
        A(f"### {len(sin_justificar)} páginas vacías SIN justificar")
        A("")
        A("Cada una de éstas es un defecto: o falta sembrado, o la pantalla no "
          "sabe pedir sus datos.")
        A("")
        A(tabla([[f"`{r['patron']}`", r["persona"],
                  (r.get("medida") or {}).get("senyales", {}).get("filas", "?"),
                  (r.get("medida") or {}).get("senyales", {}).get("caracteres", "?"),
                  r["razones"][0][:150]]
                 for r in sorted(sin_justificar, key=lambda x: x["patron"])],
                ["Ruta", "Persona", "Filas", "Car. en `<main>`", "Lo que se ve"]))
        A("")
    else:
        A("**No hay ninguna página vacía sin justificar.**")
        A("")

    rebotes = [r for r in res if r["estado"] == "rebote-esperado"]
    if rebotes:
        A(f"### {len(rebotes)} páginas que te echan a la entrada, y deben echarte")
        A("")
        A("Declaradas en `docs/recorrido/rebotes_esperados.json`. Es el **único** "
          "veredicto que admite declaración, y a propósito: hay páginas que deben "
          "echarte, pero ninguna que deba reventar. Un error de página o un HTTP "
          "4xx no se pueden declarar esperados por esta vía.")
        A("")
        A(tabla([[f"`{r['patron']}`", r["razones"][0]] for r in rebotes],
                ["Ruta", "Por qué echa, y por qué está bien"]))
        A("")

    # ── texto fabricado ─────────────────────────────────────────────────────
    A("### Texto fabricado en el DOM visible")
    A("")
    A("Se busca en cada página: `[MOCK]`, `undefined`, `NaN`, `null`, `lorem`, "
      "`TODO`, `FIXME`. `[MOCK]` está el primero por un motivo concreto: así "
      "apareció «[MOCK] Agent 12» bajo el rótulo «Sugerencia IA» en la portada "
      "del cliente. La comprobación se queda aquí para siempre.")
    A("")
    fabricados = [(r, h) for r in res
                  for h in (r.get("medida") or {}).get("fabricado", [])]
    if fabricados:
        A(tabla([[f"`{r['patron']}`", f"`{h['patron']}`", f"…{h['contexto']}…"]
                 for r, h in fabricados[:60]],
                ["Ruta", "Patrón", "Contexto en pantalla"]))
        A("")
    else:
        A("**Cero apariciones.** Ninguna de las 167 páginas enseña texto "
          "fabricado.")
        A("")

    # ── expectativas ────────────────────────────────────────────────────────
    A("## 4 · Tabla de expectativas · un 403 esperado es un resultado correcto")
    A("")
    A("Lo de arriba comprueba que la puerta de cada persona **se abre** para "
      "ella. Esto comprueba lo contrario: que está **cerrada** para las demás. "
      "Que el cliente reboto a su pantalla de entrada al pedir una página de "
      "administrador no es un fallo del recorrido; es el resultado que se "
      "esperaba. Lo que sería un fallo es que se abriera.")
    A("")
    exp = d.get("expectativas") or []
    if exp:
        A(tabla([[e["persona"], f"`{e['ruta']}`", e["esperado"], e["observado"],
                  "correcto" if e["correcto"] else "**HUECO**"] for e in exp],
                ["Persona", "Ruta (dueño: otra persona)", "Esperado", "Observado", ""]))
        A("")
        huecos = [e for e in exp if not e["correcto"]]
        if huecos:
            A(f"**{len(huecos)} huecos de aislamiento.** Una página que se abre "
              "para quien no es su dueño no es un fallo de esta tabla: es un "
              "agujero de autorización.")
        else:
            A("Sin huecos: todas las puertas cerradas se comportan como debían.")
        A("")

    # ── alcanzabilidad ──────────────────────────────────────────────────────
    A("## 5 · Alcanzabilidad · «¿lo puede usar alguien de fuera?», medido")
    A("")
    alc = d.get("alcance")
    if not alc:
        A("No medido en esta ejecución (`RECORRIDO_SIN_BFS=1`).")
        A("")
    else:
        total = d["inventario"]["total"]
        A(f"Recorriendo en anchura los enlaces desde la portada de cada persona "
          f"se abrieron **{alc['abiertas']}** páginas.")
        A("")
        A(tabla([
            ["Se alcanzan pinchando", len(alc["alcanzados"]),
             f"de {total} páginas del inventario"],
            ["**Huérfanas**", len(alc["huerfanas"]),
             "existen, pero **no las enlaza nadie**"],
            ["Sólo por enlace de correo", len(alc["porToken"]),
             "portales por token · no se llega pinchando **por diseño**, "
             "no se cuentan como huérfanas"],
            ["Enlaces rotos", len(alc["rotos"]), "apuntan a un 404"],
        ], ["", "Número", ""]))
        A("")
        A("Las huérfanas son el defecto que apareció a mano con el alta de "
          "cliente —la página estaba entera y no había **un solo enlace** que "
          "llevara a ella—, ahora contado. Y al revés: los enlaces rotos son los "
          "que sí están y no llevan a ninguna parte.")
        A("")
        if alc["huerfanas"]:
            A(f"### Las {len(alc['huerfanas'])} huérfanas")
            A("")
            for p in sorted(alc["huerfanas"]):
                A(f"- `{p}`")
            A("")
        if alc["rotos"]:
            A(f"### Los {len(alc['rotos'])} enlaces a 404")
            A("")
            A(tabla([[f"`{x['url']}`", x["http"], x.get("persona", "")]
                     for x in alc["rotos"][:40]],
                    ["URL", "HTTP", "Persona"]))
            A("")

    # ── fallos ──────────────────────────────────────────────────────────────
    A("## 6 · Fallos e incidencias, uno a uno")
    A("")
    A("El criterio de cierre exige **cero fallos sin explicar**. No cero fallos: "
      "cero fallos *sin explicar*. Una incidencia que se deja sin explicación "
      "cuenta como fallo.")
    A("")
    fallos = [r for r in res if r["estado"] == "fallida"]
    if fallos:
        A(f"### {len(fallos)} páginas fallidas")
        A("")
        A(tabla([[f"`{r['patron']}`", r["persona"], "; ".join(r["razones"])[:200]]
                 for r in fallos], ["Ruta", "Persona", "Por qué"]))
        A("")
    else:
        A("**Ninguna página fallida.**")
        A("")
    incid = [r for r in res if r["estado"] == "verificada-con-incidencia"]
    if incid:
        A(f"### {len(incid)} páginas que se ven pero tienen algo roto por debajo")
        A("")
        A(tabla([[f"`{r['patron']}`", r["persona"],
                  "; ".join(r.get("incidencias", []))[:200]] for r in incid],
                ["Ruta", "Persona", "Incidencia"]))
        A("")

    A("---")
    A("")
    A("**Capturas de pantalla**: `var/recorrido/capturas/` (una por página). "
      "**Medida en bruto**: `var/recorrido/recorrido.json`. "
      "**El arnés**: `scripts/recorrer_todo.cjs`.")
    A("")

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text("\n".join(L), encoding="utf-8")
    print(f"Escrito {SALIDA.relative_to(RAIZ)} "
          f"({verificadas} verificadas · {no_verificadas} no verificadas · "
          f"{fallidas} fallidas)")


if __name__ == "__main__":
    main()
