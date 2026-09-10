# ════════════════════════════════════════════════════════════════════════════
# FULKRO · imagen del backend — DOS VARIANTES DESDE UN SOLO FICHERO
# ════════════════════════════════════════════════════════════════════════════
# Medido el 2026-09-10 sobre la imagen de una sola pieza que había antes:
# 7,91 GB, de los cuales ~4,4 GB eran instrumental de pentest (ScoutSuite 1,66 GB
# + Prowler 1,6 GB + checkov 348 MB + semgrep 333 MB + trivy 168 MB + nuclei
# 78,3 MB + grype 69,6 MB + httpx 38,5 MB + subfinder 29 MB, según
# `docker history`). Esa imagen la usan `backend`, `provision`, `celery-worker`
# y `celery-beat`: cuatro servicios que NO ejecutan un solo escáner para servir
# la aplicación. Pedir 8 GB de herramientas de ataque para ver un panel de
# cumplimiento es un bloqueante de instalabilidad, así que se parte
# (docs/adr/ADR-002-imagen-backend-sin-instrumental-pentest.md).
#
# ── Cómo se elige la variante ───────────────────────────────────────────────
# El argumento de build RUNTIME decide de qué base cuelga la aplicación:
#
#   docker build -f infra/docker/Dockerfile .                    → APLICACIÓN
#       RUNTIME=runtime-lean (por defecto). BuildKit NO construye siquiera la
#       etapa runtime-pentest, así que la descarga de nuclei y compañía deja de
#       estar en el camino del demo: github.com puede estar caído y `make demo`
#       sigue funcionando.
#
#   docker build -f infra/docker/Dockerfile \
#                --build-arg RUNTIME=runtime-pentest .           → INSTRUMENTAL
#       Misma aplicación MÁS los escáneres. Es la imagen del perfil `scanner`
#       de docker-compose.yml (servicio `fulkro-scanner-tools`).
#
# Las capas de la aplicación se escriben UNA sola vez, al final: las dos
# variantes las comparten. Y el orden de instalación se conserva exactamente
# como estaba: primero el instrumental, DESPUÉS `uv pip install -e .[runtime]`,
# para que las dependencias de la aplicación sigan ganando cualquier conflicto
# de versiones con prowler/semgrep (que se instalan en el Python del sistema).
#
# ── Qué pasa cuando los escáneres no están ──────────────────────────────────
# Degradan, no revientan. El contrato está en el código, no en este comentario:
#   · backend/app/motors/m08_verification/tools/base.py:121  is_binary_available()
#     = `shutil.which(binario) is not None`; `ensure_available()` levanta
#     RunnerNotInstalled, que remediation/retest_runner.py captura en 5 sitios.
#   · backend/app/mcp_client.py:242  scanner_capability() devuelve
#     `available=False` con su razón ("herramienta 'nuclei' no instalada en este
#     host") e invoke_mcp corta limpio, sin fingir un hallazgo.
# ════════════════════════════════════════════════════════════════════════════

# ARG global: sólo es visible en las instrucciones FROM. Va antes del primer
# FROM a propósito; ahí es donde Docker lo admite.
ARG RUNTIME=runtime-lean


# ════════════════════════════════════════════════════════════════════════════
# ETAPA `base` — sistema operativo que la aplicación necesita para SERVIR
# ════════════════════════════════════════════════════════════════════════════
# Aquí sólo entra lo que usa el proceso uvicorn o el aprovisionamiento:
#   build-essential/pkg-config/libpq-dev/libcairo2-dev  compilar ruedas Python
#   tesseract-ocr(-spa)                                 OCR de evidencias
#   libreoffice-writer-nogui + pandoc                   generación de entregables
#   postgresql-client                                   psql, que invoca
#                                                       provision-entrypoint.sh
#   curl                                                healthcheck de compose
#   ca-certificates                                     TLS saliente
FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    libpq-dev \
    libcairo2-dev \
    tesseract-ocr \
    tesseract-ocr-spa \
    libreoffice-writer-nogui \
    pandoc \
    postgresql-client \
    curl \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*


