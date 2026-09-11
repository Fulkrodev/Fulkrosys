# FULKRO — atajos de operación local.
#
# Objetivo: que un tercero levante la aplicación entera y compruebe que trae
# datos reales con dos órdenes (`make demo` y `make smoke`), sin leerse el repo
# antes.  `make help` lista todo.
#
# CUIDADO (medido 2026-09-10): `backend/alembic.ini:3` cablea
# `sqlalchemy.url = postgresql://fulkro:changeme@localhost:5433/fulkro`, y
# `backend/migrations/env.py` cae a esa URL si falta `DATABASE_MIGRATE_URL`.
# Por eso NINGÚN objetivo de este fichero invoca alembic: las migraciones del
# demo las corre `infra/docker/provision-entrypoint.sh` DENTRO del contenedor,
# que exporta su propia `DATABASE_MIGRATE_URL` explícita (línea 107). Si algún
# día se añade aquí un objetivo que llame a alembic, tiene que exportar
# `DATABASE_MIGRATE_URL` sí o sí, o migrará la base de desarrollo de alguien.

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.ONESHELL:
.DEFAULT_GOAL := help

# ── Contrato del demo ───────────────────────────────────────────────────────
COMPOSE_FILE ?= docker-compose.demo.yml
PROJECT      ?= fulkro-demo
ENV_FILE     ?= .env.demo
DEMO_URL     ?= http://localhost:3000
BACKEND_URL  ?= http://127.0.0.1:18000

# docker-compose.demo.yml NO interpola `${...}`: cada servicio lee sus secretos
# con `env_file: .env.demo`. Por eso aquí no hace falta `--env-file`.
DC = docker compose -f $(COMPOSE_FILE) -p $(PROJECT)

# Servicios que deben quedar EN PIE. `minio-init` y `provision` son de un solo
# disparo (terminan con código 0) y se comprueban aparte.
LIVE_SERVICES    ?= postgres redis minio backend frontend
ONESHOT_SERVICES ?= minio-init provision

# Espera activa: se consulta el ESTADO de cada servicio, no se duerme a ciegas.
# HEALTH_RETRIES x HEALTH_INTERVAL = techo de espera (por defecto 10 minutos:
# el primer `up` construye la imagen del backend y siembra la base entera).
HEALTH_RETRIES  ?= 120
HEALTH_INTERVAL ?= 5

# Credenciales del operador del demo (los defaults son parte del contrato).
FULKRO_DEMO_OWNER_EMAIL    ?= demo@fulkro.es
FULKRO_DEMO_OWNER_PASSWORD ?= fulkro-demo-2026

RUFF   ?= ruff
PYTEST ?= pytest

# Conexión a la base del demo (la fija docker-compose.demo.yml en `environment:`).
PG_USER_DEMO ?= fulkro
PG_DB_DEMO   ?= fulkro

.PHONY: help demo smoke down clean test lint logs recorrido recorrer-todo carga check-tools .env-keys eval-recuperacion

