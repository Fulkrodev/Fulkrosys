# Instalación

Un solo comando deja la aplicación navegable con datos dentro. No hace falta ninguna clave de API
ni cuenta en ningún servicio.

```bash
git clone https://github.com/Fulkrodev/Fulkrosys.git
cd Fulkrosys
make demo
```

Al terminar imprime la URL y las credenciales. Después:

```bash
make smoke     # comprueba que hay datos reales en los tres portales
```

> Si prefiere leer antes de ejecutar: `make demo` construye dos imágenes Docker, levanta siete
> contenedores en `localhost`, migra la base, la siembra y crea un operador con su segundo factor.
> No toca nada fuera de Docker salvo un fichero `.env.demo` en el directorio del clon, que está
> ignorado por git.

---

## Requisitos

| | Mínimo | Comprobar con |
|---|---|---|
| Docker Engine | 24 (probado con **29.8.0**) | `docker --version` |
| Docker Compose | v2 (probado con **v5.5.1**) | `docker compose version` |
| git | cualquiera reciente (probado con **2.43.0**) | `git --version` |
| GNU make | cualquiera | `make --version` |

**Nada más.** No hace falta Python, ni Node, ni PostgreSQL en el equipo: todo corre dentro de
contenedores. Esto es deliberado, porque instalar el backend a mano en una máquina limpia exige
un entorno de compilación de C que el proyecto no declaraba (ver *Problemas frecuentes*).

### Espacio y memoria, medidos

| | |
|---|---:|
| Imágenes descargadas y construidas | **~10,8 GB** |
| └ `fulkro/backend:demo` | 7,91 GB |
| └ `fulkro/frontend:demo` | 1,85 GB |
| └ `pgvector/pgvector:pg16` | 621 MB |
| └ minio + mc + redis | 419 MB |
| Volúmenes de datos tras `make demo` | ~118 MB |
| **Memoria con la pila en reposo** | **~754 MiB** |
| └ backend | 530 MiB |
| └ postgres | 75 MiB |
| └ minio | 75 MiB |
| └ frontend | 70 MiB |
| └ redis | 3,5 MiB |

```console
$ docker stats --no-stream --format '{{.Name}}\t{{.MemUsage}}' $(docker compose -f docker-compose.demo.yml -p fulkro-demo ps -q)
fulkro-demo-backend-1   530.1MiB / 25.44GiB
fulkro-demo-frontend-1  70.2MiB / 25.44GiB
fulkro-demo-minio-1     74.53MiB / 25.44GiB
fulkro-demo-postgres-1  75.37MiB / 25.44GiB
fulkro-demo-redis-1     3.477MiB / 25.44GiB
```

**Disco: reserve 25 GB para la primera vez.** Medido dentro de una máquina limpia, después de un
`make demo` construyendo desde cero:

```console
$ docker system df
TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE
Images          6         6         10.58GB   0B (0%)
Containers      7         5         335.9kB   86.02kB (25%)
Local Volumes   4         4         119.2MB   0B (0%)
Build Cache     51        0         11.76GB   9.912GB
```

La caché de construcción pesa casi tanto como las imágenes y **nadie la cuenta**: son 11,76 GB, de
los cuales 9,9 GB se pueden liberar en cuanto termine. En régimen, tras `docker builder prune`, el
demo se queda en unos **11 GB**. El consumo del disco del anfitrión durante la verificación
completa fue de **~19 GB**.

**La imagen del backend pesa 7,91 GB**, y conviene decir por qué: lleva dentro el instrumental de
pentest (nuclei, trivy, grype, semgrep, prowler, checkov, ScoutSuite, tesseract). Para *ver* la
aplicación no hace falta nada de eso; adelgazar la imagen del demo está pendiente y se dice en
*Lo que no funciona todavía*.

---

## Qué se espera ver

`make demo` termina con un bloque así (los códigos y los identificadores cambian en cada ejecución):

```
════════════════════════════════════════════════════════════════════════
  DEMO DE FULKRO · LISTO
════════════════════════════════════════════════════════════════════════
  Aplicación   http://localhost:3000
  API / docs   http://localhost:18000/docs

  ── Administración ───────────────────────────────────────
  Entrar en    http://localhost:3000/login
  Correo       demo@fulkro.es
  Contraseña   fulkro-demo-2026
  Código TOTP  519029   (cambia cada 30 s)
  Secreto TOTP 3MCQGE4P55MLUKTC5QZX6AHV5YV3MGP5

  ── Portal de cliente ────────────────────────────────────
  Entrar en    http://localhost:3000/client-portal/login
  Correo       cliente@fulkro.es
  Contraseña   fulkro-demo-2026

  ── Portal de auditor (enlace de un solo uso) ────────────
  Entrar en    http://localhost:3000/auditor-portal/<token>/summary
  Código OTP   380237
════════════════════════════════════════════════════════════════════════
```

**El acceso de administración pide segundo factor**, porque el producto no permite entrar sin él:
`POST /auth/login` solo devuelve un ticket, y la cookie de sesión la emite `/auth/totp/verify`. El
demo resuelve eso enrolando TOTP automáticamente e imprimiendo el secreto y un código vigente; no
hay ninguna bandera para desactivar el segundo factor, precisamente para que no exista una que
pueda escaparse a producción. Puede escanear el secreto con cualquier autenticador, o usar el
código que imprime (cambia cada 30 segundos: si caduca, `make demo` otra vez lo reimprime sin
resembrar).

Las credenciales por defecto se cambian con `FULKRO_DEMO_OWNER_EMAIL` y `FULKRO_DEMO_OWNER_PASSWORD`.

### Con qué datos viene

