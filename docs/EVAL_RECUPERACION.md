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

**La fusión RRF se ha quitado del producto.** No por criterio arquitectónico:
porque se midió que perdía, se arregló la rama que estaba rota, se volvió a
medir, y perdía más.

Esta sección se ha reescrito el **2026-09-11**. La versión anterior sacaba la
conclusión antes de tiempo y hay que decir en qué: concluía que la fusión no
servía teniendo la rama léxica **rota por el analizador**. Descartar una
arquitectura con una de sus dos mitades desenchufada no es una medición, es un
accidente con suerte. Lo que sigue es la medición con las dos mitades
enchufadas.

### El defecto que estaba desactivando media recuperación en silencio

`plainto_tsquery('spanish', …)` une **todos** los lexemas con `&`, es decir con
AND. Una pregunta natural de diez palabras exigía que **un mismo fragmento**
contuviera las diez. Medido sobre las 49 consultas etiquetadas:

| analizador | consultas sin UN SOLO candidato léxico |
|---|---|
| `plainto_tsquery` (AND) — lo que corría hasta 2026-09-11 | **27 de 49** |
| operador reescrito a OR — lo que corre ahora | **0 de 49** |

```
$ python3 -c "import json;d=json.load(open('out/eval_recuperacion.json'));\
print({k:v['n'] for k,v in d['lexico_sin_candidatos'].items()})"
{'or_produccion': 0, 'and_anterior': 27}
```

El arreglo es una línea, y consiste en reescribir el operador del tsquery **ya
analizado**, que conserva el lematizado y las palabras vacías del analizador
`spanish` en vez de volver a trocear la cadena a mano:

```sql
replace(plainto_tsquery('spanish', :q)::text, '&', '|')::tsquery
```

Y funciona: la rama léxica mejora de verdad, con las tres diferencias pareadas
excluyendo el cero.

| contraste (léxico OR − léxico AND) | diferencia | IC 95 % | ¿excluye el 0? |
|---|---|---|---|
| hitrate@5 | +0,265 | [+0,102, +0,429] | **SÍ** |
| recall@5 | +0,180 | [+0,041, +0,313] | **SÍ** |
| MRR | +0,137 | [+0,035, +0,236] | **SÍ** |

### Y con la rama arreglada, la fusión pierde más

| rama | hitrate@5 | recall@5 | MRR |
|---|---|---|---|
| léxica sola, AND (el defecto) | 0,163 | 0,134 | 0,107 |
| léxica sola, OR (arreglada) | 0,429 | 0,315 | 0,244 |
| **vectorial sola** | **0,959** | **0,824** | **0,752** |
| fusión RRF con la léxica arreglada | 0,857 | 0,667 | 0,627 |
| fusión RRF con la léxica rota | 0,898 | 0,786 | 0,679 |

Las tres ramas se miden sobre las **mismas** 49 consultas, así que la
comparación es pareada o no es comparación:

| contraste | diferencia | IC 95 % | ¿excluye el 0? |
|---|---|---|---|
| vectorial − fusión · hitrate@5 | +0,102 | [+0,020, +0,204] | **SÍ** |
| vectorial − fusión · recall@5 | +0,157 | [+0,065, +0,255] | **SÍ** |
| vectorial − fusión · MRR | +0,125 | [+0,013, +0,246] | **SÍ** |
| fusión(OR) − fusión(AND) · recall@5 | −0,119 | [−0,204, −0,027] | **SÍ** |

Antes del arreglo, sólo el MRR distinguía la vectorial de la fusión y las otras
dos métricas eran un empate dentro del ruido. **Con la rama léxica funcionando,
las tres excluyen el cero.** Y la última fila es la contraintuitiva, que es
justo la que hay que publicar: **arreglar la rama léxica empeora la fusión**.
Tiene sentido una vez visto — con AND, la rama estaba callada en 27 consultas y
la fusión heredaba el orden vectorial intacto; con OR habla en las 49 y mete
candidatos mediocres que desplazan a los buenos.

### El dato que cierra la puerta

Las medias no bastan para quitar una rama: una rama puede tener peor media y
aun así ser la única que rescata ciertas consultas. Así que se midió eso
directamente — cuántos fragmentos **relevantes** aparecen entre los candidatos
léxicos y **no** entre los vectoriales:

| | fragmentos relevantes aportados en exclusiva | consultas |
|---|---|---|
| sólo la rama léxica | **0 de 96** | **0 de 49** |
| sólo la rama vectorial | 25 de 96 | 19 de 49 |

Y consultas en las que el único relevante recuperado lo trae la rama léxica:
**ninguna**.

```
$ python3 -c "import json;d=json.load(open('out/eval_recuperacion.json'));\
a=d['f2c_aporte_unico_de_cada_rama'];\
print(a['relevantes_solo_lexico'],'/',a['relevantes_totales'],\
      '· rescates:',a['consultas_que_SOLO_rescata_la_rama_lexica'])"
0 / 96 · rescates: []
```

No es que la rama léxica pese poco. Es que **no aporta nada que el vector no
traiga ya**, y desplaza lo que sí aporta. Eso es lo que convierte «quitarla» en
una decisión medida en vez de una preferencia.

### Y no hay peso que la salve

Antes de borrar se barrió el peso de la rama léxica en la fusión, de 0 a 1 de
0,1 en 0,1, donde **w = 0 es exactamente no fusionar** y w = 0,5 es el RRF
clásico que corría. Si la fusión valiera algo con otro reparto, saldría aquí.

| w (peso de la léxica) | hitrate@5 | recall@5 | MRR |
|---|---|---|---|
| **0,0 — sin fusión** | **0,959** | **0,824** | 0,752 |
| 0,1 | 0,959 | 0,783 | **0,770** |
| 0,2 | 0,918 | 0,750 | 0,759 |
| 0,3 | 0,878 | 0,721 | 0,711 |
| 0,4 | 0,878 | 0,694 | 0,701 |
| 0,5 — el RRF que corría | 0,857 | 0,667 | 0,627 |
| 0,6 | 0,837 | 0,656 | 0,556 |
| 0,7 | 0,837 | 0,636 | 0,538 |
| 0,8 | 0,796 | 0,585 | 0,506 |
| 0,9 | 0,633 | 0,473 | 0,437 |
| 1,0 — sólo léxica | 0,429 | 0,315 | 0,247 |

La curva es monótona decreciente y su máximo está en w = 0. De los **30
contrastes pareados** de cada peso contra w = 0, **ninguno** excluye el cero en
la dirección de mejorar.

Hay una excepción que merece decirse en voz alta porque va en contra de la
conclusión: en **MRR**, w = 0,1 da 0,770 frente a 0,752 de w = 0. Es el único
número de toda la tabla que apunta a favor de fusionar. Y no se ha usado para
decidir, porque su contraste pareado **no excluye el cero**: es exactamente el
máximo puntual de una curva ruidosa contra el que este bloque avisa. Si la
conclusión se hubiera querido invertir, ese es el número que habría que haber
pescado.

### Qué se ha hecho, en el código

- La rama léxica se arregló (OR) **y luego se quitó**, junto con la fusión.
  `backend/app/corpus/retrieval.py` hace ahora una sola cosa: ranking vectorial.
- `hybrid_search` → `corpus_search`, `HybridResult` → `CorpusResult`,
  `rrf_score` → `score` (el coseno de ese fragmento). Un nombre que promete una
  fusión que no existe es la misma clase de defecto que llamar BM25 a lo que no
  lo es.
- El arnés de evaluación **sigue midiendo las cinco ramas**, incluidas las dos
  que ya no corren. Es deliberado: 1.031 fragmentos, un modelo y 49 consultas es
  el alcance de esta evidencia, y `make eval-recuperacion` es lo que debe volver
  a responder la pregunta cuando el corpus crezca o cambie el modelo. Medir la
  rama que se quitó es la única forma de saber cuándo habría que devolverla.

**Lo que esto NO dice**: no dice que la recuperación híbrida sea mala idea, ni
que un ranking léxico no sirva. Dice que **sobre este corpus (1.031 fragmentos
de normativa), con este modelo (e5-large) y este tipo de consulta (preguntas
largas en lenguaje natural), medido con 49 consultas, no aporta**. Con consultas
cortas de términos exactos («op.acc.6», «artículo 33»), que es donde un ranking
léxico luce, el resultado podría ser el contrario — y para ese caso concreto ya
existe una vía que no depende de acertar el ranking: el filtro `measure_codes`
de `corpus_search`, que va por igualdad sobre la columna. Ese conjunto de
consultas cortas no existe y no se ha medido.

---