# ───────────────────────────────────────────────────────────────────────────
help:
	@echo "FULKRO — objetivos disponibles"
	@echo
	@echo "  make demo    Levanta la aplicación entera con $(COMPOSE_FILE) y la deja"
	@echo "               poblada: genera $(ENV_FILE) si no existe, construye las"
	@echo "               imágenes, espera a que los servicios estén sanos y termina"
	@echo "               imprimiendo la URL y las credenciales de entrada."
	@echo "                 aplicación  $(DEMO_URL)"
	@echo "                 API (docs)  $(BACKEND_URL)/docs"
	@echo
	@echo "  make smoke   Comprueba que el demo trae DATOS REALES: entra en los tres"
	@echo "               portales (administrador, cliente y auditor) y contrasta los"
	@echo "               recuentos de catálogo con sus umbrales. Con la base vacía"
	@echo "               FALLA (es su criterio de aceptación)."
	@echo
	@echo "  make down    PARA la pila y borra los contenedores. CONSERVA los"
	@echo "               volúmenes (la base de datos sobrevive) y CONSERVA"
	@echo "               $(ENV_FILE): 'make demo' vuelve a levantar lo mismo sin"
	@echo "               resembrar."
	@echo
	@echo "  make clean   Además de lo anterior, BORRA los volúmenes (se pierden la"
	@echo "               base de datos y los ficheros de MinIO) y borra $(ENV_FILE)"
	@echo "               (se pierden las claves y las contraseñas generadas)."
	@echo "               Es el reinicio de cero."
	@echo
	@echo "  make logs    Vuelca los logs de la pila (SERVICE=backend para uno solo)."
	@echo
	@echo "  make test    pytest backend/tests/ — necesita la base de datos de test ya"
	@echo "               provisionada:  bash scripts/build_test_db.sh"
	@echo
	@echo "  make lint    ruff check backend/  (lo mismo que el job 'lint' de CI)."
	@echo
	@echo "  make recorrido  Comprueba que el recorrido guiado de USAGE.md sigue"
	@echo "                  siendo cierto: navega el demo y contrasta cada cifra,"
	@echo "                  rótulo y botón que el documento promete."
	@echo
	@echo "  make recorrer-todo   Abre las 167 páginas de la aplicación, una por una,"
	@echo "               con tres sesiones de verdad (operador, cliente y portal por"
	@echo "               token) y por el puerto del frontend. De cada una mide si trae"
	@echo "               CONTENIDO REAL o sólo dice «no hay datos», qué peticiones"
	@echo "               fallan por debajo, si hay texto fabricado en pantalla y si"
	@echo "               alguien puede llegar pinchando. Necesita el demo en pie."
	@echo "                 informe  docs/RECORRIDO_COMPLETO.md"
	@echo
	@echo "  make carga   Rampa de concurrencia sobre los seis endpoints más usados"
	@echo "               hasta encontrar dónde se rompe el p95, con una réplica y con"
	@echo "               dos. Convierte «escalable» en un número con su límite dicho."
	@echo "                 informe  docs/PRUEBA_DE_CARGA.md"
	@echo
	@echo "  make eval-recuperacion   MIDE si el buscador del corpus recupera lo que"
	@echo "               debe: hitrate@k, recall@k y MRR sobre 49 consultas etiquetadas"
	@echo "               a mano. Mide la rama que corre (vectorial) Y las que se"
	@echo "               retiraron (léxica y fusión RRF), para poder volver a decidir"
	@echo "               cuando cambie el corpus. NO mide la calidad de la RESPUESTA"
	@echo "               del modelo, sólo qué fragmentos le llegan. Necesita el demo."
	@echo "                 informe con las conclusiones  docs/EVAL_RECUPERACION.md"
	@echo

# ───────────────────────────────────────────────────────────────────────────
# Herramientas del anfitrión. Medido: la imagen `ubuntu:24.04` pelada no trae
# curl, ni python3, ni openssl; una instalación real de Ubuntu 24.04 sí trae
# python3 y openssl. Se comprueba antes de empezar y se dice qué falta, en vez
# de reventar a mitad del arranque.
check-tools:
	@missing=""
	for t in docker curl python3; do
		command -v "$$t" >/dev/null 2>&1 || missing="$$missing $$t"
	done
	if [ -n "$$missing" ]; then
		echo "ERROR: faltan herramientas en este equipo:$$missing" >&2
		echo "       Ubuntu/Debian:  sudo apt-get install -y$$missing" >&2
		exit 1
	fi
	if ! docker compose version >/dev/null 2>&1; then
		echo "ERROR: no hay 'docker compose' (plugin v2)." >&2
		echo "       Ubuntu/Debian:  sudo apt-get install -y docker-compose-plugin" >&2
		exit 1
	fi
	if ! docker info >/dev/null 2>&1; then
		echo "ERROR: el demonio de Docker no responde (¿arrancado? ¿permisos del grupo docker?)." >&2
		exit 1
	fi
	if [ ! -f "$(COMPOSE_FILE)" ]; then
		echo "ERROR: no existe $(COMPOSE_FILE) en $$(pwd)." >&2
		echo "       Ejecuta make desde la raíz del repositorio." >&2
		exit 1
	fi