# ════════════════════════════════════════════════════════════════════════════
# ETAPA `runtime-lean` — la base, tal cual. Variante por defecto.
# ════════════════════════════════════════════════════════════════════════════
FROM base AS runtime-lean
LABEL es.fulkro.variante="lean" \
      es.fulkro.instrumental-pentest="no · los escáneres degradan a no disponible"


# ════════════════════════════════════════════════════════════════════════════
# ETAPA `runtime-pentest` — la base MÁS el instrumental de escaneo
# ════════════════════════════════════════════════════════════════════════════
# Todo lo que hay de aquí a la siguiente etapa se construye ÚNICAMENTE cuando se
# pide RUNTIME=runtime-pentest. En la construcción por defecto BuildKit ni la
# mira, así que ni descarga releases de GitHub ni tarda en ello.
FROM base AS runtime-pentest

# Herramientas de paquete Debian. nmap/testssl.sh/lynis los invoca m08 por
# subprocess. dnsutils (dig) y ldap-utils (ldapsearch) se conservan por
# continuidad, PERO medido el 2026-09-10 no los invoca nadie: dns_checker.py usa
# dnspython y ad_password_checker.py usa ldap3, ambas bibliotecas Python. El
# único sitio del repositorio que nombraba `dig` y `ldapsearch` era la
# verificación `which` de este mismo fichero.
RUN apt-get update && apt-get install -y --no-install-recommends \
    nmap \
    testssl.sh \
    lynis \
    dnsutils \
    ldap-utils \
    && rm -rf /var/lib/apt/lists/*

# El paquete testssl.sh de Debian trixie instala el binario como `testssl`
# (sin extensión `.sh`). El código del motor (mcp_servers/webpentest/tools/
# testssl_tool.py) y la verificación de abajo invocan `testssl.sh`. Symlink
# idempotente para que ambos nombres resuelvan (HOTFIX build prod · base trixie).
RUN if [ ! -e /usr/bin/testssl.sh ] && [ -e /usr/bin/testssl ]; then \
        ln -s /usr/bin/testssl /usr/bin/testssl.sh; \
    fi

# Nuclei (Go binary) — ProjectDiscovery oficial.
# Best-effort, igual que httpx/subfinder/semgrep/trivy/grype: si GitHub no responde
# o la release cambia de nombre, el build NO se rompe y scanner_capabilities() lo
# refleja honesto. Desde que esta etapa es opcional, además, una caída de
# github.com ya no puede tocar el camino del demo.
RUN (curl -sfL https://github.com/projectdiscovery/nuclei/releases/download/v3.3.0/nuclei_3.3.0_linux_amd64.zip -o /tmp/nuclei.zip \
      && cd /tmp && python3 -c "import zipfile; zipfile.ZipFile('nuclei.zip').extractall('/usr/local/bin/')" \
      && chmod +x /usr/local/bin/nuclei \
      && rm -f /tmp/nuclei.zip) \
    || echo "WARNING: nuclei install failed"


# Prowler (cloud scanner) — pip install
RUN pip install --no-cache-dir prowler-cloud==4.0.0 || \
    pip install --no-cache-dir prowler==3.13.0 || \
    echo "WARNING: Prowler install failed; container scanner alternativo en fulkro-scanner"

# httpx + subfinder (Go binaries · ProjectDiscovery) — recon (httpx_scan está en
# el plan BASICO del autopilot · subfinder en MEDIO/ALTO). Best-effort: si una
# release falla, el build NO se rompe y scanner_capabilities() lo refleja honesto.
RUN (curl -sfL https://github.com/projectdiscovery/httpx/releases/download/v1.6.9/httpx_1.6.9_linux_amd64.zip -o /tmp/httpx.zip \
      && cd /tmp && python3 -c "import zipfile; zipfile.ZipFile('httpx.zip').extractall('/usr/local/bin/')" \
      && chmod +x /usr/local/bin/httpx && rm -f /tmp/httpx.zip) \
    || echo "WARNING: httpx install failed"
RUN (curl -sfL https://github.com/projectdiscovery/subfinder/releases/download/v2.6.6/subfinder_2.6.6_linux_amd64.zip -o /tmp/subfinder.zip \
      && cd /tmp && python3 -c "import zipfile; zipfile.ZipFile('subfinder.zip').extractall('/usr/local/bin/')" \
      && chmod +x /usr/local/bin/subfinder && rm -f /tmp/subfinder.zip) \
    || echo "WARNING: subfinder install failed"

# semgrep (SAST · pip) — sast plan. Best-effort (fallback graceful).
RUN pip install --no-cache-dir semgrep || echo "WARNING: semgrep install failed"

# ─────────────────────────────────────────────────────────────────────────────
# Scanners ENS read-only (audit-roundup 2026-06-16 · Opción 1 · pentest funcional
# en Hetzner). Estos son los binarios que el motor m08 invoca IN-PROCESS (spawn de
# server.py vía mcp_client cuando USE_MCP_REAL=true):
#   · trivy  → mcp_servers/vulnscan/tools/trivy_tool.py  (CVE imagen/fs)
#   · grype  → mcp_servers/vulnscan/tools/grype_tool.py  (CVE SBOM)
#   · checkov→ mcp_servers/sast/tools/checkov_tool.py    (IaC/cloud config)
#   · scoutsuite → m08_verification/tools/scoutsuite_runner.py (postura cloud)
# Alimentan el puente pentest→remediación (cloud writers + agente on-prem · ADR-055).
# nikto (web) NO se instala: el paquete no existe en python:3.12-slim (Debian trixie)
# y la remediación no actúa sobre hallazgos web → webpentest/nikto_tool degrada a
# stub honesto (scanner_capabilities lo refleja). Diferido a la imagen pentest ALTA.
# Best-effort + versión fijada con fallback: si una release/PyPI falla, el build NO
# se rompe; scanner_capabilities() lo refleja honesto y el pipeline degrada con stub.
# trivy + grype: binarios standalone (Go · 0 deps Python) → install script + symlink.
RUN (curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh \
        | sh -s -- -b /usr/local/bin v0.71.1) \
    || (curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh \
        | sh -s -- -b /usr/local/bin) \
    || echo "WARNING: trivy install failed (vulnscan trivy_tool degrada a stub)"
RUN (curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh \
        | sh -s -- -b /usr/local/bin v0.87.0) \
    || (curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh \
        | sh -s -- -b /usr/local/bin) \
    || echo "WARNING: grype install failed (vulnscan grype_tool degrada a stub)"
# checkov + scoutsuite: CLIs Python con árboles de deps pesados → pipx (venv AISLADO
# por herramienta · shim en /usr/local/bin) para NO contaminar ni romper el entorno
# de la app (uv pip install -e .[runtime] más abajo). Verificado: checkov 3.2.334 +
# ScoutSuite 5.14.0 instalan y ejecutan (--version) en una capa aislada.
RUN pip install --no-cache-dir pipx || echo "WARNING: pipx install failed (checkov/scoutsuite degradan a stub)"
RUN PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install "checkov==3.2.334" \
    || PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install checkov \
    || echo "WARNING: checkov install failed (sast checkov_tool degrada a stub)"
RUN PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install "ScoutSuite==5.14.0" \
    || PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install ScoutSuite \
    || echo "WARNING: scoutsuite install failed (cloud scoutsuite_runner degrada a stub)"

# Verificación: si alguna tool ligera falta, el build de ESTA variante FALLA. ZAP y
# openvas-scanner viven en fulkro-scanner (compose); aquí sólo las que se invocan
# directamente desde la app FastAPI. La variante por defecto no pasa por aquí.
RUN which nmap && \
    which nuclei && \
    which testssl.sh && \
    which lynis && \
    which dig && \
    which ldapsearch && \
    nuclei -version && \
    nmap --version | head -1

# Reporte SOFT de capacidades de los scanners best-effort (trivy/grype/checkov/
# scoutsuite/prowler/...): NO rompe el build (un binario ausente degrada a stub
# vía scanner_capabilities). Sirve para auditar en los logs del build qué arsenal
# read-only quedó realmente disponible para USE_MCP_REAL=true.
RUN echo "=== scanner-capabilities (read-only ENS · Opción 1) ===" && \
    for t in trivy grype checkov scout scoutsuite nikto prowler httpx subfinder semgrep nuclei nmap; do \
      if command -v "$t" >/dev/null 2>&1; then echo "  $t = OK"; else echo "  $t = ABSENT (degrada a stub)"; fi; \
    done

LABEL es.fulkro.variante="pentest" \
      es.fulkro.instrumental-pentest="sí · nmap nuclei testssl lynis prowler trivy grype checkov scoutsuite semgrep httpx subfinder"


# ════════════════════════════════════════════════════════════════════════════
# ETAPA FINAL — la aplicación, sobre la base que haya elegido RUNTIME
# ════════════════════════════════════════════════════════════════════════════
# Escrita una sola vez y compartida por las dos variantes.
FROM ${RUNTIME} AS app

# Install uv for fast dependency management
RUN pip install uv

WORKDIR /app

# Copy dependency files first for caching
COPY backend/pyproject.toml ./backend/
# Sin enmascarar el fallo: si una dependencia no resuelve, el build DEBE romper
# (B2 · antes `2>/dev/null || true` ocultaba py-webauthn inexistente → imagen
# sin deps Python → backend no arranca en runtime).
#
# W9-2 hardening (audit-roundup 2026-06-16 · §5): la imagen de PRODUCCIÓN instala
# `.[runtime]` (NO `.[dev]`) → NO arrastra pytest/ruff/mypy al contenedor (menor
# superficie de ataque · imagen más ligera). El extra `runtime` (backend/
# pyproject.toml) conserva las deps de producción que viven aparte del core por
# ser pesadas/opcionales: moto (lazy-import en prowler/scoutsuite_runner) +
# python-gvm (lazy-import en openvas_runner). El gate de tests corre LOCAL/CI con
# `.[dev]` (que incluye `.[runtime]`), no desde esta imagen.
#
# Va DESPUÉS del instrumental a propósito: en la variante pentest, prowler y
# semgrep se instalan en el mismo Python del sistema, y este paso final es el que
# fija las versiones que la aplicación necesita.
RUN cd backend && uv pip install --system -e ".[runtime]"

# Copy application code
COPY backend/ ./backend/
COPY frontend/ ./frontend/
# Catálogos de datos que leen el SEED (seed_all_fulkro: MAGERIT asset_types,
# safeguards, threats, template_catalog, legal_obligations) y el RUNTIME
# (copilot_personas_v1.yaml, lms_courses_v1.json, threats.yaml,
# SYSTEM_KNOWLEDGE_BASE.md, CANONICAL_PRICING.md...). Sin docs/ en la imagen el
# provision falla con FileNotFoundError docs/magerit_catalog/asset_types.yaml
# (deploy 2026-06-10).
COPY docs/ ./docs/

# Scripts y SQL de aprovisionamiento. El servicio `provision` arranca con
#   entrypoint: bash /app/infra/docker/provision-entrypoint.sh
# y ese script ejecuta los tres init-*.sql. Hasta ahora .dockerignore excluia
# `infra/` entero, no llegaban a la imagen y docker-compose tenia que montar
# ./infra/docker:/app/infra/docker:ro para taparlo. Con las dos negaciones del
# .dockerignore (`!infra/docker/*.sh` y `!infra/docker/*.sql`) aqui SOLO entran
# los seis ficheros que el proceso lee (4 .sql + 2 .sh): los Dockerfile de pentest,
# scanner-verify.Dockerfile y pgbackrest.conf siguen fuera del contexto.
COPY infra/docker/ ./infra/docker/

# ─────────────────────────────────────────────────────────────────────────────
# W9-2 hardening (audit-roundup 2026-06-16 · §5) · USUARIO NO-ROOT.
#
# CUIDADO al desplegar en un servidor que ya tenga el volumen `vardata` con
# contenido de root: hay que hacer el chown ANTES, con la aplicación parada, o
# los writes a /app/var fallan con EACCES.
#   docker compose -f docker-compose.prod.yml stop backend celery-worker
#   docker run --rm -v fulkro_vardata:/v alpine chown -R 10001:10001 /v
#   # (sustituir `fulkro_vardata` por el nombre real: `docker volume ls`)
#
# Los binds read-only (templates_docx · infra/docker) son legibles por 10001 (755).
# ─────────────────────────────────────────────────────────────────────────────
RUN useradd -m -u 10001 -s /usr/sbin/nologin fulkro \
    && mkdir -p /app/var \
    && chown -R fulkro:fulkro /app/var
USER fulkro

# Default command: run FastAPI with uvicorn
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
