# ADR-060 · El número de workers no lo limita la CPU: lo limita la memoria del modelo

**Fecha**: 2026-09-11 · **Estado**: aceptado · **Ámbito**: capa de aplicación
**Sucede a**: [ADR-058 · ¿Es escalable en horizontal?](ADR-058-escalabilidad-horizontal.md),
que midió **corrección** con dos réplicas y dejó escrito que el rendimiento
**no** se había medido. Esto es lo que salió al medirlo.

**Origen de los números**: [`docs/PRUEBA_DE_CARGA.md`](../PRUEBA_DE_CARGA.md) y
`make carga` (bloque H) · latencias por etapa de
[`docs/EVAL_RECUPERACION.md`](../EVAL_RECUPERACION.md) (bloque F) · memoria del
modelo de `out/memoria_modelo.json` y
[`backend/scripts/medir_memoria_modelo.py`](../../backend/scripts/medir_memoria_modelo.py)
(bloque I).

---

## La observación, en cuatro cifras que no encajan

Las cuatro se midieron por separado y apuntan al mismo sitio. La cuarta se
añadió el 2026-09-11, cuando una revisión señaló que el número del título era el
único del documento que nadie había medido.

**1. Con dos workers, el backend se clava en el 200 % de CPU en una máquina de
catorce núcleos.** En los cinco endpoints de base de datos, a concurrencia 80:

| endpoint | CPU backend | CPU Postgres |
|---|---|---|
| `/auth/me` | 203,90 % | 23,31 % |
| `/clients` | 197,39 % | 28,36 % |
| `/alerts/active` | 197,63 % | 27,62 % |
| `/projects/{id}/header` | 198,24 % | 35,34 % |
| `/projects/{id}/feature-flags` | 200,43 % | 57,75 % |

200 % son exactamente dos núcleos: **dos workers, uno por núcleo, saturados**.
Postgres nunca pasa del 58 %. El cuello de botella no es la base: son los dos
procesos de Python. Y quedan **doce núcleos sin tocar**.

**2. La segunda réplica multiplica por 1,7–2,4 cuatro de los cinco endpoints de
base de datos** (y empeora el quinto).

| endpoint (c=40) | 1 réplica | 2 réplicas | factor |
|---|---|---|---|
| `/clients` | 324,8 rps | 722,6 rps | **×2,22** |
| `/alerts/active` | 430,1 rps | 725,6 rps | ×1,69 |
| `/projects/{id}/header` | 200,5 rps | 354,6 rps | ×1,77 |
| `/projects/{id}/feature-flags` | 157,0 rps | 376,4 rps | ×2,40 |
| `/auth/me` | 306,8 rps | 264,0 rps | **×0,86** |

Es decir: la aplicación **sí** escala repartiendo. Doblar procesos casi dobla el
caudal. Lo único que impedía usar los doce núcleos libres era el `--workers 2`.

**Salvo `/auth/me`, que va en la tabla precisamente porque no encaja.** Hasta el
2026-09-11 esta tabla listaba cuatro endpoints y omitía el quinto, el único que
**empeora** con la segunda réplica. Una tabla que sólo enseña las filas que
sostienen el titular no es una medida, es una ilustración. Y el documento de
origen (`docs/PRUEBA_DE_CARGA.md:131`) sí lo recogía, con un 1,18× que sale de
comparar los **picos** de cada serie, no el mismo escalón.

A un solo escalón, `/auth/me` no tiene una dirección clara:

| c | 1 réplica | 2 réplicas | factor |
|---|---|---|---|
| 1 | 157,0 | 72,1 | ×0,46 |
| 5 | 359,6 | 328,1 | ×0,91 |
| 20 | 322,5 | 425,0 | ×1,32 |
| 40 | 306,8 | 264,0 | ×0,86 |
| 80 | 340,8 | 330,3 | ×0,97 |

Va de ×0,46 a ×1,32 y vuelve a bajar. **No se ha investigado por qué**, y no se
inventa aquí la explicación. Lo que sí cambia es el alcance de la cifra 2: la
segunda réplica multiplica el caudal de los endpoints que **consultan** la base;
`/auth/me`, que valida una cookie de sesión en cada petición, no se comporta
como ellos.