# ───────────────────────────────────────────────────────────────────────────
# $(ENV_FILE) — se genera UNA vez y NO se versiona (está en .gitignore).
#
# Trae exactamente lo que docker-compose.demo.yml declara en su "CONTRATO CON
# .env.demo". Lo que ese compose ya fija en `environment:` (APP_ENV, REDIS_URL,
# MINIO_ENDPOINT, PROVISION_PGHOST, PROVISION_SEED_FLAGS...) NO se repite aquí:
# `environment:` gana sobre `env_file:`, así que duplicarlo solo crearía dos
# sitios donde mirar.
#
# Contraseñas: las de infraestructura (Postgres, MinIO) se generan aleatorias y
# el fichero queda en modo 600; nadie las teclea. La del operador que SÍ se
# teclea en la pantalla de login es fija y está en el contrato del demo.
$(ENV_FILE):
	@echo "==> generando $(ENV_FILE) (contraseñas aleatorias + claves Ed25519)"
	rand() { head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n'; }
	pg_pw="$$(rand)"; app_pw="$$(rand)"; mig_pw="$$(rand)"
	minio_pw="$$(rand)"; secret="$$(rand)$$(rand)"; backup_pw="$$(rand)"
	umask 077
	cat > $(ENV_FILE) <<-ENVEOF
		# FULKRO · entorno del DEMO. Lo genera 'make demo'. NO se versiona.
		# Regenerarlo de cero:  make clean && make demo
		# El contrato de estas variables está documentado en la cabecera de
		# docker-compose.demo.yml.

		# ── PostgreSQL ───────────────────────────────────────────────────────
		# El usuario y la base (fulkro/fulkro) los fija el propio compose.
		POSTGRES_PASSWORD=$$pg_pw
		PROVISION_SUPER_PW=$$pg_pw
		PROVISION_APP_PW=$$app_pw
		PROVISION_MIGRATE_PW=$$mig_pw
		DATABASE_URL=postgresql+asyncpg://fulkro_app:$$app_pw@postgres:5432/fulkro
		DATABASE_URL_SYNC=postgresql://fulkro_app:$$app_pw@postgres:5432/fulkro
		DATABASE_MIGRATE_URL=postgresql://fulkro_migrate:$$mig_pw@postgres:5432/fulkro

		# ── MinIO ────────────────────────────────────────────────────────────
		# MINIO_ROOT_* las lee el servidor; MINIO_ACCESS_KEY/MINIO_SECRET_KEY las
		# lee backend/app/config.py (sin prefijo FULKRO_). Tienen que coincidir.
		MINIO_ROOT_USER=fulkro
		MINIO_ROOT_PASSWORD=$$minio_pw
		MINIO_ACCESS_KEY=fulkro
		MINIO_SECRET_KEY=$$minio_pw

		# ── Aplicación ───────────────────────────────────────────────────────
		# APP_SECRET_KEY deriva el cifrado Fernet de tokens OAuth y credenciales
		# de pentest: >=32 caracteres.
		APP_SECRET_KEY=$$secret
		BACKUP_ENCRYPTION_KEY=$$backup_pw
		# Sin clave de Anthropic el copiloto LLM no responde; el resto funciona.
		ANTHROPIC_API_KEY=

		# ── Operador del demo ────────────────────────────────────────────────
		# backend/scripts/demo_bootstrap.py crea/actualiza este usuario y le
		# auto-enrola TOTP. MARCOS_ADMIN_EMAIL apunta al mismo correo para que la
		# identidad de administrador del backend sea ese operador.
		FULKRO_DEMO_OWNER_EMAIL=$(FULKRO_DEMO_OWNER_EMAIL)
		FULKRO_DEMO_OWNER_PASSWORD=$(FULKRO_DEMO_OWNER_PASSWORD)
		MARCOS_ADMIN_EMAIL=$(FULKRO_DEMO_OWNER_EMAIL)
	ENVEOF
	$(MAKE) --no-print-directory .env-keys ENV_FILE=$(ENV_FILE)
	chmod 600 $(ENV_FILE)

# Las cuatro claves Ed25519 dentro de $(ENV_FILE) (tres privadas + la pública
# de AUTH, que lee el middleware del frontend).
#
# Camino canónico: scripts/generate_dev_signing_keys.py, que necesita el paquete
# 'cryptography'. Si no hay ningún intérprete que lo tenga, se cae a openssl,
# que emite EL MISMO formato (PEM PKCS#8 Ed25519); se avisa por pantalla.
.env-keys:
	@pybin=""
	for cand in "$${PYTHON:-}" ./.venv/bin/python python3; do
		[ -n "$$cand" ] || continue
		command -v "$$cand" >/dev/null 2>&1 || continue
		"$$cand" -c 'import cryptography' >/dev/null 2>&1 || continue
		pybin="$$cand"; break
	done
	if [ -n "$$pybin" ]; then
		echo "==> claves Ed25519 con scripts/generate_dev_signing_keys.py ($$pybin)"
		"$$pybin" scripts/generate_dev_signing_keys.py \
			--env-file $(ENV_FILE) --no-frontend-env
	elif command -v openssl >/dev/null 2>&1; then
		echo "AVISO: no hay ningún Python con el paquete 'cryptography' en este equipo."
		echo "       Genero las claves Ed25519 con openssl (mismo formato PEM PKCS#8)."
		tmpdir="$$(mktemp -d)"
		trap 'rm -rf "$$tmpdir"' EXIT
		for var in FULKRO_AUTH_PRIVATE_KEY FULKRO_ML_PRIVATE_KEY FULKRO_BACKUP_SIGNING_KEY; do
			openssl genpkey -algorithm ed25519 -out "$$tmpdir/$$var.pem" 2>/dev/null
			{ printf '\n%s="' "$$var"; cat "$$tmpdir/$$var.pem"; printf '"\n'; } >> $(ENV_FILE)
		done
		{ printf 'FULKRO_AUTH_PUBLIC_KEY="'
		  openssl pkey -in "$$tmpdir/FULKRO_AUTH_PRIVATE_KEY.pem" -pubout
		  printf '"\n'; } >> $(ENV_FILE)
	else
		echo "ERROR: no puedo generar las claves Ed25519." >&2
		echo "       Instala openssl, o un Python con 'cryptography' (pip install" >&2
		echo "       cryptography), y repite 'make demo'." >&2
		exit 1
	fi

# ───────────────────────────────────────────────────────────────────────────
demo: check-tools $(ENV_FILE)
	@echo "==> construyendo y levantando la pila del demo ($(PROJECT))"
	@# La imagen del backend se construye UNA vez y la comparten `backend` y `provision`.
	@# Construir con `up --build` los ponia a exportar el mismo tag en paralelo y fallaba
	@# con «image already exists» (medido en la primera ejecucion real de `make demo`).
	$(DC) build backend frontend
	$(DC) up -d --no-build
	echo "==> servicios de un solo disparo: $(ONESHOT_SERVICES)"
	for svc in $(ONESHOT_SERVICES); do
		cid="$$($(DC) ps -aq "$$svc" 2>/dev/null || true)"
		if [ -z "$$cid" ]; then
			echo "    - $$svc: no está en $(COMPOSE_FILE), lo salto"
			continue
		fi
		ok=""
		for i in $$(seq 1 $(HEALTH_RETRIES)); do
			st="$$(docker inspect -f '{{.State.Status}}' "$$cid" || true)"
			if [ "$$st" = "exited" ]; then ok="si"; break; fi
			sleep $(HEALTH_INTERVAL)
		done
		if [ -z "$$ok" ]; then
			echo "ERROR: '$$svc' sigue sin terminar tras $$(( $(HEALTH_RETRIES) * $(HEALTH_INTERVAL) )) s. Últimos logs:" >&2
			$(DC) logs --tail 200 "$$svc" >&2 || true
			exit 1
		fi
		code="$$(docker inspect -f '{{.State.ExitCode}}' "$$cid" || true)"
		if [ "$$code" != "0" ]; then
			echo "ERROR: '$$svc' terminó con código $$code. Últimos logs:" >&2
			$(DC) logs --tail 200 "$$svc" >&2 || true
			exit 1
		fi
		echo "    - $$svc: terminado con código 0"
	done
	echo "==> servicios que deben quedar en pie: $(LIVE_SERVICES)"
	for svc in $(LIVE_SERVICES); do
		cid="$$($(DC) ps -q "$$svc" 2>/dev/null || true)"
		if [ -z "$$cid" ]; then
			echo "ERROR: el servicio '$$svc' no tiene contenedor. Estado de la pila:" >&2
			$(DC) ps -a >&2 || true
			exit 1
		fi
		ok=""; st=""; hz=""
		for i in $$(seq 1 $(HEALTH_RETRIES)); do
			st="$$(docker inspect -f '{{.State.Status}}' "$$cid" || true)"
			hz="$$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}sin-healthcheck{{end}}' "$$cid" || true)"
			if [ "$$st" = "running" ] && { [ "$$hz" = "healthy" ] || [ "$$hz" = "sin-healthcheck" ]; }; then
				ok="si"; break
			fi
			if [ "$$st" = "exited" ] || [ "$$st" = "dead" ]; then
				echo "ERROR: el servicio '$$svc' se ha caído (estado=$$st). Últimos logs:" >&2
				$(DC) logs --tail 200 "$$svc" >&2 || true
				exit 1
			fi
			sleep $(HEALTH_INTERVAL)
		done
		if [ -z "$$ok" ]; then
			echo "ERROR: '$$svc' no llegó a estar sano en $$(( $(HEALTH_RETRIES) * $(HEALTH_INTERVAL) )) s (último estado=$$st salud=$$hz). Últimos logs:" >&2
			$(DC) logs --tail 200 "$$svc" >&2 || true
			exit 1
		fi
		echo "    - $$svc: en pie (salud: $$hz)"
	done
	# Sondeo HTTP desde el anfitrión: comprueba además que los puertos publicados
	# en 127.0.0.1 responden. OJO: /api/v1/health NO toca la base de datos
	# (devuelve {status,version,environment} pase lo que pase), así que sirve para
	# saber si uvicorn responde y para NADA MÁS. Quien comprueba que hay datos es
	# 'make smoke'.
	echo "==> sondeo HTTP desde el anfitrión"
	for i in $$(seq 1 $(HEALTH_RETRIES)); do
		if curl -fsS -o /dev/null --max-time 5 "$(BACKEND_URL)/api/v1/health"; then break; fi
		if [ "$$i" = "$(HEALTH_RETRIES)" ]; then
			echo "ERROR: el backend no responde en $(BACKEND_URL). Últimos logs:" >&2
			$(DC) logs --tail 200 backend >&2 || true
			exit 1
		fi
		sleep $(HEALTH_INTERVAL)
	done
	echo "    - backend: responde en $(BACKEND_URL)"
	for i in $$(seq 1 $(HEALTH_RETRIES)); do
		# curl imprime "000" y ADEMÁS sale con código != 0 cuando no conecta: un
		# `|| echo 000` encadenaría un segundo "000" y saldría "000000", que como
		# número vale 0 y colaría por el `-lt 500`. Se normaliza en dos pasos.
		code="$$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$(DEMO_URL)/" 2>/dev/null || true)"
		code="$${code:-000}"
		if [ "$$code" != "000" ] && [ "$$code" -lt 500 ]; then break; fi
		if [ "$$i" = "$(HEALTH_RETRIES)" ]; then
			echo "ERROR: el frontend no responde en $(DEMO_URL) (último código HTTP: $$code). Últimos logs:" >&2
			$(DC) logs --tail 200 frontend >&2 || true
			exit 1
		fi
		sleep $(HEALTH_INTERVAL)
	done
	echo "    - frontend: responde en $(DEMO_URL)"
	echo "==> creando el operador del demo y enrolando su segundo factor"
	$(DC) exec -T -e PYTHONPATH=/app backend python backend/scripts/demo_bootstrap.py
	echo
	echo "════════════════════════════════════════════════════════════════"
	echo " FULKRO · demo levantado"
	echo "   aplicación : $(DEMO_URL)"
	echo "   API (docs) : $(BACKEND_URL)/docs"
	echo "   credenciales y código de un solo uso: en el bloque de arriba"
	echo "   comprobar que hay datos reales:  make smoke"
	echo "════════════════════════════════════════════════════════════════"

