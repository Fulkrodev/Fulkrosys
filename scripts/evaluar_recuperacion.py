#!/usr/bin/env python3
"""Evalua la recuperacion del corpus: lexica, vectorial y la fusion RRF.

DOS METRICAS DISTINTAS, Y NO SON LO MISMO
  - hitrate@k: fraccion de CONSULTAS con AL MENOS un fragmento relevante en el
    top-k. Es 0 o 1 por consulta. Responde «¿le llego algo util al modelo?».
  - recall@k: fraccion media de los RELEVANTES DE CADA CONSULTA que caen en el
    top-k. Responde «¿le llego TODO lo util?».
  Con 96 etiquetas sobre 49 consultas (1,96 relevantes de media, hasta 4 en
  algunas) los dos numeros divergen: una consulta con 4 relevantes de los que
  entra 1 en el top-5 puntua hitrate@5 = 1,000 y recall@5 = 0,250. Hasta
  2026-09-11 el informe llamaba «acierto@k» al primero, que no distinguia.

QUE MIDE
  - hitrate@k, recall@k (k = 1, 3, 5, 10) y MRR, para las ramas por separado:
    lexica sola, vectorial sola y la fusion RRF, mas las variantes de
    diagnostico (el analizador AND anterior y el barrido de peso).
  - un barrido de RRF_K con intervalo de confianza por remuestreo (bootstrap)
    sobre las consultas.
  - la latencia de una busqueda completa, desglosada por etapa.
  - si los embeddings guardados llevan el prefijo 'passage: ' que espera e5, y
    cuanto costaria en recall@5 que no lo llevaran.

QUE **NO** MIDE
  - la calidad de la RESPUESTA del modelo. Esto mide que fragmentos llegan al
    modelo, no que hace el modelo con ellos.
  - nada fuera de las 49 consultas etiquetadas. Son 49 y no 50 porque el
    conjunto tiene 50 y una (dora-03, el plazo de notificacion de incidentes
    TIC) NO tiene respuesta en el corpus: el art. 19 de DORA que hay indexado
    remite los plazos a normas tecnicas que no estan. Se marca
    `sin_relevante: true` y se excluye, en vez de reescribirla para que encaje.
    El denominador de TODAS las cifras del informe es 49.
    49 consultas es una muestra pequeña: los intervalos de confianza que imprime
    son anchos a proposito, para que no se lean como precision que no hay.
  - la relevancia graduada. Es binaria (ver el porque en docs/EVAL_RECUPERACION.md).

Se ejecuta DENTRO del contenedor del backend (necesita fastembed y la base):
    make eval-recuperacion
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, "/app")

import numpy as np
import psycopg2
import yaml

from backend.app.core.ai.embeddings import get_default_embedding_provider

# Las mismas constantes que usa la aplicacion (backend/app/corpus/retrieval.py).
# k de la fusion RRF. Desde 2026-09-11 la fusion NO corre en produccion (se
# midio que perdia; ver el docstring de backend/app/corpus/retrieval.py). Se
# conserva aqui, y con el las ramas `lexico`, `lexico_and`, `rrf` y `rrf_and`,
# porque este arnes es justamente lo que debe volver a responder la pregunta
# cuando el corpus crezca o cambie el modelo de embeddings. Medir la rama que
# se quito es la unica forma de saber cuando habria que devolverla.
RRF_K_PRODUCCION = 60
LEXICO_TOP = 30
VECTOR_TOP = 30
E5_QUERY_PREFIX = "query: "
E5_PASSAGE_PREFIX = "passage: "

KS = (1, 3, 5, 10)
BARRIDO_K = (1, 5, 10, 20, 30, 60, 100, 200)
# Peso de la rama LEXICA en la fusion ponderada. w = 0,5 es el RRF clasico
# (las dos ramas pesan igual); w = 0 es BORRAR la fusion y quedarse con el
# vector; w = 1 es quedarse solo con la rama lexica. Se barre para que la
# decision «¿se sostiene la fusion?» sea un punto de una curva medida y no un
# binario decidido a ojo.
BARRIDO_W = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
BOOTSTRAP_N = 1000
SEMILLA = 20260910


# ---------------------------------------------------------------------------
# Acceso a datos
# ---------------------------------------------------------------------------
def conectar():
    url = os.environ.get("DATABASE_URL_SYNC") or os.environ["DATABASE_URL"]
    return psycopg2.connect(url.replace("postgresql+asyncpg", "postgresql"))


def normaliza(v):
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v] if n > 0 else v


def lexico(cur, consulta: str, top: int) -> list[str]:
    """La rama lexica TAL COMO CORRE EN PRODUCCION desde 2026-09-11.

    Misma expresion que `_LEXICO_TSQUERY` en backend/app/corpus/retrieval.py:
    se reescribe el operador del tsquery ya analizado para unir los lexemas con
    OR. Si esta funcion y aquella dejan de coincidir, este arnes mide otra cosa
    distinta de la que sirve el producto.
    """
    tsq = "replace(plainto_tsquery('spanish', %s)::text, '&', '|')::tsquery"
    cur.execute(
        f"SELECT c.id::text FROM knowledge_chunks c "
        f"WHERE c.content_tsvector @@ {tsq} "
        f"ORDER BY ts_rank_cd(c.content_tsvector, {tsq}) DESC "
        f"LIMIT %s",
        (consulta, consulta, top),
    )
    return [r[0] for r in cur.fetchall()]


def lexico_and(cur, consulta: str, top: int) -> list[str]:
    """El ANTES: `plainto_tsquery` a pelo, que une TODOS los lexemas con AND.

    Se conserva para poder publicar el antes y el despues del mismo defecto en
    la misma tabla, no porque nadie deba volver a usarlo.
    """
    cur.execute(
        "SELECT c.id::text FROM knowledge_chunks c "
        "WHERE c.content_tsvector @@ plainto_tsquery('spanish', %s) "
        "ORDER BY ts_rank_cd(c.content_tsvector, plainto_tsquery('spanish', %s)) DESC "
        "LIMIT %s",
        (consulta, consulta, top),
    )
    return [r[0] for r in cur.fetchall()]


def vectorial(cur, emb: list[float], top: int) -> list[str]:
    """Igual que _vector_search: distancia coseno de pgvector."""
    cur.execute(
        "SELECT c.id::text FROM knowledge_chunks c WHERE c.embedding IS NOT NULL "
        "ORDER BY c.embedding <=> %s::vector LIMIT %s",
        (str(emb), top),
    )
    return [r[0] for r in cur.fetchall()]


def rrf(lista_lex: list[str], lista_vec: list[str], k: int,
        w_lex: float = 0.5) -> tuple[list[str], dict]:
    """Fusion RRF ponderada: score(d) = w/(k+rango_lex) + (1-w)/(k+rango_vec).

    Con w = 0,5 es el RRF clasico salvo un factor 2 global, que no cambia NINGUN
    orden: es la misma fusion que corre en produccion. w = 0 deja solo el vector
    (equivale a borrar la fusion) y w = 1 deja solo la rama lexica.

    El desempate es por id, para que el resultado no dependa del orden de
    iteracion de un conjunto de Python (seria irreproducible entre ejecuciones).
    """
    r_le = {c: i + 1 for i, c in enumerate(lista_lex)}
    r_ve = {c: i + 1 for i, c in enumerate(lista_vec)}
    puntos = {}
    for c in set(r_le) | set(r_ve):
        s = 0.0
        if c in r_le:
            s += w_lex / (k + r_le[c])
        if c in r_ve:
            s += (1.0 - w_lex) / (k + r_ve[c])
        puntos[c] = s
    return sorted(puntos, key=lambda c: (-puntos[c], c)), puntos


# ---------------------------------------------------------------------------
# Metricas
# ---------------------------------------------------------------------------
def metricas_una(ordenados: list[str], relevantes: set[str]) -> dict:
    """hitrate@k, recall@k y RR de UNA consulta.

    hitrate@k: 1 si hay AL MENOS un relevante en el top-k, 0 si no.
    recall@k:  que fraccion de LOS RELEVANTES DE ESTA CONSULTA cae en el top-k.
    No son la misma cifra en cuanto una consulta tiene mas de un relevante.
    """
    out = {}
    for k in KS:
        top = ordenados[:k]
        encontrados = len(set(top) & relevantes)
        out[f"hitrate@{k}"] = 1.0 if encontrados else 0.0
        out[f"recall@{k}"] = encontrados / len(relevantes)
    rr = 0.0
    for i, c in enumerate(ordenados, 1):
        if c in relevantes:
            rr = 1.0 / i
            break
    out["mrr"] = rr
    return out


def promedia(lista_de_dicts: list[dict]) -> dict:
    if not lista_de_dicts:
        return {}
    return {k: sum(d[k] for d in lista_de_dicts) / len(lista_de_dicts)
            for k in lista_de_dicts[0]}


def bootstrap_ic_pareado(a: list[float], b: list[float], n=BOOTSTRAP_N,
                         semilla=SEMILLA) -> dict:
    """IC de la DIFERENCIA a-b remuestreando las MISMAS consultas para las dos
    ramas. Comparar dos intervalos sueltos que se solapan no dice nada: las dos
    ramas se miden sobre las mismas 49 consultas, asi que la comparacion tiene
    que ser pareada o no es una comparacion."""
    rnd = random.Random(semilla)
    m = len(a)
    difs = []
    for _ in range(n):
        idx = [rnd.randrange(m) for _ in range(m)]
        difs.append(sum(a[i] - b[i] for i in idx) / m)
    difs.sort()
    lo, hi = difs[int(0.025 * n)], difs[int(0.975 * n)]
    return {"diferencia": sum(x - y for x, y in zip(a, b)) / m,
            "ic95": [lo, hi],
            "excluye_el_cero": bool(lo > 0 or hi < 0)}


def bootstrap_ic(valores: list[float], n=BOOTSTRAP_N, semilla=SEMILLA) -> tuple[float, float]:
    """IC percentil 2,5/97,5 remuestreando CONSULTAS con reemplazo."""
    if not valores:
        return (0.0, 0.0)
    rnd = random.Random(semilla)
    m = len(valores)
    medias = []
    for _ in range(n):
        medias.append(sum(valores[rnd.randrange(m)] for _ in range(m)) / m)
    medias.sort()
    return (medias[int(0.025 * n)], medias[int(0.975 * n)])


# ---------------------------------------------------------------------------
# F5 · prefijos de e5
# ---------------------------------------------------------------------------
def diagnostico_prefijo(cur, prov, muestra_por_fuente=3) -> dict:
    """¿Con que prefijo se embebio lo que hay GUARDADO? Se responde volviendo a
    embeber el contenido de tres formas y viendo cual da coseno ~1 con lo
    guardado. No es una lectura del codigo: es una medida sobre la base."""
    cur.execute(
        "SELECT c.id::text, COALESCE(s.code,'?'), c.content, c.embedding::text "
        "FROM knowledge_chunks c JOIN knowledge_documents d ON d.id=c.document_id "
        "LEFT JOIN knowledge_sources s ON s.id=d.source_id "
        "WHERE c.embedding IS NOT NULL ORDER BY s.code, c.id"
    )
    filas = cur.fetchall()
    por_fuente = {}
    for f in filas:
        por_fuente.setdefault(f[1], []).append(f)
    muestra = [f for v in por_fuente.values() for f in v[:muestra_por_fuente]]

    res = []
    for cid, fuente, cont, emb_txt in muestra:
        guardado = np.array(normaliza([float(x) for x in emb_txt.strip("[]").split(",")]))
        vs = prov.embed_documents([cont, E5_PASSAGE_PREFIX + cont, E5_QUERY_PREFIX + cont])
        cos = {n: float(guardado @ np.array(normaliza(v)))
               for n, v in zip(("sin", "passage", "query"), vs)}
        res.append({"fuente": fuente, "chunk": cid[:8], **cos,
                    "mejor": max(cos, key=cos.get)})
    return {"muestra": res,
            "veredicto": max(set(r["mejor"] for r in res),
                             key=lambda m: sum(1 for r in res if r["mejor"] == m)),
            "unanime": len(set(r["mejor"] for r in res)) == 1}


# ---------------------------------------------------------------------------
# Programa
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--conjunto", default="/app/backend/tests/eval/consultas_corpus.yaml")
    ap.add_argument("--salida", default="/tmp/eval_recuperacion.json")
    ap.add_argument("--repeticiones-latencia", type=int, default=5)
    ap.add_argument("--sin-ab-prefijo", action="store_true",
                    help="salta el A/B de F5 (re-embeber los 1.031 fragmentos)")
    args = ap.parse_args()

    ds = yaml.safe_load(open(args.conjunto))
    consultas = ds["consultas"]
    usables = [q for q in consultas if q["relevantes"]]
    excluidas = [q["id"] for q in consultas if not q["relevantes"]]

    conn = conectar()
    cur = conn.cursor()
    prov = get_default_embedding_provider()
    prov.embed_query("query: calentamiento")  # calentamiento explicito

    resultados = {
        "conjunto": {"total": len(consultas), "usables": len(usables),
                     "excluidas": excluidas,
                     "etiquetas": sum(len(q["relevantes"]) for q in usables)},
        "parametros": {"lexico_top": LEXICO_TOP, "vector_top": VECTOR_TOP,
                       "rrf_k_produccion": RRF_K_PRODUCCION,
                       "bootstrap": BOOTSTRAP_N, "semilla": SEMILLA},
    }

    # --- comprobacion del corpus, para que las cifras no floten -------------
    cur.execute("SELECT count(*), count(*) FILTER (WHERE embedding IS NOT NULL) "
                "FROM knowledge_chunks")
    total, con_emb = cur.fetchone()
    cur.execute("SELECT COALESCE(s.code,'?'), count(*) FROM knowledge_chunks c "
                "JOIN knowledge_documents d ON d.id=c.document_id "
                "LEFT JOIN knowledge_sources s ON s.id=d.source_id GROUP BY 1 ORDER BY 2 DESC")
    resultados["corpus"] = {"fragmentos": total, "con_embedding": con_emb,
                            "por_fuente": dict(cur.fetchall())}
    print(f"corpus: {total} fragmentos ({con_emb} con embedding) · "
          f"{resultados['corpus']['por_fuente']}")
    print(f"conjunto: {len(consultas)} consultas · {len(usables)} usables · "
          f"excluidas {excluidas}\n")

    # --- candidatos: se calculan UNA vez por consulta -----------------------
    candidatos = {}
    for q in usables:
        emb = normaliza(prov.embed_query(E5_QUERY_PREFIX + q["texto"]))
        candidatos[q["id"]] = {
            "lex": lexico(cur, q["texto"], LEXICO_TOP),
            "lex_and": lexico_and(cur, q["texto"], LEXICO_TOP),
            "vec": vectorial(cur, emb, VECTOR_TOP),
            "relevantes": set(q["relevantes"]),
            "emb": emb,
        }

    sin_cand = {
        "or_produccion": [i for i, c in candidatos.items() if not c["lex"]],
        "and_anterior": [i for i, c in candidatos.items() if not c["lex_and"]],
    }
    resultados["lexico_sin_candidatos"] = {
        "or_produccion": {"n": len(sin_cand["or_produccion"]),
                          "consultas": sin_cand["or_produccion"]},
        "and_anterior": {"n": len(sin_cand["and_anterior"]),
                         "consultas": sin_cand["and_anterior"]},
    }
    print(f"consultas sin UN SOLO candidato lexico: "
          f"{len(sin_cand['and_anterior'])}/{len(candidatos)} con el AND anterior · "
          f"{len(sin_cand['or_produccion'])}/{len(candidatos)} con el OR de produccion\n")

    # --- F2 · las ramas -----------------------------------------------------
    # `lexico_and` y `rrf_and` son el ANTES del arreglo del analizador: se miden
    # sobre las MISMAS 49 consultas para que el antes y el despues esten en la
    # misma tabla y no en dos ejecuciones distintas.
    ramas = {}
    for nombre in ("lexico", "lexico_and", "vectorial", "rrf", "rrf_and"):
        por_consulta = {}
        for qid, c in candidatos.items():
            if nombre == "lexico":
                orden = c["lex"]
            elif nombre == "lexico_and":
                orden = c["lex_and"]
            elif nombre == "vectorial":
                orden = c["vec"]
            elif nombre == "rrf_and":
                orden, _ = rrf(c["lex_and"], c["vec"], RRF_K_PRODUCCION)
            else:
                orden, _ = rrf(c["lex"], c["vec"], RRF_K_PRODUCCION)
            por_consulta[qid] = metricas_una(orden, c["relevantes"])
        media = promedia(list(por_consulta.values()))
        ics = {m: bootstrap_ic([d[m] for d in por_consulta.values()])
               for m in media}
        ramas[nombre] = {"media": media, "ic95": ics, "por_consulta": por_consulta}
    resultados["ramas"] = {n: {"media": v["media"], "ic95": v["ic95"]}
                           for n, v in ramas.items()}

    # Contrastes PAREADOS: es lo unico que responde «¿gana la fusion?».
    orden_q = list(candidatos)
    def serie(rama, met):
        return [ramas[rama]["por_consulta"][q][met] for q in orden_q]
    contrastes = {}
    for a, b in (("vectorial", "rrf"), ("rrf", "rrf_and"),
                 ("lexico", "lexico_and"), ("vectorial", "lexico"),
                 ("rrf", "lexico"), ("vectorial", "rrf_and")):
        for met in ("hitrate@5", "recall@5", "mrr"):
            contrastes[f"{a} - {b} · {met}"] = bootstrap_ic_pareado(
                serie(a, met), serie(b, met))
    resultados["contrastes_pareados"] = contrastes

    print("F2 · RAMAS (n=%d consultas) · `lexico_and` y `rrf_and` son el ANTES\n"
          "     del arreglo del analizador; `lexico` y `rrf` son produccion." % len(usables))
    print("     hitrate@k = ¿llego ALGUN relevante al top-k? · recall@k = ¿que")
    print("     fraccion de LOS relevantes de esa consulta llego? No es lo mismo.")
    cab = "rama          " + "".join(f"  hitrate@{k:<2}" for k in KS) + "   MRR"
    print(cab)
    for n, v in ramas.items():
        fila = f"{n:<14}" + "".join(f"  {v['media'][f'hitrate@{k}']:>10.3f}" for k in KS)
        print(fila + f"  {v['media']['mrr']:.3f}")
    print()
    print("rama          " + "".join(f"   recall@{k:<2}" for k in KS))
    for n, v in ramas.items():
        print(f"{n:<14}" + "".join(f"  {v['media'][f'recall@{k}']:>10.3f}" for k in KS))
    print()

    print("F2b · CONTRASTES PAREADOS (misma consulta en las dos ramas)")
    print("contraste                        dif.     IC95              ¿excluye el 0?")
    for nom, c in contrastes.items():
        print(f"{nom:<32} {c['diferencia']:+.3f}   "
              f"[{c['ic95'][0]:+.3f}, {c['ic95'][1]:+.3f}]   "
              f"{'SI' if c['excluye_el_cero'] else 'no'}")
    print()

    # --- F3 · barrido de RRF_K con IC --------------------------------------
    barrido = {}
    for k in BARRIDO_K:
        vals5, valsmrr, valsr5 = [], [], []
        for qid, c in candidatos.items():
            orden, _ = rrf(c["lex"], c["vec"], k)
            m = metricas_una(orden, c["relevantes"])
            vals5.append(m["hitrate@5"])
            valsr5.append(m["recall@5"])
            valsmrr.append(m["mrr"])
        barrido[k] = {
            "hitrate@5": sum(vals5) / len(vals5),
            "hitrate@5_ic95": bootstrap_ic(vals5),
            "recall@5": sum(valsr5) / len(valsr5),
            "recall@5_ic95": bootstrap_ic(valsr5),
            "mrr": sum(valsmrr) / len(valsmrr),
            "mrr_ic95": bootstrap_ic(valsmrr),
        }
    resultados["barrido_k"] = barrido

    print("F3 · BARRIDO DE RRF_K (IC 95 %% por remuestreo de consultas, %d repeticiones)"
          % BOOTSTRAP_N)
    print("   k    hitrate@5  IC95              MRR    IC95")
    for k, v in barrido.items():
        print(f"{k:>4}    {v['hitrate@5']:.3f}   [{v['hitrate@5_ic95'][0]:.3f}, "
              f"{v['hitrate@5_ic95'][1]:.3f}]    {v['mrr']:.3f}  "
              f"[{v['mrr_ic95'][0]:.3f}, {v['mrr_ic95'][1]:.3f}]")
    mejor = max(barrido, key=lambda k: barrido[k]["hitrate@5"])
    dentro = (barrido[RRF_K_PRODUCCION]["hitrate@5"] >= barrido[mejor]["hitrate@5_ic95"][0])
    resultados["decision_k"] = {"mejor_puntual": mejor,
                                "produccion": RRF_K_PRODUCCION,
                                "produccion_dentro_del_ic_del_mejor": bool(dentro)}
    print(f"\n  maximo puntual en k={mejor}; el 60 de produccion "
          f"{'CAE DENTRO' if dentro else 'queda FUERA'} del IC del mejor\n")

    # --- F2c · ¿aporta la rama lexica algo que el vector NO traiga? ---------
    # Esta es la pregunta que decide si la rama se puede QUITAR, y no la
    # responden las medias: una rama puede tener peor recall medio y aun asi
    # ser la unica que rescata ciertas consultas. Se cuenta el numero de
    # fragmentos RELEVANTES que aparecen en los candidatos lexicos y NO en los
    # vectoriales, y en cuantas consultas eso ocurre.
    aporte = {"consultas_con_relevante_solo_lexico": [],
              "consultas_con_relevante_solo_vectorial": [],
              "relevantes_solo_lexico": 0, "relevantes_solo_vectorial": 0,
              "relevantes_totales": 0}
    for qid, c in candidatos.items():
        rel = c["relevantes"]
        solo_lex = rel & set(c["lex"]) - set(c["vec"])
        solo_vec = rel & set(c["vec"]) - set(c["lex"])
        aporte["relevantes_totales"] += len(rel)
        aporte["relevantes_solo_lexico"] += len(solo_lex)
        aporte["relevantes_solo_vectorial"] += len(solo_vec)
        if solo_lex:
            aporte["consultas_con_relevante_solo_lexico"].append(qid)
        if solo_vec:
            aporte["consultas_con_relevante_solo_vectorial"].append(qid)
    # Y el que de verdad importa para quitar la rama: ¿en cuantas consultas el
    # UNICO relevante recuperado viene de la rama lexica?
    rescates = [qid for qid, c in candidatos.items()
                if (c["relevantes"] & set(c["lex"])) and not (c["relevantes"] & set(c["vec"]))]
    aporte["consultas_que_SOLO_rescata_la_rama_lexica"] = rescates
    resultados["f2c_aporte_unico_de_cada_rama"] = aporte
    print("F2c · ¿aporta la rama lexica algo que el vector no traiga?")
    print(f"     relevantes que solo trae la lexica:   "
          f"{aporte['relevantes_solo_lexico']}/{aporte['relevantes_totales']} "
          f"(en {len(aporte['consultas_con_relevante_solo_lexico'])} consultas)")
    print(f"     relevantes que solo trae la vectorial: "
          f"{aporte['relevantes_solo_vectorial']}/{aporte['relevantes_totales']} "
          f"(en {len(aporte['consultas_con_relevante_solo_vectorial'])} consultas)")
    print(f"     consultas en las que el UNICO relevante recuperado lo trae la "
          f"lexica: {len(rescates)} {rescates}\n")

    # --- F3b · barrido del PESO de la rama lexica ---------------------------
    # Esta es la medida que decide si la fusion se sostiene, y sustituye a la
    # pregunta binaria «¿fusion si o no?»: w = 0 ES borrar la fusion (queda el
    # vector solo), w = 0,5 es el RRF clasico que corre hoy, w = 1 es quedarse
    # con la rama lexica. Si el maximo cae en w = 0, la fusion sobra y hay una
    # curva que lo dice, en vez de una opinion.
    barrido_w = {}
    for w in BARRIDO_W:
        vals = {m: [] for m in ("hitrate@5", "recall@5", "mrr")}
        for qid, c in candidatos.items():
            orden, _ = rrf(c["lex"], c["vec"], RRF_K_PRODUCCION, w_lex=w)
            m = metricas_una(orden, c["relevantes"])
            for k2 in vals:
                vals[k2].append(m[k2])
        barrido_w[w] = {m: sum(v) / len(v) for m, v in vals.items()}
        barrido_w[w].update({f"{m}_ic95": bootstrap_ic(v) for m, v in vals.items()})
        barrido_w[w]["_series"] = vals
    # Contraste pareado de CADA peso contra w = 0 (vector solo). Comparar medias
    # sueltas de once curvas seria pescar el maximo del ruido.
    contra_w0 = {}
    for w in BARRIDO_W:
        if w == 0.0:
            continue
        for met in ("hitrate@5", "recall@5", "mrr"):
            contra_w0[f"w={w:.1f} - w=0 · {met}"] = bootstrap_ic_pareado(
                barrido_w[w]["_series"][met], barrido_w[0.0]["_series"][met])
    resultados["barrido_peso_lexico"] = {
        w: {k2: v2 for k2, v2 in d.items() if k2 != "_series"}
        for w, d in barrido_w.items()
    }
    resultados["barrido_peso_contrastes_contra_w0"] = contra_w0

    print("F3b · BARRIDO DEL PESO DE LA RAMA LEXICA en la fusion")
    print("      w = 0 es BORRAR la fusion (vector solo) · w = 0,5 es el RRF de hoy")
    print("   w    hitrate@5  IC95              recall@5   MRR")
    for w, v in barrido_w.items():
        print(f"{w:>4.1f}    {v['hitrate@5']:.3f}   [{v['hitrate@5_ic95'][0]:.3f}, "
              f"{v['hitrate@5_ic95'][1]:.3f}]     {v['recall@5']:.3f}   {v['mrr']:.3f}")
    mejor_w = max(BARRIDO_W, key=lambda w: (barrido_w[w]["recall@5"], barrido_w[w]["mrr"]))
    algun_w_gana = [nom for nom, c in contra_w0.items()
                    if c["excluye_el_cero"] and c["diferencia"] > 0]
    resultados["decision_fusion"] = {
        "mejor_w_puntual": mejor_w,
        "w_produccion": 0.5,
        "pesos_que_baten_a_w0_con_ic_que_excluye_el_cero": algun_w_gana,
        "hay_algun_peso_que_justifique_la_fusion": bool(algun_w_gana),
    }
    print(f"\n      maximo puntual en w={mejor_w:.1f}; pesos que baten al vector solo "
          f"con IC que excluye el 0: {len(algun_w_gana)} de {len(contra_w0)} contrastes")
    if not algun_w_gana:
        print("      NINGUNO. Con este corpus y estas 49 consultas, no hay peso de la")
        print("      rama lexica que mejore al vector solo de forma distinguible del ruido.\n")
    else:
        print(f"      {algun_w_gana}\n")

    # --- F4 · no monotonia del RRF -----------------------------------------
    # QUE SE BUSCA, exactamente: que al quitar del conjunto de candidatos un
    # documento NO RELEVANTE se INVIERTA el orden relativo de dos documentos
    # que SIGUEN estando. Eso es lo que hace del RRF una funcion no monotona:
    # la posicion de A frente a B depende de un tercero que no es ninguno de
    # los dos.
    #
    # NO cuenta como ejemplo que, al quitar el que iba 5.º, suba el 6.º: eso
    # pasa en CUALQUIER lista y no dice nada del RRF. La primera version de
    # esta comprobacion medía justo eso y daba «49 de 49»; era una cifra
    # vacia y esta sustituida por la de abajo.
    ejemplos = []
    sin_ejemplo = []
    for qid, c in candidatos.items():
        base, pts = rrf(c["lex"], c["vec"], RRF_K_PRODUCCION)
        no_rel = [d for d in set(c["lex"]) | set(c["vec"]) if d not in c["relevantes"]]
        encontrado = None
        encontrado_estricto = None
        for quitado in sorted(no_rel):
            nb = [x for x in c["lex"] if x != quitado]
            nv = [x for x in c["vec"] if x != quitado]
            nuevo_orden, npts = rrf(nb, nv, RRF_K_PRODUCCION)
            pos_a = {d: i for i, d in enumerate(base) if d != quitado}
            pos_b = {d: i for i, d in enumerate(nuevo_orden)}
            inversiones, estrictas = [], []
            supervivientes = sorted(pos_a, key=lambda d: pos_a[d])
            for i in range(len(supervivientes)):
                for j in range(i + 1, len(supervivientes)):
                    x, y = supervivientes[i], supervivientes[j]
                    if pos_b.get(x, 1e9) > pos_b.get(y, 1e9):
                        inversiones.append((x, y))
                        # ESTRICTA: antes x puntuaba MAS que y de verdad, y
                        # despues y puntua MAS que x de verdad. Si alguno de
                        # los dos lados es un empate, el vuelco lo decide el
                        # criterio de desempate, no el RRF, y no vale como
                        # demostracion.
                        if pts[x] > pts[y] and npts.get(y, 0.0) > npts.get(x, 0.0):
                            estrictas.append((x, y))
            if not inversiones:
                continue
            afecta_top5 = (set(nuevo_orden[:5]) - {quitado}) != (set(base[:5]) - {quitado})
            encontrado = {
                "consulta": qid,
                "texto": next(q["texto"] for q in usables if q["id"] == qid),
                "quitado": quitado,
                "quitado_estaba_en_top5": quitado in base[:5],
                "inversiones": [{"sube": y, "baja": x} for x, y in inversiones],
                "inversiones_estrictas": [{"sube": y, "baja": x,
                                           "antes": {"baja": pts[x], "sube": pts[y]},
                                           "despues": {"baja": npts.get(x, 0.0),
                                                       "sube": npts.get(y, 0.0)}}
                                          for x, y in estrictas],
                "cambia_el_top5": bool(afecta_top5),
                "antes": [{"id": d, "rrf": pts[d], "relevante": d in c["relevantes"],
                           "lexico": (c["lex"].index(d) + 1) if d in c["lex"] else None,
                           "vec": (c["vec"].index(d) + 1) if d in c["vec"] else None}
                          for d in base[:5]],
                "despues": [{"id": d, "rrf": npts[d], "relevante": d in c["relevantes"],
                             "lexico": (nb.index(d) + 1) if d in nb else None,
                             "vec": (nv.index(d) + 1) if d in nv else None}
                            for d in nuevo_orden[:5]],
            }
            if afecta_top5 and estrictas:
                break   # el mejor ejemplo posible: estricta y llega al top-5
            if encontrado_estricto is None and estrictas:
                encontrado_estricto = encontrado
        if encontrado_estricto is not None and not (
                encontrado and encontrado.get("inversiones_estrictas")):
            encontrado = encontrado_estricto
        if encontrado:
            ejemplos.append(encontrado)
        else:
            sin_ejemplo.append(qid)

    con_top5 = [e for e in ejemplos if e["cambia_el_top5"]]
    con_estricta = [e for e in ejemplos if e["inversiones_estrictas"]]
    resultados["f4_no_monotonia"] = {
        "criterio": ("se invierte el orden relativo de dos documentos que SIGUEN "
                     "en la lista al quitar un tercero NO relevante"),
        "consultas_exploradas": len(candidatos),
        "consultas_con_inversion": len(ejemplos),
        "consultas_sin_inversion": sin_ejemplo,
        "consultas_donde_la_inversion_llega_al_top5": len(con_top5),
        "consultas_con_inversion_ESTRICTA": len(con_estricta),
        "nota_empates": ("una inversion que pasa por un EMPATE de puntuacion la "
                         "decide el criterio de desempate, no el RRF; por eso se "
                         "cuentan aparte las estrictas"),
        "ejemplos": ([e for e in con_estricta if e["cambia_el_top5"]][:2]
                     or con_estricta[:2] or con_top5[:2] or ejemplos[:2]),
    }
    print("F4 · no monotonia (criterio: se INVIERTE el orden de dos documentos "
          "que siguen estando)")
    print(f"     {len(ejemplos)} de {len(candidatos)} consultas tienen al menos una "
          f"inversion; en {len(con_top5)} llega al top-5")
    print(f"     de ellas, {len(con_estricta)} tienen una inversion ESTRICTA "
          f"(desigualdad real de puntuacion, no un empate deshecho por el desempate)")
    if sin_ejemplo:
        print(f"     sin ninguna inversion: {len(sin_ejemplo)} consultas "
              f"(las que se quedan sin candidatos lexicos no pueden tenerla)\n")
    else:
        print()

    # --- F5 · prefijo -------------------------------------------------------
    diag = diagnostico_prefijo(cur, prov)
    resultados["f5_prefijo_guardado"] = diag
    print(f"F5 · prefijo de los embeddings guardados: '{diag['veredicto']}' "
          f"(unanime en la muestra: {diag['unanime']})")

    if not args.sin_ab_prefijo:
        # A/B: ¿cuanto costaria que el documento NO llevara 'passage: '?
        # Se re-embebe el corpus entero de las dos formas y se busca en numpy,
        # para que la comparacion sea exactamente la misma operacion en ambos
        # lados (no pgvector contra numpy).
        cur.execute("SELECT id::text, content FROM knowledge_chunks "
                    "WHERE embedding IS NOT NULL ORDER BY id")
        filas = cur.fetchall()
        ids = [f[0] for f in filas]
        textos = [f[1] for f in filas]
        # Por lotes de 32, igual que el ingestor. En un solo lote de 1.031
        # textos largos el proceso se comio 12,8 GB y no termino en 13 minutos
        # (medido); el comando reproducible no puede comportarse asi.
        def embebe_por_lotes(lista, lote=32):
            vs = []
            for i in range(0, len(lista), lote):
                vs.extend(normaliza(v) for v in prov.embed_documents(lista[i:i + lote]))
                if i and (i // lote) % 8 == 0:
                    print(f"      ...{i}/{len(lista)}", flush=True)
            return np.array(vs)

        print(f"    re-embebiendo {len(textos)} fragmentos por lotes de 32 "
              f"(dos pasadas: con 'passage: ' y sin prefijo)")
        t0 = time.perf_counter()
        M_con = embebe_por_lotes([E5_PASSAGE_PREFIX + x for x in textos])
        t_con = time.perf_counter() - t0
        t0 = time.perf_counter()
        M_sin = embebe_por_lotes(textos)
        t_sin = time.perf_counter() - t0

        # ¿reproduce numpy el orden de pgvector? Si no, el A/B no compara lo
        # que dice comparar. Se mide, no se supone.
        idx = {c: i for i, c in enumerate(ids)}
        coincidencias = []
        for qid, c in candidatos.items():
            orden_np = [ids[i] for i in np.argsort(-(M_con @ np.array(c["emb"])))[:5]]
            coincidencias.append(orden_np == c["vec"][:5])
        resultados["f5_numpy_reproduce_pgvector"] = {
            "consultas": len(coincidencias),
            "top5_identico": sum(coincidencias),
        }
        print(f"    comprobacion previa: numpy reproduce el top-5 de pgvector en "
              f"{sum(coincidencias)}/{len(coincidencias)} consultas")

        def evalua_matriz(M):
            por = []
            for qid, c in candidatos.items():
                orden = [ids[i] for i in np.argsort(-(M @ np.array(c["emb"])))[:VECTOR_TOP]]
                mv = metricas_una(orden, c["relevantes"])
                of, _ = rrf(c["lex"], orden, RRF_K_PRODUCCION)
                por.append({"vec": mv, "rrf": metricas_una(of, c["relevantes"])})
            return por

        por_con, por_sin = evalua_matriz(M_con), evalua_matriz(M_sin)
        vc = promedia([p["vec"] for p in por_con])
        fc = promedia([p["rrf"] for p in por_con])
        vs = promedia([p["vec"] for p in por_sin])
        fs = promedia([p["rrf"] for p in por_sin])
        # El efecto es pequeño: sin un IC pareado, un +-0,02 no se distingue
        # del ruido y publicarlo a secas seria una cifra vacia.
        ab_contrastes = {}
        for rama in ("vec", "rrf"):
            for met in ("hitrate@1", "hitrate@5", "recall@5", "mrr"):
                ab_contrastes[f"{rama} · {met} · con-passage menos sin-prefijo"] = \
                    bootstrap_ic_pareado([p[rama][met] for p in por_con],
                                         [p[rama][met] for p in por_sin])
        resultados["f5_ab_prefijo"] = {
            "segundos_reembeber_1031_con_passage": round(t_con, 1),
            "segundos_reembeber_1031_sin_prefijo": round(t_sin, 1),
            "con_passage": {"vectorial": vc, "rrf": fc},
            "sin_prefijo": {"vectorial": vs, "rrf": fs},
            "contrastes_pareados": ab_contrastes,
        }
        print(f"    A/B (re-embebido {len(ids)} fragmentos: "
              f"{t_con:.0f}s con prefijo, {t_sin:.0f}s sin):")
        print("      contraste (con 'passage: ' MENOS sin prefijo)      dif.     "
              "IC95              ¿excluye el 0?")
        for nom, c2 in ab_contrastes.items():
            print(f"      {nom:<48} {c2['diferencia']:+.3f}   "
                  f"[{c2['ic95'][0]:+.3f}, {c2['ic95'][1]:+.3f}]   "
                  f"{'SI' if c2['excluye_el_cero'] else 'no'}")
    print()

    # --- F6 · latencia ------------------------------------------------------
    etapas = {"embebido": [], "lexico": [], "vectorial": [], "fusion": []}
    for _ in range(args.repeticiones_latencia):
        for q in usables:
            t = time.perf_counter()
            emb = normaliza(prov.embed_query(E5_QUERY_PREFIX + q["texto"]))
            t1 = time.perf_counter(); etapas["embebido"].append(t1 - t)
            b = lexico(cur, q["texto"], LEXICO_TOP)
            t2 = time.perf_counter(); etapas["lexico"].append(t2 - t1)
            v = vectorial(cur, emb, VECTOR_TOP)
            t3 = time.perf_counter(); etapas["vectorial"].append(t3 - t2)
            rrf(b, v, RRF_K_PRODUCCION)
            etapas["fusion"].append(time.perf_counter() - t3)

    def pct(xs, p):
        s = sorted(xs)
        return s[min(len(s) - 1, int(p * len(s)))] * 1000

    lat = {e: {"p50_ms": round(pct(v, 0.50), 2), "p95_ms": round(pct(v, 0.95), 2),
               "n": len(v)} for e, v in etapas.items()}
    total_ms = [sum(x) for x in zip(*(etapas[e] for e in etapas))]
    lat["TOTAL"] = {"p50_ms": round(pct(total_ms, 0.50), 2),
                    "p95_ms": round(pct(total_ms, 0.95), 2), "n": len(total_ms)}
    # La carga del anfitrion se anota SIEMPRE junto a la latencia: sin ella el
    # numero no significa nada. Medido: en este mismo equipo, con otro agente
    # moviendo navegadores de Playwright (carga ~10-15 sobre 14 nucleos), el p50
    # total paso de 34,56 ms a 160,42 ms. Es la misma cifra y no dice lo mismo.
    try:
        carga = open("/proc/loadavg").read().split()[:3]
    except OSError:
        carga = None
    try:
        nucleos = len(os.sched_getaffinity(0))
    except AttributeError:
        nucleos = os.cpu_count()
    resultados["f6_latencia"] = {
        "repeticiones": args.repeticiones_latencia,
        "calentamiento": "si · una llamada al modelo antes de medir",
        "carga_del_anfitrion_1_5_15_min": carga,
        "nucleos_visibles": nucleos,
        "etapas": lat,
    }
    print("F6 · LATENCIA (%d repeticiones x %d consultas, con calentamiento)"
          % (args.repeticiones_latencia, len(usables)))
    print("     carga del anfitrion (1/5/15 min): %s sobre %s nucleos "
          "· sin esto la cifra no significa nada" % (carga, nucleos))
    print("etapa         p50 (ms)   p95 (ms)")
    for e, v in lat.items():
        print(f"{e:<12}  {v['p50_ms']:>8.2f}   {v['p95_ms']:>8.2f}")

    Path(args.salida).parent.mkdir(parents=True, exist_ok=True)
    with open(args.salida, "w") as fh:
        json.dump(resultados, fh, indent=2, ensure_ascii=False)
    print(f"\nresultados en bruto: {args.salida}")


if __name__ == "__main__":
    main()
