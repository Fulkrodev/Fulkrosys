# Evaluación de la recuperación del corpus

**Fecha**: 2026-09-10 · **Rama**: `main` · **Corpus medido**: 1.031 fragmentos

Todo lo que sigue lleva el comando que lo reproduce. El comando único es:

```
make eval-recuperacion          # necesita el demo en pie (make demo)
```

que escribe `out/eval_recuperacion.json` con las cifras en bruto. Las tablas de
este documento están sacadas de ese fichero.

`out/` está en `.gitignore`, así que ese JSON **no viaja en el repositorio**: se
genera al ejecutar el comando. Las órdenes de comprobación que aparecen más
abajo y que lo leen no funcionarán sobre un clon recién hecho hasta que
`make eval-recuperacion` haya corrido una vez. Lo que sí viaja versionado es el
conjunto etiquetado, que es el dato de entrada y lo único que hay que creerse.

---

## Lo primero, porque es lo que cambia una decisión

**La fusión RRF no gana a la búsqueda vectorial sola. En ninguna métrica.**

| rama | acierto@5 | recall@5 | MRR |
|---|---|---|---|
| BM25 sola | 0,163 | 0,134 | 0,107 |
| **vectorial sola** | **0,959** | **0,824** | **0,752** |
| fusión RRF (lo que corre hoy) | 0,898 | 0,786 | 0,679 |

Comparar los tres intervalos de confianza por separado no responde a la
pregunta, porque las tres ramas se miden sobre las **mismas** 49 consultas. La
comparación tiene que ser pareada, y lo es:

| contraste | diferencia | IC 95 % | ¿excluye el 0? |
|---|---|---|---|
| vectorial − RRF · acierto@5 | +0,061 | [+0,000, +0,143] | no |
| vectorial − RRF · recall@5 | +0,038 | [−0,020, +0,109] | no |
| **vectorial − RRF · MRR** | **+0,072** | **[+0,020, +0,133]** | **SÍ** |

Leído con honestidad: en acierto@5 y recall@5 la diferencia **no se distingue
del ruido** con 49 consultas — y eso es un empate, no una victoria de la
fusión. En MRR la fusión es **medidamente peor**: pone el primer documento
relevante más abajo, y ese intervalo no toca el cero.

O sea: la fusión cuesta código, cuesta una consulta más a Postgres y **no
compra nada**; en la métrica donde sí hay señal, resta. La arquitectura
híbrida, tal y como está hoy sobre este corpus y este tipo de pregunta, **no
está justificada**.

**Por qué**, y esto es lo accionable: `_bm25_search` usa
`plainto_tsquery('spanish', …)`, que une **todos** los términos con AND. Una
pregunta de doce palabras solo casa con un fragmento que contenga las doce.
Medido: **27 de las 49 consultas devuelven CERO candidatos BM25**.

```
$ python3 -c "import json;d=json.load(open('out/eval_recuperacion.json'));print(d['bm25_sin_candidatos'])"
```

En esas 27 la «fusión» no fusiona nada: es la lista vectorial con otro nombre.
En las 22 restantes, BM25 aporta una lista tan mala (acierto@5 = 0,163) que
mezclarla empeora el orden. La rama BM25 no está aportando robustez léxica:
está aportando ruido en una cuarta parte de los casos y nada en el resto.

### ¿Y si se arregla el AND? También medido, y tampoco

Se probó una variante de **diagnóstico** (no es lo que corre en producción) con
los mismos lexemas unidos por OR en vez de por AND:

| rama | acierto@5 | recall@5 | MRR |
|---|---|---|---|
| BM25 con OR | 0,469 | 0,349 | 0,231 |
| fusión RRF sobre esa BM25 | 0,837 | 0,656 | 0,633 |

El OR arregla la rama BM25 (0,163 → 0,469 de acierto@5, casi el triple) y aun
así **la fusión sigue perdiendo contra la vectorial sola**:

| contraste | diferencia | IC 95 % | ¿excluye el 0? |
|---|---|---|---|
| vectorial − RRF(OR) · acierto@5 | +0,122 | [+0,041, +0,224] | SÍ |
| vectorial − RRF(OR) · recall@5 | +0,167 | [+0,072, +0,265] | SÍ |
| vectorial − RRF(OR) · MRR | +0,119 | [+0,004, +0,247] | SÍ |
| RRF(OR) − RRF(AND) · recall@5 | −0,129 | [−0,211, −0,034] | SÍ |