# ───────────────────────────────────────────────────────────────────────────
smoke:
	@bash scripts/demo_smoke.sh

# down  = para y borra los contenedores; CONSERVA volúmenes y $(ENV_FILE).
# clean = además borra los VOLÚMENES (base de datos y MinIO) y $(ENV_FILE).
down:
	@$(DC) down --remove-orphans

clean:
	@$(DC) down -v --remove-orphans || true
	rm -f $(ENV_FILE)
	echo "Borrados: contenedores, volúmenes y $(ENV_FILE)."

SERVICE ?=
logs:
	@$(DC) logs --tail 200 $(SERVICE)

# ───────────────────────────────────────────────────────────────────────────
# Mismo comando que el job 'test' de .github/workflows/ci.yml, con una
# diferencia que conviene saber: el de CI arranca contra un Postgres pelado, sin
# migraciones ni seed, y además está detrás de un
# `if: github.event_name == 'workflow_dispatch'` (nunca se ha disparado). El
# gate real es local y necesita la base provisionada primero.
PYTEST_ARGS ?=
test:
	@echo "Nota: la suite necesita la base de datos de test provisionada."
	echo "      Si falla por conexión o por tablas ausentes:  bash scripts/build_test_db.sh"
	$(PYTEST) backend/tests/ $(PYTEST_ARGS)