## No era BM25, y el código lo llamaba así

Hasta el 2026-09-11 el módulo, la API y este informe llamaban «BM25» a la rama
léxica. No lo era, y no es un detalle de nombres.

PostgreSQL **no implementa BM25**. `ts_rank_cd` puntúa la *densidad de
coincidencias dentro del documento*: cuenta las apariciones, las pondera por
etiqueta de posición (A/B/C/D) y premia que los términos estén cerca unos de
otros. Le faltan las dos mitades que hacen que BM25 funcione:

1. **La IDF — la rareza del término en el corpus entero.** Para `ts_rank_cd`,
   que un fragmento contenga «seguridad» (presente en casi todos los 1.031) pesa
   igual que si contiene «eIDAS» (presente en 115). BM25 hace lo contrario, y
   ese es su mecanismo central: lo raro discrimina, lo común no informa. Un
   ranking sin IDF, ante una pregunta larga en lenguaje natural, se deja
   arrastrar por las palabras vacías de contenido, que son la mayoría.
2. **La normalización contra la longitud MEDIA del corpus** (el término
   `b·|d|/avgdl`). `ts_rank_cd` admite banderas de normalización, pero todas
   dividen por la longitud del *propio* documento; ninguna la compara con la
   media, que es lo que impide que los fragmentos largos ganen por acumulación.

El nombre importaba porque hacía esperar de esa rama un comportamiento que no
tenía, y porque durante meses tapó el defecto real: si crees que tienes BM25,
que devuelva pocos resultados parece rigor. Sabiendo que es `ts_rank_cd` con los
términos en AND, que devuelva cero en 27 de 49 consultas es lo que es.

Si algún día hiciera falta BM25 de verdad sobre Postgres, existe la extensión
`pg_search`/`ParadeDB`; con la extensión pelada no se puede. Eso no se ha
probado y no se afirma que haga falta.

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

## F2 · Métricas y las ramas

### Dos métricas que no son la misma, y hasta ahora se llamaban igual

Este informe llamaba «acierto@k» a una de ellas, y ese nombre no distinguía. Se
renombra, en el informe y en el JSON:

- **hitrate@k**: fracción de **consultas** con **al menos un** relevante en el
  top-k. Vale 0 o 1 por consulta. Responde *«¿le llegó algo útil al modelo?»*, y
  es la que importa para un RAG.
- **recall@k**: fracción media de **los relevantes de cada consulta** que caen
  en el top-k. Responde *«¿le llegó todo lo útil?»*.

Con 96 etiquetas sobre 49 consultas —1,96 relevantes de media, hasta 4 en
algunas— divergen: una consulta con 4 relevantes de los que entra 1 en el top-5
puntúa hitrate@5 = 1,000 y recall@5 = 0,250. Con 2 relevantes, recall@1 no puede
pasar de 0,5, así que sus valores bajos en k pequeños son aritmética y no un
fallo.

### Por qué relevancia binaria y no graduada

La media es de 1,96 fragmentos relevantes por consulta, y 19 de las 49 tienen
exactamente uno. Con uno o dos relevantes, un nDCG no tiene grados que ordenar —
se reduce a una función del rango del primer acierto, que es lo que ya mide el
MRR, pero con un logaritmo por medio que lo hace más difícil de leer y no añade
información. Graduar exigiría además una escala («responde del todo» / «responde
en parte») que este etiquetador aplicaría con un criterio propio no auditable.
Binaria es menos sofisticada y más honesta.

### Las cifras

n = **49** consultas (el conjunto tiene 50; ver F1 para por qué una se excluye).
`vector_top = 30`, `lexico_top = 30`. Las filas marcadas ya **no corren en
producción**: la léxica y las dos fusiones se conservan en el arnés para poder
volver a decidir cuando cambie el corpus.

```
rama            hitrate@1   hitrate@3   hitrate@5   hitrate@10     MRR
vectorial  ★        0,612       0,878       0,959        0,980    0,752
  · ya no corren en producción, se siguen midiendo ·
lexico (OR)         0,082       0,286       0,429        0,673    0,244
lexico (AND)        0,061       0,143       0,163        0,163    0,107
rrf   (OR)          0,429       0,816       0,857        0,939    0,627
rrf   (AND)         0,531       0,776       0,898        0,980    0,679

rama             recall@1    recall@3    recall@5    recall@10
vectorial  ★        0,379       0,688       0,824        0,904
lexico (OR)         0,044       0,192       0,315        0,553
lexico (AND)        0,026       0,128       0,134        0,134
rrf   (OR)          0,281       0,592       0,667        0,794
rrf   (AND)         0,352       0,619       0,786        0,921
```