`make demo` no deja pantallas vacías. Siembra, medido sobre una base creada desde cero:

| Ámbito | Tabla | Filas |
|---|---|---:|
| Global | medidas del Anexo II | 73 |
| Global | mapeo MAGERIT–ENS | 73 |
| Global | amenazas / salvaguardas | 57 / 98 |
| Global | plantillas documentales | 123 |
| Global | corpus normativo (con vector) | 1.031 |
| Proyecto | entradas de Declaración de Aplicabilidad | 73 |
| Proyecto | evidencias | 204 |
| Proyecto | tareas del plan | 35 |
| Proyecto | documentos generados | 21 |

`make smoke` contrasta esas cifras contra sus umbrales y entra en los tres portales. **Con la base
vacía falla a propósito**: es su criterio de aceptación, no un adorno.

---

## Cómo pararlo y cómo borrarlo

```bash
make down      # para y borra los contenedores · CONSERVA la base y .env.demo
make demo      # vuelve a levantar lo mismo sin resembrar

make clean     # además borra los volúmenes y .env.demo · se pierden los datos
```

`make clean` no borra las imágenes. Para recuperar también esos ~10,8 GB:

```bash
docker rmi fulkro/backend:demo fulkro/frontend:demo
docker builder prune          # caché de construcción
```

---

## Alternativa sin compilar

La imagen del backend se publica en GHCR etiquetada por commit, así que se puede usar la de un
commit exacto sin construir nada:

```bash
docker pull ghcr.io/fulkrodev/fulkrosys/backend:latest
# o por commit exacto (SHA completo, no abreviado):
docker pull ghcr.io/fulkrodev/fulkrosys/backend:sha-<sha completo>
```

El workflow que la publica es
[`.github/workflows/publish-image.yml`](.github/workflows/publish-image.yml), y su primera
ejecución en `main` terminó en verde el 10 de septiembre de 2026. **Salvedad honesta:** lo que
está medido de punta a punta es `make demo` (ver `docs/INSTALL_TRACE.md`); de esta vía se ha
comprobado que el workflow publica, no que un tercero levante la aplicación partiendo del
`docker pull`.

---

## Problemas frecuentes

Esta sección no es genérica: son los fallos reales que aparecieron al seguir el README anterior en
un Ubuntu 24.04 limpio. La traza completa, con sus siete fallos numerados, está en
[`docs/INSTALL_TRACE.md`](docs/INSTALL_TRACE.md).

### `make demo` falla con «bind: An attempt was made to access a socket…»

Windows reserva rangos de puertos dinámicos a partir del 49152 (Hyper-V / WinNAT), y `docker
compose` muere al intentar publicar uno de ellos. Los puertos del demo ya están todos por debajo de
ese umbral por este motivo. Si aun así choca con algo suyo, mire qué rangos tiene excluidos:

```console
$ netsh interface ipv4 show excludedportrange protocol=tcp
```

y cambie el puerto en `docker-compose.demo.yml`.

### Quiero instalarlo a mano, sin Docker

Se puede, pero el proyecto necesita un entorno de compilación de C que no declaraba. En un Ubuntu
24.04 limpio, `pip install -e "backend[dev]"` falla porque `mjml-python` arrastra `pycairo`, que se
construye desde fuente:

```
Did not find pkg-config by name 'pkg-config'
Run-time dependency cairo found: NO
error: metadata-generation-failed
```

Hacen falta, antes:

```bash
sudo apt install python3.12-venv python3-pip \
                 pkg-config cmake libcairo2-dev python3.12-dev build-essential
```

`python3.12-venv` es imprescindible por separado: sin él, `python3.12 -m venv` falla con
«ensurepip is not available».

### `cp .env.example .env` y el backend no arranca

Ya no debería pasar: `.env.example` trae ahora las cuatro variables que `startup_checks.py` exige, y
hay un test que impide que vuelva a quedarse corto. Pero recuerde que **escribir `.env` no basta**:
pydantic lee el fichero y no lo exporta a `os.environ`, y el arranque mira `os.environ`. Hay que
arrancar con `uvicorn --env-file .env` o exportar las variables de verdad. `make demo` no tiene este
problema porque las inyecta como entorno del contenedor.

### `scripts/build_test_db.sh` dice «No such container»

El script deriva el nombre del contenedor del proyecto de Compose, que sale del nombre del
directorio. Si clonó en un directorio con otro nombre, dígaselo:

```bash
FULKRO_PG_CONTAINER=mi-postgres-1 bash scripts/build_test_db.sh
```

Si no encuentra el contenedor, **aborta y lista los candidatos** en vez de elegir uno: su primer
paso hace `DROP DATABASE` y equivocarse destruiría la base de otro proyecto.

### El copiloto tarda mucho la primera vez que se le pregunta

El modelo de embeddings se descarga de HuggingFace en la primera consulta al corpus, no durante el
arranque. Son unos 2 GB y necesita red. El volumen de caché lo conserva, así que solo pasa una vez
por instalación. Está pendiente precargarlo en la imagen.

---

## Lo que no funciona todavía

- **La imagen del backend pesa 7,91 GB** porque lleva el instrumental de pentest, que no hace falta
  para ver la aplicación. Una imagen de demo sin esas herramientas está pendiente.
- **El modelo de embeddings no viene precargado** (ver arriba). Sin red, la búsqueda del copiloto
  sobre el corpus falla; el resto de la aplicación funciona.
- **No hay autorregistro.** Esto no es un producto que una empresa instale y use por su cuenta: es
  la consola de un operador único con portales de cliente por token. El demo crea ese operador por
  usted, pero el modelo de identidad no soporta equipos. Está explicado en el README.
