FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git wget curl ca-certificates dotnet-sdk-8.0 \
 && rm -rf /var/lib/apt/lists/* 2>/dev/null || true

RUN git clone --depth 1 https://github.com/mitre/caldera.git /opt/caldera 2>/dev/null || true \
 && pip install --no-cache-dir -r /opt/caldera/requirements.txt 2>/dev/null || true

RUN git clone --depth 1 https://github.com/redcanaryco/atomic-red-team.git /opt/atomic-red-team 2>/dev/null || true

RUN pip install --no-cache-dir infection-monkey 2>/dev/null || true

COPY shared/ /app/shared/
COPY redteam/ /app/redteam/
WORKDIR /app
CMD ["python", "-m", "redteam.server"]
