# Prueba de carga · dónde se rompe, con el número delante

**Fecha**: 2026-09-10 · **Rama**: `main`

> **La conclusión de este informe tiene ahora su ADR.** Lo que aquí son
> tablas —200 % de CPU con dos workers en catorce núcleos, ×1,7 a ×2,4 al
> añadir réplica en los endpoints de base de datos, y esa misma réplica
> rompiendo `/corpus/search`— se razona junto en
> [ADR-060 · el modelo en el proceso limita los workers](adr/ADR-060-el-modelo-en-el-proceso-limita-los-workers.md),
> con las tres salidas y sus contrapartidas. *(2026-09-11 · BLOQUE I4.)*

Para poder decir «escalable» con algo detrás. Sin un límite medido la palabra no
significa nada: toda aplicación escala hasta que deja de hacerlo, y lo único
defendible es decir **dónde** deja de hacerlo.

Reproducirlo entero:

```
make demo && make carga
```

que escribe `out/carga_1_replica.json` y `out/carga_2_replicas.json`. Todas las
tablas de aquí salen de esos dos ficheros.

---

## La máquina, antes que los números

Los números absolutos no se pueden trasladar a otro sitio sin decir dónde se
tomaron:

| | |
|---|---|
| CPU | 14 núcleos lógicos (WSL2) |
| Memoria | 25 GB |
| Todo en la misma máquina | Postgres, Redis, MinIO, frontend, backend **y el generador de carga** |
| Backend | uvicorn con **2 workers** (`docker-compose.demo.yml:347`) |
| Umbral de rotura | **p95 > 1000 ms**, declarado ANTES de medir |
| Escalones | concurrencia 1 → 2 → 5 → 10 → 20 → 40 → 80, 12 s cada uno |

Los seis endpoints se eligieron **contando el tráfico real** que el recorrido
completo del BLOQUE E generó sobre el registro de acceso del backend, no a ojo:

```
$ docker logs fulkro-demo-backend-1 2>&1 | grep -o '"[A-Z]* /api/[^"]*"' \
    | sed 's/?.*//' | sed -E 's#/[0-9a-f-]{36}#/{id}#g' | sort | uniq -c | sort -rn
```

Se excluyeron dos cosas: `/api/v1/health`, que lo dispara el *healthcheck* de
Docker cada 5 s y no es tráfico de nadie, y los `/events`, que son flujos SSE de
larga duración y en una rampa medirían cuántas conexiones caben abiertas, no
cuánto se tarda. El sexto —la búsqueda del corpus— **no** es de los más
llamados: entra porque es el único que toca el embebido de la consulta, que era
justo donde se sospechaba el cuello. Sin él, la prueba no podría ni confirmar ni
desmentir esa sospecha.

---

## El resultado, en una línea

**Con una réplica, los cinco endpoints de lectura aguantan la rampa entera sin
romper: hasta 80 peticiones simultáneas, p95 por debajo de 300 ms y cero
errores. El que rompe es el buscador del corpus, y rompe pronto: en
concurrencia 10.** Y el cuello no es Postgres: es el proceso del backend.

---

## 1 · Con una réplica

| endpoint | techo de rendimiento | p95 en c=80 | dónde rompe |
|---|---:|---:|---|
| `/auth/me` | 360 pet./s | 300 ms | no rompe |
| `/clients` | 432 pet./s | 264 ms | no rompe |
| `/alerts/active` | 453 pet./s | 274 ms | no rompe |
| `/projects/{id}/header` | 200 pet./s | 953 ms | no rompe (rozando) |
| `/projects/{id}/feature-flags` | 194 pet./s | 887 ms | no rompe (rozando) |
| **`/corpus/search`** | **17 pet./s** | — | **c=10 · p95 1.385 ms** |

La forma de la curva es la de un servidor saturado y sano: el rendimiento se
aplana (~200–450 peticiones por segundo según el endpoint) y la latencia crece
**linealmente** con la concurrencia, sin errores. Eso es una cola, no una
rotura: las peticiones esperan turno y salen.

### Dónde está el cuello, medido y no supuesto

El uso de CPU por contenedor durante cada escalón:

| escalón | backend | postgres |
|---|---:|---:|
| c=1 | 83 % | 12 % |
| c=10 | 198 % | 25 % |
| c=20 | 200 % | 26 % |
| c=80 | **204 %** | 28 % |

**El backend se clava en el 200 % y Postgres nunca pasa del 58 %.** Ese 200 % no
es casualidad: son exactamente los **2 workers de uvicorn** que fija
`docker-compose.demo.yml:347`, cada uno saturando un núcleo. El cuello de los
cinco endpoints de lectura **es el número de workers**, no la base de datos.
Queda sitio de sobra: la máquina tiene 14 núcleos y se están usando 2.

### El buscador del corpus es otra cosa