**El único sitio donde la fusión gana, y por qué no sostiene la arquitectura**:
en recall@10 la fusión con la léxica **rota** (0,921) queda por encima de la
vectorial (0,904). Ese número existe y hay que enseñarlo. Lo que le quita peso
no es una opinión sino F2c: la rama léxica aporta **0 de 96** relevantes que la
vectorial no traiga en su top-30. Si no aporta ningún relevante propio, ese
+0,017 de recall@10 sólo puede venir de reordenar dentro de lo que la vectorial
ya tenía — y a cambio la fusión pierde en hitrate@5, recall@5 y MRR con los tres
intervalos excluyendo el cero. Además desaparece en cuanto se arregla la rama
(la fusión OR baja a 0,794).

Intervalos de confianza de cada rama por separado (remuestreo de las 49
consultas, 1.000 repeticiones, percentiles 2,5/97,5). **No se comparan entre sí**
—para eso están los contrastes pareados de la cabecera—, sirven para ver la
anchura que impone una muestra de 49:

```
rama            hitrate@5   IC 95 %             MRR     IC 95 %
vectorial  ★        0,959   [0,898, 1,000]    0,752   [0,660, 0,844]
lexico (OR)         0,429   [0,286, 0,571]    0,244   [0,175, 0,318]
lexico (AND)        0,163   [0,061, 0,265]    0,107   [0,036, 0,189]
rrf   (OR)          0,857   [0,755, 0,959]    0,627   [0,529, 0,728]
rrf   (AND)         0,898   [0,816, 0,980]    0,679   [0,576, 0,778]
```

---

## F3 · Barrido de RRF_K, y por qué la respuesta cambió

`RRF_K` en {1, 5, 10, 20, 30, 60, 100, 200}, sobre la fusión con la rama léxica
**arreglada**. Cada punto con su intervalo por remuestreo de las consultas
(bootstrap, 1.000 repeticiones, percentiles 2,5/97,5).

```
   k    hitrate@5   IC 95 %              MRR     IC 95 %
   1       0,878    [0,776, 0,959]     0,653    [0,553, 0,748]
   5       0,918    [0,837, 0,980]     0,650    [0,557, 0,746]   <- máximo puntual
  10       0,878    [0,776, 0,959]     0,662    [0,567, 0,760]
  20       0,857    [0,755, 0,959]     0,655    [0,555, 0,755]
  30       0,857    [0,755, 0,959]     0,651    [0,551, 0,752]
  60       0,857    [0,755, 0,959]     0,627    [0,529, 0,728]   <- el que corría
 100       0,857    [0,755, 0,959]     0,627    [0,529, 0,728]
 200       0,857    [0,755, 0,959]     0,627    [0,529, 0,728]
```

**Este barrido también estaba contaminado por el defecto del analizador, y la
conclusión anterior era falsa.** La versión anterior de este informe publicaba
una curva **plana** —hitrate@5 idéntico en los ocho valores— y concluía que «k es
una palanca desconectada». Lo era, pero no por lo que decía: era plana porque
con el AND, 27 de 49 consultas tenían **una sola lista**, y con una sola lista el
orden del RRF es el de esa lista sea cual sea k. La palanca no estaba
desconectada: estaba desconectada la de al lado.

Con la rama léxica funcionando, k **sí** hace algo: hitrate@5 va de 0,918 en k=5
a 0,857 de k≥20 en adelante. Sigue siendo un efecto pequeño frente a la anchura
de los intervalos con 49 consultas, y el 60 cae dentro del intervalo del máximo
(k=5), así que por parsimonia el 60 se habría quedado.

**Pero la decisión de k ya no aplica**, y esta es la conclusión que se lleva el
apartado: la fusión se ha quitado (ver la cabecera), así que `RRF_K` no existe en
producción. El barrido se conserva porque es lo que habría que volver a mirar si
la fusión regresara, y porque enseña de qué forma un defecto aguas arriba
falsifica una curva entera sin que salte ningún error.

---

## F4 · La no monotonía del RRF, demostrada (y qué no demuestra)

