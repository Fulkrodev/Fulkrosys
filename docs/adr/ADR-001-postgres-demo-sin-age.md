# ADR-001 · El perfil demo usa la imagen oficial de PostgreSQL, sin Apache AGE ni pgAudit

- **Estado**: aceptada
- **Fecha**: 2026-09-10
- **Ámbito**: `docker-compose.demo.yml` únicamente. Producción (`docker-compose.prod.yml`)
  y desarrollo (`docker-compose.yml`) no cambian.

---

## Contexto

El perfil demo tiene un único objetivo: que alguien que acaba de clonar el repositorio
levante la aplicación entera y la vea funcionando. Cualquier cosa que haga esperar, que
dependa de la red o que pueda fallar en la máquina de otro juega en contra.

La imagen de PostgreSQL del repositorio (`infra/docker/Dockerfile.postgres`) parte de
`pgvector/pgvector:pg16` y le añade tres cosas: **pgAudit** (paquete apt), **Apache AGE**
(compilado desde el código fuente, clonando el repositorio de Apache) y **pgBackRest**
(paquete apt). Compilar AGE exige instalar `build-essential`, `git`,
`postgresql-server-dev-16`, `flex` y `bison`, clonar `github.com/apache/age` y ejecutar
`make install`.

Es decir: la primera vez, el demo compilaría un motor de grafos antes de enseñar nada.

## Decisión

En `docker-compose.demo.yml` el servicio `postgres` usa **`pgvector/pgvector:pg16` tal
cual**, sin capa propia, y monta `infra/docker/init-extensions-demo.sql` (uuid-ossp +
pgcrypto + vector) en lugar de `infra/docker/init-extensions.sql`.

De ahí se sigue, obligatoriamente y en bloque:

1. No se pasa `command: postgres -c shared_preload_libraries=pgaudit`. Sobre una imagen
   sin pgAudit, precargar esa librería **impide que el servidor arranque**; no degrada.
2. El fichero de extensiones del demo es propio, porque el original crea `age` y
   `pgaudit` y `provision-entrypoint.sh` lo ejecuta con `psql -v ON_ERROR_STOP=1`.
3. El seed corre con `--skip-age-kg` (que ya era su valor por defecto).

## Lo medido

Cada cifra con el comando que la produce. Todo ejecutado el 2026-09-10 en el portátil de
desarrollo (WSL2, Docker 28.5.1).

### Compilar AGE es el 89 % del tiempo de construcción de la imagen

```
$ cd infra/docker && /usr/bin/time -f "TOTAL_SEGUNDOS=%e" \
    docker build --no-cache --progress=plain -f Dockerfile.postgres -t fulkro/postgres:medicion-adr .
#6 DONE 57.1s      ← apt install + git clone apache/age + make install + apt purge
#7 DONE 2.4s       ← pgbackrest
#8 DONE 0.1s       ← COPY pgbackrest.conf
TOTAL_SEGUNDOS=63.95
```

**57,1 s de 63,95 s** (89,3 %) se van en el paso que compila AGE e instala pgAudit. La
imagen oficial no construye nada: se descarga y ya está.

> Nota de honestidad: el paso #6 hace las dos cosas a la vez (pgAudit por apt y AGE por
> compilación) en un único `RUN`, así que 57,1 s es el coste **conjunto**, no el de AGE
> aislado. No se ha medido por separado.

### La capa propia añade entre 48 MiB y 189 MB según cómo se mida

```
$ docker image inspect pgvector/pgvector:pg16 fulkro/postgres:pg16 --format '{{.RepoTags}} {{.Size}}'
[pgvector/pgvector:pg16] 156061256
[fulkro/postgres:pg16]   206781894
```

`docker image inspect` devuelve **156.061.256 bytes (148,8 MiB)** para la oficial y
**206.781.894 bytes (197,2 MiB)** para la propia: **+48,4 MiB**.

```
$ docker image ls --format '{{.Repository}}:{{.Tag}} {{.Size}}' | grep -iE "pgvector|fulkro/postgres"
fulkro/postgres:pg16 809MB
pgvector/pgvector:pg16 620MB
```

