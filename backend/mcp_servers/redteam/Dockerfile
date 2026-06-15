FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git wget curl ca-certificates dotnet-sdk-8.0 \
 && rm -rf /var/lib/apt/lists/*

# Frameworks red-team pesados · best-effort por diseño (pueden fallar en slim) ·
# log VISIBLE (antes 2>/dev/null ocultaba el fallo → imagen verde sin frameworks).
RUN ( git clone --depth 1 https://github.com/mitre/caldera.git /opt/caldera \
      && pip install --no-cache-dir -r /opt/caldera/requirements.txt ) \
    || echo "caldera best-effort · omitido (log visible)"

RUN git clone --depth 1 https://github.com/redcanaryco/atomic-red-team.git /opt/atomic-red-team \
    || echo "atomic-red-team best-effort · omitido (log visible)"

RUN pip install --no-cache-dir infection-monkey \
    || echo "infection-monkey best-effort · omitido (log visible)"

# §6 audit-2026-06-15 · el build FALLA si falta el toolchain base certero (dotnet).
RUN command -v dotnet >/dev/null 2>&1 || { echo "FALTA toolchain base: dotnet" >&2; exit 1; }

COPY shared/ /app/shared/
COPY redteam/ /app/redteam/
WORKDIR /app
CMD ["python", "-m", "redteam.server"]