La última fila es la contraintuitiva y por eso se publica: **arreglar BM25
empeora la fusión** en recall@5. Tiene sentido una vez visto: con AND, BM25
estaba callado en 27 consultas y la fusión heredaba el orden vectorial intacto;
con OR, BM25 habla en las 49 y mete candidatos mediocres que desplazan a los
buenos. Una rama léxica a medias es peor que ninguna.

**Lo que este bloque NO dice**: no dice que la recuperación híbrida sea mala
idea en general, ni que BM25 no sirva. Dice que **sobre este corpus (1.031
fragmentos de normativa) y este tipo de consulta (preguntas largas en lenguaje
natural), medido con 49 consultas, no aporta**. Con consultas cortas y llenas
de términos exactos («op.acc.6», «artículo 33»), que es justo donde BM25 luce,
el resultado podría ser el contrario. Ese conjunto no existe y no se ha medido.

---

## F1 · El conjunto de consultas, y la trampa que se evitó

El conjunto vive en [`backend/tests/eval/consultas_corpus.yaml`](../backend/tests/eval/consultas_corpus.yaml).

**Por qué ahí y no en `docs/eval/`**: es el dato de entrada de una medición que
importa el paquete `backend` (`backend.app.corpus.retrieval`,
`backend.app.core.ai.embeddings`) y que se ejecuta dentro del contenedor del
backend. Vive al lado de lo que mide. Es un `.yaml`, así que `make test`
(`pytest backend/tests/`) no lo recoge como test.

**La trampa**: si las consultas se escriben mirando los fragmentos, cada
consulta acaba siendo una paráfrasis del fragmento que la responde, el recall
se dispara y la medición no vale nada.

Se evitó en dos pasos, y el orden es **comprobable en el historial**:

```
$ git log --oneline -- backend/tests/eval/consultas_corpus.yaml
dabcd57 etiqueta a mano los fragmentos que responden a cada una de las 50 consultas
f59ef35 anota 50 consultas de cumplimiento escritas sin mirar el corpus

$ git show f59ef35:backend/tests/eval/consultas_corpus.yaml | grep -c 'relevantes: \[\]'
52          # las 50 consultas + 2 apariciones en los comentarios de la cabecera
```

En el primer commit las 50 preguntas ya están escritas y **todas** las listas de
relevantes están vacías. El etiquetado llega después, en otro commit. Quien
dude puede comprobarlo con esas dos órdenes.

**Cifras del conjunto**: 50 consultas escritas · **49 usables** · 96 etiquetas
(media 1,96 relevantes por consulta). Reparto por norma, calcado al del corpus:
RGPD 15, DORA 13, NIS2 11, ENS 6, eIDAS 5.

**1 consulta excluida** del cálculo, y no se reescribió para que encajara:

> `dora-03` — «¿Qué plazo hay para notificar un incidente grave relacionado con
> las TIC a la autoridad competente?»

El texto de DORA que hay en el corpus (art. 19) remite los plazos concretos a
normas técnicas de regulación que **no están ingeridas**. Se comprobó buscando
«informe intermedio» y «notificación inicial» en los 266 fragmentos de DORA.
Reescribir la pregunta para que tuviera respuesta habría sido cometer la trampa
por la puerta de atrás. Se marca `sin_relevante: true` y el denominador de todo
este documento es **49**.

**El sesgo, dicho en voz alta** (está también en la cabecera del fichero):
etiqueta quien conoce el corpus **y** el sistema que se evalúa, y buscó
candidatos por palabras clave, que es una herramienta emparentada con una de
las tres ramas que se comparan. Eso puede favorecer sistemáticamente a BM25 en
el etiquetado: un fragmento que responde pero no comparte vocabulario con la
pregunta tiene más probabilidad de habérsele escapado al etiquetador y de faltar
en `relevantes`. **La rama que más pierde con ese sesgo es la vectorial** — que
es, precisamente, la que gana. El sesgo empuja en contra del resultado, no a
favor. No hay un segundo etiquetador independiente que lo corrija.

---

## F2 · Métricas y las tres ramas

**Por qué relevancia binaria y no graduada**: la media es de 1,96 fragmentos
relevantes por consulta, y 19 de las 49 tienen exactamente uno. Con uno o dos
relevantes, un nDCG no tiene grados que ordenar — se reduce a una función del
rango del primer acierto, que es lo que ya mide el MRR, pero con un logaritmo
por medio que lo hace más difícil de leer y no añade información. Graduar
exigiría además una escala («responde del todo» / «responde en parte») que este
etiquetador aplicaría con un criterio propio no auditable. Binaria es menos
sofisticada y más honesta.