Este apartado se mantiene aunque la fusión ya no corra, por dos razones: es lo
que se pidió demostrar, y explica una parte de por qué fusionar por rango salía
caro. Todas las cifras son de la fusión **con la rama léxica arreglada**.

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

| | con la léxica arreglada (OR) | con la léxica rota (AND) |
|---|---|---|
| consultas exploradas | 49 | 49 |
| con al menos una inversión | **49** | 12 |
| con al menos una inversión **estricta** | **38** | 1 |
| en las que la inversión llega al top-5 | **31** | — |
| sin ninguna inversión | **0** | 37 |

La columna de la derecha es la que publicaba la versión anterior de este
informe, y **también estaba falseada por el defecto del analizador**: las 37
consultas «sin inversión» eran, casi todas, las que se quedaban sin candidatos
léxicos. Con una sola lista el RRF no puede invertir nada, así que aquello no
medía el RRF: medía cuántas veces la fusión no fusionaba. La conclusión
anterior —«existe pero es raro, 1 de 49»— era falsa.

Con las dos listas de verdad, la respuesta es la contraria y mucho más fuerte:
**la no monotonía no es rara, es la norma.** Las 49 consultas tienen al menos
una inversión, **38** tienen una inversión *estricta* —A puntuaba más que B de
verdad y después puntúa menos que B de verdad, sin empates de por medio— y en
**31** el vuelco llega al top-5, que es lo único que ve el usuario.

Que una fusión cuyo orden depende de documentos que el usuario nunca verá sea la
norma y no la excepción es, por sí solo, un argumento contra fusionar por rango.
No es el argumento que la quitó —eso fue F2c—, pero apunta al mismo sitio.

### El ejemplo trabajado

**Consulta `rgpd-01`**: *«¿Qué plazo hay para notificar una violación de
seguridad de datos personales a la autoridad de control?»*

**Documento que se quita**: `1c488d03` — **no relevante**, y **no estaba en el
top-5**. Es el caso fuerte: un documento que el usuario nunca habría visto y que
a nadie le importa.

**Top-5 ANTES** (`RRF_K = 60`):

| # | fragmento | rango léxico | rango vect. | puntuación RRF | ¿relevante? |
|---|---|---|---|---|---|
| 1 | `273d4c8b` | 5 | 1 | 0,01588903 | **sí** |
| 2 | `fc496f85` | 9 | 2 | 0,01531089 | **sí** |
| 3 | `10482c6e` | 12 | 7 | 0,01440713 | no |
| 4 | `72368708` | 21 | 8 | 0,01352578 | no |
| 5 | `b5b1a2f5` | 17 | 12 | **0,01343795** | no |

**Top-5 DESPUÉS de quitar `1c488d03`**:

| # | fragmento | rango léxico | rango vect. | puntuación RRF | ¿relevante? |
|---|---|---|---|---|---|
| 1 | `273d4c8b` | 5 | 1 | 0,01588903 | **sí** |
| 2 | `fc496f85` | 9 | 2 | 0,01531089 | **sí** |
| 3 | `10482c6e` | 12 | 7 | 0,01440713 | no |
| 4 | `72368708` | 21 | 8 | 0,01352578 | no |
| 5 | `a0fc381d` | **7** | 23 | **0,01348678** | no |

`b5b1a2f5` sale del top-5 y entra `a0fc381d`, y la aritmética se sigue a mano:

```
ANTES
  b5b1a2f5 = 1/(60+17) + 1/(60+12) = 0,01298701 + 0,01388889 = 0,01343795
  a0fc381d = 1/(60+ 8) + 1/(60+23) = 0,01470588 + 0,01204819 = 0,01341507
                                      b5b1a2f5  >  a0fc381d     (por 0,00002288)

Se quita 1c488d03, que iba por delante de a0fc381d en la lista LÉXICA
y por detrás de b5b1a2f5 en la vectorial.
  · a0fc381d sube del 8.º al 7.º en la lista léxica.
  · b5b1a2f5 no se mueve en ninguna de las dos.

DESPUÉS
  b5b1a2f5 = 1/(60+17) + 1/(60+12) = 0,01343795   (igual)
  a0fc381d = 1/(60+ 7) + 1/(60+23) = 0,01492537 + 0,01204819 = 0,01348678
                                      a0fc381d  >  b5b1a2f5     (por 0,00004883)
```

