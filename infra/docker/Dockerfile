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

# Install uv for fast dependency management
RUN pip install uv

WORKDIR /app

# Copy dependency files first for caching
COPY backend/pyproject.toml ./backend/
# Sin enmascarar el fallo: si una dependencia no resuelve, el build DEBE romper
# (B2 · antes `2>/dev/null || true` ocultaba py-webauthn inexistente → imagen
# sin deps Python → backend no arranca en runtime).
RUN cd backend && uv pip install --system -e ".[dev]"

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

# Default command: run FastAPI with uvicorn
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