`docker image ls` mide el árbol ya desempaquetado en disco: **620 MB** frente a
**809 MB**, **+189 MB**. Las dos cifras son correctas; miden cosas distintas.

### Apache AGE no lo usa nadie

```
$ command grep -rniE "ag_catalog|cypher\(|create_graph|LOAD 'age'|EXTENSION .?age" backend/migrations/ | wc -l
0
$ command grep -rniE "ag_catalog|cypher\(|create_graph|LOAD 'age'|EXTENSION .?age" backend/app/ | wc -l
0
$ command grep -rlniE "ag_catalog|cypher\(|create_graph" backend/ --include=*.py --include=*.sql
backend/scripts/age_seed_kg.py
```

Cero apariciones en el árbol de migraciones y cero en el código de la aplicación. El único
consumidor es el script `backend/scripts/age_seed_kg.py`, que además el seed ya salta por
defecto (`--skip-age-kg` es el valor por omisión de `PROVISION_SEED_FLAGS` en
`infra/docker/provision-entrypoint.sh`).

### pgAudit tampoco

```
$ command grep -rniE "pgaudit" backend/app backend/migrations | wc -l
2
$ command grep -niE "pgaudit" backend/app/motors/m08_verification/models.py backend/migrations/versions/m8_autopilot_canonical_001.py
backend/app/motors/m08_verification/models.py:508:# 7. EvidenceRecord — append-only (doc §4 · pgAudit/R6 hash chain)
backend/migrations/versions/m8_autopilot_canonical_001.py:120:    # 4. m8_evidence_records · APPEND-ONLY (doc §4 · R6 pgAudit)
```

Las dos únicas apariciones son **comentarios**. La trazabilidad inmutable de la regla R6
no la da pgAudit: la da la cadena de hash SHA-256 sobre `audit_log`, implementada como
trigger PL/pgSQL en la migración `d4f8b2a90001`, más el `REVOKE UPDATE, DELETE ON
audit_log` del paso [7/7] de la provisión. Todo eso funciona igual en el demo.

### El fichero de extensiones original revienta sobre la imagen oficial

```
$ docker cp infra/docker/init-extensions.sql fulkro-demo-postgres-1:/tmp/orig.sql
$ docker exec fulkro-demo-postgres-1 psql -v ON_ERROR_STOP=1 -U fulkro -d fulkro -f /tmp/orig.sql; echo "rc=$?"
psql:/tmp/orig.sql:9: ERROR:  extension "age" is not available
DETAIL:  Could not open extension control file ".../age.control": No such file or directory.
rc=3
```

Aborta en la línea 9. Por eso el demo monta su propio `init-extensions-demo.sql`.

### Con el fichero del demo, la provisión arranca limpia

Levantando solo el servicio `postgres` del perfil demo:

```
$ docker inspect --format '{{.State.Health.Status}}' fulkro-demo-postgres-1
healthy

$ docker exec fulkro-demo-postgres-1 psql -U fulkro -d fulkro -c "SELECT extname, extversion FROM pg_extension ORDER BY extname;"
  extname  | extversion
-----------+------------
 pgcrypto  | 1.3
 plpgsql   | 1.0
 uuid-ossp | 1.1
 vector    | 0.8.1

$ docker exec fulkro-demo-postgres-1 psql -U fulkro -d fulkro -tA -c "SHOW shared_preload_libraries;"
(vacío)
```

Y los tres primeros pasos de `provision-entrypoint.sh`, reejecutados con
`ON_ERROR_STOP=1` sobre esa base, devuelven `rc=0` los tres, creando los cuatro roles
(`fulkro`, `fulkro_app`, `fulkro_app_bypassrls`, `fulkro_migrate`) y las dos funciones
helper de RLS (`current_client_id`, `current_project_id`).

### No es un experimento: la integración continua ya vive así

```
$ command grep -n "pgvector/pgvector:pg16\|CREATE EXTENSION" .github/workflows/admin-polish-empirical.yml
63:        image: pgvector/pgvector:pg16
111:            -c 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";' \
112:            -c 'CREATE EXTENSION IF NOT EXISTS pgcrypto;' \
113:            -c 'CREATE EXTENSION IF NOT EXISTS vector;'
```