**Se publican dos lecturas de «recall@k», porque significan cosas distintas:**

- **acierto@k**: ¿hay **al menos un** relevante en el top-k? Es la que importa
  para un RAG: basta con que un fragmento bueno llegue al modelo.
- **recall@k**: fracción de los relevantes recuperada. Es la definición
  estricta. Con 2 relevantes, recall@1 no puede pasar de 0,5, así que sus
  valores bajos en k pequeños son aritmética, no un fallo.

n = 49 consultas. `RRF_K = 60`, `bm25_top = 30`, `vector_top = 30` (los valores
de producción).

```
rama          acierto@1   acierto@3   acierto@5   acierto@10     MRR
BM25              0,061       0,143       0,163        0,163    0,107
vectorial         0,612       0,878       0,959        0,980    0,752
fusión RRF        0,531       0,776       0,898        0,980    0,679
  · diagnóstico, NO es lo que corre en producción ·
BM25 (OR)         0,061       0,286       0,469        0,633    0,231
RRF sobre OR      0,449       0,796       0,837        0,939    0,633

rama           recall@1    recall@3    recall@5    recall@10
BM25              0,026       0,128       0,134        0,134
vectorial         0,379       0,688       0,824        0,904
fusión RRF        0,352       0,619       0,786        0,921
BM25 (OR)         0,048       0,196       0,349        0,526
RRF sobre OR      0,298       0,582       0,656        0,801
```

**El único sitio donde la fusión aporta algo**: recall@10, donde la fusión
(0,921) queda por encima de la vectorial (0,904). Es coherente — a profundidad
10 los pocos candidatos de BM25 añaden algún relevante que la vectorial no
traía. Pero el acierto@10 está empatado (0,980 las dos) y la diferencia de
recall@10 es de 0,017 en la media de fracciones, sin contraste pareado que la
respalde (no se calculó para k=10). No sostiene la arquitectura.

Intervalos de confianza de cada rama por separado (remuestreo de las 49
consultas, 1.000 repeticiones, percentiles 2,5/97,5):

```
rama          acierto@5   IC 95 %             MRR     IC 95 %
BM25              0,163   [0,061, 0,265]    0,107   [0,036, 0,189]
vectorial         0,959   [0,898, 1,000]    0,752   [0,660, 0,844]
fusión RRF        0,898   [0,816, 0,980]    0,679   [0,576, 0,778]
BM25 (OR)         0,469   [0,327, 0,612]    0,231   [0,166, 0,302]
RRF sobre OR      0,837   [0,735, 0,939]    0,633   [0,528, 0,739]
```

---

## F3 · Barrido de RRF_K, y la decisión

`RRF_K` en {1, 5, 10, 20, 30, 60, 100, 200}. Cada punto con su intervalo de
confianza por remuestreo de las consultas (bootstrap, 1.000 repeticiones,
percentiles 2,5/97,5).

```
   k    acierto@5   IC 95 %              MRR     IC 95 %
   1       0,898    [0,816, 0,980]     0,678    [0,577, 0,776]
   5       0,898    [0,816, 0,980]     0,679    [0,576, 0,778]
  10       0,898    [0,816, 0,980]     0,679    [0,576, 0,778]
  20       0,898    [0,816, 0,980]     0,679    [0,576, 0,778]
  30       0,898    [0,816, 0,980]     0,679    [0,576, 0,778]
  60       0,898    [0,816, 0,980]     0,679    [0,576, 0,778]   <- producción
 100       0,898    [0,816, 0,980]     0,679    [0,576, 0,778]
 200       0,898    [0,816, 0,980]     0,679    [0,576, 0,778]
```

La curva no es ruidosa: es **plana**. El acierto@5 es idéntico en los ocho
valores, de 1 a 200. El MRR se mueve una milésima entre k=1 (0,678) y el resto
(0,679).

**Decisión: se queda el 60.** El máximo puntual está en k=1 (por esa milésima
de MRR), y el 60 cae holgadamente dentro de su intervalo de confianza. La regla
acordada dice que en ese caso se elige por parsimonia, y eso es lo que se hace:
no se toca una constante para perseguir una milésima de una curva plana.

**Pero la conclusión honesta del barrido no es «60 está bien»: es que k da
igual.** Y da igual por la misma razón que hunde a la fusión — en 27 de 49
consultas solo hay una lista, y con una sola lista el orden del RRF es el de esa
lista sea cual sea k. En las 22 con dos listas, k solo decide empates de tercer
orden que no llegan a cambiar el top-5. Ajustar `RRF_K` en este sistema es una
palanca desconectada; el problema está aguas arriba.