# Mismo comando que el job 'lint' de .github/workflows/ci.yml (que fija ruff==0.15.13).
# O8 · `make lint` tiene que funcionar SIN ruff instalado, porque en la maquina
# del autor no lo esta y eso ya ha costado DOS rojos de CI por el mismo F541
# ("f-string sin sustituciones"): se escribio y se empujo sin pasar el linter
# que el CI si pasa. Si no hay ruff en el PATH, se cae a la imagen de test con
# la MISMA version que fija .github/workflows/ci.yml, para que el veredicto
# local y el del CI sean el mismo y no dos opiniones.
RUFF_VERSION ?= 0.15.13
RUFF_IMAGE   ?= fulkro/backend:test

lint:
	@if command -v $(RUFF) >/dev/null 2>&1; then \
		echo "==> ruff local"; \
		$(RUFF) check backend/; \
	elif docker image inspect $(RUFF_IMAGE) >/dev/null 2>&1; then \
		echo "==> ruff $(RUFF_VERSION) en $(RUFF_IMAGE) (no hay ruff local)"; \
		docker run --rm -v "$(PWD)":/app -w /app --entrypoint sh $(RUFF_IMAGE) -c \
			"pip install -q ruff==$(RUFF_VERSION) >/dev/null 2>&1 && ruff check backend/"; \
	else \
		echo "    ERROR: no hay ruff en el PATH ni la imagen $(RUFF_IMAGE)." >&2; \
		echo "    Instala ruff==$(RUFF_VERSION) o construye la imagen (make demo)." >&2; \
		exit 1; \
	fi