El workflow `admin-polish-empirical.yml` usa desde hace tiempo exactamente esta
configuración —imagen oficial, esas tres extensiones, sin AGE ni pgAudit— y sus
ejecuciones son verdes. El perfil demo adopta una receta ya probada, no inventa una.

## La contrapartida

Se pierden tres cosas, y conviene decirlas sin adornos:

1. **El grafo de conocimiento no existe en el demo.** `backend/scripts/age_seed_kg.py` no
   se puede ejecutar contra esta base. Hoy no lo lee nadie (cero consumidores medidos
   arriba), así que la pérdida es de una capacidad latente, no de una funcionalidad
   visible. Si algún día el grafo pasa a ser parte del producto, el demo tendrá que
   volver a la imagen propia, y con ella volverán los ~57 s de compilación.
2. **No hay auditoría a nivel de servidor.** Sin pgAudit no queda registro de las
   sentencias que ejecuta el propio motor. El `audit_log` aplicativo con cadena de hash sí
   funciona, que es lo que la aplicación enseña y lo que exige R6, pero la defensa en
   profundidad de producción no está en el demo. **El perfil demo no vale como evidencia
   de conformidad**; es un escaparate.
3. **Dos ficheros que decir lo mismo.** `init-extensions.sql` e
   `init-extensions-demo.sql` comparten las dos funciones helper de RLS. Si alguien toca
   una y olvida la otra, divergen en silencio. Mitigación parcial: el paso [2/7] de la
   provisión ejecuta `init-functions.sql`, que vuelve a crear esas dos funciones con
   `CREATE OR REPLACE`, así que la copia del fichero de extensiones es redundante en la
   práctica y una divergencia ahí no rompería el arranque.

**Por qué un fichero nuevo en vez de relajar el original.** La alternativa era hacer
tolerante `init-extensions.sql` (envolver `CREATE EXTENSION age` en un `DO $$ ...
EXCEPTION` o quitarle el `ON_ERROR_STOP`). Se descarta: ese fichero es el que provisiona
**producción**, donde que AGE o pgAudit falten es exactamente el tipo de fallo que uno
quiere que aborte el despliegue a gritos. Ablandar el arranque de producción para que un
demo local sea más cómodo es cambiar el riesgo de sitio, y al sitio malo. El coste de la
decisión contraria es duplicar veinte líneas de SQL en un fichero cuyo nombre lleva la
palabra `demo`.

## Lo que se gana

- **Un demo que no compila nada.** Se descarga una imagen firmada y publicada, y arranca.
  Menos superficie para que falle en la máquina de otro: sin `git clone` a GitHub durante
  el `build`, sin `apt` de paquetes de desarrollo, sin compilador.
- **Compatibilidad con PostgreSQL gestionado.** Ni RDS, ni Cloud SQL, ni Postgres de
  Hetzner permiten instalar una extensión compilada a mano. Un demo que solo necesita
  `uuid-ossp`, `pgcrypto` y `vector` —las tres disponibles en cualquier servicio
  gestionado moderno— demuestra que la aplicación **puede** correr ahí. Mientras AGE
  siguiera siendo obligatorio, esa puerta estaba cerrada por definición.
- **Un aviso temprano.** Si mañana alguien introduce una dependencia real de AGE o de
  pgAudit en el código de la aplicación, el demo dejará de arrancar y se enterará el
  mismo día, no en el despliegue.

## Consecuencias para otros ficheros

`backend/scripts/seed_all_fulkro.py` (línea ~100) exige las cinco extensiones y devuelve 1
si falta alguna:

```python
required_ext = {"uuid-ossp", "pgcrypto", "vector", "age", "pgaudit"}
```

Con este ADR, el paso [6/7] de la provisión del demo abortaría ahí. El seed debe tratar
`age` y `pgaudit` como **opcionales** (avisar si faltan, no morir), o aceptar una bandera
que las excluya. Ese fichero no se toca en este ADR; queda anotado como cambio necesario.