| escalón | backend | postgres |
|---|---:|---:|
| c=1 | **1.303 %** | — |
| c=10 | **1.325 %** | 11 % |

Trece núcleos, no dos. La búsqueda **no está esperando a Postgres: está
calculando**. Encaja exactamente con lo que midió el BLOQUE F por otro camino
([docs/EVAL_RECUPERACION.md](EVAL_RECUPERACION.md)): el embebido de la consulta
se lleva **el 89–93 % del tiempo** de una búsqueda (p50 total ~35 ms, de los
que ~31 ms son embebido). Aquí se ve el mismo hecho desde la carga: el modelo de
embeddings usa todos los hilos que encuentra, así que **una sola búsqueda ya
compite consigo misma**, y con diez concurrentes el reparto de CPU hunde el p95.

La sospecha de partida —«el embebido de la consulta o Postgres»— queda resuelta:
**es el embebido**, y las dos mediciones independientes coinciden.

---

## 2 · ¿Sirve de algo la segunda réplica?

Reutilizando el montaje de D4 (nginx + reparto por turnos):

| endpoint | 1 réplica | 2 réplicas | ganancia |
|---|---:|---:|---:|
| `/clients` | 432 pet./s | **743 pet./s** | **1,72×** |
| `/alerts/active` | 453 pet./s | **790 pet./s** | **1,74×** |
| `/projects/{id}/header` | 200 pet./s | **373 pet./s** | **1,87×** |
| `/projects/{id}/feature-flags` | 194 pet./s | **376 pet./s** | **1,94×** |
| `/auth/me` | 360 pet./s | 425 pet./s | 1,18× |
| **`/corpus/search`** | 17 pet./s | **0 pet./s · 30 s de espera y error** | **peor** |

**Para lo que va a la base de datos, la segunda réplica sirve**: entre 1,7× y
1,9× en cuatro de los cinco, con Postgres subiendo del ~28 % al ~84 % de CPU —
es decir, el trabajo se reparte y la base empieza a notarse, que es lo que
debería pasar. `/auth/me` gana menos (1,18×) y no se ha investigado por qué;
queda dicho.

### Y para la búsqueda, la empeora hasta romperla

Con dos réplicas, la **primera** petición a `/corpus/search` tardó **30 s y
terminó en error**. Ni siquiera llegó al segundo escalón.

El motivo está escrito, irónicamente, en el propio `docker-compose.demo.yml`
(línea 345), en el comentario que justifica usar 2 workers y no 4:

> *«cada worker carga su propia copia del modelo de embeddings si se usa el
> copiloto»*

Con dos réplicas × 2 workers = **cuatro copias del modelo**, cada una queriendo
usar los trece núcleos que ya vimos. En una máquina de 14, eso no es escalar:
es competir. **Replicar horizontalmente un servicio que hace inferencia en CPU
dentro del propio proceso no reparte el trabajo, lo multiplica.**

Es el resultado más útil de este bloque, porque es el que cambia una decisión:
si algún día hay que escalar, **el embebido tiene que salir del proceso del
backend** —a un servicio propio, con su propio dimensionado— antes de que
añadir réplicas sirva de algo para el buscador.

---

## Lo que este número NO autoriza a decir

- **No es una prueba de producción.** Es un Docker Compose en un portátil con
  todo compartiendo CPU, **incluido el generador de carga**. Lo que se traslada
  es la forma de la curva y dónde está el cuello, no los valores absolutos.
- **No se han medido escrituras.** Los seis endpoints son de lectura, porque una
  rampa de escrituras dejaría el demo inservible para el resto de bloques. El
  límite de escritura **no está medido**.
- **Los 121 y 30 errores en c=80** (`/header` y `/feature-flags`, sólo con dos
  réplicas) aparecen con nginx delante y no con una sola réplica. No se ha
  aislado si son del balanceador, de los límites de conexión, o del propio
  generador. **Se publican como están y sin explicación**, porque inventarle una
  causa sería peor que dejarlos sin explicar.
- **El techo de la rampa son 80 peticiones simultáneas.** Que cinco endpoints
  «no rompan» significa que no rompen **hasta ahí**. No se ha buscado su límite
  real, y decir que no tienen sería exactamente el tipo de afirmación que esta
  campaña existe para no hacer.

---

## Qué se puede afirmar, entonces

Sobre esta máquina, con dos workers de uvicorn y una réplica:

> Los endpoints de lectura sostienen **entre 200 y 450 peticiones por segundo**
> con el p95 por debajo de 300 ms hasta 80 clientes simultáneos, y el límite lo
> pone el número de workers, no la base de datos. La búsqueda del corpus
> sostiene **17 peticiones por segundo** y rompe en 10 clientes simultáneos,
> porque el embebido de la consulta consume 13 núcleos. Añadir una segunda
> réplica multiplica por ~1,7–1,9 los primeros y **rompe** la segunda.

Eso es «escalable» con su límite dicho, que es lo único que lo hace defendible.
