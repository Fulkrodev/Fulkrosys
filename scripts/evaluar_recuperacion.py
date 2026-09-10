#!/usr/bin/env python3
"""Evalua la recuperacion del corpus: BM25, vectorial y la fusion RRF.

QUE MIDE
  - acierto@k y recall@k (k = 1, 3, 5, 10) y MRR, para las TRES ramas por
    separado: BM25 sola, vectorial sola y la fusion RRF.
  - un barrido de RRF_K con intervalo de confianza por remuestreo (bootstrap)
    sobre las consultas.
  - la latencia de una busqueda completa, desglosada por etapa.
  - si los embeddings guardados llevan el prefijo 'passage: ' que espera e5, y
    cuanto costaria en recall@5 que no lo llevaran.

QUE **NO** MIDE
  - la calidad de la RESPUESTA del modelo. Esto mide que fragmentos llegan al
    modelo, no que hace el modelo con ellos.
  - nada fuera de las 49 consultas etiquetadas. 49 consultas es una muestra
    pequeña: los intervalos de confianza que imprime son anchos a proposito,
    para que no se lean como precision que no hay.
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
RRF_K_PRODUCCION = 60
BM25_TOP = 30
VECTOR_TOP = 30
E5_QUERY_PREFIX = "query: "
E5_PASSAGE_PREFIX = "passage: "

KS = (1, 3, 5, 10)
BARRIDO_K = (1, 5, 10, 20, 30, 60, 100, 200)
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


def bm25(cur, consulta: str, top: int) -> list[str]:
    """Igual que _bm25_search: plainto_tsquery('spanish') + ts_rank_cd."""
    cur.execute(
        "SELECT c.id::text FROM knowledge_chunks c "
        "WHERE c.content_tsvector @@ plainto_tsquery('spanish', %s) "
        "ORDER BY ts_rank_cd(c.content_tsvector, plainto_tsquery('spanish', %s)) DESC "
        "LIMIT %s",
        (consulta, consulta, top),
    )
    return [r[0] for r in cur.fetchall()]


def bm25_or(cur, consulta: str, top: int) -> list[str]:
    """Variante de DIAGNOSTICO: los mismos lexemas pero unidos por OR.

    `plainto_tsquery` une TODOS los terminos con AND. Una pregunta de doce
    palabras solo casa con un fragmento que contenga las doce, asi que la rama
    BM25 se queda sin candidatos. Esto NO es lo que corre en produccion: esta
    aqui para medir si esa es la causa, en vez de suponerlo."""
    cur.execute("SELECT to_tsvector('spanish', %s)", (consulta,))
    tsv = cur.fetchone()[0] or ""
    lex = [p.split(":")[0] for p in tsv.split()]
    if not lex:
        return []
    q = " | ".join(lex)
    cur.execute(
        "SELECT c.id::text FROM knowledge_chunks c "
        "WHERE c.content_tsvector @@ to_tsquery('spanish', %s) "
        "ORDER BY ts_rank_cd(c.content_tsvector, to_tsquery('spanish', %s)) DESC "
        "LIMIT %s",
        (q, q, top),
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


def rrf(lista_bm25: list[str], lista_vec: list[str], k: int) -> list[str]:
    """Fusion RRF: score(d) = suma de 1/(k + rango_i(d)). Devuelve ids ordenados.

    El desempate es por id, para que el resultado no dependa del orden de
    iteracion de un conjunto de Python (seria irreproducible entre ejecuciones).
    """
    r_bm = {c: i + 1 for i, c in enumerate(lista_bm25)}
    r_ve = {c: i + 1 for i, c in enumerate(lista_vec)}
    puntos = {}
    for c in set(r_bm) | set(r_ve):
        s = 0.0
        if c in r_bm:
            s += 1.0 / (k + r_bm[c])
        if c in r_ve:
            s += 1.0 / (k + r_ve[c])
        puntos[c] = s
    return sorted(puntos, key=lambda c: (-puntos[c], c)), puntos


# ---------------------------------------------------------------------------
# Metricas
# ---------------------------------------------------------------------------
def metricas_una(ordenados: list[str], relevantes: set[str]) -> dict:
    """acierto@k (¿hay algun relevante en el top-k?), recall@k (fraccion) y RR."""
    out = {}
    for k in KS:
        top = ordenados[:k]
        encontrados = len(set(top) & relevantes)
        out[f"acierto@{k}"] = 1.0 if encontrados else 0.0
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
    ap.add_argument("--salida", default="/app/out/eval_recuperacion.json")
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
        "parametros": {"bm25_top": BM25_TOP, "vector_top": VECTOR_TOP,
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
            "bm25": bm25(cur, q["texto"], BM25_TOP),
            "bm25_or": bm25_or(cur, q["texto"], BM25_TOP),
            "vec": vectorial(cur, emb, VECTOR_TOP),
            "relevantes": set(q["relevantes"]),
            "emb": emb,
        }

    vacias_bm25 = [i for i, c in candidatos.items() if not c["bm25"]]
    resultados["bm25_sin_candidatos"] = {"n": len(vacias_bm25), "consultas": vacias_bm25}

    # --- F2 · las tres ramas -----------------------------------------------
    ramas = {}
    for nombre in ("bm25", "vectorial", "rrf", "bm25_or", "rrf_or"):
        por_consulta = {}
        for qid, c in candidatos.items():
            if nombre == "bm25":
                orden = c["bm25"]
            elif nombre == "bm25_or":
                orden = c["bm25_or"]
            elif nombre == "vectorial":
                orden = c["vec"]
            elif nombre == "rrf_or":
                orden, _ = rrf(c["bm25_or"], c["vec"], RRF_K_PRODUCCION)
            else:
                orden, _ = rrf(c["bm25"], c["vec"], RRF_K_PRODUCCION)
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
    for a, b in (("vectorial", "rrf"), ("vectorial", "bm25"), ("rrf", "bm25"),
                 ("rrf_or", "rrf"), ("vectorial", "rrf_or")):
        for met in ("acierto@5", "recall@5", "mrr"):
            contrastes[f"{a} - {b} · {met}"] = bootstrap_ic_pareado(
                serie(a, met), serie(b, met))
    resultados["contrastes_pareados"] = contrastes

    print("F2 · TRES RAMAS (n=%d consultas) · las dos ultimas son DIAGNOSTICO,\n"
          "     no son lo que corre en produccion" % len(usables))
    cab = "rama        " + "".join(f"  acierto@{k:<2}" for k in KS) + "   MRR"
    print(cab)
    for n, v in ramas.items():
        fila = f"{n:<12}" + "".join(f"  {v['media'][f'acierto@{k}']:>10.3f}" for k in KS)
        print(fila + f"  {v['media']['mrr']:.3f}")
    print()
    print("rama        " + "".join(f"   recall@{k:<2}" for k in KS))
    for n, v in ramas.items():
        print(f"{n:<12}" + "".join(f"  {v['media'][f'recall@{k}']:>10.3f}" for k in KS))
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
            orden, _ = rrf(c["bm25"], c["vec"], k)
            m = metricas_una(orden, c["relevantes"])
            vals5.append(m["acierto@5"])
            valsr5.append(m["recall@5"])
            valsmrr.append(m["mrr"])
        barrido[k] = {
            "acierto@5": sum(vals5) / len(vals5),
            "acierto@5_ic95": bootstrap_ic(vals5),
            "recall@5": sum(valsr5) / len(valsr5),
            "recall@5_ic95": bootstrap_ic(valsr5),
            "mrr": sum(valsmrr) / len(valsmrr),
            "mrr_ic95": bootstrap_ic(valsmrr),
        }
    resultados["barrido_k"] = barrido

    print("F3 · BARRIDO DE RRF_K (IC 95 %% por remuestreo de consultas, %d repeticiones)"
          % BOOTSTRAP_N)
    print("   k    acierto@5  IC95              MRR    IC95")
    for k, v in barrido.items():
        print(f"{k:>4}    {v['acierto@5']:.3f}   [{v['acierto@5_ic95'][0]:.3f}, "
              f"{v['acierto@5_ic95'][1]:.3f}]    {v['mrr']:.3f}  "
              f"[{v['mrr_ic95'][0]:.3f}, {v['mrr_ic95'][1]:.3f}]")
    mejor = max(barrido, key=lambda k: barrido[k]["acierto@5"])
    dentro = (barrido[RRF_K_PRODUCCION]["acierto@5"] >= barrido[mejor]["acierto@5_ic95"][0])
    resultados["decision_k"] = {"mejor_puntual": mejor,
                                "produccion": RRF_K_PRODUCCION,
                                "produccion_dentro_del_ic_del_mejor": bool(dentro)}
    print(f"\n  maximo puntual en k={mejor}; el 60 de produccion "
          f"{'CAE DENTRO' if dentro else 'queda FUERA'} del IC del mejor\n")

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
        base, pts = rrf(c["bm25"], c["vec"], RRF_K_PRODUCCION)
        no_rel = [d for d in set(c["bm25"]) | set(c["vec"]) if d not in c["relevantes"]]
        encontrado = None
        for quitado in sorted(no_rel):
            nb = [x for x in c["bm25"] if x != quitado]
            nv = [x for x in c["vec"] if x != quitado]
            nuevo_orden, npts = rrf(nb, nv, RRF_K_PRODUCCION)
            pos_a = {d: i for i, d in enumerate(base) if d != quitado}
            pos_b = {d: i for i, d in enumerate(nuevo_orden)}
            inversiones = []
            supervivientes = sorted(pos_a, key=lambda d: pos_a[d])
            for i in range(len(supervivientes)):
                for j in range(i + 1, len(supervivientes)):
                    x, y = supervivientes[i], supervivientes[j]
                    if pos_b.get(x, 1e9) > pos_b.get(y, 1e9):
                        inversiones.append((x, y))
            if not inversiones:
                continue
            afecta_top5 = (set(nuevo_orden[:5]) - {quitado}) != (set(base[:5]) - {quitado})
            encontrado = {
                "consulta": qid,
                "texto": next(q["texto"] for q in usables if q["id"] == qid),
                "quitado": quitado,
                "quitado_estaba_en_top5": quitado in base[:5],
                "inversiones": [{"sube": y, "baja": x} for x, y in inversiones],
                "cambia_el_top5": bool(afecta_top5),
                "antes": [{"id": d, "rrf": pts[d], "relevante": d in c["relevantes"],
                           "bm25": (c["bm25"].index(d) + 1) if d in c["bm25"] else None,
                           "vec": (c["vec"].index(d) + 1) if d in c["vec"] else None}
                          for d in base[:5]],
                "despues": [{"id": d, "rrf": npts[d], "relevante": d in c["relevantes"],
                             "bm25": (nb.index(d) + 1) if d in nb else None,
                             "vec": (nv.index(d) + 1) if d in nv else None}
                            for d in nuevo_orden[:5]],
            }
            if afecta_top5:
                break   # el mejor ejemplo posible: la inversion llega al top-5
        if encontrado:
            ejemplos.append(encontrado)
        else:
            sin_ejemplo.append(qid)

    con_top5 = [e for e in ejemplos if e["cambia_el_top5"]]
    resultados["f4_no_monotonia"] = {
        "criterio": ("se invierte el orden relativo de dos documentos que SIGUEN "
                     "en la lista al quitar un tercero NO relevante"),
        "consultas_exploradas": len(candidatos),
        "consultas_con_inversion": len(ejemplos),
        "consultas_sin_inversion": sin_ejemplo,
        "consultas_donde_la_inversion_llega_al_top5": len(con_top5),
        "ejemplos": (con_top5[:2] or ejemplos[:2]),
    }
    print(f"F4 · no monotonia (criterio: se INVIERTE el orden de dos documentos "
          f"que siguen estando)")
    print(f"     {len(ejemplos)} de {len(candidatos)} consultas tienen al menos una "
          f"inversion; en {len(con_top5)} la inversion llega al top-5")
    if sin_ejemplo:
        print(f"     sin ninguna inversion: {len(sin_ejemplo)} consultas "
              f"(las que se quedan sin candidatos BM25 no pueden tenerla)\n")
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
                sims = M @ np.array(c["emb"])
                orden = [ids[i] for i in np.argsort(-sims)[:VECTOR_TOP]]
                mv = metricas_una(orden, c["relevantes"])
                of, _ = rrf(c["bm25"], orden, RRF_K_PRODUCCION)
                mf = metricas_una(of, c["relevantes"])
                por.append({"vec": mv, "rrf": mf})
            return (promedia([p["vec"] for p in por]),
                    promedia([p["rrf"] for p in por]),
                    [p["vec"]["acierto@5"] for p in por],
                    [p["rrf"]["acierto@5"] for p in por])

        vc, fc, _, _ = evalua_matriz(M_con)
        vs, fs, _, _ = evalua_matriz(M_sin)
        resultados["f5_ab_prefijo"] = {
            "segundos_reembeber_1031_con_passage": round(t_con, 1),
            "segundos_reembeber_1031_sin_prefijo": round(t_sin, 1),
            "con_passage": {"vectorial": vc, "rrf": fc},
            "sin_prefijo": {"vectorial": vs, "rrf": fs},
        }
        print(f"    A/B (re-embebido {len(ids)} fragmentos: "
              f"{t_con:.0f}s con prefijo, {t_sin:.0f}s sin):")
        print(f"      vectorial acierto@5  con 'passage: ' {vc['acierto@5']:.3f}  ->  "
              f"sin prefijo {vs['acierto@5']:.3f}")
        print(f"      fusion    acierto@5  con 'passage: ' {fc['acierto@5']:.3f}  ->  "
              f"sin prefijo {fs['acierto@5']:.3f}")
    print()

    # --- F6 · latencia ------------------------------------------------------
    etapas = {"embebido": [], "bm25": [], "vectorial": [], "fusion": []}
    for _ in range(args.repeticiones_latencia):
        for q in usables:
            t = time.perf_counter()
            emb = normaliza(prov.embed_query(E5_QUERY_PREFIX + q["texto"]))
            t1 = time.perf_counter(); etapas["embebido"].append(t1 - t)
            b = bm25(cur, q["texto"], BM25_TOP)
            t2 = time.perf_counter(); etapas["bm25"].append(t2 - t1)
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
    resultados["f6_latencia"] = {
        "repeticiones": args.repeticiones_latencia,
        "calentamiento": "si · una llamada al modelo antes de medir",
        "etapas": lat,
    }
    print("F6 · LATENCIA (%d repeticiones x %d consultas, con calentamiento)"
          % (args.repeticiones_latencia, len(usables)))
    print("etapa         p50 (ms)   p95 (ms)")
    for e, v in lat.items():
        print(f"{e:<12}  {v['p50_ms']:>8.2f}   {v['p95_ms']:>8.2f}")

    Path(args.salida).parent.mkdir(parents=True, exist_ok=True)
    with open(args.salida, "w") as fh:
        json.dump(resultados, fh, indent=2, ensure_ascii=False)
    print(f"\nresultados en bruto: {args.salida}")


if __name__ == "__main__":
    main()