**3. Y la misma segunda réplica ROMPE la búsqueda del corpus.**

| `/corpus/search` | 1 réplica | 2 réplicas |
|---|---|---|
| c=1 | 7,2 rps · p50 54 ms · 0 errores | **0,0 rps · 30.027 ms · 1 error** |

No se degrada: se cae con el tiempo de espera agotado a **concurrencia uno**. Y
la CPU del backend con una sola réplica ya venía diciendo por qué: **1.324 %**
en `/corpus/search`, frente al 200 % de todo lo demás. Trece núcleos.

## Lo que las tres dicen juntas

El 1.324 % no es paralelismo de la aplicación: es **ONNX Runtime**, que por
defecto abre tantos hilos como núcleos ve para multiplicar las matrices del
modelo de embeddings. Cada worker de uvicorn es un **proceso** distinto, así que
cada uno carga **su propia copia** del modelo e5-large y abre **su propio** grupo
de hilos.

De ahí sale la contradicción aparente entre las cifras 2 y 3: la misma segunda
réplica que casi dobla el caudal de los endpoints de base de datos hunde la
búsqueda. No es la misma unidad de trabajo. Un endpoint de base de datos es
E/S: dos procesos esperando a Postgres caben en dos núcleos y sobran. Una
búsqueda del corpus es aritmética densa: **un** proceso ya quiere los catorce
núcleos, y cuatro procesos (2 réplicas × 2 workers) se pelean por ellos mientras
cada uno arrastra **1,48 GB** de modelo en memoria.

### Cifra 4 · el modelo cuesta 1,48 GB por proceso, y abre 58 hilos

Esta cifra estuvo en este ADR **afirmada y sin fuente** («~1,4 GB») hasta el
2026-09-11, y era justo la que sostiene el título. Ahora está medida dentro de
la propia imagen del backend (`out/memoria_modelo.json`,
`backend/scripts/medir_memoria_modelo.py`):

| momento del proceso | RSS |
|---|---|
| intérprete de Python solo | 10,8 MB |
| tras importar numpy + onnxruntime + fastembed, **sin** modelo | 99,8 MB |
| tras construir `TextEmbedding(e5-large)` | 1.603,6 MB |
| tras el primer `embed()` | 1.607,7 MB |
| tras un lote de 32 | 1.613,7 MB |
| **coste atribuible al modelo** | **1.513,9 MB** |

La estimación anterior se quedaba **un 8 % corta**: son 1,48 GB, no 1,4. Y el
proceso termina con **58 hilos sobre 14 núcleos**, con
`SessionOptions().intra_op_num_threads` en **0**, que en ONNX Runtime no
significa «ninguno» sino «los que haga falta, uno por núcleo». Es la
confirmación medida de lo que la cifra 3 sólo permitía inferir: el 1.324 % de
CPU no es un proceso ocupado, es un proceso abriendo hilos por su cuenta.

Dos matices que la medida obliga a decir:

- **El coste se paga tarde, no al arrancar.** El proveedor es un singleton
  perezoso por proceso (`get_default_embedding_provider`,
  `backend/app/core/ai/embeddings.py:87-92`), y el camino caliente que lo
  invoca es `backend/app/corpus/retrieval.py:185`. Un worker que nunca atiende
  una búsqueda no paga el 1,48 GB. Por eso la segunda réplica no se negó a
  arrancar: **rompió la búsqueda**, que es cuando se cobra.
- **Cuatro procesos que hayan buscado son ~6 GB sólo de modelo**, antes de
  contar Postgres, Redis, MinIO y el frontend.

La conclusión, que es la decisión de este ADR:

> **El número de procesos de backend no lo limita la CPU. Lo limita la memoria
> del modelo de embeddings, y la contención de hilos que ese modelo provoca.**

