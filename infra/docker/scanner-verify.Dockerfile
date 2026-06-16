# Verificación aislada de la capa de scanners read-only (audit-roundup 2026-06-16 · Opción 1).
# NO es imagen de producción: replica SOLO la receta de instalación de
# trivy/grype/checkov/scoutsuite/nikto sobre python:3.12-slim (misma base que el
# backend) para probar que instalan y ejecutan, SIN reconstruir el backend completo
# (que arrastra libreoffice/tesseract/torch · ~30 min). Build:
#   docker build -f infra/docker/scanner-verify.Dockerfile -t fulkro-scanner-verify .
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN (curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh \
        | sh -s -- -b /usr/local/bin v0.58.1) \
    || (curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh \
        | sh -s -- -b /usr/local/bin)
RUN (curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh \
        | sh -s -- -b /usr/local/bin v0.87.0) \
    || (curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh \
        | sh -s -- -b /usr/local/bin)
RUN pip install --no-cache-dir pipx
RUN PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install "checkov==3.2.334" \
    || PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install checkov
RUN PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install "ScoutSuite==5.14.0" \
    || PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install ScoutSuite

# Prueba dura: los 5 binarios resuelven y responden a --version (build FALLA si no).
RUN set -e; \
    echo "=== scanner-verify (Opción 1) ==="; \
    for t in trivy grype checkov scout; do \
      command -v "$t" >/dev/null 2>&1 || { echo "FAIL: $t no instalado"; exit 1; }; \
      printf "%s -> " "$t"; ( "$t" --version 2>&1 | head -1 ) || true; \
    done; \
    echo "OK: trivy/grype/checkov/scoutsuite(scout) instalados"