---

## F4 · La no monotonía del RRF, demostrada (y qué no demuestra)

El RRF puntúa por **rango**, no por puntuación. Quitar un documento de la lista
de candidatos desplaza el rango de todos los que van por debajo **en esa lista**,
y como un documento puede estar en una lista o en las dos, el desplazamiento es
asimétrico. Consecuencia: el orden relativo de A y B puede depender de un
tercero C que no es ninguno de los dos.

**Primero, cómo NO se mide.** La primera versión de esta comprobación
preguntaba «¿cambia la composición del top-5 al quitar un documento no
relevante?» y contestaba **49 de 49**. Esa cifra era vacía: si quitas el que va
5.º, sube el 6.º. Eso pasa en cualquier lista ordenada y no dice nada del RRF.
La cifra se ha tirado y sustituido por el criterio de abajo; queda escrita aquí
porque una cifra vistosa y vacía es exactamente lo que este trabajo persigue.

**Criterio que sí mide algo**: que se **invierta el orden relativo de dos
documentos que siguen estando** en la lista, al quitar un tercero no relevante.

Sobre las 49 consultas, quitando de una en una **cada** documento no relevante
del conjunto de candidatos:

| | consultas |
|---|---|
| exploradas | 49 |
| con al menos una inversión | **12** |
| con al menos una inversión **estricta** (desigualdad real de puntuación) | **1** |
| sin ninguna inversión | 37 |

Las dos cifras en negrita son exhaustivas: para cada consulta se prueba a quitar
**cada uno** de sus candidatos no relevantes, uno a uno. Las 37 sin inversión
son, casi todas, las que se quedan sin candidatos BM25: con una sola lista el
RRF no puede invertir nada.

Y aquí la distinción que hace falta para no vender humo: de las 12 consultas con
inversión, **11 la tienen por un empate**. La puntuación de A y la de B acaban
siendo *exactamente* la misma, y quién va delante lo decide el criterio de
desempate, no el RRF. Eso es un hallazgo, pero es otro (ver «los empates», más
abajo). **Una sola de las 49 consultas tiene una inversión estricta**: A
puntuaba más que B de verdad, y después puntúa menos que B de verdad.

Así que la respuesta honesta a F4 es: **sí existe, se ha encontrado, y es raro**
— 1 de 49 consultas exploradas. Quien esperara que la no monotonía del RRF
zarandee los resultados a todas horas se lleva un chasco; lo que hace es
morderte una vez de cada cincuenta, y ahí va esa vez.

### El ejemplo trabajado

**Consulta `eidas-02`**: *«¿Qué requisitos debe cumplir un prestador cualificado
de servicios de confianza?»*

**Documento que se quita**: `27ef0472` — **no relevante**, y **no estaba en el
top-5** (iba 8.º en la lista vectorial). Es el caso fuerte: un documento que el
usuario nunca habría visto y que a nadie le importa.

> `(45) A fin de permitir un proceso de puesta en marcha eficiente, que lleve a
> la inclusión de los prestadores cualificados de servicios de confianza…`

**Top-5 ANTES** (`RRF_K = 60`):

| # | fragmento | rango BM25 | rango vect. | puntuación RRF | ¿relevante? |
|---|---|---|---|---|---|
| 1 | `5b1a0bf8` | 3 | 7 | **0,03079839** | no |
| 2 | `d9be4303` | 1 | 10 | **0,03067916** | no |
| 3 | `3fbb833e` | 4 | 11 | 0,02970951 | **sí** |
| 4 | `e45c0bee` | — | 1 | 0,01639344 | **sí** |
| 5 | `63c9ea3c` | — | 2 | 0,01612903 | no |

**Top-5 DESPUÉS de quitar `27ef0472`**:

| # | fragmento | rango BM25 | rango vect. | puntuación RRF | ¿relevante? |
|---|---|---|---|---|---|
| 1 | `d9be4303` | 1 | **9** | **0,03088620** | no |
| 2 | `5b1a0bf8` | 3 | 7 | **0,03079839** | no |
| 3 | `3fbb833e` | 4 | 10 | 0,02991071 | **sí** |
| 4 | `e45c0bee` | — | 1 | 0,01639344 | **sí** |
| 5 | `63c9ea3c` | — | 2 | 0,01612903 | no |

**Los puestos 1 y 2 se han intercambiado**, y la aritmética se puede seguir a
mano:

```
ANTES
  5b1a0bf8 = 1/(60+3) + 1/(60+7)  = 0,01587302 + 0,01492537 = 0,03079839
  d9be4303 = 1/(60+1) + 1/(60+10) = 0,01639344 + 0,01428571 = 0,03067916
                                     5b1a0bf8  >  d9be4303      (por 0,00011923)

Se quita 27ef0472, que iba 8.º en la lista vectorial.
  · 5b1a0bf8 iba 7.º: está POR ENCIMA del que se ha ido, no se mueve.
  · d9be4303 iba 10.º: está POR DEBAJO, sube al 9.º.

DESPUÉS
  5b1a0bf8 = 1/(60+3) + 1/(60+7)  = 0,03079839   (igual)
  d9be4303 = 1/(60+1) + 1/(60+9)  = 0,01639344 + 0,01449275 = 0,03088620
                                     d9be4303  >  5b1a0bf8      (por 0,00008781)
```

Ahí está la no monotonía, sin metáforas: **el orden relativo de `5b1a0bf8` y
`d9be4303` lo decidió un tercer documento que no es ninguno de los dos, que no
es relevante, y que ni siquiera aparecía en el resultado.** Basta con que ese
tercero se cuele entre ellos en una de las dos listas para que el que va por
debajo gane un puesto —y con él un `1/(60+r)` un pelín mayor— mientras el que va
por encima se queda igual.

En este caso concreto el daño es cosmético: los dos que se intercambian son no
relevantes y el conjunto de cinco no cambia. Pero la propiedad es la que es, y
donde muerde de verdad es en la frontera del top-k, en el puesto 5 contra el 6.

Reproducirlo:

```
$ python3 -c "
import json; d=json.load(open('out/eval_recuperacion.json'))
e=d['f4_no_monotonia']['ejemplos'][0]
print(e['consulta'], e['quitado'], e['inversiones_estrictas'])"
```

### Los empates: un hallazgo que salió buscando otra cosa

Persiguiendo la no monotonía apareció algo que no se buscaba. En 11 de las 12
inversiones, las puntuaciones RRF de dos documentos coinciden **exactamente**.
No es casualidad: el RRF sólo puede tomar valores de la forma `1/(60+r)` y
sumas de dos de ellos, así que un documento que va 3.º en la lista vectorial y
otro que va 3.º en la lista BM25 puntúan **lo mismo**, `1/63`, y los empates son
frecuentes por construcción.

¿Cómo se deshace ese empate en producción? Así
(`backend/app/corpus/retrieval.py`):

```python
all_chunks = set(bm25_ranks) | set(vector_ranks)      # un set
...
top_ids = sorted(rrf_scores, key=lambda c: rrf_scores[c], reverse=True)[:top_k]
```

`sorted` es estable, así que ante un empate respeta el orden de iteración del
diccionario, que viene del orden de iteración de un **`set` de cadenas**. Ese
orden depende del `hash()` de cada cadena, y en CPython el hash de las cadenas
está **aleatorizado por proceso** salvo que se fije `PYTHONHASHSEED`.

Consecuencia, que no se ha medido y por tanto no se afirma como fallo
observado: **ante un empate, dos procesos distintos del backend pueden devolver
el top-5 en distinto orden para la misma consulta y el mismo corpus.** Es una
hipótesis con una base de código clara, no una medición: para confirmarla haría
falta ejecutar la misma consulta en dos procesos con `PYTHONHASHSEED` distinto y
comparar, y eso **no se ha hecho**. Queda anotado en «lo que no se ha medido».

El arnés de evaluación de este documento **sí** desempata de forma
determinista (por `chunk_id`), porque una medición que cambia entre ejecuciones
no es una medición. Esa es una diferencia deliberada entre el arnés y
producción, y está escrita en el código del arnés.

---

## F5 · Los prefijos de e5 y el agrupamiento

El modelo `intfloat/multilingual-e5-large` se entrena esperando `query: ` en la
consulta y `passage: ` en el documento. Asimetría = pérdida de calidad
silenciosa. Se comprobaron los dos lados, y **no leyendo el código, sino
midiendo sobre la base**.

### ¿Se aplica `query: ` en la consulta? Sí

`backend/app/corpus/retrieval.py` define `E5_QUERY_PREFIX = "query: "` y lo
aplica en `_vector_search`:

```python
raw_emb = provider.embed_query(E5_QUERY_PREFIX + query)
```

### ¿Se aplica `passage: ` en el documento? Sí — y esto contradecía la hipótesis

La sospecha de partida, leyendo `scripts/corpus_ingest_v2.py`, era que **no**:
ese script llamaba a `emb.embed_documents(batch)` con el texto pelado. La
hipótesis era «el corpus está mal embebido».

