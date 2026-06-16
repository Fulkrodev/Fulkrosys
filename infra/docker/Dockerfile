FROM python:3.12-slim AS base

# System dependencies for document generation + M8 v5.1 verification tools.
# Las tools mas pesadas (ZAP, OpenVAS) viven en containers separados
# (vease docker-compose: fulkro-scanner). Aqui solo las ligeras que el
# motor invoca via subprocess directo desde el proceso uvicorn.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    libpq-dev \
    libcairo2-dev \
    tesseract-ocr \
    tesseract-ocr-spa \
    libreoffice-writer-nogui \
    pandoc \
    nmap \
    testssl.sh \
    lynis \
    dnsutils \
    ldap-utils \
    postgresql-client \
    curl \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# El paquete testssl.sh de Debian trixie instala el binario como `testssl`
# (sin extensión `.sh`). El código del motor (mcp_servers/webpentest/tools/
# testssl_tool.py) y la verificación de abajo invocan `testssl.sh`. Symlink
# idempotente para que ambos nombres resuelvan (HOTFIX build prod · base trixie).
RUN if [ ! -e /usr/bin/testssl.sh ] && [ -e /usr/bin/testssl ]; then \
        ln -s /usr/bin/testssl /usr/bin/testssl.sh; \
    fi

# Nuclei (Go binary) — ProjectDiscovery oficial
RUN curl -sL https://github.com/projectdiscovery/nuclei/releases/download/v3.3.0/nuclei_3.3.0_linux_amd64.zip -o /tmp/nuclei.zip \
    && cd /tmp && python3 -c "import zipfile; zipfile.ZipFile('nuclei.zip').extractall('/usr/local/bin/')" \
    && chmod +x /usr/local/bin/nuclei \
    && rm /tmp/nuclei.zip

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
# server.py vía mcp_client cuando USE_MCP_REAL=true) y que faltaban en la imagen:
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

# Verification: si alguna tool ligera falta, el build FALLA. ZAP y
# openvas-scanner viven en fulkro-scanner (compose); aqui solo las
# que invocamos directamente desde la app FastAPI.
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

# ─────────────────────────────────────────────────────────────────────────────
# W9-2 hardening (audit-roundup 2026-06-16 · §5) · USUARIO NO-ROOT · DOCUMENTADO,
# NO ACTIVADO. El contenedor corre hoy como root. Pasar a un usuario no-root es
# deseable (defensa en profundidad) PERO NO se puede activar a ciegas vía CD:
#
#   BLOQUEANTE = el volumen Docker `vardata` (docker-compose.prod.yml:166,213,410)
#   se monta en /app/var COMPARTIDO por backend + celery-worker y YA EXISTE en el
#   host Hetzner con contenido propiedad de root (evidencias en filesystem,
#   hf-cache de embeddings, logs). Si se añade `USER fulkro` sin un `chown`
#   coordinado del volumen EN EL SERVIDOR, los writes a /app/var fallarían con
#   EACCES (rompería /documents, evidencias, descarga de modelos HF).
#
# PASO HETZNER-ONLY requerido ANTES de activar el bloque de abajo (un único
# operador, con la app parada para evitar writes a medias):
#   docker compose -f docker-compose.prod.yml stop backend celery-worker
#   docker run --rm -v fulkro_vardata:/v alpine chown -R 10001:10001 /v
#   # (sustituir `fulkro_vardata` por el nombre real: `docker volume ls`)
#   # luego rebuild + up con el Dockerfile que tenga el bloque USER activo.
#
# Bind de plantillas DOCX `./var/templates_docx:/app/var/templates_docx:ro` es
# read-only → no requiere chown. El bind `./infra/docker:ro` (provision) tampoco.
#
# Para ACTIVAR (tras el chown de arriba), descomentar:
#   RUN useradd -m -u 10001 -s /usr/sbin/nologin fulkro \
#       && mkdir -p /app/var \
#       && chown -R fulkro:fulkro /app/var
#   USER fulkro
# ─────────────────────────────────────────────────────────────────────────────

# Default command: run FastAPI with uvicorn
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