Es la razón por la que el `docker-compose.demo.yml` dice `--workers 2` con un
comentario que ya lo intuía —«cada worker carga su propia copia del modelo de
embeddings si se usa el copiloto»— pero sin número detrás. Ahora lo tiene: el
número es **1,48 GB por proceso** (medido) y 1.324 % de CPU por búsqueda.

Y explica una asimetría incómoda: **el reparto correcto de workers es distinto
para los endpoints de base de datos que para los que embeben**. No hay un solo
número bueno mientras las dos cosas vivan en el mismo proceso.

## Las salidas, con sus contrapartidas

Ninguna está implementada. Este ADR razona la decisión con los números que ya
hay; implementarla es otro trabajo y hace falta medirlo igual que esto.

### A · El embebido como servicio aparte, con su propia escala

El backend deja de cargar el modelo y llama por HTTP a un servicio de embeddings
con su propio número de réplicas.

- **A favor**: las dos cosas escalan por separado, que es lo que pide la medida.
  El backend baja a un orden de ~150 MB por proceso —**estimado, no medido**: lo
  medido es que los `import` de numpy + onnxruntime + fastembed **sin** construir
  el modelo ocupan 99,8 MB, y a eso hay que sumarle FastAPI, SQLAlchemy y el
  resto de la aplicación, que esta medición no aísla— y puede subir a 8–12 workers usando los
  catorce núcleos. El servicio de embeddings se queda con 1–2 procesos, que es lo
  que su aritmética admite. Y hay un dato que lo hace especialmente barato aquí:
  **el embebido de la consulta es el 80 % del reloj de una búsqueda** (32,8 ms de
  41,2 ms de p50, medido en F6), así que aislarlo aísla el problema entero.
- **En contra**: un servicio más que desplegar, vigilar y versionar. Y un salto
  de red en el camino caliente: hoy el embebido es una llamada en proceso, y
  pasaría a ser HTTP. Sobre 32,8 ms, un milisegundo o dos de red es ruido — pero
  es una pieza más que puede estar caída, y `corpus_search` tendría que decidir
  qué hace cuando lo está.
- **Detalle que no es menor**: la configuración ya lo contempla a medias.
  `backend/app/config.py:67` declara `embeddings_endpoint =
  "http://localhost:8080"`. La idea de un servicio de embeddings separado ya
  está escrita en la configuración. Ahora bien, la honestidad exige la segunda
  mitad: **ese ajuste no lo lee nadie** —`grep -rn embeddings_endpoint backend/`
  devuelve una sola línea, su propia declaración—, así que no es «medio camino
  hecho», es una intención declarada y nunca cableada. El camino real carga el
  modelo en proceso con fastembed.

### B · Una cola con un único trabajador que tenga el modelo cargado

Las búsquedas del corpus se encolan a un trabajador de Celery que carga el modelo
una vez.

- **A favor**: no hay servicio nuevo que inventar — Celery y Redis ya están en la
  pila. Una sola copia del modelo en toda la instalación. Y da un sitio natural
  donde limitar la concurrencia de búsqueda, que es justo lo que se descontroló.
- **En contra**: convierte una operación **síncrona de 41 ms** en un
  ida-y-vuelta por cola. El copiloto responde en flujo continuo y el usuario está
  esperando delante de la pantalla; meter una cola ahí cambia la sensación del
  producto por una razón de infraestructura. Y un único trabajador es un único
  punto de fallo con una única fila de espera: a concurrencia 10 ya medimos p95
  de 1.385 ms **con** el modelo en proceso; con cola, esa espera se hace visible
  en vez de repartirse.

### C · Un endpoint de embeddings externo

Un proveedor de fuera (o una instancia dedicada) sirve los vectores.

- **A favor**: la solución más simple de operar — cero procesos que gestionar,
  cero memoria, y el backend se vuelve trivialmente escalable.
- **En contra**, y aquí pesa más que en otro producto: los fragmentos de consulta
  del copiloto salen de la máquina. En una plataforma de cumplimiento del ENS que
  hace dogfooding sobre sí misma (R7), mandar texto de cliente a un tercero es
  una decisión de tratamiento de datos, no de arquitectura: encargado de
  tratamiento, DPA, sub-procesador declarado en `/sub-processors`. Además ata la
  latencia a una red que no controlamos, y hoy el p50 entero son 41 ms.