**Era falsa, y se comprobó midiendo**: se coge una muestra de fragmentos, se
vuelve a embeber su `content` de tres formas y se compara cada resultado con el
vector que ya está guardado en la columna `embedding`.

Coseno contra el vector guardado (un fragmento por fuente; la muestra completa
son 3 por fuente, 15 en total, y está en el JSON):

```
fuente          sin prefijo     passage:       query:      veredicto
RD_311_2022         0.99203      1.00000      0.95906  ->  passage
UE-DORA             0.99426      1.00000      0.95868  ->  passage
UE-EIDAS            0.99393      1.00000      0.96853  ->  passage
UE-NIS2             0.98260      1.00000      0.92897  ->  passage
UE-RGPD             0.99470      1.00000      0.95719  ->  passage
```

`1.00000` clavado, unánime en los **15** fragmentos de la muestra. Y nótese que
sin prefijo el coseno ya sale a 0,98–0,99: el prefijo mueve poco el vector, que
es exactamente lo que anticipa el A/B de más abajo, donde el efecto medido es
pequeño. La prueba no es que `passage` gane, es que da **1,00000 exacto**
mientras las otras dos no.
El corpus cargado **sí** lleva `passage: `; lo ingirió otro camino, no el
`corpus_ingest_v2.py`. Los dos lados son simétricos y **no había nada que
arreglar en los datos**.

### Pero sí había dos agujeros, y se han tapado

**1. `scripts/corpus_ingest_v2.py` no ponía el prefijo.** Es el ingestor que el
propio repositorio documenta como el vigente («Replaces
`scripts/corpus_ingest.py`»). El corpus actual no está afectado, pero
**cualquier documento añadido con él** habría quedado en un espacio distinto
del de las consultas, sin ningún error visible. Arreglado (una línea) y con el
porqué escrito al lado.

**2. El suelo `fastembed>=0.4.2` permitía un agrupamiento distinto.** Al cargar
el modelo, la propia librería avisa:

```
UserWarning: The model intfloat/multilingual-e5-large now uses mean pooling
instead of CLS embedding. In order to preserve the previous behaviour, consider
either pinning fastembed version to 0.5.1 or using `add_custom_model`.
```

e5 se entrena con agrupamiento por **media**, así que la media es lo correcto y
la versión instalada (0.8.0) hace lo correcto. **Que el corpus guardado también
esté agrupado por media no es una suposición: es lo que prueba el coseno
`1.00000` de la tabla de arriba**, calculado con el modelo actual. Lo que era un
peligro es el suelo: `>=0.4.2` dejaba resolver 0.4.2–0.5.1, que agrupan por CLS,
y entonces los embeddings del corpus y los de las consultas habrían vivido en
espacios distintos sin que nada fallara. El suelo sube a `>=0.6.0`.

**Lo que NO se ha medido de esto**: cuánto costaría exactamente esa mezcla
CLS/media. Haría falta instalar fastembed 0.5.1 y volver a medir, y no se ha
hecho. Se afirma el riesgo, no su magnitud.

### El antes y el después del prefijo, con su barra de error

Como no había nada roto que arreglar, el «antes y después» que se puede publicar
es el A/B contrario: **cuánto costaría** la asimetría que el ingestor v2 habría
introducido. Se vuelven a embeber los 1.031 fragmentos de las dos formas y se
compara. La búsqueda vectorial se hace en numpy en los dos lados, para que sea
exactamente la misma operación; antes de usarla se comprueba que reproduce
pgvector: **top-5 idéntico en 49/49 consultas**.

| métrica | con `passage: ` | sin prefijo | diferencia | IC 95 % | ¿excluye el 0? |
|---|---|---|---|---|---|
| vectorial · acierto@1 | 0,612 | 0,653 | −0,041 | [−0,102, +0,000] | no |
| vectorial · acierto@5 | 0,959 | 0,939 | +0,020 | [+0,000, +0,061] | no |
| **vectorial · recall@5** | **0,824** | **0,795** | **+0,029** | **[+0,005, +0,061]** | **SÍ** |
| vectorial · MRR | 0,752 | 0,755 | −0,003 | [−0,039, +0,026] | no |
| fusión · acierto@5 | 0,898 | 0,857 | +0,041 | [+0,000, +0,102] | no |
| fusión · MRR | 0,679 | 0,683 | −0,003 | [−0,028, +0,014] | no |