Ahí está la no monotonía, sin metáforas: **el orden relativo de `b5b1a2f5` y
`a0fc381d` lo decidió un tercer documento que no es ninguno de los dos, que no
es relevante, y que ni siquiera aparecía en el resultado.** Y esta vez el efecto
no es cosmético: **cambia la composición del top-5**, que es lo único que llega
al modelo.

En este caso concreto los dos que se intercambian son no relevantes, así que la
calidad de la respuesta no cambia. Pero de las 49 consultas hay **31** donde el
vuelco alcanza el top-5, y nada garantiza que en todas ellas los afectados sean
irrelevantes.

Reproducirlo:

```
$ python3 -c "
import json; d=json.load(open('out/eval_recuperacion.json'))
e=d['f4_no_monotonia']['ejemplos'][0]
print(e['consulta'], e['quitado'], e['inversiones_estrictas'])"
```

### Los empates: un hallazgo que salió buscando otra cosa

Persiguiendo la no monotonía apareció algo que no se buscaba, y que **ya no
afecta al producto porque la fusión se ha ido** — pero que hay que dejar escrito,
porque es la clase de defecto que vuelve en cuanto alguien reintroduzca un
`sorted` sobre un `set`.

El RRF sólo puede tomar valores de la forma `1/(60+r)` y sumas de dos de ellos,
así que un documento que va 3.º en una lista y otro que va 3.º en la otra puntúan
**exactamente lo mismo**, `1/63`. Los empates son frecuentes por construcción,
no por casualidad.

¿Cómo se deshacía ese empate? Así, en el `retrieval.py` de antes del 2026-09-11:

```python
all_chunks = set(bm25_ranks) | set(vector_ranks)      # un set
...
top_ids = sorted(rrf_scores, key=lambda c: rrf_scores[c], reverse=True)[:top_k]
```

`sorted` es estable, así que ante un empate respetaba el orden de iteración del
diccionario, que venía del orden de iteración de un **`set` de cadenas**. Ese
orden depende del `hash()` de cada cadena, y en CPython el hash de las cadenas
está **aleatorizado por proceso** salvo que se fije `PYTHONHASHSEED`.

Consecuencia, que no se llegó a medir y por tanto no se afirma como fallo
observado: **ante un empate, dos procesos distintos del backend podían devolver
el top-5 en distinto orden para la misma consulta y el mismo corpus.** Con dos
réplicas —que es el montaje que mide el bloque H— eso es dos respuestas
distintas a la misma pregunta según a qué réplica te toque.

Hoy no puede pasar: el ranking es por coseno, que es un flotante continuo, y los
empates exactos entre fragmentos distintos son prácticamente imposibles. El
arnés de evaluación, que sí sigue calculando RRF para las ramas de diagnóstico,
desempata **por id** de forma explícita, para que sus cifras sean reproducibles
entre ejecuciones.

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

Nota de fecha: esta tabla es de la ejecución del 2026-09-10, **anterior** al
arreglo del analizador, así que sus filas de «fusión» son la fusión con la rama
léxica rota. Las de «vectorial» no dependen de ese arreglo y siguen valiendo tal
cual, que son las que sostienen la conclusión.

| métrica | con `passage: ` | sin prefijo | diferencia | IC 95 % | ¿excluye el 0? |
|---|---|---|---|---|---|
| vectorial · hitrate@1 | 0,612 | 0,653 | −0,041 | [−0,102, +0,000] | no |
| vectorial · hitrate@5 | 0,959 | 0,939 | +0,020 | [+0,000, +0,061] | no |
| **vectorial · recall@5** | **0,824** | **0,795** | **+0,029** | **[+0,005, +0,061]** | **SÍ** |
| vectorial · MRR | 0,752 | 0,755 | −0,003 | [−0,039, +0,026] | no |
| fusión · hitrate@5 | 0,898 | 0,857 | +0,041 | [+0,000, +0,102] | no |
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

