# Traza de instalación en máquina limpia

Este fichero es la **línea base** del bloque C0: qué le pasa a alguien que clona este repositorio
desde GitHub y sigue el README al pie de la letra. No se borra cuando el problema se arregla; al
final se le añade la ejecución buena, para que la mejora se pueda medir en vez de afirmar.

- **Fecha:** 10 de septiembre de 2026
- **Commit del árbol de trabajo desde el que se audita:** `c8ece1c`
- **Commit publicado en GitHub en el momento de la traza:** `2fe3462`

> **Aviso que condiciona la lectura de todo lo que sigue.** El árbol local va por delante del
> repositorio publicado: `origin/main` está en `2fe3462` y el README reescrito (el de "cada cifra con
> su comando") vive en `c8ece1c`, **sin publicar**. Quien clone hoy recibe el README anterior, de 194
> líneas, con instrucciones distintas. La traza sigue **el README publicado**, porque es el que un
> tercero lee de verdad.
>
> ```console
> $ git ls-remote origin HEAD | cut -c1-7
> 2fe3462
> $ git rev-parse --short HEAD
> c8ece1c
> $ git show 2fe3462:README.md | wc -l
> 194
> $ git show c8ece1c:README.md | wc -l
> 417
> ```

---

## Cómo se ha medido

La regla del encargo es que un arreglo de instalabilidad solo cuenta si se prueba **clonando desde
GitHub en un contenedor limpio**, no en el directorio de trabajo del autor, que arrastra estado que
la máquina de otro no tiene.

La "máquina limpia" es un contenedor **Ubuntu 24.04 con su propio demonio Docker**, aislado del
demonio del anfitrión, con `git` y nada más. No se le monta el checkout local: el repositorio entra
por `git clone` desde GitHub, como el de cualquiera.

```console
$ docker exec fulkro-limpia bash -lc '. /etc/os-release; echo $PRETTY_NAME; git --version; docker --version; docker compose version; python3 --version'
Ubuntu 24.04.4 LTS
git version 2.43.0
Docker version 29.8.0, build 88096ef
Docker Compose version v5.5.1
Python 3.12.3
```

El script del trazado es `scripts/traza_instalacion_limpia.sh` y hace, por cada paso del README: intentarlo **literal**,
registrar el fallo con su traza completa si lo hay, aplicar el arreglo mínimo que aplicaría un
usuario decidido, y seguir. Así salen a la vez las dos cifras que importan: **qué está roto** y
**cuántas intervenciones manuales** hacen falta para llegar al final.

### Tres errores de método propios, corregidos

Se dejan escritos porque cada uno produjo una cifra falsa, y porque son la clase de error que este
repositorio ya ha pagado antes.

1. **Overlay anidado.** La primera máquina limpia guardaba las imágenes del Docker interno sobre el
   sistema de ficheros del contenedor externo. La compilación de Apache AGE fallaba con
   `failed to convert whiteout file: operation not permitted`. **No es un fallo del repositorio**:
   es un artefacto del arnés. Se corrigió montando `/var/lib/docker` sobre un volumen real, y a
   partir de ahí la imagen construye. Si se hubiera dado por bueno, el informe habría acusado al
   repositorio de algo que no hace.

2. **Códigos de salida enmascarados por una tubería.** Los pasos se ejecutaban como
   `comando 2>&1 | tail -20`, y `tail` devuelve 0 aunque el comando muera. Dos pasos —recolección de
   `pytest` y arranque de `uvicorn`— se apuntaron como **correctos** cuando en realidad ni siquiera
   existía el binario (`timeout: failed to run command 'pytest': No such file or directory`). Es una
   verdad vacua de manual, y en la versión definitiva el código de salida se captura sin tubería.

3. **Nombre del clon elegido a mano.** La primera pasada clonaba en `/fulkro`. Eso **oculta** un bug
   real: `git clone` sin argumentos crea `Fulkrosys`, el proyecto de Compose pasa a llamarse
   `fulkrosys`, y `scripts/build_test_db.sh` busca un contenedor `fulkro-postgres-1` cableado por
   defecto que ya no existe. La traza definitiva clona con el nombre por defecto.

---

## Fallos encontrados

Siete fallos, tres de ellos con arreglo manual conocido. Se reproducen con el arnés que va en el repositorio; abajo va lo esencial de cada uno.

```bash
bash scripts/maquina_limpia_up.sh fulkro-limpia
docker cp scripts/traza_instalacion_limpia.sh fulkro-limpia:/t.sh
docker exec fulkro-limpia bash /t.sh && docker exec fulkro-limpia cat /trace3.log
```

**Cifra de cabecera: 3 pasos manuales que el README no menciona, y 4 fallos que ni siquiera tienen
arreglo manual documentado.** Tiempo total del recorrido, con los arreglos ya conocidos aplicados
sobre la marcha: **229 s**.

### F1 · `python3.12 -m venv` no funciona en un Ubuntu limpio

Paso 1a del README. `ensurepip` no viene en la imagen base.

```console
$ python3.12 -m venv .venv
The virtual environment was not created successfully because ensurepip is not
available.  On Debian/Ubuntu systems, you need to install the python3-venv
package using the following command.
    apt install python3.12-venv
```

**Arreglo manual M1:** `apt-get install -y python3.12-venv python3-pip`. El README no lo menciona.

### F2 · `pip install -e backend[dev]` no compila: falta el entorno de construcción de `pycairo`

Paso 1b. `mjml-python>=1.4` (`backend/pyproject.toml:56`) arrastra `pycairo`, que se construye desde
fuente y necesita `pkg-config`, CMake y las cabeceras de cairo.

```console
$ .venv/bin/pip install -e "backend[dev]"
      Did not find pkg-config by name 'pkg-config'
      Found pkg-config: NO
      Did not find CMake 'cmake'
      Run-time dependency cairo found: NO
      ../cairo/meson.build:31:12: ERROR: Dependency lookup for cairo with method
      'pkg-config' failed: Pkg-config for machine host machine not found. Giving up.
error: metadata-generation-failed
```

**Arreglo manual M2:** `apt-get install -y pkg-config cmake libcairo2-dev python3.12-dev build-essential`.
Con eso la instalación tarda 49 s y termina bien. El README no declara ninguna dependencia de sistema.

### F3 · `cp .env.example .env` deja las cuatro variables obligatorias sin definir

Paso 3. `backend/app/startup_checks.py:34` declara cuatro variables sin las cuales el arranque aborta.
`.env.example` no trae **ninguna** de las cuatro sin comentar.

```console
$ cp .env.example .env
$ for v in DATABASE_URL FULKRO_AUTH_PRIVATE_KEY FULKRO_ML_PRIVATE_KEY FULKRO_BACKUP_SIGNING_KEY; do
>   grep -qE "^${v}=" .env && echo "$v: SI" || echo "$v: NO"; done
DATABASE_URL: NO
FULKRO_AUTH_PRIVATE_KEY: NO
FULKRO_ML_PRIVATE_KEY: NO
FULKRO_BACKUP_SIGNING_KEY: NO
```

Sin arreglo manual documentado: el README trata el `cp` como suficiente.

### F4 · `build_test_db.sh` busca un contenedor que solo existe si el clon se llama `fulkro`

Paso 4. `scripts/build_test_db.sh:12` cablea `CONTAINER="${FULKRO_PG_CONTAINER:-fulkro-postgres-1}"`.
El repositorio es `Fulkrosys`, así que `git clone` sin argumentos crea el directorio `Fulkrosys`, el
proyecto de Compose pasa a llamarse `fulkrosys` y los contenedores llevan ese prefijo. Falla en el
paso 1 de 6.

```console
$ bash scripts/build_test_db.sh
==> [1/6] drop+create fulkro_test
Error response from daemon: No such container: fulkro-postgres-1

  busca : fulkro-postgres-1        <- default cableado
  existe: fulkrosys-postgres-1     <- lo que compose crea de verdad
  existe: fulkrosys-redis-1
  existe: fulkrosys-minio-1
```

Es sobreescribible con `FULKRO_PG_CONTAINER`, pero eso no está en el README. Este fallo se le
escapa a quien clone en un directorio llamado `fulkro`, que es justamente lo que hacía la primera
versión de esta traza.

### F5 · La recolección de `pytest` aborta: tres dependencias se importan y no están declaradas

Paso 5. Salida 2, y ni un test llega a ejecutarse.

```console
$ PYTHONPATH=. .venv/bin/python -m pytest backend/tests/ --collect-only -q
ERROR backend/tests/corpus/test_pdf_ingest.py
ERROR backend/tests/corpus/test_rd311_parser.py
ERROR backend/tests/motors/m16_onboarding/test_m16_cierre.py
ERROR backend/tests/motors/m16_onboarding/test_m16_connectors.py
ERROR backend/tests/motors/m16_onboarding/test_oauth_service.py
ERROR backend/tests/motors/m_remediation/test_cloud_writers_simulator.py
ERROR backend/tests/test_corpus_clean.py
!!!!!!!!!!!!!!!!!!! Interrupted: 7 errors during collection !!!!!!!!!!!!!!!!!!!!
6383 tests collected, 7 errors in 10.29s
```

La causa raíz de los siete, con su traza: `ModuleNotFoundError: No module named 'bs4'` (3 ficheros),
`respx` (4) y `pypdf` (1). Ninguna de las tres está en `backend/pyproject.toml`. **Este es el motivo
por el que el job `test` del CI fallaría siempre si alguien lo activase**, sin ejecutar un solo test.

### F6 · El backend aborta en el arranque, incluso arrancándolo como el README dice

Y esto es lo más incómodo del recorrido: el mensaje de error recomienda exactamente lo que ya
estábamos haciendo.

```console
$ .venv/bin/python -m uvicorn backend.app.main:app --env-file .env
backend.app.startup_checks.CriticalConfigError: Env vars críticas ausentes:
['DATABASE_URL', 'FULKRO_AUTH_PRIVATE_KEY', 'FULKRO_ML_PRIVATE_KEY', 'FULKRO_BACKUP_SIGNING_KEY'].
En dev: arrancar uvicorn con `--env-file .env` (LECCIÓN-OPS-004). En prod: gestor de secrets.
```

El consejo del mensaje no resuelve nada aquí, porque el problema no es cómo se arranca sino que
`.env.example` no define esas variables (F3). Un lector honesto se queda atascado creyendo que ha
hecho algo mal.

### F7 · No hay Node ni npm, y el README los da por supuestos

Paso del frontend. `npm install` funciona (19 s) una vez instalado Node 20.

**Arreglo manual M3:** instalar Node desde NodeSource. El README dice `cd frontend && npm install`
sin mencionar que hace falta Node ni qué versión.

---

## Resumen de la línea base

| | |
|---|---:|
| Pasos del README recorridos | 9 |
| Fallos | **7** |
| Pasos manuales no documentados | **3** |
| Tiempo total del recorrido | 229 s |
| ¿Queda una aplicación navegable al final? | **No** |

Al terminar los nueve pasos no hay ni backend ni base de datos provisionada: hay un frontend con
sus dependencias instaladas, tres contenedores de infraestructura y una API que no arranca.


---

## Ejecución limpia (C0.10)

<!-- RELLENAR: se añade al cerrar C0.10 -->