**Y aquí toca no vender el resultado.** El titular vendible sería «poner el
prefijo mejora el recall@5 un 3 %», y es literalmente cierto: es la única fila
cuyo intervalo no toca el cero. Pero el resto de la tabla dice otra cosa: en
acierto@1 el prefijo sale **peor** (−0,041, aunque el intervalo toca el cero) y
en MRR la diferencia es de tres milésimas en ambas ramas. Con 49 consultas, el
efecto medido de poner o quitar el prefijo del lado del documento es **pequeño y
no apunta todo en la misma dirección**.

La conclusión honesta: el prefijo debe ponerse porque es lo que el modelo espera
y porque el arreglo cuesta una línea, no porque estos números demuestren una
mejora contundente. **No la demuestran.** Con este corpus, el modelo tolera bien
la asimetría; el argumento para arreglarlo es de corrección, no de rendimiento.

**Tiempo del re-embebido**, por si alguien lo repite: **1.031 fragmentos en
288–368 s por pasada** (dos pasadas por ejecución), en lotes de 32, sobre CPU.
La primera versión lo intentó en un solo lote de 1.031: se comió 12,8 GB y no
había terminado a los 13 minutos. Por eso va por lotes.

---

## F6 · Latencia

p50 y p95 de la búsqueda completa, desglosada por etapa. **5 repeticiones × 49
consultas = 245 medidas por etapa. Con calentamiento**: se hace una llamada al
modelo antes de empezar a medir, para que la carga perezosa del modelo ONNX no
se cuele en la primera muestra.

Tres ejecuciones de la misma medición en el mismo equipo:

| etapa | ejec. 1 p50 | p95 | ejec. 2 p50 | p95 | ejec. 3 p50 | p95 |
|---|---|---|---|---|---|---|
| embebido de la consulta | 30,66 | 45,82 | 148,95 | 316,99 | 33,09 | 54,00 |
| BM25 (Postgres) | 0,52 | 0,68 | 0,76 | 4,71 | 0,54 | 0,71 |
| vectorial (pgvector) | 3,05 | 4,19 | 5,18 | 12,03 | 3,14 | 4,24 |
| fusión RRF (Python) | 0,03 | 0,04 | 0,04 | 0,07 | 0,03 | 0,05 |
| **TOTAL** | **34,56** | **50,14** | **160,42** | **323,85** | **36,96** | **58,65** |

Todo en milisegundos.

**La ejecución 2 se sale por un factor de 4,3 y no sé por qué.** Eso es el
resultado, y va aquí en vez de en una nota al pie.

La hipótesis obvia era la carga del anfitrión: ese equipo tiene 14 núcleos y
había otro proceso trabajando en paralelo. **La hipótesis no se sostiene con lo
medido**: la ejecución 3, la lenta candidata, se hizo con carga media
**16,23** y dio 36,96 ms; la ejecución 2, con carga observada entre 10 y 15, dio
160,42 ms. Con más carga salió más rápido. La carga media, por sí sola, no
separa los casos.

Lo que distingue a la 2 de las otras dos, y es **una conjetura sin comprobar**:
se solapó con el final de un `make clean && make demo` en la misma máquina, es
decir con un `docker build` del frontend. Un build satura el ancho de banda de
memoria y las cachés de forma que la carga media de un minuto refleja mal, y la
etapa que se lleva el golpe es justo la que hace aritmética densa: el embebido
(×4,9), mientras que las consultas a Postgres apenas se mueven (×1,5 y ×1,7).
Encaja, pero **no se ha medido**: haría falta repetir la ejecución con y sin un
build simultáneo, y no se ha hecho.

Lo que sí se puede afirmar:

- **Hay una varianza grande entre ejecuciones que la carga media no explica.**
  Cualquier cifra de latencia de este sistema debe leerse con eso delante.
- Por eso el script anota ahora la carga del anfitrión (`/proc/loadavg`) y el
  número de núcleos **dentro del propio JSON de resultados**, junto a la
  latencia. No arregla la varianza, pero impide que la cifra viaje sin su
  contexto.

Y esto se sostiene en las tres ejecuciones, que es lo accionable:

- **El embebido de la consulta se lleva entre el 89 % y el 93 % del tiempo**
  (30,66 de 34,56 = 88,7 %; 148,95 de 160,42 = 92,9 %; 33,09 de 36,96 = 89,5 %).
  Todo lo demás es ruido a su lado.
- **La fusión RRF es gratis**: 0,03 ms, un 0,09 % del total. Quitarla no
  ahorraría tiempo — el argumento para quitarla es de calidad (F2), no de
  latencia.