| etapa | ejec. 1 p50 | p95 | ejec. 2 p50 | p95 | ejec. 3 p50 | p95 | ejec. 5 p50 | p95 |
|---|---|---|---|---|---|---|---|---|
| embebido de la consulta | 30,66 | 45,82 | 148,95 | 316,99 | 33,09 | 54,00 | 32,82 | 47,16 |
| léxica (Postgres) | 0,52 | 0,68 | 0,76 | 4,71 | 0,54 | 0,71 | 4,66 | 6,68 |
| vectorial (pgvector) | 3,05 | 4,19 | 5,18 | 12,03 | 3,14 | 4,24 | 2,95 | 4,23 |
| fusión RRF (Python) | 0,03 | 0,04 | 0,04 | 0,07 | 0,03 | 0,05 | 0,05 | 0,06 |
| **TOTAL** | **34,56** | **50,14** | **160,42** | **323,85** | **36,96** | **58,65** | **41,18** | **54,75** |

Todo en milisegundos. La ejecución 5 es la del 2026-09-11, ya con la rama léxica
en OR, y tiene una lectura propia: **la rama léxica pasa de 0,5 ms a 4,7 ms**, un
factor de 9. Es lo esperable —con AND, en 27 de 49 consultas Postgres cortaba
casi sin trabajo; con OR tiene que puntuar de verdad—, y sigue siendo un 11 % del
total. No fue eso lo que la quitó.

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

Una cuarta ejecución posterior, con **2** repeticiones en vez de 5 (así que con
menos muestras: 98 por etapa) y con el equipo ya tranquilo (carga media 3,73),
dio **TOTAL p50 = 35,52 ms** y embebido 31,22 ms. Es decir: tres de las cuatro
medidas caen entre 34,5 y 37 ms y la ejecución 2 sigue siendo la única rara.

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
- **La fusión RRF era gratis**: 0,03-0,05 ms, menos del 0,15 % del total.
  Quitarla **no ahorra tiempo**, y hay que decirlo así: el argumento para
  quitarla fue de calidad (F2 y F2c), no de latencia. Lo que sí se ahorra es la
  consulta léxica a Postgres, 4,7 ms de p50 con el OR, un 11 % del total. Es una
  mejora real pero menor, y no habría bastado por sí sola para justificar el
  cambio.
- **Las consultas a Postgres juntas eran ~7,6 ms**, un 18 % del total (con el
  AND anterior eran 3,6 ms, un 10 %). El índice vectorial no es el cuello de
  botella con 1.031 fragmentos: son 2,95 ms.

Si alguna vez hay que bajar la latencia de este camino, el sitio donde mirar es
el embebido de la consulta, no la base de datos ni la fusión.

**Lo que NO mide F6**: nada de esto incluye la llamada al modelo de lenguaje que
viene después. Es el tiempo de **recuperar los fragmentos**, no el de responder.

---

## Qué hacer con todo esto

Las decisiones, separadas de las conjeturas. **Todo lo de esta lista está hecho,
no propuesto.**

1. **La rama léxica se arregló.** `plainto_tsquery` unía los términos con AND y
   dejaba 27 de 49 consultas sin un solo candidato. Ahora el operador se
   reescribe a OR sobre el tsquery ya analizado y son 0 de 49. La mejora de la
   rama está medida y las tres diferencias pareadas excluyen el cero.
2. **La fusión RRF se quitó del producto.** Con la rama arreglada, la vectorial
   sola gana en hitrate@5, recall@5 y MRR con los tres intervalos excluyendo el
   cero; la rama léxica aporta **0 de 96** relevantes que la vectorial no traiga;
   y el barrido de peso tiene su máximo en «no fusionar», sin que ninguno de los
   30 contrastes contra ese punto excluya el cero.
3. **`RRF_K` deja de existir en producción**, porque se fue con la fusión. El
   barrido se conserva en el arnés. La conclusión anterior —«k es una palanca
   desconectada»— era falsa: la curva era plana porque la mitad de las consultas
   no tenían segunda lista.
4. **Los nombres se corrigieron.** No era BM25 (`ts_rank_cd` no tiene IDF ni
   normalización contra la longitud media del corpus), y `hybrid_search` /
   `HybridResult` / `rrf_score` prometían una fusión que ya no existe. Ahora son
   `corpus_search` / `CorpusResult` / `score`.
5. **Dos agujeros del prefijo de e5, tapados** (ingestor v2 y suelo de
   fastembed), con la honestidad de que el A/B **no** demuestra una mejora
   grande.

Y una cosa que **no** se ha hecho y podría parecer que sí: no se ha tocado nada
para mejorar la recuperación por encima de lo que ya daba la rama vectorial. El
sistema recupera hoy exactamente lo mismo que recuperaba la rama vectorial antes
del cambio; lo que se ha quitado es lo que la empeoraba.

