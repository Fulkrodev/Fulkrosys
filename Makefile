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

.PHONY: help demo smoke down clean test lint logs recorrido check-tools .env-keys

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
lint:
	@$(RUFF) check backend/

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