## Decisión

1. **Se documenta la restricción** y se deja escrita donde vive el número:
   `--workers` en el compose deja de ser un valor sin justificar.
2. **No se sube `--workers` sin sacar antes el modelo del proceso.** Subirlo con
   el modelo dentro multiplica 1,48 GB por worker y empeora la búsqueda, que es
   exactamente lo que se midió al añadir la segunda réplica.
3. **La opción A es la preferida** si esto se toca: es la única que escala las dos
   cargas por separado, que es el problema real, y no mueve datos fuera de la
   máquina. Pero **no está medida**, y hasta que lo esté es una preferencia
   razonada, no un resultado.
4. **La opción C queda condicionada** a una decisión de protección de datos que no
   es de este ADR.

## Lo que NO se ha medido, y por tanto no se afirma

- **Que la opción A funcione.** Nadie ha desplegado un servicio de embeddings
  aparte y ha vuelto a pasar `make carga`. Todo lo de arriba es aritmética sobre
  medidas existentes.
- **Cuántos workers aguanta el backend sin el modelo.** Que sobren doce núcleos no
  implica que 12 workers sean el número: aparecerían el pool de conexiones a
  Postgres y `max_connections` como límite siguiente, y ese techo no se ha
  buscado.
- **El comportamiento con réplicas en máquinas distintas.** Todo esto es una sola
  máquina de 14 núcleos con Docker Compose. Sigue en pie lo que decía ADR-058.
- **El techo de PostgreSQL.** Nunca pasó del 58 % de un núcleo. Que no sea el
  cuello de botella *aquí* no dice dónde está el suyo.
- **Si ONNX Runtime se puede domar con `OMP_NUM_THREADS`.** Limitar los hilos por
  proceso es una cuarta salida, más barata que las tres de arriba, y no se ha
  probado. Se apunta como lo primero que habría que medir antes de montar nada.
  Ahora hay un número que la hace más atractiva todavía: 58 hilos sobre 14
  núcleos, con `intra_op_num_threads = 0`.
- **Cuánta memoria ocupa el backend COMPLETO sin el modelo.** Lo medido son los
  99,8 MB de los `import` de numpy + onnxruntime + fastembed en seco. El ~150 MB
  que usa la opción A para argumentar añade a ojo FastAPI, SQLAlchemy y el resto;
  esa suma no se ha medido y va marcada como estimación donde aparece.
- **Por qué `/auth/me` no escala como los demás** (ver cifra 2). Se deja escrito
  que no lo hace, sin explicación inventada.

### Una nota sobre esta sección

Hasta el 2026-09-11 esta lista era más corta y le faltaba justo la entrada que
importaba: **el «~1,4 GB» del título no estaba medido**, y era la única cifra que
este apartado no se molestaba en descargar. Un documento que enumera con
escrúpulo lo que no sabe, y deja fuera de esa lista precisamente el número que
sostiene su tesis, da una impresión de rigor que no se ha ganado. Ahora la cifra
está medida (1,48 GB, cifra 4) y esta lista incluye lo que sigue sin estarlo.

## Cómo reproducir los números

La memoria del modelo (cifra 4), que no necesita levantar la pila entera:

```
docker run --rm \
  -v $PWD/backend/scripts/medir_memoria_modelo.py:/tmp/m.py:ro \
  --entrypoint python fulkro/backend:demo /tmp/m.py
# escribe lo mismo que out/memoria_modelo.json
```

El resto:

```
make demo
make carga      # hace las DOS pasadas: rampa 1..80 sobre 6 endpoints con una
                # réplica, y luego el mismo montaje con nginx y dos réplicas.
                # Al terminar restaura el demo a una sola réplica.
```

Deja `out/carga_1_replica.json` y `out/carga_2_replicas.json`, que es de donde
salen todas las tablas de este documento.