# ───────────────────────────────────────────────────────────────────────────
# Comprueba que el recorrido guiado de USAGE.md sigue siendo cierto: navega el
# demo como una persona y contrasta CADA cosa que el documento promete (rótulos,
# cifras, botones, las cinco evidencias firmadas, los tres portales). Un
# recorrido guiado envejece en silencio; esto lo mide.
# Necesita el demo en pie y los navegadores de Playwright ya instalados
# (frontend/node_modules + ~/.cache/ms-playwright).
recorrido:
	@if [ ! -d frontend/node_modules/playwright ]; then
		echo "Falta frontend/node_modules/playwright. Ejecuta: (cd frontend && npm ci)" >&2
		exit 1
	fi
	secreto="$$(docker exec $(PROJECT)-postgres-1 psql -U $(PG_USER_DEMO) -d $(PG_DB_DEMO) -tA \
	  -c "SELECT s.secret FROM auth_totp_secrets s JOIN auth_users u ON u.id = s.user_id \
	      WHERE u.email = '$(FULKRO_DEMO_OWNER_EMAIL)' AND s.verified LIMIT 1;" | tr -d '[:space:]')"
	if [ -z "$$secreto" ]; then
		echo "No hay segundo factor enrolado para $(FULKRO_DEMO_OWNER_EMAIL). ¿Corrió 'make demo'?" >&2
		exit 1
	fi
	SECRETO_TOTP="$$secreto" NODE_PATH=frontend/node_modules \
	  node scripts/verificar_recorrido_usage.cjs

# ───────────────────────────────────────────────────────────────────────────
# Evaluación de la recuperación del corpus (BLOQUE F).
#
# QUÉ MIDE: hitrate@k, recall@k y MRR de CINCO ramas del buscador. Sólo una de
# ellas corre en producción desde el 2026-09-11 (la vectorial); las otras
# cuatro —léxica con AND, léxica con OR, y las dos fusiones RRF— se siguen
# midiendo A PROPÓSITO, porque son las que se retiraron y este comando es lo
# que debe volver a responder si retirarlas sigue siendo lo correcto cuando el
# corpus crezca o cambie el modelo de embeddings.
# Mide además: el barrido de RRF_K, el barrido del PESO de la rama léxica en la
# fusión (w=0 es no fusionar), cuántos relevantes aporta cada rama en
# exclusiva, un ejemplo trabajado de la no monotonía del RRF, si los embeddings
# guardados llevan el prefijo 'passage: ' que espera e5, y la latencia p50/p95
# desglosada por etapa.
#
# hitrate@k y recall@k NO son lo mismo: hitrate@k es la fracción de CONSULTAS
# con al menos un relevante en el top-k; recall@k es la fracción media de LOS
# RELEVANTES de cada consulta que caen ahí. Con 96 etiquetas sobre 49 consultas
# divergen, y hasta el 2026-09-11 el informe llamaba «acierto@k» al primero,
# que no distinguía.
#
# QUÉ **NO** MIDE, y conviene tenerlo delante al leer los números:
#   - La calidad de la RESPUESTA del copiloto. Esto mide qué fragmentos llegan
#     al modelo; lo que el modelo hace con ellos es otra cosa y no se toca aquí.
#   - Nada fuera de las 49 consultas etiquetadas (de 50 escritas; una se excluye
#     porque el corpus no la responde). 49 es una muestra PEQUEÑA: por eso cada
#     punto lleva su intervalo de confianza, que sale ancho.
#   - La relevancia graduada: aquí es binaria (el porqué, en el informe).
#   - Cualquier corpus que no sea el que hay cargado en el demo en ese momento.
#     El script imprime los recuentos que encuentra ANTES de medir, para que se
#     vea contra qué se midió.
#
# Corre DENTRO del contenedor del backend, que es donde están fastembed y la
# base. La primera ejecución descarga el modelo e5-large (~36 s medidos) y la
# guarda en la capa del contenedor: si se recrea el contenedor, se repite.
#
# Con EVAL_AB_PREFIJO=no se salta el A/B de F5, que vuelve a embeber los 1.031
# fragmentos dos veces y es lo que más tarda.
EVAL_AB_PREFIJO ?= si
EVAL_REPETICIONES ?= 5
eval-recuperacion:
	@cid="$$($(DC) ps -q backend 2>/dev/null || true)"
	if [ -z "$$cid" ]; then
		echo "ERROR: el backend del demo no está en pie. Ejecuta 'make demo' primero." >&2
		exit 1
	fi
	extra=""
	[ "$(EVAL_AB_PREFIJO)" = "no" ] && extra="--sin-ab-prefijo" || true
	docker cp scripts/evaluar_recuperacion.py "$$cid":/tmp/evaluar_recuperacion.py
	docker cp backend/tests/eval/consultas_corpus.yaml "$$cid":/tmp/consultas_corpus.yaml
	@# La salida va a /tmp DENTRO del contenedor: /app/out no es escribible por
	@# el usuario del backend en una imagen recien construida (medido: el primer
	@# `make eval-recuperacion` sobre un contenedor nuevo moria con
	@# «PermissionError: /app/out» despues de 12 minutos de calculo).
	docker exec "$$cid" python /tmp/evaluar_recuperacion.py \
	  --conjunto /tmp/consultas_corpus.yaml \
	  --salida /tmp/eval_recuperacion.json \
	  --repeticiones-latencia $(EVAL_REPETICIONES) $$extra
	mkdir -p out
	docker cp "$$cid":/tmp/eval_recuperacion.json out/eval_recuperacion.json
	echo
	echo "Resultados en bruto: out/eval_recuperacion.json"
	echo "Conclusiones y decisiones: docs/EVAL_RECUPERACION.md"

