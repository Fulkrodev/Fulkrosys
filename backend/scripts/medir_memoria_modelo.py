"""Mide la RSS de un proceso antes y despues de cargar e5-large.

Sirve para una sola cosa: sustituir por una medida el "~1,4 GB por proceso" que
ADR-060 afirmaba sin fuente. Resultado (2026-09-11, imagen fulkro/backend:demo):
el modelo cuesta 1.513,9 MB y el proceso acaba con 58 hilos sobre 14 nucleos.

Se ejecuta DENTRO de la imagen del backend, que es donde estan fastembed y
onnxruntime, y no necesita levantar Postgres ni el resto de la pila:

    docker run --rm \
      -v $PWD/backend/scripts/medir_memoria_modelo.py:/tmp/m.py:ro \
      --entrypoint python fulkro/backend:demo /tmp/m.py

La salida se guarda en out/memoria_modelo.json. Mide el mismo camino que usa la
busqueda del corpus: get_default_embedding_provider (app/core/ai/embeddings.py)
construye un TextEmbedding por PROCESO, de forma perezosa, y lo consume
app/corpus/retrieval.py:185.
"""
import json, os

def rss_mb():
    with open(f"/proc/{os.getpid()}/status") as f:
        for linea in f:
            if linea.startswith("VmRSS:"):
                return int(linea.split()[1]) / 1024.0
    return None

out = {}
out["1_interprete_solo_mb"] = round(rss_mb(), 1)

import numpy, onnxruntime  # noqa: F401
from fastembed import TextEmbedding
out["2_imports_sin_modelo_mb"] = round(rss_mb(), 1)
out["onnxruntime_version"] = onnxruntime.__version__

m = TextEmbedding(model_name="intfloat/multilingual-e5-large")
out["3_modelo_construido_mb"] = round(rss_mb(), 1)

v = list(m.embed(["query: prueba de memoria"]))
out["4_tras_primer_embed_mb"] = round(rss_mb(), 1)
out["dimensiones"] = len(v[0])

v = list(m.embed([f"query: lote {i}" for i in range(32)]))
out["5_tras_lote_32_mb"] = round(rss_mb(), 1)

out["coste_del_modelo_mb"] = round(out["5_tras_lote_32_mb"] - out["2_imports_sin_modelo_mb"], 1)
out["hilos_del_proceso"] = len(os.listdir(f"/proc/{os.getpid()}/task"))
out["nucleos_visibles"] = os.cpu_count()
try:
    out["ort_intra_op_threads_por_defecto"] = onnxruntime.SessionOptions().intra_op_num_threads
except Exception as e:
    out["ort_intra_op_threads_por_defecto"] = f"n/d: {e}"

print(json.dumps(out, indent=2, ensure_ascii=False))