## Lo que NO se ha medido, y por tanto no se afirma

- **La calidad de la respuesta del copiloto.** Todo esto mide qué fragmentos
  llegan al modelo. Que el modelo responda bien con ellos es otra cosa, y no se
  ha tocado.
- **Consultas cortas con términos exactos** («op.acc.6», «artículo 33»), que son
  justo donde un ranking léxico debería lucir. El conjunto son 49 preguntas
  largas en lenguaje natural. Es plausible que con consultas de ese otro tipo la
  fusión gane; **plausible no es medido**, y hacerlo exige otro conjunto
  etiquetado. Es la limitación más seria de la decisión de quitar la fusión, y
  por eso el arnés sigue midiendo las ramas retiradas.
- **Corpus grandes.** 1.031 fragmentos es un corpus donde el vector cabe entero
  en memoria y la búsqueda es exacta, no aproximada. Con dos órdenes de magnitud
  más, con índice HNSW y con vocabulario más disperso, el reparto de fuerzas
  entre las dos ramas puede ser otro. No se ha medido y no se afirma.
- **El no determinismo del desempate en el código anterior.** Había una base
  clara para sospecharlo (orden de iteración de un `set` + hash aleatorizado por
  proceso), pero no se ejecutó la comprobación con dos `PYTHONHASHSEED` distintos
  antes de que ese código desapareciera. Fue una hipótesis, y se queda en
  hipótesis: ya no hay dónde comprobarla.
- **El coste de mezclar agrupamiento CLS y media.** Exigiría instalar fastembed
  0.5.1 y volver a medir. No se ha hecho.
- **Un segundo etiquetador.** Las 96 etiquetas las puso un solo etiquetador
  (quién, en la cabecera del propio conjunto), que además conoce el sistema
  evaluado. El sesgo está declarado, no corregido.
- **Corpus distintos del cargado.** Todas las cifras son sobre estos 1.031
  fragmentos. El script imprime los recuentos que encuentra antes de medir, para
  que nunca se lea una tabla sin saber contra qué se midió.
- **La causa de la varianza de latencia de F6.** Una de las tres ejecuciones
  salió 4,3 veces más lenta y la carga media del anfitrión no lo explica. La
  conjetura (un `docker build` simultáneo) no se ha comprobado: haría falta
  repetir la medición con y sin build en paralelo.
- **Reranking con cross-encoder.** No existe, así que no se ha medido. La
  mención a un «paso 4 · rerank» que arrastraba `retrieval.py` se ha quitado del
  código con la reescritura: era una promesa en un docstring, no un plan.

## Cómo repetirlo entero

```
make demo                 # si la pila no está en pie
make eval-recuperacion    # ~13 min: descarga el modelo la primera vez,
                          # mide, y deja out/eval_recuperacion.json
```

Con `EVAL_AB_PREFIJO=no` se salta el A/B de F5 (el re-embebido de los 1.031
fragmentos, que es lo que más tarda) y baja a un par de minutos.

Comprobado que reproduce: las tablas de F2, F2b y F3 salieron idénticas en
**cinco ejecuciones**, **tres de ellas sobre una pila levantada de cero** con
`make clean && make demo` (contenedores nuevos, volúmenes nuevos, corpus
resembrado desde el volcado, modelo descargado otra vez). También salió idéntica
la tabla de cosenos de F5, que es la que dice con qué prefijo está embebido el
corpus.

Las cinco ejecuciones son de **antes** del arreglo del analizador. Las cifras de
la cabecera, de F2, de F3, de F3b y de F4 son de las **dos ejecuciones del
2026-09-11** con la rama léxica en OR, y las dos dieron lo mismo (la segunda
sólo añadía la medida F2c del aporte único). Que la reproducibilidad de las
tablas nuevas se apoye en dos ejecuciones y no en cinco es una diferencia real
frente a la versión anterior de este informe, y se dice.

Aviso para quien lo repita: el primer intento de `make eval-recuperacion` sobre
un contenedor recién construido **falló** después de doce minutos de cálculo,
porque `/app/out` no es escribible por el usuario del backend. Está arreglado
(la salida va a `/tmp` dentro del contenedor y se copia fuera), pero se cuenta
porque es justo el tipo de fallo que sólo aparece cuando alguien ejecuta el
comando de verdad en vez de darlo por bueno.