# ───────────────────────────────────────────────────────────────────────────
# Recorrido COMPLETO de la aplicación (BLOQUE E).
#
# La regla que manda sobre todas las demás aquí:
#     UNA PÁGINA QUE CARGA NO ES UNA PÁGINA QUE FUNCIONA.
#
# QUÉ MIDE: abre las 167 páginas que declara `frontend/app` —el inventario se
# DERIVA del árbol, no se escribe a mano— con tres sesiones de verdad (operador,
# cliente y portal por token) y SIEMPRE por el puerto del frontend. De cada una
# recoge: estado del documento, errores de consola y de página, peticiones XHR o
# fetch que devuelvan 4xx/5xx con su URL, promesas rechazadas sin capturar y una
# captura de pantalla. Después clasifica cada página en CONTENIDO REAL o ESTADO
# VACÍO (una que dice «no hay datos» NO aprueba), busca texto fabricado en el DOM
# visible ([MOCK], undefined, NaN, null, lorem, TODO, FIXME) y recorre los
# enlaces en anchura para contar cuántas páginas se alcanzan pinchando y cuántas
# existen sin que nadie las enlace.
#
# QUÉ **NO** MIDE:
#   - Que los datos sean CORRECTOS. Mide que HAY datos y que la pantalla no se
#     rompe; si una cifra está mal calculada, esto no se entera.
#   - Nada que haya detrás de un formulario: no rellena ni envía nada. Es un
#     recorrido de lectura.
#   - Los portales por token no se recorren en anchura: se entra en ellos por un
#     enlace que llega por correo, no pinchando desde la aplicación. Por eso NO
#     se cuentan como huérfanos; se declaran aparte.
#
# Necesita el demo en pie (`make demo`) y los navegadores de Playwright
# instalados (frontend/node_modules + ~/.cache/ms-playwright).
RECORRIDO_ESPERA ?= 4000
RECORRIDO_MAX_BFS ?= 220
recorrer-todo:
	@if [ ! -d frontend/node_modules/playwright ]; then
		echo "Falta frontend/node_modules/playwright. Ejecuta: (cd frontend && npm ci)" >&2
		exit 1
	fi
	cid="$$($(DC) ps -q backend 2>/dev/null || true)"
	if [ -z "$$cid" ]; then
		echo "ERROR: el backend del demo no está en pie. Ejecuta 'make demo' primero." >&2
		exit 1
	fi
	mkdir -p var/recorrido
	@# 1 · identificadores REALES para las 83 rutas dinámicas. Sin esto habría
	@# que inventarse UUIDs, y la pantalla de «no encontrado» devuelve HTTP 200:
	@# entraría en verde una ruta que no se ha comprobado.
	echo "==> resolviendo los identificadores de las rutas dinámicas"
	docker cp scripts/recorrido_identificadores.py "$$cid":/tmp/recorrido_identificadores.py
	docker exec -e PYTHONPATH=/app "$$cid" \
	  python /tmp/recorrido_identificadores.py /tmp/identificadores.json >/dev/null 2>&1 || {
		echo "ERROR: no se pudo construir el catálogo de identificadores." >&2
		docker exec -e PYTHONPATH=/app "$$cid" \
		  python /tmp/recorrido_identificadores.py /tmp/identificadores.json 2>&1 | tail -20 >&2
		exit 1
	}
	docker cp "$$cid":/tmp/identificadores.json var/recorrido/identificadores.json
	@# 2 · el segundo factor del operador, igual que hace `make recorrido`.
	secreto="$$(docker exec $(PROJECT)-postgres-1 psql -U $(PG_USER_DEMO) -d $(PG_DB_DEMO) -tA \
	  -c "SELECT s.secret FROM auth_totp_secrets s JOIN auth_users u ON u.id = s.user_id \
	      WHERE u.email = '$(FULKRO_DEMO_OWNER_EMAIL)' AND s.verified LIMIT 1;" | tr -d '[:space:]')"
	if [ -z "$$secreto" ]; then
		echo "No hay segundo factor enrolado para $(FULKRO_DEMO_OWNER_EMAIL). ¿Corrió 'make demo'?" >&2
		exit 1
	fi
	@# 3 · el recorrido. Devuelve != 0 si hay páginas fallidas o vacías sin
	@# justificar; el informe se genera IGUAL, porque un recorrido que falla es
	@# justo el que hay que leer.
	rc=0
	SECRETO_TOTP="$$secreto" NODE_PATH=frontend/node_modules \
	  RECORRIDO_ESPERA=$(RECORRIDO_ESPERA) RECORRIDO_MAX_BFS=$(RECORRIDO_MAX_BFS) \
	  node scripts/recorrer_todo.cjs || rc=$$?
	python3 scripts/recorrido_informe.py
	echo
	echo "Informe:  docs/RECORRIDO_COMPLETO.md"
	echo "Capturas: var/recorrido/capturas/  ·  Detalle: var/recorrido/recorrido.json"
	exit $$rc