- **Las dos consultas a Postgres juntas son ~3,6 ms**, un 10 % del total. El
  índice vectorial no es el cuello de botella con 1.031 fragmentos.

Si alguna vez hay que bajar la latencia de este camino, el sitio donde mirar es
el embebido de la consulta, no la base de datos ni la fusión.

**Lo que NO mide F6**: nada de esto incluye la llamada al modelo de lenguaje que
viene después. Es el tiempo de **recuperar los fragmentos**, no el de responder.

---

## Qué hacer con todo esto

Las decisiones, separadas de las conjeturas:

1. **`RRF_K` se queda en 60.** Cae dentro del intervalo del máximo puntual y el
   barrido es plano. Se elige por parsimonia, como estaba acordado. Lo que
   cambia es el comentario: ya no es «la constante del artículo», es «el valor
   por defecto, medido, indistinguible de cualquier otro entre 1 y 200 sobre
   este corpus».
2. **La fusión híbrida queda en entredicho, con número.** No gana a la vectorial
   sola en ninguna métrica y pierde en MRR con un intervalo que no toca el cero.
   La decisión de retirarla o de arreglar la rama léxica **no se toma en este
   bloque** —cambiar el buscador de producción es otro trabajo, con sus tests—
   pero queda medida y documentada, que es lo que faltaba.
3. **Dos agujeros del prefijo de e5, tapados** (ingestor v2 y suelo de
   fastembed), con la honestidad de que el A/B **no** demuestra una mejora
   grande.

## Lo que NO se ha medido, y por tanto no se afirma

- **La calidad de la respuesta del copiloto.** Todo esto mide qué fragmentos
  llegan al modelo. Que el modelo responda bien con ellos es otra cosa, y no se
  ha tocado.
- **Consultas cortas con términos exactos** («op.acc.6», «artículo 33»), que son
  justo donde BM25 debería lucir. El conjunto son 49 preguntas largas en
  lenguaje natural. Es plausible que con consultas de ese otro tipo la fusión
  gane; **plausible no es medido**, y hacerlo exige otro conjunto etiquetado.
- **El no determinismo del desempate en producción.** Hay una base de código
  clara para sospecharlo (orden de iteración de un `set` + hash aleatorizado por
  proceso), pero no se ha ejecutado la comprobación con dos `PYTHONHASHSEED`
  distintos. Es una hipótesis, no un hallazgo.
- **El coste de mezclar agrupamiento CLS y media.** Exigiría instalar fastembed
  0.5.1 y volver a medir. No se ha hecho.
- **Un segundo etiquetador.** Las 96 etiquetas las puso una sola persona, que
  además conoce el sistema evaluado. El sesgo está declarado, no corregido.
- **Corpus distintos del cargado.** Todas las cifras son sobre estos 1.031
  fragmentos. El script imprime los recuentos que encuentra antes de medir, para
  que nunca se lea una tabla sin saber contra qué se midió.
- **La causa de la varianza de latencia de F6.** Una de las tres ejecuciones
  salió 4,3 veces más lenta y la carga media del anfitrión no lo explica. La
  conjetura (un `docker build` simultáneo) no se ha comprobado: haría falta
  repetir la medición con y sin build en paralelo.
- **Reranking con cross-encoder.** El propio `retrieval.py` lo menciona como
  paso 4 pendiente. No existe, así que no se ha medido.

## Cómo repetirlo entero

```
make demo                 # si la pila no está en pie
make eval-recuperacion    # ~13 min: descarga el modelo la primera vez,
                          # mide, y deja out/eval_recuperacion.json
```

Con `EVAL_AB_PREFIJO=no` se salta el A/B de F5 (el re-embebido de los 1.031
fragmentos, que es lo que más tarda) y baja a un par de minutos.

Comprobado que reproduce: las tablas de F2, F2b y F3 de este documento salieron
idénticas en **cuatro ejecuciones**, **dos de ellas sobre una pila levantada de
cero** con `make clean && make demo` (contenedores nuevos, volúmenes nuevos,
corpus resembrado desde el volcado, modelo descargado otra vez). También salió
idéntica la tabla de cosenos de F5, que es la que dice con qué prefijo está
embebido el corpus.

Aviso para quien lo repita: el primer intento de `make eval-recuperacion` sobre
un contenedor recién construido **falló** después de doce minutos de cálculo,
porque `/app/out` no es escribible por el usuario del backend. Está arreglado
(la salida va a `/tmp` dentro del contenedor y se copia fuera), pero se cuenta
porque es justo el tipo de fallo que sólo aparece cuando alguien ejecuta el
comando de verdad en vez de darlo por bueno.