# ───────────────────────────────────────────────────────────────────────────
# Prueba de carga modesta (BLOQUE H).
#
# Para qué: para poder decir «escalable» con un número detrás. Sin un límite
# medido la palabra no significa nada — toda aplicación escala hasta que deja de
# hacerlo, y lo único defendible es decir DÓNDE deja de hacerlo.
#
# QUÉ MIDE: una rampa de concurrencia (1→80) sobre los seis endpoints más
# llamados de verdad —elegidos contando el tráfico que el recorrido completo del
# BLOQUE E generó sobre el registro de acceso del backend, no a ojo— hasta
# encontrar dónde se rompe el p95. Publica p50/p95/p99, peticiones por segundo,
# errores y el uso de CPU de cada contenedor en cada escalón, que es lo que
# permite decir dónde está el cuello en vez de suponerlo. Y repite la medida con
# DOS RÉPLICAS del backend, reutilizando el montaje de D4.
#
# QUÉ **NO** MIDE, y conviene tenerlo delante al leer los números:
#   - No es una prueba de producción. Corre contra un Docker Compose en un
#     portátil donde la base, Redis, MinIO, el frontend y el propio generador de
#     carga comparten las mismas CPU. Los números absolutos valen para ESA
#     máquina; lo que se traslada es la forma de la curva y dónde está el cuello.
#   - No mide el frontend: entra por el puerto del backend a propósito.
#   - No mide escrituras: todos los endpoints son de lectura, porque una rampa
#     de escrituras dejaría el demo inservible para el resto de bloques.
#   - Con concurrencias altas, parte del límite puede ser del propio generador
#     (Python con hilos). Por eso se publica la CPU por contenedor: es lo que
#     distingue «se rompió el servidor» de «se rompió mi medidor».
CARGA_SEGUNDOS ?= 12
carga:
	@cid="$$($(DC) ps -q backend 2>/dev/null || true)"
	if [ -z "$$cid" ]; then
		echo "ERROR: el demo no está en pie. Ejecuta 'make demo' primero." >&2
		exit 1
	fi
	mkdir -p out
	echo "==> 1 de 2 · una réplica"
	python3 scripts/prueba_de_carga.py --replicas 1 --segundos $(CARGA_SEGUNDOS) \
	  --salida out/carga_1_replica.json
	echo
	echo "==> 2 de 2 · dos réplicas (montaje de D4: nginx + reparto por turnos)"
	docker compose -f $(COMPOSE_FILE) -f docker-compose.escalabilidad.yml -p $(PROJECT) \
	  up -d --no-build --scale backend=2 >/dev/null
	@# Espera activa a que las DOS estén sanas: medir contra una réplica que
	@# todavía arranca daría un p95 malísimo que no es del sistema, es del reloj.
	for i in $$(seq 1 60); do
		sanos="$$(docker ps --filter "label=com.docker.compose.project=$(PROJECT)" \
		          --filter "label=com.docker.compose.service=backend" \
		          --format '{{.Status}}' | grep -c healthy || true)"
		[ "$${sanos:-0}" -ge 2 ] && break
		sleep 5
	done
	python3 scripts/prueba_de_carga.py --replicas 2 --segundos $(CARGA_SEGUNDOS) \
	  --salida out/carga_2_replicas.json || true
	echo "==> restaurando el demo a una sola réplica"
	docker compose -f $(COMPOSE_FILE) -f docker-compose.escalabilidad.yml -p $(PROJECT) \
	  down --remove-orphans >/dev/null 2>&1 || true
	$(DC) up -d --no-build >/dev/null
	echo
	echo "Medidas en bruto: out/carga_1_replica.json · out/carga_2_replicas.json"
	echo "Conclusiones:     docs/PRUEBA_DE_CARGA.md"
